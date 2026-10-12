"""SL-E8: el documento canónico de una versión y su lectura (spec S3 §6.1; maestro §4.5).

`documento(session, version)` serializa, **desde las filas guardadas** (nunca recalculadas), todo
lo que define una versión: JSON UTF-8, claves ordenadas, sin espacios, `Decimal` como el texto
posicional exacto de `DecimalExacto`, y sin ningún `id` de fila (cambian entre instalaciones).
Es a la vez el contenido que se encadena (`huella_contenido`), el `presupuesto.json` del paquete
y el cuerpo de `POST /v1/auditorias` (DRY).

`leer(objeto)` es la inversa. Recibe el objeto ya leído por el lector JSON estricto del paquete
(`seguridad.json_estricto`, que `core` no puede importar): aquí solo se valida la forma y que
cada cifra cumpla `PATRON_CIFRA` ANTES de construir un `Decimal`. El patrón es el mismo de aquel
lector; `tests/unit/test_canonico.py` vigila que no diverjan.

Tres decisiones que el spec dejó abiertas (plan 0.8.0, RP8-3 y RP8-13):
* la **moneda del proyecto** de una versión sale de `_moneda_del_proyecto`: la última conversión
  hecha hasta esa versión (por **orden de creación**, no por fecha) o, si no hay, la primera
  declaración si ya existía a su fecha;
* los `Decimal` se escriben con `format(valor, "f")`: nunca con exponente (`1E+3` no pasaría el
  patrón); coincide con `str` para toda cifra sin exponente;
* el patrón admite 20 enteros y 28 decimales: el motor no redondea (prec 28).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget.curva import PeriodoPlan
from core.catalog.empresa import es_heredado
from core.catalog.origen import origenes_efectivos
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.presupuesto import PuntoCurva
from core.contracts.verificacion import Hallazgo, Severidad

__all__ = [
    "FORMATO",
    "PATRON_CIFRA",
    "VERSION_FORMATO",
    "DocumentoInvalido",
    "DocumentoLeido",
    "LineaLeida",
    "RenglonDeclarado",
    "documento",
    "estructura",
    "contar_filas",
    "huella",
    "json_canonico",
    "leer",
    "texto_decimal",
]

FORMATO = "silice-presupuesto"
VERSION_FORMATO = 1
PATRON_CIFRA = re.compile(r"^-?[0-9]{1,20}(\.[0-9]{1,28})?$")


class DocumentoInvalido(ValueError):  # noqa: N818
    """El documento no tiene la forma de `silice-presupuesto` v1; el mensaje dice qué falta."""


# --- serialización --------------------------------------------------------------------------


def texto_decimal(valor: Decimal | None) -> str | None:
    """El texto posicional exacto de un `Decimal` (sin exponente); `None` queda `None`."""
    return None if valor is None else format(valor, "f")


def json_canonico(objeto: Any) -> bytes:
    """Claves ordenadas, sin espacios, UTF-8 sin escapar: la misma entrada, los mismos bytes."""
    return json.dumps(objeto, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def huella(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def documento(session: Session, version: models.Presupuesto) -> bytes:
    """El documento canónico de `version`, leído de la base (sin `commit` ni escritura)."""
    return json_canonico(estructura(session, version))


def estructura(session: Session, version: models.Presupuesto) -> dict[str, Any]:
    lista = version.lista_precios
    precios = {precio.insumo_id: precio for precio in lista.precios}
    origenes = origenes_efectivos(session, lista)
    referencias = dict(
        session.execute(
            select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
            .join(models.PrecioInsumo, models.PrecioInsumo.id == models.ReferenciaPrecio.precio_id)
            .where(models.PrecioInsumo.lista_id == lista.id)
        ).all()
    )
    renglones = sorted(version.partidas, key=lambda r: r.orden)
    citados = {r.item_computo_id for r in renglones}
    pendientes = [i for i in _items(session, version) if i.id not in citados]
    return {
        "formato": FORMATO,
        "version_formato": VERSION_FORMATO,
        "codigo": version.codigo,
        "fecha": version.fecha.isoformat(),
        "moneda": version.moneda,
        "moneda_proyecto": _moneda_del_proyecto(session, version),
        "proyecto": version.proyecto.nombre,
        "parametros": {
            "fcas": texto_decimal(version.fcas),
            "bono_alimentacion": texto_decimal(version.bono_alimentacion),
            "administracion": texto_decimal(version.administracion),
            "utilidad": texto_decimal(version.utilidad),
        },
        "lista": _lista(session, lista),
        "renglones": [_renglon(r) for r in renglones],
        "pendientes": [_item(i) for i in pendientes],
        "composiciones": _composiciones(session, version, lista, precios, origenes, referencias),
        "plan": _plan(session, version),
        "curva": [
            {
                "orden": p.orden,
                "periodo": p.periodo,
                "monto": texto_decimal(p.monto),
                "acumulado": texto_decimal(p.acumulado),
            }
            for p in sorted(version.curva, key=lambda p: p.orden)
        ],
        "hallazgos": _hallazgos(session, version),
    }


def _items(session: Session, version: models.Presupuesto) -> list[models.ItemComputo]:
    return list(
        session.scalars(
            select(models.ItemComputo)
            .where(models.ItemComputo.presupuesto_id == version.id)
            .order_by(models.ItemComputo.id)
        )
    )


def _moneda_del_proyecto(session: Session, version: models.Presupuesto) -> str | None:
    """La moneda del proyecto que regía en `version`, de `moneda_proyecto` (S1). Regla única:
    1) la última conversión (fila con `version_id`) hecha hasta esta versión, por orden de
    creación; 2) si no hay, la PRIMERA declaración sin versión, si ya existía a la fecha de la
    versión; 3) si no, ninguna. Así ni una conversión ni una declaración POSTERIOR cambian el
    documento de una versión ya sellada."""
    filas = list(
        session.scalars(
            select(models.MonedaProyecto)
            .where(models.MonedaProyecto.proyecto_id == version.proyecto_id)
            .order_by(models.MonedaProyecto.id)
        )
    )
    conversiones = [f for f in filas if f.version_id is not None and f.version_id <= version.id]
    if conversiones:
        return conversiones[-1].moneda
    declaraciones = [f for f in filas if f.version_id is None]
    if declaraciones and declaraciones[0].desde.date() <= version.fecha:
        return declaraciones[0].moneda
    return None


def _lista(session: Session, lista: models.ListaPrecios) -> dict[str, Any]:
    origen = session.get(models.ListaPreciosOrigen, lista.id)
    de_empresa = session.get(models.ListaEmpresa, lista.id)
    return {
        "nombre": lista.nombre,
        "moneda": lista.moneda,
        "fecha_vigencia": lista.fecha_vigencia.isoformat(),
        "origen": lista.origen,
        "alcance": origen.alcance if origen else models.ALCANCE_GLOBAL,
        "tasa": texto_decimal(origen.tasa) if origen else None,
        "fecha_tasa": origen.fecha_tasa.isoformat() if origen and origen.fecha_tasa else None,
        "empresa": (
            {"nombre": de_empresa.empresa_nombre, "rif": de_empresa.empresa_rif}
            if de_empresa
            else None
        ),
    }


def _item(item: models.ItemComputo) -> dict[str, Any]:
    return {
        "codigo_partida": item.codigo_partida,
        "descripcion": item.descripcion,
        "unidad": item.unidad,
        "unidad_original": item.unidad_original,
        "cantidad": texto_decimal(item.cantidad),
        "origen_id": item.origen_id,
        "origen_tipo": item.origen_tipo,
        "dominio": item.dominio,
        "regla": item.regla,
        "parametros": json.loads(item.parametros),
        "especificaciones": json.loads(item.especificaciones),
    }


def _renglon(renglon: models.PartidaPresupuestada) -> dict[str, Any]:
    return {
        "orden": renglon.orden,
        "item": _item(renglon.item_computo),
        "cantidad": texto_decimal(renglon.cantidad),
        "materiales": texto_decimal(renglon.materiales),
        "equipos": texto_decimal(renglon.equipos),
        "mano_obra": texto_decimal(renglon.mano_obra),
        "costo_directo": texto_decimal(renglon.costo_directo),
        "con_administracion": texto_decimal(renglon.con_administracion),
        "precio_unitario": texto_decimal(renglon.precio_unitario),
        "total": texto_decimal(renglon.total),
    }


def _composiciones(
    session: Session,
    version: models.Presupuesto,
    lista: models.ListaPrecios,
    precios: Mapping[int, models.PrecioInsumo],
    origenes: Mapping[int, Any],
    referencias: Mapping[int, str],
) -> list[dict[str, Any]]:
    filas = session.scalars(
        select(models.ComposicionVersion)
        .where(models.ComposicionVersion.presupuesto_id == version.id)
        .order_by(models.ComposicionVersion.id)
    )
    salida = []
    for fila in filas:
        lineas = []
        for linea in sorted(fila.lineas, key=lambda x: x.orden):
            precio = precios.get(linea.insumo_id) if linea.insumo_id is not None else None
            lineas.append(
                {
                    "orden": linea.orden,
                    "tipo": linea.tipo,
                    "insumo": linea.insumo.codigo if linea.insumo is not None else None,
                    "descripcion": linea.descripcion,
                    "unidad": linea.unidad,
                    "cantidad": texto_decimal(linea.cantidad),
                    "precio": texto_decimal(linea.precio),
                    "depreciacion": texto_decimal(linea.depreciacion),
                    "modalidad": linea.modalidad,
                    "referencia": referencias.get(precio.id, "") if precio else "",
                    "precio_origen": _precio_origen(session, lista, precio, origenes),
                }
            )
        salida.append(
            {
                "codigo_partida": fila.codigo_partida,
                "descripcion": fila.descripcion,
                "unidad": fila.unidad,
                "rendimiento": texto_decimal(fila.rendimiento),
                "lineas": lineas,
            }
        )
    return salida


def _precio_origen(
    session: Session,
    lista: models.ListaPrecios,
    precio: models.PrecioInsumo | None,
    origenes: Mapping[int, Any],
) -> dict[str, Any] | None:
    """El `precio_origen` de S1 (RF-65): moneda original, precio original, fecha, tasa con su
    fecha y su fuente, y si el precio es propio o heredado de la base."""
    if precio is None or precio.id not in origenes:
        return None
    o = origenes[precio.id]
    return {
        "moneda_original": o.moneda_original,
        "precio_original": texto_decimal(o.precio_original),
        "fecha_precio": o.fecha_precio.isoformat(),
        "tasa": texto_decimal(o.tasa),
        "fecha_tasa": o.fecha_tasa.isoformat() if o.fecha_tasa else None,
        "fuente_tasa": o.fuente_tasa,
        "fuente": o.fuente,
        "heredado": es_heredado(session, lista, precio),
    }


def _plan(session: Session, version: models.Presupuesto) -> list[dict[str, Any]]:
    filas = session.scalars(
        select(models.PlanVersion)
        .where(models.PlanVersion.presupuesto_id == version.id)
        .order_by(models.PlanVersion.periodo, models.PlanVersion.orden, models.PlanVersion.id)
    )
    return [
        {
            "periodo": f.periodo,
            "etiqueta": f.etiqueta,
            "orden": f.orden,
            "codigo_partida": f.codigo_partida,
            "fraccion": texto_decimal(f.fraccion),
        }
        for f in filas
    ]


def _hallazgos(session: Session, version: models.Presupuesto) -> list[dict[str, Any]]:
    filas = session.scalars(
        select(models.Hallazgo)
        .where(models.Hallazgo.presupuesto_id == version.id)
        .order_by(models.Hallazgo.id)
    )
    return [
        {
            "regla": h.regla,
            "severidad": h.severidad,
            "descripcion": h.descripcion,
            "impacto": texto_decimal(h.impacto),
            "origen_ids": json.loads(h.origen_ids),
            "valor_observado": texto_decimal(h.valor_observado),
            "valor_esperado": texto_decimal(h.valor_esperado),
        }
        for h in filas
    ]


# --- lectura --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RenglonDeclarado:
    """Lo que el emisor declaró para un renglón: se compara con el recálculo, no se cree."""

    orden: int
    codigo_partida: str
    cantidad: Decimal
    materiales: Decimal
    equipos: Decimal
    mano_obra: Decimal
    costo_directo: Decimal
    con_administracion: Decimal
    precio_unitario: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class LineaLeida:
    """Una línea de composición con lo que no cabe en el contrato: insumo, referencia, origen."""

    insumo: str | None
    referencia: str
    precio: Decimal
    precio_origen: Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class DocumentoLeido:
    codigo: str
    fecha: date
    moneda: str
    moneda_proyecto: str | None
    proyecto: str
    parametros: ParametrosCosto
    lista: Mapping[str, Any]
    items: tuple[ItemComputo, ...]
    pendientes: tuple[ItemComputo, ...]
    declarados: tuple[RenglonDeclarado, ...]
    composiciones: Mapping[str, ComposicionAPU]
    lineas: Mapping[str, tuple[LineaLeida, ...]]
    plan: tuple[PeriodoPlan, ...] | None
    curva: tuple[PuntoCurva, ...]
    hallazgos: tuple[Hallazgo, ...]


def _dec(texto: object, donde: str) -> Decimal:
    if not isinstance(texto, str) or not PATRON_CIFRA.fullmatch(texto):
        raise DocumentoInvalido(f"{donde}: cifra fuera del patron estricto: {str(texto)[:30]!r}")
    return Decimal(texto)


def _dec_o_nulo(texto: object, donde: str) -> Decimal | None:
    return None if texto is None else _dec(texto, donde)


def _campo(objeto: Mapping[str, Any], clave: str, tipo: type, donde: str) -> Any:
    valor = objeto.get(clave)
    if not isinstance(valor, tipo):
        raise DocumentoInvalido(f"{donde}: falta '{clave}' o no es {tipo.__name__}")
    return valor


def contar_filas(objeto: Mapping[str, Any]) -> int:
    """Renglones más líneas de composición del documento, sin validarlo (para el límite de
    S3 §8.4 antes de leerlo entero)."""
    renglones = objeto.get("renglones")
    composiciones = objeto.get("composiciones")
    total = len(renglones) if isinstance(renglones, list) else 0
    if isinstance(composiciones, list):
        total += sum(
            len(c.get("lineas", ()))
            for c in composiciones
            if isinstance(c, dict) and isinstance(c.get("lineas", ()), list)
        )
    return total


def _contrato_item(datos: Mapping[str, Any], donde: str) -> ItemComputo:
    try:
        return ItemComputo(
            codigo_partida=_campo(datos, "codigo_partida", str, donde),
            descripcion=_campo(datos, "descripcion", str, donde),
            unidad=_campo(datos, "unidad", str, donde),
            cantidad=_dec(datos.get("cantidad"), f"{donde}.cantidad"),
            origen_id=_campo(datos, "origen_id", str, donde),
            origen_tipo=OrigenTipo(_campo(datos, "origen_tipo", str, donde)),
            dominio=Dominio(_campo(datos, "dominio", str, donde)),
            regla=datos.get("regla"),
            parametros={
                k: _dec(v, f"{donde}.parametros.{k}")
                for k, v in _campo(datos, "parametros", dict, donde).items()
            },
            especificaciones=_campo(datos, "especificaciones", dict, donde),
        )
    except (ValueError, TypeError) as error:
        if isinstance(error, DocumentoInvalido):
            raise
        raise DocumentoInvalido(f"{donde}: {error}") from None


def _composicion(datos: Mapping[str, Any]) -> tuple[ComposicionAPU, tuple[LineaLeida, ...]]:
    """La composición y los datos de sus líneas, alineados con `(*materiales, *equipos,
    *mano_obra)` (el orden de `ComposicionAPU`, como `_insumos_alineados` de S1)."""
    donde = f"composicion {datos.get('codigo_partida')!r}"
    materiales: list[tuple[LineaMaterial, LineaLeida]] = []
    equipos: list[tuple[LineaEquipo, LineaLeida]] = []
    mano_obra: list[tuple[LineaManoObra, LineaLeida]] = []
    for numero, linea in enumerate(_campo(datos, "lineas", list, donde)):
        aqui = f"{donde}, linea {numero}"
        tipo = _campo(linea, "tipo", str, aqui)
        cantidad = _dec(linea.get("cantidad"), f"{aqui}.cantidad")
        precio = _dec(linea.get("precio"), f"{aqui}.precio")
        descripcion = _campo(linea, "descripcion", str, aqui)
        extra = LineaLeida(
            linea.get("insumo"), linea.get("referencia", ""), precio, linea.get("precio_origen")
        )
        if tipo == models.TipoInsumo.MATERIAL:
            material = LineaMaterial(descripcion, linea.get("unidad") or "", cantidad, precio)
            materiales.append((material, extra))
        elif tipo == models.TipoInsumo.EQUIPO:
            dep = _dec(linea.get("depreciacion"), f"{aqui}.depreciacion")
            equipos.append((LineaEquipo(descripcion, cantidad, precio, dep), extra))
        elif tipo == models.TipoInsumo.MANO_OBRA:
            modalidad = linea.get("modalidad") or "jornal"
            mano_obra.append((LineaManoObra(descripcion, cantidad, precio, modalidad), extra))
        else:
            raise DocumentoInvalido(f"{aqui}: tipo de insumo desconocido {tipo!r}")
    composicion = ComposicionAPU(
        codigo_partida=_campo(datos, "codigo_partida", str, donde),
        descripcion=_campo(datos, "descripcion", str, donde),
        unidad=_campo(datos, "unidad", str, donde),
        rendimiento=_dec(datos.get("rendimiento"), f"{donde}.rendimiento"),
        materiales=tuple(m for m, _ in materiales),
        equipos=tuple(e for e, _ in equipos),
        mano_obra=tuple(o for o, _ in mano_obra),
    )
    return composicion, tuple(x for _, x in (*materiales, *equipos, *mano_obra))


def _plan_leido(filas: Sequence[Mapping[str, Any]]) -> tuple[PeriodoPlan, ...] | None:
    if not filas:
        return None
    periodos: dict[int, tuple[str, list[tuple[str, Decimal]]]] = {}
    for fila in filas:
        etiqueta, reparto = periodos.setdefault(fila["periodo"], (fila["etiqueta"], []))
        if fila.get("codigo_partida") is not None and fila.get("fraccion") is not None:
            reparto.append((fila["codigo_partida"], _dec(fila["fraccion"], "plan.fraccion")))
    return tuple((etiqueta, tuple(reparto)) for etiqueta, reparto in periodos.values())


def leer(objeto: Mapping[str, Any]) -> DocumentoLeido:
    """`DocumentoLeido` de un documento canónico ya leído; `DocumentoInvalido` si no tiene la
    forma de `silice-presupuesto` v1 o trae una cifra fuera del patrón estricto."""
    if not isinstance(objeto, Mapping) or objeto.get("formato") != FORMATO:
        raise DocumentoInvalido("no es un presupuesto de Silice (formato)")
    if objeto.get("version_formato") != VERSION_FORMATO:
        raise DocumentoInvalido(f"version_formato {objeto.get('version_formato')!r} desconocida")
    parametros = _campo(objeto, "parametros", dict, "parametros")
    renglones = _campo(objeto, "renglones", list, "documento")
    items, declarados = [], []
    for numero, renglon in enumerate(renglones):
        aqui = f"renglon {numero}"
        items.append(_contrato_item(_campo(renglon, "item", dict, aqui), f"{aqui}.item"))
        declarados.append(
            RenglonDeclarado(
                orden=_campo(renglon, "orden", int, aqui),
                codigo_partida=items[-1].codigo_partida,
                cantidad=_dec(renglon.get("cantidad"), f"{aqui}.cantidad"),
                materiales=_dec(renglon.get("materiales"), f"{aqui}.materiales"),
                equipos=_dec(renglon.get("equipos"), f"{aqui}.equipos"),
                mano_obra=_dec(renglon.get("mano_obra"), f"{aqui}.mano_obra"),
                costo_directo=_dec(renglon.get("costo_directo"), f"{aqui}.costo_directo"),
                con_administracion=_dec(
                    renglon.get("con_administracion"), f"{aqui}.con_administracion"
                ),
                precio_unitario=_dec(renglon.get("precio_unitario"), f"{aqui}.precio_unitario"),
                total=_dec(renglon.get("total"), f"{aqui}.total"),
            )
        )
    composiciones, lineas = {}, {}
    for datos in _campo(objeto, "composiciones", list, "documento"):
        composicion, extra = _composicion(datos)
        composiciones[composicion.codigo_partida] = composicion
        lineas[composicion.codigo_partida] = extra
    try:
        fecha = date.fromisoformat(_campo(objeto, "fecha", str, "documento"))
        costo = ParametrosCosto(
            fcas=_dec(parametros.get("fcas"), "parametros.fcas"),
            bono_alimentacion=_dec(parametros.get("bono_alimentacion"), "parametros.bono"),
            administracion=_dec(parametros.get("administracion"), "parametros.administracion"),
            utilidad=_dec(parametros.get("utilidad"), "parametros.utilidad"),
        )
    except (ValueError, InvalidOperation) as error:
        if isinstance(error, DocumentoInvalido):
            raise
        raise DocumentoInvalido(f"documento: {error}") from None
    return DocumentoLeido(
        codigo=_campo(objeto, "codigo", str, "documento"),
        fecha=fecha,
        moneda=_campo(objeto, "moneda", str, "documento"),
        moneda_proyecto=objeto.get("moneda_proyecto"),
        proyecto=_campo(objeto, "proyecto", str, "documento"),
        parametros=costo,
        lista=_campo(objeto, "lista", dict, "documento"),
        items=tuple(items),
        pendientes=tuple(
            _contrato_item(p, f"pendiente {n}")
            for n, p in enumerate(_campo(objeto, "pendientes", list, "documento"))
        ),
        declarados=tuple(declarados),
        composiciones=composiciones,
        lineas=lineas,
        plan=_plan_leido(_campo(objeto, "plan", list, "documento")),
        curva=tuple(
            PuntoCurva(
                periodo=_campo(p, "periodo", str, "curva"),
                monto=_dec(p.get("monto"), "curva.monto"),
                acumulado=_dec(p.get("acumulado"), "curva.acumulado"),
            )
            for p in _campo(objeto, "curva", list, "documento")
        ),
        hallazgos=tuple(
            Hallazgo(
                regla=_campo(h, "regla", str, "hallazgo"),
                severidad=Severidad(_campo(h, "severidad", int, "hallazgo")),
                descripcion=_campo(h, "descripcion", str, "hallazgo"),
                impacto=_dec_o_nulo(h.get("impacto"), "hallazgo.impacto"),
                origen_ids=tuple(h.get("origen_ids", ())),
                valor_observado=_dec_o_nulo(h.get("valor_observado"), "hallazgo.observado"),
                valor_esperado=_dec_o_nulo(h.get("valor_esperado"), "hallazgo.esperado"),
            )
            for h in _campo(objeto, "hallazgos", list, "documento")
        ),
    )
