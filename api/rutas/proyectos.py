"""`GET /v1/proyectos`: los proyectos del caso de la sesión (ola 0a de la sesión 2b).

`[{codigo, nombre, version_vigente, version_codigo, actualizado}]`, en orden alfabético, sobre
`aplicacion.proyectos.proyectos_del_caso` con la sesión del caso de la petición (RM-2):

- `codigo`: el identificador del proyecto en la base, como texto (el modelo no tiene otro código);
- `version_vigente`: el `id` de la versión vigente (el presupuesto de mayor `id` no descartado, la
  misma regla que la barra de Streamlit), o `null` sin versiones;
- `version_codigo`: el código de esa versión, el que muestra la barra (agregado al contrato del
  plan: el selector lo necesita para rotularla); `actualizado`: su fecha ISO, o `null`.

`LEER_PROYECTO` (arma y revisa), como la barra y el Tablero.

`POST /v1/proyectos` (BCP-3, diseño `2026-10-21-bienvenida-casos-proyectos-design.md` §5): crea un
proyecto en el caso de la petición (el de la ficha, RM-2) con `EDITAR_HOJA` (clave de API o sesión).
`{nombre ≤ 120, moneda: "Bs"|"USD"|null, dominio: ""|civil|telecom|industrial|sistemas,
descripcion ≤ 500, cliente ≤ 200, ubicacion ≤ 200,
carpeta}` → 201 con la forma de un elemento de la lista
(`version_vigente: null`). MOD-3a: `cliente` y `ubicacion` (vacíos por omisión) son la ficha de la
obra (`aplicacion.obras`), guardada en la misma transacción que el proyecto; `GET` los repite. El
responsable de la moneda es la cuenta de la sesión (`Nombre <login>`, RF-82) o, con clave de API,
`USUARIO_API`. Va sobre la sesión de escritura (`BEGIN IMMEDIATE`): dos peticiones con el mismo
nombre dan 201 y 409.

`carpeta` (opcional; rediseño del marco, Tarea 6b): la carpeta donde se crea la obra, el nombre que
lista `GET /v1/obras/todas` (`Obra Norte.db`) o `"empresa"` para la carpeta de la empresa (la del
proceso; el `null` de esa lista no cabe aquí porque `null` es «la de la sesión»). Sin `carpeta`, o
con la que ya tiene la sesión, todo sigue como arriba. Con otra: exige `CAMBIAR_CASO` (403; 409 con
la clave de API, que trabaja en la carpeta del proceso), valida el nombre como
`POST /v1/casos/actual` (`aplicacion.casos.carpeta_de_la_lista`: 422 con un texto fijo, sin repetir
lo enviado, si lleva rutas, `..` o no es una carpeta que existe; no se crea ningún archivo) y crea
la obra allí, con su ficha y su moneda, en una sola transacción de esa carpeta. **No** cambia la
carpeta de la sesión ni olvida sus borradores. Un nombre de carpeta real que sea exactamente
`empresa` (sin `.db`) se manda con su extensión.

Errores: 409 repetido; 422 vacío, moneda o tipo de obra (textos con tilde,
DV-BCP-3). El 422 de forma no repite lo enviado (`RutaSinEco`).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.acceso import LEER
from api.dependencias import (
    USUARIO_API,
    SesionDeEscrituraDep,
    SesionDep,
    obtener_motor,
    ruta_de_url,
    url_de_la_peticion,
    url_de_ruta,
    url_del_proceso,
)
from api.rutas.casos import MENSAJE_CON_CLAVE, MENSAJE_SIN_EMPRESA
from api.rutas.sesion import Detalle
from api.sesion_web import exigir_clave_o_sesion
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import casos as carpetas
from aplicacion import obras
from aplicacion.proyectos import (
    ProyectoInvalido,
    ProyectoRepetido,
    crear_proyecto_en_sesion,
    proyectos_del_caso,
)
from core.catalog import abrir_sesion_de_escritura
from operacion.base_datos import RutaDeCasoRechazada
from seguridad.permisos import Accion, PermisoDenegado, exigir
from seguridad.sesiones import SesionActiva

MENSAJE_CUERPO_INVALIDO = (
    "Indique el nombre de la obra (hasta 120 caracteres), la moneda (Bs o USD), el tipo de obra "
    "y una descripción de hasta 500 caracteres."
)

MENSAJE_CARPETA = "La carpeta no está en la lista: elija una de las que ofrece la barra lateral."
#: Cómo se nombra la carpeta de la empresa en `ProyectoNuevo.carpeta` (ningún nombre real lo es:
#: los de las carpetas terminan en `.db`).
CARPETA_DE_LA_EMPRESA = "empresa"


class _RutaProyectos(RutaSinEco):
    mensaje_por_omision = MENSAJE_CUERPO_INVALIDO


router = APIRouter(prefix="/v1/proyectos", tags=["proyectos"], route_class=_RutaProyectos)
EDITAR_HOJA = Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))


class ProyectoDelCasoRespuesta(BaseModel):
    codigo: str
    nombre: str
    version_vigente: int | None
    version_codigo: str | None
    actualizado: str | None
    cliente: str = ""
    ubicacion: str = ""


@router.get("", response_model=list[ProyectoDelCasoRespuesta], dependencies=LEER)
def listar_proyectos_del_caso(sesion: SesionDep) -> list[ProyectoDelCasoRespuesta]:
    """Los proyectos del caso de esta sesión con su versión vigente."""
    guardadas = obras.fichas(sesion)
    return [
        ProyectoDelCasoRespuesta(
            codigo=str(fila.id),
            nombre=fila.nombre,
            version_vigente=fila.version_id,
            version_codigo=fila.version_codigo,
            actualizado=None if fila.version_fecha is None else fila.version_fecha.isoformat(),
            cliente=guardadas.get(fila.id, obras.SIN_FICHA).cliente,
            ubicacion=guardadas.get(fila.id, obras.SIN_FICHA).ubicacion,
        )
        for fila in proyectos_del_caso(sesion)
    ]


class ProyectoNuevo(BaseModel):
    nombre: str = Field(max_length=120)
    moneda: str | None = None
    dominio: str = ""
    descripcion: str = Field(default="", max_length=500)
    cliente: str = Field(default="", max_length=200)
    ubicacion: str = Field(default="", max_length=200)
    carpeta: str | None = Field(
        default=None,
        max_length=200,
        description="Dónde se crea: un nombre de `GET /v1/obras/todas`, o `empresa`; "
        "sin él, la carpeta de la sesión",
    )


def _ruta_de_destino(carpeta: str) -> Path:
    if carpeta == CARPETA_DE_LA_EMPRESA:
        empresa = ruta_de_url(url_del_proceso())
        if empresa is None:
            raise HTTPException(503, MENSAJE_SIN_EMPRESA)
        return empresa
    try:
        return carpetas.carpeta_de_la_lista(carpeta)
    except (RutaDeCasoRechazada, carpetas.CarpetaFueraDeLaLista):
        raise HTTPException(422, MENSAJE_CARPETA) from None  # sin repetir lo enviado


@contextmanager
def _sesion_de_destino(
    request: Request,
    de_la_sesion: Session,
    carpeta: str | None,
    activa: SesionActiva | None,
) -> Iterator[Session]:
    """La sesión de escritura donde se crea la obra: la de la petición, o la de `carpeta` abierta
    solo mientras dura la petición (`api.caso_web` no se toca)."""
    if carpeta is None:
        yield de_la_sesion
        return
    destino = _ruta_de_destino(carpeta)
    propia = ruta_de_url(url_de_la_peticion(request))
    if propia is not None and propia.resolve() == destino.resolve():
        yield de_la_sesion
        return
    if activa is None:
        raise HTTPException(409, MENSAJE_CON_CLAVE)
    try:
        exigir(activa.roles, Accion.CAMBIAR_CASO)
    except PermisoDenegado as error:
        raise HTTPException(403, str(error)) from None
    with abrir_sesion_de_escritura(obtener_motor(url_de_ruta(destino))) as sesion:
        yield sesion


@router.post(
    "",
    response_model=ProyectoDelCasoRespuesta,
    status_code=201,
    dependencies=[EDITAR_HOJA],
    responses={
        403: {
            "model": Detalle,
            "description": "Sin `EDITAR_HOJA`, o sin `CAMBIAR_CASO` para crear en otra carpeta, "
            "o sin CSRF u origen propio.",
        },
        409: {
            "model": Detalle,
            "description": "Ya hay una obra con ese nombre, o con la clave de API se pidió otra "
            "carpeta.",
        },
        503: {
            "model": Detalle,
            "description": "`carpeta: empresa` y el proceso no usa una carpeta de la empresa.",
        },
    },
)
@sin_eco(MENSAJE_CUERPO_INVALIDO)
def crear_proyecto_del_caso(
    request: Request,
    sesion: SesionDeEscrituraDep,
    peticion: ProyectoNuevo,
    activa: Annotated[SesionActiva | None, EDITAR_HOJA],
) -> ProyectoDelCasoRespuesta:
    """Crea el proyecto en el caso de esta sesión (o en `carpeta`); sin versión guardada todavía."""
    responsable = USUARIO_API if activa is None else activa.usuario
    ficha = obras.FichaObra(peticion.cliente, peticion.ubicacion)
    try:
        with _sesion_de_destino(request, sesion, peticion.carpeta, activa) as donde:
            proyecto = crear_proyecto_en_sesion(
                donde,
                peticion.nombre,
                peticion.moneda,
                peticion.dominio,
                peticion.descripcion,
                responsable,
                # la función se busca al llamar: ficha y proyecto se confirman juntos o ninguno
                lambda abierta, nuevo: obras.guardar_ficha(abierta, nuevo.id, ficha),
            )
            # tras el `commit` el objeto caduca: se lee antes de cerrar la sesión del destino
            codigo, nombre = str(proyecto.id), proyecto.nombre
    except ProyectoRepetido as error:
        raise HTTPException(409, str(error)) from None
    except ProyectoInvalido as error:
        raise HTTPException(422, str(error)) from None
    return ProyectoDelCasoRespuesta(
        codigo=codigo,
        nombre=nombre,
        version_vigente=None,
        version_codigo=None,
        actualizado=None,
        cliente=peticion.cliente,
        ubicacion=peticion.ubicacion,
    )
