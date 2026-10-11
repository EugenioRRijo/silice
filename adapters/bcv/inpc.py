"""INPC mensual del BCV (spec S1 §7): una hoja con una columna de periodo y otra del indice
general. La hoja, los dos encabezados, la marca de provisional y la base llegan de `formatos.json`
(copia de `docs/fuentes/bcv_formatos.md`, Tarea 3): el lector no adivina ninguno. El periodo se lee
de una celda fecha o de un texto («Ene-2026», «enero 2026», «01/2026», «2026-01») y se guarda como
el primer dia del mes. Una fila mala se rechaza y se reporta; las demas siguen (UC-17 2b)."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from adapters.bcv.formatos import FormatoMensual
from adapters.bcv.informe import (
    FormatoNoReconocido,
    InformeImportacion,
    Rechazo,
    SerieLeida,
    ValorLeido,
    validar_fuente,
)
from adapters.bcv.libro import Celda, Hoja, Libro

MESES = {
    "ene": 1,
    "enero": 1,
    "feb": 2,
    "febrero": 2,
    "mar": 3,
    "marzo": 3,
    "abr": 4,
    "abril": 4,
    "may": 5,
    "mayo": 5,
    "jun": 6,
    "junio": 6,
    "jul": 7,
    "julio": 7,
    "ago": 8,
    "agosto": 8,
    "sep": 9,
    "sept": 9,
    "set": 9,
    "septiembre": 9,
    "setiembre": 9,
    "oct": 10,
    "octubre": 10,
    "nov": 11,
    "noviembre": 11,
    "dic": 12,
    "diciembre": 12,
}
_NOMBRE_Y_ANIO = re.compile(r"^([a-z]+)\.?[\s\-/]+(\d{4})$")
_MES_Y_ANIO = re.compile(r"^(\d{1,2})[/\-](\d{4})$")
_ANIO_Y_MES = re.compile(r"^(\d{4})[/\-](\d{1,2})$")
_NUMERO = re.compile(r"^\d+(\.\d+)?$")


def _sin_marca(texto: str, marca: str) -> str:
    return (texto.replace(marca, "") if marca else texto).strip()


def _mes(celda: Celda, marca: str) -> date | None:
    if isinstance(celda, date):
        return date(celda.year, celda.month, 1)
    if not isinstance(celda, str):
        return None
    texto = _sin_marca(celda, marca).casefold()
    if m := _NOMBRE_Y_ANIO.match(texto):
        mes, anio = MESES.get(m.group(1)), int(m.group(2))
    elif m := _MES_Y_ANIO.match(texto):
        mes, anio = int(m.group(1)), int(m.group(2))
    elif m := _ANIO_Y_MES.match(texto):
        anio, mes = int(m.group(1)), int(m.group(2))
    else:
        return None
    return date(anio, mes, 1) if mes is not None and 1 <= mes <= 12 else None


def _valor(celda: Celda, marca: str) -> Decimal | None:
    """`Decimal` de la celda: el de la cuadricula o el de un texto con punto decimal."""
    if isinstance(celda, Decimal):
        return celda
    if isinstance(celda, str) and _NUMERO.match(_sin_marca(celda, marca)):
        return Decimal(_sin_marca(celda, marca))
    return None


def _siguiente(mes: date) -> date:
    return date(mes.year + (mes.month == 12), mes.month % 12 + 1, 1)


def _hoja(libro: Libro, formato: FormatoMensual) -> Hoja:
    buscada = formato.hoja.strip().casefold()
    for hoja in libro.hojas:
        if hoja.nombre.strip().casefold() == buscada:
            return hoja
    raise FormatoNoReconocido(f"{libro.archivo}: falta la hoja «{formato.hoja}» del INPC")


def _columna(fila: tuple[Celda, ...], etiqueta: str) -> int | None:
    buscada = etiqueta.casefold()
    return next(
        (i for i, c in enumerate(fila) if isinstance(c, str) and buscada in c.casefold()), None
    )


def _encabezados(hoja: Hoja, formato: FormatoMensual, archivo: str) -> tuple[int, int, int]:
    """Fila de encabezados y columnas del periodo y del valor; el que falte se nombra."""
    for n, fila in enumerate(hoja.filas):
        periodo = _columna(fila, formato.etiqueta_periodo)
        if periodo is None:
            continue
        valor = _columna(fila, formato.etiqueta_valor)
        if valor is None:
            raise FormatoNoReconocido(
                f"{archivo}, hoja «{hoja.nombre}»: falta el encabezado «{formato.etiqueta_valor}»"
            )
        return n, periodo, valor
    raise FormatoNoReconocido(
        f"{archivo}, hoja «{hoja.nombre}»: falta el encabezado «{formato.etiqueta_periodo}»"
    )


def _celda(fila: tuple[Celda, ...], columna: int) -> Celda:
    return fila[columna] if columna < len(fila) else None


_ANIO = re.compile(r"^(\d{4})(?:\.0)?$")


def _columna_exacta(fila: tuple[Celda, ...], etiqueta: str) -> int | None:
    """Columna cuyo texto es exactamente la etiqueta (un titulo que la contiene no cuenta)."""
    return next(
        (i for i, c in enumerate(fila) if isinstance(c, str) and c.strip().casefold() == etiqueta),
        None,
    )


def _anio(celda: Celda, marca: str) -> int | None:
    """Ano de una fila de ano («2026(*)», «2019 », `2024`), o `None` si la celda no lo es."""
    if isinstance(celda, Decimal) and celda == celda.to_integral_value():
        texto = str(int(celda))
    elif isinstance(celda, str):
        texto = _sin_marca(celda, marca)
    else:
        return None
    m = _ANIO.match(texto)
    return int(m.group(1)) if m else None


def _mes_por_nombre(celda: Celda) -> int | None:
    return MESES.get(celda.strip().casefold()) if isinstance(celda, str) else None


Entrada = tuple[str, date | None, Celda, bool, str]  # lugar, mes, celda del valor, marca, motivo


def _entradas_por_celda(hoja: Hoja, formato: FormatoMensual, archivo: str) -> list[Entrada]:
    encabezado, col_periodo, col_valor = _encabezados(hoja, formato, archivo)
    marca = formato.marca_provisional
    entradas: list[Entrada] = []
    for numero, fila in enumerate(hoja.filas[encabezado + 1 :], start=encabezado + 2):
        celda_periodo, celda_valor = _celda(fila, col_periodo), _celda(fila, col_valor)
        if celda_periodo is None and celda_valor is None:
            continue
        provisional = bool(marca) and any(
            isinstance(c, str) and marca in c for c in (celda_periodo, celda_valor)
        )
        mes = _mes(celda_periodo, marca)
        motivo = "mes ilegible" if mes is None else ""
        entradas.append((f"{hoja.nombre}!{numero}", mes, celda_valor, provisional, motivo))
    return entradas


def _entradas_por_anio(hoja: Hoja, formato: FormatoMensual, archivo: str) -> list[Entrada]:
    """Disposicion de `4_5_7.xls`: el ano en una fila propia (columna del periodo, la primera) y
    debajo los nombres de mes; la marca `(*)` del ano vale para todos sus meses. Salen del mas
    antiguo al mas reciente para validar la continuidad."""
    marca = formato.marca_provisional
    etiqueta = formato.etiqueta_valor.casefold()
    encabezado = next(
        (n for n, f in enumerate(hoja.filas) if _columna_exacta(f, etiqueta) is not None), None
    )
    if encabezado is None:
        raise FormatoNoReconocido(
            f"{archivo}, hoja «{hoja.nombre}»: falta el encabezado «{formato.etiqueta_valor}»"
        )
    col_valor = _columna_exacta(hoja.filas[encabezado], etiqueta)
    anio: int | None = None
    provisional = False
    entradas: list[Entrada] = []
    for numero, fila in enumerate(hoja.filas[encabezado + 1 :], start=encabezado + 2):
        celda_periodo, celda_valor = _celda(fila, 0), _celda(fila, col_valor)
        if celda_periodo is None and celda_valor is None:
            continue
        lugar = f"{hoja.nombre}!{numero}"
        nuevo_anio = _anio(celda_periodo, marca) if celda_valor is None else None
        if nuevo_anio is not None:
            anio = nuevo_anio
            provisional = bool(marca) and isinstance(celda_periodo, str) and marca in celda_periodo
            continue
        numero_mes = _mes_por_nombre(celda_periodo)
        if numero_mes is None:
            entradas.append((lugar, None, celda_valor, False, "mes ilegible"))
        elif anio is None:
            entradas.append((lugar, None, celda_valor, False, "mes sin fila de ano"))
        else:
            entradas.append((lugar, date(anio, numero_mes, 1), celda_valor, provisional, ""))
    sin_fecha = [e for e in entradas if e[1] is None]
    return sin_fecha + sorted((e for e in entradas if e[1] is not None), key=lambda e: e[1])


def leer_inpc(
    libro: Libro, *, fuente: str, fecha_descarga: date, formato: FormatoMensual
) -> InformeImportacion:
    fuente = validar_fuente(fuente)
    hoja = _hoja(libro, formato)
    if formato.disposicion == "anio_en_filas":
        entradas = _entradas_por_anio(hoja, formato, libro.archivo)
    elif formato.disposicion == "periodo_en_celda":
        entradas = _entradas_por_celda(hoja, formato, libro.archivo)
    else:
        raise FormatoNoReconocido(f"disposicion {formato.disposicion!r} desconocida")
    marca = formato.marca_provisional
    valores: list[ValorLeido] = []
    rechazos: list[Rechazo] = []
    for lugar, mes, celda_valor, provisional, previo in entradas:
        valor = _valor(celda_valor, marca)
        anterior = valores[-1].fecha if valores else None
        motivo = previo or (
            "mes repetido"
            if any(v.fecha == mes for v in valores)
            else "mes posterior a la descarga"
            if mes > fecha_descarga
            else "mes no consecutivo con el anterior"
            if anterior and mes != _siguiente(anterior)
            else "valor no numerico"
            if valor is None
            else "el valor debe ser mayor que cero"
            if valor <= 0
            else ""
        )
        if motivo:
            rechazos.append(Rechazo(lugar, motivo))
            continue
        valores.append(ValorLeido(mes, valor, provisional, lugar))
    serie = SerieLeida(
        "inpc_general",
        "INPC, indice general",
        "BCV-INE",
        "indice_bs",
        "mensual",
        formato.base,
        tuple(valores),
    )
    return InformeImportacion(
        libro.archivo,
        libro.huella,
        fuente,
        fecha_descarga,
        (serie,),
        tuple(rechazos),
        tuple(libro.avisos),
        len(entradas),
    )
