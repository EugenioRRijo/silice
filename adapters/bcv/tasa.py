"""Tasa de referencia del BCV: .xls trimestral, una hoja por día hábil (S1 §7). Solo el USD (H‑D1).
Las etiquetas «Fecha Valor» y el código USD están verificadas (antecedentes §6); la letra del
trimestre llega de `formatos.json` (Tarea 3). SUPUESTO_DECLARADO: la fecha valor puede caer hasta 7
días naturales después del fin del trimestre (la última hoja del 3T‑2026 vale el 01‑10‑2026)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, timedelta
from decimal import Decimal

from adapters.bcv.informe import (
    FormatoNoReconocido,
    InformeImportacion,
    Rechazo,
    SerieLeida,
    ValorLeido,
    validar_fuente,
)
from adapters.bcv.libro import Hoja, Libro

ETIQUETA_FECHA_VALOR = "fecha valor"
CODIGO_USD = "USD"
PATRON_NOMBRE = re.compile(r"^2_1_2([a-d])(\d{2})_smc\.xls$", re.IGNORECASE)
DIAS_DE_FECHA_VALOR = 7
_FECHA = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_SIN_ETIQUETA = object()


def _es_usd(celda) -> bool:
    return isinstance(celda, str) and celda.strip().upper() == CODIGO_USD


def _fecha_de(celda) -> date | None:
    if isinstance(celda, date):
        return celda
    m = _FECHA.search(celda) if isinstance(celda, str) else None
    if m is None:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _fecha_valor(hoja: Hoja):
    for fila in hoja.filas:
        for i, celda in enumerate(fila):
            if isinstance(celda, str) and ETIQUETA_FECHA_VALOR in celda.casefold():
                propia = _fecha_de(celda.split(":", 1)[1]) if ":" in celda else None
                siguiente = next((c for c in fila[i + 1 :] if c is not None), None)
                return propia or _fecha_de(siguiente)
    return _SIN_ETIQUETA


def _rango(archivo: str, letras: Mapping[str, int]) -> tuple[date, date] | None:
    m = PATRON_NOMBRE.match(archivo)
    if m is None:
        return None
    trimestre, anio = letras[m.group(1).lower()], 2000 + int(m.group(2))
    inicio = date(anio, 3 * trimestre - 2, 1)
    fin = (
        date(anio + 1, 1, 1) if trimestre == 4 else date(anio, 3 * trimestre + 1, 1)
    ) - timedelta(1)
    return inicio, fin + timedelta(days=DIAS_DE_FECHA_VALOR)


def leer_tasa(
    libro: Libro, *, fuente: str, fecha_descarga: date, trimestre_por_letra: Mapping[str, int]
) -> InformeImportacion:
    fuente = validar_fuente(fuente)
    advertencias = list(libro.avisos)
    rango = _rango(libro.archivo, trimestre_por_letra)
    if rango is None:
        advertencias.append(
            f"el nombre {libro.archivo!r} no sigue 2_1_2<letra><AA>_smc.xls: se "
            "importa porque el formato valida (UC-17 2e)"
        )
    compra, venta, rechazos, vistas, con_etiqueta, otras = [], [], [], set(), 0, 0
    for hoja in libro.hojas:
        fecha = _fecha_valor(hoja)
        if fecha is _SIN_ETIQUETA:
            rechazos.append(Rechazo(hoja.nombre, "falta la etiqueta «Fecha Valor»"))
            continue
        con_etiqueta += 1
        motivo = (
            "fecha valor ilegible"
            if fecha is None
            else "fecha repetida"
            if fecha in vistas
            else "fecha posterior a la descarga"
            if fecha > fecha_descarga
            else "fecha fuera del trimestre del archivo"
            if rango and not rango[0] <= fecha <= rango[1]
            else ""
        )
        if motivo:
            rechazos.append(Rechazo(hoja.nombre, motivo))
            continue
        fila_usd = next(
            (
                (n, f)
                for n, f in enumerate(hoja.filas)
                if any(isinstance(c, str) and c.strip().upper() == CODIGO_USD for c in f)
            ),
            None,
        )
        if fila_usd is None:
            rechazos.append(
                Rechazo(hoja.nombre, "la hoja no trae la fila USD (hoja de otra moneda)")
            )
            continue
        n, fila = fila_usd
        # Tras el codigo vienen el pais, la cotizacion M.E./US$ (compra y venta: 1.0 y 1.0 para el
        # USD) y los Bs por moneda (compra y venta): las dos ultimas cifras son las de Bs.
        despues = fila[[i for i, c in enumerate(fila) if _es_usd(c)][0] + 1 :]
        numeros = [c for c in despues if c is not None][-2:]
        if len(numeros) < 2 or not all(isinstance(x, Decimal) for x in numeros):
            rechazos.append(
                Rechazo(f"{hoja.nombre}!{n + 1}", "valor no numerico en compra o venta")
            )
            continue
        c, v = numeros
        if c <= 0 or v <= 0:
            rechazos.append(Rechazo(f"{hoja.nombre}!{n + 1}", "el valor debe ser mayor que cero"))
            continue
        if c > v:
            advertencias.append(
                f"{hoja.nombre}: compra {c} mayor que venta {v} (expectativa, no regla)"
            )
        vistas.add(fecha)
        compra.append(ValorLeido(fecha, c, lugar=f"{hoja.nombre}!{n + 1}"))
        venta.append(ValorLeido(fecha, v, lugar=f"{hoja.nombre}!{n + 1}"))
        otras += sum(
            1
            for f in hoja.filas
            for x in f[:1]
            if isinstance(x, str)
            and re.fullmatch(r"[A-Z]{3}", x.strip())
            and x.strip() != CODIGO_USD
        )
    if con_etiqueta == 0:
        raise FormatoNoReconocido(f"{libro.archivo}: ninguna hoja trae la etiqueta «Fecha Valor»")
    if otras:
        advertencias.append(f"{otras} filas de otras monedas no importadas (solo USD, H-D1)")
    series = tuple(
        SerieLeida(clave, f"Tasa USD ({lado})", "BCV", "Bs/USD", "diaria", "", tuple(vals))
        for clave, lado, vals in (("usd_compra", "compra", compra), ("usd_venta", "venta", venta))
    )
    return InformeImportacion(
        libro.archivo,
        libro.huella,
        fuente,
        fecha_descarga,
        series,
        tuple(rechazos),
        tuple(advertencias),
        len(libro.hojas),
    )
