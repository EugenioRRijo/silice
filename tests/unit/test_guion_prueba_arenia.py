"""El guion manual no escribe en `data/apu.db` (INV‑065, bloqueante; spec de cierre §4).

Lee `docs/guion_prueba_arenia.md` como texto y comprueba cuatro cosas:

- toda orden de siembra lleva `--db` con una base propia **en la misma línea** que la orden: la
  comprobación es línea a línea, así que una orden partida con `--db` en la línea siguiente cuenta
  como orden sin base (el guion escribe cada orden en una sola línea);
- la preparación anota y comprueba la base de trabajo;
- la preparación ejecuta CP‑01…CP‑06 desde una copia desechable del repositorio (`git worktree
  add`/`remove`): hasta que la Tarea 12 de U1 llegue, la aplicación abre `data/apu.db` de la carpeta
  desde la que corre en el primer renderizado de cada página, antes de que se pueda escribir otra
  ruta, así que ni sembrar en `data/prueba_arenia.db` ni escribir el campo **Archivo SQLite**
  bastan por sí solos;
- la precondición de cada caso CP‑01…CP‑06 manda abrir la base de prueba en el campo
  **Archivo SQLite**, porque la aplicación vuelve a `data/apu.db` en cada recarga.

Cuando la Tarea 12 de U1 (fase C3, con `ARENIA_CASO` leído por `ui/caso.py`) reescriba esas
precondiciones podrá migrar la corrección a `ARENIA_CASO`, que esta prueba también acepta, y podrá
retirar la copia desechable, pero no volver en silencio a la ruta por defecto.

Límite conocido: esta prueba lee el texto del guion, no ejecuta la aplicación; comprueba que la
instrucción está escrita, no que quien la siga la respete.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
GUION = RAIZ / "docs" / "guion_prueba_arenia.md"
BASE_DE_PRUEBA = "data/prueba_arenia.db"
BASE_DE_TRABAJO = "data/apu.db"
CASO_ABIERTO = "ARENIA_CASO"
CREAR_COPIA_DESECHABLE = "git worktree add"
BORRAR_COPIA_DESECHABLE = "git worktree remove"

#: Los encabezados de los casos usan el guion no separable U+2011 («### CP‑01 — …»).
_ENCABEZADO_DE_CASO = re.compile(r"^### CP‑(0[1-7]) ", re.MULTILINE)


def _texto() -> str:
    return GUION.read_text(encoding="utf-8")


def _seccion(texto: str, inicio: str, fin: str) -> str:
    desde = texto.index(inicio)
    return texto[desde : texto.index(fin, desde)]


def _casos() -> dict[str, str]:
    """Texto de cada caso, de su encabezado al del caso siguiente (CP‑07 cierra a CP‑06)."""
    texto = _texto()
    marcas = list(_ENCABEZADO_DE_CASO.finditer(texto))
    return {
        f"CP-{marca.group(1)}": texto[marca.start() : siguiente.start()]
        for marca, siguiente in zip(marcas, marcas[1:], strict=False)
    }


def test_toda_orden_de_siembra_lleva_su_propia_base():
    ordenes = [
        linea.strip()
        for linea in _texto().splitlines()
        if "uv run python scripts/seed_demo.py" in linea
    ]
    assert ordenes, "el guion debe sembrar con scripts/seed_demo.py"
    sin_base = [orden for orden in ordenes if "--db" not in orden]
    assert not sin_base, f"sin --db apuntan a {BASE_DE_TRABAJO}: {sin_base}"
    assert not [orden for orden in ordenes if f"--db {BASE_DE_TRABAJO}" in orden]


def test_la_preparacion_anota_y_comprueba_la_base_de_trabajo():
    texto = _texto()
    preparacion = _seccion(texto, "## 4. Entorno y preparación", "## 5.")
    registro = _seccion(texto, "## 8. Registro de la ejecución", "## 9.")
    assert "**Antes de empezar" in preparacion
    assert "**Al terminar la prueba.**" in preparacion
    assert f"`{BASE_DE_TRABAJO}` al empezar" in registro
    assert f"`{BASE_DE_TRABAJO}` sin cambios al terminar" in registro


def test_la_preparacion_usa_una_copia_desechable_del_repositorio():
    """La app abre `data/apu.db` de la carpeta en el primer renderizado: solo una copia desechable
    del repositorio evita tocarlo, antes de que se pueda escribir otra ruta (INV‑065, ronda 1)."""
    preparacion = _seccion(_texto(), "## 4. Entorno y preparación", "## 5.")
    assert CREAR_COPIA_DESECHABLE in preparacion, (
        f"la preparacion debe crear una copia desechable con `{CREAR_COPIA_DESECHABLE}`"
    )
    assert BORRAR_COPIA_DESECHABLE in preparacion, (
        f"la preparacion debe borrar la copia desechable con `{BORRAR_COPIA_DESECHABLE}`"
    )


@pytest.mark.parametrize("caso", ["CP-01", "CP-02", "CP-03", "CP-04", "CP-05", "CP-06"])
def test_la_precondicion_de_cada_caso_abre_la_base_de_prueba(caso):
    precondicion = _seccion(_casos()[caso], "**Precondición:**", "**Pasos**")
    assert BASE_DE_PRUEBA in precondicion or CASO_ABIERTO in precondicion, (
        f"{caso}: la precondicion no abre {BASE_DE_PRUEBA}; la aplicacion volveria a "
        f"{BASE_DE_TRABAJO} (INV-065)"
    )


def test_la_segunda_pestana_de_cp02_tambien_abre_la_base_de_prueba():
    """La pestaña nueva empieza en la ruta por defecto: el paso 6 de CP‑02 la corrige."""
    pasos = _seccion(_casos()["CP-02"], "**Pasos**", "**Resultado esperado**")
    assert BASE_DE_PRUEBA in pasos or CASO_ABIERTO in pasos
