"""Pruebas de `scripts/medir_inyeccion.py` (cadena inyectar -> recalcular -> auditar -> medir)."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import openpyxl
import pytest

from aplicacion.oraculo_hoja import LibreOfficeNoDisponibleError
from scripts import medir_inyeccion as mi
from scripts.inyector_fallas import Inyeccion
from tests.fixtures.libros_empresa import libro_limpio


class _LibreOfficeFalso:
    """Doble de prueba sin LibreOffice real."""

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
        buf = io.BytesIO()
        nuevo.save(buf)
        nuevo.close()
        return buf.getvalue()


def _escribir_taxonomia(ruta: Path) -> Path:
    ruta.write_text(
        '[[categorias]]\n'
        'id = "TAX-01"\n'
        'nombre = "Valor fijo"\n'
        'fuente = "Fuente de prueba"\n'
        'operacion = "valor_fijo"\n'
        'peso = 1.0\n'
        'hojas = ["PRESUPUESTO"]\n',
        encoding="utf-8",
    )
    return ruta


def test_ejecutar_escribe_json_con_claves_pedidas_y_resumen_cp1252(tmp_path: Path) -> None:
    datos_base = libro_limpio().datos
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(datos_base)
    tax = _escribir_taxonomia(tmp_path / "tax.toml")
    salida = tmp_path / "medicion"
    repo = tmp_path / "repo"
    repo.mkdir()

    destino, texto = mi.ejecutar(
        libro,
        tax,
        salida,
        n=3,
        semilla=7,
        raiz_repo=repo,
        recalculador=_LibreOfficeFalso(),
    )

    assert destino.is_file()
    crudo = destino.read_text(encoding="utf-8")
    carga = json.loads(crudo)

    assert set(carga) == {"sha256_libro_base", "manifiesto", "totales", "inyecciones"}
    assert carga["sha256_libro_base"] == hashlib.sha256(datos_base).hexdigest()
    assert carga["manifiesto"]["version_libreoffice"] == "LibreOffice 24.8.3.2 (falso)"
    assert carga["manifiesto"]["semilla"] == 7
    assert carga["manifiesto"]["configuracion_regional"] == "es-VE"

    assert len(carga["inyecciones"]) == 3
    for inj in carga["inyecciones"]:
        assert set(inj) == {"numero", "hoja", "celda", "categoria", "operacion", "detectado_por"}
        assert inj["detectado_por"] is None or isinstance(inj["detectado_por"], int)

    totales = carga["totales"]
    assert totales["inyectadas"] == 3
    assert totales["detectadas"] + totales["escapadas"] == 3

    texto.encode("cp1252")
    assert "Detectó " in texto
    assert " de 3 fallas inyectadas (" in texto
    assert "," in texto

    for secreto in ("Friso liso", "Condominio Ejemplo", "Constructora Didáctica", "Rehabilitación"):
        assert secreto not in crudo
        assert secreto not in texto


def test_resumen_pantalla_lista_escapadas_en_cp1252(tmp_path: Path) -> None:
    inyecciones = [
        Inyeccion(1, "PRESUPUESTO", "P5", "TAX-01", "valor_fijo", "=1", "2"),
        Inyeccion(2, "APU-01", "E10", "TAX-04", "signo", "0.2", "-0.2"),
    ]
    texto = mi.resumen_pantalla(inyecciones, {1: 1, 2: None}, destino=tmp_path / "salida.json")
    texto.encode("cp1252")
    assert "Detectó 1 de 2 fallas inyectadas (50,0 %)" in texto
    assert "TAX-04" in texto
    assert "APU-01!E10" in texto


def test_se_niega_a_escribir_dentro_del_repositorio(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(libro_limpio().datos)
    tax = _escribir_taxonomia(tmp_path / "tax.toml")

    with pytest.raises(ValueError, match="repositorio"):
        mi.ejecutar(libro, tax, repo / "sub", raiz_repo=repo, recalculador=_LibreOfficeFalso())
    with pytest.raises(ValueError, match="repositorio"):
        mi.main([str(libro), "--taxonomia", str(tax), "--salida", str(mi.RAIZ / "docs")])


def test_no_sobrescribe_informe_existente(tmp_path: Path) -> None:
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(libro_limpio().datos)
    tax = _escribir_taxonomia(tmp_path / "tax.toml")
    salida = tmp_path / "fuera"
    repo = tmp_path / "repo"

    mi.ejecutar(libro, tax, salida, n=2, semilla=7, raiz_repo=repo, recalculador=_LibreOfficeFalso())
    with pytest.raises(FileExistsError):
        mi.ejecutar(
            libro, tax, salida, n=2, semilla=7, raiz_repo=repo, recalculador=_LibreOfficeFalso()
        )


def test_sin_libreoffice_devuelve_codigo_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class _SinLO:
        def version(self) -> str:
            raise LibreOfficeNoDisponibleError("No se encontró LibreOffice (soffice).")

        def recalcular(self, datos: bytes, nombre: str) -> bytes:
            raise LibreOfficeNoDisponibleError("No se encontró LibreOffice (soffice).")

    monkeypatch.setattr(mi, "RecalculadorLibreOffice", lambda *_a, **_k: _SinLO())
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(libro_limpio().datos)
    tax = _escribir_taxonomia(tmp_path / "tax.toml")
    salida = tmp_path / "fuera"
    repo = tmp_path / "repo"

    codigo = mi.main([
        str(libro),
        "--taxonomia",
        str(tax),
        "--salida",
        str(salida),
        "--raiz-repo",
        str(repo),
    ])
    assert codigo == 2
    assert "LibreOffice" in capsys.readouterr().out
