"""La medición por errores sembrados (S3 §11.5, §13.5 b; RF-89): el catálogo, el plano limpio y la
tasa de detección. Meta ratificada por Eugenio (P8): 100 % de lo detectable y 0 falsas alarmas."""

from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from scripts import medir_deteccion_planos as medicion
from scripts import sembrar_errores_planos as siembra

RAIZ = Path(__file__).resolve().parents[2]
LIMPIO = RAIZ / "tests" / "fixtures" / "errores_planos" / "of001_limpio.py"
FORMAS = ("estado", "item", "regla", "r16", "ninguna")


@pytest.fixture(scope="module")
def medida() -> dict:
    return medicion.medir()


def test_el_catalogo_y_las_siembras_tienen_los_mismos_ids() -> None:
    assert set(siembra.catalogo()) == set(siembra.SIEMBRAS)
    assert len(siembra.catalogo()) == 17


def test_cada_fila_del_catalogo_declara_una_deteccion_con_una_forma_conocida() -> None:
    for fila in siembra.catalogo().values():
        assert fila.deteccion, fila.id
        for etiqueta in (*fila.deteccion, *fila.consecuencias):
            for alternativa in etiqueta.split("|"):
                assert alternativa.split(":")[0] in FORMAS, (fila.id, alternativa)
        assert fila.autor in {"P", "A"}
        assert (fila.deteccion == ("ninguna",)) is (not fila.detectable), fila.id


def test_el_catalogo_tiene_tres_controles_y_casi_todo_escrito_sin_ver_el_codigo() -> None:
    filas = siembra.catalogo().values()
    assert sorted(f.id for f in filas if not f.detectable) == [
        "NO-DET-LUCES", "NO-DET-PERMUTA", "NO-DET-TRASLADO"]
    assert sum(1 for f in filas if f.autor == "P") >= 10  # la mayoría, escrita por pruebas


def test_el_plano_limpio_da_el_conjunto_exacto_escrito_en_s3_0() -> None:
    literal = runpy.run_path(str(LIMPIO))["LIMPIO"]
    for formato in ("dxf", "ifc"):
        auditoria = medicion.auditar(siembra.limpio(formato), formato)
        assert auditoria.items == literal[formato]["items"]
        assert auditoria.hallazgos == literal[formato]["hallazgos"]


def test_of001_limpio_no_da_hallazgos_de_r9_r10_ni_r15_y_8_de_r8() -> None:
    hallazgos = medicion.auditar(siembra.limpio("dxf"), "dxf").hallazgos
    reglas = [h[0] for h in hallazgos]
    assert reglas == ["R8"] * 8 and all(h[1] == "ADVERTENCIA" for h in hallazgos)
    assert len(medicion.auditar(siembra.limpio("dxf"), "dxf").items) == 15


def test_la_deteccion_es_total_sin_falsas_alarmas_y_los_controles_no_se_detectan(medida) -> None:
    assert medida["tasa"] == 1 and medida["falsas_alarmas"] == 0
    assert medida["no_detectables"] == 5 and medida["no_detectados"] == 5
    for id_, c in medida["categorias"].items():
        if c["detectables"]:
            assert c["detectados"] == c["sembrados"], id_
            assert c["falsas_alarmas"] == 0, id_


def test_la_tabla_dice_la_tasa_y_las_falsas_alarmas(medida) -> None:
    texto = medicion.tabla(medida)
    assert "Tasa de detección: 100%." in texto and "Falsas alarmas: 0." in texto
    assert texto.count("\n| ") == 17


def test_ningun_error_sembrado_da_r9_y_r15_a_la_vez() -> None:
    base = medicion.auditar(siembra.limpio("dxf"), "dxf")
    for id_, s in siembra.SIEMBRAS.items():
        if s.formato != "dxf":
            continue
        for variante in range(s.variantes):
            sembrado = siembra.sembrar(id_, variante)
            nuevos = medicion.agregado(
                medicion.auditar(sembrado.contenido, "dxf"), base, None).hallazgos
            reglas = {h[0] for h in nuevos}
            assert not {"R9", "R15"} <= reglas, (id_, variante, reglas)


def test_la_siembra_es_determinista_y_la_semilla_la_cambia() -> None:
    a, b = siembra.sembrar("CAPA-EQUIVOCADA", 1), siembra.sembrar("CAPA-EQUIVOCADA", 1)
    assert a.detalle == b.detalle and a.id == b.id
    otros = {siembra.sembrar("CAPA-EQUIVOCADA", v).detalle for v in range(3)}
    assert len(otros) >= 2  # las variantes no repiten siempre el mismo elemento
    por_semilla = {siembra.sembrar("FUERA-DE-AMBIENTE", 0, semilla=s).detalle for s in range(40)}
    assert len(por_semilla) > 1


def test_si_r15_dejara_de_funcionar_la_medicion_lo_nota(monkeypatch) -> None:
    from adapters.espacio.planos import geometria_plano

    monkeypatch.setattr(geometria_plano, "reglas_plano", lambda espacio: ())
    roto = medicion.medir()
    assert roto["tasa"] < 1
    perdidas = {i for i, c in roto["categorias"].items()
                if c["detectables"] and c["detectados"] < c["sembrados"]}
    assert perdidas == {"ESCALA-X1000", "SUPERPUESTO", "PUNTO-DUPLICADO"}


def test_la_salida_json_trae_la_semilla_y_el_plano_limpio(capsys) -> None:
    assert medicion.main(["--json"]) == 0
    datos = json.loads(capsys.readouterr().out)
    assert datos["semilla"] == siembra.SEMILLA == 42 and datos["tasa"] == 1
    assert len(datos["limpio"]["dxf"]["items"]) == 15
