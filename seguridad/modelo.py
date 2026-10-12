"""Tablas de la base de la instalación (`instalacion.db`; spec S3 §7.4; maestro §4.2).

Base propia (`Base`, `Base.metadata`): no comparte metadatos con `core.models`. Su destino de
migración es `migraciones/instalacion/` (revisión `ins_0001_seguridad`) y su lista
`METADATAS_INSTALACION` (`migraciones/metadatos.py`). Ninguna tabla guarda una contraseña, una
ficha de sesión ni un secreto de API en claro: solo huellas (Argon2 o SHA-256) y cifrados.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Metadatos de la base de la instalación."""


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(60), unique=True)  # normalizado, inmutable
    nombre: Mapped[str] = mapped_column(String(120))
    huella_clave: Mapped[str] = mapped_column(String(200))  # Argon2, nunca la contraseña
    roles: Mapped[str] = mapped_column(String(60))  # "arma,revisa" ordenado
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    debe_cambiar_clave: Mapped[bool] = mapped_column(Boolean, default=False)
    restablecida_por_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    creado: Mapped[datetime] = mapped_column(DateTime)
    creado_por: Mapped[str] = mapped_column(String(120), default="")


class IntentoAcceso(Base):
    """Contador por login normalizado; sirve igual para logins que existen y que no (S3 §5.4)."""

    __tablename__ = "intento_acceso"

    login_normalizado: Mapped[str] = mapped_column(String(60), primary_key=True)
    fallos_seguidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    ultimo_fallo: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class Sesion(Base):
    __tablename__ = "sesion"

    huella_ficha: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA-256 de la ficha
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    creada: Mapped[datetime] = mapped_column(DateTime)
    ultima_actividad: Mapped[datetime] = mapped_column(DateTime)
    cerrada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_cierre: Mapped[str] = mapped_column(String(40), default="")


class EventoAcceso(Base):
    """Registro de seguridad solo-agregar. Lo lee `operacion.respaldo` (`id`, `fecha_hora`)."""

    __tablename__ = "evento_acceso"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    login_intentado: Mapped[str] = mapped_column(String(60), default="")
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), default=None)
    ip_cliente: Mapped[str] = mapped_column(String(64), default="")
    tipo: Mapped[str] = mapped_column(String(30))
    detalle: Mapped[str] = mapped_column(Text, default="")


class CodigoInstalacion(Base):
    __tablename__ = "codigo_instalacion"

    huella: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA-256 del código
    creado: Mapped[datetime] = mapped_column(DateTime)
    usado: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    motivo: Mapped[str] = mapped_column(String(20))  # primera vez | restablecimiento


class EmpresaPropia(Base):
    """Una sola fila (`id` = 1): la empresa dueña de esta instalación (RV-6, P1)."""

    __tablename__ = "empresa_propia"
    __table_args__ = (CheckConstraint("id = 1", name="ck_empresa_propia_unica"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    rif: Mapped[str] = mapped_column(String(20))
    ciudad: Mapped[str] = mapped_column(String(80), default="")
    actualizada: Mapped[datetime] = mapped_column(DateTime)
    actualizada_por: Mapped[str] = mapped_column(String(120), default="")


class ClaveEmpresa(Base):
    """La clave de firma de la empresa propia. `privada_cifrada` es nula al retirar o revocar."""

    __tablename__ = "clave_empresa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    publica: Mapped[bytes] = mapped_column(LargeBinary)  # 32 B crudos
    huella: Mapped[str] = mapped_column(String(64))  # SHA-256 completo de la pública
    privada_cifrada: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    kdf: Mapped[str | None] = mapped_column(String(160), default=None)
    sal: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    estado: Mapped[str] = mapped_column(String(12))  # activa | retirada | revocada
    creada: Mapped[datetime] = mapped_column(DateTime)
    creada_por: Mapped[str] = mapped_column(String(120), default="")
    fecha_estado: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    motivo: Mapped[str] = mapped_column(String(300), default="")


class EmpresaRegistrada(Base):
    """Una empresa ajena cuya clave pública se registró (la que emite paquetes que se reciben)."""

    __tablename__ = "empresa_registrada"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa: Mapped[str] = mapped_column(String(200))
    rif: Mapped[str] = mapped_column(String(20), default="")
    publica: Mapped[bytes] = mapped_column(LargeBinary)
    huella: Mapped[str] = mapped_column(String(64))
    estado: Mapped[str] = mapped_column(String(12))  # activa | retirada | revocada
    comprobada_con: Mapped[str] = mapped_column(String(200))
    metodo: Mapped[str] = mapped_column(String(20))  # telefono | en persona | qr
    fecha_comprobacion: Mapped[datetime] = mapped_column(DateTime)
    registrada_por: Mapped[str] = mapped_column(String(120), default="")
    fecha_estado: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    motivo: Mapped[str] = mapped_column(String(300), default="")


class ClaveApi(Base):
    __tablename__ = "clave_api"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    identificador: Mapped[str] = mapped_column(String(8), unique=True)  # público, no es secreto
    huella_secreto: Mapped[str] = mapped_column(String(64))  # SHA-256 de un secreto de 256 bits
    creada: Mapped[datetime] = mapped_column(DateTime)
    creada_por: Mapped[str] = mapped_column(String(120), default="")
    ultimo_uso: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    revocada: Mapped[bool] = mapped_column(Boolean, default=False)
