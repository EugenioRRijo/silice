"""La elección (carpeta y obra) y las preferencias (módulo, sidebar fijado) de cada cuenta (MOD-0).

Lo que la interfaz nueva recuerda de una persona entre sesiones y reinicios de la API, en la tabla
`mp_eleccion` de la instalación (`aplicacion.tablas_eleccion`). Estas funciones solo leen o
escriben la fila (`flush`, nunca `commit`): la transacción es de quien llama (en la API, la de la
petición). Qué carpeta existe y qué obra hay en ella lo decide la API al restaurar
(`api.rutas.sesion`), no este módulo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from aplicacion.tablas_eleccion import EleccionDeCuenta

MODULOS = ("auditoria", "obras", "produccion")
MENSAJE_MODULO = "Ese módulo no existe."


@dataclass(frozen=True)
class Eleccion:
    caso: str | None
    proyecto: str | None
    modulo: str | None
    sidebar_fijado: bool


def eleccion_de(sesion_ins: Session, usuario_id: int) -> Eleccion | None:
    """Lo que recuerda la cuenta, o `None` si nunca guardó nada."""
    fila = sesion_ins.get(EleccionDeCuenta, usuario_id)
    if fila is None:
        return None
    return Eleccion(
        caso=fila.caso,
        proyecto=fila.proyecto,
        modulo=fila.modulo,
        sidebar_fijado=bool(fila.sidebar_fijado),
    )


def _fila(sesion_ins: Session, usuario_id: int, ahora: datetime) -> EleccionDeCuenta:
    """La fila de la cuenta, creada si falta. `INSERT ... ON CONFLICT DO NOTHING`: dos peticiones
    a la vez de la misma cuenta no chocan con la clave primaria."""
    sesion_ins.execute(
        insert(EleccionDeCuenta)
        .values(usuario_id=usuario_id, sidebar_fijado=False, fecha=ahora)
        .on_conflict_do_nothing(index_elements=["usuario_id"])
    )
    fila = sesion_ins.get(EleccionDeCuenta, usuario_id, populate_existing=True)
    assert fila is not None  # recién insertada o ya estaba
    fila.fecha = ahora
    return fila


def recordar_caso(sesion_ins: Session, usuario_id: int, caso: str | None, ahora: datetime) -> None:
    """Recuerda la carpeta (`None` = la de la instalación) y olvida la obra, que era de otra."""
    fila = _fila(sesion_ins, usuario_id, ahora)
    fila.caso = caso
    fila.proyecto = None
    sesion_ins.flush()


def recordar_proyecto(
    sesion_ins: Session, usuario_id: int, proyecto: str | None, ahora: datetime
) -> None:
    """Recuerda la obra de la carpeta recordada (`None` = ninguna)."""
    fila = _fila(sesion_ins, usuario_id, ahora)
    fila.proyecto = proyecto
    sesion_ins.flush()


def recordar_preferencias(
    sesion_ins: Session,
    usuario_id: int,
    *,
    modulo: str | None = None,
    sidebar_fijado: bool | None = None,
    ahora: datetime,
) -> None:
    """Recuerda el último módulo y si el sidebar queda fijado; `None` deja el valor como estaba.
    `ValueError(MENSAJE_MODULO)` si el módulo no es uno de `MODULOS` (antes de escribir nada)."""
    if modulo is not None and modulo not in MODULOS:
        raise ValueError(MENSAJE_MODULO)
    fila = _fila(sesion_ins, usuario_id, ahora)
    if modulo is not None:
        fila.modulo = modulo
    if sidebar_fijado is not None:
        fila.sidebar_fijado = sidebar_fijado
    sesion_ins.flush()
