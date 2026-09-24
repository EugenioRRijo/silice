"""El caso abierto de la sesion y el recorrido activo (sprint de UI, RF-38 a RF-40).

El archivo de la base se fija una vez por sesion y todas las pantallas operan sobre el: ninguna,
salvo el Inicio, vuelve a pedir la ruta. Antes de este modulo cada pantalla tenia su caja de texto
y su propia copia de `RUTA_BASE_POR_DEFECTO` (ocho copias); esta es la unica.

Tres invariantes (spec de UI, §3.2):

1. **Claves propias de `st.session_state`, nunca de widget.** Streamlit descarta las entradas de los
   widgets que no se vuelven a montar: si el caso abierto viviera en la clave de la caja de texto
   del Inicio, se olvidaria al navegar a otra pantalla. Por eso `CLAVE_CASO` y `CLAVE_RECORRIDO` no
   son la `key` de ningun widget.
2. **Respaldo declarado.** Se puede entrar por URL a cualquier pantalla sin pasar por el Inicio. Sin
   caso fijado, manda la variable de entorno `ARENIA_CASO` (el guion CP-07 la usa) y, si no esta,
   `RUTA_BASE_POR_DEFECTO`. `ruta_caso()` lee esa constante **al llamarse**, no al definirse: las
   pruebas la parchan en el objeto modulo de `sys.modules`.
3. **El motor de SQLAlchemy no va a la sesion.** Cada pantalla lo crea y lo cierra con
   `motor.dispose()`: en Windows no se puede borrar un archivo con un motor abierto.

`estado_caso` comprueba si el archivo existe **antes** de crear el esquema: `crear_esquema` sobre
una ruta con una errata crearia una base vacia en silencio. La siembra desde la interfaz nunca
construye el flag de reinicio de `scripts/seed_demo.py`, que borra la base entera.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion, crear_esquema, crear_motor

RUTA_BASE_POR_DEFECTO = "data/apu.db"
VARIABLE_RUTA_CASO = "ARENIA_CASO"
CLAVE_CASO = "arenia_caso_ruta"
CLAVE_RECORRIDO = "arenia_recorrido_activo"


def resolver_ruta(guardada: str | None, entorno: Mapping[str, str], por_defecto: str) -> Path:
    """La ruta del caso: la fijada en la sesion; si no, la del entorno; si no, la por defecto."""
    if guardada:
        return Path(guardada)
    del_entorno = entorno.get(VARIABLE_RUTA_CASO, "").strip()
    return Path(del_entorno or por_defecto)


def ruta_caso() -> Path:
    """La ruta del caso abierto en esta sesion."""
    return resolver_ruta(st.session_state.get(CLAVE_CASO), os.environ, RUTA_BASE_POR_DEFECTO)


def fijar_caso(ruta: Path | str) -> None:
    """Fija el caso abierto para toda la sesion. `ValueError` si la ruta queda vacia."""
    texto = str(ruta).strip()
    if not texto:
        raise ValueError("Escriba la ruta del archivo del caso: no puede quedar vacia.")
    st.session_state[CLAVE_CASO] = texto


def recorrido_activo() -> str | None:
    """El nombre del recorrido elegido en el Inicio, o `None` si no se eligio ninguno."""
    return st.session_state.get(CLAVE_RECORRIDO)


def fijar_recorrido(nombre: str | None) -> None:
    """Fija (o, con `None`, suelta) el recorrido activo de la sesion."""
    st.session_state[CLAVE_RECORRIDO] = nombre


@dataclass(frozen=True, slots=True)
class EstadoCaso:
    """Lo que el marco muestra del caso abierto (RF-39)."""

    ruta: Path
    existe: bool
    partidas: int = 0
    insumos: int = 0
    lista_vigente: str | None = None
    error: str | None = None

    @property
    def vacio(self) -> bool:
        """Legible y sin partidas: incluye el archivo que todavia no existe (RF-40)."""
        return self.error is None and self.partidas == 0


def estado_caso(ruta: Path) -> EstadoCaso:
    """El estado del caso en `ruta`, sin crear el archivo si no existe."""
    if not ruta.exists():
        return EstadoCaso(ruta=ruta, existe=False)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
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
    return (
        f"{estado.partidas} partidas · {estado.insumos} insumos · "
        f"lista vigente: {estado.lista_vigente or 'ninguna'}"
    )


def argv_siembra(ruta: Path) -> list[str]:
    """Argumentos de `scripts.seed_demo.main` para sembrar el caso: nunca el flag de reinicio."""
    return ["--db", str(ruta)]
