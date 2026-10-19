"""`/v1/auditorias-libro`: el historial de auditorias de «Libro de la empresa» (UC-30; RF-145/146).

Solo lectura. Cada auditoria de UC-25 (libro o PDF simple) deja guardado su resumen y sus
hallazgos compactos (`fusion.historial`); el libro y el PDF no se guardan nunca (RNF-28). Quien
escribe es `POST /v1/libros/auditoria` y `/pdf`, no esta ruta.

- `GET /v1/auditorias-libro?limite=N`: las `N` mas recientes (1 a 100; 20 por omision), la ultima
  primero, como lista de `{id, archivo, fecha, tipo, errores, advertencias}`. Es el contrato que
  consume el Inicio de la interfaz nueva; `fecha` es ISO con hora (`2026-10-18T14:03:05`).
- `GET /v1/auditorias-libro/{id}`: el resumen completo y los hallazgos compactos
  (`regla`, `hoja`, `celda`, `severidad`, `mensaje`); 404 si no existe.

Los montos viajan como texto decimal exacto. El acceso (clave de API, o cuenta que arma o revisa)
lo exige `api.main` con `exigir_clave_o_sesion(Accion.LEER_PROYECTO)`. Errores: `{"detalle": ...}`.
Toda respuesta, también las de error, lleva `Cache-Control: no-store` (`api.sin_cache`).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.dependencias import SesionInstalacionDep
from api.sin_cache import RutaSinCache
from fusion.historial import (
    AuditoriaGuardada,
    AuditoriaInexistente,
    ResumenAuditoria,
    detalle,
    listar,
)

router = APIRouter(
    prefix="/v1/auditorias-libro", tags=["auditorias-libro"], route_class=RutaSinCache
)

LIMITE_POR_OMISION = 20
LIMITE_MAXIMO = 100


class AuditoriaResumenRespuesta(BaseModel):
    id: int
    archivo: str
    fecha: str
    tipo: Literal["libro", "pdf"]
    errores: int
    advertencias: int


class HallazgoGuardadoRespuesta(BaseModel):
    regla: str
    hoja: str
    celda: str
    severidad: str
    mensaje: str


class AuditoriaDetalleRespuesta(AuditoriaResumenRespuesta):
    usuario: str
    sha256: str
    fecha_libro: str | None
    total_libro: str | None
    total_silice: str | None
    informativos: int
    atipicos: int
    recortado: bool
    hallazgos: list[HallazgoGuardadoRespuesta]


def _fecha(valor: datetime) -> str:
    return valor.isoformat(timespec="seconds")


def _monto(valor: Decimal | None) -> str | None:
    return None if valor is None else format(valor, "f")


def _dia(valor: date | None) -> str | None:
    return None if valor is None else valor.isoformat()


def _resumen(r: ResumenAuditoria) -> AuditoriaResumenRespuesta:
    return AuditoriaResumenRespuesta(
        id=r.id,
        archivo=r.nombre_archivo,
        fecha=_fecha(r.fecha_hora),
        tipo=r.tipo,  # type: ignore[arg-type]  # la tabla solo admite 'libro' o 'pdf'
        errores=r.errores,
        advertencias=r.advertencias,
    )


def _detalle(a: AuditoriaGuardada) -> AuditoriaDetalleRespuesta:
    return AuditoriaDetalleRespuesta(
        id=a.id,
        archivo=a.nombre_archivo,
        fecha=_fecha(a.fecha_hora),
        tipo=a.tipo,  # type: ignore[arg-type]  # la tabla solo admite 'libro' o 'pdf'
        errores=a.errores,
        advertencias=a.advertencias,
        usuario=a.usuario,
        sha256=a.sha256,
        fecha_libro=_dia(a.fecha_libro),
        total_libro=_monto(a.total_libro),
        total_silice=_monto(a.total_silice),
        informativos=a.informativos,
        atipicos=a.atipicos,
        recortado=a.recortado,
        hallazgos=[
            HallazgoGuardadoRespuesta(
                regla=h.regla, hoja=h.hoja, celda=h.celda, severidad=h.severidad, mensaje=h.mensaje
            )
            for h in a.hallazgos
        ],
    )


@router.get("", response_model=list[AuditoriaResumenRespuesta])
def listar_auditorias(
    sesion: SesionInstalacionDep,
    limite: Annotated[int, Query(ge=1, le=LIMITE_MAXIMO)] = LIMITE_POR_OMISION,
) -> list[AuditoriaResumenRespuesta]:
    """Las auditorias mas recientes de la instalacion, la ultima primero."""
    return [_resumen(r) for r in listar(sesion, limite)]


@router.get("/{auditoria_id}", response_model=AuditoriaDetalleRespuesta)
def ver_auditoria(auditoria_id: int, sesion: SesionInstalacionDep) -> AuditoriaDetalleRespuesta:
    """El resumen y los hallazgos compactos de una auditoria guardada."""
    try:
        return _detalle(detalle(sesion, auditoria_id))
    except AuditoriaInexistente as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
