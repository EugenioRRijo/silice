"""Sesion de base de datos por peticion. Lo unico de la API que sabe de configuracion.

El caso se abre por `operacion.base_datos.preparar_base` (RV-5, spec S5 §5.2): el de `APU_BASE` (que
en el producto fija el lanzador) o, sin ella, el caso por defecto de la carpeta de datos. Una base
que no se puede preparar (mas nueva, ilegible, bloqueada, no adoptable) responde 503 con el mensaje,
sin crear tablas.

Caso por sesion web (RM-2, sesion 2b): una peticion con la cookie de una ficha que eligio caso
(`api.caso_web`) trabaja en ese caso; con la clave de API (`X-Silice-Clave`), o sin eleccion, en el
del proceso. El motor de SQLAlchemy se guarda **uno por ruta de caso** (`obtener_motor`): la base se
prepara una sola vez por proceso y caso. Quien llega aqui ya paso la dependencia de acceso de su
ruta (`api.sesion_web.exigir_clave_o_sesion`), que valido la ficha.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api import caso_web
from api.sesion_web import COOKIE
from core.catalog import abrir_sesion, abrir_sesion_de_escritura, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from operacion.config import ruta_caso_por_defecto
from operacion.instalacion import motor_de_instalacion, sesion_de_instalacion
from seguridad import claves_api, sesiones

VARIABLE_BASE = "APU_BASE"
_PREFIJO_ARCHIVO = "sqlite:///"
#: El `usuario` de lo que crean las rutas antiguas, que S3 no protege con clave (S5 decide).
USUARIO_SIN_CLAVE = "api (sin clave)"
#: El `usuario` de lo que escriben las rutas con clave (RT-S4-4): `exigir_clave_api` no entrega la
#: identidad de la clave a la ruta, así que la bitácora dice solo que fue por la API.
USUARIO_API = "api (clave de API)"
_motores: dict[str, Engine] = {}
_cerrojo = threading.Lock()


def url_por_defecto() -> str:
    return url_de_ruta(ruta_caso_por_defecto())


def url_de_ruta(ruta: Path) -> str:
    return f"{_PREFIJO_ARCHIVO}{Path(ruta).as_posix()}"


def ruta_de_url(url: str) -> Path | None:
    """El archivo de una URL `sqlite:///...`; `None` si no es un archivo SQLite."""
    if not url.startswith(_PREFIJO_ARCHIVO):
        return None
    ruta = url[len(_PREFIJO_ARCHIVO) :]
    return Path(ruta) if ruta and ruta != ":memory:" else None


def url_del_proceso() -> str:
    """El caso del proceso: `APU_BASE` o el por defecto de la carpeta de datos."""
    return os.environ.get(VARIABLE_BASE, "").strip() or url_por_defecto()


def url_de_la_peticion(request: Request) -> str:
    """El caso de esta peticion: el elegido por su ficha (RM-2) o, con la clave de API o sin
    eleccion, el del proceso. No abre la base."""
    if claves_api.CABECERA in request.headers:
        return url_del_proceso()
    ficha = request.cookies.get(COOKIE)
    if ficha:
        ruta = caso_web.elegido(sesiones.huella_de(ficha))
        if ruta is not None:
            return url_de_ruta(ruta)
    return url_del_proceso()


def carpeta_de_la_peticion(request: Request) -> str | None:
    """El nombre del archivo de la carpeta de esta petición (`None` si no es un archivo)."""
    ruta = ruta_de_url(url_de_la_peticion(request))
    return None if ruta is None else ruta.name


def carpeta_de_la_empresa() -> str | None:
    """El nombre del archivo de la carpeta del proceso, la de la empresa (`None` sin archivo)."""
    ruta = ruta_de_url(url_del_proceso())
    return None if ruta is None else ruta.name


def obtener_motor(url: str) -> Engine:
    """El motor del caso `url`, uno por proceso: la primera vez prepara la base (503 si no se
    puede, sin guardar el motor)."""
    with _cerrojo:
        motor = _motores.get(url)
        if motor is None:
            ruta = ruta_de_url(url)
            if ruta is not None:
                try:
                    preparar_base(ruta)
                except ErrorDeBase as error:
                    raise HTTPException(status_code=503, detail=str(error)) from error
            motor = _motores[url] = crear_motor(url)
        return motor


def cerrar_motores() -> None:
    """Cierra y olvida todos los motores (las pruebas; en Windows un motor abierto retiene el
    archivo del caso)."""
    with _cerrojo:
        for motor in _motores.values():
            motor.dispose()
        _motores.clear()


def sesion_api(request: Request) -> Iterator[Session]:
    with abrir_sesion(obtener_motor(url_de_la_peticion(request))) as sesion:
        yield sesion


def abridor_de_la_carpeta(request: Request) -> Callable[[], AbstractContextManager[Session]]:
    """Abre la sesión del caso de esta petición solo cuando se llama (C11b: el barrido de
    `GET /v1/notificaciones` lee la carpeta solo si la persona recibe compras). Un caso que no se
    puede preparar lanza aquí el 503 de `obtener_motor`; quien la llama decide qué hacer."""
    return lambda: contextmanager(sesion_api)(request)


def sesion_de_escritura_api(request: Request) -> Iterator[Session]:
    """La sesion de una ruta que CREA UNA VERSION (SL-E12, diseno §4.5) o un proyecto (BCP-3, que
    compara el nombre y da el alta bajo el mismo bloqueo): su transaccion empieza con
    `BEGIN IMMEDIATE` en la primera sentencia, asi que quien guarda toma el bloqueo de escritura
    antes de leer la version vigente y el ultimo codigo (el otro espera). No confirma por si
    misma: confirma o deshace la funcion de aplicacion que escribe (todo o nada), y al salir se
    cierra (lo que quede sin confirmar se deshace). Quien la usa envuelve la cadena de anexos.

    Tarea A.9 (DS-56): `expire_on_commit=False`, como `hoja_guardado.guardar`: leer lo confirmado
    para responder no reabre otro `BEGIN IMMEDIATE` (que esperaria a otro que escribe y podria dar
    503 tras un guardado bueno). Lo que se consulta de nuevo tras el `commit` si lo abre; por eso
    `SesionDeEscrituraDep` cierra la sesion con `scope="function"`, antes de enviar."""
    with abrir_sesion_de_escritura(obtener_motor(url_de_la_peticion(request))) as sesion:
        sesion.expire_on_commit = False
        yield sesion


#: Alias de tipo para inyectar la sesion en las rutas sin disparar B008 (ruff): un `Depends(...)`
#: como valor por defecto es una llamada en la firma; dentro de `Annotated` no lo es.
SesionDep = Annotated[Session, Depends(sesion_api)]
#: La de escritura (`BEGIN IMMEDIATE`): para las rutas que crean versiones o proyectos (BCP-3).
#: `scope="function"` (tarea A.9, DS-56): se cierra al volver la ruta, con la respuesta ya
#: serializada y ANTES de enviarla; con el alcance por omision el bloqueo de escritura que reabre
#: una lectura tras el `commit` duraria hasta que el cliente recibe la respuesta. Ninguna ruta que
#: la usa responde en flujo (`StreamingResponse`) leyendo el caso al enviar.
SesionDeEscrituraDep = Annotated[Session, Depends(sesion_de_escritura_api, scope="function")]


def _transaccion_de_instalacion(*, escritura: bool) -> Iterator[Session]:
    """Una transacción de `instalacion.db` por petición: al terminar bien hace `commit`; si la ruta
    lanza cualquier excepción (un 4xx incluido), hace `rollback` y la vuelve a lanzar. Los
    servicios de `produccion/` solo hacen `flush`."""
    try:
        motor_de_instalacion()  # la prepara y migra una vez por proceso; una base mala es un 503
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    with sesion_de_instalacion(escritura=escritura) as sesion:
        if not escritura:
            # `BEGIN` explícito: `pysqlite` no emite `BEGIN` antes de un `SAVEPOINT` (solo antes
            # de un `INSERT`/`UPDATE`/`DELETE`) y, sin él, el `RELEASE` del primer
            # `begin_nested()` de un servicio confirmaría todo y el `rollback` posterior no
            # deshace nada. La de escritura lo abre sola (`BEGIN IMMEDIATE`) en su primera
            # sentencia, sea la que sea.
            sesion.connection().exec_driver_sql("BEGIN")
        try:
            yield sesion
            sesion.commit()
        except BaseException:
            sesion.rollback()
            raise


def sesion_instalacion_api() -> Iterator[Session]:
    """Sesión de `instalacion.db` por petición (arenera, RT-S4-1), `BEGIN` diferido: la de las
    rutas que solo leen y la del control de módulos (`requiere_modulo`) de TODA ruta, incluidas las
    que escriben en el caso o corren una simulación larga. No toma el bloqueo de escritura.

    Las rutas bajo esta dependencia no deben convertir una `HTTPException` en respuesta
    (`RutaSinCache` la relanza): si lo hacen, la sesión ve una salida normal y confirma lo
    escrito a medias."""
    yield from _transaccion_de_instalacion(escritura=False)


def sesion_instalacion_escritura_api() -> Iterator[Session]:
    """La misma transacción por petición, pero con `BEGIN IMMEDIATE` en su primera sentencia: la de
    las rutas que ESCRIBEN tras leer algo que deciden (el último conteo, un contador, si ya existe).
    Toma el bloqueo de escritura antes de leer y la otra petición espera (hasta `busy_timeout`) y
    lo ve ya confirmado, en vez de leer el mismo estado y pisarlo. Se toma al primer uso (no al
    resolver la dependencia): una ruta que escribe también en el caso toca primero el caso y luego
    ésta, siempre en ese orden (caso, instalación), para que dos peticiones no se esperen en cruz.
    Si la ruta pide también la diferida, son dos sesiones: la diferida solo lee (en WAL no
    bloquea)."""
    yield from _transaccion_de_instalacion(escritura=True)


#: `scope="function"`: la salida del generador (el `commit`) corre al volver la ruta, ANTES de
#: enviar la respuesta; con el alcance por omisión correría después y un cliente podría leer antes
#: del commit.
SesionInstalacionDep = Annotated[Session, Depends(sesion_instalacion_api, scope="function")]
#: La de escritura (`BEGIN IMMEDIATE`), solo para las rutas que escriben tras leer lo que deciden.
SesionInstalacionEscrituraDep = Annotated[
    Session, Depends(sesion_instalacion_escritura_api, scope="function")
]


class RespuestaNoArmada(RuntimeError):  # noqa: N818
    """Falló armar la respuesta con lo escrito y antes del `commit` (DS-57): no se guardó nada y
    no es culpa de lo enviado. Sale como error del servidor (500), no como el 422 de un
    `ValueError`."""


def sin_culpar_a_la_entrada[T](armar: Callable[[], T]) -> Callable[[], T]:
    """`armar` para el `antes_de_confirmar` de una función de aplicación: un fallo que no es de la
    base (que sigue siendo 503) ni una `HTTPException` sale como `RespuestaNoArmada`, para que el
    `except ValueError` de la ruta no lo tome por un dato malo y culpe a la entrada (arbitraje de
    DS-57: una `pydantic.ValidationError` es un `ValueError`)."""

    def armada() -> T:
        try:
            return armar()
        except (HTTPException, SQLAlchemyError):
            raise
        except Exception as error:
            raise RespuestaNoArmada("no se pudo armar la respuesta; no se guardó nada") from error

    return armada
