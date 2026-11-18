"""Los listados de Administracion que salieron de `api/rutas` (tarea 3.2 del plan de desenredo).

`seguridad.claves_api.claves`, `seguridad.empresas.registradas` y `seguridad.cuentas.usuarios`
devuelven las filas en orden. Cada prueba arma a mano una base de instalacion en memoria con tres
filas escritas fuera de orden. Nombres ficticios.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from seguridad import claves_api, cuentas, empresas
from seguridad.modelo import Base, ClaveApi, EmpresaRegistrada, Usuario

AHORA = datetime(2026, 11, 17, 9, 0)


@pytest.fixture
def bd() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


def test_claves_salen_por_id(bd: Session) -> None:
    for identificador in (3, 1, 2):
        bd.add(
            ClaveApi(
                id=identificador,
                nombre=f"Integracion {identificador}",
                identificador=f"id{identificador:06d}",
                huella_secreto="0" * 64,
                creada=AHORA,
            )
        )
        bd.flush()
    assert [c.id for c in claves_api.claves(bd)] == [1, 2, 3]


def test_empresas_registradas_salen_por_id(bd: Session) -> None:
    for identificador in (2, 3, 1):
        bd.add(
            EmpresaRegistrada(
                id=identificador,
                empresa=f"Constructora Ficticia {identificador}",
                publica=bytes([identificador]) * 32,
                huella=f"{identificador:064d}",
                estado="activa",
                comprobada_con="Persona Inventada",
                metodo="telefono",
                fecha_comprobacion=AHORA,
            )
        )
        bd.flush()
    assert [e.id for e in empresas.registradas(bd)] == [1, 2, 3]


def test_usuarios_salen_por_login(bd: Session) -> None:
    for login in ("rita", "ana", "pedro"):
        bd.add(
            Usuario(login=login, nombre=login.title(), huella_clave="x", roles="arma", creado=AHORA)
        )
        bd.flush()
    assert [u.login for u in cuentas.usuarios(bd)] == ["ana", "pedro", "rita"]
