"""Pruebas de la meta de datos: la documentacion no presenta los datos del repositorio como reales.

La sesion de limpieza (2026-09-15) corrigio 69 afirmaciones en 29 archivos. Esta meta existe para
que no vuelvan: `scripts/meta_redaccion.py` solo vigila los capitulos de la tesis (R7), y la
contradiccion estaba fuera de ellos.

Cada chequeo es una funcion pura sobre texto, igual que en las demas metas del proyecto.
"""

from __future__ import annotations

from scripts import meta_datos as meta
from scripts.meta_alpha import Estado

# --- Que oraciones se reportan ------------------------------------------------------------


def test_presupuesto_presentado_como_real_se_reporta():
    texto = "Se audito un presupuesto real elaborado por el procedimiento tradicional."

    assert meta.oraciones_como_reales(texto) == [
        "Se audito un presupuesto real elaborado por el procedimiento tradicional."
    ]


def test_apu_declarado_didactico_no_se_reporta():
    texto = "Los APU del caso son un ejercicio didactico, no valores reales de una obra."

    assert meta.oraciones_como_reales(texto) == []


def test_datos_que_el_usuario_suministre_despues_no_se_reportan():
    """La propia fuente unica (CLAUDE.md seccion 1) habla de APU reales en futuro."""
    texto = "Cuando se suministren APU de casos reales, se incorporaran como evidencia adicional."

    assert meta.oraciones_como_reales(texto) == []


def test_rendimientos_reales_de_obra_no_se_reportan():
    """UC-06 mide rendimientos de obra ejecutada: es vocabulario del dominio, no una afirmacion
    sobre los datos.
    """
    texto = "Registrar y consultar rendimientos reales de obra ejecutada."

    assert meta.oraciones_como_reales(texto) == []


def test_un_mensaje_de_commit_citado_no_se_reporta():
    """Sobre el repositorio real: `PLAN_MULTIDOMINIO.md` cita mensajes de commit ya hechos, que no
    se reescriben porque son historia. Lo que va entre comillas invertidas se cita, no se afirma.
    """
    texto = "**Commit.** `feat(industrial): presupuesto de mantenimiento auditado con datos reales`"

    assert meta.oraciones_como_reales(texto) == []


def test_la_nota_de_errata_que_cita_la_redaccion_vieja_no_se_reporta():
    """Sobre el repositorio real: la errata de `data/telecom/fuentes/README.md` tiene que poder
    citar entre comillas angulares lo que decia antes para declararlo corregido.
    """
    texto = (
        "Las sesiones M1.1-M4.2 los trataron como «presupuestos reales» y "
        "«segunda linea base real»."
    )

    assert meta.oraciones_como_reales(texto) == []


def test_una_lista_de_precios_publicada_no_se_reporta():
    texto = "El catalogo se costea con la lista de precios publicada y fechada de MaPreX."

    assert meta.oraciones_como_reales(texto) == []


# --- La meta sobre varios documentos ------------------------------------------------------


def test_meta_falla_nombrando_documento_y_oracion():
    textos = {
        "PLAN.md": "La segunda linea base real de la tesis esta en telecom.",
        "otro.md": "Todo correcto.",
    }

    estado, evidencia = meta.evaluar_documentos(textos)

    assert estado is Estado.FALLA
    assert "PLAN.md" in evidencia and "linea base real" in evidencia
    assert "otro.md" not in evidencia


def test_meta_ok_con_documentos_limpios():
    textos = {"PLAN.md": "Los presupuestos del repositorio son ejercicios academicos ficticios."}

    estado, evidencia = meta.evaluar_documentos(textos)

    assert estado is Estado.OK, evidencia


def test_meta_sin_documentos_queda_pendiente():
    assert meta.evaluar_documentos({})[0] is Estado.PENDIENTE


# --- Las notas de errata de los documentos historicos --------------------------------------


def test_errata_falta_en_un_documento_historico():
    textos = {
        "PLAN_MULTIDOMINIO.md": "> **Errata (2026-09-15).** Son ejercicios ficticios.",
        "PLAN_DESARROLLO.md": "Sin nota.",
    }

    estado, evidencia = meta.evaluar_errata(textos)

    assert estado is Estado.FALLA
    assert "PLAN_DESARROLLO.md" in evidencia and "PLAN_MULTIDOMINIO.md" not in evidencia


def test_errata_presente_en_todos():
    textos = {
        "PLAN_MULTIDOMINIO.md": "> **Errata (2026-09-15).** Son ejercicios ficticios.",
        "PLAN_DESARROLLO.md": "> **Errata (2026-09-15).** Es un ejercicio academico ficticio.",
    }

    assert meta.evaluar_errata(textos)[0] is Estado.OK


# --- Que archivos se vigilan ----------------------------------------------------------------


def test_se_vigila_la_documentacion_del_proyecto():
    for relativo in ("CLAUDE.md", "README.md", "PLAN_MULTIDOMINIO.md", "docs/ERS.md"):
        assert meta.es_vigilado(relativo), relativo


def test_no_se_vigilan_los_registros_fechados_ni_los_capitulos():
    """Bitacoras, specs y planes de sprints ya ejecutados registran lo que se sabia en su fecha;
    los capitulos los vigila `meta_redaccion.py` (R7), y `.venv` no es del proyecto.

    `.superpowers/` tampoco lo es: es el cuaderno de trabajo de los agentes, no esta rastreado por
    git (vive en `.git/info/exclude`) y no viaja con ninguna fusion. Vigilarlo hacia fallar D1 por
    una frase de un informe efimero -- «una fila real del CSV», dicho de una fila que existe en el
    archivo-- mientras la documentacion del proyecto estaba limpia. Un control que falla por
    borradores que nadie publica ensena a ignorar sus fallos.
    """
    for relativo in (
        "docs/bitacora/2026-09-02-M4.1-recuento-g2.md",
        "docs/superpowers/specs/2026-09-15-sprint-r1-capitulos-design.md",
        "docs/superpowers/plans/2026-09-02-sprint-multidominio.md",
        "docs/tesis/capitulos/01-el-problema.md",
        ".superpowers/sdd/un-plan/task-2-report.md",
        ".venv/Lib/site-packages/algo.md",
        "scripts/meta_datos.py",
    ):
        assert not meta.es_vigilado(relativo), relativo
