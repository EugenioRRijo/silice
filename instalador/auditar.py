"""`pip-audit` esencial sobre las dependencias exportadas de cada capa (SEG-14; spec S5 §10.2).

    uv run python instalador/auditar.py --capa basica=build/req-basica.txt \\
        --capa similitud=build/req-completa.txt --salida pip-audit-basico.json

Audita el candado, no el equipo: lee los `requirements` que escribió `uv export` (versiones fijas,
sin resolver ni instalar nada). Una vulnerabilidad sin ruling vigente en
`docs/pip-audit-aceptadas.toml` hace salir con 1. El JSON queda adjunto a cada versión.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PIP_AUDIT = "2.9.0"
RAIZ = Path(__file__).resolve().parents[1]
RUTA_ACEPTADAS = RAIZ / "docs" / "pip-audit-aceptadas.toml"
CAMPOS = ("id", "ruling", "hasta", "razon")


@dataclass(frozen=True, slots=True)
class Aceptada:
    id: str
    ruling: str
    hasta: date
    razon: str


@dataclass(frozen=True, slots=True)
class Veredicto:
    abiertas: list[dict]
    aceptadas: list[dict]
    vencidas: list[dict]
    no_auditadas: list[str]


def cargar_aceptadas(ruta: Path = RUTA_ACEPTADAS) -> dict[str, Aceptada]:
    datos = tomllib.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else {}
    aceptadas = {}
    for entrada in datos.get("aceptada", []):
        for campo in CAMPOS:
            if campo not in entrada:
                raise ValueError(f"{ruta.name}: una excepción no tiene «{campo}»")
        aceptadas[entrada["id"]] = Aceptada(
            entrada["id"], entrada["ruling"], entrada["hasta"], entrada["razon"]
        )
    return aceptadas


def vulnerabilidades(resultado: Mapping) -> list[dict]:
    halladas = []
    for dependencia in resultado.get("dependencies", []):
        for vuln in dependencia.get("vulns", []):
            halladas.append(
                {
                    "paquete": dependencia["name"],
                    "version": dependencia["version"],
                    "id": vuln["id"],
                    "alias": list(vuln.get("aliases", [])),
                    "arreglo": list(vuln.get("fix_versions", [])),
                }
            )
    return halladas


def fusionar(resultados: Sequence[Mapping]) -> dict:
    unidas: dict[tuple[str, str], dict] = {}
    for resultado in resultados:
        for dependencia in resultado.get("dependencies", []):
            unidas.setdefault((dependencia["name"], dependencia.get("version", "")), dependencia)
    return {"dependencies": list(unidas.values()), "fixes": []}


def evaluar(resultado: Mapping, aceptadas: Mapping[str, Aceptada], hoy: date) -> Veredicto:
    abiertas, aceptadas_usadas, vencidas = [], [], []
    for vuln in vulnerabilidades(resultado):
        ruling = next((aceptadas[i] for i in (vuln["id"], *vuln["alias"]) if i in aceptadas), None)
        if ruling is None:
            abiertas.append(vuln)
        elif ruling.hasta < hoy:
            abiertas.append(vuln)
            vencidas.append(vuln)
        else:
            aceptadas_usadas.append({**vuln, "ruling": ruling.ruling})
    no_auditadas = [
        f"{d['name']} {d.get('version', '?')}: {d['skip_reason']}"
        for d in resultado.get("dependencies", [])
        if "skip_reason" in d
    ]
    return Veredicto(abiertas, aceptadas_usadas, vencidas, no_auditadas)


def _ejecutar(orden: Sequence[str], **_: object) -> int:
    return subprocess.run(list(orden), check=False).returncode


def auditar_capa(requisitos: Path, ejecutar: Callable[..., int] = _ejecutar) -> dict:
    with tempfile.TemporaryDirectory() as carpeta:
        salida = Path(carpeta) / "pip-audit.json"
        ejecutar(
            [
                "uv",
                "tool",
                "run",
                "--from",
                f"pip-audit=={PIP_AUDIT}",
                "pip-audit",
                "-r",
                str(requisitos),
                "--no-deps",
                "--disable-pip",
                "--format",
                "json",
                "--progress-spinner",
                "off",
                "--output",
                str(salida),
            ]
        )
        # pip-audit sale con 1 si encontró vulnerabilidades pero escribe el JSON igual; sin JSON
        # la auditoría no ocurrió y eso es un fallo, no un «limpio».
        if not salida.is_file():
            raise RuntimeError(f"pip-audit no produjo resultado para {requisitos}")
        return json.loads(salida.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None, ejecutar: Callable[..., int] = _ejecutar) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--capa", action="append", required=True, help="NOMBRE=archivo.txt")
    analizador.add_argument("--salida", type=Path, required=True)
    argumentos = analizador.parse_args(argv)
    nombres, resultados = [], []
    for capa in argumentos.capa:
        nombre, _, archivo = capa.partition("=")
        nombres.append(nombre)
        resultados.append(auditar_capa(Path(archivo), ejecutar))
    unido = fusionar(resultados)
    veredicto = evaluar(unido, cargar_aceptadas(), date.today())
    argumentos.salida.write_text(
        json.dumps(
            {
                "pip_audit": PIP_AUDIT,
                "fecha": date.today().isoformat(),
                "capas": nombres,
                "abiertas": veredicto.abiertas,
                "aceptadas": veredicto.aceptadas,
                "vencidas": veredicto.vencidas,
                "no_auditadas": veredicto.no_auditadas,
                "dependencias": len(unido["dependencies"]),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"{len(unido['dependencies'])} dependencias; abiertas: {len(veredicto.abiertas)}")
    return 1 if veredicto.abiertas else 0


if __name__ == "__main__":
    raise SystemExit(main())
