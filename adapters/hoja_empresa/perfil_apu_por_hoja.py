"""Perfil hermano `apu_por_hoja`: un libro con un APU por hoja y solo valores (F5 vial, tarea 4).

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §7 (opción B). Es otro
tipo de perfil, no una extensión del de la plantilla conocida (`perfil.py`, 12 hojas y un bloque de
líneas): aquí cada hoja cuyo nombre empieza por `prefijo_hoja` es un APU con su cabecera, tres
bloques con columnas distintas (materiales con desperdicio, equipos con coeficiente, mano de obra
con jornal y bono) y un pie de porcentajes en cascada. Todo se busca por **rótulos**, nunca por
fila fija, y se compara con `perfil.normalizar` (sin mayúsculas, NBSP como espacio): por prefijo,
salvo el título de cada bloque, que debe ser la celda entera (así «MANO DE OBRA» no confunde la fila
«Mano de obra por unidad»).

El perfil también declara la **traducción de unidades** del libro («lo que el libro escribe → la
unidad de Sílice», para lo que no es un alias general del núcleo) y el **patrón de la banda** de
distancia del transporte (grupos `minimo` y `maximo`, coma decimal), que usa la auditoría del libro
(tarea 5).

**Perfiles locales** (decisión provisional 5 del 2026-11-06): el perfil del repositorio se escribe
contra el libro ficticio de `tests/fixtures/libro_apu_por_hoja.py`; el de un libro real vive en la
carpeta de datos de la instalación, fuera del repositorio. `cargar_perfil_apu_por_hoja` busca
primero en `carpetas` (por omisión, `carpetas_locales()`) y después en el paquete.

Este adaptador no sabe dónde está la carpeta de datos (no importa `operacion`): la API la toma de
`operacion.config.carpeta_perfiles_libros()` (`<carpeta de datos>/perfiles_libros/`) y se la pasa
a quien audita (`fusion.apu_por_hoja`), que la entrega a `carpetas_locales(por_omision=...)`.
`SILICE_PERFILES_LIBROS`, si está, la reemplaza (arbitraje F5 vial, P2; `docs/manual_tecnico.md`,
«Perfiles de libros locales»).
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from adapters.hoja_empresa.perfil import PerfilInvalido

__all__ = [
    "BLOQUES",
    "VARIABLE_PERFILES",
    "Bloque",
    "PerfilApuPorHoja",
    "cargar_perfil_apu_por_hoja",
    "carpetas_locales",
]

_DIR_PERFILES = Path(__file__).parent / "perfiles"
_NOMBRE = re.compile(r"[a-z0-9_]+")
#: La variable de entorno con otra carpeta de perfiles locales (fuera del repositorio). Es una
#: opción: nadie la fija por omisión y, si está, reemplaza la carpeta por omisión que recibe
#: `carpetas_locales` (la de la carpeta de datos de la instalación).
VARIABLE_PERFILES = "SILICE_PERFILES_LIBROS"

BLOQUES = ("materiales", "equipos", "mano_obra")
_CABECERA = ("numero", "codigo", "descripcion", "unidad", "cantidad", "rendimiento")
_PORCENTAJES = ("prestaciones", "administracion", "utilidad", "financiamiento", "impuesto")
_COLUMNAS_OBLIGATORIAS = ("descripcion", "cantidad", "precio")
_COLUMNAS_OPCIONALES = {
    "materiales": ("numero", "unidad", "desperdicio"),
    "equipos": ("numero", "depreciacion"),
    "mano_obra": ("numero", "bono"),
}
_PRESUPUESTO = ("numero", "codigo", "descripcion", "unidad", "cantidad", "precio_unitario")


@dataclass(frozen=True, slots=True)
class Bloque:
    """Un bloque de líneas de la hoja: su título (celda entera), sus columnas por encabezado y el
    rótulo de la fila que lo cierra."""

    titulo: tuple[str, ...]
    columnas: Mapping[str, tuple[str, ...]]
    fin: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PerfilApuPorHoja:
    """El libro con un APU por hoja descrito por rótulos (ver la cabecera del módulo)."""

    nombre: str
    prefijo_hoja: str
    cabecera: Mapping[str, tuple[str, ...]]
    bloques: Mapping[str, Bloque]
    porcentajes: Mapping[str, tuple[str, ...]]
    precio_unitario: tuple[str, ...]
    unidades: Mapping[str, str]
    patron_banda: str | None
    hoja_presupuesto: str
    encabezado_presupuesto: Mapping[str, tuple[str, ...]]
    origen: str = "paquete"


def _error(nombre: str, msg: str) -> PerfilInvalido:
    return PerfilInvalido(f"perfil {nombre!r}: {msg}")


def _dic(nombre: str, d: Any, donde: str) -> dict[str, Any]:
    if not isinstance(d, dict):
        raise _error(nombre, f"{donde} debe ser un objeto")
    return d


def _texto(nombre: str, v: Any, donde: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise _error(nombre, f"{donde} debe ser un texto no vacío")
    return v


def _textos(nombre: str, v: Any, donde: str) -> tuple[str, ...]:
    if not isinstance(v, list) or not v:
        raise _error(nombre, f"{donde} debe ser una lista no vacía de textos")
    return tuple(_texto(nombre, x, donde) for x in v)


def _variantes(
    nombre: str, d: Any, obligatorias: Sequence[str], opcionales: Sequence[str], donde: str
) -> Mapping[str, tuple[str, ...]]:
    d = _dic(nombre, d, donde)
    faltan = [k for k in obligatorias if k not in d]
    if faltan:
        raise _error(nombre, f"{donde}: faltan {faltan}")
    sobran = [k for k in d if k not in (*obligatorias, *opcionales)]
    if sobran:
        raise _error(nombre, f"{donde}: no se conocen {sobran}")
    return MappingProxyType({k: _textos(nombre, v, f"{donde}.{k}") for k, v in d.items()})


def _construir(nombre: str, crudo: Any, origen: str) -> PerfilApuPorHoja:
    raiz = _dic(nombre, crudo, "la raíz")
    declarado = _texto(nombre, raiz.get("nombre"), "nombre")
    if declarado != nombre:
        raise _error(nombre, f"nombre {declarado!r} no coincide con el del archivo ({nombre}.json)")
    if raiz.get("tipo") != "apu_por_hoja":
        raise _error(nombre, "tipo debe ser «apu_por_hoja»")
    bloques_crudos = _dic(nombre, raiz.get("bloques"), "bloques")
    faltan = [b for b in BLOQUES if b not in bloques_crudos]
    if faltan:
        raise _error(nombre, f"bloques: faltan {faltan}")
    bloques = {}
    for b in BLOQUES:
        d = _dic(nombre, bloques_crudos[b], f"bloques.{b}")
        bloques[b] = Bloque(
            titulo=_textos(nombre, d.get("titulo"), f"bloques.{b}.titulo"),
            columnas=_variantes(
                nombre,
                d.get("columnas"),
                _COLUMNAS_OBLIGATORIAS,
                _COLUMNAS_OPCIONALES[b],
                f"bloques.{b}.columnas",
            ),
            fin=_textos(nombre, d.get("fin"), f"bloques.{b}.fin"),
        )
    unidades = _dic(nombre, raiz.get("unidades", {}), "unidades")
    for de, a in unidades.items():
        if not isinstance(a, str) or not a.strip() or not str(de).strip():
            raise _error(nombre, f"unidades.{de}: debe traducirse a una unidad no vacía")
    patron = raiz.get("patron_banda")
    if patron is not None:
        try:
            compilado = re.compile(_texto(nombre, patron, "patron_banda"))
        except re.error as exc:
            raise _error(nombre, f"patron_banda no compila: {exc}") from exc
        if not {"minimo", "maximo"} <= set(compilado.groupindex):
            raise _error(nombre, "patron_banda debe tener los grupos «minimo» y «maximo»")
    presupuesto = _dic(nombre, raiz.get("presupuesto"), "presupuesto")
    return PerfilApuPorHoja(
        nombre=declarado,
        prefijo_hoja=_texto(nombre, raiz.get("prefijo_hoja"), "prefijo_hoja"),
        cabecera=_variantes(nombre, raiz.get("cabecera"), _CABECERA, (), "cabecera"),
        bloques=MappingProxyType(bloques),
        porcentajes=_variantes(nombre, raiz.get("porcentajes"), _PORCENTAJES, (), "porcentajes"),
        precio_unitario=_textos(nombre, raiz.get("precio_unitario"), "precio_unitario"),
        unidades=MappingProxyType({str(k): v.strip() for k, v in unidades.items()}),
        patron_banda=patron,
        hoja_presupuesto=_texto(nombre, presupuesto.get("hoja"), "presupuesto.hoja"),
        encabezado_presupuesto=_variantes(
            nombre, presupuesto.get("encabezado"), _PRESUPUESTO, (), "presupuesto.encabezado"
        ),
        origen=origen,
    )


def carpetas_locales(por_omision: Path | None = None) -> tuple[Path, ...]:
    """La carpeta de perfiles locales de la instalación, si existe: `SILICE_PERFILES_LIBROS` si
    está; si no, `por_omision` (la de la carpeta de datos, que pasa quien audita)."""
    valor = os.environ.get(VARIABLE_PERFILES, "").strip()
    carpeta = Path(valor) if valor else por_omision
    return (carpeta,) if carpeta is not None and carpeta.is_dir() else ()


def cargar_perfil_apu_por_hoja(
    nombre: str = "apu_por_hoja", carpetas: Sequence[Path] | None = None
) -> PerfilApuPorHoja:
    """Carga y valida `<nombre>.json`: primero en `carpetas` (por omisión, la carpeta local de la
    instalación), después en el paquete. `PerfilInvalido` si el nombre no es válido, si no existe
    o si el JSON no describe un libro con un APU por hoja."""
    if not _NOMBRE.fullmatch(nombre):
        raise PerfilInvalido(f"nombre de perfil no válido: {nombre!r}")
    buscadas = [*(carpetas_locales() if carpetas is None else carpetas), _DIR_PERFILES]
    for carpeta in buscadas:
        ruta = Path(carpeta) / f"{nombre}.json"
        if ruta.is_file():
            try:
                crudo = json.loads(ruta.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise _error(nombre, f"JSON mal formado: {exc}") from exc
            origen = "paquete" if Path(carpeta) == _DIR_PERFILES else "local"
            return _construir(nombre, crudo, origen)
    raise PerfilInvalido(f"no existe el perfil {nombre!r}")
