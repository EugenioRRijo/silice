"""Tipos neutrales de proveedor, proveedor guionado y tarifas (S4 §5.3, §8.4, §10.1).

Costos calculados a mano: con la tarifa de Opus 5.5 (4,00 de entrada, 20,00 de salida y 0,20 de
lectura de cache, USD por millon de fichas), 10 000 de entrada + 3 000 de salida + 6 000 de cache
dan 10 000·4/10⁶ + 3 000·20/10⁶ + 6 000·0,2/10⁶ = 0,04 + 0,06 + 0,0012 = 0,1012 USD.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from asistente.proveedores.base import FinTurno, Tarifa, Turno, Uso
from asistente.proveedores.guionado import ProveedorGuionado, guion_desde_archivo, turno_de_json
from asistente.tarifas import cargar_tarifas, fecha_de_los_precios, tarifa_de

USO = Uso(entrada=10_000, salida=3_000, cache_lectura=6_000)


def test_el_costo_de_un_turno_es_la_suma_por_tipo_de_ficha():
    tarifa = Tarifa(Decimal(4), Decimal(20), Decimal("0.2"), Decimal(5))
    assert tarifa.costo(USO) == Decimal("0.1012")
    assert tarifa.costo(Uso(cache_escritura=1_000_000)) == Decimal(5)
    assert tarifa.costo(Uso()) == 0


def test_las_tarifas_salen_del_archivo_con_fecha_y_el_modo_local_cuesta_cero():
    tarifas = cargar_tarifas()
    assert tarifa_de("claude-opus-5-5").costo(USO) == Decimal("0.1012")
    assert tarifas["local"].costo(USO) == 0 and tarifa_de("cualquiera", local=True).costo(USO) == 0
    assert fecha_de_los_precios()[:2] == "20"
    with pytest.raises(KeyError):
        tarifa_de("modelo-sin-tarifa")


def turno(texto="", fin=FinTurno.FIN) -> Turno:
    return Turno(texto, (), fin, Uso(entrada=1), "guion-1")


def test_el_guionado_reproduce_en_orden_guarda_lo_recibido_y_se_agota_con_un_error_claro():
    proveedor = ProveedorGuionado([turno("a"), turno("b")])
    assert proveedor.disponible().disponible and not proveedor.envia_fuera_del_equipo
    assert proveedor.turno("sistema", [], []).texto == "a"
    assert proveedor.turno("otro", [], []).texto == "b"
    assert [r[0] for r in proveedor.recibidos] == ["sistema", "otro"]
    with pytest.raises(AssertionError, match="se agoto"):
        proveedor.turno("x", [], [])


def test_el_guionado_lanza_los_errores_del_guion():
    proveedor = ProveedorGuionado([ConnectionError("sin red")])
    with pytest.raises(ConnectionError):
        proveedor.turno("s", [], [])


def test_una_grabacion_json_se_convierte_en_turnos(tmp_path):
    grabacion = [
        {
            "texto": "hola",
            "llamadas": [{"id": "c1", "nombre": "consultar_borrador", "argumentos": {}}],
            "fin": "herramientas",
            "uso": {"entrada": 12, "salida": 3},
            "modelo": "claude-opus-5-5",
        },
        {"fin": "fin"},
    ]
    ruta = tmp_path / "grabacion.json"
    ruta.write_text(json.dumps(grabacion), encoding="utf-8")
    primero, segundo = guion_desde_archivo(ruta)
    assert primero.llamadas[0].nombre == "consultar_borrador" and primero.uso.entrada == 12
    assert (
        primero.fin is FinTurno.HERRAMIENTAS and primero.modelo_que_respondio == "claude-opus-5-5"
    )
    assert segundo == turno_de_json({"fin": "fin"}) and segundo.uso == Uso()
