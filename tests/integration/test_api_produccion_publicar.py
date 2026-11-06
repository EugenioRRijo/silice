"""`/v1/produccion/calculos/{id}/publicar`: el costo propio al catalogo por la API (Tarea 5 del plan
vial). Datos FICTICIOS: la planta de noviembre de 2026 de `tests/fixtures/costo_propio.py`, sembrada
en la instalacion con los servicios, y una lista en USD en la carpeta del caso.

Oraculos a mano: el calculo da `AGR-12` 5, `AGR-34` 5 y `MZ-1` 50,70; lo publicado es el valor
exacto (decimales como texto) con la fuente «Producción, período 2026-11, cálculo n.º <id>». Solo el
administrador publica: arma (`ana`) y revisa (`rita`) reciben 403 y no se escribe nada.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from api import dependencias
from core import models
from operacion.base_datos import preparar_base
from operacion.config import ruta_caso_por_defecto, ruta_instalacion
from operacion.instalacion import sesion_de_instalacion
from seguridad import cuentas, empresas
from tests.fixtures import costo_propio as cp
from tests.fixtures.hoja_versiones_api import base
from tests.fixtures.produccion_api import Web, cliente_con_clave
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

CALCULOS = "/v1/produccion/calculos"
HORA_DEL_SERVIDOR = datetime(2026, 12, 1, 7, 30, 0)
EMPRESA = ("Constructora Ejemplo, C.A.", "J-00000000-0")
SIN_EMPRESA = "Configure la empresa en la Cuenta («Empresa y tema») antes de publicar."


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("plantilla_produccion"))


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path):
    copiar_instalacion(_instalacion_migrada)
    yield
    cuentas.FRENO.reiniciar()
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


@pytest.fixture
def http() -> TestClient:
    return cliente_con_clave()


def _noviembre(con_empresa: bool = True) -> None:
    """La planta y los costos en la instalacion (y la empresa configurada en Administracion); la
    lista en USD en la carpeta del caso."""
    with sesion_de_instalacion() as ins:
        cp.planta(ins)
        cp.costos_usd(ins)
        ins.commit()
        if con_empresa:
            empresas.guardar_empresa_propia(ins, *EMPRESA, "Ciudad ficticia", "admin", cp.AHORA)
    ruta = ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(ruta)
    with base(ruta) as caso:
        cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
        caso.commit()


def _calcular(http) -> int:
    r = http.post(CALCULOS, json={"periodo": "2026-11", "moneda": "USD"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _listas_de_empresa() -> list[tuple[int, str, str]]:
    with base(ruta_caso_por_defecto()) as caso:
        filas = caso.execute(
            select(models.ListaPrecios.id, models.ListaPrecios.origen, models.ListaPrecios.moneda)
            .join(models.ListaEmpresa, models.ListaEmpresa.lista_id == models.ListaPrecios.id)
            .order_by(models.ListaPrecios.id)
        )
        return [tuple(f) for f in filas]


def _precios(lista_id: int) -> dict[str, tuple[Decimal, str]]:
    with base(ruta_caso_por_defecto()) as caso:
        filas = caso.execute(
            select(models.Insumo.codigo, models.PrecioInsumo.precio, models.PrecioOrigen.fuente)
            .join(models.PrecioInsumo, models.PrecioInsumo.insumo_id == models.Insumo.id)
            .join(models.PrecioOrigen, models.PrecioOrigen.precio_id == models.PrecioInsumo.id)
            .where(models.PrecioInsumo.lista_id == lista_id)
        )
        return {codigo: (precio, fuente) for codigo, precio, fuente in filas}


def _insumos_propios() -> int:
    with base(ruta_caso_por_defecto()) as caso:
        return caso.scalar(
            select(func.count()).select_from(models.Insumo).where(models.Insumo.codigo.like("%P-%"))
        )


def test_el_administrador_publica_el_calculo(http) -> None:
    _noviembre()
    calculo = _calcular(http)
    admin = Web("admin")
    r = admin.post(f"{CALCULOS}/{calculo}/publicar", json={})
    assert r.status_code == 201, r.text
    lista_id = r.json()["id"]
    assert [fila[0] for fila in _listas_de_empresa()] == [lista_id]
    fuente = f"Producción, período 2026-11, cálculo n.º {calculo}"
    assert _precios(lista_id)["AGP-AGR-12"] == (Decimal("5"), fuente)
    assert _precios(lista_id)["MZP-MZ-1"] == (Decimal("50.70"), fuente)


def test_la_hora_y_el_usuario_son_los_del_servidor(http, monkeypatch) -> None:
    monkeypatch.setattr("api.rutas.produccion._ahora", lambda: HORA_DEL_SERVIDOR)
    _noviembre()
    calculo = _calcular(http)
    cuerpo = {"ahora": "2020-01-01T00:00:00", "usuario": "otro"}
    r = Web("admin").post(f"{CALCULOS}/{calculo}/publicar", json=cuerpo)
    assert r.status_code == 201, r.text
    (_, origen, _) = _listas_de_empresa()[0]
    assert "publicado por Admin de Prueba <admin> el 01/12/2026 07:30" in origen
    assert "2020" not in origen and "otro" not in origen


def test_publicar_dos_calculos_son_dos_listas_y_un_solo_insumo(http) -> None:
    """Tarea 4b (P22): cada calculo se publica una vez (el 409 esta en `..._calculos_4b`)."""
    _noviembre()
    admin = Web("admin")
    primera = admin.post(f"{CALCULOS}/{_calcular(http)}/publicar", json={}).json()["id"]
    segunda = admin.post(f"{CALCULOS}/{_calcular(http)}/publicar", json={}).json()["id"]
    assert primera != segunda
    assert len(_listas_de_empresa()) == 2
    assert _insumos_propios() == 3  # AGP-AGR-12, AGP-AGR-34 y MZP-MZ-1


@pytest.mark.parametrize("quien", ["ana", "rita"], ids=["arma", "revisa"])
def test_arma_y_revisa_reciben_403_al_publicar(http, quien: str) -> None:
    _noviembre()
    calculo = _calcular(http)
    r = Web(quien).post(f"{CALCULOS}/{calculo}/publicar", json={})
    assert r.status_code == 403, r.text
    assert r.json()["detalle"] == "Su cuenta no tiene permiso para esta acción."
    assert _listas_de_empresa() == [] and _insumos_propios() == 0


def test_un_calculo_alterado_no_se_publica(http) -> None:
    _noviembre()
    calculo = _calcular(http)
    with closing(sqlite3.connect(ruta_instalacion())) as bd:
        bd.execute("UPDATE prod_calculo SET moneda = 'Bs' WHERE id = ?", (calculo,))
        bd.commit()
    r = Web("admin").post(f"{CALCULOS}/{calculo}/publicar", json={})
    assert r.status_code == 422, r.text
    assert "fue alterado" in r.json()["detalle"]
    assert _listas_de_empresa() == [] and _insumos_propios() == 0


def test_un_calculo_inexistente_es_404(http) -> None:
    _noviembre()
    r = Web("admin").post(f"{CALCULOS}/99/publicar", json={})
    assert r.status_code == 404, r.text
    assert "detalle" in r.json()
    assert _listas_de_empresa() == []


def test_sin_empresa_configurada_es_422_y_no_escribe(http) -> None:
    _noviembre(con_empresa=False)
    calculo = _calcular(http)
    r = Web("admin").post(f"{CALCULOS}/{calculo}/publicar", json={})
    assert r.status_code == 422, r.text
    assert r.json()["detalle"] == SIN_EMPRESA
    assert _listas_de_empresa() == [] and _insumos_propios() == 0


def test_la_lista_lleva_la_empresa_de_administracion(http) -> None:
    _noviembre()
    calculo = _calcular(http)
    cuerpo = {"empresa_nombre": "Otra, C.A.", "empresa_rif": "J-99999999-9"}  # se ignora
    r = Web("admin").post(f"{CALCULOS}/{calculo}/publicar", json=cuerpo)
    assert r.status_code == 201, r.text
    with base(ruta_caso_por_defecto()) as caso:
        fila = caso.scalar(select(models.ListaEmpresa))
        assert (fila.empresa_nombre, fila.empresa_rif) == EMPRESA


def test_la_clave_de_api_recibe_403_al_publicar(http) -> None:
    _noviembre()
    calculo = _calcular(http)
    r = http.post(f"{CALCULOS}/{calculo}/publicar", json={})
    assert r.status_code == 403, r.text
    assert _listas_de_empresa() == [] and _insumos_propios() == 0


def test_sin_lista_vigente_en_la_carpeta_es_422_y_no_escribe(http) -> None:
    """Publicar parte de la lista vigente al cierre del periodo; sin ella, 422 claro."""
    _noviembre()
    calculo = _calcular(http)
    with base(ruta_caso_por_defecto()) as caso:
        caso.execute(delete(models.PrecioInsumo))
        caso.execute(delete(models.ListaPrecios))
        caso.commit()
    r = Web("admin").post(f"{CALCULOS}/{calculo}/publicar", json={})
    assert r.status_code == 422, r.text
    assert "lista de precios vigente" in r.json()["detalle"]
    assert _listas_de_empresa() == []
