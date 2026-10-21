"""`silice.toml`: valores por defecto y archivo dañado (RF-98; spec S5 §8.1).

Un solo proceso y un solo puerto (decisión de Eugenio, 2026-10-21): `[servidor] puerto` es el de
Uvicorn, que sirve la API y la interfaz; `[api] activa` y `[api] puerto` se ignoran con un aviso.
Los valores esperados son literales (8501, `INFO`, red apagada); ninguno se
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


def test_los_valores_por_defecto_apagan_la_red(tmp_path: Path) -> None:
    ajustes = cargar_ajustes(tmp_path / "no_existe.toml")
    assert ajustes == Ajustes()
    assert (ajustes.red_local, ajustes.mostrar_investigacion) == (False, False)
    assert (ajustes.puerto, ajustes.nivel_registro) == (8501, "INFO")
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
        mostrar_investigacion=True,
        nivel_registro="WARNING",
    )
    guardar_ajustes(ruta, esperados)
    assert cargar_ajustes(ruta) == esperados


def test_lo_guardado_ya_no_lleva_la_tabla_api(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    guardar_ajustes(ruta, Ajustes(puerto=8600))
    texto = ruta.read_text(encoding="utf-8")
    assert "[api]" not in texto and "activa" not in texto
    assert "[servidor]" in texto and "puerto = 8600" in texto


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
    assert ajustes.red_local is False
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


def test_la_tabla_api_de_un_silice_toml_viejo_se_ignora_con_un_aviso(tmp_path: Path) -> None:
    ruta = _escribir(
        tmp_path / "silice.toml", "[servidor]\npuerto = 8600\n[api]\nactiva = true\npuerto = 8010\n"
    )
    ajustes = cargar_ajustes(ruta)
    assert ajustes.puerto == 8600  # el único puerto es el de [servidor]
    assert len(ajustes.avisos) == 1 and "[api]" in ajustes.avisos[0]
    assert "8600" in ajustes.avisos[0]
    assert replace(ajustes, avisos=()) == Ajustes(puerto=8600)


def test_sin_la_tabla_api_no_hay_aviso(tmp_path: Path) -> None:
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", "[servidor]\npuerto = 8600\n"))
    assert ajustes.avisos == ()


def test_la_tabla_api_vacia_o_con_basura_tambien_se_ignora_sin_romper(tmp_path: Path) -> None:
    for texto in ("[api]\n", "[api]\nactiva = 1\npuerto = 1023\n", "api = true\n"):
        ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", texto))
        assert ajustes.puerto == 8501 and ajustes.red_local is False
        assert replace(ajustes, avisos=()) == Ajustes()


def test_los_puertos_de_la_api_siguen_leyendose_para_quien_los_consulta(tmp_path: Path) -> None:
    """`api/rutas/admin_instalacion.py` aún lee `api_activa` y `puerto_api`: describen la verdad
    nueva (la API siempre está activa y vive en el único puerto)."""
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", "[servidor]\npuerto = 8600\n"))
    assert ajustes.api_activa is True and ajustes.puerto_api == 8600


def test_el_puerto_8000_ya_no_choca_con_nada(tmp_path: Path) -> None:
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", "[servidor]\npuerto = 8000\n"))
    assert ajustes.puerto == 8000 and ajustes.avisos == ()


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
        '[servidor]\nred_local = "true"\n[interfaz]\nmostrar_investigacion = "si"\n',
    )
    ajustes = cargar_ajustes(ruta)
    assert (ajustes.red_local, ajustes.mostrar_investigacion) == (False, False)
    assert len(ajustes.avisos) == 2


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
