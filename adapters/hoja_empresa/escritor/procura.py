"""PROCURA: la lista de compras cubre todo lo que usan los APU (spec 1.5, F-D4; H7, H8).

La plantilla lista los insumos por la fila que ocupan en INSUMOS (`=INSUMOS!$B$7`, `$B$8`…) y
tiene un número fijo de filas por sección (20 materiales en los libros A y B, aunque INSUMOS tiene
más de 40). Los insumos que no caben no se compran y la fila "Dif. vs presupuesto" no da 0.

En la devolución, cada sección lista primero los códigos que usan los APU unidos (en el orden de
INSUMOS) y después los demás; si los usados no caben, la sección crece: se insertan filas antes de
la última, como lo haría Excel (todas las referencias a filas de abajo se desplazan y los totales
amplían su rango). La explosión de cada fila la escribe `derivadas` (SUMIF directos sobre los APU
uniformes).

Destajo: una línea de mano de obra pagada por unidad (m², ml…) no lleva FCAS en el APU (la regla de
la plantilla, duplicada en `plantilla`); su fila de PROCURA tampoco lo lleva, para que el costo de
personal cuadre con el componente de mano de obra.
"""

from __future__ import annotations

import re

from openpyxl.formula.tokenizer import Token
from openpyxl.formula.translate import Translator

from adapters.hoja_empresa.escritor.contexto import Contexto
from adapters.hoja_empresa.escritor.formulas import cita, col_num, letra, tokens
from adapters.hoja_empresa.escritor.hoja import CeldaSalida, HojaSalida
from adapters.hoja_empresa.modelo import TipoInsumo
from adapters.hoja_empresa.plantilla import es_destajo, fila_de, filas_base_mo

__all__ = ["ajustar_procura", "insertar_filas"]

_DIRECCION = re.compile(r"(\$?[A-Za-z]{1,3}\$?)(\d+)")
_FILAS = re.compile(r"^(\$?)(\d+):(\$?)(\d+)$")


# --- Insertar filas como Excel -------------------------------------------------------------------


def _prefijo_hoja(texto: str) -> tuple[str, str]:
    """('\\'APU-01\\'!', '$B$10:$B$20') o ('', 'A5')."""
    if texto.startswith("'"):
        i = 1
        while i < len(texto):
            if texto[i] == "'":
                if i + 1 < len(texto) and texto[i + 1] == "'":
                    i += 2
                    continue
                break
            i += 1
        return texto[: i + 2], texto[i + 2 :]
    if "!" in texto:
        a, _, b = texto.partition("!")
        return a + "!", b
    return "", texto


def _hoja_de_prefijo(prefijo: str) -> str | None:
    if not prefijo:
        return None
    p = prefijo[:-1]
    if p.startswith("'"):
        p = p[1:-1].replace("''", "'")
    return p


def _desplazar_dir(direccion: str, desde: int, n: int) -> str:
    m = _FILAS.match(direccion)
    if m:
        a, b = int(m.group(2)), int(m.group(4))
        a2 = a + n if a >= desde else a
        b2 = b + n if b >= desde else b
        return f"{m.group(1)}{a2}:{m.group(3)}{b2}"
    return _DIRECCION.sub(
        lambda x: f"{x.group(1)}{int(x.group(2)) + n if int(x.group(2)) >= desde else x.group(2)}",
        direccion,
    )


def desplazar_formula(formula: str, hoja_formula: str, objetivo: str, desde: int, n: int) -> str:
    """Desplaza n filas toda referencia a `objetivo` en filas >= desde (inserción de filas)."""
    salida: list[str] = []
    for t in tokens(formula):
        if t.type == Token.OPERAND and t.subtype == Token.RANGE and "[" not in t.value:
            prefijo, direccion = _prefijo_hoja(t.value)
            hoja = _hoja_de_prefijo(prefijo) or hoja_formula
            if hoja == objetivo and re.search(r"\d", direccion):
                salida.append(prefijo + _desplazar_dir(direccion, desde, n))
                continue
        salida.append(t.value)
    return "=" + "".join(salida)


def _desplazar_rango_texto(texto: str, desde: int, n: int) -> str:
    prefijo, direccion = _prefijo_hoja(texto)
    return prefijo + _desplazar_dir(direccion, desde, n)


def insertar_filas(ctx: Contexto, h: HojaSalida, desde: int, n: int) -> None:
    """Inserta `n` filas en `h` antes de la fila `desde` y copia en ellas la fila que queda debajo
    (estilo y fórmulas trasladadas), como 'insertar filas' de Excel."""
    h.celdas = {((f + n if f >= desde else f), c): cel for (f, c), cel in h.celdas.items()}
    for hoja in ctx.salida.hojas.values():
        for cel in hoja.celdas.values():
            if cel.formula:
                cel.formula = desplazar_formula(cel.formula, hoja.nombre, h.nombre, desde, n)
    h.combinadas = [
        (
            f1 + n if f1 >= desde else f1,
            c1,
            f2 + n if f2 >= desde else f2,
            c2,
        )
        for f1, c1, f2, c2 in h.combinadas
    ]
    h.altos = {(f + n if f >= desde else f): v for f, v in h.altos.items()}
    h.validaciones = [
        (" ".join(_desplazar_rango_texto(r, desde, n) for r in rango.split()), op)
        for rango, op in h.validaciones
    ]
    h.condicionales = [
        (" ".join(_desplazar_rango_texto(r, desde, n) for r in rango.split()), op, e)
        for rango, op, e in h.condicionales
    ]
    if "area" in h.impresion:
        h.impresion["area"] = _desplazar_rango_texto(h.impresion["area"], desde, n)
    for img in h.imagenes:
        if img.fila >= desde:
            img.fila += n
    for hoja in ctx.salida.hojas.values():
        for g in hoja.graficos:
            for serie in g.series:
                for k in ("name", "categories", "values"):
                    v = serie.get(k)
                    if isinstance(v, str) and v.startswith("="):
                        serie[k] = desplazar_formula(v, hoja.nombre, h.nombre, desde, n)
    for nombre, texto in list(ctx.nombres.items()):
        ctx.nombres[nombre] = desplazar_formula(texto, "", h.nombre, desde, n)
    ctx.pendientes = [
        (hoja, f + n if hoja == h.nombre and f >= desde else f, c, o, m)
        for hoja, f, c, o, m in ctx.pendientes
    ]
    modelo = desde + n
    for (f, c), cel in list(h.celdas.items()):
        if f != modelo:
            continue
        for r in range(desde, desde + n):
            nueva = CeldaSalida(estilo=cel.estilo, respaldo=None, comentario=None)
            if cel.formula:
                nueva.formula = Translator(
                    cel.formula, origin=f"{letra(c)}{modelo}"
                ).translate_formula(f"{letra(c)}{r}")
            else:
                nueva.valor = cel.valor
            h.celdas[(r, c)] = nueva
    if modelo in h.altos:
        for r in range(desde, desde + n):
            h.altos[r] = h.altos[modelo]


# --- Secciones de PROCURA ------------------------------------------------------------------------


def _fila_insumos(ctx: Contexto, formula: str) -> int | None:
    hoja = re.escape(ctx.perfil.hoja("INSUMOS"))
    col = ctx.perfil.columnas_insumos["codigo"]
    m = re.search(rf"(?:'{hoja}'|{hoja})!\$?{col}\$?(\d+)", formula, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _secciones(ctx: Contexto, h: HojaSalida) -> list[tuple[TipoInsumo, list[tuple[int, int]]]]:
    """Bloques de filas consecutivas con explosión de insumos: (tipo, [(fila, col del código)]).

    Una fila es de un bloque si tiene la explosión (SUMIF sobre los APU) y su criterio es la celda
    de código de la misma fila; el código puede faltar (la empresa borró la fórmula de una fila).
    """
    por_fila_insumos = {fila_de(i.celda.ref): i for i in ctx.libro.insumos}
    apus = [cita(x) + "!" for x in ctx.unidos]
    filas: dict[int, int] = {}
    for (f, _c), cel in sorted(h.celdas.items()):
        if f in filas or not cel.formula or "SUMIF(" not in cel.formula.upper():
            continue
        if not any(x in cel.formula for x in apus):
            continue
        m = re.search(r"SUMIF\([^,]+,\s*\$?([A-Z]{1,3})\$?(\d+)", cel.formula, re.IGNORECASE)
        if m is not None and int(m.group(2)) == f:
            filas[f] = col_num(m.group(1))
    bloques: list[list[tuple[int, int]]] = []
    for f, c in sorted(filas.items()):
        if bloques and f == bloques[-1][-1][0] + 1 and c == bloques[-1][-1][1]:
            bloques[-1].append((f, c))
        else:
            bloques.append([(f, c)])
    out = []
    for b in bloques:
        tipos: list[TipoInsumo] = []
        for f, c in b:
            cel = h.celdas.get((f, c))
            if cel is None:
                continue
            n = _fila_insumos(ctx, cel.formula) if cel.formula else None
            ins = por_fila_insumos.get(n) if n is not None else None
            if ins is not None:
                tipos.append(ins.tipo)
            elif ctx.perfil.es_codigo_insumo(cel.respaldo if cel.formula else cel.valor):
                codigo = str(cel.respaldo if cel.formula else cel.valor).strip()
                tipos.append(TipoInsumo(codigo[:2].upper()))
        if tipos:
            out.append((max(set(tipos), key=tipos.count), b))
    return out


def ajustar_procura(ctx: Contexto) -> None:
    h = next((x for x in ctx.salida.hojas.values() if ctx.es(x.nombre, "PROCURA")), None)
    if h is None:
        return
    usados: dict[TipoInsumo, set[str]] = {t: set() for t in TipoInsumo}
    destajo: set[str] = set()
    for hoja in ctx.unidos:
        a = ctx.apu(hoja)
        if a is None:
            continue
        base = filas_base_mo(a, ctx.libro)
        for linea in a.lineas:
            usados[linea.tipo].add(linea.codigo)
            if es_destajo(linea, ctx.libro, base):
                destajo.add(linea.codigo)
    hoja_ins = ctx.perfil.hoja("INSUMOS")
    col_ins = ctx.perfil.columnas_insumos["codigo"]
    # De abajo hacia arriba, para que insertar filas no mueva los bloques que faltan.
    for tipo, filas in reversed(_secciones(ctx, h)):
        insumos = [i for i in ctx.libro.insumos if i.tipo is tipo]
        en_uso = [i for i in insumos if i.codigo in usados[tipo]]
        resto = [i for i in insumos if i.codigo not in usados[tipo]]
        secuencia = en_uso + resto
        faltan = len(en_uso) - len(filas)
        if faltan > 0:
            ultima, col = filas[-1]
            insertar_filas(ctx, h, ultima, faltan)
            filas = filas[:-1] + [(ultima + k, col) for k in range(faltan + 1)]
            ctx.salida.anotar(
                "Filas añadidas a PROCURA",
                faltan,
                f"{h.nombre}!{letra(col)}{ultima}",
                f"los APU usan {len(en_uso)} códigos de {tipo.name.lower()} y la sección tenía "
                f"{len(filas) - faltan} filas",
            )
        modelo = next(
            (
                h.celdas[(f, c)]
                for f, c in filas
                if (f, c) in h.celdas
                and h.celdas[(f, c)].formula
                and _fila_insumos(ctx, h.celdas[(f, c)].formula or "") is not None
            ),
            None,
        )
        for k, (f, c) in enumerate(filas):
            cel = h.celdas.get((f, c))
            if cel is None:
                cel = CeldaSalida(estilo=modelo.estilo if modelo else None)
                h.celdas[(f, c)] = cel
            if k < len(secuencia):
                ins = secuencia[k]
                fila_ins = fila_de(ins.celda.ref)
                base = cel.formula if cel.formula and _fila_insumos(ctx, cel.formula) else None
                base = base or (modelo.formula if modelo is not None else None)
                if base is None:
                    cel.formula, cel.valor = None, ins.codigo
                else:
                    cel.formula = re.sub(
                        rf"((?:'{re.escape(hoja_ins)}'|{re.escape(hoja_ins)})!\$?{col_ins}\$?)(\d+)",
                        lambda m, r=fila_ins: f"{m.group(1)}{r}",
                        base,
                        flags=re.IGNORECASE,
                    )
                cel.respaldo = ins.codigo
                if tipo is TipoInsumo.MANO_OBRA:
                    _fcas_segun(h, f, ins.codigo in destajo)
            else:
                cel.formula = None
                cel.valor = ""


def _fcas_segun(h: HojaSalida, fila: int, destajo: bool) -> None:
    """El costo de personal lleva FCAS si la línea es jornal y no lo lleva si es destajo, con la
    misma regla que el APU (la fórmula manda, F-D7), aunque la plantilla decida por la unidad."""
    for (f, _c), cel in h.celdas.items():
        if f != fila or not cel.formula or "FCAS" not in cel.formula.upper():
            continue
        texto = re.sub(
            r"IF\([^(),]*,\s*FCAS\s*,\s*1\s*\)",
            "1" if destajo else "FCAS",
            cel.formula,
            flags=re.IGNORECASE,
        )
        if destajo:
            texto = re.sub(r"\*\s*FCAS\b", "", texto, flags=re.IGNORECASE)
            texto = re.sub(r"\*\s*1\b(?![.\d])", "", texto)
        cel.formula = texto
