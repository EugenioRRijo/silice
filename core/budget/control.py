# core/budget/control.py
"""SL-E5: el control de la obra al corte, de la base de datos al resultado (spec S2 §4, §5.3).

`calcular_control` lee la instantánea de control (`core.budget.valuaciones`), convierte los costos
reales con la tasa de su fecha (S1), toma los precios del corte y el reajuste ya reconocido y
llama a las funciones puras de `core.budget.valor_ganado`. **Nada derivado se guarda**: los
indicadores, las alertas, los hallazgos de R13-R14 y la reproyección se recalculan cada vez, sin
reescribir filas (S2-R13, RV-9). Los parámetros de control sí se guardan, con su `RegistroCambio`.

Un costo real sin tasa aplicable (más de 7 días sin tasa, S1-R2) deja el AC «no disponible» con la
lista de esos costos; PV, EV, SPI, el precio y el término se calculan igual (S2-R17, REQ-25).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget.calendario import numero_de_dia, periodo_de
from core.budget.curva import generar_curva
from core.budget.edicion import CambioEditado, _exigir_respaldo, version_vigente
from core.budget.equilibrio import PuntoEquilibrio, punto_equilibrio
from core.budget.persistencia import cargar_presupuesto
from core.budget.puente import ReajusteReconocido, reajuste_reconocido
from core.budget.valor_ganado import (
    PERSPECTIVA_COSTO,
    Alertas,
    EstadoObra,
    Indicadores,
    ParametrosControl,
    PreciosDelCorte,
    Reproyeccion,
    Separacion,
    alertas,
    equilibrio_proyectado,
    indicadores,
    partidas_de_plan,
    reproyectar,
    separar_desvio,
)
from core.budget.valuaciones import CostoReal, InstantaneaControl, instantanea_control
from core.catalog import Catalogo
from core.catalog.indices import LADO_POR_DEFECTO, TasaNoDisponible, tasa_aplicable
from core.catalog.moneda import convertir
from core.contracts.apu import ComposicionAPU
from core.verification.informe import InformeAuditoria

__all__ = [
    "ResultadoControl",
    "calcular_control",
    "construir_estado",
    "composiciones_de_la_linea_base",
    "costo_real_al_corte",
    "guardar_parametros",
    "parametros_de_control",
    "precios_del_corte_de_version",
]

CERO = Decimal(0)
OBJETO_PARAMETRO = "parametro"


@dataclass(frozen=True)
class ResultadoControl:
    """Todo lo que la pantalla «Control de obra» muestra al corte (S2 §5.5)."""

    instantanea: InstantaneaControl
    estado: EstadoObra
    indicadores: Indicadores
    separacion: Separacion
    reproyeccion: Reproyeccion
    equilibrio_base: PuntoEquilibrio | None
    equilibrio_proyectado: PuntoEquilibrio | None
    reajuste: ReajusteReconocido
    alertas: Alertas
    informe: InformeAuditoria
    costos_sin_tasa: tuple[CostoReal, ...]
    parametros: ParametrosControl
    venta: Decimal
    costo_fijo: Decimal


def precios_del_corte_de_version(
    session: Session,
    proyecto_nombre: str,
    codigo_version: str,
    perspectiva: str,
    catalogo: Catalogo,
) -> PreciosDelCorte:
    """Los unitarios del corte por **comprobación directa** (S2 §4.3): los de una versión
    revalorada por UC-02 (costo directo o precio unitario según la perspectiva). La fuente cita
    la versión y su lista de precios."""
    modelo = session.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(
            models.Proyecto.nombre == proyecto_nombre, models.Presupuesto.codigo == codigo_version
        )
    ).one_or_none()
    if modelo is None:
        raise KeyError(
            f"no hay ninguna version {codigo_version!r} en el proyecto {proyecto_nombre!r}"
        )
    presupuesto = cargar_presupuesto(session, proyecto_nombre, codigo_version, catalogo)
    unitarios: dict[str, Decimal] = {}
    for renglon in presupuesto.partidas:
        unitarios.setdefault(
            renglon.item.codigo_partida,
            renglon.resultado.costo_directo
            if perspectiva == PERSPECTIVA_COSTO
            else renglon.resultado.precio_unitario,
        )
    fuente = (
        f"version {codigo_version} del {modelo.fecha.isoformat()} "
        f"(lista {modelo.lista_precios.nombre})"
    )
    return PreciosDelCorte("comprobacion", fuente, unitarios)


def costo_real_al_corte(
    session: Session, instantanea: InstantaneaControl, *, lado: str = LADO_POR_DEFECTO
) -> tuple[Decimal | None, tuple[CostoReal, ...]]:
    """El AC de la perspectiva *costo*: los costos reales con fecha menor o igual al corte,
    convertidos a la moneda del proyecto con `tasa_aplicable(fecha)` (S1). Si alguno no tiene tasa
    aplicable, el AC es `None` y se devuelven esos costos (S2-R17): ninguno se estima."""
    total = CERO
    sin_tasa: list[CostoReal] = []
    for costo in instantanea.costos:
        if costo.fecha > instantanea.corte:
            continue
        if costo.moneda == instantanea.moneda:
            total += costo.monto
            continue
        try:
            tasa = tasa_aplicable(session, costo.fecha, lado=lado)
        except TasaNoDisponible:
            sin_tasa.append(costo)
            continue
        total += convertir(costo.monto, costo.moneda, instantanea.moneda, tasa.valor)
    return (None if sin_tasa else total), tuple(sin_tasa)


def construir_estado(
    instantanea: InstantaneaControl,
    *,
    costo_real: Decimal | None,
    motivo_costo: str = "",
    precios: PreciosDelCorte | None = None,
) -> EstadoObra:
    """El `EstadoObra` puro al corte: partidas con su plan, el día hábil del corte y lo ejecutado
    por partida y por período del *hasta* (valuaciones con *hasta* menor o igual al corte)."""
    calendario = instantanea.calendario
    feriados = frozenset(calendario.feriados)
    largo = calendario.dias_por_periodo
    ejecutado: dict[str, Decimal] = {}
    por_periodo: dict[tuple[str, int], Decimal] = {}
    ultima = 0
    for valuacion in instantanea.para_el_valor_ganado():
        # Una valuacion que termina antes del primer dia habil cae en el periodo 1.
        periodo = max(1, periodo_de(calendario.fecha_inicio, largo, valuacion.hasta, feriados))
        ultima = max(ultima, numero_de_dia(calendario.fecha_inicio, valuacion.hasta, feriados))
        for linea in valuacion.lineas:
            ejecutado[linea.codigo_partida] = (
                ejecutado.get(linea.codigo_partida, CERO) + linea.cantidad
            )
            clave = (linea.codigo_partida, periodo)
            por_periodo[clave] = por_periodo.get(clave, CERO) + linea.cantidad
    return EstadoObra(
        partidas=partidas_de_plan(
            instantanea.presupuesto, instantanea.plan, instantanea.linea_base.perspectiva
        ),
        etiquetas=tuple(etiqueta for etiqueta, _ in instantanea.plan),
        dias_por_periodo=largo,
        dia=numero_de_dia(calendario.fecha_inicio, instantanea.corte, feriados),
        ejecutado=ejecutado,
        por_periodo=por_periodo,
        perspectiva=instantanea.linea_base.perspectiva,
        costo_real=costo_real,
        motivo_costo=motivo_costo,
        precios=precios,
        dia_ultima_valuacion=ultima,
    )


def calcular_control(
    session: Session,
    proyecto_nombre: str,
    *,
    catalogo: Catalogo,
    corte: date | None = None,
    precios: PreciosDelCorte | None = None,
    parametros: ParametrosControl | None = None,
    lado: str = LADO_POR_DEFECTO,
) -> ResultadoControl:
    """Indicadores, separación del desvío, reproyección, punto de equilibrio proyectado, alertas e
    informe de control al `corte` (por defecto el *hasta* de la última valuación). Sin escribir.

    `precios` son los del corte (S1): sin ellos la separación y el EAC quedan «no disponible»."""
    instantanea = instantanea_control(session, proyecto_nombre, catalogo=catalogo, corte=corte)
    parametros = parametros or parametros_de_control(session, proyecto_nombre)
    perspectiva = instantanea.linea_base.perspectiva
    costo_real, sin_tasa = (None, ())
    motivo = ""
    if perspectiva == PERSPECTIVA_COSTO:
        costo_real, sin_tasa = costo_real_al_corte(session, instantanea, lado=lado)
        if sin_tasa:
            motivo = "sin tasa aplicable para: " + "; ".join(
                f"{c.monto} {c.moneda} del {c.fecha.isoformat()}" for c in sin_tasa
            )
    estado = construir_estado(
        instantanea, costo_real=costo_real, motivo_costo=motivo, precios=precios
    )
    calculados = indicadores(estado)
    separacion = separar_desvio(estado, calculados)
    reproyeccion = reproyectar(estado)
    reconocido = reajuste_reconocido(session, proyecto_nombre, instantanea.corte)
    venta = instantanea.presupuesto.total
    base = None
    proyectado = None
    costo_fijo = CERO
    if perspectiva == PERSPECTIVA_COSTO:
        base = punto_equilibrio(instantanea.presupuesto, instantanea.parametros_costo)
        costo_fijo = base.costo_fijo
        if calculados.eac_sistema is not None and reproyeccion.termino is not None:
            proyectado = equilibrio_proyectado(
                venta=venta,
                costo_variable=calculados.eac_sistema,
                costo_fijo=costo_fijo,
                dias_plan=estado.dias_plan,
                dias_proyectados=reproyeccion.termino,
                reajuste_reconocido=reconocido.monto,
                curva=generar_curva(instantanea.presupuesto, reproyeccion.plan),
            )
    return ResultadoControl(
        instantanea=instantanea,
        estado=estado,
        indicadores=calculados,
        separacion=separacion,
        reproyeccion=reproyeccion,
        equilibrio_base=base,
        equilibrio_proyectado=proyectado,
        reajuste=reconocido,
        alertas=alertas(
            calculados,
            separacion,
            reproyeccion,
            dias_plan=estado.dias_plan,
            equilibrio_base=base,
            equilibrio_proyectado=proyectado,
            parametros=parametros,
        ),
        informe=instantanea.informe(),
        costos_sin_tasa=sin_tasa,
        parametros=parametros,
        venta=venta,
        costo_fijo=costo_fijo,
    )


# ---------------------------------------------------------------------------------------------
# Parámetros de control (S2 §4.5, §4.6)
# ---------------------------------------------------------------------------------------------

_CAMPOS = tuple(campo.name for campo in fields(ParametrosControl))


def parametros_de_control(session: Session, proyecto_nombre: str) -> ParametrosControl:
    """Los parámetros del proyecto; sin fila, los valores por defecto (§4.5 y §4.6)."""
    proyecto = session.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == proyecto_nombre)
    ).one()
    fila = session.get(models.ParametrosControl, proyecto.id)
    if fila is None:
        return ParametrosControl()
    return ParametrosControl(**{nombre: getattr(fila, nombre) for nombre in _CAMPOS})


def guardar_parametros(
    session: Session,
    proyecto_nombre: str,
    parametros: ParametrosControl,
    *,
    fuente: str,
    responsable: str,
    ahora: datetime | None = None,
) -> list[CambioEditado]:
    """Cambia los parámetros de control del proyecto con un `RegistroCambio` (objeto `parametro`)
    por cada valor que cambió, sobre la versión vigente. Exige fuente y responsable. No confirma.
    Devuelve los cambios; sin ninguno no escribe nada."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    proyecto = session.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == proyecto_nombre)
    ).one()
    vigente = version_vigente(session, proyecto_nombre)
    if vigente is None:
        raise ValueError("el proyecto no tiene version guardada: no hay donde registrar el cambio")
    anterior = parametros_de_control(session, proyecto_nombre)
    cambios = [
        CambioEditado(
            OBJETO_PARAMETRO,
            f"control|{nombre}",
            nombre,
            str(getattr(anterior, nombre)),
            str(getattr(parametros, nombre)),
        )
        for nombre in _CAMPOS
        if getattr(anterior, nombre) != getattr(parametros, nombre)
    ]
    if not cambios:
        return []
    fila = session.get(models.ParametrosControl, proyecto.id)
    if fila is None:
        fila = models.ParametrosControl(proyecto_id=proyecto.id)
        session.add(fila)
    for nombre in _CAMPOS:
        setattr(fila, nombre, getattr(parametros, nombre))
    momento = ahora or datetime.now()
    session.add_all(
        models.RegistroCambio(
            proyecto_id=proyecto.id,
            version_origen_id=vigente.id,
            version_resultante_id=vigente.id,
            objeto=cambio.objeto,
            clave=cambio.clave,
            campo=cambio.campo,
            valor_anterior=cambio.valor_anterior,
            valor_nuevo=cambio.valor_nuevo,
            fuente=fuente,
            responsable=responsable,
            fecha_hora=momento,
        )
        for cambio in cambios
    )
    session.flush()
    return cambios


def composiciones_de_la_linea_base(resultado: ResultadoControl) -> dict[str, ComposicionAPU]:
    """Los APU congelados de la línea base por código (SF-E6): `Presupuesto.partidas[i].apu`."""
    return {p.item.codigo_partida: p.apu for p in resultado.instantanea.presupuesto.partidas}
