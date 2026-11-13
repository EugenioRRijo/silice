"""La ventana propia de Sílice (diseño 2026-11-03-ventana-de-escritorio §6 y §7.3; V2).

Ningún WebView2 real: pywebview se sustituye por un doble con la misma forma (`settings` que no
admite claves nuevas, `create_window`, `start`, los eventos `initialized`, `shown`, `loaded` y
`closed`). Los nombres de los ajustes del doble son los de pywebview 6.2.1 leídos en su código
(`webview/__init__.py`, `settings`), escritos aquí a mano: si la ventana pusiera uno que no existe,
el doble falla igual que el de verdad.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

from operacion import ventana

URL = "http://127.0.0.1:8501/app/"
CLIENTE = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
MAQUINA = rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{CLIENTE}"
USUARIO = rf"Software\Microsoft\EdgeUpdate\Clients\{CLIENTE}"


# --- WebView2: la clave de registro que da la documentación de Microsoft (bitácora V0 §1.4) -----


def _registro(valores: dict[tuple[str, str], str | None]) -> Callable[[str, str], str | None]:
    return lambda raiz, clave: valores.get((raiz, clave))


def test_las_claves_de_webview2_son_las_de_la_documentacion() -> None:
    assert ventana.CLAVES_WEBVIEW2 == (
        ("HKEY_LOCAL_MACHINE", MAQUINA),
        ("HKEY_CURRENT_USER", USUARIO),
    )


@pytest.mark.parametrize(
    ("valores", "esperada"),
    [
        ({("HKEY_LOCAL_MACHINE", MAQUINA): "156.0.4314.58"}, "156.0.4314.58"),
        ({("HKEY_CURRENT_USER", USUARIO): "141.0.1.2"}, "141.0.1.2"),  # instalación por usuario
        ({("HKEY_LOCAL_MACHINE", MAQUINA): "0.0.0.0"}, None),
        ({("HKEY_LOCAL_MACHINE", MAQUINA): ""}, None),
        ({("HKEY_LOCAL_MACHINE", MAQUINA): None}, None),
        ({}, None),
        (
            {("HKEY_LOCAL_MACHINE", MAQUINA): "0.0.0.0", ("HKEY_CURRENT_USER", USUARIO): "141.0"},
            "141.0",
        ),
    ],
)
def test_version_de_webview2(valores, esperada) -> None:
    assert ventana.version_webview2(leer=_registro(valores)) == esperada


def test_sin_windows_no_hay_ventana() -> None:
    motivo = ventana.motivo_sin_ventana(
        plataforma="linux", leer=_registro({}), importar=lambda nombre: object()
    )
    assert motivo is not None and "Windows" in motivo


def test_sin_webview2_no_hay_ventana_y_el_motivo_lo_dice() -> None:
    motivo = ventana.motivo_sin_ventana(
        plataforma="win32", leer=_registro({}), importar=lambda nombre: object()
    )
    assert motivo is not None and "WebView2" in motivo


def test_sin_pywebview_no_hay_ventana() -> None:
    def importar(nombre: str) -> object:
        raise ImportError(nombre)

    motivo = ventana.motivo_sin_ventana(
        plataforma="win32",
        leer=_registro({("HKEY_LOCAL_MACHINE", MAQUINA): "156.0.4314.58"}),
        importar=importar,
    )
    assert motivo is not None and "pywebview" in motivo


def test_con_webview2_y_pywebview_hay_ventana() -> None:
    importados: list[str] = []

    def importar(nombre: str) -> object:
        importados.append(nombre)
        return object()

    assert (
        ventana.motivo_sin_ventana(
            plataforma="win32",
            leer=_registro({("HKEY_LOCAL_MACHINE", MAQUINA): "156.0.4314.58"}),
            importar=importar,
        )
        is None
    )
    assert importados == ["webview"]


def test_leer_el_registro_de_una_clave_que_no_existe_da_none() -> None:
    """En Windows abre el registro de verdad; en otro sistema no hay `winreg`: los dos, `None`."""
    assert ventana._leer_registro("HKEY_CURRENT_USER", r"Software\Silice\NoExiste\{0}") is None


# --- El puerto de depuración: variable y políticas de WebView2 (diseño §7.2, enmienda 2026-11-12) -

POLITICA = r"SOFTWARE\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments"
PIDE = "--remote-debugging-port=9222"


def _politicas(
    valores: dict[tuple[str, str], str | None],
) -> Callable[[str, str, str], str | None]:
    """Un registro de mentira: `(raíz, nombre del valor)` dentro de la clave de la política."""

    def leer(raiz: str, clave: str, nombre: str) -> str | None:
        assert clave == POLITICA
        return valores.get((raiz, nombre))

    return leer


def test_la_politica_es_la_de_la_documentacion_de_microsoft() -> None:
    """«CreateCoreWebView2EnvironmentWithOptions»: primero HKLM y luego HKCU; el nombre del valor
    es el AUMID del proceso, luego el nombre del ejecutable y luego `*`."""
    assert ventana.POLITICA_ARGUMENTOS_WEBVIEW2 == POLITICA
    assert ventana.RAICES_POLITICA_WEBVIEW2 == ("HKEY_LOCAL_MACHINE", "HKEY_CURRENT_USER")
    assert ventana.nombres_de_la_politica("python.exe") == (
        ventana.IDENTIFICADOR_APLICACION,
        "python.exe",
        "*",
    )


def test_sin_variable_ni_politica_no_hay_fuentes() -> None:
    assert ventana.fuentes_puerto_depuracion({}, leer=_politicas({}), ejecutable="python.exe") == []


def test_la_variable_es_una_fuente() -> None:
    fuentes = ventana.fuentes_puerto_depuracion(
        {"WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": PIDE},
        leer=_politicas({}),
        ejecutable="python.exe",
    )
    assert fuentes == ["la variable WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"]


def test_una_variable_sin_depuracion_no_es_fuente() -> None:
    fuentes = ventana.fuentes_puerto_depuracion(
        {"WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": "--lang=es"},
        leer=_politicas({("HKEY_LOCAL_MACHINE", "python.exe"): "--disable-gpu"}),
        ejecutable="python.exe",
    )
    assert fuentes == []


@pytest.mark.parametrize("raiz", ["HKEY_LOCAL_MACHINE", "HKEY_CURRENT_USER"])
@pytest.mark.parametrize("nombre", ["EugenioRijo.Silice", "pythonw.exe", "*"])
def test_cada_raiz_y_cada_nombre_de_la_politica_es_una_fuente(raiz: str, nombre: str) -> None:
    fuentes = ventana.fuentes_puerto_depuracion(
        {},
        leer=_politicas({(raiz, nombre): f"--lang=es {PIDE.upper()}"}),
        ejecutable="pythonw.exe",
    )
    assert fuentes == [f"la política {raiz}\\{POLITICA} (valor «{nombre}»)"]


def test_un_valor_con_el_nombre_de_otro_ejecutable_no_es_fuente() -> None:
    fuentes = ventana.fuentes_puerto_depuracion(
        {},
        leer=_politicas({("HKEY_LOCAL_MACHINE", "msedge.exe"): PIDE}),
        ejecutable="python.exe",
    )
    assert fuentes == []


def test_se_nombran_todas_las_fuentes_en_el_orden_de_microsoft() -> None:
    fuentes = ventana.fuentes_puerto_depuracion(
        {"WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": PIDE},
        leer=_politicas(
            {("HKEY_CURRENT_USER", "*"): PIDE, ("HKEY_LOCAL_MACHINE", "python.exe"): PIDE}
        ),
        ejecutable="python.exe",
    )
    assert fuentes == [
        "la variable WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
        f"la política HKEY_LOCAL_MACHINE\\{POLITICA} (valor «python.exe»)",
        f"la política HKEY_CURRENT_USER\\{POLITICA} (valor «*»)",
    ]


def test_por_omision_el_ejecutable_es_el_de_este_proceso() -> None:
    vistos: list[str] = []

    def leer(_raiz: str, _clave: str, nombre: str) -> str | None:
        vistos.append(nombre)
        return None

    ventana.fuentes_puerto_depuracion({}, leer=leer)
    assert Path(sys.executable).name in vistos


def test_leer_un_valor_de_una_clave_que_no_existe_da_none() -> None:
    """En Windows abre el registro de verdad; en Linux (sin `winreg`) no falla: `None`."""
    assert (
        ventana._leer_valor_registro(
            "HKEY_LOCAL_MACHINE", r"SOFTWARE\Silice\NoExiste\{0}", "python.exe"
        )
        is None
    )


def test_sin_winreg_las_fuentes_por_omision_no_fallan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Como en Linux: `import winreg` da `ImportError` y solo cuenta la variable."""
    import builtins

    importar = builtins.__import__

    def sin_winreg(nombre: str, *args, **kwargs):
        if nombre == "winreg":
            raise ImportError(nombre)
        return importar(nombre, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", sin_winreg)
    assert ventana.fuentes_puerto_depuracion({}) == []
    assert ventana.fuentes_puerto_depuracion({"WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": PIDE}) == [
        "la variable WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"
    ]


# --- El doble de pywebview -------------------------------------------------------------------

#: Las claves de `webview.settings` de pywebview 6.2.1 (copiadas a mano de su código).
CLAVES_DE_PYWEBVIEW = {
    "ALLOW_DOWNLOADS": False,
    "ALLOW_FILE_URLS": True,
    "DRAG_REGION_SELECTOR": ".pywebview-drag-region",
    "DRAG_REGION_DIRECT_TARGET_ONLY": False,
    "DEFAULT_HTTP_PORT": 42001,
    "OPEN_EXTERNAL_LINKS_IN_BROWSER": True,
    "OPEN_DEVTOOLS_IN_DEBUG": True,
    "REMOTE_DEBUGGING_PORT": None,
    "IGNORE_SSL_ERRORS": False,
    "SHOW_DEFAULT_MENUS": True,
}


class AjustesSinClavesNuevas(dict):
    def __setitem__(self, clave, valor) -> None:
        if clave not in self:
            raise KeyError(f"pywebview no tiene el ajuste {clave}")
        super().__setitem__(clave, valor)


class Evento:
    def __init__(self) -> None:
        self.puesto = False
        self.manejadores: list[Callable[..., object]] = []

    def set(self) -> None:
        self.puesto = True

    def is_set(self) -> bool:
        return self.puesto

    def wait(self, timeout: float | None = None) -> bool:
        return self.puesto

    def __iadd__(self, manejador):
        self.manejadores.append(manejador)
        return self


class VentanaDoble:
    def __init__(self) -> None:
        self.events = SimpleNamespace(
            initialized=Evento(), shown=Evento(), loaded=Evento(), closed=Evento()
        )
        self.html: list[str] = []
        self.destruida = False

    def load_html(self, html: str, *_a) -> None:
        self.html.append(html)

    def destroy(self) -> None:
        self.destruida = True
        self.events.closed.set()


class Motor:
    """`guion(ventana)` hace lo que pasaría con la ventana abierta, antes de la vigilancia."""

    def __init__(
        self,
        guion: Callable[[VentanaDoble], None] | None = None,
        *,
        renderer: str = "edgechromium",
        falla: BaseException | None = None,
        falla_despues: BaseException | None = None,
    ) -> None:
        self.settings = AjustesSinClavesNuevas(CLAVES_DE_PYWEBVIEW)
        self.creadas: list[tuple[str, str, dict]] = []
        self.arranques: list[dict] = []
        self.guion = guion or _carga_y_cierra
        self.renderer = renderer
        self.falla = falla
        self.falla_despues = falla_despues
        self.ventana: VentanaDoble | None = None

    def create_window(self, title, url=None, **opciones):
        self.creadas.append((title, url, opciones))
        self.ventana = VentanaDoble()
        return self.ventana

    def start(self, func=None, *args, **opciones) -> None:
        self.arranques.append(opciones)
        if self.falla is not None:
            raise self.falla
        assert self.ventana is not None
        if any(m(self.renderer) is False for m in self.ventana.events.initialized.manejadores):
            return  # pywebview no crea la ventana si `initialized` devuelve False
        self.ventana.events.shown.set()
        self.guion(self.ventana)
        if func is not None:
            func()
        self.ventana.events.closed.set()  # la persona la cierra
        if self.falla_despues is not None:
            raise self.falla_despues


def _carga_y_cierra(v: VentanaDoble) -> None:
    v.events.loaded.set()
    v.events.closed.set()


#: El perfil de WebView2 de las pruebas (nunca se crea: el doble no escribe nada).
PERFIL = Path(__file__).parent / "no_se_crea" / "perfil_ventana"


def _abrir(motor: Motor, vivo: Callable[[], bool] = lambda: True, **extra) -> list[str]:
    identificadores: list[str] = []
    ventana.abrir(
        URL,
        vivo,
        motor=motor,
        perfil=extra.pop("perfil", PERFIL),
        icono=extra.pop("icono", Path(__file__)),
        fijar_identificador=identificadores.append,
        reloj=extra.pop("reloj", iter(range(10_000)).__next__),
        **extra,
    )
    return identificadores


# --- Abrir la ventana ------------------------------------------------------------------------


def test_la_ventana_carga_app_con_su_titulo_maximizada_y_sin_puente() -> None:
    motor = Motor()
    _abrir(motor)
    ((titulo, url, opciones),) = motor.creadas
    assert (titulo, url) == ("Sílice", URL)
    assert isinstance(opciones["js_api"], ventana.PuenteCerrado)  # ver «El puente cerrado» abajo
    assert opciones["maximized"] is True
    assert opciones["min_size"] == (1056, 600)
    # la persona puede seleccionar y copiar texto y ampliar con Ctrl + rueda (WCAG 1.4.4)
    assert opciones["text_select"] is True and opciones["zoomable"] is True


def test_la_ventana_arranca_sin_depuracion_ni_servidor_propio_y_con_perfil_en_datos(
    tmp_path: Path,
) -> None:
    """Decisión de Eugenio del 2026-11-07 («guardar perfil en datos»; V1 del árbitro): sin modo
    privado, con el perfil de WebView2 en la carpeta que se le da, para que el tamaño de letra y el
    zoom de la Hoja (`localStorage`) sigan ahí al volver a abrir Sílice."""
    motor = Motor()
    perfil = tmp_path / "datos" / "perfil_ventana"
    _abrir(motor, icono=Path(__file__), perfil=perfil)
    (arranque,) = motor.arranques
    assert arranque["gui"] == "edgechromium"
    assert arranque["debug"] is False
    assert arranque["http_server"] is False
    assert arranque["private_mode"] is False
    assert arranque["storage_path"] == str(perfil)
    assert arranque["icon"] == str(Path(__file__))
    assert not perfil.exists()  # la crea pywebview; si no puede escribir, falla: abre el navegador


def test_sin_perfil_explicito_la_ventana_usa_el_de_la_carpeta_de_datos(
    monkeypatch, tmp_path: Path
) -> None:
    from operacion import config

    monkeypatch.setenv(config.VARIABLE_DATOS, str(tmp_path / "datos"))
    motor = Motor()
    ventana.abrir(
        URL,
        lambda: True,
        motor=motor,
        icono=Path(__file__),
        fijar_identificador=lambda _i: None,
        reloj=iter(range(10_000)).__next__,
    )
    assert motor.arranques[0]["storage_path"] == str(
        (tmp_path / "datos").resolve() / "perfil_ventana"
    )


def test_la_cookie_de_sesion_no_sobrevive_al_cierre_aunque_el_perfil_quede_en_disco() -> None:
    """Lo que hace seguro guardar el perfil (RNF-22): `silice_sesion` es una cookie de sesión, sin
    `Max-Age` ni `Expires`; WebView2 no la escribe en el perfil y se pierde al cerrar la ventana.
    Si alguien le pusiera vencimiento, la sesión quedaría en `perfil_ventana` y esta prueba cae."""
    from fastapi import Response

    from api.sesion_web import COOKIE, poner_cookie

    respuesta = Response()
    poner_cookie(respuesta, "ficha-de-prueba")
    (galleta,) = respuesta.headers.getlist("set-cookie")
    atributos = {a.strip().split("=", 1)[0].lower() for a in galleta.split(";")[1:]}
    assert galleta.startswith(f"{COOKIE}=ficha-de-prueba;")
    assert {"max-age", "expires"} & atributos == set()


def test_los_ajustes_de_pywebview_cierran_lo_que_viene_abierto() -> None:
    motor = Motor()
    _abrir(motor)
    # pywebview añade --allow-file-access-from-files si no se apaga
    assert motor.settings["ALLOW_FILE_URLS"] is False
    assert motor.settings["ALLOW_DOWNLOADS"] is True  # DescargaArchivo (blob:) lo necesita
    assert motor.settings["REMOTE_DEBUGGING_PORT"] is None
    assert motor.settings["OPEN_DEVTOOLS_IN_DEBUG"] is False
    assert motor.settings["IGNORE_SSL_ERRORS"] is False
    assert motor.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] is True


def test_el_identificador_de_aplicacion_se_fija_antes_de_abrir() -> None:
    motor = Motor()
    assert _abrir(motor) == ["EugenioRijo.Silice"]
    assert ventana.IDENTIFICADOR_APLICACION == "EugenioRijo.Silice"


def test_sin_icono_en_disco_la_ventana_abre_igual(tmp_path: Path) -> None:
    motor = Motor()
    _abrir(motor, icono=tmp_path / "no_existe.ico")
    assert motor.arranques[0]["icon"] is None


def test_cerrar_la_ventana_devuelve_el_control() -> None:
    motor = Motor()
    _abrir(motor)
    assert motor.ventana is not None and motor.ventana.html == []
    assert motor.ventana.destruida is False


def test_si_uvicorn_muere_la_ventana_muestra_el_mensaje_y_no_queda_colgada() -> None:
    def solo_carga(v: VentanaDoble) -> None:
        v.events.loaded.set()

    motor = Motor(solo_carga)
    _abrir(motor, vivo=lambda: False)
    assert motor.ventana is not None
    (pagina,) = motor.ventana.html
    assert "Sílice se detuvo" in pagina and 'lang="es"' in pagina
    assert "vuelva a abrir Sílice" in pagina
    assert "<script" not in pagina.lower()


def test_si_la_interfaz_no_carga_en_el_plazo_se_cierra_y_se_avisa() -> None:
    """Frontera del plazo de carga (30 s) con un reloj que avanza 1 s por consulta."""

    def nunca_carga(_v: VentanaDoble) -> None:
        pass

    motor = Motor(nunca_carga)
    with pytest.raises(ventana.VentanaNoDisponible) as error:
        _abrir(motor)
    assert motor.ventana is not None and motor.ventana.destruida is True
    assert "30" in str(error.value)


def test_si_la_persona_la_cierra_antes_de_cargar_no_es_un_fallo() -> None:
    def cierra_enseguida(v: VentanaDoble) -> None:
        v.events.closed.set()

    motor = Motor(cierra_enseguida)
    _abrir(motor)  # no lanza
    assert motor.ventana is not None and motor.ventana.destruida is False


def test_con_el_motor_viejo_de_internet_explorer_no_se_abre() -> None:
    """Sin WebView2, pywebview cae a MSHTML, que no puede con la interfaz: se niega."""
    motor = Motor(renderer="mshtml")
    with pytest.raises(ventana.VentanaNoDisponible) as error:
        _abrir(motor)
    assert "mshtml" in str(error.value)
    assert motor.ventana is not None and motor.ventana.events.shown.is_set() is False


def test_si_pywebview_falla_al_arrancar_se_avisa_con_el_tipo_de_error() -> None:
    class WebViewException(Exception):  # noqa: N818 - el nombre real de pywebview
        pass

    motor = Motor(falla=WebViewException("You must have pythonnet installed"))
    with pytest.raises(ventana.VentanaNoDisponible) as error:
        _abrir(motor)
    assert "WebViewException" in str(error.value)


def test_un_error_despues_de_mostrarse_no_reabre_nada() -> None:
    """Si la ventana ya se vio y algo falla al cerrarla, no es un «no se pudo abrir»: abrir el
    navegador después de que la persona cerró la ventana sería volver a abrir Sílice."""
    motor = Motor(falla_despues=RuntimeError("al cerrar"))
    _abrir(motor)  # no lanza VentanaNoDisponible


# --- El puente cerrado (RF-184, MENOR del árbitro) ----------------------------------------------
#
# pywebview resuelve el nombre que pide la página con `getattr` encadenado sobre `js_api`
# (`webview/util.py`, `js_bridge_call`). Con `js_api=None` la cadena sigue por los atributos de
# `None`: «__class__» da `NoneType`, que pywebview llama (visto con la sonda del 2026-11-07). El
# puente cerrado responde AttributeError a todo nombre, así que no hay cadena por donde empezar.


def test_el_puente_cerrado_no_tiene_ningun_atributo() -> None:
    puente = ventana.PuenteCerrado()
    assert dir(puente) == []
    for nombre in ("__class__", "__dict__", "__init__", "abrir", "_x"):
        assert getattr(puente, nombre, None) is None


# --- Segunda ejecución: traer al frente la ventana que ya está (decisión 3, 2026-11-06) --------


def test_traer_al_frente_restaura_la_primera_ventana_de_silice_del_proceso() -> None:
    buscadas: list[tuple[int, str]] = []
    mostradas: list[int] = []

    def buscar(pid: int, titulo: str) -> list[int]:
        buscadas.append((pid, titulo))
        return [701, 702]

    assert ventana.traer_al_frente(4321, buscar=buscar, mostrar=mostradas.append) is True
    assert buscadas == [(4321, "Sílice")] and mostradas == [701]


def test_traer_al_frente_sin_ventana_de_silice_dice_que_no() -> None:
    mostradas: list[int] = []
    assert ventana.traer_al_frente(4321, buscar=lambda p, t: [], mostrar=mostradas.append) is False
    assert mostradas == []


def test_el_proceso_de_las_pruebas_no_tiene_ventanas_de_silice() -> None:
    """La búsqueda de verdad (Windows) o su ausencia (otro sistema) no encuentra nada aquí."""
    assert ventana._ventanas_de(os.getpid(), "Sílice") == []
