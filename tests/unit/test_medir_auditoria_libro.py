"""Herramienta local para medir la auditoría de un libro (anteproyecto v8, §8; plan del consejo).

Oráculos independientes del código: el kappa de Cohen se comprueba con el ejemplo publicado
(50 casos, acuerdo observado 0,70, esperado 0,50, kappa 0,40) y las tasas con cuentas hechas a
mano. Los libros son sintéticos (`tests/fixtures/libros_empresa.py`): ningún dato real.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest

from core.contracts.verificacion import Hallazgo, Severidad
from scripts import medir_auditoria_libro as m

# --- kappa de Cohen ------------------------------------------------------------------------------


def test_kappa_del_ejemplo_publicado():
    # 20 sí/sí, 5 sí/no, 10 no/sí, 15 no/no: po = 0,70; pe = 0,5·0,6 + 0,5·0,4 = 0,50; κ = 0,40.
    a = ["V"] * 20 + ["V"] * 5 + ["F"] * 10 + ["F"] * 15
    b = ["V"] * 20 + ["F"] * 5 + ["V"] * 10 + ["F"] * 15
    assert m.kappa_cohen(a, b) == pytest.approx(0.40)


def test_kappa_con_acuerdo_total_vale_uno():
    assert m.kappa_cohen(["V", "F", "V"], ["V", "F", "V"]) == pytest.approx(1.0)


def test_kappa_sin_variacion_no_se_puede_calcular():
    # Los dos ponen todo en la misma categoría: pe = 1 y el kappa queda indefinido.
    assert m.kappa_cohen(["V", "V"], ["V", "V"]) is None


def test_kappa_exige_listas_del_mismo_largo_y_no_vacias():
    with pytest.raises(ValueError):
        m.kappa_cohen(["V"], ["V", "F"])
    with pytest.raises(ValueError):
        m.kappa_cohen([], [])


# --- filas de la planilla ------------------------------------------------------------------------


def _h(regla: str, *origen: str, sev=Severidad.ERROR, impacto=None) -> Hallazgo:
    return Hallazgo(regla=regla, severidad=sev, descripcion=f"desc {regla}", impacto=impacto,
                    origen_ids=origen)


def test_filas_numeran_desde_uno_y_conservan_todas_las_celdas():
    filas = m.filas_de_hallazgos([_h("L1", "APU1!F12", "PRES!G10"), _h("R3", sev=Severidad.INFO)])
    assert [f.numero for f in filas] == [1, 2]
    assert filas[0].celdas == ("APU1!F12", "PRES!G10")
    assert filas[0].severidad == "ERROR"
    assert filas[1].celdas == ()


def test_las_reglas_no_aplicables_no_se_exportan_para_marcar():
    # R2 y R7 «no aplicable» salen en todo libro sin curva ni plan: no son errores que marcar.
    no_aplica = Hallazgo(
        regla="R2", severidad=Severidad.INFO,
        descripcion="R2 no aplicable: el presupuesto no declara curva de inversion",
    )
    filas = m.filas_de_hallazgos([no_aplica, _h("L1", "PRES!G10")])
    assert [(f.numero, f.regla) for f in filas] == [(1, "L1")]
    assert m.reglas_no_aplicables([no_aplica, _h("L1")]) == ["R2"]


# --- causa raíz ----------------------------------------------------------------------------------

_CRONO = ("CRONOGRAMA!D{f} (partida {p}) lee APU-0{p}!F23 (valor vacía) como rendimiento; el "
          "rendimiento de APU-0{p} está en APU-0{p}!F2{p} (valor 0,{p}5). Efecto: la duración da {p} d")


def _hd(regla: str, texto: str, *origen: str, sev=Severidad.ERROR) -> Hallazgo:
    return Hallazgo(regla=regla, severidad=sev, descripcion=texto, origen_ids=origen)


def test_la_misma_formula_copiada_es_una_sola_causa():
    # Dos partidas con la misma fórmula del CRONOGRAMA copiada con fila fija: una causa, dos casos.
    hallazgos = [
        _hd("L1", _CRONO.format(f=4, p=1), "CRONOGRAMA!D4"),
        _hd("L9", "PLAN DE PAGOS!B6 «Verificación» vale 40,00 USD", "PLAN DE PAGOS!B6"),
        _hd("L1", _CRONO.format(f=5, p=2), "CRONOGRAMA!D5", sev=Severidad.CRITICO),
    ]
    causas = m.causas_de_hallazgos(hallazgos)
    assert [(c.numero, c.regla, c.ocurrencias) for c in causas] == [(1, "L1", 2), (2, "L9", 1)]
    assert causas[0].celdas == ("CRONOGRAMA!D4", "CRONOGRAMA!D5")
    assert causas[0].severidad == "CRITICO"  # la más grave de sus casos


def test_reglas_distintas_con_el_mismo_texto_no_se_juntan():
    causas = m.causas_de_hallazgos([_hd("L5", "texto igual"), _hd("L6", "texto igual")])
    assert [c.regla for c in causas] == ["L5", "L6"]


def test_la_agrupacion_deja_fuera_lo_no_aplicable():
    no_aplica = _hd("R2", "R2 no aplicable: sin curva", sev=Severidad.INFO)
    assert m.causas_de_hallazgos([no_aplica]) == []


def test_un_sembrado_en_cualquier_caso_de_la_causa_cuenta_como_detectado():
    causas = m.causas_de_hallazgos([
        _hd("L1", _CRONO.format(f=4, p=1), "CRONOGRAMA!D4"),
        _hd("L1", _CRONO.format(f=5, p=2), "CRONOGRAMA!D5"),
    ])
    d = m.deteccion([m.Sembrado(1, "CRONOGRAMA!D5", "fila fija")], causas)
    assert d.por_sembrado == {1: 1}


def test_el_resumen_dice_cuantos_hallazgos_se_agruparon_en_cuantas_causas():
    texto = m.resumen(precision=m.precision({1: "Verdadero"}), deteccion=None,
                      exhaustividad=m.exhaustividad(1, 0), kappa=None, agrupacion=(3, 2))
    assert "3 hallazgos agrupados en 2 causas" in texto


def test_la_planilla_agrupada_conserva_las_ocurrencias(tmp_path: Path):
    carpeta = tmp_path / "medicion"
    carpeta.mkdir()
    ruta = carpeta / "p.xlsx"
    causas = m.causas_de_hallazgos([
        _hd("L1", _CRONO.format(f=4, p=1), "CRONOGRAMA!D4"),
        _hd("L1", _CRONO.format(f=5, p=2), "CRONOGRAMA!D5"),
    ])
    m.escribir_planilla(causas, ruta, raiz_repo=tmp_path / "repo")
    assert [(f.numero, f.ocurrencias, f.celdas) for f in m.leer_filas(ruta)] == \
        [(1, 2, ("CRONOGRAMA!D4", "CRONOGRAMA!D5"))]


# --- precisión, detección y exhaustividad --------------------------------------------------------


def test_precision_cuenta_solo_lo_marcado_y_declara_pendientes():
    marcas = {1: "Verdadero", 2: "Falso", 3: "Verdadero", 4: ""}
    p = m.precision(marcas)
    assert (p.aciertos, p.total, p.pendientes) == (2, 3, 1)
    assert p.valor == pytest.approx(2 / 3)


def test_precision_sin_nada_marcado_no_tiene_valor():
    assert m.precision({1: ""}).valor is None


def test_marca_desconocida_se_rechaza():
    with pytest.raises(ValueError, match="Quizás"):
        m.precision({1: "Quizás"})


def test_deteccion_por_celda_sin_importar_mayusculas_y_en_cualquier_origen():
    filas = m.filas_de_hallazgos([_h("L1", "PRES!G10", "apu1!f12"), _h("L4", "INSUMOS!C3")])
    sembrados = [
        m.Sembrado(numero=1, celda="APU1!F12", tipo="rendimiento"),
        m.Sembrado(numero=2, celda="APU2!D5", tipo="precio"),
    ]
    d = m.deteccion(sembrados, filas)
    assert (d.detectados, d.total) == (1, 2)
    assert d.por_sembrado == {1: 1, 2: None}


def test_deteccion_manual_manda_sobre_la_celda():
    filas = m.filas_de_hallazgos([_h("L1", "PRES!G10"), _h("L4", "INSUMOS!C3")])
    sembrados = [m.Sembrado(numero=1, celda="APU2!D5", tipo="precio", detectado_por=2)]
    d = m.deteccion(sembrados, filas)
    assert d.por_sembrado == {1: 2}
    assert d.manuales == 1


def test_deteccion_manual_con_numero_inexistente_se_rechaza():
    filas = m.filas_de_hallazgos([_h("L1", "PRES!G10")])
    with pytest.raises(ValueError, match="9"):
        m.deteccion([m.Sembrado(numero=1, celda="X!A1", tipo="t", detectado_por=9)], filas)


def test_exhaustividad_con_lo_que_se_le_escapo():
    e = m.exhaustividad(verdaderos=6, escapados=2)
    assert e.valor == pytest.approx(0.75)
    assert m.exhaustividad(verdaderos=0, escapados=0).valor is None


# --- formato de salida ---------------------------------------------------------------------------


def test_porcentaje_con_coma_decimal():
    assert m.porcentaje(2 / 3) == "66,7 %"
    assert m.porcentaje(None) == "sin dato"
    assert m.decimal_coma(0.4) == "0,40"


def test_resumen_no_trae_descripciones_ni_celdas():
    filas = m.filas_de_hallazgos([_h("L1", "PRES!G10")])
    texto = m.resumen(
        precision=m.precision({1: "Verdadero"}),
        deteccion=m.deteccion([m.Sembrado(1, "PRES!G10", "precio")], filas),
        exhaustividad=m.exhaustividad(1, 0),
        kappa=None,
    )
    assert "desc L1" not in texto and "PRES!G10" not in texto
    assert "100,0 %" in texto
    assert "kappa" in texto.lower()


# --- la planilla en disco ------------------------------------------------------------------------


@pytest.fixture
def fuera(tmp_path: Path) -> Path:
    return tmp_path / "medicion"


def test_planilla_ida_y_vuelta(fuera: Path):
    fuera.mkdir()
    ruta = fuera / "planilla.xlsx"
    filas = m.filas_de_hallazgos([_h("L1", "PRES!G10", impacto=Decimal("12.5")), _h("R3")])
    m.escribir_planilla(filas, ruta, raiz_repo=fuera.parent / "repo")
    libro = openpyxl.load_workbook(ruta)
    assert {"Instrucciones", "Hallazgos", "Se le escaparon"} <= set(libro.sheetnames)
    hoja = libro["Hallazgos"]
    encabezado = [c.value for c in hoja[1]]
    assert encabezado[:2] == ["N°", "Regla"] and "Veredicto" in encabezado
    assert any("Verdadero" in (v.formula1 or "") for v in hoja.data_validations.dataValidation)
    # el evaluador marca y anota un error que Sílice no vio
    col = encabezado.index("Veredicto") + 1
    hoja.cell(row=2, column=col, value="Verdadero")
    hoja.cell(row=3, column=col, value="Falso")
    libro["Se le escaparon"].append(["APU3!E8", "rendimiento inflado"])
    libro.save(ruta)
    marcas, escapados = m.leer_marcas(ruta)
    assert marcas == {1: "Verdadero", 2: "Falso"}
    assert escapados == 1


def test_no_escribe_dentro_del_repositorio(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    with pytest.raises(ValueError, match="repositorio"):
        m.escribir_planilla([], repo / "docs" / "p.xlsx", raiz_repo=repo)


def test_no_sobrescribe_una_planilla(fuera: Path):
    fuera.mkdir()
    ruta = fuera / "p.xlsx"
    ruta.write_bytes(b"ya marcada")
    with pytest.raises(FileExistsError):
        m.escribir_planilla([], ruta, raiz_repo=fuera.parent / "repo")


def test_clave_de_siembra_ida_y_vuelta(fuera: Path):
    fuera.mkdir()
    ruta = fuera / "clave.xlsx"
    m.escribir_clave_vacia(ruta, raiz_repo=fuera.parent / "repo")
    libro = openpyxl.load_workbook(ruta)
    hoja = libro["Sembrados"]
    hoja.append([1, "APU1!F12", "rendimiento", "de 0,5 a 5", None])
    hoja.append([2, "PRES!G10", "precio", "", 3])
    libro.save(ruta)
    assert m.leer_clave(ruta) == [
        m.Sembrado(1, "APU1!F12", "rendimiento"),
        m.Sembrado(2, "PRES!G10", "precio", detectado_por=3),
    ]


# --- de punta a punta con un libro sintético -----------------------------------------------------


def test_exportar_un_libro_sintetico_con_errores_sembrados(fuera: Path):
    import hashlib

    from fusion.proceso import procesar_libro
    from tests.fixtures.libros_empresa import APUS_LIMPIOS, Siembra, construir_libro

    datos = construir_libro(APUS_LIMPIOS, Siembra(resumen_ref_rota=True, procura_dif=Decimal("5"))
                            ).datos
    esperados = procesar_libro(datos, "libro.xlsx",
                               fecha_devolucion=date(2026, 10, 13)).informe.hallazgos
    assert esperados  # la siembra produce hallazgos: si no, la prueba no prueba nada
    fuera.mkdir()
    origen = fuera / "libro.xlsx"
    origen.write_bytes(datos)
    destino = fuera / "planilla.xlsx"
    codigo = m.main(["exportar", str(origen), "--salida", str(destino), "--sin-agrupar",
                     "--fecha", "2026-10-13", "--raiz-repo", str(fuera.parent / "repo")])
    assert codigo == 0
    filas = m.leer_filas(destino)
    a_marcar = [h for h in esperados if "no aplicable" not in h.descripcion]
    assert [(f.regla, f.celdas) for f in filas] == [(h.regla, h.origen_ids) for h in a_marcar]
    instrucciones = [c.value for c in openpyxl.load_workbook(destino)["Instrucciones"]["A"]]
    assert f"SHA-256 del libro auditado: {hashlib.sha256(datos).hexdigest()}" in instrucciones
    marcas, escapados = m.leer_marcas(destino)
    assert set(marcas.values()) == {""} and escapados == 0  # nada marcado todavía


def test_calcular_desde_la_linea_de_comandos(fuera: Path, capsys):
    fuera.mkdir()
    filas = m.filas_de_hallazgos([_h("L1", "PRES!G10"), _h("L4", "INSUMOS!C3")])
    a, b = fuera / "a.xlsx", fuera / "b.xlsx"
    for ruta, marcas in ((a, ["Verdadero", "Falso"]), (b, ["Verdadero", "Verdadero"])):
        m.escribir_planilla(filas, ruta, raiz_repo=fuera.parent / "repo")
        libro = openpyxl.load_workbook(ruta)
        hoja = libro["Hallazgos"]
        col = [c.value for c in hoja[1]].index("Veredicto") + 1
        for i, v in enumerate(marcas, start=2):
            hoja.cell(row=i, column=col, value=v)
        libro.save(ruta)
    assert m.main(["calcular", "--planilla", str(a), "--otra", str(b)]) == 0
    salida = capsys.readouterr().out
    assert "50,0 %" in salida  # precisión de la planilla principal: 1 de 2
    assert "Hallazgos marcados por los dos: 2" in salida


def test_fecha_iso_del_libro():
    assert m.fecha_iso("2026-10-13") == date(2026, 10, 13)
