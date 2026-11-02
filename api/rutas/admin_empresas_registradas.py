"""Administración, pestaña «Empresas registradas» (UC-21; spec S3 §7; T5 de la migración final).

Paridad con `_pestana_registradas` y `_cambiar_registrada` de `ui/paginas/administracion.py`, sobre
`seguridad.empresas`:

- `GET /v1/admin/empresas-registradas` → `{registradas, metodos}`: las mismas columnas que la tabla
  de la clásica (empresa, huella corta, estado, con quién y cómo se comprobó) y los métodos de
  comprobación (`empresas.METODOS`) con su rótulo en español.
- `POST .../leer` (multipart `archivo`) → `{empresa, huella}`: lee el `.silice-clave` con el lector
  estricto y devuelve la empresa declarada y la huella **calculada**; no guarda nada.
- `POST ...` (multipart `archivo`, `huella`, `comprobada_con`, `metodo`): registra la clave ajena
  solo si la huella leída por otro canal coincide (`registrar_empresa_ajena`).
- `POST .../{id}/retirar` `{fecha}` (AAAA-MM-DD) y `POST .../{id}/revocar` (multipart `motivo` y,
  opcional, el `aviso` de revocación firmado).

Rol: `ADMINISTRAR_EMPRESA`, solo con sesión (la clave de API no administra; la clásica tampoco pide
el propio equipo aquí: no hay secretos). Los archivos vienen de fuera: tope de `TOPE_BYTES` (una
clave o un aviso ocupan menos de 1 KiB) y el lector JSON estricto de `seguridad` como guardia; el
422 no repite lo enviado.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from api.admin_acceso import administrar, sin_cache
from api.sesion_web import ahora
from api.sin_eco import RutaSinEco as _RutaSinEco
from api.sin_eco import sin_eco as _sin_eco
from operacion.instalacion import sesion_de_instalacion
from seguridad import empresas, firma
from seguridad.modelo import EmpresaRegistrada
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

TOPE_BYTES = 64 * 1024
MENSAJE_TOPE = "El archivo supera el máximo de 64 KiB."
MENSAJE_SIN_ARCHIVO = "Suba el archivo de la clave pública (.silice-clave)."
MENSAJE_REGISTRO_INVALIDO = (
    "Suba el archivo de la clave pública y escriba la huella, con quién y cómo se comprobó."
)
MENSAJE_FECHA_INVALIDA = "Indique la fecha del retiro como AAAA-MM-DD."
MENSAJE_REVOCACION_INVALIDA = "Escriba el motivo o suba el aviso de revocación."
#: Cómo se comprobó la huella, dicho en español (el valor guardado es el de `empresas.METODOS`).
ETIQUETAS_DE_METODO = {"telefono": "teléfono", "en persona": "en persona", "qr": "código QR"}
ERRORES_ESPERADOS = (empresas.ClaveError, ValueError)

router = APIRouter(
    prefix="/v1/admin/empresas-registradas",
    tags=["administracion"],
    dependencies=[Depends(sin_cache)],
    route_class=_RutaSinEco,
)
ADMIN = Depends(administrar(Accion.ADMINISTRAR_EMPRESA))


class Registrada(BaseModel):
    id: int
    empresa: str
    huella: str
    estado: str
    comprobada_con: str
    metodo: str


class Metodo(BaseModel):
    valor: str
    etiqueta: str


class RegistradasRespuesta(BaseModel):
    registradas: list[Registrada]
    metodos: list[Metodo]


class ClaveLeida(BaseModel):
    empresa: str
    huella: str


class Retiro(BaseModel):
    fecha: date


def _estado() -> RegistradasRespuesta:
    with sesion_de_instalacion() as bd:
        filas = bd.scalars(select(EmpresaRegistrada).order_by(EmpresaRegistrada.id)).all()
        return RegistradasRespuesta(
            registradas=[
                Registrada(
                    id=f.id,
                    empresa=f.empresa,
                    huella=firma.huella_corta(f.publica),
                    estado=f.estado,
                    comprobada_con=f.comprobada_con,
                    metodo=f.metodo,
                )
                for f in filas
            ],
            metodos=[
                Metodo(valor=m, etiqueta=ETIQUETAS_DE_METODO.get(m, m)) for m in empresas.METODOS
            ],
        )


def _rechazo(error: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(error))


def _contenido(archivo: UploadFile) -> bytes:
    """Los bytes de la subida; 413 si pasan de `TOPE_BYTES` (no se lee más allá del tope)."""
    datos = archivo.file.read(TOPE_BYTES + 1)
    if len(datos) > TOPE_BYTES:
        raise HTTPException(status_code=413, detail=MENSAJE_TOPE)
    return datos


@router.get("", response_model=RegistradasRespuesta, dependencies=[ADMIN])
def listar() -> RegistradasRespuesta:
    return _estado()


@router.post("/leer", response_model=ClaveLeida, dependencies=[ADMIN])
@_sin_eco(MENSAJE_SIN_ARCHIVO)
def leer(archivo: Annotated[UploadFile, File()]) -> ClaveLeida:
    """Lo que trae el archivo, con la huella que calcula el sistema; no se guarda nada."""
    try:
        leida = firma.leer_clave_publica(_contenido(archivo))
    except ValueError as error:
        raise _rechazo(error) from None
    return ClaveLeida(empresa=leida.nombre, huella=leida.huella_corta)


@router.post("", response_model=RegistradasRespuesta)
@_sin_eco(MENSAJE_REGISTRO_INVALIDO)
def registrar(
    archivo: Annotated[UploadFile, File()],
    huella: Annotated[str, Form()],
    metodo: Annotated[str, Form()],
    activa: Annotated[SesionActiva, ADMIN],
    comprobada_con: Annotated[str, Form()] = "",
) -> RegistradasRespuesta:
    """Registra la clave de otra empresa con la huella leída por otro canal."""
    contenido = _contenido(archivo)
    with sesion_de_instalacion() as bd:
        try:
            empresas.registrar_empresa_ajena(
                bd, contenido, huella, comprobada_con, metodo, activa.login, ahora()
            )
        except ERRORES_ESPERADOS as error:
            raise _rechazo(error) from None
    return _estado()


@router.post("/{empresa_id}/retirar", response_model=RegistradasRespuesta)
@_sin_eco(MENSAJE_FECHA_INVALIDA)
def retirar(
    empresa_id: int, datos: Retiro, activa: Annotated[SesionActiva, ADMIN]
) -> RegistradasRespuesta:
    """La empresa avisó que cambió de clave: sus paquetes anteriores a la fecha siguen valiendo."""
    with sesion_de_instalacion() as bd:
        try:
            empresas.retirar_ajena(
                bd, empresa_id, datetime.combine(datos.fecha, time.min), activa.login, ahora()
            )
        except ERRORES_ESPERADOS as error:
            raise _rechazo(error) from None
    return _estado()


@router.post("/{empresa_id}/revocar", response_model=RegistradasRespuesta)
@_sin_eco(MENSAJE_REVOCACION_INVALIDA)
def revocar(
    empresa_id: int,
    activa: Annotated[SesionActiva, ADMIN],
    motivo: Annotated[str, Form()] = "",
    aviso: Annotated[UploadFile | None, File()] = None,
) -> RegistradasRespuesta:
    """Ningún paquete con esa clave verifica después de revocarla."""
    # Un campo de archivo que el navegador manda vacío (sin nombre) cuenta como ausente.
    firmado = _contenido(aviso) if aviso is not None and aviso.filename else None
    if firmado is None and motivo.strip() == "":
        raise HTTPException(status_code=400, detail=MENSAJE_REVOCACION_INVALIDA)
    with sesion_de_instalacion() as bd:
        try:
            empresas.revocar_ajena(bd, empresa_id, motivo, activa.login, ahora(), firmado)
        except ERRORES_ESPERADOS as error:
            raise _rechazo(error) from None
    return _estado()
