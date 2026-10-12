"""El caso abierto de la sesion y el recorrido activo (UI, RF-38 a RF-40; Silice 0.6.0, RV-5).

El archivo de la base se fija una vez por sesion y todas las pantallas operan sobre el: ninguna,
salvo el Inicio, vuelve a pedir el caso. Desde la 0.6.0 el Inicio lo elige de la lista de la carpeta
de casos (`abrir_caso`), y todo caso se abre con `operacion.base_datos.preparar_base`
(spec S5 §6.6).

Tres invariantes (spec de UI, §3.2):

1. **Claves propias de `st.session_state`, nunca de widget.** Streamlit descarta las entradas de los
   widgets que no se vuelven a montar: `CLAVE_CASO` y `CLAVE_RECORRIDO` no son la `key` de ningun
   widget.
2. **Respaldo declarado.** Se puede entrar por URL a cualquier pantalla sin pasar por el Inicio. Sin
   caso fijado, manda la variable de entorno `SILICE_CASO` (el guion CP-07 la usa; la lee
   `ui.entorno.leer_variable`, con su alias anterior hasta la 0.6.0; en el producto la fija el
   lanzador) y, si no esta, el caso por defecto de la carpeta de datos (`<datos>/casos/silice.db`,
   `operacion.config`). `SILICE_CASO` es configuracion de quien arranca, no entrada del usuario: no
   pasa por la lista. `ruta_caso()` lee `RUTA_BASE_POR_DEFECTO` **al
   llamarse**: las pruebas la parchan en el objeto modulo de `sys.modules`.
3. **El motor de SQLAlchemy no va a la sesion.** Cada pantalla lo crea y lo cierra con
   `motor.dispose()`: en Windows no se puede borrar un archivo con un motor abierto.

`estado_caso` no crea el archivo ni emite DDL: lee con una conexion de solo lectura (RV-5). La
siembra desde la interfaz nunca construye el flag de reinicio de `scripts/seed_demo.py`, que
borra la base entera.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion
from operacion.base_datos import (
    MENSAJE_MAS_NUEVA,
    Destino,
    ErrorDeBase,
    RutaDeCasoRechazada,
    leer_estado,
    motor_solo_lectura,
    preparar_base,
    resolver_caso,
    revision_head,
    revisiones_conocidas,
)
from operacion.config import ruta_caso_por_defecto
from seguridad.permisos import Accion
from ui import sesion as ui_sesion
from ui.entorno import VARIABLE_CASO, leer_variable

#: Sin caso fijado ni `SILICE_CASO`: `None` es el caso por defecto de la carpeta de datos. Las
#: pruebas lo desvian con una ruta de texto.
RUTA_BASE_POR_DEFECTO = None
VARIABLE_RUTA_CASO = VARIABLE_CASO  # nombre que ya importan las pruebas (RF-38; A1)
CLAVE_CASO = "silice_caso_ruta"
CLAVE_RECORRIDO = "silice_recorrido_activo"
CLAVE_PROYECTO = "silice_proyecto_abierto"
CLAVE_ACCION = "silice_accion_pedida"
#: Acciones que la barra superior le pide a la hoja del proyecto (`pedir_accion`).
ACCION_PRECIOS = "precios"
ACCION_IMPORTAR_PLANO = "importar_plano"
ACCION_GUARDAR_VERSION = "guardar_version"
ACCION_EXPORTAR_EXCEL = "exportar_excel"
SIN_PERMISO_DE_CAMBIO = (
    "Su cuenta no puede cambiar de caso: pidaselo a quien arma o al administrador."
)


def resolver_ruta(guardada: str | None, entorno: Mapping[str, str], por_defecto: str) -> Path:
    """La ruta del caso: la fijada en la sesion; si no, la del entorno; si no, la por defecto."""
    if guardada:
        return Path(guardada)
    del_entorno = (leer_variable(entorno, VARIABLE_RUTA_CASO) or "").strip()
    return Path(del_entorno or por_defecto)


def ruta_caso() -> Path:
    """La ruta del caso abierto en esta sesion."""
    por_defecto = RUTA_BASE_POR_DEFECTO or str(ruta_caso_por_defecto())
    return resolver_ruta(st.session_state.get(CLAVE_CASO), os.environ, por_defecto)


def fijar_caso(ruta: Path | str) -> None:
    """Fija el caso abierto para toda la sesion. `ValueError` si la ruta queda vacia."""
    texto = str(ruta).strip()
    if not texto:
        raise ValueError("Elija un caso de la lista: no puede quedar vacio.")
    st.session_state[CLAVE_CASO] = texto


def puede_cambiar_de_caso() -> bool:
    """«Cambiar de caso»: solo *arma* y administrador (maestro §4.3, S3 §5.1). Con el acceso
    apagado (transicion, RP8-4) la sesion de desarrollo tiene todos los roles."""
    return ui_sesion.puede(Accion.CAMBIAR_CASO)


def abrir_caso(nombre: str, carpeta: Path | None = None) -> Path:
    """Abre un caso de la lista (RV-5): valida el nombre dentro de la carpeta de casos, lo prepara
    con `preparar_base` (lo migra con respaldo si hace falta) y lo fija para la sesion.
    `PermissionError` sin permiso de cambiar de caso; `ErrorDeBase` con el mensaje si no se
    puede."""
    if not puede_cambiar_de_caso():
        raise PermissionError(SIN_PERMISO_DE_CAMBIO)
    ruta = resolver_caso(nombre, carpeta)
    if not ruta.exists():
        raise RutaDeCasoRechazada(f"El caso {ruta.name} ya no esta en la carpeta de casos.")
    preparar_base(ruta)
    fijar_caso(ruta)
    return ruta


def recorrido_activo() -> str | None:
    """El nombre del recorrido elegido en el Inicio, o `None` si no se eligio ninguno."""
    return st.session_state.get(CLAVE_RECORRIDO)


def fijar_recorrido(nombre: str | None) -> None:
    """Fija (o, con `None`, suelta) el recorrido activo de la sesion."""
    st.session_state[CLAVE_RECORRIDO] = nombre


def proyecto_abierto() -> str | None:
    """El nombre del proyecto abierto en esta sesion (barra superior, RF-63), o `None`."""
    return st.session_state.get(CLAVE_PROYECTO)


def fijar_proyecto(nombre: str | None) -> None:
    """Fija (o, con `None`, suelta) el proyecto abierto de la sesion."""
    st.session_state[CLAVE_PROYECTO] = nombre


def pedir_accion(accion: str) -> None:
    """Deja una accion de la barra superior para la pantalla de destino (la hoja del proyecto)."""
    st.session_state[CLAVE_ACCION] = accion


def tomar_accion() -> str | None:
    """La accion pedida por la barra, que se consume: la segunda llamada devuelve `None`."""
    return st.session_state.pop(CLAVE_ACCION, None)


@dataclass(frozen=True, slots=True)
class EstadoCaso:
    """Lo que el marco muestra del caso abierto (RF-39)."""

    ruta: Path
    existe: bool
    partidas: int = 0
    insumos: int = 0
    lista_vigente: str | None = None
    error: str | None = None
    por_migrar: bool = False

    @property
    def vacio(self) -> bool:
        """Legible y sin partidas: incluye el archivo que todavia no existe (RF-40)."""
        return self.error is None and self.partidas == 0


def estado_caso(ruta: Path) -> EstadoCaso:
    """El estado del caso en `ruta`, sin crear el archivo y sin DDL (RV-5)."""
    if not ruta.exists():
        return EstadoCaso(ruta=ruta, existe=False)
    try:
        base = leer_estado(ruta)
    except ErrorDeBase as error:
        return EstadoCaso(ruta=ruta, existe=True, error=str(error))
    if base.revision is not None and base.revision not in revisiones_conocidas(Destino.CASO):
        texto = MENSAJE_MAS_NUEVA.format(nombre=ruta.name, revision=base.revision)
        return EstadoCaso(ruta=ruta, existe=True, error=texto)
    if base.sin_datos:
        return EstadoCaso(ruta=ruta, existe=True)
    motor = motor_solo_lectura(ruta)
    try:
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            try:
                lista: str | None = catalogo.lista_vigente().nombre
            except CatalogoIncompleto:
                lista = None
            return EstadoCaso(
                ruta=ruta,
                existe=True,
                partidas=len(catalogo.partidas()),
                insumos=len(catalogo.insumos()),
                lista_vigente=lista,
                por_migrar=base.revision != revision_head(Destino.CASO),
            )
    except SQLAlchemyError as error:
        # `orig` (el mensaje de SQLite, sin la sentencia SQL) solo existe en `DBAPIError`.
        return EstadoCaso(ruta=ruta, existe=True, error=str(getattr(error, "orig", None) or error))
    finally:
        motor.dispose()


def resumen_caso(estado: EstadoCaso) -> str:
    """Una linea con el estado del caso, para la barra lateral."""
    if estado.error is not None:
        return f"No se pudo leer: {estado.error}"
    if not estado.existe:
        return "El archivo no existe todavia."
    texto = (
        f"{estado.partidas} partidas · {estado.insumos} insumos · "
        f"lista vigente: {estado.lista_vigente or 'ninguna'}"
    )
    return texto + (" · se actualizara al abrirlo" if estado.por_migrar else "")


def argv_siembra(ruta: Path) -> list[str]:
    """Argumentos de `scripts.seed_demo.main` para sembrar el caso: nunca el flag de reinicio."""
    return ["--db", str(ruta)]


# --- resumen de trabajo para la barra (PLAN_SILICE_UI, tarea 5) --------------------------------

CLAVE_RESUMEN = "caso_resumen_de_trabajo"  # clave propia, no de widget


@dataclass(frozen=True, slots=True)
class ResumenDeTrabajo:
    """Lo que la hoja publica para la linea de estado de la barra: textos ya formateados.

    `proyecto` y `version` son texto ajeno: quien los pinte los escapa (RU-9).
    """

    proyecto: str
    version: str | None
    estado: str
    total: str


def publicar_resumen(resumen: ResumenDeTrabajo | None) -> None:
    """La hoja deja su resumen (o lo retira con `None`)."""
    if resumen is None:
        st.session_state.pop(CLAVE_RESUMEN, None)
    else:
        st.session_state[CLAVE_RESUMEN] = resumen


def resumen_publicado() -> ResumenDeTrabajo | None:
    resumen = st.session_state.get(CLAVE_RESUMEN)
    return resumen if isinstance(resumen, ResumenDeTrabajo) else None
