"""Construir el `.silice` (spec S3 §8.1 y §8.2; maestro §4.5).

`construir_paquete` recibe los bytes ya generados de cada archivo (el documento canónico, el
informe, la cadena y los anexos) y arma el ZIP: el manifiesto lleva el SHA-256 y el tamaño de cada
archivo, la huella de todos los anexos y la última huella de la cadena; la firma cubre el
manifiesto con el prefijo de dominio de paquete. **No viaja el Excel** (DA-S3-10): el revisor lo
regenera. El ZIP es reproducible (fechas fijas, orden fijo): con el mismo `paquete_id` y la misma
fecha, los mismos bytes.
"""

from __future__ import annotations

import hashlib
import io
import uuid
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from core.budget.canonico import json_canonico
from paquete.formato import (
    ANEXOS_ADMITIDOS,
    FORMATO_PAQUETE,
    NOMBRE_FIRMA,
    NOMBRE_MANIFIESTO,
    VERSION_FORMATO,
    PaqueteRechazado,
    comprobar_salida,
    huella_de_anexos,
)
from seguridad import firma

__all__ = ["Emisor", "construir_paquete"]

FECHA_FIJA_ZIP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True, slots=True)
class Emisor:
    """Quién emite: la empresa y la huella COMPLETA de su clave (o `None` sin firma) y el
    usuario que entregó. No hay no repudio individual: es lo que declara el emisor (SEG-6)."""

    empresa: str | None
    huella_clave: str | None
    usuario: str


def _sha(octetos: bytes) -> str:
    return hashlib.sha256(octetos).hexdigest()


def construir_paquete(
    *,
    presupuesto: bytes,
    informe: bytes,
    cadena: bytes,
    anexos: Mapping[str, bytes],
    emisor: Emisor,
    destinatario: str | None,
    proyecto: str,
    codigo: str,
    moneda: str,
    total: str,
    ultima_huella: str,
    ahora: datetime,
    version_silice: str,
    privada: bytes | None = None,
    paquete_id: str | None = None,
) -> bytes:
    """El archivo `.silice`. Con `privada`, lo firma; sin ella, queda «sin firma»."""
    desconocidos = sorted(set(anexos) - set(ANEXOS_ADMITIDOS))
    if desconocidos:
        raise PaqueteRechazado(f"anexo no admitido por el formato v1: {desconocidos[0]!r}")
    if privada is not None and not emisor.huella_clave:
        raise ValueError("para firmar hace falta la huella de la clave del emisor")
    archivos = {
        "presupuesto.json": presupuesto,
        "informe.json": informe,
        "cadena.json": cadena,
        **anexos,
    }
    manifiesto = json_canonico(
        {
            "formato": FORMATO_PAQUETE,
            "version_formato": VERSION_FORMATO,
            "version_silice": version_silice,
            "paquete_id": paquete_id or str(uuid.uuid4()),
            "emitido": ahora.isoformat(timespec="seconds"),
            "empresa": emisor.empresa,
            "huella_clave": emisor.huella_clave,
            "usuario_emisor": emisor.usuario,
            "destinatario": destinatario or None,
            "proyecto": proyecto,
            "codigo": codigo,
            "moneda": moneda,
            "total": total,
            "archivos": [
                {"nombre": n, "sha256": _sha(archivos[n]), "tamano": len(archivos[n])}
                for n in sorted(archivos)
            ],
            "huella_anexos": huella_de_anexos(anexos),
            "ultima_huella_eslabon": ultima_huella,
            "algoritmo": "Ed25519",
        }
    )
    contenido: dict[str, bytes] = {NOMBRE_MANIFIESTO: manifiesto}
    if privada is not None:
        contenido[NOMBRE_FIRMA] = firma.firmar(privada, firma.DOMINIO_PAQUETE, manifiesto)
    contenido.update({n: archivos[n] for n in sorted(archivos)})
    flujo = io.BytesIO()
    with zipfile.ZipFile(flujo, "w", zipfile.ZIP_DEFLATED) as zip_:
        for nombre, octetos in contenido.items():
            info = zipfile.ZipInfo(nombre, date_time=FECHA_FIJA_ZIP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zip_.writestr(info, octetos)
    datos = flujo.getvalue()
    comprobar_salida(contenido, len(datos))
    return datos
