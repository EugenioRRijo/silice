"""Una corrida del experimento de punta a punta con el proveedor guionado (plan 0.9.0, tarea 19).

El guion es la solucion que un modelo ideal daria a `dev-agua-01`; los defectuosos cambian un dato
y el resultado esperado (errores, detecciones, metricas) esta calculado a mano.
"""

from __future__ import annotations

from decimal import Decimal

from asistente.experimento.banco import cargar_banco
from asistente.experimento.ejecucion import correr
from asistente.proveedores.base import FinTurno, LlamadaHerramienta, Tarifa, Turno, Uso
from asistente.proveedores.guionado import ProveedorGuionado
from tests.fixtures import caso_of001
from tests.fixtures.asistente_banco import catalogo_del_experimento

FICHA = cargar_banco()["dev-agua-01"]
TARIFA = Tarifa(entrada=Decimal(1_000_000), salida=Decimal(2_000_000))


def cita(campo, texto):
    return {"campo": campo, "texto": texto}


def sup(campo, motivo="dato del pedido"):
    return {"campo": campo, "motivo": motivo}


def llamada(n, nombre, argumentos):
    return LlamadaHerramienta(f"c{n}", nombre, argumentos)


def guion(x_lavamanos="1,5 m", incluir_ducha=True, x_supuesto=False):
    ambiente = llamada(
        1,
        "proponer_ambiente",
        {
            "id": "BAN",
            "nombre": "Bano",
            "x0": "0",
            "y0": "0",
            "largo": "2.0",
            "ancho": "1.5",
            "alto": "2.5",
            "citas": [
                cita("largo", "2,0"),
                cita("ancho", "1,5 m"),
                cita("alto", "alto de 2,5 m"),
                cita("x0", "(0;0)"),
                cita("y0", "(0;0)"),
            ],
            "supuestos": [],
        },
    )
    fuente = llamada(
        2,
        "proponer_fuente",
        {
            "id": "MONT",
            "especialidad": "agua",
            "tipo": "montante_agua",
            "ambiente_id": "BAN",
            "x": "0",
            "y": "0",
            "z": "0",
            "citas": [cita("x", "(0;0;0)"), cita("y", "(0;0;0)"), cita("z", "(0;0;0)")],
            "supuestos": [],
        },
    )
    lavamanos = llamada(
        3,
        "proponer_punto",
        {
            "id": "LAV",
            "nombre": "lavamanos",
            "especialidad": "agua",
            "tipo": "agua_fria",
            "ambiente_id": "BAN",
            "superficie": "pared",
            "x": x_lavamanos.split()[0].replace(",", "."),
            "y": "0",
            "z": "0.6",
            "fuente_id": "MONT",
            "circuito_id": None,
            "especificaciones": [
                {"clave": "diametro", "valor": '1/2"'},
                {"clave": "llave_de_paso", "valor": "si"},
            ],
            "citas": [
                *([] if x_supuesto else [cita("x", f"x = {x_lavamanos}")]),
                cita("y", "y = 0 m"),
                cita("z", "60 cm"),
            ],
            "supuestos": [sup("x", "estimado a ojo")] if x_supuesto else [],
        },
    )
    ducha = llamada(
        4,
        "proponer_punto",
        {
            "id": "DUC",
            "nombre": "ducha",
            "especialidad": "agua",
            "tipo": "agua_fria",
            "ambiente_id": "BAN",
            "superficie": "pared",
            "x": "1.0",
            "y": "1.5",
            "z": "1.2",
            "fuente_id": "MONT",
            "circuito_id": None,
            "especificaciones": [
                {"clave": "diametro", "valor": '3/4"'},
                {"clave": "llave_de_paso", "valor": "si"},
            ],
            "citas": [cita("x", "x = 1,0 m"), cita("y", "y = 1,5 m"), cita("z", "1,2 m")],
            "supuestos": [],
        },
    )
    r1 = llamada(
        5,
        "proponer_recorrido",
        {
            "punto_id": "LAV",
            "circuito_id": None,
            "modo": "propuesto",
            "tramos": None,
            "citas": [],
            "supuestos": [],
        },
    )
    r2 = llamada(
        6,
        "proponer_recorrido",
        {
            "punto_id": "DUC",
            "circuito_id": None,
            "modo": "propuesto",
            "tramos": None,
            "citas": [],
            "supuestos": [],
        },
    )
    cierre = llamada(7, "terminar", {"notas": ["bano propuesto"]})
    llamadas = [
        ambiente,
        fuente,
        lavamanos,
        *([ducha] if incluir_ducha else []),
        r1,
        *([r2] if incluir_ducha else []),
        cierre,
    ]
    return [Turno("", tuple(llamadas), FinTurno.HERRAMIENTAS, Uso(entrada=2, salida=1), "guion-1")]


def corrida(guion_):
    return correr(
        FICHA,
        ProveedorGuionado(guion_),
        catalogo=catalogo_del_experimento(),
        tarifa=TARIFA,
        composiciones=caso_of001.COMPOSICIONES,
    )


def test_el_modelo_ideal_no_comete_errores_y_tiene_exhaustividad_total():
    c = corrida(guion())
    assert c.errores == ()
    assert (c.llamadas_de_propuesta, c.validas_al_primer_intento) == (6, 6)
    # 1 ambiente, 1 fuente, 2 puntos y 2 recorridos
    assert (c.elementos_presentes, c.elementos_de_referencia) == (6, 6)
    assert c.costo_usd == Decimal(4)  # 2 fichas de entrada a 1 USD + 1 de salida a 2 USD
    assert c.veredicto.detectados == () and c.veredicto.falsas_alarmas == 0


def test_un_x_supuesto_5_cm_de_mas_es_un_e3_que_el_auditor_marca_por_el_supuesto():
    c = corrida(guion("1,55 m", x_supuesto=True))
    assert [(e.tipo, e.campo) for e in c.errores] == [("E3", "x")]
    # el supuesto declarado por la IA es un hallazgo de R8 NO esperado (la referencia no lo trae)
    # que cita la fila con el error: cuenta como deteccion (el auditor lo marco), sin falsa alarma
    assert len(c.veredicto.detectados) == 1 and c.veredicto.escapan == ()
    assert (c.veredicto.inesperados, c.veredicto.falsas_alarmas) == (1, 0)


def test_omitir_la_ducha_y_su_recorrido_son_dos_e6():
    c = corrida(guion(incluir_ducha=False))
    assert sorted((e.tipo, e.clase) for e in c.errores) == [("E6", "punto"), ("E6", "recorrido")]
    assert (c.elementos_presentes, c.elementos_de_referencia) == (4, 6)


def test_el_auditor_del_experimento_corre_exactamente_las_reglas_del_protocolo():
    import json
    from datetime import date

    from aplicacion.hoja import Borrador
    from asistente.experimento.congelado import PROTOCOLO
    from asistente.experimento.ejecucion import reglas_del_auditor

    protocolo = json.loads(PROTOCOLO.read_text(encoding="utf-8"))
    corridas = reglas_del_auditor(Borrador(fecha=date(2026, 10, 31)))
    assert list(corridas) == protocolo["reglas_del_experimento"]
