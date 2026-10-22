"""Construcción del instalador: órdenes de uv, capas, BOM y encadenado (spec S5 §7.1; RNF-20; T14).

No se construye nada de verdad: `ejecutar` es un grabador y los pasos que tocan el disco real o a
Inno Setup se sustituyen. Desviaciones registradas en la bitácora 2026-10-silice-100 (S5-3 · T13
y T14) que esta prueba sigue:
- sin `--compile-bytecode` en las capas (`_BYTECODE = ()`): con él, el básico pasaba de 150 MB;
- `formatear_sumas` vive en `construir.py` mientras `operacion.firma_sumas` (T3) no exista;
- `--solo-carpeta` arma `build/app` sin Inno Setup.
"""

from __future__ import annotations

import hashlib
import json
import ntpath
from dataclasses import replace
from pathlib import Path

import pytest

from instalador import construir as c
from instalador.manifiesto import cargar

BASICA = "alfa==1.0 ; sys_platform == 'win32'\nBeta_Uno==2.0\n# via x\n-e .\ngamma==3.0.post1\n"
COMPLETA = (
    BASICA + "sentence-transformers==5.0.0\ntorch==2.9.0 ; sys_platform == 'win32'\nbeta-uno==2.0\n"
)


def test_paquetes_de_normaliza_nombres_y_salta_comentarios() -> None:
    assert c.paquetes_de(BASICA) == {"alfa": "1.0", "beta-uno": "2.0", "gamma": "3.0.post1"}


def test_solo_los_nuevos_quita_lo_que_la_basica_ya_trae() -> None:
    nuevos = c.solo_los_nuevos(BASICA, COMPLETA)
    assert nuevos.splitlines() == [
        "sentence-transformers==5.0.0",
        "torch==2.9.0 ; sys_platform == 'win32'",
    ]
    assert nuevos.endswith("\n")
    assert c.solo_los_nuevos(BASICA, BASICA) == ""  # nada nuevo: archivo vacío, sin salto


def test_solo_los_nuevos_no_repite_un_paquete_listado_dos_veces() -> None:
    completa = BASICA + "torch==2.9.0\nTorch==2.9.0\n"
    assert c.solo_los_nuevos(BASICA, completa).splitlines() == ["torch==2.9.0"]


def test_los_extras_del_completo_suman_similitud_y_el_ifc_solo_si_el_manifiesto_lo_pide() -> None:
    m = cargar()
    assert c.extras_de(m, similitud=False) == list(m.extras_basica)
    assert c.extras_de(m, similitud=True) == [*m.extras_basica, "similitud"]
    assert "ifc" not in c.extras_de(m, similitud=False)
    con_ifc = replace(m, ifc=True)
    assert c.extras_de(con_ifc, similitud=False) == [*m.extras_basica, "ifc"]
    assert c.extras_de(con_ifc, similitud=True)[-2:] == ["ifc", "similitud"]


class Grabador:
    def __init__(self) -> None:
        self.ordenes: list[list[str]] = []
        self.cwds: list[object] = []

    def __call__(self, orden, entorno=None, cwd=None) -> None:
        self.ordenes.append([str(p) for p in orden])
        self.cwds.append(cwd)
        if list(orden[:2]) == ["uv", "export"]:
            destino = Path(orden[orden.index("--output-file") + 1])
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(COMPLETA if "similitud" in orden else BASICA, encoding="utf-8")
        if list(orden[:3]) == ["uv", "python", "install"]:
            destino = Path(orden[orden.index("--install-dir") + 1])
            exe = destino / f"cpython-{orden[3]}-windows-x86_64-none" / "python.exe"
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"MZ")


def test_las_ordenes_de_uv_son_las_del_spec(tmp_path: Path) -> None:
    rutas, ejecutar = c.Rutas(tmp_path), Grabador()
    python = c.instalar_python("3.13.13", rutas, ejecutar)
    assert python == rutas.app / "python" / "python.exe" and python.is_file()
    assert ejecutar.ordenes[0] == [
        "uv",
        "python",
        "install",
        "3.13.13",
        "--install-dir",
        str(rutas.py),
    ]
    c.exportar(["api", "planos"], tmp_path / "req.txt", ejecutar)
    assert ejecutar.ordenes[1] == [
        "uv",
        "export",
        "--frozen",
        "--no-dev",
        "--no-emit-project",
        "--no-hashes",
        "--extra",
        "api",
        "--extra",
        "planos",
        "--output-file",
        str(tmp_path / "req.txt"),
    ]
    c.instalar_capa(python, tmp_path / "req.txt", ejecutar)
    # Sin `--compile-bytecode` (bitácora S5-3: con él, 164,2 MB comprimido > 150 MB de RNF-19)
    assert ejecutar.ordenes[2] == [
        "uv",
        "pip",
        "install",
        "--python",
        str(python),
        "--break-system-packages",
        "--no-deps",
        "-r",
        str(tmp_path / "req.txt"),
    ]
    c.instalar_similitud(python, tmp_path / "nuevos.txt", tmp_path / "paq", ejecutar)
    assert ejecutar.ordenes[3] == [
        "uv",
        "pip",
        "install",
        "--python",
        str(python),
        "--target",
        str(tmp_path / "paq"),
        "--no-deps",
        "-r",
        str(tmp_path / "nuevos.txt"),
    ]
    # ninguna orden resuelve: todas parten del candado o de una lista fija sin dependencias
    assert all("--no-deps" in o for o in ejecutar.ordenes if o[:3] == ["uv", "pip", "install"])


def test_el_codigo_propio_si_se_compila(tmp_path: Path) -> None:
    ejecutar = Grabador()
    c.compilar(tmp_path / "python.exe", tmp_path / "codigo", ejecutar)
    assert ejecutar.ordenes == [
        [
            str(tmp_path / "python.exe"),
            "-m",
            "compileall",
            "-q",
            "-j",
            "0",
            str(tmp_path / "codigo"),
        ]
    ]


def test_sin_python_exe_la_construccion_falla_con_mensaje(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="uv no dejó"):
        c.instalar_python("3.13.13", c.Rutas(tmp_path), lambda *a, **k: None)


def test_las_licencias_se_reunen_con_el_python_construido_y_aislado(
    tmp_path: Path, monkeypatch
) -> None:
    ejecutar = Grabador()
    app = tmp_path / "app"
    (app / "LICENCIAS").mkdir(parents=True)
    (app / "modulos" / "similitud" / "paquetes").mkdir(parents=True)
    c.licencias(app / "python" / "python.exe", app, ejecutar)
    (orden,) = ejecutar.ordenes
    assert orden[:3] == [str(app / "python" / "python.exe"), "-E", "-s"]
    rutas = [orden[i + 1] for i, parte in enumerate(orden) if parte == "--solo-ruta"]
    assert rutas == [
        str(app / "python" / "Lib" / "site-packages"),
        str(app / "modulos" / "similitud" / "paquetes"),
    ]
    assert (app / "LICENCIAS" / "Silice-LICENSE.txt").read_bytes() == (
        (c.RAIZ / "LICENSE").read_bytes()
    )


def test_el_pth_apunta_a_modulos_similitud_desde_site_packages(tmp_path: Path) -> None:
    c.escribir_pth(tmp_path)
    linea = (tmp_path / "silice_similitud.pth").read_text(encoding="utf-8").strip()
    # lo que hace `site.addpackage` en Windows: une la línea a la carpeta del .pth y normaliza
    sitio = r"C:\Prueba\python\Lib\site-packages"
    assert ntpath.normpath(ntpath.join(sitio, linea)) == r"C:\Prueba\modulos\similitud\paquetes"


def test_el_iss_se_compila_desde_una_copia_con_bom_utf8(tmp_path: Path) -> None:
    origen = tmp_path / "silice.iss"
    origen.write_bytes("; Sílice\n[Setup]\n".encode())
    copia = c.asegurar_bom(origen, tmp_path / "build" / "silice.iss")
    datos = copia.read_bytes()
    assert datos.startswith(b"\xef\xbb\xbf") and datos[3:].decode("utf-8") == "; Sílice\n[Setup]\n"
    origen.write_bytes(b"\xef\xbb\xbf; ya trae BOM\n")
    assert c.asegurar_bom(origen, tmp_path / "otra.iss").read_bytes().count(b"\xef\xbb\xbf") == 1


def test_el_iss_del_repositorio_sale_con_un_solo_bom(tmp_path: Path) -> None:
    iss = c.RAIZ / "instalador" / "silice.iss"
    copia = c.asegurar_bom(iss, tmp_path / "silice.iss").read_bytes()
    assert copia.startswith(b"\xef\xbb\xbf") and copia.count(b"\xef\xbb\xbf") == 1
    assert copia.lstrip(b"\xef\xbb\xbf") == iss.read_bytes().lstrip(b"\xef\xbb\xbf")


def test_buscar_iscc_prueba_las_ubicaciones_conocidas(tmp_path: Path) -> None:
    pf = tmp_path / "pf86"
    exe = pf / "Inno Setup 6" / "ISCC.exe"
    entorno = {"ProgramFiles(x86)": str(pf), "PATH": ""}
    assert c.buscar_iscc(entorno, existe=lambda p: Path(p) == exe) == exe
    with pytest.raises(FileNotFoundError, match="Inno Setup"):
        c.buscar_iscc(entorno, existe=lambda p: False)


def test_buscar_iscc_prefiere_el_path_y_conoce_la_instalacion_por_usuario(tmp_path: Path) -> None:
    en_path = tmp_path / "bin" / "ISCC.exe"
    por_usuario = tmp_path / "local" / "Programs" / "Inno Setup 6" / "ISCC.exe"
    entorno = {"PATH": str(en_path.parent), "LOCALAPPDATA": str(tmp_path / "local")}
    assert c.buscar_iscc(entorno, existe=lambda p: Path(p) in {en_path, por_usuario}) == en_path
    assert c.buscar_iscc(entorno, existe=lambda p: Path(p) == por_usuario) == por_usuario


def test_el_comando_de_iscc_lleva_version_perfil_y_carpetas(tmp_path: Path) -> None:
    rutas = c.Rutas(tmp_path)
    iss = rutas.build / "silice.iss"
    comando = c.comando_iscc(Path("ISCC.exe"), iss, "1.0.0-rc.1", "completo", rutas)
    assert comando[0] == "ISCC.exe" and comando[-1].endswith("silice.iss")
    assert "/DVersion=1.0.0-rc.1" in comando and "/DCompleto" in comando
    assert "/DCompleto" not in c.comando_iscc(Path("ISCC.exe"), iss, "1.0.0", "basico", rutas)
    assert f"/DOrg={rutas.app}" in comando and f"/DSalida={rutas.salida}" in comando
    assert f"/DRaiz={tmp_path}" in comando


def test_el_nombre_del_instalador() -> None:
    assert c.nombre_instalador("1.0.0", "basico") == "Silice-1.0.0.exe"
    assert c.nombre_instalador("1.0.0-rc.1", "completo") == "Silice-1.0.0-rc.1-completo.exe"


def test_formatear_sumas_es_el_formato_de_sha256sum() -> None:
    """`<hex>  <nombre>\\n` por línea, ordenado por nombre y con LF (el de T3, duplicado aquí)."""
    datos = c.formatear_sumas({"b.txt": "2" * 64, "a.txt": "1" * 64})
    assert datos == ("1" * 64 + "  a.txt\n" + "2" * 64 + "  b.txt\n").encode("ascii")
    assert c.formatear_sumas({}) == b""


def test_las_sumas_son_sha256sum_con_saltos_de_linea_lf(tmp_path: Path) -> None:
    (tmp_path / "Silice-1.0.0.exe").write_bytes(b"instalador")
    (tmp_path / "manifiesto.json").write_bytes(b"{}")
    sumas = c.escribir_sumas(tmp_path, "basico", ["manifiesto.json", "Silice-1.0.0.exe"])
    crudo = sumas.read_bytes()
    assert sumas.name == "SHA256SUMS-basico" and b"\r" not in crudo
    assert crudo.decode().splitlines() == [
        f"{hashlib.sha256(b'instalador').hexdigest()}  Silice-1.0.0.exe",
        f"{hashlib.sha256(b'{}').hexdigest()}  manifiesto.json",
    ]


def test_el_manifiesto_json_cubre_codigo_y_python(tmp_path: Path) -> None:
    (tmp_path / "codigo" / "api").mkdir(parents=True)
    (tmp_path / "python").mkdir()
    (tmp_path / "codigo" / "api" / "main.py").write_text("x", encoding="utf-8")
    (tmp_path / "python" / "python.exe").write_bytes(b"MZ")
    (tmp_path / "python" / "otro.dll").write_bytes(b"dll")
    destino = c.escribir_manifiesto_json(tmp_path, "1.0.0")
    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert [a["ruta"] for a in datos["archivos"]] == ["codigo/api/main.py", "python/python.exe"]
    assert datos["version"] == "1.0.0"


def test_la_carpeta_reporta_sus_tamanos(tmp_path: Path) -> None:
    (tmp_path / "python").mkdir()
    (tmp_path / "codigo").mkdir()
    (tmp_path / "python" / "python.exe").write_bytes(b"x" * 1_500_000)
    (tmp_path / "codigo" / "a.py").write_bytes(b"y" * 250_000)
    assert c.tamanos_de_la_carpeta(tmp_path, "basico") == [
        "carpeta basico: 1.8 MB sin comprimir",  # 1 750 000 bytes
        "  python: 1.5 MB",
        "  codigo: 0.2 MB",  # 0,25 redondea a 0,2 (mitad a par)
    ]


def _sin_efectos(monkeypatch, pasos: list[str], tmp_path: Path) -> None:
    """Sustituye los pasos que tocan el disco real o a Inno Setup; anota cuáles se llaman."""
    for nombre in (
        "copiar_codigo",
        "compilar",
        "licencias",
        "escribir_manifiesto_json",
        "descargar_modelo",
        "escribir_pth",
    ):
        monkeypatch.setattr(c, nombre, lambda *a, _n=nombre, **k: pasos.append(_n))
    monkeypatch.setattr(c, "asegurar_bom", lambda o, d: pasos.append("bom") or d)
    monkeypatch.setattr(c, "buscar_iscc", lambda *a, **k: Path("ISCC.exe"))
    monkeypatch.setattr(c, "escribir_sumas", lambda *a, **k: pasos.append("sumas") or tmp_path)


def test_construir_encadena_los_pasos_en_el_orden_del_spec(tmp_path: Path, monkeypatch) -> None:
    pasos: list[str] = []
    _sin_efectos(monkeypatch, pasos, tmp_path)
    ejecutar = Grabador()
    rutas = c.Rutas(tmp_path)
    rutas.salida.mkdir(parents=True)
    salidas = c.construir("completo", version="1.0.0", rutas=rutas, ejecutar=ejecutar)
    verbos = [" ".join(o[:3]) for o in ejecutar.ordenes]
    assert (
        verbos.index("uv python install")
        < verbos.index("uv export --frozen")
        < verbos.index("uv pip install")
    )
    assert verbos.count("uv export --frozen") == 2 and verbos.count("uv pip install") == 2
    iscc = [o for o in ejecutar.ordenes if o[0] == "ISCC.exe"]
    assert len(iscc) == 1 and "/DCompleto" in iscc[0] and "/DVersion=1.0.0" in iscc[0]
    assert ejecutar.cwds[ejecutar.ordenes.index(iscc[0])] == c.RAIZ
    assert pasos == [
        "escribir_pth",
        "descargar_modelo",
        "copiar_codigo",
        "compilar",
        "licencias",
        "escribir_manifiesto_json",
        "bom",
        "sumas",
    ]
    # la capa de similitud solo instala lo que la básica no trae
    assert (rutas.build / "req-similitud.txt").read_text(encoding="utf-8").splitlines() == [
        "sentence-transformers==5.0.0",
        "torch==2.9.0 ; sys_platform == 'win32'",
    ]
    assert salidas[0] == rutas.salida / "Silice-1.0.0-completo.exe"


def test_el_basico_no_trae_la_capa_de_similitud(tmp_path: Path, monkeypatch) -> None:
    pasos: list[str] = []
    _sin_efectos(monkeypatch, pasos, tmp_path)
    ejecutar = Grabador()
    rutas = c.Rutas(tmp_path)
    rutas.salida.mkdir(parents=True)
    c.construir("basico", version="1.0.0", rutas=rutas, ejecutar=ejecutar)
    assert "escribir_pth" not in pasos and "descargar_modelo" not in pasos
    assert not any("--target" in orden for orden in ejecutar.ordenes)
    assert not any("similitud" in orden for orden in ejecutar.ordenes)
    assert not any(orden[0] == "ISCC.exe" and "/DCompleto" in orden for orden in ejecutar.ordenes)
    assert any(orden[0] == "ISCC.exe" for orden in ejecutar.ordenes)


def test_solo_iss_no_reconstruye_el_arbol(tmp_path: Path, monkeypatch) -> None:
    pasos: list[str] = []
    _sin_efectos(monkeypatch, pasos, tmp_path)
    ejecutar = Grabador()
    c.construir(
        "basico", version="1.0.1", solo_iss=True, rutas=c.Rutas(tmp_path), ejecutar=ejecutar
    )
    assert [o[0] for o in ejecutar.ordenes] == ["ISCC.exe"]
    assert "/DVersion=1.0.1" in ejecutar.ordenes[0]
    assert pasos == ["bom", "sumas"]


def test_solo_carpeta_arma_la_carpeta_y_no_llama_a_inno(tmp_path: Path, monkeypatch) -> None:
    pasos: list[str] = []
    _sin_efectos(monkeypatch, pasos, tmp_path)
    ejecutar = Grabador()
    rutas = c.Rutas(tmp_path)
    salidas = c.construir(
        "basico", version="1.0.0", solo_carpeta=True, rutas=rutas, ejecutar=ejecutar
    )
    assert salidas == [rutas.app]
    assert not any(o[0] == "ISCC.exe" for o in ejecutar.ordenes)
    assert pasos == ["copiar_codigo", "compilar", "licencias", "escribir_manifiesto_json"]


def test_main_solo_sumas_suma_el_instalador_el_manifiesto_y_los_extras(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    rutas = c.Rutas(tmp_path)
    rutas.salida.mkdir(parents=True)
    for nombre, contenido in (
        ("Silice-1.0.0.exe", b"exe"),
        ("manifiesto.json", b"{}"),
        ("pip-audit-basico.json", b"[]"),
    ):
        (rutas.salida / nombre).write_bytes(contenido)
    monkeypatch.setattr(c, "Rutas", lambda: rutas)
    argumentos = ["--perfil", "basico", "--version", "1.0.0", "--solo-sumas"]
    assert c.main([*argumentos, "--extra", "pip-audit-basico.json"]) == 0
    lineas = (rutas.salida / "SHA256SUMS-basico").read_text(encoding="utf-8").splitlines()
    assert [linea.split("  ", 1)[1] for linea in lineas] == [
        "Silice-1.0.0.exe",
        "manifiesto.json",
        "pip-audit-basico.json",
    ]
    assert lineas[0].split("  ")[0] == hashlib.sha256(b"exe").hexdigest()
    assert "SHA256SUMS-basico" in capsys.readouterr().out
