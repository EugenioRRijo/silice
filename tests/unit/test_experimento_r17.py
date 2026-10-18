"""R17 sobre el banco de evaluacion de la medicion controlada (tarea 1.7).

El experimento esta congelado y no mide R17: esta prueba NO cambia la medicion. Toma los mismos
mutantes E5 que `scripts/evaluar_asistente.py::medicion_controlada` (misma semilla y mismo n del
protocolo, mismas 12 referencias de evaluacion) y les aplica solo R17. Oraculo:

* R17 detecta los 24 mutantes E5: cada uno da exactamente UN aviso, y es del punto mutado;
* las 12 referencias dan 0 avisos (sin falsas alarmas);
* el reparto es el del diagnostico: 18 mutantes quitan la fuente (agua, datos y mixta) y 6 el
  circuito (electricidad).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from adapters.espacio.conexion import ConexionDeCadaPunto
from asistente.experimento.banco import cargar_banco, referencia_de
from asistente.experimento.mutaciones import generar
from core.contracts import Severidad
from core.contracts.presupuesto import Presupuesto
from tests.fixtures.asistente_banco import codigos_y_unidades

PROTOCOLO = json.loads(
    (
        Path(__file__).resolve().parents[2] / "asistente" / "experimento" / "protocolo.json"
    ).read_text(encoding="utf-8")
)
SEMILLA = int(PROTOCOLO["semilla"])
N = int(PROTOCOLO["n_por_tipo_de_mutacion"])
VACIO = Presupuesto(codigo="X", fecha=date(2026, 1, 1), moneda="USD", partidas=())
REFERENCIAS = {
    f.id: referencia_de(f) for f in cargar_banco().values() if f.conjunto == "evaluacion"
}
MUTANTES_E5 = generar("E5", REFERENCIAS, SEMILLA, N, codigos_y_unidades())


def _mutado(mutante) -> tuple[str, str]:
    """(id del punto mutado, que se le quito) comparando con su referencia."""
    antes = {p.id: p for p in REFERENCIAS[mutante.tarea].espacio.puntos}
    distintos = [p for p in mutante.espacio.puntos if p != antes[p.id]]
    assert len(distintos) == 1
    (p,) = distintos
    quitado = "circuito" if antes[p.id].circuito_id != p.circuito_id else "fuente"
    return p.id, quitado


def test_el_banco_tiene_12_referencias_y_24_mutantes_e5():
    assert len(REFERENCIAS) == 12
    assert len(MUTANTES_E5) == N == 24


@pytest.mark.parametrize("tarea", sorted(REFERENCIAS))
def test_ninguna_referencia_da_falsa_alarma(tarea):
    assert ConexionDeCadaPunto(REFERENCIAS[tarea].espacio).evaluar(VACIO) == []


@pytest.mark.parametrize("mutante", MUTANTES_E5, ids=[f"{m.tarea}#{m.indice}" for m in MUTANTES_E5])
def test_cada_mutante_e5_da_un_aviso_del_punto_mutado(mutante):
    punto_id, quitado = _mutado(mutante)
    hallazgos = ConexionDeCadaPunto(mutante.espacio).evaluar(VACIO)
    assert len(hallazgos) == 1
    (h,) = hallazgos
    assert (h.regla, h.severidad, h.origen_ids) == (
        "R17",
        Severidad.ADVERTENCIA,
        (f"esp_puntos:{punto_id}",),
    )
    assert f"no tiene {quitado}:" in h.descripcion


def test_r17_detecta_24_de_24_y_el_reparto_es_18_fuentes_y_6_circuitos():
    detectados = sum(1 for m in MUTANTES_E5 if ConexionDeCadaPunto(m.espacio).evaluar(VACIO))
    reparto = sorted(_mutado(m)[1] for m in MUTANTES_E5)
    assert detectados == 24
    assert reparto.count("fuente") == 18
    assert reparto.count("circuito") == 6
