"""El precio nuevo de un material como precio del corte de control (MP-7, Tarea 25; diseño de montar
un presupuesto §11, meta 4).

Un precio nuevo de un insumo (desde el estudio de mercado o al recibir una compra) puede declararse
«precio del corte» de una obra, para que el valor ganado separe el desvío de precio del de consumo
sin cargar un archivo en «Actualizar precios».

- **Declarar** (`declarar_precio_del_corte`): el precio de un material de la línea base de la obra
  (la última declarada), desde una fecha, en la moneda de la obra, con su fuente, quién y cuándo
  (`aplicacion/tablas_corte.py`, solo inserción). Un precio en otra moneda que la obra no se
  rechaza: se **convierte** con la tasa del BCV de su fecha (decisión de Eugenio del 2026-10-27,
  Tarea D2) y la fila guarda el rastro (`Equivalencia`: original, tasa, su fecha y su fuente,
  resultado). La tasa es la del mismo día del precio (`aplicacion/tasa_del_dia.py`, D2b) y la
  aritmética la de `core.catalog.moneda.convertir` (28 dígitos, mitad al par, sin redondear a
  centavos), la que usan la conversión de versiones y de listas; sin tasa del día,
  `SinTasaDelCorte` y nada se escribe.
- **Leer** (`precios_declarados`): por partida de la línea base vigente al corte, su composición
  congelada con el precio de cada material sustituido por el último declarado con `fecha <= corte`
  (mismas descripción y unidad, y la moneda de la obra), calculada con los parámetros de esa
  versión (`calcular_apu` del núcleo) → el costo directo (perspectiva costo) o el precio unitario
  (perspectiva precio). Una partida sin material declarado conserva su resultado de la línea base,
  así que su desvío de precio es exactamente cero. Sin ningún declarado que toque la línea base →
  `None`.
- **Equivalencias** (`precios_convertidos`): los precios vigentes al corte que se convirtieron, con
  su rastro, para que la pantalla del corte los muestre.

`core/` no se toca: se usan `instantanea_control`, `calcular_apu` y `PreciosDelCorte` tal cual. Sin
Streamlit ni FastAPI. Ninguna función confirma: escriben con `flush` y quien llama confirma.
`ReglaDelCorte` lleva el mensaje para la persona; `NoExiste` es el del estudio de mercado; los
demás `ValueError` son de programación.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.listas_para_armar import exigir_responsable
from aplicacion.mercado import NoExiste
from aplicacion.procura import explosion
from aplicacion.proyectos import resolver_proyecto
from aplicacion.tablas_corte import PrecioDelCorte, crear_esquema_corte, hay_tabla_corte
from aplicacion.tasa_del_dia import SinTasaDelDia, tasa_del_dia
from core import models
from core.budget.moneda import moneda_del_proyecto
from core.budget.valor_ganado import PERSPECTIVA_COSTO, PreciosDelCorte
from core.budget.valuaciones import instantanea_control, linea_base_vigente
from core.catalog import Catalogo
from core.catalog.moneda import convertir
from core.contracts.unidades import normalizar_unidad
from core.costing import calcular_apu

__all__ = [
    "LARGO_FUENTE",
    "METODO",
    "Equivalencia",
    "PrecioConvertido",
    "ReglaDelCorte",
    "SinTasaDelCorte",
    "declarar_desde_el_catalogo",
    "declarar_precio_del_corte",
    "precios_convertidos",
    "precios_declarados",
]

#: El nombre del método en `PreciosDelCorte.metodo` (lo muestra la fila «Método y fuente»).
METODO = "declarados"
LARGO_FUENTE = 300
_LARGO_RESPONSABLE = 200

Clave = tuple[str, str]


class ReglaDelCorte(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """Lo declarado no cumple una regla del precio del corte; el mensaje es el que ve la persona."""


class SinTasaDelCorte(ReglaDelCorte):
    """No hay tasa del BCV para la fecha del precio: no se puede convertir y nada se guarda."""


@dataclass(frozen=True, slots=True)
class Equivalencia:
    """La cuenta de un precio convertido, reconstruible por quien revise: el precio original (monto
    y moneda), la tasa (Bs por USD) con su fecha y su fuente, y el resultado en la moneda de la obra
    (exacto: `core.catalog.moneda.convertir`, sin redondear)."""

    precio_original: Decimal
    moneda_original: str
    tasa: Decimal
    fecha_tasa: date
    fuente_tasa: str
    convertido: Decimal
    moneda: str

    @property
    def operacion(self) -> str:
        """«÷» si se dividió por la tasa (Bs a USD), «×» si se multiplicó (USD a Bs): lo que hace
        `convertir`, dicho en un solo sitio."""
        return "÷" if self.moneda_original == "Bs" else "×"

    @property
    def fuente_legible(self) -> str:
        """La fuente de la tasa como se lee: «BCV, publicación del dd/mm/aaaa» (`fuente_tasa` es la
        referencia interna del rastro)."""
        return f"BCV, publicación del {self.fecha_tasa:%d/%m/%Y}"


@dataclass(frozen=True, slots=True)
class PrecioConvertido:
    """Un precio del corte vigente que se declaró en otra moneda, con su equivalencia."""

    descripcion: str
    unidad: str
    fecha: date
    fuente: str
    equivalencia: Equivalencia


def _convertir(sesion: Session, precio: Decimal, de: str, a: str, fecha: date) -> Equivalencia:
    """`precio` de `de` a `a` con la tasa del BCV de `fecha`; `SinTasaDelCorte` si no hay tasa."""
    try:
        tasa = tasa_del_dia(sesion, fecha, a)
    except SinTasaDelDia as error:
        raise SinTasaDelCorte(str(error)) from None
    return Equivalencia(
        precio_original=precio,
        moneda_original=de,
        tasa=tasa.valor,
        fecha_tasa=tasa.fecha,
        fuente_tasa=tasa.fuente,
        convertido=convertir(precio, de, a, tasa.valor),
        moneda=a,
    )


def _equivalencia(fila: PrecioDelCorte) -> Equivalencia | None:
    """La conversión que guardó la fila, o `None` si el precio ya estaba en la moneda de la obra."""
    if fila.moneda_original is None:
        return None
    assert fila.precio_original is not None and fila.tasa is not None  # se guardan juntos
    assert fila.fecha_tasa is not None and fila.fuente_tasa is not None
    return Equivalencia(
        precio_original=fila.precio_original,
        moneda_original=fila.moneda_original,
        tasa=fila.tasa,
        fecha_tasa=fila.fecha_tasa,
        fuente_tasa=fila.fuente_tasa,
        convertido=fila.precio,
        moneda=fila.moneda,
    )


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
) -> Equivalencia | None:
    """Declara `precio` como el precio del corte del material (`descripcion`, `unidad`) de la obra
    `proyecto` (código o nombre) desde `fecha`.

    El precio queda en la moneda de la obra. `moneda`, si se da, es la del precio: si es otra que la
    de la obra, se convierte con la tasa del BCV de `fecha` (`SinTasaDelCorte`, que es una
    `ReglaDelCorte`, si no hay tasa) y se devuelve su `Equivalencia`, que la fila también guarda;
    si es la misma, o no se da, se devuelve `None`. `ReglaDelCorte` también con un precio que no es
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
    equivalencia = (
        None
        if moneda is None or moneda == de_la_obra
        else _convertir(sesion, precio, moneda, de_la_obra, fecha)
    )
    if not hay_tabla_corte(sesion):
        crear_esquema_corte(sesion.connection())
    sesion.add(
        PrecioDelCorte(
            proyecto_id=obra.id,
            descripcion_insumo=clave[0],
            unidad=clave[1],
            precio=precio if equivalencia is None else equivalencia.convertido,
            moneda=de_la_obra,
            fecha=fecha,
            fuente=fuente,
            responsable=responsable,
            fecha_hora=ahora,
            moneda_original=None if equivalencia is None else equivalencia.moneda_original,
            precio_original=None if equivalencia is None else equivalencia.precio_original,
            tasa=None if equivalencia is None else equivalencia.tasa,
            fecha_tasa=None if equivalencia is None else equivalencia.fecha_tasa,
            fuente_tasa=None if equivalencia is None else equivalencia.fuente_tasa,
        )
    )
    sesion.flush()
    return equivalencia


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
) -> tuple[str, Equivalencia | None]:
    """`declarar_precio_del_corte` con el material nombrado por su código del catálogo (el estudio
    de mercado); devuelve la frase que lo confirma y la equivalencia si el precio se convirtió.
    `NoExiste` si el código no es de un insumo."""
    insumo = sesion.scalars(
        select(models.Insumo).where(models.Insumo.codigo == codigo_insumo)
    ).one_or_none()
    if insumo is None:
        raise NoExiste(f"No hay ningún insumo «{codigo_insumo}» en el catálogo.")
    equivalencia = declarar_precio_del_corte(
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
    frase = f"Declarado precio del corte de la obra «{obra.nombre}» desde el {fecha:%d/%m/%Y}."
    return frase, equivalencia


def _filas_ultimas(
    sesion: Session, proyecto_id: int, corte: date, moneda: str
) -> dict[Clave, PrecioDelCorte]:
    """La última fila declarada hasta `corte` de cada material de la obra en `moneda` (por fecha
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
    return {(fila.descripcion_insumo, _unidad(fila.unidad)): fila for fila in filas}


def _ultimos(sesion: Session, proyecto_id: int, corte: date, moneda: str) -> dict[Clave, Decimal]:
    """El último precio declarado hasta `corte` de cada material de la obra en `moneda`."""
    ultimas = _filas_ultimas(sesion, proyecto_id, corte, moneda)
    return {clave: fila.precio for clave, fila in ultimas.items()}


def precios_convertidos(sesion: Session, proyecto: str, corte: date) -> list[PrecioConvertido]:
    """Los precios del corte vigentes a `corte` (el último de cada material) que se declararon en
    otra moneda que la obra, con su equivalencia, por descripción. Es lo que la pantalla del corte
    muestra para que quien revise reconstruya la cuenta. `NoExiste` si la obra no existe."""
    obra = _obra(sesion, proyecto)
    if not hay_tabla_corte(sesion):
        return []
    ultimas = _filas_ultimas(sesion, obra.id, corte, moneda_del_proyecto(sesion, obra))
    convertidos = []
    for fila in ultimas.values():
        equivalencia = _equivalencia(fila)
        if equivalencia is not None:
            convertidos.append(
                PrecioConvertido(
                    descripcion=fila.descripcion_insumo,
                    unidad=fila.unidad,
                    fecha=fila.fecha,
                    fuente=fila.fuente,
                    equivalencia=equivalencia,
                )
            )
    return sorted(convertidos, key=lambda c: (c.descripcion, c.unidad))


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
