"""Partidas agregadas a mano en el borrador de la Hoja (plan de montar un presupuesto, Tarea 8).

Una obra civil se presupuesta por partidas: la persona elige una partida del catálogo, escribe su
cantidad y, si quiere, «cómo se midió» (el cálculo, con coma decimal: «6*35», «2,5*4») y una nota
de medición. Diseño: `docs/especificaciones/2026-10-25-montar-presupuesto-design.md` §5.3 y la
decisión de ingeniería «Cómo se midió».

* `traducir_calculo` pasa el cálculo tecleado a la sintaxis de `core.verification.evaluar`: las
  cifras con la regla de `aplicacion.cifras.cifra_escrita` (coma decimal, punto de miles) se
  reescriben con punto decimal y sin miles; solo se admiten `+ - * / ( )`, espacios y `×` o `x`
  como multiplicación (y el «−» tipográfico como resta, porque es el que muestra el mensaje).
  El texto nunca se ejecuta: lo evalúa el evaluador aritmético del núcleo, que recorre el árbol
  sintáctico y rechaza todo lo que no sea aritmética; aquí, además, solo pasan cifras y signos.
* `cantidad_y_regla` decide la cantidad y la regla del renglón: el cálculo traducido se guarda
  como regla **solo si** su resultado coincide con la cantidad dentro de la tolerancia, así R1
  lo reconoce como reproducible en vez de advertir que es manual.
* `agregar_partida` y `quitar_partida` cambian el borrador (inmutable: devuelven otro). Los
  renglones agregados son `ItemComputo` `MANUAL` con `origen_id` «a-mano:n»; en los cambios del
  borrador son altas y bajas (`hoja._cambios_de_cantidades`).
* `texto_llano` presenta la advertencia de R1 para una cantidad manual sin regla en lenguaje
  llano.
* `calculo_tecleable` muestra la regla de un renglón con coma decimal (Tarea 9), y
  `pendientes_sin_calculo` es la fuente «cantidades sin cálculo» de la mesa de control.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.vial.modelo import PREFIJO_TRAMO as _PREFIJO_TRAMO
from aplicacion.cifras import BLANCOS, MENSAJE_CIFRA, CifraInvalida, cifra_escrita, texto_de_cifra
from aplicacion.errores import HojaInvalida
from aplicacion.hoja import Borrador, claves_de_items, items_sin_escribir
from core import models
from core.contracts import ItemComputo, OrigenTipo
from core.contracts.dominio import Dominio
from core.verification import REGLAS, TrazabilidadGeometrica, evaluar
from core.verification.expresiones import ExpresionInvalida, ParametroFaltante

if TYPE_CHECKING:
    from aplicacion.mesa import Pendiente

__all__ = [
    "PREFIJO_A_MANO",
    "CalculoInvalido",
    "PartidaElegida",
    "agregar_partida",
    "calculo_tecleable",
    "cantidad_y_regla",
    "pendientes_sin_calculo",
    "quitar_partida",
    "texto_llano",
    "traducir_calculo",
]

#: Prefijo del `origen_id` de un renglón agregado a mano: «a-mano:1», «a-mano:2»…
PREFIJO_A_MANO = "a-mano:"

#: El prefijo del `origen_id` de un tramo, de `adapters/vial/modelo.py` (su única definición). Se
#: ofrece aquí, y no desde `hoja_vial`, para que `hoja_vista` no cierre el ciclo `hoja_vial` →
#: `elaboracion` → `hoja_edicion` → `hoja_vista` → `hoja_vial` (punta a punta, 2026-11-13).
PREFIJO_TRAMO = _PREFIJO_TRAMO

SOLO_ARITMETICA = "El cálculo solo admite números y los signos + − × / y paréntesis."
CALCULO_IMPOSIBLE = "El cálculo no se puede hacer: revise los signos y los paréntesis."
DIVIDE_ENTRE_CERO = "El cálculo divide entre cero."
CALCULO_VACIO = "Escriba el cálculo, por ejemplo 6*3-2."
CALCULO_LARGO = "El cálculo es demasiado largo: use a lo sumo 300 caracteres."
CALCULO_ENORME = "El cálculo da una cifra demasiado grande para una cantidad."
PRECISION_PERDIDA = (
    "Con cuatro decimales, el resultado del cálculo pierde precisión: escriba también la "
    "cantidad, con los decimales que necesite."
)
CANTIDAD_NEGATIVA = "La cantidad no puede ser negativa."
FILA_DEL_ESPACIO = "Esa fila sale del espacio: cámbiela en «Espacio y metrajes»."
FILA_AUSENTE = "Esa fila ya no está en el presupuesto."

#: Tope del cálculo: deja holgura al evaluador recursivo del núcleo (un «1+1+…» de 150 sumas
#: anida 150 nodos) y alcanza para cualquier medición escrita a mano.
LARGO_MAXIMO = 300
#: La cantidad calculada se guarda con cuatro decimales (la mitad hacia arriba).
CUATRO_DECIMALES = Decimal("0.0001")
#: Cifras significativas con que un mensaje dice un resultado que no cabe en cuatro decimales.
CIFRAS_EN_EL_MENSAJE = 8
#: La diferencia máxima entre la cantidad escrita y el resultado del cálculo (plan, Tarea 8).
TOLERANCIA_ABSOLUTA = Decimal("0.001")
#: La tolerancia relativa con que R1 compara la cantidad con su regla: la misma instancia que
#: audita la Hoja, para que lo que aquí coincide R1 no lo marque como error.
TOLERANCIA_R1 = next(r for r in REGLAS if isinstance(r, TrazabilidadGeometrica)).tolerancia_relativa

_CARACTERES_DE_CIFRA = frozenset("0123456789.,")
_SIGNOS = {
    "+": "+",
    "-": "-",
    "−": "-",
    "*": "*",
    "×": "*",
    "x": "*",
    "/": "/",
    "(": "(",
    ")": ")",
}
#: La advertencia de R1 para una cantidad manual sin regla (`core/verification/reglas.py`).
_R1_MANUAL = re.compile(
    r"la cantidad de (?P<codigo>.+) \((?P<medida>[^()]*)\) es manual y no declara la regla que "
    r"la produjo: no es derivable ni reproducible"
)


class CalculoInvalido(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """El cálculo o la cantidad no se pueden usar; el mensaje es el que ve la persona."""


@dataclass(frozen=True, slots=True)
class PartidaElegida:
    """La partida del catálogo que la persona eligió agregar."""

    codigo: str
    descripcion: str
    unidad: str
    dominio: Dominio


def traducir_calculo(texto: str) -> str:
    """El cálculo tecleado en la sintaxis de `evaluar`: «2,5 × 4» → «2.5*4».

    `CalculoInvalido` con `SOLO_ARITMETICA` si hay cualquier otro carácter (se mira primero, en
    todo el texto) o «**» y «//» (potencia y división entera, que no son las cuatro operaciones),
    y con `MENSAJE_CIFRA` si una cifra no sigue la regla (también dos cifras separadas solo por
    un espacio, «1 234»).
    """
    limpio = texto.strip(BLANCOS)
    if not limpio:
        raise CalculoInvalido(CALCULO_VACIO)
    if len(limpio) > LARGO_MAXIMO:
        raise CalculoInvalido(CALCULO_LARGO)
    if any(c not in _CARACTERES_DE_CIFRA and c not in _SIGNOS and c not in BLANCOS for c in limpio):
        raise CalculoInvalido(SOLO_ARITMETICA)
    partes: list[str] = []
    tras_cifra = False
    i = 0
    while i < len(limpio):
        caracter = limpio[i]
        if caracter in _CARACTERES_DE_CIFRA:
            fin = i
            while fin < len(limpio) and limpio[fin] in _CARACTERES_DE_CIFRA:
                fin += 1
            if tras_cifra:
                raise CalculoInvalido(MENSAJE_CIFRA)
            try:
                valor = cifra_escrita(limpio[i:fin])
            except CifraInvalida as error:
                raise CalculoInvalido(MENSAJE_CIFRA) from error
            partes.append(format(valor, "f"))
            tras_cifra, i = True, fin
        elif caracter in BLANCOS:
            i += 1
        else:
            partes.append(_SIGNOS[caracter])
            tras_cifra, i = False, i + 1
    traducido = "".join(partes)
    if "**" in traducido or "//" in traducido:
        raise CalculoInvalido(SOLO_ARITMETICA)
    return traducido


def _coinciden(cantidad: Decimal, resultado: Decimal) -> bool:
    """La cantidad coincide con el resultado: diferencia de a lo sumo 0,001 y dentro de la
    tolerancia relativa de R1 (con resultado cero, solo la igualdad, como R1)."""
    diferencia = abs(cantidad - resultado)
    return diferencia <= TOLERANCIA_ABSOLUTA and diferencia <= abs(resultado) * TOLERANCIA_R1


def _a_cuatro_decimales(valor: Decimal) -> Decimal:
    """`valor` con cuatro decimales (la mitad hacia arriba), sin ceros a la derecha ni exponente."""
    try:
        redondeado = valor.quantize(CUATRO_DECIMALES, rounding=ROUND_HALF_UP)
    except InvalidOperation as error:  # más cifras de las que caben en un Decimal
        raise CalculoInvalido(CALCULO_ENORME) from error
    return Decimal(format(redondeado.normalize(), "f"))


def _divide_entre_cero(causa: BaseException | None) -> bool:
    """La causa que encadena `evaluar` es una división entre cero: `decimal.DivisionByZero`
    (x/0) es un `ZeroDivisionError`; la división indefinida (0/0) llega, con el `decimal` en C,
    como `InvalidOperation` cuyo primer argumento es la lista de señales (`DivisionUndefined`,
    que también es un `ZeroDivisionError`)."""
    if isinstance(causa, ZeroDivisionError):
        return True
    senales = causa.args[0] if isinstance(causa, InvalidOperation) and causa.args else ()
    return isinstance(senales, list) and any(
        isinstance(s, type) and issubclass(s, ZeroDivisionError) for s in senales
    )


def _resultado(traducido: str) -> Decimal:
    """El resultado exacto del cálculo (el cero, sin signo: «0*-1» da 0, no −0)."""
    try:
        resultado = evaluar(traducido, {})
    except (ExpresionInvalida, ParametroFaltante, RecursionError) as error:
        if _divide_entre_cero(error.__cause__):
            raise CalculoInvalido(DIVIDE_ENTRE_CERO) from error
        raise CalculoInvalido(CALCULO_IMPOSIBLE) from error
    return resultado.copy_abs() if resultado.is_zero() else resultado


def _texto_del_resultado(resultado: Decimal, redondeado: Decimal, comparado: Decimal) -> str:
    """El resultado como se dice en un mensaje: con cuatro decimales, salvo que así se vea igual
    a `comparado` (la cantidad escrita, o cero); entonces con `CIFRAS_EN_EL_MENSAJE` cifras
    significativas (la mitad hacia arriba: 1/30000 → 0,000033333333), y con todas si aun así se
    viera igual."""
    if texto_de_cifra(redondeado) != texto_de_cifra(comparado):
        return texto_de_cifra(redondeado)
    paso = Decimal(1).scaleb(resultado.adjusted() - CIFRAS_EN_EL_MENSAJE + 1)
    for valor in (resultado.quantize(paso, rounding=ROUND_HALF_UP), resultado):
        texto = texto_de_cifra(Decimal(format(valor.normalize(), "f")))
        if texto != texto_de_cifra(comparado):
            return texto
    return texto


def cantidad_y_regla(cantidad: str, calculo: str) -> tuple[Decimal, str | None]:
    """La cantidad del renglón y su regla, a partir de lo que la persona escribió.

    * Sin cálculo: la cantidad escrita (`cifra_escrita`, con su `CifraInvalida`) y sin regla.
    * Con cálculo y sin cantidad: el resultado con cuatro decimales; si ese redondeo lo aleja
      del resultado más de lo que R1 tolera, `PRECISION_PERDIDA` (que escriba la cantidad).
    * Con los dos: la cantidad escrita, si coincide con el resultado (`_coinciden`); si no,
      «El cálculo da X y la cantidad es Y: corrija uno de los dos.».

    La regla devuelta es el cálculo traducido. Toda falla es `CalculoInvalido` salvo la cifra
    mal escrita de la cantidad, que es `CifraInvalida` con el mensaje de la regla de las cifras.
    """
    if not calculo.strip(BLANCOS):
        escrita = cifra_escrita(cantidad)
        if escrita < 0:
            raise CalculoInvalido(CANTIDAD_NEGATIVA)
        return escrita, None
    traducido = traducir_calculo(calculo)
    resultado = _resultado(traducido)
    redondeado = _a_cuatro_decimales(resultado)
    if resultado < 0:
        mostrado = _texto_del_resultado(resultado, redondeado, Decimal(0))
        raise CalculoInvalido(f"El cálculo da {mostrado}: una cantidad no puede ser negativa.")
    if not cantidad.strip(BLANCOS):
        if not _coinciden(redondeado, resultado):
            raise CalculoInvalido(PRECISION_PERDIDA)
        return redondeado, traducido
    escrita = cifra_escrita(cantidad)
    if not _coinciden(escrita, resultado):
        raise CalculoInvalido(
            f"El cálculo da {_texto_del_resultado(resultado, redondeado, escrita)} y la cantidad "
            f"es {texto_de_cifra(escrita)}: corrija uno de los dos."
        )
    return escrita, traducido


def _numero_a_mano(origen_id: str) -> int:
    resto = origen_id.removeprefix(PREFIJO_A_MANO)
    if resto == origen_id or not (resto.isascii() and resto.isdigit()):
        return 0
    return int(resto)


def agregar_partida(
    borrador: Borrador, partida: PartidaElegida, *, cantidad: str, calculo: str, nota: str
) -> tuple[Borrador, str]:
    """El borrador con la partida agregada al final de sus renglones, y la clave del renglón.

    El renglón es un `ItemComputo` `MANUAL` con `origen_id` «a-mano:n» (n, uno más que el mayor
    de los agregados que quedan en el borrador), la cantidad y la regla de `cantidad_y_regla` y
    sin parámetros. La nota (sin blancos en los bordes) se guarda en `notas` si no está vacía.
    """
    valor, regla = cantidad_y_regla(cantidad, calculo)
    numero = 1 + max((_numero_a_mano(i.origen_id) for i in borrador.items_base), default=0)
    item = ItemComputo(
        codigo_partida=partida.codigo,
        descripcion=partida.descripcion,
        unidad=partida.unidad,
        cantidad=valor,
        origen_id=f"{PREFIJO_A_MANO}{numero}",
        origen_tipo=OrigenTipo.MANUAL,
        dominio=partida.dominio,
        regla=regla,
        parametros={},
    )
    clave = f"{item.codigo_partida}|{item.origen_id}"
    notas = dict(borrador.notas)
    if nota.strip(BLANCOS):
        notas[clave] = nota.strip(BLANCOS)
    return replace(borrador, items_base=(*borrador.items_base, item), notas=notas), clave


def quitar_partida(borrador: Borrador, clave: str) -> Borrador:
    """El borrador sin el renglón `clave`, su cantidad escrita y su nota.

    Solo se quitan renglones de la versión (`items_base`); uno que sale del espacio se cambia en
    «Espacio y metrajes» (`HojaInvalida`). Si quitarlo renombra un renglón repetido («…#2» pasa
    a ser la clave sin sufijo), su cantidad escrita y su nota lo siguen.
    """
    todas = claves_de_items(items_sin_escribir(borrador))
    propias = todas[: len(borrador.items_base)]
    if clave not in propias:
        raise HojaInvalida(FILA_DEL_ESPACIO if clave in todas else FILA_AUSENTE)
    indice = propias.index(clave)
    items = (*borrador.items_base[:indice], *borrador.items_base[indice + 1 :])
    nuevas = claves_de_items(items)
    renombre = dict(zip([c for c in propias if c != clave], nuevas, strict=True))
    return replace(
        borrador,
        items_base=items,
        cantidades={renombre.get(k, k): v for k, v in borrador.cantidades.items() if k != clave},
        notas={renombre.get(k, k): v for k, v in borrador.notas.items() if k != clave},
    )


def texto_llano(descripcion: str) -> str:
    """La advertencia de R1 para una cantidad manual sin regla, en lenguaje llano y con la
    cantidad en es-VE (R1 la cita con punto decimal: «12.5 m2» → «12,5 m2», «1234.5» →
    «1.234,5»); cualquier otra descripción, igual."""
    manual = _R1_MANUAL.fullmatch(descripcion)
    if manual is None:
        return descripcion
    numero, espacio, unidad = manual["medida"].partition(" ")
    try:
        cifra = texto_de_cifra(Decimal(numero))
    except (InvalidOperation, ValueError):  # no es una cifra: se deja como la escribió R1
        cifra = numero
    return (
        f"La cantidad de {manual['codigo']} ({cifra}{espacio}{unidad}) se escribió a mano sin "
        "cálculo: escriba cómo se obtuvo si quiere que Sílice la pueda verificar."
    )


#: La regla de un renglón agregado a mano: solo cifras con punto decimal y los signos.
_REGLA_ARITMETICA = re.compile(r"[0-9.+\-*/() ]+")
_CIFRA_DE_LA_REGLA = re.compile(r"[0-9.]+")


def calculo_tecleable(regla: str | None) -> str | None:
    """El cálculo de un renglón como lo teclea la persona: la regla que dejó `cantidad_y_regla`
    («2.5*84») con cada cifra en es-VE («2,5*84»), que `traducir_calculo` vuelve a leer igual.
    `None` sin regla o si no es solo aritmética (la regla de un renglón del espacio)."""
    if not regla or _REGLA_ARITMETICA.fullmatch(regla) is None:
        return None
    try:
        return _CIFRA_DE_LA_REGLA.sub(lambda cifra: texto_de_cifra(Decimal(cifra[0])), regla)
    except InvalidOperation:  # «1.2.3» no es una cifra: no se muestra
        return None


def pendientes_sin_calculo(sesion: Session, hoy: date) -> list[Pendiente]:
    """Fuente «calidad» de la mesa: por obra, cuántos hallazgos de R1 de cantidad manual sin
    regla tiene su versión vigente (los guardados con la versión) → «{n} cantidad(es) escritas a
    mano sin cálculo en {versión}», acción «Abrir el presupuesto». No escribe."""
    # `aplicacion.mesa` registra esta fuente en `FUENTES`: importarla arriba sería circular.
    from aplicacion.mesa import ABRIR_EL_PRESUPUESTO, pendiente, plural, versiones_vigentes

    del hoy  # la regla no depende del día
    salida = []
    for fila, version in versiones_vigentes(sesion):
        descripciones = sesion.scalars(
            select(models.Hallazgo.descripcion).where(
                models.Hallazgo.presupuesto_id == version.id,
                models.Hallazgo.regla == TrazabilidadGeometrica.codigo,
            )
        )
        cuantas = sum(1 for d in descripciones if _R1_MANUAL.fullmatch(d) is not None)
        if cuantas:
            cantidades = plural(cuantas, "cantidad escrita", "cantidades escritas")
            texto = f"{cantidades} a mano sin cálculo en {version.codigo}"
            salida.append(pendiente(fila, texto, ABRIR_EL_PRESUPUESTO))
    return salida
