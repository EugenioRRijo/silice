"""Los parámetros del precio unitario en «Componer una partida» (RF-200, ola 2 del 2026-11-13).

Componer calculaba siempre con los `ParametrosCosto()` de omisión (NORMAS.md §4) y su precio
unitario no era el de la obra, que usa los de «Ajustes de costo» (prueba de punta a punta del
2026-11-13). Ahora la pantalla manda los cuatro factores como texto (coma decimal y punto de
miles) y el servidor calcula con ellos el desglose que se ve y el precio del mensaje de guardado.
No se guardan con la partida: la composición es del catálogo y sirve a todas las obras; los
parámetros son de cada obra (bitácora `docs/bitacora/2026-11-13-ola2-front.md` §6, opción C).

`aplicacion/composicion.py` (congelado por el experimento) no cambia: `evaluar_composicion` sigue
calculando con los de omisión, también el contraste con las reglas (Ayuda 4, AACE), que así
compara el precio anterior y el construido sobre la misma base de indirectos. Aquí solo se
recalcula el desglose que se muestra.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from aplicacion import hoja
from aplicacion.cifras import CifraInvalida, cifra_escrita, texto_de_cifra
from aplicacion.composicion import composicion_desde_tablas
from aplicacion.hoja_vista import ROTULOS_PARAMETROS
from core.contracts import ParametrosCosto, ResultadoAPU
from core.costing.motor import calcular_apu

__all__ = [
    "CAMPOS",
    "ParametrosInvalidos",
    "desglose_con_parametros",
    "mensaje_con_precio",
    "parametros_de_omision",
    "parametros_desde_textos",
]

#: Los cuatro campos, en el orden de la pestaña «Ajustes de costo» de la Hoja.
CAMPOS = hoja.CAMPOS_PARAMETROS

#: El nombre corto de cada campo en los mensajes.
NOMBRES = {
    "fcas": "FCAS",
    "bono_alimentacion": "Bono de alimentación",
    "administracion": "Administración",
    "utilidad": "Utilidad",
}

#: Lo que antecede a todo mensaje de un parámetro mal escrito (la pantalla lo ubica por él).
PREFIJO = "Parámetros del precio unitario."


class ParametrosInvalidos(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """Un parámetro no sigue la regla de las cifras o es negativo; `campo` es su clave y el
    mensaje, el que ve la persona («Parámetros del precio unitario. FCAS: …»)."""

    def __init__(self, campo: str, motivo: str) -> None:
        super().__init__(f"{PREFIJO} {NOMBRES[campo]}: {motivo}")
        self.campo = campo


def parametros_de_omision() -> list[tuple[str, str, str]]:
    """Clave, rótulo y valor escrito (coma decimal) de cada parámetro de omisión: lo que
    Componer propone cuando no hay una obra abierta."""
    omision = ParametrosCosto()
    return [(c, ROTULOS_PARAMETROS[c], texto_de_cifra(getattr(omision, c))) for c in CAMPOS]


def parametros_desde_textos(textos: Mapping[str, str]) -> ParametrosCosto:
    """Los `ParametrosCosto` de los cuatro textos, o `ParametrosInvalidos` con el primero que
    falla (en el orden de `CAMPOS`)."""
    valores: dict[str, Decimal] = {}
    for campo in CAMPOS:
        try:
            valor = cifra_escrita(textos.get(campo, ""))
        except CifraInvalida as error:
            raise ParametrosInvalidos(campo, str(error)) from None
        if valor < 0:
            raise ParametrosInvalidos(campo, "no puede ser negativo.")
        valores[campo] = valor
    return ParametrosCosto(**valores)


def desglose_con_parametros(
    codigo: str,
    descripcion: str,
    unidad: str,
    rendimiento: str,
    filas_materiales: Sequence[Mapping[str, str]],
    filas_equipos: Sequence[Mapping[str, str]],
    filas_mano_obra: Sequence[Mapping[str, str]],
    parametros: ParametrosCosto,
) -> ResultadoAPU:
    """El desglose de la composición de las tablas con `parametros` (`calcular_apu`, el mismo
    motor que la Hoja). Quien llama ya comprobó que las tablas forman una composición válida
    (`evaluar_composicion` dio `valido` o `guardar_desde_tablas` guardó)."""
    composicion = composicion_desde_tablas(
        codigo,
        descripcion,
        unidad,
        rendimiento,
        filas_materiales,
        filas_equipos,
        filas_mano_obra,
    )
    return calcular_apu(composicion, parametros)


def mensaje_con_precio(mensaje: str, anterior: str, nuevo: str) -> str:
    """El mensaje de guardado de `guardar_desde_tablas` con el precio `nuevo` en lugar del
    `anterior` (los dos con punto, como el campo `precio_unitario`). El mensaje dice «precio
    unitario 10,19.»; si no lo dice así, `ValueError` (un cambio del texto no debe pasar
    callado)."""
    viejo = f"precio unitario {texto_de_cifra(Decimal(anterior))}."
    if viejo not in mensaje:
        raise ValueError(f"el mensaje de guardado no dice {viejo!r}")
    return mensaje.replace(viejo, f"precio unitario {texto_de_cifra(Decimal(nuevo))}.", 1)
