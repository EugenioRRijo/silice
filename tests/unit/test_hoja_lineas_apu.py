"""Agregar y quitar líneas del APU de la versión (MP-7, Tarea 26 de PLAN_MONTAR_PRESUPUESTO).

Contrato:

- `hoja_lineas_apu.agregar_linea(composicion, tipo, *, descripcion, unidad, cantidad, precio,
  depreciacion=None, modalidad=None)` pone la línea al final de su rubro; `quitar_linea(composicion,
  tipo, indice)` la quita y no deja un APU sin líneas («Un APU necesita al menos una línea.»).
- `hoja.cambios_entre` registra una línea que entra como `CambioEditado("apu",
  "{partida}|{tipo}|{n}", "alta", "", descripción)` y una que sale como `"baja"` (antes las líneas
  se emparejaban por posición con `zip(strict=False)` y la de más se perdía).
- `hoja_edicion.agregar_linea_apu` y `quitar_linea_apu` editan el borrador vivo de una versión
  guardada (un insumo del catálogo toma el precio de la lista de la versión; uno nuevo, el que se
  teclea, con la regla de las cifras); guardar escribe la línea en `linea_composicion_version`
  (`insumo_id` nulo si el insumo es nuevo).
- `hoja_lineas_apu.antes_y_despues(sesion, proyecto, catalogo, version)`: por partida cuyo APU
  cambió respecto de la línea base, el costo directo unitario, la duración y el término por
  rendimientos (Tarea 21) y el punto de equilibrio (`equilibrio_proyectado` del núcleo).

Datos FICTICIOS: la vivienda de `tests/fixtures/obra_vivienda.py`. Oráculos a mano, con la cuenta
en cada comentario. OBRA-02 (concreto, rendimiento 6, 12 m³): materiales 1 × 95 = 95; equipos
1 × 60 × 1 ÷ 6 = 10; mano de obra (2 × 45 × (1 + 6) + 1 × 2) ÷ 6 = 632 ÷ 6; costo directo
95 + 10 + 632 ÷ 6 = 210,333…; con «Concreto premezclado» (1,05 m³ a 95,00) el material sube en
1,05 × 95 = 99,75.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from aplicacion import hoja, hoja_borradores, hoja_edicion, hoja_lineas_apu
from aplicacion.control import declarar_linea_base
from aplicacion.errores import HojaInvalida
from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from core import models
from core.budget import CambioEditado, crear_proyecto
from core.budget.equilibrio import equilibrio, punto_equilibrio
from core.budget.moneda import declarar_moneda
from core.budget.persistencia import cargar_presupuesto
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ModalidadManoObra,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.costing.motor import calcular_apu
from operacion.base_datos import preparar_base
from tests.fixtures.obra_vivienda import COMPOSICIONES, FECHA, ITEMS, sembrar_catalogo

D = Decimal
OBRA = "Vivienda Demo 80 m2"
ANA = "Ana <ana>"
PARAMETROS = ParametrosCosto()  # FCAS 6, bono 1, administración 0,15 y utilidad 0,10
CONCRETO = COMPOSICIONES["OBRA-02"]
UNA_LINEA = "Un APU necesita al menos una línea."
YA_NO_ESTA = "Esa línea ya no está en el APU: vuelva a cargarlo."
REGLA = "Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56."
SIN_VERSION = (
    "Las líneas del APU se agregan y se quitan en una versión guardada: guarde primero la versión."
)


def _premezclado(composicion: ComposicionAPU = CONCRETO) -> ComposicionAPU:
    return hoja_lineas_apu.agregar_linea(
        composicion,
        "material",
        descripcion="Concreto premezclado",
        unidad="m3",
        cantidad=D("1.05"),
        precio=D("95.00"),
    )


# --- agregar y quitar una línea (funciones puras) ------------------------------------------------


def test_agregar_un_material_lo_pone_al_final_y_el_costo_directo_sube_en_99_75():
    nueva = _premezclado()
    assert nueva.materiales == (
        LineaMaterial("Cemento gris", "m3", D("1"), D("95.00")),
        LineaMaterial("Concreto premezclado", "m3", D("1.05"), D("95.00")),
    )
    assert nueva.equipos == CONCRETO.equipos and nueva.mano_obra == CONCRETO.mano_obra
    antes, despues = calcular_apu(CONCRETO, PARAMETROS), calcular_apu(nueva, PARAMETROS)
    assert despues.materiales == D("194.75")  # 95 + 1,05 × 95
    assert despues.costo_directo - antes.costo_directo == D("99.75")  # 1,05 × 95,00
    assert antes.costo_directo == D(95) + D(10) + D(632) / D(6)


def test_agregar_un_equipo_exige_su_depreciacion_y_entra_entre_el_rendimiento():
    with pytest.raises(HojaInvalida) as error:
        hoja_lineas_apu.agregar_linea(
            CONCRETO, "equipo", descripcion="Vibrador", unidad="", cantidad=D(1), precio=D(30)
        )
    assert str(error.value) == "Escriba la depreciación del equipo, por ejemplo 0,005."
    for mala in (D(0), D("1.5")):
        with pytest.raises(HojaInvalida) as error:
            hoja_lineas_apu.agregar_linea(
                CONCRETO,
                "equipo",
                descripcion="Vibrador",
                unidad="",
                cantidad=D(1),
                precio=D(30),
                depreciacion=mala,
            )
        assert str(error.value) == (
            "La depreciación debe ser mayor que 0 y a lo sumo 1, por ejemplo 0,005."
        )
    nueva = hoja_lineas_apu.agregar_linea(
        CONCRETO,
        "equipo",
        descripcion="Vibrador",
        unidad="",
        cantidad=D(1),
        precio=D(30),
        depreciacion=D("0.5"),
    )
    assert nueva.equipos[-1] == LineaEquipo("Vibrador", D(1), D(30), D("0.5"))
    # equipos: (1 × 60 × 1 + 1 × 30 × 0,5) ÷ 6 = 75 ÷ 6 = 12,5
    assert calcular_apu(nueva, PARAMETROS).equipos == D("12.5")


def test_agregar_mano_de_obra_a_destajo_entra_completa():
    nueva = hoja_lineas_apu.agregar_linea(
        CONCRETO,
        "mano_obra",
        descripcion="Cuadrilla de vaciado",
        unidad="",
        cantidad=D(1),
        precio=D(12),
        modalidad="destajo",
    )
    assert nueva.mano_obra[-1] == LineaManoObra(
        "Cuadrilla de vaciado", D(1), D(12), ModalidadManoObra.DESTAJO
    )
    # el destajo es precio por unidad de partida: + 1 × 12, sin dividir ni FCAS ni bono
    antes, despues = calcular_apu(CONCRETO, PARAMETROS), calcular_apu(nueva, PARAMETROS)
    assert despues.mano_obra - antes.mano_obra == D(12)
    jornal = hoja_lineas_apu.agregar_linea(
        CONCRETO, "mano_obra", descripcion="Ayudante", unidad="", cantidad=D(1), precio=D(30)
    )
    assert jornal.mano_obra[-1].modalidad is ModalidadManoObra.JORNAL


@pytest.mark.parametrize(
    ("tipo", "campos", "mensaje"),
    [
        ("otro", {}, "El tipo de línea debe ser material, equipo o mano de obra."),
        ("material", {"descripcion": "  "}, "Escriba la descripción del insumo nuevo."),
        (
            "material",
            {"descripcion": "x" * 301},
            "La descripción admite a lo sumo 300 caracteres.",
        ),
        (
            "material",
            {"descripcion": "Cemento gris"},
            "Ese insumo ya está en este rubro del APU: edítelo en la tabla.",
        ),
        ("material", {"unidad": " "}, "Escriba la unidad del material, por ejemplo m3."),
        ("material", {"unidad": "u" * 21}, "La unidad admite a lo sumo 20 caracteres."),
        ("material", {"cantidad": D("-1")}, "La cantidad no puede ser negativa."),
        ("material", {"precio": D("-0.01")}, "El precio no puede ser negativo."),
        (
            "mano_obra",
            {"modalidad": "por hora"},
            "La modalidad de la mano de obra debe ser jornal o destajo.",
        ),
    ],
)
def test_agregar_con_un_dato_malo_dice_que_falta(tipo, campos, mensaje):
    datos = {
        "descripcion": "Concreto premezclado",
        "unidad": "m3",
        "cantidad": D("1.05"),
        "precio": D(95),
        **campos,
    }
    with pytest.raises(HojaInvalida) as error:
        hoja_lineas_apu.agregar_linea(CONCRETO, tipo, **datos)
    assert str(error.value) == mensaje


def test_quitar_el_material_baja_el_costo_directo_en_95():
    nueva = hoja_lineas_apu.quitar_linea(CONCRETO, "material", 0)
    assert nueva.materiales == () and nueva.equipos == CONCRETO.equipos
    antes, despues = calcular_apu(CONCRETO, PARAMETROS), calcular_apu(nueva, PARAMETROS)
    assert antes.costo_directo - despues.costo_directo == D(95)  # 1 × 95


def test_quitar_una_linea_que_no_existe_o_la_ultima_del_apu_no_se_puede():
    tipo_malo = "El tipo de línea debe ser material, equipo o mano de obra."
    for tipo, indice, mensaje in (
        ("material", 1, YA_NO_ESTA),
        ("equipo", 5, YA_NO_ESTA),
        ("otro", 0, tipo_malo),
    ):
        with pytest.raises(HojaInvalida) as error:
            hoja_lineas_apu.quitar_linea(CONCRETO, tipo, indice)
        assert str(error.value) == mensaje
    sola = replace(CONCRETO, equipos=(), mano_obra=())
    with pytest.raises(HojaInvalida) as error:
        hoja_lineas_apu.quitar_linea(sola, "material", 0)
    assert str(error.value) == UNA_LINEA


# --- los cambios del borrador: altas y bajas de líneas ------------------------------------------


def _borrador(composiciones) -> hoja.Borrador:
    return hoja.Borrador(fecha=FECHA, moneda="Bs", items_base=ITEMS, composiciones=composiciones)


def test_una_linea_que_entra_es_un_alta_y_una_que_sale_una_baja():
    base = _borrador(COMPOSICIONES)
    agregada = _borrador({**COMPOSICIONES, "OBRA-02": _premezclado()})
    assert hoja.cambios_entre(base, agregada) == [
        CambioEditado("apu", "OBRA-02|material|2", "alta", "", "Concreto premezclado")
    ]
    sin_equipo = _borrador(
        {**COMPOSICIONES, "OBRA-02": hoja_lineas_apu.quitar_linea(CONCRETO, "equipo", 0)}
    )
    assert hoja.cambios_entre(base, sin_equipo) == [
        CambioEditado("apu", "OBRA-02|equipo|1", "baja", "Mezcladora de concreto", "")
    ]


def test_quitar_una_linea_del_medio_no_corre_las_demas():
    """Antes, quitar «Arena» (la 2.ª de tres) emparejaba la 2.ª con «Piedra» y perdía la 3.ª."""
    tres = replace(
        CONCRETO,
        materiales=(
            LineaMaterial("Cemento gris", "saco", D(7), D(95)),
            LineaMaterial("Arena lavada", "m3", D("0.5"), D(20)),
            LineaMaterial("Piedra picada", "m3", D("0.8"), D(25)),
        ),
    )
    sin_arena = replace(
        tres,
        materiales=(tres.materiales[0], replace(tres.materiales[2], cantidad=D("0.9"))),
    )
    base = _borrador({**COMPOSICIONES, "OBRA-02": tres})
    actual = _borrador({**COMPOSICIONES, "OBRA-02": sin_arena})
    assert hoja.cambios_entre(base, actual) == [
        CambioEditado("apu", "OBRA-02|material|2", "baja", "Arena lavada", ""),
        CambioEditado("apu", "OBRA-02|Piedra picada", "cantidad", "0.8", "0.9"),
    ]


def test_cambiar_el_insumo_o_la_cantidad_de_una_linea_sigue_igual():
    base = _borrador(COMPOSICIONES)
    otro = replace(
        CONCRETO,
        rendimiento=D(4),
        materiales=(LineaMaterial("Mortero premezclado", "m3", D(2), D(4)),),
    )
    assert hoja.cambios_entre(base, _borrador({**COMPOSICIONES, "OBRA-02": otro})) == [
        CambioEditado("apu", "OBRA-02", "rendimiento", "6", "4"),
        CambioEditado(
            "apu", "OBRA-02|Cemento gris", "insumo", "Cemento gris", "Mortero premezclado"
        ),
        CambioEditado("apu", "OBRA-02|Cemento gris", "cantidad", "1", "2"),
        CambioEditado("apu", "OBRA-02|Cemento gris", "precio", "95", "4"),
    ]


# --- el borrador vivo de una versión guardada ---------------------------------------------------


@pytest.fixture
def base(tmp_path: Path) -> Iterator:
    """La vivienda en Bs con su primera versión «001» guardada (plan por rendimientos)."""
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
        borrador = hoja.Borrador(fecha=FECHA, moneda="Bs", items_base=ITEMS)
        hoja.crear_primera_version(
            sesion, Catalogo(sesion), OBRA, borrador, fuente="Medición en sitio", responsable=ANA
        )
        yield sesion
    motor.dispose()
    hoja_borradores.olvidar_todo()


def _abierto(sesion) -> hoja_borradores.BorradorVivo:
    abierta = hoja.abrir_version(sesion, Catalogo(sesion), OBRA, "001")
    return hoja_borradores.crear("ficha", "caso", OBRA, "001", abierta.borrador, abierta)


def _agregar(sesion, vivo, rev=0, partida="OBRA-02", **campos):
    datos = {
        "tipo": "material",
        "insumo": "",
        "descripcion": "Concreto premezclado",
        "unidad": "m3",
        "cantidad": "1,05",
        "precio": "95,00",
        "depreciacion": "",
        "modalidad": "jornal",
        **campos,
    }
    return hoja_edicion.agregar_linea_apu(sesion, "ficha", vivo.id, rev, partida, **datos)


def _insumo(sesion, descripcion: str) -> models.Insumo:
    return sesion.scalars(
        select(models.Insumo).where(models.Insumo.descripcion == descripcion)
    ).one()


def test_agregar_un_insumo_nuevo_al_borrador_cuenta_un_cambio(base):
    vivo = _abierto(base)
    editado = _agregar(base, vivo)
    assert editado.rev == 1
    assert editado.borrador.composiciones["OBRA-02"].materiales[-1] == LineaMaterial(
        "Concreto premezclado", "m3", D("1.05"), D("95.00")
    )
    assert hoja_edicion.cambios_del_borrador(editado) == (
        1,
        [CambioEditado("apu", "OBRA-02|material|2", "alta", "", "Concreto premezclado")],
    )


def test_un_insumo_del_catalogo_toma_el_precio_de_la_lista_de_la_version(base):
    vivo = _abierto(base)
    mortero = _insumo(base, "Mortero premezclado")
    editado = _agregar(
        base, vivo, insumo=mortero.codigo, descripcion="", unidad="", precio="999,00", cantidad="2"
    )
    # el precio de la «Lista Bs de la vivienda» (4,00 por m2), no el tecleado
    assert editado.borrador.composiciones["OBRA-02"].materiales[-1] == LineaMaterial(
        "Mortero premezclado", "m2", D(2), D("4.00")
    )


@pytest.mark.parametrize(
    ("campos", "mensaje"),
    [
        ({"cantidad": "1.05"}, f"La cantidad no se entiende como número. {REGLA}"),
        ({"cantidad": ""}, f"Escriba la cantidad. {REGLA}"),
        ({"precio": "95.00"}, f"El precio no se entiende como número. {REGLA}"),
        ({"precio": " "}, f"Escriba el precio del insumo nuevo. {REGLA}"),
        (
            {"tipo": "equipo", "descripcion": "Vibrador", "unidad": "", "depreciacion": "0.5"},
            f"La depreciación no se entiende como número. {REGLA}",
        ),
        (
            {"insumo": "NO-EXISTE"},
            "Ese insumo no está en la lista de precios de la versión: elíjalo de la lista.",
        ),
    ],
)
def test_un_dato_malo_no_cambia_el_borrador(base, campos, mensaje):
    vivo = _abierto(base)
    with pytest.raises(HojaInvalida) as error:
        _agregar(base, vivo, **campos)
    assert str(error.value) == mensaje
    assert hoja_borradores.obtener("ficha", vivo.id).rev == 0


def test_sin_version_guardada_no_se_agregan_ni_se_quitan_lineas(base):
    vivo = hoja_borradores.crear(
        "ficha",
        "caso",
        OBRA,
        None,
        hoja.Borrador(fecha=FECHA, moneda="Bs", items_base=ITEMS, composiciones=COMPOSICIONES),
        None,
    )
    with pytest.raises(hoja_lineas_apu.SinVersionGuardada) as error:
        _agregar(base, vivo)
    assert str(error.value) == SIN_VERSION
    with pytest.raises(hoja_lineas_apu.SinVersionGuardada):
        hoja_edicion.quitar_linea_apu(base, "ficha", vivo.id, 0, "OBRA-02", "material", 0)


def test_una_partida_sin_apu_en_el_borrador(base):
    vivo = _abierto(base)
    with pytest.raises(hoja_edicion.PartidaSinApu):
        _agregar(base, vivo, partida="OBRA-99")


def test_quitar_hasta_la_ultima_linea_no_se_puede_y_el_rev_no_sube(base):
    vivo = _abierto(base)
    # el borrador vivo es el mismo objeto: su `rev` se lee en seguida
    uno = hoja_edicion.quitar_linea_apu(base, "ficha", vivo.id, 0, "OBRA-02", "material", 0).rev
    dos = hoja_edicion.quitar_linea_apu(base, "ficha", vivo.id, 1, "OBRA-02", "equipo", 0).rev
    assert (uno, dos) == (1, 2)
    with pytest.raises(HojaInvalida) as error:
        hoja_edicion.quitar_linea_apu(base, "ficha", vivo.id, 2, "OBRA-02", "mano_obra", 0)
    assert str(error.value) == UNA_LINEA
    assert hoja_borradores.obtener("ficha", vivo.id).rev == 2


def test_guardar_escribe_las_lineas_con_insumo_nulo_si_es_nuevo(base):
    vivo = _abierto(base)
    mortero = _insumo(base, "Mortero premezclado")
    _agregar(base, vivo)
    editado = _agregar(base, vivo, rev=1, insumo=mortero.codigo, cantidad="2")
    abierta = hoja.abrir_version(base, Catalogo(base), OBRA, "001")
    guardada = hoja.guardar_version(
        base,
        Catalogo(base),
        abierta,
        editado.borrador,
        fuente="Crisis del cemento: concreto premezclado",
        responsable=ANA,
    )
    assert guardada is not None and guardada.codigo == "002" and guardada.cambios == 2
    lineas = base.execute(
        select(
            models.LineaComposicionVersion.descripcion,
            models.LineaComposicionVersion.insumo_id,
            models.LineaComposicionVersion.precio,
        )
        .join(models.ComposicionVersion)
        .join(models.Presupuesto)
        .where(
            models.Presupuesto.codigo == "002",
            models.ComposicionVersion.codigo_partida == "OBRA-02",
            models.LineaComposicionVersion.tipo == "material",
        )
        .order_by(models.LineaComposicionVersion.orden)
    ).all()
    assert [(d, i, p) for d, i, p in lineas] == [
        ("Cemento gris", _insumo(base, "Cemento gris").id, D("95.00")),
        ("Concreto premezclado", None, D("95.00")),
        ("Mortero premezclado", mortero.id, D("4.00")),
    ]
    reabierta = hoja.abrir_version(base, Catalogo(base), OBRA, "002")
    assert [m.descripcion for m in reabierta.borrador.composiciones["OBRA-02"].materiales] == [
        "Cemento gris",
        "Concreto premezclado",
        "Mortero premezclado",
    ]


# --- antes y después respecto de la línea base (Control de obra) --------------------------------


def _con_linea_base(sesion) -> None:
    declarar_linea_base(
        sesion,
        OBRA,
        "001",
        desde="2026-11-02",
        perspectiva="costo",
        inicio="2026-11-02",
        dias_por_periodo="1",
        feriados="",
        fuente="Contrato firmado",
        responsable=ANA,
    )


def _version_con_la_crisis(sesion) -> str:
    """«002»: OBRA-02 con el concreto premezclado y rendimiento 4."""
    vivo = _abierto(sesion)
    _agregar(sesion, vivo)
    editado = hoja_edicion.editar_apu(
        sesion, "ficha", vivo.id, 1, "OBRA-02", "4", ["1", "1,05"], ["1"], ["2"]
    )
    abierta = hoja.abrir_version(sesion, Catalogo(sesion), OBRA, "001")
    guardada = hoja.guardar_version(
        sesion, Catalogo(sesion), abierta, editado.borrador, fuente="Crisis", responsable=ANA
    )
    assert guardada is not None
    return guardada.codigo


def test_antes_y_despues_de_la_partida_cambiada(base):
    _con_linea_base(base)
    version = _version_con_la_crisis(base)
    filas = hoja_lineas_apu.antes_y_despues(base, OBRA, Catalogo(base), version)
    assert [f.partida for f in filas] == ["OBRA-02"]
    fila = filas[0]
    assert (fila.descripcion, fila.unidad, fila.cantidad) == (
        "Concreto para fundaciones",
        "m3",
        D(12),
    )
    assert fila.costo_antes == D(95) + D(10) + D(632) / D(6)  # 210,333…
    # 194,75 de materiales + (60 + 632) ÷ 4 = 194,75 + 173 = 367,75
    assert fila.costo_despues == D("367.75")
    assert (fila.duracion_antes, fila.duracion_despues) == (D(2), D(3))  # 12 ÷ 6; 12 ÷ 4
    # 4 + 2 + 4 + 17,5 + 23,5 + 7 = 58 días; con OBRA-02 en 3 días, 59
    assert (fila.termino_antes, fila.termino_despues) == (58, 59)
    presupuesto = cargar_presupuesto(base, OBRA, "001", Catalogo(base))
    antes = punto_equilibrio(presupuesto, PARAMETROS)
    assert fila.equilibrio_antes == antes.punto
    # CV' = CV + 12 × (367,75 − 210,333…); CF' = CF × 59 ÷ 58 (el término nuevo sobre el base)
    variable = antes.costo_variable + D(12) * (D("367.75") - fila.costo_antes)
    despues = equilibrio(
        presupuesto.total, variable, antes.costo_fijo * D(59) / D(58), presupuesto.curva
    )
    assert fila.equilibrio_despues == despues.punto
    assert fila.equilibrio_despues > fila.equilibrio_antes


def test_sin_linea_base_o_con_la_misma_version_no_hay_nada_que_comparar(base):
    version = _version_con_la_crisis(base)
    assert hoja_lineas_apu.antes_y_despues(base, OBRA, Catalogo(base), version) == []
    _con_linea_base(base)
    assert hoja_lineas_apu.antes_y_despues(base, OBRA, Catalogo(base), "001") == []
