"""Adaptador de Ollama: bucle local por IP resuelta, version minima, plan B (S4 §8.6, RNF-18 a).

Respuestas grabadas del servicio local (formas de `ollama.ChatResponse`); ningun Ollama real.
"""

from __future__ import annotations

import socket
from types import SimpleNamespace

import pytest

from asistente.orquestador import herramientas_visibles
from asistente.proveedores.base import (
    ErrorDeProveedor,
    FinTurno,
    LlamadaHerramienta,
    Mensaje,
    ResultadoHerramienta,
)
from asistente.proveedores.ollama_local import (
    ProveedorOllama,
    es_bucle_local,
    extraer_objeto,
    version_a_tupla,
)

MINIMA = (0, 9, 0)


def resolvedor(*direcciones):
    def resolver(nombre, puerto):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (d, 0)) for d in direcciones]

    return resolver


@pytest.mark.parametrize(
    ("url", "ips", "local"),
    [
        ("http://localhost:11434", ["127.0.0.1"], True),  # localhost -> 127.0.0.1
        ("127.0.0.1:11434", ["127.0.0.1"], True),
        ("http://[::1]:11434", ["::1"], True),
        ("http://127.0.5.9:11434", ["127.0.5.9"], True),  # todo 127.0.0.0/8
        ("http://ollama.empresa.local:11434", ["192.168.1.20"], False),  # nombre no local
        ("http://parece-local:11434", ["127.0.0.1", "10.0.0.5"], False),  # una sola IP externa
        ("http://x:11434", [], False),
    ],
)
def test_el_bucle_local_se_decide_por_la_ip_resuelta_y_no_por_el_nombre(url, ips, local):
    assert es_bucle_local(url, resolvedor(*ips)) is local


def test_un_nombre_que_no_resuelve_se_trata_como_nube():
    def falla(nombre, puerto):
        raise socket.gaierror("sin DNS")

    assert es_bucle_local("http://inexistente:11434", falla) is False


def test_un_anfitrion_no_local_se_marca_como_envio_fuera_del_equipo():
    nube = ProveedorOllama(
        "m", anfitrion="http://srv:11434", version_minima=MINIMA, resolver=resolvedor("203.0.113.9")
    )
    local = ProveedorOllama(
        "m",
        anfitrion="http://localhost:11434",
        version_minima=MINIMA,
        resolver=resolvedor("127.0.0.1"),
    )
    assert nube.envia_fuera_del_equipo and not local.envia_fuera_del_equipo


def cliente(*, modelos=("m",), chat=None):
    return SimpleNamespace(
        list=lambda: SimpleNamespace(models=[SimpleNamespace(model=m) for m in modelos]),
        chat=chat or (lambda **kw: None),
    )


def proveedor(version="0.9.0", **kw):
    return ProveedorOllama(
        "m",
        version_minima=MINIMA,
        resolver=resolvedor("127.0.0.1"),
        obtener_version=lambda: version,
        **kw,
    )


def test_la_version_menor_que_la_minima_deja_el_modo_local_no_disponible():
    assert version_a_tupla("0.9.0-rc1") == (0, 9, 0)
    assert proveedor("0.9.0", cliente=cliente()).disponible().disponible
    d = proveedor("0.8.9", cliente=cliente()).disponible()
    assert not d.disponible and "0.8.9" in d.motivo and "0.9.0" in d.motivo


def test_modelo_no_instalado_y_servicio_caido_dicen_que_falta():
    assert "no esta instalado" in proveedor(cliente=cliente(modelos=("otro",))).disponible().motivo

    def cae():
        raise ConnectionError("rechazada")

    caido = ProveedorOllama(
        "m",
        version_minima=MINIMA,
        resolver=resolvedor("127.0.0.1"),
        obtener_version=cae,
        cliente=cliente(),
    )
    assert "no responde" in caido.disponible().motivo


def respuesta(contenido="", llamadas=None, razon="stop"):
    return SimpleNamespace(
        message=SimpleNamespace(content=contenido, tool_calls=llamadas),
        done_reason=razon,
        prompt_eval_count=50,
        eval_count=7,
        model="m",
    )


def llamada_ollama(nombre, argumentos):
    return SimpleNamespace(function=SimpleNamespace(name=nombre, arguments=argumentos))


def turno(prov, *mensajes):
    return prov.turno(
        "sistema", list(mensajes) or [Mensaje("usuario", "pedido")], herramientas_visibles(True)
    )


def test_llamadas_a_herramientas_a_turno_y_solicitud_con_tools():
    capturado = {}

    def chat(**kw):
        capturado.update(kw)
        return respuesta(llamadas=[llamada_ollama("consultar_borrador", {})])

    t = turno(proveedor(cliente=cliente(chat=chat)))
    assert t.fin is FinTurno.HERRAMIENTAS and t.llamadas[0].nombre == "consultar_borrador"
    assert (t.uso.entrada, t.uso.salida) == (50, 7)
    assert capturado["tools"][0]["function"]["name"] == "consultar_borrador"
    assert capturado["messages"][0] == {"role": "system", "content": "sistema"}


def test_texto_solo_es_fin_y_corte_por_longitud_es_limite():
    assert (
        turno(proveedor(cliente=cliente(chat=lambda **kw: respuesta("listo")))).fin is FinTurno.FIN
    )
    cortado = cliente(chat=lambda **kw: respuesta("abc", razon="length"))
    assert turno(proveedor(cliente=cortado)).fin is FinTurno.LIMITE


def test_el_historial_lleva_las_llamadas_y_los_resultados_con_el_nombre_de_la_herramienta():
    capturado = {}

    def chat(**kw):
        capturado.update(kw)
        return respuesta("ok")

    asistente = Mensaje(
        "asistente", "", (LlamadaHerramienta("local_1_0", "consultar_borrador", {}),)
    )
    resultado = Mensaje("usuario", resultados=(ResultadoHerramienta("local_1_0", "datos"),))
    turno(proveedor(cliente=cliente(chat=chat)), Mensaje("usuario", "pedido"), asistente, resultado)
    assert capturado["messages"][2]["tool_calls"][0]["function"]["name"] == "consultar_borrador"
    assert capturado["messages"][3] == {
        "role": "tool",
        "tool_name": "consultar_borrador",
        "content": "datos",
    }


def test_sin_conexion_es_un_error_de_proveedor_9a():
    def chat(**kw):
        raise ConnectionError("rechazada")

    with pytest.raises(ErrorDeProveedor) as capturado:
        turno(proveedor(cliente=cliente(chat=chat)))
    assert capturado.value.categoria == "sin_conexion"


# --- plan B: salida estructurada ---------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ('{"herramienta": "terminar", "argumentos": {"notas": []}}', ("terminar", {"notas": []})),
        (
            'Claro: {"herramienta": "terminar", "argumentos": {"notas": []}} listo.',
            ("terminar", {"notas": []}),
        ),
        ('{"herramienta": "terminar"}', None),  # falta `argumentos`
        ("no es json", None),
        ("{ roto", None),
    ],
)
def test_plan_b_objeto_valido_con_texto_alrededor_e_invalido(texto, esperado):
    prov = proveedor(estructurado=True, cliente=cliente(chat=lambda **kw: respuesta(texto)))
    t = turno(prov)
    if esperado is None:
        assert t.fin is FinTurno.LIMITE and t.llamadas == () and t.motivo == "salida_invalida"
    else:
        assert t.fin is FinTurno.HERRAMIENTAS
        assert (t.llamadas[0].nombre, dict(t.llamadas[0].argumentos)) == esperado


def test_plan_b_no_envia_tools_y_describe_el_formato_en_el_sistema():
    capturado = {}

    def chat(**kw):
        capturado.update(kw)
        return respuesta('{"herramienta": "terminar", "argumentos": {"notas": []}}')

    turno(proveedor(estructurado=True, cliente=cliente(chat=chat)))
    assert "tools" not in capturado
    assert '"herramienta"' in capturado["messages"][0]["content"]


def test_extraer_objeto_ignora_corchetes_que_no_son_objeto():
    assert extraer_objeto('[1, 2] {"a": 1}') == {"a": 1}
    assert extraer_objeto("{") is None
