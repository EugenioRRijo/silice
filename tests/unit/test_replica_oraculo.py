"""Oráculo compartido de coordenadas, lado Python (Sílice 1.2.0, Task 2.6; RF-111, RS2-1).

El libro mínimo (`tests/fixtures/replica/libro_minimo.py`) tiene su salida esperada **escrita a
mano** en `libro_minimo.json`, deducida celda por celda de `ORACULO.md` (cómo se ve el libro en
Excel según ECMA-376), nunca de lo que devuelve `replicar_libro`. Aquí se comprueba que:

1. `replicar_libro` reproduce ese JSON, campo a campo con mensajes legibles;
2. la tabla de `ORACULO.md` y el JSON no divergen (cada fila de la tabla está en el JSON y el JSON
   no trae celdas, hojas ni estilos que la tabla no tenga).

Las pruebas de TypeScript de la 2.4 (`aUniver.test.ts`) leen el mismo JSON.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json

from adapters.hoja_empresa.visual import LibroVisual, replicar_libro
from tests.fixtures.replica.libro_minimo import NOMBRE, libro_minimo
from tests.fixtures.replica.oraculo import (
    cargar_json,
    diferencias,
    letras_de_columna,
    literal,
    tablas_oraculo,
)

CAMPOS_DE_ESTILO = (
    "relleno",
    "fuente",
    "tamano",
    "negrita",
    "cursiva",
    "subrayado",
    "color",
    "alineacion_h",
    "alineacion_v",
    "ajustar_texto",
    "formato_numero",
    "bordes",
)
CAMPOS_DE_HOJA = (
    "visible",
    "filas",
    "columnas",
    "anchos",
    "altos",
    "ocultas_filas",
    "ocultas_columnas",
    "combinadas",
    "fijas",
)


def _como_la_api(libro: LibroVisual) -> dict:
    """`LibroVisual` serializado como lo serializa la API: `dataclasses.asdict`, las tuplas son
    listas y las claves enteras de los mapas de anchos y altos pasan a texto (`{"2": "20"}`)."""
    return json.loads(json.dumps(dataclasses.asdict(libro)))


def test_visual_reproduce_el_oraculo_a_mano() -> None:
    datos = libro_minimo()
    obtenido = _como_la_api(replicar_libro(datos, NOMBRE))
    # El SHA-256 no se puede escribir a mano: se compara aparte, calculado de los bytes del libro.
    assert obtenido.pop("sha256") == hashlib.sha256(datos).hexdigest()
    esperado = cargar_json()
    assert "sha256" not in esperado
    dif = diferencias(esperado, obtenido)
    assert not dif, f"{len(dif)} diferencia(s) con el oráculo a mano:\n" + "\n".join(dif)


def test_el_libro_minimo_se_construye_igual_dos_veces() -> None:
    """El SHA-256 del libro es estable: sin esto la prueba de la API compararía contra otro hash."""
    assert libro_minimo() == libro_minimo()


def test_el_oraculo_y_su_tabla_coinciden() -> None:
    esperado = cargar_json()
    tablas = tablas_oraculo()
    assert set(tablas) == {"Hoja", "Celda", "Estilo"}

    # Hojas: mismas, en el mismo orden, con los mismos datos.
    filas_hoja = tablas["Hoja"]
    assert [literal(f["Hoja"]) for f in filas_hoja] == [h["nombre"] for h in esperado["hojas"]]
    por_nombre = {h["nombre"]: h for h in esperado["hojas"]}
    for f in filas_hoja:
        nombre = literal(f["Hoja"])
        for campo in CAMPOS_DE_HOJA:
            assert literal(f[campo]) == por_nombre[nombre][campo], (nombre, campo)

    # Celdas: cada fila de la tabla, y solo ellas, están en el JSON.
    en_tabla = set()
    for f in tablas["Celda"]:
        hoja, ref = literal(f["hoja"]), literal(f["ref"])
        fila, columna = literal(f["fila"]), literal(f["columna"])
        # La tabla es coherente consigo misma antes de compararla con el JSON.
        assert ref == f"{letras_de_columna(columna)}{fila}", (hoja, ref)
        assert f["Celda"] == f"{hoja}!{ref}"
        assert (literal(f["fila0"]), literal(f["columna0"])) == (fila - 1, columna - 1), (hoja, ref)
        celda = next(c for c in por_nombre[hoja]["celdas"] if c["ref"] == ref)
        assert (celda["fila"], celda["columna"]) == (fila, columna), (hoja, ref)
        assert celda["mostrado"] == literal(f["mostrado"]), (hoja, ref)
        assert celda["formula"] == literal(f["formula"]), (hoja, ref)
        assert celda["estilo"] == literal(f["estilo"]), (hoja, ref)
        en_tabla.add((hoja, ref))
    en_json = {(h["nombre"], c["ref"]) for h in esperado["hojas"] for c in h["celdas"]}
    assert en_tabla == en_json

    # Estilos: la tabla es la lista de estilos del JSON, en su orden.
    filas_estilo = tablas["Estilo"]
    assert [literal(f["Estilo"]) for f in filas_estilo] == list(range(len(esperado["estilos"])))
    for f in filas_estilo:
        indice = literal(f["Estilo"])
        for campo in CAMPOS_DE_ESTILO:
            assert literal(f[campo]) == esperado["estilos"][indice][campo], (indice, campo)
