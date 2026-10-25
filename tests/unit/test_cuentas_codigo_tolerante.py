"""El código de instalación se acepta como lo escribe o lo pega una persona (caso real, 2026-10-25).

Una persona de la empresa no pudo crear el primer administrador. Dos de las causas estaban en cómo
se lee lo que escribe:

- el alfabeto del código es base32 (`A-Z` y `2-7`): no tiene `0`, `1`, `8` ni `9`. Quien copia a
  mano escribe `0` por `O`, `1` por `I` y `8` por `B`. Como esas cifras **nunca** salen en un
  código, leerlas como su letra es inequívoco y no cambia el espacio de códigos (32^20 = 2^100);
- quien pega la línea entera de la consola («Código de instalación (un solo uso, …): XXXX-…»)
  metía las letras del prefijo en la huella.

Oráculos a mano: el código sembrado es un literal; su huella se calcula aquí con `hashlib` sobre
ese literal (no con la función bajo prueba); las variantes escritas son literales. No se traducen
`l`/`L` (la `L` es una letra válida) ni el `9` (no se parece a ninguna letra del alfabeto).
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from seguridad import cuentas
from seguridad.modelo import CodigoInstalacion, EventoAcceso, IntentoAcceso
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, instalacion

#: Un código con B, O e I (las letras que se confunden con 8, 0 y 1) y un L.
CODIGO = "BOIAQRSTIOBUVWXYZL34"
CON_GUIONES = "BOIA-QRST-IOBU-VWXY-ZL34"
LINEA_DE_LA_CONSOLA = (
    "Código de instalación (un solo uso, para crear el primer administrador): " + CON_GUIONES
)


@pytest.fixture
def freno() -> cuentas.FrenoGlobal:
    return cuentas.FrenoGlobal()


def _sembrar(sesion, codigo: str = CODIGO, motivo: str = "primera vez") -> None:
    sesion.add(
        CodigoInstalacion(
            huella=hashlib.sha256(codigo.encode("ascii")).hexdigest(), creado=AHORA, motivo=motivo
        )
    )
    sesion.commit()


def _reclamar(sesion, texto: str, carpeta: Path, freno, login: str = "dueno"):
    return cuentas.reclamar_instalacion(
        sesion, texto, login, "Dueña Demo", CONTRASENA, AHORA, carpeta, freno=freno
    )


def _fallos(sesion) -> int:
    fila = sesion.get(IntentoAcceso, cuentas.CLAVE_INTENTOS_CODIGO)
    return 0 if fila is None else fila.fallos_seguidos


@pytest.mark.parametrize(
    "escrito",
    [
        "8O1A-QRST-1O8U-VWXY-ZL34",  # 8 por B, 1 por I
        "B01A-QRST-I0BU-VWXY-ZL34",  # 0 por O
        "801A-QRST-108U-VWXY-ZL34",  # todas a la vez
        "801a qrst 108u vwxy zl34",  # y en minúsculas con espacios
    ],
)
def test_las_cifras_que_no_estan_en_el_alfabeto_se_leen_como_su_letra(
    tmp_path: Path, freno, escrito: str
) -> None:
    with instalacion(tmp_path) as sesion:
        _sembrar(sesion)
        assert _reclamar(sesion, escrito, tmp_path, freno).login == "dueno"


@pytest.mark.parametrize(
    "escrito",
    [
        "boia qrst iobu vwxy zl34",
        "  BOIA QRST  IOBU VWXY ZL34 \n",
        "boiaqrstiobuvwxyzl34",
        "BOIA–QRST–IOBU–VWXY–ZL34",  # guion largo (lo pone un procesador de texto)
    ],
)
def test_minusculas_espacios_y_guiones_se_aceptan(tmp_path: Path, freno, escrito: str) -> None:
    with instalacion(tmp_path) as sesion:
        _sembrar(sesion)
        assert _reclamar(sesion, escrito, tmp_path, freno).login == "dueno"


@pytest.mark.parametrize(
    "escrito",
    [
        LINEA_DE_LA_CONSOLA,
        LINEA_DE_LA_CONSOLA + "\r\n",
        "Código: " + CON_GUIONES.lower() + " (copiado del Bloc de notas)",
        "Código " + CON_GUIONES + " HOLA",  # palabras de cuatro letras alrededor
        "CODE " + CON_GUIONES,
        LINEA_DE_LA_CONSOLA.replace("BOIA", "8O1A"),  # la línea entera, y además con cifras
    ],
)
def test_la_linea_entera_de_la_consola_pegada_se_acepta(
    tmp_path: Path, freno, escrito: str
) -> None:
    with instalacion(tmp_path) as sesion:
        _sembrar(sesion)
        assert _reclamar(sesion, escrito, tmp_path, freno).login == "dueno"


@pytest.mark.parametrize(
    "escrito",
    [
        "BOIA-QRST-IOBU-VWXY-Z134",  # la L escrita como 1 se lee I: no es L
        "BOlA-QRST-IOBU-VWXY-ZL34",  # la I escrita como l (ele) se lee L: no se traduce
        "BOIA-QRST-IOBU-VWXY-ZL39",  # el 9 no se traduce
        "BOIA-QRST-IOBU-VWXY-ZL35",  # un carácter cambiado
        # dos grupos con forma de código: no se adivina cuál es y se lee todo junto
        CON_GUIONES + " " + "AAAA-BBBB-CCCC-DDDD-EEEE",
        "BOIA QRST IOBU VWXY ZL34 AAAA BBBB CCCC DDDD EEEE",
    ],
)
def test_un_codigo_realmente_errado_sigue_siendo_el_mismo_error_y_cuenta(
    tmp_path: Path, freno, escrito: str
) -> None:
    with instalacion(tmp_path) as sesion:
        _sembrar(sesion)
        with pytest.raises(cuentas.ErrorDeAcceso) as error:
            _reclamar(sesion, escrito, tmp_path, freno)
        assert type(error.value) is cuentas.ErrorDeAcceso
        assert str(error.value) == "El código de instalación no es válido o ya se usó."
        assert _fallos(sesion) == 1  # cuenta para el bloqueo de 5, como cualquier código errado


def test_cinco_variantes_erradas_bloquean_igual_que_antes(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        _sembrar(sesion)
        for _ in range(4):
            with pytest.raises(cuentas.ErrorDeAcceso):
                _reclamar(sesion, "8O1A-QRST-1O8U-VWXY-ZL35", tmp_path, freno)
        with pytest.raises(cuentas.CuentaBloqueada):
            _reclamar(sesion, LINEA_DE_LA_CONSOLA.replace("ZL34", "ZL35"), tmp_path, freno)
        with pytest.raises(cuentas.CuentaBloqueada):  # el bueno, ya bloqueado
            _reclamar(sesion, LINEA_DE_LA_CONSOLA, tmp_path, freno)


def test_el_codigo_de_restablecimiento_se_lee_igual(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        _sembrar(sesion, motivo="restablecimiento")
        usuario = _reclamar(sesion, "801a-qrst-108u-vwxy-zl34", tmp_path, freno, login="admin")
        assert usuario.login == "admin"
        with pytest.raises(cuentas.ErrorDeAcceso):  # de un solo uso, igual que antes
            _reclamar(sesion, CON_GUIONES, tmp_path, freno, login="admin")


def test_el_restablecimiento_caduca_igual_aunque_se_pegue_la_linea(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        _sembrar(sesion, motivo="restablecimiento")
        with pytest.raises(cuentas.ErrorDeAcceso):
            cuentas.reclamar_instalacion(
                sesion,
                LINEA_DE_LA_CONSOLA,
                "admin",
                "A",
                CONTRASENA,
                AHORA + timedelta(hours=24),
                tmp_path,
                freno=freno,
            )


def test_la_huella_de_un_codigo_emitido_no_cambia(tmp_path: Path) -> None:
    """Los códigos ya guardados siguen sirviendo: la huella de un código del alfabeto es la de
    siempre (SHA-256 del texto sin guiones), calculada aquí a mano."""
    with instalacion(tmp_path) as sesion:
        codigo = cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        [fila] = sesion.scalars(select(CodigoInstalacion)).all()
        assert fila.huella == hashlib.sha256(codigo.encode("ascii")).hexdigest()


def test_lo_escrito_no_queda_en_los_eventos(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        _sembrar(sesion)
        with pytest.raises(cuentas.ErrorDeAcceso):
            _reclamar(sesion, LINEA_DE_LA_CONSOLA.replace("ZL34", "ZL35"), tmp_path, freno)
        _reclamar(sesion, LINEA_DE_LA_CONSOLA, tmp_path, freno)
        for evento in sesion.scalars(select(EventoAcceso)):
            texto = f"{evento.login_intentado}{evento.detalle}"
            assert "QRST" not in texto and "ZL3" not in texto
