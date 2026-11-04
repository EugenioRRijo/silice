"""Costo por tonelada del periodo: la aritmetica pura (Tarea 4 del plan vial).

Sin sesion ni reloj: recibe montos ya convertidos a una sola moneda y toneladas, y devuelve costos
por tonelada. Quien lee la base, convierte la moneda y guarda la instantanea es
`aplicacion.costo_propio`.

- **Reparto de la cantera (D-V-1)**: sin pesos, el mismo costo por tonelada para todos los
  agregados (total / toneladas de todos); con pesos (suman 1, uno por agregado, todos mayores que
  cero), `total x peso / toneladas` de cada uno.
- **Mezcla**: lo que lleva una tonelada segun su receta (componentes propios a su costo del periodo,
  comprados a su precio de lista) mas el costo de planta por tonelada. Si en el periodo se
  produjo con mas de una receta, cada receta pesa por las toneladas hechas con ella.
- **Exacto**: toda operacion con `CIFRAS_DEL_CALCULO` (28) cifras significativas y redondeo de mitad
  al par, fijados aqui (no dependen del contexto decimal del hilo); se redondea solo al presentar
  (`presentar`: `DECIMALES_AL_PRESENTAR`, mitad hacia arriba).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, localcontext

from produccion.costos import ErrorDeCosto
from produccion.fuentes import CIFRAS_DEL_CALCULO, DECIMALES_AL_PRESENTAR
from produccion.receta import Receta

__all__ = [
    "ErrorDeCalculo",
    "costo_de_mezcla",
    "costo_de_mezcla_del_periodo",
    "costo_por_tonelada",
    "exacto",
    "presentar",
]

CERO = Decimal(0)
UNO = Decimal(1)


class ErrorDeCalculo(ErrorDeCosto):
    """No se puede calcular el costo por tonelada; el mensaje esta escrito para el usuario."""


def exacto[T](operacion: Callable[[], T]) -> T:
    """`operacion()` con el contexto del calculo: 28 cifras y redondeo de mitad al par."""
    with localcontext(prec=CIFRAS_DEL_CALCULO, rounding=ROUND_HALF_EVEN):
        return operacion()


def _coma(valor: Decimal) -> str:
    return format(valor, "f").replace(".", ",")


def _validar_toneladas(toneladas: Mapping[str, Decimal]) -> None:
    if not toneladas:
        raise ErrorDeCalculo("No hay ningún producto entre el que repartir el costo.")
    sin_toneladas = sorted(c for c, t in toneladas.items() if not t > CERO)
    if sin_toneladas:
        raise ErrorDeCalculo(
            f"Sin toneladas producidas no hay costo por tonelada: {', '.join(sin_toneladas)}."
        )


def _validar_pesos(pesos: Mapping[str, Decimal], toneladas: Mapping[str, Decimal]) -> None:
    faltan = sorted(set(toneladas) - set(pesos))
    if faltan:
        raise ErrorDeCalculo(f"Falta el peso de {', '.join(faltan)} en el reparto por pesos.")
    sobran = sorted(set(pesos) - set(toneladas))
    if sobran:
        raise ErrorDeCalculo(
            f"El reparto por pesos solo admite los agregados producidos en el periodo; "
            f"sobra: {', '.join(sobran)}."
        )
    no_positivos = sorted(c for c, p in pesos.items() if not p > CERO)
    if no_positivos:
        raise ErrorDeCalculo(
            f"Cada peso debe ser mayor que cero (un peso cero daría un costo cero): "
            f"{', '.join(no_positivos)}."
        )
    suma = sum(pesos.values(), CERO)
    if suma != UNO:
        raise ErrorDeCalculo(f"Los pesos del reparto deben sumar 1; suman {_coma(suma)}.")


def costo_por_tonelada(
    total: Decimal,
    toneladas: Mapping[str, Decimal],
    *,
    pesos: Mapping[str, Decimal] | None = None,
) -> dict[str, Decimal]:
    """Reparte `total` entre los productos de `toneladas` y devuelve el costo por tonelada de
    cada uno, en el orden de `toneladas`. Sin `pesos`, el mismo para todos (D-V-1)."""
    if not total >= CERO:
        raise ErrorDeCalculo("El total a repartir no puede ser negativo.")
    _validar_toneladas(toneladas)
    if pesos is None:

        def por_tonelada() -> dict[str, Decimal]:
            unico = total / sum(toneladas.values(), CERO)
            return dict.fromkeys(toneladas, unico)

        return exacto(por_tonelada)
    _validar_pesos(pesos, toneladas)
    return exacto(lambda: {c: total * pesos[c] / t for c, t in toneladas.items()})


def costo_de_mezcla(
    receta: Receta,
    costo_propio: Mapping[str, Decimal],
    precio_comprado: Mapping[str, Decimal],
    costo_planta_por_t: Decimal,
) -> Decimal:
    """Costo de una tonelada de mezcla con `receta`: cada componente por su cantidad por tonelada
    (propios a `costo_propio`, comprados a `precio_comprado`, en su unidad) mas la planta."""
    terminos: list[tuple[Decimal, Decimal]] = []
    for c in receta.componentes:
        fuente = costo_propio if c.tipo == "propio" else precio_comprado
        if c.codigo not in fuente:
            que = "el costo propio del periodo" if c.tipo == "propio" else "el precio de lista"
            raise ErrorDeCalculo(
                f"Falta {que} de {c.codigo} (receta n.º {receta.id} de {receta.producto})."
            )
        terminos.append((c.cantidad_por_t, fuente[c.codigo]))
    return exacto(lambda: sum((q * p for q, p in terminos), CERO) + costo_planta_por_t)


def costo_de_mezcla_del_periodo(
    usos: Sequence[tuple[Receta, Decimal]],
    costo_propio: Mapping[str, Decimal],
    precio_comprado: Mapping[str, Decimal],
    costo_planta_por_t: Decimal,
) -> Decimal:
    """Costo por tonelada de una mezcla hecha en el periodo con una o mas recetas: `usos` son
    pares (receta, toneladas hechas con ella). Los componentes pesan por toneladas y la planta se
    suma una vez: `planta + suma(t_r x componentes_r) / suma(t_r)`; con una sola receta da los
    componentes de esa receta sin perder cifras."""
    if not usos:
        raise ErrorDeCalculo("La mezcla no tuvo producción en el periodo.")
    _validar_toneladas({f"receta n.º {r.id}": t for r, t in usos})
    componentes = [(costo_de_mezcla(r, costo_propio, precio_comprado, CERO), t) for r, t in usos]
    return exacto(
        lambda: (
            costo_planta_por_t
            + sum((t * c for c, t in componentes), CERO) / sum((t for _, t in componentes), CERO)
        )
    )


def presentar(valor: Decimal) -> Decimal:
    """El costo como se muestra: `DECIMALES_AL_PRESENTAR` decimales, mitad hacia arriba."""
    return valor.quantize(Decimal(1).scaleb(-DECIMALES_AL_PRESENTAR), rounding=ROUND_HALF_UP)
