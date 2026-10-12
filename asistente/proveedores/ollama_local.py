"""Adaptador del modelo local servido por Ollama (S4 §8.6, RNF-18 a). Importacion diferida.

* El anfitrion debe RESOLVER a una IP de bucle local (`127.0.0.0/8` o `::1`), comprobado por la IP
  resuelta y no por el nombre; si no, se trata como modo nube (`envia_fuera_del_equipo`) y se avisa.
* Ollama no tiene autenticacion y ha tenido vulnerabilidades (SEG-18): se exige una VERSION MINIMA
  (fijada en S4.0, `asistente/config_ia.json`); con una menor, el modo local no esta
  disponible (9b).
* Plan B si el modelo no admite llamadas a herramientas: salida estructurada, un solo objeto
  `{"herramienta": ..., "argumentos": {...}}` que se valida con los mismos modelos Pydantic.
"""

from __future__ import annotations

import ipaddress
import json
import socket
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import urlparse

from asistente.proveedores.base import (
    Disponibilidad,
    ErrorDeProveedor,
    EsquemaHerramienta,
    FinTurno,
    LlamadaHerramienta,
    Mensaje,
    Turno,
    Uso,
)

ANFITRION_POR_DEFECTO = "http://127.0.0.1:11434"
Resolvedor = Callable[..., Sequence[tuple[Any, ...]]]


def _anfitrion(url: str) -> str:
    return urlparse(url if "//" in url else f"//{url}").hostname or ""


def es_bucle_local(url: str, resolver: Resolvedor = socket.getaddrinfo) -> bool:
    """True solo si TODAS las IP a las que resuelve el anfitrion son de bucle local."""
    nombre = _anfitrion(url)
    if not nombre:
        return False
    try:
        direcciones = {info[4][0].split("%", 1)[0] for info in resolver(nombre, None)}
    except OSError:
        return False
    try:
        return bool(direcciones) and all(ipaddress.ip_address(d).is_loopback for d in direcciones)
    except ValueError:
        return False


def version_a_tupla(texto: str) -> tuple[int, ...]:
    """`"0.9.2"` -> (0, 9, 2); un sufijo como `-rc1` se ignora."""
    return tuple(int(p) for p in texto.split("-", 1)[0].split("+", 1)[0].split("."))


def extraer_objeto(texto: str) -> dict[str, Any] | None:
    """El primer objeto JSON de `texto` (puede haber texto alrededor), o `None`."""
    decodificador = json.JSONDecoder()
    for inicio, caracter in enumerate(texto):
        if caracter != "{":
            continue
        try:
            objeto, _ = decodificador.raw_decode(texto, inicio)
        except json.JSONDecodeError:
            continue
        if isinstance(objeto, dict):
            return objeto
    return None


def instruccion_estructurada(herramientas: Sequence[EsquemaHerramienta]) -> str:
    catalogo = "\n".join(
        f"- {h.nombre}: {h.descripcion} Argumentos: {json.dumps(h.esquema, sort_keys=True)}"
        for h in herramientas
    )
    return (
        "Responde SIEMPRE con un unico objeto JSON "
        '{"herramienta": "<nombre>", "argumentos": {...}} y nada mas. Herramientas:\n' + catalogo
    )


class ProveedorOllama:
    nombre = "ollama"

    def __init__(
        self,
        modelo: str,
        *,
        anfitrion: str = ANFITRION_POR_DEFECTO,
        version_minima: tuple[int, ...],
        estructurado: bool = False,
        cliente: Any | None = None,
        obtener_version: Callable[[], str] | None = None,
        resolver: Resolvedor = socket.getaddrinfo,
    ) -> None:
        self.modelo = modelo
        self._anfitrion = anfitrion
        self._version_minima = version_minima
        self._estructurado = estructurado
        self._cliente = cliente
        self._obtener_version = obtener_version
        self._local = es_bucle_local(anfitrion, resolver)

    @property
    def envia_fuera_del_equipo(self) -> bool:
        """Un anfitrion que no resuelve a bucle local es un destino externo: modo nube."""
        return not self._local

    def _crear_cliente(self) -> Any:
        if self._cliente is None:
            import ollama  # importacion diferida: extra `ia`

            self._cliente = ollama.Client(host=self._anfitrion)
        return self._cliente

    def disponible(self) -> Disponibilidad:
        try:
            version = (self._obtener_version or self._version_del_servicio)()
            if version_a_tupla(version) < self._version_minima:
                minima = ".".join(map(str, self._version_minima))
                return Disponibilidad(
                    False, f"Ollama {version} es anterior a la minima ({minima})."
                )
            instalados = {m.model for m in self._crear_cliente().list().models}
        except (OSError, ValueError, AttributeError) as error:
            return Disponibilidad(
                False, f"El servicio de Ollama no responde ({type(error).__name__})."
            )
        if self.modelo not in instalados:
            return Disponibilidad(False, f"El modelo {self.modelo!r} no esta instalado en Ollama.")
        return Disponibilidad(True)

    def _version_del_servicio(self) -> str:
        from urllib.request import urlopen

        base = self._anfitrion if "//" in self._anfitrion else f"http://{self._anfitrion}"
        with urlopen(f"{base}/api/version", timeout=5) as respuesta:
            return json.load(respuesta)["version"]

    def turno(
        self,
        sistema: str,
        mensajes: Sequence[Mensaje],
        herramientas: Sequence[EsquemaHerramienta],
    ) -> Turno:
        cliente = self._crear_cliente()
        pedido: dict[str, Any] = {
            "model": self.modelo,
            "messages": _mensajes(sistema, mensajes, herramientas if self._estructurado else ()),
            "options": {"temperature": 0},
        }
        if not self._estructurado:
            pedido["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": h.nombre,
                        "description": h.descripcion,
                        "parameters": dict(h.esquema),
                    },
                }
                for h in herramientas
            ]
        try:
            respuesta = cliente.chat(**pedido)
        except (ConnectionError, OSError) as error:
            raise ErrorDeProveedor("sin_conexion", "El servicio de Ollama no responde.") from error
        return self._a_turno(respuesta, len(mensajes))

    def _a_turno(self, respuesta: Any, n: int) -> Turno:
        uso = Uso(
            entrada=getattr(respuesta, "prompt_eval_count", 0) or 0,
            salida=getattr(respuesta, "eval_count", 0) or 0,
        )
        texto = respuesta.message.content or ""
        modelo = getattr(respuesta, "model", self.modelo)
        if self._estructurado:
            objeto = extraer_objeto(texto)
            if objeto is None or "herramienta" not in objeto or "argumentos" not in objeto:
                return Turno(texto, (), FinTurno.LIMITE, uso, modelo, motivo="salida_invalida")
            llamada = LlamadaHerramienta(
                f"local_{n}", str(objeto["herramienta"]), dict(objeto["argumentos"])
            )
            return Turno("", (llamada,), FinTurno.HERRAMIENTAS, uso, modelo)
        llamadas = tuple(
            LlamadaHerramienta(f"local_{n}_{i}", c.function.name, dict(c.function.arguments))
            for i, c in enumerate(respuesta.message.tool_calls or ())
        )
        corte = getattr(respuesta, "done_reason", "stop") == "length"
        fin = FinTurno.LIMITE if corte else (FinTurno.HERRAMIENTAS if llamadas else FinTurno.FIN)
        return Turno(texto, llamadas, fin, uso, modelo)


def _mensajes(
    sistema: str, mensajes: Sequence[Mensaje], estructurado: Sequence[EsquemaHerramienta]
) -> list[dict[str, Any]]:
    cabecera = sistema + ("\n\n" + instruccion_estructurada(estructurado) if estructurado else "")
    salida: list[dict[str, Any]] = [{"role": "system", "content": cabecera}]
    nombres: dict[str, str] = {}
    for m in mensajes:
        if m.rol == "asistente":
            nombres.update({c.id: c.nombre for c in m.llamadas})
            entrada: dict[str, Any] = {"role": "assistant", "content": m.texto}
            if m.llamadas and not estructurado:
                entrada["tool_calls"] = [
                    {"function": {"name": c.nombre, "arguments": dict(c.argumentos)}}
                    for c in m.llamadas
                ]
            elif m.llamadas:
                c = m.llamadas[0]
                entrada["content"] = json.dumps(
                    {"herramienta": c.nombre, "argumentos": dict(c.argumentos)}
                )
            salida.append(entrada)
        elif m.resultados:
            for r in m.resultados:
                if estructurado:
                    salida.append(
                        {
                            "role": "user",
                            "content": (
                                f"Resultado de {nombres.get(r.llamada_id, '?')}:\n{r.contenido}"
                            ),
                        }
                    )
                else:
                    salida.append(
                        {
                            "role": "tool",
                            "tool_name": nombres.get(r.llamada_id, ""),
                            "content": r.contenido,
                        }
                    )
        else:
            salida.append({"role": "user", "content": m.texto})
    return salida
