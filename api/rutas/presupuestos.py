"""Rutas de presupuestos por HTTP: elaborar, consultar, exportar y actualizar precios.

UC-01 (`POST /presupuestos`, a partir de `ItemComputo` ya extraídos; un ítem sin partida queda
pendiente y se lista con sus partidas similares, flujo 3a), UC-05 (el informe de auditoría, que se
genera siempre) y UC-02 (`POST /presupuestos/{codigo}/actualizacion`). Los montos se presentan
siempre con dos decimales (`core.verification.informe.DECIMALES_PRESENTACION`), la misma cifra que
usa `ui/app.py` y la exportación a Excel: esta capa no inventa su propio redondeo.
"""

from __future__ import annotations

import logging
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from api.dependencias import SesionDep
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
    PresupuestoCreadoRespuesta,
    PresupuestoDetalleRespuesta,
    PresupuestoPeticion,
    PresupuestoResumenRespuesta,
    PropuestaPartidaRespuesta,
    decimal_desde_texto,
)
from core import models
from core.budget import (
    Comparativo,
    actualizar_precios,
    cargar_elaboracion,
    cargar_presupuesto,
    comparar_por_partida,
    elaborar,
    exportar_excel,
    generar_escenario,
    guardar_presupuesto,
    plan_secuencial,
)
from core.catalog import Catalogo
from core.contracts import Dominio, ItemComputo, OrigenTipo, ParametrosCosto
from core.contracts.presupuesto import Presupuesto
from core.verification.informe import DECIMALES_PRESENTACION, InformeAuditoria
from core.verification.texto import formatear_decimal

if TYPE_CHECKING:
    from ml.normalization import PartidaSimilar

router = APIRouter(tags=["presupuestos"])
_registro = logging.getLogger(__name__)

_CAMPOS_PARAMETROS = ("fcas", "bono_alimentacion", "administracion", "utilidad")
# Fallas de UC-03 que dejan un ítem pendiente sin propuestas en vez de responder 500 o 422
# (`_proponedor`): extra `ml` ausente, modelo ausente, identificador inválido, pesos corruptos.
_FALLAS_DE_LA_PROPUESTA = (ImportError, OSError, ValueError, RuntimeError)


@router.post(
    "/presupuestos",
    response_model=PresupuestoCreadoRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def crear_presupuesto(
    sesion: SesionDep, peticion: PresupuestoPeticion
) -> PresupuestoCreadoRespuesta:
    """Elabora el presupuesto (UC-01), lo audita siempre (UC-05) y lo guarda; los ítems sin
    partida quedan pendientes (flujo 3a)."""
    proyecto = sesion.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == peticion.proyecto)
    ).one_or_none()
    if proyecto is None:
        raise LookupError(f"no hay ningún proyecto {peticion.proyecto!r} en el catálogo")

    items = [_a_item_computo(item) for item in peticion.items]
    catalogo = Catalogo(sesion)
    # UC-01, flujo 3a (INV-072): solo se piden composiciones de las partidas que existen; las
    # demás las deja pendientes `elaborar`, en vez de abortar con el KeyError del catálogo (404).
    descripciones = {partida.codigo: partida.descripcion for partida in catalogo.partidas()}
    composiciones = catalogo.composiciones(
        dict.fromkeys(
            item.codigo_partida for item in items if item.codigo_partida in descripciones
        ),
        fecha=peticion.fecha,
    )
    parametros = _parametros_costo(peticion)

    resultado = elaborar(
        items,
        composiciones,
        parametros,
        peticion.codigo,
        peticion.fecha,
        peticion.moneda,
        plan=plan_secuencial,
    )
    guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=catalogo.lista_vigente(peticion.fecha),
        parametros=parametros,
        pendientes=resultado.pendientes,
    )
    sesion.commit()

    return PresupuestoCreadoRespuesta(
        codigo=resultado.presupuesto.codigo,
        total=formatear_decimal(resultado.presupuesto.total, DECIMALES_PRESENTACION),
        hallazgos=len(resultado.informe.hallazgos),
        pendientes=_pendientes(descripciones, resultado.pendientes),
    )


@router.get("/presupuestos", response_model=list[PresupuestoResumenRespuesta])
def listar_presupuestos(sesion: SesionDep) -> list[PresupuestoResumenRespuesta]:
    """Códigos y totales de todos los presupuestos guardados, ordenados por código."""
    catalogo = Catalogo(sesion)
    resumenes: list[PresupuestoResumenRespuesta] = []
    consulta = select(models.Presupuesto).order_by(models.Presupuesto.codigo)
    for modelo in sesion.scalars(consulta):
        presupuesto = cargar_presupuesto(sesion, modelo.proyecto.nombre, modelo.codigo, catalogo)
        resumenes.append(
            PresupuestoResumenRespuesta(
                codigo=presupuesto.codigo,
                total=formatear_decimal(presupuesto.total, DECIMALES_PRESENTACION),
            )
        )
    return resumenes


@router.get("/presupuestos/{codigo}", response_model=PresupuestoDetalleRespuesta)
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


@router.get("/presupuestos/{codigo}/informe")
def informe_de_auditoria(
    sesion: SesionDep, codigo: str, proyecto: str | None = None
) -> PlainTextResponse:
    """El informe de auditoría en markdown (UC-05): se genera siempre, con la misma llamada que
    usa `ui/app.py` (`InformeAuditoria.a_markdown()`), nunca reinventada aquí.
    """
    _, informe = _cargar(sesion, codigo, proyecto)
    return PlainTextResponse(informe.a_markdown(), media_type="text/markdown")


@router.get("/presupuestos/{codigo}/excel")
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


@router.post("/presupuestos/{codigo}/actualizacion", response_model=ComparativoRespuesta)
def actualizar_presupuesto(
    sesion: SesionDep,
    codigo: str,
    peticion: ActualizacionPeticion,
    proyecto: str | None = None,
) -> ComparativoRespuesta:
    """UC-02: revalora el presupuesto con `peticion.lista` y guarda la versión `codigo_nuevo`.

    Mismo criterio que `ui/app.py`: si ningún insumo cambió de precio
    (`comparativo.insumos_afectados == 0`) no hay nada que confirmar (409, sin `commit`).
    """
    modelo = _buscar_modelo(sesion, codigo, proyecto)
    lista_nueva = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == peticion.lista)
    ).one_or_none()
    if lista_nueva is None:
        raise LookupError(f"no hay ninguna lista de precios {peticion.lista!r}")

    _nuevo, comparativo = actualizar_precios(
        sesion, modelo.proyecto.nombre, codigo, lista_nueva, peticion.codigo_nuevo
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


@router.post("/presupuestos/{codigo}/escenarios", response_model=EscenariosRespuesta)
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
    """
    modelo = _buscar_modelo(sesion, codigo, proyecto)
    catalogo = Catalogo(sesion)
    base = cargar_presupuesto(sesion, modelo.proyecto.nombre, codigo, catalogo)
    composiciones = {
        codigo_partida: catalogo.composicion(
            codigo_partida, fecha=modelo.fecha, lista=modelo.lista_precios
        )
        for codigo_partida in dict.fromkeys(
            partida.item.codigo_partida for partida in base.partidas
        )
    }

    respuestas: list[EscenarioRespuesta] = []
    for datos in peticion.escenarios:
        precios = {
            descripcion: decimal_desde_texto(texto, f"precio de {descripcion}")
            for descripcion, texto in datos.precios.items()
        }
        escenario = generar_escenario(
            datos.nombre, base, composiciones, _parametros_escenario(modelo, datos), precios=precios
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
        escenarios=respuestas,
    )


# ---------------------------------------------------------------------------------------------
# Ayudantes
# ---------------------------------------------------------------------------------------------


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
    """
    if not pendientes:
        return []
    proponer = _proponedor(descripciones)
    return [
        ItemPendienteRespuesta(
            codigo_partida=item.codigo_partida,
            descripcion=item.descripcion,
            unidad=item.unidad,
            cantidad=str(item.cantidad),
            origen_id=item.origen_id,
            propuestas=[
                PropuestaPartidaRespuesta(
                    codigo=similar.codigo, descripcion=similar.descripcion, puntaje=similar.puntaje
                )
                for similar in proponer(item.descripcion)
            ],
        )
        for item in pendientes
    ]


def _proponedor(descripciones: Mapping[str, str]) -> Callable[[str], Sequence[PartidaSimilar]]:
    """`similares` del normalizador de UC-03 sobre el catálogo, o una propuesta vacía.

    La propuesta es una ayuda, no una condición: sin el extra `ml`, o sin el modelo de similitud en
    la caché local (precondición de UC-03, `docs/ERS.md`), el ítem queda pendiente y el informe lo
    declara igual. Ante la falta del extra es el criterio de `rutas/rendimientos._veredicto_bosque`
    (que solo atrapa `ImportError`); aquí se atrapan además `OSError` (modelo ausente, sin red) y
    `ValueError` (`HFValidationError` de Hugging Face es su subclase), que de otro modo llegarían
    como 500 o 422 después de guardar el presupuesto, y `RuntimeError` (un archivo de pesos
    corrupto hace fallar `torch.load`). Las mismas fallas se atrapan en la construcción del
    normalizador y en cada llamada a `similares`: la que falla deja sin propuestas solo a su ítem,
    y se registra con `logging.warning` y su tipo, para que un fallo del modelo no pase por un
    simple «sin propuestas». Solo se construye si hay pendientes: cargar el modelo cuesta segundos
    dentro de la petición, y la primera vez puede descargarlo.
    """
    try:
        from ml.normalization import NormalizadorPartidas

        normalizador = NormalizadorPartidas(dict(descripciones))
    except _FALLAS_DE_LA_PROPUESTA as error:
        _registro.warning(
            "UC-03 sin propuestas: el normalizador no se pudo construir (%s: %s)",
            type(error).__name__,
            error,
        )
        return lambda _descripcion: []

    def proponer(descripcion: str) -> Sequence[PartidaSimilar]:
        try:
            return normalizador.similares(descripcion)
        except _FALLAS_DE_LA_PROPUESTA as error:
            _registro.warning(
                "UC-03 sin propuestas para %r: similares fallo (%s: %s)",
                descripcion,
                type(error).__name__,
                error,
            )
            return []

    return proponer


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
