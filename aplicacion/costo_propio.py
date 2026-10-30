"""Costo por tonelada del periodo, convertido y guardado con sus entradas (Tarea 4 del plan vial).

Lee la instalacion (costos vigentes del periodo, entradas y recetas de `produccion/`) y la carpeta
del caso (tasas BCV y la lista de precios vigente), hace la aritmetica con `produccion.costo` y
guarda una instantanea en `prod_calculo`. Nada se sobrescribe: recalcular es otro registro.

Reglas (las decisiones estan en `docs/bitacora/2026-10-30-plan-vial-fase-a.md`, Tarea 4):

- **Guardas (Foco 2)**: si la suma de los costos vigentes es cero (ninguno, todos anulados o todos
  en cero) «No hay costos registrados en AAAA-MM.»; sin entradas, «No hubo producción en AAAA-MM.».
  Ademas: costos de cantera sin agregados que los reciban, agregados sin costos de cantera (su costo
  seria cero), costos de planta sin mezcla, y ningun costo por tonelada publicado en cero o menos.
- **Que es mezcla**: un producto con receta registrada que rija al ultimo dia del periodo; el
  resto de lo producido son agregados y reciben la cantera (D-V-1: por tonelada, o por pesos). La
  planta va a las mezclas por tonelada.
- **Receta de cada produccion**: la vigente en la fecha de esa entrada (`receta_vigente`), no la
  nota del movimiento; la mezcla del periodo pondera cada receta por sus toneladas.
- **Moneda (Foco 1)**: cada costo en otra moneda se convierte con la tasa BCV del dia exacto de
  su fecha (`aplicacion.tasa_del_dia`). Un componente comprado toma su precio de la lista global
  vigente de la carpeta al ultimo dia del periodo; si esa lista esta en otra moneda, se convierte
  con la tasa del dia de su `fecha_vigencia` (la fecha del precio). Si falta alguna tasa, no se
  calcula nada y `FaltanTasas` nombra cada costo (n.º y fecha) y la lista sin tasa.
- **Instantanea**: JSON canonico (claves ordenadas, sin espacios, decimales como texto) con
  `entradas` y `resultado`; su huella es el SHA-256 de ese texto. Mismas entradas, misma huella. Se
  guarda exacto (28 cifras); se redondea solo al presentar.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.tasa_del_dia import Equivalencia, SinTasaDelDia, equivalencia_del_dia
from core.catalog import Catalogo, CatalogoIncompleto
from core.contracts.unidades import unidades_equivalentes
from produccion.costo import (
    ErrorDeCalculo,
    costo_de_mezcla_del_periodo,
    costo_por_tonelada,
    exacto,
)
from produccion.costos import MONEDAS, CostoRegistrado, costos_del_periodo, validar_periodo
from produccion.inventario import entradas_del_periodo
from produccion.modelo import Calculo
from produccion.receta import Receta, receta_vigente

__all__ = [
    "CalculoGuardado",
    "CalculoInexistente",
    "FaltanTasas",
    "calcular_periodo",
    "calculo_guardado",
    "ultimo_calculo",
]

CERO = Decimal(0)
VERSION_DE_LA_INSTANTANEA = 1


class CalculoInexistente(ErrorDeCalculo):
    """No hay un calculo con ese numero: la API lo responde 404."""


class FaltanTasas(ErrorDeCalculo):
    """Falta la tasa BCV del dia de uno o mas montos: no se calcula nada. `faltan` nombra cada
    uno («costo n.º 7 del 07/11/2026», «lista «X» vigente desde el 01/11/2026»)."""

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


def _t(valor: Decimal) -> str:
    return format(valor, "f")


def _ultimo_dia(periodo: str) -> date:
    anio, mes = validar_periodo(periodo)
    return date(anio + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)


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
    cierre = _ultimo_dia(periodo)
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


def _exigir_centros(periodo: str, costos: list[CostoRegistrado], producido: _Producido) -> None:
    """Cada centro con costo tiene a quien cargarlo y cada agregado tiene costo de cantera."""
    hay = {
        centro: any(r.costo.monto > CERO for r in costos if r.costo.centro == centro)
        for centro in ("cantera", "planta")
    }
    if hay["cantera"] and not producido.agregados:
        raise ErrorDeCalculo(
            f"Hay costos de cantera en {periodo} pero no se produjo ningún agregado: no hay a "
            "quién repartirlos."
        )
    if producido.agregados and not hay["cantera"]:
        raise ErrorDeCalculo(
            f"No hay costos de cantera en {periodo} para los agregados "
            f"{', '.join(sorted(producido.agregados))}: su costo por tonelada sería cero."
        )
    if hay["planta"] and not producido.usos:
        raise ErrorDeCalculo(
            f"Hay costos de planta en {periodo} pero no se produjo mezcla: no hay a quién "
            "cargarlos."
        )
    for mezcla, usos in producido.usos.items():
        for receta, _ in usos.values():
            for c in receta.componentes:
                if c.tipo == "propio" and c.codigo not in producido.agregados:
                    raise ErrorDeCalculo(
                        f"La mezcla {mezcla} (receta n.º {receta.id}) usa {c.codigo}, que no se "
                        f"produjo en {periodo}: no tiene costo propio del periodo."
                    )


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
    cierre: date,
    moneda: str,
    faltan: list[str],
) -> tuple[dict[str, Decimal], dict[str, Any]]:
    """Precio de cada componente comprado en la lista global vigente de la carpeta al `cierre`,
    convertido a `moneda` con la tasa del dia de la vigencia de la lista. Sin lista, sin precio o
    con otra unidad: `ErrorDeCalculo` que nombra los codigos. Sin tasa: se anota en `faltan`."""
    if not unidades:
        return {}, {}
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
    for codigo in codigos:
        fila = filas[codigo]
        equivalencia: Equivalencia | None = None
        if lista.moneda != moneda:
            try:
                equivalencia = equivalencia_del_dia(
                    sesion_caso, fila.precio, lista.moneda, moneda, lista.fecha_vigencia
                )
            except SinTasaDelDia:
                faltan.append(
                    f"lista «{lista.nombre}» vigente desde el {lista.fecha_vigencia:%d/%m/%Y}"
                )
                return {}, {}
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
    return precios, detalle


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
    entradas. Todo se valida y convierte antes de escribir: un error no deja nada."""
    _validar_entrada(periodo, moneda, usuario)
    costos = costos_del_periodo(sesion_ins, periodo)
    if sum((r.costo.monto for r in costos), CERO) == CERO:
        raise ErrorDeCalculo(f"No hay costos registrados en {periodo}.")
    producido = _producido(sesion_ins, periodo)
    if not producido.toneladas:
        raise ErrorDeCalculo(f"No hubo producción en {periodo}.")
    _exigir_centros(periodo, costos, producido)

    faltan: list[str] = []
    convertidos = _convertir_costos(sesion_caso, costos, moneda, faltan)
    precios, detalle_precios = _precios_comprados(
        sesion_caso, _unidades_compradas(producido), _ultimo_dia(periodo), moneda, faltan
    )
    if faltan:
        raise FaltanTasas(moneda, tuple(faltan))

    def total(centro: str) -> Decimal:
        return exacto(lambda: sum((v for r, v, _ in convertidos if r.costo.centro == centro), CERO))

    cantera, planta = total("cantera"), total("planta")
    por_tonelada: dict[str, Decimal] = {}
    if producido.agregados:
        por_tonelada |= costo_por_tonelada(cantera, producido.agregados, pesos=pesos)
    planta_por_t: Decimal | None = None
    if producido.usos:
        mezclas = {m: sum((t for _, t in u.values()), CERO) for m, u in producido.usos.items()}
        planta_por_t = costo_por_tonelada(planta, mezclas)[next(iter(mezclas))]
        for mezcla, usos in sorted(producido.usos.items()):
            por_tonelada[mezcla] = costo_de_mezcla_del_periodo(
                [usos[i] for i in sorted(usos)], por_tonelada, precios, planta_por_t
            )
    en_cero = sorted(c for c, v in por_tonelada.items() if not v > CERO)
    if en_cero:
        raise ErrorDeCalculo(
            f"El costo por tonelada de {', '.join(en_cero)} en {periodo} da cero: revise los "
            "costos y los precios; no se guardó nada."
        )

    entradas = {
        "version": VERSION_DE_LA_INSTANTANEA,
        "periodo": periodo,
        "moneda": moneda,
        "reparto_cantera": "por tonelada" if pesos is None else "por pesos",
        "pesos": None if pesos is None else {c: _t(p) for c, p in pesos.items()},
        "fecha_de_la_lista": _ultimo_dia(periodo).isoformat(),
        "costos": [_costo_json(r, v, eq) for r, v, eq in convertidos],
        "producido": {c: _t(t) for c, t in producido.toneladas.items()},
        "agregados": sorted(producido.agregados),
        "recetas": [
            _receta_json(receta, toneladas)
            for _, usos in sorted(producido.usos.items())
            for receta, toneladas in (usos[i] for i in sorted(usos))
        ],
        "precios_comprados": detalle_precios,
    }
    resultado = {
        "total_cantera": _t(cantera),
        "total_planta": _t(planta),
        "planta_por_t": None if planta_por_t is None else _t(planta_por_t),
        "por_tonelada": {c: _t(v) for c, v in por_tonelada.items()},
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
    """El calculo de la fila, comprobando que su instantanea es la de su huella."""
    if hashlib.sha256(fila.instantanea.encode("utf-8")).hexdigest() != fila.huella:
        raise ErrorDeCalculo(
            f"El cálculo n.º {fila.id} fue alterado: su huella no coincide con lo guardado."
        )
    resultado = json.loads(fila.instantanea)["resultado"]
    return CalculoGuardado(
        id=fila.id,
        periodo=fila.periodo,
        moneda=fila.moneda,
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


def ultimo_calculo(sesion_ins: Session, producto: str) -> CalculoGuardado | None:
    """El calculo mas reciente (mayor numero) que da costo por tonelada a `producto`, o `None`."""
    for fila in sesion_ins.scalars(select(Calculo).order_by(Calculo.id.desc())):
        calculo = _guardado(fila)
        if producto in calculo.por_tonelada:
            return calculo
    return None
