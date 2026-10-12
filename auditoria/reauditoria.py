"""La reauditoría en memoria de un documento ajeno (spec S3 §9 paso 3 y §10; RF-87, RF-88).

La comparten la vista de quien revisa (`ui/revision.py`) y la ruta `POST /v1/auditorias`
(`api/rutas/auditorias.py`): por eso vive en un paquete aparte, fuera del núcleo, que importa
`core`, `adapters.espacio` y `paquete` y que **ni `ui` ni `api` ni el núcleo tocan al revés**
(RP8-6; el spec la ponía en `ui/revision.py`, pero la API no puede importar `ui`).

NUNCA confía en lo que trae el documento: recalcula cada precio unitario con el motor desde las
composiciones y los parámetros (no se creen los precios ni los totales escritos), corre `REGLAS` y
las reglas externas del contexto «reauditoría» (maestro §3.3): R8-R10 y R15 con el anexo de
espacio; R11-R12 con el `precio_origen` del documento, **a la fecha que se le da** (la de emisión
en un paquete, la del cuerpo en la API; nunca el reloj), contra la referencia MaPreX de quien
revisa; R13-R14 con el anexo de control **solo si hay servicio de S2 que lo recompute** (el puente
no existe todavía: queda apagada y se declara en `avisos`). R16 no corre aquí. Toda reevaluación
es en memoria: no reescribe nada.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as TiempoAgotado
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from adapters.espacio import Espacio
from adapters.espacio.planos.geometria_plano import reglas_plano
from adapters.espacio.reglas import reglas_espacio
from adapters.espacio.serie import espacio_desde_objeto
from core.budget import canonico
from core.budget.presupuesto import ResultadoElaboracion, elaborar
from core.catalog.empresa import PLAZO_VIGENCIA_DIAS, RANGO_INFERIOR, RANGO_SUPERIOR
from core.contracts.verificacion import Hallazgo, ReglaVerificacion
from core.verification import REGLAS
from core.verification.precios import (
    InstantaneaPrecios,
    PartidaPrecios,
    PrecioAuditado,
    reglas_precios,
)
from paquete.formato import LIMITE_FILAS, PaqueteRechazado
from seguridad.json_estricto import a_decimal, leer_json

__all__ = [
    "LIMITE_SEGUNDOS",
    "NOMBRE_CONTROL",
    "NOMBRE_ESPACIO",
    "DiferenciaDeclarada",
    "Reauditoria",
    "ReferenciaDeMercado",
    "Servicios",
    "instantanea_del_documento",
    "leer_documento",
    "leer_documento_json",
    "reauditar",
]

LIMITE_SEGUNDOS = 60
NOMBRE_ESPACIO = "anexos/espacio.json"
NOMBRE_CONTROL = "anexos/control.json"

#: `erosion(precio, moneda_lista, moneda_original, precio_original, tasa_del_precio, tasa_de_hoy)`
#: es la de S1 §5.3: por unidad y en la moneda de la lista; `None` sin tasa; 0 si el original es
#: USD.
Erosion = Callable[
    [Decimal, str, str, Decimal, "Decimal | None", "Decimal | None"], "Decimal | None"
]

#: Lo que un JSON bien formado pero con la forma equivocada puede lanzar al leerlo: nunca llega a
#: la pantalla ni a la API como una traza.
_FORMA_EQUIVOCADA = (KeyError, TypeError, AttributeError, IndexError, InvalidOperation)


@dataclass(frozen=True, slots=True)
class ReferenciaDeMercado:
    """El precio MaPreX de la referencia de un insumo en la instalación que revisa."""

    codigo: str
    precio: Decimal
    moneda: str
    tasa: Decimal | None  # a la fecha de la referencia; None en USD


@dataclass(frozen=True, slots=True)
class Servicios:
    """Lo que la reauditoría necesita de la base de quien revisa. `auditoria.servicios` lo arma
    con S1 y S2; las pruebas, con funciones a mano."""

    referencia_de: Callable[[str], ReferenciaDeMercado | None] = lambda codigo: None
    tasa_en: Callable[[date], Decimal | None] = lambda fecha: None
    erosion: Erosion = lambda precio, lista, original, p_original, t0, t1: Decimal(0)
    reglas_de_control: (
        Callable[[canonico.DocumentoLeido, Mapping[str, Any], date], Sequence[ReglaVerificacion]]
        | None
    ) = None
    rango: tuple[Decimal, Decimal] = (RANGO_INFERIOR, RANGO_SUPERIOR)
    plazo_vigencia_dias: int = PLAZO_VIGENCIA_DIAS


def leer_documento(archivos: Mapping[str, bytes]) -> canonico.DocumentoLeido:
    """`presupuesto.json` con el lector estricto y el tope de filas (S3 §8.4)."""
    return leer_documento_json(archivos["presupuesto.json"])


def leer_documento_json(datos: bytes) -> canonico.DocumentoLeido:
    objeto = leer_json(datos)
    if canonico.contar_filas(objeto) > LIMITE_FILAS:
        raise PaqueteRechazado(
            f"El presupuesto trae más de {LIMITE_FILAS} renglones y líneas de composición."
        )
    return canonico.leer(objeto)


def _insumos_alineados(ids: Mapping[str, int], lineas) -> tuple[int | None, ...]:
    return tuple(ids.get(extra.insumo) if extra.insumo else None for extra in lineas)


def instantanea_del_documento(
    doc: canonico.DocumentoLeido, servicios: Servicios, fecha_evaluacion: date
) -> InstantaneaPrecios:
    """R11 y R12 de un documento ajeno, en memoria: los precios que usa, con su `precio_origen`
    (S1), contra la referencia de quien revisa y a `fecha_evaluacion`."""
    moneda = str(doc.lista.get("moneda", doc.moneda))
    tasa_evaluacion = servicios.tasa_en(fecha_evaluacion)
    ids: dict[str, int] = {}
    precios: dict[str, PrecioAuditado] = {}
    for codigo, composicion in doc.composiciones.items():
        todas = [*composicion.materiales, *composicion.equipos, *composicion.mano_obra]
        for linea, extra in zip(todas, doc.lineas[codigo], strict=True):
            if extra.insumo is None or extra.insumo in precios:
                continue
            ids[extra.insumo] = len(ids) + 1
            origen = extra.precio_origen or {}
            precio = extra.precio
            fecha_precio = date.fromisoformat(
                origen.get("fecha_precio") or str(doc.lista["fecha_vigencia"])
            )
            tasa = a_decimal(origen["tasa"]) if origen.get("tasa") else None
            fecha_tasa = (
                date.fromisoformat(origen["fecha_tasa"]) if origen.get("fecha_tasa") else None
            )
            a_su_fecha = (
                None if tasa is not None or moneda == "USD" else servicios.tasa_en(fecha_precio)
            )
            moneda_original = origen.get("moneda_original") or moneda
            precio_original = (
                a_decimal(origen["precio_original"]) if origen.get("precio_original") else precio
            )
            referencia = servicios.referencia_de(extra.referencia) if extra.referencia else None
            precios[extra.insumo] = PrecioAuditado(
                insumo_id=ids[extra.insumo],
                codigo=extra.insumo,
                descripcion=linea.descripcion,
                precio=precio,
                moneda=moneda,
                moneda_original=moneda_original,
                precio_original=precio_original,
                fecha_precio=fecha_precio,
                tasa=tasa,
                fecha_tasa=fecha_tasa,
                fuente_tasa=origen.get("fuente_tasa") or "",
                tasa_a_su_fecha=a_su_fecha,
                referencia=referencia.precio if referencia else None,
                moneda_referencia=referencia.moneda if referencia else moneda,
                tasa_referencia=referencia.tasa if referencia else None,
                codigo_referencia=extra.referencia or "",
                erosion=servicios.erosion(
                    precio,
                    moneda,
                    moneda_original,
                    precio_original,
                    tasa or a_su_fecha,
                    tasa_evaluacion,
                ),
                heredado=origen.get("heredado"),
            )
    cantidades: dict[str, Decimal] = {}
    for item in doc.items:
        previa = cantidades.get(item.codigo_partida, Decimal(0))
        cantidades[item.codigo_partida] = previa + item.cantidad
    partidas = tuple(
        PartidaPrecios(c, q, doc.composiciones[c], _insumos_alineados(ids, doc.lineas[c]))
        for c, q in cantidades.items()
    )
    return InstantaneaPrecios(
        fecha_evaluacion=fecha_evaluacion,
        moneda=doc.moneda,
        precios=tuple(sorted(precios.values(), key=lambda p: p.insumo_id)),
        tasa_evaluacion=tasa_evaluacion,
        rango_inferior=servicios.rango[0],
        rango_superior=servicios.rango[1],
        plazo_vigencia_dias=servicios.plazo_vigencia_dias,
        partidas=partidas,
        parametros=doc.parametros,
    )


@dataclass(frozen=True, slots=True)
class DiferenciaDeclarada:
    """Un precio unitario o un total declarado que no cuadra con el recálculo, con su monto."""

    codigo_partida: str
    campo: str  # precio_unitario | total
    declarado: Decimal
    recalculado: Decimal
    monto: Decimal  # lo declarado menos lo recalculado, a la cantidad del renglón


@dataclass(frozen=True, slots=True)
class Reauditoria:
    documento: canonico.DocumentoLeido
    resultado: ResultadoElaboracion | None
    contextos: tuple[str, ...]
    fecha_evaluacion: date | None = None
    nuevos: tuple[Hallazgo, ...] = ()  # el emisor no los declaró
    ya_no: tuple[Hallazgo, ...] = ()  # los declaró y ya no aparecen
    comunes: tuple[Hallazgo, ...] = ()
    diferencias: tuple[DiferenciaDeclarada, ...] = ()
    total_recalculado: Decimal | None = None
    no_termino: bool = False
    avisos: tuple[str, ...] = field(default=())


def _clave(h: Hallazgo) -> tuple:
    return (h.regla, int(h.severidad), tuple(h.origen_ids), h.descripcion)


def _separar(
    declarados: Sequence[Hallazgo], propios: Sequence[Hallazgo]
) -> tuple[list[Hallazgo], list[Hallazgo], list[Hallazgo]]:
    """`(nuevos, ya_no, comunes)` como multiconjuntos: dos hallazgos idénticos cuentan dos veces."""
    pendientes = Counter(_clave(h) for h in declarados)
    nuevos, comunes = [], []
    for h in propios:
        if pendientes[_clave(h)] > 0:
            pendientes[_clave(h)] -= 1
            comunes.append(h)
        else:
            nuevos.append(h)
    ya_no = []
    for h in declarados:
        if pendientes[_clave(h)] > 0:
            pendientes[_clave(h)] -= 1
            ya_no.append(h)
    return nuevos, ya_no, comunes


def _reglas_externas(
    doc: canonico.DocumentoLeido,
    espacio_json: bytes | None,
    control_json: bytes | None,
    servicios: Servicios,
    fecha_evaluacion: date,
) -> tuple[list[ReglaVerificacion], list[str], list[str]]:
    reglas: list[ReglaVerificacion] = []
    contextos = ["R1-R7"]
    avisos: list[str] = []
    if espacio_json is not None:
        espacio: Espacio = espacio_desde_objeto(leer_json(espacio_json), a_decimal)
        reglas += [*reglas_espacio(espacio), *reglas_plano(espacio)]
        contextos += ["R8-R10", "R15"]
    reglas += list(reglas_precios(instantanea_del_documento(doc, servicios, fecha_evaluacion)))
    contextos.append("R11-R12")
    if control_json is not None:
        if servicios.reglas_de_control is None:
            avisos.append(
                "El paquete trae anexos/control.json, pero esta instalación todavía no puede "
                "recomputar R13 y R14 desde un anexo: esas dos reglas no se corrieron."
            )
        else:
            reglas += list(
                servicios.reglas_de_control(doc, leer_json(control_json), fecha_evaluacion)
            )
            contextos.append("R13-R14")
    return reglas, contextos, avisos


def _trabajo(
    doc: canonico.DocumentoLeido,
    servicios: Servicios,
    fecha_evaluacion: date,
    espacio_json: bytes | None,
    control_json: bytes | None,
) -> Reauditoria:
    externas, contextos, avisos = _reglas_externas(
        doc, espacio_json, control_json, servicios, fecha_evaluacion
    )
    resultado = elaborar(
        [*doc.items, *doc.pendientes],
        doc.composiciones,
        doc.parametros,
        codigo=doc.codigo,
        fecha=doc.fecha,
        moneda=doc.moneda,
        plan=list(doc.plan) if doc.plan else None,
        reglas=(*REGLAS, *externas),
    )
    recalculado = {
        (p.item.codigo_partida, p.item.origen_id): p for p in resultado.presupuesto.partidas
    }
    diferencias: list[DiferenciaDeclarada] = []
    for d, item in zip(doc.declarados, doc.items, strict=True):
        real = recalculado[(item.codigo_partida, item.origen_id)]
        for campo, declarado, calculado in (
            ("precio_unitario", d.precio_unitario, real.resultado.precio_unitario),
            ("total", d.total, real.total),
        ):
            if declarado != calculado:
                por = d.cantidad if campo == "precio_unitario" else 1
                diferencias.append(
                    DiferenciaDeclarada(
                        item.codigo_partida,
                        campo,
                        declarado,
                        calculado,
                        (declarado - calculado) * por,
                    )
                )
    nuevos, ya_no, comunes = _separar(doc.hallazgos, resultado.informe.hallazgos)
    return Reauditoria(
        documento=doc,
        resultado=resultado,
        contextos=tuple(contextos),
        fecha_evaluacion=fecha_evaluacion,
        nuevos=tuple(nuevos),
        ya_no=tuple(ya_no),
        comunes=tuple(comunes),
        diferencias=tuple(diferencias),
        total_recalculado=resultado.presupuesto.total,
        avisos=tuple(avisos),
    )


def reauditar(
    doc: canonico.DocumentoLeido,
    servicios: Servicios,
    fecha_evaluacion: date,
    *,
    espacio_json: bytes | None = None,
    control_json: bytes | None = None,
    tiempo_maximo: float = LIMITE_SEGUNDOS,
) -> Reauditoria:
    """La reauditoría de `doc` a `fecha_evaluacion` (R12; la de emisión en un paquete, la que
    manda el cuerpo en la API). Si pasa de `tiempo_maximo` segundos se corta y se informa «no
    terminó» (S3 §8.4); el hilo de trabajo no se puede matar, pero ya nadie espera su resultado.
    Un documento con la forma equivocada es `PaqueteRechazado`, no una traza."""
    ejecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="reauditoria")
    futuro = ejecutor.submit(_trabajo, doc, servicios, fecha_evaluacion, espacio_json, control_json)
    try:
        return futuro.result(timeout=tiempo_maximo)
    except TiempoAgotado:
        return Reauditoria(
            documento=doc,
            resultado=None,
            contextos=(),
            fecha_evaluacion=fecha_evaluacion,
            no_termino=True,
            avisos=(f"La reauditoría no terminó en {tiempo_maximo:g} s.",),
        )
    except _FORMA_EQUIVOCADA as error:
        raise PaqueteRechazado(
            f"El documento o su anexo no tiene la forma esperada ({type(error).__name__}: "
            f"{error}). No se pudo reauditar."
        ) from None
    finally:
        ejecutor.shutdown(wait=False, cancel_futures=True)
