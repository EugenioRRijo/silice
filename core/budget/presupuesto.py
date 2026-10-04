"""Armado del presupuesto: de las cantidades de obra al precio de cada renglón.

`generar_presupuesto` cose las tres piezas del núcleo sin conocer ningún dominio: recibe los
`ItemComputo` que produjo un adaptador, las composiciones del catálogo y los parámetros de costo, y
llama al motor puro `core.costing.calcular_apu` una vez por renglón. Es un paso intermedio, sin
valor de entrega: exige composición para todo ítem y devuelve un presupuesto sin informe, así que
se entrega siempre con `elaborar` (INV‑037).

`elaborar` es el flujo completo de la Sesión I0.5: presupuesto, curva y **auditoría siempre**, sin
que el usuario la pida (principio 7 de NORMAS.md §2). Por eso devuelve `ResultadoElaboracion`, que
lleva el informe junto al presupuesto: no hay forma de obtener uno sin el otro. Es también el único
lugar del protocolo «presupuesto valorado → plan de trabajo → curva → auditoría» (INV‑069): quien
necesita el plan secuencial pasa `plan=plan_secuencial`, sin armar un borrador propio.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Protocol

from core.budget.curva import PeriodoPlan, con_curva, generar_curva
from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.contracts.item_computo import ItemComputo
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad
from core.costing import calcular_apu
from core.verification import REGLAS, auditar
from core.verification.informe import InformeAuditoria
from core.verification.texto import formatear_decimal

__all__ = [
    "CODIGO_ATIPICO",
    "CODIGO_PENDIENTE",
    "DetectorAtipicos",
    "GeneradorPlan",
    "MarcaAtipica",
    "ResultadoElaboracion",
    "elaborar",
    "exigir_composiciones",
    "generar_presupuesto",
    "hallazgos_externos",
]

MONEDA_POR_DEFECTO = "USD"

#: Código con que el informe declara un ítem sin partida en el catálogo (UC‑01, flujo 3a). No es una
#: de las siete reglas de NORMAS.md §7: lo emite la elaboración, que es quien sabe qué ítems no pudo
#: valorar, y viaja en el mismo informe para que nadie reciba el presupuesto sin esa declaración.
CODIGO_PENDIENTE = "PENDIENTE"

#: Código con que el informe de una versión revalorada declara un precio atípico de su lista nueva
#: (UC‑07, paso 5; expediente C6.5). Tampoco es una de las siete reglas: lo emite la revaloración,
#: que es quien tiene la lista nueva y el detector, con severidad ADVERTENCIA.
CODIGO_ATIPICO = "ATIPICO"


class MarcaAtipica(Protocol):
    """Una variación de precio marcada como atípica por un detector ajeno al núcleo.

    `id` es el de su `CambioPrecio` (como texto), `valor` su variación y `puntaje` el del detector
    (más negativo, más anómalo). `ml.anomaly.PrecioAtipico` lo cumple sin que `core/` lo importe.
    """

    @property
    def id(self) -> str: ...

    @property
    def valor(self) -> Decimal: ...

    @property
    def puntaje(self) -> float: ...


#: El detector de atípicos que recibe la revaloración: el histórico `{id del cambio: variación}` en
#: la entrada y las marcas en la salida, la forma de `ml.anomaly.precios_atipicos`.
DetectorAtipicos = Callable[[Mapping[str, Decimal]], Sequence[MarcaAtipica]]

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

    Paso intermedio, sin valor de entrega: el presupuesto que devuelve no lleva informe de
    auditoría. Entregar siempre con `elaborar` (principio 7 de NORMAS.md §2; INV‑037).

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
    reglas: Sequence[ReglaVerificacion] = REGLAS,
) -> ResultadoElaboracion:
    """Genera el presupuesto, le añade la curva si hay plan y lo audita siempre.

    `plan` es el plan de trabajo ya escrito o una función que lo calcula sobre el presupuesto
    valorado. `plan=plan_secuencial` es el protocolo de la interfaz, la API y los sembradores, que
    antes cada uno escribía con un borrador propio (INV‑069). Sin `plan` el presupuesto no lleva
    curva y las reglas R2 y R7 lo declaran no aplicable.

    `reglas` son las reglas que audita la elaboración: por defecto las siete de `REGLAS`; quien
    tiene reglas propias (p. ej. las de una hoja de cálculo de espacio) pasa `REGLAS + las suyas`
    (SF‑E1, RF‑62). Sus hallazgos se guardan con el informe y, al recargar, revalorar, simular o
    importar, `hallazgos_externos` los distingue de los de las siete para volver a declararlos.

    Un ítem cuya partida no tiene composición en `composiciones` queda **pendiente** (UC‑01, flujo
    3a): no entra al presupuesto, no suma al total ni al plan, y el informe lo declara con un
    hallazgo `CODIGO_PENDIENTE` de severidad ERROR. `ResultadoElaboracion.pendientes` los devuelve
    para que quien llama proponga partidas similares (UC‑03). Un plan ya escrito que reparta una
    partida pendiente lanza `PlanInvalido`, como cualquier código desconocido.

    Si todos los ítems quedan pendientes, el presupuesto sale vacío (sin partidas, total 0) y el
    informe no cumple: lleva un `CODIGO_PENDIENTE` de severidad ERROR por ítem. Aunque se pase
    `plan`, no hay curva que repartir, y R2 y R7 se declaran no aplicables (INFO).
    """
    reglas = tuple(reglas)
    valorables = [item for item in items if item.codigo_partida in composiciones]
    pendientes = tuple(item for item in items if item.codigo_partida not in composiciones)
    presupuesto = generar_presupuesto(valorables, composiciones, parametros, codigo, fecha, moneda)
    reparto = plan(presupuesto) if callable(plan) else plan
    if reparto is not None:
        presupuesto = con_curva(presupuesto, generar_curva(presupuesto, reparto))
    informe = _declarar_pendientes(auditar(presupuesto, reglas), pendientes)
    return ResultadoElaboracion(presupuesto=presupuesto, informe=informe, pendientes=pendientes)


def _declarar_pendientes(
    informe: InformeAuditoria, pendientes: Sequence[ItemComputo]
) -> InformeAuditoria:
    """El mismo informe con un hallazgo ERROR por ítem pendiente, atribuido a su partida.

    ERROR y no ADVERTENCIA: un presupuesto al que le falta una partida no cumple, aunque la
    verificación no bloquee su emisión (UC‑01, flujo 7a).

    El hallazgo cita primero el código de la partida y luego el `origen_id`, y el índice gana la
    identidad `codigo -> codigo`, como hace R6 (`core.verification.informe._indice_de_partidas`).
    Así `partida_de` lo atribuye a la partida pendiente aunque su `origen_id` lo comparta un ítem
    valorado de otra partida (el adaptador civil tabular da la misma fila `T-01` al concreto, al
    encofrado y a la excavación). El `origen_id` del pendiente **no** entra al índice: nadie lo
    necesita (el hallazgo se resuelve por su código) y, como el índice del informe ya no registra
    un origen que citan dos partidas valoradas (INV‑095), la entrada del pendiente ocuparía ese
    hueco y una regla que no declara su partida y cita ese origen se atribuiría al pendiente, que
    es justo la conjetura que el índice evita (M‑1 de la revisión de C5).
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
            origen_ids=_clave_pendiente(item),
            valor_observado=item.cantidad,
        )
        for item in pendientes
    )
    # `replace` y no un informe nuevo campo por campo: así se conservan las reglas evaluadas y la
    # partida que cada regla declaró (INV‑092 e INV‑095, expediente C5.2), y lo que el informe gane.
    return replace(
        informe,
        hallazgos=informe.hallazgos + declarados,
        partida_por_origen={
            **{item.codigo_partida: item.codigo_partida for item in pendientes},
            **informe.partida_por_origen,
        },
    )


def _declarar_atipicos(
    informe: InformeAuditoria, hallazgos: Sequence[Hallazgo]
) -> InformeAuditoria:
    """El mismo informe con los hallazgos `CODIGO_ATIPICO` de una revaloración (UC‑07, paso 5).

    Cada hallazgo cita, en `origen_ids`, los códigos de las partidas del presupuesto que usan el
    insumo cuyo precio es atípico. Se atribuye a su partida si cita una sola, y a ninguna (`None`)
    si cita varias: el informe no elige una por su cuenta (INV‑095). Única definición de esa
    atribución: la usan `actualizar_precios` al revalorar y `cargar_elaboracion` al recargar.
    `replace`, como `_declarar_pendientes`, para no perder lo que el informe ya lleva.
    """
    if not hallazgos:
        return informe
    return replace(
        informe,
        hallazgos=informe.hallazgos + tuple(hallazgos),
        partida_por_hallazgo={
            **informe.partida_por_hallazgo,
            **{
                hallazgo: hallazgo.origen_ids[0] if len(hallazgo.origen_ids) == 1 else None
                for hallazgo in hallazgos
            },
        },
    )


def hallazgos_externos(
    informe: InformeAuditoria, reglas: Sequence[ReglaVerificacion] = REGLAS
) -> tuple[Hallazgo, ...]:
    """Los hallazgos del informe que no son de `reglas` ni son `CODIGO_PENDIENTE` (SF‑E1).

    Son los que una reauditoría con `reglas` no puede recalcular: los de reglas ajenas a ellas
    (incluido `CODIGO_ATIPICO`, que declara la revaloración). Quien rehace un informe (un
    escenario, por ejemplo) los pasa a `_declarar_externos` para no perderlos.
    """
    conocidos = {regla.codigo for regla in reglas} | {CODIGO_PENDIENTE}
    return tuple(h for h in informe.hallazgos if h.regla not in conocidos)


def _declarar_externos(
    informe: InformeAuditoria, hallazgos: Sequence[Hallazgo]
) -> InformeAuditoria:
    """El mismo informe con los hallazgos guardados de reglas que la reauditoría no corrió.

    Los `CODIGO_ATIPICO` se atribuyen como siempre (`_declarar_atipicos`). Los demás se agregan
    sin declarar partida: una regla que no declara partida la deja al índice de orígenes del
    informe, y es lo mismo que pasó al emitirlos. Única definición, como `_declarar_atipicos`.
    """
    atipicos = [h for h in hallazgos if h.regla == CODIGO_ATIPICO]
    otros = tuple(h for h in hallazgos if h.regla != CODIGO_ATIPICO)
    if otros:
        informe = replace(informe, hallazgos=informe.hallazgos + otros)
    return _declarar_atipicos(informe, atipicos)


def _clave_pendiente(item: ItemComputo) -> tuple[str, str]:
    """Los `origen_ids` del hallazgo `CODIGO_PENDIENTE` de un ítem: su partida y su origen.

    Única definición de la clave: la usan `_declarar_pendientes` al redactar el hallazgo y
    `core.budget.persistencia` al comprobar que cada pendiente guardado está declarado (INV‑080).
    """
    return (item.codigo_partida, item.origen_id)


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
