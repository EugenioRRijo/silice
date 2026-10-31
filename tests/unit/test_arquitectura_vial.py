"""Reglas de arquitectura de la especialidad vial y de los módulos (plan vial, Tarea 19).

El núcleo (`core/`) es de todas las especialidades: no conoce `adapters.vial`, `produccion` ni
`aplicacion.riesgo`. Apagar un módulo se resuelve en la API y la aplicación, nunca dentro del
cálculo del núcleo. Ayudantes compartidos: `tests/fixtures/arquitectura.py`.
"""

from __future__ import annotations

import pytest

from tests.fixtures.arquitectura import archivos, importaciones, ruta

#: Lo que `core/` no puede importar: los módulos activables y sus paquetes.
PROHIBIDOS = ("adapters.vial", "produccion", "aplicacion.riesgo", "aplicacion.modulos")


def _es(modulo: str, prohibido: str) -> bool:
    return modulo == prohibido or modulo.startswith(prohibido + ".")


def test_la_guardia_ve_el_nucleo() -> None:
    assert archivos("core"), "la guardia no ve core/"


@pytest.mark.parametrize("archivo", archivos("core"), ids=ruta)
def test_el_nucleo_no_importa_los_modulos_activables(archivo) -> None:
    hallados = sorted(m for m in importaciones(archivo) if any(_es(m, p) for p in PROHIBIDOS))
    assert hallados == []


def test_un_modulo_activable_no_se_importa_a_si_mismo_desde_el_otro() -> None:
    """`produccion/` es dominio puro: tampoco conoce la API ni el estado de los módulos."""
    hallados = sorted(
        f"{ruta(a)}: {m}"
        for a in archivos("produccion")
        for m in importaciones(a)
        if _es(m, "aplicacion.modulos") or _es(m, "api")
    )
    assert hallados == []


def test_los_routers_de_los_tres_modulos_exigen_el_modulo() -> None:
    """Cada router de un módulo activable declara `requiere_modulo` (la API es la que corta)."""
    from api.rutas import produccion, produccion_planta, riesgo, vial

    for router, clave in (
        (produccion.router, "produccion"),
        (produccion_planta.router, "produccion"),
        (vial.router, "vial"),
        (riesgo.router, "riesgo"),
    ):
        nombres = [d.dependency.__name__ for d in router.dependencies]
        assert f"requiere_modulo_{clave}" in nombres, (clave, nombres)
