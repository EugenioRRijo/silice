"""Persistencia propia del espacio: tablas `esp_*`, todas con la clave de versión (spec §6.2).

El adaptador no importa `core.models`: sus tablas viven en un `MetaData` propio y la clave de
versión (`version_id`) es el id de la versión del presupuesto, sin clave foránea para no acoplar los
esquemas. Toda dimensión se guarda como texto `Decimal` (SQLite perdería precisión con un
`NUMERIC`). Guardar una versión reemplaza lo que tuviera; el commit lo hace quien llama, para que
la hoja se guarde junto con el presupuesto en una sola transacción.
"""

from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Connection,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    delete,
    insert,
    inspect,
    select,
)
from sqlalchemy.orm import Session

from adapters.espacio.modelo import (
    Ambiente,
    Circuito,
    Coord,
    Espacio,
    Fuente,
    Punto,
    Recorrido,
    SobrescrituraSegmento,
    Tramo,
)
from adapters.espacio.origen import OrigenMedida

_metadata = MetaData()


def _tabla(nombre: str, *columnas: Column) -> Table:
    return Table(
        nombre,
        _metadata,
        Column("version_id", Integer, primary_key=True),
        *columnas,
    )


def _id() -> Column:
    return Column("id", String, primary_key=True)


esp_origenes = _tabla(
    "esp_origenes", _id(), Column("tipo", String, nullable=False), Column("referencia", Text)
)
esp_ambientes = _tabla(
    "esp_ambientes",
    _id(),
    Column("nombre", String, nullable=False),
    Column("x0", String, nullable=False),
    Column("y0", String, nullable=False),
    Column("largo", String, nullable=False),
    Column("ancho", String, nullable=False),
    Column("alto", String, nullable=False),
    Column("origen_id", String, nullable=False),
)
esp_fuentes = _tabla(
    "esp_fuentes",
    _id(),
    Column("especialidad", String, nullable=False),
    Column("tipo", String, nullable=False),
    Column("ambiente_id", String, nullable=False),
    Column("posicion", String, nullable=False),
    Column("origen_id", String, nullable=False),
)
esp_circuitos = _tabla(
    "esp_circuitos",
    _id(),
    Column("tablero", String, nullable=False),
    Column("numero", Integer, nullable=False),
    Column("conductores", String, nullable=False),
    Column("calibre", String, nullable=False),
    Column("puntos_maximos", Integer, nullable=False),
    Column("orden", Text, nullable=False),
)
esp_puntos = _tabla(
    "esp_puntos",
    _id(),
    Column("nombre", String, nullable=False),
    Column("especialidad", String, nullable=False),
    Column("tipo", String, nullable=False),
    Column("ambiente_id", String, nullable=False),
    Column("superficie", String, nullable=False),
    Column("posicion", String, nullable=False),
    Column("fuente_id", String),
    Column("circuito_id", String),
    Column("especificaciones", Text, nullable=False),
    Column("origen_id", String, nullable=False),
)
esp_recorridos = _tabla(
    "esp_recorridos",
    _id(),
    Column("punto_id", String),
    Column("circuito_id", String),
    Column("modo", String, nullable=False),
)
esp_tramos = _tabla(
    "esp_tramos",
    Column("recorrido_id", String, primary_key=True),
    Column("orden", Integer, primary_key=True),
    Column("superficie", String, nullable=False),
    Column("empotrado", Boolean),
    Column("vertices", Text, nullable=False),
    Column("pendiente", String),
    Column("longitud", String, nullable=False),
)
esp_sobrescrituras = _tabla(
    "esp_sobrescrituras",
    Column("clave", String, primary_key=True),
    Column("diametro", String),
    Column("empotrado", Boolean),
)

TABLAS = (
    esp_origenes,
    esp_ambientes,
    esp_fuentes,
    esp_circuitos,
    esp_puntos,
    esp_recorridos,
    esp_tramos,
    esp_sobrescrituras,
)


def crear_esquema_espacio(destino: Engine | Connection) -> None:
    """Crea las tablas `esp_*` que falten. Idempotente; no toca las demás tablas de la base.

    `destino` es el motor o, para guardar una version y sus filas en UNA sola sesion (SF3), la
    conexion de esa sesion (`sesion.connection()`): una segunda conexion no puede crear tablas
    mientras la sesion ya escribio."""
    _metadata.create_all(destino)


def _coord_a_texto(c: Coord) -> str:
    return f"{c.x},{c.y},{c.z}"


def _coord_de_texto(texto: str) -> Coord:
    x, y, z = (Decimal(v) for v in texto.split(","))
    return Coord(x, y, z)


def _vertices_a_texto(vertices: tuple[Coord, ...]) -> str:
    return ";".join(_coord_a_texto(v) for v in vertices)


def _vertices_de_texto(texto: str) -> tuple[Coord, ...]:
    return tuple(_coord_de_texto(v) for v in texto.split(";"))


def _texto_o_none(valor: Decimal | None) -> str | None:
    return None if valor is None else str(valor)


def guardar_espacio(sesion: Session, version_id: int, espacio: Espacio) -> None:
    """Guarda el espacio de una versión, reemplazando el que tuviera. No hace commit."""
    for tabla in TABLAS:
        sesion.execute(delete(tabla).where(tabla.c.version_id == version_id))

    def poner(tabla: Table, filas: list[dict]) -> None:
        if filas:
            sesion.execute(insert(tabla), [{"version_id": version_id, **f} for f in filas])

    poner(
        esp_origenes,
        [
            {"id": o.id, "tipo": o.tipo.value, "referencia": json.dumps(dict(o.referencia))}
            for o in espacio.origenes
        ],
    )
    poner(
        esp_ambientes,
        [
            {
                "id": a.id,
                "nombre": a.nombre,
                "x0": str(a.x0),
                "y0": str(a.y0),
                "largo": str(a.largo),
                "ancho": str(a.ancho),
                "alto": str(a.alto),
                "origen_id": a.origen_id,
            }
            for a in espacio.ambientes
        ],
    )
    poner(
        esp_fuentes,
        [
            {
                "id": f.id,
                "especialidad": f.especialidad.value,
                "tipo": f.tipo.value,
                "ambiente_id": f.ambiente_id,
                "posicion": _coord_a_texto(f.posicion),
                "origen_id": f.origen_id,
            }
            for f in espacio.fuentes
        ],
    )
    poner(
        esp_circuitos,
        [
            {
                "id": c.id,
                "tablero": c.tablero,
                "numero": c.numero,
                "conductores": json.dumps(list(c.conductores)),
                "calibre": c.calibre,
                "puntos_maximos": c.puntos_maximos,
                "orden": json.dumps(list(c.orden)),
            }
            for c in espacio.circuitos
        ],
    )
    poner(
        esp_puntos,
        [
            {
                "id": p.id,
                "nombre": p.nombre,
                "especialidad": p.especialidad.value,
                "tipo": p.tipo.value,
                "ambiente_id": p.ambiente_id,
                "superficie": p.superficie.value,
                "posicion": _coord_a_texto(p.posicion),
                "fuente_id": p.fuente_id,
                "circuito_id": p.circuito_id,
                "especificaciones": json.dumps(dict(p.especificaciones)),
                "origen_id": p.origen_id,
            }
            for p in espacio.puntos
        ],
    )
    poner(
        esp_recorridos,
        [
            {"id": r.id, "punto_id": r.punto_id, "circuito_id": r.circuito_id, "modo": r.modo.value}
            for r in espacio.recorridos
        ],
    )
    poner(
        esp_tramos,
        [
            {
                "recorrido_id": r.id,
                "orden": t.orden,
                "superficie": t.superficie.value,
                "empotrado": t.empotrado,
                "vertices": _vertices_a_texto(t.vertices),
                "pendiente": _texto_o_none(t.pendiente),
                "longitud": str(t.longitud),
            }
            for r in espacio.recorridos
            for t in r.tramos
        ],
    )
    poner(
        esp_sobrescrituras,
        [
            {"clave": s.clave, "diametro": s.diametro, "empotrado": s.empotrado}
            for s in espacio.sobrescrituras
        ],
    )


def cargar_espacio(sesion: Session, version_id: int) -> Espacio:
    """El espacio guardado de una versión; vacío si no tiene (FR-1).

    Si la base no tiene (todas) las tablas `esp_*` (una clínica o TI-001 anteriores a la hoja,
    FR-5) devuelve el espacio vacío sin crearlas ni escribir. Quien guarde debe llamar antes a
    `crear_esquema_espacio`.
    """
    tablas = set(inspect(sesion.connection()).get_table_names())
    if not {t.name for t in TABLAS} <= tablas:
        return Espacio()

    def filas(tabla: Table):
        return sesion.execute(select(tabla).where(tabla.c.version_id == version_id)).mappings()

    tramos: dict[str, list[Tramo]] = {}
    for t in filas(esp_tramos):
        tramos.setdefault(t["recorrido_id"], []).append(
            Tramo(
                orden=t["orden"],
                superficie=t["superficie"],
                empotrado=t["empotrado"],
                vertices=_vertices_de_texto(t["vertices"]),
                pendiente=None if t["pendiente"] is None else Decimal(t["pendiente"]),
            )
        )
    return Espacio(
        origenes=tuple(
            OrigenMedida(id=o["id"], tipo=o["tipo"], referencia=json.loads(o["referencia"]))
            for o in filas(esp_origenes)
        ),
        ambientes=tuple(
            Ambiente(
                id=a["id"],
                nombre=a["nombre"],
                x0=Decimal(a["x0"]),
                y0=Decimal(a["y0"]),
                largo=Decimal(a["largo"]),
                ancho=Decimal(a["ancho"]),
                alto=Decimal(a["alto"]),
                origen_id=a["origen_id"],
            )
            for a in filas(esp_ambientes)
        ),
        fuentes=tuple(
            Fuente(
                id=f["id"],
                especialidad=f["especialidad"],
                tipo=f["tipo"],
                ambiente_id=f["ambiente_id"],
                posicion=_coord_de_texto(f["posicion"]),
                origen_id=f["origen_id"],
            )
            for f in filas(esp_fuentes)
        ),
        circuitos=tuple(
            Circuito(
                id=c["id"],
                tablero=c["tablero"],
                numero=c["numero"],
                conductores=tuple(json.loads(c["conductores"])),
                calibre=c["calibre"],
                puntos_maximos=c["puntos_maximos"],
                orden=tuple(json.loads(c["orden"])),
            )
            for c in filas(esp_circuitos)
        ),
        puntos=tuple(
            Punto(
                id=p["id"],
                nombre=p["nombre"],
                especialidad=p["especialidad"],
                tipo=p["tipo"],
                ambiente_id=p["ambiente_id"],
                superficie=p["superficie"],
                posicion=_coord_de_texto(p["posicion"]),
                fuente_id=p["fuente_id"],
                circuito_id=p["circuito_id"],
                especificaciones=json.loads(p["especificaciones"]),
                origen_id=p["origen_id"],
            )
            for p in filas(esp_puntos)
        ),
        recorridos=tuple(
            Recorrido(
                id=r["id"],
                punto_id=r["punto_id"],
                circuito_id=r["circuito_id"],
                modo=r["modo"],
                tramos=tuple(tramos.get(r["id"], ())),
            )
            for r in filas(esp_recorridos)
        ),
        sobrescrituras=tuple(
            SobrescrituraSegmento(
                clave=s["clave"], diametro=s["diametro"], empotrado=s["empotrado"]
            )
            for s in filas(esp_sobrescrituras)
        ),
    )
