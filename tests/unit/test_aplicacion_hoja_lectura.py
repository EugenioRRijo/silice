"""Lectura de la Hoja (`aplicacion/hoja.py`): abrir una version, historial, cambios y estado.

Corre los casos de LECTURA de la sub-rebanada 3b-1 (`abrir_version`, `historial_de_versiones`,
`cambios_entre`, `elaborar_borrador` y `estado_de_filas`, diseno §5.6 y 3b-B3C) sobre OF-001 y
TI-001, y fija con una tabla literal (diseno §5.7, 3b-B27) que toda funcion o clase publica de
`aplicacion/hoja.py` tiene rebanada y clase asignadas.

Oraculos a mano, ninguno sale del codigo: los literales de la memoria de OF-001
(`tests/fixtures/memorias/of001.md`: 6 ambientes, 6 fuentes y 21 puntos; FCAS 6,00; bono 5,81;
administracion 0,15; utilidad 0,10) y de la prueba de aceptacion SF (total 2 703,86; CV 2 137,44;
PE 1 530,49 en el Dia 23; 56,60 %; con administracion 0,20: 2 821,42; 1 763,39; 62,50 %). Las
pruebas ya no comparan contra `ui.hoja` (retiro de Streamlit, F6). Los casos de escritura
(guardar, restaurar, cotizar...) se prueban en las rebanadas 3c a 3e.
"""

from __future__ import annotations

import ast
import shutil
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion import hoja
from core.catalog import Catalogo, abrir_sesion, crear_motor
from tests.fixtures import caso_of001, caso_ti001
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    NOMBRE_TI001,
    plantilla_of001,
    plantilla_ti001,
)

RAIZ = Path(__file__).resolve().parents[2]
D = Decimal

#: Tabla de §5.7 del diseno, copiada como literal: funcion o clase publica -> (rebanada, clase).
#: «contrato»: la funcion tiene prueba de comportamiento y de mensajes en su rebanada;
#: «divergencia»: `abrir_version` se divide en la rebanada que la use;
#: «no migra»: ninguna ruta de la interfaz nueva la llama.
TABLA_5_7 = {
    "rotulo_de_valor": ("3b-2", "contrato"),
    "EstadoFila": ("3b-1", "contrato"),
    "ResultadoHoja": ("3b-1", "contrato"),
    "Borrador": ("3b-1", "contrato"),
    "filas_desde_espacio": ("3b-2", "contrato"),
    "espacio_desde_filas": ("3c-1", "contrato"),
    "borrador_de_version": ("ninguna", "no migra"),
    "items_del_borrador": ("3b-2", "contrato"),
    "elaborar_hoja": ("3b-2", "contrato"),
    "elaborar_borrador": ("3b-2", "contrato"),
    "claves_de_items": ("3b-2", "contrato"),
    "filas_del_presupuesto": ("3b-2", "contrato"),
    "estado_de_items": ("3b-2", "contrato"),
    "items_sin_escribir": ("3c-2", "contrato"),
    "items_elaborados": ("3c-1", "contrato"),
    "cantidades_escritas": ("3c-1", "contrato"),
    "plan_efectivo": ("3c-1", "contrato"),
    "cantidades_desde_filas": ("3c-2", "contrato"),
    "filas_de_apu": ("3b-2", "contrato"),
    "filtrar_partidas": ("3b-2", "contrato"),
    "filas_de_cierre": ("3b-2", "contrato"),
    "texto_numero": ("3b-2", "contrato"),
    "composicion_con_cantidades": ("3c-3", "contrato"),
    "FilaInsumo": ("3c-3", "contrato"),
    "insumos_candidatos": ("3c-3", "contrato"),
    "cambiar_insumo": ("3c-3", "contrato"),
    "filas_de_curva": ("3b-2", "contrato"),
    "plan_como_filas": ("3b-2", "contrato"),
    "parametros_desde_texto": ("3c-2", "contrato"),
    "ajustar_plan": ("3b-2", "contrato"),
    "con_plan_secuencial": ("3c-2", "contrato"),
    "plan_desde_filas": ("3c-2", "contrato"),
    "texto_equilibrio": ("3b-3", "contrato"),
    "cambios_entre": ("3b-1", "contrato"),
    "estado_de_filas": ("3b-2", "contrato"),
    "VersionAbierta": ("3b-1", "contrato"),
    "abrir_version": ("3b-1", "divergencia"),
    "espacio_de_version": ("3b-1", "contrato"),
    "lista_de_version": ("3c-1", "contrato"),
    "completar_composiciones": ("3c-1", "contrato"),
    "motivo_para_no_guardar": ("3d-1", "contrato"),
    "motivo_para_no_crear_primera": ("3d-1", "contrato"),
    "puede_guardar": ("ninguna", "no migra"),
    "VersionGuardada": ("3d-1", "contrato"),
    "guardar_version": ("3d-1", "contrato"),
    "crear_primera_version": ("3d-1", "contrato"),
    "restaurar": ("3d-2", "contrato"),
    "cotizar": ("3d-2", "contrato"),
    "retirar_cotizacion": ("3d-2", "contrato"),
    "convertir": ("3d-2", "contrato"),
    "codigo_vigente": ("3b-1", "contrato"),
    "FilaVersion": ("3b-1", "contrato"),
    "historial_de_versiones": ("3b-1", "contrato"),
    "FilaRegistro": ("3b-3", "contrato"),
    "registros_de_version": ("3b-3", "contrato"),
    "tabla_de_trazabilidad": ("3e", "contrato"),
    "tablas_de_espacio": ("3e", "contrato"),
    "tabla_de_precios": ("3e", "contrato"),
    "exportar_excel": ("3e", "contrato"),
    "excel_de_hoja_en_bytes": ("3e", "contrato"),
    "FilaPrecio": ("3b-3", "contrato"),
    "texto_propio": ("3b-3", "contrato"),
    "precios_de_version": ("3b-3", "contrato"),
    "composiciones_del_catalogo": ("ninguna", "no migra"),
    "formato_de_plano": ("3e", "contrato"),
    "leer_plano": ("3e", "contrato"),
    "subir_plano": ("3e", "contrato"),
    "resumen_del_informe": ("3e", "contrato"),
    "resumen_de_importacion": ("3e", "contrato"),
    "filas_del_informe": ("3e", "contrato"),
    "ResumenDeFusion": ("3e", "contrato"),
    "resumen_de_la_fusion": ("3e", "contrato"),
    "fusionar_plano": ("3e", "contrato"),
    "alturas_pendientes": ("3e", "contrato"),
    "cargar_alturas_desde_texto": ("3e", "contrato"),
    "circuitos_supuestos": ("3e", "contrato"),
    "declarar_circuitos_desde_texto": ("3e", "contrato"),
}


def _publicos(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    return {
        n.name
        for n in arbol.body
        if isinstance(n, ast.FunctionDef | ast.ClassDef) and not n.name.startswith("_")
    }


def test_toda_funcion_o_clase_publica_de_aplicacion_hoja_esta_asignada_a_una_rebanada():
    """3b-B27: el barrido AST de `aplicacion/hoja.py` contra la tabla literal de §5.7."""
    publicos = _publicos(RAIZ / "aplicacion" / "hoja.py")
    assert publicos - set(TABLA_5_7) == set(), "funcion publica sin rebanada asignada"
    assert set(TABLA_5_7) - publicos == set(), "la tabla nombra algo que ya no existe"


# --- los casos de lectura ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> tuple[Path, Path]:
    carpeta = tmp_path_factory.mktemp("lectura_hoja")
    return plantilla_of001(carpeta / "of001.db"), plantilla_ti001(carpeta / "ti001.db")


def _abrir(plantilla: Path, destino: Path, nombre: str, codigo: str = "001"):
    """Copia la plantilla, abre la version `codigo` y devuelve (abierta, historial, vigente)."""
    copia = destino / f"{nombre[:6]}.db"
    shutil.copyfile(plantilla, copia)
    motor = crear_motor(f"sqlite:///{copia.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            abierta = hoja.abrir_version(
                sesion, catalogo, nombre, codigo, fecha_evaluacion=caso_of001.FECHA
            )
            historial = hoja.historial_de_versiones(sesion, nombre)
            vigente = hoja.codigo_vigente(sesion, nombre)
    finally:
        motor.dispose()
    return abierta, historial, vigente


@pytest.fixture(scope="module")
def _of001(_plantillas, tmp_path_factory):
    return _abrir(_plantillas[0], tmp_path_factory.mktemp("of001_lectura"), NOMBRE_OF001)


@pytest.fixture(scope="module")
def _ti001(_plantillas, tmp_path_factory):
    return _abrir(
        _plantillas[1], tmp_path_factory.mktemp("ti001_lectura"), NOMBRE_TI001, caso_ti001.CODIGO
    )


def test_abrir_of001_da_el_total_de_la_memoria(_of001):
    abierta, _, _ = _of001
    assert abs(abierta.guardada.presupuesto.total - D("2703.86")) <= D("0.01")
    assert abierta.guardada.presupuesto.moneda == "USD"
    assert abierta.solo_lectura is False
    assert abierta.espacio_de == "001"
    assert abierta.proyecto == NOMBRE_OF001
    assert abierta.codigo == "001"
    assert abierta.lista == "Lista MaPreX jul-2026 (OF-001)"
    assert abierta.instantanea.creadas == ()


def test_el_borrador_de_of001_trae_el_espacio_y_los_parametros_de_la_memoria(_of001):
    """Memoria §1: 6 ambientes, 6 fuentes y 21 puntos; FCAS 6,00, bono 5,81, 0,15 y 0,10."""
    borrador = _of001[0].borrador
    assert (len(borrador.espacio.ambientes), len(borrador.espacio.fuentes)) == (6, 6)
    assert len(borrador.espacio.puntos) == 21
    parametros = borrador.parametros
    assert (parametros.fcas, parametros.bono_alimentacion) == (D("6.00"), D("5.8100"))
    assert (parametros.administracion, parametros.utilidad) == (D("0.15"), D("0.10"))
    assert borrador.moneda == "USD" and borrador.fecha == caso_of001.FECHA
    # el espacio da los items (ninguno fijo) y no hay cantidades escritas a mano
    assert (borrador.items_base, borrador.cantidades) == ((), {})
    assert borrador.plan[0] == ("Dia 1", (("AF-CODO-1/2", D("1")),))  # el plan del Dia 1
    assert len(borrador.plan) >= 23  # el equilibrio cae en el Dia 23 (memoria)
    assert "AF-LLAVE" in borrador.composiciones


def test_abrir_ti001_no_tiene_espacio_y_trae_sus_27_items(_ti001):
    abierta, _, _ = _ti001
    assert abierta.espacio_de is None
    assert abierta.borrador.espacio == type(abierta.borrador.espacio)()  # espacio vacio
    # los items de la version, no los del espacio: las 27 partidas de la topologia de TI-001
    assert len(abierta.borrador.items_base) == len(caso_ti001.items()) == 27
    assert set(abierta.borrador.composiciones) == set(caso_ti001.COMPOSICIONES)
    assert abierta.borrador.parametros == caso_ti001.PARAMETROS
    assert (abierta.proyecto, abierta.codigo) == (NOMBRE_TI001, caso_ti001.CODIGO)


def test_el_historial_de_of001_es_una_sola_version_vigente_y_sin_cambios(_of001):
    _, filas, vigente = _of001
    esperado = [("001", "", "", True, False, 0)]  # una version elaborada de cero (aceptacion SF)
    assert [
        (f.codigo, f.motivo, f.origen, f.vigente, f.descartada, f.cambios) for f in filas
    ] == esperado
    assert filas[0].fecha == caso_of001.FECHA
    assert vigente == "001"


def test_elaborar_of001_da_los_literales_de_la_memoria(_of001):
    abierta = _of001[0]
    resultado = hoja.elaborar_borrador(abierta.borrador)
    pe = resultado.equilibrio
    assert abs(resultado.elaboracion.presupuesto.total - D("2703.86")) <= D("0.01")
    assert abs(pe.costo_variable - D("2137.44")) <= D("0.01")
    assert abs(pe.punto - D("1530.49")) <= D("0.01")
    assert abs(pe.porcentaje - D("56.60")) <= D("0.01")
    assert pe.periodo.split(" [")[0] == "Dia 23"
    assert hoja.cambios_entre(abierta.borrador, abierta.borrador) == []


def test_un_parametro_cambiado_recalcula_con_los_literales(_of001):
    """Administracion 0,20: total 2 821,42; PE 1 763,39; 62,50 % y un solo cambio (confirmado)."""
    abierta = _of001[0]
    editado = replace(
        abierta.borrador,
        parametros=replace(abierta.borrador.parametros, administracion=D("0.20")),
    )
    resultado = hoja.elaborar_borrador(editado)
    assert abs(resultado.elaboracion.presupuesto.total - D("2821.42")) <= D("0.01")
    assert abs(resultado.equilibrio.punto - D("1763.39")) <= D("0.01")
    assert abs(resultado.equilibrio.porcentaje - D("62.50")) <= D("0.01")
    cambios = hoja.cambios_entre(abierta.borrador, editado)
    assert [(c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("parametro", "administracion", "valor", "0.15", "0.20")
    ]


def test_el_estado_de_filas_de_of001_trae_una_fila_por_ambiente_fuente_y_punto(_of001):
    """Memoria §1: 6 ambientes + 6 fuentes + 21 puntos = 33 filas, todas del espacio (`esp_`)."""
    abierta = _of001[0]
    resultado = hoja.elaborar_borrador(abierta.borrador)
    estados = hoja.estado_de_filas(abierta.borrador.espacio, resultado.elaboracion.informe)
    assert len(estados) == 6 + 6 + 21
    assert all(clave.startswith("esp_") for clave in estados)
    assert {"esp_ambientes:BAN-01", "esp_ambientes:ZB"} <= set(estados)
    assert all(e.severidad is None or e.texto for e in estados.values())


def test_el_estado_de_filas_marca_ok_en_una_fila_que_ningun_hallazgo_toca(_of001):
    """Oraculo a mano: sin hallazgos todas las filas son `EstadoFila(None, "OK")`."""
    from types import SimpleNamespace

    abierta = _of001[0]
    sin_hallazgos = SimpleNamespace(hallazgos=())
    estados = hoja.estado_de_filas(abierta.borrador.espacio, sin_hallazgos)
    espacio = abierta.borrador.espacio
    assert len(estados) == len(espacio.ambientes) + len(espacio.fuentes) + len(espacio.puntos)
    assert {(e.severidad, e.texto) for e in estados.values()} == {(None, "OK")}
    assert estados["esp_ambientes:BAN-01"] == hoja.EstadoFila(None, "OK")


def test_elaborar_ti001_da_el_punto_de_equilibrio_de_la_memoria(_ti001):
    pe = hoja.elaborar_borrador(_ti001[0].borrador).equilibrio
    assert abs(pe.porcentaje - D("56.60")) <= D("0.01")  # 0,15 / 0,265 de las ventas
