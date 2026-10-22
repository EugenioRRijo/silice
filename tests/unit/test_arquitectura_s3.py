"""Quién importa a quién en lo que agrega S3 (spec S3 §4.1 y §13.2, fila «Arquitectura»).

Complementa a `test_arquitectura.py` (que vigila `core/` y los adaptadores): aquí, `seguridad`,
`paquete`, `auditoria`, la interfaz de S3 y la API. Retiro de Streamlit (F4): se fueron con las
pantallas la regla de que ningún texto ajeno llega a Streamlit sin `texto_seguro` y las de quién
importa `ui.acceso`, `ui.entrega` y `ui.revision`.

Escrita en la auditoría final (2026-10-13) desde la tarea 23 del plan, con lo que S1, S2, S4 y la
1.5 agregaron después de escribirse: los llamadores del embudo de S1 y S2 (`convertir_version`,
`aplicar_decision`, la decisión de recuperación y la obra de control, bitácora S3-2), la caché del
libro de la empresa (1.5, por SHA-256 del contenido) y los mensajes fijos de `ui.cliente` y de
`asistente.administracion`."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


def _importados(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module)
            nombres.update(f"{nodo.module}.{a.name}" for a in nodo.names)  # `from ui import x`
    return nombres


def _archivos(carpeta: str) -> list[Path]:
    return sorted((RAIZ / carpeta).rglob("*.py"))


def _raices(ruta: Path) -> set[str]:
    return {nombre.split(".")[0] for nombre in _importados(ruta)}


@pytest.mark.parametrize("ruta", _archivos("seguridad"), ids=lambda r: r.name)
def test_seguridad_no_conoce_ni_al_nucleo_ni_a_las_pantallas_ni_a_los_adaptadores(ruta) -> None:
    prohibidas = {"core", "ui", "api", "adapters", "ml", "paquete", "auditoria", "streamlit"}
    assert not (_raices(ruta) & prohibidas), _raices(ruta) & prohibidas


@pytest.mark.parametrize("ruta", _archivos("paquete"), ids=lambda r: r.name)
def test_paquete_solo_usa_el_nucleo_y_seguridad_nunca_las_pantallas(ruta) -> None:
    prohibidas = {"ui", "api", "adapters", "ml", "auditoria", "streamlit", "fastapi"}
    assert not (_raices(ruta) & prohibidas), _raices(ruta) & prohibidas


@pytest.mark.parametrize("ruta", _archivos("auditoria"), ids=lambda r: r.name)
def test_auditoria_la_usan_la_api_y_la_interfaz_y_no_importa_ninguna(ruta) -> None:
    """RP8-6: vive aparte porque la API no puede importar `ui/`."""
    assert not (_raices(ruta) & {"ui", "api", "streamlit", "fastapi"})


def test_la_api_no_importa_la_interfaz() -> None:
    for ruta in _archivos("api"):
        assert not (_raices(ruta) & {"ui", "streamlit"}), ruta.name


@pytest.mark.parametrize("modulo", ["aplicacion/entrega.py", "aplicacion/revision.py"])
def test_las_orquestaciones_de_s3_no_usan_streamlit(modulo: str) -> None:
    assert "streamlit" not in _raices(RAIZ / modulo)


def test_ningun_modulo_usa_unsafe_allow_html() -> None:
    cuales = [
        ruta.relative_to(RAIZ).as_posix()
        for carpeta in ("api", "seguridad", "paquete", "auditoria", "aplicacion")
        for ruta in _archivos(carpeta)
        if "unsafe_allow_html" in ruta.read_text(encoding="utf-8")
    ]
    assert cuales == []


#: Nada por usuario en cachés compartidas por el proceso (S3 §4.4): estas son las únicas
#: cachés de `seguridad/` y `paquete/`, y ninguna guarda datos de una persona.
CACHES_PERMITIDAS = {
    "seguridad/cuentas.py": 1,  # la huella de relleno para usuarios inexistentes
}


def test_ninguna_cache_compartida_guarda_datos_de_una_persona() -> None:
    cuantas: dict[str, int] = {}
    for carpeta in ("aplicacion", "seguridad", "paquete", "auditoria", "api"):
        for ruta in _archivos(carpeta):
            texto = ruta.read_text(encoding="utf-8")
            n = sum(
                texto.count(marca)
                for marca in (
                    "st.cache_data",
                    "st.cache_resource",
                    "@cache",
                    "lru_cache",
                    "functools.cache",
                )
            )
            if n:
                cuantas[ruta.relative_to(RAIZ).as_posix()] = n
    assert cuantas == CACHES_PERMITIDAS


# --- el embudo: todo llamador dice quién guarda (RF-82, RF-83) -----------------------------------

#: Las funciones que crean una versión (o escriben su `RegistroCambio`) y el argumento con el que
#: dicen quién lo hace. S1 y S2 agregan las suyas (`convertir_version`, la decisión de
#: recuperación...) en la tarea que las crea.
EMBUDO = {
    "guardar_presupuesto": "usuario",
    "actualizar_precios": "usuario",
    "importar_presupuesto": "usuario",
    "guardar_edicion": "responsable",
    "restaurar_version": "responsable",
    "cotizar_insumo": "responsable",
    "retirar_cotizacion": "responsable",
    "_retirar_cotizacion": "responsable",
    "guardar_version": "responsable",
    "crear_primera_version": "responsable",
    "restaurar": "responsable",
    "cotizar": "responsable",
    "abrir_version": "responsable",
    # S1 y S2 (bitácora S3-2, «Llamadores»): la conversión de moneda y la decisión de recuperación
    "convertir_version": "responsable",
    "aplicar_decision": "responsable",
}
#: Los llamadores de hoy, fuera de `tests/`. Uno nuevo hace fallar la prueba hasta que se agrega
#: aquí con su prueba de que dice quién es.
LLAMADORES = {
    ("core/budget/actualizacion.py", "guardar_presupuesto"),
    ("core/budget/cotizacion.py", "guardar_presupuesto"),
    ("core/budget/edicion.py", "guardar_presupuesto"),
    ("core/budget/importacion.py", "guardar_presupuesto"),
    ("aplicacion/actualizacion.py", "actualizar_precios"),
    ("api/rutas/presupuestos.py", "guardar_presupuesto"),
    ("api/rutas/presupuestos.py", "actualizar_precios"),
    ("api/rutas/presupuestos.py", "importar_presupuesto"),
    ("scripts/generar_resultados_ml.py", "guardar_presupuesto"),
    ("scripts/generar_resultados_ml.py", "actualizar_precios"),
    ("scripts/medir_rnf03.py", "guardar_presupuesto"),
    ("scripts/medir_rnf03.py", "actualizar_precios"),
    ("scripts/probar_precios_maprex.py", "guardar_presupuesto"),
    ("scripts/probar_precios_maprex.py", "actualizar_precios"),
    ("scripts/seed_demo.py", "guardar_presupuesto"),
    ("scripts/seed_of001.py", "abrir_version"),
    # S1: la conversión de moneda; S2: la decisión de recuperación y la obra de control
    ("core/budget/moneda.py", "guardar_presupuesto"),
    ("core/budget/decision.py", "guardar_edicion"),
    ("aplicacion/control.py", "aplicar_decision"),
    # T10 (hoja en la interfaz nueva, Plan C): la hoja de `aplicacion/` (ya sin la copia de `ui/`)
    ("aplicacion/hoja.py", "guardar_edicion"),
    ("aplicacion/hoja.py", "guardar_presupuesto"),
    ("aplicacion/hoja.py", "restaurar_version"),
    ("aplicacion/hoja.py", "cotizar_insumo"),
    ("aplicacion/hoja.py", "_retirar_cotizacion"),
    ("aplicacion/hoja.py", "convertir_version"),
    ("api/rutas/hoja.py", "abrir_version"),  # R2: responsable = la persona de la sesion
    # 3d-1 (S1): guardar el borrador vivo; el responsable es la persona de la sesion, no el cuerpo
    ("aplicacion/hoja_guardado.py", "guardar_version"),
    ("aplicacion/hoja_guardado.py", "crear_primera_version"),
    # 3d-2 (S2 a S4): restaurar, cotizar y retirar desde una guardada; el responsable es la sesion
    ("aplicacion/hoja_versiones.py", "restaurar"),
    ("aplicacion/hoja_versiones.py", "cotizar"),
    ("aplicacion/hoja_versiones.py", "retirar_cotizacion"),
    ("api/rutas/hoja.py", "restaurar"),
    ("api/rutas/hoja.py", "cotizar"),
    ("api/rutas/hoja.py", "retirar_cotizacion"),
    ("scripts/generar_obra_control.py", "guardar_presupuesto"),
}


def _llamadas_del_embudo():
    for carpeta in (
        "core",
        "aplicacion",
        "api",
        "scripts",
        "adapters",
        "ml",
        "seguridad",
        "paquete",
        "auditoria",
        "asistente",
        "fusion",
        # `operacion` no: su `respaldo.restaurar` repone un juego de respaldo, no una versión
    ):
        for archivo in _archivos(carpeta):
            for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
                if not isinstance(nodo, ast.Call):
                    continue
                nombre = (
                    nodo.func.id
                    if isinstance(nodo.func, ast.Name)
                    else getattr(nodo.func, "attr", None)
                )
                if nombre in EMBUDO:
                    yield archivo.relative_to(RAIZ).as_posix(), nombre, nodo


def test_todo_llamador_del_embudo_dice_quien_guarda() -> None:
    sin_quien = sorted(
        f"{archivo}:{nodo.lineno} {nombre}() sin {EMBUDO[nombre]}="
        for archivo, nombre, nodo in _llamadas_del_embudo()
        if EMBUDO[nombre] not in {k.arg for k in nodo.keywords}
    )
    assert sin_quien == []


def test_la_lista_de_llamadores_del_embudo_esta_completa() -> None:
    encontrados = {(archivo, nombre) for archivo, nombre, _ in _llamadas_del_embudo()}
    nuevos, perdidos = sorted(encontrados - LLAMADORES), sorted(LLAMADORES - encontrados)
    assert encontrados == LLAMADORES, f"nuevos: {nuevos}; ya no existen: {perdidos}"
