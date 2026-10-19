"""Quién importa a quién en lo que agrega S3 (spec S3 §4.1 y §13.2, fila «Arquitectura»).

Complementa a `test_arquitectura.py` (que vigila `core/` y los adaptadores): aquí, `seguridad`,
`paquete`, `auditoria`, la interfaz de S3, la API y la regla de que ningún texto ajeno llega
a Streamlit sin `texto_seguro`.

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


@pytest.mark.parametrize(
    "modulo", ["aplicacion/entrega.py", "ui/entrega.py", "ui/revision.py", "ui/texto_seguro.py"]
)
def test_las_orquestaciones_de_s3_no_usan_streamlit(modulo: str) -> None:
    assert "streamlit" not in _raices(RAIZ / modulo)


def test_solo_el_marco_importa_ui_acceso() -> None:
    importadores = sorted(
        ruta.relative_to(RAIZ).as_posix()
        for ruta in _archivos("ui")
        if ruta.name != "acceso.py"
        and any(n == "ui.acceso" or n.startswith("ui.acceso.") for n in _importados(ruta))
    )
    assert importadores == ["ui/app.py"]


def test_solo_las_pantallas_y_el_marco_importan_ui_entrega_y_ui_revision() -> None:
    permitidos = {
        "ui/app.py",
        "ui/caso.py",
        "ui/paginas/entregar.py",
        "ui/paginas/revisar.py",
        "ui/paginas/hoja.py",
    }  # `caso` sella al abrir; `hoja` verifica la cadena
    importadores = {
        ruta.relative_to(RAIZ).as_posix()
        for ruta in _archivos("ui")
        if any(n in {"ui.entrega", "ui.revision"} for n in _importados(ruta))
    }
    assert importadores <= permitidos


def test_ningun_modulo_usa_unsafe_allow_html() -> None:
    cuales = [
        ruta.relative_to(RAIZ).as_posix()
        for carpeta in ("ui", "api", "seguridad", "paquete", "auditoria")
        for ruta in _archivos(carpeta)
        if "unsafe_allow_html" in ruta.read_text(encoding="utf-8")
    ]
    assert cuales == []


#: Nada por usuario en cachés compartidas por el proceso (S3 §4.4): estas son las únicas
#: cachés de `ui/`, `seguridad/` y `paquete/`, y ninguna guarda datos de una persona.
CACHES_PERMITIDAS = {
    "seguridad/cuentas.py": 1,  # la huella de relleno para usuarios inexistentes
    # 1.5: el libro abierto para la vista calcada, con el SHA-256 de su contenido como clave (solo
    # lo alcanza quien sube los mismos octetos); la marca aparece en el docstring y en el decorador.
    "ui/paginas/libros.py": 2,
}


def test_ninguna_cache_compartida_guarda_datos_de_una_persona() -> None:
    cuantas: dict[str, int] = {}
    for carpeta in ("ui", "seguridad", "paquete", "auditoria", "api"):
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


# --- texto ajeno -----------------------------------------------------------------------------

PAGINAS_CON_TEXTO_AJENO = (
    "ui/paginas/administracion.py",
    "ui/paginas/entregar.py",
    "ui/paginas/revisar.py",
    "ui/acceso.py",
)
LLAMADAS_DE_TEXTO = {
    "markdown",
    "info",
    "warning",
    "error",
    "success",
    "caption",
    "write",
    "subheader",
    "header",
    "title",
    "text_input",
    "metric",
    "toast",
}
SEGURAS = {"texto_seguro", "formatear_decimal", "len", "sum", "sorted", "isoformat"}


#: Variables que solo reciben literales propios (un título, un aviso fijo): se vigilan en su
#: origen con la misma regla. Cualquier otro nombre sin `texto_seguro` es sospechoso.
LITERALES_PROPIOS = {"titulo", "exito", "aviso"}
#: Expresiones que un módulo puede pasar sin `texto_seguro` porque su texto es fijo por diseño.
FIJAS_POR_MODULO = {
    "ui/acceso.py": {"str(error)"},  # mensajes fijos de `seguridad.cuentas`
    # `motivo` sale de `ui.cliente.operacion_sensible_permitida`: MENSAJE_REMOTO o MENSAJE_PENDIENTE
    "ui/paginas/administracion.py": {"motivo", "f'Respaldo de la clave: {motivo}'"},
}


def _formateado_seguro(valor: ast.FormattedValue) -> bool:
    """`{x:%Y-%m-%d}` y `{x:.2f}` no pueden inyectar marcado; `{x}` sí si `x` es ajeno."""
    return valor.format_spec is not None or _segura(valor.value)


def _segura(nodo: ast.AST) -> bool:
    """Una expresión de texto es segura si es literal o pasa por una función de `SEGURAS`."""
    if isinstance(nodo, ast.Constant):
        return True
    if isinstance(nodo, ast.Name):  # una constante del módulo, o un literal propio que se pasa
        return nodo.id.isupper() or nodo.id in LITERALES_PROPIOS
    if isinstance(nodo, ast.Attribute):  # la constante de otro módulo (`modulo.AVISO_FIJO`)
        return nodo.attr.isupper()
    if isinstance(nodo, ast.JoinedStr):
        return all(
            _formateado_seguro(v) if isinstance(v, ast.FormattedValue) else True
            for v in nodo.values
        )
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
        return _segura(nodo.left) and _segura(nodo.right)
    if isinstance(nodo, ast.Call):
        nombre = nodo.func.id if isinstance(nodo.func, ast.Name) else getattr(nodo.func, "attr", "")
        if nombre == "join":  # ", ".join(<generador>): seguro si lo es cada elemento
            argumento = nodo.args[0]
            elemento = getattr(argumento, "elt", argumento)
            return _segura(elemento)
        return nombre in SEGURAS
    if isinstance(nodo, ast.IfExp):
        return _segura(nodo.body) and _segura(nodo.orelse)
    return False


def _llamadas_de_texto(ruta: Path):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Attribute)
            and nodo.func.attr in LLAMADAS_DE_TEXTO
            and nodo.args
        ):
            yield nodo


@pytest.mark.parametrize("modulo", PAGINAS_CON_TEXTO_AJENO)
def test_todo_texto_que_llega_a_streamlit_es_literal_o_pasa_por_texto_seguro(modulo: str) -> None:
    sospechosas = [
        f"{modulo}:{n.lineno}: {ast.unparse(n.args[0])[:70]}"
        for n in _llamadas_de_texto(RAIZ / modulo)
        if not _segura(n.args[0]) and ast.unparse(n.args[0]) not in FIJAS_POR_MODULO.get(modulo, ())
    ]
    assert sospechosas == []


def test_la_regla_de_texto_ajeno_distingue_lo_seguro_de_lo_que_no(tmp_path: Path) -> None:
    def hallazgos(fuente: str) -> int:
        archivo = tmp_path / "x.py"
        archivo.write_text(fuente, encoding="utf-8")
        return sum(1 for n in _llamadas_de_texto(archivo) if not _segura(n.args[0]))

    assert hallazgos("st.info('fijo')\n") == 0
    assert hallazgos("st.info(f'hola {texto_seguro(nombre)}')\n") == 0
    assert hallazgos("st.info(f'hola {nombre}')\n") == 1
    assert hallazgos("st.error(str(error))\n") == 1
    assert hallazgos("st.error(texto_seguro(str(error)))\n") == 0
    assert hallazgos("st.caption('a ' + valor)\n") == 1
    assert hallazgos("st.caption(', '.join(texto_seguro(x) for x in xs))\n") == 0
    assert hallazgos("st.caption(', '.join(x for x in xs))\n") == 1
    assert hallazgos("st.caption(f'{fecha:%Y-%m-%d}')\n") == 0
    assert hallazgos("st.info(AVISO_FIJO)\n") == 0
    assert hallazgos("st.info(texto_libre)\n") == 1
    assert hallazgos("st.warning(modulo.AVISO_FIJO)\n") == 0
    assert hallazgos("st.warning(objeto.descripcion)\n") == 1


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
    ("ui/hoja.py", "guardar_edicion"),
    ("ui/hoja.py", "guardar_presupuesto"),
    ("ui/hoja.py", "restaurar_version"),
    ("ui/hoja.py", "cotizar_insumo"),
    ("ui/hoja.py", "_retirar_cotizacion"),
    ("ui/paginas/actualizacion.py", "actualizar_precios"),
    ("ui/paginas/hoja.py", "guardar_version"),
    ("ui/paginas/hoja.py", "crear_primera_version"),
    ("ui/paginas/hoja.py", "restaurar"),
    ("ui/paginas/hoja.py", "abrir_version"),
    ("ui/paginas/hoja.py", "cotizar"),
    ("ui/paginas/hoja.py", "retirar_cotizacion"),
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
    ("ui/hoja.py", "convertir_version"),
    ("ui/control.py", "aplicar_decision"),
    ("scripts/generar_obra_control.py", "guardar_presupuesto"),
}


def _llamadas_del_embudo():
    for carpeta in (
        "core",
        "ui",
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
