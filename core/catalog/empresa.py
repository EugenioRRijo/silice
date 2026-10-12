"""SL-E2: lista de precios de una empresa y lista de referencia (spec S1 §6). No hace `commit`."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.catalog.moneda import TasaDeclarada, convertir, copiar_precios, exigir_moneda
from core.catalog.origen import origenes_efectivos
from core.catalog.precios import (
    PrecioLeido,
    _identidad_alta,
    _insumos_por_clave,
    leer_lista_precios,
)
from core.catalog.repositorio import Catalogo

RANGO_INFERIOR = Decimal("-0.20")  # S1-R5, por analogía con AACE clase 3
RANGO_SUPERIOR = Decimal("0.30")
PLAZO_VIGENCIA_DIAS = 30  # S1-R6, SUPUESTO_DECLARADO


@dataclass(frozen=True, slots=True)
class PrecioPropio:
    """Un precio de la empresa: su valor en `moneda_original` con fecha, fuente y, si se
    convierte, la tasa con su fecha y su fuente."""

    insumo_id: int
    precio: Decimal
    fecha: date
    fuente: str
    referencia: str = ""
    moneda_original: str = ""
    tasa: Decimal | None = None
    fecha_tasa: date | None = None
    fuente_tasa: str = ""


def precios_propios_desde(
    session: Session, leidos: Sequence[PrecioLeido]
) -> tuple[list[PrecioPropio], list[PrecioLeido]]:
    """Las filas del archivo como precios propios (todas las variantes homónimas, como UC-02).

    Devuelve `(propios, desconocidos)`: un insumo que el catálogo no tiene no se da de alta aquí
    (decisión del administrador). Una fila sin fecha o sin fuente se rechaza con su insumo (RF-67).
    """
    indice = _insumos_por_clave(session)
    propios: list[PrecioPropio] = []
    desconocidos: list[PrecioLeido] = []
    for leido in leidos:
        variantes = indice.get(_identidad_alta(leido))
        if not variantes:
            desconocidos.append(leido)
            continue
        if leido.fecha is None or not leido.fuente.strip():
            raise ValueError(f"{leido.descripcion}: el precio propio exige fecha y fuente (RF-67)")
        propios += [
            PrecioPropio(
                insumo.id,
                leido.precio,
                leido.fecha,
                leido.fuente,
                leido.referencia,
                leido.moneda,
                leido.tasa,
                leido.fecha_tasa,
                leido.fuente_tasa,
            )
            for insumo in variantes
        ]
    return propios, desconocidos


def _validar_propios(precios_propios: Sequence[PrecioPropio], moneda: str) -> None:
    """Todo propio se valida antes de escribir nada: la lista no queda a medias."""
    vistos: set[int] = set()
    for p in precios_propios:
        if p.insumo_id in vistos:
            raise ValueError(f"insumo {p.insumo_id}: dos precios propios para el mismo insumo")
        vistos.add(p.insumo_id)
        original = exigir_moneda(p.moneda_original or moneda)
        if original != moneda and p.tasa is None:
            raise ValueError(f"insumo {p.insumo_id}: precio en {original} sin tasa a {moneda}")


def crear_lista_de_empresa(
    session: Session,
    empresa_nombre: str,
    empresa_rif: str,
    base: models.ListaPrecios,
    precios_propios: Sequence[PrecioPropio],
    *,
    moneda: str,
    fecha: date,
    fuente: str,
    referencia: models.ListaPrecios | None,
    nombre: str | None = None,
    tasa_base: TasaDeclarada | None = None,
    plazo_vigencia_dias: int = PLAZO_VIGENCIA_DIAS,
    rango_inferior: Decimal = RANGO_INFERIOR,
    rango_superior: Decimal = RANGO_SUPERIOR,
) -> models.ListaPrecios:
    """Copia de `base` (convertida con `tasa_base` si su moneda difiere) con los propios encima.

    Alcance `empresa`: `lista_vigente` no la resuelve; una versión la referencia explícitamente. La
    empresa es texto (RV-6). Cada precio propio lleva su `PrecioOrigen`; los heredados conservan el
    de la base.
    """
    if moneda not in ("Bs", "USD"):
        raise ValueError(f"moneda {moneda!r}: la lista se rechaza (UC-17 4b)")
    if not empresa_nombre.strip() or not empresa_rif.strip() or not fuente.strip():
        raise ValueError("la empresa (nombre y RIF) y la fuente de la lista son obligatorias")
    if rango_inferior > rango_superior:
        raise ValueError("el rango inferior no puede ser mayor que el superior")
    if plazo_vigencia_dias < 0:
        raise ValueError("el plazo de vigencia no puede ser negativo")
    _validar_propios(precios_propios, moneda)
    lista = models.ListaPrecios(
        nombre=(nombre or f"{empresa_nombre} {fecha:%Y-%m-%d}")[:120],
        moneda=moneda,
        fecha_vigencia=fecha,
        origen=fuente[:200],
    )
    session.add(lista)
    session.flush()
    session.add(
        models.ListaPreciosOrigen(
            lista_id=lista.id, alcance=models.ALCANCE_EMPRESA, lista_base_id=base.id
        )
    )
    copiar_precios(session, base, lista, tasa_base, excluir={p.insumo_id for p in precios_propios})
    for p in precios_propios:
        original = exigir_moneda(p.moneda_original or moneda)
        if original == moneda or p.tasa is None:
            valor = p.precio
        else:
            valor = convertir(p.precio, original, moneda, p.tasa)
        fila = models.PrecioInsumo(lista_id=lista.id, insumo_id=p.insumo_id, precio=valor)
        session.add(fila)
        session.flush()
        session.add(
            models.PrecioOrigen(
                precio_id=fila.id,
                moneda_original=original,
                precio_original=p.precio,
                fecha_precio=p.fecha,
                tasa=p.tasa,
                fecha_tasa=p.fecha_tasa,
                fuente_tasa=p.fuente_tasa,
                fuente=p.fuente,
            )
        )
        if p.referencia.strip():
            session.add(models.ReferenciaPrecio(precio_id=fila.id, referencia=p.referencia.strip()))
    session.add(
        models.ListaEmpresa(
            lista_id=lista.id,
            empresa_nombre=empresa_nombre.strip(),
            empresa_rif=empresa_rif.strip(),
            lista_base_id=base.id,
            lista_referencia_id=referencia.id if referencia else None,
            plazo_vigencia_dias=plazo_vigencia_dias,
            rango_inferior=rango_inferior,
            rango_superior=rango_superior,
        )
    )
    session.flush()
    session.expire(lista, ["precios"])
    return lista


def crear_lista_de_referencia(
    session: Session, ruta: Path, *, nombre: str, moneda: str, tasa: TasaDeclarada
) -> models.ListaPrecios:
    """Lista de alcance `referencia` (p. ej. MaPreX en Bs): da de alta los insumos que falten
    (decisión explícita del administrador al cargarla) y guarda Ref, fecha y tasa por precio.

    Solo sirve para contrastar con R11: `lista_vigente` no la resuelve (S1 §6.2)."""
    leidos = leer_lista_precios(ruta)
    if not leidos:
        raise ValueError(f"{ruta.name}: la lista de referencia no tiene ninguna fila")
    for numero, leido in enumerate(leidos, start=2):
        if leido.fecha is None:
            raise ValueError(f"{ruta.name}, fila {numero}: la referencia exige la columna fecha")
    catalogo = Catalogo(session)
    indice = _insumos_por_clave(session)
    lista = models.ListaPrecios(
        nombre=nombre[:120],
        moneda=exigir_moneda(moneda),
        fecha_vigencia=max(leido.fecha for leido in leidos if leido.fecha is not None),
        origen=ruta.name,
    )
    session.add(lista)
    session.flush()
    session.add(
        models.ListaPreciosOrigen(
            lista_id=lista.id,
            tasa=tasa.valor,
            fecha_tasa=tasa.fecha,
            alcance=models.ALCANCE_REFERENCIA,
        )
    )
    for leido in leidos:
        clave = _identidad_alta(leido)
        insumo = (indice.get(clave) or [None])[0] or catalogo.dar_de_alta_insumo(
            leido.tipo, leido.descripcion, leido.unidad
        )
        indice[clave] = [insumo]
        fila = models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=leido.precio)
        session.add(fila)
        session.flush()
        session.add(
            models.PrecioOrigen(
                precio_id=fila.id,
                moneda_original=moneda,
                precio_original=leido.precio,
                fecha_precio=leido.fecha,
                tasa=tasa.valor,
                fecha_tasa=tasa.fecha,
                fuente_tasa=tasa.fuente,
                fuente=leido.fuente,
            )
        )
        if leido.referencia:
            session.add(models.ReferenciaPrecio(precio_id=fila.id, referencia=leido.referencia))
    session.flush()
    session.expire(lista, ["precios"])
    return lista


def lista_de_referencia(session: Session) -> models.ListaPrecios | None:
    """La última lista de alcance `referencia` cargada, o `None`."""
    return session.scalars(
        select(models.ListaPrecios)
        .join(
            models.ListaPreciosOrigen,
            models.ListaPreciosOrigen.lista_id == models.ListaPrecios.id,
        )
        .where(models.ListaPreciosOrigen.alcance == models.ALCANCE_REFERENCIA)
        .order_by(models.ListaPrecios.id.desc())
        .limit(1)
    ).one_or_none()


def es_heredado(
    session: Session, lista: models.ListaPrecios, precio: models.PrecioInsumo
) -> bool | None:
    """`None` si la lista no es de empresa. Heredado = mismo insumo en la base con igual moneda y
    precio originales, fecha y fuente (la tasa puede diferir si la base se convirtió)."""
    fila = session.get(models.ListaEmpresa, lista.id)
    if fila is None:
        return None
    base = session.get(models.ListaPrecios, fila.lista_base_id)
    en_base = {p.insumo_id: p for p in base.precios}
    if precio.insumo_id not in en_base:
        return False
    propio = origenes_efectivos(session, lista)[precio.id]
    de_base = origenes_efectivos(session, base)[en_base[precio.insumo_id].id]
    campos = ("moneda_original", "precio_original", "fecha_precio", "fuente")
    return all(getattr(propio, c) == getattr(de_base, c) for c in campos)
