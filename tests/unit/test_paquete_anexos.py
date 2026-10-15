"""Los anexos del paquete (S3 §8.1): filas con huella, filtradas por proyecto, sin cadena propia.

`anexo_de_tablas` serializa lo que existe: una tabla que esta versión no conoce se omite, una
tabla hija se filtra por los padres ya incluidos, y cada entrada trae la huella de su fila. Una
tabla con columna `responsable` está en un anexo o en la lista de las que no viajan (RF-82).

Oráculo de la huella: SHA-256 de `json.dumps(fila, sort_keys=True, separators=(",", ":"),
ensure_ascii=False)` calculado aquí con `hashlib`, no con `core.budget.canonico`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal

import pytest

from core import models
from core.budget import crear_proyecto
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.contracts.dominio import Dominio
from core.models import Base
from migraciones.metadatos import METADATAS_CASO
from paquete import anexos
from tests.fixtures.canonico_minimo import guardar_otra, registro, sembrar_minimo


@pytest.fixture
def caso():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        yield sesion
    motor.dispose()


def _huella_a_mano(fila: dict) -> str:
    texto = json.dumps(fila, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _anexo(sesion, tablas, proyecto_id) -> dict:
    octetos = anexos.anexo_de_tablas(sesion, "prueba", tablas, proyecto_id)
    assert octetos is not None
    return json.loads(octetos)


def _clausula(presupuesto_id: int, fuente: str) -> models.ClausulaReajuste:
    return models.ClausulaReajuste(
        presupuesto_id=presupuesto_id,
        fecha_inicio=date(2026, 11, 1),
        duracion_meses=6,
        fecha_referencia_primer_anio=date(2026, 11, 1),
        periodicidad="mensual",
        mecanismo="formula",
        estructura="declarada",
        fecha_base_indices=date(2026, 10, 1),
        r=Decimal("0.15"),
        fuente_r="contrato de prueba",
        fuente=fuente,
        responsable="Ana Pérez <ana>",
    )


def test_cada_entrada_trae_la_huella_de_su_fila_y_solo_las_del_proyecto(caso) -> None:
    proyecto, version, _ = sembrar_minimo(caso)
    caso.add(registro(proyecto, None, version))
    otro = crear_proyecto(caso, "OTRO", dominio=Dominio.CIVIL)
    ajeno = registro(proyecto, None, version)
    ajeno.proyecto_id = otro.id  # una fila de otro proyecto no debe viajar
    caso.add(ajeno)
    caso.commit()
    anexo = _anexo(caso, ("registro_cambio",), proyecto.id)
    assert (anexo["formato"], anexo["nombre"], anexo["version_formato"]) == (
        "silice-anexo",
        "prueba",
        1,
    )
    [entrada] = anexo["entradas"]
    assert entrada["tabla"] == "registro_cambio"
    assert entrada["huella"] == _huella_a_mano(entrada["fila"])
    assert entrada["fila"]["proyecto_id"] == proyecto.id
    assert entrada["fila"]["responsable"] == "Ana Pérez <ana>"  # UTF-8 sin escapar
    assert anexos.huellas_de_entradas(anexo) == [entrada["huella"]]


def test_el_anexo_es_json_canonico_y_reproducible(caso) -> None:
    proyecto, version, _ = sembrar_minimo(caso)
    caso.add(registro(proyecto, None, version))
    caso.commit()
    una = anexos.anexo_de_tablas(caso, "prueba", ("registro_cambio",), proyecto.id)
    otra = anexos.anexo_de_tablas(caso, "prueba", ("registro_cambio",), proyecto.id)
    assert una == otra
    assert una == json.dumps(
        json.loads(una), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def test_una_tabla_desconocida_se_omite_y_sin_filas_no_hay_anexo(caso) -> None:
    proyecto, _, _ = sembrar_minimo(caso)
    caso.commit()
    assert anexos.anexo_de_tablas(caso, "x", ("tabla_que_no_existe",), proyecto.id) is None
    assert anexos.anexo_de_tablas(caso, "x", ("registro_cambio",), proyecto.id) is None
    assert anexos.anexo_de_tablas(caso, "x", (), proyecto.id) is None


def test_una_tabla_hija_se_filtra_por_los_padres_incluidos(caso) -> None:
    proyecto, version, lista = sembrar_minimo(caso)
    otro = crear_proyecto(caso, "OTRO", dominio=Dominio.CIVIL)
    ajena = guardar_otra(caso, otro, lista, "001")
    caso.commit()
    anexo = _anexo(caso, ("presupuesto", "item_computo"), proyecto.id)
    tablas = [e["tabla"] for e in anexo["entradas"]]
    assert tablas.count("presupuesto") == 1 and tablas.count("item_computo") == 1
    hijos = [e["fila"] for e in anexo["entradas"] if e["tabla"] == "item_computo"]
    assert {h["presupuesto_id"] for h in hijos} == {version.id}
    assert ajena.id != version.id


def test_una_tabla_hija_sin_padres_con_filas_no_trae_nada(caso) -> None:
    proyecto, _, lista = sembrar_minimo(caso)
    otro = crear_proyecto(caso, "OTRO", dominio=Dominio.CIVIL)
    caso.commit()
    # OTRO no tiene versiones: el padre queda vacío y la hija no debe traer las de MIN-001
    assert anexos.anexo_de_tablas(caso, "x", ("presupuesto", "item_computo"), otro.id) is None
    assert lista is not None and proyecto.id != otro.id


def test_los_decimales_van_como_texto_y_las_fechas_como_iso(caso) -> None:
    proyecto, version, _ = sembrar_minimo(caso)
    caso.commit()
    anexo = _anexo(caso, ("presupuesto",), proyecto.id)
    fila = anexo["entradas"][0]["fila"]
    assert isinstance(fila["fcas"], str) and Decimal(fila["fcas"]) == version.fcas
    assert fila["fecha"] == "2026-11-01"


def test_el_anexo_de_reajuste_no_lleva_las_clausulas_de_otro_proyecto(caso) -> None:
    """`clausula_reajuste` no tiene `proyecto_id` y su padre (`presupuesto`) no está en
    `TABLAS_DE_REAJUSTE`: debe filtrarse igual por el proyecto (S3 §8.1, «filas del proyecto»)."""
    proyecto, version, lista = sembrar_minimo(caso)
    otro = crear_proyecto(caso, "OTRO", dominio=Dominio.CIVIL)
    ajena = guardar_otra(caso, otro, lista, "001")
    caso.add_all([_clausula(version.id, "propia"), _clausula(ajena.id, "AJENA")])
    caso.commit()
    anexo = _anexo(caso, anexos.TABLAS_DE_REAJUSTE, proyecto.id)
    clausulas = [e["fila"] for e in anexo["entradas"] if e["tabla"] == "clausula_reajuste"]
    assert [(c["fuente"], c["presupuesto_id"]) for c in clausulas] == [("propia", version.id)]


def test_toda_tabla_con_responsable_viaja_o_esta_en_la_lista_de_las_que_no() -> None:
    declaradas = {
        *anexos.TABLAS_DE_REAJUSTE,
        *anexos.TABLAS_DE_CONTROL,
        *anexos.TABLAS_QUE_NO_VIAJAN,
    }
    con_responsable = {
        tabla.name
        for metadata in METADATAS_CASO
        for tabla in metadata.tables.values()
        if "responsable" in tabla.c
    }
    assert con_responsable, "el recorrido de metadatos no encontró ninguna tabla"
    assert sorted(con_responsable - declaradas) == []


def test_las_tablas_declaradas_existen_en_el_modelo_del_caso() -> None:
    """Lo contrario: una tabla de un anexo que no existe en el modelo se omitiría en silencio;
    hoy todas existen y están en `Base.metadata`, la única que lee `anexo_de_tablas`."""
    nucleo = Base.metadata.tables
    for nombre in (*anexos.TABLAS_DE_REAJUSTE, *anexos.TABLAS_DE_CONTROL):
        assert nombre in nucleo, nombre
    assert set(anexos.TABLAS_DE_REAJUSTE).isdisjoint(anexos.TABLAS_DE_CONTROL)


def test_todo_nombre_de_los_anexos_es_una_tabla_real_del_caso() -> None:
    """Tarea 24: un nombre mal escrito en una lista de anexos ya no se omite en silencio."""
    reales = {t for metadata in METADATAS_CASO for t in metadata.tables}
    declaradas = {*anexos.TABLAS_DE_REAJUSTE, *anexos.TABLAS_DE_CONTROL}
    assert sorted(declaradas - reales) == []
