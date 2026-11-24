"""Modo «una falla por vez» de `scripts/medir_inyeccion.py` (pruebas de mutación): cada falla
se inyecta sola y cuenta como detectada si la auditoría da algún hallazgo que el libro limpio,
pasado por la misma cadena, no daba. Así no depende de que Sílice marque la celda exacta."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from core.contracts.verificacion import Severidad
from scripts import medir_inyeccion as mi
from tests.fixtures.libros_empresa import libro_limpio
from tests.unit.test_medir_inyeccion import _escribir_taxonomia, _LibreOfficeFalso


def _h(regla: str, descripcion: str, *celdas: str, sev: Severidad = Severidad.ERROR):
    return SimpleNamespace(regla=regla, severidad=sev, descripcion=descripcion, origen_ids=celdas)


def test_sin_hallazgos_nuevos_no_hay_reaccion() -> None:
    base = [_h("L9", "verificación vale 40,00", "PLAN!B6")]
    assert mi.reaccion(base, list(base)) == []


def test_un_hallazgo_nuevo_o_cambiado_es_reaccion_y_da_su_regla() -> None:
    base = [_h("L9", "verificación vale 40,00", "PLAN!B6")]
    mutado = [_h("L9", "verificación vale 45,00", "PLAN!B6"), _h("L3", "guarda 5", "P!P5")]
    assert mi.reaccion(base, mutado) == ["L3", "L9"]


def test_los_avisos_no_aplicables_no_cuentan_como_reaccion() -> None:
    aviso = _h("R2", "R2 no aplicable: sin curva", sev=Severidad.INFO)
    assert mi.reaccion([], [aviso]) == []


def test_ejecutar_mutantes_escribe_una_fila_por_falla_y_resumen_cp1252(tmp_path: Path) -> None:
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(libro_limpio().datos)
    tax = _escribir_taxonomia(tmp_path / "tax.toml")
    repo = tmp_path / "repo"
    repo.mkdir()

    destino, texto = mi.ejecutar_mutantes(
        libro, tax, tmp_path / "medicion", n=3, semilla=7, raiz_repo=repo,
        recalculador=_LibreOfficeFalso(),
    )  # fmt: skip

    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert datos["modo"] == "una_por_vez"
    assert 1 <= len(datos["mutantes"]) <= 3
    for m in datos["mutantes"]:
        assert set(m) == {"numero", "hoja", "celda", "categoria", "operacion", "detectada",
                          "reglas_nuevas", "rechazado"}
        assert m["detectada"] == bool(m["reglas_nuevas"] or m["rechazado"])
    assert datos["totales"]["inyectadas"] == len(datos["mutantes"])
    texto.encode("cp1252")
    assert "una por vez" in texto
