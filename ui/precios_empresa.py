"""UC-17 4-5 sin Streamlit: la referencia MaPreX en Bs, la lista de una empresa y sus hallazgos de
R11 y R12 a una fecha de evaluacion (spec S1 §6). La pantalla `ui/paginas/precios_empresa.py` solo
pinta. Cada accion que escribe confirma o deshace su transaccion entera. Sin Streamlit, sin pandas y
sin `ui.caso` (lo vigila `tests/unit/test_arquitectura_s1.py`)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select

from core import models
from core.catalog import leer_lista_precios
from core.catalog.empresa import (
    crear_lista_de_empresa,
    crear_lista_de_referencia,
    instantanea_de_lista,
    lista_de_referencia,
    precios_propios_desde,
)
from core.catalog.indices import tasa_aplicable
from core.catalog.moneda import TasaDeclarada, exigir_moneda
from core.verification.precios import reglas_precios
from core.verification.texto import formatear_decimal

COLUMNAS_HALLAZGOS = ("Regla", "Severidad", "Descripción", "Impacto")
NOMBRE_REFERENCIA = "MaPreX julio 2026 en Bs"


@dataclass(frozen=True, slots=True)
class ResumenEmpresa:
    """Lo que hizo `crear_lista`: el nombre de la lista, cuantos precios propios entraron y las
    descripciones que el catalogo no conoce (UC-17 4a: se informan, no se dan de alta)."""

    nombre: str
    propios: int
    desconocidos: tuple[str, ...]


def _confirmar[T](sesion, accion: Callable[[], T]) -> T:
    try:
        resultado = accion()
        sesion.commit()
    except BaseException:
        sesion.rollback()
        raise
    return resultado


def cargar_referencia_maprex(sesion) -> str:
    """Carga la lista MaPreX julio 2026 en Bs (S1 §6.2). El script se importa aqui, dentro de la
    accion, nunca al cargar la pagina (RV-25). Una referencia ya cargada no se duplica."""
    from scripts.lista_maprex_bs import (
        FECHA_TASA_MAPREX,
        FUENTE_TASA_MAPREX,
        RUTA_SALIDA,
        TASA_MAPREX,
    )

    existente = lista_de_referencia(sesion)
    if existente is not None:
        return f"La referencia «{existente.nombre}» ya estaba cargada: no se escribio nada."
    tasa = TasaDeclarada(TASA_MAPREX, FECHA_TASA_MAPREX, FUENTE_TASA_MAPREX)
    lista = _confirmar(
        sesion,
        lambda: crear_lista_de_referencia(
            sesion, RUTA_SALIDA, nombre=NOMBRE_REFERENCIA, moneda="Bs", tasa=tasa
        ),
    )
    return f"Referencia «{lista.nombre}» cargada con {len(lista.precios)} precios."


def crear_lista(
    sesion,
    ruta: Path,
    *,
    empresa_nombre: str,
    empresa_rif: str,
    base_id: int,
    moneda: str,
    fecha: date,
    fuente: str,
    nombre: str,
) -> ResumenEmpresa:
    """UC-17 4: lee el archivo, separa los precios propios de los insumos que el catalogo no
    conoce y crea la lista de empresa sobre la base elegida. Si la base esta en otra moneda, se
    convierte con la tasa del BCV aplicable a `fecha` (S1 §6.1). Confirma o deshace todo."""
    exigir_moneda(moneda)
    leidos = leer_lista_precios(ruta)

    def accion() -> ResumenEmpresa:
        base = sesion.get(models.ListaPrecios, base_id)
        if base is None:
            raise ValueError(f"la lista base {base_id} no existe en este caso")
        propios, desconocidos = precios_propios_desde(sesion, leidos)
        tasa_base = None
        if base.moneda != moneda:
            tasa_base = TasaDeclarada.de_importacion(tasa_aplicable(sesion, fecha))
        lista = crear_lista_de_empresa(
            sesion,
            empresa_nombre,
            empresa_rif,
            base,
            propios,
            moneda=moneda,
            fecha=fecha,
            fuente=fuente,
            referencia=lista_de_referencia(sesion),
            nombre=nombre.strip() or None,
            tasa_base=tasa_base,
        )
        return ResumenEmpresa(
            lista.nombre, len(propios), tuple(leido.descripcion for leido in desconocidos)
        )

    return _confirmar(sesion, accion)


def hallazgos_de_lista(sesion, lista_id: int, fecha_evaluacion: date) -> list[dict[str, str]]:
    """R11 y R12 de la lista sola a `fecha_evaluacion`, en memoria (no escribe nada): sin version
    no hay cantidades, asi que el impacto es por unidad de insumo."""
    lista = sesion.get(models.ListaPrecios, lista_id)
    if lista is None:
        raise ValueError(f"la lista {lista_id} no existe en este caso")
    instantanea = instantanea_de_lista(sesion, lista, lista_de_referencia(sesion), fecha_evaluacion)
    return [
        dict(
            zip(
                COLUMNAS_HALLAZGOS,
                (
                    h.regla,
                    h.severidad.name,
                    h.descripcion,
                    "" if h.impacto is None else formatear_decimal(h.impacto, 2),
                ),
                strict=True,
            )
        )
        for regla in reglas_precios(instantanea)
        for h in regla.evaluar(None)
    ]


def listas_base(sesion) -> list[tuple[int, str, str]]:
    """Las listas que pueden ser base de una lista de empresa (id, nombre, moneda): todas menos las
    de proyecto y las de empresa, de la mas reciente a la mas antigua."""
    fuera = select(models.ListaPreciosOrigen.lista_id).where(
        models.ListaPreciosOrigen.alcance.in_((models.ALCANCE_PROYECTO, models.ALCANCE_EMPRESA))
    )
    return [
        (lista.id, lista.nombre, lista.moneda)
        for lista in sesion.scalars(
            select(models.ListaPrecios)
            .where(models.ListaPrecios.id.not_in(fuera))
            .order_by(models.ListaPrecios.fecha_vigencia.desc(), models.ListaPrecios.id.desc())
        )
    ]


def listas_de_empresa(sesion) -> list[tuple[int, str]]:
    """Las listas de empresa del caso (id, nombre), en el orden en que se crearon."""
    return [
        (lista.id, lista.nombre)
        for lista in sesion.scalars(
            select(models.ListaPrecios)
            .join(models.ListaEmpresa, models.ListaEmpresa.lista_id == models.ListaPrecios.id)
            .order_by(models.ListaPrecios.id)
        )
    ]
