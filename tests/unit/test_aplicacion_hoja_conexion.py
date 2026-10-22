"""R17 ligada a cada elaboracion de la hoja nueva (T10, 3b-2; diseno 3b-B21, primera clausula).

La pagina clasica elabora solo por `_elaborar`, que agrega R17 (la conexion de cada punto) ligada al
espacio vigente (`tests/unit/test_ui_hoja_conexion.py`). En la interfaz nueva esa unica via es
`aplicacion.hoja_vista.elaborar`. Esta prueba lee el codigo (AST, sin importar nada del producto)
y falla si una funcion publica de `aplicacion/hoja.py` que llega a `elaborar_hoja` no esta
clasificada, o si la API o las vistas la usan por otra via. La segunda clausula de 3b-B21 (un punto
de agua sin fuente da R17 ADVERTENCIA en la auditoria) esta en `test_aplicacion_hoja_vista.py` y
`test_api_hoja.py` (R11, 3b-3); aqui solo se vigila que la auditoria salga de `calculo`.
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
HOJA = RAIZ / "aplicacion" / "hoja.py"
#: Quien puede llamar a las funciones que elaboran, fuera de `aplicacion/hoja.py`.
USO_PERMITIDO = {
    "elaborar_borrador": "solo desde hoja_vista.elaborar, que agrega R17",
    "guardar_version": "3d: con el borrador ligado a R17",
    "crear_primera_version": "3d: con el borrador ligado a R17",
    "con_plan_secuencial": "sin R17: solo lee el presupuesto (3c)",
}
CLASIFICADAS = {"elaborar_hoja", "elaborar_borrador", *USO_PERMITIDO}


def _llamadas(arbol: ast.AST) -> set[str]:
    nombres = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                nombres.add(f.id)
            elif isinstance(f, ast.Attribute):
                nombres.add(f.attr)
    return nombres


def _funciones_que_elaboran() -> set[str]:
    arbol = ast.parse(HOJA.read_text(encoding="utf-8"))
    llama = {f.name: _llamadas(f) for f in arbol.body if isinstance(f, ast.FunctionDef)}
    elaboran = {"elaborar_hoja"}
    while True:
        nuevas = {f for f, ll in llama.items() if ll & elaboran} - elaboran
        if not nuevas:
            break
        elaboran |= nuevas
    return {f for f in elaboran if not f.startswith("_")}


def _usos_fuera_de_la_copia() -> dict[str, list[tuple[str, str]]]:
    """Para cada llamada a una funcion que elabora: (archivo, funcion que la contiene)."""
    elaboran = _funciones_que_elaboran()
    usos: dict[str, list[tuple[str, str]]] = {}
    archivos = [
        *sorted((RAIZ / "api").rglob("*.py")),
        *sorted((RAIZ / "aplicacion").glob("hoja_*.py")),
    ]
    for archivo in archivos:
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for definicion in ast.walk(arbol):
            if not isinstance(definicion, ast.FunctionDef):
                continue
            for nombre in _llamadas(definicion) & elaboran:
                usos.setdefault(nombre, []).append(
                    (archivo.relative_to(RAIZ).as_posix(), definicion.name)
                )
    return usos


def test_toda_funcion_publica_de_la_copia_que_elabora_esta_clasificada():
    elaboran = _funciones_que_elaboran()
    assert {"elaborar_hoja", "elaborar_borrador", "guardar_version"} <= elaboran  # mira algo
    assert elaboran <= CLASIFICADAS, elaboran - CLASIFICADAS


def test_la_api_y_las_vistas_solo_llegan_a_la_copia_por_las_vias_clasificadas():
    usos = _usos_fuera_de_la_copia()
    assert set(usos) <= set(USO_PERMITIDO), set(usos) - set(USO_PERMITIDO)
    assert "elaborar_hoja" not in usos  # nadie se salta elaborar_borrador


def test_elaborar_borrador_solo_se_llama_desde_hoja_vista_elaborar():
    usos = _usos_fuera_de_la_copia()["elaborar_borrador"]
    assert usos == [("aplicacion/hoja_vista.py", "elaborar")]


def test_las_vistas_leen_siempre_el_calculo_que_agrega_r17():
    """Cada vista del borrador vivo (`vista_*(vivo, ...)` y el informe de la auditoria) pide el
    resultado a `calculo` (que elabora con R17), no a `elaborar_*`. Las que leen la base (precios y
    trazabilidad, 3b-3) no reciben un borrador y no elaboran nada."""
    arbol = ast.parse((RAIZ / "aplicacion" / "hoja_vista.py").read_text(encoding="utf-8"))
    funciones = [f for f in arbol.body if isinstance(f, ast.FunctionDef)]
    del_borrador = [
        f
        for f in funciones
        if (f.name.startswith("vista_") and f.args.args and f.args.args[0].arg == "vivo")
        or f.name == "informe_de_auditoria"
    ]
    assert {f.name for f in del_borrador} >= {
        "vista_espacio",
        "vista_presupuesto",
        "vista_apu",
        "vista_plan",
        "vista_equilibrio",
        "vista_parametros",
        "informe_de_auditoria",  # 3b-B21, segunda clausula: la auditoria sale de la via con R17
    }
    for f in del_borrador:
        assert "calculo" in _llamadas(f), f.name
    for f in funciones:
        if f.name != "elaborar":
            assert not _llamadas(f) & {"elaborar_borrador", "elaborar_hoja"}, f.name
