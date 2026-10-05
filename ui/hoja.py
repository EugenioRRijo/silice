"""La hoja del proyecto, sin Streamlit: borrador, derivacion, elaboracion y Estado por fila.

Orquesta lo que la pantalla `ui/paginas/hoja.py` solo pinta (spec del sprint final, §5.3 y §9.2):

1. **Borrador en memoria.** El modelo espacial (`adapters.espacio.Espacio`) se edita como tablas de
   texto (`COLUMNAS`): `filas_desde_espacio` lo vuelca a filas y `espacio_desde_filas` lo
   reconstruye, conservando de la base lo que el editor no muestra (circuitos, sobrescrituras de
   segmento y recorridos propuestos). Una fila mala es un `HojaInvalida` con la fila y el campo;
   la pantalla conserva entonces el ultimo borrador valido. Las celdas se leen con
   `ui.composicion.texto_de_celda`, la unica lectura de celdas de `ui/` (INV-046).
2. **Derivacion y elaboracion.** `elaborar_hoja` deriva los `ItemComputo` con
   `adapters.espacio.derivar`, les suma los items de la version que no vienen del espacio
   (`items_base`) y llama a `core.budget.elaborar` con `reglas = REGLAS + reglas_espacio(espacio)`:
   el `Espacio` inmutable es la instantanea que reciben R8, R9 y R10 (DA-SF-8).
3. **Estado por fila** (RF-55). `estado_de_filas` asigna a cada fila editable el peor hallazgo que
   la toca, por las claves `esp_*` que los hallazgos citan en `origen_ids` (tambien dentro del
   `origen_id` compuesto de un item, que separa sus fuentes con «;»). Las advertencias de una misma
   fila van en un solo texto: R8 marca una por origen supuesto y, sin agrupar, el baño correcto
   del ejemplo pintaria cinco lineas.

Un presupuesto sin espacio (la clinica, TI-001) abre igual que antes de la hoja (FR-5): espacio
vacio, ningun item derivado, solo `items_base`; R8, R9 y R10 se declaran evaluadas sin hallazgos.
La hoja deriva agua, datos y electricidad (`TODAS`). **No persiste**: guardar una version es SF3.

Sin Streamlit, sin `pandas` y sin `ui.caso`; lo vigila
`tests/unit/test_arquitectura.py::test_ui_respeta_sus_importaciones_prohibidas`.
"""

from __future__ import annotations

import re
import tempfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from adapters.espacio import (
    ESPECIALIDADES,
    Ambiente,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    ModoRecorrido,
    OrigenMedida,
    Punto,
    Recorrido,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoOrigen,
    TipoPunto,
    Tramo,
    cargar_espacio,
    crear_esquema_espacio,
    derivar,
    guardar_espacio,
)
from adapters.espacio.reglas import CantidadEscrita, reglas_espacio
from core import models
from core.budget import (
    CODIGO_PENDIENTE,
    CambioEditado,
    EstadoEquilibrio,
    PuntoEquilibrio,
    ResultadoElaboracion,
    ResultadoInstantanea,
    TablaExportable,
    asegurar_instantanea,
    cargar_elaboracion,
    cotizar_insumo,
    elaborar,
    exportar_hoja,
    guardar_edicion,
    plan_de_version,
    plan_secuencial,
    punto_equilibrio,
    restaurar_version,
    siguiente_codigo,
    tabla_trazabilidad,
    version_vigente,
)
from core.budget import registros_de_version as registros_de_version_core
from core.budget import retirar_cotizacion as _retirar_cotizacion
from core.budget.curva import FORMATO_PERIODO
from core.budget.instantanea import composiciones_de_version
from core.budget.presupuesto import MONEDA_POR_DEFECTO
from core.catalog import Catalogo, CatalogoIncompleto
from core.catalog.origen import origen_de_precios
from core.contracts import ComposicionAPU, ItemComputo, ParametrosCosto, Severidad
from core.contracts.item_computo import OrigenTipo
from core.verification import REGLAS
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from ui.composicion import ComposicionInvalida, decimal_desde_texto, texto_de_celda

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from core.budget import GeneradorPlan, PeriodoPlan
    from core.catalog.origen import OrigenPrecio
    from core.contracts.verificacion import Hallazgo
    from core.verification.informe import InformeAuditoria

#: Columnas de cada tabla editable del borrador: la clave interna de cada celda, no su rotulo.
COLUMNAS: dict[str, tuple[str, ...]] = {
    "origenes": ("id", "tipo", "referencia"),
    "ambientes": ("id", "nombre", "x0", "y0", "largo", "ancho", "alto", "origen_id"),
    "fuentes": ("id", "especialidad", "tipo", "ambiente_id", "x", "y", "z", "origen_id"),
    "puntos": (
        "id",
        "nombre",
        "especialidad",
        "tipo",
        "ambiente_id",
        "superficie",
        "x",
        "y",
        "z",
        "fuente_id",
        "circuito_id",
        "especificaciones",
        "origen_id",
    ),
    "tramos": (
        "recorrido_id",
        "punto_id",
        "circuito_id",
        "orden",
        "superficie",
        "empotrado",
        "pendiente",
        "vertices",
    ),
}

#: Rotulo de cada tabla en los mensajes de error.
ROTULOS: dict[str, str] = {
    "origenes": "origenes de medida",
    "ambientes": "ambientes",
    "fuentes": "fuentes",
    "puntos": "puntos",
    "tramos": "vertices de recorridos",
}

#: Tablas editables que muestran la columna Estado, con el prefijo de sus claves `esp_*`.
TABLAS_CON_ESTADO = {"ambientes": "esp_ambientes", "fuentes": "esp_fuentes", "puntos": "esp_puntos"}

#: Estado de una fila que ningun hallazgo toca.
TEXTO_OK = "OK"

#: Estado de una fila cuyos items citan partidas sin APU en el catalogo (no es error de medida).
TEXTO_PENDIENTE = "PENDIENTE: sin APU en el catálogo"

_SI, _NO = "si", "no"


class HojaInvalida(ValueError):  # noqa: N818
    """Una fila (o el conjunto) del borrador no forma un espacio valido; dice cual y por que."""


@dataclass(frozen=True, slots=True)
class EstadoFila:
    """Estado de una fila editable: su peor severidad (`None` si esta limpia) y un solo texto."""

    severidad: Severidad | None
    texto: str


@dataclass(frozen=True, slots=True)
class ResultadoHoja:
    """Lo que la pantalla pinta de un borrador (spec §5.3).

    `items` son los derivados del espacio (como antes de SF3); `todos` son los que se elaboraron
    (los de la version que no vienen del espacio mas los derivados, con las cantidades escritas a
    mano ya aplicadas) y `estado_items` es el Estado de cada uno por su clave (`claves_de_items`).
    `estado` es el de las filas editables del espacio. `plan` es el plan efectivo con que se hizo
    la curva (ya ajustado a las partidas del presupuesto) y `equilibrio` el punto de equilibrio.
    """

    items: list[ItemComputo]
    elaboracion: ResultadoElaboracion
    estado: dict[str, EstadoFila]
    equilibrio: PuntoEquilibrio
    plan: tuple[PeriodoPlan, ...] | None = None
    todos: list[ItemComputo] = field(default_factory=list)
    estado_items: dict[str, EstadoFila] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class Borrador:
    """Lo que la hoja edita sin persistir (spec §5.3 y §9.2): el borrador completo de una version.

    * `espacio`: el modelo espacial (pestana Espacio y metrajes);
    * `items_base`: los items de la version que no vienen del espacio (la clinica, TI-001);
    * `composiciones`: **la copia de la version** de los APU (DA-SF-7): cantidades de linea,
      insumo elegido y rendimiento se editan aqui, nunca en el catalogo;
    * `parametros`: los de `ParametrosCosto` (FCAS, bono, administracion y utilidad);
    * `plan`: el reparto de cada partida por periodo (`None`: la version no tiene plan);
    * `cantidades`: las cantidades escritas a mano (DA-SF-5), por la clave de su item
      (`claves_de_items`). R8 las marca.

    Es inmutable: cada edicion produce otro borrador con `dataclasses.replace`, y la pantalla
    compara el vigente con el abierto (`cambios_entre`) para saber si hay algo sin guardar.
    """

    fecha: date
    moneda: str = MONEDA_POR_DEFECTO
    espacio: Espacio = field(default_factory=Espacio)
    items_base: tuple[ItemComputo, ...] = ()
    composiciones: Mapping[str, ComposicionAPU] = field(default_factory=dict)
    parametros: ParametrosCosto = field(default_factory=ParametrosCosto)
    plan: tuple[PeriodoPlan, ...] | None = None
    cantidades: Mapping[str, Decimal] = field(default_factory=dict)


# --- filas -> modelo ----------------------------------------------------------------------------


def _numero(valor: Decimal) -> str:
    """Un decimal sin ceros de relleno ni notacion cientifica (`2.500` -> `2.5`, `1E+1` -> `10`)."""
    texto = format(valor.normalize(), "f")
    return "0" if texto in {"-0", ""} else texto


def _coords_a_texto(vertices: Iterable[Coord]) -> str:
    return "; ".join(f"{_numero(v.x)},{_numero(v.y)},{_numero(v.z)}" for v in vertices)


def _pares_a_texto(pares: Iterable[tuple[str, str]]) -> str:
    return "; ".join(f"{k}={v}" for k, v in pares)


def _bool_a_texto(valor: bool | None) -> str:
    return "" if valor is None else (_SI if valor else _NO)


def filas_desde_espacio(espacio: Espacio) -> dict[str, list[dict[str, str]]]:
    """Las cinco tablas editables del borrador, con las celdas como texto exacto."""
    tramos = [
        {
            "recorrido_id": r.id,
            "punto_id": r.punto_id or "",
            "circuito_id": r.circuito_id or "",
            "orden": str(t.orden),
            "superficie": t.superficie.value,
            "empotrado": _bool_a_texto(t.empotrado),
            "pendiente": "" if t.pendiente is None else _numero(t.pendiente),
            "vertices": _coords_a_texto(t.vertices),
        }
        for r in espacio.recorridos
        if r.modo is ModoRecorrido.DECLARADO
        for t in r.tramos
    ]
    return {
        "origenes": [
            {"id": o.id, "tipo": o.tipo.value, "referencia": _pares_a_texto(o.referencia)}
            for o in espacio.origenes
        ],
        "ambientes": [
            {
                "id": a.id,
                "nombre": a.nombre,
                "x0": _numero(a.x0),
                "y0": _numero(a.y0),
                "largo": _numero(a.largo),
                "ancho": _numero(a.ancho),
                "alto": _numero(a.alto),
                "origen_id": a.origen_id,
            }
            for a in espacio.ambientes
        ],
        "fuentes": [
            {
                "id": f.id,
                "especialidad": f.especialidad.value,
                "tipo": f.tipo.value,
                "ambiente_id": f.ambiente_id,
                "x": _numero(f.posicion.x),
                "y": _numero(f.posicion.y),
                "z": _numero(f.posicion.z),
                "origen_id": f.origen_id,
            }
            for f in espacio.fuentes
        ],
        "puntos": [
            {
                "id": p.id,
                "nombre": p.nombre,
                "especialidad": p.especialidad.value,
                "tipo": p.tipo.value,
                "ambiente_id": p.ambiente_id,
                "superficie": p.superficie.value,
                "x": _numero(p.posicion.x),
                "y": _numero(p.posicion.y),
                "z": _numero(p.posicion.z),
                "fuente_id": p.fuente_id or "",
                "circuito_id": p.circuito_id or "",
                "especificaciones": _pares_a_texto(p.especificaciones),
                "origen_id": p.origen_id,
            }
            for p in espacio.puntos
        ],
        "tramos": tramos,
    }


def _enum[E: StrEnum](clase: type[E], valor: str, campo: str) -> E:
    try:
        return clase(valor)
    except ValueError:
        validos = ", ".join(m.value for m in clase)
        raise ValueError(f"{campo}: {valor!r} no es un valor valido ({validos})") from None


def _pares_desde_texto(texto: str, campo: str) -> dict[str, str]:
    pares: dict[str, str] = {}
    for trozo in texto.split(";"):
        if not trozo.strip():
            continue
        clave, igual, valor = trozo.partition("=")
        if not igual or not clave.strip():
            raise ValueError(f"{campo}: {trozo.strip()!r} no tiene la forma clave=valor")
        pares[clave.strip()] = valor.strip()
    return pares


def _coord(x: str, y: str, z: str, campo: str) -> Coord:
    return Coord(
        decimal_desde_texto(x, f"{campo} x"),
        decimal_desde_texto(y, f"{campo} y"),
        decimal_desde_texto(z, f"{campo} z"),
    )


def _vertices(texto: str) -> tuple[Coord, ...]:
    puntos = [p for p in texto.split(";") if p.strip()]
    vertices = []
    for p in puntos:
        partes = p.split(",")
        if len(partes) != 3:
            raise ValueError(f"vertices: {p.strip()!r} no tiene la forma x,y,z")
        vertices.append(_coord(*partes, campo="vertices"))
    if len(vertices) < 2:
        raise ValueError("vertices: un tramo necesita dos vertices x,y,z o mas, separados por «;»")
    return tuple(vertices)


def _tri(texto: str, campo: str) -> bool | None:
    if not texto:
        return None
    if texto.lower() not in {_SI, _NO}:
        raise ValueError(f"{campo}: {texto!r} debe ser «si», «no» o quedar vacio")
    return texto.lower() == _SI


def _opcional(texto: str) -> str | None:
    return texto or None


def _celdas(fila: Mapping[str, object], tabla: str) -> dict[str, str]:
    return {c: texto_de_celda(fila, c) for c in COLUMNAS[tabla]}


def _construir[T](
    tabla: str,
    filas: Sequence[Mapping[str, object]],
    fabrica: Callable[[dict[str, str]], T],
) -> list[T]:
    """Una entidad por fila con datos; una fila dinamica en blanco no es un error."""
    construidas: list[T] = []
    for numero, fila in enumerate(filas, start=1):
        celdas = _celdas(fila, tabla)
        if not any(celdas.values()):
            continue
        try:
            construidas.append(fabrica(celdas))
        except (ValueError, TypeError, ComposicionInvalida) as error:
            raise HojaInvalida(f"{ROTULOS[tabla]}, fila {numero}: {error}") from error
    return construidas


def _origen(c: dict[str, str]) -> OrigenMedida:
    return OrigenMedida(
        id=c["id"],
        tipo=_enum(TipoOrigen, c["tipo"], "tipo"),
        referencia=_pares_desde_texto(c["referencia"], "referencia"),
    )


def _ambiente(c: dict[str, str]) -> Ambiente:
    d = {k: decimal_desde_texto(c[k], k) for k in ("x0", "y0", "largo", "ancho", "alto")}
    return Ambiente(id=c["id"], nombre=c["nombre"], origen_id=c["origen_id"], **d)


def _fuente(c: dict[str, str]) -> Fuente:
    return Fuente(
        id=c["id"],
        especialidad=_enum(Especialidad, c["especialidad"] or "agua", "especialidad"),
        tipo=_enum(TipoFuente, c["tipo"], "tipo"),
        ambiente_id=c["ambiente_id"],
        posicion=_coord(c["x"], c["y"], c["z"], "posicion"),
        origen_id=c["origen_id"],
    )


def _punto(c: dict[str, str]) -> Punto:
    return Punto(
        id=c["id"],
        nombre=c["nombre"],
        especialidad=_enum(Especialidad, c["especialidad"] or "agua", "especialidad"),
        tipo=_enum(TipoPunto, c["tipo"], "tipo"),
        ambiente_id=c["ambiente_id"],
        superficie=_enum(SuperficiePunto, c["superficie"], "superficie"),
        posicion=_coord(c["x"], c["y"], c["z"], "posicion"),
        fuente_id=_opcional(c["fuente_id"]),
        circuito_id=_opcional(c["circuito_id"]),
        especificaciones=_pares_desde_texto(c["especificaciones"], "especificaciones"),
        origen_id=c["origen_id"],
    )


def _tramo(c: dict[str, str]) -> tuple[str, str | None, str | None, Tramo]:
    if not c["recorrido_id"]:
        raise ValueError("recorrido_id: el tramo debe nombrar su recorrido")
    try:
        orden = int(c["orden"])
    except ValueError:
        raise ValueError(f"orden: {c['orden']!r} no es un entero") from None
    tramo = Tramo(
        orden=orden,
        superficie=_enum(SuperficieTramo, c["superficie"], "superficie"),
        vertices=_vertices(c["vertices"]),
        empotrado=_tri(c["empotrado"], "empotrado"),
        pendiente=decimal_desde_texto(c["pendiente"], "pendiente") if c["pendiente"] else None,
    )
    return c["recorrido_id"], _opcional(c["punto_id"]), _opcional(c["circuito_id"]), tramo


def _recorridos_declarados(
    filas: Sequence[Mapping[str, object]],
) -> list[Recorrido]:
    por_recorrido: dict[str, tuple[str | None, str | None, list[Tramo]]] = {}
    for rid, punto, circuito, tramo in _construir("tramos", filas, _tramo):
        _, _, tramos = por_recorrido.setdefault(rid, (punto, circuito, []))
        tramos.append(tramo)
    try:
        return [
            Recorrido(
                id=rid,
                modo=ModoRecorrido.DECLARADO,
                punto_id=punto,
                circuito_id=circuito,
                tramos=tuple(tramos),
            )
            for rid, (punto, circuito, tramos) in por_recorrido.items()
        ]
    except ValueError as error:
        raise HojaInvalida(f"{ROTULOS['tramos']}: {error}") from error


def espacio_desde_filas(
    filas: Mapping[str, Sequence[Mapping[str, object]]], base: Espacio | None = None
) -> Espacio:
    """El borrador que describen las tablas del editor, o `HojaInvalida` con la fila culpable.

    `base` aporta lo que el editor no muestra: circuitos, sobrescrituras de segmento y recorridos
    propuestos (los declarados salen de la tabla de vertices). Una tabla ausente de `filas` cuenta
    como vacia.
    """
    base = base if base is not None else Espacio()
    declarados = _recorridos_declarados(filas.get("tramos", ()))
    nombres = {r.id for r in declarados}
    puntos = tuple(_construir("puntos", filas.get("puntos", ()), _punto))
    existentes = {p.id for p in puntos}
    # un recorrido propuesto no guarda datos: solo marca que el punto usa el camino que propone la
    # hoja; si el punto se quita de la tabla, su recorrido propuesto se va con el
    propuestos = [
        r
        for r in base.recorridos
        if r.modo is ModoRecorrido.PROPUESTO
        and r.id not in nombres
        and (r.punto_id is None or r.punto_id in existentes)
    ]
    try:
        return Espacio(
            origenes=tuple(_construir("origenes", filas.get("origenes", ()), _origen)),
            ambientes=tuple(_construir("ambientes", filas.get("ambientes", ()), _ambiente)),
            fuentes=tuple(_construir("fuentes", filas.get("fuentes", ()), _fuente)),
            circuitos=base.circuitos,
            puntos=puntos,
            recorridos=(*propuestos, *declarados),
            sobrescrituras=base.sobrescrituras,
        )
    except ValueError as error:
        if isinstance(error, HojaInvalida):
            raise
        raise HojaInvalida(str(error)) from error


# --- derivacion y elaboracion -------------------------------------------------------------------


def borrador_de_version(sesion: Session, version_id: int) -> Espacio:
    """El espacio guardado de una version; vacio si no tiene o si la base es anterior a la hoja.

    Lee y no escribe (FR-5): una clinica o TI-001 sin tablas `esp_*` abren con la hoja vacia.
    """
    return cargar_espacio(sesion, version_id)


#: Las tres especialidades que deriva la hoja (agua, datos y electricidad), en este orden.
TODAS: tuple[str, ...] = ESPECIALIDADES


def items_del_borrador(
    espacio: Espacio, especialidad: str | Iterable[str] = Especialidad.AGUA.value
) -> list[ItemComputo]:
    """Los `ItemComputo` que deriva el borrador para una especialidad o para varias, en el orden
    pedido (`TODAS` pide las tres). Vacio si no hay espacio (FR-1)."""
    if isinstance(especialidad, str):
        return derivar(espacio, especialidad)
    return [item for una in especialidad for item in derivar(espacio, una)]


def composiciones_del_catalogo(
    catalogo: Catalogo, items: Sequence[ItemComputo], fecha: date
) -> dict[str, ComposicionAPU]:
    """Las composiciones que el catalogo tiene para los codigos de `items`, a `fecha`.

    Un codigo sin partida no esta en el resultado: `elaborar` lo deja pendiente y el informe lo
    declara (UC-01 3a), igual que `ui.elaboracion.elaborar_desde_catalogo`.
    """
    existentes = {partida.codigo for partida in catalogo.partidas()}
    codigos = [c for c in dict.fromkeys(i.codigo_partida for i in items) if c in existentes]
    return catalogo.composiciones(codigos, fecha=fecha)


def elaborar_hoja(
    espacio: Espacio,
    composiciones: Mapping[str, ComposicionAPU],
    *,
    codigo: str,
    fecha: date,
    especialidad: str | Iterable[str] = Especialidad.AGUA.value,
    items_base: Sequence[ItemComputo] = (),
    parametros: ParametrosCosto | None = None,
    moneda: str = MONEDA_POR_DEFECTO,
    plan: Sequence[PeriodoPlan] | GeneradorPlan | None = plan_secuencial,
    cantidades: Mapping[str, Decimal] | None = None,
) -> ResultadoHoja:
    """Deriva, elabora y audita el borrador: `REGLAS + reglas_espacio(espacio)`, siempre.

    `items_base` son los items de la version que no vienen del espacio (la clinica, TI-001, o las
    cantidades escritas a mano): se elaboran junto a los derivados. Con espacio vacio y sin
    `items_base` el presupuesto sale vacio y el Estado, `{}` (FR-1).

    `cantidades` son las cantidades escritas a mano por clave de item (DA-SF-5): el item deja de
    ser de regla y R8 lo marca. Un `plan` ya escrito se ajusta a las partidas valoradas
    (`ajustar_plan`); sin plan (`None`) no hay curva. El punto de equilibrio sale siempre.
    """
    parametros = parametros if parametros is not None else ParametrosCosto()
    derivados = items_del_borrador(espacio, especialidad)
    sin_escribir = [*items_base, *derivados]
    todos = _con_cantidades(sin_escribir, cantidades or {})
    escritas = _cantidades_escritas(sin_escribir, cantidades or {})
    if plan is not None and not callable(plan):
        valoradas = [i.codigo_partida for i in todos if i.codigo_partida in composiciones]
        plan = ajustar_plan(plan, valoradas)
    usado: list[tuple[PeriodoPlan, ...]] = []
    plan_final: Sequence[PeriodoPlan] | GeneradorPlan | None = plan
    if callable(plan):
        generador = plan

        def plan_capturado(presupuesto):
            reparto = tuple(generador(presupuesto))
            usado.append(reparto)
            return reparto

        plan_final = plan_capturado
    elaboracion = elaborar(
        todos,
        composiciones,
        parametros,
        codigo=codigo,
        fecha=fecha,
        moneda=moneda,
        plan=plan_final,
        reglas=(*REGLAS, *reglas_espacio(espacio, escritas)),
    )
    if usado:
        efectivo: tuple[PeriodoPlan, ...] | None = usado[0]
    else:
        efectivo = None if plan_final is None else tuple(plan_final)
    return ResultadoHoja(
        items=derivados,
        elaboracion=elaboracion,
        estado=estado_de_filas(espacio, elaboracion.informe),
        equilibrio=punto_equilibrio(elaboracion.presupuesto, parametros),
        plan=efectivo,
        todos=todos,
        estado_items=estado_de_items(todos, elaboracion.informe),
    )


def elaborar_borrador(
    borrador: Borrador, codigo: str = "HOJA", especialidad: str | Iterable[str] = TODAS
) -> ResultadoHoja:
    """Elabora el borrador completo (RF-52): lo que cambia al aplicar una edicion, sin persistir.

    Es la unica via de la pantalla, de `guardar_version` y de `scripts/medir_rnf11.py`: deriva,
    valora con la copia de composiciones del borrador, ajusta el plan, audita con R1 a R10 y
    calcula el punto de equilibrio. `codigo` es el de la version que saldra si se guarda.
    """
    return elaborar_hoja(
        borrador.espacio,
        borrador.composiciones,
        codigo=codigo,
        fecha=borrador.fecha,
        especialidad=especialidad,
        items_base=borrador.items_base,
        parametros=borrador.parametros,
        moneda=borrador.moneda,
        plan=borrador.plan,
        cantidades=borrador.cantidades,
    )


# --- items, claves y cantidades escritas a mano -------------------------------------------------


def claves_de_items(items: Sequence[ItemComputo]) -> list[str]:
    """La clave estable de cada item: `partida|origen_id`, con `#2`, `#3`... si se repite.

    Es la identidad con que se escribe una cantidad a mano y con que el Estado y el registro de
    cambios nombran un renglon del presupuesto.
    """
    vistas: dict[str, int] = {}
    claves: list[str] = []
    for item in items:
        base = f"{item.codigo_partida}|{item.origen_id}"
        veces = vistas.get(base, 0) + 1
        vistas[base] = veces
        claves.append(base if veces == 1 else f"{base}#{veces}")
    return claves


def _con_cantidades(
    items: Sequence[ItemComputo], cantidades: Mapping[str, Decimal]
) -> list[ItemComputo]:
    """Los items con las cantidades escritas aplicadas. Un item escrito a mano deja de ser de
    la regla que lo derivo y declara como regla su propio valor (`"9"`): R1 compara la cantidad
    con su regla (seria un falso ERROR) o, sin regla, advierte que es manual, y la marca de la
    cantidad escrita es de R8 (DA-SF-5), no de R1. Una clave sin item se ignora."""
    if not cantidades:
        return list(items)
    return [
        replace(
            item,
            cantidad=cantidades[clave],
            origen_tipo=OrigenTipo.MANUAL,
            regla=_numero(cantidades[clave]),
            parametros={},
        )
        if clave in cantidades and cantidades[clave] != item.cantidad
        else item
        for clave, item in zip(claves_de_items(items), items, strict=True)
    ]


def _cantidades_escritas(
    items: Sequence[ItemComputo], cantidades: Mapping[str, Decimal]
) -> list[CantidadEscrita]:
    return [
        CantidadEscrita(item.codigo_partida, item.origen_id, item.cantidad, cantidades[clave])
        for clave, item in zip(claves_de_items(items), items, strict=True)
        if clave in cantidades and cantidades[clave] != item.cantidad
    ]


def items_sin_escribir(borrador: Borrador) -> list[ItemComputo]:
    """Los items del borrador con la cantidad calculada o guardada (sin lo escrito a mano): el
    valor con que `cantidades_desde_filas` compara cada fila de la tabla del Presupuesto."""
    return [*borrador.items_base, *items_del_borrador(borrador.espacio, TODAS)]


def items_elaborados(borrador: Borrador) -> list[ItemComputo]:
    """Los items que se elaboran: los de la version que no vienen del espacio, los derivados del
    espacio y las cantidades escritas a mano ya aplicadas (DA-SF-5)."""
    return _con_cantidades(items_sin_escribir(borrador), borrador.cantidades)


def cantidades_escritas(borrador: Borrador) -> list[CantidadEscrita]:
    """Las cantidades que el borrador escribe a mano y difieren de la calculada o guardada."""
    return _cantidades_escritas(items_sin_escribir(borrador), borrador.cantidades)


def cantidades_desde_filas(
    filas: Sequence[Mapping[str, object]], items: Sequence[ItemComputo]
) -> dict[str, Decimal]:
    """Las cantidades escritas a mano que describe la tabla del Presupuesto, por clave de item.

    La tabla tiene la `clave` de cada item y su `cantidad` editable; solo cuentan las filas cuyo
    valor difiere del calculado (`items`, los de `items_sin_escribir`). `HojaInvalida` con la fila
    culpable si no es un numero no negativo.
    """
    por_clave = dict(zip(claves_de_items(items), items, strict=True))
    escritas: dict[str, Decimal] = {}
    for numero, fila in enumerate(filas, start=1):
        clave = texto_de_celda(fila, "clave")
        item = por_clave.get(clave)
        if item is None:
            continue
        donde = f"presupuesto, fila {numero} ({item.codigo_partida})"
        try:
            valor = decimal_desde_texto(texto_de_celda(fila, "cantidad"), "cantidad")
        except ComposicionInvalida as error:
            raise HojaInvalida(f"{donde}: {error}") from error
        if valor < 0:
            raise HojaInvalida(
                f"{donde}: la cantidad no puede ser negativa; escriba cero o una cantidad positiva"
            )
        if valor != item.cantidad:
            escritas[clave] = valor
    return escritas


# --- parametros ---------------------------------------------------------------------------------

#: Los campos de `ParametrosCosto` que la pestana Parametros edita (no se agregan nuevos).
CAMPOS_PARAMETROS = ("fcas", "bono_alimentacion", "administracion", "utilidad")


def parametros_desde_texto(textos: Mapping[str, str]) -> ParametrosCosto:
    """Los `ParametrosCosto` que escriben los cuadros de texto; `HojaInvalida` dice el campo."""
    try:
        return ParametrosCosto(
            **{c: decimal_desde_texto(textos.get(c, ""), c) for c in CAMPOS_PARAMETROS}
        )
    except (ComposicionInvalida, ValueError) as error:
        raise HojaInvalida(f"parametros: {error}") from error


# --- plan ---------------------------------------------------------------------------------------


def ajustar_plan(plan: Sequence[PeriodoPlan], codigos: Iterable[str]) -> list[PeriodoPlan]:
    """El plan con exactamente las partidas `codigos`: conserva el reparto de las que ya estaban,
    quita las que ya no estan (y los periodos que quedan vacios) y agrega un periodo de cierre
    por cada partida nueva, ejecutada al 100 %.

    Asi editar el espacio (agregar o quitar una partida) no rompe la curva con `PlanInvalido`.
    """
    codigos = list(dict.fromkeys(codigos))
    presentes = set(codigos)
    periodos: list[PeriodoPlan] = []
    for etiqueta, reparto in plan:
        filtrado = tuple((c, f) for c, f in reparto if c in presentes)
        if filtrado or not reparto:
            periodos.append((etiqueta, filtrado))
    cubiertos = {c for _, reparto in periodos for c, _ in reparto}
    siguiente = len(plan)
    for codigo in codigos:
        if codigo not in cubiertos:
            siguiente += 1
            periodos.append((FORMATO_PERIODO.format(n=siguiente), ((codigo, Decimal(1)),)))
    return periodos


def plan_como_filas(
    plan: Sequence[PeriodoPlan], codigos: Sequence[str]
) -> tuple[list[str], list[dict[str, str]]]:
    """La matriz del plan para el editor: una fila por partida y una columna por periodo.

    Devuelve las etiquetas de los periodos (unicas: si dos coinciden, la segunda lleva ` (2)`) y
    las filas `{"partida": codigo, etiqueta: fraccion}` con la fraccion como texto.
    """
    etiquetas: list[str] = []
    for etiqueta, _ in plan:
        candidata, n = etiqueta, 1
        while candidata in etiquetas:
            n += 1
            candidata = f"{etiqueta} ({n})"
        etiquetas.append(candidata)
    filas = []
    for codigo in codigos:
        fila = {"partida": codigo}
        for etiqueta, (_, reparto) in zip(etiquetas, plan, strict=True):
            fila[etiqueta] = _numero(sum((f for c, f in reparto if c == codigo), Decimal(0)))
        filas.append(fila)
    return etiquetas, filas


def plan_desde_filas(
    filas: Sequence[Mapping[str, object]], etiquetas: Sequence[str]
) -> list[PeriodoPlan]:
    """El plan que describe la matriz del editor, o `HojaInvalida`: cada partida debe sumar
    exactamente 1 y ninguna fraccion puede ser negativa. Una celda vacia es 0."""
    reparto: dict[str, list[tuple[str, Decimal]]] = {etiqueta: [] for etiqueta in etiquetas}
    for fila in filas:
        codigo = texto_de_celda(fila, "partida")
        if not codigo:
            continue
        suma = Decimal(0)
        for etiqueta in etiquetas:
            texto = texto_de_celda(fila, etiqueta) or "0"
            try:
                fraccion = decimal_desde_texto(texto, etiqueta)
            except ComposicionInvalida as error:
                raise HojaInvalida(f"plan, partida {codigo}: {error}") from error
            if fraccion < 0:
                raise HojaInvalida(
                    f"plan, partida {codigo}: la fraccion de {etiqueta} no puede ser negativa"
                )
            suma += fraccion
            if fraccion > 0:
                reparto[etiqueta].append((codigo, fraccion))
        if suma != Decimal(1):
            raise HojaInvalida(
                f"plan, partida {codigo}: las fracciones suman {_numero(suma)} y deben sumar "
                "exactamente 1; repartala entre los periodos hasta completar 1"
            )
    return [(etiqueta, tuple(reparto[etiqueta])) for etiqueta in etiquetas]


# --- punto de equilibrio ------------------------------------------------------------------------

_CODIGOS_AL_FINAL = re.compile(r"\s*\[[^\[\]]*\]\s*$")


def texto_equilibrio(pe: PuntoEquilibrio) -> str:
    """La salida declarada de cada caso del punto de equilibrio (spec §9.4), en una frase."""
    if pe.estado is EstadoEquilibrio.NO_APLICABLE:
        return "El presupuesto no tiene ventas: el punto de equilibrio no aplica."
    if pe.estado is EstadoEquilibrio.NO_EXISTE:
        return (
            "No existe punto de equilibrio: el margen de contribución no es positivo "
            "(los costos directos igualan o superan las ventas)."
        )
    if pe.estado is EstadoEquilibrio.NO_SE_ALCANZA:
        punto = formatear_decimal(pe.punto, DECIMALES_PRESENTACION)
        venta = formatear_decimal(pe.venta, DECIMALES_PRESENTACION)
        return f"El punto de equilibrio ({punto}) no se alcanza dentro del contrato ({venta})."
    if pe.periodo is None or pe.fraccion_periodo is None:
        return "Sin curva de inversión: el punto de equilibrio no se ubica en el plan."
    periodo = _CODIGOS_AL_FINAL.sub("", pe.periodo)
    avance = formatear_decimal(pe.fraccion_periodo * 100, 0)
    return f"Se alcanza en {periodo}, al {avance} % de ese período."


# --- cambios entre dos borradores ---------------------------------------------------------------

_TABLAS_ESP = {
    "origenes": "esp_origenes",
    "ambientes": "esp_ambientes",
    "fuentes": "esp_fuentes",
    "puntos": "esp_puntos",
    "tramos": "esp_tramos",
}
_LLAVES = {
    "origenes": ("id",),
    "ambientes": ("id",),
    "fuentes": ("id",),
    "puntos": ("id",),
    "tramos": ("recorrido_id", "orden"),
}


def _clave_de_fila(tabla: str, fila: Mapping[str, str]) -> str:
    return _TABLAS_ESP[tabla] + ":" + "#".join(fila[c] for c in _LLAVES[tabla])


def _resumen_de_fila(fila: Mapping[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in fila.items() if v)


def _cambios_de_metraje(base: Espacio, actual: Espacio) -> list[CambioEditado]:
    antes, despues = filas_desde_espacio(base), filas_desde_espacio(actual)
    cambios: list[CambioEditado] = []
    for tabla in COLUMNAS:
        previas = {_clave_de_fila(tabla, f): f for f in antes[tabla]}
        nuevas = {_clave_de_fila(tabla, f): f for f in despues[tabla]}
        for clave in [*previas, *(k for k in nuevas if k not in previas)]:
            if clave not in nuevas:
                resumen = _resumen_de_fila(previas[clave])
                cambios.append(CambioEditado("metraje", clave, "fila", resumen, ""))
            elif clave not in previas:
                resumen = _resumen_de_fila(nuevas[clave])
                cambios.append(CambioEditado("metraje", clave, "fila", "", resumen))
            else:
                cambios += [
                    CambioEditado(
                        "metraje", clave, columna, previas[clave][columna], nuevas[clave][columna]
                    )
                    for columna in COLUMNAS[tabla]
                    if previas[clave][columna] != nuevas[clave][columna]
                ]
    return cambios


def _lineas(composicion: ComposicionAPU) -> list[tuple[str, Decimal, Decimal]]:
    """Las lineas de un APU como `(descripcion, cantidad, precio)`: materiales, equipos y mano
    de obra, en ese orden."""
    return [
        *((m.descripcion, m.cantidad, m.precio) for m in composicion.materiales),
        *((e.descripcion, e.cantidad, e.precio) for e in composicion.equipos),
        *((o.descripcion, o.cantidad, o.sueldo) for o in composicion.mano_obra),
    ]


def _cambios_de_apu(
    base: Mapping[str, ComposicionAPU], actual: Mapping[str, ComposicionAPU]
) -> list[CambioEditado]:
    cambios: list[CambioEditado] = []
    for codigo, despues in actual.items():
        if codigo not in base:  # partida nueva traida del catalogo: no es una celda editada
            continue
        antes = base[codigo]
        if antes.rendimiento != despues.rendimiento:
            cambios.append(
                CambioEditado(
                    "apu",
                    codigo,
                    "rendimiento",
                    _numero(antes.rendimiento),
                    _numero(despues.rendimiento),
                )
            )
        for (d0, c0, p0), (d1, c1, p1) in zip(_lineas(antes), _lineas(despues), strict=False):
            clave = f"{codigo}|{d0}"
            if d0 != d1:
                cambios.append(CambioEditado("apu", clave, "insumo", d0, d1))
            if c0 != c1:
                cambios.append(CambioEditado("apu", clave, "cantidad", _numero(c0), _numero(c1)))
            if p0 != p1:
                cambios.append(CambioEditado("apu", clave, "precio", _numero(p0), _numero(p1)))
    return cambios


def _cambios_de_parametros(base: ParametrosCosto, actual: ParametrosCosto) -> list[CambioEditado]:
    return [
        CambioEditado(
            "parametro", campo, "valor", str(getattr(base, campo)), str(getattr(actual, campo))
        )
        for campo in CAMPOS_PARAMETROS
        if getattr(base, campo) != getattr(actual, campo)
    ]


def plan_efectivo(borrador: Borrador) -> tuple[PeriodoPlan, ...] | None:
    """El plan del borrador ajustado a las partidas que se valoran (el que se guarda)."""
    if borrador.plan is None:
        return None
    valoradas = [
        i.codigo_partida
        for i in items_elaborados(borrador)
        if i.codigo_partida in borrador.composiciones
    ]
    return tuple(ajustar_plan(borrador.plan, valoradas))


def _celdas_del_plan(plan: Sequence[PeriodoPlan] | None) -> dict[tuple[str, str], Decimal]:
    celdas: dict[tuple[str, str], Decimal] = {}
    for etiqueta, reparto in plan or ():
        for codigo, fraccion in reparto:
            celdas[(codigo, etiqueta)] = celdas.get((codigo, etiqueta), Decimal(0)) + fraccion
    return celdas


def _cambios_de_plan(base: Borrador, actual: Borrador) -> list[CambioEditado]:
    plan_base = plan_efectivo(base)
    antes, despues = _celdas_del_plan(plan_base), _celdas_del_plan(plan_efectivo(actual))
    vacio = "" if plan_base is None else "0"
    orden = [*antes, *(k for k in despues if k not in antes)]
    return [
        CambioEditado(
            "plan",
            codigo,
            etiqueta,
            _numero(antes[(codigo, etiqueta)]) if (codigo, etiqueta) in antes else vacio,
            _numero(despues[(codigo, etiqueta)]) if (codigo, etiqueta) in despues else "0",
        )
        for codigo, etiqueta in orden
        if antes.get((codigo, etiqueta)) != despues.get((codigo, etiqueta))
    ]


def _cambios_de_cantidades(base: Borrador, actual: Borrador) -> list[CambioEditado]:
    def efectivas(b: Borrador) -> dict[str, Decimal]:
        sin = items_sin_escribir(b)
        return {
            clave: b.cantidades.get(clave, item.cantidad)
            for clave, item in zip(claves_de_items(sin), sin, strict=True)
        }

    antes, despues = efectivas(base), efectivas(actual)
    claves = [*base.cantidades, *(k for k in actual.cantidades if k not in base.cantidades)]
    return [
        CambioEditado("cantidad", clave, "cantidad", _numero(antes[clave]), _numero(despues[clave]))
        for clave in claves
        if clave in antes and clave in despues and antes[clave] != despues[clave]
    ]


def cambios_entre(base: Borrador, actual: Borrador) -> list[CambioEditado]:
    """Las celdas que cambiaron del borrador abierto (`base`) al vigente (`actual`), una por celda,
    en el orden metraje, APU, cantidad, parametro y plan (spec §9.3).

    Cada `CambioEditado` lleva objeto, clave de fila, campo y los dos valores como texto. Lo
    arma la hoja, que conoce las claves `esp_*`: `core` no las interpreta. Sin cambios, lista
    vacia (y guardar no hace nada: FR-4).
    """
    return [
        *_cambios_de_metraje(base.espacio, actual.espacio),
        *_cambios_de_apu(base.composiciones, actual.composiciones),
        *_cambios_de_cantidades(base, actual),
        *_cambios_de_parametros(base.parametros, actual.parametros),
        *_cambios_de_plan(base, actual),
    ]


# --- Estado por fila ----------------------------------------------------------------------------

_PREFIJO_ESP = "esp_"


def _claves_de_filas(espacio: Espacio) -> list[str]:
    return (
        [f"esp_ambientes:{a.id}" for a in espacio.ambientes]
        + [f"esp_fuentes:{f.id}" for f in espacio.fuentes]
        + [f"esp_puntos:{p.id}" for p in espacio.puntos]
    )


def _claves_citadas(origen_ids: Iterable[str]) -> list[str]:
    """Las claves `esp_*` de unos `origen_ids`, tambien dentro de un `origen_id` compuesto.

    Un item de la derivacion separa sus fuentes con «;» (y un resumen `+N`); el hallazgo de una
    regla del nucleo cita ese texto entero.
    """
    return [
        trozo.strip()
        for origen in origen_ids
        for trozo in origen.split(";")
        if trozo.strip().startswith(_PREFIJO_ESP)
    ]


def estado_de_filas(espacio: Espacio, informe: InformeAuditoria) -> dict[str, EstadoFila]:
    """El Estado de cada fila editable (ambiente, fuente, punto): el peor hallazgo que la toca.

    La clave es la de `adapters.espacio.clave_esp` (`esp_puntos:P1`). Una fila sin hallazgos es
    `EstadoFila(None, TEXTO_OK)`. Los hallazgos de una fila van agrupados por severidad, de la
    mas grave a la menos, cada severidad con su rotulo una sola vez: `ADVERTENCIA: a; b`.

    Un item sin APU en el catalogo (hallazgo `PENDIENTE` del nucleo, ERROR) no es un error de la
    medida: la fila lo dice aparte, `PENDIENTE: sin APU en el catálogo (AF-SALIDA; ...)`, con las
    partidas que faltan, y va despues del `ERROR:` de medida si lo hay. La severidad de la fila
    sigue siendo la del informe.
    """
    por_fila: dict[str, dict[Severidad, list[str]]] = {}
    sin_apu: dict[str, list[str]] = {}
    for hallazgo in informe.hallazgos:
        for clave in dict.fromkeys(_claves_citadas(hallazgo.origen_ids)):
            if hallazgo.regla == CODIGO_PENDIENTE:
                partida = hallazgo.origen_ids[0]
                if partida not in sin_apu.setdefault(clave, []):
                    sin_apu[clave].append(partida)
                continue
            textos = por_fila.setdefault(clave, {}).setdefault(hallazgo.severidad, [])
            if hallazgo.descripcion not in textos:
                textos.append(hallazgo.descripcion)
    return {
        clave: _estado_de(por_fila.get(clave, {}), sin_apu.get(clave))
        for clave in _claves_de_filas(espacio)
    }


def _estado_de(
    grupos: Mapping[Severidad, Sequence[str]], partidas: Sequence[str] | None
) -> EstadoFila:
    """El Estado de una fila a partir de sus hallazgos por severidad y de sus partidas sin APU."""
    if not grupos and not partidas:
        return EstadoFila(None, TEXTO_OK)
    segmentos = [(s, f"{s.name}: {'; '.join(grupos[s])}") for s in grupos]
    if partidas:
        segmentos.append((Severidad.ERROR, f"{TEXTO_PENDIENTE} ({'; '.join(sorted(partidas))})"))
    # de la mas grave a la menos; a igual severidad la medida va antes que la partida pendiente
    segmentos.sort(key=lambda sg: (-sg[0], sg[1].startswith(TEXTO_PENDIENTE)))
    return EstadoFila(segmentos[0][0], " | ".join(t for _, t in segmentos))


def estado_de_items(
    items: Sequence[ItemComputo], informe: InformeAuditoria
) -> dict[str, EstadoFila]:
    """El Estado de cada renglon del presupuesto, por su clave (`claves_de_items`).

    Un hallazgo toca un item si cita su `origen_id` o si el informe lo atribuye a su partida
    (`InformeAuditoria.partida_de`). Un hallazgo `PENDIENTE` es solo del item que cita (partida y
    origen). Mismo formato que `estado_de_filas`.
    """
    por_origen: dict[str, list[Hallazgo]] = {}
    por_partida: dict[str, list[Hallazgo]] = {}
    pendientes: dict[tuple[str, ...], bool] = {}
    for hallazgo in informe.hallazgos:
        if hallazgo.regla == CODIGO_PENDIENTE:
            pendientes[hallazgo.origen_ids] = True
            continue
        for origen in hallazgo.origen_ids:
            por_origen.setdefault(origen, []).append(hallazgo)
        partida = informe.partida_de(hallazgo)
        if partida is not None:
            por_partida.setdefault(partida, []).append(hallazgo)
    estado: dict[str, EstadoFila] = {}
    for clave, item in zip(claves_de_items(items), items, strict=True):
        grupos: dict[Severidad, list[str]] = {}
        vistos: set[int] = set()
        for hallazgo in [
            *por_origen.get(item.origen_id, ()),
            *por_partida.get(item.codigo_partida, ()),
        ]:
            if id(hallazgo) in vistos:
                continue
            vistos.add(id(hallazgo))
            textos = grupos.setdefault(hallazgo.severidad, [])
            if hallazgo.descripcion not in textos:
                textos.append(hallazgo.descripcion)
        falta_apu = (item.codigo_partida, item.origen_id) in pendientes
        estado[clave] = _estado_de(grupos, [item.codigo_partida] if falta_apu else None)
    return estado


# --- abrir una version guardada -----------------------------------------------------------------

#: Versiones que no copian filas `esp_*`: su espacio es el de su version de origen (spec §5.3).
MOTIVOS_QUE_HEREDAN_EL_ESPACIO = ("restauracion", "cotizacion", "revaloracion")


@dataclass(frozen=True, slots=True)
class VersionAbierta:
    """Lo que `abrir_version` entrega: el borrador de partida y la version tal como se guardo.

    * `borrador`: la version como borrador editable (el espacio efectivo, la copia de sus
      composiciones, sus parametros y su plan, los items que no vienen del espacio y las
      cantidades escritas a mano). Es la base con que `cambios_entre` y `guardar_version`
      comparan lo editado.
    * `guardada`: la version recargada con su informe **reauditado** con R8 a R10 sobre la
      instantanea de su espacio (§8.4): reemplaza los hallazgos guardados de esas reglas.
    * `espacio_de`: el codigo de la version cuyas filas `esp_*` aportan el espacio (la misma, o
      la primera de su cadena de `version_origen`); `None` si ninguna tiene.
    * `instantanea`: lo que se congelo al abrir (UC-15e); `solo_lectura` es True si alguna
      partida no tiene composicion vigente: no se puede recalcular sin cambiar su precio.
    """

    proyecto: str
    codigo: str
    lista: str
    borrador: Borrador
    guardada: ResultadoElaboracion
    espacio_de: str | None
    instantanea: ResultadoInstantanea
    solo_lectura: bool = False


def _modelo(sesion: Session, proyecto: str, codigo: str) -> models.Presupuesto:
    modelo = sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
    ).one_or_none()
    if modelo is None:
        raise HojaInvalida(
            f"El proyecto {proyecto!r} no tiene una version {codigo!r}: elija una de la lista."
        )
    return modelo


def espacio_de_version(sesion: Session, modelo: models.Presupuesto) -> tuple[Espacio, str | None]:
    """El espacio de una version y el codigo de la version que lo aporta (spec §5.3).

    Una version con filas `esp_*` propias lo trae; una creada por restaurar, cotizar o revalorar
    (UC-02) no copia filas y hereda el de su `version_origen`, subiendo por la cadena hasta la
    primera que tenga filas propias. Una version de la hoja (edicion) o elaborada de cero es
    siempre la ultima de la cadena: su espacio, aunque haya quedado vacio, es suyo y no sube.
    """
    actual, visitadas = modelo, set()
    while True:
        propio = cargar_espacio(sesion, actual.id)
        if propio != Espacio():
            return propio, actual.codigo
        origen = sesion.get(models.VersionOrigen, actual.id)
        visitadas.add(actual.id)
        if (
            origen is None
            or origen.origen_id is None
            or origen.motivo not in MOTIVOS_QUE_HEREDAN_EL_ESPACIO
            or origen.origen_id in visitadas
        ):
            return Espacio(), None
        siguiente = sesion.get(models.Presupuesto, origen.origen_id)
        if siguiente is None:
            return Espacio(), None
        actual = siguiente


def _parametros_de_version(modelo: models.Presupuesto) -> ParametrosCosto:
    return ParametrosCosto(
        fcas=modelo.fcas,
        bono_alimentacion=modelo.bono_alimentacion,
        administracion=modelo.administracion,
        utilidad=modelo.utilidad,
    )


def _composiciones_de_la_version(
    sesion: Session, catalogo: Catalogo, modelo: models.Presupuesto
) -> tuple[dict[str, ComposicionAPU], bool]:
    """La copia de las composiciones de la version (instantanea y, solo donde falta, catalogo)
    y si alguna partida valorada quedo sin ellas."""
    composiciones = dict(composiciones_de_version(sesion, modelo))
    completa = True
    for codigo in dict.fromkeys(r.partida.codigo for r in modelo.partidas):
        if codigo in composiciones:
            continue
        try:
            composiciones[codigo] = catalogo.composicion(
                codigo, fecha=modelo.fecha, lista=modelo.lista_precios
            )
        except (KeyError, ValueError, CatalogoIncompleto):
            completa = False
    return composiciones, completa


def _clasificar(
    espacio: Espacio, guardados: Sequence[ItemComputo]
) -> tuple[tuple[ItemComputo, ...], dict[str, Decimal]]:
    """Los items guardados que no vienen del espacio y las cantidades escritas a mano.

    Un item guardado es del espacio si su clave (`partida|origen_id`) es la de uno que deriva el
    espacio; si ademas su cantidad difiere de la derivada, esa cantidad se escribio a mano.
    """
    derivados = items_del_borrador(espacio, TODAS)
    derivada = dict(zip(claves_de_items(derivados), derivados, strict=True))
    base: list[ItemComputo] = []
    escritas: dict[str, Decimal] = {}
    for clave, item in zip(claves_de_items(guardados), guardados, strict=True):
        calculado = derivada.get(clave)
        if calculado is None:
            base.append(item)
        elif item.cantidad != calculado.cantidad:
            escritas[clave] = item.cantidad
    return tuple(base), escritas


def abrir_version(
    sesion: Session,
    catalogo: Catalogo,
    proyecto: str,
    codigo: str,
    *,
    responsable: str = "sistema",
    ahora: datetime | None = None,
) -> VersionAbierta:
    """Abre una version guardada como borrador editable (RF-52), sea de la hoja o no (FR-5).

    1. `asegurar_instantanea`: una version sin instantanea (clinica, TI-001, importadas) la
       crea desde el catalogo vigente si este todavia reproduce su precio, y lo **registra**
       (UC-15e). Es la unica escritura al abrir y se confirma aqui.
    2. Espacio por `espacio_de_version`; composiciones, parametros y plan de la version.
    3. Los items guardados se separan en los del espacio y los de la version, y las cantidades
       diferentes de la derivada son cantidades escritas a mano.
    4. La version se recarga con `REGLAS + reglas_espacio(espacio)`: R8 a R10 se recalculan
       sobre la instantanea del espacio y reemplazan las guardadas (§8.4).

    `HojaInvalida` si la version no existe o ya no se puede reconstruir.
    """
    modelo = _modelo(sesion, proyecto, codigo)
    try:
        instantanea = asegurar_instantanea(
            sesion, proyecto, codigo, catalogo, responsable=responsable, ahora=ahora
        )
        sesion.commit()
        espacio, espacio_de = espacio_de_version(sesion, modelo)
        composiciones, completa = _composiciones_de_la_version(sesion, catalogo, modelo)
        emitida = cargar_elaboracion(sesion, proyecto, codigo, catalogo)
        guardados = [p.item for p in emitida.presupuesto.partidas] + list(emitida.pendientes)
        items_base, escritas = _clasificar(espacio, guardados)
        derivados = items_del_borrador(espacio, TODAS)
        derivada = dict(zip(claves_de_items(derivados), derivados, strict=True))
        cantidades = [
            CantidadEscrita(
                derivada[k].codigo_partida, derivada[k].origen_id, derivada[k].cantidad, v
            )
            for k, v in escritas.items()
        ]
        guardada = cargar_elaboracion(
            sesion,
            proyecto,
            codigo,
            catalogo,
            reglas=(*REGLAS, *reglas_espacio(espacio, cantidades)),
        )
    except (ValueError, CatalogoIncompleto, KeyError) as error:
        sesion.rollback()
        raise HojaInvalida(
            f"No se pudo abrir la version {codigo!r} del proyecto {proyecto!r}: {error}"
        ) from error
    plan = plan_de_version(sesion, modelo)
    borrador = Borrador(
        fecha=emitida.presupuesto.fecha,
        moneda=emitida.presupuesto.moneda,
        espacio=espacio,
        items_base=items_base,
        composiciones=composiciones,
        parametros=_parametros_de_version(modelo),
        plan=None if plan is None else tuple((e, tuple(r)) for e, r in plan),
        cantidades=escritas,
    )
    return VersionAbierta(
        proyecto=proyecto,
        codigo=codigo,
        lista=modelo.lista_precios.nombre,
        borrador=borrador,
        guardada=guardada,
        espacio_de=espacio_de,
        instantanea=instantanea,
        solo_lectura=not completa,
    )


def completar_composiciones(
    catalogo: Catalogo, borrador: Borrador, lista: models.ListaPrecios | None = None
) -> Borrador:
    """El borrador con la composicion de cada partida nueva que el catalogo conoce.

    Editar el espacio puede derivar una partida que la version no tenia: su composicion sale del
    catalogo (con `lista`, o la vigente a la fecha del borrador) y pasa a ser parte de la copia
    de la version. Una partida sin composicion en el catalogo queda pendiente (UC-01 3a).
    """
    nuevas = {
        i.codigo_partida
        for i in items_elaborados(borrador)
        if i.codigo_partida not in borrador.composiciones
    }
    if not nuevas:
        return borrador
    existentes = {p.codigo for p in catalogo.partidas()}
    composiciones = dict(borrador.composiciones)
    for codigo in sorted(nuevas & existentes):
        try:
            composiciones[codigo] = catalogo.composicion(codigo, fecha=borrador.fecha, lista=lista)
        except (KeyError, ValueError, CatalogoIncompleto):
            continue
    return replace(borrador, composiciones=composiciones)


# --- guardar, restaurar y versiones -------------------------------------------------------------


def motivo_para_no_guardar(
    base: Borrador, actual: Borrador, fuente: str, responsable: str
) -> str | None:
    """Por que no se puede guardar ahora, o `None` si se puede (RF-53).

    Sin cambios no hay nada que guardar (FR-4); con cambios, cada guardado exige la fuente del
    cambio y el responsable (spec §9.3).
    """
    if not cambios_entre(base, actual):
        return "No hay cambios para guardar: edite alguna celda primero."
    if not fuente.strip():
        return "Escriba la fuente del cambio: por que se cambia y con que respaldo."
    if not responsable.strip():
        return "Escriba el responsable del cambio: quien lo hace."
    return None


def puede_guardar(base: Borrador, actual: Borrador, fuente: str, responsable: str) -> bool:
    """True si hay cambios y se declararon la fuente y el responsable (`guardar_version`)."""
    return motivo_para_no_guardar(base, actual, fuente, responsable) is None


@dataclass(frozen=True, slots=True)
class VersionGuardada:
    """La version que creo `guardar_version`: su codigo, cuantas celdas registro y su total."""

    codigo: str
    cambios: int
    total: Decimal


def guardar_version(
    sesion: Session,
    catalogo: Catalogo,
    abierta: VersionAbierta,
    borrador: Borrador,
    *,
    fuente: str,
    responsable: str,
    ahora: datetime | None = None,
) -> VersionGuardada | None:
    """Guarda `borrador` como version nueva de la abierta, en UNA sola `Session` (spec §5.3).

    Sin cambios (`cambios_entre` vacio) no hace nada y devuelve `None` (FR-4). Con cambios exige
    `fuente` y `responsable` (`HojaInvalida` antes de tocar la base). En una transaccion:
    `core.budget.edicion.guardar_edicion` crea la version con su informe, la instantanea de sus
    composiciones, su plan y un `RegistroCambio` por celda, y el gancho copia las filas `esp_*` del
    espacio con la clave de la version nueva (`adapters.espacio`). Confirma si todo sale bien; si
    algo falla, deshace todo y propaga el error.
    """
    cambios = cambios_entre(abierta.borrador, borrador)
    if not cambios:
        return None
    motivo = motivo_para_no_guardar(abierta.borrador, borrador, fuente, responsable)
    if motivo is not None:
        raise HojaInvalida(motivo)
    if abierta.solo_lectura:
        raise HojaInvalida(
            "Esta version esta en solo lectura: alguna de sus partidas ya no tiene composicion "
            "vigente en el catalogo, asi que recalcularla cambiaria sus precios."
        )
    try:
        origen = _modelo(sesion, abierta.proyecto, abierta.codigo)
        borrador = completar_composiciones(catalogo, borrador, lista=origen.lista_precios)
        codigo = siguiente_codigo(sesion, abierta.proyecto)
        resultado = elaborar_borrador(borrador, codigo=codigo)
        con_espacio = borrador.espacio != Espacio()
        if con_espacio:
            crear_esquema_espacio(sesion.connection())

        def copiar_espacio(sesion_: Session, version: models.Presupuesto) -> None:
            guardar_espacio(sesion_, version.id, borrador.espacio)

        nueva = guardar_edicion(
            sesion,
            abierta.proyecto,
            abierta.codigo,
            resultado.elaboracion,
            borrador.parametros,
            cambios,
            fuente=fuente,
            responsable=responsable,
            plan=resultado.plan,
            ahora=ahora,
            gancho=copiar_espacio if con_espacio else None,
        )
        sesion.commit()
    except BaseException:
        sesion.rollback()
        raise
    assert nueva is not None  # `cambios` no estaba vacio
    return VersionGuardada(
        codigo=nueva.codigo, cambios=len(cambios), total=resultado.elaboracion.presupuesto.total
    )


def _en_una_transaccion(sesion: Session, accion: Callable[[], str]) -> str:
    """Corre `accion` y confirma; ante cualquier error deshace y, si es un `ValueError` del
    nucleo, lo vuelve `HojaInvalida` con su mismo mensaje."""
    try:
        codigo = accion()
        sesion.commit()
    except HojaInvalida:
        sesion.rollback()
        raise
    except ValueError as error:
        sesion.rollback()
        raise HojaInvalida(str(error)) from error
    except BaseException:
        sesion.rollback()
        raise
    return codigo


def restaurar(
    sesion: Session,
    catalogo: Catalogo,
    proyecto: str,
    codigo: str,
    *,
    fuente: str,
    responsable: str,
    ahora: datetime | None = None,
) -> str:
    """RF-54: crea una version nueva, copia de `codigo`, y devuelve su codigo. Nada se borra.

    La nueva pasa a ser la vigente y su espacio es el de la restaurada (no copia filas `esp_*`).
    """

    def accion() -> str:
        nuevo = siguiente_codigo(sesion, proyecto)
        restaurar_version(
            sesion, proyecto, codigo, nuevo, catalogo,
            fuente=fuente, responsable=responsable, ahora=ahora,
        )  # fmt: skip
        return nuevo

    return _en_una_transaccion(sesion, accion)


def cotizar(
    sesion: Session,
    catalogo: Catalogo,
    proyecto: str,
    codigo_origen: str,
    *,
    insumo: str,
    precio: Decimal,
    proveedor: str,
    numero: str,
    fecha: date,
    responsable: str,
    fuente: str = "",
    ahora: datetime | None = None,
) -> str:
    """RF-56: cotiza `insumo` (su codigo) para el proyecto y devuelve el codigo de la version
    nueva, que referencia la lista del proyecto y conserva el plan y la curva."""

    def accion() -> str:
        nuevo = siguiente_codigo(sesion, proyecto)
        cotizar_insumo(
            sesion, proyecto, codigo_origen, nuevo, catalogo,
            insumo=insumo, precio=precio, proveedor=proveedor, numero=numero, fecha=fecha,
            responsable=responsable, fuente=fuente, ahora=ahora,
        )  # fmt: skip
        return nuevo

    return _en_una_transaccion(sesion, accion)


def retirar_cotizacion(
    sesion: Session,
    catalogo: Catalogo,
    proyecto: str,
    codigo_origen: str,
    *,
    insumo: str,
    fuente: str,
    responsable: str,
    ahora: datetime | None = None,
) -> str:
    """Retira la cotizacion de `insumo` (con su registro) y devuelve el codigo de la version
    nueva, que vuelve al precio de la lista base para ese insumo."""

    def accion() -> str:
        nuevo = siguiente_codigo(sesion, proyecto)
        _retirar_cotizacion(
            sesion, proyecto, codigo_origen, nuevo, catalogo,
            insumo=insumo, fuente=fuente, responsable=responsable, ahora=ahora,
        )  # fmt: skip
        return nuevo

    return _en_una_transaccion(sesion, accion)


def codigo_vigente(sesion: Session, proyecto: str) -> str | None:
    """El codigo de la version vigente del proyecto (la de mayor id no descartada), o `None`."""
    vigente = version_vigente(sesion, proyecto)
    return None if vigente is None else vigente.codigo


@dataclass(frozen=True, slots=True)
class FilaVersion:
    """Una fila del historial: la version, por que se creo, de cual salio y cuanto cambio.

    `motivo` es `""` si se elaboro de cero; `origen` es el codigo de la version de que salio.
    """

    codigo: str
    fecha: date
    motivo: str
    origen: str
    vigente: bool
    descartada: bool
    cambios: int


def historial_de_versiones(sesion: Session, proyecto: str) -> list[FilaVersion]:
    """Todas las versiones del proyecto, de la mas antigua a la mas reciente (el historial solo
    crece, RF-54)."""
    versiones = list(
        sesion.scalars(
            select(models.Presupuesto)
            .join(models.Proyecto)
            .where(models.Proyecto.nombre == proyecto)
            .order_by(models.Presupuesto.id)
        )
    )
    codigos = {v.id: v.codigo for v in versiones}
    descartadas = set(sesion.scalars(select(models.DescarteVersion.presupuesto_id)))
    registros = dict(
        sesion.execute(
            select(models.RegistroCambio.version_resultante_id, func.count())
            .where(models.RegistroCambio.version_resultante_id.in_(codigos))
            .group_by(models.RegistroCambio.version_resultante_id)
        ).all()
    )
    vigente = codigo_vigente(sesion, proyecto)
    filas = []
    for version in versiones:
        origen = sesion.get(models.VersionOrigen, version.id)
        filas.append(
            FilaVersion(
                codigo=version.codigo,
                fecha=version.fecha,
                motivo=origen.motivo if origen is not None else "",
                origen=codigos.get(origen.origen_id, "") if origen is not None else "",
                vigente=version.codigo == vigente,
                descartada=version.id in descartadas,
                cambios=registros.get(version.id, 0),
            )
        )
    return filas


@dataclass(frozen=True, slots=True)
class FilaRegistro:
    """Un `RegistroCambio` como lo muestra la pestana Trazabilidad."""

    objeto: str
    clave: str
    campo: str
    valor_anterior: str
    valor_nuevo: str
    fuente: str
    responsable: str
    fecha_hora: datetime


def registros_de_version(sesion: Session, proyecto: str, codigo: str) -> list[FilaRegistro]:
    """Los registros que produjeron la version, en el orden en que se guardaron."""
    return [
        FilaRegistro(
            r.objeto,
            r.clave,
            r.campo,
            r.valor_anterior,
            r.valor_nuevo,
            r.fuente,
            r.responsable,
            r.fecha_hora,
        )  # fmt: skip
        for r in registros_de_version_core(sesion, _modelo(sesion, proyecto, codigo))
    ]


def tabla_de_trazabilidad(sesion: Session, proyecto: str, codigo: str) -> TablaExportable:
    """La hoja Trazabilidad del Excel de la version (`core.budget.edicion.tabla_trazabilidad`)."""
    return tabla_trazabilidad(sesion, _modelo(sesion, proyecto, codigo))


# --- precios con su origen ----------------------------------------------------------------------

COLUMNAS_PRECIOS = (
    "Insumo",
    "Código",
    "Tipo",
    "Precio",
    "Lista",
    "Moneda",
    "Fecha del precio",
    "Tasa",
    "Fecha de la tasa",
    "Referencia",
    "Cotización",
    "Estado",
)


@dataclass(frozen=True, slots=True)
class FilaPrecio:
    """El origen del precio de un insumo (pestana Precios, RF-56): lista, referencia, fecha,
    moneda original y tasa con su fecha; `estado` marca el que no tiene fuente o fecha."""

    codigo: str
    descripcion: str
    tipo: str
    precio: Decimal
    lista: str
    moneda: str
    fecha: date
    tasa: Decimal | None
    fecha_tasa: date | None
    referencia: str
    cotizacion: str
    alcance: str
    estado: str


def _estado_de_precio(o: OrigenPrecio) -> str:
    avisos = []
    if not o.referencia and not o.cotizacion:
        avisos.append("Sin referencia ni cotización: el precio no tiene fuente")
    if o.tasa is not None and o.fecha_tasa is None:
        avisos.append("La tasa de cambio no declara su fecha")
    return "; ".join(avisos) if avisos else TEXTO_OK


def precios_de_version(sesion: Session, proyecto: str, codigo: str) -> list[FilaPrecio]:
    """El origen de cada precio que usa la version, ordenado por codigo de insumo (§9.6)."""
    return [
        FilaPrecio(
            codigo=o.codigo,
            descripcion=o.descripcion,
            tipo=o.tipo,
            precio=o.precio,
            lista=o.lista,
            moneda=o.moneda,
            fecha=o.fecha_vigencia,
            tasa=o.tasa,
            fecha_tasa=o.fecha_tasa,
            referencia=o.referencia,
            cotizacion=o.cotizacion,
            alcance=o.alcance,
            estado=_estado_de_precio(o),
        )
        for o in origen_de_precios(sesion, _modelo(sesion, proyecto, codigo))
    ]


# --- Excel de la hoja ---------------------------------------------------------------------------

#: Titulo de la hoja de metrajes del Excel y de cada tabla del espacio (spec §9.5).
TITULOS_TABLAS_ESPACIO = {
    "origenes": "Esp origenes",
    "ambientes": "Esp ambientes",
    "fuentes": "Esp fuentes",
    "puntos": "Esp puntos",
    "tramos": "Esp vertices",
}


def tabla_de_precios(precios: Sequence[FilaPrecio]) -> TablaExportable:
    """La hoja Precios: una fila por insumo, con precios y tasas como numeros."""
    return TablaExportable(
        "Precios",
        COLUMNAS_PRECIOS,
        tuple(
            (
                p.descripcion,
                p.codigo,
                p.tipo,
                p.precio,
                p.lista,
                p.moneda,
                p.fecha,
                p.tasa,
                p.fecha_tasa,
                p.referencia,
                p.cotizacion,
                p.estado,
            )  # fmt: skip
            for p in precios
        ),
    )


def tablas_de_espacio(
    espacio: Espacio, derivados: Sequence[ItemComputo], estado: Mapping[str, EstadoFila]
) -> list[TablaExportable]:
    """Las hojas del espacio que `core` no conoce: «Espacio y metrajes» (las cantidades que deriva
    la hoja, con su origen) y una hoja por tabla editable, con el Estado de cada fila."""
    cantidades = TablaExportable(
        "Espacio y metrajes",
        ("Partida", "Descripción", "Unidad", "Cantidad", "Origen"),
        tuple(
            (i.codigo_partida, i.descripcion, i.unidad, i.cantidad, i.origen_id) for i in derivados
        ),
    )
    filas = filas_desde_espacio(espacio)
    tablas = [cantidades]
    for tabla, columnas in COLUMNAS.items():
        con_estado = tabla in TABLAS_CON_ESTADO
        encabezado = (*columnas, "Estado") if con_estado else columnas
        tablas.append(
            TablaExportable(
                TITULOS_TABLAS_ESPACIO[tabla],
                encabezado,
                tuple(
                    (
                        *(fila[c] for c in columnas),
                        *(
                            (
                                estado.get(
                                    f"{TABLAS_CON_ESTADO[tabla]}:{fila['id']}", EstadoFila(None, "")
                                ).texto,
                            )
                            if con_estado
                            else ()
                        ),
                    )
                    for fila in filas[tabla]
                ),
            )
        )
    return tablas


def exportar_excel_hoja(
    ruta: Path,
    resultado: ResultadoHoja,
    borrador: Borrador,
    *,
    trazabilidad: TablaExportable | None = None,
    precios: Sequence[FilaPrecio] = (),
) -> Path:
    """Escribe el libro de la hoja (spec §9.5) con lo que muestra `resultado`: una hoja por
    pestana, mas Trazabilidad y Auditoria, con formulas vivas. Solo se llama al pulsar Exportar.
    """
    extras = [
        *tablas_de_espacio(borrador.espacio, resultado.items, resultado.estado),
        tabla_de_precios(precios),
    ]
    return exportar_hoja(
        resultado.elaboracion.presupuesto,
        resultado.elaboracion.informe,
        ruta,
        borrador.parametros,
        trazabilidad=trazabilidad,
        hojas_extra=extras,
    )


def excel_de_hoja_en_bytes(
    resultado: ResultadoHoja,
    borrador: Borrador,
    *,
    trazabilidad: TablaExportable | None = None,
    precios: Sequence[FilaPrecio] = (),
) -> bytes:
    """El libro de `exportar_excel_hoja` como bytes, para `st.download_button`."""
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = exportar_excel_hoja(
            Path(carpeta) / "hoja.xlsx",
            resultado,
            borrador,
            trazabilidad=trazabilidad,
            precios=precios,
        )
        return ruta.read_bytes()
