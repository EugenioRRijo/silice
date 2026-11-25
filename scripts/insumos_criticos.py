"""Mide el peso aproximado de los insumos (ABC) y la frescura de sus precios en un libro.

Herramienta LOCAL del plan del consejo (2026-11-24): lee un libro real en el equipo, calcula
el peso aproximado por código, clasifica en ABC, extrae la fecha de la columna FUENTE y escribe
el informe JSON FUERA del repositorio (NORMAS §1). La salida en pantalla usa coma decimal, solo
caracteres cp1252 y solo códigos (sin descripciones ni datos identificables de la empresa).

    uv run python scripts/insumos_criticos.py LIBRO.xlsx --salida D:/medicion \
        [--fecha AAAA-MM-DD] [--ventana 90]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from adapters.hoja_empresa.lector import leer_libro  # noqa: E402
from adapters.hoja_empresa.modelo import LibroLeido, TipoInsumo  # noqa: E402
from adapters.hoja_empresa.perfil import cargar_perfil, normalizar  # noqa: E402
from core.verification.texto import formatear_decimal  # noqa: E402
from fusion.alertas import _sin_fuente  # noqa: E402
from fusion.proceso import fecha_del_libro  # noqa: E402
from scripts.medir_auditoria_libro import _destino_seguro  # noqa: E402

CORTE_A_POR_DEFECTO = Decimal("0.80")
CORTE_B_POR_DEFECTO = Decimal("0.95")
VENTANA_POR_DEFECTO = 90

_MESES = {
    "enero": 1,
    "ene": 1,
    "febrero": 2,
    "feb": 2,
    "marzo": 3,
    "mar": 3,
    "abril": 4,
    "abr": 4,
    "mayo": 5,
    "may": 5,
    "junio": 6,
    "jun": 6,
    "julio": 7,
    "jul": 7,
    "agosto": 8,
    "ago": 8,
    "septiembre": 9,
    "setiembre": 9,
    "sept": 9,
    "sep": 9,
    "set": 9,
    "octubre": 10,
    "oct": 10,
    "noviembre": 11,
    "nov": 11,
    "diciembre": 12,
    "dic": 12,
}
_PATRON_MES = "|".join(sorted(_MESES, key=len, reverse=True))
_RE_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_RE_DMY = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
_RE_MES_ANIO = re.compile(rf"\b({_PATRON_MES})\.?(?:\s+(?:de(?:l)?\s+)?|-)(\d{{4}})\b")


@dataclass(frozen=True, slots=True)
class PesoInsumo:
    """Peso aproximado de un insumo en el presupuesto (sin FCAS ni herramientas)."""

    codigo: str
    descripcion: str
    tipo: TipoInsumo
    peso: Decimal
    sin_rendimiento: int = 0


@dataclass(frozen=True, slots=True)
class InsumoAbc:
    """Clasificación ABC de un insumo según su peso aproximado."""

    codigo: str
    descripcion: str
    tipo: TipoInsumo
    peso: Decimal
    porcentaje: Decimal
    acumulado: Decimal
    clase: str
    sin_rendimiento: int = 0


@dataclass(frozen=True, slots=True)
class InsumoEvaluado:
    """Insumo clasificado en ABC junto con la frescura de su fuente de precio."""

    codigo: str
    descripcion: str
    tipo: TipoInsumo
    peso: Decimal
    porcentaje: Decimal
    acumulado: Decimal
    clase: str
    fuente: str
    sin_fuente: bool
    fecha: date | None
    edad_dias: int | None
    vigente: str
    sin_rendimiento: int = 0


@dataclass(frozen=True, slots=True)
class IndicadoresCriticos:
    """Indicadores agregados sobre los insumos críticos (clase A) y la frescura del libro."""

    total_insumos: int
    insumos_a: int
    a_vigentes: int
    a_sin_fuente: int
    total_sin_fuente: int
    porcentaje_costo_a: Decimal
    sin_rendimiento: int


def _fecha(anio: int, mes: int, dia: int) -> date | None:
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def pesos(libro: LibroLeido) -> list[PesoInsumo]:
    """Calcula el peso aproximado por código de insumo en `libro`, de mayor a menor.

    Es una aproximación para ordenar insumos: multiplica la cantidad de cada partida por el
    aporte unitario de cada línea de su APU (sin FCAS ni herramientas menores). Si el
    rendimiento es 0 en una línea de mano de obra o equipo, esa línea no aporta y se cuenta en
    `sin_rendimiento`.
    """
    totales: dict[str, Decimal] = {}
    sin_rend: dict[str, int] = {}
    meta: dict[str, tuple[str, TipoInsumo]] = {}
    for partida in libro.partidas:
        if partida.hoja_apu is None:
            continue
        apu = libro.apu(partida.hoja_apu)
        if apu is None:
            continue
        for linea in apu.lineas:
            ins = libro.insumo(linea.codigo)
            if linea.codigo not in meta:
                desc = ins.descripcion if ins is not None else linea.descripcion
                tipo = ins.tipo if ins is not None else linea.tipo
                meta[linea.codigo] = (desc, tipo)
                totales[linea.codigo] = Decimal(0)
                sin_rend[linea.codigo] = 0
            if linea.tipo == TipoInsumo.MATERIAL:
                aporte = linea.cantidad * linea.precio
            elif apu.rendimiento == 0:
                sin_rend[linea.codigo] += 1
                continue
            else:
                aporte = linea.cantidad * linea.precio / apu.rendimiento
            totales[linea.codigo] += partida.cantidad * aporte
    salida = [
        PesoInsumo(
            codigo=cod,
            descripcion=desc,
            tipo=tipo,
            peso=totales[cod],
            sin_rendimiento=sin_rend[cod],
        )
        for cod, (desc, tipo) in meta.items()
    ]
    return sorted(salida, key=lambda p: (-p.peso, p.codigo))


def abc(
    pesos_insumos: Sequence[PesoInsumo],
    corte_a: Decimal = CORTE_A_POR_DEFECTO,
    corte_b: Decimal = CORTE_B_POR_DEFECTO,
) -> list[InsumoAbc]:
    """Clasifica los insumos en A, B o C tras ordenarlos de mayor a menor peso.

    Los cortes (`corte_a=0,80` y `corte_b=0,95`) son supuestos por confirmar con Eugenio
    (convención habitual de inventarios): A mientras el acumulado previo sea menor que `corte_a`
    (la frontera exacta de 80 % queda en A), B hasta `corte_b` y C el resto.
    """
    ordenados = sorted(pesos_insumos, key=lambda p: (-p.peso, p.codigo))
    total = sum((p.peso for p in ordenados), Decimal(0))
    acum_peso = Decimal(0)
    salida: list[InsumoAbc] = []
    cien = Decimal(100)
    for p in ordenados:
        if total <= 0:
            frac = Decimal(0)
            acum_frac = Decimal(0)
            clase = "C"
        else:
            prev_frac = acum_peso / total
            frac = p.peso / total
            acum_peso += p.peso
            acum_frac = acum_peso / total
            if p.peso <= 0:
                clase = "C"
            elif prev_frac < corte_a:
                clase = "A"
            elif prev_frac < corte_b:
                clase = "B"
            else:
                clase = "C"
        salida.append(
            InsumoAbc(
                codigo=p.codigo,
                descripcion=p.descripcion,
                tipo=p.tipo,
                peso=p.peso,
                porcentaje=frac * cien,
                acumulado=acum_frac * cien,
                clase=clase,
                sin_rendimiento=p.sin_rendimiento,
            )
        )
    return salida


def fecha_de_fuente(texto: str) -> date | None:
    """Extrae una fecha de la columna FUENTE o devuelve `None` si no hay fecha válida.

    Acepta `dd/mm/aaaa`, `dd-mm-aaaa`, `aaaa-mm-dd` y mes en español con año (`julio 2026`,
    `jul-2026`, `Julio de 2026`), que vale como día 1 del mes.
    """
    limpio = normalizar(texto)
    if not limpio:
        return None
    if m := _RE_ISO.search(limpio):
        return _fecha(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if m := _RE_DMY.search(limpio):
        return _fecha(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    if m := _RE_MES_ANIO.search(limpio):
        return _fecha(int(m.group(2)), _MESES[m.group(1)], 1)
    return None


def evaluar_insumos(
    libro: LibroLeido,
    *,
    fecha: date | None = None,
    ventana: int = VENTANA_POR_DEFECTO,
    corte_a: Decimal = CORTE_A_POR_DEFECTO,
    corte_b: Decimal = CORTE_B_POR_DEFECTO,
) -> tuple[date | None, list[InsumoEvaluado], IndicadoresCriticos]:
    """Calcula pesos, clasificación ABC, frescura de precios e indicadores de `libro`."""
    if ventana < 0:
        raise ValueError("La ventana en días no puede ser negativa.")
    fecha_libro = fecha if fecha is not None else fecha_del_libro(libro)
    clasificados = abc(pesos(libro), corte_a=corte_a, corte_b=corte_b)
    evaluados: list[InsumoEvaluado] = []
    for item in clasificados:
        ins = libro.insumo(item.codigo)
        fuente = ins.fuente if ins is not None else ""
        sin_f = _sin_fuente(fuente)
        fecha_f = None if sin_f else fecha_de_fuente(fuente)
        if fecha_f is not None and fecha_libro is not None:
            edad: int | None = (fecha_libro - fecha_f).days
            vigente = "sí" if 0 <= edad <= ventana else "no"
        else:
            edad = None
            vigente = "sin_dato"
        evaluados.append(
            InsumoEvaluado(
                codigo=item.codigo,
                descripcion=item.descripcion,
                tipo=item.tipo,
                peso=item.peso,
                porcentaje=item.porcentaje,
                acumulado=item.acumulado,
                clase=item.clase,
                fuente=fuente,
                sin_fuente=sin_f,
                fecha=fecha_f,
                edad_dias=edad,
                vigente=vigente,
                sin_rendimiento=item.sin_rendimiento,
            )
        )
    total_peso = sum((x.peso for x in evaluados), Decimal(0))
    a_items = [x for x in evaluados if x.clase == "A"]
    peso_a = sum((x.peso for x in a_items), Decimal(0))
    pct_a = (peso_a / total_peso * Decimal(100)) if total_peso > 0 else Decimal(0)
    indicadores = IndicadoresCriticos(
        total_insumos=len(evaluados),
        insumos_a=len(a_items),
        a_vigentes=sum(1 for x in a_items if x.vigente == "sí"),
        a_sin_fuente=sum(1 for x in a_items if x.sin_fuente),
        total_sin_fuente=sum(1 for x in evaluados if x.sin_fuente),
        porcentaje_costo_a=pct_a,
        sin_rendimiento=sum(x.sin_rendimiento for x in evaluados),
    )
    return fecha_libro, evaluados, indicadores


def _decimal_coma(valor: Decimal, decimales: int = 2) -> str:
    return formatear_decimal(valor, decimales).replace(".", ",")


def resumen_pantalla(
    evaluados: Sequence[InsumoEvaluado],
    indicadores: IndicadoresCriticos,
    *,
    fecha_libro: date | None,
    ventana: int,
    destino: Path,
) -> str:
    """Resumen en español con coma decimal, solo en cp1252 y solo con códigos."""
    fecha_txt = fecha_libro.isoformat() if fecha_libro is not None else "sin fecha"
    pct_a = _decimal_coma(indicadores.porcentaje_costo_a, 1)
    lineas = [
        f"Insumos críticos (ABC): {indicadores.insumos_a} A de {indicadores.total_insumos} "
        f"insumos ({pct_a} % del costo aproximado).",
        f"Frescura al {fecha_txt} (ventana {ventana} d): {indicadores.a_vigentes} A vigentes, "
        f"{indicadores.a_sin_fuente} A sin fuente "
        f"({indicadores.total_sin_fuente} sin fuente en total).",
        "Supuestos: cortes ABC 80 % / 95 % por confirmar con Eugenio; "
        "peso aproximado sin FCAS ni herramientas.",
    ]
    if indicadores.sin_rendimiento:
        lineas.append(
            "Líneas de mano de obra o equipo omitidas por rendimiento 0: "
            f"{indicadores.sin_rendimiento}."
        )
    criticos = [x for x in evaluados if x.clase == "A"]
    if criticos:
        lineas.append("Insumos A (solo códigos):")
        for item in criticos:
            if item.sin_fuente:
                estado = "sin fuente"
            elif item.vigente == "sí":
                estado = f"vigente ({item.edad_dias} d)"
            elif item.vigente == "no":
                estado = f"vencido ({item.edad_dias} d)"
            else:
                estado = "sin fecha"
            peso_txt = _decimal_coma(item.peso, 2)
            pct_txt = _decimal_coma(item.porcentaje, 1)
            acum_txt = _decimal_coma(item.acumulado, 1)
            lineas.append(
                f"- {item.codigo} ({item.tipo.value}): peso {peso_txt} "
                f"({pct_txt} %, acum. {acum_txt} %), {estado}"
            )
    lineas.append(f"Informe JSON: {destino}")
    return "\n".join(lineas)


def _objetivo_json(salida: Path, origen: Path) -> Path:
    if salida.suffix.lower() == ".json" and not salida.is_dir():
        return salida
    return salida / f"insumos_criticos_{origen.stem}.json"


def ejecutar(
    ruta_libro: Path,
    carpeta_salida: Path,
    *,
    fecha: date | None = None,
    ventana: int = VENTANA_POR_DEFECTO,
    perfil: str | None = None,
    raiz_repo: Path = RAIZ,
) -> tuple[Path, str]:
    """Lee `ruta_libro`, guarda el JSON fuera del repositorio y devuelve `(destino, resumen)`."""
    origen = Path(ruta_libro)
    destino = _destino_seguro(_objetivo_json(Path(carpeta_salida), origen), Path(raiz_repo))
    datos = origen.read_bytes()
    libro = leer_libro(datos, origen.name, perfil=cargar_perfil(perfil) if perfil else None)
    fecha_libro, evaluados, indicadores = evaluar_insumos(libro, fecha=fecha, ventana=ventana)
    carga = {
        "sha256_libro": hashlib.sha256(datos).hexdigest(),
        "fecha_libro": fecha_libro.isoformat() if fecha_libro is not None else None,
        "ventana_dias": ventana,
        "supuestos": {
            "corte_a": format(CORTE_A_POR_DEFECTO, "f"),
            "corte_b": format(CORTE_B_POR_DEFECTO, "f"),
            "nota_cortes": (
                "Cortes ABC (80 % / 95 %) son supuestos por confirmar con Eugenio "
                "(convención habitual de inventarios)."
            ),
            "nota_pesos": (
                "El peso es una aproximación para ordenar insumos "
                "(sin FCAS ni herramientas menores)."
            ),
        },
        "indicadores": {
            "total_insumos": indicadores.total_insumos,
            "insumos_a": indicadores.insumos_a,
            "a_vigentes": indicadores.a_vigentes,
            "a_sin_fuente": indicadores.a_sin_fuente,
            "total_sin_fuente": indicadores.total_sin_fuente,
            "porcentaje_costo_a": format(indicadores.porcentaje_costo_a, "f"),
            "sin_rendimiento": indicadores.sin_rendimiento,
        },
        "insumos": [
            {
                "codigo": x.codigo,
                "descripcion": x.descripcion,
                "tipo": x.tipo.value,
                "peso": format(x.peso, "f"),
                "porcentaje": format(x.porcentaje, "f"),
                "acumulado": format(x.acumulado, "f"),
                "clase": x.clase,
                "fuente": x.fuente,
                "sin_fuente": x.sin_fuente,
                "fecha": x.fecha.isoformat() if x.fecha is not None else None,
                "edad_dias": x.edad_dias,
                "vigente": x.vigente,
                "sin_rendimiento": x.sin_rendimiento,
            }
            for x in evaluados
        ],
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(carga, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    texto = resumen_pantalla(
        evaluados,
        indicadores,
        fecha_libro=fecha_libro,
        ventana=ventana,
        destino=destino,
    )
    return destino, texto


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada de línea de comandos."""
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("libro", help="ruta del libro .xlsx a analizar")
    analizador.add_argument("--salida", required=True, help="carpeta fuera del repositorio")
    analizador.add_argument("--fecha", type=date.fromisoformat, default=None, help="AAAA-MM-DD")
    analizador.add_argument(
        "--ventana",
        type=int,
        default=VENTANA_POR_DEFECTO,
        help="días máximos de antigüedad vigente (por omisión, 90)",
    )
    analizador.add_argument("--perfil", default=None, help="perfil de plantilla")
    analizador.add_argument("--raiz-repo", default=str(RAIZ))
    args = analizador.parse_args(argv)
    _, texto = ejecutar(
        Path(args.libro),
        Path(args.salida),
        fecha=args.fecha,
        ventana=args.ventana,
        perfil=args.perfil,
        raiz_repo=Path(args.raiz_repo),
    )
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
