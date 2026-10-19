"""Sesion P2.5 (Tarea 4): el contrato de la pagina de componer con las cuatro ayudas de AREN.IA.

Las cuatro ayudas (`ml.normalization`, `ml.anomaly` dos veces, `ml.prediction`) ya tienen sus
propias pruebas (`tests/unit/test_normalizacion.py`, `test_anomalias.py`, `test_prediccion.py`).
Lo que se prueba aqui es distinto: el contrato de `ui/composicion.py` con esas ayudas, que es
absoluto por diseno (spec §3.7) -- "todas sugerencia y ninguna bloqueante" -- y que ninguna decide
ni modifica la composicion por su cuenta.

Se usan dobles, nunca el modelo real: el normalizador semantico descarga pesos de un modelo de
lenguaje y una prueba unitaria no puede depender de una descarga (ademas, la CI corre con
`--all-extras` y falla si una prueba se omite, asi que la ausencia del extra `ml` se simula con un
doble que lanza `ImportError`, nunca con `skipif`).
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from core.contracts import Hallazgo, Severidad
from ml.normalization import Propuesta
from tests.fixtures.sin_extra import SinExtra
from ui.composicion import (
    ContrasteAace,
    advertencia_precio_atipico,
    composicion_desde_tablas,
    contrastar_precio_con_reglas,
    sugerir_partidas_similares,
    veredicto_ml_rendimiento,
)


def _que_falla(*_args, **_kwargs):
    """Un doble que representa cualquier fallo de una ayuda: modelo caido, sin red, bosque que no
    converge... la razon no importa, el contrato es el mismo para todas: degradar en silencio.
    """
    raise RuntimeError("ayuda de ml caida a proposito, para la prueba")


def _que_falla_por_extra_ausente(*_args, **_kwargs):
    """El doble que simula el extra `ml` no instalado: un `import` real de un modulo ausente lanza
    exactamente esta excepcion (`ModuleNotFoundError`, subclase de `ImportError`), y aqui se
    reproduce sin depender de (des)instalar nada.
    """
    raise ModuleNotFoundError("simulado: el extra 'ml' no esta instalado")


# ---------------------------------------------------------------------------------------------
# Ayuda 1: partidas similares del catalogo (ml.normalization.proponedor, INV-081)
# ---------------------------------------------------------------------------------------------
#
# Reescritura declarada de C3 (10c, QA-4): la costura `cargar_normalizacion` ya no ofrece
# `NormalizadorPartidas`, sino `Propuesta` y `proponedor`, el criterio unico de fallas de `ml`. Las
# fallas del modelo se simulan en `ml.normalization.normalizador._cargar_modelo`, donde ocurren de
# verdad, con la costura por defecto.


def _modulo_normalizacion(resultado):
    def proponedor(partidas):
        assert partidas, "se le debe pasar el catalogo real, no un mapeo vacio"

        def proponer(descripcion):
            assert descripcion
            return Propuesta(tuple(resultado))

        return proponer

    return SimpleNamespace(Propuesta=Propuesta, proponedor=proponedor)


def test_sugerir_partidas_similares_ofrece_lo_que_devuelve_la_ayuda():
    resultado = [SimpleNamespace(codigo="LB-01-EXC", descripcion="Excavacion", puntaje=0.91)]
    modulo = _modulo_normalizacion(resultado)

    propuesta = sugerir_partidas_similares(
        {"LB-01-EXC": "Excavacion a mano"},
        "excavacion de zanja",
        cargar_normalizacion=lambda: modulo,
    )

    assert propuesta.similares == tuple(resultado)
    assert propuesta.falla is None


def test_sugerir_partidas_similares_no_bloquea_si_la_ayuda_lanza(monkeypatch):
    monkeypatch.setattr("ml.normalization.normalizador._cargar_modelo", _que_falla)
    propuesta = sugerir_partidas_similares({"A": "algo"}, "algo parecido")
    assert propuesta.similares == ()
    assert propuesta.falla.startswith("RuntimeError")


def test_sugerir_partidas_similares_sin_el_extra_ml(monkeypatch):
    """El extra ausente llega como `ModuleNotFoundError` y `ml` lo declara `ImportError`: es el
    prefijo con que la pagina de similares reconoce «instale el extra»."""
    monkeypatch.setattr(
        "ml.normalization.normalizador._cargar_modelo", _que_falla_por_extra_ausente
    )
    propuesta = sugerir_partidas_similares({"A": "algo"}, "algo parecido")
    assert propuesta.similares == ()
    assert propuesta.falla.startswith("ImportError:")


def test_sugerir_partidas_similares_propaga_lo_que_no_es_una_falla_declarada(monkeypatch):
    """INV-081 (C3-4): solo las cuatro fallas declaradas de `ml.normalization` dejan la ayuda sin
    propuestas; un `KeyError` es un defecto y se propaga, no se traga como «sin sugerencias»."""

    def _defecto(*_args, **_kwargs):
        raise KeyError("defecto, no una falla declarada del modelo")

    monkeypatch.setattr("ml.normalization.normalizador._cargar_modelo", _defecto)
    with pytest.raises(KeyError):
        sugerir_partidas_similares({"A": "algo"}, "algo parecido")


def test_sugerir_partidas_similares_sin_descripcion_no_intenta_nada():
    """Sin texto que buscar no hay nada que sugerir: ni siquiera se construye el normalizador."""

    def _no_se_llama(_partidas):
        raise AssertionError("sin descripcion no se construye ningun normalizador")

    modulo = SimpleNamespace(Propuesta=Propuesta, proponedor=_no_se_llama)
    propuesta = sugerir_partidas_similares(
        {"A": "algo"}, "   ", cargar_normalizacion=lambda: modulo
    )
    assert propuesta == Propuesta(())


# ---------------------------------------------------------------------------------------------
# Ayuda 2: aviso de precio atipico (ml.anomaly.precios_atipicos)
# ---------------------------------------------------------------------------------------------


def _modulo_anomalia_precios(marcar_todo: bool):
    def precios_atipicos(variaciones):
        if not marcar_todo:
            return []
        return [
            SimpleNamespace(id=clave, valor=valor, puntaje=-1.0)
            for clave, valor in variaciones.items()
        ]

    return SimpleNamespace(precios_atipicos=precios_atipicos)


def test_advertencia_precio_atipico_ofrece_el_aviso_cuando_la_ayuda_marca_el_candidato():
    modulo = _modulo_anomalia_precios(marcar_todo=True)

    atipico = advertencia_precio_atipico(
        historico={"cambio-01": Decimal("0.02")},
        precio_anterior=Decimal("100"),
        precio_nuevo=Decimal("500"),
        cargar_anomalia=lambda: modulo,
    )

    assert atipico is True


def test_advertencia_precio_atipico_no_ofrece_nada_si_la_ayuda_no_marca_nada():
    modulo = _modulo_anomalia_precios(marcar_todo=False)

    atipico = advertencia_precio_atipico(
        historico={"cambio-01": Decimal("0.02")},
        precio_anterior=Decimal("100"),
        precio_nuevo=Decimal("101"),
        cargar_anomalia=lambda: modulo,
    )

    assert atipico is False


def test_advertencia_precio_atipico_no_bloquea_si_la_ayuda_lanza():
    atipico = advertencia_precio_atipico(
        historico={"cambio-01": Decimal("0.02")},
        precio_anterior=Decimal("100"),
        precio_nuevo=Decimal("500"),
        cargar_anomalia=_que_falla,
    )
    assert atipico is False


def test_advertencia_precio_atipico_sin_el_extra_ml():
    atipico = advertencia_precio_atipico(
        historico={"cambio-01": Decimal("0.02")},
        precio_anterior=Decimal("100"),
        precio_nuevo=Decimal("500"),
        cargar_anomalia=_que_falla_por_extra_ausente,
    )
    assert atipico is False


def test_advertencia_precio_atipico_sin_precio_anterior_no_hay_nada_que_evaluar():
    """Sin un precio anterior conocido no hay variacion que calcular: ni se intenta cargar `ml`."""
    atipico = advertencia_precio_atipico(
        historico={}, precio_anterior=None, precio_nuevo=Decimal("100"), cargar_anomalia=_que_falla
    )
    assert atipico is False


# ---------------------------------------------------------------------------------------------
# Ayuda 3: lectura de ml.anomaly sobre el rendimiento (complementa la Tarea 1)
# ---------------------------------------------------------------------------------------------


def _modulo_anomalia_rendimiento(veredicto):
    return SimpleNamespace(evaluar_rendimiento=lambda observados, valor: veredicto)


def test_veredicto_ml_rendimiento_ofrece_el_veredicto_de_la_ayuda():
    veredicto_esperado = SimpleNamespace(atipico=True, puntaje=-0.31)
    modulo = _modulo_anomalia_rendimiento(veredicto_esperado)

    veredicto = veredicto_ml_rendimiento(
        [Decimal("8")] * 8, Decimal("30"), cargar_anomalia=lambda: modulo
    )

    assert veredicto is veredicto_esperado


def test_veredicto_ml_rendimiento_none_cuando_la_ayuda_se_abstiene():
    """Con pocas observaciones, `ml.anomaly.evaluar_rendimiento` ya devuelve `None` por su cuenta:
    esta funcion no le anade una segunda razon para abstenerse, solo la deja pasar.
    """
    modulo = _modulo_anomalia_rendimiento(None)

    veredicto = veredicto_ml_rendimiento(
        [Decimal("8")], Decimal("8"), cargar_anomalia=lambda: modulo
    )

    assert veredicto is None


def test_veredicto_ml_rendimiento_no_bloquea_si_la_ayuda_lanza():
    veredicto = veredicto_ml_rendimiento(
        [Decimal("8")] * 8, Decimal("30"), cargar_anomalia=_que_falla
    )
    assert veredicto is None


def test_veredicto_ml_rendimiento_sin_el_extra_ml():
    veredicto = veredicto_ml_rendimiento(
        [Decimal("8")] * 8, Decimal("30"), cargar_anomalia=_que_falla_por_extra_ausente
    )
    assert veredicto is None


# ---------------------------------------------------------------------------------------------
# Ayuda 4: contraste del PU contra la estimacion por reglas (ml.prediction, marco AACE)
# ---------------------------------------------------------------------------------------------


def _modulo_prediccion(pu_estimado: Decimal, hallazgo: Hallazgo | None, tecnica: str = "reglas"):
    def predecir_por_reglas(pus_base, variaciones):
        ((codigo, pu_base),) = pus_base.items()
        return [
            SimpleNamespace(
                codigo_partida=codigo,
                pu_base=pu_base,
                pu_estimado=pu_estimado,
                pu_minimo=pu_estimado,
                pu_maximo=pu_estimado,
            )
        ]

    return SimpleNamespace(
        predecir_por_reglas=predecir_por_reglas,
        contrastar_aace=lambda codigo, construido, estimado: hallazgo,
        tecnica_para=lambda registros: tecnica,
    )


def test_contrastar_precio_con_reglas_ofrece_el_marco_aace_cuando_hay_hallazgo():
    hallazgo = Hallazgo(
        regla="CONTRASTE-AACE3",
        severidad=Severidad.ADVERTENCIA,
        descripcion="el precio construido se desvia fuera de la clase 3 de AACE",
    )
    modulo = _modulo_prediccion(Decimal("120"), hallazgo)

    contraste = contrastar_precio_con_reglas(
        "LB-01-EXC",
        Decimal("200"),
        Decimal("100"),
        [Decimal("0.2")],
        registros=5,
        cargar_prediccion=lambda: modulo,
    )

    esperado = ContrasteAace(tecnica="reglas", pu_estimado=Decimal("120"), hallazgo=hallazgo)
    assert contraste == esperado


def test_contrastar_precio_con_reglas_sin_hallazgo_cuando_esta_dentro_del_rango():
    modulo = _modulo_prediccion(Decimal("200"), None)

    contraste = contrastar_precio_con_reglas(
        "LB-01-EXC",
        Decimal("200"),
        Decimal("190"),
        [],
        registros=5,
        cargar_prediccion=lambda: modulo,
    )

    assert contraste is not None
    assert contraste.hallazgo is None


def test_contrastar_precio_con_reglas_no_bloquea_si_la_ayuda_lanza():
    contraste = contrastar_precio_con_reglas(
        "LB-01-EXC", Decimal("200"), Decimal("100"), [], registros=5, cargar_prediccion=_que_falla
    )
    assert contraste is None


def test_contrastar_precio_con_reglas_sin_el_extra_ml():
    contraste = contrastar_precio_con_reglas(
        "LB-01-EXC",
        Decimal("200"),
        Decimal("100"),
        [],
        registros=5,
        cargar_prediccion=_que_falla_por_extra_ausente,
    )
    assert contraste is None


# ---------------------------------------------------------------------------------------------
# El contrato central: ninguna ayuda decide ni modifica la composicion (spec §3.7)
# ---------------------------------------------------------------------------------------------


def test_ninguna_ayuda_modifica_las_filas_ni_la_composicion_resultante(monkeypatch):
    """Se arma una composicion real con `composicion_desde_tablas` antes y despues de invocar las
    cuatro ayudas -- con dobles, todos fallando a proposito -- y debe ser exactamente la misma: lo
    que se guarda es lo que la persona compuso, nunca lo que una ayuda propuso (spec §3.7).
    """
    filas_materiales = [
        {"descripcion": "Cemento", "unidad": "saco", "cantidad": "2", "precio": "8"}
    ]
    filas_equipos: list[dict] = []
    filas_mano_obra: list[dict] = []

    def componer() -> object:
        return composicion_desde_tablas(
            "LB-99-PRUEBA",
            "Partida de prueba",
            "m3",
            "10",
            filas_materiales,
            filas_equipos,
            filas_mano_obra,
        )

    antes = componer()

    monkeypatch.setattr("ml.normalization.normalizador._cargar_modelo", _que_falla)
    sugerir_partidas_similares({"A": "algo"}, "cemento")
    advertencia_precio_atipico(
        {}, Decimal("8"), Decimal("8"), cargar_anomalia=_que_falla_por_extra_ausente
    )
    veredicto_ml_rendimiento([], Decimal("10"), cargar_anomalia=_que_falla)
    contrastar_precio_con_reglas(
        "LB-99-PRUEBA", Decimal("50"), Decimal("48"), [], 5, cargar_prediccion=_que_falla
    )

    despues = componer()
    assert antes == despues
    assert filas_materiales == [
        {"descripcion": "Cemento", "unidad": "saco", "cantidad": "2", "precio": "8"}
    ]


# ---------------------------------------------------------------------------------------------
# La pagina arranca y compone sin el extra `ml` (no solo las funciones puras: la pagina completa)
# ---------------------------------------------------------------------------------------------

#: Modulos que un import perezoso mal hecho dejaria en cache con `ml` ya cargado; se limpian antes
#: y se restauran despues (el mismo gestor `tests.fixtures.sin_extra.SinExtra`
#: que usa `tests/unit/test_ui_actualizacion_alta.py` para otros extras).
_MODULOS_RELACIONADOS_CON_ML = (
    "ml",
    "ml.normalization",
    "ml.normalization.normalizador",
    "ml.anomaly",
    "ml.anomaly.detector",
    "ml.prediction",
    "ml.prediction.reglas",
    "aplicacion.composicion",
    "ui.composicion",
    "ui.paginas.componer",
)


def test_la_pagina_de_componer_se_importa_sin_el_extra_ml(monkeypatch):
    """RF de arranque (spec §3.7): la interfaz sigue arrancando sin el extra `ml`; las cuatro
    ayudas simplemente no aparecen (cada una degrada a "sin sugerencia" al intentar usarse).
    """
    import importlib

    with SinExtra(monkeypatch, ("ml",), _MODULOS_RELACIONADOS_CON_ML):
        modulo_composicion = importlib.import_module("ui.composicion")
        modulo_pagina = importlib.import_module("ui.paginas.componer")

    # INV-024: `is not None` no afirma nada; se exige el punto de entrada de cada modulo.
    assert callable(modulo_composicion.sugerir_partidas_similares)
    assert callable(modulo_pagina.render)
