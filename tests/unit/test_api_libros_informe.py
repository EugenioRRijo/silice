"""`informe_de` (api/rutas/libros_informe.py): del resultado de la auditoría al informe ya escrito.

Un `ResultadoFusion` FICTICIO mínimo (solo lo que `informe_de` lee); los oráculos están escritos a
mano: 154,275 al alza es «154,28» y 1.234,565 es «1.234,57» (decisión de Eugenio del 2026-11-17).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from adapters.hoja_empresa.modelo import FilaHallazgo
from api.rutas.libros_informe import informe_de

D = Decimal
EMITIDO = date(2026, 11, 19)


def _resultado(**cambios):
    base = {
        "libro": SimpleNamespace(
            nombre="obra.xlsx",
            sha256="0123456789abcdef" * 4,
            totales={"SUBSINIVA": D("4203.93325"), "TOTALGEN": D("4876.56257")},
        ),
        "totales_silice": {"SUBSINIVA": D("4358.20825"), "TOTALGEN": D("5055.52157")},
        "fecha_libro": date(2026, 7, 31),
        "fecha_devolucion": date(2026, 10, 13),
        "informe": SimpleNamespace(cumple=False),
        "hallazgos_tabla": (
            FilaHallazgo(
                "F1", "ERROR", "Falta el IVA", "PRESUPUESTO!P12", D("154.275"), "corregido"
            ),
            FilaHallazgo("R2", "INFO", "Aviso", "PORTADA!B3", None, "informado"),
            FilaHallazgo("L9", "ERROR", "Sobra", "APU-01!G9", D("-1234.565"), "a confirmar"),
        ),
    }
    return SimpleNamespace(**{**base, **cambios})


def test_el_informe_escribe_las_fechas_el_resultado_el_conteo_y_la_huella():
    i = informe_de(_resultado(), EMITIDO)
    assert (i.libro, i.fecha_libro, i.fecha_devolucion, i.emitido) == (
        "obra.xlsx",
        "31/07/2026",
        "13/10/2026",
        "19/11/2026",
    )
    assert i.veredicto == "No cumple"
    assert i.conteo == ("2 errores", "1 aviso informativo")
    assert i.huella == "0123456789ab"


def test_los_totales_van_del_libro_frente_a_silice_con_coma_y_punto_de_miles():
    i = informe_de(_resultado(), EMITIDO)
    assert [(t.concepto, t.libro, t.silice) for t in i.totales] == [
        ("Subtotal sin IVA", "4.203,93", "4.358,21"),
        ("Total general", "4.876,56", "5.055,52"),
    ]


def test_un_total_que_falta_de_un_lado_sale_con_raya_y_si_falta_de_los_dos_no_sale():
    libro = SimpleNamespace(
        nombre="obra.xlsx", sha256="a" * 64, totales={"TOTALGEN": D("10"), "IVATOT": None}
    )
    i = informe_de(_resultado(libro=libro, totales_silice={"SUBSINIVA": D("7.5")}), EMITIDO)
    assert [(t.concepto, t.libro, t.silice) for t in i.totales] == [
        ("Subtotal sin IVA", "—", "7,50"),
        ("Total general", "10,00", "—"),
    ]


def test_sin_fecha_del_libro_lo_dice_y_un_libro_sin_totales_no_tumba_el_informe():
    libro = SimpleNamespace(nombre="obra.xlsx", sha256="a" * 64, totales=None)
    i = informe_de(_resultado(libro=libro, fecha_libro=None, totales_silice={}), EMITIDO)
    assert i.fecha_libro == "sin fecha"
    assert i.totales == ()


def test_cada_hallazgo_con_su_impacto_al_alza_vacio_si_no_tiene_y_con_su_signo():
    filas = informe_de(_resultado(), EMITIDO).hallazgos
    assert [(h.codigo, h.severidad, h.impacto, h.accion) for h in filas] == [
        ("F1", "Error", "154,28", "corregido"),
        ("R2", "Información", "", "informado"),
        ("L9", "Error", "-1.234,57", "a confirmar"),
    ]
    assert filas[0].celda == "PRESUPUESTO!P12"


def test_un_libro_que_cumple_lo_dice_y_sin_hallazgos_el_conteo_tambien():
    i = informe_de(_resultado(informe=SimpleNamespace(cumple=True), hallazgos_tabla=()), EMITIDO)
    assert i.veredicto == "Cumple"
    assert i.conteo == ("Sin hallazgos",)
    assert i.hallazgos == ()
