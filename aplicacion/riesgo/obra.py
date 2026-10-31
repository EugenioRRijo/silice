"""El riesgo de una obra guardada, lo que pide la pantalla «Riesgo de la obra» (plan vial, T16).

Aquí se arma lo que `proyectar` y `comprobar_hacia_atras` reciben a partir de lo guardado, sin
calcular nada nuevo:

- **El presupuesto** de la versión, **recalculado con el motor** (`cargar_presupuesto`: cada
  renglón se revalora con su composición congelada), nunca un total guardado y redondeado: la
  proyección compara exacto contra el total. Sus composiciones (`composiciones_de_presupuesto`) y
  sus parámetros de costo congelados.
- **La mezcla propia** (`mezclas_publicadas`): por cada insumo `MZP-<producto>` que use el
  presupuesto (se reconoce por su descripción, `descripcion_de_costo_propio`), el **último cálculo
  publicado** de la Tarea 4 (`costos_propios_publicados`, el mismo que concilia CV3) da su receta
  del período, su costo de planta por tonelada y el precio de cada componente. El cálculo guarda
  sus cifras en su moneda; si no es la del presupuesto se convierten con la **tasa del cierre del
  mes del cálculo** (`equivalencia_del_cierre`, la misma con que el cálculo convirtió lo comprado).
  Si en el mes hubo dos recetas, la del período pondera por las toneladas hechas con cada una
  (`costo_de_mezcla_del_periodo` hace lo mismo). Sin mezcla propia, todo vacío.
- **La historia**: hasta el último día del mes anterior al inicio (`historia_para_proyectar`), así
  ningún mes queda a medias (fila 75).
- **El inicio**: el declarado; si no se declara, la fecha de inicio del calendario de la última
  línea base de control de esa versión; sin ninguno de los dos, se niega.

Nada se guarda: proyectar y comprobar son cálculos de consulta.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.conciliacion import costos_propios_publicados
from aplicacion.costo_propio import (
    PREFIJO_DE_MEZCLA,
    CalculoGuardado,
    descripcion_de_costo_propio,
)
from aplicacion.riesgo.comprobacion import Comprobacion, comprobar_hacia_atras
from aplicacion.riesgo.proyeccion import (
    SERIE_TASA,
    ParametrosProyeccion,
    Proyeccion,
    historia_para_proyectar,
    proyectar,
    series_del_mapa,
)
from aplicacion.riesgo.series import SERIES_VIALES, MapaSeries, historia_mensual
from aplicacion.tasa_del_dia import SinTasaDelDia, equivalencia_del_cierre
from aplicacion.vial import version_de
from core import models
from core.budget import cargar_presupuesto, composiciones_de_presupuesto
from core.catalog import Catalogo
from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.contracts.presupuesto import Presupuesto
from produccion.costo import exacto
from produccion.receta import Componente, Receta

__all__ = [
    "ComprobacionDeLaObra",
    "InsumosDeLaObra",
    "MezclasPropias",
    "ProyeccionDeLaObra",
    "SerieOfrecida",
    "comprobar_obra",
    "insumos_de_la_obra",
    "mezclas_publicadas",
    "proyectar_obra",
]

CERO = Decimal(0)
INICIO_DE_LA_LINEA_BASE = "linea_base"
INICIO_DECLARADO = "declarado"
SIN_INICIO = (
    "Indique la fecha de inicio de la obra: la versión no tiene línea base de control de la que "
    "tomarla."
)


@dataclass(frozen=True)
class MezclasPropias:
    """Lo que `proyectar` recibe de las mezclas propias, por la descripción del insumo de la
    mezcla en el APU (y los componentes por su código), en la moneda del presupuesto; `calculos`
    dice de qué cálculo publicado salió cada mezcla."""

    recetas: dict[str, Receta] = field(default_factory=dict)
    costo_planta_por_t: dict[str, Decimal] = field(default_factory=dict)
    precio_de_componente: dict[str, Decimal] = field(default_factory=dict)
    calculos: dict[str, int] = field(default_factory=dict)


# --- La mezcla propia del cálculo publicado -------------------------------------------------------


def _receta_del_periodo(recetas: list[dict[str, Any]], producto: str, calculo: int) -> Receta:
    """La receta con que se hizo `producto` en el período; con varias, una sola que pondera cada
    componente por las toneladas hechas con cada receta."""
    usos = [r for r in recetas if r["producto"] == producto]
    if not usos:
        raise ValueError(
            f"El cálculo n.º {calculo} no guarda la receta de {producto}: no se puede proyectar "
            "su mezcla."
        )
    toneladas = [Decimal(r["toneladas"]) for r in usos]
    total = sum(toneladas, CERO)
    cantidades: dict[tuple[str, str, str], Decimal] = {}
    for receta, t in zip(usos, toneladas, strict=True):
        for c in receta["componentes"]:
            clave = (c["codigo"], c["unidad"], c["tipo"])
            cantidades[clave] = cantidades.get(clave, CERO) + t * Decimal(c["cantidad_por_t"])
    if len({codigo for codigo, _, _ in cantidades}) != len(cantidades):
        raise ValueError(
            f"Las recetas de {producto} del cálculo n.º {calculo} usan un componente con dos "
            "unidades o tipos distintos: no se pueden ponderar."
        )
    componentes = tuple(
        Componente(codigo, exacto(lambda q=q: q / total), unidad, tipo)
        for (codigo, unidad, tipo), q in cantidades.items()
    )
    ids = ", ".join(str(r["id"]) for r in usos)
    return Receta(
        id=usos[0]["id"],
        producto=producto,
        componentes=componentes,
        fuente=usos[0]["fuente"] if len(usos) == 1 else f"recetas n.º {ids}, por toneladas",
        vigente_desde=min(date.fromisoformat(r["vigente_desde"]) for r in usos),
    )


def _precio_en_el_calculo(datos: Mapping[str, Any], c: Componente, calculo: int) -> Decimal:
    """El precio de un componente tal como lo usó el cálculo, en la moneda del cálculo."""
    entradas, resultado = datos["entradas"], datos["resultado"]
    if c.tipo == "comprado":
        precio = entradas["precios_comprados"].get(c.codigo, {}).get("convertido")
    elif c.codigo in resultado["por_tonelada"]:
        precio = resultado["por_tonelada"][c.codigo]
    else:
        precio = entradas["de_otro_calculo"].get(c.codigo, {}).get("costo")
    if precio is None:
        raise ValueError(f"El cálculo n.º {calculo} no guarda el precio de {c.codigo}.")
    return Decimal(precio)


def _en_la_moneda(caso: Session, calculo: CalculoGuardado, moneda: str):
    if calculo.moneda == moneda:
        return lambda valor: valor

    def convertir(valor: Decimal) -> Decimal:
        try:
            return equivalencia_del_cierre(
                caso, valor, calculo.moneda, moneda, calculo.periodo
            ).convertido
        except SinTasaDelDia as error:
            raise ValueError(
                f"El cálculo n.º {calculo.id} está en {calculo.moneda} y el presupuesto en "
                f"{moneda}: falta la tasa del BCV del cierre de {calculo.periodo}. {error}"
            ) from None

    return convertir


def mezclas_publicadas(
    sesion_ins: Session, sesion_caso: Session, descripciones: Collection[str], moneda: str
) -> MezclasPropias:
    """Receta, costo de planta por tonelada y precio de cada componente de cada mezcla propia que
    usa el presupuesto (`descripciones`: las de sus insumos), del último cálculo publicado, en
    `moneda` (véase el encabezado del módulo). Sin mezcla propia, todo vacío."""
    mezclas = MezclasPropias()
    for codigo, calculo in sorted(costos_propios_publicados(sesion_ins).items()):
        descripcion = descripcion_de_costo_propio(codigo)
        if not codigo.startswith(PREFIJO_DE_MEZCLA) or descripcion not in descripciones:
            continue
        producto = codigo[len(PREFIJO_DE_MEZCLA) :]
        datos = json.loads(calculo.instantanea)
        planta = datos["resultado"]["planta_por_t"]
        if planta is None:
            raise ValueError(f"El cálculo n.º {calculo.id} no tiene costo de planta por tonelada.")
        receta = _receta_del_periodo(datos["entradas"]["recetas"], producto, calculo.id)
        convertir = _en_la_moneda(sesion_caso, calculo, moneda)
        for c in receta.componentes:
            precio = convertir(_precio_en_el_calculo(datos, c, calculo.id))
            anterior = mezclas.precio_de_componente.setdefault(c.codigo, precio)
            if anterior != precio:
                raise ValueError(
                    f"El componente {c.codigo} tiene dos precios en los cálculos publicados de "
                    "las mezclas del presupuesto: la proyección lo variaría con uno solo."
                )
        mezclas.recetas[descripcion] = receta
        mezclas.costo_planta_por_t[descripcion] = convertir(Decimal(planta))
        mezclas.calculos[descripcion] = calculo.id
    return mezclas


# --- La versión ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Version:
    id: int
    proyecto: str
    codigo: str
    presupuesto: Presupuesto
    composiciones: dict[str, ComposicionAPU]
    parametros: ParametrosCosto


def _version(sesion: Session, proyecto: str, codigo: str) -> _Version:
    version_id = version_de(sesion, proyecto, codigo)  # `LookupError` si no existe
    modelo = sesion.get(models.Presupuesto, version_id)
    nombre = modelo.proyecto.nombre
    catalogo = Catalogo(sesion)
    return _Version(
        id=version_id,
        proyecto=nombre,
        codigo=codigo,
        presupuesto=cargar_presupuesto(sesion, nombre, codigo, catalogo),
        composiciones=composiciones_de_presupuesto(sesion, nombre, codigo, catalogo),
        parametros=ParametrosCosto(
            fcas=modelo.fcas,
            bono_alimentacion=modelo.bono_alimentacion,
            administracion=modelo.administracion,
            utilidad=modelo.utilidad,
        ),
    )


def _descripciones(composiciones: Mapping[str, ComposicionAPU]) -> list[str]:
    return sorted(
        {
            linea.descripcion
            for apu in composiciones.values()
            for linea in (*apu.materiales, *apu.equipos, *apu.mano_obra)
        }
    )


def inicio_de_la_linea_base(sesion: Session, version_id: int) -> date | None:
    """La fecha de inicio del calendario de la última línea base de control de esa versión."""
    fila = sesion.scalars(
        select(models.LineaBaseControl)
        .where(models.LineaBaseControl.presupuesto_id == version_id)
        .order_by(models.LineaBaseControl.desde.desc(), models.LineaBaseControl.id.desc())
    ).first()
    return None if fila is None else fila.calendario.fecha_inicio


@dataclass(frozen=True)
class SerieOfrecida:
    codigo: str
    nombre: str


def _series_ofrecidas(moneda: str) -> list[SerieOfrecida]:
    """Las series que un insumo puede seguir: las viales y, en Bs, también la tasa (en un
    presupuesto en USD la proyección no la admite, fila 78)."""
    ofrecidas = [SerieOfrecida(s.codigo, s.nombre) for s in SERIES_VIALES]
    if moneda == "Bs":
        ofrecidas.append(SerieOfrecida(SERIE_TASA, "Tasa de referencia del BCV (Bs por USD)"))
    return ofrecidas


@dataclass(frozen=True)
class InsumosDeLaObra:
    proyecto: str
    version: str
    moneda: str
    insumos: list[str]
    componentes: list[str]
    mezclas: dict[str, int]
    series: list[SerieOfrecida]
    inicio_linea_base: date | None


def insumos_de_la_obra(
    sesion_caso: Session, sesion_ins: Session, proyecto: str, codigo: str
) -> InsumosDeLaObra:
    """Lo que la pantalla ofrece para declarar el mapa de series: los insumos de los APU (sin las
    mezclas que se recalculan con su receta), los componentes de esas recetas, las series que se
    admiten en la moneda del presupuesto y el inicio de la línea base, si hay."""
    v = _version(sesion_caso, proyecto, codigo)
    descripciones = _descripciones(v.composiciones)
    moneda = v.presupuesto.moneda
    mezclas = mezclas_publicadas(sesion_ins, sesion_caso, descripciones, moneda)
    return InsumosDeLaObra(
        proyecto=v.proyecto,
        version=codigo,
        moneda=moneda,
        insumos=[d for d in descripciones if d not in mezclas.recetas],
        componentes=sorted(mezclas.precio_de_componente),
        mezclas=mezclas.calculos,
        series=_series_ofrecidas(moneda),
        inicio_linea_base=inicio_de_la_linea_base(sesion_caso, v.id),
    )


# --- Proyectar y comprobar ------------------------------------------------------------------------


@dataclass(frozen=True)
class ProyeccionDeLaObra:
    proyecto: str
    version: str
    moneda: str
    inicio: date
    inicio_de: str  # «linea_base» o «declarado»
    parametros: ParametrosProyeccion
    proyeccion: Proyeccion
    mezclas: dict[str, int]


@dataclass(frozen=True)
class ComprobacionDeLaObra:
    proyecto: str
    version: str
    moneda: str
    parametros: ParametrosProyeccion
    comprobacion: Comprobacion
    mezclas: dict[str, int]


def _argumentos(mezclas: MezclasPropias) -> dict[str, Any]:
    return {
        "recetas": mezclas.recetas,
        "costo_planta_por_t": mezclas.costo_planta_por_t,
        "precio_de_componente": mezclas.precio_de_componente,
    }


def proyectar_obra(
    sesion_caso: Session,
    sesion_ins: Session,
    proyecto: str,
    codigo: str,
    mapa: Mapping[str, str],
    *,
    inicio: date | None = None,
    **parametros: int,
) -> ProyeccionDeLaObra:
    """La proyección de la versión con los parámetros de D-V-3 (`parametros`: meses,
    trayectorias, semilla, ventana_meses) y el mapa declarado. El inicio, el declarado o el de la
    línea base (véase el encabezado del módulo)."""
    v = _version(sesion_caso, proyecto, codigo)
    origen = INICIO_DECLARADO
    if inicio is None:
        inicio, origen = inicio_de_la_linea_base(sesion_caso, v.id), INICIO_DE_LA_LINEA_BASE
    if inicio is None:
        raise ValueError(SIN_INICIO)
    p = ParametrosProyeccion(inicio=inicio, **parametros)
    mapa_series = MapaSeries(mapa)
    moneda = v.presupuesto.moneda
    mezclas = mezclas_publicadas(sesion_ins, sesion_caso, _descripciones(v.composiciones), moneda)
    historia = historia_para_proyectar(sesion_caso, mapa_series, p)
    proyeccion = proyectar(
        v.presupuesto,
        v.composiciones,
        v.parametros,
        historia,
        mapa_series,
        p,
        **_argumentos(mezclas),
    )
    return ProyeccionDeLaObra(
        v.proyecto, codigo, moneda, inicio, origen, p, proyeccion, mezclas.calculos
    )


def comprobar_obra(
    sesion_caso: Session,
    sesion_ins: Session,
    proyecto: str,
    codigo: str,
    mapa: Mapping[str, str],
    *,
    hoy: date,
    **parametros: int,
) -> ComprobacionDeLaObra:
    """La comprobación hacia atrás de la versión sobre toda la historia guardada hasta el último
    día del mes anterior a `hoy` (los cortes ponen su propio inicio; `hoy` no interviene en
    ellos). `parametros`: meses, trayectorias (por corte), semilla y ventana_meses."""
    v = _version(sesion_caso, proyecto, codigo)
    p = ParametrosProyeccion(inicio=hoy, **parametros)
    mapa_series = MapaSeries(mapa)
    moneda = v.presupuesto.moneda
    mezclas = mezclas_publicadas(sesion_ins, sesion_caso, _descripciones(v.composiciones), moneda)
    hasta = hoy.replace(day=1) - timedelta(days=1)
    historia = historia_mensual(sesion_caso, series_del_mapa(mapa_series), date.min, hasta)
    comprobacion = comprobar_hacia_atras(
        v.presupuesto,
        v.composiciones,
        v.parametros,
        historia,
        mapa_series,
        p,
        **_argumentos(mezclas),
    )
    return ComprobacionDeLaObra(v.proyecto, codigo, moneda, p, comprobacion, mezclas.calculos)
