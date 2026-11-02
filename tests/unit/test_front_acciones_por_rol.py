"""Las acciones por rol que las pruebas del front copian a mano son las de la matriz de permisos.

`frontend-desktop/src/shell/obras/datosDePrueba.tsx::ACCIONES` (ana arma, rita revisa, admin
administra) es el oraculo de las pruebas del marco: «ninguna pantalla usable queda inalcanzable»
(`marco/Marco.test.tsx`), la barra lateral, el buscador y la mesa. Si un dia `seguridad/permisos.py`
cambia lo que puede un rol, esas pruebas seguirian pasando con acciones viejas: esta prueba lo
detecta.

Antes vigilaba tambien `shell/navegacion.ts::ENTRADA_POR_ROL` (el modulo de entrada de cada rol);
con el marco nuevo (rediseno del marco, Tarea 8) los modulos se retiraron y toda cuenta entra en
Pendientes, asi que esa suposicion ya no existe en el front.

Oraculo: `PERMISOS` (la matriz real).
"""

from __future__ import annotations

import re
from pathlib import Path

from seguridad.permisos import PERMISOS, Rol

RAIZ = Path(__file__).resolve().parents[2]
DATOS_DE_PRUEBA = RAIZ / "frontend-desktop" / "src" / "shell" / "obras" / "datosDePrueba.tsx"


def _acciones_por_rol_de_la_prueba(texto: str) -> dict[str, set[str]]:
    bloque = texto[texto.index("export const ACCIONES = {") :]
    bloque = bloque[: bloque.index("} as const;")]
    return {
        login: set(re.findall(r'"([a-z_]+)"', lista))
        for login, lista in re.findall(r"(ana|rita|admin):\s*\[([^\]]*)\]", bloque)
    }


def test_las_acciones_por_rol_de_las_pruebas_del_marco_son_las_de_la_matriz() -> None:
    copiadas = _acciones_por_rol_de_la_prueba(DATOS_DE_PRUEBA.read_text(encoding="utf-8"))
    roles = {"ana": Rol.ARMA, "rita": Rol.REVISA, "admin": Rol.ADMINISTRADOR}
    assert set(copiadas) == set(roles)
    for login, rol in roles.items():
        de_la_matriz = {a.value for a, quienes in PERMISOS.items() if rol in quienes}
        assert copiadas[login] == de_la_matriz, login


def test_la_prueba_ve_una_accion_de_mas() -> None:
    """Si la copia se desvia, se nota: una accion inventada no esta en la matriz de ningun rol."""
    texto = DATOS_DE_PRUEBA.read_text(encoding="utf-8").replace(
        '  rita: ["leer_proyecto",', '  rita: ["accion_inventada", "leer_proyecto",', 1
    )
    copiadas = _acciones_por_rol_de_la_prueba(texto)
    de_la_matriz = {a.value for a, quienes in PERMISOS.items() if Rol.REVISA in quienes}
    assert copiadas["rita"] != de_la_matriz
