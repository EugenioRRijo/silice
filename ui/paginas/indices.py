"""Pantalla «Indices del BCV» (UC-17 1-3): leer un archivo del BCV sin escribir nada, revisar el
informe previo y confirmar. La logica vive en `ui.indices` (sin Streamlit); aqui solo se pinta. Los
nombres de hoja, las etiquetas y los motivos vienen del archivo: son texto ajeno y van en celdas o
por `ui.texto_seguro`, nunca como Markdown interpretado (RV-14). Sin efectos al importarse."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import abrir_sesion, crear_motor
from core.catalog.indices import PERIODICIDADES, UNIDAD_INDICE_BS, DefinicionSerie
from operacion.base_datos import ErrorDeBase, preparar_base
from seguridad.permisos import Accion
from ui import indices
from ui import sesion as ui_sesion
from ui.caso import ruta_caso
from ui.subidas import guardar_subida
from ui.texto_seguro import texto_seguro

CLAVE_INFORME = "indices_informe"  # (tipo, InformeImportacion) leido: no es clave de ningun widget
ROTULOS_TIPO = {
    "tasa": "Tasa de referencia del USD (.xls trimestral)",
    "inpc": "INPC (.xls mensual)",
    "csv": "Una serie en CSV canonico (serie, fecha, valor, provisional, fuente)",
}


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
        "Importe la tasa de referencia del BCV, el INPC o una serie en CSV. «Leer» no escribe "
        "nada: muestra lo que se importaria. «Confirmar» guarda los valores con la huella del "
        "archivo; el mismo archivo dos veces no escribe nada."
    )
    with st.form("indices_leer"):
        tipo = st.selectbox("Que archivo es", indices.TIPOS, format_func=ROTULOS_TIPO.get)
        archivo = st.file_uploader("Archivo", type=["xls", "xlsx", "csv"])
        fuente = st.text_input("Direccion de la pagina del BCV de donde lo bajo")
        descarga = st.date_input("Fecha de descarga", value=date.today())
        leer = st.form_submit_button("Leer")
    if leer:
        _leer(tipo, archivo, fuente, descarga)
    leido = st.session_state.get(CLAVE_INFORME)
    if leido is not None:
        _pintar(*leido)


def _leer(tipo: str, archivo, fuente: str, descarga: date) -> None:
    st.session_state.pop(CLAVE_INFORME, None)
    if archivo is None:
        st.error("Elija el archivo que bajo del BCV.")
        return
    try:
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = guardar_subida(carpeta, archivo)
            informe = indices.leer(Path(ruta), tipo, fuente=fuente, fecha_descarga=descarga)
    except ValueError as error:  # `FormatoNoReconocido` es `ValueError` (UC-17 2a)
        st.error(texto_seguro(f"No se importo nada: {error}"))
        return
    st.session_state[CLAVE_INFORME] = (tipo, informe)


def _rango(serie) -> tuple[str, str]:
    fechas = [valor.fecha for valor in serie.valores]
    return (min(fechas).isoformat(), max(fechas).isoformat()) if fechas else ("", "")


def _pintar(tipo: str, informe) -> None:
    st.subheader("Informe previo (todavia no se guardo nada)")
    a, b, c = st.columns(3)
    a.metric("Filas leidas", informe.filas_leidas)
    b.metric("Rechazadas", informe.filas_rechazadas)
    c.metric("Provisionales", informe.provisionales)
    st.dataframe(
        DataFrame(
            [
                {
                    "Serie": serie.clave,
                    "Valores": len(serie.valores),
                    "Desde": _rango(serie)[0],
                    "Hasta": _rango(serie)[1],
                }
                for serie in informe.series
            ],
            columns=["Serie", "Valores", "Desde", "Hasta"],
        ),
        hide_index=True,
        width="stretch",
    )
    if informe.rechazos:
        st.dataframe(
            DataFrame(indices.filas_del_informe(informe)), hide_index=True, width="stretch"
        )
    for advertencia in informe.advertencias:
        st.text(advertencia)
    definiciones = _definiciones_csv(informe) if tipo == "csv" else None
    responsable = st.text_input("Responsable de la importacion")
    if st.button("Confirmar la importacion", type="primary"):
        _confirmar(informe, responsable, definiciones)


def _definiciones_csv(informe) -> dict[str, DefinicionSerie]:
    """Una serie del CSV canonico no trae nombre, organismo, unidad ni periodicidad: se declaran."""
    definiciones = {}
    for serie in informe.series:
        st.markdown(f"**Serie {texto_seguro(serie.clave)}**")
        a, b, c, d = st.columns(4)
        nombre = a.text_input("Nombre", value=serie.clave, key=f"indices_nombre_{serie.clave}")
        organismo = b.text_input("Organismo", key=f"indices_organismo_{serie.clave}")
        unidad = c.text_input("Unidad", value=UNIDAD_INDICE_BS, key=f"indices_unidad_{serie.clave}")
        periodicidad = d.selectbox(
            "Periodicidad", PERIODICIDADES, index=1, key=f"indices_periodicidad_{serie.clave}"
        )
        if nombre.strip() and organismo.strip() and unidad.strip():
            definiciones[serie.clave] = DefinicionSerie(
                serie.clave, nombre.strip(), organismo.strip(), unidad.strip(), periodicidad
            )
    return definiciones


def _confirmar(informe, responsable: str, definiciones) -> None:
    motor = _motor_del_caso()
    if motor is None:
        return
    try:
        with abrir_sesion(motor) as sesion:
            mensajes = indices.confirmar(
                sesion, informe, responsable=responsable, definiciones_csv=definiciones
            )
    except ValueError as error:
        st.error(texto_seguro(f"No se guardo nada: {error}"))
        return
    except SQLAlchemyError as error:
        st.error(f"No se pudo escribir en el caso: {getattr(error, 'orig', None) or error}")
        return
    finally:
        motor.dispose()
    st.session_state.pop(CLAVE_INFORME, None)
    for mensaje in mensajes:
        st.success(texto_seguro(mensaje))
