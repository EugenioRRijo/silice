"""El plan desde los rendimientos (MP-7, Tarea 21 de `docs/planes/PLAN_MONTAR_PRESUPUESTO.md`).

Contrato:

- Duración de cada partida = cantidad ÷ rendimiento ÷ cuadrillas, hacia arriba al medio día; sin
  composición → 1 día y «{código} no tiene rendimiento: se le asignó 1 día.»; cantidad 0 → 0 días,
  fuera del plan y «{código} tiene cantidad 0.».
- Encadenado en el orden del presupuesto; una partida en paralelo empieza donde empezó la anterior y
  la siguiente no paralela, en el mayor fin alcanzado. Fracción de un período = días de la partida
  dentro del período ÷ duración, a 0,000001 (ROUND_HALF_UP); el último período de la partida
  absorbe el residuo y cada partida suma exactamente 1. «Dia n» en días hábiles; «Semana n» con 5.
- `POST /v1/hoja/borradores/{id}/plan/rendimientos` `{rev, cuadrillas, paralelas, unidad}` →
  `{rev, resumen, plan, avisos}`; `crear_primera_version` sin plan guarda el de rendimientos.

Datos FICTICIOS: la vivienda de `tests/fixtures/obra_vivienda.py`. Oráculos a mano (la cuenta va
en cada comentario): duraciones 18 ÷ 4,5 = 4; 12 ÷ 6 = 2; 950 ÷ 250 = 3,8 → 4; 210 ÷ 12 = 17,5;
420 ÷ 18 = 23,33… → 23,5; 420 ÷ 60 = 7; en total 4 + 2 + 4 + 17,5 + 23,5 + 7 = 58 días.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from api.rutas import hoja as rutas_hoja
from aplicacion import hoja, hoja_borradores, hoja_edicion, hoja_guardado
from aplicacion.errores import HojaInvalida
from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from aplicacion.plan_rendimientos import (
    CuadrillasInvalidas,
    Duracion,
    PlanDemasiadoLargo,
    cuadrillas_escritas,
    duraciones,
    paralelas_del_plan,
    plan_del_borrador,
    plan_por_rendimientos,
    plan_que_cabe,
)
from core.budget import crear_proyecto
from core.budget.moneda import declarar_moneda
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.obra_vivienda import COMPOSICIONES, FECHA, ITEMS, item, sembrar_catalogo
from tests.fixtures.sesion_web import (
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

D = Decimal
OBRA = "Vivienda Demo 80 m2"
ANA = "Ana <ana>"
CODIGOS = ["OBRA-01", "OBRA-02", "OBRA-03", "OBRA-04", "OBRA-05", "OBRA-06"]
SIN_RENDIMIENTO = "OBRA-99 no tiene rendimiento: se le asignó 1 día."
CANTIDAD_CERO = "OBRA-02 tiene cantidad 0."
CUADRILLAS_INVALIDAS = "Las cuadrillas de OBRA-04 deben ser un número entero de 1 a 99."
PARTIDA_AJENA = (
    "Las cuadrillas o las partidas en paralelo nombran una partida que no está en el "
    "presupuesto: vuelva a cargar el plan."
)
DEMASIADO_LARGO = (
    "El plan desde los rendimientos tendría 501 períodos y la matriz admite 500: elija semanas o "
    "meses, o más cuadrillas."
)
FORMA_RENDIMIENTOS = (
    "El plan desde los rendimientos no tiene la forma esperada: envíe rev (entero), las "
    "cuadrillas de cada partida como texto, las partidas en paralelo y la unidad (dia, semana o "
    "mes)."
)
REV_VIEJO = "El borrador cambió en otra ventana: vuelva a cargarlo."


def _fracciones(plan, codigo: str) -> dict[str, Decimal]:
    """Las fracciones de `codigo` por etiqueta (solo los períodos en que aparece)."""
    return {e: f for e, reparto in plan for c, f in reparto if c == codigo}


def _primer_periodo(plan, codigo: str) -> str:
    return next(e for e, reparto in plan for c, _ in reparto if c == codigo)


def _dias(n: int, desde: int = 1) -> list[str]:
    return [f"Dia {k}" for k in range(desde, desde + n)]


def _sin_composicion(codigo: str = "OBRA-99", cantidad: str = "5") -> ItemComputo:
    return ItemComputo(
        codigo_partida=codigo,
        descripcion="Partida sin APU",
        unidad="m2",
        cantidad=D(cantidad),
        origen_id="FILA-99",
        origen_tipo=OrigenTipo.TABULAR,
        dominio=Dominio.CIVIL,
    )


# --- duraciones ---------------------------------------------------------------------------------


def test_las_duraciones_de_la_vivienda_salen_de_cantidad_entre_rendimiento():
    # 18 ÷ 4,5 = 4; 12 ÷ 6 = 2; 950 ÷ 250 = 3,8 → 4; 210 ÷ 12 = 17,5; 420 ÷ 18 = 23,33… → 23,5;
    # 420 ÷ 60 = 7 (hacia arriba al medio día)
    assert duraciones(ITEMS, COMPOSICIONES, {}) == [
        Duracion("OBRA-01", D("4"), ""),
        Duracion("OBRA-02", D("2"), ""),
        Duracion("OBRA-03", D("4"), ""),
        Duracion("OBRA-04", D("17.5"), ""),
        Duracion("OBRA-05", D("23.5"), ""),
        Duracion("OBRA-06", D("7"), ""),
    ]


def test_dos_cuadrillas_dividen_la_duracion_y_se_redondea_al_medio_dia():
    # OBRA-04: 210 ÷ 12 ÷ 2 = 8,75 → 9 días
    obra_04 = duraciones(ITEMS, COMPOSICIONES, {"OBRA-04": 2})[3]
    assert obra_04 == Duracion("OBRA-04", D("9"), "")


def test_dos_renglones_de_la_misma_partida_suman_su_cantidad():
    # 105 + 105 = 210 m2 de OBRA-04 → 210 ÷ 12 = 17,5 días en una sola duración
    renglones = [item("OBRA-04", "105", 1), item("OBRA-04", "105", 2)]
    assert duraciones(renglones, COMPOSICIONES, {}) == [Duracion("OBRA-04", D("17.5"), "")]


def test_sin_composicion_es_un_dia_con_aviso_y_cantidad_cero_queda_fuera_con_aviso():
    renglones = [item("OBRA-02", "0"), _sin_composicion()]
    assert duraciones(renglones, COMPOSICIONES, {}) == [
        Duracion("OBRA-02", D("0"), CANTIDAD_CERO),
        Duracion("OBRA-99", D("1"), SIN_RENDIMIENTO),
    ]


# --- el plan en días hábiles ---------------------------------------------------------------------


def test_el_plan_secuencial_de_la_vivienda_dura_58_dias():
    plan = plan_por_rendimientos(duraciones(ITEMS, COMPOSICIONES, {}))
    assert [e for e, _ in plan] == _dias(58)


def test_obra_01_ejecuta_un_cuarto_en_cada_uno_de_sus_cuatro_dias():
    plan = plan_por_rendimientos(duraciones(ITEMS, COMPOSICIONES, {}))
    # 1 día ÷ 4 días = 0,25 en Dia 1 a Dia 4 (OBRA-01 va de 0 a 4)
    assert _fracciones(plan, "OBRA-01") == dict.fromkeys(_dias(4), D("0.25"))


def test_obra_05_empieza_a_medio_dia_y_su_ultimo_dia_absorbe_el_residuo():
    plan = plan_por_rendimientos(duraciones(ITEMS, COMPOSICIONES, {}))
    obra_05 = _fracciones(plan, "OBRA-05")
    # OBRA-05 va de 27,5 a 51: medio día en Dia 28, días enteros en Dia 29 a Dia 51.
    # 0,5 ÷ 23,5 = 0,0212765… → 0,021277; 1 ÷ 23,5 = 0,0425531… → 0,042553;
    # Dia 51: 1 − 0,021277 − 22 × 0,042553 = 1 − 0,021277 − 0,936166 = 0,042557
    assert list(obra_05) == _dias(24, desde=28)
    assert obra_05["Dia 28"] == D("0.021277")
    assert obra_05["Dia 29"] == D("0.042553")
    assert obra_05["Dia 51"] == D("0.042557")
    assert sum(obra_05.values()) == D(1)


def test_el_dia_28_comparte_el_fin_de_obra_04_con_el_inicio_de_obra_05():
    plan = plan_por_rendimientos(duraciones(ITEMS, COMPOSICIONES, {}))
    # OBRA-04 va de 10 a 27,5: Dia 11 a Dia 27 con 1 ÷ 17,5 = 0,0571428… → 0,057143;
    # Dia 28: 1 − 17 × 0,057143 = 1 − 0,971431 = 0,028569
    dia_28 = dict(dict(plan)["Dia 28"])
    assert dia_28 == {"OBRA-04": D("0.028569"), "OBRA-05": D("0.021277")}


def test_cada_partida_suma_exactamente_uno():
    plan = plan_por_rendimientos(duraciones(ITEMS, COMPOSICIONES, {}))
    assert {c: sum(_fracciones(plan, c).values()) for c in CODIGOS} == dict.fromkeys(CODIGOS, D(1))


def test_obra_03_en_paralelo_empieza_con_obra_02_y_el_plan_dura_56_dias():
    plan = plan_por_rendimientos(duraciones(ITEMS, COMPOSICIONES, {}), paralelas={"OBRA-03"})
    # OBRA-02 va de 4 a 6; OBRA-03 en paralelo, de 4 a 8; OBRA-04 empieza en 8 (el mayor fin):
    # 58 − 2 = 56 días
    assert [e for e, _ in plan] == _dias(56)
    assert _fracciones(plan, "OBRA-03") == dict.fromkeys(_dias(4, desde=5), D("0.25"))
    assert _primer_periodo(plan, "OBRA-04") == "Dia 9"


def test_las_paralelas_del_plan_son_las_que_empiezan_con_una_anterior():
    base = duraciones(ITEMS, COMPOSICIONES, {})
    assert paralelas_del_plan(plan_por_rendimientos(base)) == frozenset()
    assert paralelas_del_plan(plan_por_rendimientos(base, paralelas={"OBRA-03"})) == {"OBRA-03"}


def test_foco_4_un_plan_irreal_sigue_siendo_valido_y_lo_dice():
    renglones = [
        item("OBRA-01", "18"),  # 18 ÷ 4,5 = 4 días: de 0 a 4
        item("OBRA-02", "0"),  # cantidad 0: fuera del plan
        _sin_composicion(),  # sin APU: 1 día, de 4 a 5
        item("OBRA-03", "100"),  # 100 ÷ 250 = 0,4 → medio día: de 5 a 5,5
        item("OBRA-06", "420"),  # 420 ÷ 60 = 7, en paralelo con OBRA-03: de 5 a 12
    ]
    lista = duraciones(renglones, COMPOSICIONES, {})
    assert [d.aviso for d in lista if d.aviso] == [CANTIDAD_CERO, SIN_RENDIMIENTO]
    plan = plan_por_rendimientos(lista, paralelas={"OBRA-06"})

    assert [e for e, _ in plan] == _dias(12)
    assert "OBRA-02" not in {c for _, reparto in plan for c, _ in reparto}
    assert _fracciones(plan, "OBRA-99") == {"Dia 5": D(1)}
    assert _fracciones(plan, "OBRA-03") == {"Dia 6": D(1)}  # 0,5 ÷ 0,5
    # 1 ÷ 7 = 0,142857…: seis días de 0,142857 y el último 1 − 0,857142 = 0,142858
    assert _fracciones(plan, "OBRA-06") == {
        **dict.fromkeys(_dias(6, desde=6), D("0.142857")),
        "Dia 12": D("0.142858"),
    }
    # la matriz del editor lo acepta tal cual: cada partida suma exactamente 1
    etiquetas = [e for e, _ in plan]
    filas = [
        {"partida": c, **{e: hoja.texto_editable(f) for e, f in _fracciones(plan, c).items()}}
        for c in ("OBRA-01", "OBRA-99", "OBRA-03", "OBRA-06")
    ]
    releido = hoja.plan_desde_filas(filas, etiquetas)
    assert [(e, sorted(r)) for e, r in releido] == [(e, sorted(r)) for e, r in plan]


# --- el plan en semanas --------------------------------------------------------------------------


def test_en_semanas_obra_01_cae_entera_en_la_semana_1():
    plan = plan_por_rendimientos(duraciones(ITEMS, COMPOSICIONES, {}), unidad="semana")
    # 58 días ÷ 5 días hábiles por semana = 11,6 → 12 semanas
    assert [e for e, _ in plan] == [f"Semana {n}" for n in range(1, 13)]
    # OBRA-01 va de 0 a 4: 4 ÷ 4 = 1 en Semana 1
    assert _fracciones(plan, "OBRA-01") == {"Semana 1": D(1)}
    # OBRA-02 va de 4 a 6: 1 ÷ 2 = 0,5 en Semana 1 (día 5) y 0,5 en Semana 2 (día 6)
    assert _fracciones(plan, "OBRA-02") == {"Semana 1": D("0.5"), "Semana 2": D("0.5")}


# --- topes y textos tecleados --------------------------------------------------------------------


def test_un_plan_de_mas_de_500_periodos_se_rechaza_y_en_semanas_cabe():
    # 2.254,5 ÷ 4,5 = 501 días: la matriz del editor admite 500 períodos
    lista = duraciones([item("OBRA-01", "2254.5")], COMPOSICIONES, {})
    with pytest.raises(PlanDemasiadoLargo) as error:
        plan_por_rendimientos(lista)
    assert str(error.value) == DEMASIADO_LARGO
    # 501 ÷ 5 = 100,2 → 101 semanas
    assert len(plan_por_rendimientos(lista, unidad="semana")) == 101


def test_una_partida_muy_larga_en_semanas_no_deja_un_residuo_negativo():
    # OBRA-01: 15,75 ÷ 4,5 = 3,5 días (de 0 a 3,5); OBRA-06: 148.920 ÷ 60 = 2.482 días (de 3,5 a
    # 2.485,5) → 2.485,5 ÷ 5 = 497,1 → 498 semanas. Redondeando cada semana entera, 5 ÷ 2.482 =
    # 0,0020145… → 0,002015 sube 0,0000005 por semana: en 495 semanas el residuo de la última
    # (0,5 ÷ 2.482 = 0,000201) quedaría en −0,000044. Con el acumulado cuantizado:
    # Semana 1 = 1,5 ÷ 2.482 = 0,000604351… → 0,000604;
    # Semana 2 = 6,5 ÷ 2.482 = 0,0026188… → 0,002619 − 0,000604 = 0,002015;
    # Semana 498 = 1 − (2.481,5 ÷ 2.482 = 0,9997985… → 0,999799) = 0,000201.
    renglones = [item("OBRA-01", "15.75"), item("OBRA-06", "148920")]
    plan = plan_por_rendimientos(duraciones(renglones, COMPOSICIONES, {}), unidad="semana")
    obra_06 = _fracciones(plan, "OBRA-06")
    assert len(plan) == 498
    assert min(obra_06.values()) >= 0
    assert sum(obra_06.values()) == D(1)
    assert obra_06["Semana 1"] == D("0.000604")
    assert obra_06["Semana 2"] == D("0.002015")
    assert obra_06["Semana 498"] == D("0.000201")
    # la matriz del editor lo acepta: ninguna fracción negativa
    etiquetas = [e for e, _ in plan]
    filas = [{"partida": "OBRA-06", **{e: hoja.texto_editable(f) for e, f in obra_06.items()}}]
    assert len(hoja.plan_desde_filas(filas, etiquetas)) == 498


def test_las_cuadrillas_tecleadas_son_enteros_de_1_a_99():
    assert cuadrillas_escritas({"OBRA-04": "2", "OBRA-05": " 1 "}) == {"OBRA-04": 2, "OBRA-05": 1}
    for malo in ("0", "1,5", "dos", "", "100", "-1", "1.000", "01"):
        with pytest.raises(CuadrillasInvalidas) as error:
            cuadrillas_escritas({"OBRA-04": malo})
        assert str(error.value) == CUADRILLAS_INVALIDAS, malo


def test_en_la_hoja_una_partida_con_cantidad_0_va_al_ultimo_periodo_sin_alargar_el_plan():
    renglones = [*ITEMS[:1], item("OBRA-02", "0")]  # OBRA-01 de 0 a 4; OBRA-02 con 0
    plan, avisos = plan_del_borrador(renglones, COMPOSICIONES)
    # la curva exige que cada partida valorada sume 1: OBRA-02 (monto 0) va entera al Dia 4
    assert [e for e, _ in plan] == _dias(4)
    assert _fracciones(plan, "OBRA-02") == {"Dia 4": D(1)}
    assert avisos == [CANTIDAD_CERO]


# --- la edición del borrador vivo -------------------------------------------------------------


@pytest.fixture
def base(tmp_path: Path) -> Iterator:
    """Una base del caso con los seis APU en una lista en Bs y la obra en Bs, sin versiones."""
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    with abrir_sesion(motor) as sesion:
        sembrar_catalogo(sesion)
        declarar_moneda_de_la_carpeta(
            sesion, "Bs", responsable=ANA, ahora=datetime(2026, 11, 2, 8, 0)
        )
        proyecto = crear_proyecto(sesion, OBRA, dominio=Dominio.CIVIL)
        declarar_moneda(sesion, proyecto, "Bs", responsable=ANA)
        sesion.commit()
        yield sesion
    motor.dispose()
    hoja_borradores.olvidar_todo()


def _vivo(plan=None) -> hoja_borradores.BorradorVivo:
    borrador = hoja.Borrador(
        fecha=FECHA, moneda="Bs", items_base=ITEMS, composiciones=COMPOSICIONES, plan=plan
    )
    return hoja_borradores.crear("ficha", "caso", OBRA, None, borrador, None)


def test_el_borrador_toma_el_plan_desde_los_rendimientos(base):
    vivo = _vivo()
    editado, avisos = hoja_edicion.plan_desde_rendimientos(
        base, "ficha", vivo.id, 0, cuadrillas={"OBRA-04": "2"}, paralelas=["OBRA-03"], unidad="dia"
    )
    # 4, 2, 4 en paralelo con OBRA-02 (fin 8), 210 ÷ 24 = 8,75 → 9 (fin 17), 23,5 (fin 40,5) y 7:
    # 40,5 + 7 = 47,5 → 48 días
    assert editado.rev == 1 and avisos == []
    assert [e for e, _ in editado.borrador.plan] == _dias(48)
    assert _primer_periodo(editado.borrador.plan, "OBRA-03") == "Dia 5"
    assert list(_fracciones(editado.borrador.plan, "OBRA-04")) == _dias(9, desde=9)


def test_reemplaza_el_plan_que_habia_y_el_mismo_plan_no_sube_el_rev(base):
    vivo = _vivo(plan=(("Dia 1", tuple((c, D(1)) for c in CODIGOS)),))
    editado, _ = hoja_edicion.plan_desde_rendimientos(
        base, "ficha", vivo.id, 0, cuadrillas={}, paralelas=[], unidad="dia"
    )
    assert editado.rev == 1 and len(editado.borrador.plan) == 58
    igual, _ = hoja_edicion.plan_desde_rendimientos(
        base, "ficha", vivo.id, 1, cuadrillas={}, paralelas=[], unidad="dia"
    )
    assert igual.rev == 1


@pytest.mark.parametrize(
    ("cuadrillas", "paralelas", "mensaje"),
    [
        ({"OBRA-04": "1,5"}, [], CUADRILLAS_INVALIDAS),
        ({"OBRA-77": "2"}, [], PARTIDA_AJENA),
        ({}, ["OBRA-77"], PARTIDA_AJENA),
    ],
)
def test_cuadrillas_invalidas_o_partidas_ajenas_no_cambian_el_borrador(
    base, cuadrillas, paralelas, mensaje
):
    vivo = _vivo()
    with pytest.raises(HojaInvalida) as error:
        hoja_edicion.plan_desde_rendimientos(
            base, "ficha", vivo.id, 0, cuadrillas=cuadrillas, paralelas=paralelas, unidad="dia"
        )
    assert str(error.value) == mensaje
    assert hoja_borradores.obtener("ficha", vivo.id).rev == 0
    assert hoja_borradores.obtener("ficha", vivo.id).borrador.plan is None


def test_la_primera_version_sin_plan_guarda_el_de_los_rendimientos(base):
    borrador = hoja.Borrador(fecha=FECHA, moneda="Bs", items_base=ITEMS)
    hoja.crear_primera_version(
        base, Catalogo(base), OBRA, borrador, fuente="Medición en sitio", responsable=ANA
    )
    abierta = hoja.abrir_version(base, Catalogo(base), OBRA, "001")
    plan = abierta.borrador.plan
    assert [e for e, _ in plan] == _dias(58)
    assert _fracciones(plan, "OBRA-01") == dict.fromkeys(_dias(4), D("0.25"))
    presupuesto = abierta.guardada.presupuesto
    assert presupuesto.curva[-1].acumulado == presupuesto.total


# --- la ruta -----------------------------------------------------------------------------------


HOY = date(2026, 11, 2)


@pytest.fixture
def navegador(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, str]]:
    """La instalación con cuentas y la carpeta de la vivienda como caso por defecto; ana entra."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    monkeypatch.setattr(rutas_hoja, "_hoy", lambda: HOY)
    copiar_instalacion(plantilla_con_cuentas(tmp_path / "instalacion"))
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar_catalogo(sesion)
            declarar_moneda_de_la_carpeta(
                sesion, "Bs", responsable=ANA, ahora=datetime(2026, 11, 2, 8, 0)
            )
            proyecto = crear_proyecto(sesion, OBRA, dominio=Dominio.CIVIL)
            declarar_moneda(sesion, proyecto, "Bs", responsable=ANA)
            sesion.commit()
    finally:
        motor.dispose()
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    yield con_cuenta(app, "ana")
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    dependencias.cerrar_motores()


def _borrador_con_la_vivienda(navegador: TestClient, ficha: str, cantidades: dict[str, str]):
    respuesta = navegador.post(
        "/v1/hoja/borradores", json={"proyecto": OBRA, "version": None}, headers=protegida(ficha)
    )
    assert respuesta.status_code == 201, respuesta.text
    id_, rev = respuesta.json()["id"], 0
    for codigo, cantidad in cantidades.items():
        agregada = navegador.post(
            f"/v1/hoja/borradores/{id_}/partidas",
            json={"rev": rev, "codigo": codigo, "cantidad": cantidad, "calculo": "", "nota": ""},
            headers=protegida(ficha),
        )
        assert agregada.status_code == 200, agregada.text
        rev = agregada.json()["rev"]
    return id_, rev


def _rendimientos(navegador: TestClient, ficha: str, id_: str, cuerpo: dict):
    return navegador.post(
        f"/v1/hoja/borradores/{id_}/plan/rendimientos", json=cuerpo, headers=protegida(ficha)
    )


def test_la_ruta_rehace_el_plan_y_devuelve_los_avisos(navegador):
    cliente, ficha = navegador
    cantidades = {"OBRA-01": "18", "OBRA-02": "0", "OBRA-03": "950", "OBRA-04": "210"}
    id_, rev = _borrador_con_la_vivienda(cliente, ficha, cantidades)
    respuesta = _rendimientos(
        cliente,
        ficha,
        id_,
        {"rev": rev, "cuadrillas": {"OBRA-04": "2"}, "paralelas": ["OBRA-03"], "unidad": "dia"},
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    # OBRA-01 de 0 a 4; OBRA-02 con 0; OBRA-03 en paralelo con la anterior que entra al plan
    # (OBRA-01): de 0 a 4; OBRA-04: 210 ÷ 24 = 8,75 → 9, de 4 a 13 → 13 días
    assert cuerpo["rev"] == rev + 1
    assert cuerpo["avisos"] == [CANTIDAD_CERO]
    assert cuerpo["plan"]["hay_plan"] is True
    assert cuerpo["plan"]["etiquetas"] == _dias(13)
    filas = {f["partida"]: f["valores"] for f in cuerpo["plan"]["filas"]}
    assert filas["OBRA-03"]["Dia 1"] == "0,25"
    assert filas["OBRA-02"]["Dia 13"] == "1"  # cantidad 0: al último período, monto 0


def test_la_ruta_en_semanas(navegador):
    cliente, ficha = navegador
    id_, rev = _borrador_con_la_vivienda(cliente, ficha, {"OBRA-01": "18", "OBRA-02": "12"})
    respuesta = _rendimientos(
        cliente, ficha, id_, {"rev": rev, "cuadrillas": {}, "paralelas": [], "unidad": "semana"}
    )
    assert respuesta.status_code == 200, respuesta.text
    # 4 + 2 = 6 días → 2 semanas; OBRA-01 entera en la Semana 1
    assert respuesta.json()["plan"]["etiquetas"] == ["Semana 1", "Semana 2"]
    filas = {f["partida"]: f["valores"] for f in respuesta.json()["plan"]["filas"]}
    assert filas["OBRA-01"] == {"Semana 1": "1", "Semana 2": "0"}


def test_la_ruta_en_meses(navegador):
    # Ola 2 (2026-11-13): «Mes n» también desde la pestaña, no solo en la primera versión
    cliente, ficha = navegador
    id_, rev = _borrador_con_la_vivienda(cliente, ficha, {"OBRA-01": "18", "OBRA-02": "12"})
    respuesta = _rendimientos(
        cliente, ficha, id_, {"rev": rev, "cuadrillas": {}, "paralelas": [], "unidad": "mes"}
    )
    assert respuesta.status_code == 200, respuesta.text
    # 4 + 2 = 6 días hábiles → un mes de 20
    assert respuesta.json()["plan"]["etiquetas"] == ["Mes 1"]


def test_sin_plan_la_vista_trae_las_partidas_para_poner_las_cuadrillas(navegador):
    # Ola 2 (2026-11-13): la salida del 422 de más de 10.000 días pide cuadrillas antes del plan
    cliente, ficha = navegador
    id_, _ = _borrador_con_la_vivienda(cliente, ficha, {"OBRA-04": "210", "OBRA-01": "18"})
    vista = cliente.get(f"/v1/hoja/borradores/{id_}/vistas/plan").json()
    assert vista["hay_plan"] is False and vista["filas"] == []
    assert vista["partidas"] == ["OBRA-04", "OBRA-01"]


def test_en_meses_demasiado_largo_solo_queda_asignar_cuadrillas():
    # 10.020 días hábiles de una partida (45.090 ÷ 4,5) → 501 meses de 20
    lista = duraciones([item("OBRA-01", "45090")], COMPOSICIONES, {})
    with pytest.raises(PlanDemasiadoLargo) as error:
        plan_por_rendimientos(lista, unidad="mes")
    assert str(error.value) == (
        "El plan desde los rendimientos tendría 501 períodos y la matriz admite 500: asigne más "
        "cuadrillas a las partidas largas."
    )


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"rev": 0, "cuadrillas": {}, "paralelas": [], "unidad": "anio"},
        {"rev": "0", "cuadrillas": {}, "paralelas": [], "unidad": "dia"},
        {"rev": 0, "cuadrillas": {"OBRA-01": 2}, "paralelas": [], "unidad": "dia"},
        {"rev": 0, "cuadrillas": {}, "paralelas": [], "unidad": "dia", "otro": "VALOR-CENTINELA"},
    ],
)
def test_la_ruta_rechaza_la_forma_sin_eco(navegador, cuerpo):
    cliente, ficha = navegador
    id_, _ = _borrador_con_la_vivienda(cliente, ficha, {"OBRA-01": "18"})
    respuesta = _rendimientos(cliente, ficha, id_, cuerpo)
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"] == FORMA_RENDIMIENTOS
    assert "VALOR-CENTINELA" not in respuesta.text


def test_la_ruta_con_un_rev_viejo_es_409_y_con_cuadrillas_malas_422(navegador):
    cliente, ficha = navegador
    id_, rev = _borrador_con_la_vivienda(cliente, ficha, {"OBRA-04": "210"})
    viejo = _rendimientos(
        cliente, ficha, id_, {"rev": rev - 1, "cuadrillas": {}, "paralelas": [], "unidad": "dia"}
    )
    assert (viejo.status_code, viejo.json()["detalle"]) == (409, REV_VIEJO)
    malo = _rendimientos(
        cliente,
        ficha,
        id_,
        {"rev": rev, "cuadrillas": {"OBRA-04": "0"}, "paralelas": [], "unidad": "dia"},
    )
    assert (malo.status_code, malo.json()["detalle"]) == (422, CUADRILLAS_INVALIDAS)


# --- la primera versión de una obra larga (prueba de punta a punta del 2026-11-13, D-2) --------
#
# Un presupuesto grande no se podía guardar: el plan por días pasaba de 500 períodos y Guardar
# respondía 422 desde otra pestaña, sin plan todavía para poner cuadrillas. Decisión simulada
# (bitácora 2026-11-13-e2e-precios §1): la primera versión sube de unidad, días → semanas → meses
# de 20 días hábiles, la primera que cabe, y lo dice. Datos FICTICIOS: la vivienda con OBRA-01
# agrandada (como 60.000 m2 a 100 m2/día).

AVISO_SEMANAS = (
    "El plan por días tendría 654 períodos y la matriz admite 500: se armó por semanas "
    "(131 períodos). Puede rehacerlo con cuadrillas en «Plan y equilibrio»."
)


def test_el_plan_que_cabe_de_la_vivienda_es_el_de_dias_sin_aviso():
    plan, unidad, aviso = plan_que_cabe(ITEMS, COMPOSICIONES)
    assert (unidad, aviso) == ("dia", "")
    assert plan == plan_del_borrador(ITEMS, COMPOSICIONES)[0]


def test_con_600_dias_de_una_partida_el_plan_que_cabe_va_por_semanas_y_lo_dice():
    # OBRA-01: 2.700 ÷ 4,5 = 600 días; con las otras cinco (2 + 4 + 17,5 + 23,5 + 7 = 54) son
    # 654 días → 654 períodos > 500; en semanas 654 ÷ 5 = 130,8 → 131
    items = [item("OBRA-01", "2700"), *ITEMS[1:]]
    plan, unidad, aviso = plan_que_cabe(items, COMPOSICIONES)
    assert unidad == "semana"
    assert [e for e, _ in plan] == [f"Semana {n}" for n in range(1, 132)]
    assert aviso == AVISO_SEMANAS


def test_si_tampoco_cabe_en_semanas_va_por_meses_de_20_dias_habiles():
    # OBRA-01: 13.500 ÷ 4,5 = 3.000 días; con las otras 54, 3.054 → 3.054 ÷ 5 = 610,8 → 611
    # semanas > 500; en meses de 20 días 3.054 ÷ 20 = 152,7 → 153
    items = [item("OBRA-01", "13500"), *ITEMS[1:]]
    plan, unidad, aviso = plan_que_cabe(items, COMPOSICIONES)
    assert unidad == "mes"
    assert [e for e, _ in plan] == [f"Mes {n}" for n in range(1, 154)]
    assert aviso == (
        "El plan por días tendría 3.054 períodos y la matriz admite 500: se armó por meses de 20 "
        "días hábiles (153 períodos). Puede rehacerlo con cuadrillas en «Plan y equilibrio»."
    )
    # cada partida suma exactamente 1
    for codigo in CODIGOS:
        assert sum(_fracciones(plan, codigo).values()) == 1


def test_si_ni_en_meses_cabe_lo_dice_con_la_salida():
    # OBRA-01: 45.004,5 ÷ 4,5 = 10.001 días; con las otras 54, 10.055 ÷ 20 = 502,75 → 503 meses
    with pytest.raises(PlanDemasiadoLargo) as error:
        plan_que_cabe([item("OBRA-01", "45004.5"), *ITEMS[1:]], COMPOSICIONES)
    assert str(error.value) == (
        "El plan desde los rendimientos tendría 503 meses y la matriz admite 500 períodos: en "
        "«Plan y equilibrio» asigne más cuadrillas a las partidas largas, haga el plan desde los "
        "rendimientos por meses y vuelva a guardar."
    )


def test_la_primera_version_de_una_obra_de_600_dias_se_guarda_por_semanas_y_lo_dice(base):
    borrador = hoja.Borrador(
        fecha=FECHA, moneda="Bs", items_base=(item("OBRA-01", "2700"), *ITEMS[1:])
    )
    vivo = hoja_borradores.crear("ficha", "caso", OBRA, None, borrador, None)
    guardado = hoja_guardado.guardar(
        base, "ficha", vivo.id, 0, fuente="Medición en sitio", responsable=ANA
    )
    assert guardado.codigo == "001" and guardado.primera
    assert guardado.mensaje.endswith(AVISO_SEMANAS)
    abierta = hoja.abrir_version(base, Catalogo(base), OBRA, "001")
    assert [e for e, _ in abierta.borrador.plan] == [f"Semana {n}" for n in range(1, 132)]
    presupuesto = abierta.guardada.presupuesto
    assert presupuesto.curva[-1].acumulado == presupuesto.total


def test_la_primera_version_de_la_vivienda_por_el_servicio_sigue_por_dias_sin_aviso(base):
    borrador = hoja.Borrador(fecha=FECHA, moneda="Bs", items_base=ITEMS)
    vivo = hoja_borradores.crear("ficha", "caso", OBRA, None, borrador, None)
    guardado = hoja_guardado.guardar(
        base, "ficha", vivo.id, 0, fuente="Medición en sitio", responsable=ANA
    )
    assert guardado.mensaje.endswith(
        "Quedó registrada su creación, con su fuente y su responsable."
    )
    abierta = hoja.abrir_version(base, Catalogo(base), OBRA, "001")
    assert [e for e, _ in abierta.borrador.plan] == _dias(58)
