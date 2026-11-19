"""DS-52: ninguna ruta escribe un `Decimal` con notación científica.

`str(Decimal("1E+3"))` es «1E+3» y `str(Decimal("0.0000001"))` es «1E-7»: la pantalla no lo puede
leer ni editar. Estos campos son exactos para la máquina (precios, rendimientos, cantidades,
parámetros): viajan tal cual, sin redondear, en notación fija (`api.presentacion.exacto`). Cada caso
es construido: se sustituye lo que la ruta consulta por un valor que hoy sale en notación
científica y se mira el texto de la respuesta.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from api.esquemas_ola2 import DeclararRendimientoPeticion
from api.rutas import (
    catalogo,
    fcas,
    listas,
    obras,
    precios_empresa,
    presupuestos_ayudas,
    presupuestos_calculo,
    presupuestos_escenarios,
    rendimientos,
)
from aplicacion.mesa import Cifra
from core.catalog import DispersionRendimiento, PrecioLeido
from core.contracts.apu import Rendimiento, TipoRendimiento
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.models import TipoInsumo

MIL = Decimal("1E+3")  # str: «1E+3»
DIEZ_MILLONESIMA = Decimal("0.0000001")  # str: «1E-7»


def test_los_valores_de_la_prueba_salen_hoy_en_notacion_cientifica() -> None:
    assert (str(MIL), str(DIEZ_MILLONESIMA)) == ("1E+3", "1E-7")


def _leido(precio: Decimal) -> PrecioLeido:
    return PrecioLeido(
        tipo=TipoInsumo.MATERIAL, descripcion="Cemento de prueba", unidad="saco", precio=precio
    )


def test_vista_previa_de_lista_escribe_el_precio_en_notacion_fija(monkeypatch) -> None:
    monkeypatch.setattr(listas, "guardar_subida", lambda directorio, archivo: Path("x.csv"))
    monkeypatch.setattr(listas, "comprobar_libro_legible", lambda ruta: None)
    monkeypatch.setattr(
        listas, "insumos_desconocidos", lambda sesion, ruta: [_leido(DIEZ_MILLONESIMA)]
    )
    respuesta = listas.vista_previa_de_lista(None, None)
    assert [d.precio for d in respuesta.desconocidos] == ["0.0000001"]


def test_cambios_de_precio_en_notacion_fija(monkeypatch) -> None:
    cambio = SimpleNamespace(
        insumo=SimpleNamespace(descripcion="Cemento de prueba"),
        precio_anterior=MIL,
        precio_nuevo=DIEZ_MILLONESIMA,
        variacion=Decimal("-0.9999999999"),
        fecha=date(2026, 11, 19),
    )
    monkeypatch.setattr(listas, "cambios_precio", lambda sesion, **filtros: [cambio])
    (fila,) = listas.listar_cambios_precio(None)
    assert (fila.precio_anterior, fila.precio_nuevo, fila.variacion) == (
        "1000",
        "0.0000001",
        "-0.9999999999",
    )


def test_cambios_de_precio_variacion_minima_en_notacion_fija(monkeypatch) -> None:
    cambio = SimpleNamespace(
        insumo=SimpleNamespace(descripcion="Cemento de prueba"),
        precio_anterior=Decimal("10"),
        precio_nuevo=Decimal("10.000001"),
        variacion=DIEZ_MILLONESIMA,
        fecha=date(2026, 11, 19),
    )
    monkeypatch.setattr(listas, "cambios_precio", lambda sesion, **filtros: [cambio])
    (fila,) = listas.listar_cambios_precio(None)
    assert fila.variacion == "0.0000001"


def test_insumos_del_catalogo_con_su_precio_en_notacion_fija(monkeypatch) -> None:
    class CatalogoDePrueba:
        def __init__(self, sesion) -> None:
            del sesion

        def lista_vigente(self):
            return SimpleNamespace(precios=[SimpleNamespace(insumo_id=1, precio=MIL)])

        def insumos(self):
            return [
                SimpleNamespace(
                    id=1,
                    codigo="I-1",
                    descripcion="Cemento de prueba",
                    tipo=TipoInsumo.MATERIAL,
                    unidad="saco",
                )
            ]

    monkeypatch.setattr(catalogo, "Catalogo", CatalogoDePrueba)
    (insumo,) = catalogo.listar_insumos(None)
    assert insumo.precio_vigente == "1000"


def test_resumen_de_la_mesa_con_cifras_y_tasa_en_notacion_fija(monkeypatch) -> None:
    cifra = Cifra(
        clave="valor_ganado",
        titulo="Valor ganado",
        actual=MIL,
        meta=DIEZ_MILLONESIMA,
        delta=Decimal("1E+2"),
        delta_pct=None,
        sentido="neutro",
        detalle=None,
    )
    conversion = SimpleNamespace(
        obra="Obra de prueba",
        moneda="USD",
        tasa=MIL,
        fecha=date(2026, 11, 19),
        fecha_tasa=date(2026, 11, 18),
    )
    cifras = SimpleNamespace(
        valor_ganado=cifra, avance=None, conversiones=[conversion], fuera_de_suma=[]
    )
    monkeypatch.setattr(obras, "Catalogo", lambda sesion: None)
    monkeypatch.setattr(obras, "obras_de_la_mesa", lambda sesion, cat, hoy: [])
    monkeypatch.setattr(obras, "moneda_de_la_carpeta", lambda sesion, hoy: "Bs")
    monkeypatch.setattr(obras, "cifras_de_la_mesa", lambda o, m, tasa: cifras)
    monkeypatch.setattr(obras, "moneda_de_la_suma", lambda o, m: "Bs")
    respuesta = obras._resumen(None, date(2026, 11, 19))
    (de_la_mesa,) = respuesta.cifras
    assert (de_la_mesa.actual, de_la_mesa.meta, de_la_mesa.delta) == ("1000", "0.0000001", "100")
    assert [c.tasa for c in respuesta.conversiones] == ["1000"]


def test_revision_de_lista_de_empresa_escribe_el_precio_en_notacion_fija(monkeypatch) -> None:
    @contextmanager
    def subido(archivo):
        del archivo
        yield Path("x.csv")

    revision = SimpleNamespace(
        reconocidos=0,
        nuevos=[
            SimpleNamespace(
                tipo=TipoInsumo.MATERIAL, descripcion="Cemento de prueba", unidad="saco", precio=MIL
            )
        ],
        otra_unidad=[],
    )
    monkeypatch.setattr(precios_empresa, "_archivo_subido", subido)
    monkeypatch.setattr(precios_empresa.logica, "revisar_archivo", lambda sesion, ruta: revision)
    respuesta = precios_empresa.revisar_archivo(None, archivo=object())
    assert [n.precio for n in respuesta.nuevos] == ["1000"]


def test_rendimiento_y_su_dispersion_en_notacion_fija() -> None:
    rendimiento = Rendimiento(
        codigo_partida="P-1",
        valor=DIEZ_MILLONESIMA,
        tipo=TipoRendimiento.ESTIMADO,
        fecha=date(2026, 11, 19),
    )
    dispersion = DispersionRendimiento(
        observaciones=2,
        media=MIL,
        minimo=DIEZ_MILLONESIMA,
        maximo=Decimal("2E+3"),
        medidos=0,
        estimados=2,
    )
    assert rendimientos._a_rendimiento_respuesta(rendimiento).valor == "0.0000001"
    textos = rendimientos._a_dispersion_respuesta(dispersion)
    assert (textos.media, textos.minimo, textos.maximo) == ("1000", "0.0000001", "2000")


def test_declarar_el_rendimiento_propuesto_lo_devuelve_en_notacion_fija(monkeypatch) -> None:
    rendimiento = Rendimiento(
        codigo_partida="P-1", valor=MIL, tipo=TipoRendimiento.ESTIMADO, fecha=date(2026, 11, 19)
    )
    elaboracion = presupuestos_calculo.aplicacion_elaboracion
    monkeypatch.setattr(elaboracion, "rendimiento_por_declarar", lambda *a: None)
    monkeypatch.setattr(elaboracion, "declarar_rendimiento", lambda *a: rendimiento)
    peticion = DeclararRendimientoPeticion(
        codigo_partida="P-1", tipo="estimado", fecha=date(2026, 11, 19)
    )
    sesion = SimpleNamespace(commit=lambda: None)
    respuesta = presupuestos_calculo.declarar_rendimiento_propuesto(sesion, peticion)
    assert respuesta.valor == "1000"


def test_componentes_del_fcas_en_notacion_fija(monkeypatch) -> None:
    componente = SimpleNamespace(
        id="demo", nombre="Demostración", base="dias", valor=MIL, fuente="ficticio", a_cotejar=False
    )
    monkeypatch.setattr(fcas, "COMPONENTES_FCAS", (componente,))
    monkeypatch.setattr(fcas, "ParametrosCosto", lambda: SimpleNamespace(fcas=Decimal("1E+1")))
    respuesta = fcas.componentes_por_defecto()
    assert [c.valor for c in respuesta.componentes] == ["1000"]
    assert respuesta.fcas_version == "10"


def test_los_dias_pagados_del_fcas_en_notacion_fija() -> None:
    cuerpo = fcas.CalculoFcasEntrada(
        dias_calendario="0.0000001", dias_trabajados="0.0000001", componentes=[]
    )
    assert fcas.calcular(cuerpo).dias_pagados == "0.0000001"


def _item(cantidad: Decimal) -> ItemComputo:
    return ItemComputo(
        codigo_partida="P-1",
        descripcion="Partida de prueba",
        unidad="m3",
        cantidad=cantidad,
        origen_id="O-1",
        origen_tipo=OrigenTipo.TABULAR,
        dominio=Dominio.CIVIL,
    )


@pytest.mark.parametrize(("cantidad", "texto"), [(MIL, "1000"), (DIEZ_MILLONESIMA, "0.0000001")])
def test_la_cantidad_de_un_pendiente_viaja_en_notacion_fija(cantidad: Decimal, texto: str) -> None:
    assert presupuestos_ayudas._campos_pendiente(_item(cantidad))["cantidad"] == texto


def test_los_parametros_de_la_base_de_escenarios_en_notacion_fija(monkeypatch) -> None:
    modelo = SimpleNamespace(
        proyecto=SimpleNamespace(nombre="Obra de prueba"),
        fcas=Decimal("6E+0"),
        bono_alimentacion=MIL,
        administracion=DIEZ_MILLONESIMA,
        utilidad=Decimal("0.10"),
    )
    elaboracion = SimpleNamespace(
        presupuesto=SimpleNamespace(codigo="V-1", moneda="Bs", total=Decimal("1")), pendientes=[]
    )
    monkeypatch.setattr(presupuestos_escenarios, "_buscar_modelo", lambda s, c, p: modelo)
    monkeypatch.setattr(presupuestos_escenarios, "Catalogo", lambda sesion: None)
    monkeypatch.setattr(
        presupuestos_escenarios, "cargar_elaboracion", lambda s, p, c, cat: elaboracion
    )
    respuesta = presupuestos_escenarios.base_de_escenarios(None, "V-1")
    assert respuesta.parametros == {
        "fcas": "6",
        "bono_alimentacion": "1000",
        "administracion": "0.0000001",
        "utilidad": "0.10",
    }
