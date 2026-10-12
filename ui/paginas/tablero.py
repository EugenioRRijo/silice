"""Pantalla «Tablero del proyecto» (PLAN_SILICE_UI, tarea 4): la vista de un vistazo.

Toma de los tableros de costos de obra lo que el sistema puede respaldar:
* tarjetas de la version vigente (total, costo directo, punto de equilibrio y auditoria);
* anillos y tarjetas del control de obra (avance fisico, SPI, CPI y EAC) cuando hay linea base y
  valuaciones;
* la curva de plan y avance, el desglose del costo por rubro, las partidas de mayor peso y el
  comparativo de versiones.

Solo lectura (RU-10): no abre la version ni escribe. Los datos salen de `ui.tablero` y los graficos
de `ui.graficos`. Texto ajeno solo por `texto_seguro`, en tablas o en tooltips (RU-9).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from seguridad.permisos import Accion
from ui import caso, graficos, tablero
from ui import sesion as ui_sesion
from ui.caso import ruta_caso
from ui.estilo import COLOR_ATENCION, COLOR_BIEN, indice, porcentaje
from ui.proyectos import listar_proyectos
from ui.texto_seguro import texto_seguro

SIN_PROYECTO = "Elija un proyecto para ver su tablero."
SIN_PROYECTOS = "Este caso todavia no tiene proyectos."
CLAVE_PROYECTO_VISTO = "tablero_proyecto_visto"  # el elegido aqui; no abre el proyecto de la barra
SIN_VERSION = "El proyecto todavia no tiene una version guardada: armela en la Hoja del proyecto."


def render() -> None:
    """El tablero del proyecto abierto, o lo que falta para tenerlo."""
    ui_sesion.exigir(Accion.LEER_PROYECTO)
    ruta = ruta_caso()
    if not ruta.exists():
        st.info(SIN_PROYECTOS)
        return
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(texto_seguro(str(error)))
        return
    proyecto = _proyecto_a_ver(ruta)
    if proyecto is None:
        return
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            datos = tablero.leer_tablero(sesion, Catalogo(sesion), proyecto)
    except (SQLAlchemyError, ValueError, LookupError) as error:
        st.error("No se pudo leer el proyecto: " + texto_seguro(str(error)))
        return
    finally:
        motor.dispose()
    if datos is None:
        st.info(SIN_VERSION)
        return
    _encabezado(datos)
    _tarjetas(tablero.tarjetas_del_presupuesto(datos))
    _control(datos)
    _curva_y_desglose(datos)
    _pareto(datos)
    _versiones(datos)


def _proyecto_a_ver(ruta: Path) -> str | None:
    """El proyecto abierto en la barra; si no hay (el rol que solo lee no tiene la barra), el que
    se elija aqui, de solo lectura y sin abrirlo. `None` si falta elegir, ya con su aviso."""
    abierto = caso.proyecto_abierto()
    if abierto is not None:
        return abierto
    nombres = listar_proyectos(ruta)
    if not nombres:
        st.info(SIN_PROYECTOS)
        return None
    elegido = st.selectbox(
        "Proyecto",
        nombres,
        index=None,
        placeholder="Elija un proyecto",
        key=CLAVE_PROYECTO_VISTO,
    )
    if elegido is None:
        st.info(SIN_PROYECTO)
    return elegido


def _encabezado(datos: tablero.DatosTablero) -> None:
    presupuesto = datos.elaboracion.presupuesto
    st.subheader(texto_seguro(datos.proyecto))
    st.caption(
        f"Version vigente {texto_seguro(datos.codigo)} del {datos.fecha.isoformat()} · moneda "
        f"{texto_seguro(presupuesto.moneda)} · {len(presupuesto.partidas)} renglon(es)"
    )


def _tarjetas(tarjetas: list[tablero.Tarjeta]) -> None:
    if not tarjetas:
        return
    for tarjeta, columna in zip(tarjetas, st.columns(len(tarjetas)), strict=True):
        columna.metric(
            tarjeta.rotulo,
            tarjeta.valor,
            help=texto_seguro(tarjeta.detalle) if tarjeta.detalle else None,
            border=True,
        )


def _color_de_indice(valor: Decimal | None) -> str:
    return COLOR_BIEN if valor is not None and valor >= 1 else COLOR_ATENCION


def _control(datos: tablero.DatosTablero) -> None:
    with st.container(border=True):
        st.markdown("**Control de obra**")
        ind = datos.control.indicadores
        if ind is None:
            st.info(texto_seguro(datos.control.motivo))
            return
        avance = tablero.avance_fisico(ind)
        anillos = st.columns(3)
        for columna, rotulo, fraccion, texto, color in (
            (anillos[0], "Avance fisico", avance, porcentaje(avance), None),
            (anillos[1], "SPI (plazo)", ind.spi, indice(ind.spi), _color_de_indice(ind.spi)),
            (anillos[2], "CPI (costo)", ind.cpi, indice(ind.cpi), _color_de_indice(ind.cpi)),
        ):
            with columna:
                st.caption(rotulo)
                opciones = {} if color is None else {"color": color}
                st.altair_chart(
                    graficos.anillo(0.0 if fraccion is None else float(fraccion), texto, **opciones)
                )
        _tarjetas(tablero.tarjetas_de_control(datos.control, datos.elaboracion.presupuesto.moneda))


def _curva_y_desglose(datos: tablero.DatosTablero) -> None:
    presupuesto = datos.elaboracion.presupuesto
    izquierda, derecha = st.columns((3, 2))
    with izquierda, st.container(border=True):
        con_control = datos.control.indicadores is not None
        st.markdown("**Valor ganado (PV, EV, AC)**" if con_control else "**Plan acumulado**")
        filas = tablero.filas_de_curvas(presupuesto, datos.control)
        if filas:
            st.altair_chart(graficos.curvas(filas), width="stretch")
        else:
            st.caption("La version no tiene plan de trabajo: declarelo en la Hoja del proyecto.")
    with derecha, st.container(border=True):
        st.markdown("**Desglose del costo**")
        filas = tablero.filas_de_desglose(presupuesto)
        if not filas:
            st.caption("El total del presupuesto es cero.")
            return
        st.altair_chart(graficos.desglose(filas), width="stretch")
        st.dataframe(
            DataFrame(filas, columns=["Rubro", "Monto", "Peso"]), hide_index=True, width="stretch"
        )


def _pareto(datos: tablero.DatosTablero) -> None:
    filas = tablero.filas_pareto(datos.elaboracion.presupuesto)
    if not filas:
        return
    with st.container(border=True):
        st.markdown("**Partidas de mayor peso** (son las que conviene cotizar primero)")
        grafico, tabla = st.columns((2, 3))
        grafico.altair_chart(graficos.pareto(filas), width="stretch")
        tabla.dataframe(
            DataFrame(filas, columns=["Partida", "Descripcion", "Total", "Peso", "Acumulado"]),
            hide_index=True,
            width="stretch",
        )


def _versiones(datos: tablero.DatosTablero) -> None:
    if not datos.versiones:
        return
    with st.container(border=True):
        st.markdown("**Comparativo de versiones**")
        grafico, tabla = st.columns((2, 3))
        grafico.altair_chart(graficos.versiones(datos.versiones), width="stretch")
        tabla.dataframe(
            DataFrame(
                datos.versiones,
                columns=["Version", "Fecha", "Motivo", "Costo directo", "Total", "Vigente"],
            ),
            hide_index=True,
            width="stretch",
        )
