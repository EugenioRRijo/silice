"""Pruebas de `scripts/medir_inyeccion.py` (cadena inyectar -> recalcular -> auditar -> medir)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aplicacion.oraculo_hoja import LibreOfficeNoDisponibleError
from scripts import medir_inyeccion as mi
from scripts.inyector_fallas import Inyeccion
from tests.fixtures.libros_empresa import libro_limpio
from tests.fixtures.recalculo_falso import LibreOfficeFalso, escribir_taxonomia


def test_ejecutar_escribe_json_con_claves_pedidas_y_resumen_cp1252(tmp_path: Path) -> None:
    datos_base = libro_limpio().datos
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(datos_base)
    tax = escribir_taxonomia(tmp_path / "tax.toml")
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
        recalculador=LibreOfficeFalso(),
    )

    assert destino.is_file()
    crudo = destino.read_text(encoding="utf-8")
    carga = json.loads(crudo)

    assert set(carga) == {
        "modo",
        "cifra_oficial",
        "sha256_libro_base",
        "manifiesto",
        "totales",
        "inyecciones",
        "criterio_de_fracaso",
    }
    assert carga["modo"] == "todas_a_la_vez"
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
    tax = escribir_taxonomia(tmp_path / "tax.toml")

    with pytest.raises(ValueError, match="repositorio"):
        mi.ejecutar(libro, tax, repo / "sub", raiz_repo=repo, recalculador=LibreOfficeFalso())
    with pytest.raises(ValueError, match="repositorio"):
        mi.main([str(libro), "--taxonomia", str(tax), "--salida", str(mi.RAIZ / "docs")])


def test_no_sobrescribe_informe_existente(tmp_path: Path) -> None:
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(libro_limpio().datos)
    tax = escribir_taxonomia(tmp_path / "tax.toml")
    salida = tmp_path / "fuera"
    repo = tmp_path / "repo"

    mi.ejecutar(libro, tax, salida, n=2, semilla=7, raiz_repo=repo, recalculador=LibreOfficeFalso())
    with pytest.raises(FileExistsError):
        mi.ejecutar(
            libro, tax, salida, n=2, semilla=7, raiz_repo=repo, recalculador=LibreOfficeFalso()
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
    tax = escribir_taxonomia(tmp_path / "tax.toml")
    salida = tmp_path / "fuera"
    repo = tmp_path / "repo"

    codigo = mi.main(
        [
            str(libro),
            "--taxonomia",
            str(tax),
            "--salida",
            str(salida),
            "--raiz-repo",
            str(repo),
        ]
    )
    assert codigo == 2
    assert "LibreOffice" in capsys.readouterr().out


# --- hallazgos previos, Wilson, criterio y menos fallas (2026-11-25) -----------------------------


def _hallazgo(regla: str, *celdas: str, descripcion: str = "desc"):
    from types import SimpleNamespace

    from core.contracts.verificacion import Severidad

    return SimpleNamespace(
        regla=regla,
        severidad=Severidad.ERROR,
        descripcion=descripcion,
        impacto=None,
        origen_ids=celdas,
    )


def _procesar_en_secuencia(monkeypatch: pytest.MonkeyPatch, *respuestas) -> list[bytes]:
    """`procesar_libro` falso: cada llamada devuelve (o lanza) la respuesta siguiente."""
    from types import SimpleNamespace

    vistos: list[bytes] = []
    cola = iter(respuestas)

    def falso(datos: bytes, *_a, **_k):
        vistos.append(datos)
        r = next(cola)
        if isinstance(r, Exception):
            raise r
        return SimpleNamespace(informe=SimpleNamespace(hallazgos=r))

    monkeypatch.setattr(mi, "procesar_libro", falso)
    return vistos


def _preparar(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(libro_limpio().datos)
    tax = escribir_taxonomia(tmp_path / "tax.toml")
    repo = tmp_path / "repo"
    repo.mkdir()
    return libro, tax, tmp_path / "medicion", repo


def _celda_sembrada(libro: Path, tax: Path, n: int = 1) -> str:
    from scripts.inyector_fallas import cargar_taxonomia, inyectar

    _, inyecciones = inyectar(libro.read_bytes(), cargar_taxonomia(tax), n=n, semilla=7)
    return f"{inyecciones[0].hoja}!{inyecciones[0].celda}"


def test_un_hallazgo_previo_del_libro_no_acredita_la_falla_sembrada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    libro, tax, salida, repo = _preparar(tmp_path)
    previo = _hallazgo("L1", _celda_sembrada(libro, tax))
    # el libro base ya tenía ese hallazgo y el sembrado (que ninguna regla ve) lo deja igual
    _procesar_en_secuencia(monkeypatch, [previo], [previo])

    destino, _ = mi.ejecutar(
        libro, tax, salida, n=1, semilla=7, raiz_repo=repo, recalculador=LibreOfficeFalso()
    )

    totales = json.loads(destino.read_text(encoding="utf-8"))["totales"]
    assert totales["detectadas"] == 0
    assert totales["hallazgos_previos_descontados"] == 1


def test_un_hallazgo_nuevo_en_la_celda_sembrada_si_la_acredita(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    libro, tax, salida, repo = _preparar(tmp_path)
    nuevo = _hallazgo("L1", _celda_sembrada(libro, tax))
    _procesar_en_secuencia(monkeypatch, [], [nuevo])

    destino, _ = mi.ejecutar(
        libro, tax, salida, n=1, semilla=7, raiz_repo=repo, recalculador=LibreOfficeFalso()
    )

    assert json.loads(destino.read_text(encoding="utf-8"))["totales"]["detectadas"] == 1


def test_el_json_y_la_pantalla_traen_wilson_y_criterio(tmp_path: Path) -> None:
    from asistente.experimento.metricas import wilson

    libro, tax, salida, repo = _preparar(tmp_path)
    destino, texto = mi.ejecutar(
        libro, tax, salida, n=3, semilla=7, raiz_repo=repo, recalculador=LibreOfficeFalso()
    )
    carga = json.loads(destino.read_text(encoding="utf-8"))
    det = carga["totales"]["detectadas"]
    assert carga["totales"]["intervalo_wilson_95"] == pytest.approx(list(wilson(det, 3)))
    assert any("Detección < 50 %" in linea for linea in carga["criterio_de_fracaso"])
    assert "Wilson" in texto
    assert "Detección < 50 %" in texto
    assert "todas las fallas a la vez" in texto


def test_resumen_pantalla_trae_el_intervalo_de_wilson(tmp_path: Path) -> None:
    inyecciones = [
        Inyeccion(i, "PRESUPUESTO", f"P{i}", "TAX-01", "valor_fijo", "1", "2") for i in range(1, 25)
    ]
    detectado = {i: (1 if i <= 12 else None) for i in range(1, 25)}
    texto = mi.resumen_pantalla(inyecciones, detectado, destino=tmp_path / "s.json")
    assert "[31,4 %; 68,6 %]" in texto


def test_menos_fallas_que_las_pedidas_termina_con_error_claro(tmp_path: Path) -> None:
    libro, tax, salida, repo = _preparar(tmp_path)
    with pytest.raises(mi.MenosFallasQueLasPedidas, match="pidieron 5000"):
        mi.ejecutar(
            libro, tax, salida, n=5000, semilla=7, raiz_repo=repo, recalculador=LibreOfficeFalso()
        )
    assert not salida.exists()  # no escribió un informe a medias
    destino, _ = mi.ejecutar(
        libro,
        tax,
        salida,
        n=5000,
        semilla=7,
        raiz_repo=repo,
        recalculador=LibreOfficeFalso(),
        permitir_menos=True,
    )
    carga = json.loads(destino.read_text(encoding="utf-8"))
    assert carga["totales"]["pedidas"] == 5000
    assert carga["totales"]["inyectadas"] < 5000


def test_main_devuelve_3_con_menos_fallas_salvo_permitir_menos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    libro, tax, salida, repo = _preparar(tmp_path)
    monkeypatch.setattr(mi, "RecalculadorLibreOffice", lambda *_a, **_k: LibreOfficeFalso())
    comun = [str(libro), "--taxonomia", str(tax), "--n", "5000", "--raiz-repo", str(repo)]
    assert mi.main([*comun, "--salida", str(salida)]) == 3
    assert "pidieron 5000" in capsys.readouterr().out
    assert mi.main([*comun, "--salida", str(salida), "--permitir-menos"]) == 0


def test_el_porcentaje_de_la_pantalla_redondea_half_up_sobre_decimal(tmp_path: Path) -> None:
    inyecciones = [
        Inyeccion(i, "PRESUPUESTO", f"P{i}", "TAX-01", "valor_fijo", "1", "2")
        for i in range(1, 401)
    ]
    detectado = {i: (1 if i <= 29 else None) for i in range(1, 401)}
    texto = mi.resumen_pantalla(inyecciones, detectado, destino=tmp_path / "s.json")
    assert "Detectó 29 de 400 fallas inyectadas (7,3 %)" in texto  # 7,25 %: mitad hacia arriba
    vacio = mi.resumen_pantalla([], {}, destino=tmp_path / "s.json")
    assert "(sin dato)" in vacio


def test_la_medicion_automatica_dice_que_cuenta_lo_senalado(tmp_path: Path) -> None:
    inyecciones = [Inyeccion(1, "PRESUPUESTO", "P1", "TAX-01", "valor_fijo", "1", "2")]
    texto = mi.resumen_pantalla(inyecciones, {1: 1}, destino=tmp_path / "s.json")
    assert "Detección < 50 % (señalado por Sílice" in texto
