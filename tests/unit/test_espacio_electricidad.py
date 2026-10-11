"""Derivacion de electricidad (tarea 2.2, spec §7.3) contra la memoria a mano `of001.md`.

Las cifras salen del bloque JSON de la memoria; no se copian.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.espacio import Circuito, Espacio, derivar
from adapters.espacio.geometria import unir_segmentos
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.unidades import normalizar_unidad
from core.verification.expresiones import evaluar
from tests.fixtures.espacio_of001 import espacio_of001

MEMORIAS = Path(__file__).resolve().parents[1] / "fixtures" / "memorias"
TOLERANCIA = Decimal("0.001")
D = Decimal
LIMITE_ORIGEN = 120
LIMITE_DESCRIPCION = 300


@pytest.fixture(scope="module")
def memoria() -> dict:
    texto = (MEMORIAS / "of001.md").read_text(encoding="utf-8")
    return json.loads(re.findall(r"```json\n(.*?)\n```", texto, flags=re.DOTALL)[0])


def _items(espacio: Espacio | None = None) -> list[ItemComputo]:
    return derivar(espacio or espacio_of001(), "electricidad")


def _clave(item: ItemComputo) -> str:
    """Clave de partida del oraculo: `conductor_12 AWG`, `tuberia_3/4`, `caja`..."""
    cuerpo = item.codigo_partida.removeprefix("EL-")
    if cuerpo.startswith("COND-"):
        return "conductor_" + cuerpo.removeprefix("COND-").replace("-", " ")
    if cuerpo.startswith("TUB-"):
        return "tuberia_" + cuerpo.rsplit("-", 1)[1]
    return {
        "CAJA": "caja",
        "SALIDA-TOMA": "salida_tomacorriente",
        "SALIDA-ILUM": "salida_iluminacion",
        "PROT": "proteccion",
    }[cuerpo]


def _por_clave(items: list[ItemComputo]) -> dict[str, ItemComputo]:
    claves = [_clave(i) for i in items]
    assert len(set(claves)) == len(claves), "una partida por clave"
    return dict(zip(claves, items, strict=True))


def _con_punto(espacio: Espacio, id_: str, **cambios: object) -> Espacio:
    return replace(
        espacio, puntos=tuple(replace(p, **cambios) if p.id == id_ else p for p in espacio.puntos)
    )


# --- oraculo ---------------------------------------------------------------------------------


def test_electricidad_de_of001_iguala_la_memoria(memoria: dict) -> None:
    items = _por_clave(_items())
    esperado = {p["partida"]: p for p in memoria["electricidad"]["partidas"]}
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


def test_el_conductor_es_la_cadena_por_los_conductores_y_el_desperdicio(memoria: dict) -> None:
    items = _por_clave(_items())
    c1 = items["conductor_12 AWG"]
    assert c1.parametros["desperdicio"] == D("0.10")
    assert abs(c1.parametros["metros_de_conductor"] - D("68.7")) <= TOLERANCIA  # 22,9 x 3
    assert "conductores" in c1.regla or "metros_de_conductor" in c1.regla
    assert abs(items["conductor_14 AWG"].parametros["metros_de_conductor"] - D("30")) <= TOLERANCIA


def test_la_tuberia_es_la_union_de_las_cadenas(memoria: dict) -> None:
    espacio = espacio_of001()
    unida = sum((s.longitud for s in unir_segmentos(espacio, "T1")), D(0))
    items = _por_clave(_items(espacio))
    total = items["tuberia_3/4"].cantidad + items["tuberia_1/2"].cantidad
    assert abs(total - unida) <= TOLERANCIA
    assert items["tuberia_3/4"].parametros["desperdicio"] == D("0")  # la regla es «longitud unida»


# --- contrato, trazabilidad y constantes ---------------------------------------------------------


def _refs_existentes(espacio: Espacio) -> set[str]:
    refs = {f"esp_puntos:{p.id}" for p in espacio.puntos}
    refs |= {f"esp_fuentes:{f.id}" for f in espacio.fuentes}
    refs |= {f"esp_circuitos:{c.id}" for c in espacio.circuitos}
    refs |= {f"esp_segmentos:{s.clave}" for s in unir_segmentos(espacio)}
    return refs


def _citadas(item: ItemComputo) -> list[str]:
    refs = item.origen_id.split(";")
    if re.fullmatch(r"\+\d+", refs[-1]):
        refs.pop()
    return refs


def test_cada_item_es_regla_civil_trazable_y_con_especialidad() -> None:
    espacio = espacio_of001()
    existentes = _refs_existentes(espacio)
    for i in _items(espacio):
        assert i.origen_tipo is OrigenTipo.REGLA and i.regla
        assert i.dominio is Dominio.CIVIL  # DA-SF-3
        assert i.especificaciones["_especialidad"] == "electricidad"
        assert len(i.origen_id) <= LIMITE_ORIGEN, i.codigo_partida
        assert len(i.descripcion) <= LIMITE_DESCRIPCION, i.codigo_partida
        refs = _citadas(i)
        assert refs, i.codigo_partida
        assert all(r in existentes for r in refs), (i.codigo_partida, refs)


def test_la_regla_reproduce_la_cantidad_r1() -> None:
    for i in _items():
        assert evaluar(i.regla, i.parametros) == i.cantidad, i.codigo_partida


def test_las_constantes_viven_en_un_solo_lugar_con_fuente_o_supuesto() -> None:
    from adapters.espacio.especialidades import electricidad

    ids = [c.id for c in electricidad.CONSTANTES_ELECTRICIDAD]
    assert len(set(ids)) == len(ids) and ids
    for c in electricidad.CONSTANTES_ELECTRICIDAD:
        assert isinstance(c.valor, (Decimal, str)), c.id
        assert c.fuente.strip(), c.id
        assert c.supuesto_declarado == (c.fuente == "supuesto declarado"), c.id
    assert all(c.supuesto_declarado for c in electricidad.CONSTANTES_ELECTRICIDAD)
    assert electricidad.DESPERDICIO_CONDUCTOR == D("0.10")
    # el maximo de puntos por circuito lo declara cada circuito; su fuente candidata (COVENIN 200)
    # no esta verificada: hoy es un supuesto declarado
    assert electricidad.LIMITE_PUNTOS_POR_CIRCUITO.supuesto_declarado


def test_el_conductor_y_la_tuberia_muestran_sus_supuestos() -> None:
    items = _por_clave(_items())
    assert "supuesto declarado" in items["conductor_12 AWG"].descripcion
    assert "12 AWG" in items["conductor_12 AWG"].descripcion
    tuberia = items["tuberia_3/4"].descripcion
    assert "supuesto declarado" in tuberia and "tipo por defecto" in tuberia  # D-12


def test_especificaciones_comparables_con_el_apu() -> None:
    items = _por_clave(_items())
    assert dict(items["tuberia_1/2"].especificaciones) == {
        "tipo": "EMT",
        "diametro": "1/2 pulg",
        "_especialidad": "electricidad",
    }
    assert dict(items["conductor_14 AWG"].especificaciones) == {
        "calibre": "14 AWG",
        "_especialidad": "electricidad",
    }


def test_ordenados_por_codigo_de_partida() -> None:
    codigos = [i.codigo_partida for i in _items()]
    assert codigos == sorted(codigos)


# --- degenerados y variaciones ----------------------------------------------------------------


def test_espacio_vacio_y_sin_electricidad_no_derivan_nada() -> None:
    assert derivar(Espacio(), "electricidad") == []
    base = espacio_of001()
    sin = replace(
        base,
        puntos=tuple(p for p in base.puntos if p.especialidad.value != "electricidad"),
        circuitos=(),
        fuentes=tuple(f for f in base.fuentes if f.id != "T1"),
    )
    assert derivar(sin, "electricidad") == []


def test_otras_especialidades_no_alteran_la_electricidad() -> None:
    base = espacio_of001()
    solo = replace(
        base,
        puntos=tuple(p for p in base.puntos if p.especialidad.value == "electricidad"),
        fuentes=tuple(f for f in base.fuentes if f.id == "T1"),
    )
    assert {(i.codigo_partida, i.cantidad) for i in _items(base)} == {
        (i.codigo_partida, i.cantidad) for i in _items(solo)
    }


def test_un_punto_sin_circuito_cuenta_en_cajas_y_salidas_pero_no_lleva_conductor() -> None:
    espacio = _con_punto(espacio_of001(), "LZ4", circuito_id=None)
    items = _por_clave(_items(espacio))
    assert items["caja"].cantidad == D(8)
    assert items["salida_iluminacion"].cantidad == D(4)
    # LZ4 sale de la cadena de C2 (LZ1, LZ2, LZ3): 4 + 2 + 2 = 8 m x 3 conductores
    assert abs(items["conductor_14 AWG"].parametros["metros_de_conductor"] - D("24")) <= TOLERANCIA


def test_un_punto_en_el_orden_declarado_va_en_la_cadena_aunque_no_cite_el_circuito() -> None:
    """El orden que declara el usuario manda: TB2 sigue en la cadena de C1 (su orden lo nombra)."""
    espacio = _con_punto(espacio_of001(), "TB2", circuito_id=None)
    c1 = _por_clave(_items(espacio))["conductor_12 AWG"]
    assert abs(c1.parametros["metros_de_conductor"] - D("68.7")) <= TOLERANCIA


def test_los_conductores_del_circuito_multiplican_la_cadena() -> None:
    espacio = replace(
        espacio_of001(),
        circuitos=tuple(
            replace(c, conductores=(2, 1, 1)) if c.id == "C1" else c
            for c in espacio_of001().circuitos
        ),
    )
    c1 = _por_clave(_items(espacio))["conductor_12 AWG"]
    assert abs(c1.parametros["metros_de_conductor"] - D("22.9") * 4) <= TOLERANCIA
    assert abs(c1.cantidad - D("22.9") * 4 * D("1.10")) <= TOLERANCIA


def test_circuitos_del_mismo_calibre_suman_en_una_partida() -> None:
    espacio = replace(
        espacio_of001(),
        circuitos=tuple(
            replace(c, calibre=" 12  awg ") if c.id == "C2" else c
            for c in espacio_of001().circuitos
        ),
    )
    items = _items(espacio)
    conductores = [i for i in items if i.codigo_partida.startswith("EL-COND-")]
    assert [i.codigo_partida for i in conductores] == ["EL-COND-12-AWG"]
    esperado = (D("22.9") + D("10")) * 3
    assert abs(conductores[0].parametros["metros_de_conductor"] - esperado) <= TOLERANCIA
    assert conductores[0].especificaciones["calibre"] == "12 AWG"


def test_un_circuito_sin_puntos_igual_lleva_su_proteccion() -> None:
    base = espacio_of001()
    vacio = Circuito(
        id="C9", tablero="T1", numero=9, conductores=(1, 1, 1), calibre="12 AWG", puntos_maximos=4
    )
    espacio = replace(base, circuitos=base.circuitos + (vacio,))
    items = _por_clave(_items(espacio))
    assert items["proteccion"].cantidad == D(3)
    assert items["conductor_12 AWG"].cantidad == _por_clave(_items())["conductor_12 AWG"].cantidad


def test_el_punto_puede_declarar_otro_tipo_de_tuberia() -> None:
    espacio = espacio_of001()
    for id_ in ("LZ1", "LZ2", "LZ3", "LZ4"):
        espacio = _con_punto(
            espacio, id_, especificaciones=(("diametro", '1/2"'), ("canalizacion", "pvc"))
        )
    codigos = {i.codigo_partida for i in _items(espacio)}
    assert "EL-TUB-PVC-1/2" in codigos  # el tramo propio de C2
    assert "EL-TUB-EMT-3/4" in codigos  # lo manda el circuito de mayor diametro


def test_la_cadena_declarada_cambia_el_conductor() -> None:
    base = espacio_of001()
    espacio = replace(
        base,
        circuitos=tuple(
            replace(c, orden=("TB2", "TB1", "TA2", "TA1")) if c.id == "C1" else c
            for c in base.circuitos
        ),
    )
    original = _por_clave(_items(base))["conductor_12 AWG"].cantidad
    assert _por_clave(_items(espacio))["conductor_12 AWG"].cantidad > original
