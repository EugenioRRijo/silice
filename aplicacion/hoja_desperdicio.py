"""El desperdicio de los materiales editado en la Hoja (F5 vial, punto 1; 2026-11-13).

Decisión y simulación: `docs/bitacora/2026-11-13-desperdicio-en-la-hoja.md` (opción a). La Hoja
edita la neta y el porcentaje, nunca el producto (riesgo del diseño §12), como Componer:

- **Al editar** (E6, `hoja_edicion.editar_apu`), cada material trae su porcentaje; con uno no vacío
  y distinto de cero, la cantidad escrita es la **neta** y el servidor guarda
  `neta × (1 + porcentaje / 100)`, exacta (`con_desperdicio_en_materiales`). La traza queda en el
  borrador (`BorradorVivo.desperdicios`, en memoria): editar no escribe en la base, y descartar el
  borrador no deja nada.
- **Al mirar**, la vista usa primero las trazas del borrador y después las vigentes de la base
  (`unir`), con la misma regla de emparejado de siempre (descripción, unidad y cantidad), y dice
  quién guardó el desglose de la base que muestra (`desglose_de_la_vista`, acta DS-48g).
- **Al guardar la versión** (`guardar_con_la_version`, en la misma transacción que la versión), la
  traza del borrador que sigue casando con su línea se escribe como un guardado nuevo de la
  partida, **unida a las vigentes** (`por_guardar`): la traza vive por código de partida, así que
  sin la unión el catálogo y las otras versiones perderían la suya.
- **El desglose es un cambio** (anexo A.6 del desenredo; acta DS-3, opción B, y DS-48): una línea
  de material que sigue igual en la versión abierta y en el borrador pero muestra otro desglose
  cuenta como un cambio (`cambios_de_desglose`, campo `desperdicio`). Si es lo único que cambió,
  guardar escribe solo las trazas, sin versión nueva (`hoja_guardado`).

Límite conocido (en la bitácora): si después Componer vuelve a guardar la partida, su guardado
manda y la versión de la Hoja deja de mostrar el desglose; la cantidad sigue siendo la correcta y
nunca se muestra un desglose falso.

`aplicacion/hoja.py` (congelado por el experimento) no cambia. Sin FastAPI; `Decimal` siempre.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from aplicacion import hoja
from aplicacion.cifras import BLANCOS, texto_de_cifra
from aplicacion.composicion import ComposicionInvalida
from aplicacion.desperdicio import (
    GuardadoDelDesglose,
    TrazaDesperdicio,
    cantidad_con_desperdicio,
    guardar_trazas,
    neta_y_porcentaje,
    porcentaje_escrito,
    trazas_de_las_filas,
    trazas_vigentes,
)
from aplicacion.errores import HojaInvalida
from core.contracts.apu import ComposicionAPU

if TYPE_CHECKING:
    from aplicacion.hoja_borradores import BorradorVivo

__all__ = [
    "CAMPO_DESGLOSE",
    "MENSAJE_DESPERDICIOS",
    "DesperdicioDeLinea",
    "GuardadoDePartida",
    "TrazasDePartida",
    "anotables",
    "cambios_de_desglose",
    "cambios_del_borrador",
    "con_desperdicio_en_materiales",
    "cuantos_desgloses",
    "desglose_de_la_vista",
    "desgloses_visibles",
    "es_de_desglose",
    "guardar_con_la_version",
    "por_guardar",
    "sin_lo_de_la_base",
    "trazas_del_borrador",
    "unir",
    "vigentes_de_la_base",
]

#: El navegador manda un porcentaje por material, en el orden del APU; otra cuenta solo llega de
#: una ventana con otro APU.
MENSAJE_DESPERDICIOS = (
    "materiales: los desperdicios enviados no corresponden a las líneas de materiales del APU: "
    "vuelva a cargarlo."
)
#: El campo del `CambioEditado` de un desglose que cambió (la clave es la de la línea del APU,
#: `{partida}|material|{n}`, como las de `hoja.cambios_entre`).
CAMPO_DESGLOSE = "desperdicio"

_CERO = Decimal(0)

#: Las trazas vigentes del desperdicio de una partida, por su código (la ruta las lee de la base
#: del caso con `aplicacion.desperdicio.trazas_vigentes`).
TrazasDePartida = Callable[[str], Sequence[TrazaDesperdicio]]
#: Quién guardó el desglose vigente de una partida, por su código (la ruta lo lee de la base del
#: caso con `aplicacion.desperdicio.quien_guardo_el_desglose`).
GuardadoDePartida = Callable[[str], GuardadoDelDesglose | None]


@dataclass(frozen=True, slots=True)
class DesperdicioDeLinea:
    """La neta y el porcentaje de desperdicio de una fila de Materiales (desde 1), «0,50 + 4 %»
    (F5 vial, punto 1). La cantidad de la fila ya los incluye: esto solo la explica. `neta` y
    `porcentaje`, con coma decimal, son lo que siembra los campos de la Hoja (2026-11-13)."""

    fila: int
    texto: str
    neta: str
    porcentaje: str


def con_desperdicio_en_materiales(
    composicion: ComposicionAPU, porcentajes: Sequence[str]
) -> tuple[ComposicionAPU, tuple[TrazaDesperdicio, ...]]:
    """`composicion`, cuyas cantidades de material son las netas ya leídas, con la cantidad con
    desperdicio en cada material de porcentaje no vacío ni cero, y la traza de cada material.

    Un material sin porcentaje (vacío o cero) deja su línea como está y su traza es de 0 %: la
    Hoja dice «esta línea no lleva desperdicio», y `unir` deja por ella la vigente de la misma
    descripción, unidad y cantidad sin mostrarla ni guardarla (depuración del 2026-11-15, L2).

    `HojaInvalida` si no hay un porcentaje por material (`MENSAJE_DESPERDICIOS`) o si uno no es
    una cifra de 0 a menos de 100 («materiales, fila N: el desperdicio «…» …»)."""
    if len(porcentajes) != len(composicion.materiales):
        raise HojaInvalida(MENSAJE_DESPERDICIOS)
    lineas = []
    trazas = []
    for numero, (linea, texto) in enumerate(
        zip(composicion.materiales, porcentajes, strict=True), start=1
    ):
        porcentaje = _CERO
        if texto.strip(BLANCOS):  # el recorte de `aplicacion/cifras` (árbitro 13/11, M4)
            try:
                porcentaje = porcentaje_escrito(texto, f"materiales, fila {numero}", ": ")
            except ComposicionInvalida as error:
                raise HojaInvalida(str(error)) from error
        if porcentaje.is_zero():  # también «-0» y «0,0»: la línea queda como está
            porcentaje, cantidad = _CERO, linea.cantidad
            lineas.append(linea)
        else:
            cantidad = cantidad_con_desperdicio(linea.cantidad, porcentaje)
            lineas.append(replace(linea, cantidad=cantidad))
        trazas.append(
            # recortadas como las de Componer (`texto_de_celda`): unir y por_guardar las comparan
            # con las vigentes (Argon, ronda 2 del árbitro, 2026-11-13)
            TrazaDesperdicio(
                linea.descripcion.strip(),
                linea.unidad.strip(),
                linea.cantidad,
                porcentaje,
                cantidad,
            )
        )
    return replace(composicion, materiales=tuple(lineas)), tuple(trazas)


def _clave(traza: TrazaDesperdicio) -> tuple:
    return (traza.descripcion.strip(), traza.unidad.strip(), traza.cantidad)


def unir(
    nuevas: Sequence[TrazaDesperdicio], vigentes: Sequence[TrazaDesperdicio]
) -> list[TrazaDesperdicio]:
    """Las trazas `nuevas` (las del borrador) y, detrás, las `vigentes` de otra línea: una vigente
    con la misma descripción, unidad y cantidad que una nueva se deja (otro desglose de la misma
    cantidad: manda el más nuevo). Una nueva de 0 % (la línea sin desperdicio) deja la vigente de
    su línea y no se devuelve: no hay desglose que mostrar ni que guardar."""
    propias = {_clave(t) for t in nuevas}
    return [
        *(t for t in nuevas if not t.desperdicio_pct.is_zero()),
        *(t for t in vigentes if _clave(t) not in propias),
    ]


def desgloses_visibles(
    filas: Sequence[Mapping[str, str]],
    propias: Sequence[TrazaDesperdicio],
    vigentes: Sequence[TrazaDesperdicio],
) -> list[tuple[int, TrazaDesperdicio]]:
    """El número de fila (desde 1) y la traza de cada fila de materiales que la Hoja muestra con
    desglose: las `propias` del borrador antes que las `vigentes` de la partida (`unir`)."""
    return trazas_de_las_filas(filas, unir(propias, vigentes))


def desglose_de_la_vista(
    filas: Sequence[Mapping[str, str]],
    propias: Sequence[TrazaDesperdicio],
    vigentes: Sequence[TrazaDesperdicio],
    guardado: Callable[[], GuardadoDelDesglose | None],
) -> tuple[tuple[DesperdicioDeLinea, ...], GuardadoDelDesglose | None]:
    """Lo que la pestaña APU dice del desperdicio de las `filas` de materiales: la neta y el
    porcentaje de cada una con desglose (`desgloses_visibles`) y quién guardó el de la base
    (`guardado`, que solo se lee entonces) si alguna muestra uno de las `vigentes`. Si todas
    muestran el del borrador, aún sin guardar, no hay responsable que decir (acta DS-48g)."""
    visibles = desgloses_visibles(filas, propias, vigentes)
    lineas = tuple(
        DesperdicioDeLinea(
            fila,
            neta_y_porcentaje(traza),
            texto_de_cifra(traza.cantidad_neta),
            texto_de_cifra(traza.desperdicio_pct),
        )
        for fila, traza in visibles
    )
    # solo si todo lo que se ve es lo guardado: una línea con un desglose del borrador aún sin
    # guardar no es de quien guardó la base (revisión de Neon, hallazgo 2; acta DS-120)
    de_la_base = bool(visibles) and all(traza in vigentes for _, traza in visibles)
    return lineas, guardado() if de_la_base else None


def anotables(
    trazas: Sequence[TrazaDesperdicio], vigentes: Sequence[TrazaDesperdicio]
) -> tuple[TrazaDesperdicio, ...]:
    """De las `trazas` de una edición, las que cambian algo frente a las `vigentes` de la partida:
    un 0 % de una línea que tiene desglose en la base (se le quita) y un desglose que no es igual
    al vigente. El navegador manda un porcentaje por material en cada «Aplicar» (también si solo
    cambió el rendimiento): un 0 % donde la base no tiene desglose, o el mismo desglose que ya está
    guardado, no se anota en el borrador; si se anotara, taparía lo que Componer guarde después y
    la versión siguiente lo borraría (revisión de Neon, hallazgo 1; acta DS-121)."""
    con_desglose = {_clave(v) for v in vigentes}
    guardados = {(_clave(v), v.cantidad_neta, v.desperdicio_pct) for v in vigentes}
    return tuple(
        t
        for t in trazas
        if (t.desperdicio_pct.is_zero() and _clave(t) in con_desglose)
        or (
            not t.desperdicio_pct.is_zero()
            and (_clave(t), t.cantidad_neta, t.desperdicio_pct) not in guardados
        )
    )


def cambios_de_desglose(
    base: hoja.Borrador,
    actual: hoja.Borrador,
    desperdicios: Mapping[str, Sequence[TrazaDesperdicio]],
    vigentes: Mapping[str, Sequence[TrazaDesperdicio]],
) -> list[hoja.CambioEditado]:
    """Un `CambioEditado("apu", "{partida}|material|{n}", "desperdicio", antes, después)` por
    línea de material cuyo desglose («0,8 + 25 %», o «» sin él) cambia de la versión abierta
    `base` al borrador `actual`: en `base` con las `vigentes` de la partida y en `actual` con las
    trazas del borrador (`desperdicios`) delante (`desgloses_visibles`).

    Solo cuenta la línea que es la misma en las dos (misma posición, insumo y cantidad): si su
    cantidad cambió, ese cambio ya lo registra `hoja.cambios_entre` y el desglose viaja con él.
    Una partida que no está en `base` (borrador en blanco, partida nueva) no cuenta."""
    cambios: list[hoja.CambioEditado] = []
    for codigo, propias in desperdicios.items():
        antes, ahora = base.composiciones.get(codigo), actual.composiciones.get(codigo)
        if antes is None or ahora is None:
            continue
        de_la_base = vigentes.get(codigo, ())
        mostradas_antes = _textos(desgloses_visibles(hoja.filas_de_apu(antes)[0], (), de_la_base))
        mostradas_ahora = _textos(
            desgloses_visibles(hoja.filas_de_apu(ahora)[0], propias, de_la_base)
        )
        for fila, (linea_antes, linea_ahora) in enumerate(
            zip(antes.materiales, ahora.materiales, strict=False), start=1
        ):
            texto_antes, texto_ahora = mostradas_antes.get(fila, ""), mostradas_ahora.get(fila, "")
            if linea_antes == linea_ahora and texto_antes != texto_ahora:
                cambios.append(
                    hoja.CambioEditado(
                        "apu", f"{codigo}|material|{fila}", CAMPO_DESGLOSE, texto_antes, texto_ahora
                    )
                )
    return cambios


def _textos(visibles: Sequence[tuple[int, TrazaDesperdicio]]) -> dict[int, str]:
    return {fila: neta_y_porcentaje(traza) for fila, traza in visibles}


def es_de_desglose(cambio: hoja.CambioEditado) -> bool:
    """Si `cambio` es el de un desglose (`cambios_de_desglose`) y no el de una celda."""
    return cambio.objeto == "apu" and cambio.campo == CAMPO_DESGLOSE


def cuantos_desgloses(cambios: Sequence[hoja.CambioEditado]) -> int:
    """Cuántos de `cambios` son de un desglose (`ResumenHoja.desgloses`)."""
    return sum(1 for cambio in cambios if es_de_desglose(cambio))


def cambios_del_borrador(vivo: BorradorVivo) -> list[hoja.CambioEditado]:
    """Los cambios que cuenta la vista (`hoja_vista.calculo`): los de las celdas de la versión
    abierta (o de un borrador en blanco) al borrador `vivo` (`hoja.cambios_entre`) y, detrás, los
    de sus desgloses, contra las vigentes anotadas al editar (`cambios_de_desglose`)."""
    if vivo.abierta is not None:
        base = vivo.abierta.borrador
    else:
        base = hoja.Borrador(fecha=vivo.borrador.fecha, moneda=vivo.borrador.moneda)
    return [
        *hoja.cambios_entre(base, vivo.borrador),
        *cambios_de_desglose(base, vivo.borrador, vivo.desperdicios, vivo.vigentes_del_desperdicio),
    ]


def trazas_del_borrador(vivo: BorradorVivo, codigo: str) -> tuple[TrazaDesperdicio, ...]:
    """Las trazas que la Hoja dejó en el borrador `vivo` para la partida `codigo` (aún sin
    guardar)."""
    return vivo.desperdicios.get(codigo, ())


def por_guardar(
    borrador: hoja.Borrador,
    desperdicios: Mapping[str, Sequence[TrazaDesperdicio]],
    vigentes: Callable[[str], Sequence[TrazaDesperdicio]],
) -> dict[str, list[TrazaDesperdicio]]:
    """Lo que el guardado de `borrador` escribe por partida: las trazas de `desperdicios` que
    siguen casando con una línea de material del borrador, unidas a las `vigentes` de la partida.
    Una partida sin traza que case, o cuya unión es ya la vigente, no escribe nada."""
    salida: dict[str, list[TrazaDesperdicio]] = {}
    for codigo, propias in desperdicios.items():
        composicion = borrador.composiciones.get(codigo)
        if composicion is None or not propias:
            continue
        filas = hoja.filas_de_apu(composicion)[0]
        casadas = [traza for _, traza in trazas_de_las_filas(filas, propias)]
        if not casadas:
            continue
        antes = list(vigentes(codigo))
        unidas = unir(casadas, antes)
        if unidas != antes:
            salida[codigo] = unidas
    return salida


def guardar_con_la_version(
    sesion: Session,
    vivo: BorradorVivo,
    borrador: hoja.Borrador,
    *,
    ahora: datetime,
    responsable: str,
) -> dict[str, list[TrazaDesperdicio]]:
    """Escribe en `sesion` las trazas del borrador que `por_guardar` pide, con su `responsable` (la
    cuenta de la sesión, acta DS-48g), y las devuelve por partida. **Sin `commit`**: va en la
    transacción de la versión (`hoja_guardado`), o sola si solo cambió el desglose (anexo A.6), y
    quien guarda confirma o deshace todo junto."""
    pendientes = por_guardar(
        borrador, vivo.desperdicios, lambda codigo: trazas_vigentes(sesion, codigo)
    )
    for codigo, trazas in pendientes.items():
        guardar_trazas(sesion, codigo, trazas, ahora=ahora, responsable=responsable)
    return pendientes


def sin_lo_de_la_base(
    base: hoja.Borrador,
    actual: hoja.Borrador,
    desperdicios: Mapping[str, Sequence[TrazaDesperdicio]],
    vigentes: Mapping[str, Sequence[TrazaDesperdicio]],
) -> dict[str, tuple[TrazaDesperdicio, ...]]:
    """Las trazas de `desperdicios` de las partidas cuyo desglose todavía cambia contra las
    `vigentes` (`cambios_de_desglose`). La de una partida que ya muestra lo de la base (otra
    persona o Componer guardaron ese mismo desglose) sobra en el borrador: si se quedara, taparía
    el próximo guardado de la partida en la base (arbitraje de A.6, acta DS-48i)."""
    return {
        codigo: tuple(trazas)
        for codigo, trazas in desperdicios.items()
        if cambios_de_desglose(base, actual, {codigo: trazas}, vigentes)
    }


def vigentes_de_la_base(
    sesion: Session, vivo: BorradorVivo
) -> dict[str, tuple[TrazaDesperdicio, ...]]:
    """Las trazas vigentes en la base de cada partida cuyo desglose editó la Hoja en `vivo`."""
    return {codigo: tuple(trazas_vigentes(sesion, codigo)) for codigo in vivo.desperdicios}
