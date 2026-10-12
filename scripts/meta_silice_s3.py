"""Parte S3 de la meta única de Sílice (spec S3 §13.6; plan 0.8.0, tarea 2).

`scripts/meta_silice.py` la descubre por su nombre. Con `--version 0.8.0 --hasta S3-n` evalúa,
además de las siete comprobaciones comunes (C1 a C7):

* **C1** (presencia en la ERS): en `S3-0`, UC-21 a UC-23, RF-80 a RF-89, RNF-16 y RNF-17; en
  `S3-6`, RF-100 (deseable: solo se exige si la fase se evalúa; si cae, la meta de la 0.8.0 se
  cierra en `S3-5` y RF-100 se declara no construido);
* **C3** (la prueba antes que la implementación): los pares de `PARES_S3`;
* **S3-M1** (`S3-0`): la huella SHA-256 de los dos protocolos de §13.5 y de la lista congelada
  coincide con la escrita en `docs/protocolos_s3.json`, antes de Med;
* **S3-M2** (`S3-0`): el conjunto exacto de OF-001 limpio está escrito como literal;
* **S3-M3** (`S3-1`): ningún `unsafe_allow_html` en `ui/`, `api/`, `seguridad/`, `paquete/` ni
  `auditoria/`;
* **S3-M4** (`S3-3`): la CI exige cobertura ≥ 80 % de `seguridad/` y `paquete/`;
* **S3-M5** (`S3-5`): las ramas de S3-5 y S3-6 fusionadas no tocan `core/`.
"""

from __future__ import annotations

import hashlib
import json
import runpy
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado  # noqa: E402
from scripts.meta_silice import Comprobacion, Contexto, ParTDD, Parte, _git  # noqa: E402

RUTA_HUELLAS = RAIZ / "docs" / "protocolos_s3.json"
#: Los dos protocolos de §13.5 y la lista congelada de diferencias sembradas del primero.
PROTOCOLOS = (
    "docs/protocolo_indicador_administrador.md",
    "docs/protocolo_deteccion_planos.md",
    "docs/protocolo_indicador_administrador_lista.md",
)
RUTA_LIMPIO = RAIZ / "tests" / "fixtures" / "errores_planos" / "of001_limpio.py"
RUTA_CI = RAIZ / ".github" / "workflows" / "ci.yml"
CARPETAS_SIN_HTML_INSEGURO = ("ui", "api", "seguridad", "paquete", "auditoria")
RAMAS_SIN_NUCLEO = ("inc/080-s3-5", "inc/080-s3-6")
REQUISITOS_S3_0 = (
    "UC-21", "UC-22", "UC-23", "RF-80", "RF-81", "RF-82", "RF-83", "RF-84", "RF-85", "RF-86",
    "RF-87", "RF-88", "RF-89", "RNF-16", "RNF-17",
)

#: Prueba -> implementación, por fase (C3: el commit de la prueba va antes).
PARES_S3: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_licencia_ifc.py", "docs/licencias_ifc.md", "S3-0"),
    ParTDD("tests/unit/test_documentos_s3_0.py", "docs/protocolos_s3.json", "S3-0"),
    ParTDD("tests/unit/test_meta_silice_s3.py", "scripts/meta_silice_s3.py", "S3-0"),
    ParTDD("tests/unit/test_json_estricto.py", "seguridad/json_estricto.py", "S3-1"),
    ParTDD("tests/unit/test_secretos.py", "seguridad/secretos.py", "S3-1"),
    ParTDD("tests/unit/test_permisos.py", "seguridad/permisos.py", "S3-1"),
    ParTDD("tests/unit/test_cuentas.py", "seguridad/cuentas.py", "S3-1"),
    ParTDD("tests/unit/test_sesiones.py", "seguridad/sesiones.py", "S3-1"),
    ParTDD("tests/unit/test_ui_acceso.py", "ui/acceso.py", "S3-1"),
    ParTDD("tests/unit/test_ui_marco.py", "ui/sesion.py", "S3-1"),
    ParTDD("tests/integration/test_concurrencia.py", "core/catalog/sesion.py", "S3-2"),
    ParTDD("tests/integration/test_canonico.py", "core/budget/canonico.py", "S3-2"),
    ParTDD("tests/integration/test_cadena.py", "core/budget/cadena.py", "S3-2"),
    ParTDD("tests/unit/test_comparacion.py", "core/budget/comparacion.py", "S3-2"),
    ParTDD("tests/unit/test_firma.py", "seguridad/firma.py", "S3-3"),
    ParTDD("tests/unit/test_empresas.py", "seguridad/empresas.py", "S3-3"),
    ParTDD("tests/unit/test_paquete_formato.py", "paquete/formato.py", "S3-3"),
    ParTDD("tests/unit/test_paquete_verificar.py", "paquete/verificar.py", "S3-3"),
    ParTDD("tests/unit/test_paquete_anterioridad.py", "paquete/verificar.py", "S3-3"),
    ParTDD("tests/integration/test_entrega.py", "ui/entrega.py", "S3-3"),
    ParTDD("tests/unit/test_ui_administracion.py", "ui/paginas/administracion.py", "S3-3"),
    ParTDD("tests/unit/test_ui_revision.py", "ui/revision.py", "S3-4"),
    ParTDD("tests/integration/test_revision_recibir.py", "ui/revision.py", "S3-4"),
    ParTDD("tests/unit/test_ui_revisar.py", "ui/paginas/revisar.py", "S3-4"),
    ParTDD("tests/unit/test_ui_roles.py", "ui/paginas/revisar.py", "S3-4"),
    ParTDD("tests/integration/test_api_auditorias.py", "api/rutas/auditorias.py", "S3-4"),
    ParTDD("tests/unit/test_claves_api_y_red.py", "seguridad/claves_api.py", "S3-3"),
    ParTDD("tests/unit/test_r15_geometria_plano.py",
           "adapters/espacio/planos/geometria_plano.py", "S3-5"),
    ParTDD("tests/unit/test_r16_contraste.py", "adapters/espacio/planos/contraste.py", "S3-5"),
    ParTDD("tests/unit/test_ui_contraste.py", "ui/contraste.py", "S3-5"),
    ParTDD("tests/unit/test_planos_auditoria_s3.py", "adapters/espacio/planos/ids.py", "S3-5"),
    ParTDD("tests/unit/test_deteccion_planos.py", "scripts/medir_deteccion_planos.py", "S3-5"),
    ParTDD("tests/unit/test_series_atipicas.py", "ml/anomaly/series.py", "S3-6"),
    ParTDD("tests/integration/test_atipicos.py", "ui/atipicos.py", "S3-6"),
)


# --- evaluadores puros ------------------------------------------------------------------------


def huella_de(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def evaluar_protocolos(raiz: Path, huellas: Path) -> tuple[Estado, str]:
    """S3-M1: cada protocolo de §13.5 y la lista congelada existen y su SHA-256 es el escrito en
    `protocolos_s3.json`."""
    if not huellas.is_file():
        return Estado.FALLA, f"falta {huellas.name}"
    escritas = json.loads(huellas.read_text(encoding="utf-8")).get("protocolos", {})
    malos = []
    for relativa in PROTOCOLOS:
        ruta = raiz / relativa
        if not ruta.is_file():
            malos.append(f"{relativa}: no existe")
        elif escritas.get(relativa) != huella_de(ruta):
            malos.append(f"{relativa}: la huella no coincide con la escrita")
    if malos:
        return Estado.FALLA, "; ".join(malos)
    return Estado.OK, "huella escrita de los protocolos y su lista: " + ", ".join(
        p.rpartition("/")[2] for p in PROTOCOLOS)


def evaluar_literal_of001(ruta: Path) -> tuple[Estado, str]:
    """S3-M2: el conjunto exacto de OF-001 limpio está escrito (ítems y hallazgos del DXF)."""
    if not ruta.is_file():
        return Estado.FALLA, f"falta {ruta.name}"
    dxf = runpy.run_path(str(ruta)).get("LIMPIO", {}).get("dxf") or {}
    if not dxf.get("items") or not dxf.get("hallazgos"):
        return Estado.FALLA, "el literal de OF-001 no trae los ítems y los hallazgos del DXF"
    items, hallazgos = len(dxf["items"]), len(dxf["hallazgos"])
    return Estado.OK, f"OF-001 limpio: {items} ítems y {hallazgos} hallazgos"


def evaluar_html_inseguro(raiz: Path, carpetas: Iterable[str]) -> tuple[Estado, str]:
    """S3-M3: ningún `unsafe_allow_html` en el código de las carpetas dadas."""
    usan = sorted(
        archivo.relative_to(raiz).as_posix()
        for carpeta in carpetas
        for archivo in (raiz / carpeta).rglob("*.py")
        if "unsafe_allow_html" in archivo.read_text(encoding="utf-8")
    )
    if usan:
        return Estado.FALLA, "usan unsafe_allow_html: " + ", ".join(usan)
    return Estado.OK, "ningún unsafe_allow_html en " + ", ".join(carpetas)


def evaluar_cobertura_en_ci(texto_ci: str | None) -> tuple[Estado, str]:
    """S3-M4: la CI declara el paso de cobertura de `seguridad/` y `paquete/`, mínimo 80."""
    if texto_ci is None:
        return Estado.PENDIENTE, "falta .github/workflows/ci.yml"
    pedido = all(c in texto_ci for c in ("seguridad/*", "paquete/*", "--fail-under=80"))
    if not pedido:
        return Estado.FALLA, "la CI no exige cobertura >= 80 % de seguridad/ y paquete/"
    return Estado.OK, "la CI exige cobertura >= 80 % de seguridad/ y paquete/"


def evaluar_ramas_sin_nucleo(ramas: Mapping[str, str | None]) -> tuple[Estado, str]:
    """S3-M5: `ramas` = rama -> salida de `git diff --stat` sobre `core/` (`None` si no se leyó).
    Sin ramas fusionadas no hay evidencia: PENDIENTE."""
    if not ramas:
        return Estado.PENDIENTE, "ninguna rama de S3-5 ni de S3-6 está fusionada todavía"
    sin_leer = [r for r, d in ramas.items() if d is None]
    if sin_leer:
        return Estado.PENDIENTE, "no se pudo leer el diff de: " + ", ".join(sin_leer)
    tocan = [r for r, d in ramas.items() if d and d.strip()]
    if tocan:
        return Estado.FALLA, "tocan core/: " + ", ".join(tocan)
    return Estado.OK, "no tocan core/: " + ", ".join(ramas)


# --- orquestación: git y disco ----------------------------------------------------------------


def _ramas_fusionadas() -> dict[str, str | None]:
    r = _git("log", "--first-parent", "--merges", "--format=%H|%P|%s")
    if r is None or r.returncode != 0:
        return {}
    ramas: dict[str, str | None] = {}
    for linea in r.stdout.splitlines():
        sha, _, resto = linea.partition("|")
        padres, _, asunto = resto.partition("|")
        if not any(rama in asunto for rama in RAMAS_SIN_NUCLEO):
            continue
        primero = padres.split()[0] if padres.split() else ""
        d = _git("diff", "--stat", primero, sha, "--", "core/")
        ramas[asunto] = d.stdout if d is not None and d.returncode == 0 else None
    return ramas


def _s3_m1(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_protocolos(RAIZ, RUTA_HUELLAS)


def _s3_m2(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_literal_of001(RUTA_LIMPIO)


def _s3_m3(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_html_inseguro(RAIZ, CARPETAS_SIN_HTML_INSEGURO)


def _s3_m4(_ctx: Contexto) -> tuple[Estado, str]:
    texto = RUTA_CI.read_text(encoding="utf-8") if RUTA_CI.is_file() else None
    return evaluar_cobertura_en_ci(texto)


def _s3_m5(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_ramas_sin_nucleo(_ramas_fusionadas())


PARTE = Parte(
    nombre="S3 cuentas, cadena, firma, paquete y planos",
    requisitos={"S3-0": REQUISITOS_S3_0, "S3-6": ("RF-100",)},
    pares_tdd=PARES_S3,
    comprobaciones=(
        Comprobacion("S3-M1", "Huella de los dos protocolos de §13.5", "S3-0", _s3_m1),
        Comprobacion("S3-M2", "Conjunto exacto de OF-001 limpio escrito", "S3-0", _s3_m2),
        Comprobacion("S3-M3", "Ningún unsafe_allow_html", "S3-1", _s3_m3),
        Comprobacion("S3-M4", "Cobertura de seguridad/ y paquete/ en la CI", "S3-3", _s3_m4),
        Comprobacion("S3-M5", "Las ramas de planos y anomalías no tocan core/", "S3-5", _s3_m5),
    ),
)
