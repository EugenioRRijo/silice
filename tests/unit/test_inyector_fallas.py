"""Pruebas del inyector genérico de fallas con taxonomía TOML."""

from __future__ import annotations

import io
import re
import tomllib
from pathlib import Path

import openpyxl
import pytest

from scripts import inyector_fallas as inyector
from scripts import medir_auditoria_libro as m
from tests.fixtures.libros_empresa import libro_limpio

RUTA_PLANTILLA = (
    Path(__file__).resolve().parents[2] / "docs" / "tesis" / "taxonomia_fallas_plantilla.toml"
)


def _taxonomia_unica(
    operacion: str,
    *,
    cat_id: str = "T-01",
    nombre: str = "Falla de prueba",
    hojas: list[str] | None = None,
) -> dict:
    categoria: dict[str, object] = {
        "id": cat_id,
        "nombre": nombre,
        "fuente": "Fuente de prueba (por verificar)",
        "operacion": operacion,
        "peso": 1.0,
    }
    if hojas is not None:
        categoria["hojas"] = hojas
    return {"categorias": [categoria]}


def _celdas_libro(
    datos: bytes, *, data_only: bool
) -> tuple[list[str], dict[tuple[str, str], tuple]]:
    wb = openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=data_only)
    try:
        hojas = list(wb.sheetnames)
        celdas: dict[tuple[str, str], tuple] = {}
        for ws in wb.worksheets:
            for fila in ws.iter_rows(values_only=False):
                for c in fila:
                    if c.value is not None:
                        celdas[(ws.title, c.coordinate)] = (c.value, c.data_type)
        return hojas, celdas
    finally:
        wb.close()


def test_misma_semilla_da_mismo_libro_y_misma_clave():
    datos = libro_limpio().datos
    tax = tomllib.loads(RUTA_PLANTILLA.read_text(encoding="utf-8"))

    datos_a, inj_a = inyector.inyectar(datos, tax, n=8, semilla=7)
    datos_b, inj_b = inyector.inyectar(datos, tax, n=8, semilla=7)
    _, inj_otra = inyector.inyectar(datos, tax, n=8, semilla=99)

    assert datos_a == datos_b
    assert inj_a == inj_b
    assert len(inj_a) == 8
    assert inj_a != inj_otra


@pytest.mark.parametrize("operacion", inyector.OPERACIONES)
def test_cada_operacion_cambia_solo_la_celda_anotada(operacion: str):
    datos = libro_limpio().datos
    tax = _taxonomia_unica(operacion)

    datos_out, inyecciones = inyector.inyectar(datos, tax, n=1, semilla=11)
    assert len(inyecciones) == 1
    inj = inyecciones[0]
    assert inj.operacion == operacion
    objetivo = (inj.hoja, inj.celda)

    hojas_antes, celdas_f_antes = _celdas_libro(datos, data_only=False)
    hojas_despues, celdas_f_despues = _celdas_libro(datos_out, data_only=False)
    assert hojas_antes == hojas_despues

    sin_objetivo_antes = {k: v for k, v in celdas_f_antes.items() if k != objetivo}
    sin_objetivo_despues = {k: v for k, v in celdas_f_despues.items() if k != objetivo}
    assert sin_objetivo_antes == sin_objetivo_despues
    assert celdas_f_antes.get(objetivo) != celdas_f_despues.get(objetivo)

    _, celdas_v_antes = _celdas_libro(datos, data_only=True)
    _, celdas_v_despues = _celdas_libro(datos_out, data_only=True)
    assert {k: v for k, v in celdas_v_antes.items() if k != objetivo} == {
        k: v for k, v in celdas_v_despues.items() if k != objetivo
    }


def test_valor_fijo_deja_un_numero_donde_habia_formula():
    datos = libro_limpio().datos
    datos_out, inyecciones = inyector.inyectar(
        datos, _taxonomia_unica("valor_fijo"), n=1, semilla=3
    )
    inj = inyecciones[0]
    objetivo = (inj.hoja, inj.celda)

    _, antes_f = _celdas_libro(datos, data_only=False)
    _, despues_f = _celdas_libro(datos_out, data_only=False)
    _, despues_v = _celdas_libro(datos_out, data_only=True)

    val_antes, tipo_antes = antes_f[objetivo]
    assert tipo_antes == "f" and isinstance(val_antes, str) and val_antes.startswith("=")

    val_despues, tipo_despues = despues_f[objetivo]
    assert tipo_despues != "f"
    assert isinstance(val_despues, (int, float)) and not isinstance(val_despues, bool)
    assert despues_v[objetivo][0] == pytest.approx(val_despues)


def test_referencia_desplazada_cambia_solo_la_fila():
    datos = libro_limpio().datos
    _, inyecciones = inyector.inyectar(
        datos, _taxonomia_unica("referencia_desplazada"), n=3, semilla=5
    )
    assert len(inyecciones) == 3
    patron = re.compile(r"(\$?[A-Za-z]{1,3}\$?)(\d+)")
    for inj in inyecciones:
        assert inj.antes.startswith("=") and inj.despues.startswith("=")
        refs_a = patron.findall(inj.antes)
        refs_d = patron.findall(inj.despues)
        assert len(refs_a) == len(refs_d)
        cambios = [(a, d) for a, d in zip(refs_a, refs_d, strict=True) if a != d]
        assert len(cambios) == 1
        (col_a, fila_a), (col_d, fila_d) = cambios[0]
        assert col_a == col_d
        assert abs(int(fila_d) - int(fila_a)) == 1


def test_operaciones_numericas_y_borrado_cumplen_su_regla():
    datos = libro_limpio().datos

    out_sig, inj_sig = inyector.inyectar(datos, _taxonomia_unica("signo"), n=1, semilla=2)
    _, cf_antes = _celdas_libro(datos, data_only=False)
    _, cf_sig = _celdas_libro(out_sig, data_only=False)
    obj_s = (inj_sig[0].hoja, inj_sig[0].celda)
    assert cf_sig[obj_s][0] == pytest.approx(-cf_antes[obj_s][0])

    out_esc, inj_esc = inyector.inyectar(datos, _taxonomia_unica("escala"), n=1, semilla=2)
    _, cf_esc = _celdas_libro(out_esc, data_only=False)
    obj_e = (inj_esc[0].hoja, inj_esc[0].celda)
    assert cf_esc[obj_e][0] == pytest.approx(cf_antes[obj_e][0] * 1000)

    out_bor, inj_bor = inyector.inyectar(datos, _taxonomia_unica("formula_borrada"), n=1, semilla=2)
    _, cf_bor = _celdas_libro(out_bor, data_only=False)
    _, cv_bor = _celdas_libro(out_bor, data_only=True)
    obj_b = (inj_bor[0].hoja, inj_bor[0].celda)
    assert cf_antes[obj_b][1] == "f"
    assert obj_b not in cf_bor and obj_b not in cv_bor


def test_sin_celdas_elegibles_no_falla(capsys):
    datos = libro_limpio().datos
    # PORTADA no tiene fórmulas; buscar valor_fijo allí no encuentra celdas elegibles.
    tax = _taxonomia_unica("valor_fijo", hojas=["PORTADA"])
    datos_out, inyecciones = inyector.inyectar(datos, tax, n=4, semilla=1)
    assert inyecciones == []
    assert datos_out == datos
    err = capsys.readouterr().err
    assert "valor_fijo" in err and "elegibles" in err


def test_respeta_hojas():
    datos = libro_limpio().datos
    tax = _taxonomia_unica("valor_fijo", hojas=["PRESUPUESTO"])
    _, inyecciones = inyector.inyectar(datos, tax, n=5, semilla=13)
    assert len(inyecciones) == 5
    assert all(inj.hoja == "PRESUPUESTO" for inj in inyecciones)


def test_cli_escribe_libro_y_clave_legible_con_medir_auditoria(tmp_path: Path):
    origen = tmp_path / "fuente" / "limpio.xlsx"
    origen.parent.mkdir()
    origen.write_bytes(libro_limpio().datos)
    salida = tmp_path / "salida"
    repo = tmp_path / "repo"
    repo.mkdir()

    codigo = inyector.main([
        str(origen),
        "--taxonomia",
        str(RUTA_PLANTILLA),
        "--n",
        "6",
        "--semilla",
        "7",
        "--salida",
        str(salida),
        "--raiz-repo",
        str(repo),
    ])
    assert codigo == 0
    libro_out = salida / "limpio_inyectado.xlsx"
    clave_out = salida / "limpio_clave.xlsx"
    assert libro_out.is_file() and clave_out.is_file()

    sembrados = m.leer_clave(clave_out)
    assert [s.numero for s in sembrados] == list(range(1, 7))
    assert all("!" in s.celda and ": " in s.tipo for s in sembrados)

    hoja = openpyxl.load_workbook(clave_out)["Sembrados"]
    cambios = [hoja.cell(row=r, column=4) for r in range(2, 8)]
    assert all(" → " in str(c.value) and c.data_type == "s" for c in cambios)


def test_cli_se_niega_a_escribir_dentro_del_repositorio(tmp_path: Path):
    origen = tmp_path / "limpio.xlsx"
    origen.write_bytes(libro_limpio().datos)
    repo = tmp_path / "repo"
    repo.mkdir()
    destino = repo / "datos_fuera_de_lugar"

    with pytest.raises(ValueError, match="repositorio"):
        inyector.main([
            str(origen),
            "--taxonomia",
            str(RUTA_PLANTILLA),
            "--n",
            "3",
            "--semilla",
            "7",
            "--salida",
            str(destino),
            "--raiz-repo",
            str(repo),
        ])
    assert not destino.exists()


def test_plantilla_toml_cubre_las_seis_operaciones_con_fuente_por_verificar():
    tax = tomllib.loads(RUTA_PLANTILLA.read_text(encoding="utf-8"))
    cats = tax["categorias"]
    assert len(cats) == 6
    assert {c["operacion"] for c in cats} == set(inyector.OPERACIONES)
    assert all("por verificar" in c["fuente"].casefold() for c in cats)


def test_la_lista_sin_operacion_de_la_guia_del_tercero_no_se_siembra():
    """La guía del tercero (docs/tesis/2026-11-25-guia-taxonomia-tercero.md) manda las familias
    que el inyector no sabe producir a una lista aparte, `[[sin_operacion]]`: el inyector la
    ignora y siembra solo `[[categorias]]`. Una operación desconocida en `categorias` se rechaza."""
    texto = (
        '[[categorias]]\nid = "TAX-01"\nnombre = "Valor fijo"\n'
        'fuente = "Panko y Aurigemma (2010)"\n'
        'operacion = "valor_fijo"\npeso = 1.0\n\n'
        '[[sin_operacion]]\nid = "TAX-X1"\nnombre = "Renglón contado dos veces"\n'
        'fuente = "Rajalingham et al. (2000)"\njustificacion = "Sin operación de duplicado."\n'
    )
    taxonomia = tomllib.loads(texto)
    _, inyecciones = inyector.inyectar(libro_limpio().datos, taxonomia, n=3, semilla=7)
    assert {i.categoria for i in inyecciones} == {"TAX-01"}
    taxonomia["categorias"][0]["operacion"] = "no_disponible"
    with pytest.raises(ValueError, match="Operación desconocida"):
        inyector.inyectar(libro_limpio().datos, taxonomia, n=1, semilla=7)
