"""Lector CSV de tramos viales y `AdaptadorVial` (plan vial, Tarea 7; Foco de revisión 3).

Formato en `data/samples/vial/README.md`: una fila por capa o por línea de demarcación, separador
`;` (o `,` si la cabecera no trae `;`), coma o punto decimal. Todo error nombra el archivo y la
fila tal como la numera una hoja de cálculo (la cabecera es la fila 1) y se lanza como
`ValueError`, que la API traduce a 422. Nada se adivina: lo que no sigue el formato se rechaza.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Demarcacion, Tramo
from core.contracts import AdaptadorDominio, Dominio, ItemComputo

_COLUMNAS_TRAMO = ("progresiva_ini_km", "progresiva_fin_km", "ancho_m", "distancia_planta_km")
_COLUMNAS_CAPA = ("espesor_m", "densidad_t_m3", "dosis_l_m2")
COLUMNAS = ("tramo", *_COLUMNAS_TRAMO, "elemento", "tipo", *_COLUMNAS_CAPA, "lineas")

_CAPA = "capa"
_DEMARCACION = "demarcacion"


def numero(texto: str) -> Decimal:
    """`"7,30"` -> `Decimal("7.30")`; `"1.234,5"` -> `Decimal("1234.5")`; `"7.30"` -> `7.30`.

    Con coma, la coma es el separador decimal y los puntos son de miles (es-VE); sin coma, el
    punto es el decimal. Un texto que no es un número finito lanza `ValueError`.
    """
    limpio = texto.strip().replace(" ", "")
    if "," in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(limpio)
    except InvalidOperation:
        raise ValueError(f"no es un número: {texto!r}") from None
    if not valor.is_finite():
        raise ValueError(f"no es un número finito: {texto!r}")
    return valor


def _celda(fila: dict[str, str | None], columna: str) -> str:
    return (fila.get(columna) or "").strip()


def _decimal(fila: dict[str, str | None], columna: str) -> Decimal | None:
    texto = _celda(fila, columna)
    if not texto:
        return None
    try:
        return numero(texto)
    except ValueError as error:
        raise ValueError(f"la columna {columna!r} {error}") from None


@dataclass
class _Borrador:
    """Lo leído de un tramo mientras se recorren sus filas."""

    fila: int
    ini: Decimal
    fin: Decimal
    ancho: Decimal
    datos: dict[str, Decimal | None]
    capas: list[Capa] = field(default_factory=list)
    demarcacion: list[Demarcacion] = field(default_factory=list)


def _borrador(fila: dict[str, str | None], numero_fila: int, previo: _Borrador | None) -> _Borrador:
    """El borrador del tramo de `fila`: uno nuevo en su primera fila; si no, el previo, con la
    comprobación de que las columnas del tramo que la fila llene coincidan con las de la primera."""
    datos = {columna: _decimal(fila, columna) for columna in _COLUMNAS_TRAMO}
    if previo is not None:
        for columna, valor in datos.items():
            if valor is not None and valor != previo.datos[columna]:
                raise ValueError(
                    f"la columna {columna!r} ({valor}) no coincide con la de la fila "
                    f"{previo.fila} del mismo tramo ({previo.datos[columna]})"
                )
        return previo
    ini, fin, ancho = (datos[columna] for columna in _COLUMNAS_TRAMO[:3])
    if ini is None or fin is None or ancho is None:
        faltan = [c for c in _COLUMNAS_TRAMO[:3] if datos[c] is None]
        raise ValueError(f"la primera fila del tramo debe llenar {', '.join(faltan)}")
    return _Borrador(numero_fila, ini, fin, ancho, datos)


def _agregar_elemento(fila: dict[str, str | None], borrador: _Borrador) -> None:
    elemento, tipo = _celda(fila, "elemento"), _celda(fila, "tipo")
    if elemento == _CAPA:
        if _celda(fila, "lineas"):
            raise ValueError("una capa no usa la columna 'lineas': déjela vacía")
        valores = (_decimal(fila, columna) for columna in _COLUMNAS_CAPA)
        borrador.capas.append(Capa(tipo, *valores))
    elif elemento == _DEMARCACION:
        llenas = [columna for columna in _COLUMNAS_CAPA if _celda(fila, columna)]
        if llenas:
            raise ValueError(f"una demarcación no usa {', '.join(llenas)}: déjelas vacías")
        lineas = _celda(fila, "lineas")
        if not (lineas.isascii() and lineas.isdigit()):
            raise ValueError(f"la columna 'lineas' debe ser un entero: {lineas!r}")
        borrador.demarcacion.append(Demarcacion(tipo, int(lineas)))
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
