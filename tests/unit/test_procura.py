"""La procura con fechas: explosión de materiales, compras y alertas (MP-7, Tarea 23; diseño de
montar un presupuesto §11, meta 3; foco de revisión 5).

Caso FICTICIO (nada es real): la vivienda de 80 m² de `tests/fixtures/procura_vivienda.py` (la de
`obra_vivienda` con dos APU cambiados para que la procura tenga sacos y un material compartido):

- OBRA-02 (concreto, 12 m³): 7 sacos de «Cemento gris» y 0,55 m³ de «Arena lavada» por m³.
- OBRA-04 (paredes, 210 m²): 12,5 piezas de «Bloque de arcilla de 15 cm» y 0,2 sacos de «Cemento
  gris» (mortero de pega) por m².
- Las demás conservan su material de la fixture (una unidad de material por unidad de partida).

Plan de la línea base: el de los rendimientos de la Tarea 21 (duraciones 4, 2, 4, 17,5, 23,5 y 7
días, encadenadas), en días hábiles (un día por período) desde el lunes 2026-11-02. Oráculos a mano:

Cantidades (Σ cantidad de la partida × cantidad del material):
- Agua 18 × 1 = 18 m³; Cemento gris 12 × 7 + 210 × 0,2 = 84 + 42 = 126 sacos; Arena lavada
  12 × 0,55 = 6,6 m³; Cabilla 950 × 1 = 950 kg; Bloque 210 × 12,5 = 2.625 piezas; Mortero 420 × 1;
  Pintura 420 × 1.

Primer día de cada partida (día hábil n desde el lunes 02/11: 1 = 02/11 … 5 = 06/11, 6 = 09/11):
- OBRA-01 día 1 = 02/11; OBRA-02 empieza tras 4 días: día 5 = vie 06/11; OBRA-03 tras 6: día 7 =
  mar 10/11; OBRA-04 tras 10: día 11 = lun 16/11; OBRA-05 tras 27,5: día 28 = mié 09/12 (semana 6
  son los días 26 a 30, del 07/12 al 11/12); OBRA-06 tras 51: día 52 = mar 12/01/2027 (semana 11 son
  los días 51 a 55, del 11/01 al 15/01).

Pedir a más tardar = se necesita − 3 días hábiles (contando hacia atrás, sin fines de semana):
- 02/11 (lun) → vie 30/10 (1), jue 29/10 (2), mié 28/10 (3) → 28/10/2026.
- 06/11 (vie) → jue 05 (1), mié 04 (2), mar 03 (3) → 03/11/2026.
- 10/11 (mar) → lun 09 (1), vie 06 (2), jue 05 (3) → 05/11/2026.
- 16/11 (lun) → vie 13, jue 12, mié 11 → 11/11/2026.
- 09/12 (mié) → mar 08, lun 07, vie 04 → 04/12/2026.
- 12/01/2027 (mar) → lun 11, vie 08, jue 07 → 07/01/2027.

Con el feriado del miércoles 04/11: los días hábiles son 02 (1), 03 (2), 05 (3), 06 (4) y lun 09
(5) → el cemento se necesita el 09/11; hacia atrás vie 06 (1), jue 05 (2), [04 feriado], mar 03 (3)
→ se pide a más tardar el 03/11.

Alerta anticipada: sin pedir y el corte desde `pedir − 2 días hábiles` hasta el día anterior a
`pedir`: para el 03/11 (mar) → lun 02 (1), vie 30/10 (2) → aviso del 30/10 al 02/11; desde el 03/11,
error.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from aplicacion import mesa
from aplicacion.cifras import CifraInvalida
from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from aplicacion.mercado import CarpetaSinMoneda, NoExiste
from aplicacion.mesa import GrupoPendientes, Pendiente, Siguiente
from aplicacion.procura import (
    AVISO,
    ERROR,
    MENSAJE_SIN_LINEA_BASE,
    AlertaDeCompra,
    NecesidadDeInsumo,
    ReglaDeProcura,
    alertas_de_compra,
    causa_sugerida,
    explosion,
    fijar_plazo,
    pendientes_de_compras,
    procura,
    registrar_compra,
)
from aplicacion.tablas_mercado import ObservacionDeMercado
from aplicacion.tablas_procura import CompraDeInsumo, crear_esquema_procura
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import procura_vivienda as pv

D = Decimal
OBRA = pv.OBRA
VERSION = pv.VERSION
LUNES = pv.LUNES
VER_LA_PROCURA = Siguiente("Ver la procura", "control")
CEMENTO = ("Cemento gris", "saco")
AGUA = ("Agua", "m3")
ARENA = ("Arena lavada", "m3")


def _necesidad(
    descripcion: str,
    unidad: str,
    cantidad: str,
    partidas: tuple[str, ...],
    se_necesita: date | None,
    pedir: date | None,
    *,
    plazo: int = 3,
    pedida: date | None = None,
    recibida: date | None = None,
) -> NecesidadDeInsumo:
    return NecesidadDeInsumo(
        descripcion=descripcion,
        unidad=unidad,
        cantidad=D(cantidad),
        partidas=partidas,
        se_necesita=se_necesita,
        pedir_a_mas_tardar=pedir,
        plazo=plazo,
        pedida=pedida,
        recibida=recibida,
    )


#: La explosión de la vivienda sin feriados ni compras (oráculos del encabezado).
ESPERADA = [
    _necesidad("Agua", "m3", "18", ("OBRA-01",), LUNES, date(2026, 10, 28)),
    _necesidad(
        "Cemento gris", "saco", "126", ("OBRA-02", "OBRA-04"), date(2026, 11, 6), date(2026, 11, 3)
    ),
    _necesidad("Arena lavada", "m3", "6.6", ("OBRA-02",), date(2026, 11, 6), date(2026, 11, 3)),
    _necesidad(
        "Cabilla de 1/2 pulgada", "kg", "950", ("OBRA-03",), date(2026, 11, 10), date(2026, 11, 5)
    ),
    _necesidad(
        "Bloque de arcilla de 15 cm",
        "pieza",
        "2625",
        ("OBRA-04",),
        date(2026, 11, 16),
        date(2026, 11, 11),
    ),
    _necesidad(
        "Mortero premezclado", "m2", "420", ("OBRA-05",), date(2026, 12, 9), date(2026, 12, 4)
    ),
    _necesidad("Pintura de caucho", "m2", "420", ("OBRA-06",), date(2027, 1, 12), date(2027, 1, 7)),
]


# --- con base ------------------------------------------------------------------------------------


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator:
    ruta = tmp_path / "carpeta.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema_procura(motor)  # sin efecto cuando la migración ya la creó
    try:
        with abrir_sesion(motor) as abierta:
            yield abierta
            abierta.rollback()
    finally:
        motor.dispose()


def _vivienda(sesion, *, nombre: str = OBRA, lista: models.ListaPrecios | None = None):
    return pv.sembrar(sesion, nombre=nombre, lista=lista)


def _linea_base(sesion, feriados: tuple[date, ...] = (), *, nombre: str = OBRA) -> None:
    pv.declarar_linea_base(sesion, feriados, nombre=nombre)


def _comprar(sesion, insumo: tuple[str, str], evento: str, dia: date, **extra) -> None:
    registrar_compra(
        sesion,
        OBRA,
        descripcion=insumo[0],
        unidad=insumo[1],
        evento=evento,
        fecha=dia,
        responsable="Ana <ana>",
        ahora=datetime(dia.year, dia.month, dia.day, 17),
        **extra,
    )
    sesion.commit()


def _por_insumo(necesidades: list[NecesidadDeInsumo]) -> dict[tuple[str, str], NecesidadDeInsumo]:
    return {(n.descripcion, n.unidad): n for n in necesidades}


def test_el_plan_de_entrada_es_el_de_la_tarea_21() -> None:
    """La entrada (no el oráculo): OBRA-02 empieza en el día 5 y OBRA-06 en el 52."""
    primero = {}
    for etiqueta, reparto in pv.plan():
        for codigo, fraccion in reparto:
            if fraccion > 0:
                primero.setdefault(codigo, etiqueta)
    assert primero["OBRA-02"] == "Dia 5"
    assert primero["OBRA-05"] == "Dia 28"
    assert primero["OBRA-06"] == "Dia 52"


def test_la_explosion_de_la_vivienda_con_la_linea_base(sesion) -> None:
    _vivienda(sesion)
    _linea_base(sesion)
    assert explosion(sesion, OBRA, VERSION) == ESPERADA


def test_equipos_y_mano_de_obra_no_aparecen(sesion) -> None:
    _vivienda(sesion)
    nombres = {n.descripcion for n in explosion(sesion, OBRA, VERSION)}
    assert not nombres & {"Mezcladora de concreto", "Andamio", "Pala y pico", "Obrero"}


def test_sin_linea_base_no_hay_fechas_y_la_procura_lo_dice(sesion) -> None:
    _vivienda(sesion)
    sin_fechas = explosion(sesion, OBRA, VERSION)
    assert [(n.descripcion, n.cantidad) for n in sin_fechas] == [
        (n.descripcion, n.cantidad) for n in ESPERADA
    ]
    assert {(n.se_necesita, n.pedir_a_mas_tardar) for n in sin_fechas} == {(None, None)}
    leida = procura(sesion, OBRA)
    assert (leida.version, leida.aviso) == (VERSION, MENSAJE_SIN_LINEA_BASE)
    assert MENSAJE_SIN_LINEA_BASE == "Declare la línea base para calcular las fechas de compra."
    assert alertas_de_compra(leida.necesidades, LUNES, leida.feriados) == []


def test_un_feriado_declarado_corre_las_fechas(sesion) -> None:
    _vivienda(sesion)
    _linea_base(sesion, feriados=(date(2026, 11, 4),))
    cemento = _por_insumo(explosion(sesion, OBRA, VERSION))[CEMENTO]
    assert (cemento.se_necesita, cemento.pedir_a_mas_tardar) == (
        date(2026, 11, 9),
        date(2026, 11, 3),
    )


def test_foco_5_al_corte_del_02_11_avisa_el_cemento_y_al_03_11_es_error(sesion) -> None:
    _vivienda(sesion)
    _linea_base(sesion)
    leida = procura(sesion, OBRA)
    assert (leida.version, leida.aviso) == (VERSION, None)
    # El agua debía pedirse el 28/10: al 02/11 ya es error. Cemento y arena, aviso.
    assert alertas_de_compra(leida.necesidades, LUNES, leida.feriados) == [
        AlertaDeCompra(ERROR, "Agua no está pedido y debía pedirse el 28/10/2026."),
        AlertaDeCompra(AVISO, "Pida Cemento gris antes del 03/11/2026."),
        AlertaDeCompra(AVISO, "Pida Arena lavada antes del 03/11/2026."),
    ]
    al_03 = alertas_de_compra(leida.necesidades, date(2026, 11, 3), leida.feriados)
    assert (
        AlertaDeCompra(ERROR, "Cemento gris no está pedido y debía pedirse el 03/11/2026.") in al_03
    )
    assert (AVISO, ERROR) == ("AVISO", "ERROR")


def test_pedida_a_tiempo_no_alerta_y_recibida_tarde_es_compra_tardia(sesion) -> None:
    _vivienda(sesion)
    _linea_base(sesion)
    _comprar(sesion, CEMENTO, "pedida", LUNES)
    cemento = _por_insumo(explosion(sesion, OBRA, VERSION))[CEMENTO]
    assert (cemento.pedida, cemento.recibida) == (LUNES, None)
    leida = procura(sesion, OBRA)
    textos = [a.texto for a in alertas_de_compra(leida.necesidades, date(2026, 11, 3), ())]
    assert not [t for t in textos if "Cemento gris" in t]

    _comprar(sesion, CEMENTO, "recibida", date(2026, 11, 9), cantidad="126", precio="20,00")
    leida = procura(sesion, OBRA)
    assert _por_insumo(leida.necesidades)[CEMENTO].recibida == date(2026, 11, 9)
    tardia = AlertaDeCompra(
        ERROR, "Compra tardía: Cemento gris llegó el 09/11/2026 y se necesitaba el 06/11/2026."
    )
    assert tardia in alertas_de_compra(leida.necesidades, date(2026, 11, 9), ())
    # Al corte del 06/11 la recepción aún no ha ocurrido: ni tardía ni «no está pedido».
    al_06 = alertas_de_compra(leida.necesidades, date(2026, 11, 6), ())
    assert not [a for a in al_06 if "Cemento gris" in a.texto]


def test_la_causa_sugerida_de_la_partida_es_compra_tardia(sesion) -> None:
    _vivienda(sesion)
    _linea_base(sesion)
    assert causa_sugerida(sesion, OBRA, "OBRA-02", date(2026, 11, 13)) is None
    _comprar(sesion, CEMENTO, "recibida", date(2026, 11, 9))
    assert causa_sugerida(sesion, OBRA, "OBRA-02", date(2026, 11, 13)) == "compra_tardia"
    # Antes de la recepción no hay de qué culparla; OBRA-01 no usa cemento.
    assert causa_sugerida(sesion, OBRA, "OBRA-02", date(2026, 11, 8)) is None
    assert causa_sugerida(sesion, OBRA, "OBRA-01", date(2026, 11, 13)) is None
    # OBRA-04 empieza el 16/11: el cemento del 09/11 le llegó a tiempo.
    assert causa_sugerida(sesion, OBRA, "OBRA-04", date(2026, 11, 20)) is None


def test_sin_linea_base_no_hay_causa_sugerida(sesion) -> None:
    _vivienda(sesion)
    _comprar(sesion, CEMENTO, "recibida", date(2026, 11, 9))
    assert causa_sugerida(sesion, OBRA, "OBRA-02", date(2026, 11, 13)) is None


def test_la_recepcion_con_precio_crea_una_observacion_de_compra(sesion) -> None:
    _vivienda(sesion)
    declarar_moneda_de_la_carpeta(
        sesion, "Bs", responsable="Ana <ana>", ahora=datetime(2026, 10, 26, 9)
    )
    sesion.commit()
    _comprar(sesion, CEMENTO, "recibida", date(2026, 11, 9), cantidad="126", precio="20,00")
    (observacion,) = sesion.scalars(select(ObservacionDeMercado)).all()
    codigo = sesion.scalars(
        select(models.Insumo.codigo).where(models.Insumo.descripcion == "Cemento gris")
    ).first()
    assert (
        observacion.lado,
        observacion.codigo,
        observacion.fuente_tipo,
        observacion.fecha,
        observacion.precio,
        observacion.moneda,
        observacion.responsable,
    ) == ("compra", codigo, "compra", date(2026, 11, 9), D("20.00"), "Bs", "Ana <ana>")
    assert observacion.fuente == f"Compra recibida en la obra {OBRA}"
    (compra,) = sesion.scalars(select(CompraDeInsumo)).all()
    assert (compra.evento, compra.cantidad, compra.precio, compra.moneda) == (
        "recibida",
        D("126"),
        D("20.00"),
        "Bs",
    )


def test_una_recepcion_sin_precio_o_un_pedido_no_crean_observacion(sesion) -> None:
    _vivienda(sesion)
    declarar_moneda_de_la_carpeta(
        sesion, "Bs", responsable="Ana <ana>", ahora=datetime(2026, 10, 26, 9)
    )
    sesion.commit()
    _comprar(sesion, CEMENTO, "pedida", LUNES, precio="19,00")
    _comprar(sesion, CEMENTO, "recibida", date(2026, 11, 5), cantidad="126")
    assert sesion.scalars(select(ObservacionDeMercado)).all() == []
    assert len(sesion.scalars(select(CompraDeInsumo)).all()) == 2


def test_con_varias_compras_vale_la_primera_de_cada_evento(sesion) -> None:
    _vivienda(sesion)
    _linea_base(sesion)
    _comprar(sesion, CEMENTO, "pedida", date(2026, 10, 30))
    _comprar(sesion, CEMENTO, "pedida", date(2026, 10, 28))
    _comprar(sesion, CEMENTO, "recibida", date(2026, 11, 9))
    _comprar(sesion, CEMENTO, "recibida", date(2026, 11, 5))
    cemento = _por_insumo(explosion(sesion, OBRA, VERSION))[CEMENTO]
    assert (cemento.pedida, cemento.recibida) == (date(2026, 10, 28), date(2026, 11, 5))


def test_las_compras_de_otra_obra_no_cuentan(sesion) -> None:
    _, lista = _vivienda(sesion)
    _vivienda(sesion, nombre="Otra vivienda demo", lista=lista)
    _linea_base(sesion)
    registrar_compra(
        sesion, "Otra vivienda demo", descripcion="Cemento gris", unidad="saco",
        evento="pedida", fecha=LUNES, responsable="Ana <ana>", ahora=datetime(2026, 11, 2, 9),
    )  # fmt: skip
    sesion.commit()
    assert _por_insumo(explosion(sesion, OBRA, VERSION))[CEMENTO].pedida is None


def test_el_plazo_de_entrega_se_cambia_por_insumo(sesion) -> None:
    _vivienda(sesion)
    _linea_base(sesion)
    fijar_plazo(sesion, OBRA, descripcion="Cemento gris", unidad="saco", dias="5")
    sesion.commit()
    por_insumo = _por_insumo(explosion(sesion, OBRA, VERSION))
    # 06/11 − 5 días hábiles: jue 05, mié 04, mar 03, lun 02, vie 30/10 → 30/10.
    assert (por_insumo[CEMENTO].plazo, por_insumo[CEMENTO].pedir_a_mas_tardar) == (
        5,
        date(2026, 10, 30),
    )
    assert (por_insumo[ARENA].plazo, por_insumo[ARENA].pedir_a_mas_tardar) == (
        3,
        date(2026, 11, 3),
    )
    fijar_plazo(sesion, OBRA, descripcion="Cemento gris", unidad="saco", dias="0")
    sesion.commit()
    cemento = _por_insumo(explosion(sesion, OBRA, VERSION))[CEMENTO]
    assert (cemento.plazo, cemento.pedir_a_mas_tardar) == (0, date(2026, 11, 6))


@pytest.mark.parametrize("dias", ["-1", "366", "2,5", "tres"])
def test_un_plazo_fuera_de_0_a_365_dias_enteros_se_rechaza(sesion, dias: str) -> None:
    _vivienda(sesion)
    with pytest.raises(ReglaDeProcura) as error:
        fijar_plazo(sesion, OBRA, descripcion="Cemento gris", unidad="saco", dias=dias)
    assert str(error.value) == (
        "El plazo de entrega es un número entero de días hábiles, de 0 a 365."
    )


def test_registrar_compra_valida_lo_escrito(sesion) -> None:
    _vivienda(sesion)
    ahora = datetime(2026, 11, 2, 9)

    def comprar(**cambios):
        datos = dict(
            descripcion="Cemento gris", unidad="saco", evento="pedida", fecha=LUNES,
            responsable="Ana <ana>", ahora=ahora,
        )  # fmt: skip
        datos.update(cambios)
        registrar_compra(sesion, OBRA, **datos)

    with pytest.raises(ReglaDeProcura, match=r"^La fecha de la compra no puede ser posterior"):
        comprar(fecha=date(2026, 11, 3))
    with pytest.raises(ReglaDeProcura, match=r"^La cantidad debe ser mayor que cero\.$"):
        comprar(cantidad="0")
    with pytest.raises(ReglaDeProcura, match=r"^El precio debe ser mayor que cero\.$"):
        comprar(precio="0,00")
    with pytest.raises(CifraInvalida):
        comprar(precio="2.5")
    with pytest.raises(NoExiste, match="Mezcladora de concreto"):
        comprar(descripcion="Mezcladora de concreto", unidad="")
    with pytest.raises(NoExiste, match="no existe"):
        registrar_compra(
            sesion, "Obra que no existe", descripcion="Cemento gris", unidad="saco",
            evento="pedida", fecha=LUNES, responsable="Ana <ana>", ahora=ahora,
        )  # fmt: skip
    with pytest.raises(ValueError, match="evento"):
        comprar(evento="perdida")
    assert sesion.scalars(select(CompraDeInsumo)).all() == []


def test_un_precio_sin_moneda_en_la_carpeta_no_se_registra(sesion) -> None:
    """Sin moneda declarada y sin lista vigente al día no hay en qué contar el precio."""
    _vivienda(sesion)
    with pytest.raises(CarpetaSinMoneda):
        registrar_compra(
            sesion, OBRA, descripcion="Cemento gris", unidad="saco", evento="recibida",
            fecha=date(2026, 10, 20), precio="20,00", responsable="Ana <ana>",
            ahora=datetime(2026, 10, 20, 9),
        )  # fmt: skip


# --- alertas (puras): fronteras -------------------------------------------------------------------

CEMENTO_06 = _necesidad(
    "Cemento gris", "saco", "126", ("OBRA-02",), date(2026, 11, 6), date(2026, 11, 3)
)


@pytest.mark.parametrize(
    ("corte", "esperadas"),
    [
        (date(2026, 10, 29), []),  # antes de vie 30/10 (pedir − 2 días hábiles)
        (date(2026, 10, 30), [AlertaDeCompra(AVISO, "Pida Cemento gris antes del 03/11/2026.")]),
        (date(2026, 10, 31), [AlertaDeCompra(AVISO, "Pida Cemento gris antes del 03/11/2026.")]),
        (LUNES, [AlertaDeCompra(AVISO, "Pida Cemento gris antes del 03/11/2026.")]),
        (
            date(2026, 11, 3),
            [AlertaDeCompra(ERROR, "Cemento gris no está pedido y debía pedirse el 03/11/2026.")],
        ),
        (
            date(2026, 11, 20),
            [AlertaDeCompra(ERROR, "Cemento gris no está pedido y debía pedirse el 03/11/2026.")],
        ),
    ],
)
def test_las_fronteras_de_la_alerta_sin_pedir(corte: date, esperadas: list) -> None:
    assert alertas_de_compra([CEMENTO_06], corte, ()) == esperadas


def test_el_feriado_cuenta_al_retroceder_la_alerta() -> None:
    """Pedir el mar 03/11 con feriado el lun 02/11: −1 = vie 30/10, −2 = jue 29/10."""
    feriados = (date(2026, 11, 2),)
    assert alertas_de_compra([CEMENTO_06], date(2026, 10, 28), feriados) == []
    assert alertas_de_compra([CEMENTO_06], date(2026, 10, 29), feriados) == [
        AlertaDeCompra(AVISO, "Pida Cemento gris antes del 03/11/2026.")
    ]


@pytest.mark.parametrize(
    ("recibida", "tardia"),
    [(date(2026, 11, 5), False), (date(2026, 11, 6), False), (date(2026, 11, 9), True)],
)
def test_la_frontera_de_la_compra_tardia(recibida: date, tardia: bool) -> None:
    necesidad = _necesidad(
        "Cemento gris", "saco", "126", ("OBRA-02",), date(2026, 11, 6), date(2026, 11, 3),
        recibida=recibida,
    )  # fmt: skip
    esperadas = (
        [AlertaDeCompra(ERROR, f"Compra tardía: Cemento gris llegó el {recibida:%d/%m/%Y} y se "
                               "necesitaba el 06/11/2026.")]
        if tardia
        else []
    )  # fmt: skip
    assert alertas_de_compra([necesidad], date(2026, 11, 20), ()) == esperadas


def test_recibida_sin_pedido_registrado_no_dice_que_falta_pedirla() -> None:
    necesidad = _necesidad(
        "Cemento gris", "saco", "126", ("OBRA-02",), date(2026, 11, 6), date(2026, 11, 3),
        recibida=date(2026, 11, 2),
    )  # fmt: skip
    assert alertas_de_compra([necesidad], date(2026, 11, 4), ()) == []


def test_sin_fechas_no_hay_alertas() -> None:
    necesidad = _necesidad("Cemento gris", "saco", "126", ("OBRA-02",), None, None)
    assert alertas_de_compra([necesidad], date(2026, 11, 20), ()) == []


# --- la fuente «compras» de la mesa ---------------------------------------------------------------


def test_pendientes_de_compras_al_corte_del_02_11(sesion, monkeypatch: pytest.MonkeyPatch) -> None:
    obra, _ = _vivienda(sesion)
    _linea_base(sesion)
    _comprar(sesion, AGUA, "pedida", date(2026, 10, 28))
    _comprar(sesion, ARENA, "pedida", date(2026, 10, 28))
    esperado = Pendiente(
        str(obra.id), OBRA, "Pida Cemento gris antes del 03/11/2026.", VER_LA_PROCURA
    )
    assert pendientes_de_compras(sesion, LUNES) == [esperado]

    # Con la fuente registrada (la línea de `FUENTES` la suma el orquestador), sale en «Compras».
    monkeypatch.setitem(mesa.FUENTES, "compras", (pendientes_de_compras,))
    grupos = {grupo.clave: grupo for grupo in mesa.pendientes(sesion, LUNES)}
    assert grupos["compras"] == GrupoPendientes("compras", "Compras", (esperado,))


def test_una_obra_sin_linea_base_no_da_pendientes_de_compras(sesion) -> None:
    _vivienda(sesion)
    assert pendientes_de_compras(sesion, LUNES) == []
