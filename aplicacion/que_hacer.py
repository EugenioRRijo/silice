"""El «Qué hacer» de cada hallazgo y de cada alerta de precio de un libro (B2, ficha-b2 §3.3).

Es una capa de **presentación**: dice, en palabras llanas y en trato de usted, qué quiere decir cada
regla y qué conviene revisar. No decide nada de la auditoría ni cambia lo que las reglas informan
(las reglas, sus umbrales y `aplicacion/causas_raiz.py` están sellados por la etiqueta
`reglas-congeladas-2026-11-24`). Cada entrada lleva un **código estable**: el de la regla («L4») o
`alerta:<tipo>` para las alertas de precio, que el PDF, el historial y la pantalla pueden citar sin
depender del texto.

Los textos dicen qué revisar y no qué decidir: el auditor no decide la intención de quien hizo el
libro (F-D7). Un código que el catálogo no conoce recibe `GENERICO`, marcado como tal, para que la
pantalla no lo presente como una guía propia.

`aplicacion/` no importa `fusion/`, así que los tipos de alerta se repiten aquí con su texto
literal; una prueba (`tests/unit/test_que_hacer.py`) los compara con `fusion/alertas.py` y
comprueba las frases de `sin_aviso_si` contra una alerta real.
"""

from __future__ import annotations

from dataclasses import dataclass

from aplicacion.nombres_reglas import nombre_de_regla

__all__ = [
    "CODIGOS_DE_REGLA",
    "GENERICO",
    "TIPOS_DE_ALERTA",
    "QueHacer",
    "catalogo",
    "que_hacer_de_alerta",
    "que_hacer_de_regla",
]


@dataclass(frozen=True, slots=True)
class QueHacer:
    """La guía de un código. `generico`: no es una guía propia de ese código. `sin_aviso_si`:
    frases con que el servidor declara que una alerta de ese tipo no avisa de nada (solo USD-Bs
    «dentro del umbral»)."""

    codigo: str
    titulo: str
    significa: str
    que_hacer: str
    generico: bool = False
    sin_aviso_si: tuple[str, ...] = ()

    def como_dict(self) -> dict[str, object]:
        return {
            "codigo": self.codigo,
            "titulo": self.titulo,
            "significa": self.significa,
            "que_hacer": self.que_hacer,
            "generico": self.generico,
            "sin_aviso_si": list(self.sin_aviso_si),
        }


# --- Reglas ---------------------------------------------------------------------------------------

# (significa, qué hacer) por código de regla. El título sale de `aplicacion/nombres_reglas.py`.
_REGLAS: dict[str, tuple[str, str]] = {
    "L1": (
        "Una fórmula del libro lee una celda distinta de la que le corresponde, por ejemplo el "
        "rendimiento de otro "
        "renglón del análisis.",
        "Abra la celda indicada en su Excel y compare lo que lee con lo que la descripción dice "
        "que debería leer; "
        "corríjala. Si la misma fórmula se copió en varias partidas, corrija la primera y cópiela "
        "de nuevo: se "
        "arreglan todos los casos de la causa.",
    ),
    "L2": (
        "El precio de una partida no viene de su análisis de precio unitario, o el enlace apunta "
        "al análisis de otra.",
        "Enlace de nuevo el precio unitario de la partida con el total de su análisis y confirme "
        "que el número de la "
        "partida es el mismo en el presupuesto y en la hoja del análisis.",
    ),
    "L3": (
        "El número que muestra una celda no es el que daría su fórmula: alguien lo escribió "
        "encima o el libro no se "
        "recalculó antes de guardarlo.",
        "Recalcule el libro (F9). Si el valor sigue distinto, restituya la fórmula de la celda, o "
        "deje anotado por qué "
        "el valor se escribió a mano.",
    ),
    "L4": (
        "El costo directo de un análisis no suma todos sus componentes (materiales, mano de obra, "
        "equipos y "
        "transporte), o un componente vale cero.",
        "Revise la fórmula del total del análisis: debe sumar todos los componentes. Corrija el "
        "rango de la suma y "
        "compare el resultado con el efecto en el total que dice la descripción. Si un componente "
        "vale cero a "
        "propósito, déjelo anotado.",
    ),
    "L5": (
        "Una fórmula apunta a una celda u hoja que ya no existe o a otro archivo, o una celda da "
        "error al calcular.",
        "Busque las celdas con #REF! o con un vínculo a otro archivo y escriba de nuevo la "
        "fórmula con la celda "
        "correcta. Si el vínculo externo es a propósito, copie su valor dentro del libro. Si la "
        "celda da error al calcular (#¡DIV/0!, #¡VALOR!), revise la celda que la fórmula lee o "
        "divide: suele estar vacía o tener texto en lugar de un número.",
    ),
    "L6": (
        "Un porcentaje o un rendimiento que debería venir de los parámetros del libro está "
        "escrito a mano en un "
        "análisis.",
        "Confirme con quien hizo el libro si el valor propio es intencional. Si no lo es, "
        "enlácelo de nuevo con el "
        "parámetro del libro; si lo es, "
        "déjelo y anote la razón junto a la celda.",
    ),
    "L7": (
        "Una fórmula lleva un número escrito dentro: si el dato cambia, hay que acordarse de "
        "editar la fórmula.",
        "Lleve ese número a una celda propia, con su rótulo, y haga que la fórmula la lea.",
    ),
    "L8": (
        "Dos partidas del presupuesto llevan el mismo número.",
        "Renumere una de las dos. Si es la misma partida repetida, quite la repetida y compruebe "
        "que cada partida lee "
        "su propio análisis.",
    ),
    "L9": (
        "Una suma del libro no cuadra con sus partes, por ejemplo el costo directo contra sus "
        "componentes.",
        "Compare la suma con sus partes en la celda indicada y corrija la que esté mal; después "
        "suba el libro de "
        "nuevo para comprobar que cuadra.",
    ),
    "L10": (
        "Se revisó un PDF contra sí mismo porque no había un libro de Excel con qué compararlo.",
        "Cotéjelo con el presupuesto original. Si necesita una revisión completa, suba el libro "
        "de Excel del que "
        "salió el PDF.",
    ),
    "L11": (
        "Los totales del PDF entregado no coinciden con los del libro.",
        "Genere el PDF de nuevo desde el libro corregido. Si el que está bien es el PDF, corrija "
        "el libro hasta que "
        "sus totales coincidan.",
    ),
    "F1": (
        "El precio unitario que trae el libro difiere del que Sílice recalcula con los "
        "componentes del análisis.",
        "Compare los dos precios que dice la descripción y corrija el componente, la cantidad o "
        "el redondeo que los "
        "separa.",
    ),
    "R1": (
        "Una cantidad del cómputo no se puede rastrear hasta su origen, o no coincide con la "
        "regla de la que sale.",
        "Anote de dónde sale la cantidad (plano, cómputo o medición), o corrija la regla con que "
        "se calcula.",
    ),
    "R2": (
        "El acumulado de la curva de inversión no es el total del presupuesto.",
        "Si el libro trae curva de inversión, ajústela hasta que su último acumulado sea el total "
        "del presupuesto. Si "
        "no la trae, la regla no aplica y no hay nada que corregir.",
    ),
    "R3": (
        "La unidad del cómputo no equivale a la unidad del análisis que lo costea.",
        "Compare la unidad de la partida con la de su análisis y corrija la que no corresponda.",
    ),
    "R4": (
        "Una especificación del cómputo no se reconoce en el texto del análisis, o lo contradice.",
        "Lea la especificación junto a la descripción del análisis y corrija la que esté mal. Si "
        "el análisis calla "
        "un dato sin contradecirlo, basta con confirmarlo con quien lo hizo.",
    ),
    "R5": (
        "La cantidad de una partida no cuadra con el balance que ella misma declara.",
        "Revise las cantidades que entran en el balance de la partida, que la descripción lista, "
        "y corrija la que no "
        "cuadre.",
    ),
    "R6": (
        "Un mismo insumo lleva factores de depreciación distintos en distintos análisis.",
        "Confirme con quien hizo el libro si los factores distintos son intencionales; si no lo "
        "son, use el mismo factor en todos los análisis del insumo. Las primeras partidas de la "
        "lista son las que menos se repiten y las más probables de corregir.",
    ),
    "R7": (
        "Un monto del plan de trabajo no coincide con el monto de las partidas que ejecuta.",
        "Si el libro trae plan de trabajo, concilie cada período con sus partidas. Si no lo trae, "
        "la regla no aplica "
        "y no hay nada que corregir.",
    ),
}

#: Los códigos de regla con guía propia, en orden.
CODIGOS_DE_REGLA: tuple[str, ...] = tuple(_REGLAS)

#: Lo que se dice de un código que el catálogo no conoce: qué hacer sin inventar una causa.
GENERICO = QueHacer(
    codigo="",
    titulo="Hallazgo",
    significa="Sílice encontró algo que no cuadra en esta celda.",
    que_hacer=(
        "Abra la celda indicada en su Excel, lea la descripción del hallazgo y corríjalo. Si no "
        "está seguro de la "
        "causa, consúltelo con quien hizo el libro."
    ),
    generico=True,
)


def que_hacer_de_regla(codigo: str) -> QueHacer:
    """La guía de la regla `codigo`, o `GENERICO` con ese código si el catálogo no la conoce."""
    propia = _REGLAS.get(codigo)
    if propia is None:
        return QueHacer(
            codigo=codigo,
            titulo=nombre_de_regla(codigo) or GENERICO.titulo,
            significa=GENERICO.significa,
            que_hacer=GENERICO.que_hacer,
            generico=True,
        )
    significa, que_hacer = propia
    return QueHacer(
        codigo=codigo, titulo=nombre_de_regla(codigo), significa=significa, que_hacer=que_hacer
    )


# --- Alertas de precio ----------------------------------------------------------------------------

# Por tipo de alerta de `fusion/alertas.py`:
# (código estable, título, significa, qué hacer, frases de «sin aviso»).
_ALERTAS: dict[str, tuple[str, str, str, str, tuple[str, ...]]] = {
    "sin fuente": (
        "alerta:sin-fuente",
        "Sin fuente",
        "El precio de un insumo no dice de dónde sale: su fuente está vacía o dice «por cotizar» "
        "o «referencial», y "
        "nadie puede comprobarlo.",
        "Pida a quien hizo el libro la cotización o la lista de la que sale el precio y anótela "
        "en la columna de "
        "fuente. Mientras tanto, el precio queda sin respaldo.",
        (),
    ),
    "base de la empresa": (
        "alerta:base-de-la-empresa",
        "Base de la empresa",
        "El precio del libro se aparta del precio propio que la empresa tiene para ese insumo, "
        "más allá del umbral.",
        "Compárelo con la base de la empresa. Si el libro debe seguirla, use el precio de la "
        "base; si el precio del "
        "libro tiene una razón, como una cotización más reciente, anótela como su fuente.",
        (),
    ),
    "otra versión": (
        "alerta:otra-version",
        "Otra versión",
        "El precio cambió frente a la otra versión del mismo libro, o el insumo no estaba en ella.",
        "Confirme con quien hizo el libro que el cambio es intencional y que su fuente quedó "
        "anotada.",
        (),
    ),
    "USD-Bs": (
        "alerta:usd-bs",
        "USD-Bs",
        "El mismo precio vale distinto en bolívares entre la fecha del libro y la de la revisión, "
        "por el cambio de la "
        "tasa del BCV.",
        "Si el presupuesto se entrega en bolívares, actualice los precios con la tasa vigente. Si "
        "la instalación no "
        "tiene la tasa de una fecha, cárguela en Índices del BCV y vuelva a auditar.",
        ("dentro del umbral",),
    ),
}

#: Los tipos de alerta de precio que `fusion/alertas.py` produce.
TIPOS_DE_ALERTA: tuple[str, ...] = tuple(_ALERTAS)


def que_hacer_de_alerta(tipo: str) -> QueHacer:
    """La guía del tipo de alerta `tipo` (`fusion.alertas.TIPO_*`), o `GENERICO` si no se conoce."""
    propia = _ALERTAS.get(tipo)
    if propia is None:
        return QueHacer(
            codigo=f"alerta:{tipo}",
            titulo=GENERICO.titulo,
            significa=GENERICO.significa,
            que_hacer=GENERICO.que_hacer,
            generico=True,
        )
    codigo, titulo, significa, que_hacer, sin_aviso = propia
    return QueHacer(
        codigo=codigo,
        titulo=titulo,
        significa=significa,
        que_hacer=que_hacer,
        sin_aviso_si=sin_aviso,
    )


def catalogo() -> dict[str, object]:
    """Todo lo que la pantalla necesita, de una vez: las guías por código de regla y por tipo de
    alerta, y la genérica. Es lo que responde `GET /v1/libros/que-hacer`."""
    return {
        "reglas": {c: que_hacer_de_regla(c).como_dict() for c in CODIGOS_DE_REGLA},
        "alertas": {t: que_hacer_de_alerta(t).como_dict() for t in TIPOS_DE_ALERTA},
        "generico": GENERICO.como_dict(),
    }
