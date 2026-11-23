"""Respaldo local fuera de OneDrive (plan del consejo, días 1-2).

Se prueba con un repositorio de git construido en una carpeta temporal: ningún dato real.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from scripts import respaldo_local as r


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    raiz = tmp_path / "TESIS"
    raiz.mkdir()
    _git(raiz, "init", "-q", "-b", "main")
    _git(raiz, "config", "user.email", "prueba@example.invalid")
    _git(raiz, "config", "user.name", "Prueba")
    (raiz / ".gitignore").write_text("node_modules/\n.venv/\n__pycache__/\n*.db\ndocs/auditoria/\n"
                                     ".worktrees/\n", encoding="utf-8")
    (raiz / "a.py").write_text("print('a')\n", encoding="utf-8")
    _git(raiz, "add", ".")
    _git(raiz, "commit", "-q", "-m", "inicio")
    # una rama que no está en ningún remoto
    _git(raiz, "branch", "feature/sin-subir")
    # lo que solo vive en el equipo: ignorado y no regenerable
    (raiz / "docs" / "auditoria").mkdir(parents=True)
    (raiz / "docs" / "auditoria" / "libro.xlsx").write_bytes(b"libro ficticio")
    (raiz / "apu.db").write_bytes(b"base")
    # lo regenerable: no se respalda
    (raiz / "node_modules" / "x").mkdir(parents=True)
    (raiz / "node_modules" / "x" / "i.js").write_text("//", encoding="utf-8")
    (raiz / ".venv").mkdir()
    (raiz / ".venv" / "pyvenv.cfg").write_text("x", encoding="utf-8")
    # trabajo sin commit en el árbol principal
    (raiz / "a.py").write_text("print('a cambiado')\n", encoding="utf-8")
    (raiz / "nuevo.md").write_text("sin commit\n", encoding="utf-8")
    return raiz


@pytest.fixture
def destino(tmp_path: Path) -> Path:
    return tmp_path / "RespaldoSilice"


def test_el_paquete_trae_todas_las_ramas_y_se_verifica(repo: Path, destino: Path):
    hecho = r.respaldar(repo, destino, prohibidas=(), sello="20261123-2000")
    paquete = hecho / "repositorio.bundle"
    assert paquete.exists()
    _git(repo, "bundle", "verify", str(paquete))
    cabezas = _git(repo, "bundle", "list-heads", str(paquete))
    assert "refs/heads/feature/sin-subir" in cabezas and "refs/heads/main" in cabezas


def test_el_trabajo_sin_commit_queda_como_parche_y_copia(repo: Path, destino: Path):
    hecho = r.respaldar(repo, destino, prohibidas=(), sello="20261123-2000")
    parche = (hecho / "sin-commit" / "principal.patch").read_text(encoding="utf-8")
    assert "a cambiado" in parche
    assert (hecho / "sin-commit" / "principal" / "nuevo.md").read_text(encoding="utf-8") == \
        "sin commit\n"


def test_los_ignorados_no_regenerables_se_copian_y_los_regenerables_no(repo: Path, destino: Path):
    hecho = r.respaldar(repo, destino, prohibidas=(), sello="20261123-2000")
    solo = hecho / "solo-en-el-equipo" / "principal"
    assert (solo / "docs" / "auditoria" / "libro.xlsx").read_bytes() == b"libro ficticio"
    assert (solo / "apu.db").exists()
    assert not (solo / "node_modules").exists()
    assert not (solo / ".venv").exists()


def test_los_arboles_de_trabajo_tambien(repo: Path, destino: Path):
    arbol = repo / ".worktrees" / "w1"
    _git(repo, "worktree", "add", "-q", str(arbol), "feature/sin-subir")
    (arbol / "a.py").write_text("print('en el arbol')\n", encoding="utf-8")
    hecho = r.respaldar(repo, destino, prohibidas=(), sello="20261123-2000")
    assert "en el arbol" in (hecho / "sin-commit" / "w1.patch").read_text(encoding="utf-8")
    # el árbol no se copia entero dentro de los ignorados del principal
    assert not (hecho / "solo-en-el-equipo" / "principal" / ".worktrees").exists()


def test_un_arbol_anidado_en_el_principal_respalda_sus_nuevos_y_sus_ignorados(repo: Path,
                                                                             destino: Path):
    # Los árboles viven dentro del principal (.worktrees/): eso no los excluye de sí mismos.
    arbol = repo / ".worktrees" / "w1"
    _git(repo, "worktree", "add", "-q", str(arbol), "feature/sin-subir")
    (arbol / "nota.md").write_text("nuevo en el arbol\n", encoding="utf-8")
    (arbol / "local.db").write_bytes(b"base del arbol")
    hecho = r.respaldar(repo, destino, prohibidas=(), sello="20261123-2000")
    assert (hecho / "sin-commit" / "w1" / "nota.md").read_text(encoding="utf-8") == \
        "nuevo en el arbol\n"
    assert (hecho / "solo-en-el-equipo" / "w1" / "local.db").read_bytes() == b"base del arbol"


def test_extras_fuera_del_repositorio(repo: Path, destino: Path, tmp_path: Path):
    memoria = tmp_path / "memoria"
    memoria.mkdir()
    (memoria / "MEMORY.md").write_text("índice", encoding="utf-8")
    hecho = r.respaldar(repo, destino, prohibidas=(), sello="20261123-2000",
                        extras={"memoria-claude": memoria})
    assert (hecho / "extras" / "memoria-claude" / "MEMORY.md").read_text(encoding="utf-8") == \
        "índice"


def test_un_extra_que_no_existe_se_anota_y_no_tumba_el_respaldo(repo: Path, destino: Path,
                                                               tmp_path: Path):
    hecho = r.respaldar(repo, destino, prohibidas=(), sello="20261123-2000",
                        extras={"no-esta": tmp_path / "no-existe"})
    assert "no-esta" in (hecho / "MANIFIESTO.txt").read_text(encoding="utf-8")


def test_el_manifiesto_lleva_el_sha256_de_cada_archivo(repo: Path, destino: Path):
    hecho = r.respaldar(repo, destino, prohibidas=(), sello="20261123-2000")
    lineas = (hecho / "MANIFIESTO.txt").read_text(encoding="utf-8").splitlines()
    libro = hecho / "solo-en-el-equipo" / "principal" / "docs" / "auditoria" / "libro.xlsx"
    esperado = hashlib.sha256(libro.read_bytes()).hexdigest()
    assert any(esperado in linea and "libro.xlsx" in linea for linea in lineas)
    assert r.verificar(hecho) == []


def test_verificar_detecta_un_archivo_alterado(repo: Path, destino: Path):
    hecho = r.respaldar(repo, destino, prohibidas=(), sello="20261123-2000")
    (hecho / "solo-en-el-equipo" / "principal" / "apu.db").write_bytes(b"otra cosa")
    assert r.verificar(hecho) == ["solo-en-el-equipo/principal/apu.db"]


def test_no_respalda_dentro_de_onedrive_ni_del_repositorio(repo: Path, tmp_path: Path):
    nube = tmp_path / "OneDrive"
    with pytest.raises(ValueError, match="OneDrive"):
        r.respaldar(repo, nube / "respaldo", prohibidas=(nube,), sello="x")
    with pytest.raises(ValueError, match="repositorio"):
        r.respaldar(repo, repo / "respaldo", prohibidas=(), sello="x")


def test_conserva_solo_los_ultimos(repo: Path, destino: Path):
    for sello in ("20261101-1000", "20261102-1000", "20261103-1000"):
        r.respaldar(repo, destino, prohibidas=(), sello=sello, conservar=2)
    assert sorted(p.name for p in destino.iterdir()) == ["20261102-1000", "20261103-1000"]


def test_no_pisa_un_respaldo_del_mismo_sello(repo: Path, destino: Path):
    r.respaldar(repo, destino, prohibidas=(), sello="20261123-2000")
    with pytest.raises(FileExistsError):
        r.respaldar(repo, destino, prohibidas=(), sello="20261123-2000")
