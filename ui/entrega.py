"""Entregar el paquete auditado, sin Streamlit (spec S3 §8.2, UC-22; RF-85).

Orquesta lo que `core`, `paquete`, `seguridad` y `adapters.espacio` no pueden orquestar entre sí
(el núcleo no conoce a los demás): el anexo de espacio, los anexos de S1, S2 y S4, la cadena, el
informe del emisor, la firma y el registro en `evento_acceso`. La base del caso **no cambia**: lo
único que se escribe es el registro de la entrega en la base de la instalación.

`anexos_de_cadena` es el proveedor que `guardar_presupuesto(..., anexos_de=...)` y
`verificar_cadena` usan para que la cadena cubra el espacio de la versión: lo pasa todo
camino que escribe `esp_*` (la hoja, los sembradores).
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from adapters.espacio import cargar_espacio
from adapters.espacio.serie import espacio_a_objeto
from asistente import registro as registro_ia
from core import models
from core.budget import cadena, canonico
from core.contracts.verificacion import Severidad
from core.models.cadena import EslabonVersion
from paquete import anexos as anexos_paquete
from paquete.exportar import Emisor, construir_paquete
from paquete.formato import EXTENSION
from paquete.verificar import armar_cadena_json
from seguridad import empresas, eventos

__all__ = [
    "Entrega",
    "EstadoDeLaCadena",
    "EntregaRechazada",
    "Resumen",
    "anexos_de_cadena",
    "anexo_de_ia",
    "anexos_del_paquete",
    "con_anexos_de_cadena",
    "entregar",
    "estado_de_la_cadena",
    "nombre_de_archivo",
    "resumen_de_entrega",
]

NOMBRE_ANEXO_ESPACIO = "anexos/espacio.json"
FORMATO_INFORME = "silice-informe"


class EntregaRechazada(ValueError):  # noqa: N818
    """No se puede entregar; el mensaje dice por qué (22c, 22e, 22f)."""


def anexos_de_cadena(session: Session, version: models.Presupuesto) -> Mapping[str, bytes]:
    """Los anexos que la cadena cubre: solo el espacio, y solo si la versión lo tiene."""
    espacio = cargar_espacio(session, version.id)
    if espacio.vacio:
        return {}
    return {NOMBRE_ANEXO_ESPACIO: canonico.json_canonico(espacio_a_objeto(espacio))}


def anexo_de_ia(session: Session, version: models.Presupuesto) -> bytes | None:
    """`anexos/ia.json` del asistente (S4, `asistente.registro.anexo_ia`): las sesiones con
    propuestas aceptadas y guardadas hasta esta versión, sin fichas ni costos ni claves (RV-19).
    `None` si no hay ninguna o si la base aún no tiene el registro de IA."""
    try:
        return registro_ia.anexo_ia(session.connection(), version.proyecto.nombre, version.codigo)
    except SQLAlchemyError:
        return None


def anexos_del_paquete(
    session: Session, version: models.Presupuesto, ia: bytes | None = None
) -> dict[str, bytes]:
    """Los anexos que viajan: espacio (cubierto por la cadena), reajuste de S1, control de S2 y el
    registro de IA (el que se pasa en `ia` o, si no, el del asistente). Los de S1, S2 y S4 llevan
    huella por entrada y no tienen cadena propia (límite declarado)."""
    if ia is None:
        ia = anexo_de_ia(session, version)
    salida = dict(anexos_de_cadena(session, version))
    reajuste = anexos_paquete.anexo_de_tablas(
        session, "reajuste", anexos_paquete.TABLAS_DE_REAJUSTE, version.proyecto_id
    )
    control = anexos_paquete.anexo_de_tablas(
        session, "control", anexos_paquete.TABLAS_DE_CONTROL, version.proyecto_id
    )
    if reajuste is not None:
        salida["anexos/reajuste.json"] = reajuste
    if control is not None:
        salida["anexos/control.json"] = control
    if ia is not None:
        salida["anexos/ia.json"] = ia
    return salida


def _cadena_json(session: Session, version: models.Presupuesto) -> bytes:
    proyecto = version.proyecto
    codigos = {v.id: v.codigo for v in proyecto.presupuestos}
    eslabones = [
        e for e in cadena.eslabones_de(session, proyecto) if e.presupuesto_id <= version.id
    ]
    objetos, cambios = [], {}
    for e in eslabones:
        objetos.append(
            {
                "codigo": codigos[e.presupuesto_id],
                "anterior": e.anterior,
                "huella_contenido": e.huella_contenido,
                "huella_cambios": e.huella_cambios,
                "huella_anexos": e.huella_anexos,
                "huella_eslabon": e.huella_eslabon,
                "usuario": e.usuario,
                "fecha_hora": e.fecha_hora.isoformat(),
                "tipo": e.tipo,
                "version_formato": e.version_formato,
            }
        )
        registros = session.scalars(
            select(models.RegistroCambio)
            .where(models.RegistroCambio.version_resultante_id == e.presupuesto_id)
            .order_by(models.RegistroCambio.id)
        )
        filas = [cadena.fila_de_cambio(r) for r in registros]
        if filas:
            cambios[codigos[e.presupuesto_id]] = filas
    return canonico.json_canonico(armar_cadena_json(objetos, cambios))


def con_anexos_de_cadena(session: Session) -> Session:
    """La sesión de una pantalla que guarda versiones con su espacio: la cadena lo cubre."""
    return cadena.anexos_por_omision(session, anexos_de_cadena)


@dataclass(frozen=True, slots=True)
class EstadoDeLaCadena:
    """Lo que la pestaña Trazabilidad dice de la cadena de un proyecto (S3 §6.4 y §6.5)."""

    integra: bool
    mensaje: str
    declaracion: str | None  # «Versiones 001 a 004 selladas el …», si hay retroactivas


def estado_de_la_cadena(session: Session, proyecto_nombre: str) -> EstadoDeLaCadena | None:
    """Verifica la cadena del proyecto recalculando cada huella; `None` si el proyecto no existe."""
    proyecto = session.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == proyecto_nombre)
    ).first()
    if proyecto is None:
        return None
    resultado = cadena.verificar_cadena(session, proyecto, anexos_de=anexos_de_cadena)
    return EstadoDeLaCadena(
        resultado.integra,
        cadena.mensaje_de_cadena(resultado),
        cadena.texto_retroactivo(session, proyecto),
    )


@dataclass(frozen=True, slots=True)
class Resumen:
    """Lo que la pantalla muestra antes de pedir la contraseña (UC-22 paso 2)."""

    codigo: str
    total: Decimal
    hallazgos_por_severidad: Mapping[str, int]
    cadena_integra: bool
    mensaje_de_cadena: str
    empresa: str | None
    firma_disponible: bool
    anexos: tuple[str, ...]


def resumen_de_entrega(
    session: Session, instalacion: Session, version: models.Presupuesto
) -> Resumen:
    resultado = cadena.verificar_cadena(session, version.proyecto, anexos_de=anexos_de_cadena)
    empresa = empresas.empresa_propia(instalacion)
    severidades: dict[str, int] = {}
    for h in session.scalars(
        select(models.Hallazgo).where(models.Hallazgo.presupuesto_id == version.id)
    ):
        nombre = Severidad(h.severidad).name
        severidades[nombre] = severidades.get(nombre, 0) + 1
    return Resumen(
        codigo=version.codigo,
        total=sum((r.total for r in version.partidas), Decimal(0)),
        hallazgos_por_severidad=severidades,
        cadena_integra=resultado.integra,
        mensaje_de_cadena=cadena.mensaje_de_cadena(resultado),
        empresa=empresa.nombre if empresa else None,
        firma_disponible=empresas.clave_activa(instalacion) is not None,
        anexos=tuple(sorted(anexos_del_paquete(session, version))),
    )


@dataclass(frozen=True, slots=True)
class Entrega:
    datos: bytes
    nombre: str
    sha256: str
    paquete_id: str
    firmado: bool


def nombre_de_archivo(proyecto: str, codigo: str) -> str:
    """`PROYECTO-codigo.silice` con solo caracteres seguros."""
    limpio = "".join(c if c.isalnum() else "-" for c in proyecto).strip("-")[:60] or "proyecto"
    return f"{limpio}-{codigo}{EXTENSION}"


def entregar(
    session: Session,
    instalacion: Session,
    version: models.Presupuesto,
    *,
    usuario: str,
    ahora: datetime,
    version_silice: str,
    destinatario: str | None = None,
    contrasena_clave: str | None = None,
    ia: bytes | None = None,
) -> Entrega:
    """Genera el `.silice` de `version` en memoria. Con `contrasena_clave` lo firma (la UI ya
    exigió el propio equipo). `EntregaRechazada` si la cadena está rota (22c) o la versión no
    está sellada; `ContrasenaDeClaveIncorrecta` (22b) y `PaqueteRechazado` (22f) propagan."""
    resultado = cadena.verificar_cadena(session, version.proyecto, anexos_de=anexos_de_cadena)
    if not resultado.integra:
        raise EntregaRechazada(cadena.mensaje_de_cadena(resultado))
    eslabon = session.get(EslabonVersion, version.id)
    if eslabon is None:
        raise EntregaRechazada(f"La versión {version.codigo} no está sellada.")
    estructura = canonico.estructura(session, version)
    privada, huella_clave = None, None
    if contrasena_clave is not None:
        privada = empresas.abrir_privada(instalacion, contrasena_clave)
        huella_clave = empresas.clave_activa(instalacion).huella
    empresa = empresas.empresa_propia(instalacion)
    total = sum((r.total for r in version.partidas), Decimal(0))
    paquete_id = str(uuid.uuid4())
    datos = construir_paquete(
        presupuesto=canonico.json_canonico(estructura),
        informe=canonico.json_canonico(
            {
                "formato": FORMATO_INFORME,
                "version_formato": 1,
                "codigo": version.codigo,
                "hallazgos": estructura["hallazgos"],
            }
        ),
        cadena=_cadena_json(session, version),
        anexos=anexos_del_paquete(session, version, ia),
        emisor=Emisor(empresa.nombre if empresa else None, huella_clave, usuario),
        destinatario=destinatario,
        proyecto=version.proyecto.nombre,
        codigo=version.codigo,
        moneda=version.moneda,
        total=format(total, "f"),
        ultima_huella=eslabon.huella_eslabon,
        ahora=ahora,
        version_silice=version_silice,
        privada=privada,
        paquete_id=paquete_id,
    )
    sha = hashlib.sha256(datos).hexdigest()
    detalle = f"{paquete_id}; version {version.codigo}; sha256 {sha}"
    if privada is not None:
        eventos.registrar(instalacion, "firma", ahora, detalle=detalle)
    eventos.registrar(instalacion, "paquete exportado", ahora, detalle=detalle)
    instalacion.commit()
    return Entrega(
        datos,
        nombre_de_archivo(version.proyecto.nombre, version.codigo),
        sha,
        paquete_id,
        privada is not None,
    )
