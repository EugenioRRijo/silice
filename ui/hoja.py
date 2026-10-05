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
   el `Espacio` inmutable es la instantanea que reciben R8 y R9 (DA-SF-8).
3. **Estado por fila** (RF-55). `estado_de_filas` asigna a cada fila editable el peor hallazgo que
   la toca, por las claves `esp_*` que los hallazgos citan en `origen_ids` (tambien dentro del
   `origen_id` compuesto de un item, que separa sus fuentes con «;»). Las advertencias de una misma
   fila van en un solo texto: R8 marca una por origen supuesto y, sin agrupar, el baño correcto
   del ejemplo pintaria cinco lineas.

Un presupuesto sin espacio (la clinica, TI-001) abre igual que antes de la hoja (FR-5): espacio
vacio, ningun item derivado, solo `items_base`; R8 y R9 se declaran evaluadas sin hallazgos. Solo
agua por ahora. **No persiste**: guardar una version es SF3.

Sin Streamlit, sin `pandas` y sin `ui.caso`; lo vigila
`tests/unit/test_arquitectura.py::test_ui_respeta_sus_importaciones_prohibidas`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from adapters.espacio import (
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
    derivar,
)
from adapters.espacio.reglas import reglas_espacio
from core.budget import CODIGO_PENDIENTE, ResultadoElaboracion, elaborar, plan_secuencial
from core.budget.presupuesto import MONEDA_POR_DEFECTO
from core.catalog import Catalogo
from core.contracts import ComposicionAPU, ItemComputo, ParametrosCosto, Severidad
from core.verification import REGLAS
from ui.composicion import ComposicionInvalida, decimal_desde_texto, texto_de_celda

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from core.budget import GeneradorPlan, PeriodoPlan
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
    """Lo que la pantalla pinta: los items derivados, la elaboracion y el Estado por fila."""

    items: list[ItemComputo]
    elaboracion: ResultadoElaboracion
    estado: dict[str, EstadoFila]


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
    propuestos = [
        r for r in base.recorridos if r.modo is ModoRecorrido.PROPUESTO and r.id not in nombres
    ]
    try:
        return Espacio(
            origenes=tuple(_construir("origenes", filas.get("origenes", ()), _origen)),
            ambientes=tuple(_construir("ambientes", filas.get("ambientes", ()), _ambiente)),
            fuentes=tuple(_construir("fuentes", filas.get("fuentes", ()), _fuente)),
            circuitos=base.circuitos,
            puntos=tuple(_construir("puntos", filas.get("puntos", ()), _punto)),
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


def items_del_borrador(espacio: Espacio, especialidad: str) -> list[ItemComputo]:
    """Los `ItemComputo` que deriva el borrador para una especialidad (vacio si no hay espacio)."""
    return derivar(espacio, especialidad)


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
    especialidad: str = Especialidad.AGUA.value,
    items_base: Sequence[ItemComputo] = (),
    parametros: ParametrosCosto | None = None,
    moneda: str = MONEDA_POR_DEFECTO,
    plan: Sequence[PeriodoPlan] | GeneradorPlan = plan_secuencial,
) -> ResultadoHoja:
    """Deriva, elabora y audita el borrador: `REGLAS + reglas_espacio(espacio)`, siempre.

    `items_base` son los items de la version que no vienen del espacio (la clinica, TI-001, o las
    cantidades escritas a mano): se elaboran junto a los derivados. Con espacio vacio y sin
    `items_base` el presupuesto sale vacio y el Estado, `{}` (FR-1).
    """
    derivados = items_del_borrador(espacio, especialidad)
    elaboracion = elaborar(
        [*items_base, *derivados],
        composiciones,
        parametros if parametros is not None else ParametrosCosto(),
        codigo=codigo,
        fecha=fecha,
        moneda=moneda,
        plan=plan,
        reglas=(*REGLAS, *reglas_espacio(espacio)),
    )
    return ResultadoHoja(
        items=derivados,
        elaboracion=elaboracion,
        estado=estado_de_filas(espacio, elaboracion.informe),
    )


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
    estado: dict[str, EstadoFila] = {}
    for clave in _claves_de_filas(espacio):
        grupos = por_fila.get(clave, {})
        partidas = sin_apu.get(clave)
        if not grupos and not partidas:
            estado[clave] = EstadoFila(None, TEXTO_OK)
            continue
        segmentos = [(s, f"{s.name}: {'; '.join(grupos[s])}") for s in grupos]
        if partidas:
            segmentos.append(
                (Severidad.ERROR, f"{TEXTO_PENDIENTE} ({'; '.join(sorted(partidas))})")
            )
        # de la mas grave a la menos; a igual severidad la medida va antes que la partida pendiente
        segmentos.sort(key=lambda sg: (-sg[0], sg[1].startswith(TEXTO_PENDIENTE)))
        estado[clave] = EstadoFila(segmentos[0][0], " | ".join(t for _, t in segmentos))
    return estado
