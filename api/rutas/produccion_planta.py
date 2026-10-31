"""`/v1/produccion`, la parte de la planta: costos, recetas, producciones y cálculos (plan vial).

Mismo prefijo, misma etiqueta, misma puerta (`OPERAR_ARENERA`, el mismo objeto que en
`api.rutas.produccion`, así FastAPI la evalúa una sola vez), `RutaSinCache` y reglas de frontera
de `api.rutas.produccion`, de donde salieron estas rutas sin cambiar su comportamiento (plan vial,
Tarea 4, a pedido del árbitro de la Tarea 3: el router pasaba de 900 líneas). Se registra justo
después de aquél en `api.main`, así el orden de `docs/api.json` no cambia.

- **Hora del servidor**: `registrado` de costos, recetas y producciones la pone el servidor con
  `api.rutas.produccion._ahora`, que se busca en su módulo en cada llamada (las pruebas la fijan
  allí); el cuerpo no lleva `ahora` (si lo trae, se ignora).
- Las rutas de `/costos` y `/calculos` suman una segunda puerta del mismo tipo, `REGISTRAR_COSTOS`
  (`Accion.REGISTRAR_COSTOS_PRODUCCION`, hoy los mismos roles): se exigen las dos y la sesión se
  toma de ésta. Un cálculo lee los costos, por eso comparte su puerta.
- **Cálculo del costo por tonelada** (Tarea 4): `POST /calculos` lee la instalación y, para las
  tasas BCV y la lista de precios, la carpeta del caso de la petición (`SesionDep`: la elegida por
  la ficha o la del proceso). Responde el costo exacto (texto) y el presentado (dos decimales, mitad
  hacia arriba), con la instantánea guardada. Falta de tasa, de precio o de costos: 422 con el
  mensaje, sin guardar nada. Un mes sin producción se calcula (todo pasa al mes siguiente, Tarea
  4b). Cálculo inexistente: 404.
- **Publicar** (Tarea 5): `POST /calculos/{id}/publicar` suma la puerta `PUBLICAR_COSTO`
  (`Accion.PUBLICAR_COSTO_PROPIO`, solo administrador con cuenta: la clave de API recibe 403) a la
  del router. La empresa es la de Administración (`empresa_propia`). Crea una lista de empresa
  nueva en la carpeta del caso y la confirma aquí; la hora es la del servidor.
- **Tarea 4b** (respuestas de Eugenio): `GET /calculos?periodo=AAAA-MM` (periodo opcional) lista
  los cálculos, del más reciente al más viejo, con su publicación (`publicado`: lista, carpeta y
  hora, o `null`); `GET /calculos/{id}` añade el mismo `publicado`. Cada cálculo se publica una
  sola vez: el segundo intento es 409 sin escribir nada; un cálculo sin costo por tonelada (un mes
  sin producción) es 422. La publicación se anota en la instalación en la misma operación: aquí se
  confirma la carpeta y, al volver, la dependencia confirma la instalación; si la carpeta falla, la
  instalación se deshace y no queda publicación.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from api.acceso_modulos import requiere_modulo
from api.admin_acceso import administrar
from api.dependencias import (
    USUARIO_API,
    SesionDep,
    SesionInstalacionDep,
    ruta_de_url,
    url_de_la_peticion,
)
from api.rutas import produccion as arenera
from api.rutas.produccion import OPERAR_ARENERA, UsuarioDep, _decimal, _fecha
from api.sesion_web import exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from aplicacion.costo_propio import (
    CalculoGuardado,
    CalculoInexistente,
    CalculoYaPublicado,
    Publicacion,
    calcular_periodo,
    calculo_guardado,
    calculos_registrados,
    exigir_publicable,
    lista_base_del_periodo,
    publicacion_de,
    publicar_calculo,
)
from produccion.costo import presentar
from produccion.costos import (
    CostoDelPeriodo,
    CostoInexistente,
    CostoRegistrado,
    CostoYaAnulado,
    anular_costo,
    costos_del_periodo,
    registrar_costo,
    totales_por_centro,
)
from produccion.fuentes import MAX_COMPONENTES, MAX_PESOS
from produccion.receta import (
    Componente,
    Receta,
    producido_en_periodo,
    producir_con_receta,
    receta_vigente,
    registrar_receta,
)
from seguridad import empresas
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

#: La puerta de los costos del periodo (plan vial, Tarea 1): misma regla de entrada, con su propia
#: acción. Se suma a la del router; `_usuario_costos` la reutiliza para no evaluarla dos veces.
REGISTRAR_COSTOS = exigir_clave_o_sesion(Accion.REGISTRAR_COSTOS_PRODUCCION)
#: La puerta de publicar un costo propio al catálogo (plan vial, Tarea 5): solo el administrador.
PUBLICAR_COSTO = administrar(Accion.PUBLICAR_COSTO_PROPIO)

router = APIRouter(
    prefix="/v1/produccion",
    tags=["produccion"],
    dependencies=[Depends(OPERAR_ARENERA), Depends(requiere_modulo("produccion"))],
    route_class=RutaSinCache,  # costos y recetas no se guardan en el navegador
)

__all__ = ["PUBLICAR_COSTO", "REGISTRAR_COSTOS", "router"]


def _usuario_publica(activa: Annotated[SesionActiva, Depends(PUBLICAR_COSTO)]) -> str:
    return activa.usuario


UsuarioPublicaDep = Annotated[str, Depends(_usuario_publica)]


def _usuario_costos(activa: Annotated[SesionActiva | None, Depends(REGISTRAR_COSTOS)]) -> str:
    return USUARIO_API if activa is None else activa.usuario


UsuarioCostosDep = Annotated[str, Depends(_usuario_costos)]


# --- Esquemas ------------------------------------------------------------------------------------


class CostoEntrada(BaseModel):
    periodo: str  # AAAA-MM
    centro: str  # "cantera" o "planta"
    concepto: str
    monto: str  # decimal con punto; la coma es cosa del front
    moneda: str  # "Bs" o "USD"
    fecha: str  # ISO, dentro del periodo
    fuente: str
    nota: str = ""


class ComponenteEntrada(BaseModel):
    codigo: str
    cantidad_por_t: str  # decimal con punto, por tonelada de mezcla
    unidad: str  # "t" o "l"
    tipo: str  # "propio" o "comprado"


class RecetaEntrada(BaseModel):
    producto: str  # código del material que se produce
    componentes: list[ComponenteEntrada] = Field(max_length=MAX_COMPONENTES)
    fuente: str
    vigente_desde: str  # ISO, AAAA-MM-DD


class RecetaCreada(BaseModel):
    id: int


class RecetaRespuesta(BaseModel):
    id: int
    producto: str
    componentes: list[ComponenteEntrada]
    fuente: str
    vigente_desde: str


class ProduccionEntrada(BaseModel):
    producto: str
    toneladas: str  # decimal con punto
    fecha: str  # ISO, AAAA-MM-DD


class ProduccionCreada(BaseModel):
    movimientos: list[int]  # la entrada del producto y luego un consumo por componente propio


class ProducidoRespuesta(BaseModel):
    codigo: str
    toneladas: str  # decimal con punto, entradas del periodo pasadas a toneladas


class AnularCostoEntrada(BaseModel):
    motivo: str


class CostoCreado(BaseModel):
    id: int


class TotalDeCostos(BaseModel):
    centro: str
    moneda: str
    total: str  # decimal con punto, suma exacta de los costos vigentes


class CalculoDeCostoEntrada(BaseModel):
    periodo: str  # AAAA-MM
    moneda: str  # "Bs" o "USD", la del cálculo
    #: reparto de la cantera por pesos (D-V-1, opcional): código del agregado -> peso con punto
    pesos: dict[str, str] | None = Field(default=None, max_length=MAX_PESOS)


class PublicacionCreada(BaseModel):
    id: int  # la lista de empresa nueva
    nombre: str


class CostoDeProducto(BaseModel):
    codigo: str
    por_tonelada: str  # exacto, como se guardó
    presentado: str  # dos decimales, mitad hacia arriba


class PublicadoRespuesta(BaseModel):
    lista_id: int  # la lista de empresa donde quedó
    caso: str  # el nombre de la carpeta de trabajo
    registrado: str  # hora del servidor, ISO


class CalculoDeCostoRespuesta(BaseModel):
    id: int
    periodo: str
    moneda: str
    huella: str  # SHA-256 de la instantánea
    usuario: str
    registrado: str
    productos: list[CostoDeProducto]  # por código
    instantanea: dict[str, Any]  # entradas y resultado, decimales como texto
    publicado: PublicadoRespuesta | None = None  # Tarea 4b: una sola publicación por cálculo


class CalculoResumen(BaseModel):
    id: int
    periodo: str
    moneda: str
    usuario: str
    registrado: str
    huella: str
    publicado: PublicadoRespuesta | None


class CostoRespuesta(BaseModel):
    id: int
    periodo: str
    centro: str
    concepto: str
    monto: str
    moneda: str
    fecha: str
    fuente: str
    nota: str
    usuario: str
    registrado: str
    anulado: bool
    anula_id: int | None
    motivo: str


# --- Costos del periodo (plan vial, Tarea 1) -----------------------------------------------------


def _costo_respuesta(r: CostoRegistrado) -> CostoRespuesta:
    c = r.costo
    return CostoRespuesta(
        id=r.id,
        periodo=c.periodo,
        centro=c.centro,
        concepto=c.concepto,
        monto=format(c.monto, "f"),
        moneda=c.moneda,
        fecha=c.fecha.isoformat(),
        fuente=c.fuente,
        nota=c.nota,
        usuario=r.usuario,
        registrado=r.registrado.isoformat(),
        anulado=r.anulado,
        anula_id=r.anula_id,
        motivo=r.motivo,
    )


@router.post(
    "/costos",
    response_model=CostoCreado,
    status_code=201,
    dependencies=[Depends(REGISTRAR_COSTOS)],
)
def registrar_un_costo(
    entrada: CostoEntrada, sesion: SesionInstalacionDep, usuario: UsuarioCostosDep
) -> CostoCreado:
    """Registra un costo del periodo (cantera o planta). Monto como texto con punto; periodo,
    centro, concepto, moneda, fecha o fuente inválidos: 422. No guarda nada si algo falla."""
    costo = CostoDelPeriodo(
        periodo=entrada.periodo.strip(),
        centro=entrada.centro.strip(),
        concepto=entrada.concepto.strip(),
        monto=_decimal(entrada.monto, "monto"),
        moneda=entrada.moneda.strip(),
        fecha=_fecha(entrada.fecha, "fecha"),
        fuente=entrada.fuente,
        nota=entrada.nota,
    )
    return CostoCreado(id=registrar_costo(sesion, costo, usuario=usuario, ahora=arenera._ahora()))


@router.get(
    "/costos", response_model=list[CostoRespuesta], dependencies=[Depends(REGISTRAR_COSTOS)]
)
def listar_costos(
    sesion: SesionInstalacionDep,
    periodo: Annotated[str, Query(description="Periodo AAAA-MM")],
    incluir_anulados: Annotated[
        bool, Query(description="También los anulados y sus anulaciones")
    ] = False,
) -> list[CostoRespuesta]:
    """Los costos del periodo en orden de registro; por omisión solo los vigentes."""
    filas = costos_del_periodo(sesion, periodo.strip(), incluir_anulados=incluir_anulados)
    return [_costo_respuesta(f) for f in filas]


@router.get(
    "/costos/totales",
    response_model=list[TotalDeCostos],
    dependencies=[Depends(REGISTRAR_COSTOS)],
)
def totales_de_costos(
    sesion: SesionInstalacionDep,
    periodo: Annotated[str, Query(description="Periodo AAAA-MM")],
) -> list[TotalDeCostos]:
    """Total vigente del periodo por centro y moneda, sin convertir; los anulados no suman."""
    totales = totales_por_centro(sesion, periodo.strip())
    return [TotalDeCostos(centro=c, moneda=m, total=format(t, "f")) for c, m, t in totales]


@router.post(
    "/costos/{costo_id}/anular",
    response_model=CostoCreado,
    status_code=201,
    dependencies=[Depends(REGISTRAR_COSTOS)],
)
def anular_un_costo(
    costo_id: int,
    entrada: AnularCostoEntrada,
    sesion: SesionInstalacionDep,
    usuario: UsuarioCostosDep,
) -> CostoCreado:
    """Anula un costo con un registro nuevo; el original no se borra. Inexistente: 404; ya
    anulado: 409; sin motivo: 422."""
    try:
        nuevo = anular_costo(
            sesion, costo_id, motivo=entrada.motivo, usuario=usuario, ahora=arenera._ahora()
        )
    except CostoInexistente as error:
        raise HTTPException(404, str(error)) from None
    except CostoYaAnulado as error:
        raise HTTPException(409, str(error)) from None
    return CostoCreado(id=nuevo)


# --- Receta de la planta y consumos (plan vial, Tarea 3) -----------------------------------------


def _receta_respuesta(r: Receta) -> RecetaRespuesta:
    return RecetaRespuesta(
        id=r.id,
        producto=r.producto,
        componentes=[
            ComponenteEntrada(
                codigo=c.codigo,
                cantidad_por_t=format(c.cantidad_por_t, "f"),
                unidad=c.unidad,
                tipo=c.tipo,
            )
            for c in r.componentes
        ],
        fuente=r.fuente,
        vigente_desde=r.vigente_desde.isoformat(),
    )


@router.post("/recetas", response_model=RecetaCreada, status_code=201)
def registrar_una_receta(
    entrada: RecetaEntrada, sesion: SesionInstalacionDep, usuario: UsuarioDep
) -> RecetaCreada:
    """Registra una receta de la planta; una receta nueva no cambia las anteriores. Las toneladas
    de componentes por tonelada de mezcla deben sumar 1 (con tolerancia); si no, 422 con la suma."""
    componentes = [
        Componente(
            codigo=c.codigo,
            cantidad_por_t=_decimal(c.cantidad_por_t, "cantidad_por_t"),
            unidad=c.unidad.strip(),
            tipo=c.tipo.strip(),
        )
        for c in entrada.componentes
    ]
    nueva = registrar_receta(
        sesion,
        entrada.producto,
        componentes,
        fuente=entrada.fuente,
        vigente_desde=_fecha(entrada.vigente_desde, "vigente_desde"),
        usuario=usuario,
        ahora=arenera._ahora(),
    )
    return RecetaCreada(id=nueva)


@router.get("/recetas/vigente", response_model=RecetaRespuesta)
def ver_receta_vigente(
    sesion: SesionInstalacionDep,
    producto: Annotated[str, Query(description="Código del producto")],
    fecha: Annotated[str, Query(description="Fecha ISO, AAAA-MM-DD")],
) -> RecetaRespuesta:
    """La receta que rige para el producto en esa fecha; 404 si no hay ninguna."""
    receta = receta_vigente(sesion, producto, _fecha(fecha, "fecha"))
    if receta is None:
        raise HTTPException(
            404, f"No hay receta vigente de {producto.strip()[:40]} el {fecha.strip()[:10]}."
        )
    return _receta_respuesta(receta)


@router.post("/producciones", response_model=ProduccionCreada, status_code=201)
def producir_mezcla(
    entrada: ProduccionEntrada, sesion: SesionInstalacionDep, usuario: UsuarioDep
) -> ProduccionCreada:
    """Produce el producto con la receta vigente en la fecha: registra su entrada y un consumo por
    cada componente propio. Sin receta vigente o con un material que no existe: 422, sin dejar
    nada."""
    movimientos = producir_con_receta(
        sesion,
        entrada.producto,
        _decimal(entrada.toneladas, "toneladas"),
        _fecha(entrada.fecha, "fecha"),
        usuario=usuario,
        ahora=arenera._ahora(),
    )
    return ProduccionCreada(movimientos=movimientos)


@router.get("/producido", response_model=list[ProducidoRespuesta])
def ver_producido(
    sesion: SesionInstalacionDep,
    periodo: Annotated[str, Query(description="Periodo AAAA-MM")],
) -> list[ProducidoRespuesta]:
    """Toneladas producidas en el periodo por código de material (m3 por densidad)."""
    producido = producido_en_periodo(sesion, periodo.strip())
    return [ProducidoRespuesta(codigo=c, toneladas=format(t, "f")) for c, t in producido.items()]


# --- Costo por tonelada del periodo (plan vial, Tarea 4) ------------------------------------------


def _publicado(publicacion: Publicacion | None) -> PublicadoRespuesta | None:
    if publicacion is None:
        return None
    return PublicadoRespuesta(
        lista_id=publicacion.lista_id,
        caso=publicacion.caso,
        registrado=publicacion.registrado.isoformat(),
    )


def _calculo_respuesta(
    calculo: CalculoGuardado, publicacion: Publicacion | None = None
) -> CalculoDeCostoRespuesta:
    return CalculoDeCostoRespuesta(
        id=calculo.id,
        periodo=calculo.periodo,
        moneda=calculo.moneda,
        huella=calculo.huella,
        usuario=calculo.usuario,
        registrado=calculo.registrado.isoformat() if calculo.registrado else "",
        productos=[
            CostoDeProducto(
                codigo=codigo, por_tonelada=format(valor, "f"), presentado=str(presentar(valor))
            )
            for codigo, valor in sorted(calculo.por_tonelada.items())
        ],
        instantanea=json.loads(calculo.instantanea),
        publicado=_publicado(publicacion),
    )


@router.post(
    "/calculos",
    response_model=CalculoDeCostoRespuesta,
    status_code=201,
    dependencies=[Depends(REGISTRAR_COSTOS)],
)
def calcular_costo_por_tonelada(
    entrada: CalculoDeCostoEntrada,
    sesion: SesionInstalacionDep,
    caso: SesionDep,
    usuario: UsuarioCostosDep,
) -> CalculoDeCostoRespuesta:
    """Calcula el costo por tonelada de cada producto del periodo en la moneda pedida y lo guarda
    con sus entradas (otro registro cada vez; nada se sobrescribe). Sin costos, sin la tasa BCV que
    pide algún monto (la del día de cada costo, la del cierre del mes para lo comprado) o sin precio
    de un componente comprado: 422, sin guardar. Un mes sin producción se calcula y todo pasa."""
    pesos = (
        None
        if entrada.pesos is None
        else {codigo.strip(): _decimal(peso, "pesos") for codigo, peso in entrada.pesos.items()}
    )
    calculo = calcular_periodo(
        sesion,
        caso,
        entrada.periodo.strip(),
        entrada.moneda.strip(),
        pesos=pesos,
        usuario=usuario,
        ahora=arenera._ahora(),
    )
    return _calculo_respuesta(calculo)


@router.get(
    "/calculos", response_model=list[CalculoResumen], dependencies=[Depends(REGISTRAR_COSTOS)]
)
def listar_calculos(
    sesion: SesionInstalacionDep,
    periodo: Annotated[str | None, Query(description="Periodo AAAA-MM (opcional)")] = None,
) -> list[CalculoResumen]:
    """Los cálculos guardados (del período, si se pide), del más reciente al más viejo, con su
    publicación. Período inválido o un cálculo alterado: 422."""
    filas = calculos_registrados(sesion, None if periodo is None else periodo.strip())
    return [
        CalculoResumen(
            id=c.id,
            periodo=c.periodo,
            moneda=c.moneda,
            usuario=c.usuario,
            registrado=c.registrado.isoformat() if c.registrado else "",
            huella=c.huella,
            publicado=_publicado(p),
        )
        for c, p in filas
    ]


@router.get(
    "/calculos/{calculo_id}",
    response_model=CalculoDeCostoRespuesta,
    dependencies=[Depends(REGISTRAR_COSTOS)],
)
def ver_calculo(calculo_id: int, sesion: SesionInstalacionDep) -> CalculoDeCostoRespuesta:
    """Un cálculo guardado, tal como se calculó, con su publicación. Inexistente: 404; alterado:
    422."""
    try:
        calculo = calculo_guardado(sesion, calculo_id)
    except CalculoInexistente as error:
        raise HTTPException(404, str(error)) from None
    return _calculo_respuesta(calculo, publicacion_de(sesion, calculo.id))


@router.post(
    "/calculos/{calculo_id}/publicar",
    response_model=PublicacionCreada,
    status_code=201,
    dependencies=[Depends(PUBLICAR_COSTO)],
)
def publicar_costo_propio(
    calculo_id: int,
    request: Request,
    sesion: SesionInstalacionDep,
    caso: SesionDep,
    usuario: UsuarioPublicaDep,
) -> PublicacionCreada:
    """Publica un cálculo concreto como lista de empresa nueva en la carpeta del caso: un precio por
    producto con el valor exacto del cálculo y la fuente «Producción, período AAAA-MM, cálculo n.º
    N». La empresa es la de Administración (sin ella, 422); solo una cuenta de administrador
    (la clave de API recibe 403). Parte de la lista vigente al cierre del período. Un cálculo
    alterado (huella o columnas que no coinciden), sin lista vigente o sin tasa BCV para llevarla
    a la moneda del cálculo: 422, sin escribir; inexistente: 404. Sin costo por tonelada: 422;
    ya publicado: 409, sin escribir nada (Tarea 4b). Nada se sobrescribe: cada publicación es otra
    lista, anotada en la instalación, que se confirma después de la carpeta."""
    try:
        calculo = calculo_guardado(sesion, calculo_id)
        exigir_publicable(sesion, calculo)
    except CalculoInexistente as error:
        raise HTTPException(404, str(error)) from None
    except CalculoYaPublicado as error:
        raise HTTPException(409, str(error)) from None
    propia = empresas.empresa_propia(sesion)
    if propia is None:
        raise HTTPException(422, "Configure la empresa en Administración antes de publicar.")
    ruta = ruta_de_url(url_de_la_peticion(request))
    try:
        lista = publicar_calculo(
            caso,
            calculo,
            sesion_ins=sesion,
            nombre_del_caso=ruta.name if ruta is not None else "(carpeta sin archivo)",
            base=lista_base_del_periodo(caso, calculo),
            empresa_nombre=propia.nombre,
            empresa_rif=propia.rif,
            usuario=usuario,
            ahora=arenera._ahora(),
        )
    except CalculoYaPublicado as error:  # otra publicación ganó la carrera (el `unique`)
        raise HTTPException(409, str(error)) from None
    publicada = PublicacionCreada(id=lista.id, nombre=lista.nombre)
    caso.commit()  # primero la carpeta; la instalación la confirma su dependencia al volver
    return publicada
