"""R17, conexion de cada punto: todo punto que su especialidad mide desde una fuente o por un
circuito lo tiene (tarea 1.7, pedido de Eugenio del 2026-10-18).

Un punto sin fuente no tiene recorrido propuesto (`geometria.recorrido_propuesto` devuelve `()`) y
un punto electrico sin circuito no esta en ninguna cadena (`geometria.orden_de_cadena`): la hoja
cuenta la salida pero el presupuesto no trae la tuberia ni el cable que llega a ella. Ninguna de
R8 a R10 lo ve (R10 no mira `fuente_id`), asi que la medicion controlada daba E5 0/24.

**Que exige cada punto (ruling 1.7-a).** Lo decide el par especialidad-tipo que consume una
derivacion de `adapters/espacio/especialidades`:

* agua fria y drenaje (especialidad agua) y datos (especialidad datos): **fuente**;
* tomacorriente e iluminacion (especialidad electricidad): **circuito**, sea por su `circuito_id`
  o por estar en el `orden` de un circuito (asi lo cuentan R10 y la cadena); su `fuente_id` no se
  exige, porque el conductor va por la cadena del circuito desde su tablero;
* cualquier otro par (un punto de electricidad con tipo de agua, por ejemplo) no lo deriva ninguna
  especialidad: R17 no le exige nada.

**Severidad (ruling 1.7-b).** Siempre ADVERTENCIA, nunca ERROR: un punto puede quedar sin conexion
a proposito (la fuente o el tablero estan fuera del alcance del presupuesto) y es el usuario quien
decide si lo corrige; la descripcion lo dice en lenguaje llano y nombra el punto y lo que le falta.
Un hallazgo por punto, en orden de id; `origen_ids = ("esp_puntos:<id>",)`, que la columna Estado
pinta en la fila del punto.

Como R8 a R10, la regla guarda la instantanea del espacio que recibe: quien la agrega tiene que
ligarla al espacio que se elabora (la pagina de la hoja lo hace en cada elaboracion). No vive en
`adapters/espacio/reglas.py` porque ese archivo es del auditor congelado del experimento.
"""

from __future__ import annotations

from adapters.espacio.modelo import Espacio, Especialidad, Punto, TipoPunto
from adapters.espacio.origen import clave_esp
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad

__all__ = ["CODIGO_R17", "ConexionDeCadaPunto", "reglas_conexion"]

CODIGO_R17 = "R17"

_FUENTE = "fuente"
_CIRCUITO = "circuito"

#: Lo que exige cada par (especialidad, tipo) y lo que le falta al presupuesto sin ello.
_EXIGE: dict[tuple[Especialidad, TipoPunto], tuple[str, str]] = {
    (Especialidad.AGUA, TipoPunto.AGUA_FRIA): (
        _FUENTE,
        "el presupuesto no incluye cómo le llega el agua. Asígnele su acometida o montante",
    ),
    (Especialidad.AGUA, TipoPunto.DRENAJE): (
        _FUENTE,
        "el presupuesto no incluye la tubería que lo lleva al colector de drenaje. Asígnele su "
        "colector",
    ),
    (Especialidad.DATOS, TipoPunto.DATOS): (
        _FUENTE,
        "el presupuesto no incluye el cable que lo une al rack. Asígnele su rack",
    ),
    (Especialidad.ELECTRICIDAD, TipoPunto.TOMACORRIENTE): (
        _CIRCUITO,
        "el presupuesto no incluye el cable que lo alimenta desde el tablero. Asígnele su circuito",
    ),
    (Especialidad.ELECTRICIDAD, TipoPunto.ILUMINACION): (
        _CIRCUITO,
        "el presupuesto no incluye el cable que lo alimenta desde el tablero. Asígnele su circuito",
    ),
}


def _nombre(p: Punto) -> str:
    """`P2 (lavamanos)`; solo el id si el punto no tiene un nombre propio."""
    nombre = (p.nombre or "").strip()
    return p.id if not nombre or nombre == p.id else f"{p.id} ({nombre})"


def _hallazgos_r17(espacio: Espacio) -> list[Hallazgo]:
    en_cadena = {i for c in espacio.circuitos for i in c.orden}
    hallazgos: list[Hallazgo] = []
    for p in espacio.puntos:  # el modelo ya los ordena por id
        exigencia = _EXIGE.get((p.especialidad, p.tipo))
        if exigencia is None:
            continue
        falta, consecuencia = exigencia
        if falta == _FUENTE:
            conectado = p.fuente_id is not None
        else:
            conectado = p.circuito_id is not None or p.id in en_cadena
        if conectado:
            continue
        hallazgos.append(
            Hallazgo(
                regla=CODIGO_R17,
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"El punto {_nombre(p)} no tiene {falta}: {consecuencia}, o déjelo así si es "
                    "a propósito."
                ),
                origen_ids=(clave_esp("esp_puntos", p.id),),
            )
        )
    return hallazgos


class ConexionDeCadaPunto(ReglaVerificacion):
    """R17: cada punto tiene la fuente o el circuito que su especialidad exige; si no, ADVERTENCIA
    con el punto y lo que le falta (ruling 1.7-a y 1.7-b)."""

    codigo = CODIGO_R17
    nombre = "Conexión de cada punto"

    def __init__(self, espacio: Espacio) -> None:
        self.espacio = espacio

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return _hallazgos_r17(self.espacio)


def reglas_conexion(espacio: Espacio) -> tuple[ReglaVerificacion, ...]:
    """R17 sobre la instantanea `espacio`, para `reglas_extra` de la hoja."""
    return (ConexionDeCadaPunto(espacio),)
