"""Tarea 13 del plan vial: proyección del riesgo por remuestreo de meses históricos completos.

Los oráculos se calculan a mano aquí, sin pasar por el módulo: el crecimiento constante del 1 %
mensual da en cada mes del plazo 1,01^k y, con gasto uniforme en 6 meses, el factor es el promedio
de 1,01; 1,0201; 1,030301; 1,04060401; 1,0510100501 y 1,061520150601 (suman 6,213535210701). Los
totales salen de la fórmula del motor (NORMAS.md §4): materiales completos, administración 15 % y
utilidad 10 % en cascada (× 1,265), sin mano de obra ni bono para que el total sea lineal en los
precios.

Todo es ficticio: insumos, recetas, series y tasa inventados para la prueba (ninguna cifra real).
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from decimal import Decimal

import pytest

from aplicacion.riesgo.proyeccion import (
    SERIE_TASA,
    ParametrosProyeccion,
    Proyeccion,
    historia_para_proyectar,
    percentil_mas_cercano_por_rango,
    proyectar,
)
from aplicacion.riesgo.series import MapaSeries
from core.budget import generar_presupuesto
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.catalog.indices import DefinicionSerie, Observacion, registrar_importacion
from core.contracts.apu import ComposicionAPU, LineaMaterial, ParametrosCosto
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from produccion.receta import Componente, Receta

D = Decimal
PPI = "CEMENTO_ASFALTICO_PPI"
GASOIL = "GASOIL_USD"
INICIO = date(2027, 1, 1)
CIEN = Decimal(100)
UNO = Decimal(1)
CASCADA = D("1.15") * D("1.10")  # administración y utilidad en cascada: 1,265
PARAMETROS = ParametrosCosto(
    fcas=D(0), bono_alimentacion=D(0), administracion=D("0.15"), utilidad=D("0.10")
)
TOLERANCIA = D("0.000001")

#: Suma de 1,01^k para k = 1..6, escrita a mano (véase el encabezado).
SUMA_UNO_POR_CIENTO = D("6.213535210701")
F_UNO = SUMA_UNO_POR_CIENTO / 6

MEZCLA = "Costo propio de mezcla 01"
ASFALTO = "Cemento asfáltico"
GASOIL_LITRO = "Gasoil"
FLETE = "Flete"


# --- Historia ficticia ----------------------------------------------------------------------------


def _mes(base: date, desplazamiento: int) -> date:
    indice = base.year * 12 + base.month - 1 + desplazamiento
    return date(indice // 12, indice % 12 + 1, 1)


def _meses(n: int, *, hasta_antes_de: date = INICIO) -> list[date]:
    """Los `n` meses que terminan el mes anterior a `hasta_antes_de`, en orden."""
    return [_mes(hasta_antes_de, -i) for i in range(n, 0, -1)]


def _creciente(variacion: Decimal, n: int = 37, inicial: Decimal = CIEN) -> dict[date, Decimal]:
    """`n` meses con la misma variación mensual (37 puntos = 36 variaciones antes de INICIO)."""
    return {m: inicial * variacion**i for i, m in enumerate(_meses(n))}


def _con_variaciones(variaciones: list[Decimal], inicial: Decimal = CIEN) -> dict[date, Decimal]:
    valores = [inicial]
    for v in variaciones:
        valores.append(valores[-1] * v)
    return dict(zip(_meses(len(valores)), valores, strict=True))


def _historia(ppi=UNO, gasoil=UNO, tasa=UNO, n: int = 37):
    return {
        PPI: _creciente(ppi, n),
        GASOIL: _creciente(gasoil, n),
        SERIE_TASA: _creciente(tasa, n, inicial=D(40)),
    }


def _promedio_compuesto(variacion: Decimal, meses: int = 6) -> Decimal:
    """El oráculo del gasto uniforme: promedio de variacion^k, k = 1..meses."""
    return sum((variacion**k for k in range(1, meses + 1)), D(0)) / meses


# --- Presupuesto ficticio -------------------------------------------------------------------------


def _apu(codigo: str, lineas: list[tuple[str, str, Decimal, Decimal]]) -> ComposicionAPU:
    return ComposicionAPU(
        codigo_partida=codigo,
        descripcion=f"Partida ficticia {codigo}",
        unidad="t",
        rendimiento=D(1),
        materiales=tuple(LineaMaterial(d, u, q, p) for d, u, q, p in lineas),
    )


CARPETA = _apu("VIA-01", [(MEZCLA, "t", D(1), D("46.75"))])
RIEGO = _apu("VIA-02", [(ASFALTO, "t", D("0.5"), D(600)), (GASOIL_LITRO, "l", D(10), D("0.5"))])
TRANSPORTE = _apu("VIA-03", [(FLETE, "t", D(1), D(20))])


def _obra(cantidades: dict[ComposicionAPU, Decimal], moneda: str = "USD"):
    composiciones = {apu.codigo_partida: apu for apu in cantidades}
    items = [
        ItemComputo(
            codigo_partida=apu.codigo_partida,
            descripcion=apu.descripcion,
            unidad=apu.unidad,
            cantidad=cantidad,
            origen_id=f"ficticio:{apu.codigo_partida}",
            origen_tipo=OrigenTipo.MANUAL,
            dominio=Dominio.CIVIL,
        )
        for apu, cantidad in cantidades.items()
    ]
    presupuesto = generar_presupuesto(
        items, composiciones, PARAMETROS, codigo="RV-1", fecha=date(2026, 12, 15), moneda=moneda
    )
    return presupuesto, composiciones


RECETA = Receta(
    id=1,
    producto="01",
    componentes=(
        Componente("AGR-12", D("0.95"), "t", "propio"),
        Componente("CA-30", D("0.05"), "t", "comprado"),
    ),
    fuente="Dosificación ficticia",
    vigente_desde=date(2026, 1, 1),
)
#: 0,95 × 5 + 0,05 × 600 + 12 de planta = 4,75 + 30 + 12 = 46,75 (el precio de la carpeta).
COMPONENTES = {"AGR-12": D(5), "CA-30": D(600)}


def _p(**cambios) -> ParametrosProyeccion:
    return ParametrosProyeccion(inicio=INICIO, trayectorias=200, **cambios)


# --- Pruebas --------------------------------------------------------------------------------------


def test_crecimiento_constante_da_un_solo_valor():
    # toda la historia sube 1 % mensual: todas las trayectorias son iguales
    presupuesto, composiciones = _obra({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = _historia(ppi=D("1.01"), gasoil=D("1.01"), tasa=D("1.01"))

    p = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p(meses=6))

    # 100 × (0,5 × 600 + 10 × 0,5) × 1,265 = 38.582,5
    assert p.total_base == D("38582.5")
    esperado = D("38582.5") * F_UNO
    assert p.percentiles[50] == p.percentiles[80]
    assert abs(p.percentiles[50] - esperado) < TOLERANCIA  # exacto; se redondea al presentar
    assert abs(p.reserva - (esperado - D("38582.5"))) < TOLERANCIA
    assert p.meses_usados == 36
    assert set(p.percentiles) == {50, 80}


def test_misma_semilla_mismo_resultado():
    presupuesto, composiciones = _obra({RIEGO: D(100), TRANSPORTE: D(40)}, moneda="Bs")
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = _historia_variable()

    a = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p(semilla=7))
    b = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p(semilla=7))

    assert a == b
    assert a.semilla == 7
    assert a.percentiles[80] >= a.percentiles[50]


def test_otra_semilla_otro_resultado():
    presupuesto, composiciones = _obra({RIEGO: D(100), TRANSPORTE: D(40)}, moneda="Bs")
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = _historia_variable()

    a = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p(semilla=1))
    b = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p(semilla=2))

    assert a.percentiles != b.percentiles
    assert (a.semilla, b.semilla) == (1, 2)


def _historia_variable():
    """Variaciones escritas a mano (36), distintas entre series para que el remuestreo importe."""
    ppi = [D(x) for x in ("1.03", "0.97", "1.05", "1.00", "0.98", "1.08")] * 6
    gasoil = [D(x) for x in ("1.00", "1.00", "1.10", "1.00", "1.00", "0.95")] * 6
    tasa = [D(x) for x in ("1.02", "1.06", "1.01", "1.12", "1.00", "1.04")] * 6
    return {
        PPI: _con_variaciones(ppi),
        GASOIL: _con_variaciones(gasoil, inicial=D("0.5")),
        SERIE_TASA: _con_variaciones(tasa, inicial=D(40)),
    }


def test_menos_de_12_meses_completos():
    # Foco de revisión 4: 10 meses de historia dan solo 9 variaciones
    presupuesto, composiciones = _obra({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})

    with pytest.raises(ValueError, match="^solo hay 9 meses completos; se necesitan 12$"):
        proyectar(presupuesto, composiciones, PARAMETROS, _historia(n=10), mapa, _p())


def test_una_serie_del_mapa_sin_historia_deja_cero_meses():
    presupuesto, composiciones = _obra({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = _historia()
    del historia[GASOIL]

    with pytest.raises(ValueError, match="^solo hay 0 meses completos; se necesitan 12$"):
        proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p())


def test_mes_faltante_en_una_serie_se_descarta_para_todas():
    presupuesto, composiciones = _obra({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    completa = proyectar(presupuesto, composiciones, PARAMETROS, _historia(), mapa, _p())

    sin_el_ultimo = _historia()
    del sin_el_ultimo[GASOIL][date(2026, 12, 1)]
    p = proyectar(presupuesto, composiciones, PARAMETROS, sin_el_ultimo, mapa, _p())

    assert completa.meses_usados == 36
    assert p.meses_usados == 35


def test_un_hueco_en_medio_cuesta_dos_meses():
    # sin junio de 2025 no hay variación de junio (le falta el mes) ni de julio (le falta la base)
    presupuesto, composiciones = _obra({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = _historia()
    del historia[SERIE_TASA][date(2025, 6, 1)]

    p = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p())

    assert p.meses_usados == 34


def test_la_historia_posterior_al_inicio_no_cuenta():
    presupuesto, composiciones = _obra({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = _historia(ppi=D("1.01"), gasoil=D("1.01"), tasa=D("1.01"))
    base = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p())

    for serie in historia.values():
        serie[date(2027, 1, 1)] = D(999999)  # el mes del inicio y el futuro no se ven
        serie[date(2027, 2, 1)] = D(1)
    p = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p())

    assert p == base


def test_la_mezcla_sube_si_sube_el_asfalto():
    # solo el PPI sube 1 % mensual; el cemento asfáltico CA-30 lo sigue y la mezcla se recalcula
    presupuesto, composiciones = _obra({CARPETA: D(1000)})
    mapa = MapaSeries({"CA-30": PPI})

    p = proyectar(
        presupuesto,
        composiciones,
        PARAMETROS,
        _historia(ppi=D("1.01")),
        mapa,
        _p(),
        recetas={MEZCLA: RECETA},
        costo_planta_por_t={MEZCLA: D(12)},
        precio_de_componente=COMPONENTES,
    )

    # base: 1000 × 46,75 × 1,265 = 59.138,75; la mezcla pasa a 4,75 + 30 × F + 12
    assert p.total_base == D("59138.75")
    esperado = D(1000) * (D("16.75") + D(30) * F_UNO) * CASCADA
    assert abs(p.percentiles[50] - esperado) < TOLERANCIA
    assert p.percentiles[50] > p.total_base
    [(insumo, monto)] = p.contribucion
    assert insumo == MEZCLA
    assert abs(monto - D(1000) * D(30) * (F_UNO - 1) * CASCADA) < TOLERANCIA


def test_mezcla_sin_costo_de_planta_se_niega():
    presupuesto, composiciones = _obra({CARPETA: D(1000)})

    with pytest.raises(ValueError, match="costo de planta por tonelada de «Costo propio de mezcla"):
        proyectar(
            presupuesto,
            composiciones,
            PARAMETROS,
            _historia(),
            MapaSeries({"CA-30": PPI}),
            _p(),
            recetas={MEZCLA: RECETA},
            precio_de_componente=COMPONENTES,
        )


def test_insumo_en_bs_sin_serie_sigue_la_tasa():
    # presupuesto en Bs, el flete no tiene serie: USD fijo × tasa, y la tasa sube 2 % mensual
    presupuesto, composiciones = _obra({TRANSPORTE: D(50)}, moneda="Bs")

    p = proyectar(
        presupuesto, composiciones, PARAMETROS, _historia(tasa=D("1.02")), MapaSeries({}), _p()
    )

    # 50 × 20 × 1,265 = 1.265; 1,02^k suma 6,434283382464 (k = 1..6)
    assert p.total_base == D("1265")
    esperado = D("1265") * D("6.434283382464") / 6
    assert abs(p.percentiles[80] - esperado) < TOLERANCIA


def test_insumo_en_usd_sin_serie_queda_fijo():
    presupuesto, composiciones = _obra({TRANSPORTE: D(50)}, moneda="USD")

    p = proyectar(
        presupuesto, composiciones, PARAMETROS, _historia(tasa=D("1.02")), MapaSeries({}), _p()
    )

    assert p.percentiles == {50: D("1265"), 80: D("1265")}
    assert p.reserva == 0
    assert p.contribucion == ()


def test_serie_en_usd_en_presupuesto_en_bs_se_compone_con_la_tasa():
    # el PPI sube 1 % y la tasa 2 %: el asfalto en Bs sube 1,01 × 1,02 = 1,0302 por mes
    presupuesto, composiciones = _obra({RIEGO: D(100)}, moneda="Bs")
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})

    p = proyectar(
        presupuesto,
        composiciones,
        PARAMETROS,
        _historia(ppi=D("1.01"), tasa=D("1.02")),
        mapa,
        _p(),
    )

    # asfalto 100 × 300 y gasoil 100 × 5, cada uno × 1,265
    asfalto = D(100) * D(300) * CASCADA * _promedio_compuesto(D("1.0302"))
    gasoil = D(100) * D(5) * CASCADA * _promedio_compuesto(D("1.02"))
    assert abs(p.percentiles[50] - (asfalto + gasoil)) < TOLERANCIA


def test_contribucion_por_insumo_de_mayor_a_menor():
    # asfalto con el PPI (+1 %), gasoil con su serie (+0,5 %), flete en USD sin serie (fijo)
    presupuesto, composiciones = _obra({RIEGO: D(100), TRANSPORTE: D(10)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})

    p = proyectar(
        presupuesto,
        composiciones,
        PARAMETROS,
        _historia(ppi=D("1.01"), gasoil=D("1.005")),
        mapa,
        _p(),
    )

    assert [insumo for insumo, _ in p.contribucion] == [ASFALTO, GASOIL_LITRO]
    (_, asfalto), (_, gasoil) = p.contribucion
    assert abs(asfalto - D(100) * D(300) * CASCADA * (F_UNO - 1)) < TOLERANCIA
    assert abs(gasoil - D(100) * D(5) * CASCADA * (_promedio_compuesto(D("1.005")) - 1)) < (
        TOLERANCIA
    )


def test_supuestos_declarados():
    presupuesto, composiciones = _obra({TRANSPORTE: D(50)}, moneda="Bs")

    p = proyectar(presupuesto, composiciones, PARAMETROS, _historia(), MapaSeries({}), _p())

    assert any("gasto uniforme" in s for s in p.supuestos)
    assert any("USD fijo × tasa" in s for s in p.supuestos)
    assert any("más cercano por rango" in s for s in p.supuestos)
    assert any("36 meses completos" in s for s in p.supuestos)


def test_dos_precios_para_el_mismo_insumo_se_niega():
    otro = _apu("VIA-04", [(FLETE, "t", D(1), D(25))])
    presupuesto, composiciones = _obra({TRANSPORTE: D(1), otro: D(1)})

    with pytest.raises(ValueError, match="«Flete» tiene dos precios"):
        proyectar(presupuesto, composiciones, PARAMETROS, _historia(), MapaSeries({}), _p())


def test_composiciones_que_no_reproducen_el_total_se_niegan():
    presupuesto, composiciones = _obra({TRANSPORTE: D(50)})
    otros = ParametrosCosto(
        fcas=D(0), bono_alimentacion=D(0), administracion=D("0.20"), utilidad=D("0.10")
    )

    with pytest.raises(ValueError, match="no reproducen el total del presupuesto"):
        proyectar(presupuesto, composiciones, otros, _historia(), MapaSeries({}), _p())


def test_serie_de_moneda_desconocida_se_niega():
    presupuesto, composiciones = _obra({TRANSPORTE: D(50)}, moneda="Bs")
    historia = _historia()
    historia["INDICE_BS_X"] = _creciente(D("1.01"))

    mapa = MapaSeries({FLETE: "INDICE_BS_X"})

    with pytest.raises(ValueError, match="INDICE_BS_X"):
        proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p())


def test_insumo_que_sigue_la_tasa_en_presupuesto_en_usd_se_niega():
    presupuesto, composiciones = _obra({TRANSPORTE: D(50)}, moneda="USD")
    mapa = MapaSeries({FLETE: SERIE_TASA})

    with pytest.raises(ValueError, match="presupuesto en USD .*: Flete$"):
        proyectar(presupuesto, composiciones, PARAMETROS, _historia(), mapa, _p())


def test_insumo_que_sigue_la_tasa_en_presupuesto_en_bs():
    presupuesto, composiciones = _obra({TRANSPORTE: D(50)}, moneda="Bs")
    mapa = MapaSeries({FLETE: SERIE_TASA})

    p = proyectar(presupuesto, composiciones, PARAMETROS, _historia(tasa=D("1.02")), mapa, _p())

    esperado = D("1265") * D("6.434283382464") / 6
    assert abs(p.percentiles[50] - esperado) < TOLERANCIA


def test_percentil_mas_cercano_por_rango():
    diez = [D(v) for v in range(10, 0, -1)]  # desordenados a propósito
    assert percentil_mas_cercano_por_rango(diez, 50) == D(5)  # rango ⌈0,5 × 10⌉ = 5
    assert percentil_mas_cercano_por_rango(diez, 80) == D(8)
    assert percentil_mas_cercano_por_rango(diez, 95) == D(10)  # ⌈9,5⌉ = 10
    assert percentil_mas_cercano_por_rango(diez, 1) == D(1)
    siete = [D(v) for v in range(1, 8)]
    assert percentil_mas_cercano_por_rango(siete, 50) == D(4)  # ⌈3,5⌉ = 4


@pytest.mark.parametrize(
    ("cambios", "texto"),
    [
        ({"meses": 0}, "meses"),
        ({"trayectorias": 0}, "trayectorias"),
        ({"ventana_meses": 11}, "ventana"),
        ({"percentiles": (50,)}, "80"),
        ({"percentiles": (0, 80)}, "percentil"),
        ({"percentiles": (80, 101)}, "percentil"),
    ],
)
def test_parametros_fuera_de_rango(cambios, texto):
    with pytest.raises(ValueError, match=texto):
        ParametrosProyeccion(inicio=INICIO, **cambios)


def test_parametros_por_defecto_son_los_de_d_v_3():
    p = ParametrosProyeccion(inicio=INICIO)
    assert (p.meses, p.semilla, p.trayectorias, p.ventana_meses, p.percentiles) == (
        6,
        1,
        2000,
        36,
        (50, 80),
    )


def test_proyeccion_es_inmutable():
    presupuesto, composiciones = _obra({TRANSPORTE: D(50)})
    p = proyectar(presupuesto, composiciones, PARAMETROS, _historia(), MapaSeries({}), _p())
    assert isinstance(p, Proyeccion)
    with pytest.raises(AttributeError):
        p.reserva = D(0)  # type: ignore[misc]


# --- La historia de la base: hasta el fin del mes anterior al inicio ------------------------------


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{(tmp_path / 'proyeccion.db').as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        yield sesion
    motor.dispose()


def _sembrar(sesion, codigo: str, unidad: str, periodicidad: str, fechas: list[date]) -> None:
    registrar_importacion(
        sesion,
        DefinicionSerie(codigo, f"{codigo} ficticia", "Prueba", unidad, periodicidad),
        [Observacion(f, D(i + 1), False) for i, f in enumerate(fechas)],
        archivo=f"{codigo}.csv",
        huella=hashlib.sha256(codigo.encode()).hexdigest(),
        fuente="prueba ficticia",
        fecha_descarga=date(2027, 3, 1),
        responsable="Prueba",
        filas_leidas=len(fechas),
        filas_rechazadas=0,
        informe="",
        ahora=datetime(2027, 3, 1, 12, 0),
    )


def test_historia_para_proyectar_lee_hasta_el_fin_del_mes_anterior(sesion):
    # inicio a mitad de octubre de 2026: la ventana va de octubre de 2023 a septiembre de 2026 y
    # la variación del primer mes necesita septiembre de 2023
    _sembrar(
        sesion,
        PPI,
        "indice",
        "mensual",
        [date(2023, 8, 1), date(2023, 9, 1), date(2026, 9, 1), date(2026, 10, 1)],
    )
    _sembrar(
        sesion,
        SERIE_TASA,
        "Bs/USD",
        "diaria",
        [date(2023, 9, 10), date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 5)],
    )
    p = ParametrosProyeccion(inicio=date(2026, 10, 15))

    historia = historia_para_proyectar(sesion, MapaSeries({ASFALTO: PPI}), p)

    assert historia == {
        PPI: {date(2023, 9, 1): D(2), date(2026, 9, 1): D(3)},
        SERIE_TASA: {date(2023, 9, 1): D(1), date(2026, 9, 1): D(3)},
    }
