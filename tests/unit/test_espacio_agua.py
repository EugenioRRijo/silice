"""Derivacion de agua fria y drenaje (tarea 1.5, spec §7.1) contra las memorias a mano.

Las cifras salen de los bloques JSON de `bano_of001.md` y `bano_drenaje_of001.md`; no se copian.
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
    Especialidad,
    Fuente,
    Punto,
    SobrescrituraSegmento,
    SuperficiePunto,
    TipoFuente,
    TipoPunto,
    derivar,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.unidades import normalizar_unidad
from tests.fixtures.espacio_bano import espacio_bano, espacio_bano_con_drenaje

MEMORIAS = Path(__file__).resolve().parents[1] / "fixtures" / "memorias"
TOLERANCIA = Decimal("0.001")
D = Decimal


def _json(nombre: str) -> dict:
    texto = (MEMORIAS / nombre).read_text(encoding="utf-8")
    return json.loads(re.findall(r"```json\n(.*?)\n```", texto, flags=re.DOTALL)[0])


@pytest.fixture(scope="module")
def agua_memoria() -> dict:
    return _json("bano_of001.md")


@pytest.fixture(scope="module")
def drenaje_memoria() -> dict:
    return _json("bano_drenaje_of001.md")


def _diametro(item: ItemComputo) -> str:
    return item.especificaciones["diametro"].removesuffix(" pulg")


def _clave(item: ItemComputo) -> str:
    """Clave de partida del oraculo para un item: `tuberia_3/4`, `codo_1 1/2`, `salida_agua`..."""
    sistema, tipo, *_ = item.codigo_partida.split("-")
    if tipo in ("TUB", "CODO", "TEE"):
        return f"{ {'TUB': 'tuberia', 'CODO': 'codo', 'TEE': 'tee'}[tipo] }_{_diametro(item)}"
    if tipo == "LLAVE":
        return "llave_de_paso"
    if tipo == "SALIDA":
        return "salida_agua" if sistema == "AF" else "salida_drenaje"
    if tipo == "PICADO":
        return "picado_resane_" + item.codigo_partida.rsplit("-", 1)[1].lower()
    raise AssertionError(item.codigo_partida)


def _por_clave(items: list[ItemComputo], sistema: str) -> dict[str, ItemComputo]:
    elegidos = [i for i in items if i.codigo_partida.startswith(sistema + "-")]
    claves = [_clave(i) for i in elegidos]
    assert len(set(claves)) == len(claves), "una partida por clave"
    return dict(zip(claves, elegidos, strict=True))


def _comparar(items: dict[str, ItemComputo], memoria: dict) -> None:
    esperado = {p["partida"]: p for p in memoria["partidas"]}
    assert set(items) == set(esperado)
    for clave, p in esperado.items():
        item = items[clave]
        assert item.unidad == normalizar_unidad(p["unidad"]), clave
        assert abs(item.cantidad - D(p["cantidad"])) <= TOLERANCIA, clave
        if p["unidad"] == "u":
            assert item.cantidad == D(p["cantidad"]), clave


# --- oraculos ----------------------------------------------------------------------------


def test_agua_fria_del_bano_iguala_la_memoria(agua_memoria: dict) -> None:
    items = derivar(espacio_bano(), "agua")
    assert all(i.codigo_partida.startswith("AF-") for i in items)
    _comparar(_por_clave(items, "AF"), agua_memoria)


def test_drenaje_del_bano_iguala_la_memoria(agua_memoria: dict, drenaje_memoria: dict) -> None:
    items = derivar(espacio_bano_con_drenaje(), "agua")
    _comparar(_por_clave(items, "DR"), drenaje_memoria)
    _comparar(_por_clave(items, "AF"), agua_memoria)  # el drenaje no altera el agua fria


def test_cantidades_decimal_exactas(drenaje_memoria: dict) -> None:
    for i in derivar(espacio_bano_con_drenaje(), "agua"):
        assert isinstance(i.cantidad, Decimal)
        assert all(isinstance(v, Decimal) for v in i.parametros.values())


# --- trazabilidad y constantes -----------------------------------------------------------


def test_cada_item_es_regla_civil_y_trazable() -> None:
    espacio = espacio_bano_con_drenaje()
    refs_validas = {f"esp_puntos:{p.id}" for p in espacio.puntos}
    refs_validas |= {f"esp_fuentes:{f.id}" for f in espacio.fuentes}
    for i in derivar(espacio, "agua"):
        assert i.origen_tipo is OrigenTipo.REGLA and i.regla
        assert i.dominio is Dominio.CIVIL
        for ref in i.origen_id.split(";"):
            assert ref.startswith("esp_segmentos:") or ref in refs_validas, (i.codigo_partida, ref)


def test_origen_cita_los_segmentos_los_puntos_y_las_fuentes(agua_memoria: dict) -> None:
    items = _por_clave(derivar(espacio_bano(), "agua"), "AF")
    claves_34 = {s["clave"] for s in agua_memoria["segmentos"] if s["diametro"] == "3/4"}
    citadas = set(items["tuberia_3/4"].origen_id.split(";"))
    assert citadas == {f"esp_segmentos:{c}" for c in claves_34}
    assert items["llave_de_paso"].origen_id == "esp_puntos:P1;esp_puntos:P2"
    assert items["salida_agua"].origen_id == "esp_puntos:P1;esp_puntos:P2"
    assert items["codo_3/4"].origen_id == "esp_fuentes:F1"


def test_la_constante_sin_fuente_se_ve_como_supuesto_declarado() -> None:
    items = _por_clave(derivar(espacio_bano(), "agua"), "AF")
    tuberia = items["tuberia_3/4"]
    assert "supuesto declarado" in tuberia.descripcion
    assert tuberia.parametros["desperdicio"] == D("0.10")
    assert tuberia.parametros["longitud_unida"] == D("6.300")
    assert "1 + desperdicio" in tuberia.regla


def test_las_constantes_viven_en_un_solo_lugar_con_fuente_o_supuesto() -> None:
    from adapters.espacio.especialidades import agua

    ids = [c.id for c in agua.CONSTANTES_AGUA]
    assert len(set(ids)) == len(ids) and ids
    for c in agua.CONSTANTES_AGUA:
        assert isinstance(c.valor, (Decimal, str)), c.id
        assert c.fuente.strip(), c.id
        assert c.supuesto_declarado == (c.fuente == "supuesto declarado"), c.id
    assert agua.DESPERDICIO_TUBERIA_AGUA_FRIA == D("0.10")


def test_especificaciones_comparables_con_el_apu() -> None:
    items = _por_clave(derivar(espacio_bano_con_drenaje(), "agua"), "DR")
    assert dict(items["tuberia_1 1/2"].especificaciones) == {
        "material": "PVC",
        "diametro": "1 1/2 pulg",
    }
    assert items["tuberia_1 1/2"].unidad == "m"


# --- casos --------------------------------------------------------------------------------


def test_fr1_espacio_vacio() -> None:
    assert derivar(Espacio(), "agua") == []


def test_fr2_punto_sin_recorrido_y_fuente_sin_puntos() -> None:
    base = espacio_bano()
    f2 = Fuente(
        id="F2",
        especialidad=Especialidad.AGUA,
        tipo=TipoFuente.MONTANTE_AGUA,
        ambiente_id="BAN-01",
        posicion=Coord(D("2"), D("1.5"), D("0")),
        origen_id="O1",
    )
    p3 = Punto(
        id="P3",
        nombre="llave de manguera",
        especialidad=Especialidad.AGUA,
        tipo=TipoPunto.AGUA_FRIA,
        ambiente_id="BAN-01",
        superficie=SuperficiePunto.PARED,
        posicion=Coord(D("1.8"), D("1.5"), D("0.4")),
        fuente_id=None,
        origen_id="O1",
    )
    con = replace(base, fuentes=base.fuentes + (f2,), puntos=base.puntos + (p3,))
    antes = {i.codigo_partida: i.cantidad for i in derivar(base, "agua")}
    despues = {i.codigo_partida: i.cantidad for i in derivar(con, "agua")}
    # sin tuberia ni accesorios nuevos; el punto sin fuente solo suma su salida
    assert despues.pop("AF-SALIDA") == antes.pop("AF-SALIDA") + 1
    assert despues == antes


def test_solo_un_punto_sin_fuente_da_llave_y_salida_sin_tuberia() -> None:
    esp = espacio_bano()
    solo = replace(
        esp,
        fuentes=(),
        puntos=(replace(esp.puntos[0], fuente_id=None),),
        recorridos=(),
        sobrescrituras=(),
    )
    items = derivar(solo, "agua")
    # su llave declarada y su salida cuentan; sin fuente no hay tuberia ni accesorios
    assert [i.codigo_partida for i in items] == ["AF-LLAVE", "AF-SALIDA"]
    assert all(i.cantidad == 1 for i in items)


def _con_puntos(*puntos: Punto) -> Espacio:
    base = espacio_bano()
    return replace(base, puntos=tuple(puntos), recorridos=(), sobrescrituras=())


def _punto(base: Punto, **cambios: object) -> Punto:
    espec = dict(base.espec)
    espec.update(cambios.pop("espec", {}))  # type: ignore[arg-type]
    return replace(base, especificaciones=tuple(espec.items()), **cambios)  # type: ignore[arg-type]


def test_material_y_diametro_distintos_se_separan() -> None:
    p1, p2 = espacio_bano().puntos
    mismo_diametro = _punto(p2, espec={"diametro": '1/2"'})
    pvc = _con_puntos(p1, mismo_diametro)
    cpvc = _con_puntos(p1, _punto(mismo_diametro, espec={"material": "CPVC"}))
    tub_pvc = [i for i in derivar(pvc, "agua") if i.codigo_partida.startswith("AF-TUB")]
    tub_mixto = [i for i in derivar(cpvc, "agua") if i.codigo_partida.startswith("AF-TUB")]
    assert len(tub_pvc) == 1 and tub_pvc[0].especificaciones["material"] == "PVC"
    assert {i.especificaciones["material"] for i in tub_mixto} == {"PVC", "CPVC"}
    total = sum(i.cantidad for i in tub_mixto)
    assert total > 0 and len({i.codigo_partida for i in tub_mixto}) == 2


def test_llave_de_paso_solo_si_se_declara() -> None:
    p1, p2 = espacio_bano().puntos
    sin_p1 = _punto(p1, espec={"llave_de_paso": "no"})
    una = _con_puntos(sin_p1, p2)
    llaves = [i for i in derivar(una, "agua") if i.codigo_partida == "AF-LLAVE"]
    assert len(llaves) == 1 and llaves[0].cantidad == 1
    assert llaves[0].origen_id == "esp_puntos:P2"
    ninguna = replace(una, puntos=(sin_p1, _punto(p2, espec={"llave_de_paso": "no"})))
    assert not [i for i in derivar(ninguna, "agua") if i.codigo_partida == "AF-LLAVE"]


def test_el_drenaje_no_lleva_llave_de_paso() -> None:
    esp = espacio_bano_con_drenaje()
    ducha = next(p for p in esp.puntos if p.id == "D1")
    declarada = replace(
        esp,
        puntos=tuple(
            _punto(p, espec={"llave_de_paso": "si"}) if p is ducha else p for p in esp.puntos
        ),
    )
    llaves = [i for i in derivar(declarada, "agua") if i.codigo_partida == "AF-LLAVE"]
    assert llaves[0].cantidad == 2  # solo P1 y P2, agua fria


def test_sobrescritura_que_cambia_el_diametro_de_un_segmento(agua_memoria: dict) -> None:
    s5 = next(s for s in agua_memoria["segmentos"] if s["id"] == "S5")
    esp = espacio_bano()
    esp = replace(
        esp,
        sobrescrituras=esp.sobrescrituras
        + (SobrescrituraSegmento(clave=s5["clave"], diametro='1"'),),
    )
    items = _por_clave(derivar(esp, "agua"), "AF")
    assert items["tuberia_3/4"].cantidad == D("4.800") * D("1.10")
    assert items["tuberia_1"].cantidad == D("1.500") * D("1.10")
    assert items["tuberia_1/2"].cantidad == D("2.640")
    # codo G (S5 de 1" con S6 de 3/4") y tee E (S2 3/4", S3 1/2", S5 1") toman el mayor
    assert items["codo_1"].cantidad == 1 and items["codo_3/4"].cantidad == 1
    assert items["tee_1"].cantidad == 1 and "tee_3/4" not in items


def test_punto_sin_diametro_se_separa_y_no_inventa_uno() -> None:
    p1, p2 = espacio_bano().puntos
    sin = replace(p2, especificaciones=(("llave_de_paso", "si"),))
    items = derivar(_con_puntos(p1, sin), "agua")
    tuberias = [i for i in items if i.codigo_partida.startswith("AF-TUB")]
    sin = [i for i in tuberias if i.codigo_partida.endswith("SIN-DIAMETRO")]
    assert len(sin) == 1 and "diametro" not in sin[0].especificaciones
    assert "sin diametro declarado" in sin[0].descripcion


# --- determinismo ---------------------------------------------------------------------------


def _huella(items: list[ItemComputo]) -> list[tuple[str, str, str, Decimal]]:
    return [(i.codigo_partida, i.descripcion, i.unidad, i.cantidad) for i in items]


def test_items_ordenados_y_repetibles() -> None:
    items = derivar(espacio_bano_con_drenaje(), "agua")
    codigos = [i.codigo_partida for i in items]
    assert codigos == sorted(codigos)
    assert derivar(espacio_bano_con_drenaje(), "agua") == items


def test_permutar_ids_no_cambia_las_cantidades() -> None:
    original = espacio_bano_con_drenaje()
    renombres = {"P1": "Z9", "P2": "A1", "D1": "Y8", "D2": "B2", "F1": "ZF", "FD1": "AF0"}
    puntos = tuple(
        replace(p, id=renombres[p.id], fuente_id=renombres.get(p.fuente_id or ""))
        for p in original.puntos
    )
    fuentes = tuple(replace(f, id=renombres[f.id]) for f in original.fuentes)
    recorridos = tuple(
        replace(r, id="R-" + renombres[r.punto_id or ""], punto_id=renombres[r.punto_id or ""])
        for r in original.recorridos
    )
    sobre = tuple(replace(s, clave=s.clave.replace("F1|", "ZF|")) for s in original.sobrescrituras)
    permutado = Espacio(
        origenes=original.origenes,
        ambientes=original.ambientes,
        fuentes=tuple(reversed(fuentes)),
        puntos=tuple(reversed(puntos)),
        recorridos=tuple(reversed(recorridos)),
        sobrescrituras=sobre,
    )
    assert _huella(derivar(permutado, "agua")) == _huella(derivar(original, "agua"))
