"""`/v1/vial`: los tramos viales de una versión, por la API (plan vial, Tarea 8).

Mismo estilo que la Hoja (`api/rutas/hoja.py`): la obra se nombra con `proyecto` (su código de
`/v1/proyectos` o su nombre) y la versión con su `version` (código), ambos en la consulta; montos y
cifras como texto; `Cache-Control: no-store` también en los errores; el 422 de forma no repite lo
enviado. Acción `EDITAR_HOJA`:

- `GET /tramos?proyecto=&version=` → los tramos de la versión, sus cantidades (m2, m3, l, t, t·km y
  m, cada una con su regla y su origen), si se pueden editar, de qué versión los hereda
  (`heredados_de`) y quién guardó por última vez. Clave de API o sesión.
- `PUT /tramos?proyecto=&version=` `{tramos, fuente}` → guarda los tramos como los de la versión
  (un guardado nuevo: el anterior queda como rastro). Solo con una cuenta (la clave de API recibe
  403, como en la Hoja). 422 con el texto del dominio y el id del tramo; versión enviada, aprobada
  o devuelta: 409; obra o versión inexistente: 404.
- `POST /tramos/importar?proyecto=&version=` (multipart: `archivo`, un CSV de hasta 2 MiB) → lee el
  archivo y lo guarda como el `PUT`. Todo o nada: una fila mala es 422 con el nombre del archivo y
  el número de fila, y no se guarda nada. Archivo que no es `.csv`: 415; de más de 2 MiB: 413.
- `GET /obras` → los `id` de las obras de la carpeta abierta con tramos guardados (lo usa el marco
  para ofrecer «Tramos» solo donde hay una vía).
- `POST /tramos/llevar` `{proyecto, version}` → 200 `{borrador_id, renglones, version}` (Tarea
  8b, `aplicacion.hoja_vial`): lleva las cantidades de los tramos de esa versión al borrador de la
  Hoja de la obra (el vivo de esa ficha y obra o uno nuevo sobre la vigente), cada una con su
  origen de tramo; llevar otra vez sincroniza. No guarda versión. Mismo acceso que
  `POST /v1/hoja/llevar` (solo una cuenta, CSRF, `Origin`, `no-store`) y sus mismos errores: obra
  que no existe, 404 sin eco; partidas sin APU, 404 con todos los códigos; borrador de otra
  versión, versión que no existe o sin tramos, sin lista o que ya no se abre, o borrador que
  cambió entretanto, 409; cifra mala, 422; la base, 503.
- `GET /reportes/{tipo}?proyecto=&version=&periodo=` → un libro .xlsx (Tarea 21,
  `aplicacion.reportes_viales`) con una hoja de portada que dice de dónde sale cada cifra. `tipo`:
  `computos` (tramos y cantidades), `apu` (APU con el origen de cada precio y la conciliación CV1 a
  CV3), `resumen` (subtotal, IVA y total) —los tres piden `proyecto` y `version`— y `produccion`
  (costo de producción de un `periodo` AAAA-MM). Mismo acceso que `GET /tramos` (clave de API o
  sesión), solo lee y no deja caché. Tipo que no existe y período sin cálculos: 404; falta de un
  dato, período mal escrito o versión sin tramos: 422; la base, 503.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from api.acceso_modulos import ModuloVial
from api.admin_acceso import cuenta_con
from api.dependencias import SesionDep, SesionInstalacionDep, url_de_la_peticion
from api.esquemas_vial import (
    LlevarTramos,
    ObrasViales,
    TramosEntrada,
    TramosLlevados,
    TramosRespuesta,
    a_tramos,
    cantidad_a_respuesta,
    rastro_a_respuesta,
    tramo_a_respuesta,
)
from api.rutas.hoja import CuentaDeLaHoja
from api.rutas.hoja_exportar import TIPO_XLSX
from api.rutas.hoja_llevar import MENSAJE_CAMBIO
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import elaboracion, hoja_edicion, hoja_vial, reportes_viales, vial
from aplicacion.entrega import con_anexos_de_cadena
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_borradores import BorradorInexistente, RevDesactualizado
from aplicacion.proyectos import resolver_proyecto
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_FORMA = (
    "Los tramos no tienen la forma esperada: envíe cada tramo con su id, sus progresivas, su ancho "
    "y sus capas, y cada cifra como texto con punto decimal; hasta 2000 tramos."
)
MENSAJE_SOLO_CUENTA = "Los tramos se guardan con una cuenta; la clave de API no sirve."
MENSAJE_BASE = (
    "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro "
    "programa."
)
FORMA_LLEVAR = "Envíe la obra y la versión cuyos tramos se llevan al presupuesto."
#: Los reportes de la Tarea 21 que piden una versión, y el que pide un período.
REPORTES_DE_VERSION = ("computos", "apu", "resumen")
REPORTE_DE_PERIODO = "produccion"
MENSAJE_REPORTE = (
    "Este reporte pide la obra y la versión (proyecto y version en la consulta); el de "
    "producción, el período como AAAA-MM (periodo)."
)
TOPE_BYTES = 2 * 1024 * 1024
BLOQUE = 64 * 1024
EXTENSION = ".csv"


class _RutaVial(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (como `_RutaHoja`)."""

    mensaje_por_omision = MENSAJE_FORMA


# El módulo vial se comprueba en cada ruta (`ModuloVial`), DESPUÉS de la acción: sin entrar, 401;
# sin el rol, 403; con el rol y el módulo apagado, 404 (D-V-4).
router = APIRouter(prefix="/v1/vial", tags=["vial"], route_class=_RutaVial)

LEER = Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))
CuentaQueEdita = Annotated[
    SesionActiva, Depends(cuenta_con(Accion.EDITAR_HOJA, MENSAJE_SOLO_CUENTA))
]
Proyecto = Annotated[str, Query(min_length=1, max_length=500)]
Version = Annotated[str, Query(min_length=1, max_length=40)]
# La cuenta va antes que la sesión de la base en cada firma: el acceso se decide antes de abrir.


def _respuesta(sesion, proyecto: str, codigo: str) -> TramosRespuesta:
    """Lo guardado de la versión (404 si no existe), con sus cantidades y su estado."""
    version_id = vial.version_de(sesion, proyecto, codigo)
    obra = resolver_proyecto(sesion, proyecto)
    tramos = vial.tramos_de_version(sesion, version_id)
    bloqueo = vial.bloqueo_de_version(sesion, version_id)
    return TramosRespuesta(
        proyecto=obra.nombre if obra else proyecto,
        version=codigo,
        editable=bloqueo is None,
        bloqueo=bloqueo,
        heredados_de=vial.heredados_de(sesion, version_id),
        guardado=rastro_a_respuesta(vial.guardado_de_version(sesion, version_id)),
        tramos=[tramo_a_respuesta(t) for t in tramos],
        cantidades=[cantidad_a_respuesta(c) for c in vial.cantidades_de_tramos(tramos)],
    )


def _guardar(sesion, proyecto: str, codigo: str, tramos, activa: SesionActiva, fuente: str):
    try:
        vial.guardar_tramos(
            sesion,
            vial.version_de(sesion, proyecto, codigo),
            tramos,
            usuario=activa.usuario,
            ahora=ahora(),
            fuente=fuente,
        )
    except vial.VersionBloqueada as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return _respuesta(sesion, proyecto, codigo)


@router.get("/tramos", response_model=TramosRespuesta, dependencies=[LEER])
def leer_tramos(
    _modulo: ModuloVial, sesion: SesionDep, proyecto: Proyecto, version: Version
) -> TramosRespuesta:
    """Los tramos de la versión con sus cantidades, y si se pueden editar."""
    try:
        return _respuesta(sesion, proyecto, version)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None


@router.put("/tramos", response_model=TramosRespuesta)
def guardar_los_tramos(
    activa: CuentaQueEdita,
    _modulo: ModuloVial,
    sesion: SesionDep,
    entrada: TramosEntrada,
    proyecto: Proyecto,
    version: Version,
) -> TramosRespuesta:
    """Guarda los tramos como los de la versión (un guardado nuevo; el anterior queda de rastro)."""
    try:
        tramos = a_tramos(entrada.tramos)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    try:
        return _guardar(sesion, proyecto, version, tramos, activa, entrada.fuente)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None


async def _leer_archivo(archivo: UploadFile) -> bytes:
    """Los bytes de la subida, por bloques; 413 en cuanto pasan de `TOPE_BYTES`."""
    excedido = HTTPException(
        413, f"El archivo supera el máximo de {TOPE_BYTES // 2**20} MiB. Divídalo en varios."
    )
    if archivo.size is not None and archivo.size > TOPE_BYTES:
        raise excedido
    partes: list[bytes] = []
    total = 0
    while bloque := await archivo.read(BLOQUE):
        total += len(bloque)
        if total > TOPE_BYTES:
            raise excedido
        partes.append(bloque)
    return b"".join(partes)


@router.post("/tramos/importar", response_model=TramosRespuesta)
async def importar_tramos(
    activa: CuentaQueEdita,
    _modulo: ModuloVial,
    sesion: SesionDep,
    proyecto: Proyecto,
    version: Version,
    archivo: Annotated[UploadFile, File(description="Tramos de la vía (.csv, UTF-8)")],
) -> TramosRespuesta:
    """Lee el CSV y lo guarda como los tramos de la versión. Todo o nada: una fila mala es 422 con
    su número y no se guarda nada."""
    nombre = (archivo.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not nombre.lower().endswith(EXTENSION) or len(nombre) <= len(EXTENSION):
        recibido = nombre[:120] or "sin nombre"
        raise HTTPException(415, f"Los tramos van en un archivo .csv (se recibió «{recibido}»).")
    contenido = await _leer_archivo(archivo)

    def operacion() -> TramosRespuesta:
        try:
            tramos = vial.tramos_desde_csv(contenido, nombre)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        return _guardar(sesion, proyecto, version, tramos, activa, f"Importado de {nombre[:120]}")

    try:
        return await run_in_threadpool(operacion)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None


@router.get("/obras", response_model=ObrasViales, dependencies=[LEER])
def obras_con_tramos(_modulo: ModuloVial, sesion: SesionDep) -> ObrasViales:
    """Las obras de la carpeta abierta que tienen tramos guardados."""
    try:
        return ObrasViales(obras=vial.obras_con_tramos(sesion))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None


def _hoy() -> date:
    """El día de la evaluación de precios al abrir la versión: hoy (las pruebas lo fijan)."""
    return date.today()


@router.post("/tramos/llevar", response_model=TramosLlevados)
@sin_eco(FORMA_LLEVAR)
def llevar_al_presupuesto(
    datos: LlevarTramos,
    request: Request,
    activa: CuentaDeLaHoja,
    _modulo: ModuloVial,
    sesion: SesionDep,
) -> TramosLlevados:
    """Lleva las cantidades de los tramos al borrador de la Hoja de la obra, todo o nada, sin
    guardar versión (`aplicacion.hoja_vial.llevar_tramos_a_la_hoja`). `activa` va antes que
    `sesion`: el acceso responde antes de abrir la base del caso."""
    try:
        con_anexos_de_cadena(sesion)  # el sello de lo que se escriba cubre los anexos (§1.2)
        proyecto = resolver_proyecto(sesion, datos.proyecto)
        if proyecto is None:
            raise HTTPException(status_code=404, detail=elaboracion.MENSAJE_SIN_OBRA)
        borrador_id, renglones = hoja_vial.llevar_tramos_a_la_hoja(
            sesion,
            activa.huella_ficha,
            url_de_la_peticion(request),
            proyecto,
            datos.version,
            responsable=activa.usuario,
            hoy=_hoy(),
        )
    except hoja_edicion.PartidaFueraDelCatalogo as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except (
        hoja_vial.BorradorDeOtraVersion,
        hoja_vial.SinTramos,
        vial.VersionInexistente,
        hoja_edicion.SinListaDeLaObra,
        elaboracion.VersionQueNoSeAbre,
    ) as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except (hoja_edicion.BorradorYaGuardado, RevDesactualizado, BorradorInexistente):
        raise HTTPException(status_code=409, detail=MENSAJE_CAMBIO) from None
    except HojaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return TramosLlevados(borrador_id=borrador_id, renglones=renglones, version=datos.version)


@router.get(
    "/reportes/{tipo}",
    response_class=Response,
    dependencies=[LEER],
    responses={200: {"content": {TIPO_XLSX: {}}, "description": "El libro .xlsx del reporte."}},
)
def descargar_reporte(
    tipo: str,
    _modulo: ModuloVial,
    sesion: SesionDep,
    instalacion: SesionInstalacionDep,
    proyecto: Annotated[str | None, Query(min_length=1, max_length=500)] = None,
    version: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
    periodo: Annotated[str | None, Query(min_length=1, max_length=20)] = None,
) -> Response:
    """Un reporte de la obra vial en Excel (`aplicacion.reportes_viales`); solo lee."""
    if tipo not in (*REPORTES_DE_VERSION, REPORTE_DE_PERIODO):
        raise HTTPException(status_code=404, detail=f"No existe el reporte «{tipo[:40]}».")
    if tipo == REPORTE_DE_PERIODO and periodo is None:
        raise HTTPException(status_code=422, detail=MENSAJE_REPORTE)
    if tipo in REPORTES_DE_VERSION and (proyecto is None or version is None):
        raise HTTPException(status_code=422, detail=MENSAJE_REPORTE)
    try:
        if tipo == "computos":
            contenido = reportes_viales.computos_de_la_version(sesion, proyecto, version)
        elif tipo == "apu":
            contenido = reportes_viales.apu_de_la_version(sesion, instalacion, proyecto, version)
        elif tipo == "resumen":
            contenido = reportes_viales.resumen_de_la_version(sesion, proyecto, version)
        else:
            contenido = reportes_viales.costo_de_produccion_del_periodo(instalacion, periodo)
    except reportes_viales.SinCalculosDelPeriodo as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    partes = (x for x in (proyecto, version, periodo) if x)
    nombre = reportes_viales.nombre_de_reporte(tipo, *partes)
    return Response(
        content=contenido,
        media_type=TIPO_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
