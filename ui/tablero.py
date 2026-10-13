"""Datos del tablero del proyecto, sin Streamlit ni pandas (PLAN_SILICE_UI, tarea 2).

El tablero es de **solo lectura** (RU-10): lee la version vigente con
`core.budget.persistencia.cargar_elaboracion`, que reconstruye el presupuesto y su informe sin
escribir, y el control de obra con `ui.control` (0.7.0). Aqui solo se arman filas y tarjetas; la
pantalla `ui/paginas/tablero.py` las pinta y `ui/graficos.py` las dibuja.

Las filas para graficos llevan una columna `float` (`monto`, `Acumulado`) solo para dibujar; el
texto que se muestra sale del `Decimal` con `ui.estilo`. Las etiquetas de `Tarjeta.rotulo` son
textos del sistema: van a la etiqueta de `st.metric`, que interpreta Markdown (RU-9).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget.equilibrio import PuntoEquilibrio, punto_equilibrio
from core.budget.persistencia import cargar_elaboracion
from core.budget.presupuesto import ResultadoElaboracion
from core.budget.valor_ganado import Indicadores
from core.catalog import Catalogo
from core.contracts import ParametrosCosto, Severidad
from core.contracts.presupuesto import Presupuesto
from core.verification.texto import formatear_decimal
from ui import control, hoja
from ui.estilo import NO_DISPONIBLE, dinero, indice, porcentaje

CERO = Decimal(0)
PARTIDAS_EN_PARETO = 10


@dataclass(frozen=True, slots=True)
class Tarjeta:
    """Una tarjeta del tablero: etiqueta del sistema, valor y una ayuda opcional."""

    rotulo: str
    valor: str
    detalle: str = ""


@dataclass(frozen=True, slots=True)
class DatosControl:
    """El control de obra al ultimo corte, o el motivo por el que no hay (`indicadores` None)."""

    indicadores: Indicadores | None
    curva: list[dict[str, object]]
    motivo: str


@dataclass(frozen=True, slots=True)
class DatosTablero:
    """Todo lo que pinta el tablero, leido en una sola sesion."""

    proyecto: str
    codigo: str
    fecha: date
    elaboracion: ResultadoElaboracion
    equilibrio: PuntoEquilibrio
    versiones: list[dict[str, object]]
    control: DatosControl


# --- lectura -------------------------------------------------------------------------------------


def _version(sesion: Session, proyecto: str, codigo: str) -> models.Presupuesto:
    return sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
    ).one()


def leer_tablero(sesion: Session, catalogo: Catalogo, proyecto: str) -> DatosTablero | None:
    """El tablero de la version vigente del proyecto; `None` si no tiene version guardada.

    `ValueError` si el catalogo ya no reconstruye la version (`cargar_presupuesto`): la pantalla
    lo muestra y no pinta cifras.
    """
    codigo = hoja.codigo_vigente(sesion, proyecto)
    if codigo is None:
        return None
    modelo = _version(sesion, proyecto, codigo)
    elaboracion = cargar_elaboracion(sesion, proyecto, codigo, catalogo)
    parametros = ParametrosCosto(
        fcas=modelo.fcas,
        bono_alimentacion=modelo.bono_alimentacion,
        administracion=modelo.administracion,
        utilidad=modelo.utilidad,
    )
    return DatosTablero(
        proyecto=proyecto,
        codigo=codigo,
        fecha=modelo.fecha,
        elaboracion=elaboracion,
        equilibrio=punto_equilibrio(elaboracion.presupuesto, parametros),
        versiones=filas_comparativo(sesion, proyecto),
        control=leer_control(sesion, catalogo, proyecto),
    )


def leer_control(sesion: Session, catalogo: Catalogo, proyecto: str) -> DatosControl:
    """El control al corte por defecto (la ultima valuacion), sin escribir."""
    if not control.tiene_linea_base(sesion, proyecto):
        return DatosControl(None, [], "Sin linea base de control: declarela en Control de obra.")
    if not control.hay_valuaciones(sesion, proyecto):
        return DatosControl(None, [], "La linea base esta declarada; falta la primera valuacion.")
    try:
        resultado = control.calcular_el_control(
            sesion, proyecto, catalogo, corte=control.corte_por_defecto(sesion, proyecto)
        )
        curva = control.curva_pv_ev_ac(sesion, resultado)
    except (control.ControlInvalido, ValueError, LookupError) as error:
        return DatosControl(None, [], str(error))
    return DatosControl(resultado.indicadores, curva, "")


def filas_comparativo(sesion: Session, proyecto: str) -> list[dict[str, object]]:
    """Una fila por version no descartada, de la mas antigua a la mas reciente.

    Los totales salen de las filas guardadas (`partida_presupuestada.total`), sumados en Python
    con `Decimal`: no se recalcula nada.
    """
    filas: list[dict[str, object]] = []
    for version in hoja.historial_de_versiones(sesion, proyecto):
        if version.descartada:
            continue
        modelo = _version(sesion, proyecto, version.codigo)
        total = sum((r.total for r in modelo.partidas), CERO)
        directo = sum((r.cantidad * r.costo_directo for r in modelo.partidas), CERO)
        filas.append(
            {
                "Version": version.codigo,
                "Fecha": version.fecha.isoformat(),
                "Motivo": version.motivo or "elaborada",
                "Costo directo": dinero(directo, modelo.moneda),
                "Total": dinero(total, modelo.moneda),
                "Vigente": "si" if version.vigente else "",
                "total": float(total),
            }
        )
    return filas


# --- tarjetas ------------------------------------------------------------------------------------


def _costo_directo(presupuesto: Presupuesto) -> Decimal:
    return sum((p.item.cantidad * p.resultado.costo_directo for p in presupuesto.partidas), CERO)


def tarjetas_del_presupuesto(datos: DatosTablero) -> list[Tarjeta]:
    """Total, costo directo, punto de equilibrio y auditoria de la version vigente."""
    presupuesto = datos.elaboracion.presupuesto
    moneda = presupuesto.moneda
    pe = datos.equilibrio
    informe = datos.elaboracion.informe
    cuenta = Counter(h.severidad for h in informe.hallazgos)
    detalle = ", ".join(f"{cuenta[s]} {s.name.lower()}" for s in reversed(Severidad) if cuenta[s])
    return [
        Tarjeta("Total del contrato", dinero(presupuesto.total, moneda)),
        Tarjeta("Costo directo", dinero(_costo_directo(presupuesto), moneda)),
        Tarjeta(
            "Punto de equilibrio",
            NO_DISPONIBLE if pe.porcentaje is None else f"{formatear_decimal(pe.porcentaje, 2)} %",
            pe.mensaje,
        ),
        Tarjeta(
            "Auditoria",
            "CUMPLE" if informe.cumple else "NO CUMPLE",
            detalle or "sin hallazgos",
        ),
    ]


def avance_fisico(indicadores: Indicadores | None) -> Decimal | None:
    """EV / BAC, la fraccion ganada del presupuesto; `None` sin control o con BAC cero."""
    if indicadores is None or indicadores.bac == CERO:
        return None
    return indicadores.ev / indicadores.bac


def tarjetas_de_control(datos: DatosControl, moneda: str) -> list[Tarjeta]:
    """Avance fisico, SPI, CPI y EAC al corte; cada «no disponible» con su motivo."""
    ind = datos.indicadores
    if ind is None:
        return []
    motivo = ind.no_disponible
    return [
        Tarjeta("Avance fisico (EV/BAC)", porcentaje(avance_fisico(ind))),
        Tarjeta("SPI (plazo)", indice(ind.spi), motivo.get("SPI", "")),
        Tarjeta("CPI (costo)", indice(ind.cpi), motivo.get("CPI") or motivo.get("AC", "")),
        Tarjeta(
            "EAC (costo final estimado)",
            dinero(ind.eac_indice, moneda),
            # La tarjeta es el EAC por indice (BAC / CPI): falta solo si falta el CPI. La clave
            # "EAC" de `no_disponible` habla del EAC del sistema y es el ultimo respaldo.
            ""
            if ind.eac_indice is not None
            else motivo.get("CPI") or motivo.get("AC") or motivo.get("EAC", ""),
        ),
    ]


# --- filas para graficos -------------------------------------------------------------------------


def filas_de_desglose(presupuesto: Presupuesto) -> list[dict[str, object]]:
    """El total del contrato por rubro. Los cinco suman exactamente `presupuesto.total`.

    Administracion = cantidad x (con_administracion - costo_directo); utilidad = cantidad x
    (precio_unitario - con_administracion), la cascada de `core.costing.motor.calcular_apu`.
    Lista vacia si el total es cero.
    """
    montos = dict.fromkeys(
        ("Materiales", "Equipos", "Mano de obra", "Administracion", "Utilidad"), CERO
    )
    for partida in presupuesto.partidas:
        q, r = partida.item.cantidad, partida.resultado
        montos["Materiales"] += q * r.materiales
        montos["Equipos"] += q * r.equipos
        montos["Mano de obra"] += q * r.mano_obra
        montos["Administracion"] += q * (r.con_administracion - r.costo_directo)
        montos["Utilidad"] += q * (r.precio_unitario - r.con_administracion)
    total = presupuesto.total
    if total == CERO:
        return []
    return [
        {
            "Rubro": rubro,
            "Monto": dinero(monto, presupuesto.moneda),
            "Peso": porcentaje(monto / total),
            "monto": float(monto),
        }
        for rubro, monto in montos.items()
    ]


def filas_pareto(presupuesto: Presupuesto, n: int = PARTIDAS_EN_PARETO) -> list[dict[str, object]]:
    """Las `n` partidas de mayor total (sumando sus renglones), con su peso y el acumulado, y una
    fila «Resto» si hay mas. Lista vacia si el total es cero."""
    total = presupuesto.total
    if total == CERO:
        return []
    por_partida: dict[str, tuple[str, Decimal]] = {}
    for partida in presupuesto.partidas:
        codigo = partida.item.codigo_partida
        descripcion, monto = por_partida.get(codigo, (partida.apu.descripcion, CERO))
        por_partida[codigo] = (descripcion, monto + partida.total)
    orden = sorted(por_partida.items(), key=lambda par: (-par[1][1], par[0]))
    filas: list[dict[str, object]] = []
    acumulado = CERO
    for codigo, (descripcion, monto) in orden[:n]:
        acumulado += monto
        filas.append(
            {
                "Partida": codigo,
                "Descripcion": descripcion,
                "Total": dinero(monto, presupuesto.moneda),
                "Peso": porcentaje(monto / total),
                "Acumulado": porcentaje(acumulado / total),
                "monto": float(monto),
            }
        )
    if len(orden) > n:
        resto = total - acumulado
        filas.append(
            {
                "Partida": f"Resto ({len(orden) - n})",
                "Descripcion": "las demas partidas",
                "Total": dinero(resto, presupuesto.moneda),
                "Peso": porcentaje(resto / total),
                "Acumulado": porcentaje(Decimal(1)),
                "monto": float(resto),
            }
        )
    return filas


def filas_de_curvas(
    presupuesto: Presupuesto, control_obra: DatosControl
) -> list[dict[str, object]]:
    """Filas largas (Orden, Periodo, Serie, Acumulado) para la curva del tablero.

    Con control: PV, EV y AC acumulados al cierre de cada periodo (el AC falta donde un costo no
    tiene tasa). Sin control: el plan acumulado del presupuesto (RU-12).
    """
    if control_obra.indicadores is not None:
        filas = []
        for orden, punto in enumerate(control_obra.curva, start=1):
            for serie in ("PV", "EV", "AC"):
                valor = punto[serie]
                if valor is not None:
                    filas.append(
                        {
                            "Orden": orden,
                            "Periodo": str(punto["Periodo"]),
                            "Serie": serie,
                            "Acumulado": float(valor),
                        }
                    )
        return filas
    return [
        {"Orden": orden, "Periodo": p.periodo, "Serie": "Plan", "Acumulado": float(p.acumulado)}
        for orden, p in enumerate(presupuesto.curva, start=1)
    ]
