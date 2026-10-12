"""El banco de tareas: forma, referencias coherentes, huella y respuestas preparadas (S4 §9.2).

El banco se CONGELA en S4.0 con su huella SHA-256 (`docs/protocolo_asistente.md`); esta prueba
vigila que las fichas sigan siendo las congeladas y que cada referencia sea una hoja valida y
limpia (sin errores de R9 en la propia referencia).
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date

import pytest

from adapters.espacio.reglas import CoherenciaEspacial
from asistente.experimento.banco import (
    CARPETA_TAREAS,
    NO_SE,
    borrador_de_partida,
    cargar_banco,
    huella_del_banco,
    referencia_de,
    respuesta_preparada,
)
from core.contracts import Severidad
from core.contracts.presupuesto import Presupuesto
from ui import hoja

BANCO = cargar_banco()
VACIO = Presupuesto(codigo="X", fecha=date(2026, 1, 1), moneda="USD", partidas=())


def test_hay_cuatro_tareas_de_desarrollo_y_doce_de_evaluacion_con_el_reparto_del_spec():
    cuenta = Counter((f.conjunto, f.especialidad) for f in BANCO.values())
    desarrollo = [f for f in BANCO.values() if f.conjunto == "desarrollo"]
    evaluacion = [f for f in BANCO.values() if f.conjunto == "evaluacion"]
    assert len(desarrollo) == 4 and len(evaluacion) == 12
    assert {f.id[:9] for f in desarrollo} == {"dev-agua-", "dev-datos", "dev-elec-", "dev-mixta"}
    assert sum(f.id.startswith("ev-agua") for f in evaluacion) == 4
    assert sum(f.id.startswith("ev-datos") for f in evaluacion) == 3
    assert sum(f.id.startswith("ev-elec") for f in evaluacion) == 3
    assert sum(f.id.startswith("ev-mixta") for f in evaluacion) == 2
    assert cuenta  # la especialidad de cada ficha esta declarada


def test_tres_de_las_doce_de_evaluacion_traen_errores_sembrados_y_ninguna_de_desarrollo():
    con = sorted(f.id for f in BANCO.values() if f.sembrados)
    assert con == ["ev-agua-04", "ev-datos-03", "ev-elec-03"]


@pytest.mark.parametrize("ficha", BANCO.values(), ids=lambda f: f.id)
def test_cada_referencia_es_una_hoja_valida_que_deriva_y_no_rompe_r9(ficha):
    referencia = referencia_de(ficha)
    items = hoja.items_del_borrador(referencia.espacio, hoja.TODAS)
    assert referencia.espacio.ambientes and referencia.espacio.puntos
    assert items  # el sistema deriva cantidades de la referencia
    r9 = CoherenciaEspacial(referencia.espacio).evaluar(VACIO)
    assert [h for h in r9 if h.severidad >= Severidad.ERROR] == []
    assert borrador_de_partida(ficha, date(2026, 10, 11)).espacio.circuitos == (
        referencia.espacio.circuitos
    )


@pytest.mark.parametrize("ficha", [f for f in BANCO.values() if f.sembrados], ids=lambda f: f.id)
def test_el_valor_sembrado_esta_en_el_pedido_y_difiere_de_la_referencia(ficha):
    referencia = referencia_de(ficha)
    for s in ficha.sembrados:
        literal = str(s.valor).replace(".", ",")
        assert literal in ficha.pedido or f"{literal}0" in ficha.pedido or "0,0" in ficha.pedido
        fila = next(
            e
            for e in (*referencia.espacio.puntos, *referencia.espacio.ambientes)
            if e.id == s.id_referencia
        )
        real = {
            "x": lambda e: e.posicion.x,
            "y": lambda e: e.posicion.y,
            "ancho": lambda e: e.ancho,
        }[s.campo](fila)
        assert real != s.valor


def test_la_huella_es_estable_y_cambia_con_cualquier_byte(tmp_path):
    h1 = huella_del_banco()
    assert h1 == huella_del_banco() and len(h1) == 64
    copia = tmp_path / "tareas"
    copia.mkdir()
    for ruta in CARPETA_TAREAS.glob("*.json"):
        (copia / ruta.name).write_bytes(ruta.read_bytes())
    assert huella_del_banco(copia) == h1
    ruta = copia / "dev-agua-01.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["pedido"] += " "
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    assert huella_del_banco(copia) != h1


def test_respuestas_preparadas_una_que_empareja_una_ambigua_y_una_sin_respuesta():
    ficha = BANCO["ev-agua-04"]
    # empareja por palabras clave (sin tildes ni mayusculas): ["largo"] -> 2,4 m
    assert respuesta_preparada(ficha, "¿Cuál es el LARGO del baño?") == "2,4 m"
    # ambigua: lleva «lavamanos» y «x» (primera respuesta) y tambien «medida» (tercera): gana la 1.ª
    assert respuesta_preparada(ficha, "¿Qué medida tiene la x del lavamanos?") == "2,0 m"
    # ninguna cumple todas sus palabras clave
    assert respuesta_preparada(ficha, "¿De qué color es la pintura?") == NO_SE


def test_la_huella_es_la_misma_con_saltos_de_linea_de_windows_y_de_linux(tmp_path):
    copia = tmp_path / "tareas"
    copia.mkdir()
    for ruta in CARPETA_TAREAS.glob("*.json"):
        (copia / ruta.name).write_bytes(ruta.read_bytes().replace(b"\n", b"\r\n"))
    assert huella_del_banco(copia) == huella_del_banco()
