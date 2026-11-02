"""Ronda 1 del árbitro, punto 3: los mensajes del núcleo que llegan a «Reajuste de precios».

Los mensajes nacen en `core/budget/reajuste.py` (intocable) sin tildes y con datos adentro
(códigos de partida y de versión, series, fechas). La capa de aplicación reutiliza el catálogo
de frases de `aplicacion.control` (T8b): frase fija con huecos, el texto del usuario intacto fuera
y dentro de su hueco, las fechas del sistema (y solo ellas) en dd/mm/aaaa. Oráculos con tilde
escritos a mano.
"""

from __future__ import annotations

import ast
import re
import time
from pathlib import Path

import pytest

from aplicacion.reajuste import PLANTILLAS_DE_REAJUSTE, con_tildes_de_reajuste

RAIZ = Path(__file__).resolve().parents[2]

# (mensaje tal como lo emite el núcleo, el mismo con tildes). Una fila por plantilla.
CASOS = [
    (
        "una partida con costo directo cero no tiene pesos por componente",
        "una partida con costo directo cero no tiene pesos por componente",
    ),
    ("el estudio necesita al menos un periodo", "el estudio necesita al menos un período"),
    ("los periodos van en orden y sin solaparse", "los períodos van en orden y sin solaparse"),
    (
        "las series FIC-MAT, FIC-EQU no estan importadas (UC-17)",
        "las series FIC-MAT, FIC-EQU no están importadas (UC-17)",
    ),
    (
        "la version de comprobacion '009' no existe en el proyecto (UC-18 4)",
        "la versión de comprobación '009' no existe en el proyecto (UC-18 4)",
    ),
    (
        "la version 002 no valora S1-R01, S1-R02: no sirve de comprobacion para ese periodo",
        "la versión 002 no valora S1-R01, S1-R02: no sirve de comprobación para ese período",
    ),
    ("el estudio 4 no es de la version 001", "el estudio 4 no es de la versión 001"),
    (
        "el estudio 4 esta cerrado: solo un parcial se reemplaza",
        "el estudio 4 está cerrado: solo un parcial se reemplaza",
    ),
    (
        "un parcial se reemplaza una sola vez (S1-R21)",
        "un parcial se reemplaza una sola vez (S1-R21)",
    ),
    (
        "el estudio que reemplaza a un parcial debe estar cerrado (S1-R21)",
        "el estudio que reemplaza a un parcial debe estar cerrado (S1-R21)",
    ),
    (
        "el estudio exige fuente y responsable (UC-18 6)",
        "el estudio exige fuente y responsable (UC-18 6)",
    ),
    (
        "cada cantidad ejecutada exige su fuente: acta o valuacion (UC-18 2)",
        "cada cantidad ejecutada exige su fuente: acta o valuación (UC-18 2)",
    ),
    ("no hay ningun estudio de reajuste 12", "no hay ningún estudio de reajuste 12"),
    (
        "la duracion del contrato debe ser positiva",
        "la duración del contrato debe ser positiva",
    ),
    (
        "el mes base de los indices se declara con su primer dia (S1-R10)",
        "el mes base de los índices se declara con su primer día (S1-R10)",
    ),
    ("R va en [0, 1) con su fuente (S1-R8)", "R va en [0, 1) con su fuente (S1-R8)"),
    ("la clausula exige fuente y responsable", "la cláusula exige fuente y responsable"),
    (
        "mecanismo_pagadero solo con 'ambos', uno de los dos y con su fuente",
        "mecanismo_pagadero solo con 'ambos', uno de los dos y con su fuente",
    ),
    ("componente repetido en la clausula", "componente repetido en la cláusula"),
    (
        "la cantidad ejecutada de S1-R01 no puede ser negativa",
        "la cantidad ejecutada de S1-R01 no puede ser negativa",
    ),
    (
        "el periodo 01/02/2027-28/02/2027 del estudio 3 no recalcula igual a lo guardado (RNF-14)",
        "el período 01/02/2027-28/02/2027 del estudio 3 no recalcula igual a lo guardado (RNF-14)",
    ),
    (
        "por_partida exige materiales, equipos y mano_obra con su serie",
        "por_partida exige materiales, equipos y mano_obra con su serie",
    ),
    (
        "la estructura declarada exige el peso de cada componente",
        "la estructura declarada exige el peso de cada componente",
    ),
    (
        "los pesos de la estructura declarada suman 0.9, no 1 (§8.1)",
        "los pesos de la estructura declarada suman 0.9, no 1 (§8.1)",
    ),
    (
        "la partida S1-R09 no esta en la version del contrato",
        "la partida S1-R09 no está en la versión del contrato",
    ),
    # Las tres fechas son del sistema (ISO en el núcleo): solo ellas pasan a dd/mm/aaaa.
    (
        "el periodo 2027-01-01–2027-01-31 cruza el aniversario 2027-01-15: partalo (UC-18 3b)",
        "el período 01/01/2027–31/01/2027 cruza el aniversario 15/01/2027: pártalo (UC-18 3b)",
    ),
    (
        "el estudio 3 cita la importacion 7 de FIC-MAT al 01/02/2027, que ya no esta en la base",
        "el estudio 3 cita la importación 7 de FIC-MAT al 01/02/2027, que ya no está en la base",
    ),
]


@pytest.mark.parametrize(("emitido", "esperado"), CASOS)
def test_cada_mensaje_del_nucleo_sale_con_tilde(emitido: str, esperado: str) -> None:
    assert con_tildes_de_reajuste(emitido) == esperado


@pytest.mark.parametrize(
    ("emitido", "esperado"),
    [
        # El código de la partida, de la versión o la serie con forma de fecha los escribió el
        # usuario: no se tocan (la lección del punto 1).
        (
            "la partida 2026-11-10 no esta en la version del contrato",
            "la partida 2026-11-10 no está en la versión del contrato",
        ),
        (
            "la version de comprobacion '2026-11-10' no existe en el proyecto (UC-18 4)",
            "la versión de comprobación '2026-11-10' no existe en el proyecto (UC-18 4)",
        ),
        (
            "las series serie 2026-11-10 no estan importadas (UC-17)",
            "las series serie 2026-11-10 no están importadas (UC-17)",
        ),
        (
            "la cantidad ejecutada de dia ningun periodo no puede ser negativa",
            "la cantidad ejecutada de dia ningun periodo no puede ser negativa",
        ),
        # Una «fecha» imposible en un hueco de fecha se deja como vino.
        (
            "el periodo 2027-02-30–2027-03-31 cruza el aniversario 2027-01-15: partalo (UC-18 3b)",
            "el período 2027-02-30–31/03/2027 cruza el aniversario 15/01/2027: pártalo (UC-18 3b)",
        ),
    ],
)
def test_el_texto_del_usuario_no_se_altera(emitido: str, esperado: str) -> None:
    assert con_tildes_de_reajuste(emitido) == esperado


@pytest.mark.parametrize(
    "libre",
    ["texto libre sin catalogar", "", "la partida", "el periodo no es un mensaje del nucleo"],
)
def test_lo_que_no_esta_catalogado_pasa_tal_cual(libre: str) -> None:
    assert con_tildes_de_reajuste(libre) == libre


def test_la_funcion_es_idempotente() -> None:
    for _emitido, esperado in CASOS:
        assert con_tildes_de_reajuste(esperado) == esperado


# --- guardia: un mensaje nuevo o cambiado del núcleo no puede llegar sin catalogar ---------------


def _fragmentos_de_raise(ruta: Path) -> set[str]:
    """Los trozos de texto literal (con espacio) de los mensajes de `raise` de un módulo."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    trozos: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Raise) and nodo.exc is not None:
            for hijo in ast.walk(nodo.exc):
                if (
                    isinstance(hijo, ast.Constant)
                    and isinstance(hijo.value, str)
                    and " " in hijo.value.strip()
                ):
                    trozos.add(hijo.value)
    return trozos


def test_ningun_mensaje_del_nucleo_de_reajuste_queda_sin_catalogar() -> None:
    crudos = [crudo for crudo, _ in PLANTILLAS_DE_REAJUSTE]
    sin_catalogar = sorted(
        f"{ruta.name}: {trozo!r}"
        for ruta in (
            RAIZ / "core" / "budget" / "reajuste.py",
            RAIZ / "core" / "budget" / "puente.py",
        )
        for trozo in _fragmentos_de_raise(ruta)
        if not any(trozo.strip() in crudo for crudo in crudos)
    )
    assert sin_catalogar == [], "mensajes del núcleo sin catalogar:\n" + "\n".join(sin_catalogar)


def test_cada_plantilla_la_ejerce_un_caso_escrito_a_mano() -> None:
    emitidos = [e for e, _ in CASOS]
    for crudo, _ in PLANTILLAS_DE_REAJUSTE:
        patron = re.sub(r"\\\{[a-z_]+\\\}", ".+", re.escape(crudo))
        assert any(re.fullmatch(patron, e) for e in emitidos), crudo


# --- robustez: texto hostil, largo y con los separadores de las plantillas -----------------------

N = 100_000


def _adversariales(n: int) -> dict[str, str]:
    return {
        "partida": "la partida " + "no esta en la version del contrato " * (n // 35) + "x",
        "series": "las series " + "no estan importadas (UC-17) " * (n // 28) + "!",
        "valora": "la version 1 no valora " + ": no sirve de comprobacion " * (n // 27) + "z",
        "aniversario": "el periodo 2027-01-01–" + "2027-01-31 cruza el aniversario " * (n // 32),
        "importacion": "el estudio 3 cita la importacion 7 de "
        + " al 01/02/2027, que ya no " * (n // 26)
        + "q",
        "comprobacion": "la version de comprobacion " + "' no existe en el proyecto " * (n // 27),
    }


@pytest.mark.parametrize("n", [N, 1_900])
@pytest.mark.parametrize(
    "nombre", ["partida", "series", "valora", "aniversario", "importacion", "comprobacion"]
)
def test_un_texto_adversarial_vuelve_intacto_en_menos_de_un_segundo(nombre: str, n: int) -> None:
    texto = _adversariales(n)[nombre]
    inicio = time.perf_counter()
    salida = con_tildes_de_reajuste(texto)
    segundos = time.perf_counter() - inicio
    print(f"{nombre} n={n}: {segundos:.4f} s")
    assert salida == texto
    assert segundos < 1.0
