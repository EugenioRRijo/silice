"""R17 en la reauditoria de un paquete con anexo de espacio (tarea 1.7, revision de arquitectura).

Un paquete guardado desde la hoja declara sus avisos R17 (el canonico exporta los hallazgos
guardados). Si la reauditoria no corriera R17, esos avisos caerian en `ya_no` y la pagina Revisar
diria «Los declaro y ya no aparecen»: una senal falsa de correccion. Oraculo: con el punto aun sin
fuente el aviso es comun; con el punto corregido, si cae en `ya_no`.
"""

from __future__ import annotations

import copy
from datetime import date
from decimal import Decimal

from adapters.espacio.modelo import (
    Ambiente,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    Punto,
    SuperficiePunto,
    TipoFuente,
    TipoPunto,
)
from adapters.espacio.origen import OrigenMedida, TipoOrigen
from adapters.espacio.serie import espacio_a_objeto
from auditoria import reauditoria
from core.budget.canonico import json_canonico
from core.contracts.verificacion import Hallazgo, Severidad
from tests.fixtures.canonico.ejemplo_v1 import EJEMPLO_V1

D = Decimal
FECHA = date(2026, 11, 10)
LEV = OrigenMedida(
    id="LEV", tipo=TipoOrigen.LEVANTAMIENTO, referencia={"fecha": "2026-10-01", "responsable": "EP"}
)
AVISO = Hallazgo(
    regla="R17",
    severidad=Severidad.ADVERTENCIA,
    descripcion=(
        "El punto P2 (lavamanos) no tiene fuente: el presupuesto no incluye cómo le llega el "
        "agua. Asígnele su acometida o montante, o déjelo así si es a propósito."
    ),
    origen_ids=("esp_puntos:P2",),
)


def _espacio(fuente_id: str | None) -> bytes:
    punto = Punto(
        id="P2",
        nombre="lavamanos",
        especialidad=Especialidad.AGUA,
        tipo=TipoPunto.AGUA_FRIA,
        ambiente_id="A",
        superficie=SuperficiePunto.PARED,
        posicion=Coord(D("2"), D("0"), D("0.6")),
        origen_id="LEV",
        fuente_id=fuente_id,
    )
    espacio = Espacio(
        origenes=(LEV,),
        ambientes=(Ambiente("A", "Bano", D("0"), D("0"), D("3"), D("2"), D("2.5"), "LEV"),),
        fuentes=(
            Fuente(
                "F",
                Especialidad.AGUA,
                TipoFuente.ACOMETIDA_AGUA,
                "A",
                Coord(D(0), D(0), D("0.5")),
                "LEV",
            ),
        ),
        puntos=(punto,),
    )
    return json_canonico(espacio_a_objeto(espacio))


def _documento_que_declara_el_aviso():
    objeto = copy.deepcopy(EJEMPLO_V1)
    objeto["hallazgos"] = [
        {
            "regla": AVISO.regla,
            "severidad": int(AVISO.severidad),
            "descripcion": AVISO.descripcion,
            "impacto": None,
            "origen_ids": list(AVISO.origen_ids),
            "valor_observado": None,
            "valor_esperado": None,
        }
    ]
    return reauditoria.leer_documento_json(json_canonico(objeto))


def _reauditar(fuente_id: str | None) -> reauditoria.Reauditoria:
    return reauditoria.reauditar(
        _documento_que_declara_el_aviso(),
        reauditoria.Servicios(),
        FECHA,
        espacio_json=_espacio(fuente_id),
    )


def test_con_el_anexo_de_espacio_la_reauditoria_corre_r17():
    assert "R17" in _reauditar(None).contextos


def test_un_aviso_r17_que_sigue_vigente_es_comun_y_no_cae_en_ya_no():
    r = _reauditar(None)
    assert AVISO in r.comunes
    assert [h for h in r.ya_no if h.regla == "R17"] == []
    assert [h for h in r.nuevos if h.regla == "R17"] == []


def test_un_aviso_r17_del_punto_ya_corregido_cae_en_ya_no():
    r = _reauditar("F")
    assert [h for h in r.ya_no if h.regla == "R17"] == [AVISO]
    assert [h for h in r.comunes if h.regla == "R17"] == []
