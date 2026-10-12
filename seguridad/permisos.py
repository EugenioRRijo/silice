"""Roles, acciones y la matriz de permisos (spec S3 §5.1; maestro §4.1, P2 ratificada).

Una fila de la matriz = una `Accion`. `permitido(roles, accion)` es la única función que decide;
la navegación, cada `render()` de `ui/paginas` y cada función de `ui/` que escribe la llaman.
Las operaciones con secretos de la empresa (`Sensible`) exigen además el propio equipo
(`seguridad.red`).
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum


class Rol(StrEnum):
    ARMA = "arma"
    REVISA = "revisa"
    ADMINISTRADOR = "administrador"


class Accion(StrEnum):
    # Trabajo (rol arma)
    EDITAR_HOJA = "editar_hoja"  # crear proyecto, hoja, versiones, planos, contraste, Excel
    CONVERTIR_Y_REAJUSTAR = "convertir_y_reajustar"  # moneda del proyecto y estudios (S1)
    CONTROL_DE_OBRA = "control_de_obra"  # línea base, valuaciones, costos incurridos (S2)
    DECIDIR_RECUPERACION = "decidir_recuperacion"  # (S2)
    ENTREGAR_PAQUETE = "entregar_paquete"
    # Lectura
    LEER_PROYECTO = "leer_proyecto"
    # Revisión (rol revisa)
    REVISAR_PAQUETE = "revisar_paquete"  # abrir paquetes, reauditar, dictamen
    # Compartida
    CAMBIAR_CASO = "cambiar_caso"
    # Administración
    ADMINISTRAR_CUENTAS = "administrar_cuentas"  # cuentas, desbloqueo, sesiones, accesos
    ADMINISTRAR_EMPRESA = "administrar_empresa"  # empresa, clave de firma, empresas registradas
    ADMINISTRAR_PRECIOS = "administrar_precios"  # lista de la empresa e importar el BCV (S1)
    ADMINISTRAR_RED_Y_API = "administrar_red_y_api"  # red local, API y claves de API
    CAMBIAR_CARPETA_DE_DATOS = "cambiar_carpeta_de_datos"  # (S5)


class Sensible(StrEnum):
    """Lo que solo se hace desde el propio equipo (spec S3 §5.6; maestro §4.7)."""

    FIRMAR = "firmar"
    CLAVE_DE_FIRMA = "clave_de_firma"  # generar, exportar, retirar, revocar
    CLAVE_DE_API = "clave_de_api"  # crear
    CLAVE_DE_IA = "clave_de_ia"  # registrar (S4)
    CARPETA_DE_DATOS = "carpeta_de_datos"  # cambiar (S5)


_ARMA, _REVISA, _ADMIN = Rol.ARMA, Rol.REVISA, Rol.ADMINISTRADOR

#: La matriz de S3 §5.1, una fila por acción. Es la única fuente: `test_permisos` la reproduce
#: a mano, fila por fila y rol por rol.
PERMISOS: dict[Accion, frozenset[Rol]] = {
    Accion.EDITAR_HOJA: frozenset({_ARMA}),
    Accion.CONVERTIR_Y_REAJUSTAR: frozenset({_ARMA}),
    Accion.CONTROL_DE_OBRA: frozenset({_ARMA}),
    Accion.DECIDIR_RECUPERACION: frozenset({_ARMA}),
    Accion.ENTREGAR_PAQUETE: frozenset({_ARMA}),
    Accion.LEER_PROYECTO: frozenset({_ARMA, _REVISA}),
    Accion.REVISAR_PAQUETE: frozenset({_REVISA}),
    Accion.CAMBIAR_CASO: frozenset({_ARMA, _ADMIN}),
    Accion.ADMINISTRAR_CUENTAS: frozenset({_ADMIN}),
    Accion.ADMINISTRAR_EMPRESA: frozenset({_ADMIN}),
    Accion.ADMINISTRAR_PRECIOS: frozenset({_ADMIN}),
    Accion.ADMINISTRAR_RED_Y_API: frozenset({_ADMIN}),
    Accion.CAMBIAR_CARPETA_DE_DATOS: frozenset({_ADMIN}),
}

#: La acción de cada operación sensible: además de este rol, exigen el propio equipo.
ROL_DE_LO_SENSIBLE: dict[Sensible, Accion] = {
    Sensible.FIRMAR: Accion.ENTREGAR_PAQUETE,
    Sensible.CLAVE_DE_FIRMA: Accion.ADMINISTRAR_EMPRESA,
    Sensible.CLAVE_DE_API: Accion.ADMINISTRAR_RED_Y_API,
    Sensible.CLAVE_DE_IA: Accion.ADMINISTRAR_EMPRESA,
    Sensible.CARPETA_DE_DATOS: Accion.CAMBIAR_CARPETA_DE_DATOS,
}


class PermisoDenegado(PermissionError):  # noqa: N818
    """El rol no corresponde a la acción; el mensaje está en lenguaje llano, sin traza."""


def roles_de(texto: str) -> frozenset[Rol]:
    """Los roles de una cuenta guardados como `"arma,revisa"`; ignora lo desconocido."""
    conocidos = {rol.value for rol in Rol}
    return frozenset(Rol(r) for r in texto.split(",") if r in conocidos)


def texto_de_roles(roles: Iterable[Rol | str]) -> str:
    """Los roles normalizados para guardar: sin repetidos y en el orden de `Rol`."""
    pedidos = {Rol(r) for r in roles}
    if not pedidos:
        raise ValueError("una cuenta necesita al menos un rol")
    return ",".join(r.value for r in Rol if r in pedidos)


def permitido(roles: Iterable[Rol], accion: Accion) -> bool:
    return bool(set(roles) & PERMISOS[accion])


def exigir(roles: Iterable[Rol], accion: Accion) -> None:
    """`PermisoDenegado` si ningún rol permite `accion`."""
    if not permitido(roles, accion):
        raise PermisoDenegado("Su cuenta no tiene permiso para esta acción.")


def aviso_de_roles(roles: Iterable[Rol]) -> str | None:
    """Lo que la pantalla de cuentas informa sin impedir (S3 §5.1, P2): arma y revisa a la vez."""
    pedidos = set(roles)
    if {Rol.ARMA, Rol.REVISA} <= pedidos:
        return (
            "Esta cuenta podrá revisar paquetes que ella misma armó; la vista de revisión "
            "lo indicará."
        )
    return None
