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
3. Cada evaluador marca su copia por separado, sin ver la clave. `revision`: la planilla de la
   revisión ciega por partida del experto (`scripts/medir_partidas.py`).
4. `calcular`: precisión (Verdadero / marcados), detección de lo sembrado sin acreditar los
   hallazgos que el libro base ya tenía (`--libro` y `--libro-base`), exhaustividad aproximada
   (Verdadero / (Verdadero + escapados)), el kappa experto–Sílice por partida
   (`--revision-experto`, decide el criterio de fracaso) y, con dos planillas, el kappa entre
   evaluadores (fiabilidad entre personas, no decide nada).

    uv run python scripts/medir_auditoria_libro.py clave --salida D:/medicion/clave.xlsx
    uv run python scripts/medir_auditoria_libro.py exportar COPIA.xlsx --salida D:/medicion/p1.xlsx
    uv run python scripts/medir_auditoria_libro.py revision COPIA.xlsx --salida D:/medicion/rev.xlsx
    uv run python scripts/medir_auditoria_libro.py calcular --planilla p1.xlsx --otra p2.xlsx \\
        --clave clave.xlsx --libro COPIA.xlsx --libro-base LIBRO.xlsx --revision-experto rev.xlsx
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import Counter
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from aplicacion.causas_raiz import agrupar, es_no_aplicable, patron  # noqa: E402, F401
from asistente.experimento.metricas import wilson  # noqa: E402
from core.verification.texto import formatear_decimal  # noqa: E402

if TYPE_CHECKING:
    from scripts.medir_partidas import KappaPartidas

VERDADERO = "Verdadero"
FALSO = "Falso"
MARCAS = {"verdadero": VERDADERO, "falso": FALSO}
SEPARADOR_CELDAS = "; "
ETIQUETA_SHA = "SHA-256 del libro auditado"

ENCABEZADO_HALLAZGOS = (
    "N°",
    "Regla",
    "Severidad",
    "Ocurrencias",
    "Celdas",
    "Descripción",
    "Impacto",
    "Veredicto",
    "Nota del evaluador",
)
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
        filas.append(
            FilaPlanilla(
                numero=numero,
                regla=casos[0].regla,
                severidad=max(casos, key=lambda h: h.severidad).severidad.name,
                celdas=celdas,
                descripcion=casos[0].descripcion,
                impacto=float(sum(impactos)) if impactos else None,
                ocurrencias=len(casos),
            )
        )
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
    return Medida(
        aciertos=marcadas.count(VERDADERO),
        total=len(marcadas),
        pendientes=len(normales) - len(marcadas),
    )


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
    """`detectados` = señalados por Sílice. `confirmados` y `marcados_falsos` cuentan, de esos, los
    que el evaluador marcó «Verdadero» o «Falso» (`None` si no se dieron las marcas)."""

    por_sembrado: dict[int, int | None] = field(default_factory=dict)
    manuales: int = 0
    confirmados: int | None = None
    marcados_falsos: int | None = None

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
    """La celda normalizada para compararla: sin `$`, en minúsculas y con la hoja sin comillas
    simples (`'PLAN DE PAGOS'!B6`; una comilla dentro del nombre va duplicada: `'O''Brien'`)."""
    hoja, signo, coordenada = texto.strip().rpartition("!")
    hoja = hoja.strip()
    if len(hoja) >= 2 and hoja[0] == hoja[-1] == "'":
        hoja = hoja[1:-1].replace("''", "'").strip()
    coordenada = coordenada.strip().replace("$", "")
    return f"{hoja}{signo}{coordenada}".casefold()


def deteccion(
    sembrados: Sequence[Sembrado],
    filas: Sequence[FilaPlanilla],
    marcas: Mapping[int, object] | None = None,
    con_nuevos: Collection[int] | None = None,
) -> Deteccion:
    """Qué error sembrado señaló Sílice. Manda la columna «Detectado por hallazgo N°» de la clave
    (la llena quien sembró, porque un error en un APU puede aparecer en otra celda); si está
    vacía, cuenta como detectado el primer hallazgo que apunta a la misma celda. Con `marcas`
    (veredicto del evaluador por N° de hallazgo) cuenta aparte los señalados que el evaluador
    confirmó «Verdadero» y los que marcó «Falso». Con `con_nuevos` (los N° de las filas que traen
    algún hallazgo que el libro base no tenía), la columna manual no puede señalar una fila que
    solo trae hallazgos previos: se rechaza para que quien sembró corrija la clave."""
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
            if con_nuevos is not None and s.detectado_por not in con_nuevos:
                raise ValueError(
                    f"El sembrado {s.numero} dice que lo detectó el hallazgo {s.detectado_por}, "
                    "y esa fila solo trae hallazgos que el libro base ya tenía: corrija la clave "
                    "(deje la columna vacía si ningún hallazgo nuevo lo señala)."
                )
            por[s.numero] = s.detectado_por
            manuales += 1
            continue
        objetivo = _celda(s.celda)
        citan = [f.numero for f in filas if any(_celda(c) == objetivo for c in f.celdas)]
        verdaderas = [n for n in citan if marcas is not None and _marca(marcas.get(n)) == VERDADERO]
        por[s.numero] = (verdaderas or citan or [None])[0]
    if marcas is None:
        return Deteccion(por_sembrado=por, manuales=manuales)
    veredictos = [_marca(marcas.get(n)) for n in por.values() if n is not None]
    return Deteccion(
        por_sembrado=por,
        manuales=manuales,
        confirmados=veredictos.count(VERDADERO),
        marcados_falsos=veredictos.count(FALSO),
    )


def kappa_exacto(a: Sequence[str], b: Sequence[str]) -> Fraction | None:
    """Kappa de Cohen (1960) exacto, con fracciones: así `κ = 0,4` no cae por debajo del umbral por
    un error de redondeo del `float`. `None` si el acuerdo esperado por azar es 1."""
    if len(a) != len(b):
        raise ValueError("Las dos listas de marcas deben tener el mismo largo.")
    if not a:
        raise ValueError("No hay casos marcados por los dos evaluadores.")
    n = len(a)
    observado = Fraction(sum(1 for x, y in zip(a, b, strict=True) if x == y), n)
    ca, cb = Counter(a), Counter(b)
    esperado = Fraction(sum(ca[k] * cb[k] for k in ca.keys() | cb.keys()), n * n)
    if esperado == 1:
        return None
    return (observado - esperado) / (1 - esperado)


def kappa_cohen(a: Sequence[str], b: Sequence[str]) -> float | None:
    """`kappa_exacto` como `float` (para mostrarlo). `None` si no se puede calcular."""
    exacto = kappa_exacto(a, b)
    return None if exacto is None else float(exacto)


# --- formato -------------------------------------------------------------------------------------


def decimal_coma(valor: float, decimales: int = 2) -> str:
    """Coma decimal con redondeo HALF_UP sobre `Decimal` (NORMAS §2.3), no sobre el `float`."""
    return formatear_decimal(Decimal(repr(float(valor))), decimales).replace(".", ",")


def porcentaje(valor: float | None) -> str:
    """Porcentaje con una cifra: pasa a `Decimal` ANTES de multiplicar por 100 (en `float`,
    0,0725 * 100 da 7,2499... y se redondearía mal)."""
    if valor is None:
        return "sin dato"
    centesimos = Decimal(repr(float(valor))) * 100
    return formatear_decimal(centesimos, 1).replace(".", ",") + " %"


def porcentaje_de(aciertos: int, total: int) -> str:
    """`aciertos` sobre `total` como porcentaje HALF_UP, calculado en enteros y `Decimal`."""
    if total == 0:
        return "sin dato"
    valor = Decimal(aciertos) * 100 / Decimal(total)
    return formatear_decimal(valor, 1).replace(".", ",") + " %"


def intervalo_wilson(aciertos: int, total: int) -> str:
    """El intervalo de Wilson al 95 % de `aciertos` sobre `total`, como «[31,4 %; 68,6 %]»."""
    if total == 0:
        return "sin dato"
    bajo, alto = wilson(aciertos, total)
    return f"[{porcentaje(bajo)}; {porcentaje(alto)}]"


NOTA_CIFRA_OFICIAL = (
    "La cifra oficial de detección es la de todas las fallas a la vez (acta del 2026-11-25); "
    "la de una por vez es secundaria y no decide el fracaso."
)


def _estado(se_cumple: bool | None) -> str:
    if se_cumple is None:
        return "no se puede calcular con los datos de esta corrida"
    return "SE CUMPLE" if se_cumple else "NO se cumple"


BASE_SENALADO = "señalado por Sílice"
BASE_CONFIRMADO = "confirmado verdadero por el evaluador"


def _kappa_menor_que_dos_quintos(kappa: float | Fraction) -> bool:
    exacto = (
        kappa if isinstance(kappa, Fraction) else Fraction(repr(kappa)).limit_denominator(10**9)
    )
    return exacto < Fraction(2, 5)


def criterio_de_fracaso(
    *,
    deteccion: tuple[int, int] | None = None,
    falsos: tuple[int, int] | None = None,
    kappa_experto: float | Fraction | None = None,
    base_deteccion: str = BASE_SENALADO,
) -> list[str]:
    """Evalúa el criterio de fracaso sellado (plan no circular): detección < 50 %, falsos positivos
    > 40 % por causa, kappa experto–Sílice < 0,4. `deteccion` y `falsos` son (casos, total); lo
    que no se puede calcular con los datos de la corrida se dice. Compara con enteros y fracciones,
    sin redondear. `base_deteccion` dice qué se contó: con marcas del evaluador, solo lo confirmado
    verdadero (decisión de Eugenio, 2026-11-25); sin marcas, lo señalado por Sílice.
    `kappa_experto` es el kappa por partida entre el experto y Sílice (acta del 2026-11-25,
    punto 1), nunca el de dos evaluadores, que mide la fiabilidad entre personas."""
    detecta = None if not deteccion or not deteccion[1] else deteccion[0] * 2 < deteccion[1]
    falsea = None if not falsos or not falsos[1] else falsos[0] * 5 > falsos[1] * 2
    return [
        f"Detección < 50 % ({base_deteccion}): {_estado(detecta)}",
        f"Falsos positivos > 40 %: {_estado(falsea)}",
        "Kappa experto–Sílice < 0,4: "
        + _estado(None if kappa_experto is None else _kappa_menor_que_dos_quintos(kappa_experto)),
        NOTA_CIFRA_OFICIAL,
    ]


def _cuenta_de_deteccion(d: Deteccion | None) -> tuple[int, int] | None:
    """(casos, total) que decide el criterio: lo confirmado verdadero si hay marcas del evaluador;
    si no, lo señalado por Sílice."""
    if d is None:
        return None
    return (d.detectados if d.confirmados is None else d.confirmados, d.total)


def resumen(
    *,
    precision: Medida,
    deteccion: Deteccion | None,
    exhaustividad: Medida,
    kappa: float | Fraction | None,
    marcados_por_los_dos: int | None = None,
    agrupacion: tuple[int, int] | None = None,
    experto: KappaPartidas | None = None,
    previos: int | None = None,
) -> str:
    """Las cifras agregadas para la tesis: sin celdas, sin descripciones, sin nombres. `kappa` es
    el de dos evaluadores (fiabilidad entre personas); `experto`, el kappa por partida entre el
    experto y Sílice, el único que decide el criterio; `previos`, los hallazgos del libro base
    descontados de la detección."""
    falsos = precision.total - precision.aciertos
    lineas = [
        "| Medida | Cuentas | Valor | Intervalo de Wilson 95 % |",
        "|---|---|---|---|",
        f"| Precisión (verdaderos / marcados) | {precision.aciertos} de {precision.total} "
        f"({precision.pendientes} pendientes) | {porcentaje(precision.valor)} | "
        f"{intervalo_wilson(precision.aciertos, precision.total)} |",
        f"| Falsos positivos (falsos / marcados) | {falsos} de {precision.total} | "
        f"{porcentaje_de(falsos, precision.total)} | "
        f"{intervalo_wilson(falsos, precision.total)} |",
    ]
    if deteccion is not None:
        lineas.append(
            f"| Detección de errores sembrados (señalado por Sílice) | {deteccion.detectados} de "
            f"{deteccion.total} ({deteccion.manuales} por la columna manual) | "
            f"{porcentaje_de(deteccion.detectados, deteccion.total)} | "
            f"{intervalo_wilson(deteccion.detectados, deteccion.total)} |"
        )
        if deteccion.confirmados is not None:
            lineas.append(
                f"| Detección, señalado y confirmado verdadero | {deteccion.confirmados} de "
                f"{deteccion.total} ({deteccion.marcados_falsos} señalados marcados Falso) | "
                f"{porcentaje_de(deteccion.confirmados, deteccion.total)} | "
                f"{intervalo_wilson(deteccion.confirmados, deteccion.total)} |"
            )
    lineas.append(
        f"| Exhaustividad aproximada (con «se le escapó») | {exhaustividad.aciertos} de "
        f"{exhaustividad.total} | {porcentaje(exhaustividad.valor)} | — |"
    )
    texto_kappa = (
        "sin dato (hace falta una segunda planilla con variación)"
        if kappa is None
        else decimal_coma(float(kappa))
    )
    lineas.append(
        "| Kappa de Cohen entre los dos evaluadores (fiabilidad entre personas; no decide el "
        f"fracaso) | — | {texto_kappa} | — |"
    )
    if experto is not None:
        lineas.append(
            f"| Kappa de Cohen experto–Sílice por partida (decide el criterio) | "
            f"{experto.revisadas} partidas revisadas: ambos Sí {experto.ambos_si}, solo el experto "
            f"{experto.solo_experto}, solo Sílice {experto.solo_silice}, ambos No "
            f"{experto.ambos_no} ({experto.pendientes} pendientes) | "
            + (
                "sin dato (sin variación)"
                if experto.kappa is None
                else decimal_coma(float(experto.kappa))
            )
            + " | — |"
        )
    if previos is not None:
        lineas += ["", f"Hallazgos previos del libro descontados: {previos}"]
    if experto is not None:
        lineas += [
            "",
            "Filas de la planilla sin partida (no entran en el kappa): "
            f"{experto.filas_sin_partida}",
        ]
    if agrupacion is not None and agrupacion[1]:
        hallazgos, causas = agrupacion
        lineas += [
            "",
            f"{hallazgos} hallazgos agrupados en {causas} causas "
            f"({decimal_coma(hallazgos / causas, 1)} por causa).",
        ]
    if marcados_por_los_dos is not None:
        lineas += ["", f"Hallazgos marcados por los dos: {marcados_por_los_dos}"]
    lineas += ["", "Criterio de fracaso sellado:"]
    lineas += [
        f"- {t}"
        for t in criterio_de_fracaso(
            deteccion=_cuenta_de_deteccion(deteccion),
            falsos=(falsos, precision.total),
            kappa_experto=None if experto is None else experto.kappa,
            base_deteccion=BASE_SENALADO
            if deteccion is None or deteccion.confirmados is None
            else BASE_CONFIRMADO,
        )
    ]
    return "\n".join(lineas)


# --- disco ---------------------------------------------------------------------------------------


def _checkout_principal(raiz_repo: Path) -> Path | None:
    """La raíz del checkout principal si `raiz_repo` es un worktree (su `.git` es un archivo
    «gitdir: <principal>/.git/worktrees/<nombre>»); `None` si no lo es."""
    marca = raiz_repo / ".git"
    if not marca.is_file():
        return None
    try:
        primera = marca.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError, UnicodeDecodeError):
        return None
    if not primera.startswith("gitdir:"):
        return None
    administrativo = Path(primera.removeprefix("gitdir:").strip())
    if not administrativo.is_absolute():
        administrativo = raiz_repo / administrativo
    comun = administrativo.resolve().parent.parent  # <principal>/.git
    return comun.parent if comun.name == ".git" else None


def _destino_seguro(destino: Path, raiz_repo: Path) -> Path:
    destino = destino.resolve()
    raiz_repo = raiz_repo.resolve()
    prohibidas = [raiz_repo]
    if (principal := _checkout_principal(raiz_repo)) is not None:
        prohibidas.append(principal)
    ajeno = any((carpeta / ".git").exists() for carpeta in (destino, *destino.parents))
    if ajeno or any(destino.is_relative_to(r) for r in prohibidas):
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


def escribir_planilla(
    filas: Sequence[FilaPlanilla],
    destino: Path,
    *,
    raiz_repo: Path = RAIZ,
    origen: Mapping[str, str] | None = None,
) -> Path:
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
        for col, valor in (
            (2, f.regla),
            (3, f.severidad),
            (5, SEPARADOR_CELDAS.join(f.celdas)),
            (6, f.descripcion),
        ):
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
        sembrados.append(
            Sembrado(
                numero=int(f["N°"]),
                celda=str(f["Celda"] or ""),
                tipo=str(f["Tipo de error"] or ""),
                detectado_por=int(detectado) if detectado not in (None, "") else None,
            )
        )
    return sembrados


# --- línea de comandos ---------------------------------------------------------------------------


def fecha_iso(texto: str) -> date:
    return date.fromisoformat(texto)


def _auditar(ruta: Path, args: argparse.Namespace, recalculador=None) -> tuple[bytes, object]:
    """Los bytes del libro y su `ResultadoFusion`: el mismo proceso de la pantalla
    (`procesar_libro`); con `--recalcular`, sobre los valores de LibreOffice trasplantados."""
    from fusion.proceso import procesar_libro

    datos = ruta.read_bytes()
    auditado = datos
    if args.recalcular:
        from aplicacion.oraculo_hoja import RecalculadorLibreOffice
        from aplicacion.trasplante_valores import trasplantar

        motor = recalculador or RecalculadorLibreOffice(
            configuracion_regional=args.configuracion_regional
        )
        auditado = trasplantar(datos, motor.recalcular(datos, ruta.name))
    resultado = procesar_libro(
        auditado, ruta.name, fecha_devolucion=args.fecha or date.today(), perfil=args.perfil
    )
    return datos, resultado


def _filas(hallazgos: Sequence, sin_agrupar: bool) -> list[FilaPlanilla]:
    return filas_de_hallazgos(hallazgos) if sin_agrupar else causas_de_hallazgos(hallazgos)


def _exportar(args: argparse.Namespace, recalculador=None) -> int:
    _destino_seguro(Path(args.salida), Path(args.raiz_repo))  # antes de gastar un recálculo
    datos, resultado = _auditar(Path(args.libro), args, recalculador)
    filas = _filas(resultado.informe.hallazgos, args.sin_agrupar)
    destino = escribir_planilla(
        filas,
        Path(args.salida),
        raiz_repo=Path(args.raiz_repo),
        origen={
            ETIQUETA_SHA: hashlib.sha256(datos).hexdigest(),
            "Recalculado con LibreOffice y valores trasplantados": "sí"
            if args.recalcular
            else "no",
            "Hallazgos exportados": str(len(filas)),
            "Reglas que no aplicaron a este libro (no se marcan)": ", ".join(
                reglas_no_aplicables(resultado.informe.hallazgos)
            )
            or "ninguna",
        },
    )
    print(f"Planilla con {len(filas)} hallazgos: {destino}")
    return 0


def _clave(args: argparse.Namespace) -> int:
    destino = escribir_clave_vacia(Path(args.salida), raiz_repo=Path(args.raiz_repo))
    print(f"Clave de la siembra, vacía: {destino}")
    return 0


def _leer_libro(ruta: Path, perfil: str | None):
    from adapters.hoja_empresa.lector import leer_libro
    from adapters.hoja_empresa.perfil import cargar_perfil

    return leer_libro(ruta.read_bytes(), ruta.name, cargar_perfil(perfil) if perfil else None)


def _revision(args: argparse.Namespace) -> int:
    from scripts.medir_partidas import escribir_revision_vacia

    destino = escribir_revision_vacia(
        _leer_libro(Path(args.libro), args.perfil),
        Path(args.salida),
        raiz_repo=Path(args.raiz_repo),
    )
    print(f"Revisión por partida, vacía: {destino}")
    return 0


def _comprobar_libro(planilla: Path, libro: Path) -> None:
    """La planilla se exportó de este libro: lo dice el SHA-256 que `exportar` dejó en ella."""
    import openpyxl

    esperado = f"{ETIQUETA_SHA}: {hashlib.sha256(libro.read_bytes()).hexdigest()}"
    hoja = openpyxl.load_workbook(planilla, read_only=True)
    try:
        lineas = [str(f[0] or "") for f in hoja["Instrucciones"].iter_rows(values_only=True) if f]
    finally:
        hoja.close()
    if esperado not in lineas:
        raise ValueError(
            f"La planilla «{planilla.name}» no es de este libro: su SHA-256 no es el de "
            f"«{libro.name}»."
        )


def _comprobar_reproduce(hallazgos: Sequence, args: argparse.Namespace, planilla) -> None:
    if [(f.numero, f.regla, f.celdas) for f in _filas(hallazgos, args.sin_agrupar)] != [
        (f.numero, f.regla, f.celdas) for f in planilla
    ]:
        raise ValueError(
            f"La auditoría de «{Path(args.libro).name}» no reproduce la planilla: use las mismas "
            "opciones que en exportar (--fecha, --perfil, --recalcular, --sin-agrupar)."
        )


def _filas_sin_previos(
    base: Sequence, hallazgos: Sequence, sin_agrupar: bool
) -> tuple[list[FilaPlanilla], int, set[int]]:
    """Las filas de la planilla con solo las celdas nuevas (`sin_previos`), cuántos hallazgos
    previos se descontaron y qué filas traen algo nuevo."""
    from scripts.hallazgos_previos import filas_con_nuevos, sin_previos

    recortados, previos, nuevos = sin_previos(base, hallazgos)
    return (
        _filas(recortados, sin_agrupar),
        previos,
        filas_con_nuevos(hallazgos, nuevos, sin_agrupar=sin_agrupar),
    )


def _calcular(args: argparse.Namespace, recalculador=None) -> int:
    from scripts.medir_partidas import (
        clasificar,
        comprobar_revision,
        kappa_por_partida,
        leer_revision,
    )

    marcas, escapados = leer_marcas(Path(args.planilla))
    filas = leer_filas(Path(args.planilla))
    auditado = None
    if args.libro:
        _comprobar_libro(Path(args.planilla), Path(args.libro))
        # El mismo libro auditado que en exportar (con --recalcular, el trasplantado).
        _, auditado = _auditar(Path(args.libro), args, recalculador)
        _comprobar_reproduce(auditado.informe.hallazgos, args, filas)
    p = precision(marcas)
    det = previos = None
    if args.clave:
        _, base = _auditar(Path(args.libro_base), args, recalculador)
        filas_det, previos, con_nuevos = _filas_sin_previos(
            base.informe.hallazgos, auditado.informe.hallazgos, args.sin_agrupar
        )
        det = deteccion(
            leer_clave(Path(args.clave)), filas_det, marcas=marcas, con_nuevos=con_nuevos
        )
    experto = None
    if args.revision_experto:
        comprobar_revision(Path(args.revision_experto), Path(args.libro).read_bytes())
        experto = kappa_por_partida(
            leer_revision(Path(args.revision_experto)), clasificar(filas, auditado.libro)
        )
    kappa = None
    los_dos = None
    if args.otra:
        otras = leer_filas(Path(args.otra))
        if [(f.numero, f.regla, f.celdas) for f in filas] != [
            (f.numero, f.regla, f.celdas) for f in otras
        ]:
            raise ValueError("Las dos planillas no traen los mismos hallazgos: no son comparables.")
        otras_marcas, _ = leer_marcas(Path(args.otra))
        comunes = sorted(n for n in marcas if marcas[n] and otras_marcas.get(n))
        los_dos = len(comunes)
        if comunes:
            kappa = kappa_exacto([marcas[n] for n in comunes], [otras_marcas[n] for n in comunes])
    print(
        resumen(
            precision=p,
            deteccion=det,
            exhaustividad=exhaustividad(p.aciertos, escapados),
            kappa=kappa,
            marcados_por_los_dos=los_dos,
            agrupacion=(sum(f.ocurrencias for f in filas), len(filas)),
            experto=experto,
            previos=previos,
        )
    )
    return 0


def _opciones_de_auditoria(analizador: argparse.ArgumentParser) -> None:
    """Las opciones con que se audita un libro: `calcular` debe repetir las de `exportar`."""
    analizador.add_argument(
        "--fecha", type=fecha_iso, default=None, help="AAAA-MM-DD (por omisión, hoy)"
    )
    analizador.add_argument("--perfil", default=None)
    analizador.add_argument(
        "--sin-agrupar",
        action="store_true",
        help="un hallazgo por fila en vez de una causa raíz por fila",
    )
    analizador.add_argument(
        "--recalcular",
        action="store_true",
        help="recalcula el libro con LibreOffice y trasplanta los valores antes de "
        "auditarlo (un libro sembrado no trae valores guardados al día)",
    )
    analizador.add_argument("--configuracion-regional", default="es-VE")


def main(argv: list[str] | None = None, *, recalculador=None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = analizador.add_subparsers(dest="orden", required=True)

    e = sub.add_parser("exportar", help="audita un libro y escribe la planilla para marcar")
    e.add_argument("libro")
    e.add_argument("--salida", required=True)
    _opciones_de_auditoria(e)
    e.add_argument("--raiz-repo", default=str(RAIZ))
    e.set_defaults(funcion=_exportar)

    c = sub.add_parser("clave", help="escribe la clave de la siembra, vacía")
    c.add_argument("--salida", required=True)
    c.add_argument("--raiz-repo", default=str(RAIZ))
    c.set_defaults(funcion=_clave)

    r = sub.add_parser("revision", help="escribe la revisión ciega por partida, vacía")
    r.add_argument("libro")
    r.add_argument("--salida", required=True)
    r.add_argument("--perfil", default=None)
    r.add_argument("--raiz-repo", default=str(RAIZ))
    r.set_defaults(funcion=_revision)

    k = sub.add_parser("calcular", help="calcula las medidas desde las planillas marcadas")
    k.add_argument("--planilla", required=True)
    k.add_argument(
        "--otra", default=None, help="la planilla del segundo evaluador (fiabilidad entre personas)"
    )
    k.add_argument(
        "--clave",
        default=None,
        help="la clave de la siembra (detección); exige --libro y --libro-base",
    )
    k.add_argument("--libro", default=None, help="el libro del que se exportó la planilla")
    k.add_argument(
        "--libro-base",
        default=None,
        help="el libro sin sembrar: sus hallazgos no se acreditan a las fallas sembradas",
    )
    k.add_argument(
        "--revision-experto",
        default=None,
        help="la revisión ciega del experto por partida (.xlsx o .csv); exige --libro",
    )
    _opciones_de_auditoria(k)
    k.set_defaults(funcion=_calcular)

    args = analizador.parse_args(argv)
    if args.funcion is _calcular:
        if args.clave and not (args.libro and args.libro_base):
            k.error("--clave exige --libro y --libro-base (para descontar los hallazgos previos)")
        if args.libro_base and not args.clave:
            k.error("--libro-base solo sirve con --clave")
        if args.revision_experto and not args.libro:
            k.error("--revision-experto exige --libro (para ubicar las partidas)")
    from aplicacion.oraculo_hoja import LibreOfficeNoDisponibleError

    try:
        if args.funcion not in (_exportar, _calcular):
            return args.funcion(args)
        return args.funcion(args, recalculador)
    # Negarse a sobrescribir una planilla es un aviso para la persona, no una traza de Python
    # (auditoría antes de medicion-v1, #11).
    except (FileExistsError, LibreOfficeNoDisponibleError) as error:
        print(error)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
