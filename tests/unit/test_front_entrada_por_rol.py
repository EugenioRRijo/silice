"""El front deduce el rol por acciones exclusivas: que sigan siendolo en la matriz de permisos.

`frontend-desktop/src/shell/navegacion.ts::ENTRADA_POR_ROL` elige el modulo de entrada de una
cuenta (decision 3 de Eugenio, ratificada el 2026-10-25) leyendo una accion que «solo tiene ese
rol». La sesion no le da al front un rol util para esto (una cuenta puede tener varios), asi que
la suposicion vive en el front. Si un dia `seguridad/permisos.py` le da `editar_hoja` tambien a
quien revisa, el front lo mandaria en silencio al modulo equivocado: esta prueba lo detecta
(observacion menor 1 del arbitro de MOD-1).

Tambien ata las acciones por rol que las pruebas del armazon copian a mano (`ACCIONES_POR_ROL`
de `Shell.test.tsx`): son el oraculo de «toda pantalla alcanzable por rol» y deben ser las de la
matriz.

Oraculo: `PERMISOS` (la matriz real) y, escrito a mano, que rol corresponde a cada accion de
entrada.
"""

from __future__ import annotations

import re
from pathlib import Path

from seguridad.permisos import PERMISOS, Accion, Rol

RAIZ = Path(__file__).resolve().parents[2]
NAVEGACION = RAIZ / "frontend-desktop" / "src" / "shell" / "navegacion.ts"
PRUEBA_SHELL = RAIZ / "frontend-desktop" / "src" / "shell" / "Shell.test.tsx"

#: Escrito a mano: la accion con que el front reconoce a cada rol y el modulo en que entra.
ESPERADO = [
    ("editar_hoja", Rol.ARMA, "obras"),
    ("revisar_paquete", Rol.REVISA, "auditoria"),
    ("administrar_precios", Rol.ADMINISTRADOR, "obras"),
]


def _entrada_por_rol(texto: str) -> list[tuple[str, str]]:
    bloque = texto[texto.index("export const ENTRADA_POR_ROL") :]
    bloque = bloque[: bloque.index("];")]
    return re.findall(r'\{\s*accion:\s*"([a-z_]+)",\s*modulo:\s*"([a-z]+)"\s*\}', bloque)


def _roles_con(accion: str) -> frozenset[Rol]:
    return PERMISOS[Accion(accion)]


def test_el_front_lee_las_tres_entradas_por_rol() -> None:
    entradas = _entrada_por_rol(NAVEGACION.read_text(encoding="utf-8"))
    assert entradas == [(a, m) for a, _, m in ESPERADO]


def test_cada_accion_de_entrada_es_exclusiva_de_su_rol_en_la_matriz() -> None:
    for accion, rol, _ in ESPERADO:
        assert _roles_con(accion) == frozenset({rol}), accion


def test_la_prueba_ve_una_accion_compartida() -> None:
    """Si la suposicion se rompe, se nota: `leer_proyecto` la tienen arma y revisa."""
    assert _roles_con("leer_proyecto") == frozenset({Rol.ARMA, Rol.REVISA})
    assert _roles_con("leer_proyecto") != frozenset({Rol.ARMA})


def _acciones_por_rol_de_la_prueba(texto: str) -> dict[str, set[str]]:
    bloque = texto[texto.index("const ACCIONES_POR_ROL") :]
    bloque = bloque[: bloque.index("};")]
    return {
        login: set(re.findall(r'"([a-z_]+)"', lista))
        for login, lista in re.findall(r"(ana|rita|admin):\s*\[([^\]]*)\]", bloque)
    }


def test_las_acciones_por_rol_de_las_pruebas_del_armazon_son_las_de_la_matriz() -> None:
    copiadas = _acciones_por_rol_de_la_prueba(PRUEBA_SHELL.read_text(encoding="utf-8"))
    roles = {"ana": Rol.ARMA, "rita": Rol.REVISA, "admin": Rol.ADMINISTRADOR}
    assert set(copiadas) == set(roles)
    for login, rol in roles.items():
        de_la_matriz = {a.value for a, quienes in PERMISOS.items() if rol in quienes}
        assert copiadas[login] == de_la_matriz, login
