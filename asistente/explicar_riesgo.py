"""El asistente explica el riesgo de la obra, no lo calcula (plan vial, Tarea 16; objetivo 6).

`explicar_riesgo` es una herramienta de **solo lectura** y sin argumentos: devuelve las cifras que
ya calculó el sistema (la proyección y la comprobación hacia atrás de `aplicacion.riesgo`) tal como
las ve la persona, con coma decimal y punto de miles. Las recibe hechas, como texto: `asistente/`
no importa `aplicacion.riesgo` (guardia de arquitectura, `test_arquitectura_asistente.py`); quien
llama (la API, cuando se conecte) le pasa lo que ya tiene en la pantalla.

El asistente solo narra. La **validación de citas** de `asistente.validacion` (S4 §7.3: «todo
número trae una cita») se aplica a la narración: cada cifra del texto debe estar en lo que la
herramienta devolvió en esta conversación. Una cifra que no está es `NUMERO_AUSENTE_DE_LA_CITA`
(también un redondeo propio: 1.248,7 no es 1.248,72); una escrita fuera de la regla de las cifras
(«248.72», decimal anglosajón) es `NUMERO_INVALIDO`. Sin haber llamado a la herramienta, ninguna
cifra vale. La herramienta va aparte de `HERRAMIENTAS` (`asistente/herramientas.py`): esa tupla y
la validación de las propuestas son del experimento congelado (`protocolo.json`) y no se tocan.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from aplicacion.cifras import CifraInvalida, cifra_escrita
from asistente.herramientas import Herramienta, TipoHerramienta
from asistente.proveedores.base import (
    EsquemaHerramienta,
    FinTurno,
    Mensaje,
    ProveedorIA,
    ResultadoHerramienta,
)
from asistente.validacion import Causa, Rechazo

__all__ = [
    "HERRAMIENTA",
    "Explicacion",
    "ExplicarRiesgo",
    "explicar",
    "salida_de_la_herramienta",
    "validar_explicacion",
]

NOMBRE = "explicar_riesgo"
MAX_TURNOS = 4
SISTEMA = (
    "Eres el asistente de Sílice. Explica a la persona, en pocas frases y en español, qué riesgo "
    "de precios tiene su obra. Llama primero a la herramienta explicar_riesgo: trae las cifras ya "
    "calculadas por el sistema. No calcules, no redondees ni inventes ninguna cifra: copia cada "
    "una tal como la da la herramienta, con coma decimal y punto de miles."
)
PEDIDO = "Explícame el riesgo de precios de esta obra con las cifras del sistema."
SIN_CIFRAS = "la herramienta explicar_riesgo no recibe argumentos: llámela sin ninguno"


class ExplicarRiesgo(BaseModel):
    """Sin argumentos: la herramienta lee lo ya calculado (`extra="forbid"`, como las demás)."""

    model_config = ConfigDict(extra="forbid")


HERRAMIENTA = Herramienta(
    NOMBRE,
    TipoHerramienta.LECTURA,
    ExplicarRiesgo,
    "Cifras del riesgo de la obra ya calculadas por el sistema (P50, P80, reserva, insumos que "
    "empujan, cobertura). Solo para narrarlas, sin calcular.",
)

#: Una cifra del texto: dígitos con puntos o comas entre ellos (la regla decide si es válida).
_CIFRA = re.compile(r"[0-9](?:[0-9.,]*[0-9])?")


def salida_de_la_herramienta(cifras: Mapping[str, str]) -> str:
    """Lo que la herramienta devuelve al modelo: las cifras tal cual, como JSON."""
    return json.dumps(dict(cifras), ensure_ascii=False, sort_keys=True)


def _cifras(texto: str) -> list[tuple[str, Decimal | None]]:
    """Cada cifra del texto con su valor por la regla de las cifras (`None` si no la cumple)."""
    leidas = []
    for crudo in _CIFRA.findall(texto):
        try:
            leidas.append((crudo, cifra_escrita(crudo)))
        except CifraInvalida:
            leidas.append((crudo, None))
    return leidas


def validar_explicacion(texto: str, salidas: Sequence[str]) -> Rechazo | None:
    """`None` si toda cifra de `texto` está en alguna de las `salidas` de la herramienta."""
    citables = {v for salida in salidas for _, v in _cifras(salida) if v is not None}
    for crudo, valor in _cifras(texto):
        if valor is None:
            return Rechazo(
                Causa.NUMERO_INVALIDO,
                f"la cifra {crudo} no sigue la regla de coma decimal y punto de miles",
            )
        if valor not in citables:
            return Rechazo(
                Causa.NUMERO_AUSENTE_DE_LA_CITA,
                f"la cifra {crudo} no está en lo que devolvió {NOMBRE}",
            )
    return None


@dataclass(frozen=True, slots=True)
class Explicacion:
    """La narración aceptada (`texto`) o por qué no (`rechazo`); `turnos` pedidos al proveedor."""

    texto: str | None
    rechazo: Rechazo | None
    turnos: int


def _responder(llamada, cifras: Mapping[str, str]) -> ResultadoHerramienta:
    if llamada.nombre != NOMBRE:
        return ResultadoHerramienta(llamada.id, f"herramienta desconocida: {llamada.nombre}", True)
    if llamada.argumentos:
        return ResultadoHerramienta(llamada.id, SIN_CIFRAS, True)
    return ResultadoHerramienta(llamada.id, salida_de_la_herramienta(cifras))


def explicar(
    proveedor: ProveedorIA, cifras: Mapping[str, str], *, max_turnos: int = MAX_TURNOS
) -> Explicacion:
    """Pide al proveedor la narración del riesgo con la única herramienta `explicar_riesgo` y la
    valida contra lo que la herramienta devolvió. Se corta a los `max_turnos` turnos."""
    esquema = EsquemaHerramienta(NOMBRE, HERRAMIENTA.descripcion, HERRAMIENTA.esquema())
    mensajes = [Mensaje("usuario", PEDIDO)]
    salidas: list[str] = []
    for n in range(1, max_turnos + 1):
        turno = proveedor.turno(SISTEMA, mensajes, (esquema,))
        if turno.fin is FinTurno.FIN or (turno.fin is FinTurno.HERRAMIENTAS and not turno.llamadas):
            rechazo = validar_explicacion(turno.texto, salidas)
            return Explicacion(turno.texto if rechazo is None else None, rechazo, n)
        if turno.fin is not FinTurno.HERRAMIENTAS:  # cortada por el límite o rechazada
            motivo = f"el proveedor no terminó la explicación ({turno.fin.value})"
            return Explicacion(None, Rechazo(Causa.FILA_NO_CONSTRUIBLE, motivo), n)
        resultados = tuple(_responder(llamada, cifras) for llamada in turno.llamadas)
        salidas += [r.contenido for r in resultados if not r.es_error]
        mensajes += [
            Mensaje("asistente", turno.texto, turno.llamadas, crudo=turno.crudo),
            Mensaje("usuario", resultados=resultados),
        ]
    motivo = f"el asistente no terminó la explicación en {max_turnos} turnos"
    return Explicacion(None, Rechazo(Causa.FILA_NO_CONSTRUIBLE, motivo), max_turnos)
