"""Pantalla «Precios de la empresa» (UC-17 4-5): cargar la referencia MaPreX en Bs, crear la lista
de una empresa sobre una lista base y ver sus hallazgos de R11 y R12 a una fecha de evaluacion. La
logica vive en `ui.precios_empresa` (sin Streamlit); aqui solo se pinta. Las descripciones de una
lista importada son texto ajeno: van en celdas (RV-14). El script de MaPreX se importa dentro de la
accion, no al cargar esta pagina (RV-25). Sin efectos al importarse."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import abrir_sesion, crear_motor
from core.catalog.moneda import MONEDAS
from operacion.base_datos import ErrorDeBase, preparar_base
from seguridad.permisos import Accion
from ui import atipicos, precios_empresa
from ui import sesion as ui_sesion
from ui.caso import ruta_caso
from ui.subidas import guardar_subida
from ui.texto_seguro import texto_seguro


def _motor_del_caso():
    """El motor del caso abierto, ya en `head` (RV-5); `None` si no se puede preparar."""
    ruta = ruta_caso()
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(str(error))
        return None
    return crear_motor(f"sqlite:///{ruta.as_posix()}")


def render() -> None:
    ui_sesion.exigir(Accion.ADMINISTRAR_PRECIOS)
    st.caption(
        "La lista de su empresa: una copia de la lista base con sus precios encima, cada uno con "
        "su fecha y su fuente. No cambia la valoracion de ningun proyecto que no la use."
    )
    motor = _motor_del_caso()
    if motor is None:
        return
    try:
        _referencia(motor)
        _crear(motor)
        _hallazgos(motor)
    except SQLAlchemyError as error:
        st.error(f"No se pudo leer o escribir el caso: {getattr(error, 'orig', None) or error}")
    finally:
        motor.dispose()


def _referencia(motor) -> None:
    st.subheader("1. La referencia MaPreX en bolivares")
    if st.button("Cargar la referencia MaPreX en Bs"):
        try:
            with abrir_sesion(motor) as sesion:
                st.success(precios_empresa.cargar_referencia_maprex(sesion))
        except (ValueError, OSError) as error:
            st.error(texto_seguro(f"No se cargo la referencia: {error}"))


def _crear(motor) -> None:
    st.subheader("2. La lista de la empresa")
    with abrir_sesion(motor) as sesion:
        bases = precios_empresa.listas_base(sesion)
    if not bases:
        st.info("El caso no tiene listas de precios: cargue una en Actualizar precios.")
        return
    with st.form("precios_empresa_crear"):
        a, b = st.columns(2)
        empresa = a.text_input("Empresa (nombre)")
        rif = b.text_input("RIF")
        base = st.selectbox("Lista base", bases, format_func=lambda x: f"{x[1]} ({x[2]})")
        c, d = st.columns(2)
        moneda = c.selectbox(
            "Moneda de la lista", MONEDAS, index=None, placeholder="Elija Bs o USD"
        )
        fecha = d.date_input("Fecha de la lista", value=date.today())
        fuente = st.text_input("Fuente de la lista (de donde salen estos precios)")
        nombre = st.text_input("Nombre de la lista (opcional)")
        archivo = st.file_uploader("Archivo de precios (CSV o XLSX)", type=["csv", "xlsx"])
        enviar = st.form_submit_button("Crear la lista de la empresa")
    if not enviar:
        return
    if moneda is None or archivo is None:
        st.error(
            "Elija la moneda de la lista y el archivo de precios: no tienen valor por defecto."
        )
        return
    try:
        with tempfile.TemporaryDirectory() as carpeta, abrir_sesion(motor) as sesion:
            ruta = guardar_subida(carpeta, archivo)
            resumen = precios_empresa.crear_lista(
                sesion,
                Path(ruta),
                empresa_nombre=empresa,
                empresa_rif=rif,
                base_id=base[0],
                moneda=moneda,
                fecha=fecha,
                fuente=fuente,
                nombre=nombre,
            )
    except ValueError as error:
        st.error(texto_seguro(f"No se creo la lista: {error}"))
        return
    st.success(
        texto_seguro(f"Lista «{resumen.nombre}» creada con {resumen.propios} precios propios.")
    )
    if resumen.desconocidos:
        st.warning("Estos insumos no estan en el catalogo y no entraron a la lista (UC-17 4a):")
        st.dataframe(DataFrame({"Insumo": list(resumen.desconocidos)}), hide_index=True)


def _hallazgos(motor) -> None:
    st.subheader("3. Precios vencidos o fuera de rango (R11 y R12)")
    with abrir_sesion(motor) as sesion:
        listas = precios_empresa.listas_de_empresa(sesion)
    if not listas:
        st.info("Todavia no hay listas de empresa en este caso.")
        return
    a, b = st.columns(2)
    lista = a.selectbox("Lista", listas, format_func=lambda x: x[1])
    evaluacion = b.date_input("Fecha de evaluacion", value=date.today())
    with abrir_sesion(motor) as sesion:
        filas = precios_empresa.hallazgos_de_lista(sesion, lista[0], evaluacion)
    st.caption("Sin version, el impacto es por unidad de insumo. Nada de esto se guarda.")
    st.dataframe(
        DataFrame(filas, columns=list(precios_empresa.COLUMNAS_HALLAZGOS)),
        hide_index=True,
        width="stretch",
    )
    _atipicos(motor, lista[0])


def _atipicos(motor, lista_id: int) -> None:
    """RF-100: las variaciones atipicas de precio de los insumos de la lista elegida. Solo lee:
    cada hallazgo es una ADVERTENCIA y no impide nada. Sin el extra `ml` lo dice y no busca."""
    if not st.button(atipicos.ROTULO_BOTON, key="precios_empresa_atipicos"):
        return
    hallazgos = []
    with abrir_sesion(motor) as sesion:
        for codigo in atipicos.codigos_de_la_lista(sesion, lista_id):
            hallados = atipicos.atipicos_del_insumo(sesion, codigo)
            if hallados is None:
                st.info(atipicos.AVISO_SIN_ML)
                return
            hallazgos.extend(hallados)
    if not hallazgos:
        st.success(atipicos.MENSAJE_NADA_ATIPICO)
    for hallazgo in hallazgos:
        st.warning(texto_seguro(hallazgo.descripcion))
