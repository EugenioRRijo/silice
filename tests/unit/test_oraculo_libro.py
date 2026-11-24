"""Herramienta local `scripts/oraculo_libro.py` (Fase 1)."""

from __future__ import annotations

import io
import json
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest

from scripts import oraculo_libro as ol
from tests.fixtures.libros_empresa import libro_limpio


class _LibreOfficeFalso:
    """Doble de prueba sin LibreOffice real para ejercitar la CLI de punta a punta."""

    def __init__(self, cambios: dict[str, object] | None = None) -> None:
        self._cambios = dict(cambios or {})

    def version(self) -> str:
        return "LibreOffice 24.8.3.2 (falso)"

    def recalcular(self, datos: bytes, nombre: str) -> bytes:
        origen = openpyxl.load_workbook(
            io.BytesIO(datos), read_only=True, data_only=True, keep_links=False
        )
        nuevo = openpyxl.Workbook()
        nuevo.remove(nuevo.active)
        try:
            for ws_orig in origen.worksheets:
                ws_nueva = nuevo.create_sheet(ws_orig.title)
                for fila_idx, fila in enumerate(ws_orig.iter_rows(values_only=True), start=1):
                    for col_idx, valor in enumerate(fila, start=1):
                        if valor is not None:
                            ws_nueva.cell(row=fila_idx, column=col_idx, value=valor)
        finally:
            origen.close()
        for clave_celda, nuevo_valor in self._cambios.items():
            hoja, coord = clave_celda.split("!", 1)
            nuevo[hoja][coord] = nuevo_valor
        buf = io.BytesIO()
        nuevo.save(buf)
        nuevo.close()
        return buf.getvalue()


def test_se_niega_a_escribir_dentro_del_repositorio(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    libro = tmp_path / "entrada.xlsx"
    libro.write_bytes(libro_limpio().datos)
    with pytest.raises(ValueError, match="repositorio"):
        ol.main([str(libro), "--salida", str(repo / "sub"), "--raiz-repo", str(repo)])
    with pytest.raises(ValueError, match="repositorio"):
        ol.main([str(libro), "--salida", str(ol.RAIZ / "docs")])


def test_no_sobrescribe_informe_existente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ol, "RecalculadorLibreOffice", lambda *_a, **_k: _LibreOfficeFalso())
    libro = tmp_path / "ensayo.xlsx"
    libro.write_bytes(libro_limpio().datos)
    salida = tmp_path / "fuera"
    assert ol.main([str(libro), "--salida", str(salida), "--raiz-repo", str(tmp_path / "r")]) == 0
    with pytest.raises(FileExistsError):
        ol.main([str(libro), "--salida", str(salida), "--raiz-repo", str(tmp_path / "r")])


def test_escribe_json_sin_descripciones_y_resumen_con_coma_decimal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    construido = libro_limpio()
    fila_p1 = construido.filas_partida["APU-01"]
    falso = _LibreOfficeFalso({f"PRESUPUESTO!P{fila_p1}": Decimal("20.5")})
    monkeypatch.setattr(ol, "RecalculadorLibreOffice", lambda *_a, **_k: falso)

    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(construido.datos)
    salida = tmp_path / "medicion"
    repo = tmp_path / "repo"

    codigo = ol.main([str(libro), "--salida", str(salida), "--raiz-repo", str(repo)])
    assert codigo == 0

    archivos = list(salida.glob("*.json"))
    assert len(archivos) == 1
    crudo = archivos[0].read_text(encoding="utf-8")
    datos = json.loads(crudo)

    assert datos["manifiesto"]["version_libreoffice"] == "LibreOffice 24.8.3.2 (falso)"
    assert datos["manifiesto"]["configuracion_regional"] == "es-VE"
    assert len(datos["discrepancias"]) == 1
    disc = datos["discrepancias"][0]
    assert set(disc) == {"hoja", "celda", "formula", "guardado", "recalculado"}
    assert disc["hoja"] == "PRESUPUESTO"
    assert disc["celda"] == f"P{fila_p1}"
    assert disc["guardado"] == "14.486725"
    assert disc["recalculado"] == "20.5"

    texto_pantalla = capsys.readouterr().out
    secretos = ("Friso liso", "Condominio Ejemplo", "Constructora Didáctica", "Rehabilitación")
    for secreto in secretos:
        assert secreto not in crudo
        assert secreto not in texto_pantalla
    assert "14,486725" in texto_pantalla
    assert "20,5" in texto_pantalla
    assert "0,005" in texto_pantalla


def test_el_resumen_se_puede_escribir_en_la_consola_de_windows(tmp_path: Path) -> None:
    from aplicacion.oraculo_hoja import Discrepancia

    d = Discrepancia(
        hoja="PRESUPUESTO", celda="P5", formula="=N5*O5",
        guardado=Decimal("999.99"), recalculado=Decimal("14.486725"),
    )  # fmt: skip
    texto = ol.resumen_pantalla([d], total_formulas=10, destino=tmp_path / "x.json")
    texto.encode("cp1252")  # la consola de Windows por omisión no admite «≠»
    assert "PRESUPUESTO!P5: guardado 999,99; recalculado 14,486725" in texto
