"""Ayudantes de las rutas de presupuestos (`presupuestos`, `presupuestos_calculo` y
`presupuestos_escenarios`): la dependencia de edicion compartida, convertir lo que llega por
HTTP a los contratos del nucleo, buscar el presupuesto pedido y presentar sus renglones. No
declara rutas.

Salieron de `api/rutas/presupuestos.py` sin cambios (tarea 4.1 del plan de desenredo).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.dependencias import USUARIO_SIN_CLAVE
from api.esquemas import (
    EscenarioPeticion,
    EscenariosPeticion,
    FilaComparativoRespuesta,
    ItemComputoPeticion,
    ItemPendienteRespuesta,
    PartidaPresupuestadaRespuesta,
    PeriodoPlanPeticion,
    PresupuestoPeticion,
    PropuestaPartidaRespuesta,
    RendimientoPorDeclararRespuesta,
    RendimientosPorDeclararRespuesta,
    decimal_desde_texto,
)
from api.esquemas_ola2 import (
    MAX_ESCENARIOS,
    MAX_PRECIOS_POR_ESCENARIO,
    CalculoPeticion,
    PendienteConPropuestasRespuesta,
)
from api.rutas.rendimientos import propuesta_respuesta
from api.sesion_web import exigir_clave_o_sesion
from aplicacion import actualizacion as aplicacion_actualizacion
from aplicacion import elaboracion as aplicacion_elaboracion
from aplicacion.cifras import texto_de_cifra
from aplicacion.componer_parametros import NOMBRES as NOMBRES_DE_PARAMETROS
from aplicacion.formulas import neutralizar_formula
from aplicacion.listas_para_armar import SinListaParaArmar, lista_para_el_proyecto
from aplicacion.proyectos import proyecto_por_nombre, resolver_proyecto
from core.budget import (
    Comparativo,
    DetectorAtipicos,
    Escenario,
    GeneradorPlan,
    PeriodoPlan,
    ResultadoElaboracion,
    cargar_elaboracion,
    generar_escenario,
    hallazgos_externos,
    plan_secuencial,
)
from core.budget.instantanea import composiciones_de_presupuesto
from core.catalog import Catalogo, CatalogoIncompleto
from core.contracts import Dominio, ItemComputo, OrigenTipo, ParametrosCosto
from core.contracts.presupuesto import Presupuesto
from core.verification.informe import DECIMALES_PRESENTACION, InformeAuditoria
from core.verification.texto import formatear_decimal
from ml.normalization import propuestas_para
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

if TYPE_CHECKING:
    from core import models

#: Una sola dependencia de edicion, compartida por las rutas que ademas necesitan a la persona
#: (FastAPI la ejecuta una vez por peticion): su `usuario` firma lo que se guarda (RF-82).
_QUIEN_EDITA = exigir_clave_o_sesion(Accion.EDITAR_HOJA)

_CAMPOS_PARAMETROS = ("fcas", "bono_alimentacion", "administracion", "utilidad")


MAX_PENDIENTES_CON_PROPUESTAS = 50


def _pendientes_con_propuestas(
    descripciones: Mapping[str, str], pendientes: Sequence[ItemComputo]
) -> list[PendienteConPropuestasRespuesta]:
    """Los pendientes con sus partidas similares. El emparejamiento cuesta tiempo por item, asi que
    solo los primeros `MAX_PENDIENTES_CON_PROPUESTAS` lo piden; el resto se declara sin propuestas
    y con el motivo en `falla`."""
    con = aplicacion_elaboracion.propuestas_de_pendientes(
        descripciones, pendientes[:MAX_PENDIENTES_CON_PROPUESTAS]
    )
    respuestas = [
        PendienteConPropuestasRespuesta(
            **_campos_pendiente(entrada.item),
            propuestas=[
                PropuestaPartidaRespuesta(
                    codigo=similar.codigo, descripcion=similar.descripcion, puntaje=similar.puntaje
                )
                for similar in entrada.similares
            ],
            falla=entrada.falla,
        )
        for entrada in con
    ]
    respuestas.extend(
        PendienteConPropuestasRespuesta(
            **_campos_pendiente(item),
            propuestas=[],
            falla=(
                f"Sin propuestas: solo se calculan para los primeros "
                f"{MAX_PENDIENTES_CON_PROPUESTAS} pendientes."
            ),
        )
        for item in pendientes[MAX_PENDIENTES_CON_PROPUESTAS:]
    )
    return respuestas


def _lista_de_la_obra(
    sesion: Session, peticion: CalculoPeticion, quien: SesionActiva | None
) -> models.ListaPrecios | None:
    """La lista con que se valora la obra de `peticion` (Tarea 12), o `None` sin obra. No confirma:
    la conversión que escriba `lista_para_el_proyecto` se deshace al cerrar la sesión."""
    if peticion.proyecto is None:
        return None
    proyecto = resolver_proyecto(sesion, peticion.proyecto)
    if proyecto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=aplicacion_elaboracion.MENSAJE_SIN_OBRA
        )
    try:
        return lista_para_el_proyecto(
            sesion,
            proyecto.nombre,
            peticion.fecha,
            responsable=USUARIO_SIN_CLAVE if quien is None else quien.usuario,
        )
    except SinListaParaArmar as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None


def _elaborar_sin_guardar(
    sesion: Session, peticion: CalculoPeticion, quien: SesionActiva | None
) -> tuple[ResultadoElaboracion, dict[str, str]] | JSONResponse:
    """Elabora `peticion` con `aplicacion.elaboracion` (la misma lógica que la página de Streamlit)
    sin guardar nada. Devuelve el resultado y las partidas del catálogo (código → descripción), o
    el 409 de «rendimientos por declarar» (UC-01, flujo 3b). Con obra, con su lista y su moneda."""
    items = [_a_item_computo(item) for item in peticion.items]
    plan = aplicacion_elaboracion.plan_de(
        None if peticion.plan is None else [fila.model_dump() for fila in peticion.plan]
    )
    catalogo = Catalogo(sesion)
    lista = _lista_de_la_obra(sesion, peticion, quien)
    moneda = peticion.moneda if lista is None else lista.moneda
    try:
        resultado = aplicacion_elaboracion.elaborar_desde_catalogo(
            catalogo, items, peticion.codigo, peticion.fecha, moneda, plan, lista
        )
    except CatalogoIncompleto:
        por_declarar = aplicacion_elaboracion.rendimientos_por_declarar(
            sesion, items, peticion.fecha
        )
        if not por_declarar:
            raise  # falta otra cosa (un precio, una unidad, la lista vigente): el 409 de siempre
        sin_estimado = ", ".join(entrada.codigo_partida for entrada in por_declarar)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=RendimientosPorDeclararRespuesta(
                detalle=(
                    f"sin rendimiento estimado vigente al {peticion.fecha}: {sin_estimado}; "
                    "declare el rendimiento propuesto con POST "
                    "/presupuestos/calcular/declarar-rendimiento (tipo 'estimado', fecha no "
                    "posterior a la del presupuesto) y vuelva a calcular"
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
    descripciones = {partida.codigo: partida.descripcion for partida in catalogo.partidas()}
    return resultado, descripciones


def _partidas_respuesta(presupuesto: Presupuesto) -> list[PartidaPresupuestadaRespuesta]:
    """Los renglones de un presupuesto a dos decimales (NORMAS.md §2.3)."""
    return [
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
    ]


def _neutralizar_formula(texto: str) -> str:
    """Antepone `'` al texto que una hoja de calculo leeria como formula (`aplicacion.formulas`)."""
    return neutralizar_formula(texto)


def _generar_escenarios(
    sesion: Session, codigo: str, proyecto: str | None, peticion: EscenariosPeticion
) -> tuple[
    models.Presupuesto,
    ResultadoElaboracion,
    list[Escenario],
    list[aplicacion_elaboracion.PreciosSinEfecto],
]:
    """El base y un `Escenario` por cada supuesto de la petición (UC-08), sin guardar nada, con
    los precios de ensayo de cada uno que no cambiaron nada (`precios_sin_efecto`)."""
    # INV-083: el base se lee con `cargar_elaboracion`, no con `cargar_presupuesto`, porque el
    # contrato `Presupuesto` no lleva los pendientes y `generar_escenario` solo recalcula los
    # renglones valorados (lo mismo hace la página de escenarios). El informe propio de cada
    # escenario no los declara: ruling C4-3 (limitaciones), sin cambio de `core/` en C4.
    if len(peticion.escenarios) > MAX_ESCENARIOS:
        raise ValueError(f"se admiten como maximo {MAX_ESCENARIOS} escenarios por peticion")
    for datos in peticion.escenarios:
        if len(datos.precios) > MAX_PRECIOS_POR_ESCENARIO:
            raise ValueError(
                f"el escenario {datos.nombre!r} trae mas de {MAX_PRECIOS_POR_ESCENARIO} precios "
                "de ensayo"
            )
    modelo = _buscar_modelo(sesion, codigo, proyecto)
    catalogo = Catalogo(sesion)
    elaboracion = cargar_elaboracion(sesion, modelo.proyecto.nombre, codigo, catalogo)
    base = elaboracion.presupuesto
    # SF3: las composiciones son las de la instantanea de la version (la hoja las edita ahi); los
    # hallazgos de reglas externas (R8 a R10) se vuelven a declarar en cada escenario (SF-E1).
    composiciones = composiciones_de_presupuesto(sesion, modelo.proyecto.nombre, codigo, catalogo)
    externos = hallazgos_externos(elaboracion.informe)
    precios = [
        {
            descripcion: decimal_desde_texto(texto, f"precio de {descripcion}")
            for descripcion, texto in datos.precios.items()
        }
        for datos in peticion.escenarios
    ]
    escenarios = [
        generar_escenario(
            datos.nombre,
            base,
            composiciones,
            _parametros_escenario(modelo, datos),
            precios=de_este,
            externos=externos,
        )
        for datos, de_este in zip(peticion.escenarios, precios, strict=True)
    ]
    sin_efecto = [
        aplicacion_elaboracion.precios_sin_efecto(composiciones, de_este) for de_este in precios
    ]
    return modelo, elaboracion, escenarios, sin_efecto


def _detector_de_atipicos() -> DetectorAtipicos | None:
    """`aplicacion.actualizacion.detector_de_atipicos`: una sola definicion del detector (UC-07,
    paso 5) para la pagina de Streamlit y la API."""
    return aplicacion_actualizacion.detector_de_atipicos()


def _proyecto(sesion: Session, nombre: str) -> models.Proyecto:
    """El proyecto de ese nombre; `LookupError` (404) si no existe (`POST /proyectos` lo crea)."""
    proyecto = proyecto_por_nombre(sesion, nombre)
    if proyecto is None:
        raise LookupError(f"no hay ninguna obra {nombre!r} en el catálogo")
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
            # El contrato diría «utilidad no puede ser negativo: -0.1» (nombre interno y punto
            # decimal): se responde con el nombre de la pantalla y la coma (prueba en vivo
            # 2026-11-18, hallazgo 5), como Componer.
            if campos[nombre] < 0:
                raise ValueError(
                    f"{NOMBRES_DE_PARAMETROS[nombre]}: el valor no puede ser negativo "
                    f"({texto_de_cifra(campos[nombre])})."
                )
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
    """El renglón del presupuesto de ese código, acotado por proyecto si se indica
    (`aplicacion.elaboracion.presupuesto_por_codigo`): ninguna coincidencia es `LookupError` (404);
    un código que existe en dos obras sin `proyecto` se declara con un 409 explícito en vez de
    dejar que `MultipleResultsFound` llegue sin manejador (hallazgo de la revisión de la Tarea 2).
    """
    try:
        return aplicacion_elaboracion.presupuesto_por_codigo(sesion, codigo, proyecto)
    except aplicacion_elaboracion.PresupuestoAmbiguo as ambiguo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"el código {codigo!r} existe en más de una obra ({', '.join(ambiguo.obras)}): "
                "indique 'proyecto' en la consulta para desambiguar"
            ),
        ) from None


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
