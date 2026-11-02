"""SF-E7 (RF-56, DA-SF-9, spec 9.6): origen de precios y cotizaciones con alcance de proyecto.

Una cotizacion crea una lista del proyecto (copia de la base con ese insumo cambiado) que la version
nueva referencia explicitamente; no cambia ningun otro proyecto, conserva el plan y la curva, y una
carga global posterior (UC-02) no la pisa hasta que se retire. `lista_vigente` no resuelve listas de
proyecto.

Oraculos independientes: el APU del concreto de la linea base calculado a mano (7,5 sacos de cemento
y 0,45 m3 de arena por m3; administracion y utilidad en cascada, 1,15 x 1,10) y las constantes de
UC-02 de `tests/fixtures/actualizacion_uc02.py`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from core import models
from core.budget import actualizar_precios, cargar_elaboracion, crear_proyecto
from core.budget.cotizacion import cotizaciones_de_version, cotizar_insumo, retirar_cotizacion
from core.budget.edicion import registros_de_version
from core.budget.instantanea import composiciones_de_version, plan_de_version
from core.budget.persistencia import _buscar
from core.catalog import (
    Catalogo,
    abrir_sesion,
    crear_esquema,
    crear_lista_desde_archivo,
    crear_motor,
)
from core.catalog.origen import fijar_referencia, origen_de_precios, registrar_origen_lista
from core.contracts import Dominio
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import INCREMENTO_TOTAL
from tests.fixtures.computo_auditado import items_auditados
from tests.fixtures.versiones import elaborar_001, guardar_001

D = Decimal
RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv"
CODIGO = linea_base.CODIGO_PRESUPUESTO
CONCRETO = linea_base.APU_CONCRETO.codigo_partida
CANTIDAD_CONCRETO = sum(
    (i.cantidad for i in items_auditados() if i.codigo_partida == CONCRETO), D(0)
)
PROVEEDOR = "Cementos Andinos C.A."
NUMERO = "COT-0457"
FECHA = date(2026, 10, 1)
RESPONSABLE = "Ing. Prueba"
AHORA = datetime(2026, 10, 5, 11, 0, 0)

#: Delta del PU del concreto por cada USD que sube el saco de cemento:
#: 7,5 sacos x 1,15 x 1,10 (administracion y utilidad en cascada).
POR_USD_DE_CEMENTO = D("7.5") * D("1.15") * D("1.10")
#: La arena de la muestra de UC-02 (30 -> 33) pesa 0,45 m3 por m3 de concreto.
POR_USD_DE_ARENA = D("0.45") * D("1.15") * D("1.10")


@pytest.fixture
def v001(sesion):
    proyecto = sembrar(sesion)
    guardar_001(sesion, proyecto, elaborar_001(sesion))
    sesion.commit()
    return proyecto


@pytest.fixture
def cemento(sesion, v001):
    return sesion.scalars(
        select(models.Insumo).where(models.Insumo.descripcion == "Cemento Portland")
    ).one()


@pytest.fixture
def arena(sesion, v001):
    return sesion.scalars(
        select(models.Insumo).where(models.Insumo.descripcion == "Arena lavada")
    ).one()


def _modelo(sesion, codigo):
    return _buscar(sesion, NOMBRE_PROYECTO, codigo)


def _pu(sesion, codigo, partida=CONCRETO) -> Decimal:
    cargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, codigo, Catalogo(sesion))
    return next(
        p.resultado.precio_unitario
        for p in cargado.presupuesto.partidas
        if p.item.codigo_partida == partida
    )


def _total(sesion, codigo) -> Decimal:
    return cargar_elaboracion(sesion, NOMBRE_PROYECTO, codigo, Catalogo(sesion)).presupuesto.total


def _cotizar(sesion, insumo, precio, codigo_nuevo="002", desde=CODIGO, **cambios):
    argumentos = dict(
        insumo=insumo,
        precio=D(precio),
        proveedor=PROVEEDOR,
        numero=NUMERO,
        fecha=FECHA,
        responsable=RESPONSABLE,
        ahora=AHORA,
    )
    argumentos.update(cambios)
    return cotizar_insumo(
        sesion, NOMBRE_PROYECTO, desde, codigo_nuevo, Catalogo(sesion), **argumentos
    )


def _lista_uc02(sesion):
    return crear_lista_desde_archivo(
        sesion,
        MUESTRA,
        nombre="Lista de precios 01/06/2026",
        moneda=linea_base.MONEDA,
        fecha_vigencia=date(2026, 6, 1),
        origen=MUESTRA.name,
    ).lista


def _cerca(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= D("1e-12")


def _contar(sesion, tabla) -> int:
    return sesion.scalar(select(func.count()).select_from(tabla))


# ---------------------------------------------------------------------------------------------
# La cotizacion cambia solo ese insumo en ese proyecto
# ---------------------------------------------------------------------------------------------


def test_la_cotizacion_cambia_solo_ese_insumo_y_solo_en_ese_proyecto(sesion, v001, cemento):
    otro = crear_proyecto(sesion, "Otro", dominio=Dominio.CIVIL)
    guardar_001(sesion, otro, elaborar_001(sesion))
    sesion.commit()
    antes_otro = cargar_elaboracion(sesion, "Otro", CODIGO, Catalogo(sesion)).presupuesto

    nueva = _cotizar(sesion, cemento, "20")
    sesion.commit()

    assert nueva.codigo == "002"
    assert _cerca(_pu(sesion, "002") - _pu(sesion, CODIGO), 5 * POR_USD_DE_CEMENTO)
    assert _cerca(
        _total(sesion, "002") - _total(sesion, CODIGO), CANTIDAD_CONCRETO * 5 * POR_USD_DE_CEMENTO
    )
    # solo el cemento cambio, en solo una partida
    nuevas = composiciones_de_version(sesion, nueva)
    viejas = composiciones_de_version(sesion, _modelo(sesion, CODIGO))
    cambiadas = {
        (codigo, a.descripcion)
        for codigo in viejas
        for a, b in zip(viejas[codigo].materiales, nuevas[codigo].materiales, strict=True)
        if a != b
    }
    assert cambiadas == {(CONCRETO, "Cemento Portland")}
    assert viejas[CONCRETO] == linea_base.APU_CONCRETO  # la version anterior, intacta
    # el otro proyecto sobre la misma lista no cambia
    despues_otro = cargar_elaboracion(sesion, "Otro", CODIGO, Catalogo(sesion)).presupuesto
    assert despues_otro.total == antes_otro.total


def test_la_version_referencia_su_lista_de_proyecto_y_la_cotizacion_queda_registrada(
    sesion, v001, cemento
):
    base = _modelo(sesion, CODIGO).lista_precios

    nueva = _cotizar(sesion, cemento, "20")
    sesion.commit()

    lista = nueva.lista_precios
    assert lista.id != base.id
    origen = sesion.get(models.ListaPreciosOrigen, lista.id)
    assert (origen.alcance, origen.proyecto_id, origen.lista_base_id) == (
        models.ALCANCE_PROYECTO,
        nueva.proyecto_id,
        base.id,
    )
    (cotizacion,) = cotizaciones_de_version(sesion, nueva)
    assert (cotizacion.insumo_id, cotizacion.precio, cotizacion.precio_base) == (
        cemento.id,
        D("20"),
        D("15"),
    )
    assert (cotizacion.proveedor, cotizacion.numero, cotizacion.fecha) == (PROVEEDOR, NUMERO, FECHA)
    # la lista base no se toca: sigue valiendo 15 y la del proyecto, 20
    precios_base = {p.insumo_id: p.precio for p in base.precios}
    precios_proyecto = {p.insumo_id: p.precio for p in lista.precios}
    assert precios_base[cemento.id] == D("15") and precios_proyecto[cemento.id] == D("20")
    assert {k: v for k, v in precios_base.items() if k != cemento.id} == {
        k: v for k, v in precios_proyecto.items() if k != cemento.id
    }


def test_lista_vigente_no_resuelve_las_listas_de_proyecto(sesion, v001, cemento):
    nueva = _cotizar(sesion, cemento, "20")
    # aunque la lista del proyecto fuera la de vigencia mas reciente
    nueva.lista_precios.fecha_vigencia = date(2030, 1, 1)
    sesion.commit()

    vigente = Catalogo(sesion).lista_vigente(date(2031, 1, 1))

    assert vigente.id != nueva.lista_precios.id
    assert sesion.get(models.ListaPreciosOrigen, vigente.id) is None


def test_la_version_resultante_conserva_el_plan_y_la_curva(sesion, v001, cemento):
    antes = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))

    nueva = _cotizar(sesion, cemento, "20")
    sesion.commit()

    despues = cargar_elaboracion(sesion, NOMBRE_PROYECTO, "002", Catalogo(sesion))
    assert [p.periodo for p in despues.presupuesto.curva] == [
        p.periodo for p in antes.presupuesto.curva
    ]
    assert despues.presupuesto.total_curva == despues.presupuesto.total  # R2 cierra
    assert despues.presupuesto.curva[-1].acumulado != antes.presupuesto.curva[-1].acumulado
    assert [h.regla for h in despues.informe.hallazgos] == [
        h.regla for h in antes.informe.hallazgos
    ]
    assert plan_de_version(sesion, nueva) == plan_de_version(sesion, _modelo(sesion, CODIGO))


def test_version_de_origen_y_registro_de_cambio_de_la_cotizacion(sesion, v001, cemento):
    nueva = _cotizar(sesion, cemento, "20")
    sesion.commit()

    origen = sesion.get(models.VersionOrigen, nueva.id)
    assert (origen.origen_id, origen.motivo) == (_modelo(sesion, CODIGO).id, "cotizacion")
    (registro,) = registros_de_version(sesion, nueva)
    assert (registro.objeto, registro.clave, registro.campo) == (
        "precio",
        cemento.codigo,
        "cotizacion",
    )
    assert (registro.valor_anterior, registro.valor_nuevo) == ("15", "20")
    assert PROVEEDOR in registro.fuente and NUMERO in registro.fuente
    assert (registro.responsable, registro.fecha_hora) == (RESPONSABLE, AHORA)


def test_cotizaciones_sucesivas_se_acumulan_y_la_misma_insumo_se_reemplaza(
    sesion, v001, cemento, arena
):
    _cotizar(sesion, cemento, "20")
    _cotizar(sesion, arena, "40", codigo_nuevo="003", desde="002", numero="COT-0500")
    _cotizar(sesion, cemento, "19", codigo_nuevo="004", desde="003", numero="COT-0600")
    sesion.commit()

    activas = {c.insumo_id: c for c in cotizaciones_de_version(sesion, _modelo(sesion, "004"))}

    assert set(activas) == {cemento.id, arena.id}
    assert (activas[cemento.id].precio, activas[cemento.id].numero) == (D("19"), "COT-0600")
    assert (activas[arena.id].precio, activas[arena.id].numero) == (D("40"), "COT-0500")
    assert _cerca(
        _pu(sesion, "004") - _pu(sesion, CODIGO), 4 * POR_USD_DE_CEMENTO + 10 * POR_USD_DE_ARENA
    )
    # cada version conserva sus propias cotizaciones
    assert {c.insumo_id for c in cotizaciones_de_version(sesion, _modelo(sesion, "002"))} == {
        cemento.id
    }


# ---------------------------------------------------------------------------------------------
# UC-02 posterior no la pisa; retirarla
# ---------------------------------------------------------------------------------------------


def test_una_carga_global_posterior_por_uc02_no_pisa_la_cotizacion(sesion, v001, cemento):
    _cotizar(sesion, cemento, "20")
    sesion.commit()
    lista = _lista_uc02(sesion)  # cemento 15 -> 18 y arena 30 -> 33, para todos

    nuevo, _ = actualizar_precios(sesion, NOMBRE_PROYECTO, "002", lista, "003")
    sesion.commit()

    # cemento sigue en 20 (cotizacion); la arena toma 33 de la lista nueva
    assert _cerca(
        _pu(sesion, "003") - _pu(sesion, CODIGO), 5 * POR_USD_DE_CEMENTO + 3 * POR_USD_DE_ARENA
    )
    modelo = _modelo(sesion, "003")
    (cotizacion,) = cotizaciones_de_version(sesion, modelo)
    assert (cotizacion.insumo_id, cotizacion.precio) == (cemento.id, D("20"))
    origen = sesion.get(models.ListaPreciosOrigen, modelo.lista_precios_id)
    assert (origen.alcance, origen.lista_base_id) == (models.ALCANCE_PROYECTO, lista.id)
    # la lista de proyecto anterior no cambia
    anterior = {p.insumo_id: p.precio for p in _modelo(sesion, "002").lista_precios.precios}
    assert anterior[cemento.id] == D("20")
    # el historial compara listas base: la cotizacion no aparece como cambio de precio
    cambios = sesion.scalars(select(models.CambioPrecio)).all()
    assert {c.insumo.descripcion for c in cambios} == {"Cemento Portland", "Arena lavada"}
    assert all(c.precio_anterior in (D("15"), D("30")) for c in cambios)
    assert nuevo.presupuesto.total == _total(sesion, "003")
    origen_version = sesion.get(models.VersionOrigen, modelo.id)
    assert (origen_version.motivo, origen_version.origen_id) == (
        "revaloracion",
        _modelo(sesion, "002").id,
    )


def test_retirar_la_cotizacion_vuelve_al_precio_de_la_lista_base_con_su_registro(
    sesion, v001, cemento
):
    _cotizar(sesion, cemento, "20")
    sesion.commit()
    lista = _lista_uc02(sesion)
    actualizar_precios(sesion, NOMBRE_PROYECTO, "002", lista, "003")
    sesion.commit()

    nueva = retirar_cotizacion(
        sesion,
        NOMBRE_PROYECTO,
        "003",
        "004",
        Catalogo(sesion),
        insumo=cemento,
        fuente="el proveedor no mantuvo el precio",
        responsable=RESPONSABLE,
        ahora=AHORA,
    )
    sesion.commit()

    # sin cotizaciones la version usa la lista base (global) y suma lo mismo que UC-02 sola
    assert nueva.lista_precios_id == lista.id
    assert cotizaciones_de_version(sesion, nueva) == []
    assert _cerca(_total(sesion, "004") - _total(sesion, CODIGO), INCREMENTO_TOTAL)
    (registro,) = registros_de_version(sesion, nueva)
    assert (registro.objeto, registro.clave, registro.campo) == (
        "precio",
        cemento.codigo,
        "cotizacion",
    )
    assert (registro.valor_anterior, registro.valor_nuevo) == ("20", "18")
    assert (registro.fuente, registro.responsable) == (
        "el proveedor no mantuvo el precio",
        RESPONSABLE,
    )
    origen = sesion.get(models.VersionOrigen, nueva.id)
    assert (origen.motivo, origen.origen_id) == ("cotizacion", _modelo(sesion, "003").id)


def test_retirar_una_de_dos_cotizaciones_deja_la_otra(sesion, v001, cemento, arena):
    _cotizar(sesion, cemento, "20")
    _cotizar(sesion, arena, "40", codigo_nuevo="003", desde="002", numero="COT-0500")
    sesion.commit()

    nueva = retirar_cotizacion(
        sesion,
        NOMBRE_PROYECTO,
        "003",
        "004",
        Catalogo(sesion),
        insumo=cemento,
        fuente="retirada",
        responsable=RESPONSABLE,
    )

    assert [c.insumo_id for c in cotizaciones_de_version(sesion, nueva)] == [arena.id]
    assert _cerca(_pu(sesion, "004") - _pu(sesion, CODIGO), 10 * POR_USD_DE_ARENA)


# ---------------------------------------------------------------------------------------------
# Rechazos: no dejan filas
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"proveedor": " "}, "proveedor"),
        ({"numero": ""}, "numero"),
        ({"responsable": ""}, "responsable"),
        ({"precio": D("-1")}, "precio"),
        ({"precio": D("15")}, "ya vale"),
    ],
)
def test_una_cotizacion_incompleta_o_sin_efecto_se_rechaza_sin_dejar_filas(
    sesion, v001, cemento, cambios, mensaje
):
    listas = _contar(sesion, models.ListaPrecios)

    with pytest.raises(ValueError, match=mensaje):
        _cotizar(sesion, cemento, cambios.pop("precio", "20"), **cambios)

    assert _contar(sesion, models.Presupuesto) == 1
    assert _contar(sesion, models.ListaPrecios) == listas
    assert _contar(sesion, models.Cotizacion) == 0


def test_cotizar_un_insumo_que_la_version_no_usa_se_rechaza(sesion, v001):
    sesion.add(models.Insumo(codigo="MAT-999", tipo="material", descripcion="Ajeno", unidad="kg"))
    sesion.commit()
    ajeno = sesion.scalars(select(models.Insumo).where(models.Insumo.codigo == "MAT-999")).one()

    with pytest.raises(ValueError, match="no usa"):
        _cotizar(sesion, ajeno, "5")

    assert _contar(sesion, models.Presupuesto) == 1


def test_retirar_una_cotizacion_que_no_existe_se_rechaza(sesion, v001, cemento):
    with pytest.raises(ValueError, match="cotizacion"):
        retirar_cotizacion(
            sesion,
            NOMBRE_PROYECTO,
            CODIGO,
            "002",
            Catalogo(sesion),
            insumo=cemento,
            fuente="x",
            responsable=RESPONSABLE,
        )

    assert _contar(sesion, models.Presupuesto) == 1


# ---------------------------------------------------------------------------------------------
# Origen de precios
# ---------------------------------------------------------------------------------------------


def test_el_origen_de_cada_precio_muestra_lista_referencia_fecha_moneda_tasa_y_cotizacion(
    sesion, v001, cemento, arena
):
    base = _modelo(sesion, CODIGO).lista_precios
    registrar_origen_lista(sesion, base, tasa=D("633.3644"), fecha_tasa=date(2026, 7, 1))
    fijar_referencia(sesion, base, cemento, "CEM019")
    sesion.commit()
    nueva = _cotizar(sesion, cemento, "20")
    sesion.commit()

    filas = {f.codigo: f for f in origen_de_precios(sesion, nueva)}

    c = filas[cemento.codigo]
    assert (c.descripcion, c.precio, c.referencia) == ("Cemento Portland", D("20"), "CEM019")
    assert (c.moneda, c.tasa, c.fecha_tasa) == ("USD", D("633.3644"), date(2026, 7, 1))
    assert c.lista == nueva.lista_precios.nombre and c.alcance == models.ALCANCE_PROYECTO
    assert c.cotizacion == f"{PROVEEDOR}, {NUMERO}, {FECHA.isoformat()}"
    a = filas[arena.codigo]
    assert (a.precio, a.referencia, a.cotizacion) == (D("30"), "", "")
    assert a.fecha_vigencia == base.fecha_vigencia
    # solo los insumos que la version usa
    usados = set(
        sesion.scalars(
            select(models.LineaComposicionVersion.insumo_id)
            .join(models.ComposicionVersion)
            .where(models.ComposicionVersion.presupuesto_id == nueva.id)
        )
    )
    assert {f.insumo_id for f in filas.values()} == usados


def test_una_lista_sin_origen_registrado_es_global_y_sin_tasa(sesion, v001, cemento):
    (fila,) = [
        f for f in origen_de_precios(sesion, _modelo(sesion, CODIGO)) if f.codigo == cemento.codigo
    ]

    assert (fila.alcance, fila.tasa, fila.fecha_tasa, fila.referencia, fila.cotizacion) == (
        models.ALCANCE_GLOBAL,
        None,
        None,
        "",
        "",
    )


# ---------------------------------------------------------------------------------------------
# Bases anteriores
# ---------------------------------------------------------------------------------------------


def test_una_base_sin_las_tablas_de_origen_abre_y_cotiza(tmp_path):
    url = f"sqlite:///{(tmp_path / 'vieja.db').as_posix()}"
    motor = crear_motor(url)
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        guardar_001(sesion, sembrar(sesion), elaborar_001(sesion))
        sesion.commit()
    for tabla in (models.Cotizacion, models.ReferenciaPrecio, models.ListaPreciosOrigen):
        tabla.__table__.drop(motor)
    motor.dispose()

    motor = crear_motor(url)
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        assert Catalogo(sesion).lista_vigente(date(2026, 4, 28)).nombre
        cemento = sesion.scalars(
            select(models.Insumo).where(models.Insumo.descripcion == "Cemento Portland")
        ).one()
        nueva = _cotizar(sesion, cemento, "20")
        sesion.commit()
        assert nueva.codigo == "002"
    motor.dispose()


# ---------------------------------------------------------------------------------------------
# RF-62: un hallazgo de regla externa (R8) sobrevive a cotizar y a retirar la cotizacion
# ---------------------------------------------------------------------------------------------


def test_cotizar_y_retirar_conservan_el_hallazgo_externo_y_el_informe_recargado_es_identico(
    sesion,
):
    from dataclasses import replace

    from core.contracts import Hallazgo, Severidad

    r8 = Hallazgo(
        regla="R8",
        severidad=Severidad.ADVERTENCIA,
        descripcion="fila con origen de medida supuesto",
        impacto=D("2.5"),
        origen_ids=("LB-01-EXC",),
        valor_observado=D("1.25"),
        valor_esperado=D("1"),
    )
    resultado = elaborar_001(sesion)
    informe = replace(resultado.informe, hallazgos=resultado.informe.hallazgos + (r8,))
    guardar_001(sesion, sembrar(sesion), replace(resultado, informe=informe))
    sesion.commit()
    cemento = sesion.scalars(
        select(models.Insumo).where(models.Insumo.descripcion == "Cemento Portland")
    ).one()

    _cotizar(sesion, cemento, "20")
    sesion.commit()
    retirar_cotizacion(
        sesion,
        NOMBRE_PROYECTO,
        "002",
        "003",
        Catalogo(sesion),
        insumo=cemento,
        fuente="el proveedor no mantuvo el precio",
        responsable=RESPONSABLE,
    )
    sesion.commit()
    sesion.expunge_all()

    for codigo in ("002", "003"):
        recargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, codigo, Catalogo(sesion)).informe
        assert [h for h in recargado.hallazgos if h.regla == "R8"] == [r8], codigo
        guardados = sesion.scalar(
            select(func.count())
            .select_from(models.Hallazgo)
            .where(
                models.Hallazgo.regla == "R8",
                models.Hallazgo.presupuesto_id == _modelo(sesion, codigo).id,
            )
        )
        assert guardados == 1, codigo
    # volver a recargar da lo mismo (no se duplica ni se pierde nada al leer)
    primero = cargar_elaboracion(sesion, NOMBRE_PROYECTO, "003", Catalogo(sesion)).informe
    segundo = cargar_elaboracion(sesion, NOMBRE_PROYECTO, "003", Catalogo(sesion)).informe
    assert primero.hallazgos == segundo.hallazgos
