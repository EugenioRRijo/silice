"""La base de las vistas de la hoja del proyecto en la interfaz nueva (T10, 3b-1; diseno §4.2).

Lo que la API arma a partir del borrador vivo sin repetir logica de la hoja: `elaborar(borrador)`
es la UNICA via de la interfaz nueva a `aplicacion.hoja.elaborar_borrador` y agrega R17 (la
conexion de cada punto) ligada al espacio que se elabora, sin guardarla en el borrador (como
`_elaborar` de la pagina clasica, P:286-296); `calculo(vivo)` lo hace una vez por `rev`;
`resumen` y `base` son los contratos `Resumen` y `BaseAbierta`. Las cifras viajan como `Monto`
`{texto, exacto}`: `texto` a dos decimales, como la clasica, y `exacto` sin notacion cientifica;
la interfaz no calcula ni redondea. Sin FastAPI ni Streamlit.

La 3b-2 anade las vistas de Espacio y metrajes, APU, Presupuesto y Plan y curva (`vista_*`): cada
una lee el borrador vivo (no la base), usa solo funciones de `aplicacion.hoja` (la copia del Plan C)
y devuelve dataclasses que la API serializa. La 3b-3 anade las demas pestanas.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext

from adapters.espacio.conexion import con_conexion
from adapters.espacio.modelo import (
    Especialidad,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoPunto,
)
from adapters.espacio.origen import TipoOrigen
from aplicacion import hoja
from aplicacion.hoja_borradores import BorradorVivo
from core.contracts import Severidad
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal


@dataclass(frozen=True, slots=True)
class Monto:
    """Una cifra: `texto` a dos decimales (como la clasica) y `exacto` sin redondear."""

    texto: str
    exacto: str


@dataclass(frozen=True, slots=True)
class HallazgosDeSeveridad:
    severidad: str
    total: int


@dataclass(frozen=True, slots=True)
class BaseAbierta:
    """Que se abrio: el proyecto, la version (o `None`: proyecto sin versiones) y como esta."""

    proyecto: str
    version: str | None
    vigente: str | None
    lista: str | None
    espacio_de: str | None
    solo_lectura: bool
    moneda: str


@dataclass(frozen=True, slots=True)
class ResumenHoja:
    """`Resumen` del contrato (§4.2): lo que muestra la barra de estado del borrador."""

    rev: int
    moneda: str
    total: Monto
    cambios: int
    pendientes_catalogo: int
    hallazgos: tuple[HallazgosDeSeveridad, ...]
    hay_plan: bool
    version_mas_nueva: str | None
    guardado_como: str | None


def monto(valor: Decimal) -> Monto:
    """`texto` como la clasica (dos decimales) y `exacto`; con precision de sobra para que una
    cifra de muchos digitos no falle al redondear (el contexto por omision tiene 28)."""
    with localcontext() as contexto:
        contexto.prec = max(60, len(valor.as_tuple().digits) + 10)
        return Monto(formatear_decimal(valor, DECIMALES_PRESENTACION), format(valor, "f"))


def version_por_omision(filas: Sequence[hoja.FilaVersion]) -> str | None:
    """La version que se preselecciona (P:417-421): entre las no descartadas (si todas lo estan,
    entre todas), la vigente; si ninguna lo es, la ultima. `None` sin versiones."""
    codigos = [f.codigo for f in filas if not f.descartada] or [f.codigo for f in filas]
    if not codigos:
        return None
    return next((f.codigo for f in filas if f.vigente and f.codigo in codigos), codigos[-1])


def mensaje_instantanea(creadas: int) -> str | None:
    """El aviso de que abrir congelo la instantanea de las composiciones (UC-15e; P:346-351)."""
    if not creadas:
        return None
    return (
        "Se creó y registró la instantánea de las composiciones de esta versión "
        f"({creadas} partidas): sus APU ya no cambian si cambia el catálogo."
    )


def elaborar(borrador: hoja.Borrador) -> hoja.ResultadoHoja:
    """Elabora el borrador con R17 del espacio vigente; la reemplaza si ya traia una vieja y no
    toca el borrador (las reglas extra no cuentan como cambios)."""
    ligado = replace(borrador, reglas_extra=con_conexion(borrador.reglas_extra, borrador.espacio))
    return hoja.elaborar_borrador(ligado)


def _base_de_comparacion(vivo: BorradorVivo) -> hoja.Borrador:
    if vivo.abierta is not None:
        return vivo.abierta.borrador
    return hoja.Borrador(fecha=vivo.borrador.fecha, moneda=vivo.borrador.moneda)


def calculo(vivo: BorradorVivo) -> tuple[hoja.ResultadoHoja, list]:
    """El resultado y los cambios del borrador vivo; se calculan una vez por `rev`."""
    with vivo.cerrojo:
        if vivo.calculo is None or vivo.calculo[0] != vivo.rev:
            resultado = elaborar(vivo.borrador)
            cambios = hoja.cambios_entre(_base_de_comparacion(vivo), vivo.borrador)
            vivo.calculo = (vivo.rev, resultado, cambios)
        return vivo.calculo[1], vivo.calculo[2]


def resumen(vivo: BorradorVivo, version_mas_nueva: str | None = None) -> ResumenHoja:
    resultado, cambios = calculo(vivo)
    presupuesto = resultado.elaboracion.presupuesto
    por_severidad: dict[int, int] = {}
    for hallazgo in resultado.elaboracion.informe.hallazgos:
        por_severidad[int(hallazgo.severidad)] = por_severidad.get(int(hallazgo.severidad), 0) + 1
    hallazgos = tuple(
        HallazgosDeSeveridad(Severidad(n).name, por_severidad[n])
        for n in sorted(por_severidad, reverse=True)
    )
    return ResumenHoja(
        rev=vivo.rev,
        moneda=presupuesto.moneda,
        total=monto(presupuesto.total),
        cambios=len(cambios),
        pendientes_catalogo=len(resultado.elaboracion.pendientes),
        hallazgos=hallazgos,
        hay_plan=vivo.borrador.plan is not None,
        version_mas_nueva=version_mas_nueva,
        guardado_como=vivo.guardado_como,
    )


def base(vivo: BorradorVivo, vigente: str | None) -> BaseAbierta:
    abierta = vivo.abierta
    return BaseAbierta(
        proyecto=vivo.proyecto,
        version=vivo.version,
        vigente=vigente,
        lista=None if abierta is None else abierta.lista,
        espacio_de=None if abierta is None else abierta.espacio_de,
        solo_lectura=False if abierta is None else abierta.solo_lectura,
        moneda=vivo.borrador.moneda,
    )


# --- Estado de una fila (compartido por las vistas) ---------------------------------------------


@dataclass(frozen=True, slots=True)
class EstadoDeFila:
    """`EstadoFila` del contrato: la peor severidad (`None` si esta limpia) y su texto."""

    severidad: str | None
    texto: str


def estado_de_fila(estado: hoja.EstadoFila) -> EstadoDeFila:
    return EstadoDeFila(None if estado.severidad is None else estado.severidad.name, estado.texto)


# --- Espacio y metrajes (R5) --------------------------------------------------------------------

AYUDA_ESPACIO = (
    "Describa el espacio en metros (eje z hacia arriba desde el piso terminado). Cada fila cita un "
    "origen de medida; un punto de agua fría sin recorrido declarado usa el recorrido propuesto. "
    "Los vértices se escriben como «x,y,z; x,y,z» y la longitud de cada tramo se calcula."
)
SIN_CANTIDADES = (
    "El borrador todavía no deriva cantidades: agregue un ambiente, una fuente y los puntos de "
    "agua, de datos o de electricidad."
)

#: Rotulo de cada tabla para la persona (en los mensajes de error van los de `hoja.ROTULOS`).
ROTULOS_DE_TABLA = {
    "origenes": "Orígenes de medida",
    "ambientes": "Ambientes",
    "fuentes": "Fuentes",
    "puntos": "Puntos",
    "tramos": "Vértices de recorridos",
}

#: Las columnas con lista cerrada (P:1113-1137): sus valores internos, en el orden de la lista.
_LISTAS: dict[str, dict[str, tuple[str, ...]]] = {
    "origenes": {"tipo": tuple(m.value for m in TipoOrigen)},
    "fuentes": {
        "especialidad": tuple(m.value for m in Especialidad),
        "tipo": tuple(m.value for m in TipoFuente),
    },
    "puntos": {
        "especialidad": tuple(m.value for m in Especialidad),
        "tipo": tuple(m.value for m in TipoPunto),
        "superficie": tuple(m.value for m in SuperficiePunto),
    },
    "tramos": {
        "superficie": tuple(m.value for m in SuperficieTramo),
        "empotrado": ("", "si", "no"),
    },
}


@dataclass(frozen=True, slots=True)
class OpcionDeLista:
    """Un valor de una lista cerrada: el interno (lo que se guarda) y su rotulo."""

    valor: str
    rotulo: str


@dataclass(frozen=True, slots=True)
class ColumnaDeTabla:
    clave: str
    rotulo: str
    lista: tuple[OpcionDeLista, ...] | None


@dataclass(frozen=True, slots=True)
class TablaDelEspacio:
    clave: str
    rotulo: str
    columnas: tuple[ColumnaDeTabla, ...]
    con_estado: bool


@dataclass(frozen=True, slots=True)
class CantidadDerivada:
    partida: str
    descripcion: str
    unidad: str
    cantidad: Monto
    origen: str


@dataclass(frozen=True, slots=True)
class VistaEspacio:
    ayuda: str
    tablas: tuple[TablaDelEspacio, ...]
    filas: dict[str, list[dict[str, str]]]
    estado: dict[str, EstadoDeFila]
    derivadas: tuple[CantidadDerivada, ...]
    total: Monto
    moneda: str
    pendientes: int
    vacio_mensaje: str | None


def _tabla(clave: str) -> TablaDelEspacio:
    listas = _LISTAS.get(clave, {})
    rotulos = hoja.ROTULOS_DE_COLUMNA[clave]
    return TablaDelEspacio(
        clave=clave,
        rotulo=ROTULOS_DE_TABLA[clave],
        columnas=tuple(
            ColumnaDeTabla(
                clave=columna,
                rotulo=rotulos[columna],
                lista=(
                    tuple(OpcionDeLista(v, hoja.rotulo_de_valor(v)) for v in listas[columna])
                    if columna in listas
                    else None
                ),
            )
            for columna in hoja.COLUMNAS[clave]
        ),
        con_estado=clave in hoja.TABLAS_CON_ESTADO,
    )


def vista_espacio(vivo: BorradorVivo) -> VistaEspacio:
    """La pestana Espacio y metrajes en lectura (P:1190-1233): las cinco tablas con su Estado por
    fila, las cantidades derivadas, el total y los pendientes del catalogo."""
    resultado, _ = calculo(vivo)
    presupuesto = resultado.elaboracion.presupuesto
    return VistaEspacio(
        ayuda=AYUDA_ESPACIO,
        tablas=tuple(_tabla(clave) for clave in hoja.COLUMNAS),
        filas=hoja.filas_desde_espacio(vivo.borrador.espacio),
        estado={clave: estado_de_fila(e) for clave, e in resultado.estado.items()},
        derivadas=tuple(
            CantidadDerivada(
                partida=i.codigo_partida,
                descripcion=i.descripcion,
                unidad=i.unidad,
                cantidad=monto(i.cantidad),
                origen=i.origen_id,
            )
            for i in resultado.items
        ),
        total=monto(presupuesto.total),
        moneda=presupuesto.moneda,
        pendientes=len(resultado.elaboracion.pendientes),
        vacio_mensaje=None if resultado.items else SIN_CANTIDADES,
    )


# --- Presupuesto (R6) ---------------------------------------------------------------------------

SIN_RENGLONES = "El presupuesto no tiene renglones todavía."


@dataclass(frozen=True, slots=True)
class FilaDePresupuesto:
    """Un renglon: `cantidad` es la vigente (texto, la que se edita) y `cantidad_calculada` la del
    sistema; `pu` y `total` son `None` en una partida pendiente (sin APU en el catalogo)."""

    clave: str
    partida: str
    descripcion: str
    unidad: str
    cantidad: str
    cantidad_calculada: str
    escrita: bool
    pu: Monto | None
    total: Monto | None
    estado: EstadoDeFila


@dataclass(frozen=True, slots=True)
class VistaPresupuesto:
    filas: tuple[FilaDePresupuesto, ...]
    total: Monto
    moneda: str
    vacio_mensaje: str | None


def vista_presupuesto(vivo: BorradorVivo) -> VistaPresupuesto:
    """La pestana Presupuesto en lectura (P:1744-1790): una fila por renglon con su cantidad, la
    calculada, el precio unitario, el total y el Estado."""
    resultado, _ = calculo(vivo)
    presupuesto = resultado.elaboracion.presupuesto
    valorados = dict(
        zip(
            hoja.claves_de_items([p.item for p in presupuesto.partidas]),
            presupuesto.partidas,
            strict=True,
        )
    )
    sin_escribir = hoja.items_sin_escribir(vivo.borrador)
    calculadas = dict(zip(hoja.claves_de_items(sin_escribir), sin_escribir, strict=True))
    escritas = vivo.borrador.cantidades
    filas = []
    for texto in hoja.filas_del_presupuesto(resultado):
        clave = texto["clave"]
        renglon = valorados.get(clave)
        calculada = calculadas[clave].cantidad
        filas.append(
            FilaDePresupuesto(
                clave=clave,
                partida=texto["partida"],
                descripcion=texto["descripcion"],
                unidad=texto["unidad"],
                cantidad=texto["cantidad"],
                cantidad_calculada=hoja.texto_numero(calculada),
                escrita=clave in escritas and escritas[clave] != calculada,
                pu=None if renglon is None else monto(renglon.resultado.precio_unitario),
                total=None if renglon is None else monto(renglon.total),
                estado=estado_de_fila(
                    resultado.estado_items.get(clave, hoja.EstadoFila(None, hoja.TEXTO_OK))
                ),
            )
        )
    return VistaPresupuesto(
        filas=tuple(filas),
        total=monto(presupuesto.total),
        moneda=presupuesto.moneda,
        vacio_mensaje=None if filas else SIN_RENGLONES,
    )
