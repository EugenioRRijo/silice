"""Alertas de precio del libro, en su moneda y en bolívares (spec 1.5 §4).

Para cada insumo de INSUMOS se producen, cuando aplican, cuatro clases de alerta:

1. **Sin fuente** (`TIPO_SIN_FUENTE`): la columna FUENTE está vacía o dice "REFERENCIAL…" (o "POR
   COTIZAR", que tampoco es una fuente). Un precio sin fuente no se puede rastrear.
2. **Base de la empresa** (`TIPO_EMPRESA`): la instalación tiene un precio propio con el mismo
   código y la diferencia alcanza o supera el umbral (en la moneda del libro).
3. **Otra versión** (`TIPO_VERSION`): se procesó otra versión del mismo libro (por ejemplo B-1 y
   B-2) y el precio del código cambió, o el código no estaba en la otra.
4. **USD-Bs** (`TIPO_BS`): el equivalente en bolívares a la tasa del BCV de la fecha del libro y a
   la de la fecha de devolución, con la variación. Una fila por insumo: es la tabla de conversión
   de la hoja ALERTAS USD-Bs, y su mensaje dice si la variación pasa del umbral.

**Nunca se inventa una tasa** (F-D8): las tasas las da la instalación por `ContextoPrecios.tasa_en`
(en producción, `auditoria.servicios`); un día sin tasa deja `tasa=None`, `precio_bs=None` y el
mensaje "no contrastable: la instalación no tiene la tasa del BCV de <fecha>". Sin contexto (por
ejemplo, la verificación local sin base), todas las alertas en Bs son "no contrastable".

`variacion` es una **fracción** (0,05 = 5 %), como el umbral, sin redondear: se redondea solo al
presentar (NORMAS §2.3). Las conversiones entre monedas son las del catálogo
(`core.catalog.moneda.convertir`, con sus `MONEDAS` Bs y USD).

Este módulo no lee el reloj: las dos fechas las da quien llama (`fusion.proceso`).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from adapters.hoja_empresa.modelo import FilaAlerta, InsumoLeido, LibroLeido
from adapters.hoja_empresa.perfil import normalizar
from core.catalog.moneda import MONEDAS, convertir
from fusion.mapeo import moneda_del_libro

__all__ = [
    "TIPO_BS",
    "TIPO_EMPRESA",
    "TIPO_SIN_FUENTE",
    "TIPO_VERSION",
    "UMBRAL_POR_DEFECTO",
    "ContextoPrecios",
    "alertas_de_precios",
]

TIPO_SIN_FUENTE = "sin fuente"
TIPO_EMPRESA = "base de la empresa"
TIPO_VERSION = "otra versión"
TIPO_BS = "USD-Bs"
_ORDEN_TIPOS = {TIPO_SIN_FUENTE: 0, TIPO_EMPRESA: 1, TIPO_VERSION: 2, TIPO_BS: 3}

#: Umbral de variación que dispara la alerta (spec §4: 5 % por defecto, configurable).
UMBRAL_POR_DEFECTO = Decimal("0.05")

#: Textos de FUENTE que no son una fuente. SUPUESTO_DECLARADO: el spec nombra "REFERENCIAL"; los
#: libros recibidos escriben "REFERENCIAL — ajustar" y "POR COTIZAR", que dicen lo mismo.
_NO_ES_FUENTE = ("referencial", "por cotizar")

_RE_CODIGO = re.compile(r"^([A-Za-z]+)-?(\d+)")


@dataclass(frozen=True, slots=True)
class ContextoPrecios:
    """Los servicios de la instalación que las alertas consultan, inyectados (como los `Servicios`
    de la reauditoría): así `fusion` no abre la base y la verificación local corre sin ella.

    `tasa_en(fecha)` es la tasa Bs/USD del BCV aplicable a esa fecha, o `None` si la instalación no
    la tiene. `precio_propio(codigo)` es `(precio, fecha, moneda)` del precio de la empresa con ese
    código en la instalación, o `None`. Un servicio ausente (`None`) equivale a no tener el dato.
    """

    tasa_en: Callable[[date], Decimal | None] | None = None
    precio_propio: Callable[[str], tuple[Decimal, date, str] | None] | None = None
    umbral: Decimal = UMBRAL_POR_DEFECTO


def _texto(valor: Decimal) -> str:
    return format(valor, "f")


def _pct(fraccion: Decimal) -> str:
    return f"{fraccion * 100:+.2f} %"


def _variacion(nuevo: Decimal, anterior: Decimal) -> Decimal | None:
    """(nuevo − anterior) ÷ anterior; `None` si el anterior es 0 (no hay variación relativa)."""
    if anterior == 0:
        return None
    return (nuevo - anterior) / anterior


def _sin_fuente(fuente: str) -> bool:
    texto = normalizar(fuente)
    return not texto or texto.startswith(_NO_ES_FUENTE)


def _fila(
    insumo: InsumoLeido,
    tipo: str,
    moneda: str,
    fecha: date | None,
    mensaje: str,
    *,
    tasa: Decimal | None = None,
    precio_bs: Decimal | None = None,
    variacion: Decimal | None = None,
) -> FilaAlerta:
    return FilaAlerta(
        codigo=insumo.codigo,
        descripcion=insumo.descripcion,
        tipo=tipo,
        moneda=moneda,
        precio=insumo.precio,
        fecha=fecha.isoformat() if fecha else "",
        fuente=insumo.fuente,
        tasa=tasa,
        precio_bs=precio_bs,
        variacion=variacion,
        mensaje=mensaje,
    )


def _tasa(contexto: ContextoPrecios | None, fecha: date | None) -> Decimal | None:
    if contexto is None or contexto.tasa_en is None or fecha is None:
        return None
    return contexto.tasa_en(fecha)


def _alerta_empresa(
    insumo: InsumoLeido,
    moneda: str,
    fecha_libro: date | None,
    contexto: ContextoPrecios,
) -> FilaAlerta | None:
    """Contra el precio propio de la instalación, llevado a la moneda del libro.

    Si las monedas difieren, el precio propio se convierte con la tasa de SU fecha (la del día en
    que la empresa lo fijó); sin esa tasa la comparación no es contrastable y se dice.
    """
    if contexto.precio_propio is None:
        return None
    propio = contexto.precio_propio(insumo.codigo)
    if propio is None:
        return None
    precio, fecha, moneda_propia = propio
    referencia = f"precio propio de la instalación {_texto(precio)} {moneda_propia} del {fecha}"
    if moneda_propia != moneda:
        if moneda_propia not in MONEDAS or moneda not in MONEDAS:
            return _fila(
                insumo,
                TIPO_EMPRESA,
                moneda,
                fecha_libro,
                f"no contrastable: {referencia}; Silice solo convierte entre {' y '.join(MONEDAS)}",
            )
        tasa = _tasa(contexto, fecha)
        if tasa is None or tasa == 0:
            return _fila(
                insumo,
                TIPO_EMPRESA,
                moneda,
                fecha_libro,
                f"no contrastable: {referencia}; la instalación no tiene la tasa del BCV de "
                f"{fecha.isoformat()} para llevarlo a {moneda}",
            )
        precio = convertir(precio, moneda_propia, moneda, tasa)
        referencia += f" ({_texto(precio)} {moneda} a la tasa {_texto(tasa)})"
    variacion = _variacion(insumo.precio, precio)
    if variacion is None or abs(variacion) < contexto.umbral:
        return None
    return _fila(
        insumo,
        TIPO_EMPRESA,
        moneda,
        fecha_libro,
        f"el libro usa {_texto(insumo.precio)} {moneda}; {referencia}: {_pct(variacion)}, pasa "
        f"del umbral de {_pct(contexto.umbral).lstrip('+')}",
        variacion=variacion,
    )


def _alertas_version(
    libro: LibroLeido, otro: LibroLeido, moneda: str, fecha_libro: date | None
) -> list[FilaAlerta]:
    """Cambios de precio por código contra la otra versión del libro, y códigos nuevos."""
    salida: list[FilaAlerta] = []
    for insumo in libro.insumos:
        anterior = otro.insumo(insumo.codigo)
        if anterior is None:
            salida.append(
                _fila(
                    insumo,
                    TIPO_VERSION,
                    moneda,
                    fecha_libro,
                    f"{insumo.codigo} no está en la otra versión ({otro.nombre})",
                )
            )
            continue
        if anterior.precio == insumo.precio:
            continue
        variacion = _variacion(insumo.precio, anterior.precio)
        cambio = f": {_pct(variacion)}" if variacion is not None else ""
        salida.append(
            _fila(
                insumo,
                TIPO_VERSION,
                moneda,
                fecha_libro,
                f"en la otra versión ({otro.nombre}, {anterior.celda}) costaba "
                f"{_texto(anterior.precio)} {moneda}; en esta ({insumo.celda}) "
                f"{_texto(insumo.precio)}{cambio}",
                variacion=variacion,
            )
        )
    return salida


def _faltan(fechas: Iterable[tuple[date | None, Decimal | None]]) -> str:
    textos = []
    for fecha, tasa in fechas:
        if tasa is None:
            textos.append("la fecha del libro (no legible)" if fecha is None else fecha.isoformat())
    return " ni la de ".join(textos)


def _alerta_bs(
    insumo: InsumoLeido,
    moneda: str,
    fecha_libro: date | None,
    fecha_devolucion: date,
    t_libro: Decimal | None,
    t_devolucion: Decimal | None,
    umbral: Decimal,
) -> FilaAlerta:
    """El equivalente en Bs a las dos fechas. `tasa` y `precio_bs` son los de la fecha de
    devolución (lo que vale hoy); el mensaje da también el de la fecha del libro.

    En un libro en dólares la variación es la del precio en Bs; en un libro en bolívares, la del
    valor en dólares (lo que el monto en Bs pierde o gana frente al dólar).
    """
    if fecha_libro is None or not t_libro or not t_devolucion:
        return _fila(
            insumo,
            TIPO_BS,
            moneda,
            fecha_libro,
            "no contrastable: la instalación no tiene la tasa del BCV de "
            + _faltan(((fecha_libro, t_libro), (fecha_devolucion, t_devolucion))),
        )
    if moneda == "Bs":
        antes = convertir(insumo.precio, "Bs", "USD", t_libro)
        ahora = convertir(insumo.precio, "Bs", "USD", t_devolucion)
        precio_bs = insumo.precio
        detalle = (
            f"{_texto(antes)} USD al {fecha_libro} (tasa {_texto(t_libro)}) y "
            f"{_texto(ahora)} USD al {fecha_devolucion} (tasa {_texto(t_devolucion)})"
        )
    else:
        antes = convertir(insumo.precio, "USD", "Bs", t_libro)
        ahora = convertir(insumo.precio, "USD", "Bs", t_devolucion)
        precio_bs = ahora
        detalle = (
            f"{_texto(antes)} Bs al {fecha_libro} (tasa {_texto(t_libro)}) y "
            f"{_texto(ahora)} Bs al {fecha_devolucion} (tasa {_texto(t_devolucion)})"
        )
    variacion = _variacion(ahora, antes)
    pasa = variacion is not None and abs(variacion) >= umbral
    juicio = "pasa del umbral" if pasa else "dentro del umbral"
    cambio = _pct(variacion) if variacion is not None else "sin variación relativa"
    return _fila(
        insumo,
        TIPO_BS,
        moneda,
        fecha_libro,
        f"{detalle}: {cambio}, {juicio} de {_pct(umbral).lstrip('+')}",
        tasa=t_devolucion,
        precio_bs=precio_bs,
        variacion=variacion,
    )


def _clave_codigo(codigo: str) -> tuple[str, int, str]:
    """MT-2 antes que MT-10: orden natural por prefijo y número."""
    m = _RE_CODIGO.match(codigo)
    if m is None:
        return (codigo, -1, codigo)
    return (m.group(1).upper(), int(m.group(2)), codigo)


def alertas_de_precios(
    libro: LibroLeido,
    fecha_libro: date | None,
    fecha_devolucion: date,
    contexto: ContextoPrecios | None,
    otro: LibroLeido | None = None,
) -> tuple[FilaAlerta, ...]:
    """Las alertas de la hoja ALERTAS USD-Bs, ordenadas por tipo, por código (orden natural) y por
    mensaje: el mismo libro con el mismo contexto da siempre las mismas filas en el mismo orden.

    `fecha_libro` puede ser `None` si la PORTADA no trae una fecha legible y el usuario no dio
    otra: las alertas en Bs lo dicen y no se toma otra fecha en su lugar.
    """
    moneda = moneda_del_libro(libro)
    umbral = contexto.umbral if contexto is not None else UMBRAL_POR_DEFECTO
    t_libro = _tasa(contexto, fecha_libro)
    t_devolucion = _tasa(contexto, fecha_devolucion)
    filas: list[FilaAlerta] = []
    for insumo in libro.insumos:
        if _sin_fuente(insumo.fuente):
            dice = f"dice «{insumo.fuente}»" if insumo.fuente.strip() else "está vacía"
            filas.append(
                _fila(
                    insumo,
                    TIPO_SIN_FUENTE,
                    moneda,
                    fecha_libro,
                    f"la FUENTE de {insumo.codigo} {dice}: el precio ({insumo.celda}) no se puede "
                    "rastrear",
                )
            )
        if contexto is not None:
            empresa = _alerta_empresa(insumo, moneda, fecha_libro, contexto)
            if empresa is not None:
                filas.append(empresa)
        filas.append(
            _alerta_bs(insumo, moneda, fecha_libro, fecha_devolucion, t_libro, t_devolucion, umbral)
        )
    if otro is not None:
        filas.extend(_alertas_version(libro, otro, moneda, fecha_libro))
    return tuple(
        sorted(
            filas,
            key=lambda f: (_ORDEN_TIPOS.get(f.tipo, 99), _clave_codigo(f.codigo), f.mensaje),
        )
    )
