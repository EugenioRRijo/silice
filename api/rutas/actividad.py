"""`/v1/actividad`: la actividad de una cuenta, como la página de actividad de GitHub (C10).

Solo lectura y sobre datos que ya se guardan (`aplicacion.actividad`): las versiones que guardó,
las que envió a aprobación, los dictámenes que dio y los libros que auditó.

Contrato:

- `GET /v1/actividad?usuario=<login>&desde=AAAA-MM-DD&hasta=AAAA-MM-DD` →
  `{usuario, desde, hasta, dias, cifras, eventos, recortado}`:
    - `usuario`: el login de la cuenta (por omisión, el de quien pregunta); `desde` y `hasta`, el
      rango con ambos días incluidos (por omisión, el último año: 365 días que acaban hoy).
    - `dias`: `[{fecha: "AAAA-MM-DD", cuantos}]`, solo los días con actividad, del más antiguo al
      más nuevo.
    - `cifras`: `{versiones_guardadas, versiones_enviadas, dictamenes, auditorias}` del período.
    - `eventos`: `[{fecha: "AAAA-MM-DDTHH:MM:SS", tipo, obra, archivo, texto}]`, lo más reciente
      primero (hasta 500); `tipo` es `version_guardada | version_enviada | dictamen | auditoria`;
      `obra` o `archivo` van vacíos cuando no aplican; `texto` es la frase corta en español.
    - `recortado`: verdadero si hubo más eventos que los devueltos (las cifras cuentan todos).
- Las versiones guardadas son las de la carpeta de trabajo abierta en la sesión.
- La ve la propia cuenta o quien tiene `administrar_cuentas`; la clave de API no es una persona y
  da 403. 403 sin ese permiso (sin decir si la cuenta existe), 404 si la cuenta no existe, 422 si
  `desde` es posterior a `hasta`. Toda respuesta lleva `Cache-Control: no-store`.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.dependencias import SesionDep, SesionInstalacionDep
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from aplicacion import actividad
from seguridad.cuentas import normalizar_login
from seguridad.permisos import Accion, permitido
from seguridad.sesiones import SesionActiva

MENSAJE_SIN_PERMISO = "Solo puede ver su propia actividad, o la de todos si administra las cuentas."
MENSAJE_SIN_CUENTA = "No hay una cuenta con ese usuario."
MENSAJE_RANGO = "La fecha «desde» no puede ser posterior a «hasta»."
MENSAJE_CON_CLAVE = "La actividad es de una persona: entre con su cuenta, no con la clave de API."
#: Cuántos días abarca el período por omisión (un año de calendario, como GitHub).
DIAS_POR_OMISION = 365

router = APIRouter(tags=["actividad"], route_class=RutaSinCache)

CuentaQueMira = Annotated[SesionActiva | None, Depends(exigir_clave_o_sesion(None))]


class DiaRespuesta(BaseModel):
    fecha: str
    cuantos: int


class CifrasRespuesta(BaseModel):
    versiones_guardadas: int
    versiones_enviadas: int
    dictamenes: int
    auditorias: int


class EventoRespuesta(BaseModel):
    fecha: str
    tipo: str
    obra: str
    archivo: str
    texto: str


class ActividadRespuesta(BaseModel):
    usuario: str
    desde: str
    hasta: str
    dias: list[DiaRespuesta]
    cifras: CifrasRespuesta
    eventos: list[EventoRespuesta]
    recortado: bool


@router.get("/v1/actividad", response_model=ActividadRespuesta)
def ver_actividad(
    activa: CuentaQueMira,
    instalacion: SesionInstalacionDep,
    caso: SesionDep,
    usuario: Annotated[str | None, Query(min_length=1, max_length=60)] = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> ActividadRespuesta:
    """La actividad de la cuenta `usuario` entre `desde` y `hasta` (por omisión, el último año)."""
    if activa is None:
        raise HTTPException(status_code=403, detail=MENSAJE_CON_CLAVE)
    login = normalizar_login(activa.login if usuario is None else usuario)
    es_propia = login == normalizar_login(activa.login)
    if not es_propia and not permitido(activa.roles, Accion.ADMINISTRAR_CUENTAS):
        raise HTTPException(status_code=403, detail=MENSAJE_SIN_PERMISO)
    if not actividad.cuenta_existe(instalacion, login):
        raise HTTPException(status_code=404, detail=MENSAJE_SIN_CUENTA)
    fin = hasta or ahora().date()
    inicio = desde or fin - timedelta(days=DIAS_POR_OMISION - 1)
    if inicio > fin:
        raise HTTPException(status_code=422, detail=MENSAJE_RANGO)
    resultado = actividad.actividad_de(instalacion, login, inicio, fin, caso=caso)
    return ActividadRespuesta(
        usuario=login,
        desde=inicio.isoformat(),
        hasta=fin.isoformat(),
        dias=[DiaRespuesta(fecha=d.fecha.isoformat(), cuantos=d.cuantos) for d in resultado.dias],
        cifras=CifrasRespuesta(
            versiones_guardadas=resultado.cifras.versiones_guardadas,
            versiones_enviadas=resultado.cifras.versiones_enviadas,
            dictamenes=resultado.cifras.dictamenes,
            auditorias=resultado.cifras.auditorias,
        ),
        eventos=[
            EventoRespuesta(
                fecha=e.fecha_hora.isoformat(timespec="seconds"),
                tipo=e.tipo,
                obra=e.obra,
                archivo=e.archivo,
                texto=e.texto,
            )
            for e in resultado.eventos
        ],
        recortado=resultado.recortado,
    )
