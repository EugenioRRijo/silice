"""Empresa propia, clave de firma y empresas ajenas (RF-84; spec S3 §7, §5.6 y §13.2).

Cada `generar_clave` y cada `abrir_privada` gasta un Argon2id de 64 MiB (unos 0,3 s): el mínimo
del spec no se baja para las pruebas (`ParametrosKdf` lo impide), así que se cuentan.
"""

from __future__ import annotations

import base64
import json
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from seguridad import empresas, firma
from seguridad.modelo import ClaveEmpresa, EmpresaPropia, EmpresaRegistrada, EventoAcceso
from seguridad.secretos import ContrasenaRechazada, InvalidTag, SecretoCifrado, descifrar
from tests.fixtures.instalacion import AHORA, instalacion

CLAVE = "frase de firma larga y propia"


@pytest.fixture
def con_empresa(tmp_path: Path):
    with instalacion(tmp_path) as sesion:
        empresas.guardar_empresa_propia(
            sesion, "Contratista Demo, C.A.", "J-00000000-0", "Caracas", "ana", AHORA
        )
        yield sesion


def _archivo_ajeno(nombre: str = "Otra Empresa, C.A.") -> tuple[bytes, firma.ParDeClaves]:
    par = firma.generar_par()
    return firma.exportar_clave_publica(nombre, "J-11111111-1", par.publica, AHORA), par


def _bytes_de_la_base(carpeta: Path) -> bytes:
    """Todo lo que hay en disco de la base: el archivo, su WAL y su memoria compartida."""
    return b"".join(p.read_bytes() for p in sorted(carpeta.glob("instalacion.db*")))


def _formas(privada: bytes) -> tuple[bytes, ...]:
    """La privada en claro tal cual, en hexadecimal y en base64."""
    return (privada, privada.hex().encode(), base64.b64encode(privada))


def _todas_las_celdas(sesion) -> list[object]:
    """Cada valor de cada columna de cada tabla de la instalación (búsqueda exhaustiva)."""
    tablas = sesion.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars()
    celdas: list[object] = []
    for tabla in list(tablas):
        for fila in sesion.execute(text(f'SELECT * FROM "{tabla}"')):
            celdas.extend(fila)
    return celdas


# --- empresa propia -------------------------------------------------------------------------


def test_una_sola_empresa_propia_y_guardar_otra_vez_la_actualiza(con_empresa) -> None:
    empresas.guardar_empresa_propia(con_empresa, " Otra, C.A. ", " J-2 ", "", "luis", AHORA)
    assert con_empresa.query(EmpresaPropia).count() == 1
    propia = empresas.empresa_propia(con_empresa)
    assert (propia.id, propia.nombre, propia.rif, propia.actualizada_por) == (
        1,
        "Otra, C.A.",
        "J-2",
        "luis",
    )


@pytest.mark.parametrize("nombre,rif", [("", "J-1"), ("  ", "J-1"), ("X", ""), ("X", "  ")])
def test_la_empresa_necesita_nombre_y_rif(tmp_path: Path, nombre: str, rif: str) -> None:
    with instalacion(tmp_path) as sesion:
        with pytest.raises(empresas.ClaveError, match="nombre y RIF"):
            empresas.guardar_empresa_propia(sesion, nombre, rif, "", "ana", AHORA)
        assert empresas.empresa_propia(sesion) is None


# --- clave de firma propia ------------------------------------------------------------------


def test_generar_cifra_la_privada_y_la_huella_es_la_misma_en_otra_base(tmp_path: Path):
    with instalacion(tmp_path / "a") as una, instalacion(tmp_path / "b") as otra:
        for sesion in (una, otra):
            empresas.guardar_empresa_propia(sesion, "X", "J-1", "", "ana", AHORA)
        clave = empresas.generar_clave(una, CLAVE, "ana", AHORA)
        privada = empresas.abrir_privada(una, CLAVE)
        assert len(privada) == 32
        assert clave.privada_cifrada != privada and privada not in (clave.privada_cifrada or b"")
        assert firma.publica_de(privada) == clave.publica
        assert clave.huella == firma.huella_completa(clave.publica)
        # la misma clave pública, llevada a la otra instalación, da la misma huella
        archivo = empresas.exportar_clave_publica_propia(una, AHORA)
        fila = empresas.registrar_empresa_ajena(
            otra, archivo, firma.huella_corta(clave.publica), "Ana", "telefono", "ana", AHORA
        )
        assert (fila.huella, fila.publica) == (clave.huella, clave.publica)
        # ninguna celda de ninguna tabla contiene la privada (cruda, hex o base64)
        for celda in _todas_las_celdas(una):
            if isinstance(celda, bytes | str):
                bruto = celda if isinstance(celda, bytes) else celda.encode()
                assert not any(forma in bruto for forma in _formas(privada))
    bruto = _bytes_de_la_base(tmp_path / "a")
    assert not any(forma in bruto for forma in _formas(privada))  # nunca sin cifrar en disco
    assert CLAVE.encode() not in bruto  # ni la contraseña de la clave


def test_la_privada_se_guarda_con_argon2id_y_aes_gcm(con_empresa) -> None:
    clave = empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    parametros = json.loads(clave.kdf)
    assert parametros == {"alg": "argon2id", "v": 19, "m": 65536, "t": 3, "p": 4}
    assert len(clave.sal) == 16 and len(clave.nonce) == 12
    assert len(clave.privada_cifrada) == 32 + 16  # 32 B de la privada y 16 B de etiqueta GCM
    # el cifrado está atado a la huella de la clave (dato asociado): con otra huella no abre
    guardado = SecretoCifrado(clave.kdf, clave.sal, clave.nonce, clave.privada_cifrada)
    privada = descifrar(guardado, CLAVE, clave.huella)
    assert firma.publica_de(privada) == clave.publica
    with pytest.raises(InvalidTag):
        descifrar(guardado, CLAVE, "0" * 64)


def test_dos_claves_no_comparten_sal_ni_nonce(con_empresa) -> None:
    primera = empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    sal, nonce, cifrado = primera.sal, primera.nonce, primera.privada_cifrada
    empresas.retirar_clave(con_empresa, "ana", AHORA)
    segunda = empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)  # misma contraseña
    assert segunda.id != primera.id
    assert (segunda.sal, segunda.nonce, segunda.privada_cifrada) != (sal, nonce, cifrado)
    assert segunda.sal != sal and segunda.nonce != nonce
    assert con_empresa.query(ClaveEmpresa).filter_by(estado="activa").count() == 1


def test_contrasena_de_clave_erronea_da_un_mensaje_sin_traza(con_empresa) -> None:
    empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    with pytest.raises(empresas.ContrasenaDeClaveIncorrecta, match="no es correcta") as error:
        empresas.abrir_privada(con_empresa, CLAVE + "x")
    assert error.value.__cause__ is None and error.value.__suppress_context__
    assert not isinstance(error.value, KeyError)
    assert CLAVE not in str(error.value)
    # el fallo no estropea nada: con la buena sigue abriendo
    assert len(empresas.abrir_privada(con_empresa, CLAVE)) == 32


@pytest.mark.parametrize(
    "mala",
    [
        "corta",
        "a" * 11,  # 11: frontera inferior (el mínimo es 12)
        "administrador",  # de la lista de comunes
        "  Administrador  ",
        "x" * 129,  # 129: frontera superior (el máximo es 128)
    ],
)
def test_contrasena_corta_larga_o_comun_no_genera_clave(con_empresa, mala: str) -> None:
    with pytest.raises(ContrasenaRechazada):
        empresas.generar_clave(con_empresa, mala, "ana", AHORA)
    assert con_empresa.query(ClaveEmpresa).count() == 0


def test_las_contrasenas_de_12_y_de_128_caracteres_generan_clave(con_empresa) -> None:
    corta = "b" * 11 + "c"  # 12: frontera inferior
    clave = empresas.generar_clave(con_empresa, corta, "ana", AHORA)
    assert clave.estado == "activa"
    empresas.retirar_clave(con_empresa, "ana", AHORA)
    larga = "d" * 127 + "e"  # 128: frontera superior
    otra = empresas.generar_clave(con_empresa, larga, "ana", AHORA)
    assert otra.estado == "activa" and len(empresas.abrir_privada(con_empresa, larga)) == 32


def test_solo_una_clave_activa_y_hace_falta_la_empresa(tmp_path: Path, con_empresa) -> None:
    empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    with pytest.raises(empresas.ClaveError, match="Ya hay una clave activa"):
        empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    assert con_empresa.query(ClaveEmpresa).count() == 1
    with instalacion(tmp_path / "vacia") as sin_empresa:
        with pytest.raises(empresas.ClaveError, match="datos de la empresa"):
            empresas.generar_clave(sin_empresa, CLAVE, "ana", AHORA)
        assert sin_empresa.query(ClaveEmpresa).count() == 0


def test_sin_clave_activa_no_hay_privada_ni_respaldo_ni_publica(con_empresa) -> None:
    for accion in (
        lambda: empresas.abrir_privada(con_empresa, CLAVE),
        lambda: empresas.exportar_respaldo_cifrado(con_empresa),
        lambda: empresas.exportar_clave_publica_propia(con_empresa, AHORA),
        lambda: empresas.retirar_clave(con_empresa, "ana", AHORA),
        lambda: empresas.revocar_clave_propia(con_empresa, "ana", AHORA, "robo"),
    ):
        with pytest.raises(empresas.ClaveError, match="no tiene una clave de firma activa"):
            accion()


def test_retirar_destruye_la_privada_en_la_base(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        empresas.guardar_empresa_propia(sesion, "X", "J-1", "", "ana", AHORA)
        clave = empresas.generar_clave(sesion, CLAVE, "ana", AHORA)
        cifrado = clave.privada_cifrada
        retirada = empresas.retirar_clave(sesion, "ana", AHORA, "cambio de equipo")
        assert (retirada.estado, retirada.privada_cifrada, retirada.sal, retirada.nonce) == (
            "retirada",
            None,
            None,
            None,
        )
        assert retirada.kdf is None and retirada.motivo == "cambio de equipo"
        assert retirada.fecha_estado == AHORA
        sesion.expire_all()  # lo que quedó en la base, no en el objeto
        fila = sesion.get(ClaveEmpresa, clave.id)
        assert (fila.privada_cifrada, fila.kdf, fila.sal, fila.nonce) == (None, None, None, None)
        assert fila.publica == clave.publica  # la pública queda para verificar lo ya firmado
        with pytest.raises(empresas.ClaveError, match="no tiene una clave de firma activa"):
            empresas.abrir_privada(sesion, CLAVE)
        empresas.generar_clave(sesion, CLAVE, "ana", AHORA)  # ya se puede generar otra
    assert cifrado is not None and cifrado not in _bytes_de_la_base(tmp_path)


def test_revocar_con_la_contrasena_da_un_aviso_firmado_y_destruye_la_privada(con_empresa):
    clave = empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    aviso = empresas.revocar_clave_propia(con_empresa, "ana", AHORA, "robo", CLAVE)
    publica, motivo, valida = firma.leer_aviso_revocacion(aviso)
    assert (publica, motivo, valida) == (clave.publica, "robo", True)
    con_empresa.expire_all()
    fila = con_empresa.get(ClaveEmpresa, clave.id)
    assert (fila.estado, fila.privada_cifrada, fila.kdf, fila.sal, fila.nonce) == (
        "revocada",
        None,
        None,
        None,
        None,
    )
    assert empresas.clave_activa(con_empresa) is None


def test_revocar_con_la_contrasena_erronea_no_revoca_nada(con_empresa) -> None:
    clave = empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    with pytest.raises(empresas.ContrasenaDeClaveIncorrecta):
        empresas.revocar_clave_propia(con_empresa, "ana", AHORA, "robo", CLAVE + "x")
    con_empresa.expire_all()
    fila = con_empresa.get(ClaveEmpresa, clave.id)
    assert fila.estado == "activa" and fila.privada_cifrada is not None


def test_revocar_sin_la_contrasena_no_da_aviso(con_empresa) -> None:
    empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    assert empresas.revocar_clave_propia(con_empresa, "ana", AHORA, "se perdio la clave") is None
    fila = con_empresa.query(ClaveEmpresa).one()
    assert (fila.estado, fila.privada_cifrada, fila.motivo) == (
        "revocada",
        None,
        "se perdio la clave",
    )


def test_el_respaldo_cifrado_no_trae_la_privada_en_claro_y_se_puede_abrir(con_empresa) -> None:
    clave = empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    privada = empresas.abrir_privada(con_empresa, CLAVE)
    respaldo = empresas.exportar_respaldo_cifrado(con_empresa)
    assert not any(forma in respaldo for forma in _formas(privada))
    assert CLAVE.encode() not in respaldo
    documento = json.loads(respaldo)
    assert documento["formato"] == "silice-clave-cifrada" and documento["version_formato"] == 1
    assert documento["huella"] == clave.huella
    # el respaldo sirve: con la contraseña se recupera la misma privada
    guardado = SecretoCifrado(
        documento["kdf"],
        base64.b64decode(documento["sal"]),
        base64.b64decode(documento["nonce"]),
        base64.b64decode(documento["cifrado"]),
    )
    assert descifrar(guardado, CLAVE, documento["huella"]) == privada


def test_la_clave_publica_propia_se_exporta_con_los_datos_de_la_empresa(con_empresa) -> None:
    clave = empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    leida = firma.leer_clave_publica(empresas.exportar_clave_publica_propia(con_empresa, AHORA))
    assert (leida.nombre, leida.rif, leida.publica) == (
        "Contratista Demo, C.A.",
        "J-00000000-0",
        clave.publica,
    )
    assert leida.huella_coincide


def test_la_privada_abierta_firma_y_la_publica_registrada_verifica(con_empresa) -> None:
    clave = empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    privada = empresas.abrir_privada(con_empresa, CLAVE)
    manifiesto = b'{"paquete":"PQ-1"}'
    hecha = firma.firmar(privada, firma.DOMINIO_PAQUETE, manifiesto)
    assert firma.verificar(clave.publica, firma.DOMINIO_PAQUETE, manifiesto, hecha)


def test_ningun_secreto_queda_en_el_registro_de_accesos(con_empresa, caplog) -> None:
    caplog.set_level("DEBUG")
    empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    privada = empresas.abrir_privada(con_empresa, CLAVE)
    aviso = empresas.revocar_clave_propia(con_empresa, "ana", AHORA, "robo", CLAVE)
    assert aviso is not None
    tipos = [e.tipo for e in con_empresa.query(EventoAcceso).order_by(EventoAcceso.id)]
    assert tipos == ["empresa", "alta de clave", "revocacion"]
    for evento in con_empresa.query(EventoAcceso):
        texto = " ".join([evento.detalle, evento.login_intentado]).encode()
        assert CLAVE.encode() not in texto
        assert not any(forma in texto for forma in _formas(privada))
    assert CLAVE not in caplog.text and privada.hex() not in caplog.text


# --- solo desde el propio equipo (RV-15) ------------------------------------------------------


@pytest.mark.parametrize(
    "ip,direccion",
    [
        ("127.0.0.1", ""),
        ("::1", ""),
        ("127.0.0.1", "192.168.1.20"),
        ("192.168.1.20", "192.168.1.20"),
    ],
)
def test_el_propio_equipo_puede_gestionar_la_clave(ip: str, direccion: str) -> None:
    empresas.exigir_equipo_propio(ip, direccion)  # no lanza


@pytest.mark.parametrize(
    "ip,direccion",
    [
        (None, ""),
        ("", ""),
        ("192.168.1.20", ""),
        ("192.168.1.21", "192.168.1.20"),
        ("0.0.0.0", "0.0.0.0"),
        ("no es ip", ""),
    ],
)
def test_otra_maquina_no_gestiona_la_clave(ip, direccion: str) -> None:
    with pytest.raises(empresas.ClaveError, match="propio equipo"):
        empresas.exigir_equipo_propio(ip, direccion)


# --- empresas ajenas ------------------------------------------------------------------------


def test_registrar_una_ajena_exige_la_huella_leida_y_con_quien_se_comprobo(con_empresa) -> None:
    archivo, par = _archivo_ajeno()
    corta = firma.huella_corta(par.publica)
    with pytest.raises(empresas.HuellaNoCoincide, match="No se registró nada"):
        empresas.registrar_empresa_ajena(
            con_empresa, archivo, "AAAA-AAAA-AAAA-AAAA-AAAA", "Pedro", "telefono", "ana", AHORA
        )
    with pytest.raises(empresas.ClaveError, match="con quién"):
        empresas.registrar_empresa_ajena(con_empresa, archivo, corta, " ", "telefono", "ana", AHORA)
    with pytest.raises(empresas.ClaveError, match="cómo se comprobó"):
        empresas.registrar_empresa_ajena(
            con_empresa, archivo, corta, "Pedro", "carta", "ana", AHORA
        )
    with pytest.raises(empresas.HuellaNoCoincide):  # una huella mal escrita tampoco registra
        empresas.registrar_empresa_ajena(
            con_empresa, archivo, "no es una huella", "Pedro", "telefono", "ana", AHORA
        )
    assert con_empresa.query(EmpresaRegistrada).count() == 0
    fila = empresas.registrar_empresa_ajena(
        con_empresa, archivo, corta.lower(), "Pedro, gerente", "telefono", "ana", AHORA
    )
    assert (fila.estado, fila.publica, fila.huella) == (
        "activa",
        par.publica,
        firma.huella_completa(par.publica),
    )
    assert (fila.empresa, fila.rif, fila.comprobada_con, fila.metodo) == (
        "Otra Empresa, C.A.",
        "J-11111111-1",
        "Pedro, gerente",
        "telefono",
    )
    assert fila.fecha_comprobacion == AHORA and fila.registrada_por == "ana"
    with pytest.raises(empresas.ClaveError, match="ya está registrada"):
        empresas.registrar_empresa_ajena(con_empresa, archivo, corta, "Pedro", "qr", "ana", AHORA)
    assert con_empresa.query(EmpresaRegistrada).count() == 1


@pytest.mark.parametrize("metodo", ["telefono", "en persona", "qr"])
def test_los_tres_metodos_del_spec_registran(con_empresa, metodo: str) -> None:
    archivo, par = _archivo_ajeno()
    fila = empresas.registrar_empresa_ajena(
        con_empresa, archivo, firma.huella_corta(par.publica), "Pedro", metodo, "ana", AHORA
    )
    assert fila.metodo == metodo


def test_la_huella_declarada_en_el_archivo_no_se_cree(con_empresa) -> None:
    archivo, par = _archivo_ajeno()
    otra = firma.generar_par()
    falso = archivo.replace(
        firma.huella_corta(par.publica).encode(), firma.huella_corta(otra.publica).encode()
    )
    # quien llama por teléfono lee la huella de la empresa REAL: la del archivo falso no coincide
    with pytest.raises(empresas.HuellaNoCoincide):
        empresas.registrar_empresa_ajena(
            con_empresa, falso, firma.huella_corta(otra.publica), "Pedro", "telefono", "ana", AHORA
        )
    assert con_empresa.query(EmpresaRegistrada).count() == 0


def test_la_propia_clave_no_se_registra_como_ajena(con_empresa) -> None:
    clave = empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    archivo = empresas.exportar_clave_publica_propia(con_empresa, AHORA)
    with pytest.raises(empresas.ClaveError, match="misma empresa"):
        empresas.registrar_empresa_ajena(
            con_empresa, archivo, firma.huella_corta(clave.publica), "yo", "qr", "ana", AHORA
        )
    assert con_empresa.query(EmpresaRegistrada).count() == 0


def test_dos_claves_con_la_misma_huella_corta_no_se_confunden(con_empresa) -> None:
    """La búsqueda interna usa la clave completa: aunque dos filas compartan la huella (la corta
    solo sirve por teléfono), cada clave pública encuentra la suya. Dos claves reales con los
    mismos 100 bits iniciales cuestan ~2^50 intentos: se fuerza la colisión en la columna."""
    uno, otro = firma.generar_par(), firma.generar_par()
    for nombre, par in (("Uno", uno), ("Otro", otro)):
        con_empresa.add(
            EmpresaRegistrada(
                empresa=nombre,
                rif="",
                publica=par.publica,
                huella="mismos-100-bits",
                estado="activa",
                comprobada_con="t",
                metodo="telefono",
                fecha_comprobacion=AHORA,
            )
        )
    con_empresa.commit()
    assert empresas.buscar_por_publica(con_empresa, uno.publica).empresa == "Uno"
    assert empresas.buscar_por_publica(con_empresa, otro.publica).empresa == "Otro"
    assert empresas.buscar_por_publica(con_empresa, firma.generar_par().publica) is None


def test_retiro_y_revocacion_ajenos(con_empresa) -> None:
    archivo, par = _archivo_ajeno()
    fila = empresas.registrar_empresa_ajena(
        con_empresa, archivo, firma.huella_corta(par.publica), "Pedro", "telefono", "ana", AHORA
    )
    retiro = AHORA + timedelta(days=2)
    retirada = empresas.retirar_ajena(con_empresa, fila.id, retiro, "ana", AHORA)
    assert (retirada.estado, retirada.fecha_estado) == ("retirada", retiro)
    falso = firma.crear_aviso_revocacion(firma.generar_par().privada, "x", AHORA)
    with pytest.raises(empresas.ClaveError, match="no es válido"):
        empresas.revocar_ajena(con_empresa, fila.id, "", "ana", AHORA, aviso=falso)
    assert con_empresa.get(EmpresaRegistrada, fila.id).estado == "retirada"  # no cambió
    bueno = firma.crear_aviso_revocacion(par.privada, "robo", AHORA)
    revocada = empresas.revocar_ajena(con_empresa, fila.id, "", "ana", AHORA, aviso=bueno)
    assert (revocada.estado, revocada.motivo) == ("revocada", "robo")


def test_un_aviso_ajeno_manipulado_o_de_dominio_de_paquete_no_revoca(con_empresa) -> None:
    archivo, par = _archivo_ajeno()
    fila = empresas.registrar_empresa_ajena(
        con_empresa, archivo, firma.huella_corta(par.publica), "Pedro", "qr", "ana", AHORA
    )
    aviso = firma.crear_aviso_revocacion(par.privada, "robo", AHORA)
    manipulado = aviso.replace(b"robo", b"rob0")
    with pytest.raises(empresas.ClaveError, match="no es válido"):
        empresas.revocar_ajena(con_empresa, fila.id, "", "ana", AHORA, aviso=manipulado)
    documento = json.loads(aviso)
    del documento["firma"]
    canonico = json.dumps(documento, sort_keys=True, separators=(",", ":")).encode()
    de_paquete = firma.firmar(par.privada, firma.DOMINIO_PAQUETE, canonico)
    documento["firma"] = base64.b64encode(de_paquete).decode()
    with pytest.raises(empresas.ClaveError, match="no es válido"):
        empresas.revocar_ajena(
            con_empresa, fila.id, "", "ana", AHORA, aviso=json.dumps(documento).encode()
        )
    assert con_empresa.get(EmpresaRegistrada, fila.id).estado == "activa"


def test_revocar_una_ajena_a_mano_con_el_motivo(con_empresa) -> None:
    archivo, par = _archivo_ajeno()
    fila = empresas.registrar_empresa_ajena(
        con_empresa, archivo, firma.huella_corta(par.publica), "Pedro", "qr", "ana", AHORA
    )
    despues = AHORA + timedelta(hours=1)
    revocada = empresas.revocar_ajena(con_empresa, fila.id, "llamó: le robaron", "ana", despues)
    assert (revocada.estado, revocada.motivo, revocada.fecha_estado) == (
        "revocada",
        "llamó: le robaron",
        despues,
    )
    # el motivo escrito a mano manda sobre el del aviso
    otra, otro_par = _archivo_ajeno("Tercera, C.A.")
    tercera = empresas.registrar_empresa_ajena(
        con_empresa, otra, firma.huella_corta(otro_par.publica), "Rosa", "qr", "ana", AHORA
    )
    aviso = firma.crear_aviso_revocacion(otro_par.privada, "del aviso", AHORA)
    con_aviso = empresas.revocar_ajena(con_empresa, tercera.id, "a mano", "ana", AHORA, aviso)
    assert con_aviso.motivo == "a mano"


def test_retirar_o_revocar_una_ajena_que_no_existe(con_empresa) -> None:
    with pytest.raises(empresas.ClaveError, match="No hay una empresa registrada"):
        empresas.retirar_ajena(con_empresa, 999, AHORA, "ana", AHORA)
    with pytest.raises(empresas.ClaveError, match="No hay una empresa registrada"):
        empresas.revocar_ajena(con_empresa, 999, "m", "ana", AHORA)
