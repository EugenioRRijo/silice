"""R6 y el buscador de la referencia MaPreX (Tarea 3): autocompletar evita el hallazgo.

La regla R6 (`CriterioDepreciacion`, `core/verification/reglas.py`) compara el factor de
depreciacion de un mismo insumo entre partidas. Dos personas tecleando 0,20 y 0,25 para la misma
retroexcavadora producen un hallazgo de auditoria legitimo y evitable; autocompletar el factor
desde `buscar_referencia` (Tarea 2, `ui/composicion.py`) es lo que lo evita.

Esta prueba compone dos partidas que comparten el mismo equipo, tomando su factor de
`FilaReferencia` en ambas, las persiste con `Catalogo.cargar_composicion` (con condiciones,
RF-33) y evalua R6 sobre un `Presupuesto` real, no uno inventado para pasar. El caso negativo
(factores distintos) demuestra que la regla si se esta evaluando: una prueba que solo comprueba
el silencio no distingue "la regla esta satisfecha" de "la regla no se esta evaluando".
"""

from __future__ import annotations

from decimal import Decimal

from core.catalog import Catalogo
from core.contracts import (
    ComposicionAPU,
    Dominio,
    ItemComputo,
    LineaEquipo,
    OrigenTipo,
    PartidaPresupuestada,
    Presupuesto,
)
from core.costing import calcular_apu
from core.verification.reglas import CriterioDepreciacion
from tests.fixtures import apu_linea_base as linea_base
from ui.composicion import buscar_referencia

FECHA = linea_base.FECHA_LINEA_BASE


def _fila_retroexcavadora():
    """La fila de referencia que autocompleta el factor de depreciacion en ambas partidas."""
    resultados = buscar_referencia("retroexcavadora", "equipo")
    assert resultados, "la referencia MaPreX debe traer al menos una retroexcavadora"
    return resultados[0]


def _apu_con_equipo(codigo: str, fila, factor: Decimal) -> ComposicionAPU:
    return ComposicionAPU(
        codigo_partida=codigo,
        descripcion=f"Partida de prueba {codigo}",
        unidad="m3",
        rendimiento=Decimal("10"),
        equipos=(
            LineaEquipo(
                descripcion=fila.descripcion,
                cantidad=Decimal("1"),
                precio=fila.precio_usd,
                depreciacion=factor,
            ),
        ),
    )


def _item(codigo: str) -> ItemComputo:
    return ItemComputo(
        codigo_partida=codigo,
        descripcion=f"Partida de prueba {codigo}",
        unidad="m3",
        cantidad=Decimal("5"),
        origen_id=f"manual-{codigo}",
        origen_tipo=OrigenTipo.MANUAL,
        dominio=Dominio.CIVIL,
    )


def _presupuesto_persistido(sesion, composiciones: dict[str, ComposicionAPU]) -> Presupuesto:
    """Persiste cada composicion (RF-33) y arma el `Presupuesto` real que evalua la regla.

    Mismo camino que `tests/fixtures/presupuesto_auditado.py`: `PartidaPresupuestada` con el
    `ComposicionAPU` ya construido y el `ResultadoAPU` del motor, no un doble de prueba.
    """
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(FECHA)
    for composicion in composiciones.values():
        catalogo.cargar_composicion(
            composicion, lista, Dominio.CIVIL, FECHA, "condiciones de prueba de la regla R6"
        )
    sesion.flush()

    partidas = tuple(
        PartidaPresupuestada(
            item=_item(codigo),
            apu=composicion,
            resultado=calcular_apu(composicion, linea_base.PARAMETROS_LINEA_BASE),
        )
        for codigo, composicion in composiciones.items()
    )
    return Presupuesto(
        codigo="PRUEBA-R6", fecha=FECHA, moneda=linea_base.MONEDA, partidas=partidas
    )


def test_mismo_factor_de_la_referencia_r6_no_emite_hallazgo(sesion):
    """Dos partidas, mismo equipo, mismo factor tomado de la misma `FilaReferencia`: R6 calla."""
    fila = _fila_retroexcavadora()
    composiciones = {
        "R6-01": _apu_con_equipo("R6-01", fila, fila.factor_depreciacion),
        "R6-02": _apu_con_equipo("R6-02", fila, fila.factor_depreciacion),
    }
    presupuesto = _presupuesto_persistido(sesion, composiciones)

    assert CriterioDepreciacion().evaluar(presupuesto) == []


def test_factores_distintos_del_mismo_equipo_r6_si_emite_hallazgo(sesion):
    """Misma referencia, pero alguien teclea otro factor a mano: R6 debe hablar, no callar.

    Sin este caso, el test anterior no distingue "la regla esta satisfecha" de "la regla no se
    esta evaluando": este es el que demuestra que R6 realmente corre sobre el presupuesto.
    """
    fila = _fila_retroexcavadora()
    otro_factor = fila.factor_depreciacion + Decimal("0.05")
    composiciones = {
        "R6-03": _apu_con_equipo("R6-03", fila, fila.factor_depreciacion),
        "R6-04": _apu_con_equipo("R6-04", fila, otro_factor),
    }
    presupuesto = _presupuesto_persistido(sesion, composiciones)

    hallazgos = CriterioDepreciacion().evaluar(presupuesto)

    assert len(hallazgos) == 1
    assert hallazgos[0].regla == "R6"
    assert set(hallazgos[0].origen_ids) == {"R6-03", "R6-04"}
