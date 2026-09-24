"""Pagina de partidas similares (UC-03, Sesion I2): reutilizar desgloses del catalogo.

El proyectista escribe la descripcion de una partida en texto libre y el sistema propone las tres
partidas mas parecidas del catalogo con su puntaje de similitud del coseno
(`ml.normalization.NormalizadorPartidas`, RF-15); al desplegar una propuesta se precargan su
desglose (`core.catalog.Catalogo.composicion`) y su rendimiento, conservando el codigo de la
partida de origen y el puntaje que la propuso (RF-16, la parte de precarga: la persistencia de una
partida nueva con esa referencia espera al flujo de creacion de partidas, que ningun UC
implementado ofrece todavia -- documentado en la bitacora de la sesion).

La capa de composicion es esta pagina: `ml/` no conoce la base de datos (CLAUDE.md §2), asi que
aqui se consulta `core.catalog` y se le pasan pares (codigo, descripcion) planos.

`ml.normalization` (sentence-transformers) se carga de forma perezosa en `_cargar_normalizacion()`,
no al importar este modulo: mismo criterio que `ui/paginas/visor.py` con el extra `civil` -- un
import incondicional romperia toda la UI en un entorno sin el extra `ml`. Sin pruebas de UI
(decision del proyecto): la logica se prueba en `tests/unit/test_normalizacion.py` y esta pagina
solo se comprueba importable.
"""

from __future__ import annotations

from types import ModuleType
from typing import TYPE_CHECKING

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion, crear_esquema, crear_motor
from core.contracts.apu import ComposicionAPU
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from ui.caso import ruta_caso

if TYPE_CHECKING:
    from ml.normalization import PartidaSimilar

_MENSAJE_SIN_EXTRA_ML = (
    "Las propuestas de partidas similares necesitan el extra 'ml' (sentence-transformers): "
    "instala con 'uv sync --extra ml' y vuelve a intentar."
)


def _cargar_normalizacion() -> ModuleType | None:
    """El modulo `ml.normalization`, o `None` si el extra `ml` no esta instalado."""
    try:
        import ml.normalization
    except ImportError:
        return None
    return ml.normalization


def render() -> None:
    """Descripcion en texto libre -> tres propuestas con puntaje, desglose y rendimiento."""
    st.caption(
        "Escribe la descripcion de la partida: el sistema propone las mas parecidas del catalogo "
        "para reutilizar su desglose y su rendimiento (similitud semantica, sin entrenamiento)."
    )

    normalizacion = _cargar_normalizacion()
    if normalizacion is None:
        st.error(_MENSAJE_SIN_EXTRA_ML)
        return

    ruta = ruta_caso()
    descripcion = st.text_input("Descripcion de la partida", value="")
    if not descripcion.strip():
        st.info("Escribe una descripcion para buscar partidas similares.")
        return

    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            partidas = {p.codigo: p.descripcion for p in catalogo.partidas()}
            try:
                normalizador = normalizacion.NormalizadorPartidas(partidas)
            except OSError as error:
                # Precondicion del UC-03: el modelo debe estar disponible localmente; la primera
                # construccion lo descarga y sin red eso falla con un mensaje, no una traza.
                st.error(f"El modelo de similitud no esta disponible: {error}")
                return
            propuestas = normalizador.similares(descripcion)
            _mostrar_propuestas(catalogo, propuestas)
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # Mismo criterio que el resto de las paginas: mensaje, no traza cruda.
        st.error(str(error))
    finally:
        motor.dispose()


def _mostrar_propuestas(catalogo: Catalogo, propuestas: list[PartidaSimilar]) -> None:
    if not propuestas:
        # Flujos 2a y 2b del UC-03: nada sobre el umbral (o catalogo vacio) -> desde cero.
        st.info(
            "Ninguna partida del catalogo supera el umbral de similitud: "
            "la partida se crearia desde cero."
        )
        return

    st.subheader(f"{len(propuestas)} propuesta(s), de mayor a menor similitud")
    for propuesta in propuestas:
        titulo = f"{propuesta.puntaje:.2f} - {propuesta.codigo} - {propuesta.descripcion}"
        with st.expander(titulo, expanded=False):
            st.caption(
                f"Partida de origen: {propuesta.codigo} | "
                f"puntaje de similitud: {propuesta.puntaje:.4f}"
            )
            try:
                composicion = catalogo.composicion(propuesta.codigo)
            except CatalogoIncompleto as error:
                # Flujo 4a del UC-03: desglose con insumos sin precio en la lista vigente -> se
                # senala y la partida quedaria incompleta hasta que se coticen.
                st.warning(f"Desglose incompleto en la lista vigente: {error}")
                continue
            _mostrar_composicion(composicion)


def _mostrar_composicion(composicion: ComposicionAPU) -> None:
    st.markdown(
        f"**Unidad:** {composicion.unidad} | "
        f"**Rendimiento:** {formatear_decimal(composicion.rendimiento, DECIMALES_PRESENTACION)} "
        f"{composicion.unidad}/dia"
    )
    if composicion.materiales:
        st.markdown("**Materiales**")
        st.dataframe(
            DataFrame(
                [
                    {
                        "descripcion": linea.descripcion,
                        "unidad": linea.unidad,
                        "cantidad": formatear_decimal(linea.cantidad, DECIMALES_PRESENTACION),
                        "precio": formatear_decimal(linea.precio, DECIMALES_PRESENTACION),
                    }
                    for linea in composicion.materiales
                ]
            ),
            hide_index=True,
        )
    if composicion.equipos:
        st.markdown("**Equipos**")
        st.dataframe(
            DataFrame(
                [
                    {
                        "descripcion": linea.descripcion,
                        "cantidad": formatear_decimal(linea.cantidad, DECIMALES_PRESENTACION),
                        "precio": formatear_decimal(linea.precio, DECIMALES_PRESENTACION),
                        "depreciacion": str(linea.depreciacion),
                    }
                    for linea in composicion.equipos
                ]
            ),
            hide_index=True,
        )
    if composicion.mano_obra:
        st.markdown("**Mano de obra**")
        st.dataframe(
            DataFrame(
                [
                    {
                        "descripcion": linea.descripcion,
                        "cantidad": formatear_decimal(linea.cantidad, DECIMALES_PRESENTACION),
                        "sueldo": formatear_decimal(linea.sueldo, DECIMALES_PRESENTACION),
                    }
                    for linea in composicion.mano_obra
                ]
            ),
            hide_index=True,
        )
