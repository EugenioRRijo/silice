"""Pantalla de Inicio (sprint de UI, UC-12; RF-36 a RF-40).

La puerta de entrada: que caso esta abierto, que hacer si esta vacio y que recorridos hay. Solo
pinta; lo que decide vive en `ui/caso.py` y `ui/recorridos.py`. El titulo, el estado del caso en
la barra lateral y el boton «Siguiente» los pinta el marco de `ui/app.py`.

El estado vacio ofrece cargar el caso de demostracion con `scripts.seed_demo.main`, siempre sin el
flag de reinicio, y solo cuando el caso no tiene partidas (una base con insumos o listas de
precios pero sin partidas cuenta como vacia): nunca borra nada, y lo que ya hubiera en la base se
conserva junto a lo sembrado.
"""

from __future__ import annotations

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from scripts.seed_demo import main as sembrar_demostracion
from ui.caso import (
    EstadoCaso,
    argv_siembra,
    estado_caso,
    fijar_caso,
    fijar_recorrido,
    recorrido_activo,
    resumen_caso,
    ruta_caso,
)
from ui.recorridos import RECORRIDOS, recorrido_por_nombre

ROTULO_ARCHIVO = "Archivo del caso (SQLite)"
ROTULO_ABRIR = "Abrir este caso"
ROTULO_SEMBRAR = "Cargar el caso de demostracion"
ROTULO_RECORRIDO = "Que quiere hacer?"


def render() -> None:
    """El caso abierto, su estado vacio si lo tiene y los tres recorridos."""
    st.caption(
        "Esta aplicacion arma, costea y audita analisis de precios unitarios. Elija el caso con "
        "que va a trabajar y lo que quiere hacer: cada pantalla le indicara el paso siguiente."
    )
    _elegir_caso()
    _estado(estado_caso(ruta_caso()))
    _elegir_recorrido()


def _elegir_caso() -> None:
    st.subheader("1. El caso con que va a trabajar")
    texto = st.text_input(ROTULO_ARCHIVO, value=str(ruta_caso()))
    if st.button(ROTULO_ABRIR):
        try:
            fijar_caso(texto)
        except ValueError as error:
            st.error(str(error))
        else:
            st.rerun()


def _estado(estado: EstadoCaso) -> None:
    if estado.error is not None:
        st.error(f"{resumen_caso(estado)}. Revise la ruta o abra otro archivo.")
        return
    if not estado.vacio:
        st.success(f"Caso listo: {resumen_caso(estado)}.")
        return
    st.info(
        f"El caso {estado.ruta} no existe todavia o no tiene partidas. Puede cargar el caso de "
        "demostracion —la linea base de la clinica y una linea de agua potable didactica, con su "
        "presupuesto auditado— o abrir otro archivo arriba."
    )
    if st.button(ROTULO_SEMBRAR, type="primary"):
        with st.spinner("Cargando la linea base, la demostracion y su presupuesto auditado..."):
            try:
                sembrar_demostracion(argv_siembra(estado.ruta))
            except (LookupError, ValueError, ArithmeticError, OSError, SQLAlchemyError) as error:
                st.error(f"No se pudo cargar el caso de demostracion: {error}")
                return
        st.rerun()


def _elegir_recorrido() -> None:
    st.subheader("2. Que quiere hacer")
    nombres = [recorrido.nombre for recorrido in RECORRIDOS]
    activo = recorrido_activo()
    eleccion = st.radio(
        ROTULO_RECORRIDO,
        nombres,
        index=nombres.index(activo) if activo in nombres else None,
        captions=[recorrido.proposito for recorrido in RECORRIDOS],
    )
    if eleccion is not None and eleccion != activo:
        fijar_recorrido(eleccion)
        st.rerun()
    recorrido = recorrido_por_nombre(eleccion)
    if recorrido is None:
        return
    for numero, paso in enumerate(recorrido.pasos, start=1):
        st.markdown(f"**{numero}. {paso.titulo}.** {paso.que_hacer}")
    st.caption("Pulse «Siguiente» al pie de la pagina para ir al primer paso.")
