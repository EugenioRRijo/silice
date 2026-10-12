"""La prueba exploratoria de S4.0 con dobles: ninguna red, ningun Ollama ni almacen reales."""

from __future__ import annotations

import json
from types import SimpleNamespace

from scripts.explorar_ia import a_markdown, informe_de_keyring, informe_de_ollama


class AlmacenDeMemoria:
    def __init__(self, roto=False):
        self.datos = {}
        self.roto = roto

    def get_keyring(self):
        return self

    def set_password(self, servicio, usuario, clave):
        if self.roto:
            raise OSError("sin almacen")
        self.datos[(servicio, usuario)] = clave

    def get_password(self, servicio, usuario):
        return self.datos.get((servicio, usuario))

    def delete_password(self, servicio, usuario):
        self.datos.pop((servicio, usuario), None)


def test_keyring_ida_y_vuelta_y_borrado_o_el_error_dicho():
    assert informe_de_keyring(AlmacenDeMemoria()) == {
        "backend": "AlmacenDeMemoria",
        "ida_y_vuelta": True,
        "borrado": True,
    }
    assert informe_de_keyring(AlmacenDeMemoria(roto=True))["error"] == "OSError"


def respuesta(contenido="", llamadas=None):
    return SimpleNamespace(
        message=SimpleNamespace(content=contenido, tool_calls=llamadas), eval_count=12
    )


def test_ollama_con_herramientas_y_salida_restringida():
    llamada = SimpleNamespace(function=SimpleNamespace(name="saludar", arguments={"nombre": "Ana"}))
    objeto = json.dumps({"herramienta": "saludar", "argumentos": {"nombre": "Ana"}})
    cliente = SimpleNamespace(chat=lambda **kw: respuesta(objeto, [llamada]))
    relojes = iter([10.0, 12.5, 12.5, 12.5])
    informe = informe_de_ollama(cliente, "modelo-x", "0.9.0", lambda: next(relojes))
    assert informe == {
        "modelo": "modelo-x",
        "version": "0.9.0",
        "herramientas": True,
        "segundos_por_turno": 2.5,
        "fichas_de_salida": 12,
        "salida_restringida": True,
    }


def test_lo_que_falla_se_dice_no_comprobado_y_nunca_se_afirma():
    def falla(**kw):
        raise ConnectionError("sin servicio")

    informe = informe_de_ollama(SimpleNamespace(chat=falla), "m", "0.9.0", lambda: 0.0)
    assert informe["herramientas"] == "no comprobado (ConnectionError)"
    assert informe["salida_restringida"] == "no comprobado (ConnectionError)"
    texto = a_markdown("ollama", informe)
    assert texto.startswith("### ollama") and "| herramientas | no comprobado" in texto
