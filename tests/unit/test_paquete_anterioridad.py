"""Anterioridad entre paquetes, reenvío y banner de versión (S3 §6.5 y §8.3; 23c, 23h).

Oráculo: los textos literales del spec y la cadena sintética de `tests/fixtures/paquetes.py`
(huellas con `hashlib`, aparte del núcleo). El contenido de cada versión es `v<codigo>`: la misma
versión da la misma huella en cualquier paquete, como en la realidad (el eslabón es de la versión,
no del paquete).
"""

from __future__ import annotations

import json
from datetime import datetime

from paquete.verificar import evaluar_anterioridad
from tests.fixtures.paquetes import cadena_para

RECIBIDO_ANTES = datetime(2026, 11, 3, 8, 0)


def cadena_de(*codigos: str) -> dict:
    datos, _ = cadena_para(f"v{codigos[-1]}".encode(), {}, codigos)
    return json.loads(datos)


def previo(cadena: dict, codigo: str, sha="aaa", paquete_id="p-0", anexos=None, emitido=None):
    return {
        "huella_archivo": sha,
        "paquete_id": paquete_id,
        "codigo": codigo,
        "emitido": emitido or datetime(2026, 11, 3),
        "fecha": RECIBIDO_ANTES,
        "cadena": json.dumps([[e["codigo"], e["huella_eslabon"]] for e in cadena["eslabones"]]),
        "huellas_anexos": json.dumps(anexos or {}),
    }


def evaluar(cadena, previos, sha="nuevo", paquete_id="p-1", huellas=None):
    return evaluar_anterioridad({"paquete_id": paquete_id}, cadena, huellas or {}, sha, previos)


def test_la_misma_version_da_la_misma_huella_en_dos_paquetes() -> None:
    """Premisa de las pruebas: el prefijo común de dos cadenas del mismo proyecto es igual."""
    corta, larga = cadena_de("004"), cadena_de("004", "005")
    assert corta["eslabones"][0]["huella_eslabon"] == larga["eslabones"][0]["huella_eslabon"]


def test_el_primer_paquete_que_se_recibe_no_tiene_aviso_ni_ultima_recibida() -> None:
    r = evaluar(cadena_de("004", "005"), [])
    assert (r.avisos, r.ya_recibido, r.ultima_recibida) == ((), False, "")


def test_un_paquete_que_extiende_el_ultimo_recibido_no_avisa() -> None:
    anterior = cadena_de("004")
    r = evaluar(cadena_de("004", "005"), [previo(anterior, "004")])
    assert (r.avisos, r.ya_recibido) == ((), False)
    assert r.ultima_recibida == "versión 004 del 2026-11-03"


def test_un_paquete_que_reescribe_la_historia_lo_dice_con_la_version_y_la_fecha() -> None:
    recibida = cadena_de("003", "004")
    otra = cadena_de("003", "004b")
    otra["eslabones"][1]["huella_eslabon"] = "f" * 64
    r = evaluar(otra, [previo(recibida, "004")])
    assert r.avisos == (
        "Este paquete reescribe la historia: la versión 004 que recibió el 2026-11-03 tenía "
        "otra huella.",
    )


def test_reescribir_la_primera_version_tambien_se_dice() -> None:
    recibida = cadena_de("003", "004")
    otra = cadena_de("003", "004", "005")
    otra["eslabones"][0]["huella_eslabon"] = "e" * 64
    r = evaluar(otra, [previo(recibida, "004")])
    assert r.avisos == (
        "Este paquete reescribe la historia: la versión 003 que recibió el 2026-11-03 tenía "
        "otra huella.",
    )


def test_un_paquete_anterior_a_uno_ya_recibido_se_avisa() -> None:
    recibida = cadena_de("004", "005")
    r = evaluar(cadena_de("004"), [previo(recibida, "005")])
    assert r.avisos == (
        "Este paquete es anterior a uno que ya recibió (versión 005 del 2026-11-03).",
    )


def test_un_paquete_de_la_misma_version_con_otro_archivo_se_avisa_como_anterior() -> None:
    """Frontera de la longitud: la misma cadena (len igual) con otro SHA y otro id es «anterior
    o igual», no una extensión."""
    cadena = cadena_de("004", "005")
    r = evaluar(cadena, [previo(cadena, "005", sha="x", paquete_id="p-x")])
    assert r.avisos == (
        "Este paquete es anterior a uno que ya recibió (versión 005 del 2026-11-03).",
    )
    assert not r.ya_recibido


def test_el_mismo_paquete_otra_vez_se_reconoce_por_el_sha_256_o_por_el_paquete_id() -> None:
    cadena = cadena_de("004", "005")
    visto = previo(cadena, "005", sha="igual", paquete_id="p-9")
    por_sha = evaluar(cadena, [visto], sha="igual", paquete_id="otro")
    por_id = evaluar(cadena, [visto], sha="distinto", paquete_id="p-9")
    for r in (por_sha, por_id):
        assert r.ya_recibido and r.avisos == ("Ya recibió este mismo paquete el 2026-11-03.",)
        assert r.ultima_recibida == "versión 005 del 2026-11-03"


def test_el_reenvio_se_reconoce_aunque_no_sea_el_ultimo_recibido() -> None:
    viejo = previo(cadena_de("004"), "004", sha="viejo", paquete_id="p-v")
    ultimo = previo(cadena_de("004", "005"), "005", sha="ultimo", paquete_id="p-u")
    r = evaluar(cadena_de("004"), [viejo, ultimo], sha="viejo", paquete_id="p-nuevo")
    assert r.ya_recibido and r.ultima_recibida == "versión 005 del 2026-11-03"


def test_una_entrada_de_un_anexo_que_ya_no_viene_se_avisa() -> None:
    cadena = cadena_de("004", "005")
    visto = previo(cadena_de("004"), "004", anexos={"anexos/control.json": ["h1", "h2", "h3"]})
    r = evaluar(cadena, [visto], huellas={"anexos/control.json": ["h1", "h3"]})
    assert r.avisos == (
        "1 entrada(s) de anexos/control.json que recibió el 2026-11-03 ya no vienen.",
    )


def test_entradas_que_siguen_o_que_se_agregan_no_avisan() -> None:
    cadena = cadena_de("004", "005")
    visto = previo(cadena_de("004"), "004", anexos={"anexos/control.json": ["h1", "h2"]})
    r = evaluar(cadena, [visto], huellas={"anexos/control.json": ["h1", "h2", "h3"]})
    assert r.avisos == ()


def test_un_anexo_entero_que_ya_no_viene_cuenta_todas_sus_entradas_en_orden() -> None:
    cadena = cadena_de("004", "005")
    antes = {"anexos/reajuste.json": ["r1", "r2"], "anexos/control.json": ["c1"]}
    visto = previo(cadena_de("004"), "004", anexos=antes)
    r = evaluar(cadena, [visto], huellas={})
    assert r.avisos == (
        "1 entrada(s) de anexos/control.json que recibió el 2026-11-03 ya no vienen.",
        "2 entrada(s) de anexos/reajuste.json que recibió el 2026-11-03 ya no vienen.",
    )


def test_solo_cuenta_el_ultimo_paquete_recibido() -> None:
    viejo = previo(cadena_de("001"), "001", sha="v", paquete_id="p-v")
    ultimo = previo(cadena_de("001", "002", "003"), "003", sha="u", paquete_id="p-u")
    r = evaluar(cadena_de("001", "002", "003", "004"), [viejo, ultimo])
    assert r.avisos == () and r.ultima_recibida == "versión 003 del 2026-11-03"


def test_la_fecha_del_aviso_anterior_es_la_de_emision_y_la_de_reescritura_la_de_recepcion() -> None:
    recibida = cadena_de("004", "005")
    emitido = datetime(2026, 11, 1, 23, 59)
    r = evaluar(cadena_de("004"), [previo(recibida, "005", emitido=emitido)])
    assert r.avisos == (
        "Este paquete es anterior a uno que ya recibió (versión 005 del 2026-11-01).",
    )
    assert r.ultima_recibida == "versión 005 del 2026-11-01"
