"""Respaldo por CSV canonico de series (spec S1 §7.3): `serie,fecha,valor,provisional,fuente`.

Para el indice de insumos de la construccion mientras su formato no este documentado, y para
cualquier serie si el BCV cambia el formato. Las mismas validaciones de fecha, valor y repeticion
que los lectores de .xls; la fuente es obligatoria por fila. Nombre, organismo, unidad y
periodicidad de cada serie los declara la interfaz al confirmar (`ui.indices.confirmar`,
`definiciones_csv`)."""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from adapters.bcv.informe import (
    FormatoNoReconocido,
    InformeImportacion,
    Rechazo,
    SerieLeida,
    ValorLeido,
)
from adapters.bcv.libro import LIMITE_BYTES

COLUMNAS_CSV = ("serie", "fecha", "valor", "provisional", "fuente")
_PROVISIONAL = {"si": True, "sí": True, "no": False, "": False}


def _valor(texto: str) -> Decimal | str:
    """El valor de la fila o, si no vale, el motivo del rechazo (nunca pasa por `float`)."""
    if "," in texto:
        return f"{texto!r} lleva coma; use punto como separador decimal"
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return f"valor {texto!r} no numerico"
    if not valor.is_finite():
        return f"valor {texto!r} no numerico"
    return valor if valor > 0 else "el valor debe ser mayor que cero"


def _fecha(texto: str) -> date | None:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return None


def leer_csv_canonico(ruta: Path, *, fecha_descarga: date) -> InformeImportacion:
    tamano = ruta.stat().st_size
    if tamano > LIMITE_BYTES:
        raise FormatoNoReconocido(f"{ruta.name}: pesa {tamano / 2**20:.1f} MB; el limite es 20 MB")
    contenido = ruta.read_bytes()
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise FormatoNoReconocido(f"{ruta.name}: el CSV debe estar en UTF-8") from None
    lector = csv.DictReader(io.StringIO(texto, newline=""))
    columnas = tuple((c or "").strip().lower() for c in lector.fieldnames or ())
    if columnas != COLUMNAS_CSV:
        faltan = [c for c in COLUMNAS_CSV if c not in columnas]
        raise FormatoNoReconocido(
            f"{ruta.name}: las columnas deben ser exactamente {', '.join(COLUMNAS_CSV)}"
            + (f"; faltan {', '.join(faltan)}" if faltan else "")
        )
    lector.fieldnames = list(COLUMNAS_CSV)
    valores: dict[str, list[ValorLeido]] = {}
    rechazos: list[Rechazo] = []
    vistas: set[tuple[str, date]] = set()
    fuentes: list[str] = []
    leidas = 0
    for numero, fila in enumerate(lector, start=2):
        leidas += 1
        lugar = f"{ruta.name}:{numero}"
        celda = {c: (fila.get(c) or "").strip() for c in COLUMNAS_CSV}
        fecha, valor = _fecha(celda["fecha"]), _valor(celda["valor"])
        provisional = _PROVISIONAL.get(celda["provisional"].casefold())
        motivo = (
            "la serie no puede estar vacia"
            if not celda["serie"]
            else f"fecha {celda['fecha']!r} no es AAAA-MM-DD"
            if fecha is None
            else "fecha posterior a la descarga"
            if fecha > fecha_descarga
            else valor
            if isinstance(valor, str)
            else "provisional debe ser si, no o vacio"
            if provisional is None
            else "la fuente es obligatoria por fila"
            if not celda["fuente"]
            else "(serie, fecha) repetido"
            if (celda["serie"], fecha) in vistas
            else ""
        )
        if motivo:
            rechazos.append(Rechazo(lugar, motivo))
            continue
        vistas.add((celda["serie"], fecha))
        fuentes.append(celda["fuente"])
        valores.setdefault(celda["serie"], []).append(ValorLeido(fecha, valor, provisional, lugar))
    series = tuple(
        SerieLeida(clave, clave, "", "", "", "", tuple(lista)) for clave, lista in valores.items()
    )
    return InformeImportacion(
        ruta.name,
        hashlib.sha256(contenido).hexdigest(),
        "; ".join(dict.fromkeys(fuentes)),
        fecha_descarga,
        series,
        tuple(rechazos),
        (),
        leidas,
    )
