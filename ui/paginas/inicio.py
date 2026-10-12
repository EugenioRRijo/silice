"""Pantalla de Inicio (sprint de UI, UC-12; RF-36 a RF-40; Silice 0.6.0, RV-5).

La puerta de entrada: que caso esta abierto, que hacer si esta vacio y que recorridos hay. Desde la
0.6.0 el caso se elige de la **lista** de la carpeta de casos, se crea con un nombre o se sube un
`.db`; ya no hay campo de texto con la ruta (spec S5 §6.6). Todo caso se abre con `preparar_base`:
al entrar, el caso abierto se lleva a `head` (con respaldo previo si hace falta). «Cambiar de caso»
queda tras `ui.caso.puede_cambiar_de_caso` (gancho para los roles de S3).

El estado vacio ofrece cargar el caso de demostracion con `scripts.seed_demo.main`, siempre sin el
flag de reinicio, y solo cuando el caso no tiene partidas: nunca borra nada. Antes de sembrar, el
caso se crea en `head` por `preparar_base`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from operacion.base_datos import ErrorDeBase, crear_caso, listar_casos, preparar_base, subir_caso
from operacion.config import BASE_ANTERIOR, carpeta_casos
from scripts.seed_demo import main as sembrar_demostracion
from ui import caso
from ui.caso import (
    SIN_PERMISO_DE_CAMBIO,
    EstadoCaso,
    abrir_caso,
    argv_siembra,
    estado_caso,
    fijar_caso,
    fijar_recorrido,
    recorrido_activo,
    resumen_caso,
    ruta_caso,
)
from ui.recorridos import RECORRIDOS, recorrido_por_nombre

ROTULO_CASO = "Casos de la carpeta de datos"
ROTULO_ABRIR = "Abrir este caso"
ROTULO_NUEVO = "Nombre del caso nuevo"
ROTULO_CREAR = "Crear el caso"
ROTULO_SUBIR = "Subir un caso (.db)"
ROTULO_GUARDAR_SUBIDA = "Agregar el caso subido"
ROTULO_SEMBRAR = "Cargar el caso de demostracion"
ROTULO_RECORRIDO = "Que quiere hacer?"
PREFIJO_CASO_ABIERTO = "Caso abierto: "
MENSAJE_BASE_ANTERIOR = (
    "Hay una base de una version anterior en data/apu.db. Para seguir trabajando con ella, "
    "adoptela (se copia; el original no se toca): "
    "uv run python -m operacion adoptar data/apu.db --nombre silice"
)


def render() -> None:
    """El caso abierto, su estado vacio si lo tiene y los recorridos."""
    st.caption(
        "Esta aplicacion arma, costea y audita analisis de precios unitarios. Elija el caso con "
        "que va a trabajar y lo que quiere hacer: cada pantalla le indicara el paso siguiente."
    )
    _preparar_abierto()
    _elegir_caso()
    _estado(estado_caso(ruta_caso()))
    _elegir_recorrido()


def _preparar_abierto() -> None:
    """El caso abierto se lleva a `head` al entrar; uno que no existe no se crea."""
    ruta = ruta_caso()
    if not ruta.exists():
        return
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(str(error))


def _hacer(accion: Callable[[], object]) -> None:
    try:
        accion()
    except (ErrorDeBase, PermissionError) as error:
        st.error(str(error))
    else:
        st.rerun()


def _fijar(ruta: Path) -> Path:
    fijar_caso(ruta)
    return ruta


def _elegir_caso() -> None:
    st.subheader("1. El caso con que va a trabajar")
    st.caption(f"{PREFIJO_CASO_ABIERTO}{ruta_caso()}")
    if not caso.puede_cambiar_de_caso():
        st.info(SIN_PERMISO_DE_CAMBIO)
        return
    carpeta = carpeta_casos()
    nombres = [ruta.name for ruta in listar_casos(carpeta)]
    if nombres:
        eleccion = st.selectbox(ROTULO_CASO, nombres, index=None, placeholder="Elija un caso")
        if st.button(ROTULO_ABRIR) and eleccion is not None:
            _hacer(lambda: abrir_caso(str(eleccion), carpeta))
    else:
        st.info(f"Todavia no hay casos en {carpeta}. Cree uno o suba un archivo.")
        if BASE_ANTERIOR.exists():
            st.info(MENSAJE_BASE_ANTERIOR)
    with st.expander("Crear o subir un caso"):
        nombre = st.text_input(ROTULO_NUEVO, value="")
        if st.button(ROTULO_CREAR):
            _hacer(lambda: _fijar(crear_caso(nombre, carpeta).ruta))
        archivo = st.file_uploader(ROTULO_SUBIR, type=["db"])
        if archivo is not None and st.button(ROTULO_GUARDAR_SUBIDA):
            _hacer(lambda: _fijar(subir_caso(archivo.name, archivo.getvalue(), carpeta).ruta))


def _estado(estado: EstadoCaso) -> None:
    if estado.error is not None:
        st.error(f"{resumen_caso(estado)}. Revise el caso o abra otro.")
        return
    if not estado.vacio:
        st.success(f"Caso listo: {resumen_caso(estado)}.")
        return
    st.info(
        f"El caso {estado.ruta} no existe todavia o no tiene partidas. Puede cargar el caso de "
        "demostracion —la linea base de la clinica y una linea de agua potable didactica, con su "
        "presupuesto auditado— o abrir otro caso arriba."
    )
    if st.button(ROTULO_SEMBRAR, type="primary"):
        with st.spinner("Cargando la linea base, la demostracion y su presupuesto auditado..."):
            try:
                preparar_base(estado.ruta)
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
