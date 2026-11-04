"""`POST /computos/{dominio}` con un CSV como lo guarda Excel en español (pulido F5, tanda 2).

Columnas separadas por punto y coma y cifras con coma decimal y punto de miles (la regla de
Eugenio). Las cuatro muestras de `data/samples/`, reescritas así, dan exactamente los mismos ítems
que las de siempre (separadas por coma, con punto decimal), que siguen leyéndose igual. Las
columnas numéricas de cada muestra están escritas aquí a mano, no salen del adaptador: si un
adaptador olvida declarar una, su muestra con coma decimal falla. Datos ficticios.
"""

from __future__ import annotations

import csv
import io
import json
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.cifras import MENSAJE_CIFRA
from tests.fixtures.computo_civil import CODIGOS as CODIGOS_CIVIL

MUESTRAS = Path(__file__).resolve().parents[2] / "data" / "samples"

#: dominio → (muestra, columnas con cifras), leídas de los README de `data/samples/<dominio>/`.
CASOS = {
    "civil": (
        "civil/tanquillas_y_zanja.csv",
        (
            "a",
            "h",
            "e",
            "n",
            "sobreancho",
            "espesor_fondo",
            "longitud",
            "ancho",
            "profundidad",
            "diametro",
            "desperdicio",
        ),
    ),
    "telecom": ("telecom/topologia_arenaza.csv", ("cantidad", "longitud_m", "reserva")),
    "industrial": ("industrial/activos_planta.csv", ("frecuencia_anual", "horizonte_anios")),
    "sistemas": (
        "sistemas/alcance_funcional.csv",
        ("entradas", "salidas", "consultas", "archivos", "interfaces"),
    ),
}


def _subir(cliente, dominio: str, nombre: str, contenido: bytes):
    datos = {"codigos": json.dumps(CODIGOS_CIVIL)} if dominio == "civil" else None
    return cliente.post(
        f"/computos/{dominio}", files={"archivo": (nombre, contenido, "text/csv")}, data=datos
    )


def _como_excel_en_espanol(muestra: str, numericas: tuple[str, ...]) -> bytes:
    """La muestra con `;` entre columnas y la coma como decimal. Las muestras no tienen cifras de
    miles; las de industrial y sistemas solo traen enteros: prueban el separador."""
    with (MUESTRAS / muestra).open(newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        columnas = list(lector.fieldnames or ())
        filas = list(lector)
    salida = io.StringIO(newline="")
    escritor = csv.DictWriter(salida, fieldnames=columnas, delimiter=";", lineterminator="\r\n")
    escritor.writeheader()
    for fila in filas:
        escritor.writerow(
            {c: (v.replace(".", ",") if c in numericas else v) for c, v in fila.items()}
        )
    return salida.getvalue().encode("utf-8-sig")


@pytest.mark.parametrize("dominio", sorted(CASOS))
def test_la_muestra_con_punto_y_coma_y_coma_decimal_da_los_mismos_items(cliente, dominio):
    muestra, numericas = CASOS[dominio]
    de_siempre = _subir(cliente, dominio, Path(muestra).name, (MUESTRAS / muestra).read_bytes())
    en_espanol = _subir(
        cliente, dominio, Path(muestra).name, _como_excel_en_espanol(muestra, numericas)
    )

    assert de_siempre.status_code == 200, de_siempre.text
    assert en_espanol.status_code == 200, en_espanol.text
    assert en_espanol.json() == de_siempre.json()


def test_con_punto_y_coma_el_punto_es_de_miles(cliente):
    """Oráculo a mano: un nodo de 1.200 piezas es 1200 y un enlace de 1.234,5 m con 0,1 de
    reserva, 1357,95 m."""
    contenido = (
        b"tipo;id;descripcion;codigo_partida;unidad;cantidad;origen;destino;longitud_m;reserva;especificaciones\n"
        b"nodo;AP-01;Punto de acceso ficticio;TI-AP;pieza;1.200;;;;;\n"
        b"enlace;L-01;Cable UTP ficticio;TI-UTP;m;;AP-01;AP-01;1.234,5;0,1;categoria=cat 6\n"
    )

    r = _subir(cliente, "telecom", "red.csv", contenido)

    assert r.status_code == 200, r.text
    cantidades = {i["origen_id"]: Decimal(i["cantidad"]) for i in r.json()}
    assert cantidades == {"AP-01": Decimal("1200"), "L-01": Decimal("1357.95")}


def test_con_punto_y_coma_un_punto_decimal_responde_422_con_archivo_fila_y_columna(cliente):
    contenido = (
        b"id_activo;descripcion;codigo_partida;unidad;frecuencia_anual;horizonte_anios\n"
        b"IN-9;Bomba;MNT-B;u;2.5;5\n"
    )

    r = _subir(cliente, "industrial", "activos.csv", contenido)

    assert r.status_code == 422
    detalle = r.json()["detalle"]
    assert "activos.csv" in detalle
    assert "fila 2" in detalle
    assert "frecuencia_anual" in detalle
    assert MENSAJE_CIFRA in detalle
