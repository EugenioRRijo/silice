"""Derivacion de datos (tarea 2.1, spec §7.2) contra la memoria a mano `of001.md`.

Las cifras salen del bloque JSON de la memoria; no se copian.
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
    ModoRecorrido,
    Recorrido,
    Tramo,
    derivar,
)
from adapters.espacio.geometria import unir_segmentos
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.unidades import normalizar_unidad
from core.verification.expresiones import evaluar
from tests.fixtures.espacio_of001 import espacio_of001

MEMORIAS = Path(__file__).resolve().parents[1] / "fixtures" / "memorias"
TOLERANCIA = Decimal("0.001")
D = Decimal
LIMITE_ORIGEN = 120  # core/models/entidades.py: origen_id String(120)
LIMITE_DESCRIPCION = 300


@pytest.fixture(scope="module")
def memoria() -> dict:
    texto = (MEMORIAS / "of001.md").read_text(encoding="utf-8")
    return json.loads(re.findall(r"```json\n(.*?)\n```", texto, flags=re.DOTALL)[0])


def _items(espacio: Espacio | None = None) -> list[ItemComputo]:
    return derivar(espacio or espacio_of001(), "datos")


def _clave(item: ItemComputo) -> str:
    """Clave de partida del oraculo: `cable_cat_6`, `canalizacion_3/4`, `caja`..."""
    cuerpo = item.codigo_partida.removeprefix("DT-")
    if cuerpo.startswith("UTP-"):
        return "cable_" + cuerpo.removeprefix("UTP-").lower().replace("-", "_")
    if cuerpo.startswith("CAN-"):
        return "canalizacion_" + cuerpo.rsplit("-", 1)[1]
    return {"CAJA": "caja", "FACEPLATE": "faceplate", "JACK": "jack", "CERT": "certificacion"}[
        cuerpo
    ]


def _por_clave(items: list[ItemComputo]) -> dict[str, ItemComputo]:
    claves = [_clave(i) for i in items]
    assert len(set(claves)) == len(claves), "una partida por clave"
    return dict(zip(claves, items, strict=True))


# --- oraculo ---------------------------------------------------------------------------------


def test_datos_de_of001_igualan_la_memoria(memoria: dict) -> None:
    items = _por_clave(_items())
    esperado = {p["partida"]: p for p in memoria["datos"]["partidas"]}
    assert set(items) == set(esperado)
    for clave, p in esperado.items():
        item = items[clave]
        assert item.unidad == normalizar_unidad(p["unidad"]), clave
        assert abs(item.cantidad - D(p["cantidad"])) <= TOLERANCIA, clave
        if p["unidad"] in ("pieza", "punto"):
            assert item.cantidad == D(p["cantidad"]), clave


def test_cantidades_decimal_exactas() -> None:
    for i in _items():
        assert isinstance(i.cantidad, Decimal)
        assert all(isinstance(v, Decimal) for v in i.parametros.values())


def test_el_cable_usa_el_recorrido_mas_holguras_y_reserva(memoria: dict) -> None:
    cable = _por_clave(_items())["cable_cat_6"]
    p = cable.parametros
    assert p["enlaces"] == 7
    assert p["holgura_rack"] == D("2.0") and p["holgura_punto"] == D("0.5")
    assert p["reserva"] == D("0.10")
    assert p["longitud_recorridos"] == D(memoria["datos"]["longitud_sin_unir"])


def test_la_canalizacion_es_la_union_de_segmentos(memoria: dict) -> None:
    espacio = espacio_of001()
    unida = sum((s.longitud for s in unir_segmentos(espacio, "RK1")), D(0))
    items = _por_clave(_items(espacio))
    total = items["canalizacion_3/4"].cantidad + items["canalizacion_1/2"].cantidad
    assert abs(total - unida) <= TOLERANCIA
    assert abs(unida - D(memoria["datos"]["longitud_unida_total"])) <= TOLERANCIA
    # ni la reserva ni el desperdicio: la regla es «longitud unida»
    assert items["canalizacion_3/4"].parametros["desperdicio"] == D("0")


# --- contrato, trazabilidad y constantes ---------------------------------------------------------


def _refs_existentes(espacio: Espacio) -> set[str]:
    refs = {f"esp_puntos:{p.id}" for p in espacio.puntos}
    refs |= {f"esp_fuentes:{f.id}" for f in espacio.fuentes}
    refs |= {f"esp_segmentos:{s.clave}" for s in unir_segmentos(espacio)}
    return refs


def _citadas(item: ItemComputo) -> list[str]:
    refs = item.origen_id.split(";")
    if re.fullmatch(r"\+\d+", refs[-1]):
        refs.pop()
    return refs


def test_cada_item_es_regla_telecom_trazable_y_con_especialidad() -> None:
    espacio = espacio_of001()
    existentes = _refs_existentes(espacio)
    for i in _items(espacio):
        assert i.origen_tipo is OrigenTipo.REGLA and i.regla
        assert i.dominio is Dominio.TELECOM  # DA-SF-3
        assert i.especificaciones["_especialidad"] == "datos"
        assert len(i.origen_id) <= LIMITE_ORIGEN, i.codigo_partida
        assert len(i.descripcion) <= LIMITE_DESCRIPCION, i.codigo_partida
        refs = _citadas(i)
        assert refs, i.codigo_partida
        assert all(r in existentes for r in refs), i.codigo_partida


def test_la_regla_reproduce_la_cantidad_r1() -> None:
    for i in _items():
        assert evaluar(i.regla, i.parametros) == i.cantidad, i.codigo_partida


def test_las_constantes_viven_en_un_solo_lugar_con_fuente_o_supuesto() -> None:
    from adapters.espacio.especialidades import datos

    ids = [c.id for c in datos.CONSTANTES_DATOS]
    assert len(set(ids)) == len(ids) and ids
    for c in datos.CONSTANTES_DATOS:
        assert isinstance(c.valor, (Decimal, str)), c.id
        assert c.fuente.strip(), c.id
        assert c.supuesto_declarado == (c.fuente == "supuesto declarado"), c.id
    # hoy ninguna tiene fuente verificada (la cita ANSI/TIA-568 esta pendiente en referencias.md)
    assert all(c.supuesto_declarado for c in datos.CONSTANTES_DATOS)
    assert datos.HOLGURA_RACK == D("2.0")
    assert datos.HOLGURA_PUNTO == D("0.5")
    assert datos.RESERVA_CABLE == D("0.10")
    assert datos.LIMITE_ENLACE.valor == D("90")
    assert datos.LIMITE_ENLACE.supuesto_declarado


def test_el_cable_y_la_canalizacion_muestran_sus_supuestos() -> None:
    items = _por_clave(_items())
    cable = items["cable_cat_6"].descripcion
    assert "supuesto declarado" in cable
    assert "cat 6" in cable.lower()
    assert "categoría por defecto" in cable  # PA1 no declara la suya (D-11)
    assert "supuesto declarado" in items["canalizacion_3/4"].descripcion
    assert "tipo por defecto" in items["canalizacion_3/4"].descripcion  # D-12


def test_especificaciones_comparables_con_el_apu() -> None:
    items = _por_clave(_items())
    assert dict(items["canalizacion_1/2"].especificaciones) == {
        "tipo": "EMT",
        "diametro": "1/2 pulg",
        "_especialidad": "datos",
    }
    assert dict(items["cable_cat_6"].especificaciones) == {
        "categoria": "cat 6",
        "_especialidad": "datos",
    }
    assert items["cable_cat_6"].unidad == "m"


def test_ordenados_por_codigo_de_partida() -> None:
    codigos = [i.codigo_partida for i in _items()]
    assert codigos == sorted(codigos)


# --- degenerados y variaciones ----------------------------------------------------------------


def test_espacio_vacio_y_sin_datos_no_derivan_nada() -> None:
    assert derivar(Espacio(), "datos") == []
    base = espacio_of001()
    sin_datos = replace(
        base,
        puntos=tuple(p for p in base.puntos if p.especialidad.value != "datos"),
        fuentes=tuple(f for f in base.fuentes if f.id != "RK1"),
    )
    assert derivar(sin_datos, "datos") == []


def test_otras_especialidades_no_alteran_los_datos() -> None:
    base = espacio_of001()
    solo_datos = replace(
        base,
        puntos=tuple(p for p in base.puntos if p.especialidad.value == "datos"),
        circuitos=(),
    )
    assert {(i.codigo_partida, i.cantidad) for i in _items(base)} == {
        (i.codigo_partida, i.cantidad) for i in _items(solo_datos)
    }


def _con_punto_modificado(id_: str, **cambios: object) -> Espacio:
    base = espacio_of001()
    return replace(
        base, puntos=tuple(replace(p, **cambios) if p.id == id_ else p for p in base.puntos)
    )


def test_un_punto_sin_fuente_cuenta_en_cajas_pero_no_lleva_cable() -> None:
    items = _por_clave(_items(_con_punto_modificado("PB3", fuente_id=None)))
    assert items["caja"].cantidad == D(7)
    assert items["certificacion"].cantidad == D(7)
    assert items["cable_cat_6"].parametros["enlaces"] == D(6)
    # PB3 era el unico que llegaba a (6; 5,5): su tramo desaparece de la canalizacion
    assert abs(items["canalizacion_3/4"].cantidad - D("20.5")) <= TOLERANCIA


def test_dos_categorias_dan_dos_partidas_de_cable() -> None:
    espacio = _con_punto_modificado(
        "PB3", especificaciones=(("categoria", "CAT  6A"), ("diametro", '3/4"'))
    )
    items = _items(espacio)
    cables = sorted(i.codigo_partida for i in items if i.codigo_partida.startswith("DT-UTP-"))
    assert cables == ["DT-UTP-CAT-6", "DT-UTP-CAT-6A"]  # grafia normalizada: minusculas, un espacio
    por = {i.codigo_partida: i for i in items}
    assert por["DT-UTP-CAT-6A"].parametros["enlaces"] == D(1)
    assert por["DT-UTP-CAT-6"].parametros["enlaces"] == D(6)
    assert por["DT-UTP-CAT-6A"].especificaciones["categoria"] == "cat 6a"


def test_la_categoria_con_otra_grafia_se_agrupa_con_la_misma() -> None:
    espacio = _con_punto_modificado(
        "PA2", especificaciones=(("categoria", " Cat   6 "), ("diametro", '3/4"'))
    )
    cables = [i for i in _items(espacio) if i.codigo_partida.startswith("DT-UTP-")]
    assert [i.codigo_partida for i in cables] == ["DT-UTP-CAT-6"]


def test_el_punto_puede_declarar_otro_tipo_de_canalizacion() -> None:
    espacio = _con_punto_modificado(
        "PR1",
        especificaciones=(("categoria", "cat 6"), ("diametro", '1/2"'), ("canalizacion", "PVC")),
    )
    codigos = {i.codigo_partida for i in _items(espacio)}
    assert "DT-CAN-PVC-1/2" in codigos  # su tramo propio (DS1 a DS3) es de PVC
    assert "DT-CAN-EMT-1/2" not in codigos
    assert "DT-CAN-EMT-3/4" in codigos  # el tronco compartido lo manda el de mayor diametro (EMT)


def test_un_recorrido_declarado_manda_sobre_el_propuesto() -> None:
    base = espacio_of001()
    tramo = Tramo(
        orden=1,
        superficie="techo",
        vertices=(Coord(D("3"), D("1"), D("0")), Coord(D("6"), D("5.5"), D("0.3"))),
    )
    declarado = Recorrido(id="R-PB3", punto_id="PB3", modo=ModoRecorrido.DECLARADO, tramos=(tramo,))
    espacio = replace(base, recorridos=(declarado,))
    cable = _por_clave(_items(espacio))["cable_cat_6"]
    esperado = D("74.9") - D("12.2") + tramo.longitud
    assert abs(cable.parametros["longitud_recorridos"] - esperado) <= TOLERANCIA


def test_longitud_del_enlace_es_recorrido_mas_holguras(memoria: dict) -> None:
    from adapters.espacio.especialidades.datos import longitud_enlace

    espacio = espacio_of001()
    por_id = {p.id: p for p in espacio.puntos}
    for punto, r in memoria["datos"]["recorridos"].items():
        enlace = longitud_enlace(espacio, por_id[punto])
        assert enlace is not None
        assert abs(enlace - D(r["enlace"])) <= TOLERANCIA, punto
    assert longitud_enlace(espacio, por_id["P1"]) is None  # un punto de agua no tiene enlace
    sin_fuente = replace(por_id["PB3"], fuente_id=None)
    assert longitud_enlace(espacio, sin_fuente) is None  # sin recorrido no hay enlace
