"""Adaptador de Claude con un cliente falso (S4 §8.5, §10.1; plan 0.9.0, tarea 12).

El cliente falso captura la solicitud y devuelve respuestas grabadas (JSON sanitizado, sin clave ni
encabezados). Los oraculos de la solicitud y de los turnos se escribieron a mano.
"""

from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from asistente.herramientas import HERRAMIENTAS
from asistente.orquestador import herramientas_visibles
from asistente.proveedores.base import (
    ErrorDeProveedor,
    FinTurno,
    LlamadaHerramienta,
    Mensaje,
    ResultadoHerramienta,
    Uso,
)
from asistente.proveedores.claude import (
    BETA_RESPALDO,
    ProveedorClaude,
    construir_solicitud,
    esquema_estricto,
)
from asistente.tarifas import cargar_tarifas, fecha_de_los_precios

SISTEMA = "instrucciones fijas"


def respuesta(stop_reason, contenido, *, uso=None, detalles=None, modelo="claude-opus-5-5"):
    uso = uso or SimpleNamespace(
        input_tokens=100,
        output_tokens=40,
        cache_read_input_tokens=None,
        cache_creation_input_tokens=None,
    )
    return SimpleNamespace(
        stop_reason=stop_reason, content=contenido, usage=uso, model=modelo, stop_details=detalles
    )


TEXTO = SimpleNamespace(type="text", text="hola")
USO_TOOL = SimpleNamespace(type="tool_use", id="toolu_1", name="consultar_borrador", input={})


class ClienteFalso:
    """Captura la ultima solicitud; `beta.messages` y `messages` comparten la misma cola."""

    def __init__(self, *respuestas):
        self._respuestas = list(respuestas)
        self.solicitudes = []
        self.messages = SimpleNamespace(create=self._crear("messages"))
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._crear("beta")))

    def _crear(self, via):
        def crear(**kwargs):
            self.solicitudes.append((via, kwargs))
            siguiente = self._respuestas.pop(0)
            if isinstance(siguiente, Exception):
                raise siguiente
            return siguiente

        return crear


def turno(cliente, **kw):
    proveedor = ProveedorClaude("sk-ant-de-prueba", cliente=cliente, **kw)
    return proveedor.turno(SISTEMA, [Mensaje("usuario", "pedido")], herramientas_visibles(True))


def test_la_solicitud_sale_con_el_orden_fijo_y_los_parametros_del_spec():
    cliente = ClienteFalso(respuesta("end_turn", [TEXTO]))
    turno(cliente, con_respaldo=False)
    via, s = cliente.solicitudes[0]
    assert via == "messages" and "fallbacks" not in s
    assert s["model"] == "claude-opus-5-5"
    assert s["output_config"] == {"effort": "high"}  # explicito, no el valor por defecto
    assert s["tool_choice"] == {"type": "auto"}  # el forzado devuelve 400 en este modelo
    assert s["cache_control"] == {"type": "ephemeral"}
    assert not {"temperature", "top_p", "top_k"} & set(s)
    assert [t["name"] for t in s["tools"]] == [h.nombre for h in HERRAMIENTAS]
    assert all(t["strict"] is True for t in s["tools"])
    assert s["messages"] == [{"role": "user", "content": "pedido"}]


def test_con_respaldo_usa_el_endpoint_beta_y_lo_declara():
    cliente = ClienteFalso(respuesta("end_turn", [TEXTO]))
    turno(cliente, con_respaldo=True)
    via, s = cliente.solicitudes[0]
    assert via == "beta" and s["betas"] == [BETA_RESPALDO] and s["fallbacks"] == "default"


def test_el_esquema_estricto_quita_lo_que_no_admite_y_conserva_la_forma():
    esquema = HERRAMIENTAS[3].esquema()  # proponer_ambiente
    limpio = esquema_estricto(esquema)
    texto = json.dumps(limpio)
    for fuera in ("minLength", "maxLength", "minItems", "maxItems", '"title"'):
        assert fuera not in texto
    assert limpio["additionalProperties"] is False
    assert limpio["required"] == esquema["required"] and "pattern" in texto
    assert "minLength" in json.dumps(esquema)  # el original no se toca


def test_el_historial_devuelve_los_bloques_del_modelo_sin_editarlos_y_un_solo_mensaje():
    crudo = [TEXTO, USO_TOOL]
    mensajes = [
        Mensaje("usuario", "pedido"),
        Mensaje("asistente", "hola", (LlamadaHerramienta("toolu_1", "x", {}),), crudo=crudo),
        Mensaje(
            "usuario",
            resultados=(
                ResultadoHerramienta("toolu_1", "bien"),
                ResultadoHerramienta("toolu_2", "mal", True),
            ),
        ),
    ]
    s = construir_solicitud(
        modelo="m", esfuerzo="high", sistema=SISTEMA, mensajes=mensajes, herramientas=[]
    )
    assert s["messages"][1] == {"role": "assistant", "content": crudo}
    assert s["messages"][1]["content"] is crudo
    assert s["messages"][2]["content"] == [
        {"type": "tool_result", "tool_use_id": "toolu_1", "content": "bien", "is_error": False},
        {"type": "tool_result", "tool_use_id": "toolu_2", "content": "mal", "is_error": True},
    ]


@pytest.mark.parametrize(
    ("stop", "fin"),
    [
        ("end_turn", FinTurno.FIN),
        ("tool_use", FinTurno.HERRAMIENTAS),
        ("max_tokens", FinTurno.LIMITE),
        ("refusal", FinTurno.RECHAZO),
    ],
)
def test_cada_stop_reason_da_su_fin_de_turno(stop, fin):
    cliente = ClienteFalso(
        respuesta(
            stop, [TEXTO, USO_TOOL], detalles=SimpleNamespace(category="cyber", explanation="x")
        )
    )
    t = turno(cliente)
    assert t.fin is fin
    assert t.modelo_que_respondio == "claude-opus-5-5"
    assert [(c.id, c.nombre) for c in t.llamadas] == [("toolu_1", "consultar_borrador")]
    assert t.texto == "hola"


def test_el_uso_trae_los_tokens_de_cache_y_el_motivo_del_rechazo():
    uso = SimpleNamespace(
        input_tokens=10_000,
        output_tokens=3_000,
        cache_read_input_tokens=6_000,
        cache_creation_input_tokens=None,
    )
    cliente = ClienteFalso(
        respuesta("refusal", [], uso=uso, detalles=SimpleNamespace(category="bio", explanation="x"))
    )
    t = turno(cliente)
    assert t.uso == Uso(entrada=10_000, salida=3_000, cache_lectura=6_000, cache_escritura=0)
    assert t.motivo == "bio"
    # costo a mano con la tarifa de Opus 5.5: 10000*4/1e6 + 3000*20/1e6 + 6000*0.2/1e6
    tarifa = cargar_tarifas()["claude-opus-5-5"]
    assert tarifa.costo(t.uso) == Decimal("0.1012")
    assert fecha_de_los_precios() == "2026-09-25"


class AuthenticationError(Exception):
    status_code = 401


class APIConnectionError(Exception):
    pass


class RateLimitError(Exception):
    status_code = 429


@pytest.mark.parametrize(
    ("error", "categoria"),
    [
        (AuthenticationError("sk-ant-de-prueba rechazada"), "clave_invalida"),
        (APIConnectionError("sin red"), "sin_conexion"),
        (RateLimitError("limite"), "otro"),
    ],
)
def test_los_errores_del_sdk_se_traducen_sin_filtrar_la_clave(error, categoria):
    cliente = ClienteFalso(error)
    with pytest.raises(ErrorDeProveedor) as capturado:
        turno(cliente)
    assert capturado.value.categoria == categoria
    assert "sk-ant" not in str(capturado.value)


def test_sin_clave_y_sin_cliente_no_esta_disponible():
    assert not ProveedorClaude(None).disponible().disponible
    assert ProveedorClaude("sk-ant-x").disponible().disponible
