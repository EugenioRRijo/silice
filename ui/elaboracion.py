"""Orquestacion de la elaboracion desde la interfaz, sin Streamlit (INV-043, fase C3).

Antes vivia dentro de `ui/paginas/componer.py`, que asi pintaba, orquestaba «cantidades ->
elaborar -> exportar», calculaba y persistia a la vez (criterio S, spec de cierre §4). Aqui queda
la orquestacion contra `core.budget` y `core.catalog`; las paginas solo pintan y deciden los
mensajes. Sin Streamlit, sin `pandas` y sin `ui.caso`: cada funcion recibe lo que necesita y se
prueba como funcion (`tests/unit/test_elaboracion.py`). Lo vigila
`tests/unit/test_arquitectura.py::test_ui_respeta_sus_importaciones_prohibidas`.

Es el unico modulo de `ui/` sin pagina que escribe filas en la base (regla A-2 del plan de C3):
`guardar_composicion` y `declarar_rendimiento` (UC-01 3b, INV-088) escriben, pero no confirman;
el `commit` es de la pagina. Filas, no esquema:
`ui.caso.estado_caso` no escribe: lee con una conexion de solo lectura (RV-5).
"""

from __future__ import annotations

import dataclasses
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from core.budget import ResultadoElaboracion, elaborar, exportar_excel, plan_secuencial
from core.catalog import Catalogo, PropuestaRendimiento, proponer_rendimiento, registrar_rendimiento
from core.contracts import ComposicionAPU, Dominio, ItemComputo, ParametrosCosto, ResultadoAPU
from core.contracts.apu import Rendimiento, TipoRendimiento
from ui.composicion import (
    ComposicionInvalida,
    decimal_desde_texto,
    desglose,
    item_desde_cantidad,
    motivo_para_no_reemplazar,
    texto_de_celda,
)

if TYPE_CHECKING:
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from core.budget import GeneradorPlan, PeriodoPlan
    from core.contracts.presupuesto import Presupuesto
    from core.models import Partida
    from ml.normalization import PartidaSimilar

#: Columnas de la tabla de cantidades de obra: la clave interna de cada fila, no su rotulo.
COLUMNAS_CANTIDADES = ("codigo_partida", "cantidad", "origen_id")

#: Columnas de la tabla del plan de trabajo (UC-01, paso 6): una fila por partida y periodo.
COLUMNAS_PLAN = ("periodo", "codigo_partida", "fraccion")


def items_desde_filas(
    filas: Sequence[Mapping[str, object]], partidas_por_codigo: Mapping[str, Partida]
) -> tuple[list[ItemComputo], list[str]]:
    """Las filas de la tabla de cantidades de obra como `ItemComputo`, mas un aviso por fila mala.

    El origen es obligatorio (una cantidad sin origen no es trazable, y `item_desde_cantidad` la
    rechaza: no es un dato, es un hallazgo). El dominio de cada item es el que ya declara la
    cabecera de esa partida en el catalogo (`models.Partida.dominio`). Una fila todavia en blanco
    no es un aviso: es el estado normal de una tabla dinamica.
    """
    items: list[ItemComputo] = []
    avisos: list[str] = []
    for indice, fila in enumerate(filas, start=1):
        codigo, cantidad_texto, origen_id = (
            texto_de_celda(fila, clave) for clave in COLUMNAS_CANTIDADES
        )
        if not codigo and not cantidad_texto and not origen_id:
            continue  # fila dinamica todavia en blanco: no es un error, es el estado normal
        if not codigo or codigo not in partidas_por_codigo:
            avisos.append(f"cantidades de obra, fila {indice}: seleccione una partida del catalogo")
            continue
        partida = partidas_por_codigo[codigo]
        try:
            items.append(
                item_desde_cantidad(
                    codigo=codigo,
                    descripcion=partida.descripcion,
                    unidad=partida.unidad,
                    cantidad=cantidad_texto,
                    origen_id=origen_id,
                    dominio=Dominio(partida.dominio),
                )
            )
        except ComposicionInvalida as error:
            avisos.append(f"cantidades de obra, fila {indice}: {error}")
    return items, avisos


def elaborar_desde_catalogo(
    catalogo: Catalogo,
    items: Sequence[ItemComputo],
    codigo: str,
    fecha: date,
    moneda: str,
    plan: Sequence[PeriodoPlan] | GeneradorPlan = plan_secuencial,
) -> ResultadoElaboracion:
    """Elabora y audita el presupuesto de `items` con las composiciones del catalogo a `fecha`.

    UC-01, paso 6 (INV-087): `plan` es el plan de trabajo que distribuyo el proyectista
    (`plan_desde_filas`). Por defecto, `plan_secuencial` (una partida por dia, en el orden del
    presupuesto): la curva cierra exactamente en el total y R2 y R7 quedan limpias, y la linea base
    no cambia. Un plan que no reparte exactamente una vez cada partida lanza `PlanInvalido`.

    UC-01 3a (INV-072): pide solo las composiciones de los codigos que el catalogo tiene, el mismo
    criterio que `api/rutas/presupuestos.py`. Un item sin partida no lanza: `elaborar` lo deja en
    `ResultadoElaboracion.pendientes` y el informe lo declara con un hallazgo `PENDIENTE`.
    """
    existentes = {partida.codigo for partida in catalogo.partidas()}
    codigos_unicos = [
        codigo
        for codigo in dict.fromkeys(item.codigo_partida for item in items)
        if codigo in existentes
    ]
    composiciones = catalogo.composiciones(codigos_unicos, fecha=fecha)
    return elaborar(
        list(items),
        composiciones,
        ParametrosCosto(),
        codigo=codigo,
        fecha=fecha,
        moneda=moneda,
        plan=plan,
    )


def filas_desde_plan(plan: Sequence[PeriodoPlan]) -> list[dict[str, str]]:
    """UC-01, paso 6 (INV-087): el plan de trabajo como filas de la tabla editable, una por
    partida y periodo, con la fraccion como texto exacto (`str` del `Decimal`)."""
    return [
        {"periodo": periodo, "codigo_partida": codigo, "fraccion": str(fraccion)}
        for periodo, reparto in plan
        for codigo, fraccion in reparto
    ]


def plan_de(filas: Sequence[Mapping[str, object]] | None) -> list[PeriodoPlan] | GeneradorPlan:
    """UC-01, paso 6: el plan de las filas del proyectista o, sin filas, el plan por defecto
    (`plan_secuencial`). Decide aqui, no en la pagina (U-6 de la revision de C5)."""
    return plan_secuencial if filas is None else plan_desde_filas(filas)


def filas_del_plan_por_defecto(presupuesto: Presupuesto) -> list[dict[str, str]]:
    """Las filas del plan por defecto (`plan_secuencial`) sobre el presupuesto ya valorado: la
    tabla que la pagina precarga tras cada elaboracion sin plan del proyectista."""
    return filas_desde_plan(plan_secuencial(presupuesto))


def plan_desde_filas(filas: Sequence[Mapping[str, object]]) -> list[PeriodoPlan]:
    """UC-01, paso 6 (INV-087): las filas de la tabla del plan como plan de trabajo de `elaborar`.

    Los periodos siguen el orden de su primera fila, y cada uno reune las partidas de sus filas en
    su orden. Una fila en blanco se ignora (estado normal de una tabla dinamica); una a medias o
    con una fraccion que no es un decimal lanza `ComposicionInvalida` (un `ValueError`) con su
    numero de fila. Que cada partida sume exactamente 1 lo juzga `elaborar` (`PlanInvalido`): la
    regla del plan vive en `core.budget.curva`, no aqui.
    """
    periodos: dict[str, list[tuple[str, Decimal]]] = {}
    for indice, fila in enumerate(filas, start=1):
        periodo, codigo, fraccion = (texto_de_celda(fila, clave) for clave in COLUMNAS_PLAN)
        if not periodo and not codigo and not fraccion:
            continue  # fila dinamica todavia en blanco
        if not periodo or not codigo or not fraccion:
            raise ComposicionInvalida(
                f"plan de trabajo, fila {indice}: declare el periodo, la partida y la fraccion"
            )
        valor = decimal_desde_texto(fraccion, f"plan de trabajo, fila {indice}, fraccion")
        periodos.setdefault(periodo, []).append((codigo, valor))
    return [(periodo, tuple(reparto)) for periodo, reparto in periodos.items()]


def libro_excel(resultado: ResultadoElaboracion) -> tuple[bytes, str]:
    """El libro de Excel del presupuesto elaborado (con su hoja de auditoria) y su nombre."""
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / f"presupuesto_{resultado.presupuesto.codigo}.xlsx"
        libro = exportar_excel(resultado.presupuesto, resultado.informe, ruta)
        return libro.read_bytes(), libro.name


@dataclass(frozen=True, slots=True)
class Guardado:
    """Lo que dejo `guardar_composicion`: el desglose guardado o el motivo para no guardar."""

    resultado: ResultadoAPU | None = None
    motivo: str | None = None

    def __post_init__(self) -> None:
        if (self.resultado is None) == (self.motivo is None):
            raise ValueError("un Guardado lleva exactamente uno de los dos: resultado o motivo")


def guardar_composicion(
    catalogo: Catalogo,
    composicion: ComposicionAPU,
    dominio: Dominio,
    fecha: date,
    condiciones: str,
) -> Guardado:
    """Persiste la composicion: UC-10 si la partida no existe, UC-11 si ya existe.

    Sobre una partida existente, `motivo_para_no_reemplazar` decide antes de escribir: una
    composicion sin lineas borraria el desglose, y una cabecera distinta se descartaria en silencio
    (`reemplazar_composicion` solo sustituye lineas y rendimiento). En ese caso devuelve el motivo
    y no escribe nada. **No confirma**: el `commit` lo decide la pagina.
    """
    lista = catalogo.lista_vigente(fecha)
    try:
        partida = catalogo.partida(composicion.codigo_partida)
    except KeyError:
        catalogo.cargar_composicion(composicion, lista, dominio, fecha, condiciones)
    else:
        motivo = motivo_para_no_reemplazar(partida.descripcion, partida.unidad, composicion)
        if motivo is not None:
            return Guardado(motivo=motivo)
        catalogo.reemplazar_composicion(composicion, lista, dominio, fecha, condiciones)
    return Guardado(resultado=desglose(composicion))


# --- UC-01 3a: los pendientes, sus propuestas y la aceptacion (INV-072, D6) --------------------


@dataclass(frozen=True, slots=True)
class PendienteConPropuestas:
    """Un item pendiente y las partidas similares que se le proponen (o por que no las hay)."""

    item: ItemComputo
    similares: tuple[PartidaSimilar, ...] = ()
    falla: str | None = None


def propuestas_de_pendientes(
    partidas: Mapping[str, str], pendientes: Sequence[ItemComputo]
) -> tuple[PendienteConPropuestas, ...]:
    """Una entrada por pendiente, en su orden, con las partidas del catalogo parecidas a su
    descripcion (`partidas`: codigo -> descripcion). Sin pendientes devuelve `()` sin cargar nada.

    El emparejamiento es `ml.normalization.propuestas_para`, el mismo de la API (INV-081): un solo
    normalizador por elaboracion, y el criterio unico de fallas (una falla declarada deja al
    pendiente sin similares y con su `falla`; un defecto se propaga). `ml.normalization` se importa
    aqui, perezoso, como las demas ayudas de `ml`: no arrastra el extra, pero `ui/` no carga `ml`
    hasta que hay pendientes.
    """
    if not pendientes:
        return ()
    from ml.normalization import propuestas_para

    return tuple(
        PendienteConPropuestas(item, propuesta.similares, propuesta.falla)
        for item, propuesta in propuestas_para(partidas, pendientes)
    )


def aceptar_propuesta(
    items: Sequence[ItemComputo], pendiente: ItemComputo, codigo_elegido: str
) -> list[ItemComputo]:
    """UC-01 3a (D6): el item `pendiente` pasa a la partida propuesta que el usuario acepto. Los
    demas items no cambian; si `pendiente` no esta entre `items`, ValueError."""
    if pendiente not in items:
        raise ValueError(f"el item {pendiente.origen_id!r} no esta entre los items a elaborar")
    return [
        dataclasses.replace(item, codigo_partida=codigo_elegido) if item == pendiente else item
        for item in items
    ]


# --- UC-01 3b: la partida sin rendimiento vigente (INV-088) ------------------------------------


@dataclass(frozen=True, slots=True)
class RendimientoPorDeclarar:
    """Una partida sin rendimiento estimado vigente y la propuesta del historico (UC-06), o
    `None` si la partida no tiene ningun rendimiento registrado."""

    codigo_partida: str
    propuesta: PropuestaRendimiento | None


def rendimientos_por_declarar(
    sesion: Session, items: Sequence[ItemComputo], fecha: date
) -> tuple[RendimientoPorDeclarar, ...]:
    """UC-01 3b: las partidas de `items` sin rendimiento estimado vigente a `fecha`, en su orden,
    cada una con la propuesta de `proponer_rendimiento` (el rendimiento y su dispersion).

    Vigente es lo que `Catalogo.composicion` exige para reconstruir un APU: un rendimiento ESTIMADO
    de fecha no posterior a la del presupuesto. Los codigos sin partida no cuentan: quedan
    pendientes (flujo 3a).

    `Catalogo.composiciones` resuelve la lista de precios antes que los rendimientos, asi que sin
    lista vigente a `fecha` el `CatalogoIncompleto` es de la lista, no de 3b: se relanza aqui
    (`Catalogo.lista_vigente`) antes de clasificar nada (U-1 de la revision de C5).
    """
    catalogo = Catalogo(sesion)
    catalogo.lista_vigente(fecha)
    existentes = {partida.codigo for partida in catalogo.partidas()}
    codigos = [
        codigo
        for codigo in dict.fromkeys(item.codigo_partida for item in items)
        if codigo in existentes
    ]
    return tuple(
        RendimientoPorDeclarar(codigo, proponer_rendimiento(sesion, codigo))
        for codigo in codigos
        if not any(
            rendimiento.tipo is TipoRendimiento.ESTIMADO and rendimiento.fecha <= fecha
            for rendimiento in catalogo.rendimientos(codigo)
        )
    )


def declarar_rendimiento(
    sesion: Session, por_declarar: RendimientoPorDeclarar, tipo: TipoRendimiento, fecha: date
) -> Rendimiento:
    """UC-01 3b: registra el rendimiento propuesto con el tipo que declaro el proyectista.

    La elaboracion usa solo el rendimiento ESTIMADO vigente (`Catalogo.composicion`): declarado
    ESTIMADO, se registra a la `fecha` del presupuesto con condiciones generadas desde su
    procedencia (tipo, fecha, ejecucion y dispersion del propuesto). Declarado MEDIDO no se usa tal
    cual (esa politica es de `core/`, fuera del alcance de C5): `ValueError` y nada se registra.
    Sin propuesta, tambien `ValueError`. **No confirma**: el `commit` es de la pagina, como en
    `guardar_composicion`.
    """
    propuesta = por_declarar.propuesta
    codigo = por_declarar.codigo_partida
    if propuesta is None:
        raise ValueError(f"la partida {codigo} no tiene historico de rendimientos que proponer")
    if tipo is not TipoRendimiento.ESTIMADO:
        raise ValueError(
            f"la elaboracion usa el rendimiento estimado vigente de {codigo}: un rendimiento "
            "declarado medido no se usa tal cual; declare el propuesto como estimado para elaborar"
        )
    origen = propuesta.rendimiento
    dispersion = propuesta.dispersion
    referencia = f", ejecucion {origen.referencia_ejecucion}" if origen.referencia_ejecucion else ""
    condiciones = (
        f"propuesto del historico al elaborar (UC-01 3b): {origen.tipo.value} del {origen.fecha}"
        f"{referencia}; dispersion: {dispersion.observaciones} observaciones, rango "
        f"[{dispersion.minimo}, {dispersion.maximo}]"
    )
    return registrar_rendimiento(sesion, codigo, origen.valor, tipo, fecha, condiciones)
