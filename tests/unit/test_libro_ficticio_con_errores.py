"""Libro ficticio con errores sembrados, para mostrar la auditoría y ensayar la medición.

El oráculo es el catálogo de la siembra: cada error sembrado declara la regla que debe
señalarlo, y la auditoría del libro tiene que traer un hallazgo de esa regla.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts import libro_ficticio_con_errores as f
from scripts import medir_auditoria_libro as m


@pytest.fixture
def fuera(tmp_path: Path) -> Path:
    carpeta = tmp_path / "ensayo"
    carpeta.mkdir()
    return carpeta


def test_cada_error_sembrado_lo_senala_su_regla(fuera: Path):
    from fusion.proceso import procesar_libro

    libro, _ = f.generar(fuera, raiz_repo=fuera.parent / "repo")
    hallazgos = procesar_libro(libro.read_bytes(), libro.name,
                               fecha_devolucion=date(2026, 11, 23)).informe.hallazgos
    reglas = {h.regla for h in hallazgos}
    faltan = [s.regla for s in f.SIEMBRAS if s.regla not in reglas]
    assert faltan == []
    assert len({s.regla for s in f.SIEMBRAS}) >= 8  # variedad: no siempre el mismo aviso


def test_la_clave_trae_una_fila_por_error_sembrado(fuera: Path):
    _, clave = f.generar(fuera, raiz_repo=fuera.parent / "repo")
    sembrados = m.leer_clave(clave)
    assert [s.numero for s in sembrados] == list(range(1, len(f.SIEMBRAS) + 1))
    assert all(s.tipo.startswith(e.regla) for s, e in zip(sembrados, f.SIEMBRAS, strict=True))


def test_no_escribe_dentro_del_repositorio(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="repositorio"):
        f.generar(repo, raiz_repo=repo)


def test_la_medicion_completa_corre_sobre_el_libro_ficticio(fuera: Path, capsys):
    libro, clave = f.generar(fuera, raiz_repo=fuera.parent / "repo")
    planilla = fuera / "planilla.xlsx"
    assert m.main(["exportar", str(libro), "--salida", str(planilla), "--fecha", "2026-11-23",
                   "--raiz-repo", str(fuera.parent / "repo")]) == 0
    base = fuera / "libro_ficticio_base.xlsx"  # el mismo libro sin sembrar, para los previos
    assert base.is_file()
    assert m.main(["calcular", "--planilla", str(planilla), "--clave", str(clave),
                   "--libro", str(libro), "--libro-base", str(base), "--fecha", "2026-11-23"]) == 0
    salida = capsys.readouterr().out
    assert "Detección de errores sembrados" in salida
    # por omisión se exporta por causa raíz: menos filas que hallazgos
    filas = m.leer_filas(planilla)
    assert sum(f.ocurrencias for f in filas) > len(filas)
    assert "hallazgos agrupados en" in salida


def test_no_crea_la_carpeta_si_el_destino_esta_dentro_del_repositorio(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    destino = repo / "datos_fuera_de_lugar"

    with pytest.raises(ValueError, match="repositorio"):
        f.main(["--salida", str(destino), "--raiz-repo", str(repo)])
    assert not destino.exists()


def test_crea_la_carpeta_de_salida_cuando_el_destino_es_seguro(tmp_path: Path):
    destino = tmp_path / "nueva" / "ensayo"
    libro, clave = f.generar(destino, raiz_repo=tmp_path / "repo")
    assert libro.is_file() and clave.is_file()
