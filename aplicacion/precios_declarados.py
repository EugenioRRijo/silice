"""El precio nuevo de un material como precio del corte de control (MP-7, Tarea 25; diseño de montar
un presupuesto §11, meta 4).

Un precio nuevo de un insumo (desde el estudio de mercado o al recibir una compra) puede declararse
«precio del corte» de una obra, para que el valor ganado separe el desvío de precio del de consumo
sin cargar un archivo en «Actualizar precios».

- **Declarar** (`declarar_precio_del_corte`): el precio de un material de la línea base de la obra
  (la última declarada), desde una fecha, en la moneda de la obra, con su fuente, quién y cuándo
  (`aplicacion/tablas_corte.py`, solo inserción).
- **Leer** (`precios_declarados`): por partida de la línea base vigente al corte, su composición
  congelada con el precio de cada material sustituido por el último declarado con `fecha <= corte`
  (mismas descripción y unidad, y la moneda de la obra), calculada con los parámetros de esa
  versión (`calcular_apu` del núcleo) → el costo directo (perspectiva costo) o el precio unitario
  (perspectiva precio). Una partida sin material declarado conserva su resultado de la línea base,
  así que su desvío de precio es exactamente cero. Sin ningún declarado que toque la línea base →
  `None`.

`core/` no se toca: se usan `instantanea_control`, `calcular_apu` y `PreciosDelCorte` tal cual. Sin
Streamlit ni FastAPI. Ninguna función confirma: escriben con `flush` y quien llama confirma.
`ReglaDelCorte` lleva el mensaje para la persona; `NoExiste` es el del estudio de mercado; los
demás `ValueError` son de programación.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.listas_para_armar import exigir_responsable
from aplicacion.mercado import NoExiste
from aplicacion.procura import explosion
from aplicacion.proyectos import resolver_proyecto
from aplicacion.tablas_corte import PrecioDelCorte, crear_esquema_corte, hay_tabla_corte
from core import models
from core.budget.moneda import moneda_del_proyecto
from core.budget.valor_ganado import PERSPECTIVA_COSTO, PreciosDelCorte
from core.budget.valuaciones import instantanea_control, linea_base_vigente
from core.catalog import Catalogo
from core.contracts.unidades import normalizar_unidad
from core.costing import calcular_apu

__all__ = [
    "LARGO_FUENTE",
    "METODO",
    "ReglaDelCorte",
    "declarar_desde_el_catalogo",
    "declarar_precio_del_corte",
    "precios_declarados",
]

#: El nombre del método en `PreciosDelCorte.metodo` (lo muestra la fila «Método y fuente»).
METODO = "declarados"
LARGO_FUENTE = 300
_LARGO_RESPONSABLE = 200

Clave = tuple[str, str]


class ReglaDelCorte(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """Lo declarado no cumple una regla del precio del corte; el mensaje es el que ve la persona."""


def _unidad(texto: str) -> str:
    """La unidad canónica (`normalizar_unidad` del núcleo); sin unidad, vacía."""
    return normalizar_unidad(texto) if texto.strip() else ""


def _obra(sesion: Session, proyecto: str) -> models.Proyecto:
    obra = resolver_proyecto(sesion, proyecto.strip())
    if obra is None:
        raise NoExiste(f"No hay ninguna obra «{proyecto}» en esta carpeta de trabajo.")
    return obra


def _material(sesion: Session, obra: models.Proyecto, descripcion: str, unidad: str) -> Clave:
    """La clave (descripción, unidad) del material en la última línea base de la obra.

    `ReglaDelCorte` si la obra no tiene línea base; `NoExiste` si su versión no pide ese material
    (los materiales son los de la explosión de la procura: equipos y mano de obra no cuentan)."""
    fila = linea_base_vigente(sesion, obra.nombre, date.max)
    if fila is None:
        raise ReglaDelCorte(
            f"La obra «{obra.nombre}» no tiene línea base de control: declárela antes de declarar "
            "precios del corte."
        )
    version = sesion.get(models.Presupuesto, fila.presupuesto_id)
    buscada = (descripcion.strip(), _unidad(unidad))
    for necesidad in explosion(sesion, obra.nombre, version.codigo):
        if (necesidad.descripcion, _unidad(necesidad.unidad)) == buscada:
            return necesidad.descripcion, necesidad.unidad
    raise NoExiste(f"«{buscada[0]}» no es un material de la línea base de la obra «{obra.nombre}».")


def declarar_precio_del_corte(
    sesion: Session,
    proyecto: str,
    *,
    descripcion: str,
    unidad: str,
    precio: Decimal,
    fecha: date,
    fuente: str,
    responsable: str,
    ahora: datetime,
    moneda: str | None = None,
) -> None:
    """Declara `precio` como el precio del corte del material (`descripcion`, `unidad`) de la obra
    `proyecto` (código o nombre) desde `fecha`.

    El precio queda en la moneda de la obra; `moneda`, si se da, es la del precio y debe ser esa
    (`ReglaDelCorte`: no se convierte en silencio). `ReglaDelCorte` también con un precio que no es
    mayor que cero, una fecha posterior a `ahora`, la fuente vacía o de más de 300 caracteres, o una
    obra sin línea base; `NoExiste` si la obra no existe o su línea base no pide ese material. Si la
    base no tiene la tabla, la crea en la misma transacción. No confirma."""
    responsable = exigir_responsable(responsable)
    if len(responsable) > _LARGO_RESPONSABLE:
        raise ValueError(
            f"quien lo hace (responsable) admite hasta {_LARGO_RESPONSABLE} caracteres"
        )
    obra = _obra(sesion, proyecto)
    if precio <= 0:
        raise ReglaDelCorte("El precio del corte debe ser mayor que cero.")
    if fecha > ahora.date():
        raise ReglaDelCorte("La fecha del precio no puede ser posterior a hoy.")
    fuente = fuente.strip()
    if not fuente:
        raise ReglaDelCorte("Diga de dónde sale el precio (la fuente).")
    if len(fuente) > LARGO_FUENTE:
        raise ReglaDelCorte(f"La fuente del precio admite hasta {LARGO_FUENTE} caracteres.")
    clave = _material(sesion, obra, descripcion, unidad)
    de_la_obra = moneda_del_proyecto(sesion, obra)
    if moneda is not None and moneda != de_la_obra:
        raise ReglaDelCorte(
            f"El precio está en {moneda} y la obra «{obra.nombre}» en {de_la_obra}: no se puede "
            "declarar como precio del corte."
        )
    if not hay_tabla_corte(sesion):
        crear_esquema_corte(sesion.connection())
    sesion.add(
        PrecioDelCorte(
            proyecto_id=obra.id,
            descripcion_insumo=clave[0],
            unidad=clave[1],
            precio=precio,
            moneda=de_la_obra,
            fecha=fecha,
            fuente=fuente,
            responsable=responsable,
            fecha_hora=ahora,
        )
    )
    sesion.flush()


def declarar_desde_el_catalogo(
    sesion: Session,
    proyecto: str,
    codigo_insumo: str,
    *,
    precio: Decimal,
    fecha: date,
    fuente: str,
    responsable: str,
    ahora: datetime,
    moneda: str | None = None,
) -> str:
    """`declarar_precio_del_corte` con el material nombrado por su código del catálogo (el estudio
    de mercado); devuelve la frase que lo confirma. `NoExiste` si el código no es de un insumo."""
    insumo = sesion.scalars(
        select(models.Insumo).where(models.Insumo.codigo == codigo_insumo)
    ).one_or_none()
    if insumo is None:
        raise NoExiste(f"No hay ningún insumo «{codigo_insumo}» en el catálogo.")
    declarar_precio_del_corte(
        sesion,
        proyecto,
        descripcion=insumo.descripcion,
        unidad=insumo.unidad or "",
        precio=precio,
        fecha=fecha,
        fuente=fuente,
        responsable=responsable,
        ahora=ahora,
        moneda=moneda,
    )
    obra = _obra(sesion, proyecto)
    return f"Declarado precio del corte de la obra «{obra.nombre}» desde el {fecha:%d/%m/%Y}."


def _ultimos(sesion: Session, proyecto_id: int, corte: date, moneda: str) -> dict[Clave, Decimal]:
    """El último precio declarado hasta `corte` de cada material de la obra en `moneda` (por fecha
    y, el mismo día, por orden de registro)."""
    filas = sesion.scalars(
        select(PrecioDelCorte)
        .where(
            PrecioDelCorte.proyecto_id == proyecto_id,
            PrecioDelCorte.fecha <= corte,
            PrecioDelCorte.moneda == moneda,
        )
        .order_by(PrecioDelCorte.fecha, PrecioDelCorte.id)
    )
    return {(fila.descripcion_insumo, _unidad(fila.unidad)): fila.precio for fila in filas}


def precios_declarados(
    sesion: Session,
    proyecto: str,
    catalogo: Catalogo,
    corte: date | None,
    perspectiva: str,
) -> PreciosDelCorte | None:
    """Los precios del corte con los materiales declarados hasta `corte` (sin `corte`, el de la
    instantánea de control: el *hasta* de la última valuación), en la `perspectiva` dada, o `None`
    si ningún declarado toca la línea base.

    `NoExiste` si la obra no existe; los errores de `instantanea_control` (sin línea base al corte,
    línea base invalidada) pasan tal cual."""
    obra = _obra(sesion, proyecto)
    if not hay_tabla_corte(sesion):
        return None
    instantanea = instantanea_control(sesion, obra.nombre, catalogo=catalogo, corte=corte)
    declarados = _ultimos(sesion, obra.id, instantanea.corte, instantanea.moneda)
    if not declarados:
        return None
    usados: set[Clave] = set()
    unitarios: dict[str, Decimal] = {}
    for renglon in instantanea.presupuesto.partidas:
        materiales = []
        for linea in renglon.apu.materiales:
            clave = (linea.descripcion, linea.unidad)
            if clave in declarados:
                usados.add(clave)
                linea = replace(linea, precio=declarados[clave])
            materiales.append(linea)
        resultado = renglon.resultado
        if tuple(materiales) != renglon.apu.materiales:
            nueva = replace(renglon.apu, materiales=tuple(materiales))
            resultado = calcular_apu(nueva, instantanea.parametros_costo)
        unitarios.setdefault(
            renglon.item.codigo_partida,
            resultado.costo_directo
            if perspectiva == PERSPECTIVA_COSTO
            else resultado.precio_unitario,
        )
    if not usados:
        return None
    cuantos = f"{len(usados)} {'insumo' if len(usados) == 1 else 'insumos'}"
    return PreciosDelCorte(
        METODO, f"Precios declarados al {instantanea.corte:%d/%m/%Y}: {cuantos}", unitarios
    )
