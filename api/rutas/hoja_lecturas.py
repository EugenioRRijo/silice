"""`/v1/hoja`: las lecturas de la hoja (borrador vivo y version guardada), sin escribir nada.

- `GET /antes-y-despues` (Tarea 26): el APU de cada partida cambiada contra la linea base.
- E8 `GET /borradores/{id}/insumos` y E9 `GET /borradores/{id}/cambios`.
- R5 a R11: las vistas del borrador vivo (`/borradores/{id}/vistas/...`).
- R14 `GET /trazabilidad`, R12 `GET /precios` y R13 `GET /precios/atipicos` de una version
  guardada (clave de API o sesion con `LEER_PROYECTO`).

Salieron de `api/rutas/hoja.py` sin cambios (tarea 4.2 del plan de desenredo), con su misma
clase de ruta (`_RutaHoja`) y sus mismos ayudantes, que se leen de alli como en los otros
modulos hermanos (`hoja_exportar`, `hoja_libro`): el «hoy» de R12 es `rutas_hoja._hoy()`, el
de toda la Hoja. `api/main.py` registra este router justo despues del de la hoja, asi el orden
de las rutas no cambia.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy.exc import SQLAlchemyError

from api.dependencias import SesionDep
from api.esquemas_atipicos import AtipicosRespuesta, atipicos_a_respuesta
from api.esquemas_hoja import (
    AntesYDespuesRespuesta,
    CambiosHojaRespuesta,
    InsumosHojaRespuesta,
    PreciosHojaRespuesta,
    TrazabilidadHojaRespuesta,
    VistaApuRespuesta,
    VistaEquilibrioRespuesta,
    VistaEspacioRespuesta,
    VistaParametrosRespuesta,
    VistaPlanRespuesta,
    VistaPresupuestoRespuesta,
    antes_y_despues_a_respuesta,
    cambios_a_respuesta,
    insumos_a_respuesta,
    precios_a_respuesta,
    trazabilidad_a_respuesta,
    vista_apu_a_respuesta,
    vista_equilibrio_a_respuesta,
    vista_espacio_a_respuesta,
    vista_parametros_a_respuesta,
    vista_plan_a_respuesta,
    vista_presupuesto_a_respuesta,
)
from api.esquemas_informe import InformeAuditoriaRespuesta, informe_a_respuesta
from api.rutas import hoja as rutas_hoja
from api.rutas.hoja import (
    FORMA_ANTES,
    FORMA_BUSQUEDA,
    MENSAJE_BASE,
    MENSAJE_SIN_VERSION,
    SIN_LINEA_BASE,
    VER,
    CuentaQueVe,
    IdDeBorrador,
    _proyecto,
    _RutaHoja,
    _version_guardada,
    _vista_apu,
    _vivo,
)
from api.sin_eco import sin_eco
from aplicacion import atipicos as busqueda_atipica
from aplicacion import (
    hoja,
    hoja_edicion,
    hoja_lineas_apu,
    hoja_vista,
)
from aplicacion.errores import HojaInvalida
from core.budget.moneda import moneda_del_proyecto
from core.catalog import Catalogo, CatalogoIncompleto
from seguridad.permisos import Accion, permitido

router = APIRouter(prefix="/v1/hoja", tags=["hoja"], route_class=_RutaHoja)


@router.get("/antes-y-despues", response_model=AntesYDespuesRespuesta, dependencies=[VER])
@sin_eco(FORMA_ANTES)
def antes_y_despues(
    sesion: SesionDep,
    proyecto: Annotated[str, Query(min_length=1, max_length=500)],
    version: Annotated[str | None, Query(max_length=500)] = None,
) -> AntesYDespuesRespuesta:
    """Tarea 26 (lo muestra Control de obra): por partida de la versión (la vigente si no se dice)
    cuyo APU cambió respecto de la línea base, el costo directo unitario, la duración y el término
    por rendimientos y el punto de equilibrio, antes y después. Solo lee. Sin línea base, o sin
    partidas cambiadas, la lista va vacía con el aviso; la obra o la versión que no existen, 404."""
    encontrado = _proyecto(sesion, proyecto)
    nombre = encontrado.nombre
    try:
        codigo = version if version is not None else hoja.codigo_vigente(sesion, nombre)
        moneda = moneda_del_proyecto(sesion, encontrado)
        if codigo is not None:
            _version_guardada(sesion, nombre, codigo)  # 404 si no existe
        base = hoja_lineas_apu.linea_base_de(sesion, nombre)
        if base is None or codigo is None:
            return antes_y_despues_a_respuesta(base, codigo, moneda, [], SIN_LINEA_BASE)
        try:
            filas = hoja_lineas_apu.antes_y_despues(sesion, nombre, Catalogo(sesion), codigo)
        except hoja_lineas_apu.MonedasDistintas as distintas:
            return antes_y_despues_a_respuesta(base, codigo, moneda, [], str(distintas))
    except (HojaInvalida, ValueError, CatalogoIncompleto) as error:
        raise HTTPException(status_code=409, detail=f"No se pudo comparar: {error}") from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    aviso = None
    if not filas:
        aviso = (
            f"Ninguna partida de la versión {codigo} cambió su APU respecto de la línea base "
            f"{base}."
        )
    return antes_y_despues_a_respuesta(base, codigo, moneda, filas, aviso)


@router.get("/borradores/{id}/insumos", response_model=InsumosHojaRespuesta)
@sin_eco(FORMA_BUSQUEDA)
def buscar_insumos(
    id: IdDeBorrador,
    request: Request,
    activa: CuentaQueVe,
    sesion: SesionDep,
    tipo: Annotated[Literal["material", "equipo", "mano_obra"], Query()],
    texto: Annotated[str, Query(max_length=500)] = "",
    limite: Annotated[int, Query(ge=1, le=hoja_edicion.LIMITE_INSUMOS + 1)] = (
        hoja_edicion.LIMITE_INSUMOS
    ),
) -> InsumosHojaRespuesta:
    """E8: los insumos de la lista de precios de la versión que se pueden elegir para una línea
    (del `tipo`, con `texto` en la descripción; ordenados por descripción). A lo sumo `limite`
    (301 se trata como 300, el tope de la clásica) y `hay_mas` si había más."""
    vivo = _vivo(request, activa, id)
    try:
        filas, hay_mas = hoja_edicion.candidatos_de_insumo(
            sesion, vivo, tipo, texto, min(limite, hoja_edicion.LIMITE_INSUMOS)
        )
    except hoja_edicion.SinVersionAbierta:
        raise HTTPException(status_code=409, detail=MENSAJE_SIN_VERSION) from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return insumos_a_respuesta(filas, hay_mas)


@router.get("/borradores/{id}/cambios", response_model=CambiosHojaRespuesta)
def cambios_del_borrador(
    id: IdDeBorrador, request: Request, activa: CuentaQueVe
) -> CambiosHojaRespuesta:
    """E9: la lista de cambios entre la versión abierta y el borrador (la que cuenta
    `resumen.cambios`), con el `rev` con que se calculó. Cada uno trae `insumo`: el de la línea
    del APU que nombra su clave (`{partida}|{rubro}|{n}`; nulo en otra clave, acta DS-75)."""
    return cambios_a_respuesta(*hoja_edicion.cambios_con_insumo(_vivo(request, activa, id)))


@router.get("/borradores/{id}/vistas/espacio", response_model=VistaEspacioRespuesta)
def vista_espacio(id: IdDeBorrador, request: Request, activa: CuentaQueVe) -> VistaEspacioRespuesta:
    """R5: Espacio y metrajes en lectura (tablas, Estado por fila, cantidades derivadas)."""
    return vista_espacio_a_respuesta(hoja_vista.vista_espacio(_vivo(request, activa, id)))


@router.get("/borradores/{id}/vistas/presupuesto", response_model=VistaPresupuestoRespuesta)
def vista_presupuesto(
    id: IdDeBorrador, request: Request, activa: CuentaQueVe
) -> VistaPresupuestoRespuesta:
    """R6: Presupuesto en lectura (renglones, cantidad calculada y escrita, PU, total, Estado)."""
    return vista_presupuesto_a_respuesta(hoja_vista.vista_presupuesto(_vivo(request, activa, id)))


@router.get("/borradores/{id}/vistas/apu", response_model=VistaApuRespuesta)
def vista_apu(
    id: IdDeBorrador,
    request: Request,
    activa: CuentaQueVe,
    sesion: SesionDep,
    partida: Annotated[str | None, Query(max_length=500)] = None,
    buscar: Annotated[str | None, Query(max_length=500)] = None,
) -> VistaApuRespuesta:
    """R7: APU en lectura (lista con buscador, tres rubros, cierre). La búsqueda la hace el
    servidor; sin coincidencias se devuelven todas las partidas. Los materiales con la traza
    vigente de su desperdicio traen la neta y el porcentaje (F5 vial, punto 1); no escribe."""
    vivo = _vivo(request, activa, id)
    try:
        vista = _vista_apu(sesion, vivo, partida, buscar)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return vista_apu_a_respuesta(vista)


@router.get("/borradores/{id}/vistas/plan", response_model=VistaPlanRespuesta)
def vista_plan(id: IdDeBorrador, request: Request, activa: CuentaQueVe) -> VistaPlanRespuesta:
    """R8: Plan y curva en lectura (matriz partida por periodo y curva de inversión)."""
    return vista_plan_a_respuesta(hoja_vista.vista_plan(_vivo(request, activa, id)))


@router.get("/borradores/{id}/vistas/equilibrio", response_model=VistaEquilibrioRespuesta)
def vista_equilibrio(
    id: IdDeBorrador, request: Request, activa: CuentaQueVe
) -> VistaEquilibrioRespuesta:
    """R9: Punto de equilibrio en lectura (ventas, costos, utilidad, punto y la frase del caso)."""
    return vista_equilibrio_a_respuesta(hoja_vista.vista_equilibrio(_vivo(request, activa, id)))


@router.get("/borradores/{id}/vistas/parametros", response_model=VistaParametrosRespuesta)
def vista_parametros(
    id: IdDeBorrador, request: Request, activa: CuentaQueVe, sesion: SesionDep
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
    id: IdDeBorrador, request: Request, activa: CuentaQueVe
) -> InformeAuditoriaRespuesta:
    """R11: el informe de auditoría del borrador, con todas las reglas y R17 (conexión de cada
    punto) ligada a su espacio; texto plano, sin Markdown."""
    return informe_a_respuesta(hoja_vista.informe_de_auditoria(_vivo(request, activa, id)))


@router.get("/trazabilidad", response_model=TrazabilidadHojaRespuesta, dependencies=[VER])
def trazabilidad(
    sesion: SesionDep,
    proyecto: Annotated[str, Query(min_length=1, max_length=500)],
    version: Annotated[str, Query(min_length=1, max_length=500)],
) -> TrazabilidadHojaRespuesta:
    """R14: el historial del proyecto y los registros de cambio de una versión guardada. Clave de
    API o sesión con `LEER_PROYECTO`; solo lee."""
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


@router.get("/precios", response_model=PreciosHojaRespuesta, dependencies=[VER])
def precios(
    sesion: SesionDep,
    proyecto: Annotated[str, Query(min_length=1, max_length=500)],
    version: Annotated[str, Query(min_length=1, max_length=500)],
) -> PreciosHojaRespuesta:
    """R12: el origen de cada precio de una versión guardada, evaluado a hoy (erosión y avisos de
    R11 y R12 en memoria). Clave de API o sesión con `LEER_PROYECTO`; solo lee."""
    try:
        nombre, lista = _version_guardada(sesion, proyecto, version)
        hoy = rutas_hoja._hoy()
        filas = hoja.precios_de_version(sesion, nombre, version, fecha_evaluacion=hoy)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return precios_a_respuesta(hoja_vista.vista_precios(filas, lista.moneda, hoy))


@router.get("/precios/atipicos", response_model=AtipicosRespuesta, dependencies=[VER])
def precios_atipicos(
    sesion: SesionDep,
    proyecto: Annotated[str, Query(min_length=1, max_length=500)],
    version: Annotated[str, Query(min_length=1, max_length=500)],
) -> AtipicosRespuesta:
    """R13: «Buscar variaciones atípicas de precio» (RF-100) sobre los insumos de una versión
    guardada, como el botón de la pestaña Precios. Solo lee: nada se guarda ni se bloquea. Sin el
    extra `ml` responde `disponible: false` y lo dice. Clave de API o sesión con `LEER_PROYECTO`."""
    try:
        nombre, _ = _version_guardada(sesion, proyecto, version)
        precios_de_la_version = hoja.precios_de_version(sesion, nombre, version)
        busqueda = busqueda_atipica.atipicos_de_insumos(
            sesion, [p.codigo for p in precios_de_la_version]
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return atipicos_a_respuesta(busqueda)
