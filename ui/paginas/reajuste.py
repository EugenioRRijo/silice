"""Pantalla «Reajuste de precios» (UC-18): la clausula, los periodos con lo ejecutado y su fuente,
la escalatoria y la comprobacion directa lado a lado en las dos monedas, el guardado del estudio y
su Excel. La logica vive en `ui.reajuste` (sin Streamlit); aqui solo se pinta. Avisos y marcas van
en celdas o por `ui.texto_seguro` (RV-14). Sin efectos al importarse."""

from __future__ import annotations

from datetime import date

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.budget.reajuste import COMPONENTES, EstadoEstudio, Estructura, Mecanismo
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from ui import reajuste
from ui.caso import proyecto_abierto, ruta_caso
from ui.hoja import HojaInvalida, historial_de_versiones
from ui.texto_seguro import texto_seguro

CLAVE_CALCULO = "reajuste_calculo"  # (contrato, clausula, periodos, resultado): no es de widget
CLAVE_EXCEL = "reajuste_excel"  # bytes del ultimo Excel preparado


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
    proyecto = proyecto_abierto()
    if proyecto is None:
        st.info("Abra un proyecto en la barra superior (Proyecto) para reajustar sus precios.")
        return
    motor = _motor_del_caso()
    if motor is None:
        return
    try:
        with abrir_sesion(motor) as sesion:
            versiones = historial_de_versiones(sesion, proyecto)
        if not versiones:
            st.info("El proyecto no tiene versiones guardadas: guarde la del contrato primero.")
            return
        _pintar(motor, proyecto, versiones)
    except SQLAlchemyError as error:
        st.error(f"No se pudo leer o escribir el caso: {getattr(error, 'orig', None) or error}")
    finally:
        motor.dispose()


def _clausula() -> tuple[dict[str, str], list[dict[str, str]]]:
    st.subheader("1. La clausula de reajuste (S1 §8.1, a cotejar con la Gaceta)")
    a, b, c = st.columns(3)
    inicio = a.date_input("Inicio del contrato", value=None)
    duracion = b.text_input("Duracion (meses)")
    primer_anio = c.date_input(
        "El primer año corre desde",
        value=None,
        help="Por defecto, el inicio del contrato (a cotejar).",
    )
    d, e, f = st.columns(3)
    periodicidad = d.selectbox("Periodicidad", ("mensual", "trimestral"))
    mecanismo = e.selectbox("Mecanismo", [m.value for m in Mecanismo])
    pagadero = f.selectbox(
        "Mecanismo pagadero (solo con «ambos»)",
        ["", Mecanismo.ESCALATORIA.value, Mecanismo.COMPROBACION.value],
    )
    fuente_pagadero = st.text_input("Fuente del mecanismo pagadero")
    g, h, i = st.columns(3)
    estructura = g.selectbox("Estructura", [x.value for x in Estructura])
    base = h.date_input("Mes base de los indices (I0)", value=None)
    r = i.text_input("R (fraccion no reajustable)")
    fuente_r = st.text_input("Fuente de R (si el contrato no la trae, escriba 0 y declarelo)")
    r_en_comprobacion = st.checkbox("La clausula aplica R tambien a la comprobacion (S1-R14)")
    fuente = st.text_input("Fuente de la clausula (contrato, numero, fecha)")
    responsable = st.text_input("Responsable")
    st.caption("Componentes: la serie de cada uno y, si la estructura es declarada, su peso.")
    componentes = st.data_editor(
        DataFrame({"componente": list(COMPONENTES), "serie": [""] * 3, "peso": [""] * 3}),
        hide_index=True,
        key="reajuste_componentes",
    )
    referencia = primer_anio or inicio
    campos = {
        "fecha_inicio": inicio.isoformat() if inicio else "",
        "duracion_meses": duracion,
        "fecha_referencia_primer_anio": referencia.isoformat() if referencia else "",
        "periodicidad": periodicidad,
        "mecanismo": mecanismo,
        "mecanismo_pagadero": pagadero,
        "fuente_pagadero": fuente_pagadero,
        "estructura": estructura,
        "fecha_base_indices": date(base.year, base.month, 1).isoformat() if base else "",
        "r": r,
        "fuente_r": fuente_r,
        "r_en_comprobacion": "si" if r_en_comprobacion else "no",
        "fuente": fuente,
        "responsable": responsable,
    }
    return campos, componentes.to_dict("records")


def _periodos(versiones) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    st.subheader("2. Periodos y lo ejecutado (con su fuente)")
    revaloradas = [v.codigo for v in versiones if v.motivo == "revaloracion"]
    st.caption(
        "Versiones revaloradas para la comprobacion directa: "
        + (", ".join(revaloradas) or "ninguna (la comprobacion quedara «no disponible»)")
    )
    periodos = st.data_editor(
        DataFrame({"desde": [""], "hasta": [""], "version_comprobacion": [""], "excepcion": [""]}),
        num_rows="dynamic",
        hide_index=True,
        key="reajuste_periodos",
    )
    ejecutado = st.data_editor(
        DataFrame({"periodo": ["1"], "partida": [""], "cantidad": [""], "fuente": [""]}),
        num_rows="dynamic",
        hide_index=True,
        key="reajuste_ejecutado",
    )
    st.caption("Fechas en AAAA-MM-DD. «periodo» es el numero de la fila de periodos (1, 2, ...).")
    return periodos.to_dict("records"), ejecutado.to_dict("records")


def _pintar(motor, proyecto: str, versiones) -> None:
    contrato = st.selectbox("Version del contrato", [v.codigo for v in versiones])
    campos, componentes = _clausula()
    filas_periodos, filas_ejecutado = _periodos(versiones)
    if st.button("Calcular", type="primary"):
        try:
            clausula = reajuste.clausula_desde_textos(campos, componentes)
            periodos = reajuste.periodos_desde_filas(filas_periodos, filas_ejecutado)
            with abrir_sesion(motor) as sesion:
                resultado = reajuste.calcular(
                    sesion, proyecto, contrato, clausula, periodos, fecha_calculo=date.today()
                )
        except HojaInvalida as error:
            st.error(texto_seguro(str(error)))
        else:
            st.session_state[CLAVE_CALCULO] = (contrato, clausula, periodos, resultado)
            st.session_state.pop(CLAVE_EXCEL, None)
    calculo = st.session_state.get(CLAVE_CALCULO)
    if calculo is None or calculo[0] != contrato:
        return
    _, clausula, periodos, resultado = calculo
    st.subheader("3. Escalatoria y comprobacion, lado a lado")
    st.dataframe(
        DataFrame(reajuste.filas_lado_a_lado(resultado), columns=list(reajuste.COLUMNAS_REAJUSTE)),
        hide_index=True,
        width="stretch",
    )
    for aviso in resultado.avisos:
        st.warning(texto_seguro(aviso))
    if resultado.estado is EstadoEstudio.PARCIAL:
        st.info(
            f"El ultimo periodo aun no cierra: el estudio se guardara «parcial al corte» al "
            f"{resultado.fecha_corte:%d/%m/%Y} y se reemplaza al cerrar el mes (S1-R21)."
        )
    _guardar(motor, proyecto, contrato, clausula, periodos, resultado)
    _excel(motor, proyecto, contrato, resultado, periodos)


def _guardar(motor, proyecto, contrato, clausula, periodos, resultado) -> None:
    st.subheader("4. Guardar el estudio")
    with abrir_sesion(motor) as sesion:
        parciales = reajuste.parciales_por_reemplazar(sesion, proyecto, contrato)
    fuente = st.text_input("Fuente del estudio", key="reajuste_fuente")
    responsable = st.text_input("Responsable del estudio", key="reajuste_responsable")
    reemplaza = None
    if parciales and resultado.estado is EstadoEstudio.CERRADO:
        elegido = st.selectbox(
            "Reemplaza al estudio parcial",
            [None, *parciales],
            format_func=lambda x: (
                "ninguno" if x is None else f"{x[0]} (calculado el {x[1]:%d/%m/%Y})"
            ),
        )
        reemplaza = None if elegido is None else elegido[0]
    if st.button("Guardar estudio"):
        try:
            with abrir_sesion(motor) as sesion:
                estudio = reajuste.guardar(
                    sesion,
                    proyecto,
                    contrato,
                    clausula,
                    periodos,
                    fecha_calculo=date.today(),
                    fuente=fuente,
                    responsable=responsable,
                    reemplaza_a=reemplaza,
                )
        except HojaInvalida as error:
            st.error(texto_seguro(str(error)))
        else:
            st.success(f"Estudio {estudio} guardado ({resultado.estado.value}).")


def _excel(motor, proyecto, contrato, resultado, periodos) -> None:
    if st.button("Preparar Excel"):
        try:
            with abrir_sesion(motor) as sesion:
                st.session_state[CLAVE_EXCEL] = reajuste.excel_en_bytes(
                    sesion, proyecto, contrato, resultado, periodos
                )
        except (HojaInvalida, ValueError) as error:
            st.error(texto_seguro(f"No se pudo preparar el Excel: {error}"))
    contenido = st.session_state.get(CLAVE_EXCEL)
    if contenido is not None:
        st.download_button("Descargar Excel", contenido, file_name=f"reajuste_{contrato}.xlsx")
