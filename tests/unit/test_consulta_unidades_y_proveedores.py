"""AC4: lo ya usado en la carpeta para guiar dos campos de texto (pedido de Eugenio, 2026-10-21).

- `GET /v1/consulta/unidades`: las unidades del catálogo (partidas e insumos), agrupadas con la
  única tabla de alias del sistema (`core.contracts.unidades.normalizar_unidad`): «m3», «m³» y
  «M3» son una sola unidad, `m3`, con sus grafías y cuántas veces aparece. Las más usadas primero;
  a igual uso, por orden alfabético.
- `GET /v1/consulta/proveedores`: los proveedores de las cotizaciones de la carpeta, sin repetir
  (sin distinguir mayúsculas ni acentos) y con la fecha de su último uso; el último usado primero.
  Se escribe como en su cotización más reciente.

Las dos solo leen: `LEER_PROYECTO` (arma y revisa; el administrador, 403), como `/{tabla}`, y
`Cache-Control: no-store`. El proveedor ya lo ve quien lee en la columna «Cotización» de los
precios de una versión (`GET /v1/hoja/precios`). Datos ficticios; oráculos escritos a mano.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from api import caso_web, dependencias
from api.main import manejar_http_exception
from api.proteccion import proteger
from api.rutas import consulta, sesion
from aplicacion.consulta import (
    ProveedorUsado,
    UnidadUsada,
    proveedores_usados,
    unidades_usadas,
)
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
)


def _partida(codigo: str, unidad: str) -> models.Partida:
    return models.Partida(
        codigo=codigo, descripcion=f"Partida {codigo} ficticia", unidad=unidad, dominio="civil"
    )


def _insumo(codigo: str, unidad: str | None, tipo: str = "material") -> models.Insumo:
    return models.Insumo(
        codigo=codigo, tipo=tipo, descripcion=f"Insumo {codigo} ficticio", unidad=unidad
    )


def _sembrar(s: Session) -> None:
    """Unidades: m3 ×3 (tres grafías), saco ×2, kg ×1, h ×1 (de «hora»), glb ×1 (desconocida, sin
    traducir); un insumo sin unidad y otro con la unidad en blanco no cuentan.

    Proveedores (diseño §13: solo las cotizaciones **activas**, las de la lista de la versión
    vigente de cada obra, la de mayor id no descartada, como `core.budget.version_vigente`):

    - Obra A: la 001 con la lista de julio (la ferretería y la cantera) y la 002 con la de agosto
      (la ferretería dos veces, con y sin acentos). La 002 retiró la cantera: no se ofrece.
    - Obra B: la 001 con la lista de setiembre (la bloquera) y la 002, descartada, con la de una
      «Distribuidora Descartada»: no se ofrece.
    - Una lista sin ninguna versión, con un «Proveedor Suelto»: no se ofrece."""
    s.add_all(
        [
            _partida("P-1", "m3"),
            _partida("P-2", "m³"),
            _partida("P-3", "Glb"),
            _insumo("MAT-1", "M3"),
            _insumo("MAT-2", "saco"),
            _insumo("MAT-3", "Saco"),
            _insumo("MAT-4", "kg"),
            _insumo("MAT-5", None),
            _insumo("MAT-6", "  "),
            _insumo("EQ-1", "hora", tipo="equipo"),
        ]
    )
    s.flush()

    def lista(nombre: str, vigencia: date) -> models.ListaPrecios:
        return models.ListaPrecios(nombre=nombre, moneda="Bs", fecha_vigencia=vigencia)

    julio = lista("Lista ficticia de julio", date(2026, 7, 1))
    agosto = lista("Lista ficticia de agosto", date(2026, 8, 1))
    setiembre = lista("Lista ficticia de setiembre", date(2026, 9, 1))
    descartada = lista("Lista ficticia descartada", date(2026, 9, 15))
    suelta = lista("Lista ficticia sin versión", date(2026, 9, 20))
    obra_a = models.Proyecto(nombre="Obra ficticia A")
    obra_b = models.Proyecto(nombre="Obra ficticia B")
    s.add_all([julio, agosto, setiembre, descartada, suelta, obra_a, obra_b])
    s.flush()
    insumos = {i.codigo: i.id for i in s.query(models.Insumo)}

    def version(obra: models.Proyecto, codigo: str, de: models.ListaPrecios) -> models.Presupuesto:
        return models.Presupuesto(
            codigo=codigo,
            proyecto_id=obra.id,
            fecha=de.fecha_vigencia,
            moneda="Bs",
            lista_precios_id=de.id,
            fcas=Decimal("6"),
            bono_alimentacion=Decimal("1"),
            administracion=Decimal("0.15"),
            utilidad=Decimal("0.10"),
        )

    descartada_b = version(obra_b, "002", descartada)
    s.add_all(
        [
            version(obra_a, "001", julio),
            version(obra_a, "002", agosto),
            version(obra_b, "001", setiembre),
            descartada_b,
        ]
    )
    s.flush()
    s.add(models.DescarteVersion(presupuesto_id=descartada_b.id, fecha=date(2026, 9, 16)))

    def cotizacion(
        lista: models.ListaPrecios, insumo: str, proveedor: str, fecha: date
    ) -> models.Cotizacion:
        return models.Cotizacion(
            lista_id=lista.id,
            insumo_id=insumos[insumo],
            precio=Decimal("10"),
            proveedor=proveedor,
            numero="C-1",
            fecha=fecha,
        )

    s.add_all(
        [
            cotizacion(julio, "MAT-1", "Ferretería Demo, C.A.", date(2026, 7, 10)),
            cotizacion(julio, "MAT-2", "Cantera Retirada", date(2026, 9, 25)),
            cotizacion(agosto, "MAT-2", "Ferretería Demo, C.A.", date(2026, 7, 10)),
            cotizacion(agosto, "MAT-1", "  ferreteria demo, c.a. ", date(2026, 9, 5)),
            cotizacion(setiembre, "MAT-1", "Bloquera Ficticia", date(2026, 8, 20)),
            cotizacion(descartada, "MAT-1", "Distribuidora Descartada", date(2026, 9, 30)),
            cotizacion(suelta, "MAT-1", "Proveedor Suelto", date(2026, 10, 1)),
        ]
    )
    s.commit()


UNIDADES = [
    UnidadUsada("m3", 3, ("M3", "m3", "m³")),
    UnidadUsada("saco", 2, ("Saco", "saco")),
    UnidadUsada("glb", 1, ("Glb",)),
    UnidadUsada("h", 1, ("hora",)),
    UnidadUsada("kg", 1, ("kg",)),
]
PROVEEDORES = [
    ProveedorUsado("ferreteria demo, c.a.", date(2026, 9, 5)),
    ProveedorUsado("Bloquera Ficticia", date(2026, 8, 20)),
]


# --- aplicacion.consulta ------------------------------------------------------------------------


@pytest.fixture
def base(tmp_path: Path) -> Iterator[Session]:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            yield s
    finally:
        motor.dispose()


def test_carpeta_vacia_no_ofrece_nada(base: Session) -> None:
    assert unidades_usadas(base) == []
    assert proveedores_usados(base) == []


def test_unidades_agrupadas_con_la_tabla_de_alias_y_contadas(base: Session) -> None:
    _sembrar(base)
    assert unidades_usadas(base) == UNIDADES


def test_proveedores_sin_repetir_con_su_ultimo_uso(base: Session) -> None:
    _sembrar(base)
    assert proveedores_usados(base) == PROVEEDORES


def test_solo_se_ofrecen_los_proveedores_de_cotizaciones_activas(base: Session) -> None:
    """Diseño §13: una cotización retirada (su obra ya va por otra versión sin ella), la de una
    versión descartada o la de una lista que ninguna versión usa no sugieren su proveedor, aunque
    sean más recientes que las activas."""
    _sembrar(base)
    nombres = {p.proveedor for p in proveedores_usados(base)}
    assert nombres == {"ferreteria demo, c.a.", "Bloquera Ficticia"}
    assert not {"Cantera Retirada", "Distribuidora Descartada", "Proveedor Suelto"} & nombres


# --- API ----------------------------------------------------------------------------------------


def _aplicacion() -> FastAPI:
    aplicacion = FastAPI()
    aplicacion.add_exception_handler(HTTPException, manejar_http_exception)
    aplicacion.include_router(sesion.router)
    aplicacion.include_router(consulta.router)
    proteger(aplicacion)
    return aplicacion


APLICACION = _aplicacion()


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("api_consulta_usados"))


@pytest.fixture
def ana(_plantilla: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    copiar_instalacion(_plantilla)
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            _sembrar(s)
    finally:
        motor.dispose()
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta.as_posix()}")
    yield con_cuenta(APLICACION, "ana")[0]
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def test_api_unidades(ana: TestClient) -> None:
    r = ana.get("/v1/consulta/unidades")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-store"
    assert r.json() == {
        "unidades": [
            {"unidad": "m3", "usos": 3, "grafias": ["M3", "m3", "m³"]},
            {"unidad": "saco", "usos": 2, "grafias": ["Saco", "saco"]},
            {"unidad": "glb", "usos": 1, "grafias": ["Glb"]},
            {"unidad": "h", "usos": 1, "grafias": ["hora"]},
            {"unidad": "kg", "usos": 1, "grafias": ["kg"]},
        ]
    }


def test_api_proveedores(ana: TestClient) -> None:
    r = ana.get("/v1/consulta/proveedores")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-store"
    assert r.json() == {
        "proveedores": [
            {"proveedor": "ferreteria demo, c.a.", "ultimo_uso": "2026-09-05"},
            {"proveedor": "Bloquera Ficticia", "ultimo_uso": "2026-08-20"},
        ]
    }


def test_una_tabla_desconocida_sigue_siendo_404(ana: TestClient) -> None:
    assert ana.get("/v1/consulta/monedas", params={"q": "bs"}).status_code == 404


@pytest.mark.parametrize("ruta", ["/v1/consulta/unidades", "/v1/consulta/proveedores"])
def test_el_administrador_recibe_403_y_sin_sesion_401(ana: TestClient, ruta: str) -> None:
    admin = con_cuenta(APLICACION, "admin")[0]
    r = admin.get(ruta)
    assert r.status_code == 403 and MENSAJE_PERMISO in r.text
    assert r.headers.get("cache-control") == "no-store"
    assert cliente(APLICACION).get(ruta).status_code == 401


@pytest.mark.parametrize(
    ("ruta", "funcion"),
    [
        ("/v1/consulta/unidades", "unidades_usadas"),
        ("/v1/consulta/proveedores", "proveedores_usados"),
    ],
)
def test_un_fallo_de_la_base_es_503_sin_sql(
    ana: TestClient, monkeypatch: pytest.MonkeyPatch, ruta: str, funcion: str
) -> None:
    def falla(_sesion: Session) -> list:
        raise OperationalError("SELECT secreto FROM cotizacion", {}, Exception("disco"))

    monkeypatch.setattr(consulta, funcion, falla)
    r = ana.get(ruta)
    assert r.status_code == 503
    assert r.headers.get("cache-control") == "no-store"
    assert "SELECT" not in r.text and "secreto" not in r.text
