"""Pagina de UC-08: escenarios de sensibilidad sobre un presupuesto guardado (RF-30, RF-31).

Cierra el hallazgo 1 de la bitacora del cierre de UC-08 (la ERS §3.1 promete la interfaz con los
ocho casos de uso). Solo presentacion: toda la logica vive en `core.budget.escenarios`
(`generar_escenario`, `comparar_escenarios`, `comparar_por_partida`); esta capa abre la sesion,
lee el presupuesto base con sus parametros congelados, arma los supuestos que el proyectista
declara (parametros nuevos y/o precios de ensayo) y presenta la tabla de RF-31 con su detalle
por partida. Nada se persiste: el base queda intacto (RF-30) y los escenarios viven en
`st.session_state` mientras dura la comparacion.

El base se lee con `cargar_elaboracion`, que trae sus items pendientes (UC-01 3a, INV-080):
`generar_escenario` solo recalcula los renglones valorados, asi que la pagina los declara con un
aviso para que ningun escenario se lea como completo (INV-083).

La descarga CSV entrega la tabla con los `Decimal` exactos (`str`), no los dos decimales de la
pantalla: es la exportacion de RF-31, y el redondeo es solo de presentacion (NORMAS.md §2.3).
Los dos decimales visibles son los de `core.verification.informe.DECIMALES_PRESENTACION`, la
unica definicion de presentacion del sistema.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from core import models
from core.budget import (
    Escenario,
    cargar_elaboracion,
    comparar_escenarios,
    comparar_por_partida,
    generar_escenario,
    hallazgos_externos,
)
from core.budget.instantanea import composiciones_de_presupuesto
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.contracts import ItemComputo, ParametrosCosto
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from ui.caso import ruta_caso
from ui.composicion import decimal_desde_texto

_CAMPOS_PARAMETROS = ("fcas", "bono_alimentacion", "administracion", "utilidad")
_ESTADO_ESCENARIOS = "uc08_escenarios"
_ESTADO_BASE = "uc08_base"


def render() -> None:
    """Selector de presupuesto, formulario de supuestos y tabla comparativa de RF-31."""
    st.caption(
        "Recalcula un presupuesto guardado variando parametros de costo o precios de insumos. "
        "El presupuesto base no se altera y ningun escenario se guarda."
    )

    ruta = ruta_caso()
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            _pagina(sesion, ruta)
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # Mismo criterio que las demas paginas: un dato invalido o una base inaccesible es un
        # mensaje, no una traza cruda.
        st.error(str(error))
    finally:
        motor.dispose()


def _pagina(sesion, ruta: Path) -> None:
    modelos = list(sesion.scalars(select(models.Presupuesto).order_by(models.Presupuesto.codigo)))
    if not modelos:
        st.info("No hay presupuestos guardados todavia: elabore uno primero (UC-01).")
        return

    etiquetas = {f"{modelo.proyecto.nombre} / {modelo.codigo}": modelo for modelo in modelos}
    eleccion = st.selectbox("Presupuesto base", list(etiquetas))
    modelo = etiquetas[eleccion]

    # Los escenarios acumulados pertenecen a un base concreto: cambiar de presupuesto (o de
    # archivo) los descarta, porque compararlos contra otro base no significa nada.
    clave_base = (ruta.as_posix(), modelo.proyecto.nombre, modelo.codigo)
    if st.session_state.get(_ESTADO_BASE) != clave_base:
        st.session_state[_ESTADO_BASE] = clave_base
        st.session_state[_ESTADO_ESCENARIOS] = []

    catalogo = Catalogo(sesion)
    # `cargar_elaboracion`, no `cargar_presupuesto`: el contrato `Presupuesto` no lleva los items
    # pendientes del base, y los escenarios no los ven (INV-083).
    elaboracion = cargar_elaboracion(sesion, modelo.proyecto.nombre, modelo.codigo, catalogo)
    base = elaboracion.presupuesto
    _declarar_pendientes(elaboracion.pendientes)
    parametros_base = ParametrosCosto(
        **{nombre: getattr(modelo, nombre) for nombre in _CAMPOS_PARAMETROS}
    )

    _formulario(sesion, modelo, base, elaboracion.informe, catalogo, parametros_base)
    _resultados(base)


def _declarar_pendientes(pendientes: Sequence[ItemComputo]) -> None:
    """UC-01 3a en UC-08: el base tiene items sin partida que ningun escenario recalcula."""
    if not pendientes:
        return
    lineas = "\n".join(
        f"- {item.origen_id}: {item.codigo_partida} ({item.descripcion})" for item in pendientes
    )
    st.warning(
        "El presupuesto base tiene items pendientes, sin partida en el catalogo:\n\n"
        f"{lineas}\n\n"
        "Pendientes del base: los escenarios solo recalculan los renglones valorados; estos "
        "items no suman al total del base ni de ningun escenario (UC-01 3a)."
    )


def _formulario(
    sesion, modelo, base, informe_base, catalogo: Catalogo, parametros_base: ParametrosCosto
) -> None:
    with st.form("nuevo_escenario"):
        nombre = st.text_input(
            "Nombre del escenario",
            value=f"escenario {len(st.session_state[_ESTADO_ESCENARIOS]) + 1}",
        )
        st.caption(
            "Parametros de costo del escenario (por defecto, los del presupuesto base). "
            "Fracciones: 6.00 = prestaciones del 600 %."
        )
        columnas = st.columns(len(_CAMPOS_PARAMETROS))
        textos = {
            nombre_campo: columna.text_input(
                nombre_campo, value=str(getattr(parametros_base, nombre_campo))
            )
            for nombre_campo, columna in zip(_CAMPOS_PARAMETROS, columnas, strict=True)
        }
        st.caption(
            "Precios de ensayo (opcional): descripcion exacta del insumo y precio nuevo. "
            "Lo no mencionado conserva su precio vigente."
        )
        precios_tabla = st.data_editor(
            DataFrame(columns=["insumo", "precio_nuevo"]).astype(str),
            num_rows="dynamic",
            hide_index=True,
        )
        generar = st.form_submit_button("Generar escenario")

    if not generar:
        return

    parametros = replace(
        parametros_base,
        **{campo: decimal_desde_texto(texto, campo) for campo, texto in textos.items()},
    )
    precios = {
        str(fila.insumo).strip(): decimal_desde_texto(
            str(fila.precio_nuevo), f"precio de {fila.insumo}"
        )
        for fila in precios_tabla.itertuples(index=False)
        if str(fila.insumo).strip()
    }
    # SF3: las composiciones son las de la instantanea de la version (la hoja las edita ahi), no
    # las del catalogo en vivo; los hallazgos de R8 a R10 se vuelven a declarar (SF-E1).
    composiciones = composiciones_de_presupuesto(
        sesion, modelo.proyecto.nombre, modelo.codigo, catalogo
    )
    escenario = generar_escenario(
        nombre,
        base,
        composiciones,
        parametros,
        precios=precios,
        externos=hallazgos_externos(informe_base),
    )
    st.session_state[_ESTADO_ESCENARIOS].append(escenario)


def _resultados(base) -> None:
    escenarios: list[Escenario] = st.session_state[_ESTADO_ESCENARIOS]
    if not escenarios:
        st.info("Defina un escenario para compararlo contra el presupuesto base.")
        return

    tabla = comparar_escenarios(base, escenarios)
    st.subheader("Comparacion contra el base (RF-31)")
    st.dataframe(_presentar(tabla), hide_index=True)
    st.download_button(
        "Descargar tabla (CSV, valores exactos)",
        tabla.to_csv(index=False),
        file_name=f"escenarios_{base.codigo}.csv",
        mime="text/csv",
    )
    if st.button("Descartar escenarios"):
        st.session_state[_ESTADO_ESCENARIOS] = []
        st.rerun()

    for escenario in escenarios:
        with st.expander(f"Detalle por partida: {escenario.nombre}"):
            comparativo = comparar_por_partida(base, escenario)
            st.dataframe(_presentar(comparativo.tabla), hide_index=True)
            st.caption(
                f"Hallazgos de la auditoria del escenario: {len(escenario.informe.hallazgos)} "
                f"(el informe se genera siempre). Insumos variados: {escenario.insumos_variados}."
            )


def _presentar(tabla: DataFrame) -> DataFrame:
    """Copia de presentacion: `Decimal` a texto con los dos decimales del sistema."""

    def _celda(valor: object) -> object:
        if isinstance(valor, Decimal):
            return formatear_decimal(valor, DECIMALES_PRESENTACION)
        return valor

    presentada = tabla.copy()
    for columna in presentada.columns:
        presentada[columna] = [_celda(valor) for valor in presentada[columna]]
    return presentada
