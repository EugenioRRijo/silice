"""Causas de retraso y atraso por partida (MP-7, Tarea 22; diseño §11, meta 2).

En cada línea de una valuación se puede elegir una causa de `CAUSAS` además de la observación; la
guarda `aplicacion.control.registrar_y_controlar` en la misma transacción que la valuación
(`aplicacion/tablas_causas.py`, solo inserción). `atrasos` dice, por partida, cuántos días hábiles
termina después de su plan según la reproyección del núcleo (que ya usa el avance propio de cada
partida cuando lo hay y, si no, el SPI global) y la última causa declarada para ella.

`core/` no se toca: el atraso sale de `ResultadoControl` tal cual (`reproyeccion.partidas[].fin`
y el plan de cada partida), con `techo_de_dias` del núcleo para el techo. Sin Streamlit, sin
FastAPI y sin `aplicacion.control` (que importa este módulo).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from aplicacion.cifras import texto_de_cifra
from aplicacion.tablas_causas import causas_de_valuaciones
from core.budget.control import ResultadoControl
from core.budget.valor_ganado import techo_de_dias

__all__ = [
    "CAUSAS",
    "MENSAJE_CAUSA_DESCONOCIDA",
    "SIN_CAUSA",
    "Atraso",
    "CausaDesconocida",
    "atrasos",
    "causas_de_las_filas",
    "texto_de_atraso",
]

#: Las causas que se pueden elegir en una línea de valuación (clave → nombre), en su orden.
CAUSAS: Mapping[str, str] = {
    "compra_tardia": "Compra tardía",
    "precio": "Precio",
    "clima": "Lluvia o clima",
    "cambio_cliente": "Cambio del cliente",
    "falta_personal": "Falta de personal",
    "falla_equipo": "Falla de equipo",
    "otra": "Otra",
}
SIN_CAUSA = "sin causa declarada"
#: El rechazo de una causa que no está en `CAUSAS`: no repite lo enviado.
MENSAJE_CAUSA_DESCONOCIDA = "La causa del retraso no está en la lista de causas."


class CausaDesconocida(ValueError):  # noqa: N818
    """La causa de una línea no es una clave de `CAUSAS`."""


@dataclass(frozen=True)
class Atraso:
    """Una partida que termina `dias` días hábiles después de su plan, con la última causa
    declarada para ella (`None` si no hay) y la frase que lo dice."""

    codigo: str
    dias: int
    causa: str | None
    texto: str


def texto_de_atraso(codigo: str, dias: int, causa: str | None) -> str:
    """«{código} atrasada {n} días: {causa}»: «1 día» en singular, los miles con punto y «sin
    causa declarada» si no hay causa."""
    cuantos = f"{texto_de_cifra(Decimal(dias))} {'día' if dias == 1 else 'días'}"
    return f"{codigo} atrasada {cuantos}: {SIN_CAUSA if causa is None else CAUSAS[causa]}"


def causas_de_las_filas(filas: Sequence[Mapping[str, object]]) -> list[tuple[str, str]]:
    """`(partida, causa)` de las líneas de una valuación (las filas de `COLUMNAS_LINEAS` con la
    clave «Causa»), en su orden. Una causa nula o en blanco no deja rastro; una que no está en
    `CAUSAS` levanta `CausaDesconocida` (aunque la línea esté vacía), con un mensaje fijo. Las
    líneas sin partida no dan causa (`lineas_desde_filas` las ignora o las rechaza)."""
    salida = []
    for fila in filas:
        causa = str(fila.get("Causa") or "").strip()
        if not causa:
            continue
        if causa not in CAUSAS:
            raise CausaDesconocida(MENSAJE_CAUSA_DESCONOCIDA)
        partida = str(fila.get("Partida") or "").strip()
        if partida:
            salida.append((partida, causa))
    return salida


def _ultimas_causas(sesion: Session, resultado: ResultadoControl) -> dict[str, str]:
    """La última causa declarada por partida en las valuaciones que cuentan al corte: no
    anuladas (`instantanea.valuaciones`) y con *hasta* hasta el corte."""
    instantanea = resultado.instantanea
    cuentan = {v.id for v in instantanea.valuaciones if v.hasta <= instantanea.corte}
    ultimas: dict[str, str] = {}
    for _, partida, causa in causas_de_valuaciones(sesion, cuentan):
        ultimas[partida] = causa
    return ultimas


def atrasos(sesion: Session, resultado: ResultadoControl) -> list[Atraso]:
    """Las partidas que, reproyectadas, terminan después de su plan, en el orden del presupuesto.

    `dias = ⌈fin − fin_plan⌉` (`techo_de_dias`), con `fin` el día hábil reproyectado de la partida
    y `fin_plan` el último período de su plan con fracción mayor que 0 por los días del período.
    Solo las que tienen `fin` (les queda obra y son proyectables) y `dias > 0`. La causa es la
    última declarada para la partida (la de una valuación anulada no cuenta)."""
    largo = resultado.estado.dias_por_periodo
    planes = {partida.codigo: partida.plan for partida in resultado.estado.partidas}
    ultimas = _ultimas_causas(sesion, resultado)
    salida = []
    for proyeccion in resultado.reproyeccion.partidas:
        plan = planes.get(proyeccion.codigo, ())
        activos = [n for n, fraccion in enumerate(plan, start=1) if fraccion > 0]
        if proyeccion.fin is None or not activos:
            continue
        dias = techo_de_dias(proyeccion.fin - activos[-1] * largo)
        if dias <= 0:
            continue
        causa = ultimas.get(proyeccion.codigo)
        salida.append(
            Atraso(proyeccion.codigo, dias, causa, texto_de_atraso(proyeccion.codigo, dias, causa))
        )
    return salida
