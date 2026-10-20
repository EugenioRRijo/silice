"""Rendimiento y tamano de las vistas de la hoja con 500 puntos (T10, 3b-2; diseno 3b-B22 y 3b-B23).

Como RNF-11 (`tests/unit/test_medir_rnf11.py`), esta prueba SOLO registra: no afirma ningun tiempo
(una prueba de tiempo seria fragil con la carga de la maquina). Comprueba el procedimiento (una
corrida de calentamiento y la mediana de cinco, con el reloj de `scripts.medir_rnf11`) y que las
siete vistas del borrador se arman sobre los 500 puntos del generador determinista. La cifra se
anota en `docs/bitacora/2026-10-19-hoja-3b2-avance.md` (R5 a R8) y en
`docs/bitacora/2026-10-19-hoja-3b3-backend-avance.md` (R5 a R11: R9 a R11 son las vistas de la
3b-3 que leen el borrador vivo; R12 a R14 leen la base y no entran aqui).
"""

from __future__ import annotations

from datetime import date

from aplicacion import hoja, hoja_vista
from aplicacion.hoja_borradores import Registro
from scripts import medir_rnf11 as medir
from scripts.generar_hoja_prueba import PARAMETROS_PRUEBA, composiciones_de_prueba, generar_items

HOY = date(2026, 10, 19)
PUNTOS = 500


def _vivo(puntos: int = PUNTOS):
    plan = None
    borrador = hoja.Borrador(
        fecha=HOY,
        items_base=tuple(generar_items(puntos, medir.SEMILLA)),
        composiciones=composiciones_de_prueba(),
        parametros=PARAMETROS_PRUEBA,
    )
    plan = tuple(hoja.con_plan_secuencial(borrador).plan or ())
    borrador = hoja.Borrador(**{**_campos(borrador), "plan": plan})
    return Registro().crear("f", "caso", "Carga", None, borrador, None)


def _campos(borrador):
    import dataclasses

    return {c.name: getattr(borrador, c.name) for c in dataclasses.fields(borrador)}


def _las_siete_vistas(vivo, _: int = 0):
    vivo.calculo = None  # cada corrida elabora de nuevo, como tras una edicion
    return (
        hoja_vista.vista_espacio(vivo),
        hoja_vista.vista_presupuesto(vivo),
        hoja_vista.vista_apu(vivo),
        hoja_vista.vista_plan(vivo),
        hoja_vista.vista_equilibrio(vivo),
        hoja_vista.vista_parametros(vivo, "USD", True),
        hoja_vista.informe_de_auditoria(vivo),
    )


def test_las_siete_vistas_se_arman_con_500_puntos_y_la_mediana_se_registra():
    vivo = _vivo()
    espacio, presupuesto, apu, plan, equilibrio, parametros, informe = _las_siete_vistas(vivo)
    assert len(presupuesto.filas) == PUNTOS
    assert len(apu.partidas) == 8 and apu.detalle is not None  # las 8 partidas sinteticas
    assert plan.hay_plan and len(plan.curva) == len({p.periodo for p in plan.curva})
    assert espacio.derivadas == ()  # la carga son items de la version, no un espacio
    assert equilibrio.estado in {"calculado", "no_se_alcanza"} and len(parametros.campos) == 4
    assert "R17" in [codigo for codigo, _, _ in informe.cuenta_por_regla_evaluada()]

    medicion = medir.medir(lambda i: _las_siete_vistas(vivo, i))
    assert len(medicion.corridas) == medir.CORRIDAS == 5
    assert medicion.mediana >= 0  # solo se registra: ningun umbral
    print(f"3b-B22 vistas R5-R11 con {PUNTOS} puntos: mediana {medicion.mediana:.3f} s")


def test_el_tamano_del_borrador_de_500_puntos_se_registra():
    tamano = _vivo().tamano  # `len(pickle.dumps)` o, si no se serializa, el recorrido de objetos
    print(f"3b-B23 tamano estimado del borrador con {PUNTOS} puntos: {tamano} bytes")
    assert tamano > 0
