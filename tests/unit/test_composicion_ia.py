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

import builtins
import sys
from decimal import Decimal
from types import SimpleNamespace

import pytest

from core.contracts import Hallazgo, Severidad
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
    """El doble que simula el extra `ml` no instalado: un `import ml.algo` real lanza exactamente
    esta excepcion, y aqui se reproduce sin depender de (des)instalar nada.
    """
    raise ImportError("simulado: el extra 'ml' no esta instalado")


# ---------------------------------------------------------------------------------------------
# Ayuda 1: partidas similares del catalogo (ml.normalization.NormalizadorPartidas)
# ---------------------------------------------------------------------------------------------


def _modulo_normalizacion(resultado):
    class _NormalizadorDoble:
        def __init__(self, partidas):
            assert partidas, "se le debe pasar el catalogo real, no un mapeo vacio"
            self.partidas = partidas

        def similares(self, descripcion):
            assert descripcion
            return resultado

    return SimpleNamespace(NormalizadorPartidas=_NormalizadorDoble)


def test_sugerir_partidas_similares_ofrece_lo_que_devuelve_la_ayuda():
    resultado = [SimpleNamespace(codigo="LB-01-EXC", descripcion="Excavacion", puntaje=0.91)]
    modulo = _modulo_normalizacion(resultado)

    propuestas = sugerir_partidas_similares(
        {"LB-01-EXC": "Excavacion a mano"},
        "excavacion de zanja",
        cargar_normalizacion=lambda: modulo,
    )

    assert propuestas == resultado


def test_sugerir_partidas_similares_no_bloquea_si_la_ayuda_lanza():
    propuestas = sugerir_partidas_similares(
        {"A": "algo"}, "algo parecido", cargar_normalizacion=_que_falla
    )
    assert propuestas == []


def test_sugerir_partidas_similares_sin_el_extra_ml():
    propuestas = sugerir_partidas_similares(
        {"A": "algo"}, "algo parecido", cargar_normalizacion=_que_falla_por_extra_ausente
    )
    assert propuestas == []


def test_sugerir_partidas_similares_sin_descripcion_no_intenta_nada():
    """Sin texto que buscar no hay nada que sugerir: ni siquiera se llega a cargar la ayuda."""
    propuestas = sugerir_partidas_similares(
        {"A": "algo"}, "   ", cargar_normalizacion=_que_falla
    )
    assert propuestas == []


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


def test_ninguna_ayuda_modifica_las_filas_ni_la_composicion_resultante():
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

    sugerir_partidas_similares({"A": "algo"}, "cemento", cargar_normalizacion=_que_falla)
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
#: y se restauran despues (mismo patron que `tests/unit/test_visor3d.py::_SinIfcopenshell` para el
#: extra `civil`).
_MODULOS_RELACIONADOS_CON_ML = (
    "ml",
    "ml.normalization",
    "ml.normalization.normalizador",
    "ml.anomaly",
    "ml.anomaly.detector",
    "ml.prediction",
    "ml.prediction.reglas",
    "ui.composicion",
    "ui.paginas.componer",
)


class _SinExtraML:
    """Bloquea `import ml` (y sus submodulos) con un `ImportError`, para que un import a nivel de
    modulo mal hecho en `ui.composicion` o `ui.paginas.componer` se delate de inmediato. Restaura
    el cache de modulos original al salir, para no afectar otras pruebas de la suite.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._monkeypatch = monkeypatch

    def __enter__(self) -> None:
        self._respaldo = {
            nombre: sys.modules[nombre]
            for nombre in _MODULOS_RELACIONADOS_CON_ML
            if nombre in sys.modules
        }
        for nombre in _MODULOS_RELACIONADOS_CON_ML:
            sys.modules.pop(nombre, None)

        import_original = builtins.__import__

        def import_bloqueado(nombre, *args, **kwargs):
            if nombre == "ml" or nombre.startswith("ml."):
                raise ImportError(f"simulado: extra ml no instalado ({nombre})")
            return import_original(nombre, *args, **kwargs)

        self._monkeypatch.setattr(builtins, "__import__", import_bloqueado)

    def __exit__(self, *excepcion: object) -> None:
        for nombre in _MODULOS_RELACIONADOS_CON_ML:
            sys.modules.pop(nombre, None)
        sys.modules.update(self._respaldo)
        # Arreglo de la Tarea 1 (P4.1, `tests/unit/test_ui_componer.py`): `sys.modules.pop`/
        # `.update` restauran la entrada de `sys.modules`, pero NO el atributo del paquete padre
        # (p. ej. `ui.paginas.componer`, el atributo, no la clave del diccionario). El `import`
        # perezoso de mas arriba (dentro del `with`) deja ese atributo apuntando a la copia fria
        # sin `ml`; sin este paso queda asi para el resto de la sesion de pytest, y cualquier
        # prueba posterior que resuelva por una ruta de texto (`monkeypatch.setattr("ui.paginas.
        # componer.X", ...)`, que resuelve por ese atributo via `getattr`, no por `sys.modules`)
        # parcha la copia huerfana en vez de la que de verdad se ejecuta. Se sincroniza cada
        # atributo de paquete con lo que quedo en `sys.modules` (o se borra, si el modulo no
        # existia antes de `__enter__`).
        for nombre in _MODULOS_RELACIONADOS_CON_ML:
            if "." not in nombre:
                continue  # modulo de nivel superior: no hay atributo de paquete padre que fijar
            nombre_paquete, atributo = nombre.rsplit(".", 1)
            paquete = sys.modules.get(nombre_paquete)
            if paquete is None:
                continue  # el paquete padre tampoco esta cargado: nada que sincronizar
            if nombre in sys.modules:
                setattr(paquete, atributo, sys.modules[nombre])
            elif hasattr(paquete, atributo):
                delattr(paquete, atributo)


def test_la_pagina_de_componer_se_importa_sin_el_extra_ml(monkeypatch):
    """RF de arranque (spec §3.7): la interfaz sigue arrancando sin el extra `ml`; las cuatro
    ayudas simplemente no aparecen (cada una degrada a "sin sugerencia" al intentar usarse).
    """
    import importlib

    with _SinExtraML(monkeypatch):
        modulo_composicion = importlib.import_module("ui.composicion")
        modulo_pagina = importlib.import_module("ui.paginas.componer")

    assert modulo_composicion is not None
    assert modulo_pagina is not None
