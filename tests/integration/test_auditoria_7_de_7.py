"""Prueba de aceptación crítica de la Sesión I4: 7 de 7 (indicador 1 de la tesis).

El presupuesto auditado reproduce las siete inconsistencias documentadas en `docs/linea_base.md`.
El informe se genera siempre y debe señalar las siete, cada una con la regla que le corresponde y
la partida involucrada, sin que el núcleo conozca el dominio civil.

Ninguna prueba de este archivo se omite por su cuenta: el `importorskip` de `core.budget` que
protegía a la última mientras I0.5 no existía convertiría hoy una regresión del núcleo en un
*skip* silencioso justo en la prueba del indicador 1 de la tesis (revisión final, ítem 6).
"""

from __future__ import annotations

from core.contracts import Severidad
from core.verification import auditar
from core.verification.reglas import NO_APLICABLE
from tests.fixtures.apu_linea_base import HALLAZGOS_ADICIONALES, INCONSISTENCIAS
from tests.fixtures.presupuesto_auditado import (
    presupuesto_con_siete_inconsistencias,
    presupuesto_corregido,
)


def _detectadas(informe) -> set[tuple[str, str | None]]:
    return {
        (hallazgo.regla, informe.partida_de(hallazgo))
        for hallazgo in informe.hallazgos
        if hallazgo.severidad >= Severidad.ERROR
    }


def test_detecta_las_siete_inconsistencias():
    informe = auditar(presupuesto_con_siete_inconsistencias())

    esperadas = {(i.regla, i.codigo_partida) for i in INCONSISTENCIAS}
    detectadas = _detectadas(informe)

    assert len(esperadas) == 7
    assert esperadas <= detectadas, f"no detectadas: {sorted(esperadas - detectadas, key=str)}"
    assert len(esperadas & detectadas) == 7


def test_detecta_los_hallazgos_adicionales_8_y_9():
    informe = auditar(presupuesto_con_siete_inconsistencias())
    detectadas = _detectadas(informe)

    octavo, noveno = HALLAZGOS_ADICIONALES
    assert (octavo.regla, octavo.codigo_partida) in detectadas
    # El noveno (plan de trabajo día a día) no se atribuye a una sola partida: el contrato
    # `PuntoCurva` no lleva código de partida, así que R7 reporta una componente conexa por grupo
    # de períodos y partidas enlazadas. Basta con que la regla lo señale.
    assert noveno.regla in {regla for regla, _ in detectadas}


def test_todo_hallazgo_de_partida_referencia_un_origen_trazable():
    """Trazabilidad total (CLAUDE.md §2.6): salvo el cierre de la curva y la declaración de R7 no
    aplicable (INV‑012), que son propiedades del presupuesto completo, todo hallazgo referencia
    orígenes que el informe sabe atribuir.
    """
    presupuesto = presupuesto_con_siete_inconsistencias()
    informe = auditar(presupuesto)
    codigos = {partida.item.codigo_partida for partida in presupuesto.partidas}

    for hallazgo in informe.hallazgos:
        if hallazgo.regla == "R2":
            continue
        # Salto defensivo: el fixture trae curva, así que R7 no entra hoy en la rama «no
        # aplicable». Se conserva para que la prueba no dependa de ese detalle del fixture.
        if (
            hallazgo.regla == "R7"
            and NO_APLICABLE in hallazgo.descripcion
            and hallazgo.severidad is Severidad.INFO
        ):
            continue
        assert hallazgo.origen_ids, hallazgo.descripcion
        assert informe.partida_de(hallazgo) in codigos, hallazgo.descripcion


def test_el_presupuesto_corregido_no_tiene_errores():
    informe = auditar(presupuesto_corregido())
    assert informe.cumple, informe.a_markdown()
