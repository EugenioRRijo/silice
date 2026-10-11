"""SF-E1 (RF-62, spec 8.4): los hallazgos de reglas que no son las siete sobreviven a cada camino.

`elaborar` admite `reglas=`; la recarga, la revaloracion, los escenarios y la importacion vuelven a
declarar los hallazgos guardados cuya regla no esta en `REGLAS`, como ya hacia `CODIGO_ATIPICO`
(expediente C6.5), de modo que el informe recargado es el emitido. La regla de prueba es generica:
ningun dominio ni adaptador entra en estas pruebas.

Oraculos independientes: los hallazgos de `elaborar` en memoria (la ruta que no pasa por la base)
y los hallazgos persistidos (`models.Hallazgo`), contados con una consulta propia.
"""

from __future__ import annotations

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
    crear_proyecto,
    elaborar,
    generar_escenario,
    guardar_presupuesto,
    hallazgos_externos,
    importar_presupuesto,
    plan_secuencial,
)
from core.catalog import Catalogo, crear_lista_desde_archivo
from core.contracts import Dominio, Hallazgo, ReglaVerificacion, Severidad
from core.contracts.presupuesto import Presupuesto
from core.verification import REGLAS
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import CEMENTO, PRECIOS_NUEVOS
from tests.fixtures.computo_auditado import items_auditados
from tests.fixtures.presupuesto_tabular import escribir_presupuesto_tabular

CODIGO = linea_base.CODIGO_PRESUPUESTO
CODIGO_NUEVO = "002"
CODIGO_EXTERNA = "X1"


class ReglaExterna(ReglaVerificacion):
    """Una regla ajena a las siete: un aviso sobre la primera partida y un error sobre las dos
    primeras. Con valores `Decimal` en los campos opcionales para probar la ida y vuelta."""

    codigo = CODIGO_EXTERNA
    nombre = "Regla externa de prueba"

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        codigos = [p.item.codigo_partida for p in presupuesto.partidas]
        if len(codigos) < 2:
            return []
        return [
            Hallazgo(
                regla=CODIGO_EXTERNA,
                severidad=Severidad.ADVERTENCIA,
                descripcion=f"aviso externo sobre {codigos[0]}",
                impacto=Decimal("1.25"),
                origen_ids=(codigos[0],),
                valor_observado=Decimal("3.5"),
                valor_esperado=Decimal("4"),
            ),
            Hallazgo(
                regla=CODIGO_EXTERNA,
                severidad=Severidad.ERROR,
                descripcion=f"error externo sobre {codigos[0]} y {codigos[1]}",
                origen_ids=(codigos[0], codigos[1]),
            ),
        ]


EXTRA = ReglaExterna()
CON_EXTRA = (*REGLAS, EXTRA)


def _externos(informe):
    return [h for h in informe.hallazgos if h.regla == CODIGO_EXTERNA]


def _elaborar(sesion, codigo=CODIGO, reglas=REGLAS):
    catalogo = Catalogo(sesion)
    items = items_auditados()
    composiciones = catalogo.composiciones(
        dict.fromkeys(i.codigo_partida for i in items), fecha=linea_base.FECHA_LINEA_BASE
    )
    return elaborar(
        items,
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=codigo,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan_secuencial,
        reglas=reglas,
    )


def _guardar(sesion, proyecto, resultado):
    return guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=Catalogo(sesion).lista_vigente(linea_base.FECHA_LINEA_BASE),
        parametros=linea_base.PARAMETROS_LINEA_BASE,
        pendientes=resultado.pendientes,
    )


def _guardados(sesion, codigo, proyecto=NOMBRE_PROYECTO, regla=CODIGO_EXTERNA) -> int:
    return sesion.scalar(
        select(func.count())
        .select_from(models.Hallazgo)
        .join(models.Presupuesto)
        .join(models.Proyecto)
        .where(
            models.Presupuesto.codigo == codigo,
            models.Proyecto.nombre == proyecto,
            models.Hallazgo.regla == regla,
        )
    )


def _mismo_informe(recargado, emitido) -> None:
    assert recargado.hallazgos == emitido.hallazgos
    assert recargado.cumple == emitido.cumple
    for hallazgo in emitido.hallazgos:
        assert recargado.partida_de(hallazgo) == emitido.partida_de(hallazgo)


@pytest.fixture
def base(sesion):
    """El presupuesto 001 de la linea base elaborado con la regla externa y guardado."""
    proyecto = sembrar(sesion)
    emitido = _elaborar(sesion, reglas=CON_EXTRA)
    _guardar(sesion, proyecto, emitido)
    sesion.commit()
    sesion.expunge_all()
    return emitido


def test_elaborar_con_reglas_extra_las_evalua_y_sin_ellas_no(sesion):
    con = _elaborar(sesion, reglas=CON_EXTRA)
    sin = _elaborar(sesion)

    assert len(_externos(con.informe)) == 2
    assert _externos(sin.informe) == []
    assert (CODIGO_EXTERNA, EXTRA.nombre) in con.informe.reglas_evaluadas
    assert con.informe.reglas_evaluadas[: len(REGLAS)] == sin.informe.reglas_evaluadas
    assert not con.informe.cumple  # el error externo cuenta como cualquier otro


def test_hallazgos_externos_toma_los_que_ninguna_regla_dada_evalua(sesion):
    informe = _elaborar(sesion, reglas=CON_EXTRA).informe

    assert hallazgos_externos(informe) == tuple(_externos(informe))
    assert hallazgos_externos(informe, CON_EXTRA) == ()


def test_la_recarga_devuelve_el_informe_emitido(sesion, base):
    recargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))

    assert len(_externos(recargado.informe)) == 2
    _mismo_informe(recargado.informe, base.informe)


def test_recargar_con_la_regla_la_reaudita_y_no_duplica(sesion, base):
    recargado = cargar_elaboracion(
        sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion), reglas=CON_EXTRA
    )

    assert len(_externos(recargado.informe)) == 2
    _mismo_informe(recargado.informe, base.informe)


def test_fr4_guardar_lo_recargado_no_duplica_los_hallazgos(sesion, base):
    """[FR-4] recargar y volver a guardar, cuantas veces sea, deja los mismos hallazgos."""
    vigente = base
    origen = NOMBRE_PROYECTO
    for destino in ("Segundo", "Tercero"):
        recargado = cargar_elaboracion(sesion, origen, CODIGO, Catalogo(sesion))
        _guardar(sesion, crear_proyecto(sesion, destino, dominio=Dominio.CIVIL), recargado)
        sesion.commit()
        sesion.expunge_all()
        assert len(_externos(recargado.informe)) == 2
        vigente, origen = recargado, destino

    assert _guardados(sesion, CODIGO) == 2
    assert _guardados(sesion, CODIGO, proyecto="Segundo") == 2
    assert _guardados(sesion, CODIGO, proyecto="Tercero") == 2
    _mismo_informe(vigente.informe, base.informe)


@dataclass(frozen=True)
class Marca:
    id: str
    valor: Decimal
    puntaje: float


def _marca_todo(variaciones):
    """Detector falso: todo cambio de la lista es atipico."""
    return [Marca(id=i, valor=v, puntaje=-0.3) for i, v in variaciones.items()]


def _lista(sesion, tmp_path, nombre, precio, fecha):
    archivo = tmp_path / f"{nombre}.csv"
    archivo.write_text(
        f"tipo,insumo,unidad,precio{chr(10)}material,{CEMENTO},saco,{precio}{chr(10)}"
    )
    return crear_lista_desde_archivo(
        sesion, archivo, nombre=nombre, moneda=linea_base.MONEDA, fecha_vigencia=fecha
    ).lista


def _atipicos(informe):
    return [h for h in informe.hallazgos if h.regla == CODIGO_ATIPICO]


def test_revalorar_arrastra_los_externos_y_no_los_atipicos_viejos(sesion, base, tmp_path):
    precio = Decimal(str(PRECIOS_NUEVOS[CEMENTO]))
    lista2 = _lista(sesion, tmp_path, "L2", precio, date(2026, 6, 1))

    segundo, _ = actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        CODIGO,
        lista2,
        CODIGO_NUEVO,
        plan=plan_secuencial,
        detectar_atipicos=_marca_todo,
    )
    sesion.commit()
    sesion.expunge_all()
    lista3 = _lista(sesion, tmp_path, "L3", precio * 2, date(2026, 7, 1))
    tercero, _ = actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        CODIGO_NUEVO,
        lista3,
        "003",
        plan=plan_secuencial,
        detectar_atipicos=_marca_todo,
    )
    sesion.commit()
    sesion.expunge_all()

    viejos, nuevos = _atipicos(segundo.informe), _atipicos(tercero.informe)
    assert len(viejos) == 1 and len(nuevos) == 1
    assert nuevos[0] not in viejos  # solo el del detector de la lista 3, no el heredado
    assert len(_externos(segundo.informe)) == len(_externos(tercero.informe)) == 2
    assert _guardados(sesion, "003") == 2
    assert _guardados(sesion, "003", regla=CODIGO_ATIPICO) == 1
    recargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, "003", Catalogo(sesion))
    _mismo_informe(recargado.informe, tercero.informe)


def test_el_escenario_declara_los_externos_que_se_le_pasan(sesion, base):
    recargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))
    composiciones = Catalogo(sesion).composiciones(
        dict.fromkeys(p.item.codigo_partida for p in recargado.presupuesto.partidas),
        fecha=linea_base.FECHA_LINEA_BASE,
    )
    externos = hallazgos_externos(recargado.informe)

    con = generar_escenario(
        "alza",
        recargado.presupuesto,
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        externos=externos,
    )
    sin = generar_escenario(
        "alza", recargado.presupuesto, composiciones, linea_base.PARAMETROS_LINEA_BASE
    )

    assert len(externos) == 2
    assert tuple(_externos(con.informe)) == externos
    assert _externos(sin.informe) == []

    atipico = Hallazgo(
        regla=CODIGO_ATIPICO,
        severidad=Severidad.ADVERTENCIA,
        descripcion="precio atipico de la lista del base",
    )
    con_atipico = generar_escenario(
        "alza",
        recargado.presupuesto,
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        externos=(*externos, atipico),
    )
    assert _atipicos(con_atipico.informe) == []  # los atipicos son de la lista del base
    assert tuple(_externos(con_atipico.informe)) == externos


def test_importar_con_reglas_extra_recarga_el_mismo_informe(sesion, tmp_path):
    proyecto = crear_proyecto(sesion, "Tercero", dominio=Dominio.CIVIL)
    archivo: Path = escribir_presupuesto_tabular(tmp_path)

    emitido = importar_presupuesto(sesion, archivo, proyecto, reglas=CON_EXTRA)
    sesion.commit()
    sesion.expunge_all()
    recargado = cargar_elaboracion(sesion, "Tercero", CODIGO, Catalogo(sesion))

    assert len(_externos(emitido.informe)) == 2
    _mismo_informe(recargado.informe, emitido.informe)


def test_reglas_como_iterador_no_duplican_las_siete(sesion, base):
    """Un iterador de un solo uso se consume una vez: las siete no se evaluan dos veces."""
    items = items_auditados()
    catalogo = Catalogo(sesion)
    composiciones = catalogo.composiciones(
        dict.fromkeys(i.codigo_partida for i in items), fecha=linea_base.FECHA_LINEA_BASE
    )
    resultado = elaborar(
        items,
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        codigo="IT",
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan_secuencial,
        reglas=iter(CON_EXTRA),
    )
    de_lista = _elaborar(sesion, codigo="IT", reglas=CON_EXTRA)
    assert resultado.informe.hallazgos == de_lista.informe.hallazgos
    assert resultado.informe.reglas_evaluadas == de_lista.informe.reglas_evaluadas

    recargado = cargar_elaboracion(
        sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion), reglas=iter(CON_EXTRA)
    )
    _mismo_informe(recargado.informe, base.informe)
