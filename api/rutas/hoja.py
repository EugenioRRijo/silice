"""`/v1/hoja`: la hoja del proyecto en la interfaz nueva, lectura y navegación (T10, rebanada 3b).

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
- Vistas del borrador vivo (solo cuenta): R5 a R8 (3b-2: espacio, presupuesto, APU, plan) y R9 a R11
  (3b-3: `/vistas/equilibrio`, `/vistas/parametros`, `/vistas/auditoria`, esta con R17).
- Edición del borrador vivo (3c): E1 a E5 (espacio, cantidades, parámetros, plan), E6
  `PUT /apu/{partida}` y E7 `POST /apu/{partida}/insumo`, la lectura de los candidatos E8
  (`/insumos`) y de los cambios E9 (`/cambios`), E10 `GET /borradores` (retomar) y E11, el
  `reemplazar` de R2 (3c-3). Nada de esto escribe en la base: el guardado es 3d.
- Lecturas de una versión GUARDADA (3b-3; clave de API o sesión con `EDITAR_HOJA`; sin borrador y
  solo leen): R12 `GET /precios?proyecto=&version=`, R13 `GET /precios/atipicos?...` y R14
  `GET /trazabilidad?...`.

Los borradores y todo lo que los toca son **solo de una cuenta** (RF-82: el responsable es la
persona de la sesión, nunca un campo): con `X-Silice-Clave`, 403. Un borrador de otra ficha no
existe (404, no 403) y uno abierto en otro caso da 409 con un mensaje fijo, sin tocar ninguna base.
Montos como `{texto, exacto}`; `Cache-Control: no-store` también en los errores; el 422 no repite
lo enviado (`_RutaHoja` combina `RutaSinCache` y `RutaSinEco` **en ese orden**: al revés, la
primera atrapa el `RequestValidationError` antes y devuelve el 422 con eco).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from api.admin_acceso import cuenta_con
from api.dependencias import SesionDeEscrituraDep, SesionDep, url_de_la_peticion
from api.esquemas_atipicos import AtipicosRespuesta, atipicos_a_respuesta
from api.esquemas_hoja import (
    BorradorAbierto,
    BorradoresHojaRespuesta,
    BorradorHojaRespuesta,
    BorradorNuevo,
    CadenaHojaRespuesta,
    CambioDeInsumo,
    CambiosHojaRespuesta,
    ConvertirVersion,
    CotizarVersion,
    EdicionApu,
    EdicionApuRespuesta,
    EdicionCantidades,
    EdicionCantidadesRespuesta,
    EdicionEspacio,
    EdicionEspacioRespuesta,
    EdicionParametros,
    EdicionParametrosRespuesta,
    EdicionPlan,
    EdicionPlanRespuesta,
    EdicionSecuencial,
    GuardadoRespuesta,
    GuardarVersion,
    InstantaneaHojaRespuesta,
    InsumosHojaRespuesta,
    PreciosHojaRespuesta,
    RestaurarVersion,
    RetirarCotizacion,
    TrazabilidadHojaRespuesta,
    VersionesHojaRespuesta,
    VersionNuevaRespuesta,
    VistaApuRespuesta,
    VistaEquilibrioRespuesta,
    VistaEspacioRespuesta,
    VistaParametrosRespuesta,
    VistaPlanRespuesta,
    VistaPresupuestoRespuesta,
    base_a_respuesta,
    borradores_a_respuesta,
    cadena_a_respuesta,
    cambios_a_respuesta,
    guardado_a_respuesta,
    insumos_a_respuesta,
    precios_a_respuesta,
    resumen_a_respuesta,
    trazabilidad_a_respuesta,
    version_a_respuesta,
    version_nueva_a_respuesta,
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
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import atipicos as busqueda_atipica
from aplicacion import (
    hoja,
    hoja_borradores,
    hoja_edicion,
    hoja_guardado,
    hoja_versiones,
    hoja_vista,
)
from aplicacion.entrega import con_anexos_de_cadena
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_borradores import BorradorInexistente, BorradorVivo, RevDesactualizado
from aplicacion.hoja_versiones import ProyectoInexistente, VersionInexistente, VersionNueva
from aplicacion.proyectos import resolver_proyecto
from core.budget.moneda import moneda_del_proyecto
from core.catalog import Catalogo, CatalogoIncompleto
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
MENSAJE_REV = "El borrador cambió en otra ventana: vuelva a cargarlo."
MENSAJE_FORMA_ESPACIO = (
    "Los datos del espacio no tienen la forma esperada: escriba cada celda como texto de hasta "
    "500 caracteres y no pase de 5000 orígenes, 1000 ambientes, 1000 fuentes, 5000 puntos y "
    "20000 vértices."
)
FORMA_CANTIDADES = (
    "Las cantidades no tienen la forma esperada: envíe cada renglón como clave y cantidad en "
    "texto de hasta 500 caracteres, con no más de 20000 renglones."
)
FORMA_PARAMETROS = (
    "Los parámetros no tienen la forma esperada: envíe fcas, bono_alimentacion, administracion y "
    "utilidad, cada uno como texto de hasta 500 caracteres."
)
FORMA_PLAN = (
    "El plan no tiene la forma esperada: envíe periodos distintos (de 1 a 500) y cada fracción "
    "como texto de hasta 500 caracteres, con no más de 5000 partidas."
)
FORMA_REV = "La petición debe traer el rev del borrador, un número entero."
FORMA_APU = (
    "El APU no tiene la forma esperada: envíe el rendimiento y las cantidades de materiales, "
    "equipos y mano de obra, cada una como texto de hasta 500 caracteres, con no más de 500 "
    "líneas por rubro."
)
FORMA_INSUMO = (
    "El cambio de insumo no tiene la forma esperada: envíe tipo, indice (entero), insumo "
    "(código) y rev."
)
FORMA_BUSQUEDA = (
    "La búsqueda de insumos no tiene la forma esperada: indique tipo (material, equipo o "
    "mano_obra), un texto de hasta 500 caracteres y un límite de 1 a 301."
)
FORMA_GUARDAR = (
    "El guardado no tiene la forma esperada: envíe rev (entero) y la fuente como texto de hasta "
    "300 caracteres."
)
FORMA_RESTAURAR = (
    "La restauración no tiene la forma esperada: envíe proyecto, version y la fuente como texto "
    "de hasta 300 caracteres."
)
FORMA_COTIZAR = (
    "La cotización no tiene la forma esperada: envíe proyecto, version, insumo, precio (texto), "
    "proveedor, numero, fecha (AAAA-MM-DD) y, si quiere, la evidencia; cada texto con su tope."
)
FORMA_RETIRAR = (
    "El retiro no tiene la forma esperada: envíe proyecto, version, insumo (código) y el motivo "
    "como texto de hasta 300 caracteres."
)
FORMA_CONVERTIR = (
    "La conversión no tiene la forma esperada: envíe proyecto, version, moneda, lado (venta o "
    "compra) y la fuente como texto de hasta 300 caracteres."
)
FORMA_CADENA = "Indique el proyecto (código o nombre) de hasta 500 caracteres."
MENSAJE_PARTIDA = "Esa partida no tiene APU en este borrador: vuelva a cargar la lista de partidas."
MENSAJE_SIN_VERSION = "Abra una version guardada: los insumos se eligen de su lista de precios."
MENSAJE_SIN_PLAN = "Esta versión no tiene plan de trabajo: cree primero el plan secuencial."
MENSAJE_YA_TIENE_PLAN = "Esta versión ya tiene plan de trabajo: edítelo en la matriz del plan."


class _RutaHoja(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (diseño §1.3-7)."""

    mensaje_por_omision = MENSAJE_FORMA


router = APIRouter(prefix="/v1/hoja", tags=["hoja"], route_class=_RutaHoja)

LEER = Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))
CuentaDeLaHoja = Annotated[
    SesionActiva, Depends(cuenta_con(Accion.EDITAR_HOJA, MENSAJE_SOLO_CUENTA))
]
CuentaQueConvierte = Annotated[
    SesionActiva, Depends(cuenta_con(Accion.CONVERTIR_Y_REAJUSTAR, MENSAJE_SOLO_CUENTA))
]
IdDeBorrador = Annotated[str, Path(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
#: El código de una partida puede traer «/» (`EL-TUB-EMT-3/4`): se admite como segmento con barras.
CodigoDePartida = Annotated[str, Path(min_length=1, max_length=500)]


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


def _ya_guardado(codigo: str) -> HTTPException:
    """409: el borrador ya se guardó como la versión `codigo` (E1 a E7 y S1)."""
    return HTTPException(
        status_code=409,
        detail=(
            f"Este borrador ya se guardó como la versión {codigo}; abra esa versión para seguir."
        ),
    )


def _vivo(request: Request, activa: SesionActiva, id_: str) -> BorradorVivo:
    """El borrador de MI ficha (404 si no existe) y abierto en el caso de ahora (409)."""
    try:
        vivo = hoja_borradores.obtener(activa.huella_ficha, id_)
    except BorradorInexistente:
        raise HTTPException(status_code=404, detail=MENSAJE_FALTA) from None
    if vivo.caso != url_de_la_peticion(request):
        raise HTTPException(status_code=409, detail=MENSAJE_OTRO_CASO)
    return vivo


def _mas_nueva(vivo: BorradorVivo, vigente: str | None) -> str | None:
    """La versión vigente si alguien guardó después de que se abrió el borrador (D-5): regla única
    de `hoja_vista.version_mas_nueva` (la vigente de ahora contra la vigente al abrir)."""
    return hoja_vista.version_mas_nueva(vivo, vigente)


def _respuesta(sesion, vivo: BorradorVivo) -> dict:
    vigente = hoja.codigo_vigente(sesion, vivo.proyecto)
    mas_nueva = _mas_nueva(vivo, vigente)
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


def _pendiente_sin_guardar(vivo: BorradorVivo, cambios: int) -> JSONResponse:
    """E11: el 409 que lleva, además del texto, el id del borrador que se puede retomar."""
    cuantos = "1 cambio" if cambios == 1 else f"{cambios} cambios"
    return JSONResponse(
        status_code=409,
        content={
            "detalle": (
                f"Ya tiene un borrador de esta versión con {cuantos} sin guardar: "
                "retómelo o reemplácelo."
            ),
            "borrador_id": vivo.id,
        },
    )


@router.get("/borradores", response_model=BorradoresHojaRespuesta)
def listar_borradores(request: Request, activa: CuentaDeLaHoja) -> BorradoresHojaRespuesta:
    """E10: los borradores de MI ficha abiertos en el caso de ahora (sin los ya guardados), el
    usado más recientemente primero: lo que se puede retomar tras recargar o cambiar de proyecto.
    Listar no renueva el plazo de ninguno."""
    return borradores_a_respuesta(
        hoja_edicion.borradores_para_retomar(activa.huella_ficha, url_de_la_peticion(request))
    )


@router.post("/borradores", response_model=BorradorAbierto, status_code=201)
def abrir_borrador(
    datos: BorradorNuevo, request: Request, activa: CuentaDeLaHoja, sesion: SesionDep
) -> BorradorAbierto | JSONResponse:
    """R2: abre la versión como borrador vivo. Escribe la instantánea si faltaba (UC-15e).

    E11: si ya hay un borrador de esa misma versión con cambios sin guardar y `reemplazar` es
    falso, 409 con el id de ese borrador (`borrador_id`) y no se abre ni se escribe nada; con
    `reemplazar` se descartan los de esa versión y se abre uno nuevo. Un borrador sin cambios no
    estorba (se abre otro, como siempre: el tope por ficha acota). Abrir OTRA versión no descarta
    nada.

    En la firma `activa` va antes que `sesion`: FastAPI resuelve en ese orden y el acceso (401,
    403) debe responder antes de abrir la base del caso."""
    try:
        con_anexos_de_cadena(sesion)  # el sello de lo que se escriba cubre los anexos (§1.2)
        nombre = _proyecto(sesion, datos.proyecto).nombre
        caso = url_de_la_peticion(request)
        if not datos.reemplazar:  # E11: antes de escribir nada (la instantánea de abajo)
            pendiente = hoja_edicion.pendiente_de_la_version(
                activa.huella_ficha, caso, nombre, datos.version
            )
            if pendiente is not None:
                return _pendiente_sin_guardar(*pendiente)
        filas = hoja.historial_de_versiones(sesion, nombre)
        # D-5: la vigente se lee ANTES de abrir; si alguien guarda entre las dos lecturas, la
        # vigente de ahora diferira de esta y se pedira confirmar (falla hacia lo seguro).
        vigente_al_abrir = hoja.codigo_vigente(sesion, nombre)
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
        if datos.reemplazar:  # recién ahora, cuando abrir ya no puede fallar: si falla, queda
            hoja_edicion.descartar_de_la_version(activa.huella_ficha, caso, nombre, datos.version)
        vivo = hoja_borradores.crear(
            activa.huella_ficha,
            caso,
            nombre,
            datos.version,
            borrador,
            abierta,
            vigente_al_abrir=vigente_al_abrir,
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


def _editar(
    sesion,
    vivo: BorradorVivo,
    editar: Callable[[], BorradorVivo],
    vista_de: Callable[[BorradorVivo], Any],
) -> tuple[Any, Any]:
    """El esqueleto común de E1 a E7: una petición a la vez por borrador (su cerrojo) y, dentro,
    la edición y las dos piezas de la respuesta (el resumen y la vista de la pestaña), de modo que
    ambas son las del `rev` que ESTA edición produjo. Los errores de la edición se traducen aquí:
    404 (ya no existe el borrador ni la partida), 409 (`rev` viejo, ya guardado, el estado del
    plan, sin versión abierta), 422 (el texto de la clásica, sin repetirlo en ningún otro lado) y
    503 (la base)."""
    try:
        with vivo.cerrojo:
            try:
                editado = editar()
            except BorradorInexistente:
                raise HTTPException(status_code=404, detail=MENSAJE_FALTA) from None
            except RevDesactualizado:
                raise HTTPException(status_code=409, detail=MENSAJE_REV) from None
            except hoja_edicion.BorradorYaGuardado as error:
                raise _ya_guardado(error.codigo) from None
            except hoja_edicion.SinPlan:
                raise HTTPException(status_code=409, detail=MENSAJE_SIN_PLAN) from None
            except hoja_edicion.YaTienePlan:
                raise HTTPException(status_code=409, detail=MENSAJE_YA_TIENE_PLAN) from None
            except hoja_edicion.SinVersionAbierta:
                raise HTTPException(status_code=409, detail=MENSAJE_SIN_VERSION) from None
            except hoja_edicion.PartidaSinApu:
                raise HTTPException(status_code=404, detail=MENSAJE_PARTIDA) from None
            except HojaInvalida as error:
                raise HTTPException(status_code=422, detail=str(error)) from None
            mas_nueva = _mas_nueva(editado, hoja.codigo_vigente(sesion, editado.proyecto))
            return hoja_vista.resumen(editado, mas_nueva), vista_de(editado)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None


@router.post("/borradores/{id}/guardar", response_model=GuardadoRespuesta)
@sin_eco(FORMA_GUARDAR)
def guardar_borrador(
    id: IdDeBorrador,
    datos: GuardarVersion,
    request: Request,
    activa: CuentaDeLaHoja,
    sesion: SesionDeEscrituraDep,
) -> GuardadoRespuesta | JSONResponse:
    """S1: guarda el borrador como versión nueva (o como la primera si el proyecto no tenía
    versiones) y lo cierra. ESCRIBE en la base del caso, en una sola transacción que empieza con
    `BEGIN IMMEDIATE` y con la cadena de sellos cubriendo el espacio (3d-B3, B7).

    El responsable es la persona de la sesión, nunca un campo del cuerpo (RF-82). Todo o nada: ante
    cualquier error no queda ninguna fila. Con una versión más nueva que la abierta, 409 (con
    `version_mas_nueva`) salvo `confirmar_version_mas_nueva`. `activa` va antes que `sesion`: el
    acceso (401, 403) responde antes de abrir la base del caso."""
    _vivo(request, activa, id)  # 404 (otra ficha), 409 (otro caso): sin tocar ninguna base
    try:
        guardado = hoja_guardado.guardar(
            sesion,
            activa.huella_ficha,
            id,
            datos.rev,
            fuente=datos.fuente,
            responsable=activa.usuario,
            confirmar_version_mas_nueva=datos.confirmar_version_mas_nueva,
        )
    except BorradorInexistente:
        raise HTTPException(status_code=404, detail=MENSAJE_FALTA) from None
    except RevDesactualizado:
        raise HTTPException(status_code=409, detail=MENSAJE_REV) from None
    except hoja_guardado.BorradorYaGuardado as error:
        raise _ya_guardado(error.codigo) from None
    except hoja_guardado.VersionMasNueva as error:
        return JSONResponse(
            status_code=409, content={"detalle": str(error), "version_mas_nueva": error.vigente}
        )
    except hoja_guardado.VersionSoloLectura as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except HojaInvalida as error:  # antes que ValueError: es una subclase
        raise HTTPException(status_code=422, detail=str(error)) from None
    except (ValueError, CatalogoIncompleto) as error:
        raise HTTPException(status_code=409, detail=f"No se guardó nada: {error}") from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return guardado_a_respuesta(guardado)


@router.put("/borradores/{id}/espacio", response_model=EdicionEspacioRespuesta)
@sin_eco(MENSAJE_FORMA_ESPACIO)
def editar_espacio(
    id: IdDeBorrador,
    datos: EdicionEspacio,
    request: Request,
    activa: CuentaDeLaHoja,
    sesion: SesionDep,
) -> EdicionEspacioRespuesta:
    """E1: aplica las cinco tablas del editor al espacio del borrador y lo devuelve recalculado.

    Solo cambia el borrador en memoria (nada a la base: el guardado es 3d). `rev` viejo, 409; un
    dato inválido, 422 con el texto de la clásica y el borrador intacto. Una petición a la vez por
    borrador: se toma su cerrojo y la respuesta es la del `rev` que esta edición produjo."""
    vivo = _vivo(request, activa, id)
    resumen, vista = _editar(
        sesion,
        vivo,
        lambda: hoja_edicion.editar_espacio(
            sesion, activa.huella_ficha, id, datos.rev, datos.tablas.como_filas()
        ),
        hoja_vista.vista_espacio,
    )
    return EdicionEspacioRespuesta(
        rev=resumen.rev,
        resumen=resumen_a_respuesta(resumen),
        espacio=vista_espacio_a_respuesta(vista),
    )


@router.put("/borradores/{id}/cantidades", response_model=EdicionCantidadesRespuesta)
@sin_eco(FORMA_CANTIDADES)
def editar_cantidades(
    id: IdDeBorrador,
    datos: EdicionCantidades,
    request: Request,
    activa: CuentaDeLaHoja,
    sesion: SesionDep,
) -> EdicionCantidadesRespuesta:
    """E2: escribe a mano las cantidades de los renglones tocados (solo esas filas) y devuelve el
    presupuesto recalculado. El servidor arma la tabla completa para que `fila {n}` del error sea
    la de la clásica; un valor igual al calculado deja de ser «escrito» (3c-B3 a B5)."""
    vivo = _vivo(request, activa, id)
    resumen, vista = _editar(
        sesion,
        vivo,
        lambda: hoja_edicion.editar_cantidades(
            sesion, activa.huella_ficha, id, datos.rev, datos.como_filas()
        ),
        hoja_vista.vista_presupuesto,
    )
    return EdicionCantidadesRespuesta(
        rev=resumen.rev,
        resumen=resumen_a_respuesta(resumen),
        presupuesto=vista_presupuesto_a_respuesta(vista),
    )


@router.put("/borradores/{id}/parametros", response_model=EdicionParametrosRespuesta)
@sin_eco(FORMA_PARAMETROS)
def editar_parametros(
    id: IdDeBorrador,
    datos: EdicionParametros,
    request: Request,
    activa: CuentaDeLaHoja,
    sesion: SesionDep,
) -> EdicionParametrosRespuesta:
    """E3: aplica los cuatro parámetros de costo (texto exacto) y devuelve la vista de
    parámetros; un cambio válido recalcula todos los APU (3c-B1, 3c-B2)."""
    vivo = _vivo(request, activa, id)

    def vista_de(editado: BorradorVivo):
        moneda = moneda_del_proyecto(sesion, _proyecto(sesion, editado.proyecto))
        return hoja_vista.vista_parametros(
            editado, moneda, permitido(activa.roles, Accion.CONVERTIR_Y_REAJUSTAR)
        )

    resumen, vista = _editar(
        sesion,
        vivo,
        lambda: hoja_edicion.editar_parametros(
            sesion, activa.huella_ficha, id, datos.rev, datos.como_textos()
        ),
        vista_de,
    )
    return EdicionParametrosRespuesta(
        rev=resumen.rev,
        resumen=resumen_a_respuesta(resumen),
        parametros=vista_parametros_a_respuesta(vista),
    )


@router.put("/borradores/{id}/plan", response_model=EdicionPlanRespuesta)
@sin_eco(FORMA_PLAN)
def editar_plan(
    id: IdDeBorrador,
    datos: EdicionPlan,
    request: Request,
    activa: CuentaDeLaHoja,
    sesion: SesionDep,
) -> EdicionPlanRespuesta:
    """E4: aplica la matriz partida por periodo (cada partida suma exactamente 1) y devuelve el
    plan y la curva recalculados. Sin plan, 409: se crea primero el secuencial (3c-B12)."""
    vivo = _vivo(request, activa, id)
    resumen, vista = _editar(
        sesion,
        vivo,
        lambda: hoja_edicion.editar_plan(
            sesion, activa.huella_ficha, id, datos.rev, datos.etiquetas, datos.como_filas()
        ),
        hoja_vista.vista_plan,
    )
    return EdicionPlanRespuesta(
        rev=resumen.rev, resumen=resumen_a_respuesta(resumen), plan=vista_plan_a_respuesta(vista)
    )


@router.post("/borradores/{id}/plan/secuencial", response_model=EdicionPlanRespuesta)
@sin_eco(FORMA_REV)
def crear_plan_secuencial(
    id: IdDeBorrador,
    datos: EdicionSecuencial,
    request: Request,
    activa: CuentaDeLaHoja,
    sesion: SesionDep,
) -> EdicionPlanRespuesta:
    """E5: crea el plan secuencial (una partida por periodo) de un borrador sin plan; con plan,
    409 (3c-B12)."""
    vivo = _vivo(request, activa, id)
    resumen, vista = _editar(
        sesion,
        vivo,
        lambda: hoja_edicion.crear_plan_secuencial(sesion, activa.huella_ficha, id, datos.rev),
        hoja_vista.vista_plan,
    )
    return EdicionPlanRespuesta(
        rev=resumen.rev, resumen=resumen_a_respuesta(resumen), plan=vista_plan_a_respuesta(vista)
    )


@router.put("/borradores/{id}/apu/{partida:path}", response_model=EdicionApuRespuesta)
@sin_eco(FORMA_APU)
def editar_apu(
    id: IdDeBorrador,
    partida: CodigoDePartida,
    datos: EdicionApu,
    request: Request,
    activa: CuentaDeLaHoja,
    sesion: SesionDep,
) -> EdicionApuRespuesta:
    """E6: escribe el rendimiento y la cantidad de cada línea del APU de una partida (en la copia
    de la versión, DA-SF-7) y devuelve el APU recalculado (3c-B10). Una partida sin APU en el
    borrador es 404; un APU igual al vigente no sube `rev`."""
    vivo = _vivo(request, activa, id)
    resumen, vista = _editar(
        sesion,
        vivo,
        lambda: hoja_edicion.editar_apu(
            sesion,
            activa.huella_ficha,
            id,
            datos.rev,
            partida,
            datos.rendimiento,
            datos.materiales,
            datos.equipos,
            datos.mano_obra,
        ),
        lambda editado: hoja_vista.vista_apu(editado, partida),
    )
    return EdicionApuRespuesta(
        rev=resumen.rev, resumen=resumen_a_respuesta(resumen), apu=vista_apu_a_respuesta(vista)
    )


@router.post("/borradores/{id}/apu/{partida:path}/insumo", response_model=EdicionApuRespuesta)
@sin_eco(FORMA_INSUMO)
def cambiar_insumo(
    id: IdDeBorrador,
    partida: CodigoDePartida,
    datos: CambioDeInsumo,
    request: Request,
    activa: CuentaDeLaHoja,
    sesion: SesionDep,
) -> EdicionApuRespuesta:
    """E7: la línea `indice` del rubro `tipo` pasa al insumo `insumo` (código) de la lista de
    precios de la versión: toma descripción, unidad y precio y conserva la cantidad (3c-B11).
    Sin versión abierta, 409; un insumo que la lista no valora, 422."""
    vivo = _vivo(request, activa, id)
    resumen, vista = _editar(
        sesion,
        vivo,
        lambda: hoja_edicion.cambiar_insumo_de_linea(
            sesion,
            activa.huella_ficha,
            id,
            datos.rev,
            partida,
            datos.tipo,
            datos.indice,
            datos.insumo,
        ),
        lambda editado: hoja_vista.vista_apu(editado, partida),
    )
    return EdicionApuRespuesta(
        rev=resumen.rev, resumen=resumen_a_respuesta(resumen), apu=vista_apu_a_respuesta(vista)
    )


@router.get("/borradores/{id}/insumos", response_model=InsumosHojaRespuesta)
@sin_eco(FORMA_BUSQUEDA)
def buscar_insumos(
    id: IdDeBorrador,
    request: Request,
    activa: CuentaDeLaHoja,
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
    id: IdDeBorrador, request: Request, activa: CuentaDeLaHoja
) -> CambiosHojaRespuesta:
    """E9: la lista de cambios entre la versión abierta y el borrador (la que cuenta
    `resumen.cambios`), con el `rev` con que se calculó."""
    return cambios_a_respuesta(*hoja_edicion.cambios_del_borrador(_vivo(request, activa, id)))


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


# --- S2 a S6 (3d-2): versiones nuevas desde una guardada y la cadena -------------------------


def _crear_version(operacion: Callable[[], VersionNueva]) -> VersionNuevaRespuesta:
    """Corre una operacion que crea una version y traduce sus errores: 404 (el proyecto o la
    version no existen), 422 (un dato de dominio, con el texto de la clasica), 409
    (`CatalogoIncompleto`: falta una composicion) y 503 (la base). Lo inesperado sube: tras
    deshacer, FastAPI responde su 500 generico sin detalle."""
    try:
        return version_nueva_a_respuesta(operacion())
    except (ProyectoInexistente, VersionInexistente) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except HojaInvalida as error:  # antes que ValueError: es una subclase
        raise HTTPException(status_code=422, detail=str(error)) from None
    except (ValueError, CatalogoIncompleto) as error:
        raise HTTPException(status_code=409, detail=f"No se guardó nada: {error}") from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None


@router.post("/versiones/restaurar", response_model=VersionNuevaRespuesta)
@sin_eco(FORMA_RESTAURAR)
def restaurar_version(
    datos: RestaurarVersion, activa: CuentaDeLaHoja, sesion: SesionDeEscrituraDep
) -> VersionNuevaRespuesta:
    """S2: restaura una versión anterior como versión nueva y vigente (RF-54). Escribe en una
    transacción con `BEGIN IMMEDIATE` y la cadena de sellos cubriendo los anexos; el responsable
    es la persona de la sesión. `activa` va antes que `sesion`: el acceso responde antes de abrir
    la base del caso."""
    return _crear_version(
        lambda: hoja_versiones.restaurar(
            sesion,
            datos.proyecto,
            datos.version,
            fuente=datos.fuente,
            responsable=activa.usuario,
        )
    )


@router.post("/versiones/cotizar", response_model=VersionNuevaRespuesta)
@sin_eco(FORMA_COTIZAR)
def cotizar_insumo(
    datos: CotizarVersion, activa: CuentaDeLaHoja, sesion: SesionDeEscrituraDep
) -> VersionNuevaRespuesta:
    """S3: cotiza un insumo para el proyecto y guarda la versión nueva (RF-56). El precio llega
    como texto; solo cambia ese insumo en ese proyecto."""
    return _crear_version(
        lambda: hoja_versiones.cotizar(
            sesion,
            datos.proyecto,
            datos.version,
            insumo=datos.insumo,
            precio=datos.precio,
            proveedor=datos.proveedor,
            numero=datos.numero,
            fecha=datos.fecha,
            evidencia=datos.evidencia,
            responsable=activa.usuario,
        )
    )


@router.post("/versiones/retirar-cotizacion", response_model=VersionNuevaRespuesta)
@sin_eco(FORMA_RETIRAR)
def retirar_cotizacion(
    datos: RetirarCotizacion, activa: CuentaDeLaHoja, sesion: SesionDeEscrituraDep
) -> VersionNuevaRespuesta:
    """S4: retira la cotización de un insumo; la versión nueva vuelve al precio de la lista base."""
    return _crear_version(
        lambda: hoja_versiones.retirar_cotizacion(
            sesion,
            datos.proyecto,
            datos.version,
            insumo=datos.insumo,
            motivo=datos.motivo,
            responsable=activa.usuario,
        )
    )


@router.post("/versiones/convertir", response_model=VersionNuevaRespuesta)
@sin_eco(FORMA_CONVERTIR)
def convertir_version(
    datos: ConvertirVersion, activa: CuentaQueConvierte, sesion: SesionDeEscrituraDep
) -> VersionNuevaRespuesta:
    """S5: convierte la versión a otra moneda con la tasa del BCV de hoy (RF-64). Exige
    `CONVERTIR_Y_REAJUSTAR` (la matriz de permisos), no solo editar la hoja."""
    return _crear_version(
        lambda: hoja_versiones.convertir(
            sesion,
            datos.proyecto,
            datos.version,
            datos.moneda,
            lado=datos.lado,
            fecha=_hoy(),
            fuente=datos.fuente,
            responsable=activa.usuario,
        )
    )


@router.get("/cadena", response_model=CadenaHojaRespuesta, dependencies=[LEER])
@sin_eco(FORMA_CADENA)
def cadena_de_sellos(
    sesion: SesionDep, proyecto: Annotated[str, Query(min_length=1, max_length=500)]
) -> CadenaHojaRespuesta:
    """S6: el estado de integridad de la cadena de sellos del proyecto (recalcula cada huella).
    Clave de API o sesión con `EDITAR_HOJA`; solo lee."""
    try:
        return cadena_a_respuesta(hoja_versiones.estado_de_la_cadena(sesion, proyecto))
    except ProyectoInexistente as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
