"""El presupuesto de las siete inconsistencias como archivo tabular de un tercero (RF-24, INV-076).

Escribe el XLSX que importa `core.budget.importacion` a partir de
`presupuesto_con_siete_inconsistencias()`, sin repetir ningun dato: items, unidades del autor, APU,
curva y parametros salen de esa fixture y de la linea base. Solo cambia el **prefijo** de los
codigos de partida (`LB-` por `TER-`, tambien dentro de los `origen_id` y del balance de R5), porque
la base de prueba ya tiene sembradas las partidas `LB-*` y la importacion rechaza un codigo que ya
esta en el catalogo (expediente C6.4). Todo numero se escribe como texto: el archivo del tercero no
pasa por `float`. El archivo vive donde diga la prueba (`tmp_path`): nada escribe en `data/`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import openpyxl

from core.budget.importacion import (
    COLUMNAS_APU,
    COLUMNAS_CURVA,
    COLUMNAS_DATOS,
    COLUMNAS_INSUMOS,
    COLUMNAS_PRESUPUESTO,
    HOJA_APU,
    HOJA_CURVA,
    HOJA_DATOS,
    HOJA_INSUMOS,
    HOJA_PRESUPUESTO,
)
from core.contracts import ComposicionAPU, ItemComputo, Presupuesto
from core.verification.directivas import CLAVE_UNIDAD_ORIGINAL
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.presupuesto_auditado import presupuesto_con_siete_inconsistencias

PREFIJO_LINEA_BASE = "LB-"
PREFIJO_TERCERO = "TER-"
NOMBRE_ARCHIVO = "presupuesto_tercero.xlsx"


def codigo_tercero(texto: str, prefijo: str = PREFIJO_TERCERO) -> str:
    """El texto con el prefijo de partida de la linea base cambiado por el del tercero."""
    return texto.replace(PREFIJO_LINEA_BASE, prefijo)


def _item_tercero(item: ItemComputo, prefijo: str) -> ItemComputo:
    return replace(
        item,
        codigo_partida=codigo_tercero(item.codigo_partida, prefijo),
        origen_id=codigo_tercero(item.origen_id, prefijo),
        especificaciones={
            clave: codigo_tercero(valor, prefijo) for clave, valor in item.especificaciones.items()
        },
    )


def presupuesto_tercero(prefijo: str = PREFIJO_TERCERO) -> Presupuesto:
    """El presupuesto de las siete inconsistencias con los codigos del tercero: el oraculo de lo
    que la importacion debe reconstruir."""
    original = presupuesto_con_siete_inconsistencias()
    return replace(
        original,
        partidas=tuple(
            replace(
                partida,
                item=_item_tercero(partida.item, prefijo),
                apu=replace(
                    partida.apu, codigo_partida=codigo_tercero(partida.apu.codigo_partida, prefijo)
                ),
            )
            for partida in original.partidas
        ),
    )


def _con_precios(apu: ComposicionAPU, precios: Mapping[str, Decimal]) -> ComposicionAPU:
    return replace(
        apu,
        materiales=tuple(
            replace(m, precio=precios.get(m.descripcion, m.precio)) for m in apu.materiales
        ),
    )


def _texto(valor: object) -> str:
    return "" if valor is None else str(valor)


def _filas_datos(presupuesto: Presupuesto) -> list[list[str]]:
    parametros = linea_base.PARAMETROS_LINEA_BASE
    (dominio,) = {partida.item.dominio for partida in presupuesto.partidas}
    return [
        ["codigo", presupuesto.codigo],
        ["fecha", presupuesto.fecha.isoformat()],
        ["moneda", presupuesto.moneda],
        ["dominio", dominio.value],
        ["fcas", str(parametros.fcas)],
        ["bono_alimentacion", str(parametros.bono_alimentacion)],
        ["administracion", str(parametros.administracion)],
        ["utilidad", str(parametros.utilidad)],
    ]


def _fila_presupuesto(item: ItemComputo) -> list[str]:
    especificaciones = {
        clave: valor
        for clave, valor in item.especificaciones.items()
        if clave != CLAVE_UNIDAD_ORIGINAL
    }
    return [
        item.codigo_partida,
        item.descripcion,
        item.especificaciones[CLAVE_UNIDAD_ORIGINAL],  # la unidad que escribio el autor
        str(item.cantidad),
        item.origen_id,
        _texto(item.regla),
        json.dumps({k: str(v) for k, v in item.parametros.items()}) if item.parametros else "",
        json.dumps(especificaciones, ensure_ascii=False) if especificaciones else "",
    ]


def _filas_insumos(apu: ComposicionAPU) -> list[list[str]]:
    return [
        *(
            [
                apu.codigo_partida,
                "material",
                m.descripcion,
                m.unidad,
                str(m.cantidad),
                str(m.precio),
                "",
                "",
            ]
            for m in apu.materiales
        ),
        *(
            [
                apu.codigo_partida,
                "equipo",
                e.descripcion,
                "",
                str(e.cantidad),
                str(e.precio),
                str(e.depreciacion),
                "",
            ]
            for e in apu.equipos
        ),
        *(
            [
                apu.codigo_partida,
                "mano_obra",
                o.descripcion,
                "",
                str(o.cantidad),
                str(o.sueldo),
                "",
                o.modalidad.value,
            ]
            for o in apu.mano_obra
        ),
    ]


def escribir_presupuesto_tabular(
    carpeta: Path,
    prefijo: str = PREFIJO_TERCERO,
    con_curva: bool = True,
    nombre: str = NOMBRE_ARCHIVO,
    precios_materiales: Mapping[str, Decimal] | None = None,
) -> Path:
    """Escribe el XLSX del tercero en `carpeta` y devuelve su ruta.

    `prefijo` cambia el de los codigos de partida (`"LB-"` reproduce los de la linea base, que
    chocan con el catalogo sembrado); `con_curva=False` omite la hoja opcional `Curva`;
    `precios_materiales` (descripcion -> precio) da al tercero un precio propio, distinto del
    del catalogo, en los materiales con esa descripcion de todos sus APU.
    """
    presupuesto = presupuesto_tercero(prefijo)
    composiciones = {
        partida.apu.codigo_partida: _con_precios(partida.apu, precios_materiales or {})
        for partida in presupuesto.partidas
    }

    libro = openpyxl.Workbook()
    hojas = [
        (HOJA_DATOS, COLUMNAS_DATOS, _filas_datos(presupuesto)),
        (
            HOJA_PRESUPUESTO,
            COLUMNAS_PRESUPUESTO,
            [_fila_presupuesto(partida.item) for partida in presupuesto.partidas],
        ),
        (
            HOJA_APU,
            COLUMNAS_APU,
            [
                [apu.codigo_partida, apu.descripcion, apu.unidad, str(apu.rendimiento)]
                for apu in composiciones.values()
            ],
        ),
        (
            HOJA_INSUMOS,
            COLUMNAS_INSUMOS,
            [fila for apu in composiciones.values() for fila in _filas_insumos(apu)],
        ),
    ]
    if con_curva:
        hojas.append(
            (
                HOJA_CURVA,
                COLUMNAS_CURVA,
                [
                    [punto.periodo, str(punto.monto), str(punto.acumulado)]
                    for punto in presupuesto.curva
                ],
            )
        )
    libro.remove(libro.active)
    for titulo, columnas, filas in hojas:
        hoja = libro.create_sheet(titulo)
        hoja.append(list(columnas))
        for fila in filas:
            hoja.append(fila)
    ruta = carpeta / nombre
    libro.save(ruta)
    return ruta
