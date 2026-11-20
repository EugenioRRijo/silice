"""Los hallazgos de las valuaciones (R13 y R14) como los lee la persona.

Prueba en vivo del 2026-11-18 (frente C, hallazgo 2): al registrar una valuación solo volvían los
conteos («4 hallazgo(s), 4 con severidad Error») y la tabla decía «ERROR: R14», sin decir qué estaba
mal. Las frases nacen en `core/verification/valuaciones.py` sin tildes, con fechas ISO y punto
decimal, y `core/` no se toca: aquí se reescriben sobre las FRASES FIJAS del núcleo con el mismo
catálogo de la casa que usan las alertas (`catalogo_de_frases`). Lo que escribió el usuario (el
número de una valuación, el código de una partida) entra en un hueco y sale tal cual; las fechas
salen en dd/mm/aaaa y las cantidades con coma decimal y punto de miles.

Límite conocido: el número de una valuación se acota a texto sin espacios (`\\S+`), porque varias
frases llevan dos números y el catálogo admite un solo hueco libre por frase. Un número con
espacios deja la frase sin reescribir: se lee igual, sin tildes.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from aplicacion.cifras import texto_de_cifra
from aplicacion.control_comun import _valuacion_del_hallazgo
from aplicacion.control_tablas import Hueco, catalogo_de_frases
from core.budget.control import ResultadoControl

__all__ = ["PLANTILLAS_DE_HALLAZGOS", "hallazgos_de_valuaciones", "mensaje_de_hallazgo"]


def _fecha(iso: str) -> str:
    try:
        return f"{date.fromisoformat(iso):%d/%m/%Y}"
    except ValueError:
        return iso


def _cantidad(texto: str) -> str:
    try:
        return texto_de_cifra(Decimal(texto))
    except (InvalidOperation, ValueError):
        return texto


_FECHA: Hueco = (r"\d{4}-\d{2}-\d{2}", _fecha)
_CANTIDAD: Hueco = (r"-?\d+(?:\.\d+)?", _cantidad)
_CLAVE: Hueco = r"\S+"

#: Los huecos de las frases de R13 y R14: fechas, cantidades, días y los números de valuación.
#: El código de una partida (`codigo`) es el único hueco libre de cada frase.
HUECOS_DE_HALLAZGOS: dict[str, Hueco] = {
    "clave": _CLAVE,
    "otra": _CLAVE,
    "desde": _FECHA,
    "hasta": _FECHA,
    "desde2": _FECHA,
    "hasta2": _FECHA,
    "fecha": _FECHA,
    "corte": _FECHA,
    "inicio": _FECHA,
    "medida": _FECHA,
    "total": _CANTIDAD,
    "cantidad": _CANTIDAD,
    "exceso": _CANTIDAD,
    "dias": r"\d+",
}

#: (frase tal como la emite `core/verification/valuaciones.py`, la misma para la pantalla).
PLANTILLAS_DE_HALLAZGOS: tuple[tuple[str, str], ...] = (
    # R13
    (
        "la valuacion {clave} valua la partida {codigo}, que la linea base no tiene: sin "
        "unitario, no se cuantifica",
        "La valuación {clave} valúa la partida {codigo}, que la línea base no tiene: sin "
        "unitario, no se cuantifica.",
    ),
    (
        "la partida {codigo} lleva {total} valuados y la linea base presupuesta {cantidad}: "
        "exceso de {exceso} desde la valuacion {clave}",
        "La partida {codigo} lleva {total} valuados y la línea base presupuesta {cantidad}: "
        "exceso de {exceso} desde la valuación {clave}.",
    ),
    (
        "la partida {codigo} esta presupuestada y el plan de la linea base no la programa en "
        "ningun periodo",
        "La partida {codigo} está presupuestada y el plan de la línea base no la programa en "
        "ningún período.",
    ),
    # R14
    ("la valuacion {clave} no tiene numero", "La valuación {clave} no tiene número."),
    ("la valuacion {clave} no tiene inspector", "La valuación {clave} no tiene inspector."),
    ("la valuacion {clave} no tiene fecha", "La valuación {clave} no tiene fecha."),
    (
        "la valuacion {clave} empieza el {desde}, despues de su fin ({hasta})",
        "La valuación {clave} empieza el {desde}, después de su fin ({hasta}).",
    ),
    (
        "la valuacion {clave} tiene fecha {fecha}, anterior a su fin ({hasta})",
        "La valuación {clave} tiene fecha {fecha}, anterior a su fin ({hasta}).",
    ),
    (
        "la valuacion {clave} termina el {hasta}, despues del corte ({corte})",
        "La valuación {clave} termina el {hasta}, después del corte ({corte}).",
    ),
    (
        "la valuacion {clave} empieza el {desde}, antes del inicio del calendario ({inicio})",
        "La valuación {clave} empieza el {desde}, antes del inicio del calendario ({inicio}).",
    ),
    (
        "la medicion de {codigo} en la valuacion {clave} es del {medida}, fuera de su periodo "
        "{desde} a {hasta}",
        "La medición de {codigo} en la valuación {clave} es del {medida}, fuera de su período "
        "{desde} a {hasta}.",
    ),
    ("el numero {clave} esta repetido", "El número {clave} está repetido."),
    (
        "el periodo de la valuacion {clave} ({desde} a {hasta}) se solapa con el de la {otra} "
        "({desde2} a {hasta2})",
        "El período de la valuación {clave} ({desde} a {hasta}) se solapa con el de la {otra} "
        "({desde2} a {hasta2}).",
    ),
    (
        "las valuaciones {otra} y {clave} no son consecutivas: falta al menos un numero",
        "Las valuaciones {otra} y {clave} no son consecutivas: falta al menos un número.",
    ),
    (
        "entre las valuaciones {otra} y {clave} hay {dias} dia(s) habil(es) sin cubrir "
        "({desde} a {hasta})",
        "Entre las valuaciones {otra} y {clave} hay {dias} día(s) hábil(es) sin cubrir "
        "({desde} a {hasta}).",
    ),
)

_REESCRIBIR = catalogo_de_frases(PLANTILLAS_DE_HALLAZGOS, HUECOS_DE_HALLAZGOS)

#: Cómo se nombra cada severidad en la pantalla (el nombre del núcleo es interno).
SEVERIDADES = {
    "CRITICO": "Crítico",
    "ERROR": "Error",
    "ADVERTENCIA": "Advertencia",
    "INFO": "Información",
}
_ORDEN = ("CRITICO", "ERROR", "ADVERTENCIA", "INFO")


def mensaje_de_hallazgo(descripcion: str) -> str:
    """La frase del núcleo con tildes, fechas en dd/mm/aaaa y cantidades con coma decimal. Una
    frase que el catálogo no conoce solo empieza con mayúscula y termina en punto."""
    texto = _REESCRIBIR(descripcion)
    if texto != descripcion:
        return texto
    texto = descripcion.strip()
    if not texto:
        return texto
    texto = texto[0].upper() + texto[1:]
    return texto if texto.endswith(".") else texto + "."


def hallazgos_de_valuaciones(resultado: ResultadoControl) -> list[dict[str, str]]:
    """Cada hallazgo de R13 y R14 al corte: la valuación que lo trae (o vacía si es de una
    partida), la regla, la severidad y el mensaje legible; los más graves primero y, dentro de
    cada severidad, en el orden del núcleo."""
    hallazgos = sorted(
        resultado.informe.hallazgos,
        key=lambda h: _ORDEN.index(h.severidad.name) if h.severidad.name in _ORDEN else 99,
    )
    claves = [v.clave for v in resultado.instantanea.valuaciones]
    filas = []
    for h in hallazgos:
        filas.append(
            {
                "Valuacion": _valuacion_del_hallazgo(h.origen_ids, claves) or "",
                "Regla": h.regla,
                "Severidad": SEVERIDADES.get(h.severidad.name, h.severidad.name),
                "Mensaje": mensaje_de_hallazgo(h.descripcion),
            }
        )
    return filas
