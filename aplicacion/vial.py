"""Los tramos viales guardados por versión (plan vial, Tarea 8).

Cada versión de una obra puede llevar los tramos de su vía (`adapters.vial.Tramo`). Se guardan en
la base del caso (`aplicacion/tablas_vial.py`) y se leen idénticos: las cifras son `Decimal` y se
persisten como texto, así que el «7.30» vuelve como «7.30».

- **Nada se sobrescribe.** Guardar otra vez los tramos de una versión inserta un guardado nuevo con
  su usuario, su hora y su fuente; al leer manda el último y los anteriores quedan en la base como
  rastro. (La Hoja tampoco pisa una versión: cada cambio es una versión nueva. Los tramos no
  forman parte del sello de la versión: son un anexo suyo, como el estudio de mercado.)
- **Herencia al leer, sin copiar.** Una versión sin guardado propio usa el último guardado de la
  versión anterior más cercana de la misma obra que tenga uno (`heredados_de` dice cuál). Leer no
  escribe filas ni cuenta como guardado de nadie. Para que lo heredado no cambie bajo los pies de
  una versión posterior, solo se guardan tramos en la versión más reciente de la obra.
- **Versión enviada, aprobada o devuelta: no se edita** (`VersionBloqueada`, la API responde 409).
  Solo se editan los tramos de una versión guardada o cuyo envío se retiró. La Hoja no crea ese
  bloqueo por sí sola (cada edición suya ya es una versión nueva); aquí sí hace falta porque los
  tramos se guardan sobre la misma versión que ve quien aprueba.
- **Todo o nada.** Un guardado que falla no deja filas; `guardar_tramos` confirma al terminar.
- **Importar un CSV** (`tramos_desde_csv`) lee con `adapters.vial.leer_tramos`: un solo error de
  cualquier fila y no se guarda nada; el mensaje nombra la fila como la numera una hoja de cálculo.

Cuándo se hace cada cosa lo decide quien llama: aquí no hay reloj ni usuario implícitos.
"""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Demarcacion, Tramo
from adapters.vial.reglas import ReglasViales
from adapters.vial.tabular import leer_tramos
from aplicacion import aprobaciones
from aplicacion.proyectos import resolver_proyecto
from aplicacion.tablas_vial import (
    GuardadoDeTramos,
    TramoGuardado,
    crear_esquema_vial,
    hay_tablas_viales,
)
from core import models
from produccion.receta import Receta

__all__ = [
    "CantidadVial",
    "RastroDeGuardado",
    "VersionBloqueada",
    "VersionInexistente",
    "bloqueo_de_version",
    "cantidades_de_tramos",
    "formula_asfalto_de_receta",
    "guardado_de_version",
    "heredados_de",
    "guardar_tramos",
    "obras_con_tramos",
    "reglas_viales",
    "texto_decimal",
    "tramos_de_version",
    "tramos_desde_csv",
    "version_de",
]

#: Cómo se dice el estado de una versión que ya no admite cambios en sus tramos.
_NO_EDITABLES = {
    "en_aprobacion": "en aprobación",
    "aprobada": "aprobada",
    "aprobada_con_observaciones": "aprobada con observaciones",
    "devuelta": "devuelta",
}

LARGO_FUENTE = 300
LARGO_USUARIO = 200
_NOMBRE_INVALIDO = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class VersionInexistente(LookupError):  # noqa: N818
    """La obra o la versión no existen en este caso (la API responde 404)."""


class VersionBloqueada(ValueError):  # noqa: N818
    """La versión ya no admite cambios en sus tramos (la API responde 409)."""


@dataclass(frozen=True, slots=True)
class RastroDeGuardado:
    """Quién guardó los tramos de una versión, cuándo y de dónde salieron."""

    usuario: str
    fecha_hora: datetime
    fuente: str


@dataclass(frozen=True, slots=True)
class CantidadVial:
    """Una cantidad de obra derivada de un tramo, con el origen y la regla que la producen."""

    tramo: str
    codigo: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    origen_id: str
    regla: str


def texto_decimal(valor: Decimal) -> str:
    """El decimal en notación fija y sin ceros de sobra («857.75», «7300»), sin redondear nada."""
    texto = format(valor, "f")
    return texto.rstrip("0").rstrip(".") if "." in texto else texto


# --- resolver la versión --------------------------------------------------------------------------


def version_de(sesion: Session, proyecto: str, codigo: str) -> int:
    """El `id` de la versión `codigo` de la obra `proyecto` (su código de `/v1/proyectos` o su
    nombre). `VersionInexistente` con el texto que se le dice a la persona si no existe."""
    obra = resolver_proyecto(sesion, proyecto)
    if obra is None:
        raise VersionInexistente(f"El proyecto «{proyecto}» no existe en este caso.")
    id_ = sesion.scalars(
        select(models.Presupuesto.id).where(
            models.Presupuesto.proyecto_id == obra.id, models.Presupuesto.codigo == codigo
        )
    ).first()
    if id_ is None:
        raise VersionInexistente(f"La versión {codigo} no existe en la obra «{obra.nombre}».")
    return id_


def _presupuesto(sesion: Session, version_id: int) -> models.Presupuesto:
    presupuesto = sesion.get(models.Presupuesto, version_id)
    if presupuesto is None:
        raise VersionInexistente(f"La versión n.º {version_id} no existe en este caso.")
    return presupuesto


def bloqueo_de_version(sesion: Session, version_id: int) -> str | None:
    """Por qué los tramos de la versión ya no se editan, o `None` si se pueden editar. Solo se
    editan los de la versión más reciente de la obra (las anteriores quedan fijas, así lo que una
    versión nueva hereda no cambia) y, en ella, mientras no se haya enviado a aprobación."""
    presupuesto = _presupuesto(sesion, version_id)
    obra = sesion.get(models.Proyecto, presupuesto.proyecto_id)
    if obra is None:  # una versión sin obra no existe a efectos de la API
        raise VersionInexistente(f"La versión n.º {version_id} no existe en este caso.")
    reciente = sesion.scalars(
        select(models.Presupuesto)
        .where(models.Presupuesto.proyecto_id == obra.id)
        .order_by(models.Presupuesto.id.desc())
    ).first()
    if reciente is not None and reciente.id != presupuesto.id:
        return f"Solo se editan los tramos de la versión más reciente ({reciente.codigo})."
    estado = aprobaciones.estados(sesion, obra.nombre)[presupuesto.codigo].estado
    texto = _NO_EDITABLES.get(estado)
    if texto is None:
        return None
    return (
        f"La versión {presupuesto.codigo} está {texto}: sus tramos ya no se editan. Guarde una "
        "versión nueva y cargue los tramos allí."
    )


# --- guardar y leer -------------------------------------------------------------------------------


def _capas_a_texto(capas: Sequence[Capa]) -> str:
    return json.dumps(
        [
            {
                "tipo": c.tipo,
                "espesor_m": None if c.espesor_m is None else str(c.espesor_m),
                "densidad_t_m3": None if c.densidad_t_m3 is None else str(c.densidad_t_m3),
                "dosis_l_m2": None if c.dosis_l_m2 is None else str(c.dosis_l_m2),
            }
            for c in capas
        ],
        ensure_ascii=False,
    )


def _capas_de_texto(texto: str) -> tuple[Capa, ...]:
    def cifra(valor: str | None) -> Decimal | None:
        return None if valor is None else Decimal(valor)

    return tuple(
        Capa(c["tipo"], cifra(c["espesor_m"]), cifra(c["densidad_t_m3"]), cifra(c["dosis_l_m2"]))
        for c in json.loads(texto)
    )


def _demarcacion_a_texto(demarcacion: Sequence[Demarcacion]) -> str:
    return json.dumps([{"tipo": d.tipo, "lineas": d.lineas} for d in demarcacion])


def _demarcacion_de_texto(texto: str) -> tuple[Demarcacion, ...]:
    return tuple(Demarcacion(d["tipo"], d["lineas"]) for d in json.loads(texto))


def guardar_tramos(
    sesion: Session,
    version_id: int,
    tramos: Sequence[Tramo],
    *,
    usuario: str,
    ahora: datetime,
    fuente: str = "",
) -> None:
    """Guarda `tramos` como los de la versión `version_id` y confirma. Es un guardado nuevo: el
    anterior no se borra. `VersionInexistente`, `VersionBloqueada` y `ValueError` (un id de tramo
    repetido, un usuario o una fuente demasiado largos); en cualquier fallo no queda nada."""
    try:
        _presupuesto(sesion, version_id)
        bloqueo = bloqueo_de_version(sesion, version_id)
        if bloqueo is not None:
            raise VersionBloqueada(bloqueo)
        _validar(tramos, usuario, fuente)
        if not hay_tablas_viales(sesion):
            crear_esquema_vial(sesion.connection())
        guardado = GuardadoDeTramos(
            version_id=version_id, usuario=usuario, fecha_hora=ahora, fuente=fuente
        )
        sesion.add(guardado)
        sesion.flush()
        for orden, tramo in enumerate(tramos, start=1):
            sesion.add(
                TramoGuardado(
                    guardado_id=guardado.id,
                    orden=orden,
                    tramo_id=tramo.id,
                    progresiva_ini_km=tramo.progresiva_ini_km,
                    progresiva_fin_km=tramo.progresiva_fin_km,
                    ancho_m=tramo.ancho_m,
                    distancia_planta_km=tramo.distancia_planta_km,
                    capas=_capas_a_texto(tramo.capas),
                    demarcacion=_demarcacion_a_texto(tramo.demarcacion),
                )
            )
        sesion.commit()
    except BaseException:
        sesion.rollback()
        raise


def _validar(tramos: Sequence[Tramo], usuario: str, fuente: str) -> None:
    vistos: set[str] = set()
    for tramo in tramos:
        if tramo.id in vistos:
            raise ValueError(f"el tramo {tramo.id} está repetido: cada tramo lleva un id propio")
        vistos.add(tramo.id)
    if len(usuario) > LARGO_USUARIO:
        raise ValueError(f"el usuario pasa de {LARGO_USUARIO} caracteres")
    if len(fuente) > LARGO_FUENTE:
        raise ValueError(f"la fuente pasa de {LARGO_FUENTE} caracteres")


def _propio(sesion: Session, version_id: int) -> GuardadoDeTramos | None:
    """El último guardado de la versión misma, sin herencia."""
    if not hay_tablas_viales(sesion):
        return None
    return sesion.scalars(
        select(GuardadoDeTramos)
        .where(GuardadoDeTramos.version_id == version_id)
        .order_by(GuardadoDeTramos.id.desc())
    ).first()


def _vigente(sesion: Session, version_id: int) -> tuple[GuardadoDeTramos | None, str | None]:
    """El guardado que vale para la versión y, si no es el suyo, el código de la versión de la que
    se hereda. Una versión sin guardado propio usa el último guardado de la versión anterior más
    cercana de la misma obra que tenga uno. Heredar no copia ni escribe nada."""
    propio = _propio(sesion, version_id)
    if propio is not None:
        return propio, None
    presupuesto = _presupuesto(sesion, version_id)
    anteriores = sesion.execute(
        select(models.Presupuesto.id, models.Presupuesto.codigo)
        .where(
            models.Presupuesto.proyecto_id == presupuesto.proyecto_id,
            models.Presupuesto.id < version_id,
        )
        .order_by(models.Presupuesto.id.desc())
    )
    for id_, codigo in anteriores:
        guardado = _propio(sesion, id_)
        if guardado is not None:
            return guardado, codigo
    return None, None


def heredados_de(sesion: Session, version_id: int) -> str | None:
    """El código de la versión de la que la versión hereda sus tramos, o `None` si tiene los suyos
    o no hay ninguno que heredar."""
    _presupuesto(sesion, version_id)
    return _vigente(sesion, version_id)[1]


def guardado_de_version(sesion: Session, version_id: int) -> RastroDeGuardado | None:
    """Quién, cuándo y de dónde salió el guardado que vale para la versión (el propio o el
    heredado); `None` si no hay."""
    _presupuesto(sesion, version_id)
    ultimo = _vigente(sesion, version_id)[0]
    if ultimo is None:
        return None
    return RastroDeGuardado(ultimo.usuario, ultimo.fecha_hora, ultimo.fuente)


def tramos_de_version(sesion: Session, version_id: int) -> list[Tramo]:
    """Los tramos que valen para la versión, en su orden: los de su último guardado o, si no tiene
    uno propio, los de la versión anterior más cercana que lo tenga (`heredados_de`); vacío si
    ninguna lo tiene."""
    _presupuesto(sesion, version_id)
    ultimo = _vigente(sesion, version_id)[0]
    if ultimo is None:
        return []
    filas = sesion.scalars(
        select(TramoGuardado)
        .where(TramoGuardado.guardado_id == ultimo.id)
        .order_by(TramoGuardado.orden)
    )
    return [
        Tramo(
            f.tramo_id,
            f.progresiva_ini_km,
            f.progresiva_fin_km,
            f.ancho_m,
            _capas_de_texto(f.capas),
            _demarcacion_de_texto(f.demarcacion),
            f.distancia_planta_km,
        )
        for f in filas
    ]


def obras_con_tramos(sesion: Session) -> list[int]:
    """Los `id` de las obras que tienen alguna versión con tramos en su último guardado."""
    if not hay_tablas_viales(sesion):
        return []
    ultimos = select(func.max(GuardadoDeTramos.id)).group_by(GuardadoDeTramos.version_id)
    con_tramos = (
        select(GuardadoDeTramos.version_id)
        .join(TramoGuardado, TramoGuardado.guardado_id == GuardadoDeTramos.id)
        .where(GuardadoDeTramos.id.in_(ultimos))
    )
    return sorted(
        set(
            sesion.scalars(
                select(models.Presupuesto.proyecto_id).where(models.Presupuesto.id.in_(con_tramos))
            )
        )
    )


# --- cantidades y CSV -----------------------------------------------------------------------------


def cantidades_de_tramos(tramos: Sequence[Tramo]) -> list[CantidadVial]:
    """Las cantidades de obra de `tramos` (las de `adapters.vial.derivar_tramos`), cada una con su
    tramo, su origen y la regla que la produce."""
    return [
        CantidadVial(
            tramo=item.origen_id.split(":")[1],
            codigo=item.codigo_partida,
            descripcion=item.descripcion,
            unidad=item.unidad,
            cantidad=item.cantidad,
            origen_id=item.origen_id,
            regla=item.regla or "",
        )
        for item in derivar_tramos(tramos)
    ]


def tramos_desde_csv(contenido: bytes, nombre: str) -> list[Tramo]:
    """Los tramos del CSV `contenido` (formato de `data/samples/vial/README.md`). Todo o nada:
    un error en cualquier fila es un `ValueError` que nombra el archivo y la fila."""
    limpio = _NOMBRE_INVALIDO.sub("_", nombre.replace("\\", "/").rsplit("/", 1)[-1]).strip()
    seguro = (limpio or "tramos.csv")[:100]
    with tempfile.TemporaryDirectory(prefix="silice-tramos-") as carpeta:
        ruta = Path(carpeta) / seguro
        ruta.write_bytes(contenido)
        try:
            return leer_tramos(ruta)
        except ValueError as error:
            raise ValueError(str(error).replace(repr(seguro), repr(nombre[:100]))) from None


# --- reglas del auditor ---------------------------------------------------------------------------


def formula_asfalto_de_receta(receta: Receta | None, codigo_ligante: str | None) -> Decimal | None:
    """El porcentaje de asfalto (en puntos: 5,5 es 5,5 %) de la fórmula de trabajo de `receta`.

    La fórmula es el componente ligante de la receta: el que lleva `codigo_ligante`, en t por
    tonelada de mezcla. Sin receta, sin código o sin ese componente en t, `None` (VR2 no se evalúa).
    """
    if receta is None or not codigo_ligante:
        return None
    for componente in receta.componentes:
        if componente.codigo == codigo_ligante and componente.unidad == "t":
            return componente.cantidad_por_t * 100
    return None


def reglas_viales(
    sesion: Session,
    version_id: int,
    *,
    receta: Receta | None = None,
    codigo_ligante: str | None = None,
) -> tuple[ReglasViales, ...]:
    """Las reglas VR1 a VR7 de la versión, para `elaborar(reglas=(*REGLAS, *reglas_viales(…)))` o
    `reglas_extra` de la Hoja: sus hallazgos entran en la auditoría como los de `Espacio` (regla
    ajena a `REGLAS`, que `hallazgos_externos` vuelve a declarar). Vacío si la versión no tiene
    tramos (propios o heredados)."""
    tramos = tramos_de_version(sesion, version_id)
    if not tramos:
        return ()
    return (ReglasViales(tramos, formula_asfalto_de_receta(receta, codigo_ligante)),)
