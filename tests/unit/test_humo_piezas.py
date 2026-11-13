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
import shutil
import sqlite3
import subprocess
import threading
from contextlib import closing
from pathlib import Path

import pytest

from instalador import navegador, proxy_testigo, verificar_bases
from operacion.base_datos import preparar_base
from seguridad import cuentas
from tests.fixtures import bases_prueba as bp

RAIZ = Path(__file__).resolve().parents[2]
HUMO = RAIZ / "instalador" / "humo.ps1"


def test_externos_ignora_el_bucle_local_y_los_esquemas_que_no_son_red() -> None:
    urls = [
        "http://127.0.0.1:8501/",
        "ws://127.0.0.1:8501/app/stream",
        "http://localhost:8501/x",
        "http://[::1]:8501/x",
        "data:image/png;base64,AAAA",
        "blob:http://127.0.0.1:8501/abc",
        "about:srcdoc",
        "https://cdnjs.cloudflare.com/ajax/libs/otra/biblioteca.min.js",
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
    assert pedidas == [("http://127.0.0.1:8501", ["", "#/precios/catalogo", "#/precios/simulador"])]
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos == {"peticiones": 2, "externos": ["cdnjs.cloudflare.com"], "urls": vistas}
    monkeypatch.setattr(navegador, "recorrer", lambda url, paginas: vistas[:1])
    assert navegador.main(["--url", "http://127.0.0.1:8501", "--salida", str(salida)]) == 0


def _herramientas_por_espacio() -> dict[str, set[str]]:
    """Lee `marco/espacios.ts` (el registro de rutas canónicas): espacio -> ids de herramienta."""
    texto = (RAIZ / "frontend-desktop" / "src" / "marco" / "espacios.ts").read_text(
        encoding="utf-8"
    )
    cuerpo = texto[texto.index("export const ESPACIOS:") : texto.index("export const SUBVISTAS")]
    espacios: dict[str, set[str]] = {}
    for bloque in re.finditer(r"^  ([a-z]+): \{\n(.*?)^  \},", cuerpo, flags=re.M | re.S):
        espacios[bloque[1]] = set(re.findall(r'\{ id: "([a-z-]+)", titulo:', bloque[2]))
    return espacios


def test_las_paginas_del_humo_existen_en_el_registro_de_rutas(tmp_path: Path, monkeypatch) -> None:
    """Una pantalla dada de baja redirige a Pendientes y el humo cargaría una pantalla menos sin
    decirlo (F4: `similares`, `elaborar` e `historico` salieron del registro). Se comprueba la
    ruta canónica completa (espacio y herramienta), no solo el último segmento."""
    pedidas: list[list[str]] = []
    monkeypatch.setattr(navegador, "recorrer", lambda url, paginas: pedidas.append(paginas) or [])
    navegador.main(["--url", "http://127.0.0.1:8501", "--salida", str(tmp_path / "p.json")])
    registro = _herramientas_por_espacio()
    assert registro["precios"] >= {
        "catalogo",
        "simulador",
        "indices",
        "listas",
    }  # el lector funciona
    assert set(registro) == {"produccion", "auditoria", "precios"}
    paginas = [p.removeprefix("#/") for p in pedidas[0] if p]
    assert paginas == ["precios/catalogo", "precios/simulador"]
    for ruta in paginas:
        espacio, herramienta = ruta.split("/")
        assert herramienta in registro[espacio], ruta
    # Una herramienta que existe en otro espacio no vale: la ruta completa es la que se comprueba.
    assert "simulador" not in registro["auditoria"]
    assert "catalogo" not in registro["produccion"]


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
        "/salud",
        "$UrlApp",
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


def test_el_humo_espera_cada_base_cuando_el_diseno_la_crea() -> None:
    """La instalación crea `instalacion.db` (orden `migrar`, spec S5 UC-24 paso 2) y el caso de
    demostración (orden `demostracion`); el caso por defecto `casos/silice.db` lo crea el lanzador
    al primer arranque (`preparar_base`, spec S5 §5.4 paso 3). Hasta 2026-10-18 el paso 2 exigía
    `silice.db` justo después de instalar, y el humo nunca pasó en la CI."""
    texto = HUMO.read_text(encoding="utf-8-sig")
    paso2, paso3 = texto.index("Paso '2."), texto.index("Paso '3.")
    paso4, paso5 = texto.index("Paso '4."), texto.index("Paso '5.")
    instalacion = texto[paso2:paso3]
    arranque = texto[paso4:paso5]
    assert "'instalacion.db'" in instalacion and r"'casos\demostracion.db'" in instalacion
    assert "silice.db" not in instalacion
    assert r"'casos\silice.db'" in arranque
    assert arranque.index("EsperarSalud") < arranque.index("silice.db")


def test_ninguna_variable_del_humo_pisa_a_otra_por_mayusculas() -> None:
    """PowerShell no distingue mayúsculas en los nombres de variable: `$codigo = InstalarSilencioso`
    pisaba la ruta `$Codigo` con el código de salida y el paso 3 arrancaba en la carpeta «0»
    (diagnosticado en la CI el 2026-10-18). Cada variable global del encabezado se asigna una
    sola vez."""
    texto = HUMO.read_text(encoding="utf-8-sig")
    globales = ("Base", "Programa", "Usuario", "Datos", "Respaldos", "Codigo", "Python")
    for nombre in globales:
        asignaciones = re.findall(rf"(?im)^\s*\${nombre}\s*=", texto)
        assert len(asignaciones) == 1, (nombre, asignaciones)


def _funcion_del_humo(nombre: str) -> str:
    """El texto de `function nombre ... }` de `humo.ps1` (las funciones de este archivo cierran en
    una línea que empieza por `}` sin sangría)."""
    texto = HUMO.read_text(encoding="utf-8-sig")
    m = re.search(rf"^function {nombre}\b.*?^\}}$", texto, re.S | re.M)
    assert m, nombre
    return m.group(0)


def _a_entero(ip: str) -> int:
    a, b, c, d = (int(x) for x in ip.split("."))
    return (a << 24) | (b << 16) | (c << 8) | d


@pytest.mark.parametrize(
    "ip",
    ["10.1.2.3", "10.0.0.0", "172.18.0.5", "192.168.1.7", "128.0.0.0", "126.255.255.255"],
)
def test_rangos_sin_cubre_todo_ipv4_salvo_el_bucle_local_y_la_ip_propia(
    ip: str, tmp_path: Path
) -> None:
    """Set-NetFirewallRule rechaza un rango con el final menor que el inicio: la CI de Windows lo
    probó con una IP 10.x (inicio 128.0.0.0) y el paso 8 del humo cayó. Se corre la función
    REAL de `humo.ps1` con PowerShell y se compara con un oráculo en enteros."""
    pwsh = shutil.which("pwsh")
    assert pwsh, "la prueba necesita PowerShell 7 (pwsh), igual que la CI"
    guion = tmp_path / "rangos.ps1"
    guion.write_text(
        "\n".join(_funcion_del_humo(f) for f in ("AEntero", "ADecimal", "RangosSin"))
        + f"\nRangosSin '{ip}'\n",
        encoding="utf-8",
    )
    salida = subprocess.run(
        [pwsh, "-NoProfile", "-File", str(guion)], capture_output=True, text=True, check=True
    ).stdout.split()
    tramos = [tuple(_a_entero(x) for x in r.split("-")) for r in salida]
    assert all(inicio <= fin for inicio, fin in tramos), salida
    propia = _a_entero(ip)
    # Sin solaparse y ordenados: cada tramo empieza después del final del anterior.
    assert all(a[1] < b[0] for a, b in zip(tramos, tramos[1:], strict=False)), salida
    cubierto = sum(fin - inicio + 1 for inicio, fin in tramos)
    assert cubierto == (2**32 - 2**24) - 1  # todo menos 127.0.0.0/8 y la IP propia
    assert not any(inicio <= propia <= fin for inicio, fin in tramos)
    assert not any(inicio <= _a_entero("127.0.0.1") <= fin for inicio, fin in tramos)


def _buena_descarga() -> dict:
    return {
        "reclamo": 201,
        "respaldo": 200,
        "bajada": 200,
        "tipo": "application/zip",
        "disposicion": 'attachment; filename="respaldo.zip"',
        "bytes": 256,
        "firma": "PK",
    }


def test_descarga_valida_acepta_un_zip_completo() -> None:
    assert navegador.descarga_valida(_buena_descarga()) is True


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("reclamo", 401),
        ("respaldo", 403),
        ("bajada", 404),
        ("tipo", "text/html; charset=utf-8"),
        ("disposicion", "inline"),
        ("bytes", 0),
        ("firma", "<!"),
        ("firma", None),
    ],
)
def test_descarga_valida_rechaza_cada_campo_malo(campo: str, valor: object) -> None:
    malo = _buena_descarga()
    malo[campo] = valor
    assert navegador.descarga_valida(malo) is False


class _PeticionFalsa:
    def __init__(self, url: str) -> None:
        self.url = url


class _PaginaFalsa:
    def __init__(self, url: str, resultado_eval: dict | None = None) -> None:
        self.url = url
        self._resultado_eval = resultado_eval
        self._manejadores: dict[str, list] = {}
        self.visitadas: list[str] = []
        self.evaluaciones: list[tuple[str, dict]] = []

    def on(self, evento: str, manejador) -> None:
        self._manejadores.setdefault(evento, []).append(manejador)

    def goto(self, url: str, **_kwargs) -> None:
        self.visitadas.append(url)
        for manejador in self._manejadores.get("request", []):
            manejador(_PeticionFalsa(url))

    def wait_for_timeout(self, _ms: int) -> None:
        pass

    def evaluate(self, guion: str, arg: dict) -> dict | None:
        self.evaluaciones.append((guion, arg))
        return self._resultado_eval


class _ContextoFalso:
    def __init__(self, pages: list[_PaginaFalsa]) -> None:
        self.pages = pages


class _NavegadorFalso:
    def __init__(self, contextos: list[_ContextoFalso]) -> None:
        self.contexts = contextos
        self.cerrado = False

    def close(self) -> None:
        self.cerrado = True


class _ChromiumFalso:
    def __init__(self, navegador_falso: _NavegadorFalso) -> None:
        self.navegador = navegador_falso
        self.llamadas: list[tuple[str, int | None]] = []

    def connect_over_cdp(self, cdp: str, timeout: int | None = None) -> _NavegadorFalso:
        self.llamadas.append((cdp, timeout))
        return self.navegador


class _PlaywrightFalso:
    def __init__(self, navegador_falso: _NavegadorFalso) -> None:
        self.chromium = _ChromiumFalso(navegador_falso)

    def __enter__(self) -> _PlaywrightFalso:
        return self

    def __exit__(self, *_args) -> None:
        pass


def test_recorrer_ventana_elige_pagina_app_evalua_y_no_cierra() -> None:
    blanco = _PaginaFalsa("about:blank")
    esperado = _buena_descarga()
    app = _PaginaFalsa("http://127.0.0.1:8501/app/", esperado)
    nav = _NavegadorFalso([_ContextoFalso([blanco, app])])
    pw = _PlaywrightFalso(nav)

    vistas, resultado = navegador.recorrer_ventana(
        "http://127.0.0.1:9333",
        "http://127.0.0.1:8501/app",
        ["", "#/precios/catalogo"],
        "CODIGODEPRUEBA123456",
        abrir_playwright=lambda: pw,
    )

    assert pw.chromium.llamadas == [("http://127.0.0.1:9333", 60_000)]
    assert blanco.visitadas == [] and blanco.evaluaciones == []
    assert app.visitadas == [
        "http://127.0.0.1:8501/app/",
        "http://127.0.0.1:8501/app/#/precios/catalogo",
    ]
    assert vistas == app.visitadas
    assert resultado == esperado
    assert len(app.evaluaciones) == 1
    guion, arg = app.evaluaciones[0]
    assert guion == navegador.GUION_DESCARGA
    assert arg["codigo"] == "CODIGODEPRUEBA123456"
    assert cuentas.validar_login(arg["usuario"]) == arg["usuario"]
    cuentas.validar_contrasena(arg["contrasena"], arg["usuario"])
    assert not nav.cerrado


def test_recorrer_ventana_sin_codigo_no_evalua_y_devuelve_none() -> None:
    app = _PaginaFalsa("http://127.0.0.1:8501/app/", _buena_descarga())
    nav = _NavegadorFalso([_ContextoFalso([app])])
    pw = _PlaywrightFalso(nav)

    vistas, resultado = navegador.recorrer_ventana(
        "http://127.0.0.1:9333",
        "http://127.0.0.1:8501/app",
        [""],
        None,
        abrir_playwright=lambda: pw,
    )

    assert vistas == ["http://127.0.0.1:8501/app/"]
    assert app.evaluaciones == []
    assert resultado is None
    assert not nav.cerrado


def test_navegador_main_con_cdp_valida_descarga_y_limpia_codigo(
    tmp_path: Path, monkeypatch
) -> None:
    llamadas: list[tuple[str, str, list[str], str | None]] = []
    mala = {**_buena_descarga(), "firma": "NO"}

    def falso_recorrer(cdp: str, url: str, paginas: list[str], codigo: str | None):
        llamadas.append((cdp, url, paginas, codigo))
        return ["http://127.0.0.1:8501/app/"], mala

    monkeypatch.setattr(navegador, "recorrer_ventana", falso_recorrer)
    archivo_codigo = tmp_path / "codigo.txt"
    archivo_codigo.write_text("  ABCD2345EFGH6789IJKL \n", encoding="utf-8")
    salida = tmp_path / "ventana.json"

    rc_malo = navegador.main(
        [
            "--url",
            "http://127.0.0.1:8501/app/",
            "--cdp",
            "http://127.0.0.1:9333",
            "--codigo",
            str(archivo_codigo),
            "--salida",
            str(salida),
        ]
    )
    assert rc_malo == 1
    assert llamadas == [
        (
            "http://127.0.0.1:9333",
            "http://127.0.0.1:8501/app",
            ["", "#/precios/catalogo", "#/precios/simulador"],
            "ABCD2345EFGH6789IJKL",
        )
    ]
    assert json.loads(salida.read_text(encoding="utf-8"))["descarga"] == mala

    buena = _buena_descarga()
    monkeypatch.setattr(
        navegador,
        "recorrer_ventana",
        lambda *_args: (["http://127.0.0.1:8501/app/"], buena),
    )
    rc_bueno = navegador.main(
        [
            "--url",
            "http://127.0.0.1:8501/app",
            "--cdp",
            "http://127.0.0.1:9333",
            "--codigo",
            str(archivo_codigo),
            "--salida",
            str(salida),
        ]
    )
    assert rc_bueno == 0
    assert json.loads(salida.read_text(encoding="utf-8"))["descarga"] == buena


def test_guion_descarga_apunta_a_rutas_reales_de_la_api() -> None:
    from api.main import app

    # el esquema y no `app.routes`: los routers incluidos no exponen `path` en esa lista
    rutas = set(app.openapi()["paths"])
    for esperada in (
        "/v1/primer-arranque/reclamo",
        "/v1/admin/instalacion/respaldos",
        "/v1/admin/instalacion/respaldos/{nombre}",
    ):
        assert esperada in rutas
        assert esperada.replace("/{nombre}", "") in navegador.GUION_DESCARGA
    assert "X-Silice-CSRF" in navegador.GUION_DESCARGA
    assert "same-origin" in navegador.GUION_DESCARGA


def test_humo_cubre_ventana_por_cdp_sin_contaminar_iniciar_silice() -> None:
    texto = HUMO.read_text(encoding="utf-8-sig")
    paso6 = texto.index("Paso '6.")
    paso6b = texto.index("Paso '6b.")
    paso7 = texto.index("Paso '7.")
    assert paso6 < paso6b < paso7
    bloque = texto[paso6b:paso7]
    for pieza in (
        "--cdp",
        "codigo_instalacion.txt",
        "CloseMainWindow",
        "WaitForExit",
        r"estado\servidor.json",
        "Se cerró la ventana de Sílice",
        "puerto de depuración",
    ):
        assert pieza in bloque, pieza
    iniciar_ventana = _funcion_del_humo("IniciarVentana")
    assert "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS" in iniciar_ventana
    # solo la hereda ese proceso: se quita en el `finally`, también si Start-Process falla
    despues_finally = iniciar_ventana[iniciar_ventana.index("finally") :]
    assert re.search(r"Remove-Item[^\n]*Env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", despues_finally)
    assert "--sin-navegador" not in iniciar_ventana
    assert "Hidden" not in iniciar_ventana
    # sin consola propia: con una, `MainWindowHandle` y `CloseMainWindow()` podrían ser los de la
    # consola (Windows la atribuye al proceso) y no los de la ventana «Sílice»
    assert "-NoNewWindow" in iniciar_ventana
    # Python con la salida en archivo la guarda en búfer: los textos del lanzador se leen cuando
    # ya terminó (`WaitForExit`), no mientras la ventana sigue abierta
    # el puerto CDP lo da Windows (puerto 0): uno fijo puede caer en un rango reservado de
    # Hyper-V y Chromium no lo abre sin avisar (1.ª corrida en windows-2025, ECONNREFUSED 9333)
    assert "9333" not in texto
    assert "PuertoLibre" in bloque
    assert "TcpListener" in _funcion_del_humo("PuertoLibre")
    # si CDP no responde, deja el diagnóstico: la orden de WebView2 y los puertos reservados
    assert "msedgewebview2" in bloque and "excludedportrange" in bloque
    # 2.ª y 3.ª corrida: el runner corre ELEVADO y, desde el runtime 150, WebView2 ignora ahí la
    # variable `WEBVIEW2_*` y la política de HKCU («Develop secure WebView2 apps», Microsoft); solo
    # respeta la de máquina (HKLM). Valor con el nombre del ejecutable, solo mientras dura el paso
    # y quitado también en el `finally`
    politica = r"SOFTWARE\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments"
    assert f"$PoliticaCdp = 'HKLM:\\{politica}'" in texto
    poner, quitar = _funcion_del_humo("PonerPoliticaCdp"), _funcion_del_humo("QuitarPoliticaCdp")
    assert "$PoliticaCdp" in poner and "'python.exe'" in poner
    assert "Remove-ItemProperty -Path $PoliticaCdp -Name 'python.exe'" in quitar
    final = texto[texto.rindex("finally {") :]
    assert "QuitarPoliticaCdp" in final
    assert bloque.index("PonerPoliticaCdp") < bloque.index("IniciarVentana")
    assert bloque.index("QuitarPoliticaCdp") > bloque.index("WaitForExit")
    assert r"Policies\Microsoft\Edge" in bloque  # diagnóstico: las políticas del runner
    espera = bloque.index("WaitForExit")
    assert bloque.index("puerto de depuración") > espera
    assert bloque.index("Se cerró la ventana de Sílice") > espera
    assert "WEBVIEW2" not in _funcion_del_humo("IniciarSilice")


def test_workflow_instalador_asegura_webview2_antes_del_humo() -> None:
    flujo = (RAIZ / ".github" / "workflows" / "instalador.yml").read_text(encoding="utf-8")
    guid = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    assert guid in flujo
    assert flujo.index(guid) < flujo.index("Prueba de humo")


def test_humo_exige_un_juego_de_migracion_nuevo_tras_la_actualizacion() -> None:
    """El 6b deja un juego manual en la misma carpeta (`GUION_DESCARGA` llama a `POST
    /v1/admin/instalacion/respaldos`): «hay al menos un juego» pasaría aunque la actualización
    no respaldara. El paso 7 anota los juegos antes de actualizar y exige uno nuevo cuya ficha
    diga que es de la migración (`respaldo.MOTIVO_MIGRACION`) y que lleve la base de la 0.5.0."""
    from operacion import respaldo

    assert respaldo.MOTIVO_MIGRACION == "migracion"
    assert respaldo.NOMBRE_FICHA == "ficha.json"
    texto = HUMO.read_text(encoding="utf-8-sig")
    paso7, paso8 = texto.index("Paso '7."), texto.index("Paso '8.")
    bloque = texto[paso7:paso8]
    antes = re.search(r"\$juegosAntes = JuegosDe \$Respaldos", bloque)
    assert antes, "anota los juegos antes de actualizar"
    assert antes.start() < bloque.index("InstalarSilencioso $Actualizacion")
    assert "$juegos.Count -ge 1" not in bloque
    juegos_de = _funcion_del_humo("JuegosDe")
    assert "ficha.json" in juegos_de and "ConvertFrom-Json" in juegos_de
    nuevos = bloque.index("$juegosAntes -notcontains")
    assert nuevos > bloque.index("InstalarSilencioso $Actualizacion")
    assert "motivo -eq 'migracion'" in bloque
    assert "v050_demo.db" in bloque[nuevos:]
