"""Auditoría de archivo de un DXF dañado, con la lectura con recuperación de `ezdxf` (S3 §11.1).

La importación pasaba por `ezdxf.readfile`, que o abre el archivo o falla, y la auditoría de
`ezdxf` nunca se ejecutaba. Ahora el archivo se lee con `ezdxf.recover.readfile`, que devuelve el
documento y un auditor con lo que arregló y lo que no. Lo que la biblioteca arregló se informa
(el plano sigue siendo importable); lo irrecuperable se rechaza con su mensaje (UC-14d).

No es una validación de seguridad: los analizadores en C++ de DXF/IFC quedan fuera (S3 §12).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import ezdxf
from ezdxf import recover

__all__ = ["Auditoria", "auditar_archivo", "texto_del_informe"]

#: Cuántos mensajes se citan en el informe; el resto se cuenta.
MENSAJES_VISIBLES = 5


@dataclass(frozen=True, slots=True)
class Auditoria:
    """Lo que `ezdxf` arregló (`reparaciones`) y lo que no pudo arreglar (`pendientes`)."""

    reparaciones: tuple[str, ...] = ()
    pendientes: tuple[str, ...] = ()

    @property
    def limpia(self) -> bool:
        return not (self.reparaciones or self.pendientes)


def _mensajes(entradas: Sequence) -> tuple[str, ...]:
    return tuple(" ".join(str(e.message).split()) for e in entradas)


def auditar_archivo(ruta: Path | str):
    """`(documento, Auditoria)` de un DXF con recuperación. Lanza lo que `ezdxf` lance si el
    archivo es irrecuperable (`DXFStructureError`, `OSError`...): el lector lo convierte en un
    rechazo con mensaje."""
    ruta = Path(ruta)
    if ruta.stat().st_size == 0:
        raise ezdxf.DXFStructureError("el archivo esta vacio")
    try:
        documento = ezdxf.readfile(str(ruta))  # el que importa: lectura normal, sin mutarlo
    except Exception:  # noqa: BLE001 - dañado: se reintenta con recuperación
        documento, auditor = recover.readfile(str(ruta))
        if len(documento.modelspace()) == 0:  # nada que rescatar: es un rechazo, no una reparación
            raise ezdxf.DXFStructureError("el archivo esta truncado o no tiene entidades") from None
        return documento, _resumen(auditor)
    # `audit()` borra lo que no entiende (p. ej. un INSERT sin bloque) y el importador sí lo
    # usa: se audita una segunda lectura, solo para informar lo que la biblioteca arreglaría
    return documento, _resumen(ezdxf.readfile(str(ruta)).audit())


def _resumen(auditor) -> Auditoria:
    return Auditoria(
        reparaciones=_mensajes(list(auditor.fixes)), pendientes=_mensajes(list(auditor.errors))
    )


def texto_del_informe(auditoria: Auditoria) -> list[str]:
    """Los ítems del informe de importación (uno por grupo), en lenguaje llano."""
    textos = []
    if auditoria.reparaciones:
        n = len(auditoria.reparaciones)
        citados = "; ".join(auditoria.reparaciones[:MENSAJES_VISIBLES])
        mas = f" (y {n - MENSAJES_VISIBLES} mas)" if n > MENSAJES_VISIBLES else ""
        textos.append(
            f"el plano tenia {n} {'error' if n == 1 else 'errores'} de estructura que se "
            f"repararon: {citados}{mas}"
        )
    if auditoria.pendientes:
        n = len(auditoria.pendientes)
        citados = "; ".join(auditoria.pendientes[:MENSAJES_VISIBLES])
        textos.append(
            f"el plano conserva {n} {'error' if n == 1 else 'errores'} de estructura que la "
            f"biblioteca no pudo reparar: {citados}"
        )
    return textos
