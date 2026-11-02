"""Agregar y quitar líneas del APU de la versión, y su antes y después (MP-7, Tarea 26).

Para solventar una crisis de precio o de material (diseño de montar un presupuesto, §11 meta 5), la
pestaña APU de una versión guardada agrega una línea (un insumo de la lista de la versión, o uno
nuevo con el precio que se teclea) y quita otra, además de cambiar cantidades, rendimiento e insumo
como antes. Todo es en la copia de la versión (DA-SF-7): el catálogo no cambia. El borrador vivo lo
edita `aplicacion.hoja_edicion` (`agregar_linea_apu`, `quitar_linea_apu`) con estas funciones
puras; los cambios del borrador cuentan la línea que entra o sale (`hoja.cambios_entre`) y guardar
la escribe en `linea_composicion_version` (el núcleo resuelve su insumo por tipo y descripción: uno
nuevo queda con `insumo_id` nulo).

`antes_y_despues` dice, para Control de obra, qué cambió cada partida cuyo APU difiere del de la
línea base: su costo directo unitario, su duración y el término de la obra por rendimientos
(Tarea 21) y el punto de equilibrio con `core.budget.valor_ganado.equilibrio_proyectado` (sin
tocar el núcleo). Cada partida se mide sola: el efecto es el de cambiar SOLO su APU en la línea
base.

Sin FastAPI ni Streamlit (RM-1); `Decimal` siempre.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.errores import HojaInvalida
from aplicacion.parametros_de_costo import parametros_de_version
from aplicacion.plan_rendimientos import (
    PlanDemasiadoLargo,
    duraciones,
    paralelas_del_plan,
    plan_por_rendimientos,
)
from core import models
from core.budget.instantanea import plan_de_version
from core.budget.persistencia import cargar_presupuesto
from core.budget.valor_ganado import equilibrio_proyectado
from core.budget.valuaciones import linea_base_vigente
from core.catalog import Catalogo
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ModalidadManoObra,
    ParametrosCosto,
)
from core.contracts.presupuesto import Presupuesto
from core.costing.motor import calcular_apu

__all__ = [
    "MENSAJE_SIN_VERSION",
    "MENSAJE_TIPO",
    "MENSAJE_UNA_LINEA",
    "MENSAJE_YA_NO_ESTA",
    "PartidaAntesYDespues",
    "MonedasDistintas",
    "SinVersionGuardada",
    "agregar_linea",
    "antes_y_despues",
    "linea_base_de",
    "quitar_linea",
]

#: El campo de la composición de cada tipo de línea, como los llama el catálogo.
_CAMPOS = {"material": "materiales", "equipo": "equipos", "mano_obra": "mano_obra"}

MENSAJE_TIPO = "El tipo de línea debe ser material, equipo o mano de obra."
MENSAJE_UNA_LINEA = "Un APU necesita al menos una línea."
MENSAJE_YA_NO_ESTA = "Esa línea ya no está en el APU: vuelva a cargarlo."
MENSAJE_SIN_VERSION = (
    "Las líneas del APU se agregan y se quitan en una versión guardada: guarde primero la versión."
)
#: Los topes de `linea_composicion_version` (`descripcion` String(300), `unidad` String(20)).
LARGO_DESCRIPCION = 300
LARGO_UNIDAD = 20


class MonedasDistintas(Exception):  # noqa: N818
    """La version esta en otra moneda que la linea base: sus montos no se comparan."""

    def __init__(self, version: str, moneda: str, linea_base: str, moneda_base: str) -> None:
        super().__init__(version)
        self.texto = (
            f"La versión {version} está en {moneda} y la línea base {linea_base} en "
            f"{moneda_base}: no se comparan montos en monedas distintas."
        )

    def __str__(self) -> str:
        return self.texto


class SinVersionGuardada(Exception):  # noqa: N818
    """Las líneas se agregan y se quitan en el borrador de una versión guardada: el de una obra en
    blanco no tiene lista de la versión y su primera versión toma los APU del catálogo tal cual
    (`hoja.con_precios_de_la_lista` exige las mismas líneas)."""

    def __str__(self) -> str:
        return MENSAJE_SIN_VERSION


def _rubro(composicion: ComposicionAPU, tipo: str) -> tuple:
    if tipo not in _CAMPOS:
        raise HojaInvalida(MENSAJE_TIPO)
    return getattr(composicion, _CAMPOS[tipo])


def _modalidad(texto: str | None) -> ModalidadManoObra:
    try:
        return ModalidadManoObra(texto or ModalidadManoObra.JORNAL)
    except ValueError:
        raise HojaInvalida("La modalidad de la mano de obra debe ser jornal o destajo.") from None


def agregar_linea(
    composicion: ComposicionAPU,
    tipo: str,
    *,
    descripcion: str,
    unidad: str,
    cantidad: Decimal,
    precio: Decimal,
    depreciacion: Decimal | None = None,
    modalidad: str | None = None,
) -> ComposicionAPU:
    """El APU con una línea nueva al final del rubro `tipo` (`material`, `equipo`, `mano_obra`).

    `precio` es el precio del material o del equipo, o el sueldo de la mano de obra (el jornal
    diario, o el precio por unidad de partida a destajo). La unidad solo la lleva un material; la
    depreciación (mayor que 0 y a lo sumo 1), solo un equipo; la modalidad (jornal por omisión),
    solo la mano de obra. Un insumo que ya está en el rubro no se repite: se edita su cantidad.
    `HojaInvalida` con el texto que ve la persona."""
    grupo = _rubro(composicion, tipo)
    descripcion = descripcion.strip()
    if not descripcion:
        raise HojaInvalida("Escriba la descripción del insumo nuevo.")
    if len(descripcion) > LARGO_DESCRIPCION:
        raise HojaInvalida(f"La descripción admite a lo sumo {LARGO_DESCRIPCION} caracteres.")
    if any(linea.descripcion == descripcion for linea in grupo):
        raise HojaInvalida("Ese insumo ya está en este rubro del APU: edítelo en la tabla.")
    unidad = unidad.strip()
    if tipo == "material":
        if not unidad:
            raise HojaInvalida("Escriba la unidad del material, por ejemplo m3.")
        if len(unidad) > LARGO_UNIDAD:
            raise HojaInvalida(f"La unidad admite a lo sumo {LARGO_UNIDAD} caracteres.")
    if cantidad < 0:
        raise HojaInvalida("La cantidad no puede ser negativa.")
    if precio < 0:
        raise HojaInvalida("El precio no puede ser negativo.")
    nueva: LineaMaterial | LineaEquipo | LineaManoObra
    if tipo == "material":
        nueva = LineaMaterial(descripcion, unidad, cantidad, precio)
    elif tipo == "equipo":
        if depreciacion is None:
            raise HojaInvalida("Escriba la depreciación del equipo, por ejemplo 0,005.")
        if not Decimal(0) < depreciacion <= Decimal(1):
            raise HojaInvalida(
                "La depreciación debe ser mayor que 0 y a lo sumo 1, por ejemplo 0,005."
            )
        nueva = LineaEquipo(descripcion, cantidad, precio, depreciacion)
    else:
        nueva = LineaManoObra(descripcion, cantidad, precio, _modalidad(modalidad))
    return replace(composicion, **{_CAMPOS[tipo]: (*grupo, nueva)})


def quitar_linea(composicion: ComposicionAPU, tipo: str, indice: int) -> ComposicionAPU:
    """El APU sin la línea `indice` (desde 0) del rubro `tipo`. No deja un APU sin líneas."""
    grupo = _rubro(composicion, tipo)
    if not 0 <= indice < len(grupo):
        raise HojaInvalida(MENSAJE_YA_NO_ESTA)
    total = len(composicion.materiales) + len(composicion.equipos) + len(composicion.mano_obra)
    if total == 1:
        raise HojaInvalida(MENSAJE_UNA_LINEA)
    return replace(composicion, **{_CAMPOS[tipo]: (*grupo[:indice], *grupo[indice + 1 :])})


# --- antes y después respecto de la línea base (Control de obra) --------------------------------


@dataclass(frozen=True, slots=True)
class PartidaAntesYDespues:
    """Una partida cuyo APU cambió respecto de la línea base: su costo directo unitario y su
    duración (días hábiles, por rendimientos) con el APU de la línea base y con el de la versión,
    y el término de la obra (días) y el punto de equilibrio (en la moneda de la línea base) si
    solo cambiara esta partida. `None`: no se pudo calcular (plan de más de 500 días, o sin
    partidas que duren)."""

    partida: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    costo_antes: Decimal
    costo_despues: Decimal
    duracion_antes: Decimal
    duracion_despues: Decimal
    termino_antes: int | None
    termino_despues: int | None
    equilibrio_antes: Decimal | None
    equilibrio_despues: Decimal | None


def _version_de_la_linea_base(sesion: Session, proyecto: str) -> models.Presupuesto | None:
    """La version de la linea base vigente hoy de `proyecto` (la de mayor `desde`), o `None`."""
    linea_base = linea_base_vigente(sesion, proyecto, date.max)
    if linea_base is None:
        return None
    return sesion.get(models.Presupuesto, linea_base.presupuesto_id)


def linea_base_de(sesion: Session, proyecto: str) -> str | None:
    """El codigo de la version de la linea base vigente de `proyecto`, o `None` si no tiene."""
    modelo = _version_de_la_linea_base(sesion, proyecto)
    return None if modelo is None else modelo.codigo


def _version(sesion: Session, proyecto: str, codigo: str) -> models.Presupuesto:
    modelo = sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
    ).first()
    if modelo is None:
        raise HojaInvalida(f"La versión {codigo} no existe en la obra {proyecto}.")
    return modelo


def _apus(presupuesto: Presupuesto) -> dict[str, ComposicionAPU]:
    """El APU de cada partida del presupuesto, por código (el del primer renglón)."""
    apus: dict[str, ComposicionAPU] = {}
    for partida in presupuesto.partidas:
        apus.setdefault(partida.item.codigo_partida, partida.apu)
    return apus


def _termino(
    presupuesto: Presupuesto, apus: dict[str, ComposicionAPU], paralelas: frozenset[str]
) -> tuple[dict[str, Decimal], int | None]:
    """La duración de cada partida y los días del plan por rendimientos (una cuadrilla, las
    paralelas de la línea base), o `None` si el plan no se puede hacer."""
    items = [p.item for p in presupuesto.partidas]
    lista = duraciones(items, apus, {})
    por_partida = {d.codigo: d.dias for d in lista}
    try:
        plan = plan_por_rendimientos(lista, paralelas=paralelas)
    except PlanDemasiadoLargo:
        return por_partida, None
    return por_partida, len(plan) or None


def antes_y_despues(
    sesion: Session, proyecto: str, catalogo: Catalogo, version_nueva: str
) -> list[PartidaAntesYDespues]:
    """Por partida de `version_nueva` cuyo APU difiere del de la línea base vigente de `proyecto`
    (en el orden del presupuesto), su antes y su después (`PartidaAntesYDespues`).

    Antes: la línea base con sus parámetros de costo. Después: la línea base con SOLO el APU de esa
    partida cambiado por el de la versión (mismos parámetros y cantidades), de modo que el efecto
    es el de la partida. Costo: costo directo unitario (`calcular_apu`). Duración y término: el
    plan por rendimientos de la Tarea 21 (una cuadrilla; las paralelas que muestra el plan de la
    línea base). Punto de equilibrio: `equilibrio_proyectado` con la venta de la línea base, el
    costo variable con la diferencia de costo directo × cantidad de la partida, el costo fijo de la
    línea base escalado por término nuevo ÷ término base y la curva de la línea base; antes, el
    mismo cálculo sin cambios (que es el punto de equilibrio de la línea base).

    Sin línea base, o si `version_nueva` es la de la línea base, lista vacía; en otra moneda que la
    línea base, `MonedasDistintas` (no se mezclan montos). `HojaInvalida` si la
    versión no existe.
    """
    base_modelo = _version_de_la_linea_base(sesion, proyecto)
    if base_modelo is None:
        return []
    codigo_base = base_modelo.codigo
    nueva_modelo = _version(sesion, proyecto, version_nueva)
    if nueva_modelo.id == base_modelo.id:
        return []
    if nueva_modelo.moneda != base_modelo.moneda:
        raise MonedasDistintas(
            nueva_modelo.codigo, nueva_modelo.moneda, codigo_base, base_modelo.moneda
        )
    base = cargar_presupuesto(sesion, proyecto, codigo_base, catalogo)
    nueva = cargar_presupuesto(sesion, proyecto, nueva_modelo.codigo, catalogo)
    parametros: ParametrosCosto = parametros_de_version(base_modelo)
    apus_base, apus_nueva = _apus(base), _apus(nueva)
    cambiadas = [c for c, apu in apus_nueva.items() if c in apus_base and apus_base[c] != apu]
    if not cambiadas:
        return []
    plan = plan_de_version(sesion, base_modelo)
    paralelas = paralelas_del_plan(plan) if plan else frozenset()
    duracion_base, termino_base = _termino(base, apus_base, paralelas)
    variable = sum((p.item.cantidad * p.resultado.costo_directo for p in base.partidas), Decimal(0))
    fijo = variable * parametros.administracion

    def punto(costo_variable: Decimal, termino: int | None) -> Decimal | None:
        if termino_base is None or termino is None:
            return None
        return equilibrio_proyectado(
            venta=base.total,
            costo_variable=costo_variable,
            costo_fijo=fijo,
            dias_plan=termino_base,
            dias_proyectados=termino,
            reajuste_reconocido=Decimal(0),
            curva=base.curva,
        ).punto

    filas = []
    for codigo in cambiadas:
        antes, despues = apus_base[codigo], apus_nueva[codigo]
        cantidad = sum(
            (p.item.cantidad for p in base.partidas if p.item.codigo_partida == codigo),
            Decimal(0),
        )
        costo_antes = calcular_apu(antes, parametros).costo_directo
        costo_despues = calcular_apu(despues, parametros).costo_directo
        duracion_despues, termino_despues = _termino(
            base, {**apus_base, codigo: despues}, paralelas
        )
        filas.append(
            PartidaAntesYDespues(
                partida=codigo,
                descripcion=antes.descripcion,
                unidad=antes.unidad,
                cantidad=cantidad,
                costo_antes=costo_antes,
                costo_despues=costo_despues,
                duracion_antes=duracion_base.get(codigo, Decimal(0)),
                duracion_despues=duracion_despues.get(codigo, Decimal(0)),
                termino_antes=termino_base,
                termino_despues=termino_despues,
                equilibrio_antes=punto(variable, termino_base),
                equilibrio_despues=punto(
                    variable + cantidad * (costo_despues - costo_antes), termino_despues
                ),
            )
        )
    return filas
