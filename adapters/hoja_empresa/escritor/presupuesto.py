"""PRESUPUESTO regenerado en las mismas filas y columnas del original (spec 1.5, F-D4 y F-D5).

La hoja se copia celda a celda (cabeceras, capítulos, totales y estilos en su sitio) y en cada fila
de partida se reescriben las columnas calculadas:

- F = `=<ident>_REND`; H…P = `=<ident>_MAT` … `=<ident>_PU` (nombres del APU uniforme, nunca
  `INDIRECT` con texto: causa C1/C2);
- G conserva su fórmula de cantidad (SUMIF a MEDICIONES u otra) con el valor que usó Silice;
- Q = `=G*P`, R = `=ROUND(P-(N+O),2)`, S = `=IF(SUBSINIVA=0,0,Q/SUBSINIVA)`.

Una partida sin APU unido conserva sus valores guardados como literales (Silice tampoco la
recalcula). Los subtotales de capítulo suman su rango de partidas; los totales conservan su fórmula
y llevan los valores de Silice en las celdas de SUBSINIVA, IVATOT y TOTALGEN.
"""

from __future__ import annotations

from adapters.hoja_empresa.escritor.contexto import Contexto
from adapters.hoja_empresa.escritor.formulas import col_num, letra, reescribir
from adapters.hoja_empresa.escritor.hoja import HojaSalida
from adapters.hoja_empresa.modelo import Rotulo, TipoFilaEspecial, clave

__all__ = ["regenerar_presupuesto", "sembrar_totales"]

_DESGLOSE = (
    Rotulo.MAT,
    Rotulo.MO,
    Rotulo.EQ,
    Rotulo.TR,
    Rotulo.CD,
    Rotulo.ADM,
    Rotulo.SUB,
    Rotulo.UTI,
    Rotulo.PU,
)


def regenerar_presupuesto(ctx: Contexto, h: HojaSalida) -> set[tuple[int, int]]:
    """Reescribe las filas de partida y de subtotal; devuelve las celdas ya resueltas."""
    perfil = ctx.perfil
    datos = ctx.datos
    cp = {k: col_num(v) for k, v in perfil.columnas_presupuesto.items()}
    desglose = [col_num(c) for c in perfil.columnas_desglose]
    col_de = dict(zip(_DESGLOSE, desglose, strict=False))
    g, p_, q = letra(cp["cantidad"]), letra(cp["precio_unitario"]), letra(cp["monto"])
    n_, o_ = letra(col_de[Rotulo.SUB]), letra(col_de[Rotulo.UTI])
    subsin = "SUBSINIVA" if ctx.existe_nombre("SUBSINIVA") else None
    hechas: set[tuple[int, int]] = set()

    for p in ctx.libro.partidas:
        r = p.fila
        hoja_apu = p.hoja_apu if p.hoja_apu in ctx.unidos and ctx.unidos[p.hoja_apu] is p else None
        if hoja_apu is not None:
            h.poner(r, cp["rendimiento"], formula=f"={ctx.nombre_rotulo(hoja_apu, Rotulo.REND)}")
            for rot, col in col_de.items():
                h.poner(r, col, formula=f"={ctx.nombre_rotulo(hoja_apu, rot)}")
        else:
            for letra_col in ("F", *(letra(c) for c in desglose)):
                col = col_num(letra_col)
                h.poner(r, col, p.guardados.get(letra_col))
            ctx.salida.anotar(
                "Partida sin APU unido",
                p.numero,
                clave(h.nombre, f"B{r}"),
                "rendimiento y desglose quedan con sus valores guardados (Silice no la recalcula)",
            )
        pu = datos.precios_unitarios.get(r)
        if pu is None and hoja_apu is not None and hoja_apu in datos.apus:
            pu = datos.apus[hoja_apu].precio_unitario
        celda_p = h.celda(r, cp["precio_unitario"])
        if pu is not None:
            if celda_p.formula:
                celda_p.fijo = pu
            else:
                celda_p.valor = pu

        celda_g = h.celda(r, cp["cantidad"])
        if celda_g.formula:
            nueva = reescribir(celda_g.formula, lambda t: ctx.rango(t, h.nombre))
            if nueva is None or "INDIRECT(" in nueva.upper():
                ctx.salida.anotar(
                    "Fórmula sustituida por su valor",
                    p.cantidad,
                    clave(h.nombre, f"{g}{r}"),
                    "la cantidad leía una referencia que no sale en la devolución: "
                    f"{celda_g.formula}",
                )
                celda_g.formula = None
                celda_g.valor = p.cantidad
            else:
                celda_g.formula = nueva
                celda_g.fijo = p.cantidad
        else:
            celda_g.valor = p.cantidad

        h.poner(r, cp["monto"], formula=f"={g}{r}*{p_}{r}")
        h.poner(r, cp["verificacion"], formula=f"=ROUND({p_}{r}-({n_}{r}+{o_}{r}),2)")
        if subsin:
            h.poner(r, cp["peso"], formula=f"=IF({subsin}=0,0,{q}{r}/{subsin})")
        hechas.update(
            (r, c)
            for c in (
                cp["rendimiento"],
                cp["cantidad"],
                cp["monto"],
                cp["verificacion"],
                cp["peso"],
                *desglose,
            )
        )

    filas_partida = sorted(p.fila for p in ctx.libro.partidas)
    frontera = 0
    for e in sorted(ctx.libro.filas_especiales, key=lambda x: x.fila):
        if e.tipo in (TipoFilaEspecial.SUBTOTAL, TipoFilaEspecial.SUMA):
            filas = [f for f in filas_partida if frontera < f < e.fila]
            if filas:
                h.poner(e.fila, cp["monto"], formula=f"=SUM({q}{filas[0]}:{q}{filas[-1]})")
                hechas.add((e.fila, cp["monto"]))
            frontera = e.fila
        elif e.tipo is TipoFilaEspecial.CAPITULO:
            frontera = e.fila
    return hechas


def sembrar_totales(ctx: Contexto) -> None:
    """Las celdas de SUBSINIVA, IVATOT y TOTALGEN llevan los totales de Silice."""
    for nombre, valor in ctx.datos.totales.items():
        lugar = ctx.celda_nombre(nombre)
        if lugar is None:
            continue
        hoja, f, c = lugar
        h = ctx.salida.hojas.get(hoja)
        if h is None:
            continue
        cel = h.celda(f, c)
        if cel.formula:
            cel.fijo = valor
        else:
            cel.valor = valor
