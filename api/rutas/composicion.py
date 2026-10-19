"""`/v1/composicion/*`: «Componer una partida» por HTTP (ola 3 de la migración, S2-B).

Contrato: `docs/planes/PLAN_MIGRACION_OLA_3_B_COMPONER.md` §2. Seis rutas, todas con `EDITAR_HOJA`
(arma), como la página clásica (`ui/paginas/componer.py`, UC-10 y UC-11), sobre el caso de la
sesión (`SesionDep`). La lógica vive en `aplicacion.composicion` (la comparte la página); aquí
solo se traducen las tablas de texto y se arma la respuesta. Montos y decimales viajan como texto
(NORMAS.md, regla 3); el navegador no calcula nada (RB-2).

- `evaluar` no escribe y nunca responde 4xx por una tabla a medias: `estado: "incompleto"` con el
  mensaje de la conversión.
- `guardar` confirma (`commit`) solo con resultado: 422 sin escribir si faltan las condiciones
  (RF-33), si la composición es inválida o si `motivo_para_no_reemplazar` da motivo; 409 sin lista
  de precios vigente (`CatalogoIncompleto`, manejador global de `api/main.py`).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.acceso import EDITAR
from api.dependencias import SesionDep
from aplicacion.composicion import (
    ComposicionInvalida,
    Evaluacion,
    Precarga,
    TablasDeTexto,
    evaluar_composicion,
    filas_desde_composicion,
    guardar_desde_tablas,
    precarga_de_partida,
    presentar,
    similares_con_composicion,
    sugerencias_de_referencia,
)
from core.contracts import Dominio, ModalidadManoObra, ResultadoAPU

router = APIRouter(prefix="/v1/composicion", tags=["composicion"])


# --- Esquemas (junto a la ruta, plan de la sesión 2b §3) ---------------------------------------


class FilaMaterial(BaseModel):
    descripcion: str = ""
    unidad: str = ""
    cantidad: str = ""
    precio: str = ""


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


class EvaluacionRespuesta(BaseModel):
    estado: Literal["vacio", "incompleto", "valido"]
    aviso: str | None
    desglose: Desglose | None
    advertencias: list[Advertencia]
    requiere_justificacion: bool
    contraste: Contraste | None


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


def _evaluacion(evaluacion: Evaluacion) -> EvaluacionRespuesta:
    contraste = evaluacion.contraste
    return EvaluacionRespuesta(
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
    """El desglose en vivo con sus advertencias, sin escribir (RB-2, RB-5)."""
    evaluacion = evaluar_composicion(
        sesion,
        peticion.codigo,
        peticion.descripcion,
        peticion.unidad,
        peticion.dominio,
        peticion.rendimiento,
        _filas(peticion.materiales),
        _filas(peticion.equipos),
        _filas(peticion.mano_obra),
    )
    return _evaluacion(evaluacion)


@router.get("/partidas/{codigo}", response_model=PrecargaRespuesta, dependencies=EDITAR)
def precargar(sesion: SesionDep, codigo: str) -> PrecargaRespuesta:
    """UC-11, paso 1: las tablas de una partida existente; sin partida o sin lista vigente,
    `existe=false` y tablas vacías (UC-10), nunca 404."""
    return _precarga(precarga_de_partida(sesion, codigo))


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
def guardar(sesion: SesionDep, peticion: PeticionGuardar) -> GuardadoRespuesta:
    """Guarda la composición (UC-10 o UC-11) y, con la advertencia de RF-27, su justificación
    (UC-06 4a). Confirma solo con resultado; con motivo, 422 y nada se escribe."""
    try:
        resultado = guardar_desde_tablas(
            sesion,
            peticion.codigo,
            peticion.descripcion,
            peticion.unidad,
            peticion.dominio,
            peticion.rendimiento,
            _filas(peticion.materiales),
            _filas(peticion.equipos),
            _filas(peticion.mano_obra),
            fecha=peticion.fecha,
            condiciones=peticion.condiciones,
            justificacion=peticion.justificacion,
        )
    except ComposicionInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if resultado.precio_unitario is None or resultado.mensaje is None:
        sesion.rollback()
        raise HTTPException(status_code=422, detail=resultado.motivo)
    sesion.commit()
    return GuardadoRespuesta(
        precio_unitario=resultado.precio_unitario,
        mensaje=resultado.mensaje,
        justificada=resultado.justificada,
        avisos=list(resultado.avisos),
    )
