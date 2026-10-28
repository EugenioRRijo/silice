"""`/v1/mercado`: el estudio de mercado y «Usar este precio» (MP-5, Tarea 14 del plan de montar un
presupuesto; diseño §5.1 y §10, D-MP2).

Rutas finas sobre `aplicacion.mercado`, todas con `EDITAR_HOJA` (arma, o la clave de API: es
trabajo de quien arma); revisa y administra reciben 403. Operan sobre la carpeta de trabajo de la
sesión (`SesionDep`); las que escriben van con `BEGIN IMMEDIATE` y confirman aquí (todo o nada).

- `GET /{lado}/{codigo}?dias=90&proyecto=` → `{lado, codigo, moneda, estadisticas, propuesta,
  piso, precio_unitario, observaciones}`. Las estadísticas, la propuesta, el piso y el precio con
  utilidad van en céntimos (lo que se muestra); el precio de cada observación, exacto y tal como se
  anotó (`precio`, `moneda`). Una observación en otra moneda se cita **convertida** a la de la
  carpeta con la tasa del BCV del mismo día de la observación (Tarea D3): trae su `equivalencia`
  (la misma de D2) y entra en las cifras con el valor convertido (`estadisticas.convertidas`). Sin
  tasa de ese día `sin_tasa` dice «sin tasa del BCV del dd/mm/aaaa», no entra en las cifras y se
  cuenta en `estadisticas.sin_tasa` (antes `otras_monedas`). En cobro,
  `proyecto` (código o nombre de la obra abierta) da los parámetros del piso.
- `POST /observaciones` → 201 `{id}`; `POST /observaciones/{id}/anular` → 200 `{id, anulada_por}`.
- `GET /compra/{codigo}/afectados` → `{apus}` (lo que se muestra antes de «Usar este precio»).
- `POST /compra/{codigo}/usar` `{precio, observacion_id, declarar_en}` → 200 `{lista, corte,
  equivalencia}` (el nombre de la lista). Con `declarar_en` (el código o el nombre de una obra), el
  precio queda además como precio del corte de ese material en la obra desde hoy (MP-7, Tarea 25),
  en la misma transacción: si no se puede declarar, tampoco cambia la lista; `corte` es la frase que
  lo confirma (`null` sin `declarar_en`). Si la obra trabaja en la otra moneda, el precio se
  convierte con la tasa del BCV de hoy (Tarea D2) y `equivalencia` trae la cuenta; sin esa tasa, 409
  y no cambia nada.
- `POST /cobro/{codigo}/usar` `{precio, observaciones}` → 200 `{codigo, precio, moneda}`.
- `GET /objetivos?partidas=A,B&pu=A:2074.44,B:30&moneda=Bs` → `{objetivos: [{codigo, precio, moneda,
  margen, equivalencia, sin_tasa}]}`. `pu` son los precios unitarios que la Hoja ya tiene (con
  utilidad, sin IVA; decimal con punto) y `moneda` la de esos precios; `margen` lo calcula
  `margen()` de la lógica (Tarea 16: el front no calcula) y va vacío sin el precio unitario de esa
  partida, con un precio unitario de cero, con uno tan pequeño que el margen no cabe en la
  precisión, o con el objetivo en otra moneda sin tasa de su día. Un objetivo en otra moneda que
  `moneda` se convierte con la tasa del BCV del mismo día en que se fijó (`fecha_hora`, Tarea D3b;
  nada se guarda, se recalcula en cada lectura): trae su `equivalencia` (la misma de D2) y el margen
  se calcula sobre el convertido; sin tasa de ese día `margen` va vacío y `sin_tasa` dice «sin tasa
  del BCV del dd/mm/aaaa» (sin 409: una partida sin tasa no tumba la tanda). En la misma moneda
  ambos van vacíos. Un `pu` mal formado es un 422 con su propio mensaje fijo, y una
  `moneda` que no sea Bs ni USD (`MONEDAS` del núcleo) también, sin repetir lo enviado.

Errores: el 422 de forma (lado, fuente, fecha, precio que no es texto, códigos largos, ventana
fuera de 1 a 3.650 días) es un mensaje fijo que no repite lo enviado; el 422 de una regla
(`CifraInvalida` y `ReglaDeMercado`: fuente, nota, fecha futura, precio no positivo, objetivo de
más de 2 decimales, observación ajena o de otra moneda) lleva el mensaje de `aplicacion.mercado`, y
cualquier otro `ValueError` un texto fijo; 404 lo que no existe (también la obra de `declarar_en` o
un material que no está en su línea base); 409 sin moneda, sin lista para armar, una partida cuyo
costo no se puede calcular, una observación ya anulada, un precio del corte que la obra no admite
(sin línea base) o sin tasa del BCV para convertirlo a la moneda de la obra; 503 fijo ante un
fallo de la base.
`Cache-Control: no-store` en toda respuesta. Quien escribe consta como la cuenta de la sesión (o
`USUARIO_API` con la clave). Montos como texto con punto decimal, nunca como número.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from api.dependencias import USUARIO_API, SesionDeEscrituraDep, SesionDep
from api.esquemas_corte import EquivalenciaRespuesta, equivalencia_a_respuesta
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion.cifras import CifraInvalida, cifra_escrita
from aplicacion.listas_para_armar import SinListaParaArmar
from aplicacion.mercado import (
    CarpetaSinMoneda,
    NoExiste,
    ObservacionAnulada,
    ReglaDeMercado,
    anular_observacion,
    apus_afectados,
    centimos,
    convertir_o_sin_tasa,
    estadisticas,
    exigir_codigo,
    margen,
    objetivos,
    observaciones_leidas,
    piso_de_cobro,
    propuesta,
    registrar_observacion,
    usar_precio_de_cobro,
    usar_precio_de_compra,
)
from aplicacion.precios_declarados import ReglaDelCorte, declarar_desde_el_catalogo
from aplicacion.proyectos import resolver_proyecto
from core.catalog import Catalogo
from core.catalog.errores import CatalogoIncompleto
from core.catalog.moneda import MONEDAS
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_FORMA = (
    "Los datos del estudio de mercado no son válidos: el lado es compra o cobro; la fuente es "
    "proveedor, competidor, cotización, MaPreX o compra; la fecha va como aaaa-mm-dd; el precio "
    "va como texto; los códigos admiten hasta 40 caracteres y la ventana va de 1 a 3.650 días."
)
#: El 422 de `pu` en `GET /objetivos` (los precios unitarios que manda la Hoja): fijo, sin eco.
MENSAJE_PU = (
    "Los precios unitarios de la Hoja no son válidos: cada uno va como código:monto, separados "
    "por coma, con punto decimal y con la moneda de esos precios."
)
#: El 422 de `moneda` en `GET /objetivos` cuando no es una que el sistema admite: fijo, sin eco.
MENSAJE_MONEDA = "La moneda de los precios unitarios no es válida: el sistema admite Bs o USD."
MENSAJE_BASE = "No se pudo leer ni guardar el estudio de mercado de la carpeta de trabajo."
MENSAJE_INESPERADO = "No se pudo procesar el estudio de mercado con esos datos."
_LARGO_CODIGO = 40
_DIAS_MAXIMO = 3650
#: Los precios unitarios de la Hoja: un decimal con punto, sin exponente (`format(x, "f")`).
_DECIMAL_CON_PUNTO = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")

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
    convertidas: int = Field(
        description="De las que entran en las cifras, las que estaban en otra moneda (convertidas)"
    )
    sin_tasa: int = Field(
        description=(
            "Observaciones de la ventana en otra moneda sin tasa del BCV de su día: no entran en "
            "las cifras"
        )
    )
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
    cuenta: bool = Field(
        description="Entra en las cifras: está en la moneda de la carpeta o se convirtió"
    )
    equivalencia: EquivalenciaRespuesta | None = Field(
        description=(
            "Si estaba en otra moneda y hay tasa del BCV de su día: el precio original, la tasa "
            "con su fecha y fuente, y el precio convertido a la moneda de la carpeta (el que "
            "entra en las cifras); `precio` y `moneda` son siempre los originales"
        )
    )
    sin_tasa: str | None = Field(
        description="«sin tasa del BCV del dd/mm/aaaa» si no se pudo convertir (no entra en cifras)"
    )


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
    declarar_en: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Obra (código o nombre) en la que el precio queda como precio del corte",
    )


class UsarCompraRespuesta(BaseModel):
    lista: str
    corte: str | None = Field(
        default=None, description="La frase que confirma el precio del corte declarado, si se pidió"
    )
    equivalencia: EquivalenciaRespuesta | None = Field(
        default=None,
        description=(
            "Si el precio del corte se convirtió a la moneda de la obra con la tasa del BCV: el "
            "precio original, la tasa con su fecha y fuente, y el resultado"
        ),
    )


class UsarCobro(BaseModel):
    precio: str = Field(max_length=60)
    observaciones: list[int] = Field(default_factory=list, max_length=100)


class ObjetivoRespuesta(BaseModel):
    codigo: str
    precio: str
    moneda: str


class ObjetivoConMargen(ObjetivoRespuesta):
    margen: str | None = Field(
        description=(
            "(objetivo − precio unitario) / precio unitario, en % con una cifra decimal; vacío sin "
            "el precio unitario de la partida, con uno de cero o con un objetivo en otra moneda "
            "sin tasa del BCV de su día. Con el objetivo en otra moneda se calcula sobre el "
            "convertido (`equivalencia`)"
        )
    )
    equivalencia: EquivalenciaRespuesta | None = Field(
        default=None,
        description=(
            "Si el objetivo está en otra moneda que `moneda`: la cuenta con la que se convirtió "
            "(tasa del BCV del mismo día en que se fijó el objetivo, Tarea D3b); nada se guarda, "
            "se recalcula en cada lectura. Vacía en la misma moneda o sin tasa de ese día"
        ),
    )
    sin_tasa: str | None = Field(
        default=None,
        description=(
            "«sin tasa del BCV del dd/mm/aaaa» (la fecha del objetivo) si estaba en otra moneda y "
            "no hay tasa de ese día; vacío en los demás casos"
        ),
    )


class ObjetivosRespuesta(BaseModel):
    objetivos: list[ObjetivoConMargen]


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
    except (CarpetaSinMoneda, SinListaParaArmar, ObservacionAnulada, ReglaDelCorte) as error:
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


def _pu_invalido() -> HTTPException:
    return HTTPException(422, MENSAJE_PU)


def _precios_unitarios(pu: str, moneda: str | None) -> dict[str, Decimal]:
    """`CODIGO:2074.44,…` → {código: precio}. El código va antes del último «:»; la misma partida
    con dos precios distintos, un decimal que no es con punto o `pu` sin `moneda` es un 422 de
    forma (sin repetir lo enviado)."""
    precios: dict[str, Decimal] = {}
    for parte in (p.strip() for p in pu.split(",")):
        if not parte:
            continue
        codigo, separador, texto = parte.rpartition(":")
        codigo = codigo.strip()
        texto = texto.strip()
        if (
            not separador
            or not codigo
            or len(codigo) > _LARGO_CODIGO
            or _DECIMAL_CON_PUNTO.fullmatch(texto) is None
        ):
            raise _pu_invalido()
        valor = Decimal(texto)
        if precios.setdefault(codigo, valor) != valor:
            raise _pu_invalido()
    if precios and moneda is None:
        raise _pu_invalido()
    return precios


def _margen(objetivo: Decimal, precio_unitario: Decimal | None) -> str | None:
    if precio_unitario is None or precio_unitario <= 0:
        return None
    try:
        valor = margen(objetivo, precio_unitario)
    except InvalidOperation:
        # Un precio unitario tan pequeño que el margen no cabe en la precisión: sin margen (no un
        # 500 que tumbe la tanda entera de objetivos).
        return None
    # −0,0 (un margen que redondea a cero desde abajo) se dice 0,0: el signo no significa nada.
    return format(abs(valor) if valor == 0 else valor, "f")


# --- rutas --------------------------------------------------------------------------------------


@router.get("/objetivos", response_model=ObjetivosRespuesta, dependencies=[EDITAR_HOJA])
def leer_objetivos(
    sesion: SesionDep,
    partidas: Annotated[str, Query(max_length=2000, description="Códigos separados por coma")] = "",
    pu: Annotated[
        str,
        Query(
            max_length=4000,
            description=(
                "Precios unitarios de la Hoja (con utilidad, sin IVA) como CODIGO:monto separados "
                "por coma, decimal con punto"
            ),
        ),
    ] = "",
    moneda: Annotated[
        str | None,
        Query(min_length=1, max_length=10, description="Moneda de los precios unitarios de `pu`"),
    ] = None,
) -> ObjetivosRespuesta:
    """El último precio de venta objetivo de cada partida pedida que tenga uno y, con el precio
    unitario de la Hoja, su margen. Un objetivo en otra moneda que `moneda` se convierte con la
    tasa del BCV del día en que se fijó (D3b) y el margen se calcula sobre el convertido."""
    codigos = [c.strip() for c in partidas.split(",") if c.strip()]
    if moneda is not None and moneda not in MONEDAS:
        raise HTTPException(422, MENSAJE_MONEDA)
    precios = _precios_unitarios(pu, moneda)
    filas = _traducir(lambda: objetivos(sesion, codigos))
    respuesta: list[ObjetivoConMargen] = []
    for f in filas:
        valor, equivalencia, sin_tasa = f.precio, None, None
        if moneda is not None and f.moneda != moneda:
            # La tasa del día en que se fijó el objetivo (D3b); sin ella, sin margen y sin 409.
            equivalencia, sin_tasa = convertir_o_sin_tasa(
                sesion, f.precio, f.moneda, moneda, f.fecha_hora.date()
            )
            valor = None if equivalencia is None else equivalencia.convertido
        respuesta.append(
            ObjetivoConMargen(
                codigo=f.codigo_partida,
                precio=_en_centimos(f.precio),
                moneda=f.moneda,
                margen=None if valor is None else _margen(valor, precios.get(f.codigo_partida)),
                equivalencia=None
                if equivalencia is None
                else equivalencia_a_respuesta(equivalencia),
                sin_tasa=sin_tasa,
            )
        )
    return ObjetivosRespuesta(objetivos=respuesta)


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
        filas = observaciones_leidas(sesion, lado, cual, hoy, dias)
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
                convertidas=est.convertidas,
                sin_tasa=est.sin_tasa,
                dias=est.dias,
            ),
            propuesta=PropuestaRespuesta(precio=_texto(elegida.precio), razon=elegida.razon),
            piso=_texto(centimos(piso)),
            precio_unitario=_texto(centimos(precio_unitario)),
            observaciones=[
                ObservacionRespuesta(
                    id=o.fila.id,
                    fuente_tipo=o.fila.fuente_tipo,
                    fuente=o.fila.fuente,
                    fecha=o.fila.fecha.isoformat(),
                    moneda=o.fila.moneda,
                    precio=format(o.fila.precio, "f"),
                    nota=o.fila.nota,
                    responsable=o.fila.responsable,
                    cuenta=o.cuenta,
                    equivalencia=(
                        None if o.equivalencia is None else equivalencia_a_respuesta(o.equivalencia)
                    ),
                    sin_tasa=o.sin_tasa,
                )
                for o in filas
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

    def escribir() -> UsarCompraRespuesta:
        momento = ahora()
        responsable = _responsable(activa)
        lista = usar_precio_de_compra(
            sesion,
            codigo,
            datos.precio,
            observacion_id=datos.observacion_id,
            fecha=momento.date(),
            responsable=responsable,
        )
        corte = equivalencia = None
        if datos.declarar_en is not None:
            # El precio ya pasó las reglas del estudio de mercado; está en la moneda de la lista. Si
            # la obra trabaja en la otra, se convierte con la tasa del BCV de hoy (o es un 409).
            corte, convertido = declarar_desde_el_catalogo(
                sesion,
                datos.declarar_en,
                codigo,
                precio=cifra_escrita(datos.precio),
                fecha=momento.date(),
                fuente=(
                    f"Estudio de mercado: observación n.º {datos.observacion_id}"
                    if datos.observacion_id is not None
                    else "Estudio de mercado: precio propio"
                ),
                responsable=responsable,
                ahora=momento,
                moneda=lista.moneda,
            )
            if convertido is not None:
                equivalencia = equivalencia_a_respuesta(convertido)
        respuesta = UsarCompraRespuesta(lista=lista.nombre, corte=corte, equivalencia=equivalencia)
        sesion.commit()
        return respuesta

    return _traducir(escribir)


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
