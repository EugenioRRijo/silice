"""CRONOGRAMA: tantas semanas como necesite la obra (spec 1.5, F-D4).

La plantilla trae un bloque fijo de semanas (12 o 16 columnas). Con los rendimientos corregidos la
obra puede durar más que ese bloque (en el libro A todas las duraciones daban 0 por leer otra celda,
H6). Si hace falta, el bloque se extiende a la derecha copiando la última columna de semanas con sus
fórmulas trasladadas y su estilo, y se amplían los rangos que lo leen (curva S, avance proyectado de
CONTROL DE OBRA).
"""

from __future__ import annotations

import math
import re
from decimal import Decimal

from openpyxl.formula.translate import Translator

from adapters.hoja_empresa.escritor.calculos import Evaluador
from adapters.hoja_empresa.escritor.contexto import Contexto
from adapters.hoja_empresa.escritor.formulas import Ref, analizar_ref, cita, letra, reescribir
from adapters.hoja_empresa.escritor.hoja import CeldaSalida, HojaSalida
from adapters.hoja_empresa.perfil import normalizar

__all__ = ["extender_semanas"]

_MINIMO = 12


def _bloque_semanas(h: HojaSalida) -> tuple[int, int, int, int] | None:
    """(fila, col inicial, col final, n) de la fila de encabezado 1, 2, 3… del Gantt."""
    filas: dict[int, dict[int, Decimal]] = {}
    for (f, c), cel in h.celdas.items():
        if cel.formula is None and isinstance(cel.valor, Decimal):
            filas.setdefault(f, {})[c] = cel.valor
    for f in sorted(filas):
        cols = filas[f]
        for c, v in sorted(cols.items()):
            if v != 1:
                continue
            n = 1
            while cols.get(c + n) == n + 1:
                n += 1
            if n >= 4:
                return f, c, c + n - 1, n
    return None


def _columna_fin(h: HojaSalida, fila_enc: int) -> int | None:
    for f in (fila_enc, fila_enc - 1, fila_enc + 1):
        for (ff, c), cel in h.celdas.items():
            if ff == f and isinstance(cel.valor, str) and normalizar(cel.valor).startswith("fin"):
                return c
    return None


def extender_semanas(ctx: Contexto, ev: Evaluador) -> int:
    """Extiende el bloque de semanas si la obra lo necesita; devuelve las semanas añadidas."""
    h = next((x for x in ctx.salida.hojas.values() if ctx.es(x.nombre, "CRONOGRAMA")), None)
    if h is None:
        return 0
    bloque = _bloque_semanas(h)
    if bloque is None:
        return 0
    fila_enc, c_ini, c_fin, n = bloque
    col_fin = _columna_fin(h, fila_enc)
    if col_fin is None:
        return 0
    dsem_txt = ctx.nombres.get("DSEM")
    dsem = None
    if dsem_txt:
        v = ev.formula(dsem_txt, h.nombre)
        dsem = v if isinstance(v, Decimal) and v > 0 else None
    if dsem is None:
        return 0
    fin = Decimal(0)
    for (f, c), _cel in h.celdas.items():
        if c == col_fin and f > fila_enc:
            v = ev.celda(h.nombre, f, c)
            if isinstance(v, Decimal) and v > fin:
                fin = v
    semanas = max(_MINIMO, math.ceil(fin / dsem))
    extra = semanas - n
    if extra <= 0:
        return 0

    ultima = letra(c_fin)
    for (f, c), cel in sorted(h.celdas.items()):
        if c != c_fin:
            continue
        for i in range(1, extra + 1):
            nueva = CeldaSalida(estilo=cel.estilo, respaldo=None)
            if f == fila_enc:
                nueva.valor = Decimal(n + i)
            elif cel.formula:
                nueva.formula = Translator(cel.formula, origin=f"{ultima}{f}").translate_formula(
                    f"{letra(c_fin + i)}{f}"
                )
            else:
                nueva.valor = cel.valor
            h.celdas[(f, c_fin + i)] = nueva
    if c_fin in h.anchos:
        for i in range(1, extra + 1):
            h.anchos[c_fin + i] = h.anchos[c_fin]
    h.combinadas = [
        (f1, c1, f2, c2 + extra if c1 <= c_fin <= c2 else c2) for f1, c1, f2, c2 in h.combinadas
    ]
    h.condicionales = [(_ampliar(r, c_fin, extra), o, e) for r, o, e in h.condicionales]
    if "area" in h.impresion:
        h.impresion["area"] = _ampliar_texto(h.impresion["area"], c_fin, extra)

    # Rangos que leen el bloque de semanas, en esta hoja y en las demás.
    for hoja in ctx.salida.hojas.values():
        for cel in hoja.celdas.values():
            if not cel.formula:
                continue
            nueva = _ampliar_formula(cel.formula, hoja.nombre, h.nombre, c_ini, c_fin, extra, n)
            if nueva is not None:
                cel.formula = nueva
    for hoja in ctx.salida.hojas.values():
        for g in hoja.graficos:
            for serie in g.series:
                for k in ("name", "categories", "values"):
                    v = serie.get(k)
                    if isinstance(v, str) and v.startswith("="):
                        nueva = _ampliar_formula(v, hoja.nombre, h.nombre, c_ini, c_fin, extra, n)
                        if nueva is not None:
                            serie[k] = nueva
    ctx.salida.anotar(
        "Semanas del cronograma",
        semanas,
        f"{h.nombre}!{letra(c_ini)}{fila_enc}",
        f"la obra dura más de {n} semanas: se añadieron {extra} columnas al Gantt y a la curva S",
    )
    return extra


def _ampliar(rango: str, c_fin: int, extra: int) -> str:
    return " ".join(_ampliar_texto(r, c_fin, extra) for r in rango.split())


def _ampliar_texto(texto: str, c_fin: int, extra: int) -> str:
    r = analizar_ref(texto)
    if not isinstance(r, Ref) or r.c2 != c_fin:
        return texto
    hoja = f"{cita(r.hoja)}!" if r.hoja else ""
    return f"{hoja}${letra(r.c1)}${r.f1}:${letra(r.c2 + extra)}${r.f2}"


def _ampliar_formula(
    formula: str, hoja_formula: str, cronograma: str, c_ini: int, c_fin: int, extra: int, n: int
) -> str | None:
    cambio = False

    def rango(t: str) -> str:
        nonlocal cambio
        r = analizar_ref(t)
        if not isinstance(r, Ref) or r.es_celda:
            return t
        hoja = r.hoja or hoja_formula
        if hoja != cronograma or r.c1 != c_ini or r.c2 != c_fin:
            return t
        cambio = True
        pref = f"{cita(r.hoja)}!" if r.hoja else ""
        abs1 = "$" if t.split("!")[-1].startswith("$") else ""
        return f"{pref}{abs1}{letra(r.c1)}{abs1}{r.f1}:{abs1}{letra(r.c2 + extra)}{abs1}{r.f2}"

    nueva = reescribir(formula, rango)
    if not cambio or nueva is None:
        return None
    # El tope de semanas escrito en la fórmula (MIN(N($C$4),12)) sube con el bloque.
    return re.sub(
        rf"(MIN\([^()]*(?:\([^()]*\))?[^()]*,\s*){n}(\s*\))", rf"\g<1>{n + extra}\2", nueva
    )
