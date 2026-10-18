"""La prueba real del asistente audita como el producto: con R17 (tarea 1.7, ruling 1.7-d).

No abre la red: solo se llama a la funcion con que el script audita cada propuesta.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from adapters.espacio.conexion import ConexionDeCadaPunto
from adapters.espacio.modelo import (
    Ambiente,
    Coord,
    Espacio,
    Especialidad,
    Punto,
    SuperficiePunto,
    TipoPunto,
)
from adapters.espacio.origen import OrigenMedida, TipoOrigen
from scripts import prueba_real_asistente as script
from ui import hoja

D = Decimal
LEV = OrigenMedida(
    id="LEV", tipo=TipoOrigen.LEVANTAMIENTO, referencia={"fecha": "2026-10-01", "responsable": "EP"}
)
SIN_FUENTE = Espacio(
    origenes=(LEV,),
    ambientes=(Ambiente("A", "Bano", D("0"), D("0"), D("3"), D("2"), D("2.5"), "LEV"),),
    puntos=(
        Punto(
            id="P2",
            nombre="lavamanos",
            especialidad=Especialidad.AGUA,
            tipo=TipoPunto.AGUA_FRIA,
            ambiente_id="A",
            superficie=SuperficiePunto.PARED,
            posicion=Coord(D("2"), D("0"), D("0.6")),
            origen_id="LEV",
        ),
    ),
)


def test_el_auditor_de_la_prueba_real_trae_r17_del_espacio_que_recibe():
    viejo = ConexionDeCadaPunto(Espacio())  # un R17 ajeno no tapa el del espacio auditado
    borrador = hoja.Borrador(fecha=date(2026, 10, 18), espacio=SIN_FUENTE, reglas_extra=(viejo,))
    informe = script.auditar(borrador)
    avisos = [h for h in informe.hallazgos if h.regla == "R17"]
    assert [h.origen_ids for h in avisos] == [("esp_puntos:P2",)]
