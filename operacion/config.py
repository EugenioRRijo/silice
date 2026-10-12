"""Dónde viven los datos de Sílice (maestro §4.2; spec S5 §5.3).

En el producto, el lanzador (S5-2) fija `SILICE_DATOS` (`%LOCALAPPDATA%\\Silice\\datos`),
`SILICE_INSTALACION` y `SILICE_RESPALDOS` (`%LOCALAPPDATA%\\Silice\\respaldos`). En desarrollo,
`SILICE_DATOS` vale por defecto `data/` del repositorio, con la misma disposición: `instalacion.db`,
`casos/`, `paquetes/`, `codigo_instalacion.txt` y `respaldos/` (todos en `.gitignore`).

Las funciones reciben el entorno para que las pruebas no dependan de `os.environ`, y **ninguna crea
carpetas**: las crea quien escribe.
"""

from __future__ import annotations

import ipaddress
import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

VARIABLE_DATOS = "SILICE_DATOS"
VARIABLE_INSTALACION = "SILICE_INSTALACION"
VARIABLE_RESPALDOS = "SILICE_RESPALDOS"

RAIZ = Path(__file__).resolve().parents[1]
DATOS_DESARROLLO = RAIZ / "data"
NOMBRE_INSTALACION = "instalacion.db"
CARPETA_CASOS = "casos"
CARPETA_RESPALDOS = "respaldos"
CASO_POR_DEFECTO = "silice.db"
#: La base de trabajo de las versiones 0.1 a 0.5 (`scripts/seed.py`, `ui/caso.py`, `api`). No se
#: abre en su sitio: se adopta COPIÁNDOLA a la carpeta de casos con `python -m operacion adoptar`.
BASE_ANTERIOR = DATOS_DESARROLLO / "apu.db"


def _valor(nombre: str, entorno: Mapping[str, str] | None) -> str:
    fuente = os.environ if entorno is None else entorno
    return fuente.get(nombre, "").strip()


def _ruta(valor: str) -> Path:
    return Path(valor).expanduser().resolve()


def carpeta_datos(entorno: Mapping[str, str] | None = None) -> Path:
    """`SILICE_DATOS`; si no, `<usuario>/datos` en el producto y `data/` en desarrollo."""
    valor = _valor(VARIABLE_DATOS, entorno)
    if valor:
        return _ruta(valor)
    return carpeta_usuario(entorno) / "datos" if es_producto() else DATOS_DESARROLLO


def carpeta_casos(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_datos(entorno) / CARPETA_CASOS


def ruta_instalacion(entorno: Mapping[str, str] | None = None) -> Path:
    """`SILICE_INSTALACION` si está; si no, `instalacion.db` de la carpeta de datos."""
    valor = _valor(VARIABLE_INSTALACION, entorno)
    return _ruta(valor) if valor else carpeta_datos(entorno) / NOMBRE_INSTALACION


def carpeta_respaldos(entorno: Mapping[str, str] | None = None) -> Path:
    """`SILICE_RESPALDOS`; si no, `<usuario>/respaldos` en el producto y `<datos>/respaldos`."""
    valor = _valor(VARIABLE_RESPALDOS, entorno)
    if valor:
        return _ruta(valor)
    if es_producto():
        return carpeta_usuario(entorno) / CARPETA_RESPALDOS
    return carpeta_datos(entorno) / CARPETA_RESPALDOS


def ruta_caso_por_defecto(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_casos(entorno) / CASO_POR_DEFECTO


VARIABLE_USUARIO = "SILICE_USUARIO"
NIVELES_DE_REGISTRO = ("DEBUG", "INFO", "WARNING", "ERROR")
PUERTO_STREAMLIT = 8501
PUERTO_API = 8000


def es_producto(raiz: Path | None = None) -> bool:
    """El instalador deja `manifiesto.json` junto a `codigo/`: eso distingue el producto de un
    árbol de desarrollo (spec S5 §5.3)."""
    return ((raiz or RAIZ).parent / "manifiesto.json").is_file()


def carpeta_usuario(entorno: Mapping[str, str] | None = None) -> Path:
    """Donde viven `config/`, `registros/` y `estado/`: `SILICE_USUARIO`; en el producto
    `%LOCALAPPDATA%\\Silice`; en desarrollo, `data/`."""
    valor = _valor(VARIABLE_USUARIO, entorno)
    if valor:
        return _ruta(valor)
    if es_producto():
        local = _valor("LOCALAPPDATA", entorno) or str(Path.home() / "AppData" / "Local")
        return _ruta(local) / "Silice"
    return DATOS_DESARROLLO


def ruta_ajustes(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_usuario(entorno) / "config" / "silice.toml"


def carpeta_registros(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_usuario(entorno) / "registros"


def ruta_estado(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_usuario(entorno) / "estado" / "servidor.json"


def ruta_codigo_instalacion(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_datos(entorno) / "codigo_instalacion.txt"


@dataclass(frozen=True, slots=True)
class Ajustes:
    """El contenido de `silice.toml` ya validado (spec S5 §8.1). Todo lo dudoso cae al valor
    por defecto, que tiene la red local y la API apagadas."""

    puerto: int = PUERTO_STREAMLIT
    red_local: bool = False
    direccion: str = ""
    api_activa: bool = False
    puerto_api: int = PUERTO_API
    mostrar_investigacion: bool = False
    nivel_registro: str = "INFO"
    avisos: tuple[str, ...] = ()


def _direccion_valida(texto: str) -> bool:
    try:
        ip = ipaddress.ip_address(texto)
    except ValueError:
        return False
    return ip.version == 4 and ip.is_private and not (ip.is_unspecified or ip.is_multicast)


def _puerto(valor: object, defecto: int, nombre: str, avisos: list[str]) -> int:
    if isinstance(valor, int) and not isinstance(valor, bool) and 1024 <= valor <= 65535:
        return valor
    if valor is not None:
        avisos.append(f"El puerto de {nombre} no es válido ({valor!r}); se usa {defecto}.")
    return defecto


def _booleano(valor: object, nombre: str, avisos: list[str]) -> bool:
    if isinstance(valor, bool):
        return valor
    if valor is not None:
        avisos.append(f"«{nombre}» debe ser true o false ({valor!r}); se usa false.")
    return False


def _tabla(datos: dict, nombre: str) -> dict:
    tabla = datos.get(nombre, {})
    return tabla if isinstance(tabla, dict) else {}


def cargar_ajustes(ruta: Path) -> Ajustes:
    """Lee `silice.toml`. Falta → valores por defecto. Dañado → valores por defecto y un aviso:
    nunca la red encendida."""
    if not ruta.exists():
        return Ajustes()
    try:
        datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        return Ajustes(
            avisos=(
                f"No se pudo leer {ruta.name} ({type(error).__name__}); se usan los valores por "
                "defecto: red local apagada y API apagada.",
            )
        )
    avisos: list[str] = []
    servidor, api = _tabla(datos, "servidor"), _tabla(datos, "api")
    interfaz, reg = _tabla(datos, "interfaz"), _tabla(datos, "registro")
    puerto = _puerto(servidor.get("puerto"), PUERTO_STREAMLIT, "la interfaz", avisos)
    puerto_api = _puerto(api.get("puerto"), PUERTO_API, "la API", avisos)
    if puerto_api == puerto:
        avisos.append("La interfaz y la API no pueden usar el mismo puerto; la API vuelve a 8000.")
        puerto_api = PUERTO_API
    red_local = _booleano(servidor.get("red_local"), "red_local", avisos)
    direccion = servidor.get("direccion", "")
    if red_local and not (isinstance(direccion, str) and _direccion_valida(direccion)):
        avisos.append(
            f"La dirección de la red local ({direccion!r}) no es una IP privada IPv4; la red local "
            "queda apagada."
        )
        red_local, direccion = False, ""
    nivel = str(reg.get("nivel", "INFO")).upper()
    if nivel not in NIVELES_DE_REGISTRO:
        avisos.append(f"El nivel de registro {nivel!r} no existe; se usa INFO.")
        nivel = "INFO"
    return Ajustes(
        puerto=puerto,
        red_local=red_local,
        direccion=direccion if red_local else "",
        api_activa=_booleano(api.get("activa"), "api.activa", avisos),
        puerto_api=puerto_api,
        mostrar_investigacion=_booleano(
            interfaz.get("mostrar_investigacion"), "mostrar_investigacion", avisos
        ),
        nivel_registro=nivel,
        avisos=tuple(avisos),
    )


def guardar_ajustes(ruta: Path, ajustes: Ajustes) -> None:
    """Escribe `silice.toml` completo y con comentarios, de golpe (archivo temporal + reemplazo)."""
    texto = (
        "[servidor]\n"
        f"puerto = {ajustes.puerto}\n"
        f"red_local = {str(ajustes.red_local).lower()}        # true: escucha en la IP de abajo\n"
        f'direccion = "{ajustes.direccion}"         # IP de la interfaz elegida; nunca 0.0.0.0\n'
        "[api]\n"
        f"activa = {str(ajustes.api_activa).lower()}\n"
        f"puerto = {ajustes.puerto_api}\n"
        "[interfaz]\n"
        f"mostrar_investigacion = {str(ajustes.mostrar_investigacion).lower()}"
        "   # false = modo entrega (RS5-9)\n"
        "[registro]\n"
        f'nivel = "{ajustes.nivel_registro}"\n'
    )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(texto, encoding="utf-8", newline="\n")
    temporal.replace(ruta)
