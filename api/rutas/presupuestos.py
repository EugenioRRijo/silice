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

import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.background import BackgroundTask

from api.acceso import EDITAR, LEER
from api.archivos import guardar_subida
from api.dependencias import USUARIO_SIN_CLAVE, SesionDeEscrituraDep, SesionDep
from api.esquemas import (
    ActualizacionPeticion,
    ComparativoRespuesta,
    PartidaPresupuestadaRespuesta,
    PresupuestoCreadoRespuesta,
    PresupuestoDetalleRespuesta,
    PresupuestoPeticion,
    ProyectoPeticion,
    ProyectoRespuesta,
    RendimientoPorDeclararRespuesta,
    RendimientosPorDeclararRespuesta,
    impuestos_a_respuesta,
)
from api.esquemas_informe import informe_a_respuesta
from api.esquemas_ola2 import (
    AvisoRespuesta,
    DescarteRespuesta,
    PresupuestoConProyectoRespuesta,
    RevaloracionRespuesta,
    exigir_codigo,
)
from api.rutas.listas import _elegidos, comprobar_libro_legible
from api.rutas.presupuestos_ayudas import (
    _QUIEN_EDITA,
    MAX_PENDIENTES_CON_PROPUESTAS,
    _a_item_computo,
    _buscar_modelo,
    _cargar,
    _detector_de_atipicos,
    _filas_comparativo,
    _parametros_costo,
    _pendientes,
    _plan,
    _proyecto,
)
from api.rutas.presupuestos_calculo import (
    calcular_presupuesto,
    calcular_presupuesto_excel,
    declarar_rendimiento_propuesto,
)
from api.rutas.presupuestos_escenarios import (
    base_de_escenarios,
    escenarios_de_presupuesto,
    escenarios_en_csv,
)
from api.rutas.rendimientos import propuesta_respuesta
from aplicacion import actualizacion as aplicacion_actualizacion
from aplicacion import elaboracion as aplicacion_elaboracion
from aplicacion.impuestos import con_iva
from aplicacion.listas_para_armar import lista_por_nombre
from core.budget import (
    actualizar_precios,
    cargar_presupuesto,
    crear_proyecto,
    elaborar,
    exportar_excel,
    guardar_presupuesto,
    importar_presupuesto,
)
from core.catalog import Catalogo, CatalogoIncompleto, insumos_desconocidos
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from seguridad.sesiones import SesionActiva

#: La fachada (tarea 4.1): el calculo de ensayo vive en `presupuestos_calculo`, los escenarios
#: en `presupuestos_escenarios` y los ayudantes en `presupuestos_ayudas`; aqui se siguen
#: ofreciendo los nombres de siempre.
__all__ = [
    "MAX_PENDIENTES_CON_PROPUESTAS",
    "actualizar_presupuesto",
    "base_de_escenarios",
    "calcular_presupuesto",
    "calcular_presupuesto_excel",
    "crear_presupuesto",
    "crear_proyecto_de_presupuestos",
    "declarar_rendimiento_propuesto",
    "descartar_version_revalorada",
    "escenarios_de_presupuesto",
    "escenarios_en_csv",
    "exportar_presupuesto_excel",
    "importar_presupuesto_de_tercero",
    "informe_de_auditoria",
    "listar_presupuestos",
    "obtener_presupuesto",
    "revalorar_presupuesto",
    "router",
]

router = APIRouter(tags=["presupuestos"])


@router.post(
    "/proyectos",
    response_model=ProyectoRespuesta,
    status_code=status.HTTP_201_CREATED,
    dependencies=EDITAR,
)
def crear_proyecto_de_presupuestos(
    sesion: SesionDeEscrituraDep, peticion: ProyectoPeticion
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
    dependencies=[Depends(_QUIEN_EDITA)],  # antes que la sesión: sin permiso no se abre el caso
)
def crear_presupuesto(
    sesion: SesionDeEscrituraDep,
    peticion: PresupuestoPeticion,
    quien: Annotated[SesionActiva | None, Depends(_QUIEN_EDITA)],
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
        por_declarar = aplicacion_elaboracion.rendimientos_por_declarar(
            sesion, items, peticion.fecha
        )
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
                rendimientos_por_declarar=[
                    RendimientoPorDeclararRespuesta(
                        codigo_partida=entrada.codigo_partida,
                        propuesta=propuesta_respuesta(entrada.propuesta),
                    )
                    for entrada in por_declarar
                ],
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
        usuario=USUARIO_SIN_CLAVE if quien is None else quien.usuario,
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
    dependencies=[Depends(_QUIEN_EDITA)],  # antes que la sesión: sin permiso no se abre el caso
)
def importar_presupuesto_de_tercero(
    sesion: SesionDeEscrituraDep,
    quien: Annotated[SesionActiva | None, Depends(_QUIEN_EDITA)],
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
    El libro se inspecciona antes de la primera consulta (DS-32, DS-112): la sesión de escritura
    toma el bloqueo en ella y nadie debe esperar la lectura de hasta 20 MiB; por eso un archivo
    malo sobre una obra inexistente es 422, no 404. El presupuesto del tercero no tiene ítems
    pendientes: todo renglón trae su APU. Se declara antes de las rutas con `{codigo}` para que
    `importar` no se lea como un código.
    """
    with tempfile.TemporaryDirectory() as directorio:
        ruta = guardar_subida(directorio, archivo)
        comprobar_libro_legible(ruta)
        destino = _proyecto(sesion, proyecto)
        try:
            resultado = importar_presupuesto(
                sesion, ruta, destino, usuario=USUARIO_SIN_CLAVE if quien is None else quien.usuario
            )
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
    for modelo in aplicacion_elaboracion.presupuestos_guardados(sesion):
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
        impuestos=impuestos_a_respuesta(con_iva(presupuesto.total)),
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
    try:
        ruta = exportar_excel(presupuesto, informe, Path(ruta_texto))
    except BaseException:
        # Sin libro no hay respuesta ni `BackgroundTask` que borre el temporal: se borra aqui.
        Path(ruta_texto).unlink(missing_ok=True)
        raise
    return FileResponse(
        ruta,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"presupuesto_{presupuesto.codigo}.xlsx",
        background=BackgroundTask(ruta.unlink),
    )


@router.post(
    "/presupuestos/{codigo}/actualizacion",
    response_model=ComparativoRespuesta,
    dependencies=[Depends(_QUIEN_EDITA)],  # antes que la sesión: sin permiso no se abre el caso
)
def actualizar_presupuesto(
    sesion: SesionDeEscrituraDep,
    quien: Annotated[SesionActiva | None, Depends(_QUIEN_EDITA)],
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
    lista_nueva = lista_por_nombre(sesion, peticion.lista)
    if lista_nueva is None:
        raise LookupError(f"no hay ninguna lista de precios {peticion.lista!r}")

    _nuevo, comparativo = actualizar_precios(
        sesion,
        modelo.proyecto.nombre,
        codigo,
        lista_nueva,
        peticion.codigo_nuevo,
        detectar_atipicos=_detector_de_atipicos(),
        usuario=USUARIO_SIN_CLAVE if quien is None else quien.usuario,
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
    dependencies=[Depends(_QUIEN_EDITA)],  # antes que la sesión: sin permiso no se abre el caso
)
def revalorar_presupuesto(
    sesion: SesionDeEscrituraDep,
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
    exigir_codigo(codigo_nuevo, "codigo_nuevo")
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
            # El texto del error de base nombra tablas y columnas: no sale por la API.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "No se pudo guardar la version nueva: ya existe una version con ese codigo en "
                    "la obra o una lista de precios con ese nombre."
                    if isinstance(error, IntegrityError)
                    else "No se pudo guardar la version nueva por un conflicto en la base de datos."
                ),
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
    sesion: SesionDeEscrituraDep, codigo: str, proyecto: str | None = None
) -> DescarteRespuesta:
    """UC-02, flujo 7a: marca como descartada la última versión revalorada del proyecto.

    La versión sigue guardada como documento y su historial de cambios se conserva. Solo la última
    versión del proyecto, y una sola vez; en otro caso 422 con el motivo del núcleo.
    """
    modelo = _buscar_modelo(sesion, codigo, proyecto)
    hoy = date.today()
    aplicacion_actualizacion.descartar(sesion, modelo.proyecto.nombre, codigo, hoy)
    return DescarteRespuesta(codigo=codigo, descartada=True, fecha=hoy)
