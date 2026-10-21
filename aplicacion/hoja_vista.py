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
y devuelve dataclasses que la API serializa. La 3b-3 anade las demas pestanas: Punto de equilibrio,
Parametros, Auditoria, Precios y Trazabilidad.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
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
from core.budget.equilibrio import PuntoEquilibrio
from core.contracts import Severidad
from core.verification.informe import DECIMALES_PRESENTACION, InformeAuditoria
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


def con_r17(borrador: hoja.Borrador) -> hoja.Borrador:
    """El borrador con R17 (la conexion de cada punto) ligada a SU espacio; reemplaza una R17 vieja.
    Las reglas extra no cuentan como cambios (`Borrador.reglas_extra` no se compara). Es el
    `_con_conexion` de la pagina clasica: la usan `elaborar` y el guardado (3d-1)."""
    return replace(borrador, reglas_extra=con_conexion(borrador.reglas_extra, borrador.espacio))


def elaborar(borrador: hoja.Borrador) -> hoja.ResultadoHoja:
    """Elabora el borrador con R17 del espacio vigente; la reemplaza si ya traia una vieja y no
    toca el borrador (las reglas extra no cuentan como cambios)."""
    return hoja.elaborar_borrador(con_r17(borrador))


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


def version_mas_nueva(vivo: BorradorVivo, vigente: str | None) -> str | None:
    """La version vigente de AHORA si alguien guardo despues de abrir el borrador (D-5): es la
    que hay y no la que habia AL ABRIR (`vigente_al_abrir`). Abrir a proposito una version vieja
    o descartada no cuenta como adelantamiento. Un borrador en blanco (sin version) nunca avisa.
    Es la unica regla: el resumen y el guardado la usan."""
    if vivo.abierta is None or vigente is None or vigente == vivo.vigente_al_abrir:
        return None
    return vigente


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


# --- APU (R7) -----------------------------------------------------------------------------------

SIN_PARTIDAS = "Todavía no hay partidas valoradas: derive cantidades en Espacio y metrajes."

#: Los tres rubros de un APU y las columnas de cada uno (P:1490-1494, `_GRUPOS_APU`).
_GRUPOS_APU: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = (
    (
        "materiales",
        "Materiales",
        (
            ("descripcion", "Descripción"),
            ("unidad", "Unidad"),
            ("cantidad", "Cantidad"),
            ("precio", "Precio"),
        ),
    ),
    (
        "equipos",
        "Equipos",
        (
            ("descripcion", "Descripción"),
            ("cantidad", "Cantidad"),
            ("precio", "Precio"),
            ("depreciacion", "Depreciación"),
        ),
    ),
    (
        "mano de obra",
        "Mano de obra",
        (
            ("descripcion", "Descripción"),
            ("cantidad", "Cantidad"),
            ("sueldo", "Sueldo"),
            ("modalidad", "Modalidad"),
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class PartidaDeLista:
    codigo: str
    descripcion: str


@dataclass(frozen=True, slots=True)
class ColumnaDeApu:
    clave: str
    rotulo: str


@dataclass(frozen=True, slots=True)
class GrupoDeApu:
    """Un rubro del APU: sus lineas como texto (la cantidad es lo unico que se edita en 3c) y el
    subtotal por unidad de partida."""

    clave: str
    rotulo: str
    columnas: tuple[ColumnaDeApu, ...]
    filas: list[dict[str, str]]
    subtotal: Monto


@dataclass(frozen=True, slots=True)
class FilaDeCierre:
    concepto: str
    monto: Monto
    nota: str


@dataclass(frozen=True, slots=True)
class MetricasDeApu:
    materiales: Monto
    equipos: Monto
    mano_obra: Monto
    precio_unitario: Monto


@dataclass(frozen=True, slots=True)
class DetalleDeApu:
    codigo: str
    descripcion: str
    unidad: str
    rendimiento: str
    grupos: tuple[GrupoDeApu, ...]
    cierre: tuple[FilaDeCierre, ...]
    metricas: MetricasDeApu
    estados: tuple[str, ...]
    solo_lectura_insumos: bool


@dataclass(frozen=True, slots=True)
class VistaApu:
    partidas: tuple[PartidaDeLista, ...]
    sin_coincidencias: bool
    seleccionada: str | None
    detalle: DetalleDeApu | None
    vacio_mensaje: str | None


def _detalle_de_apu(vivo: BorradorVivo, resultado: hoja.ResultadoHoja, codigo: str) -> DetalleDeApu:
    borrador = vivo.borrador
    composicion = borrador.composiciones[codigo]
    presupuesto = resultado.elaboracion.presupuesto
    r = next(p.resultado for p in presupuesto.partidas if p.item.codigo_partida == codigo)
    tablas = hoja.filas_de_apu(composicion)
    subtotales = (r.materiales, r.equipos, r.mano_obra)
    # montos del cierre, en el orden de `hoja.filas_de_cierre` (la cascada de `calcular_apu`)
    montos = (
        r.materiales,
        r.equipos,
        r.mano_obra,
        r.costo_directo,
        r.con_administracion - r.costo_directo,
        r.con_administracion,
        r.precio_unitario - r.con_administracion,
        r.precio_unitario,
    )
    cierre = hoja.filas_de_cierre(r, borrador.parametros, presupuesto.moneda)
    return DetalleDeApu(
        codigo=codigo,
        descripcion=composicion.descripcion,
        unidad=composicion.unidad,
        rendimiento=hoja.texto_numero(composicion.rendimiento),
        grupos=tuple(
            GrupoDeApu(
                clave=clave,
                rotulo=rotulo,
                columnas=tuple(ColumnaDeApu(c, t) for c, t in columnas),
                filas=filas,
                subtotal=monto(subtotal),
            )
            for (clave, rotulo, columnas), filas, subtotal in zip(
                _GRUPOS_APU, tablas, subtotales, strict=True
            )
        ),
        cierre=tuple(
            FilaDeCierre(f["Concepto"], monto(valor), f["Nota"])
            for f, valor in zip(cierre, montos, strict=True)
        ),
        metricas=MetricasDeApu(*(monto(v) for v in (*subtotales, r.precio_unitario))),
        estados=tuple(
            f"Estado de {fila['clave']}: {fila['estado']}"
            for fila in hoja.filas_del_presupuesto(resultado)
            if fila["partida"] == codigo and fila["estado"] != hoja.TEXTO_OK
        ),
        solo_lectura_insumos=vivo.abierta is None,
    )


def vista_apu(
    vivo: BorradorVivo, partida: str | None = None, buscar: str | None = None
) -> VistaApu:
    """La pestana APU en lectura (P:1488-1738): la lista de partidas valoradas (con su buscador),
    la seleccionada y su detalle: tres rubros con subtotal, cierre paso a paso y metricas.

    Sin coincidencias en el buscador se muestran todas (P:1599); una `partida` que no esta entre
    las visibles se ignora y se toma la primera (el radio de la clasica nunca queda fuera de la
    lista, P:1604)."""
    resultado, _ = calculo(vivo)
    valoradas = resultado.elaboracion.presupuesto.partidas
    codigos = list(dict.fromkeys(p.item.codigo_partida for p in valoradas))
    if not codigos:
        return VistaApu((), False, None, None, SIN_PARTIDAS)
    descripciones = {p.item.codigo_partida: p.apu.descripcion for p in valoradas}
    visibles = hoja.filtrar_partidas(codigos, descripciones, buscar or "")
    sin_coincidencias = not visibles
    visibles = visibles or codigos
    seleccionada = partida if partida in visibles else visibles[0]
    return VistaApu(
        partidas=tuple(PartidaDeLista(c, descripciones.get(c, "")) for c in visibles),
        sin_coincidencias=sin_coincidencias,
        seleccionada=seleccionada,
        detalle=_detalle_de_apu(vivo, resultado, seleccionada),
        vacio_mensaje=None,
    )


# --- Plan y curva (R8) --------------------------------------------------------------------------

SIN_PLAN = "Esta versión no tiene plan de trabajo, así que no hay curva de inversión."


@dataclass(frozen=True, slots=True)
class FilaDePlan:
    """Una partida y la fraccion (texto) que se ejecuta en cada periodo (clave: la etiqueta)."""

    partida: str
    valores: dict[str, str]


@dataclass(frozen=True, slots=True)
class PuntoDeCurvaHoja:
    periodo: str
    monto: Monto
    acumulado: Monto
    porcentaje: Monto


@dataclass(frozen=True, slots=True)
class VistaPlan:
    hay_plan: bool
    etiquetas: tuple[str, ...]
    filas: tuple[FilaDePlan, ...]
    curva: tuple[PuntoDeCurvaHoja, ...]
    moneda: str
    mensaje: str | None


def vista_plan(vivo: BorradorVivo) -> VistaPlan:
    """La pestana Plan y curva en lectura (P:1796-1848): la matriz partida por periodo y la curva
    de inversion (periodo, monto, acumulado y % acumulado)."""
    resultado, _ = calculo(vivo)
    presupuesto = resultado.elaboracion.presupuesto
    if vivo.borrador.plan is None:
        return VistaPlan(False, (), (), (), presupuesto.moneda, SIN_PLAN)
    codigos = list(dict.fromkeys(p.item.codigo_partida for p in presupuesto.partidas))
    etiquetas, filas = hoja.plan_como_filas(resultado.plan or (), codigos)
    textos = hoja.filas_de_curva(presupuesto)
    curva = []
    for texto, punto in zip(textos, presupuesto.curva, strict=True):
        porcion = punto.acumulado / presupuesto.total * 100 if presupuesto.total else Decimal(0)
        curva.append(
            PuntoDeCurvaHoja(
                periodo=texto["periodo"],
                monto=monto(punto.monto),
                acumulado=monto(punto.acumulado),
                porcentaje=monto(porcion),
            )
        )
    return VistaPlan(
        hay_plan=True,
        etiquetas=tuple(etiquetas),
        filas=tuple(FilaDePlan(f["partida"], {e: f[e] for e in etiquetas}) for f in filas),
        curva=tuple(curva),
        moneda=presupuesto.moneda,
        mensaje=None,
    )


# --- Punto de equilibrio (R9) -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VistaEquilibrio:
    """Las cuatro metricas, el punto (si existe) y la frase del caso (P:1854-1868). `porcentaje` es
    el punto como % de las ventas; `fraccion_periodo`, de 0 a 1, exacta y como texto."""

    estado: str
    moneda: str
    venta: Monto
    costo_variable: Monto
    costo_fijo: Monto
    utilidad: Monto
    punto: Monto | None
    porcentaje: Monto | None
    periodo: str | None
    fraccion_periodo: str | None
    mensaje: str


def equilibrio_a_vista(pe: PuntoEquilibrio, moneda: str) -> VistaEquilibrio:
    """El punto de equilibrio de `core` como vista; la frase es `hoja.texto_equilibrio`."""
    return VistaEquilibrio(
        estado=pe.estado.value,
        moneda=moneda,
        venta=monto(pe.venta),
        costo_variable=monto(pe.costo_variable),
        costo_fijo=monto(pe.costo_fijo),
        utilidad=monto(pe.utilidad),
        punto=None if pe.punto is None else monto(pe.punto),
        porcentaje=None if pe.porcentaje is None else monto(pe.porcentaje),
        periodo=pe.periodo,
        fraccion_periodo=None if pe.fraccion_periodo is None else format(pe.fraccion_periodo, "f"),
        mensaje=hoja.texto_equilibrio(pe),
    )


def vista_equilibrio(vivo: BorradorVivo) -> VistaEquilibrio:
    """La pestana Punto de equilibrio (no se edita, RS-4): sale del calculo del borrador vivo."""
    resultado, _ = calculo(vivo)
    return equilibrio_a_vista(resultado.equilibrio, resultado.elaboracion.presupuesto.moneda)


# --- Parametros (R10) ---------------------------------------------------------------------------

#: Los rotulos de los cuatro cuadros (P:2030-2035), con tildes: son texto de la interfaz nueva.
ROTULOS_PARAMETROS = {
    "fcas": "FCAS (fracción: 6.00 = prestaciones del 600 %)",
    "bono_alimentacion": "Bono de alimentación (por obrero y día)",
    "administracion": "Administración (fracción del costo directo)",
    "utilidad": "Utilidad (fracción, en cascada sobre la administración)",
}


@dataclass(frozen=True, slots=True)
class CampoDeParametro:
    clave: str
    rotulo: str
    valor: str


@dataclass(frozen=True, slots=True)
class VistaParametros:
    campos: tuple[CampoDeParametro, ...]
    moneda_proyecto: str | None
    total: Monto
    puede_convertir: bool


def vista_parametros(
    vivo: BorradorVivo, moneda_proyecto: str, puede_convertir: bool
) -> VistaParametros:
    """La pestana Parametros en lectura (P:2028-2118): los cuatro factores como texto exacto
    (`str(Decimal)`, lo que el cuadro de la clasica siembra) y el total. La moneda del proyecto y
    el cambio de moneda solo existen con una version abierta (P:2073); `moneda_proyecto` la lee la
    ruta de la base y `puede_convertir` es el permiso de quien pregunta."""
    resultado, _ = calculo(vivo)
    abierta = vivo.abierta is not None
    return VistaParametros(
        campos=tuple(
            CampoDeParametro(
                clave=c,
                rotulo=ROTULOS_PARAMETROS[c],
                valor=str(getattr(vivo.borrador.parametros, c)),
            )
            for c in hoja.CAMPOS_PARAMETROS
        ),
        moneda_proyecto=moneda_proyecto if abierta else None,
        total=monto(resultado.elaboracion.presupuesto.total),
        puede_convertir=abierta and puede_convertir,
    )


# --- Auditoria (R11) ----------------------------------------------------------------------------


def informe_de_auditoria(vivo: BorradorVivo) -> InformeAuditoria:
    """El informe de la pestana Auditoria (P:2124-2128): todas las reglas sobre el borrador vigente,
    con R17 (viene de `elaborar`, no de la base). La API lo serializa con `informe_a_respuesta`."""
    resultado, _ = calculo(vivo)
    return resultado.elaboracion.informe


# --- Trazabilidad (R14) -------------------------------------------------------------------------

SIN_REGISTROS = "Esta versión no nació de una edición: no tiene registros de cambio."


@dataclass(frozen=True, slots=True)
class RegistroDeTraza:
    """Un `RegistroCambio` de la version como lo muestra la pestana (P:2176-2196)."""

    objeto: str
    clave: str
    campo: str
    antes: str
    despues: str
    fuente: str
    responsable: str
    fecha_hora: str


@dataclass(frozen=True, slots=True)
class VistaTrazabilidad:
    versiones: tuple[hoja.FilaVersion, ...]
    registros: tuple[RegistroDeTraza, ...]
    vacio_mensaje: str | None


def vista_trazabilidad(
    versiones: Sequence[hoja.FilaVersion], registros: Sequence[hoja.FilaRegistro]
) -> VistaTrazabilidad:
    """El historial del proyecto y los registros de la version pedida, en el orden en que se
    guardaron. Sin registros, el mensaje de la clasica (P:2199)."""
    return VistaTrazabilidad(
        versiones=tuple(versiones),
        registros=tuple(
            RegistroDeTraza(
                r.objeto,
                r.clave,
                r.campo,
                r.valor_anterior,
                r.valor_nuevo,
                r.fuente,
                r.responsable,
                r.fecha_hora.isoformat(),
            )
            for r in registros
        ),
        vacio_mensaje=None if registros else SIN_REGISTROS,
    )


# --- Precios con su origen (R12) ----------------------------------------------------------------

#: Clave y numericidad de cada columna, en el orden de `hoja.COLUMNAS_PRECIOS` (cuyos rotulos se
#: usan tal cual: una sola fuente).
_CLAVES_DE_PRECIOS: tuple[tuple[str, bool], ...] = (
    ("insumo", False),
    ("codigo", False),
    ("tipo", False),
    ("precio", True),
    ("lista", False),
    ("moneda", False),
    ("fecha_precio", False),
    ("tasa", True),
    ("fecha_tasa", False),
    ("referencia", False),
    ("cotizacion", False),
    ("moneda_original", False),
    ("precio_original", True),
    ("fuente_tasa", False),
    ("fuente", False),
    ("propio", False),
    ("erosion_usd", True),
    ("erosion_bs", True),
    ("erosion_pct", True),
    ("erosion_indice", True),
    ("estado", False),
)


@dataclass(frozen=True, slots=True)
class ColumnaDePrecio:
    clave: str
    rotulo: str
    numerica: bool


@dataclass(frozen=True, slots=True)
class FilaDePrecioVista:
    """El origen del precio de un insumo (P:1913-1944). `erosion_pct` ya va multiplicada por 100,
    como la muestra la clasica; las erosiones son `None` sin evaluacion o sin alguna tasa."""

    insumo: str
    codigo: str
    tipo: str
    precio: Monto
    lista: str
    moneda: str
    fecha_precio: str
    tasa: Monto | None
    fecha_tasa: str | None
    referencia: str
    cotizacion: str
    moneda_original: str
    precio_original: Monto | None
    fuente_tasa: str
    fuente: str
    propio: str
    erosion_usd: Monto | None
    erosion_bs: Monto | None
    erosion_pct: Monto | None
    erosion_indice: Monto | None
    estado: str


@dataclass(frozen=True, slots=True)
class VistaPrecios:
    moneda: str
    fecha_evaluacion: str
    columnas: tuple[ColumnaDePrecio, ...]
    filas: tuple[FilaDePrecioVista, ...]


def _monto_o_nada(valor: Decimal | None) -> Monto | None:
    return None if valor is None else monto(valor)


def _fila_de_precio(p: hoja.FilaPrecio) -> FilaDePrecioVista:
    return FilaDePrecioVista(
        insumo=p.descripcion,
        codigo=p.codigo,
        tipo=p.tipo,
        precio=monto(p.precio),
        lista=p.lista,
        moneda=p.moneda,
        fecha_precio=p.fecha.isoformat(),
        tasa=_monto_o_nada(p.tasa),
        fecha_tasa=None if p.fecha_tasa is None else p.fecha_tasa.isoformat(),
        referencia=p.referencia,
        cotizacion=p.cotizacion,
        moneda_original=p.moneda_original,
        precio_original=_monto_o_nada(p.precio_original),
        fuente_tasa=p.fuente_tasa,
        fuente=p.fuente,
        propio=hoja.texto_propio(p.propio),
        erosion_usd=_monto_o_nada(p.erosion_usd),
        erosion_bs=_monto_o_nada(p.erosion_bs),
        erosion_pct=None if p.erosion_pct is None else monto(p.erosion_pct * 100),
        erosion_indice=_monto_o_nada(p.erosion_indice),
        estado=p.estado,
    )


def vista_precios(
    precios: Sequence[hoja.FilaPrecio], moneda: str, fecha_evaluacion: date
) -> VistaPrecios:
    """La pestana Precios (P:1899-2025) sobre la version GUARDADA, evaluada a `fecha_evaluacion`
    (hoy). `precios` ya viene ordenado por codigo de insumo (`hoja.precios_de_version`)."""
    return VistaPrecios(
        moneda=moneda,
        fecha_evaluacion=fecha_evaluacion.isoformat(),
        columnas=tuple(
            ColumnaDePrecio(clave, rotulo, numerica)
            for (clave, numerica), rotulo in zip(
                _CLAVES_DE_PRECIOS, hoja.COLUMNAS_PRECIOS, strict=True
            )
        ),
        filas=tuple(_fila_de_precio(p) for p in precios),
    )
