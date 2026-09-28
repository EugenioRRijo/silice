"""Las tres tablas de texto de la pantalla de componer, desde un `ComposicionAPU` (INV-052).

Es el camino de la pantalla: desarma una composicion en los diccionarios **de texto** que produce
`st.data_editor`, para darselos a `ui.composicion.composicion_desde_tablas` o sembrarlos en
`st.session_state`. Antes vivia en `tests/integration/test_composicion_extremo_a_extremo.py`, y
`tests/unit/test_ui_componer.py` lo importaba de ahi; lo compartido entre pruebas vive en
`tests/fixtures/` (regla A-6 del plan de C3).
"""

from __future__ import annotations

from decimal import Decimal

from core.contracts import ComposicionAPU


def texto_tecleado(valor: Decimal) -> str:
    """El `Decimal` tal como lo teclea una persona: notacion fija, sin exponente.

    `str(Decimal("1E+2"))` da `"1E+2"`, que ninguna pantalla muestra; `f"{...:f}"` fuerza la
    notacion posicional sin perder ni un digito ni la escala (`Decimal("1.00")` -> `"1.00"`).
    """
    return f"{valor:f}"


def filas_materiales(apu: ComposicionAPU) -> list[dict[str, str]]:
    return [
        {
            "descripcion": linea.descripcion,
            "unidad": linea.unidad,
            "cantidad": texto_tecleado(linea.cantidad),
            "precio": texto_tecleado(linea.precio),
        }
        for linea in apu.materiales
    ]


def filas_equipos(apu: ComposicionAPU) -> list[dict[str, str]]:
    return [
        {
            "descripcion": equipo.descripcion,
            "cantidad": texto_tecleado(equipo.cantidad),
            "precio": texto_tecleado(equipo.precio),
            "depreciacion": texto_tecleado(equipo.depreciacion),
        }
        for equipo in apu.equipos
    ]


def filas_mano_obra(apu: ComposicionAPU) -> list[dict[str, str]]:
    return [
        {
            "descripcion": obrero.descripcion,
            "cantidad": texto_tecleado(obrero.cantidad),
            "sueldo": texto_tecleado(obrero.sueldo),
            "modalidad": obrero.modalidad.value,
        }
        for obrero in apu.mano_obra
    ]
