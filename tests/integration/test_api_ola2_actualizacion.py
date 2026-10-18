"""Ola 2 de la migración, Actualizar precios (UC-02) por HTTP: vista previa, revalorar y descartar.

Oráculos sin circularidad: el total nuevo es el de la línea base más el incremento de la muestra de
precios calculado a mano en `tests/fixtures/actualizacion_uc02.py` (30,17025 × 1,66 m3 = 50,082615).
Los textos de los avisos son los de la página de Streamlit (paridad), escritos a mano aquí.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from scripts.seed import NOMBRE_PROYECTO
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import INCREMENTO_TOTAL

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv"
CABECERA = "tipo,insumo,unidad,precio\n"
#: Un precio que cambia, un desconocido (2a) y un rechazado por unidad (2b).
LISTA_MIXTA = (
    CABECERA
    + "material,Cemento Portland,saco,18\n"
    + "material,Cemento blanco,saco,20\n"
    + "material,Arena lavada,kg,1\n"
)
#: Ningún precio cambia (la piedra sigue a 35) y trae un desconocido para el alta.
LISTA_SIN_CAMBIOS = (
    CABECERA + "material,Piedra picada,m3,35\n" + "material,Cemento blanco,saco,20\n"
)
DATOS = {
    "proyecto": NOMBRE_PROYECTO,
    "codigo": "API-001",
    "codigo_nuevo": "API-002",
    "nombre": "Lista de prueba",
    "moneda": "USD",
    "fecha_vigencia": "2026-06-01",
}


def _csv(texto: str, nombre: str = "lista.csv"):
    return {"archivo": (nombre, texto.encode("utf-8"), "text/csv")}


@pytest.fixture
def base(cliente, items_payload):
    """El presupuesto API-001 guardado por la API sobre la línea base."""
    respuesta = cliente.post(
        "/presupuestos",
        json={
            "codigo": "API-001",
            "fecha": "2026-04-28",
            "moneda": "USD",
            "proyecto": NOMBRE_PROYECTO,
            "items": items_payload,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _revalorar(cliente, texto: str = None, dar_de_alta=(), **cambios):
    contenido = MUESTRA.read_text(encoding="utf-8") if texto is None else texto
    datos = {**DATOS, **cambios}
    if dar_de_alta:
        datos["dar_de_alta"] = list(dar_de_alta)
    return cliente.post("/presupuestos/revalorar", files=_csv(contenido), data=datos)


# ---------------------------------------------------------------------------------------------
# GET /presupuestos trae el proyecto
# ---------------------------------------------------------------------------------------------


def test_el_listado_de_presupuestos_trae_el_proyecto(cliente, base):
    respuesta = cliente.get("/presupuestos")

    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"codigo": "API-001", "total": base["total"], "proyecto": NOMBRE_PROYECTO}
    ]


# ---------------------------------------------------------------------------------------------
# Vista previa de los insumos desconocidos (UC-02, 2a): no escribe
# ---------------------------------------------------------------------------------------------


def test_la_vista_previa_ofrece_el_desconocido_y_no_escribe(cliente, base):
    listas = cliente.get("/listas-precios").json()
    insumos = cliente.get("/insumos").json()

    respuesta = cliente.post("/listas-precios/vista-previa", files=_csv(LISTA_MIXTA))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "desconocidos": [
            {
                "descripcion": "Cemento blanco",
                "tipo": "material",
                "unidad": "saco",
                "precio": "20",
                "etiqueta": "Cemento blanco (material, saco)",
            }
        ],
        "motivo": None,
    }
    assert cliente.get("/listas-precios").json() == listas  # ninguna lista nueva
    assert cliente.get("/insumos").json() == insumos  # ninguna alta


def test_la_vista_previa_de_la_muestra_no_ofrece_nada(cliente, base):
    respuesta = cliente.post("/listas-precios/vista-previa", files=_csv(MUESTRA.read_text("utf-8")))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"desconocidos": [], "motivo": None}


def test_un_archivo_mal_formado_no_ofrece_nada_y_trae_su_motivo(cliente, base):
    respuesta = cliente.post(
        "/listas-precios/vista-previa", files=_csv("esto,no,es,una,lista\n1,2,3,4,5\n")
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["desconocidos"] == []
    assert cuerpo["motivo"]  # el mismo fallo sale con su mensaje al revalorar


# ---------------------------------------------------------------------------------------------
# Revalorar (UC-02)
# ---------------------------------------------------------------------------------------------


def test_revalorar_guarda_la_version_y_devuelve_el_comparativo_y_el_informe(cliente, base):
    respuesta = _revalorar(cliente)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    total_anterior = linea_base.TOTAL_EXACTO_LINEA_BASE.quantize(Decimal("0.01"), ROUND_HALF_UP)
    total_nuevo = (linea_base.TOTAL_EXACTO_LINEA_BASE + INCREMENTO_TOTAL).quantize(
        Decimal("0.01"), ROUND_HALF_UP
    )
    assert cuerpo["total_anterior"] == str(total_anterior)
    assert cuerpo["total_nuevo"] == str(total_nuevo)
    assert cuerpo["variacion"] == str(INCREMENTO_TOTAL.quantize(Decimal("0.01"), ROUND_HALF_UP))
    assert cuerpo["resumen"].startswith(f"{total_anterior} -> {total_nuevo} USD  (")
    assert cuerpo["resumen"].endswith(" %)")
    assert cuerpo["version_guardada"] == "API-002"
    assert cuerpo["avisos"] == []
    assert cuerpo["insumos_afectados"] == 2
    assert sum(1 for f in cuerpo["filas"] if f["variacion_pct"] not in ("0", "0.00")) == 1
    assert cuerpo["informe"]["codigo_presupuesto"] == "API-002"
    assert cuerpo["informe"]["veredicto"] in ("CUMPLE", "NO CUMPLE")
    assert cuerpo["dados_de_alta"] == cuerpo["ignorados"] == cuerpo["rechazados"] == []
    # La versión quedó guardada: su libro se baja por la ruta de siempre.
    assert cliente.get("/presupuestos/API-002/excel").status_code == 200


def test_revalorar_sin_cambios_de_precio_no_guarda_ni_da_de_alta(cliente, base):
    listas = cliente.get("/listas-precios").json()

    respuesta = _revalorar(cliente, LISTA_SIN_CAMBIOS, dar_de_alta=["Cemento blanco"])

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["version_guardada"] is None
    assert cuerpo["dados_de_alta"] == []
    assert len(cuerpo["avisos"]) == 1
    assert cuerpo["avisos"][0]["nivel"] == "advertencia"
    assert re.fullmatch(
        r"Ningun precio cambio: no se guardo una version nueva \(UC-02, flujo 3a\)\. "
        r"Los insumos elegidos para el alta tampoco se guardaron: Cemento blanco \([^)]+\)\.",
        cuerpo["avisos"][0]["texto"],
    )
    assert cliente.get("/presupuestos/API-002").status_code == 404
    assert cliente.get("/listas-precios").json() == listas
    assert "Cemento blanco" not in {i["descripcion"] for i in cliente.get("/insumos").json()}


def test_revalorar_da_de_alta_lo_elegido_y_separa_ignorados_y_rechazados(cliente, base):
    respuesta = _revalorar(cliente, LISTA_MIXTA, dar_de_alta=["Cemento blanco"])

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert len(cuerpo["dados_de_alta"]) == 1
    assert cuerpo["dados_de_alta"][0].startswith("Cemento blanco (")
    assert cuerpo["ignorados"] == []
    assert cuerpo["rechazados"] == ["Arena lavada (material, kg)"]
    assert "Cemento blanco" in {i["descripcion"] for i in cliente.get("/insumos").json()}


def test_revalorar_ignora_el_desconocido_no_elegido(cliente, base):
    respuesta = _revalorar(cliente, LISTA_MIXTA)

    cuerpo = respuesta.json()
    assert cuerpo["dados_de_alta"] == []
    assert cuerpo["ignorados"] == ["Cemento blanco (material, saco)"]


def test_revalorar_un_alta_que_no_es_desconocida_es_422_y_no_escribe(cliente, base):
    respuesta = _revalorar(cliente, LISTA_MIXTA, dar_de_alta=["Cemento Portland"])

    assert respuesta.status_code == 422
    assert cliente.get("/presupuestos/API-002").status_code == 404


def test_revalorar_un_presupuesto_inexistente_es_404(cliente, base):
    respuesta = _revalorar(cliente, codigo="NO-EXISTE")

    assert respuesta.status_code == 404


def test_revalorar_dos_veces_con_el_mismo_codigo_nuevo_es_409_con_motivo(cliente, base):
    assert _revalorar(cliente).status_code == 200

    segunda = _revalorar(cliente, nombre="Otra lista")

    assert segunda.status_code == 409
    assert segunda.json()["detalle"]


# ---------------------------------------------------------------------------------------------
# Descartar (UC-02, 7a)
# ---------------------------------------------------------------------------------------------


def test_descartar_marca_la_version_y_no_se_puede_dos_veces(cliente, base):
    assert _revalorar(cliente).status_code == 200

    primera = cliente.post("/presupuestos/API-002/descartar", params={"proyecto": NOMBRE_PROYECTO})

    assert primera.status_code == 200, primera.text
    assert primera.json()["codigo"] == "API-002" and primera.json()["descartada"] is True
    segunda = cliente.post("/presupuestos/API-002/descartar", params={"proyecto": NOMBRE_PROYECTO})
    assert segunda.status_code == 422
    assert "ya esta descartada" in segunda.json()["detalle"]
    # Sigue guardada como documento (UC-02 7a).
    assert cliente.get("/presupuestos/API-002").status_code == 200


def test_descartar_solo_la_ultima_version_revalorada(cliente, base):
    assert _revalorar(cliente).status_code == 200

    respuesta = cliente.post(
        "/presupuestos/API-001/descartar", params={"proyecto": NOMBRE_PROYECTO}
    )

    assert respuesta.status_code == 422
