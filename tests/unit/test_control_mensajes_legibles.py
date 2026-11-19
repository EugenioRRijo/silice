"""Los mensajes de Control de obra nombran el campo como lo ve la persona, con tildes.

Prueba en vivo del 2026-11-18 (frente C, hallazgo 5): «hasta: '' no es una fecha (AAAA-MM-DD)»,
«monto: '' no es un numero decimal», «la fuente del cambio es obligatoria» cuando el campo se llama
«Motivo», «valuacion(es)». Los que nacen en `core/` se traducen en `aplicacion` sobre su frase fija
o se adelantan con una comprobación propia; `core/` no cambia.

Obra ficticia OB-S2 (`tests/fixtures/control_ob_s2.py`); nada en `data/`.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from aplicacion import control
from core.budget.valuaciones import valuaciones_registradas
from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob

HOY = date(2026, 11, 18)


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as abierta:
            ob.sembrar(abierta)
            ob.declarar_linea_base(abierta)
            ob.registrar_v01_y_v02(abierta)
            abierta.commit()
            yield abierta
            abierta.rollback()
    finally:
        motor.dispose()


def _registrar(sesion, **cambios):
    datos = dict(
        numero="V-03",
        desde="2026-11-16",
        hasta="2026-11-18",
        fecha="2026-11-18",
        inspector=ob.INSPECTOR,
        filas=[{"Partida": "OB-B", "Cantidad": "10"}],
        fuente=ob.FUENTE,
        responsable=ob.RESPONSABLE,
        hoy=HOY,
    )
    datos.update(cambios)
    return control.registrar_y_controlar(sesion, ob.NOMBRE, Catalogo(sesion), **datos)


def _mensaje(funcion, *args, **kwargs) -> str:
    with pytest.raises(control.ControlInvalido) as error:
        funcion(*args, **kwargs)
    return str(error.value)


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"hasta": ""}, "Falta la fecha «Período hasta»."),
        ({"hasta": "18/11/2026"}, "«Período hasta»: «18/11/2026» no es una fecha válida."),
        ({"desde": ""}, "Falta la fecha «Período desde»."),
        ({"fecha": "ayer"}, "«Fecha de la valuación»: «ayer» no es una fecha válida."),
        (
            {"filas": [{"Partida": "OB-B", "Cantidad": "diez"}]},
            "«Cantidad 1» no es un número válido.",
        ),
        (
            {"filas": [{"Partida": "OB-B", "Cantidad": "1", "Fecha de medicion": "x"}]},
            "«Fecha de medición 1»: «x» no es una fecha válida.",
        ),
        ({"filas": [{"Partida": "", "Cantidad": "1"}]}, "Línea 1: falta la partida."),
        (
            {"fuente": " "},
            "La fuente de la valuación es obligatoria: diga de dónde sale (acta, oficio).",
        ),
    ],
)
def test_registrar_una_valuacion_dice_el_campo_de_la_pantalla(sesion, cambios, mensaje) -> None:
    assert _mensaje(_registrar, sesion, **cambios) == mensaje
    assert [v.numero for v in valuaciones_registradas(sesion, ob.NOMBRE)] == ["V-01", "V-02"]


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"monto": ""}, "Falta la cifra «Monto»."),
        ({"monto": "cien"}, "«Monto» no es un número válido."),
        ({"fecha": ""}, "Falta la fecha «Fecha»."),
        (
            {"fuente": ""},
            "La fuente del costo es obligatoria: diga de dónde sale (factura, libro de obra).",
        ),
    ],
)
def test_anotar_un_costo_dice_el_campo_de_la_pantalla(sesion, cambios, mensaje) -> None:
    datos = dict(monto="10.00", moneda="USD", fecha="2026-11-12", fuente="factura 1")
    datos.update(cambios)
    assert (
        _mensaje(
            control.registrar_costo_real, sesion, ob.NOMBRE, responsable=ob.RESPONSABLE, **datos
        )
        == mensaje
    )


def test_anular_sin_motivo_pide_el_motivo_y_no_la_fuente(sesion) -> None:
    (primera, _) = valuaciones_registradas(sesion, ob.NOMBRE)
    assert _mensaje(control.anular, sesion, primera.id, motivo="", responsable="x") == (
        "El motivo de la anulación es obligatorio: diga por qué se anula y con qué respaldo."
    )


@pytest.mark.parametrize(
    ("campo", "valor", "mensaje"),
    [
        ("desde", "02/11/2026", "«Vigente desde»: «02/11/2026» no es una fecha válida."),
        ("inicio", "", "Falta la fecha «Inicio de obra»."),
        ("dias_por_periodo", "cinco", "«Días hábiles por período» no es un número válido."),
        (
            "dias_por_periodo",
            "2.5",
            "«Días hábiles por período» debe ser un número entero: «2.5».",
        ),
        ("feriados", "2026-13-40", "«Feriados»: «2026-13-40» no es una fecha válida."),
        (
            "fuente",
            "",
            "La fuente de la línea base es obligatoria: diga de dónde sale (acta, contrato).",
        ),
    ],
)
def test_declarar_la_linea_base_dice_el_campo_de_la_pantalla(
    sesion, campo, valor, mensaje
) -> None:
    datos = dict(
        desde="2026-11-20", perspectiva="costo", inicio="2026-11-02", dias_por_periodo="5",
        feriados="", fuente=ob.FUENTE, responsable=ob.RESPONSABLE,
    )  # fmt: skip
    datos[campo] = valor
    assert _mensaje(control.declarar_linea_base, sesion, ob.NOMBRE, ob.CODIGO, **datos) == mensaje


def test_el_informe_previo_del_xlsx_lleva_tildes(tmp_path: Path) -> None:
    lectura = control.leer_excel(ob.escribir_xlsx(tmp_path / "ob_s2.xlsx"))
    assert list(lectura.informe) == [
        "Hoja «Valuaciones»: 2 valuación(es)",
        "Hoja «Lineas»: 3 línea(s)",
        "Hoja «Costos»: 1 costo(s)",
    ]
