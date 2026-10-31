"""Plan vial, Tarea 16: el asistente explica el riesgo de la obra, no lo calcula.

La herramienta de solo lectura `explicar_riesgo` devuelve las cifras que ya calculó el sistema (las
recibe hechas: `asistente/` no importa `aplicacion.riesgo`, guardia de arquitectura) y el asistente
solo las narra. La validación de citas rechaza una narración con una cifra que no está en lo que la
herramienta devolvió, leída con coma decimal y punto de miles. El proveedor es el doble guionado:
ninguna llamada a un modelo, ningún gasto. Cifras FICTICIAS.
"""

from __future__ import annotations

import json

import pytest

from asistente.explicar_riesgo import (
    HERRAMIENTA,
    explicar,
    salida_de_la_herramienta,
    validar_explicacion,
)
from asistente.herramientas import CAMPOS_PROHIBIDOS, TipoHerramienta
from asistente.proveedores.base import FinTurno, LlamadaHerramienta, Turno
from asistente.proveedores.guionado import ProveedorGuionado
from asistente.validacion import Causa

CIFRAS = {
    "Moneda": "USD",
    "Total base": "1.000,00",
    "P50": "1.248,72",
    "P80": "1.248,72",
    "Reserva": "248,72",
    "Meses completos usados": "24",
    "Insumo que más empuja": "Cemento asfáltico, 248,72",
    "Cobertura": "100,00 % (7 de 7 cortes)",
}
BUENA = (
    "Con 24 meses completos de historia, el P80 de la obra es 1.248,72 USD frente a un total "
    "base de 1.000,00: la reserva es 248,72 y la empuja el cemento asfáltico. En la "
    "comprobación hacia atrás la realidad cayó dentro en 7 de 7 cortes (100,00 %)."
)


def _llamada(id_: str = "l1") -> Turno:
    return Turno(
        texto="",
        llamadas=(LlamadaHerramienta(id_, "explicar_riesgo", {}),),
        fin=FinTurno.HERRAMIENTAS,
    )


def _texto(texto: str) -> Turno:
    return Turno(texto=texto, llamadas=(), fin=FinTurno.FIN)


def test_una_respuesta_con_una_cifra_que_no_esta_en_la_herramienta_se_rechaza() -> None:
    inventada = BUENA.replace("la reserva es 248,72", "la reserva es 250,00")
    proveedor = ProveedorGuionado([_llamada(), _texto(inventada)])
    resultado = explicar(proveedor, CIFRAS)
    assert resultado.texto is None
    assert resultado.rechazo is not None
    assert resultado.rechazo.causa is Causa.NUMERO_AUSENTE_DE_LA_CITA
    assert "250,00" in resultado.rechazo.motivo


def test_una_respuesta_que_solo_narra_las_cifras_de_la_herramienta_se_acepta() -> None:
    proveedor = ProveedorGuionado([_llamada(), _texto(BUENA)])
    resultado = explicar(proveedor, CIFRAS)
    assert resultado.rechazo is None
    assert resultado.texto == BUENA
    # la herramienta devolvió las cifras tal cual, sin calcular nada
    _, mensajes, herramientas = proveedor.recibidos[1]
    (devuelto,) = mensajes[-1].resultados
    assert json.loads(devuelto.contenido) == CIFRAS
    assert [h.nombre for h in herramientas] == ["explicar_riesgo"]


def test_sin_llamar_a_la_herramienta_ninguna_cifra_vale() -> None:
    resultado = explicar(ProveedorGuionado([_texto(BUENA)]), CIFRAS)
    assert resultado.texto is None
    assert resultado.rechazo.causa is Causa.NUMERO_AUSENTE_DE_LA_CITA


def test_una_cifra_redondeada_distinta_tambien_se_rechaza() -> None:
    """1.248,7 no es 1.248,72: el asistente no redondea por su cuenta."""
    salida = salida_de_la_herramienta(CIFRAS)
    assert validar_explicacion("El P80 es 1.248,72 USD.", [salida]) is None
    rechazo = validar_explicacion("El P80 ronda 1.248,7 USD.", [salida])
    assert rechazo is not None and "1.248,7" in rechazo.motivo


def test_una_cifra_con_punto_decimal_anglosajon_se_rechaza() -> None:
    """«248.72» no se lee como 248,72 (coma decimal, punto de miles: regla de Eugenio)."""
    rechazo = validar_explicacion("La reserva es 248.72.", [salida_de_la_herramienta(CIFRAS)])
    assert rechazo is not None and rechazo.causa is Causa.NUMERO_INVALIDO


def test_un_texto_sin_cifras_se_acepta() -> None:
    assert validar_explicacion("El riesgo lo empuja el asfalto.", []) is None


def test_la_herramienta_es_de_lectura_y_no_pide_nada() -> None:
    assert HERRAMIENTA.nombre == "explicar_riesgo"
    assert HERRAMIENTA.tipo is TipoHerramienta.LECTURA
    esquema = HERRAMIENTA.esquema()
    assert esquema["properties"] == {}
    assert esquema["additionalProperties"] is False
    assert not CAMPOS_PROHIBIDOS & set(esquema["properties"])


def test_una_llamada_con_argumentos_recibe_error_y_no_cifras() -> None:
    con_argumentos = Turno(
        texto="",
        llamadas=(LlamadaHerramienta("l1", "explicar_riesgo", {"total": "1"}),),
        fin=FinTurno.HERRAMIENTAS,
    )
    proveedor = ProveedorGuionado([con_argumentos, _texto(BUENA)])
    resultado = explicar(proveedor, CIFRAS)
    _, mensajes, _ = proveedor.recibidos[1]
    (devuelto,) = mensajes[-1].resultados
    assert devuelto.es_error
    assert resultado.texto is None  # nunca recibió cifras: las de su texto no valen


def test_un_guion_que_no_termina_se_corta_en_el_tope_de_turnos() -> None:
    proveedor = ProveedorGuionado([_llamada(f"l{n}") for n in range(10)])
    resultado = explicar(proveedor, CIFRAS, max_turnos=3)
    assert resultado.texto is None
    assert len(proveedor.recibidos) == 3


def test_el_numero_de_un_rotulo_no_es_una_cifra_citable() -> None:
    """«P80» es un rótulo: su 80 no se puede citar como si fuera una cifra que dio el sistema."""
    salida = salida_de_la_herramienta(CIFRAS)
    rechazo = validar_explicacion("Cubre el 80 por ciento de los casos.", [salida])
    assert rechazo is not None
    assert rechazo.causa is Causa.NUMERO_AUSENTE_DE_LA_CITA
    assert "80" in rechazo.motivo


def test_el_rotulo_se_puede_nombrar_en_la_narracion() -> None:
    """Nombrar el rótulo «P80» no es citar la cifra 80: la narración buena lo usa."""
    salida = salida_de_la_herramienta(CIFRAS)
    assert validar_explicacion("El P80 y el P50 coinciden: 1.248,72.", [salida]) is None


def test_una_cifra_pegada_a_una_palabra_tambien_se_valida() -> None:
    """Solo se quitan los rótulos de la herramienta: «Bs250,00» no se escapa de la validación."""
    salida = salida_de_la_herramienta(CIFRAS)
    rechazo = validar_explicacion("La reserva es Bs250,00.", [salida])
    assert rechazo is not None and rechazo.causa is Causa.NUMERO_AUSENTE_DE_LA_CITA


def test_cada_valor_de_la_herramienta_sigue_la_regla_de_las_cifras() -> None:
    """Las cifras de los valores se leen con `cifra_escrita`: «248.72» no es una cifra es-VE y la
    herramienta no la entrega (quien llama le pasa lo que ya ve la persona)."""
    with pytest.raises(ValueError, match="Reserva"):
        salida_de_la_herramienta({**CIFRAS, "Reserva": "248.72"})
    with pytest.raises(ValueError, match="Reserva"):
        explicar(ProveedorGuionado([_llamada(), _texto(BUENA)]), {**CIFRAS, "Reserva": "248.72"})
