"""`/v1/hoja`: la hoja del proyecto en la interfaz nueva, lectura y navegación (T10, rebanada 3b-1).

Es la página `ui/paginas/hoja.py` hecha servicio sobre `aplicacion.hoja` (la COPIA del Plan C: la
clásica y su módulo están en el congelado del experimento y no se tocan), `aplicacion.hoja_vista`
y `aplicacion.hoja_borradores`. Esta rebanada trae las rutas R1 a R4 del diseño
(`docs/especificaciones/2026-10-19-hoja-react-design.md`, §4.3):

- `GET /v1/hoja/versiones?proyecto=` → las versiones del proyecto y la que se preselecciona
  (`por_omision`, calculada aquí). Clave de API o sesión con `EDITAR_HOJA`.
- `POST /v1/hoja/borradores` `{proyecto, version}` → 201: abre la versión como borrador VIVO del
  servidor (el equivalente de `st.session_state["hoja_borrador"]`). Escribe, y solo eso, la
  instantánea de las composiciones si faltaba (UC-15e), a nombre de la persona de la sesión.
  `version: null` es un proyecto sin versiones: borrador en blanco.
- `GET /v1/hoja/borradores/{id}` y `DELETE` (204, idempotente).

Los borradores y todo lo que los toca son **solo de una cuenta** (RF-82: el responsable es la
persona de la sesión, nunca un campo): con `X-Silice-Clave`, 403. Un borrador de otra ficha no
existe (404, no 403) y uno abierto en otro caso da 409 con un mensaje fijo, sin tocar ninguna base.
Montos como `{texto, exacto}`; `Cache-Control: no-store` también en los errores; el 422 no repite
lo enviado (`_RutaHoja` combina `RutaSinCache` y `RutaSinEco` **en ese orden**: al revés, la
primera atrapa el `RequestValidationError` antes y devuelve el 422 con eco).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from sqlalchemy.exc import SQLAlchemyError

from api.admin_acceso import cuenta_con
from api.dependencias import SesionDep, url_de_la_peticion
from api.esquemas_atipicos import AtipicosRespuesta, atipicos_a_respuesta
from api.esquemas_hoja import (
    BorradorAbierto,
    BorradorHojaRespuesta,
    BorradorNuevo,
    InstantaneaHojaRespuesta,
    PreciosHojaRespuesta,
    TrazabilidadHojaRespuesta,
    VersionesHojaRespuesta,
    VistaApuRespuesta,
    VistaEquilibrioRespuesta,
    VistaEspacioRespuesta,
    VistaParametrosRespuesta,
    VistaPlanRespuesta,
    VistaPresupuestoRespuesta,
    base_a_respuesta,
    precios_a_respuesta,
    resumen_a_respuesta,
    trazabilidad_a_respuesta,
    version_a_respuesta,
    vista_apu_a_respuesta,
    vista_equilibrio_a_respuesta,
    vista_espacio_a_respuesta,
    vista_parametros_a_respuesta,
    vista_plan_a_respuesta,
    vista_presupuesto_a_respuesta,
)
from api.esquemas_informe import InformeAuditoriaRespuesta, informe_a_respuesta
from api.sesion_web import exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion import atipicos as busqueda_atipica
from aplicacion import hoja, hoja_borradores, hoja_vista
from aplicacion.entrega import con_anexos_de_cadena
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_borradores import BorradorInexistente, BorradorVivo
from aplicacion.proyectos import resolver_proyecto
from core.budget.moneda import moneda_del_proyecto
from core.catalog import Catalogo
from seguridad.permisos import Accion, permitido
from seguridad.sesiones import SesionActiva

MENSAJE_FORMA = "Los datos de la hoja no tienen la forma esperada: escriba cada celda como texto."
MENSAJE_SOLO_CUENTA = (
    "La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve."
)
MENSAJE_FALTA = (
    "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). "
    "Lo que no guardó se perdió: abra la versión otra vez."
)
MENSAJE_OTRO_CASO = (
    "El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual."
)
MENSAJE_BASE = (
    "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro "
    "programa."
)
MENSAJE_CON_VERSIONES = "Este proyecto ya tiene versiones: elija una de la lista."


class _RutaHoja(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (diseño §1.3-7)."""

    mensaje_por_omision = MENSAJE_FORMA


router = APIRouter(prefix="/v1/hoja", tags=["hoja"], route_class=_RutaHoja)

LEER = Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))
CuentaDeLaHoja = Annotated[
    SesionActiva, Depends(cuenta_con(Accion.EDITAR_HOJA, MENSAJE_SOLO_CUENTA))
]
IdDeBorrador = Annotated[str, Path(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


def _proyecto(sesion, referencia: str):
    encontrado = resolver_proyecto(sesion, referencia)
    if encontrado is None:
        raise HTTPException(
            status_code=404, detail=f"El proyecto «{referencia}» no existe en este caso."
        )
    return encontrado


def _hoy() -> date:
    """El dia de la evaluacion de los precios: hoy (las pruebas lo fijan)."""
    return date.today()


def _version_guardada(sesion, proyecto: str, version: str):
    """El nombre del proyecto y la lista de precios de una version GUARDADA; 404 con los textos de
    la clasica si el proyecto o la version no existen (H:1572)."""
    nombre = _proyecto(sesion, proyecto).nombre
    try:
        return nombre, hoja.lista_de_version(sesion, nombre, version)
    except HojaInvalida as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


def _vivo(request: Request, activa: SesionActiva, id_: str) -> BorradorVivo:
    """El borrador de MI ficha (404 si no existe) y abierto en el caso de ahora (409)."""
    try:
        vivo = hoja_borradores.obtener(activa.huella_ficha, id_)
    except BorradorInexistente:
        raise HTTPException(status_code=404, detail=MENSAJE_FALTA) from None
    if vivo.caso != url_de_la_peticion(request):
        raise HTTPException(status_code=409, detail=MENSAJE_OTRO_CASO)
    return vivo


def _respuesta(sesion, vivo: BorradorVivo) -> dict:
    vigente = hoja.codigo_vigente(sesion, vivo.proyecto)
    mas_nueva = vigente if vivo.version is not None and vigente != vivo.version else None
    return {
        "id": vivo.id,
        "base": base_a_respuesta(hoja_vista.base(vivo, vigente)),
        "resumen": resumen_a_respuesta(hoja_vista.resumen(vivo, mas_nueva)),
    }


@router.get("/versiones", response_model=VersionesHojaRespuesta, dependencies=[LEER])
def listar_versiones(
    sesion: SesionDep, proyecto: Annotated[str, Query(min_length=1, max_length=500)]
) -> VersionesHojaRespuesta:
    """R1: las versiones del proyecto (código de `/v1/proyectos` o nombre) y la preseleccionada."""
    try:
        encontrado = _proyecto(sesion, proyecto)
        filas = hoja.historial_de_versiones(sesion, encontrado.nombre)
        moneda = moneda_del_proyecto(sesion, encontrado)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return VersionesHojaRespuesta(
        proyecto=encontrado.nombre,
        moneda=moneda,
        por_omision=hoja_vista.version_por_omision(filas),
        versiones=[version_a_respuesta(f) for f in filas],
    )


@router.post("/borradores", response_model=BorradorAbierto, status_code=201)
def abrir_borrador(
    datos: BorradorNuevo, request: Request, activa: CuentaDeLaHoja, sesion: SesionDep
) -> BorradorAbierto:
    """R2: abre la versión como borrador vivo. Escribe la instantánea si faltaba (UC-15e).

    En la firma `activa` va antes que `sesion`: FastAPI resuelve en ese orden y el acceso (401,
    403) debe responder antes de abrir la base del caso."""
    try:
        con_anexos_de_cadena(sesion)  # el sello de lo que se escriba cubre los anexos (§1.2)
        nombre = _proyecto(sesion, datos.proyecto).nombre
        filas = hoja.historial_de_versiones(sesion, nombre)
        creadas = 0
        if datos.version is None:
            if filas:
                raise HTTPException(status_code=409, detail=MENSAJE_CON_VERSIONES)
            borrador, abierta = hoja.Borrador(fecha=date.today()), None
        else:
            try:
                hoja.lista_de_version(sesion, nombre, datos.version)  # el 404 de la clásica
            except HojaInvalida as error:
                raise HTTPException(status_code=404, detail=str(error)) from None
            try:
                abierta = hoja.abrir_version(
                    sesion,
                    Catalogo(sesion),
                    nombre,
                    datos.version,
                    fecha_evaluacion=date.today(),
                    responsable=activa.usuario,
                )
            except HojaInvalida as error:
                raise HTTPException(status_code=409, detail=str(error)) from None
            borrador, creadas = abierta.borrador, len(abierta.instantanea.creadas)
        vivo = hoja_borradores.crear(
            activa.huella_ficha,
            url_de_la_peticion(request),
            nombre,
            datos.version,
            borrador,
            abierta,
        )
        cuerpo = _respuesta(sesion, vivo)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return BorradorAbierto(
        **cuerpo,
        instantanea=InstantaneaHojaRespuesta(
            creadas=creadas, mensaje=hoja_vista.mensaje_instantanea(creadas)
        ),
    )


@router.get("/borradores/{id}", response_model=BorradorHojaRespuesta)
def leer_borrador(
    id: IdDeBorrador, request: Request, activa: CuentaDeLaHoja, sesion: SesionDep
) -> BorradorHojaRespuesta:
    """R3: el estado del borrador vivo (su base y su resumen)."""
    vivo = _vivo(request, activa, id)
    try:
        return BorradorHojaRespuesta(**_respuesta(sesion, vivo))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None


@router.delete("/borradores/{id}", status_code=204, response_class=Response)
def descartar_borrador(id: IdDeBorrador, request: Request, activa: CuentaDeLaHoja) -> Response:
    """R4: descarta el borrador. Idempotente: un id desconocido, vencido o ajeno también es 204."""
    try:
        _vivo(request, activa, id)
    except HTTPException as error:
        if error.status_code == 404:
            return Response(status_code=204)
        raise
    hoja_borradores.descartar(activa.huella_ficha, id)
    return Response(status_code=204)


@router.get("/borradores/{id}/vistas/espacio", response_model=VistaEspacioRespuesta)
def vista_espacio(
    id: IdDeBorrador, request: Request, activa: CuentaDeLaHoja
) -> VistaEspacioRespuesta:
    """R5: Espacio y metrajes en lectura (tablas, Estado por fila, cantidades derivadas)."""
    return vista_espacio_a_respuesta(hoja_vista.vista_espacio(_vivo(request, activa, id)))


@router.get("/borradores/{id}/vistas/presupuesto", response_model=VistaPresupuestoRespuesta)
def vista_presupuesto(
    id: IdDeBorrador, request: Request, activa: CuentaDeLaHoja
) -> VistaPresupuestoRespuesta:
    """R6: Presupuesto en lectura (renglones, cantidad calculada y escrita, PU, total, Estado)."""
    return vista_presupuesto_a_respuesta(hoja_vista.vista_presupuesto(_vivo(request, activa, id)))


@router.get("/borradores/{id}/vistas/apu", response_model=VistaApuRespuesta)
def vista_apu(
    id: IdDeBorrador,
    request: Request,
    activa: CuentaDeLaHoja,
    partida: Annotated[str | None, Query(max_length=500)] = None,
    buscar: Annotated[str | None, Query(max_length=500)] = None,
) -> VistaApuRespuesta:
    """R7: APU en lectura (lista con buscador, tres rubros, cierre). La búsqueda la hace el
    servidor; sin coincidencias se devuelven todas las partidas."""
    return vista_apu_a_respuesta(hoja_vista.vista_apu(_vivo(request, activa, id), partida, buscar))


@router.get("/borradores/{id}/vistas/plan", response_model=VistaPlanRespuesta)
def vista_plan(id: IdDeBorrador, request: Request, activa: CuentaDeLaHoja) -> VistaPlanRespuesta:
    """R8: Plan y curva en lectura (matriz partida por periodo y curva de inversión)."""
    return vista_plan_a_respuesta(hoja_vista.vista_plan(_vivo(request, activa, id)))


@router.get("/borradores/{id}/vistas/equilibrio", response_model=VistaEquilibrioRespuesta)
def vista_equilibrio(
    id: IdDeBorrador, request: Request, activa: CuentaDeLaHoja
) -> VistaEquilibrioRespuesta:
    """R9: Punto de equilibrio en lectura (ventas, costos, utilidad, punto y la frase del caso)."""
    return vista_equilibrio_a_respuesta(hoja_vista.vista_equilibrio(_vivo(request, activa, id)))


@router.get("/borradores/{id}/vistas/parametros", response_model=VistaParametrosRespuesta)
def vista_parametros(
    id: IdDeBorrador, request: Request, activa: CuentaDeLaHoja, sesion: SesionDep
) -> VistaParametrosRespuesta:
    """R10: Parámetros en lectura (los cuatro factores, el total y la moneda del proyecto)."""
    vivo = _vivo(request, activa, id)
    try:
        moneda = moneda_del_proyecto(sesion, _proyecto(sesion, vivo.proyecto))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return vista_parametros_a_respuesta(
        hoja_vista.vista_parametros(
            vivo, moneda, permitido(activa.roles, Accion.CONVERTIR_Y_REAJUSTAR)
        )
    )


@router.get("/borradores/{id}/vistas/auditoria", response_model=InformeAuditoriaRespuesta)
def vista_auditoria(
    id: IdDeBorrador, request: Request, activa: CuentaDeLaHoja
) -> InformeAuditoriaRespuesta:
    """R11: el informe de auditoría del borrador, con todas las reglas y R17 (conexión de cada
    punto) ligada a su espacio; texto plano, sin Markdown."""
    return informe_a_respuesta(hoja_vista.informe_de_auditoria(_vivo(request, activa, id)))


@router.get("/trazabilidad", response_model=TrazabilidadHojaRespuesta, dependencies=[LEER])
def trazabilidad(
    sesion: SesionDep,
    proyecto: Annotated[str, Query(min_length=1, max_length=500)],
    version: Annotated[str, Query(min_length=1, max_length=500)],
) -> TrazabilidadHojaRespuesta:
    """R14: el historial del proyecto y los registros de cambio de una versión guardada. Clave de
    API o sesión con `EDITAR_HOJA`; solo lee."""
    try:
        nombre, _ = _version_guardada(sesion, proyecto, version)
        return trazabilidad_a_respuesta(
            hoja_vista.vista_trazabilidad(
                hoja.historial_de_versiones(sesion, nombre),
                hoja.registros_de_version(sesion, nombre, version),
            )
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None


@router.get("/precios", response_model=PreciosHojaRespuesta, dependencies=[LEER])
def precios(
    sesion: SesionDep,
    proyecto: Annotated[str, Query(min_length=1, max_length=500)],
    version: Annotated[str, Query(min_length=1, max_length=500)],
) -> PreciosHojaRespuesta:
    """R12: el origen de cada precio de una versión guardada, evaluado a hoy (erosión y avisos de
    R11 y R12 en memoria). Clave de API o sesión con `EDITAR_HOJA`; solo lee."""
    try:
        nombre, lista = _version_guardada(sesion, proyecto, version)
        hoy = _hoy()
        filas = hoja.precios_de_version(sesion, nombre, version, fecha_evaluacion=hoy)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return precios_a_respuesta(hoja_vista.vista_precios(filas, lista.moneda, hoy))


@router.get("/precios/atipicos", response_model=AtipicosRespuesta, dependencies=[LEER])
def precios_atipicos(
    sesion: SesionDep,
    proyecto: Annotated[str, Query(min_length=1, max_length=500)],
    version: Annotated[str, Query(min_length=1, max_length=500)],
) -> AtipicosRespuesta:
    """R13: «Buscar variaciones atípicas de precio» (RF-100) sobre los insumos de una versión
    guardada, como el botón de la pestaña Precios. Solo lee: nada se guarda ni se bloquea. Sin el
    extra `ml` responde `disponible: false` y lo dice. Clave de API o sesión con `EDITAR_HOJA`."""
    try:
        nombre, _ = _version_guardada(sesion, proyecto, version)
        precios_de_la_version = hoja.precios_de_version(sesion, nombre, version)
        busqueda = busqueda_atipica.atipicos_de_insumos(
            sesion, [p.codigo for p in precios_de_la_version]
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return atipicos_a_respuesta(busqueda)
