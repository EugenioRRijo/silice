"""El puente MCP hacia Antigravity arma `agy -p` en solo lectura y no se cuelga.

Lo que importa probar es lo que se aprendió a mano el 2026-11-04: sin `stdin` cerrado `agy -p` espera
para siempre; sin `--sandbox` podría editar; el encargo debe empezar por las reglas del repositorio.
El servidor MCP en sí (paquete `mcp`) no es dependencia del producto y no se importa aquí.
"""

from __future__ import annotations

import subprocess

import pytest

from scripts import mcp_antigravity as puente


def test_el_comando_va_en_sandbox_y_sin_saltarse_permisos():
    comando = puente.armar_comando("revisa X", continuar=False, minutos=5)
    assert comando[:3] == [puente.AGY, "-p", comando[2]]
    assert "--sandbox" in comando
    assert "--dangerously-skip-permissions" not in comando
    assert comando[comando.index("--print-timeout") + 1] == "5m0s"
    assert "--continue" not in comando


def test_continuar_retoma_la_conversacion():
    assert "--continue" in puente.armar_comando("sigue", continuar=True, minutos=5)


def test_el_encargo_empieza_por_las_reglas_y_lleva_el_pedido_entero():
    encargo = puente.armar_encargo("Audita la rama feature/x contra main.")
    assert encargo.index("AGENTS.md") < encargo.index("Audita la rama feature/x contra main.")
    assert "docs/ESTADO.md" in encargo
    assert "solo lectura" in encargo.lower()


@pytest.mark.parametrize("minutos", [0, -1, 31])
def test_los_minutos_fuera_de_rango_se_rechazan(minutos):
    with pytest.raises(ValueError, match="minutos"):
        puente.armar_comando("x", continuar=False, minutos=minutos)


def test_encargo_vacio_se_rechaza():
    with pytest.raises(ValueError, match="encargo"):
        puente.armar_encargo("   ")


def test_ejecutar_cierra_stdin_y_devuelve_la_salida():
    vistos = {}

    def correr(comando, **kwargs):
        vistos.update(kwargs)
        return subprocess.CompletedProcess(comando, 0, stdout="OK\n", stderr="ruido del registro")

    assert puente.ejecutar(["agy"], minutos=1, correr=correr) == "OK"
    assert vistos["stdin"] is subprocess.DEVNULL
    assert vistos["cwd"] == puente.RAIZ
    assert vistos["timeout"] > 60


def test_ejecutar_explica_el_tiempo_agotado_y_el_error():
    def agotado(comando, **kwargs):
        raise subprocess.TimeoutExpired(comando, kwargs["timeout"])

    def falla(comando, **kwargs):
        return subprocess.CompletedProcess(comando, 2, stdout="", stderr="sin sesion de Google")

    assert "tiempo" in puente.ejecutar(["agy"], minutos=1, correr=agotado).lower()
    texto = puente.ejecutar(["agy"], minutos=1, correr=falla)
    assert "2" in texto and "sin sesion de Google" in texto
