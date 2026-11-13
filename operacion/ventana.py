"""La ventana propia de Sílice (diseño 2026-11-03-ventana-de-escritorio §6; F5, 2026-11-06).

Una ventana de pywebview con WebView2 sobre la misma interfaz que sirve Uvicorn en `/app/`: misma
página, mismo origen, misma CSP, misma cookie de sesión. Es **el único módulo que importa
pywebview**, y lo importa tarde (dentro de las funciones): en Linux, en las pruebas y en un equipo
sin la capa `escritorio` nada se rompe, el lanzador abre el navegador.

Seguridad (diseño §2 y §7.2): `js_api` es un `PuenteCerrado` (ninguna función de Python a la vista
de la página, ni siquiera los atributos de `None`), sin herramientas de desarrollo, sin puerto de
depuración (`REMOTE_DEBUGGING_PORT` siempre `None`), sin `--allow-file-access-from-files`
(pywebview lo añade si no se apaga) y sin servidor HTTP propio de pywebview. Las descargas se
encienden porque `DescargaArchivo` las necesita; pywebview pregunta dónde guardar con el diálogo
de Windows.

Perfil (decisión de Eugenio del 2026-11-07, «guardar perfil en datos»; diseño §10): sin modo
privado y con el perfil de WebView2 en `<datos>/perfil_ventana` (`config.carpeta_perfil_ventana`),
para que el tamaño de letra y el zoom de la Hoja, que viven en `localStorage`, sigan ahí al volver
a abrir Sílice. La sesión no queda en ese perfil: `silice_sesion` es una cookie de sesión, sin
`Max-Age` ni `Expires` (`api.sesion_web.poner_cookie`), y se pierde al cerrar la ventana (RNF-22).
"""

from __future__ import annotations

import ctypes
import html
import importlib
import logging
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from operacion import config

logger = logging.getLogger("silice.ventana")

TITULO = "Sílice"
#: El mismo identificador va en los accesos directos de Inno Setup (`instalador/silice.iss`): así la
#: barra de tareas agrupa la ventana con el acceso «Sílice» y no con Python.
IDENTIFICADOR_APLICACION = "EugenioRijo.Silice"
#: 1056 px es el ancho más chico que la interfaz soporta (RNF-29).
TAMANO_MINIMO = (1056, 600)
PLAZO_CARGA_S = 30
ICONO = Path(__file__).with_name("silice.ico")
#: La variable propia de WebView2 que añade argumentos al navegador (y con ellos el puerto de
#: depuración). Sílice nunca la pone; el entorno de Uvicorn nunca la hereda
#: (`lanzador.entorno_hijos`). En un proceso elevado WebView2 la ignora (bitácora V0 §3.4).
VARIABLE_ARGUMENTOS_WEBVIEW2 = "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"
#: El permiso explícito para abrir la ventana aunque algo pida el puerto de depuración (decisión
#: (e) del 2026-11-12): sin él, el lanzador abre el navegador. Solo la prueba de humo lo pone.
VARIABLE_PERMITIR_DEPURACION = "SILICE_PERMITIR_DEPURACION_VENTANA"
#: La política que hace lo mismo que la variable («CreateCoreWebView2EnvironmentWithOptions»,
#: documentación de Microsoft): el cargador mira primero HKLM y luego HKCU, y en cada una un valor
#: REG_SZ con el AUMID del proceso, luego con el nombre del ejecutable y luego `*`. La prueba de
#: humo, que corre elevada, abre así el puerto de depuración (valor `python.exe` en HKLM).
POLITICA_ARGUMENTOS_WEBVIEW2 = (
    r"SOFTWARE\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments"
)
RAICES_POLITICA_WEBVIEW2 = ("HKEY_LOCAL_MACHINE", "HKEY_CURRENT_USER")
_PIDE_DEPURACION = "remote-debugging"

#: «Detect if a WebView2 Runtime is already installed» (documentación de Microsoft, vista en V0,
#: bitácora 2026-11-06-ventana-v0 §1.4): valor `pv` del cliente del runtime, por equipo (Windows de
#: 64 bits; el instalador solo admite x64) o por usuario. Vacío, nulo o 0.0.0.0 = no instalado.
CLIENTE_WEBVIEW2 = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
CLAVES_WEBVIEW2 = (
    (
        "HKEY_LOCAL_MACHINE",
        rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{CLIENTE_WEBVIEW2}",
    ),
    ("HKEY_CURRENT_USER", rf"Software\Microsoft\EdgeUpdate\Clients\{CLIENTE_WEBVIEW2}"),
)
_SIN_VERSION = frozenset({"", "0.0.0.0"})


class PuenteCerrado:
    """El `js_api` de la ventana: no tiene ningún atributo.

    pywebview resuelve lo que la página pide por `window.pywebview.api` con `getattr` encadenado
    sobre `js_api` (`webview/util.py`, `js_bridge_call`) y llama lo que encuentra. Con `None`, la
    cadena sigue por los atributos de `None` («__class__» es `NoneType`, que se puede llamar).
    Aquí todo nombre da `AttributeError`, `dir()` sale vacío y pywebview no expone ni llama nada.
    Quedan los mensajes internos de pywebview (mover la ventana, su estado, eventos del DOM), que
    no llegan a Sílice; solo los puede mandar un guion de la página, y la CSP `script-src 'self'`
    deja correr solo el de Sílice (RF-184).
    """

    __slots__ = ()

    def __getattribute__(self, nombre: str) -> Any:
        raise AttributeError(nombre)


class VentanaNoDisponible(Exception):  # noqa: N818 - es un motivo, no un error del programa
    """La ventana no se pudo abrir; el texto dice por qué (va al AVISO de la consola)."""


def _leer_valor_registro(raiz: str, clave: str, nombre: str) -> str | None:
    """El valor `nombre` de `raiz\\clave`, o `None` si no existe (o si no es Windows)."""
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(getattr(winreg, raiz), clave) as abierta:
            valor, _tipo = winreg.QueryValueEx(abierta, nombre)
    except OSError:
        return None
    return None if valor is None else str(valor)


def _leer_registro(raiz: str, clave: str) -> str | None:
    """El valor `pv` de `raiz\\clave`, o `None` si no existe (o si no es Windows)."""
    return _leer_valor_registro(raiz, clave, "pv")


def version_webview2(leer: Callable[[str, str], str | None] = _leer_registro) -> str | None:
    for raiz, clave in CLAVES_WEBVIEW2:
        valor = leer(raiz, clave)
        if valor is not None and valor.strip() not in _SIN_VERSION:
            return valor.strip()
    return None


def nombres_de_la_politica(ejecutable: str) -> tuple[str, ...]:
    """Los nombres de valor que mira WebView2 en la política, en su orden."""
    return (IDENTIFICADOR_APLICACION, ejecutable, "*")


def fuentes_puerto_depuracion(
    entorno: Mapping[str, str],
    *,
    leer: Callable[[str, str, str], str | None] = _leer_valor_registro,
    ejecutable: str | None = None,
) -> list[str]:
    """Qué pide a WebView2 un puerto de depuración para esta ventana, en palabras llanas: la
    variable y cada valor de la política que lo contiene, en el orden en que los mira Microsoft.
    Se nombran todos (la documentación no dice si la variable tapa a la política ni si HKLM tapa a
    HKCU). Lista vacía si nada lo pide; sin `winreg` (Linux) solo cuenta la variable."""
    ejecutable = ejecutable or Path(sys.executable).name
    fuentes: list[str] = []
    if _PIDE_DEPURACION in entorno.get(VARIABLE_ARGUMENTOS_WEBVIEW2, "").lower():
        fuentes.append(f"la variable {VARIABLE_ARGUMENTOS_WEBVIEW2}")
    for raiz in RAICES_POLITICA_WEBVIEW2:
        for nombre in nombres_de_la_politica(ejecutable):
            valor = leer(raiz, POLITICA_ARGUMENTOS_WEBVIEW2, nombre)
            if valor is not None and _PIDE_DEPURACION in valor.lower():
                fuentes.append(
                    f"la política {raiz}\\{POLITICA_ARGUMENTOS_WEBVIEW2} (valor «{nombre}»)"
                )
    return fuentes


def motivo_sin_ventana(
    *,
    plataforma: str = sys.platform,
    leer: Callable[[str, str], str | None] = _leer_registro,
    importar: Callable[[str], Any] = importlib.import_module,
) -> str | None:
    """`None` si este equipo puede mostrar la ventana; si no, el motivo en palabras llanas."""
    if plataforma != "win32":
        return "la ventana propia de Sílice solo existe en Windows"
    if version_webview2(leer) is None:
        return (
            "WebView2 de Microsoft no está instalado en este equipo (cómo instalarlo, en el "
            "manual de instalación, «Si falta WebView2»)"
        )
    try:
        importar("webview")
    except ImportError:
        return "falta el componente de la ventana (pywebview) en esta instalación"
    return None


def _fijar_identificador(identificador: str) -> None:
    """`SetCurrentProcessExplicitAppUserModelID`: agrupa la ventana con el acceso de Sílice."""
    shell32 = getattr(getattr(ctypes, "windll", None), "shell32", None)
    if shell32 is None:
        return
    try:
        shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(identificador))
    except (OSError, AttributeError):
        pass


def pagina_detenida() -> str:
    """Lo que muestra la ventana si Uvicorn termina con ella abierta. Sin guiones ni recursos."""
    titulo = html.escape("Sílice se detuvo")
    texto = html.escape(
        "El servidor de Sílice terminó y esta ventana ya no puede trabajar. Cierre esta ventana y "
        "vuelva a abrir Sílice. Si vuelve a pasar, el registro está en la carpeta «registros» de "
        "Sílice."
    )
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        f"<title>{titulo}</title></head>"
        "<body style=\"font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif; margin: 3rem; "
        'max-width: 40rem; color: #161616">'
        f"<h1>{titulo}</h1><p>{texto}</p></body></html>"
    )


def _configurar(motor: Any) -> None:
    ajustes = motor.settings
    ajustes["ALLOW_DOWNLOADS"] = True
    ajustes["ALLOW_FILE_URLS"] = False
    ajustes["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    ajustes["OPEN_DEVTOOLS_IN_DEBUG"] = False
    ajustes["REMOTE_DEBUGGING_PORT"] = None
    ajustes["IGNORE_SSL_ERRORS"] = False


def abrir(
    url: str,
    vivo: Callable[[], bool],
    *,
    motor: Any = None,
    perfil: Path | None = None,
    icono: Path = ICONO,
    plazo: float = PLAZO_CARGA_S,
    fijar_identificador: Callable[[str], Any] = _fijar_identificador,
    reloj: Callable[[], float] = time.monotonic,
) -> None:
    """Abre la ventana sobre `url` y **bloquea** (en el hilo principal) hasta que se cierra.

    Un hilo de pywebview vigila: si la interfaz no carga en `plazo` segundos cierra la ventana; si
    `vivo()` deja de ser cierto (Uvicorn terminó), muestra `pagina_detenida()` y deja que la persona
    la cierre. Lanza `VentanaNoDisponible` si la ventana no llegó a servir (pywebview no arranca,
    el motor no es WebView2 o la interfaz no cargó): el lanzador abre entonces el navegador.

    `perfil` es la carpeta del perfil de WebView2; por omisión, `config.carpeta_perfil_ventana()`.
    No se crea aquí: pywebview la crea, y si no puede escribir en ella falla y se abre el navegador.
    """
    perfil = perfil if perfil is not None else config.carpeta_perfil_ventana()
    motor = motor if motor is not None else importlib.import_module("webview")
    _configurar(motor)
    fijar_identificador(IDENTIFICADOR_APLICACION)
    fallos: list[str] = []
    ventana = motor.create_window(
        TITULO,
        url,
        js_api=PuenteCerrado(),
        maximized=True,
        min_size=TAMANO_MINIMO,
        text_select=True,
        zoomable=True,
    )

    def exigir_webview2(motor_web: str) -> bool:
        if motor_web != "edgechromium":
            fallos.append(f"pywebview usaría el motor «{motor_web}» en vez de WebView2")
            return False
        return True

    ventana.events.initialized += exigir_webview2

    def vigilar() -> None:
        limite = reloj() + plazo
        while not ventana.events.loaded.wait(0.5):
            if ventana.events.closed.is_set():
                return  # la persona la cerró antes de que cargara: no es un fallo
            if reloj() >= limite:
                fallos.append(f"la ventana no cargó la interfaz en {plazo:g} s")
                ventana.destroy()
                return
        while not ventana.events.closed.wait(1):
            if not vivo():
                ventana.load_html(pagina_detenida())
                return

    try:
        motor.start(
            vigilar,
            gui="edgechromium",
            debug=False,
            http_server=False,
            private_mode=False,
            storage_path=str(perfil),
            icon=str(icono) if icono.is_file() else None,
        )
    except Exception as error:  # noqa: BLE001 - cualquier fallo de pywebview o de .NET
        if ventana.events.shown.is_set():
            logger.warning("la ventana falló al cerrarse: %s", type(error).__name__)
            return
        raise VentanaNoDisponible(
            f"no se pudo abrir la ventana ({type(error).__name__}: {error})"
        ) from error
    if fallos:
        raise VentanaNoDisponible(fallos[0])


# --- Segunda ejecución: traer al frente la ventana de la instancia viva -------------------------


def _ventanas_de(pid: int, titulo: str) -> list[int]:
    """Las ventanas visibles de primer nivel del proceso `pid` con ese título (Win32)."""
    user32 = getattr(getattr(ctypes, "windll", None), "user32", None)
    if user32 is None:
        return []
    from ctypes import wintypes

    halladas: list[int] = []
    tipo = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cada(hwnd: int, _parametro: int) -> bool:
        propio = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(propio))
        if propio.value == pid and user32.IsWindowVisible(hwnd):
            largo = user32.GetWindowTextLengthW(hwnd)
            texto = ctypes.create_unicode_buffer(largo + 1)
            user32.GetWindowTextW(hwnd, texto, largo + 1)
            if texto.value == titulo:
                halladas.append(int(hwnd))
        return True

    user32.EnumWindows(tipo(cada), 0)
    return halladas


def _mostrar(hwnd: int) -> None:
    user32 = getattr(getattr(ctypes, "windll", None), "user32", None)
    if user32 is None:
        return
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)


def traer_al_frente(
    pid: int,
    *,
    buscar: Callable[[int, str], list[int]] = _ventanas_de,
    mostrar: Callable[[int], Any] = _mostrar,
) -> bool:
    """Trae al frente la ventana «Sílice» del lanzador `pid`. `False` si ese proceso no tiene
    ninguna (la instancia viva abrió el navegador): el lanzador abre entonces el navegador."""
    halladas = buscar(pid, TITULO)
    if not halladas:
        return False
    mostrar(halladas[0])
    return True
