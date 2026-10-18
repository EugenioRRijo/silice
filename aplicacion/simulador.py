"""Simulador de listas de precios: la logica de `scripts/simular_lista.py` y de la pagina
«Simulador de listas», sin Streamlit (RM-1).

Herramienta de prueba, no fuente de mercado (UC-07 es I6.3). Toma la lista vigente del catalogo y
emite variaciones reproducibles segun una semilla, en el formato canonico
`tipo,insumo,unidad,precio` que consume UC-02. Los mensajes de error son los de la pagina Streamlit.
"""

from __future__ import annotations

import csv
import io
import random
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from core.catalog import Catalogo
from core.verification.informe import DECIMALES_PRESENTACION

COLUMNAS_CSV = ("tipo", "insumo", "unidad", "precio")
NOMBRE_CSV = "lista_simulada.csv"
MENSAJE_SIN_FILAS = "La simulacion no produjo ninguna fila (revise el filtro de insumos)."

#: El paso del precio simulado: los mismos dos decimales de la presentacion (INV-049). Solo el
#: paso: el `quantize` que lo usa no fija `rounding`, asi que aplica el modo del contexto
#: (`ROUND_HALF_EVEN`), no el `ROUND_HALF_UP` de `formatear_decimal`. Es a proposito: lo que se
#: redondea es un precio que se guarda en la lista simulada, no un texto que se presenta, y
#: cambiar el modo alteraria las series ya generadas con cada semilla.
PASO_DE_PRESENTACION = Decimal(1).scaleb(-DECIMALES_PRESENTACION)

#: Tope de la variacion maxima, en porcentaje (inclusive).
VARIACION_MAXIMA = Decimal(1000)
MENSAJE_VARIACION_NO_FINITA = "La variacion maxima debe ser un numero finito."
MENSAJE_VARIACION_NEGATIVA = "La variacion maxima no puede ser negativa."
MENSAJE_VARIACION_TOPE = f"La variacion maxima no puede pasar de {VARIACION_MAXIMA} %."

FilaSimulada = tuple[str, str, str, Decimal]


def simular(
    precios: dict[str, tuple[str, str, Decimal]],
    variacion_max: Decimal,
    semilla: int,
    solo: set[str] | None,
) -> list[FilaSimulada]:
    """Aplica variaciones deterministas a una lista de precios.

    Args:
        precios: {insumo: (tipo, unidad, precio_decimal)}
        variacion_max: porcentaje máximo de variación (ej: Decimal("10") para ±10%)
        semilla: número para reproducibilidad
        solo: conjunto de nombres de insumos a incluir; None para todos

    Returns:
        Lista de tuplas (tipo, insumo, unidad, precio_nuevo con variacion aplicada)
    """
    generador = random.Random(semilla)
    pb_max = int(variacion_max * 100)  # puntos básicos

    resultados = []
    for insumo, (tipo, unidad, precio) in sorted(precios.items()):
        if solo is not None and insumo not in solo:
            continue

        pb_sorteado = generador.randint(-pb_max, pb_max)
        factor_variacion = 1 + Decimal(pb_sorteado) / Decimal(10000)
        precio_nuevo = precio * factor_variacion
        precio_nuevo = precio_nuevo.quantize(PASO_DE_PRESENTACION)

        resultados.append((tipo, insumo, unidad, precio_nuevo))

    return resultados


def variacion_de_texto(texto: str) -> Decimal:
    """La variacion maxima (%) escrita como decimal finito, 0 <= v <= `VARIACION_MAXIMA`.

    `ValueError` con el mensaje de la pagina si no es decimal; con mensaje propio si no es finita,
    es negativa o pasa del tope. El tope evita que `int(v * 100)` de `simular` construya un entero
    gigante (`1E+999999` tardaria segundos o minutos de CPU) y es mucho mas de lo que tiene sentido
    para una variacion de precios.
    """
    try:
        valor = Decimal(str(texto))
    except InvalidOperation as error:
        raise ValueError(f"La variacion maxima no es un numero decimal: {error}") from error
    if not valor.is_finite():
        raise ValueError(MENSAJE_VARIACION_NO_FINITA)
    if valor < 0:
        raise ValueError(MENSAJE_VARIACION_NEGATIVA)
    if valor > VARIACION_MAXIMA:
        raise ValueError(MENSAJE_VARIACION_TOPE)
    return valor


def insumos_de_texto(texto: str | None) -> set[str] | None:
    """Los insumos separados por coma; vacio (o solo espacios) = todos (`None`)."""
    limpio = (texto or "").strip()
    if not limpio:
        return None
    return {i.strip() for i in limpio.split(",") if i.strip()}


def precios_vigentes(catalogo: Catalogo) -> dict[str, tuple[str, str, Decimal]]:
    """`{insumo: (tipo, unidad, precio)}` de la lista vigente, tal como espera `simular()`."""
    lista = catalogo.lista_vigente()
    return {
        precio.insumo.descripcion: (precio.insumo.tipo, precio.insumo.unidad, precio.precio)
        for precio in lista.precios
    }


def simular_desde_catalogo(
    sesion: Session, variacion_max: str, semilla: int, insumos: str | None
) -> list[FilaSimulada]:
    """Lee la lista vigente y la simula. Solo lee: no escribe en la base.

    `ValueError` si la variacion o la semilla no sirven (tambien las `ArithmeticError` de
    `Decimal`, convertidas), `CatalogoIncompleto` (`LookupError`) si no hay lista vigente.
    """
    variacion = variacion_de_texto(variacion_max)
    precios = precios_vigentes(Catalogo(sesion))
    try:
        return simular(precios, variacion, semilla, insumos_de_texto(insumos))
    except ArithmeticError as error:
        raise ValueError(str(error)) from error


def csv_de(filas: list[FilaSimulada]) -> bytes:
    """El CSV canonico (`tipo,insumo,unidad,precio`) en UTF-8.

    Deuda conocida: las celdas de texto (insumo, unidad) no se neutralizan contra la inyeccion de
    formulas de hoja de calculo (`=`, `+`, `-`, `@` al inicio). No se cambia aqui porque rompe el
    ida y vuelta con UC-02, que relee este mismo formato; se decide con el tutor.
    """
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(COLUMNAS_CSV)
    for tipo, insumo, unidad, precio in filas:
        escritor.writerow([tipo, insumo, unidad, str(precio)])
    return buffer.getvalue().encode("utf-8")
