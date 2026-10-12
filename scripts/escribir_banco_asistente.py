"""Escribe las 16 fichas del banco de tareas del asistente (S4 §9.2).

Van a tests/fixtures/asistente/tareas.

Las fichas SON la memoria de calculo: la referencia (ambientes, fuentes, puntos, partidas) esta
escrita a mano aqui, con las cifras que el PEDIDO da literalmente, antes de cualquier corrida. Este
script solo las pasa a JSON; despues de congelarlas (huella SHA-256 en el protocolo) no se vuelve a
correr. Los datos son construidos y declarados (NORMAS §1): no representan obras reales.

Convenciones del pedido: metros; esquina del primer ambiente en el origen salvo que la ficha sea de
POSICION LIBRE; pared sur y = 0, pared norte y = ancho, pared oeste x = 0, pared este x = largo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "tests" / "fixtures" / "asistente" / "tareas"


def amb(id_, nombre, largo, ancho, alto="2.5", x0="0", y0="0"):
    return {
        "id": id_,
        "nombre": nombre,
        "x0": x0,
        "y0": y0,
        "largo": largo,
        "ancho": ancho,
        "alto": alto,
    }


def fte(id_, esp, tipo, amb_id, x, y, z):
    return {
        "id": id_,
        "especialidad": esp,
        "tipo": tipo,
        "ambiente_id": amb_id,
        "x": x,
        "y": y,
        "z": z,
    }


def pto(id_, nombre, esp, tipo, amb_id, sup, x, y, z, fuente="", circuito="", espec=""):
    return {
        "id": id_,
        "nombre": nombre,
        "especialidad": esp,
        "tipo": tipo,
        "ambiente_id": amb_id,
        "superficie": sup,
        "x": x,
        "y": y,
        "z": z,
        "fuente_id": fuente,
        "circuito_id": circuito,
        "especificaciones": espec,
    }


def ficha(
    id_, conjunto, esp, pedido, respuestas, referencia, *, base="vacio", libre=False, sembrados=()
):
    return {
        "id": id_,
        "conjunto": conjunto,
        "especialidad": esp,
        "pedido": pedido,
        "respuestas": [{"palabras": p, "texto": t} for p, t in respuestas],
        "base": base,
        "posicion_libre": libre,
        "referencia": referencia,
        "sembrados": list(sembrados),
    }


AGUA = "agua"
DAT = "datos"
ELE = "electricidad"
LLAVE = 'diametro=1/2"; llave_de_paso=si'


def fichas() -> dict[str, dict]:
    f: dict[str, dict] = {}

    # ---------------- desarrollo (4) ----------------
    f["dev-agua-01"] = ficha(
        "dev-agua-01",
        "desarrollo",
        AGUA,
        "Bano de 2,0 x 1,5 m con alto de 2,5 m, esquina en el origen (0;0). Montante de agua en "
        "la esquina (0;0;0). Lavamanos en la pared sur: x = 1,5 m, y = 0 m, a 60 cm del piso, "
        'diametro 1/2" con llave de paso. Ducha en la pared norte: x = 1,0 m, y = 1,5 m, a 1,2 m '
        'del piso, diametro 3/4" con llave de paso.',
        [(["alto"], "2,5 m"), (["diametro"], "Los diametros estan en el pedido")],
        {
            "ambientes": [amb("A1", "Bano", "2", "1.5")],
            "fuentes": [fte("F1", AGUA, "montante_agua", "A1", "0", "0", "0")],
            "puntos": [
                pto(
                    "P1",
                    "lavamanos",
                    AGUA,
                    "agua_fria",
                    "A1",
                    "pared",
                    "1.5",
                    "0",
                    "0.6",
                    "F1",
                    espec=LLAVE,
                ),
                pto(
                    "P2",
                    "ducha",
                    AGUA,
                    "agua_fria",
                    "A1",
                    "pared",
                    "1",
                    "1.5",
                    "1.2",
                    "F1",
                    espec='diametro=3/4"; llave_de_paso=si',
                ),
            ],
        },
    )
    f["dev-datos-01"] = ficha(
        "dev-datos-01",
        "desarrollo",
        DAT,
        "Oficina de 4,0 x 3,0 m con alto de 2,5 m, esquina en el origen. Rack en la esquina "
        "(0;0;0). Dos puntos de datos en la pared sur: x = 3,0 m, y = 0 m, z = 0,3 m; y en la "
        "pared este: x = 4,0 m, y = 2,0 m, z = 0,3 m.",
        [(["categoria"], "Categoria 6")],
        {
            "ambientes": [amb("A1", "Oficina", "4", "3")],
            "fuentes": [fte("RK1", DAT, "rack", "A1", "0", "0", "0")],
            "puntos": [
                pto("D1", "dato 1", DAT, "datos", "A1", "pared", "3", "0", "0.3", "RK1"),
                pto("D2", "dato 2", DAT, "datos", "A1", "pared", "4", "2", "0.3", "RK1"),
            ],
        },
    )
    f["dev-elec-01"] = ficha(
        "dev-elec-01",
        "desarrollo",
        ELE,
        "Sala de 5,0 x 4,0 m con alto de 2,5 m, esquina en el origen. Tablero T1 en la pared "
        "oeste: x = 0 m, y = 0 m, z = 1,2 m. Circuito C1 ya existe. Tomacorrientes del circuito C1 "
        "en la pared sur: x = 1,0 m, y = 0 m, z = 0,3 m; y x = 3,0 m, y = 0 m, z = 0,3 m. "
        "Luminaria del circuito C1 en el techo: x = 2,5 m, y = 2,0 m, z = 2,5 m.",
        [(["circuito"], "C1")],
        {
            "ambientes": [amb("A1", "Sala", "5", "4")],
            "fuentes": [fte("T1", ELE, "tablero", "A1", "0", "0", "1.2")],
            "puntos": [
                pto(
                    "E1", "toma 1", ELE, "tomacorriente", "A1", "pared", "1", "0", "0.3", "T1", "C1"
                ),
                pto(
                    "E2", "toma 2", ELE, "tomacorriente", "A1", "pared", "3", "0", "0.3", "T1", "C1"
                ),
                pto(
                    "L1", "luz 1", ELE, "iluminacion", "A1", "techo", "2.5", "2", "2.5", "T1", "C1"
                ),
            ],
        },
        base="circuito",
    )
    f["dev-mixta-01"] = ficha(
        "dev-mixta-01",
        "desarrollo",
        DAT,
        "Cuarto de equipos de 3,0 x 3,0 m con alto de 2,5 m, esquina en el origen. Rack en la "
        "esquina (0;0;0). Un punto de datos en la pared sur: x = 2,0 m, y = 0 m, z = 0,3 m. "
        "Ademas: 1 UPS y 1 switch para el rack.",
        [(["cuantos", "ups"], "Una UPS"), (["switch"], "Un switch")],
        {
            "ambientes": [amb("A1", "Equipos", "3", "3")],
            "fuentes": [fte("RK1", DAT, "rack", "A1", "0", "0", "0")],
            "puntos": [pto("D1", "dato 1", DAT, "datos", "A1", "pared", "2", "0", "0.3", "RK1")],
            "partidas": [
                {"codigo": "TI-UPS", "unidad": "pieza", "cantidad": "1", "dominio": "telecom"},
                {"codigo": "TI-SW", "unidad": "pieza", "cantidad": "1", "dominio": "telecom"},
            ],
        },
    )

    # ---------------- evaluacion: agua (4) ----------------
    f["ev-agua-01"] = ficha(
        "ev-agua-01",
        "evaluacion",
        AGUA,
        "Bano de 2,4 x 1,5 m con alto de 2,5 m, esquina en el origen. Montante de agua en (0;0;0). "
        'Lavamanos en la pared sur: x = 1,2 m, y = 0 m, a 55 cm del piso, diametro 1/2" con llave '
        'de paso. Poceta en la pared sur: x = 2,0 m, y = 0 m, a 25 cm del piso, diametro 1/2" '
        "con llave de paso.",
        [(["alto"], "2,5 m")],
        {
            "ambientes": [amb("A1", "Bano", "2.4", "1.5")],
            "fuentes": [fte("F1", AGUA, "montante_agua", "A1", "0", "0", "0")],
            "puntos": [
                pto(
                    "P1",
                    "lavamanos",
                    AGUA,
                    "agua_fria",
                    "A1",
                    "pared",
                    "1.2",
                    "0",
                    "0.55",
                    "F1",
                    espec=LLAVE,
                ),
                pto(
                    "P2",
                    "poceta",
                    AGUA,
                    "agua_fria",
                    "A1",
                    "pared",
                    "2",
                    "0",
                    "0.25",
                    "F1",
                    espec=LLAVE,
                ),
            ],
        },
    )
    f["ev-agua-02"] = ficha(
        "ev-agua-02",
        "evaluacion",
        AGUA,
        "Cocina de 3,0 x 2,0 m con alto de 2,5 m, esquina en el origen. Montante de agua en "
        "(0;2,0;0). Fregadero en la pared norte: x = 1,5 m, y = 2,0 m, a 90 cm del piso, "
        'diametro 1/2" con llave de paso. Lavadora en la pared este: x = 3,0 m, y = 1,0 m, a 1,0 m '
        'del piso, diametro 1/2" con llave de paso.',
        [(["diametro"], "1/2 pulgada")],
        {
            "ambientes": [amb("A1", "Cocina", "3", "2")],
            "fuentes": [fte("F1", AGUA, "montante_agua", "A1", "0", "2", "0")],
            "puntos": [
                pto(
                    "P1",
                    "fregadero",
                    AGUA,
                    "agua_fria",
                    "A1",
                    "pared",
                    "1.5",
                    "2",
                    "0.9",
                    "F1",
                    espec=LLAVE,
                ),
                pto(
                    "P2",
                    "lavadora",
                    AGUA,
                    "agua_fria",
                    "A1",
                    "pared",
                    "3",
                    "1",
                    "1",
                    "F1",
                    espec=LLAVE,
                ),
            ],
        },
    )
    f["ev-agua-03"] = ficha(
        "ev-agua-03",
        "evaluacion",
        AGUA,
        "Lavanderia de 2,0 x 2,0 m con alto de 2,5 m (la posicion en el plano es libre: ponga la "
        "esquina donde quiera). Montante de agua en la esquina del ambiente a nivel del piso. "
        'Lavadero en la pared norte, en el centro del ambiente, a 85 cm del piso, 1/2" con llave '
        'de paso. Lavadora en la pared este, en el centro del ambiente, a 1,0 m del piso, 1/2" '
        "con llave de paso.",
        [(["esquina"], "Cualquiera; use la esquina inferior izquierda en (0;0)")],
        {
            "ambientes": [amb("A1", "Lavanderia", "2", "2")],
            "fuentes": [fte("F1", AGUA, "montante_agua", "A1", "0", "0", "0")],
            "puntos": [
                pto(
                    "P1",
                    "lavadero",
                    AGUA,
                    "agua_fria",
                    "A1",
                    "pared",
                    "1",
                    "2",
                    "0.85",
                    "F1",
                    espec=LLAVE,
                ),
                pto(
                    "P2",
                    "lavadora",
                    AGUA,
                    "agua_fria",
                    "A1",
                    "pared",
                    "2",
                    "1",
                    "1",
                    "F1",
                    espec=LLAVE,
                ),
            ],
        },
        libre=True,
    )
    f["ev-agua-04"] = ficha(
        "ev-agua-04",
        "evaluacion",
        AGUA,
        "Bano de 2,4 x 1,5 m con alto de 2,5 m, esquina en el origen. Montante de agua en (0;0;0). "
        'Lavamanos en la pared sur: x = 3,00 m, y = 0 m, a 60 cm del piso, diametro 1/2" con llave '
        'de paso. Ducha en la pared norte: x = 1,0 m, y = 1,5 m, a 1,2 m del piso, 3/4" con llave '
        "de paso.",
        [(["lavamanos", "x"], "2,0 m"), (["largo"], "2,4 m"), (["medida"], "2,0 m")],
        {
            "ambientes": [amb("A1", "Bano", "2.4", "1.5")],
            "fuentes": [fte("F1", AGUA, "montante_agua", "A1", "0", "0", "0")],
            "puntos": [
                pto(
                    "P1",
                    "lavamanos",
                    AGUA,
                    "agua_fria",
                    "A1",
                    "pared",
                    "2",
                    "0",
                    "0.6",
                    "F1",
                    espec=LLAVE,
                ),
                pto(
                    "P2",
                    "ducha",
                    AGUA,
                    "agua_fria",
                    "A1",
                    "pared",
                    "1",
                    "1.5",
                    "1.2",
                    "F1",
                    espec='diametro=3/4"; llave_de_paso=si',
                ),
            ],
        },
        sembrados=[{"clase": "punto", "id": "P1", "campo": "x", "valor": "3.00"}],
    )

    # ---------------- evaluacion: datos (3) ----------------
    f["ev-datos-01"] = ficha(
        "ev-datos-01",
        "evaluacion",
        DAT,
        "Oficina de 5,0 x 4,0 m con alto de 2,5 m, esquina en el origen. Rack en (0;0;0). Tres "
        "puntos de datos a 30 cm del piso: x = 1,0 y = 0; x = 3,0 y = 0; x = 5,0 y = 2,0.",
        [(["altura"], "30 cm")],
        {
            "ambientes": [amb("A1", "Oficina", "5", "4")],
            "fuentes": [fte("RK1", DAT, "rack", "A1", "0", "0", "0")],
            "puntos": [
                pto("D1", "dato 1", DAT, "datos", "A1", "pared", "1", "0", "0.3", "RK1"),
                pto("D2", "dato 2", DAT, "datos", "A1", "pared", "3", "0", "0.3", "RK1"),
                pto("D3", "dato 3", DAT, "datos", "A1", "pared", "5", "2", "0.3", "RK1"),
            ],
        },
    )
    f["ev-datos-02"] = ficha(
        "ev-datos-02",
        "evaluacion",
        DAT,
        "Sala de 6,0 x 3,0 m con alto de 2,5 m (posicion libre en el plano). Rack en la esquina "
        "del ambiente a nivel del piso. Cuatro puntos de datos a 30 cm del piso en la pared sur: "
        "a 1,0 m, 2,5 m, 4,0 m y 5,5 m de la esquina donde esta el rack.",
        [(["esquina"], "Use la esquina inferior izquierda en (0;0)")],
        {
            "ambientes": [amb("A1", "Sala", "6", "3")],
            "fuentes": [fte("RK1", DAT, "rack", "A1", "0", "0", "0")],
            "puntos": [
                pto("D1", "dato 1", DAT, "datos", "A1", "pared", "1", "0", "0.3", "RK1"),
                pto("D2", "dato 2", DAT, "datos", "A1", "pared", "2.5", "0", "0.3", "RK1"),
                pto("D3", "dato 3", DAT, "datos", "A1", "pared", "4", "0", "0.3", "RK1"),
                pto("D4", "dato 4", DAT, "datos", "A1", "pared", "5.5", "0", "0.3", "RK1"),
            ],
        },
        libre=True,
    )
    f["ev-datos-03"] = ficha(
        "ev-datos-03",
        "evaluacion",
        DAT,
        "Oficina de 4,0 x 0,0 m con alto de 2,5 m, esquina en el origen. Rack en (0;0;0). Dos "
        "puntos de datos a 30 cm del piso en la pared sur: x = 1,0 m y x = 3,0 m (y = 0).",
        [(["ancho"], "1,5 m"), (["medida"], "1,5 m")],
        {
            "ambientes": [amb("A1", "Oficina", "4", "1.5")],
            "fuentes": [fte("RK1", DAT, "rack", "A1", "0", "0", "0")],
            "puntos": [
                pto("D1", "dato 1", DAT, "datos", "A1", "pared", "1", "0", "0.3", "RK1"),
                pto("D2", "dato 2", DAT, "datos", "A1", "pared", "3", "0", "0.3", "RK1"),
            ],
        },
        sembrados=[{"clase": "ambiente", "id": "A1", "campo": "ancho", "valor": "0"}],
    )

    # ---------------- evaluacion: electricidad (3) ----------------
    f["ev-elec-01"] = ficha(
        "ev-elec-01",
        "evaluacion",
        ELE,
        "Sala de 5,0 x 4,0 m con alto de 2,5 m, esquina en el origen. Tablero T1 en (0;0;1,2). "
        "Circuito C1 ya existe. Tres tomacorrientes del circuito C1 a 30 cm del piso: "
        "x = 1,0 y = 0; x = 3,0 y = 0; x = 5,0 y = 2,0. "
        "Una luminaria del circuito C1 en el techo: x = 2,5 y = 2,0.",
        [(["circuito"], "C1")],
        {
            "ambientes": [amb("A1", "Sala", "5", "4")],
            "fuentes": [fte("T1", ELE, "tablero", "A1", "0", "0", "1.2")],
            "puntos": [
                pto(
                    "E1", "toma 1", ELE, "tomacorriente", "A1", "pared", "1", "0", "0.3", "T1", "C1"
                ),
                pto(
                    "E2", "toma 2", ELE, "tomacorriente", "A1", "pared", "3", "0", "0.3", "T1", "C1"
                ),
                pto(
                    "E3", "toma 3", ELE, "tomacorriente", "A1", "pared", "5", "2", "0.3", "T1", "C1"
                ),
                pto(
                    "L1", "luz 1", ELE, "iluminacion", "A1", "techo", "2.5", "2", "2.5", "T1", "C1"
                ),
            ],
        },
        base="circuito",
    )
    f["ev-elec-02"] = ficha(
        "ev-elec-02",
        "evaluacion",
        ELE,
        "Taller de 6,0 x 5,0 m con alto de 3,0 m, esquina en el origen. Tablero T1 en (0;0;1,2). "
        "Circuito C1 ya existe. Cuatro tomacorrientes del circuito C1 a 1,0 m del piso en la pared "
        "sur: x = 1,0; 2,5; 4,0; 5,5 (y = 0). Dos luminarias del circuito C1 en el techo: "
        "(2,0;2,5;3,0) y (4,0;2,5;3,0).",
        [(["alto"], "3,0 m")],
        {
            "ambientes": [amb("A1", "Taller", "6", "5", "3")],
            "fuentes": [fte("T1", ELE, "tablero", "A1", "0", "0", "1.2")],
            "puntos": [
                pto("E1", "toma 1", ELE, "tomacorriente", "A1", "pared", "1", "0", "1", "T1", "C1"),
                pto(
                    "E2", "toma 2", ELE, "tomacorriente", "A1", "pared", "2.5", "0", "1", "T1", "C1"
                ),
                pto("E3", "toma 3", ELE, "tomacorriente", "A1", "pared", "4", "0", "1", "T1", "C1"),
                pto(
                    "E4", "toma 4", ELE, "tomacorriente", "A1", "pared", "5.5", "0", "1", "T1", "C1"
                ),
                pto("L1", "luz 1", ELE, "iluminacion", "A1", "techo", "2", "2.5", "3", "T1", "C1"),
                pto("L2", "luz 2", ELE, "iluminacion", "A1", "techo", "4", "2.5", "3", "T1", "C1"),
            ],
        },
        base="circuito",
    )
    f["ev-elec-03"] = ficha(
        "ev-elec-03",
        "evaluacion",
        ELE,
        "Sala de 5,0 x 4,0 m con alto de 2,5 m, esquina en el origen. Tablero T1 en (0;0;1,2). "
        "Circuito C1 ya existe. Dos tomacorrientes del circuito C1 a 30 cm del piso: "
        "x = 1,0 y = 0; "
        "y una toma en el pasillo: x = 3,0 m, y = 6,0 m (a 30 cm del piso).",
        [
            (["pasillo"], "No hay pasillo; la toma va en la pared norte, y = 4,0 m"),
            (["medida"], "y = 4,0 m"),
        ],
        {
            "ambientes": [amb("A1", "Sala", "5", "4")],
            "fuentes": [fte("T1", ELE, "tablero", "A1", "0", "0", "1.2")],
            "puntos": [
                pto(
                    "E1", "toma 1", ELE, "tomacorriente", "A1", "pared", "1", "0", "0.3", "T1", "C1"
                ),
                pto(
                    "E2",
                    "toma pasillo",
                    ELE,
                    "tomacorriente",
                    "A1",
                    "pared",
                    "3",
                    "4",
                    "0.3",
                    "T1",
                    "C1",
                ),
            ],
        },
        base="circuito",
        sembrados=[{"clase": "punto", "id": "E2", "campo": "y", "valor": "6.0"}],
    )

    # ---------------- evaluacion: mixtas (2) ----------------
    f["ev-mixta-01"] = ficha(
        "ev-mixta-01",
        "evaluacion",
        DAT,
        "Sala de servidores de 4,0 x 3,0 m con alto de 2,5 m, esquina en el origen. Rack en "
        "(0;0;0). Dos puntos de datos a 30 cm del piso: x = 2,0 y = 0; x = 4,0 y = 1,5. Ademas: "
        "1 UPS y 1 switch para el rack.",
        [(["ups"], "Una UPS"), (["switch"], "Un switch")],
        {
            "ambientes": [amb("A1", "Servidores", "4", "3")],
            "fuentes": [fte("RK1", DAT, "rack", "A1", "0", "0", "0")],
            "puntos": [
                pto("D1", "dato 1", DAT, "datos", "A1", "pared", "2", "0", "0.3", "RK1"),
                pto("D2", "dato 2", DAT, "datos", "A1", "pared", "4", "1.5", "0.3", "RK1"),
            ],
            "partidas": [
                {"codigo": "TI-UPS", "unidad": "pieza", "cantidad": "1", "dominio": "telecom"},
                {"codigo": "TI-SW", "unidad": "pieza", "cantidad": "1", "dominio": "telecom"},
            ],
        },
    )
    f["ev-mixta-02"] = ficha(
        "ev-mixta-02",
        "evaluacion",
        DAT,
        "Oficina de 5,0 x 4,0 m con alto de 2,5 m, esquina en el origen. Rack en (0;0;0). Tres "
        "puntos de datos a 30 cm del piso: x = 1,0 y = 0; x = 3,0 y = 0; x = 5,0 y = 2,0. Ademas: "
        "1 UPS y 3 laptops.",
        [(["laptops"], "Tres laptops"), (["ups"], "Una UPS")],
        {
            "ambientes": [amb("A1", "Oficina", "5", "4")],
            "fuentes": [fte("RK1", DAT, "rack", "A1", "0", "0", "0")],
            "puntos": [
                pto("D1", "dato 1", DAT, "datos", "A1", "pared", "1", "0", "0.3", "RK1"),
                pto("D2", "dato 2", DAT, "datos", "A1", "pared", "3", "0", "0.3", "RK1"),
                pto("D3", "dato 3", DAT, "datos", "A1", "pared", "5", "2", "0.3", "RK1"),
            ],
            "partidas": [
                {"codigo": "TI-UPS", "unidad": "pieza", "cantidad": "1", "dominio": "telecom"},
                {"codigo": "TI-LAP", "unidad": "pieza", "cantidad": "3", "dominio": "telecom"},
            ],
        },
    )
    return f


def main(argv: list[str] | None = None) -> int:
    CARPETA.mkdir(parents=True, exist_ok=True)
    for nombre, datos in fichas().items():
        texto = json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        (CARPETA / f"{nombre}.json").write_bytes(texto.encode("utf-8"))  # LF en todo sistema
    print(f"{len(fichas())} fichas en {CARPETA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
