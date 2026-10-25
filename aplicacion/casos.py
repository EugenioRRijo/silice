"""Carpetas de trabajo («casos»): crear, subir, la demostración y el resumen de la abierta (BCP-2).

Diseño `docs/especificaciones/2026-10-21-bienvenida-casos-proyectos-design.md` §4, §9 y §16 (9.1 y
9.2). La interfaz dice «carpeta de trabajo»; el código, la API y la base siguen diciendo `caso`.
Sin FastAPI ni Streamlit: la API (`api/rutas/casos.py`) traduce las excepciones a estados HTTP.

**Nada a medias en `casos/`.** Toda carpeta nueva (creada, subida o la demostración) nace en una
carpeta propia de la petición dentro de `<datos>/cuarentena/` (fuera de `casos/`), se valida y se
prepara allí, y solo entonces se publica: copia con la API de respaldo de SQLite a
`casos/.subiendo-<token>.tmp` (que `listar_casos` no ve: no termina en `.db`) y `os.rename` al
nombre final. `os.rename` nunca pisa en Windows; en POSIX lo cubre la comprobación previa bajo el
cerrojo. Pase lo que pase, la cuarentena de la petición se borra al terminar y la carpeta
`cuarentena/` misma, si quedó vacía.

**Un cerrojo de proceso por toda creación** (la API corre en un solo proceso): la comprobación de
que el nombre está libre (sin distinguir mayúsculas, sobre `listar_casos`), el tope de carpetas y
la publicación van dentro. Se toma con plazo: si otra creación sigue en curso, `CreacionEnCurso`.
Nunca bloquea lecturas ni la hoja de nadie.

**La subida** (DV-BCP-4) se lee por bloques hasta `TOPE_SUBIDA`; se comprueba la firma de SQLite y
se inspecciona en solo lectura con `trusted_schema=OFF`: `quick_check` e `integrity_check` en «ok»,
ningún disparador, vista ni tabla virtual, y las tablas núcleo de un caso de Sílice; una revisión
de Alembic que este código no conoce es `CarpetaMasNueva`. La inspección tiene plazo
(`PLAZO_VALIDACION_S`). Después `preparar_base` sobre la copia de cuarentena (respaldo previo y
migración a `head`, RF-96). Los mensajes al usuario son fijos: ninguno lleva rutas del servidor ni
el texto de SQLite (eso va al registro, sin contenido del archivo).

`estado` reconstruye el `ui.caso.estado_caso` que el retiro de Streamlit borró: conexión de solo
lectura, sin DDL, nunca crea el archivo (RV-5).
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import shutil
import sqlite3
import threading
import time
import unicodedata
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import BinaryIO

from sqlalchemy.exc import SQLAlchemyError

from aplicacion.proyectos import proyectos_del_caso
from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion
from operacion import config, respaldo
from operacion.base_datos import (
    CABECERA_SQLITE,
    EXTENSION,
    MENSAJE_MAS_NUEVA,
    BaseBloqueada,
    BaseMasNueva,
    BaseNoAdoptable,
    CasoYaExiste,
    Destino,
    ErrorDeBase,
    RutaDeCasoRechazada,
    _validar_forma,
    leer_estado,
    listar_casos,
    motor_solo_lectura,
    preparar_base,
    resolver_caso,
    revision_head,
    revisiones_conocidas,
    sanear_nombre,
)
from operacion.demostracion import DemostracionFallida

__all__ = [
    "ArchivoDemasiadoGrande",
    "ArchivoNoValido",
    "CarpetaMasNueva",
    "CarpetaRechazada",
    "CasoYaExiste",
    "CreacionEnCurso",
    "DemostracionFallida",
    "EstadoCarpeta",
    "NombreReservado",
    "PreparacionFallida",
    "Subida",
    "TopeDeCarpetas",
    "crear",
    "demostracion",
    "es_demostracion",
    "estado",
    "purgar_cuarentena",
    "subir_seguro",
    "ubicacion",
]

# --- supuestos (D-4: se adoptan y se miden en BCP-10) --------------------------------------------
#: El del cuerpo de la API (`api.proteccion.LIMITE_CUERPO`); el multipart suma unos cientos de B.
TOPE_SUBIDA = 20 * 1024 * 1024
MAXIMO_CARPETAS = 100
#: Lo que queda en la cuarentena por un corte se purga al arrancar pasada esta antigüedad.
VIDA_CUARENTENA_S = 3600.0
#: Plazo de la inspección de un archivo subido (quick_check e integrity_check).
PLAZO_VALIDACION_S = 60.0
#: Cuánto espera una creación a que termine otra antes de rendirse.
PLAZO_CERROJO_S = 10.0

CARPETA_CUARENTENA = "cuarentena"
NOMBRE_DEMOSTRACION = "demostracion" + EXTENSION
PREFIJO_TEMPORAL = ".subiendo-"
SUFIJO_TEMPORAL = ".tmp"
AUXILIARES_TEMPORAL = ("-journal", "-wal", "-shm")
#: Las tablas que todo caso de Sílice tiene desde la 0.5.0 (revisión `caso_0001`, ficha de v0_5_0).
TABLAS_NUCLEO = frozenset(
    {"composicion_apu", "insumo", "lista_precios", "partida", "precio_insumo", "presupuesto"}
)

# --- mensajes fijos (diseño §9; con tildes, DV-BCP-3) --------------------------------------------
MENSAJE_EXISTE = "Ya existe la carpeta de trabajo {nombre}: ábrala de la lista o elija otro nombre."
MENSAJE_EXISTE_SUBIDA = (
    "Ya hay una carpeta de trabajo llamada {nombre}: cambie el nombre antes de subirla."
)
MENSAJE_TOPE = "Ya hay {maximo} carpetas de trabajo: retire alguna antes de crear otra."
MENSAJE_EN_CURSO = "Hay otra creación de carpeta en curso: espere unos segundos y repita."
MENSAJE_RESERVADO = "Ese nombre está reservado para la demostración."
MENSAJE_SIN_NOMBRE = (
    "El archivo no trae un nombre utilizable: escriba un nombre para la carpeta de trabajo."
)
MENSAJE_GRANDE = "El archivo pasa de 20 MiB."
MENSAJE_NO_ES_SQLITE = "«{nombre}» no es una base de Sílice (SQLite): no se guardó."
MENSAJE_NO_VALIDO = "El archivo no es una carpeta de trabajo de Sílice válida: no se guardó."
MENSAJE_PREPARACION = (
    "No se pudo preparar la carpeta de trabajo: no se guardó. Pruebe de nuevo; si sigue, avise al "
    "administrador."
)
MENSAJE_DEMOSTRACION = (
    "No se pudo preparar la demostración. Pruebe de nuevo; si sigue, avise al administrador."
)
MENSAJE_DEMOSTRACION_OCUPADA = (
    "Ya existe demostracion.db, pero sin los datos de ejemplo: para volver a crearla, el "
    "administrador la retira de la carpeta de datos con Sílice cerrado."
)
AVISO_MIGRADA = "Se actualizó el archivo a la versión actual de Sílice; quedó un respaldo previo."
ERROR_ILEGIBLE = "No se pudo leer esta carpeta de trabajo: restaure un respaldo o elija otra."
ERROR_BLOQUEADA = (
    "Otro programa tiene abierta esta carpeta de trabajo: ciérrelo y vuelva a intentarlo."
)
ERROR_POR_MIGRAR = (
    "Esta carpeta de trabajo se actualizará al abrirla; su resumen aparecerá entonces."
)

_VIRTUAL = re.compile(r"^\s*create\s+virtual\s+table", re.IGNORECASE)
_REVISION_LEGIBLE = re.compile(r"[0-9A-Za-z_]{1,64}")
_BLOQUE = 1 << 20
_OPERACIONES_ENTRE_PLAZOS = 1000
_registro = logging.getLogger("silice.casos")
_cerrojo = threading.Lock()


class CarpetaRechazada(Exception):  # noqa: N818
    """Una carpeta de trabajo no se creó; el mensaje es fijo y dice qué hacer."""


class NombreReservado(RutaDeCasoRechazada):
    """«demostracion» (con o sin mayúsculas o tilde) es de la demostración: 422."""


class TopeDeCarpetas(CarpetaRechazada):
    """Ya hay `MAXIMO_CARPETAS`: 409."""


class CreacionEnCurso(CarpetaRechazada):
    """Otra creación no terminó dentro del plazo del cerrojo: 409 (503 en la demostración)."""


class ArchivoDemasiadoGrande(CarpetaRechazada):
    """La subida pasa de `TOPE_SUBIDA`: 413."""


class ArchivoNoValido(CarpetaRechazada):
    """No es SQLite, está rota, trae disparadores, vistas o tablas virtuales, o no es caso: 422."""


class CarpetaMasNueva(CarpetaRechazada):
    """Su revisión es de un Sílice más nuevo (`MENSAJE_MAS_NUEVA`): 422."""


class PreparacionFallida(CarpetaRechazada):
    """No se pudo preparar o publicar (migración, disco): 503."""


@dataclass(frozen=True, slots=True)
class Subida:
    ruta: Path
    aviso: str | None


@dataclass(frozen=True, slots=True)
class EstadoCarpeta:
    """Lo que la interfaz muestra de la carpeta abierta (RF-39; el `estado_caso` de la clásica)."""

    nombre: str
    ubicacion: str
    partidas: int = 0
    insumos: int = 0
    lista_vigente: str | None = None
    proyectos: int = 0
    proyectos_con_version: int = 0
    es_demostracion: bool = False
    por_migrar: bool = False
    error: str | None = None


# --- nombres -----------------------------------------------------------------------------------


def _sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).casefold()


def es_demostracion(nombre: str) -> bool:
    """Por el nombre (reservado), no por el contenido: `demostracion.db` sin distinguir mayúsculas
    ni la tilde de «demostración»."""
    base = nombre[: -len(EXTENSION)] if nombre.lower().endswith(EXTENSION) else nombre
    return _sin_tildes(base.strip()) == "demostracion"


def _no_reservado(final: str) -> str:
    if es_demostracion(final):
        raise NombreReservado(MENSAJE_RESERVADO)
    return final


def _nombre_elegido(nombre: str) -> str:
    """Un nombre que escribió la persona: la forma de la clásica (sin rutas, `..`, unidades, `:` ni
    reservados de Windows), saneado y no reservado para la demostración."""
    texto = nombre.strip()
    _validar_forma(texto)
    return _no_reservado(sanear_nombre(texto))


def _nombre_de_subida(nombre_archivo: str | None, nombre: str | None) -> str:
    if nombre is not None and nombre.strip():
        return _nombre_elegido(nombre)
    ultimo = PureWindowsPath((nombre_archivo or "").replace("/", "\\")).name.strip()
    if not ultimo or ultimo in {".", ".."}:
        raise RutaDeCasoRechazada(MENSAJE_SIN_NOMBRE)
    return _no_reservado(sanear_nombre(ultimo))


# --- cerrojo, tope y cuarentena ---------------------------------------------------------------


@contextmanager
def _creando() -> Iterator[None]:
    if not _cerrojo.acquire(timeout=PLAZO_CERROJO_S):
        raise CreacionEnCurso(MENSAJE_EN_CURSO)
    try:
        yield
    finally:
        _cerrojo.release()


def _existente(destino: Path) -> Path | None:
    """La carpeta de la lista con el nombre de `destino` sin distinguir mayúsculas (NTFS ya no
    distingue; la CI corre en Linux, que sí)."""
    clave = destino.name.casefold()
    return next((caso for caso in listar_casos() if caso.name.casefold() == clave), None)


def _exigir_libre(destino: Path, plantilla: str) -> None:
    existente = _existente(destino)
    if existente is not None or destino.exists():
        raise CasoYaExiste(plantilla.format(nombre=(existente or destino).name))


def _exigir_bajo_tope() -> None:
    if len(listar_casos()) >= MAXIMO_CARPETAS:
        raise TopeDeCarpetas(MENSAJE_TOPE.format(maximo=MAXIMO_CARPETAS))


def carpeta_cuarentena() -> Path:
    """`<datos>/cuarentena/`: fuera de `casos/`, donde nace todo antes de publicarse."""
    return config.carpeta_datos() / CARPETA_CUARENTENA


def _quitar_si_vacia(carpeta: Path) -> None:
    try:
        carpeta.rmdir()
    except OSError:
        pass  # no existe o tiene lo de otra petición en curso


@contextmanager
def _cuarentena() -> Iterator[Path]:
    """Una carpeta propia de esta petición en la cuarentena; se borra entera al salir."""
    propia = carpeta_cuarentena() / secrets.token_hex(16)
    propia.mkdir(parents=True)  # exclusiva: el token no se repite
    try:
        yield propia
    finally:
        shutil.rmtree(propia, ignore_errors=True)
        _quitar_si_vacia(carpeta_cuarentena())


def _publicar(origen: Path, destino: Path, plantilla: str = MENSAJE_EXISTE) -> None:
    """Copia `origen` (consolida el WAL) a un temporal invisible de `casos/` y lo renombra al nombre
    final. Se llama con el cerrojo tomado y tras `_exigir_libre`."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.parent / f"{PREFIJO_TEMPORAL}{secrets.token_hex(16)}{SUFIJO_TEMPORAL}"
    try:
        respaldo.copiar_sqlite(origen, temporal)
        with closing(sqlite3.connect(temporal)) as copia:  # sin WAL: leerla no deja -wal ni -shm
            copia.execute("PRAGMA journal_mode = DELETE").fetchall()
        os.rename(temporal, destino)  # en Windows falla si el destino existe: nunca pisa
    except FileExistsError:
        raise CasoYaExiste(plantilla.format(nombre=destino.name)) from None
    except (OSError, sqlite3.Error) as error:
        _registro.warning("no se pudo publicar una carpeta de trabajo: %s", type(error).__name__)
        raise PreparacionFallida(MENSAJE_PREPARACION) from None
    finally:
        for resto in (temporal, *(Path(f"{temporal}{s}") for s in ("-journal", "-wal", "-shm"))):
            try:
                resto.unlink(missing_ok=True)
            except OSError:
                pass


def _preparar(ruta: Path) -> str | None:
    """`preparar_base` sobre la copia de la cuarentena; el aviso si hubo que migrar con respaldo."""
    try:
        resultado = preparar_base(ruta, motivo=respaldo.MOTIVO_SUBIDA)
    except BaseMasNueva as error:
        raise CarpetaMasNueva(str(error)) from None
    except BaseNoAdoptable:
        raise ArchivoNoValido(MENSAJE_NO_VALIDO) from None
    except ErrorDeBase as error:
        _registro.warning("no se pudo preparar una carpeta de trabajo: %s", type(error).__name__)
        raise PreparacionFallida(MENSAJE_PREPARACION) from None
    return None if resultado.juego is None else AVISO_MIGRADA


# --- validación de un archivo ajeno --------------------------------------------------------------


def _tablas_conocidas() -> frozenset[str]:
    from migraciones.metadatos import METADATAS_CASO  # diferido: solo para el registro

    return frozenset(t for metadata in METADATAS_CASO for t in metadata.tables) | {
        respaldo.TABLA_VERSION
    }


def _inspeccionar(archivo: Path) -> tuple[set[str], str | None]:
    """Las tablas y la revisión de `archivo`, en solo lectura, con plazo. `ArchivoNoValido` si no
    pasa las comprobaciones de integridad o trae disparadores, vistas o tablas virtuales."""
    limite = time.monotonic() + PLAZO_VALIDACION_S
    try:
        with closing(respaldo.abrir_solo_lectura(archivo)) as conexion:
            conexion.text_factory = lambda crudo: crudo.decode("utf-8", "replace")
            conexion.set_progress_handler(
                lambda: int(time.monotonic() > limite), _OPERACIONES_ENTRE_PLAZOS
            )
            conexion.execute("PRAGMA trusted_schema = OFF")
            for comprobacion in ("quick_check", "integrity_check"):
                filas = [str(fila[0]) for fila in conexion.execute(f"PRAGMA {comprobacion}")]
                if filas != ["ok"]:
                    _registro.warning("subida rechazada: %s no dio ok", comprobacion)
                    raise ArchivoNoValido(MENSAJE_NO_VALIDO)
            esquema = conexion.execute("SELECT type, sql FROM sqlite_master").fetchall()
            tablas = respaldo.tablas_de(conexion)
            revision = respaldo.revision_de(conexion)
    except (sqlite3.Error, UnicodeDecodeError) as error:  # el mensaje de SQLite puede no ser UTF-8
        _registro.warning("subida rechazada: SQLite no la lee (%s)", type(error).__name__)
        raise ArchivoNoValido(MENSAJE_NO_VALIDO) from None
    for tipo, sql in esquema:
        if tipo in {"trigger", "view"} or (sql and _VIRTUAL.search(sql)):
            _registro.warning("subida rechazada: trae un objeto de tipo %s", tipo)
            raise ArchivoNoValido(MENSAJE_NO_VALIDO)
    return tablas, revision


def _validar(archivo: Path, nombre: str) -> None:
    """Pasos 4 a 6 de §4.4 sobre la copia de la cuarentena; nunca la modifica."""
    with archivo.open("rb") as entrada:
        if entrada.read(len(CABECERA_SQLITE)) != CABECERA_SQLITE:
            raise ArchivoNoValido(MENSAJE_NO_ES_SQLITE.format(nombre=nombre))
    tablas, revision = _inspeccionar(archivo)
    if revision is not None and revision not in revisiones_conocidas(Destino.CASO):
        if revision in revisiones_conocidas(Destino.INSTALACION) or not (
            _REVISION_LEGIBLE.fullmatch(revision)
        ):
            raise ArchivoNoValido(MENSAJE_NO_VALIDO)
        raise CarpetaMasNueva(MENSAJE_MAS_NUEVA.format(nombre=nombre, revision=revision))
    if not TABLAS_NUCLEO <= tablas:
        _registro.warning("subida rechazada: faltan tablas núcleo de un caso")
        raise ArchivoNoValido(MENSAJE_NO_VALIDO)
    extra = len(tablas - _tablas_conocidas())
    if extra:
        _registro.info("subida con %s tabla(s) que este Sílice no conoce", extra)


def _copiar_con_tope(fuente: BinaryIO, destino: Path, tope: int) -> None:
    leidos = 0
    with destino.open("xb") as salida:
        while bloque := fuente.read(_BLOQUE):
            leidos += len(bloque)
            if leidos > tope:
                raise ArchivoDemasiadoGrande(MENSAJE_GRANDE)
            salida.write(bloque)


# --- las tres maneras de tener una carpeta nueva -------------------------------------------------


def crear(nombre: str) -> Path:
    """Una carpeta vacía en `head` con el nombre saneado (§4.3). Devuelve su ruta final."""
    final = _nombre_elegido(nombre)
    destino = resolver_caso(final)
    with _creando():
        _exigir_libre(destino, MENSAJE_EXISTE)
        _exigir_bajo_tope()
        with _cuarentena() as propia:
            nueva = propia / final
            _preparar(nueva)
            _publicar(nueva, destino)
    return destino


def subir_seguro(
    contenido: BinaryIO,
    nombre_archivo: str | None,
    nombre: str | None = None,
    *,
    tope: int = TOPE_SUBIDA,
) -> Subida:
    """Un `.db` ajeno, todo o nada (§4.4): nada llega a `casos/` sin validarse, respaldarse y
    migrarse, y un archivo rechazado no deja nada en la carpeta de datos."""
    final = _nombre_de_subida(nombre_archivo, nombre)
    destino = resolver_caso(final)
    _exigir_libre(destino, MENSAJE_EXISTE_SUBIDA)  # temprano, sin cerrojo: no trabajar en balde
    _exigir_bajo_tope()
    with _cuarentena() as propia:
        archivo = propia / final
        _copiar_con_tope(contenido, archivo, tope)
        _validar(archivo, final)
        aviso = _preparar(archivo)
        with _creando():
            _exigir_libre(destino, MENSAJE_EXISTE_SUBIDA)
            _exigir_bajo_tope()
            _publicar(archivo, destino, MENSAJE_EXISTE_SUBIDA)
    return Subida(destino, aviso)


def demostracion(construir: Callable[[Path], None]) -> tuple[Path, bool]:
    """La carpeta `demostracion.db` (§4.5). `(ruta, True)` si la creó; `(ruta, False)` si ya
    existía con partidas, sin tocarla. `construir(salida)` siembra `salida` (absoluta, en la
    cuarentena) en un proceso hijo (`operacion.demostracion.construir`; las pruebas pasan un
    doble). No toca ninguna otra carpeta."""
    destino = resolver_caso(NOMBRE_DEMOSTRACION)
    with _creando():
        existente = _existente(destino)
        if existente is not None:
            resumen = estado(existente)
            if resumen.error is None and resumen.partidas > 0:
                return existente, False
            raise CasoYaExiste(MENSAJE_DEMOSTRACION_OCUPADA)
        _exigir_bajo_tope()
        with _cuarentena() as propia:
            salida = propia.resolve() / NOMBRE_DEMOSTRACION
            try:
                construir(salida)
                _validar(salida, NOMBRE_DEMOSTRACION)
            except (DemostracionFallida, CarpetaRechazada, OSError):
                raise DemostracionFallida(MENSAJE_DEMOSTRACION) from None
            _publicar(salida, destino)
    return destino, True


# --- mantenimiento -------------------------------------------------------------------------------


def _antiguo(ruta: Path, ahora: float) -> bool:
    try:
        return ahora - ruta.stat().st_mtime > VIDA_CUARENTENA_S
    except OSError:
        return False


def purgar_cuarentena(ahora: float | None = None) -> int:
    """Al arrancar la API: borra lo de la cuarentena y los `casos/.subiendo-*.tmp` de más de una
    hora (un corte a mitad de una creación). Devuelve cuántos quitó; no crea nada."""
    momento = time.time() if ahora is None else ahora
    quitados = 0
    cuarentena = carpeta_cuarentena()
    if cuarentena.is_dir():
        for resto in cuarentena.iterdir():
            if _antiguo(resto, momento):
                if resto.is_dir():
                    shutil.rmtree(resto, ignore_errors=True)
                else:
                    resto.unlink(missing_ok=True)
                quitados += not resto.exists()
        _quitar_si_vacia(cuarentena)
    carpeta_casos = config.carpeta_casos()
    if carpeta_casos.is_dir():
        # Con los auxiliares de SQLite: un corte a mitad de la copia deja -journal, -wal y -shm.
        for sufijo in ("", *AUXILIARES_TEMPORAL):
            patron = f"{PREFIJO_TEMPORAL}*{SUFIJO_TEMPORAL}{sufijo}"
            for temporal in carpeta_casos.glob(patron):
                if temporal.is_file() and _antiguo(temporal, momento):
                    temporal.unlink(missing_ok=True)
                    quitados += 1
    return quitados


# --- la carpeta abierta ------------------------------------------------------------------------


def _relativa(ruta: Path, base: Path) -> Path | None:
    try:
        return ruta.relative_to(base.resolve())
    except ValueError:
        return None


def ubicacion(ruta: Path) -> str:
    """Dónde está la carpeta, en llano y **sin ruta absoluta**: en el producto, con la variable
    `%LOCALAPPDATA%` literal; en desarrollo, relativa a la carpeta del programa; si no, relativa a
    la carpeta de datos; fuera de todo, solo el nombre."""
    ruta = Path(ruta).resolve()
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if config.es_producto() and local:
        relativa = _relativa(ruta, Path(local))
        if relativa is not None:
            return "En %LOCALAPPDATA%\\" + "\\".join(relativa.parts)
    relativa = _relativa(ruta, config.RAIZ)
    if relativa is not None:
        return f"En {relativa.as_posix()}"
    relativa = _relativa(ruta, config.carpeta_datos())
    if relativa is not None:
        return f"En la carpeta de datos de Sílice: {relativa.as_posix()}"
    return f"Fuera de la carpeta de datos de Sílice: {ruta.name}"


def estado(ruta: Path) -> EstadoCarpeta:
    """El resumen de la carpeta en `ruta`, sin crear el archivo y sin DDL (RV-5). Los errores son
    textos fijos sin rutas."""
    ruta = Path(ruta)
    comun = {
        "nombre": ruta.name,
        "ubicacion": ubicacion(ruta),
        "es_demostracion": es_demostracion(ruta.name),
    }
    if not ruta.exists():
        return EstadoCarpeta(**comun)
    try:
        base = leer_estado(ruta)
    except BaseBloqueada:
        return EstadoCarpeta(**comun, error=ERROR_BLOQUEADA)
    except ErrorDeBase:
        return EstadoCarpeta(**comun, error=ERROR_ILEGIBLE)
    if base.revision is not None and base.revision not in revisiones_conocidas(Destino.CASO):
        texto = MENSAJE_MAS_NUEVA.format(nombre=ruta.name, revision=base.revision)
        return EstadoCarpeta(**comun, error=texto)
    por_migrar = base.revision != revision_head(Destino.CASO)
    if base.sin_datos:
        return EstadoCarpeta(**comun, por_migrar=por_migrar)
    motor = motor_solo_lectura(ruta)
    try:
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            try:
                lista: str | None = catalogo.lista_vigente().nombre
            except CatalogoIncompleto:
                lista = None
            proyectos = proyectos_del_caso(sesion)
            return EstadoCarpeta(
                **comun,
                partidas=len(catalogo.partidas()),
                insumos=len(catalogo.insumos()),
                lista_vigente=lista,
                proyectos=len(proyectos),
                proyectos_con_version=sum(p.version_id is not None for p in proyectos),
                por_migrar=por_migrar,
            )
    except (SQLAlchemyError, sqlite3.Error) as error:
        _registro.info("resumen de una carpeta no disponible: %s", type(error).__name__)
        return EstadoCarpeta(
            **comun, por_migrar=por_migrar, error=ERROR_POR_MIGRAR if por_migrar else ERROR_ILEGIBLE
        )
    finally:
        motor.dispose()
