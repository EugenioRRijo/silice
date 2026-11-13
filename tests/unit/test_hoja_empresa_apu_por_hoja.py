"""F5 vial, tarea 4: el perfil hermano `apu_por_hoja` (un APU por hoja, solo valores) y su mapeo.

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §7 (punto 4, opción B):
un tipo de perfil hermano en `adapters/hoja_empresa/` con su lector, que produce el mismo
`LibroLeido` / `ApuLeido` y usa la misma guardia; `fusion/mapeo.py` arma la composición del núcleo
con el desperdicio dentro de la cantidad (punto 1, opción B) y devuelve la traza aparte.

El libro es el FICTICIO de `tests/fixtures/libro_apu_por_hoja.py`; los oráculos son los de su
memoria de cálculo, escritos a mano.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.hoja_empresa import guardia
from adapters.hoja_empresa.guardia import ArchivoRechazado
from adapters.hoja_empresa.lector_apu_por_hoja import (
    leer_hojas,
    leer_libro_apu_por_hoja,
    letra,
    numero_de,
)
from adapters.hoja_empresa.modelo import Celda, LibroNoInterpretable, Rotulo, TipoInsumo
from adapters.hoja_empresa.perfil import PerfilInvalido
from adapters.hoja_empresa.perfil_apu_por_hoja import cargar_perfil_apu_por_hoja
from core.contracts.apu import ParametrosCosto
from core.costing.motor import calcular_apu
from fusion.mapeo import composicion_de_apu_por_hoja
from tests.fixtures.libro_apu_por_hoja import (
    APUS,
    ApuFicticio,
    Equipo,
    Material,
    Obrero,
    con_celdas,
    libro_apu,
    libro_presupuesto,
)

D = Decimal


@pytest.fixture(scope="module")
def libro():
    return leer_libro_apu_por_hoja(libro_apu(), "frente_ficticio.xlsx")


def test_el_perfil_del_paquete_carga_y_se_valida():
    perfil = cargar_perfil_apu_por_hoja("apu_por_hoja")
    assert perfil.nombre == "apu_por_hoja"
    assert perfil.prefijo_hoja == "APU"
    assert set(perfil.bloques) == {"materiales", "equipos", "mano_obra"}


def test_un_perfil_incompleto_se_rechaza_al_cargar(tmp_path: Path):
    crudo = json.loads(
        (
            Path(__file__).resolve().parents[2] / "adapters/hoja_empresa/perfiles/apu_por_hoja.json"
        ).read_text(encoding="utf-8")
    )
    del crudo["bloques"]["equipos"]
    (tmp_path / "otro.json").write_text(json.dumps({**crudo, "nombre": "otro"}), encoding="utf-8")
    with pytest.raises(PerfilInvalido, match="bloques: faltan"):
        cargar_perfil_apu_por_hoja("otro", carpetas=(tmp_path,))


def test_lee_una_hoja_por_partida_con_su_cabecera(libro):
    assert libro.perfil == "apu_por_hoja"
    assert [a.hoja for a in libro.apus] == ["APU 1", "APU 2", "APU 3", "APU 4", "APU 5"]
    apu = libro.apu("APU 1")
    assert (apu.numero, apu.codigo_partida, apu.titulo, apu.unidad) == (
        1,
        "VF-001",
        "Riego de adherencia ficticio",
        "m2",
    )
    assert (apu.cantidad, apu.rendimiento) == (D("1000"), D("2000"))
    assert (apu.prestaciones, apu.administracion, apu.utilidad) == (D("2.5"), D("0.15"), D("0.1"))
    assert (apu.financiamiento, apu.impuesto) == (D("0"), D("0"))
    assert apu.guardados[Rotulo.PU] == D("2.08")
    assert apu.rotulos[Rotulo.PU] == Celda("APU 1", "G33")


def test_lee_todos_los_renglones_con_o_sin_numero(libro):
    apu = libro.apu("APU 1")
    assert [(x.tipo, x.codigo, x.descripcion, x.cantidad) for x in apu.lineas] == [
        (TipoInsumo.MATERIAL, "1", "Emulsión asfáltica ficticia", D("0.5")),
        (TipoInsumo.MATERIAL, "", "Arena de secado ficticia", D("0.002")),
        (TipoInsumo.EQUIPO, "1", "Camión irrigador ficticio", D("1")),
        (TipoInsumo.EQUIPO, "2", "Barredora ficticia", D("1")),
        (TipoInsumo.MANO_OBRA, "1", "Operador ficticio", D("2")),
        (TipoInsumo.MANO_OBRA, "", "Ayudante ficticio", D("3")),
    ]
    emulsion, arena, _, barredora, *_ = apu.lineas
    assert (emulsion.unidad, emulsion.desperdicio, emulsion.precio) == ("lt", D("4"), D("2"))
    assert emulsion.celda_cantidad == Celda("APU 1", "D9")
    assert arena.desperdicio == D("0")
    assert barredora.depreciacion == D("0.5")
    assert len(libro.apu("APU 3").lineas) == 6 + 1 + 1


def test_bono_financiamiento_e_impuesto(libro):
    assert libro.apu("APU 4").financiamiento == D("0.02")
    cinco = libro.apu("APU 5")
    assert [x.bono for x in cinco.lineas] == [D("5")]
    assert cinco.impuesto == D("0.16")


def test_una_hoja_sin_precio_unitario_no_se_interpreta():
    rota = ApuFicticio(
        9,
        "VF-009",
        "Sin pie ficticio",
        "m2",
        "1",
        "1",
        materiales=(Material(1, "Cosa ficticia", "kg", "1", "0", "1"),),
    )
    datos = libro_apu((rota,))
    import io

    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(datos))
    hoja = wb["APU 9"]
    for fila in hoja.iter_rows():
        for celda in fila:
            if celda.value == "PRECIO UNITARIO":
                celda.value = "Otra cosa"
    salida = io.BytesIO()
    wb.save(salida)
    with pytest.raises(LibroNoInterpretable, match="APU 9.*PRECIO UNITARIO"):
        leer_libro_apu_por_hoja(salida.getvalue(), "roto.xlsx")


def test_un_libro_sin_hojas_de_apu_se_rechaza():
    import io

    import openpyxl

    wb = openpyxl.Workbook()
    wb.active.title = "Hoja1"
    salida = io.BytesIO()
    wb.save(salida)
    with pytest.raises(ArchivoRechazado, match="ninguna hoja de APU"):
        leer_libro_apu_por_hoja(salida.getvalue(), "vacio.xlsx")


def test_la_misma_guardia_de_siempre():
    with pytest.raises(ArchivoRechazado):
        leer_libro_apu_por_hoja(b"esto no es un xlsx", "malo.xlsx")


# --- valores que el núcleo no admite (arbitraje F5 vial, P3) ----------------------------------
#
# Un precio, una cantidad o un porcentaje negativos, un coeficiente de depreciación fuera de
# (0; 1] o un rendimiento que no es mayor que cero no se pueden recalcular: antes daban un 500 (el
# contrato del núcleo los rechaza con `ValueError`). Ahora la hoja no es interpretable y el mensaje
# dice la celda. Las celdas salen de la forma del libro ficticio (`_hoja_apu`), contadas a mano:
# con un solo material, su renglón es la fila 9 (D cantidad, E desperdicio, F precio) y el pie
# queda en la fila 20 (prestaciones, E) y 24-25 (administración y utilidad, F); sin materiales, el
# primer equipo es la fila 13 (D precio, E coeficiente); sin materiales ni equipos, el primer
# obrero es la fila 18 (C cantidad, D jornal). El rendimiento es F5.

_MATERIAL = (Material(1, "Cemento ficticio", "kg", "1", "0", "1"),)


def _hoja(**cambios) -> ApuFicticio:
    base = {"materiales": _MATERIAL, "rendimiento": "1", **cambios}
    return ApuFicticio(9, "VF-009", "Partida ficticia inválida", "m2", "1", **base)


INVALIDOS = [
    (
        _hoja(materiales=(Material(1, "Cemento ficticio", "kg", "1", "0", "-1"),)),
        "APU 9!F9: el precio de «Cemento ficticio» es -1 y no puede ser negativo",
    ),
    (
        _hoja(materiales=(Material(1, "Cemento ficticio", "kg", "-0.5", "0", "1"),)),
        "APU 9!D9: la cantidad de «Cemento ficticio» es -0,5 y no puede ser negativa",
    ),
    (
        _hoja(materiales=(Material(1, "Cemento ficticio", "kg", "1", "-5", "1"),)),
        "APU 9!E9: el desperdicio de «Cemento ficticio» es -5 y no puede ser negativo",
    ),
    (
        _hoja(materiales=(), equipos=(Equipo(1, "Mezcladora ficticia", "1", "-10", "1"),)),
        "APU 9!D13: el precio de «Mezcladora ficticia» es -10 y no puede ser negativo",
    ),
    (
        _hoja(materiales=(), equipos=(Equipo(1, "Mezcladora ficticia", "1", "10", "1.5"),)),
        "APU 9!E13: el coeficiente de depreciación de «Mezcladora ficticia» es 1,5 y debe ser "
        "mayor que 0 y no pasar de 1",
    ),
    (
        _hoja(materiales=(), equipos=(Equipo(1, "Mezcladora ficticia", "1", "10", "0"),)),
        "APU 9!E13: el coeficiente de depreciación de «Mezcladora ficticia» es 0 y debe ser "
        "mayor que 0 y no pasar de 1",
    ),
    (
        _hoja(materiales=(), mano_obra=(Obrero(1, "Albañil ficticio", "1", "-40"),)),
        "APU 9!D18: el precio de «Albañil ficticio» es -40 y no puede ser negativo",
    ),
    (
        _hoja(materiales=(), mano_obra=(Obrero(1, "Albañil ficticio", "-2", "40"),)),
        "APU 9!C18: la cantidad de «Albañil ficticio» es -2 y no puede ser negativa",
    ),
    (
        _hoja(rendimiento="-2"),
        "APU 9!F5: el rendimiento es -2 y debe ser mayor que cero",
    ),
    (
        _hoja(prestaciones="-500"),
        "APU 9!E20: el porcentaje de Prestaciones sociales es -500 y no puede ser negativo",
    ),
    (
        _hoja(administracion="-5"),
        "APU 9!F24: el porcentaje de Administración es -5 y no puede ser negativo",
    ),
    (
        _hoja(utilidad="-1.5"),
        "APU 9!F25: el porcentaje de Utilidad es -1,5 y no puede ser negativo",
    ),
]


CASOS_INVALIDOS = (
    "precio_material",
    "cantidad_material",
    "desperdicio",
    "precio_equipo",
    "coeficiente_1_5",
    "coeficiente_0",
    "jornal",
    "obreros",
    "rendimiento_negativo",
    "prestaciones",
    "administracion",
    "utilidad",
)


@pytest.mark.parametrize(("hoja", "mensaje"), INVALIDOS, ids=CASOS_INVALIDOS)
def test_un_valor_que_el_nucleo_no_admite_hace_la_hoja_no_interpretable(hoja, mensaje):
    with pytest.raises(LibroNoInterpretable) as error:
        leer_libro_apu_por_hoja(libro_apu((hoja,)), "invalido.xlsx")
    assert str(error.value) == f"{mensaje}: Sílice no recalcula la hoja «APU 9»."


def _con_rendimiento_cero() -> bytes:
    """El fixture divide entre el rendimiento: el cero se escribe después, en la celda F5."""
    import io

    import openpyxl

    libro = openpyxl.load_workbook(io.BytesIO(libro_apu((_hoja(),))))
    libro["APU 9"]["F5"] = 0
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def test_un_rendimiento_cero_hace_la_hoja_no_interpretable():
    with pytest.raises(LibroNoInterpretable) as error:
        leer_libro_apu_por_hoja(_con_rendimiento_cero(), "cero.xlsx")
    assert str(error.value) == (
        "APU 9!F5: el rendimiento es 0 y debe ser mayor que cero: Sílice no recalcula la hoja "
        "«APU 9»."
    )


# Arbitraje F5/F7/F8 r2, N3: una magnitud enorme (1e20, 1e300, 9,99e307) daba un 500 al presentar
# el precio (`Decimal.quantize` pasa de la precisión). El lector la ataja con su celda: ninguna
# cantidad, precio, porcentaje ni rendimiento de un APU pasa de un billón (10^12). Las del
# material se prueban por la ruta (`test_api_libros_replica.py`); aquí, las de la cabecera y el pie.
TOPE = "1.000.000.000.000"


@pytest.mark.parametrize(
    ("celda", "que"),
    [
        ("F5", "el rendimiento"),
        ("D5", "la cantidad de la partida"),
        ("F24", "el porcentaje de Administración"),
        ("G28", "el precio unitario impreso"),
    ],
    ids=["rendimiento", "cantidad_cabecera", "administracion", "precio_impreso"],
)
def test_una_magnitud_enorme_hace_la_hoja_no_interpretable_con_su_celda(celda: str, que: str):
    datos = con_celdas(libro_apu((_hoja(),)), "APU 9", {celda: 1e20}, dimension_de_antes=False)
    with pytest.raises(LibroNoInterpretable) as error:
        leer_libro_apu_por_hoja(datos, "enorme.xlsx")
    assert str(error.value) == (
        f"APU 9!{celda}: {que} pasa del tope de {TOPE}: Sílice no recalcula la hoja «APU 9»."
    )


def test_el_tope_mismo_se_lee():
    """«Pasa del tope» es estrictamente mayor: un billón exacto se lee."""
    datos = con_celdas(libro_apu((_hoja(),)), "APU 9", {"F9": 1e12}, dimension_de_antes=False)
    (linea,) = leer_libro_apu_por_hoja(datos, "tope.xlsx").apu("APU 9").lineas
    assert linea.precio == D("1000000000000")


# --- mapeo al núcleo --------------------------------------------------------------------------


def test_el_mapeo_pone_el_desperdicio_dentro_de_la_cantidad_y_da_la_traza(libro):
    composicion, parametros, trazas = composicion_de_apu_por_hoja(libro.apu("APU 1"))
    assert [(m.descripcion, m.cantidad) for m in composicion.materiales] == [
        ("Emulsión asfáltica ficticia", D("0.52")),
        ("Arena de secado ficticia", D("0.002")),
    ]
    assert [(t.descripcion, t.cantidad_neta, t.desperdicio_pct, t.cantidad) for t in trazas] == [
        ("Emulsión asfáltica ficticia", D("0.5"), D("4"), D("0.52"))
    ]
    assert parametros == ParametrosCosto(
        fcas=D("2.5"), bono_alimentacion=D("0"), administracion=D("0.15"), utilidad=D("0.1")
    )
    # memoria: 1,6425 × 1,15 × 1,10
    assert calcular_apu(composicion, parametros).precio_unitario == D("2.0777625")


def test_el_mapeo_de_la_demarcacion_da_el_precio_exacto(libro):
    composicion, parametros, _ = composicion_de_apu_por_hoja(libro.apu("APU 3"))
    assert calcular_apu(composicion, parametros).precio_unitario == D("0.81213")


def test_el_fixture_es_el_de_la_memoria():
    assert [a.numero for a in APUS] == [1, 2, 3, 4, 5]


# --- entrada hostil: celdas lejanas que la <dimension> no declara (arbitraje F5/F7/F8 r2, P1) -----
#
# La guardia solo mira la `<dimension>` que declara cada hoja, y un libro hostil puede declarar un
# área pequeña y escribir lejos: A1048576 (variante C de la sonda del árbitro: openpyxl entregaba
# un millón de filas) o una celda en XFD en 2.000 filas (variante E: 16.384 valores por fila, 32
# millones de celdas en unos 12 KB). Sílice lee de cada hoja a lo sumo las filas y las columnas que
# justifica `MAX_AREA_HOJA` (20.000 × 100) y rechaza el libro si tiene algo escrito más allá; cada
# fila llega solo hasta su último valor. Se cuentan filas Y celdas: contar solo celdas no veía el
# millón de filas vacías.

#: El libro de APU y el de presupuesto, con la hoja que Sílice lee de cada uno.
LIBROS = {"apu": (libro_apu, "APU 1"), "presupuesto": (libro_presupuesto, "PRESUPUESTO")}
#: Lo más que puede entregar openpyxl con el tope (a mano, de la guardia): 20.000 filas y una más
#: (la que delata que la hoja sigue), y 20.000 × 100 celdas más una fila ancha (la que se rechaza).
TOPE_FILAS_ENTREGADAS = 20_001
TOPE_CELDAS_ENTREGADAS = 2_000_000 + 16_384
SIGUE = (
    "Sílice lee de cada hoja hasta 20.000 filas y 100 columnas (de la A a la CV). Se rechaza por "
    "seguridad: borre lo que sobra al final de la hoja y guárdelo de nuevo."
)


def _variante(cual: str, datos: bytes, hoja: str) -> bytes:
    if cual == "C":
        return con_celdas(datos, hoja, {"A1048576": "fin ficticio"})
    return con_celdas(datos, hoja, {f"XFD{fila}": "y" for fila in range(2, 2002)})


def _contar(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """[filas, celdas] que openpyxl entrega a Sílice al recorrer las hojas en solo lectura."""
    from openpyxl.worksheet._read_only import ReadOnlyWorksheet

    medida = [0, 0]
    original = ReadOnlyWorksheet.iter_rows

    def contando(self, *args, **kwargs):
        for fila in original(self, *args, **kwargs):
            medida[0] += 1
            medida[1] += len(fila)
            yield fila

    monkeypatch.setattr(ReadOnlyWorksheet, "iter_rows", contando)
    return medida


@pytest.mark.parametrize("libro_hostil", sorted(LIBROS))
@pytest.mark.parametrize("variante", ["C", "E"])
def test_una_celda_lejana_que_la_dimension_no_declara_rechaza_el_libro(
    libro_hostil: str, variante: str, monkeypatch: pytest.MonkeyPatch
):
    construir, hoja = LIBROS[libro_hostil]
    datos = _variante(variante, construir(), hoja)
    medida = _contar(monkeypatch)
    error = None
    try:
        hojas = leer_hojas(datos, "hostil.xlsx", lambda titulo: titulo == hoja)
    except ArchivoRechazado as exc:
        error, hojas = exc, {}
    filas, celdas = medida
    guardadas = sum(len(f) for f in hojas.values()), sum(len(r) for f in hojas.values() for r in f)
    assert (filas <= TOPE_FILAS_ENTREGADAS, celdas <= TOPE_CELDAS_ENTREGADAS) == (True, True), (
        f"openpyxl entregó {filas:,} filas y {celdas:,} celdas; Sílice guardó {guardadas}"
    )
    assert error is not None
    donde = (
        "tiene filas con datos o con formato más allá de la 20.000"
        if variante == "C"
        else (
            "la fila 2 tiene celdas con datos o con formato hasta la columna XFD, más allá de la CV"
        )
    )
    assert str(error) == f"El libro «hostil.xlsx», hoja «{hoja}»: {donde}. {SIGUE}"


@pytest.mark.parametrize(
    "frontera", ["ultima_fila", "fila_siguiente", "ultima_columna", "columna_siguiente"]
)
def test_la_frontera_del_tope_es_la_de_la_guardia(frontera: str):
    """El tope sale de las constantes de la guardia (20.000 × 100 = `MAX_AREA_HOJA`), no de una
    cifra escrita dos veces: la última fila y la última columna se leen; la siguiente, no."""
    filas, columnas = guardia.MAX_FILAS_HOJA, guardia.MAX_COLUMNAS_HOJA
    assert (filas, columnas, filas * columnas) == (20_000, 100, guardia.MAX_AREA_HOJA)
    ref = {
        "ultima_fila": f"A{filas}",
        "fila_siguiente": f"A{filas + 1}",
        "ultima_columna": f"{letra(columnas - 1)}5",
        "columna_siguiente": f"{letra(columnas)}5",
    }[frontera]
    datos = con_celdas(libro_apu(), "APU 1", {ref: "fin ficticio"})
    if frontera.endswith("siguiente"):
        with pytest.raises(ArchivoRechazado, match="Se rechaza por seguridad"):
            leer_hojas(datos, "frontera.xlsx")
        return
    hojas = leer_hojas(datos, "frontera.xlsx")
    assert _valor_en(hojas, ref) == "fin ficticio"
    assert leer_libro_apu_por_hoja(datos, "frontera.xlsx").apu("APU 1").titulo == (
        "Riego de adherencia ficticio"
    )


def _valor_en(hojas: dict[str, list[list[object]]], ref: str) -> object:
    """El valor de `ref` en la hoja «APU 1» de lo que devolvió `leer_hojas`."""
    from openpyxl.utils.cell import column_index_from_string, coordinate_from_string

    columna, fila = coordinate_from_string(ref)
    return hojas["APU 1"][fila - 1][column_index_from_string(columna) - 1]


def _sin_vacios_al_final(datos: bytes) -> dict[str, list[list[object]]]:
    """Oráculo independiente: openpyxl en modo normal (sin `reset_dimensions` ni solo lectura),
    cada fila sin los vacíos del final."""
    import io

    import openpyxl

    libro = openpyxl.load_workbook(io.BytesIO(datos), data_only=True)
    resultado = {}
    for hoja in libro.worksheets:
        filas = []
        for fila in hoja.iter_rows(values_only=True):
            valores = list(fila)
            while valores and valores[-1] is None:
                valores.pop()
            filas.append(valores)
        resultado[hoja.title] = filas
    return resultado


@pytest.mark.parametrize("cual", sorted(LIBROS))
def test_un_libro_legitimo_se_lee_igual_que_siempre(cual: str):
    construir, _ = LIBROS[cual]
    datos = construir()
    assert leer_hojas(datos, "f.xlsx") == _sin_vacios_al_final(datos)


def test_cada_fila_llega_solo_hasta_su_ultimo_valor(monkeypatch: pytest.MonkeyPatch):
    """Una celda con formato y sin valor al final de la fila (H3, CV7) no alarga la fila: Sílice
    guarda las mismas filas y celdas que el oráculo."""
    datos = con_celdas(libro_apu(), "APU 1", {}, solo_formato=("H3", "CV7"))
    esperado = _sin_vacios_al_final(datos)
    hojas = leer_hojas(datos, "f.xlsx")
    medida = (len(hojas["APU 1"]), sum(len(f) for f in hojas["APU 1"]))
    assert medida == (len(esperado["APU 1"]), sum(len(f) for f in esperado["APU 1"]))
    assert hojas == esperado


def test_el_libro_entero_tiene_un_tope_de_celdas():
    """Revisión final del árbitro (MENOR 1): el tope por hoja no basta, porque 64 hojas en su tope
    pasan la guardia y materializan 128 millones de celdas. El libro entero tiene su presupuesto,
    que sale de la guardia, cuenta las celdas antes de recortar y rechaza en voz alta."""
    assert guardia.MAX_CELDAS_LIBRO == 4_000_000
    assert guardia.MAX_CELDAS_LIBRO >= 2 * guardia.MAX_AREA_HOJA
    from adapters.hoja_empresa import lector_apu_por_hoja as lector

    datos = libro_apu()
    leidas = sum(len(fila) for hoja in leer_hojas(datos, "normal.xlsx").values() for fila in hoja)
    assert leidas > 10
    lector_tope = lector.MAX_CELDAS_LIBRO
    try:
        lector.MAX_CELDAS_LIBRO = 10
        with pytest.raises(ArchivoRechazado) as error:
            leer_hojas(datos, "grande.xlsx")
    finally:
        lector.MAX_CELDAS_LIBRO = lector_tope
    assert str(error.value).startswith(
        "El libro «grande.xlsx» tiene más de 10 celdas con datos o con formato entre sus hojas."
    )


# --- El porcentaje del pie a la izquierda de su rótulo (libro vial real, 2026-11-13) ---
# Un libro real escribe «p | Administración (%) | … | monto»: el porcentaje a la IZQUIERDA del
# rótulo y el monto a la derecha. Leer «el primer número a la derecha» tomaba el monto por
# porcentaje y daba un AH1 falso en cada hoja. El perfil dice de qué lado está
# (`lado_de_los_porcentajes`, «derecha» por omisión, como el libro ficticio). Datos FICTICIOS.

_ROTULOS_DEL_PIE = (
    "Prestaciones sociales",
    "Administración",
    "Utilidad",
    "Financiamiento",
    "Impuesto",
)
#: Un monto ficticio a la derecha del rótulo, como el del libro real: con el lado equivocado se lee
#: como porcentaje.
_MONTO_A_LA_DERECHA = 123.45


def _con_porcentajes_a_la_izquierda(datos: bytes) -> bytes:
    import io

    import openpyxl

    libro = openpyxl.load_workbook(io.BytesIO(datos))
    for hoja in libro.worksheets:
        for fila in hoja.iter_rows(max_col=7):
            rotulo = fila[0].value
            if not (isinstance(rotulo, str) and rotulo.startswith(_ROTULOS_DEL_PIE)):
                continue
            numeros = [c.value for c in fila[1:] if isinstance(c.value, (int, float))]
            for celda in fila:
                celda.value = None
            fila[0].value, fila[1].value = numeros[0], rotulo
            fila[6].value = numeros[1] if len(numeros) > 1 else _MONTO_A_LA_DERECHA
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def _perfil_con_lado(tmp_path: Path, lado: object):
    crudo = json.loads(
        (
            Path(__file__).resolve().parents[2] / "adapters/hoja_empresa/perfiles/apu_por_hoja.json"
        ).read_text(encoding="utf-8")
    )
    crudo = {**crudo, "nombre": "lado", "lado_de_los_porcentajes": lado}
    (tmp_path / "lado.json").write_text(json.dumps(crudo), encoding="utf-8")
    return cargar_perfil_apu_por_hoja("lado", carpetas=(tmp_path,))


def _pie(apu) -> tuple:
    return (apu.prestaciones, apu.administracion, apu.utilidad, apu.financiamiento, apu.impuesto)


def test_el_perfil_del_paquete_lee_los_porcentajes_a_la_derecha():
    assert cargar_perfil_apu_por_hoja("apu_por_hoja").lado_de_los_porcentajes == "derecha"


def test_con_el_lado_izquierdo_el_pie_se_lee_igual_que_el_libro_de_siempre(libro, tmp_path: Path):
    perfil = _perfil_con_lado(tmp_path, "izquierda")
    datos = _con_porcentajes_a_la_izquierda(libro_apu())
    leido = leer_libro_apu_por_hoja(datos, "izquierda.xlsx", perfil)
    for original in libro.apus:
        assert _pie(leido.apu(original.hoja)) == _pie(original), original.hoja
    # con el lado de siempre, ese mismo libro toma el monto por porcentaje (lo que pasaba)
    a_la_derecha = leer_libro_apu_por_hoja(
        datos, "izquierda.xlsx", _perfil_con_lado(tmp_path, "derecha")
    )
    assert a_la_derecha.apu("APU 1").administracion == D("1.2345")


@pytest.mark.parametrize("lado", ["arriba", "", 3, None])
def test_un_lado_desconocido_se_rechaza_al_cargar(tmp_path: Path, lado: object):
    with pytest.raises(PerfilInvalido, match="lado_de_los_porcentajes"):
        _perfil_con_lado(tmp_path, lado)


# --- Cifras con la precisión de Excel (15 dígitos significativos) ---
# Excel guarda el valor en caché de una fórmula como doble: 0,1 + 0,2 queda 0.30000000000000004 y
# `Decimal(str(float))` arrastraba el ruido (AH6 falsos). Excel garantiza 15 dígitos
# significativos: el lector toma la cifra con esa precisión.


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (0.1 + 0.2, D("0.3")),
        (1000.0000000000001, D("1000")),
        (1 / 3, D("0.333333333333333")),
        (2.08, D("2.08")),
        (123456789012.5, D("123456789012.5")),
        (7, D("7")),
        (D("0.30000000000000004"), D("0.30000000000000004")),  # un Decimal ya es exacto
    ],
)
def test_la_cifra_de_una_celda_tiene_la_precision_de_excel(valor, esperado):
    assert numero_de(valor) == esperado
