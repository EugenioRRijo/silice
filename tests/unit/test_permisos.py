"""La matriz de roles de S3 §5.1, escrita a mano fila por fila (RF-80; P2 ratificada)."""

from __future__ import annotations

import pytest

from seguridad.permisos import (
    PERMISOS,
    Accion,
    PermisoDenegado,
    Rol,
    aviso_de_roles,
    exigir,
    permitido,
    roles_de,
    texto_de_roles,
)

#: (acción, arma, revisa, administrador): la tabla de §5.1, no derivada de PERMISOS.
MATRIZ = (
    (Accion.EDITAR_HOJA, True, False, False),
    (Accion.CONVERTIR_Y_REAJUSTAR, True, False, False),
    (Accion.CONTROL_DE_OBRA, True, False, False),
    (Accion.DECIDIR_RECUPERACION, True, False, False),
    (Accion.ENTREGAR_PAQUETE, True, False, False),
    (Accion.LEER_PROYECTO, True, True, False),
    (Accion.REVISAR_PAQUETE, False, True, False),
    (Accion.CAMBIAR_CASO, True, False, True),
    (Accion.ADMINISTRAR_CUENTAS, False, False, True),
    (Accion.ADMINISTRAR_EMPRESA, False, False, True),
    (Accion.ADMINISTRAR_PRECIOS, False, False, True),
    (Accion.ADMINISTRAR_RED_Y_API, False, False, True),
    (Accion.CAMBIAR_CARPETA_DE_DATOS, False, False, True),
)


def test_la_matriz_cubre_todas_las_acciones() -> None:
    assert {fila[0] for fila in MATRIZ} == set(Accion) == set(PERMISOS)


@pytest.mark.parametrize("accion,arma,revisa,admin", MATRIZ)
def test_cada_fila_de_la_matriz(accion: Accion, arma: bool, revisa: bool, admin: bool) -> None:
    assert permitido({Rol.ARMA}, accion) is arma
    assert permitido({Rol.REVISA}, accion) is revisa
    assert permitido({Rol.ADMINISTRADOR}, accion) is admin
    # varios roles suman
    assert permitido({Rol.ARMA, Rol.REVISA, Rol.ADMINISTRADOR}, accion) is (
        arma or revisa or admin
    )


def test_exigir_rechaza_con_un_mensaje_llano() -> None:
    with pytest.raises(PermisoDenegado, match="no tiene permiso"):
        exigir({Rol.REVISA}, Accion.EDITAR_HOJA)
    exigir({Rol.ARMA}, Accion.EDITAR_HOJA)


def test_los_roles_se_guardan_ordenados_y_sin_repetir() -> None:
    assert texto_de_roles(["revisa", Rol.ARMA, "arma"]) == "arma,revisa"
    assert roles_de("arma,revisa,inventado") == {Rol.ARMA, Rol.REVISA}
    with pytest.raises(ValueError):
        texto_de_roles([])


def test_armar_y_revisar_a_la_vez_se_informa_sin_impedirlo() -> None:
    assert "ella misma armó" in aviso_de_roles({Rol.ARMA, Rol.REVISA})
    assert aviso_de_roles({Rol.ARMA}) is None
