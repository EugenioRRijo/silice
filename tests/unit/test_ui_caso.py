"""El caso abierto de la interfaz (sprint de UI, RF-38, RF-39 y RF-40).

Toda base de este archivo vive en `tmp_path`; la salvaguarda de `tests/conftest.py` falla la
sesion si alguna toca `data/apu.db`.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from sqlalchemy import Engine, event

from core.catalog import abrir_sesion, crear_esquema, crear_motor
from operacion.config import ruta_caso_por_defecto
from scripts.seed import sembrar
from tests.fixtures.apu_linea_base import APUS_LINEA_BASE
from tests.fixtures.bases_prueba import crear_base_futura
from ui import caso as caso_ui
from ui.caso import (
    VARIABLE_RUTA_CASO,
    EstadoCaso,
    argv_siembra,
    estado_caso,
    resolver_ruta,
    resumen_caso,
)

RAIZ = Path(__file__).resolve().parents[2]


def _base_sembrada(ruta: Path) -> Path:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


# --- resolucion de la ruta (RF-38) ------------------------------------------------------------


def test_la_ruta_guardada_en_la_sesion_manda() -> None:
    entorno = {VARIABLE_RUTA_CASO: "entorno.db"}
    assert resolver_ruta("sesion.db", entorno, "defecto.db") == Path("sesion.db")


def test_sin_ruta_en_la_sesion_manda_la_variable_de_entorno() -> None:
    entorno = {VARIABLE_RUTA_CASO: "entorno.db"}
    assert resolver_ruta(None, entorno, "defecto.db") == Path("entorno.db")


def test_una_variable_de_entorno_vacia_no_cuenta() -> None:
    assert resolver_ruta(None, {VARIABLE_RUTA_CASO: "  "}, "defecto.db") == Path("defecto.db")


def test_sin_sesion_ni_entorno_queda_el_caso_por_defecto_de_la_carpeta_de_datos(
    tmp_path: Path,
) -> None:
    assert caso_ui.RUTA_BASE_POR_DEFECTO is None
    por_defecto = str(ruta_caso_por_defecto({"SILICE_DATOS": str(tmp_path)}))
    assert resolver_ruta(None, {}, por_defecto) == tmp_path.resolve() / "casos" / "silice.db"


# --- estado del caso (RF-39) ------------------------------------------------------------------


def test_estado_de_una_ruta_inexistente_no_crea_el_archivo(tmp_path: Path) -> None:
    ruta = tmp_path / "con_errata" / "apu.db"
    estado = estado_caso(ruta)
    assert estado == EstadoCaso(ruta=ruta, existe=False)
    assert estado.vacio
    assert not ruta.exists()
    assert not ruta.parent.exists()


def test_estado_de_una_base_vacia(tmp_path: Path) -> None:
    ruta = tmp_path / "vacia.db"
    ruta.touch()
    estado = estado_caso(ruta)
    assert (estado.existe, estado.partidas, estado.insumos, estado.lista_vigente) == (
        True,
        0,
        0,
        None,
    )
    assert estado.error is None
    assert estado.vacio


def test_estado_de_una_base_sembrada(tmp_path: Path) -> None:
    estado = estado_caso(_base_sembrada(tmp_path / "sembrada.db"))
    assert estado.existe and estado.error is None
    assert estado.partidas == len(APUS_LINEA_BASE)
    assert estado.insumos > 0
    assert estado.lista_vigente
    assert not estado.vacio


def test_estado_de_un_directorio_es_un_error_sin_traza(tmp_path: Path) -> None:
    estado = estado_caso(tmp_path)
    assert estado.existe
    assert estado.error
    assert not estado.vacio


def test_estado_de_un_archivo_que_no_es_sqlite_es_un_error_sin_traza(tmp_path: Path) -> None:
    ruta = tmp_path / "notas.db"
    ruta.write_text("esto no es una base de datos\n" * 20, encoding="utf-8")
    estado = estado_caso(ruta)
    assert estado.error
    assert ruta.read_text(encoding="utf-8").startswith("esto no es")


def test_resumen_de_cada_estado(tmp_path: Path) -> None:
    ruta = tmp_path / "x.db"
    assert resumen_caso(EstadoCaso(ruta, existe=False)) == "El archivo no existe todavia."
    assert (
        resumen_caso(EstadoCaso(ruta, existe=True, error="file is not a database"))
        == "No se pudo leer: file is not a database"
    )
    assert (
        resumen_caso(EstadoCaso(ruta, True, partidas=5, insumos=12, lista_vigente="Lista A"))
        == "5 partidas · 12 insumos · lista vigente: Lista A"
    )
    assert (
        resumen_caso(EstadoCaso(ruta, True, partidas=0, insumos=0))
        == "0 partidas · 0 insumos · lista vigente: ninguna"
    )


# --- la siembra no puede destruir (RF-40) -----------------------------------------------------


def test_la_siembra_apunta_al_caso_y_no_reinicia(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    argv = argv_siembra(ruta)
    assert argv == ["--db", str(ruta)]
    assert "--reiniciar" not in argv


def test_ningun_archivo_de_ui_contiene_el_flag_de_reinicio() -> None:
    con_flag = [
        archivo.relative_to(RAIZ).as_posix()
        for archivo in sorted((RAIZ / "ui").rglob("*.py"))
        if "--reiniciar" in archivo.read_text(encoding="utf-8")
    ]
    assert con_flag == []


def test_la_ruta_por_defecto_se_define_una_sola_vez_en_ui() -> None:
    definiciones = [
        archivo.relative_to(RAIZ).as_posix()
        for archivo in sorted((RAIZ / "ui").rglob("*.py"))
        if re.search(r"^RUTA_BASE_POR_DEFECTO\s*=", archivo.read_text(encoding="utf-8"), re.M)
    ]
    assert definiciones == ["ui/caso.py"]


# --- estado sin DDL y bases que no están en head (RV-5) ---------------------------------------


def test_estado_caso_no_emite_ddl_ni_cambia_el_archivo(tmp_path: Path) -> None:
    ruta = _base_sembrada(tmp_path / "sembrada.db")
    antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
    sentencias: list[str] = []

    def anotar(_conexion, _cursor, sentencia, *_resto) -> None:
        sentencias.append(sentencia)

    event.listen(Engine, "before_cursor_execute", anotar)
    try:
        estado = estado_caso(ruta)
    finally:
        event.remove(Engine, "before_cursor_execute", anotar)
    assert estado.partidas == len(APUS_LINEA_BASE) and estado.por_migrar
    primeras = {s.lstrip().split(" ", 1)[0].upper() for s in sentencias}
    assert sentencias and not primeras & {"CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE"}
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == antes


def test_estado_de_una_base_mas_nueva_es_un_error_con_mensaje(tmp_path: Path) -> None:
    estado = estado_caso(crear_base_futura(tmp_path / "futura.db"))
    assert estado.error and "versión más nueva" in estado.error


def test_el_resumen_avisa_que_el_caso_se_actualizara(tmp_path: Path) -> None:
    estado = EstadoCaso(tmp_path / "x.db", True, partidas=1, insumos=2, por_migrar=True)
    assert resumen_caso(estado).endswith("se actualizara al abrirlo")
