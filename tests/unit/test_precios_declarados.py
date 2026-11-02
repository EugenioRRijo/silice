"""El precio nuevo de un material como precio del corte (MP-7, Tarea 25; diseño §11, meta 4).

`aplicacion/precios_declarados.py` guarda el precio que la persona declara para un material de la
obra (desde el estudio de mercado o al recibir una compra) y arma con él los precios del corte del
control: por partida de la línea base, su composición congelada con el precio de cada material
sustituido por el último declarado hasta el corte, calculada con los parámetros de esa versión.

Un precio en otra moneda ya no se rechaza: se convierte (`test_precios_declarados_convertidos.py`).

Oráculos de la memoria de OB-S2 (`tests/fixtures/memorias/control_ob_s2.md`), escritos a mano y
ninguno sacado del código bajo prueba: el material de B pasa de 3,00 a 4,00 (1 m por m de tubería:
`u'` de B = 5 + (4 − 3) × 1 = 6,00) y el de C de 12,00 a 14,10 (1 m3 por m3: 20 + 2,10 = 22,10); A
no tiene material y queda en 10,00 (§1). Con V-01 y V-02 al corte del 13/11/2026 (A 90, B 60) la
separación es ΔP = 90 × 0 + 60 × (5 − 6) = −60,00 y ΔC = 1 260 − 1 280 = −20,00; al término
VAC_precio = −(200 × 1 + 100 × 2,10) = −410,00 (§3). En la perspectiva precio, PU = u × 1,265:
B 6,325 → 7,59 (§6), A 12,65 y C 25,30.

Las bases viven en `tmp_path` (`preparar_base`): nada en `data/`.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import inspect, select

from aplicacion import control
from aplicacion.mercado import NoExiste
from aplicacion.precios_declarados import (
    ReglaDelCorte,
    declarar_precio_del_corte,
    precios_declarados,
)
from aplicacion.tablas_corte import PrecioDelCorte
from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob

D = Decimal
TUBO = "Material de Tuberia de drenaje"
RELLENO = "Material de Relleno compactado"
AHORA = datetime(2026, 11, 20, 8, 0)
QUIEN = "Ana <ana>"


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator:
    ruta = tmp_path / "carpeta.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as abierta:
            yield abierta
            abierta.rollback()
    finally:
        motor.dispose()


def _obra(sesion, perspectiva: str = "costo"):
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion, perspectiva)
    ob.registrar_v01_y_v02(sesion)
    sesion.commit()
    return sesion


@pytest.fixture
def obra(sesion):
    return _obra(sesion)


def _declarar(sesion, descripcion: str, unidad: str, precio: str, fecha: date, **extra) -> None:
    datos = {
        "descripcion": descripcion,
        "unidad": unidad,
        "precio": D(precio),
        "fecha": fecha,
        "fuente": "Estudio de mercado: precio propio",
        "responsable": QUIEN,
        "ahora": AHORA,
        **extra,
    }
    declarar_precio_del_corte(sesion, ob.NOMBRE, **datos)
    sesion.commit()


def _precios(sesion, corte: date = ob.CORTE, perspectiva: str = "costo"):
    return precios_declarados(sesion, ob.NOMBRE, Catalogo(sesion), corte, perspectiva)


# --- sin declarar nada ------------------------------------------------------------------------


def test_sin_precios_declarados_no_hay_precios_del_corte(obra) -> None:
    assert _precios(obra) is None


# --- el unitario de la partida que usa el material, y solo el de ella ---------------------------


def test_el_material_de_b_de_3_a_4_sube_b_en_1_y_las_demas_no_cambian(obra) -> None:
    _declarar(obra, TUBO, "m", "4.00", date(2026, 11, 10))
    precios = _precios(obra)
    assert precios.metodo == "declarados"
    assert precios.fuente == "Precios declarados al 13/11/2026: 1 insumo"
    assert dict(precios.unitarios) == {"OB-A": D("10.00"), "OB-B": D("6.00"), "OB-C": D("20.00")}


def test_los_dos_materiales_de_la_memoria_dan_los_unitarios_del_corte(obra) -> None:
    _declarar(obra, TUBO, "m", "4.00", date(2026, 11, 10))
    _declarar(obra, RELLENO, "m3", "14.10", date(2026, 11, 12))
    precios = _precios(obra)
    assert precios.fuente == "Precios declarados al 13/11/2026: 2 insumos"
    assert dict(precios.unitarios) == {"OB-A": D("10.00"), "OB-B": D("6.00"), "OB-C": D("22.10")}


def test_con_los_declarados_el_control_separa_el_desvio_de_precio(obra) -> None:
    _declarar(obra, TUBO, "m", "4.00", date(2026, 11, 10))
    _declarar(obra, RELLENO, "m3", "14.10", date(2026, 11, 12))
    resultado = control.calcular_el_control(
        obra, ob.NOMBRE, Catalogo(obra), corte=ob.CORTE, precios=_precios(obra)
    )
    separacion = resultado.separacion
    assert separacion.precio == D("-60.00")
    assert separacion.consumo == D("-20.00")
    assert separacion.vac_precio == D("-410.00")
    assert "precio" not in separacion.no_disponible


def test_un_declarado_posterior_al_corte_no_cuenta(obra) -> None:
    _declarar(obra, TUBO, "m", "4.00", date(2026, 11, 10))
    _declarar(obra, RELLENO, "m3", "14.10", date(2026, 11, 16))
    precios = _precios(obra)
    assert precios.fuente == "Precios declarados al 13/11/2026: 1 insumo"
    assert precios.unitarios["OB-C"] == D("20.00")
    # al 16/11 ya cuenta: 20 + (14,10 − 12) × 1 = 22,10
    assert _precios(obra, date(2026, 11, 16)).unitarios["OB-C"] == D("22.10")


def test_solo_declarados_despues_del_corte_es_como_no_tener_ninguno(obra) -> None:
    _declarar(obra, TUBO, "m", "4.00", date(2026, 11, 16))
    assert _precios(obra) is None


def test_manda_el_ultimo_declarado_hasta_el_corte(obra) -> None:
    _declarar(obra, TUBO, "m", "3.50", date(2026, 11, 5))
    _declarar(obra, TUBO, "m", "4.00", date(2026, 11, 10))
    # el mismo día manda el último registrado: 5 + (4,50 − 3) = 6,50
    _declarar(obra, RELLENO, "m3", "13.00", date(2026, 11, 11))
    _declarar(obra, RELLENO, "m3", "12.50", date(2026, 11, 11))
    precios = _precios(obra)
    assert precios.unitarios["OB-B"] == D("6.00")
    # 20 + (12,50 − 12) × 1 = 20,50
    assert precios.unitarios["OB-C"] == D("20.50")
    assert precios.fuente == "Precios declarados al 13/11/2026: 2 insumos"


def test_en_la_perspectiva_precio_cuenta_el_precio_unitario(sesion) -> None:
    obra = _obra(sesion, "precio")
    _declarar(obra, TUBO, "m", "4.00", date(2026, 11, 10))
    precios = _precios(obra, perspectiva="precio")
    # PU = u × 1,265: A 10 × 1,265 = 12,65; B 6 × 1,265 = 7,59; C 20 × 1,265 = 25,30
    assert dict(precios.unitarios) == {
        "OB-A": D("12.65"),
        "OB-B": D("7.59"),
        "OB-C": D("25.30"),
    }


def test_la_unidad_se_compara_normalizada(obra) -> None:
    _declarar(obra, RELLENO, " M3 ", "14.10", date(2026, 11, 10))
    assert _precios(obra).unitarios["OB-C"] == D("22.10")


# --- la declaración ----------------------------------------------------------------------------


def test_la_declaracion_queda_con_quien_cuando_la_fuente_y_la_moneda_de_la_obra(obra) -> None:
    _declarar(obra, TUBO, "m", "4.00", date(2026, 11, 10))
    fila = obra.scalars(select(PrecioDelCorte)).one()
    assert (
        fila.descripcion_insumo,
        fila.unidad,
        fila.precio,
        fila.moneda,
        fila.fecha,
        fila.fuente,
        fila.responsable,
        fila.fecha_hora,
    ) == (
        TUBO,
        "m",
        D("4.00"),
        "USD",
        date(2026, 11, 10),
        "Estudio de mercado: precio propio",
        QUIEN,
        AHORA,
    )


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        ({"precio": D("0")}, "El precio del corte debe ser mayor que cero."),
        ({"precio": D("-1")}, "El precio del corte debe ser mayor que cero."),
        ({"fecha": date(2026, 11, 21)}, "La fecha del precio no puede ser posterior a hoy."),
        ({"fuente": "  "}, "Diga de dónde sale el precio (la fuente)."),
        ({"fuente": "x" * 301}, "La fuente del precio admite hasta 300 caracteres."),
    ],
)
def test_una_regla_rota_no_guarda_nada(obra, cambio: dict, mensaje: str) -> None:
    datos = {
        "descripcion": TUBO,
        "unidad": "m",
        "precio": D("4.00"),
        "fecha": date(2026, 11, 10),
        "fuente": "Estudio de mercado: precio propio",
        "responsable": QUIEN,
        "ahora": AHORA,
        **cambio,
    }
    with pytest.raises(ReglaDelCorte) as error:
        declarar_precio_del_corte(obra, ob.NOMBRE, **datos)
    assert str(error.value) == mensaje
    obra.rollback()
    assert obra.scalars(select(PrecioDelCorte)).all() == []


def test_un_material_que_no_esta_en_la_linea_base_no_existe(obra) -> None:
    with pytest.raises(NoExiste) as error:
        _declarar(obra, "Cemento gris", "saco", "20.00", date(2026, 11, 10))
    assert (
        str(error.value) == "«Cemento gris» no es un material de la línea base de la obra «OB-S2»."
    )
    # un equipo de la obra tampoco: solo los materiales tienen precio del corte
    with pytest.raises(NoExiste):
        _declarar(obra, "Equipo de Excavacion de zanja", "", "1.00", date(2026, 11, 10))


def test_una_obra_que_no_existe(obra) -> None:
    with pytest.raises(NoExiste) as error:
        declarar_precio_del_corte(
            obra,
            "NO-HAY",
            descripcion=TUBO,
            unidad="m",
            precio=D("4"),
            fecha=date(2026, 11, 10),
            fuente="f",
            responsable=QUIEN,
            ahora=AHORA,
        )
    assert str(error.value) == "No hay ninguna obra «NO-HAY» en esta carpeta de trabajo."


def test_una_obra_sin_linea_base_no_admite_precios_del_corte(sesion) -> None:
    ob.sembrar(sesion)
    sesion.commit()
    with pytest.raises(ReglaDelCorte) as error:
        _declarar(sesion, TUBO, "m", "4.00", date(2026, 11, 10))
    assert str(error.value) == (
        "La obra «OB-S2» no tiene línea base de control: declárela antes de declarar precios "
        "del corte."
    )


# --- una base que todavía no tiene la tabla ------------------------------------------------------


def test_una_base_sin_la_tabla_se_lee_sin_declarados_y_la_crea_al_declarar(obra) -> None:
    obra.connection().exec_driver_sql("DROP TABLE mp_precio_corte")
    obra.commit()
    assert _precios(obra) is None
    assert not inspect(obra.connection()).has_table("mp_precio_corte")
    _declarar(obra, TUBO, "m", "4.00", date(2026, 11, 10))
    assert _precios(obra).unitarios["OB-B"] == D("6.00")
