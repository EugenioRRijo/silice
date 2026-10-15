"""RNF-19: arranque del acceso directo a la salud 200, mediana de cinco (spec S5 §4.3; T19).

Oráculo: medianas calculadas a mano sobre cinco valores escritos aquí; umbral literal de 20 s
(frontera 20,00 pasa / 20,01 falla). `una_vez` se prueba de punta a punta con un `operacion`
falso en `tmp_path` (un servidor HTTP mínimo en 127.0.0.1), sin Streamlit.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

import pytest

from scripts import medir_arranque as ma

TOLERANCIA_S = 0.005


def test_resumen_calcula_la_mediana_de_cinco() -> None:
    datos = ma.resumen([11.2, 11.4, 11.1, 11.3, 11.5])  # ordenados: 11,1 11,2 [11,3] 11,4 11,5
    assert datos["mediana_s"] == pytest.approx(11.3, abs=TOLERANCIA_S)
    assert datos["valores_s"] == pytest.approx([11.2, 11.4, 11.1, 11.3, 11.5], abs=TOLERANCIA_S)
    # ordenados: 1,0 2,0 [3,0] 5,123 9,999
    assert ma.resumen([5.123, 1.0, 9.999, 3.0, 2.0])["mediana_s"] == pytest.approx(3.0, abs=0.005)


def test_resumen_redondea_a_centesimas_y_conserva_el_orden() -> None:
    datos = ma.resumen([12.814, 12.566, 13.37, 12.99, 13.404])  # bitácora 2026-10-12, a 3 cifras
    assert datos["valores_s"] == pytest.approx([12.81, 12.57, 13.37, 12.99, 13.40], abs=1e-9)
    assert datos["mediana_s"] == pytest.approx(12.99, abs=1e-9)  # la de la bitácora


@pytest.mark.parametrize("cantidad", [0, 1, 4, 6])
def test_resumen_exige_exactamente_cinco_valores(cantidad: int) -> None:
    with pytest.raises(ValueError, match="cinco"):
        ma.resumen([1.0] * cantidad)


def test_la_tabla_para_plan_de_pruebas_trae_fecha_y_los_cinco_valores() -> None:
    datos = {
        **ma.resumen([11.2, 11.4, 11.1, 11.3, 11.5]),
        "fecha": "2026-10-30",
        "equipo": "Windows-11",
    }
    tabla = ma.tabla_markdown(datos).replace("‑", "-")
    assert tabla.startswith("### Medición de arranque (RNF-19)") and "2026-10-30" in tabla
    assert "11,20; 11,40; 11,10; 11,30; 11,50 s; mediana 11,30 s" in tabla
    assert "umbral de 20 s" in tabla and "Windows-11" in tabla


def _main_con(tiempos: list[float], salida: Path, monkeypatch) -> int:
    pendientes = iter(tiempos)
    llamadas: list[tuple] = []

    def una_vez(*argumentos, **_):
        llamadas.append(argumentos)
        return next(pendientes)

    monkeypatch.setattr(ma, "una_vez", una_vez)
    codigo = ma.main(["--salida", str(salida)])
    assert len(llamadas) == 6  # calentamiento + cinco
    assert next(pendientes, None) is None
    return codigo


def test_main_mide_una_corrida_de_calentamiento_y_cinco_y_deja_el_json(
    tmp_path: Path, monkeypatch
) -> None:
    salida = tmp_path / "arranque.json"
    # el primero es el calentamiento (crea las bases): se descarta
    assert _main_con([30.0, 11.2, 11.4, 11.1, 11.3, 11.5], salida, monkeypatch) == 0
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["valores_s"] == pytest.approx([11.2, 11.4, 11.1, 11.3, 11.5], abs=TOLERANCIA_S)
    assert datos["mediana_s"] == pytest.approx(11.3, abs=TOLERANCIA_S)
    assert {"fecha", "equipo", "python", "instalado"} <= set(datos)
    assert datos["instalado"] is False  # el repositorio no tiene manifiesto.json


@pytest.mark.parametrize(
    ("mediana", "codigo"),
    [(20.0, 0), (20.01, 1)],  # el umbral cumple; un centésimo más, no
)
def test_main_sale_con_1_si_la_mediana_pasa_de_20_s(
    tmp_path: Path, monkeypatch, mediana: float, codigo: int
) -> None:
    tiempos = [30.0, 1.0, 2.0, mediana, 25.0, 26.0]
    assert _main_con(tiempos, tmp_path / "a.json", monkeypatch) == codigo


def test_main_usa_una_carpeta_de_datos_temporal_y_un_puerto_libre(
    tmp_path: Path, monkeypatch
) -> None:
    vistas: list[tuple] = []

    def una_vez(python, cwd, puerto, entorno):
        carpeta = Path(entorno["SILICE_DATOS"])
        ajustes = (carpeta / "config" / "silice.toml").read_text(encoding="utf-8")
        vistas.append((carpeta, puerto, str(puerto) in ajustes, entorno["SILICE_USUARIO"]))
        return 1.0

    monkeypatch.setattr(ma, "una_vez", una_vez)
    monkeypatch.setenv("PYTHONPATH", "no-debe-pasar")
    assert ma.main(["--salida", str(tmp_path / "a.json")]) == 0
    carpetas = {v[0] for v in vistas}
    assert len(carpetas) == 1 and len(vistas) == 6
    (carpeta,) = carpetas
    assert not carpeta.exists()  # se borra al terminar: no toca datos reales
    assert all(v[2] for v in vistas) and all(v[3] == str(carpeta) for v in vistas)


OPERACION_FALSA = """
import http.server, os, pathlib, sys

orden = sys.argv[1]
puerto = int(os.environ["PUERTO_FALSO"])
marca = pathlib.Path(os.environ["MARCA_FALSA"])
if orden == "arrancar":
    if os.environ.get("FALLAR"):
        raise SystemExit(3)

    class Salud(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200 if self.path == "/_stcore/health" else 404)
            self.end_headers()

        def log_message(self, *a):
            pass

    servidor = http.server.HTTPServer(("127.0.0.1", puerto), Salud)
    servidor.timeout = 0.1
    while not marca.exists():
        servidor.handle_request()
    servidor.server_close()
elif orden == "parar":
    marca.write_text("parar", encoding="utf-8")
"""


def _operacion_falsa(tmp_path: Path, **extra: str) -> tuple[int, dict[str, str]]:
    (tmp_path / "operacion").mkdir()
    (tmp_path / "operacion" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "operacion" / "__main__.py").write_text(OPERACION_FALSA, encoding="utf-8")
    with socket.socket() as zocalo:
        zocalo.bind(("127.0.0.1", 0))
        puerto = zocalo.getsockname()[1]
    entorno = {
        **os.environ,
        "PUERTO_FALSO": str(puerto),
        "MARCA_FALSA": str(tmp_path / "parado"),
        **extra,
    }
    return puerto, entorno


def test_una_vez_mide_hasta_la_salud_200_y_luego_para(tmp_path: Path) -> None:
    puerto, entorno = _operacion_falsa(tmp_path)
    segundos = ma.una_vez(Path(sys.executable), tmp_path, puerto, entorno)
    assert 0 < segundos < 60
    assert (tmp_path / "parado").read_text(encoding="utf-8") == "parar"  # corrió `parar`


def test_una_vez_falla_si_silice_termina_antes_de_responder(tmp_path: Path) -> None:
    puerto, entorno = _operacion_falsa(tmp_path, FALLAR="1")
    with pytest.raises(RuntimeError, match="terminó antes"):
        ma.una_vez(Path(sys.executable), tmp_path, puerto, entorno)
    assert (tmp_path / "parado").is_file()  # `parar` corre igual (finally)


def test_las_banderas_son_las_del_lanzador() -> None:
    assert ma.BANDERAS == ["-E", "-s", "-B", "-X", "utf8", "-m", "operacion"]  # RP10-7
    assert ma.LIMITE_S == pytest.approx(20.0, abs=1e-9)
