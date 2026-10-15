"""RF-82: el responsable es el usuario de la sesión, en toda columna `responsable` (S3 §3.2, §13.2).

Vigilancias: (1) la lista de toda columna `responsable` de los metadatos, cada una con la prueba
que dice que la escribe el usuario de la sesión (una columna nueva sin dueño hace fallar la lista);
(2) ninguna pantalla pide «Responsable» con un cuadro propio: todas pasan por
`ui.sesion.caja_de_responsable`; (3) el literal `"sistema"` aparece una sola vez en `ui/`
(`ui.hoja.RESPONSABLE_POR_OMISION`); (4) ningún llamador de `ui/` pasa como `responsable=` o
`usuario=` un texto fijo (salvo esa constante, de la transición RP8-4). Y el comportamiento de los
dos ayudantes de `ui.sesion` con el acceso encendido y apagado.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from migraciones.metadatos import METADATAS_CASO, METADATAS_INSTALACION
from ui import hoja
from ui import sesion as ui_sesion

RAIZ = Path(__file__).resolve().parents[2]

#: tabla -> «archivo::prueba» que demuestra que la escribe el usuario de la sesión. Las tablas de
#: S1 y S2 entran en cuanto existen en los metadatos; su prueba la agrega la tarea que cablea su
#: pantalla (`ui.sesion.caja_de_responsable`), siguiendo el patrón de `test_ui_hoja_responsable`.
_HOJA = "tests/unit/test_ui_hoja_responsable.py::test_guardar_registra_al_usuario"
_CAJA = "tests/unit/test_responsables.py::test_las_pantallas_de_s1_y_s2_usan_la_caja"
COBERTURA = {
    "registro_cambio": _HOJA,
    **dict.fromkeys(
        (
            "importacion_indice",
            "moneda_proyecto",
            "clausula_reajuste",
            "estudio_reajuste",
            "linea_base_control",
            "valuacion",
            "anulacion_valuacion",
            "costo_real",
            "decision_recuperacion",
        ),
        _CAJA,
    ),
}

#: Las tablas que nombra RF-82 en la ERS (docs/ERS.md, RF-82), copiadas a mano: la lista de los
#: metadatos no puede tener menos.
TABLAS_DE_RF82 = {
    "registro_cambio",
    "importacion_indice",
    "moneda_proyecto",
    "clausula_reajuste",
    "estudio_reajuste",
    "linea_base_control",
    "valuacion",
    "anulacion_valuacion",
    "costo_real",
    "decision_recuperacion",
}

#: Las pantallas de S1 y S2 que la bitácora de la 0.8.0 («S3-3, primer PR: tarea 18») dice que
#: piden el responsable con `ui.sesion.caja_de_responsable`.
PANTALLAS_CON_CAJA = (
    "ui/paginas/hoja.py",
    "ui/paginas/control.py",
    "ui/paginas/reajuste.py",
    "ui/paginas/indices.py",
)


def _tablas_con_responsable() -> set[str]:
    metadatas = (*METADATAS_CASO, *METADATAS_INSTALACION)
    return {
        tabla.name
        for metadata in metadatas
        for tabla in metadata.tables.values()
        if "responsable" in tabla.c
    }


def _archivos_de_ui() -> list[Path]:
    return sorted((RAIZ / "ui").rglob("*.py"))


def _donde(archivo: Path, nodo: ast.AST) -> str:
    """`ui/x.py:12`; fuera del repositorio (las autopruebas en `tmp_path`), solo el nombre."""
    nombre = archivo.relative_to(RAIZ).as_posix() if archivo.is_relative_to(RAIZ) else archivo.name
    return f"{nombre}:{nodo.lineno}"


# --- (1) toda columna `responsable` con su prueba ----------------------------------------------


def test_toda_columna_responsable_tiene_su_prueba() -> None:
    sin_dueno = sorted(_tablas_con_responsable() - set(COBERTURA))
    assert sin_dueno == [], f"columna `responsable` sin prueba en COBERTURA: {sin_dueno}"


def test_las_tablas_que_nombra_rf82_tienen_responsable_en_los_metadatos() -> None:
    assert TABLAS_DE_RF82 <= _tablas_con_responsable()
    assert set(COBERTURA) == TABLAS_DE_RF82


def test_las_pruebas_de_la_lista_existen() -> None:
    for tabla in sorted(_tablas_con_responsable()):
        archivo, _, prueba = COBERTURA[tabla].partition("::")
        ruta = RAIZ / archivo
        assert ruta.is_file(), f"{tabla}: no existe el archivo {archivo}"
        texto = ruta.read_text(encoding="utf-8")
        assert f"def {prueba}(" in texto, f"{tabla}: no existe {COBERTURA[tabla]}"


@pytest.mark.parametrize("tabla", sorted(COBERTURA))
def test_la_lista_no_nombra_tablas_que_no_son_de_responsable(tabla: str) -> None:
    """Una entrada de COBERTURA es una tabla con `responsable` o aún no existe en los metadatos."""
    todas = {t for m in (*METADATAS_CASO, *METADATAS_INSTALACION) for t in m.tables}
    assert tabla in _tablas_con_responsable() or tabla not in todas


# --- (2) ningún cuadro «Responsable» propio ------------------------------------------------------


def _rotulo(nodo: ast.Call) -> str | None:
    """El rótulo literal de un `text_input`/`text_area`: el primer argumento o `label=`."""
    candidatos = [*nodo.args[:1], *(k.value for k in nodo.keywords if k.arg == "label")]
    for valor in candidatos:
        if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
            return valor.value
    return None


def _cuadros_de_texto(archivo: Path):
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Attribute)
            and nodo.func.attr in ("text_input", "text_area")
            and _rotulo(nodo) is not None
        ):
            yield nodo


def _cuadros_de_responsable(archivo: Path) -> list[str]:
    return [
        _donde(archivo, nodo)
        for nodo in _cuadros_de_texto(archivo)
        if _rotulo(nodo).strip().lower().startswith("responsable")
    ]


def test_las_pantallas_de_s1_y_s2_usan_la_caja() -> None:
    """Ninguna pantalla de `ui/` pide «Responsable» con su propio `text_input` o `text_area`:
    todas pasan por `ui.sesion.caja_de_responsable` (que con el acceso encendido no es un
    cuadro). `ui/sesion.py` es la caja misma."""
    propios = sorted(
        donde
        for archivo in _archivos_de_ui()
        if archivo.name != "sesion.py"
        for donde in _cuadros_de_responsable(archivo)
    )
    assert propios == []


@pytest.mark.parametrize("pantalla", PANTALLAS_CON_CAJA)
def test_cada_pantalla_de_s1_y_s2_llama_a_la_caja(pantalla: str) -> None:
    """La vigilancia de arriba no pasa en vacío: las pantallas que guardan con responsable lo
    piden por la caja de la sesión."""
    arbol = ast.parse((RAIZ / pantalla).read_text(encoding="utf-8"))
    llamadas = [
        n
        for n in ast.walk(arbol)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "caja_de_responsable"
    ]
    assert llamadas, f"{pantalla} no llama a ui.sesion.caja_de_responsable"


def test_la_vigilancia_de_cuadros_propios_ve_el_cuadro(tmp_path: Path) -> None:
    archivo = tmp_path / "x.py"
    archivo.write_text(
        'st.text_input("Responsable ")\n'
        'st.text_input("Fuente")\n'
        'col.text_area(label="responsable del cambio")\n'
        'st.text_input("Quien responde")\n'
        "st.text_input(rotulo)\n",
        encoding="utf-8",
    )
    vistos = [n.lineno for n in _cuadros_de_texto(archivo)]
    assert vistos == [1, 2, 3, 4]  # el rótulo variable (línea 5) no se puede leer
    marcados = [
        n.lineno
        for n in _cuadros_de_texto(archivo)
        if _rotulo(n).strip().lower().startswith("responsable")
    ]
    assert marcados == [1, 3]


# --- (3) el literal «sistema» --------------------------------------------------------------------


def _literales_sistema() -> list[str]:
    return sorted(
        _donde(archivo, nodo)
        for archivo in _archivos_de_ui()
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8")))
        if isinstance(nodo, ast.Constant)
        and isinstance(nodo.value, str)
        and nodo.value.strip().lower() == "sistema"
    )


def test_el_literal_sistema_aparece_una_sola_vez_en_ui() -> None:
    donde = _literales_sistema()
    assert len(donde) == 1 and donde[0].startswith("ui/hoja.py:")
    linea = int(donde[0].split(":")[1])
    texto = (RAIZ / "ui/hoja.py").read_text(encoding="utf-8").splitlines()[linea - 1]
    assert texto.startswith("RESPONSABLE_POR_OMISION = ")
    assert hoja.RESPONSABLE_POR_OMISION == "sistema"


# --- (4) ningún responsable fijo en los llamadores de ui/ ---------------------------------------


def _es_texto_fijo(valor: ast.expr) -> bool:
    """Un literal de texto o una constante de módulo en MAYÚSCULAS (`NOMBRE` o `mod.NOMBRE`)."""
    if isinstance(valor, ast.Constant):
        return isinstance(valor.value, str)
    nombre = (
        valor.id
        if isinstance(valor, ast.Name)
        else valor.attr
        if isinstance(valor, ast.Attribute)
        else None
    )
    return nombre is not None and nombre.isupper()


def _responsables_fijos(archivo: Path) -> list[str]:
    salida = []
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if not isinstance(nodo, ast.Call):
            continue
        for k in nodo.keywords:
            if k.arg not in ("responsable", "usuario"):
                continue
            valores = k.value.values if isinstance(k.value, ast.BoolOp) else [k.value]
            permitido = isinstance(k.value, ast.BoolOp) and isinstance(k.value.op, ast.Or)
            fijos = [
                v
                for v in valores
                if _es_texto_fijo(v)
                # `quien() or hoja.RESPONSABLE_POR_OMISION`: la transición (RP8-4), permitida
                and not (
                    permitido
                    and v is valores[-1]
                    and isinstance(v, ast.Attribute)
                    and v.attr == "RESPONSABLE_POR_OMISION"
                )
            ]
            if fijos:
                salida.append(_donde(archivo, k.value))
    return salida


def test_ningun_llamador_de_ui_pasa_un_responsable_fijo() -> None:
    """RF-82: lo que `ui/` guarda lleva al usuario de la sesión, no un texto puesto en el código.
    Única excepción: el respaldo `... or hoja.RESPONSABLE_POR_OMISION` de la transición RP8-4.
    La caja «Responsable» no ve este camino (no hay cuadro): por eso se vigila aparte."""
    fijos = sorted(d for archivo in _archivos_de_ui() for d in _responsables_fijos(archivo))
    assert fijos == []


def test_la_vigilancia_de_responsables_fijos_ve_cada_forma(tmp_path: Path) -> None:
    archivo = tmp_path / "x.py"
    archivo.write_text(
        'f(responsable="sistema")\n'
        "f(responsable=RESPONSABLE_DE_LA_INTERFAZ)\n"
        "f(usuario=mod.USUARIO_FIJO)\n"
        "f(responsable=_responsable() or hoja.RESPONSABLE_POR_OMISION)\n"
        'f(responsable=_responsable() or "nadie")\n'
        "f(responsable=responsable)\n"
        "f(usuario=ui_sesion.responsable_actual())\n",
        encoding="utf-8",
    )
    lineas = sorted(int(d.rsplit(":", 1)[1]) for d in _responsables_fijos(archivo))
    assert lineas == [1, 2, 3, 5]


# --- los ayudantes de `ui.sesion` ---------------------------------------------------------------


class _Contenedor:
    """Doble de `st` o de una columna: anota lo que se le pide."""

    def __init__(self) -> None:
        self.llamadas: list[tuple] = []

    def caption(self, texto: str) -> None:
        self.llamadas.append(("caption", texto))

    def text_input(self, rotulo: str, key: str | None = None) -> str:
        self.llamadas.append(("text_input", rotulo, key))
        return "lo escrito a mano"


@pytest.fixture
def acceso_encendido(monkeypatch):
    monkeypatch.setenv(ui_sesion.VARIABLE_ACCESO, "1")
    monkeypatch.setattr(ui_sesion, "responsable_actual", lambda: "Ana Pérez <ana>")


@pytest.fixture
def acceso_apagado(monkeypatch):
    monkeypatch.setenv(ui_sesion.VARIABLE_ACCESO, "0")

    def _no_debe_llamarse() -> str:
        raise AssertionError("con el acceso apagado manda lo escrito")

    monkeypatch.setattr(ui_sesion, "responsable_actual", _no_debe_llamarse)


def test_con_el_acceso_encendido_el_responsable_es_la_sesion_diga_lo_que_diga_el_cuadro(
    acceso_encendido,
) -> None:
    assert ui_sesion.responsable_de_la_hoja("Otro Nombre") == "Ana Pérez <ana>"
    assert ui_sesion.responsable_de_la_hoja("") == "Ana Pérez <ana>"


def test_con_el_acceso_apagado_manda_lo_escrito(acceso_apagado) -> None:
    assert ui_sesion.responsable_de_la_hoja("Luis Gómez") == "Luis Gómez"
    assert ui_sesion.responsable_de_la_hoja("") == ""


def test_la_caja_con_el_acceso_encendido_no_es_un_cuadro(acceso_encendido) -> None:
    contenedor = _Contenedor()
    quien = ui_sesion.caja_de_responsable(
        "Responsable ", key="x_responsable", contenedor=contenedor
    )
    assert quien == "Ana Pérez <ana>"
    # «Ana Pérez <ana>» con `<` y `>` escapados para Markdown (RV-14)
    assert contenedor.llamadas == [("caption", "Responsable: Ana Pérez \\<ana\\>")]


def test_la_caja_con_el_acceso_apagado_es_el_cuadro_de_siempre(acceso_apagado) -> None:
    contenedor = _Contenedor()
    quien = ui_sesion.caja_de_responsable(
        "Responsable del cambio", key="x_responsable", contenedor=contenedor
    )
    assert quien == "lo escrito a mano"
    assert contenedor.llamadas == [("text_input", "Responsable del cambio", "x_responsable")]
