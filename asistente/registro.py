"""Registro `ia_*` de cada sesion del asistente y el anexo `anexos/ia.json` (S4 §5.5, RF-93).

Tablas aditivas propias en la base del CASO, sin clave foranea a `core/models` (como `esp_*`).
La revision de Alembic que las crea (`migraciones/caso/versions/`) se escribe a mano con las
mismas columnas; la prueba de deriva de RNF-20 las compara. NUNCA se guarda la clave de IA de la
empresa ni encabezados de la solicitud (RNF-18 c). El anexo para el paquete no lleva uso de fichas
ni costo (RV-19, P4 ratificada por Eugenio el 2026-10-11).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Connection, Engine

METADATA_IA = MetaData()

ia_sesiones = Table(
    "ia_sesiones",
    METADATA_IA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("proyecto", String(120), nullable=False),
    Column("version_partida", String(20), nullable=False),
    Column("version_guardada", String(20)),
    Column("proveedor", String(40), nullable=False),
    Column("modelo_pedido", String(80), nullable=False),
    Column("pedido", Text, nullable=False),
    Column("topes", Text, nullable=False),
    Column("inicio", DateTime, nullable=False),
    Column("fin", DateTime),
    Column("motivo_fin", String(40)),
)
ia_turnos = Table(
    "ia_turnos",
    METADATA_IA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sesion_id", Integer, ForeignKey("ia_sesiones.id"), nullable=False),
    Column("orden", Integer, nullable=False),
    Column("modelo_respondio", String(80), nullable=False),
    Column("fin", String(20), nullable=False),
    Column("entrada", Integer, nullable=False),
    Column("salida", Integer, nullable=False),
    Column("cache_lectura", Integer, nullable=False),
    Column("cache_escritura", Integer, nullable=False),
    Column("costo", String(40), nullable=False),
    Column("texto", Text, nullable=False),
)
ia_llamadas = Table(
    "ia_llamadas",
    METADATA_IA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sesion_id", Integer, ForeignKey("ia_sesiones.id"), nullable=False),
    Column("turno", Integer, nullable=False),
    Column("herramienta", String(40), nullable=False),
    Column("argumentos", Text, nullable=False),
    Column("resultado", String(40), nullable=False),
    Column("motivo", Text, nullable=False),
    Column("respuesta", Text),
)
ia_propuestas = Table(
    "ia_propuestas",
    METADATA_IA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sesion_id", Integer, ForeignKey("ia_sesiones.id"), nullable=False),
    Column("propuesta", String(20), nullable=False),
    Column("tipo", String(20), nullable=False),
    Column("estado", String(20), nullable=False),
    Column("citas", Text, nullable=False),
    Column("supuestos", Text, nullable=False),
    Column("filas", Text, nullable=False),
    Column("decidida_por", String(80)),
    Column("decidida_en", DateTime),
)

TABLAS = ("ia_sesiones", "ia_turnos", "ia_llamadas", "ia_propuestas")
#: Claves que el anexo del paquete nunca lleva (uso de fichas, costo, topes): RV-19.
CLAVES_FUERA_DEL_ANEXO = frozenset(
    {"uso", "costo", "entrada", "salida", "cache_lectura", "cache_escritura", "topes"}
)


def crear_esquema_ia(motor: Engine) -> None:
    """Para pruebas y para una base nueva sin Alembic; el producto usa la revision de Alembic."""
    METADATA_IA.create_all(motor)


def _json(datos: object) -> str:
    return json.dumps(datos, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class RegistroIA:
    """Escribe el registro de UNA conexion; el llamador confirma la transaccion."""

    def __init__(self, conexion: Connection, ahora: Callable[[], datetime] = datetime.now) -> None:
        self._con = conexion
        self._ahora = ahora

    def iniciar(
        self,
        *,
        proyecto: str,
        version_partida: str,
        proveedor: str,
        modelo: str,
        pedido: str,
        topes: Mapping[str, object],
    ) -> int:
        resultado = self._con.execute(
            insert(ia_sesiones).values(
                proyecto=proyecto,
                version_partida=version_partida,
                proveedor=proveedor,
                modelo_pedido=modelo,
                pedido=pedido,
                topes=_json(topes),
                inicio=self._ahora(),
            )
        )
        return int(resultado.inserted_primary_key[0])

    def turno(
        self,
        sesion: int,
        orden: int,
        *,
        modelo: str,
        fin: str,
        uso: Mapping[str, int],
        costo: Decimal,
        texto: str,
    ) -> None:
        self._con.execute(
            insert(ia_turnos).values(
                sesion_id=sesion,
                orden=orden,
                modelo_respondio=modelo,
                fin=fin,
                entrada=uso["entrada"],
                salida=uso["salida"],
                cache_lectura=uso["cache_lectura"],
                cache_escritura=uso["cache_escritura"],
                costo=str(costo),
                texto=texto,
            )
        )

    def llamada(
        self,
        sesion: int,
        turno: int,
        herramienta: str,
        argumentos: Mapping[str, object],
        resultado: str,
        motivo: str,
        respuesta: str | None = None,
    ) -> None:
        self._con.execute(
            insert(ia_llamadas).values(
                sesion_id=sesion,
                turno=turno,
                herramienta=herramienta,
                argumentos=_json(argumentos),
                resultado=resultado,
                motivo=motivo,
                respuesta=respuesta,
            )
        )

    def propuesta(
        self,
        sesion: int,
        id_: str,
        tipo: str,
        estado: str,
        citas: object,
        supuestos: object,
        filas: object,
    ) -> None:
        self._con.execute(
            insert(ia_propuestas).values(
                sesion_id=sesion,
                propuesta=id_,
                tipo=tipo,
                estado=estado,
                citas=_json(citas),
                supuestos=_json(supuestos),
                filas=_json(filas),
            )
        )

    def decidir(self, sesion: int, id_: str, estado: str, quien: str) -> None:
        self._con.execute(
            update(ia_propuestas)
            .where(ia_propuestas.c.sesion_id == sesion, ia_propuestas.c.propuesta == id_)
            .values(estado=estado, decidida_por=quien, decidida_en=self._ahora())
        )

    def cerrar(self, sesion: int, motivo: str) -> None:
        self._con.execute(
            update(ia_sesiones)
            .where(ia_sesiones.c.id == sesion)
            .values(fin=self._ahora(), motivo_fin=motivo)
        )

    def marcar_guardada(
        self, sesion: int, codigo_version: str, *, proyecto: str | None = None
    ) -> None:
        """Anota la version en que entro la sesion. Si la sesion se hizo en un borrador sin
        proyecto (`proyecto` vacio) y `proyecto` viene dado, la sesion pasa a ese proyecto: sin
        eso `anexo_ia`, que filtra por proyecto, no la encontraria."""
        if proyecto:
            self._con.execute(
                update(ia_sesiones)
                .where(ia_sesiones.c.id == sesion, ia_sesiones.c.proyecto == "")
                .values(proyecto=proyecto)
            )
        self._con.execute(
            update(ia_sesiones)
            .where(ia_sesiones.c.id == sesion)
            .values(version_guardada=codigo_version)
        )


#: Columnas de tiempo de cada tabla: `volcado` las omite para comparar dos corridas.
MARCAS_DE_TIEMPO = {"ia_sesiones": ("inicio", "fin"), "ia_propuestas": ("decidida_en",)}


def volcado(conexion: Connection) -> dict[str, list[dict[str, Any]]]:
    """Todas las filas del registro, en orden y sin marcas de tiempo (para comparar corridas)."""
    salida: dict[str, list[dict[str, Any]]] = {}
    for tabla in (ia_sesiones, ia_turnos, ia_llamadas, ia_propuestas):
        omitir = MARCAS_DE_TIEMPO.get(tabla.name, ())
        filas = conexion.execute(select(tabla).order_by(tabla.c.id)).mappings().all()
        salida[tabla.name] = [{k: v for k, v in f.items() if k not in omitir} for f in filas]
    return salida


def anexo_ia(conexion: Connection, proyecto: str, hasta_codigo: str) -> bytes | None:
    """`anexos/ia.json`: sesiones del proyecto con propuestas aceptadas y guardadas hasta la
    version `hasta_codigo`, con pedido, turnos, llamadas con su validacion y decisiones; SIN uso de
    fichas ni costo y sin ninguna clave (RV-19). `None` si no hay ninguna (el anexo es opcional)."""
    sesiones = (
        conexion.execute(
            select(ia_sesiones)
            .where(
                ia_sesiones.c.proyecto == proyecto,
                ia_sesiones.c.version_guardada.is_not(None),
                ia_sesiones.c.version_guardada <= hasta_codigo,
            )
            .order_by(ia_sesiones.c.id)
        )
        .mappings()
        .all()
    )
    documento = []
    for s in sesiones:
        propuestas = (
            conexion.execute(
                select(ia_propuestas)
                .where(ia_propuestas.c.sesion_id == s["id"])
                .order_by(ia_propuestas.c.id)
            )
            .mappings()
            .all()
        )
        if not any(p["estado"] in ("aceptada", "editada") for p in propuestas):
            continue
        turnos = (
            conexion.execute(
                select(ia_turnos)
                .where(ia_turnos.c.sesion_id == s["id"])
                .order_by(ia_turnos.c.orden)
            )
            .mappings()
            .all()
        )
        llamadas = (
            conexion.execute(
                select(ia_llamadas)
                .where(ia_llamadas.c.sesion_id == s["id"])
                .order_by(ia_llamadas.c.id)
            )
            .mappings()
            .all()
        )
        documento.append(
            {
                "sesion": s["id"],
                "proveedor": s["proveedor"],
                "modelo_pedido": s["modelo_pedido"],
                "version_guardada": s["version_guardada"],
                "pedido": s["pedido"],
                "turnos": [
                    {
                        "orden": t["orden"],
                        "modelo": t["modelo_respondio"],
                        "fin": t["fin"],
                        "texto": t["texto"],
                    }
                    for t in turnos
                ],
                "llamadas": [
                    {
                        "turno": c["turno"],
                        "herramienta": c["herramienta"],
                        "argumentos": json.loads(c["argumentos"]),
                        "resultado": c["resultado"],
                        "motivo": c["motivo"],
                        "respuesta": c["respuesta"],
                    }
                    for c in llamadas
                ],
                "propuestas": [
                    {
                        "id": p["propuesta"],
                        "tipo": p["tipo"],
                        "estado": p["estado"],
                        "citas": json.loads(p["citas"]),
                        "supuestos": json.loads(p["supuestos"]),
                        "decidida_por": p["decidida_por"],
                    }
                    for p in propuestas
                ],
            }
        )
    if not documento:
        return None
    return _json({"formato": "silice-ia", "version_formato": 1, "sesiones": documento}).encode()
