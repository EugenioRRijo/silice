"""Todo modulo de `ui/` se importa sin construir objetos de Streamlit (spec de UI, §4 regla 3).

La lista ya no se escribe a mano: las paginas salen de `ui.app.PAGINAS`, de modo que una pagina
nueva queda cubierta sin tocar este archivo. Los modulos que no son pagina se nombran aparte.

INV-023: importar en el mismo proceso de pytest no afirmaba nada (un `st.title` suelto al importar
pasaba). La importacion corre en un proceso limpio, con `cwd` temporal, y se afirma la ausencia de
efectos: ni archivos creados ni llamadas a Streamlit sin runtime.
"""

from tests.fixtures.subproceso import importar_en_limpio
from ui.app import PAGINAS

MODULOS_SIN_PAGINA = (
    "ui.app",
    "ui.caso",
    "ui.recorridos",
    "ui.composicion",
    "ui.elaboracion",
    "ui.hoja",
    "ui.resultado",
)


def test_las_paginas_se_importan_sin_efectos(tmp_path):
    """Importar cada modulo de ui/ en un proceso limpio, con cwd temporal: no crea archivos ni
    llama a Streamlit fuera de `main()` (spec de UI, §4 regla 3)."""
    modulos = (*MODULOS_SIN_PAGINA, *(p.render.__module__ for p in PAGINAS))
    assert len(modulos) == len(MODULOS_SIN_PAGINA) + 11  # las once paginas del marco
    assert "ui.paginas.componer" in modulos  # meta P8 del prototipo (scripts/meta_prototipo.py)
    salida = importar_en_limpio(modulos, cwd=tmp_path)
    assert salida.returncode == 0, salida.stderr
    assert list(tmp_path.iterdir()) == []
    assert "ScriptRunContext" not in salida.stderr  # Streamlit llamado sin runtime
