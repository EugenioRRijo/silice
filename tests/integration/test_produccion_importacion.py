"""Importacion idempotente de pesajes de bascula y bandeja de sospechosos (Tarea 4.7).

EJEMPLO CONSTRUIDO. Los valores esperados estan escritos a mano a partir de
`tests/fixtures/bascula/ORACULO.md` (no se derivan del codigo que se prueba). Catalogo de la prueba:
`ARENA` en m3 con densidad 1,60 t/m3 (del fixture) y `PIEDRA34` en t. El lector da 3 leidos y 3
dudosos; la importacion manda ademas TCK-006 (`GRAVA9`, que no esta en el catalogo) a la bandeja:
2 despachos y 4 sospechosos.

Cubre los puntos 2 (reimportar no duplica) y 4 (material desconocido o sin densidad, nunca un
despacho en 0) del Review Focus del plan.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from produccion import importacion
from produccion.conectores.bascula import LecturaBascula, PesajeLeido, leer
from produccion.importacion import (
    ResultadoImportacion,
    descartar,
    importar,
    pendientes,
    resolver,
)
from produccion.inventario import (
    ErrorDeInventario,
    crear_material,
    existencia,
    registrar_despacho,
    registrar_entrada,
)
from produccion.modelo import METADATA_PRODUCCION, Material, Movimiento, PesajeSospechoso
from tests.fixtures.bascula import construir

D = Decimal
HOY = date(2026, 10, 18)  # fecha de referencia del oraculo (la manda el cliente, no el reloj)
USUARIO = "prueba"
AHORA = datetime(2026, 10, 18, 9, 30, 0)
NETO_DISTINTO = "neto distinto de bruto − tara"  # U+2212, como en el lector y el oraculo


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    METADATA_PRODUCCION.create_all(motor)
    with Session(motor) as s:
        yield s
    motor.dispose()


def _catalogo(sesion: Session) -> None:
    """ARENA (m3, 1,60 t/m3) y PIEDRA34 (t): ejemplo construido."""
    crear_material(
        sesion,
        codigo="ARENA",
        nombre="Arena lavada",
        unidad_venta="m3",
        densidad_t_m3=D("1.60"),
        existencia_minima=D("20"),
    )
    crear_material(
        sesion,
        codigo="PIEDRA34",
        nombre="Piedra picada 3/4",
        unidad_venta="t",
        existencia_minima=D("10"),
    )
    sesion.commit()


def _basico() -> LecturaBascula:
    return leer(construir.csv_basico(), "basico.csv", fecha_referencia=HOY)


def _movimientos(sesion: Session) -> list[Movimiento]:
    return list(sesion.scalars(select(Movimiento).order_by(Movimiento.id)))


def _por_ticket(sesion: Session, ticket: str) -> Movimiento:
    return sesion.scalars(select(Movimiento).where(Movimiento.ticket == ticket)).one()


def _sospechoso(sesion: Session, ticket: str) -> PesajeSospechoso:
    return sesion.scalars(select(PesajeSospechoso).where(PesajeSospechoso.ticket == ticket)).one()


def _id_material(sesion: Session, codigo: str) -> int:
    return sesion.scalars(select(Material).where(Material.codigo == codigo)).one().id


def _id_de(sesion: Session, ticket: str) -> int:
    return _sospechoso(sesion, ticket).id


def _cuantos(sesion: Session, modelo: type[Any]) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo)) or 0


def test_importar_el_basico_registra_dos_y_manda_cuatro_a_la_bandeja(sesion: Session) -> None:
    _catalogo(sesion)
    lectura = _basico()
    assert (len(lectura.pesajes), len(lectura.dudosos)) == (3, 3)  # el lector, antes de importar

    resultado = importar(sesion, lectura, usuario=USUARIO)

    assert resultado == ResultadoImportacion(
        registrados=2, ya_registrados=0, a_la_bandeja=4, huella=lectura.huella
    )
    assert len(resultado.huella) == 64
    movimientos = _movimientos(sesion)
    assert len(movimientos) == 2
    arena = _por_ticket(sesion, "TCK-001")
    assert arena.cantidad == D("17.6875")  # 28,300 t / 1,60 t/m3
    assert (arena.tipo, arena.origen, arena.usuario) == ("despacho", "bascula", USUARIO)
    assert arena.fecha == date(2026, 10, 15)
    assert (arena.placa, arena.cliente) == ("EJ-001", "Cliente Ejemplo A")
    piedra = _por_ticket(sesion, "TCK-002")
    assert piedra.cantidad == D("24.5")  # material en t: tal cual
    assert (piedra.tipo, piedra.origen) == ("despacho", "bascula")

    cola = pendientes(sesion)
    assert [p.ticket for p in cola] == ["TCK-003", "TCK-004", "TCK-005", "TCK-006"]
    assert [p.motivo for p in cola] == [
        "tara mayor o igual que el bruto",
        NETO_DISTINTO,
        "fecha futura",
        "material desconocido",
    ]
    assert [p.fila for p in cola] == [4, 5, 6, 7]
    assert {p.estado for p in cola} == {"pendiente"}
    assert {p.huella_archivo for p in cola} == {lectura.huella}
    # textos legibles: ISO para la fecha, Decimal en texto para los pesos del pesaje leido
    grava = cola[3]
    assert (grava.fecha_texto, grava.material_texto, grava.placa) == (
        "2026-10-17",
        "GRAVA9",
        "EJ-006",
    )
    assert (grava.bruto_texto, grava.tara_texto, grava.neto_texto) == ("40", "15", "25")
    # un dudoso del lector conserva el texto crudo del archivo
    futuro = cola[2]
    assert (futuro.fecha_texto, futuro.bruto_texto, futuro.neto_texto) == (
        "2026-12-31",
        "40000",
        "25000",
    )


def test_reimportar_no_duplica(sesion: Session) -> None:
    _catalogo(sesion)
    lectura = _basico()
    importar(sesion, lectura, usuario=USUARIO)

    segunda = importar(sesion, lectura, usuario=USUARIO)

    assert segunda == ResultadoImportacion(
        registrados=0, ya_registrados=2, a_la_bandeja=0, huella=lectura.huella
    )
    assert _cuantos(sesion, Movimiento) == 2
    assert len(pendientes(sesion)) == 4


def test_otro_reporte_con_tickets_ya_vistos_no_duplica_despachos(sesion: Session) -> None:
    """Review Focus 2: un reporte distinto que repite TCK-001 no crea un segundo despacho."""
    _catalogo(sesion)
    importar(sesion, _basico(), usuario=USUARIO)
    cabecera = "Ticket;Fecha;Placa;Cliente;Material;Bruto (kg);Tara (kg);Neto (kg)"
    otro = (
        f"{cabecera}\n"
        "TCK-001;2026-10-15;EJ-001;Cliente Ejemplo A;ARENA;42500;14200;28300\n"
        "TCK-007;2026-10-17;EJ-007;Cliente Ejemplo A;PIEDRA34;40000;15000;25000\n"
    ).encode()
    lectura = leer(otro, "otro.csv", fecha_referencia=HOY)

    resultado = importar(sesion, lectura, usuario=USUARIO)

    assert (resultado.registrados, resultado.ya_registrados, resultado.a_la_bandeja) == (1, 1, 0)
    assert _cuantos(sesion, Movimiento) == 3
    assert _por_ticket(sesion, "TCK-001").cantidad == D("17.6875")
    assert _por_ticket(sesion, "TCK-007").cantidad == D("25")


def test_material_sin_densidad_va_a_la_bandeja(sesion: Session) -> None:
    """Review Focus 4: ARENA en m3 sin densidad no genera un despacho en 0."""
    crear_material(
        sesion, codigo="ARENA", nombre="Arena lavada", unidad_venta="m3", existencia_minima=D("20")
    )
    crear_material(
        sesion, codigo="PIEDRA34", nombre="Piedra", unidad_venta="t", existencia_minima=D("10")
    )
    sesion.commit()
    lectura = _basico()

    resultado = importar(sesion, lectura, usuario=USUARIO)

    assert (resultado.registrados, resultado.ya_registrados, resultado.a_la_bandeja) == (1, 0, 5)
    assert [m.ticket for m in _movimientos(sesion)] == ["TCK-002"]
    sin_densidad = _sospechoso(sesion, "TCK-001")
    assert sin_densidad.motivo == "material sin densidad"
    assert sin_densidad.estado == "pendiente"
    assert sin_densidad.material_texto == "ARENA"
    assert (sin_densidad.bruto_texto, sin_densidad.neto_texto) == ("42.5", "28.3")
    assert _sospechoso(sesion, "TCK-006").motivo == "material desconocido"


def test_el_material_se_busca_por_nombre_sin_tildes_ni_mayusculas(sesion: Session) -> None:
    crear_material(
        sesion,
        codigo="AR-01",
        nombre="  Árena ",  # normaliza a «arena»
        unidad_venta="m3",
        densidad_t_m3=D("1.60"),
        existencia_minima=D("20"),
    )
    crear_material(
        sesion,
        codigo="P-34",
        nombre="Piédra34",  # normaliza a «piedra34»
        unidad_venta="t",
        existencia_minima=D("10"),
    )
    sesion.commit()

    resultado = importar(sesion, _basico(), usuario=USUARIO)

    assert (resultado.registrados, resultado.a_la_bandeja) == (2, 4)
    assert _por_ticket(sesion, "TCK-001").cantidad == D("17.6875")
    assert _por_ticket(sesion, "TCK-002").cantidad == D("24.5")


def test_un_peso_que_redondea_a_cero_va_a_la_bandeja(sesion: Session) -> None:
    """Review Focus 4: nunca un despacho en 0."""
    _catalogo(sesion)
    diminuto = PesajeLeido(
        fila=2,
        ticket="TCK-900",
        fecha=date(2026, 10, 15),
        placa="EJ-900",
        cliente="",
        material="ARENA",
        bruto_t=D("0.0001"),
        tara_t=D("0"),
        neto_t=D("0.00001"),  # / 1,60 = 0,00000625 -> 0,0000 con 4 decimales
    )
    lectura = LecturaBascula(huella="a" * 64, pesajes=(diminuto,), dudosos=())

    resultado = importar(sesion, lectura, usuario=USUARIO)

    assert (resultado.registrados, resultado.a_la_bandeja) == (0, 1)
    assert _cuantos(sesion, Movimiento) == 0
    assert _sospechoso(sesion, "TCK-900").motivo == "peso neto en cero"


def test_resolver_crea_el_despacho_y_cierra_el_sospechoso(sesion: Session) -> None:
    _catalogo(sesion)
    importar(sesion, _basico(), usuario=USUARIO)
    id_tara = _id_de(sesion, "TCK-003")
    id_grava = _id_de(sesion, "TCK-006")

    # corregido a mano: 28,3 t de ARENA (m3) -> 17,6875 m3
    movimiento = resolver(
        sesion,
        id_tara,
        material_codigo="ARENA",
        fecha=date(2026, 10, 16),
        neto_t=D("28.3"),
        ticket="TCK-003",
        usuario="ana",
        ahora=AHORA,
    )

    assert movimiento.tipo == "despacho"
    assert movimiento.origen == "bascula"
    assert movimiento.ticket == "TCK-003"
    assert movimiento.cantidad == D("17.6875")
    assert movimiento.fecha == date(2026, 10, 16)
    assert movimiento.usuario == "ana"
    assert movimiento.placa == "EJ-003"
    cerrado = sesion.get(PesajeSospechoso, id_tara)
    assert cerrado is not None
    assert cerrado.estado == "resuelto"
    assert cerrado.resuelto_por == "ana"
    assert cerrado.resuelto_en == AHORA
    assert [p.ticket for p in pendientes(sesion)] == ["TCK-004", "TCK-005", "TCK-006"]
    assert _cuantos(sesion, Movimiento) == 3

    # la grava se corrige a PIEDRA34 (t): cantidad tal cual; la existencia puede quedar negativa
    # y el despacho se registra igual (RT-S4-2)
    en_t = resolver(
        sesion,
        id_grava,
        material_codigo="PIEDRA34",
        fecha=date(2026, 10, 17),
        neto_t=D("25"),
        ticket="TCK-006",
        usuario="ana",
        ahora=AHORA,
    )
    assert en_t.cantidad == D("25")
    # sin entradas: 0 - 24,5 - 25
    assert existencia(sesion, _id_material(sesion, "PIEDRA34")) == D("-49.5")


def test_resolver_con_datos_invalidos_deja_el_sospechoso_pendiente(sesion: Session) -> None:
    _catalogo(sesion)
    crear_material(
        sesion,
        codigo="CASCAJO",
        nombre="Cascajo",
        unidad_venta="m3",
        existencia_minima=D("0"),
    )
    sesion.commit()
    importar(sesion, _basico(), usuario=USUARIO)
    id_sospechoso = _id_de(sesion, "TCK-003")
    base = {"fecha": date(2026, 10, 16), "usuario": "ana", "ahora": AHORA}

    casos: list[tuple[dict[str, Any], str]] = [
        (
            {"material_codigo": "NOEXISTE", "neto_t": D("1"), "ticket": "TCK-003"},
            "No existe un material",
        ),
        (
            {"material_codigo": "CASCAJO", "neto_t": D("1"), "ticket": "TCK-003"},
            "no tiene densidad",
        ),
        ({"material_codigo": "ARENA", "neto_t": D("0"), "ticket": "TCK-003"}, "mayor que cero"),
        ({"material_codigo": "ARENA", "neto_t": D("-3"), "ticket": "TCK-003"}, "mayor que cero"),
        ({"material_codigo": "ARENA", "neto_t": D("1"), "ticket": "  "}, "Indique el ticket"),
        (
            {"material_codigo": "ARENA", "neto_t": D("1"), "ticket": "TCK-001"},
            "El ticket TCK-001 ya está registrado.",
        ),
    ]
    for datos, mensaje in casos:
        with pytest.raises(ErrorDeInventario, match=mensaje):
            resolver(sesion, id_sospechoso, **base, **datos)

    assert _cuantos(sesion, Movimiento) == 2
    sigue = sesion.get(PesajeSospechoso, id_sospechoso)
    assert sigue is not None
    assert (sigue.estado, sigue.resuelto_por, sigue.resuelto_en) == ("pendiente", None, None)
    with pytest.raises(ErrorDeInventario, match="No existe ese pesaje"):
        resolver(
            sesion,
            99999,
            material_codigo="ARENA",
            fecha=date(2026, 10, 16),
            neto_t=D("1"),
            ticket="TCK-X",
            usuario="ana",
            ahora=AHORA,
        )


def test_descartar_no_crea_despacho(sesion: Session) -> None:
    _catalogo(sesion)
    importar(sesion, _basico(), usuario=USUARIO)
    id_neto = _id_de(sesion, "TCK-004")

    resultado = descartar(sesion, id_neto, usuario="ana", ahora=AHORA)

    assert resultado is None
    cerrado = sesion.get(PesajeSospechoso, id_neto)
    assert cerrado is not None
    assert cerrado.estado == "descartado"
    assert cerrado.resuelto_por == "ana"
    assert cerrado.resuelto_en == AHORA
    assert _cuantos(sesion, Movimiento) == 2
    assert [p.ticket for p in pendientes(sesion)] == ["TCK-003", "TCK-005", "TCK-006"]
    with pytest.raises(ErrorDeInventario, match="No existe ese pesaje"):
        descartar(sesion, 99999, usuario="ana", ahora=AHORA)


def test_resolver_dos_veces_se_rechaza(sesion: Session) -> None:
    _catalogo(sesion)
    importar(sesion, _basico(), usuario=USUARIO)
    id_tara = _id_de(sesion, "TCK-003")
    id_neto = _id_de(sesion, "TCK-004")
    datos: dict[str, Any] = {
        "material_codigo": "ARENA",
        "fecha": date(2026, 10, 16),
        "neto_t": D("28.3"),
        "usuario": "ana",
        "ahora": AHORA,
    }
    resolver(sesion, id_tara, ticket="TCK-003", **datos)

    with pytest.raises(ErrorDeInventario, match="ya fue resuelto o descartado"):
        resolver(sesion, id_tara, ticket="TCK-003B", **datos)
    with pytest.raises(ErrorDeInventario, match="ya fue resuelto o descartado"):
        descartar(sesion, id_tara, usuario="ana", ahora=AHORA)
    descartar(sesion, id_neto, usuario="ana", ahora=AHORA)
    with pytest.raises(ErrorDeInventario, match="ya fue resuelto o descartado"):
        descartar(sesion, id_neto, usuario="ana", ahora=AHORA)
    with pytest.raises(ErrorDeInventario, match="ya fue resuelto o descartado"):
        resolver(sesion, id_neto, ticket="TCK-004B", **datos)

    assert _cuantos(sesion, Movimiento) == 3  # los 2 importados + el resuelto
    assert _por_ticket(sesion, "TCK-003").cantidad == D("17.6875")


def test_un_fallo_deja_todo_como_estaba(sesion: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Un ticket que choca a mitad de la importacion deshace los despachos y la bandeja."""
    _catalogo(sesion)
    llamadas: list[str | None] = []

    def despacho_que_choca(sesion_: Session, *args: Any, **kwargs: Any) -> Movimiento:
        llamadas.append(kwargs.get("ticket"))
        if len(llamadas) == 2:  # el segundo ticket ya existe "por otra via": el servicio lo rechaza
            sesion_.add(
                Movimiento(
                    material_id=args[0],
                    fecha=args[1],
                    tipo="despacho",
                    cantidad=D("1"),
                    ticket=kwargs["ticket"],
                    usuario="otro",
                    registrado=AHORA,
                )
            )
            sesion_.flush()
        return registrar_despacho(sesion_, *args, **kwargs)

    monkeypatch.setattr(importacion, "registrar_despacho", despacho_que_choca)
    lectura = _basico()

    with pytest.raises(ErrorDeInventario, match="ya está registrado"):
        importar(sesion, lectura, usuario=USUARIO)

    assert llamadas == ["TCK-001", "TCK-002"]  # el primero llego a registrarse antes del choque
    assert _cuantos(sesion, Movimiento) == 0
    assert _cuantos(sesion, PesajeSospechoso) == 0
    assert pendientes(sesion) == []

    monkeypatch.undo()  # la sesion sigue sirviendo: la misma lectura entra completa
    resultado = importar(sesion, lectura, usuario=USUARIO)
    assert (resultado.registrados, resultado.ya_registrados, resultado.a_la_bandeja) == (2, 0, 4)


def test_existencia_final_con_la_serie_a_mano(sesion: Session) -> None:
    _catalogo(sesion)
    arena = _id_material(sesion, "ARENA")
    registrar_entrada(sesion, arena, date(2026, 10, 1), D("100"), usuario=USUARIO)

    importar(sesion, _basico(), usuario=USUARIO)

    assert existencia(sesion, arena) == D("82.3125")  # 100 - 28,3 / 1,60 = 100 - 17,6875


def _acumulado() -> LecturaBascula:
    """Reporte del dia siguiente: los 6 tickets de ayer mas TCK-007 (tara mayor que el bruto)."""
    nueva = "TCK-007;2026-10-17;EJ-007;Cliente Ejemplo C;ARENA;40000;45000;-5000\n"
    return leer(construir.csv_basico() + nueva.encode(), "acumulado.csv", fecha_referencia=HOY)


def test_un_reporte_acumulado_no_duplica_sospechosos(sesion: Session) -> None:
    _catalogo(sesion)
    primera = importar(sesion, _basico(), usuario=USUARIO)
    lectura = _acumulado()
    assert lectura.huella != primera.huella  # otro archivo: la clave (huella, fila) no basta

    resultado = importar(sesion, lectura, usuario=USUARIO)

    assert (resultado.registrados, resultado.ya_registrados, resultado.a_la_bandeja) == (0, 2, 1)
    assert _cuantos(sesion, Movimiento) == 2
    assert [p.ticket for p in pendientes(sesion)] == [
        "TCK-003",
        "TCK-004",
        "TCK-005",
        "TCK-006",
        "TCK-007",
    ]
    nuevo = _sospechoso(sesion, "TCK-007")
    assert (nuevo.motivo, nuevo.fila, nuevo.huella_archivo) == (
        "tara mayor o igual que el bruto",
        8,
        lectura.huella,
    )
    assert _cuantos(sesion, PesajeSospechoso) == 5


def test_un_sospechoso_descartado_no_resucita(sesion: Session) -> None:
    _catalogo(sesion)
    importar(sesion, _basico(), usuario=USUARIO)
    descartar(sesion, _id_de(sesion, "TCK-004"), usuario="ana", ahora=AHORA)
    resuelto = resolver(
        sesion,
        _id_de(sesion, "TCK-003"),
        material_codigo="ARENA",
        fecha=date(2026, 10, 16),
        neto_t=D("28.3"),
        ticket="TCK-003",
        usuario="ana",
        ahora=AHORA,
    )

    resultado = importar(sesion, _acumulado(), usuario=USUARIO)

    assert (resultado.registrados, resultado.ya_registrados, resultado.a_la_bandeja) == (0, 2, 1)
    assert resuelto.ticket == "TCK-003"  # el resuelto sigue como despacho y no se toca
    assert _cuantos(sesion, Movimiento) == 3
    estados = {
        p.ticket: p.estado
        for p in sesion.scalars(select(PesajeSospechoso))
        if p.ticket != "TCK-007"
    }
    assert estados == {
        "TCK-003": "resuelto",
        "TCK-004": "descartado",
        "TCK-005": "pendiente",
        "TCK-006": "pendiente",
    }
    assert _cuantos(sesion, PesajeSospechoso) == 5
    assert [p.ticket for p in pendientes(sesion)] == ["TCK-005", "TCK-006", "TCK-007"]


def test_sin_ticket_la_clave_sigue_siendo_huella_y_fila(sesion: Session) -> None:
    _catalogo(sesion)
    sin_ticket = (
        b"Ticket;Fecha;Placa;Cliente;Material;Bruto (kg);Tara (kg);Neto (kg)\n"
        b";2026-10-15;EJ-1;Cliente Ejemplo A;ARENA;40000;15000;25000\n"
    )
    lectura = leer(sin_ticket, "sin_ticket.csv", fecha_referencia=HOY)
    otra = leer(sin_ticket + b"\n", "sin_ticket_2.csv", fecha_referencia=HOY)

    assert importar(sesion, lectura, usuario=USUARIO).a_la_bandeja == 1
    assert importar(sesion, lectura, usuario=USUARIO).a_la_bandeja == 0  # mismo archivo
    assert importar(sesion, otra, usuario=USUARIO).a_la_bandeja == 1  # otro archivo: sin ticket
    assert _cuantos(sesion, PesajeSospechoso) == 2
