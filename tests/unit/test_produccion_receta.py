"""Receta de la planta y consumos al producir mezcla (Tarea 3 del plan vial). Datos FICTICIOS.

Oraculos a mano: ningun valor sale de la funcion bajo prueba. La mezcla `MZ-1` se hace con 0,94 t de
agregado propio `AGR-12`, 0,05 t de cemento asfaltico comprado `CA-30` y 8 l de gasoil comprado
`GO`: en toneladas suman 0,99 (el gasoil va en litros y no cuenta). Producir 100 t consume
0,94 x 100 = 94 t de `AGR-12` y nada de lo comprado.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from produccion.inventario import crear_material, existencia, registrar_entrada
from produccion.modelo import METADATA_PRODUCCION, Movimiento
from produccion.receta import (
    TOLERANCIA_MASA,
    Componente,
    ErrorDeReceta,
    producido_en_periodo,
    producir_con_receta,
    receta_vigente,
    registrar_receta,
)

D = Decimal
AHORA = datetime(2026, 11, 20, 9, 0, 0)
OCTUBRE = date(2026, 10, 1)
NOVIEMBRE = date(2026, 11, 1)


def _c(codigo: str, cantidad: str, unidad: str = "t", tipo: str = "propio") -> Componente:
    return Componente(codigo, D(cantidad), unidad, tipo)


def _mezcla() -> list[Componente]:
    return [
        _c("AGR-12", "0.94"),
        _c("CA-30", "0.05", tipo="comprado"),
        _c("GO", "8", "l", "comprado"),
    ]


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    METADATA_PRODUCCION.create_all(motor)
    with Session(motor) as s:
        yield s
    motor.dispose()


def _planta(sesion: Session) -> None:
    crear_material(
        sesion, codigo="AGR-12", nombre="Agregado 1/2", unidad_venta="t", existencia_minima=D(0)
    )
    crear_material(sesion, codigo="MZ-1", nombre="Mezcla", unidad_venta="t", existencia_minima=D(0))


def _movimientos(sesion: Session) -> int:
    return sesion.scalar(select(func.count()).select_from(Movimiento)) or 0


def _registrar(sesion: Session, componentes, vigente_desde=OCTUBRE, producto="MZ-1") -> int:
    return registrar_receta(
        sesion,
        producto,
        componentes,
        fuente="dosificacion ficticia 1",
        vigente_desde=vigente_desde,
        usuario="ana",
        ahora=AHORA,
    )


def test_la_tolerancia_es_la_del_plan() -> None:
    assert TOLERANCIA_MASA == D("0.02")


def test_receta_masa_debe_sumar_uno(sesion) -> None:
    assert _registrar(sesion, _mezcla()) > 0  # 0,94 + 0,05 = 0,99 pasa
    with pytest.raises(ValueError, match="suman 0,95 t"):
        _registrar(sesion, [_c("AGR-12", "0.90"), _c("CA-30", "0.05", tipo="comprado")])


def test_la_tolerancia_incluye_sus_bordes(sesion) -> None:
    assert _registrar(sesion, [_c("AGR-12", "0.98")]) > 0  # 1 - 0,02
    assert _registrar(sesion, [_c("AGR-12", "1.02")]) > 0  # 1 + 0,02
    with pytest.raises(ValueError, match="suman 0,979 t"):
        _registrar(sesion, [_c("AGR-12", "0.979")])
    with pytest.raises(ValueError, match="suman 1,021 t"):
        _registrar(sesion, [_c("AGR-12", "1.021")])


def test_componente_invalido_se_rechaza() -> None:
    with pytest.raises(ValueError, match="tipo"):
        _c("AGR-12", "0.94", tipo="regalado")
    with pytest.raises(ValueError, match="unidad"):
        _c("AGR-12", "0.94", unidad="kg")
    with pytest.raises(ValueError, match="mayor que cero"):
        _c("AGR-12", "0")
    with pytest.raises(ValueError, match="mayor que cero"):
        _c("AGR-12", "-0")
    with pytest.raises(ValueError, match="mayor que cero"):
        _c("AGR-12", "NaN")
    with pytest.raises(ValueError, match="código"):
        _c(" ", "0.94")
    with pytest.raises(ValueError, match="propio"):  # un propio sale del inventario, en t
        _c("AGR-12", "8", "l", "propio")


def test_receta_sin_componentes_fuente_o_codigos_repetidos(sesion) -> None:
    with pytest.raises(ValueError, match="componente"):
        _registrar(sesion, [])
    with pytest.raises(ValueError, match="repetido"):
        _registrar(sesion, [_c("AGR-12", "0.50"), _c("AGR-12", "0.49")])
    with pytest.raises(ValueError, match="fuente"):
        registrar_receta(
            sesion, "MZ-1", _mezcla(), fuente=" ", vigente_desde=OCTUBRE, usuario="ana", ahora=AHORA
        )
    with pytest.raises(ValueError, match="producto"):
        _registrar(sesion, _mezcla(), producto=" ")
    with pytest.raises(ValueError, match="usuario"):
        registrar_receta(
            sesion, "MZ-1", _mezcla(), fuente="f", vigente_desde=OCTUBRE, usuario=" ", ahora=AHORA
        )


def test_producir_100_t_de_mezcla_consume_94_t_de_agregado(sesion) -> None:
    _planta(sesion)
    _registrar(sesion, _mezcla())
    ids = producir_con_receta(
        sesion, "MZ-1", D("100"), date(2026, 10, 15), usuario="ana", ahora=AHORA
    )
    assert len(ids) == 2 and _movimientos(sesion) == 2  # nada para CA-30 ni GO (comprados)
    entrada, consumo = (sesion.get(Movimiento, i) for i in ids)
    assert (entrada.tipo, entrada.cantidad) == ("entrada", D("100"))
    assert (consumo.tipo, consumo.cantidad) == ("consumo", D("94"))
    assert (consumo.fecha, consumo.usuario, consumo.registrado) == (
        date(2026, 10, 15),
        "ana",
        AHORA,
    )
    por_codigo = {m.codigo: m.id for m in _materiales(sesion)}
    assert existencia(sesion, por_codigo["AGR-12"]) == D("-94")
    assert existencia(sesion, por_codigo["MZ-1"]) == D("100")


def _materiales(sesion: Session):
    from produccion.modelo import Material

    return list(sesion.scalars(select(Material)))


def test_un_propio_en_m3_se_consume_en_m3_con_su_densidad(sesion) -> None:
    crear_material(
        sesion,
        codigo="AGR-12",
        nombre="Agregado",
        unidad_venta="m3",
        existencia_minima=D(0),
        densidad_t_m3=D("1.6"),
    )
    crear_material(sesion, codigo="MZ-1", nombre="Mezcla", unidad_venta="t", existencia_minima=D(0))
    _registrar(sesion, [_c("AGR-12", "0.8"), _c("CA-30", "0.2", tipo="comprado")])
    ids = producir_con_receta(
        sesion, "MZ-1", D("100"), date(2026, 10, 15), usuario="ana", ahora=AHORA
    )
    assert sesion.get(Movimiento, ids[1]).cantidad == D("50")  # 80 t / 1,6 t/m3


def test_sin_receta_vigente_no_produce(sesion) -> None:
    _planta(sesion)
    with pytest.raises(ErrorDeReceta, match="MZ-1"):
        producir_con_receta(
            sesion, "MZ-1", D("100"), date(2026, 10, 15), usuario="ana", ahora=AHORA
        )
    _registrar(sesion, _mezcla(), vigente_desde=NOVIEMBRE)
    with pytest.raises(ErrorDeReceta, match="MZ-1"):  # la receta empieza despues de la fecha
        producir_con_receta(
            sesion, "MZ-1", D("100"), date(2026, 10, 15), usuario="ana", ahora=AHORA
        )
    assert _movimientos(sesion) == 0


def test_producir_valida_antes_de_escribir(sesion) -> None:
    _planta(sesion)
    _registrar(sesion, [_c("AGR-12", "0.94"), _c("AGR-99", "0.05")])  # AGR-99 no existe
    with pytest.raises(ErrorDeReceta, match="AGR-99"):
        producir_con_receta(
            sesion, "MZ-1", D("100"), date(2026, 10, 15), usuario="ana", ahora=AHORA
        )
    assert _movimientos(sesion) == 0
    with pytest.raises(ValueError, match="mayor que cero"):
        producir_con_receta(sesion, "MZ-1", D("0"), date(2026, 10, 15), usuario="ana", ahora=AHORA)
    with pytest.raises(ValueError, match="MZ-9"):  # el producto tampoco existe
        _registrar(sesion, _mezcla(), producto="MZ-9")
        producir_con_receta(sesion, "MZ-9", D("1"), date(2026, 10, 15), usuario="ana", ahora=AHORA)
    assert _movimientos(sesion) == 0


def test_receta_nueva_no_cambia_la_anterior(sesion) -> None:
    octubre = _registrar(sesion, _mezcla(), vigente_desde=OCTUBRE)
    noviembre = _registrar(
        sesion,
        [_c("AGR-12", "0.90"), _c("CA-30", "0.09", tipo="comprado")],
        vigente_desde=NOVIEMBRE,
    )
    assert octubre != noviembre
    de_octubre = receta_vigente(sesion, "MZ-1", date(2026, 10, 15))
    assert de_octubre is not None and de_octubre.id == octubre
    assert de_octubre.componentes == tuple(_mezcla())
    assert (de_octubre.fuente, de_octubre.vigente_desde) == ("dosificacion ficticia 1", OCTUBRE)
    de_noviembre = receta_vigente(sesion, "MZ-1", date(2026, 11, 15))
    assert de_noviembre is not None and de_noviembre.id == noviembre
    assert de_noviembre.componentes[0].cantidad_por_t == D("0.90")
    assert receta_vigente(sesion, "MZ-1", date(2026, 9, 30)) is None
    assert receta_vigente(sesion, "MZ-1", NOVIEMBRE).id == noviembre  # el dia de inicio ya rige
    assert receta_vigente(sesion, "OTRA", date(2026, 10, 15)) is None


def test_dos_recetas_con_la_misma_fecha_rige_la_registrada_despues(sesion) -> None:
    _registrar(sesion, _mezcla())
    corregida = _registrar(sesion, [_c("AGR-12", "0.95"), _c("CA-30", "0.05", tipo="comprado")])
    assert receta_vigente(sesion, "MZ-1", OCTUBRE).id == corregida


def test_producido_en_periodo_convierte_m3_con_densidad(sesion) -> None:
    crear_material(
        sesion,
        codigo="ARENA",
        nombre="Arena",
        unidad_venta="m3",
        existencia_minima=D(0),
        densidad_t_m3=D("1.6"),
    )
    crear_material(
        sesion, codigo="PIEDRA", nombre="Piedra", unidad_venta="t", existencia_minima=D(0)
    )
    ids = {m.codigo: m.id for m in _materiales(sesion)}
    registrar_entrada(sesion, ids["ARENA"], date(2026, 10, 3), D("100"), usuario="ana")
    registrar_entrada(sesion, ids["ARENA"], date(2026, 10, 20), D("10"), usuario="ana")
    registrar_entrada(sesion, ids["PIEDRA"], date(2026, 10, 31), D("50"), usuario="ana")
    registrar_entrada(sesion, ids["PIEDRA"], date(2026, 11, 1), D("999"), usuario="ana")
    registrar_entrada(sesion, ids["PIEDRA"], date(2026, 9, 30), D("999"), usuario="ana")
    assert producido_en_periodo(sesion, "2026-10") == {"ARENA": D("176"), "PIEDRA": D("50")}
    assert producido_en_periodo(sesion, "2026-12") == {}


def test_producido_ignora_despachos_y_consumos(sesion) -> None:
    _planta(sesion)
    _registrar(sesion, _mezcla())
    producir_con_receta(sesion, "MZ-1", D("100"), date(2026, 10, 15), usuario="ana", ahora=AHORA)
    assert producido_en_periodo(sesion, "2026-10") == {"MZ-1": D("100")}  # el consumo no suma


def test_material_en_m3_sin_densidad_nombra_su_codigo(sesion) -> None:
    crear_material(
        sesion, codigo="ARENA", nombre="Arena", unidad_venta="m3", existencia_minima=D(0)
    )
    material = _materiales(sesion)[0]
    registrar_entrada(sesion, material.id, date(2026, 10, 3), D("100"), usuario="ana")
    with pytest.raises(ValueError, match="ARENA"):
        producido_en_periodo(sesion, "2026-10")
    with pytest.raises(ValueError, match="periodo"):
        producido_en_periodo(sesion, "2026-13")


def test_consumo_en_m3_se_cuantiza_a_cuatro_decimales(sesion) -> None:
    """94 t / 1,7 t/m3 = 55,29411... -> 55,2941 (4 decimales, mitad al par)."""
    crear_material(
        sesion,
        codigo="AGR-12",
        nombre="Agregado",
        unidad_venta="m3",
        existencia_minima=D(0),
        densidad_t_m3=D("1.7"),
    )
    crear_material(sesion, codigo="MZ-1", nombre="Mezcla", unidad_venta="t", existencia_minima=D(0))
    _registrar(sesion, _mezcla())
    ids = producir_con_receta(
        sesion, "MZ-1", D("100"), date(2026, 10, 15), usuario="ana", ahora=AHORA
    )
    assert sesion.get(Movimiento, ids[1]).cantidad == D("55.2941")


def test_una_sola_regla_t_a_unidad_de_venta() -> None:
    from produccion.inventario import de_toneladas
    from produccion.modelo import Material

    m3 = Material(
        codigo="X",
        nombre="X",
        unidad_venta="m3",
        densidad_t_m3=D("1.7"),
        existencia_minima=D(0),
        activo=True,
    )
    assert de_toneladas(m3, D("94")) == D("55.2941")
    m2 = Material(
        codigo="Y",
        nombre="Y",
        unidad_venta="m3",
        densidad_t_m3=D("2"),
        existencia_minima=D(0),
        activo=True,
    )
    # mitad al par: 0,00005 va al 0,0000 par (HALF_UP daria 0,0001) y 0,00015 al 0,0002 par
    assert str(de_toneladas(m2, D("0.0001"))) == "0.0000"
    assert str(de_toneladas(m2, D("0.0003"))) == "0.0002"
    t = Material(codigo="T", nombre="T", unidad_venta="t", existencia_minima=D(0), activo=True)
    assert de_toneladas(t, D("94.12345")) == D("94.12345")
