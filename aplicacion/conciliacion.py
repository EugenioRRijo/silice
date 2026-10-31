"""Conciliación entre el APU, el presupuesto, los tramos y el costo propio (plan vial, Tarea 10).

`conciliar` compara lo que dice el presupuesto con tres fuentes que las reglas R1 a R12 y VR1 a VR7
no cruzan entre sí:

- **CV1** el precio unitario de un renglón contra el recalculado desde su APU (`calcular_apu`
  con los parámetros de costo). Se comprobó antes de escribirla que ninguna regla R1 a R12 lo hace:
  R1 y R5 usan el precio unitario solo como `impacto` de su hallazgo. Tolerancia 0,01 en la
  moneda (V-15). Un renglón sin composición en `composiciones` no se recalcula.
- **CV2** la cantidad de una partida vial contra la suma de las cantidades de los tramos para esa
  partida (`items_viales`, lo que deriva `adapters.vial.derivar_tramos`; tolerancia relativa
  V-16). Cubre lo que VR1 a VR7 no evalúan: una partida derivada de los tramos que **falta** en el
  presupuesto (ERROR, observado 0) y una partida vial del presupuesto que ningún tramo produce
  (ADVERTENCIA). Sin `items_viales` no hay nada que conciliar y CV2 calla. Las unidades no se
  convierten: se suman las cantidades de la partida tal como vienen (VR7 vigila las unidades).
- **CV3** el precio con que el APU usa un insumo propio (`AGP-…` agregado, `MZP-…` mezcla) contra
  el del último cálculo publicado de ese producto (`costos_propios`, ver
  `costos_propios_publicados`). La línea del APU se reconoce por la descripción del insumo que
  publica el costo propio (`descripcion_de_costo_propio`). Si el cálculo está en otra moneda que
  el presupuesto no se compara y se dice (INFO «regla no evaluable»). El mensaje lleva el n.º del
  último cálculo publicado y, si `calculos_usados` lo sabe (se saca de la fuente del precio con
  `numero_de_calculo`), el del cálculo del que viene el precio usado.

Cada hallazgo cita como origen el `origen_id` del renglón (CV1, CV3) o los de los tramos (CV2). No
hay Streamlit, reloj ni usuario aquí: quien llama arma los insumos. Los mensajes llevan coma
decimal y punto de miles.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal

from sqlalchemy.orm import Session

from adapters.vial.constantes import (
    PARTIDAS_VIALES,
    TOLERANCIA_CANTIDAD_CONCILIADA,
    TOLERANCIA_PRECIO,
)
from aplicacion.cifras import texto_de_cifra
from aplicacion.costo_propio import (
    PREFIJO_DE_AGREGADO,
    PREFIJO_DE_MEZCLA,
    CalculoGuardado,
    calculos_registrados,
    descripcion_de_costo_propio,
)
from core.contracts import ItemComputo, Presupuesto
from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.contracts.verificacion import Hallazgo, Severidad
from core.costing import calcular_apu

__all__ = [
    "conciliar",
    "costos_propios_publicados",
    "numero_de_calculo",
]

_CERO = Decimal(0)
_CENTAVOS = Decimal("0.01")
_NO_EVALUABLE = "regla no evaluable"
_CALCULO_DE_LA_FUENTE = re.compile(r"cálculo n\.º (\d+)")
_NOMBRE_DE_PARTIDA = {codigo: nombre for codigo, nombre, _ in PARTIDAS_VIALES.values()}


def _dinero(valor: Decimal) -> str:
    """Un monto con dos decimales, o con los que haga falta si tiene más (12,70; 12,661)."""
    return texto_de_cifra(
        valor.quantize(_CENTAVOS) if valor == valor.quantize(_CENTAVOS) else valor
    )


def _cantidad(valor: Decimal) -> str:
    return texto_de_cifra(valor.normalize())


def numero_de_calculo(fuente: str) -> int | None:
    """El n.º de cálculo que dice la fuente de un precio propio («Producción, período 2026-11,
    cálculo n.º 7»), o `None` si la fuente no es de un cálculo."""
    coincidencia = _CALCULO_DE_LA_FUENTE.search(fuente)
    return None if coincidencia is None else int(coincidencia.group(1))


def costos_propios_publicados(sesion_ins: Session) -> dict[str, CalculoGuardado]:
    """Por código de insumo propio (`AGP-<producto>`, `MZP-<producto>`), el último cálculo
    **publicado** que le da costo (el de mayor n.º entre los publicados). Un cálculo sin publicar no
    cuenta. Lee con `calculos_registrados`: un cálculo alterado (huella que no cuadra) es
    `ErrorDeCalculo`, nada alterado se toma por bueno."""
    ultimos: dict[str, CalculoGuardado] = {}
    for calculo, publicacion in calculos_registrados(sesion_ins):  # del más reciente al más viejo
        if publicacion is None:
            continue
        agregados = set(json.loads(calculo.instantanea)["entradas"]["agregados"])
        for producto in calculo.por_tonelada:
            prefijo = PREFIJO_DE_AGREGADO if producto in agregados else PREFIJO_DE_MEZCLA
            ultimos.setdefault(prefijo + producto, calculo)
    return ultimos


def _hallazgo(
    regla: str,
    severidad: Severidad,
    origen: tuple[str, ...],
    descripcion: str,
    observado: Decimal | None = None,
    esperado: Decimal | None = None,
) -> Hallazgo:
    return Hallazgo(
        regla=regla,
        severidad=severidad,
        descripcion=descripcion,
        origen_ids=origen,
        valor_observado=observado,
        valor_esperado=esperado,
    )


# --- CV1 ------------------------------------------------------------------------------------------


def _cv1(
    presupuesto: Presupuesto,
    composiciones: Mapping[str, ComposicionAPU],
    parametros: ParametrosCosto,
) -> list[Hallazgo]:
    hallazgos = []
    tolerancia = Decimal(TOLERANCIA_PRECIO.valor)
    for partida in presupuesto.partidas:
        composicion = composiciones.get(partida.item.codigo_partida)
        if composicion is None:
            continue
        esperado = calcular_apu(composicion, parametros).precio_unitario
        observado = partida.resultado.precio_unitario
        if abs(observado - esperado) <= tolerancia:
            continue
        moneda = presupuesto.moneda
        hallazgos.append(
            _hallazgo(
                "CV1",
                Severidad.ERROR,
                (partida.item.origen_id,),
                f"El precio unitario de {partida.item.codigo_partida} es {_dinero(observado)} "
                f"{moneda}, pero su APU recalculado da {_dinero(esperado)} {moneda} "
                f"(tolerancia {_dinero(tolerancia)})",
                observado,
                esperado,
            )
        )
    return hallazgos


# --- CV2 ------------------------------------------------------------------------------------------


def _tramos_de(derivados: Sequence[ItemComputo]) -> str:
    ids = dict.fromkeys(i.origen_id.split(":")[1] for i in derivados)
    return ("tramo " if len(ids) == 1 else "tramos ") + ", ".join(ids)


def _cv2(presupuesto: Presupuesto, items_viales: Sequence[ItemComputo]) -> list[Hallazgo]:
    if not items_viales:
        return []  # sin tramos no hay con qué conciliar
    derivados: dict[str, list[ItemComputo]] = defaultdict(list)
    for item in items_viales:
        derivados[item.codigo_partida].append(item)
    del_presupuesto: dict[str, list[ItemComputo]] = defaultdict(list)
    for partida in presupuesto.partidas:
        del_presupuesto[partida.item.codigo_partida].append(partida.item)
    hallazgos = []
    for codigo, de_tramos in derivados.items():
        esperado = sum((i.cantidad for i in de_tramos), _CERO)
        unidad = de_tramos[0].unidad
        origenes = tuple(dict.fromkeys(i.origen_id for i in de_tramos))
        nombre = f"{codigo} ({_NOMBRE_DE_PARTIDA.get(codigo, de_tramos[0].descripcion)})"
        if codigo not in del_presupuesto:
            hallazgos.append(
                _hallazgo(
                    "CV2",
                    Severidad.ERROR,
                    origenes,
                    f"La partida {nombre} falta en el presupuesto: los tramos dan "
                    f"{_cantidad(esperado)} {unidad} ({_tramos_de(de_tramos)})",
                    _CERO,
                    esperado,
                )
            )
            continue
        observado = sum((i.cantidad for i in del_presupuesto[codigo]), _CERO)
        tolerancia = esperado * Decimal(TOLERANCIA_CANTIDAD_CONCILIADA.valor)
        if abs(observado - esperado) <= tolerancia:
            continue
        hallazgos.append(
            _hallazgo(
                "CV2",
                Severidad.ERROR,
                origenes,
                f"La partida {nombre} suma {_cantidad(observado)} {unidad} en el presupuesto y "
                f"los tramos dan {_cantidad(esperado)} {unidad} ({_tramos_de(de_tramos)})",
                observado,
                esperado,
            )
        )
    for codigo, items in del_presupuesto.items():
        if codigo in derivados or codigo not in _NOMBRE_DE_PARTIDA:
            continue
        observado = sum((i.cantidad for i in items), _CERO)
        hallazgos.append(
            _hallazgo(
                "CV2",
                Severidad.ADVERTENCIA,
                tuple(dict.fromkeys(i.origen_id for i in items)),
                f"La partida {codigo} ({_NOMBRE_DE_PARTIDA[codigo]}) suma {_cantidad(observado)} "
                f"{items[0].unidad} en el presupuesto, pero ningún tramo la produce",
                observado,
                _CERO,
            )
        )
    return hallazgos


# --- CV3 ------------------------------------------------------------------------------------------


def _cv3(
    presupuesto: Presupuesto,
    costos_propios: Mapping[str, CalculoGuardado],
    calculos_usados: Mapping[str, int],
) -> list[Hallazgo]:
    por_descripcion = {descripcion_de_costo_propio(c): c for c in costos_propios}
    tolerancia = Decimal(TOLERANCIA_PRECIO.valor)
    hallazgos = []
    for partida in presupuesto.partidas:
        for linea in partida.apu.materiales:
            codigo = por_descripcion.get(linea.descripcion)
            if codigo is None:
                continue
            ultimo = costos_propios[codigo]
            esperado = ultimo.por_tonelada.get(codigo.split("-", 1)[1])
            if esperado is None:
                continue
            origen = (partida.item.origen_id,)
            if ultimo.moneda != presupuesto.moneda:
                hallazgos.append(
                    _hallazgo(
                        "CV3",
                        Severidad.INFO,
                        origen,
                        f"{_NO_EVALUABLE}: el último cálculo publicado de {codigo} (n.º "
                        f"{ultimo.id}) está en {ultimo.moneda} y el presupuesto en "
                        f"{presupuesto.moneda}; no se compara",
                    )
                )
                continue
            if abs(linea.precio - esperado) <= tolerancia:
                continue
            usado = calculos_usados.get(codigo)
            de_donde = (
                "ningún cálculo publicado conocido" if usado is None else f"cálculo n.º {usado}"
            )
            hallazgos.append(
                _hallazgo(
                    "CV3",
                    Severidad.ADVERTENCIA,
                    origen,
                    f"{partida.item.codigo_partida} usa {codigo} a {_dinero(linea.precio)} "
                    f"{presupuesto.moneda}/t ({de_donde}), pero el último cálculo publicado, el "
                    f"cálculo n.º {ultimo.id} (período {ultimo.periodo}), da {_dinero(esperado)} "
                    f"{ultimo.moneda}/t",
                    linea.precio,
                    esperado,
                )
            )
    return hallazgos


def conciliar(
    presupuesto: Presupuesto,
    composiciones: Mapping[str, ComposicionAPU],
    parametros: ParametrosCosto,
    *,
    items_viales: Sequence[ItemComputo],
    costos_propios: Mapping[str, CalculoGuardado],
    calculos_usados: Mapping[str, int] | None = None,
) -> list[Hallazgo]:
    """Los hallazgos CV1, CV2 y CV3 de `presupuesto`, en ese orden y, dentro de cada regla, en el
    de las partidas. `composiciones` son los APU vigentes por código de partida; `items_viales`,
    las cantidades derivadas de los tramos; `costos_propios`, el último cálculo publicado por
    código de insumo propio (`costos_propios_publicados`); `calculos_usados`, el n.º del cálculo
    del que viene el precio que usa el APU, por código de insumo propio (`numero_de_calculo`)."""
    return [
        *_cv1(presupuesto, composiciones, parametros),
        *_cv2(presupuesto, items_viales),
        *_cv3(presupuesto, costos_propios, calculos_usados or {}),
    ]
