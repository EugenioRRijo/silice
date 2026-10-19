"""Ayudas de lectura y comparación del oráculo del libro mínimo (Task 2.6).

Nada de aquí llama al código bajo prueba: lee `libro_minimo.json` y `ORACULO.md`, escritos a mano, y
compara estructuras ya serializadas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CARPETA = Path(__file__).parent
RUTA_JSON = CARPETA / "libro_minimo.json"
RUTA_ORACULO = CARPETA / "ORACULO.md"


def cargar_json() -> dict[str, Any]:
    """La respuesta esperada de `POST /v1/libros/replica`, escrita a mano (sin `sha256`)."""
    return json.loads(RUTA_JSON.read_text(encoding="utf-8"))


def _identidad(elemento: Any) -> str | None:
    """Con qué se nombra un elemento de lista en los mensajes: la hoja por su nombre, la celda por
    su referencia."""
    if isinstance(elemento, dict):
        for clave in ("nombre", "ref"):
            if isinstance(elemento.get(clave), str):
                return str(elemento[clave])
    return None


def diferencias(esperado: Any, obtenido: Any, ruta: str = "libro") -> list[str]:
    """Todas las diferencias campo a campo entre dos estructuras JSON, una línea por diferencia.

    Las hojas y las celdas se alinean por nombre y por referencia, no por posición, para que el
    mensaje diga `libro.hojas['PLAN DE PAGOS'].celdas['F12'].mostrado` y no un índice. El tipo
    cuenta: `true` no es `1`.
    """
    if isinstance(esperado, dict) and isinstance(obtenido, dict):
        out: list[str] = []
        for clave in sorted(set(esperado) | set(obtenido)):
            sub = f"{ruta}.{clave}"
            if clave not in obtenido:
                out.append(f"{sub}: falta en lo obtenido (esperado {esperado[clave]!r})")
            elif clave not in esperado:
                out.append(f"{sub}: sobra en lo obtenido ({obtenido[clave]!r})")
            else:
                out.extend(diferencias(esperado[clave], obtenido[clave], sub))
        return out
    if isinstance(esperado, list) and isinstance(obtenido, list):
        ids_e = [_identidad(x) for x in esperado]
        ids_o = [_identidad(x) for x in obtenido]
        if all(i is not None for i in ids_e + ids_o) and len(set(ids_e)) == len(ids_e):
            out = []
            if ids_e != ids_o:
                out.append(
                    f"{ruta}: el orden o el conjunto difiere: esperado {ids_e}, obtenido {ids_o}"
                )
            por_id = dict(zip(ids_o, obtenido, strict=True))
            for ident, elem in zip(ids_e, esperado, strict=True):
                sub = f"{ruta}[{ident!r}]"
                if ident not in por_id:
                    out.append(f"{sub}: falta en lo obtenido")
                else:
                    out.extend(diferencias(elem, por_id[ident], sub))
            return out
        out = []
        if len(esperado) != len(obtenido):
            out.append(f"{ruta}: largo esperado {len(esperado)}, obtenido {len(obtenido)}")
        for i, (e, o) in enumerate(zip(esperado, obtenido, strict=False)):
            out.extend(diferencias(e, o, f"{ruta}[{i}]"))
        return out
    if type(esperado) is not type(obtenido) or esperado != obtenido:
        return [f"{ruta}: esperado {esperado!r}, obtenido {obtenido!r}"]
    return []


# --- ORACULO.md ----------------------------------------------------------------------------------


def _fila_de_tabla(linea: str) -> list[str]:
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def tablas_oraculo() -> dict[str, list[dict[str, str]]]:
    """Las tablas de `ORACULO.md`, por el nombre de su primera columna (`Hoja`, `Celda`,
    `Estilo`): una lista de filas, cada una un diccionario encabezado → texto de la celda."""
    lineas = RUTA_ORACULO.read_text(encoding="utf-8").splitlines()
    tablas: dict[str, list[dict[str, str]]] = {}
    i = 0
    while i < len(lineas):
        if lineas[i].startswith("|") and i + 1 < len(lineas) and set(lineas[i + 1]) <= set("|-: "):
            encabezado = _fila_de_tabla(lineas[i])
            filas: list[dict[str, str]] = []
            i += 2
            while i < len(lineas) and lineas[i].startswith("|"):
                celdas = _fila_de_tabla(lineas[i])
                filas.append(dict(zip(encabezado, celdas, strict=True)))
                i += 1
            tablas[encabezado[0]] = filas
        else:
            i += 1
    return tablas


def literal(texto: str) -> Any:
    """Una celda de la tabla escrita como literal JSON entre comillas invertidas → su valor."""
    t = texto.strip()
    if not (t.startswith("`") and t.endswith("`")):
        raise ValueError(
            f"la celda de ORACULO.md no es un literal entre comillas invertidas: {texto!r}"
        )
    return json.loads(t[1:-1])


def letras_de_columna(n: int) -> str:
    """Columna base 1 → letras de Excel (1 → A, 27 → AA), calculado aquí a mano."""
    out = ""
    while n > 0:
        n, resto = divmod(n - 1, 26)
        out = chr(ord("A") + resto) + out
    return out
