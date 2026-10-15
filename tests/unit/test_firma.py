"""Firma Ed25519 con separación de dominio y huella legible (RF-84; spec S3 §7; RFC 8032 §7.1).

Oráculos independientes: los vectores TEST 1 y TEST 2 del RFC 8032 §7.1 (literales del RFC) y las
huellas de sus claves públicas, calculadas aparte (`printf <hex> | xxd -r -p | sha256sum` y los
primeros 100 bits pasados a mano al alfabeto de Crockford), nunca con `seguridad.firma`.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime

import pytest

from seguridad import firma
from seguridad.json_estricto import JsonRechazado

#: Vectores de prueba del RFC 8032, sección 7.1 (TEST 1 y TEST 2): la biblioteca se usa bien.
RFC_8032 = (
    (
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        "",
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e3970"
        "1cf9b46bd25bf5f0595bbe24655141438e7a100b",
    ),
    (
        "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
        "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
        "72",
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613"
        "d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
    ),
)
#: SHA-256 de las claves públicas del RFC y su huella corta (calculadas fuera de Sílice).
HUELLAS_RFC = (
    (
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        "21fe31dfa154a261626bf854046fd2271b7bed4b6abe45aa58877ef47f9721b9",
        "47Z3-3QX1-AJH6-2RKB-Z1A0",
    ),
    (
        "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
        "39f713d0a644253f04529421b9f51b9b08979d08295959c4f3990ee617f5139f",
        "77VH-7M56-8GJK-Y12J-JGGV",
    ),
)
#: Crockford sin I, L, O ni U (spec S3 §7.2), escrito aquí como literal.
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
AHORA = datetime(2026, 11, 10, 9, 30)


def _cambiar_un_byte(datos: bytes, posicion: int) -> bytes:
    return datos[:posicion] + bytes([datos[posicion] ^ 0x01]) + datos[posicion + 1 :]


# --- vectores del RFC 8032 --------------------------------------------------------------------


@pytest.mark.parametrize("privada,publica,mensaje,firma_esperada", RFC_8032)
def test_vectores_del_rfc_8032(privada: str, publica: str, mensaje: str, firma_esperada: str):
    privada_b, publica_b = bytes.fromhex(privada), bytes.fromhex(publica)
    assert firma.publica_de(privada_b) == publica_b
    # sin dominio: el vector del RFC es la firma del mensaje tal cual
    assert firma.firmar(privada_b, b"", bytes.fromhex(mensaje)).hex() == firma_esperada
    assert firma.verificar(publica_b, b"", bytes.fromhex(mensaje), bytes.fromhex(firma_esperada))


@pytest.mark.parametrize("privada,publica,mensaje,firma_esperada", RFC_8032)
def test_un_byte_cambiado_en_la_firma_del_rfc_la_invalida(
    privada: str, publica: str, mensaje: str, firma_esperada: str
) -> None:
    publica_b, mensaje_b = bytes.fromhex(publica), bytes.fromhex(mensaje)
    buena = bytes.fromhex(firma_esperada)
    for posicion in (0, 31, 32, 63):  # primer y último byte de R y de S
        mala = _cambiar_un_byte(buena, posicion)
        assert firma.verificar(publica_b, b"", mensaje_b, mala) is False


def test_un_byte_cambiado_en_el_mensaje_del_rfc_la_invalida() -> None:
    _, publica, mensaje, firma_esperada = RFC_8032[1]  # TEST 2: mensaje de un byte (0x72)
    mensaje_b = bytes.fromhex(mensaje)
    otro = _cambiar_un_byte(mensaje_b, 0)
    assert (
        firma.verificar(bytes.fromhex(publica), b"", otro, bytes.fromhex(firma_esperada)) is False
    )
    # y la firma del TEST 2 no vale para el mensaje vacío del TEST 1
    assert firma.verificar(bytes.fromhex(publica), b"", b"", bytes.fromhex(firma_esperada)) is False


def test_la_firma_de_un_rfc_no_vale_con_la_clave_del_otro() -> None:
    (_, publica_1, mensaje_1, firma_1), (_, publica_2, _, _) = RFC_8032
    assert not firma.verificar(
        bytes.fromhex(publica_2), b"", bytes.fromhex(mensaje_1), bytes.fromhex(firma_1)
    )
    assert firma.verificar(
        bytes.fromhex(publica_1), b"", bytes.fromhex(mensaje_1), bytes.fromhex(firma_1)
    )


def test_firmar_es_determinista_y_firma_el_dominio_mas_el_mensaje() -> None:
    privada = bytes.fromhex(RFC_8032[0][0])
    publica = bytes.fromhex(RFC_8032[0][1])
    con_dominio = firma.firmar(privada, firma.DOMINIO_PAQUETE, b"m")
    assert con_dominio == firma.firmar(privada, firma.DOMINIO_PAQUETE, b"m")
    # firmar con dominio = firmar el prefijo concatenado sin dominio (es lo que dice el spec)
    assert con_dominio == firma.firmar(privada, b"", b"silice-paquete-v1\0m")
    assert not firma.verificar(publica, b"", b"m", con_dominio)  # sin el prefijo no vale


# --- huella ----------------------------------------------------------------------------------


@pytest.mark.parametrize("publica,completa,corta", HUELLAS_RFC)
def test_la_huella_de_las_claves_del_rfc_es_el_literal_calculado_aparte(
    publica: str, completa: str, corta: str
) -> None:
    assert firma.huella_completa(bytes.fromhex(publica)) == completa
    assert firma.huella_corta(bytes.fromhex(publica)) == corta


def test_el_alfabeto_de_la_huella_es_crockford() -> None:
    assert firma.ALFABETO_HUELLA == CROCKFORD and len(set(CROCKFORD)) == 32


def test_la_huella_corta_son_cinco_grupos_de_cuatro_sin_simbolos_ambiguos() -> None:
    par = firma.generar_par()
    corta = firma.huella_corta(par.publica)
    grupos = corta.split("-")
    assert [len(g) for g in grupos] == [4, 4, 4, 4, 4]
    assert set(corta.replace("-", "")) <= set(CROCKFORD)
    assert not set("ILOU") & set(corta)
    assert firma.huella_corta(par.publica) == corta  # determinista
    assert firma.normalizar_huella_corta(corta.lower().replace("-", " ")) == corta


def test_la_huella_corta_toma_los_primeros_100_bits_de_la_completa() -> None:
    import hashlib

    par = firma.generar_par()
    completa = int(hashlib.sha256(par.publica).hexdigest(), 16)  # oráculo fuera del módulo
    corta = firma.huella_corta(par.publica).replace("-", "")
    valor = 0
    for simbolo in corta:
        valor = (valor << 5) | CROCKFORD.index(simbolo)
    assert valor == completa >> (256 - 100)


def test_normalizar_admite_espacios_minusculas_y_guiones() -> None:
    corta = HUELLAS_RFC[0][2]
    for escrita in (corta, corta.lower(), corta.replace("-", ""), " 47z3 3qx1 ajh6 2rkb z1a0 "):
        assert firma.normalizar_huella_corta(escrita) == corta


@pytest.mark.parametrize(
    "malo",
    [
        "",
        "ABC",
        "K7QF-M9XR-A2PT-W4HN-C8D",  # 19 símbolos (frontera inferior)
        "K7QF-M9XR-A2PT-W4HN-C8DVX",  # 21 símbolos (frontera superior)
        "K7QF-M9XR-A2PT-W4HN-C8DI",  # I es ambigua
        "K7QF-M9XR-A2PT-W4HN-C8DL",  # L es ambigua
        "K7QF-M9XR-A2PT-W4HN-C8DO",  # O es ambigua
        "K7QF-M9XR-A2PT-W4HN-C8DU",  # U no está en Crockford
    ],
)
def test_normalizar_rechaza_lo_que_no_es_una_huella(malo: str) -> None:
    with pytest.raises(ValueError):
        firma.normalizar_huella_corta(malo)


def test_normalizar_acepta_exactamente_20_simbolos() -> None:
    assert firma.normalizar_huella_corta("K7QF-M9XR-A2PT-W4HN-C8DV") == "K7QF-M9XR-A2PT-W4HN-C8DV"


# --- separación de dominio y firmas malas ----------------------------------------------------


def test_una_firma_de_un_dominio_no_vale_en_el_otro() -> None:
    par = firma.generar_par()
    mensaje = b"{}"
    del_paquete = firma.firmar(par.privada, firma.DOMINIO_PAQUETE, mensaje)
    assert firma.verificar(par.publica, firma.DOMINIO_PAQUETE, mensaje, del_paquete)
    assert not firma.verificar(par.publica, firma.DOMINIO_REVOCACION, mensaje, del_paquete)
    de_revocacion = firma.firmar(par.privada, firma.DOMINIO_REVOCACION, mensaje)
    assert firma.verificar(par.publica, firma.DOMINIO_REVOCACION, mensaje, de_revocacion)
    assert not firma.verificar(par.publica, firma.DOMINIO_PAQUETE, mensaje, de_revocacion)


def test_los_dominios_son_los_del_spec() -> None:
    assert firma.DOMINIO_PAQUETE == b"silice-paquete-v1\x00"
    assert firma.DOMINIO_REVOCACION == b"silice-revocacion-v1\x00"


@pytest.mark.parametrize("tamano", [0, 1, 63, 65])
def test_firma_vacia_o_truncada_es_falsa_sin_lanzar(tamano: int) -> None:
    par = firma.generar_par()
    buena = firma.firmar(par.privada, firma.DOMINIO_PAQUETE, b"m")
    assert len(buena) == 64
    assert not firma.verificar(par.publica, firma.DOMINIO_PAQUETE, b"m", (buena + b"x")[:tamano])


def test_una_firma_de_ceros_es_falsa_sin_lanzar() -> None:
    par = firma.generar_par()
    assert not firma.verificar(par.publica, firma.DOMINIO_PAQUETE, b"m", bytes(64))


def test_un_byte_cambiado_en_el_mensaje_con_dominio_la_invalida() -> None:
    par = firma.generar_par()
    mensaje = b'{"paquete":"PQ-1","total":"28586.76"}'
    buena = firma.firmar(par.privada, firma.DOMINIO_PAQUETE, mensaje)
    for posicion in (0, len(mensaje) // 2, len(mensaje) - 1):
        otro = _cambiar_un_byte(mensaje, posicion)
        assert not firma.verificar(par.publica, firma.DOMINIO_PAQUETE, otro, buena)


@pytest.mark.parametrize("tamano", [0, 31, 33])
def test_una_clave_publica_de_tamano_malo_es_falsa_sin_lanzar(tamano: int) -> None:
    assert not firma.verificar(b"k" * tamano, firma.DOMINIO_PAQUETE, b"m", b"x" * 64)


def test_la_clave_publica_corta_del_plan_es_falsa_sin_lanzar() -> None:
    assert not firma.verificar(b"corta", firma.DOMINIO_PAQUETE, b"m", b"x" * 64)


def test_generar_par_da_32_bytes_y_pares_distintos() -> None:
    uno, otro = firma.generar_par(), firma.generar_par()
    assert len(uno.privada) == len(uno.publica) == 32
    assert firma.publica_de(uno.privada) == uno.publica
    assert uno.privada != otro.privada and uno.publica != otro.publica


# --- archivo de clave pública ----------------------------------------------------------------


def test_exportar_y_leer_la_clave_publica_calcula_la_huella_el_sistema() -> None:
    par = firma.generar_par()
    archivo = firma.exportar_clave_publica(
        "Contratista Demo, C.A.", "J-00000000-0", par.publica, AHORA
    )
    leida = firma.leer_clave_publica(archivo)
    assert (leida.nombre, leida.rif, leida.publica) == (
        "Contratista Demo, C.A.",
        "J-00000000-0",
        par.publica,
    )
    assert leida.huella == firma.huella_completa(par.publica) and leida.huella_coincide
    documento = json.loads(archivo)
    assert documento["formato"] == "silice-clave" and documento["version_formato"] == 1
    assert base64.b64decode(documento["clave_publica"]) == par.publica
    assert documento["fecha"] == "2026-11-10T09:30:00"


def test_el_archivo_de_la_clave_del_rfc_lleva_su_huella_literal() -> None:
    publica, completa, corta = HUELLAS_RFC[0]
    archivo = firma.exportar_clave_publica("Demo", "", bytes.fromhex(publica), AHORA)
    leida = firma.leer_clave_publica(archivo)
    assert (leida.huella, leida.huella_corta, leida.huella_corta_declarada) == (
        completa,
        corta,
        corta,
    )


def test_una_huella_declarada_falsa_se_nota() -> None:
    par, otra = firma.generar_par(), firma.generar_par()
    archivo = firma.exportar_clave_publica("X", "", par.publica, AHORA)
    falso = archivo.replace(
        firma.huella_corta(par.publica).encode(), firma.huella_corta(otra.publica).encode()
    )
    leida = firma.leer_clave_publica(falso)
    assert not leida.huella_coincide
    # la huella que usa el sistema sigue siendo la calculada, no la declarada
    assert leida.huella_corta == firma.huella_corta(par.publica)


def test_un_archivo_de_clave_con_clave_duplicada_se_rechaza() -> None:
    with pytest.raises(JsonRechazado):
        firma.leer_clave_publica(b'{"formato":"silice-clave","formato":"silice-clave"}')
    with pytest.raises(JsonRechazado):
        firma.leer_clave_publica(b'{"formato":"otro"}')


def _archivo_de_clave(**cambios: object) -> bytes:
    documento: dict[str, object] = {
        "formato": "silice-clave",
        "version_formato": 1,
        "nombre": "Demo",
        "rif": "",
        "clave_publica": base64.b64encode(bytes(32)).decode(),
        "huella": "",
        "fecha": "2026-11-10T09:30:00",
    }
    documento.update(cambios)
    return json.dumps({k: v for k, v in documento.items() if v is not None}).encode()


@pytest.mark.parametrize(
    "cambios",
    [
        {"clave_publica": base64.b64encode(bytes(31)).decode()},  # 31 bytes
        {"clave_publica": base64.b64encode(bytes(33)).decode()},  # 33 bytes
        {"clave_publica": "no es base64!"},
        {"clave_publica": None},  # falta
        {"nombre": "   "},  # sin nombre
        {"nombre": None},
    ],
)
def test_un_archivo_de_clave_danado_se_rechaza(cambios: dict) -> None:
    with pytest.raises(JsonRechazado):
        firma.leer_clave_publica(_archivo_de_clave(**cambios))


def test_un_archivo_de_clave_de_32_bytes_y_sin_rif_se_lee() -> None:
    leida = firma.leer_clave_publica(_archivo_de_clave(rif=None))
    assert (leida.nombre, leida.rif, len(leida.publica)) == ("Demo", "", 32)


# --- aviso de revocación ---------------------------------------------------------------------


def test_el_aviso_de_revocacion_firmado_se_valida_y_uno_falso_no() -> None:
    par = firma.generar_par()
    aviso = firma.crear_aviso_revocacion(par.privada, "se perdio el equipo", AHORA)
    publica, motivo, valida = firma.leer_aviso_revocacion(aviso)
    assert (publica, motivo, valida) == (par.publica, "se perdio el equipo", True)
    manipulado = aviso.replace(b"se perdio el equipo", b"otro motivo")
    assert firma.leer_aviso_revocacion(manipulado)[2] is False


def test_un_aviso_con_la_fecha_cambiada_o_la_firma_truncada_no_vale_y_no_lanza() -> None:
    par = firma.generar_par()
    aviso = firma.crear_aviso_revocacion(par.privada, "robo", AHORA)
    otra_fecha = aviso.replace(b"2026-11-10T09:30:00", b"2026-11-09T09:30:00")
    assert otra_fecha != aviso and firma.leer_aviso_revocacion(otra_fecha)[2] is False
    documento = json.loads(aviso)
    firma_b = base64.b64decode(documento["firma"])
    truncada = json.dumps({**documento, "firma": base64.b64encode(firma_b[:63]).decode()})
    assert firma.leer_aviso_revocacion(truncada.encode())[2] is False
    vacia = json.dumps({**documento, "firma": ""})
    assert firma.leer_aviso_revocacion(vacia.encode())[2] is False


def test_un_aviso_con_la_clave_cambiada_no_vale() -> None:
    """Quien cambia la clave pública del aviso por la suya no puede reusar la firma ajena."""
    par, intruso = firma.generar_par(), firma.generar_par()
    documento = json.loads(firma.crear_aviso_revocacion(par.privada, "robo", AHORA))
    documento["clave_publica"] = base64.b64encode(intruso.publica).decode()
    publica, _, valida = firma.leer_aviso_revocacion(json.dumps(documento).encode())
    assert publica == intruso.publica and valida is False


def test_un_aviso_de_otro_formato_o_incompleto_se_rechaza() -> None:
    with pytest.raises(JsonRechazado):
        firma.leer_aviso_revocacion(b'{"formato":"silice-clave"}')
    with pytest.raises(JsonRechazado):
        firma.leer_aviso_revocacion(b'{"formato":"silice-revocacion","clave_publica":"AAAA"}')
    with pytest.raises(JsonRechazado):
        firma.leer_aviso_revocacion(
            b'{"formato":"silice-revocacion","formato":"silice-revocacion"}'
        )


def test_una_firma_de_paquete_no_sirve_de_aviso_de_revocacion() -> None:
    par = firma.generar_par()
    cuerpo = {
        "formato": firma.FORMATO_REVOCACION,
        "version_formato": 1,
        "huella": firma.huella_completa(par.publica),
        "clave_publica": base64.b64encode(par.publica).decode(),
        "motivo": "m",
        "fecha": AHORA.isoformat(timespec="seconds"),
    }
    canonico = json.dumps(cuerpo, sort_keys=True, separators=(",", ":")).encode()
    mala = firma.firmar(par.privada, firma.DOMINIO_PAQUETE, canonico)  # dominio equivocado
    falso = json.dumps({**cuerpo, "firma": base64.b64encode(mala).decode()}).encode()
    assert firma.leer_aviso_revocacion(falso)[2] is False
    # el mismo cuerpo firmado con el dominio de revocación sí vale (el control es el dominio)
    buena = firma.firmar(par.privada, firma.DOMINIO_REVOCACION, canonico)
    cierto = json.dumps({**cuerpo, "firma": base64.b64encode(buena).decode()}).encode()
    assert firma.leer_aviso_revocacion(cierto)[2] is True


def test_la_firma_de_un_aviso_no_vale_como_firma_de_paquete() -> None:
    par = firma.generar_par()
    documento = json.loads(firma.crear_aviso_revocacion(par.privada, "robo", AHORA))
    firma_aviso = base64.b64decode(documento.pop("firma"))
    canonico = json.dumps(documento, sort_keys=True, separators=(",", ":")).encode()
    assert firma.verificar(par.publica, firma.DOMINIO_REVOCACION, canonico, firma_aviso)
    assert not firma.verificar(par.publica, firma.DOMINIO_PAQUETE, canonico, firma_aviso)
