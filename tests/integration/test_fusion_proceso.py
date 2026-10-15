"""Proceso «de vuelta» de la 1.5: libro -> motor -> auditoría -> alertas -> libro calcado
(Silice 1.5, UC-25, RF-103, RF-106 a RF-108; spec §1, F-D2, F-D7, F-D8, F-D9).

Ida y vuelta con libros sintéticos (`tests/fixtures/libros_empresa.py`): el motor reproduce los
P.U. al centavo contra la memoria de cálculo a mano, la devolución reabre con openpyxl con los
valores de Silice, y releída por el mismo lector ya no tiene los errores que Silice corrige
(F1, L1, L4, L5, L9 del desglose) pero conserva los que son decisión de la empresa (L6 «a
confirmar», F-D7) y lo que solo se informa (L7).
"""

from __future__ import annotations

import hashlib
import io
from datetime import date

import openpyxl
import pytest

from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.modelo import LibroNoInterpretable
from adapters.hoja_empresa.reglas import reglas_del_libro
from fusion.alertas import TIPO_BS, TIPO_VERSION, ContextoPrecios
from fusion.proceso import (
    ACCION_A_CONFIRMAR,
    ACCION_CORREGIDO,
    ACCION_INFORMADO,
    devolver,
    fecha_del_libro,
    procesar_libro,
    servicios_desde_sesion,
)
from operacion.version import version
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    INSUMOS,
    MEMORIA,
    PARAMETROS,
    D,
    Siembra,
    con,
    construir_libro,
    libro_limpio,
)

A1, A2, A3 = APUS_LIMPIOS
HOY = date(2026, 10, 13)
TOL = 1e-9  # los valores guardados se releen como float de Excel
VINCULO = "file:///\\\\servidor-ficticio\\obras\\mediciones.xlsx"


@pytest.fixture(scope="module")
def limpio():
    c = libro_limpio()
    r = procesar_libro(c.datos, "limpio.xlsx", fecha_devolucion=HOY)
    return c, r


def _varios():
    apus = (
        A1,
        con(A2, cd_sin_equipos=True, utilidad_literal=D("0.02")),
        con(A3, divisor_equipos=D("12")),
    )
    return construir_libro(
        apus,
        Siembra(
            mediciones_literales=("=9.73*2.75",),
            resumen_ref_rota=True,
            nombres_externos=("MEDP1", "MEDP2"),
            procura_dif=D("5"),
            cronograma_fila_rend=23,
            vinculo_externo=VINCULO,
        ),
    )


# --- Libro limpio --------------------------------------------------------------------------------


def test_limpio_precios_y_totales_de_silice_igual_a_la_memoria(limpio):
    _, r = limpio
    assert dict(r.precios_unitarios) == {
        5: MEMORIA["componentes"]["APU-01"]["PU"],
        6: MEMORIA["componentes"]["APU-02"]["PU"],
        7: MEMORIA["componentes"]["APU-03"]["PU"],
    }
    assert r.totales_silice == {
        "SUBSINIVA": MEMORIA["SUBSINIVA"],
        "IVATOT": MEMORIA["IVATOT"],
        "TOTALGEN": MEMORIA["TOTALGEN"],
    }


def test_limpio_conjunto_exacto_de_hallazgos(limpio):
    """Sin errores sembrados quedan solo los «no aplicable» del núcleo: no hay curva (R2) ni plan
    de trabajo (R7) que reconstruir (la 1.5 no los inventa)."""
    _, r = limpio
    assert [(h.regla, h.severidad.name, h.origen_ids) for h in r.informe.hallazgos] == [
        ("R2", "INFO", ()),
        ("R7", "INFO", ()),
    ]
    assert [(f.codigo, f.accion) for f in r.hallazgos_tabla] == [
        ("R2", ACCION_INFORMADO),
        ("R7", ACCION_INFORMADO),
    ]


def test_reglas_evaluadas_y_no_evaluadas(limpio):
    _, r = limpio
    codigos = [c for c, _ in r.informe.reglas_evaluadas]
    assert codigos == [f"R{i}" for i in range(1, 8)] + ["F1"] + [f"L{i}" for i in range(1, 10)]
    assert [(c, m) for c, _, m in r.reglas_no_evaluadas] == [
        (
            "R11",
            "no se evalúa en la 1.5: no hay un mapeo de los códigos MT/MO/EQ de la empresa a "
            "MaPreX, así que ningún precio del libro tiene referencia con qué compararse",
        ),
        (
            "R12",
            "no se evalúa en la 1.5: los libros no traen la fecha de cada precio (solo la de la "
            "PORTADA), así que no se puede saber si un precio está vencido",
        ),
        ("L10", "no se recibió un PDF simple (sin modelo) para revisar"),
        (
            "L11",
            "no se recibió el PDF entregado, así que no hay totales impresos con qué cotejar",
        ),
    ]


def test_metadatos_y_fechas(limpio):
    c, r = limpio
    assert r.fecha_libro == date(2026, 7, 31)  # «Julio 2026» -> último día del mes (F-D8)
    assert r.fecha_devolucion == HOY
    assert r.presupuesto.fecha == date(2026, 7, 31)
    assert dict(r.metadatos) == {
        "sha256_origen": hashlib.sha256(c.datos).hexdigest(),
        "version": version(),
        "fecha": "2026-10-13",
        "producido_por": "Silice",
        "fecha_libro": "2026-07-31",
    }


def test_trazabilidad_dice_de_donde_sale_cada_dato(limpio):
    c, r = limpio
    filas = {t.dato: t for t in r.trazabilidad}
    assert filas["SHA-256 del libro recibido"].valor == hashlib.sha256(c.datos).hexdigest()
    assert filas["Fecha del libro"].origen == "PORTADA: «Julio 2026»"
    assert (filas["Parámetro FCAS"].valor, filas["Parámetro FCAS"].origen) == ("1.9", "INSUMOS!E16")
    assert "el núcleo recibe fcas = 0.9" in filas["Parámetro FCAS"].nota
    mt03 = next(t for t in r.trazabilidad if t.dato.startswith("Precio MT-03"))
    assert (mt03.origen, mt03.nota) == ("INSUMOS!E7", "fuente: REFERENCIAL — ajustar")
    eq01 = next(t for t in r.trazabilidad if t.dato.startswith("Precio EQ-01"))
    assert eq01.nota == "sin fuente"
    cantidades = [(t.valor, t.origen) for t in r.trazabilidad if t.dato.startswith("Cantidad")]
    assert cantidades == [
        ("120", "PRESUPUESTO!G5"),
        ("80", "PRESUPUESTO!G6"),
        ("50", "PRESUPUESTO!G7"),
    ]
    # 1 SHA + 1 fecha + 8 parámetros + 8 precios + 3 cantidades, sin avisos del mapeo.
    assert len(r.trazabilidad) == 21


# --- Fecha del libro (F-D8) ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "esperada"),
    [
        ("Julio 2026", date(2026, 7, 31)),
        ("julio de 2026", date(2026, 7, 31)),
        ("Febrero 2024", date(2024, 2, 29)),  # año bisiesto
        ("Febrero 2026", date(2026, 2, 28)),
        ("Setiembre 2026", date(2026, 9, 30)),
        ("07/2026", date(2026, 7, 31)),
        ("15/07/2026", date(2026, 7, 15)),  # día/mes/año, como en Venezuela
        ("2026-07-15", date(2026, 7, 15)),
        ("31/02/2026", None),  # día inexistente
        ("13/2026", None),  # mes 13
        ("pendiente", None),
        ("", None),
    ],
)
def test_fecha_del_libro(limpio, texto, esperada):
    _, r = limpio
    from dataclasses import replace

    libro = replace(r.libro, portada=replace(r.libro.portada, fecha_texto=texto))
    assert fecha_del_libro(libro) == esperada


def test_sin_fecha_legible_el_presupuesto_usa_la_de_devolucion():
    c = construir_libro(siembra=Siembra(fecha_texto="por definir"))
    r = procesar_libro(c.datos, "sin_fecha.xlsx", fecha_devolucion=HOY)
    assert r.fecha_libro is None
    assert r.presupuesto.fecha == HOY
    fila = next(t for t in r.trazabilidad if t.dato == "Fecha del libro")
    assert fila.origen == "PORTADA: «por definir» (no legible)"
    assert "las alertas en Bs no son contrastables" in fila.nota


def test_fecha_dada_por_el_usuario_manda():
    r = procesar_libro(
        libro_limpio().datos, "l.xlsx", fecha_libro=date(2026, 8, 15), fecha_devolucion=HOY
    )
    assert r.fecha_libro == date(2026, 8, 15)
    fila = next(t for t in r.trazabilidad if t.dato == "Fecha del libro")
    assert fila.origen == "dada por el usuario"


# --- Errores en la frontera ----------------------------------------------------------------------


def test_fcas_menor_que_uno_no_se_puede_interpretar():
    p = {**PARAMETROS, "FCAS": D("0.9")}
    c = construir_libro(siembra=Siembra(parametros=p))
    with pytest.raises(LibroNoInterpretable, match="El FCAS del libro"):
        procesar_libro(c.datos, "fcas.xlsx", fecha_devolucion=HOY)


def test_rendimiento_cero_se_traduce_con_el_nombre_de_la_hoja():
    c = construir_libro(siembra=Siembra(parches={"APU-01!F19": (D("0"), None)}))
    with pytest.raises(LibroNoInterpretable, match=r"El APU APU-01 \(partida 1\) no se puede"):
        procesar_libro(c.datos, "rend0.xlsx", fecha_devolucion=HOY)


# --- Ida y vuelta --------------------------------------------------------------------------------


def _valores(datos: bytes, hoja: str, celdas: list[str]) -> list[float]:
    wb = openpyxl.load_workbook(io.BytesIO(datos), data_only=True)
    return [wb[hoja][c].value for c in celdas]


def test_devolucion_del_limpio_lleva_los_valores_de_silice_y_vuelve_limpia(limpio):
    _, r = limpio
    dev = devolver(r)
    pu = _valores(dev, "PRESUPUESTO", ["P5", "P6", "P7", "Q10", "Q11", "Q12"])
    esperados = [
        MEMORIA["componentes"]["APU-01"]["PU"],
        MEMORIA["componentes"]["APU-02"]["PU"],
        MEMORIA["componentes"]["APU-03"]["PU"],
        MEMORIA["SUBSINIVA"],
        MEMORIA["IVATOT"],
        MEMORIA["TOTALGEN"],
    ]
    for obtenido, esperado in zip(pu, esperados, strict=True):
        assert abs(obtenido - float(esperado)) <= TOL
    releido = leer_libro(dev, "devuelto.xlsx")
    assert reglas_del_libro(releido) == []
    r2 = procesar_libro(dev, "devuelto.xlsx", fecha_devolucion=HOY)
    assert dict(r2.precios_unitarios) == dict(r.precios_unitarios)
    assert [h.regla for h in r2.informe.hallazgos] == ["R2", "R7"]


def test_devolucion_corrige_lo_que_no_admite_dos_lecturas_y_conserva_lo_demas():
    """F-D7. Antes: F1, L1×3, L4, L5×3, L6×2, L7, L9×3. Después de la devolución: quedan la
    utilidad del 2 % y el `/12` (L6 «a confirmar», se conservan), las medidas escritas en
    MEDICIONES (L7, informado) y la lista de compras escrita a mano en PROCURA (L9: su total es un
    número, no una fórmula que Silice pueda rehacer)."""
    c = _varios()
    r = procesar_libro(c.datos, "varios.xlsx", fecha_devolucion=HOY)
    antes = sorted((h.regla, h.severidad.name) for h in r.informe.hallazgos)
    assert antes == sorted(
        [("F1", "ERROR")]
        + [("L1", "ERROR")] * 3
        + [("L4", "ERROR")]
        + [("L5", "ERROR"), ("L5", "ADVERTENCIA"), ("L5", "ADVERTENCIA")]
        + [("L6", "ADVERTENCIA")] * 2
        + [("L7", "INFO")]
        + [("L9", "ERROR")] * 3
        + [("R2", "INFO"), ("R7", "INFO")]
    )
    acciones = {f.codigo: f.accion for f in r.hallazgos_tabla}
    assert acciones["F1"] == acciones["L4"] == acciones["L1"] == ACCION_CORREGIDO
    assert acciones["L6"] == ACCION_A_CONFIRMAR
    assert acciones["L7"] == ACCION_INFORMADO

    dev = devolver(r)
    despues = reglas_del_libro(leer_libro(dev, "devuelto.xlsx"))
    assert sorted((h.regla, h.severidad.name) for h in despues) == [
        ("L6", "ADVERTENCIA"),
        ("L6", "ADVERTENCIA"),
        ("L7", "INFO"),
        ("L9", "ERROR"),
    ]
    utilidad = next(h for h in despues if h.regla == "L6" and h.impacto is not None)
    # Con el equipo ya dentro del CD: SUB = 24,96875 × 1,1 = 27,465625;
    # (0,10 − 0,02) × 27,465625 × 80 = 175,78.
    assert utilidad.impacto == D("175.78")
    assert next(h for h in despues if h.regla == "L9").impacto == D("5.00")
    # El P.U. de la partida 2 en la devolución es el de Silice (no el guardado sin equipos):
    # 24,96875 × 1,1 × 1,02 = 28,0149375.
    assert r.precios_unitarios[6] == D("28.0149375")
    (p6,) = _valores(dev, "PRESUPUESTO", ["P6"])
    assert abs(p6 - 28.0149375) <= TOL
    r2 = procesar_libro(dev, "devuelto.xlsx", fecha_devolucion=HOY)
    assert dict(r2.precios_unitarios) == dict(r.precios_unitarios)
    assert "F1" not in {h.regla for h in r2.informe.hallazgos}


def test_mismo_libro_misma_devolucion(limpio):
    c, r = limpio
    assert devolver(r) == devolver(r)
    r2 = procesar_libro(c.datos, "limpio.xlsx", fecha_devolucion=HOY)
    assert devolver(r2) == devolver(r)


# --- Alertas dentro del proceso ------------------------------------------------------------------


def test_alertas_con_otra_version_y_tasas():
    otro_insumos = tuple(i if i.codigo != "MT-02" else _con_precio(i, D("20")) for i in INSUMOS)
    otro = construir_libro(siembra=Siembra(insumos=otro_insumos)).datos
    tasas = {date(2026, 7, 31): D("100"), HOY: D("110")}
    ctx = ContextoPrecios(tasa_en=lambda f: tasas.get(f))
    r = procesar_libro(
        libro_limpio().datos,
        "b2.xlsx",
        fecha_devolucion=HOY,
        contexto=ctx,
        otro=otro,
        otro_nombre="b1.xlsx",
    )
    version_ = [(a.codigo, a.variacion) for a in r.alertas if a.tipo == TIPO_VERSION]
    assert version_ == [("MT-02", (D("25") - D("20")) / D("20"))]
    mt02 = next(a for a in r.alertas if a.tipo == TIPO_BS and a.codigo == "MT-02")
    # 25 USD × 110 = 2 750 Bs; (2 750 − 2 500) ÷ 2 500 = 0,1
    assert (mt02.tasa, mt02.precio_bs, mt02.variacion) == (D("110"), D("2750"), D("0.1"))


def _con_precio(insumo, precio):
    from dataclasses import replace

    return replace(insumo, precio=precio)


def test_servicios_desde_la_sesion_de_la_instalacion(sesion):
    ctx = servicios_desde_sesion(sesion, umbral=D("0.07"))
    assert ctx.umbral == D("0.07")
    assert callable(ctx.tasa_en)
    # La base de prueba no tiene lista de empresa: sin precios propios no hay contraste.
    r = procesar_libro(libro_limpio().datos, "l.xlsx", fecha_devolucion=HOY, contexto=ctx)
    assert all(a.tipo != "base de la empresa" for a in r.alertas)
