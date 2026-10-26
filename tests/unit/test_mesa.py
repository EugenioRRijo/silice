"""La mesa de control de «Presupuestos y obras» (MOD-4a; diseño de módulos §6 y §12.6).

`aplicacion/mesa.py` calcula, sin tocar el núcleo, las cifras de arriba (valor ganado y avance
contra el plan, en la moneda de la carpeta), la tabla de obras (etapa, avance, qué pasa y el
siguiente paso) y los pendientes agrupados (Aprobar, Precios y Calidad).

Oráculos escritos a mano, con la cuenta al lado; ninguno sale del código bajo prueba:

- las cifras puras con las obras ficticias A, B y C del plan (A y B en Bs, C en USD);
- la obra OB-S2 con la memoria `tests/fixtures/memorias/control_ob_s2.md` (§3 y §4: EV 1 200,00,
  PV 1 500,00, BAC 4 000,00, SPI 0,8000, término día 23 contra 20 del plan: 3 días hábiles);
- los pendientes con la carpeta ficticia «Casa Demo» (versión CD-001 sobre la lista «Base»).

`hoy` es el domingo 2026-10-25. Las bases viven en `tmp_path` (`preparar_base`): nada en `data/`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import delete, select

from aplicacion import aprobaciones, control, mesa
from aplicacion.aprobaciones import aprobadas_sin_entregar, pendientes_de_aprobacion
from aplicacion.hoja_partidas import pendientes_sin_calculo
from aplicacion.mercado import pendientes_de_mercado
from aplicacion.mesa import (
    Cifra,
    Conversion,
    GrupoPendientes,
    ObraEnMesa,
    Pendiente,
    Siguiente,
    TasaDelBcv,
    cifras_de_la_mesa,
    dias_habiles_entre,
    hallazgos_graves,
    lista_vieja,
    obras_de_la_mesa,
    pendientes,
    precios_sin_referencia,
    precios_viejos,
)
from aplicacion.obras import FichaObra, guardar_ficha
from aplicacion.procura import pendientes_de_compras
from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto
from core.budget.control import guardar_parametros
from core.budget.valor_ganado import ParametrosControl
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.verificacion import Severidad
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import obra_atrasada
from tests.fixtures.canonico_minimo import FECHA, RELLENO, guardar_otra

D = Decimal
HOY = date(2026, 10, 25)
CORTE_A = date(2026, 10, 23)
REGISTRAR = Siguiente("Registrar el avance", "control")
ALERTAS = Siguiente("Ver las alertas", "control")
HOJA = Siguiente("Abrir la Hoja", "hoja")
ACTUALIZAR = Siguiente("Actualizar precios", "actualizacion")
CATALOGO = Siguiente("Ver el catálogo", "catalogo")
VER_EL_ENVIO = Siguiente("Ver el envío", "aprobar")
DECLARAR = Siguiente("Declarar la línea base", "control")


def _obra(
    nombre: str,
    moneda: str,
    ev: str | None,
    pv: str | None,
    *,
    etapa: str = "en_ejecucion",
    corte: date = CORTE_A,
    retraso: int | None = None,
) -> ObraEnMesa:
    """Una obra de la mesa escrita a mano (sin base)."""
    return ObraEnMesa(
        codigo=f"cod-{nombre}",
        nombre=nombre,
        cliente="",
        moneda=moneda,
        etapa=etapa,
        version=f"{nombre}-001",
        total=None,
        corte=corte,
        ev=None if ev is None else D(ev),
        pv=None if pv is None else D(pv),
        bac=None,
        spi=None if ev is None or pv is None or D(pv) == 0 else D(ev) / D(pv),
        retraso_dias=retraso,
        que_pasa=None,
        siguiente=None,
    )


#: A (Bs, EV 40 000, PV 50 000, SPI 0,80 < 0,90: atrasada 3 días) y B (Bs, EV 30 000, PV 25 000).
A = _obra("A", "Bs", "40000.00", "50000.00", etapa="atrasada", retraso=3)
B = _obra("B", "Bs", "30000.00", "25000.00")
#: C (USD, EV 100, PV 100, corte 2026-10-23).
C = _obra("C", "USD", "100.00", "100.00")


#: La tasa del BCV más reciente al 2026-10-23 es la del jueves 2026-10-22 (40,00 Bs/USD).
FECHA_TASA = date(2026, 10, 22)


def _sin_tasa(_fecha: date) -> TasaDelBcv | None:
    return None


def _tasa_40(fecha: date) -> TasaDelBcv | None:
    return TasaDelBcv(D("40.00"), FECHA_TASA) if fecha == CORTE_A else None


# --- cifras de la mesa (puras) --------------------------------------------------------------------


def test_valor_ganado_y_avance_de_dos_obras_en_la_moneda_de_la_carpeta() -> None:
    cifras = cifras_de_la_mesa([A, B], "Bs", _sin_tasa)
    # ΣEV = 40 000 + 30 000 = 70 000; ΣPV = 50 000 + 25 000 = 75 000; SV = −5 000;
    # −5 000 / 75 000 × 100 = −6,666… → −6,7 (ROUND_HALF_UP a 0,1)
    assert cifras.valor_ganado == Cifra(
        clave="valor_ganado",
        titulo="Valor ganado",
        actual=D("70000.00"),
        meta=D("75000.00"),
        delta=D("-5000.00"),
        delta_pct=D("-6.7"),
        sentido="rendimiento",
        detalle=None,
    )
    assert str(cifras.valor_ganado.actual) == "70000.00"
    assert str(cifras.valor_ganado.delta_pct) == "-6.7"
    # SPI agregado = 70 000 / 75 000 = 0,93333… → 0,9333; desviación 0,9333 − 1 = −0,0667
    assert cifras.avance == Cifra(
        clave="avance",
        titulo="Avance contra el plan",
        actual=D("0.9333"),
        meta=D("1.0000"),
        delta=D("-0.0667"),
        delta_pct=None,
        sentido="rendimiento",
        detalle="1 obra atrasada; la más atrasada, A: 3 días hábiles",
    )
    assert str(cifras.avance.actual) == "0.9333"
    assert str(cifras.avance.meta) == "1.0000"
    assert cifras.conversiones == ()
    assert cifras.fuera_de_suma == ()


def test_una_obra_en_otra_moneda_se_convierte_con_la_tasa_de_su_corte_y_se_declara() -> None:
    cifras = cifras_de_la_mesa([A, B, C], "Bs", _tasa_40)
    # C: 100 USD × 40,00 = 4 000 Bs de EV y de PV.
    # ΣEV = 70 000 + 4 000 = 74 000; ΣPV = 75 000 + 4 000 = 79 000; SV = −5 000;
    # −5 000 / 79 000 × 100 = −6,329… → −6,3; SPI 74 000 / 79 000 = 0,93670… → 0,9367
    assert cifras.valor_ganado is not None and cifras.avance is not None
    assert (cifras.valor_ganado.actual, cifras.valor_ganado.meta) == (D("74000.00"), D("79000.00"))
    assert cifras.valor_ganado.delta == D("-5000.00")
    assert cifras.valor_ganado.delta_pct == D("-6.3")
    assert str(cifras.avance.actual) == "0.9367"
    assert cifras.avance.delta == D("-0.0633")
    assert cifras.conversiones == (Conversion("C", "USD", D("40.00"), CORTE_A, FECHA_TASA),)
    assert cifras.fuera_de_suma == ()


def test_sin_tasa_del_bcv_la_obra_va_aparte_y_no_se_suma() -> None:
    cifras = cifras_de_la_mesa([A, B, C], "Bs", _sin_tasa)
    assert cifras.valor_ganado is not None and cifras.avance is not None
    # los mismos números de A + B (la primera prueba)
    assert (cifras.valor_ganado.actual, cifras.valor_ganado.meta) == (D("70000.00"), D("75000.00"))
    assert cifras.avance.actual == D("0.9333")
    assert cifras.conversiones == ()
    assert cifras.fuera_de_suma == ("C",)


def test_solo_una_obra_sin_tasa_no_da_ninguna_cifra() -> None:
    cifras = cifras_de_la_mesa([C], "Bs", _sin_tasa)
    assert (cifras.valor_ganado, cifras.avance) == (None, None)
    assert cifras.fuera_de_suma == ("C",)


def test_carpeta_en_usd_convierte_una_obra_en_bs_dividiendo_por_la_tasa() -> None:
    # D: 4 000 Bs de EV y 8 000 Bs de PV con 40,00 Bs/USD → 100 USD y 200 USD; más C (100 / 100):
    # ΣEV 200, ΣPV 300, SV −100, −100 / 300 × 100 = −33,33… → −33,3; SPI 0,6667
    obra_d = _obra("D", "Bs", "4000.00", "8000.00")
    cifras = cifras_de_la_mesa([C, obra_d], "USD", _tasa_40)
    assert cifras.valor_ganado is not None and cifras.avance is not None
    assert (cifras.valor_ganado.actual, cifras.valor_ganado.meta) == (D("200.00"), D("300.00"))
    assert cifras.valor_ganado.delta_pct == D("-33.3")
    assert cifras.avance.actual == D("0.6667")
    assert cifras.conversiones == (Conversion("D", "Bs", D("40.00"), CORTE_A, FECHA_TASA),)


def test_ev_y_pv_en_cero_dan_valor_ganado_en_cero_y_sin_avance() -> None:
    cifras = cifras_de_la_mesa([_obra("E", "Bs", "0", "0")], "Bs", _sin_tasa)
    assert cifras.valor_ganado is not None
    assert (cifras.valor_ganado.actual, cifras.valor_ganado.meta, cifras.valor_ganado.delta) == (
        D("0.00"),
        D("0.00"),
        D("0.00"),
    )
    assert str(cifras.valor_ganado.actual) == "0.00"
    assert cifras.valor_ganado.delta_pct is None
    assert cifras.avance is None


def test_sin_obras_en_ejecucion_no_hay_cifras() -> None:
    en_elaboracion = _obra("F", "Bs", None, None, etapa="en_elaboracion")
    assert cifras_de_la_mesa([en_elaboracion], "Bs", _sin_tasa) == mesa.CifrasMesa(
        None, None, (), ()
    )
    assert cifras_de_la_mesa([], "Bs", _sin_tasa) == mesa.CifrasMesa(None, None, (), ())


def test_una_obra_en_ejecucion_sin_ev_ni_pv_no_se_suma_ni_va_aparte() -> None:
    # ControlInvalido: la obra sigue en la tabla, pero no tiene cifras que sumar
    sin_control = _obra("G", "Bs", None, None)
    cifras = cifras_de_la_mesa([A, sin_control], "Bs", _sin_tasa)
    assert cifras.valor_ganado is not None
    assert cifras.valor_ganado.actual == D("40000.00")
    assert cifras.fuera_de_suma == ()


def test_sin_moneda_de_carpeta_se_suma_en_la_de_las_obras_si_comparten_una() -> None:
    cifras = cifras_de_la_mesa([A, B], None, _sin_tasa)
    assert cifras.valor_ganado is not None
    assert cifras.valor_ganado.actual == D("70000.00")
    assert mesa.moneda_de_la_suma([A, B], None) == "Bs"


def test_sin_moneda_de_carpeta_y_obras_en_dos_monedas_todas_van_aparte() -> None:
    cifras = cifras_de_la_mesa([A, B, C], None, _tasa_40)
    assert (cifras.valor_ganado, cifras.avance) == (None, None)
    assert cifras.fuera_de_suma == ("A", "B", "C")
    assert mesa.moneda_de_la_suma([A, B, C], None) is None


def test_el_detalle_del_avance_cuenta_las_atrasadas_y_nombra_la_peor() -> None:
    # A atrasada 3 días y H atrasada 5: dos obras; la peor es H con 5
    obra_h = _obra("H", "Bs", "10.00", "20.00", etapa="atrasada", retraso=5)
    cifras = cifras_de_la_mesa([A, B, obra_h], "Bs", _sin_tasa)
    assert cifras.avance is not None
    assert cifras.avance.detalle == "2 obras atrasadas; la más atrasada, H: 5 días hábiles"


def test_el_detalle_dice_un_dia_habil_en_singular_y_sin_dias_no_nombra_la_peor() -> None:
    uno = _obra("I", "Bs", "10.00", "20.00", etapa="atrasada", retraso=1)
    cifras = cifras_de_la_mesa([uno], "Bs", _sin_tasa)
    assert cifras.avance is not None
    assert cifras.avance.detalle == "1 obra atrasada; la más atrasada, I: 1 día hábil"
    sin_dias = _obra("J", "Bs", "10.00", "20.00", etapa="atrasada", retraso=None)
    cifras = cifras_de_la_mesa([sin_dias], "Bs", _sin_tasa)
    assert cifras.avance is not None
    assert cifras.avance.detalle == "1 obra atrasada"


def test_sin_obras_atrasadas_el_avance_no_lleva_detalle() -> None:
    cifras = cifras_de_la_mesa([B], "Bs", _sin_tasa)
    assert cifras.avance is not None
    assert cifras.avance.detalle is None


# --- días hábiles ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("desde", "hasta", "dias"),
    [
        # martes 20: miércoles 21, jueves 22 y viernes 23
        (date(2026, 10, 20), date(2026, 10, 23), 3),
        # el sábado 24 no cuenta
        (date(2026, 10, 20), date(2026, 10, 24), 3),
        # el domingo 25 tampoco; el lunes 26 sí
        (date(2026, 10, 20), date(2026, 10, 26), 4),
        (date(2026, 10, 23), date(2026, 10, 23), 0),
        # hacia atrás no hay días
        (date(2026, 10, 23), date(2026, 10, 20), 0),
    ],
)
def test_dias_habiles_entre(desde: date, hasta: date, dias: int) -> None:
    assert dias_habiles_entre(desde, hasta) == dias


# --- obras de la mesa (con base) ------------------------------------------------------------------


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


def _total_a_mano(sesion, codigo: str) -> Decimal:
    """Σ `partida_presupuestada.total` de la versión `codigo`, con su propia consulta."""
    version = sesion.scalars(
        select(models.Presupuesto).where(models.Presupuesto.codigo == codigo)
    ).one()
    totales = sesion.scalars(
        select(models.PartidaPresupuestada.total).where(
            models.PartidaPresupuestada.presupuesto_id == version.id
        )
    )
    return sum(totales, D(0))


def _por_nombre(obras: list[ObraEnMesa]) -> dict[str, ObraEnMesa]:
    return {obra.nombre: obra for obra in obras}


def test_ob_s2_con_v01_y_v02_esta_atrasada_con_sus_cifras_de_la_memoria(sesion) -> None:
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion)
    ob.registrar_v01_y_v02(sesion)
    proyecto = sesion.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == ob.NOMBRE)
    ).one()
    guardar_ficha(sesion, proyecto.id, FichaObra("Contratista Demo, C.A.", "Maracay"))
    crear_proyecto(sesion, "Casa Demo")  # sin versión ni línea base
    sesion.flush()

    obras = obras_de_la_mesa(sesion, Catalogo(sesion), HOY)

    assert [obra.nombre for obra in obras] == ["Casa Demo", "OB-S2"]
    ob_s2 = _por_nombre(obras)["OB-S2"]
    assert ob_s2.codigo == str(proyecto.id)
    assert ob_s2.cliente == "Contratista Demo, C.A."
    assert ob_s2.moneda == "USD"
    assert ob_s2.etapa == "atrasada"
    assert ob_s2.version == "OB-001"
    assert ob_s2.corte == date(2026, 11, 13)  # el «hasta» de V-02
    # memoria §3: EV = 90 × 10 + 60 × 5 = 1 200; PV = 1 000 + 1 000 × 0,5 = 1 500; BAC 4 000
    assert ob_s2.ev == D("1200.00")
    assert ob_s2.pv == D("1500.00")
    assert ob_s2.bac == D("4000.00")
    assert ob_s2.spi == D("0.8000")
    # memoria §4: término día 23 contra 20 del plan
    assert ob_s2.retraso_dias == 3
    # T22: qué pasa nombra la primera partida atrasada en el orden del presupuesto. Memoria §4: OB-A
    # termina en el día 11,11 y su plan en la semana 2 (2 × 5 = día 10): ⌈1,11⌉ = 2 días, sin causa.
    assert ob_s2.que_pasa == "OB-A atrasada 2 días: sin causa declarada"
    assert ob_s2.siguiente == ALERTAS
    # memoria §1: V = 4 000 × 1,265 = 5 060,00
    assert ob_s2.total == _total_a_mano(sesion, "OB-001")
    assert ob_s2.total == D("5060.00")


def test_una_obra_sin_linea_base_esta_en_elaboracion(sesion) -> None:
    ob.sembrar(sesion)
    crear_proyecto(sesion, "Casa Demo")
    sesion.flush()

    obras = _por_nombre(obras_de_la_mesa(sesion, Catalogo(sesion), HOY))

    casa = obras["Casa Demo"]
    assert (casa.etapa, casa.version, casa.total, casa.cliente) == (
        "en_elaboracion",
        None,
        None,
        "",
    )
    assert (casa.ev, casa.pv, casa.spi, casa.que_pasa) == (None, None, None, None)
    assert casa.siguiente == HOJA
    # OB-S2 con su versión guardada y sin línea base: el total es el de la versión vigente
    ob_s2 = obras["OB-S2"]
    assert (ob_s2.etapa, ob_s2.version) == ("en_elaboracion", "OB-001")
    assert ob_s2.total == _total_a_mano(sesion, "OB-001")
    assert ob_s2.siguiente == HOJA


def test_con_linea_base_y_sin_valuaciones_esta_en_ejecucion_sin_avance(sesion) -> None:
    # línea base vigente desde el 2026-10-01: al 2026-10-25 el plan (que empieza el 2026-11-02)
    # aún no pide nada, PV = 0 y no hay SPI
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion, desde=date(2026, 10, 1))
    sesion.flush()

    (obra,) = obras_de_la_mesa(sesion, Catalogo(sesion), HOY)

    assert obra.etapa == "en_ejecucion"
    assert obra.corte == HOY
    assert (obra.ev, obra.pv, obra.spi) == (D("0"), D("0"), None)
    assert obra.que_pasa == "Sin avance registrado"
    assert obra.siguiente == REGISTRAR


def test_con_linea_base_futura_y_sin_valuaciones_tambien_dice_sin_avance(sesion) -> None:
    # la línea base desde el 2026-11-02 aún no rige al 2026-10-25: no hay nada que controlar
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion)
    sesion.flush()

    (obra,) = obras_de_la_mesa(sesion, Catalogo(sesion), HOY)

    assert obra.etapa == "en_ejecucion"
    assert (obra.ev, obra.pv, obra.que_pasa) == (None, None, "Sin avance registrado")
    assert obra.siguiente == REGISTRAR


def test_un_control_que_no_se_puede_calcular_lo_dice_con_un_texto_fijo(sesion) -> None:
    # línea base desde el 2026-11-20 y valuaciones hasta el 2026-11-13: al corte no hay línea base
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion, desde=date(2026, 11, 20))
    ob.registrar_v01_y_v02(sesion)
    sesion.flush()

    (obra,) = obras_de_la_mesa(sesion, Catalogo(sesion), HOY)

    assert obra.etapa == "en_ejecucion"
    assert (obra.ev, obra.pv, obra.spi) == (None, None, None)
    # el mensaje del núcleo («no hay linea base … al 2026-11-13») no llega a la interfaz
    assert obra.que_pasa == "No se pudo calcular el avance; ábralo en Control para ver el motivo."
    assert not re.search(r"\d{4}-\d{2}-\d{2}", obra.que_pasa)
    assert obra.siguiente == REGISTRAR


def test_con_el_plan_empezado_y_sin_valuaciones_esta_atrasada_y_se_suma(sesion) -> None:
    # Comportamiento vigente hasta que Eugenio decida: al viernes 2026-11-13 (sin valuaciones, el
    # corte es hoy) el plan pide PV 1 500,00 (memoria §3) y no hay nada ejecutado: EV 0, SPI 0.
    # Sin avance no hay ritmo con que reproyectar: no hay días de retraso.
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion)
    sesion.flush()
    hoy = date(2026, 11, 13)

    (obra,) = obras_de_la_mesa(sesion, Catalogo(sesion), hoy)

    assert obra.etapa == "atrasada"
    assert obra.corte == hoy
    assert (obra.ev, obra.pv, obra.spi) == (D("0"), D("1500.00"), D("0"))
    assert obra.retraso_dias is None
    assert obra.que_pasa == "Atrasada (SPI 0,00)"
    assert obra.siguiente == ALERTAS
    cifras = cifras_de_la_mesa([obra], "USD", _sin_tasa)
    assert cifras.valor_ganado is not None and cifras.avance is not None
    # entra en la suma: 0,00 contra 1 500,00; SV −1 500,00 (−100,0 %); avance 0,0000
    assert (cifras.valor_ganado.actual, cifras.valor_ganado.meta) == (D("0.00"), D("1500.00"))
    assert cifras.valor_ganado.delta_pct == D("-100.0")
    assert cifras.avance.actual == D("0.0000")
    assert cifras.avance.detalle == "1 obra atrasada"


def test_una_obra_atrasada_dice_la_partida_atrasada_y_su_causa(sesion) -> None:
    # T22, la obra de dos partidas: A en 5 de 10 al viernes 2026-11-06 (día hábil 5) por una compra
    # tardía. SPI = 300 / 600 = 0,5 < 0,90: atrasada. A termina en el día 10 contra el 5 de su plan
    # (5 días) y B en el 9 contra el 7 (2 días): la primera en el orden del presupuesto es A.
    obra_atrasada.sembrar_dos_partidas(sesion)
    sesion.commit()
    control.registrar_y_controlar(
        sesion,
        obra_atrasada.NOMBRE,
        Catalogo(sesion),
        numero="V-01",
        desde="2026-11-02",
        hasta="2026-11-06",
        fecha="2026-11-06",
        inspector="Ing. Ficticio",
        filas=[{"Partida": "A", "Cantidad": "5", "Causa": "compra_tardia"}],
        fuente=obra_atrasada.FUENTE,
        responsable=obra_atrasada.RESPONSABLE,
    )

    (obra,) = obras_de_la_mesa(sesion, Catalogo(sesion), HOY)

    assert obra.etapa == "atrasada"
    assert obra.spi == D("0.5")
    assert obra.que_pasa == "A atrasada 5 días: Compra tardía"
    assert obra.siguiente == ALERTAS


@pytest.mark.parametrize(
    ("umbral", "etapa"),
    [
        # SPI 0,8000 (memoria §3) no es menor que 0,8000: en ejecución
        ("0.8000", "en_ejecucion"),
        # 0,8000 < 0,8001: atrasada
        ("0.8001", "atrasada"),
    ],
)
def test_la_frontera_del_umbral_de_spi(sesion, umbral: str, etapa: str) -> None:
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion)
    ob.registrar_v01_y_v02(sesion)
    guardar_parametros(
        sesion,
        ob.NOMBRE,
        ParametrosControl(spi_error=D(umbral)),
        fuente="umbral ficticio de la prueba",
        responsable=ob.RESPONSABLE,
    )
    sesion.flush()

    (obra,) = obras_de_la_mesa(sesion, Catalogo(sesion), HOY)

    assert obra.etapa == etapa


# --- etapas de aprobación (MP-4, T18) ------------------------------------------------------------


def _vivienda_guardada(sesion) -> str:
    """«Vivienda Demo 80 m2» (ficticia) con VIV-001 guardada y sellada a nombre de «Ana <ana>»;
    confirma (el sello se escribe al confirmar) y devuelve el código de la obra."""
    lista = models.ListaPrecios(
        nombre="Lista de prueba", moneda="USD", fecha_vigencia=FECHA, origen="prueba"
    )
    sesion.add(lista)
    sesion.flush()
    Catalogo(sesion).cargar_composicion(RELLENO, lista, Dominio.CIVIL, FECHA, "prueba")
    obra = crear_proyecto(sesion, "Vivienda Demo 80 m2", dominio=Dominio.CIVIL)
    guardar_otra(sesion, obra, lista, "VIV-001", usuario="Ana <ana>")
    sesion.commit()
    return str(obra.id)


def test_una_obra_pasa_por_en_aprobacion_y_aprobada_sin_linea_base(sesion) -> None:
    codigo = _vivienda_guardada(sesion)

    (obra,) = obras_de_la_mesa(sesion, Catalogo(sesion), HOY)
    assert (obra.etapa, obra.siguiente) == ("en_elaboracion", HOJA)

    envio = aprobaciones.enviar(
        sesion, codigo, "VIV-001", nota="", usuario="Ana <ana>", ahora=datetime(2026, 10, 20, 10)
    )
    (obra,) = obras_de_la_mesa(sesion, Catalogo(sesion), HOY)
    assert (obra.etapa, obra.version) == ("en_aprobacion", "VIV-001")
    assert obra.siguiente == VER_EL_ENVIO
    assert obra.siguiente.pagina == "aprobar"
    assert (obra.ev, obra.pv, obra.que_pasa) == (None, None, None)

    aprobaciones.dictaminar(
        sesion,
        envio.id,
        resultado="aprobada",
        notas="",
        usuario="Rita <rita>",
        ahora=datetime(2026, 10, 21, 9),
    )
    (obra,) = obras_de_la_mesa(sesion, Catalogo(sesion), HOY)
    assert (obra.etapa, obra.version) == ("aprobada", "VIV-001")
    assert obra.siguiente == DECLARAR
    assert obra.siguiente.pagina == "control"
    assert mesa.ETAPA_TEXTO["en_aprobacion"] == "En aprobación"
    assert mesa.ETAPA_TEXTO["aprobada"] == "Aprobada"


# --- pendientes (con base) ------------------------------------------------------------------------

PARAMETROS = ParametrosCosto(D("6.00"), D("1.00"), D("0.15"), D("0.10"))
#: Un muro ficticio con tres insumos: bloque (material), mezcladora (equipo) y cuadrilla.
MURO = ComposicionAPU(
    "CD-01",
    "Muro de bloque ficticio",
    "m2",
    D(10),
    materiales=(LineaMaterial("Bloque ficticio", "pza", D(12), D("2.00")),),
    equipos=(LineaEquipo("Mezcladora ficticia", D(1), D(100), D("0.10")),),
    mano_obra=(LineaManoObra("Cuadrilla ficticia", D(2), D("3.00")),),
)


def _casa_demo(sesion, fecha_base: date) -> models.Presupuesto:
    """«Casa Demo» con la versión CD-001 sobre la lista «Base» (Bs, del `fecha_base`) y la lista
    para armar «Nueva» del 2026-10-01. No confirma."""
    base = models.ListaPrecios(nombre="Base", moneda="Bs", fecha_vigencia=fecha_base)
    sesion.add(base)
    sesion.flush()
    Catalogo(sesion).cargar_composicion(MURO, base, Dominio.CIVIL, fecha_base, "prueba de la mesa")
    item = ItemComputo(
        "CD-01", "Muro de bloque ficticio", "m2", D(50), "prueba:CD-01", OrigenTipo.MANUAL,
        Dominio.CIVIL,
    )  # fmt: skip
    resultado = elaborar([item], {"CD-01": MURO}, PARAMETROS, codigo="CD-001", fecha=fecha_base,
                         moneda="Bs")  # fmt: skip
    version = guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=crear_proyecto(sesion, "Casa Demo"),
        lista=base,
        parametros=PARAMETROS,
    )
    sesion.add(models.ListaPrecios(nombre="Nueva", moneda="Bs", fecha_vigencia=date(2026, 10, 1)))
    sesion.flush()
    return version


def _precio(sesion, lista_id: int, descripcion: str) -> models.PrecioInsumo:
    return sesion.scalars(
        select(models.PrecioInsumo)
        .join(models.Insumo)
        .where(models.PrecioInsumo.lista_id == lista_id, models.Insumo.descripcion == descripcion)
    ).one()


def _referencias(sesion, version: models.Presupuesto) -> None:
    """El bloque tiene su referencia (MaPreX ficticio), la mezcladora su origen (cotización
    ficticia) y la cuadrilla nada."""
    bloque = _precio(sesion, version.lista_precios_id, "Bloque ficticio")
    mezcladora = _precio(sesion, version.lista_precios_id, "Mezcladora ficticia")
    sesion.add(models.ReferenciaPrecio(precio_id=bloque.id, referencia="REF-FICTICIA-01"))
    sesion.add(
        models.PrecioOrigen(
            precio_id=mezcladora.id,
            moneda_original="Bs",
            precio_original=D(100),
            fecha_precio=date(2026, 6, 1),
            fuente="cotización ficticia",
        )
    )
    sesion.flush()


def _hallazgos(sesion, version: models.Presupuesto) -> None:
    """Exactamente 2 ERROR, 1 CRITICO y 3 ADVERTENCIA en la versión."""
    sesion.execute(delete(models.Hallazgo).where(models.Hallazgo.presupuesto_id == version.id))
    for severidad in (Severidad.ERROR, Severidad.ERROR, Severidad.CRITICO) + (
        Severidad.ADVERTENCIA,
    ) * 3:
        sesion.add(
            models.Hallazgo(
                presupuesto_id=version.id,
                regla="R0",
                severidad=int(severidad),
                descripcion="hallazgo ficticio",
            )
        )
    sesion.flush()


def _codigo(sesion, nombre: str) -> str:
    return str(
        sesion.scalars(select(models.Proyecto.id).where(models.Proyecto.nombre == nombre)).one()
    )


def test_precios_viejos_cuenta_los_dias_desde_la_vigencia_de_la_lista(sesion) -> None:
    _casa_demo(sesion, date(2026, 6, 1))
    # del 01/06 al 25/10: 29 + 31 + 31 + 30 + 25 = 146 días
    assert precios_viejos(sesion, HOY) == [
        Pendiente(
            obra=_codigo(sesion, "Casa Demo"),
            obra_nombre="Casa Demo",
            texto="Precios de hace 146 días (lista «Base» del 01/06/2026)",
            accion=ACTUALIZAR,
        )
    ]


@pytest.mark.parametrize(
    ("fecha_base", "hay"),
    [
        # del 27/07 al 25/10: 4 + 31 + 30 + 25 = 90 días: no pasa de 90
        (date(2026, 7, 27), False),
        # del 26/07: 91 días
        (date(2026, 7, 26), True),
    ],
)
def test_precios_viejos_desde_mas_de_90_dias(sesion, fecha_base: date, hay: bool) -> None:
    _casa_demo(sesion, fecha_base)
    assert bool(precios_viejos(sesion, HOY)) is hay


def test_lista_vieja_frente_a_la_lista_para_armar(sesion) -> None:
    _casa_demo(sesion, date(2026, 6, 1))
    # del 01/06 al 01/10: 30 + 31 + 31 + 30 = 122 días
    assert lista_vieja(sesion, HOY) == [
        Pendiente(
            obra=_codigo(sesion, "Casa Demo"),
            obra_nombre="Casa Demo",
            texto="La lista de CD-001 es 122 días más vieja que la lista para armar.",
            accion=ACTUALIZAR,
        )
    ]


def test_los_dias_y_las_cuentas_se_escriben_con_punto_de_miles(sesion) -> None:
    # 2023-07-13 → 2023-10-25: 18 + 31 + 30 + 25 = 104 días; → 2026-10-25: + 365 + 366 + 365 =
    # 1 200 días. A la lista para armar (2026-10-01) le faltan 24: 1 176 días.
    _casa_demo(sesion, date(2023, 7, 13))
    (viejos,) = precios_viejos(sesion, HOY)
    assert viejos.texto == "Precios de hace 1.200 días (lista «Base» del 13/07/2023)"
    (vieja,) = lista_vieja(sesion, HOY)
    assert vieja.texto == "La lista de CD-001 es 1.176 días más vieja que la lista para armar."


def test_lista_vieja_de_90_dias_o_menos_no_es_pendiente(sesion) -> None:
    # del 03/07 al 01/10: 28 + 31 + 30 + 1 = 90 días
    _casa_demo(sesion, date(2026, 7, 3))
    assert lista_vieja(sesion, HOY) == []


def test_precios_sin_referencia_ni_origen(sesion) -> None:
    version = _casa_demo(sesion, date(2026, 6, 1))
    _referencias(sesion, version)
    # tres insumos: el bloque con referencia, la mezcladora con origen y la cuadrilla sin nada
    assert precios_sin_referencia(sesion, HOY) == [
        Pendiente(
            obra=_codigo(sesion, "Casa Demo"),
            obra_nombre="Casa Demo",
            texto="1 precio sin referencia en CD-001",
            accion=CATALOGO,
        )
    ]


def test_precios_sin_referencia_en_plural_y_ninguno_si_todos_la_tienen(sesion) -> None:
    version = _casa_demo(sesion, date(2026, 6, 1))
    (pendiente,) = precios_sin_referencia(sesion, HOY)
    assert pendiente.texto == "3 precios sin referencia en CD-001"
    _referencias(sesion, version)
    cuadrilla = _precio(sesion, version.lista_precios_id, "Cuadrilla ficticia")
    sesion.add(models.ReferenciaPrecio(precio_id=cuadrilla.id, referencia="REF-FICTICIA-02"))
    sesion.flush()
    assert precios_sin_referencia(sesion, HOY) == []


def test_hallazgos_graves_cuenta_error_y_critico(sesion) -> None:
    version = _casa_demo(sesion, date(2026, 6, 1))
    _hallazgos(sesion, version)
    # 2 ERROR + 1 CRITICO = 3; las 3 ADVERTENCIA no cuentan
    assert hallazgos_graves(sesion, HOY) == [
        Pendiente(
            obra=_codigo(sesion, "Casa Demo"),
            obra_nombre="Casa Demo",
            texto="3 hallazgos de error o críticos en CD-001",
            accion=HOJA,
        )
    ]


def test_un_hallazgo_grave_en_singular(sesion) -> None:
    version = _casa_demo(sesion, date(2026, 6, 1))
    sesion.execute(delete(models.Hallazgo).where(models.Hallazgo.presupuesto_id == version.id))
    sesion.add(
        models.Hallazgo(
            presupuesto_id=version.id, regla="R0", severidad=int(Severidad.CRITICO),
            descripcion="hallazgo ficticio",
        )
    )  # fmt: skip
    sesion.flush()
    (pendiente,) = hallazgos_graves(sesion, HOY)
    assert pendiente.texto == "1 hallazgo de error o crítico en CD-001"


def test_pendientes_trae_aprobar_precios_y_calidad_en_ese_orden(sesion) -> None:
    version = _casa_demo(sesion, date(2026, 6, 1))
    _referencias(sesion, version)
    _hallazgos(sesion, version)
    codigo = _codigo(sesion, "Casa Demo")

    def item(texto: str, accion: Siguiente) -> Pendiente:
        return Pendiente(codigo, "Casa Demo", texto, accion)

    assert pendientes(sesion, HOY) == [
        GrupoPendientes("aprobar", "Aprobar", ()),  # Casa Demo no tiene envíos
        GrupoPendientes("compras", "Compras", ()),  # Casa Demo no tiene línea base
        GrupoPendientes(
            "precios",
            "Precios",
            (
                item("Precios de hace 146 días (lista «Base» del 01/06/2026)", ACTUALIZAR),
                item("1 precio sin referencia en CD-001", CATALOGO),
            ),
        ),
        GrupoPendientes(
            "calidad",
            "Calidad",
            (
                item("3 hallazgos de error o críticos en CD-001", HOJA),
                item(
                    "La lista de CD-001 es 122 días más vieja que la lista para armar.", ACTUALIZAR
                ),
            ),
        ),
    ]


def test_un_grupo_con_una_fuente_registrada_sale_aunque_no_tenga_pendientes(
    sesion, monkeypatch: pytest.MonkeyPatch
) -> None:
    def ninguna(_sesion, _hoy: date) -> list[Pendiente]:
        return []

    monkeypatch.setitem(mesa.FUENTES, "compras", (ninguna,))
    grupos = pendientes(sesion, HOY)
    assert [(grupo.clave, grupo.titulo, grupo.items) for grupo in grupos] == [
        ("aprobar", "Aprobar", ()),
        ("compras", "Compras", ()),
        ("precios", "Precios", ()),
        ("calidad", "Calidad", ()),
    ]


def test_los_ayudantes_de_las_fuentes_son_publicos(sesion) -> None:
    """Otras fuentes (T9 `pendientes_sin_calculo`) los usan: son parte de la mesa, no privados."""
    version = _casa_demo(sesion, date(2026, 6, 1))
    assert mesa.plural(1, "cantidad escrita", "cantidades escritas") == "1 cantidad escrita"
    assert mesa.plural(1200, "día", "días") == "1.200 días"
    ((fila, vigente),) = list(mesa.versiones_vigentes(sesion))
    assert (fila.nombre, vigente.codigo) == ("Casa Demo", version.codigo)
    assert mesa.pendiente(fila, "texto", mesa.ABRIR_LA_HOJA) == Pendiente(
        _codigo(sesion, "Casa Demo"), "Casa Demo", "texto", mesa.ABRIR_LA_HOJA
    )


def test_los_grupos_y_las_fuentes_de_esta_tarea() -> None:
    assert mesa.GRUPOS == (
        ("aprobar", "Aprobar"),
        ("compras", "Compras"),
        ("precios", "Precios"),
        ("calidad", "Calidad"),
    )
    # T14 agrega «el mercado cobra menos que su costo» (compartido del orquestador).
    assert mesa.FUENTES["precios"] == (
        precios_viejos,
        precios_sin_referencia,
        pendientes_de_mercado,
    )
    # T9 agrega «cantidades escritas a mano sin cálculo» (compartido del orquestador).
    assert mesa.FUENTES["calidad"] == (hallazgos_graves, lista_vieja, pendientes_sin_calculo)
    # T18: «espera dictamen» y «devuelta»; T20: «aprobada y sin entregar» (del orquestador).
    assert mesa.FUENTES["aprobar"] == (pendientes_de_aprobacion, aprobadas_sin_entregar)
    # T23 agrega «las compras de la procura» (compartido del orquestador).
    assert mesa.FUENTES["compras"] == (pendientes_de_compras,)
