"""Adaptador de Claude con el SDK oficial `anthropic` (S4 §8.5). Importacion diferida (extra `ia`).

Modelo `claude-opus-5-5`: razonamiento adaptativo (no se puede desactivar) con esfuerzo FIJADO
explicitamente; `tool_choice` automatico (el forzado devuelve 400 en este modelo); sin parametros de
muestreo; `strict: true` en cada herramienta; el contenido completo del turno se agrega al
historial sin editarlo; las llamadas de un turno se responden en un solo mensaje, con `is_error`
para las rechazadas. Cache de prompt por `cache_control` de nivel superior. El respaldo del lado del
servidor ante un rechazo (`fallbacks`) se activa en el producto y se DESACTIVA en el experimento
(RS4-7): `con_respaldo`. La clave va en el cliente, nunca en el contenido ni en un registro.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from importlib.util import find_spec
from typing import Any

from asistente.proveedores.base import (
    FALTA_EL_COMPONENTE,
    Disponibilidad,
    ErrorDeProveedor,
    EsquemaHerramienta,
    FinTurno,
    LlamadaHerramienta,
    Mensaje,
    Turno,
    Uso,
)

MODELO_POR_DEFECTO = "claude-opus-5-5"
ESFUERZO_POR_DEFECTO = "high"  # RS4-11: se confirma con el piloto antes de congelar el protocolo
MAX_TOKENS = 16000  # sin streaming: por debajo del limite de tiempo del SDK
BETA_RESPALDO = "server-side-fallback-2026-07-01"
#: Palabras clave de JSON Schema que el modo estricto no admite: se quitan del esquema que viaja
#: (el sistema valida igual, §7.1). `pattern` se conserva; S4.0 confirma si el modo estricto lo
#: acepta y, si no, se agrega aqui.
NO_ADMITIDAS_EN_ESTRICTO = frozenset(
    {"minLength", "maxLength", "minimum", "maximum", "minItems", "maxItems", "title", "default"}
)
_FIN = {
    "end_turn": FinTurno.FIN,
    "tool_use": FinTurno.HERRAMIENTAS,
    "max_tokens": FinTurno.LIMITE,
    "pause_turn": FinTurno.LIMITE,
    "refusal": FinTurno.RECHAZO,
}


def esquema_estricto(esquema: Mapping[str, Any]) -> dict[str, Any]:
    """El esquema sin las palabras clave que el modo estricto no admite (copia profunda)."""

    def limpiar(nodo: Any) -> Any:
        if isinstance(nodo, dict):
            return {k: limpiar(v) for k, v in nodo.items() if k not in NO_ADMITIDAS_EN_ESTRICTO}
        if isinstance(nodo, list):
            return [limpiar(v) for v in nodo]
        return nodo

    return limpiar(deepcopy(dict(esquema)))


def construir_solicitud(
    *,
    modelo: str,
    esfuerzo: str,
    sistema: str,
    mensajes: Sequence[Mensaje],
    herramientas: Sequence[EsquemaHerramienta],
    max_tokens: int = MAX_TOKENS,
) -> dict[str, Any]:
    """Los argumentos de `messages.create`, en un orden y con un JSON estables (cache)."""
    return {
        "model": modelo,
        "max_tokens": max_tokens,
        "system": sistema,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": esfuerzo},
        "tool_choice": {"type": "auto"},
        "cache_control": {"type": "ephemeral"},
        "tools": [
            {
                "name": h.nombre,
                "description": h.descripcion,
                "input_schema": esquema_estricto(h.esquema),
                "strict": True,
            }
            for h in herramientas
        ],
        "messages": [_mensaje(m) for m in mensajes],
    }


def _mensaje(m: Mensaje) -> dict[str, Any]:
    if m.rol == "asistente":
        return {"role": "assistant", "content": m.crudo}  # tal como llego, sin editarlo
    if m.resultados:
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": r.llamada_id,
                    "content": r.contenido,
                    "is_error": r.es_error,
                }
                for r in m.resultados
            ],
        }
    return {"role": "user", "content": m.texto}


def turno_desde_respuesta(respuesta: Any) -> Turno:
    """Un `Turno` desde un `Message` del SDK (o un objeto de la misma forma: grabaciones)."""
    texto = "".join(b.text for b in respuesta.content if b.type == "text")
    llamadas = tuple(
        LlamadaHerramienta(b.id, b.name, dict(b.input))
        for b in respuesta.content
        if b.type == "tool_use"
    )
    uso = respuesta.usage
    detalles = getattr(respuesta, "stop_details", None)
    return Turno(
        texto=texto,
        llamadas=llamadas,
        fin=_FIN.get(respuesta.stop_reason, FinTurno.LIMITE),
        uso=Uso(
            entrada=uso.input_tokens or 0,
            salida=uso.output_tokens or 0,
            cache_lectura=getattr(uso, "cache_read_input_tokens", 0) or 0,
            cache_escritura=getattr(uso, "cache_creation_input_tokens", 0) or 0,
        ),
        modelo_que_respondio=respuesta.model,
        crudo=list(respuesta.content),
        motivo=(getattr(detalles, "category", None) or "") if detalles else "",
    )


class ProveedorClaude:
    nombre = "claude"
    envia_fuera_del_equipo = True

    def __init__(
        self,
        clave: str | None,
        *,
        modelo: str = MODELO_POR_DEFECTO,
        esfuerzo: str = ESFUERZO_POR_DEFECTO,
        con_respaldo: bool = True,
        cliente: Any | None = None,
    ) -> None:
        self.modelo = modelo
        self._esfuerzo = esfuerzo
        self._con_respaldo = con_respaldo
        self._clave = clave
        self._cliente = cliente

    def disponible(self) -> Disponibilidad:
        if not self._clave and self._cliente is None:
            return Disponibilidad(False, "Falta registrar la clave de IA de la empresa.")
        if self._cliente is None and find_spec("anthropic") is None:
            return Disponibilidad(False, FALTA_EL_COMPONENTE)
        return Disponibilidad(True)

    def _crear_cliente(self) -> Any:
        if self._cliente is None:
            import anthropic  # importacion diferida: extra `ia`

            self._cliente = anthropic.Anthropic(api_key=self._clave, max_retries=2)
        return self._cliente

    def turno(
        self,
        sistema: str,
        mensajes: Sequence[Mensaje],
        herramientas: Sequence[EsquemaHerramienta],
    ) -> Turno:
        solicitud = construir_solicitud(
            modelo=self.modelo,
            esfuerzo=self._esfuerzo,
            sistema=sistema,
            mensajes=mensajes,
            herramientas=herramientas,
        )
        cliente = self._crear_cliente()
        try:
            if self._con_respaldo:
                respuesta = cliente.beta.messages.create(
                    betas=[BETA_RESPALDO], fallbacks="default", **solicitud
                )
            else:
                respuesta = cliente.messages.create(**solicitud)
        except Exception as error:  # noqa: BLE001 - se reclasifica del mas especifico al general
            raise _traducir(error) from None
        return turno_desde_respuesta(respuesta)


def _traducir(error: Exception) -> ErrorDeProveedor:
    """Del mas especifico al mas general (S4 §8.5). Nunca incluye encabezados ni la clave."""
    clases = {c.__name__ for c in type(error).__mro__}
    if "AuthenticationError" in clases:
        return ErrorDeProveedor("clave_invalida", "El proveedor rechazo la clave de IA.")
    if clases & {"APIConnectionError", "APITimeoutError"}:
        return ErrorDeProveedor("sin_conexion", "Sin conexion con el proveedor de IA.")
    estado = getattr(error, "status_code", None)
    nombre = type(error).__name__
    return ErrorDeProveedor("otro", f"Error del proveedor de IA ({nombre}, estado {estado}).")
