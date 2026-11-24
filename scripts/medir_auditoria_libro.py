"""Mide la auditoría de Sílice sobre un libro, con la marca de personas (anteproyecto v8, §8).

Herramienta LOCAL: no forma parte del producto y nada de lo que produce entra al repositorio. Los
libros, las planillas marcadas y la clave de la siembra se quedan en el equipo (NORMAS §1); lo
único que sale es el resumen con cifras agregadas, sin celdas ni descripciones.

Protocolo (ver `docs/tesis/2026-11-23-protocolo-medicion-auditoria.md`):

1. `clave`: el autor que NO escribió las reglas prepara la clave de la siembra (qué errores sembró
   y en qué celda) antes de correr Sílice.
2. `exportar`: Sílice audita el libro (el mismo proceso de la pantalla, `procesar_libro`) y los
   hallazgos salen a una planilla con la columna «Veredicto» (Verdadero o Falso) y la hoja «Se le
   escaparon» para los errores reales que Sílice no vio.
3. Cada evaluador marca su copia por separado, sin ver la clave.
4. `calcular`: precisión (Verdadero / marcados), detección de lo sembrado, exhaustividad
   aproximada (Verdadero / (Verdadero + escapados)) y, con dos planillas, el kappa de Cohen.

    uv run python scripts/medir_auditoria_libro.py clave --salida D:/medicion/clave.xlsx
    uv run python scripts/medir_auditoria_libro.py exportar LIBRO.xlsx --salida D:/medicion/p1.xlsx
    uv run python scripts/medir_auditoria_libro.py calcular --planilla p1.xlsx --otra p2.xlsx \\
        --clave clave.xlsx
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from aplicacion.causas_raiz import agrupar, es_no_aplicable, patron  # noqa: E402, F401

VERDADERO = "Verdadero"
FALSO = "Falso"
MARCAS = {"verdadero": VERDADERO, "falso": FALSO}
SEPARADOR_CELDAS = "; "

ENCABEZADO_HALLAZGOS = ("N°", "Regla", "Severidad", "Ocurrencias", "Celdas", "Descripción",
                        "Impacto", "Veredicto", "Nota del evaluador")
ENCABEZADO_ESCAPADOS = ("Celda", "Qué error es")
ENCABEZADO_CLAVE = ("N°", "Celda", "Tipo de error", "Qué se cambió", "Detectado por hallazgo N°")

INSTRUCCIONES = (
    "Medición de la auditoría de Sílice. Esta planilla NO se sube a ningún repositorio.",
    "1. En la hoja «Hallazgos», marque cada fila en «Veredicto»: Verdadero si es un error real del "
    "libro, Falso si no lo es. Si no sabe, déjela en blanco: cuenta como pendiente.",
    "2. Marque solo, sin hablar con el otro evaluador y sin ver la clave de la siembra.",
    "3. Si al revisar el libro encuentra un error que Sílice no señaló, anótelo en la hoja «Se le "
    "escaparon» (una fila por error).",
    "4. No cambie los números de la columna N° ni borre filas.",
)


# --- las filas de la planilla --------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FilaPlanilla:
    numero: int
    regla: str
    severidad: str
    celdas: tuple[str, ...]
    descripcion: str
    impacto: float | None = None
    ocurrencias: int = 1


def _no_aplica(h) -> bool:
    """El aviso de una regla que no tuvo nada que revisar (R2 y R7 sin curva ni plan, UC-05 2a):
    no es un error del libro y no se marca. Mismo criterio que la pantalla de auditoría."""
    return es_no_aplicable(h.severidad.name, h.descripcion)


def reglas_no_aplicables(hallazgos: Iterable) -> list[str]:
    return sorted({h.regla for h in hallazgos if _no_aplica(h)})


def filas_de_hallazgos(hallazgos: Iterable) -> list[FilaPlanilla]:
    """Un `Hallazgo` del núcleo por fila, numerados desde 1 en el orden del informe; los avisos de
    regla no aplicable quedan fuera."""
    hallazgos = [h for h in hallazgos if not _no_aplica(h)]
    return [
        FilaPlanilla(
            numero=i,
            regla=h.regla,
            severidad=h.severidad.name,
            celdas=tuple(str(c) for c in h.origen_ids),
            descripcion=h.descripcion,
            impacto=float(h.impacto) if h.impacto is not None else None,
        )
        for i, h in enumerate(hallazgos, start=1)
    ]


def causas_de_hallazgos(hallazgos: Iterable) -> list[FilaPlanilla]:
    """Una fila por causa raíz (misma regla y mismo patrón, `aplicacion/causas_raiz.py`, lo mismo
    que muestra la pantalla de auditoría), numeradas desde 1 en el orden en que aparece su primer
    caso. Lleva la severidad más grave, todas las celdas, la suma del impacto y cuántos hallazgos
    agrupa. Los avisos de regla no aplicable quedan fuera."""
    hallazgos = list(hallazgos)
    causas, _ = agrupar([(h.regla, h.severidad.name, h.descripcion) for h in hallazgos])
    filas = []
    for numero, causa in enumerate(causas, start=1):
        casos = [hallazgos[i] for i in causa.indices]
        celdas = tuple(dict.fromkeys(str(c) for h in casos for c in h.origen_ids))
        impactos = [h.impacto for h in casos if h.impacto is not None]
        filas.append(FilaPlanilla(
            numero=numero,
            regla=casos[0].regla,
            severidad=max(casos, key=lambda h: h.severidad).severidad.name,
            celdas=celdas,
            descripcion=casos[0].descripcion,
            impacto=float(sum(impactos)) if impactos else None,
            ocurrencias=len(casos),
        ))
    return filas


# --- las medidas ---------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Medida:
    aciertos: int
    total: int
    pendientes: int = 0

    @property
    def valor(self) -> float | None:
        return self.aciertos / self.total if self.total else None


def _marca(texto: object) -> str:
    """La marca normalizada: «Verdadero», «Falso» o "" (pendiente)."""
    limpio = str(texto or "").strip()
    if not limpio:
        return ""
    try:
        return MARCAS[limpio.casefold()]
    except KeyError:
        raise ValueError(f"Marca desconocida «{limpio}»: use {VERDADERO} o {FALSO}.") from None


def precision(marcas: Mapping[int, object]) -> Medida:
    """Verdaderos sobre lo marcado; lo que quedó en blanco se cuenta aparte como pendiente."""
    normales = [_marca(v) for v in marcas.values()]
    marcadas = [v for v in normales if v]
    return Medida(aciertos=marcadas.count(VERDADERO), total=len(marcadas),
                  pendientes=len(normales) - len(marcadas))


def exhaustividad(verdaderos: int, escapados: int) -> Medida:
    """Aproximada: los errores reales son los que Sílice acertó más los que el evaluador anotó
    como «se le escapó». Depende de cuánto buscó el evaluador; se declara como tal."""
    return Medida(aciertos=verdaderos, total=verdaderos + escapados)


@dataclass(frozen=True, slots=True)
class Sembrado:
    numero: int
    celda: str
    tipo: str
    detectado_por: int | None = None


@dataclass(frozen=True, slots=True)
class Deteccion:
    por_sembrado: dict[int, int | None] = field(default_factory=dict)
    manuales: int = 0

    @property
    def total(self) -> int:
        return len(self.por_sembrado)

    @property
    def detectados(self) -> int:
        return sum(1 for v in self.por_sembrado.values() if v is not None)

    @property
    def valor(self) -> float | None:
        return self.detectados / self.total if self.total else None


def _celda(texto: str) -> str:
    return texto.strip().replace("$", "").casefold()


def deteccion(sembrados: Sequence[Sembrado], filas: Sequence[FilaPlanilla]) -> Deteccion:
    """Qué error sembrado señaló Sílice. Manda la columna «Detectado por hallazgo N°» de la clave
    (la llena quien sembró, porque un error en un APU puede aparecer en otra celda); si está
    vacía, cuenta como detectado el primer hallazgo que apunta a la misma celda."""
    numeros = {f.numero for f in filas}
    por: dict[int, int | None] = {}
    manuales = 0
    for s in sembrados:
        if s.detectado_por is not None:
            if s.detectado_por not in numeros:
                raise ValueError(
                    f"El sembrado {s.numero} dice que lo detectó el hallazgo {s.detectado_por}, "
                    "y ese número no está en la planilla."
                )
            por[s.numero] = s.detectado_por
            manuales += 1
            continue
        objetivo = _celda(s.celda)
        por[s.numero] = next(
            (f.numero for f in filas if any(_celda(c) == objetivo for c in f.celdas)), None
        )
    return Deteccion(por_sembrado=por, manuales=manuales)


def kappa_cohen(a: Sequence[str], b: Sequence[str]) -> float | None:
    """Kappa de Cohen (1960) para dos evaluadores sobre los mismos casos y categorías nominales.
    `None` si el acuerdo esperado por azar es 1 (los dos usaron una sola categoría)."""
    if len(a) != len(b):
        raise ValueError("Las dos listas de marcas deben tener el mismo largo.")
    if not a:
        raise ValueError("No hay casos marcados por los dos evaluadores.")
    n = len(a)
    observado = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    esperado = sum(ca[k] * cb[k] for k in ca.keys() | cb.keys()) / (n * n)
    if esperado == 1:
        return None
    return (observado - esperado) / (1 - esperado)


# --- formato -------------------------------------------------------------------------------------


def decimal_coma(valor: float, decimales: int = 2) -> str:
    return f"{valor:.{decimales}f}".replace(".", ",")


def porcentaje(valor: float | None) -> str:
    return "sin dato" if valor is None else decimal_coma(valor * 100, 1) + " %"


def resumen(*, precision: Medida, deteccion: Deteccion | None, exhaustividad: Medida,
            kappa: float | None, marcados_por_los_dos: int | None = None,
            agrupacion: tuple[int, int] | None = None) -> str:
    """Las cifras agregadas para la tesis: sin celdas, sin descripciones, sin nombres."""
    lineas = [
        "| Medida | Cuentas | Valor |",
        "|---|---|---|",
        f"| Precisión (verdaderos / marcados) | {precision.aciertos} de {precision.total} "
        f"({precision.pendientes} pendientes) | {porcentaje(precision.valor)} |",
    ]
    if deteccion is not None:
        lineas.append(
            f"| Detección de errores sembrados | {deteccion.detectados} de {deteccion.total} "
            f"({deteccion.manuales} por la columna manual) | {porcentaje(deteccion.valor)} |"
        )
    lineas.append(
        f"| Exhaustividad aproximada (con «se le escapó») | {exhaustividad.aciertos} de "
        f"{exhaustividad.total} | {porcentaje(exhaustividad.valor)} |"
    )
    texto_kappa = "sin dato (hace falta una segunda planilla con variación)" if kappa is None \
        else decimal_coma(kappa)
    lineas.append(f"| Kappa de Cohen entre los dos evaluadores | — | {texto_kappa} |")
    if agrupacion is not None and agrupacion[1]:
        hallazgos, causas = agrupacion
        lineas += ["", f"{hallazgos} hallazgos agrupados en {causas} causas "
                       f"({decimal_coma(hallazgos / causas, 1)} por causa)."]
    if marcados_por_los_dos is not None:
        lineas += ["", f"Hallazgos marcados por los dos: {marcados_por_los_dos}"]
    return "\n".join(lineas)


# --- disco ---------------------------------------------------------------------------------------


def _destino_seguro(destino: Path, raiz_repo: Path) -> Path:
    destino = destino.resolve()
    if destino.is_relative_to(raiz_repo.resolve()):
        raise ValueError(
            f"«{destino}» está dentro del repositorio: los datos de la medición se guardan fuera "
            "(NORMAS §1). Elija una carpeta fuera del proyecto."
        )
    if destino.exists():
        raise FileExistsError(f"«{destino}» ya existe; no se sobrescribe una planilla.")
    return destino


def _texto(celda, valor: object) -> None:
    """Escribe texto tal cual: lo que empieza con «=» no se vuelve fórmula."""
    celda.value = "" if valor is None else str(valor)
    celda.data_type = "s"


def _hoja_con_encabezado(libro, titulo: str, encabezado: Sequence[str]):
    from openpyxl.styles import Font

    hoja = libro.create_sheet(titulo)
    hoja.append(list(encabezado))
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    hoja.freeze_panes = "A2"
    return hoja


def escribir_planilla(filas: Sequence[FilaPlanilla], destino: Path, *, raiz_repo: Path = RAIZ,
                      origen: Mapping[str, str] | None = None) -> Path:
    """La planilla para que un evaluador marque los hallazgos."""
    import openpyxl
    from openpyxl.worksheet.datavalidation import DataValidation

    destino = _destino_seguro(Path(destino), Path(raiz_repo))
    libro = openpyxl.Workbook()
    instrucciones = libro.active
    instrucciones.title = "Instrucciones"
    for linea in INSTRUCCIONES:
        instrucciones.append([linea])
    for clave, valor in (origen or {}).items():
        instrucciones.append([f"{clave}: {valor}"])
    instrucciones.column_dimensions["A"].width = 110

    hoja = _hoja_con_encabezado(libro, "Hallazgos", ENCABEZADO_HALLAZGOS)
    for f in filas:
        fila = hoja.max_row + 1
        hoja.cell(row=fila, column=1, value=f.numero)
        hoja.cell(row=fila, column=4, value=f.ocurrencias)
        for col, valor in ((2, f.regla), (3, f.severidad), (5, SEPARADOR_CELDAS.join(f.celdas)),
                           (6, f.descripcion)):
            _texto(hoja.cell(row=fila, column=col), valor)
        hoja.cell(row=fila, column=7, value=f.impacto)
    columna = ENCABEZADO_HALLAZGOS.index("Veredicto") + 1
    letra = hoja.cell(row=1, column=columna).column_letter
    lista = DataValidation(type="list", formula1=f'"{VERDADERO},{FALSO}"', allow_blank=True)
    lista.add(f"{letra}2:{letra}{max(hoja.max_row, 2) + 500}")
    hoja.add_data_validation(lista)
    for letra_col, ancho in zip("ABCDEFGHI", (6, 8, 12, 12, 28, 70, 12, 12, 30), strict=True):
        hoja.column_dimensions[letra_col].width = ancho

    _hoja_con_encabezado(libro, "Se le escaparon", ENCABEZADO_ESCAPADOS)
    libro.save(destino)
    return destino


def escribir_clave_vacia(destino: Path, *, raiz_repo: Path = RAIZ) -> Path:
    """La clave de la siembra, vacía, para que la llene quien siembra."""
    import openpyxl

    destino = _destino_seguro(Path(destino), Path(raiz_repo))
    libro = openpyxl.Workbook()
    libro.remove(libro.active)
    _hoja_con_encabezado(libro, "Sembrados", ENCABEZADO_CLAVE)
    libro.save(destino)
    return destino


def _filas_de_hoja(ruta: Path, titulo: str, encabezado: Sequence[str]) -> list[dict[str, object]]:
    import openpyxl

    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    try:
        filas = libro[titulo].iter_rows(values_only=True)
        cabeza = [str(c or "").strip() for c in next(filas, ())]
        faltan = [c for c in encabezado if c not in cabeza]
        if faltan:
            raise ValueError(f"La hoja «{titulo}» de «{ruta.name}» no tiene las columnas {faltan}.")
        return [
            dict(zip(cabeza, valores, strict=False))
            for valores in filas
            if any(v not in (None, "") for v in valores)
        ]
    finally:
        libro.close()


def leer_marcas(ruta: Path) -> tuple[dict[int, str], int]:
    """Las marcas por N° (pendiente = "") y cuántos errores anotó el evaluador como escapados."""
    marcas = {
        int(f["N°"]): _marca(f["Veredicto"])
        for f in _filas_de_hoja(Path(ruta), "Hallazgos", ENCABEZADO_HALLAZGOS)
    }
    escapados = len(_filas_de_hoja(Path(ruta), "Se le escaparon", ENCABEZADO_ESCAPADOS))
    return marcas, escapados


def leer_filas(ruta: Path) -> list[FilaPlanilla]:
    """Los hallazgos tal como quedaron en la planilla (para la detección y para comparar dos)."""
    return [
        FilaPlanilla(
            numero=int(f["N°"]),
            regla=str(f["Regla"] or ""),
            severidad=str(f["Severidad"] or ""),
            celdas=tuple(c for c in str(f["Celdas"] or "").split(SEPARADOR_CELDAS) if c),
            descripcion=str(f["Descripción"] or ""),
            ocurrencias=int(f["Ocurrencias"] or 1),
        )
        for f in _filas_de_hoja(Path(ruta), "Hallazgos", ENCABEZADO_HALLAZGOS)
    ]


def leer_clave(ruta: Path) -> list[Sembrado]:
    sembrados = []
    for f in _filas_de_hoja(Path(ruta), "Sembrados", ENCABEZADO_CLAVE):
        detectado = f["Detectado por hallazgo N°"]
        sembrados.append(Sembrado(
            numero=int(f["N°"]),
            celda=str(f["Celda"] or ""),
            tipo=str(f["Tipo de error"] or ""),
            detectado_por=int(detectado) if detectado not in (None, "") else None,
        ))
    return sembrados


# --- línea de comandos ---------------------------------------------------------------------------


def fecha_iso(texto: str) -> date:
    return date.fromisoformat(texto)


def _exportar(args: argparse.Namespace) -> int:
    from fusion.proceso import procesar_libro

    origen = Path(args.libro)
    datos = origen.read_bytes()
    resultado = procesar_libro(datos, origen.name, fecha_devolucion=args.fecha or date.today(),
                               perfil=args.perfil)
    hallazgos = resultado.informe.hallazgos
    filas = filas_de_hallazgos(hallazgos) if args.sin_agrupar else causas_de_hallazgos(hallazgos)
    destino = escribir_planilla(
        filas, Path(args.salida), raiz_repo=Path(args.raiz_repo),
        origen={"SHA-256 del libro auditado": hashlib.sha256(datos).hexdigest(),
                "Hallazgos exportados": str(len(filas)),
                "Reglas que no aplicaron a este libro (no se marcan)":
                    ", ".join(reglas_no_aplicables(resultado.informe.hallazgos)) or "ninguna"},
    )
    print(f"Planilla con {len(filas)} hallazgos: {destino}")
    return 0


def _clave(args: argparse.Namespace) -> int:
    destino = escribir_clave_vacia(Path(args.salida), raiz_repo=Path(args.raiz_repo))
    print(f"Clave de la siembra, vacía: {destino}")
    return 0


def _calcular(args: argparse.Namespace) -> int:
    marcas, escapados = leer_marcas(Path(args.planilla))
    p = precision(marcas)
    det = None
    if args.clave:
        det = deteccion(leer_clave(Path(args.clave)), leer_filas(Path(args.planilla)))
    kappa = None
    los_dos = None
    if args.otra:
        mias, otras = leer_filas(Path(args.planilla)), leer_filas(Path(args.otra))
        if [(f.numero, f.regla, f.celdas) for f in mias] != \
                [(f.numero, f.regla, f.celdas) for f in otras]:
            raise ValueError("Las dos planillas no traen los mismos hallazgos: no son comparables.")
        otras_marcas, _ = leer_marcas(Path(args.otra))
        comunes = sorted(n for n in marcas if marcas[n] and otras_marcas.get(n))
        los_dos = len(comunes)
        if comunes:
            kappa = kappa_cohen([marcas[n] for n in comunes], [otras_marcas[n] for n in comunes])
    filas = leer_filas(Path(args.planilla))
    agrupacion = (sum(f.ocurrencias for f in filas), len(filas))
    print(resumen(precision=p, deteccion=det, exhaustividad=exhaustividad(p.aciertos, escapados),
                  kappa=kappa, marcados_por_los_dos=los_dos, agrupacion=agrupacion))
    return 0


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = analizador.add_subparsers(dest="orden", required=True)

    e = sub.add_parser("exportar", help="audita un libro y escribe la planilla para marcar")
    e.add_argument("libro")
    e.add_argument("--salida", required=True)
    e.add_argument("--fecha", type=fecha_iso, default=None, help="AAAA-MM-DD (por omisión, hoy)")
    e.add_argument("--perfil", default=None)
    e.add_argument("--sin-agrupar", action="store_true",
                   help="un hallazgo por fila en vez de una causa raíz por fila")
    e.add_argument("--raiz-repo", default=str(RAIZ))
    e.set_defaults(funcion=_exportar)

    c = sub.add_parser("clave", help="escribe la clave de la siembra, vacía")
    c.add_argument("--salida", required=True)
    c.add_argument("--raiz-repo", default=str(RAIZ))
    c.set_defaults(funcion=_clave)

    k = sub.add_parser("calcular", help="calcula las medidas desde las planillas marcadas")
    k.add_argument("--planilla", required=True)
    k.add_argument("--otra", default=None, help="la planilla del segundo evaluador (kappa)")
    k.add_argument("--clave", default=None, help="la clave de la siembra (detección)")
    k.set_defaults(funcion=_calcular)

    args = analizador.parse_args(argv)
    return args.funcion(args)


if __name__ == "__main__":
    raise SystemExit(main())
