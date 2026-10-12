"""Argon2id -> AES-GCM para secretos con contraseña (maestro §4.4, RV-13; spec S3 §7.1)."""

from __future__ import annotations

import pytest

from seguridad.secretos import (
    MINIMO_CLAVE,
    ContrasenaRechazada,
    InvalidTag,
    ParametrosKdf,
    cifrar,
    descifrar,
    exigir_contrasena_de_clave,
)

SECRETO = bytes(range(32))
HUELLA = "A" * 64
CONTRASENA = "una frase larga y propia 2026"


def test_ida_y_vuelta_con_la_contrasena_buena() -> None:
    guardado = cifrar(SECRETO, CONTRASENA, HUELLA)
    assert descifrar(guardado, CONTRASENA, HUELLA) == SECRETO
    assert SECRETO not in guardado.cifrado  # el secreto no queda en claro
    assert len(guardado.sal) == 16 and len(guardado.nonce) == 12


def test_una_contrasena_erronea_da_invalid_tag() -> None:
    guardado = cifrar(SECRETO, CONTRASENA, HUELLA)
    with pytest.raises(InvalidTag):
        descifrar(guardado, CONTRASENA + "x", HUELLA)


def test_el_dato_asociado_ata_el_cifrado_a_su_huella() -> None:
    guardado = cifrar(SECRETO, CONTRASENA, HUELLA)
    with pytest.raises(InvalidTag):
        descifrar(guardado, CONTRASENA, "B" * 64)


def test_sal_y_nonce_cambian_en_cada_cifrado() -> None:
    uno, otro = cifrar(SECRETO, CONTRASENA, HUELLA), cifrar(SECRETO, CONTRASENA, HUELLA)
    assert (uno.sal, uno.nonce, uno.cifrado) != (otro.sal, otro.nonce, otro.cifrado)


def test_los_parametros_se_guardan_y_son_los_minimos_del_spec() -> None:
    guardado = cifrar(SECRETO, CONTRASENA, HUELLA)
    assert ParametrosKdf.de_json(guardado.kdf) == ParametrosKdf(65536, 3, 4)


@pytest.mark.parametrize("memoria,pasadas", [(65535, 3), (65536, 2), (1024, 1)])
def test_parametros_por_debajo_del_minimo_no_se_aceptan(memoria: int, pasadas: int) -> None:
    with pytest.raises(ValueError, match="minimo"):
        ParametrosKdf(memoria, pasadas, 4)


def test_el_kdf_guardado_manda_al_descifrar() -> None:
    fuerte = cifrar(SECRETO, CONTRASENA, HUELLA, ParametrosKdf(131072, 4, 2))
    assert ParametrosKdf.de_json(fuerte.kdf).memoria_kib == 131072
    assert descifrar(fuerte, CONTRASENA, HUELLA) == SECRETO


def test_contrasena_de_clave_corta_o_comun_se_rechaza() -> None:
    with pytest.raises(ContrasenaRechazada, match=str(MINIMO_CLAVE)):
        exigir_contrasena_de_clave("a" * (MINIMO_CLAVE - 1))
    exigir_contrasena_de_clave("a" * MINIMO_CLAVE + "b")  # 13: pasa
    for comun in ("123456789012", "  Administrador  ", "QWERTYUIOPAS"):
        with pytest.raises(ContrasenaRechazada, match="demasiado"):
            exigir_contrasena_de_clave(comun)
    with pytest.raises(ContrasenaRechazada):
        exigir_contrasena_de_clave("x" * 129)
