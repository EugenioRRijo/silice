"""Pagina del simulador de listas de precios (Sesion F.1, spec §3): formulario sobre
`scripts.simular_lista.simular`.

Aplica variaciones deterministas (segun una semilla) a la lista vigente del catalogo y ofrece el
CSV resultante para descargar, en el mismo formato canonico de `data/samples/precios/`
(`tipo,insumo,unidad,precio`) que consume UC-02. Herramienta de prueba, no una fuente de mercado
(UC-07 es I6.3): el simulador ya lo declara asi en su propio docstring, y esta pagina no repite ese
supuesto de otra forma que invocandolo.
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation
from pathlib import Path

import streamlit as st
from pandas import DataFrame

from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from scripts.simular_lista import simular
from ui.caso import ruta_caso

COLUMNAS_CSV = ("tipo", "insumo", "unidad", "precio")
CLAVE_RESULTADO = "resultado_simulador"


def render() -> None:
    """Formulario en la barra lateral; vista previa y descarga del CSV en el cuerpo."""
    st.caption(
        "Toma la lista de precios vigente del catalogo y aplica variaciones deterministas segun "
        "una semilla, en el formato tipo,insumo,unidad,precio. Herramienta de prueba, no una "
        "fuente de mercado (UC-07 es I6.3)."
    )

    parametros = _formulario()

    if st.button("Generar lista simulada", type="primary"):
        with st.spinner("Simulando..."):
            _generar(parametros)

    _mostrar(st.session_state.get(CLAVE_RESULTADO))


def _formulario() -> dict[str, object]:
    with st.sidebar:
        st.header("Simulacion")
        semilla = st.number_input("Semilla", min_value=0, value=42, step=1)
        variacion_max = st.text_input("Variacion maxima (%)", value="5")
        insumos = st.text_input("Insumos (separados por coma; vacio = todos)", value="")

    return {
        "ruta": ruta_caso(),
        "semilla": int(semilla),
        "variacion_max": variacion_max,
        "insumos": insumos,
    }


def _generar(parametros: dict[str, object]) -> None:
    """Lee la lista vigente, aplica `simular()` y deja el CSV listo para descargar."""
    try:
        variacion_max = Decimal(str(parametros["variacion_max"]))
    except InvalidOperation as error:
        st.session_state[CLAVE_RESULTADO] = None
        st.error(f"La variacion maxima no es un numero decimal: {error}")
        return

    texto_insumos = str(parametros["insumos"]).strip()
    solo = {i.strip() for i in texto_insumos.split(",") if i.strip()} if texto_insumos else None

    motor = crear_motor(f"sqlite:///{Path(parametros['ruta']).as_posix()}")
    try:
        preparar_base(Path(parametros["ruta"]))
        with abrir_sesion(motor) as sesion:
            precios = _precios_vigentes(Catalogo(sesion))
        filas = simular(precios, variacion_max, int(parametros["semilla"]), solo)
    except (LookupError, ValueError, ArithmeticError) as error:
        # `CatalogoIncompleto` (LookupError) si no hay lista vigente; `ValueError` si la variacion
        # maxima o la semilla son invalidas; `ArithmeticError` desde cualquier operacion con
        # `Decimal` que reciba un valor mal formado.
        st.session_state[CLAVE_RESULTADO] = None
        st.error(str(error))
        return
    finally:
        motor.dispose()

    st.session_state[CLAVE_RESULTADO] = (filas, _csv_de(filas))


def _precios_vigentes(catalogo: Catalogo) -> dict[str, tuple[str, str, Decimal]]:
    """`{insumo: (tipo, unidad, precio)}` de la lista vigente, tal como espera `simular()`."""
    lista = catalogo.lista_vigente()
    return {
        precio.insumo.descripcion: (precio.insumo.tipo, precio.insumo.unidad, precio.precio)
        for precio in lista.precios
    }


def _csv_de(filas: list[tuple[str, str, str, Decimal]]) -> bytes:
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(COLUMNAS_CSV)
    for tipo, insumo, unidad, precio in filas:
        escritor.writerow([tipo, insumo, unidad, str(precio)])
    return buffer.getvalue().encode("utf-8")


def _mostrar(resultado: tuple[list[tuple[str, str, str, Decimal]], bytes] | None) -> None:
    if resultado is None:
        return

    filas, csv_bytes = resultado
    st.subheader("Lista simulada")
    if not filas:
        st.info("La simulacion no produjo ninguna fila (revise el filtro de insumos).")
        return

    tabla = DataFrame(
        [
            {"tipo": tipo, "insumo": insumo, "unidad": unidad, "precio": str(precio)}
            for tipo, insumo, unidad, precio in filas
        ],
        columns=list(COLUMNAS_CSV),
    )
    st.dataframe(tabla, hide_index=True)
    st.download_button(
        "Descargar CSV",
        data=csv_bytes,
        file_name="lista_simulada.csv",
        mime="text/csv",
    )
