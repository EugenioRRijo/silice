"""El desperdicio de un material: dentro de la cantidad y con su traza (F5 vial, tarea 3).

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §4 (punto 1, opción B),
construido con la decisión provisional 1 del 2026-11-06 (sin esperar al tutor; si el tutor quiere el
concepto en el contrato, opción A, esta traza es exactamente lo que se migraría al campo nuevo).

- **El núcleo no cambia.** La `LineaMaterial` lleva la cantidad con desperdicio,
  `neta × (1 + porcentaje / 100)`, en `Decimal` y sin redondear (`cantidad_con_desperdicio`): el
  motor la suma como siempre y el precio unitario recalculado cuadra con el que imprime un APU
  que cobra el desperdicio. Es el precedente de `adapters/civil/reglas.py` (`longitud * (1 +
  desperdicio)`).
- **La traza** (`TrazaDesperdicio`: la neta, el porcentaje y la cantidad que resultó) se guarda
  aparte, en la base del caso (`aplicacion/tablas_desperdicio.py`), por partida y en cada guardado
  de su composición (`guardar_trazas`; manda el último, `trazas_vigentes`).
- **Sin desincronizarse** (riesgo del diseño §12): una traza solo vale para la línea cuya cantidad
  guardada sigue siendo la que resultó (`con_desperdicio`). Si la cantidad cambió por otro camino,
  la traza ya no se muestra: Sílice nunca dice «0,50 + 4 %» de una cantidad que no es 0,52.
- Componer manda, por fila de materiales, la cantidad neta en `cantidad` y el porcentaje en
  `desperdicio` (texto con coma decimal, «4» es 4 %, de 0 a menos de 100); `aplicar_desperdicio`
  convierte esas filas en las de siempre (sin la clave, con la cantidad ya multiplicada) antes de
  pasarlas a `aplicacion.composicion`, que no cambia (archivo congelado del experimento).

Sin FastAPI ni Streamlit; `Decimal` siempre.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.cifras import CifraInvalida, cifra_escrita, texto_de_cifra
from aplicacion.composicion import ComposicionInvalida, texto_de_celda
from aplicacion.regla_desperdicio import TrazaDesperdicio, cantidad_con_desperdicio
from aplicacion.tablas_desperdicio import (
    GuardadoDeDesperdicio,
    LineaConDesperdicio,
    crear_esquema_desperdicio,
    hay_tablas_de_desperdicio,
)

__all__ = [
    "CLAVE",
    "TrazaDesperdicio",
    "aplicar_desperdicio",
    "cantidad_con_desperdicio",
    "con_desperdicio",
    "guardar_trazas",
    "leyenda",
    "neta_y_porcentaje",
    "porcentaje_escrito",
    "trazas_de_las_filas",
    "trazas_por_fila",
    "trazas_vigentes",
]

#: La clave del porcentaje en una fila de materiales de Componer.
CLAVE = "desperdicio"
_CIEN = Decimal(100)


def leyenda(traza: TrazaDesperdicio) -> str:
    """«0,52 (0,50 + 4 %)»: la cantidad que resultó (sin ceros de más), la neta y el porcentaje
    tal como se escribieron, con coma decimal y punto de miles."""
    return (
        f"{texto_de_cifra(traza.cantidad.normalize())} ({texto_de_cifra(traza.cantidad_neta)} + "
        f"{texto_de_cifra(traza.desperdicio_pct)} %)"
    )


def porcentaje_escrito(texto: str, lugar: str, separador: str = ", ") -> Decimal:
    """El porcentaje tecleado (coma decimal, de 0 a menos de 100), o `ComposicionInvalida` con
    «{lugar}{separador}el desperdicio «…» …». Componer dice «En Materiales, fila 2 («…»), el…»; la
    Hoja, «materiales, fila 2: el…», el prefijo con que ubica el error en su campo."""
    try:
        valor = cifra_escrita(texto)
    except CifraInvalida as error:
        raise ComposicionInvalida(
            f"{lugar}{separador}el desperdicio «{texto}» no se entiende como número. {error}"
        ) from error
    if not Decimal(0) <= valor < _CIEN:
        raise ComposicionInvalida(
            f"{lugar}{separador}el desperdicio «{texto}» debe estar entre 0 y 100 (es un "
            "porcentaje: 4 es 4 %)."
        )
    return valor


def trazas_por_fila(filas: Sequence[Mapping[str, str]]) -> list[tuple[int, TrazaDesperdicio]]:
    """Las trazas de las filas de materiales que traen desperdicio, cada una con su número de fila
    (desde 1). Mismas reglas y errores que `aplicar_desperdicio`."""
    trazas: list[tuple[int, TrazaDesperdicio]] = []
    for indice, fila in enumerate(filas, start=1):
        texto = texto_de_celda(fila, CLAVE)
        if not texto:
            continue
        lugar = f"En Materiales, fila {indice} («{texto_de_celda(fila, 'descripcion')}»)"
        porcentaje = porcentaje_escrito(texto, lugar)
        if porcentaje.is_zero():
            continue
        try:
            neta = cifra_escrita(texto_de_celda(fila, "cantidad"))
        except CifraInvalida:
            continue  # la conversión de siempre da el aviso de la cantidad
        trazas.append(
            (
                indice,
                TrazaDesperdicio(
                    texto_de_celda(fila, "descripcion"),
                    texto_de_celda(fila, "unidad"),
                    neta,
                    porcentaje,
                    cantidad_con_desperdicio(neta, porcentaje),
                ),
            )
        )
    return trazas


def aplicar_desperdicio(
    filas: Sequence[Mapping[str, str]],
) -> tuple[list[dict[str, str]], list[TrazaDesperdicio]]:
    """Las filas de materiales de siempre (sin la clave `desperdicio`) y la traza de las que lo
    traen. Con desperdicio, la `cantidad` de la fila pasa a ser la neta × (1 + porcentaje / 100).

    Un porcentaje vacío o cero deja la fila como está. `ComposicionInvalida`, con la fila y la
    descripción, si el porcentaje no es una cifra o no está entre 0 y 100. Si la cantidad neta no
    es una cifra, la fila sigue sin multiplicar y la conversión de siempre da su aviso.
    """
    por_fila = dict(trazas_por_fila(filas))
    salida: list[dict[str, str]] = []
    for indice, fila in enumerate(filas, start=1):
        limpia = {clave: valor for clave, valor in fila.items() if clave != CLAVE}
        traza = por_fila.get(indice)
        if traza is not None:
            limpia["cantidad"] = texto_de_cifra(traza.cantidad)
        salida.append(limpia)
    return salida, list(por_fila.values())


def _de_la_linea(fila: Mapping[str, str], traza: TrazaDesperdicio) -> bool:
    try:
        cantidad = cifra_escrita(texto_de_celda(fila, "cantidad"))
    except CifraInvalida:
        return False
    # `texto_de_celda` recorta la fila; la traza de la Hoja guarda la descripción del APU tal
    # cual, así que se recorta igual (árbitro del 2026-11-13, M3).
    return (
        texto_de_celda(fila, "descripcion") == traza.descripcion.strip()
        and texto_de_celda(fila, "unidad") == traza.unidad.strip()
        and cantidad == traza.cantidad
    )


def _emparejar(
    filas: Sequence[Mapping[str, str]], trazas: Sequence[TrazaDesperdicio]
) -> list[TrazaDesperdicio | None]:
    """La traza de cada fila, o `None`: solo la fila cuya descripción, unidad y cantidad son las de
    la traza, y cada traza una vez (la primera fila que la cumple)."""
    libres = list(trazas)
    salida: list[TrazaDesperdicio | None] = []
    for fila in filas:
        traza = next((t for t in libres if _de_la_linea(fila, t)), None)
        if traza is not None:
            libres.remove(traza)
        salida.append(traza)
    return salida


def con_desperdicio(
    filas: Sequence[Mapping[str, str]], trazas: Sequence[TrazaDesperdicio]
) -> list[dict[str, str]]:
    """Las filas de materiales de una precarga con la neta y el porcentaje de su traza, solo en la
    fila cuya descripción, unidad y cantidad son las de la traza (cada traza, una vez)."""
    salida = []
    for fila, traza in zip(filas, _emparejar(filas, trazas), strict=True):
        propia = dict(fila)
        if traza is not None:
            propia["cantidad"] = texto_de_cifra(traza.cantidad_neta)
            propia[CLAVE] = texto_de_cifra(traza.desperdicio_pct)
        salida.append(propia)
    return salida


def neta_y_porcentaje(traza: TrazaDesperdicio) -> str:
    """«0,50 + 4 %»: la neta y el porcentaje tal como se escribieron, con coma decimal y punto de
    miles. Es lo que la Hoja pone junto a la cantidad, que ya está en su celda."""
    return f"{texto_de_cifra(traza.cantidad_neta)} + {texto_de_cifra(traza.desperdicio_pct)} %"


def trazas_de_las_filas(
    filas: Sequence[Mapping[str, str]], trazas: Sequence[TrazaDesperdicio]
) -> list[tuple[int, TrazaDesperdicio]]:
    """El número de fila (desde 1) y la traza de cada fila de materiales que la tiene, con la misma
    regla que `con_desperdicio`: descripción, unidad y cantidad iguales, cada traza una vez."""
    return [
        (indice, traza)
        for indice, traza in enumerate(_emparejar(filas, trazas), start=1)
        if traza is not None
    ]


def guardar_trazas(
    sesion: Session, partida: str, trazas: Sequence[TrazaDesperdicio], *, ahora: datetime
) -> None:
    """Registra el guardado de la composición de `partida` con sus `trazas` (puede no traer
    ninguna: así la anterior deja de valer). **No confirma**: el `commit` es de quien guarda la
    composición, en la misma transacción."""
    if not trazas and not hay_tablas_de_desperdicio(sesion):
        return  # nada que dejar ni que anular
    if not hay_tablas_de_desperdicio(sesion):
        crear_esquema_desperdicio(sesion.connection())
    guardado = GuardadoDeDesperdicio(partida_codigo=partida, fecha_hora=ahora)
    sesion.add(guardado)
    sesion.flush()
    for orden, traza in enumerate(trazas, start=1):
        sesion.add(
            LineaConDesperdicio(
                guardado_id=guardado.id,
                orden=orden,
                descripcion=traza.descripcion,
                unidad=traza.unidad,
                cantidad_neta=traza.cantidad_neta,
                desperdicio_pct=traza.desperdicio_pct,
                cantidad=traza.cantidad,
            )
        )
    sesion.flush()


def trazas_vigentes(sesion: Session, partida: str) -> list[TrazaDesperdicio]:
    """Las trazas del último guardado de la composición de `partida`, en orden; vacío si no hay."""
    if not hay_tablas_de_desperdicio(sesion):
        return []
    ultimo = sesion.scalars(
        select(GuardadoDeDesperdicio.id)
        .where(GuardadoDeDesperdicio.partida_codigo == partida)
        .order_by(GuardadoDeDesperdicio.id.desc())
    ).first()
    if ultimo is None:
        return []
    lineas = sesion.scalars(
        select(LineaConDesperdicio)
        .where(LineaConDesperdicio.guardado_id == ultimo)
        .order_by(LineaConDesperdicio.orden)
    )
    return [
        TrazaDesperdicio(x.descripcion, x.unidad, x.cantidad_neta, x.desperdicio_pct, x.cantidad)
        for x in lineas
    ]
