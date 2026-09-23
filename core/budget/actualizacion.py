"""UC‑02: revalorar un presupuesto guardado con una lista de precios nueva (Sesión I1).

`actualizar_precios` cose las piezas que ya existen sin tocar ninguna: carga el presupuesto
anterior (`cargar_presupuesto`), reconstruye sus APU con la lista nueva (`Catalogo.composicion`),
vuelve a elaborar con **las mismas cantidades y los mismos parámetros de costo** (`elaborar`, que
audita siempre) y guarda la versión nueva (`guardar_presupuesto`). Ninguna composición se edita:
lo único que cambia es la lista de precios que la valora.

Además persiste las dos tablas del histórico de UC‑02: `CambioPrecio` (qué insumo cambió y cuánto,
en `core.catalog.precios`) e `IncidenciaCambio` (qué le hizo ese cambio al precio unitario de cada
partida del presupuesto). Ese registro es el que alimentará al módulo predictivo de la Sesión I6.

El `Comparativo` es la salida para el usuario: una fila por renglón con su precio unitario antes y
después, y la incidencia de cada partida en la variación del total. Sus celdas son `Decimal`
—el `DataFrame` es de tipo `object`, nunca `float`— porque un comparativo de precios que redondea
al pasar por pandas deja de cuadrar con el presupuesto que compara (CLAUDE.md §2.3).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from pandas import DataFrame
from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget.curva import PeriodoPlan

# `_buscar` y `_parametros_de` son ayudantes del módulo hermano del mismo paquete: el contrato
# `Presupuesto` no lleva los `ParametrosCosto` (insuficiencia registrada en la bitácora de
# I0.5) y duplicar aquí su lectura de la fila sería repetir la única definición que existe.
from core.budget.persistencia import (
    _buscar,
    _parametros_de,
    cargar_presupuesto,
    guardar_presupuesto,
)
from core.budget.presupuesto import ResultadoElaboracion, elaborar
from core.catalog import Catalogo
from core.catalog.precios import registrar_cambios, variacion_relativa
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto

__all__ = ["COLUMNAS_COMPARATIVO", "Comparativo", "actualizar_precios"]

#: Columnas del comparativo, en el orden en que se presentan.
COLUMNAS_COMPARATIVO = (
    "codigo_partida",
    "descripcion",
    "cantidad",
    "pu_anterior",
    "pu_nuevo",
    "variacion_pct",
    "total_anterior",
    "total_nuevo",
    "incidencia_pct",
)

CERO = Decimal(0)
CIEN = Decimal(100)


# `eq=False`: comparar dos `Comparativo` compararía sus `DataFrame`, cuyo `==` devuelve otro
# `DataFrame` en vez de un booleano. La igualdad no significa nada aquí; el dato sí.
@dataclass(frozen=True, slots=True, eq=False)
class Comparativo:
    """Informe comparativo entre la versión anterior de un presupuesto y la nueva (RF‑13).

    `tabla` trae una fila por renglón con las columnas de `COLUMNAS_COMPARATIVO`:

    - `variacion_pct`: cuánto varió el precio unitario de esa partida, en porcentaje;
    - `incidencia_pct`: cuánto aportó esa partida a la variación del presupuesto, en porcentaje
      sobre el total anterior. Las incidencias suman la variación porcentual del total, porque el
      precio unitario es una función afín de los precios de los insumos.

    `insumos_afectados` es cuántos insumos cambiaron de precio entre la lista anterior y la nueva
    (`core.catalog.precios.insumos_afectados`, ya persistidos por `registrar_cambios`), **hayan o
    no** afectado a este presupuesto en particular: un cambio en un insumo que no participa de
    ninguna partida de este presupuesto deja `variacion` en cero sin que el cambio deje de ser
    real. Quien confirma la transacción decide con este campo, no con `variacion` (hallazgo de la
    ronda de corrección 1: `variacion == 0` no distingue «nada cambió» de «cambió algo que no
    afecta a este presupuesto»).
    """

    tabla: DataFrame
    total_anterior: Decimal
    total_nuevo: Decimal
    insumos_afectados: int

    @property
    def variacion(self) -> Decimal:
        """Variación absoluta del total, en la moneda del presupuesto."""
        return self.total_nuevo - self.total_anterior

    @property
    def variacion_pct(self) -> Decimal:
        """Variación del total en porcentaje."""
        return _porcentaje(self.variacion, self.total_anterior)


def actualizar_precios(
    session: Session,
    proyecto_nombre: str,
    codigo_presupuesto: str,
    lista_nueva: models.ListaPrecios,
    codigo_nuevo: str,
    plan: Sequence[PeriodoPlan] | None = None,
) -> tuple[ResultadoElaboracion, Comparativo]:
    """Revalora un presupuesto con `lista_nueva` y lo guarda como versión `codigo_nuevo`.

    Devuelve la elaboración nueva —presupuesto e informe de auditoría, que se genera siempre
    (principio 7 de CLAUDE.md §2)— y el comparativo contra la versión anterior, que sigue intacta
    y reconstruyéndose con su propia lista.

    El presupuesto nuevo se fecha en la vigencia de `lista_nueva`, que es cuando pasan a valer esos
    precios, y conserva la moneda y los cuatro parámetros de costo del anterior: lo único que se
    mueve son los precios. Sin `plan` no lleva curva y la regla R2 lo hace constar como INFO.

    No confirma la transacción: como `guardar_presupuesto`, la deja abierta para que el llamador
    acepte la versión nueva o la descarte (UC‑02, flujo 7a). Quien confirma decide mirando
    `Comparativo.insumos_afectados`, no `Comparativo.variacion`: si ningún insumo cambió de precio,
    el presupuesto nuevo es idéntico al anterior y no hay nada que guardar (flujo 3a). Si sí
    cambiaron insumos pero ninguno participa de este presupuesto, `variacion` también da cero,
    pero el cambio es real y su historial (`CambioPrecio`, `IncidenciaCambio`) debe quedar
    registrado igual.
    """
    modelo = _buscar(session, proyecto_nombre, codigo_presupuesto)
    parametros = _parametros_de(modelo)
    lista_anterior = modelo.lista_precios
    catalogo = Catalogo(session)

    anterior = cargar_presupuesto(session, proyecto_nombre, codigo_presupuesto, catalogo)
    items = [partida.item for partida in anterior.partidas]
    composiciones = {
        codigo: catalogo.composicion(codigo, fecha=lista_nueva.fecha_vigencia, lista=lista_nueva)
        for codigo in dict.fromkeys(item.codigo_partida for item in items)
    }
    nuevo = elaborar(
        items,
        composiciones,
        parametros,
        codigo=codigo_nuevo,
        fecha=lista_nueva.fecha_vigencia,
        moneda=anterior.moneda,
        plan=plan,
    )
    guardar_presupuesto(
        session,
        nuevo.presupuesto,
        nuevo.informe,
        proyecto=modelo.proyecto,
        lista=lista_nueva,
        parametros=parametros,
    )

    cambios = registrar_cambios(session, lista_anterior, lista_nueva)
    _registrar_incidencias(session, cambios, anterior, nuevo.presupuesto)
    return nuevo, _comparar(anterior, nuevo.presupuesto, len(cambios))


# ---------------------------------------------------------------------------------------------
# Incidencia de cada cambio en las partidas del presupuesto
# ---------------------------------------------------------------------------------------------


def _registrar_incidencias(
    session: Session,
    cambios: Sequence[models.CambioPrecio],
    anterior: Presupuesto,
    nuevo: Presupuesto,
) -> list[models.IncidenciaCambio]:
    """Una `IncidenciaCambio` por cada par (cambio de precio, partida del presupuesto que lo usa).

    Los dos precios unitarios son los de la partida con la lista anterior y con la nueva, tal como
    define docs/modelo_datos.md §2.2. Cuando varios insumos suben en la misma partida, cada cambio
    registra ese mismo par: repartir el efecto entre ellos exigiría una columna que la entidad no
    tiene, y el reparto ya está en el comparativo.

    Idempotente, como `registrar_cambios`: si esos cambios ya tienen su incidencia registrada,
    devuelve la existente en vez de duplicarla. Repetir UC‑02 con el mismo par de listas es
    normal (el usuario descarta la versión nueva y vuelve a intentarlo) y la tabla que alimentará
    el módulo predictivo de I6 no puede llenarse de filas repetidas.
    """
    if not cambios:
        return []

    registradas = list(
        session.scalars(
            select(models.IncidenciaCambio)
            .where(models.IncidenciaCambio.cambio_id.in_([cambio.id for cambio in cambios]))
            .order_by(models.IncidenciaCambio.id)
        )
    )
    if registradas:
        return registradas

    precios_anteriores = _precio_unitario_por_partida(anterior)
    precios_nuevos = _precio_unitario_por_partida(nuevo)
    partidas = _partidas_por_insumo(
        session, [cambio.insumo_id for cambio in cambios], list(precios_anteriores)
    )

    incidencias = [
        models.IncidenciaCambio(
            cambio_id=cambio.id,
            partida_id=partida.id,
            precio_unitario_anterior=precios_anteriores[partida.codigo],
            precio_unitario_nuevo=precios_nuevos[partida.codigo],
            variacion=variacion_relativa(
                precios_anteriores[partida.codigo], precios_nuevos[partida.codigo]
            ),
        )
        for cambio in cambios
        for partida in partidas.get(cambio.insumo_id, ())
    ]
    session.add_all(incidencias)
    session.flush()
    return incidencias


def _partidas_por_insumo(
    session: Session, insumos: Sequence[int], codigos: Sequence[str]
) -> dict[int, list[models.Partida]]:
    """Qué partidas del presupuesto llevan cada insumo, según la composición del catálogo.

    Cada partida aparece **una sola vez** por insumo: nada impide que una partida repita el mismo
    insumo en dos líneas de su composición (`composicion_apu` no tiene clave única por partida e
    insumo), y sin eliminar el repetido el `join` registraría dos incidencias idénticas para el
    mismo cambio de precio.
    """
    filas = session.execute(
        select(models.ComposicionAPU.insumo_id, models.Partida)
        .join(models.Partida, models.Partida.id == models.ComposicionAPU.partida_id)
        .where(
            models.ComposicionAPU.insumo_id.in_(insumos),
            models.Partida.codigo.in_(codigos),
        )
        .order_by(models.Partida.codigo)
    ).all()
    por_insumo: dict[int, list[models.Partida]] = {}
    for insumo_id, partida in filas:
        partidas = por_insumo.setdefault(insumo_id, [])
        if all(registrada.id != partida.id for registrada in partidas):
            partidas.append(partida)
    return por_insumo


def _precio_unitario_por_partida(presupuesto: Presupuesto) -> dict[str, Decimal]:
    """Precio unitario de cada código de partida del presupuesto.

    Dos renglones del mismo código comparten APU y, por tanto, precio unitario: el diccionario los
    colapsa sin perder información.
    """
    return {
        partida.item.codigo_partida: partida.resultado.precio_unitario
        for partida in presupuesto.partidas
    }


# ---------------------------------------------------------------------------------------------
# Comparativo
# ---------------------------------------------------------------------------------------------


def _comparar(anterior: Presupuesto, nuevo: Presupuesto, insumos_afectados: int) -> Comparativo:
    """Arma la tabla renglón por renglón. Los dos presupuestos tienen los mismos ítems y orden."""
    total_anterior = anterior.total
    filas = [
        _fila(uno, otro, total_anterior)
        for uno, otro in zip(anterior.partidas, nuevo.partidas, strict=True)
    ]
    return Comparativo(
        tabla=DataFrame(filas, columns=list(COLUMNAS_COMPARATIVO)),
        total_anterior=total_anterior,
        total_nuevo=nuevo.total,
        insumos_afectados=insumos_afectados,
    )


def _fila(
    anterior: PartidaPresupuestada, nuevo: PartidaPresupuestada, total_anterior: Decimal
) -> dict[str, object]:
    if anterior.item.codigo_partida != nuevo.item.codigo_partida:
        raise ValueError(
            "los presupuestos comparados no tienen los mismos renglones: "
            f"{anterior.item.codigo_partida} frente a {nuevo.item.codigo_partida}"
        )
    return {
        "codigo_partida": anterior.item.codigo_partida,
        "descripcion": anterior.item.descripcion,
        "cantidad": anterior.item.cantidad,
        "pu_anterior": anterior.resultado.precio_unitario,
        "pu_nuevo": nuevo.resultado.precio_unitario,
        "variacion_pct": _porcentaje(
            nuevo.resultado.precio_unitario - anterior.resultado.precio_unitario,
            anterior.resultado.precio_unitario,
        ),
        "total_anterior": anterior.total,
        "total_nuevo": nuevo.total,
        "incidencia_pct": _porcentaje(nuevo.total - anterior.total, total_anterior),
    }


def _porcentaje(variacion: Decimal, base: Decimal) -> Decimal:
    """La variación como porcentaje de la base. Una base nula no varía: no hay de qué."""
    return variacion / base * CIEN if base else CERO
