"""Juegos de respaldo de las dos bases y su restauración (RF-96; spec S5 §6.3 y §6.5).

Un **juego** es la carpeta `<respaldos>/<AAAAMMDD-HHMMSS>_<motivo>/` con `instalacion.db`
(si existe: va siempre, aunque no se migre, para que la pareja restaurada sea coherente), los
casos en `casos/` y `ficha.json`: versión de Sílice, motivo, fecha y, por base, revisión de
origen y de destino, filas por tabla y SHA-256 de la copia; además, el último `evento_acceso`
de la instalación. Cada copia sale de la API de respaldo de `sqlite3` (segura con la base
abierta) y pasa `PRAGMA integrity_check`: sin juego verificado no se migra.

En la 0.6.0 la base de la instalación no tiene tablas (S3-1 las agrega): el juego y la restauración
ya la tratan, y la lista de eventos de seguridad perdidos lee `evento_acceso` (`id`, `fecha_hora`,
S3 §12) cuando existe. S3 agrega aquí las diferencias de cuentas, roles, claves y revocaciones.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tomllib
from collections.abc import Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from migraciones.comun import TABLA_VERSION, ErrorDeBase
from operacion import config

FORMATO_FICHA = 1
NOMBRE_FICHA = "ficha.json"
CARPETA_CASOS_DEL_JUEGO = "casos"
MOTIVO_MIGRACION = "migracion"
MOTIVO_MANUAL = "manual"
MOTIVO_ANTES_DE_RESTAURAR = "antes_de_restaurar"
CONSERVAR_MIGRACIONES = 5
TABLA_EVENTOS = "evento_acceso"
#: Segundos que se espera a otro proceso que tiene la base bloqueada antes de rendirse.
ESPERA_BLOQUEO_S = 5.0
_BLOQUE = 1 << 20

__all__ = ["TABLA_VERSION"]


class RespaldoFallido(ErrorDeBase):  # noqa: N818
    """No se pudo crear, verificar o restaurar un juego. Si era previo a una migración, no se migró
    nada: las bases quedan como estaban."""


@dataclass(frozen=True, slots=True)
class Restauracion:
    """Lo que hizo `restaurar`: el juego con las bases de antes, las restauradas y, si el juego
    traía la instalación, el archivo de eventos de seguridad perdidos (`revisado: false`)."""

    antes: Path
    restauradas: tuple[Path, ...]
    eventos_perdidos: Path | None


def uri_solo_lectura(ruta: Path) -> str:
    """URI `file:` de solo lectura; `as_uri` codifica espacios, tildes y `ñ` (rutas de OneDrive)."""
    return Path(ruta).resolve().as_uri() + "?mode=ro"


def abrir_solo_lectura(ruta: Path) -> sqlite3.Connection:
    return sqlite3.connect(uri_solo_lectura(ruta), uri=True, timeout=ESPERA_BLOQUEO_S)


def huella(ruta: Path) -> str:
    sha = hashlib.sha256()
    with Path(ruta).open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(_BLOQUE), b""):
            sha.update(bloque)
    return sha.hexdigest()


def tablas_de(conexion: sqlite3.Connection) -> set[str]:
    return {
        nombre
        for (nombre,) in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def revision_de(conexion: sqlite3.Connection) -> str | None:
    if TABLA_VERSION not in tablas_de(conexion):
        return None
    fila = conexion.execute(f"SELECT version_num FROM {TABLA_VERSION}").fetchone()
    return None if fila is None else str(fila[0])


def filas_por_tabla(conexion: sqlite3.Connection) -> dict[str, int]:
    return {
        tabla: conexion.execute(f'SELECT count(*) FROM "{tabla}"').fetchone()[0]
        for tabla in sorted(tablas_de(conexion))
    }


def copiar_sqlite(origen: Path, destino: Path) -> None:
    """Copia `origen` en `destino` con la API de respaldo de SQLite: segura con la base abierta por
    otro proceso y transaccional sobre el destino (un fallo no lo deja a medias)."""
    with (
        closing(abrir_solo_lectura(origen)) as fuente,
        closing(sqlite3.connect(destino, timeout=ESPERA_BLOQUEO_S)) as copia,
    ):
        fuente.backup(copia)


def verificar_integridad(ruta: Path) -> None:
    try:
        with closing(abrir_solo_lectura(ruta)) as conexion:
            resultado = [str(fila[0]) for fila in conexion.execute("PRAGMA integrity_check")]
    except sqlite3.DatabaseError as error:
        raise RespaldoFallido(f"La copia {ruta.name} no es una base legible: {error}.") from error
    if resultado != ["ok"]:
        raise RespaldoFallido(
            f"La copia {ruta.name} no pasó PRAGMA integrity_check: {'; '.join(resultado[:5])}."
        )


def ruta_en_juego(juego: Path, ruta: Path, destino: str) -> Path:
    if destino == "instalacion":
        return juego / config.NOMBRE_INSTALACION
    return juego / CARPETA_CASOS_DEL_JUEGO / Path(ruta).name


def _version_silice() -> str:
    """La versión de `pyproject.toml` (fuente única, RF-99); S5-2 la pasa a `operacion.version`."""
    with (config.RAIZ / "pyproject.toml").open("rb") as archivo:
        return str(tomllib.load(archivo)["project"]["version"])


def _escribir_json(ruta: Path, datos: Mapping[str, Any]) -> None:
    ruta.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _carpeta_nueva(padre: Path, nombre: str) -> Path:
    padre.mkdir(parents=True, exist_ok=True)
    for numero in range(1, 1000):
        carpeta = padre / (nombre if numero == 1 else f"{nombre}_{numero}")
        try:
            carpeta.mkdir()
        except FileExistsError:
            continue
        return carpeta
    raise RespaldoFallido(f"Demasiados juegos llamados {nombre} en {padre}.")


def _ultimo_evento(ruta: Path) -> dict[str, Any] | None:
    if not ruta.exists():
        return None
    with closing(abrir_solo_lectura(ruta)) as conexion:
        if TABLA_EVENTOS not in tablas_de(conexion):
            return None
        fila = conexion.execute(
            f"SELECT id, fecha_hora FROM {TABLA_EVENTOS} ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return None if fila is None else {"id": fila[0], "fecha_hora": str(fila[1])}


def _copiar_y_describir(
    origen: Path, juego: Path, destino: str, heads: Mapping[str, str | None]
) -> dict[str, Any]:
    copia = ruta_en_juego(juego, origen, destino)
    copia.parent.mkdir(parents=True, exist_ok=True)
    copiar_sqlite(origen, copia)
    verificar_integridad(copia)
    with closing(abrir_solo_lectura(copia)) as conexion:
        revision = revision_de(conexion)
        filas = filas_por_tabla(conexion)
    return {
        "archivo": copia.relative_to(juego).as_posix(),
        "origen": str(Path(origen).resolve()),
        "destino": destino,
        "revision_origen": revision,
        "revision_destino": heads.get(destino),
        "filas_por_tabla": filas,
        "sha256": huella(copia),
    }


def respaldar(
    casos: Sequence[Path],
    motivo: str,
    *,
    ruta_instalacion: Path,
    carpeta_respaldos: Path,
    heads: Mapping[str, str | None],
    ahora: datetime | None = None,
) -> Path:
    """Crea y verifica un juego con la instalación (si existe) y `casos`. `RespaldoFallido` sin
    dejar carpeta a medias (disco lleno, copia ilegible, integridad, permisos)."""
    nombres = [Path(caso).name for caso in casos]
    if len(set(nombres)) != len(nombres):
        raise RespaldoFallido(
            f"Dos casos con el mismo nombre no caben en un juego: {sorted(nombres)}."
        )
    momento = ahora or datetime.now()
    try:
        juego = _carpeta_nueva(carpeta_respaldos, f"{momento:%Y%m%d-%H%M%S}_{motivo}")
    except OSError as error:
        raise RespaldoFallido(
            f"No se pudo crear el respaldo en {carpeta_respaldos}: {error}."
        ) from error
    try:
        bases = []
        if ruta_instalacion.exists():
            bases.append(_copiar_y_describir(ruta_instalacion, juego, "instalacion", heads))
        for caso in casos:
            bases.append(_copiar_y_describir(Path(caso), juego, "caso", heads))
        _escribir_json(
            juego / NOMBRE_FICHA,
            {
                "formato": FORMATO_FICHA,
                "version_silice": _version_silice(),
                "motivo": motivo,
                "fecha": momento.isoformat(timespec="microseconds"),
                "bases": bases,
                "ultimo_evento_acceso": _ultimo_evento(juego / config.NOMBRE_INSTALACION),
            },
        )
    except RespaldoFallido:
        shutil.rmtree(juego, ignore_errors=True)
        raise
    except (OSError, sqlite3.Error) as error:
        shutil.rmtree(juego, ignore_errors=True)
        raise RespaldoFallido(
            f"No se pudo crear el respaldo en {carpeta_respaldos}: {error}. "
            "No se migró ni se cambió nada."
        ) from error
    return juego


def leer_ficha(juego: Path) -> dict[str, Any]:
    try:
        ficha = json.loads((Path(juego) / NOMBRE_FICHA).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RespaldoFallido(f"{juego} no es un juego de respaldo de Sílice: {error}.") from error
    if ficha.get("formato") != FORMATO_FICHA:
        raise RespaldoFallido(f"La ficha de {Path(juego).name} tiene un formato desconocido.")
    return ficha


def listar_juegos(carpeta_respaldos: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Los juegos legibles, del más viejo al más nuevo (por la fecha de su ficha)."""
    if not carpeta_respaldos.is_dir():
        return []
    juegos = []
    for carpeta in carpeta_respaldos.iterdir():
        if carpeta.is_dir() and (carpeta / NOMBRE_FICHA).is_file():
            try:
                juegos.append((carpeta, leer_ficha(carpeta)))
            except RespaldoFallido:
                continue
    return sorted(juegos, key=lambda par: par[1]["fecha"])


def podar_juegos(carpeta_respaldos: Path, conservar: int = CONSERVAR_MIGRACIONES) -> list[Path]:
    """Borra los juegos de migración más viejos y conserva los `conservar` últimos (al menos uno:
    nunca el más reciente). Los manuales y los de antes de restaurar no se borran (spec S5 §6.3)."""
    de_migracion = [
        carpeta
        for carpeta, ficha in listar_juegos(carpeta_respaldos)
        if ficha["motivo"] == MOTIVO_MIGRACION
    ]
    sobran = de_migracion[: -max(conservar, 1)]
    for carpeta in sobran:
        shutil.rmtree(carpeta)
    return sobran


def eventos_perdidos(actual: Path, ultimo: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Los `evento_acceso` de la instalación actual posteriores al último del juego (SEG-12)."""
    if not actual.exists():
        return []
    with closing(abrir_solo_lectura(actual)) as conexion:
        if TABLA_EVENTOS not in tablas_de(conexion):
            return []
        conexion.row_factory = sqlite3.Row
        desde = int(ultimo["id"]) if ultimo else 0
        filas = conexion.execute(
            f"SELECT * FROM {TABLA_EVENTOS} WHERE id > ? ORDER BY id", (desde,)
        ).fetchall()
    return [dict(fila) for fila in filas]


def _con_extension(nombre: str) -> str:
    return nombre if nombre.lower().endswith(".db") else f"{nombre}.db"


def restaurar(
    juego: Path,
    *,
    ruta_instalacion: Path,
    carpeta_casos: Path,
    carpeta_datos: Path,
    carpeta_respaldos: Path,
    heads: Mapping[str, str | None],
    conocidas: Mapping[str, frozenset[str]],
    solo_caso: str | None = None,
    ahora: datetime | None = None,
) -> Restauracion:
    """Restaura un juego (spec S5 §6.5). Rechaza, sin tocar nada, un juego alterado (huella distinta
    de la ficha), ilegible o de una versión más nueva. Antes guarda las bases actuales como juego
    `antes_de_restaurar`. Si el juego trae la instalación, escribe en la carpeta de datos
    `eventos_perdidos_<fecha>.json` con `revisado: false`. Exige Sílice detenido: hasta que el
    lanzador (S5-2) deje `estado/servidor.json`, lo comprueba quien ejecuta la orden."""
    juego = Path(juego)
    ficha = leer_ficha(juego)
    elegidas = [
        base
        for base in ficha["bases"]
        if solo_caso is None
        or (base["destino"] == "caso" and Path(base["archivo"]).name == _con_extension(solo_caso))
    ]
    if not elegidas:
        raise RespaldoFallido(f"El juego {juego.name} no trae {solo_caso or 'ninguna base'}.")
    for base in elegidas:
        copia = juego / base["archivo"]
        if not copia.is_file() or huella(copia) != base["sha256"]:
            raise RespaldoFallido(
                f"La copia {base['archivo']} del juego {juego.name} falta o fue alterada (su "
                "huella no es la de la ficha). No se restauró nada."
            )
        verificar_integridad(copia)
        origen = base["revision_origen"]
        if origen is not None and origen not in conocidas[base["destino"]]:
            raise RespaldoFallido(
                f"El juego {juego.name} es de una versión más nueva de Sílice (revisión {origen}). "
                "Instale esa versión para restaurarlo."
            )
    destinos = {
        base["archivo"]: ruta_instalacion
        if base["destino"] == "instalacion"
        else carpeta_casos / Path(base["archivo"]).name
        for base in elegidas
    }
    momento = ahora or datetime.now()
    actuales = [
        destinos[base["archivo"]]
        for base in elegidas
        if base["destino"] == "caso" and destinos[base["archivo"]].exists()
    ]
    antes = respaldar(
        actuales,
        MOTIVO_ANTES_DE_RESTAURAR,
        ruta_instalacion=ruta_instalacion,
        carpeta_respaldos=carpeta_respaldos,
        heads=heads,
        ahora=momento,
    )
    perdidos = None
    if any(base["destino"] == "instalacion" for base in elegidas):
        carpeta_datos.mkdir(parents=True, exist_ok=True)
        perdidos = carpeta_datos / f"eventos_perdidos_{momento:%Y%m%d-%H%M%S}.json"
        _escribir_json(
            perdidos,
            {
                "juego": str(juego),
                "fecha": momento.isoformat(timespec="seconds"),
                "revisado": False,
                "eventos": eventos_perdidos(ruta_instalacion, ficha.get("ultimo_evento_acceso")),
            },
        )
    restauradas = []
    for base in elegidas:
        destino = destinos[base["archivo"]]
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:
            copiar_sqlite(juego / base["archivo"], destino)
        except sqlite3.Error as error:
            raise RespaldoFallido(
                f"No se pudo restaurar {destino.name}: {error}. Cierre Sílice y reintente; "
                f"las bases de antes están en {antes}."
            ) from error
        restauradas.append(destino)
    return Restauracion(antes=antes, restauradas=tuple(restauradas), eventos_perdidos=perdidos)
