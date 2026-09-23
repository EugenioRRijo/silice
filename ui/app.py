"""Interfaz Streamlit multipagina del sistema APU (Sesion F.1, Tarea 4).

Enrutador `st.navigation` sobre las nueve pantallas de `ui/paginas/`: actualizacion masiva de
precios (UC-02), catalogo, componer o editar una partida a mano (UC-10 / UC-11, Sesion P2.2),
elaborar presupuesto (UC-01), los escenarios de sensibilidad (UC-08), historico de cambios de
precio, las partidas similares (UC-03, Sesion I2), el simulador de listas de prueba y el visor 3D
del modelo IFC (Tarea 7).

Cada pagina expone `def render() -> None` sin efectos al importarse (los suyos, y los de este
modulo, los comprueba `tests/unit/test_ui_importable.py` con `importlib.import_module`): este
modulo importa esas funciones para poder registrarlas, pero **no** construye ningun objeto de
Streamlit (`st.Page`, `st.navigation`) a nivel de modulo, solo dentro de `main()`, que unicamente
corre cuando la app se ejecuta de verdad (`if __name__ == "__main__"`). `st.set_page_config` se
llama una unica vez aqui, antes de `st.navigation` (regla de Streamlit para apps multipagina): las
paginas ya no la llaman por su cuenta, a diferencia del `ui/app.py` de una sola pantalla que existia
antes de esta sesion.

Las paginas no comparten constantes de presentacion con este enrutador (evita un import circular
`ui.app` <-> `ui.paginas.*`): cada una define su propio valor por defecto trivial de UI (por ejemplo
`RUTA_BASE_POR_DEFECTO = "data/apu.db"`, ya repetido igual en `scripts/simular_lista.py`), mientras
que la unica definicion de presentacion que sí importan todas es la compartida de verdad:
`core.verification.informe.DECIMALES_PRESENTACION` y `core.verification.texto.formatear_decimal`
(principio DRY, CLAUDE.md §2).

Modo entrega (Sesion P5.1, prototipo AREN.IA). Por defecto se ven las nueve pantallas. Con la
variable de entorno `ARENIA_MODO_ENTREGA=1` (exactamente `"1"`; cualquier otro valor o su ausencia
lo dejan apagado) se ven solo las cinco que AREN.IA necesita —actualizacion de precios, catalogo,
componer, elaborar e historico— y se ocultan las cuatro de investigacion de la tesis —escenarios,
similares, simulador y visor 3D—. El filtro es la funcion pura `paginas_visibles` sobre la tupla
`PAGINAS` de `DefinicionPagina`, que no es de Streamlit: los `st.Page` se siguen construyendo solo
dentro de `main()` (lo prueba `tests/unit/test_ui_app.py` sin Streamlit).

Uso (con `python -m`: `streamlit run` a secas pone en `sys.path` la carpeta `ui/` y no la raiz
del repositorio, y entonces `import ui` falla; `python -m` agrega el directorio actual)::

    uv sync --extra ui --extra api --extra civil
    uv run python -m streamlit run ui/app.py

Modo entrega, en bash::

    ARENIA_MODO_ENTREGA=1 uv run python -m streamlit run ui/app.py

y en PowerShell::

    $env:ARENIA_MODO_ENTREGA = "1"; uv run python -m streamlit run ui/app.py
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import streamlit as st

from ui.paginas import (
    actualizacion,
    catalogo,
    componer,
    elaborar,
    escenarios,
    historico,
    similares,
    simulador,
    visor,
)

TITULO_APP = "Sistema APU"
VARIABLE_MODO_ENTREGA = "ARENIA_MODO_ENTREGA"
VALOR_MODO_ENTREGA = "1"


@dataclass(frozen=True, slots=True)
class DefinicionPagina:
    """Una pantalla del enrutador, sin Streamlit: de ella nace un `st.Page` dentro de `main()`."""

    render: Callable[[], None]
    titulo: str
    investigacion: bool  # True: pantalla de la tesis que AREN.IA no necesita

    @property
    def ruta_url(self) -> str:
        """Ruta URL de la pagina: el nombre de su modulo (`ui.paginas.componer` -> `componer`).

        Sin ella Streamlit la infiere del nombre de la funcion, y como las nueve se llaman `render`
        `st.navigation` rechaza la aplicacion entera por rutas repetidas.
        """
        return self.render.__module__.rsplit(".", 1)[-1]


PAGINAS: tuple[DefinicionPagina, ...] = (
    DefinicionPagina(actualizacion.render, "Actualizacion de precios (UC-02)", False),
    DefinicionPagina(catalogo.render, "Catalogo", False),
    DefinicionPagina(componer.render, "Componer partida (UC-10 / UC-11)", False),
    DefinicionPagina(elaborar.render, "Elaborar presupuesto (UC-01)", False),
    DefinicionPagina(escenarios.render, "Escenarios (UC-08)", True),
    DefinicionPagina(historico.render, "Historico de precios", False),
    DefinicionPagina(similares.render, "Partidas similares (UC-03)", True),
    DefinicionPagina(simulador.render, "Simulador de listas", True),
    DefinicionPagina(visor.render, "Visor 3D", True),
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
    """Las pantallas que se muestran: las nueve, o sin las de investigacion en modo entrega."""
    if not modo_entrega:
        return PAGINAS
    return tuple(pagina for pagina in PAGINAS if not pagina.investigacion)


def main() -> None:
    """Punto de entrada de `streamlit run ui/app.py`: configura la pagina y arranca el enrutador."""
    st.set_page_config(page_title=TITULO_APP, layout="wide")
    paginas = [
        st.Page(
            pagina.render, title=pagina.titulo, url_path=pagina.ruta_url, default=indice == 0
        )
        for indice, pagina in enumerate(paginas_visibles(modo_entrega_activo()))
    ]
    st.navigation(paginas).run()


if __name__ == "__main__":
    main()
