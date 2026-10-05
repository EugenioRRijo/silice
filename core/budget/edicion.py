"""SF‑E2: guardar una edición como versión nueva, registrar el cambio y restaurar (RF‑52 a RF‑54).

Una edición de la hoja del proyecto (cantidades de un APU, parámetros, plan, precios, metrajes) se
guarda como **versión nueva** de un presupuesto ya guardado (`guardar_edicion`), con su informe, la
instantánea de sus composiciones (SF‑E6) y un `RegistroCambio` por celda que cambió. Es propio de
cualquier presupuesto guardado, tenga o no hoja de metrajes: `core` no conoce las tablas `esp_*`;
quien las tiene pasa un **gancho** que corre en la misma `Session` (y por tanto en la misma
transacción) una vez creada la versión.

Reglas (spec §9.3): todo guardado exige **fuente del cambio** y **responsable** (`ValueError`, antes
de tocar la base); guardar sin cambios no crea versión ni registros vacíos (FR‑4: devuelve `None`);
toda versión nueva declara su `version_origen`. **Restaurar** la versión N crea una versión nueva,
copia de N, con su registro: nada se borra y la restaurada pasa a ser la vigente (la de mayor
`id` no descartada). Ninguna función confirma la transacción; si algo falla, quien llama hace
`rollback`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from core import models
from core.budget.excel import COLUMNAS_TRAZABILIDAD, PESTANA_TRAZABILIDAD, TablaExportable
from core.budget.instantanea import plan_de_version
from core.budget.persistencia import (
    _buscar,
    _parametros_de,
    cargar_elaboracion,
    guardar_presupuesto,
)
from core.budget.presupuesto import ResultadoElaboracion
from core.catalog import Catalogo
from core.contracts.apu import ParametrosCosto

__all__ = [
    "OBJETOS",
    "CambioEditado",
    "guardar_edicion",
    "registros_de_version",
    "restaurar_version",
    "siguiente_codigo",
    "tabla_trazabilidad",
    "version_vigente",
]

#: Qué puede cambiar un `RegistroCambio`: metraje (hoja de espacio), APU (líneas o rendimiento),
#: cantidad (sobrescritura en el presupuesto), precio (cotización), plan, parámetro y versión
#: (restauración).
#: Código de versión: prefijo libre y número final (`001`, `TI-001`).
_CODIGO_VERSION = re.compile(r"^(.*?)(\d+)$")

OBJETOS = ("metraje", "apu", "cantidad", "precio", "plan", "parametro", "version")

#: Gancho de quien guarda: recibe la sesión y la versión recién creada (con `id`).
Gancho = Callable[[Session, models.Presupuesto], None]


@dataclass(frozen=True, slots=True)
class CambioEditado:
    """Una celda que cambió: qué objeto, qué fila (`clave`), qué campo, y los dos valores como
    texto. Lo arma quien edita (la hoja); `core` no interpreta las claves."""

    objeto: str
    clave: str
    campo: str
    valor_anterior: str
    valor_nuevo: str


def _exigir_respaldo(fuente: str, responsable: str) -> tuple[str, str]:
    fuente, responsable = fuente.strip(), responsable.strip()
    if not fuente:
        raise ValueError("la fuente del cambio es obligatoria: diga por que y con que respaldo")
    if not responsable:
        raise ValueError("el responsable del cambio es obligatorio")
    return fuente, responsable


def _exigir_codigo_libre(session: Session, proyecto_id: int, codigo: str) -> None:
    repetido = session.scalar(
        select(models.Presupuesto.id).where(
            models.Presupuesto.proyecto_id == proyecto_id, models.Presupuesto.codigo == codigo
        )
    )
    if repetido is not None:
        raise ValueError(f"el proyecto ya tiene una version {codigo!r}")


def guardar_edicion(
    session: Session,
    proyecto_nombre: str,
    codigo_origen: str,
    resultado: ResultadoElaboracion,
    parametros: ParametrosCosto,
    cambios: Sequence[CambioEditado],
    *,
    fuente: str,
    responsable: str,
    plan=None,
    lista: models.ListaPrecios | None = None,
    ahora: datetime | None = None,
    gancho: Gancho | None = None,
) -> models.Presupuesto | None:
    """Guarda `resultado` (la elaboración ya editada) como versión nueva de `codigo_origen`.

    `resultado.presupuesto.codigo` es el código de la versión nueva (ver `siguiente_codigo`).
    `cambios` son las celdas que cambiaron: las de valor anterior igual al nuevo no cuentan, y si no
    queda ninguna no se crea nada y se devuelve `None` (FR‑4). Crea un `RegistroCambio` por celda.
    `lista` es la de la versión de origen salvo que se diga otra; `plan` se guarda con la versión.
    `gancho(session, version)` corre tras crearla, en la misma sesión. No confirma.
    """
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    for cambio in cambios:
        if cambio.objeto not in OBJETOS:
            raise ValueError(f"objeto {cambio.objeto!r} desconocido; se espera uno de {OBJETOS}")
    reales = [c for c in cambios if c.valor_anterior != c.valor_nuevo]
    if not reales:
        return None
    origen = _buscar(session, proyecto_nombre, codigo_origen)
    _exigir_codigo_libre(session, origen.proyecto_id, resultado.presupuesto.codigo)
    nueva = guardar_presupuesto(
        session,
        resultado.presupuesto,
        resultado.informe,
        proyecto=origen.proyecto,
        lista=lista or origen.lista_precios,
        parametros=parametros,
        pendientes=resultado.pendientes,
        plan=plan,
        version_origen=origen,
        motivo="edicion",
        heredar_insumos=True,
    )
    momento = ahora or datetime.now()
    session.add_all(
        models.RegistroCambio(
            proyecto_id=origen.proyecto_id,
            version_origen_id=origen.id,
            version_resultante_id=nueva.id,
            objeto=cambio.objeto,
            clave=cambio.clave,
            campo=cambio.campo,
            valor_anterior=cambio.valor_anterior,
            valor_nuevo=cambio.valor_nuevo,
            fuente=fuente,
            responsable=responsable,
            fecha_hora=momento,
        )
        for cambio in reales
    )
    session.flush()
    if gancho is not None:
        gancho(session, nueva)
    return nueva


def restaurar_version(
    session: Session,
    proyecto_nombre: str,
    codigo: str,
    codigo_nuevo: str,
    catalogo: Catalogo,
    *,
    fuente: str,
    responsable: str,
    ahora: datetime | None = None,
    gancho: Gancho | None = None,
) -> models.Presupuesto:
    """RF‑54: crea la versión `codigo_nuevo`, copia de `codigo`, con su `RegistroCambio`.

    La copia lleva los mismos renglones, ítems, pendientes, curva, plan, parámetros, lista de
    precios y composiciones congeladas, y el informe del documento original (recargado). Su
    `version_origen` es la restaurada. No usa `descartar_version`: nada se borra. No confirma.
    """
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    origen = _buscar(session, proyecto_nombre, codigo)
    _exigir_codigo_libre(session, origen.proyecto_id, codigo_nuevo)
    vigente = version_vigente(session, proyecto_nombre)
    elaboracion = cargar_elaboracion(session, proyecto_nombre, codigo, catalogo)
    nueva = guardar_presupuesto(
        session,
        replace(elaboracion.presupuesto, codigo=codigo_nuevo),
        replace(elaboracion.informe, codigo_presupuesto=codigo_nuevo),
        proyecto=origen.proyecto,
        lista=origen.lista_precios,
        parametros=_parametros_de(origen),
        pendientes=elaboracion.pendientes,
        plan=plan_de_version(session, origen),
        version_origen=origen,
        motivo="restauracion",
        heredar_insumos=True,
    )
    session.add(
        models.RegistroCambio(
            proyecto_id=origen.proyecto_id,
            version_origen_id=origen.id,
            version_resultante_id=nueva.id,
            objeto="version",
            clave=codigo,
            campo="restauracion",
            valor_anterior=vigente.codigo if vigente is not None else "",
            valor_nuevo=codigo_nuevo,
            fuente=fuente,
            responsable=responsable,
            fecha_hora=ahora or datetime.now(),
        )
    )
    session.flush()
    if gancho is not None:
        gancho(session, nueva)
    return nueva


def version_vigente(session: Session, proyecto_nombre: str) -> models.Presupuesto | None:
    """La versión vigente del proyecto: la de mayor `id` no descartada (spec §9.3)."""
    descartada = exists().where(models.DescarteVersion.presupuesto_id == models.Presupuesto.id)
    return session.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto_nombre, ~descartada)
        .order_by(models.Presupuesto.id.desc())
        .limit(1)
    ).one_or_none()


def siguiente_codigo(session: Session, proyecto_nombre: str) -> str:
    """El código de la próxima versión (SF‑E9): prefijo y número del código de la última versión
    guardada, con el número del mayor código de ese prefijo más uno y su ancho (mínimo tres).

    `TI-001` → `TI-002`, `001` → `002`; con `001` y luego `TI-001` manda la última (`TI-002`).
    Un código sin número final se ignora; sin ninguno reconocible, `001`. Nunca devuelve un
    código que el proyecto ya tenga."""
    codigos = session.scalars(
        select(models.Presupuesto.codigo)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto_nombre)
        .order_by(models.Presupuesto.id)
    ).all()
    partes = [(m.group(1), m.group(2)) for c in codigos if (m := _CODIGO_VERSION.match(c))]
    prefijo = partes[-1][0] if partes else ""
    mismos = [numero for pref, numero in partes if pref == prefijo]
    ancho = max([len(numero) for numero in mismos], default=3)
    siguiente = max((int(numero) for numero in mismos), default=0) + 1
    existentes = set(codigos)
    while (candidato := f"{prefijo}{str(siguiente).zfill(max(ancho, 3))}") in existentes:
        siguiente += 1
    return candidato


def registros_de_version(
    session: Session, modelo: models.Presupuesto
) -> list[models.RegistroCambio]:
    """Los `RegistroCambio` que produjeron la versión, en el orden en que se registraron."""
    return list(
        session.scalars(
            select(models.RegistroCambio)
            .where(models.RegistroCambio.version_resultante_id == modelo.id)
            .order_by(models.RegistroCambio.id)
        )
    )


def tabla_trazabilidad(session: Session, modelo: models.Presupuesto) -> TablaExportable:
    """Los registros de la versión como la hoja Trazabilidad del Excel (spec §9.5): columnas de
    `COLUMNAS_TRAZABILIDAD`, con los códigos de las versiones de origen y resultante."""
    codigos = {
        fila.id: fila.codigo
        for fila in session.scalars(
            select(models.Presupuesto).where(models.Presupuesto.proyecto_id == modelo.proyecto_id)
        )
    }
    filas = tuple(
        (
            codigos.get(registro.version_origen_id, ""),
            codigos.get(registro.version_resultante_id, ""),
            registro.objeto,
            registro.clave,
            registro.campo,
            registro.valor_anterior,
            registro.valor_nuevo,
            registro.fuente,
            registro.responsable,
            registro.fecha_hora,
        )
        for registro in registros_de_version(session, modelo)
    )
    return TablaExportable(PESTANA_TRAZABILIDAD, COLUMNAS_TRAZABILIDAD, filas)
