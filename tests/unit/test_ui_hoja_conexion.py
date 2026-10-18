"""R17 en la pantalla de la hoja: siempre ligada al espacio VIGENTE (tarea 1.7).

`ui/hoja.py` esta congelado por el protocolo del experimento, asi que R17 no entra en
`elaborar_hoja` ni en `abrir_version`: la agrega la pagina en cada elaboracion y antes de guardar,
sobre el borrador que se elabora (`_con_conexion`). Nunca se guarda en el borrador de la sesion: un
R17 guardado ahi quedaria ligado al espacio de ese momento y se volveria viejo al editar.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from adapters.espacio.conexion import CODIGO_R17
from adapters.espacio.modelo import (
    Ambiente,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    Punto,
    SuperficiePunto,
    TipoFuente,
    TipoPunto,
)
from adapters.espacio.origen import OrigenMedida, TipoOrigen
from core.contracts import Hallazgo, ReglaVerificacion, Severidad
from ui import hoja
from ui.paginas import hoja as pagina

D = Decimal
LEV = OrigenMedida(
    id="LEV", tipo=TipoOrigen.LEVANTAMIENTO, referencia={"fecha": "2026-10-01", "responsable": "EP"}
)
AMBIENTE = Ambiente("A", "Bano", D("0"), D("0"), D("3"), D("2"), D("2.5"), "LEV")
FUENTE = Fuente(
    "F", Especialidad.AGUA, TipoFuente.ACOMETIDA_AGUA, "A", Coord(D(0), D(0), D("0.5")), "LEV"
)


def _punto(fuente_id: str | None) -> Punto:
    return Punto(
        id="P2",
        nombre="lavamanos",
        especialidad=Especialidad.AGUA,
        tipo=TipoPunto.AGUA_FRIA,
        ambiente_id="A",
        superficie=SuperficiePunto.PARED,
        posicion=Coord(D("2"), D("0"), D("0.6")),
        origen_id="LEV",
        fuente_id=fuente_id,
        especificaciones={"diametro": '1/2"', "llave_de_paso": "si"},
    )


def _espacio(fuente_id: str | None) -> Espacio:
    return Espacio(
        origenes=(LEV,), ambientes=(AMBIENTE,), fuentes=(FUENTE,), puntos=(_punto(fuente_id),)
    )


SIN_FUENTE = _espacio(None)
CON_FUENTE = _espacio("F")


class _Otra(ReglaVerificacion):
    """Una regla extra cualquiera (en la pantalla, R11 y R12 de `abrir_version`)."""

    codigo = "R11"
    nombre = "otra"

    def evaluar(self, presupuesto):
        return []


def _r17(borrador: hoja.Borrador) -> list[ReglaVerificacion]:
    return [r for r in borrador.reglas_extra if r.codigo == CODIGO_R17]


def test_con_conexion_liga_r17_al_espacio_del_borrador_y_conserva_las_otras_extra():
    otra = _Otra()
    borrador = hoja.Borrador(fecha=date(2026, 10, 18), espacio=SIN_FUENTE, reglas_extra=(otra,))
    ligado = pagina._con_conexion(borrador)
    (r17,) = _r17(ligado)
    assert r17.espacio is SIN_FUENTE
    assert ligado.reglas_extra[0] is otra
    assert hoja.cambios_entre(borrador, ligado) == []  # no es un cambio sin guardar


def test_con_conexion_reemplaza_un_r17_viejo_por_el_del_espacio_vigente():
    viejo = pagina._con_conexion(hoja.Borrador(fecha=date(2026, 10, 18), espacio=SIN_FUENTE))
    editado = replace(viejo, espacio=CON_FUENTE)  # el usuario le asigno la fuente
    ligado = pagina._con_conexion(editado)
    (r17,) = _r17(ligado)
    assert r17.espacio is CON_FUENTE
    assert len(_r17(pagina._con_conexion(ligado))) == 1  # ligar dos veces no la duplica


def test_la_hoja_muestra_el_aviso_en_la_fila_del_punto_y_desaparece_al_corregir():
    sin = pagina._elaborar(hoja.Borrador(fecha=date(2026, 10, 18), espacio=SIN_FUENTE))
    avisos = [h for h in sin.elaboracion.informe.hallazgos if h.regla == CODIGO_R17]
    assert avisos == [
        Hallazgo(
            regla="R17",
            severidad=Severidad.ADVERTENCIA,
            descripcion=(
                "El punto P2 (lavamanos) no tiene fuente: el presupuesto no incluye cómo le llega "
                "el agua. Asígnele su acometida o montante, o déjelo así si es a propósito."
            ),
            origen_ids=("esp_puntos:P2",),
        )
    ]
    fila = sin.estado["esp_puntos:P2"]
    assert "no tiene fuente" in fila.texto
    # el borrador corregido, aunque traiga el R17 viejo, se elabora con el de su espacio
    viejo = pagina._con_conexion(hoja.Borrador(fecha=date(2026, 10, 18), espacio=SIN_FUENTE))
    con = pagina._elaborar(replace(viejo, espacio=CON_FUENTE))
    assert [h for h in con.elaboracion.informe.hallazgos if h.regla == CODIGO_R17] == []
    assert "no tiene fuente" not in con.estado["esp_puntos:P2"].texto


# --- guardia: ninguna elaboracion ni guardado de la pagina se salta R17 --------------------------

FUENTE_PAGINA = Path(pagina.__file__).read_text(encoding="utf-8")
ARBOL = ast.parse(FUENTE_PAGINA)


def _llamadas(nombre: str) -> list[tuple[ast.Call, str]]:
    """Las llamadas `<modulo>.<nombre>(...)` de la pagina con la funcion que las contiene."""
    encontradas: list[tuple[ast.Call, str]] = []
    for funcion in ast.walk(ARBOL):
        if not isinstance(funcion, ast.FunctionDef):
            continue
        for nodo in ast.walk(funcion):
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == nombre
            ):
                encontradas.append((nodo, funcion.name))
    return encontradas


def _es_con_conexion(nodo: ast.expr) -> bool:
    return (
        isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Name)
        and nodo.func.id == "_con_conexion"
    )


def test_la_pagina_solo_elabora_por_elaborar_que_agrega_r17():
    llamadas = _llamadas("elaborar_borrador")
    assert llamadas  # la guardia mira algo
    assert {f for _, f in llamadas} == {"_elaborar"}


def test_guardar_y_el_resultado_hipotetico_reciben_el_borrador_con_r17():
    for nombre, posicion in (
        ("guardar_version", 3),
        ("crear_primera_version", 3),
        ("resumen_hipotetico", 0),
    ):
        llamadas = _llamadas(nombre)
        assert llamadas, nombre
        for llamada, _ in llamadas:
            assert _es_con_conexion(llamada.args[posicion]), nombre
