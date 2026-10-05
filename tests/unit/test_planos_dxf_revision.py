"""Correcciones de la revision de SF5 sobre la importacion de DXF (spec §6.6.1, RF-50, RNF-12).

Cubre la altura de un punto sin atributo ALTURA, la frontera del alto provisional (RS-15) y el
tope de entidades tras abrir el archivo (RNF-12, riesgo de memoria). Las cifras son literales de lo
dibujado, no la salida del importador.
"""

from __future__ import annotations

import datetime
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from adapters.espacio import SuperficiePunto
from adapters.espacio.planos.dxf import MAX_ENTIDADES_DXF, importar_dxf
from adapters.espacio.planos.informe import EstadoImportacion, TipoItem, cargar_alturas
from adapters.espacio.reglas import ALTO_PROVISIONAL, ALTURA_PENDIENTE, OrigenDeLaMedida
from core.contracts.presupuesto import Presupuesto
from tests.unit.test_planos_dxf import plano_base, tipos

D = Decimal
VACIO = Presupuesto(codigo="X", fecha=datetime.date(2026, 1, 1), moneda="USD", partidas=())
OF001 = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "planos" / "of001.dxf"


# --- altura de un punto sin atributo ALTURA: cota z de la insercion ----------


def test_un_bloque_sin_altura_con_cota_z_usa_la_cota_y_marca_la_altura_pendiente():
    p = plano_base()
    p.bloque("PTO-DATOS", 1, 1, id="X", z=0.45)
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    pto = r.puntos[0]
    assert pto.posicion.z == D("0.45")  # la z de la insercion
    assert pto.superficie is SuperficiePunto.PARED  # z > 0
    assert ALTURA_PENDIENTE in pto.especificaciones
    assert any("sin atributo ALTURA" in i.mensaje for i in tipos(r, TipoItem.PENDIENTE))


def test_un_bloque_sin_altura_y_con_z_cero_queda_en_el_piso_y_tambien_pendiente():
    p = plano_base()
    p.bloque("PTO-DRENAJE", 1, 1, id="X", z=0.0)
    pto = importar_dxf(p.bytes(), nombre="a.dxf").puntos[0]
    assert pto.posicion.z == D(0)
    assert pto.superficie is SuperficiePunto.PISO
    assert ALTURA_PENDIENTE in pto.especificaciones


def test_el_atributo_altura_gana_sobre_la_cota_z_de_la_insercion():
    p = plano_base()
    p.bloque("PTO-DATOS", 1, 1, id="X", z=0.45, altura="0.3")
    pto = importar_dxf(p.bytes(), nombre="a.dxf").puntos[0]
    assert pto.posicion.z == D("0.3") and ALTURA_PENDIENTE not in pto.especificaciones


# --- RS-15: frontera del alto provisional (falso positivo declarado) ----------


def _r8_de_altura(espacio) -> list[str]:
    return [
        h.origen_ids[0]
        for h in OrigenDeLaMedida(espacio).evaluar(VACIO)
        if "altura pendiente" in h.descripcion and h.origen_ids[0].startswith("esp_ambientes")
    ]


def _con_alto(resultado, alto: Decimal):
    return replace(
        resultado, ambientes=tuple(replace(a, alto=alto) for a in resultado.ambientes)
    ).espacio()


def test_rs15_alto_exactamente_2_5_con_la_marca_puesta_sigue_en_advertencia():
    """Falso positivo conocido: un alto REAL de 2,5 m con la marca `altura=pendiente` coincide con
    el provisional y R8 sigue avisando hasta `cargar_alturas` (que quita la marca)."""
    r = importar_dxf(plano_base().bytes(), nombre="a.dxf")
    assert ALTO_PROVISIONAL == D("2.5")
    assert _r8_de_altura(_con_alto(r, D("2.5"))) == ["esp_ambientes:COCINA", "esp_ambientes:SALA"]


def test_rs15_alto_distinto_de_2_5_ya_no_avisa_aunque_la_marca_siga():
    r = importar_dxf(plano_base().bytes(), nombre="a.dxf")
    assert _r8_de_altura(_con_alto(r, D("2.501"))) == []
    assert _r8_de_altura(_con_alto(r, D("2.499"))) == []


def test_rs15_tras_cargar_alturas_con_2_5_se_quita_la_marca_y_no_avisa():
    r = importar_dxf(plano_base().bytes(), nombre="a.dxf")
    cargado = cargar_alturas(r, {"SALA": D("2.5"), "COCINA": D("2.5")})
    assert _r8_de_altura(cargado.espacio()) == []
    assert not [
        i for i in cargado.informe if i.tipo is TipoItem.PENDIENTE and i.tabla == "esp_ambientes"
    ]


# --- RNF-12: tope de entidades tras abrir el archivo ----------


def test_el_tope_por_defecto_es_una_constante_con_nombre():
    assert MAX_ENTIDADES_DXF == 100_000


def test_un_dxf_con_mas_entidades_que_el_tope_se_rechaza_sin_traza():
    p = plano_base()  # 2 polilineas + 2 textos = 4 entidades
    for i in range(7):
        p.bloque("PTO-DATOS", 1, 1, id=f"P{i}", altura="0.3")
    r = importar_dxf(p.bytes(), nombre="denso.dxf", max_entidades=10)  # 11 entidades > 10
    assert r.estado is EstadoImportacion.RECHAZADA
    assert r.espacio().vacio
    assert "denso.dxf" in r.mensaje and "11" in r.mensaje and "10" in r.mensaje
    assert "tope" in r.mensaje
    assert "Traceback" not in r.mensaje and "\n" not in r.mensaje


def test_un_dxf_con_exactamente_el_tope_de_entidades_se_importa():
    p = plano_base()  # 4 entidades
    assert importar_dxf(p.bytes(), nombre="a.dxf", max_entidades=4).estado is (
        EstadoImportacion.IMPORTADA
    )
    assert importar_dxf(p.bytes(), nombre="a.dxf", max_entidades=3).estado is (
        EstadoImportacion.RECHAZADA
    )


def test_el_tope_tambien_rige_para_una_ruta(tmp_path):
    ruta = tmp_path / "a.dxf"
    ruta.write_bytes(plano_base().bytes())
    assert importar_dxf(ruta, max_entidades=2).estado is EstadoImportacion.RECHAZADA


def test_el_tope_por_defecto_no_rechaza_el_dxf_de_of001():
    assert importar_dxf(OF001).estado is EstadoImportacion.IMPORTADA
