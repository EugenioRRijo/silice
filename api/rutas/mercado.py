"""`/v1/mercado`: el estudio de mercado y «Usar este precio» (MP-5, Tarea 14 del plan de montar un
presupuesto; diseño §5.1 y §10, D-MP2).

Rutas finas sobre `aplicacion.mercado`, todas con `EDITAR_HOJA` (arma, o la clave de API: es
trabajo de quien arma); revisa y administra reciben 403. Operan sobre la carpeta de trabajo de la
sesión (`SesionDep`); las que escriben van con `BEGIN IMMEDIATE` y confirman aquí (todo o nada).

- `GET /{lado}/{codigo}?dias=90&proyecto=` → `{lado, codigo, moneda, estadisticas, propuesta,
  piso, precio_unitario, observaciones}`. Las estadísticas, la propuesta, el piso y el precio con
  utilidad van en céntimos (lo que se muestra); el precio de cada observación, exacto. En cobro,
  `proyecto` (código o nombre de la obra abierta) da los parámetros del piso.
- `POST /observaciones` → 201 `{id}`; `POST /observaciones/{id}/anular` → 200 `{id, anulada_por}`.
- `GET /compra/{codigo}/afectados` → `{apus}` (lo que se muestra antes de «Usar este precio»).
- `POST /compra/{codigo}/usar` `{precio, observacion_id}` → 200 `{lista}` (el nombre de la lista).
- `POST /cobro/{codigo}/usar` `{precio, observaciones}` → 200 `{codigo, precio, moneda}`.
- `GET /objetivos?partidas=A,B` → `{objetivos: [{codigo, precio, moneda}]}`.

Errores: el 422 de forma (lado, fuente, fecha, precio que no es texto, códigos largos, ventana
fuera de 1 a 3.650 días) es un mensaje fijo que no repite lo enviado; el 422 de una regla
(`CifraInvalida` y `ReglaDeMercado`: fuente, nota, fecha futura, precio no positivo, objetivo de
más de 2 decimales, observación ajena o de otra moneda) lleva el mensaje de `aplicacion.mercado`, y
cualquier otro `ValueError` un texto fijo; 404 lo que no existe; 409 sin moneda, sin lista para
armar, una partida cuyo costo no se puede calcular o una observación ya anulada; 503 fijo ante un
fallo de la base.
`Cache-Control: no-store` en toda respuesta. Quien escribe consta como la cuenta de la sesión (o
`USUARIO_API` con la clave). Montos como texto con punto decimal, nunca como número.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from api.dependencias import USUARIO_API, SesionDeEscrituraDep, SesionDep
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion.cifras import CifraInvalida
from aplicacion.listas_para_armar import SinListaParaArmar
from aplicacion.mercado import (
    CarpetaSinMoneda,
    NoExiste,
    ObservacionAnulada,
    ReglaDeMercado,
    anular_observacion,
    apus_afectados,
    centimos,
    estadisticas,
    exigir_codigo,
    objetivos,
    observaciones_vigentes,
    piso_de_cobro,
    propuesta,
    registrar_observacion,
    usar_precio_de_cobro,
    usar_precio_de_compra,
)
from aplicacion.proyectos import resolver_proyecto
from core.catalog import Catalogo
from core.catalog.errores import CatalogoIncompleto
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_FORMA = (
    "Los datos del estudio de mercado no son válidos: el lado es compra o cobro; la fuente es "
    "proveedor, competidor, cotización, MaPreX o compra; la fecha va como aaaa-mm-dd; el precio "
    "va como texto; los códigos admiten hasta 40 caracteres y la ventana va de 1 a 3.650 días."
)
MENSAJE_BASE = "No se pudo leer ni guardar el estudio de mercado de la carpeta de trabajo."
MENSAJE_INESPERADO = "No se pudo procesar el estudio de mercado con esos datos."
_LARGO_CODIGO = 40
_DIAS_MAXIMO = 3650

#: Los valores de `aplicacion.mercado.LADOS` y `FUENTES` (una prueba vigila que coincidan).
Lado = Literal["compra", "cobro"]
FuenteTipo = Literal["proveedor", "competidor", "cotizacion", "maprex", "compra"]


class _RutaMercado(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (diseño de la Hoja §1.3-7)."""

    mensaje_por_omision = MENSAJE_FORMA


router = APIRouter(prefix="/v1/mercado", tags=["mercado"], route_class=_RutaMercado)
EDITAR_HOJA = Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))
Activa = Annotated[SesionActiva | None, EDITAR_HOJA]
Codigo = Annotated[str, Path(min_length=1, max_length=_LARGO_CODIGO)]


# --- esquemas -----------------------------------------------------------------------------------


class EstadisticasRespuesta(BaseModel):
    n: int
    minimo: str | None
    q1: str | None
    mediana: str | None
    promedio: str | None
    maximo: str | None
    ids: list[int] = Field(description="Las observaciones de las que salen las cifras")
    otras_monedas: int = Field(description="Observaciones de la ventana en otra moneda")
    dias: int


class PropuestaRespuesta(BaseModel):
    precio: str | None
    razon: str


class ObservacionRespuesta(BaseModel):
    id: int
    fuente_tipo: str
    fuente: str
    fecha: str
    moneda: str
    precio: str
    nota: str
    responsable: str
    cuenta: bool = Field(description="Está en la moneda de la carpeta y entra en las cifras")


class EstudioRespuesta(BaseModel):
    lado: str
    codigo: str
    moneda: str
    estadisticas: EstadisticasRespuesta
    propuesta: PropuestaRespuesta
    piso: str | None = Field(description="Cobro: costo directo + administración")
    precio_unitario: str | None = Field(description="Cobro: con utilidad, sin IVA")
    observaciones: list[ObservacionRespuesta]


class ObservacionNueva(BaseModel):
    lado: Lado
    codigo: str = Field(min_length=1, max_length=_LARGO_CODIGO)
    fuente_tipo: FuenteTipo
    fuente: str = Field(max_length=1000)
    fecha: date
    precio: str = Field(max_length=60)
    nota: str = Field(default="", max_length=2000)


class Creada(BaseModel):
    id: int


class Anulada(BaseModel):
    id: int
    anulada_por: int


class AfectadosRespuesta(BaseModel):
    apus: list[str]


class UsarCompra(BaseModel):
    precio: str = Field(max_length=60)
    observacion_id: int | None = None


class UsarCompraRespuesta(BaseModel):
    lista: str


class UsarCobro(BaseModel):
    precio: str = Field(max_length=60)
    observaciones: list[int] = Field(default_factory=list, max_length=100)


class ObjetivoRespuesta(BaseModel):
    codigo: str
    precio: str
    moneda: str


class ObjetivosRespuesta(BaseModel):
    objetivos: list[ObjetivoRespuesta]


# --- traducción de errores ----------------------------------------------------------------------


def _texto(valor: Decimal | None) -> str | None:
    return None if valor is None else format(valor, "f")


def _en_centimos(valor: Decimal) -> str:
    """Un monto que siempre existe, como se muestra (`centimos` de la lógica)."""
    texto = _texto(centimos(valor))
    assert texto is not None  # `centimos` de un monto nunca es None
    return texto


def _responsable(activa: SesionActiva | None) -> str:
    return USUARIO_API if activa is None else activa.usuario


def _traducir[T](hacer: Callable[[], T]) -> T:
    """Corre `hacer` y lleva cada error de la lógica a su código HTTP (sin SQL ni rutas)."""
    try:
        return hacer()
    except NoExiste as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from None
    except (CarpetaSinMoneda, SinListaParaArmar, ObservacionAnulada) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
    except CatalogoIncompleto:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede calcular el costo de la partida con la lista para armar: le falta un "
            "precio o su rendimiento.",
        ) from None
    except (CifraInvalida, ReglaDeMercado) as error:
        raise HTTPException(422, str(error)) from None
    except ValueError:
        # Un error de programación (lado, tipo de fuente, responsable): su texto no sale.
        raise HTTPException(422, MENSAJE_INESPERADO) from None
    except SQLAlchemyError:
        # El texto de un error de base lleva el SQL y sus parámetros: no sale por la API.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, MENSAJE_BASE) from None


# --- rutas --------------------------------------------------------------------------------------


@router.get("/objetivos", response_model=ObjetivosRespuesta, dependencies=[EDITAR_HOJA])
def leer_objetivos(
    sesion: SesionDep,
    partidas: Annotated[str, Query(max_length=2000, description="Códigos separados por coma")] = "",
) -> ObjetivosRespuesta:
    """El último precio de venta objetivo de cada partida pedida que tenga uno."""
    codigos = [c.strip() for c in partidas.split(",") if c.strip()]
    filas = _traducir(lambda: objetivos(sesion, codigos))
    return ObjetivosRespuesta(
        objetivos=[
            ObjetivoRespuesta(
                codigo=f.codigo_partida, precio=_en_centimos(f.precio), moneda=f.moneda
            )
            for f in filas
        ]
    )


@router.get("/{lado}/{codigo}", response_model=EstudioRespuesta, dependencies=[EDITAR_HOJA])
def leer_estudio(
    sesion: SesionDep,
    lado: Lado,
    codigo: Codigo,
    dias: Annotated[int, Query(ge=1, le=_DIAS_MAXIMO)] = 90,
    proyecto: Annotated[str | None, Query(min_length=1, max_length=500)] = None,
) -> EstudioRespuesta:
    """Las observaciones de la ventana, sus cifras, el piso (cobro) y la propuesta."""
    hoy = ahora().date()

    def leer() -> EstudioRespuesta:
        cual = exigir_codigo(sesion, lado, codigo)
        est = estadisticas(sesion, lado=lado, codigo=cual, hoy=hoy, dias=dias)
        piso = precio_unitario = None
        if lado == "cobro":
            obra = None
            if proyecto is not None:
                encontrada = resolver_proyecto(sesion, proyecto)
                if encontrada is None:
                    raise NoExiste(f"No hay ninguna obra «{proyecto}» en esta carpeta de trabajo.")
                obra = encontrada.nombre
            piso, precio_unitario = piso_de_cobro(
                sesion, Catalogo(sesion), cual, proyecto=obra, fecha=hoy
            )
        elegida = propuesta(lado, est, piso)
        filas = observaciones_vigentes(sesion, lado=lado, codigo=cual, hoy=hoy, dias=dias)
        return EstudioRespuesta(
            lado=lado,
            codigo=cual,
            moneda=est.moneda,
            estadisticas=EstadisticasRespuesta(
                n=est.n,
                minimo=_texto(centimos(est.minimo)),
                q1=_texto(centimos(est.q1)),
                mediana=_texto(centimos(est.mediana)),
                promedio=_texto(centimos(est.promedio)),
                maximo=_texto(centimos(est.maximo)),
                ids=list(est.ids),
                otras_monedas=est.otras_monedas,
                dias=est.dias,
            ),
            propuesta=PropuestaRespuesta(precio=_texto(elegida.precio), razon=elegida.razon),
            piso=_texto(centimos(piso)),
            precio_unitario=_texto(centimos(precio_unitario)),
            observaciones=[
                ObservacionRespuesta(
                    id=f.id,
                    fuente_tipo=f.fuente_tipo,
                    fuente=f.fuente,
                    fecha=f.fecha.isoformat(),
                    moneda=f.moneda,
                    precio=format(f.precio, "f"),
                    nota=f.nota,
                    responsable=f.responsable,
                    cuenta=f.moneda == est.moneda,
                )
                for f in filas
            ],
        )

    return _traducir(leer)


@router.post("/observaciones", response_model=Creada, status_code=201, dependencies=[EDITAR_HOJA])
def registrar(sesion: SesionDeEscrituraDep, datos: ObservacionNueva, activa: Activa) -> Creada:
    """Anota un precio visto en el mercado (en la moneda de la carpeta)."""

    def escribir() -> int:
        ident = registrar_observacion(
            sesion,
            lado=datos.lado,
            codigo=datos.codigo,
            fuente_tipo=datos.fuente_tipo,
            fuente=datos.fuente,
            fecha=datos.fecha,
            precio=datos.precio,
            nota=datos.nota,
            responsable=_responsable(activa),
            ahora=ahora(),
        )
        sesion.commit()
        return ident

    return Creada(id=_traducir(escribir))


@router.post(
    "/observaciones/{observacion_id}/anular", response_model=Anulada, dependencies=[EDITAR_HOJA]
)
def anular(
    sesion: SesionDeEscrituraDep,
    observacion_id: Annotated[int, Path(ge=1)],
    activa: Activa,
) -> Anulada:
    """Anula una observación (queda su contraasiento: quién y cuándo)."""

    def escribir() -> int:
        contra = anular_observacion(
            sesion, observacion_id, responsable=_responsable(activa), ahora=ahora()
        )
        sesion.commit()
        return contra

    return Anulada(id=observacion_id, anulada_por=_traducir(escribir))


@router.get(
    "/compra/{codigo}/afectados", response_model=AfectadosRespuesta, dependencies=[EDITAR_HOJA]
)
def afectados(sesion: SesionDep, codigo: Codigo) -> AfectadosRespuesta:
    """Las partidas del catálogo que cambian de precio si cambia el del insumo."""
    return AfectadosRespuesta(apus=_traducir(lambda: apus_afectados(sesion, codigo)))


@router.post(
    "/compra/{codigo}/usar", response_model=UsarCompraRespuesta, dependencies=[EDITAR_HOJA]
)
def usar_compra(
    sesion: SesionDeEscrituraDep, codigo: Codigo, datos: UsarCompra, activa: Activa
) -> UsarCompraRespuesta:
    """Pone el precio en la lista de hoy de la carpeta (otra del día si una versión ya la usa)."""

    def escribir() -> str:
        momento = ahora()
        lista = usar_precio_de_compra(
            sesion,
            codigo,
            datos.precio,
            observacion_id=datos.observacion_id,
            fecha=momento.date(),
            responsable=_responsable(activa),
        )
        nombre = lista.nombre
        sesion.commit()
        return nombre

    return UsarCompraRespuesta(lista=_traducir(escribir))


@router.post("/cobro/{codigo}/usar", response_model=ObjetivoRespuesta, dependencies=[EDITAR_HOJA])
def usar_cobro(
    sesion: SesionDeEscrituraDep, codigo: Codigo, datos: UsarCobro, activa: Activa
) -> ObjetivoRespuesta:
    """Guarda el precio como el precio de venta objetivo de la partida."""

    def escribir() -> ObjetivoRespuesta:
        fila = usar_precio_de_cobro(
            sesion,
            codigo,
            datos.precio,
            observaciones=datos.observaciones,
            responsable=_responsable(activa),
            ahora=ahora(),
        )
        respuesta = ObjetivoRespuesta(
            codigo=fila.codigo_partida,
            precio=_en_centimos(fila.precio),
            moneda=fila.moneda,
        )
        sesion.commit()
        return respuesta

    return _traducir(escribir)
