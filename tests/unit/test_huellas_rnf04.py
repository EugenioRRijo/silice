"""Las dos huellas SHA‑256 que ancla RNF‑04 (`docs/protocolo_rnf04.md` §1), regresión del sprint
final (spec §2, meta S8).

El informe que juzgan los expertos es el de la fixture de siete inconsistencias, en sus dos formas:
la de pantalla (`informe_rnf04.md`) y la exportada (`informe_rnf04.xlsx`, cuya huella de contenido
excluye `docProps/core.xml`, que lleva la fecha). Las dos se generan con la misma orden del
protocolo. Si un cambio del sprint mueve alguna, esta prueba falla antes que Med: el cambio no se
re‑ancla aquí, se registra un ruling de reanclaje en la bitácora (spec §2, como el C6‑11).
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from core.budget import exportar_excel
from core.verification import auditar
from tests.fixtures.presupuesto_auditado import presupuesto_con_siete_inconsistencias

#: `docs/protocolo_rnf04.md` §1, punto 2 (GC5 y GC6, ruling C6‑11).
HUELLA_PANTALLA = "1d7ba8d6ae0f08b2ddc43b8d73c985915a2c0554001887745b6e23889077a840"
#: `docs/protocolo_rnf04.md` §1, punto 3, huella del contenido (GC5 y GC6).
HUELLA_CONTENIDO_LIBRO = "386bca1cb4a75868b5ac12fd0f637c02072c748b5a64fe16064c225bdd5b7748"


@pytest.fixture(scope="module")
def informe_rnf04(tmp_path_factory) -> tuple[Path, Path]:
    """Los dos archivos del protocolo, generados como lo hace su orden de la §1."""
    carpeta = tmp_path_factory.mktemp("rnf04")
    presupuesto = presupuesto_con_siete_inconsistencias()
    informe = auditar(presupuesto)
    libro = carpeta / "informe_rnf04.xlsx"
    exportar_excel(presupuesto, informe, libro)
    pantalla = carpeta / "informe_rnf04.md"
    pantalla.write_text(informe.a_markdown(), encoding="utf-8", newline="\n")
    return pantalla, libro


def test_huella_de_la_forma_de_pantalla(informe_rnf04):
    pantalla, _ = informe_rnf04
    assert hashlib.sha256(pantalla.read_bytes()).hexdigest() == HUELLA_PANTALLA


def test_huella_del_contenido_del_libro(informe_rnf04):
    _, libro = informe_rnf04
    huella = hashlib.sha256()
    with zipfile.ZipFile(libro) as archivo:
        for nombre in sorted(archivo.namelist()):
            if nombre != "docProps/core.xml":
                huella.update(nombre.encode() + archivo.read(nombre))
    assert huella.hexdigest() == HUELLA_CONTENIDO_LIBRO
