"""La puerta de entrada de los agentes externos (AGENTS.md, GEMINI.md, docs/ESTADO.md) no se pudre.

Antigravity, Codex y otros agentes leen `AGENTS.md` (o `GEMINI.md`) al abrir el repositorio. Si esos
archivos enlazan rutas que ya no existen, o si `docs/ESTADO.md` pierde su fecha, el agente vuelve a
leer planes viejos como si fueran el estado actual (el problema que los creo, 2026-11-04).
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

#: Enlaces Markdown relativos: [texto](ruta) sin esquema ni ancla sola.
_ENLACE = re.compile(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)")

ENTRADAS = ("AGENTS.md", "GEMINI.md", "docs/ESTADO.md")


def _enlaces(ruta: str) -> list[str]:
    texto = (RAIZ / ruta).read_text(encoding="utf-8")
    return [m.group(1).split("#", 1)[0] for m in _ENLACE.finditer(texto)]


def test_existen_las_tres_entradas() -> None:
    faltan = [r for r in ENTRADAS if not (RAIZ / r).is_file()]
    assert faltan == []


def test_todo_enlace_relativo_apunta_a_algo_que_existe() -> None:
    rotos = []
    for ruta in ENTRADAS:
        base = (RAIZ / ruta).parent
        for destino in _enlaces(ruta):
            if destino and not (base / destino).exists():
                rotos.append(f"{ruta} -> {destino}")
    assert rotos == []


def test_gemini_remite_a_agents() -> None:
    assert "AGENTS.md" in _enlaces("GEMINI.md")


def test_agents_manda_a_leer_primero_el_estado() -> None:
    assert "docs/ESTADO.md" in _enlaces("AGENTS.md")


def test_el_estado_declara_su_fecha() -> None:
    texto = (RAIZ / "docs/ESTADO.md").read_text(encoding="utf-8")
    assert re.search(r"^\*\*Actualizado:\*\* \d{4}-\d{2}-\d{2}", texto, re.MULTILINE)


def test_agents_declara_historicos_todos_los_planes_de_la_raiz() -> None:
    texto = (RAIZ / "AGENTS.md").read_text(encoding="utf-8")
    planes = sorted(p.name for p in RAIZ.glob("PLAN_*.md"))
    sin_declarar = [p for p in planes if p not in texto]
    assert sin_declarar == []
