"""El instalador lleva la interfaz nueva ya compilada (Task 2.7; RF-112, RNF-19).

El `dist` lo compila la CI con Node (`npm ci && npm run build`); Python solo lo copia. Aquí no se
compila nada ni se construye el instalador: el `dist` es falso y vive en `tmp_path`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from instalador import construir as c
from instalador import manifiesto as mf

RAIZ = Path(__file__).resolve().parents[2]


def _dist_falso(raiz: Path) -> Path:
    dist = raiz / "frontend-desktop" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    return dist


def test_el_manifiesto_declara_el_dist_de_la_interfaz() -> None:
    assert mf.cargar().interfaz_dist == "frontend-desktop/dist"


def test_un_manifiesto_sin_interfaz_es_invalido(tmp_path: Path) -> None:
    texto = mf.RUTA_MANIFIESTO.read_text(encoding="utf-8")
    roto = tmp_path / "roto.toml"
    roto.write_text(texto.replace("[interfaz]", "[otra]"), encoding="utf-8")
    with pytest.raises(mf.ManifiestoInvalido, match="falta la clave"):
        mf.cargar(roto)


def test_copiar_interfaz_deja_el_dist_donde_api_interfaz_lo_busca(tmp_path: Path) -> None:
    origen, destino = tmp_path / "repo", tmp_path / "app" / "codigo"
    _dist_falso(origen)
    copiados = mf.copiar_interfaz(origen, destino, mf.cargar())
    # `api/interfaz.py` sirve RAIZ / "frontend-desktop" / "dist"; en el producto RAIZ = {app}\codigo
    assert (destino / "frontend-desktop" / "dist" / "index.html").is_file()
    assert (destino / "frontend-desktop" / "dist" / "assets" / "app.js").is_file()
    assert sorted(p.as_posix() for p in copiados) == [
        "frontend-desktop/dist/assets/app.js",
        "frontend-desktop/dist/index.html",
    ]


def test_sin_dist_la_construccion_falla_y_dice_como_compilarlo(tmp_path: Path) -> None:
    with pytest.raises(mf.ManifiestoInvalido, match=r"npm ci && npm run build"):
        mf.copiar_interfaz(tmp_path, tmp_path / "codigo", mf.cargar())


def test_un_dist_vacio_tambien_falla(tmp_path: Path) -> None:
    (tmp_path / "frontend-desktop" / "dist").mkdir(parents=True)
    with pytest.raises(mf.ManifiestoInvalido, match="frontend-desktop"):
        mf.copiar_interfaz(tmp_path, tmp_path / "codigo", mf.cargar())


def test_un_dist_sin_index_html_falla(tmp_path: Path) -> None:
    dist = tmp_path / "frontend-desktop" / "dist"
    dist.mkdir(parents=True)
    (dist / "otra.js").write_text("x", encoding="utf-8")
    with pytest.raises(mf.ManifiestoInvalido, match="index.html"):
        mf.copiar_interfaz(tmp_path, tmp_path / "codigo", mf.cargar())


def test_copiar_codigo_copia_tambien_la_interfaz(tmp_path: Path, monkeypatch) -> None:
    repo, destino = tmp_path / "repo", tmp_path / "app" / "codigo"
    _dist_falso(repo)
    monkeypatch.setattr(c, "RAIZ", repo)
    monkeypatch.setattr(mf, "armar_arbol", lambda *a, **k: [])  # el código real no es el tema
    c.copiar_codigo(mf.cargar(), destino)
    assert (destino / "frontend-desktop" / "dist" / "index.html").is_file()


def test_copiar_codigo_sin_dist_falla(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(c, "RAIZ", tmp_path)
    monkeypatch.setattr(mf, "armar_arbol", lambda *a, **k: [])
    with pytest.raises(mf.ManifiestoInvalido, match="npm run build"):
        c.copiar_codigo(mf.cargar(), tmp_path / "codigo")


def test_el_flujo_compila_la_interfaz_con_node_22_antes_de_construir() -> None:
    flujo = yaml.safe_load((RAIZ / ".github" / "workflows" / "instalador.yml").read_text("utf-8"))
    pasos = flujo["jobs"]["construir"]["steps"]
    nodos = [
        i for i, p in enumerate(pasos) if str(p.get("uses", "")).startswith("actions/setup-node")
    ]
    assert len(nodos) == 1
    assert pasos[nodos[0]]["uses"] == "actions/setup-node@v6.5.0"
    assert str(pasos[nodos[0]]["with"]["node-version"]) == "22"
    ordenes = [str(p.get("run", "")) for p in pasos]
    ci = next(i for i, o in enumerate(ordenes) if "npm ci" in o)
    build = next(i for i, o in enumerate(ordenes) if "npm run build" in o)
    construir = next(i for i, o in enumerate(ordenes) if "instalador/construir.py" in o)
    assert nodos[0] < ci < build < construir
    assert pasos[ci]["working-directory"] == "frontend-desktop"
    assert pasos[build]["working-directory"] == "frontend-desktop"
    # el disparador de PR vigila la interfaz
    assert "frontend-desktop/**" in flujo[True]["pull_request"]["paths"]
