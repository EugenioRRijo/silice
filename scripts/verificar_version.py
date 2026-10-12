"""Comprueba que la etiqueta de git coincide con `pyproject.toml` (RF-99; spec S5 §9.2).

    uv run python scripts/verificar_version.py --etiqueta v1.0.0-rc.1

La etiqueta es SemVer con `v`; `pyproject.toml` guarda PEP 440; se comparan normalizadas con
`packaging.version`. Código de salida 0 si coinciden, 1 si no.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from packaging.version import InvalidVersion, Version

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from operacion.version import a_semver, siguiente_parche, version  # noqa: E402

_SEMVER_CON_V = re.compile(r"^v\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?$")


def version_del_proyecto() -> str:
    return version()


def comparar(etiqueta: str, pep440: str) -> tuple[bool, str]:
    if not etiqueta.startswith("v"):
        return False, f"la etiqueta «{etiqueta}» debe empezar con «v»"
    if _SEMVER_CON_V.match(etiqueta) is None:
        return False, f"la etiqueta «{etiqueta}» no es SemVer (vX.Y.Z o vX.Y.Z-rc.N)"
    try:
        igual = Version(etiqueta[1:]) == Version(pep440)
    except InvalidVersion as error:
        return False, f"versión inválida: {error}"
    if not igual:
        return False, f"la etiqueta {etiqueta} no coincide con pyproject.toml ({pep440})"
    return True, f"{etiqueta} coincide con pyproject.toml ({pep440})"


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    grupo = analizador.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--etiqueta", help="vX.Y.Z[-rc.N]: comprobar contra pyproject.toml")
    grupo.add_argument("--imprimir", choices=["semver", "parche"], help="imprimir la versión")
    argumentos = analizador.parse_args(argv)
    if argumentos.imprimir:
        semver = a_semver(version_del_proyecto())
        print(semver if argumentos.imprimir == "semver" else siguiente_parche(semver))
        return 0
    coincide, mensaje = comparar(argumentos.etiqueta, version_del_proyecto())
    print(mensaje, file=sys.stdout if coincide else sys.stderr)
    return 0 if coincide else 1


if __name__ == "__main__":
    raise SystemExit(main())
