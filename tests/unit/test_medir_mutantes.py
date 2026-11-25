"""Modo «una falla por vez» de `scripts/medir_inyeccion.py` (pruebas de mutación): cada falla
se inyecta sola y cuenta como detectada si la auditoría da algún hallazgo que el libro limpio,
pasado por la misma cadena, no daba. Así no depende de que Sílice marque la celda exacta."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.contracts.verificacion import Severidad
from scripts import medir_inyeccion as mi
from tests.fixtures.libros_empresa import libro_limpio
from tests.fixtures.recalculo_falso import LibreOfficeFalso, escribir_taxonomia


def _h(regla: str, descripcion: str, *celdas: str, sev: Severidad = Severidad.ERROR):
    return SimpleNamespace(regla=regla, severidad=sev, descripcion=descripcion, origen_ids=celdas)


def test_sin_hallazgos_nuevos_no_hay_reaccion() -> None:
    base = [_h("L9", "verificación vale 40,00", "PLAN!B6")]
    assert mi.reaccion(base, list(base)) == []


def test_un_hallazgo_nuevo_es_reaccion_y_da_su_regla() -> None:
    base = [_h("L9", "verificación vale 40,00", "PLAN!B6")]
    mutado = [_h("L9", "verificación vale 40,00", "PLAN!B6"), _h("L3", "guarda 5", "P!P5")]
    assert mi.reaccion(base, mutado) == ["L3"]


def test_un_hallazgo_previo_que_solo_cambio_una_cifra_no_es_reaccion() -> None:
    base = [_h("L9", "verificación vale 40,00", "PLAN!B6")]
    mutado = [_h("L9", "verificación vale 45,00", "PLAN!B6")]
    assert mi.reaccion(base, mutado) == []


def test_los_avisos_no_aplicables_no_cuentan_como_reaccion() -> None:
    aviso = _h("R2", "R2 no aplicable: sin curva", sev=Severidad.INFO)
    assert mi.reaccion([], [aviso]) == []


def test_ejecutar_mutantes_escribe_una_fila_por_falla_y_resumen_cp1252(tmp_path: Path) -> None:
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(libro_limpio().datos)
    tax = escribir_taxonomia(tmp_path / "tax.toml")
    repo = tmp_path / "repo"
    repo.mkdir()

    destino, texto = mi.ejecutar_mutantes(
        libro, tax, tmp_path / "medicion", n=3, semilla=7, raiz_repo=repo,
        recalculador=LibreOfficeFalso(),
    )  # fmt: skip

    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert datos["modo"] == "una_por_vez"
    assert len(datos["mutantes"]) == 3
    for m in datos["mutantes"]:
        assert set(m) == {
            "numero",
            "hoja",
            "celda",
            "categoria",
            "operacion",
            "detectada",
            "reglas_nuevas",
            "rechazado",
        }
        assert m["detectada"] == bool(m["reglas_nuevas"])
    assert datos["totales"]["inyectadas"] == len(datos["mutantes"])
    texto.encode("cp1252")
    assert "una por vez" in texto


# --- las mismas n fallas, rechazos aparte y hallazgos previos (2026-11-25) -----------------------


def test_una_por_vez_usa_las_mismas_n_inyecciones_que_todas_a_la_vez(tmp_path: Path) -> None:
    from scripts.inyector_fallas import cargar_taxonomia, inyectar

    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(libro_limpio().datos)
    tax = escribir_taxonomia(tmp_path / "tax.toml")
    repo = tmp_path / "repo"
    repo.mkdir()
    _, esperadas = inyectar(libro.read_bytes(), cargar_taxonomia(tax), n=4, semilla=7)

    destino, _ = mi.ejecutar_mutantes(
        libro, tax, tmp_path / "medicion", n=4, semilla=7, raiz_repo=repo,
        recalculador=LibreOfficeFalso(),
    )  # fmt: skip

    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert [(m["hoja"], m["celda"], m["operacion"]) for m in datos["mutantes"]] == [
        (i.hoja, i.celda, i.operacion) for i in esperadas
    ]


def test_cada_libro_mutante_difiere_del_base_solo_en_su_celda(tmp_path: Path) -> None:
    import io

    import openpyxl

    from scripts.inyector_fallas import cargar_taxonomia, inyectar

    base = libro_limpio().datos
    tax = escribir_taxonomia(tmp_path / "tax.toml")
    todo, inyecciones = inyectar(base, cargar_taxonomia(tax), n=3, semilla=7)
    assert len(inyecciones) == 3

    def celdas(datos: bytes) -> dict[tuple[str, str], object]:
        libro = openpyxl.load_workbook(io.BytesIO(datos))
        return {
            (ws.title, c.coordinate): c.value for ws in libro for f in ws.iter_rows() for c in f
        }

    valores_base, valores_todo = celdas(base), celdas(todo)
    for inj in inyecciones:
        solo = celdas(mi._solo_una(base, todo, inj))
        distintas = {k for k in solo if solo[k] != valores_base.get(k)}
        assert distintas == {(inj.hoja, inj.celda)}
        assert solo[(inj.hoja, inj.celda)] == valores_todo[(inj.hoja, inj.celda)]


def _procesar_en_secuencia(monkeypatch: pytest.MonkeyPatch, *respuestas) -> None:
    cola = iter(respuestas)

    def falso(datos: bytes, *_a, **_k):
        r = next(cola)
        if isinstance(r, Exception):
            raise r
        return SimpleNamespace(informe=SimpleNamespace(hallazgos=r))

    monkeypatch.setattr(mi, "procesar_libro", falso)


def _una_por_vez(tmp_path: Path, n: int = 2, **extra):
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(libro_limpio().datos)
    tax = escribir_taxonomia(tmp_path / "tax.toml")
    repo = tmp_path / "repo"
    repo.mkdir()
    destino, texto = mi.ejecutar_mutantes(
        libro, tax, tmp_path / "medicion", n=n, semilla=7, raiz_repo=repo,
        recalculador=LibreOfficeFalso(), **extra,
    )  # fmt: skip
    return json.loads(destino.read_text(encoding="utf-8")), texto


def test_un_rechazo_del_lector_se_cuenta_aparte_y_no_como_detectada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from adapters.hoja_empresa.modelo import LibroNoInterpretable

    _procesar_en_secuencia(monkeypatch, [], LibroNoInterpretable("x"), LibroNoInterpretable("y"))
    datos, texto = _una_por_vez(tmp_path, n=2)
    assert datos["totales"]["detectadas"] == 0
    assert datos["totales"]["rechazados"] == 2
    assert all(m["rechazado"] and not m["detectada"] for m in datos["mutantes"])
    assert "rechazó 2" in texto


def test_un_hallazgo_previo_con_otra_cifra_no_acredita_la_falla_una_por_vez(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previo = _h("L9", "verificación vale 40,00", "PLAN!B6")
    cambiado = _h("L9", "verificación vale 45,00", "PLAN!B6")
    _procesar_en_secuencia(monkeypatch, [previo], [cambiado], [cambiado])
    datos, _ = _una_por_vez(tmp_path, n=2)
    assert datos["totales"]["detectadas"] == 0


def test_una_por_vez_trae_wilson_criterio_y_nota_de_cifra_secundaria(tmp_path: Path) -> None:
    datos, texto = _una_por_vez(tmp_path, n=3)
    assert len(datos["totales"]["intervalo_wilson_95"]) == 2
    assert datos["cifra_oficial"] is False
    assert "Wilson" in texto
    assert "secundaria" in texto
    assert "Detección < 50 %" in texto


def test_una_por_vez_con_menos_fallas_que_las_pedidas_da_error_claro(tmp_path: Path) -> None:
    with pytest.raises(mi.MenosFallasQueLasPedidas, match="pidieron 5000"):
        _una_por_vez(tmp_path, n=5000)
