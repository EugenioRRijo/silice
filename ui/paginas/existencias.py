"""Existencias de la arenera (Tarea 4.9; UC-28 / UC-29; RT-S4-2 y RT-S4-3).

Cuatro pestañas: **Existencias** (cuánto hay y cuánto queda de cada material, con el estado en
signo y texto: «✔ Normal», «▲ Queda poco», «✖ Existencia negativa: falta registrar producción o
conteo»; no se usa solo el color), **Registrar** (entrada, despacho, conteo y material nuevo),
**Importar báscula** (zona de carga y resultado) y **Pesajes sospechosos** (resolver o descartar).

Quién puede: `OPERAR_ARENERA` (arma y administrador). Se exige al abrir la página y otra vez en cada
acción. El usuario de cada movimiento sale de la sesión de la interfaz (`ui.sesion`); la fecha de
referencia de la importación es hoy, a la vista y editable. Un despacho nunca se bloquea por dejar
la existencia negativa: se registra y el tablero lo marca (RT-S4-2).

Tras cada acción que cambia datos la página se repinta (`st.rerun`) con un aviso guardado en
`st.session_state` (clave que no es de widget) y los campos escritos se limpian, para que un doble
clic no registre dos veces. Los errores del usuario muestran su mensaje; un fallo inesperado da un
mensaje fijo y, plegado, solo el nombre de la clase de error (el detalle va al registro del
servidor).
La sesión de base sale de `ui.sesion.instalacion()` y se abre solo dentro de la página.
"""

from __future__ import annotations

import logging
from datetime import date

import streamlit as st

from seguridad.permisos import Accion
from ui import existencias as logica
from ui import sesion as ui_sesion
from ui.subidas import nombre_seguro
from ui.texto_seguro import texto_seguro

LOG = logging.getLogger(__name__)

CLAVE_AVISO = "existencias_aviso"  # aviso para después del repintado: no es de widget
CLAVE_LIMPIAR = "existencias_limpiar"  # claves de widget por reiniciar en el próximo repintado
CLAVE_RESULTADO = "existencias_resultado"  # último ResultadoImportacion
CLAVE_FALTAN = "existencias_faltan"  # campos que el usuario debe mapear a una columna
PESTANAS = ("Existencias", "Registrar", "Importar báscula", "Pesajes sospechosos")
MENSAJE_FALLO = (
    "No se pudo completar la acción por un problema inesperado. Vuelva a intentarlo; si se repite, "
    "comunique a quien administra Sílice el tipo de error de abajo (el detalle quedó en el "
    "registro del servidor)."
)
LEYENDA_ESTADOS = (
    "Estado: ✔ favorable (hay más que la mínima) · ▲ a vigilar (existencia menor o igual que la "
    "mínima) · ✖ desfavorable (existencia negativa: falta registrar producción o conteo)."
)
AYUDA_CANTIDAD = "Escriba el número con coma o punto decimal, sin separador de miles."
SIN_MATERIALES = (
    "Todavía no hay materiales. Créelos en «Registrar», con su existencia mínima, antes de "
    "registrar movimientos o importar la báscula."
)
ROTULOS_DE_CAMPO = {
    "ticket": "ticket",
    "fecha": "fecha",
    "placa": "placa",
    "cliente": "cliente",
    "material": "material",
    "bruto": "peso bruto",
    "tara": "tara",
    "neto": "peso neto",
}
UNIDAD_SEGUN_ENCABEZADO = "Según el encabezado"


# --- avisos y errores -----------------------------------------------------------------------------


def _repintar(aviso: str, *claves: str) -> None:
    """Deja un aviso, reinicia los campos escritos y repinta (el tablero ya cambió)."""
    st.session_state[CLAVE_AVISO] = aviso
    st.session_state[CLAVE_LIMPIAR] = list(claves)
    st.rerun()


def _error_del_usuario(error: Exception) -> None:
    st.error(texto_seguro(str(error)))


def _fallo_inesperado(error: Exception, que: str) -> None:
    """Mensaje fijo y solo la clase del error, plegada; la traza va al registro."""
    LOG.error("Existencias de la arenera, %s: %s", que, type(error).__name__, exc_info=error)
    st.error(MENSAJE_FALLO)
    with st.expander("Detalle técnico"):
        st.code(type(error).__name__, language=None)


def _ejecutar(que: str, accion):
    """Corre `accion()`; devuelve `(True, resultado)` o `(False, None)` tras decir por qué falló."""
    try:
        return True, accion()
    except logica.ERRORES_DEL_USUARIO as error:
        _error_del_usuario(error)
    except Exception as error:  # noqa: BLE001 - nunca una traza en pantalla
        _fallo_inesperado(error, que)
    return False, None


def _pedir_permiso() -> object:
    """Cada acción vuelve a exigir el permiso (la navegación no es el control)."""
    return ui_sesion.exigir(Accion.OPERAR_ARENERA)


def _hoy() -> date:
    return ui_sesion.ahora().date()


# --- pestañas -------------------------------------------------------------------------------------


def _pestana_existencias(bd) -> None:
    fecha = st.date_input(
        "Existencia al",
        value=_hoy(),
        key="existencias_fecha",
        format="DD/MM/YYYY",
        help="Cuánto había de cada material al final de ese día. Por defecto, hoy.",
    )
    filas = logica.tablero_para_pantalla(bd, fecha)
    if not filas:
        st.info(SIN_MATERIALES)
        return
    pocos = sum(1 for f in filas if f.estado == "queda poco")
    negativos = sum(1 for f in filas if f.estado == "negativa")
    c = st.columns(3)
    c[0].metric("Materiales", len(filas))
    c[1].metric("Queda poco", pocos)
    c[2].metric("Existencia negativa", negativos)
    st.dataframe(logica.filas_de_tablero(filas), hide_index=True, width="stretch")
    st.caption(LEYENDA_ESTADOS)
    if negativos:
        st.warning(
            "Hay materiales con existencia negativa: salió más de lo que se registró. Registre la "
            "producción (entrada) o un conteo físico para corregirlo."
        )


def _selector_de_material(bd, rotulo: str, clave: str):
    """(material_id, etiqueta) del material elegido, o `None` si aún no hay materiales."""
    materiales = logica.materiales_activos(bd)
    if not materiales:
        st.info(SIN_MATERIALES)
        return None
    por_etiqueta = {logica.etiqueta_de_material(m): m for m in materiales}
    elegida = st.selectbox(rotulo, list(por_etiqueta), key=clave)
    return por_etiqueta[elegida]


def _pestana_registrar(bd) -> None:
    sesion = ui_sesion.exigir(Accion.OPERAR_ARENERA)
    st.caption(
        "Cada movimiento queda con su fecha y con su nombre. Un despacho nunca se bloquea: si deja "
        "la existencia negativa, se registra y el tablero lo marca."
    )
    with st.expander("Entrada (producción)", expanded=True):
        material = _selector_de_material(bd, "Material", "existencias_entrada_material")
        if material is not None:
            c = st.columns(3)
            fecha = c[0].date_input(
                "Fecha", value=_hoy(), key="existencias_entrada_fecha", format="DD/MM/YYYY"
            )
            cantidad = c[1].text_input(
                f"Cantidad ({logica.UNIDADES[material.unidad_venta]})",
                key="existencias_entrada_cantidad",
                help=AYUDA_CANTIDAD,
            )
            nota = c[2].text_input("Nota (opcional)", key="existencias_entrada_nota")
            if st.button("Registrar entrada", key="existencias_entrada_registrar"):
                _pedir_permiso()
                ok, _ = _ejecutar(
                    "entrada",
                    lambda: logica.registrar_entrada_desde_pantalla(
                        bd, material.id, fecha, cantidad, sesion.usuario, nota
                    ),
                )
                if ok:
                    _repintar(
                        f"Entrada registrada: {texto_seguro(cantidad.strip())} "
                        f"de {material.codigo}.",
                        "existencias_entrada_cantidad",
                        "existencias_entrada_nota",
                    )
    with st.expander("Despacho"):
        material = _selector_de_material(bd, "Material", "existencias_despacho_material")
        if material is not None:
            c = st.columns(3)
            fecha = c[0].date_input(
                "Fecha", value=_hoy(), key="existencias_despacho_fecha", format="DD/MM/YYYY"
            )
            cantidad = c[1].text_input(
                f"Cantidad ({logica.UNIDADES[material.unidad_venta]})",
                key="existencias_despacho_cantidad",
                help=AYUDA_CANTIDAD,
            )
            ticket = c[2].text_input(
                "Ticket (opcional)",
                key="existencias_despacho_ticket",
                help="Si lo escribe, no puede repetirse.",
            )
            d = st.columns(3)
            placa = d[0].text_input("Placa (opcional)", key="existencias_despacho_placa")
            cliente = d[1].text_input("Cliente (opcional)", key="existencias_despacho_cliente")
            nota = d[2].text_input("Nota (opcional)", key="existencias_despacho_nota")
            if st.button("Registrar despacho", key="existencias_despacho_registrar"):
                _pedir_permiso()
                ok, _ = _ejecutar(
                    "despacho",
                    lambda: logica.registrar_despacho_desde_pantalla(
                        bd,
                        material.id,
                        fecha,
                        cantidad,
                        sesion.usuario,
                        ticket=ticket,
                        placa=placa,
                        cliente=cliente,
                        nota=nota,
                    ),
                )
                if ok:
                    _repintar(
                        f"Despacho registrado: {texto_seguro(cantidad.strip())} "
                        f"de {material.codigo}.",
                        "existencias_despacho_cantidad",
                        "existencias_despacho_ticket",
                        "existencias_despacho_placa",
                        "existencias_despacho_cliente",
                        "existencias_despacho_nota",
                    )
    with st.expander("Conteo físico"):
        st.caption(
            "Escriba lo que hay contado en el patio: Sílice registra el ajuste que lleva la "
            "existencia a ese valor."
        )
        material = _selector_de_material(bd, "Material", "existencias_conteo_material")
        if material is not None:
            c = st.columns(3)
            fecha = c[0].date_input(
                "Fecha", value=_hoy(), key="existencias_conteo_fecha", format="DD/MM/YYYY"
            )
            conteo = c[1].text_input(
                f"Lo contado ({logica.UNIDADES[material.unidad_venta]})",
                key="existencias_conteo_cantidad",
                help=AYUDA_CANTIDAD,
            )
            nota = c[2].text_input("Nota (opcional)", key="existencias_conteo_nota")
            if st.button("Registrar conteo", key="existencias_conteo_registrar"):
                _pedir_permiso()
                ok, ajuste = _ejecutar(
                    "conteo",
                    lambda: logica.registrar_conteo_desde_pantalla(
                        bd, material.id, fecha, conteo, sesion.usuario, nota
                    ),
                )
                if ok:
                    _repintar(
                        "Conteo registrado."
                        if ajuste is not None
                        else "El conteo coincide con la existencia: no hizo falta ajustar.",
                        "existencias_conteo_cantidad",
                        "existencias_conteo_nota",
                    )
    with st.expander("Material nuevo"):
        st.caption(
            "La existencia mínima y la densidad son datos de la empresa: Sílice no propone "
            "ninguna. "
            "Sin densidad, los pesajes de la báscula en m³ para este material irán a la bandeja."
        )
        c = st.columns(3)
        codigo = c[0].text_input("Código", key="existencias_nuevo_codigo")
        nombre = c[1].text_input("Nombre", key="existencias_nuevo_nombre")
        unidad = c[2].selectbox(
            "Unidad de venta",
            ["m3", "t"],
            format_func=lambda u: logica.UNIDADES[u],
            key="existencias_nuevo_unidad",
        )
        d = st.columns(2)
        minima = d[0].text_input("Existencia mínima", key="existencias_nuevo_minima")
        densidad = d[1].text_input(
            "Densidad (t/m³, opcional)", key="existencias_nuevo_densidad", help=AYUDA_CANTIDAD
        )
        if st.button("Crear material", key="existencias_nuevo_crear"):
            _pedir_permiso()
            ok, _ = _ejecutar(
                "material nuevo",
                lambda: logica.crear_material_desde_pantalla(
                    bd,
                    codigo=codigo,
                    nombre=nombre,
                    unidad_venta=unidad,
                    minima_texto=minima,
                    densidad_texto=densidad,
                ),
            )
            if ok:
                _repintar(
                    f"Material creado: {texto_seguro(codigo.strip())}.",
                    "existencias_nuevo_codigo",
                    "existencias_nuevo_nombre",
                    "existencias_nuevo_minima",
                    "existencias_nuevo_densidad",
                )


def _mapeo_pedido() -> dict[str, int] | None:
    """Las columnas que el usuario indica cuando Sílice no las reconoció (1 = la primera)."""
    faltan = st.session_state.get(CLAVE_FALTAN)
    if not faltan:
        return None
    st.warning(
        "Sílice no reconoció las columnas de: "
        + ", ".join(ROTULOS_DE_CAMPO.get(f, f) for f in faltan)
        + ". Indique en qué columna está cada una (1 = la primera columna) y vuelva a importar."
    )
    return {
        campo: int(
            st.number_input(
                f"Columna de {ROTULOS_DE_CAMPO.get(campo, campo)}",
                min_value=1,
                max_value=200,
                value=1,
                step=1,
                key=f"existencias_columna_{campo}",
            )
        )
        - 1
        for campo in faltan
    }


def _resultado_de_la_importacion() -> None:
    resultado = st.session_state.get(CLAVE_RESULTADO)
    if resultado is None:
        return
    st.subheader("Resultado de la importación")
    c = st.columns(3)
    c[0].metric("Despachos registrados", resultado.registrados)
    c[1].metric("Ya estaban registrados", resultado.ya_registrados)
    c[2].metric("A la bandeja de sospechosos", resultado.a_la_bandeja)
    if resultado.a_la_bandeja:
        st.info(
            "Los pesajes dudosos no entraron al inventario: revíselos en «Pesajes sospechosos» "
            "para resolverlos o descartarlos."
        )


def _pestana_importar(bd) -> None:
    sesion = ui_sesion.exigir(Accion.OPERAR_ARENERA)
    st.caption(
        "Suba el reporte de la báscula (.csv o .xlsx). Reimportar el mismo reporte no duplica "
        "nada. Los pesajes con fecha futura, sin ticket, con pesos que no cuadran o de un "
        "material que no está en la lista van a la bandeja."
    )
    subida = st.file_uploader(
        "Reporte de la báscula (.csv o .xlsx)",
        type=["csv", "xlsx"],
        key="existencias_archivo",
        help="Un .xlsx con macros (.xlsm) no se acepta.",
    )
    c = st.columns(2)
    unidad = c[0].radio(
        "Unidad de los pesos",
        [UNIDAD_SEGUN_ENCABEZADO, "kg", "t"],
        key="existencias_unidad_peso",
        horizontal=True,
        help="Si el encabezado de las columnas de peso no dice kg o t, indíquelo aquí.",
    )
    referencia = c[1].date_input(
        "Fecha de referencia",
        value=_hoy(),
        key="existencias_referencia",
        format="DD/MM/YYYY",
        help="Un pesaje con fecha posterior a esta se considera dudoso. Por defecto, hoy.",
    )
    mapeo = _mapeo_pedido()
    if subida is None:
        st.info("Suba el reporte de la báscula para empezar.")
    elif st.button("Importar", type="primary", key="existencias_importar"):
        _pedir_permiso()
        try:
            nombre = nombre_seguro(subida.name)
        except ValueError:
            nombre = "reporte"
        with st.spinner("Leyendo e importando el reporte…"):
            try:
                resultado = logica.importar_desde_pantalla(
                    bd,
                    subida.getvalue(),
                    nombre,
                    referencia,
                    None if unidad == UNIDAD_SEGUN_ENCABEZADO else unidad,
                    sesion.usuario,
                    mapeo,
                )
            except logica.MapeoNecesario as error:
                st.session_state[CLAVE_FALTAN] = list(error.faltan)
                st.rerun()
            except logica.ERRORES_DEL_USUARIO as error:
                _error_del_usuario(error)
            except Exception as error:  # noqa: BLE001 - nunca una traza en pantalla
                _fallo_inesperado(error, "importar")
            else:
                st.session_state[CLAVE_RESULTADO] = resultado
                st.session_state.pop(CLAVE_FALTAN, None)
                _repintar(
                    "Importación terminada.",
                    "existencias_archivo",
                    *(f"existencias_columna_{campo}" for campo in logica.CAMPOS),
                )
    _resultado_de_la_importacion()


def _fecha_de_la_bandeja(texto: str) -> date:
    try:
        return date.fromisoformat(texto.strip()[:10])
    except ValueError:
        return _hoy()


def _pestana_sospechosos(bd) -> None:
    sesion = ui_sesion.exigir(Accion.OPERAR_ARENERA)
    pendientes = logica.sospechosos_pendientes(bd)
    if not pendientes:
        st.success("No hay pesajes sospechosos por resolver.")
        return
    st.caption(
        f"{len(pendientes)} pesaje(s) por resolver. Corrija el material, la fecha, el neto y el "
        "ticket y regístrelo como despacho, o descártelo. El peso neto se escribe en toneladas (t)."
    )
    st.dataframe(logica.filas_de_sospechosos(pendientes), hide_index=True, width="stretch")
    por_etiqueta = {
        f"Fila {s.fila} · {s.ticket or 'sin ticket'} · {s.motivo}": s for s in pendientes
    }
    elegido = por_etiqueta[st.selectbox("Pesaje", list(por_etiqueta), key="existencias_sospechoso")]
    materiales = logica.materiales_activos(bd)
    if not materiales:
        st.info(SIN_MATERIALES)
        return
    codigos = {logica.etiqueta_de_material(m): m for m in materiales}
    por_defecto = next(
        (
            i
            for i, m in enumerate(materiales)
            if m.codigo.casefold() == elegido.material_texto.casefold()
        ),
        0,
    )
    c = st.columns(4)
    material = codigos[
        c[0].selectbox(
            "Material correcto",
            list(codigos),
            index=por_defecto,
            key=f"existencias_resolver_material_{elegido.id}",
        )
    ]
    fecha = c[1].date_input(
        "Fecha",
        value=_fecha_de_la_bandeja(elegido.fecha_texto),
        key=f"existencias_resolver_fecha_{elegido.id}",
        format="DD/MM/YYYY",
    )
    neto = c[2].text_input(
        "Peso neto (t)", key=f"existencias_resolver_neto_{elegido.id}", help=AYUDA_CANTIDAD
    )
    ticket = c[3].text_input(
        "Ticket", value=elegido.ticket, key=f"existencias_resolver_ticket_{elegido.id}"
    )
    b = st.columns(2)
    if b[0].button("Resolver como despacho", type="primary", key="existencias_resolver"):
        _pedir_permiso()
        ok, _ = _ejecutar(
            "resolver",
            lambda: logica.resolver_desde_pantalla(
                bd,
                elegido.id,
                material_codigo=material.codigo,
                fecha=fecha,
                neto_texto=neto,
                ticket=ticket,
                usuario=sesion.usuario,
                ahora=ui_sesion.ahora(),
            ),
        )
        if ok:
            _repintar(f"Pesaje resuelto: despacho de {material.codigo} registrado.")
    if b[1].button("Descartar", key="existencias_descartar"):
        _pedir_permiso()
        ok, _ = _ejecutar(
            "descartar",
            lambda: logica.descartar_desde_pantalla(
                bd, elegido.id, usuario=sesion.usuario, ahora=ui_sesion.ahora()
            ),
        )
        if ok:
            _repintar("Pesaje descartado: no se registró ningún despacho.")


# --- página ---------------------------------------------------------------------------------------


def render() -> None:
    ui_sesion.exigir(Accion.OPERAR_ARENERA)
    for clave in st.session_state.pop(CLAVE_LIMPIAR, ()):
        st.session_state.pop(clave, None)
    aviso = st.session_state.pop(CLAVE_AVISO, None)
    if aviso:
        st.success(aviso)
    st.caption(
        "Cuánto hay y cuánto queda de cada material de la arenera: producción, despachos de la "
        "báscula y conteos físicos. Aquí se registra y se importa; los reportes reales de la "
        "báscula no se guardan fuera de la base de la instalación."
    )
    with ui_sesion.instalacion() as bd:
        pestanas = st.tabs(list(PESTANAS))
        with pestanas[0]:
            _pestana_existencias(bd)
        with pestanas[1]:
            _pestana_registrar(bd)
        with pestanas[2]:
            _pestana_importar(bd)
        with pestanas[3]:
            _pestana_sospechosos(bd)
