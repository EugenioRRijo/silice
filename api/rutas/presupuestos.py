"""Rutas de presupuestos por HTTP: elaborar, consultar, exportar, actualizar precios y escenarios.

UC-01 (`POST /presupuestos`, a partir de `ItemComputo` ya extraídos, con el plan de trabajo del
proyectista o, sin él, `plan_secuencial`, paso 6; un ítem sin partida queda pendiente y se lista
con sus partidas similares, flujo 3a; una partida sin rendimiento estimado vigente responde 409
con el rendimiento que propone el histórico, flujo 3b), UC-05 (el informe de auditoría, que se
genera siempre), UC-02 (`POST /presupuestos/{codigo}/actualizacion`, que desde C6 declara en el
informe de la versión nueva los precios atípicos de la lista, UC-07 5) y UC-08
(`POST /presupuestos/{codigo}/escenarios`, que declara los pendientes del base). Desde C6, también
el paso 1 de UC-01 (`POST /proyectos`, INV-086) y el presupuesto tabular de un tercero de RF-24 y
UC-05 (`POST /presupuestos/importar`, INV-076). Los montos se presentan siempre con dos decimales
(`core.verification.informe.DECIMALES_PRESENTACION`), la misma cifra que usa `ui/app.py` y la
exportación a Excel: esta capa no inventa su propio redondeo.
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from api.acceso import EDITAR, LEER
from api.archivos import guardar_subida
from api.dependencias import USUARIO_SIN_CLAVE, SesionDep
from api.esquemas import (
    ActualizacionPeticion,
    ComparativoRespuesta,
    EscenarioPeticion,
    EscenarioRespuesta,
    EscenariosPeticion,
    EscenariosRespuesta,
    FilaComparativoRespuesta,
    ItemComputoPeticion,
    ItemPendienteRespuesta,
    PartidaPresupuestadaRespuesta,
    PendienteRespuesta,
    PeriodoPlanPeticion,
    PresupuestoCreadoRespuesta,
    PresupuestoDetalleRespuesta,
    PresupuestoPeticion,
    PropuestaPartidaRespuesta,
    ProyectoPeticion,
    ProyectoRespuesta,
    RendimientoPorDeclararRespuesta,
    RendimientosPorDeclararRespuesta,
    decimal_desde_texto,
)
from api.esquemas_informe import informe_a_respuesta
from api.esquemas_ola2 import (
    AvisoRespuesta,
    DescarteRespuesta,
    PresupuestoConProyectoRespuesta,
    RevaloracionRespuesta,
)
from api.rutas.listas import _elegidos, comprobar_libro_legible
from api.rutas.rendimientos import propuesta_respuesta
from api.sesion_web import exigir_clave_o_sesion
from aplicacion import actualizacion as aplicacion_actualizacion
from core import models
from core.budget import (
    Comparativo,
    DetectorAtipicos,
    GeneradorPlan,
    PeriodoPlan,
    actualizar_precios,
    cargar_elaboracion,
    cargar_presupuesto,
    comparar_por_partida,
    crear_proyecto,
    elaborar,
    exportar_excel,
    generar_escenario,
    guardar_presupuesto,
    hallazgos_externos,
    importar_presupuesto,
    plan_secuencial,
)
from core.budget.instantanea import composiciones_de_presupuesto
from core.catalog import Catalogo, CatalogoIncompleto, insumos_desconocidos, proponer_rendimiento
from core.contracts import Dominio, ItemComputo, OrigenTipo, ParametrosCosto
from core.contracts.apu import TipoRendimiento
from core.contracts.presupuesto import Presupuesto
from core.verification.informe import DECIMALES_PRESENTACION, InformeAuditoria
from core.verification.texto import formatear_decimal
from ml.normalization import propuestas_para
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

router = APIRouter(tags=["presupuestos"])

#: Una sola dependencia de edicion, compartida por las rutas que ademas necesitan a la persona
#: (FastAPI la ejecuta una vez por peticion): su `usuario` firma lo que se guarda (RF-82).
_QUIEN_EDITA = exigir_clave_o_sesion(Accion.EDITAR_HOJA)

_CAMPOS_PARAMETROS = ("fcas", "bono_alimentacion", "administracion", "utilidad")


@router.post(
    "/proyectos",
    response_model=ProyectoRespuesta,
    status_code=status.HTTP_201_CREATED,
    dependencies=EDITAR,
)
def crear_proyecto_de_presupuestos(
    sesion: SesionDep, peticion: ProyectoPeticion
) -> ProyectoRespuesta:
    """UC-01, paso 1 (INV-086): crea el proyecto sobre el que luego se elabora
    (`POST /presupuestos`) o se importa (`POST /presupuestos/importar`) y confirma la transaccion.

    La validacion es de `core.budget.crear_proyecto`: un nombre vacio o repetido, o un dominio que
    no es de `Dominio`, es 422 sin crear nada. La interfaz no crea proyectos; por HTTP, solo esta
    ruta (los scripts de siembra de `scripts/` tambien los crean, directamente en la base).
    """
    proyecto = crear_proyecto(sesion, peticion.nombre, peticion.descripcion, peticion.dominio)
    sesion.commit()
    return ProyectoRespuesta.model_validate(proyecto)


@router.post(
    "/presupuestos",
    response_model=PresupuestoCreadoRespuesta,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "model": RendimientosPorDeclararRespuesta,
            "description": "Falta un dato vigente del catálogo; si es un rendimiento estimado, "
            "la respuesta propone el del histórico (UC-01, flujo 3b)",
        }
    },
    dependencies=EDITAR,
)
def crear_presupuesto(
    sesion: SesionDep, peticion: PresupuestoPeticion
) -> PresupuestoCreadoRespuesta | JSONResponse:
    """Elabora el presupuesto (UC-01), lo audita siempre (UC-05) y lo guarda; los ítems sin
    partida quedan pendientes (flujo 3a).

    Flujo 3b (INV-088): si una partida no tiene rendimiento estimado vigente a la fecha, responde
    409 sin guardar nada, con el rendimiento que propone el histórico y su dispersión por partida.
    El tipo se declara al registrarlo con `POST /partidas/{codigo}/rendimientos`, y el presupuesto
    se vuelve a enviar: la elaboración usa el rendimiento **estimado** vigente, así que un medido
    registrado no la desbloquea."""
    proyecto = _proyecto(sesion, peticion.proyecto)

    items = [_a_item_computo(item) for item in peticion.items]
    catalogo = Catalogo(sesion)
    # UC-01, flujo 3a (INV-072): solo se piden composiciones de las partidas que existen; las
    # demás las deja pendientes `elaborar`, en vez de abortar con el KeyError del catálogo (404).
    descripciones = {partida.codigo: partida.descripcion for partida in catalogo.partidas()}
    codigos = dict.fromkeys(
        item.codigo_partida for item in items if item.codigo_partida in descripciones
    )
    try:
        composiciones = catalogo.composiciones(codigos, fecha=peticion.fecha)
    except CatalogoIncompleto:
        por_declarar = _rendimientos_por_declarar(sesion, catalogo, codigos, peticion.fecha)
        if not por_declarar:
            raise  # falta otra cosa (un precio de la lista vigente): el 409 de siempre
        sin_estimado = ", ".join(entrada.codigo_partida for entrada in por_declarar)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=RendimientosPorDeclararRespuesta(
                detalle=(
                    f"sin rendimiento estimado vigente al {peticion.fecha}: {sin_estimado}; "
                    "declare el rendimiento propuesto con POST "
                    "/partidas/{codigo}/rendimientos (tipo 'estimado', fecha no posterior a la "
                    "del presupuesto) y vuelva a enviar el presupuesto"
                ),
                rendimientos_por_declarar=por_declarar,
            ).model_dump(mode="json"),
        )
    parametros = _parametros_costo(peticion)

    resultado = elaborar(
        items,
        composiciones,
        parametros,
        peticion.codigo,
        peticion.fecha,
        peticion.moneda,
        plan=_plan(peticion.plan),
    )
    guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=catalogo.lista_vigente(peticion.fecha),
        parametros=parametros,
        pendientes=resultado.pendientes,
        usuario=USUARIO_SIN_CLAVE,
    )
    sesion.commit()

    return PresupuestoCreadoRespuesta(
        codigo=resultado.presupuesto.codigo,
        total=formatear_decimal(resultado.presupuesto.total, DECIMALES_PRESENTACION),
        hallazgos=len(resultado.informe.hallazgos),
        pendientes=_pendientes(descripciones, resultado.pendientes),
    )


@router.post(
    "/presupuestos/importar",
    response_model=PresupuestoCreadoRespuesta,
    status_code=status.HTTP_201_CREATED,
    dependencies=EDITAR,
)
def importar_presupuesto_de_tercero(
    sesion: SesionDep,
    archivo: Annotated[
        UploadFile,
        File(
            description="El presupuesto del tercero en un libro XLSX con las hojas Datos, "
            "Presupuesto, APU, Insumos y, opcional, Curva (formato de core.budget.importacion)"
        ),
    ],
    proyecto: Annotated[str, Form(description="Proyecto existente donde se guarda")],
) -> PresupuestoCreadoRespuesta:
    """RF-24 y UC-05, pasos 1 y 2 (INV-076): importa el presupuesto tabular de un tercero, lo
    audita siempre y lo guarda con su informe, que luego sirven `GET /presupuestos/{codigo}/informe`
    y `GET /presupuestos/{codigo}/excel`.

    La lectura, la auditoría y la persistencia son de `core.budget.importar_presupuesto`. Un
    proyecto inexistente es 404. Un archivo que no es XLSX o está mal formado (con archivo, hoja y
    fila), un código de partida que ya está en el catálogo, un código de presupuesto repetido en el
    proyecto o una moneda distinta de la de la lista vigente a su fecha son 422, sin escribir nada.
    El presupuesto del tercero no tiene ítems pendientes: todo renglón trae su APU. Se declara
    antes de las rutas con `{codigo}` para que `importar` no se lea como un código.
    """
    destino = _proyecto(sesion, proyecto)
    with tempfile.TemporaryDirectory() as directorio:
        ruta = guardar_subida(directorio, archivo)
        comprobar_libro_legible(ruta)
        try:
            resultado = importar_presupuesto(sesion, ruta, destino, usuario=USUARIO_SIN_CLAVE)
        except ValueError:
            sesion.rollback()
            raise
    sesion.commit()

    return PresupuestoCreadoRespuesta(
        codigo=resultado.presupuesto.codigo,
        total=formatear_decimal(resultado.presupuesto.total, DECIMALES_PRESENTACION),
        hallazgos=len(resultado.informe.hallazgos),
        pendientes=[],
    )


@router.get(
    "/presupuestos", response_model=list[PresupuestoConProyectoRespuesta], dependencies=LEER
)
def listar_presupuestos(sesion: SesionDep) -> list[PresupuestoConProyectoRespuesta]:
    """Códigos, totales y proyecto de todos los presupuestos guardados, ordenados por código."""
    catalogo = Catalogo(sesion)
    resumenes: list[PresupuestoConProyectoRespuesta] = []
    consulta = select(models.Presupuesto).order_by(models.Presupuesto.codigo)
    for modelo in sesion.scalars(consulta):
        presupuesto = cargar_presupuesto(sesion, modelo.proyecto.nombre, modelo.codigo, catalogo)
        resumenes.append(
            PresupuestoConProyectoRespuesta(
                codigo=presupuesto.codigo,
                total=formatear_decimal(presupuesto.total, DECIMALES_PRESENTACION),
                proyecto=modelo.proyecto.nombre,
            )
        )
    return resumenes


@router.get("/presupuestos/{codigo}", response_model=PresupuestoDetalleRespuesta, dependencies=LEER)
def obtener_presupuesto(
    sesion: SesionDep, codigo: str, proyecto: str | None = None
) -> PresupuestoDetalleRespuesta:
    """El presupuesto reconstruido desde el catálogo (`cargar_presupuesto`), con sus renglones.

    `codigo` es único solo por proyecto: si dos proyectos comparten código, indique `proyecto`
    para desambiguar (`_buscar_modelo` responde 409 en vez de una ambigüedad silenciosa).
    """
    presupuesto, _ = _cargar(sesion, codigo, proyecto)
    return PresupuestoDetalleRespuesta(
        codigo=presupuesto.codigo,
        fecha=presupuesto.fecha,
        moneda=presupuesto.moneda,
        total=formatear_decimal(presupuesto.total, DECIMALES_PRESENTACION),
        partidas=[
            PartidaPresupuestadaRespuesta(
                codigo_partida=partida.item.codigo_partida,
                descripcion=partida.item.descripcion,
                unidad=partida.item.unidad,
                cantidad=formatear_decimal(partida.item.cantidad, DECIMALES_PRESENTACION),
                precio_unitario=formatear_decimal(
                    partida.resultado.precio_unitario, DECIMALES_PRESENTACION
                ),
                total=formatear_decimal(partida.total, DECIMALES_PRESENTACION),
            )
            for partida in presupuesto.partidas
        ],
    )


@router.get("/presupuestos/{codigo}/informe", dependencies=LEER)
def informe_de_auditoria(
    sesion: SesionDep, codigo: str, proyecto: str | None = None
) -> PlainTextResponse:
    """El informe de auditoría en markdown (UC-05): se genera siempre, con la misma llamada que
    usa `ui/app.py` (`InformeAuditoria.a_markdown()`), nunca reinventada aquí.
    """
    _, informe = _cargar(sesion, codigo, proyecto)
    return PlainTextResponse(informe.a_markdown(), media_type="text/markdown")


@router.get("/presupuestos/{codigo}/excel", dependencies=LEER)
def exportar_presupuesto_excel(
    sesion: SesionDep, codigo: str, proyecto: str | None = None
) -> FileResponse:
    """El presupuesto, su APU, su curva y su auditoría como libro de Excel descargable."""
    presupuesto, informe = _cargar(sesion, codigo, proyecto)
    descriptor, ruta_texto = tempfile.mkstemp(suffix=".xlsx")
    os.close(descriptor)  # exportar_excel abre la ruta por su cuenta (openpyxl.Workbook.save)
    ruta = exportar_excel(presupuesto, informe, Path(ruta_texto))
    return FileResponse(
        ruta,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"presupuesto_{presupuesto.codigo}.xlsx",
        background=BackgroundTask(ruta.unlink),
    )


@router.post(
    "/presupuestos/{codigo}/actualizacion", response_model=ComparativoRespuesta, dependencies=EDITAR
)
def actualizar_presupuesto(
    sesion: SesionDep,
    codigo: str,
    peticion: ActualizacionPeticion,
    proyecto: str | None = None,
) -> ComparativoRespuesta:
    """UC-02: revalora el presupuesto con `peticion.lista` y guarda la versión `codigo_nuevo`.

    Mismo criterio que `ui/app.py`: si ningún insumo cambió de precio
    (`comparativo.insumos_afectados == 0`) no hay nada que confirmar (409, sin `commit`).

    UC-07, paso 5 (INV-099): pasa al núcleo el detector de precios atípicos de `ml.anomaly`
    (`_detector_de_atipicos`); los que marque entran como hallazgos `ATIPICO` en el informe de la
    versión nueva, que sirve `GET /presupuestos/{codigo_nuevo}/informe`. Sin el extra `ml`, o con
    menos variaciones de las que el detector necesita, no hay atípicos que declarar.
    """
    modelo = _buscar_modelo(sesion, codigo, proyecto)
    lista_nueva = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == peticion.lista)
    ).one_or_none()
    if lista_nueva is None:
        raise LookupError(f"no hay ninguna lista de precios {peticion.lista!r}")

    _nuevo, comparativo = actualizar_precios(
        sesion,
        modelo.proyecto.nombre,
        codigo,
        lista_nueva,
        peticion.codigo_nuevo,
        detectar_atipicos=_detector_de_atipicos(),
        usuario=USUARIO_SIN_CLAVE,
    )
    if comparativo.insumos_afectados == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ningún insumo cambió de precio entre la lista anterior y la nueva: no hay "
            "nada que confirmar (UC-02, flujo 3a)",
        )
    sesion.commit()

    return ComparativoRespuesta(
        total_anterior=formatear_decimal(comparativo.total_anterior, DECIMALES_PRESENTACION),
        total_nuevo=formatear_decimal(comparativo.total_nuevo, DECIMALES_PRESENTACION),
        insumos_afectados=comparativo.insumos_afectados,
        filas=_filas_comparativo(comparativo),
    )


@router.post(
    "/presupuestos/revalorar",
    response_model=RevaloracionRespuesta,
    dependencies=[Depends(_QUIEN_EDITA)],  # antes que `sesion_api`: sin permiso no se abre el caso
)
def revalorar_presupuesto(
    sesion: SesionDep,
    quien: Annotated[SesionActiva | None, Depends(_QUIEN_EDITA)],
    archivo: Annotated[UploadFile, File(description="La lista de precios nueva, CSV o XLSX")],
    proyecto: Annotated[str, Form()],
    codigo: Annotated[str, Form(description="Código del presupuesto base")],
    codigo_nuevo: Annotated[str, Form(description="Código de la versión nueva")],
    nombre: Annotated[str, Form(description="Nombre de la lista nueva")],
    moneda: Annotated[str, Form()],
    fecha_vigencia: Annotated[date, Form()],
    dar_de_alta: Annotated[
        list[str] | None,
        Form(description="Descripciones de los insumos desconocidos que se dan de alta (2a)"),
    ] = None,
) -> RevaloracionRespuesta:
    """UC-02 de una vez, como la página de Streamlit: crea la lista desde el archivo, revalora el
    presupuesto `codigo` y guarda la versión `codigo_nuevo` si algún insumo cambió de precio.

    Sin cambios de precio (flujo 3a) no se guarda nada, ni la lista ni las altas, y la respuesta lo
    dice en `avisos` con `version_guardada: null`. Un código nuevo repetido es 409. La versión
    guardada se puede descartar con `POST /presupuestos/{codigo}/descartar` (flujo 7a).
    """
    with tempfile.TemporaryDirectory() as directorio:
        ruta = guardar_subida(directorio, archivo)
        comprobar_libro_legible(ruta)
        elegidos = _elegidos(insumos_desconocidos(sesion, ruta), dar_de_alta or (), ruta.name)
        try:
            resultado = aplicacion_actualizacion.revalorar(
                sesion,
                {
                    "proyecto": proyecto,
                    "codigo": codigo,
                    "codigo_nuevo": codigo_nuevo,
                    "nombre": nombre,
                    "moneda": moneda,
                    "vigencia": fecha_vigencia,
                },
                ruta,
                dar_de_alta=elegidos,
                detector=_detector_de_atipicos(),
                usuario=USUARIO_SIN_CLAVE if quien is None else quien.usuario,
            )
        except SQLAlchemyError as error:
            sesion.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(getattr(error, "orig", error))
            ) from error
    comparativo = resultado.comparativo
    return RevaloracionRespuesta(
        proyecto=proyecto,
        codigo_base=codigo,
        codigo_nuevo=codigo_nuevo,
        moneda=resultado.nuevo.presupuesto.moneda,
        total_anterior=formatear_decimal(comparativo.total_anterior, DECIMALES_PRESENTACION),
        total_nuevo=formatear_decimal(comparativo.total_nuevo, DECIMALES_PRESENTACION),
        variacion=formatear_decimal(comparativo.variacion, DECIMALES_PRESENTACION),
        variacion_pct=formatear_decimal(comparativo.variacion_pct, DECIMALES_PRESENTACION),
        resumen=resultado.resumen,
        insumos_afectados=comparativo.insumos_afectados,
        filas=_filas_comparativo(comparativo),
        dados_de_alta=list(resultado.dados_de_alta),
        ignorados=list(resultado.ignorados),
        rechazados=list(resultado.rechazados),
        version_guardada=resultado.version_guardada,
        avisos=[AvisoRespuesta(nivel=a.nivel, texto=a.texto) for a in resultado.avisos],
        informe=informe_a_respuesta(resultado.nuevo.informe),
    )


@router.post(
    "/presupuestos/{codigo}/descartar", response_model=DescarteRespuesta, dependencies=EDITAR
)
def descartar_version_revalorada(
    sesion: SesionDep, codigo: str, proyecto: str | None = None
) -> DescarteRespuesta:
    """UC-02, flujo 7a: marca como descartada la última versión revalorada del proyecto.

    La versión sigue guardada como documento y su historial de cambios se conserva. Solo la última
    versión del proyecto, y una sola vez; en otro caso 422 con el motivo del núcleo.
    """
    modelo = _buscar_modelo(sesion, codigo, proyecto)
    hoy = date.today()
    aplicacion_actualizacion.descartar(sesion, modelo.proyecto.nombre, codigo, hoy)
    return DescarteRespuesta(codigo=codigo, descartada=True, fecha=hoy)


@router.post(
    "/presupuestos/{codigo}/escenarios", response_model=EscenariosRespuesta, dependencies=EDITAR
)
def escenarios_de_presupuesto(
    sesion: SesionDep,
    codigo: str,
    peticion: EscenariosPeticion,
    proyecto: str | None = None,
) -> EscenariosRespuesta:
    """UC-08: recalcula el presupuesto bajo los supuestos de cada escenario, sin persistir nada.

    Los parámetros que un escenario no declara heredan los congelados en el presupuesto base;
    un parámetro fuera de rango lo rechaza el contrato (`ParametrosCosto`) y responde 422
    (flujo 1a). La sesión no confirma nada: el base queda como única versión guardada (RF-30).

    Los ítems pendientes del base (sin partida en el catálogo, UC-01 flujo 3a) no se recalculan en
    ningún escenario ni suman a ningún total: la respuesta los lista en `pendientes_base`, con la
    misma forma que los pendientes de `POST /presupuestos` pero sin propuestas. Los hallazgos de
    cada escenario no los cuentan.
    """
    # INV-083: el base se lee con `cargar_elaboracion`, no con `cargar_presupuesto`, porque el
    # contrato `Presupuesto` no lleva los pendientes y `generar_escenario` solo recalcula los
    # renglones valorados (lo mismo hace la página de escenarios). El informe propio de cada
    # escenario no los declara: ruling C4‑3 (limitaciones), sin cambio de `core/` en C4.
    modelo = _buscar_modelo(sesion, codigo, proyecto)
    catalogo = Catalogo(sesion)
    elaboracion = cargar_elaboracion(sesion, modelo.proyecto.nombre, codigo, catalogo)
    base = elaboracion.presupuesto
    # SF3: las composiciones son las de la instantanea de la version (la hoja las edita ahi); los
    # hallazgos de reglas externas (R8 a R10) se vuelven a declarar en cada escenario (SF-E1).
    composiciones = composiciones_de_presupuesto(sesion, modelo.proyecto.nombre, codigo, catalogo)
    externos = hallazgos_externos(elaboracion.informe)

    respuestas: list[EscenarioRespuesta] = []
    for datos in peticion.escenarios:
        precios = {
            descripcion: decimal_desde_texto(texto, f"precio de {descripcion}")
            for descripcion, texto in datos.precios.items()
        }
        escenario = generar_escenario(
            datos.nombre,
            base,
            composiciones,
            _parametros_escenario(modelo, datos),
            precios=precios,
            externos=externos,
        )
        comparativo = comparar_por_partida(base, escenario)
        respuestas.append(
            EscenarioRespuesta(
                nombre=escenario.nombre,
                total=formatear_decimal(escenario.presupuesto.total, DECIMALES_PRESENTACION),
                variacion=formatear_decimal(comparativo.variacion, DECIMALES_PRESENTACION),
                variacion_pct=formatear_decimal(comparativo.variacion_pct, DECIMALES_PRESENTACION),
                hallazgos=len(escenario.informe.hallazgos),
                insumos_variados=escenario.insumos_variados,
                partidas=_filas_comparativo(comparativo),
            )
        )
    return EscenariosRespuesta(
        codigo_base=base.codigo,
        total_base=formatear_decimal(base.total, DECIMALES_PRESENTACION),
        pendientes_base=[
            PendienteRespuesta(**_campos_pendiente(item)) for item in elaboracion.pendientes
        ],
        escenarios=respuestas,
    )


# ---------------------------------------------------------------------------------------------
# Ayudantes
# ---------------------------------------------------------------------------------------------


def _detector_de_atipicos() -> DetectorAtipicos | None:
    """`ml.anomaly.precios_atipicos` con import perezoso, o `None` sin el extra `ml` (el mismo
    criterio que `_veredicto_bosque` en `api/rutas/rendimientos.py`): `core/` recibe el detector
    como parámetro porque no importa `ml/` (expediente C6.5).

    El extra se reconoce por `scikit-learn`, no por `ml.anomaly`: ese paquete se importa solo con
    `numpy` y el detector importa `sklearn` al llamarlo, con 8 o más variaciones. Mirar solo la
    importación dejaba un 500 sin el extra (ronda 1 de la pista A, H3).
    """
    if importlib.util.find_spec("sklearn") is None:
        return None
    try:
        from ml.anomaly import precios_atipicos
    except ImportError:
        return None
    return precios_atipicos


def _proyecto(sesion: Session, nombre: str) -> models.Proyecto:
    """El proyecto de ese nombre; `LookupError` (404) si no existe (`POST /proyectos` lo crea)."""
    proyecto = sesion.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == nombre)
    ).one_or_none()
    if proyecto is None:
        raise LookupError(f"no hay ningún proyecto {nombre!r} en el catálogo")
    return proyecto


def _a_item_computo(item: ItemComputoPeticion) -> ItemComputo:
    return ItemComputo(
        codigo_partida=item.codigo_partida,
        descripcion=item.descripcion,
        unidad=item.unidad,
        cantidad=decimal_desde_texto(item.cantidad, f"cantidad de {item.codigo_partida}"),
        origen_id=item.origen_id,
        origen_tipo=OrigenTipo(item.origen_tipo),
        dominio=Dominio(item.dominio),
        regla=item.regla,
        parametros={
            clave: decimal_desde_texto(valor, f"parametro {clave} de {item.codigo_partida}")
            for clave, valor in item.parametros.items()
        },
        especificaciones=dict(item.especificaciones),
    )


def _pendientes(
    descripciones: Mapping[str, str], pendientes: Sequence[ItemComputo]
) -> list[ItemPendienteRespuesta]:
    """UC-01, flujo 3a: cada ítem sin partida con las partidas más similares del catálogo (UC-03).

    `descripciones` son las partidas del catálogo (código → descripción) que la ruta ya consultó
    para separar los pendientes: no se vuelven a pedir. La cantidad viaja exacta (como en
    `ItemComputoRespuesta`), no redondeada: quien acepta una propuesta vuelve a enviar este mismo
    ítem con el código elegido.

    El emparejamiento y el criterio de fallas son los de `ml.normalization.propuestas_para`
    (INV-081), el mismo que usa `ui/`: un solo normalizador por petición, y ninguno sin
    pendientes. Una falla declarada del modelo deja al ítem sin propuestas y la registra el
    registrador de `ml.normalization.normalizador`; cualquier otra se propaga.
    """
    return [
        ItemPendienteRespuesta(
            **_campos_pendiente(item),
            propuestas=[
                PropuestaPartidaRespuesta(
                    codigo=similar.codigo, descripcion=similar.descripcion, puntaje=similar.puntaje
                )
                for similar in propuesta.similares
            ],
        )
        for item, propuesta in propuestas_para(descripciones, pendientes)
    ]


def _campos_pendiente(item: ItemComputo) -> dict[str, str]:
    """Los campos de un ítem pendiente, los mismos en UC-01 y en UC-08 (`PendienteRespuesta`).
    La cantidad viaja exacta (`str` del `Decimal`), no redondeada."""
    return {
        "codigo_partida": item.codigo_partida,
        "descripcion": item.descripcion,
        "unidad": item.unidad,
        "cantidad": str(item.cantidad),
        "origen_id": item.origen_id,
    }


def _plan(
    periodos: Sequence[PeriodoPlanPeticion] | None,
) -> list[PeriodoPlan] | GeneradorPlan:
    """UC-01, paso 6 (INV-087): el plan de trabajo del proyectista, o `plan_secuencial` si no lo
    envía (el valor por defecto, que deja la línea base como estaba). Las fracciones se construyen
    desde su texto exacto; que cada partida sume 1 lo juzga `elaborar` (`PlanInvalido`, 422)."""
    if periodos is None:
        return plan_secuencial
    return [
        (
            periodo.periodo,
            tuple(
                (
                    codigo,
                    decimal_desde_texto(fraccion, f"fraccion de {codigo} en {periodo.periodo}"),
                )
                for codigo, fraccion in periodo.reparto.items()
            ),
        )
        for periodo in periodos
    ]


def _rendimientos_por_declarar(
    sesion: Session, catalogo: Catalogo, codigos: Sequence[str], fecha: date
) -> list[RendimientoPorDeclararRespuesta]:
    """UC-01, flujo 3b (INV-088): las partidas sin rendimiento estimado vigente a `fecha`, cada una
    con la propuesta de `proponer_rendimiento` (RF-26).

    Vigente es lo que `Catalogo.composicion` exige para reconstruir un APU: un rendimiento ESTIMADO
    de fecha no posterior a la del presupuesto; es el mismo criterio de
    `ui.elaboracion.rendimientos_por_declarar`, que la API no puede importar.

    `Catalogo.composiciones` resuelve la lista de precios antes que los rendimientos, asi que sin
    lista vigente a `fecha` el `CatalogoIncompleto` es de la lista, no de 3b: se relanza aqui
    (`Catalogo.lista_vigente`, 409 con solo `detalle`) antes de clasificar nada (U-1).
    """
    catalogo.lista_vigente(fecha)
    return [
        RendimientoPorDeclararRespuesta(
            codigo_partida=codigo,
            propuesta=propuesta_respuesta(proponer_rendimiento(sesion, codigo)),
        )
        for codigo in codigos
        if not any(
            rendimiento.tipo is TipoRendimiento.ESTIMADO and rendimiento.fecha <= fecha
            for rendimiento in catalogo.rendimientos(codigo)
        )
    ]


def _parametros_costo(peticion: PresupuestoPeticion) -> ParametrosCosto:
    """Los cuatro parámetros de costo; los que el cuerpo no trae quedan en su valor por defecto."""
    campos = {
        nombre: decimal_desde_texto(valor, nombre)
        for nombre in _CAMPOS_PARAMETROS
        if (valor := getattr(peticion, nombre)) is not None
    }
    return ParametrosCosto(**campos)


def _parametros_escenario(
    modelo: models.Presupuesto, escenario: EscenarioPeticion
) -> ParametrosCosto:
    """Los parámetros del escenario: los del presupuesto base con los del cuerpo por encima.

    A diferencia de `_parametros_costo`, lo omitido hereda del **base** (los valores congelados
    en su fila), no del contrato: el escenario varía lo que el presupuesto realmente usa.
    """
    campos = {nombre: getattr(modelo, nombre) for nombre in _CAMPOS_PARAMETROS}
    for nombre in _CAMPOS_PARAMETROS:
        texto = getattr(escenario, nombre)
        if texto is not None:
            campos[nombre] = decimal_desde_texto(texto, nombre)
    return ParametrosCosto(**campos)


def _filas_comparativo(comparativo: Comparativo) -> list[FilaComparativoRespuesta]:
    """Las filas de un `Comparativo` presentadas a dos decimales (UC-02 y UC-08 por igual)."""
    return [
        FilaComparativoRespuesta(
            codigo_partida=fila.codigo_partida,
            descripcion=fila.descripcion,
            cantidad=formatear_decimal(fila.cantidad, DECIMALES_PRESENTACION),
            pu_anterior=formatear_decimal(fila.pu_anterior, DECIMALES_PRESENTACION),
            pu_nuevo=formatear_decimal(fila.pu_nuevo, DECIMALES_PRESENTACION),
            variacion_pct=formatear_decimal(fila.variacion_pct, DECIMALES_PRESENTACION),
            total_anterior=formatear_decimal(fila.total_anterior, DECIMALES_PRESENTACION),
            total_nuevo=formatear_decimal(fila.total_nuevo, DECIMALES_PRESENTACION),
            incidencia_pct=formatear_decimal(fila.incidencia_pct, DECIMALES_PRESENTACION),
        )
        for fila in comparativo.tabla.itertuples(index=False)
    ]


def _buscar_modelo(sesion: Session, codigo: str, proyecto: str | None = None) -> models.Presupuesto:
    """El renglón de `models.Presupuesto` de ese código, acotado por proyecto si se indica.

    `codigo` solo es único **por proyecto** (`UniqueConstraint(proyecto_id, codigo)` en
    `core.models.entidades.Presupuesto`, el mismo criterio con que `cargar_presupuesto` exige
    `proyecto_nombre`): sin `proyecto`, dos proyectos con el mismo código son ambiguos y se
    declaran con un 409 explícito en vez de dejar que `MultipleResultsFound` llegue sin manejador
    registrado en `api/main.py` (hallazgo de la revisión de la Tarea 2). Ninguna coincidencia sigue
    siendo `LookupError` (404), como antes.
    """
    consulta = select(models.Presupuesto).where(models.Presupuesto.codigo == codigo)
    if proyecto is not None:
        consulta = consulta.join(models.Proyecto).where(models.Proyecto.nombre == proyecto)
    encontrados = list(sesion.scalars(consulta))

    if not encontrados:
        detalle = f"no hay ningún presupuesto con código {codigo!r}"
        if proyecto is not None:
            detalle += f" en el proyecto {proyecto!r}"
        raise LookupError(detalle)

    if len(encontrados) > 1:
        nombres = ", ".join(sorted({modelo.proyecto.nombre for modelo in encontrados}))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"el código {codigo!r} existe en más de un proyecto ({nombres}): "
                "indique 'proyecto' en la consulta para desambiguar"
            ),
        )

    return encontrados[0]


def _cargar(
    sesion: Session, codigo: str, proyecto: str | None = None
) -> tuple[Presupuesto, InformeAuditoria]:
    """El presupuesto reconstruido desde el catálogo y su informe de auditoría, recién evaluado.

    El informe es el del documento emitido (`cargar_elaboracion`): vuelve a declarar los ítems que
    quedaron pendientes al elaborar (UC-01 3a), así que `/informe` y `/excel` no pueden declarar
    CUMPLE un presupuesto emitido NO CUMPLE (INV-080).
    """
    modelo = _buscar_modelo(sesion, codigo, proyecto)
    elaboracion = cargar_elaboracion(sesion, modelo.proyecto.nombre, codigo, Catalogo(sesion))
    return elaboracion.presupuesto, elaboracion.informe
