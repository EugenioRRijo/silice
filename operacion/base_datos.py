"""Abrir una base de Sílice: `preparar_base` y la lista de casos (RF-96; spec S5 §6.4 y §6.6).

Un caso se abre **solo** con `preparar_base` (RV-5). Una base nueva nace en `head` por las
revisiones. Una base anterior (sin `alembic_version`: la 0.5.0 o una de desarrollo creada con
`create_all`) o con una revisión vieja se **respalda** (juego con ficha, `operacion.respaldo`), se
migra sobre una **copia de trabajo** y, solo si llega entera a `head`, se devuelve a su archivo con
la API de respaldo de `sqlite3`, que es transaccional: si algo falla antes, el archivo original no
se tocó (su SHA-256 es el de antes). Una base de una versión más nueva, ilegible, bloqueada o no
adoptable se rechaza con un mensaje que dice qué hacer, sin modificarla.

Dos destinos (DA-S5-7): la base de cada caso y la de la instalación, cada una con su entorno en
`migraciones/<destino>/` y su `alembic_version`. Sin `alembic.ini`: la configuración se arma aquí.

Los casos viven en `<datos>/casos/` y se eligen de `listar_casos`; un nombre que llega del usuario
pasa por `resolver_caso` (`resolve` + `is_relative_to`): se rechazan rutas UNC, absolutas, con `..`
o con carpetas antes de tocar el disco. `SILICE_CASO` y `APU_BASE` son configuración de quien
arranca (el lanzador, las pruebas), no entrada del usuario: se preparan sin pasar por la lista.
"""

from __future__ import annotations

import functools
import re
import shutil
import sqlite3
import unicodedata
from collections.abc import Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.pool import NullPool

import migraciones
from migraciones.comun import BaseNoAdoptable, ErrorDeBase
from operacion import config, respaldo
from operacion.respaldo import RespaldoFallido, Restauracion

CARPETA_MIGRACIONES = Path(migraciones.__file__).resolve().parent

__all__ = ["BaseNoAdoptable", "ErrorDeBase", "RespaldoFallido", "Restauracion"]


class Destino(StrEnum):
    CASO = "caso"
    INSTALACION = "instalacion"


class MigracionFallida(ErrorDeBase):  # noqa: N818
    """Una revisión falló o dejó la base inconsistente; la base original no se modificó."""


def _configuracion(destino: Destino) -> Config:
    configuracion = Config()
    ubicacion = str(CARPETA_MIGRACIONES / destino.value).replace("%", "%%")
    configuracion.set_main_option("script_location", ubicacion)
    configuracion.set_main_option("path_separator", "os")
    configuracion.set_main_option("version_path_separator", "os")
    return configuracion


@functools.cache
def _guion(destino: Destino) -> ScriptDirectory:
    return ScriptDirectory.from_config(_configuracion(destino))


def revision_head(destino: Destino) -> str | None:
    """La última revisión del destino; `None` mientras no tenga ninguna (la instalación hoy)."""
    return _guion(destino).get_current_head()


def revisiones_conocidas(destino: Destino) -> frozenset[str]:
    return frozenset(script.revision for script in _guion(destino).walk_revisions())


def revisiones_en_orden(destino: Destino) -> list[str]:
    """De la base a `head`."""
    return list(reversed([script.revision for script in _guion(destino).walk_revisions()]))


def motor_de_migracion(ruta: Path) -> Engine:
    """Motor SIN `PRAGMA foreign_keys`: el modo batch de Alembic recrea tablas y, con las claves
    activas, borrar la tabla vieja dispararía las foráneas. Se comprueban al terminar."""
    return create_engine(URL.create("sqlite", database=str(ruta)))


def aplicar_revisiones(ruta: Path, destino: Destino, objetivo: str = "head") -> None:
    """`upgrade` hasta `objetivo` y, después, `foreign_key_check` e `integrity_check`."""
    motor = motor_de_migracion(ruta)
    try:
        with motor.begin() as conexion:
            configuracion = _configuracion(destino)
            configuracion.attributes["connection"] = conexion
            command.upgrade(configuracion, objetivo)
        with motor.connect() as conexion:
            rotas = conexion.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            integridad = [str(f[0]) for f in conexion.exec_driver_sql("PRAGMA integrity_check")]
    finally:
        motor.dispose()
    if rotas:
        raise MigracionFallida(
            f"Tras migrar {ruta.name} quedaron {len(rotas)} filas con claves foráneas rotas."
        )
    if integridad != ["ok"]:
        raise MigracionFallida(
            f"Tras migrar {ruta.name}, integrity_check: {'; '.join(integridad[:5])}."
        )


def deshacer_revisiones(ruta: Path, destino: Destino, objetivo: str = "base") -> None:
    """`downgrade` (DA-S5-6): existe y se prueba en la CI; nunca se ofrece al usuario."""
    motor = motor_de_migracion(ruta)
    try:
        with motor.begin() as conexion:
            configuracion = _configuracion(destino)
            configuracion.attributes["connection"] = conexion
            command.downgrade(configuracion, objetivo)
    finally:
        motor.dispose()


SUFIJO_TRABAJO = ".migrando"
EXTENSION = ".db"
LARGO_MAXIMO_NOMBRE = 80
CABECERA_SQLITE = b"SQLite format 3\x00"
MENSAJE_MAS_NUEVA = (
    "Esta base ({nombre}) es de una versión más nueva de Sílice (revisión {revision}). Instale esa "
    "versión o restaure el respaldo previo; no se modificó."
)
_RESERVADOS_WINDOWS = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{n}" for n in range(1, 10)),
        *(f"LPT{n}" for n in range(1, 10)),
    }
)
_NO_PERMITIDO = re.compile(r"[^\w\- .]")  # `\w` es Unicode: conserva tildes y ñ


class RutaDeCasoRechazada(ErrorDeBase):  # noqa: N818
    """El nombre o la ruta de un caso sale de la carpeta de casos; se rechaza sin tocar el disco."""


class BaseIlegible(ErrorDeBase):  # noqa: N818
    """El archivo no es una base SQLite legible (o es una carpeta)."""


class BaseBloqueada(ErrorDeBase):  # noqa: N818
    """Otro proceso tiene la base bloqueada o la cambió durante la migración; no se modificó."""


class BaseMasNueva(ErrorDeBase):  # noqa: N818
    """La base tiene una revisión que este código no conoce (bajó de versión, §6.4 3d)."""


@dataclass(frozen=True, slots=True)
class EstadoBase:
    """Lo que se lee de una base sin escribir nada."""

    existe: bool
    tablas: frozenset[str] = frozenset()
    revision: str | None = None

    @property
    def sin_datos(self) -> bool:
        return not (self.tablas - {respaldo.TABLA_VERSION})


@dataclass(frozen=True, slots=True)
class ResultadoPreparacion:
    ruta: Path
    destino: Destino
    revision_origen: str | None  # `None`: base sin `alembic_version` (adoptada) o nueva
    revision_destino: str | None  # `head` del destino; `None` mientras no tenga revisiones
    juego: Path | None  # el juego de respaldo previo, si hubo que migrar una base con datos
    nueva: bool  # la base no existía o no tenía tablas


def _es_bloqueo(error: sqlite3.Error) -> bool:
    texto = str(error).lower()
    return "locked" in texto or "busy" in texto


def leer_estado(ruta: Path) -> EstadoBase:
    """Existencia, tablas y revisión, con una conexión de solo lectura: nunca crea ni escribe."""
    ruta = Path(ruta)
    if not ruta.exists():
        return EstadoBase(existe=False)
    if ruta.is_dir():
        raise BaseIlegible(f"{ruta} es una carpeta, no una base de Sílice.")
    try:
        with closing(respaldo.abrir_solo_lectura(ruta)) as conexion:
            tablas = frozenset(respaldo.tablas_de(conexion))
            revision = respaldo.revision_de(conexion)
    except sqlite3.OperationalError as error:
        if _es_bloqueo(error):
            raise BaseBloqueada(
                f"La base {ruta.name} está bloqueada por otro programa ({error}). Ciérrelo y "
                "vuelva a intentarlo; no se modificó."
            ) from error
        raise BaseIlegible(
            f"{ruta.name} no es una base de Sílice legible ({error}). Restaure un respaldo o elija "
            "otro caso."
        ) from error
    except sqlite3.DatabaseError as error:
        raise BaseIlegible(
            f"{ruta.name} no es una base de Sílice legible ({error}). Restaure un respaldo o elija "
            "otro caso."
        ) from error
    return EstadoBase(existe=True, tablas=tablas, revision=revision)


def _heads() -> dict[str, str | None]:
    return {destino.value: revision_head(destino) for destino in Destino}


def _clasificar(ruta: Path, destino: Destino) -> tuple[str, EstadoBase]:
    """«al_dia», «nueva» o «pendiente»; `BaseMasNueva` si la revisión es desconocida."""
    estado = leer_estado(ruta)
    if estado.existe and respaldo.TABLA_VERSION in estado.tablas:
        if estado.revision == revision_head(destino):
            return "al_dia", estado
    if estado.revision is not None and estado.revision not in revisiones_conocidas(destino):
        raise BaseMasNueva(MENSAJE_MAS_NUEVA.format(nombre=ruta.name, revision=estado.revision))
    if not estado.existe or estado.sin_datos:
        return "nueva", estado
    return "pendiente", estado


def _crear(ruta: Path, destino: Destino) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        aplicar_revisiones(ruta, destino)
    except ErrorDeBase:
        raise
    except Exception as error:  # una revisión puede lanzar cualquier cosa
        raise MigracionFallida(f"No se pudo crear {ruta.name}: {error}.") from error


def _devolver(
    bases: Sequence[tuple[Path, Destino]],
    trabajos: Mapping[Path, Path],
    huellas: Mapping[Path, str],
    juego: Path,
) -> None:
    """Devuelve cada copia migrada a su archivo; si una no se puede, repone las ya devueltas."""
    devueltas: list[tuple[Path, Destino]] = []
    for ruta, destino in bases:
        try:
            if respaldo.huella(ruta) != huellas[ruta]:
                raise BaseBloqueada(
                    f"La base {ruta.name} cambió mientras se migraba (¿otra ventana de Sílice la "
                    "usa?). No se modificó: vuelva a abrirla."
                )
            respaldo.copiar_sqlite(trabajos[ruta], ruta)
        except (BaseBloqueada, OSError, sqlite3.Error) as error:
            for ya, su_destino in devueltas:
                respaldo.copiar_sqlite(respaldo.ruta_en_juego(juego, ya, su_destino.value), ya)
            if isinstance(error, BaseBloqueada):
                raise
            raise BaseBloqueada(
                f"No se pudo escribir {ruta.name} ({error}): otro programa la tiene abierta. No se "
                f"modificó; el respaldo previo está en {juego}."
            ) from error
        devueltas.append((ruta, destino))


def _migrar(bases: Sequence[tuple[Path, Destino]], entorno: Mapping[str, str] | None) -> Path:
    """Un juego para todas; cada una se migra en su copia de trabajo y se devuelve solo si todas
    llegaron a `head`. Un fallo antes de devolver deja los originales intactos (RF-96 c)."""
    huellas = {ruta: respaldo.huella(ruta) for ruta, _ in bases}
    ruta_instalacion = next(
        (ruta for ruta, destino in bases if destino is Destino.INSTALACION),
        config.ruta_instalacion(entorno),
    )
    juego = respaldo.respaldar(
        [ruta for ruta, destino in bases if destino is Destino.CASO],
        respaldo.MOTIVO_MIGRACION,
        ruta_instalacion=ruta_instalacion,
        carpeta_respaldos=config.carpeta_respaldos(entorno),
        heads=_heads(),
    )
    trabajos: dict[Path, Path] = {}
    try:
        for ruta, destino in bases:
            trabajo = ruta.with_name(ruta.name + SUFIJO_TRABAJO)
            trabajo.unlink(missing_ok=True)
            shutil.copyfile(respaldo.ruta_en_juego(juego, ruta, destino.value), trabajo)
            trabajos[ruta] = trabajo
            try:
                aplicar_revisiones(trabajo, destino)
            except ErrorDeBase:
                raise
            except Exception as error:  # una revisión puede lanzar cualquier cosa
                raise MigracionFallida(
                    f"La migración de {ruta.name} falló ({type(error).__name__}: {error}). La base "
                    f"no se modificó; el respaldo previo está en {juego}."
                ) from error
        _devolver(bases, trabajos, huellas, juego)
    finally:
        for trabajo in trabajos.values():
            trabajo.unlink(missing_ok=True)
    respaldo.podar_juegos(config.carpeta_respaldos(entorno))
    return juego


def preparar_base(
    ruta: Path, destino: Destino = Destino.CASO, *, entorno: Mapping[str, str] | None = None
) -> ResultadoPreparacion:
    """El único camino para abrir una base (RV-5): al día, la deja; nueva, la crea en `head`;
    anterior, la respalda y la migra (spec S5 §6.4). Idempotente."""
    ruta = Path(ruta)
    clase, estado = _clasificar(ruta, destino)
    head = revision_head(destino)
    if clase == "al_dia":
        return ResultadoPreparacion(ruta, destino, estado.revision, head, None, False)
    if clase == "nueva":
        _crear(ruta, destino)
        return ResultadoPreparacion(ruta, destino, None, head, None, True)
    juego = _migrar([(ruta, destino)], entorno)
    return ResultadoPreparacion(ruta, destino, estado.revision, head, juego, False)


def migrar_todo(entorno: Mapping[str, str] | None = None) -> list[ResultadoPreparacion]:
    """La instalación y todos los casos de la carpeta a `head`, con un solo juego (spec S5 §5.4)."""
    candidatos = [(config.ruta_instalacion(entorno), Destino.INSTALACION)]
    candidatos += [(caso, Destino.CASO) for caso in listar_casos(entorno=entorno)]
    resultados: list[ResultadoPreparacion] = []
    pendientes: list[tuple[Path, Destino, str | None]] = []
    for ruta, destino in candidatos:
        clase, estado = _clasificar(ruta, destino)
        head = revision_head(destino)
        if clase == "al_dia":
            resultados.append(
                ResultadoPreparacion(ruta, destino, estado.revision, head, None, False)
            )
        elif clase == "nueva":
            _crear(ruta, destino)
            resultados.append(ResultadoPreparacion(ruta, destino, None, head, None, True))
        else:
            pendientes.append((ruta, destino, estado.revision))
    if pendientes:
        juego = _migrar([(ruta, destino) for ruta, destino, _ in pendientes], entorno)
        resultados += [
            ResultadoPreparacion(ruta, destino, origen, revision_head(destino), juego, False)
            for ruta, destino, origen in pendientes
        ]
    return resultados


def respaldar_todo(entorno: Mapping[str, str] | None = None) -> Path:
    """Juego manual de la instalación y de todos los casos (no se poda nunca)."""
    return respaldo.respaldar(
        listar_casos(entorno=entorno),
        respaldo.MOTIVO_MANUAL,
        ruta_instalacion=config.ruta_instalacion(entorno),
        carpeta_respaldos=config.carpeta_respaldos(entorno),
        heads=_heads(),
    )


def restaurar_juego(
    juego: Path, *, solo_caso: str | None = None, entorno: Mapping[str, str] | None = None
) -> Restauracion:
    return respaldo.restaurar(
        Path(juego),
        ruta_instalacion=config.ruta_instalacion(entorno),
        carpeta_casos=config.carpeta_casos(entorno),
        carpeta_datos=config.carpeta_datos(entorno),
        carpeta_respaldos=config.carpeta_respaldos(entorno),
        heads=_heads(),
        conocidas={destino.value: revisiones_conocidas(destino) for destino in Destino},
        solo_caso=solo_caso,
    )


def motor_solo_lectura(ruta: Path) -> Engine:
    """Motor que no puede escribir (URI `mode=ro`): leer el estado no emite DDL ni crea nada."""
    uri = respaldo.uri_solo_lectura(Path(ruta))
    return create_engine(
        "sqlite://",
        creator=lambda: sqlite3.connect(uri, uri=True, check_same_thread=False),
        poolclass=NullPool,
    )


# --- casos en la carpeta de datos (spec S5 §6.6) --------------------------------------------------


def _carpeta(carpeta: Path | None, entorno: Mapping[str, str] | None) -> Path:
    return config.carpeta_casos(entorno) if carpeta is None else Path(carpeta)


def _es_reservado(nombre: str) -> bool:
    return PureWindowsPath(nombre).name.split(".")[0].strip().upper() in _RESERVADOS_WINDOWS


def _validar_forma(texto: str) -> None:
    """Rechaza UNC, absolutas, `..`, carpetas, `:` (unidad o flujo alterno de NTFS) y nombres
    reservados de Windows, sin resolver nada en el disco."""
    if not texto:
        raise RutaDeCasoRechazada("Elija un caso: el nombre no puede quedar vacío.")
    if texto.startswith(("\\\\", "//")):
        raise RutaDeCasoRechazada(f"«{texto}» es una ruta de red (UNC): elija un caso de la lista.")
    ventanas, posix = PureWindowsPath(texto), PurePosixPath(texto)
    if ventanas.drive or ventanas.root or posix.is_absolute():
        raise RutaDeCasoRechazada(f"«{texto}» es una ruta absoluta: elija un caso de la lista.")
    if ".." in ventanas.parts or ".." in posix.parts:
        raise RutaDeCasoRechazada(f"«{texto}» sale de la carpeta de casos (..).")
    if len(ventanas.parts) != 1 or len(posix.parts) != 1:
        raise RutaDeCasoRechazada(f"«{texto}» lleva carpetas: escriba solo el nombre del caso.")
    if ":" in texto:
        raise RutaDeCasoRechazada(f"«{texto}» no puede llevar «:».")
    if _es_reservado(texto):
        raise RutaDeCasoRechazada(f"«{texto}» es un nombre reservado de Windows: elija otro.")


def listar_casos(
    carpeta: Path | None = None, *, entorno: Mapping[str, str] | None = None
) -> list[Path]:
    """Los `.db` de la carpeta de casos, por nombre; vacía (y sin crearla) si no existe."""
    carpeta = _carpeta(carpeta, entorno)
    if not carpeta.is_dir():
        return []
    return sorted(
        (ruta for ruta in carpeta.iterdir() if ruta.is_file() and ruta.suffix.lower() == EXTENSION),
        key=lambda ruta: ruta.name.casefold(),
    )


def resolver_caso(
    nombre: str, carpeta: Path | None = None, *, entorno: Mapping[str, str] | None = None
) -> Path:
    """La ruta del caso `nombre` dentro de la carpeta de casos (`resolve` + `is_relative_to`).
    `RutaDeCasoRechazada` antes de tocar el disco si sale de ella."""
    texto = nombre.strip()
    _validar_forma(texto)
    if not texto.lower().endswith(EXTENSION):
        texto += EXTENSION
    base = _carpeta(carpeta, entorno).resolve()
    ruta = (base / texto).resolve()
    if not ruta.is_relative_to(base) or ruta.parent != base:
        raise RutaDeCasoRechazada(f"«{nombre.strip()}» queda fuera de la carpeta de casos.")
    return ruta


def sanear_nombre(nombre: str) -> str:
    """Nombre de archivo seguro para un caso nuevo o subido: solo la última parte, sin caracteres
    raros (conserva tildes y ñ), con `.db`. `RutaDeCasoRechazada` si queda vacío o reservado."""
    ultimo = unicodedata.normalize("NFC", PureWindowsPath(nombre.replace("/", "\\")).name)
    if ultimo.lower().endswith(EXTENSION):
        ultimo = ultimo[: -len(EXTENSION)]
    limpio = _NO_PERMITIDO.sub("_", ultimo).strip(" .")[:LARGO_MAXIMO_NOMBRE].strip(" .")
    if not limpio or _es_reservado(limpio):
        raise RutaDeCasoRechazada(
            f"«{nombre}» no sirve como nombre de caso: use letras, números, espacios, guiones "
            "o puntos."
        )
    return limpio + EXTENSION


def crear_caso(
    nombre: str, carpeta: Path | None = None, *, entorno: Mapping[str, str] | None = None
) -> ResultadoPreparacion:
    _validar_forma(nombre.strip())
    ruta = resolver_caso(sanear_nombre(nombre), carpeta, entorno=entorno)
    if ruta.exists():
        raise RutaDeCasoRechazada(
            f"Ya existe el caso {ruta.name}: ábralo de la lista o elija otro nombre."
        )
    return preparar_base(ruta, entorno=entorno)


def subir_caso(
    nombre_original: str,
    contenido: bytes,
    carpeta: Path | None = None,
    *,
    entorno: Mapping[str, str] | None = None,
) -> ResultadoPreparacion:
    """Copia un `.db` subido a la carpeta de casos con nombre saneado y lo prepara; si no se puede
    preparar, no queda en la carpeta."""
    ruta = resolver_caso(sanear_nombre(nombre_original), carpeta, entorno=entorno)
    if ruta.exists():
        raise RutaDeCasoRechazada(
            f"Ya hay un caso llamado {ruta.name}: cambie el nombre del archivo antes de subirlo."
        )
    if not contenido.startswith(CABECERA_SQLITE):
        raise BaseIlegible(f"«{nombre_original}» no es una base de Sílice (SQLite): no se guardó.")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)
    try:
        return preparar_base(ruta, entorno=entorno)
    except ErrorDeBase:
        ruta.unlink(missing_ok=True)
        raise


def adoptar_base(
    origen: Path, nombre: str | None = None, *, entorno: Mapping[str, str] | None = None
) -> ResultadoPreparacion:
    """Adopta una base que vive fuera de la carpeta de casos (la `data/apu.db` de la 0.5.0, la de
    `SILICE_CASO` o la de `APU_BASE`): la COPIA con la API de respaldo a `<datos>/casos/` y prepara
    la copia. El original nunca se modifica (huella igual)."""
    origen = Path(origen)
    if not leer_estado(origen).existe:
        raise BaseIlegible(f"No existe {origen}.")
    ruta = resolver_caso(sanear_nombre(nombre or origen.name), entorno=entorno)
    if ruta.exists():
        raise RutaDeCasoRechazada(f"Ya existe el caso {ruta.name}: adopte con otro --nombre.")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        respaldo.copiar_sqlite(origen, ruta)
    except sqlite3.Error as error:
        ruta.unlink(missing_ok=True)
        raise BaseIlegible(f"No se pudo copiar {origen}: {error}.") from error
    try:
        return preparar_base(ruta, entorno=entorno)
    except ErrorDeBase:
        ruta.unlink(missing_ok=True)
        raise
