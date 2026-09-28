"""UC-01 6 y 3b por HTTP (fase C5, pista U: INV-087 e INV-088).

INV-087 (UC-01, paso 6): `POST /presupuestos` recibe el plan de trabajo del proyectista en `plan`
(periodos con la fraccion de cada partida, como texto decimal) y lo pasa a `elaborar`. Sin `plan`,
`plan_secuencial` sigue siendo el valor por defecto: la linea base no cambia.

Oraculo independiente: la aritmetica a mano de la fixture de la linea base (cantidad del computo
auditado por el precio unitario exacto del motor) y la curva persistida, leida de la base.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from core import models
from tests.fixtures import apu_linea_base as linea_base

PROYECTO = "Drenaje de la clínica"

#: El plan del proyectista: dos semanas, con la tuberia repartida mitad y mitad entre ellas.
PLAN_DOS_SEMANAS = [
    {"periodo": "Semana 1", "reparto": {"LB-01-EXC": "1", "LB-02-TUB": "0.5"}},
    {
        "periodo": "Semana 2",
        "reparto": {"LB-02-TUB": "0.5", "LB-03-ENC": "1", "LB-04-CON": "1", "LB-05-REL": "1"},
    },
]


def _cuerpo(codigo: str, items: list[dict], **extra) -> dict:
    return {
        "codigo": codigo,
        "fecha": "2026-04-28",
        "moneda": "USD",
        "proyecto": PROYECTO,
        "items": items,
        **extra,
    }


def _total_de(codigo: str) -> Decimal:
    """Aritmetica a mano de la fixture: cantidad auditada por el precio unitario exacto."""
    return sum(
        (
            linea.cantidad * linea_base.PRECIO_UNITARIO_EXACTO[linea.codigo_partida]
            for linea in linea_base.PRESUPUESTO_AUDITADO
            if linea.codigo_partida == codigo
        ),
        Decimal(0),
    )


def _curva_guardada(sesion, codigo: str) -> list[models.PuntoCurva]:
    presupuesto = sesion.scalars(
        select(models.Presupuesto).where(models.Presupuesto.codigo == codigo)
    ).one()
    return list(presupuesto.curva)


# --- INV-087: el plan del proyectista (UC-01, paso 6) -----------------------------------------


def test_sin_plan_la_curva_es_una_partida_por_dia(cliente, sesion, items_payload):
    r = cliente.post("/presupuestos", json=_cuerpo("API-SEC", items_payload))
    assert r.status_code == 201
    assert r.json()["total"] == str(linea_base.TOTAL_PRESUPUESTO_AUDITADO)
    assert [punto.periodo for punto in _curva_guardada(sesion, "API-SEC")] == [
        f"Dia {numero} [{codigo}]"
        for numero, codigo in enumerate(linea_base.CODIGOS_LINEA_BASE, start=1)
    ]


def test_el_plan_del_proyectista_reparte_los_periodos_por_http(cliente, sesion, items_payload):
    r = cliente.post(
        "/presupuestos", json=_cuerpo("API-PLAN", items_payload, plan=PLAN_DOS_SEMANAS)
    )
    assert r.status_code == 201, r.json()
    assert r.json()["total"] == str(linea_base.TOTAL_PRESUPUESTO_AUDITADO)

    curva = _curva_guardada(sesion, "API-PLAN")
    assert [punto.periodo for punto in curva] == [
        "Semana 1 [LB-01-EXC, LB-02-TUB]",
        "Semana 2 [LB-02-TUB, LB-03-ENC, LB-04-CON, LB-05-REL]",
    ]
    # Aritmetica a mano: la excavacion entera y media tuberia en la primera semana.
    assert curva[0].monto == _total_de("LB-01-EXC") + Decimal("0.5") * _total_de("LB-02-TUB")
    assert curva[-1].acumulado == linea_base.TOTAL_EXACTO_LINEA_BASE  # cierra en el total


def test_un_plan_que_no_reparte_toda_partida_responde_422_sin_guardar(
    cliente, sesion, items_payload
):
    incompleto = [PLAN_DOS_SEMANAS[0]]  # la segunda semana, con el resto, no se declara
    r = cliente.post("/presupuestos", json=_cuerpo("API-MAL", items_payload, plan=incompleto))
    assert r.status_code == 422
    assert "LB-05-REL" in r.json()["detalle"]
    assert (
        sesion.scalars(
            select(models.Presupuesto).where(models.Presupuesto.codigo == "API-MAL")
        ).one_or_none()
        is None
    )


def test_una_fraccion_que_no_es_decimal_responde_422(cliente, items_payload):
    plan = [{"periodo": "Semana 1", "reparto": {"LB-01-EXC": "1,5"}}]
    r = cliente.post("/presupuestos", json=_cuerpo("API-MAL", items_payload, plan=plan))
    assert r.status_code == 422
    assert "LB-01-EXC" in r.json()["detalle"]


# --- INV-088: sin rendimiento vigente, se propone el del historico (UC-01, flujo 3b) ------------


def test_sin_rendimiento_vigente_responde_409_con_la_propuesta_y_no_guarda(
    cliente, sesion, items_payload
):
    from tests.fixtures.sin_rendimiento_vigente import FECHA_PRESUPUESTO, dejar_sin_estimado

    dejar_sin_estimado(sesion)
    sesion.commit()
    cuerpo = _cuerpo("API-3B", items_payload, fecha=FECHA_PRESUPUESTO.isoformat())

    r = cliente.post("/presupuestos", json=cuerpo)

    assert r.status_code == 409
    respuesta = r.json()
    assert "LB-02-TUB" in respuesta["detalle"]
    (por_declarar,) = respuesta["rendimientos_por_declarar"]
    assert por_declarar["codigo_partida"] == "LB-02-TUB"
    propuesta = por_declarar["propuesta"]
    # El MEDIDO mas reciente del historico (100, no 90), con su tipo declarado.
    assert (propuesta["rendimiento"]["valor"], propuesta["rendimiento"]["tipo"]) == (
        "100",
        "medido",
    )
    # Dispersion a mano: dos medidos, 90 y 100 -> media 95, rango [90, 100].
    assert propuesta["dispersion"] == {
        "observaciones": 2,
        "media": "95",
        "minimo": "90",
        "maximo": "100",
        "medidos": 2,
        "estimados": 0,
    }
    assert (
        sesion.scalars(
            select(models.Presupuesto).where(models.Presupuesto.codigo == "API-3B")
        ).one_or_none()
        is None
    )


def test_declarado_el_estimado_propuesto_la_elaboracion_reproduce_la_linea_base(
    cliente, sesion, items_payload
):
    """El tipo se declara con la ruta de rendimientos que ya existe (RF-25), y se vuelve a
    enviar: con el 100 propuesto, el APU de la tuberia es el de la linea base."""
    from tests.fixtures.sin_rendimiento_vigente import FECHA_PRESUPUESTO, dejar_sin_estimado

    dejar_sin_estimado(sesion)
    sesion.commit()
    cuerpo = _cuerpo("API-3B", items_payload, fecha=FECHA_PRESUPUESTO.isoformat())
    propuesta = cliente.post("/presupuestos", json=cuerpo).json()["rendimientos_por_declarar"]

    registro = cliente.post(
        "/partidas/LB-02-TUB/rendimientos",
        json={
            "valor": propuesta[0]["propuesta"]["rendimiento"]["valor"],
            "tipo": "estimado",
            "fecha": FECHA_PRESUPUESTO.isoformat(),
            "condiciones": "propuesto del historico al elaborar (prueba de UC-01 3b)",
        },
    )
    assert registro.status_code == 201

    r = cliente.post("/presupuestos", json=cuerpo)
    assert r.status_code == 201, r.json()
    assert r.json()["total"] == str(linea_base.TOTAL_PRESUPUESTO_AUDITADO)


# --- U-1 y U-3 de la revision: sin lista vigente no es 3b ----------------------------------------


def test_sin_lista_vigente_el_409_no_propone_rendimientos_y_no_guarda(
    cliente, sesion, items_payload
):
    """Un `CatalogoIncompleto` real: el presupuesto se fecha antes de la lista (y de los estimados)
    de la linea base. Lo que falta es la lista: el 409 lo dice y no ofrece 3b."""
    from datetime import date

    anterior = date(2026, 1, 1)
    assert anterior < linea_base.FECHA_LINEA_BASE
    cuerpo = _cuerpo("API-SIN-LISTA", items_payload, fecha=anterior.isoformat())

    r = cliente.post("/presupuestos", json=cuerpo)

    assert r.status_code == 409
    respuesta = r.json()
    assert "lista de precios" in respuesta["detalle"]
    assert respuesta.get("rendimientos_por_declarar", []) == []
    assert (
        sesion.scalars(
            select(models.Presupuesto).where(models.Presupuesto.codigo == "API-SIN-LISTA")
        ).one_or_none()
        is None
    )


def test_un_insumo_sin_precio_responde_el_409_de_siempre(cliente, sesion, items_payload):
    """Otro `CatalogoIncompleto` real que no es de rendimiento: el cemento sin precio en la lista
    vigente. Todas las partidas tienen su estimado: 409 con solo el `detalle` del precio."""
    from tests.fixtures.sin_rendimiento_vigente import INSUMO_SIN_PRECIO, quitar_precio

    quitar_precio(sesion)
    sesion.commit()

    r = cliente.post("/presupuestos", json=_cuerpo("API-SIN-PRECIO", items_payload))

    assert r.status_code == 409
    assert INSUMO_SIN_PRECIO in r.json()["detalle"]
    assert r.json().get("rendimientos_por_declarar", []) == []
