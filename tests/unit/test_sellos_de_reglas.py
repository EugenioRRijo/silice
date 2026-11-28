"""Los archivos sellados por `reglas-congeladas-2026-11-24` no cambian (B2, ficha-b2 §6, R3).

El acta del 2026-11-25 (reestructuración del front) deja intactos `core/`, las reglas, los
umbrales, `aplicacion/causas_raiz.py`, el plan no circular, la taxonomía de plantilla,
`api/rutas/libros.py` y `aplicacion/hoja.py`. Esta prueba compara la huella SHA-256 de cada uno
(contenido con finales LF, como `aplicacion/manifiesto_corrida.py`) con la que tenía en la
etiqueta. Las huellas se fijan aquí para no depender de que la etiqueta exista en el clon; si
existe, otra prueba comprueba que lo fijado es lo que la etiqueta dice.

Una regla solo cambia con un acta de re-congelado: ese día se actualizan estas huellas junto con
`tests/unit/test_manifiesto_corrida.py`.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ETIQUETA = "reglas-congeladas-2026-11-24"

#: Los diez de la etiqueta, más `libros.py` y `hoja.py`, sellados por el acta.
SELLOS: dict[str, str] = {
    "core/verification/reglas.py": (
        "e4fb1579d25e38dcdb3348a4f4b01fd253ca404dc5b24f0a5f0586341ba8f8c2"
    ),
    "adapters/hoja_empresa/reglas.py": (
        "ff620d51f00aef7998ebd0bdcff21cd5f0b1e9a28a00a07e4d6032eff06cf8c1"
    ),
    "adapters/hoja_empresa/reglas_calculo.py": (
        "0231d006f015a9c76e77a0f6df3da4a9aacd2bc36abe0760b08b5b786aa57a54"
    ),
    "adapters/hoja_empresa/reglas_contexto.py": (
        "c938aa19cf754bed3003cc7788a8eed18b93e40859e0cb22379e22e0ef09b57b"
    ),
    "adapters/hoja_empresa/umbrales.py": (
        "a8da53e3cf0138b9b97a6e411d888d9ca8db7576cd6f28d16f44f15addc4df9d"
    ),
    "adapters/vial/reglas.py": ("531eb72cbcef5718e1d72b4d1b5656e651263869c9ddb30c7dc47ff1264c6961"),
    "adapters/vial/constantes.py": (
        "ebb5c6e586cf63a617e417e158c04165f2d1d52154f4aaeb4005aa4c0fff512b"
    ),
    "aplicacion/causas_raiz.py": (
        "bb2a53a4d13c8cc6aff3a84cd9669974ac49e7f8e547411ef55b3722a5f0c9d6"
    ),
    "docs/planes/2026-11-23-plan-auditoria-no-circular.md": (
        "370fc28d4623d5981b4b91ae2eead8d734b5727944cb68e6bf6dd75a848af6b2"
    ),
    "docs/tesis/taxonomia_fallas_plantilla.toml": (
        "f622ad95952899445bb3230e81ad4659c728b7b4336188cc1c33d73c31217494"
    ),
    "api/rutas/libros.py": ("e26b2e85d0295da2d766aa607edc1c433de6a5341cae9aa92635d6392825144e"),
    "aplicacion/hoja.py": ("bd92dfd12cc0ef74741e9c0e2ac1df3cf56735b00de9426bac5f9aaff3155bd6"),
}

#: Los 62 módulos de `core/` en la etiqueta: la huella de las líneas «ruta huella» ordenadas.
HUELLA_DE_CORE = "551d6475b077c4db80a8e0b6f1d7d324655d2fadeb223592319315ed67e1e725"
MODULOS_DE_CORE = 62


def _huella_lf(contenido: bytes) -> str:
    return hashlib.sha256(contenido.replace(b"\r\n", b"\n")).hexdigest()


def _huella_de_core(leer) -> tuple[int, str]:
    """`leer(ruta)` da el contenido de un archivo de `core/`; las rutas salen ordenadas."""
    rutas = sorted(p.relative_to(RAIZ).as_posix() for p in (RAIZ / "core").rglob("*.py"))
    lineas = [f"{ruta} {_huella_lf(leer(ruta))}" for ruta in rutas]
    return len(rutas), hashlib.sha256("\n".join(lineas).encode()).hexdigest()


def _git(*argumentos: str) -> bytes | None:
    try:
        return subprocess.run(
            ["git", *argumentos], cwd=RAIZ, capture_output=True, check=True, timeout=60
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None


@pytest.mark.parametrize("ruta", sorted(SELLOS))
def test_cada_sellado_conserva_su_huella(ruta: str) -> None:
    assert _huella_lf((RAIZ / ruta).read_bytes()) == SELLOS[ruta]


def test_core_conserva_su_huella() -> None:
    cuenta, huella = _huella_de_core(lambda ruta: (RAIZ / ruta).read_bytes())
    assert (cuenta, huella) == (MODULOS_DE_CORE, HUELLA_DE_CORE)


def test_lo_fijado_aqui_es_lo_que_dice_la_etiqueta() -> None:
    """Con la etiqueta en el clon, cada huella fijada es la de su archivo en la etiqueta."""
    if _git("rev-parse", "--verify", "--quiet", f"{ETIQUETA}^{{commit}}") is None:
        return  # un clon sin etiquetas: las huellas fijadas arriba son la garantía
    for ruta, huella in SELLOS.items():
        contenido = _git("show", f"{ETIQUETA}:{ruta}")
        assert contenido is not None, ruta
        assert _huella_lf(contenido) == huella, ruta
    _, huella_core = _huella_de_core(lambda ruta: _git("show", f"{ETIQUETA}:{ruta}") or b"")
    # Un módulo nuevo en `core/` cambia la huella: también se detecta aquí.
    assert huella_core == HUELLA_DE_CORE


def test_la_huella_ignora_el_fin_de_linea() -> None:
    assert _huella_lf(b"a = 1\r\nb = 2\r\n") == _huella_lf(b"a = 1\nb = 2\n")


def test_una_linea_cambiada_cambia_la_huella() -> None:
    assert _huella_lf(b"UMBRAL = 0.05\n") != _huella_lf(b"UMBRAL = 0.06\n")
