"""Informe de importacion y reimportacion por origen (spec §6.6, RF-50, RF-51, tarea 5.4).

`ResultadoImportacion` junta las filas que un plano crea en la hoja y el informe tipado de lo que no
creo. `fusionar` reimporta el mismo plano: empareja por el origen de la fila (handle o GlobalId),
actualiza, agrega y MARCA las que desaparecieron (no las borra). Sin ezdxf ni ifcopenshell: las
filas se arman a mano.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from adapters.espacio import (
    Ambiente,
    Circuito,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    ModoRecorrido,
    OrigenMedida,
    Punto,
    Recorrido,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoOrigen,
    TipoPunto,
    Tramo,
)
from adapters.espacio.planos.informe import (
    EstadoImportacion,
    ItemInforme,
    ResultadoImportacion,
    TipoItem,
    cargar_alturas,
    fusionar,
)
from adapters.espacio.reglas import (
    ALTO_PROVISIONAL,
    ORIGEN_ALTURA_PENDIENTE,
    ORIGEN_DESAPARECIDA,
    OrigenDeLaMedida,
)
from core.contracts import Severidad
from core.contracts.presupuesto import Presupuesto

D = Decimal
VACIO = Presupuesto(codigo="X", fecha=date(2026, 1, 1), moneda="USD", partidas=())


def origen(handle: str, archivo: str = "a.dxf", capa: str = "AMBIENTES", *extra) -> OrigenMedida:
    referencia = {"archivo": archivo, "capa": capa, "handle": handle}
    referencia.update(dict(extra))
    return OrigenMedida(id=f"DXF-{handle}", tipo=TipoOrigen.DXF, referencia=referencia)


def ambiente(id_="SALA", handle="A1", ancho="3", alto=ALTO_PROVISIONAL, pendiente=True):
    extra = (ORIGEN_ALTURA_PENDIENTE,) if pendiente else ()
    o = origen(handle, "a.dxf", "AMBIENTES", *extra)
    a = Ambiente(
        id=id_, nombre=id_, x0=D(0), y0=D(0), largo=D(4), ancho=D(ancho), alto=alto, origen_id=o.id
    )
    return a, o


def fuente(id_="F1", handle="F1H", ambiente_id="SALA", x="0"):
    o = origen(handle, "a.dxf", "FTE-AGUA")
    f = Fuente(
        id=id_,
        especialidad=Especialidad.AGUA,
        tipo=TipoFuente.MONTANTE_AGUA,
        ambiente_id=ambiente_id,
        posicion=Coord(D(x), D(0), D(0)),
        origen_id=o.id,
    )
    return f, o


def punto(id_="P1", handle="P1H", ambiente_id="SALA", fuente_id="F1", y="1"):
    o = origen(handle, "a.dxf", "PTO-AGUA")
    p = Punto(
        id=id_,
        nombre=id_,
        especialidad=Especialidad.AGUA,
        tipo=TipoPunto.AGUA_FRIA,
        ambiente_id=ambiente_id,
        superficie=SuperficiePunto.PARED,
        posicion=Coord(D(1), D(y), D("0.6")),
        origen_id=o.id,
        fuente_id=fuente_id,
        especificaciones=(("diametro", '1/2"'),),
    )
    return p, o


def resultado(*filas, archivo="a.dxf", formato="dxf", informe=(), circuitos=(), recorridos=()):
    """Resultado con las filas `(fila, origen)` dadas, en su tabla segun el tipo de la fila."""
    tablas: dict[type, list] = {Ambiente: [], Fuente: [], Punto: []}
    origenes = []
    for fila, o in filas:
        tablas[type(fila)].append(fila)
        origenes.append(o)
    return ResultadoImportacion(
        formato=formato,
        archivo=archivo,
        origenes=tuple(origenes),
        ambientes=tuple(tablas[Ambiente]),
        fuentes=tuple(tablas[Fuente]),
        puntos=tuple(tablas[Punto]),
        circuitos=tuple(circuitos),
        recorridos=tuple(recorridos),
        informe=tuple(informe),
    )


def basico(**cambios) -> ResultadoImportacion:
    r = resultado(ambiente(), fuente(), punto())
    return replace(r, **cambios) if cambios else r


# --- el resultado ----------


def test_el_resultado_cuenta_filas_por_tabla_e_items_por_tipo():
    items = (
        ItemInforme(TipoItem.IMPORTADO, "esp_ambientes", "A1", "SALA", "importado"),
        ItemInforme(TipoItem.IMPORTADO, "esp_puntos", "P1H", "P1", "importado"),
        ItemInforme(TipoItem.NO_RECONOCIDO, "", "ZZ", "", "capa ajena"),
        ItemInforme(TipoItem.APROXIMADO, "esp_ambientes", "A1", "SALA", "caja envolvente"),
        ItemInforme(TipoItem.PENDIENTE, "esp_ambientes", "A1", "SALA", "altura pendiente"),
    )
    r = basico(informe=items)
    assert r.estado is EstadoImportacion.IMPORTADA
    assert r.filas == {
        "esp_origenes": 3,
        "esp_ambientes": 1,
        "esp_fuentes": 1,
        "esp_circuitos": 0,
        "esp_puntos": 1,
        "esp_recorridos": 0,
    }
    assert r.conteos == {
        TipoItem.IMPORTADO: 2,
        TipoItem.NO_RECONOCIDO: 1,
        TipoItem.APROXIMADO: 1,
        TipoItem.PENDIENTE: 1,
        TipoItem.DESAPARECIDO: 0,
        TipoItem.OMITIDO: 0,
    }


def test_el_resultado_se_convierte_en_un_espacio_consistente():
    espacio = basico().espacio()
    assert [a.id for a in espacio.ambientes] == ["SALA"]
    assert [p.id for p in espacio.puntos] == ["P1"]
    assert len(espacio.origenes) == 3


def test_un_resultado_detenido_o_rechazado_no_trae_filas():
    for estado in (EstadoImportacion.DETENIDA, EstadoImportacion.RECHAZADA):
        r = ResultadoImportacion(formato="dxf", archivo="a.dxf", estado=estado, mensaje="motivo")
        assert r.espacio().vacio
        assert all(n == 0 for n in r.filas.values())


# --- altura de los ambientes ----------


def test_cargar_alturas_cambia_el_alto_y_quita_la_marca_de_pendiente():
    pendiente = ItemInforme(TipoItem.PENDIENTE, "esp_ambientes", "A1", "SALA", "altura pendiente")
    otro = ItemInforme(TipoItem.PENDIENTE, "esp_puntos", "P1H", "P1", "sin fuente")
    r = basico(informe=(pendiente, otro))
    cargado = cargar_alturas(r, {"SALA": D("2.8")})
    assert cargado.ambientes[0].alto == D("2.8")
    marca = dict(cargado.origenes_por_id["DXF-A1"].referencia)
    assert ORIGEN_ALTURA_PENDIENTE[0] not in marca
    assert cargado.informe == (otro,)  # solo cae el pendiente de ese ambiente
    assert r.ambientes[0].alto == ALTO_PROVISIONAL  # el original no se muta


def test_cargar_alturas_ignora_ambientes_que_no_existen():
    assert cargar_alturas(basico(), {"NO-EXISTE": D(3)}).ambientes == basico().ambientes


def test_r8_marca_la_altura_pendiente_del_ambiente_importado():
    hallazgos = OrigenDeLaMedida(basico().espacio()).evaluar(VACIO)
    pendientes = [h for h in hallazgos if "altura pendiente" in h.descripcion]
    assert [(h.severidad, h.origen_ids) for h in pendientes] == [
        (Severidad.ADVERTENCIA, ("esp_ambientes:SALA",))
    ]


def test_r8_no_marca_pendiente_si_la_altura_ya_no_es_la_provisional():
    r = basico()
    espacio = replace(r, ambientes=(replace(r.ambientes[0], alto=D("2.8")),)).espacio()
    hallazgos = OrigenDeLaMedida(espacio).evaluar(VACIO)
    assert not [h for h in hallazgos if "altura pendiente" in h.descripcion]


def test_r8_marca_la_fila_desaparecida_del_plano():
    r = basico()
    marcado = origen("P1H", "a.dxf", "PTO-AGUA", ORIGEN_DESAPARECIDA)
    espacio = replace(
        r, origenes=tuple(marcado if o.id == marcado.id else o for o in r.origenes)
    ).espacio()
    hallazgos = [h for h in OrigenDeLaMedida(espacio).evaluar(VACIO) if "plano" in h.descripcion]
    assert [(h.severidad, h.origen_ids) for h in hallazgos] == [
        (Severidad.ADVERTENCIA, ("esp_puntos:P1",))
    ]


# --- reimportacion (fusionar) ----------


def test_fusionar_en_un_espacio_vacio_agrega_todo_y_lo_informa():
    r = basico()
    espacio, informe = fusionar(Espacio(), r)
    assert espacio == r.espacio()
    agregadas = [i for i in informe if i.tipo is TipoItem.IMPORTADO and "agregada" in i.mensaje]
    assert len(agregadas) == 3


def test_reimportar_el_mismo_plano_no_cambia_nada():
    r = basico()
    primero, _ = fusionar(Espacio(), r)
    segundo, informe = fusionar(primero, r)
    assert segundo == primero
    assert not [i for i in informe if i.tipo in (TipoItem.DESAPARECIDO, TipoItem.OMITIDO)]


def test_reimportar_actualiza_la_fila_con_el_mismo_handle_y_conserva_su_id():
    primero, _ = fusionar(Espacio(), basico())
    movido = punto(id_="OTRO-ID", handle="P1H", y="1.25")  # mismo handle, otra posicion y otro id
    r2 = resultado(ambiente(), fuente(), movido)
    espacio, informe = fusionar(primero, r2)
    assert [p.id for p in espacio.puntos] == ["P1"]  # el id estable de la hoja
    assert espacio.puntos[0].posicion.y == D("1.25")
    assert any(i.tipo is TipoItem.IMPORTADO and "actualizada" in i.mensaje for i in informe)


def test_reimportar_conserva_la_altura_cargada_si_el_plano_no_la_trae():
    primero, _ = fusionar(Espacio(), cargar_alturas(basico(), {"SALA": D("2.8")}))
    espacio, _ = fusionar(primero, basico())  # el plano sigue sin altura (provisional)
    assert espacio.ambientes[0].alto == D("2.8")
    marca = dict(next(o for o in espacio.origenes if o.id == "DXF-A1").referencia)
    assert "altura" not in marca  # la altura ya estaba cargada: no vuelve a quedar pendiente


def test_reimportar_agrega_la_fila_nueva():
    primero, _ = fusionar(Espacio(), basico())
    r2 = resultado(ambiente(), fuente(), punto(), punto(id_="P2", handle="P2H", y="2"))
    espacio, _ = fusionar(primero, r2)
    assert [p.id for p in espacio.puntos] == ["P1", "P2"]


def test_reimportar_marca_la_fila_desaparecida_y_no_la_borra():
    primero, _ = fusionar(Espacio(), resultado(ambiente(), fuente(), punto(), punto("P2", "P2H")))
    r2 = resultado(ambiente(), fuente(), punto())  # P2 ya no esta en el plano
    espacio, informe = fusionar(primero, r2)
    assert [p.id for p in espacio.puntos] == ["P1", "P2"]  # no se borra
    marca = dict(next(o for o in espacio.origenes if o.id == "DXF-P2H").referencia)
    assert marca[ORIGEN_DESAPARECIDA[0]] == ORIGEN_DESAPARECIDA[1]
    desaparecidos = [i for i in informe if i.tipo is TipoItem.DESAPARECIDO]
    assert [(i.tabla, i.fila) for i in desaparecidos] == [("esp_puntos", "P2")]


def test_una_fila_desaparecida_que_vuelve_pierde_la_marca():
    base = resultado(ambiente(), fuente(), punto(), punto("P2", "P2H"))
    sin_p2, _ = fusionar(Espacio(), base)
    sin_p2, _ = fusionar(sin_p2, resultado(ambiente(), fuente(), punto()))
    de_vuelta, _ = fusionar(sin_p2, base)
    marca = dict(next(o for o in de_vuelta.origenes if o.id == "DXF-P2H").referencia)
    assert ORIGEN_DESAPARECIDA[0] not in marca


def test_un_id_en_uso_por_una_fila_ajena_se_omite_con_su_item():
    manual = OrigenMedida(id="LEV", tipo=TipoOrigen.SUPUESTO, referencia={"motivo": "a mano"})
    a, _ = ambiente()
    a = replace(a, origen_id="LEV")
    f, _ = fuente()
    f = replace(f, origen_id="LEV")
    p_manual = replace(punto()[0], origen_id="LEV")  # un P1 de la hoja que no viene del plano
    actual = Espacio(origenes=(manual,), ambientes=(a,), fuentes=(f,), puntos=(p_manual,))
    espacio, informe = fusionar(actual, resultado(ambiente(), fuente(), punto()))
    assert espacio.puntos == actual.puntos  # la fila manual no se toca
    omitidos = [(i.tabla, i.fila) for i in informe if i.tipo is TipoItem.OMITIDO]
    assert ("esp_puntos", "P1") in omitidos


def test_una_fila_que_cita_a_una_omitida_tambien_se_omite():
    manual = OrigenMedida(id="LEV", tipo=TipoOrigen.SUPUESTO, referencia={"motivo": "a mano"})
    otro_sala = replace(ambiente()[0], origen_id="LEV", ancho=D(9))
    actual = Espacio(origenes=(manual,), ambientes=(otro_sala,))
    espacio, informe = fusionar(actual, resultado(ambiente(), fuente(), punto()))
    assert espacio.ambientes == actual.ambientes
    assert espacio.fuentes == () and espacio.puntos == ()
    assert {i.fila for i in informe if i.tipo is TipoItem.OMITIDO} == {"SALA", "F1", "P1"}


def test_otro_archivo_es_otro_plano_y_no_marca_desaparecidas_las_filas_del_primero():
    primero, _ = fusionar(Espacio(), basico())
    otro = resultado(
        (
            replace(ambiente("PATIO", "A9")[0], origen_id="DXF-A9"),
            origen("A9", "otro.dxf", "AMBIENTES"),
        ),
        archivo="otro.dxf",
    )
    espacio, informe = fusionar(primero, otro)
    assert {a.id for a in espacio.ambientes} == {"SALA", "PATIO"}
    assert not [i for i in informe if i.tipo is TipoItem.DESAPARECIDO]


def test_fusionar_un_resultado_detenido_deja_el_espacio_igual():
    actual, _ = fusionar(Espacio(), basico())
    detenido = ResultadoImportacion(
        formato="dxf", archivo="a.dxf", estado=EstadoImportacion.DETENIDA, mensaje="falta unidad"
    )
    espacio, informe = fusionar(actual, detenido)
    assert espacio == actual
    assert [i.mensaje for i in informe if "falta unidad" in i.mensaje]


def test_los_circuitos_existentes_se_conservan_y_los_nuevos_se_agregan():
    circuito = Circuito(
        id="C1", tablero="F1", numero=1, conductores=(1, 1, 1), calibre="12 AWG", puntos_maximos=6
    )
    editado = replace(circuito, puntos_maximos=4)
    actual, _ = fusionar(Espacio(), basico())
    actual = replace(actual, circuitos=(editado,))
    nuevo = replace(circuito, id="C2", numero=2)
    espacio, _ = fusionar(actual, replace(basico(), circuitos=(circuito, nuevo)))
    assert [(c.id, c.puntos_maximos) for c in espacio.circuitos] == [("C1", 4), ("C2", 6)]


def test_un_recorrido_declarado_se_actualiza_por_id_y_se_informa_si_desaparece():
    def rec(id_, y):
        return Recorrido(
            id=id_,
            modo=ModoRecorrido.DECLARADO,
            punto_id="P1",
            tramos=(
                Tramo(0, SuperficieTramo.TECHO, (Coord(D(0), D(0), D(2)), Coord(D(1), D(y), D(2)))),
            ),
        )

    r1 = replace(basico(), recorridos=(rec("REC-1", 0), rec("REC-2", 0)))
    primero, _ = fusionar(Espacio(), r1)
    r2 = replace(basico(), recorridos=(rec("REC-1", 1),))
    espacio, informe = fusionar(primero, r2)
    assert [r.id for r in espacio.recorridos] == ["REC-1", "REC-2"]  # no se borra
    assert espacio.recorridos[0].tramos[0].vertices[1].y == D(1)
    assert [(i.tabla, i.fila) for i in informe if i.tipo is TipoItem.DESAPARECIDO] == [
        ("esp_recorridos", "REC-2")
    ]


def test_la_fusion_no_deja_referencias_colgadas():
    primero, _ = fusionar(Espacio(), basico())
    r2 = resultado(ambiente(ancho="5"), fuente(x="1"), punto(y="2"), punto("P9", "P9H"))
    espacio, _ = fusionar(primero, r2)
    ids = {a.id for a in espacio.ambientes}
    assert all(p.ambiente_id in ids for p in espacio.puntos)
    assert espacio.validar() == []


@pytest.mark.parametrize("campo", ["formato", "archivo"])
def test_el_resultado_es_inmutable(campo):
    with pytest.raises(AttributeError):
        setattr(basico(), campo, "x")
