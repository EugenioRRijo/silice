"""Kappa experto–Sílice por partida (acta de Eugenio del 2026-11-25, punto 1).

Herramienta LOCAL de medición, como `medir_auditoria_libro.py`: nada de lo que lee ni de lo que
escribe entra al repositorio (NORMAS §1).

La unidad es la **partida** del PRESUPUESTO. El experto, en su revisión ciega (línea base humana
del protocolo), dice por cada partida si tiene un error que un presupuestista corregiría. Sílice lo
dice por sus hallazgos: una fila de la planilla cuenta para una partida cuando alguna de sus celdas
está en el renglón de esa partida del PRESUPUESTO o en la hoja APU unida a ella (`partida_de_apu`
del contexto de reglas, que se importa y no se copia). Las filas que no caen en ninguna partida
(RESUMEN, INSUMOS…) se informan aparte y no entran en el kappa. El kappa se calcula sobre todas las
partidas, también las sanas, con `kappa_exacto` (fracciones).
"""

from __future__ import annotations

import csv
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

from adapters.hoja_empresa.modelo import LibroLeido
from adapters.hoja_empresa.perfil import cargar_perfil
from adapters.hoja_empresa.reglas_contexto import _Contexto
from scripts.medir_auditoria_libro import (
    FilaPlanilla,
    _celda,
    _destino_seguro,
    _hoja_con_encabezado,
    _texto,
    kappa_exacto,
)

SI = "Sí"
NO = "No"
RESPUESTAS = {"sí": True, "si": True, "no": False}
HOJA_REVISION = "Revisión por partida"
COLUMNA_PARTIDA = "Partida"
COLUMNA_ERROR = "¿Tiene error?"
ENCABEZADO_REVISION = (COLUMNA_PARTIDA, "Código", "Descripción", COLUMNA_ERROR, "Nota")
INSTRUCCIONES_REVISION = (
    "Revisión ciega por partida (línea base humana). "
    "Esta planilla NO se sube a ningún repositorio.",
    "1. Revise el libro a mano, con su forma habitual de trabajo, sin abrir Sílice y sin ver la "
    "clave de la siembra.",
    "2. En «¿Tiene error?» escriba Sí si la partida (su renglón del PRESUPUESTO o su APU) tiene un "
    "error que usted corregiría; No si está sana. Si no sabe, déjela en blanco: cuenta como "
    "pendiente y no entra en el kappa.",
    "3. No cambie los números de la columna «Partida» ni borre filas.",
)

_RX_FILA = re.compile(r"^[a-z]*(\d+)$")


# --- la revisión del experto ---------------------------------------------------------------------


def _respuesta(texto: object, partida: int) -> bool | None:
    limpio = str(texto or "").strip()
    if not limpio:
        return None
    try:
        return RESPUESTAS[limpio.casefold()]
    except KeyError:
        raise ValueError(
            f"Respuesta desconocida «{limpio}» en la partida {partida}: use {SI} o {NO}."
        ) from None


def _numero_de_partida(valor: object) -> int:
    try:
        numero = Decimal(str(valor).strip())
    except InvalidOperation:
        raise ValueError(f"«{valor}» no es un número de partida.") from None
    if numero != numero.to_integral_value():
        raise ValueError(f"«{valor}» no es un número de partida.")
    return int(numero)


def _filas_csv(ruta: Path) -> list[dict[str, object]]:
    texto = ruta.read_text(encoding="utf-8-sig")
    primera = texto.splitlines()[0] if texto else ""
    lector = csv.DictReader(texto.splitlines(), delimiter=";" if ";" in primera else ",")
    return [{(k or "").strip(): v for k, v in fila.items()} for fila in lector]


def _filas_xlsx(ruta: Path) -> list[dict[str, object]]:
    import openpyxl

    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    try:
        if HOJA_REVISION not in libro.sheetnames:
            raise ValueError(f"«{ruta.name}» no tiene la hoja «{HOJA_REVISION}».")
        filas = libro[HOJA_REVISION].iter_rows(values_only=True)
        cabeza = [str(c or "").strip() for c in next(filas, ())]
        return [dict(zip(cabeza, valores, strict=False)) for valores in filas]
    finally:
        libro.close()


def leer_revision(ruta: Path) -> dict[int, bool | None]:
    """La revisión del experto: por número de partida, `True` (Sí), `False` (No) o `None`
    (pendiente). Acepta la planilla de `revision` (.xlsx) o un CSV con las columnas «Partida» y
    «¿Tiene error?» (separadas por coma o punto y coma)."""
    ruta = Path(ruta)
    filas = _filas_csv(ruta) if ruta.suffix.casefold() == ".csv" else _filas_xlsx(ruta)
    if filas and not {COLUMNA_PARTIDA, COLUMNA_ERROR} <= set(filas[0]):
        raise ValueError(
            f"«{ruta.name}» debe traer las columnas «{COLUMNA_PARTIDA}» y «{COLUMNA_ERROR}»."
        )
    revision: dict[int, bool | None] = {}
    for fila in filas:
        if all(v in (None, "") for v in fila.values()):
            continue
        numero = _numero_de_partida(fila[COLUMNA_PARTIDA])
        if numero in revision:
            raise ValueError(f"La partida {numero} aparece dos veces en la revisión.")
        revision[numero] = _respuesta(fila[COLUMNA_ERROR], numero)
    return revision


def escribir_revision_vacia(libro: LibroLeido, destino: Path, *, raiz_repo: Path) -> Path:
    """La planilla de la revisión ciega: una fila por partida, sin nada de Sílice."""
    import openpyxl
    from openpyxl.worksheet.datavalidation import DataValidation

    destino = _destino_seguro(Path(destino), Path(raiz_repo))
    salida = openpyxl.Workbook()
    instrucciones = salida.active
    instrucciones.title = "Instrucciones"
    for linea in INSTRUCCIONES_REVISION:
        instrucciones.append([linea])
    instrucciones.append([f"SHA-256 del libro revisado: {libro.sha256}"])
    instrucciones.column_dimensions["A"].width = 110
    hoja = _hoja_con_encabezado(salida, HOJA_REVISION, ENCABEZADO_REVISION)
    for p in libro.partidas:
        fila = hoja.max_row + 1
        hoja.cell(row=fila, column=1, value=p.numero)
        _texto(hoja.cell(row=fila, column=2), p.codigo)
        _texto(hoja.cell(row=fila, column=3), p.descripcion)
    lista = DataValidation(type="list", formula1=f'"{SI},{NO}"', allow_blank=True)
    lista.add(f"D2:D{max(hoja.max_row, 2)}")
    hoja.add_data_validation(lista)
    for letra, ancho in zip("ABCDE", (9, 16, 60, 14, 40), strict=True):
        hoja.column_dimensions[letra].width = ancho
    salida.save(destino)
    return destino


# --- la clasificación de Sílice ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClasificacionSilice:
    """`partidas`: los números de todas las partidas del libro; `con_error`: las que Sílice
    señaló; `sin_partida`: N° de las filas de la planilla que no caen en ninguna partida."""

    partidas: tuple[int, ...]
    con_error: frozenset[int]
    sin_partida: tuple[int, ...]


def _filas_del_rango(coordenada: str) -> list[int]:
    extremos = [_RX_FILA.match(parte) for parte in coordenada.split(":")]
    if not extremos or not all(extremos):
        return []
    numeros = [int(e.group(1)) for e in extremos if e is not None]
    return list(range(min(numeros), max(numeros) + 1))


def clasificar(filas: Sequence[FilaPlanilla], libro: LibroLeido) -> ClasificacionSilice:
    """Qué partidas señala Sílice: una fila cuenta para cada partida en cuyo renglón del
    PRESUPUESTO, o en cuya hoja APU, está alguna de sus celdas."""
    ctx = _Contexto(libro, cargar_perfil(libro.perfil))
    presupuesto = ctx.h_pres.casefold()
    por_fila = {fila: p.numero for fila, p in ctx.partida_por_fila.items()}
    por_apu = {hoja.casefold(): p.numero for hoja, p in ctx.partida_de_apu.items()}

    def partidas_de(celda: str) -> set[int]:
        hoja, signo, coordenada = _celda(celda).rpartition("!")
        if not signo:
            return set()
        if hoja == presupuesto:
            return {por_fila[f] for f in _filas_del_rango(coordenada) if f in por_fila}
        return {por_apu[hoja]} if hoja in por_apu else set()

    con_error: set[int] = set()
    sin_partida: list[int] = []
    for f in filas:
        tocadas = set().union(*(partidas_de(c) for c in f.celdas)) if f.celdas else set()
        if tocadas:
            con_error |= tocadas
        else:
            sin_partida.append(f.numero)
    return ClasificacionSilice(
        partidas=tuple(p.numero for p in libro.partidas),
        con_error=frozenset(con_error),
        sin_partida=tuple(sin_partida),
    )


# --- el kappa ------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class KappaPartidas:
    """La tabla de 2 × 2 por partida (experto, Sílice) y su kappa exacto (`None` si el acuerdo
    esperado por azar es 1 o no hay partidas revisadas)."""

    kappa: Fraction | None
    ambos_si: int
    solo_experto: int
    solo_silice: int
    ambos_no: int
    pendientes: int
    filas_sin_partida: int

    @property
    def revisadas(self) -> int:
        return self.ambos_si + self.solo_experto + self.solo_silice + self.ambos_no


def kappa_por_partida(
    revision: Mapping[int, bool | None], silice: ClasificacionSilice
) -> KappaPartidas:
    """El kappa de Cohen entre el experto y Sílice, por partida, sanas incluidas. La revisión debe
    traer exactamente las partidas del libro; las que dejó en blanco quedan como pendientes."""
    del_libro = set(silice.partidas)
    faltan = sorted(del_libro - set(revision))
    sobran = sorted(set(revision) - del_libro)
    if faltan or sobran:
        raise ValueError(
            "La revisión del experto no trae las partidas del libro "
            f"(faltan {faltan or 'ninguna'}; sobran {sobran or 'ninguna'})."
        )
    revisadas = [p for p in silice.partidas if revision[p] is not None]
    experto = [SI if revision[p] else NO for p in revisadas]
    sistema = [SI if p in silice.con_error else NO for p in revisadas]
    pares = list(zip(experto, sistema, strict=True))
    kappa = kappa_exacto(experto, sistema) if revisadas else None
    return KappaPartidas(
        kappa=kappa,
        ambos_si=pares.count((SI, SI)),
        solo_experto=pares.count((SI, NO)),
        solo_silice=pares.count((NO, SI)),
        ambos_no=pares.count((NO, NO)),
        pendientes=len(silice.partidas) - len(revisadas),
        filas_sin_partida=len(silice.sin_partida),
    )
