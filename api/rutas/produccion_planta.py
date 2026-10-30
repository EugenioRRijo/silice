"""`/v1/produccion`, la parte de la planta: costos del periodo, recetas y producciones (plan vial).

Mismo prefijo, misma etiqueta, misma puerta (`OPERAR_ARENERA`, el mismo objeto que en
`api.rutas.produccion`, así FastAPI la evalúa una sola vez), `RutaSinCache` y reglas de frontera
de `api.rutas.produccion`, de donde salieron estas rutas sin cambiar su comportamiento (plan vial,
Tarea 4, a pedido del árbitro de la Tarea 3: el router pasaba de 900 líneas). Se registra justo
después de aquél en `api.main`, así el orden de `docs/api.json` no cambia.

- **Hora del servidor**: `registrado` de costos, recetas y producciones la pone el servidor con
  `api.rutas.produccion._ahora`, que se busca en su módulo en cada llamada (las pruebas la fijan
  allí); el cuerpo no lleva `ahora` (si lo trae, se ignora).
- Las rutas de `/costos` suman una segunda puerta del mismo tipo, `REGISTRAR_COSTOS`
  (`Accion.REGISTRAR_COSTOS_PRODUCCION`, hoy los mismos roles): se exigen las dos y la sesión se
  toma de ésta.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencias import USUARIO_API, SesionInstalacionDep
from api.rutas import produccion as arenera
from api.rutas.produccion import OPERAR_ARENERA, UsuarioDep, _decimal, _fecha
from api.sesion_web import exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
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
from produccion.receta import (
    Componente,
    Receta,
    producido_en_periodo,
    producir_con_receta,
    receta_vigente,
    registrar_receta,
)
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

#: La puerta de los costos del periodo (plan vial, Tarea 1): misma regla de entrada, con su propia
#: acción. Se suma a la del router; `_usuario_costos` la reutiliza para no evaluarla dos veces.
REGISTRAR_COSTOS = exigir_clave_o_sesion(Accion.REGISTRAR_COSTOS_PRODUCCION)

router = APIRouter(
    prefix="/v1/produccion",
    tags=["produccion"],
    dependencies=[Depends(OPERAR_ARENERA)],
    route_class=RutaSinCache,  # costos y recetas no se guardan en el navegador
)

__all__ = ["REGISTRAR_COSTOS", "router"]


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
    componentes: list[ComponenteEntrada] = Field(max_length=50)
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
