"""SF-E6 (RF-53, DA-SF-7): cada version congela las composiciones, los rendimientos y el plan.

Hoy `cargar_presupuesto` reconstruye cada APU desde la composicion del catalogo y exige que el PU
cuadre con el renglon guardado: editar un APU en el catalogo rompe la recarga de toda version
anterior. Con la instantanea, la recarga, la revaloracion (UC-02) y los escenarios toman la
composicion de la version y solo las versiones anteriores a SF-E6 usan el catalogo.

Oraculos independientes: la linea base de `tests/fixtures/apu_linea_base.py` (APU, lineas y
rendimientos tal como se escribieron), las constantes de UC-02 calculadas a mano
(`tests/fixtures/actualizacion_uc02.py`) y consultas propias a las tablas de la instantanea.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select

from core import models
from core.budget import (
    actualizar_precios,
    cargar_elaboracion,
    cargar_presupuesto,
    elaborar,
    guardar_presupuesto,
    importar_presupuesto,
    plan_secuencial,
)
from core.budget.instantanea import (
    asegurar_instantanea,
    composiciones_de_presupuesto,
    composiciones_de_version,
    plan_de_version,
    tiene_instantanea,
)
from core.budget.persistencia import _buscar
from core.catalog import (
    Catalogo,
    abrir_sesion,
    crear_esquema,
    crear_lista_desde_archivo,
    crear_motor,
)
from core.contracts import Dominio
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import INCREMENTO_TOTAL
from tests.fixtures.computo_auditado import items_auditados
from tests.fixtures.presupuesto_tabular import escribir_presupuesto_tabular

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv"
FECHA_NUEVA = date(2026, 6, 1)

CODIGO = linea_base.CODIGO_PRESUPUESTO
CODIGOS = list(linea_base.CODIGOS_LINEA_BASE)
CONCRETO = linea_base.APU_CONCRETO
TABLAS_DE_LA_INSTANTANEA = (
    models.PlanVersion,
    models.LineaComposicionVersion,
    models.ComposicionVersion,
)


def _elaborar(sesion, codigo=CODIGO, plan=plan_secuencial):
    catalogo = Catalogo(sesion)
    return elaborar(
        items_auditados(),
        catalogo.composiciones(CODIGOS, fecha=linea_base.FECHA_LINEA_BASE),
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=codigo,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan,
    )


def _guardar(sesion, proyecto, resultado, **opciones):
    return guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=Catalogo(sesion).lista_vigente(linea_base.FECHA_LINEA_BASE),
        parametros=linea_base.PARAMETROS_LINEA_BASE,
        pendientes=resultado.pendientes,
        **opciones,
    )


@pytest.fixture
def v001(sesion):
    """La version 001 de la linea base guardada (con instantanea) y confirmada."""
    resultado = _elaborar(sesion)
    _guardar(sesion, sembrar(sesion), resultado)
    sesion.commit()
    return resultado


def _modelo(sesion, codigo=CODIGO) -> models.Presupuesto:
    return _buscar(sesion, NOMBRE_PROYECTO, codigo)


def _borrar_instantanea(sesion, codigo=CODIGO) -> None:
    """Deja la version como la dejaba SF anterior a SF-E6: sin filas de instantanea."""
    modelo = _modelo(sesion, codigo)
    comps = select(models.ComposicionVersion.id).where(
        models.ComposicionVersion.presupuesto_id == modelo.id
    )
    sesion.execute(
        delete(models.LineaComposicionVersion).where(
            models.LineaComposicionVersion.composicion_id.in_(comps)
        )
    )
    sesion.execute(
        delete(models.ComposicionVersion).where(
            models.ComposicionVersion.presupuesto_id == modelo.id
        )
    )
    sesion.execute(delete(models.PlanVersion).where(models.PlanVersion.presupuesto_id == modelo.id))
    sesion.commit()
    sesion.expire_all()


def _editar_concreto_en_el_catalogo(sesion, cantidad_cemento: str = "9") -> None:
    """UC-11: un APU del catalogo cambia (mas cemento y mas rendimiento)."""
    catalogo = Catalogo(sesion)
    materiales = tuple(
        replace(m, cantidad=Decimal(cantidad_cemento)) if m.descripcion == "Cemento Portland" else m
        for m in CONCRETO.materiales
    )
    catalogo.reemplazar_composicion(
        replace(CONCRETO, materiales=materiales, rendimiento=CONCRETO.rendimiento + 1),
        catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
        Dominio.CIVIL,
        linea_base.FECHA_LINEA_BASE,
        condiciones="cuadrilla ampliada; mas cemento por m3",
    )
    sesion.commit()
    sesion.expire_all()


def _contar(sesion, modelo_orm, **filtros) -> int:
    consulta = select(func.count()).select_from(modelo_orm)
    for columna, valor in filtros.items():
        consulta = consulta.where(getattr(modelo_orm, columna) == valor)
    return sesion.scalar(consulta)


# ---------------------------------------------------------------------------------------------
# Lo que se congela
# ---------------------------------------------------------------------------------------------


def test_guardar_congela_las_composiciones_tal_como_se_escribieron(sesion, v001):
    modelo = _modelo(sesion)

    congeladas = composiciones_de_version(sesion, modelo)

    assert congeladas == {apu.codigo_partida: apu for apu in linea_base.APUS_LINEA_BASE}
    assert tiene_instantanea(sesion, modelo)


def test_cada_partida_distinta_guarda_una_composicion_y_su_rendimiento(sesion, v001):
    modelo = _modelo(sesion)
    filas = sesion.scalars(
        select(models.ComposicionVersion)
        .where(models.ComposicionVersion.presupuesto_id == modelo.id)
        .order_by(models.ComposicionVersion.codigo_partida)
    ).all()

    assert [f.codigo_partida for f in filas] == sorted(CODIGOS)
    esperados = {apu.codigo_partida: apu.rendimiento for apu in linea_base.APUS_LINEA_BASE}
    assert {f.codigo_partida: f.rendimiento for f in filas} == esperados
    lineas = sum(
        len(a.materiales) + len(a.equipos) + len(a.mano_obra) for a in linea_base.APUS_LINEA_BASE
    )
    assert _contar(sesion, models.LineaComposicionVersion) == lineas


def test_cada_linea_apunta_a_un_insumo_cuyo_precio_en_la_lista_es_el_de_la_linea(sesion, v001):
    modelo = _modelo(sesion)
    lineas = sesion.scalars(
        select(models.LineaComposicionVersion)
        .join(models.ComposicionVersion)
        .where(models.ComposicionVersion.presupuesto_id == modelo.id)
    ).all()
    precios = {p.insumo_id: p.precio for p in modelo.lista_precios.precios}

    assert lineas
    for linea in lineas:
        assert linea.insumo_id is not None, linea.descripcion
        assert precios[linea.insumo_id] == linea.precio
        assert linea.insumo.descripcion == linea.descripcion


def test_recargar_no_escribe_nada_en_la_instantanea(sesion, v001):
    antes = [_contar(sesion, tabla) for tabla in TABLAS_DE_LA_INSTANTANEA]

    for _ in range(2):
        cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))
        sesion.commit()

    assert [_contar(sesion, tabla) for tabla in TABLAS_DE_LA_INSTANTANEA] == antes


# ---------------------------------------------------------------------------------------------
# La prueba clave: editar el catalogo no rompe la version anterior
# ---------------------------------------------------------------------------------------------


def test_editar_un_apu_del_catalogo_no_rompe_la_recarga_de_la_version_anterior(sesion, v001):
    _editar_concreto_en_el_catalogo(sesion)

    recargado = cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))

    assert recargado.total == linea_base.TOTAL_EXACTO_LINEA_BASE
    assert recargado.partidas == v001.presupuesto.partidas
    concreto = next(p for p in recargado.partidas if p.item.codigo_partida == "LB-04-CON")
    assert concreto.apu == CONCRETO


def test_un_rendimiento_nuevo_en_el_catalogo_tampoco_cambia_la_recarga(sesion, v001):
    _editar_concreto_en_el_catalogo(sesion, cantidad_cemento="7.5")  # solo el rendimiento cambia

    recargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))

    assert recargado.presupuesto.total == linea_base.TOTAL_EXACTO_LINEA_BASE
    assert recargado.informe.hallazgos == v001.informe.hallazgos


def test_la_version_sin_instantanea_sigue_usando_el_catalogo_y_denuncia_el_desligue(sesion, v001):
    _borrar_instantanea(sesion)
    assert not tiene_instantanea(sesion, _modelo(sesion))
    # catalogo intacto: la ruta anterior a SF-E6 sigue funcionando
    assert cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion)).total == (
        linea_base.TOTAL_EXACTO_LINEA_BASE
    )

    _editar_concreto_en_el_catalogo(sesion)

    with pytest.raises(ValueError, match="no se reconstruye"):
        cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))


# ---------------------------------------------------------------------------------------------
# UC-02 y escenarios usan la instantanea
# ---------------------------------------------------------------------------------------------


def test_la_revaloracion_usa_las_lineas_congeladas_y_no_las_del_catalogo(sesion, v001):
    _editar_concreto_en_el_catalogo(sesion)
    lista = crear_lista_desde_archivo(
        sesion,
        MUESTRA,
        nombre="Lista de precios 01/06/2026",
        moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_NUEVA,
        origen=MUESTRA.name,
    ).lista

    nuevo, comparativo = actualizar_precios(sesion, NOMBRE_PROYECTO, CODIGO, lista, "002")

    assert comparativo.total_anterior == linea_base.TOTAL_EXACTO_LINEA_BASE
    assert nuevo.presupuesto.total - comparativo.total_anterior == INCREMENTO_TOTAL
    congelada = composiciones_de_version(sesion, _modelo(sesion, "002"))
    cemento = next(
        m for m in congelada["LB-04-CON"].materiales if m.descripcion == "Cemento Portland"
    )
    assert cemento.precio == Decimal("18")
    assert cemento.cantidad == Decimal("7.5")  # la cantidad de la version, no la editada (9)


def test_la_version_revalorada_congela_sus_propias_lineas_con_los_precios_nuevos(sesion, v001):
    lista = crear_lista_desde_archivo(
        sesion,
        MUESTRA,
        nombre="Lista de precios 01/06/2026",
        moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_NUEVA,
        origen=MUESTRA.name,
    ).lista
    actualizar_precios(sesion, NOMBRE_PROYECTO, CODIGO, lista, "002")

    anterior = composiciones_de_version(sesion, _modelo(sesion, CODIGO))
    nueva = composiciones_de_version(sesion, _modelo(sesion, "002"))

    assert anterior["LB-04-CON"] == CONCRETO
    assert nueva["LB-04-CON"] != CONCRETO
    assert nueva["LB-01-EXC"] == linea_base.APU_EXCAVACION  # lo que no cambio de precio
    assert nueva["LB-04-CON"].rendimiento == CONCRETO.rendimiento


def test_composiciones_de_presupuesto_da_la_instantanea_y_solo_si_falta_el_catalogo(sesion, v001):
    _editar_concreto_en_el_catalogo(sesion)
    catalogo = Catalogo(sesion)

    con = composiciones_de_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO, catalogo)
    assert con["LB-04-CON"] == CONCRETO

    _borrar_instantanea(sesion)
    sin = composiciones_de_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO, catalogo)
    assert sin["LB-04-CON"] != CONCRETO  # sin instantanea: el catalogo editado
    assert sin["LB-01-EXC"] == linea_base.APU_EXCAVACION


# ---------------------------------------------------------------------------------------------
# Bases anteriores y UC-15e
# ---------------------------------------------------------------------------------------------


def test_una_base_con_el_esquema_anterior_abre_y_gana_las_tablas(tmp_path):
    url = f"sqlite:///{(tmp_path / 'vieja.db').as_posix()}"
    motor = crear_motor(url)
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        _guardar(sesion, sembrar(sesion), _elaborar(sesion))
        sesion.commit()
    for tabla in TABLAS_DE_LA_INSTANTANEA:  # la base como la dejo SF anterior a SF-E6
        tabla.__table__.drop(motor)
    motor.dispose()

    motor = crear_motor(url)
    crear_esquema(motor)  # abre: las tablas aditivas se crean vacias
    with abrir_sesion(motor) as sesion:
        modelo = _modelo(sesion)
        assert not tiene_instantanea(sesion, modelo)
        assert cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion)).total == (
            linea_base.TOTAL_EXACTO_LINEA_BASE
        )
        resultado = asegurar_instantanea(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))
        sesion.commit()
        assert sorted(resultado.creadas) == sorted(CODIGOS)
        assert tiene_instantanea(sesion, modelo)
    motor.dispose()


def test_asegurar_instantanea_crea_desde_el_catalogo_y_es_idempotente(sesion, v001):
    _borrar_instantanea(sesion)
    catalogo = Catalogo(sesion)

    primera = asegurar_instantanea(sesion, NOMBRE_PROYECTO, CODIGO, catalogo)
    segunda = asegurar_instantanea(sesion, NOMBRE_PROYECTO, CODIGO, catalogo)

    assert sorted(primera.creadas) == sorted(CODIGOS)
    assert primera.sin_composicion == ()
    assert segunda.creadas == ()
    assert composiciones_de_version(sesion, _modelo(sesion)) == {
        apu.codigo_partida: apu for apu in linea_base.APUS_LINEA_BASE
    }
    assert _contar(sesion, models.ComposicionVersion) == len(CODIGOS)


def test_asegurar_instantanea_deja_en_solo_lectura_la_partida_que_el_catalogo_ya_no_reproduce(
    sesion, v001
):
    _borrar_instantanea(sesion)
    _editar_concreto_en_el_catalogo(sesion)

    resultado = asegurar_instantanea(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))

    assert resultado.sin_composicion == ("LB-04-CON",)
    assert sorted(resultado.creadas) == sorted(set(CODIGOS) - {"LB-04-CON"})
    assert "LB-04-CON" not in composiciones_de_version(sesion, _modelo(sesion))


def test_el_presupuesto_importado_de_un_tercero_tambien_congela_su_instantanea(sesion, tmp_path):
    from core.budget import crear_proyecto

    proyecto = crear_proyecto(sesion, "Tercero", dominio=Dominio.CIVIL)
    importar_presupuesto(sesion, escribir_presupuesto_tabular(tmp_path), proyecto)
    sesion.commit()

    modelo = _buscar(sesion, "Tercero", CODIGO)
    assert tiene_instantanea(sesion, modelo)
    assert set(composiciones_de_version(sesion, modelo)) == {
        "TER-" + c.removeprefix("LB-") for c in CODIGOS
    }


# ---------------------------------------------------------------------------------------------
# El plan
# ---------------------------------------------------------------------------------------------


def test_el_plan_secuencial_se_conserva_exacto(sesion, v001):
    esperado = [
        (etiqueta, tuple(reparto)) for etiqueta, reparto in plan_secuencial(v001.presupuesto)
    ]

    assert plan_de_version(sesion, _modelo(sesion)) == esperado


def test_un_plan_con_una_partida_repartida_en_dos_periodos_se_guarda_si_se_da(sesion):
    resultado = _elaborar(sesion, plan=None)
    codigos = list(dict.fromkeys(p.item.codigo_partida for p in resultado.presupuesto.partidas))
    mitad = Decimal("0.5")
    plan = [
        ("Dia 1", ((codigos[0], Decimal(1)), (codigos[1], mitad))),
        ("Dia 2", ((codigos[1], mitad), *((c, Decimal(1)) for c in codigos[2:]))),
    ]
    con_plan = _elaborar(sesion, plan=plan)
    _guardar(sesion, sembrar(sesion), con_plan, plan=plan)
    sesion.commit()

    assert plan_de_version(sesion, _modelo(sesion)) == [
        (etiqueta, tuple(reparto)) for etiqueta, reparto in plan
    ]


def test_sin_plan_dado_y_con_una_partida_en_dos_periodos_no_se_inventa_un_plan(sesion):
    resultado = _elaborar(sesion, plan=None)
    codigos = list(dict.fromkeys(p.item.codigo_partida for p in resultado.presupuesto.partidas))
    mitad = Decimal("0.5")
    plan = [
        ("Dia 1", ((codigos[0], mitad),)),
        ("Dia 2", ((codigos[0], mitad), *((c, Decimal(1)) for c in codigos[1:]))),
    ]
    con_plan = _elaborar(sesion, plan=plan)
    _guardar(sesion, sembrar(sesion), con_plan)  # sin plan=: no se puede inferir
    sesion.commit()

    assert plan_de_version(sesion, _modelo(sesion)) is None


def test_sin_curva_no_hay_plan(sesion):
    _guardar(sesion, sembrar(sesion), _elaborar(sesion, plan=None))
    sesion.commit()

    assert plan_de_version(sesion, _modelo(sesion)) is None
