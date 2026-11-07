"""`/v1/composicion/*`: «Componer una partida» por HTTP (ola 3 de la migración, S2-B).

Contrato: `docs/planes/PLAN_MIGRACION_OLA_3_B_COMPONER.md` §2. Seis rutas, todas con `EDITAR_HOJA`
(arma), como la página clásica (`ui/paginas/componer.py`, UC-10 y UC-11), sobre el caso de la
sesión (`SesionDep`). La lógica vive en `aplicacion.composicion` (la comparte la página); aquí
solo se traducen las tablas de texto y se arma la respuesta. Montos y decimales viajan como texto
(NORMAS.md, regla 3); el navegador no calcula nada (RB-2).

- `evaluar` no escribe y nunca responde 4xx por una tabla a medias: `estado: "incompleto"` con el
  mensaje de la conversión.
- `guardar` confirma (`commit`) solo con resultado: 422 sin escribir si faltan las condiciones
  (RF-33), si la composición es inválida o si `motivo_para_no_reemplazar` da motivo; 409 con el
  mensaje de `SinListaParaArmar` sin lista para armar o con la vigente en otra moneda que la
  carpeta (MP-1, Tarea 3: los precios van a la lista de hoy).
- `prever` (MP-1, Tarea 3; D-MP2) recibe el mismo cuerpo que `guardar` y dice, sin escribir nada,
  en qué lista quedarían los precios (`lista_nueva` si el guardado la crearía) y qué insumos
  quedarían como variante con su precio en la lista y el tecleado. Los mismos 409 y 422 que
  `guardar`.
- **Desperdicio** (F5 vial, tarea 3; `aplicacion.desperdicio`): una fila de materiales puede traer
  `desperdicio` (porcentaje, «4» es 4 %) con la cantidad neta en `cantidad`. `evaluar`, `guardar` y
  `prever` pasan a la composición la cantidad con desperdicio que calcula el servidor; `evaluar`
  devuelve la leyenda de cada fila («0,52 (0,50 + 4 %)») en `desperdicios`; `guardar` deja la
  traza en la misma transacción y la precarga devuelve la neta y el porcentaje. Una fila sin
  desperdicio viaja igual que antes, sin la clave. Un porcentaje mal escrito es `incompleto` en
  `evaluar` y 422 en `guardar` y `prever`, con el mensaje de la fila.
- Ningún 422 de forma repite lo enviado (`RutaSinEco` en todo el router; deuda de la Tarea 3 que
  cierra la Tarea 4): `guardar` y `prever` dicen `MENSAJE_FORMA_PREVER` (reciben el mismo cuerpo);
  las demás, el mensaje de omisión de `RutaSinEco`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.acceso import EDITAR
from api.dependencias import SesionDep
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion.composicion import (
    ComposicionInvalida,
    Evaluacion,
    Precarga,
    Prevision,
    TablasDeTexto,
    evaluar_composicion,
    filas_desde_composicion,
    guardar_desde_tablas,
    precarga_de_partida,
    presentar,
    prever_guardado,
    similares_con_composicion,
    sugerencias_de_referencia,
)
from aplicacion.desperdicio import (
    TrazaDesperdicio,
    aplicar_desperdicio,
    con_desperdicio,
    guardar_trazas,
    leyenda,
    trazas_por_fila,
    trazas_vigentes,
)
from aplicacion.listas_para_armar import SinListaParaArmar
from core.contracts import Dominio, ModalidadManoObra, ResultadoAPU

#: El 422 de forma de `guardar` y `prever`: fijo, sin repetir lo enviado.
MENSAJE_FORMA_PREVER = (
    "La composición enviada no tiene la forma esperada: revise la cabecera, las tres tablas, la "
    "fecha y las condiciones."
)

router = APIRouter(prefix="/v1/composicion", tags=["composicion"], route_class=RutaSinEco)


# --- Esquemas (junto a la ruta, plan de la sesión 2b §3) ---------------------------------------


def _vacio(valor: str) -> bool:
    return valor == ""


class FilaMaterial(BaseModel):
    """`desperdicio` (F5 vial, tarea 3): el porcentaje de desperdicio, con la cantidad neta en
    `cantidad`. Vacío no viaja en la respuesta, así una fila de siempre no cambia."""

    descripcion: str = ""
    unidad: str = ""
    cantidad: str = ""
    precio: str = ""
    desperdicio: str = Field(default="", exclude_if=_vacio)


class FilaEquipo(BaseModel):
    descripcion: str = ""
    cantidad: str = ""
    precio: str = ""
    depreciacion: str = ""


class FilaManoObra(BaseModel):
    """`modalidad` vacía es jornal (el contrato); una que no es `jornal` ni `destajo` da el aviso
    de la conversión, como en la página clásica, no un 422 de validación."""

    descripcion: str = ""
    cantidad: str = ""
    sueldo: str = ""
    modalidad: str = ""


class Tablas(BaseModel):
    materiales: list[FilaMaterial] = []
    equipos: list[FilaEquipo] = []
    mano_obra: list[FilaManoObra] = []


class Cabecera(BaseModel):
    codigo: str = ""
    descripcion: str = ""
    unidad: str = ""
    dominio: Dominio
    rendimiento: str = ""


class PeticionEvaluar(Cabecera, Tablas):
    """Cabecera y tablas tal como se teclean: todo texto, vacíos permitidos."""


class PeticionGuardar(PeticionEvaluar):
    fecha: date
    condiciones: str = ""
    justificacion: str | None = None


class Desglose(BaseModel):
    materiales: str
    equipos: str
    mano_obra: str
    costo_directo: str
    con_administracion: str
    precio_unitario: str


class Advertencia(BaseModel):
    tipo: Literal[
        "rendimiento", "rendimiento_ml", "precio_atipico", "contraste_aace", "partida_nueva"
    ]
    texto: str


class Contraste(BaseModel):
    tecnica: str
    registros: int
    pu_estimado: str
    dentro_de_rango: bool


class DesperdicioDeFila(BaseModel):
    """La cantidad con desperdicio de una fila de materiales, dicha por el servidor (F5 vial)."""

    fila: int
    descripcion: str
    leyenda: str


class EvaluacionRespuesta(BaseModel):
    estado: Literal["vacio", "incompleto", "valido"]
    aviso: str | None
    desglose: Desglose | None
    advertencias: list[Advertencia]
    requiere_justificacion: bool
    contraste: Contraste | None
    desperdicios: list[DesperdicioDeFila] = []


class OpcionesRespuesta(BaseModel):
    dominios: list[str]
    modalidades: list[str]


class PrecargaRespuesta(BaseModel):
    existe: bool
    tablas: Tablas
    rendimiento_propuesto: str | None
    hay_historial: bool


class SugerenciaRespuesta(BaseModel):
    etiqueta: str
    ref_maprex: str
    fila: dict[str, str]


class SimilarRespuesta(BaseModel):
    codigo: str
    descripcion: str
    puntaje: str
    rendimiento: str | None
    unidad: str | None
    tablas: Tablas | None
    aviso: str | None


class GuardadoRespuesta(BaseModel):
    precio_unitario: str
    mensaje: str
    justificada: bool
    avisos: list[str]


class ListaDeHoy(BaseModel):
    """La lista donde quedarían los precios; `fecha` en ISO (`aaaa-mm-dd`)."""

    nombre: str
    moneda: str
    fecha: str


class VariantePrevista(BaseModel):
    """Montos como texto con punto, exactos (`Decimal` en notación fija)."""

    descripcion: str
    unidad: str
    precio_en_lista: str
    precio_tecleado: str
    codigo_variante: str


class PrevisionRespuesta(BaseModel):
    lista: ListaDeHoy
    lista_nueva: bool
    variantes: list[VariantePrevista]


# --- Traducción ---------------------------------------------------------------------------------


def _filas(filas: Sequence[BaseModel]) -> list[dict[str, str]]:
    return [fila.model_dump() for fila in filas]


def _tablas(tablas: TablasDeTexto) -> Tablas:
    materiales, equipos, mano_obra = tablas
    return Tablas(
        materiales=[FilaMaterial(**fila) for fila in materiales],
        equipos=[FilaEquipo(**fila) for fila in equipos],
        mano_obra=[FilaManoObra(**fila) for fila in mano_obra],
    )


def _desglose(resultado: ResultadoAPU) -> Desglose:
    return Desglose(
        materiales=presentar(resultado.materiales),
        equipos=presentar(resultado.equipos),
        mano_obra=presentar(resultado.mano_obra),
        costo_directo=presentar(resultado.costo_directo),
        con_administracion=presentar(resultado.con_administracion),
        precio_unitario=presentar(resultado.precio_unitario),
    )


def _materiales(
    filas: Sequence[FilaMaterial],
) -> tuple[list[dict[str, str]], list[TrazaDesperdicio]]:
    """Las filas de materiales con la cantidad con desperdicio que calcula el servidor, y la traza.
    `ComposicionInvalida` si un porcentaje está mal escrito."""
    return aplicar_desperdicio(_filas(filas))


def _evaluacion(
    evaluacion: Evaluacion, desperdicios: Sequence[tuple[int, TrazaDesperdicio]] = ()
) -> EvaluacionRespuesta:
    contraste = evaluacion.contraste
    return EvaluacionRespuesta(
        desperdicios=[
            DesperdicioDeFila(fila=fila, descripcion=traza.descripcion, leyenda=leyenda(traza))
            for fila, traza in desperdicios
        ],
        estado=evaluacion.estado,
        aviso=evaluacion.aviso,
        desglose=None if evaluacion.resultado is None else _desglose(evaluacion.resultado),
        advertencias=[Advertencia(tipo=a.tipo, texto=a.texto) for a in evaluacion.advertencias],
        requiere_justificacion=evaluacion.requiere_justificacion,
        contraste=None
        if contraste is None
        else Contraste(
            tecnica=contraste.tecnica,
            registros=contraste.registros,
            pu_estimado=f"{contraste.pu_estimado:f}",
            dentro_de_rango=contraste.dentro_de_rango,
        ),
    )


def _prevision(prevision: Prevision) -> PrevisionRespuesta:
    return PrevisionRespuesta(
        lista=ListaDeHoy(
            nombre=prevision.lista.nombre,
            moneda=prevision.lista.moneda,
            fecha=prevision.lista.fecha.isoformat(),
        ),
        lista_nueva=prevision.lista_nueva,
        variantes=[
            VariantePrevista(
                descripcion=variante.descripcion,
                unidad=variante.unidad,
                precio_en_lista=f"{variante.precio_en_lista:f}",
                precio_tecleado=f"{variante.precio_tecleado:f}",
                codigo_variante=variante.codigo_variante,
            )
            for variante in prevision.variantes
        ],
    )


def _precarga(precarga: Precarga) -> PrecargaRespuesta:
    return PrecargaRespuesta(
        existe=precarga.existe,
        tablas=_tablas(precarga.tablas),
        rendimiento_propuesto=precarga.rendimiento_propuesto,
        hay_historial=precarga.hay_historial,
    )


# --- Rutas --------------------------------------------------------------------------------------


@router.get("/opciones", response_model=OpcionesRespuesta, dependencies=EDITAR)
def opciones() -> OpcionesRespuesta:
    """Los dominios de la cabecera y las modalidades de mano de obra (los valores del contrato,
    los mismos que ofrece la página clásica)."""
    return OpcionesRespuesta(
        dominios=[dominio.value for dominio in Dominio],
        modalidades=[modalidad.value for modalidad in ModalidadManoObra],
    )


@router.post("/evaluar", response_model=EvaluacionRespuesta, dependencies=EDITAR)
def evaluar(sesion: SesionDep, peticion: PeticionEvaluar) -> EvaluacionRespuesta:
    """El desglose en vivo con sus advertencias, sin escribir (RB-2, RB-5). Con desperdicio, la
    cantidad que se evalúa es la que calcula el servidor y cada fila trae su leyenda."""
    try:
        por_fila = trazas_por_fila(_filas(peticion.materiales))
        materiales, _ = _materiales(peticion.materiales)
    except ComposicionInvalida as error:
        return EvaluacionRespuesta(
            estado="incompleto",
            aviso=str(error),
            desglose=None,
            advertencias=[],
            requiere_justificacion=False,
            contraste=None,
        )
    evaluacion = evaluar_composicion(
        sesion,
        peticion.codigo,
        peticion.descripcion,
        peticion.unidad,
        peticion.dominio,
        peticion.rendimiento,
        materiales,
        _filas(peticion.equipos),
        _filas(peticion.mano_obra),
    )
    return _evaluacion(evaluacion, por_fila)


@router.get("/partidas/{codigo}", response_model=PrecargaRespuesta, dependencies=EDITAR)
def precargar(sesion: SesionDep, codigo: str) -> PrecargaRespuesta:
    """UC-11, paso 1: las tablas de una partida existente; sin partida o sin lista vigente,
    `existe=false` y tablas vacías (UC-10), nunca 404. Los materiales con la traza de su
    desperdicio vuelven con la cantidad neta y el porcentaje (F5 vial)."""
    precarga = precarga_de_partida(sesion, codigo)
    materiales, equipos, mano_obra = precarga.tablas
    trazas = trazas_vigentes(sesion, codigo.strip()) if precarga.existe else []
    if trazas:
        tablas = (con_desperdicio(materiales, trazas), equipos, mano_obra)
        precarga = replace(precarga, tablas=tablas)
    return _precarga(precarga)


@router.get("/referencia", response_model=list[SugerenciaRespuesta], dependencies=EDITAR)
def referencia(
    tipo: Literal["material", "equipo", "mano_obra"], q: str = ""
) -> list[SugerenciaRespuesta]:
    """Las filas de la referencia MaPreX que contienen `q`, ya completadas para su tabla (la
    referencia son archivos del repositorio, no el caso: no abre la base)."""
    return [
        SugerenciaRespuesta(etiqueta=s.etiqueta, ref_maprex=s.ref_maprex, fila=s.fila)
        for s in sugerencias_de_referencia(q, tipo)
    ]


@router.get("/similares", response_model=list[SimilarRespuesta], dependencies=EDITAR)
def similares(
    sesion: SesionDep, dominio: Dominio, descripcion: str = Query("")
) -> list[SimilarRespuesta]:
    """Ayuda 1: partidas del mismo dominio parecidas a la descripción, de solo lectura."""
    respuesta = []
    for similar in similares_con_composicion(sesion, dominio, descripcion):
        composicion = similar.composicion
        respuesta.append(
            SimilarRespuesta(
                codigo=similar.codigo,
                descripcion=similar.descripcion,
                puntaje=f"{similar.puntaje:.2f}",
                rendimiento=None if composicion is None else f"{composicion.rendimiento:f}",
                unidad=None if composicion is None else composicion.unidad,
                tablas=None
                if composicion is None
                else _tablas(filas_desde_composicion(composicion)),
                aviso=similar.aviso,
            )
        )
    return respuesta


@router.post("/guardar", response_model=GuardadoRespuesta, dependencies=EDITAR)
@sin_eco(MENSAJE_FORMA_PREVER)
def guardar(sesion: SesionDep, peticion: PeticionGuardar) -> GuardadoRespuesta:
    """Guarda la composición (UC-10 o UC-11) y, con la advertencia de RF-27, su justificación
    (UC-06 4a). Confirma solo con resultado; con motivo, 422 y nada se escribe. La traza del
    desperdicio (F5 vial) se guarda en la misma transacción."""
    try:
        materiales, trazas = _materiales(peticion.materiales)
        resultado = guardar_desde_tablas(
            sesion,
            peticion.codigo,
            peticion.descripcion,
            peticion.unidad,
            peticion.dominio,
            peticion.rendimiento,
            materiales,
            _filas(peticion.equipos),
            _filas(peticion.mano_obra),
            fecha=peticion.fecha,
            condiciones=peticion.condiciones,
            justificacion=peticion.justificacion,
        )
    except SinListaParaArmar as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ComposicionInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if resultado.precio_unitario is None or resultado.mensaje is None:
        sesion.rollback()
        raise HTTPException(status_code=422, detail=resultado.motivo)
    # la hora solo fecha el rastro de la traza; no entra en ninguna cifra
    ahora = datetime.now().replace(microsecond=0)
    guardar_trazas(sesion, peticion.codigo.strip(), trazas, ahora=ahora)
    sesion.commit()
    return GuardadoRespuesta(
        precio_unitario=resultado.precio_unitario,
        mensaje=resultado.mensaje,
        justificada=resultado.justificada,
        avisos=list(resultado.avisos),
    )


@sin_eco(MENSAJE_FORMA_PREVER)
def prever(sesion: SesionDep, peticion: PeticionGuardar) -> PrevisionRespuesta:
    """Lo que haría `guardar` con el mismo cuerpo (la lista de hoy y las variantes), sin escribir
    nada: `prever_guardado` lo deshace siempre y aquí no se confirma."""
    try:
        materiales, _ = _materiales(peticion.materiales)
        prevision = prever_guardado(
            sesion,
            peticion.codigo,
            peticion.descripcion,
            peticion.unidad,
            peticion.dominio,
            peticion.rendimiento,
            materiales,
            _filas(peticion.equipos),
            _filas(peticion.mano_obra),
            fecha=peticion.fecha,
            condiciones=peticion.condiciones,
            justificacion=peticion.justificacion,
        )
    except SinListaParaArmar as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ComposicionInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _prevision(prevision)


# Con `add_api_route`, como en la Tarea 3: el orden de las rutas en `docs/api.json` no cambia.
router.add_api_route(
    "/prever",
    prever,
    methods=["POST"],
    response_model=PrevisionRespuesta,
    dependencies=EDITAR,
    responses={
        409: {"description": "Sin lista para armar, o la vigente en otra moneda que la carpeta."},
        422: {"description": "Sin condiciones, composición inválida o cabecera distinta."},
    },
)
