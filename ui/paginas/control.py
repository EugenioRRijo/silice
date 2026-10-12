"""Pantalla «Control de obra» (UC-19 y UC-20; spec S2 §5.5).

Cinco pestañas sobre la línea base de control del proyecto abierto:

* **Línea base**: la vigente (versión, perspectiva, calendario), su declaración y los parámetros
  de control con su naturaleza visible (SUPUESTO_DECLARADO, salvo la penalización del contrato);
* **Valuaciones**: las guardadas en solo lectura con su fecha de registro y su Estado (el peor
  hallazgo de R13-R14); registrar una a mano, importar un XLSX con informe previo, anular con
  fuente y anotar costos incurridos;
* **Valor ganado**: la tabla de §4.2 y la separación del desvío en plazo, precio y consumo, cada
  monto en las dos monedas con la tasa del corte (S1), y la curva PV/EV/AC;
* **Alertas y reproyección**: AL-1 a AL-6, el término por los dos métodos, el EAC, el punto de
  equilibrio proyectado con los estudios de reajuste que suma y el plan reproyectado. Se calculan
  **siempre**, sin que se pidan;
* **Recuperación**: «Calcular opciones» (a pedido) y elegir una, con fuente y responsable.

Toda la lógica vive en `ui.control` (sin Streamlit); aquí solo se pinta. Los textos que vienen de
fuera (inspector, observación, fuente de un XLSX) van en celdas o por `ui.texto_seguro`, nunca como
Markdown interpretado (RV-14). El caso se abre con `preparar_base` (RV-5). Sin efectos al
importarse.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from seguridad.permisos import Accion
from ui import control
from ui import sesion as ui_sesion
from ui.caso import ACCION_REGISTRAR_VALUACION, proyecto_abierto, ruta_caso, tomar_accion
from ui.subidas import guardar_subida
from ui.texto_seguro import texto_seguro

PESTANAS = ("Línea base", "Valuaciones", "Valor ganado", "Alertas y reproyección", "Recuperación")
CLAVE_PESTANA = "control_pestana"
CLAVE_OPCIONES = "control_opciones"  # (proyecto, corte, opciones): no es clave de ningún widget
CLAVE_MENSAJE = "control_mensaje"  # (tipo, texto) del último intento de escribir
CLAVE_LECTURA = "control_lectura"  # (nombre, LecturaControl) del XLSX leído
PERSPECTIVAS = ("costo", "precio")


def _motor_del_caso():
    """El motor del caso abierto, ya en `head` (RV-5); `None` si no se puede preparar."""
    ruta = ruta_caso()
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(texto_seguro(str(error)))
        return None
    return crear_motor(f"sqlite:///{ruta.as_posix()}")


def _mensaje(tipo: str, texto: str) -> None:
    st.session_state[CLAVE_MENSAJE] = (tipo, texto)


def _mostrar_mensaje() -> None:
    pendiente = st.session_state.pop(CLAVE_MENSAJE, None)
    if pendiente is not None:
        tipo, texto = pendiente
        {"error": st.error, "success": st.success}.get(tipo, st.info)(texto)


def _intentar(accion, exito: str) -> bool:
    """Corre `accion`; deja el resultado en el mensaje de la pantalla. True si salió bien."""
    try:
        accion()
    except control.ControlInvalido as error:
        _mensaje("error", texto_seguro(str(error)))
        return False
    _mensaje("success", exito)
    return True


def _tabla(filas: list[dict[str, str]], columnas: tuple[str, ...]) -> None:
    st.dataframe(DataFrame(filas, columns=list(columnas)), hide_index=True, width="stretch")


def render() -> None:
    ui_sesion.exigir(Accion.CONTROL_DE_OBRA)
    proyecto = proyecto_abierto()
    if proyecto is None:
        st.info("Abra un proyecto en la barra superior (Proyecto) para controlar su obra.")
        return
    motor = _motor_del_caso()
    if motor is None:
        return
    try:
        with abrir_sesion(motor) as sesion:
            _pintar(sesion, proyecto)
    except SQLAlchemyError as error:
        detalle = getattr(error, "orig", error)
        st.error(texto_seguro(f"No se pudo leer o escribir el caso: {detalle}"))
    finally:
        motor.dispose()


def _pintar(sesion, proyecto: str) -> None:
    catalogo = Catalogo(sesion)
    if tomar_accion() == ACCION_REGISTRAR_VALUACION:
        st.session_state[CLAVE_PESTANA] = PESTANAS[1]
    _mostrar_mensaje()
    st.session_state.setdefault(CLAVE_PESTANA, PESTANAS[0])
    pestana = st.segmented_control(
        "Seccion", PESTANAS, key=CLAVE_PESTANA, label_visibility="collapsed"
    )
    pestana = pestana or PESTANAS[0]
    if pestana == PESTANAS[0]:
        _linea_base(sesion, proyecto)
    elif pestana == PESTANAS[1]:
        _valuaciones(sesion, proyecto, catalogo)
    elif not control.tiene_linea_base(sesion, proyecto):
        st.info("Declare primero la linea base de control (pestana Línea base).")
    elif not control.hay_valuaciones(sesion, proyecto):
        st.info("Registre la primera valuacion (pestana Valuaciones) para ver el control.")
    else:
        resultado = _calcular(sesion, proyecto, catalogo)
        if resultado is None:
            return
        if pestana == PESTANAS[2]:
            _valor_ganado(sesion, resultado)
        elif pestana == PESTANAS[3]:
            _alertas_y_reproyeccion(resultado)
        else:
            _recuperacion(sesion, proyecto, catalogo, resultado)


# --- pestaña Línea base ---------------------------------------------------------------------------


def _linea_base(sesion, proyecto: str) -> None:
    descripcion = control.describir_linea_base(sesion, proyecto)
    if descripcion is None:
        st.info("El proyecto no tiene linea base de control. Declarela abajo.")
    else:
        st.markdown(f"**Linea base vigente**: {texto_seguro(descripcion)}.")
    with st.expander("Declarar una linea base", expanded=descripcion is None):
        versiones = control.versiones_para_la_linea_base(sesion, proyecto)
        version = st.selectbox("Version del contrato", versiones, key="control_lb_version")
        a, b, c = st.columns(3)
        desde = a.text_input("Vigente desde (AAAA-MM-DD)", key="control_lb_desde")
        perspectiva = b.selectbox(
            "Perspectiva",
            PERSPECTIVAS,
            key="control_lb_perspectiva",
            help="costo: quien arma (contratista); precio: quien revisa (contratante).",
        )
        inicio = c.text_input("Inicio de obra (AAAA-MM-DD)", key="control_lb_inicio")
        d, e = st.columns(2)
        dias = d.text_input("Dias habiles por periodo", value="5", key="control_lb_dias")
        feriados = e.text_area("Feriados (AAAA-MM-DD, separados por comas)", key="control_lb_fer")
        fuente = st.text_input("Fuente de la linea base", key="control_lb_fuente")
        responsable = st.text_input("Responsable", key="control_lb_responsable")
        if st.button("Declarar linea base", key="control_lb_declarar") and _intentar(
            lambda: control.declarar_linea_base(
                sesion,
                proyecto,
                version,
                desde=desde,
                perspectiva=perspectiva,
                inicio=inicio,
                dias_por_periodo=dias,
                feriados=feriados,
                fuente=fuente,
                responsable=responsable,
            ),
            "Linea base declarada.",
        ):
            st.rerun()
        _mostrar_mensaje()
    _parametros(sesion, proyecto)


def _parametros(sesion, proyecto: str) -> None:
    st.subheader("Parametros de control")
    st.caption(
        "Umbrales de las alertas y supuestos de las opciones. Son SUPUESTO_DECLARADO, sin fuente "
        "normativa, salvo la penalizacion (dato del contrato). Cambiarlos deja su registro."
    )
    filas = control.filas_de_parametros(control.parametros_actuales(sesion, proyecto))
    editadas = st.data_editor(
        DataFrame(filas, columns=list(control.COLUMNAS_PARAMETROS)),
        hide_index=True,
        disabled=["Parametro", "Que es", "Naturaleza"],
        key="control_parametros",
        width="stretch",
    )
    fuente = st.text_input("Fuente del cambio de parametros", key="control_par_fuente")
    responsable = st.text_input("Responsable del cambio", key="control_par_responsable")
    if st.button("Guardar parametros", key="control_par_guardar"):
        try:
            cambiados = control.guardar_los_parametros(
                sesion,
                proyecto,
                editadas.to_dict("records"),
                fuente=fuente,
                responsable=responsable,
            )
        except control.ControlInvalido as error:
            st.error(texto_seguro(str(error)))
        else:
            st.success(f"{cambiados} parametro(s) cambiado(s).")


# --- pestaña Valuaciones --------------------------------------------------------------------------


def _valuaciones(sesion, proyecto: str, catalogo: Catalogo) -> None:
    if not control.tiene_linea_base(sesion, proyecto):
        st.info("Declare primero la linea base de control (pestana Línea base).")
        return
    if control.hay_valuaciones(sesion, proyecto):
        try:
            resultado = control.calcular_el_control(sesion, proyecto, catalogo)
        except control.ControlInvalido as error:
            st.error(texto_seguro(str(error)))
        else:
            st.subheader("Valuaciones registradas (cuentan desde su registro)")
            _tabla(control.filas_de_valuaciones(resultado), control.COLUMNAS_VALUACIONES)
            st.caption(
                "Una valuacion registrada cuenta desde su registro; solo anularla la saca del "
                "calculo (S2-R14). Si el cliente no la aprueba, anulela."
            )
    else:
        st.info("Aun no hay valuaciones registradas.")
    _registrar(sesion, proyecto, catalogo)
    _importar(sesion, proyecto)
    _anular(sesion, proyecto)
    _costo(sesion, proyecto)


def _registrar(sesion, proyecto: str, catalogo: Catalogo) -> None:
    with st.expander("Registrar una valuacion", expanded=True):
        a, b, c = st.columns(3)
        numero = a.text_input("Numero", key="control_v_numero")
        desde = b.text_input("Periodo desde (AAAA-MM-DD)", key="control_v_desde")
        hasta = c.text_input("Periodo hasta (AAAA-MM-DD)", key="control_v_hasta")
        d, e = st.columns(2)
        fecha = d.text_input("Fecha de la valuacion (AAAA-MM-DD)", key="control_v_fecha")
        inspector = e.text_input("Inspector", key="control_v_inspector")
        editadas = st.data_editor(
            DataFrame({c: [""] for c in control.COLUMNAS_LINEAS}),
            num_rows="dynamic",
            hide_index=True,
            key="control_v_lineas",
            width="stretch",
        )
        fuente = st.text_input("Fuente (acta, oficio)", key="control_v_fuente")
        responsable = st.text_input("Responsable", key="control_v_responsable")
        if st.button("Registrar y controlar", type="primary", key="control_v_registrar"):
            try:
                resultado = control.registrar_y_controlar(
                    sesion,
                    proyecto,
                    catalogo,
                    numero=numero,
                    desde=desde,
                    hasta=hasta,
                    fecha=fecha,
                    inspector=inspector,
                    filas=editadas.to_dict("records"),
                    fuente=fuente,
                    responsable=responsable,
                )
            except control.ControlInvalido as error:
                st.error(texto_seguro(str(error)))
            else:
                graves = sum(1 for h in resultado.informe.hallazgos if h.severidad.name == "ERROR")
                _mensaje(
                    "success",
                    f"Valuacion registrada: corte {resultado.instantanea.corte.isoformat()}, "
                    f"{len(resultado.informe.hallazgos)} hallazgo(s) de R13-R14 ({graves} ERROR).",
                )
                st.rerun()


def _importar(sesion, proyecto: str) -> None:
    with st.expander("Importar valuaciones de un XLSX"):
        st.caption(
            "Hojas Valuaciones (numero, desde, hasta, fecha, inspector), Lineas (numero, "
            "codigo_partida, cantidad, fecha_medicion, observacion) y Costos (opcional). Un "
            "archivo malformado se rechaza entero."
        )
        subida = st.file_uploader("Archivo .xlsx", type=["xlsx"], key="control_x_archivo")
        if subida is not None:
            with tempfile.TemporaryDirectory() as carpeta:
                ruta = guardar_subida(subida, Path(carpeta))
                try:
                    st.session_state[CLAVE_LECTURA] = (subida.name, control.leer_excel(ruta))
                except control.ControlInvalido as error:
                    st.session_state.pop(CLAVE_LECTURA, None)
                    st.error(texto_seguro(str(error)))
        leida = st.session_state.get(CLAVE_LECTURA)
        if leida is None:
            return
        nombre, lectura = leida
        st.markdown(f"Informe previo de **{texto_seguro(nombre)}**:")
        for linea in lectura.informe:
            st.markdown(f"- {texto_seguro(linea)}")
        fuente = st.text_input("Fuente de la importacion", key="control_x_fuente")
        responsable = st.text_input("Responsable de la importacion", key="control_x_responsable")
        if st.button("Importar", key="control_x_importar"):
            try:
                cuantas = control.importar_excel(
                    sesion, proyecto, lectura, fuente=fuente, responsable=responsable
                )
            except control.ControlInvalido as error:
                st.error(texto_seguro(str(error)))
            else:
                st.session_state.pop(CLAVE_LECTURA, None)
                _mensaje("success", f"{cuantas} valuacion(es) importada(s).")
                st.rerun()


def _anular(sesion, proyecto: str) -> None:
    opciones = control.valuaciones_para_anular(sesion, proyecto)
    if not opciones:
        return
    with st.expander("Anular una valuacion"):
        rotulos = {rotulo: id_ for id_, rotulo in opciones}
        elegida = st.selectbox("Valuacion", list(rotulos), key="control_a_valuacion")
        motivo = st.text_input("Motivo", key="control_a_motivo")
        responsable = st.text_input("Responsable de la anulacion", key="control_a_responsable")
        if st.button("Anular", key="control_a_anular") and _intentar(
            lambda: control.anular(
                sesion, rotulos[elegida], motivo=motivo, responsable=responsable
            ),
            "Valuacion anulada: se conserva y ya no cuenta.",
        ):
            st.rerun()
        _mostrar_mensaje()


def _costo(sesion, proyecto: str) -> None:
    with st.expander("Anotar un costo incurrido"):
        a, b, c = st.columns(3)
        monto = a.text_input("Monto", key="control_c_monto")
        moneda = b.selectbox("Moneda", ("USD", "Bs"), key="control_c_moneda")
        fecha = c.text_input("Fecha (AAAA-MM-DD)", key="control_c_fecha")
        partida = st.text_input("Partida (opcional)", key="control_c_partida")
        fuente = st.text_input("Fuente del costo", key="control_c_fuente")
        responsable = st.text_input("Responsable", key="control_c_responsable")
        if st.button("Anotar costo", key="control_c_anotar") and _intentar(
            lambda: control.registrar_costo_real(
                sesion,
                proyecto,
                monto=monto,
                moneda=moneda,
                fecha=fecha,
                fuente=fuente,
                responsable=responsable,
                partida=partida,
            ),
            "Costo anotado: se convierte con la tasa de su fecha al calcular.",
        ):
            st.rerun()
        _mostrar_mensaje()


# --- pestañas de resultados -----------------------------------------------------------------------


def _calcular(sesion, proyecto: str, catalogo: Catalogo):
    """Corte y precios del corte elegidos arriba; el control se recalcula en cada ejecución."""
    a, b = st.columns(2)
    corte = a.date_input(
        "Fecha de corte", value=control.corte_por_defecto(sesion, proyecto), key="control_corte"
    )
    metodo = b.selectbox("Precios del corte (S1)", control.METODOS_DE_PRECIOS, key="control_metodo")
    version = km = r = fuente = ""
    if metodo == control.METODO_COMPROBACION:
        revaloradas = control.versiones_revaloradas(sesion, proyecto)
        version = st.selectbox("Version revalorada", revaloradas, key="control_pc_version") or ""
        if not revaloradas:
            st.caption("El proyecto no tiene versiones revaloradas (UC-02): no hay comprobacion.")
    elif metodo == control.METODO_ESCALATORIA:
        c, d, e = st.columns(3)
        km = c.text_input("Km declarado", key="control_pc_km")
        r = d.text_input("R declarado", value="0", key="control_pc_r")
        fuente = e.text_input("Fuente de Km y R", key="control_pc_fuente")
    try:
        precios = None
        if metodo != control.METODO_NINGUNO:
            elegido = control.PrecioElegido(metodo, version, km, r, fuente)
            precios = control.precios_del_corte(sesion, proyecto, catalogo, elegido, "costo")
        return control.calcular_el_control(sesion, proyecto, catalogo, corte=corte, precios=precios)
    except control.ControlInvalido as error:
        st.error(texto_seguro(str(error)))
        return None


def _valor_ganado(sesion, resultado) -> None:
    st.caption(
        f"Corte {resultado.instantanea.corte.isoformat()} (dia habil {resultado.estado.dia}). "
        "Las formulas de valor ganado son definiciones del sistema (S2-R11); el EAC del sistema y "
        "la separacion del desvio son propios de este trabajo. Sin proyectar inflacion futura "
        "(S2-R12)."
    )
    for costo in resultado.costos_sin_tasa:
        st.warning(
            f"El costo de {costo.monto} {costo.moneda} del {costo.fecha.isoformat()} no tiene "
            "tasa aplicable (mas de 7 dias sin tasa): el AC y lo que depende de el no estan "
            "disponibles; nada se estima."
        )
    _tabla(control.filas_de_indicadores(sesion, resultado), control.COLUMNAS_INDICADORES)
    curva = control.curva_pv_ev_ac(sesion, resultado)
    if curva:
        st.subheader("PV, EV y AC al cierre de cada periodo")
        st.line_chart(
            DataFrame(
                {
                    "PV": [float(p["PV"]) for p in curva],
                    "EV": [float(p["EV"]) for p in curva],
                    "AC": [None if p["AC"] is None else float(p["AC"]) for p in curva],
                },
                index=[p["Periodo"] for p in curva],
            )
        )
    if resultado.indicadores.pv == 0:
        st.caption("El corte es anterior a todo trabajo planificado: el SPI no aplica.")


def _alertas_y_reproyeccion(resultado) -> None:
    ind, rep = resultado.indicadores, resultado.reproyeccion
    st.subheader("Alertas")
    _tabla(control.alertas_en_filas(resultado), control.COLUMNAS_ALERTAS)
    st.subheader("Termino, costo final y punto de equilibrio")
    st.markdown(
        f"- Termino por el indice: {control.dia_con_fecha(resultado, ind.termino_indice)}\n"
        f"- Termino por el plan reproyectado: {control.dia_con_fecha(resultado, rep.termino)}\n"
        f"- Termino del plan base: {control.dia_con_fecha(resultado, resultado.estado.dias_plan)}\n"
        f"- EAC (sistema): {control.texto_monto(ind.eac_sistema)} {resultado.instantanea.moneda}"
    )
    if rep.termino is None:
        st.caption(rep.motivo_termino)
    equilibrio = resultado.equilibrio_proyectado
    if equilibrio is None:
        st.caption("Punto de equilibrio proyectado: no disponible (perspectiva precio o AC/EAC).")
    else:
        st.markdown(
            f"- Punto de equilibrio proyectado: {control.texto_monto(equilibrio.punto)} "
            f"({equilibrio.mensaje})"
        )
    st.caption(control.estudios_que_suma(resultado))
    st.subheader("Reproyeccion por partida")
    _tabla(control.filas_de_reproyeccion(resultado), control.COLUMNAS_REPROYECCION)
    st.subheader("Plan reproyectado")
    columnas, filas = control.filas_del_plan_reproyectado(resultado)
    _tabla(filas, columnas)


def _recuperacion(sesion, proyecto: str, catalogo: Catalogo, resultado) -> None:
    st.caption(
        "Las opciones se calculan a pedido, cada una sola, con el rendimiento y la cuadrilla de "
        "cada APU y un factor de eficiencia declarado (supuesto, no dato). Elegir una crea una "
        "version nueva; la linea base no cambia."
    )
    a, b = st.columns(2)
    objetivo = a.text_input(
        "Dia habil objetivo (vacio: el fin del plan base)", key="control_r_objetivo"
    )
    previas = b.text_input(
        "Horas extra que el obrero ya acumula en el año", value="0", key="control_r_previas"
    )
    corte = resultado.instantanea.corte
    if st.button("Calcular opciones", key="control_r_calcular"):
        try:
            st.session_state[CLAVE_OPCIONES] = (
                proyecto,
                corte,
                control.calcular_las_opciones(resultado, objetivo=objetivo, horas_previas=previas),
            )
        except control.ControlInvalido as error:
            st.session_state.pop(CLAVE_OPCIONES, None)
            st.error(texto_seguro(str(error)))
    guardadas = st.session_state.get(CLAVE_OPCIONES)
    if guardadas is not None and guardadas[:2] == (proyecto, corte):
        _elegir(sesion, catalogo, resultado, guardadas[2])
    decisiones = control.filas_de_decisiones(sesion, proyecto)
    if decisiones:
        st.subheader("Decisiones tomadas")
        _tabla(decisiones, control.COLUMNAS_DECISIONES)


def _elegir(sesion, catalogo: Catalogo, resultado, todas) -> None:
    _tabla(control.filas_de_opciones(todas), control.COLUMNAS_OPCIONES)
    for opcion in todas:
        if opcion.requisitos:
            st.caption(f"{opcion.titulo}: requiere " + "; ".join(opcion.requisitos))
    aplican = [o for o in todas if o.aplica]
    if not aplican:
        st.info("Ninguna opcion aplica a este corte.")
        return
    if not ui_sesion.puede(Accion.DECIDIR_RECUPERACION):
        st.info("Su cuenta puede ver las opciones, pero no elegir una (decide quien arma la obra).")
        return
    elegida = st.radio(
        "Opcion a aplicar", aplican, format_func=lambda o: o.titulo, key="control_r_elegida"
    )
    declaracion = ""
    if elegida.requiere_declaracion:
        declaracion = st.text_input(
            "Declaro que estas partidas no dependen de las que estan en curso (con su fuente)",
            key="control_r_independencia",
        )
    fuente = st.text_input("Fuente de la decision", key="control_r_fuente")
    responsable = st.text_input("Responsable de la decision", key="control_r_responsable")
    if st.button("Elegir y crear la version", type="primary", key="control_r_elegir"):
        try:
            codigo = control.elegir_opcion(
                sesion,
                resultado,
                elegida,
                catalogo,
                fuente=fuente,
                responsable=responsable,
                declaracion_independencia=declaracion,
            )
        except control.ControlInvalido as error:
            st.error(texto_seguro(str(error)))
        else:
            st.session_state.pop(CLAVE_OPCIONES, None)
            _mensaje("success", f"Version {codigo} creada con el plan de la opcion elegida.")
            st.rerun()
