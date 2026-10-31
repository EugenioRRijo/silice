"""Costo por tonelada del periodo, convertido y guardado con sus entradas (Tarea 4 del plan vial).

Lee la instalacion (costos vigentes del periodo, entradas y recetas de `produccion/`) y la carpeta
del caso (tasas BCV y la lista de precios vigente), hace la aritmetica con `produccion.costo` y
guarda una instantanea en `prod_calculo`. Nada se sobrescribe: recalcular es otro registro.

Reglas (las decisiones estan en `docs/bitacora/2026-10-30-plan-vial-fase-a.md`, Tarea 4):

- **Guardas (Foco 2)**: si no hay ningun costo mayor que cero (ninguno, todos anulados o todos en
  cero) ni nada que venga del mes anterior, «No hay costos registrados en AAAA-MM.». Ademas:
  agregados sin costos de cantera (su costo seria cero), mezclas sin costos de planta, y ningun
  costo por tonelada en cero o menos.
- **Lo que no tiene quien lo reciba pasa al mes siguiente** (Tarea 4b, pregunta 16): el total de
  la cantera sin agregados o de la planta sin mezcla queda en `pasa_al_mes_siguiente`; un mes con
  costos y sin ninguna produccion tambien se calcula (sin costo por tonelada; no se publica). El
  calculo de M suma a cada centro lo que pasa del **ultimo calculo de M-1** (id mayor; sin
  calculo de M-1 no pasa nada), convertido con la tasa del cierre de M-1 si las monedas difieren,
  y lo anota en `viene_del_mes_anterior` con el calculo de donde vino: recalcular M-1 despues no
  cambia el calculo ya guardado de M. Lo que de nuevo no tiene receptor pasa a M+1 sumado (con los
  costos de donde viene).
- **Agregado propio no producido en el mes** (Tarea 4b, pregunta 15): la mezcla lo toma al costo
  del calculo del periodo anterior mas reciente (y dentro de el, el de id mayor) en la misma moneda
  que lo tenga, anotado en `de_otro_calculo`; nunca de un mes posterior. Sin ninguno, se niega.
- **Que es mezcla**: un producto con receta registrada que rija al ultimo dia del periodo; el
  resto de lo producido son agregados y reciben la cantera (D-V-1: por tonelada, o por pesos). La
  planta va a las mezclas por tonelada.
- **Receta de cada produccion**: la vigente en la fecha de esa entrada (`receta_vigente`), no la
  nota del movimiento; la mezcla del periodo pondera cada receta por sus toneladas.
- **Moneda (Foco 1)**: cada costo en otra moneda se convierte con la tasa BCV del dia exacto de
  su fecha (`aplicacion.tasa_del_dia`). Un componente comprado toma su precio de la lista global
  vigente de la carpeta al ultimo dia del periodo; si esa lista esta en otra moneda, se convierte
  con la **tasa del cierre del mes** (Tarea 4b, pregunta 14: la ultima publicada dentro del mes),
  no con la de su vigencia. Si falta alguna tasa, no se calcula nada y `FaltanTasas` nombra cada
  costo (n.º y fecha), la lista y lo que pasa del mes anterior sin tasa.
- **Instantanea** (version 2; la 1 se sigue leyendo): JSON canonico (claves ordenadas, sin
  espacios, decimales como texto) con `entradas` y `resultado`; su huella es el SHA-256 de ese
  texto. Mismas entradas, misma huella. Se guarda exacto (28 cifras); se redondea solo al
  presentar. La version 2 suma a `entradas` `tasa_del_cierre` (`{valor, fecha, fuente}` o nula si
  no hizo falta convertir lo comprado), `de_otro_calculo` (codigo -> `{costo, calculo, periodo}`) y
  `viene_del_mes_anterior` (centro -> `{total, calculo, periodo, costos, tasa}`), y a `resultado`
  `pasa_al_mes_siguiente` (centro -> `{total, costos}`). `total_cantera` y `total_planta` incluyen
  lo que vino del mes anterior.

Publicar (Tarea 5, `publicar_calculo`): un calculo concreto, ya verificado, pasa a la carpeta como
lista de empresa nueva (alcance `empresa`: `lista_vigente` no la resuelve, asi los calculos
siguientes siguen leyendo lo comprado de la lista global). Cada producto es el insumo `AGP-<codigo>`
(agregado) o `MZP-<codigo>` (mezcla), material en t, dado de alta una sola vez (D-V-2). El precio
es el valor exacto del calculo (no el presentado), con fecha el ultimo dia del periodo y fuente
«Produccion, periodo AAAA-MM, calculo n.º N». Cada calculo se publica **una sola vez** (Tarea 4b,
pregunta 22): `publicar_calculo` registra `prod_publicacion` en la instalacion en la misma
operacion (un segundo intento es `CalculoYaPublicado`, sin escribir nada) y un calculo sin costo
por tonelada no se publica. No hace `commit`: quien llama confirma la carpeta antes que la
instalacion, asi un fallo al escribir la lista no deja la publicacion registrada.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aplicacion.tasa_del_dia import (
    Equivalencia,
    SinTasaDelDia,
    equivalencia_del_cierre,
    equivalencia_del_dia,
    tasa_del_cierre,
)
from core import models
from core.catalog import Catalogo, CatalogoIncompleto
from core.catalog.empresa import PrecioPropio, crear_lista_de_empresa, lista_de_referencia
from core.catalog.moneda import TasaDeclarada
from core.contracts.unidades import unidades_equivalentes
from produccion.costo import (
    ErrorDeCalculo,
    costo_de_mezcla_del_periodo,
    costo_por_tonelada,
    exacto,
)
from produccion.costos import (
    MONEDAS,
    CostoRegistrado,
    costos_del_periodo,
    ultimo_dia_del_mes,
    validar_periodo,
)
from produccion.importacion import abrir_transaccion
from produccion.inventario import entradas_del_periodo
from produccion.modelo import Calculo, PublicacionRegistrada
from produccion.receta import Receta, receta_vigente

__all__ = [
    "VERSION_DE_LA_INSTANTANEA",
    "CalculoGuardado",
    "CalculoInexistente",
    "CalculoYaPublicado",
    "FaltanTasas",
    "Publicacion",
    "calcular_periodo",
    "calculo_guardado",
    "calculos_registrados",
    "descripcion_de_costo_propio",
    "exigir_publicable",
    "lista_base_del_periodo",
    "publicacion_de",
    "publicar_calculo",
    "ultimo_calculo",
]

CERO = Decimal(0)
VERSION_DE_LA_INSTANTANEA = 2
CENTROS = ("cantera", "planta")


class CalculoInexistente(ErrorDeCalculo):
    """No hay un calculo con ese numero: la API lo responde 404."""


class CalculoYaPublicado(ErrorDeCalculo):
    """El calculo ya se publico (pregunta 22): la API lo responde 409 y no se escribe nada."""


class FaltanTasas(ErrorDeCalculo):
    """Falta la tasa BCV de uno o mas montos: no se calcula nada. `faltan` nombra cada uno
    («costo n.º 7 del 07/11/2026», «lista «X» sin tasa del BCV publicada en 2026-11 ...»). El
    encabezado no cambia con la Tarea 4b: la pantalla lo reconoce para listar cada falta."""

    def __init__(self, moneda: str, faltan: tuple[str, ...]) -> None:
        self.faltan = faltan
        super().__init__(
            f"No hay tasa del BCV del mismo día para convertir a {moneda}: {'; '.join(faltan)}. "
            "Cárguela en Índices y vuelva a calcular; no se calculó nada."
        )


@dataclass(frozen=True)
class CalculoGuardado:
    id: int
    periodo: str
    moneda: str
    por_tonelada: dict[str, Decimal]
    huella: str
    usuario: str = ""
    registrado: datetime | None = None
    instantanea: str = field(default="", repr=False)


@dataclass(frozen=True)
class Publicacion:
    """La publicacion de un calculo (pregunta 22): en que carpeta y en que lista quedo."""

    id: int
    calculo_id: int
    caso: str
    lista_id: int
    usuario: str
    registrado: datetime


def _t(valor: Decimal) -> str:
    return format(valor, "f")


def _mes_anterior(periodo: str) -> str:
    anio, mes = validar_periodo(periodo)
    return f"{anio - 1}-12" if mes == 1 else f"{anio:04d}-{mes - 1:02d}"


def _tasa(equivalencia: Equivalencia | None) -> dict[str, str] | None:
    if equivalencia is None:
        return None
    return {
        "valor": _t(equivalencia.tasa),
        "fecha": equivalencia.fecha_tasa.isoformat(),
        "fuente": equivalencia.fuente_tasa,
    }


# --- Lo producido: agregados y mezclas ------------------------------------------------------------


@dataclass
class _Producido:
    toneladas: dict[str, Decimal] = field(default_factory=dict)  # todo, por codigo
    agregados: dict[str, Decimal] = field(default_factory=dict)
    #: por mezcla, (receta, toneladas hechas con ella) por numero de receta
    usos: dict[str, dict[int, tuple[Receta, Decimal]]] = field(default_factory=dict)


def _producido(sesion_ins: Session, periodo: str) -> _Producido:
    """Cada entrada del periodo, clasificada: una mezcla (con receta al cierre) suma a la receta
    vigente en la fecha de esa entrada; lo demas es agregado."""
    cierre = ultimo_dia_del_mes(periodo)
    producido = _Producido()
    es_mezcla: dict[str, bool] = {}
    recetas: dict[tuple[str, date], Receta | None] = {}
    for e in entradas_del_periodo(sesion_ins, periodo):
        producido.toneladas[e.codigo] = producido.toneladas.get(e.codigo, CERO) + e.toneladas
        if e.codigo not in es_mezcla:
            es_mezcla[e.codigo] = receta_vigente(sesion_ins, e.codigo, cierre) is not None
        if not es_mezcla[e.codigo]:
            producido.agregados[e.codigo] = producido.agregados.get(e.codigo, CERO) + e.toneladas
            continue
        clave = (e.codigo, e.fecha)
        if clave not in recetas:
            recetas[clave] = receta_vigente(sesion_ins, e.codigo, e.fecha)
        receta = recetas[clave]
        if receta is None:
            raise ErrorDeCalculo(
                f"La producción de {e.codigo} del {e.fecha:%d/%m/%Y} no tiene receta vigente en "
                "su fecha: registre la receta que regía ese día o corrija la entrada."
            )
        de_la_mezcla = producido.usos.setdefault(e.codigo, {})
        _, antes = de_la_mezcla.get(receta.id, (receta, CERO))
        de_la_mezcla[receta.id] = (receta, antes + e.toneladas)
    return producido


def _exigir_centros(periodo: str, hay: Mapping[str, bool], producido: _Producido) -> None:
    """Cada agregado tiene costo de cantera y cada mezcla costo de planta (sin ellos su costo por
    tonelada saldria corto). Un centro con costo y sin receptor ya no se niega: pasa al mes
    siguiente (pregunta 16)."""
    if producido.agregados and not hay["cantera"]:
        raise ErrorDeCalculo(
            f"No hay costos de cantera en {periodo} para los agregados "
            f"{', '.join(sorted(producido.agregados))}: su costo por tonelada sería cero."
        )
    if producido.usos and not hay["planta"]:
        raise ErrorDeCalculo(
            f"No hay costos de planta en {periodo} para las mezclas "
            f"{', '.join(sorted(producido.usos))}: su costo por tonelada saldría sin la planta."
        )


# --- Lo que viene de otros calculos (Tarea 4b) ----------------------------------------------------


def _de_otro_calculo(
    sesion_ins: Session, periodo: str, moneda: str, producido: _Producido
) -> dict[str, CalculoGuardado]:
    """Por cada agregado propio de una mezcla que no se produjo en `periodo`, el calculo en
    `moneda` que le da costo del periodo anterior mas reciente y, dentro de el, el de id mayor
    (pregunta 15; fila 26 de la bitacora: recalcular septiembre despues de octubre no gana a
    octubre). Nunca uno de un mes posterior. Sin ninguno, `ErrorDeCalculo` que nombra la mezcla y
    el agregado."""
    faltan: dict[str, str] = {}  # agregado -> la primera mezcla que lo usa
    for mezcla, usos in sorted(producido.usos.items()):
        for receta, _ in usos.values():
            for c in receta.componentes:
                if c.tipo == "propio" and c.codigo not in producido.agregados:
                    faltan.setdefault(c.codigo, mezcla)
    if not faltan:
        return {}
    anteriores = [
        _guardado(fila)
        for fila in sesion_ins.scalars(
            select(Calculo)
            .where(Calculo.periodo < periodo, Calculo.moneda == moneda)
            .order_by(Calculo.periodo.desc(), Calculo.id.desc())
        )
    ]
    hallados: dict[str, CalculoGuardado] = {}
    for codigo, mezcla in sorted(faltan.items()):
        hallado = next((c for c in anteriores if codigo in c.por_tonelada), None)
        if hallado is None:
            raise ErrorDeCalculo(
                f"La mezcla {mezcla} usa {codigo}, que no se produjo en {periodo} ni tiene un "
                f"costo calculado antes en {moneda}."
            )
        hallados[codigo] = hallado
    return hallados


def _ultimo_del_mes_anterior(sesion_ins: Session, periodo: str) -> CalculoGuardado | None:
    """El ultimo calculo (id mayor) del mes anterior a `periodo`, verificado, o `None`."""
    fila = sesion_ins.scalar(
        select(Calculo)
        .where(Calculo.periodo == _mes_anterior(periodo))
        .order_by(Calculo.id.desc())
        .limit(1)
    )
    return None if fila is None else _guardado(fila)


def _lo_que_pasa(calculo: CalculoGuardado | None) -> dict[str, Any]:
    """Lo que `calculo` deja para el mes siguiente; un calculo de la version 1 no dejaba nada."""
    if calculo is None:
        return {}
    return json.loads(calculo.instantanea)["resultado"].get("pasa_al_mes_siguiente", {})


# --- Moneda ---------------------------------------------------------------------------------------


def _convertir_costos(
    sesion_caso: Session, costos: list[CostoRegistrado], moneda: str, faltan: list[str]
) -> list[tuple[CostoRegistrado, Decimal, Equivalencia | None]]:
    convertidos: list[tuple[CostoRegistrado, Decimal, Equivalencia | None]] = []
    for r in costos:
        c = r.costo
        if c.moneda == moneda:
            convertidos.append((r, c.monto, None))
            continue
        try:
            equivalencia = equivalencia_del_dia(sesion_caso, c.monto, c.moneda, moneda, c.fecha)
        except SinTasaDelDia:
            faltan.append(f"costo n.º {r.id} del {c.fecha:%d/%m/%Y}")
            continue
        convertidos.append((r, equivalencia.convertido, equivalencia))
    return convertidos


def _convertir_lo_que_viene(
    sesion_caso: Session, anterior: CalculoGuardado | None, moneda: str, faltan: list[str]
) -> dict[str, tuple[Decimal, dict[str, Any]]]:
    """Lo que pasa del calculo `anterior`, por centro, en `moneda`: si la del calculo anterior es
    otra, con la tasa del cierre de su mes. Sin tasa: se anota en `faltan`."""
    viene: dict[str, tuple[Decimal, dict[str, Any]]] = {}
    if anterior is None:
        return viene
    for centro, dato in sorted(_lo_que_pasa(anterior).items()):
        total = Decimal(dato["total"])
        equivalencia: Equivalencia | None = None
        if anterior.moneda != moneda:
            try:
                equivalencia = equivalencia_del_cierre(
                    sesion_caso, total, anterior.moneda, moneda, anterior.periodo
                )
            except SinTasaDelDia:
                faltan.append(
                    f"lo que pasó de {anterior.periodo} ({centro}, cálculo n.º {anterior.id}) "
                    f"sin tasa del BCV publicada en {anterior.periodo} (la del cierre del mes)"
                )
                continue
        valor = total if equivalencia is None else equivalencia.convertido
        viene[centro] = (
            valor,
            {
                "total": _t(valor),
                "calculo": anterior.id,
                "periodo": anterior.periodo,
                "costos": list(dato["costos"]),
                "tasa": _tasa(equivalencia),
            },
        )
    return viene


def _unidades_compradas(producido: _Producido) -> dict[str, set[str]]:
    unidades: dict[str, set[str]] = {}
    for usos in producido.usos.values():
        for receta, _ in usos.values():
            for c in receta.componentes:
                if c.tipo == "comprado":
                    unidades.setdefault(c.codigo, set()).add(c.unidad)
    return unidades


def _precios_comprados(
    sesion_caso: Session,
    unidades: Mapping[str, set[str]],
    periodo: str,
    moneda: str,
    faltan: list[str],
) -> tuple[dict[str, Decimal], dict[str, Any], Equivalencia | None]:
    """Precio de cada componente comprado en la lista global vigente de la carpeta al cierre del
    `periodo`, convertido a `moneda` con la tasa del cierre del mes (pregunta 14), que tambien se
    devuelve (`None` si no hizo falta convertir). Sin lista, sin precio o con otra unidad:
    `ErrorDeCalculo` que nombra los codigos. Sin tasa: se anota en `faltan`."""
    if not unidades:
        return {}, {}, None
    cierre = ultimo_dia_del_mes(periodo)
    codigos = sorted(unidades)
    try:
        lista = Catalogo(sesion_caso).lista_vigente(cierre)
    except CatalogoIncompleto:
        raise ErrorDeCalculo(
            f"No hay lista de precios vigente en la carpeta al {cierre:%d/%m/%Y} para los "
            f"componentes comprados {', '.join(codigos)}."
        ) from None
    filas = {p.insumo.codigo: p for p in lista.precios}
    vigencia = f"«{lista.nombre}» (vigente desde el {lista.fecha_vigencia:%d/%m/%Y})"
    sin_precio = [c for c in codigos if c not in filas]
    if sin_precio:
        raise ErrorDeCalculo(
            f"La lista {vigencia} no trae precio de {', '.join(sin_precio)}: cárguelo antes de "
            "calcular."
        )
    otra_unidad = [
        f"{c} es por {filas[c].insumo.unidad} y la receta lo pide por {u}"
        for c in codigos
        for u in sorted(unidades[c])
        if filas[c].insumo.unidad and not unidades_equivalentes(filas[c].insumo.unidad, u)
    ]
    if otra_unidad:
        raise ErrorDeCalculo(f"En la lista {vigencia}, {'; '.join(otra_unidad)}.")
    precios: dict[str, Decimal] = {}
    detalle: dict[str, Any] = {}
    usada: Equivalencia | None = None
    for codigo in codigos:
        fila = filas[codigo]
        equivalencia: Equivalencia | None = None
        if lista.moneda != moneda:
            try:
                equivalencia = equivalencia_del_cierre(
                    sesion_caso, fila.precio, lista.moneda, moneda, periodo
                )
            except SinTasaDelDia:
                faltan.append(
                    f"lista «{lista.nombre}» vigente desde el {lista.fecha_vigencia:%d/%m/%Y} "
                    f"sin tasa del BCV publicada en {periodo} (la del cierre del mes)"
                )
                return {}, {}, None
            usada = equivalencia
        precios[codigo] = fila.precio if equivalencia is None else equivalencia.convertido
        detalle[codigo] = {
            "precio": _t(fila.precio),
            "moneda": lista.moneda,
            "unidad": fila.insumo.unidad,
            "convertido": _t(precios[codigo]),
            "tasa": _tasa(equivalencia),
            "lista": {
                "id": lista.id,
                "nombre": lista.nombre,
                "fecha_vigencia": lista.fecha_vigencia.isoformat(),
            },
        }
    return precios, detalle, usada


# --- El calculo -----------------------------------------------------------------------------------


def _receta_json(receta: Receta, toneladas: Decimal) -> dict[str, Any]:
    return {
        "id": receta.id,
        "producto": receta.producto,
        "fuente": receta.fuente,
        "vigente_desde": receta.vigente_desde.isoformat(),
        "toneladas": _t(toneladas),
        "componentes": [
            {
                "codigo": c.codigo,
                "cantidad_por_t": _t(c.cantidad_por_t),
                "unidad": c.unidad,
                "tipo": c.tipo,
            }
            for c in receta.componentes
        ],
    }


def _costo_json(r: CostoRegistrado, convertido: Decimal, eq: Equivalencia | None) -> dict:
    c = r.costo
    return {
        "id": r.id,
        "centro": c.centro,
        "concepto": c.concepto,
        "monto": _t(c.monto),
        "moneda": c.moneda,
        "fecha": c.fecha.isoformat(),
        "fuente": c.fuente,
        "convertido": _t(convertido),
        "tasa": _tasa(eq),
    }


def _validar_entrada(periodo: str, moneda: str, usuario: str) -> None:
    validar_periodo(periodo)
    if moneda not in MONEDAS:
        raise ErrorDeCalculo("La moneda del cálculo debe ser Bs o USD.")
    if not usuario.strip():
        raise ErrorDeCalculo("Falta el usuario que calcula.")


def calcular_periodo(
    sesion_ins: Session,
    sesion_caso: Session,
    periodo: str,
    moneda: str,
    *,
    pesos: Mapping[str, Decimal] | None = None,
    usuario: str,
    ahora: datetime,
) -> CalculoGuardado:
    """Calcula el costo por tonelada de cada producto del periodo en `moneda` y lo guarda con sus
    entradas, lo que vino del mes anterior y lo que pasa al siguiente. Todo se valida y convierte
    antes de escribir: un error no deja nada."""
    _validar_entrada(periodo, moneda, usuario)
    costos = costos_del_periodo(sesion_ins, periodo)
    producido = _producido(sesion_ins, periodo)
    anterior = _ultimo_del_mes_anterior(sesion_ins, periodo)
    pasa_de_antes = _lo_que_pasa(anterior)
    hay = {
        centro: any(r.costo.monto > CERO for r in costos if r.costo.centro == centro)
        or Decimal(pasa_de_antes.get(centro, {"total": "0"})["total"]) > CERO
        for centro in CENTROS
    }
    if not any(hay.values()):
        raise ErrorDeCalculo(f"No hay costos registrados en {periodo}.")
    _exigir_centros(periodo, hay, producido)
    if pesos is not None and not producido.agregados:
        raise ErrorDeCalculo(
            f"Se pidió el reparto de la cantera por pesos, pero en {periodo} no se produjo "
            "ningún agregado."
        )
    de_otro = _de_otro_calculo(sesion_ins, periodo, moneda, producido)

    faltan: list[str] = []
    convertidos = _convertir_costos(sesion_caso, costos, moneda, faltan)
    viene = _convertir_lo_que_viene(sesion_caso, anterior, moneda, faltan)
    precios, detalle_precios, cierre_usado = _precios_comprados(
        sesion_caso, _unidades_compradas(producido), periodo, moneda, faltan
    )
    if faltan:
        raise FaltanTasas(moneda, tuple(faltan))

    def total(centro: str) -> Decimal:
        del_mes = (v for r, v, _ in convertidos if r.costo.centro == centro)
        de_antes = viene[centro][0] if centro in viene else CERO
        return exacto(lambda: sum(del_mes, CERO) + de_antes)

    cantera, planta = total("cantera"), total("planta")
    por_tonelada: dict[str, Decimal] = {}
    if producido.agregados:
        por_tonelada |= costo_por_tonelada(cantera, producido.agregados, pesos=pesos)
    planta_por_t: Decimal | None = None
    if producido.usos:
        mezclas = {m: sum((t for _, t in u.values()), CERO) for m, u in producido.usos.items()}
        planta_por_t = costo_por_tonelada(planta, mezclas)[next(iter(mezclas))]
        propios = por_tonelada | {c: calc.por_tonelada[c] for c, calc in de_otro.items()}
        for mezcla, usos in sorted(producido.usos.items()):
            por_tonelada[mezcla] = costo_de_mezcla_del_periodo(
                [usos[i] for i in sorted(usos)], propios, precios, planta_por_t
            )
    en_cero = sorted(c for c, v in por_tonelada.items() if not v > CERO)
    if en_cero:
        raise ErrorDeCalculo(
            f"El costo por tonelada de {', '.join(en_cero)} en {periodo} da cero: revise los "
            "costos y los precios; no se guardó nada."
        )
    sin_receptor = {"cantera": not producido.agregados, "planta": not producido.usos}
    pasa = {
        centro: {
            "total": _t(valor),
            "costos": (viene[centro][1]["costos"] if centro in viene else [])
            + [r.id for r, _, _ in convertidos if r.costo.centro == centro],
        }
        for centro, valor in (("cantera", cantera), ("planta", planta))
        if sin_receptor[centro] and valor > CERO
    }

    entradas = {
        "version": VERSION_DE_LA_INSTANTANEA,
        "periodo": periodo,
        "moneda": moneda,
        "reparto_cantera": "por tonelada" if pesos is None else "por pesos",
        "pesos": None if pesos is None else {c: _t(p) for c, p in pesos.items()},
        "fecha_de_la_lista": ultimo_dia_del_mes(periodo).isoformat(),
        "costos": [_costo_json(r, v, eq) for r, v, eq in convertidos],
        "producido": {c: _t(t) for c, t in producido.toneladas.items()},
        "agregados": sorted(producido.agregados),
        "recetas": [
            _receta_json(receta, toneladas)
            for _, usos in sorted(producido.usos.items())
            for receta, toneladas in (usos[i] for i in sorted(usos))
        ],
        "precios_comprados": detalle_precios,
        "tasa_del_cierre": _tasa(cierre_usado),
        "de_otro_calculo": {
            codigo: {
                "costo": _t(calc.por_tonelada[codigo]),
                "calculo": calc.id,
                "periodo": calc.periodo,
            }
            for codigo, calc in de_otro.items()
        },
        "viene_del_mes_anterior": {centro: dato for centro, (_, dato) in viene.items()},
    }
    resultado = {
        "total_cantera": _t(cantera),
        "total_planta": _t(planta),
        "planta_por_t": None if planta_por_t is None else _t(planta_por_t),
        "por_tonelada": {c: _t(v) for c, v in por_tonelada.items()},
        "pasa_al_mes_siguiente": pasa,
    }
    texto = json.dumps(
        {"entradas": entradas, "resultado": resultado},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    fila = Calculo(
        periodo=periodo,
        moneda=moneda,
        huella=hashlib.sha256(texto.encode("utf-8")).hexdigest(),
        instantanea=texto,
        usuario=usuario,
        registrado=ahora,
    )
    sesion_ins.add(fila)
    sesion_ins.flush()
    return _guardado(fila)


# --- Leer lo guardado -----------------------------------------------------------------------------


def _guardado(fila: Calculo) -> CalculoGuardado:
    """El calculo de la fila, comprobando que su instantanea es la de su huella. Periodo y moneda
    salen de la instantanea verificada; las columnas (que la huella no cubre y solo sirven para
    buscar) deben decir lo mismo."""
    if hashlib.sha256(fila.instantanea.encode("utf-8")).hexdigest() != fila.huella:
        raise ErrorDeCalculo(
            f"El cálculo n.º {fila.id} fue alterado: su huella no coincide con lo guardado."
        )
    datos = json.loads(fila.instantanea)
    entradas, resultado = datos["entradas"], datos["resultado"]
    if (fila.periodo, fila.moneda) != (entradas["periodo"], entradas["moneda"]):
        raise ErrorDeCalculo(
            f"El cálculo n.º {fila.id} fue alterado: su período o su moneda no son los de su "
            "instantánea."
        )
    return CalculoGuardado(
        id=fila.id,
        periodo=entradas["periodo"],
        moneda=entradas["moneda"],
        por_tonelada={c: Decimal(v) for c, v in resultado["por_tonelada"].items()},
        huella=fila.huella,
        usuario=fila.usuario,
        registrado=fila.registrado,
        instantanea=fila.instantanea,
    )


def calculo_guardado(sesion_ins: Session, calculo_id: int) -> CalculoGuardado:
    """El calculo con ese numero; `CalculoInexistente` si no hay ninguno."""
    fila = sesion_ins.get(Calculo, calculo_id)
    if fila is None:
        raise CalculoInexistente("No existe ese cálculo. Actualice la lista.")
    return _guardado(fila)


def _publicacion(fila: PublicacionRegistrada) -> Publicacion:
    return Publicacion(
        id=fila.id,
        calculo_id=fila.calculo_id,
        caso=fila.caso,
        lista_id=fila.lista_id,
        usuario=fila.usuario,
        registrado=fila.registrado,
    )


def publicacion_de(sesion_ins: Session, calculo_id: int) -> Publicacion | None:
    """La publicacion del calculo `calculo_id`, o `None` si no se ha publicado."""
    fila = sesion_ins.scalar(
        select(PublicacionRegistrada).where(PublicacionRegistrada.calculo_id == calculo_id)
    )
    return None if fila is None else _publicacion(fila)


def calculos_registrados(
    sesion_ins: Session, periodo: str | None = None
) -> list[tuple[CalculoGuardado, Publicacion | None]]:
    """Los calculos (de `periodo`, si se da), del mas reciente al mas viejo, cada uno verificado
    contra su huella (uno alterado es `ErrorDeCalculo`) y con su publicacion, si la tiene."""
    consulta = select(Calculo).order_by(Calculo.id.desc())
    if periodo is not None:
        validar_periodo(periodo)
        consulta = consulta.where(Calculo.periodo == periodo)
    calculos = [_guardado(fila) for fila in sesion_ins.scalars(consulta)]
    ids = [c.id for c in calculos]
    publicaciones = {
        fila.calculo_id: _publicacion(fila)
        for fila in sesion_ins.scalars(
            select(PublicacionRegistrada).where(PublicacionRegistrada.calculo_id.in_(ids))
        )
    }
    return [(c, publicaciones.get(c.id)) for c in calculos]


def ultimo_calculo(sesion_ins: Session, producto: str) -> CalculoGuardado | None:
    """El calculo mas reciente (mayor numero) que da costo por tonelada a `producto`, o `None`."""
    for fila in sesion_ins.scalars(select(Calculo).order_by(Calculo.id.desc())):
        calculo = _guardado(fila)
        if producto in calculo.por_tonelada:
            return calculo
    return None


# --- Publicar al catalogo -------------------------------------------------------------------------

#: El largo del codigo de un insumo del catalogo (`Insumo.codigo`).
LARGO_DEL_CODIGO = 20
PREFIJO_DE_AGREGADO = "AGP-"
PREFIJO_DE_MEZCLA = "MZP-"


def descripcion_de_costo_propio(codigo: str) -> str:
    """La descripcion del insumo propio `AGP-<producto>` o `MZP-<producto>`: la que se le da al
    publicar y, por tanto, la de la linea del APU que lo usa (la conciliacion CV3 la reconoce)."""
    for prefijo, tipo in ((PREFIJO_DE_AGREGADO, "agregado"), (PREFIJO_DE_MEZCLA, "mezcla")):
        if codigo.startswith(prefijo):
            return f"Costo propio de {tipo} {codigo[len(prefijo) :]}"
    raise ValueError(
        f"{codigo!r} no es un insumo de costo propio: debe empezar por "
        f"{PREFIJO_DE_AGREGADO!r} o {PREFIJO_DE_MEZCLA!r}."
    )


def _exigir_insumo_propio(caso: Session, codigo: str) -> models.Insumo | None:
    """El insumo propio de ese codigo si ya existe; si es de otro tipo o unidad, se niega: publicar
    a un insumo ajeno confundiria el catalogo. Solo lee."""
    insumo = caso.scalar(select(models.Insumo).where(models.Insumo.codigo == codigo))
    if insumo is not None and (insumo.tipo, insumo.unidad) != ("material", "t"):
        raise ErrorDeCalculo(
            f"El insumo {codigo} del catálogo no es un material en t: no se puede publicar ahí."
        )
    return insumo


def lista_base_del_periodo(sesion_caso: Session, calculo: CalculoGuardado) -> models.ListaPrecios:
    """La lista global vigente de la carpeta al ultimo dia del periodo: la base natural de la lista
    que se publica. Sin ninguna, `ErrorDeCalculo`."""
    cierre = ultimo_dia_del_mes(calculo.periodo)
    try:
        return Catalogo(sesion_caso).lista_vigente(cierre)
    except CatalogoIncompleto:
        raise ErrorDeCalculo(
            f"No hay lista de precios vigente en la carpeta al {cierre:%d/%m/%Y}: cárguela antes "
            "de publicar el costo propio."
        ) from None


def _tasa_de_la_base(
    sesion_caso: Session, base: models.ListaPrecios, calculo: CalculoGuardado
) -> TasaDeclarada:
    """La tasa del cierre del mes del calculo (pregunta 14: la misma con que el calculo convirtio
    lo comprado). Sin ella, `SinTasaDelDia` que nombra la lista y el mes."""
    try:
        return tasa_del_cierre(sesion_caso, calculo.periodo, calculo.moneda)
    except SinTasaDelDia:
        raise SinTasaDelDia(
            f"No hay tasa del BCV publicada en {calculo.periodo} (hace falta la del cierre del "
            f"mes) para llevar la lista «{base.nombre}» a {calculo.moneda}. Cárguela en Índices y "
            "vuelva a publicar; no se publicó nada."
        ) from None


def exigir_publicable(sesion_ins: Session, calculo: CalculoGuardado) -> None:
    """Un calculo sin costo por tonelada (un mes sin produccion) no se publica; uno ya publicado
    tampoco (`CalculoYaPublicado`, pregunta 22). Solo lee."""
    if not calculo.por_tonelada:
        raise ErrorDeCalculo("Este cálculo no tiene costos por tonelada que publicar.")
    previa = publicacion_de(sesion_ins, calculo.id)
    if previa is not None:
        raise CalculoYaPublicado(
            f"El cálculo n.º {calculo.id} ya se publicó en la lista n.º {previa.lista_id}."
        )


def publicar_calculo(
    sesion_caso: Session,
    calculo: CalculoGuardado,
    *,
    sesion_ins: Session,
    nombre_del_caso: str,
    base: models.ListaPrecios,
    empresa_nombre: str,
    empresa_rif: str,
    usuario: str,
    ahora: datetime,
) -> models.ListaPrecios:
    """Publica el costo por tonelada de `calculo` como lista de empresa nueva sobre `base` y lo
    registra en `prod_publicacion` de `sesion_ins` (una sola vez por calculo).

    `calculo` es lo que devuelve `calculo_guardado` (huella verificada): su periodo y su moneda son
    los de la instantanea. La lista copia `base` (convertida con la tasa del cierre del mes del
    calculo, si esta en otra moneda) y pone encima un precio por producto. Todo se valida antes de
    escribir. No hace `commit` en ninguna de las dos bases: quien llama confirma primero la carpeta
    y despues la instalacion. Nunca toca una lista anterior."""
    if not (empresa_nombre.strip() and empresa_rif.strip() and usuario.strip()):
        raise ErrorDeCalculo("Faltan el nombre y el RIF de la empresa y el usuario que publica.")
    if not nombre_del_caso.strip():
        raise ErrorDeCalculo("Falta la carpeta de trabajo donde se publica.")
    exigir_publicable(sesion_ins, calculo)
    cierre = ultimo_dia_del_mes(calculo.periodo)
    es_agregado = set(json.loads(calculo.instantanea)["entradas"]["agregados"])
    codigos = {
        producto: (PREFIJO_DE_AGREGADO if producto in es_agregado else PREFIJO_DE_MEZCLA) + producto
        for producto in sorted(calculo.por_tonelada)
    }
    largos = [c for c in codigos.values() if len(c) > LARGO_DEL_CODIGO]
    if largos:
        raise ErrorDeCalculo(
            f"El código de insumo {', '.join(largos)} pasa de {LARGO_DEL_CODIGO} caracteres: "
            "use un código de material más corto."
        )
    tasa_base = None
    if base.moneda != calculo.moneda:
        tasa_base = _tasa_de_la_base(sesion_caso, base, calculo)
    fuente = f"Producción, período {calculo.periodo}, cálculo n.º {calculo.id}"
    existentes = {c: _exigir_insumo_propio(sesion_caso, c) for c in codigos.values()}
    propios = []
    for producto, codigo in codigos.items():
        insumo = existentes[codigo]
        if insumo is None:
            insumo = models.Insumo(
                codigo=codigo,
                tipo="material",
                descripcion=descripcion_de_costo_propio(codigo),
                unidad="t",
            )
            sesion_caso.add(insumo)
            sesion_caso.flush()
        propios.append(
            PrecioPropio(
                insumo.id,
                calculo.por_tonelada[producto],
                cierre,
                fuente,
                moneda_original=calculo.moneda,
            )
        )
    publicado = (
        f"publicado por {usuario.strip()} el {ahora:%d/%m/%Y %H:%M}; huella {calculo.huella[:16]}"
    )
    lista = crear_lista_de_empresa(
        sesion_caso,
        empresa_nombre,
        empresa_rif,
        base,
        propios,
        moneda=calculo.moneda,
        fecha=cierre,
        fuente=f"{fuente}; {publicado}",
        referencia=lista_de_referencia(sesion_caso),
        nombre=f"Costo propio {calculo.periodo}, cálculo n.º {calculo.id}",
        tasa_base=tasa_base,
    )
    _registrar_publicacion(sesion_ins, calculo, nombre_del_caso, lista.id, usuario, ahora)
    return lista


def _registrar_publicacion(
    sesion_ins: Session,
    calculo: CalculoGuardado,
    nombre_del_caso: str,
    lista_id: int,
    usuario: str,
    ahora: datetime,
) -> None:
    """Anota la publicacion. Si otra del mismo calculo gano la carrera despues de la
    comprobacion, el `unique` de `calculo_id` frena esta: se deshace solo su savepoint y sale
    `CalculoYaPublicado` con la lista de la otra (la API: 409, sin confirmar la carpeta)."""
    abrir_transaccion(sesion_ins)
    try:
        with sesion_ins.begin_nested():
            sesion_ins.add(
                PublicacionRegistrada(
                    calculo_id=calculo.id,
                    caso=nombre_del_caso.strip(),
                    lista_id=lista_id,
                    usuario=usuario.strip(),
                    registrado=ahora,
                )
            )
            sesion_ins.flush()
    except IntegrityError:
        previa = publicacion_de(sesion_ins, calculo.id)
        donde = "" if previa is None else f" en la lista n.º {previa.lista_id}"
        raise CalculoYaPublicado(f"El cálculo n.º {calculo.id} ya se publicó{donde}.") from None
