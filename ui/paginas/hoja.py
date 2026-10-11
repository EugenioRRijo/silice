"""Pantalla «Hoja del proyecto»: la pestana Espacio y metrajes (SF 1.8, spec §9.1 y §9.2).

El usuario describe el espacio —origenes de medida, ambientes, fuentes, puntos y los vertices de
los recorridos que declara— en tablas editables (`st.data_editor`); debajo ve las cantidades que la
hoja deriva de ese espacio y el informe de auditoria del presupuesto que resulta (principio 7 de
NORMAS.md §2: se genera siempre). Toda la logica vive en `ui.hoja` (sin Streamlit); aqui solo se
pinta.

Tres decisiones de pantalla (spec §5.3 y §9.2):

* **El borrador vive en `st.session_state[CLAVE_BORRADOR]`**, una clave que no es de ningun widget:
  Streamlit descarta el estado de los widgets que no se vuelven a montar. Las tablas del editor se
  siembran **una sola vez** desde el borrador (`CLAVE_PARTIDA`); si se le devolviera al editor la
  tabla recalculada en cada edicion, se reiniciaria.
* **La columna Estado va fuera del editor**: un `st.dataframe` aparte, junto a cada tabla, con el
  peor hallazgo de cada fila (`ui.hoja.estado_de_filas`). Se pinta despues de elaborar, en el hueco
  que se reservo al lado del editor.
* **La pestana activa es un `st.segmented_control`** con su propia clave. Hoy solo existe la
  primera; las demas (APU, Presupuesto, Plan y curva...) llegan con SF2 a SF4.

Una fila invalida no pierde el trabajo: `ui.hoja.HojaInvalida` se muestra como error y la hoja sigue
con el ultimo borrador valido. Esta pantalla **no guarda**: guardar una version es SF3. Sin efectos
al importarse: todo vive dentro de `render()`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from adapters.espacio import (
    Espacio,
    Especialidad,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoOrigen,
    TipoPunto,
)
from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion, crear_motor
from core.contracts import ComposicionAPU, ItemComputo
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from ui import hoja
from ui.caso import ruta_caso

PESTANAS = ("Espacio y metrajes",)
CLAVE_BORRADOR = "hoja_borrador"  # el Espacio vigente: no es la clave de ningun widget
CLAVE_PARTIDA = "hoja_partida"  # el Espacio con que se sembraron las tablas del editor
CLAVE_PESTANA = "hoja_pestana"  # clave del st.segmented_control
PREFIJO_EDITOR = "hoja_editor_"
TABLAS_CON_ESTADO = {"ambientes": "esp_ambientes", "fuentes": "esp_fuentes", "puntos": "esp_puntos"}

_AYUDA_ESPACIO = (
    "Describa el espacio en metros (eje z hacia arriba desde el piso terminado). Cada fila cita un "
    "origen de medida; un punto de agua fria sin recorrido declarado usa el recorrido propuesto. "
    "Los vertices se escriben como `x,y,z; x,y,z` y la longitud de cada tramo se calcula."
)


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
    return {
        columna: st.column_config.SelectboxColumn(columna, options=opciones)
        for columna, opciones in listas.items()
    }


def _composiciones(
    items: Sequence[ItemComputo], fecha: date
) -> tuple[dict[str, ComposicionAPU], str | None]:
    """Las composiciones del catalogo del caso abierto para los items derivados, y un aviso.

    Sin archivo, sin items o con un catalogo ilegible no se escribe nada: el informe declara
    entonces cada item como pendiente (UC-01 3a).
    """
    ruta = ruta_caso()
    if not items or not ruta.exists():
        return {}, None
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return hoja.composiciones_del_catalogo(Catalogo(sesion), items, fecha), None
    except (SQLAlchemyError, CatalogoIncompleto) as error:
        return {}, f"No se pudo leer el catalogo del caso: {getattr(error, 'orig', None) or error}"
    finally:
        motor.dispose()


def _pintar_estado(
    hueco, tabla: str, filas: Sequence[dict[str, str]], estado: dict[str, hoja.EstadoFila]
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


def _cantidades(items: Sequence[ItemComputo]) -> None:
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
    st.caption(_AYUDA_ESPACIO)
    borrador = st.session_state.get(CLAVE_BORRADOR)
    if not isinstance(borrador, Espacio):
        borrador = Espacio()
        st.session_state[CLAVE_BORRADOR] = borrador
    partida = st.session_state.get(CLAVE_PARTIDA)
    if not isinstance(partida, Espacio):
        partida = borrador
        st.session_state[CLAVE_PARTIDA] = partida
    base = hoja.filas_desde_espacio(partida)

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
                key=f"{PREFIJO_EDITOR}{tabla}",
            )
        editadas[tabla] = tabla_editada.to_dict("records")

    try:
        borrador = hoja.espacio_desde_filas(editadas, base=partida)
        st.session_state[CLAVE_BORRADOR] = borrador
    except hoja.HojaInvalida as error:
        st.error(f"{error}. La hoja sigue con el ultimo borrador valido.")
        borrador = st.session_state[CLAVE_BORRADOR]

    fecha = date.today()
    items = hoja.items_del_borrador(borrador, hoja.TODAS)
    composiciones, aviso = _composiciones(items, fecha)
    if aviso is not None:
        st.warning(aviso)
    resultado = hoja.elaborar_hoja(
        borrador, composiciones, codigo="HOJA", fecha=fecha, especialidad=hoja.TODAS
    )

    filas_borrador = hoja.filas_desde_espacio(borrador)
    for tabla, hueco in huecos.items():
        _pintar_estado(hueco, tabla, filas_borrador[tabla], resultado.estado)

    _cantidades(resultado.items)
    presupuesto = resultado.elaboracion.presupuesto
    st.metric(
        "Total del presupuesto",
        f"{formatear_decimal(presupuesto.total, DECIMALES_PRESENTACION)} {presupuesto.moneda}",
    )
    if resultado.elaboracion.pendientes:
        st.warning(
            f"{len(resultado.elaboracion.pendientes)} partida(s) derivada(s) no tienen "
            "composicion en el catalogo del caso: quedan pendientes y no suman al total."
        )
    st.subheader("Informe de auditoria")
    st.markdown(resultado.elaboracion.informe.a_markdown())


def render() -> None:
    """La hoja del proyecto: la pestana activa y su contenido."""
    pestana = st.segmented_control(
        "Pestana",
        PESTANAS,
        default=PESTANAS[0],
        key=CLAVE_PESTANA,
        label_visibility="collapsed",
    )
    if pestana in (None, PESTANAS[0]):  # sin seleccion (se deselecciono): la primera
        _pestana_espacio()
