"""Armado del presupuesto: de las cantidades de obra al precio de cada renglón.

`generar_presupuesto` cose las tres piezas del núcleo sin conocer ningún dominio: recibe los
`ItemComputo` que produjo un adaptador, las composiciones del catálogo y los parámetros de costo, y
llama al motor puro `core.costing.calcular_apu` una vez por renglón. Es un paso intermedio: exige
composición para todo ítem.

`elaborar` es el flujo completo de la Sesión I0.5: presupuesto, curva y **auditoría siempre**, sin
que el usuario la pida (principio 7 de CLAUDE.md §2). Por eso devuelve `ResultadoElaboracion`, que
lleva el informe junto al presupuesto: no hay forma de obtener uno sin el otro. Es también el único
lugar del protocolo «presupuesto valorado → plan de trabajo → curva → auditoría» (INV‑069): quien
necesita el plan secuencial pasa `plan=plan_secuencial`, sin armar un borrador propio.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from core.budget.curva import PeriodoPlan, con_curva, generar_curva
from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.contracts.item_computo import ItemComputo
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Hallazgo, Severidad
from core.costing import calcular_apu
from core.verification import auditar
from core.verification.informe import InformeAuditoria
from core.verification.texto import formatear_decimal

__all__ = [
    "CODIGO_PENDIENTE",
    "GeneradorPlan",
    "ResultadoElaboracion",
    "elaborar",
    "exigir_composiciones",
    "generar_presupuesto",
]

MONEDA_POR_DEFECTO = "USD"

#: Código con que el informe declara un ítem sin partida en el catálogo (UC‑01, flujo 3a). No es una
#: de las siete reglas de CLAUDE.md §7: lo emite la elaboración, que es quien sabe qué ítems no pudo
#: valorar, y viaja en el mismo informe para que nadie reciba el presupuesto sin esa declaración.
CODIGO_PENDIENTE = "PENDIENTE"

#: Un plan de trabajo que se calcula sobre el presupuesto ya valorado (p. ej. `plan_secuencial`).
GeneradorPlan = Callable[[Presupuesto], Sequence[PeriodoPlan]]


@dataclass(frozen=True, slots=True)
class ResultadoElaboracion:
    """Lo que produce una elaboración: el presupuesto, el informe que siempre lo acompaña y los
    ítems que quedaron pendientes por no tener partida en el catálogo (UC‑01, flujo 3a)."""

    presupuesto: Presupuesto
    informe: InformeAuditoria
    pendientes: tuple[ItemComputo, ...] = ()


def generar_presupuesto(
    items: Sequence[ItemComputo],
    composiciones: Mapping[str, ComposicionAPU],
    parametros: ParametrosCosto,
    codigo: str,
    fecha: date,
    moneda: str = MONEDA_POR_DEFECTO,
) -> Presupuesto:
    """Un `PartidaPresupuestada` por ítem, en el orden recibido, con su precio recién calculado.

    Lanza `ValueError` con la lista de códigos si alguna cantidad no tiene composición de APU: un
    presupuesto incompleto es un presupuesto sin precio, no un presupuesto con ceros.
    """
    exigir_composiciones(items, composiciones)

    partidas = tuple(
        PartidaPresupuestada(
            item=item,
            apu=composiciones[item.codigo_partida],
            resultado=calcular_apu(composiciones[item.codigo_partida], parametros),
        )
        for item in items
    )
    return Presupuesto(codigo=codigo, fecha=fecha, moneda=moneda, partidas=partidas)


def elaborar(
    items: Sequence[ItemComputo],
    composiciones: Mapping[str, ComposicionAPU],
    parametros: ParametrosCosto,
    codigo: str,
    fecha: date,
    moneda: str = MONEDA_POR_DEFECTO,
    plan: Sequence[PeriodoPlan] | GeneradorPlan | None = None,
) -> ResultadoElaboracion:
    """Genera el presupuesto, le añade la curva si hay plan y lo audita siempre.

    `plan` es el plan de trabajo ya escrito o una función que lo calcula sobre el presupuesto
    valorado. `plan=plan_secuencial` es el protocolo de la interfaz, la API y los sembradores, que
    antes cada uno escribía con un borrador propio (INV‑069). Sin `plan` el presupuesto no lleva
    curva y las reglas R2 y R7 lo declaran no aplicable.

    Un ítem cuya partida no tiene composición en `composiciones` queda **pendiente** (UC‑01, flujo
    3a): no entra al presupuesto, no suma al total ni al plan, y el informe lo declara con un
    hallazgo `CODIGO_PENDIENTE` de severidad ERROR. `ResultadoElaboracion.pendientes` los devuelve
    para que quien llama proponga partidas similares (UC‑03). Un plan ya escrito que reparta una
    partida pendiente lanza `PlanInvalido`, como cualquier código desconocido.
    """
    valorables = [item for item in items if item.codigo_partida in composiciones]
    pendientes = tuple(item for item in items if item.codigo_partida not in composiciones)
    presupuesto = generar_presupuesto(valorables, composiciones, parametros, codigo, fecha, moneda)
    reparto = plan(presupuesto) if callable(plan) else plan
    if reparto is not None:
        presupuesto = con_curva(presupuesto, generar_curva(presupuesto, reparto))
    informe = _declarar_pendientes(auditar(presupuesto), pendientes)
    return ResultadoElaboracion(presupuesto=presupuesto, informe=informe, pendientes=pendientes)


def _declarar_pendientes(
    informe: InformeAuditoria, pendientes: Sequence[ItemComputo]
) -> InformeAuditoria:
    """El mismo informe con un hallazgo ERROR por ítem pendiente, atribuido a su partida.

    ERROR y no ADVERTENCIA: un presupuesto al que le falta una partida no cumple, aunque la
    verificación no bloquee su emisión (UC‑01, flujo 7a).
    """
    if not pendientes:
        return informe
    declarados = tuple(
        Hallazgo(
            regla=CODIGO_PENDIENTE,
            severidad=Severidad.ERROR,
            descripcion=(
                f"el item {item.origen_id} ({formatear_decimal(item.cantidad)} {item.unidad}) "
                f"cita la partida {item.codigo_partida}, que no tiene composicion de APU: queda "
                "pendiente y no suma al total"
            ),
            origen_ids=(item.origen_id,),
            valor_observado=item.cantidad,
        )
        for item in pendientes
    )
    return InformeAuditoria(
        codigo_presupuesto=informe.codigo_presupuesto,
        hallazgos=informe.hallazgos + declarados,
        partida_por_origen={
            **{item.origen_id: item.codigo_partida for item in pendientes},
            **informe.partida_por_origen,
        },
    )


def exigir_composiciones(
    items: Sequence[ItemComputo], composiciones: Mapping[str, ComposicionAPU]
) -> None:
    """Precondición estricta: toda partida citada por `items` tiene composición en `composiciones`.

    Lanza `ValueError` con la lista de códigos que faltan. La usan `generar_presupuesto` y los
    llamadores del núcleo que no pueden perder renglones en silencio (`actualizar_precios`,
    `generar_escenario`); `elaborar` no la usa, porque deja pendientes (UC‑01, flujo 3a).
    """
    faltantes = _codigos_sin_composicion(items, composiciones)
    if faltantes:
        raise ValueError("no hay composicion de APU para las partidas: " + ", ".join(faltantes))


def _codigos_sin_composicion(
    items: Sequence[ItemComputo], composiciones: Mapping[str, ComposicionAPU]
) -> list[str]:
    faltantes: list[str] = []
    for item in items:
        if item.codigo_partida not in composiciones and item.codigo_partida not in faltantes:
            faltantes.append(item.codigo_partida)
    return faltantes
