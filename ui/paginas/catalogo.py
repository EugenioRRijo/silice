"""Pagina de consulta del catalogo: partidas e insumos con su precio vigente (Sesion F.1).

Solo lectura, equivalente Streamlit de `GET /partidas` y `GET /insumos` (spec F.1 §2), pero
llamando a `core.catalog.Catalogo` directo: la UI no consume la API por HTTP (decision del usuario,
2026-08-31, spec F.1 §4). No calcula ni redondea nada por su cuenta: el precio vigente es el
`Decimal` que devuelve `Catalogo`, presentado con `formatear_decimal` y
`core.verification.informe.DECIMALES_PRESENTACION`, la unica definicion de presentacion del
sistema.
"""

from __future__ import annotations

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion, crear_esquema, crear_motor
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from ui.caso import ruta_caso


def render() -> None:
    """Dos tablas de solo lectura: partidas del catalogo e insumos con su precio vigente."""
    st.caption("Partidas e insumos del catalogo, con el precio vigente de cada insumo.")

    ruta = ruta_caso()

    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            _mostrar_partidas(catalogo)
            _mostrar_insumos(catalogo)
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # Mismo criterio que `ui/paginas/actualizacion.py`: un archivo de base de datos corrupto
        # o inaccesible (`OperationalError` de `crear_esquema`) es un mensaje, no una traza cruda.
        st.error(str(error))
    finally:
        motor.dispose()


def _mostrar_partidas(catalogo: Catalogo) -> None:
    st.subheader("Partidas")
    partidas = catalogo.partidas()
    if not partidas:
        st.info("El catalogo no tiene partidas cargadas todavia.")
        return
    tabla = DataFrame(
        [
            {
                "codigo": partida.codigo,
                "descripcion": partida.descripcion,
                "unidad": partida.unidad,
                "dominio": partida.dominio,
            }
            for partida in partidas
        ]
    )
    st.dataframe(tabla, hide_index=True)


def _mostrar_insumos(catalogo: Catalogo) -> None:
    st.subheader("Insumos")
    insumos = catalogo.insumos()
    if not insumos:
        st.info("El catalogo no tiene insumos cargados todavia.")
        return

    try:
        lista = catalogo.lista_vigente()
        precios = {precio.insumo_id: precio.precio for precio in lista.precios}
    except CatalogoIncompleto:
        # Sin lista vigente, cada insumo se muestra sin precio: el catalogo puede tener partidas e
        # insumos cargados antes de que exista ninguna lista de precios (UC-01 sin UC-02 todavia).
        precios = {}

    tabla = DataFrame(
        [
            {
                "codigo": insumo.codigo,
                "tipo": insumo.tipo,
                "descripcion": insumo.descripcion,
                "unidad": insumo.unidad or "",
                "precio_vigente": (
                    formatear_decimal(precios[insumo.id], DECIMALES_PRESENTACION)
                    if insumo.id in precios
                    else ""
                ),
            }
            for insumo in insumos
        ]
    )
    st.dataframe(tabla, hide_index=True)
