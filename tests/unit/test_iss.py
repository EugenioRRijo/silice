"""Comprobaciones estáticas de silice.iss (spec S5 §7.3; T15). La compilación real la hace la CI.

Inno Setup no está en el equipo de desarrollo (H5, bitácora 2026-10-12): aquí solo se lee el
texto, con los atajos `#define` sustituidos como lo hace ISPP.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from instalador import construir

RAIZ = Path(__file__).resolve().parents[2]
ISS = RAIZ / "instalador" / "silice.iss"
GUID = "D3E5A9C1-6B24-4F0A-8E7D-2C41B96A5F30"  # fijo para siempre: lo usa la actualización
PARAMETROS = "-E -s -B -X utf8 -m operacion"  # RP10-7


def _texto() -> str:
    """El .iss con sus atajos `#define` sustituidos, como lo ve Inno Setup."""
    texto = ISS.read_text(encoding="utf-8-sig")
    atajos = dict(re.findall(r'^#define (\w+) "(.*)"$', texto, re.M))
    for nombre, valor in atajos.items():
        texto = texto.replace("{#" + nombre + "}", valor.replace('""', '"'))
    return texto


def _secciones() -> dict[str, list[str]]:
    secciones: dict[str, list[str]] = {}
    actual = ""
    for linea in _texto().splitlines():
        if re.match(r"^\[[A-Za-z]+\]$", linea.strip()):
            actual = linea.strip()[1:-1]
            secciones[actual] = []
        elif actual and linea.strip() and not linea.strip().startswith(";"):
            secciones[actual].append(linea.strip())
    return secciones


def _sin_directivas(lineas: list[str]) -> list[str]:
    return [linea for linea in lineas if not linea.startswith("#")]


def test_ninguna_linea_pasa_de_100_columnas() -> None:
    largas = [
        n
        for n, linea in enumerate(ISS.read_text(encoding="utf-8-sig").splitlines(), 1)
        if len(linea) > 100
    ]
    assert largas == []


def test_los_atajos_se_sustituyen_todos() -> None:
    """Un `{#Nombre}` que quede sin sustituir es una variable de la línea de órdenes de ISCC."""
    restantes = set(re.findall(r"\{#(\w+)\}", _texto()))
    assert restantes == {"Version", "Sufijo", "Raiz", "Salida", "Org"}


def test_el_iss_instala_por_usuario_y_con_el_appid_fijo() -> None:
    texto = _texto()
    assert "PrivilegesRequired=lowest" in texto
    assert f"AppId={{{{{GUID}}}" in texto  # {{ escapa la llave: el AppId real es {GUID}
    assert f"{{{GUID}}}_is1" in texto  # clave de desinstalación de donde se lee la versión previa
    assert "DefaultDirName={autopf}\\Silice" in texto
    assert "MinVersion=10.0.19045" in texto and "ArchitecturesAllowed=x64compatible" in texto
    assert "Compression=lzma2/ultra64" in texto and "SolidCompression=yes" in texto
    assert "LicenseFile={#Raiz}\\LICENSE" in texto
    assert len(re.findall(r"^AppId=", texto, re.M)) == 1


def test_la_version_viene_de_la_linea_de_ordenes_y_es_obligatoria() -> None:
    texto = _texto()
    assert "AppVersion={#Version}" in texto
    assert re.search(r"^#ifndef Version\s*\n\s*#error", texto, re.M)
    # ninguna versión escrita a mano en el .iss: la pone construir.py desde pyproject
    assert not re.search(r"^AppVersion=\d", texto, re.M)


def test_el_iss_no_toca_la_carpeta_de_datos_ni_descarga_nada() -> None:
    secciones = _secciones()
    for nombre in ("Files", "InstallDelete", "UninstallDelete", "Dirs"):
        for linea in secciones.get(nombre, []):
            assert "localappdata" not in linea.lower() and "\\datos" not in linea.lower(), linea
            assert "respaldos" not in linea.lower(), linea
            assert "{userappdata}" not in linea.lower(), linea
    texto = _texto()
    assert "DownloadTemporaryFile" not in texto and "CreateDownloadPage" not in texto
    assert not re.search(r"https?://", "\n".join(sum(secciones.values(), [])))


def test_install_delete_borra_el_programa_pero_no_los_datos() -> None:
    borradas = _sin_directivas(_secciones()["InstallDelete"])
    assert borradas == [
        f'Type: filesandordirs; Name: "{{app}}\\{carpeta}"'
        for carpeta in ("python", "modulos", "codigo", "LICENCIAS")
    ]


def test_uninstall_delete_solo_borra_el_programa() -> None:
    borradas = _sin_directivas(_secciones()["UninstallDelete"])
    assert borradas == [
        f'Type: filesandordirs; Name: "{{app}}\\{carpeta}"'
        for carpeta in ("codigo", "python", "modulos")
    ]


def test_files_lleva_el_arbol_de_construir_y_el_manifiesto() -> None:
    archivos = " ".join(_secciones()["Files"])
    for origen in ("python\\*", "codigo\\*", "LICENCIAS\\*", "manifiesto.json"):
        assert f'Source: "{{#Org}}\\{origen}"' in archivos, origen
    assert "silice_similitud.pth" in archivos  # solo dentro de #ifdef Completo (abajo)


def test_los_accesos_directos_usan_las_banderas_de_aislamiento() -> None:
    iconos = _sin_directivas(_secciones()["Icons"])
    nombres = " ".join(iconos)
    for nombre in ("Sílice", "Detener Sílice", "Sílice: red local (administrador)"):
        assert f'Name: "{{autoprograms}}\\{nombre}"' in nombres
    assert len(iconos) == 4  # los tres del menú y el del escritorio (tarea opcional)
    for linea in iconos:
        assert "Filename: {app}\\python\\python.exe" in linea
        assert "WorkingDir: {app}\\codigo" in linea
        assert f'Parameters: "{PARAMETROS} ' in linea
    escritorio = next(linea for linea in iconos if "{autodesktop}" in linea)
    assert "Tasks: escritorio" in escritorio


def test_las_ordenes_de_los_accesos_son_las_de_la_cli() -> None:
    iconos = " ".join(_secciones()["Icons"])
    assert f"{PARAMETROS} arrancar" in iconos and f"{PARAMETROS} parar" in iconos
    assert f"{PARAMETROS} red-local activar" in iconos


def test_la_migracion_corre_despues_de_copiar_y_antes_de_ofrecer_abrir() -> None:
    texto = _texto()
    assert "ssPostInstall" in texto and f"{PARAMETROS} migrar" in texto
    ejecuciones = _sin_directivas(_secciones()["Run"])
    assert not any("migrar" in linea for linea in ejecuciones)  # la migración se hace en [Code]
    assert "postinstall" in ejecuciones[-1] and "skipifsilent" in ejecuciones[-1]
    assert f"{PARAMETROS} arrancar" in ejecuciones[-1]


def test_la_demostracion_se_siembra_solo_con_su_componente() -> None:
    ejecuciones = _sin_directivas(_secciones()["Run"])
    assert len(ejecuciones) == 2
    (demo,) = [linea for linea in ejecuciones if f"{PARAMETROS} demostracion" in linea]
    assert "Components: demostracion" in demo and "runhidden" in demo
    assert "Filename: {app}\\python\\python.exe" in demo and "WorkingDir: {app}\\codigo" in demo
    assert ejecuciones.index(demo) == 0  # antes de ofrecer abrir


def test_se_detiene_silice_antes_de_copiar_y_al_desinstalar() -> None:
    texto = _texto()
    assert "function PrepareToInstall" in texto and f"{PARAMETROS} parar" in texto
    desinstalar = " ".join(_secciones()["UninstallRun"])
    assert f"{PARAMETROS} parar" in desinstalar and "RunOnceId" in desinstalar


def test_bajar_de_version_pide_confirmacion_y_en_silencio_se_niega() -> None:
    texto = _texto()
    assert "function ClaveDeVersion" in texto and "function InitializeSetup" in texto
    assert "IDNO" in texto  # la respuesta por defecto de SuppressibleMsgBox es «no»
    assert "MB_DEFBUTTON2" in texto  # y el botón por defecto también es «no»


def test_el_perfil_completo_agrega_el_componente_de_similitud() -> None:
    texto = _texto()
    assert "#ifdef Completo" in texto and "similitud" in texto
    componentes = _secciones()["Components"]
    nombres = re.findall(r'^Name: "(\w+)"', "\n".join(componentes), re.M)
    assert nombres == ["programa", "demostracion", "similitud"]
    # similitud va entre #ifdef Completo y #endif; programa es fijo
    i_si, i_fin = componentes.index("#ifdef Completo"), componentes.index("#endif")
    assert i_si < next(i for i, x in enumerate(componentes) if '"similitud"' in x) < i_fin
    assert "Flags: fixed" in next(x for x in componentes if '"programa"' in x)
    assert "OutputBaseFilename=Silice-{#Version}{#Sufijo}" in texto


def test_el_sufijo_del_completo_coincide_con_el_nombre_que_espera_construir() -> None:
    texto = ISS.read_text(encoding="utf-8-sig")
    sufijo = re.search(r'#ifdef Completo\s*\n\s*#define Sufijo "([^"]*)"', texto)
    assert sufijo is not None
    for perfil, valor in (("completo", sufijo.group(1)), ("basico", "")):
        assert f"Silice-1.0.0{valor}.exe" == construir.nombre_instalador("1.0.0", perfil)


def test_el_idioma_es_espanol_y_el_archivo_es_utf8() -> None:
    assert 'MessagesFile: "compiler:Languages\\Spanish.isl"' in _texto()
    assert "Sílice" in _texto()  # el nombre visible lleva tilde: por eso construir.py agrega el BOM
    ISS.read_bytes().decode("utf-8")  # UTF-8 válido


def test_el_mensaje_de_desinstalacion_dice_donde_quedan_los_datos() -> None:
    texto = _texto()
    assert "usDone" in texto and "Sus datos quedan en" in texto and "{localappdata}" in texto


@pytest.mark.parametrize("variable", ["Version", "Org", "Raiz"])
def test_faltar_una_definicion_obligatoria_es_un_error_de_compilacion(variable: str) -> None:
    assert re.search(rf"^#ifndef {variable}\s*\n\s*#error", _texto(), re.M)


def test_las_definiciones_que_pasa_construir_son_las_que_lee_el_iss(tmp_path: Path) -> None:
    rutas = construir.Rutas(tmp_path)
    comando = construir.comando_iscc(Path("ISCC.exe"), ISS, "1.0.0", "completo", rutas)
    pasadas = {parte[2:].split("=", 1)[0] for parte in comando if parte.startswith("/D")}
    leidas = set(re.findall(r"^#ifn?def (\w+)", _texto(), re.M))
    assert pasadas == {"Version", "Completo", "Org", "Salida", "Raiz"}
    assert pasadas <= leidas


def test_el_resultado_de_migrar_queda_en_el_registro_aunque_sea_silencioso() -> None:
    """En modo silencioso `SuppressibleMsgBox` no se muestra: el código de `migrar` debe quedar en
    el registro de Inno Setup para que la prueba de humo y el soporte lo vean."""
    assert "Log('operacion migrar: codigo ' + IntToStr(Codigo))" in _texto()
