"""Ola 2 de la migración: pruebas que cierran la revisión de `silice-rev-seguridad`.

Cada prueba apunta a un hallazgo (H1 a H6). Entradas hostiles construidas a mano; ningún dato real.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from scripts.seed import NOMBRE_PROYECTO

CABECERA = "tipo,insumo,unidad,precio\n"
MUESTRA = (
    Path(__file__).resolve().parents[2] / "data" / "samples" / "precios" / "lista_2026-06-01.csv"
)
DATOS = {
    "proyecto": NOMBRE_PROYECTO,
    "codigo": "API-001",
    "codigo_nuevo": "API-002",
    "nombre": "Lista de prueba",
    "moneda": "USD",
    "fecha_vigencia": "2026-06-01",
}


def _calculo(items, **extra):
    return {"codigo": "P-001", "fecha": "2026-04-28", "moneda": "USD", "items": items, **extra}


def _guardar(cliente, items, codigo="API-001"):
    respuesta = cliente.post(
        "/presupuestos",
        json={
            "codigo": codigo,
            "fecha": "2026-04-28",
            "moneda": "USD",
            "proyecto": NOMBRE_PROYECTO,
            "items": items,
        },
    )
    assert respuesta.status_code == 201, respuesta.text


def _revalorar(cliente, **cambios):
    archivo = {"archivo": ("lista.csv", MUESTRA.read_bytes(), "text/csv")}
    return cliente.post("/presupuestos/revalorar", files=archivo, data={**DATOS, **cambios})


# --- H1: el código del cuerpo no puede salir del directorio temporal -------------------------


@pytest.mark.parametrize("codigo", ["../x", "/tmp/x", "a/b", "a\\b", "x:y", "", " ", "x" * 65])
def test_un_codigo_con_ruta_o_invalido_es_422_en_calcular(cliente, items_payload, codigo):
    assert (
        cliente.post(
            "/presupuestos/calcular", json=_calculo(items_payload, codigo=codigo)
        ).status_code
        == 422
    )
    excel = cliente.post(
        "/presupuestos/calcular/excel", json=_calculo(items_payload, codigo=codigo)
    )
    assert excel.status_code == 422


@pytest.mark.parametrize("codigo", ["001", "P-001", "API-002", "v1.2_final", "Version 3"])
def test_los_codigos_normales_siguen_valiendo(cliente, items_payload, codigo):
    respuesta = cliente.post(
        "/presupuestos/calcular/excel", json=_calculo(items_payload, codigo=codigo)
    )

    assert respuesta.status_code == 200
    assert f'filename="presupuesto_{codigo}.xlsx"' in respuesta.headers["content-disposition"]


def test_el_libro_nunca_se_escribe_fuera_del_temporal_aunque_el_codigo_lleve_ruta(tmp_path):
    from aplicacion.elaboracion import elaborar_desde_catalogo, libro_excel
    from core.catalog import abrir_sesion, crear_esquema, crear_motor
    from scripts.seed import sembrar
    from tests.fixtures import apu_linea_base as linea_base
    from tests.fixtures.computo_auditado import items_auditados

    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            from core.catalog import Catalogo

            destino = tmp_path / "fuera"
            destino.mkdir()
            sin_unidad = destino.as_posix().split(":", 1)[-1].lstrip("/")
            codigo = "/" + "../" * 30 + sin_unidad + "/pwn"
            resultado = elaborar_desde_catalogo(
                Catalogo(sesion),
                list(items_auditados()),
                codigo,
                linea_base.FECHA_LINEA_BASE,
                linea_base.MONEDA,
            )

            contenido, nombre = libro_excel(resultado)
    finally:
        motor.dispose()

    assert contenido[:2] == b"PK"  # es un xlsx
    assert not list(destino.iterdir())  # nada se escribio fuera del temporal
    assert "/" not in nombre and "\\" not in nombre and ".." not in nombre


def test_un_codigo_nuevo_con_ruta_es_422_en_revalorar(cliente, items_payload):
    _guardar(cliente, items_payload)

    respuesta = _revalorar(cliente, codigo_nuevo="../x")

    assert respuesta.status_code == 422
    assert cliente.get("/presupuestos/..%2Fx").status_code == 404


# --- H2: el nombre de descarga no rompe la cabecera Content-Disposition ------------------------


def test_el_csv_de_un_codigo_con_comillas_no_inyecta_cabecera(cliente, items_payload):
    _guardar(cliente, items_payload, codigo="X\";filename*=UTF-8''evil.html")

    respuesta = cliente.post(
        "/presupuestos/X%22;filename*=UTF-8''evil.html/escenarios/csv",
        json={"escenarios": [{"nombre": "e"}]},
    )

    assert respuesta.status_code == 200, respuesta.text
    # Las comillas, el punto y coma, el asterisco y la comilla simple pasan a guion bajo: queda un
    # solo parametro `filename` y ninguna extension propia del atacante.
    assert (
        respuesta.headers["content-disposition"]
        == 'attachment; filename="escenarios_X__filename__UTF-8__evil.html.csv"'
    )


# --- H3: el CSV de escenarios no ejecuta fórmulas al abrirse en Excel --------------------------


@pytest.mark.parametrize(
    "nombre", ['=HYPERLINK("http://x","clic")', "+1+1", "-1+1", "@SUMA(1)", "\tx", "\rx"]
)
def test_el_csv_neutraliza_los_nombres_que_empiezan_como_formula(cliente, items_payload, nombre):
    _guardar(cliente, items_payload)

    respuesta = cliente.post(
        "/presupuestos/API-001/escenarios/csv", json={"escenarios": [{"nombre": nombre}]}
    )

    filas = list(csv.reader(io.StringIO(respuesta.text)))
    assert filas[2][0] == "'" + nombre
    assert filas[2][1]  # el total sigue siendo un número sin tocar
    assert not filas[2][1].startswith("'")


# --- H4: topes de tamaño ------------------------------------------------------------------------


def _item(i):
    return {
        "codigo_partida": f"X-{i}",
        "descripcion": "x",
        "unidad": "m3",
        "cantidad": "1",
        "origen_id": f"o{i}",
        "origen_tipo": "manual",
        "dominio": "civil",
    }


def test_calcular_rechaza_mas_de_2000_items(cliente):
    respuesta = cliente.post(
        "/presupuestos/calcular", json=_calculo([_item(i) for i in range(2001)])
    )

    assert respuesta.status_code == 422


def test_calcular_rechaza_un_plan_de_mas_de_5000_filas(cliente, items_payload):
    plan = [{"periodo": "S", "codigo_partida": "LB-01-EXC", "fraccion": "0"}] * 5001

    assert (
        cliente.post("/presupuestos/calcular", json=_calculo(items_payload, plan=plan)).status_code
        == 422
    )


def test_los_escenarios_estan_acotados_a_20_y_a_1000_precios(cliente, items_payload):
    _guardar(cliente, items_payload)

    demasiados = {"escenarios": [{"nombre": f"e{i}"} for i in range(21)]}
    muchos_precios = {
        "escenarios": [{"nombre": "p", "precios": {f"i{i}": "1" for i in range(1001)}}]
    }

    for ruta in ("escenarios", "escenarios/csv"):
        assert cliente.post(f"/presupuestos/API-001/{ruta}", json=demasiados).status_code == 422
        assert cliente.post(f"/presupuestos/API-001/{ruta}", json=muchos_precios).status_code == 422


def test_solo_los_primeros_50_pendientes_piden_propuestas(cliente, monkeypatch):
    pedidos = []

    class _Propuesta:
        similares: tuple = ()
        falla = None

    def _falso(partidas, pendientes):
        pedidos.append(len(pendientes))
        return [(item, _Propuesta()) for item in pendientes]

    monkeypatch.setattr("ml.normalization.propuestas_para", _falso)

    respuesta = cliente.post("/presupuestos/calcular", json=_calculo([_item(i) for i in range(60)]))

    assert respuesta.status_code == 200, respuesta.text
    assert pedidos == [50]
    assert len(respuesta.json()["pendientes"]) == 60  # los 10 restantes se declaran sin propuestas


# --- H5: un importe desmesurado es 422, no 500 --------------------------------------------------


def test_una_cantidad_desmesurada_es_422(cliente, items_payload):
    items = [dict(i) for i in items_payload]
    items[0]["cantidad"] = "1e999999"

    assert cliente.post("/presupuestos/calcular", json=_calculo(items)).status_code == 422


def test_un_precio_de_ensayo_desmesurado_es_422(cliente, items_payload):
    _guardar(cliente, items_payload)

    respuesta = cliente.post(
        "/presupuestos/API-001/escenarios",
        json={"escenarios": [{"nombre": "x", "precios": {"Cemento Portland": "1e999999"}}]},
    )

    assert respuesta.status_code == 422


# --- H6: los errores de base de datos no cuentan SQL ni nombres de tabla ------------------------


def test_la_vista_previa_no_filtra_el_sql_de_un_error_de_base(cliente, monkeypatch):
    def _falla(*args, **kwargs):
        raise OperationalError(
            "SELECT secreto FROM tabla_interna", {"p": 1}, Exception("no such table")
        )

    monkeypatch.setattr("api.rutas.listas.insumos_desconocidos", _falla)

    respuesta = cliente.post(
        "/listas-precios/vista-previa",
        files={"archivo": ("l.csv", (CABECERA + "material,A,m,1\n").encode(), "text/csv")},
    )

    assert respuesta.status_code == 200
    motivo = respuesta.json()["motivo"]
    assert motivo and "SELECT" not in motivo and "tabla_interna" not in motivo


def test_el_conflicto_de_revalorar_trae_un_mensaje_fijo(cliente, items_payload, monkeypatch):
    _guardar(cliente, items_payload)

    def _falla(*args, **kwargs):
        raise IntegrityError(
            "INSERT", {}, Exception("UNIQUE constraint failed: presupuesto.codigo")
        )

    monkeypatch.setattr("aplicacion.actualizacion.revalorar", _falla)

    respuesta = _revalorar(cliente)

    assert respuesta.status_code == 409
    detalle = respuesta.json()["detalle"]
    assert "UNIQUE" not in detalle and "presupuesto.codigo" not in detalle
    assert "ya existe" in detalle
