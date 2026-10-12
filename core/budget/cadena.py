"""SL-E7: el registro encadenado con huellas SHA-256 (spec S3 §6.2 a §6.5; maestro §3.2, RV-7).

Cada versión lleva un eslabón que encadena su contenido, sus `RegistroCambio`, sus anexos y el
eslabón anterior del mismo proyecto:

    huella_contenido = SHA-256(documento canónico, SL-E8)
    huella_cambios   = SHA-256(JSON canónico de sus RegistroCambio, en orden de id)
    huella_anexos    = SHA-256(JSON canónico de [[nombre, SHA-256(bytes)], ...] ordenado)
    huella_eslabon   = SHA-256(JSON canónico de {anterior, codigo, contenido, cambios, anexos,
                                usuario, fecha_hora, tipo, version_formato})

**Sellado en el embudo.** No depende de una lista de caminos: `guardar_presupuesto` (el único
embudo) llama a `marcar_por_sellar`, y un evento `before_commit` de la sesión sella cada versión
pendiente en la MISMA transacción, cuando ya existen sus `RegistroCambio` y su gancho (la hoja
copia `esp_*` después del embudo). Una versión pendiente sin `usuario` impide confirmar
(`SelladoSinUsuario`; nada se escribe: el llamador hace `rollback`). El `commit` de un SAVEPOINT
no sella; el de la transacción raíz, sí. Un `rollback` olvida lo pendiente.

**Anexos.** `core` no interpreta los anexos de una versión: los da una función inyectada
(`anexos_de`), que corre al sellar y al verificar con las mismas reglas (hoy, el espacio `esp_*`,
que arma `ui.entrega.anexos_de_cadena`). Las entradas de S1 y S2 que viajan en el paquete NO
entran a la cadena: llevan su propia huella (límite declarado, S3 §8.1).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core import models
from core.budget import canonico
from core.models.cadena import TIPOS_DE_ESLABON, EslabonVersion

__all__ = [
    "anexos_ninguno",
    "anexos_por_omision",
    "GENESIS",
    "FalloDeCadena",
    "ResultadoCadena",
    "SelladoEnConflicto",
    "SelladoSinUsuario",
    "eslabones_de",
    "fila_de_cambio",
    "huella_de_anexos",
    "huella_de_cambios",
    "huella_de_filas_de_cambios",
    "huella_del_eslabon",
    "marcar_por_sellar",
    "mensaje_de_cadena",
    "sellar_historial",
    "sellar_version",
    "texto_retroactivo",
    "verificar_cadena",
]

GENESIS = "0" * 64
CLAVE_PENDIENTES = "silice_por_sellar"
CLAVE_ANEXOS = "silice_anexos_de"  # el proveedor de anexos de la sesión (S3 §6.2)

#: `anexos_de(session, version) -> {nombre: bytes}`. Lo que da la versión y `core` no interpreta.
AnexosDe = Callable[[Session, models.Presupuesto], Mapping[str, bytes]]


def anexos_ninguno(session: Session, version: models.Presupuesto) -> Mapping[str, bytes]:
    """El proveedor de anexos por omisión: la versión no trae ninguno."""
    return {}


class SelladoSinUsuario(ValueError):  # noqa: N818
    """Se intentó confirmar una versión sin `usuario`: nada se escribe (S3 §6.2, punto 3)."""


class SelladoEnConflicto(RuntimeError):  # noqa: N818
    """Otra transacción selló antes sobre el mismo eslabón: el borrador sigue en la pestaña."""


@dataclass(frozen=True, slots=True)
class FalloDeCadena:
    codigo_version: str
    motivo: str  # contenido | registro | anexo | eslabon | sin_sellar
    mensaje: str


@dataclass(frozen=True, slots=True)
class ResultadoCadena:
    integra: bool
    versiones: int
    fallo: FalloDeCadena | None = None


# --- huellas ---------------------------------------------------------------------------------


def _sha(octetos: bytes) -> str:
    return hashlib.sha256(octetos).hexdigest()


def fila_de_cambio(registro: models.RegistroCambio) -> list[str]:
    """Los ocho campos de un `RegistroCambio` que entran a la huella, en su orden."""
    return [
        registro.objeto,
        registro.clave,
        registro.campo,
        registro.valor_anterior,
        registro.valor_nuevo,
        registro.fuente,
        registro.responsable,
        registro.fecha_hora.isoformat(),
    ]


def huella_de_filas_de_cambios(filas: Sequence[Sequence[str]]) -> str:
    """La misma huella a partir de las filas ya extraídas: la usa el verificador del paquete,
    que solo tiene el JSON de `cadena.json` y no la base del emisor."""
    return _sha(canonico.json_canonico([list(fila) for fila in filas]))


def huella_de_cambios(registros: Sequence[models.RegistroCambio]) -> str:
    return huella_de_filas_de_cambios([fila_de_cambio(r) for r in registros])


def huella_de_anexos(anexos: Mapping[str, bytes]) -> str:
    return _sha(canonico.json_canonico([[n, _sha(anexos[n])] for n in sorted(anexos)]))


def huella_del_eslabon(
    *,
    anterior: str,
    codigo: str,
    contenido: str,
    cambios: str,
    anexos: str,
    usuario: str,
    fecha_hora: datetime,
    tipo: str,
    version_formato: int,
) -> str:
    return _sha(
        canonico.json_canonico(
            {
                "anterior": anterior,
                "codigo": codigo,
                "contenido": contenido,
                "cambios": cambios,
                "anexos": anexos,
                "usuario": usuario,
                "fecha_hora": fecha_hora.isoformat(),
                "tipo": tipo,
                "version_formato": version_formato,
            }
        )
    )


def _registros(session: Session, version: models.Presupuesto) -> list[models.RegistroCambio]:
    return list(
        session.scalars(
            select(models.RegistroCambio)
            .where(models.RegistroCambio.version_resultante_id == version.id)
            .order_by(models.RegistroCambio.id)
        )
    )


# --- sellar ----------------------------------------------------------------------------------


def eslabones_de(session: Session, proyecto: models.Proyecto) -> list[EslabonVersion]:
    """Los eslabones del proyecto en el orden de sus versiones."""
    return list(
        session.scalars(
            select(EslabonVersion)
            .where(EslabonVersion.proyecto_id == proyecto.id)
            .order_by(EslabonVersion.presupuesto_id)
        )
    )


def _cabeza(session: Session, proyecto_id: int) -> str:
    """La `huella_eslabon` del último eslabón del proyecto (génesis si no hay)."""
    eslabones = list(
        session.scalars(select(EslabonVersion).where(EslabonVersion.proyecto_id == proyecto_id))
    )
    if not eslabones:
        return GENESIS
    referidas = {e.anterior for e in eslabones}
    cabezas = [e.huella_eslabon for e in eslabones if e.huella_eslabon not in referidas]
    if len(cabezas) != 1:
        raise SelladoEnConflicto("La cadena del proyecto se bifurcó: revise con el administrador.")
    return cabezas[0]


def sellar_version(
    session: Session,
    version: models.Presupuesto,
    usuario: str,
    *,
    anexos_de: AnexosDe = anexos_ninguno,
    tipo: str = "normal",
    ahora: datetime | None = None,
) -> EslabonVersion:
    """Escribe el eslabón de `version` en la transacción en curso (no confirma)."""
    if not usuario or not usuario.strip():
        raise SelladoSinUsuario("Falta el usuario: toda versión se confirma a nombre de alguien.")
    if tipo not in TIPOS_DE_ESLABON:
        raise ValueError(f"tipo de eslabon desconocido: {tipo!r}")
    session.flush()
    if session.get(EslabonVersion, version.id) is not None:
        raise ValueError(f"La version {version.codigo} ya esta sellada.")
    anterior = _cabeza(session, version.proyecto_id)
    contenido = canonico.huella(canonico.documento(session, version))
    cambios = huella_de_cambios(_registros(session, version))
    anexos = huella_de_anexos(anexos_de(session, version))
    fecha_hora = ahora or datetime.now()
    eslabon = EslabonVersion(
        presupuesto_id=version.id,
        proyecto_id=version.proyecto_id,
        anterior=anterior,
        huella_contenido=contenido,
        huella_cambios=cambios,
        huella_anexos=anexos,
        huella_eslabon=huella_del_eslabon(
            anterior=anterior,
            codigo=version.codigo,
            contenido=contenido,
            cambios=cambios,
            anexos=anexos,
            usuario=usuario,
            fecha_hora=fecha_hora,
            tipo=tipo,
            version_formato=canonico.VERSION_FORMATO,
        ),
        usuario=usuario,
        fecha_hora=fecha_hora,
        tipo=tipo,
        version_formato=canonico.VERSION_FORMATO,
    )
    session.add(eslabon)
    try:
        session.flush()
    except IntegrityError as error:
        raise SelladoEnConflicto(
            "Otra persona guardó antes sobre la misma versión. Su borrador sigue aquí; "
            "vuelva a abrir la versión vigente y repita el cambio."
        ) from error
    return eslabon


def anexos_por_omision(session: Session, anexos_de: AnexosDe) -> Session:
    """Fija el proveedor de anexos de TODA versión que esta sesión guarde sin pasar el suyo.
    Quien arma la sesión de una pantalla que escribe `esp_*` junto con la versión lo llama una vez
    (`ui.entrega.con_anexos_de_cadena`): así la cadena cubre el espacio sin que cada llamador del
    embudo tenga que acordarse de pasar `anexos_de`."""
    session.info[CLAVE_ANEXOS] = anexos_de
    return session


def marcar_por_sellar(
    session: Session,
    version: models.Presupuesto,
    usuario: str | None,
    anexos_de: AnexosDe | None = None,
) -> None:
    """Lo llama `guardar_presupuesto`: la versión se sella al confirmar la transacción raíz."""
    proveedor = anexos_de or session.info.get(CLAVE_ANEXOS) or anexos_ninguno
    session.info.setdefault(CLAVE_PENDIENTES, []).append((version, usuario, proveedor))


def _sellar_pendientes(session: Session) -> None:
    pendientes = session.info.get(CLAVE_PENDIENTES)
    if not pendientes or session.in_nested_transaction():
        return
    session.info[CLAVE_PENDIENTES] = []  # antes de sellar: los flush de abajo no reentran
    session.flush()
    for version, usuario, _ in pendientes:
        if not usuario or not usuario.strip():
            raise SelladoSinUsuario(
                f"La version {version.codigo} se guardo sin usuario: no se puede confirmar."
            )
    en_curso = {version.id for version, _, _ in pendientes}
    for version, usuario, anexos_de in sorted(pendientes, key=lambda p: p[0].id):
        _sellar_anteriores_sin_eslabon(session, version, usuario, anexos_de, en_curso)
        sellar_version(session, version, usuario, anexos_de=anexos_de)


def _sellar_anteriores_sin_eslabon(
    session: Session,
    version: models.Presupuesto,
    usuario: str,
    anexos_de: AnexosDe,
    en_curso: set[int],
) -> None:
    """S3 §6.5: un proyecto con versiones de antes de S3 las sella primero, una vez, de forma
    retroactiva y en orden de `id`, para que la cadena no tenga huecos aunque el primer guardado
    no pase por la interfaz (la API y los scripts también guardan versiones)."""
    previas = sorted(
        (
            v
            for v in version.proyecto.presupuestos
            if v.id < version.id
            and v.id not in en_curso
            and session.get(EslabonVersion, v.id) is None
        ),
        key=lambda v: v.id,
    )
    for previa in previas:
        sellar_version(session, previa, usuario, anexos_de=anexos_de, tipo="retroactivo")


def _olvidar_pendientes(session: Session) -> None:
    session.info.pop(CLAVE_PENDIENTES, None)


if not event.contains(Session, "before_commit", _sellar_pendientes):
    event.listen(Session, "before_commit", _sellar_pendientes)
    event.listen(Session, "after_rollback", _olvidar_pendientes)


# --- historial y verificación ----------------------------------------------------------------


def sellar_historial(
    session: Session,
    usuario: str,
    *,
    anexos_de: AnexosDe = anexos_ninguno,
    ahora: datetime | None = None,
) -> tuple[str, ...]:
    """Sella, una vez y de forma declarada, las versiones que existían antes de S3: por
    proyecto y en orden de `id`, con `tipo = "retroactivo"`. Devuelve `proyecto/codigo` de cada
    una. No confirma. Una versión se puede sellar aunque ya no recargue: el documento sale de
    las filas."""
    ahora = ahora or datetime.now()
    selladas: list[str] = []
    for proyecto in session.scalars(select(models.Proyecto).order_by(models.Proyecto.id)):
        for version in sorted(proyecto.presupuestos, key=lambda v: v.id):
            if session.get(EslabonVersion, version.id) is None:
                sellar_version(
                    session, version, usuario, anexos_de=anexos_de, tipo="retroactivo", ahora=ahora
                )
                selladas.append(f"{proyecto.nombre}/{version.codigo}")
    return tuple(selladas)


def texto_retroactivo(session: Session, proyecto: models.Proyecto) -> str | None:
    """La declaración de S3 §6.5, o `None` si el proyecto no tiene versiones retroactivas."""
    versiones = {v.id: v for v in proyecto.presupuestos}
    retro = [e for e in eslabones_de(session, proyecto) if e.tipo == "retroactivo"]
    if not retro:
        return None
    codigos = [versiones[e.presupuesto_id].codigo for e in retro]
    rango = codigos[0] if len(codigos) == 1 else f"{codigos[0]} a {codigos[-1]}"
    cuando = min(e.fecha_hora for e in retro).date().isoformat()
    plural = "Versión" if len(codigos) == 1 else "Versiones"
    return (
        f"{plural} {rango} selladas el {cuando}: prueban que no cambiaron desde esa fecha; "
        "antes no hay garantía."
    )


_MOTIVOS = {
    "contenido": "su contenido no coincide con su huella",
    "registro": "su registro de cambios no coincide con su huella",
    "anexo": "uno de sus anexos no coincide con su huella",
    "eslabon": "su eslabón no coincide con el anterior o con su propia huella",
    "sin_sellar": "no tiene eslabón",
}


def mensaje_de_cadena(resultado: ResultadoCadena) -> str:
    """El texto de la pestaña Trazabilidad y de la entrega (S3 §6.4)."""
    if resultado.integra:
        return f"Cadena íntegra: {resultado.versiones} versiones"
    fallo = resultado.fallo
    assert fallo is not None
    return (
        f"Cadena rota en la versión {fallo.codigo_version}: {_MOTIVOS[fallo.motivo]}; alguien "
        "cambió la base fuera del sistema. Revíselo con el administrador antes de entregar un "
        "paquete."
    )


def verificar_cadena(
    session: Session, proyecto: models.Proyecto, *, anexos_de: AnexosDe = anexos_ninguno
) -> ResultadoCadena:
    """RECALCULA cada huella desde la base y devuelve el primer fallo."""
    versiones = sorted(proyecto.presupuestos, key=lambda v: v.id)
    por_version = {e.presupuesto_id: e for e in eslabones_de(session, proyecto)}
    anterior = GENESIS
    for numero, version in enumerate(versiones):
        eslabon = por_version.get(version.id)
        if eslabon is None:
            return _roto(numero, version, "sin_sellar")
        contenido = canonico.huella(canonico.documento(session, version))
        cambios = huella_de_cambios(_registros(session, version))
        anexos = huella_de_anexos(anexos_de(session, version))
        if contenido != eslabon.huella_contenido:
            return _roto(numero, version, "contenido")
        if cambios != eslabon.huella_cambios:
            return _roto(numero, version, "registro")
        if anexos != eslabon.huella_anexos:
            return _roto(numero, version, "anexo")
        esperado = huella_del_eslabon(
            anterior=eslabon.anterior,
            codigo=version.codigo,
            contenido=contenido,
            cambios=cambios,
            anexos=anexos,
            usuario=eslabon.usuario,
            fecha_hora=eslabon.fecha_hora,
            tipo=eslabon.tipo,
            version_formato=eslabon.version_formato,
        )
        if eslabon.anterior != anterior or esperado != eslabon.huella_eslabon:
            return _roto(numero, version, "eslabon")
        anterior = eslabon.huella_eslabon
    return ResultadoCadena(True, len(versiones))


def _roto(numero: int, version: models.Presupuesto, motivo: str) -> ResultadoCadena:
    fallo = FalloDeCadena(version.codigo, motivo, _MOTIVOS[motivo])
    return ResultadoCadena(False, numero, fallo)
