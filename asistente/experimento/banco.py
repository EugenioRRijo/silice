"""El banco de tareas de referencia (S4 §9.2): fichas versionadas, construidas y declaradas.

Los datos del repositorio son ficticios (NORMAS §1): las tareas tambien, y no pretenden representar
obras reales. Cada ficha (`tests/fixtures/asistente/tareas/<id>.json`) trae el PEDIDO, las
RESPUESTAS PREPARADAS (emparejadas por una regla automatica, §9.2), el borrador de partida y la
REFERENCIA escrita a mano antes de cualquier corrida. La referencia no sale de ninguna salida de un
modelo ni de la derivacion que se prueba (oraculo independiente).
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from adapters.espacio import (
    Circuito,
    Espacio,
    ModoRecorrido,
    Recorrido,
)
from asistente.experimento.modelo import Referencia, Sembrado
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from ui.hoja import Borrador, espacio_desde_filas

CARPETA_TAREAS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "asistente" / "tareas"
NO_SE = "no lo se"
ORIGEN_DE_REFERENCIA = {
    "id": "REF",
    "tipo": "levantamiento",
    "referencia": "fecha=2026-10-11; responsable=ficha de referencia",
}
BASES: dict[str, tuple[Circuito, ...]] = {
    "vacio": (),
    "circuito": (Circuito("C1", "T1", 1, (1, 1, 1), "12 AWG", 6),),
}


@dataclass(frozen=True, slots=True)
class Respuesta:
    palabras: tuple[str, ...]
    texto: str


@dataclass(frozen=True, slots=True)
class Ficha:
    id: str
    conjunto: str  # `desarrollo` | `evaluacion`
    especialidad: str
    pedido: str
    respuestas: tuple[Respuesta, ...]
    base: str
    posicion_libre: bool
    referencia: Mapping[str, Any]
    sembrados: tuple[Sembrado, ...]


def normalizar(texto: str) -> str:
    """Minusculas y sin tildes: como se normalizan las palabras clave y las preguntas."""
    sin = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in sin if unicodedata.category(c) != "Mn")


def ficha_desde_json(datos: Mapping[str, Any]) -> Ficha:
    return Ficha(
        id=datos["id"],
        conjunto=datos["conjunto"],
        especialidad=datos["especialidad"],
        pedido=datos["pedido"],
        respuestas=tuple(
            Respuesta(tuple(normalizar(p) for p in r["palabras"]), r["texto"])
            for r in datos["respuestas"]
        ),
        base=datos["base"],
        posicion_libre=datos["posicion_libre"],
        referencia=datos["referencia"],
        sembrados=tuple(
            Sembrado(s["clase"], s["id"], s["campo"], Decimal(s["valor"]))
            for s in datos.get("sembrados", [])
        ),
    )


def respuesta_preparada(ficha: Ficha, pregunta: str) -> str:
    """La primera respuesta, en el orden de la ficha, cuyas palabras clave aparecen TODAS en la
    pregunta; si ninguna cumple, «no lo se». El experimentador no elige ni redacta (PRU-H9)."""
    normal = normalizar(pregunta)
    for r in ficha.respuestas:
        if all(p in normal for p in r.palabras):
            return r.texto
    return NO_SE


def espacio_base(ficha: Ficha) -> Espacio:
    return Espacio(circuitos=BASES[ficha.base])


def borrador_de_partida(ficha: Ficha, fecha) -> Borrador:
    return Borrador(fecha=fecha, espacio=espacio_base(ficha))


def referencia_de(ficha: Ficha) -> Referencia:
    """La referencia como `Espacio` + partidas, construida por la misma puerta que la hoja."""
    r = ficha.referencia
    filas = {
        "origenes": [ORIGEN_DE_REFERENCIA],
        "ambientes": [{**a, "origen_id": "REF"} for a in r.get("ambientes", [])],
        "fuentes": [{**f, "origen_id": "REF"} for f in r.get("fuentes", [])],
        "puntos": [
            {"fuente_id": "", "circuito_id": "", "especificaciones": "", **p, "origen_id": "REF"}
            for p in r.get("puntos", [])
        ],
        "tramos": [],
    }
    espacio = espacio_desde_filas(filas, base=espacio_base(ficha))
    propuestos = tuple(
        Recorrido(id=f"R-{p.id}", modo=ModoRecorrido.PROPUESTO, punto_id=p.id)
        for p in espacio.puntos
    )
    espacio = replace(espacio, recorridos=propuestos)
    items = tuple(
        ItemComputo(
            p["codigo"],
            "referencia",
            p["unidad"],
            Decimal(p["cantidad"]),
            f"ref:{i}",
            OrigenTipo.MANUAL,
            Dominio(p.get("dominio", "civil")),
        )
        for i, p in enumerate(r.get("partidas", []), start=1)
    )
    return Referencia(espacio, items, ficha.posicion_libre, ficha.sembrados)


def cargar_banco(carpeta: Path = CARPETA_TAREAS) -> dict[str, Ficha]:
    return {
        ruta.stem: ficha_desde_json(json.loads(ruta.read_text(encoding="utf-8")))
        for ruta in sorted(carpeta.glob("*.json"))
    }


def bytes_normalizados(ruta: Path) -> bytes:
    """El contenido de `ruta` con saltos de linea LF: misma huella en Windows y en Linux."""
    return ruta.read_bytes().replace(b"\r\n", b"\n")


def huella_del_banco(carpeta: Path = CARPETA_TAREAS) -> str:
    """SHA-256 de los nombres y los bytes de las fichas, en orden: se congela en S4.0."""
    resumen = hashlib.sha256()
    for ruta in sorted(carpeta.glob("*.json")):
        resumen.update(ruta.name.encode())
        resumen.update(b"\0")
        resumen.update(bytes_normalizados(ruta))
        resumen.update(b"\0")
    return resumen.hexdigest()
