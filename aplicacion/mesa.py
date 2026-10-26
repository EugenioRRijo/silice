"""La mesa de control: el inicio de «Presupuestos y obras» (MOD-4a; diseño de módulos §6 y §12.6).

Tres cosas, todas deterministas y en `Decimal` (la interfaz solo formatea):

- `obras_de_la_mesa`: cada obra de la carpeta con su etapa, su total, su valor ganado al último
  corte y qué hacer después. El control se calcula con `aplicacion.control.calcular_el_control`
  tal cual (el núcleo no cambia).
- `cifras_de_la_mesa`: «Valor ganado» (ΣEV contra ΣPV) y «Avance contra el plan» (ΣEV ÷ ΣPV) de
  las obras en ejecución, en la moneda de la carpeta; una obra en la otra moneda se convierte con la
  tasa del BCV de su corte y se declara, y sin tasa se deja aparte (nunca se suma a ciegas).
- `pendientes`: lo que requiere atención, en los grupos de `GRUPOS`. Cada grupo lo alimentan las
  fuentes de `FUENTES`; un grupo sin ninguna fuente registrada no sale (nunca un grupo vacío
  falso). Las tareas que vienen (compras, mediciones) agregan su fuente con
  una línea en `FUENTES`.

Nada escribe: solo lee la carpeta de la sesión. Los textos son los que ve la persona (español de
Venezuela, «obra» y no «proyecto»); las cifras dentro de un texto van con coma decimal
(`aplicacion.cifras.texto_de_cifra`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from aplicacion import aprobaciones
from aplicacion.aprobaciones import pendientes_de_aprobacion
from aplicacion.causas import atrasos
from aplicacion.cifras import texto_de_cifra
from aplicacion.control import (
    ControlInvalido,
    calcular_el_control,
    parametros_actuales,
)
from aplicacion.hoja_partidas import pendientes_sin_calculo
from aplicacion.listas_para_armar import describir
from aplicacion.mercado import pendientes_de_mercado
from aplicacion.obras import SIN_FICHA, fichas
from aplicacion.procura import pendientes_de_compras
from aplicacion.proyectos import ProyectoDelCaso, proyectos_del_caso
from core import models
from core.budget.moneda import moneda_del_proyecto
from core.budget.valuaciones import linea_base_vigente, valuaciones_registradas
from core.catalog import Catalogo
from core.catalog.moneda import convertir
from core.contracts.verificacion import Severidad

__all__ = [
    "ETAPA_TEXTO",
    "FUENTES",
    "GRUPOS",
    "Cifra",
    "CifrasMesa",
    "Conversion",
    "FuentePendientes",
    "GrupoPendientes",
    "ObraEnMesa",
    "Pendiente",
    "Siguiente",
    "TasaDelBcv",
    "cifras_de_la_mesa",
    "dias_habiles_entre",
    "hallazgos_graves",
    "lista_vieja",
    "moneda_de_la_suma",
    "obras_de_la_mesa",
    "pendiente",
    "pendientes",
    "plural",
    "precios_sin_referencia",
    "precios_viejos",
    "versiones_vigentes",
]

EN_ELABORACION = "en_elaboracion"
EN_APROBACION = "en_aprobacion"
APROBADA = "aprobada"
EN_EJECUCION = "en_ejecucion"
ATRASADA = "atrasada"
#: Cómo se nombra cada etapa en la interfaz.
ETAPA_TEXTO = {
    EN_ELABORACION: "En elaboración",
    EN_APROBACION: "En aprobación",
    APROBADA: "Aprobada",
    EN_EJECUCION: "En ejecución",
    ATRASADA: "Atrasada",
}
_EN_CURSO = frozenset({EN_EJECUCION, ATRASADA})

SIN_AVANCE = "Sin avance registrado"
#: Lo que dice la mesa cuando el control de una obra con valuaciones no se puede calcular: el
#: motivo (el mensaje del núcleo, sin tildes y con fechas ISO) lo explica la pantalla Control.
SIN_CALCULO = "No se pudo calcular el avance; ábralo en Control para ver el motivo."
#: Desde cuántos días una lista de precios es vieja (diseño §12.6: «más de 90 días»).
DIAS_DE_UNA_LISTA_VIEJA = 90
_SEVERIDADES_GRAVES = (int(Severidad.ERROR), int(Severidad.CRITICO))

_CENTESIMA = Decimal("0.01")
_DECIMA = Decimal("0.1")
_DIEZMILESIMA = Decimal("0.0001")
_CIEN = Decimal(100)
_CERO = Decimal(0)
_UNO = Decimal("1.0000")
_RENDIMIENTO = "rendimiento"


@dataclass(frozen=True)
class Siguiente:
    """Un paso que se puede dar: el texto del botón y la pantalla (`id` de `rutas.ts`)."""

    texto: str
    pagina: str


ABRIR_LA_HOJA = Siguiente("Abrir la Hoja", "hoja")
REGISTRAR_EL_AVANCE = Siguiente("Registrar el avance", "control")
VER_LAS_ALERTAS = Siguiente("Ver las alertas", "control")
ACTUALIZAR_PRECIOS = Siguiente("Actualizar precios", "actualizacion")
VER_EL_CATALOGO = Siguiente("Ver el catálogo", "catalogo")
VER_EL_ENVIO = Siguiente(*aprobaciones.VER_EL_ENVIO)  # el mismo de la fuente «aprobar»
DECLARAR_LA_LINEA_BASE = Siguiente("Declarar la línea base", "control")


@dataclass(frozen=True)
class ObraEnMesa:
    """Una obra de la carpeta en la mesa. `version` y `total` son los de la versión de la línea
    base o, sin ella, los de la vigente. `corte`, `ev`, `pv`, `bac` y `spi` son los del control al
    último corte (`None` si no se calculó); `retraso_dias`, los días hábiles que el término
    reproyectado pasa del plan (`None` si no pasa)."""

    codigo: str
    nombre: str
    cliente: str
    moneda: str
    etapa: str
    version: str | None
    total: Decimal | None
    corte: date | None
    ev: Decimal | None
    pv: Decimal | None
    bac: Decimal | None
    spi: Decimal | None
    retraso_dias: int | None
    que_pasa: str | None
    siguiente: Siguiente | None


@dataclass(frozen=True)
class Cifra:
    """Una cifra de la franja: valor, meta y desviación juntos (Fiori; IBCS para el sentido)."""

    clave: str
    titulo: str
    actual: Decimal
    meta: Decimal
    delta: Decimal
    delta_pct: Decimal | None
    sentido: str
    detalle: str | None


@dataclass(frozen=True)
class TasaDelBcv:
    """La tasa del BCV (Bs por USD) que rige a una fecha y la fecha valor de esa tasa."""

    valor: Decimal
    fecha: date


@dataclass(frozen=True)
class Conversion:
    """Una obra en la otra moneda que se sumó convertida con la tasa del BCV de su corte:
    `fecha` es el corte de la obra y `fecha_tasa`, la fecha valor de la tasa (hasta 7 días antes
    del corte)."""

    obra: str
    moneda: str
    tasa: Decimal
    fecha: date
    fecha_tasa: date


@dataclass(frozen=True)
class CifrasMesa:
    valor_ganado: Cifra | None
    avance: Cifra | None
    conversiones: tuple[Conversion, ...]
    fuera_de_suma: tuple[str, ...]


@dataclass(frozen=True)
class Pendiente:
    """Algo que requiere atención en una obra (`obra` es su código) y su acción."""

    obra: str
    obra_nombre: str
    texto: str
    accion: Siguiente


@dataclass(frozen=True)
class GrupoPendientes:
    clave: str
    titulo: str
    items: tuple[Pendiente, ...]


FuentePendientes = Callable[[Session, date], list[Pendiente]]


# --- días hábiles -------------------------------------------------------------------------------


def dias_habiles_entre(desde: date, hasta: date) -> int:
    """Los días de lunes a viernes `d` con `desde < d <= hasta` (0 si `hasta <= desde`)."""
    dias = 0
    dia = desde + timedelta(days=1)
    while dia <= hasta:
        if dia.weekday() < 5:
            dias += 1
        dia += timedelta(days=1)
    return dias


# --- textos ---------------------------------------------------------------------------------------


def _entero(n: int) -> str:
    """Un entero como lo lee la persona: con punto de miles («1.200»)."""
    return texto_de_cifra(Decimal(n))


def plural(n: int, singular: str, en_plural: str) -> str:
    """`n` con punto de miles y la palabra que le toca («1 obra atrasada», «1.200 días»)."""
    return f"{_entero(n)} {singular if n == 1 else en_plural}"


def _dias_habiles(n: int) -> str:
    return plural(n, "día hábil", "días hábiles")


def _a(valor: Decimal, paso: Decimal) -> Decimal:
    return valor.quantize(paso, rounding=ROUND_HALF_UP)


# --- obras de la mesa -----------------------------------------------------------------------------


def _total(sesion: Session, presupuesto_id: int) -> Decimal:
    """Σ `partida_presupuestada.total` de la versión, sumado en `Decimal` (no en la base)."""
    totales = sesion.scalars(
        select(models.PartidaPresupuestada.total).where(
            models.PartidaPresupuestada.presupuesto_id == presupuesto_id
        )
    )
    return sum(totales, _CERO)


@dataclass(frozen=True)
class _Estado:
    """La etapa de una obra y lo que su control dice (todo `None` si no se calculó)."""

    etapa: str
    siguiente: Siguiente
    que_pasa: str | None = None
    corte: date | None = None
    ev: Decimal | None = None
    pv: Decimal | None = None
    bac: Decimal | None = None
    spi: Decimal | None = None
    retraso_dias: int | None = None


_EN_ELABORACION = _Estado(EN_ELABORACION, ABRIR_LA_HOJA)
_EN_APROBACION = _Estado(EN_APROBACION, VER_EL_ENVIO)
_APROBADA = _Estado(APROBADA, DECLARAR_LA_LINEA_BASE)


def _sin_linea_base(sesion: Session, codigo: str) -> _Estado:
    """La etapa de una obra sin línea base (MP-4): en aprobación si alguna de sus versiones lo
    está; si no, aprobada si tiene una versión aprobada (con o sin observaciones); si no, en
    elaboración."""
    if any(e.estado == EN_APROBACION for e in aprobaciones.estados(sesion, codigo).values()):
        return _EN_APROBACION
    if aprobaciones.ultima_aprobada(sesion, codigo) is not None:
        return _APROBADA
    return _EN_ELABORACION


def _en_curso(sesion: Session, catalogo: Catalogo, nombre: str, hoy: date) -> _Estado:
    """La etapa y el control de una obra con línea base, al último corte (el *hasta* de la última
    valuación; sin valuaciones, `hoy`). Una obra atrasada dice la primera partida atrasada en el
    orden del presupuesto con su causa (`aplicacion.causas.atrasos`, MP-7); solo sin atrasos por
    partida dice «Atrasada …» con su SPI."""
    valuaciones = valuaciones_registradas(sesion, nombre)
    con_valuaciones = bool(valuaciones)
    # el corte por defecto del control (`corte_por_defecto`), con `hoy` en vez del reloj
    corte = max((v.hasta for v in valuaciones), default=hoy)
    try:
        resultado = calcular_el_control(sesion, nombre, catalogo, corte=corte)
    except ControlInvalido:
        # Sin valuaciones no hay nada que controlar todavía (p. ej. la línea base rige más tarde).
        que_pasa = SIN_CALCULO if con_valuaciones else SIN_AVANCE
        return _Estado(EN_EJECUCION, REGISTRAR_EL_AVANCE, que_pasa)
    indicadores = resultado.indicadores
    spi = indicadores.spi
    termino = resultado.reproyeccion.termino
    retraso = None if termino is None else termino - resultado.estado.dias_plan
    retraso = retraso if retraso is not None and retraso > 0 else None
    atrasada = spi is not None and spi < parametros_actuales(sesion, nombre).spi_error
    por_partida = atrasos(sesion, resultado) if atrasada else []
    if por_partida:
        que_pasa: str | None = por_partida[0].texto
    elif atrasada and spi is not None:
        dias = "" if retraso is None else f" {_dias_habiles(retraso)}"
        que_pasa = f"Atrasada{dias} (SPI {texto_de_cifra(_a(spi, _CENTESIMA))})"
    else:
        que_pasa = None if con_valuaciones else SIN_AVANCE
    return _Estado(
        etapa=ATRASADA if atrasada else EN_EJECUCION,
        siguiente=VER_LAS_ALERTAS if atrasada else REGISTRAR_EL_AVANCE,
        que_pasa=que_pasa,
        corte=resultado.instantanea.corte,
        ev=indicadores.ev,
        pv=indicadores.pv,
        bac=indicadores.bac,
        spi=spi,
        retraso_dias=retraso,
    )


def obras_de_la_mesa(sesion: Session, catalogo: Catalogo, hoy: date) -> list[ObraEnMesa]:
    """Las obras de la carpeta en orden alfabético, cada una con su etapa:

    - sin línea base de control declarada: `en_aprobacion` si alguna versión está en
      aprobación, `aprobada` si tiene una versión aprobada y, si no, `en_elaboracion`;
    - `en_ejecucion` con línea base, y `atrasada` si su SPI es menor que el umbral de SPI de su
      control (`parametros_actuales(...).spi_error`, 0,90 por omisión).

    Un control que no se puede calcular (`ControlInvalido`) deja EV y PV en `None` y su mensaje en
    `que_pasa`; sin valuaciones, `que_pasa` es «Sin avance registrado»."""
    de_cada_obra = fichas(sesion)
    obras = []
    for fila in proyectos_del_caso(sesion):
        proyecto = sesion.get(models.Proyecto, fila.id)
        base = linea_base_vigente(sesion, fila.nombre, date.max)
        version_id = fila.version_id if base is None else base.presupuesto_id
        version = None if version_id is None else sesion.get(models.Presupuesto, version_id)
        if base is None:
            estado = _sin_linea_base(sesion, str(fila.id))
        else:
            estado = _en_curso(sesion, catalogo, fila.nombre, hoy)
        obras.append(
            ObraEnMesa(
                codigo=str(fila.id),
                nombre=fila.nombre,
                cliente=de_cada_obra.get(fila.id, SIN_FICHA).cliente,
                moneda=moneda_del_proyecto(sesion, proyecto),
                etapa=estado.etapa,
                version=None if version is None else version.codigo,
                total=None if version is None else _total(sesion, version.id),
                corte=estado.corte,
                ev=estado.ev,
                pv=estado.pv,
                bac=estado.bac,
                spi=estado.spi,
                retraso_dias=estado.retraso_dias,
                que_pasa=estado.que_pasa,
                siguiente=estado.siguiente,
            )
        )
    return obras


# --- cifras de la mesa ----------------------------------------------------------------------------


def _sumables(obras: Sequence[ObraEnMesa]) -> list[ObraEnMesa]:
    return [o for o in obras if o.etapa in _EN_CURSO and o.ev is not None and o.pv is not None]


def moneda_de_la_suma(obras: Sequence[ObraEnMesa], moneda: str | None) -> str | None:
    """La moneda en que se suman las cifras: la de la carpeta; sin ella, la de las obras en
    ejecución si todas comparten una; si no, `None` (nada se suma)."""
    if moneda is not None:
        return moneda
    monedas = {obra.moneda for obra in _sumables(obras)}
    return monedas.pop() if len(monedas) == 1 else None


def _detalle_del_avance(obras: Sequence[ObraEnMesa]) -> str | None:
    """«{n} obra(s) atrasada(s); la más atrasada, {nombre}: {d} días hábiles» (choque 12)."""
    atrasadas = [obra for obra in obras if obra.etapa == ATRASADA]
    if not atrasadas:
        return None
    texto = plural(len(atrasadas), "obra atrasada", "obras atrasadas")
    con_dias = [obra for obra in atrasadas if obra.retraso_dias is not None]
    if not con_dias:
        return texto
    peor = max(con_dias, key=lambda obra: obra.retraso_dias or 0)
    return f"{texto}; la más atrasada, {peor.nombre}: {_dias_habiles(peor.retraso_dias or 0)}"


def cifras_de_la_mesa(
    obras: Sequence[ObraEnMesa], moneda: str | None, tasa: Callable[[date], TasaDelBcv | None]
) -> CifrasMesa:
    """Valor ganado y avance contra el plan de las obras en ejecución (o atrasadas) con EV y PV.

    Cada obra se suma en la moneda de la suma (`moneda_de_la_suma`); una en la otra moneda se
    convierte con `tasa(corte)` (Bs = USD × tasa; USD = Bs ÷ tasa) y se declara en
    `conversiones` con la fecha valor de la tasa; sin tasa va a `fuera_de_suma`. Montos a 0,01,
    `delta_pct` a 0,1 y el avance a 0,0001, con ROUND_HALF_UP. Sin ninguna obra sumada, las dos
    cifras son `None`; con ΣPV = 0 el avance es `None` y la desviación porcentual también."""
    destino = moneda_de_la_suma(obras, moneda)
    suma_ev = suma_pv = _CERO
    sumadas = 0
    conversiones: list[Conversion] = []
    fuera: list[str] = []
    for obra in _sumables(obras):
        ev, pv = obra.ev or _CERO, obra.pv or _CERO
        if destino is None:
            fuera.append(obra.nombre)
            continue
        if obra.moneda != destino:
            del_bcv = None if obra.corte is None else tasa(obra.corte)
            if del_bcv is None or obra.corte is None:
                fuera.append(obra.nombre)
                continue
            ev = convertir(ev, obra.moneda, destino, del_bcv.valor)
            pv = convertir(pv, obra.moneda, destino, del_bcv.valor)
            conversiones.append(
                Conversion(obra.nombre, obra.moneda, del_bcv.valor, obra.corte, del_bcv.fecha)
            )
        suma_ev += ev
        suma_pv += pv
        sumadas += 1
    if sumadas == 0:
        return CifrasMesa(None, None, tuple(conversiones), tuple(fuera))
    delta = suma_ev - suma_pv
    valor_ganado = Cifra(
        clave="valor_ganado",
        titulo="Valor ganado",
        actual=_a(suma_ev, _CENTESIMA),
        meta=_a(suma_pv, _CENTESIMA),
        delta=_a(delta, _CENTESIMA),
        delta_pct=None if suma_pv == _CERO else _a(delta / suma_pv * _CIEN, _DECIMA),
        sentido=_RENDIMIENTO,
        detalle=None,
    )
    avance = None
    if suma_pv != _CERO:
        actual = _a(suma_ev / suma_pv, _DIEZMILESIMA)
        avance = Cifra(
            clave="avance",
            titulo="Avance contra el plan",
            actual=actual,
            meta=_UNO,
            delta=actual - _UNO,
            delta_pct=None,
            sentido=_RENDIMIENTO,
            detalle=_detalle_del_avance(obras),
        )
    return CifrasMesa(valor_ganado, avance, tuple(conversiones), tuple(fuera))


# --- pendientes -----------------------------------------------------------------------------------


def versiones_vigentes(
    sesion: Session,
) -> Iterator[tuple[ProyectoDelCaso, models.Presupuesto]]:
    """Cada obra con versión vigente, en orden alfabético, con esa versión."""
    for fila in proyectos_del_caso(sesion):
        if fila.version_id is not None:
            yield fila, sesion.get(models.Presupuesto, fila.version_id)


def pendiente(fila: ProyectoDelCaso, texto: str, accion: Siguiente) -> Pendiente:
    return Pendiente(str(fila.id), fila.nombre, texto, accion)


def precios_viejos(sesion: Session, hoy: date) -> list[Pendiente]:
    """Precios: la lista de la versión vigente tiene más de 90 días de vigencia a `hoy`."""
    salida = []
    for fila, version in versiones_vigentes(sesion):
        lista = version.lista_precios
        dias = (hoy - lista.fecha_vigencia).days
        if dias > DIAS_DE_UNA_LISTA_VIEJA:
            texto = (
                f"Precios de hace {_entero(dias)} días (lista «{lista.nombre}» del "
                f"{lista.fecha_vigencia:%d/%m/%Y})"
            )
            salida.append(pendiente(fila, texto, ACTUALIZAR_PRECIOS))
    return salida


def precios_sin_referencia(sesion: Session, hoy: date) -> list[Pendiente]:
    """Precios: insumos de la versión vigente cuyo precio en su lista no tiene referencia (p. ej.
    el Ref de MaPreX) ni origen declarado."""
    del hoy  # la regla no depende del día
    salida = []
    for fila, version in versiones_vigentes(sesion):
        insumos = (
            select(models.LineaComposicionVersion.insumo_id)
            .join(models.ComposicionVersion)
            .where(
                models.ComposicionVersion.presupuesto_id == version.id,
                models.LineaComposicionVersion.insumo_id.is_not(None),
            )
        )
        precio = models.PrecioInsumo
        cuantos = sesion.scalar(
            select(func.count())
            .select_from(precio)
            .where(
                precio.lista_id == version.lista_precios_id,
                precio.insumo_id.in_(insumos),
                ~exists().where(models.ReferenciaPrecio.precio_id == precio.id),
                ~exists().where(models.PrecioOrigen.precio_id == precio.id),
            )
        )
        if cuantos:
            texto = f"{plural(cuantos, 'precio', 'precios')} sin referencia en {version.codigo}"
            salida.append(pendiente(fila, texto, VER_EL_CATALOGO))
    return salida


def hallazgos_graves(sesion: Session, hoy: date) -> list[Pendiente]:
    """Calidad: hallazgos de severidad ERROR o CRÍTICO de la versión vigente."""
    del hoy  # la regla no depende del día
    salida = []
    for fila, version in versiones_vigentes(sesion):
        cuantos = sesion.scalar(
            select(func.count())
            .select_from(models.Hallazgo)
            .where(
                models.Hallazgo.presupuesto_id == version.id,
                models.Hallazgo.severidad.in_(_SEVERIDADES_GRAVES),
            )
        )
        if cuantos:
            hallazgos = plural(
                cuantos, "hallazgo de error o crítico", "hallazgos de error o críticos"
            )
            salida.append(pendiente(fila, f"{hallazgos} en {version.codigo}", ABRIR_LA_HOJA))
    return salida


def lista_vieja(sesion: Session, hoy: date) -> list[Pendiente]:
    """Calidad: la lista de la versión vigente tiene más de 90 días menos que la lista para armar
    de la carpeta a `hoy` (`aplicacion.listas_para_armar.describir`)."""
    para_armar = describir(sesion, hoy)
    if para_armar is None:
        return []
    salida = []
    for fila, version in versiones_vigentes(sesion):
        dias = (para_armar.fecha - version.lista_precios.fecha_vigencia).days
        if dias > DIAS_DE_UNA_LISTA_VIEJA:
            texto = (
                f"La lista de {version.codigo} es {_entero(dias)} días más vieja que la lista "
                "para armar."
            )
            salida.append(pendiente(fila, texto, ACTUALIZAR_PRECIOS))
    return salida


#: Los grupos de la columna de pendientes, en su orden.
GRUPOS = (
    ("aprobar", "Aprobar"),
    ("compras", "Compras"),
    ("precios", "Precios"),
    ("calidad", "Calidad"),
)
#: Las fuentes de cada grupo; un grupo sin fuentes no sale. Una línea por fuente: las tareas que
#: vienen agregan la suya (MP-7 compras, T9 cantidades sin cálculo).
FUENTES: dict[str, tuple[FuentePendientes, ...]] = {
    "aprobar": (pendientes_de_aprobacion,),
    "compras": (pendientes_de_compras,),
    "precios": (
        precios_viejos,
        precios_sin_referencia,
        pendientes_de_mercado,
    ),
    "calidad": (
        hallazgos_graves,
        lista_vieja,
        pendientes_sin_calculo,
    ),
}


def pendientes(sesion: Session, hoy: date) -> list[GrupoPendientes]:
    """Los grupos de `GRUPOS` que tienen al menos una fuente registrada, con lo que dicen sus
    fuentes en el orden en que están registradas (aunque no digan nada)."""
    grupos = []
    for clave, titulo in GRUPOS:
        fuentes = FUENTES.get(clave, ())
        if not fuentes:
            continue
        items = tuple(item for fuente in fuentes for item in fuente(sesion, hoy))
        grupos.append(GrupoPendientes(clave, titulo, items))
    return grupos
