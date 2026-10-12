"""La barra de herramientas del marco comun (sprint final SF4, RF-60 y RF-63; spec §10).

Fila de herramientas bajo la navegacion superior, pintada por el marco de `ui/app.py` encima de
cada pantalla. **Solo `ui/app.py` importa este modulo**: ninguna pagina importa el marco (lo vigila
`tests/unit/test_arquitectura.py`). La barra no conoce las claves de la hoja del proyecto: pide lo
que el usuario quiere con `ui.caso.pedir_accion` y la pantalla de destino lo atiende.

| Herramienta | Que hace |
|---|---|
| Proyecto | crea (nombre unico y no vacio, RF-63), abre y muestra caso y version vigente |
| Importar plano | solo si `adapters.espacio.planos` es importable (SF5); lleva a la hoja |
| Precios | la pestana Precios de la hoja si existe; si no, la pantalla Actualizar precios |
| Auditar | resume el informe de la version vigente (se audita siempre; el boton lo muestra) |
| Registrar valuacion | lleva a «Control de obra», pestana Valuaciones (UC-19, S2) |
| Guardar version, Exportar Excel | dependen de SF3: deshabilitados hasta que `ui.hoja` exista |
| Recorrido guiado | abre o retoma el recorrido de UC-12 |

**Ganchos declarados.** `FUNCIONES_DE_SF3` nombra las dos funciones que `ui.hoja` debe exponer para
habilitar Guardar version y Exportar Excel; mientras falte alguna, los botones quedan deshabilitados
con el texto de `TEXTO_SF3` y un aviso visible (`AVISO_SF3`, sin siglas internas;
`hay_guardado_y_exportacion`). Al habilitarse, el
boton lleva a la hoja con la accion pedida (`ACCION_GUARDAR_VERSION`, `ACCION_EXPORTAR_EXCEL`): el
guardado exige fuente y responsable (RF-53) y la descarga del Excel se genera solo al pulsar, asi
que ambos viven en la pantalla de la hoja, no en la barra.

«Fija» significa que esta en el mismo lugar de todas las pantallas; no se fija con CSS (`position:
sticky` exige HTML sin escapar y se rompe con cada version de Streamlit).
"""

from __future__ import annotations

import importlib
import importlib.util
from collections.abc import Callable

import streamlit as st

from seguridad.permisos import Accion
from ui import sesion as ui_sesion
from ui.caso import (
    ACCION_EXPORTAR_EXCEL,
    ACCION_GUARDAR_VERSION,
    ACCION_IMPORTAR_PLANO,
    ACCION_PRECIOS,
    ACCION_REGISTRAR_VALUACION,
    estado_caso,
    fijar_proyecto,
    pedir_accion,
    proyecto_abierto,
    recorrido_activo,
    resumen_publicado,
    ruta_caso,
)
from ui.proyectos import (
    MONEDAS_DEL_PROYECTO,
    ProyectoInvalido,
    crear_proyecto_nuevo,
    listar_proyectos,
    resumen_auditoria,
    version_vigente,
)
from ui.recorridos import destino_de_recorrido, recorrido_por_nombre
from ui.texto_seguro import texto_seguro

ROTULO_PROYECTO = "Proyecto"
ROTULO_IMPORTAR = "Importar plano"
ROTULO_PRECIOS = "Precios"
ROTULO_AUDITAR = "Auditar"
ROTULO_VALUACION = "Registrar valuacion"
ROTULO_GUARDAR = "Guardar version"
ROTULO_EXPORTAR = "Exportar Excel"
ROTULO_RECORRIDO = "Recorrido guiado"
ROTULO_RETOMAR = "Retomar: {}"
ROTULO_CREAR = "Crear proyecto"
ROTULO_ABRIR = "Abrir"

TEXTO_SF3 = "Todavía no está disponible en esta versión del prototipo."
AVISO_SF3 = (
    "Guardar versión y Exportar Excel se habilitarán cuando la hoja del proyecto esté completa."
)

CLAVE_NOMBRE_NUEVO = "barra_proyecto_nombre"
CLAVE_MONEDA_NUEVA = "barra_proyecto_moneda"
MENSAJE_SIN_MONEDA = "Elija la moneda del proyecto (Bs o USD): no tiene valor por defecto."
CLAVE_ABRIR = "barra_proyecto_abrir"
CLAVE_MENSAJE = "barra_mensaje"  # (tipo, texto) del ultimo intento de crear: no es de widget

#: Lo que `ui.hoja` debe exponer para habilitar Guardar version y Exportar Excel (SF3).
FUNCIONES_DE_SF3: tuple[str, ...] = ("guardar_version", "exportar_excel")

PAQUETE_DE_PLANOS = "adapters.espacio.planos"
RUTA_HOJA = "hoja"
RUTA_ACTUALIZACION = "actualizacion"
RUTA_CONTROL = "control"
PESTANA_PRECIOS = "Precios"


# --- deteccion de lo que otras fases entregan --------------------------------------------------


def hay_importacion_de_planos(buscar: Callable[[str], object | None] | None = None) -> bool:
    """True si el paquete de importacion de planos (SF5) existe: si no, la herramienta se oculta."""
    buscar = buscar or importlib.util.find_spec
    try:
        return buscar(PAQUETE_DE_PLANOS) is not None
    except (ImportError, ValueError):  # ModuleNotFoundError es un ImportError
        return False


def hay_guardado_y_exportacion() -> bool:
    """True si `ui.hoja` expone las dos funciones de SF3 (`FUNCIONES_DE_SF3`)."""
    hoja = importlib.import_module("ui.hoja")
    return all(callable(getattr(hoja, nombre, None)) for nombre in FUNCIONES_DE_SF3)


def _hay_pestana_precios() -> bool:
    paginas_hoja = importlib.import_module("ui.paginas.hoja")
    return PESTANA_PRECIOS in paginas_hoja.PESTANAS


# --- acciones (callbacks de botones) -----------------------------------------------------------


def _crear_proyecto() -> None:
    ui_sesion.exigir(Accion.EDITAR_HOJA)
    moneda = st.session_state.get(CLAVE_MONEDA_NUEVA)
    if moneda is None:
        st.session_state[CLAVE_MENSAJE] = ("error", MENSAJE_SIN_MONEDA)
        return
    try:
        nombre = crear_proyecto_nuevo(
            ruta_caso(), st.session_state.get(CLAVE_NOMBRE_NUEVO, ""), moneda
        )
    except ProyectoInvalido as error:
        st.session_state[CLAVE_MENSAJE] = ("error", str(error))
        return
    fijar_proyecto(nombre)
    st.session_state[CLAVE_NOMBRE_NUEVO] = ""
    st.session_state[CLAVE_MONEDA_NUEVA] = None
    st.session_state[CLAVE_MENSAJE] = (
        "exito",
        f"Proyecto «{nombre}» creado y abierto en {moneda}.",
    )


def _abrir_proyecto() -> None:
    elegido = st.session_state.get(CLAVE_ABRIR)
    if elegido:
        fijar_proyecto(elegido)
        st.session_state[CLAVE_MENSAJE] = ("exito", f"Proyecto «{elegido}» abierto.")


def _ir_con_accion(ir_a: Callable[[str], None], ruta: str, accion: str | None) -> None:
    if accion is not None:
        pedir_accion(accion)
    ir_a(ruta)


# --- piezas ------------------------------------------------------------------------------------


def _proyecto_vigente(nombres: list[str]) -> str | None:
    """El proyecto abierto, o `None` si no hay o ya no esta en este caso."""
    abierto = proyecto_abierto()
    return abierto if abierto in nombres else None


def _pintar_proyecto(nombres: list[str], abierto: str | None) -> None:
    ruta = ruta_caso()
    estado = estado_caso(ruta)
    st.caption(f"Caso abierto: {ruta.name}", help=str(ruta))
    if abierto is None:
        st.caption("Ningun proyecto abierto.")
    else:
        version = version_vigente(ruta, abierto)
        detalle = (
            "sin version guardada"
            if version is None
            else f"version vigente: {version.codigo} ({version.fecha.isoformat()})"
        )
        st.markdown(f"**{abierto}** · {detalle}")
    if estado.error is not None:
        st.error(f"No se pudo leer el caso: {estado.error}")

    st.text_input(
        "Nombre del proyecto nuevo",
        key=CLAVE_NOMBRE_NUEVO,
        help="Unico en este caso y no vacio.",
    )
    st.selectbox(
        "Moneda del proyecto",
        MONEDAS_DEL_PROYECTO,
        index=None,
        placeholder="Elija Bs o USD",
        key=CLAVE_MONEDA_NUEVA,
    )
    st.button(ROTULO_CREAR, on_click=_crear_proyecto, key="barra_crear")
    st.selectbox(
        "Abrir un proyecto del caso",
        nombres,
        index=nombres.index(abierto) if abierto in nombres else None,
        placeholder="No hay proyectos" if not nombres else "Elija uno",
        key=CLAVE_ABRIR,
    )
    st.button(ROTULO_ABRIR, on_click=_abrir_proyecto, disabled=not nombres, key="barra_abrir")


def _pintar_auditoria(abierto: str | None) -> None:
    if abierto is None:
        st.caption("Abra un proyecto para ver el resumen de su informe de auditoria.")
        return
    resumen = resumen_auditoria(ruta_caso(), abierto)
    if resumen is None:
        st.caption(
            "El proyecto no tiene version guardada. La hoja del proyecto audita su borrador en "
            "cada edicion (véalo en la hoja del proyecto)."
        )
        return
    detalle = ", ".join(f"{n} {s.lower()}" for s, n in resumen.por_severidad.items() if n)
    st.markdown(
        f"Version {resumen.version.codigo}: **{resumen.total} hallazgo(s)**"
        + (f" ({detalle})" if detalle else "")
    )


# --- la barra ----------------------------------------------------------------------------------


def pintar_barra(ruta: str, ir_a: Callable[[str], None]) -> None:
    """Pinta la barra de herramientas encima de la pantalla `ruta`.

    `ir_a` lleva a la pantalla de una ruta (`st.switch_page` en la aplicacion, un registrador en
    las pruebas).
    """
    nombres = listar_proyectos(ruta_caso())
    abierto = _proyecto_vigente(nombres)
    con_planos = hay_importacion_de_planos()
    con_sf3 = hay_guardado_y_exportacion()
    recorrido = recorrido_por_nombre(recorrido_activo())

    with st.container(key="barra_herramientas"):
        columnas = st.columns(8 if con_planos else 7, vertical_alignment="bottom")
        celdas = iter(columnas)
        with next(celdas), st.popover(ROTULO_PROYECTO, width="stretch"):
            _pintar_proyecto(nombres, abierto)
        if con_planos:
            with next(celdas):
                if st.button(ROTULO_IMPORTAR, width="stretch", key="barra_importar"):
                    _ir_con_accion(ir_a, RUTA_HOJA, ACCION_IMPORTAR_PLANO)
        with next(celdas):
            if st.button(ROTULO_PRECIOS, width="stretch", key="barra_precios"):
                if _hay_pestana_precios():
                    _ir_con_accion(ir_a, RUTA_HOJA, ACCION_PRECIOS)
                else:
                    _ir_con_accion(ir_a, RUTA_ACTUALIZACION, None)
        with next(celdas), st.popover(ROTULO_AUDITAR, width="stretch"):
            _pintar_auditoria(abierto)
        with next(celdas):
            if st.button(ROTULO_VALUACION, width="stretch", key="barra_valuacion"):
                _ir_con_accion(ir_a, RUTA_CONTROL, ACCION_REGISTRAR_VALUACION)
        for rotulo, accion, clave in (
            (ROTULO_GUARDAR, ACCION_GUARDAR_VERSION, "barra_guardar"),
            (ROTULO_EXPORTAR, ACCION_EXPORTAR_EXCEL, "barra_exportar"),
        ):
            with next(celdas):
                if st.button(
                    rotulo,
                    width="stretch",
                    key=clave,
                    disabled=not con_sf3,
                    help=None if con_sf3 else TEXTO_SF3,
                ):
                    _ir_con_accion(ir_a, RUTA_HOJA, accion)
        with next(celdas):
            rotulo = ROTULO_RECORRIDO
            if recorrido is not None:
                rotulo = ROTULO_RETOMAR.format(recorrido.nombre)
            if st.button(rotulo, width="stretch", key="barra_recorrido"):
                ir_a(destino_de_recorrido(recorrido, ruta))

    # Fuera del popover, que puede cerrarse al recargar: lo que el usuario debe ver siempre.
    mensaje = st.session_state.pop(CLAVE_MENSAJE, None)
    if mensaje is not None:
        (st.error if mensaje[0] == "error" else st.success)(mensaje[1])
    if abierto is not None:
        st.markdown(f"Proyecto abierto: **{abierto}**")
    if not con_sf3:
        st.caption(AVISO_SF3)


def pintar_estado() -> None:
    """La linea de estado bajo la barra: proyecto, version, estado y total (PLAN_SILICE_UI, 5).

    El total y el estado solo aparecen si la hoja publico el resumen del proyecto abierto; si no,
    la version vigente guardada. Todo texto ajeno pasa por `texto_seguro` (RU-9).
    """
    abierto = proyecto_abierto()
    if abierto is None:
        return
    resumen = resumen_publicado()
    if resumen is not None and resumen.proyecto == abierto:
        partes = [f"Proyecto: {texto_seguro(abierto)}"]
        if resumen.version is not None:
            partes.append(f"Version {texto_seguro(resumen.version)}")
        partes += [f"Estado: {resumen.estado}", f"Total: {texto_seguro(resumen.total)}"]
    else:
        vigente = version_vigente(ruta_caso(), abierto)
        partes = [f"Proyecto: {texto_seguro(abierto)}"]
        partes.append(
            "sin version guardada"
            if vigente is None
            else f"Version vigente {texto_seguro(vigente.codigo)} del {vigente.fecha.isoformat()}"
        )
    st.caption(" · ".join(partes))
