"""Pantalla «Hoja del proyecto»: nueve pestanas sobre un borrador editable (SF3, spec §9).

Pestanas: Espacio y metrajes, APU, Presupuesto, Plan y curva, Punto de equilibrio, Precios,
Parametros, Auditoria y Trazabilidad. Cada una edita solo lo que la spec §9.2 declara editable y
pinta lo calculado aparte. Toda la logica vive en `ui.hoja` (sin Streamlit); aqui solo se pinta.

Decisiones de pantalla (spec §5.3, §5.4 y §9.2):

* **El borrador vive en `st.session_state[CLAVE_BORRADOR]`**, una clave que no es de ningun widget
  (Streamlit descarta el estado de los widgets que no se vuelven a montar). Es un
  `ui.hoja.Borrador`: espacio, copia de las composiciones de la version, parametros, plan y
  cantidades escritas a mano. Cada edicion valida produce otro borrador; una fila invalida se
  muestra como error y la hoja sigue con el ultimo borrador valido.
* **Los editores se siembran con `CLAVE_PARTIDA`**, no con el borrador vigente: devolverle al
  editor la tabla recalculada en cada edicion lo reiniciaria. Al cambiar de pestana, abrir una
  version o aplicar una accion que no es del editor, la siembra se renueva (`_resembrar`: sube la
  generacion que forma parte de la clave de cada editor).
* **La columna Estado y lo calculado van fuera de los editores**, en `st.dataframe` aparte.
* **La pestana activa es un `st.segmented_control`**: solo se ejecuta esa pestana en cada edicion.
  El resultado (`ui.hoja.elaborar_borrador`) se calcula una sola vez por borrador nuevo y se
  guarda junto a el.
* **El Excel se genera solo al pulsar «Preparar Excel»** (o cuando la barra superior pide
  `ACCION_EXPORTAR_EXCEL`) y se ofrece con `st.download_button`.
* **Aviso de ediciones sin guardar (15c):** mientras haya cambios la pantalla lo dice, y cambiar de
  version o de proyecto pide confirmar que se descartan. Cerrar la pestana del navegador no se
  puede interceptar desde Streamlit: queda como diferido declarado.

Guardar, restaurar y cotizar escriben en el caso por `ui.hoja` en UNA sola sesion. Sin efectos al
importarse: todo vive dentro de `render()`.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import streamlit as st
from pandas import DataFrame
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from adapters.espacio import (
    Especialidad,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoOrigen,
    TipoPunto,
)
from adapters.espacio.planos import EstadoImportacion
from asistente import privacidad as ia_privacidad
from asistente import servicio as ia_servicio
from asistente.orquestador import ESPERAR, Servicios, Topes
from asistente.propuestas import EstadoPropuesta
from asistente.registro import RegistroIA
from asistente.tarifas import tarifa_de
from core import models
from core.budget.moneda import moneda_del_proyecto
from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion, crear_motor
from core.catalog.moneda import MONEDAS
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from operacion.base_datos import ErrorDeBase, preparar_base
from seguridad.permisos import Accion
from ui import caso, control, entrega, hoja
from ui import sesion as ui_sesion
from ui.caso import ACCION_IMPORTAR_PLANO, ACCION_PRECIOS, ruta_caso
from ui.resultado import mostrar_informe
from ui.texto_seguro import texto_seguro

PESTANAS = (
    "Espacio y metrajes",
    "APU",
    "Presupuesto",
    "Plan y curva",
    "Punto de equilibrio",
    "Precios",
    "Parámetros",
    "Auditoría",
    "Trazabilidad",
)

# Claves de `st.session_state` que NO son de ningun widget.
CLAVE_BORRADOR = "hoja_borrador"  # el `Borrador` vigente
CLAVE_PARTIDA = "hoja_partida"  # el `Borrador` con que se sembraron los editores
CLAVE_ABIERTA = "hoja_abierta"  # la `VersionAbierta` (o None: borrador sin version)
CLAVE_ABIERTA_EN = "hoja_abierta_en"  # (ruta, proyecto, codigo) de lo abierto
CLAVE_RESULTADO = "hoja_resultado"  # (borrador, ResultadoHoja, cambios) del ultimo calculo
CLAVE_GENERACION = "hoja_generacion"  # sube al renovar la siembra de los editores
CLAVE_ULTIMA_PESTANA = "hoja_ultima_pestana"
CLAVE_EXCEL = "hoja_excel"  # (nombre, bytes) del ultimo Excel preparado
CLAVE_ACCION_PENDIENTE = "hoja_accion_pendiente"  # accion de la barra que aun no se atendio
CLAVE_IMPORTACION = "hoja_importacion"  # el `ResultadoImportacion` del plano que se esta revisando
CLAVE_PLANO = "hoja_plano"  # ruta (texto) del plano guardado, para reanudarlo con la unidad
CLAVE_PROYECTO_DE_LA_BARRA = "hoja_proyecto_de_la_barra"  # el de la barra que la hoja vio al final
CLAVE_PLANO_ABIERTO = "hoja_plano_abierto"  # la barra pidio abrir el flujo de importar
CLAVE_PLANO_DIRECTORIO = "hoja_plano_directorio"  # carpeta temporal de los planos subidos
CLAVE_PLANO_FUSION = "hoja_plano_fusion"  # el informe de la ultima fusion
CLAVE_PLANO_MENSAJE = "hoja_plano_mensaje"  # (tipo, texto) del ultimo intento de leer o declarar
CLAVE_SELECTORES = "hoja_selectores"  # sube para que los selectores vuelvan a la version abierta
CLAVE_MENSAJE = "hoja_mensaje"  # (tipo, texto) del ultimo intento de guardar, restaurar o cotizar
CLAVE_ASISTENTE = "hoja_asistente"  # la `SesionDeAsistente` vigente (o ausente)
CLAVE_ASISTENTE_PEDIDO = "hoja_asistente_pedido"
CLAVE_ASISTENTE_PROVEEDOR = "hoja_asistente_proveedor"
CLAVE_ASISTENTE_AVISO = "hoja_asistente_aviso"  # (tipo, texto) del ultimo intento
CLAVE_ASISTENTE_RESPUESTA = "hoja_asistente_respuesta"  # la respuesta a una pregunta de la IA
CLAVE_ASISTENTE_RESUMEN = "hoja_asistente_resumen"  # (estados, resumen) del resultado hipotetico

# Claves de widgets (los selectores llevan ademas el numero de `CLAVE_SELECTORES`).
CLAVE_PESTANA = "hoja_pestana"
CLAVE_PROYECTO = "hoja_proyecto"
CLAVE_PLANO_ARCHIVO = "hoja_plano_archivo"
CLAVE_PLANO_UNIDAD = "hoja_plano_unidad"
PREFIJO_ALTURA = "hoja_plano_altura_"
PREFIJO_CIRCUITO = "hoja_plano_circuito_"
CLAVE_VERSION = "hoja_version"
CLAVE_FUENTE = "hoja_fuente"
CLAVE_RESPONSABLE = "hoja_responsable"
PREFIJO_EDITOR = "hoja_editor_"

SIN_PROYECTO = "(borrador nuevo, sin guardar)"
SIN_VERSIONES = "Este proyecto aún no tiene versiones"
GUARDAR_PRIMERA = "Guardar primera versión"
TABLAS_CON_ESTADO = hoja.TABLAS_CON_ESTADO

_AYUDA_ESPACIO = (
    "Describa el espacio en metros (eje z hacia arriba desde el piso terminado). Cada fila cita un "
    "origen de medida; un punto de agua fria sin recorrido declarado usa el recorrido propuesto. "
    "Los vertices se escriben como `x,y,z; x,y,z` y la longitud de cada tramo se calcula."
)


# --- acceso al caso -------------------------------------------------------------------------------


@contextmanager
def _sesion() -> Iterator[Any]:
    """Una sesion sobre el caso abierto, o `None` si el archivo no existe (no se crea nada) o no se
    puede preparar (el mensaje ya se mostro). El caso se abre por `preparar_base` (RV-5)."""
    ruta = ruta_caso()
    if not ruta.exists():
        yield None
        return
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(str(error))
        yield None
        return
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            yield entrega.con_anexos_de_cadena(sesion)  # la cadena cubre el espacio (RF-83)
    finally:
        motor.dispose()


def _responsable() -> str:
    """Quien responde por lo que se guarda (RF-82): con el acceso encendido, la persona de la
    sesion; con el acceso apagado (transicion), lo escrito en el cuadro. Sin sesion vigente
    devuelve vacio: el guardado lo rechaza y la pantalla pide entrar."""
    try:
        return ui_sesion.responsable_de_la_hoja(st.session_state.get(CLAVE_RESPONSABLE, ""))
    except PermissionError:
        return ""


def _mensaje(tipo: str, texto: str) -> None:
    st.session_state[CLAVE_MENSAJE] = (tipo, texto)


def _error_de_base(error: Exception) -> str:
    return (
        "No se pudo leer o escribir el caso: "
        f"{getattr(error, 'orig', None) or error}. Revise que el archivo exista y no este abierto "
        "en otro programa."
    )


# --- estado ---------------------------------------------------------------------------------------


def _borrador() -> hoja.Borrador:
    actual = st.session_state.get(CLAVE_BORRADOR)
    if not isinstance(actual, hoja.Borrador):
        actual = hoja.Borrador(fecha=date.today())
        st.session_state[CLAVE_BORRADOR] = actual
    if not isinstance(st.session_state.get(CLAVE_PARTIDA), hoja.Borrador):
        st.session_state[CLAVE_PARTIDA] = actual
    return actual


def _partida() -> hoja.Borrador:
    _borrador()
    return st.session_state[CLAVE_PARTIDA]


def _abierta() -> hoja.VersionAbierta | None:
    return st.session_state.get(CLAVE_ABIERTA)


def _generacion() -> int:
    return st.session_state.setdefault(CLAVE_GENERACION, 0)


def _resembrar() -> None:
    """Los editores vuelven a sembrarse con el borrador vigente (cambia la clave de cada uno)."""
    st.session_state[CLAVE_PARTIDA] = _borrador()
    st.session_state[CLAVE_GENERACION] = _generacion() + 1


def _poner_borrador(nuevo: hoja.Borrador, *, resembrar: bool = False) -> None:
    """Fija el borrador vigente (completando las composiciones de las partidas nuevas) y olvida el
    resultado y el Excel, que ya no son de este borrador."""
    if nuevo == st.session_state.get(CLAVE_BORRADOR):
        return
    abierta = _abierta()
    try:
        with _sesion() as sesion:
            if sesion is not None:
                lista = None
                if abierta is not None:
                    lista = hoja.lista_de_version(sesion, abierta.proyecto, abierta.codigo)
                nuevo = hoja.completar_composiciones(Catalogo(sesion), nuevo, lista=lista)
    except (SQLAlchemyError, CatalogoIncompleto) as error:
        st.warning(_error_de_base(error))
    st.session_state[CLAVE_BORRADOR] = nuevo
    st.session_state.pop(CLAVE_RESULTADO, None)
    st.session_state.pop(CLAVE_EXCEL, None)
    if resembrar:
        _resembrar()


def _base_de_comparacion() -> hoja.Borrador:
    abierta = _abierta()
    if abierta is not None:
        return abierta.borrador
    actual = _borrador()
    return hoja.Borrador(fecha=actual.fecha, moneda=actual.moneda)


def _calculo() -> tuple[hoja.ResultadoHoja, list]:
    """El resultado y los cambios del borrador vigente; se calculan una vez por borrador."""
    actual = _borrador()
    guardado = st.session_state.get(CLAVE_RESULTADO)
    if guardado is None or guardado[0] is not actual:
        resultado = hoja.elaborar_borrador(actual)
        cambios = hoja.cambios_entre(_base_de_comparacion(), actual)
        guardado = (actual, resultado, cambios)
        st.session_state[CLAVE_RESULTADO] = guardado
    return guardado[1], guardado[2]


# --- version abierta y aviso de ediciones sin guardar --------------------------------------------


def _abrir(proyecto: str | None, codigo: str | None) -> None:
    """Abre la version elegida (o un borrador nuevo) y renueva la siembra de los editores."""
    if proyecto is None or codigo is None:
        # Sin proyecto, o un proyecto nuevo que todavia no tiene version: borrador en blanco.
        st.session_state[CLAVE_ABIERTA] = None
        st.session_state[CLAVE_ABIERTA_EN] = (str(ruta_caso()), proyecto, None)
        st.session_state[CLAVE_BORRADOR] = hoja.Borrador(fecha=date.today())
    else:
        try:
            with _sesion() as sesion:
                abierta = hoja.abrir_version(
                    sesion,
                    Catalogo(sesion),
                    proyecto,
                    codigo,
                    fecha_evaluacion=date.today(),
                    responsable=_responsable() or hoja.RESPONSABLE_POR_OMISION,
                )
        except hoja.HojaInvalida as error:
            st.error(str(error))
            return
        except SQLAlchemyError as error:
            st.error(_error_de_base(error))
            return
        st.session_state[CLAVE_ABIERTA] = abierta
        st.session_state[CLAVE_ABIERTA_EN] = (str(ruta_caso()), proyecto, codigo)
        st.session_state[CLAVE_BORRADOR] = abierta.borrador
        if abierta.instantanea.creadas:
            _mensaje(
                "info",
                "Se creo y registro la instantanea de las composiciones de esta version "
                f"({len(abierta.instantanea.creadas)} partidas): sus APU ya no cambian si cambia "
                "el catalogo.",
            )
    st.session_state.pop(CLAVE_RESULTADO, None)
    st.session_state.pop(CLAVE_EXCEL, None)
    _volver_los_selectores_a_lo_abierto()
    _resembrar()


def _volver_los_selectores_a_lo_abierto() -> None:
    """Los selectores cambian de clave y, al ser nuevos, parten de lo que esta abierto."""
    st.session_state[CLAVE_SELECTORES] = st.session_state.get(CLAVE_SELECTORES, 0) + 1


def _clave_selector(base: str) -> str:
    n = st.session_state.get(CLAVE_SELECTORES, 0)
    return base if n == 0 else f"{base}_{n}"


def _descartar_y_abrir(proyecto: str | None, codigo: str | None) -> None:
    _abrir(proyecto, codigo)


def _seguir_editando() -> None:
    _volver_los_selectores_a_lo_abierto()


def _seguir_al_proyecto_de_la_barra(proyectos: Sequence[str], clave_proyecto: str) -> None:
    """El proyecto que el usuario abre en la barra superior es el que muestra la hoja.

    Solo se actua cuando el proyecto de la barra CAMBIA respecto del que la hoja vio por ultima vez:
    asi lo que el usuario elige despues en el selector de la hoja no se pisa en cada ejecucion. Un
    nombre que ya no esta en el caso se ignora.
    """
    de_la_barra = caso.proyecto_abierto()
    if de_la_barra == st.session_state.get(CLAVE_PROYECTO_DE_LA_BARRA):
        return
    st.session_state[CLAVE_PROYECTO_DE_LA_BARRA] = de_la_barra
    if de_la_barra in proyectos:
        st.session_state[clave_proyecto] = de_la_barra


def _selector_de_version(cambios: Sequence) -> None:
    """Proyecto y version a editar; cambiar con ediciones sin guardar pide confirmar (15c)."""
    ruta = str(ruta_caso())
    abierto = st.session_state.get(CLAVE_ABIERTA_EN)
    clave_proyecto = _clave_selector(CLAVE_PROYECTO)
    with _sesion() as sesion:
        proyectos = [] if sesion is None else list(sesion.scalars(select(models.Proyecto.nombre)))
        opciones = [SIN_PROYECTO, *proyectos]
        _seguir_al_proyecto_de_la_barra(proyectos, clave_proyecto)
        elegido = st.session_state.get(clave_proyecto)
        if elegido is None and abierto is not None and abierto[1] in proyectos:
            elegido = abierto[1]
        versiones: list[hoja.FilaVersion] = []
        if sesion is not None and elegido in proyectos:
            versiones = hoja.historial_de_versiones(sesion, elegido)
    if not proyectos:
        return
    columnas = st.columns(2)
    proyecto = columnas[0].selectbox(
        "Proyecto",
        opciones,
        index=opciones.index(elegido) if elegido in opciones else 0,
        key=clave_proyecto,
    )
    codigo = None
    if proyecto != SIN_PROYECTO:
        codigos = [v.codigo for v in versiones if not v.descartada] or [v.codigo for v in versiones]
        if codigos:
            vigente = next((v.codigo for v in versiones if v.vigente), codigos[-1])
            abierta_aqui = abierto[2] if abierto is not None and abierto[1] == proyecto else None
            inicial = abierta_aqui if abierta_aqui in codigos else vigente
            codigo = columnas[1].selectbox(
                "Version",
                codigos,
                index=codigos.index(inicial) if inicial in codigos else 0,
                key=_clave_selector(CLAVE_VERSION),
                format_func=lambda c: f"{c} (vigente)" if c == vigente else c,
            )
        else:
            columnas[1].caption(SIN_VERSIONES)
    deseado = (ruta, None if proyecto == SIN_PROYECTO else proyecto, codigo)
    if abierto == deseado:
        return
    if deseado[1] is not None and codigo is None and _abierta() is None:
        # Un proyecto sin versiones adopta el borrador que ya hay (se describio el espacio antes de
        # crearlo o abrirlo): no se descarta nada, solo cambia a que proyecto pertenece.
        st.session_state[CLAVE_ABIERTA_EN] = deseado
        return
    if abierto is None and not cambios and deseado[1] is None:
        st.session_state[CLAVE_ABIERTA_EN] = deseado
        return
    if cambios and abierto is not None:
        st.warning(
            f"Tiene {len(cambios)} cambios sin guardar. Si abre otra version se pierden: guarde "
            "primero o descarte."
        )
        izquierda, derecha = st.columns(2)
        izquierda.button(
            "Descartar los cambios y abrir la version elegida",
            on_click=_descartar_y_abrir,
            args=(deseado[1], deseado[2]),
        )
        derecha.button("Seguir editando", on_click=_seguir_editando)
        return
    _abrir(deseado[1], deseado[2])
    st.rerun()


# --- guardar y exportar ---------------------------------------------------------------------------


def _atender() -> str | None:
    """La accion pendiente de la barra superior (`ui.caso.pedir_accion`). Se guarda en la sesion
    hasta que la hoja pueda atenderla: abrir una version reinicia la ejecucion y la accion no
    puede perderse en ese reinicio."""
    nueva = caso.tomar_accion()
    if nueva is not None:
        st.session_state[CLAVE_ACCION_PENDIENTE] = nueva
    return st.session_state.get(CLAVE_ACCION_PENDIENTE)


def _guardar() -> None:
    """Callback del boton Guardar: una sola sesion; el resultado se dice en el mensaje."""
    abierta, borrador = _abierta(), _borrador()
    if abierta is None:
        _guardar_primera(borrador)
        return
    try:
        with _sesion() as sesion:
            guardada = hoja.guardar_version(
                sesion,
                Catalogo(sesion),
                abierta,
                borrador,
                fuente=st.session_state.get(CLAVE_FUENTE, ""),
                responsable=_responsable(),
            )
    except hoja.HojaInvalida as error:
        _mensaje("error", str(error))
        return
    except (SQLAlchemyError, ValueError, CatalogoIncompleto) as error:
        _mensaje("error", f"No se guardo nada: {getattr(error, 'orig', None) or error}")
        return
    if guardada is None:
        _mensaje("info", "No hay cambios para guardar.")
        return
    _mensaje(
        "success",
        f"Se guardo la version {guardada.codigo} con {guardada.cambios} cambios registrados.",
    )
    _cerrar_asistente_al_guardar(guardada.codigo)
    _abrir(abierta.proyecto, guardada.codigo)
    st.session_state[CLAVE_FUENTE] = ""


def _proyecto_sin_versiones() -> str | None:
    """El proyecto elegido que aun no tiene versiones (al que pertenece el borrador), o `None`."""
    abierto = st.session_state.get(CLAVE_ABIERTA_EN)
    if _abierta() is not None or abierto is None:
        return None
    return abierto[1]


def _guardar_primera(borrador: hoja.Borrador) -> None:
    """Callback de Guardar primera version: crea la 001 del proyecto nuevo y la abre."""
    proyecto = _proyecto_sin_versiones()
    if proyecto is None:
        _mensaje("error", "Elija o cree un proyecto (barra superior) para poder guardar.")
        return
    try:
        with _sesion() as sesion:
            guardada = hoja.crear_primera_version(
                sesion,
                Catalogo(sesion),
                proyecto,
                borrador,
                fuente=st.session_state.get(CLAVE_FUENTE, ""),
                responsable=_responsable(),
            )
    except hoja.HojaInvalida as error:
        _mensaje("error", str(error))
        return
    except (SQLAlchemyError, ValueError, CatalogoIncompleto) as error:
        _mensaje("error", f"No se guardo nada: {getattr(error, 'orig', None) or error}")
        return
    _mensaje(
        "success",
        f"Se guardo la primera version {guardada.codigo} del proyecto {proyecto} "
        f"(total {formatear_decimal(guardada.total, 2)}). Quedo registrada su creacion, con su "
        "fuente y su responsable.",
    )
    _cerrar_asistente_al_guardar(guardada.codigo)
    _abrir(proyecto, guardada.codigo)
    st.session_state[CLAVE_FUENTE] = ""


def _preparar_excel() -> None:
    """Callback de Preparar Excel: el libro se genera aqui y no antes."""
    borrador = _borrador()
    resultado, _ = _calculo()
    abierta = _abierta()
    trazabilidad, precios, hojas_de_control = None, (), []
    try:
        if abierta is not None:
            with _sesion() as sesion:
                trazabilidad = hoja.tabla_de_trazabilidad(sesion, abierta.proyecto, abierta.codigo)
                precios = hoja.precios_de_version(
                    sesion, abierta.proyecto, abierta.codigo, fecha_evaluacion=date.today()
                )
                hojas_de_control = control.tablas_de_control(
                    sesion, abierta.proyecto, Catalogo(sesion)
                )
        contenido = hoja.excel_de_hoja_en_bytes(
            resultado,
            borrador,
            trazabilidad=trazabilidad,
            precios=precios,
            control=hojas_de_control,
        )
    except (SQLAlchemyError, ValueError) as error:
        _mensaje("error", f"No se pudo preparar el Excel: {getattr(error, 'orig', None) or error}")
        return
    nombre = f"hoja_{abierta.codigo}.xlsx" if abierta is not None else "hoja_borrador.xlsx"
    st.session_state[CLAVE_EXCEL] = (nombre, contenido)


def _panel_de_guardado(cambios: Sequence, accion: str | None) -> None:
    abierta = _abierta()
    pide_guardar = accion == "guardar_version"
    if accion == "exportar_excel":
        _preparar_excel()
    if cambios:
        st.warning(
            f"{len(cambios)} cambios sin guardar. Si cierra la hoja o abre otra version se pierden."
        )
    proyecto_nuevo = _proyecto_sin_versiones()
    if proyecto_nuevo is not None:
        st.info(
            f"{SIN_VERSIONES}. Describa el espacio (o importe un plano) y guarde la primera "
            "version abajo, con su fuente y su responsable."
        )
    with st.expander("Guardar version y exportar a Excel", expanded=bool(cambios) or pide_guardar):
        if abierta is None and proyecto_nuevo is None:
            st.caption(
                "Este borrador no pertenece a ningun proyecto: elija o cree uno (barra superior) "
                "para poder guardar. El Excel se puede preparar igual."
            )
        elif abierta is None:
            st.caption(
                f"Proyecto {proyecto_nuevo}: la primera version registra su creacion con la "
                "fuente y el responsable. El Excel se puede preparar igual."
            )
        else:
            st.caption(
                f"Version abierta: {abierta.codigo}. Cada guardado crea una version nueva y "
                "registra cada celda cambiada, con su fuente y su responsable."
            )
            if abierta.solo_lectura:
                st.warning(
                    "Esta version esta en solo lectura: alguna partida ya no tiene composicion "
                    "vigente en el catalogo."
                )
        fuente, responsable = st.columns(2)
        fuente.text_input(
            "Fuente de la medida (de donde salen los datos)"
            if proyecto_nuevo is not None
            else "Fuente del cambio (por que y con que respaldo)",
            key=CLAVE_FUENTE,
        )
        ui_sesion.caja_de_responsable("Responsable", key=CLAVE_RESPONSABLE, contenedor=responsable)
        if abierta is not None:
            motivo = hoja.motivo_para_no_guardar(
                abierta.borrador,
                _borrador(),
                st.session_state.get(CLAVE_FUENTE, ""),
                _responsable(),
            )
        elif proyecto_nuevo is not None:
            motivo = hoja.motivo_para_no_crear_primera(
                _borrador(),
                st.session_state.get(CLAVE_FUENTE, ""),
                _responsable(),
            )
        else:
            motivo = "Elija o cree un proyecto (barra superior) para poder guardar."
        izquierda, derecha = st.columns(2)
        izquierda.button(
            GUARDAR_PRIMERA if proyecto_nuevo is not None else "Guardar version",
            on_click=_guardar,
            disabled=motivo is not None or (abierta is not None and abierta.solo_lectura),
            help=motivo,
            type="primary",
        )
        derecha.button("Preparar Excel", on_click=_preparar_excel)
        excel = st.session_state.get(CLAVE_EXCEL)
        if excel is not None:
            st.download_button(
                "Descargar Excel",
                excel[1],
                file_name=excel[0],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


# --- asistente de IA (S4, UC-09): propone, la persona decide ------------------------------------


def _usuario_de_la_sesion() -> str:
    """Quien decide: el usuario de la sesion de acceso (S3); la IA nunca es el responsable.

    Con el acceso apagado (transicion) es la persona de desarrollo de `ui.sesion`. Sin sesion
    vigente devuelve vacio, como `_responsable`: la decision se rechaza y la pantalla pide entrar.
    """
    try:
        return ui_sesion.responsable_actual()
    except PermissionError:
        return ""


def _proveedores_del_asistente() -> dict[str, Any]:
    """`{nombre: (proveedor | None, motivo)}` de la instalacion; los tests lo reemplazan."""
    from asistente.instalacion import proveedores_de_la_instalacion

    return proveedores_de_la_instalacion()


def _prefijos_de_maprex() -> tuple[str, ...]:
    """Los prefijos de codigo de MaPreX de la instalacion; los tests lo reemplazan."""
    from asistente.instalacion import prefijos_de_maprex

    return prefijos_de_maprex()


def _tarifa_del_asistente(proveedor: Any) -> Any:
    """La tarifa del modelo del proveedor (cero si es local), o `None` si no tiene tarifa."""
    try:
        return tarifa_de(proveedor.modelo, local=not proveedor.envia_fuera_del_equipo)
    except KeyError:
        return None


def _catalogo_del_asistente(sesion: Any) -> Any:
    """Las partidas del catalogo como las ve el asistente (sin precios ni composicion).

    La busqueda semantica (UC-03) se arma en la primera busqueda: cargar el modelo cuesta segundos.
    """
    from asistente.catalogo import CatalogoDeLaBase, PartidaVista
    from core.contracts.dominio import Dominio

    if sesion is None:  # sin base: el catalogo esta vacio
        return CatalogoDeLaBase([])
    prefijos = _prefijos_de_maprex()
    partidas = [
        PartidaVista(
            p.codigo,
            p.descripcion,
            p.unidad,
            Dominio(p.dominio),
            de_maprex=p.codigo.startswith(prefijos),
        )
        for p in Catalogo(sesion).partidas()
    ]
    armado: list[Any] = []

    def semantica(texto: str) -> list[tuple[str, float]]:
        if not armado:
            from ml.normalization import proponedor

            armado.append(proponedor({p.codigo: p.descripcion for p in partidas}))
        return [(s.codigo, s.puntaje) for s in armado[0](texto).similares]

    return CatalogoDeLaBase(partidas, semantica if partidas else None)


def _aviso_del_asistente(tipo: str, texto: str) -> None:
    st.session_state[CLAVE_ASISTENTE_AVISO] = (tipo, texto)


def _proponer_con_asistente() -> None:
    """Callback de «Proponer»: corre el bucle; el borrador NO cambia hasta que se acepta."""
    ofertas = _proveedores_del_asistente()
    proveedor = ofertas.get(st.session_state.get(CLAVE_ASISTENTE_PROVEEDOR, ""), (None, ""))[0]
    if proveedor is None:
        _aviso_del_asistente("error", "Elija un proveedor disponible.")
        return
    tarifa = _tarifa_del_asistente(proveedor)
    if tarifa is None:
        _aviso_del_asistente(
            "error",
            f"No hay tarifa para el modelo {proveedor.modelo}: pida al administrador agregarla.",
        )
        return
    abierta, borrador = _abierta(), _borrador()
    proyecto = abierta.proyecto if abierta else (_proyecto_sin_versiones() or "")
    try:
        with _sesion() as sesion:
            registro = RegistroIA(sesion.connection()) if sesion is not None else None
            servicios = Servicios(
                catalogo=_catalogo_del_asistente(sesion),
                tarifa=tarifa,
                auditar=lambda b: hoja.elaborar_borrador(b).elaboracion.informe,
                responder=lambda _pregunta: ESPERAR,  # la pantalla contesta (9g)
                registro=registro,
                proyecto=proyecto,
                version_partida=abierta.codigo if abierta else "",
            )
            propuesto = ia_servicio.proponer(
                proveedor,
                st.session_state.get(CLAVE_ASISTENTE_PEDIDO, ""),
                borrador,
                servicios,
                Topes(),
            )
            if sesion is not None:
                sesion.commit()
    except SQLAlchemyError as error:
        _aviso_del_asistente("error", _error_de_base(error))
        return
    st.session_state[CLAVE_ASISTENTE] = propuesto
    _aviso_del_asistente("info", propuesto.resultado.mensaje)


def _decidir_propuesta(propuesta_id: str, estado: EstadoPropuesta) -> None:
    """Callback de Aceptar, Aceptar y editar o Rechazar de UNA propuesta."""
    propuesto = st.session_state.get(CLAVE_ASISTENTE)
    if propuesto is None:
        return
    usuario = _usuario_de_la_sesion()
    if not usuario:
        _aviso_del_asistente("error", ui_sesion.MENSAJE_SIN_ENTRAR)
        return
    try:
        with _sesion() as sesion:
            registro = RegistroIA(sesion.connection()) if sesion is not None else None
            ia_servicio.decidir(propuesto, propuesta_id, estado, usuario, registro)
            if sesion is not None:
                sesion.commit()
        nuevo = ia_servicio.borrador_resultante(propuesto)
    except ia_servicio.DependenciaPendiente as error:
        _aviso_del_asistente("warning", str(error))
        return
    except KeyError:
        _aviso_del_asistente("warning", f"{propuesta_id} ya no esta pendiente: ya se decidio.")
        return
    except hoja.HojaInvalida as error:
        _aviso_del_asistente("error", f"No se pudo aplicar {propuesta_id}: {error}")
        return
    except SQLAlchemyError as error:
        _aviso_del_asistente("error", _error_de_base(error))
        return
    _poner_borrador(nuevo, resembrar=True)
    if estado is not EstadoPropuesta.RECHAZADA and not st.session_state.get(CLAVE_FUENTE):
        st.session_state[CLAVE_FUENTE] = ia_servicio.fuente_del_cambio(propuesto)
    _aviso_del_asistente("success", f"{propuesta_id}: {estado.value}.")


def _responder_al_asistente(cancelar: bool = False) -> None:
    """Callback de «Responder» (o «Cancelar»): reanuda la sesion pausada por una pregunta (9g).

    La respuesta sale del estado de la pantalla en el acto: si lleva una clave, nunca se queda.
    """
    propuesto = st.session_state.get(CLAVE_ASISTENTE)
    texto = st.session_state.pop(CLAVE_ASISTENTE_RESPUESTA, "")
    if propuesto is None or propuesto.resultado.pregunta is None:
        return
    ia_servicio.responder(propuesto, None if cancelar else texto)
    _aviso_del_asistente("info", propuesto.resultado.mensaje)


def _descartar_asistente() -> None:
    """Descarta la sesion: lo aceptado se queda en el borrador; lo pendiente no entra."""
    st.session_state.pop(CLAVE_ASISTENTE, None)
    st.session_state.pop(CLAVE_ASISTENTE_AVISO, None)
    st.session_state.pop(CLAVE_ASISTENTE_RESUMEN, None)


def _cerrar_asistente_al_guardar(codigo_version: str) -> None:
    """Tras guardar: la sesion queda marcada con la version en que entro (anexo `ia.json`)."""
    propuesto = st.session_state.get(CLAVE_ASISTENTE)
    if propuesto is None or not propuesto.pendientes.aceptadas():
        return
    try:
        with _sesion() as sesion:
            if sesion is not None:
                RegistroIA(sesion.connection()).marcar_guardada(
                    propuesto.resultado.sesion, codigo_version
                )
                sesion.commit()
    except SQLAlchemyError as error:
        _mensaje(
            "warning",
            f"La version se guardo, pero no se pudo anotar la sesion del asistente: {error}",
        )
        return
    _descartar_asistente()


def _pintar_pregunta(propuesto: Any) -> None:
    """La pregunta del modelo, rotulada como tal y escapada: es texto ajeno (RV-14, §8.7)."""
    st.warning(
        "Pregunta generada por la IA: no escriba contrasenas, claves ni precios.\n\n"
        + texto_seguro(propuesto.resultado.pregunta)
    )
    st.text_input("Su respuesta", key=CLAVE_ASISTENTE_RESPUESTA)
    responder, cancelar = st.columns(2)
    responder.button("Responder", on_click=_responder_al_asistente, key="hoja_asistente_responder")
    cancelar.button(
        "Cancelar la sesion",
        on_click=_responder_al_asistente,
        args=(True,),
        key="hoja_asistente_cancelar",
    )


def _resumen_hipotetico(propuesto: Any) -> Any:
    """El resultado hipotetico, una vez por conjunto de decisiones (no en cada edicion)."""
    estados = tuple((p.id, p.estado) for p in propuesto.pendientes.propuestas)
    guardado = st.session_state.get(CLAVE_ASISTENTE_RESUMEN)
    if guardado is None or guardado[0] != estados:
        resumen = ia_servicio.resumen_hipotetico(ia_servicio.hipotetico(propuesto))
        guardado = (estados, resumen)
        st.session_state[CLAVE_ASISTENTE_RESUMEN] = guardado
    return guardado[1]


def _pintar_propuestas(propuesto: Any) -> None:
    if propuesto.resultado.pregunta is not None:
        _pintar_pregunta(propuesto)
        return
    for propuesta in propuesto.pendientes.propuestas:
        texto, estado, botones = st.columns([6, 2, 3])
        texto.markdown(texto_seguro(ia_servicio.descripcion(propuesta)))
        estado.caption(propuesta.estado.value)
        if propuesta.estado is EstadoPropuesta.PENDIENTE:
            aceptar, editar, rechazar = botones.columns(3)
            for columna, rotulo, nuevo in (
                (aceptar, "Aceptar", EstadoPropuesta.ACEPTADA),
                (editar, "Aceptar y editar", EstadoPropuesta.EDITADA),
                (rechazar, "Rechazar", EstadoPropuesta.RECHAZADA),
            ):
                columna.button(
                    rotulo,
                    key=f"hoja_asistente_{nuevo.value}_{propuesta.id}",
                    on_click=_decidir_propuesta,
                    args=(propuesta.id, nuevo),
                )
        if propuesta.supuestos:
            texto.caption(
                texto_seguro(
                    "Supuestos de la IA: " + "; ".join(f"{c}: {m}" for c, m in propuesta.supuestos)
                )
            )
    try:
        hipotetico = _resumen_hipotetico(propuesto)
    except hoja.HojaInvalida as error:
        st.caption(
            "No se puede calcular el resultado si se aceptara todo: " + texto_seguro(str(error))
        )
    else:
        por_severidad = ", ".join(f"{k}: {v}" for k, v in sorted(hipotetico.hallazgos.items()))
        st.caption(
            "Si aceptara todo, el SISTEMA calcularia un total de "
            f"{_dinero(hipotetico.total, hipotetico.moneda)} "
            f"y {sum(hipotetico.hallazgos.values())} hallazgos del auditor "
            f"({por_severidad or 'ninguno'})."
        )
    st.button(
        "Descartar lo pendiente", on_click=_descartar_asistente, key="hoja_asistente_descartar"
    )


def _panel_asistente() -> None:
    """UC-09 en la hoja: pedido, vista previa y costo, propuestas pendientes y su decision."""
    abierta = _abierta()
    if abierta is not None and abierta.solo_lectura:
        return  # 9i: el asistente no se abre en una version de solo lectura
    ofertas = _proveedores_del_asistente()
    with st.expander(
        "Asistente de IA: propone, usted decide", expanded=CLAVE_ASISTENTE in st.session_state
    ):
        disponibles = {n: o[0] for n, o in ofertas.items() if o[0] is not None}
        if not disponibles:
            st.caption(" ".join(sorted({o[1] for o in ofertas.values() if o[1]})))
            return
        for nombre, (proveedor, motivo) in ofertas.items():
            if proveedor is None:
                st.caption(f"{nombre}: {motivo}")
        nombre = st.selectbox("Proveedor", sorted(disponibles), key=CLAVE_ASISTENTE_PROVEEDOR)
        proveedor = disponibles[nombre]
        pedido = st.text_area("Que necesita armar (en sus palabras)", key=CLAVE_ASISTENTE_PEDIDO)
        vista = ia_privacidad.vista_previa(
            pedido, _borrador(), nube=proveedor.envia_fuera_del_equipo
        )
        tarifa = _tarifa_del_asistente(proveedor)
        if tarifa is None:
            st.caption(f"No hay tarifa para el modelo {proveedor.modelo}: no se puede estimar.")
        else:
            estimado = ia_servicio.estimar_costo(tarifa)
            st.caption(
                f"Destino: {vista['destino']}. Estimacion de costo por tarea (cota): "
                f"{estimado:.2f} USD. "
                "El pedido viaja tal como lo escribe: no escriba datos personales."
            )
        with st.expander("Lo que se enviara"):
            st.text(vista["texto"])
        st.button(
            "Proponer",
            on_click=_proponer_con_asistente,
            disabled=not pedido.strip() or tarifa is None,
            type="primary",
        )
        aviso = st.session_state.get(CLAVE_ASISTENTE_AVISO)
        if aviso is not None:
            getattr(st, aviso[0])(texto_seguro(aviso[1]))
        propuesto = st.session_state.get(CLAVE_ASISTENTE)
        if propuesto is not None:
            _pintar_propuestas(propuesto)


# --- ayudas de pantalla ---------------------------------------------------------------------------


def _opciones(*enums: type) -> list[str]:
    return [miembro.value for enum in enums for miembro in enum]


def _configuracion(tabla: str) -> dict[str, object]:
    """Columnas con lista cerrada como selectores; el resto, texto (los numeros se validan al
    reconstruir el espacio, con el campo culpable en el mensaje)."""
    por_tabla: dict[str, dict[str, list[str]]] = {
        "origenes": {"tipo": _opciones(TipoOrigen)},
        "fuentes": {"especialidad": _opciones(Especialidad), "tipo": _opciones(TipoFuente)},
        "puntos": {
            "especialidad": _opciones(Especialidad),
            "tipo": _opciones(TipoPunto),
            "superficie": _opciones(SuperficiePunto),
        },
        "tramos": {"superficie": _opciones(SuperficieTramo), "empotrado": ["", "si", "no"]},
    }
    listas = por_tabla.get(tabla, {})
    rotulos = hoja.ROTULOS_DE_COLUMNA[tabla]
    configuracion: dict[str, object] = {}
    for columna in hoja.COLUMNAS[tabla]:
        if columna in listas:
            # el usuario ve el nombre claro; la celda sigue guardando el valor interno
            configuracion[columna] = st.column_config.SelectboxColumn(
                rotulos[columna], options=listas[columna], format_func=hoja.rotulo_de_valor
            )
        else:
            configuracion[columna] = st.column_config.TextColumn(rotulos[columna])
    return configuracion


def _dinero(valor: Decimal, moneda: str) -> str:
    return f"{formatear_decimal(valor, DECIMALES_PRESENTACION)} {moneda}"


def _pintar_estado(
    hueco: Any, tabla: str, filas: Sequence[dict[str, str]], estado: dict[str, hoja.EstadoFila]
) -> None:
    prefijo = TABLAS_CON_ESTADO[tabla]
    with hueco:
        if not filas:
            st.caption("Sin filas.")
            return
        estados = [estado.get(f"{prefijo}:{f['id']}", hoja.EstadoFila(None, "")) for f in filas]
        st.dataframe(
            DataFrame({"Fila": [f["id"] for f in filas], "Estado": [e.texto for e in estados]}),
            hide_index=True,
            width="stretch",
        )


def _clave(*partes: object) -> str:
    return PREFIJO_EDITOR + "_".join(str(p) for p in (*partes, _generacion()))


# --- pestana Espacio y metrajes ------------------------------------------------------------------


def _cantidades(items: Sequence[Any]) -> None:
    st.subheader("Cantidades derivadas")
    if not items:
        st.info(
            "El borrador todavia no deriva cantidades: agregue un ambiente, una fuente y los "
            "puntos de agua, de datos o de electricidad."
        )
        return
    st.dataframe(
        DataFrame(
            {
                "Partida": [i.codigo_partida for i in items],
                "Descripcion": [i.descripcion for i in items],
                "Unidad": [i.unidad for i in items],
                "Cantidad": [formatear_decimal(i.cantidad, DECIMALES_PRESENTACION) for i in items],
                "Origen": [i.origen_id for i in items],
            }
        ),
        hide_index=True,
        width="stretch",
    )


def _pestana_espacio() -> None:
    _importar_plano()
    st.caption(_AYUDA_ESPACIO)
    base = hoja.filas_desde_espacio(_partida().espacio)
    huecos: dict[str, object] = {}
    editadas: dict[str, list[dict[str, object]]] = {}
    for tabla, columnas in hoja.COLUMNAS.items():
        st.subheader(hoja.ROTULOS[tabla].capitalize())
        if tabla in TABLAS_CON_ESTADO:
            editor, huecos[tabla] = st.columns([3, 2])
        else:
            editor = st.container()
        with editor:
            tabla_editada = st.data_editor(
                DataFrame(base[tabla], columns=list(columnas), dtype=str),
                num_rows="dynamic",
                hide_index=True,
                width="stretch",
                column_config=_configuracion(tabla),
                key=_clave(tabla),
            )
        editadas[tabla] = tabla_editada.to_dict("records")

    try:
        espacio = hoja.espacio_desde_filas(editadas, base=_borrador().espacio)
        _poner_borrador(replace(_borrador(), espacio=espacio))
    except hoja.HojaInvalida as error:
        st.error(f"{error}. La hoja sigue con el ultimo borrador valido.")

    resultado, _ = _calculo()
    filas_borrador = hoja.filas_desde_espacio(_borrador().espacio)
    for tabla, hueco in huecos.items():
        _pintar_estado(hueco, tabla, filas_borrador[tabla], resultado.estado)

    _cantidades(resultado.items)
    presupuesto = resultado.elaboracion.presupuesto
    st.metric("Total del presupuesto", _dinero(presupuesto.total, presupuesto.moneda))
    if resultado.elaboracion.pendientes:
        st.warning(
            f"{len(resultado.elaboracion.pendientes)} partida(s) no tienen composicion en el "
            "catalogo del caso: quedan pendientes y no suman al total."
        )
    st.subheader("Informe de auditoria")
    mostrar_informe(resultado.elaboracion.informe)


# --- importar un plano (RF-50, RF-51) -------------------------------------------------------------

_AYUDA_PLANO = (
    "Suba un plano en formato DXF o IFC. El plano crea filas en el borrador de esta hoja, con el "
    "archivo como origen de medida, y un informe de lo que importó, lo que no reconoció, lo que "
    "aproximó y lo que queda pendiente. Nada salta la hoja ni la auditoría: las filas entran para "
    "que las revise."
)
_AYUDA_CIRCUITOS = (
    "El plano no dice cuántos conductores tiene cada circuito ni cuántos puntos admite: se "
    "supusieron. Confírmelos o corríjalos; mientras sean supuestos, la auditoría lo advierte."
)
_AVISO_PENDIENTES = (
    "Si fusiona ahora, los ambientes sin altura entran con 2,5 m provisionales y los circuitos "
    "supuestos quedan marcados en la auditoría. Puede cargarlos antes o corregirlos después en las "
    "tablas."
)
ROTULO_IMPORTAR = "Importar plano (DXF o IFC)"
ROTULO_LEER_PLANO = "Leer plano"
ROTULO_CARGAR_ALTURAS = "Cargar alturas"
ROTULO_DECLARAR_CIRCUITOS = "Declarar circuitos"
ROTULO_CONTINUAR_UNIDAD = "Continuar con esta unidad"
ROTULO_FUSIONAR = "Fusionar con el espacio del borrador"
ROTULO_DESCARTAR_PLANO = "Descartar la importación"
_CAMPOS_DE_CIRCUITO = (
    ("fase", "Conductores de fase"),
    ("neutro", "Conductores de neutro"),
    ("tierra", "Conductores de tierra"),
    ("puntos", "Puntos máximos"),
)


def _directorio_de_planos() -> Path:
    """La carpeta temporal donde se guardan los planos subidos en esta sesion."""
    actual = st.session_state.get(CLAVE_PLANO_DIRECTORIO)
    if actual is None or not Path(actual).is_dir():
        actual = tempfile.mkdtemp(prefix="silice_planos_")
        st.session_state[CLAVE_PLANO_DIRECTORIO] = actual
    return Path(actual)


def _aviso_de_plano(tipo: str, texto: str) -> None:
    st.session_state[CLAVE_PLANO_MENSAJE] = (tipo, texto)


def _leer_plano_subido() -> None:
    subida = st.session_state.get(CLAVE_PLANO_ARCHIVO)
    if subida is None:
        _aviso_de_plano(
            "error", "Elija primero un archivo de plano (DXF o IFC) y pulse Leer plano."
        )
        return
    try:
        ruta, resultado = hoja.subir_plano(subida, _directorio_de_planos())
    except hoja.HojaInvalida as error:
        _aviso_de_plano("error", str(error))
        return
    except (ValueError, OSError) as error:
        _aviso_de_plano("error", f"{error}. Renombre el archivo y vuelva a subirlo.")
        return
    st.session_state[CLAVE_PLANO] = str(ruta)
    st.session_state[CLAVE_IMPORTACION] = resultado
    st.session_state.pop(CLAVE_PLANO_FUSION, None)


def _continuar_con_unidad() -> None:
    ruta = st.session_state.get(CLAVE_PLANO)
    if ruta is None:
        _aviso_de_plano("error", "Vuelva a subir el plano: ya no está disponible.")
        return
    try:
        st.session_state[CLAVE_IMPORTACION] = hoja.leer_plano(
            ruta, unidades=st.session_state.get(CLAVE_PLANO_UNIDAD)
        )
    except hoja.HojaInvalida as error:
        _aviso_de_plano("error", str(error))


def _descartar_importacion() -> None:
    for clave in (CLAVE_IMPORTACION, CLAVE_PLANO, CLAVE_PLANO_FUSION):
        st.session_state.pop(clave, None)


def _cargar_alturas_escritas() -> None:
    resultado = st.session_state.get(CLAVE_IMPORTACION)
    if resultado is None:
        return
    textos = {
        identificador: st.session_state.get(PREFIJO_ALTURA + identificador, "")
        for identificador, _ in hoja.alturas_pendientes(resultado)
    }
    try:
        st.session_state[CLAVE_IMPORTACION] = hoja.cargar_alturas_desde_texto(resultado, textos)
    except hoja.HojaInvalida as error:
        _aviso_de_plano("error", f"{error} No se cargó ninguna altura.")


def _declarar_circuitos_escritos() -> None:
    resultado = st.session_state.get(CLAVE_IMPORTACION)
    if resultado is None:
        return
    valores = {
        c.id: tuple(
            st.session_state.get(f"{PREFIJO_CIRCUITO}{campo}_{c.id}", "")
            for campo, _ in _CAMPOS_DE_CIRCUITO
        )
        for c in hoja.circuitos_supuestos(resultado)
    }
    try:
        st.session_state[CLAVE_IMPORTACION] = hoja.declarar_circuitos_desde_texto(
            resultado,
            valores,  # type: ignore[arg-type]
        )
    except hoja.HojaInvalida as error:
        _aviso_de_plano("error", f"{error} No se declaró ningún circuito.")


def _fusionar_importacion() -> bool:
    """Fusiona la importacion vigente con el borrador; True si lo logro (hay que reejecutar)."""
    resultado = st.session_state.get(CLAVE_IMPORTACION)
    if resultado is None:
        return False
    try:
        nuevo, informe = hoja.fusionar_plano(_borrador(), resultado)
    except hoja.HojaInvalida as error:
        _aviso_de_plano("error", str(error))
        return False
    _poner_borrador(nuevo, resembrar=True)
    filas = resultado.filas
    _descartar_importacion()
    st.session_state[CLAVE_PLANO_FUSION] = (informe, hoja.resumen_de_la_fusion(resultado, informe))
    _mensaje(
        "success",
        f"Se fusionó «{resultado.archivo}» con el borrador de la hoja: {filas['esp_ambientes']} "
        f"ambientes, {filas['esp_fuentes']} fuentes y {filas['esp_puntos']} puntos. Revise las "
        "filas en las tablas de abajo; la auditoría las evalúa como a las demás. Todavía no se "
        "guardó ninguna versión: use Guardar versión cuando esté conforme.",
    )
    return True


def _pintar_conteos(resumen: Sequence[tuple[str, int]]) -> None:
    for columna, (rotulo, cantidad) in zip(st.columns(len(resumen)), resumen, strict=True):
        columna.metric(rotulo, str(cantidad))


def _pintar_filas_de_la_fusion(resumen: hoja.ResumenDeFusion) -> None:
    """Las filas que la fusion puso en el borrador, por tabla, y los origenes aparte."""
    por_tabla = " · ".join(f"{tabla} {n}" for tabla, n in resumen.filas_por_tabla)
    st.caption(f"Filas que entraron al borrador: {por_tabla or 'ninguna'}.")
    st.caption(
        f"{resumen.origenes} orígenes de medida del plano, aparte de las filas: cada fila "
        "importada cita el suyo."
    )


def _pintar_tabla_del_informe(informe: Sequence[Any]) -> None:
    st.dataframe(
        DataFrame(hoja.filas_del_informe(informe), columns=list(hoja.COLUMNAS_DEL_INFORME)),
        hide_index=True,
        width="stretch",
    )


def _pintar_unidad_pedida(resultado: Any) -> None:
    st.warning(resultado.mensaje)
    st.selectbox("Unidad del dibujo", hoja.UNIDADES_DE_PLANO, key=CLAVE_PLANO_UNIDAD)
    st.button(ROTULO_CONTINUAR_UNIDAD, on_click=_continuar_con_unidad)


def _pintar_alturas(resultado: Any) -> None:
    pendientes = hoja.alturas_pendientes(resultado)
    if not pendientes:
        return
    st.subheader("Alturas pendientes")
    st.caption(
        "El plano no trae la altura de estos ambientes. Escríbala en metros (por ejemplo 2,50); "
        "los que deje en blanco siguen pendientes."
    )
    with st.form("hoja_plano_alturas"):
        for identificador, nombre in pendientes:
            etiqueta = identificador if nombre == identificador else f"{identificador} ({nombre})"
            st.text_input(f"Altura de {etiqueta}, en metros", key=PREFIJO_ALTURA + identificador)
        st.form_submit_button(ROTULO_CARGAR_ALTURAS, on_click=_cargar_alturas_escritas)


def _pintar_circuitos(resultado: Any) -> None:
    supuestos = hoja.circuitos_supuestos(resultado)
    if not supuestos:
        return
    st.subheader("Circuitos por declarar")
    st.caption(_AYUDA_CIRCUITOS)
    with st.form("hoja_plano_circuitos"):
        for circuito in supuestos:
            actuales = (*circuito.conductores, circuito.puntos_maximos)
            for columna, (campo, rotulo), actual in zip(
                st.columns(len(_CAMPOS_DE_CIRCUITO)), _CAMPOS_DE_CIRCUITO, actuales, strict=True
            ):
                columna.text_input(
                    f"{rotulo} del circuito {circuito.id}",
                    value=str(actual),
                    key=f"{PREFIJO_CIRCUITO}{campo}_{circuito.id}",
                )
        st.form_submit_button(ROTULO_DECLARAR_CIRCUITOS, on_click=_declarar_circuitos_escritos)


def _pintar_importacion(resultado: Any) -> None:
    if resultado.estado is EstadoImportacion.RECHAZADA:
        st.error(f"No se pudo importar «{resultado.archivo}»: {resultado.mensaje}")
        st.button(ROTULO_DESCARTAR_PLANO, on_click=_descartar_importacion)
        return
    if resultado.estado is EstadoImportacion.DETENIDA:
        _pintar_unidad_pedida(resultado)
        st.button(ROTULO_DESCARTAR_PLANO, on_click=_descartar_importacion)
        return
    st.subheader(f"Informe de la importación de {resultado.archivo}")
    _pintar_conteos(hoja.resumen_de_importacion(resultado))
    _pintar_tabla_del_informe(resultado.informe)
    _pintar_alturas(resultado)
    _pintar_circuitos(resultado)
    if hoja.alturas_pendientes(resultado) or hoja.circuitos_supuestos(resultado):
        st.info(_AVISO_PENDIENTES)
    izquierda, derecha = st.columns(2)
    if izquierda.button(ROTULO_FUSIONAR, type="primary") and _fusionar_importacion():
        st.rerun()
    derecha.button(ROTULO_DESCARTAR_PLANO, on_click=_descartar_importacion)


def _importar_plano() -> None:
    """El flujo de importar un plano, al principio de la pestana Espacio y metrajes."""
    resultado = st.session_state.get(CLAVE_IMPORTACION)
    fusion = st.session_state.get(CLAVE_PLANO_FUSION)
    abierto = bool(st.session_state.pop(CLAVE_PLANO_ABIERTO, False)) or resultado is not None
    with st.expander(ROTULO_IMPORTAR, expanded=abierto or bool(fusion)):
        st.caption(_AYUDA_PLANO)
        mensaje = st.session_state.pop(CLAVE_PLANO_MENSAJE, None)
        if mensaje is not None:
            {"error": st.error, "success": st.success}.get(mensaje[0], st.info)(mensaje[1])
        st.file_uploader(
            "Plano", type=["dxf", "ifc"], key=CLAVE_PLANO_ARCHIVO, label_visibility="collapsed"
        )
        st.button(ROTULO_LEER_PLANO, on_click=_leer_plano_subido)
        if resultado is not None:
            _pintar_importacion(resultado)
        elif fusion:
            informe, resumen = fusion
            st.subheader("Informe de la última fusión")
            _pintar_conteos(resumen.por_tipo)
            _pintar_filas_de_la_fusion(resumen)
            _pintar_tabla_del_informe(informe)


# --- pestana APU ---------------------------------------------------------------------------------

_GRUPOS_APU = (
    ("materiales", "Materiales", ("descripcion", "unidad", "cantidad", "precio")),
    ("equipos", "Equipos", ("descripcion", "cantidad", "precio", "depreciacion")),
    ("mano de obra", "Mano de obra", ("descripcion", "cantidad", "sueldo", "modalidad")),
)


def _codigos_valorados(resultado: hoja.ResultadoHoja) -> list[str]:
    return list(
        dict.fromkeys(p.item.codigo_partida for p in resultado.elaboracion.presupuesto.partidas)
    )


def _cambiar_insumo(codigo: str, tipo: str, indice: int, insumo: hoja.FilaInsumo) -> None:
    borrador = _borrador()
    try:
        nueva = hoja.cambiar_insumo(borrador.composiciones[codigo], tipo, indice, insumo)
    except hoja.HojaInvalida as error:
        _mensaje("error", str(error))
        return
    _poner_borrador(
        replace(borrador, composiciones={**borrador.composiciones, codigo: nueva}), resembrar=True
    )


LIMITE_INSUMOS = 300  # el selectbox filtra en el navegador; mas alla, se acota en la base


def _formulario_de_insumo(codigo: str, apu: Any) -> None:
    abierta = _abierta()
    with st.expander("Cambiar el insumo de una linea (en la copia de esta version)"):
        if abierta is None:
            st.caption("Abra una version guardada: los insumos se eligen de su lista de precios.")
            return
        tipo = st.selectbox("Tipo de linea", hoja.TIPOS_DE_LINEA, key=_clave("tipo", codigo))
        grupo = {"material": apu.materiales, "equipo": apu.equipos, "mano_obra": apu.mano_obra}[
            tipo
        ]
        if not grupo:
            st.caption("Este APU no tiene lineas de ese tipo.")
            return
        indice = st.selectbox(
            "Linea",
            range(len(grupo)),
            format_func=lambda i: grupo[i].descripcion,
            key=_clave("linea", codigo),
        )
        acotar = ""
        with _sesion() as sesion:
            candidatos = (
                []
                if sesion is None
                else hoja.insumos_candidatos(
                    sesion,
                    abierta.proyecto,
                    abierta.codigo,
                    tipo,
                    acotar,
                    limite=LIMITE_INSUMOS + 1,
                )
            )
        if len(candidatos) > LIMITE_INSUMOS:
            candidatos = candidatos[:LIMITE_INSUMOS]
            acotar = st.text_input(
                f"Hay mas de {LIMITE_INSUMOS} insumos: escriba parte de la descripcion para acotar",
                key=_clave("buscar", codigo),
            )
            if acotar.strip():
                with _sesion() as sesion:
                    candidatos = hoja.insumos_candidatos(
                        sesion,
                        abierta.proyecto,
                        abierta.codigo,
                        tipo,
                        acotar,
                        limite=LIMITE_INSUMOS,
                    )
        if not candidatos:
            st.caption("Ningun insumo de la lista coincide: pruebe con otra palabra.")
            return
        elegido = st.selectbox(
            "Insumo (escriba para buscar por codigo o descripcion)",
            candidatos,
            index=None,
            placeholder="Elegir insumo de la lista de precios",
            format_func=lambda c: f"{c.codigo} · {c.descripcion} · {c.unidad} · {c.precio:f}",
            key=_clave("insumo", codigo),
        )
        st.button(
            "Usar este insumo",
            on_click=_cambiar_insumo,
            args=(codigo, tipo, indice, elegido),
            key=_clave("usar", codigo),
            disabled=elegido is None,
        )


CLAVE_PARTIDA_APU = "hoja_apu_partida"
CLAVE_FILTRO_APU = "hoja_apu_filtro"
ANCHOS_APU = (1.1, 3.2, 1.6)  # partidas · tabla del APU · cierre de partida


def _lista_de_partidas(resultado: hoja.ResultadoHoja, codigos: list[str]) -> str:
    """Panel izquierdo: buscador y lista de las partidas valoradas (RU-6: no hay capitulos)."""
    descripciones = {
        p.item.codigo_partida: p.apu.descripcion for p in resultado.elaboracion.presupuesto.partidas
    }
    st.markdown("**Partidas**")
    texto = st.text_input(
        "Buscar partida", key=CLAVE_FILTRO_APU, placeholder="codigo o descripcion"
    )
    visibles = hoja.filtrar_partidas(codigos, descripciones, texto)
    if not visibles:
        st.caption("Ninguna partida coincide; se muestran todas.")
        visibles = codigos
    if st.session_state.get(CLAVE_PARTIDA_APU) not in visibles:
        st.session_state.pop(CLAVE_PARTIDA_APU, None)  # foco 4: nunca un valor fuera de la lista
    return st.radio(
        "Partida",
        visibles,
        format_func=lambda c: texto_seguro(f"{c} · {descripciones.get(c, '')}"),
        key=CLAVE_PARTIDA_APU,
        label_visibility="collapsed",
    )


def _renglon(resultado: hoja.ResultadoHoja, codigo: str) -> Any:
    return next(
        (p for p in resultado.elaboracion.presupuesto.partidas if p.item.codigo_partida == codigo),
        None,
    )


def _subtotal_de_rubro(codigo: str, clave: str) -> str:
    resultado, _ = _calculo()
    renglon = _renglon(resultado, codigo)
    if renglon is None:
        return ""
    r = renglon.resultado
    valor = {"materiales": r.materiales, "equipos": r.equipos, "mano de obra": r.mano_obra}[clave]
    return _dinero(valor, resultado.elaboracion.presupuesto.moneda)


def _tabla_de_apu(codigo: str) -> None:
    """Panel central: un bloque por rubro con su subtotal, el rendimiento y el cambio de insumo.
    Cada edicion recalcula en el servidor (RU-5)."""
    borrador, siembra = _borrador(), _partida()
    actual = borrador.composiciones[codigo]
    inicial = siembra.composiciones.get(codigo, actual)
    st.caption(
        f"{texto_seguro(actual.descripcion)} · unidad {texto_seguro(actual.unidad)}. Se edita la "
        "cantidad de cada linea y el rendimiento, en la copia de esta version: el catalogo no "
        "cambia."
    )
    tablas = hoja.filas_de_apu(inicial)
    editadas = []
    huecos = []  # el subtotal de cada rubro se escribe DESPUES de aplicar la edicion
    for (_, rotulo, columnas), filas in zip(_GRUPOS_APU, tablas, strict=True):
        with st.expander(f"{rotulo} · {len(filas)} linea(s)", expanded=True):
            huecos.append(st.empty())
            if not filas:
                st.caption("Sin lineas.")
                editadas.append([])
                continue
            tabla = st.data_editor(
                DataFrame(filas, columns=list(columnas), dtype=str),
                hide_index=True,
                width="stretch",
                disabled=[c for c in columnas if c != "cantidad"],
                key=_clave("apu", codigo, rotulo),
            )
            editadas.append(tabla.to_dict("records"))
    rendimiento = st.text_input(
        "Rendimiento (unidades por dia)",
        value=hoja.texto_numero(inicial.rendimiento),
        key=_clave("rendimiento", codigo),
    )
    try:
        nueva = hoja.composicion_con_cantidades(actual, *editadas, rendimiento)
        if nueva != actual:
            _poner_borrador(
                replace(borrador, composiciones={**borrador.composiciones, codigo: nueva})
            )
    except hoja.HojaInvalida as error:
        st.error(f"{texto_seguro(str(error))}. La hoja sigue con el ultimo APU valido.")
    for (clave, rotulo, _), hueco in zip(_GRUPOS_APU, huecos, strict=True):
        hueco.caption(f"Subtotal de {rotulo.lower()}: {_subtotal_de_rubro(codigo, clave)}")
    _formulario_de_insumo(codigo, _borrador().composiciones[codigo])


def _factores() -> None:
    """Panel derecho, arriba: los factores de la version. Se leen ANTES que la lista y la tabla,
    para que los subtotales de la tabla salgan con los factores vigentes."""
    with st.container(border=True):
        st.markdown("**Factores de la version**")
        _editar_parametros([st] * len(hoja.CAMPOS_PARAMETROS), "factor")


def _cierre_de_partida(codigo: str) -> None:
    """Panel derecho, abajo: el cierre paso a paso de la partida elegida, ya con la edicion de la
    tabla aplicada. Imprevistos no existe en el modelo (RU-3)."""
    resultado, _ = _calculo()
    renglon = _renglon(resultado, codigo)
    if renglon is None:
        return
    moneda = resultado.elaboracion.presupuesto.moneda
    with st.container(border=True):
        st.markdown("**Cierre de partida**")
        st.dataframe(
            DataFrame(
                hoja.filas_de_cierre(renglon.resultado, _borrador().parametros, moneda),
                columns=["Concepto", "Monto", "Nota"],
            ),
            hide_index=True,
            width="stretch",
        )
        _calculado_de_apu(resultado, codigo)


def _pestana_apu() -> None:
    resultado, _ = _calculo()
    codigos = _codigos_valorados(resultado)
    if not codigos:
        st.info("Todavia no hay partidas valoradas: derive cantidades en Espacio y metrajes.")
        return
    izquierda, centro, derecha = st.columns(ANCHOS_APU, gap="medium")
    with derecha:
        _factores()  # primero: los factores cambian los subtotales de la tabla
    with izquierda:
        codigo = _lista_de_partidas(resultado, codigos)
    with centro:
        _tabla_de_apu(codigo)
    with derecha:
        _cierre_de_partida(codigo)  # al final: con la edicion de la tabla ya aplicada


def _calculado_de_apu(resultado: hoja.ResultadoHoja, codigo: str) -> None:
    renglon = _renglon(resultado, codigo)
    if renglon is None:
        return
    moneda = resultado.elaboracion.presupuesto.moneda
    r = renglon.resultado
    st.metric("Materiales", _dinero(r.materiales, moneda))
    st.metric("Equipos", _dinero(r.equipos, moneda))
    st.metric("Mano de obra", _dinero(r.mano_obra, moneda))
    st.metric("Precio unitario", _dinero(r.precio_unitario, moneda), border=True)
    for fila in hoja.filas_del_presupuesto(resultado):
        if fila["partida"] == codigo and fila["estado"] != hoja.TEXTO_OK:
            st.caption(texto_seguro(f"Estado de {fila['clave']}: {fila['estado']}"))


# --- pestana Presupuesto -------------------------------------------------------------------------


def _pestana_presupuesto() -> None:
    resultado, _ = _calculo()
    borrador, siembra = _borrador(), _partida()
    if not resultado.todos:
        st.info("El presupuesto no tiene renglones todavia.")
        return
    st.caption(
        "Escribir una cantidad a mano la saca del calculo del sistema: R8 la marca como "
        "advertencia y queda en el registro de la version. El precio unitario y el total se "
        "calculan."
    )
    sembradas = hoja.filas_del_presupuesto(hoja.elaborar_borrador(siembra))
    editor = DataFrame(sembradas, columns=["clave", "partida", "descripcion", "unidad", "cantidad"])
    editada = st.data_editor(
        editor,
        hide_index=True,
        width="stretch",
        disabled=["partida", "descripcion", "unidad"],
        column_config={"clave": None},
        key=_clave("presupuesto"),
    )
    try:
        escritas = hoja.cantidades_desde_filas(
            editada.to_dict("records"), hoja.items_sin_escribir(borrador)
        )
        if escritas != dict(borrador.cantidades):
            _poner_borrador(replace(borrador, cantidades=escritas))
            resultado, _ = _calculo()
    except hoja.HojaInvalida as error:
        st.error(f"{error}. La hoja sigue con las ultimas cantidades validas.")
    st.subheader("Calculado")
    filas = hoja.filas_del_presupuesto(resultado)
    st.dataframe(
        DataFrame(
            {
                "Partida": [f["partida"] for f in filas],
                "Cantidad": [f["cantidad"] for f in filas],
                "Precio unitario": [f["pu"] for f in filas],
                "Total": [f["total"] for f in filas],
                "Estado": [f["estado"] for f in filas],
            }
        ),
        hide_index=True,
        width="stretch",
    )
    presupuesto = resultado.elaboracion.presupuesto
    st.metric("Total del presupuesto", _dinero(presupuesto.total, presupuesto.moneda))


# --- pestana Plan y curva ------------------------------------------------------------------------


def _crear_plan() -> None:
    _poner_borrador(hoja.con_plan_secuencial(_borrador()), resembrar=True)


def _pestana_plan() -> None:
    resultado, _ = _calculo()
    borrador = _borrador()
    if borrador.plan is None:
        st.info("Esta version no tiene plan de trabajo, asi que no hay curva de inversion.")
        st.button("Crear plan secuencial (una partida por periodo)", on_click=_crear_plan)
        return
    codigos = _codigos_valorados(resultado)
    st.caption(
        "Reparta cada partida entre los periodos: cada fila debe sumar exactamente 1. Los montos, "
        "los acumulados y los porcentajes se calculan."
    )
    siembra = hoja.elaborar_borrador(_partida()).plan or ()
    etiquetas, filas = hoja.plan_como_filas(siembra, codigos)
    editada = st.data_editor(
        DataFrame(filas, columns=["partida", *etiquetas], dtype=str),
        hide_index=True,
        width="stretch",
        disabled=["partida"],
        key=_clave("plan"),
    )
    try:
        plan = tuple(hoja.plan_desde_filas(editada.to_dict("records"), etiquetas))
        if plan != tuple(resultado.plan or ()):
            _poner_borrador(replace(borrador, plan=plan))
            resultado, _ = _calculo()
    except hoja.HojaInvalida as error:
        st.error(f"{error}. La hoja sigue con el ultimo plan valido.")
    st.subheader("Curva de inversion")
    curva = hoja.filas_de_curva(resultado.elaboracion.presupuesto)
    st.dataframe(
        DataFrame(
            {
                "Periodo": [f["periodo"] for f in curva],
                "Monto": [f["monto"] for f in curva],
                "Acumulado": [f["acumulado"] for f in curva],
                "% acumulado": [f["porcentaje"] for f in curva],
            }
        ),
        hide_index=True,
        width="stretch",
    )
    if curva:
        st.line_chart(
            DataFrame(
                {"Acumulado": [float(f["acumulado"]) for f in curva]},
                index=[f["periodo"] for f in curva],
            )
        )


# --- pestana Punto de equilibrio -----------------------------------------------------------------


def _pestana_equilibrio() -> None:
    resultado, _ = _calculo()
    pe = resultado.equilibrio
    moneda = resultado.elaboracion.presupuesto.moneda
    st.caption("No se edita: se mueve con las cantidades, los precios, los parametros y el plan.")
    columnas = st.columns(4)
    columnas[0].metric("Ventas (contrato)", _dinero(pe.venta, moneda))
    columnas[1].metric("Costo variable", _dinero(pe.costo_variable, moneda))
    columnas[2].metric("Costo fijo", _dinero(pe.costo_fijo, moneda))
    columnas[3].metric("Utilidad", _dinero(pe.utilidad, moneda))
    if pe.punto is not None and pe.porcentaje is not None:
        a, b = st.columns(2)
        a.metric("Punto de equilibrio", _dinero(pe.punto, moneda))
        b.metric("Como % de las ventas", f"{formatear_decimal(pe.porcentaje, 2)} %")
    st.info(hoja.texto_equilibrio(pe))


# --- pestana Precios -----------------------------------------------------------------------------


def _reabrir_nueva(codigo: str) -> None:
    abierta = _abierta()
    if abierta is not None:
        _abrir(abierta.proyecto, codigo)


def _monto(valor: Decimal | None) -> str:
    return "" if valor is None else formatear_decimal(valor, DECIMALES_PRESENTACION)


def _pestana_precios(cambios: Sequence) -> None:
    abierta = _abierta()
    if abierta is None:
        st.info("Abra una version guardada para ver el origen de sus precios.")
        return
    with _sesion() as sesion:
        precios = hoja.precios_de_version(
            sesion, abierta.proyecto, abierta.codigo, fecha_evaluacion=date.today()
        )
    st.caption(
        "Lista, referencia, fecha, moneda y tasa de cada insumo, su origen y cuanto valor perdio "
        "hasta hoy (erosion). Una cotizacion (con su proveedor, numero y fecha) vale solo para "
        "este proyecto y prevalece sobre la lista global hasta que se retire."
    )
    st.dataframe(
        DataFrame(
            {
                "Insumo": [p.descripcion for p in precios],
                "Codigo": [p.codigo for p in precios],
                "Precio": [formatear_decimal(p.precio, DECIMALES_PRESENTACION) for p in precios],
                "Lista": [p.lista for p in precios],
                "Moneda": [p.moneda for p in precios],
                "Fecha del precio": [p.fecha.isoformat() for p in precios],
                "Tasa": ["" if p.tasa is None else f"{p.tasa:f}" for p in precios],
                "Fecha de la tasa": [
                    "" if p.fecha_tasa is None else p.fecha_tasa.isoformat() for p in precios
                ],
                "Referencia": [p.referencia for p in precios],
                "Cotizacion": [p.cotizacion for p in precios],
                "Moneda original": [p.moneda_original for p in precios],
                "Precio original": [_monto(p.precio_original) for p in precios],
                "Fuente de la tasa": [p.fuente_tasa for p in precios],
                "Fuente": [p.fuente for p in precios],
                "Propio/heredado": [hoja.texto_propio(p.propio) for p in precios],
                "Erosion USD": [_monto(p.erosion_usd) for p in precios],
                "Erosion Bs": [_monto(p.erosion_bs) for p in precios],
                "Erosion %": [
                    _monto(None if p.erosion_pct is None else p.erosion_pct * 100) for p in precios
                ],
                "Erosion por indice": [_monto(p.erosion_indice) for p in precios],
                "Estado": [p.estado for p in precios],
            }
        ),
        hide_index=True,
        width="stretch",
    )
    if cambios:
        st.warning(
            "Cotizar crea una version nueva desde la guardada: guarde o descarte primero los "
            f"{len(cambios)} cambios pendientes."
        )
        return
    if not precios:
        return
    with st.form("hoja_cotizar"):
        st.markdown("**Registrar una cotizacion**")
        insumo = st.selectbox(
            "Insumo", precios, format_func=lambda p: f"{p.codigo} · {p.descripcion}"
        )
        precio = st.text_input("Precio cotizado")
        a, b, c = st.columns(3)
        proveedor = a.text_input("Proveedor")
        numero = b.text_input("Numero de la cotizacion")
        fecha = c.date_input("Fecha de la cotizacion", value=date.today())
        fuente = st.text_input("Evidencia (opcional: archivo, enlace, nota)")
        responsable = ui_sesion.caja_de_responsable("Responsable")
        enviar = st.form_submit_button("Cotizar")
    if enviar:
        try:
            valor = hoja.decimal_desde_texto(precio, "precio")
            with _sesion() as sesion:
                nuevo = hoja.cotizar(
                    sesion,
                    Catalogo(sesion),
                    abierta.proyecto,
                    abierta.codigo,
                    insumo=insumo.codigo,
                    precio=valor,
                    proveedor=proveedor,
                    numero=numero,
                    fecha=fecha,
                    responsable=responsable,
                    fuente=fuente,
                )
        except (hoja.HojaInvalida, ValueError) as error:
            st.error(f"{error}. No se guardo nada.")
        except SQLAlchemyError as error:
            st.error(_error_de_base(error))
        else:
            _mensaje(
                "success", f"Se guardo la version {nuevo} con la cotizacion de {insumo.codigo}."
            )
            _reabrir_nueva(nuevo)
            st.rerun()
    cotizadas = [p for p in precios if p.cotizacion]
    if cotizadas:
        with st.form("hoja_retirar"):
            st.markdown("**Retirar una cotizacion**")
            retirada = st.selectbox(
                "Insumo cotizado",
                cotizadas,
                format_func=lambda p: f"{p.codigo} · {p.descripcion} ({p.cotizacion})",
            )
            motivo = st.text_input("Por que se retira")
            quien = ui_sesion.caja_de_responsable("Responsable ")
            retirar = st.form_submit_button("Retirar cotizacion")
        if retirar:
            try:
                with _sesion() as sesion:
                    nuevo = hoja.retirar_cotizacion(
                        sesion,
                        Catalogo(sesion),
                        abierta.proyecto,
                        abierta.codigo,
                        insumo=retirada.codigo,
                        fuente=motivo,
                        responsable=quien,
                    )
            except (hoja.HojaInvalida, ValueError) as error:
                st.error(f"{error}. No se guardo nada.")
            except SQLAlchemyError as error:
                st.error(_error_de_base(error))
            else:
                _mensaje("success", f"Se guardo la version {nuevo} sin la cotizacion.")
                _reabrir_nueva(nuevo)
                st.rerun()


# --- pestana Parametros --------------------------------------------------------------------------

_ROTULOS_PARAMETROS = {
    "fcas": "FCAS (fraccion: 6.00 = prestaciones del 600 %)",
    "bono_alimentacion": "Bono de alimentacion (por obrero y dia)",
    "administracion": "Administracion (fraccion del costo directo)",
    "utilidad": "Utilidad (fraccion, en cascada sobre la administracion)",
}


def _editar_parametros(contenedores: Sequence[Any], prefijo: str) -> None:
    """Un campo exacto por parametro de costo (RU-7); un cambio valido recalcula todos los APU."""
    borrador, siembra = _borrador(), _partida()
    textos = {}
    for campo, contenedor in zip(hoja.CAMPOS_PARAMETROS, contenedores, strict=True):
        textos[campo] = contenedor.text_input(
            _ROTULOS_PARAMETROS[campo],
            value=str(getattr(siembra.parametros, campo)),
            key=_clave(prefijo, campo),
        )
    try:
        parametros = hoja.parametros_desde_texto(textos)
        if parametros != borrador.parametros:
            _poner_borrador(replace(borrador, parametros=parametros))
    except hoja.HojaInvalida as error:
        st.error(f"{texto_seguro(str(error))}. La hoja sigue con los ultimos parametros validos.")


def _pestana_parametros() -> None:
    st.caption(
        "Los parametros de costo de esta version. Cambiarlos recalcula todos sus APU; el cambio "
        "queda en el registro con su fuente."
    )
    _editar_parametros(st.columns(len(hoja.CAMPOS_PARAMETROS)), "param")
    resultado, cambios = _calculo()
    presupuesto = resultado.elaboracion.presupuesto
    st.metric("Total del presupuesto", _dinero(presupuesto.total, presupuesto.moneda))
    _moneda(cambios)


def _moneda(cambios: Sequence) -> None:
    """RF-64: la moneda del proyecto y su cambio, que crea una version convertida (S1 §5.3)."""
    abierta = _abierta()
    if abierta is None:
        return
    with _sesion() as sesion:
        if sesion is None:
            return
        proyecto = sesion.scalars(
            select(models.Proyecto).where(models.Proyecto.nombre == abierta.proyecto)
        ).one()
        actual = moneda_del_proyecto(sesion, proyecto)
    st.markdown(f"**Moneda del proyecto:** {actual}")
    if cambios:
        st.warning(
            "Cambiar la moneda crea una version nueva desde la guardada: guarde o descarte primero "
            f"los {len(cambios)} cambios pendientes."
        )
        return
    with st.form("hoja_moneda"):
        st.markdown("**Cambiar la moneda** (crea una version convertida; la actual no cambia)")
        destino = st.selectbox("Moneda destino", [m for m in MONEDAS if m != actual])
        lado = st.selectbox("Tasa del BCV", ("venta", "compra"), help="Por defecto, venta (S1-R1).")
        fuente = st.text_input("Por que se cambia la moneda (fuente)")
        responsable = ui_sesion.caja_de_responsable("Responsable del cambio")
        enviar = st.form_submit_button("Convertir la version")
    if not enviar:
        return
    try:
        with _sesion() as sesion:
            if sesion is None:
                return
            nuevo = hoja.convertir(
                sesion,
                Catalogo(sesion),
                abierta.proyecto,
                abierta.codigo,
                destino,
                lado=lado,
                fecha=date.today(),
                fuente=fuente,
                responsable=responsable,
            )
    except hoja.HojaInvalida as error:
        st.error(str(error))
    except SQLAlchemyError as error:
        st.error(_error_de_base(error))
    else:
        _mensaje("success", f"Se guardo la version {nuevo}, convertida a {destino}.")
        _reabrir_nueva(nuevo)
        st.rerun()


# --- pestana Auditoria ---------------------------------------------------------------------------


def _pestana_auditoria() -> None:
    resultado, _ = _calculo()
    informe = resultado.elaboracion.informe
    st.caption("El informe se genera siempre, con todas las reglas, sobre el borrador vigente.")
    mostrar_informe(informe)


# --- pestana Trazabilidad ------------------------------------------------------------------------


def _restaurar(codigo: str) -> None:
    abierta = _abierta()
    if abierta is None:
        return
    try:
        with _sesion() as sesion:
            nuevo = hoja.restaurar(
                sesion,
                Catalogo(sesion),
                abierta.proyecto,
                codigo,
                fuente=st.session_state.get("hoja_restaurar_fuente", ""),
                responsable=ui_sesion.responsable_de_la_hoja(
                    st.session_state.get("hoja_restaurar_responsable", "")
                ),
            )
    except (hoja.HojaInvalida, SQLAlchemyError, PermissionError) as error:
        _mensaje("error", f"No se restauro nada: {getattr(error, 'orig', None) or error}")
        return
    _mensaje("success", f"La version {codigo} se restauro como la version {nuevo} (la vigente).")
    _reabrir_nueva(nuevo)


def _pestana_trazabilidad(cambios: Sequence) -> None:
    abierta = _abierta()
    if abierta is None:
        st.info("Abra una version guardada para ver su historial y sus registros de cambio.")
        return
    with _sesion() as sesion:
        historial = hoja.historial_de_versiones(sesion, abierta.proyecto)
        registros = hoja.registros_de_version(sesion, abierta.proyecto, abierta.codigo)
    st.subheader("Versiones del proyecto")
    st.dataframe(
        DataFrame(
            {
                "Version": [v.codigo for v in historial],
                "Fecha": [v.fecha.isoformat() for v in historial],
                "Motivo": [v.motivo or "elaborada" for v in historial],
                "Sale de": [v.origen for v in historial],
                "Cambios": [v.cambios for v in historial],
                "Vigente": ["si" if v.vigente else "" for v in historial],
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.subheader(f"Registro de cambios de la version {abierta.codigo}")
    if registros:
        st.dataframe(
            DataFrame(
                {
                    "Objeto": [r.objeto for r in registros],
                    "Clave": [r.clave for r in registros],
                    "Campo": [r.campo for r in registros],
                    "Antes": [r.valor_anterior for r in registros],
                    "Despues": [r.valor_nuevo for r in registros],
                    "Fuente": [r.fuente for r in registros],
                    "Responsable": [r.responsable for r in registros],
                    "Fecha y hora": [r.fecha_hora.isoformat(sep=" ") for r in registros],
                }
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("Esta version no nacio de una edicion: no tiene registros de cambio.")
    if cambios:
        st.warning("Guarde o descarte los cambios pendientes antes de restaurar otra version.")
        return
    with st.form("hoja_restaurar"):
        st.markdown(
            "**Restaurar una version.** Crea una version nueva, copia de la elegida; nada se borra."
        )
        elegida = st.selectbox("Version a restaurar", [v.codigo for v in historial])
        st.text_input("Fuente (por que se restaura)", key="hoja_restaurar_fuente")
        ui_sesion.caja_de_responsable("Responsable", key="hoja_restaurar_responsable")
        enviar = st.form_submit_button("Restaurar")
    if enviar:
        _restaurar(elegida)
        st.rerun()


# --- pantalla -------------------------------------------------------------------------------------


def _mostrar_mensaje() -> None:
    mensaje = st.session_state.pop(CLAVE_MENSAJE, None)
    if mensaje is None:
        return
    tipo, texto = mensaje
    {"error": st.error, "success": st.success}.get(tipo, st.info)(texto)


def _publicar_resumen() -> None:
    """Lo que la barra muestra en su linea de estado (PLAN_SILICE_UI, tarea 5)."""
    abierta = _abierta()
    if abierta is None:  # un borrador nuevo no se atribuye al proyecto abierto de la barra
        caso.publicar_resumen(None)
        return
    proyecto = abierta.proyecto
    resultado, cambios = _calculo()
    presupuesto = resultado.elaboracion.presupuesto
    if cambios:
        estado = f"borrador con {len(cambios)} cambio(s) sin guardar"
    else:
        estado = "guardada"
    caso.publicar_resumen(
        caso.ResumenDeTrabajo(
            proyecto=proyecto,
            version=abierta.codigo,
            estado=estado,
            total=_dinero(presupuesto.total, presupuesto.moneda),
        )
    )


def render() -> None:
    """La hoja del proyecto: version abierta, guardado y la pestana activa."""
    ui_sesion.exigir(Accion.EDITAR_HOJA)
    _borrador()
    accion = _atender()
    if accion == ACCION_PRECIOS:  # la herramienta Precios de la barra lleva a su pestana
        if "Precios" in PESTANAS:
            st.session_state[CLAVE_PESTANA] = "Precios"
        st.session_state.pop(CLAVE_ACCION_PENDIENTE, None)
        accion = None
    elif accion == ACCION_IMPORTAR_PLANO:  # Importar plano lleva al flujo de la pestana Espacio
        st.session_state[CLAVE_PESTANA] = PESTANAS[0]
        st.session_state[CLAVE_PLANO_ABIERTO] = True
        st.session_state.pop(CLAVE_ACCION_PENDIENTE, None)
        accion = None
    _mostrar_mensaje()
    _, cambios = _calculo()
    _selector_de_version(cambios)
    _panel_asistente()
    # El panel de guardado se pinta arriba pero se llena al final, cuando ya se leyeron los
    # editores de la pestana: asi muestra los cambios de ESTA ejecucion y no los de la anterior.
    panel = st.container()
    pestana = st.segmented_control(
        "Pestana",
        PESTANAS,
        default=PESTANAS[0],
        key=CLAVE_PESTANA,
        label_visibility="collapsed",
    )
    pestana = pestana or PESTANAS[0]  # sin seleccion (se deselecciono): la primera
    if st.session_state.get(CLAVE_ULTIMA_PESTANA, pestana) != pestana:
        _resembrar()  # los editores de la pestana nueva parten del borrador vigente
    st.session_state[CLAVE_ULTIMA_PESTANA] = pestana
    try:
        if pestana == "Espacio y metrajes":
            _pestana_espacio()
        elif pestana == "APU":
            _pestana_apu()
        elif pestana == "Presupuesto":
            _pestana_presupuesto()
        elif pestana == "Plan y curva":
            _pestana_plan()
        elif pestana == "Punto de equilibrio":
            _pestana_equilibrio()
        elif pestana == "Precios":
            _pestana_precios(_calculo()[1])
        elif pestana == "Parámetros":
            _pestana_parametros()
        elif pestana == "Auditoría":
            _pestana_auditoria()
        else:
            _pestana_trazabilidad(_calculo()[1])
    except SQLAlchemyError as error:
        st.error(_error_de_base(error))
    with panel:
        _panel_de_guardado(_calculo()[1], accion)
    _publicar_resumen()
    if accion in ("guardar_version", "exportar_excel"):
        st.session_state.pop(CLAVE_ACCION_PENDIENTE, None)
