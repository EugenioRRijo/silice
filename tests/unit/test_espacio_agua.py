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
    ModoRecorrido,
    Punto,
    Recorrido,
    SobrescrituraSegmento,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoPunto,
    Tramo,
    derivar,
)
from adapters.espacio.especialidades.agua import superficie_de_segmento
from adapters.espacio.geometria import Segmento, unir_segmentos
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


LIMITE_ORIGEN = 120  # core/models/entidades.py: origen_id String(120)
LIMITE_DESCRIPCION = 300


def _refs_existentes(espacio: Espacio) -> set[str]:
    refs = {f"esp_puntos:{p.id}" for p in espacio.puntos}
    refs |= {f"esp_fuentes:{f.id}" for f in espacio.fuentes}
    refs |= {f"esp_segmentos:{s.clave}" for s in unir_segmentos(espacio)}
    return refs


def _citadas(item: ItemComputo) -> tuple[list[str], int]:
    """Referencias citadas y cuantas se omitieron (sufijo `+N`)."""
    refs = item.origen_id.split(";")
    omitidas = 0
    if re.fullmatch(r"\+\d+", refs[-1]):
        omitidas = int(refs.pop()[1:])
    return refs, omitidas


def test_cada_item_es_regla_civil_y_trazable() -> None:
    espacio = espacio_bano_con_drenaje()
    existentes = _refs_existentes(espacio)
    for i in derivar(espacio, "agua"):
        assert i.origen_tipo is OrigenTipo.REGLA and i.regla
        assert i.dominio is Dominio.CIVIL
        refs, _ = _citadas(i)
        assert refs, i.codigo_partida
        for ref in refs:
            assert ref in existentes, (i.codigo_partida, ref)


def test_origen_cita_la_fuente_y_los_segmentos_o_puntos(agua_memoria: dict) -> None:
    items = _por_clave(derivar(espacio_bano(), "agua"), "AF")
    claves_34 = {
        f"esp_segmentos:{s['clave']}" for s in agua_memoria["segmentos"] if s["diametro"] == "3/4"
    }
    refs, omitidas = _citadas(items["tuberia_3/4"])
    assert refs[0] == "esp_fuentes:F1"
    assert set(refs[1:]) <= claves_34
    assert len(refs) - 1 + omitidas == len(claves_34)  # citadas + omitidas = todas
    assert items["llave_de_paso"].origen_id == "esp_fuentes:F1;esp_puntos:P1;esp_puntos:P2"
    assert items["salida_agua"].origen_id == "esp_fuentes:F1;esp_puntos:P1;esp_puntos:P2"
    assert items["codo_3/4"].origen_id == "esp_fuentes:F1"


def _espacio_grande(n: int = 30) -> Espacio:
    base = espacio_bano()
    amplio = replace(base.ambientes[0], largo=D(40))
    modelo = base.puntos[0]
    puntos = tuple(
        replace(
            modelo,
            id=f"P{i:02d}",
            posicion=Coord(D("0.5") * i, D(0), D("0.6")),
            especificaciones=(("diametro", '1/2"'), ("llave_de_paso", "si")),
        )
        for i in range(1, n + 1)
    )
    return replace(base, ambientes=(amplio,), puntos=puntos, recorridos=(), sobrescrituras=())


def test_origen_nunca_supera_120_caracteres_en_un_espacio_grande() -> None:
    espacio = _espacio_grande()
    items = derivar(espacio, "agua")
    assert items == derivar(espacio, "agua")  # determinista
    existentes = _refs_existentes(espacio)
    codigos = [i.codigo_partida for i in items]
    assert len(set(codigos)) == len(codigos)
    assert len({(i.codigo_partida, i.origen_id) for i in items}) == len(items)
    por_clave = _por_clave(items, "AF")
    assert por_clave["salida_agua"].cantidad == 30 and por_clave["llave_de_paso"].cantidad == 30
    for i in items:
        assert len(i.origen_id) <= LIMITE_ORIGEN, (i.codigo_partida, len(i.origen_id))
        assert len(i.descripcion) <= LIMITE_DESCRIPCION, i.codigo_partida
        refs, omitidas = _citadas(i)
        assert refs[0] == "esp_fuentes:F1", i.codigo_partida  # trazable hasta la fuente
        assert all(r in existentes for r in refs)
        if omitidas:
            assert i.origen_id.endswith(f";+{omitidas}")
    assert _citadas(por_clave["salida_agua"])[1] > 0  # 30 puntos no caben


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
    espec = {k: v for k, v in espec.items() if v is not None}  # None = quitar la clave
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
    sin_p1 = _punto(p1, espec={"llave_de_paso": None})
    una = _con_puntos(sin_p1, p2)
    llaves = [i for i in derivar(una, "agua") if i.codigo_partida == "AF-LLAVE"]
    assert len(llaves) == 1 and llaves[0].cantidad == 1
    assert llaves[0].origen_id == "esp_puntos:P2"
    ninguna = replace(una, puntos=(sin_p1, _punto(p2, espec={"llave_de_paso": None})))
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
    assert "sin diámetro declarado" in sin[0].descripcion


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


# --- D-7: superficie del picado ---------------------------------------------------------------


def _seg(a: tuple[str, str, str], b: tuple[str, str, str], superficie=None) -> Segmento:
    ca, cb = Coord(*(D(v) for v in a)), Coord(*(D(v) for v in b))
    return Segmento(
        clave="X|a|b",
        fuente_id="X",
        a=ca,
        b=cb,
        longitud=ca.distancia(cb),
        sirve=("P",),
        diametro="1",
        empotrado=True,
        superficie=superficie,
    )


@pytest.mark.parametrize(
    ("a", "b", "esperada"),
    [
        (("0", "0", "-0.30"), ("1", "0", "-0.30"), "PISO"),  # enterrado bajo el piso
        (("0", "0", "0.0005"), ("1", "0", "0.0005"), "PISO"),  # dentro de la tolerancia
        (("0", "0", "2.5"), ("1", "0", "2.5"), "PARED"),  # la spec solo prevé pared o piso
        (("0", "0", "0"), ("0", "0", "0.5"), "PARED"),  # vertical
        (("0", "0", "-0.30"), ("0", "0", "0"), "PARED"),  # vertical que cruza el piso
    ],
)
def test_superficie_deducida_cuando_el_segmento_no_la_declara(a, b, esperada) -> None:
    assert superficie_de_segmento(_seg(a, b)) == esperada


def test_la_superficie_declarada_manda_sobre_la_deduccion() -> None:
    alto = (("0", "0", "2.5"), ("1", "0", "2.5"))
    assert superficie_de_segmento(_seg(*alto, SuperficieTramo.PISO)) == "PISO"
    bajo = (("0", "0", "0"), ("1", "0", "0"))
    assert superficie_de_segmento(_seg(*bajo, SuperficieTramo.PARED)) == "PARED"
    assert superficie_de_segmento(_seg(*alto, SuperficieTramo.TECHO)) == "PARED"


def _drenaje_a_cota(z: str) -> Espacio:
    """Drenaje de D1 con tramos de piso declarados a la cota z (pendiente o enterrado)."""
    esp = espacio_bano_con_drenaje()
    tramos = (
        Tramo(
            orden=1,
            superficie=SuperficieTramo.PISO,
            vertices=(Coord(D("1"), D("1.5"), D(z)), Coord(D("2"), D("1.5"), D(z))),
        ),
        Tramo(
            orden=2,
            superficie=SuperficieTramo.PISO,
            vertices=(Coord(D("2"), D("1.5"), D(z)), Coord(D("2"), D("0.75"), D(z))),
        ),
    )
    recorrido = Recorrido(id="R-D1", punto_id="D1", modo=ModoRecorrido.DECLARADO, tramos=tramos)
    return replace(esp, recorridos=esp.recorridos + (recorrido,))


@pytest.mark.parametrize("z", ["-0.30", "-0.02", "0"])
def test_tramo_de_piso_declarado_a_cualquier_cota_es_picado_de_piso(z: str) -> None:
    items = _por_clave(derivar(_drenaje_a_cota(z), "agua"), "DR")
    assert items["picado_resane_piso"].cantidad == D("1.750") + D("0.500") + D("0.750")
    assert items["picado_resane_pared"].cantidad == D("0.500")


# --- minors -------------------------------------------------------------------------------


def test_material_por_defecto_se_declara_como_supuesto_en_la_descripcion() -> None:
    items = _por_clave(derivar(espacio_bano(), "agua"), "AF")
    assert "material por defecto: supuesto declarado" in items["tuberia_3/4"].descripcion
    p1, p2 = espacio_bano().puntos
    con = _con_puntos(
        _punto(p1, espec={"material": "CPVC"}), _punto(p2, espec={"material": "CPVC"})
    )
    tub = [i for i in derivar(con, "agua") if i.codigo_partida.startswith("AF-TUB")]
    assert tub and all("material por defecto" not in i.descripcion for i in tub)


def _tuberias_por_material(espacio: Espacio) -> dict[str, Decimal]:
    return {
        i.codigo_partida: i.cantidad
        for i in derivar(espacio, "agua")
        if i.codigo_partida.startswith("AF-TUB-")
    }


def test_material_de_un_segmento_compartido_no_depende_de_los_ids() -> None:
    """P1 y P2 (1/2") comparten S1+S2 (3,5 m). Con materiales distintos gana el alfabetico (CPVC),
    sea cual sea el punto que lo declara."""
    p1, p2 = espacio_bano().puntos
    medio = {"diametro": '1/2"'}
    a = _con_puntos(
        _punto(p1, espec={**medio, "material": "PVC"}),
        _punto(p2, espec={**medio, "material": "CPVC"}),
    )
    b = _con_puntos(
        _punto(p1, espec={**medio, "material": "CPVC"}),
        _punto(p2, espec={**medio, "material": "PVC"}),
    )
    ta, tb = _tuberias_por_material(a), _tuberias_por_material(b)
    for t in (ta, tb):
        assert set(t) == {"AF-TUB-CPVC-1/2", "AF-TUB-PVC-1/2"}
        assert t["AF-TUB-CPVC-1/2"] >= D("3.5") * D("1.10")  # el compartido va en CPVC
    # lo propio de cada punto cambia con quien declara el material, pero el compartido no
    assert ta["AF-TUB-CPVC-1/2"] - D("3.5") * D("1.10") == tb["AF-TUB-PVC-1/2"]
    assert tb["AF-TUB-CPVC-1/2"] - D("3.5") * D("1.10") == ta["AF-TUB-PVC-1/2"]


def test_drenaje_con_tramo_compartido_y_tee() -> None:
    """Calculo a mano: D1 (2", piso en (1;1,5;0)) y D3 (1 1/2", pared en (1,5;1,5;0,5)) llegan al
    colector (2;0,75;0). Segmentos: a (de 1 a 1,5 en x, D1) 0,5; b (de 1,5 a 2 en x, D1 y D3) 0,5;
    c (en y, de 1,5 a 0,75, D1 y D3) 0,75; d (la bajante de D3) 0,5. Lo compartido toma 2"."""
    esp = espacio_bano_con_drenaje()
    d3 = replace(
        next(p for p in esp.puntos if p.id == "D2"),
        id="D3",
        posicion=Coord(D("1.5"), D("1.5"), D("0.5")),
    )
    esp = replace(esp, puntos=tuple(p for p in esp.puntos if p.id != "D2") + (d3,))
    items = _por_clave(derivar(esp, "agua"), "DR")
    assert items["tuberia_2"].cantidad == D("1.75") * D("1.10")
    assert items["tuberia_1 1/2"].cantidad == D("0.50") * D("1.10")
    assert items["tee_2"].cantidad == 1 and "tee_1 1/2" not in items
    assert items["codo_2"].cantidad == 1 and "codo_1 1/2" not in items
    assert items["picado_resane_piso"].cantidad == D("1.75")
    assert items["picado_resane_pared"].cantidad == D("0.50")
    assert items["salida_drenaje"].cantidad == 2
