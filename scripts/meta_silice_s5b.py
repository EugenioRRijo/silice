"""Parte S5 de la 1.0.0 de la meta única (spec S5 §12 y §13; plan 1.0.0, tareas 1 y 18).

`scripts/meta_silice.py` la descubre por su nombre. Con `--version 1.0.0 --hasta S5-0` exige que la
ERS defina UC-24, RF-97 a RF-99 y RNF-19 (por presencia), que RNF-08 tenga su redacción final
(S5-M1) y que la prueba de cada pieza de S5-0 sea anterior a su código. La Tarea 18 le agrega las
comprobaciones de S5-2 a S5-5 (versión, flujo, tamaños, arranque, pip-audit, clave y etiquetas).
S5-1 (RF-96, RNF-20) es de la 0.6.0 y vive en `scripts/meta_silice_s5.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from instalador.tamanos import evaluar as evaluar_tamano  # noqa: E402
from scripts.meta_alpha import Estado  # noqa: E402
from scripts.meta_silice import (  # noqa: E402
    CifraDeTiempo,
    Comprobacion,
    Contexto,
    ParTDD,
    Parte,
)

REQUISITOS_S5_0 = ("UC-24", "RF-97", "RF-98", "RF-99", "RNF-19")
#: La redacción final de RNF-08 (spec S5 §10.3, RV-23): las dos excepciones y lo que se retira.
FRASES_RNF08 = ("dos excepciones declaradas", "modo nube", "three.js", "instalador completo")
RUTA_ERS = RAIZ / "docs" / "ERS.md"
RUTA_CALIDAD = RAIZ / "docs" / "calidad_iso25010.md"

LIMITE_ARRANQUE_S = 20.0
RUTA_CLAVE = RAIZ / "operacion" / "clave_proyecto.pub"
RUTA_MANUAL = RAIZ / "docs" / "manual_instalacion.md"
RUTA_PLAN = RAIZ / "docs" / "plan_pruebas.md"
RUTAS_DEL_INSTALADOR = (
    "instalador",
    "operacion",
    "migraciones",
    "pyproject.toml",
    "uv.lock",
    ".github/workflows/instalador.yml",
)

PARES_S5B: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_meta_silice_s5b.py", "scripts/meta_silice_s5b.py", "S5-0"),
    ParTDD("tests/unit/test_documentos_s5_100.py", "docs/bitacora/2026-10-silice-100.md", "S5-0"),
    ParTDD("tests/unit/test_medir_capas.py", "instalador/medir_capas.py", "S5-0"),
    ParTDD("tests/unit/test_firma_sumas.py", "operacion/firma_sumas.py", "S5-0"),
    ParTDD("tests/unit/test_ordenes_clave.py", "operacion/ordenes_100.py", "S5-0"),
    ParTDD(
        "tests/unit/test_verificar_sumas_independiente.py", "instalador/verificar_sumas.py", "S5-0"
    ),
    ParTDD("tests/unit/test_version.py", "operacion/version.py", "S5-2"),
    ParTDD("tests/unit/test_registro.py", "operacion/registro.py", "S5-2"),
    ParTDD("tests/unit/test_verificar_version.py", "scripts/verificar_version.py", "S5-2"),
    ParTDD("tests/unit/test_red.py", "operacion/red.py", "S5-2"),
    ParTDD("tests/unit/test_lanzador.py", "operacion/lanzador.py", "S5-2"),
    ParTDD("tests/integration/test_api_clave.py", "api/proteccion.py", "S5-2"),
    ParTDD("tests/unit/test_eventos_perdidos.py", "operacion/eventos_perdidos.py", "S5-2"),
    ParTDD("tests/unit/test_ui_cliente.py", "ui/cliente.py", "S5-2"),
    ParTDD("tests/unit/test_ui_sin_cdn.py", "ui/estaticos/three.min.js", "S5-2"),
    ParTDD("tests/unit/test_ui_acerca.py", "ui/paginas/acerca.py", "S5-2"),
    ParTDD("tests/unit/test_ui_instalacion.py", "ui/paginas/instalacion.py", "S5-2"),
    ParTDD("tests/unit/test_manifiesto.py", "instalador/manifiesto.py", "S5-3"),
    ParTDD("tests/unit/test_programa.py", "operacion/programa.py", "S5-3"),
    ParTDD("tests/unit/test_construir.py", "instalador/construir.py", "S5-3"),
    ParTDD("tests/unit/test_tamanos.py", "instalador/tamanos.py", "S5-3"),
    ParTDD("tests/unit/test_licencias.py", "instalador/licencias.py", "S5-3"),
    ParTDD("tests/unit/test_iss.py", "instalador/silice.iss", "S5-3"),
    ParTDD("tests/unit/test_humo_piezas.py", "instalador/humo.ps1", "S5-4"),
    ParTDD("tests/unit/test_auditar.py", "instalador/auditar.py", "S5-4"),
    ParTDD("tests/unit/test_ci_instalador.py", ".github/workflows/instalador.yml", "S5-4"),
    ParTDD("tests/unit/test_publicar.py", "instalador/publicar.py", "S5-5"),
    ParTDD("tests/unit/test_medir_arranque.py", "scripts/medir_arranque.py", "S5-5"),
    ParTDD("tests/unit/test_manuales_s5.py", "docs/manual_instalacion.md", "S5-5"),
)
CIFRAS: tuple[CifraDeTiempo, ...] = (
    CifraDeTiempo(
        "RNF-19",
        "scripts/_salida_arranque.json",
        "mediana_s",
        "uv run python scripts/medir_arranque.py",
        "S5-5",
    ),
)


def _normal(texto: str) -> str:
    return texto.replace("\u2011", "-")


def evaluar_ers_final(ers: str | None, calidad: str | None) -> tuple[Estado, str]:
    """S5-M1: RNF-08 con su redacción final en la ERS y RNF-19 en la evaluación de calidad."""
    if ers is None or calidad is None:
        return Estado.PENDIENTE, "faltan docs/ERS.md o docs/calidad_iso25010.md"
    fila = next(
        (linea for linea in _normal(ers).splitlines() if re.match(r"^\|[^|]*\|\s*RNF-08", linea)),
        "",
    )
    faltan = [frase for frase in FRASES_RNF08 if frase not in fila]
    if "RNF-19" not in _normal(calidad):
        faltan.append("RNF-19 en docs/calidad_iso25010.md")
    if faltan:
        return Estado.FALLA, "falta: " + ", ".join(faltan)
    return Estado.OK, "RNF-08 con su redacción final y RNF-19 en la evaluación de calidad"


def evaluar_version(
    pyproject: str, api: str, operacion: str, changelog: str | None, semver: str
) -> tuple[Estado, str]:
    """S5-M5/M5a: una sola versión (pyproject = API = `operacion.version`) y, si se pide el
    CHANGELOG, su sección `## [semver] - AAAA-MM-DD`."""
    if api != pyproject:
        return Estado.FALLA, f"la API dice {api} y pyproject.toml {pyproject}"
    if operacion != pyproject:
        return Estado.FALLA, f"operacion.version dice {operacion} y pyproject.toml {pyproject}"
    if changelog is None:
        return Estado.OK, f"versión única: {pyproject}"
    if not re.search(
        rf"^## \[{re.escape(semver)}\] - \d{{4}}-\d{{2}}-\d{{2}}\s*$", changelog, re.M
    ):
        return Estado.FALLA, f"el CHANGELOG no tiene «## [{semver}] - AAAA-MM-DD»"
    return Estado.OK, f"versión única {pyproject} y sección {semver} del CHANGELOG"


def evaluar_flujo(
    ejecuciones: list[dict] | None,
    toca_despues: Callable[[str], bool],
    es_ancestro: Callable[[str], bool],
) -> tuple[Estado, str]:
    """S5-M6: hay un flujo del instalador verde sobre un commit que es ancestro de HEAD y nada
    del instalador cambió después."""
    if not ejecuciones:
        return Estado.PENDIENTE, "sin corridas de instalador.yml (¿`gh` autenticado?)"
    verdes = [
        e
        for e in ejecuciones
        if e.get("conclusion") == "success"
        and e.get("status") == "completed"
        and es_ancestro(e["headSha"])
    ]
    if not verdes:
        return Estado.FALLA, "ninguna corrida verde de instalador.yml sobre un ancestro de HEAD"
    if all(toca_despues(e["headSha"]) for e in verdes):
        return Estado.FALLA, "el instalador cambió después de su última corrida verde"
    return Estado.OK, "último flujo del instalador verde y vigente"


def evaluar_tamanos(artefactos: Mapping[str, Mapping] | None) -> tuple[Estado, str]:
    if not artefactos or not {"basico", "completo"} <= set(artefactos):
        return Estado.PENDIENTE, "faltan los tamaños de los dos perfiles (artefactos tamanos-*)"
    fuera = []
    for perfil in ("basico", "completo"):
        ok, mensaje = evaluar_tamano(perfil, int(artefactos[perfil]["bytes"]))
        if not ok:
            fuera.append(mensaje)
    if fuera:
        return Estado.FALLA, "; ".join(fuera)
    return Estado.OK, "; ".join(
        evaluar_tamano(p, int(artefactos[p]["bytes"]))[1] for p in artefactos
    )


def evaluar_arranque(datos: Mapping | None, plan_pruebas: str | None) -> tuple[Estado, str]:
    """S5-M9: la medición de RNF-19 dejó su cifra: cinco valores, mediana <= 20 s y la tabla en
    plan_pruebas §10 con fecha y los cinco valores."""
    if not datos or plan_pruebas is None:
        return (
            Estado.PENDIENTE,
            "sin scripts/_salida_arranque.json: corra scripts/medir_arranque.py",
        )
    valores = datos.get("valores_s", [])
    if len(valores) != 5 or not all(isinstance(v, (int, float)) for v in valores):
        return Estado.FALLA, f"se esperaban cinco valores y hay {valores!r}"
    if float(datos.get("mediana_s", 1e9)) > LIMITE_ARRANQUE_S:
        return Estado.FALLA, f"la mediana {datos['mediana_s']} s pasa de {LIMITE_ARRANQUE_S} s"
    texto = _normal(plan_pruebas)
    escritos = [f"{v:.2f}".replace(".", ",") for v in valores]
    if str(datos.get("fecha")) not in texto or not all(e in texto for e in escritos):
        return (
            Estado.PENDIENTE,
            "plan_pruebas §10 no trae la fecha y los cinco valores de la medición",
        )
    return (
        Estado.OK,
        f"arranque: mediana {datos['mediana_s']} s de cinco (<= {LIMITE_ARRANQUE_S} s)",
    )


def evaluar_pip_audit(archivos: Mapping[str, Mapping] | None) -> tuple[Estado, str]:
    if not archivos or not {"basico", "completo"} <= set(archivos):
        return Estado.PENDIENTE, "faltan los pip-audit de los dos perfiles"
    abiertas = [
        f"{perfil}: {v.get('paquete')} {v.get('id')}"
        for perfil, datos in archivos.items()
        for v in datos.get("abiertas", [])
    ]
    if abiertas:
        return Estado.FALLA, "vulnerabilidades abiertas: " + "; ".join(abiertas)
    return Estado.OK, "pip-audit sin vulnerabilidades abiertas en los dos perfiles"


def evaluar_clave(publica: str | None, manual: str | None) -> tuple[Estado, str]:
    """S5-CLAVE: `operacion/clave_proyecto.pub` está versionada (32 bytes en hex) y su huella
    SHA-256 aparece en el manual de instalación."""
    if publica is None:
        return Estado.FALLA, "falta operacion/clave_proyecto.pub (la ceremonia de la clave, T3)"
    try:
        crudo = bytes.fromhex(publica.strip())
    except ValueError:
        return Estado.FALLA, "clave_proyecto.pub no es hexadecimal"
    if len(crudo) != 32:
        return Estado.FALLA, f"clave_proyecto.pub mide {len(crudo)} bytes y debe medir 32"
    huella = hashlib.sha256(crudo).hexdigest()
    if manual is None or huella not in "".join(_normal(manual).split()):
        return Estado.FALLA, "el manual de instalación no trae la huella de la clave del proyecto"
    return Estado.OK, f"clave del proyecto versionada; huella {huella[:16]}… en el manual"


def evaluar_etiquetas(etiquetas: Mapping[str, str]) -> tuple[Estado, str]:
    """`v1.0-tesis` apunta al commit de una etiqueta `v1.0.x` (RS5-13), nunca a uno sin ella."""
    if "v1.0-tesis" not in etiquetas:
        return Estado.PENDIENTE, "todavía no existe v1.0-tesis"
    destino = etiquetas["v1.0-tesis"]
    semver = [t for t, c in etiquetas.items() if re.fullmatch(r"v1\.0\.\d+", t) and c == destino]
    if not semver:
        return Estado.FALLA, "v1.0-tesis no apunta al commit de ninguna etiqueta v1.0.x"
    return Estado.OK, f"v1.0-tesis = {semver[0]}"


def evaluar_trazabilidad(
    plan_pruebas: str | None, existe: Callable[[str, str | None], bool]
) -> tuple[Estado, str]:
    """Cada `archivo::prueba` (o archivo) citado en plan_pruebas §8.3 existe."""
    if plan_pruebas is None:
        return Estado.PENDIENTE, "falta docs/plan_pruebas.md"
    seccion = _normal(plan_pruebas).split("### 8.3", 1)[-1].split("\n### ", 1)[0]
    citas = re.findall(r"`(tests/[\w/.]+\.py)(?:::(\w+))?`", seccion)
    if not citas:
        return Estado.FALLA, "plan_pruebas §8.3 no cita ninguna prueba"
    faltan = [f"{a}::{p}" if p else a for a, p in citas if not existe(a, p or None)]
    if faltan:
        return Estado.FALLA, "citadas y no encontradas: " + ", ".join(sorted(set(faltan)))
    return Estado.OK, f"{len(citas)} pruebas citadas en §8.3 y todas existen"


def _gh(*argumentos: str) -> str | None:
    try:
        r = subprocess.run(
            ["gh", *argumentos], capture_output=True, text=True, check=False, cwd=RAIZ
        )
    except OSError:
        return None
    return r.stdout if r.returncode == 0 else None


def _git(*argumentos: str) -> str | None:
    r = subprocess.run(["git", *argumentos], capture_output=True, text=True, check=False, cwd=RAIZ)
    return r.stdout.strip() if r.returncode == 0 else None


def _ejecuciones() -> list[dict] | None:
    salida = _gh(
        "run",
        "list",
        "--workflow",
        "instalador.yml",
        "--limit",
        "40",
        "--json",
        "conclusion,headSha,status,databaseId,event",
    )
    return json.loads(salida) if salida else None


def _artefacto(ejecucion: int, nombre: str) -> dict | None:
    with tempfile.TemporaryDirectory() as carpeta:
        if _gh("run", "download", str(ejecucion), "-n", nombre, "-D", carpeta) is None:
            return None
        archivos = list(Path(carpeta).rglob("*.json"))
        return json.loads(archivos[0].read_text(encoding="utf-8")) if archivos else None


def _artefactos_de_perfiles(prefijo: str) -> dict[str, dict] | None:
    """Los artefactos `<prefijo>-basico` y `<prefijo>-completo` de la corrida verde más reciente
    que tenga los dos (las de un PR solo traen el básico)."""
    for e in _ejecuciones() or []:
        if e.get("conclusion") == "success" and e.get("status") == "completed":
            datos = {
                p: _artefacto(int(e["databaseId"]), f"{prefijo}-{p}")
                for p in ("basico", "completo")
            }
            if all(datos.values()):
                return datos
    return None


def _leer(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.is_file() else None


def _s5_m1(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_ers_final(_leer(RUTA_ERS), _leer(RUTA_CALIDAD))


def _m5a(_ctx: Contexto) -> tuple[Estado, str]:
    from api.main import app
    from operacion.version import a_semver, version

    return evaluar_version(version(), app.version, version(), None, a_semver(version()))


def _m5(_ctx: Contexto) -> tuple[Estado, str]:
    from api.main import app
    from operacion.version import a_semver, version

    return evaluar_version(
        version(), app.version, version(), _leer(RAIZ / "CHANGELOG.md"), a_semver(version())
    )


def _m6(_ctx: Contexto) -> tuple[Estado, str]:
    def toca_despues(sha: str) -> bool:
        return bool(_git("log", "--format=%H", f"{sha}..HEAD", "--", *RUTAS_DEL_INSTALADOR))

    def es_ancestro(sha: str) -> bool:
        return (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=RAIZ, check=False
            ).returncode
            == 0
        )

    return evaluar_flujo(_ejecuciones(), toca_despues, es_ancestro)


def _m7(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_tamanos(_artefactos_de_perfiles("tamanos"))


def _m9(_ctx: Contexto) -> tuple[Estado, str]:
    ruta = RAIZ / "scripts" / "_salida_arranque.json"
    datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else None
    return evaluar_arranque(datos, _leer(RUTA_PLAN))


def _m10(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_pip_audit(_artefactos_de_perfiles("pip-audit"))


def _clave(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_clave(_leer(RUTA_CLAVE), _leer(RUTA_MANUAL))


def _etiquetas(_ctx: Contexto) -> tuple[Estado, str]:
    salida = (
        _git(
            "for-each-ref",
            "--format=%(refname:short) %(*objectname) %(objectname)",
            "refs/tags/v1.0*",
        )
        or ""
    )
    etiquetas = {}
    for linea in salida.splitlines():
        partes_linea = linea.split()
        if partes_linea:
            etiquetas[partes_linea[0]] = (
                partes_linea[1] if len(partes_linea) == 3 else partes_linea[-1]
            )
    return evaluar_etiquetas(etiquetas)


def _traz(_ctx: Contexto) -> tuple[Estado, str]:
    def existe(archivo: str, prueba: str | None) -> bool:
        texto = _leer(RAIZ / archivo)
        return texto is not None and (prueba is None or f"def {prueba}(" in texto)

    return evaluar_trazabilidad(_leer(RUTA_PLAN), existe)


PARTE = Parte(
    nombre="S5 resto (1.0.0)",
    requisitos={"S5-0": REQUISITOS_S5_0},
    pares_tdd=PARES_S5B,
    cifras=CIFRAS,
    comprobaciones=(
        Comprobacion(
            "S5-M1", "ERS final: RNF-08 con dos excepciones y RNF-19 en calidad", "S5-0", _s5_m1
        ),
        Comprobacion("S5-M5a", "Versión única: pyproject = API = operacion.version", "S5-2", _m5a),
        Comprobacion("S5-M5", "Versión única y sección del CHANGELOG", "S5-5", _m5),
        Comprobacion("S5-M6", "Último flujo del instalador verde y vigente", "S5-5", _m6),
        Comprobacion(
            "S5-M7", "Instaladores <= 150 MB (básico) y <= 650 MB (completo)", "S5-5", _m7
        ),
        Comprobacion("S5-M9", "La medición de arranque de RNF-19 dejó su cifra", "S5-5", _m9),
        Comprobacion("S5-M10", "pip-audit sin vulnerabilidades abiertas", "S5-5", _m10),
        Comprobacion(
            "S5-CLAVE", "Clave pública del proyecto y su huella en el manual", "S5-5", _clave
        ),
        Comprobacion("S5-TRAZ", "Cada prueba de plan_pruebas §8.3 existe", "S5-5", _traz),
        Comprobacion("S5-ETIQUETAS", "v1.0-tesis = v1.0.x", "S5-5", _etiquetas),
    ),
)
