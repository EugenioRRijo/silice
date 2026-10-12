"""Tablas `paq_*` de la base del caso: lo que quien revisa guarda de cada paquete (S3 §7.4).

Como `esp_*`, viven en un `MetaData` propio y no llevan clave foránea a `core.models`: su destino
de migración es el del caso (`METADATAS_CASO`, revisión `caso_NNNN_s3_paquete`). Un paquete se
guarda por el SHA-256 de su archivo (único: el mismo archivo no se duplica, 23h). Nada de esto
entra a las versiones del caso ni al catálogo (DA-S3-7): el paquete se reaudita en memoria.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Connection,
    DateTime,
    Engine,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    insert,
    select,
)
from sqlalchemy.orm import Session

__all__ = [
    "METADATA_PAQUETE",
    "TABLAS",
    "buscar_por_huella",
    "crear_esquema_paquete",
    "dictamenes_de",
    "paquetes_del_proyecto",
    "paq_dictamen",
    "paq_recibido",
    "registrar_dictamen",
    "registrar_recibido",
]

METADATA_PAQUETE = MetaData()

paq_recibido = Table(
    "paq_recibido",
    METADATA_PAQUETE,
    Column("id", Integer, primary_key=True),
    Column("archivo", String(255), nullable=False),
    Column("huella_archivo", String(64), nullable=False, unique=True),
    Column("paquete_id", String(36), nullable=False),
    Column("destinatario", String(200), nullable=False),
    Column("ruta", String(500), nullable=False),
    Column("empresa_declarada", String(200), nullable=False),
    Column("empresa_verificada", String(200), nullable=False),
    Column("huella_clave", String(64), nullable=False),
    Column("estado", String(20), nullable=False),
    Column("proyecto", String(200), nullable=False),
    Column("codigo", String(40), nullable=False),
    Column("emitido", DateTime, nullable=False),
    Column("cadena", Text, nullable=False),
    Column("huellas_anexos", Text, nullable=False),
    Column("recibido_por", String(120), nullable=False),
    Column("fecha", DateTime, nullable=False),
)
paq_dictamen = Table(
    "paq_dictamen",
    METADATA_PAQUETE,
    Column("id", Integer, primary_key=True),
    Column("paquete_id", Integer, ForeignKey("paq_recibido.id"), nullable=False),
    Column("huella_archivo", String(64), nullable=False),
    Column("resultado", String(20), nullable=False),  # conforme | con observaciones | rechazado
    Column("notas", Text, nullable=False),
    Column("usuario", String(120), nullable=False),
    Column("fecha", DateTime, nullable=False),
    Column("estado_verificacion", String(20), nullable=False),
    Column("revisor_armo", Boolean, nullable=False),
)
TABLAS = (paq_recibido, paq_dictamen)
RESULTADOS = ("conforme", "con observaciones", "rechazado")


def crear_esquema_paquete(destino: Engine | Connection) -> None:
    """Crea las tablas `paq_*` que falten (las pruebas; en el producto las crea la revisión)."""
    METADATA_PAQUETE.create_all(destino)


def buscar_por_huella(sesion: Session, huella_archivo: str):
    """La fila de `paq_recibido` con ese SHA-256, o `None` (23h: ya se recibió este archivo)."""
    return (
        sesion.execute(select(paq_recibido).where(paq_recibido.c.huella_archivo == huella_archivo))
        .mappings()
        .first()
    )


def paquetes_del_proyecto(sesion: Session, proyecto: str, huella_clave: str):
    """Lo recibido del mismo proyecto y emisor, del más viejo al más nuevo (para §6.5)."""
    return (
        sesion.execute(
            select(paq_recibido)
            .where(paq_recibido.c.proyecto == proyecto, paq_recibido.c.huella_clave == huella_clave)
            .order_by(paq_recibido.c.id)
        )
        .mappings()
        .all()
    )


def registrar_recibido(sesion: Session, **valores) -> int:
    """Guarda un paquete recibido y devuelve su id. No confirma."""
    resultado = sesion.execute(insert(paq_recibido).values(**valores))
    return int(resultado.inserted_primary_key[0])


def registrar_dictamen(
    sesion: Session,
    *,
    paquete_id: int,
    huella_archivo: str,
    resultado: str,
    notas: str,
    usuario: str,
    fecha: datetime,
    estado_verificacion: str,
    revisor_armo: bool,
) -> int:
    """Guarda el dictamen atado al SHA-256 del archivo. Notas obligatorias salvo «conforme»."""
    if resultado not in RESULTADOS:
        raise ValueError(f"resultado desconocido: {resultado!r}; se espera {RESULTADOS}")
    if resultado != "conforme" and not notas.strip():
        raise ValueError("Un dictamen con observaciones o de rechazo necesita notas.")
    fila = sesion.execute(
        insert(paq_dictamen).values(
            paquete_id=paquete_id,
            huella_archivo=huella_archivo,
            resultado=resultado,
            notas=notas.strip(),
            usuario=usuario,
            fecha=fecha,
            estado_verificacion=estado_verificacion,
            revisor_armo=revisor_armo,
        )
    )
    return int(fila.inserted_primary_key[0])


def dictamenes_de(sesion: Session, huella_archivo: str):
    return (
        sesion.execute(
            select(paq_dictamen)
            .where(paq_dictamen.c.huella_archivo == huella_archivo)
            .order_by(paq_dictamen.c.id)
        )
        .mappings()
        .all()
    )
