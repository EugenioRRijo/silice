"""El guion de CP‑08 a CP‑11 y RNF‑13 está escrito completo (integración final del sprint SF).

Lee `docs/guion_prueba_arenia.md` y `docs/protocolo_indicador3.md` como texto. Comprueba que cada
caso es un caso IEEE 829 completo (objetivo, trazabilidad, precondición, pasos, resultado esperado y
tabla de veredicto), que usa la base propia `data/prueba_sf.db` y nunca `data/apu.db`, que CP‑10 va
antes que CP‑11, que el paso negativo de guardar sin fuente está, y que RNF‑13 declara consigna
literal, paradas, criterio, n y exclusión de las personas de CP‑07. Límite: lee texto; no ejecuta
la aplicación.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
GUION = RAIZ / "docs" / "guion_prueba_arenia.md"
PROTOCOLO_I3 = RAIZ / "docs" / "protocolo_indicador3.md"
CASOS = ("CP‑08", "CP‑09", "CP‑10", "CP‑11")
_ENCABEZADO = re.compile(r"^###? (CP‑(?:0[7-9]|1[01])|6\.1) ", re.MULTILINE)


def _texto() -> str:
    return GUION.read_text(encoding="utf-8")


def _caso(codigo: str) -> str:
    texto = _texto()
    marcas = list(_ENCABEZADO.finditer(texto))
    for marca, siguiente in zip(marcas, [*marcas[1:], None], strict=True):
        if marca.group(1) == codigo:
            return texto[marca.start() : siguiente.start() if siguiente else len(texto)]
    raise AssertionError(f"{codigo} no esta en el guion")


@pytest.mark.parametrize("codigo", CASOS)
def test_cada_caso_es_un_caso_ieee_829_completo(codigo):
    caso = _caso(codigo)
    for parte in (
        "**Objetivo:**",
        "**Trazabilidad:**",
        "**Precondición:**",
        "**Pasos**",
        "**Resultado esperado**",
        "| Resultado obtenido | Veredicto |",
    ):
        assert parte in caso, (codigo, parte)
    pasos = caso[caso.index("**Pasos**") : caso.index("**Resultado esperado**")]
    assert len(re.findall(r"^\d+\. ", pasos, re.MULTILINE)) >= 5, codigo


@pytest.mark.parametrize("codigo", CASOS)
def test_cada_caso_traza_a_su_uc_y_a_rnf_13(codigo):
    traza = re.search(r"\*\*Trazabilidad:\*\* ([^\n]+)", _caso(codigo)).group(1)
    assert re.search(r"UC‑1[3-6]", traza) and "RNF‑13" in traza, codigo


def test_la_trazabilidad_de_la_spec_se_cumple_por_caso():
    esperado = {
        "CP‑08": ("UC‑13", "RF‑44 a RF‑47", "RF‑61"),
        "CP‑09": ("UC‑14", "RF‑50"),
        "CP‑10": ("UC‑15", "UC‑16", "RF‑52", "RF‑53", "RF‑55", "RF‑58"),
        "CP‑11": ("UC‑15", "RF‑56", "RF‑59"),
    }
    for codigo, partes in esperado.items():
        traza = re.search(r"\*\*Trazabilidad:\*\* ([^\n]+)", _caso(codigo)).group(1)
        for parte in partes:
            assert parte in traza, (codigo, parte)


def test_la_base_propia_es_prueba_sf_y_ninguna_orden_usa_la_de_trabajo():
    texto = _texto()
    assert "scripts/seed_of001.py --db data/prueba_sf.db --reiniciar" in texto
    assert "ARENIA_CASO=data/prueba_sf.db" in texto
    ordenes = [
        linea
        for linea in texto.splitlines()
        if "seed_of001.py" in linea and linea.lstrip().startswith("uv run")
    ]
    assert ordenes and all("--db data/prueba_sf.db" in linea for linea in ordenes)
    for linea in texto.splitlines():
        if "uv run" in linea or "ARENIA_CASO" in linea:
            assert "ARENIA_CASO=data/apu.db" not in linea and "--db data/apu.db" not in linea


def test_cp_10_va_antes_que_cp_11_y_cp_11_lo_dice():
    texto = _texto()
    assert texto.index("### CP‑10 ") < texto.index("### CP‑11 ")
    assert "CP‑10 se ejecuta antes que CP‑11" in _caso("CP‑10")
    assert "CP‑10 terminado con PASA" in _caso("CP‑11")


def test_cp_10_tiene_el_paso_negativo_de_guardar_sin_fuente():
    caso = " ".join(_caso("CP‑10").split())  # el guion parte las lineas
    assert "sin escribir nada" in caso and "deshabilitado" in caso
    assert "Escriba la fuente del cambio" in caso  # el texto que el sistema da


def test_cp_09_declara_que_el_dxf_trae_varias_marcas_y_que_se_resuelve():
    caso = _caso("CP‑09")
    assert "Nota de alcance" in caso and "varias" in caso
    assert "Pendiente 0" in caso and "2577.59" in caso


def test_cp_07_se_actualizo_a_la_barra_superior_sin_tocar_su_criterio():
    texto = _texto()
    cp07 = _caso("CP‑07")
    assert "menú de pantallas está **arriba**" in cp07
    assert "barra de herramientas" in cp07 and "hoja_<código>.xlsx" in cp07
    assert "menú lateral" not in texto  # el menu ya no es lateral en ninguna parte
    assert "Se cumplen **20 minutos**" in cp07  # el umbral de CP‑07 no cambio
    assert "**≥ 4,0 sin ningún ítem por debajo de 3**" in cp07


def test_rnf_13_declara_consigna_paradas_criterio_n_y_exclusion():
    seccion = _caso("6.1")
    for codigo in CASOS:
        assert re.search(rf"\*\*{codigo}\.\*\* «", seccion), codigo  # consigna literal por caso
    for parte in (
        "**n = 2**",
        "Personas distintas",
        "CP‑07",
        "indicador 3",
        "RNF‑04",
        "**15 minutos**",
        "**5 minutos sin una acción nueva**",
        "Oferta única de ayuda",
        "≥ 4,0 sin ningún ítem por debajo de 3",
        "CP‑10 antes que CP‑11",
        "veredicto es **por caso**",
    ):
        assert parte in seccion, parte


def test_rnf_13_fija_el_estado_final_de_cada_caso():
    seccion = _caso("6.1")
    for cifra in ("172.42", "2577.59", "2.26", "Día 23", "hoja_003.xlsx"):
        assert cifra in seccion, cifra


def test_la_trazabilidad_cp_uc_rf_incluye_los_cuatro_casos():
    texto = _texto()
    tabla = texto[texto.index("## 7. Trazabilidad CP → UC / RF") :]
    for codigo in CASOS:
        assert f"| {codigo} |" in tabla, codigo


def test_el_protocolo_del_indicador_3_dice_donde_esta_elaborar_ahora():
    texto = PROTOCOLO_I3.read_text(encoding="utf-8")
    assert "menú superior" in texto
    assert "hoja_<código>.xlsx" in texto
    # el metodo y los umbrales no cambian: las cifras de la prueba siguen donde estaban
    assert "90 minutos en la condición manual y 45 con el sistema" in texto
    assert "Wilcoxon de rangos con signo" in texto
