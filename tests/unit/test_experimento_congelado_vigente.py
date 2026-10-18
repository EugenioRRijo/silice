"""El protocolo del experimento sigue congelado sobre los archivos reales (RS-9, RF-141).

Eugenio decidió el 2026-10-18 (opción A) que el protocolo no se toca: el resultado E3 y E5 en
0/24 se informa como hipótesis previa falsada. Las mejoras del producto que el experimento no mide
(como R17) viven fuera de `archivos_del_auditor`. Esta prueba falla si alguien cambia uno de esos
archivos sin volver a congelar a propósito. Solo lee el repositorio; las pruebas de `congelado`
con archivos sembrados están en `test_experimento_congelado.py`.
"""

from __future__ import annotations

from asistente.experimento import congelado


def test_los_archivos_del_auditor_siguen_como_se_congelaron() -> None:
    assert congelado.verificar() == []
