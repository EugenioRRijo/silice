"""Carpetas de datos de Sílice (maestro §4.2; spec S5 §5.3). Ninguna función crea carpetas."""

from __future__ import annotations

from pathlib import Path

from operacion import config


def test_sin_variables_la_carpeta_de_datos_es_data_del_repositorio() -> None:
    raiz = Path(config.__file__).resolve().parents[1]
    assert config.carpeta_datos({}) == raiz / "data"
    assert config.carpeta_casos({}) == raiz / "data" / "casos"
    assert config.ruta_instalacion({}) == raiz / "data" / "instalacion.db"
    assert config.carpeta_respaldos({}) == raiz / "data" / "respaldos"
    assert config.ruta_caso_por_defecto({}) == raiz / "data" / "casos" / "silice.db"
    assert config.BASE_ANTERIOR == raiz / "data" / "apu.db"


def test_silice_datos_mueve_todo_y_no_crea_nada(tmp_path: Path) -> None:
    datos = tmp_path / "OneDrive - Personal" / "Tésis ñ" / "datos"
    entorno = {config.VARIABLE_DATOS: str(datos)}
    assert config.carpeta_casos(entorno) == datos.resolve() / "casos"
    assert config.ruta_instalacion(entorno) == datos.resolve() / "instalacion.db"
    assert config.carpeta_respaldos(entorno) == datos.resolve() / "respaldos"
    assert config.ruta_caso_por_defecto(entorno) == datos.resolve() / "casos" / "silice.db"
    assert not datos.exists()


def test_silice_instalacion_y_silice_respaldos_mandan_sobre_la_carpeta(tmp_path: Path) -> None:
    entorno = {
        config.VARIABLE_DATOS: str(tmp_path / "datos"),
        config.VARIABLE_INSTALACION: str(tmp_path / "otra" / "inst.db"),
        config.VARIABLE_RESPALDOS: str(tmp_path / "resp"),
    }
    assert config.ruta_instalacion(entorno) == (tmp_path / "otra" / "inst.db").resolve()
    assert config.carpeta_respaldos(entorno) == (tmp_path / "resp").resolve()


def test_una_variable_vacia_no_cuenta() -> None:
    assert config.carpeta_datos({config.VARIABLE_DATOS: "   "}) == config.DATOS_DESARROLLO


def test_sin_entorno_explicito_lee_os_environ(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(config.VARIABLE_DATOS, str(tmp_path))
    assert config.carpeta_datos() == tmp_path.resolve()


def test_las_pruebas_corren_con_una_carpeta_de_datos_temporal() -> None:
    """La fixture autouse de tests/conftest.py: nada llega a data/casos ni a data/respaldos."""
    assert config.carpeta_datos() != config.DATOS_DESARROLLO
