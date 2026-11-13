"""El desperdicio de los materiales editado en la Hoja (F5 vial, punto 1; 2026-11-13).

Decisión y simulación: `docs/bitacora/2026-11-13-desperdicio-en-la-hoja.md` (opción a). La Hoja
edita la neta y el porcentaje, nunca el producto (riesgo del diseño §12), como Componer:

- **Al editar** (E6, `hoja_edicion.editar_apu`), cada material trae su porcentaje; con uno no vacío
  y distinto de cero, la cantidad escrita es la **neta** y el servidor guarda
  `neta × (1 + porcentaje / 100)`, exacta (`con_desperdicio_en_materiales`). La traza queda en el
  borrador (`BorradorVivo.desperdicios`, en memoria): editar no escribe en la base, y descartar el
  borrador no deja nada.
- **Al mirar**, la vista usa primero las trazas del borrador y después las vigentes de la base
  (`unir`), con la misma regla de emparejado de siempre (descripción, unidad y cantidad).
- **Al guardar la versión** (`guardar_con_la_version`, en la misma transacción que la versión), la
  traza del borrador que sigue casando con su línea se escribe como un guardado nuevo de la
  partida, **unida a las vigentes** (`por_guardar`): la traza vive por código de partida, así que
  sin la unión el catálogo y las otras versiones perderían la suya.

Límite conocido (en la bitácora): si después Componer vuelve a guardar la partida, su guardado
manda y la versión de la Hoja deja de mostrar el desglose; la cantidad sigue siendo la correcta y
nunca se muestra un desglose falso.

`aplicacion/hoja.py` (congelado por el experimento) no cambia. Sin FastAPI; `Decimal` siempre.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from aplicacion import hoja
from aplicacion.cifras import BLANCOS
from aplicacion.composicion import ComposicionInvalida
from aplicacion.desperdicio import (
    TrazaDesperdicio,
    cantidad_con_desperdicio,
    guardar_trazas,
    porcentaje_escrito,
    trazas_de_las_filas,
    trazas_vigentes,
)
from aplicacion.errores import HojaInvalida
from core.contracts.apu import ComposicionAPU

if TYPE_CHECKING:
    from aplicacion.hoja_borradores import BorradorVivo

__all__ = [
    "MENSAJE_DESPERDICIOS",
    "con_desperdicio_en_materiales",
    "guardar_con_la_version",
    "por_guardar",
    "trazas_del_borrador",
    "unir",
]

#: El navegador manda un porcentaje por material, en el orden del APU; otra cuenta solo llega de
#: una ventana con otro APU.
MENSAJE_DESPERDICIOS = (
    "materiales: los desperdicios enviados no corresponden a las líneas de materiales del APU: "
    "vuelva a cargarlo."
)


def con_desperdicio_en_materiales(
    composicion: ComposicionAPU, porcentajes: Sequence[str]
) -> tuple[ComposicionAPU, tuple[TrazaDesperdicio, ...]]:
    """`composicion`, cuyas cantidades de material son las netas ya leídas, con la cantidad con
    desperdicio en cada material de porcentaje no vacío ni cero, y la traza de cada uno.

    `HojaInvalida` si no hay un porcentaje por material (`MENSAJE_DESPERDICIOS`) o si uno no es
    una cifra de 0 a menos de 100 («materiales, fila N: el desperdicio «…» …»)."""
    if len(porcentajes) != len(composicion.materiales):
        raise HojaInvalida(MENSAJE_DESPERDICIOS)
    lineas = []
    trazas = []
    for numero, (linea, texto) in enumerate(
        zip(composicion.materiales, porcentajes, strict=True), start=1
    ):
        if not texto.strip(BLANCOS):  # el recorte de `aplicacion/cifras` (árbitro 13/11, M4)
            lineas.append(linea)
            continue
        try:
            porcentaje = porcentaje_escrito(texto, f"materiales, fila {numero}", ": ")
        except ComposicionInvalida as error:
            raise HojaInvalida(str(error)) from error
        if porcentaje.is_zero():
            lineas.append(linea)
            continue
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
    cantidad: manda el más nuevo)."""
    propias = {_clave(t) for t in nuevas}
    return [*nuevas, *(t for t in vigentes if _clave(t) not in propias)]


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
    sesion: Session, vivo: BorradorVivo, borrador: hoja.Borrador, *, ahora: datetime
) -> None:
    """Escribe en `sesion` las trazas del borrador que `por_guardar` pide. **Sin `commit`**: va en
    la transacción de la versión (`hoja_guardado`), que confirma o deshace todo junto."""
    pendientes = por_guardar(
        borrador, vivo.desperdicios, lambda codigo: trazas_vigentes(sesion, codigo)
    )
    for codigo, trazas in pendientes.items():
        guardar_trazas(sesion, codigo, trazas, ahora=ahora)
