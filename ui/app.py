"""Interfaz Streamlit multipagina del sistema APU: enrutador y marco comun (sprint de UI).

Dos papeles. **Enrutador:** `st.navigation` sobre las diez pantallas de `ui/paginas/`, agrupadas en
dos secciones —Trabajo e Investigacion— en el orden del trabajo real, con el Inicio como pagina por
defecto (RF-36, RF-42). **Marco comun:** alrededor de cada pantalla, `marco()` pinta el titulo y el
caso de uso que implementa, el caso abierto y su estado en la barra lateral (RF-39), en que paso del
recorrido activo esta el usuario y, al pie, el boton «Siguiente» (RF-41). Streamlit describe asi el
archivo de entrada de `st.navigation`: «acts like a router or frame of common elements around each
of your pages».

El paso siguiente lo pinta el marco, no las paginas: `st.switch_page` necesita el objeto `Page` de
destino, que solo existe dentro de `main()`, y una pagina que importara `ui.app` para obtenerlo
crearia un ciclo. El grafo queda `ui.app -> ui.paginas.* -> ui.caso -> core.catalog`, aciclico.

Cada pagina expone `def render() -> None` sin efectos al importarse. Este modulo tampoco construye
objetos de Streamlit al importarse: `st.Page` y `st.navigation` solo dentro de `main()`, que corre
cuando la app se ejecuta de verdad (`if __name__ == "__main__"`); lo comprueba
`tests/unit/test_ui_importable.py`. `st.set_page_config` se llama una unica vez aqui.

La pagina por defecto tiene `url_path == ""` en Streamlit (no la ruta que se le declaro): por eso
`ruta_actual()` traduce la ruta vacia al Inicio antes de buscar su definicion.

Modo entrega (Sesion P5.1, prototipo AREN.IA). Con `ARENIA_MODO_ENTREGA=1` (exactamente `"1"`) el
menu **omite** la seccion Investigacion —escenarios, similares, simulador y visor 3D—; la seccion
Trabajo queda completa (RF-43). Las secciones no se pueden colapsar en la barra lateral de
Streamlit (solo con `position="top"`), por eso se omite en vez de plegarse.

Uso (con `python -m`: `streamlit run` a secas pone en `sys.path` la carpeta `ui/` y no la raiz
del repositorio, y entonces `import ui` falla; `python -m` agrega el directorio actual)::

    uv sync --extra ui --extra api --extra civil
    uv run python -m streamlit run ui/app.py

Otro caso que `data/apu.db`, y modo entrega, en bash::

    ARENIA_CASO=data/otro.db ARENIA_MODO_ENTREGA=1 uv run python -m streamlit run ui/app.py

y en PowerShell::

    $env:ARENIA_CASO = "data/otro.db"; $env:ARENIA_MODO_ENTREGA = "1"
    uv run python -m streamlit run ui/app.py
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import streamlit as st

from ui.caso import estado_caso, recorrido_activo, resumen_caso, ruta_caso
from ui.paginas import (
    actualizacion,
    catalogo,
    componer,
    elaborar,
    escenarios,
    historico,
    inicio,
    similares,
    simulador,
    visor,
)
from ui.recorridos import RUTA_INICIO, Recorrido, paso_siguiente, recorrido_por_nombre

TITULO_APP = "Sistema APU"
VARIABLE_MODO_ENTREGA = "ARENIA_MODO_ENTREGA"
VALOR_MODO_ENTREGA = "1"
SECCION_TRABAJO = "Trabajo"
SECCION_INVESTIGACION = "Investigacion"
ROTULO_SIGUIENTE = "Siguiente: {}"
CLAVE_BOTON_SIGUIENTE = "marco_siguiente"


@dataclass(frozen=True, slots=True)
class DefinicionPagina:
    """Una pantalla del enrutador, sin Streamlit: de ella nace un `st.Page` dentro de `main()`."""

    render: Callable[[], None]
    titulo: str
    seccion: str
    caso_uso: str | None = None  # codigo de la ERS; el marco lo pinta como subtitulo (RF-42)

    @property
    def ruta_url(self) -> str:
        """Ruta URL de la pagina: el nombre de su modulo (`ui.paginas.componer` -> `componer`).

        Sin ella Streamlit la infiere del nombre de la funcion, y como todas se llaman `render`
        `st.navigation` rechaza la aplicacion entera por rutas repetidas.
        """
        return self.render.__module__.rsplit(".", 1)[-1]


PAGINA_INICIO = DefinicionPagina(inicio.render, "Inicio", SECCION_TRABAJO)

PAGINAS: tuple[DefinicionPagina, ...] = (
    PAGINA_INICIO,
    DefinicionPagina(catalogo.render, "Catalogo de partidas e insumos", SECCION_TRABAJO),
    DefinicionPagina(componer.render, "Componer una partida", SECCION_TRABAJO, "UC-10 / UC-11"),
    DefinicionPagina(elaborar.render, "Elaborar un presupuesto", SECCION_TRABAJO, "UC-01"),
    DefinicionPagina(actualizacion.render, "Actualizar precios", SECCION_TRABAJO, "UC-02"),
    DefinicionPagina(historico.render, "Historico de cambios de precio", SECCION_TRABAJO),
    DefinicionPagina(
        escenarios.render, "Escenarios de sensibilidad", SECCION_INVESTIGACION, "UC-08"
    ),
    DefinicionPagina(similares.render, "Partidas similares", SECCION_INVESTIGACION, "UC-03"),
    DefinicionPagina(simulador.render, "Simulador de listas", SECCION_INVESTIGACION),
    DefinicionPagina(visor.render, "Visor 3D del modelo", SECCION_INVESTIGACION),
)


def modo_entrega_activo(entorno: Mapping[str, str] | None = None) -> bool:
    """Indica si el modo entrega esta encendido: la variable vale exactamente `"1"`.

    `entorno` permite probar la funcion sin tocar `os.environ`; si es `None` se lee el entorno
    del proceso.
    """
    if entorno is None:
        entorno = os.environ
    return entorno.get(VARIABLE_MODO_ENTREGA) == VALOR_MODO_ENTREGA


def paginas_visibles(modo_entrega: bool) -> tuple[DefinicionPagina, ...]:
    """Las pantallas que se muestran: las diez, o sin la seccion Investigacion en modo entrega."""
    if not modo_entrega:
        return PAGINAS
    return tuple(pagina for pagina in PAGINAS if pagina.seccion != SECCION_INVESTIGACION)


def secciones_visibles(modo_entrega: bool) -> dict[str, tuple[DefinicionPagina, ...]]:
    """Las pantallas visibles agrupadas por seccion; el `dict` conserva el orden de `PAGINAS`."""
    secciones: dict[str, tuple[DefinicionPagina, ...]] = {}
    for pagina in paginas_visibles(modo_entrega):
        secciones[pagina.seccion] = (*secciones.get(pagina.seccion, ()), pagina)
    return secciones


def pagina_por_ruta(ruta: str) -> DefinicionPagina:
    """La definicion de la pantalla con esa ruta URL. `KeyError` si no hay ninguna."""
    for pagina in PAGINAS:
        if pagina.ruta_url == ruta:
            return pagina
    raise KeyError(f"no hay ninguna pantalla con la ruta {ruta!r}")


def ruta_actual(url_path: str) -> str:
    """La ruta de la pantalla actual.

    Streamlit da `""` a la pagina por defecto, que es el Inicio.
    """
    return url_path or RUTA_INICIO


def marco(
    definicion: DefinicionPagina, pintar: Callable[[], None], ir_a: Callable[[str], None]
) -> None:
    """Los elementos comunes alrededor de una pantalla.

    `pintar` pinta la pantalla (`Page.run` en la aplicacion, `render` en las pruebas); `ir_a` lleva
    a la pantalla de una ruta (`st.switch_page` en la aplicacion, un registrador en las pruebas).
    """
    st.title(definicion.titulo)
    if definicion.caso_uso is not None:
        st.caption(f"Caso de uso {definicion.caso_uso}")
    _pintar_caso_abierto()
    recorrido = recorrido_por_nombre(recorrido_activo())
    _pintar_posicion(recorrido, definicion.ruta_url)
    pintar()
    paso = paso_siguiente(recorrido, definicion.ruta_url)
    if paso is not None and st.button(
        ROTULO_SIGUIENTE.format(paso.titulo), type="primary", key=CLAVE_BOTON_SIGUIENTE
    ):
        ir_a(paso.pagina)


def _pintar_caso_abierto() -> None:
    estado = estado_caso(ruta_caso())
    with st.sidebar:
        st.subheader("Caso abierto")
        st.caption(str(estado.ruta))
        st.caption(resumen_caso(estado))


def _pintar_posicion(recorrido: Recorrido | None, ruta: str) -> None:
    if recorrido is None:
        return
    with st.sidebar:
        st.subheader(f"Recorrido: {recorrido.nombre}")
        if ruta == RUTA_INICIO:
            st.caption("Pulse «Siguiente» al pie de la pagina para empezar.")
            return
        posicion = recorrido.posicion(ruta)
        if posicion is None:
            st.caption("Esta pantalla no es parte del recorrido; vuelva al Inicio para retomarlo.")
            return
        paso = recorrido.pasos[posicion - 1]
        st.caption(f"Paso {posicion} de {len(recorrido.pasos)}: {paso.titulo}")
        st.markdown(paso.que_hacer)
        st.caption(f"Sabra que termino cuando: {paso.senal_de_exito}")


def main() -> None:
    """Punto de entrada de `streamlit run ui/app.py`: configura, enruta y enmarca la pantalla."""
    st.set_page_config(page_title=TITULO_APP, layout="wide")
    modo_entrega = modo_entrega_activo()
    paginas = {
        definicion.ruta_url: st.Page(
            definicion.render,
            title=definicion.titulo,
            url_path=definicion.ruta_url,
            default=definicion is PAGINA_INICIO,
        )
        for definicion in paginas_visibles(modo_entrega)
    }
    secciones = {
        seccion: [paginas[definicion.ruta_url] for definicion in definiciones]
        for seccion, definiciones in secciones_visibles(modo_entrega).items()
    }
    actual = st.navigation(secciones)
    marco(
        pagina_por_ruta(ruta_actual(actual.url_path)),
        actual.run,
        lambda ruta: st.switch_page(paginas[ruta]),
    )


if __name__ == "__main__":
    main()
