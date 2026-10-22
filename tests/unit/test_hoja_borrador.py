"""`ui.hoja`, el borrador editable de la hoja (SF3, spec §5.3, §9.2 y §9.4), sin base de datos.

El borrador reune lo que la hoja edita: el espacio, la copia de las composiciones de la version
(DA-SF-7), los parametros, el plan y las cantidades escritas a mano (DA-SF-5). Los oraculos salen de
aritmetica a mano: con el APU sintetico de `tests/fixtures/hoja_borrador.py` el precio unitario de
cada partida es 2 x 1,15 x 1,10 = 2,53 y el costo directo, 2; el punto de equilibrio es
CF x V / (V - CV) con CF = 15 % de CV, o sea 0,30 Q x 2,53 Q / 0,53 Q = 56,60 % de las ventas
(el literal que la bitacora de TI-001 ya documenta).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from adapters.espacio import Espacio
from aplicacion import hoja
from core.budget import EstadoEquilibrio
from core.budget.edicion import CambioEditado
from core.contracts import ParametrosCosto, Severidad
from tests.fixtures.hoja_borrador import PU_SINTETICO, borrador_bano

D = Decimal


def _total(borrador, **kw) -> Decimal:
    return hoja.elaborar_borrador(borrador, **kw).elaboracion.presupuesto.total


def _clave(items, codigo) -> str:
    return next(
        c
        for c, i in zip(hoja.claves_de_items(items), items, strict=True)
        if i.codigo_partida == codigo
    )


# --- cantidades escritas a mano (DA-SF-5) -------------------------------------------------------


def test_escribir_una_cantidad_cambia_el_total_en_delta_por_el_pu():
    base = borrador_bano()
    items = hoja.items_elaborados(base)
    llave = next(i for i in items if i.codigo_partida == "AF-LLAVE")
    clave = _clave(items, "AF-LLAVE")

    editado = replace(base, cantidades={clave: llave.cantidad + D("10")})

    assert _total(editado) - _total(base) == D("10") * PU_SINTETICO


def test_la_cantidad_escrita_la_marca_r8_y_ninguna_otra_regla_cambia():
    base = borrador_bano()
    items = hoja.items_elaborados(base)
    clave = _clave(items, "AF-LLAVE")
    editado = replace(base, cantidades={clave: D("9")})

    limpio = hoja.elaborar_borrador(base).elaboracion.informe
    marcado = hoja.elaborar_borrador(editado).elaboracion.informe

    nuevos = [h for h in marcado.hallazgos if h not in limpio.hallazgos]
    assert [(h.regla, h.severidad) for h in nuevos] == [("R8", Severidad.ADVERTENCIA)]
    assert "AF-LLAVE" in nuevos[0].descripcion and "a mano" in nuevos[0].descripcion


def test_el_estado_de_las_filas_de_origen_lleva_la_marca_de_la_cantidad_escrita():
    base = borrador_bano()
    items = hoja.items_elaborados(base)
    llave = next(i for i in items if i.codigo_partida == "AF-LLAVE")
    editado = replace(base, cantidades={_clave(items, "AF-LLAVE"): D("9")})

    estado = hoja.elaborar_borrador(editado).estado

    # el item AF-LLAVE cita las filas F1, P1 y P2: las tres llevan la marca; ninguna otra
    citadas = {c for c in llave.origen_id.split(";") if c.startswith("esp_")}
    marcadas = {
        k for k, e in estado.items() if "fijada a mano" in e.texto and "AF-LLAVE" in e.texto
    }
    assert citadas == marcadas
    assert {"esp_puntos:P1", "esp_puntos:P2", "esp_fuentes:F1"} <= marcadas


def test_una_cantidad_escrita_de_un_item_que_ya_no_existe_se_ignora():
    base = borrador_bano()

    huerfano = replace(base, cantidades={"X|esp_puntos:FANTASMA": D("3")})

    assert _total(huerfano) == _total(base)
    assert hoja.cantidades_escritas(huerfano) == []


def test_las_claves_de_items_son_unicas_aunque_se_repita_partida_y_origen():
    items = hoja.items_elaborados(borrador_bano())
    doble = [*items, items[0]]

    claves = hoja.claves_de_items(doble)

    assert len(set(claves)) == len(doble)
    assert claves[: len(items)] == hoja.claves_de_items(items)


# --- parametros (RF-57) -------------------------------------------------------------------------


def test_los_parametros_se_leen_de_texto_con_el_campo_culpable_en_el_error():
    ok = hoja.parametros_desde_texto(
        {"fcas": "6.5", "bono_alimentacion": "1", "administracion": "0.18", "utilidad": "0.1"}
    )
    assert ok == ParametrosCosto(
        fcas=D("6.5"), bono_alimentacion=D("1"), administracion=D("0.18"), utilidad=D("0.1")
    )
    for campo, valor in (("fcas", "mucho"), ("utilidad", "-0.1"), ("administracion", "")):
        textos = {
            "fcas": "6",
            "bono_alimentacion": "1",
            "administracion": "0.15",
            "utilidad": "0.1",
        }
        textos[campo] = valor
        with pytest.raises(hoja.HojaInvalida, match=campo):
            hoja.parametros_desde_texto(textos)


def test_cambiar_el_fcas_recalcula_todos_los_apu_de_la_version():
    """RF-57: el FCAS pesa en la mano de obra; con APU solo de material no cambia, asi que se
    mide en un APU con cuadrilla y se compara contra la aritmetica a mano."""
    from core.contracts.apu import LineaManoObra

    base = borrador_bano()
    con_cuadrilla = {
        codigo: replace(c, mano_obra=(LineaManoObra("Obrero", D("1"), D("10")),))
        for codigo, c in base.composiciones.items()
    }
    base = replace(base, composiciones=con_cuadrilla)
    nuevo = replace(base, parametros=ParametrosCosto(fcas=D("7")))

    # mano de obra por unidad = sueldo x (1 + fcas) + bono; solo cambia el FCAS: 10 por 1 de fcas
    delta_cd = D("10") * (D("7") - D("6"))
    cantidad = sum((i.cantidad for i in hoja.items_elaborados(base)), D(0))
    esperado = cantidad * delta_cd * D("1.15") * D("1.10")
    assert abs((_total(nuevo) - _total(base)) - esperado) <= D("0.0001")


# --- plan ---------------------------------------------------------------------------------------


def test_ajustar_plan_conserva_el_reparto_y_agrega_las_partidas_nuevas():
    plan = [
        ("Dia 1", (("A", D("1")),)),
        ("Dia 2", (("B", D("0.5")), ("C", D("1")))),
        ("Dia 3", (("B", D("0.5")),)),
    ]

    ajustado = hoja.ajustar_plan(plan, ["B", "C", "NUEVA"])

    assert ajustado == [
        ("Dia 2", (("B", D("0.5")), ("C", D("1")))),
        ("Dia 3", (("B", D("0.5")),)),
        ("Dia 4", (("NUEVA", D("1")),)),
    ]


def test_ajustar_plan_sin_cambios_devuelve_el_mismo_plan():
    plan = [("Dia 1", (("A", D("1")),)), ("Dia 2", (("B", D("1")),))]

    assert hoja.ajustar_plan(plan, ["A", "B"]) == plan


def test_el_plan_se_ajusta_cuando_el_espacio_agrega_una_partida():
    base = borrador_bano()
    codigos = {
        p.item.codigo_partida for p in hoja.elaborar_borrador(base).elaboracion.presupuesto.partidas
    }
    # un plan guardado que solo conoce la mitad de las partidas
    recortado = replace(base, plan=tuple(p for p in base.plan if p[1][0][0] in sorted(codigos)[:3]))

    resultado = hoja.elaborar_borrador(recortado)

    assert {c for _, reparto in resultado.plan for c, _ in reparto} == codigos
    assert resultado.elaboracion.presupuesto.curva  # la curva se genera sin PlanInvalido


def test_el_plan_se_lee_de_filas_y_cada_partida_debe_sumar_uno():
    etiquetas = ["Dia 1", "Dia 2"]
    filas = [
        {"partida": "A", "Dia 1": "0.4", "Dia 2": "0.6"},
        {"partida": "B", "Dia 1": "1", "Dia 2": "0"},
    ]

    plan = hoja.plan_desde_filas(filas, etiquetas)

    assert plan == [("Dia 1", (("A", D("0.4")), ("B", D("1")))), ("Dia 2", (("A", D("0.6")),))]
    filas[0]["Dia 2"] = "0.5"
    with pytest.raises(hoja.HojaInvalida, match="A.*0.9.*1"):
        hoja.plan_desde_filas(filas, etiquetas)
    filas[0]["Dia 2"] = "-0.4"  # suma 0 con una fraccion negativa
    with pytest.raises(hoja.HojaInvalida, match="A"):
        hoja.plan_desde_filas(filas, etiquetas)


def test_el_plan_como_filas_va_y_vuelve():
    base = borrador_bano()
    codigos = sorted({i.codigo_partida for i in hoja.items_elaborados(base)})

    etiquetas, filas = hoja.plan_como_filas(base.plan, codigos)

    assert [f["partida"] for f in filas] == codigos
    assert hoja.plan_desde_filas(filas, etiquetas) == [
        (e, tuple((c, f) for c, f in reparto)) for e, reparto in base.plan
    ]


# --- punto de equilibrio ------------------------------------------------------------------------


def test_el_punto_de_equilibrio_del_borrador_es_56_60_por_ciento_y_se_ubica_en_la_curva():
    resultado = hoja.elaborar_borrador(borrador_bano())
    pe = resultado.equilibrio

    assert pe.estado is EstadoEquilibrio.CALCULADO
    assert abs(pe.porcentaje - D("56.60")) <= D("0.01")
    assert pe.periodo is not None and pe.periodo.startswith("Dia ")
    assert pe.venta == resultado.elaboracion.presupuesto.total


def test_sin_partidas_el_punto_de_equilibrio_no_aplica():
    vacio = borrador_bano(espacio=Espacio(), composiciones={}, plan=None)

    pe = hoja.elaborar_borrador(vacio).equilibrio

    assert pe.estado is EstadoEquilibrio.NO_APLICABLE
    assert (
        hoja.texto_equilibrio(pe)
        == "El presupuesto no tiene ventas: el punto de equilibrio no aplica."
    )


def test_sin_plan_el_punto_de_equilibrio_no_tiene_ubicacion():
    pe = hoja.elaborar_borrador(borrador_bano(con_plan=False)).equilibrio

    assert pe.estado is EstadoEquilibrio.CALCULADO and pe.periodo is None
    assert "sin curva" in hoja.texto_equilibrio(pe).lower()


def test_un_margen_no_positivo_es_no_existe_con_su_texto():
    # utilidad negativa no la admite el contrato; un margen <= 0 sale de costo directo >= precio:
    # se arma con administracion y utilidad en cero y se verifica el texto del estado calculado
    base = borrador_bano()
    pe = hoja.elaborar_borrador(
        replace(base, parametros=ParametrosCosto(administracion=D(0), utilidad=D(0)))
    ).equilibrio

    assert pe.estado is EstadoEquilibrio.NO_EXISTE
    assert "no existe" in hoja.texto_equilibrio(pe).lower()


# --- cambios entre dos borradores (el RegistroCambio de cada celda) ------------------------------


def test_sin_ediciones_no_hay_cambios():
    base = borrador_bano()

    assert hoja.cambios_entre(base, replace(base)) == []


def test_editar_una_celda_de_metraje_da_exactamente_un_cambio():
    base = borrador_bano()
    filas = hoja.filas_desde_espacio(base.espacio)
    filas["ambientes"][0]["largo"] = "2.5"
    editado = replace(base, espacio=hoja.espacio_desde_filas(filas, base=base.espacio))

    assert hoja.cambios_entre(base, editado) == [
        CambioEditado("metraje", "esp_ambientes:BAN-01", "largo", "2", "2.5")
    ]


def test_agregar_y_quitar_una_fila_de_metraje_son_cambios_de_fila():
    base = borrador_bano(con_plan=False)
    filas = hoja.filas_desde_espacio(base.espacio)
    quitada = filas["puntos"].pop()
    editado = replace(base, espacio=hoja.espacio_desde_filas(filas, base=base.espacio))

    [cambio] = hoja.cambios_entre(base, editado)

    assert (cambio.objeto, cambio.clave, cambio.campo) == (
        "metraje",
        f"esp_puntos:{quitada['id']}",
        "fila",
    )
    assert cambio.valor_nuevo == "" and quitada["nombre"] in cambio.valor_anterior
    assert hoja.cambios_entre(editado, base) == [
        CambioEditado("metraje", f"esp_puntos:{quitada['id']}", "fila", "", cambio.valor_anterior)
    ]


def test_cada_parametro_cambiado_es_un_cambio_de_parametro():
    base = borrador_bano()
    editado = replace(base, parametros=ParametrosCosto(fcas=D("7"), administracion=D("0.18")))

    assert hoja.cambios_entre(base, editado) == [
        CambioEditado("parametro", "fcas", "valor", "6.00", "7"),
        CambioEditado("parametro", "administracion", "valor", "0.15", "0.18"),
    ]


def test_cantidad_de_linea_rendimiento_e_insumo_de_un_apu_son_cambios_de_apu():
    base = borrador_bano()
    apu = base.composiciones["AF-LLAVE"]
    linea = apu.materiales[0]
    nueva = replace(
        apu,
        rendimiento=D("2"),
        materiales=(replace(linea, cantidad=D("3")),),
    )
    editado = replace(base, composiciones={**base.composiciones, "AF-LLAVE": nueva})

    assert hoja.cambios_entre(base, editado) == [
        CambioEditado("apu", "AF-LLAVE", "rendimiento", "1", "2"),
        CambioEditado("apu", "AF-LLAVE|material", "cantidad", "1", "3"),
    ]
    otro = replace(apu, materiales=(replace(linea, descripcion="otro material", precio=D("5")),))
    cambios = hoja.cambios_entre(
        base, replace(base, composiciones={**base.composiciones, "AF-LLAVE": otro})
    )
    assert cambios == [
        CambioEditado("apu", "AF-LLAVE|material", "insumo", "material", "otro material"),
        CambioEditado("apu", "AF-LLAVE|material", "precio", "2", "5"),
    ]


def test_una_cantidad_escrita_es_un_cambio_de_cantidad_con_el_valor_calculado_como_anterior():
    base = borrador_bano()
    items = hoja.items_elaborados(base)
    llave = next(i for i in items if i.codigo_partida == "AF-LLAVE")
    clave = _clave(items, "AF-LLAVE")
    editado = replace(base, cantidades={clave: D("9")})

    esperado = CambioEditado("cantidad", clave, "cantidad", "2", "9")
    assert llave.cantidad == D("2")
    assert hoja.cambios_entre(base, editado) == [esperado]
    # y volver al valor calculado lo registra al reves
    assert hoja.cambios_entre(editado, base) == [
        CambioEditado("cantidad", clave, "cantidad", "9", "2")
    ]


def test_un_cambio_de_plan_es_un_cambio_por_partida_y_periodo():
    base = borrador_bano()
    primero = base.plan[0]
    codigo = primero[1][0][0]
    # la primera partida se reparte mitad en el dia 1 y mitad en el dia 2
    plan = list(base.plan)
    plan[0] = (primero[0], ((codigo, D("0.5")),))
    segundo = plan[1]
    plan[1] = (segundo[0], ((codigo, D("0.5")), *segundo[1]))
    editado = replace(base, plan=tuple(plan))

    assert hoja.cambios_entre(base, editado) == [
        CambioEditado("plan", codigo, primero[0], "1", "0.5"),
        CambioEditado("plan", codigo, segundo[0], "0", "0.5"),
    ]


# --- edicion del APU en la copia de la version (DA-SF-7) -----------------------------------------


def _apu_con_tres_grupos():
    from core.contracts.apu import LineaEquipo, LineaManoObra, LineaMaterial

    return replace(
        borrador_bano().composiciones["AF-LLAVE"],
        materiales=(
            LineaMaterial("Llave", "pza", D("1"), D("10")),
            LineaMaterial("Cinta", "m", D("0.5"), D("2")),
        ),
        equipos=(LineaEquipo("Herramienta", D("2"), D("3"), D("0.03")),),
        mano_obra=(LineaManoObra("Plomero", D("1"), D("20")),),
    )


def test_las_cantidades_de_linea_se_leen_de_las_tres_tablas_y_el_resto_no_se_toca():
    apu = _apu_con_tres_grupos()
    materiales, equipos, mano = hoja.filas_de_apu(apu)
    materiales[1]["cantidad"] = "0.75"
    equipos[0]["cantidad"] = "4"
    mano[0]["cantidad"] = "2"
    materiales[0]["precio"] = "999"  # una columna no editable: se ignora

    editada = hoja.composicion_con_cantidades(apu, materiales, equipos, mano, "2.5")

    assert editada.rendimiento == D("2.5")
    assert [m.cantidad for m in editada.materiales] == [D("1"), D("0.75")]
    assert editada.equipos[0].cantidad == D("4") and editada.mano_obra[0].cantidad == D("2")
    assert editada.materiales[0].precio == D("10")  # el precio de la lista no se edita aqui
    assert editada.materiales[1].descripcion == "Cinta"


@pytest.mark.parametrize(
    ("grupo", "valor", "rendimiento", "mensaje"),
    [
        (0, "mucho", "1", "cantidad"),
        (0, "-1", "1", "cantidad"),
        (0, "1", "0", "rendimiento"),
        (0, "1", "poco", "rendimiento"),
    ],
)
def test_una_cantidad_o_rendimiento_invalido_dice_cual_y_no_cambia_nada(
    grupo, valor, rendimiento, mensaje
):
    apu = _apu_con_tres_grupos()
    tablas = list(hoja.filas_de_apu(apu))
    tablas[grupo][0]["cantidad"] = valor

    with pytest.raises(hoja.HojaInvalida, match=mensaje):
        hoja.composicion_con_cantidades(apu, *tablas, rendimiento)


def test_un_cambio_de_filas_distinto_en_numero_se_rechaza():
    apu = _apu_con_tres_grupos()
    materiales, equipos, mano = hoja.filas_de_apu(apu)

    with pytest.raises(hoja.HojaInvalida, match="lineas"):
        hoja.composicion_con_cantidades(apu, materiales[:1], equipos, mano, "1")


def test_cambiar_el_insumo_de_una_linea_toma_la_descripcion_la_unidad_y_el_precio_de_la_lista():
    apu = _apu_con_tres_grupos()
    candidato = hoja.FilaInsumo("MT-9", "Llave de bola 1/2", "pza", D("12.50"))

    nueva = hoja.cambiar_insumo(apu, "material", 0, candidato)

    assert (nueva.materiales[0].descripcion, nueva.materiales[0].unidad) == (
        "Llave de bola 1/2",
        "pieza",  # el contrato normaliza la unidad: pza -> pieza
    )
    assert nueva.materiales[0].precio == D("12.50") and nueva.materiales[0].cantidad == D("1")
    assert nueva.materiales[1] == apu.materiales[1]
    assert nueva.equipos == apu.equipos
    mano = hoja.cambiar_insumo(
        apu, "mano_obra", 0, hoja.FilaInsumo("MO-1", "Ayudante", "dia", D("8"))
    )
    assert (mano.mano_obra[0].descripcion, mano.mano_obra[0].sueldo) == ("Ayudante", D("8"))
    equipo = hoja.cambiar_insumo(
        apu, "equipo", 0, hoja.FilaInsumo("EQ-1", "Taladro", "dia", D("9"))
    )
    assert (equipo.equipos[0].descripcion, equipo.equipos[0].precio) == ("Taladro", D("9"))
    assert equipo.equipos[0].depreciacion == D("0.03")  # la depreciacion es de la linea


def test_cambiar_el_insumo_de_una_linea_que_no_existe_o_de_un_tipo_ajeno_se_rechaza():
    apu = _apu_con_tres_grupos()
    candidato = hoja.FilaInsumo("MT-9", "x", "pza", D("1"))

    with pytest.raises(hoja.HojaInvalida, match="linea"):
        hoja.cambiar_insumo(apu, "material", 7, candidato)
    with pytest.raises(hoja.HojaInvalida, match="tipo"):
        hoja.cambiar_insumo(apu, "maquinaria", 0, candidato)


def test_crear_el_plan_secuencial_da_una_curva_que_cierra_en_el_total():
    sin_plan = borrador_bano(con_plan=False)

    con_plan = hoja.con_plan_secuencial(sin_plan)

    assert con_plan.plan is not None
    resultado = hoja.elaborar_borrador(con_plan)
    assert (
        resultado.elaboracion.presupuesto.curva[-1].acumulado
        == resultado.elaboracion.presupuesto.total
    )
    codigos = {i.codigo_partida for i in hoja.items_elaborados(con_plan)}
    assert [r[0][0] for _, r in con_plan.plan] == sorted(
        codigos, key=lambda c: [i.codigo_partida for i in hoja.items_elaborados(con_plan)].index(c)
    )


# --- tablas calculadas de la pantalla ------------------------------------------------------------


def test_las_filas_del_presupuesto_llevan_clave_cantidad_pu_total_y_estado():
    base = borrador_bano()
    items = hoja.items_elaborados(base)
    clave = _clave(items, "AF-LLAVE")
    resultado = hoja.elaborar_borrador(replace(base, cantidades={clave: D("5")}))

    filas = hoja.filas_del_presupuesto(resultado)

    assert [f["clave"] for f in filas] == hoja.claves_de_items(resultado.todos)
    llave = next(f for f in filas if f["clave"] == clave)
    assert llave["partida"] == "AF-LLAVE" and llave["cantidad"] == "5"
    assert llave["pu"] == "2.53" and llave["total"] == "12.65"  # 5 x 2,53 a mano
    assert "fijada a mano" in llave["estado"]
    otra = next(f for f in filas if f["partida"] != "AF-LLAVE")
    assert otra["estado"] == hoja.TEXTO_OK


def test_una_partida_sin_apu_sale_pendiente_y_sin_pu():
    base = borrador_bano()
    sin_apu = replace(
        base, composiciones={k: v for k, v in base.composiciones.items() if k != "AF-LLAVE"}
    )

    filas = hoja.filas_del_presupuesto(hoja.elaborar_borrador(sin_apu))

    llave = next(f for f in filas if f["partida"] == "AF-LLAVE")
    assert llave["pu"] == "" and llave["total"] == "" and "PENDIENTE" in llave["estado"]


def test_las_filas_de_la_curva_cierran_en_el_total_con_su_porcentaje():
    resultado = hoja.elaborar_borrador(borrador_bano())
    presupuesto = resultado.elaboracion.presupuesto

    filas = hoja.filas_de_curva(presupuesto)

    assert len(filas) == len(presupuesto.curva)
    assert filas[-1]["acumulado"] == f"{presupuesto.total:.2f}"
    assert filas[-1]["porcentaje"] == "100.00"
    assert all(" [" not in f["periodo"] for f in filas)  # los codigos del periodo no se muestran


# --- Foco de revision FR-1 a FR-3 por la hoja (FR-4 y FR-5 estan en test_hoja_versiones) ----------


def _longitud_de_tuberia(borrador) -> Decimal:
    return sum(
        (
            i.cantidad
            for i in hoja.items_elaborados(borrador)
            if i.codigo_partida.startswith("AF-TUB-PVC")
        ),
        D(0),
    )


def test_fr1_borrar_todas_las_filas_deja_la_hoja_vacia_y_no_falla():
    base = borrador_bano()
    filas = {tabla: [] for tabla in hoja.COLUMNAS}

    vacio = replace(base, espacio=hoja.espacio_desde_filas(filas, base=base.espacio))
    resultado = hoja.elaborar_borrador(vacio)

    assert resultado.items == [] and resultado.estado == {}
    assert resultado.elaboracion.presupuesto.total == 0
    assert resultado.equilibrio.estado is EstadoEquilibrio.NO_APLICABLE


def test_fr2_una_fuente_sin_puntos_y_un_punto_sin_recorrido_declarado_no_dividen_por_cero():
    base = borrador_bano()
    filas = hoja.filas_desde_espacio(base.espacio)
    sin_puntos = {**filas, "puntos": [], "tramos": []}
    solo_fuente = replace(base, espacio=hoja.espacio_desde_filas(sin_puntos, base=base.espacio))
    sin_tramos = {**filas, "tramos": []}  # los puntos pierden su recorrido declarado
    propuestos = replace(base, espacio=hoja.espacio_desde_filas(sin_tramos, base=base.espacio))

    assert _longitud_de_tuberia(solo_fuente) == 0
    assert hoja.elaborar_borrador(solo_fuente).elaboracion.presupuesto.total >= 0
    assert _longitud_de_tuberia(propuestos) > 0  # la hoja propone el recorrido
    assert all(
        i.cantidad > 0 for i in hoja.items_elaborados(propuestos)
    )  # sin tramos de largo cero


def test_fr3_dos_recorridos_con_un_tramo_parcial_colineal_no_cuentan_la_tuberia_dos_veces():
    """P1 sube 2,5, cruza el techo 1,5 y baja 1,9 (5,9 m); P2 sube lo mismo, cruza el techo
    1,0
    (dentro del tramo de P1), 1,5 mas y baja 1,3 (6,3 m). Unido: 2,5 + 1,5 + 1,9 + 1,5 + 1,3
    = 8,7 m, mas el desperdicio de 10 % de la memoria del bano."""
    base = borrador_bano(con_plan=False)
    filas = hoja.filas_desde_espacio(base.espacio)
    filas["tramos"] = [t for t in filas["tramos"] if t["recorrido_id"] == "R-P1"]
    p2 = [
        ("1", "pared", "si", "0,0,0; 0,0,2.5"),
        ("2", "techo", "no", "0,0,2.5; 1,0,2.5"),
        ("3", "techo", "no", "1,0,2.5; 1,1.5,2.5"),
        ("4", "pared", "si", "1,1.5,2.5; 1,1.5,1.2"),
    ]
    filas["tramos"] += [
        {
            "recorrido_id": "R-P2",
            "punto_id": "P2",
            "circuito_id": "",
            "orden": orden,
            "superficie": superficie,
            "empotrado": empotrado,
            "pendiente": "",
            "vertices": vertices,
        }
        for orden, superficie, empotrado, vertices in p2
    ]
    espacio = hoja.espacio_desde_filas(filas, base=base.espacio)

    unido = _longitud_de_tuberia(replace(base, espacio=espacio))

    assert abs(unido - D("8.7") * D("1.10")) <= D(
        "0.001"
    )  # y no 12,2 x 1,10 de sumar cada recorrido aparte
