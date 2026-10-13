"""Perfil de una plantilla de libro de la empresa: dónde está cada cosa, dicho con rótulos.

El lector nunca busca por fila fija (causa C1 del análisis de causas raíz: los APU tienen más de
diez formas, de 41 a 81 filas). Lo que sí es fijo en la plantilla son los **rótulos** ("PRECIO
UNITARIO TOTAL", "FCAS × Rendimiento"…), las **columnas** en que la plantilla pone cada valor y los
**nombres definidos** (`FCAS`, `SUBSINIVA`…). Este módulo carga esa descripción desde un JSON del
paquete (`perfiles/<nombre>.json`) y la valida al cargar, para que un perfil mal escrito falle aquí
y no a mitad de una lectura.

Los rótulos se comparan con `normalizar` (sin distinguir mayúsculas, con NBSP como espacio y los
espacios repetidos colapsados) y por **prefijo**: "Materiales (USD/u)" encuentra la fila del resumen
pero no "SUBTOTAL MATERIALES (USD/u)", que empieza distinto.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any

from adapters.hoja_empresa.modelo import Rotulo, TipoFilaEspecial

__all__ = [
    "AnclaRotulo",
    "Perfil",
    "PerfilInvalido",
    "cargar_perfil",
    "coincide",
    "normalizar",
]

_DIR_PERFILES = Path(__file__).parent / "perfiles"
_COLUMNA = re.compile(r"^[A-Z]{1,3}$")
_CELDA = re.compile(r"^[A-Z]{1,3}[1-9]\d*$")
_HEX = re.compile(r"^[0-9A-F]{6}$")
_NOMBRE = re.compile(r"^[a-z0-9_]+$")

_HOJAS = (
    "PORTADA",
    "MEDICIONES",
    "PRESUPUESTO",
    "INSUMOS",
    "RESUMEN",
    "CRONOGRAMA",
    "CONTROL DE OBRA",
    "PLAN DE PAGOS",
    "PROCURA",
    "GASTOS",
    "CONTROL DE GASTOS",
    "AUX",
)
_PARAMETROS = (
    "fcas",
    "herramientas",
    "administracion",
    "utilidad",
    "iva",
    "capacidad_camion",
    "flete",
    "tarifa_vertedero",
)
_PORTADA = ("cliente", "contratista", "ubicacion", "norma", "moneda", "fecha_texto")
_LINEA = ("codigo", "descripcion", "unidad", "cantidad", "precio")
_PRESUPUESTO = (
    "numero",
    "codigo",
    "descripcion",
    "unidad",
    "rendimiento",
    "cantidad",
    "precio_unitario",
    "monto",
    "verificacion",
    "peso",
)
_INSUMOS = ("codigo", "descripcion", "unidad", "precio", "fuente")
_PROGRAMACION = (
    "DSEM",
    "FRENTES",
    "SEMANA_CORTE",
    "TIEMPO_CONTRATADO",
    "ANTICIPO",
    "N_VALUACIONES",
    "RETENCION",
)
_CONTROL = ("inicio_ejecutado", "fin_ejecutado", "inicio_final", "fin_final")
_ESPECIALES = (
    TipoFilaEspecial.TOTAL_SIN_IVA,
    TipoFilaEspecial.TOTAL,
    TipoFilaEspecial.SUBTOTAL,
    TipoFilaEspecial.IVA,
)


class PerfilInvalido(ValueError):  # noqa: N818
    """El JSON del perfil no describe una plantilla completa. Es un error del paquete, no del
    usuario."""


def normalizar(texto: object) -> str:
    """Forma de comparación de un rótulo: NFC, NBSP y espacios repetidos como un solo espacio, sin
    espacios en los extremos y sin distinguir mayúsculas. `None` y lo que no es texto dan ''."""
    if not isinstance(texto, str):
        return ""
    t = unicodedata.normalize("NFC", texto).replace("\xa0", " ")
    return " ".join(t.split()).casefold()


def coincide(texto: object, variantes: Iterable[str]) -> bool:
    """¿El texto de la celda empieza por alguna de las variantes del rótulo (normalizadas)?"""
    t = normalizar(texto)
    return bool(t) and any(t.startswith(normalizar(v)) for v in variantes)


@dataclass(frozen=True, slots=True)
class AnclaRotulo:
    """Un rótulo del APU: los textos con que aparece en la columna de rótulos y la columna de su
    valor."""

    variantes: tuple[str, ...]
    columna: str


@dataclass(frozen=True, slots=True)
class Perfil:
    """La plantilla de la empresa descrita por rótulos, columnas y nombres definidos.

    `hojas` va por nombre lógico ('PRESUPUESTO', 'CONTROL DE OBRA'…) al nombre real de la hoja.
    `programacion` va por clave ('DSEM'…) a `(hoja lógica, variantes del rótulo)`.
    `paleta` va por papel ('titulo', 'editable'…) a un color hex sin '#'; los papeles se dedujeron
    del uso real en el libro B-2 (relleno de títulos, encabezados, celdas ámbar editables…).
    """

    nombre: str
    hojas: Mapping[str, str]
    prefijo_apu: str
    celda_titulo_apu: str
    columna_rotulos_apu: str
    columna_cabecera_apu: str
    rotulos_codigo_partida: tuple[str, ...]
    rotulos_unidad: tuple[str, ...]
    columna_porcentaje_apu: str
    respaldo_rendimiento: str
    columnas_linea: Mapping[str, str]
    rotulos_apu: Mapping[Rotulo, AnclaRotulo]
    patron_codigo_insumo: str
    nombres_parametros: Mapping[str, str]
    nombres_totales: tuple[str, ...]
    rotulos_portada: Mapping[str, tuple[str, ...]]
    ancla_obra: str
    encabezado_presupuesto: Mapping[str, tuple[str, ...]]
    columnas_presupuesto: Mapping[str, str]
    columnas_desglose: tuple[str, ...]
    columnas_guardadas: tuple[str, ...]
    filas_especiales: Mapping[TipoFilaEspecial, tuple[str, ...]]
    columnas_insumos: Mapping[str, str]
    programacion: Mapping[str, tuple[str, tuple[str, ...]]]
    secciones_control_obra: Mapping[str, tuple[str, ...]]
    columnas_control_obra: Mapping[str, str]
    columnas_gastos: Mapping[str, str]
    fuente: str
    paleta: Mapping[str, str]

    def hoja(self, logica: str) -> str:
        """Nombre real de la hoja con ese nombre lógico."""
        return self.hojas[logica]

    def es_codigo_insumo(self, texto: object) -> bool:
        """¿Es un código de insumo de la plantilla (MT-01, MO-03, EQ-11…)?"""
        if not isinstance(texto, str):
            return False
        return _regex(self.patron_codigo_insumo).match(texto.strip()) is not None


@lru_cache(maxsize=8)
def _regex(patron: str) -> re.Pattern[str]:
    return re.compile(patron)


# --- Carga y validación --------------------------------------------------------------------------


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


def _columna(nombre: str, v: Any, donde: str) -> str:
    if not isinstance(v, str) or not _COLUMNA.match(v):
        raise _error(nombre, f"{donde} debe ser una letra de columna (A, G, AB…), no {v!r}")
    return v


def _columnas(nombre: str, d: Any, claves: tuple[str, ...], donde: str) -> Mapping[str, str]:
    d = _dic(nombre, d, donde)
    faltan = [k for k in claves if k not in d]
    if faltan:
        raise _error(nombre, f"{donde}: faltan {faltan}")
    return MappingProxyType({k: _columna(nombre, d[k], f"{donde}.{k}") for k in claves})


def _construir(nombre: str, crudo: Any) -> Perfil:
    raiz = _dic(nombre, crudo, "la raíz")
    # `LibroLeido.perfil` guarda este campo y `cargar_perfil(libro.perfil)` busca el archivo por él:
    # si no coincidieran, se cargaría otro perfil (o ninguno).
    declarado = _texto(nombre, raiz.get("nombre"), "nombre")
    if declarado != nombre:
        raise _error(nombre, f"nombre {declarado!r} no coincide con el del archivo ({nombre}.json)")
    hojas = _dic(nombre, raiz.get("hojas"), "hojas")
    faltan = [h for h in _HOJAS if h not in hojas]
    if faltan:
        raise _error(nombre, f"hojas: faltan {faltan}")

    apu = _dic(nombre, raiz.get("apu"), "apu")
    celda_titulo = _texto(nombre, apu.get("celda_titulo"), "apu.celda_titulo")
    if not _CELDA.match(celda_titulo):
        raise _error(nombre, f"apu.celda_titulo no es una celda: {celda_titulo!r}")
    rot = _dic(nombre, apu.get("rotulos"), "apu.rotulos")
    rotulos: dict[Rotulo, AnclaRotulo] = {}
    for r in Rotulo:
        d = _dic(nombre, rot.get(r.value), f"apu.rotulos.{r.value}")
        rotulos[r] = AnclaRotulo(
            variantes=_textos(nombre, d.get("variantes"), f"apu.rotulos.{r.value}.variantes"),
            columna=_columna(nombre, d.get("columna"), f"apu.rotulos.{r.value}.columna"),
        )

    patron = _texto(nombre, raiz.get("patron_codigo_insumo"), "patron_codigo_insumo")
    try:
        re.compile(patron)
    except re.error as exc:
        raise _error(nombre, f"patron_codigo_insumo no compila: {exc}") from exc

    params = _dic(nombre, raiz.get("parametros"), "parametros")
    faltan = [p for p in _PARAMETROS if p not in params]
    if faltan:
        raise _error(nombre, f"parametros: faltan {faltan}")

    portada = _dic(nombre, raiz.get("portada"), "portada")
    rot_portada = _dic(nombre, portada.get("rotulos"), "portada.rotulos")
    faltan = [p for p in _PORTADA if p not in rot_portada]
    if faltan:
        raise _error(nombre, f"portada.rotulos: faltan {faltan}")

    pres = _dic(nombre, raiz.get("presupuesto"), "presupuesto")
    enc = _dic(nombre, pres.get("encabezado"), "presupuesto.encabezado")
    if not enc:
        raise _error(nombre, "presupuesto.encabezado no puede estar vacío")
    esp = _dic(nombre, pres.get("filas_especiales"), "presupuesto.filas_especiales")
    especiales: dict[TipoFilaEspecial, tuple[str, ...]] = {}
    for t in _ESPECIALES:
        especiales[t] = _textos(nombre, esp.get(t.value), f"presupuesto.filas_especiales.{t}")

    prog = _dic(nombre, raiz.get("programacion"), "programacion")
    programacion: dict[str, tuple[str, tuple[str, ...]]] = {}
    for k in _PROGRAMACION:
        d = _dic(nombre, prog.get(k), f"programacion.{k}")
        hoja = _texto(nombre, d.get("hoja"), f"programacion.{k}.hoja")
        if hoja not in hojas:
            raise _error(nombre, f"programacion.{k}.hoja {hoja!r} no está en hojas")
        programacion[k] = (hoja, _textos(nombre, d.get("rotulos"), f"programacion.{k}.rotulos"))

    control = _dic(nombre, raiz.get("control_obra"), "control_obra")
    gastos = _dic(nombre, raiz.get("gastos"), "gastos")
    estilo = _dic(nombre, raiz.get("estilo"), "estilo")
    paleta = _dic(nombre, estilo.get("paleta"), "estilo.paleta")
    for papel, color in paleta.items():
        if not _NOMBRE.match(str(papel)) or not isinstance(color, str) or not _HEX.match(color):
            raise _error(nombre, f"estilo.paleta.{papel}: color hex de 6 cifras, no {color!r}")

    return Perfil(
        nombre=declarado,
        hojas=MappingProxyType({h: _texto(nombre, hojas[h], f"hojas.{h}") for h in hojas}),
        prefijo_apu=_texto(nombre, apu.get("prefijo"), "apu.prefijo"),
        celda_titulo_apu=celda_titulo,
        columna_rotulos_apu=_columna(nombre, apu.get("columna_rotulos"), "apu.columna_rotulos"),
        columna_cabecera_apu=_columna(nombre, apu.get("columna_cabecera"), "apu.columna_cabecera"),
        rotulos_codigo_partida=_textos(
            nombre, apu.get("rotulos_codigo_partida"), "apu.rotulos_codigo_partida"
        ),
        rotulos_unidad=_textos(nombre, apu.get("rotulos_unidad"), "apu.rotulos_unidad"),
        columna_porcentaje_apu=_columna(
            nombre, apu.get("columna_porcentaje"), "apu.columna_porcentaje"
        ),
        respaldo_rendimiento=_texto(
            nombre, apu.get("respaldo_rendimiento"), "apu.respaldo_rendimiento"
        ),
        columnas_linea=_columnas(nombre, apu.get("columnas_linea"), _LINEA, "apu.columnas_linea"),
        rotulos_apu=MappingProxyType(rotulos),
        patron_codigo_insumo=patron,
        nombres_parametros=MappingProxyType(
            {p: _texto(nombre, params[p], f"parametros.{p}") for p in _PARAMETROS}
        ),
        nombres_totales=_textos(nombre, raiz.get("totales"), "totales"),
        rotulos_portada=MappingProxyType(
            {p: _textos(nombre, rot_portada[p], f"portada.rotulos.{p}") for p in _PORTADA}
        ),
        ancla_obra=_texto(nombre, portada.get("ancla_obra"), "portada.ancla_obra"),
        encabezado_presupuesto=MappingProxyType(
            {
                _columna(nombre, c, "presupuesto.encabezado"): _textos(
                    nombre, v, f"presupuesto.encabezado.{c}"
                )
                for c, v in enc.items()
            }
        ),
        columnas_presupuesto=_columnas(
            nombre, pres.get("columnas"), _PRESUPUESTO, "presupuesto.columnas"
        ),
        columnas_desglose=tuple(
            _columna(nombre, c, "presupuesto.desglose")
            for c in _textos(nombre, pres.get("desglose"), "presupuesto.desglose")
        ),
        columnas_guardadas=tuple(
            _columna(nombre, c, "presupuesto.guardados")
            for c in _textos(nombre, pres.get("guardados"), "presupuesto.guardados")
        ),
        filas_especiales=MappingProxyType(especiales),
        columnas_insumos=_columnas(
            nombre,
            _dic(nombre, raiz.get("insumos"), "insumos").get("columnas"),
            _INSUMOS,
            "insumos.columnas",
        ),
        programacion=MappingProxyType(programacion),
        secciones_control_obra=MappingProxyType(
            {k: _textos(nombre, control.get(k), f"control_obra.{k}") for k in _CONTROL}
        ),
        columnas_control_obra=_columnas(
            nombre, control, ("columna_numero", "columna_cantidad"), "control_obra"
        ),
        columnas_gastos=_columnas(nombre, gastos, ("columna_numero", "columna_gastado"), "gastos"),
        fuente=_texto(nombre, estilo.get("fuente"), "estilo.fuente"),
        paleta=MappingProxyType(dict(paleta)),
    )


@lru_cache(maxsize=4)
def cargar_perfil(nombre: str = "arenaza") -> Perfil:
    """Carga y valida `perfiles/<nombre>.json`. El perfil es inmutable, así que se guarda en caché.

    Lanza `PerfilInvalido` si el nombre no es un perfil del paquete, si el JSON está incompleto o
    si su campo `nombre` no es el del archivo.
    """
    if not re.fullmatch(r"[a-z0-9_]+", nombre):
        raise PerfilInvalido(f"nombre de perfil no válido: {nombre!r}")
    ruta = _DIR_PERFILES / f"{nombre}.json"
    if not ruta.is_file():
        raise PerfilInvalido(f"no existe el perfil {nombre!r}")
    try:
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise _error(nombre, f"JSON mal formado: {exc}") from exc
    return _construir(nombre, crudo)
