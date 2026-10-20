"""Sesion 4 de la ruta (historial): la ERS, el modelo de datos y el plan de pruebas definen lo
que se construye.

La ERS escribe los codigos con el guion no separable U+2011 (`RF‑142`); la prueba lo normaliza para
no depender de como se teclee.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
GUION_NO_SEPARABLE = "‑"

CODIGOS_HISTORIAL = ("UC-30", *(f"RF-{n}" for n in range(142, 147)), "RNF-28")
COLUMNAS = (
    "fecha_hora",
    "usuario",
    "tipo",
    "nombre_archivo",
    "sha256",
    "fecha_libro",
    "total_libro",
    "total_silice",
    "errores",
    "advertencias",
    "informativos",
    "atipicos",
    "recortado",
    "hallazgos",
)


def _texto(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8").replace(GUION_NO_SEPARABLE, "-")


@pytest.mark.parametrize("codigo", CODIGOS_HISTORIAL)
def test_la_ers_define_los_requisitos_del_historial(codigo):
    assert codigo in _texto("docs/ERS.md")


def test_la_ers_ya_no_dice_que_uc_25_no_guarda_nada():
    ers = _texto("docs/ERS.md")
    inicio = ers.index("#### UC-25")
    fin = ers.index("## Enmienda Sílice 1.1.0")
    seccion = ers[inicio:fin]
    assert "nada se guarda en la base ni en disco (F-D9)" not in seccion
    assert "el libro y el PDF no se guardan" in seccion
    assert "enmienda del historial" in seccion


def test_la_ers_traza_el_historial():
    ers = _texto("docs/ERS.md")
    assert "UC-30 → RF-142" in ers
    assert "UC-25 → RF-142" in ers


def test_la_ers_no_repite_ningun_codigo_nuevo_como_definicion():
    """Cada codigo nuevo se define una sola vez (en su tabla); las demas apariciones lo citan."""
    ers = _texto("docs/ERS.md")
    for codigo in CODIGOS_HISTORIAL[1:]:
        assert ers.count(f"| {codigo} |") == 1, codigo


def test_el_modelo_de_datos_documenta_la_tabla_y_sus_columnas():
    modelo = _texto("docs/modelo_datos.md")
    assert "auditoria_libro" in modelo and "ins_0003_auditoria_libro" in modelo
    for columna in COLUMNAS:
        assert f"`{columna}`" in modelo, columna


def test_el_plan_de_pruebas_nombra_las_pruebas_del_historial():
    plan = _texto("docs/plan_pruebas.md")
    for prueba in (
        "test_migracion_auditoria_libro.py",
        "test_historial_auditorias.py",
        "test_api_auditorias_libro.py",
    ):
        assert prueba in plan, prueba


def test_el_plan_de_la_sesion_deja_el_parche_para_libros():
    plan = _texto("docs/planes/PLAN_SESION_4_HISTORIAL.md")
    assert "registrar_auditoria" in plan and "RM-6" in plan
    assert "api/rutas/libros.py" in plan
