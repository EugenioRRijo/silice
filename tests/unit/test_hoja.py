"""`ui.hoja` (tarea 1.8): borrador -> items -> presupuesto auditado, contra la memoria a mano.

El baño de OF-001 sale de `tests/fixtures/memorias/bano_of001.md` (las cantidades no se copian):
la hoja las deriva, las valora con APU sintéticos de un solo material y las audita con
`REGLAS + reglas_espacio`. Cubre FR-1 (espacio vacío) y FR-5 (un presupuesto sin espacio abre).
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.espacio import (
    Coord,
    Espacio,
    OrigenMedida,
    TipoOrigen,
    crear_esquema_espacio,
)
from core.budget import elaborar, plan_secuencial
from core.catalog import abrir_sesion, crear_motor
from core.contracts import ComposicionAPU, ItemComputo, ParametrosCosto
from core.contracts.apu import LineaMaterial
from core.contracts.verificacion import Severidad
from tests.fixtures.apu_linea_base import FECHA_LINEA_BASE, MONEDA, PARAMETROS_LINEA_BASE
from tests.fixtures.computo_auditado import composiciones_linea_base, items_auditados
from tests.fixtures.espacio_bano import espacio_bano
from ui import hoja

D = Decimal
MEMORIA = Path(__file__).resolve().parents[1] / "fixtures" / "memorias" / "bano_of001.md"
FECHA = FECHA_LINEA_BASE
PRECIO_MATERIAL = D("2")


def _memoria() -> dict:
    texto = MEMORIA.read_text(encoding="utf-8")
    return json.loads(re.findall(r"```json\n(.*?)\n```", texto, flags=re.DOTALL)[0])


def _composiciones(items: list[ItemComputo]) -> dict[str, ComposicionAPU]:
    """Un APU por código: un material de cantidad 1 a PRECIO_MATERIAL, rendimiento 1."""
    return {
        i.codigo_partida: ComposicionAPU(
            codigo_partida=i.codigo_partida,
            descripcion=i.descripcion,
            unidad=i.unidad,
            rendimiento=D("1"),
            materiales=(LineaMaterial("material", i.unidad, D("1"), PRECIO_MATERIAL),),
        )
        for i in items
    }


def _limpio() -> Espacio:
    """El baño con un origen de levantamiento (sin supuestos): sin ruido de R8."""
    base = espacio_bano()
    levantamiento = OrigenMedida(
        id="O1",
        tipo=TipoOrigen.LEVANTAMIENTO,
        referencia={"fecha": "2026-10-05", "responsable": "E"},
    )
    return replace(base, origenes=(levantamiento,))


def _elaborar(espacio: Espacio, **kw) -> hoja.ResultadoHoja:
    items = hoja.items_del_borrador(espacio, "agua")
    return hoja.elaborar_hoja(
        espacio, _composiciones(items), codigo="OF-001", fecha=FECHA, **kw
    )


# --- borrador -> items -> presupuesto (memoria a mano) -----------------------------------------


def test_los_items_del_borrador_son_los_de_la_memoria():
    memoria = {p["partida"]: D(p["cantidad"]) for p in _memoria()["partidas"]}
    items = hoja.items_del_borrador(espacio_bano(), "agua")
    cantidades = {i.codigo_partida: i.cantidad for i in items}
    assert abs(cantidades["AF-TUB-PVC-3/4"] - memoria["tuberia_3/4"]) <= D("0.001")
    assert abs(cantidades["AF-TUB-PVC-1/2"] - memoria["tuberia_1/2"]) <= D("0.001")
    assert cantidades["AF-LLAVE"] == memoria["llave_de_paso"]
    assert cantidades["AF-SALIDA"] == memoria["salida_agua"]
    assert abs(cantidades["AF-PICADO-PARED"] - memoria["picado_resane_pared"]) <= D("0.001")


def test_el_presupuesto_del_bano_es_el_de_la_memoria_y_cumple_las_siete_reglas():
    resultado = _elaborar(_limpio())
    memoria = _memoria()["partidas"]
    cantidad_total = sum((D(p["cantidad"]) for p in memoria), D(0))
    # PU = material * (1 + admin) * (1 + utilidad); total = suma de cantidad * PU
    pu = PRECIO_MATERIAL * (1 + ParametrosCosto().administracion) * (1 + ParametrosCosto().utilidad)
    assert abs(resultado.elaboracion.presupuesto.total - cantidad_total * pu) <= D("0.05")
    codigos = {c for c, _ in resultado.elaboracion.informe.reglas_evaluadas}
    assert {"R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"} <= codigos
    assert not [
        h for h in resultado.elaboracion.informe.hallazgos if h.severidad >= Severidad.ERROR
    ]
    assert resultado.items  # lo derivado del espacio


def test_las_reglas_del_espacio_se_pasan_a_elaborar_con_la_instantanea():
    espacio = _limpio()
    fuera = replace(
        espacio,
        puntos=(
            replace(espacio.puntos[0], posicion=Coord(D("9"), D("0"), D("0.6"))),
            espacio.puntos[1],
        ),
    )
    resultado = _elaborar(fuera)
    assert any(h.regla == "R9" for h in resultado.elaboracion.informe.hallazgos)


# --- Estado por fila ----------------------------------------------------------------------------


def test_el_estado_marca_solo_la_fila_sembrada():
    espacio = _limpio()
    sembrada = replace(
        espacio,
        puntos=(
            replace(espacio.puntos[0], posicion=Coord(D("9"), D("0"), D("0.6"))),
            espacio.puntos[1],
        ),
    )
    estado = _elaborar(sembrada).estado
    assert estado["esp_puntos:P1"].severidad is Severidad.ERROR
    assert "fuera del ambiente" in estado["esp_puntos:P1"].texto
    otras = {k: e for k, e in estado.items() if k != "esp_puntos:P1"}
    assert otras  # el resto de las filas existe en el estado
    assert all(e.severidad is None and e.texto == hoja.TEXTO_OK for e in otras.values())


def test_el_estado_agrupa_las_advertencias_de_una_fila_en_un_solo_texto():
    espacio = espacio_bano()  # origen supuesto en todas las filas
    sin_origen_pendiente = replace(
        espacio,
        puntos=(
            replace(
                espacio.puntos[0],
                especificaciones={"altura": "pendiente", **espacio.puntos[0].espec},
            ),
            espacio.puntos[1],
        ),
    )
    informe = _elaborar(sin_origen_pendiente).elaboracion.informe
    en_p1 = [h for h in informe.hallazgos if "esp_puntos:P1" in h.origen_ids]
    assert len(en_p1) >= 2  # supuesto y altura pendiente: dos hallazgos
    estado = hoja.estado_de_filas(sin_origen_pendiente, informe)["esp_puntos:P1"]
    assert estado.severidad is Severidad.ADVERTENCIA
    assert "\n" not in estado.texto
    assert estado.texto.startswith("ADVERTENCIA")
    assert estado.texto.count("ADVERTENCIA") == 1  # un solo rotulo para todas
    assert "supuesto" in estado.texto and "altura pendiente" in estado.texto


def test_el_estado_cubre_cada_fila_editable_y_sus_claves_son_las_de_los_hallazgos():
    espacio = _limpio()
    estado = _elaborar(espacio).estado
    claves = {f"esp_ambientes:{a.id}" for a in espacio.ambientes}
    claves |= {f"esp_fuentes:{f.id}" for f in espacio.fuentes}
    claves |= {f"esp_puntos:{p.id}" for p in espacio.puntos}
    assert claves <= set(estado)


# --- FR-1 y FR-5 --------------------------------------------------------------------------------


def test_espacio_vacio_no_deriva_nada_y_elabora_sin_romper():
    assert hoja.items_del_borrador(Espacio(), "agua") == []
    resultado = hoja.elaborar_hoja(Espacio(), {}, codigo="VACIO", fecha=FECHA)
    assert resultado.items == []
    assert resultado.estado == {}
    assert resultado.elaboracion.presupuesto.total == 0


def test_un_presupuesto_sin_espacio_abre_igual_que_antes_de_la_hoja():
    """[FR-5] La clinica: items de la version + espacio vacio = el presupuesto de `elaborar`."""
    items = list(items_auditados())
    esperado = elaborar(
        items,
        composiciones_linea_base(),
        PARAMETROS_LINEA_BASE,
        codigo="CLI",
        fecha=FECHA,
        moneda=MONEDA,
        plan=plan_secuencial,
    )
    resultado = hoja.elaborar_hoja(
        Espacio(),
        composiciones_linea_base(),
        items_base=items,
        parametros=PARAMETROS_LINEA_BASE,
        codigo="CLI",
        fecha=FECHA,
        moneda=MONEDA,
    )
    assert resultado.elaboracion.presupuesto.total == esperado.presupuesto.total
    assert resultado.items == []
    # las siete reglas dan lo mismo; R8 y R9 se declaran evaluadas y no agregan hallazgos
    nuevas = [h for h in resultado.elaboracion.informe.hallazgos if h.regla in {"R8", "R9"}]
    assert nuevas == []
    assert {"R8", "R9"} <= {c for c, _ in resultado.elaboracion.informe.reglas_evaluadas}
    assert len(resultado.elaboracion.informe.hallazgos) == len(esperado.informe.hallazgos)


def test_borrador_de_una_base_anterior_a_la_hoja_es_vacio(tmp_path):
    """[FR-5] Sin tablas esp_* la version abre con el espacio vacio y no escribe nada."""
    motor = crear_motor(f"sqlite:///{(tmp_path / 'vieja.db').as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            assert hoja.borrador_de_version(sesion, 1) == Espacio()
        assert "esp_ambientes" not in _tablas(motor)
    finally:
        motor.dispose()


def test_borrador_de_una_version_sin_filas_esp_es_vacio(tmp_path):
    motor = crear_motor(f"sqlite:///{(tmp_path / 'nueva.db').as_posix()}")
    crear_esquema_espacio(motor)
    try:
        with abrir_sesion(motor) as sesion:
            assert hoja.borrador_de_version(sesion, 7) == Espacio()
    finally:
        motor.dispose()


def _tablas(motor) -> set[str]:
    from sqlalchemy import inspect

    return set(inspect(motor).get_table_names())


# --- filas editables <-> modelo -----------------------------------------------------------------


def test_las_filas_del_editor_reconstruyen_el_mismo_espacio():
    espacio = espacio_bano()
    filas = hoja.filas_desde_espacio(espacio)
    assert set(filas) == set(hoja.COLUMNAS)
    assert [f["id"] for f in filas["ambientes"]] == ["BAN-01"]
    reconstruido = hoja.espacio_desde_filas(filas, base=espacio)
    assert reconstruido == espacio


def test_las_filas_de_ejemplo_dan_las_mismas_cantidades_que_el_espacio():
    espacio = espacio_bano()
    filas = hoja.filas_desde_espacio(espacio)
    items = hoja.items_del_borrador(hoja.espacio_desde_filas(filas, base=espacio), "agua")
    assert items == hoja.items_del_borrador(espacio, "agua")


def test_una_fila_en_blanco_del_editor_se_ignora():
    espacio = espacio_bano()
    filas = hoja.filas_desde_espacio(espacio)
    filas["puntos"].append({c: None for c in hoja.COLUMNAS["puntos"]})
    filas["ambientes"].append({c: "" for c in hoja.COLUMNAS["ambientes"]})
    assert hoja.espacio_desde_filas(filas, base=espacio) == espacio


def test_los_vertices_declarados_se_editan_como_tramos():
    espacio = espacio_bano()
    filas = hoja.filas_desde_espacio(espacio)
    tramos = [t for t in filas["tramos"] if t["recorrido_id"] == "R-P1"]
    assert [t["orden"] for t in tramos] == ["1", "2", "3"]
    assert tramos[0]["vertices"] == "0,0,0; 0,0,2.5"
    tramos[1]["vertices"] = "0,0,2.5; 1,0,2.5"  # el techo ahora llega a x = 1
    nuevo = hoja.espacio_desde_filas(filas, base=espacio)
    declarado = next(r for r in nuevo.recorridos if r.id == "R-P1")
    assert declarado.tramos[1].vertices[1] == Coord(D("1"), D("0"), D("2.5"))


@pytest.mark.parametrize(
    ("tabla", "campo", "valor", "mensaje"),
    [
        ("ambientes", "largo", "dos", "largo"),
        ("ambientes", "alto", "-1", "alto"),
        ("puntos", "ambiente_id", "NO-EXISTE", "ambiente"),
        ("tramos", "vertices", "0,0,0", "vertices"),
        ("origenes", "tipo", "invento", "tipo"),
    ],
)
def test_una_fila_invalida_es_un_error_con_la_fila_y_el_campo(tabla, campo, valor, mensaje):
    espacio = espacio_bano()
    filas = hoja.filas_desde_espacio(espacio)
    filas[tabla][0][campo] = valor
    with pytest.raises(hoja.HojaInvalida) as error:
        hoja.espacio_desde_filas(filas, base=espacio)
    assert mensaje in str(error.value)


def test_el_origen_supuesto_sin_motivo_pasa_al_borrador_y_el_estado_lo_marca_error():
    """RF-44 / UC-13a: la hoja no rechaza la fila; R8 la marca ERROR en el Estado."""
    espacio = espacio_bano()
    filas = hoja.filas_desde_espacio(espacio)
    filas["origenes"][0]["referencia"] = ""
    borrador = hoja.espacio_desde_filas(filas, base=espacio)
    assert borrador.origenes[0].incompleto

    estado = _elaborar(borrador).estado
    assert estado["esp_puntos:P1"].severidad is Severidad.ERROR
    assert "origen sin referencia" in estado["esp_puntos:P1"].texto
    assert "motivo" in estado["esp_puntos:P1"].texto


def test_una_fila_con_origen_vacio_pasa_al_borrador_y_el_estado_la_marca_error():
    espacio = espacio_bano()
    filas = hoja.filas_desde_espacio(espacio)
    filas["puntos"][0]["origen_id"] = ""
    filas["ambientes"][0]["origen_id"] = "FANTASMA"
    borrador = hoja.espacio_desde_filas(filas, base=espacio)

    estado = _elaborar(borrador).estado
    assert estado["esp_puntos:P1"].severidad is Severidad.ERROR
    assert "origen no registrado" in estado["esp_puntos:P1"].texto
    assert estado["esp_ambientes:BAN-01"].severidad is Severidad.ERROR
    assert "origen no registrado" in estado["esp_ambientes:BAN-01"].texto


def test_circuitos_y_sobrescrituras_se_conservan_al_editar():
    espacio = espacio_bano()
    assert espacio.sobrescrituras  # el baño trae una
    filas = hoja.filas_desde_espacio(espacio)
    nuevo = hoja.espacio_desde_filas(filas, base=espacio)
    assert nuevo.sobrescrituras == espacio.sobrescrituras



# --- Estado: sin APU en el catalogo frente a error de medida ------------------------------------


def _elaborar_sin_apu(espacio: Espacio) -> hoja.ResultadoHoja:
    """El catalogo no tiene las partidas del agua (AF-*, DR-*): todos los items quedan pendientes."""
    return hoja.elaborar_hoja(espacio, {}, codigo="OF-001", fecha=FECHA)


def test_un_item_pendiente_no_se_confunde_con_un_error_de_medida_en_el_estado():
    estado = _elaborar_sin_apu(_limpio()).estado
    p1 = estado["esp_puntos:P1"]
    assert p1.severidad is Severidad.ERROR  # el informe lo declara ERROR: no cumple
    assert p1.texto.startswith("PENDIENTE: sin APU en el catálogo")
    assert "AF-SALIDA" in p1.texto  # dice que partida falta
    assert "fuera del ambiente" not in p1.texto and "origen" not in p1.texto
    assert "no tiene composicion" not in p1.texto  # el texto largo del nucleo no se repite en la fila


def test_una_fila_con_error_de_medida_y_partida_pendiente_dice_las_dos_cosas_por_separado():
    espacio = _limpio()
    fuera = replace(
        espacio,
        puntos=(
            replace(espacio.puntos[0], posicion=Coord(D("9"), D("0"), D("0.6"))),
            espacio.puntos[1],
        ),
    )
    texto = _elaborar_sin_apu(fuera).estado["esp_puntos:P1"].texto
    medida, pendiente = texto.split(" | ")
    assert medida.startswith("ERROR: ") and "fuera del ambiente" in medida
    assert pendiente.startswith("PENDIENTE: sin APU en el catálogo")


def test_con_las_partidas_en_el_catalogo_ninguna_fila_dice_pendiente():
    estado = _elaborar(_limpio()).estado
    assert all("PENDIENTE" not in e.texto and "sin APU" not in e.texto for e in estado.values())
