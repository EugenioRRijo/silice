"""Interfaz Streamlit multipagina del sistema APU: enrutador y marco comun (sprint de UI).

Dos papeles. **Enrutador:** `st.navigation` sobre las pantallas de `ui/paginas/`, agrupadas en
secciones —Trabajo, Revision (UC-23, S3) e Investigacion— en el orden del trabajo real, con el
Inicio como pagina por defecto (RF-36, RF-42). **Marco comun:** alrededor de cada pantalla,
`marco()` pinta el titulo y el caso de uso que implementa, el caso abierto y su estado en la barra
lateral (RF-39), en que paso del recorrido activo esta el usuario y, al pie, el boton «Siguiente»
(RF-41). Streamlit describe asi el
archivo de entrada de `st.navigation`: «acts like a router or frame of common elements around each
of your pages».

El paso siguiente lo pinta el marco, no las paginas: `st.switch_page` necesita el objeto `Page` de
destino, que solo existe dentro de `main()`, y una pagina que importara `ui.app` para obtenerlo
crearia un ciclo. El grafo queda `ui.app -> ui.paginas.* -> ui.caso -> core.catalog`, aciclico.

Debajo de las paginas hay una capa sin pantalla (INV-043, fase C3): `ui.elaboracion` orquesta
«cantidades -> elaborar -> exportar» y guarda composiciones sin confirmar (sin Streamlit);
`ui.composicion` convierte tablas en el contrato y calcula el desglose (puro, no escribe en la
base); y `ui.resultado` es el fragmento de Streamlit que pinta un presupuesto elaborado. El grafo
sigue aciclico: `ui.paginas.* -> ui.elaboracion -> ui.composicion -> core.costing`, y
`ui.paginas.* -> ui.resultado`. Lo que cada una no importa lo fija
`tests/unit/test_arquitectura.py::test_ui_respeta_sus_importaciones_prohibidas`.

Cada pagina expone `def render() -> None` sin efectos al importarse. Este modulo tampoco construye
objetos de Streamlit al importarse: `st.Page` y `st.navigation` solo dentro de `main()`, que corre
cuando la app se ejecuta de verdad (`if __name__ == "__main__"`); lo comprueba
`tests/unit/test_ui_importable.py`. `st.set_page_config` se llama una unica vez aqui.

La pagina por defecto tiene `url_path == ""` en Streamlit (no la ruta que se le declaro): por eso
`ruta_actual()` traduce la ruta vacia al Inicio antes de buscar su definicion.

Barra superior (SF4, RF-60). Con `position="top"` el menu va arriba (Streamlit >= 1.62) y,
debajo, `ui.barra.pintar_barra` pinta la barra de herramientas: Proyecto, Importar plano (si SF5
la entrega), Precios, Auditar, Guardar version, Exportar Excel y Recorrido guiado. Solo este
modulo importa `ui.barra`; la barra lateral queda para el caso abierto y el paso del recorrido.

Modo entrega (Sesion P5.1 del prototipo). Con `SILICE_MODO_ENTREGA=1` (exactamente `"1"`) el
menu **omite** la seccion Investigacion —escenarios, similares, simulador y visor 3D—; la seccion
Trabajo queda completa (RF-43). Se omite en vez de plegarse: la barra de herramientas y el resto
del marco no cambian. Las variables se leen con `ui.entorno.leer_variable`.

Uso (con `python -m`: `streamlit run` a secas pone en `sys.path` la carpeta `ui/` y no la raiz
del repositorio, y entonces `import ui` falla; `python -m` agrega el directorio actual)::

    uv sync --extra ui --extra api --extra civil
    uv run python -m streamlit run ui/app.py

Otro caso que `data/apu.db`, y modo entrega, en bash::

    SILICE_CASO=data/otro.db SILICE_MODO_ENTREGA=1 uv run python -m streamlit run ui/app.py

y en PowerShell::

    $env:SILICE_CASO = "data/otro.db"; $env:SILICE_MODO_ENTREGA = "1"
    uv run python -m streamlit run ui/app.py
"""

from __future__ import annotations

import os
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass

import streamlit as st

from seguridad.permisos import Accion, Rol, permitido
from seguridad.sesiones import SesionActiva
from ui import acceso, barra
from ui import sesion as ui_sesion
from ui.caso import estado_caso, recorrido_activo, resumen_caso, ruta_caso
from ui.entorno import VARIABLE_MODO_ENTREGA, leer_variable
from ui.paginas import (
    acerca,
    actualizacion,
    catalogo,
    componer,
    control,
    elaborar,
    escenarios,
    historico,
    hoja,
    indices,
    inicio,
    instalacion,
    precios_empresa,
    reajuste,
    revisar,
    similares,
    simulador,
    tablero,
    visor,
)
from ui.recorridos import RUTA_INICIO, Recorrido, paso_siguiente, recorrido_por_nombre

TITULO_APP = "Sílice"
VALOR_MODO_ENTREGA = "1"
SECCION_TRABAJO = "Trabajo"
SECCION_REVISION = "Revision"
SECCION_INVESTIGACION = "Investigacion"
ROTULO_SIGUIENTE = "Siguiente: {}"
CLAVE_BOTON_SIGUIENTE = "marco_siguiente"
POSICION_NAVEGACION = "top"  # RF-60: la navegacion va arriba (Streamlit >= 1.62)


@dataclass(frozen=True, slots=True)
class DefinicionPagina:
    """Una pantalla del enrutador, sin Streamlit: de ella nace un `st.Page` dentro de `main()`."""

    render: Callable[[], None]
    titulo: str
    seccion: str
    caso_uso: str | None = None  # codigo de la ERS; el marco lo pinta como subtitulo (RF-42)
    accion: Accion | None = None  # la de la matriz de roles (S3 5.1); None = toda cuenta la ve

    @property
    def ruta_url(self) -> str:
        """Ruta URL de la pagina: el nombre de su modulo (`ui.paginas.componer` -> `componer`).

        Sin ella Streamlit la infiere del nombre de la funcion, y como todas se llaman `render`
        `st.navigation` rechaza la aplicacion entera por rutas repetidas.
        """
        return self.render.__module__.rsplit(".", 1)[-1]


PAGINA_INICIO = DefinicionPagina(inicio.render, "Inicio", SECCION_TRABAJO)

_EDITA = Accion.EDITAR_HOJA
_LEE = Accion.LEER_PROYECTO
_PRECIOS = Accion.ADMINISTRAR_PRECIOS
_REAJUSTA = Accion.CONVERTIR_Y_REAJUSTAR
_CONTROLA = Accion.CONTROL_DE_OBRA

PAGINAS: tuple[DefinicionPagina, ...] = (
    PAGINA_INICIO,
    DefinicionPagina(tablero.render, "Tablero del proyecto", SECCION_TRABAJO, accion=_LEE),
    DefinicionPagina(
        catalogo.render, "Catalogo de partidas e insumos", SECCION_TRABAJO, accion=_LEE
    ),
    DefinicionPagina(
        componer.render, "Componer una partida", SECCION_TRABAJO, "UC-10 / UC-11", _EDITA
    ),
    DefinicionPagina(elaborar.render, "Elaborar un presupuesto", SECCION_TRABAJO, "UC-01", _EDITA),
    DefinicionPagina(hoja.render, "Hoja del proyecto", SECCION_TRABAJO, accion=_EDITA),
    DefinicionPagina(actualizacion.render, "Actualizar precios", SECCION_TRABAJO, "UC-02", _EDITA),
    DefinicionPagina(
        historico.render, "Historico de cambios de precio", SECCION_TRABAJO, accion=_LEE
    ),
    DefinicionPagina(
        precios_empresa.render, "Precios de la empresa", SECCION_TRABAJO, "UC-17", _PRECIOS
    ),
    DefinicionPagina(indices.render, "Indices del BCV", SECCION_TRABAJO, "UC-17", _PRECIOS),
    DefinicionPagina(reajuste.render, "Reajuste de precios", SECCION_TRABAJO, "UC-18", _REAJUSTA),
    DefinicionPagina(control.render, "Control de obra", SECCION_TRABAJO, "UC-19 / UC-20",
                     _CONTROLA),
    DefinicionPagina(acerca.render, "Acerca de Sílice", SECCION_TRABAJO),
    # S5-2: mientras S3-3 no traiga la página Administración, la pestaña vive como pantalla propia.
    DefinicionPagina(instalacion.render, "Instalación", SECCION_TRABAJO,
                     accion=Accion.ADMINISTRAR_RED_Y_API),
    DefinicionPagina(revisar.render, "Revisar un paquete", SECCION_REVISION, "UC-23",
                     Accion.REVISAR_PAQUETE),
    DefinicionPagina(
        escenarios.render, "Escenarios de sensibilidad", SECCION_INVESTIGACION, "UC-08", _EDITA
    ),
    DefinicionPagina(
        similares.render, "Partidas similares", SECCION_INVESTIGACION, "UC-03", _EDITA
    ),
    DefinicionPagina(simulador.render, "Simulador de listas", SECCION_INVESTIGACION, accion=_EDITA),
    DefinicionPagina(visor.render, "Visor 3D del modelo", SECCION_INVESTIGACION, accion=_EDITA),
)


def modo_entrega_activo(entorno: Mapping[str, str] | None = None) -> bool:
    """Indica si el modo entrega esta encendido: la variable vale exactamente `"1"`.

    `entorno` permite probar la funcion sin tocar `os.environ`; si es `None` se lee el entorno
    del proceso.
    """
    if entorno is None:
        entorno = os.environ
    return leer_variable(entorno, VARIABLE_MODO_ENTREGA) == VALOR_MODO_ENTREGA


def paginas_visibles(
    modo_entrega: bool, roles: Collection[Rol] | None = None
) -> tuple[DefinicionPagina, ...]:
    """Las pantallas que se muestran: las que los `roles` permiten (todas si `roles` es `None`)
    y, en modo entrega, sin la seccion Investigacion. La navegacion no es el control: cada
    `render()` vuelve a exigir su accion (S3 5.1)."""
    return tuple(
        pagina
        for pagina in PAGINAS
        if not (modo_entrega and pagina.seccion == SECCION_INVESTIGACION)
        and (roles is None or pagina.accion is None or permitido(roles, pagina.accion))
    )


def secciones_visibles(
    modo_entrega: bool, roles: Collection[Rol] | None = None
) -> dict[str, tuple[DefinicionPagina, ...]]:
    """Las pantallas visibles agrupadas por seccion; el `dict` conserva el orden de `PAGINAS`."""
    secciones: dict[str, tuple[DefinicionPagina, ...]] = {}
    for pagina in paginas_visibles(modo_entrega, roles):
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
    definicion: DefinicionPagina,
    pintar: Callable[[], None],
    ir_a: Callable[[str], None],
    sesion: SesionActiva | None = None,
) -> None:
    """Los elementos comunes alrededor de una pantalla.

    `pintar` pinta la pantalla (`Page.run` en la aplicacion, `render` en las pruebas); `ir_a` lleva
    a la pantalla de una ruta (`st.switch_page` en la aplicacion, un registrador en las pruebas).
    `sesion` es quien entro (S3): sin ella, la de desarrollo con todos los roles. La barra de
    herramientas escribe, asi que solo la ve quien puede editar la hoja; el recorrido guiado
    omite los pasos de pantallas que el rol no ve (RF-37).
    """
    roles = ui_sesion.DESARROLLO.roles if sesion is None else sesion.roles
    puede_editar = permitido(roles, Accion.EDITAR_HOJA)
    estado = None
    if puede_editar:
        barra.pintar_barra(definicion.ruta_url, ir_a)
        estado = st.empty()  # se llena al final: ve el resumen que la pantalla publica ahora
    st.title(definicion.titulo)
    if definicion.caso_uso is not None:
        st.caption(f"Caso de uso {definicion.caso_uso}")
    _pintar_caso_abierto()
    recorrido = recorrido_por_nombre(recorrido_activo())
    if recorrido is not None:
        visibles = {pagina.ruta_url for pagina in paginas_visibles(False, roles)}
        recorrido = recorrido.visible_en(visibles)
    _pintar_posicion(recorrido, definicion.ruta_url)
    pintar()
    if estado is not None:
        with estado.container():
            barra.pintar_estado()
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
    sesion = acceso.exigir_sesion()  # sin sesion valida pinta el acceso y detiene el guion
    acceso.pintar_sesion(sesion)
    modo_entrega = modo_entrega_activo()
    paginas = {
        definicion.ruta_url: st.Page(
            definicion.render,
            title=definicion.titulo,
            url_path=definicion.ruta_url,
            default=definicion is PAGINA_INICIO,
        )
        for definicion in paginas_visibles(modo_entrega, sesion.roles)
    }
    secciones = {
        seccion: [paginas[definicion.ruta_url] for definicion in definiciones]
        for seccion, definiciones in secciones_visibles(modo_entrega, sesion.roles).items()
    }
    actual = st.navigation(secciones, position=POSICION_NAVEGACION)
    marco(
        pagina_por_ruta(ruta_actual(actual.url_path)),
        actual.run,
        lambda ruta: st.switch_page(paginas[ruta]),
        sesion,
    )


if __name__ == "__main__":
    main()
