"""Plan vial, Tarea 11: mutaciones viales y matriz de deteccion. Datos FICTICIOS.

La via es `data/samples/vial/via_ficticia.csv`. El presupuesto que se audita es el coherente, armado
desde los tramos ORIGINALES; el mutante altera los tramos, de modo que presupuesto y tramos dejan de
cuadrar. Detecta quien da algun hallazgo que no sea INFO: VR1 a VR7 o la conciliacion CV2.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal
from pathlib import Path

from adapters.vial.derivacion import derivar_tramos
from adapters.vial.reglas import auditar_vial
from adapters.vial.tabular import leer_tramos
from aplicacion.conciliacion import conciliar
from asistente.experimento.mutaciones_viales import (
    TIPOS_VIALES,
    MutanteVial,
    matriz_de_deteccion,
    sembrar_vial,
)
from core.contracts.apu import ComposicionAPU, ParametrosCosto, ResultadoAPU
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Severidad

VIA = Path(__file__).resolve().parents[2] / "data" / "samples" / "vial" / "via_ficticia.csv"
D = Decimal


def _hojas(objeto):
    """Los valores sueltos de un objeto anidado, con su ruta."""
    if dataclasses.is_dataclass(objeto):
        for campo in dataclasses.fields(objeto):
            yield from (
                (f"{campo.name}.{ruta}", v) for ruta, v in _hojas(getattr(objeto, campo.name))
            )
    elif isinstance(objeto, tuple):
        for i, elemento in enumerate(objeto):
            yield from ((f"{i}.{ruta}", v) for ruta, v in _hojas(elemento))
    else:
        yield "", objeto


def _presupuesto_coherente(tramos) -> Presupuesto:
    cero = D("0")
    partidas = []
    for item in derivar_tramos(tramos):
        apu = ComposicionAPU(item.codigo_partida, item.descripcion, item.unidad, D("1"))
        resultado = ResultadoAPU(cero, cero, cero, cero, cero, D("1"))
        partidas.append(PartidaPresupuestada(item, apu, resultado))
    return Presupuesto("VIAL-ESTRES", date(2026, 10, 31), "Bs", tuple(partidas))


def test_misma_semilla_mismos_mutantes():
    tramos = leer_tramos(VIA)
    a = sembrar_vial(tramos, semilla=7, por_tipo=3)
    assert a == sembrar_vial(tramos, semilla=7, por_tipo=3)
    assert a != sembrar_vial(tramos, semilla=8, por_tipo=3)
    assert {m.tipo for m in a} == set(TIPOS_VIALES)
    assert all(sum(m.tipo == t for m in a) <= 3 for t in TIPOS_VIALES)


def test_cada_tipo_altera_un_solo_campo():
    tramos = tuple(leer_tramos(VIA))
    base = dict(_hojas(tramos))
    for mutante in sembrar_vial(tramos, semilla=11, por_tipo=4):
        cambios = {r for r, v in _hojas(mutante.tramos) if base.get(r) != v}
        assert len(cambios) == 1, (mutante.descripcion, cambios)
        assert mutante.tipo in mutante.descripcion


def test_matriz_sobre_via_ficticia():
    tramos = leer_tramos(VIA)
    presupuesto = _presupuesto_coherente(tramos)

    def detecta(mutante: MutanteVial) -> bool:
        hallazgos = [
            *auditar_vial(mutante.tramos, presupuesto),
            *conciliar(
                presupuesto,
                {},
                ParametrosCosto(),
                items_viales=derivar_tramos(mutante.tramos),
                costos_propios={},
            ),
        ]
        return any(h.severidad != Severidad.INFO for h in hallazgos)

    # La via sin mutar no da hallazgos: lo que se detecta es del mutante.
    assert not detecta(MutanteVial("ninguno", tuple(tramos), ""))
    matriz = matriz_de_deteccion(sembrar_vial(tramos, semilla=2026, por_tipo=3), detecta)
    assert matriz == {
        "EV1_espesor_x10": (3, 3),
        "EV2_densidad_coma": (3, 3),
        "EV3_dosis": (2, 2),
        "EV4_unidad": (3, 3),
        "EV5_digitos": (3, 3),
        "EV6_progresiva": (3, 3),
    }


def test_limite_declarado_las_reglas_viales_solas_no_ven_fresado_base_ni_riego():
    # VR1/VR4 solo miran carpeta y transporte, VR3 mira dosis fuera de rango: un espesor de fresado,
    # base o sub-base, o una dosis de riego aun razonable, solo la conciliacion CV2 los ve.
    tramos = leer_tramos(VIA)
    presupuesto = _presupuesto_coherente(tramos)

    def detecta(mutante: MutanteVial) -> bool:
        return any(h.severidad != Severidad.INFO for h in auditar_vial(mutante.tramos, presupuesto))

    matriz = matriz_de_deteccion(sembrar_vial(tramos, semilla=2026, por_tipo=3), detecta)
    assert matriz == {
        "EV1_espesor_x10": (1, 3),
        "EV2_densidad_coma": (3, 3),
        "EV3_dosis": (1, 2),
        "EV4_unidad": (3, 3),
        "EV5_digitos": (2, 3),
        "EV6_progresiva": (3, 3),
    }
