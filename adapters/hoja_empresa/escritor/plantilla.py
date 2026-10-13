"""Lo que la plantilla de la empresa hace con cada línea de un APU, para que las fórmulas del APU
uniforme den exactamente el valor de Silice.

**Duplicado y declarado** (directriz de adaptadores: no se importa otro paquete; `adapters/` no
puede importar `fusion/`): estas reglas repiten las de `fusion/mapeo.py` (`_filas_base_mo`,
`_modalidad`, `_factor_formula`, `_divisor_equipos`), que deciden cómo el motor del núcleo
reproduce la plantilla (spec 1.5, F-D1 y F-D7). Si una cambia allá, debe cambiar aquí; la
verificación local de la 1.5 recalcula cada fórmula del libro devuelto y la compara con el valor de
Silice, así que una divergencia se ve como diferencia.

- **Factor de la línea:** `=E10*F10*1.1` o `=E11*F11/8` multiplican cantidad × precio por un
  literal; se conserva (F-D7).
- **Destajo:** una línea de mano de obra fuera del subtotal de salarios base cuya unidad no es "día"
  se suma completa al costo de mano de obra, sin FCAS ni rendimiento.
- **Divisor de equipos:** si la plantilla divide el subtotal de equipos entre un literal distinto
  del rendimiento (`=G27/12`), se conserva (F-D7; L6 lo informa).
"""

from __future__ import annotations

import ast
import re
from decimal import Decimal, InvalidOperation

from adapters.hoja_empresa.modelo import ApuLeido, LibroLeido, LineaApu, Rotulo, TipoInsumo
from adapters.hoja_empresa.perfil import Perfil
from core.contracts.unidades import normalizar_unidad

__all__ = ["divisor_equipos", "es_destajo", "factor_linea", "filas_base_mo", "fila_de"]

_UNO = Decimal(1)
_DIA = "dia"
_RE_N = re.compile(r"N\(([A-Z]+\d+)\)")
_RE_SI_VACIO = re.compile(r'IF\([A-Z]+\d+="",0,')


class _NoReconocidaError(ValueError):
    pass


def fila_de(ref: str) -> int:
    return int(re.sub(r"\D", "", ref))


def _factor_de(nodo: ast.AST, fuente: str, abajo: bool) -> tuple[Decimal, list[str]]:
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, int | float):
        texto = ast.get_source_segment(fuente, nodo) or ""
        try:
            return Decimal(texto), []
        except InvalidOperation as exc:
            raise _NoReconocidaError(texto) from exc
    if isinstance(nodo, ast.Name) and nodo.id in ("E", "F"):
        if abajo:
            raise _NoReconocidaError(nodo.id)
        return _UNO, [nodo.id]
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Mult):
        a, na = _factor_de(nodo.left, fuente, abajo)
        b, nb = _factor_de(nodo.right, fuente, abajo)
        return a * b, na + nb
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Div):
        a, na = _factor_de(nodo.left, fuente, abajo)
        b, nb = _factor_de(nodo.right, fuente, not abajo)
        if b == 0:
            raise _NoReconocidaError("división entre 0")
        return a / b, na + nb
    raise _NoReconocidaError(ast.dump(nodo))


def _quitar_si_vacio(texto: str) -> str:
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
            raise _NoReconocidaError(texto)
        texto = f"{texto[: m.start()]}({texto[m.end() : fin]}){texto[fin + 1 :]}"
    return texto


def _factor_formula(formula: str, fila: int, col_cant: str, col_precio: str) -> Decimal:
    texto = _quitar_si_vacio(formula.lstrip("=").replace("$", "").replace(" ", "").upper())
    texto = _RE_N.sub(r"\1", texto)
    for columna, nombre in ((col_cant, "E"), (col_precio, "F")):
        texto = re.sub(rf"(?<![A-Z0-9]){columna}{fila}(?!\d)", nombre, texto)
    try:
        arbol = ast.parse(texto, mode="eval")
    except SyntaxError as exc:
        raise _NoReconocidaError(texto) from exc
    factor, nombres = _factor_de(arbol.body, texto, abajo=False)
    if sorted(nombres) != ["E", "F"]:
        raise _NoReconocidaError(texto)
    return factor


def factor_linea(linea: LineaApu, libro: LibroLeido, perfil: Perfil) -> Decimal:
    """El factor literal con que la plantilla multiplica cantidad × precio (1 si no hay)."""
    fila = fila_de(linea.celda_cantidad.ref)
    col_sub = perfil.rotulos_apu[Rotulo.MAT].columna
    celda = f"{linea.celda_cantidad.hoja}!{col_sub}{fila}"
    formula = libro.formulas.get(celda)
    if formula is None:
        return _UNO
    try:
        return _factor_formula(
            formula, fila, perfil.columnas_linea["cantidad"], perfil.columnas_linea["precio"]
        )
    except _NoReconocidaError:
        return _UNO


def filas_base_mo(apu: ApuLeido, libro: LibroLeido) -> frozenset[int] | None:
    """Filas que suma la fórmula del subtotal de salarios base, o None."""
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


def es_destajo(linea: LineaApu, libro: LibroLeido, filas_base: frozenset[int] | None) -> bool:
    if linea.tipo is not TipoInsumo.MANO_OBRA:
        return False
    insumo = libro.insumo(linea.codigo)
    unidad = insumo.unidad if insumo and insumo.unidad.strip() else linea.unidad
    en_dias = not unidad.strip() or normalizar_unidad(unidad) == _DIA
    if filas_base is None:
        return not en_dias
    if fila_de(linea.celda_cantidad.ref) in filas_base:
        return False
    return not en_dias


def divisor_equipos(apu: ApuLeido, libro: LibroLeido) -> Decimal | None:
    """El literal entre el que la plantilla divide el subtotal de equipos (si no es el
    rendimiento)."""
    celda = apu.rotulos.get(Rotulo.EQ_DIA)
    if celda is None:
        return None
    patron = re.compile(rf"(?<![A-Z0-9]){celda.ref}/(\d+(?:\.\d+)?)(?![\d.])")
    prefijo = f"{apu.hoja}!"
    for clave_celda, formula in libro.formulas.items():
        if not clave_celda.startswith(prefijo):
            continue
        m = patron.search(formula.replace("$", "").replace(" ", "").upper())
        if m is not None and Decimal(m.group(1)) != 0:
            d = Decimal(m.group(1))
            return d if d != apu.rendimiento else None
    return None
