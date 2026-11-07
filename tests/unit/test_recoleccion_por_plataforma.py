"""Las pruebas que necesitan pywebview solo se recolectan donde pywebview se instala (win32).

`pyproject.toml` declara `pywebview==6.2.1; sys_platform == 'win32'`. En Linux no existe el
paquete y la CI falla ante cualquier prueba omitida (`scripts/verificar_omitidas.py`), así que esas
pruebas no se omiten: no se recolectan (`collect_ignore` de `tests/unit/conftest.py`).
"""

from __future__ import annotations

from tests.unit.conftest import archivos_a_ignorar

ARCHIVO = "test_ventana_pywebview_real.py"


def test_en_linux_y_macos_no_se_recolectan_las_pruebas_de_pywebview_real() -> None:
    assert archivos_a_ignorar("linux") == [ARCHIVO]
    assert archivos_a_ignorar("darwin") == [ARCHIVO]


def test_en_windows_se_recolectan_todas() -> None:
    assert archivos_a_ignorar("win32") == []
