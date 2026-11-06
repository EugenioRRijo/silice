"""`/v1/control/*`: el Control de obra por la API (ola 4 S2-C; UC-19, UC-20, spec S2 §5.5).

Las cinco pestañas de la pantalla (`ui/paginas/control.py`) sobre `aplicacion.control`, sin lógica
propia:

- `GET /linea-base` y `POST /linea-base`, `POST /parametros`: la línea base vigente, su
  declaración y los parámetros de control con su naturaleza;
- `GET /valuaciones`, `POST /valuaciones`, `POST /valuaciones/{id}/anular`, `POST /costos`, `POST
  /importar/informe` y `POST /importar`: las valuaciones (con la causa de retraso de cada línea y la
  lista de causas que se pueden elegir, MP-7), su anulación, los costos y el XLSX;
- `GET /calculo`: el valor ganado, las alertas, la reproyección y el atraso por partida con su
  causa (MP-7), que se calculan siempre (UC-20 1 a 3);
- `POST /recuperacion/opciones` y `POST /recuperacion/elegir`: las opciones a pedido y la
  decisión.

Los precios del corte se toman con uno de cuatro métodos: ninguno, comprobación directa (versión
revalorada), escalatoria o los precios declarados de los materiales (MP-7, Tarea 25); sus unitarios
van en la perspectiva de la línea base vigente al corte (costo o precio), no en una fija.

Todo exige `CONTROL_DE_OBRA` (arma, o la clave de API); elegir una opción exige además
`DECIDIR_RECUPERACION`. Toda respuesta va con `Cache-Control: no-store` y el 422 de forma es un
mensaje fijo que no repite lo enviado (`RutaSinCache` y `RutaSinEco`). El responsable de cada
escritura sale de la sesión (o `USUARIO_SIN_CLAVE` con clave de API), nunca del cuerpo. El
servidor no guarda estado entre llamadas: las opciones y la elección se calculan de nuevo con los
mismos parámetros (corte, precios, objetivo y horas), así que la elección no depende de un cálculo
previo en memoria. Los textos que vienen de fuera
(inspector, observación, fuente) viajan como datos: la interfaz los pinta como texto (RV-14). Un
`ControlInvalido` sale como 422 con su mensaje (`manejar_value_error`).
"""

from __future__ import annotations

import tempfile
from datetime import date
from typing import Annotated
from zipfile import BadZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.archivos import guardar_subida
from api.dependencias import USUARIO_SIN_CLAVE, SesionDep
from api.esquemas import ImpuestosRespuesta, impuestos_a_respuesta
from api.esquemas_corte import EquivalenciaRespuesta, equivalencia_a_respuesta
from api.esquemas_partidas import PartidasDelContratoRespuesta, partidas_a_respuesta
from api.sesion_web import exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion import control as logica
from aplicacion.causas import CAUSAS, atrasos
from aplicacion.precios_declarados import precios_convertidos
from aplicacion.proyectos import resolver_proyecto
from core.budget.control import ResultadoControl
from core.catalog import Catalogo
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

CONTROLAR = Depends(exigir_clave_o_sesion(Accion.CONTROL_DE_OBRA))
DECIDIR = Depends(exigir_clave_o_sesion(Accion.DECIDIR_RECUPERACION))
MENSAJE_FORMA = (
    "Los datos del control de obra no son válidos: las cantidades, los montos, las fechas y las "
    "observaciones van como texto, y la causa del retraso es una clave de la lista de causas."
)


class _RutaControl(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (diseño de la Hoja §1.3-7)."""

    mensaje_por_omision = MENSAJE_FORMA


router = APIRouter(
    prefix="/v1/control", tags=["control"], route_class=_RutaControl, dependencies=[CONTROLAR]
)

Activa = Annotated[SesionActiva | None, CONTROLAR]
Fila = dict[str, str]

#: Cómo se nombran por fuera los métodos de precios del corte (S1; los declarados, MP-7).
METODOS = {
    "ninguno": logica.METODO_NINGUNO,
    "comprobacion": logica.METODO_COMPROBACION,
    "escalatoria": logica.METODO_ESCALATORIA,
    "declarados": logica.METODO_DECLARADOS,
}


def _responsable(activa: SesionActiva | None) -> str:
    return USUARIO_SIN_CLAVE if activa is None else activa.usuario


def _existe(sesion: Session, proyecto: str) -> str:
    """El **nombre** del proyecto que `proyecto` nombra (V-11): llega el codigo de
    `GET /v1/proyectos` o el nombre; el resto de la ruta trabaja con el nombre."""
    encontrado = resolver_proyecto(sesion, proyecto)
    if encontrado is None:
        raise HTTPException(404, f"El proyecto «{proyecto}» no existe en este caso.")
    return encontrado.nombre


def _corte(texto: str | None) -> date | None:
    if texto is None or not texto.strip():
        return None
    try:
        return date.fromisoformat(texto.strip()[:10])
    except ValueError:
        raise logica.ControlInvalido(f"corte: {texto!r} no es una fecha (AAAA-MM-DD)") from None


class Precios(BaseModel):
    """Cómo se toman los precios del corte (S2 §4.3): el nombre del método y sus datos."""

    metodo: str = "ninguno"
    version: str = ""
    km: str = ""
    r: str = "0"
    fuente: str = ""


def _precios(
    sesion: Session, proyecto: str, catalogo: Catalogo, datos: Precios, corte: date | None
):
    if datos.metodo not in METODOS:
        raise logica.ControlInvalido(
            f"método de precios {datos.metodo!r} desconocido; use " + ", ".join(METODOS)
        )
    elegido = logica.PrecioElegido(
        METODOS[datos.metodo], datos.version, datos.km, datos.r, datos.fuente
    )
    # La perspectiva es la de la línea base al corte (antes, «costo» fijo: con una línea base en
    # la perspectiva precio, el desvío comparaba costo directo con precio unitario).
    perspectiva = logica.perspectiva_de_la_linea_base(sesion, proyecto, corte)
    return logica.precios_del_corte(sesion, proyecto, catalogo, elegido, perspectiva, corte=corte)


def _calcular(
    sesion: Session, proyecto: str, corte: str | None, datos: Precios
) -> tuple[Catalogo, ResultadoControl]:
    catalogo = Catalogo(sesion)
    dia = _corte(corte)
    precios = _precios(sesion, proyecto, catalogo, datos, dia)
    resultado = logica.calcular_el_control(sesion, proyecto, catalogo, corte=dia, precios=precios)
    return catalogo, resultado


# --- línea base y parámetros -----------------------------------------------------------------


class ParametroRespuesta(BaseModel):
    parametro: str
    que_es: str
    valor: str
    naturaleza: str


class LineaBaseRespuesta(BaseModel):
    tiene_linea_base: bool
    descripcion: str | None
    versiones: list[str]
    hay_valuaciones: bool
    parametros: list[ParametroRespuesta]


def _parametros(sesion: Session, proyecto: str) -> list[ParametroRespuesta]:
    filas = logica.filas_de_parametros(logica.parametros_actuales(sesion, proyecto))
    return [
        ParametroRespuesta(
            parametro=f["Parametro"],
            que_es=f["Que es"],
            valor=f["Valor"],
            naturaleza=f["Naturaleza"],
        )
        for f in filas
    ]


@router.get("/linea-base", response_model=LineaBaseRespuesta)
def linea_base(sesion: SesionDep, proyecto: str) -> LineaBaseRespuesta:
    """La línea base vigente, las versiones que se pueden declarar y los parámetros de control."""
    proyecto = _existe(sesion, proyecto)
    return LineaBaseRespuesta(
        tiene_linea_base=logica.tiene_linea_base(sesion, proyecto),
        descripcion=logica.describir_linea_base(sesion, proyecto),
        versiones=logica.versiones_para_la_linea_base(sesion, proyecto),
        hay_valuaciones=logica.hay_valuaciones(sesion, proyecto),
        parametros=_parametros(sesion, proyecto),
    )


SIN_LINEA_BASE = "Este proyecto todavía no tiene línea base."
SIN_LINEA_BASE_AL_CORTE = "No hay una línea base vigente a esa fecha de corte."
PROYECTO_INEXISTENTE = "El proyecto no existe en este caso."
MENSAJE_BASE_PARTIDAS = "No se pudieron leer las partidas del contrato de la carpeta de trabajo."


@router.get("/partidas", response_model=PartidasDelContratoRespuesta)
def partidas(
    sesion: SesionDep,
    proyecto: str,
    corte: Annotated[
        date | None,
        Query(description="El *hasta* de la valuación (ISO): la línea base vigente a esa fecha"),
    ] = None,
) -> PartidasDelContratoRespuesta:
    """AC2: las partidas de la versión de la línea base (las únicas que una valuación puede medir),
    para el campo «Partida» con autocompletado. Con `corte`, la de la línea base vigente a esa
    fecha, la misma contra la que R13 juzga la valuación; sin él, la más reciente. Sin línea base
    (o ninguna a esa fecha) responde vacío con su aviso: no es un error, es lo que ve quien aún no
    la declaró. `truncada` dice si la lista se recortó al tope.

    Un proyecto que no existe es un 404 fijo que no repite lo pedido (diseño de autocompletado,
    H-17); un fallo de la base, el 503 fijo, sin SQL ni rutas, como `/v1/consulta`."""
    try:
        encontrado = resolver_proyecto(sesion, proyecto)
        if encontrado is None:
            raise HTTPException(404, PROYECTO_INEXISTENTE)
        halladas = logica.partidas_de_la_linea_base(sesion, encontrado.nombre, corte)
        if halladas is not None:
            return partidas_a_respuesta(halladas)
        if corte is not None and logica.tiene_linea_base(sesion, encontrado.nombre):
            return partidas_a_respuesta(None, SIN_LINEA_BASE_AL_CORTE)
        return partidas_a_respuesta(None, SIN_LINEA_BASE)
    except SQLAlchemyError:
        raise HTTPException(503, MENSAJE_BASE_PARTIDAS) from None


class DeclararLineaBase(BaseModel):
    proyecto: str
    version: str
    desde: str
    perspectiva: str
    inicio: str
    dias_por_periodo: str = "5"
    feriados: str = ""
    fuente: str


class DescripcionRespuesta(BaseModel):
    descripcion: str | None


@router.post("/linea-base", response_model=DescripcionRespuesta)
def declarar_linea_base(
    sesion: SesionDep, peticion: DeclararLineaBase, activa: Activa
) -> DescripcionRespuesta:
    """Declara la línea base de control (RF-72)."""
    peticion.proyecto = _existe(sesion, peticion.proyecto)
    logica.declarar_linea_base(
        sesion,
        peticion.proyecto,
        peticion.version,
        desde=peticion.desde,
        perspectiva=peticion.perspectiva,
        inicio=peticion.inicio,
        dias_por_periodo=peticion.dias_por_periodo,
        feriados=peticion.feriados,
        fuente=peticion.fuente,
        responsable=_responsable(activa),
    )
    return DescripcionRespuesta(descripcion=logica.describir_linea_base(sesion, peticion.proyecto))


class ValorDeParametro(BaseModel):
    parametro: str
    valor: str


class GuardarParametros(BaseModel):
    proyecto: str
    parametros: list[ValorDeParametro]
    fuente: str


class CambiadosRespuesta(BaseModel):
    cambiados: int


@router.post("/parametros", response_model=CambiadosRespuesta)
def guardar_parametros(
    sesion: SesionDep, peticion: GuardarParametros, activa: Activa
) -> CambiadosRespuesta:
    """Guarda los parámetros enviados (los demás quedan igual), con un registro por cada cambio."""
    peticion.proyecto = _existe(sesion, peticion.proyecto)
    filas = logica.filas_de_parametros(logica.parametros_actuales(sesion, peticion.proyecto))
    por_nombre = {f["Parametro"]: f for f in filas}
    for cambio in peticion.parametros:
        if cambio.parametro not in por_nombre:
            raise logica.ControlInvalido(f"parámetro desconocido: {cambio.parametro!r}")
        por_nombre[cambio.parametro]["Valor"] = cambio.valor
    cambiados = logica.guardar_los_parametros(
        sesion,
        peticion.proyecto,
        filas,
        fuente=peticion.fuente,
        responsable=_responsable(activa),
    )
    return CambiadosRespuesta(cambiados=cambiados)


# --- valuaciones, anulación, costos e importación --------------------------------------------


class Anulable(BaseModel):
    id: int
    rotulo: str


class CausaRespuesta(BaseModel):
    """Una causa de retraso que se puede elegir en una línea: su clave y su nombre."""

    clave: str
    nombre: str


class ValuacionesRespuesta(BaseModel):
    tiene_linea_base: bool
    filas: list[Fila]
    aviso: str = ""
    anulables: list[Anulable]
    corte_por_defecto: str | None
    causas: list[CausaRespuesta] = Field(
        default_factory=lambda: [CausaRespuesta(clave=c, nombre=n) for c, n in CAUSAS.items()]
    )
    #: Tarea 18: el IVA sobre lo medido en todas las valuaciones (cada fila trae el suyo).
    impuestos: ImpuestosRespuesta
    #: La perspectiva de la línea base («costo» o «precio»); vacía sin línea base. Con «costo»
    #: el IVA de lo medido no es una cifra facturable (T18-3).
    perspectiva: str = ""


@router.get("/valuaciones", response_model=ValuacionesRespuesta)
def valuaciones(sesion: SesionDep, proyecto: str) -> ValuacionesRespuesta:
    """Las valuaciones guardadas (solo lectura) con su estado, y las que se pueden anular."""
    proyecto = _existe(sesion, proyecto)
    if not logica.tiene_linea_base(sesion, proyecto):
        return ValuacionesRespuesta(
            tiene_linea_base=False,
            filas=[],
            anulables=[],
            corte_por_defecto=None,
            impuestos=impuestos_a_respuesta(logica.impuestos_de_valuaciones(None)),
            perspectiva="",
        )
    filas: list[Fila] = []
    aviso = ""
    resultado = None
    if logica.hay_valuaciones(sesion, proyecto):
        try:
            resultado = logica.calcular_el_control(sesion, proyecto, Catalogo(sesion))
            filas = logica.filas_de_valuaciones(resultado)
        except logica.ControlInvalido as error:
            aviso = str(error)
    return ValuacionesRespuesta(
        tiene_linea_base=True,
        filas=filas,
        aviso=aviso,
        anulables=[
            Anulable(id=i, rotulo=r) for i, r in logica.valuaciones_para_anular(sesion, proyecto)
        ],
        corte_por_defecto=logica.corte_por_defecto(sesion, proyecto).isoformat(),
        impuestos=impuestos_a_respuesta(logica.impuestos_de_valuaciones(resultado)),
        perspectiva=logica.perspectiva_de_la_linea_base(sesion, proyecto, None),
    )


class LineaDeValuacion(BaseModel):
    partida: str = ""
    cantidad: str = ""
    fecha_medicion: str = ""
    observacion: str = ""
    #: La clave de la causa del retraso (`GET /valuaciones`, `causas`) o nula si no hay.
    causa: str | None = None


class RegistrarValuacion(BaseModel):
    proyecto: str
    numero: str
    desde: str
    hasta: str
    fecha: str = ""
    inspector: str = ""
    lineas: list[LineaDeValuacion] = Field(default_factory=list)
    fuente: str


class RegistroRespuesta(BaseModel):
    corte: str
    hallazgos: int
    errores: int


@router.post("/valuaciones", response_model=RegistroRespuesta)
def registrar_valuacion(
    sesion: SesionDep, peticion: RegistrarValuacion, activa: Activa
) -> RegistroRespuesta:
    """UC-19 4 y 5: registra la valuación y controla al corte (su fecha *hasta*)."""
    peticion.proyecto = _existe(sesion, peticion.proyecto)
    filas = [
        {
            "Partida": linea.partida,
            "Cantidad": linea.cantidad,
            "Fecha de medicion": linea.fecha_medicion,
            "Observacion": linea.observacion,
            "Causa": linea.causa,
        }
        for linea in peticion.lineas
    ]
    resultado = logica.registrar_y_controlar(
        sesion,
        peticion.proyecto,
        Catalogo(sesion),
        numero=peticion.numero,
        desde=peticion.desde,
        hasta=peticion.hasta,
        fecha=peticion.fecha,
        inspector=peticion.inspector,
        filas=filas,
        fuente=peticion.fuente,
        responsable=_responsable(activa),
    )
    hallazgos = resultado.informe.hallazgos
    return RegistroRespuesta(
        corte=resultado.instantanea.corte.isoformat(),
        hallazgos=len(hallazgos),
        errores=sum(1 for h in hallazgos if h.severidad.name == "ERROR"),
    )


class Anulacion(BaseModel):
    motivo: str


class ListoRespuesta(BaseModel):
    listo: bool = True


@router.post("/valuaciones/{valuacion_id}/anular", response_model=ListoRespuesta)
def anular_valuacion(
    sesion: SesionDep, valuacion_id: int, peticion: Anulacion, activa: Activa
) -> ListoRespuesta:
    """Anula una valuación (UC-19 4c): se conserva y deja de contar."""
    logica.anular(sesion, valuacion_id, motivo=peticion.motivo, responsable=_responsable(activa))
    return ListoRespuesta()


class AnotarCosto(BaseModel):
    proyecto: str
    monto: str
    moneda: str
    fecha: str
    partida: str = ""
    fuente: str


@router.post("/costos", response_model=ListoRespuesta)
def anotar_costo(sesion: SesionDep, peticion: AnotarCosto, activa: Activa) -> ListoRespuesta:
    """Anota un costo incurrido; se convierte con la tasa de su fecha al calcular."""
    peticion.proyecto = _existe(sesion, peticion.proyecto)
    logica.registrar_costo_real(
        sesion,
        peticion.proyecto,
        monto=peticion.monto,
        moneda=peticion.moneda,
        fecha=peticion.fecha,
        fuente=peticion.fuente,
        responsable=_responsable(activa),
        partida=peticion.partida,
    )
    return ListoRespuesta()


class InformeRespuesta(BaseModel):
    informe: list[str]


def _leer(archivo: UploadFile):
    """Lee el XLSX subido; lo que no es un libro legible se rechaza como un XLSX malformado."""
    with tempfile.TemporaryDirectory() as carpeta:
        try:
            return logica.leer_excel(guardar_subida(carpeta, archivo))
        except (BadZipFile, InvalidFileException, OSError, KeyError):
            raise logica.ControlInvalido(
                "El archivo no es un libro .xlsx legible; no se importó nada."
            ) from None


@router.post("/importar/informe", response_model=InformeRespuesta)
def informe_de_importacion(archivo: Annotated[UploadFile, File()]) -> InformeRespuesta:
    """Lee el XLSX sin escribir nada y da el informe previo. Un archivo malformado se rechaza."""
    return InformeRespuesta(informe=list(_leer(archivo).informe))


class ImportadasRespuesta(BaseModel):
    importadas: int


@router.post("/importar", response_model=ImportadasRespuesta)
def importar(
    sesion: SesionDep,
    archivo: Annotated[UploadFile, File()],
    proyecto: Annotated[str, Form()],
    fuente: Annotated[str, Form()],
    activa: Activa,
) -> ImportadasRespuesta:
    """Registra todas las valuaciones y costos del XLSX, o ninguno."""
    proyecto = _existe(sesion, proyecto)
    cuantas = logica.importar_excel(
        sesion, proyecto, _leer(archivo), fuente=fuente, responsable=_responsable(activa)
    )
    return ImportadasRespuesta(importadas=cuantas)


# --- cálculo: valor ganado, alertas y reproyección -------------------------------------------


class PuntoDeCurva(BaseModel):
    periodo: str
    pv: str
    ev: str
    ac: str | None


class Terminos(BaseModel):
    indice: str
    reproyectado: str
    plan_base: str
    eac_sistema: str


class Equilibrio(BaseModel):
    punto: str
    mensaje: str


class PlanReproyectado(BaseModel):
    columnas: list[str]
    filas: list[Fila]


class AtrasoRespuesta(BaseModel):
    """Una partida que termina después de su plan: días hábiles, causa (clave o nula) y la frase."""

    codigo: str
    dias: int
    causa: str | None
    texto: str


class PrecioConvertidoRespuesta(BaseModel):
    """Un precio del corte vigente que se declaró en otra moneda que la obra, con su cuenta."""

    descripcion: str
    unidad: str
    fecha: str = Field(description="aaaa-mm-dd: desde cuándo rige el precio")
    fuente: str
    equivalencia: EquivalenciaRespuesta


class CalculoRespuesta(BaseModel):
    estado: str
    corte: str | None = None
    dia: int | None = None
    moneda: str | None = None
    indicadores: list[Fila] = Field(default_factory=list)
    costos_sin_tasa: list[str] = Field(default_factory=list)
    curva: list[PuntoDeCurva] = Field(default_factory=list)
    spi_no_aplica: bool = False
    alertas: list[Fila] = Field(default_factory=list)
    terminos: Terminos | None = None
    motivo_termino: str = ""
    equilibrio: Equilibrio | None = None
    estudios: str = ""
    reproyeccion: list[Fila] = Field(default_factory=list)
    plan: PlanReproyectado | None = None
    decisiones: list[Fila] = Field(default_factory=list)
    versiones_revaloradas: list[str] = Field(default_factory=list)
    atrasos: list[AtrasoRespuesta] = Field(default_factory=list)
    precios_convertidos: list[PrecioConvertidoRespuesta] = Field(
        default_factory=list,
        description=(
            "Con `metodo=declarados`, los precios del corte vigentes que se convirtieron de otra "
            "moneda con la tasa del BCV, con su cuenta; vacío con otro método"
        ),
    )


def _texto(valor: object) -> str:
    return format(valor, "f") if hasattr(valor, "as_tuple") else str(valor)


@router.get("/calculo", response_model=CalculoRespuesta, response_model_exclude_none=False)
def calculo(
    sesion: SesionDep,
    proyecto: str,
    corte: str | None = None,
    metodo: str = "ninguno",
    version: str = "",
    km: str = "",
    r: str = "0",
    fuente: str = "",
) -> CalculoRespuesta:
    """El control al corte: valor ganado, alertas, términos, reproyección y decisiones tomadas."""
    proyecto = _existe(sesion, proyecto)
    if not logica.tiene_linea_base(sesion, proyecto):
        return CalculoRespuesta(estado="sin_linea_base")
    if not logica.hay_valuaciones(sesion, proyecto):
        return CalculoRespuesta(estado="sin_valuaciones")
    _, resultado = _calcular(
        sesion, proyecto, corte, Precios(metodo=metodo, version=version, km=km, r=r, fuente=fuente)
    )
    ind, rep = resultado.indicadores, resultado.reproyeccion
    moneda = resultado.instantanea.moneda
    equilibrio = resultado.equilibrio_proyectado
    columnas, plan = logica.filas_del_plan_reproyectado(resultado)
    return CalculoRespuesta(
        estado="listo",
        corte=resultado.instantanea.corte.isoformat(),
        dia=resultado.estado.dia,
        moneda=moneda,
        indicadores=logica.filas_de_indicadores(sesion, resultado),
        costos_sin_tasa=[
            f"El costo de {c.monto} {c.moneda} del {c.fecha:%d/%m/%Y} no tiene tasa aplicable "
            "(más de 7 días sin tasa): el AC y lo que depende de él no están disponibles; "
            "nada se estima."
            for c in resultado.costos_sin_tasa
        ],
        curva=[
            PuntoDeCurva(
                periodo=str(p["Periodo"]),
                pv=_texto(p["PV"]),
                ev=_texto(p["EV"]),
                ac=None if p["AC"] is None else _texto(p["AC"]),
            )
            for p in logica.curva_pv_ev_ac(sesion, resultado)
        ],
        spi_no_aplica=ind.pv == 0,
        alertas=logica.alertas_en_filas(resultado),
        terminos=Terminos(
            indice=logica.dia_con_fecha(resultado, ind.termino_indice),
            reproyectado=logica.dia_con_fecha(resultado, rep.termino),
            plan_base=logica.dia_con_fecha(resultado, resultado.estado.dias_plan),
            eac_sistema=logica.texto_monto(ind.eac_sistema)
            + ("" if ind.eac_sistema is None else f" {moneda}"),
        ),
        motivo_termino="" if rep.termino is not None else logica.con_tildes(rep.motivo_termino),
        equilibrio=None
        if equilibrio is None
        else Equilibrio(
            punto=logica.texto_monto(equilibrio.punto),
            mensaje=logica.con_tildes(equilibrio.mensaje),
        ),
        estudios=logica.estudios_que_suma(resultado),
        reproyeccion=logica.filas_de_reproyeccion(resultado),
        plan=PlanReproyectado(columnas=list(columnas), filas=plan),
        decisiones=logica.filas_de_decisiones(sesion, proyecto),
        versiones_revaloradas=logica.versiones_revaloradas(sesion, proyecto),
        atrasos=[
            AtrasoRespuesta(codigo=a.codigo, dias=a.dias, causa=a.causa, texto=a.texto)
            for a in atrasos(sesion, resultado)
        ],
        precios_convertidos=[
            PrecioConvertidoRespuesta(
                descripcion=c.descripcion,
                unidad=c.unidad,
                fecha=c.fecha.isoformat(),
                fuente=c.fuente,
                equivalencia=equivalencia_a_respuesta(c.equivalencia),
            )
            for c in (
                precios_convertidos(sesion, proyecto, resultado.instantanea.corte)
                if metodo == "declarados"
                else []
            )
        ],
    )


# --- recuperación ----------------------------------------------------------------------------


class PeticionOpciones(BaseModel):
    proyecto: str
    corte: str | None = None
    precios: Precios = Field(default_factory=Precios)
    objetivo: str = ""
    horas_previas: str = "0"


class SupuestoRespuesta(BaseModel):
    """Un supuesto de la opción en sus tres ranuras; `naturaleza` es el código del núcleo."""

    nombre: str
    valor: str
    naturaleza: str


class OpcionRespuesta(BaseModel):
    clave: str
    titulo: str
    aplica: bool
    motivo: str
    requisitos: list[str]
    requiere_declaracion: bool
    fila: Fila
    # VD-1: los mismos supuestos de `fila["Nota"]`, por ranura; vacía si la opción no aplica.
    supuestos: list[SupuestoRespuesta] = Field(default_factory=list)


class OpcionesRespuesta(BaseModel):
    opciones: list[OpcionRespuesta]


def _opciones(sesion: Session, peticion: PeticionOpciones):
    peticion.proyecto = _existe(sesion, peticion.proyecto)
    catalogo, resultado = _calcular(sesion, peticion.proyecto, peticion.corte, peticion.precios)
    todas = logica.calcular_las_opciones(
        resultado, objetivo=peticion.objetivo, horas_previas=peticion.horas_previas
    )
    return catalogo, resultado, todas


@router.post("/recuperacion/opciones", response_model=OpcionesRespuesta)
def opciones(sesion: SesionDep, peticion: PeticionOpciones) -> OpcionesRespuesta:
    """Las opciones de recuperación a pedido (UC-20 4); no escribe nada."""
    _, _, todas = _opciones(sesion, peticion)
    return OpcionesRespuesta(
        opciones=[
            OpcionRespuesta(
                clave=o.nombre,
                titulo=logica.con_tildes(o.titulo),
                aplica=o.aplica,
                motivo=logica.con_tildes(o.motivo),
                requisitos=[logica.con_tildes(r) for r in o.requisitos],
                requiere_declaracion=o.requiere_declaracion,
                fila=logica.filas_de_opciones([o])[0],
                supuestos=[SupuestoRespuesta(**s) for s in logica.supuestos_de_opcion(o)],
            )
            for o in todas
        ]
    )


class PeticionElegir(PeticionOpciones):
    opcion: str
    fuente: str
    declaracion_independencia: str = ""


class VersionRespuesta(BaseModel):
    version: str


@router.post("/recuperacion/elegir", response_model=VersionRespuesta, dependencies=[DECIDIR])
def elegir(sesion: SesionDep, peticion: PeticionElegir, activa: Activa) -> VersionRespuesta:
    """UC-20 5 y 6: crea la versión de la opción elegida y guarda la decisión.

    Recalcula las opciones con los mismos parámetros: la elección no depende de un cálculo previo
    guardado en el servidor.
    """
    catalogo, resultado, todas = _opciones(sesion, peticion)
    elegida = next((o for o in todas if o.nombre == peticion.opcion), None)
    if elegida is None:
        raise logica.ControlInvalido(
            f"opción {peticion.opcion!r} desconocida; use " + ", ".join(o.nombre for o in todas)
        )
    codigo = logica.elegir_opcion(
        sesion,
        resultado,
        elegida,
        catalogo,
        fuente=peticion.fuente,
        responsable=_responsable(activa),
        declaracion_independencia=peticion.declaracion_independencia,
    )
    return VersionRespuesta(version=codigo)
