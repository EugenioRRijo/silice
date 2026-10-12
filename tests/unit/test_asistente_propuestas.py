"""Propuestas pendientes y su aplicacion al borrador (S4 §3.1, §5.4, RF-92; plan 0.9.0, tarea 7)."""

from __future__ import annotations

from decimal import Decimal

from adapters.espacio import ModoRecorrido, TipoOrigen
from asistente.propuestas import (
    EstadoPropuesta,
    Pendientes,
    TipoPropuesta,
    aplicar,
)
from asistente.validacion import Propuesta, Rechazo, validar_llamada
from core.contracts import Severidad
from core.contracts.item_computo import OrigenTipo
from tests.fixtures.asistente_pedidos import AMBIENTE, FECHA, ORIGEN, catalogo, contexto
from ui import hoja
from ui.hoja import Borrador

TEXTO = "Bano de 2,4 x 1,5 m con alto de 2,5 m, con un lavamanos a 60 cm del piso. Cantidad 2."
FUENTE = {
    "id": "F1",
    "especialidad": "agua",
    "tipo": "montante_agua",
    "ambiente_id": "BAN-01",
    "x": "0",
    "y": "0",
    "z": "0",
    "citas": [],
    "supuestos": [{"campo": c, "motivo": "montante en la esquina"} for c in "xyz"],
}
PUNTO = {
    "id": "P1",
    "nombre": "lavamanos",
    "especialidad": "agua",
    "tipo": "agua_fria",
    "ambiente_id": "BAN-01",
    "superficie": "pared",
    "x": "1.5",
    "y": "0",
    "z": "0.6",
    "fuente_id": "F1",
    "circuito_id": None,
    "especificaciones": [
        {"clave": "diametro", "valor": '1/2"'},
        {"clave": "llave_de_paso", "valor": "si"},
    ],
    "citas": [{"campo": "z", "texto": "60 cm"}],
    "supuestos": [{"campo": "x", "motivo": "centro"}, {"campo": "y", "motivo": "pared"}],
}
RECORRIDO = {
    "punto_id": "P1",
    "circuito_id": None,
    "modo": "propuesto",
    "tramos": None,
    "citas": [],
    "supuestos": [],
}
PARTIDA = {
    "codigo": "AF-SALIDA",
    "unidad": "punto",
    "cantidad": "2",
    "citas": [{"campo": "cantidad", "texto": "Cantidad 2"}],
    "supuestos": [],
}


def _pendientes() -> Pendientes:
    pendientes = Pendientes.vacia()
    for nombre, argumentos in [
        ("proponer_ambiente", AMBIENTE),
        ("proponer_fuente", FUENTE),
        ("proponer_punto", PUNTO),
        ("proponer_recorrido", RECORRIDO),
        ("proponer_partida", PARTIDA),
    ]:
        resultado = validar_llamada(
            nombre,
            argumentos,
            contexto(
                pendientes=pendientes.propuestas,
                textos=(TEXTO,),
                siguiente_id=pendientes.siguiente_id(),
            ),
        )
        assert isinstance(resultado, Propuesta), (nombre, resultado)
        pendientes.agregar(resultado)
    return pendientes


def test_rechazar_todo_deja_el_borrador_identico():
    vacio = Borrador(fecha=FECHA)
    pendientes = _pendientes()
    for propuesta in pendientes.vigentes():
        assert pendientes.retirar(propuesta.id)
    assert not pendientes.vigentes()
    assert aplicar(vacio, pendientes.aceptadas(), ORIGEN, catalogo()) == vacio


def test_aceptar_aplica_exactamente_las_filas_esperadas_con_origen_ia():
    borrador = aplicar(Borrador(fecha=FECHA), _pendientes().propuestas, ORIGEN, catalogo())
    espacio = borrador.espacio
    assert [o.id for o in espacio.origenes] == ["IA-7-P1", "IA-7-P2", "IA-7-P3"]
    assert {o.tipo for o in espacio.origenes} == {TipoOrigen.IA}
    assert dict(espacio.origenes[0].referencia) == {
        "proveedor": "guionado",
        "modelo": "guion-1",
        "sesion": "7",
        "propuesta": "P1",
        "supuesto.x0": "esquina del bano en el origen",
        "supuesto.y0": "esquina del bano en el origen",
    }
    assert [a.id for a in espacio.ambientes] == ["BAN-01"]
    assert espacio.ambientes[0].largo == Decimal("2.4")
    assert [(r.id, r.modo, r.punto_id) for r in espacio.recorridos] == [
        ("R-P1", ModoRecorrido.PROPUESTO, "P1")
    ]
    (item,) = borrador.items_base
    assert (item.codigo_partida, item.cantidad, item.origen_id, item.origen_tipo) == (
        "AF-SALIDA",
        Decimal("2"),
        "ia:7:P5",
        OrigenTipo.MANUAL,
    )
    assert not item.parametros and not item.especificaciones  # DA-SF-8


def test_el_auditor_marca_exactamente_los_siete_supuestos_de_la_ia():
    borrador = aplicar(Borrador(fecha=FECHA), _pendientes().propuestas, ORIGEN, catalogo())
    r8 = [
        h for h in hoja.elaborar_borrador(borrador).elaboracion.informe.hallazgos if h.regla == "R8"
    ]
    assert {(h.severidad, h.descripcion) for h in r8} == {
        (
            Severidad.ADVERTENCIA,
            f"{quien}: alto supuesto por la IA: {campo} ({motivo}) (origen IA-7-{p})",
        )
        for quien, campo, motivo, p in [
            ("ambiente BAN-01", "x0", "esquina del bano en el origen", "P1"),
            ("ambiente BAN-01", "y0", "esquina del bano en el origen", "P1"),
            ("fuente F1", "x", "montante en la esquina", "P2"),
            ("fuente F1", "y", "montante en la esquina", "P2"),
            ("fuente F1", "z", "montante en la esquina", "P2"),
            ("punto P1", "x", "centro", "P3"),
            ("punto P1", "y", "pared", "P3"),
        ]
    }


def test_un_motivo_con_punto_y_coma_o_igual_no_rompe_la_referencia():
    ambiente = {
        **AMBIENTE,
        "supuestos": [{"campo": "x0", "motivo": "a=b; c"}, {"campo": "y0", "motivo": "ok"}],
    }
    resultado = validar_llamada("proponer_ambiente", ambiente, contexto())
    assert isinstance(resultado, Propuesta)
    borrador = aplicar(Borrador(fecha=FECHA), [resultado], ORIGEN, catalogo())
    assert dict(borrador.espacio.origenes[0].referencia)["supuesto.x0"] == "a:b, c"


def test_retirar_marca_rechazada_y_solo_una_vez():
    pendientes = _pendientes()
    assert pendientes.retirar("P2") and not pendientes.retirar("P2")
    assert pendientes.buscar("P2").estado is EstadoPropuesta.RECHAZADA
    assert [p.id for p in pendientes.vigentes()] == ["P1", "P3", "P4", "P5"]


def test_una_sin_partida_no_cambia_el_borrador_y_un_id_nuevo_sigue_la_cuenta():
    pendientes = Pendientes.vacia()
    r = validar_llamada(
        "declarar_sin_partida",
        {"necesidad": "cuadro de transferencia"},
        contexto(siguiente_id=pendientes.siguiente_id()),
    )
    assert isinstance(r, Propuesta) and r.tipo is TipoPropuesta.SIN_PARTIDA
    pendientes.agregar(r)
    assert pendientes.siguiente_id() == "P2"
    vacio = Borrador(fecha=FECHA)
    assert aplicar(vacio, pendientes.propuestas, ORIGEN, catalogo()) == vacio
    assert not isinstance(r, Rechazo)
