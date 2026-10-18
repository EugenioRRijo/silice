"""`POST /v1/auditorias`: auditar un presupuesto de otra herramienta (spec S3 §10; RF-88, UC-23e).

El cuerpo es JSON con tres claves: `documento` (el documento canónico, `core.budget.canonico`),
`fecha_evaluacion` (ISO, **obligatoria**: la misma petición da siempre el mismo informe; RP8-11) y,
opcional, `anexo_espacio`. Se lee con el lector estricto (sin `NaN`, claves duplicadas, cifras
fuera del patrón ni más de 64 niveles: 422). Reaudita en memoria con las reglas de ESTA
instalación (contexto de la API: R8-R10, R15 y R17 si viene el anexo de espacio; R11-R12 con lo
que traiga el documento; R13-R14 no) y devuelve el informe. **No guarda nada.** Los montos
viajan como texto.

La clave de API, el tope de cuerpo (20 MiB) y los hosts permitidos NO se repiten aquí: los pone
`api.proteccion` para toda la aplicación (`exigir_clave_api` en `api.main`, `LimiteDeCuerpo` y
`TrustedHostMiddleware` en `proteger`). Hay una sola firma de la clave.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependencias import SesionDep
from auditoria.reauditoria import Servicios, leer_documento_json, reauditar
from core.budget.canonico import DocumentoInvalido
from paquete.formato import PaqueteRechazado
from seguridad.json_estricto import JsonRechazado, leer_json

router = APIRouter(prefix="/v1", tags=["auditorias"])


def servicios_de_la_api(sesion: SesionDep) -> Servicios:
    """Los servicios de ESTA instalación (referencia MaPreX y tasas del BCV, S1). Las pruebas
    sustituyen esta dependencia."""
    from auditoria.servicios import servicios_de_la_instalacion

    return servicios_de_la_instalacion(sesion)


ServiciosDep = Annotated[Servicios, Depends(servicios_de_la_api)]


class HallazgoRespuesta(BaseModel):
    regla: str
    severidad: str
    descripcion: str
    origen_ids: list[str]
    impacto: str | None = None


class DiferenciaRespuesta(BaseModel):
    codigo_partida: str
    campo: str
    declarado: str
    recalculado: str
    monto: str


class AuditoriaRespuesta(BaseModel):
    fecha_evaluacion: str
    contextos: list[str]
    termino: bool
    avisos: list[str]
    total_recalculado: str | None
    hallazgos: list[HallazgoRespuesta]
    no_declarados: list[HallazgoRespuesta]
    diferencias: list[DiferenciaRespuesta]


def _bytes(objeto: Any) -> bytes:
    """El objeto ya leído por el lector estricto, otra vez como JSON. Una cifra que el cliente
    mandó como número (y el lector entregó como `Decimal`) vuelve como texto, y desde ahí la
    revisa el patrón estricto de siempre."""

    def convertir(valor: Any) -> str:
        if isinstance(valor, Decimal):
            return format(valor, "f")
        raise TypeError(f"valor no serializable: {type(valor).__name__}")

    return json.dumps(
        objeto, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=convertir
    ).encode()


def _texto(valor: Any) -> str | None:
    return None if valor is None else format(valor, "f")


def _hallazgo(h) -> HallazgoRespuesta:
    return HallazgoRespuesta(
        regla=h.regla,
        severidad=h.severidad.name,
        descripcion=h.descripcion,
        origen_ids=list(h.origen_ids),
        impacto=_texto(h.impacto),
    )


@router.post(
    "/auditorias",
    response_model=AuditoriaRespuesta,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["documento", "fecha_evaluacion"],
                        "properties": {
                            "documento": {"type": "object"},
                            "fecha_evaluacion": {"type": "string", "format": "date"},
                            "anexo_espacio": {"type": "object"},
                        },
                    }
                }
            },
        }
    },
)
async def auditar_documento(peticion: Request, servicios: ServiciosDep) -> AuditoriaRespuesta:
    cuerpo = await peticion.body()
    try:
        objeto = leer_json(cuerpo)
        if not isinstance(objeto, dict) or not isinstance(objeto.get("documento"), dict):
            raise HTTPException(422, "falta 'documento'")
        evaluacion = objeto.get("fecha_evaluacion")
        if not isinstance(evaluacion, str):
            raise HTTPException(422, "falta 'fecha_evaluacion'")
        fecha = date.fromisoformat(evaluacion)
        documento = leer_documento_json(_bytes(objeto["documento"]))
        espacio = objeto.get("anexo_espacio")
        if espacio is not None and not isinstance(espacio, dict):
            raise HTTPException(422, "'anexo_espacio' debe ser un objeto")
    except (JsonRechazado, DocumentoInvalido, PaqueteRechazado, ValueError, TypeError) as error:
        raise HTTPException(422, str(error)) from None
    try:
        r = await run_in_threadpool(
            reauditar,
            documento,
            servicios,
            fecha,
            espacio_json=_bytes(espacio) if espacio is not None else None,
        )
    except (PaqueteRechazado, ValueError) as error:
        raise HTTPException(422, str(error)) from None
    return AuditoriaRespuesta(
        fecha_evaluacion=fecha.isoformat(),
        contextos=list(r.contextos),
        termino=not r.no_termino,
        avisos=list(r.avisos),
        total_recalculado=_texto(r.total_recalculado),
        hallazgos=[_hallazgo(h) for h in (r.resultado.informe.hallazgos if r.resultado else ())],
        no_declarados=[_hallazgo(h) for h in r.nuevos],
        diferencias=[
            DiferenciaRespuesta(
                codigo_partida=d.codigo_partida,
                campo=d.campo,
                declarado=_texto(d.declarado) or "",
                recalculado=_texto(d.recalculado) or "",
                monto=_texto(d.monto) or "",
            )
            for d in r.diferencias
        ],
    )
