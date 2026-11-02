"""Órdenes de `python -m operacion` de la 1.0.0 (spec S5 §5.4, §6.5, §8.2).

Ninguna orden toca el cortafuegos ni pide permisos: `red.activar`, `red.desactivar`,
`red.es_administrador` y `red.relanzar_elevado` se sustituyen por dobles que anotan.
"""

from __future__ import annotations

import pytest

from operacion import __main__ as cli
from operacion import base_datos, config, lanzador, red


def test_arrancar_y_parar_llaman_al_lanzador(monkeypatch: pytest.MonkeyPatch) -> None:
    llamadas: list[tuple] = []
    monkeypatch.setattr(lanzador, "arrancar", lambda **k: llamadas.append(("arrancar", k)) or 3)
    monkeypatch.setattr(lanzador, "parar", lambda **k: llamadas.append(("parar", k)) or 4)
    assert cli.main(["arrancar", "--sin-navegador"]) == 3
    assert cli.main(["arrancar"]) == 3
    assert cli.main(["parar"]) == 4
    assert llamadas == [
        ("arrancar", {"sin_navegador": True}),
        ("arrancar", {"sin_navegador": False}),
        ("parar", {}),
    ]


def test_restaurar_exige_silice_detenido(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(lanzador, "hay_instancia", lambda *a, **k: True)
    monkeypatch.setattr(
        base_datos, "restaurar_juego", lambda *a, **k: pytest.fail("no debe restaurar")
    )
    assert cli.main(["restaurar", str(tmp_path)]) == 1
    assert "deténgalo" in capsys.readouterr().err


def test_restaurar_con_silice_detenido_si_restaura(monkeypatch, capsys, tmp_path) -> None:
    pedidos: list[tuple] = []
    monkeypatch.setattr(lanzador, "hay_instancia", lambda *a, **k: False)

    def restaurar(juego, solo_caso=None):
        pedidos.append((juego, solo_caso))
        return base_datos.Restauracion(
            antes=tmp_path / "antes", restauradas=(tmp_path / "silice.db",), eventos_perdidos=None
        )

    monkeypatch.setattr(base_datos, "restaurar_juego", restaurar)
    assert cli.main(["restaurar", str(tmp_path), "--solo-caso", "silice"]) == 0
    assert pedidos == [(tmp_path, "silice")]
    assert "Restauradas: silice.db" in capsys.readouterr().out


def test_la_demostracion_prepara_el_caso_y_lo_siembra(monkeypatch) -> None:
    llamadas: list[list[str]] = []
    import scripts.seed_demo as seed_demo

    monkeypatch.setattr(seed_demo, "main", lambda argv: llamadas.append(list(argv)) or 0)
    assert cli.main(["demostracion"]) == 0
    destino = config.carpeta_casos() / "demostracion.db"
    assert destino.exists() and llamadas == [["--db", str(destino)]]


def test_la_demostracion_devuelve_el_codigo_del_sembrador(monkeypatch) -> None:
    import scripts.seed_demo as seed_demo

    monkeypatch.setattr(seed_demo, "main", lambda argv: 2)
    assert cli.main(["demostracion"]) == 2


def test_red_local_estado_describe_la_configuracion(capsys) -> None:
    config.guardar_ajustes(
        config.ruta_ajustes(), config.Ajustes(red_local=True, direccion="10.0.0.5")
    )
    assert cli.main(["red-local", "estado"]) == 0
    texto = capsys.readouterr().out
    assert "encendida" in texto and "http://10.0.0.5:8501/app/" in texto
    assert "API" not in texto and "Streamlit" not in texto  # un solo puerto


def test_red_local_estado_apagada_por_defecto(capsys) -> None:
    assert cli.main(["red-local", "estado"]) == 0
    texto = capsys.readouterr().out
    assert "Red local: apagada (solo http://127.0.0.1:8501/app/)" in texto
    assert not config.ruta_ajustes().exists()  # describir no crea el archivo


def test_red_local_activar_con_ip_pide_confirmacion_y_activa(monkeypatch, capsys) -> None:
    visto: dict = {}
    monkeypatch.setattr(red, "interfaces_privadas", lambda: [red.Interfaz("Ethernet", "10.0.0.5")])
    monkeypatch.setattr(red, "es_administrador", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "s")
    monkeypatch.setattr(
        red,
        "activar",
        lambda ip, **k: visto.update(ip=ip, **k) or red.ResultadoRed(True, "listo"),
    )
    assert cli.main(["red-local", "activar", "--ip", "10.0.0.5"]) == 0
    assert visto["ip"] == "10.0.0.5" and visto["puertos"] == [8501]
    assert visto["ruta_ajustes"] == config.ruta_ajustes()
    salida = capsys.readouterr().out
    assert red.AVISO_SIN_CIFRAR in salida and "listo" in salida


def test_red_local_activar_abre_solo_el_puerto_unico_aunque_haya_tabla_api(monkeypatch) -> None:
    ruta = config.ruta_ajustes()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("[servidor]\npuerto = 8501\n[api]\nactiva = true\npuerto = 8010\n", "utf-8")
    visto: dict = {}
    monkeypatch.setattr(red, "interfaces_privadas", lambda: [red.Interfaz("Ethernet", "10.0.0.5")])
    monkeypatch.setattr(red, "es_administrador", lambda: True)
    monkeypatch.setattr(
        red, "activar", lambda ip, **k: visto.update(k) or red.ResultadoRed(True, "listo")
    )
    assert cli.main(["red-local", "activar", "--ip", "10.0.0.5", "--si"]) == 0
    assert visto["puertos"] == [8501]


def test_red_local_activar_si_no_se_confirma_no_cambia_nada(monkeypatch) -> None:
    monkeypatch.setattr(red, "interfaces_privadas", lambda: [red.Interfaz("Ethernet", "10.0.0.5")])
    monkeypatch.setattr(red, "es_administrador", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    monkeypatch.setattr(red, "activar", lambda *a, **k: pytest.fail("no debe activar"))
    assert cli.main(["red-local", "activar", "--ip", "10.0.0.5"]) == 1
    assert not config.ruta_ajustes().exists()


def test_red_local_activar_elige_la_interfaz_por_numero(monkeypatch) -> None:
    interfaces = [red.Interfaz("Docker", "172.20.0.1"), red.Interfaz("Ethernet", "10.0.0.5")]
    respuestas = iter(["2", "s"])
    visto: dict = {}
    monkeypatch.setattr(red, "interfaces_privadas", lambda: interfaces)
    monkeypatch.setattr(red, "es_administrador", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: next(respuestas))
    monkeypatch.setattr(
        red, "activar", lambda ip, **k: visto.update(ip=ip) or red.ResultadoRed(True, "listo")
    )
    assert cli.main(["red-local", "activar"]) == 0 and visto["ip"] == "10.0.0.5"


@pytest.mark.parametrize("respuesta", ["0", "3", "uno", ""])
def test_red_local_activar_con_un_numero_fuera_de_rango_no_elige(monkeypatch, respuesta) -> None:
    """Frontera: con dos interfaces, 1 y 2 valen; 0 y 3 no."""
    interfaces = [red.Interfaz("Docker", "172.20.0.1"), red.Interfaz("Ethernet", "10.0.0.5")]
    monkeypatch.setattr(red, "interfaces_privadas", lambda: interfaces)
    monkeypatch.setattr(red, "es_administrador", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: respuesta)
    monkeypatch.setattr(red, "activar", lambda *a, **k: pytest.fail("no debe activar"))
    assert cli.main(["red-local", "activar"]) == 1


def test_red_local_activar_sin_permisos_relanza_elevado(monkeypatch) -> None:
    pedidos: list[list[str]] = []
    monkeypatch.setattr(red, "interfaces_privadas", lambda: [red.Interfaz("Ethernet", "10.0.0.5")])
    monkeypatch.setattr(red, "es_administrador", lambda: False)
    monkeypatch.setattr(red, "relanzar_elevado", lambda args: pedidos.append(list(args)) or True)
    monkeypatch.setattr(red, "activar", lambda *a, **k: pytest.fail("activa el elevado"))
    assert cli.main(["red-local", "activar"]) == 0
    assert cli.main(["red-local", "activar", "--ip", "10.0.0.5"]) == 0
    assert pedidos == [
        ["red-local", "activar", "--elevado"],
        ["red-local", "activar", "--elevado", "--ip", "10.0.0.5"],
    ]


def test_red_local_activar_si_el_usuario_rechaza_uac_devuelve_1(monkeypatch) -> None:
    monkeypatch.setattr(red, "interfaces_privadas", lambda: [red.Interfaz("Ethernet", "10.0.0.5")])
    monkeypatch.setattr(red, "es_administrador", lambda: False)
    monkeypatch.setattr(red, "relanzar_elevado", lambda args: False)
    assert cli.main(["red-local", "activar"]) == 1


def test_red_local_activar_sin_interfaces_privadas_lo_dice(monkeypatch, capsys) -> None:
    monkeypatch.setattr(red, "interfaces_privadas", lambda: [])
    assert cli.main(["red-local", "activar", "--si"]) == 1
    assert "ninguna interfaz" in capsys.readouterr().err


def test_red_local_activar_que_falla_devuelve_1_y_lo_dice_en_stderr(monkeypatch, capsys) -> None:
    monkeypatch.setattr(red, "interfaces_privadas", lambda: [red.Interfaz("Ethernet", "10.0.0.5")])
    monkeypatch.setattr(red, "es_administrador", lambda: True)
    monkeypatch.setattr(red, "activar", lambda ip, **k: red.ResultadoRed(False, "rechazada"))
    assert cli.main(["red-local", "activar", "--ip", "10.0.0.5", "--si"]) == 1
    assert "rechazada" in capsys.readouterr().err


@pytest.mark.parametrize(("ok", "codigo"), [(True, 0), (False, 1)])
def test_red_local_desactivar(monkeypatch, capsys, ok: bool, codigo: int) -> None:
    visto: dict = {}
    monkeypatch.setattr(
        red, "desactivar", lambda **k: visto.update(k) or red.ResultadoRed(ok, "hecho")
    )
    assert cli.main(["red-local", "desactivar"]) == codigo
    assert visto == {"ruta_ajustes": config.ruta_ajustes()}
    salida = capsys.readouterr()
    assert "hecho" in (salida.out if ok else salida.err)


def test_red_local_sin_accion_es_un_error_de_uso(capsys) -> None:
    with pytest.raises(SystemExit) as salida:
        cli.main(["red-local"])
    assert salida.value.code == 2
    capsys.readouterr()


def test_el_diagnostico_de_similitud_usa_el_proponedor_sin_red(monkeypatch, capsys) -> None:
    import ml.normalization as normalizacion

    monkeypatch.setattr(lanzador, "variables_de_similitud", lambda raiz=None: {})

    class Propuesta:
        falla = None

    monkeypatch.setattr(normalizacion, "proponedor", lambda partidas: lambda texto: Propuesta())
    assert cli.main(["diagnostico-similitud"]) == 0
    assert "sin red" in capsys.readouterr().out


def test_el_diagnostico_de_similitud_falla_si_el_modelo_no_esta(monkeypatch, capsys) -> None:
    import ml.normalization as normalizacion

    monkeypatch.setattr(lanzador, "variables_de_similitud", lambda raiz=None: {})

    class Propuesta:
        falla = "ImportError: no hay sentence_transformers"

    monkeypatch.setattr(normalizacion, "proponedor", lambda partidas: lambda texto: Propuesta())
    assert cli.main(["diagnostico-similitud"]) == 1
    assert "ImportError" in capsys.readouterr().err


def test_verificar_programa_fuera_del_producto_lo_dice(capsys) -> None:
    """En el árbol de desarrollo no hay `manifiesto.json` junto al código."""
    assert cli.main(["verificar-programa"]) == 1
    assert "manifiesto.json" in capsys.readouterr().err


def test_las_ordenes_de_la_1_0_0_estan_registradas() -> None:
    import argparse

    from operacion import ordenes_100

    tabla: dict = {}
    analizador = argparse.ArgumentParser()
    ordenes_100.registrar(analizador.add_subparsers(dest="orden"), tabla)
    assert set(tabla) == {
        "arrancar",
        "parar",
        "demostracion",
        "red-local",
        "diagnostico-similitud",
        "verificar-programa",
        "eventos",
        "generar-clave-proyecto",
        "firmar-sumas",
        "verificar-instalador",
        "huella-clave-proyecto",
        "restablecer-administrador",  # BCP-1
    }
