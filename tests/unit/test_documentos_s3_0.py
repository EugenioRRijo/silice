"""Los documentos que S3-0 escribe antes de cualquier código (spec S3 §13.1, §13.5; GS3-0).

Ninguna de estas pruebas importa código de S3: son el oráculo escrito a mano, el catálogo, los
protocolos con su huella y la ERS enmendada. El vector de huella se recalcula aquí con `json` y
`hashlib` solos, sin `core.budget.canonico` (que todavía no existe)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.meta_alpha import Estado
from scripts.meta_silice import evaluar_requisitos
from scripts.meta_silice_s3 import PROTOCOLOS, REQUISITOS_S3_0, huella_de
from tests.fixtures.canonico.ejemplo_v1 import BYTES_EJEMPLO_V1, EJEMPLO_V1, HUELLA_EJEMPLO_V1

RAIZ = Path(__file__).resolve().parents[2]
MEMORIAS = RAIZ / "tests" / "fixtures" / "memorias"
CATALOGO = RAIZ / "tests" / "fixtures" / "errores_planos" / "catalogo.md"


def test_la_ers_define_cada_uc_rf_y_rnf_de_s3_0() -> None:
    texto = (RAIZ / "docs" / "ERS.md").read_text(encoding="utf-8")
    estado, detalle = evaluar_requisitos(texto, REQUISITOS_S3_0)
    assert estado is Estado.OK, detalle


def test_la_ers_declara_rf_100_como_deseable_y_la_enmienda_unica_de_rnf_08() -> None:
    texto = (RAIZ / "docs" / "ERS.md").read_text(encoding="utf-8")
    assert "RF‑100" in texto and "Deseable" in texto
    assert "Enmienda de Sílice 0.8.0" in texto and "RNF‑08" in texto


def test_el_vector_de_huella_se_calcula_aparte_con_el_json_estandar() -> None:
    canonico = json.dumps(
        EJEMPLO_V1, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert len(canonico) == BYTES_EJEMPLO_V1 == 2271
    assert hashlib.sha256(canonico).hexdigest() == HUELLA_EJEMPLO_V1
    assert HUELLA_EJEMPLO_V1 == "b4b952dd4d049df5a18f53c00f2594a077c67f49e2b2fd1fb163cf5999003936"


def test_la_memoria_de_diferencias_trae_las_cifras_escritas_a_mano() -> None:
    texto = (MEMORIAS / "diferencias_s3.md").read_text(encoding="utf-8")
    for cifra in (
        "**840**",
        "**1130**",
        "**250**",
        "**40**",
        "**290**",
        "**550**",
        "**589**",
        "**39**",
        "**48,797375**",
        "**139,15**",
        "**47,532375**",
        "**113,85**",
        "**−59,604**",
        "**+2,928**",
        "**+59,604**",
        "101,640",
        "85,470",
    ):
        assert cifra in texto, cifra


def test_la_memoria_de_atipicos_fija_el_conjunto_esperado_antes_del_codigo() -> None:
    texto = (MEMORIAS / "atipicos_s3.md").read_text(encoding="utf-8")
    for fragmento in ("`{v8}`", "**vacío**", "**7** variaciones", "0,00390625", "(25 − 20) / 20"):
        assert fragmento in texto, fragmento


def test_el_catalogo_de_errores_trae_los_17_bloques_y_sus_tres_controles() -> None:
    ids = [
        linea[4:].strip()
        for linea in CATALOGO.read_text(encoding="utf-8").splitlines()
        if linea.startswith("### ")
    ]
    assert len(ids) == len(set(ids)) == 17 and sum(i.startswith("NO-DET") for i in ids) == 3


def test_los_dos_protocolos_estan_escritos_y_su_huella_coincide() -> None:
    escritas = json.loads((RAIZ / "docs" / "protocolos_s3.json").read_text(encoding="utf-8"))
    assert escritas["algoritmo"] == "sha256" and set(escritas["protocolos"]) == set(PROTOCOLOS)
    for relativa in PROTOCOLOS:
        assert escritas["protocolos"][relativa] == huella_de(RAIZ / relativa), relativa


def test_el_protocolo_de_planos_fija_la_meta_los_controles_y_las_amenazas() -> None:
    texto = (RAIZ / "docs" / "protocolo_deteccion_planos.md").read_text(encoding="utf-8")
    for fragmento in (
        "100 %",
        "cero falsas alarmas",
        "semilla 42",
        "no detectables",
        "validez de constructo",
        "validez externa",
    ):
        assert fragmento in texto.lower().replace("**", ""), fragmento


def test_el_protocolo_del_administrador_fija_condiciones_orden_y_sesgo() -> None:
    texto = (RAIZ / "docs" / "protocolo_indicador_administrador.md").read_text(encoding="utf-8")
    for fragmento in (
        "a mano",
        "con el sistema",
        "contrabalanceado",
        "lista congelada",
        "sesgo del autor",
        "tasa de detección",
        "falsas alarmas",
    ):
        assert fragmento in texto.lower().replace("**", ""), fragmento
