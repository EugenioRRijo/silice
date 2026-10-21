"""RF-82: el responsable es el usuario de la sesión, en toda columna `responsable` (S3 §3.2, §13.2).

Vigilancias: (1) la lista de toda columna `responsable` de los metadatos, cada una con la prueba
que dice que la escribe el usuario de la sesión (una columna nueva sin dueño hace fallar la lista);
(2) el literal `"sistema"` aparece una sola vez en `ui/` (`ui.hoja.RESPONSABLE_POR_OMISION`);
(3) ningún llamador de `ui/` pasa como `responsable=` o `usuario=` un texto fijo (salvo esa
constante, de la transición RP8-4).

Retiro de Streamlit (F4): se fueron con las pantallas la vigilancia de los cuadros «Responsable»
propios, la de la caja `ui.sesion.caja_de_responsable` y las pruebas de los dos ayudantes de
`ui.sesion`. Las pruebas que demuestran que cada tabla escribe al usuario de la sesión son ahora
las de la API (`COBERTURA`).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from aplicacion import hoja
from migraciones.metadatos import METADATAS_CASO, METADATAS_INSTALACION

RAIZ = Path(__file__).resolve().parents[2]


#: tabla -> «archivo::prueba» que demuestra que la escribe el usuario de la sesión (rutas de la API:
#: el responsable sale de la sesión y el cuerpo no puede decir otro). Tras el retiro de Streamlit,
#: `linea_base_control`, `anulacion_valuacion` y `costo_real` quedan apuntadas a la prueba de la
#: valuación de la misma ruta (`api/rutas/control.py` usa `_responsable(activa)` en las tres): no
#: hay una prueba propia de cada una.
def _api(archivo: str, prueba: str) -> str:
    return f"tests/unit/{archivo}::{prueba}"


_HOJA = _api(
    "test_api_hoja_guardado.py",
    "test_el_responsable_de_lo_guardado_es_quien_tiene_la_sesion",
)
_INDICES = _api(
    "test_api_indices.py",
    "test_confirmar_un_csv_guarda_los_valores_exactos_y_repetirlo_no_escribe",
)
_MONEDA = _api(
    "test_api_hoja_conversion_cadena.py",
    "test_convertir_a_bs_crea_la_002_con_la_tasa_de_venta_y_el_total_de_la_memoria_por_la_tasa",
)
_REAJUSTE = _api(
    "test_api_reajuste.py",
    "test_guardar_sin_responsable_usa_la_sesion",
)
_CONTROL = _api(
    "test_api_control.py",
    "test_registrar_una_valuacion_controla_al_corte_y_el_responsable_sale_de_la_sesion",
)
_DECISION = _api(
    "test_api_control.py",
    "test_elegir_una_opcion_crea_la_version_y_deja_la_decision_con_el_responsable_de_la_sesion",
)
COBERTURA = {
    "registro_cambio": _HOJA,
    "importacion_indice": _INDICES,
    "moneda_proyecto": _MONEDA,
    "clausula_reajuste": _REAJUSTE,
    "estudio_reajuste": _REAJUSTE,
    "linea_base_control": _CONTROL,
    "valuacion": _CONTROL,
    "anulacion_valuacion": _CONTROL,
    "costo_real": _CONTROL,
    "decision_recuperacion": _DECISION,
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


# --- (2) el literal «sistema» --------------------------------------------------------------------


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


# --- (3) ningún responsable fijo en los llamadores de ui/ ---------------------------------------


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
