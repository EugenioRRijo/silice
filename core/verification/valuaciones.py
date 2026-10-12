# core/verification/valuaciones.py
"""SL-E4: reglas R13 y R14 de las valuaciones de obra (spec S2 §3.4; RF-74).

Son `ReglaVerificacion` del contrato, sin cambios, y se construyen con la **instantánea de
control** (`InstantaneaDeControl`): la línea base (partidas, cantidades y unitarios), su
calendario y las valuaciones registradas y no anuladas. Entran por `reglas=` como R8-R12; **no**
entran en `REGLAS`, así que el 7 de 7 y las huellas de RNF-04 no se mueven. El `Presupuesto` que
reciben `evaluar` no se lee: la regla habla de las valuaciones, no de las partidas.

**R13 Valuación dentro del presupuesto**: (a) el acumulado no anulado de una partida supera su
cantidad de la línea base (ERROR, impacto = exceso x unitario base; la igualdad pasa); (b) partida
valuada que la línea base no tiene (ERROR, sin impacto: no hay unitario); (c) partida presupuestada
que el plan no programa en ningún período (ADVERTENCIA).

**R14 Fuente y fechas de la valuación**: (a) falta número, inspector o fecha (ERROR); (b) *desde*
posterior a *hasta*, fecha anterior a *hasta*, *hasta* posterior al corte o *desde* anterior al
inicio del calendario (ERROR); (c) períodos solapados o número repetido (ERROR); (d) fecha de
medición de una línea fuera de [*desde*, *hasta*] (ERROR); (e) números no consecutivos con el patrón
prefijo + número (ADVERTENCIA); (f) hueco de al menos un día hábil entre dos valuaciones
consecutivas (INFO).

Cada hallazgo cita en `origen_ids` la clave de la línea (`valuacion:<número>:<código>`) y, si la
línea base tiene la partida, el `origen_id` de su ítem, para que el informe atribuya la partida
(C5.1). Los hallazgos salen en un orden estable: por valuación en el orden recibido y, dentro de
ella, por línea. Este módulo no importa `core.budget`: el calendario llega como función
(`habiles_entre`), que arma quien construye la instantánea.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad

__all__ = [
    "CODIGO_R13",
    "CODIGO_R14",
    "FuenteYFechasDeValuacion",
    "InstantaneaDeControl",
    "LineaValuacion",
    "PartidaBase",
    "Valuacion",
    "ValuacionDentroDelPresupuesto",
    "reglas_de_control",
]

CODIGO_R13 = "R13"
CODIGO_R14 = "R14"
CERO = Decimal(0)
_NUMERO = re.compile(r"^(.*?)(\d+)$")


@dataclass(frozen=True, slots=True)
class LineaValuacion:
    """La cantidad ejecutada de una partida en una valuación (del período, no acumulada)."""

    codigo_partida: str
    cantidad: Decimal
    fecha_medicion: date | None = None
    observacion: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.cantidad, Decimal) or not self.cantidad.is_finite():
            raise ValueError(f"la cantidad de {self.codigo_partida!r} debe ser un Decimal finito")
        if self.cantidad < CERO:
            raise ValueError(
                f"la cantidad de {self.codigo_partida!r} no puede ser negativa ({self.cantidad}): "
                "una correccion es una anulacion"
            )


@dataclass(frozen=True, slots=True)
class Valuacion:
    """Una valuación registrada. `numero`, `inspector` y `fecha` pueden faltar: R14 los marca.

    `id` es 0 mientras no está guardada. `origen` dice si se escribió a mano o de qué archivo
    salió; `fecha_hora` es el momento del registro, desde el cual cuenta (S2-R14).
    """

    id: int
    numero: str
    desde: date
    hasta: date
    fecha: date | None
    inspector: str
    lineas: tuple[LineaValuacion, ...]
    origen: str = "manual"
    fuente: str = ""
    responsable: str = ""
    fecha_hora: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "lineas", tuple(self.lineas))

    @property
    def clave(self) -> str:
        """El número, o `#<id>` si falta: la clave que citan los hallazgos."""
        return self.numero.strip() or f"#{self.id}"


@dataclass(frozen=True, slots=True)
class PartidaBase:
    """Una partida de la línea base: su cantidad, su unitario según la perspectiva, el
    `origen_id` de su ítem de cómputo y si el plan la programa en algún período."""

    codigo: str
    cantidad: Decimal
    unitario: Decimal
    origen_id: str
    programada: bool = True


@dataclass(frozen=True)
class InstantaneaDeControl:
    """Lo que R13 y R14 miran (S2 §3.4): las valuaciones registradas y no anuladas, la línea base
    y el calendario, al `corte`. `habiles_entre(a, b)` cuenta los días hábiles de [a, b]."""

    corte: date
    inicio: date
    partidas: tuple[PartidaBase, ...]
    valuaciones: tuple[Valuacion, ...]
    habiles_entre: Callable[[date, date], int] = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "partidas", tuple(self.partidas))
        object.__setattr__(self, "valuaciones", tuple(self.valuaciones))


def _n(valor: Decimal) -> str:
    """Un decimal tal cual, sin ceros de relleno ni notación científica (mensajes deterministas)."""
    return format(valor.normalize(), "f")


def _dia(valor: date) -> str:
    return valor.isoformat()


def _origenes(
    instantanea: InstantaneaDeControl, valuacion: Valuacion, codigo: str | None = None
) -> tuple[str, ...]:
    clave = f"valuacion:{valuacion.clave}" + (f":{codigo}" if codigo else "")
    partida = next((p for p in instantanea.partidas if p.codigo == codigo), None)
    return (clave,) if partida is None else (clave, partida.origen_id)


def _hallazgo(
    regla: str,
    severidad: Severidad,
    descripcion: str,
    origenes: tuple[str, ...],
    *,
    impacto: Decimal | None = None,
    observado: Decimal | None = None,
    esperado: Decimal | None = None,
) -> Hallazgo:
    return Hallazgo(
        regla=regla,
        severidad=severidad,
        descripcion=descripcion,
        impacto=impacto,
        origen_ids=origenes,
        valor_observado=observado,
        valor_esperado=esperado,
    )


class ValuacionDentroDelPresupuesto(ReglaVerificacion):
    """R13: lo valuado no supera lo presupuestado ni sale de la línea base."""

    codigo = CODIGO_R13
    nombre = "Valuacion dentro del presupuesto"

    def __init__(self, instantanea: InstantaneaDeControl) -> None:
        self._instantanea = instantanea

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        instantanea = self._instantanea
        base = {p.codigo: p for p in instantanea.partidas}
        acumulado: dict[str, Decimal] = defaultdict(lambda: CERO)
        # Un evento por partida: la primera valuacion que la cita sin base o que la excede.
        eventos: list[tuple[str, Valuacion]] = []
        vistas: set[str] = set()
        for valuacion in instantanea.valuaciones:
            for linea in valuacion.lineas:
                codigo = linea.codigo_partida
                partida = base.get(codigo)
                antes = acumulado[codigo]
                acumulado[codigo] += linea.cantidad
                excede = partida is not None and antes <= partida.cantidad < acumulado[codigo]
                if codigo not in vistas and (partida is None or excede):
                    vistas.add(codigo)
                    eventos.append((codigo, valuacion))
        hallazgos = [
            self._sin_base(valuacion, codigo)
            if codigo not in base
            else self._exceso(valuacion, base[codigo], acumulado[codigo])
            for codigo, valuacion in eventos
        ]
        hallazgos.extend(
            _hallazgo(
                CODIGO_R13,
                Severidad.ADVERTENCIA,
                f"la partida {partida.codigo} esta presupuestada y el plan de la linea base no "
                "la programa en ningun periodo",
                (partida.origen_id,),
            )
            for partida in instantanea.partidas
            if not partida.programada
        )
        return hallazgos

    def _sin_base(self, valuacion: Valuacion, codigo: str) -> Hallazgo:
        return _hallazgo(
            CODIGO_R13,
            Severidad.ERROR,
            f"la valuacion {valuacion.clave} valua la partida {codigo}, que la linea base no "
            "tiene: sin unitario, no se cuantifica",
            _origenes(self._instantanea, valuacion, codigo),
        )

    def _exceso(self, valuacion: Valuacion, partida: PartidaBase, total: Decimal) -> Hallazgo:
        exceso = total - partida.cantidad
        return _hallazgo(
            CODIGO_R13,
            Severidad.ERROR,
            f"la partida {partida.codigo} lleva {_n(total)} valuados y la linea base "
            f"presupuesta {_n(partida.cantidad)}: exceso de {_n(exceso)} desde la valuacion "
            f"{valuacion.clave}",
            _origenes(self._instantanea, valuacion, partida.codigo),
            impacto=exceso * partida.unitario,
            observado=total,
            esperado=partida.cantidad,
        )


class FuenteYFechasDeValuacion(ReglaVerificacion):
    """R14: cada valuación declara su fuente y sus fechas son coherentes entre sí y con el
    calendario."""

    codigo = CODIGO_R14
    nombre = "Fuente y fechas de la valuacion"

    def __init__(self, instantanea: InstantaneaDeControl) -> None:
        self._instantanea = instantanea

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        instantanea = self._instantanea
        hallazgos: list[Hallazgo] = []
        for valuacion in instantanea.valuaciones:
            hallazgos.extend(self._de_la_valuacion(valuacion))
        hallazgos.extend(self._solapes_y_repetidos())
        hallazgos.extend(self._numeracion())
        hallazgos.extend(self._huecos())
        return hallazgos

    def _error(
        self, valuacion: Valuacion, descripcion: str, severidad: Severidad = Severidad.ERROR
    ) -> Hallazgo:
        return _hallazgo(CODIGO_R14, severidad, descripcion, (f"valuacion:{valuacion.clave}",))

    def _de_la_valuacion(self, valuacion: Valuacion) -> list[Hallazgo]:
        instantanea = self._instantanea
        clave = valuacion.clave
        hallazgos: list[Hallazgo] = []
        if not valuacion.numero.strip():
            hallazgos.append(self._error(valuacion, f"la valuacion {clave} no tiene numero"))
        if not valuacion.inspector.strip():
            hallazgos.append(self._error(valuacion, f"la valuacion {clave} no tiene inspector"))
        if valuacion.fecha is None:
            hallazgos.append(self._error(valuacion, f"la valuacion {clave} no tiene fecha"))
        if valuacion.desde > valuacion.hasta:
            hallazgos.append(
                self._error(
                    valuacion,
                    f"la valuacion {clave} empieza el {_dia(valuacion.desde)}, despues de su "
                    f"fin ({_dia(valuacion.hasta)})",
                )
            )
        if valuacion.fecha is not None and valuacion.fecha < valuacion.hasta:
            hallazgos.append(
                self._error(
                    valuacion,
                    f"la valuacion {clave} tiene fecha {_dia(valuacion.fecha)}, anterior a su "
                    f"fin ({_dia(valuacion.hasta)})",
                )
            )
        if valuacion.hasta > instantanea.corte:
            hallazgos.append(
                self._error(
                    valuacion,
                    f"la valuacion {clave} termina el {_dia(valuacion.hasta)}, despues del corte "
                    f"({_dia(instantanea.corte)})",
                )
            )
        if valuacion.desde < instantanea.inicio:
            hallazgos.append(
                self._error(
                    valuacion,
                    f"la valuacion {clave} empieza el {_dia(valuacion.desde)}, antes del inicio "
                    f"del calendario ({_dia(instantanea.inicio)})",
                )
            )
        for linea in valuacion.lineas:
            medida = linea.fecha_medicion
            if medida is not None and not valuacion.desde <= medida <= valuacion.hasta:
                hallazgos.append(
                    _hallazgo(
                        CODIGO_R14,
                        Severidad.ERROR,
                        f"la medicion de {linea.codigo_partida} en la valuacion {clave} es del "
                        f"{_dia(medida)}, fuera de su periodo "
                        f"{_dia(valuacion.desde)} a {_dia(valuacion.hasta)}",
                        _origenes(instantanea, valuacion, linea.codigo_partida),
                    )
                )
        return hallazgos

    def _solapes_y_repetidos(self) -> list[Hallazgo]:
        validas = [v for v in self._instantanea.valuaciones if v.desde <= v.hasta]
        hallazgos: list[Hallazgo] = []
        for i, primera in enumerate(self._instantanea.valuaciones):
            for segunda in self._instantanea.valuaciones[i + 1 :]:
                if primera.numero.strip() and primera.numero.strip() == segunda.numero.strip():
                    hallazgos.append(
                        self._error(segunda, f"el numero {segunda.clave} esta repetido")
                    )
                if (
                    primera in validas
                    and segunda in validas
                    and segunda.desde <= primera.hasta
                    and primera.desde <= segunda.hasta
                ):
                    hallazgos.append(
                        self._error(
                            segunda,
                            f"el periodo de la valuacion {segunda.clave} "
                            f"({_dia(segunda.desde)} a {_dia(segunda.hasta)}) se solapa con el "
                            f"de la {primera.clave} "
                            f"({_dia(primera.desde)} a {_dia(primera.hasta)})",
                        )
                    )
        return hallazgos

    def _numeracion(self) -> list[Hallazgo]:
        por_prefijo: dict[str, list[tuple[int, Valuacion]]] = defaultdict(list)
        for valuacion in self._instantanea.valuaciones:
            encontrado = _NUMERO.match(valuacion.numero.strip())
            if encontrado:
                por_prefijo[encontrado.group(1)].append((int(encontrado.group(2)), valuacion))
        hallazgos: list[Hallazgo] = []
        for numeradas in por_prefijo.values():
            numeradas.sort(key=lambda par: par[0])
            for (antes, anterior), (despues, siguiente) in zip(
                numeradas, numeradas[1:], strict=False
            ):
                if despues - antes > 1:
                    hallazgos.append(
                        self._error(
                            siguiente,
                            f"las valuaciones {anterior.clave} y {siguiente.clave} no son "
                            "consecutivas: falta al menos un numero",
                            Severidad.ADVERTENCIA,
                        )
                    )
        return hallazgos

    def _huecos(self) -> list[Hallazgo]:
        validas = sorted(
            (v for v in self._instantanea.valuaciones if v.desde <= v.hasta),
            key=lambda v: (v.desde, v.hasta),
        )
        hallazgos: list[Hallazgo] = []
        for anterior, siguiente in zip(validas, validas[1:], strict=False):
            primero = anterior.hasta + timedelta(days=1)
            ultimo = siguiente.desde - timedelta(days=1)
            if primero > ultimo:
                continue
            dias = self._instantanea.habiles_entre(primero, ultimo)
            if dias >= 1:
                hallazgos.append(
                    self._error(
                        siguiente,
                        f"entre las valuaciones {anterior.clave} y {siguiente.clave} hay "
                        f"{dias} dia(s) habil(es) sin cubrir ({_dia(primero)} a {_dia(ultimo)})",
                        Severidad.INFO,
                    )
                )
        return hallazgos


def reglas_de_control(instantanea: InstantaneaDeControl) -> tuple[ReglaVerificacion, ...]:
    """R13 y R14 sobre la instantánea: lo que se pasa a `elaborar`/`auditar` por `reglas=`."""
    return (ValuacionDentroDelPresupuesto(instantanea), FuenteYFechasDeValuacion(instantanea))
