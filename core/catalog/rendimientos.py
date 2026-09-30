"""Registro, dispersión y propuesta de rendimientos (UC‑06, Sesión I6.2).

El aporte del caso de uso es la trazabilidad: un rendimiento MEDIDO nace de una `Ejecucion`
registrada (obra real, referencia única) y esa procedencia viaja con él hasta el contrato
(`Rendimiento.referencia_ejecucion`). La invariante «MEDIDO exige referencia» vive en el contrato
(`core.contracts.apu.Rendimiento`, CLAUDE.md §5) y en la base
(`ck_rendimiento_medido_exige_ejecucion`); este módulo construye el contrato **antes** de tocar la
base y delega el registro en `Catalogo.registrar_rendimiento`, que exige que la referencia apunte
a una ejecución que exista (trazabilidad total, CLAUDE.md §2).

La dispersión (RF‑26) es aritmética de `Decimal`: número de observaciones, media, mínimo y máximo,
más el desglose estimado/medido — estimado y medido nunca se mezclan sin declararse. La media es la
única división del módulo y hereda la precisión del contexto de `Decimal` (28 cifras); los dos
decimales siguen siendo de presentación.

Como todo el catálogo (`crear_lista_desde_archivo`, `guardar_presupuesto`), aquí no se confirma la
transacción: el `commit` es de la capa que representa la decisión del usuario (API o UI).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.catalog.mapeo import a_rendimiento
from core.catalog.repositorio import Catalogo
from core.contracts.apu import Rendimiento, TipoRendimiento

__all__ = [
    "MINIMO_OBSERVADO_PARA_ADVERTIR",
    "DispersionRendimiento",
    "PropuestaRendimiento",
    "advertencia_rendimiento",
    "dispersion_rendimientos",
    "justificar_rendimiento",
    "proponer_rendimiento",
    "registrar_ejecucion",
    "registrar_rendimiento",
]

#: Observaciones mínimas para advertir por rango (RF‑27): un solo punto no define comportamiento
#: observado del cual apartarse. Mismo espíritu de abstención que `ml.anomaly` con su
#: `MINIMO_OBSERVACIONES` (allá, 8, porque es un juicio estadístico; aquí basta un rango real).
MINIMO_OBSERVADO_PARA_ADVERTIR = 2


@dataclass(frozen=True, slots=True)
class DispersionRendimiento:
    """El comportamiento observado de una partida (RF‑26): conteos y estadísticos exactos."""

    observaciones: int
    media: Decimal
    minimo: Decimal
    maximo: Decimal
    medidos: int
    estimados: int


@dataclass(frozen=True, slots=True)
class PropuestaRendimiento:
    """La propuesta al componer un APU: el rendimiento elegido y la dispersión que lo respalda."""

    rendimiento: Rendimiento
    dispersion: DispersionRendimiento


def registrar_ejecucion(
    session: Session,
    referencia: str,
    fecha_inicio: date,
    fecha_fin: date | None = None,
    descripcion: str = "",
    proyecto: models.Proyecto | None = None,
) -> models.Ejecucion:
    """Registra una obra ejecutada de la que se medirán rendimientos. Referencia única."""
    if not referencia.strip():
        raise ValueError("la referencia de la ejecución no puede estar vacía")
    existente = session.scalars(
        select(models.Ejecucion).where(models.Ejecucion.referencia == referencia)
    ).one_or_none()
    if existente is not None:
        raise ValueError(f"ya existe una ejecución con referencia {referencia!r}")

    ejecucion = models.Ejecucion(
        referencia=referencia,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        descripcion=descripcion,
        proyecto_id=proyecto.id if proyecto is not None else None,
    )
    session.add(ejecucion)
    session.flush()
    return ejecucion


def registrar_rendimiento(
    session: Session,
    codigo_partida: str,
    valor: Decimal,
    tipo: TipoRendimiento,
    fecha: date,
    condiciones: str = "",
    referencia_ejecucion: str | None = None,
) -> Rendimiento:
    """Registra un rendimiento y devuelve el `Rendimiento` del contrato ya persistido.

    El contrato se construye primero: sus invariantes (valor > 0, MEDIDO exige referencia)
    rechazan la petición antes de tocar la base. El registro lo hace
    `Catalogo.registrar_rendimiento`, la única implementación (INV‑005), que lanza `LookupError`
    si la partida no existe o la referencia no corresponde a ninguna ejecución registrada.
    """
    contrato = Rendimiento(
        codigo_partida=codigo_partida,
        valor=valor,
        tipo=tipo,
        fecha=fecha,
        condiciones=condiciones,
        referencia_ejecucion=referencia_ejecucion,
    )
    return a_rendimiento(Catalogo(session).registrar_rendimiento(contrato))


def dispersion_rendimientos(session: Session, codigo_partida: str) -> DispersionRendimiento | None:
    """La dispersión del histórico de la partida, o `None` si no tiene rendimientos."""
    return _dispersion_de(Catalogo(session).rendimientos(codigo_partida))


def proponer_rendimiento(session: Session, codigo_partida: str) -> PropuestaRendimiento | None:
    """El rendimiento propuesto al componer un APU, con la dispersión que lo respalda.

    Lo observado pesa más que lo declarado: se propone el MEDIDO más reciente y, solo si no hay
    ninguno, el registro más reciente (estimado). El tipo viaja declarado en el contrato: el
    llamador siempre sabe qué le están proponiendo (UC‑06).
    """
    historico = Catalogo(session).rendimientos(codigo_partida)
    if not historico:
        return None
    medidos = [r for r in historico if r.tipo is TipoRendimiento.MEDIDO]
    elegido = medidos[-1] if medidos else historico[-1]
    dispersion = _dispersion_de(historico)
    assert dispersion is not None  # historico no vacío
    return PropuestaRendimiento(rendimiento=elegido, dispersion=dispersion)


def advertencia_rendimiento(dispersion: DispersionRendimiento | None, valor: Decimal) -> str | None:
    """El texto de advertencia de RF‑27 si `valor` se aparta del comportamiento observado.

    `None` cuando no hay nada que advertir: valor dentro del rango [minimo, maximo], o menos de
    `MINIMO_OBSERVADO_PARA_ADVERTIR` observaciones. La advertencia informa, nunca impide: quien
    registra decide («sin impedir el registro», docs/ERS.md).
    """
    if dispersion is None or dispersion.observaciones < MINIMO_OBSERVADO_PARA_ADVERTIR:
        return None
    if dispersion.minimo <= valor <= dispersion.maximo:
        return None
    return (
        f"el rendimiento {valor} se aparta del comportamiento observado de la partida: "
        f"rango [{dispersion.minimo}, {dispersion.maximo}] en {dispersion.observaciones} "
        f"observaciones ({dispersion.medidos} medidas); el registro se completa igualmente"
    )


def justificar_rendimiento(
    session: Session, codigo_partida: str, texto: str, advertencia: str, fecha: date
) -> models.JustificacionRendimiento:
    """UC‑06, flujo 4a: registra la justificación con la que se acepta la advertencia de RF‑27.

    Se liga al **último** rendimiento registrado de la partida (el de mayor `id`): el que acaba de
    registrar `registrar_rendimiento` o `Catalogo.reemplazar_composicion` en la misma transacción.
    Un rendimiento tiene a lo sumo una justificación (tabla aditiva `justificacion_rendimiento`,
    expediente C6.1). `ValueError` si el texto o la advertencia están vacíos o si ese rendimiento
    ya tiene justificación; `KeyError` si la partida no existe y `LookupError` si no tiene
    rendimientos. Hace `flush`, no `commit`, como el resto del módulo.
    """
    if not texto.strip():
        raise ValueError("la justificacion de la advertencia no puede estar vacia")
    if not advertencia.strip():
        raise ValueError(
            "no hay advertencia que justificar: la justificacion acompana a una advertencia de "
            "rendimiento (UC-06, flujo 4a)"
        )
    partida = Catalogo(session).partida(codigo_partida)
    ultimo = session.scalars(
        select(models.Rendimiento)
        .where(models.Rendimiento.partida_id == partida.id)
        .order_by(models.Rendimiento.id.desc())
        .limit(1)
    ).one_or_none()
    if ultimo is None:
        raise LookupError(f"la partida {codigo_partida} no tiene rendimientos que justificar")
    if session.get(models.JustificacionRendimiento, ultimo.id) is not None:
        raise ValueError(
            f"el ultimo rendimiento de {codigo_partida} ya tiene justificacion: registre el "
            "rendimiento nuevo antes de justificarlo"
        )
    justificacion = models.JustificacionRendimiento(
        rendimiento_id=ultimo.id, texto=texto, advertencia=advertencia, fecha=fecha
    )
    session.add(justificacion)
    session.flush()
    return justificacion


def _dispersion_de(historico: list[Rendimiento]) -> DispersionRendimiento | None:
    if not historico:
        return None
    valores = [rendimiento.valor for rendimiento in historico]
    medidos = sum(1 for r in historico if r.tipo is TipoRendimiento.MEDIDO)
    return DispersionRendimiento(
        observaciones=len(valores),
        media=sum(valores) / len(valores),
        minimo=min(valores),
        maximo=max(valores),
        medidos=medidos,
        estimados=len(historico) - medidos,
    )
