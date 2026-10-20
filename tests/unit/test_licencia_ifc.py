"""La licencia de `ifctester` y de `bcf-client` frente a la licencia propietaria del producto
(RP-6; spec S3 §11.2). El fallo de cualquiera de estas pruebas obliga a releer
`docs/licencias_ifc.md` antes de seguir: no se arregla cambiando la prueba."""

from __future__ import annotations

import ast
import tomllib
from importlib import metadata
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
DOCUMENTO = RAIZ / "docs" / "licencias_ifc.md"
CARPETAS_DE_PRODUCTO = (
    "adapters",
    "api",
    "auditoria",
    "core",
    "migraciones",
    "ml",
    "operacion",
    "paquete",
    "scripts",
    "seguridad",
    "ui",
)
#: Lo que de `ifctester` el producto NO puede importar: arrastra `bcf-client` (GPLv3).
PROHIBIDOS = ("bcf", "ifctester.reporter")


def _extras() -> dict[str, list[str]]:
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(texto)["project"]["optional-dependencies"]


def _importados(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module)
            nombres.update(f"{nodo.module}.{a.name}" for a in nodo.names)
    return nombres


def test_ifctester_solo_vive_en_el_extra_ifc_y_no_en_las_dependencias_base() -> None:
    proyecto = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert not any(r.startswith("ifctester") for r in proyecto["dependencies"])
    donde = [
        extra
        for extra, requisitos in _extras().items()
        if any(r.startswith("ifctester") for r in requisitos)
    ]
    assert donde == ["ifc"]


def test_el_producto_no_importa_bcf_ni_el_reporte_bcf_de_ifctester() -> None:
    encontrados = []
    for carpeta in CARPETAS_DE_PRODUCTO:
        for ruta in (RAIZ / carpeta).rglob("*.py"):
            for nombre in _importados(ruta):
                if any(nombre == p or nombre.startswith(p + ".") for p in PROHIBIDOS):
                    encontrados.append(f"{ruta.relative_to(RAIZ).as_posix()}: {nombre}")
    assert encontrados == []


def test_la_guardia_de_licencia_ve_las_formas_de_importar_bcf(tmp_path: Path) -> None:
    for fuente in (
        "import bcf\n",
        "from bcf.v2.bcfxml import BcfXml\n",
        "from ifctester.reporter import Bcf\n",
        "from ifctester import reporter\n",
    ):
        archivo = tmp_path / "x.py"
        archivo.write_text(fuente, encoding="utf-8")
        assert any(
            n == p or n.startswith(p + ".") for n in _importados(archivo) for p in PROHIBIDOS
        ), fuente
    archivo.write_text("from ifctester import ids\n", encoding="utf-8")
    assert not any(
        n == p or n.startswith(p + ".") for n in _importados(archivo) for p in PROHIBIDOS
    )


def _licencia(distribucion: str) -> str:
    datos = metadata.metadata(distribucion)
    clasificadores = [c for c in datos.get_all("Classifier", []) if c.startswith("License")]
    declarada = datos.get("License-Expression") or datos.get("License") or ""
    return " | ".join([declarada, *clasificadores])


def test_el_documento_de_licencias_dice_lo_que_dicen_las_distribuciones_instaladas() -> None:
    """Si una versión nueva cambia la licencia, la prueba falla y se vuelve a decidir."""
    texto = DOCUMENTO.read_text(encoding="utf-8")
    esperado = {
        "ifctester": ("LGPLv3+", "Lesser General Public License v3"),
        "bcf-client": ("GPLv3", "General Public License v3 (GPLv3)"),
    }
    for distribucion, (en_documento, en_metadatos) in esperado.items():
        assert f"{distribucion} {metadata.version(distribucion)}" in texto, distribucion
        assert en_documento in texto
        assert en_metadatos in _licencia(distribucion), distribucion


@pytest.mark.parametrize("distribucion", ["xmlschema", "shapely", "ezdxf"])
def test_los_demas_terceros_nuevos_de_s3_tienen_licencia_permisiva(distribucion: str) -> None:
    licencia = _licencia(distribucion)
    assert any(clave in licencia for clave in ("MIT", "BSD")), (distribucion, licencia)
