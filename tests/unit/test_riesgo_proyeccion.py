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
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.catalog.indices import DefinicionSerie, Observacion, registrar_importacion
from core.contracts.apu import ParametrosCosto
from tests.fixtures.riesgo_proyeccion import (
    ASFALTO,
    CARPETA,
    CASCADA,
    COMPONENTES,
    F_UNO,
    FLETE,
    GASOIL,
    GASOIL_LITRO,
    INICIO,
    MEZCLA,
    PARAMETROS,
    PPI,
    RECETA,
    RIEGO,
    TOLERANCIA,
    TRANSPORTE,
    D,
    apu_ficticio,
    historia_uniforme,
    historia_variable,
    obra_ficticia,
    promedio_compuesto,
    serie_creciente,
)


def _p(**cambios) -> ParametrosProyeccion:
    return ParametrosProyeccion(inicio=INICIO, trayectorias=200, **cambios)


# --- Pruebas --------------------------------------------------------------------------------------


def test_crecimiento_constante_da_un_solo_valor():
    # toda la historia sube 1 % mensual: todas las trayectorias son iguales
    presupuesto, composiciones = obra_ficticia({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = historia_uniforme(ppi=D("1.01"), gasoil=D("1.01"), tasa=D("1.01"))

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
    presupuesto, composiciones = obra_ficticia({RIEGO: D(100), TRANSPORTE: D(40)}, moneda="Bs")
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = historia_variable()

    a = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p(semilla=7))
    b = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p(semilla=7))

    assert a == b
    assert a.semilla == 7
    assert a.percentiles[80] >= a.percentiles[50]


def test_otra_semilla_otro_resultado():
    presupuesto, composiciones = obra_ficticia({RIEGO: D(100), TRANSPORTE: D(40)}, moneda="Bs")
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = historia_variable()

    a = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p(semilla=1))
    b = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p(semilla=2))

    assert a.percentiles != b.percentiles
    assert (a.semilla, b.semilla) == (1, 2)


def test_menos_de_12_meses_completos():
    # Foco de revisión 4: 10 meses de historia dan solo 9 variaciones
    presupuesto, composiciones = obra_ficticia({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})

    with pytest.raises(ValueError, match="^solo hay 9 meses completos; se necesitan 12$"):
        proyectar(presupuesto, composiciones, PARAMETROS, historia_uniforme(n=10), mapa, _p())


def test_una_serie_del_mapa_sin_historia_deja_cero_meses():
    presupuesto, composiciones = obra_ficticia({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = historia_uniforme()
    del historia[GASOIL]

    with pytest.raises(ValueError, match="^solo hay 0 meses completos; se necesitan 12$"):
        proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p())


def test_mes_faltante_en_una_serie_se_descarta_para_todas():
    presupuesto, composiciones = obra_ficticia({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    completa = proyectar(presupuesto, composiciones, PARAMETROS, historia_uniforme(), mapa, _p())

    sin_el_ultimo = historia_uniforme()
    del sin_el_ultimo[GASOIL][date(2026, 12, 1)]
    p = proyectar(presupuesto, composiciones, PARAMETROS, sin_el_ultimo, mapa, _p())

    assert completa.meses_usados == 36
    assert p.meses_usados == 35


def test_un_hueco_en_medio_cuesta_dos_meses():
    # sin junio de 2025 no hay variación de junio (le falta el mes) ni de julio (le falta la base)
    presupuesto, composiciones = obra_ficticia({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = historia_uniforme()
    del historia[SERIE_TASA][date(2025, 6, 1)]

    p = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p())

    assert p.meses_usados == 34


def test_una_entrada_vieja_del_mapa_no_baja_los_meses():
    # el mapa aún nombra el asfalto, que ya no está en el presupuesto (solo el flete, en Bs), y su
    # serie solo tiene 6 meses: los meses completos se cuentan con las series de lo que sí está
    presupuesto, composiciones = obra_ficticia({TRANSPORTE: D(50)}, moneda="Bs")
    mapa = MapaSeries({FLETE: SERIE_TASA, ASFALTO: PPI})
    historia = historia_uniforme()
    historia[PPI] = {m: v for m, v in historia[PPI].items() if m >= date(2026, 7, 1)}

    p = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p())

    assert p.meses_usados == 36


def test_la_historia_posterior_al_inicio_no_cuenta():
    presupuesto, composiciones = obra_ficticia({RIEGO: D(100)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
    historia = historia_uniforme(ppi=D("1.01"), gasoil=D("1.01"), tasa=D("1.01"))
    base = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p())

    for serie in historia.values():
        serie[date(2027, 1, 1)] = D(999999)  # el mes del inicio y el futuro no se ven
        serie[date(2027, 2, 1)] = D(1)
    p = proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p())

    assert p == base


def test_la_mezcla_sube_si_sube_el_asfalto():
    # solo el PPI sube 1 % mensual; el cemento asfáltico CA-30 lo sigue y la mezcla se recalcula
    presupuesto, composiciones = obra_ficticia({CARPETA: D(1000)})
    mapa = MapaSeries({"CA-30": PPI})

    p = proyectar(
        presupuesto,
        composiciones,
        PARAMETROS,
        historia_uniforme(ppi=D("1.01")),
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
    presupuesto, composiciones = obra_ficticia({CARPETA: D(1000)})

    with pytest.raises(ValueError, match="costo de planta por tonelada de «Costo propio de mezcla"):
        proyectar(
            presupuesto,
            composiciones,
            PARAMETROS,
            historia_uniforme(),
            MapaSeries({"CA-30": PPI}),
            _p(),
            recetas={MEZCLA: RECETA},
            precio_de_componente=COMPONENTES,
        )


def test_insumo_en_bs_sin_serie_sigue_la_tasa():
    # presupuesto en Bs, el flete no tiene serie: USD fijo × tasa, y la tasa sube 2 % mensual
    presupuesto, composiciones = obra_ficticia({TRANSPORTE: D(50)}, moneda="Bs")

    p = proyectar(
        presupuesto,
        composiciones,
        PARAMETROS,
        historia_uniforme(tasa=D("1.02")),
        MapaSeries({}),
        _p(),
    )

    # 50 × 20 × 1,265 = 1.265; 1,02^k suma 6,434283382464 (k = 1..6)
    assert p.total_base == D("1265")
    esperado = D("1265") * D("6.434283382464") / 6
    assert abs(p.percentiles[80] - esperado) < TOLERANCIA


def test_insumo_en_usd_sin_serie_queda_fijo():
    presupuesto, composiciones = obra_ficticia({TRANSPORTE: D(50)}, moneda="USD")

    p = proyectar(
        presupuesto,
        composiciones,
        PARAMETROS,
        historia_uniforme(tasa=D("1.02")),
        MapaSeries({}),
        _p(),
    )

    assert p.percentiles == {50: D("1265"), 80: D("1265")}
    assert p.reserva == 0
    assert p.contribucion == ()


def test_serie_en_usd_en_presupuesto_en_bs_se_compone_con_la_tasa():
    # el PPI sube 1 % y la tasa 2 %: el asfalto en Bs sube 1,01 × 1,02 = 1,0302 por mes
    presupuesto, composiciones = obra_ficticia({RIEGO: D(100)}, moneda="Bs")
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})

    p = proyectar(
        presupuesto,
        composiciones,
        PARAMETROS,
        historia_uniforme(ppi=D("1.01"), tasa=D("1.02")),
        mapa,
        _p(),
    )

    # asfalto 100 × 300 y gasoil 100 × 5, cada uno × 1,265
    asfalto = D(100) * D(300) * CASCADA * promedio_compuesto(D("1.0302"))
    gasoil = D(100) * D(5) * CASCADA * promedio_compuesto(D("1.02"))
    assert abs(p.percentiles[50] - (asfalto + gasoil)) < TOLERANCIA


def test_contribucion_por_insumo_de_mayor_a_menor():
    # asfalto con el PPI (+1 %), gasoil con su serie (+0,5 %), flete en USD sin serie (fijo)
    presupuesto, composiciones = obra_ficticia({RIEGO: D(100), TRANSPORTE: D(10)})
    mapa = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})

    p = proyectar(
        presupuesto,
        composiciones,
        PARAMETROS,
        historia_uniforme(ppi=D("1.01"), gasoil=D("1.005")),
        mapa,
        _p(),
    )

    assert [insumo for insumo, _ in p.contribucion] == [ASFALTO, GASOIL_LITRO]
    (_, asfalto), (_, gasoil) = p.contribucion
    assert abs(asfalto - D(100) * D(300) * CASCADA * (F_UNO - 1)) < TOLERANCIA
    assert abs(gasoil - D(100) * D(5) * CASCADA * (promedio_compuesto(D("1.005")) - 1)) < (
        TOLERANCIA
    )


def test_supuestos_declarados():
    presupuesto, composiciones = obra_ficticia({TRANSPORTE: D(50)}, moneda="Bs")

    p = proyectar(presupuesto, composiciones, PARAMETROS, historia_uniforme(), MapaSeries({}), _p())

    assert any("gasto uniforme" in s for s in p.supuestos)
    assert any("USD fijo × tasa" in s for s in p.supuestos)
    assert any("más cercano por rango" in s for s in p.supuestos)
    assert any("36 meses completos" in s for s in p.supuestos)


def test_dos_precios_para_el_mismo_insumo_se_niega():
    otro = apu_ficticio("VIA-04", [(FLETE, "t", D(1), D(25))])
    presupuesto, composiciones = obra_ficticia({TRANSPORTE: D(1), otro: D(1)})

    with pytest.raises(ValueError, match="«Flete» tiene dos precios"):
        proyectar(presupuesto, composiciones, PARAMETROS, historia_uniforme(), MapaSeries({}), _p())


def test_composiciones_que_no_reproducen_el_total_se_niegan():
    presupuesto, composiciones = obra_ficticia({TRANSPORTE: D(50)})
    otros = ParametrosCosto(
        fcas=D(0), bono_alimentacion=D(0), administracion=D("0.20"), utilidad=D("0.10")
    )

    with pytest.raises(ValueError, match="no reproducen el total del presupuesto"):
        proyectar(presupuesto, composiciones, otros, historia_uniforme(), MapaSeries({}), _p())


def test_serie_de_moneda_desconocida_se_niega():
    presupuesto, composiciones = obra_ficticia({TRANSPORTE: D(50)}, moneda="Bs")
    historia = historia_uniforme()
    historia["INDICE_BS_X"] = serie_creciente(D("1.01"))

    mapa = MapaSeries({FLETE: "INDICE_BS_X"})

    with pytest.raises(ValueError, match="INDICE_BS_X"):
        proyectar(presupuesto, composiciones, PARAMETROS, historia, mapa, _p())


def test_insumo_que_sigue_la_tasa_en_presupuesto_en_usd_se_niega():
    presupuesto, composiciones = obra_ficticia({TRANSPORTE: D(50)}, moneda="USD")
    mapa = MapaSeries({FLETE: SERIE_TASA})

    with pytest.raises(ValueError, match="presupuesto en USD .*: Flete$"):
        proyectar(presupuesto, composiciones, PARAMETROS, historia_uniforme(), mapa, _p())


def test_insumo_que_sigue_la_tasa_en_presupuesto_en_bs():
    presupuesto, composiciones = obra_ficticia({TRANSPORTE: D(50)}, moneda="Bs")
    mapa = MapaSeries({FLETE: SERIE_TASA})

    p = proyectar(
        presupuesto, composiciones, PARAMETROS, historia_uniforme(tasa=D("1.02")), mapa, _p()
    )

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
    presupuesto, composiciones = obra_ficticia({TRANSPORTE: D(50)})
    p = proyectar(presupuesto, composiciones, PARAMETROS, historia_uniforme(), MapaSeries({}), _p())
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
