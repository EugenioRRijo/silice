"""El congelado del protocolo: huellas del banco, del protocolo y del auditor (S4 §9.1).

Todo ocurre en `tmp_path`: una copia de los archivos del auditor dentro de un repositorio git
propio (el congelado exige el arbol limpio, M5), nunca el repositorio real.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from asistente.experimento import congelado
from asistente.experimento.banco import CARPETA_TAREAS

LF = b"\n"
CRLF = b"\r\n"


def _git(raiz: Path, *argumentos: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=prueba",
            "-c",
            "user.email=prueba@example.com",
            "-c",
            "commit.gpgsign=false",
            *argumentos,
        ],
        cwd=raiz,
        check=True,
        capture_output=True,
    )


def _copia(tmp_path):
    raiz = tmp_path / "repo"
    protocolo = json.loads(congelado.PROTOCOLO.read_text(encoding="utf-8"))
    for ruta in protocolo["archivos_del_auditor"]:
        (raiz / ruta).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(congelado.RAIZ / ruta, raiz / ruta)
    # el arbol de la copia queda limpio y confirmado: `congelar` lo exige (M5)
    _git(raiz, "init", "-q")
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", "copia del auditor")
    tareas = tmp_path / "tareas"
    shutil.copytree(CARPETA_TAREAS, tareas)
    proto = tmp_path / "protocolo.json"
    shutil.copy(congelado.PROTOCOLO, proto)
    return {"protocolo": proto, "carpeta_tareas": tareas, "raiz": raiz}


def _con_saltos(archivos, saltos: bytes) -> None:
    """Reescribe cada archivo con LF o con CRLF, traiga el que traiga (core.autocrlf)."""
    for archivo in archivos:
        archivo.write_bytes(archivo.read_bytes().replace(CRLF, LF).replace(LF, saltos))


def test_sin_congelar_se_dice_y_congelado_no_hay_diferencias(tmp_path):
    rutas = _copia(tmp_path)
    destino = tmp_path / "congelado.json"
    assert "aun no esta congelado" in congelado.verificar(destino, **rutas)[0]
    huellas = congelado.congelar("abc1234", destino, **rutas)
    assert set(huellas) == {"banco", "protocolo", "auditor", "commit"}
    assert all(len(huellas[k]) == 64 for k in ("banco", "protocolo", "auditor"))
    assert congelado.verificar(destino, **rutas) == []


def test_tocar_una_regla_del_auditor_una_ficha_o_el_protocolo_se_detecta(tmp_path):
    rutas = _copia(tmp_path)
    destino = tmp_path / "congelado.json"
    congelado.congelar("abc1234", destino, **rutas)
    reglas = rutas["raiz"] / "adapters/espacio/reglas.py"
    reglas.write_text(reglas.read_text(encoding="utf-8") + "\n# ajuste\n", encoding="utf-8")
    assert congelado.verificar(destino, **rutas) == ["auditor cambio desde el congelado"]
    shutil.copy(congelado.RAIZ / "adapters/espacio/reglas.py", reglas)
    (rutas["carpeta_tareas"] / "dev-agua-01.json").write_text("{}", encoding="utf-8")
    rutas["protocolo"].write_text(rutas["protocolo"].read_text(encoding="utf-8") + " ", "utf-8")
    assert congelado.verificar(destino, **rutas) == [
        "banco cambio desde el congelado",
        "protocolo cambio desde el congelado",
    ]


def test_la_huella_es_la_misma_con_saltos_de_linea_de_windows_y_de_linux(tmp_path):
    rutas = _copia(tmp_path)
    destino = tmp_path / "congelado.json"
    archivos = [
        rutas["raiz"] / "adapters/espacio/reglas.py",
        rutas["protocolo"],
        *sorted(rutas["carpeta_tareas"].glob("*.json")),
    ]
    # se congela con LF (como en Linux), aunque el arbol de trabajo de Windows traiga CRLF...
    _con_saltos(archivos, LF)
    assert all(CRLF not in a.read_bytes() for a in archivos)
    _git(rutas["raiz"], "add", "-A")  # el arbol sigue limpio y confirmado (M5)
    _git(rutas["raiz"], "commit", "-q", "--allow-empty", "-m", "saltos LF")
    congelado.congelar("abc1234", destino, **rutas)
    # ...y se verifica con CRLF: ni el auditor, ni el banco, ni el protocolo cambian de huella
    _con_saltos(archivos, CRLF)
    assert all(CRLF in a.read_bytes() for a in archivos)
    assert congelado.verificar(destino, **rutas) == []


def test_congelar_con_cambios_sin_commit_se_niega_y_no_escribe_nada(tmp_path):
    rutas = _copia(tmp_path)
    destino = tmp_path / "congelado.json"
    reglas = rutas["raiz"] / "adapters/espacio/reglas.py"
    reglas.write_text(reglas.read_text(encoding="utf-8") + "\n# ajuste\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="arbol limpio"):
        congelado.congelar("abc1234", destino, **rutas)
    assert not destino.exists()


def test_un_archivo_del_auditor_que_falta_es_un_error(tmp_path):
    rutas = _copia(tmp_path)
    (rutas["raiz"] / "adapters/espacio/reglas.py").unlink()
    with pytest.raises(FileNotFoundError, match="reglas.py"):
        congelado.calcular(**rutas)
