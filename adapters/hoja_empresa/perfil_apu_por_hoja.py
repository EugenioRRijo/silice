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

**Libro por frentes** (ola 2, línea 3, 2026-11-13; decisiones simuladas en
`docs/bitacora/2026-11-13-ola2-libro-por-frentes.md`): el presupuesto puede declarar varias hojas
(`presupuesto.hojas`, una por frente) en vez de una (`presupuesto.hoja`); `porcentajes` admite
`otros_impuestos`, una segunda fila de impuesto que el lector suma al impuesto; e
`instalar_perfil_apu_por_hoja` pone un perfil local desde la interfaz (lo valida entero antes de
escribirlo y no pisa uno que ya está sin `reemplazar`).
"""

from __future__ import annotations

import json
import os
import re
import re._parser as _sre  # el árbol de la expresión (patron_banda)
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from adapters.hoja_empresa.perfil import PerfilInvalido, normalizar

__all__ = [
    "BLOQUES",
    "VARIABLE_PERFILES",
    "Bloque",
    "PerfilApuPorHoja",
    "PerfilDisponible",
    "PerfilYaInstalado",
    "MAX_BYTES_PERFIL",
    "cargar_perfil_apu_por_hoja",
    "carpetas_locales",
    "instalar_perfil_apu_por_hoja",
    "perfiles_apu_por_hoja",
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
#: Una segunda fila de impuesto («Otros impuestos»), opcional: el lector la suma al impuesto.
_PORCENTAJES_OPCIONALES = ("otros_impuestos",)
#: SUPUESTO_DECLARADO: lo más que pesa un perfil que se pone desde la interfaz. El del paquete pesa
#: unos 2 KiB; 64 KiB caben treinta veces y atajan un archivo que no es un perfil.
MAX_BYTES_PERFIL = 64 * 1024
#: Largo máximo de `patron_banda` (ronda 1 del árbitro de la ola 2, hallazgo 4): el del paquete
#: tiene 104 caracteres.
MAX_PATRON_BANDA = 300
#: De qué lado de su rótulo escribe el libro cada porcentaje del pie: «derecha» (el primer número a
#: la derecha, como el libro ficticio) o «izquierda» (el más cercano a la izquierda: «p |
#: Administración (%) | … | monto», prueba local del libro vial real del 2026-11-13).
LADOS_DE_LOS_PORCENTAJES = ("derecha", "izquierda")
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
    lado_de_los_porcentajes: str = "derecha"
    origen: str = "paquete"
    #: Todas las hojas del presupuesto, una por frente; `hoja_presupuesto` es la primera.
    hojas_presupuesto: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PerfilDisponible:
    """Un perfil que se puede elegir (E2E-2): su nombre, de dónde viene y qué hoja del presupuesto
    lee; si está mal escrito, `hoja_presupuesto` es `None` y `motivo` dice por qué (el mensaje de
    `PerfilInvalido`, que nombra el perfil y nunca una ruta del disco)."""

    nombre: str
    origen: str
    hoja_presupuesto: str | None
    motivo: str | None = None
    hojas_presupuesto: tuple[str, ...] = ()


class PerfilYaInstalado(Exception):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """Ya hay un perfil local con ese nombre y no se pidió reemplazarlo; el mensaje es el que ve
    la persona."""


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
        if len(_texto(nombre, patron, "patron_banda")) > MAX_PATRON_BANDA:
            raise _error(nombre, f"patron_banda: pasa de {MAX_PATRON_BANDA} caracteres")
        try:
            compilado = re.compile(patron)
            peligro = _retroceso_catastrofico(_sre.parse(patron))
        except re.error as exc:
            raise _error(nombre, f"patron_banda no compila: {exc}") from exc
        if peligro is not None:
            raise _error(
                nombre,
                f"patron_banda: {peligro} puede tardar sin fin con algunos textos; "
                "escríbalo sin ella",
            )
        if not {"minimo", "maximo"} <= set(compilado.groupindex):
            raise _error(nombre, "patron_banda debe tener los grupos «minimo» y «maximo»")
    presupuesto = _dic(nombre, raiz.get("presupuesto"), "presupuesto")
    hojas = _hojas_presupuesto(nombre, presupuesto)
    lado = raiz.get("lado_de_los_porcentajes", "derecha")
    if not isinstance(lado, str) or lado not in LADOS_DE_LOS_PORCENTAJES:
        raise _error(
            nombre,
            "lado_de_los_porcentajes debe ser «derecha» o «izquierda» (de qué lado del "
            "rótulo está cada porcentaje del pie)",
        )
    return PerfilApuPorHoja(
        nombre=declarado,
        prefijo_hoja=_texto(nombre, raiz.get("prefijo_hoja"), "prefijo_hoja"),
        cabecera=_variantes(nombre, raiz.get("cabecera"), _CABECERA, (), "cabecera"),
        bloques=MappingProxyType(bloques),
        porcentajes=_variantes(
            nombre, raiz.get("porcentajes"), _PORCENTAJES, _PORCENTAJES_OPCIONALES, "porcentajes"
        ),
        precio_unitario=_textos(nombre, raiz.get("precio_unitario"), "precio_unitario"),
        unidades=MappingProxyType({str(k): v.strip() for k, v in unidades.items()}),
        patron_banda=patron,
        hoja_presupuesto=hojas[0],
        encabezado_presupuesto=_variantes(
            nombre, presupuesto.get("encabezado"), _PRESUPUESTO, (), "presupuesto.encabezado"
        ),
        lado_de_los_porcentajes=lado,
        origen=origen,
        hojas_presupuesto=hojas,
    )


_REPETICIONES = {_sre.MAX_REPEAT, _sre.MIN_REPEAT, getattr(_sre, "POSSESSIVE_REPEAT", None)}


def _retroceso_catastrofico(items: Any, en_repeticion: bool = False) -> str | None:
    """Qué de la expresión (su árbol, `re._parser`) puede hacer que `re` retroceda sin fin
    (ronda 1 del árbitro de la ola 2, hallazgo 4; simulación en su sección «Ronda 1:
    correcciones»), o `None`: una repetición de más de una vez dentro de otra («(a+)+»), una
    alternativa dentro de una repetición («(a|aa)+»: dos caminos para el mismo texto) o una
    referencia hacia atrás. `re` no tiene tiempo máximo y el módulo `regex` no es dependencia
    de Sílice: se rechaza la forma, no se mide."""
    for op, av in items:
        if op in (_sre.GROUPREF, _sre.GROUPREF_EXISTS):
            return "una referencia hacia atrás"
        if op in _REPETICIONES:
            _minimo, maximo, sub = av
            varias = maximo > 1  # MAXREPEAT, sin tope, también
            if en_repeticion and varias:
                return "una repetición dentro de otra"
            hallado = _retroceso_catastrofico(sub, en_repeticion or varias)
        elif op == _sre.SUBPATTERN:
            hallado = _retroceso_catastrofico(av[-1], en_repeticion)
        elif op == _sre.BRANCH:
            if en_repeticion:
                return "una alternativa dentro de una repetición"
            hallado = next(
                (h for rama in av[1] if (h := _retroceso_catastrofico(rama)) is not None), None
            )
        elif op in (_sre.ASSERT, _sre.ASSERT_NOT):
            hallado = _retroceso_catastrofico(av[1], en_repeticion)
        elif op == getattr(_sre, "ATOMIC_GROUP", None):
            hallado = _retroceso_catastrofico(av, en_repeticion)
        else:
            hallado = None
        if hallado is not None:
            return hallado
    return None


def _hojas_presupuesto(nombre: str, presupuesto: dict[str, Any]) -> tuple[str, ...]:
    """`presupuesto.hoja` (una) o `presupuesto.hojas` (una por frente), nunca las dos; sin
    repetir una hoja (se comparan como el lector, con `normalizar`)."""
    if "hoja" in presupuesto and "hojas" in presupuesto:
        raise _error(nombre, "presupuesto: declare «hoja» o «hojas», no las dos")
    if "hojas" in presupuesto:
        hojas = _textos(nombre, presupuesto["hojas"], "presupuesto.hojas")
    elif "hoja" in presupuesto:
        hojas = (_texto(nombre, presupuesto["hoja"], "presupuesto.hoja"),)
    else:
        raise _error(nombre, "presupuesto: falta «hoja» u «hojas»")
    vistas: set[str] = set()
    for hoja in hojas:
        if normalizar(hoja) in vistas:
            raise _error(nombre, f"presupuesto.hojas: la hoja «{hoja}» está repetida")
        vistas.add(normalizar(hoja))
    return hojas


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
            origen = "paquete" if Path(carpeta) == _DIR_PERFILES else "local"
            return _construir(nombre, _leer_json(nombre, ruta), origen)
    raise PerfilInvalido(f"no existe el perfil {nombre!r}")


def _leer_json(nombre: str, ruta: Path) -> Any:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _error(nombre, f"JSON mal formado: {exc}") from exc


def perfiles_apu_por_hoja(carpetas: Sequence[Path] | None = None) -> tuple[PerfilDisponible, ...]:
    """Los perfiles de libro con un APU por hoja que se pueden elegir (E2E-2): los de `carpetas`
    (por omisión, la carpeta local de la instalación) y los del paquete, con la misma precedencia
    que `cargar_perfil_apu_por_hoja` (uno local reemplaza al del paquete con su nombre). Un JSON de
    otro tipo de perfil (sin `"tipo": "apu_por_hoja"`, como el de la plantilla conocida) no sale;
    uno local que no se puede usar sale con su `motivo`. Primero los válidos y después los demás,
    cada grupo por nombre."""
    vistos: dict[str, PerfilDisponible] = {}
    for carpeta in [*(carpetas_locales() if carpetas is None else carpetas), _DIR_PERFILES]:
        origen = "paquete" if Path(carpeta) == _DIR_PERFILES else "local"
        for ruta in sorted(Path(carpeta).glob("*.json")):
            nombre = ruta.stem
            if nombre in vistos or not ruta.is_file():
                continue
            try:
                if not _NOMBRE.fullmatch(nombre):
                    raise PerfilInvalido(f"nombre de perfil no válido: {nombre!r}")
                crudo = _leer_json(nombre, ruta)
                if not isinstance(crudo, dict) or crudo.get("tipo") != "apu_por_hoja":
                    continue  # otro tipo de perfil: no es de esta pantalla
                perfil = _construir(nombre, crudo, origen)
            except PerfilInvalido as exc:
                vistos[nombre] = PerfilDisponible(nombre, origen, None, str(exc))
                continue
            vistos[nombre] = _disponible(perfil)
    return tuple(sorted(vistos.values(), key=lambda p: (p.motivo is not None, p.nombre.casefold())))


def _disponible(perfil: PerfilApuPorHoja) -> PerfilDisponible:
    return PerfilDisponible(
        perfil.nombre,
        perfil.origen,
        perfil.hoja_presupuesto,
        hojas_presupuesto=perfil.hojas_presupuesto,
    )


def _carpeta_de_escritura(por_omision: Path) -> Path:
    """Donde se escribe un perfil local: la de `SILICE_PERFILES_LIBROS` si está (la misma que se
    lee), si no `por_omision` (la de la carpeta de datos, que pasa la API)."""
    valor = os.environ.get(VARIABLE_PERFILES, "").strip()
    return Path(valor) if valor else por_omision


def instalar_perfil_apu_por_hoja(
    datos: bytes, por_omision: Path, *, reemplazar: bool = False
) -> PerfilDisponible:
    """Pone el perfil `datos` (el JSON de un perfil `apu_por_hoja`) en la carpeta de perfiles
    locales y lo devuelve como se elige (libro por frentes, D5).

    Antes de escribir nada lo valida entero, con las mismas reglas que al cargarlo:
    `PerfilInvalido` si pasa de `MAX_BYTES_PERFIL`, si no es un JSON en UTF-8, si su nombre no es
    válido (minúsculas, cifras y «_»: el nombre del archivo sale de ahí, nunca de una ruta) o si no
    describe un libro con un APU por hoja. `PerfilYaInstalado` si ya hay uno local con ese nombre y
    no se pide `reemplazar`. Se escribe el archivo tal como llegó, primero en un temporal y luego
    en su sitio (`os.replace`): no queda un perfil a medias."""
    if len(datos) > MAX_BYTES_PERFIL:
        raise PerfilInvalido(
            f"El perfil pasa de {MAX_BYTES_PERFIL // 1024} KiB: no parece un perfil de libro."
        )
    try:
        crudo = json.loads(datos.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PerfilInvalido(f"El archivo no es un JSON legible: {exc}") from exc
    if not isinstance(crudo, dict):
        raise _error("?", "la raíz debe ser un objeto")
    nombre = crudo.get("nombre")
    if not isinstance(nombre, str) or not _NOMBRE.fullmatch(nombre):
        raise PerfilInvalido(f"nombre de perfil no válido: {nombre!r}")
    perfil = _construir(nombre, crudo, "local")
    carpeta = _carpeta_de_escritura(por_omision)
    destino = carpeta / f"{nombre}.json"
    if destino.exists() and not reemplazar:
        raise PerfilYaInstalado(
            f"Ya hay un perfil «{nombre}» en esta instalación: marque «Reemplazar» para cambiarlo."
        )
    carpeta.mkdir(parents=True, exist_ok=True)
    temporal = carpeta / f".{nombre}.json.tmp"
    temporal.write_bytes(datos)
    os.replace(temporal, destino)
    return _disponible(perfil)
