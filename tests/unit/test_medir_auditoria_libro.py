"""Herramienta local para medir la auditoría de un libro (anteproyecto v8, §8; plan del consejo).

Oráculos independientes del código: el kappa de Cohen se comprueba con el ejemplo publicado
(50 casos, acuerdo observado 0,70, esperado 0,50, kappa 0,40) y las tasas con cuentas hechas a
mano. Los libros son sintéticos (`tests/fixtures/libros_empresa.py`): ningún dato real.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from fractions import Fraction
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
    return Hallazgo(
        regla=regla, severidad=sev, descripcion=f"desc {regla}", impacto=impacto, origen_ids=origen
    )


def test_filas_numeran_desde_uno_y_conservan_todas_las_celdas():
    filas = m.filas_de_hallazgos([_h("L1", "APU1!F12", "PRES!G10"), _h("R3", sev=Severidad.INFO)])
    assert [f.numero for f in filas] == [1, 2]
    assert filas[0].celdas == ("APU1!F12", "PRES!G10")
    assert filas[0].severidad == "ERROR"
    assert filas[1].celdas == ()


def test_las_reglas_no_aplicables_no_se_exportan_para_marcar():
    # R2 y R7 «no aplicable» salen en todo libro sin curva ni plan: no son errores que marcar.
    no_aplica = Hallazgo(
        regla="R2",
        severidad=Severidad.INFO,
        descripcion="R2 no aplicable: el presupuesto no declara curva de inversion",
    )
    filas = m.filas_de_hallazgos([no_aplica, _h("L1", "PRES!G10")])
    assert [(f.numero, f.regla) for f in filas] == [(1, "L1")]
    assert m.reglas_no_aplicables([no_aplica, _h("L1")]) == ["R2"]


# --- causa raíz ----------------------------------------------------------------------------------

_CRONO = (
    "CRONOGRAMA!D{f} (partida {p}) lee APU-0{p}!F23 (valor vacía) como rendimiento; el "
    "rendimiento de APU-0{p} está en APU-0{p}!F2{p} (valor 0,{p}5). "
    "Efecto: la duración da {p} d"
)


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


def test_los_detalles_de_cada_caso_no_parten_la_causa():
    # La causa es la primera cláusula: qué lee y de dónde. Lo que deja sin leer en cada APU o el
    # valor que encontró en la celda equivocada son detalles del caso, no otra causa.
    aux = (
        "AUX lee de APU-0{n} las filas fijas 10-17, 22-26, 34-37 para la lista de compras; deja "
        "sin leer {lista}. Efecto: PROCURA compra de menos"
    )
    crono = (
        "CRONOGRAMA!D{n} (partida {n}) lee APU-0{n}!F23 (valor {v}) como rendimiento; el "
        "rendimiento de APU-0{n} está en APU-0{n}!F25 (valor 0,5)."
    )
    causas = m.causas_de_hallazgos(
        [
            _hd("L1", aux.format(n=1, lista="1 línea(s): EQ-03 (fila 38)")),
            _hd(
                "L1",
                aux.format(
                    n=2, lista="3 línea(s): MO-03 (fila 27), MO-05 (fila 28), EQ-03 (fila 38)"
                ),
            ),
            _hd("L1", crono.format(n=4, v="vacía")),
            _hd("L1", crono.format(n=5, v="0,75")),
            _hd("L1", crono.format(n=6, v="«Costo/día (USD)»")),
        ]
    )
    assert [c.ocurrencias for c in causas] == [2, 3]


def test_reglas_distintas_con_el_mismo_texto_no_se_juntan():
    causas = m.causas_de_hallazgos([_hd("L5", "texto igual"), _hd("L6", "texto igual")])
    assert [c.regla for c in causas] == ["L5", "L6"]


def test_la_agrupacion_deja_fuera_lo_no_aplicable():
    no_aplica = _hd("R2", "R2 no aplicable: sin curva", sev=Severidad.INFO)
    assert m.causas_de_hallazgos([no_aplica]) == []


def test_un_sembrado_en_cualquier_caso_de_la_causa_cuenta_como_detectado():
    causas = m.causas_de_hallazgos(
        [
            _hd("L1", _CRONO.format(f=4, p=1), "CRONOGRAMA!D4"),
            _hd("L1", _CRONO.format(f=5, p=2), "CRONOGRAMA!D5"),
        ]
    )
    d = m.deteccion([m.Sembrado(1, "CRONOGRAMA!D5", "fila fija")], causas)
    assert d.por_sembrado == {1: 1}


def test_el_resumen_dice_cuantos_hallazgos_se_agruparon_en_cuantas_causas():
    texto = m.resumen(
        precision=m.precision({1: "Verdadero"}),
        deteccion=None,
        exhaustividad=m.exhaustividad(1, 0),
        kappa=None,
        agrupacion=(3, 2),
    )
    assert "3 hallazgos agrupados en 2 causas" in texto


def test_la_planilla_agrupada_conserva_las_ocurrencias(tmp_path: Path):
    carpeta = tmp_path / "medicion"
    carpeta.mkdir()
    ruta = carpeta / "p.xlsx"
    causas = m.causas_de_hallazgos(
        [
            _hd("L1", _CRONO.format(f=4, p=1), "CRONOGRAMA!D4"),
            _hd("L1", _CRONO.format(f=5, p=2), "CRONOGRAMA!D5"),
        ]
    )
    m.escribir_planilla(causas, ruta, raiz_repo=tmp_path / "repo")
    assert [(f.numero, f.ocurrencias, f.celdas) for f in m.leer_filas(ruta)] == [
        (1, 2, ("CRONOGRAMA!D4", "CRONOGRAMA!D5"))
    ]


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


@pytest.mark.parametrize("orden", ["clave", "revision"])
def test_las_demas_ordenes_tampoco_sobrescriben_y_dan_2(
    fuera: Path, orden: str, capsys: pytest.CaptureFixture[str]
):
    """Auditoría antes de medicion-v1 (#11): sin traza de Python, con el mensaje y el código 2."""
    from tests.fixtures.libros_empresa import libro_limpio

    fuera.mkdir()
    origen = fuera / "obra.xlsx"
    origen.write_bytes(libro_limpio().datos)
    existente = fuera / "ya.xlsx"
    existente.write_bytes(b"x")
    libro = [str(origen)] if orden == "revision" else []
    codigo = m.main(
        [orden, *libro, "--salida", str(existente), "--raiz-repo", str(fuera.parent / "repo")]
    )
    assert codigo == 2
    assert "ya existe; no se sobrescribe una planilla" in capsys.readouterr().out
    assert existente.read_bytes() == b"x"


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

    datos = construir_libro(
        APUS_LIMPIOS, Siembra(resumen_ref_rota=True, procura_dif=Decimal("5"))
    ).datos
    esperados = procesar_libro(
        datos, "libro.xlsx", fecha_devolucion=date(2026, 10, 13)
    ).informe.hallazgos
    assert esperados  # la siembra produce hallazgos: si no, la prueba no prueba nada
    fuera.mkdir()
    origen = fuera / "libro.xlsx"
    origen.write_bytes(datos)
    destino = fuera / "planilla.xlsx"
    codigo = m.main(
        [
            "exportar",
            str(origen),
            "--salida",
            str(destino),
            "--sin-agrupar",
            "--fecha",
            "2026-10-13",
            "--raiz-repo",
            str(fuera.parent / "repo"),
        ]
    )
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


# --- Wilson, redondeo HALF_UP y criterio de fracaso (2026-11-25) ---------------------------------


def test_intervalo_de_wilson_con_los_oraculos_a_mano():
    assert m.intervalo_wilson(12, 24) == "[31,4 %; 68,6 %]"
    assert m.intervalo_wilson(0, 24) == "[0,0 %; 13,8 %]"
    assert m.intervalo_wilson(24, 24) == "[86,2 %; 100,0 %]"
    assert m.intervalo_wilson(0, 0) == "sin dato"


def test_decimal_coma_redondea_half_up_con_decimal():
    assert m.decimal_coma(0.125, 2) == "0,13"  # f"{0.125:.2f}" daría 0,12 (mitad al par)
    assert m.decimal_coma(2.5, 0) == "3"
    assert m.porcentaje(0.00125) == "0,1 %"


def _deteccion_de(detectados: int, total: int) -> m.Deteccion:
    return m.Deteccion(
        por_sembrado={i: (1 if i <= detectados else None) for i in range(1, total + 1)}
    )


def test_el_resumen_trae_wilson_y_evalua_el_criterio_de_fracaso():
    marcas = {i: ("Verdadero" if i <= 5 else "Falso") for i in range(1, 11)}
    texto = m.resumen(
        precision=m.precision(marcas),
        deteccion=_deteccion_de(12, 24),
        exhaustividad=m.exhaustividad(5, 0),
        kappa=0.3,
    )
    assert "[31,4 %; 68,6 %]" in texto  # detección 12 de 24
    assert "[23,7 %; 76,3 %]" in texto  # falsos positivos 5 de 10
    assert (
        "Detección < 50 % (señalado por Sílice): NO se cumple" in texto
    )  # 50,0 % no es menor que 50 %
    assert "Falsos positivos > 40 %: SE CUMPLE" in texto
    # el 0,3 es entre dos evaluadores: no decide el criterio del kappa experto–Sílice
    assert "Kappa experto–Sílice < 0,4: no se puede calcular" in texto
    assert "todas las fallas a la vez" in texto


def test_el_criterio_dice_cuando_no_se_puede_calcular_una_condicion():
    texto = m.resumen(
        precision=m.precision({1: "Verdadero"}),
        deteccion=None,
        exhaustividad=m.exhaustividad(1, 0),
        kappa=None,
    )
    assert "Detección < 50 % (señalado por Sílice): no se puede calcular" in texto
    assert "Kappa experto–Sílice < 0,4: no se puede calcular" in texto
    assert "Falsos positivos > 40 %: NO se cumple" in texto  # 0 de 1


# --- la celda se compara normalizada -------------------------------------------------------------


def test_celda_normaliza_comillas_de_hoja_mayusculas_y_dolares():
    assert m._celda("'PLAN DE PAGOS'!B6") == m._celda("plan de pagos!$b$6")
    assert m._celda("'O''Brien'!A1") == m._celda("O'Brien!A1")
    assert m._celda(" 'APU-01'!$G$12 ") == m._celda("apu-01!g12")
    assert m._celda("'PLAN DE PAGOS'!B6") != m._celda("'PLAN DE PAGOS'!B7")


def test_deteccion_encuentra_la_celda_citada_con_comillas():
    filas = m.filas_de_hallazgos([_h("L1", "'PLAN DE PAGOS'!B6")])
    d = m.deteccion([m.Sembrado(1, "PLAN DE PAGOS!B6", "t")], filas)
    assert d.por_sembrado == {1: 1}


# --- señalado por Sílice y confirmado por el evaluador -------------------------------------------


def test_deteccion_separa_senalado_de_confirmado_verdadero():
    filas = m.filas_de_hallazgos([_h("L1", "A!B1"), _h("L2", "A!B2"), _h("L3", "A!B3")])
    sembrados = [
        m.Sembrado(1, "A!B1", "t"),
        m.Sembrado(2, "A!B2", "t"),
        m.Sembrado(3, "A!B3", "t"),
        m.Sembrado(4, "A!B4", "t"),
    ]
    d = m.deteccion(sembrados, filas, marcas={1: "Verdadero", 2: "Falso", 3: ""})
    assert d.detectados == 3  # señalados por Sílice
    assert d.confirmados == 1  # el evaluador los dio por verdaderos
    assert d.marcados_falsos == 1
    assert m.deteccion(sembrados, filas).confirmados is None


def test_el_resumen_informa_senalado_y_confirmado():
    filas = m.filas_de_hallazgos([_h("L1", "A!B1"), _h("L2", "A!B2")])
    d = m.deteccion(
        [m.Sembrado(1, "A!B1", "t"), m.Sembrado(2, "A!B2", "t")],
        filas,
        marcas={1: "Verdadero", 2: "Falso"},
    )
    texto = m.resumen(
        precision=m.precision({1: "Verdadero", 2: "Falso"}),
        deteccion=d,
        exhaustividad=m.exhaustividad(1, 0),
        kappa=None,
    )
    assert "señalado por Sílice" in texto
    assert "señalado y confirmado verdadero" in texto


# --- el destino seguro también desde un worktree -------------------------------------------------


def test_destino_seguro_rechaza_el_checkout_principal_desde_un_worktree(tmp_path: Path):
    principal = tmp_path / "TESIS"
    admin = principal / ".git" / "worktrees" / "s4"
    admin.mkdir(parents=True)
    arbol = principal / ".worktrees" / "s4"
    arbol.mkdir(parents=True)
    (arbol / ".git").write_text(f"gitdir: {admin.as_posix()}\n", encoding="utf-8")
    (principal / "docs").mkdir()
    with pytest.raises(ValueError, match="repositorio"):
        m._destino_seguro(principal / "docs" / "p.xlsx", arbol)
    with pytest.raises(ValueError, match="repositorio"):
        m._destino_seguro(arbol / "p.xlsx", arbol)
    fuera = tmp_path / "medicion" / "p.xlsx"
    assert m._destino_seguro(fuera, arbol) == fuera.resolve()


# --- exportar con recálculo previo ---------------------------------------------------------------


class _Espia:
    def __init__(self) -> None:
        self.llamadas: list[str] = []

    def version(self) -> str:
        return "falso"

    def recalcular(self, datos: bytes, nombre: str) -> bytes:
        self.llamadas.append(nombre)
        return datos


def test_exportar_recalcula_y_trasplanta_solo_si_se_pide(fuera: Path):
    from tests.fixtures.libros_empresa import libro_limpio

    fuera.mkdir()
    origen = fuera / "obra.xlsx"
    origen.write_bytes(libro_limpio().datos)
    repo = str(fuera.parent / "repo")
    espia = _Espia()
    base = ["--fecha", "2026-10-13", "--raiz-repo", repo]
    assert (
        m.main(
            ["exportar", str(origen), "--salida", str(fuera / "a.xlsx"), *base], recalculador=espia
        )
        == 0
    )
    assert espia.llamadas == []
    assert (
        m.main(
            ["exportar", str(origen), "--salida", str(fuera / "b.xlsx"), "--recalcular", *base],
            recalculador=espia,
        )
        == 0
    )
    assert espia.llamadas == ["obra.xlsx"]
    hoja = openpyxl.load_workbook(fuera / "b.xlsx")["Instrucciones"]
    assert "Recalculado con LibreOffice y valores trasplantados: sí" in [c.value for c in hoja["A"]]


def test_calcular_imprime_wilson_y_criterio(fuera: Path, capsys):
    fuera.mkdir()
    filas = m.filas_de_hallazgos([_h("L1", "A!B1"), _h("L4", "A!B2")])
    ruta = fuera / "a.xlsx"
    m.escribir_planilla(filas, ruta, raiz_repo=fuera.parent / "repo")
    libro = openpyxl.load_workbook(ruta)
    hoja = libro["Hallazgos"]
    col = [c.value for c in hoja[1]].index("Veredicto") + 1
    hoja.cell(row=2, column=col, value="Verdadero")
    hoja.cell(row=3, column=col, value="Falso")
    libro.save(ruta)
    # la detección con --clave exige los libros (tests/unit/test_medir_partidas.py)
    assert m.main(["calcular", "--planilla", str(ruta)]) == 0
    salida = capsys.readouterr().out
    assert "[9,5 %; 90,5 %]" in salida  # falsos positivos 1 de 2 con Wilson
    assert "Falsos positivos > 40 %: SE CUMPLE" in salida


# --- ronda 2: frontera exacta, porcentajes, marcas y destino (2026-11-25) -----------------


def _marcas_con_kappa_dos_quintos() -> tuple[list[str], list[str]]:
    # 6 casos: acuerdo observado 4/6 y esperado 1/2 -> kappa exacto 2/5; en float da 0,39999...
    a = ["V", "V", "F", "F", "F", "F"]
    b = ["V", "V", "V", "V", "F", "F"]
    return a, b


def test_kappa_en_la_frontera_exacta_no_declara_fracaso():
    a, b = _marcas_con_kappa_dos_quintos()
    exacto = m.kappa_exacto(a, b)
    assert exacto == Fraction(2, 5)
    linea = "Kappa experto–Sílice < 0,4"
    assert f"{linea}: NO se cumple" in m.criterio_de_fracaso(kappa_experto=exacto)
    # aunque quien llame pase el float con su error de redondeo
    assert f"{linea}: NO se cumple" in m.criterio_de_fracaso(kappa_experto=m.kappa_cohen(a, b))
    assert f"{linea}: SE CUMPLE" in m.criterio_de_fracaso(kappa_experto=0.39)


def test_porcentaje_convierte_a_decimal_antes_de_multiplicar():
    assert m.porcentaje(29 / 400) == "7,3 %"  # 0,0725 * 100 en float da 7,2499...
    assert m.porcentaje(0.0025) == "0,3 %"
    assert m.porcentaje_de(29, 400) == "7,3 %"
    assert m.porcentaje_de(1, 0) == "sin dato"


def test_fronteras_exactas_del_criterio_de_fracaso():
    def estado(**kw):
        return m.criterio_de_fracaso(**kw)

    assert "Detección < 50 % (señalado por Sílice): SE CUMPLE" in estado(deteccion=(11, 24))
    assert "Detección < 50 % (señalado por Sílice): NO se cumple" in estado(deteccion=(12, 24))
    assert "Falsos positivos > 40 %: NO se cumple" in estado(falsos=(4, 10))  # 40 no es más de 40
    assert "Falsos positivos > 40 %: SE CUMPLE" in estado(falsos=(5, 10))
    assert "Falsos positivos > 40 %: SE CUMPLE" in estado(falsos=(41, 100))


def test_con_marcas_el_criterio_cuenta_solo_lo_confirmado_verdadero():
    d = m.Deteccion(
        por_sembrado={i: (1 if i <= 12 else None) for i in range(1, 25)},
        confirmados=11,
        marcados_falsos=1,
    )
    texto = m.resumen(
        precision=m.precision({1: "Verdadero"}),
        deteccion=d,
        exhaustividad=m.exhaustividad(1, 0),
        kappa=None,
    )
    assert "Detección < 50 % (confirmado verdadero por el evaluador): SE CUMPLE" in texto
    assert "señalado por Sílice" in texto  # lo señalado se informa al lado


def test_si_varias_filas_citan_la_celda_se_prioriza_la_marcada_verdadero():
    filas = m.filas_de_hallazgos([_h("L1", "A!B1"), _h("L2", "A!B1")])
    d = m.deteccion([m.Sembrado(1, "A!B1", "t")], filas, marcas={1: "Falso", 2: "Verdadero"})
    assert d.por_sembrado == {1: 2}
    assert d.confirmados == 1
    sin = m.deteccion([m.Sembrado(1, "A!B1", "t")], filas, marcas={1: "", 2: ""})
    assert sin.por_sembrado == {1: 1}


def test_destino_seguro_rechaza_otro_clon_o_worktree_ajeno(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    clon = tmp_path / "otro_clon"
    (clon / ".git").mkdir(parents=True)
    with pytest.raises(ValueError, match="repositorio"):
        m._destino_seguro(clon / "sub" / "p.xlsx", repo)
    ajeno = tmp_path / "ajeno"
    ajeno.mkdir()
    (ajeno / ".git").write_text("gitdir: /otro/lugar\n", encoding="utf-8")
    with pytest.raises(ValueError, match="repositorio"):
        m._destino_seguro(ajeno / "p.xlsx", repo)


def _formula_con_valor(datos: bytes) -> tuple[str, str]:
    import io

    formulas = openpyxl.load_workbook(io.BytesIO(datos))
    valores = openpyxl.load_workbook(io.BytesIO(datos), data_only=True)
    for ws in formulas:
        for fila in ws.iter_rows():
            for c in fila:
                v = valores[ws.title][c.coordinate].value
                if (
                    isinstance(c.value, str)
                    and c.value.startswith("=")
                    and isinstance(v, int | float)
                ):
                    return ws.title, c.coordinate
    raise AssertionError("el libro de prueba no trae fórmulas con valor")


def test_exportar_con_recalcular_audita_el_libro_trasplantado(
    fuera: Path, monkeypatch: pytest.MonkeyPatch
):
    import io

    from tests.fixtures.libros_empresa import libro_limpio
    from tests.fixtures.recalculo_falso import LibreOfficeFalso

    datos = libro_limpio().datos
    hoja, coord = _formula_con_valor(datos)

    class _Cambia(LibreOfficeFalso):
        def recalcular(self, datos: bytes, nombre: str) -> bytes:
            libro = openpyxl.load_workbook(io.BytesIO(super().recalcular(datos, nombre)))
            libro[hoja][coord].value = 987654
            salida = io.BytesIO()
            libro.save(salida)
            return salida.getvalue()

    recibidos: list[bytes] = []
    import fusion.proceso as proceso

    real = proceso.procesar_libro

    def espiar(datos_auditados, *a, **k):
        recibidos.append(datos_auditados)
        return real(datos_auditados, *a, **k)

    monkeypatch.setattr(proceso, "procesar_libro", espiar)
    fuera.mkdir()
    origen = fuera / "obra.xlsx"
    origen.write_bytes(datos)
    args = ["--fecha", "2026-10-13", "--raiz-repo", str(fuera.parent / "repo")]
    assert m.main(["exportar", str(origen), "--salida", str(fuera / "c.xlsx"), "--recalcular",
                   *args], recalculador=_Cambia()) == 0  # fmt: skip
    (auditado,) = recibidos
    nuevo = openpyxl.load_workbook(io.BytesIO(auditado), data_only=True)[hoja][coord].value
    assert nuevo == 987654  # el valor recalculado se trasplantó
    assert openpyxl.load_workbook(io.BytesIO(auditado))[hoja][coord].value == (
        openpyxl.load_workbook(io.BytesIO(datos))[hoja][coord].value
    )  # y la fórmula original quedó


def test_exportar_revisa_el_destino_antes_de_recalcular_y_sin_libreoffice_da_2(
    fuera: Path, capsys: pytest.CaptureFixture[str]
):
    from aplicacion.oraculo_hoja import LibreOfficeNoDisponibleError
    from tests.fixtures.libros_empresa import libro_limpio

    fuera.mkdir()
    origen = fuera / "obra.xlsx"
    origen.write_bytes(libro_limpio().datos)
    existente = fuera / "ya.xlsx"
    existente.write_bytes(b"x")
    espia = _Espia()
    comun = ["--recalcular", "--fecha", "2026-10-13", "--raiz-repo", str(fuera.parent / "repo")]
    # Negarse a sobrescribir es un mensaje y el código 2, no una traza (auditoría, #11).
    codigo = m.main(["exportar", str(origen), "--salida", str(existente), *comun],
                    recalculador=espia)  # fmt: skip
    assert codigo == 2
    assert "ya existe; no se sobrescribe una planilla" in capsys.readouterr().out
    assert espia.llamadas == []  # no recalculó para después negarse a escribir

    class _Sin:
        def recalcular(self, datos: bytes, nombre: str) -> bytes:
            raise LibreOfficeNoDisponibleError("No se encontró LibreOffice (soffice).")

    codigo = m.main(["exportar", str(origen), "--salida", str(fuera / "n.xlsx"), *comun],
                    recalculador=_Sin())  # fmt: skip
    assert codigo == 2
    assert "LibreOffice" in capsys.readouterr().out
