"""`/v1/sesion`: entrar, consultar y salir desde el navegador (RT-9, RF-113; plan sesión 2, 2.3a).

Estas rutas **no** llevan la clave de API (`CON_CLAVE`): son la puerta de la interfaz nueva, que
no tiene secretos. Las protege lo mismo que a la interfaz clásica: `seguridad.cuentas.autenticar`
con su freno global, el bloqueo de 15 minutos tras cinco fallos y el mismo mensaje exista o no
el usuario; la IP del cliente queda en el registro de accesos.

- `POST` `{login, contrasena}` → 200 `{login, nombre, roles, csrf, debe_cambiar_clave, acciones,
  modo_entrega}` y la cookie de sesión; 401 credenciales malas, 423 bloqueada, 403
  si un `Origin` presente no es el de la instalación (CSRF de acceso), 429 con `Retry-After` si el
  freno global pide esperar (RS2-11: la API no duerme en su hilo; el intento frenado no llega a
  verificar la contraseña) y 422 con un mensaje fijo, sin repetir lo enviado, si el cuerpo no es
  válido. Si el navegador trae la cookie de una ficha anterior, se cierra (y se olvida su caso).
- `GET` → 200 con el mismo cuerpo, o 401 (y borra la cookie que ya no sirve).
- `DELETE` (exige CSRF y `Origin`) → 204, cierra la ficha, olvida su caso y borra la cookie.
- `POST /contrasena` `{actual, nueva}` (exige la ficha, CSRF y `Origin`) → 200 con el cuerpo de
  una ficha nueva y su cookie: `seguridad.cuentas.cambiar_contrasena` aplica la política de
  siempre, cierra **todas** las fichas de la cuenta y abre otra (como `ui/acceso.py`); el caso
  elegido pasa a la ficha nueva. 403 si la actual no es la correcta, 422 con el motivo de la
  política o, si el cuerpo no es válido, con un mensaje fijo que no repite lo enviado.

Ola 0a (sesión 2b): la cuenta con la contraseña temporal ya no recibe un 403 al entrar («cámbiela
en la interfaz clásica»): entra con `debe_cambiar_clave: true`, `acciones: []` y una ficha que
`api.sesion_web.exigir_sesion` rechaza en toda otra ruta (la «cookie restringida»). `acciones` son
las `Accion` que su rol permite (`seguridad.permisos.permitido`), en el orden de la matriz, para que
el menú no repita la matriz; `modo_entrega` es `SILICE_MODO_ENTREGA` (de `aplicacion.entorno`).

MOD-0 (plan de módulos; absorbe la Tarea 5 del plan de montar un presupuesto): lo que la cuenta
recuerda entre sesiones y reinicios vive en `mp_eleccion` de la instalación (`aplicacion.eleccion`).

- El cuerpo de `POST`/`GET /v1/sesion` (y de `POST /contrasena` y del reclamo del primer arranque,
  que usan `_cuerpo`) gana `eleccion: {caso, proyecto, aviso}` y `preferencias: {modulo,
  sidebar_fijado}`. Si la ficha no eligió carpeta y la recordada sigue en la carpeta de casos, se
  fija para la ficha (`caso_web.fijar`): así vuelve tras salir y entrar, y tras reiniciar la API.
  Solo si la cuenta tiene `CAMBIAR_CASO` (§12.2): sin él, `caso: null` y la fila no se toca
  (vuelve si recupera el permiso); la obra solo se devuelve si se recordó para la carpeta por
  omisión (`caso` nulo en la fila), porque un código de obra es de su carpeta, y `PUT /proyecto`
  sin el permiso la recuerda así. La memoria de la ficha
  cambia solo después de confirmar la instalación.
  Una carpeta recordada que ya no existe da `caso: null` y el aviso `MENSAJE_CARPETA_PERDIDA`
  **una vez**: se olvida en la tabla (y en la ficha, para que nadie la recree vacía). Una obra que
  ya no está en la carpeta de la ficha da `proyecto: null` y también se olvida. Sin nada recordado,
  `eleccion` viene con los tres campos nulos. Con la contraseña temporal, `eleccion: null` y las
  preferencias por omisión.
- `PUT /proyecto` `{proyecto}` y `PUT /preferencias` `{modulo?, sidebar_fijado?}` (sesión completa,
  CSRF y `Origin`; la clave de API no tiene cuenta a la que recordar: 401) → 204. Lo que no viene
  (o viene `null`) en las preferencias no cambia. 422 sin repetir lo enviado: `MENSAJE_MODULO` si
  el módulo no existe; un mensaje fijo si el cuerpo no tiene la forma.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StrictBool, StrictStr

from api import caso_web
from api.dependencias import (
    SesionInstalacionDep,
    obtener_motor,
    url_de_ruta,
    url_del_proceso,
)
from api.sesion_web import (
    COOKIE,
    MENSAJE_ORIGEN,
    MENSAJE_SIN_SESION,
    ahora,
    borrar_cookie,
    csrf_de,
    exigir_csrf_y_origen,
    exigir_sesion,
    origen_propio,
    poner_cookie,
    sesion_vigente,
)
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion.eleccion import (
    MENSAJE_MODULO,
    MODULOS,
    eleccion_de,
    recordar_caso,
    recordar_preferencias,
    recordar_proyecto,
)
from aplicacion.entorno import modo_entrega_activo
from aplicacion.proyectos import resolver_proyecto
from core.catalog import abrir_sesion
from operacion.base_datos import ErrorDeBase, RutaDeCasoRechazada, listar_casos, resolver_caso
from operacion.instalacion import sesion_de_instalacion
from seguridad import cuentas, eventos, sesiones
from seguridad.permisos import Accion, Rol, permitido
from seguridad.sesiones import SesionActiva

MENSAJE_CUERPO_INVALIDO = (
    "Escriba el usuario y la contraseña como texto (la contraseña admite hasta "
    f"{cuentas.MAXIMO_CONTRASENA} caracteres)."
)
MENSAJE_CONTRASENAS_INVALIDAS = (
    "Escriba la contraseña actual y la nueva como texto (cada una admite hasta "
    f"{cuentas.MAXIMO_CONTRASENA} caracteres)."
)
MENSAJE_FRENO = (
    "Demasiados intentos fallidos en este equipo. Espere unos segundos y vuelva a probar."
)
MENSAJE_CARPETA_PERDIDA = "La carpeta de trabajo «{nombre}» ya no existe; se abrió la de siempre."
MENSAJE_OBRA_INVALIDA = "Indique la obra por su código, como texto de hasta 120 caracteres, o null."
MENSAJE_PREFERENCIAS_INVALIDAS = (
    "Indique el módulo (auditoria, obras o produccion) y si el sidebar queda fijado (true o false)."
)


class _RutaSesion(RutaSinEco):
    mensaje_por_omision = MENSAJE_CUERPO_INVALIDO


router = APIRouter(prefix="/v1/sesion", tags=["sesion"], route_class=_RutaSesion)


class _Frenado(Exception):  # noqa: N818
    """El freno global pidió esperar: la ruta responde 429 en vez de dormir en su hilo."""

    def __init__(self, segundos: float) -> None:
        super().__init__(segundos)
        self.segundos = segundos


def _no_dormir(segundos: float) -> None:
    """El `dormir` que la API pasa a `cuentas.autenticar` (RS2-11): no duerme, avisa."""
    raise _Frenado(segundos)


class Credenciales(BaseModel):
    login: str = Field(max_length=120)
    contrasena: str = Field(max_length=cuentas.MAXIMO_CONTRASENA)


class CambioDeContrasena(BaseModel):
    actual: str = Field(max_length=cuentas.MAXIMO_CONTRASENA)
    nueva: str = Field(max_length=cuentas.MAXIMO_CONTRASENA)


Modulo = Literal["auditoria", "obras", "produccion"]


class EleccionRespuesta(BaseModel):
    caso: str | None = Field(description="La carpeta recordada; `null` = la de la instalación")
    proyecto: str | None = Field(description="El código de la obra recordada en esa carpeta")
    aviso: str | None = Field(description="Qué se perdió de lo recordado (se dice una vez)")


class PreferenciasRespuesta(BaseModel):
    modulo: Modulo | None = Field(description="El último módulo abierto")
    sidebar_fijado: bool


SIN_PREFERENCIAS = PreferenciasRespuesta(modulo=None, sidebar_fijado=False)


class SesionRespuesta(BaseModel):
    login: str
    nombre: str
    roles: list[str]
    csrf: str
    debe_cambiar_clave: bool = Field(
        description="La contraseña es temporal: hasta cambiarla, la ficha solo sirve para "
        "`POST /v1/sesion/contrasena` y para salir"
    )
    acciones: list[str] = Field(
        description="Las acciones que permite su rol (vacía con la contraseña temporal)"
    )
    modo_entrega: bool = Field(description="`SILICE_MODO_ENTREGA` está encendido")
    eleccion: EleccionRespuesta | None = Field(
        description="La carpeta y la obra recordadas (`null` con la contraseña temporal)"
    )
    preferencias: PreferenciasRespuesta


class ObraElegida(BaseModel):
    proyecto: StrictStr | None = Field(max_length=120, description="El `codigo` de la obra")


class Preferencias(BaseModel):
    modulo: StrictStr | None = Field(default=None, description="auditoria, obras o produccion")
    sidebar_fijado: StrictBool | None = None


class Detalle(BaseModel):
    detalle: str


def _carpeta_en_la_lista(caso: str) -> Path | None:
    """La ruta de la carpeta recordada si sigue en la carpeta de casos; `None` si no."""
    try:
        ruta = resolver_caso(caso)
    except RutaDeCasoRechazada:
        return None
    return ruta if ruta in {c.resolve() for c in listar_casos()} else None


def _obra_sigue(carpeta: Path | None, proyecto: str) -> bool:
    """La obra está en `carpeta` (`None` = la del proceso), con la que trabajará la ficha. Si esa
    carpeta no se puede abrir no se sabe: se conserva lo recordado."""
    url = url_del_proceso() if carpeta is None else url_de_ruta(carpeta)
    try:
        motor = obtener_motor(url)
    except HTTPException:
        return True
    with abrir_sesion(motor) as sesion:
        return resolver_proyecto(sesion, proyecto) is not None


def _restaurar(activa: SesionActiva) -> tuple[EleccionRespuesta | None, PreferenciasRespuesta]:
    """Lo que recuerda la cuenta, ya aplicado a la ficha (ver la cabecera del módulo)."""
    if activa.debe_cambiar_clave:
        return None, SIN_PREFERENCIAS
    huella = activa.huella_ficha
    puede_elegir = permitido(activa.roles, Accion.CAMBIAR_CASO)
    elegida = caso_web.elegido(huella)
    efectiva = elegida  # la carpeta con que trabajará la ficha (`None` = la del proceso)
    fijar = olvidar = False
    try:
        with sesion_de_instalacion() as sesion:
            recordada = eleccion_de(sesion, activa.usuario_id)
            if recordada is None:
                return EleccionRespuesta(caso=None, proyecto=None, aviso=None), SIN_PREFERENCIAS
            caso, proyecto, aviso = recordada.caso, recordada.proyecto, None
            if not puede_elegir:
                # §12.2: sin `cambiar_caso` no se vuelve a una carpeta que ya no podría elegir. La
                # fila no se toca (vuelve si recupera el permiso). Un código de obra es de su
                # carpeta: la de otra no se mira en la de la ficha (el «7» de s1 no es el de aquí)
                if caso is not None:
                    proyecto = None
                caso = None
            elif caso is not None:
                ruta = _carpeta_en_la_lista(caso)
                if ruta is None:
                    aviso = MENSAJE_CARPETA_PERDIDA.format(nombre=Path(caso).stem)
                    # que nadie abra (y recree vacía) la que ya no está
                    olvidar = elegida is not None and elegida.name == caso
                    efectiva = None if olvidar else elegida
                    recordar_caso(sesion, activa.usuario_id, None, ahora())
                    caso = proyecto = None
                elif elegida is None:
                    fijar, efectiva = True, ruta
            if proyecto is not None and not _obra_sigue(efectiva, proyecto):
                if puede_elegir:
                    recordar_proyecto(sesion, activa.usuario_id, None, ahora())
                proyecto = None
            sesion.commit()
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    # la memoria de la ficha cambia solo después de confirmar la instalación (C2)
    if olvidar:
        caso_web.olvidar(huella)
    elif fijar and efectiva is not None:
        caso_web.fijar(huella, efectiva)
    modulo = recordada.modulo if recordada.modulo in MODULOS else None
    return (
        EleccionRespuesta(caso=caso, proyecto=proyecto, aviso=aviso),
        PreferenciasRespuesta(modulo=modulo, sidebar_fijado=recordada.sidebar_fijado),
    )


def _cuerpo(ficha: str, activa: SesionActiva) -> SesionRespuesta:
    eleccion, preferencias = _restaurar(activa)
    acciones = (
        []
        if activa.debe_cambiar_clave
        else [accion.value for accion in Accion if permitido(activa.roles, accion)]
    )
    return SesionRespuesta(
        login=activa.login,
        nombre=activa.nombre,
        roles=[rol.value for rol in Rol if rol in activa.roles],
        csrf=csrf_de(ficha),
        debe_cambiar_clave=activa.debe_cambiar_clave,
        acciones=acciones,
        modo_entrega=modo_entrega_activo(),
        eleccion=eleccion,
        preferencias=preferencias,
    )


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.post(
    "",
    response_model=SesionRespuesta,
    responses={
        401: {"model": Detalle, "description": "Usuario o contraseña incorrectos."},
        403: {"model": Detalle, "description": "Un `Origin` presente y ajeno."},
        422: {"model": Detalle, "description": "Cuerpo inválido (no repite lo enviado)."},
        423: {"model": Detalle, "description": "Cuenta bloqueada por intentos fallidos."},
        429: {"model": Detalle, "description": "Freno global: reintentar tras `Retry-After`."},
    },
)
def entrar(
    datos: Credenciales, request: Request, response: Response
) -> SesionRespuesta | JSONResponse:
    """Entra con la cuenta de la instalación y deja la cookie de sesión. Con la contraseña
    temporal la ficha queda restringida hasta `POST /v1/sesion/contrasena`."""
    if "origin" in request.headers and not origen_propio(request):
        raise HTTPException(status_code=403, detail=MENSAJE_ORIGEN)
    momento = ahora()
    try:
        with sesion_de_instalacion() as sesion:
            try:
                usuario = cuentas.autenticar(
                    sesion,
                    datos.login,
                    datos.contrasena,
                    momento,
                    ip=_ip(request),
                    dormir=_no_dormir,
                )
            except _Frenado as frenado:
                eventos.registrar(
                    sesion,
                    "bloqueo",
                    momento,
                    ip=_ip(request),
                    detalle="freno global",
                    login=cuentas.clave_de_intento(datos.login),
                )
                sesion.commit()
                return JSONResponse(
                    status_code=429,
                    content={"detalle": MENSAJE_FRENO},
                    headers={"Retry-After": str(max(1, math.ceil(frenado.segundos)))},
                )
            except cuentas.CuentaBloqueada:
                raise HTTPException(status_code=423, detail=cuentas.MENSAJE_BLOQUEO) from None
            except cuentas.ErrorDeAcceso:
                raise HTTPException(status_code=401, detail=cuentas.MENSAJE_FALLO) from None
            anterior = request.cookies.get(COOKIE)
            if anterior:  # volver a entrar desde el mismo navegador cierra la ficha anterior
                sesiones.cerrar(sesion, anterior, "salida", momento)
                caso_web.olvidar(sesiones.huella_de(anterior))  # puede ser otra persona
            ficha = sesiones.abrir(sesion, usuario, momento)
            activa = sesiones.validar(sesion, ficha, momento)
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if activa is None:  # la cuenta cambió entre las dos lecturas: no hay sesión que dar
        raise HTTPException(status_code=401, detail=MENSAJE_SIN_SESION)
    poner_cookie(response, ficha)
    return _cuerpo(ficha, activa)


@router.get(
    "",
    response_model=SesionRespuesta,
    responses={401: {"model": Detalle, "description": "Sin sesión vigente."}},
)
def consultar(request: Request) -> SesionRespuesta | JSONResponse:
    """La sesión vigente del navegador, con su token anti-CSRF (también la restringida, que
    informa `debe_cambiar_clave: true`)."""
    vigente = sesion_vigente(request)
    if vigente is None:
        respuesta = JSONResponse(status_code=401, content={"detalle": MENSAJE_SIN_SESION})
        if COOKIE in request.cookies:
            borrar_cookie(respuesta)
        return respuesta
    ficha, activa = vigente
    return _cuerpo(ficha, activa)


@router.delete(
    "",
    status_code=204,
    response_class=Response,
    responses={
        401: {"model": Detalle, "description": "Sin sesión vigente."},
        403: {"model": Detalle, "description": "Falta el CSRF o el origen no es propio."},
    },
)
def salir(request: Request) -> Response:
    """Cierra la sesión del navegador (exige CSRF y `Origin`) y borra la cookie."""
    vigente = sesion_vigente(request)
    if vigente is None:
        raise HTTPException(status_code=401, detail=MENSAJE_SIN_SESION)
    ficha, _ = vigente
    exigir_csrf_y_origen(request, ficha)
    try:
        with sesion_de_instalacion() as sesion:
            sesiones.cerrar(sesion, ficha, "salida", ahora())
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    caso_web.olvidar(sesiones.huella_de(ficha))
    respuesta = Response(status_code=204)
    borrar_cookie(respuesta)
    return respuesta


def _ficha_aunque_temporal(request: Request) -> tuple[str, SesionActiva]:
    """La ficha vigente (también la de una contraseña temporal), con CSRF y `Origin`: 401/403.
    Es la dependencia de `POST /contrasena`, que corre antes de validar el cuerpo."""
    vigente = sesion_vigente(request)
    if vigente is None:
        raise HTTPException(status_code=401, detail=MENSAJE_SIN_SESION)
    exigir_csrf_y_origen(request, vigente[0])
    return vigente


@router.post(
    "/contrasena",
    response_model=SesionRespuesta,
    responses={
        401: {"model": Detalle, "description": "Sin sesión vigente."},
        403: {"model": Detalle, "description": "Contraseña actual errada, o sin CSRF u origen."},
        422: {"model": Detalle, "description": "La política la rechaza, o cuerpo inválido."},
    },
)
@sin_eco(MENSAJE_CONTRASENAS_INVALIDAS)
def cambiar_contrasena(
    datos: CambioDeContrasena,
    vigente: Annotated[tuple[str, SesionActiva], Depends(_ficha_aunque_temporal)],
    response: Response,
) -> SesionRespuesta:
    """Cambia la contraseña propia: cierra todas las fichas de la cuenta y deja la cookie de una
    nueva, ya sin restricción (el cambio obligatorio de la temporal, o uno voluntario)."""
    ficha, activa = vigente
    momento = ahora()
    try:
        with sesion_de_instalacion() as sesion:
            try:
                nueva = cuentas.cambiar_contrasena(
                    sesion, activa.usuario_id, datos.actual, datos.nueva, momento
                )
            except cuentas.ContrasenaInvalida as error:
                raise HTTPException(status_code=422, detail=str(error)) from None
            except cuentas.ErrorDeAcceso as error:  # mensaje fijo de `seguridad.cuentas`
                raise HTTPException(status_code=403, detail=str(error)) from None
            nueva_activa = sesiones.validar(sesion, nueva, momento)
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    caso_web.heredar(sesiones.huella_de(ficha), sesiones.huella_de(nueva))
    if nueva_activa is None:  # la cuenta cambió entre las dos lecturas: no hay sesión que dar
        raise HTTPException(status_code=401, detail=MENSAJE_SIN_SESION)
    poner_cookie(response, nueva)
    return _cuerpo(nueva, nueva_activa)


# --- MOD-0: lo que la cuenta recuerda ------------------------------------------------------------


def _sesion_completa(request: Request) -> SesionActiva:
    """Sesión completa (401 sin ella, 403 con la contraseña temporal), con CSRF y `Origin` (403).
    La clave de API no cuenta: no tiene cuenta a la que recordar."""
    ficha, activa = exigir_sesion(request)
    exigir_csrf_y_origen(request, ficha)
    return activa


_RESPUESTAS_DE_LO_RECORDADO: dict[int | str, dict] = {
    401: {"model": Detalle, "description": "Sin sesión vigente (la clave de API no sirve)."},
    403: {"model": Detalle, "description": "Contraseña temporal, o sin CSRF u origen propio."},
    422: {"model": Detalle, "description": "Cuerpo inválido (no repite lo enviado)."},
}


@router.put(
    "/proyecto",
    status_code=204,
    response_class=Response,
    responses=_RESPUESTAS_DE_LO_RECORDADO,
)
@sin_eco(MENSAJE_OBRA_INVALIDA)
def recordar_obra(
    datos: ObraElegida,
    activa: Annotated[SesionActiva, Depends(_sesion_completa)],
    sesion: SesionInstalacionDep,
) -> Response:
    """Recuerda la obra elegida (`null` = ninguna) para la carpeta recordada de la cuenta. Sin
    `CAMBIAR_CASO` la ficha trabaja en la carpeta por omisión: la obra se recuerda con ella
    (`caso` nulo), para que no vuelva pegada a otra carpeta si recupera el permiso."""
    if not permitido(activa.roles, Accion.CAMBIAR_CASO):
        recordar_caso(sesion, activa.usuario_id, None, ahora())
    recordar_proyecto(sesion, activa.usuario_id, datos.proyecto, ahora())
    return Response(status_code=204)


@router.put(
    "/preferencias",
    status_code=204,
    response_class=Response,
    responses=_RESPUESTAS_DE_LO_RECORDADO,
)
@sin_eco(MENSAJE_PREFERENCIAS_INVALIDAS)
def guardar_preferencias(
    datos: Preferencias,
    activa: Annotated[SesionActiva, Depends(_sesion_completa)],
    sesion: SesionInstalacionDep,
) -> Response:
    """Recuerda el último módulo y si el sidebar queda fijado; lo que no viene no cambia."""
    try:
        recordar_preferencias(
            sesion,
            activa.usuario_id,
            modulo=datos.modulo,
            sidebar_fijado=datos.sidebar_fijado,
            ahora=ahora(),
        )
    except ValueError:
        raise HTTPException(status_code=422, detail=MENSAJE_MODULO) from None
    return Response(status_code=204)
