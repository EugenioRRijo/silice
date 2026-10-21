"""RM-1: la logica de «Precios de la empresa» vive en `aplicacion/precios_empresa.py` y
`ui/precios_empresa.py` solo la reexporta. La capa de aplicacion no importa `scripts`, asi que
repite los datos de la referencia MaPreX en Bs; esta prueba los ata a los del guion que genero
el CSV."""

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path

import aplicacion.precios_empresa as original
import ui.precios_empresa as reexportado
from aplicacion import precios_empresa
from core import models
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.catalog.empresa import lista_de_referencia
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from scripts.lista_maprex_bs import (
    FECHA_TASA_MAPREX,
    FUENTE_TASA_MAPREX,
    RUTA_SALIDA,
    TASA_MAPREX,
)
from scripts.seed import sembrar

RAIZ = Path(__file__).resolve().parents[2]


def test_los_datos_de_la_referencia_son_los_del_guion_de_maprex() -> None:
    assert original.TASA_MAPREX == TASA_MAPREX
    assert original.FECHA_TASA_MAPREX == FECHA_TASA_MAPREX
    assert original.FUENTE_TASA_MAPREX == FUENTE_TASA_MAPREX
    assert original.RUTA_REFERENCIA_MAPREX == RUTA_SALIDA


def test_ui_precios_empresa_reexporta_la_capa_de_aplicacion() -> None:
    assert reexportado.__all__ and set(reexportado.__all__) <= set(vars(original))
    for nombre in reexportado.__all__:
        assert getattr(reexportado, nombre) is getattr(original, nombre), nombre
    arbol = ast.parse((RAIZ / "ui" / "precios_empresa.py").read_text(encoding="utf-8"))
    definiciones = [
        nodo.name
        for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef)
    ]
    assert definiciones == []


# --- movida de tests/unit/test_ui_precios_empresa.py (retiro de Streamlit, F3) ---------------

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
