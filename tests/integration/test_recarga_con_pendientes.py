"""INV‑080: la recarga del informe conserva los ítems pendientes (expediente C3.1).

Un presupuesto emitido con un ítem sin partida (UC‑01, flujo 3a) lleva en su informe el hallazgo
`PENDIENTE`. Al recargarlo desde la base, el informe tiene que ser el del documento emitido
(RF‑02, «al producir o cargar»), no el de una reauditoría que ya no conoce el pendiente.

Cada prueba trabaja sobre un archivo SQLite en `tmp_path`: se guarda, se **cierra el motor** y se
vuelve a abrir, para que la recarga lea de verdad lo persistido y no la identidad de la sesión.
Oráculos independientes de la función que se prueba: los hallazgos de `elaborar` en memoria (la
otra ruta) y los hallazgos persistidos del documento emitido (`modelo.hallazgos`, leídos como en
`tests/integration/test_presupuesto_linea_base.py`), además del total de la fixture de la línea
base.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import exists, select

from core import models
from core.budget import (
    CODIGO_PENDIENTE,
    actualizar_precios,
    cargar_elaboracion,
    cargar_presupuesto,
    elaborar,
    guardar_presupuesto,
    plan_secuencial,
)
from core.catalog import (
    Catalogo,
    abrir_sesion,
    crear_esquema,
    crear_lista_desde_archivo,
    crear_motor,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.verificacion import Severidad
from core.verification import auditar
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import items_auditados

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv"
#: Vigencia de esa muestra (la misma de la prueba de UC‑02).
MUESTRA_FECHA = date(2026, 6, 1)

CODIGO = linea_base.CODIGO_PRESUPUESTO
CODIGO_NUEVO = "002"
ERROR = int(Severidad.ERROR)

#: El ítem cuya partida no existe en el catálogo sembrado (UC‑01, flujo 3a).
PENDIENTE = ItemComputo(
    codigo_partida="XX-99-NUE",
    descripcion="Excavacion de un foso nuevo",
    unidad="m3",
    cantidad=Decimal("2.5"),
    origen_id="T-99",
    origen_tipo=OrigenTipo.MANUAL,
    dominio=Dominio.CIVIL,
)
#: Un segundo pendiente cuya clave ordena **antes** que la del primero: si la recarga ordenara por
#: código, por origen o al revés del guardado, el orden de los dos cambiaría.
SEGUNDO = replace(PENDIENTE, codigo_partida="XX-98-NUE", origen_id="T-98", descripcion="Muro")


# ---------------------------------------------------------------------------------------------
# Ayudas
# ---------------------------------------------------------------------------------------------


def _url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'recarga.db').as_posix()}"


def _elaborar(sesion, items, codigo=CODIGO):
    """La elaboración de la interfaz y de la API: composiciones solo de las partidas que existen."""
    catalogo = Catalogo(sesion)
    existentes = {partida.codigo for partida in catalogo.partidas()}
    composiciones = catalogo.composiciones(
        dict.fromkeys(i.codigo_partida for i in items if i.codigo_partida in existentes),
        fecha=linea_base.FECHA_LINEA_BASE,
    )
    return elaborar(
        items,
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=codigo,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan_secuencial,
    )


def _guardar(sesion, proyecto, resultado, **extra):
    return guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=Catalogo(sesion).lista_vigente(linea_base.FECHA_LINEA_BASE),
        parametros=linea_base.PARAMETROS_LINEA_BASE,
        **extra,
    )


def _emitir(tmp_path: Path, items):
    """Siembra, elabora, guarda con sus pendientes y confirma en `tmp_path`; cierra el motor."""
    motor = crear_motor(_url(tmp_path))
    crear_esquema(motor)
    try:
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar(sesion)
            resultado = _elaborar(sesion, items)
            _guardar(sesion, proyecto, resultado, pendientes=resultado.pendientes)
            sesion.commit()
    finally:
        motor.dispose()
    return resultado


@pytest.fixture
def base_sembrada(tmp_path):
    """Una sesión sobre un archivo recién sembrado, para las pruebas que no llegan a guardar."""
    motor = crear_motor(_url(tmp_path))
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        yield sesion, sembrar(sesion)
    motor.dispose()


@pytest.fixture
def reabierta(tmp_path):
    """Una sesión nueva sobre el archivo ya cerrado: la recarga lee lo persistido."""

    def _abrir():
        motor = crear_motor(_url(tmp_path))
        motores.append(motor)
        return abrir_sesion(motor)

    motores = []
    yield _abrir
    for motor in motores:
        motor.dispose()


def _claves(hallazgos):
    """Los hallazgos como multiconjunto de `(regla, severidad, origen_ids)`: un hallazgo repetido
    o perdido cambia la cuenta."""
    return Counter((h.regla, int(h.severidad), tuple(h.origen_ids)) for h in hallazgos)


def _claves_persistidas(sesion, codigo):
    """Los hallazgos del documento emitido, tal como quedaron en la base."""
    modelo = sesion.scalars(
        select(models.Presupuesto).where(models.Presupuesto.codigo == codigo)
    ).one()
    return Counter(
        (h.regla, h.severidad, tuple(json.loads(h.origen_ids))) for h in modelo.hallazgos
    )


# ---------------------------------------------------------------------------------------------
# Pruebas
# ---------------------------------------------------------------------------------------------


def test_la_recarga_devuelve_el_informe_emitido_con_sus_pendientes(tmp_path, reabierta):
    """1. Ida y vuelta: el informe recargado es el emitido, con el pendiente declarado."""
    emitido = _emitir(tmp_path, [*items_auditados(), PENDIENTE])

    with reabierta() as sesion:
        recargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))
        persistidos = _claves_persistidas(sesion, CODIGO)

    assert _claves(emitido.informe.hallazgos)[(CODIGO_PENDIENTE, ERROR, ("XX-99-NUE", "T-99"))] == 1
    assert _claves(recargado.informe.hallazgos) == _claves(emitido.informe.hallazgos)
    assert _claves(recargado.informe.hallazgos) == persistidos
    assert recargado.pendientes == emitido.pendientes == (PENDIENTE,)
    assert recargado.presupuesto == emitido.presupuesto
    assert not recargado.informe.cumple


def test_la_recarga_conserva_el_orden_de_varios_pendientes(tmp_path, reabierta):
    """1b. Dos pendientes vuelven en el orden en que se elaboraron y se guardaron."""
    emitido = _emitir(tmp_path, [*items_auditados(), PENDIENTE, SEGUNDO])

    with reabierta() as sesion:
        recargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))

    assert emitido.pendientes == (PENDIENTE, SEGUNDO)
    assert recargado.pendientes == (PENDIENTE, SEGUNDO)
    assert _claves(recargado.informe.hallazgos) == _claves(emitido.informe.hallazgos)


def test_sin_pendientes_la_recarga_es_la_reauditoria(tmp_path, reabierta):
    """2. Sin pendientes, nada cambia: la recarga es `auditar(cargar_presupuesto(...))`."""
    _emitir(tmp_path, items_auditados())

    with reabierta() as sesion:
        catalogo = Catalogo(sesion)
        recargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, catalogo)
        presupuesto = cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO, catalogo)

    assert recargado.pendientes == ()
    assert recargado.presupuesto == presupuesto
    assert recargado.informe == auditar(presupuesto)
    assert recargado.presupuesto.total == linea_base.TOTAL_EXACTO_LINEA_BASE


def test_un_pendiente_que_el_informe_no_declara_no_se_guarda(base_sembrada):
    """3. Persistir un pendiente sin su hallazgo `PENDIENTE` haría que la recarga dijera más que
    el documento emitido."""
    sesion, proyecto = base_sembrada
    resultado = _elaborar(sesion, items_auditados())  # el informe no lo declara

    with pytest.raises(ValueError, match="no declara el pendiente XX-99-NUE"):
        _guardar(sesion, proyecto, resultado, pendientes=(PENDIENTE,))


def test_un_pendiente_declarado_que_no_se_pasa_no_se_guarda(base_sembrada):
    """3b. La otra dirección: el informe declara `XX-99-NUE` pendiente y se guarda sin
    `pendientes`. La recarga diría menos que el documento (CUMPLE sobre un NO CUMPLE)."""
    sesion, proyecto = base_sembrada
    resultado = _elaborar(sesion, [*items_auditados(), PENDIENTE])

    with pytest.raises(ValueError, match="declara pendiente XX-99-NUE T-99"):
        _guardar(sesion, proyecto, resultado)


def test_revalorar_arrastra_los_pendientes_del_base(tmp_path, reabierta):
    """4. D4 = A: `actualizar_precios` sobre un base con pendiente no aborta, la versión nueva lo
    declara (en memoria y recargada) y el comparativo recorre solo las partidas valoradas."""
    emitido = _emitir(tmp_path, [*items_auditados(), PENDIENTE])
    valoradas = [partida.item.codigo_partida for partida in emitido.presupuesto.partidas]

    with reabierta() as sesion:
        lista = crear_lista_desde_archivo(
            sesion,
            MUESTRA,
            nombre="Lista de precios 01/06/2026",
            moneda=linea_base.MONEDA,
            fecha_vigencia=MUESTRA_FECHA,
            origen=MUESTRA.name,
        ).lista
        nuevo, comparativo = actualizar_precios(
            sesion, NOMBRE_PROYECTO, CODIGO, lista, CODIGO_NUEVO, plan=plan_secuencial
        )
        sesion.commit()

    assert nuevo.pendientes == (PENDIENTE,)
    assert _claves(nuevo.informe.hallazgos)[(CODIGO_PENDIENTE, ERROR, ("XX-99-NUE", "T-99"))] == 1
    assert list(comparativo.tabla["codigo_partida"]) == valoradas

    with reabierta() as sesion:
        recargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, Catalogo(sesion))
    assert recargado.pendientes == (PENDIENTE,)
    assert _claves(recargado.informe.hallazgos) == _claves(nuevo.informe.hallazgos)


def test_un_presupuesto_guardado_sin_pendientes_no_los_inventa(tmp_path, reabierta):
    """5. Datos anteriores a INV‑080: su base no tiene los ítems pendientes. Se simula así: se
    guarda con `pendientes` (la guarda en dos sentidos ya no deja guardar sin ellos) y luego se
    borran de la base los ítems de cómputo sin renglón, que es exactamente lo que falta en una base
    vieja. La recarga no inventa ninguno. Es el límite declarado en el expediente C3.1."""
    _emitir(tmp_path, [*items_auditados(), PENDIENTE])
    with reabierta() as sesion:
        sin_renglon = sesion.scalars(
            select(models.ItemComputo).where(
                ~exists().where(
                    models.PartidaPresupuestada.item_computo_id == models.ItemComputo.id
                )
            )
        ).all()
        assert [item.codigo_partida for item in sin_renglon] == ["XX-99-NUE"]
        for item in sin_renglon:
            sesion.delete(item)
        sesion.commit()

    with reabierta() as sesion:
        catalogo = Catalogo(sesion)
        recargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, catalogo)
        presupuesto = cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO, catalogo)

    assert recargado.pendientes == ()
    assert recargado.informe == auditar(presupuesto)
    assert CODIGO_PENDIENTE not in {h.regla for h in recargado.informe.hallazgos}
