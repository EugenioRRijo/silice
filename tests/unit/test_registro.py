"""Registro de errores sin secretos (RF-98; spec S5 §8.4).

Cada secreto se siembra con un valor escrito a mano y se busca un fragmento suyo en el archivo
real (`silice.log`), no en la salida de `limpiar`: el oráculo es el texto que llega al disco.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from operacion import registro

#: Cada valor sembrado y el fragmento que no puede llegar al archivo.
SEMBRADOS = {
    "clave de IA": ("sk-ant-api03-ZXCVBNM1234567890", "sk-ant-api03"),
    "bearer": ("Bearer eyJhbGciOiJIUzI1NiJ9.cuerpo.firma", "eyJhbGci"),
    "cabecera de la API": ("X-Silice-Clave: AB12CD34.s3cretoDeClaveDeApi", "s3cretoDeClave"),
    "contraseña": ("contraseña=Tr0ub4dor&3xyz", "Tr0ub4dor"),
    "password": ("password: 'hunter2-largo'", "hunter2"),
    "token": ("token=abcdef0123456789", "abcdef0123"),
    "PEM": (
        "-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEIA\n-----END PRIVATE KEY-----",
        "MC4CAQAw",
    ),
    "consulta": ("GET http://127.0.0.1:8501/x?token=abc123def", "abc123def"),
    "codigo de instalacion": ("codigo_de_instalacion=K7QFM9XRA2PTW4HN", "K7QFM9XRA2"),
}


def _cerrar(logger: logging.Logger) -> None:
    for manejador in list(logger.handlers):
        logger.removeHandler(manejador)
        manejador.close()


@pytest.fixture
def registro_en(tmp_path: Path) -> Iterator[tuple[logging.Logger, Path]]:
    logger = registro.configurar(tmp_path / "registros")
    yield logger, tmp_path / "registros" / "silice.log"
    _cerrar(logger)
    registro.olvidar_secretos()


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


@pytest.mark.parametrize("nombre", SEMBRADOS)
def test_secretos_sembrados_no_llegan_al_archivo(registro_en, nombre: str) -> None:
    logger, archivo = registro_en
    valor, fragmento = SEMBRADOS[nombre]
    logger.error("algo falló con %s", valor)
    texto = _texto(archivo)
    assert fragmento not in texto
    assert registro.MARCA in texto


def test_el_formato_es_fecha_nivel_modulo_mensaje(registro_en) -> None:
    logger, archivo = registro_en
    logger.warning("aviso de prueba")
    (linea,) = _texto(archivo).splitlines()
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} WARNING silice aviso de prueba", linea
    ), linea


def test_un_mensaje_sin_secretos_llega_intacto(registro_en) -> None:
    logger, archivo = registro_en
    logger.error("la partida E-101 no tiene precio vigente (127.0.0.1:8501)")
    texto = _texto(archivo)
    assert "la partida E-101 no tiene precio vigente (127.0.0.1:8501)" in texto
    assert registro.MARCA not in texto


def test_una_excepcion_guarda_tipo_mensaje_y_lineas_sin_valores(registro_en) -> None:
    logger, archivo = registro_en
    try:
        raise ValueError("fallo con clave=sk-ant-api03-ZZZ y secreto=hunter2xyz")
    except ValueError:
        logger.exception("no se pudo")
    texto = _texto(archivo)
    assert "ValueError" in texto and ".py:" in texto
    assert "sk-ant-api03" not in texto and "hunter2xyz" not in texto
    assert "raise ValueError" not in texto  # ni el texto de la línea de código


def test_el_perfil_del_usuario_se_reescribe() -> None:
    perfil = r"C:\Users\euger"
    assert registro.limpiar(r"abrió C:\Users\euger\x.db", perfil) == r"abrió %USERPROFILE%\x.db"
    assert registro.limpiar("abrió c:/users/euger/x.db", perfil) == "abrió %USERPROFILE%/x.db"
    assert registro.limpiar("abrió D:/otra/x.db", perfil) == "abrió D:/otra/x.db"


def test_el_codigo_de_instalacion_conocido_no_llega_al_archivo(registro_en) -> None:
    logger, archivo = registro_en
    registro.registrar_secreto("K7QFM9XRA2PTW4HNC8DV")
    logger.info("el código es K7QFM9XRA2PTW4HNC8DV, úselo una vez")
    texto = _texto(archivo)
    assert "K7QFM9XRA2PTW4HNC8DV" not in texto and registro.MARCA in texto


def test_un_secreto_conocido_de_menos_de_ocho_caracteres_no_se_registra() -> None:
    """Frontera de `registrar_secreto`: 7 caracteres no cuentan (borraría palabras comunes);
    8 sí."""
    try:
        registro.registrar_secreto("ABCDEFG")
        registro.registrar_secreto("12345678")
        assert registro.limpiar("x ABCDEFG y 12345678 z", "") == f"x ABCDEFG y {registro.MARCA} z"
        registro.olvidar_secretos()
        assert registro.limpiar("12345678", "") == "12345678"
    finally:
        registro.olvidar_secretos()


def test_la_salida_de_un_hijo_pasa_por_el_mismo_filtro(registro_en) -> None:
    logger, archivo = registro_en
    programa = (
        "import sys\n"
        "for l in ('Bearer ABC.def.ghi', '-----BEGIN PRIVATE KEY-----', 'MC4CAQAwBQYDK2Vw',"
        " '-----END PRIVATE KEY-----', 'listo'):\n"
        "    print(l, file=sys.stderr)\n"
    )
    hijo = subprocess.run(
        [sys.executable, "-c", programa], capture_output=True, text=True, check=True, timeout=60
    )
    contadas = registro.copiar_salida(hijo.stderr.splitlines(keepends=True), logger, origen="hijo")
    texto = _texto(archivo)
    assert contadas == 5 and "listo" in texto
    assert "ABC.def" not in texto and "MC4CAQAw" not in texto


def test_copiar_salida_cuenta_las_lineas_vacias_pero_no_las_escribe(registro_en) -> None:
    logger, archivo = registro_en
    assert registro.copiar_salida(["uno\n", "\n", "   \n", "dos\r\n"], logger, origen="h") == 4
    assert len(_texto(archivo).splitlines()) == 2


def test_el_archivo_rota_y_conserva_cinco_copias(tmp_path: Path) -> None:
    logger = registro.configurar(tmp_path, max_bytes=2000, copias=5)
    try:
        for i in range(400):
            logger.error("línea %03d %s", i, "x" * 80)
    finally:
        _cerrar(logger)
    nombres = sorted(p.name for p in tmp_path.iterdir())
    assert nombres == ["silice.log"] + [f"silice.log.{n}" for n in range(1, 6)]
    assert all(p.stat().st_size <= 2000 for p in tmp_path.iterdir())


def test_configurar_dos_veces_no_duplica_las_lineas(tmp_path: Path) -> None:
    registro.configurar(tmp_path)
    logger = registro.configurar(tmp_path)
    try:
        logger.error("una sola vez")
        assert len(logger.handlers) == 1 and logger.propagate is False
    finally:
        _cerrar(logger)
    assert _texto(tmp_path / "silice.log").count("una sola vez") == 1


@pytest.mark.parametrize("nivel", ["DEBUG", "INFO", "WARNING", "ERROR", "warning"])
def test_los_cuatro_niveles_se_aceptan(tmp_path: Path, nivel: str) -> None:
    logger = registro.configurar(tmp_path, nivel)
    try:
        assert logger.level == logging.getLevelName(nivel.upper())
    finally:
        _cerrar(logger)


@pytest.mark.parametrize("nivel", ["RUIDO", "CRITICAL", ""])
def test_un_nivel_desconocido_se_rechaza(tmp_path: Path, nivel: str) -> None:
    with pytest.raises(ValueError, match="nivel"):
        registro.configurar(tmp_path, nivel)
