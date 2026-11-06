"""Entregar el paquete auditado por la API (ola 4 de la sesión 2b; UC-22, RF-85; RM-3 y RM-4).

Es la página `ui/paginas/entregar.py` hecha servicio, sobre `aplicacion.entrega` (la misma lógica
que usa Streamlit):

- `GET /v1/entregas/versiones?proyecto=` → `[{codigo, moneda, aprobacion, ultima_aprobada}]`, la más
  nueva primero (T20: el estado de aprobación de cada versión y cuál es la última aprobada).
- `GET /v1/entregas/resumen?proyecto=&version=` → lo que se ve antes de pedir la contraseña.
- `POST /v1/entregas` `{proyecto, version, destinatario?, contrasena_clave?}` → el `.silice`
  (`application/zip`); `Content-Disposition`, `X-Silice-SHA256` y `X-Silice-Firmado` (`1`/`0`).

Todas exigen `ENTREGAR_PAQUETE` (rol arma) con sesión o clave de API. **Firmar** (hay clave de firma
activa) exige además el propio equipo y que no haya eventos de seguridad perdidos sin revisar
(`Sensible.FIRMAR`, RM-4: `aplicacion.equipo`); sin clave de firma el paquete sale «sin firma» y no
hace falta. Lo hace la ruta y no una dependencia porque la misma ruta sirve a las dos entregas.

La contraseña de la clave de firma: no se guarda, no se registra y no vuelve en ningún cuerpo (el
422 de esta ruta no repite lo enviado: `RutaSinEco`). Con la clave de API, quien entrega consta
como `USUARIO_SIN_CLAVE`. La base del caso no cambia; solo se escribe el registro de la entrega en
la base de la instalación. Los montos viajan como texto: `total` exacto y `total_texto` como lo
escribe la pantalla clásica (dos decimales).

Un fallo de la base al entregar (ocupada, ilegible) es un 503 con un texto fijo (`MENSAJE_BASE`,
sin SQL ni rutas) y no se genera paquete: la marca «Versión NO aprobada» solo dice «sin aprobada
previa» si la carpeta no tiene la tabla de aprobaciones (D4, plan de decisiones 2026-10-27).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.dependencias import USUARIO_SIN_CLAVE, SesionDep
from api.rutas.sesion import Detalle
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import aprobaciones
from aplicacion import entrega as logica
from aplicacion.equipo import operacion_sensible_permitida
from core import models
from core.budget import canonico
from core.verification.texto import formatear_decimal
from operacion.instalacion import sesion_de_instalacion
from operacion.version import version as version_de_silice
from paquete.formato import PaqueteRechazado
from seguridad import cuentas, empresas, eventos
from seguridad.empresas import ContrasenaDeClaveIncorrecta
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_CUERPO_INVALIDO = (
    "Indique la obra y la versión como texto; el destinatario y la contraseña de la clave de "
    "firma, si los usa, también."
)
MENSAJE_CLAVE_INCORRECTA = "La contraseña de la clave no es correcta."
MENSAJE_BASE = "No se pudo leer la carpeta de trabajo para entregar; no se generó el paquete."
MENSAJE_FRENO = (
    "Demasiados intentos fallidos con la contraseña de la clave de firma. Espere unos segundos y "
    "vuelva a probar."
)
#: Espera progresiva por fallos de la contraseña de la clave (del proceso, como la de las cuentas).
FRENO_FIRMA = cuentas.FrenoGlobal()
SIN_CACHE = {"Cache-Control": "no-store"}  # un paquete y su resumen no se guardan en el navegador


class _RutaEntregas(RutaSinEco):
    mensaje_por_omision = MENSAJE_CUERPO_INVALIDO


router = APIRouter(prefix="/v1/entregas", tags=["entregas"], route_class=_RutaEntregas)
ENTREGAR = Depends(exigir_clave_o_sesion(Accion.ENTREGAR_PAQUETE))


class VersionEntregable(BaseModel):
    codigo: str
    moneda: str
    #: Uno de `aprobaciones.ESTADOS` (`guardada` si nunca se envió).
    aprobacion: str
    #: Es la versión del último dictamen que aprobó (no la de número más alto).
    ultima_aprobada: bool


class ResumenRespuesta(BaseModel):
    """`entregable` es `false` si la versión se selló antes de la corrección de cifras (VB-1): la
    cadena sigue íntegra, pero entregarla se rechaza (409) y hay que confirmar una versión nueva.
    El texto del aviso ya viaja al final de `mensaje_de_cadena`; la pantalla debe mostrarlo y
    deshabilitar «Entregar» cuando `entregable` es `false`."""

    proyecto: str
    version: str
    moneda: str
    total: str
    total_texto: str
    hallazgos_total: int
    hallazgos_por_severidad: dict[str, int]
    cadena_integra: bool
    mensaje_de_cadena: str
    entregable: bool
    empresa: str | None
    firma_disponible: bool
    viaja_con: list[str]


class EntregaPeticion(BaseModel):
    proyecto: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=40)
    destinatario: str | None = Field(default=None, max_length=200)
    contrasena_clave: str | None = Field(default=None, max_length=1024)

    def __repr_args__(self):  # la contraseña nunca sale en un repr, un log o un traceback
        return [(k, v) for k, v in super().__repr_args__() if k != "contrasena_clave"]


def _proyecto(sesion: Session, nombre: str) -> models.Proyecto:
    proyecto = sesion.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == nombre)
    ).first()
    if proyecto is None:
        raise HTTPException(404, f"La obra «{nombre}» no existe en este caso.")
    return proyecto


def _version(sesion: Session, proyecto: str, codigo: str) -> models.Presupuesto:
    for version in _proyecto(sesion, proyecto).presupuestos:
        if version.codigo == codigo:
            return version
    raise HTTPException(404, f"La obra «{proyecto}» no tiene la versión {codigo}.")


@router.get("/versiones", response_model=list[VersionEntregable], dependencies=[ENTREGAR])
def versiones(sesion: SesionDep, response: Response, proyecto: str) -> list[VersionEntregable]:
    """Las versiones del proyecto, la más nueva primero (como el selector de la pantalla)."""
    response.headers.update(SIN_CACHE)
    obra = _proyecto(sesion, proyecto)
    ordenadas = sorted(obra.presupuestos, key=lambda v: v.id, reverse=True)
    estados = aprobaciones.estados(sesion, str(obra.id))
    aprobada = aprobaciones.ultima_aprobada(sesion, str(obra.id))
    return [
        VersionEntregable(
            codigo=v.codigo,
            moneda=v.moneda,
            aprobacion=estados[v.codigo].estado if v.codigo in estados else "guardada",
            ultima_aprobada=v.codigo == aprobada,
        )
        for v in ordenadas
    ]


@router.get("/resumen", response_model=ResumenRespuesta, dependencies=[ENTREGAR])
def resumen(sesion: SesionDep, response: Response, proyecto: str, version: str) -> ResumenRespuesta:
    """Total, hallazgos, cadena, anexos, empresa y si hay clave de firma (UC-22 paso 2)."""
    response.headers.update(SIN_CACHE)
    elegida = _version(sesion, proyecto, version)
    with sesion_de_instalacion() as bd:
        datos = logica.resumen_de_entrega(sesion, bd, elegida)
    anexos = [a.removeprefix("anexos/").removesuffix(".json") for a in datos.anexos]
    return ResumenRespuesta(
        proyecto=proyecto,
        version=datos.codigo,
        moneda=elegida.moneda,
        total=canonico.texto_decimal(datos.total) or "0",
        total_texto=formatear_decimal(datos.total.quantize(Decimal("0.01"))),
        hallazgos_total=sum(datos.hallazgos_por_severidad.values()),
        hallazgos_por_severidad=dict(sorted(datos.hallazgos_por_severidad.items())),
        cadena_integra=datos.cadena_integra,
        mensaje_de_cadena=datos.mensaje_de_cadena,
        entregable=datos.entregable,
        empresa=datos.empresa,
        firma_disponible=datos.firma_disponible,
        viaja_con=["presupuesto", "informe", "cadena", *anexos],
    )


@router.post(
    "",
    response_class=Response,
    responses={
        200: {"content": {"application/zip": {}}},
        503: {
            "model": Detalle,
            "description": "La base de la carpeta no se pudo leer; no se generó el paquete.",
        },
    },
    dependencies=[ENTREGAR],  # antes de abrir la base del caso; FastAPI no la corre dos veces
)
@sin_eco(MENSAJE_CUERPO_INVALIDO)
def entregar(
    sesion: SesionDep,
    peticion: EntregaPeticion,
    request: Request,
    activa: Annotated[SesionActiva | None, ENTREGAR],
) -> Response:
    """Genera el `.silice` de la versión y lo entrega como descarga binaria."""
    elegida = _version(sesion, peticion.proyecto, peticion.version)
    with sesion_de_instalacion() as bd:
        firmar = empresas.clave_activa(bd) is not None
        ip = request.client.host if request.client else None
        usuario = USUARIO_SIN_CLAVE if activa is None else activa.usuario
        if firmar:
            permitida, motivo = operacion_sensible_permitida(ip)
            if not permitida:
                raise HTTPException(403, motivo)
            espera = FRENO_FIRMA.espera(ahora())
            if espera > 0:
                raise HTTPException(
                    429, MENSAJE_FRENO, headers={"Retry-After": str(int(espera) + 1)}
                )
        try:
            generada = logica.entregar(
                sesion,
                bd,
                elegida,
                usuario=usuario,
                ahora=ahora(),
                version_silice=version_de_silice(),
                destinatario=(peticion.destinatario or "").strip() or None,
                contrasena_clave=(peticion.contrasena_clave or "") if firmar else None,
                ip=ip or "",
            )
        except ContrasenaDeClaveIncorrecta:
            momento = ahora()
            FRENO_FIRMA.registrar_fallo(momento)
            eventos.registrar(
                bd, "fallo", momento, login=usuario[:60], ip=ip or "", detalle="clave de firma"
            )
            bd.commit()
            raise HTTPException(400, MENSAJE_CLAVE_INCORRECTA) from None
        except logica.EntregaRechazada as error:
            raise HTTPException(409, str(error)) from None
        except PaqueteRechazado as error:
            raise HTTPException(422, str(error)) from None
        except SQLAlchemyError:
            # la base ocupada o ilegible no se disfraza en el paquete (p. ej. como «sin aprobada
            # previa» en un manifiesto firmado): no se genera nada y el texto no trae SQL
            raise HTTPException(503, MENSAJE_BASE) from None
    return Response(
        content=generada.datos,
        media_type="application/zip",
        headers={
            **SIN_CACHE,
            "Content-Disposition": f'attachment; filename="{generada.nombre}"',
            "X-Silice-SHA256": generada.sha256,
            "X-Silice-Firmado": "1" if generada.firmado else "0",
        },
    )
