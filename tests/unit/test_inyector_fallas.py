"""Pruebas del inyector genérico de fallas con taxonomía TOML."""

from __future__ import annotations

import io
import re
import tomllib
import zipfile
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
        assert cambios
        # Todas las apariciones de la misma referencia cambian igual (una sola referencia).
        assert len(set(cambios)) == 1
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


# --- Endurecimiento del inyector (auditoría 2026-11-25) ---------------------------------------


def _libro_xlsxwriter(
    celdas: dict[str, tuple[str | None, object]], nombres: dict[str, str] | None = None
) -> bytes:
    """Libro con fórmulas y valores cacheados. `celdas`: coord -> (fórmula | None, valor)."""
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet("Hoja")
    for nombre, destino in (nombres or {}).items():
        wb.define_name(nombre, destino)
    for coord, (formula, valor) in celdas.items():
        if formula is not None:
            ws.write_formula(coord, formula, None, valor)
        elif isinstance(valor, str):
            ws.write_string(coord, valor)
        else:
            ws.write_number(coord, float(valor))
    wb.close()
    return buf.getvalue()


def _con_nombre_definido(datos: bytes, nombre: str, destino: str) -> bytes:
    """Agrega un nombre definido que parece celda (xlsxwriter y openpyxl lo rechazan)."""
    salida = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(datos)) as zin, zipfile.ZipFile(salida, "w") as zout:
        for info in zin.infolist():
            contenido = zin.read(info.filename)
            if info.filename == "xl/workbook.xml":
                xml = contenido.decode("utf-8")
                nodo = f'<definedName name="{nombre}">{destino}</definedName>'
                if "</definedNames>" in xml:
                    xml = xml.replace("</definedNames>", nodo + "</definedNames>")
                else:
                    xml = xml.replace(
                        "<calcPr", f"<definedNames>{nodo}</definedNames><calcPr", 1
                    )
                contenido = xml.encode("utf-8")
            zout.writestr(info, contenido)
    return salida.getvalue()


def _sembrar(datos: bytes, operacion: str, n: int = 5, semilla: int = 3):
    return inyector.inyectar(datos, _taxonomia_unica(operacion), n=n, semilla=semilla)


def test_referencia_desplazada_no_crea_referencia_circular(capsys):
    # Desplazar A4 -> A5 dentro de A5 sería una referencia circular: no es elegible.
    datos = _libro_xlsxwriter({"A4": (None, 3), "A5": ("=A4+1", 4)})
    _, inyecciones = _sembrar(datos, "referencia_desplazada")
    assert inyecciones == []


def test_referencia_desplazada_no_toca_nombres_definidos_que_parecen_celdas():
    datos = _con_nombre_definido(
        _libro_xlsxwriter({"A1": (None, 3), "B1": ("=PU1*2", 6), "C1": ("=PU1*A1", 6)}),
        "PU1",
        "Hoja!$A$1",
    )
    _, inyecciones = _sembrar(datos, "referencia_desplazada", n=5)
    assert [(i.celda, i.despues) for i in inyecciones] == [("C1", "=PU1*A2")]


def test_referencia_desplazada_cambia_todas_las_apariciones_de_la_referencia():
    formula = '=IF(B10="","",VLOOKUP(B10,PRECIOS,4,0))'
    datos = _libro_xlsxwriter(
        {"B10": (None, 1), "D1": (formula, 7), "E1": (None, 1)},
        nombres={"PRECIOS": "=Hoja!$E$1:$F$2"},
    )
    _, inyecciones = _sembrar(datos, "referencia_desplazada", n=1)
    assert len(inyecciones) == 1
    assert inyecciones[0].despues == '=IF(B11="","",VLOOKUP(B11,PRECIOS,4,0))'


def test_no_siembra_sobre_celdas_con_error_ni_con_ref():
    datos = _libro_xlsxwriter({
        "C1": ("=A1+B1", "#REF!"),
        "C2": ("=A1/B1", "#DIV/0!"),
        "C3": ("=#REF!+A1", 5),
        "C4": ("=A1+B1", 5),
    })
    for operacion in ("referencia_desplazada", "formula_borrada", "valor_fijo"):
        _, inyecciones = _sembrar(datos, operacion)
        assert {i.celda for i in inyecciones} <= {"C4"}, operacion
    _, inyecciones = _sembrar(datos, "formula_borrada")
    assert [i.celda for i in inyecciones] == ["C4"]


def test_signo_y_escala_no_caen_en_la_columna_de_numeracion():
    datos = _libro_xlsxwriter({
        "A1": (None, "Nº"),
        "A2": (None, 1),
        "A3": (None, 2),
        "B1": (None, "Cantidad"),
        "B2": (None, 5),
        "B3": (None, -3),
        "C1": (None, "Ítem"),
        "C2": (None, 7),
        "D2": (None, 2.5),
    })
    for operacion in ("signo", "escala"):
        _, inyecciones = _sembrar(datos, operacion, n=10)
        # Una cantidad entera en la columna B (encabezado «Cantidad») sí es elegible, también
        # negativa; la numeración (encabezados «Nº» e «Ítem») no.
        assert {i.celda for i in inyecciones} == {"B2", "B3", "D2"}, operacion


def _libro_con_formula_compartida() -> bytes:
    base = _libro_xlsxwriter({"A1": (None, 1)})
    hoja = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        '<row r="1"><c r="A1"><v>1</v></c>'
        '<c r="B1"><f t="shared" ref="B1:B3" si="0">A1*2</f><v>2</v></c></row>'
        '<row r="2"><c r="A2"><v>2</v></c><c r="B2"><f t="shared" si="0"/><v>4</v></c></row>'
        '<row r="3"><c r="A3"><v>3</v></c><c r="B3"><f t="shared" si="0"/><v>6</v></c></row>'
        "</sheetData></worksheet>"
    )
    salida = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(base)) as zin, zipfile.ZipFile(salida, "w") as zout:
        for info in zin.infolist():
            contenido = zin.read(info.filename)
            if info.filename == "xl/worksheets/sheet1.xml":
                contenido = hoja.encode("utf-8")
            zout.writestr(info, contenido)
    return salida.getvalue()


def test_formula_compartida_admite_valor_fijo_en_hijas_y_no_en_la_maestra():
    datos = _libro_con_formula_compartida()
    datos_out, inyecciones = _sembrar(datos, "valor_fijo", n=5)
    assert {i.celda for i in inyecciones} == {"B2", "B3"}
    with zipfile.ZipFile(io.BytesIO(datos_out)) as zf:
        xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert 'ref="B1:B3"' in xml and "A1*2" in xml
    assert 'si="0"/>' not in xml
    _, celdas = _celdas_libro(datos_out, data_only=False)
    assert celdas[("Hoja", "B1")][1] == "f"
    assert celdas[("Hoja", "B2")][1] == "n" and celdas[("Hoja", "B3")][1] == "n"


def test_formula_compartida_no_admite_otras_operaciones():
    datos = _libro_con_formula_compartida()
    for operacion in ("formula_borrada", "referencia_desplazada"):
        _, inyecciones = _sembrar(datos, operacion)
        assert inyecciones == [], operacion


def _taxonomia_toml(tmp_path: Path, operacion: str) -> Path:
    ruta = tmp_path / "tax.toml"
    ruta.write_text(
        f'[[categorias]]\nid = "T-01"\nnombre = "Prueba"\nfuente = "x"\n'
        f'operacion = "{operacion}"\npeso = 1.0\n',
        encoding="utf-8",
    )
    return ruta


def _args_cli(tmp_path: Path, n: int, *extra: str, salida: str = "salida") -> list[str]:
    origen = tmp_path / "pocas.xlsx"
    origen.write_bytes(_libro_xlsxwriter({"A1": (None, 2), "B1": ("=A1*2", 4), "B2": ("=A1*3", 6)}))
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    return [
        str(origen),
        "--taxonomia",
        str(_taxonomia_toml(tmp_path, "valor_fijo")),
        "--n",
        str(n),
        "--semilla",
        "1",
        "--salida",
        str(tmp_path / salida),
        "--raiz-repo",
        str(repo),
        *extra,
    ]


def test_cli_falla_si_se_siembran_menos_fallas_que_n(tmp_path: Path, capsys):
    codigo = inyector.main(_args_cli(tmp_path, 5))
    assert codigo != 0
    err = capsys.readouterr().err
    assert "2" in err and "5" in err and "--permitir-menos" in err


def test_cli_permite_menos_con_la_bandera(tmp_path: Path):
    assert inyector.main(_args_cli(tmp_path, 5, "--permitir-menos")) == 0
    assert inyector.main(_args_cli(tmp_path, 2, salida="otra")) == 0


# --- Ronda 2: referencias con hoja, numeración por encabezado, hija compartida ----------------


def _libro_hojas(hojas: dict[str, dict[str, tuple[str | None, object]]]) -> bytes:
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    for nombre, celdas in hojas.items():
        ws = wb.add_worksheet(nombre)
        for coord, (formula, valor) in celdas.items():
            if formula is not None:
                ws.write_formula(coord, formula, None, valor)
            elif isinstance(valor, str):
                ws.write_string(coord, valor)
            else:
                ws.write_number(coord, float(valor))
    wb.close()
    return buf.getvalue()


def _desplazar(datos: bytes, hoja: str):
    tax = _taxonomia_unica("referencia_desplazada", hojas=[hoja])
    return inyector.inyectar(datos, tax, n=1, semilla=3)[1]


def test_referencia_de_otra_hoja_no_se_desplaza_junto_con_la_local():
    datos = _libro_hojas({
        "Hoja": {"B4": (None, 1), "D1": ("=B4-OTRA!B4", 0)},
        "OTRA": {"B4": (None, 1)},
    })
    for semilla in range(8):
        tax = _taxonomia_unica("referencia_desplazada", hojas=["Hoja"])
        (inj,) = inyector.inyectar(datos, tax, n=1, semilla=semilla)[1]
        assert inj.despues in {"=B5-OTRA!B4", "=B4-OTRA!B5"}, inj.despues


def test_referencia_a_otra_hoja_no_es_circular_aunque_coincida_la_celda():
    # RESUMEN!B5 apunta a PRESUPUESTO!B4: desplazarla a PRESUPUESTO!B5 no es circular.
    datos = _libro_hojas({
        "PRESUPUESTO": {"B4": (None, 1)},
        "RESUMEN": {"B5": ("=PRESUPUESTO!B4+1", 2)},
    })
    (inj,) = _desplazar(datos, "RESUMEN")
    assert (inj.celda, inj.despues) == ("B5", "=PRESUPUESTO!B5+1")


def test_referencia_a_la_propia_hoja_con_prefijo_si_es_circular():
    datos = _libro_hojas({"RESUMEN": {"B4": (None, 1), "B5": ("=RESUMEN!B4+1", 2)}})
    assert _desplazar(datos, "RESUMEN") == []


def test_referencia_desplazada_agrupa_apariciones_con_y_sin_dolar():
    datos = _libro_hojas({"Hoja": {"B10": (None, 1), "D1": ('=IF($B10="","",B10)', 1)}})
    (inj,) = _desplazar(datos, "Hoja")
    assert inj.despues == '=IF($B11="","",B11)'


def test_formula_compartida_con_n_uno_cambia_una_hija_y_la_otra_sobrevive():
    datos = _libro_con_formula_compartida()
    datos_out, inyecciones = _sembrar(datos, "valor_fijo", n=1)
    (i,) = inyecciones
    assert i.celda in {"B2", "B3"}
    assert i.antes == f"=A{i.celda[1:]}*2"
    otra = "B3" if i.celda == "B2" else "B2"
    with zipfile.ZipFile(io.BytesIO(datos_out)) as zf:
        xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert f'<c r="{otra}"><f t="shared" si="0"/>' in xml
    assert 'ref="B1:B3"' in xml
