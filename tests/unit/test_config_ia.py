"""Los datos externos que S4.0 verifica: precios, version minima de Ollama y modelo local.

No se inventan: salen de `docs/fuentes/asistente_verificacion.md` (con su fuente y su fecha). La
prueba solo exige que esten, que tengan forma de dato verificado y que el documento los cite.
"""

from __future__ import annotations

import json
import re
from datetime import date

from tests.fixtures.arquitectura import RAIZ

PROTOCOLO = RAIZ / "asistente" / "experimento" / "protocolo.json"
CONFIG_IA = RAIZ / "asistente" / "config_ia.json"
PRECIOS = RAIZ / "asistente" / "precios_ia.json"
VERIFICACION = RAIZ / "docs" / "fuentes" / "asistente_verificacion.md"


def test_la_version_minima_de_ollama_es_un_numero_de_version_citado_en_el_documento():
    config = json.loads(CONFIG_IA.read_text(encoding="utf-8"))
    version = config["version_minima_ollama"]
    assert re.fullmatch(r"\d+(\.\d+)+", version)  # p. ej. 0.9.2
    assert isinstance(config["estructurado"], bool)  # plan B si el modelo no admite herramientas
    texto = VERIFICACION.read_text(encoding="utf-8")
    assert version in texto and "Ollama" in texto


def test_los_precios_traen_fecha_de_verificacion_y_el_documento_la_cita():
    precios = json.loads(PRECIOS.read_text(encoding="utf-8"))
    fecha = precios["fecha_verificacion"]
    assert date.fromisoformat(fecha) <= date.today()
    modelos = precios["usd_por_millon_de_fichas"]
    assert {"claude-opus-5-5", "local"} <= set(modelos)
    for tarifa in modelos.values():
        assert set(tarifa) == {"entrada", "salida", "cache_lectura", "cache_escritura"}
        assert all(float(valor) >= 0 for valor in tarifa.values())
    assert fecha in VERIFICACION.read_text(encoding="utf-8")


def test_el_protocolo_nombra_el_modelo_local_y_el_documento_lo_cita():
    protocolo = json.loads(PROTOCOLO.read_text(encoding="utf-8"))
    assert protocolo["modelo_local"].strip() and protocolo["modelo_local"] != "claude-opus-5-5"
    assert protocolo["modelo_local"] in VERIFICACION.read_text(encoding="utf-8")
