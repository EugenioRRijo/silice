"""Parte S5 de la 1.0.0 en la meta única (plan 1.0.0, tareas 1 y 18)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts import meta_silice_s5b as m
from scripts.meta_alpha import Estado
from scripts.meta_silice import FASES, partes, validar_partes

RAIZ = Path(__file__).resolve().parents[2]
ERS_OK = (
    "| Seguridad | RNF-08 ejecución local con dos excepciones declaradas: (1) el modelo, que el "
    "instalador completo trae incluido; (2) el asistente en modo nube. La excepción de three.js "
    "se retira | medición | meta |\n"
)
CALIDAD_OK = "## 6. Portabilidad (RNF-07 y RNF-19)\n"


def test_la_parte_se_descubre_y_solo_usa_fases_de_la_1_0_0() -> None:
    todas = partes()
    assert m.PARTE in todas
    validar_partes(todas)
    usadas = {c.fase for c in m.PARTE.comprobaciones} | set(m.PARTE.requisitos)
    assert usadas <= set(FASES["1.0.0"])


def test_los_requisitos_de_la_1_0_0_se_exigen_en_s5_0() -> None:
    assert m.PARTE.requisitos == {"S5-0": ("UC-24", "RF-97", "RF-98", "RF-99", "RNF-19")}


def test_s5_m1_acepta_la_redaccion_final_de_rnf_08_y_rnf_19_en_calidad() -> None:
    assert m.evaluar_ers_final(ERS_OK, CALIDAD_OK)[0] is Estado.OK


def test_s5_m1_falla_si_falta_una_excepcion_o_rnf_19() -> None:
    estado, detalle = m.evaluar_ers_final(ERS_OK.replace("modo nube", "la nube"), CALIDAD_OK)
    assert estado is Estado.FALLA and "modo nube" in detalle
    estado, detalle = m.evaluar_ers_final(ERS_OK, "## 6. Portabilidad (RNF-07)\n")
    assert estado is Estado.FALLA and "RNF-19" in detalle


def test_s5_m1_sin_documentos_es_pendiente() -> None:
    assert m.evaluar_ers_final(None, CALIDAD_OK)[0] is Estado.PENDIENTE
    assert m.evaluar_ers_final(ERS_OK, None)[0] is Estado.PENDIENTE


def test_s5_m1_acepta_el_guion_no_separable_de_los_documentos() -> None:
    assert m.evaluar_ers_final(ERS_OK, CALIDAD_OK.replace("RNF-19", "RNF‑19"))[0] is Estado.OK


def test_los_pares_tdd_incluyen_los_de_s5_0_sobre_archivos_nuevos() -> None:
    assert "S5-0" in {p.fase for p in m.PARES_S5B}
    assert ("tests/unit/test_meta_silice_s5b.py", "scripts/meta_silice_s5b.py") in {
        (p.prueba, p.implementacion) for p in m.PARES_S5B
    }


def test_la_ers_y_la_calidad_reales_pasan_s5_m1() -> None:
    ers = (RAIZ / "docs" / "ERS.md").read_text(encoding="utf-8")
    calidad = (RAIZ / "docs" / "calidad_iso25010.md").read_text(encoding="utf-8")
    estado, detalle = m.evaluar_ers_final(ers, calidad)
    assert estado is Estado.OK, detalle


CHANGELOG = "## [Sin publicar]\n\n## [1.0.0-rc.1] - 2026-10-30\n\n- algo\n"


def test_s5_m5a_la_api_y_operacion_dan_la_version_de_pyproject() -> None:
    assert m.evaluar_version("1.0.0rc1", "1.0.0rc1", "1.0.0rc1", None, "1.0.0-rc.1")[0] is Estado.OK
    estado, detalle = m.evaluar_version("1.0.0rc1", "0.1.0", "1.0.0rc1", None, "1.0.0-rc.1")
    assert estado is Estado.FALLA and "API" in detalle


def test_s5_m5_exige_la_seccion_del_changelog_con_fecha() -> None:
    assert (
        m.evaluar_version("1.0.0rc1", "1.0.0rc1", "1.0.0rc1", CHANGELOG, "1.0.0-rc.1")[0]
        is Estado.OK
    )
    estado, detalle = m.evaluar_version(
        "1.0.0rc1", "1.0.0rc1", "1.0.0rc1", "## [Sin publicar]\n", "1.0.0-rc.1"
    )
    assert estado is Estado.FALLA and "CHANGELOG" in detalle
    sin_fecha = "## [1.0.0-rc.1]\n"
    assert (
        m.evaluar_version("1.0.0rc1", "1.0.0rc1", "1.0.0rc1", sin_fecha, "1.0.0-rc.1")[0]
        is Estado.FALLA
    )


EJECUCIONES = [
    {
        "databaseId": 3,
        "headSha": "bbb",
        "conclusion": "failure",
        "status": "completed",
        "event": "push",
    },
    {
        "databaseId": 2,
        "headSha": "aaa",
        "conclusion": "success",
        "status": "completed",
        "event": "push",
    },
]


def test_s5_m6_exige_un_flujo_verde_sin_cambios_del_instalador_despues() -> None:
    sin_cambios, con_cambios = (lambda sha: False), (lambda sha: True)
    es_ancestro = lambda sha: sha in {"aaa", "bbb"}  # noqa: E731
    assert m.evaluar_flujo(EJECUCIONES[1:], sin_cambios, es_ancestro)[0] is Estado.OK
    assert m.evaluar_flujo(EJECUCIONES[1:], con_cambios, es_ancestro)[0] is Estado.FALLA
    assert m.evaluar_flujo(EJECUCIONES[:1], sin_cambios, es_ancestro)[0] is Estado.FALLA
    assert m.evaluar_flujo(None, sin_cambios, es_ancestro)[0] is Estado.PENDIENTE
    assert m.evaluar_flujo([], sin_cambios, es_ancestro)[0] is Estado.PENDIENTE


def _tam(perfil: str, bytes_: int) -> dict:
    return {"perfil": perfil, "bytes": bytes_, "ok": True}


def test_s5_m7_exige_los_dos_perfiles_dentro_del_limite() -> None:
    ok = {"basico": _tam("basico", 120_000_000), "completo": _tam("completo", 600_000_000)}
    assert m.evaluar_tamanos(ok)[0] is Estado.OK
    pasado = {**ok, "basico": _tam("basico", 150_000_001)}
    assert m.evaluar_tamanos(pasado)[0] is Estado.FALLA
    assert m.evaluar_tamanos({"basico": ok["basico"]})[0] is Estado.PENDIENTE
    assert m.evaluar_tamanos(None)[0] is Estado.PENDIENTE


PLAN = "### Medición de arranque (RNF‑19)\n2026-10-30: 11,20; 11,40; 11,10; 11,30; 11,50 s\n"
ARRANQUE = {"mediana_s": 11.3, "valores_s": [11.2, 11.4, 11.1, 11.3, 11.5], "fecha": "2026-10-30"}


def test_s5_m9_la_medicion_dejo_su_cifra_y_esta_en_el_plan_de_pruebas() -> None:
    assert m.evaluar_arranque(ARRANQUE, PLAN)[0] is Estado.OK
    assert m.evaluar_arranque(None, PLAN)[0] is Estado.PENDIENTE
    assert m.evaluar_arranque({**ARRANQUE, "valores_s": [11.2]}, PLAN)[0] is Estado.FALLA
    assert m.evaluar_arranque({**ARRANQUE, "mediana_s": 25.0}, PLAN)[0] is Estado.FALLA
    assert m.evaluar_arranque(ARRANQUE, "sin la tabla")[0] is Estado.PENDIENTE


def test_s5_m10_pip_audit_sin_nada_abierto_en_los_dos_perfiles() -> None:
    limpio = {"abiertas": [], "vencidas": []}
    assert m.evaluar_pip_audit({"basico": limpio, "completo": limpio})[0] is Estado.OK
    sucio = {"abiertas": [{"id": "PYSEC-1", "paquete": "x"}], "vencidas": []}
    estado, detalle = m.evaluar_pip_audit({"basico": limpio, "completo": sucio})
    assert estado is Estado.FALLA and "PYSEC-1" in detalle
    assert m.evaluar_pip_audit(None)[0] is Estado.PENDIENTE


def test_s5_clave_la_publica_esta_versionada_y_su_huella_en_el_manual() -> None:
    publica = "ab" * 32
    huella = hashlib.sha256(bytes.fromhex(publica)).hexdigest()
    manual = "Huella: " + " ".join(huella[i : i + 8] for i in range(0, 64, 8))
    assert m.evaluar_clave(publica, manual)[0] is Estado.OK
    assert m.evaluar_clave(None, manual)[0] is Estado.FALLA
    assert m.evaluar_clave("zz", manual)[0] is Estado.FALLA
    assert m.evaluar_clave(publica, "sin huella")[0] is Estado.FALLA


def test_s5_etiquetas_v1_0_tesis_apunta_al_commit_de_una_etiqueta_semver() -> None:
    etiquetas = {"v1.0.0": "c1", "v1.0.0-rc.1": "c0", "v1.0-tesis": "c1"}
    assert m.evaluar_etiquetas(etiquetas)[0] is Estado.OK
    assert m.evaluar_etiquetas({**etiquetas, "v1.0-tesis": "c9"})[0] is Estado.FALLA
    assert m.evaluar_etiquetas({"v1.0.0": "c1"})[0] is Estado.PENDIENTE


def test_s5_traz_cada_prueba_citada_en_el_plan_existe() -> None:
    plan = "| RF‑97 | `tests/unit/test_x.py::test_a` y `tests/unit/test_y.py` | verde |"
    existe = lambda archivo, prueba: (  # noqa: E731
        (archivo, prueba)
        in {
            ("tests/unit/test_x.py", "test_a"),
            ("tests/unit/test_y.py", None),
        }
    )
    assert m.evaluar_trazabilidad(plan, existe)[0] is Estado.OK
    assert m.evaluar_trazabilidad(plan, lambda a, p: False)[0] is Estado.FALLA


def test_las_fases_de_cada_comprobacion_son_las_del_spec() -> None:
    fases = {c.codigo: c.fase for c in m.PARTE.comprobaciones}
    assert fases["S5-M1"] == "S5-0" and fases["S5-M5a"] == "S5-2"
    for codigo in (
        "S5-M5",
        "S5-M6",
        "S5-M7",
        "S5-M9",
        "S5-M10",
        "S5-CLAVE",
        "S5-TRAZ",
        "S5-ETIQUETAS",
    ):
        assert fases[codigo] == "S5-5", codigo
    assert {c.fase for c in m.CIFRAS} == {"S5-5"}


def test_hay_un_par_de_prueba_e_implementacion_por_cada_tarea() -> None:
    implementaciones = {p.implementacion for p in m.PARES_S5B}
    for esperado in (
        "scripts/meta_silice_s5b.py",
        "operacion/firma_sumas.py",
        "operacion/version.py",
        "operacion/registro.py",
        "operacion/lanzador.py",
        "operacion/red.py",
        "api/proteccion.py",
        "operacion/eventos_perdidos.py",
        "ui/cliente.py",
        "instalador/manifiesto.py",
        "instalador/construir.py",
        "instalador/silice.iss",
        "instalador/humo.ps1",
        "instalador/auditar.py",
        ".github/workflows/instalador.yml",
        "instalador/publicar.py",
        "operacion/ordenes_100.py",
        "instalador/verificar_sumas.py",
        "instalador/tamanos.py",
        "scripts/verificar_version.py",
    ):
        assert esperado in implementaciones, esperado
    assert all(p.fase in {"S5-0", "S5-2", "S5-3", "S5-4", "S5-5"} for p in m.PARES_S5B)
