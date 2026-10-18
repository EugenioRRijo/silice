"""UC-17 4-5 desde la capa sin Streamlit: referencia MaPreX, lista de empresa y R11/R12 de la lista
sola, sin version: el impacto es por unidad (memoria tests/fixtures/memorias/s1_precios_empresa.md,
columna «Δ por unidad»). La lista sola trae ademas los R12 de los precios heredados de la base: la
prueba exige las filas de la memoria, no el conjunto exacto (ese es de la version, Tarea 8)."""

import importlib
from datetime import date
from decimal import Decimal
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import models
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.catalog.empresa import PrecioPropio, crear_lista_de_empresa, lista_de_referencia
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from operacion.base_datos import preparar_base
from scripts.seed import sembrar
from tests.fixtures.subproceso import importar_en_limpio, modulos_cargados
from ui import precios_empresa

CSV = Path(__file__).resolve().parents[1] / "fixtures" / "precios_empresa_s1.csv"
EVALUACION = date(2026, 10, 1)
#: (regla, severidad, insumo) -> impacto por unidad tal como lo presenta la pantalla (memoria).
DE_LA_MEMORIA = {
    ("R11", "ADVERTENCIA", 'UNION PVC A.B. 4"'): "1057.53",
    ("R11", "ADVERTENCIA", "ARENA LAVADA"): "11328.78",
    ("R11", "INFO", "LIJA DE AGUA N 100"): "",
    ("R12", "ADVERTENCIA", 'CLAVO DE ACERO LISO L=2 1/2"'): "108.15",
    ("R12", "ADVERTENCIA", "MATERIAL GRANULAR INTEGRAL"): "1622.25",
    ("R12", "ERROR", "PEGAMENTO PARA PVC  1/4 GL TANGIT  O SIM"): "",
    ("R12", "ADVERTENCIA", 'TUBO PVC A.N. D=4" / 110 MM E = 2,2 MM NORMA'): "0.00",
}


def _es(fila, regla, severidad, insumo):
    if (fila["Regla"], fila["Severidad"]) != (regla, severidad):
        return False
    # El catalogo trae «Arena lavada» y la lista «ARENA LAVADA»: misma identidad, otra caja.
    texto = fila["Descripción"].casefold()
    insumo = insumo.casefold()
    return insumo in texto if severidad == "INFO" else texto.startswith(f"{insumo}:")


def test_referencia_lista_de_empresa_y_hallazgos_de_la_memoria(tmp_path):
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    crear_esquema(motor)
    try:
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
            assert "cargada" in precios_empresa.cargar_referencia_maprex(sesion)
            assert "ya estaba" in precios_empresa.cargar_referencia_maprex(sesion)
            Catalogo(sesion).dar_de_alta_insumo(
                models.TipoInsumo.MATERIAL, "LIJA DE AGUA N 100", "pza"
            )
            registrar_importacion(
                sesion,
                definicion_tasa("venta"),
                [Observacion(EVALUACION, Decimal("860.18"))],
                archivo="FUENTE.md",
                huella="e" * 64,
                fuente="https://www.bcv.org.ve/",
                fecha_descarga=date(2026, 10, 8),
                responsable="Admin",
                filas_leidas=1,
                filas_rechazadas=0,
            )
            sesion.commit()
            resumen = precios_empresa.crear_lista(
                sesion,
                CSV,
                empresa_nombre="Constructora Ejemplo, C.A.",
                empresa_rif="J-00000000-0",
                base_id=lista_de_referencia(sesion).id,
                moneda="Bs",
                fecha=date(2026, 9, 20),
                fuente="lista interna 2026-09",
                nombre="",
            )
            assert (resumen.propios, resumen.desconocidos) == (10, ())
            ((lista_id, nombre),) = precios_empresa.listas_de_empresa(sesion)
            assert nombre == resumen.nombre
            filas = precios_empresa.hallazgos_de_lista(sesion, lista_id, EVALUACION)
    finally:
        motor.dispose()
    assert all(tuple(fila) == precios_empresa.COLUMNAS_HALLAZGOS for fila in filas)
    for (regla, severidad, insumo), impacto in DE_LA_MEMORIA.items():
        (fila,) = [f for f in filas if _es(f, regla, severidad, insumo)]
        assert fila["Impacto"] == impacto, (regla, insumo)


def test_la_pagina_no_importa_el_script_de_maprex_al_cargarse(tmp_path):
    """RV-25: el script de la lista MaPreX se importa dentro de la accion, no al cargar."""
    salida = importar_en_limpio(["ui.paginas.precios_empresa"], cwd=tmp_path)
    assert salida.returncode == 0, salida.stderr
    assert "scripts.lista_maprex_bs" not in modulos_cargados(salida)


# --- RF-100: el boton de variaciones atipicas en la lista de la empresa ----------------------

ROTULO_ATIPICOS = "Buscar variaciones atípicas de precio"
#: Memoria `atipicos_s3.md` §1 y §2: nueve precios de listas globales (enero a septiembre de 2026) y
#: el décimo, propio de la lista de la empresa (octubre).
CON_ATIPICO = (1, 2, 4, 8, 16, 32, 64, 128, 256, 257)
SIN_ATIPICO = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512)


def _caso_con_la_serie(monkeypatch, tmp_path: Path, precios) -> AppTest:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            insumo = models.Insumo(
                codigo="ATIP-001", tipo=models.TipoInsumo.MATERIAL, descripcion="Arena", unidad="m3"
            )
            sesion.add(insumo)
            sesion.flush()
            base = None
            for mes, precio in enumerate(precios[:9], start=1):
                base = models.ListaPrecios(
                    nombre=f"MaPreX {mes:02d}",
                    moneda="USD",
                    fecha_vigencia=date(2026, mes, 1),
                    origen="prueba",
                )
                sesion.add(base)
                sesion.flush()
                sesion.add(
                    models.PrecioInsumo(
                        lista_id=base.id, insumo_id=insumo.id, precio=Decimal(precio)
                    )
                )
            sesion.flush()
            crear_lista_de_empresa(
                sesion,
                "Constructora Ejemplo, C.A.",
                "J-00000000-0",
                base,
                [PrecioPropio(insumo.id, Decimal(precios[9]), date(2026, 10, 1), "prueba")],
                moneda="USD",
                fecha=date(2026, 10, 1),
                fuente="prueba",
                referencia=None,
            )
            sesion.commit()
    finally:
        motor.dispose()
    monkeypatch.setattr(importlib.import_module("ui.caso"), "RUTA_BASE_POR_DEFECTO", str(ruta))
    at = AppTest.from_string(
        "from ui.paginas.precios_empresa import render\nrender()\n", default_timeout=90
    )
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _pulsar_atipicos(at: AppTest) -> AppTest:
    next(b for b in at.button if b.label == ROTULO_ATIPICOS).click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_la_lista_de_la_empresa_muestra_la_advertencia_de_variacion_atipica(monkeypatch, tmp_path):
    at = _pulsar_atipicos(_caso_con_la_serie(monkeypatch, tmp_path, CON_ATIPICO))
    assert [w.value for w in at.warning] == [
        r"ATIP\-001: variación de 0\.39 % entre 2026\-09\-01 y 2026\-10\-01 \(en USD\) se "
        "aparta del historial de variaciones del insumo"
    ]
    assert not at.error  # nunca ERROR (RF-100)


def test_sin_atipico_la_lista_de_la_empresa_no_advierte(monkeypatch, tmp_path):
    at = _pulsar_atipicos(_caso_con_la_serie(monkeypatch, tmp_path, SIN_ATIPICO))
    assert not at.warning and not at.error
    assert any("Ninguna variación atípica" in s.value for s in at.success)


def test_sin_pulsar_la_lista_de_la_empresa_no_busca_atipicos(monkeypatch, tmp_path):
    at = _caso_con_la_serie(monkeypatch, tmp_path, CON_ATIPICO)
    assert not at.warning and not at.success
