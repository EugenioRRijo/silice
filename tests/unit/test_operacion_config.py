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


# --- Sílice 1.0.0, T5 (spec S5 §5.3): producto, carpeta del usuario y sus rutas ---------------


def test_en_desarrollo_el_usuario_es_data_y_no_es_producto() -> None:
    raiz = Path(config.__file__).resolve().parents[1]
    assert config.es_producto() is False
    assert config.carpeta_usuario({}) == raiz / "data"
    assert config.ruta_ajustes({}) == raiz / "data" / "config" / "silice.toml"


def test_hay_producto_si_el_manifiesto_esta_junto_al_codigo(tmp_path: Path) -> None:
    (tmp_path / "codigo").mkdir()
    assert config.es_producto(tmp_path / "codigo") is False
    (tmp_path / "manifiesto.json").mkdir()  # una carpeta con ese nombre no cuenta
    assert config.es_producto(tmp_path / "codigo") is False
    (tmp_path / "manifiesto.json").rmdir()
    (tmp_path / "manifiesto.json").write_text("{}", encoding="utf-8")
    assert config.es_producto(tmp_path / "codigo") is True


def test_en_el_producto_todo_vive_en_localappdata_silice(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "es_producto", lambda raiz=None: True)
    entorno = {"LOCALAPPDATA": str(tmp_path / "Local")}
    usuario = (tmp_path / "Local" / "Silice").resolve()
    assert config.carpeta_usuario(entorno) == usuario
    assert config.carpeta_datos(entorno) == usuario / "datos"
    assert config.carpeta_casos(entorno) == usuario / "datos" / "casos"
    assert config.ruta_instalacion(entorno) == usuario / "datos" / "instalacion.db"
    assert config.carpeta_respaldos(entorno) == usuario / "respaldos"
    assert config.ruta_ajustes(entorno) == usuario / "config" / "silice.toml"
    assert config.carpeta_registros(entorno) == usuario / "registros"
    assert config.ruta_estado(entorno) == usuario / "estado" / "servidor.json"
    assert config.ruta_codigo_instalacion(entorno) == usuario / "datos" / "codigo_instalacion.txt"
    assert not usuario.exists()


def test_silice_usuario_manda_sobre_localappdata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "es_producto", lambda raiz=None: True)
    entorno = {config.VARIABLE_USUARIO: str(tmp_path / "u"), "LOCALAPPDATA": str(tmp_path / "L")}
    assert config.carpeta_usuario(entorno) == (tmp_path / "u").resolve()
    assert config.ruta_estado(entorno) == (tmp_path / "u" / "estado" / "servidor.json").resolve()
    # SILICE_DATOS sigue mandando sobre la carpeta de datos del producto
    entorno[config.VARIABLE_DATOS] = str(tmp_path / "d")
    assert config.carpeta_datos(entorno) == (tmp_path / "d").resolve()
    assert config.carpeta_respaldos(entorno) == (tmp_path / "u" / "respaldos").resolve()
