"""Lector del libro de la empresa: `.xlsx` -> `LibroLeido` (Silice 1.5, RF-101; spec F-D3, F-D6).

El libro de entrada es sintético (`tests/fixtures/libros_empresa.py`), con la estructura de la
plantilla: PORTADA, INSUMOS con nombres definidos, un APU por partida con `VLOOKUP` a `PRECIOS`,
PRESUPUESTO con `INDIRECT`… Los libros reales no se usan (NORMAS §1).

Oráculo: la memoria de cálculo a mano del fixture (`MEMORIA`) y las celdas literales del libro
generado (la plantilla tiene los APU de formas distintas: el P.U. de APU-01 está en G45, el de
APU-02 en G40 y el de APU-03 en G41; el lector los encuentra por rótulo, no por fila fija).
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from decimal import Decimal

import pytest

from adapters.hoja_empresa.guardia import ArchivoRechazado
from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.modelo import (
    VINCULO_ILEGIBLE,
    Celda,
    Rotulo,
    TipoFilaEspecial,
    TipoInsumo,
)
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    MEMORIA,
    D,
    Siembra,
    con,
    construir_libro,
    libro_limpio,
)

NOMBRE = "libro_sintetico.xlsx"


@pytest.fixture(scope="module")
def limpio():
    c = libro_limpio()
    return c, leer_libro(c.datos, NOMBRE)


# --- Parámetros, INSUMOS y PORTADA -------------------------------------------------------------


def test_parametros_por_nombre_definido_con_su_celda(limpio):
    _, libro = limpio
    p = libro.parametros
    assert (p.fcas, p.herramientas, p.administracion, p.utilidad, p.iva) == (
        D("1.9"),
        D("0.05"),
        D("0.10"),
        D("0.10"),
        D("0.16"),
    )
    assert (p.capacidad_camion, p.flete, p.tarifa_vertedero) == (D("6"), D("60"), D("2"))
    # Sección 4 de INSUMOS: FCAS en E16 … VERT en E23 (filas del libro generado).
    esperadas = {
        "FCAS": "E16",
        "HERR": "E17",
        "ADMON": "E18",
        "UTIL": "E19",
        "IVA": "E20",
        "CAMION": "E21",
        "FLETE": "E22",
        "VERT": "E23",
    }
    assert {k: (c.hoja, c.ref) for k, c in p.celdas.items()} == {
        k: ("INSUMOS", ref) for k, ref in esperadas.items()
    }


def test_parametro_sin_nombre_definido_vale_cero_y_no_tiene_celda():
    c = construir_libro(siembra=Siembra(sin_parametros=("VERT",)))
    libro = leer_libro(c.datos, NOMBRE)
    assert libro.parametros.tarifa_vertedero == 0
    assert "VERT" not in libro.parametros.celdas


def test_insumos_con_codigo_tipo_precio_fuente_y_celda(limpio):
    _, libro = limpio
    assert [(i.codigo, i.tipo, i.precio, i.celda.ref) for i in libro.insumos] == [
        ("MT-01", TipoInsumo.MATERIAL, D("10"), "E5"),
        ("MT-02", TipoInsumo.MATERIAL, D("25"), "E6"),
        ("MT-03", TipoInsumo.MATERIAL, D("0.8"), "E7"),
        ("MO-01", TipoInsumo.MANO_OBRA, D("20"), "E8"),
        ("MO-02", TipoInsumo.MANO_OBRA, D("15"), "E9"),
        ("MO-03", TipoInsumo.MANO_OBRA, D("3"), "E10"),
        ("EQ-01", TipoInsumo.EQUIPO, D("30"), "E11"),
        ("EQ-02", TipoInsumo.EQUIPO, D("4"), "E12"),
    ]
    assert libro.insumo("MT-03").fuente == "REFERENCIAL — ajustar"
    assert libro.insumo("EQ-01").fuente == ""
    assert libro.insumo("MO-03").unidad == "m2"
    # Las filas de parámetros (FCAS, HERR…) no son insumos: no tienen código MT/MO/EQ.
    assert libro.insumo("FCAS") is None


def test_portada_por_rotulo(limpio):
    _, libro = limpio
    po = libro.portada
    assert po.cliente == "Condominio Ejemplo (ficticio)"
    assert po.contratista == "Constructora Didáctica (ficticia)"
    assert po.ubicacion == "Calle Ficticia 123, Ciudad Ejemplo"
    assert po.norma == "COVENIN 2000 (referencial)"
    assert po.moneda == "Dólares de los Estados Unidos de América (USD)"
    assert po.fecha_texto == "Julio 2026"
    # La obra está en la celda de abajo del ancla «PRESUPUESTO DE OBRA».
    assert po.obra == "Rehabilitación de fachada — obra ficticia"


def test_programacion_por_rotulo(limpio):
    _, libro = limpio
    assert dict(libro.programacion) == {"DSEM": D("5"), "ANTICIPO": D("0.3")}


# --- PRESUPUESTO -------------------------------------------------------------------------------


def test_partidas_unidas_a_su_apu_con_valores_guardados(limpio):
    _, libro = limpio
    pu = {h: MEMORIA["componentes"][h]["PU"] for h in ("APU-01", "APU-02", "APU-03")}
    assert [(p.fila, p.numero, p.hoja_apu, p.cantidad) for p in libro.partidas] == [
        (5, 1, "APU-01", D("120")),
        (6, 2, "APU-02", D("80")),
        (7, 3, "APU-03", D("50")),
    ]
    for p in libro.partidas:
        assert p.guardados["P"] == pu[p.hoja_apu]
        assert p.guardados["Q"] == MEMORIA["montos"][p.numero]
        assert p.capitulo == "CAPÍTULO 1. OBRAS DE ALBAÑILERÍA (FICTICIAS)"
        assert p.unidad == "m2"
    assert libro.partidas[1].codigo == "E.321.000.002"


def test_filas_especiales_de_presupuesto(limpio):
    _, libro = limpio
    assert [(e.fila, e.tipo, e.valor) for e in libro.filas_especiales] == [
        (4, TipoFilaEspecial.CAPITULO, None),
        (8, TipoFilaEspecial.SUBTOTAL, MEMORIA["SUBSINIVA"]),
        (10, TipoFilaEspecial.TOTAL_SIN_IVA, MEMORIA["SUBSINIVA"]),
        (11, TipoFilaEspecial.IVA, MEMORIA["IVATOT"]),
        (12, TipoFilaEspecial.TOTAL, MEMORIA["TOTALGEN"]),
    ]


def test_totales_por_nombre_definido(limpio):
    _, libro = limpio
    assert dict(libro.totales) == {
        "SUBSINIVA": MEMORIA["SUBSINIVA"],
        "IVATOT": MEMORIA["IVATOT"],
        "TOTALGEN": MEMORIA["TOTALGEN"],
    }


# --- APU por rótulo ----------------------------------------------------------------------------


def test_apu_por_rotulo_en_formas_distintas(limpio):
    """Tres APU con tres formas: cada rótulo en otra fila, encontrado por su texto."""
    _, libro = limpio
    celdas_pu = {a.hoja: a.rotulos[Rotulo.PU] for a in libro.apus}
    assert celdas_pu == {
        "APU-01": Celda("APU-01", "G45"),
        "APU-02": Celda("APU-02", "G40"),
        "APU-03": Celda("APU-03", "G41"),
    }
    assert {a.hoja: a.rotulos[Rotulo.REND].ref for a in libro.apus} == {
        "APU-01": "F19",
        "APU-02": "F20",
        "APU-03": "F16",
    }
    for a in libro.apus:
        esperados = MEMORIA["componentes"][a.hoja]
        for rot in ("MAT", "MO", "EQ", "TR", "CD", "ADM", "SUB", "UTI", "PU"):
            assert a.guardados[Rotulo(rot)] == esperados[rot], (a.hoja, rot)


def test_apu_cabecera_rendimiento_escombro_y_porcentajes(limpio):
    _, libro = limpio
    a1, a2, a3 = (libro.apu(h) for h in ("APU-01", "APU-02", "APU-03"))
    assert (a1.codigo_partida, a1.unidad, a1.fila_presupuesto) == ("E.311.000.001", "m2", 5)
    assert a1.titulo == "Friso liso en paredes (ficticio)"
    assert (a1.rendimiento, a2.rendimiento, a3.rendimiento) == (D("10"), D("8"), D("20"))
    # APU-02 no tiene bloque de transporte: escombro 0 y sin rótulo ESC.
    assert (a1.escombro, a2.escombro, a3.escombro) == (D("0.02"), D("0"), D("0.03"))
    assert Rotulo.ESC not in a2.rotulos
    for a in (a1, a2, a3):
        assert (a.administracion, a.utilidad, a.herramientas) == (D("0.1"), D("0.1"), D("0.05"))
    assert a1.ident == "APU_01"


def test_lineas_del_apu_con_su_celda(limpio):
    _, libro = limpio
    a2 = libro.apu("APU-02")
    assert [
        (x.tipo, x.codigo, x.cantidad, x.precio, x.celda_codigo.ref, x.celda_cantidad.ref)
        for x in a2.lineas
    ] == [
        (TipoInsumo.MATERIAL, "MT-01", D("0.1"), D("10"), "B10", "E10"),
        (TipoInsumo.MATERIAL, "MT-02", D("0.02"), D("25"), "B11", "E11"),
        (TipoInsumo.MATERIAL, "MT-03", D("12.5"), D("0.8"), "B12", "E12"),
        (TipoInsumo.MANO_OBRA, "MO-01", D("1"), D("20"), "B17", "E17"),
        (TipoInsumo.MANO_OBRA, "MO-02", D("2"), D("15"), "B18", "E18"),
        (TipoInsumo.EQUIPO, "EQ-02", D("2"), D("4"), "B26", "E26"),
    ]
    # APU-03 no tiene materiales ni equipos: solo su línea de mano de obra.
    assert [x.codigo for x in libro.apu("APU-03").lineas] == ["MO-02"]


# --- Fórmulas y valores guardados --------------------------------------------------------------


def test_formulas_y_valores_guardados_de_la_misma_celda(limpio):
    _, libro = limpio
    assert libro.formulas["APU-01!F10"] == "=VLOOKUP(B10,PRECIOS,4,0)"
    assert libro.valores["APU-01!F10"] == D("10")
    assert libro.formulas["APU-01!A2"] == "=+PRESUPUESTO!D5"
    assert libro.valores["APU-01!A2"] == "Friso liso en paredes (ficticio)"
    assert libro.formulas["PRESUPUESTO!P5"] == '=INDIRECT("\'APU-"&TEXT($B5,"00")&"\'!G45")'
    assert libro.valores["PRESUPUESTO!P5"] == D("14.486725")
    # Una celda sin fórmula está en `valores` pero no en `formulas`.
    assert "APU-01!E10" not in libro.formulas
    assert libro.valores["APU-01!E10"] == D("0.2")
    # Las claves van sin `$` y los nombres conservan su texto.
    assert libro.nombres["FCAS"] == "INSUMOS!$E$16"
    assert libro.nombres["PRECIOS"] == "INSUMOS!$B$5:$F$12"


def test_formula_nunca_calculada_guarda_none():
    """Un libro que no se recalculó (fórmula sin valor guardado): el valor queda None."""
    c = construir_libro(siembra=Siembra(parches={"APU-01!H10": (None, "=E10*2")}))
    libro = leer_libro(c.datos, NOMBRE)
    assert libro.formulas["APU-01!H10"] == "=E10*2"
    assert libro.valores["APU-01!H10"] is None


def test_sha256_nombre_y_hojas(limpio):
    c, libro = limpio
    assert libro.sha256 == hashlib.sha256(c.datos).hexdigest()
    assert libro.nombre == NOMBRE
    assert libro.hojas == c.hojas
    assert libro.perfil == "arenaza"


def test_leer_dos_veces_da_lo_mismo(limpio):
    c, libro = limpio
    assert leer_libro(c.datos, NOMBRE) == libro


# --- Tolerancia: el lector no juzga --------------------------------------------------------------


def test_cantidad_escrita_como_texto_vale_cero_y_queda_en_valores():
    c = construir_libro(siembra=Siembra(parches={"APU-01!E10": ("0,2", None)}))
    libro = leer_libro(c.datos, NOMBRE)
    linea = libro.apu("APU-01").lineas[0]
    assert (linea.codigo, linea.cantidad) == ("MT-01", Decimal(0))
    assert libro.valores["APU-01!E10"] == "0,2"


def test_rendimiento_sin_numero_vale_uno_y_no_se_guarda():
    c = construir_libro(siembra=Siembra(parches={"APU-01!F19": ("diez", None)}))
    a = leer_libro(c.datos, NOMBRE).apu("APU-01")
    assert a.rendimiento == Decimal(1)
    assert Rotulo.REND not in a.guardados


def test_rendimiento_de_respaldo_en_otra_fila_con_rotulo_rendimiento():
    c = construir_libro(
        siembra=Siembra(
            parches={
                "APU-01!F19": ("diez", None),
                "APU-01!A49": ("Rendimiento real de la cuadrilla", None),
                "APU-01!F49": (D("12"), None),
            }
        )
    )
    a = leer_libro(c.datos, NOMBRE).apu("APU-01")
    assert a.rendimiento == D("12")
    assert a.rotulos[Rotulo.REND] == Celda("APU-01", "F49")
    assert a.guardados[Rotulo.REND] == D("12")


def test_utilidad_escrita_a_mano_es_la_del_apu():
    apus = (APUS_LIMPIOS[0], con(APUS_LIMPIOS[1], utilidad_literal=D("0.02")), APUS_LIMPIOS[2])
    libro = leer_libro(construir_libro(apus).datos, NOMBRE)
    assert libro.apu("APU-02").utilidad == D("0.02")
    assert libro.apu("APU-01").utilidad == D("0.1")


# --- Unión partida ↔ APU (F-D6) ------------------------------------------------------------------


def test_dos_apu_reclaman_la_misma_fila_gana_el_del_numero_y_el_otro_se_une_por_pu():
    """Caso del libro C-1 (H5, C2): APU-01 y APU-07 dicen ser la partida 1 (fila 5); gana APU-01
    por número; la partida 2 (fila 6) no tiene APU-02 y toma el APU-07 libre porque su P.U.
    guardado coincide con su P guardado (pasada final de `_unir`)."""
    apus = (APUS_LIMPIOS[0], con(APUS_LIMPIOS[1], hoja="APU-07", fila_titulo=5))
    libro = leer_libro(construir_libro(apus).datos, NOMBRE)
    assert [(p.fila, p.hoja_apu) for p in libro.partidas] == [(5, "APU-01"), (6, "APU-07")]
    assert libro.apu("APU-07").fila_presupuesto == 5


def test_partida_sin_apu_queda_sin_hoja():
    from tests.fixtures.libros_empresa import PartidaSinApu

    s = Siembra(
        partidas_sin_apu=(
            PartidaSinApu(9, "S/C", "Limpieza final (ficticia)", "glb", D("1"), D("50")),
        )
    )
    libro = leer_libro(construir_libro(siembra=s).datos, NOMBRE)
    sin = [p for p in libro.partidas if p.numero == 9]
    assert [(p.fila, p.hoja_apu, p.guardados["P"]) for p in sin] == [(8, None, D("50"))]


def test_apu_de_plantilla_sin_partida_no_se_une():
    apus = (*APUS_LIMPIOS, con(APUS_LIMPIOS[0], numero=9, hoja="APU-x", en_presupuesto=False))
    libro = leer_libro(construir_libro(apus).datos, NOMBRE)
    assert libro.apu("APU-x").fila_presupuesto is None
    assert "APU-x" not in {p.hoja_apu for p in libro.partidas}


# --- Vínculos externos ---------------------------------------------------------------------------


def test_vinculo_externo_legible_trae_su_destino():
    destino = "file:///\\\\servidor-ficticio\\obras\\mediciones.xlsx"
    libro = leer_libro(construir_libro(siembra=Siembra(vinculo_externo=destino)).datos, NOMBRE)
    assert libro.vinculos_externos == (destino,)


def test_vinculo_externo_ilegible_no_se_pierde():
    """Un `.rels` con entidades (defusedxml lo rechaza) va como VINCULO_ILEGIBLE + la pieza."""
    datos = construir_libro(siembra=Siembra(vinculo_externo="x.xlsx")).datos
    pieza = "xl/externalLinks/_rels/externalLink1.xml.rels"
    hostil = (
        b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "b">]><Relationships>&a;</Relationships>'
    )
    entrada, salida = io.BytesIO(datos), io.BytesIO()
    with (
        zipfile.ZipFile(entrada) as zin,
        zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            zout.writestr(item, hostil if item.filename == pieza else zin.read(item.filename))
    libro = leer_libro(salida.getvalue(), NOMBRE)
    assert libro.vinculos_externos == (f"{VINCULO_ILEGIBLE}{pieza}",)


def test_libro_limpio_sin_vinculos(limpio):
    assert limpio[1].vinculos_externos == ()


# --- Rechazos del lector -------------------------------------------------------------------------


def _libro_minimo(hojas: dict[str, list[tuple[str, object]]]) -> bytes:
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    for nombre, celdas in hojas.items():
        ws = wb.add_worksheet(nombre)
        for ref, valor in celdas:
            ws.write(ref, valor)
    wb.close()
    return buf.getvalue()


def test_libro_sin_presupuesto_se_rechaza_con_mensaje():
    datos = _libro_minimo({"PORTADA": [("A1", "PRESUPUESTO DE OBRA")]})
    with pytest.raises(ArchivoRechazado, match="no tiene la hoja PRESUPUESTO"):
        leer_libro(datos, NOMBRE)


def test_hoja_presupuesto_se_encuentra_sin_distinguir_mayusculas():
    datos = _libro_minimo(
        {
            "Presupuesto": [
                ("B3", "Nº"),
                ("C3", "CÓDIGO"),
                ("B4", 1),
                ("D4", "Partida suelta (ficticia)"),
                ("G4", 2),
            ]
        }
    )
    libro = leer_libro(datos, NOMBRE)
    assert [(p.fila, p.numero, p.cantidad, p.hoja_apu) for p in libro.partidas] == [
        (4, 1, D("2"), None)
    ]


def test_xml_danado_se_rechaza():
    datos = construir_libro().datos
    entrada, salida = io.BytesIO(datos), io.BytesIO()
    with (
        zipfile.ZipFile(entrada) as zin,
        zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            contenido = zin.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                contenido = contenido[: len(contenido) // 2]  # XML cortado
            zout.writestr(item, contenido)
    with pytest.raises(ArchivoRechazado):
        leer_libro(salida.getvalue(), NOMBRE)
