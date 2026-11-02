"""El historial de auditorias de «Libro de la empresa» (UC-25, UC-30; RF-142 a RF-146, RNF-28).

Cada auditoria correcta (de un libro o de un PDF simple) deja **una fila** con su resumen y sus
hallazgos compactos; repetir la misma auditoria deja otra fila (sin deduplicar por SHA-256). El
libro y el PDF **no se guardan nunca**: solo su nombre y su huella.

Un hallazgo entra compacto: regla, hoja, celda, severidad y mensaje, y nada mas. Se guardan a lo
sumo `TOPE_HALLAZGOS` (500) por auditoria; si hay mas, `recortado` es verdadero y los conteos por
severidad siguen siendo los de todos los hallazgos. Los conteos reparten los hallazgos sin
repetirlos: `errores` suma ERROR y CRITICO, `advertencias` las ADVERTENCIA, `informativos` las INFO
y `atipicos` los de la regla `ATIPICO` (que es de severidad ADVERTENCIA, pero se cuenta aparte).

Servicio sin FastAPI. Como los de `produccion/`, solo hace `flush`: confirmar o deshacer la
transaccion es de quien lo llama (la ruta de `/v1/libros` abre la suya para que un fallo al guardar
no tumbe la auditoria).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.hoja_empresa.modelo import FilaHallazgo
from core.budget.presupuesto import CODIGO_ATIPICO
from fusion.historial_modelo import AuditoriaLibro
from fusion.proceso import ResultadoFusion, ResultadoPdf

__all__ = [
    "TOPE_HALLAZGOS",
    "TOPE_MENSAJE",
    "AuditoriaGuardada",
    "AuditoriaInexistente",
    "HallazgoCompacto",
    "ResumenAuditoria",
    "compactar",
    "detalle",
    "listar",
    "registrar_auditoria",
    "registrar_resultado",
    "registrar_resultado_pdf",
]

TOPE_HALLAZGOS = 500
TOPE_MENSAJE = 500
TIPOS = ("libro", "pdf")
SEVERIDADES = frozenset({"INFO", "ADVERTENCIA", "ERROR", "CRITICO"})
_TOPE_REGLA, _TOPE_HOJA, _TOPE_CELDA, _TOPE_USUARIO, _TOPE_ARCHIVO = 40, 80, 40, 120, 255
_TOTAL_GENERAL = "TOTALGEN"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SEPARADOR_DE_RUTA = re.compile(r"[\\/]")


class AuditoriaInexistente(LookupError):  # noqa: N818 (el proyecto nombra la falta sin «Error»)
    """No hay una auditoria guardada con ese identificador."""


@dataclass(frozen=True, slots=True)
class HallazgoCompacto:
    """Lo unico que el historial guarda de un hallazgo."""

    regla: str
    hoja: str
    celda: str
    severidad: str
    mensaje: str


@dataclass(frozen=True, slots=True)
class ResumenAuditoria:
    """Una linea del historial: lo que muestra la lista, sin cargar los hallazgos."""

    id: int
    fecha_hora: datetime
    tipo: str
    nombre_archivo: str
    errores: int
    advertencias: int


@dataclass(frozen=True, slots=True)
class AuditoriaGuardada:
    """Una auditoria guardada, completa: el resumen y sus hallazgos compactos."""

    id: int
    fecha_hora: datetime
    usuario: str
    tipo: str
    nombre_archivo: str
    sha256: str
    fecha_libro: date | None
    total_libro: Decimal | None
    total_silice: Decimal | None
    errores: int
    advertencias: int
    informativos: int
    atipicos: int
    recortado: bool
    hallazgos: tuple[HallazgoCompacto, ...]


def compactar(fila: FilaHallazgo) -> HallazgoCompacto:
    """La fila de la tabla de hallazgos de la API (`codigo`, `celda` = `HOJA!A1`...) en su forma
    compacta: separa la hoja de la celda y descarta el impacto, la accion y todo lo demas."""
    hoja, _, celda = fila.celda.rpartition("!")
    if len(hoja) >= 2 and hoja[0] == hoja[-1] == "'":
        hoja = hoja[1:-1]
    return HallazgoCompacto(
        regla=fila.codigo,
        hoja=hoja,
        celda=celda,
        severidad=fila.severidad,
        mensaje=fila.descripcion,
    )


def _nombre_de_archivo(nombre: str) -> str:
    """Solo el nombre del archivo, sin la ruta de quien lo subio."""
    return _SEPARADOR_DE_RUTA.split(nombre.strip())[-1].strip()[:_TOPE_ARCHIVO]


def _acotado(h: HallazgoCompacto) -> HallazgoCompacto:
    if h.severidad not in SEVERIDADES:
        raise ValueError(f"severidad desconocida en un hallazgo: {h.severidad!r}")
    return HallazgoCompacto(
        regla=str(h.regla)[:_TOPE_REGLA],
        hoja=str(h.hoja)[:_TOPE_HOJA],
        celda=str(h.celda)[:_TOPE_CELDA],
        severidad=h.severidad,
        mensaje=str(h.mensaje)[:TOPE_MENSAJE],
    )


def _contar(hallazgos: Sequence[HallazgoCompacto]) -> tuple[int, int, int, int]:
    errores = advertencias = informativos = atipicos = 0
    for h in hallazgos:
        if h.regla == CODIGO_ATIPICO:
            atipicos += 1
        elif h.severidad in ("ERROR", "CRITICO"):
            errores += 1
        elif h.severidad == "ADVERTENCIA":
            advertencias += 1
        else:
            informativos += 1
    return errores, advertencias, informativos, atipicos


def _total(valor: Decimal | None, nombre: str) -> Decimal | None:
    if valor is not None and not (isinstance(valor, Decimal) and valor.is_finite()):
        raise ValueError(f"{nombre} debe ser un decimal finito o None, no {valor!r}")
    return valor


def _a_json(hallazgos: Sequence[HallazgoCompacto]) -> str:
    return json.dumps(
        [
            {
                "regla": h.regla,
                "hoja": h.hoja,
                "celda": h.celda,
                "severidad": h.severidad,
                "mensaje": h.mensaje,
            }
            for h in hallazgos
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _de_json(texto: str) -> tuple[HallazgoCompacto, ...]:
    return tuple(
        HallazgoCompacto(d["regla"], d["hoja"], d["celda"], d["severidad"], d["mensaje"])
        for d in json.loads(texto)
    )


def _guardada(fila: AuditoriaLibro) -> AuditoriaGuardada:
    return AuditoriaGuardada(
        id=fila.id,
        fecha_hora=fila.fecha_hora,
        usuario=fila.usuario,
        tipo=fila.tipo,
        nombre_archivo=fila.nombre_archivo,
        sha256=fila.sha256,
        fecha_libro=fila.fecha_libro,
        total_libro=fila.total_libro,
        total_silice=fila.total_silice,
        errores=fila.errores,
        advertencias=fila.advertencias,
        informativos=fila.informativos,
        atipicos=fila.atipicos,
        recortado=fila.recortado,
        hallazgos=_de_json(fila.hallazgos),
    )


def registrar_auditoria(
    sesion: Session,
    *,
    usuario: str,
    tipo: str,
    nombre_archivo: str,
    sha256: str,
    fecha_libro: date | None,
    total_libro: Decimal | None,
    total_silice: Decimal | None,
    hallazgos: Sequence[HallazgoCompacto],
    ahora: datetime,
) -> AuditoriaGuardada:
    """Guarda una auditoria (una fila nueva, siempre) y devuelve lo guardado.

    `tipo` es `"libro"` o `"pdf"`; `sha256` es la huella del archivo recibido, en hexadecimal
    minusculo; `ahora` lo manda quien llama (el servicio no lee el reloj). Un PDF simple va sin
    `fecha_libro` ni totales. `ValueError`, sin guardar nada, ante un `tipo`, una huella, un
    usuario, un nombre, un total o una severidad que no valen.
    """
    if tipo not in TIPOS:
        raise ValueError(f"tipo de auditoria desconocido: {tipo!r}")
    if not _SHA256.fullmatch(sha256):
        raise ValueError("sha256 debe ser una huella SHA-256 en hexadecimal minusculo")
    quien = usuario.strip()[:_TOPE_USUARIO]
    nombre = _nombre_de_archivo(nombre_archivo)
    if not quien or not nombre:
        raise ValueError("el usuario y el nombre del archivo son obligatorios")
    compactos = [_acotado(h) for h in hallazgos]
    errores, advertencias, informativos, atipicos = _contar(compactos)
    guardados = compactos[:TOPE_HALLAZGOS]
    fila = AuditoriaLibro(
        fecha_hora=ahora,
        usuario=quien,
        tipo=tipo,
        nombre_archivo=nombre,
        sha256=sha256,
        fecha_libro=fecha_libro,
        total_libro=_total(total_libro, "total_libro"),
        total_silice=_total(total_silice, "total_silice"),
        errores=errores,
        advertencias=advertencias,
        informativos=informativos,
        atipicos=atipicos,
        recortado=len(compactos) > TOPE_HALLAZGOS,
        hallazgos=_a_json(guardados),
    )
    sesion.add(fila)
    sesion.flush()
    return _guardada(fila)


def registrar_resultado(
    sesion: Session, resultado: ResultadoFusion, *, usuario: str, ahora: datetime
) -> AuditoriaGuardada:
    """Guarda la auditoria de un libro (`fusion.proceso.procesar_libro`): el nombre y la huella del
    libro recibido, la fecha del libro, el total general del libro y el de Silice (`TOTALGEN`) y la
    tabla de hallazgos compactada. Es lo que llaman `POST /v1/libros/auditoria` y la pagina
    «Libro de la empresa»."""
    return registrar_auditoria(
        sesion,
        usuario=usuario,
        tipo="libro",
        nombre_archivo=resultado.libro.nombre,
        sha256=resultado.libro.sha256,
        fecha_libro=resultado.fecha_libro,
        total_libro=(resultado.libro.totales or {}).get(_TOTAL_GENERAL),
        total_silice=(resultado.totales_silice or {}).get(_TOTAL_GENERAL),
        hallazgos=[compactar(fila) for fila in resultado.hallazgos_tabla],
        ahora=ahora,
    )


def registrar_resultado_pdf(
    sesion: Session,
    resultado: ResultadoPdf,
    *,
    usuario: str,
    nombre_archivo: str,
    ahora: datetime,
) -> AuditoriaGuardada:
    """Guarda la revision de un PDF simple (`fusion.proceso.auditar_pdf_simple`, L10): sin fecha
    del libro ni totales, porque un PDF no se recalcula."""
    return registrar_auditoria(
        sesion,
        usuario=usuario,
        tipo="pdf",
        nombre_archivo=nombre_archivo,
        sha256=resultado.sha256,
        fecha_libro=None,
        total_libro=None,
        total_silice=None,
        hallazgos=[compactar(fila) for fila in resultado.hallazgos_tabla],
        ahora=ahora,
    )


def listar(sesion: Session, limite: int) -> list[ResumenAuditoria]:
    """Las `limite` auditorias mas recientes, la ultima primero (empata el identificador mayor)."""
    if limite < 1:
        raise ValueError("el limite debe ser al menos 1")
    filas = sesion.execute(
        select(
            AuditoriaLibro.id,
            AuditoriaLibro.fecha_hora,
            AuditoriaLibro.tipo,
            AuditoriaLibro.nombre_archivo,
            AuditoriaLibro.errores,
            AuditoriaLibro.advertencias,
        )
        .order_by(AuditoriaLibro.fecha_hora.desc(), AuditoriaLibro.id.desc())
        .limit(limite)
    )
    return [ResumenAuditoria(*fila) for fila in filas]


def detalle(sesion: Session, id: int) -> AuditoriaGuardada:  # noqa: A002 - es el nombre de la ruta
    """Una auditoria con su resumen y sus hallazgos; `AuditoriaInexistente` si no existe."""
    fila = sesion.get(AuditoriaLibro, id)
    if fila is None:
        raise AuditoriaInexistente(f"No hay una auditoría guardada con el número {id}.")
    return _guardada(fila)
