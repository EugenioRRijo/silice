"""`/v1/procura`: la procura con fechas de una obra, sus compras y sus plazos de entrega (MP-7,
Tarea 23 del plan de montar un presupuesto; diseño §11, meta 3).

Rutas finas sobre `aplicacion.procura`, todas con `CONTROL_DE_OBRA` (arma, o la clave de API: la
procura vive en Control de obra); revisa y administra reciben 403. Operan sobre la carpeta de
trabajo de la sesión (`SesionDep`); las que escriben van con `BEGIN IMMEDIATE` y confirman aquí
(todo o nada: la compra y su observación de mercado entran juntas o ninguna).

- `GET ?proyecto=&corte=` → `{necesidades, alertas, aviso, causas_sugeridas}`. `proyecto` es el
  código o el nombre de la obra; `corte` (aaaa-mm-dd) es hoy si no se manda. Cantidades exactas
  como texto con punto decimal; fechas aaaa-mm-dd o `null` sin línea base, y entonces `aviso` lo
  dice. `causas_sugeridas`: por partida, la causa de retraso que sugiere la procura al corte
  (Tarea 24: Valuaciones la preelige con el «hasta» de la valuación como corte).
- `POST /compras` `{proyecto, descripcion, unidad, evento, fecha, cantidad, precio,
  declarar_corte}` → 204. `cantidad` y `precio` (unitario) van como texto tecleado (coma decimal,
  punto de miles), vacíos si no se declaran. Con `declarar_corte` (la casilla «Declararlo precio
  del corte», MP-7, Tarea 25), el precio de la recepción queda además como precio del corte del
  material en la obra desde la fecha de llegada, en la misma transacción: si no se puede declarar,
  tampoco se anota la compra; sin precio o en un pedido es un 422 que lo dice.
- `PUT /plazos` `{proyecto, descripcion, unidad, dias}` → 204; `dias` tecleado, entero de 0 a 365.

Errores: el 422 de forma es un mensaje fijo que no repite lo enviado; el 422 de una regla
(`CifraInvalida`, `ReglaDeProcura` y las del estudio de mercado) lleva su mensaje, y cualquier otro
`ValueError` un texto fijo; 404 lo que no existe (obra o material); 409 sin moneda en la carpeta o
un precio del corte que la obra no admite (sin línea base o en otra moneda); 503 fijo ante un fallo
de la base. `Cache-Control: no-store` en toda respuesta. Quien escribe consta como la cuenta de la
sesión (o `USUARIO_API` con la clave).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from api.dependencias import USUARIO_API, SesionDeEscrituraDep, SesionDep
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion.cifras import CifraInvalida, cifra_escrita
from aplicacion.listas_para_armar import moneda_de_la_carpeta
from aplicacion.mercado import CarpetaSinMoneda, NoExiste, ReglaDeMercado
from aplicacion.precios_declarados import ReglaDelCorte, declarar_precio_del_corte
from aplicacion.procura import (
    NecesidadDeInsumo,
    ReglaDeProcura,
    alertas_de_compra,
    causas_sugeridas,
    fijar_plazo,
    procura,
    registrar_compra,
)
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_FORMA = (
    "Los datos de la procura no son válidos: el evento es pedida o recibida; las fechas van como "
    "aaaa-mm-dd; la cantidad, el precio y el plazo van como texto; la descripción admite hasta "
    "300 caracteres y la unidad hasta 20."
)
MENSAJE_BASE = "No se pudo leer ni guardar la procura de la carpeta de trabajo."
MENSAJE_INESPERADO = "No se pudo procesar la procura con esos datos."
#: La casilla «Declararlo precio del corte» sin precio, o en un pedido (Tarea 25). El primero
#: empieza por «El precio» para que la pantalla lo diga junto al campo del precio.
MENSAJE_CORTE_SIN_PRECIO = "El precio unitario hace falta para declararlo precio del corte."
MENSAJE_CORTE_EN_PEDIDO = "Solo el precio de una compra recibida se declara precio del corte."
_LARGO_OBRA = 500
_LARGO_DESCRIPCION = 300
_LARGO_UNIDAD = 20
_LARGO_CIFRA = 60

#: Los valores de `aplicacion.procura.EVENTOS`.
Evento = Literal["pedida", "recibida"]


class _RutaProcura(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (diseño de la Hoja §1.3-7)."""

    mensaje_por_omision = MENSAJE_FORMA


CONTROLAR = Depends(exigir_clave_o_sesion(Accion.CONTROL_DE_OBRA))
router = APIRouter(
    prefix="/v1/procura", tags=["procura"], route_class=_RutaProcura, dependencies=[CONTROLAR]
)
Activa = Annotated[SesionActiva | None, CONTROLAR]
Obra = Annotated[str, Field(min_length=1, max_length=_LARGO_OBRA)]
Descripcion = Annotated[str, Field(min_length=1, max_length=_LARGO_DESCRIPCION)]
Unidad = Annotated[str, Field(max_length=_LARGO_UNIDAD)]


# --- esquemas -----------------------------------------------------------------------------------


class NecesidadRespuesta(BaseModel):
    descripcion: str
    unidad: str
    cantidad: str = Field(description="Exacta, con punto decimal")
    partidas: list[str]
    se_necesita: str | None = Field(description="aaaa-mm-dd; null sin línea base")
    pedir_a_mas_tardar: str | None
    plazo: int = Field(description="Días hábiles de entrega")
    pedida: str | None = Field(description="El primer pedido registrado")
    recibida: str | None = Field(description="La primera recepción registrada")


class AlertaRespuesta(BaseModel):
    severidad: Literal["AVISO", "ERROR"]
    texto: str


class CausaSugeridaRespuesta(BaseModel):
    partida: str = Field(description="Código de la partida")
    causa: str = Field(description="Clave de la causa de retraso (la de `/v1/control/valuaciones`)")


class ProcuraRespuesta(BaseModel):
    necesidades: list[NecesidadRespuesta]
    alertas: list[AlertaRespuesta]
    aviso: str | None = Field(description="Por qué no hay fechas, si no las hay")
    causas_sugeridas: list[CausaSugeridaRespuesta] = Field(
        description=(
            "Por partida, la causa de retraso que sugiere la procura al corte (una compra que"
            " llegó después de que la partida empezara); Valuaciones la preelige. Solo las que"
            " tienen una."
        )
    )


class CompraNueva(BaseModel):
    proyecto: Obra
    descripcion: Descripcion
    unidad: Unidad
    evento: Evento
    fecha: date
    cantidad: str = Field(
        default="", max_length=_LARGO_CIFRA, description="Cantidad recibida, en la unidad"
    )
    precio: str = Field(
        default="",
        max_length=_LARGO_CIFRA,
        description="Precio unitario (por unidad del material), en la moneda de la carpeta",
    )
    declarar_corte: bool = Field(
        default=False,
        description="Declarar el precio de la recepción como precio del corte de la obra",
    )


class PlazoNuevo(BaseModel):
    proyecto: Obra
    descripcion: Descripcion
    unidad: Unidad
    dias: str = Field(max_length=_LARGO_CIFRA)


# --- traducción ---------------------------------------------------------------------------------


def _fecha(valor: date | None) -> str | None:
    return None if valor is None else valor.isoformat()


def _necesidad(necesidad: NecesidadDeInsumo) -> NecesidadRespuesta:
    return NecesidadRespuesta(
        descripcion=necesidad.descripcion,
        unidad=necesidad.unidad,
        cantidad=format(necesidad.cantidad, "f"),
        partidas=list(necesidad.partidas),
        se_necesita=_fecha(necesidad.se_necesita),
        pedir_a_mas_tardar=_fecha(necesidad.pedir_a_mas_tardar),
        plazo=necesidad.plazo,
        pedida=_fecha(necesidad.pedida),
        recibida=_fecha(necesidad.recibida),
    )


def _responsable(activa: SesionActiva | None) -> str:
    return USUARIO_API if activa is None else activa.usuario


def _traducir[T](hacer: Callable[[], T]) -> T:
    """Corre `hacer` y lleva cada error de la lógica a su código HTTP (sin SQL ni rutas)."""
    try:
        return hacer()
    except NoExiste as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from None
    except (CarpetaSinMoneda, ReglaDelCorte) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
    except (CifraInvalida, ReglaDeProcura, ReglaDeMercado) as error:
        raise HTTPException(422, str(error)) from None
    except ValueError:
        # Un error de programación (evento, responsable): su texto no sale.
        raise HTTPException(422, MENSAJE_INESPERADO) from None
    except SQLAlchemyError:
        # El texto de un error de base lleva el SQL y sus parámetros: no sale por la API.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, MENSAJE_BASE) from None


# --- rutas --------------------------------------------------------------------------------------


@router.get("", response_model=ProcuraRespuesta)
def leer_procura(
    sesion: SesionDep,
    proyecto: Annotated[str, Query(min_length=1, max_length=_LARGO_OBRA)],
    corte: date | None = None,
) -> ProcuraRespuesta:
    """Los materiales de la obra con sus fechas, y las alertas al corte."""
    dia = corte or ahora().date()

    def leer() -> ProcuraRespuesta:
        leida = procura(sesion, proyecto)
        alertas = alertas_de_compra(leida.necesidades, dia, leida.feriados)
        causas = causas_sugeridas(sesion, proyecto, dia)
        return ProcuraRespuesta(
            necesidades=[_necesidad(n) for n in leida.necesidades],
            alertas=[AlertaRespuesta(severidad=a.severidad, texto=a.texto) for a in alertas],
            aviso=leida.aviso,
            causas_sugeridas=[
                CausaSugeridaRespuesta(partida=partida, causa=causa)
                for partida, causa in causas.items()
            ],
        )

    return _traducir(leer)


@router.post("/compras", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def registrar(sesion: SesionDeEscrituraDep, datos: CompraNueva, activa: Activa) -> Response:
    """Anota un pedido o una recepción de un material de la obra (y, con la casilla, declara su
    precio del corte)."""

    def escribir() -> None:
        if datos.declarar_corte and datos.evento != "recibida":
            raise ReglaDeProcura(MENSAJE_CORTE_EN_PEDIDO)
        if datos.declarar_corte and not datos.precio.strip():
            raise ReglaDeProcura(MENSAJE_CORTE_SIN_PRECIO)
        momento = ahora()
        responsable = _responsable(activa)
        registrar_compra(
            sesion,
            datos.proyecto,
            descripcion=datos.descripcion,
            unidad=datos.unidad,
            evento=datos.evento,
            fecha=datos.fecha,
            cantidad=datos.cantidad,
            precio=datos.precio,
            responsable=responsable,
            ahora=momento,
        )
        if datos.declarar_corte:
            # La compra ya pasó sus reglas: el precio es positivo, la fecha no es posterior a hoy y
            # está en la moneda de la carpeta, que debe ser la de la obra (no se convierte).
            declarar_precio_del_corte(
                sesion,
                datos.proyecto,
                descripcion=datos.descripcion,
                unidad=datos.unidad,
                precio=cifra_escrita(datos.precio),
                fecha=datos.fecha,
                fuente=f"Procura: compra recibida el {datos.fecha:%d/%m/%Y}",
                responsable=responsable,
                ahora=momento,
                moneda=moneda_de_la_carpeta(sesion, momento.date()),
            )
        sesion.commit()

    _traducir(escribir)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/plazos", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def plazo(sesion: SesionDeEscrituraDep, datos: PlazoNuevo) -> Response:
    """Fija el plazo de entrega (días hábiles) de un material de la obra."""

    def escribir() -> None:
        fijar_plazo(
            sesion,
            datos.proyecto,
            descripcion=datos.descripcion,
            unidad=datos.unidad,
            dias=datos.dias,
        )
        sesion.commit()

    _traducir(escribir)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
