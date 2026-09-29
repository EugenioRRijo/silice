"""UC-07, paso 5 (INV-099, expediente C6.5): los precios atipicos de la lista nueva entran al
informe de auditoria de la version revalorada.

`core/` no importa `ml/`: `actualizar_precios` recibe el detector como un invocable. Estas pruebas
usan un detector falso (oraculo: las variaciones de la lista, calculadas a mano desde la linea
base) y, con el extra `ml`, el `ml.anomaly.precios_atipicos` real. La base vive en memoria.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from core import models
from core.budget import (
    CODIGO_ATIPICO,
    actualizar_precios,
    cargar_elaboracion,
    plan_secuencial,
)
from core.catalog import Catalogo, crear_lista_desde_archivo
from core.contracts import Severidad
from core.verification import auditar
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import CEMENTO, PRECIOS_NUEVOS, VARIACIONES
from tests.fixtures.base_con_pendiente import elaborar_en, guardar_en
from tests.fixtures.computo_auditado import items_auditados

FECHA_NUEVA = date(2026, 6, 1)
CODIGO_NUEVO = "002"
AYUDANTE = "Ayudante"
CONCRETO = linea_base.APU_CONCRETO.codigo_partida
#: El ayudante sube un dolar sobre su jornal de la linea base (uno solo en los cinco APU).
(JORNAL_AYUDANTE,) = {
    obrero.sueldo
    for apu in linea_base.APUS_LINEA_BASE
    for obrero in apu.mano_obra
    if obrero.descripcion == AYUDANTE
}
VARIACION_AYUDANTE = Decimal(1) / JORNAL_AYUDANTE
#: Las partidas de la linea base que llevan ayudante, por su codigo (las devuelve ordenadas).
CON_AYUDANTE = tuple(
    sorted(
        apu.codigo_partida
        for apu in linea_base.APUS_LINEA_BASE
        if any(obrero.descripcion == AYUDANTE for obrero in apu.mano_obra)
    )
)
UMBRAL_FALSO = Decimal("0.15")


@dataclass(frozen=True)
class Marca:
    """Una marca de atipico con la forma de `ml.anomaly.PrecioAtipico`."""

    id: str
    valor: Decimal
    puntaje: float


class DetectorFalso:
    """Marca las variaciones mayores que `UMBRAL_FALSO` y las ids extra que se le den."""

    def __init__(self, extra: tuple[Marca, ...] = ()) -> None:
        self.extra = extra
        self.recibido: dict[str, Decimal] = {}

    def __call__(self, variaciones: Mapping[str, Decimal]) -> list[Marca]:
        self.recibido = dict(variaciones)
        return [
            Marca(id=id_, valor=valor, puntaje=-0.25)
            for id_, valor in variaciones.items()
            if valor > UMBRAL_FALSO
        ] + list(self.extra)


def _contar(sesion, modelo) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


def _lista(sesion, tmp_path: Path, filas: str):
    archivo = tmp_path / "lista.csv"
    archivo.write_text("tipo,insumo,unidad,precio\n" + filas, encoding="utf-8")
    return crear_lista_desde_archivo(
        sesion,
        archivo,
        nombre="Lista 01/06/2026",
        moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_NUEVA,
    ).lista


def _revalorar(sesion, lista, detector=None):
    return actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        linea_base.CODIGO_PRESUPUESTO,
        lista,
        CODIGO_NUEVO,
        plan=plan_secuencial,
        detectar_atipicos=detector,
    )


@pytest.fixture
def base(sesion):
    """La linea base sembrada con su presupuesto 001 guardado."""
    guardar_en(sesion, sembrar(sesion), elaborar_en(sesion, items_auditados()))
    return sesion


@pytest.fixture
def lista_cemento_y_ayudante(base, tmp_path):
    return _lista(
        base,
        tmp_path,
        f"material,{CEMENTO},saco,{PRECIOS_NUEVOS[CEMENTO]}\n"
        f"mano_obra,{AYUDANTE},,{JORNAL_AYUDANTE + 1}\n",
    )


def _atipicos(informe):
    return [h for h in informe.hallazgos if h.regla == CODIGO_ATIPICO]


def test_los_atipicos_entran_al_informe_se_guardan_y_se_recargan(base, lista_cemento_y_ayudante):
    detector = DetectorFalso()

    nuevo, _ = _revalorar(base, lista_cemento_y_ayudante, detector)

    assert sorted(detector.recibido.values()) == sorted([VARIACIONES[CEMENTO], VARIACION_AYUDANTE])
    por_valor = {h.valor_observado: h for h in _atipicos(nuevo.informe)}
    assert set(por_valor) == {VARIACIONES[CEMENTO], VARIACION_AYUDANTE}
    cemento, ayudante = por_valor[VARIACIONES[CEMENTO]], por_valor[VARIACION_AYUDANTE]
    assert {cemento.severidad, ayudante.severidad} == {Severidad.ADVERTENCIA}
    assert cemento.origen_ids == (CONCRETO,)
    assert nuevo.informe.partida_de(cemento) == CONCRETO
    assert ayudante.origen_ids == CON_AYUDANTE and len(CON_AYUDANTE) > 1
    assert nuevo.informe.partida_de(ayudante) is None
    assert CEMENTO in cemento.descripcion and "+20" in cemento.descripcion
    assert "RF-29" in cemento.descripcion

    sin_atipicos = auditar(nuevo.presupuesto)
    assert nuevo.informe.cumple == sin_atipicos.cumple
    assert nuevo.informe.cuenta_por_regla_evaluada() == sin_atipicos.cuenta_por_regla_evaluada()

    base.commit()
    guardados = base.scalars(
        select(models.Hallazgo)
        .join(models.Presupuesto)
        .where(models.Presupuesto.codigo == CODIGO_NUEVO, models.Hallazgo.regla == CODIGO_ATIPICO)
    ).all()
    assert len(guardados) == 2
    base.expunge_all()
    recargado = cargar_elaboracion(base, NOMBRE_PROYECTO, CODIGO_NUEVO, Catalogo(base))
    assert sorted(_atipicos(recargado.informe), key=str) == sorted(
        _atipicos(nuevo.informe), key=str
    )
    assert recargado.informe.partida_de(cemento) == CONCRETO
    assert recargado.informe.partida_de(ayudante) is None
    assert recargado.informe.a_markdown() == nuevo.informe.a_markdown()


def test_sin_detector_el_informe_es_la_auditoria_del_presupuesto(base, lista_cemento_y_ayudante):
    nuevo, _ = _revalorar(base, lista_cemento_y_ayudante)

    assert _atipicos(nuevo.informe) == []
    assert nuevo.informe.hallazgos == auditar(nuevo.presupuesto).hallazgos


def _historico(sesion, insumo: models.Insumo, variaciones: list[str]) -> None:
    """Cambios de precio de listas anteriores (2025) de `insumo`: el historico acumulado."""
    anteriores = [
        models.ListaPrecios(
            nombre=f"Historica {n}", moneda="USD", fecha_vigencia=date(2025, n, 1), origen="prueba"
        )
        for n in (1, 2)
    ]
    sesion.add_all(anteriores)
    sesion.flush()
    sesion.add_all(
        models.CambioPrecio(
            lista_anterior_id=anteriores[0].id,
            lista_nueva_id=anteriores[1].id,
            insumo_id=insumo.id,
            precio_anterior=Decimal(100),
            precio_nuevo=Decimal(100) * (1 + Decimal(v)),
            variacion=Decimal(v),
            fecha=date(2025, 2, 1),
        )
        for v in variaciones
    )
    sesion.flush()


def _insumo(sesion, descripcion: str) -> models.Insumo:
    return next(i for i in Catalogo(sesion).insumos() if i.descripcion == descripcion)


def test_las_marcas_ajenas_a_la_lista_o_al_presupuesto_no_dan_hallazgo(base, tmp_path):
    """No son hallazgos de este presupuesto: la marca de un cambio de otra lista (un cemento de
    2025 que el detector tambien marca), la de un id que no esta en el historico y la de un
    insumo que ninguna partida usa (con precio en la lista sembrada y en la nueva)."""
    _historico(base, _insumo(base, CEMENTO), ["0.5"])
    catalogo = Catalogo(base)
    sembrada = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    ajeno = catalogo.dar_de_alta_insumo(models.TipoInsumo.MATERIAL, "Cal hidratada", "saco")
    base.add(models.PrecioInsumo(lista_id=sembrada.id, insumo_id=ajeno.id, precio=Decimal("5")))
    base.flush()
    lista = _lista(base, tmp_path, "material,Cal hidratada,saco,9\n")
    detector = DetectorFalso(extra=(Marca(id="999999", valor=Decimal("3"), puntaje=-0.4),))

    nuevo, comparativo = _revalorar(base, lista, detector)

    assert comparativo.insumos_afectados == 1
    # el cemento de 2025 y la cal de esta lista, (9 - 5) / 5: los dos marcados por el falso
    assert sorted(detector.recibido.values()) == [Decimal("0.5"), Decimal("0.8")]
    assert _atipicos(nuevo.informe) == []


def test_repetir_la_revaloracion_no_duplica_el_historial(base, lista_cemento_y_ayudante):
    """UC-02 sigue idempotente con `registrar_cambios` antes de guardar: revalorar otra vez con
    el mismo par de listas (una version 003) no duplica cambios ni incidencias, y su informe
    declara los mismos atipicos."""
    primero, _ = _revalorar(base, lista_cemento_y_ayudante, DetectorFalso())
    base.commit()
    conteos = (_contar(base, models.CambioPrecio), _contar(base, models.IncidenciaCambio))

    segundo, _ = actualizar_precios(
        base,
        NOMBRE_PROYECTO,
        linea_base.CODIGO_PRESUPUESTO,
        lista_cemento_y_ayudante,
        "003",
        plan=plan_secuencial,
        detectar_atipicos=DetectorFalso(),
    )

    assert (_contar(base, models.CambioPrecio), _contar(base, models.IncidenciaCambio)) == conteos
    assert conteos[0] == 2
    assert sorted(_atipicos(segundo.informe), key=str) == sorted(
        _atipicos(primero.informe), key=str
    )


def test_con_el_detector_real_el_cemento_sale_atipico(base, lista_cemento_y_ayudante):
    """Con el extra `ml` (la CI lo instala): diez variaciones historicas pequenas y la lista nueva;
    el cemento (+20 %) se aparta del historico y entra al informe como ATIPICO."""
    pytest.importorskip("sklearn")
    from ml.anomaly import MINIMO_OBSERVACIONES, precios_atipicos

    historicas = ["0.010", "0.020", "0.015", "0.012", "0.018", "0.011", "0.017", "0.013"]
    historicas += ["0.016", "0.014"]
    _historico(base, _insumo(base, "Piedra picada"), historicas)
    assert len(historicas) + 2 >= MINIMO_OBSERVACIONES

    nuevo, _ = _revalorar(base, lista_cemento_y_ayudante, precios_atipicos)

    cemento = [h for h in _atipicos(nuevo.informe) if CEMENTO in h.descripcion]
    assert [h.origen_ids for h in cemento] == [(CONCRETO,)]
    assert all(h.severidad is Severidad.ADVERTENCIA for h in _atipicos(nuevo.informe))
