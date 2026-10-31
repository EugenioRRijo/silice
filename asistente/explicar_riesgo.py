"""El asistente explica el riesgo de la obra, no lo calcula (plan vial, Tarea 16; objetivo 6).

`explicar_riesgo` es una herramienta de **solo lectura** y sin argumentos: devuelve las cifras que
ya calculó el sistema (la proyección y la comprobación hacia atrás de `aplicacion.riesgo`) tal como
las ve la persona, con coma decimal y punto de miles. Las recibe hechas, como texto: `asistente/`
no importa `aplicacion.riesgo` (guardia de arquitectura, `test_arquitectura_asistente.py`); quien
llama (la API, cuando se conecte) le pasa lo que ya tiene en la pantalla.

El asistente solo narra. La **validación de citas** de `asistente.validacion` (S4 §7.3: «todo
número trae una cita») se aplica a la narración: cada cifra del texto debe estar en lo que la
herramienta devolvió en esta conversación, **en sus valores**: los rótulos («P80», «P50») no dan
cifras citables, así que «cubre el 80 por ciento» no se apoya en el rótulo «P80»; nombrar el rótulo
en la narración sí vale. Cada cifra de los valores se lee con `cifra_escrita`: una que no sigue la
regla es un error de quien llama (`ValueError`) y la herramienta no la entrega. Una cifra que no
está es `NUMERO_AUSENTE_DE_LA_CITA`
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
    """Lo que la herramienta devuelve al modelo: las cifras tal cual, como JSON. `ValueError` si
    una cifra de un valor no sigue la regla de las cifras (coma decimal y punto de miles)."""
    for rotulo, valor in cifras.items():
        malas = [crudo for crudo, leida in _cifras(valor) if leida is None]
        if malas:
            raise ValueError(
                f"el valor de «{rotulo}» trae {', '.join(malas)}, que no sigue la regla de coma "
                "decimal y punto de miles"
            )
    return json.dumps(dict(cifras), ensure_ascii=False, sort_keys=True)


def _devuelto(salida: str) -> dict[str, str]:
    """Lo que devolvió la herramienta, `{rótulo: valor}` (vacío si no es eso)."""
    try:
        datos = json.loads(salida)
    except ValueError:
        return {}
    if not isinstance(datos, dict):
        return {}
    return {str(k): v for k, v in datos.items() if isinstance(v, str)}


def _sin_rotulos(texto: str, rotulos: set[str]) -> str:
    """El texto sin los rótulos de la herramienta que llevan dígitos («P80»), como palabra entera:
    nombrarlos no es citar una cifra. Una cifra pegada a otra palabra («Bs250») sigue contando."""
    for rotulo in sorted(rotulos, key=len, reverse=True):
        if any(ch.isdigit() for ch in rotulo):
            texto = re.sub(rf"(?<!\w){re.escape(rotulo)}(?!\w)", " ", texto)
    return texto


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
    """`None` si toda cifra de `texto` está en los valores de alguna de las `salidas` de la
    herramienta (los rótulos no cuentan como cifras)."""
    devueltos = [_devuelto(salida) for salida in salidas]
    citables = {
        leida
        for devuelto in devueltos
        for valor in devuelto.values()
        for _, leida in _cifras(valor)
        if leida is not None
    }
    rotulos = {rotulo for devuelto in devueltos for rotulo in devuelto}
    for crudo, valor in _cifras(_sin_rotulos(texto, rotulos)):
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


def _responder(llamada, salida: str) -> ResultadoHerramienta:
    if llamada.nombre != NOMBRE:
        return ResultadoHerramienta(llamada.id, f"herramienta desconocida: {llamada.nombre}", True)
    if llamada.argumentos:
        return ResultadoHerramienta(llamada.id, SIN_CIFRAS, True)
    return ResultadoHerramienta(llamada.id, salida)


def explicar(
    proveedor: ProveedorIA, cifras: Mapping[str, str], *, max_turnos: int = MAX_TURNOS
) -> Explicacion:
    """Pide al proveedor la narración del riesgo con la única herramienta `explicar_riesgo` y la
    valida contra lo que la herramienta devolvió. Se corta a los `max_turnos` turnos. Las `cifras`
    se validan antes de pedir el primer turno (`salida_de_la_herramienta`)."""
    salida = salida_de_la_herramienta(cifras)
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
        resultados = tuple(_responder(llamada, salida) for llamada in turno.llamadas)
        salidas += [r.contenido for r in resultados if not r.es_error]
        mensajes += [
            Mensaje("asistente", turno.texto, turno.llamadas, crudo=turno.crudo),
            Mensaje("usuario", resultados=resultados),
        ]
    motivo = f"el asistente no terminó la explicación en {max_turnos} turnos"
    return Explicacion(None, Rechazo(Causa.FILA_NO_CONSTRUIBLE, motivo), max_turnos)
