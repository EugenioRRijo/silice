"""Piezas de la prueba de humo que sí se pueden probar sin Windows ni instalador (spec S5 §11.2;
T16).

`humo.ps1` no se ejecuta aquí (toca el cortafuegos y necesita el instalador y Edge): se lee su
texto. `navegador.py` se prueba sin Playwright (solo `externos`); `proxy_testigo.py` escucha en
127.0.0.1 con un puerto libre; `verificar_bases.py` con las bases de prueba copiadas a `tmp_path`.
"""

from __future__ import annotations

import http.client
import json
import re
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

import pytest

from instalador import navegador, proxy_testigo, verificar_bases
from operacion.base_datos import preparar_base
from tests.fixtures import bases_prueba as bp

RAIZ = Path(__file__).resolve().parents[2]
HUMO = RAIZ / "instalador" / "humo.ps1"


def test_externos_ignora_el_bucle_local_y_los_esquemas_que_no_son_red() -> None:
    urls = [
        "http://127.0.0.1:8501/",
        "ws://127.0.0.1:8501/_stcore/stream",
        "http://localhost:8501/x",
        "http://[::1]:8501/x",
        "data:image/png;base64,AAAA",
        "blob:http://127.0.0.1:8501/abc",
        "about:srcdoc",
        "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
        "https://browser.events.data.microsoft.com/x",
        "https://cdnjs.cloudflare.com/otro.js",  # el mismo anfitrión una sola vez
        "wss://otro.ejemplo/socket",
    ]
    assert navegador.externos(urls) == [
        "browser.events.data.microsoft.com",
        "cdnjs.cloudflare.com",
        "otro.ejemplo",
    ]
    assert navegador.externos([]) == []


def test_una_ip_de_la_red_local_tambien_es_externa_para_el_navegador() -> None:
    """Solo el bucle local cuenta como «dentro»: 192.168.x es otro equipo."""
    assert navegador.externos(["http://192.168.1.20:8501/"]) == ["192.168.1.20"]
    assert navegador.externos(["http://127.0.0.2:8501/"]) == ["127.0.0.2"]


def test_navegador_main_escribe_el_json_y_sale_con_1_si_hay_externos(
    tmp_path: Path, monkeypatch
) -> None:
    vistas = ["http://127.0.0.1:8501/", "https://cdnjs.cloudflare.com/x.js"]
    pedidas: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        navegador, "recorrer", lambda url, paginas: pedidas.append((url, paginas)) or vistas
    )
    salida = tmp_path / "peticiones.json"
    codigo = navegador.main(["--url", "http://127.0.0.1:8501/", "--salida", str(salida)])
    assert codigo == 1
    assert pedidas == [("http://127.0.0.1:8501", ["", "visor", "similares"])]
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos == {"peticiones": 2, "externos": ["cdnjs.cloudflare.com"], "urls": vistas}
    monkeypatch.setattr(navegador, "recorrer", lambda url, paginas: vistas[:1])
    assert navegador.main(["--url", "http://127.0.0.1:8501", "--salida", str(salida)]) == 0


@pytest.fixture
def testigo(tmp_path: Path):
    registro = tmp_path / "proxy.log"
    servidor = proxy_testigo.crear_servidor(0, registro)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield servidor.server_address[1], registro
    servidor.shutdown()
    servidor.server_close()
    hilo.join(timeout=5)


def _pedir(puerto: int, metodo: str, destino: str) -> int:
    conexion = http.client.HTTPConnection("127.0.0.1", puerto, timeout=5)
    try:
        conexion.request(metodo, destino)
        return conexion.getresponse().status
    finally:
        conexion.close()


def test_el_proxy_testigo_anota_cada_peticion_y_no_deja_pasar_ninguna(testigo) -> None:
    puerto, registro = testigo
    assert _pedir(puerto, "GET", "http://ejemplo.invalid/x") == 502
    assert _pedir(puerto, "CONNECT", "ejemplo.invalid:443") == 502
    assert _pedir(puerto, "POST", "http://otro.invalid/api") == 502
    assert registro.read_text(encoding="utf-8").splitlines() == [
        "GET http://ejemplo.invalid/x",
        "CONNECT ejemplo.invalid:443",
        "POST http://otro.invalid/api",
    ]


def test_el_proxy_testigo_escucha_solo_en_el_bucle_local(testigo) -> None:
    puerto, _ = testigo
    assert puerto > 0
    servidor = proxy_testigo.crear_servidor(0, Path("no_se_usa.log"))
    try:
        assert servidor.server_address[0] == "127.0.0.1"
    finally:
        servidor.server_close()


def test_sin_peticiones_el_registro_no_existe_o_esta_vacio(testigo) -> None:
    _, registro = testigo
    assert not registro.exists() or registro.read_text(encoding="utf-8") == ""


def _caso(tmp_path: Path, version: str, nombre: str, archivo: str) -> Path:
    destino = tmp_path / archivo
    bp.copiar_base(version, nombre, destino)
    preparar_base(destino)
    return destino


def test_una_base_migrada_cuadra_con_la_ficha_de_su_version(tmp_path: Path) -> None:
    _caso(tmp_path, "0.5.0", "demo.db", "v050_demo.db")
    pares = [verificar_bases.Par("0.5.0", "demo.db", "v050_demo.db")]
    assert verificar_bases.verificar(tmp_path, pares) == []


def test_una_base_alterada_o_sin_migrar_se_reporta(tmp_path: Path) -> None:
    ruta = _caso(tmp_path, "0.5.0", "demo.db", "v050_demo.db")
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("DELETE FROM alembic_version")
        conexion.commit()
    pares = [
        verificar_bases.Par("0.5.0", "demo.db", "v050_demo.db"),
        verificar_bases.Par("0.5.0", "of001.db", "no_esta.db"),
    ]
    problemas = verificar_bases.verificar(tmp_path, pares)
    assert len(problemas) == 2
    assert any("v050_demo.db" in p and "head" in p for p in problemas)
    assert any("no_esta.db" in p and "no existe" in p for p in problemas)


def test_una_base_sin_migrar_no_esta_en_head(tmp_path: Path) -> None:
    """La base de la 0.5.0 copiada tal cual (el instalador no la migró): se reporta."""
    bp.copiar_base("0.5.0", "demo.db", tmp_path / "v050_demo.db")
    problemas = verificar_bases.verificar(
        tmp_path, [verificar_bases.Par("0.5.0", "demo.db", "v050_demo.db")]
    )
    assert problemas and all(p.startswith("v050_demo.db: ") for p in problemas)
    assert any("no en head" in p for p in problemas)


def test_una_fila_borrada_no_cuadra_con_la_ficha(tmp_path: Path) -> None:
    ruta = _caso(tmp_path, "0.5.0", "demo.db", "v050_demo.db")
    esperado = bp.ficha("0.5.0")["bases"]["demo.db"]["filas_por_tabla"]
    tabla = next(t for t, n in sorted(esperado.items()) if n > 0 and t != "alembic_version")
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("PRAGMA foreign_keys = OFF")
        conexion.execute(f'DELETE FROM "{tabla}" WHERE rowid = (SELECT MIN(rowid) FROM "{tabla}")')
        conexion.commit()
    problemas = verificar_bases.verificar(
        tmp_path, [verificar_bases.Par("0.5.0", "demo.db", "v050_demo.db")]
    )
    assert (
        f"v050_demo.db: {tabla}: {esperado[tabla] - 1} filas; la ficha dice {esperado[tabla]}"
        in (problemas)
    )


def test_el_argumento_par_se_lee_version_base_archivo() -> None:
    assert verificar_bases.leer_par("0.9.0:demo.db=v090_demo.db") == verificar_bases.Par(
        "0.9.0", "demo.db", "v090_demo.db"
    )
    for malo in ("sin-formato", "0.9.0:demo.db", "demo.db=v090.db"):
        with pytest.raises(ValueError, match="VERSION:BASE=ARCHIVO"):
            verificar_bases.leer_par(malo)


def test_verificar_bases_main_sale_con_1_y_lista_los_problemas(tmp_path: Path, capsys) -> None:
    codigo = verificar_bases.main(["--casos", str(tmp_path), "--par", "0.5.0:demo.db=falta.db"])
    assert codigo == 1
    assert json.loads(capsys.readouterr().out)["problemas"] == [
        f"falta.db: no existe en {tmp_path}"
    ]


def test_humo_cubre_cada_comprobacion_del_spec() -> None:
    texto = HUMO.read_text(encoding="utf-8-sig")
    for pieza in (
        "New-NetFirewallRule",
        "-Direction Outbound",
        "-Action Block",
        "LogBlocked",  # cortafuegos
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/CURRENTUSER",
        "/DIR=",
        "Get-NetTCPConnection -State Listen",
        "'0.0.0.0'",
        "'::'",  # escucha
        "_stcore/health",
        "navegador.py",
        "proxy_testigo.py",
        "HTTP_PROXY",
        "NO_PROXY",
        "verificar-programa",
        "verificar_bases.py",
        "red-local",
        "unins000.exe",
        "$env:SILICE_DATOS",
        "$env:SILICE_USUARIO",
        "tiempos.json",
    ):
        assert pieza in texto, pieza
    assert "Invoke-Expression" not in texto and not re.search(r"\biex\b", texto, re.I)
    assert "$ErrorActionPreference = 'Stop'" in texto and "Set-StrictMode" in texto
    assert "C:\\Prueba Sílice" in texto and "Programa ñ" in texto


def test_humo_usa_las_banderas_del_lanzador() -> None:
    texto = HUMO.read_text(encoding="utf-8-sig")
    assert "$Banderas = @('-E', '-s', '-B', '-X', 'utf8', '-m', 'operacion')" in texto


def test_humo_no_pide_nada_a_internet_desde_el_programa() -> None:
    texto = HUMO.read_text(encoding="utf-8-sig")
    # la única red que usa el script es 127.0.0.1 y la IP local; `uv run --with playwright` es del
    # runner, no de Sílice, y el cortafuegos bloquea solo el python.exe de {app}
    assert "$Url = 'http://127.0.0.1:8501'" in texto
    assert "https://" not in texto


def test_humo_trae_bom_para_powershell_5() -> None:
    """Windows PowerShell 5.1 lee sin BOM como ANSI y rompería «Sílice» y «ñ»."""
    assert HUMO.read_bytes().startswith(b"\xef\xbb\xbf")
