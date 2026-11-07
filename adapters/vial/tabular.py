"""Lector CSV de tramos viales y `AdaptadorVial` (plan vial, Tarea 7; Foco de revisión 3).

Formato en `data/samples/vial/README.md`: una fila por capa o por línea de demarcación, separador
`;` (o `,` si la cabecera no trae `;`), coma decimal con punto de miles o punto decimal
(`numero`). Todo error nombra el archivo y la fila tal como la numera una hoja de cálculo (la
cabecera es la fila 1) y se lanza como `ValueError`, que la API traduce a 422. Nada se
adivina: lo que no sigue el formato se rechaza.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Demarcacion, Tramo
from core.contracts import AdaptadorDominio, Dominio, ItemComputo

_COLUMNAS_TRAMO = ("progresiva_ini_km", "progresiva_fin_km", "ancho_m", "distancia_planta_km")
_COLUMNAS_CAPA = ("espesor_m", "densidad_t_m3", "dosis_l_m2")
COLUMNAS = ("tramo", *_COLUMNAS_TRAMO, "elemento", "tipo", *_COLUMNAS_CAPA, "lineas")
#: Columna opcional (Tarea 16b): el porcentaje de asfalto de la mezcla de la carpeta o del bacheo.
#: Un archivo sin ella se lee igual que antes.
ASFALTO = "asfalto_pct"
#: Columnas opcionales de F5 vial, tarea 1 (diseño 2026-11-03 §6.3): de la capa, el esponjamiento
#: del fresado, la limpieza de un riego («sí» o «no») y la otra medición («m2» del fresado, «t» de
#: la carpeta); de la demarcación, el área de cada elemento de superficie y los captafaros de una
#: línea. Un archivo sin ellas se lee igual que antes.
ESPONJAMIENTO = "esponjamiento"
LIMPIEZA = "limpieza"
MEDICION = "medicion"
AREA = "area_m2"
CAPTAFAROS = "captafaros"
#: Columna opcional del tramo (F5 vial, tarea 2): «banda» si la obra mide el transporte de la mezcla
#: en t por banda de distancia; vacía, en t·km. Se llena en la primera fila del tramo, como la
#: distancia; si se repite en otra fila, debe coincidir.
TRANSPORTE = "transporte"
_SOLO_CAPA = (*_COLUMNAS_CAPA, ASFALTO, ESPONJAMIENTO, LIMPIEZA, MEDICION)
_SOLO_DEMARCACION = ("lineas", AREA, CAPTAFAROS)

_CAPA = "capa"
_DEMARCACION = "demarcacion"


#: Lo que se recorta en los bordes de una celda, y nada más: copia de `aplicacion.cifras.BLANCOS`
#: (un adaptador no importa de `aplicacion`; una prueba compara ambos lectores con el oráculo
#: `tests/fixtures/cifras_escritas.json`).
BLANCOS = " \t\n\r\x0b\x0c\xa0\x85\ufeff"

# `[0-9]` y no `\d`: en Python `\d` también acepta cifras arábigas o de ancho completo.
#: Con coma: coma decimal y, en la parte entera, puntos de miles de tres en tres (es-VE, la regla
#: de `aplicacion/cifras.py`).
_CON_COMA = re.compile(r"-?(?:[0-9]+|[1-9][0-9]{0,2}(?:\.[0-9]{3})+),[0-9]+")
#: Sin coma: entero o punto decimal («7.30»).
_SIN_COMA = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
#: Sin coma pero con forma de miles («1.234»): ¿mil doscientos treinta y cuatro o uno coma dos?
_MILES_SIN_COMA = re.compile(r"-?[1-9][0-9]{0,2}(?:\.[0-9]{3})+")

_AYUDA = "coma decimal y punto de miles (1.234,5) o punto decimal sin miles (1234.5)"


def numero(texto: str) -> Decimal:
    """El `Decimal` exacto de una cifra del archivo de tramos; `ValueError` si no sigue la regla.

    - Con coma: la coma es el decimal y los puntos, de miles («7,30», «1.234,5», «12.345.678,9»).
    - Sin coma: el punto es el decimal («7.30», «0.123», «1.2345»), salvo la forma de miles
      («1.234», «1.234.567»), que es ambigua y se rechaza pidiendo cómo escribirla.
    - Solo cifras 0-9 ASCII y un «-» opcional: ni espacios, ni «_», ni exponentes, ni «+».
    """
    limpio = texto.strip(BLANCOS)
    if "," in limpio:
        if _CON_COMA.fullmatch(limpio) is None:
            raise ValueError(f"{texto!r} no es una cifra bien escrita: use {_AYUDA}")
        limpio = limpio.replace(".", "").replace(",", ".")
    elif _MILES_SIN_COMA.fullmatch(limpio) is not None:
        sin_puntos = limpio.replace(".", "")
        if limpio.count(".") > 1:
            raise ValueError(
                f"{texto!r} lleva puntos de miles sin coma decimal: "
                f"escriba {sin_puntos} o {limpio},0"
            )
        raise ValueError(
            f"{texto!r} es ambiguo (¿miles o decimales?): "
            f"escriba {sin_puntos} o {limpio.replace('.', ',')}"
        )
    elif _SIN_COMA.fullmatch(limpio) is None:
        raise ValueError(f"{texto!r} no es una cifra bien escrita: use {_AYUDA}")
    valor = Decimal(limpio)
    return valor.copy_abs() if valor.is_zero() else valor


def _celda(fila: dict[str, str | None], columna: str) -> str:
    return (fila.get(columna) or "").strip(BLANCOS)


def _decimal(fila: dict[str, str | None], columna: str) -> Decimal | None:
    texto = _celda(fila, columna)
    if not texto:
        return None
    try:
        return numero(texto)
    except ValueError as error:
        raise ValueError(f"la columna {columna!r}: {error}") from None


@dataclass
class _Borrador:
    """Lo leído de un tramo mientras se recorren sus filas."""

    fila: int
    ini: Decimal
    fin: Decimal
    ancho: Decimal
    datos: dict[str, Decimal | None]
    transporte: str | None = None
    capas: list[Capa] = field(default_factory=list)
    demarcacion: list[Demarcacion] = field(default_factory=list)


def _borrador(fila: dict[str, str | None], numero_fila: int, previo: _Borrador | None) -> _Borrador:
    """El borrador del tramo de `fila`: uno nuevo en su primera fila; si no, el previo, con la
    comprobación de que las columnas del tramo que la fila llene coincidan con las de la primera."""
    datos = {columna: _decimal(fila, columna) for columna in _COLUMNAS_TRAMO}
    transporte = _celda(fila, TRANSPORTE) or None
    if previo is not None:
        for columna, valor in datos.items():
            if valor is not None and valor != previo.datos[columna]:
                raise ValueError(
                    f"la columna {columna!r} ({valor}) no coincide con la de la fila "
                    f"{previo.fila} del mismo tramo ({previo.datos[columna]})"
                )
        if transporte is not None and transporte != previo.transporte:
            raise ValueError(
                f"la columna {TRANSPORTE!r} ({transporte}) no coincide con la de la fila "
                f"{previo.fila} del mismo tramo ({previo.transporte or 'vacía'})"
            )
        return previo
    ini, fin, ancho = (datos[columna] for columna in _COLUMNAS_TRAMO[:3])
    if ini is None or fin is None or ancho is None:
        faltan = [c for c in _COLUMNAS_TRAMO[:3] if datos[c] is None]
        raise ValueError(f"la primera fila del tramo debe llenar {', '.join(faltan)}")
    return _Borrador(numero_fila, ini, fin, ancho, datos, transporte)


def _entero(fila: dict[str, str | None], columna: str) -> int | None:
    texto = _celda(fila, columna)
    if not texto:
        return None
    if not (texto.isascii() and texto.isdigit()):
        raise ValueError(f"la columna {columna!r} debe ser un entero: {texto!r}")
    return int(texto)


def _si_no(fila: dict[str, str | None], columna: str) -> bool:
    texto = _celda(fila, columna).casefold()
    if texto in ("", "no"):
        return False
    if texto in ("si", "sí"):
        return True
    raise ValueError(f"la columna {columna!r} debe ser sí o no: {_celda(fila, columna)!r}")


def _agregar_elemento(fila: dict[str, str | None], borrador: _Borrador) -> None:
    elemento, tipo = _celda(fila, "elemento"), _celda(fila, "tipo")
    if elemento == _CAPA:
        llenas = [columna for columna in _SOLO_DEMARCACION if _celda(fila, columna)]
        if llenas:
            columnas = ", ".join(repr(c) for c in llenas)
            raise ValueError(f"una capa no usa la columna {columnas}: déjela vacía")
        valores = (_decimal(fila, columna) for columna in (*_COLUMNAS_CAPA, ASFALTO))
        borrador.capas.append(
            Capa(
                tipo,
                *valores,
                esponjamiento=_decimal(fila, ESPONJAMIENTO),
                limpieza=_si_no(fila, LIMPIEZA),
                medicion=_celda(fila, MEDICION) or None,
            )
        )
    elif elemento == _DEMARCACION:
        llenas = [columna for columna in _SOLO_CAPA if _celda(fila, columna)]
        if llenas:
            raise ValueError(f"una demarcación no usa {', '.join(llenas)}: déjelas vacías")
        lineas = _celda(fila, "lineas")
        if not (lineas.isascii() and lineas.isdigit()):
            raise ValueError(f"la columna 'lineas' debe ser un entero: {lineas!r}")
        borrador.demarcacion.append(
            Demarcacion(
                tipo,
                int(lineas),
                area_m2=_decimal(fila, AREA),
                captafaros=_entero(fila, CAPTAFAROS),
            )
        )
    else:
        raise ValueError(
            f"elemento desconocido: {elemento!r} (se esperaba {_CAPA!r} o {_DEMARCACION!r})"
        )


def _filas(ruta: Path) -> list[tuple[int, dict[str, str | None]]]:
    nombre = ruta.name
    try:
        with open(ruta, newline="", encoding="utf-8-sig") as archivo:
            cabecera = archivo.readline()
            separador = ";" if ";" in cabecera else ","
            archivo.seek(0)
            lector = csv.DictReader(archivo, delimiter=separador)
            presentes = [c.strip() for c in lector.fieldnames or ()]
            faltantes = [c for c in COLUMNAS if c not in presentes]
            if faltantes:
                raise ValueError(
                    f"el archivo {nombre!r} no es un archivo de tramos viales: faltan las "
                    f"columnas {faltantes}"
                )
            lector.fieldnames = presentes
            filas = []
            for fila in lector:
                if None in fila:
                    raise ValueError(
                        f"el archivo {nombre!r}, fila {lector.line_num}: trae más celdas que la "
                        "cabecera"
                    )
                filas.append((lector.line_num, fila))
            return filas
    except UnicodeDecodeError as error:
        raise ValueError(
            f"el archivo {nombre!r} es ilegible: no es un CSV de texto en UTF-8"
        ) from error


def leer_tramos(ruta: Path) -> list[Tramo]:
    """Los tramos del CSV `ruta`, en el orden en que aparecen por primera vez."""
    ruta = Path(ruta)
    borradores: dict[str, _Borrador] = {}
    for numero_fila, fila in _filas(ruta):
        try:
            tramo_id = _celda(fila, "tramo")
            if not tramo_id:
                raise ValueError("la columna 'tramo' está vacía")
            borrador = _borrador(fila, numero_fila, borradores.get(tramo_id))
            borradores[tramo_id] = borrador
            _agregar_elemento(fila, borrador)
        except ValueError as error:
            raise ValueError(f"el archivo {ruta.name!r}, fila {numero_fila}: {error}") from None
    if not borradores:
        raise ValueError(f"el archivo {ruta.name!r} no trae ningun tramo")
    tramos = []
    for tramo_id, b in borradores.items():
        try:
            tramos.append(
                Tramo(
                    tramo_id,
                    b.ini,
                    b.fin,
                    b.ancho,
                    tuple(b.capas),
                    tuple(b.demarcacion),
                    b.datos["distancia_planta_km"],
                    b.transporte,
                )
            )
        except ValueError as error:
            raise ValueError(f"el archivo {ruta.name!r}, fila {b.fila}: {error}") from None
    return tramos


class AdaptadorVial(AdaptadorDominio):
    """Cantidades viales trazables desde un CSV de tramos (subespecialidad de civil)."""

    dominio = Dominio.CIVIL

    def extraer(self, fuente: Path | str) -> list[ItemComputo]:
        return derivar_tramos(leer_tramos(Path(fuente)))
