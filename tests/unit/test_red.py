"""Red local, cortafuegos y cliente local (RF-98; spec S5 §8.2). Nada ejecuta netsh de verdad.

Las órdenes esperadas se escriben a mano, palabra por palabra, a partir del spec (§8.2: `localip`
explícita, `remoteip=localsubnet`, `profile=private`, programa fijo). Ni PowerShell ni el
cortafuegos se tocan: todo efecto se sustituye por un doble que anota.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from operacion import config, red
from operacion.red import Interfaz

JSON = (
    '[{"InterfaceAlias":"Ethernet","IPAddress":"192.168.1.20"},'
    '{"InterfaceAlias":"Loopback Pseudo-Interface 1","IPAddress":"127.0.0.1"},'
    '{"InterfaceAlias":"Wi-Fi","IPAddress":"169.254.3.4"},'
    '{"InterfaceAlias":"VPN publica","IPAddress":"8.8.8.8"},'
    '{"InterfaceAlias":"Docker","IPAddress":"172.20.0.1"}]'
)
PYTHON = Path(r"C:\Prueba Sílice\Programa ñ\python\python.exe")


def test_interfaces_privadas_filtra_publicas_loopback_y_link_local() -> None:
    assert red.interfaces_privadas(lambda _: JSON) == [
        Interfaz("Docker", "172.20.0.1"),
        Interfaz("Ethernet", "192.168.1.20"),
    ]


def test_una_sola_interfaz_llega_como_objeto() -> None:
    uno = '{"InterfaceAlias":"Ethernet","IPAddress":"10.0.0.7"}'
    assert red.interfaces_privadas(lambda _: uno) == [Interfaz("Ethernet", "10.0.0.7")]


def test_una_salida_vacia_no_da_interfaces() -> None:
    assert red.interfaces_privadas(lambda _: "  \n") == []


@pytest.mark.parametrize(
    "falla",
    [
        OSError("sin powershell"),
        subprocess.TimeoutExpired("powershell.exe", 20),
        ValueError("json roto"),
    ],
)
def test_si_powershell_falla_se_usa_el_nombre_del_equipo(
    monkeypatch: pytest.MonkeyPatch, falla: Exception
) -> None:
    def ejecutor(_: str) -> str:
        raise falla

    monkeypatch.setattr(
        red.socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("10.0.0.7", 0)), (2, 1, 6, "", ("127.0.1.1", 0))],
    )
    assert [i.ip for i in red.interfaces_privadas(ejecutor)] == ["10.0.0.7"]


def test_un_json_que_no_es_de_powershell_tambien_cae_al_nombre(monkeypatch) -> None:
    monkeypatch.setattr(red.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("10.1.1.1", 0))])
    assert red.interfaces_privadas(lambda _: '[{"otra":"cosa"}]') == [
        Interfaz("(sin nombre)", "10.1.1.1")
    ]


def test_ordenes_netsh_exactas() -> None:
    ordenes = red.ordenes_activar(PYTHON, "192.168.1.20", [8501, 8000, 8501])
    assert ordenes == [
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name=Silice red local TCP {p}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={p}",
            "localip=192.168.1.20",
            "remoteip=localsubnet",
            "profile=private",
            f"program={PYTHON}",
            "enable=yes",
        ]
        for p in (8000, 8501)
    ]


def test_ninguna_orden_abre_a_todas_las_interfaces_ni_a_todos_los_perfiles() -> None:
    for orden in red.ordenes_activar(PYTHON, "10.0.0.5", [8501]):
        plano = " ".join(orden)
        assert "0.0.0.0" not in plano and "localip=any" not in plano
        assert "profile=private" in plano and "remoteip=localsubnet" in plano
        assert "profile=public" not in plano and "profile=any" not in plano


def test_desactivar_borra_por_nombre_con_comodin() -> None:
    (orden,) = red.ordenes_desactivar()
    assert orden[0] == "powershell.exe" and "'Silice red local*'" in orden[-1]
    assert "Remove-NetFirewallRule" in orden[-1]
    # el comodín cubre exactamente las reglas que crea activar
    (regla,) = red.ordenes_activar(PYTHON, "10.0.0.5", [8501])
    assert regla[5].removeprefix("name=").startswith("Silice red local")


@pytest.mark.parametrize(
    ("ip", "direccion", "esperado"),
    [
        ("127.0.0.1", "", True),
        ("127.5.5.5", "", True),
        ("::1", "", True),
        ("::ffff:127.0.0.1", "", True),
        ("192.168.1.20", "192.168.1.20", True),
        ("::ffff:192.168.1.20", "192.168.1.20", True),
        ("192.168.1.21", "192.168.1.20", False),
        ("192.168.1.20", "", False),
        ("8.8.8.8", "8.8.8.8", False),
        ("0.0.0.0", "0.0.0.0", False),
        ("::ffff:8.8.8.8", "", False),
        (None, "192.168.1.20", False),
        (None, "", False),
        ("", "", False),
        ("no-es-una-ip", "no-es-una-ip", False),
    ],
)
def test_es_cliente_local(ip, direccion: str, esperado: bool) -> None:
    assert red.es_cliente_local(ip, direccion) is esperado


@pytest.mark.parametrize("ip", ["127.0.0.1", "::1", "192.168.1.5", "8.8.8.8", "10.0.0.1"])
def test_coincide_con_la_regla_de_s3_para_el_bucle_local(ip: str) -> None:
    """RP10-8: con una IP legible y sin red local, las dos reglas dicen lo mismo. `es_local` de S3
    exige `red_local_encendida` por nombre (firma real); con una IP no vacía no influye."""
    from seguridad.red import es_local

    assert red.es_cliente_local(ip, "") == es_local(ip, red_local_encendida=True)
    assert red.es_cliente_local(ip, "") == es_local(ip, red_local_encendida=False)


def test_tuneles_conocidos_en_ejecucion() -> None:
    listar = lambda: ["python.exe", "cloudflared.exe", "NGROK.EXE", "chrome.exe"]  # noqa: E731
    assert red.tuneles_en_ejecucion(listar) == ["cloudflared", "ngrok"]
    assert red.tuneles_en_ejecucion(lambda: ["python.exe"]) == []
    assert red.tuneles_en_ejecucion(lambda: ["/usr/bin/frpc"]) == ["frpc"]
    assert red.tuneles_en_ejecucion(lambda: ["ngrok-helper.exe"]) == []  # nombre exacto


@pytest.mark.parametrize(
    ("ruta", "unc"),
    [
        (r"\\equipo\x\a.db", True),
        ("//servidor/x", True),
        (r"\\?\UNC\servidor\x", True),
        (r"\\?\unc\servidor\x", True),
        (r"C:\Users\x", False),
        (r"\\?\C:\x", False),
        ("relativa/x", False),
        ("/home/x", False),
        ("", False),
    ],
)
def test_es_ruta_unc(ruta: str, unc: bool) -> None:
    assert red.es_ruta_unc(ruta) is unc


def _ejecutor(codigos: list[int], gastadas: list[list[str]]):
    def ejecutar(orden: list[str]) -> subprocess.CompletedProcess[str]:
        gastadas.append(orden)
        return subprocess.CompletedProcess(orden, codigos.pop(0), stdout="", stderr="fallo netsh")

    return ejecutar


def test_activar_sin_permisos_no_cambia_nada(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    gastadas: list[list[str]] = []
    resultado = red.activar(
        "192.168.1.20",
        programa=PYTHON,
        puertos=[8501],
        ruta_ajustes=ruta,
        interfaces=[Interfaz("Ethernet", "192.168.1.20")],
        ejecutor=_ejecutor([], gastadas),
        es_admin=lambda: False,
    )
    assert resultado.ok is False and "administrador" in resultado.mensaje
    assert gastadas == [] and not ruta.exists()


def test_activar_con_una_ip_que_no_es_del_equipo_se_rechaza(tmp_path: Path) -> None:
    gastadas: list[list[str]] = []
    resultado = red.activar(
        "10.9.9.9",
        programa=PYTHON,
        puertos=[8501],
        ruta_ajustes=tmp_path / "s.toml",
        interfaces=[Interfaz("Ethernet", "192.168.1.20")],
        ejecutor=_ejecutor([], gastadas),
        es_admin=lambda: True,
    )
    assert resultado.ok is False and "10.9.9.9" in resultado.mensaje
    assert gastadas == [] and not (tmp_path / "s.toml").exists()


def test_activar_guarda_la_ip_y_avisa_sin_cifrar(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    config.guardar_ajustes(ruta, config.Ajustes(puerto=8600))
    gastadas: list[list[str]] = []
    resultado = red.activar(
        "192.168.1.20",
        programa=PYTHON,
        puertos=[8600, 8000],
        ruta_ajustes=ruta,
        interfaces=[Interfaz("Ethernet", "192.168.1.20")],
        ejecutor=_ejecutor([0, 0], gastadas),
        es_admin=lambda: True,
    )
    ajustes = config.cargar_ajustes(ruta)
    assert resultado.ok and ajustes.red_local and ajustes.direccion == "192.168.1.20"
    assert ajustes.puerto == 8600  # lo demás no cambia
    assert red.AVISO_SIN_CIFRAR in resultado.mensaje
    assert "http://192.168.1.20:8600" in resultado.mensaje
    assert [o[9] for o in gastadas] == ["localport=8000", "localport=8600"]


def test_si_una_regla_falla_se_deshace_todo_y_los_ajustes_quedan_igual(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    gastadas: list[list[str]] = []
    resultado = red.activar(
        "192.168.1.20",
        programa=PYTHON,
        puertos=[8501, 8000],
        ruta_ajustes=ruta,
        interfaces=[Interfaz("Ethernet", "192.168.1.20")],
        ejecutor=_ejecutor([0, 1, 0], gastadas),
        es_admin=lambda: True,
    )
    assert resultado.ok is False and "fallo netsh" in resultado.mensaje
    assert len(gastadas) == 3 and gastadas[-1] == red.ordenes_desactivar()[0]
    assert config.cargar_ajustes(ruta).red_local is False and not ruta.exists()


def test_desactivar_borra_las_reglas_y_apaga_la_red(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    config.guardar_ajustes(
        ruta, config.Ajustes(red_local=True, direccion="192.168.1.20", puerto=8600)
    )
    gastadas: list[list[str]] = []
    resultado = red.desactivar(
        ruta_ajustes=ruta, ejecutor=_ejecutor([0], gastadas), es_admin=lambda: True
    )
    ajustes = config.cargar_ajustes(ruta)
    assert resultado.ok and ajustes.red_local is False and ajustes.direccion == ""
    assert ajustes.puerto == 8600 and gastadas == red.ordenes_desactivar()


def test_desactivar_sin_permisos_no_cambia_nada(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    config.guardar_ajustes(ruta, config.Ajustes(red_local=True, direccion="192.168.1.20"))
    gastadas: list[list[str]] = []
    resultado = red.desactivar(
        ruta_ajustes=ruta, ejecutor=_ejecutor([], gastadas), es_admin=lambda: False
    )
    assert resultado.ok is False and "administrador" in resultado.mensaje and gastadas == []
    assert config.cargar_ajustes(ruta).red_local is True
