"""Ola 2 de la migración, Elaborar un presupuesto (UC-01) por HTTP en modo «solo calcular».

`POST /presupuestos/calcular` hace lo que la página de Streamlit: elabora y audita sin guardar nada
y devuelve el informe como JSON. Oráculos: el total auditado de la línea base escrito a mano en
`tests/fixtures/apu_linea_base.py` y, para 3b, el rendimiento del histórico de
`tests/fixtures/sin_rendimiento_vigente.py` (100, el MEDIDO más reciente).
"""

from __future__ import annotations

import io
from decimal import Decimal

import openpyxl
import pytest

from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.sin_rendimiento_vigente import FECHA_PRESUPUESTO, dejar_sin_estimado

RUTA = "/presupuestos/calcular"
EXCEL = "/presupuestos/calcular/excel"
DECLARAR = "/presupuestos/calcular/declarar-rendimiento"


def _cuerpo(items, **extra):
    return {"codigo": "P-001", "fecha": "2026-04-28", "moneda": "USD", "items": items, **extra}


def test_calcular_no_guarda_nada_y_devuelve_total_partidas_e_informe(cliente, items_payload):
    respuesta = cliente.post(RUTA, json=_cuerpo(items_payload))

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "P-001" and cuerpo["moneda"] == "USD"
    assert cuerpo["total"] == str(linea_base.TOTAL_PRESUPUESTO_AUDITADO)
    assert len(cuerpo["partidas"]) == len(items_payload)
    assert {p["codigo_partida"] for p in cuerpo["partidas"]} == {
        i["codigo_partida"] for i in items_payload
    }
    informe = cuerpo["informe"]
    assert informe["codigo_presupuesto"] == "P-001"
    assert informe["veredicto"] in ("CUMPLE", "NO CUMPLE")
    assert informe["cumple"] == (informe["veredicto"] == "CUMPLE")
    assert informe["total_hallazgos"] == len(informe["hallazgos"])
    assert sum(s["total"] for s in cuerpo["por_severidad"]) == informe["total_hallazgos"]
    assert informe["reglas_evaluadas"], "el informe declara las reglas que evaluó"
    assert cuerpo["pendientes"] == []
    # Nada se guardó: ni presupuesto ni proyecto nuevo.
    assert cliente.get("/presupuestos").json() == []


def test_el_informe_json_numera_los_hallazgos_y_declara_la_partida(cliente, items_payload):
    cuerpo = cliente.post(RUTA, json=_cuerpo(items_payload)).json()
    hallazgos = cuerpo["informe"]["hallazgos"]

    assert [h["numero"] for h in hallazgos] == list(range(1, len(hallazgos) + 1))
    for h in hallazgos:
        assert set(h) == {
            "numero",
            "regla",
            "severidad",
            "partida",
            "descripcion",
            "impacto",
            "observado",
            "esperado",
            "origen",
        }
    if not hallazgos:
        assert cuerpo["informe"]["sin_hallazgos"]


def test_el_plan_por_defecto_trae_una_fila_por_partida_con_fraccion_uno(cliente, items_payload):
    cuerpo = cliente.post(RUTA, json=_cuerpo(items_payload)).json()
    plan = cuerpo["plan_por_defecto"]

    assert len(plan) == len(items_payload)
    assert {fila["codigo_partida"] for fila in plan} == {i["codigo_partida"] for i in items_payload}
    assert all(fila["fraccion"] == "1" and fila["periodo"] for fila in plan)


def test_un_plan_valido_de_dos_semanas_conserva_el_total(cliente, items_payload):
    codigos = [i["codigo_partida"] for i in items_payload]
    filas = [{"periodo": "S1", "codigo_partida": c, "fraccion": "0.5"} for c in codigos] + [
        {"periodo": "S2", "codigo_partida": c, "fraccion": "0.5"} for c in codigos
    ]

    respuesta = cliente.post(RUTA, json=_cuerpo(items_payload, plan=filas))

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["total"] == str(linea_base.TOTAL_PRESUPUESTO_AUDITADO)


def test_un_plan_que_no_suma_uno_es_422(cliente, items_payload):
    codigo = items_payload[0]["codigo_partida"]
    filas = [{"periodo": "S1", "codigo_partida": codigo, "fraccion": "0.5"}]

    respuesta = cliente.post(RUTA, json=_cuerpo(items_payload, plan=filas))

    assert respuesta.status_code == 422
    assert codigo in respuesta.json()["detalle"]


def test_una_fila_del_plan_a_medias_es_422_con_su_numero(cliente, items_payload):
    filas = [
        {"periodo": "", "codigo_partida": "", "fraccion": ""},  # fila en blanco: se ignora
        {"periodo": "S1", "codigo_partida": "", "fraccion": "1"},
    ]

    respuesta = cliente.post(RUTA, json=_cuerpo(items_payload, plan=filas))

    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"] == (
        "plan de trabajo, fila 2: declare el periodo, la partida y la fraccion"
    )


def test_un_item_sin_partida_queda_pendiente_con_sus_propuestas(cliente, items_payload):
    items = [dict(i) for i in items_payload]
    items.append(
        {
            "codigo_partida": "NO-EXISTE-99",
            "descripcion": "Excavación manual de zanja",
            "unidad": "m3",
            "cantidad": "2.5",
            "origen_id": "T-99",
            "origen_tipo": "manual",
            "dominio": "civil",
        }
    )

    respuesta = cliente.post(RUTA, json=_cuerpo(items))

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    (pendiente,) = cuerpo["pendientes"]
    assert pendiente["codigo_partida"] == "NO-EXISTE-99"
    assert pendiente["cantidad"] == "2.5"  # exacta
    assert pendiente["origen_id"] == "T-99"
    assert isinstance(pendiente["propuestas"], list)  # vacía sin el extra ml
    assert "falla" in pendiente
    assert cuerpo["total"] == str(linea_base.TOTAL_PRESUPUESTO_AUDITADO)  # no suma al total
    assert any(
        h["regla"] == "PENDIENTE" or "pendiente" in h["descripcion"].lower()
        for h in cuerpo["informe"]["hallazgos"]
    )


def test_aceptar_una_propuesta_es_reenviar_el_item_con_el_codigo_elegido(cliente, items_payload):
    items = [dict(i) for i in items_payload]
    pendiente = {
        "codigo_partida": "NO-EXISTE-99",
        "descripcion": "Excavación manual de zanja",
        "unidad": "m3",
        "cantidad": "2.5",
        "origen_id": "T-99",
        "origen_tipo": "manual",
        "dominio": "civil",
    }
    antes = cliente.post(RUTA, json=_cuerpo([*items, pendiente])).json()
    elegido = items[0]["codigo_partida"]

    despues = cliente.post(RUTA, json=_cuerpo([*items, {**pendiente, "codigo_partida": elegido}]))

    assert despues.status_code == 200
    assert despues.json()["pendientes"] == []
    assert float(despues.json()["total"]) > float(antes["total"])


def test_calcular_con_una_fecha_sin_lista_vigente_es_409_sin_propuesta_de_rendimientos(
    cliente, items_payload
):
    respuesta = cliente.post(RUTA, json=_cuerpo(items_payload, fecha="2026-01-01"))

    assert respuesta.status_code == 409
    assert "lista de precios" in respuesta.json()["detalle"]
    assert respuesta.json().get("rendimientos_por_declarar", []) == []


def test_sin_rendimiento_estimado_vigente_responde_409_con_la_propuesta(
    cliente, sesion, items_payload
):
    dejar_sin_estimado(sesion)
    sesion.commit()

    respuesta = cliente.post(RUTA, json=_cuerpo(items_payload, fecha=FECHA_PRESUPUESTO.isoformat()))

    assert respuesta.status_code == 409
    cuerpo = respuesta.json()
    assert "LB-02-TUB" in cuerpo["detalle"]
    (por_declarar,) = cuerpo["rendimientos_por_declarar"]
    assert por_declarar["codigo_partida"] == "LB-02-TUB"
    assert por_declarar["propuesta"]["rendimiento"]["valor"] == "100"
    assert por_declarar["propuesta"]["dispersion"]["media"] == "95"


def test_declarar_el_estimado_propuesto_desbloquea_el_calculo(cliente, sesion, items_payload):
    dejar_sin_estimado(sesion)
    sesion.commit()
    cuerpo = _cuerpo(items_payload, fecha=FECHA_PRESUPUESTO.isoformat())
    assert cliente.post(RUTA, json=cuerpo).status_code == 409

    registro = cliente.post(
        DECLARAR,
        json={
            "codigo_partida": "LB-02-TUB",
            "tipo": "estimado",
            "fecha": FECHA_PRESUPUESTO.isoformat(),
        },
    )

    assert registro.status_code == 200, registro.text
    assert registro.json()["valor"] == "100" and registro.json()["tipo"] == "estimado"
    assert "propuesto del historico al elaborar (UC-01 3b)" in registro.json()["condiciones"]
    final = cliente.post(RUTA, json=cuerpo)
    assert final.status_code == 200, final.text
    assert final.json()["total"] == str(linea_base.TOTAL_PRESUPUESTO_AUDITADO)


def test_un_rendimiento_declarado_medido_no_se_registra(cliente, sesion, items_payload):
    dejar_sin_estimado(sesion)
    sesion.commit()

    respuesta = cliente.post(
        DECLARAR,
        json={
            "codigo_partida": "LB-02-TUB",
            "tipo": "medido",
            "fecha": FECHA_PRESUPUESTO.isoformat(),
        },
    )

    assert respuesta.status_code == 422
    assert "declarado medido no se usa tal cual" in respuesta.json()["detalle"]


def test_declarar_una_partida_que_no_esta_por_declarar_es_422(cliente, items_payload):
    respuesta = cliente.post(
        DECLARAR,
        json={"codigo_partida": "LB-01-EXC", "tipo": "estimado", "fecha": "2026-04-28"},
    )

    assert respuesta.status_code == 422


def test_el_libro_de_excel_es_el_del_mismo_calculo(cliente, items_payload):
    respuesta = cliente.post(EXCEL, json=_cuerpo(items_payload))

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert 'filename="presupuesto_P-001.xlsx"' in respuesta.headers["content-disposition"]
    libro = openpyxl.load_workbook(io.BytesIO(respuesta.content))
    assert libro.sheetnames  # un libro de verdad, con su hoja de auditoría
    assert cliente.get("/presupuestos").json() == []


@pytest.mark.parametrize("ruta", [RUTA, EXCEL])
def test_un_cuerpo_sin_items_obligatorios_es_422(cliente, ruta):
    assert cliente.post(ruta, json={"codigo": "P-001"}).status_code == 422


def test_el_total_viaja_tambien_exacto_para_el_title_de_la_interfaz(cliente, items_payload):
    """VB-6: la interfaz lee el total en centésimas y muestra el exacto a un toque. Oráculo a mano
    con los P.U. exactos del motor (`PRECIO_UNITARIO_EXACTO`): 9,74 × 8,600418750 + 24 ×
    10,1933700 + 23,68 × 33,237875000 + 1,66 × 242,63965000 + 1,3 × 52,57656250 =
    83,768078625 + 244,64088 + 787,07288 + 402,781819 + 68,34953125 = 1 586,613188875."""
    cuerpo = cliente.post(RUTA, json=_cuerpo(items_payload)).json()

    assert cuerpo["total"] == "1586.61"
    assert Decimal(cuerpo["total_exacto"]) == Decimal("1586.613188875")
    assert "E" not in cuerpo["total_exacto"].upper()  # texto decimal, sin notación científica
