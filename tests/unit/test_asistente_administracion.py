"""Configuracion del asistente por el administrador (S4 §3.1, §8.3; plan 0.9.0, tarea 15).

Sin Streamlit: `asistente.administracion` con la clave en memoria. Fronteras del tope de costo:
0 se rechaza y el menor positivo representable con dos decimales (0,01) se acepta; NaN e Infinity
se rechazan (bitacora 0.9.0, T15). El archivo de configuracion se compara campo por campo.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from asistente.administracion import (
    AVISO_DE_NUBE,
    SinPermiso,
    configurar,
    estado,
    olvidar_clave,
    reactivar_clave,
    registrar_clave,
)
from asistente.clave import ClaveDeIA, ClaveNoRegistrable
from asistente.configuracion import ConfiguracionIA, de_maprex, guardar, leer
from tests.fixtures.asistente_clave import AlmacenFalso, SecretosFalsos

PARAMETROS = dict(
    activo=True,
    proveedor="claude",
    modelo_claude="claude-opus-5-5",
    modelo_local="",
    anfitrion_ollama="http://127.0.0.1:11434",
    tope_usd="2,50",
)


def clave_de(tmp_path, almacen=None):
    return ClaveDeIA(
        almacen=almacen if almacen is not None else AlmacenFalso(),
        secretos=SecretosFalsos(),
        ruta_respaldo=tmp_path / "ia_clave.cifrada",
        es_local=lambda ip: ip == "127.0.0.1",
    )


@pytest.mark.parametrize(
    "contenido",
    [
        None,  # ausente
        "{ roto",
        '{"activo": true, "proveedor": "otro"}',  # un proveedor desconocido
        '{"activo": true, "tope_usd": "0"}',  # un tope no positivo
        '{"activo": true, "tope_usd": "dos"}',
        '{"activo": true, "campo_extra": 1}',  # un campo que no es de la configuracion
        "[]",  # JSON valido que no es un objeto (hallazgo de la auditoria: AttributeError)
        '"texto"',
        "null",
    ],
)
def test_de_fabrica_esta_apagado_y_un_archivo_ausente_o_roto_no_lo_enciende(tmp_path, contenido):
    ruta = tmp_path / "ia_config.json"
    if contenido is not None:
        ruta.write_text(contenido, encoding="utf-8")
    assert leer(ruta) == ConfiguracionIA() and not leer(ruta).activo


def test_la_configuracion_de_fabrica():
    cfg = ConfiguracionIA()
    assert (cfg.activo, cfg.proveedor, cfg.modelo_claude, cfg.modelo_local) == (
        False,
        "claude",
        "claude-opus-5-5",
        "",
    )
    assert cfg.anfitrion_ollama == "http://127.0.0.1:11434" and cfg.tope_usd == Decimal(2)


def test_solo_el_administrador_configura_y_el_tope_acepta_coma(tmp_path):
    ruta = tmp_path / "ia_config.json"
    with pytest.raises(SinPermiso, match="administrador"):
        configurar(ruta, es_administrador=False, **PARAMETROS)
    assert not ruta.exists()
    guardada = configurar(ruta, es_administrador=True, **PARAMETROS)
    assert guardada.tope_usd == Decimal("2.50") and leer(ruta) == guardada
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["tope_usd"] == "2.50" and datos["activo"] is True  # el tope como texto exacto


@pytest.mark.parametrize("tope", ["0,01", "0.01", " 3,5 ", "1000"])
def test_el_menor_tope_positivo_y_otros_validos_se_aceptan(tmp_path, tope):
    ruta = tmp_path / "ia_config.json"
    guardada = configurar(ruta, es_administrador=True, **{**PARAMETROS, "tope_usd": tope})
    assert guardada.tope_usd == Decimal(tope.strip().replace(",", "."))


@pytest.mark.parametrize(
    ("malo", "mensaje"),
    [
        ("dos", "no es un número"),
        ("", "no es un número"),
        ("NaN", "no es un número"),
        ("Infinity", "no es un número"),
        ("-Infinity", "no es un número"),
        ("0", "mayor que cero"),
        ("0,00", "mayor que cero"),
        ("-1", "mayor que cero"),
        ("-0,01", "mayor que cero"),
    ],
)
def test_un_tope_no_numerico_o_no_positivo_se_rechaza_y_no_toca_el_archivo(tmp_path, malo, mensaje):
    ruta = tmp_path / "ia_config.json"
    configurar(ruta, es_administrador=True, **PARAMETROS)
    antes = ruta.read_bytes()
    with pytest.raises(ValueError, match=mensaje):
        configurar(ruta, es_administrador=True, **{**PARAMETROS, "tope_usd": malo, "activo": False})
    assert ruta.read_bytes() == antes  # conserva el ultimo valido


def test_configurar_limpia_los_espacios_de_modelos_y_anfitrion(tmp_path):
    ruta = tmp_path / "ia_config.json"
    guardada = configurar(
        ruta,
        es_administrador=True,
        **{**PARAMETROS, "modelo_local": "  m  ", "anfitrion_ollama": " http://127.0.0.1:1 "},
    )
    assert guardada.modelo_local == "m" and guardada.anfitrion_ollama == "http://127.0.0.1:1"


def test_configurar_conserva_los_prefijos_de_maprex_guardados(tmp_path):
    ruta = tmp_path / "ia_config.json"
    guardar(ruta, ConfiguracionIA(prefijos_de_maprex=("MPX-",)))
    guardada = configurar(ruta, es_administrador=True, **PARAMETROS)
    assert guardada.prefijos_de_maprex == ("MPX-",)
    assert de_maprex("MPX-001", guardada) and not de_maprex("AF-SALIDA", guardada)


def test_desactivar_el_asistente_saca_la_clave_de_la_memoria_pero_no_la_borra(tmp_path):
    almacen = AlmacenFalso()
    clave = clave_de(tmp_path, almacen)
    clave.registrar("E", "sk-ant-abcd1234", ip_cliente="127.0.0.1")
    ruta = tmp_path / "ia_config.json"
    configurar(ruta, es_administrador=True, clave=clave, **PARAMETROS)  # activo: sigue
    assert clave.vigente == "sk-ant-abcd1234"
    configurar(ruta, es_administrador=True, clave=clave, **{**PARAMETROS, "activo": False})
    assert clave.vigente is None and almacen.datos  # sigue en el almacen
    clave.activar("E")
    assert clave.vigente == "sk-ant-abcd1234"


def test_registrar_la_clave_exige_administrador_y_cliente_local_y_muestra_cuatro_caracteres(
    tmp_path,
):
    clave = clave_de(tmp_path)
    ruta = tmp_path / "ia_config.json"
    with pytest.raises(SinPermiso):
        registrar_clave(
            clave, "E", "sk-ant-abcd1234", es_administrador=False, ip_cliente="127.0.0.1"
        )
    with pytest.raises(ClaveNoRegistrable, match="propio equipo"):
        registrar_clave(clave, "E", "sk-ant-abcd1234", es_administrador=True, ip_cliente="10.0.0.9")
    assert clave.vigente is None
    mostrada = registrar_clave(
        clave, "E", "sk-ant-abcd1234", es_administrador=True, ip_cliente="127.0.0.1"
    )
    assert mostrada == "…1234"
    visto = estado(ruta, clave)
    assert visto.clave_registrada == "…1234" and visto.aviso == AVISO_DE_NUBE
    assert visto.configuracion == ConfiguracionIA()  # sin archivo: la de fabrica, apagada
    assert "sk-ant-abcd1234" not in repr(visto)
    with pytest.raises(SinPermiso):
        olvidar_clave(clave, "E", es_administrador=False)
    assert clave.vigente is not None  # sin permiso no se olvido nada
    olvidar_clave(clave, "E", es_administrador=True)
    assert estado(ruta, clave).clave_registrada is None


def test_el_aviso_de_la_nube_dice_que_no_viaja():
    for palabra in ("precios", "montos", "nombres de proyecto", "excepción declarada"):
        assert palabra in AVISO_DE_NUBE


# --- reactivar la clave desde el respaldo cifrado (ruta, sesion 1, tarea 1.2) -----------------


def con_solo_el_respaldo(tmp_path):
    clave = clave_de(tmp_path, AlmacenFalso(cae=True))
    clave.registrar("E", "sk-ant-abcd1234", ip_cliente="127.0.0.1", contrasena_respaldo="c" * 12)
    clave.desactivar()
    return clave


def test_reactivar_sin_ser_administrador_sin_permiso(tmp_path):
    clave = con_solo_el_respaldo(tmp_path)
    with pytest.raises(SinPermiso, match="administrador"):
        reactivar_clave(clave, "E", "c" * 12, es_administrador=False, ip_cliente="127.0.0.1")
    assert clave.vigente is None
    assert (
        reactivar_clave(clave, "E", "c" * 12, es_administrador=True, ip_cliente="127.0.0.1")
        == "…1234"
    )
    assert clave.vigente == "sk-ant-abcd1234"


def test_reactivar_la_clave_desde_otro_equipo_se_rechaza(tmp_path):
    clave = con_solo_el_respaldo(tmp_path)
    with pytest.raises(ClaveNoRegistrable, match="solo se reactiva desde el propio equipo"):
        reactivar_clave(clave, "E", "c" * 12, es_administrador=True, ip_cliente="10.0.0.9")
    assert clave.vigente is None
