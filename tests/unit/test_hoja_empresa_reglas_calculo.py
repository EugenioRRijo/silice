"""Huecos de reglas que halló la medición una falla por vez (2026-11-24).

Plan no circular, «Segunda medición»: de 12 fallas inyectadas de a una en el libro de desarrollo,
Sílice dejaba escapar 7. Tres de los escapes eran huecos reales y se cierran antes del
congelamiento:

- BUSCARV con el código de otra fila (fallas #1 y #7): L1, referencia desalineada.
- Costo directo que deja fuera un componente que hoy vale 0 (falla #3): L4 como advertencia.
- Celda de la cadena de montos que da error (#VALUE!, #N/A…) (fallas #5 y #6): L5.

Cada prueba siembra la falla exacta del inyector (`scripts/inyector_fallas.py`) en el libro
sintético y compara el CONJUNTO EXACTO de hallazgos. El valor guardado de la celda sembrada es
el que Excel guardaría al recalcular (oráculo: LibreOffice sobre la misma falla).
"""

from __future__ import annotations

from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.reglas import reglas_del_libro
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    D,
    Siembra,
    con,
    construir_libro,
    libro_limpio,
)


def _hallazgos(siembra: Siembra | None = None, **parches):
    c = construir_libro(APUS_LIMPIOS, siembra or Siembra(parches=parches))
    return reglas_del_libro(leer_libro(c.datos, "sintetico.xlsx"))


def _firmas(hallazgos):
    return [(h.regla, h.severidad.name, h.origen_ids, h.impacto) for h in hallazgos]


def _limpio(celda: str):
    return leer_libro(libro_limpio().datos, "limpio.xlsx").valores[celda]


# --- L1: BUSCARV con el código de otra fila -----------------------------------------------------


def test_l1_precio_buscado_con_el_codigo_de_otra_fila():
    """Falla #1 con la columna del precio: F10 busca el código de B11 (MT-02, 25) en vez del de
    su fila, B10 (MT-01, 10). El APU queda coherente consigo mismo; solo la fila lo delata."""
    hs = _hallazgos(**{"APU-02!F10": (D("25"), "=VLOOKUP(B11,PRECIOS,4,0)")})
    assert _firmas(hs) == [("L1", "ERROR", ("APU-02!F10", "APU-02!B11", "APU-02!B10"), None)]
    assert (hs[0].valor_observado, hs[0].valor_esperado) == (D("25"), D("10"))
    assert "MT-02" in hs[0].descripcion and "MT-01" in hs[0].descripcion


def test_l1_descripcion_buscada_con_el_codigo_de_otra_fila():
    """Falla #1 tal como la sembró el inyector: la descripción (columna 2) no mueve montos, así
    que es advertencia."""
    hs = _hallazgos(**{"APU-02!C10": (_limpio("APU-02!C11"), "=VLOOKUP(B11,PRECIOS,2,0)")})
    assert _firmas(hs) == [("L1", "ADVERTENCIA", ("APU-02!C10", "APU-02!B11", "APU-02!B10"), None)]


def test_l1_busqueda_con_el_codigo_de_una_fila_vacia_tambien_da_error_de_celda():
    """Falla #7: D12 busca B13, que está vacía; Excel muestra #N/A. Avisan L1 (por qué) y L5
    (la celda con error)."""
    hs = _hallazgos(**{"APU-02!D12": ("#N/A", "=VLOOKUP(B13,PRECIOS,3,0)")})
    assert _firmas(hs) == [
        ("L1", "ADVERTENCIA", ("APU-02!D12", "APU-02!B13", "APU-02!B12"), None),
        ("L5", "ERROR", ("APU-02!D12",), None),
    ]


def test_l1_no_juzga_una_busqueda_en_una_fila_sin_codigo():
    """Una fila sin código propio puede citar el de otra a propósito: no se adivina."""
    hs = _hallazgos(**{"APU-02!C14": (_limpio("APU-02!C10"), "=VLOOKUP(B10,PRECIOS,2,0)")})
    assert hs == []


# --- L4: componente en cero fuera del costo directo ---------------------------------------------


def test_l4_costo_directo_que_deja_fuera_un_componente_en_cero():
    """Falla #3: G36 = SUM(G32:G34) deja fuera el transporte (G35), que hoy vale 0. El monto no
    cambia hoy; cambia el día en que el transporte tenga valor."""
    hs = _hallazgos(**{"APU-02!G36": (D("24.96875"), "=SUM(G32:G34)")})
    assert _firmas(hs) == [("L4", "ADVERTENCIA", ("APU-02!G36", "APU-02!G35"), None)]
    assert "transporte" in hs[0].descripcion


# --- L5: celda de la cadena de montos con error -------------------------------------------------


def test_l5_sumaproducto_con_rangos_de_distinto_tamano():
    """Fallas #5 y #6: SUMPRODUCT(G5:G7, H5:H6) da #VALUE! y lo arrastra al total de la
    composición (B10). L9 no puede cuadrar un error; L5 lo informa en una sola fila."""
    hs = _hallazgos(
        **{
            "RESUMEN!B4": (
                "#VALUE!",
                "=SUMPRODUCT(PRESUPUESTO!$G$5:$G$7,PRESUPUESTO!$H$5:$H$6)",
            ),
            "RESUMEN!B10": ("#VALUE!", "=SUM(B4:B9)"),
        }
    )
    assert _firmas(hs) == [("L5", "ERROR", ("RESUMEN!B4", "RESUMEN!B10"), None)]
    # Nombra cada celda con su error, no la hoja (sobreviviente de mutator, 2026-11-25).
    assert "B4 (#VALUE!), B10 (#VALUE!)" in hs[0].descripcion


def test_l5_no_repite_el_ref_que_ya_informa():
    """B13 cita una celda borrada (#REF! en su fórmula) y B14 la arrastra: es la misma causa que
    L5 ya informa por la fórmula de B13, sin una segunda fila."""
    siembra = Siembra(resumen_ref_rota=True, parches={"RESUMEN!B14": ("#REF!", "=B13")})
    assert _firmas(_hallazgos(siembra)) == [("L5", "ERROR", ("RESUMEN!B13",), None)]


# --- Fronteras (revisión independiente del 2026-11-24) ------------------------------------------


def test_l1_no_avisa_si_la_otra_fila_tiene_el_mismo_codigo():
    """Excel no distingue mayúsculas en BUSCARV: citar «mt-01» de otra fila trae el mismo
    insumo que el «MT-01» propio y no cambia nada."""
    siembra = Siembra(
        parches={
            "APU-02!B14": ("mt-01", None),
            "APU-02!C10": (_limpio("APU-02!C10"), "=VLOOKUP($B$14,PRECIOS,2,0)"),
        }
    )
    assert _hallazgos(siembra) == []


def test_l1_referencia_absoluta_y_envuelta_en_iferror():
    hs = _hallazgos(**{"APU-02!F10": (D("25"), "=IFERROR(VLOOKUP($B$11,PRECIOS,4,0),0)")})
    assert _firmas(hs) == [("L1", "ERROR", ("APU-02!F10", "APU-02!B11", "APU-02!B10"), None)]


def test_l1_con_aritmetica_compara_lo_que_trae_cada_busqueda():
    """Con dos BUSCARV sumados, la cifra guardada (35) no es la de ninguna búsqueda: L1 compara
    lo que trae la búsqueda desalineada (25, MT-02) con la de su fila (10, MT-01), y avisa una
    sola vez por fórmula."""
    hs = _hallazgos(
        **{"APU-02!F10": (D("35"), "=VLOOKUP(B10,PRECIOS,4,0)+VLOOKUP(B11,PRECIOS,4,0)")}
    )
    l1 = [h for h in hs if h.regla == "L1"]
    assert _firmas(l1) == [("L1", "ERROR", ("APU-02!F10", "APU-02!B11", "APU-02!B10"), None)]
    assert (l1[0].valor_observado, l1[0].valor_esperado) == (D("25"), D("10"))
    assert "35" not in l1[0].descripcion


def test_l4_componente_no_nulo_y_otro_en_cero_fuera_del_costo_directo():
    """G36 = SUM(G32:G33) deja fuera los equipos (G34, 1,59375) y el transporte en 0 (G35):
    ERROR con impacto por los equipos (1,59375 × 1,21 × 80 = 154,275 -> 154,28) y ADVERTENCIA
    por el transporte."""
    hs = _hallazgos(**{"APU-02!G36": (D("23.375"), "=SUM(G32:G33)")})
    # Solo L4: el PRESUPUESTO del libro sintético guarda el CD viejo y L3 avisa de eso aparte.
    assert _firmas([h for h in hs if h.regla == "L4"]) == [
        ("L4", "ERROR", ("APU-02!G36", "APU-02!G34"), D("154.28")),
        ("L4", "ADVERTENCIA", ("APU-02!G36", "APU-02!G35"), None),
    ]


def test_l4_no_juzga_un_apu_de_plantilla_sin_partida():
    """Una plantilla sin partida no entra al presupuesto: aunque su CD (G41 = SUM(G37:G39)) deje
    fuera el transporte (G40, 0,24), L4 no tiene partida que corregir y solo avisa L2.
    Mata el mutante `p is None and celda_cd is None` de mutator (2026-11-25)."""
    a1, a2, a3 = APUS_LIMPIOS
    apus = (a1, a2, a3, con(a1, numero=9, hoja="APU-x", en_presupuesto=False))
    c = construir_libro(apus, Siembra(parches={"APU-x!G41": (D("11.7325"), "=SUM(G37:G39)")}))
    hs = reglas_del_libro(leer_libro(c.datos, "sintetico.xlsx"))
    assert [h.regla for h in hs] == ["L2"]


def test_l4_no_juzga_un_costo_directo_que_da_error():
    """Si el CD da #VALUE!, no hay cifra que comparar con la suma de componentes: lo informa L5
    y L4 calla. Mata el mutante `celda_cd is None and cd is None` de mutator (2026-11-25)."""
    hs = _hallazgos(**{"APU-02!G36": ("#VALUE!", '=SUM(G32:G35)/"x"')})
    assert _firmas(hs) == [("L5", "ERROR", ("APU-02!G36",), None)]


def test_l4_costo_directo_sin_formula_no_se_juzga_por_componente():
    assert _hallazgos(**{"APU-02!G36": (D("24.96875"), None)}) == []


def test_l4_componente_con_error_no_es_un_componente_en_cero():
    """Si el transporte da #VALUE!, no «vale 0»: lo informa L5 y L4 no repite el aviso."""
    hs = _hallazgos(
        **{
            "APU-02!G35": ("#VALUE!", '=1/"x"'),
            "APU-02!G36": (D("24.96875"), "=SUM(G32:G34)"),
        }
    )
    assert _firmas(hs) == [("L5", "ERROR", ("APU-02!G35",), None)]


def test_l5_fuera_de_la_cadena_de_montos_y_sin_formula_no_cuenta():
    """Un error en INSUMOS no está en la cadena de montos, y un «#N/A» escrito sin fórmula es
    texto: ninguno da hallazgo."""
    hs = _hallazgos(**{"INSUMOS!H5": ("#N/A", "=NA()"), "APU-02!H10": ("#N/A", None)})
    assert hs == []


def test_l5_errores_en_dos_hojas_van_en_el_orden_del_libro():
    hs = _hallazgos(
        **{
            "RESUMEN!C4": ("#DIV/0!", "=B4/0"),
            "PRESUPUESTO!S5": ("#CALC!", "=FILTER(B5:B7,B5:B7>99)"),
        }
    )
    assert _firmas(hs) == [
        ("L5", "ERROR", ("PRESUPUESTO!S5",), None),
        ("L5", "ERROR", ("RESUMEN!C4",), None),
    ]
    assert "#CALC!" in hs[0].descripcion and "#DIV/0!" in hs[1].descripcion


def test_l5_no_juzga_un_apu_de_plantilla_sin_partida():
    """Como L4 y L6: una plantilla sin partida no entra al presupuesto (L2 la informa), así que
    un error en ella no mueve ningún monto."""
    a1, a2, a3 = APUS_LIMPIOS
    apus = (a1, a2, a3, con(a1, numero=9, hoja="APU-x", en_presupuesto=False))
    c = construir_libro(apus, Siembra(parches={"APU-x!G20": ("#DIV/0!", "=1/0")}))
    hs = reglas_del_libro(leer_libro(c.datos, "sintetico.xlsx"))
    assert [h.regla for h in hs] == ["L2"]
