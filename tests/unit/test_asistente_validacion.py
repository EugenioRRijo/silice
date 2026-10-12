"""Las cuatro capas de validacion y cada causa de rechazo de S4 §7.4 (plan 0.9.0, tarea 6).

Una prueba por causa, con su frontera. Los oraculos son tablas escritas a mano antes del codigo.
"""

from __future__ import annotations

import pytest

from asistente.propuestas import EstadoPropuesta, Propuesta, TipoPropuesta, aplicar
from asistente.validacion import Causa, Rechazo, validar_llamada
from tests.fixtures.asistente_pedidos import AMBIENTE, FECHA, ORIGEN, catalogo, contexto
from ui.hoja import Borrador


def _ok(nombre, argumentos, **kw) -> Propuesta:
    resultado = validar_llamada(nombre, argumentos, contexto(**kw))
    assert isinstance(resultado, Propuesta), resultado
    return resultado


def _no(nombre, argumentos, causa: Causa, **kw) -> Rechazo:
    resultado = validar_llamada(nombre, argumentos, contexto(**kw))
    assert isinstance(resultado, Rechazo), resultado
    assert resultado.causa is causa, resultado
    return resultado


def test_un_ambiente_bien_citado_queda_pendiente_con_numeros_de_punto_decimal():
    p = _ok("proponer_ambiente", AMBIENTE)
    assert p.estado is EstadoPropuesta.PENDIENTE and p.tipo is TipoPropuesta.AMBIENTE
    assert dict(p.filas[0]) == {
        "id": "BAN-01",
        "nombre": "Bano",
        "x0": "0",
        "y0": "0",
        "largo": "2.4",
        "ancho": "1.5",
        "alto": "2.5",
    }
    assert p.supuestos == (
        ("x0", "esquina del bano en el origen"),
        ("y0", "esquina del bano en el origen"),
    )


def test_campo_extra_faltante_y_tipo_invalido():
    _no("proponer_ambiente", {**AMBIENTE, "precio": "9"}, Causa.CAMPO_EXTRA)
    sin_alto = {k: v for k, v in AMBIENTE.items() if k != "alto"}
    _no("proponer_ambiente", sin_alto, Causa.CAMPO_FALTANTE)
    _no("proponer_ambiente", {**AMBIENTE, "largo": 2.4}, Causa.TIPO_INVALIDO)
    _no("proponer_fuente", {"id": "F1"}, Causa.CAMPO_FALTANTE)
    _no("herramienta_inventada", {}, Causa.TIPO_INVALIDO)


@pytest.mark.parametrize(("largo", "acepta"), [("2.400", True), ("2.4000", False)])
def test_frontera_de_tres_y_cuatro_decimales(largo, acepta):
    citas = [{"campo": "largo", "texto": "2,4"}]
    argumentos = {**AMBIENTE, "largo": largo, "citas": citas + AMBIENTE["citas"][1:]}
    if acepta:
        _ok("proponer_ambiente", argumentos)
    else:
        _no("proponer_ambiente", argumentos, Causa.NUMERO_INVALIDO)


def test_id_repetido_en_el_borrador_y_en_las_pendientes():
    primero = _ok("proponer_ambiente", AMBIENTE)
    _no("proponer_ambiente", AMBIENTE, Causa.ID_REPETIDO, pendientes=[primero], siguiente_id="P2")


def test_referencia_inexistente():
    punto = {
        "id": "P1",
        "nombre": "lavamanos",
        "especialidad": "agua",
        "tipo": "agua_fria",
        "ambiente_id": "NO-EXISTE",
        "superficie": "pared",
        "x": "1",
        "y": "0",
        "z": "0.6",
        "fuente_id": None,
        "circuito_id": None,
        "especificaciones": [],
        "citas": [{"campo": "z", "texto": "60 cm"}],
        "supuestos": [{"campo": "x", "motivo": "m"}, {"campo": "y", "motivo": "m"}],
    }
    _no("proponer_punto", punto, Causa.REFERENCIA_INEXISTENTE)


def test_partida_inexistente_y_unidad_no_equivalente():
    base = {
        "codigo": "AF-SALIDA",
        "unidad": "punto",
        "cantidad": "2",
        "citas": [{"campo": "cantidad", "texto": "2"}],
        "supuestos": [],
    }
    _no(
        "proponer_partida",
        {**base, "codigo": "XX-999"},
        Causa.PARTIDA_INEXISTENTE,
        textos=("necesito 2 salidas",),
    )
    _no(
        "proponer_partida",
        {**base, "unidad": "m"},
        Causa.UNIDAD_NO_EQUIVALENTE,
        textos=("necesito 2 salidas",),
    )
    _ok("proponer_partida", {**base, "unidad": "pto"}, textos=("necesito 2 salidas",))


def test_numero_sin_cita_ni_supuesto_cita_no_literal_y_numero_ausente():
    sin_cita = {**AMBIENTE, "citas": AMBIENTE["citas"][1:]}
    _no("proponer_ambiente", sin_cita, Causa.SIN_CITA_NI_SUPUESTO)
    inventada = {
        **AMBIENTE,
        "citas": [{"campo": "largo", "texto": "3,0 m de largo"}] + AMBIENTE["citas"][1:],
    }
    _no("proponer_ambiente", inventada, Causa.CITA_NO_LITERAL)
    ausente = {
        **AMBIENTE,
        "largo": "2.5",
        "citas": [{"campo": "largo", "texto": "2,4"}] + AMBIENTE["citas"][1:],
    }
    _no("proponer_ambiente", ausente, Causa.NUMERO_AUSENTE_DE_LA_CITA)


@pytest.mark.parametrize(
    ("cita", "z", "acepta"),
    [
        ("60 cm", "0.6", True),  # cm -> m
        ("60 cm", "0.60", True),  # 0.60 == 0.6
        ("60 cm", "0.61", False),
        ("600 mm", "0.6", True),  # mm -> m
        ("2,5 m", "2.5", True),  # coma del pedido, punto del campo
    ],
)
def test_conversion_de_unidades_de_la_lista_cerrada(cita, z, acepta):
    punto = {
        "id": "P1",
        "nombre": "x",
        "especialidad": "agua",
        "tipo": "agua_fria",
        "ambiente_id": "BAN-01",
        "superficie": "pared",
        "x": "0",
        "y": "0",
        "z": z,
        "fuente_id": None,
        "circuito_id": None,
        "especificaciones": [],
        "citas": [{"campo": "z", "texto": cita}],
        "supuestos": [{"campo": "x", "motivo": "m"}, {"campo": "y", "motivo": "m"}],
    }
    ambiente = _ok("proponer_ambiente", AMBIENTE)
    texto = (f"la toma esta a {cita} del piso",)
    resultado = validar_llamada(
        "proponer_punto", punto, contexto(pendientes=[ambiente], textos=texto, siguiente_id="P2")
    )
    assert isinstance(resultado, Propuesta) is acepta, resultado


def test_dimension_cero_es_fila_no_construible_y_un_punto_fuera_del_ambiente_pasa():
    cero = {
        **AMBIENTE,
        "ancho": "0",
        "citas": AMBIENTE["citas"][:1] + [{"campo": "ancho", "texto": "0"}] + AMBIENTE["citas"][2:],
    }
    _no("proponer_ambiente", cero, Causa.FILA_NO_CONSTRUIBLE, textos=("ancho 0 y 2,4 y 2,5 m",))
    ambiente = _ok("proponer_ambiente", AMBIENTE)
    fuera = {
        "id": "P1",
        "nombre": "x",
        "especialidad": "agua",
        "tipo": "agua_fria",
        "ambiente_id": "BAN-01",
        "superficie": "pared",
        "x": "3",
        "y": "0",
        "z": "0.6",
        "fuente_id": None,
        "circuito_id": None,
        "especificaciones": [],
        "citas": [{"campo": "x", "texto": "3,0 m"}, {"campo": "z", "texto": "60 cm"}],
        "supuestos": [{"campo": "y", "motivo": "m"}],
    }
    # el error geometrico (x = 3,0 en un ambiente de 2,4) NO se rechaza: es de R9 (S4 §7.4)
    _ok(
        "proponer_punto",
        fuera,
        pendientes=[ambiente],
        siguiente_id="P2",
        textos=("toma a 3,0 m y a 60 cm",),
    )


def test_notas_de_terminar_con_montos():
    assert not isinstance(
        validar_llamada("terminar", {"notas": ["quedo el bano"]}, contexto()), Rechazo
    )
    for nota in ("cuesta 100 USD", "unos $ 50", "Bs. 300", "20 dolares"):
        _no("terminar", {"notas": [nota]}, Causa.NOTAS_CON_MONTOS)


def test_un_recorrido_declarado_necesita_tramos_y_un_punto_o_un_circuito():
    base = {
        "punto_id": None,
        "circuito_id": None,
        "modo": "propuesto",
        "tramos": None,
        "citas": [],
        "supuestos": [],
    }
    _no("proponer_recorrido", base, Causa.FILA_NO_CONSTRUIBLE)
    _no(
        "proponer_recorrido",
        {**base, "punto_id": "P1", "modo": "declarado"},
        Causa.REFERENCIA_INEXISTENTE,
    )


def test_una_cita_tomada_del_resumen_del_borrador_y_no_del_pedido_se_rechaza():
    """La cita debe salir del pedido, no del resumen del borrador (S4 §8.7)."""
    ambiente = _ok("proponer_ambiente", AMBIENTE)
    borrador = aplicar(Borrador(fecha=FECHA), [ambiente], ORIGEN, catalogo())
    punto = {
        "id": "P1",
        "nombre": "x",
        "especialidad": "agua",
        "tipo": "agua_fria",
        "ambiente_id": "BAN-01",
        "superficie": "pared",
        "x": "2.4",
        "y": "0",
        "z": "0.6",
        "fuente_id": None,
        "circuito_id": None,
        "especificaciones": [],
        "citas": [{"campo": "x", "texto": "2,4"}, {"campo": "z", "texto": "60 cm"}],
        "supuestos": [{"campo": "y", "motivo": "m"}],
    }
    contexto_ = contexto(borrador=borrador, textos=("Una toma de agua a 60 cm del piso.",))
    resultado = validar_llamada("proponer_punto", punto, contexto_)
    assert isinstance(resultado, Rechazo) and resultado.causa is Causa.CITA_NO_LITERAL
