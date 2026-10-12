"""El registro `ia_*` y el anexo `anexos/ia.json` (S4 §5.5, RF-93, RV-19; plan 0.9.0, tarea 10).

Escribe directo en las tablas, sin orquestador: el orden de las filas, las decisiones, lo que el
anexo lleva y lo que NUNCA lleva (uso de fichas, costo, topes, la clave de IA de la empresa).
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect

from asistente.registro import (
    METADATA_IA,
    TABLAS,
    RegistroIA,
    anexo_ia,
    crear_esquema_ia,
    volcado,
)

AHORA = datetime(2026, 10, 11, 9, 0, 0)
CLAVE_DE_PRUEBA = "sk-ant-api03-NO-DEBE-APARECER"
USO = {"entrada": 100, "salida": 40, "cache_lectura": 60, "cache_escritura": 0}


@pytest.fixture
def conexion():
    motor = create_engine("sqlite://")
    crear_esquema_ia(motor)
    with motor.begin() as con:
        yield con
    motor.dispose()


def sesion_completa(con, *, proyecto="OF", aceptar=True, guardar_en="002") -> int:
    registro = RegistroIA(con, ahora=lambda: AHORA)
    sesion = registro.iniciar(
        proyecto=proyecto,
        version_partida="001",
        proveedor="claude",
        modelo="claude-opus-5-5",
        pedido="Bano de 2,4 x 1,5 m",
        topes={"turnos": 12, "llamadas": 60, "costo": "2"},
    )
    registro.turno(
        sesion,
        1,
        modelo="claude-opus-5-5",
        fin="herramientas",
        uso=USO,
        costo=Decimal("0.1012"),
        texto="voy a proponer",
    )
    registro.llamada(sesion, 1, "proponer_ambiente", {"id": "A", "largo": "2.4"}, "valida", "")
    registro.llamada(
        sesion, 1, "preguntar_al_usuario", {"pregunta": "alto?"}, "valida", "", "2,5 m"
    )
    registro.propuesta(sesion, "P1", "ambiente", "pendiente", [["largo", "2,4"]], [], [{"id": "A"}])
    registro.cerrar(sesion, "terminar")
    if aceptar:
        registro.decidir(sesion, "P1", "aceptada", "ana")
    if guardar_en:
        registro.marcar_guardada(sesion, guardar_en)
    return sesion


def test_las_cuatro_tablas_estan_en_su_propia_metadata_y_sin_clave_foranea_al_nucleo():
    assert tuple(METADATA_IA.tables) == TABLAS
    for tabla in METADATA_IA.tables.values():
        destinos = {fk.column.table.name for fk in tabla.foreign_keys}
        assert destinos <= set(TABLAS)  # nunca a `core/models`


def test_una_sesion_deja_exactamente_las_filas_esperadas_en_orden(conexion):
    sesion_completa(conexion)
    v = volcado(conexion)
    assert [
        (s["proyecto"], s["proveedor"], s["motivo_fin"], s["version_guardada"])
        for s in v["ia_sesiones"]
    ] == [("OF", "claude", "terminar", "002")]
    assert [(t["orden"], t["fin"], t["costo"]) for t in v["ia_turnos"]] == [
        (1, "herramientas", "0.1012")
    ]
    assert [(c["herramienta"], c["resultado"], c["respuesta"]) for c in v["ia_llamadas"]] == [
        ("proponer_ambiente", "valida", None),
        ("preguntar_al_usuario", "valida", "2,5 m"),
    ]
    assert json.loads(v["ia_llamadas"][0]["argumentos"]) == {"id": "A", "largo": "2.4"}
    assert [(p["propuesta"], p["estado"], p["decidida_por"]) for p in v["ia_propuestas"]] == [
        ("P1", "aceptada", "ana")
    ]


def test_el_anexo_trae_pedido_turnos_llamadas_y_decisiones_pero_nunca_uso_ni_costo(conexion):
    sesion_completa(conexion)
    texto = anexo_ia(conexion, "OF", "002").decode()
    documento = json.loads(texto)
    assert documento["formato"] == "silice-ia" and documento["version_formato"] == 1
    (s,) = documento["sesiones"]
    assert s["pedido"] == "Bano de 2,4 x 1,5 m" and s["turnos"][0]["texto"] == "voy a proponer"
    assert [c["herramienta"] for c in s["llamadas"]] == [
        "proponer_ambiente",
        "preguntar_al_usuario",
    ]
    assert s["propuestas"][0]["decidida_por"] == "ana"

    def claves(nodo):
        if isinstance(nodo, dict):
            for k, v in nodo.items():
                yield k
                yield from claves(v)
        elif isinstance(nodo, list):
            for v in nodo:
                yield from claves(v)

    prohibidas = {"uso", "costo", "entrada", "salida", "cache_lectura", "cache_escritura", "topes"}
    assert not prohibidas & set(claves(documento))
    assert CLAVE_DE_PRUEBA not in texto


def test_el_anexo_solo_incluye_sesiones_guardadas_aceptadas_del_proyecto_y_hasta_esa_version(
    conexion,
):
    sesion_completa(conexion, aceptar=False)  # nada aceptado: no viaja
    sesion_completa(conexion, guardar_en="")  # nunca guardada: no viaja
    sesion_completa(conexion, proyecto="OTRO")  # de otro proyecto: no viaja
    assert anexo_ia(conexion, "OF", "009") is None
    sesion_completa(conexion, guardar_en="003")
    assert anexo_ia(conexion, "OF", "002") is None  # se guardo en la 003: aun no
    assert len(json.loads(anexo_ia(conexion, "OF", "003"))["sesiones"]) == 1


def test_el_volcado_de_la_base_no_contiene_la_clave_de_ia(conexion):
    sesion_completa(conexion)
    volcado_completo = json.dumps(volcado(conexion), default=str)
    assert CLAVE_DE_PRUEBA not in volcado_completo
    nombres = set(inspect(conexion).get_table_names())
    assert set(TABLAS) <= nombres
