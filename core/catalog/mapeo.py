"""Conversión entre modelos persistidos y contratos de interfaz.

Frontera del **catálogo**, en las **dos** direcciones (docs/modelo_datos.md §8): modelo → contrato
para reconstruir, contrato → modelo para cargar. En todo el sistema la frontera modelo ↔ contrato
existe en exactamente dos módulos —este y `core/budget/persistencia.py`, que hace lo propio con el
presupuesto (ADR 12 de docs/arquitectura.md)—; unirlos habría hecho que `core.catalog` dependiera
de `core.verification` por el `InformeAuditoria`. El repositorio orquesta la sesión y las consultas,
pero no construye modelos a partir de contratos ni al revés; si al catálogo le aparece una
conversión nueva, su sitio es este módulo.

Los modelos se usan cualificados (`models.X`) y los contratos por su nombre, para que nunca se
confundan los siete pares homónimos.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from core import models
from core.catalog.errores import CatalogoIncompleto
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ModalidadManoObra,
    Rendimiento,
    TipoRendimiento,
)
from core.contracts.dominio import Dominio

# ---------------------------------------------------------------------------------------------
# Modelo -> contrato
# ---------------------------------------------------------------------------------------------


def a_composicion(
    partida: models.Partida,
    lista: models.ListaPrecios,
    rendimiento: models.Rendimiento,
) -> ComposicionAPU:
    """Arma la `ComposicionAPU` del contrato con los precios de `lista` y el rendimiento dado.

    Las líneas se recorren por `orden`, que es el del documento original: sin él las tuplas del
    contrato no serían iguales a las del fixture de la línea base.
    """
    precios = {precio.insumo_id: precio.precio for precio in lista.precios}
    materiales: list[LineaMaterial] = []
    equipos: list[LineaEquipo] = []
    mano_obra: list[LineaManoObra] = []

    for linea in sorted(partida.composicion, key=lambda linea: linea.orden):
        insumo = linea.insumo
        precio = precios.get(insumo.id)
        if precio is None:
            raise CatalogoIncompleto(
                f"el insumo {insumo.codigo} ({insumo.descripcion}) no tiene precio en la lista "
                f"'{lista.nombre}'; no se puede valorar la partida {partida.codigo}"
            )
        if insumo.tipo == models.TipoInsumo.MATERIAL:
            if not insumo.unidad:
                raise CatalogoIncompleto(
                    f"el material {insumo.codigo} ({insumo.descripcion}) no declara unidad; "
                    f"no se puede valorar la partida {partida.codigo}"
                )
            materiales.append(
                LineaMaterial(insumo.descripcion, insumo.unidad, linea.cantidad, precio)
            )
        elif insumo.tipo == models.TipoInsumo.EQUIPO:
            if linea.depreciacion is None:
                raise CatalogoIncompleto(
                    f"el equipo {insumo.codigo} ({insumo.descripcion}) no declara depreciación "
                    f"en la partida {partida.codigo}"
                )
            equipos.append(
                LineaEquipo(insumo.descripcion, linea.cantidad, precio, linea.depreciacion)
            )
        else:
            mano_obra.append(
                LineaManoObra(
                    insumo.descripcion,
                    linea.cantidad,
                    precio,
                    ModalidadManoObra(linea.modalidad)
                    if linea.modalidad
                    else ModalidadManoObra.JORNAL,
                )
            )

    return ComposicionAPU(
        codigo_partida=partida.codigo,
        descripcion=partida.descripcion,
        unidad=partida.unidad,
        rendimiento=rendimiento.valor,
        materiales=tuple(materiales),
        equipos=tuple(equipos),
        mano_obra=tuple(mano_obra),
    )


def a_rendimiento(rendimiento: models.Rendimiento) -> Rendimiento:
    """Convierte un rendimiento persistido en el `Rendimiento` del contrato."""
    return Rendimiento(
        codigo_partida=rendimiento.partida.codigo,
        valor=rendimiento.valor,
        tipo=TipoRendimiento(rendimiento.tipo),
        fecha=rendimiento.fecha,
        condiciones=rendimiento.condiciones,
        referencia_ejecucion=(
            rendimiento.ejecucion.referencia if rendimiento.ejecucion is not None else None
        ),
    )


# ---------------------------------------------------------------------------------------------
# Contrato -> modelo
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LineaCatalogo:
    """Una línea de una `ComposicionAPU` traducida al vocabulario del catálogo.

    Aplana las tres tuplas del contrato (materiales, equipos, mano de obra) en la secuencia única y
    ordenada que persiste `models.ComposicionAPU`, y unifica los tres nombres del importe unitario
    (`precio` de material y equipo, `sueldo` de mano de obra) en uno solo. `modalidad` solo la
    llevan las líneas de mano de obra, igual que `depreciacion` solo la llevan los equipos.
    """

    tipo: models.TipoInsumo
    descripcion: str
    unidad: str | None
    precio: Decimal
    cantidad: Decimal
    depreciacion: Decimal | None
    modalidad: ModalidadManoObra | None = None


def lineas_de(composicion: ComposicionAPU) -> list[LineaCatalogo]:
    """Aplana un APU del contrato en el orden canónico: materiales, equipos y mano de obra.

    Ese orden es el que se guarda en `ComposicionAPU.orden` y el que `a_composicion` deshace al
    reconstruir; los dos sentidos dependen de esta única definición.
    """
    lineas = [
        LineaCatalogo(
            tipo=models.TipoInsumo.MATERIAL,
            descripcion=material.descripcion,
            unidad=material.unidad,
            precio=material.precio,
            cantidad=material.cantidad,
            depreciacion=None,
        )
        for material in composicion.materiales
    ]
    lineas += [
        LineaCatalogo(
            tipo=models.TipoInsumo.EQUIPO,
            descripcion=equipo.descripcion,
            unidad=None,
            precio=equipo.precio,
            cantidad=equipo.cantidad,
            depreciacion=equipo.depreciacion,
        )
        for equipo in composicion.equipos
    ]
    lineas += [
        LineaCatalogo(
            tipo=models.TipoInsumo.MANO_OBRA,
            descripcion=obrero.descripcion,
            unidad=None,
            precio=obrero.sueldo,
            cantidad=obrero.cantidad,
            depreciacion=None,
            modalidad=obrero.modalidad,
        )
        for obrero in composicion.mano_obra
    ]
    return lineas


def a_modelo_partida(composicion: ComposicionAPU, dominio: Dominio) -> models.Partida:
    """Construye la cabecera persistente de un APU. El dominio es un dato, no una rama de código."""
    return models.Partida(
        codigo=composicion.codigo_partida,
        descripcion=composicion.descripcion,
        unidad=composicion.unidad,
        dominio=str(dominio),
    )


def a_modelo_insumo(linea: LineaCatalogo, codigo: str) -> models.Insumo:
    """Construye el insumo de catálogo que describe una línea. `codigo` lo genera el repositorio.

    El código depende de lo que ya hay en la base (siguiente número del tipo, o sufijo de variante),
    que es una consulta, no una conversión: por eso entra como argumento ya resuelto.
    """
    return models.Insumo(
        codigo=codigo,
        tipo=linea.tipo.value,
        descripcion=linea.descripcion,
        unidad=linea.unidad,
    )


def a_modelo_lineas(
    lineas: Sequence[LineaCatalogo],
    partida: models.Partida,
    insumos: Sequence[models.Insumo],
) -> list[models.ComposicionAPU]:
    """Construye las líneas persistentes, numeradas por su posición en el orden canónico.

    `insumos` son los insumos ya resueltos por el repositorio, uno por línea y en el mismo orden.
    """
    return [
        models.ComposicionAPU(
            partida_id=partida.id,
            insumo_id=insumo.id,
            cantidad=linea.cantidad,
            depreciacion=linea.depreciacion,
            modalidad=linea.modalidad.value if linea.modalidad is not None else None,
            orden=orden,
        )
        for orden, (linea, insumo) in enumerate(zip(lineas, insumos, strict=True))
    ]


def a_modelo_rendimiento(
    rendimiento: Rendimiento,
    partida: models.Partida,
    ejecucion: models.Ejecucion | None = None,
) -> models.Rendimiento:
    """Construye el rendimiento persistente. `ejecucion` ya viene resuelta por el repositorio."""
    return models.Rendimiento(
        partida_id=partida.id,
        valor=rendimiento.valor,
        tipo=rendimiento.tipo.value,
        fecha=rendimiento.fecha,
        condiciones=rendimiento.condiciones,
        ejecucion_id=ejecucion.id if ejecucion is not None else None,
    )


def a_modelo_rendimiento_estimado(
    composicion: ComposicionAPU, partida: models.Partida, fecha: date, condiciones: str
) -> models.Rendimiento:
    """El rendimiento ESTIMADO que declara un APU del contrato, listo para persistir.

    Pasa por `contracts.Rendimiento` a propósito: así el valor queda validado por las invariantes
    del contrato (mayor que cero) antes de tocar la base de datos.

    `condiciones` no tiene valor por defecto a propósito: RF‑33 (spec §3.3) exige que ningún
    rendimiento se persista sin declarar junto a él las condiciones en que se estimó, y los dos
    caminos que llaman a esta función —`cargar_composicion` y `reemplazar_composicion`— la exigen
    y la validan antes de llegar aquí. Un valor por defecto habría dejado abierta la puerta que
    RF‑33 quiere cerrada: que un llamador nuevo la omita y persista un `Rendimiento` con
    `condiciones=''` en silencio.
    """
    return a_modelo_rendimiento(
        Rendimiento(
            codigo_partida=composicion.codigo_partida,
            valor=composicion.rendimiento,
            tipo=TipoRendimiento.ESTIMADO,
            fecha=fecha,
            condiciones=condiciones,
        ),
        partida,
    )
