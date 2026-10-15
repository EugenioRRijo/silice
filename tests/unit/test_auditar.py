"""pip-audit esencial con rulings que vencen (SEG-14; spec S5 §10.2; T17).

Sin red: `ejecutar` es un doble que escribe el JSON que pip-audit habría escrito. Frontera de la
fecha: un ruling vale hasta su día `hasta` incluido; al día siguiente vuelve a abrir la falla.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from instalador import auditar

LIMPIA = {"dependencies": [{"name": "alfa", "version": "1.0", "vulns": []}], "fixes": []}
CON_VULN = {
    "dependencies": [
        {"name": "alfa", "version": "1.0", "vulns": []},
        {
            "name": "beta",
            "version": "2.0",
            "vulns": [
                {
                    "id": "PYSEC-2026-1",
                    "fix_versions": ["2.1"],
                    "aliases": ["CVE-2026-0001"],
                    "description": "x",
                }
            ],
        },
        {"name": "gamma", "version": "3.0", "skip_reason": "Dependency not found on PyPI"},
    ],
    "fixes": [],
}
HOY = date(2026, 10, 11)


def _aceptadas(tmp_path: Path, cuerpo: str) -> dict[str, auditar.Aceptada]:
    ruta = tmp_path / "aceptadas.toml"
    ruta.write_text(cuerpo, encoding="utf-8")
    return auditar.cargar_aceptadas(ruta)


def test_vulnerabilidades_lista_paquete_version_id_y_alias() -> None:
    assert auditar.vulnerabilidades(CON_VULN) == [
        {
            "paquete": "beta",
            "version": "2.0",
            "id": "PYSEC-2026-1",
            "alias": ["CVE-2026-0001"],
            "arreglo": ["2.1"],
        }
    ]
    assert auditar.vulnerabilidades({}) == []


def test_una_capa_limpia_no_tiene_nada_abierto() -> None:
    veredicto = auditar.evaluar(LIMPIA, {}, HOY)
    assert veredicto == auditar.Veredicto([], [], [], [])


def test_una_vulnerabilidad_sin_ruling_queda_abierta() -> None:
    veredicto = auditar.evaluar(CON_VULN, {}, HOY)
    assert [v["id"] for v in veredicto.abiertas] == ["PYSEC-2026-1"]
    assert veredicto.aceptadas == [] and veredicto.vencidas == []
    assert veredicto.no_auditadas == ["gamma 3.0: Dependency not found on PyPI"]


@pytest.mark.parametrize("clave", ["CVE-2026-0001", "PYSEC-2026-1"])
def test_un_ruling_vigente_la_acepta_por_id_o_por_alias(tmp_path: Path, clave: str) -> None:
    aceptadas = _aceptadas(
        tmp_path,
        f'[[aceptada]]\nid = "{clave}"\nruling = "RP10-20"\nhasta = 2026-12-31\n'
        'razon = "no se llama a la función afectada"\n',
    )
    veredicto = auditar.evaluar(CON_VULN, aceptadas, HOY)
    assert veredicto.abiertas == [] and veredicto.vencidas == []
    assert [(v["id"], v["ruling"]) for v in veredicto.aceptadas] == [("PYSEC-2026-1", "RP10-20")]


@pytest.mark.parametrize(
    ("hasta", "abierta"),
    [
        ("2026-10-11", False),  # el mismo día: todavía vale
        ("2026-10-10", True),  # el día anterior: vencido
    ],
)
def test_un_ruling_vencido_vuelve_a_abrir_la_vulnerabilidad(
    tmp_path: Path, hasta: str, abierta: bool
) -> None:
    aceptadas = _aceptadas(
        tmp_path,
        f'[[aceptada]]\nid = "PYSEC-2026-1"\nruling = "RP10-20"\nhasta = {hasta}\nrazon = "x"\n',
    )
    veredicto = auditar.evaluar(CON_VULN, aceptadas, HOY)
    esperado = ["PYSEC-2026-1"] if abierta else []
    assert [v["id"] for v in veredicto.abiertas] == esperado
    assert [v["id"] for v in veredicto.vencidas] == esperado
    assert [v["id"] for v in veredicto.aceptadas] == ([] if abierta else ["PYSEC-2026-1"])


def test_un_ruling_de_otra_vulnerabilidad_no_cubre_esta(tmp_path: Path) -> None:
    aceptadas = _aceptadas(
        tmp_path,
        '[[aceptada]]\nid = "CVE-2026-9999"\nruling = "RP10-20"\nhasta = 2026-12-31\nrazon = "x"\n',
    )
    assert [v["id"] for v in auditar.evaluar(CON_VULN, aceptadas, HOY).abiertas] == ["PYSEC-2026-1"]


@pytest.mark.parametrize("falta", ["id", "ruling", "hasta", "razon"])
def test_una_excepcion_sin_ruling_o_sin_fecha_es_invalida(tmp_path: Path, falta: str) -> None:
    campos = {"id": '"X-1"', "ruling": '"RP10-20"', "hasta": "2026-12-31", "razon": '"porque"'}
    del campos[falta]
    with pytest.raises(ValueError, match=falta):
        _aceptadas(tmp_path, "[[aceptada]]\n" + "\n".join(f"{k} = {v}" for k, v in campos.items()))


@pytest.mark.parametrize("hasta", ['"2026-12-31"', "2026-12-31T10:00:00"])
def test_una_fecha_entre_comillas_o_con_hora_no_es_una_fecha(tmp_path: Path, hasta: str) -> None:
    """`hasta = "2026-12-31"` es texto en TOML y `2026-12-31T10:00:00` una fecha con hora: sin
    validarlos, `evaluar` reventaba con TypeError al compararlos con la fecha de hoy en vez de
    decir qué excepción está mal escrita."""
    with pytest.raises(ValueError, match="hasta"):
        _aceptadas(
            tmp_path,
            f'[[aceptada]]\nid = "X-1"\nruling = "RP10-20"\nhasta = {hasta}\nrazon = "x"\n',
        )


def test_el_archivo_de_aceptadas_del_repositorio_es_valido_y_empieza_vacio() -> None:
    assert auditar.cargar_aceptadas(auditar.RUTA_ACEPTADAS) == {}


def test_sin_archivo_de_aceptadas_no_hay_excepciones(tmp_path: Path) -> None:
    assert auditar.cargar_aceptadas(tmp_path / "no_existe.toml") == {}


def test_fusionar_une_capas_sin_duplicar_paquetes() -> None:
    otra = {
        "dependencies": [
            {"name": "alfa", "version": "1.0", "vulns": []},
            {"name": "delta", "version": "4.0", "vulns": []},
        ],
        "fixes": [],
    }
    nombres = [d["name"] for d in auditar.fusionar([LIMPIA, otra])["dependencies"]]
    assert sorted(nombres) == ["alfa", "delta"]


def test_fusionar_conserva_la_misma_vulnerabilidad_una_sola_vez() -> None:
    unido = auditar.fusionar([CON_VULN, CON_VULN])
    assert [v["id"] for v in auditar.vulnerabilidades(unido)] == ["PYSEC-2026-1"]


def test_main_escribe_el_json_y_sale_con_1_si_hay_algo_abierto(tmp_path: Path) -> None:
    requisitos = tmp_path / "req.txt"
    requisitos.write_text("beta==2.0\n", encoding="utf-8")
    salida = tmp_path / "pip-audit.json"

    def ejecutar(orden, **k):
        destino = Path(orden[orden.index("--output") + 1])
        destino.write_text(json.dumps(CON_VULN), encoding="utf-8")
        return 1  # pip-audit sale con 1 si encontró vulnerabilidades, pero escribe el JSON

    codigo = auditar.main(
        ["--capa", f"basica={requisitos}", "--salida", str(salida)], ejecutar=ejecutar
    )
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert codigo == 1 and datos["pip_audit"] == auditar.PIP_AUDIT
    assert [v["id"] for v in datos["abiertas"]] == ["PYSEC-2026-1"] and "fecha" in datos
    assert datos["capas"] == ["basica"] and datos["dependencias"] == 3
    assert datos["no_auditadas"] == ["gamma 3.0: Dependency not found on PyPI"]


def test_main_con_dos_capas_limpias_sale_con_0(tmp_path: Path) -> None:
    salida = tmp_path / "pip-audit.json"
    vistas: list[str] = []

    def ejecutar(orden, **k):
        vistas.append(orden[orden.index("-r") + 1])
        Path(orden[orden.index("--output") + 1]).write_text(json.dumps(LIMPIA), encoding="utf-8")
        return 0

    argumentos = ["--capa", "basica=a.txt", "--capa", "similitud=b.txt", "--salida", str(salida)]
    assert auditar.main(argumentos, ejecutar=ejecutar) == 0
    assert vistas == ["a.txt", "b.txt"]
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["capas"] == ["basica", "similitud"] and datos["abiertas"] == []


def test_sin_json_de_pip_audit_la_auditoria_no_ocurrio(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="no produjo resultado"):
        auditar.auditar_capa(tmp_path / "req.txt", ejecutar=lambda orden, **k: 2)


def test_la_orden_de_pip_audit_no_resuelve_ni_instala_nada(tmp_path: Path) -> None:
    visto: list[list[str]] = []

    def ejecutar(orden, **k):
        visto.append(list(orden))
        Path(orden[orden.index("--output") + 1]).write_text(json.dumps(LIMPIA), encoding="utf-8")
        return 0

    assert auditar.auditar_capa(tmp_path / "req.txt", ejecutar=ejecutar) == LIMPIA
    (orden,) = visto
    assert orden[:6] == [
        "uv",
        "tool",
        "run",
        "--from",
        f"pip-audit=={auditar.PIP_AUDIT}",
        "pip-audit",
    ]
    assert orden[orden.index("-r") + 1] == str(tmp_path / "req.txt")
    assert "--no-deps" in orden and "--disable-pip" in orden
    assert orden[orden.index("--format") + 1] == "json"
    assert auditar.PIP_AUDIT == "2.9.0"  # versión exacta, no un rango
