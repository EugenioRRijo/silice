"""Lo que la plantilla de la empresa hace con cada línea de un APU (spec 1.5, F-D1 y F-D7).

Fuente única de estas reglas: las usan `fusion.mapeo` (para que el motor del núcleo reproduzca la
plantilla) y el escritor (para que las fórmulas del APU uniforme den exactamente el valor de
Silice). Cada función `*_con_aviso` devuelve `(valor, aviso | None)`: el valor es lo que la
plantilla calcula y el aviso, si lo hay, lo que Silice tuvo que suplir o conservar para llegar a él
(`fusion.proceso` lo lleva a TRAZABILIDAD). Las funciones sin sufijo devuelven solo el valor.

- **Factor de la línea:** `=E10*F10*1.1` o `=E11*F11/8` multiplican cantidad × precio por un
  literal; se conserva (F-D7: puede ser intencional, L6/L7 lo informan).
- **Destajo:** una línea de mano de obra fuera del subtotal de salarios base cuya unidad no es "día"
  se suma completa al costo de mano de obra, sin FCAS ni rendimiento.
- **Divisor de equipos:** si la plantilla divide el subtotal de equipos entre un literal distinto
  del rendimiento (`=G27/12`), se conserva (F-D7; L6 lo informa).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from adapters.hoja_empresa.modelo import ApuLeido, LibroLeido, LineaApu, Rotulo, TipoInsumo
from adapters.hoja_empresa.perfil import Perfil
from core.contracts.apu import ModalidadManoObra
from core.contracts.unidades import normalizar_unidad

__all__ = [
    "Aviso",
    "divisor_equipos",
    "divisor_equipos_con_aviso",
    "es_destajo",
    "factor_linea",
    "factor_linea_con_aviso",
    "fila_de",
    "filas_base_mo",
    "modalidad_con_aviso",
    "texto_decimal",
    "unidad_de_linea",
]

_UNO = Decimal(1)
_DIA = "dia"
#: `N($E10)` -> `E10`; `IF($B10="",0,expr)` -> `expr` (la forma de la plantilla más nueva).
_RE_N = re.compile(r"N\(([A-Z]+\d+)\)")
_RE_SI_VACIO = re.compile(r'IF\([A-Z]+\d+="",0,')


@dataclass(frozen=True, slots=True)
class Aviso:
    """Algo que Silice tuvo que suplir o conservar. `origen` es la celda `HOJA!CELDA`."""

    origen: str
    mensaje: str


class _FormulaNoReconocidaError(ValueError):
    """La fórmula del subtotal de la línea no es cantidad × precio × literales."""


def texto_decimal(valor: Decimal) -> str:
    """Un Decimal para el texto de un aviso, sin exponente ni redondeo."""
    return format(valor, "f")


def fila_de(ref: str) -> int:
    """La fila de una referencia sin hoja (`G48` -> 48)."""
    return int(re.sub(r"\D", "", ref))


def unidad_de_linea(linea: LineaApu, libro: LibroLeido) -> str:
    """La unidad de la línea según INSUMOS; si INSUMOS no la trae, la que muestra el APU."""
    insumo = libro.insumo(linea.codigo)
    return insumo.unidad if insumo and insumo.unidad.strip() else linea.unidad


# --- Factor escrito en la fórmula de una línea --------------------------------------------------


def _factor_de(nodo: ast.AST, fuente: str, en_denominador: bool) -> tuple[Decimal, list[str]]:
    """Valor de los literales y nombres (`E`, `F`) de un producto/cociente; `E` y `F` solo pueden
    multiplicar (en el denominador no son una cantidad × precio)."""
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, int | float):
        texto = ast.get_source_segment(fuente, nodo) or ""
        try:
            return Decimal(texto), []
        except InvalidOperation as exc:
            raise _FormulaNoReconocidaError(texto) from exc
    if isinstance(nodo, ast.Name) and nodo.id in ("E", "F"):
        if en_denominador:
            raise _FormulaNoReconocidaError(nodo.id)
        return _UNO, [nodo.id]
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Mult):
        a, na = _factor_de(nodo.left, fuente, en_denominador)
        b, nb = _factor_de(nodo.right, fuente, en_denominador)
        return a * b, na + nb
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Div):
        a, na = _factor_de(nodo.left, fuente, en_denominador)
        b, nb = _factor_de(nodo.right, fuente, not en_denominador)
        if b == 0:
            raise _FormulaNoReconocidaError("división entre 0")
        return a / b, na + nb
    raise _FormulaNoReconocidaError(ast.dump(nodo))


def _quitar_si_vacio(texto: str) -> str:
    """`IF(B13="",0,expr)` -> `(expr)` dondequiera que aparezca (`IF(...)*1.1` incluido): es la
    guarda de la plantilla para una línea sin código, que no cambia el valor de una línea con
    código."""
    while m := _RE_SI_VACIO.search(texto):
        nivel, fin = 1, None
        for k in range(m.end(), len(texto)):
            if texto[k] == "(":
                nivel += 1
            elif texto[k] == ")":
                nivel -= 1
                if nivel == 0:
                    fin = k
                    break
        if fin is None:
            raise _FormulaNoReconocidaError(texto)
        texto = f"{texto[: m.start()]}({texto[m.end() : fin]}){texto[fin + 1 :]}"
    return texto


def _factor_formula(formula: str, fila: int, col_cant: str, col_precio: str) -> Decimal:
    """El factor literal de `=E10*F10*1.1` (1,1), `=E11*F11/8` (0,125) o
    `=IF($B10="",0,N($E10)*N($F10))` (1). Lanza `_FormulaNoReconocidaError` si la fórmula es otra
    cosa."""
    texto = _quitar_si_vacio(formula.lstrip("=").replace("$", "").replace(" ", "").upper())
    texto = _RE_N.sub(r"\1", texto)
    for columna, nombre in ((col_cant, "E"), (col_precio, "F")):
        texto = re.sub(rf"(?<![A-Z0-9]){columna}{fila}(?!\d)", nombre, texto)
    try:
        arbol = ast.parse(texto, mode="eval")
    except SyntaxError as exc:
        raise _FormulaNoReconocidaError(texto) from exc
    factor, nombres = _factor_de(arbol.body, texto, en_denominador=False)
    if sorted(nombres) != ["E", "F"]:
        raise _FormulaNoReconocidaError(texto)
    return factor


def factor_linea_con_aviso(
    linea: LineaApu, libro: LibroLeido, perfil: Perfil
) -> tuple[Decimal, Aviso | None]:
    """El factor con que la plantilla multiplica cantidad × precio en el subtotal de la línea.

    El subtotal de cada línea vive en la columna de los subtotales del APU (la del rótulo MAT), en
    la fila de la línea. Sin fórmula reconocible (texto, literal escrito a mano, otra referencia),
    el factor es 1 y el aviso lo dice: Silice calcula cantidad × precio. Un factor distinto de 1 se
    conserva y también se avisa.
    """
    fila = fila_de(linea.celda_cantidad.ref)
    col_sub = perfil.rotulos_apu[Rotulo.MAT].columna
    celda = f"{linea.celda_cantidad.hoja}!{col_sub}{fila}"
    formula = libro.formulas.get(celda)
    if formula is None:
        if libro.valores.get(celda) is not None:
            return _UNO, Aviso(
                celda, "subtotal de línea escrito a mano: Silice calcula cantidad × precio"
            )
        return _UNO, None
    try:
        factor = _factor_formula(
            formula, fila, perfil.columnas_linea["cantidad"], perfil.columnas_linea["precio"]
        )
    except _FormulaNoReconocidaError:
        return _UNO, Aviso(
            celda, f"fórmula de línea no reconocida ({formula}): Silice calcula cantidad × precio"
        )
    if factor == _UNO:
        return _UNO, None
    return factor, Aviso(
        celda,
        f"la fórmula {formula} multiplica cantidad × precio por {texto_decimal(factor)}: se "
        "conserva (F-D7)",
    )


def factor_linea(linea: LineaApu, libro: LibroLeido, perfil: Perfil) -> Decimal:
    """El factor literal con que la plantilla multiplica cantidad × precio (1 si no hay)."""
    return factor_linea_con_aviso(linea, libro, perfil)[0]


# --- Mano de obra: jornal o destajo -------------------------------------------------------------


def filas_base_mo(apu: ApuLeido, libro: LibroLeido) -> frozenset[int] | None:
    """Las filas que suma la fórmula del subtotal de salarios base (`=SUM(G19:G21)`,
    `=SUM(G17:G18)`, `=G19+G20`), o `None` si no hay fórmula o no es una suma de celdas de su
    columna."""
    celda = apu.rotulos.get(Rotulo.BASE_MO)
    formula = libro.formulas.get(str(celda)) if celda is not None else None
    if not formula or celda is None:
        return None
    columna = re.sub(r"\d", "", celda.ref)
    texto = formula.replace("$", "").upper()
    filas: set[int] = set()
    for desde, hasta in re.findall(rf"{columna}(\d+):{columna}(\d+)", texto):
        filas.update(range(int(desde), int(hasta) + 1))
    sin_rangos = re.sub(rf"{columna}\d+:{columna}\d+", "", texto)
    filas.update(int(f) for f in re.findall(rf"(?<![A-Z]){columna}(\d+)", sin_rangos))
    return frozenset(filas) or None


def modalidad_con_aviso(
    linea: LineaApu, libro: LibroLeido, filas_base: frozenset[int] | None
) -> tuple[ModalidadManoObra, Aviso | None]:
    """JORNAL o DESTAJO según lo que hace la plantilla con una línea de mano de obra.

    La fórmula manda: una línea que entra en el subtotal de salarios base se multiplica por FCAS y
    se divide entre el rendimiento (JORNAL), aunque su unidad sea m² (así está en algunos APU, y
    F-D7 no decide la intención). Una línea fuera de esa suma cuya unidad no es "día" es el destajo
    que la plantilla suma completo al costo de mano de obra (con aviso). Una línea en días fuera de
    la suma es un rango mal ajustado: Silice la cuenta como JORNAL (se corrige, con aviso, y F1 lo
    cuantifica). Sin fórmula reconocible, decide la unidad.
    """
    unidad = unidad_de_linea(linea, libro)
    en_dias = not unidad.strip() or normalizar_unidad(unidad) == _DIA
    if filas_base is not None and fila_de(linea.celda_cantidad.ref) in filas_base:
        return ModalidadManoObra.JORNAL, None
    if en_dias:
        if filas_base is None:
            return ModalidadManoObra.JORNAL, None
        return ModalidadManoObra.JORNAL, Aviso(
            str(linea.celda_codigo),
            f"{linea.codigo} se paga por día pero el subtotal de salarios base no la suma: "
            "Silice la cuenta como jornal",
        )
    return ModalidadManoObra.DESTAJO, Aviso(
        str(linea.celda_codigo),
        f"{linea.codigo} se paga por {unidad} (no por día): destajo, entra completo sin FCAS ni "
        "rendimiento",
    )


def es_destajo(linea: LineaApu, libro: LibroLeido, filas_base: frozenset[int] | None) -> bool:
    """¿La plantilla suma esta línea completa al costo de mano de obra (destajo)?"""
    if linea.tipo is not TipoInsumo.MANO_OBRA:
        return False
    return modalidad_con_aviso(linea, libro, filas_base)[0] is ModalidadManoObra.DESTAJO


# --- Divisor literal de los equipos -------------------------------------------------------------


def divisor_equipos_con_aviso(
    apu: ApuLeido, libro: LibroLeido
) -> tuple[Decimal | None, Aviso | None]:
    """El número literal entre el que una fórmula del APU divide el subtotal de equipos por día
    (`=G27/12+G28`) cuando no es el rendimiento, con el aviso en la celda de esa fórmula; `(None,
    None)` si lo divide entre el rendimiento (una referencia o el mismo número) o si no hay
    subtotal de equipos.

    F-D7: ese `/12` (L6) puede ser un rendimiento de equipos distinto del de la cuadrilla, escrito a
    propósito, así que Silice lo conserva y L6 lo deja "a confirmar".
    """
    celda = apu.rotulos.get(Rotulo.EQ_DIA)
    if celda is None:
        return None, None
    patron = re.compile(rf"(?<![A-Z0-9]){celda.ref}/(\d+(?:\.\d+)?)(?![\d.])")
    prefijo = f"{apu.hoja}!"
    for clave_celda, formula in libro.formulas.items():
        if not clave_celda.startswith(prefijo):
            continue
        m = patron.search(formula.replace("$", "").replace(" ", "").upper())
        if m is None or Decimal(m.group(1)) == 0:
            continue
        divisor = Decimal(m.group(1))
        if divisor == apu.rendimiento:
            return None, None
        return divisor, Aviso(
            clave_celda,
            f"los equipos se dividen entre {texto_decimal(divisor)} y no entre el rendimiento "
            f"({texto_decimal(apu.rendimiento)}): se conserva (F-D7)",
        )
    return None, None


def divisor_equipos(apu: ApuLeido, libro: LibroLeido) -> Decimal | None:
    """El literal entre el que la plantilla divide el subtotal de equipos (si no es el
    rendimiento)."""
    return divisor_equipos_con_aviso(apu, libro)[0]
