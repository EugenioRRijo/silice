"""«Solo desde el propio equipo» (`aplicacion/equipo.py`; RF-98; spec S5 §8.2).

Movidas desde `tests/unit/test_ui_cliente.py` (retiro de Streamlit, F3). Allí se probaba la lógica
a través de `ui.cliente`, que solo añadía cómo lee Streamlit la IP (`st.context.ip_address`) y
llamaba a `aplicacion.equipo` con ella. Aquí la IP se pasa directa: el criterio es el mismo
objeto (`ip_es_local`, `operacion_sensible_permitida`, `MENSAJE_REMOTO`, `MENSAJE_PENDIENTE`) y
cada prueba conserva su caso y su aserción; solo cambia el modo de dar la IP (antes
`monkeypatch.setattr(cliente, "ip_del_cliente", ...)`, ahora el argumento).
"""

from __future__ import annotations

import ast

import pytest

from aplicacion import equipo
from operacion import config
from tests.fixtures.arquitectura import archivos, ruta


@pytest.fixture
def con_red_local() -> None:
    config.guardar_ajustes(
        config.ruta_ajustes(), config.Ajustes(red_local=True, direccion="192.168.1.20")
    )


@pytest.mark.parametrize(
    ("ip", "esperado"),
    [
        ("127.0.0.1", True),
        ("::1", True),
        ("192.168.1.20", True),
        ("192.168.1.30", False),
        ("8.8.8.8", False),
    ],
)
def test_con_la_red_encendida_solo_cuentan_el_bucle_y_la_ip_elegida(
    con_red_local, ip: str, esperado: bool
) -> None:
    assert equipo.ip_es_local(ip) is esperado


def test_con_la_red_apagada_la_ip_guardada_no_cuenta_como_propia() -> None:
    """Con la red apagada nadie de la red llega; aun así, una IP que no es de bucle no es «el
    propio equipo» aunque coincida con una dirección vieja."""
    assert equipo.ip_es_local("192.168.1.20") is False


def test_si_no_se_puede_leer_la_ip_solo_es_local_con_la_red_apagada() -> None:
    assert equipo.ip_es_local(None) is True  # red apagada: solo el propio equipo puede llegar
    config.guardar_ajustes(
        config.ruta_ajustes(), config.Ajustes(red_local=True, direccion="192.168.1.20")
    )
    assert equipo.ip_es_local(None) is False


def test_un_silice_toml_danado_se_lee_con_la_red_apagada() -> None:
    ruta = config.ruta_ajustes()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("[servidor\nred_local = true", encoding="utf-8")
    assert equipo.ip_es_local(None) is True


def test_una_operacion_sensible_se_rechaza_desde_una_ip_remota(con_red_local) -> None:
    permitida, motivo = equipo.operacion_sensible_permitida("192.168.1.30")
    assert permitida is False and motivo == equipo.MENSAJE_REMOTO


def test_una_operacion_sensible_se_bloquea_con_eventos_sin_revisar() -> None:
    assert equipo.operacion_sensible_permitida("127.0.0.1") == (True, "")
    pendiente = config.carpeta_datos() / "eventos_perdidos_20261011-090000.json"
    pendiente.parent.mkdir(parents=True, exist_ok=True)
    pendiente.write_text('{"revisado": false}', encoding="utf-8")
    assert equipo.operacion_sensible_permitida("127.0.0.1") == (False, equipo.MENSAJE_PENDIENTE)


def test_remota_y_con_pendientes_manda_el_motivo_remoto(con_red_local) -> None:
    pendiente = config.carpeta_datos() / "eventos_perdidos_20261011-090000.json"
    pendiente.parent.mkdir(parents=True, exist_ok=True)
    pendiente.write_text('{"revisado": false}', encoding="utf-8")
    assert equipo.operacion_sensible_permitida("192.168.1.30") == (False, equipo.MENSAJE_REMOTO)


def test_ningun_modulo_de_api_ni_aplicacion_llama_a_es_local_de_seguridad_directamente() -> None:
    """Movida de `test_ui_cliente.py` (F3): antes recorria `ui` y `api`; `ui/` se retira, asi
    que ahora `api` y `aplicacion`. Todo pasa por `aplicacion.equipo`, no por `es_local`."""
    infractores = []
    for paquete in ("api", "aplicacion"):
        for archivo in archivos(paquete):
            for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
                usa_import = isinstance(nodo, ast.ImportFrom) and nodo.module == "seguridad.red"
                usa_llamada = (
                    isinstance(nodo, ast.Call)
                    and isinstance(nodo.func, (ast.Name, ast.Attribute))
                    and ast.unparse(nodo.func)
                    in {"es_local", "red.es_local", "seguridad.red.es_local"}
                )
                if usa_import or usa_llamada:
                    infractores.append(f"{ruta(archivo)}:{nodo.lineno}")
    assert infractores == []
