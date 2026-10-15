"""RNF-15, la causa y no el síntoma: leer una obra para controlarla no hace una consulta por
partida. `cargar_presupuesto` carga de forma perezosa (unas tres consultas por renglón), y para 500
partidas eso es lo que lleva el control sobre los 2 s de RNF-15. La prueba no mide tiempo (varía
con la máquina): cuenta las sentencias SQL de `instantanea_control` y exige que no crezcan con el
número de partidas.
"""

from __future__ import annotations

from sqlalchemy import event

from core.budget import valuaciones
from core.budget.valuaciones import instantanea_control
from core.catalog import Catalogo, abrir_sesion, crear_motor
from scripts import generar_obra_control as generador
from scripts import medir_rnf15

MAXIMO_DE_SENTENCIAS = 40  # medido: 25 con 20 y con 120 partidas; sin precarga, 20 + 3 por partida


def _sentencias(tmp_path, partidas: int) -> int:
    base, _obra = medir_rnf15.preparar(tmp_path, partidas, 8, 4)
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    cuenta = []
    event.listen(motor, "before_cursor_execute", lambda *args: cuenta.append(1))
    try:
        with abrir_sesion(motor) as sesion:
            instantanea_control(sesion, generador.NOMBRE, catalogo=Catalogo(sesion))
    finally:
        motor.dispose()
    return len(cuenta)


def test_leer_la_obra_no_hace_una_consulta_por_partida(tmp_path):
    chica = _sentencias(tmp_path / "a", 20)
    grande = _sentencias(tmp_path / "b", 120)
    assert grande <= MAXIMO_DE_SENTENCIAS, grande
    assert grande - chica <= 2, (chica, grande)  # no crece con las partidas


def test_sin_la_precarga_la_cuenta_si_crece_con_las_partidas(tmp_path, monkeypatch):
    """Guardia de la prueba anterior (auditoría final, 2026-10-13): sin `_precargar` la lectura
    vuelve a hacer consultas por renglón y pasa del tope; si no, la prueba no vigilaría nada."""
    monkeypatch.setattr(valuaciones, "_precargar", lambda *_args: [])
    chica = _sentencias(tmp_path / "a", 20)
    grande = _sentencias(tmp_path / "b", 120)
    assert grande > MAXIMO_DE_SENTENCIAS, grande
    assert grande - chica >= 100, (chica, grande)  # unas tres por partida: 100 partidas más
