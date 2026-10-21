"""El producto se llama Sílice (plan 0.6.0, tarea A1; maestro S-D7 y P9).

En los documentos vigentes y en `ui/`, el nombre anterior solo sobrevive como nombre historico del
prototipo con la forma exacta de `NOMBRE_HISTORICO`; las variables viejas solo se nombran donde se
declaran como alias. La bitacora, la auditoria y los specs anteriores al 2026-10-11 no se tocan.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

VIGENTES: tuple[str, ...] = (
    "README.md",
    "docs/README.md",
    "docs/ERS.md",
    "docs/manual_usuario.md",
    "docs/manual_tecnico.md",
    "docs/guion_prueba_arenia.md",
    "docs/plan_pruebas.md",
    "docs/calidad_iso25010.md",
    "docs/protocolo_indicador3.md",
    "docs/protocolo_precios.md",
    "docs/protocolo_rnf04.md",
    "scripts/README.md",
    "scripts/seed_demo.py",
    "scripts/meta_prototipo.py",
    "api/main.py",
)
NOMBRE_HISTORICO = "AREN.IA (hoy Sílice)"
_NOMBRE_VIEJO = re.compile(r"AREN\.IA(?! \(hoy Sílice\))")
_VARIABLE_VIEJA = re.compile(r"ARENIA_(?:CASO|MODO_ENTREGA)")
PERMITEN_VARIABLE_VIEJA = frozenset(
    {"aplicacion/entorno.py", "docs/manual_usuario.md", "docs/manual_tecnico.md"}
)
LICENCIA = "Copyright (c) 2026 Eugenio Rijo. Todos los derechos reservados.\n"


def _archivos() -> list[str]:
    assert VIGENTES, "la guardia no recorre una lista vacia"
    return [*VIGENTES]


def _texto(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8")


def test_ningun_archivo_vigente_usa_el_nombre_viejo() -> None:
    encontrados = [
        f"{ruta}:{numero}"
        for ruta in _archivos()
        for numero, linea in enumerate(_texto(ruta).splitlines(), start=1)
        if _NOMBRE_VIEJO.search(linea)
    ]
    assert encontrados == [], f"use «Sílice» o, si es historia, «{NOMBRE_HISTORICO}»"


def test_las_variables_viejas_solo_se_nombran_como_alias() -> None:
    encontrados = [
        ruta
        for ruta in _archivos()
        if ruta not in PERMITEN_VARIABLE_VIEJA and _VARIABLE_VIEJA.search(_texto(ruta))
    ]
    assert encontrados == []


def test_los_manuales_anuncian_el_retiro_del_alias() -> None:
    for ruta in ("docs/manual_usuario.md", "docs/manual_tecnico.md"):
        texto = _texto(ruta)
        assert "SILICE_CASO" in texto and "ARENIA_CASO" in texto, ruta
        assert "ya no se aceptan desde la 0.7.0" in texto, ruta


def test_la_api_y_el_readme_se_llaman_silice() -> None:
    from api.main import app

    assert app.title == "Sílice"
    assert _texto("README.md").startswith("# Sílice\n")


def test_el_proyecto_se_llama_silice_y_es_propietario() -> None:
    proyecto = tomllib.loads(_texto("pyproject.toml"))["project"]
    assert proyecto["name"] == "silice"
    assert proyecto["license"] == "LicenseRef-Propietaria"
    assert proyecto["license-files"] == ["LICENSE"]
    assert _texto("LICENSE") == LICENCIA


def test_el_candado_lleva_el_nombre_nuevo() -> None:
    candado = _texto("uv.lock")
    assert 'name = "silice"' in candado
    assert 'name = "apu-system"' not in candado
