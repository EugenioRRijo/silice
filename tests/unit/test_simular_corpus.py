"""El corpus simulado de la Sesion P4.3: determinista, sin `float` y en cuarentena.

Todas las pruebas que tocan disco usan `tmp_path`: ninguna escribe en `data/apu.db`, y toda la que
abre un motor SQLAlchemy lo cierra con `motor.dispose()` (en Windows, un archivo abierto impide
borrar el temporal).
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from enum import Enum

import scripts.simular_corpus as simular_corpus
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts import ParametrosCosto
from core.contracts.unidades import normalizar_unidad
from core.costing import calcular_apu
from scripts.simular_corpus import FECHA_CORPUS, UNIDADES_CORPUS, generar_corpus, main


def test_misma_semilla_mismo_corpus_y_semilla_distinta_corpus_distinto():
    corpus = generar_corpus(20, 42)
    assert corpus == generar_corpus(20, 42)
    assert corpus != generar_corpus(20, 43)


def test_n_composiciones_con_codigos_unicos_y_unidades_aceptadas():
    corpus = generar_corpus(50, 7)
    assert len(corpus) == 50
    codigos = [composicion.codigo_partida for composicion in corpus]
    assert len(set(codigos)) == 50
    assert codigos[0] == "SIM-0001"
    assert codigos[-1] == "SIM-0050"
    for unidad in UNIDADES_CORPUS:
        assert normalizar_unidad(unidad) == unidad
    for composicion in corpus:
        assert composicion.unidad in UNIDADES_CORPUS
        assert "simulada" in composicion.descripcion.lower()


def _numericos(linea: object) -> list[object]:
    """Los valores de los campos de una linea que no son texto ni enumeracion."""
    return [
        getattr(linea, campo.name)
        for campo in dataclasses.fields(linea)
        if not isinstance(getattr(linea, campo.name), str | Enum)
    ]


def test_ningun_float_en_lineas_ni_rendimiento():
    for composicion in generar_corpus(40, 3):
        assert isinstance(composicion.rendimiento, Decimal)
        lineas = (*composicion.materiales, *composicion.equipos, *composicion.mano_obra)
        for linea in lineas:
            valores = _numericos(linea)
            assert valores, f"{linea!r} no tiene campos numericos"
            for valor in valores:
                assert isinstance(valor, Decimal), f"{linea!r}: {valor!r} no es Decimal"


def test_cada_composicion_se_calcula_con_precio_unitario_positivo():
    parametros = ParametrosCosto()
    for composicion in generar_corpus(40, 11):
        assert 1 <= len(composicion.materiales) <= 4
        assert 0 <= len(composicion.equipos) <= 2
        assert 1 <= len(composicion.mano_obra) <= 3
        assert calcular_apu(composicion, parametros).precio_unitario > 0


def test_main_se_niega_si_el_archivo_ya_existe(tmp_path, capsys):
    base = tmp_path / "ya_existe.db"
    base.write_bytes(b"contenido previo que no debe tocarse")
    antes = (base.read_bytes(), base.stat().st_mtime_ns)

    codigo = main(["--db", str(base), "--n", "5"])

    assert codigo != 0
    assert (base.read_bytes(), base.stat().st_mtime_ns) == antes
    assert "ya existe" in capsys.readouterr().err


def test_main_carga_el_corpus_y_el_catalogo_lo_reconstruye(tmp_path):
    base = tmp_path / "corpus_simulado.db"
    assert main(["--db", str(base), "--n", "5"]) == 0

    parametros = ParametrosCosto()
    esperado = {
        composicion.codigo_partida: calcular_apu(composicion, parametros).precio_unitario
        for composicion in generar_corpus(5, 42)
    }
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            codigos = sorted(partida.codigo for partida in catalogo.partidas())
            assert codigos == sorted(esperado)
            assert all(codigo.startswith("SIM-") for codigo in codigos)
            for codigo, precio_unitario in esperado.items():
                reconstruida = catalogo.composicion(codigo, fecha=FECHA_CORPUS)
                assert calcular_apu(reconstruida, parametros).precio_unitario == precio_unitario
    finally:
        motor.dispose()


def test_el_docstring_declara_simulado_y_fuera_de_toda_compuerta():
    docstring = simular_corpus.__doc__
    assert docstring is not None
    assert "simulado" in docstring
    assert "no cuenta para ninguna compuerta" in docstring
    assert "G2" in docstring
    assert "no alimenta `ml/`" in docstring
