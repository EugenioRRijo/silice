"""Nombres llanos de reglas (Lote K, punto 6) y columna Estado en Control (punto 2).

Cada respuesta de hallazgos conserva el código interno (`regla` o `codigo`) y añade `nombre_regla`
con el nombre legible del catálogo. La columna Estado de valuaciones presenta severidad en español
con mayúscula inicial, mensaje legible y el código de regla al final entre paréntesis.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from adapters.hoja_empresa.reglas import REGLAS_LIBRO
from api.rutas import auditorias, auditorias_libro, libros, revision
from aplicacion.control_hallazgos import hallazgos_de_valuaciones
from aplicacion.control_tablas import estado_de_valuaciones
from aplicacion.nombres_reglas import NOMBRES_DE_REGLAS, nombre_de_regla
from core.contracts.verificacion import Hallazgo, Severidad
from core.verification.precios import PrecioFueraDeRango, PrecioVencido
from core.verification.reglas import REGLAS
from core.verification.valuaciones import FuenteYFechasDeValuacion, ValuacionDentroDelPresupuesto
from fusion.proceso import REGLA_F1, REGLA_L10, REGLA_L11


def test_el_catalogo_cubre_las_reglas_del_nucleo_libro_y_fusion() -> None:
    esperados = (
        {r.codigo for r in REGLAS}
        | {codigo for codigo, _ in REGLAS_LIBRO}
        | {
            REGLA_F1[0],
            REGLA_L10[0],
            REGLA_L11[0],
            PrecioFueraDeRango.codigo,
            PrecioVencido.codigo,
            ValuacionDentroDelPresupuesto.codigo,
            FuenteYFechasDeValuacion.codigo,
        }
        | {"R8", "R9", "R10", "R15", "R16", "R17", "VR"}
        | {f"VR{n}" for n in range(1, 9)}
        | {f"AH{n}" for n in range(1, 13)}
    )
    faltan = sorted(esperados - set(NOMBRES_DE_REGLAS))
    assert faltan == []
    assert all(NOMBRES_DE_REGLAS[c].strip() for c in esperados)


def test_nombre_de_regla_devuelve_tildes_y_vacio_si_desconocida() -> None:
    assert nombre_de_regla("R3") == "Consistencia matemática"
    assert nombre_de_regla("R13") == "Valuación dentro del presupuesto"
    assert nombre_de_regla("R14") == "Fuente y fechas de la valuación"
    assert nombre_de_regla("L4") == "Componente fuera del total"
    assert nombre_de_regla("F1") == "P.U. recalculado"
    assert nombre_de_regla("AH1") == "Precio unitario del APU contra el recalculado"
    assert nombre_de_regla("DESCONOCIDA") == ""


def test_estado_de_valuaciones_usa_severidad_y_mensaje_en_espanol_y_elige_la_mas_grave() -> None:
    hallazgos = (
        Hallazgo(
            regla="R14",
            severidad=Severidad.ADVERTENCIA,
            descripcion="la valuacion V-01 no tiene fecha",
            origen_ids=("valuacion:V-01",),
        ),
        Hallazgo(
            regla="R14",
            severidad=Severidad.ERROR,
            descripcion="la valuacion V-01 no tiene inspector",
            origen_ids=("valuacion:V-01",),
        ),
        Hallazgo(
            regla="R13",
            severidad=Severidad.INFO,
            descripcion="la valuacion V-02 no tiene fecha",
            origen_ids=("valuacion:V-02",),
        ),
        Hallazgo(
            regla="R13",
            severidad=Severidad.CRITICO,
            descripcion="la valuacion V-03 no tiene numero",
            origen_ids=("valuacion:V-03",),
        ),
    )
    resultado = SimpleNamespace(
        instantanea=SimpleNamespace(
            valuaciones=(
                SimpleNamespace(clave="V-01"),
                SimpleNamespace(clave="V-02"),
                SimpleNamespace(clave="V-03"),
            )
        ),
        informe=SimpleNamespace(hallazgos=hallazgos),
    )
    estados = estado_de_valuaciones(resultado)
    assert estados == {
        "V-01": "Error: La valuación V-01 no tiene inspector. (R14)",
        "V-02": "Información: La valuación V-02 no tiene fecha. (R13)",
        "V-03": "Crítico: La valuación V-03 no tiene número. (R13)",
    }
    filas = hallazgos_de_valuaciones(resultado)
    assert [f["NombreRegla"] for f in filas] == [
        "Valuación dentro del presupuesto",
        "Fuente y fechas de la valuación",
        "Fuente y fechas de la valuación",
        "Valuación dentro del presupuesto",
    ]


def test_los_esquemas_de_hallazgos_de_la_api_incluyen_nombre_regla() -> None:
    de_libro = libros._hallazgo_libro(
        SimpleNamespace(
            codigo="L4",
            severidad="ERROR",
            descripcion="El costo directo no suma",
            celda="APU1!E10",
            impacto=Decimal("12.50"),
            accion="revisar",
        )
    )
    assert (de_libro.codigo, de_libro.nombre_regla) == ("L4", "Componente fuera del total")

    guardada = auditorias_libro._detalle(
        SimpleNamespace(
            id=1,
            nombre_archivo="demo.xlsx",
            fecha_hora=datetime(2026, 11, 20, 10, 0),
            tipo="libro",
            errores=1,
            advertencias=0,
            usuario="ana",
            sha256="a" * 64,
            fecha_libro=date(2026, 11, 1),
            total_libro=Decimal("100"),
            total_silice=Decimal("100"),
            informativos=0,
            atipicos=0,
            recortado=False,
            hallazgos=[
                SimpleNamespace(
                    regla="L2",
                    hoja="PRESUPUESTO",
                    celda="C5",
                    severidad="ERROR",
                    mensaje="Enlace roto",
                )
            ],
        )
    )
    assert (guardada.hallazgos[0].regla, guardada.hallazgos[0].nombre_regla) == (
        "L2",
        "Enlace partida ↔ APU roto",
    )

    h_core = Hallazgo(
        regla="R11",
        severidad=Severidad.ADVERTENCIA,
        descripcion="precio fuera de rango",
        origen_ids=("partida:P-1",),
        impacto=Decimal("5.00"),
    )
    rev = revision._hallazgo(h_core)
    assert (rev.regla, rev.nombre_regla) == ("R11", "Precio fuera de rango")

    aud = auditorias._hallazgo(h_core)
    assert (aud.regla, aud.nombre_regla) == ("R11", "Precio fuera de rango")
