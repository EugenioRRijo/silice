"""`scripts/evaluar_asistente.py`: el informe sale de las corridas; la real exige permiso."""

from __future__ import annotations

import json

import pytest

from scripts.evaluar_asistente import PROTOCOLO, generar_informe, main, medicion_controlada
from tests.fixtures.asistente_corridas import CORRIDAS

PROTO = json.loads(PROTOCOLO.read_text(encoding="utf-8"))
PEQUENO = {**PROTO, "replicas_bootstrap": 500}
HUELLAS = {"banco": "a" * 64, "protocolo": "b" * 64, "auditor": "c" * 64, "commit": "abc1234"}


def test_el_informe_trae_las_cifras_de_la_memoria_y_se_declara_generado():
    texto = generar_informe(CORRIDAS, PEQUENO, {"E2": (24, 24, (0.862, 1.0))}, HUELLAS)
    assert texto.startswith("<!-- GENERADO por scripts/evaluar_asistente.py")
    assert "- banco: `" + "a" * 64 + "`" in texto
    fila = next(linea for linea in texto.splitlines() if linea.startswith("| M | A | 3 |"))
    # 4 detectables, 3 detectados = 75,0 %; falsas alarmas 20,0 % (1 de 5); exhaustividad 91,7 %
    assert "| 4 | 3 | 75,0 % |" in fila and "20,0 %" in fila and "91,7 %" in fila
    assert "NO cumple (se declara la brecha)" in fila  # 75 % < 80 % y 20 % > 10 %
    assert "| E2 | 24 | 24 | [86,2 %; 100,0 %] |" in texto
    assert (
        texto.count("| T1 | M | A |") == 2
        and "| T2 | M | A | 1 | puntuada | E4,E3 | 2 | 0 |" in texto
    )
    assert "Limites declarados" in texto


def test_la_corrida_real_sin_acepto_costo_se_niega_y_no_toca_la_red(capsys):
    argumentos = ["corrida", "--proveedor", "claude", "--conjunto", "desarrollo"]
    codigo = main([*argumentos, "--tope-usd", "5"])
    assert codigo == 2 and "--acepto-costo" in capsys.readouterr().err


def test_la_medicion_controlada_es_determinista_y_da_n_ensayos_por_tipo():
    a = medicion_controlada(PROTO)
    assert a == medicion_controlada(PROTO)
    # n efectivo (mutantes distintos): 24 en E1-E7 y 2 en E8, que solo tiene dos sembrados
    # construibles en el banco de evaluacion (cuenta a mano en test_experimento_mutaciones.py)
    esperado = {f"E{i}": 24 for i in range(1, 8)} | {"E8": 2}
    assert {t: n for t, (_, n, _) in a.items()} == esperado
    assert a["E6"][0] == 0  # sin fila que citar, un elemento omitido no se detecta
    with pytest.raises(KeyError):
        a["E9"]


def test_el_esfuerzo_del_piloto_es_una_opcion_y_la_corrida_real_sigue_exigiendo_permiso(capsys):
    argumentos = ["corrida", "--proveedor", "claude", "--conjunto", "desarrollo", "--tope-usd", "5"]
    assert main([*argumentos, "--esfuerzo", "medium"]) == 2
    with pytest.raises(SystemExit):  # un esfuerzo que no existe lo rechaza el analizador
        main([*argumentos, "--esfuerzo", "enorme", "--acepto-costo"])
    assert "--acepto-costo" in capsys.readouterr().err
