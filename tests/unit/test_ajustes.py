"""`silice.toml`: valores por defecto y archivo dañado (RF-98; spec S5 §8.1).

Los valores esperados son literales del spec (8501, 8000, `INFO`, red y API apagadas); ninguno se
lee de `Ajustes()` para comparar consigo mismo, salvo la igualdad de «sin archivo» con los
defectos, que es justo lo que se exige.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from operacion.config import Ajustes, cargar_ajustes, guardar_ajustes


def _escribir(ruta: Path, texto: str) -> Path:
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def test_los_valores_por_defecto_apagan_la_red_y_la_api(tmp_path: Path) -> None:
    ajustes = cargar_ajustes(tmp_path / "no_existe.toml")
    assert ajustes == Ajustes()
    assert (ajustes.red_local, ajustes.api_activa, ajustes.mostrar_investigacion) == (False,) * 3
    assert (ajustes.puerto, ajustes.puerto_api, ajustes.nivel_registro) == (8501, 8000, "INFO")
    assert ajustes.direccion == "" and ajustes.avisos == ()
    assert not (tmp_path / "no_existe.toml").exists()  # leer no crea el archivo


def test_un_archivo_vacio_da_los_defectos_sin_avisos(tmp_path: Path) -> None:
    assert cargar_ajustes(_escribir(tmp_path / "silice.toml", "")) == Ajustes()


def test_guardar_y_volver_a_leer_da_lo_mismo(tmp_path: Path) -> None:
    ruta = tmp_path / "config" / "silice.toml"
    esperados = Ajustes(
        puerto=8600,
        red_local=True,
        direccion="192.168.1.20",
        api_activa=True,
        puerto_api=8010,
        mostrar_investigacion=True,
        nivel_registro="WARNING",
    )
    guardar_ajustes(ruta, esperados)
    assert cargar_ajustes(ruta) == esperados


def test_lo_guardado_nunca_lleva_los_avisos(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    guardar_ajustes(ruta, Ajustes(avisos=("un aviso que no es un ajuste",)))
    assert "un aviso" not in ruta.read_text(encoding="utf-8")
    assert cargar_ajustes(ruta) == Ajustes()


@pytest.mark.parametrize(
    "texto",
    [
        "[servidor\npuerto = 8501",
        "\x00\x01 no es toml",
        'puerto = "sin tabla" ===',
        "[servidor]\nred_local = ",
        "[servidor]\nred_local = true\nred_local = true\n",  # clave repetida
    ],
)
def test_un_archivo_danado_da_defectos_y_nunca_red_encendida(tmp_path: Path, texto: str) -> None:
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", texto))
    assert ajustes.red_local is False and ajustes.api_activa is False
    assert ajustes.direccion == "" and len(ajustes.avisos) == 1
    assert "valores por defecto" in ajustes.avisos[0]
    assert replace(ajustes, avisos=()) == Ajustes()


def test_un_archivo_que_no_es_utf8_tambien_es_danado(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    ruta.write_bytes(b"[servidor]\nred_local = true\n\xff\xfe")
    ajustes = cargar_ajustes(ruta)
    assert ajustes.red_local is False and len(ajustes.avisos) == 1


@pytest.mark.parametrize(
    "direccion",
    [
        "",
        "0.0.0.0",
        "::",
        "8.8.8.8",
        "no-es-ip",
        "224.0.0.1",
        "127.0.0.1",
        "169.254.3.4",
        "fd00::1",
    ],
)
def test_red_local_con_direccion_invalida_se_apaga_y_avisa(tmp_path: Path, direccion: str) -> None:
    ruta = _escribir(
        tmp_path / "silice.toml", f'[servidor]\nred_local = true\ndireccion = "{direccion}"\n'
    )
    ajustes = cargar_ajustes(ruta)
    assert ajustes.red_local is False and ajustes.direccion == ""
    assert len(ajustes.avisos) == 1 and "dirección" in ajustes.avisos[0]


def test_una_direccion_que_no_es_texto_tambien_apaga_la_red(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path / "silice.toml", "[servidor]\nred_local = true\ndireccion = 10\n")
    ajustes = cargar_ajustes(ruta)
    assert ajustes.red_local is False and ajustes.direccion == "" and len(ajustes.avisos) == 1


@pytest.mark.parametrize(
    "direccion", ["192.168.1.20", "10.0.0.5", "172.16.4.9", "172.31.255.254", "10.255.255.254"]
)
def test_red_local_con_ip_privada_se_acepta(tmp_path: Path, direccion: str) -> None:
    ruta = _escribir(
        tmp_path / "silice.toml", f'[servidor]\nred_local = true\ndireccion = "{direccion}"\n'
    )
    ajustes = cargar_ajustes(ruta)
    assert ajustes.red_local is True and ajustes.direccion == direccion and ajustes.avisos == ()


@pytest.mark.parametrize("direccion", ["172.15.255.255", "172.32.0.1", "11.0.0.1"])
def test_las_fronteras_de_los_rangos_privados_se_rechazan(tmp_path: Path, direccion: str) -> None:
    ruta = _escribir(
        tmp_path / "silice.toml", f'[servidor]\nred_local = true\ndireccion = "{direccion}"\n'
    )
    assert cargar_ajustes(ruta).red_local is False


def test_con_la_red_apagada_la_direccion_guardada_se_descarta(tmp_path: Path) -> None:
    ruta = _escribir(
        tmp_path / "silice.toml", '[servidor]\nred_local = false\ndireccion = "192.168.1.20"\n'
    )
    ajustes = cargar_ajustes(ruta)
    assert ajustes.red_local is False and ajustes.direccion == "" and ajustes.avisos == ()


@pytest.mark.parametrize(
    "puerto", ["80", "1023", "65536", "70000", '"8501"', "true", "-1", "8501.5"]
)
def test_un_puerto_invalido_vuelve_al_defecto_y_avisa(tmp_path: Path, puerto: str) -> None:
    ajustes = cargar_ajustes(
        _escribir(tmp_path / "silice.toml", f"[servidor]\npuerto = {puerto}\n")
    )
    assert ajustes.puerto == 8501 and len(ajustes.avisos) == 1 and "puerto" in ajustes.avisos[0]


@pytest.mark.parametrize("puerto", [1024, 8600, 65535])
def test_los_puertos_frontera_validos_se_aceptan(tmp_path: Path, puerto: int) -> None:
    ajustes = cargar_ajustes(
        _escribir(tmp_path / "silice.toml", f"[servidor]\npuerto = {puerto}\n")
    )
    assert ajustes.puerto == puerto and ajustes.avisos == ()


def test_el_puerto_de_la_api_invalido_vuelve_a_8000(tmp_path: Path) -> None:
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", "[api]\npuerto = 1023\n"))
    assert ajustes.puerto_api == 8000 and len(ajustes.avisos) == 1


def test_los_dos_puertos_iguales_se_corrigen(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path / "silice.toml", "[servidor]\npuerto = 8600\n[api]\npuerto = 8600\n")
    ajustes = cargar_ajustes(ruta)
    assert ajustes.puerto == 8600 and ajustes.puerto_api == 8000
    assert len(ajustes.avisos) == 1 and "mismo puerto" in ajustes.avisos[0]


def test_la_interfaz_en_8000_aparta_la_api_al_8001(tmp_path: Path) -> None:
    """Frontera: la interfaz en 8000 y la API sin puerto (8000 por defecto). La API no puede
    «volver» a 8000, que es el mismo: pasa al 8001 (hallazgo de la auditoría final)."""
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", "[servidor]\npuerto = 8000\n"))
    assert (ajustes.puerto, ajustes.puerto_api) == (8000, 8001)
    assert len(ajustes.avisos) == 1 and "8001" in ajustes.avisos[0]


def test_la_interfaz_en_8001_deja_la_api_en_8000_sin_aviso(tmp_path: Path) -> None:
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", "[servidor]\npuerto = 8001\n"))
    assert (ajustes.puerto, ajustes.puerto_api, ajustes.avisos) == (8001, 8000, ())


@pytest.mark.parametrize("nivel", ["ruido", "CRITICAL", "5"])
def test_un_nivel_desconocido_vuelve_a_info(tmp_path: Path, nivel: str) -> None:
    texto = f'[registro]\nnivel = "{nivel}"\n' if nivel != "5" else "[registro]\nnivel = 5\n"
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", texto))
    assert ajustes.nivel_registro == "INFO" and len(ajustes.avisos) == 1


def test_el_nivel_en_minusculas_se_normaliza(tmp_path: Path) -> None:
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", '[registro]\nnivel = "debug"\n'))
    assert ajustes.nivel_registro == "DEBUG" and ajustes.avisos == ()


def test_las_claves_con_tipo_equivocado_no_encienden_nada(tmp_path: Path) -> None:
    ruta = _escribir(
        tmp_path / "silice.toml",
        '[servidor]\nred_local = "true"\n[api]\nactiva = 1\n'
        '[interfaz]\nmostrar_investigacion = "si"\n',
    )
    ajustes = cargar_ajustes(ruta)
    assert (ajustes.red_local, ajustes.api_activa, ajustes.mostrar_investigacion) == (False,) * 3
    assert len(ajustes.avisos) == 3


def test_una_tabla_que_no_es_tabla_se_ignora(tmp_path: Path) -> None:
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", "servidor = 5\napi = true\n"))
    assert replace(ajustes, avisos=()) == Ajustes()


def test_guardar_no_deja_un_archivo_a_medias(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    guardar_ajustes(ruta, replace(Ajustes(), puerto=8700))
    assert [p.name for p in tmp_path.iterdir()] == ["silice.toml"]
    guardar_ajustes(ruta, replace(Ajustes(), puerto=8701))  # pisar uno existente
    assert [p.name for p in tmp_path.iterdir()] == ["silice.toml"]
    assert cargar_ajustes(ruta).puerto == 8701
