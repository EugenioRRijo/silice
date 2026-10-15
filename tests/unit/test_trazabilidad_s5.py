"""Cada prueba que plan_pruebas §8.3 cita para RF-97 a RF-99 y RNF-19 existe (S5-TRAZ; T19).

La prueba del plan que usa `scripts.meta_silice_s5b._traz` no se escribe: la parte S5 de la meta
(T18) no está construida. Aquí se lee §8.3 directamente. Mientras la auditoría pasa las citas a
`archivo::prueba`, §8.3 admite también la forma «`archivo` › `prueba`» (bitácora S5-0 · T1, (5)).
Las citas de código no construido (T3 `operacion.firma_sumas`, T20 `instalador/publicar.py`) se
exigen en cuanto ese código exista.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
#: prueba citada -> código del que depende; si el código no existe, la prueba tampoco puede
NO_CONSTRUIDO = {
    "tests/unit/test_firma_sumas.py": "operacion/firma_sumas.py",
    "tests/unit/test_publicar.py": "instalador/publicar.py",
}
CITA = re.compile(r"`(tests/[\w/]+\.py)`\s*›\s*`(\w+)`|`(tests/[\w/]+\.py)::(\w+)`")


def _seccion_8_3() -> str:
    texto = (RAIZ / "docs" / "plan_pruebas.md").read_text(encoding="utf-8").replace("‑", "-")
    return texto.split("### 8.3", 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0]


def _citas(texto: str) -> list[tuple[str, str]]:
    return [(m[0] or m[2], m[1] or m[3]) for m in CITA.findall(texto)]


def test_la_lectura_de_citas_entiende_las_dos_formas() -> None:
    texto = "- **RF-1** `tests/unit/a.py` › `test_x`,\n  `tests/integration/b.py::test_y`."
    assert _citas(texto) == [("tests/unit/a.py", "test_x"), ("tests/integration/b.py", "test_y")]


def test_cada_requisito_de_la_1_0_0_tiene_al_menos_una_prueba_citada() -> None:
    vinetas = re.split(r"\n(?=- \*\*)", _seccion_8_3())
    for requisito in ("RF-97", "RF-98", "RF-99", "RNF-19", "RNF-20"):
        texto_del_requisito = next(
            v for v in vinetas if v.lstrip("- ").startswith(f"**{requisito}")
        )
        assert "`tests/" in texto_del_requisito or "humo.ps1" in texto_del_requisito, requisito


def test_la_trazabilidad_de_la_1_0_0_cita_pruebas_que_existen() -> None:
    citas = _citas(_seccion_8_3())
    assert len(citas) >= 30  # RF-97 (8), RF-98 (15), RF-99 (3), RNF-19 (2), RNF-20 (3), firma
    faltan = []
    for archivo, prueba in citas:
        codigo = NO_CONSTRUIDO.get(archivo)
        if codigo is not None and not (RAIZ / codigo).is_file():
            continue  # T3 o T20 sin construir: no aplica todavía
        ruta = RAIZ / archivo
        if not ruta.is_file() or f"def {prueba}(" not in ruta.read_text(encoding="utf-8"):
            faltan.append(f"{archivo}::{prueba}")
    assert faltan == []


def test_las_citas_del_instalador_son_de_este_paquete_de_pruebas() -> None:
    """Las que cubren RF-97 y RNF-19 desde el instalador están en los archivos de esta auditoría."""
    citas = set(_citas(_seccion_8_3()))
    for esperada in (
        ("tests/unit/test_manifiesto.py", "test_nunca_viajan_fixtures_bcv_bases_ni_db"),
        ("tests/unit/test_iss.py", "test_el_iss_instala_por_usuario_y_con_el_appid_fijo"),
        ("tests/unit/test_construir.py", "test_el_manifiesto_json_cubre_codigo_y_python"),
        ("tests/unit/test_tamanos.py", "test_el_limite_es_exacto"),
        ("tests/unit/test_medir_arranque.py", "test_resumen_calcula_la_mediana_de_cinco"),
    ):
        assert esperada in citas, esperada
