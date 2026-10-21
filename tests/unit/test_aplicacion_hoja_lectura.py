"""Plan C de la Hoja (T10, 3b-1): `aplicacion/hoja.py` es una COPIA de `ui/hoja.py`.

`ui/hoja.py` esta en el congelado del experimento (RS-9) y no se toca; la interfaz nueva usa
`aplicacion.hoja`, que es otra clase `Borrador` con las mismas funciones. Esta prueba (que SI puede
importar `ui`) corre los casos de LECTURA de la sub-rebanada 3b-1 en las dos y compara resultados:
`abrir_version`, `historial_de_versiones`, `cambios_entre`, `elaborar_borrador` y `estado_de_filas`
(diseno §5.6 y 3b-B3C), sobre OF-001 y TI-001. Ademas fija con una tabla literal (diseno §5.7,
3b-B27) que toda funcion o clase publica de la copia tiene rebanada y clase asignadas.

Oraculos: los literales de la memoria de OF-001 (`tests/fixtures/memorias/of001.md`) y de la prueba
de aceptacion SF (total 2 703,86; CV 2 137,44; PE 1 530,49 en el Dia 23; 56,60 %; con
administracion 0,20: 2 821,42; 1 763,39; 62,50 %); ninguno sale de la copia. Los casos de
escritura (guardar, restaurar, cotizar...) se prueban en las rebanadas 3c a 3e.

Si la copia y la clasica divergen, la unica que se corrige es la copia: `ui/hoja.py` esta
congelado. Un cambio legitimo del comportamiento exige cambiar esta prueba con el aval de Eugenio.
"""

from __future__ import annotations

import ast
import dataclasses
import shutil
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from core.catalog import Catalogo, abrir_sesion, crear_motor
from tests.fixtures import caso_of001, caso_ti001
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    NOMBRE_TI001,
    plantilla_of001,
    plantilla_ti001,
)
from ui import hoja as clasica

RAIZ = Path(__file__).resolve().parents[2]
D = Decimal

#: Tabla de §5.7 del diseno, copiada como literal: funcion o clase publica -> (rebanada, clase).
#: «contrato»: idéntica por contrato (esta prueba exige igualdad de comportamiento y de mensajes);
#: «divergencia»: puede diferir de la clasica (`abrir_version` se divide en la rebanada que la use);
#: «no migra»: la copia la trae pero ninguna ruta de la interfaz nueva la llama.
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


def test_toda_funcion_o_clase_publica_de_la_copia_esta_asignada_a_una_rebanada():
    """3b-B27: el barrido AST de `aplicacion/hoja.py` contra la tabla literal de §5.7."""
    publicos = _publicos(RAIZ / "aplicacion" / "hoja.py")
    assert publicos - set(TABLA_5_7) == set(), "funcion publica sin rebanada asignada"
    assert set(TABLA_5_7) - publicos == set(), "la tabla nombra algo que la copia ya no tiene"


def test_la_copia_trae_las_mismas_publicas_que_la_clasica():
    assert _publicos(RAIZ / "aplicacion" / "hoja.py") == _publicos(RAIZ / "ui" / "hoja.py")


def test_la_copia_no_importa_interfaz_ni_api_y_la_clasica_no_se_toco():
    """El Plan C no toca nada congelado: `ui/hoja.py` sigue importando de `ui` y la copia no."""
    arbol = ast.parse((RAIZ / "aplicacion" / "hoja.py").read_text(encoding="utf-8"))
    modulos = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module.split(".")[0])
        elif isinstance(nodo, ast.Import):
            modulos.update(alias.name.split(".")[0] for alias in nodo.names)
    assert modulos.isdisjoint({"ui", "streamlit", "api", "scripts", "tests"})


# --- los casos de lectura, en las dos --------------------------------------------------------


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> tuple[Path, Path]:
    carpeta = tmp_path_factory.mktemp("paridad_hoja")
    return plantilla_of001(carpeta / "of001.db"), plantilla_ti001(carpeta / "ti001.db")


def _abrir(plantilla: Path, destino: Path, modulo, nombre: str, codigo: str = "001"):
    """Copia la plantilla, abre la version `codigo` con `modulo` y devuelve (abierta, historial)."""
    copia = destino / f"{modulo.__name__}.db"
    shutil.copyfile(plantilla, copia)
    motor = crear_motor(f"sqlite:///{copia.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            abierta = modulo.abrir_version(
                sesion, catalogo, nombre, codigo, fecha_evaluacion=caso_of001.FECHA
            )
            historial = modulo.historial_de_versiones(sesion, nombre)
            vigente = modulo.codigo_vigente(sesion, nombre)
    finally:
        motor.dispose()
    return abierta, historial, vigente


def _borrador_plano(borrador) -> dict:
    """El borrador como diccionario, sin la clase (la copia define la suya)."""
    campos = dataclasses.fields(borrador)
    return {c.name: _plano(getattr(borrador, c.name)) for c in campos if c.name != "reglas_extra"}


def _plano(valor):
    if dataclasses.is_dataclass(valor) and not isinstance(valor, type):
        return {c.name: _plano(getattr(valor, c.name)) for c in dataclasses.fields(valor)}
    if isinstance(valor, dict):
        return {k: _plano(v) for k, v in valor.items()}
    if isinstance(valor, list | tuple):
        return [_plano(v) for v in valor]
    return valor


@pytest.fixture(scope="module")
def _of001(_plantillas, tmp_path_factory):
    from aplicacion import hoja as copia

    destino = tmp_path_factory.mktemp("of001_pareja")
    return (
        _abrir(_plantillas[0], destino, clasica, NOMBRE_OF001),
        _abrir(_plantillas[0], destino, copia, NOMBRE_OF001),
    )


@pytest.fixture(scope="module")
def _ti001(_plantillas, tmp_path_factory):
    from aplicacion import hoja as copia

    destino = tmp_path_factory.mktemp("ti001_pareja")
    return (
        _abrir(_plantillas[1], destino, clasica, NOMBRE_TI001, caso_ti001.CODIGO),
        _abrir(_plantillas[1], destino, copia, NOMBRE_TI001, caso_ti001.CODIGO),
    )


def test_abrir_of001_da_el_total_de_la_memoria_en_las_dos(_of001):
    (vieja, _, _), (nueva, _, _) = _of001
    for abierta in (vieja, nueva):
        assert abs(abierta.guardada.presupuesto.total - D("2703.86")) <= D("0.01")
        assert abierta.guardada.presupuesto.moneda == "USD"
        assert abierta.solo_lectura is False
        assert abierta.espacio_de == "001"
    assert _borrador_plano(vieja.borrador) == _borrador_plano(nueva.borrador)
    assert nueva.guardada.presupuesto.total == vieja.guardada.presupuesto.total
    assert (nueva.proyecto, nueva.codigo, nueva.lista) == (
        vieja.proyecto,
        vieja.codigo,
        vieja.lista,
    )
    assert nueva.instantanea.creadas == vieja.instantanea.creadas


def test_abrir_ti001_no_tiene_espacio_y_es_igual_en_las_dos(_ti001):
    (vieja, _, _), (nueva, _, _) = _ti001
    for abierta in (vieja, nueva):
        assert abierta.espacio_de is None
        assert abierta.borrador.espacio == type(abierta.borrador.espacio)()  # espacio vacio
        assert abierta.borrador.items_base  # los items de la version, no los del espacio
    assert _borrador_plano(vieja.borrador) == _borrador_plano(nueva.borrador)
    assert nueva.guardada.presupuesto.total == vieja.guardada.presupuesto.total


def test_el_historial_de_of001_es_una_sola_version_vigente_y_sin_cambios(_of001):
    (_, vieja, cv), (_, nueva, cn) = _of001
    esperado = [("001", "", "", True, False, 0)]  # una version elaborada de cero (aceptacion SF)
    for filas in (vieja, nueva):
        assert [
            (f.codigo, f.motivo, f.origen, f.vigente, f.descartada, f.cambios) for f in filas
        ] == esperado
        assert filas[0].fecha == caso_of001.FECHA
    assert cv == cn == "001"


def test_elaborar_of001_da_los_literales_de_la_memoria_en_las_dos(_of001):
    (vieja, _, _), (nueva, _, _) = _of001
    from aplicacion import hoja as copia

    for modulo, abierta in ((clasica, vieja), (copia, nueva)):
        resultado = modulo.elaborar_borrador(abierta.borrador)
        pe = resultado.equilibrio
        assert abs(resultado.elaboracion.presupuesto.total - D("2703.86")) <= D("0.01")
        assert abs(pe.costo_variable - D("2137.44")) <= D("0.01")
        assert abs(pe.punto - D("1530.49")) <= D("0.01")
        assert abs(pe.porcentaje - D("56.60")) <= D("0.01")
        assert pe.periodo.split(" [")[0] == "Dia 23"
        assert modulo.cambios_entre(abierta.borrador, abierta.borrador) == []


def test_un_parametro_cambiado_recalcula_igual_en_las_dos_con_los_literales(_of001):
    """Administracion 0,20: total 2 821,42; PE 1 763,39; 62,50 % y un solo cambio (confirmado)."""
    (vieja, _, _), (nueva, _, _) = _of001
    from aplicacion import hoja as copia

    for modulo, abierta in ((clasica, vieja), (copia, nueva)):
        editado = replace(
            abierta.borrador,
            parametros=replace(abierta.borrador.parametros, administracion=D("0.20")),
        )
        resultado = modulo.elaborar_borrador(editado)
        assert abs(resultado.elaboracion.presupuesto.total - D("2821.42")) <= D("0.01")
        assert abs(resultado.equilibrio.punto - D("1763.39")) <= D("0.01")
        assert abs(resultado.equilibrio.porcentaje - D("62.50")) <= D("0.01")
        cambios = modulo.cambios_entre(abierta.borrador, editado)
        assert [(c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
            ("parametro", "administracion", "valor", "0.15", "0.20")
        ]


def test_el_estado_de_filas_de_of001_es_igual_en_las_dos(_of001):
    (vieja, _, _), (nueva, _, _) = _of001
    from aplicacion import hoja as copia

    estados = []
    for modulo, abierta in ((clasica, vieja), (copia, nueva)):
        resultado = modulo.elaborar_borrador(abierta.borrador)
        estados.append(
            {
                k: (None if e.severidad is None else e.severidad.name, e.texto)
                for k, e in modulo.estado_de_filas(
                    abierta.borrador.espacio, resultado.elaboracion.informe
                ).items()
            }
        )
    assert estados[0] == estados[1]
    assert estados[0]  # hay filas del espacio (6 ambientes, fuentes y puntos de OF-001)
    assert all(clave.startswith("esp_") for clave in estados[0])


def test_el_estado_de_filas_marca_ok_en_una_fila_que_ningun_hallazgo_toca(_of001):
    """Oraculo a mano: sin hallazgos todas las filas son `EstadoFila(None, "OK")`."""
    from types import SimpleNamespace

    from aplicacion import hoja as copia

    (_, _, _), (nueva, _, _) = _of001
    sin_hallazgos = SimpleNamespace(hallazgos=())
    estados = copia.estado_de_filas(nueva.borrador.espacio, sin_hallazgos)
    espacio = nueva.borrador.espacio
    assert len(estados) == len(espacio.ambientes) + len(espacio.fuentes) + len(espacio.puntos)
    assert {(e.severidad, e.texto) for e in estados.values()} == {(None, "OK")}
    assert estados["esp_ambientes:BAN-01"] == copia.EstadoFila(None, "OK")


def test_elaborar_ti001_da_el_punto_de_equilibrio_de_la_memoria_en_las_dos(_ti001):
    (vieja, _, _), (nueva, _, _) = _ti001
    from aplicacion import hoja as copia

    for modulo, abierta in ((clasica, vieja), (copia, nueva)):
        pe = modulo.elaborar_borrador(abierta.borrador).equilibrio
        assert abs(pe.porcentaje - D("56.60")) <= D("0.01")  # 0,15 / 0,265 de las ventas
    assert (
        copia.elaborar_borrador(nueva.borrador).equilibrio
        == clasica.elaborar_borrador(vieja.borrador).equilibrio
    )
