"""Reglas para las hojas copiadas y derivadas (spec 1.5, F-D4 y F-D5).

Las hojas que no son APU ni PRESUPUESTO se copian con su aspecto y sus fórmulas, y se les quitan las
causas de error con reglas puntuales, antes de la reescritura general de referencias (`Contexto`):

1. **Por número de partida → referencia directa.**
   `INDEX(PRESUPUESTO!D…,MATCH($A8,PRESUPUESTO!B…,0))` y `SUMIF(PRESUPUESTO!B…,$A8,PRESUPUESTO!X…)`
   pasan a `PRESUPUESTO!$X$<fila>`: con números de partida repetidos (H4) el MATCH tomaba la primera
   fila y el SUMIF sumaba las dos.
2. **INDIRECT a un APU → nombre definido.** `INDIRECT("'APU-"&TEXT($A8,"00")&"'!$F$28")` pasa a
   `APU_01_REND`: el rótulo sale del encabezado de la columna (REND., Materiales…), no de la
   dirección escrita en el texto, que es la que estaba desalineada (C1, H6).
3. **PROCURA sin AUX.** La cantidad de cada insumo es Σ consumo/u × cantidad de cada partida, con
   SUMIF directos sobre las columnas B y H de los APU uniformes; el escombro total es Σ
   `APU_xx_ESC` × cantidad. Las filas "Dif. vs presupuesto" pasan a dar 0 (H7, H8).
4. **RESUMEN.** Un monto de capítulo con `#REF!` se enlaza al subtotal de su capítulo en PRESUPUESTO
   si el capítulo existe (H10); si no existe, vale 0 (ninguna partida lo compone).

Una fórmula que después de esto sigue sin poder conservarse (vínculo externo, `#REF!`, hoja que no
sale, INDIRECT sin equivalente) se sustituye por su valor y queda anotada en TRAZABILIDAD.
"""

from __future__ import annotations

import re

from adapters.hoja_empresa.escritor.contexto import Contexto
from adapters.hoja_empresa.escritor.formulas import Ref, analizar_ref, cita, letra, reescribir
from adapters.hoja_empresa.escritor.hoja import HojaSalida
from adapters.hoja_empresa.modelo import Rotulo, TipoFilaEspecial, clave
from adapters.hoja_empresa.perfil import normalizar

__all__ = ["transformar_hoja"]

_CELDA_TXT = r"\$?[A-Z]{1,3}\$?\d+"
_COL_RANGO = r"\$?([A-Z]{1,3})\$?\d+:\$?[A-Z]{1,3}\$?\d+"
_ENCABEZADO_ROTULO = (
    ("rend", Rotulo.REND),
    ("escombro", Rotulo.ESC),
    ("materiales", Rotulo.MAT),
    ("mano de", Rotulo.MO),
    ("equipos", Rotulo.EQ),
    ("transp", Rotulo.TR),
    ("costo directo", Rotulo.CD),
    ("admón", Rotulo.ADM),
    ("admon", Rotulo.ADM),
    ("sub-total", Rotulo.SUB),
    ("subtotal", Rotulo.SUB),
    ("utilidad", Rotulo.UTI),
    ("p.u.", Rotulo.PU),
    ("precio unitario", Rotulo.PU),
)


def _hoja_rx(nombre: str) -> str:
    return "(?:'" + re.escape(nombre.replace("'", "''")) + "'|" + re.escape(nombre) + ")"


def _valor_clave(h: HojaSalida, texto: str) -> int | None:
    r = analizar_ref(texto)
    if not isinstance(r, Ref) or not r.es_celda or r.hoja is not None:
        return None
    cel = h.celdas.get((r.f1, r.c1))
    if cel is None:
        return None
    v = cel.valor if cel.formula is None else cel.respaldo
    try:
        n = int(str(v))
    except (TypeError, ValueError):
        try:
            from decimal import Decimal

            d = Decimal(str(v))
            n = int(d) if d == d.to_integral_value() else None
        except Exception:  # texto u otro: no es un número de partida
            return None
    return n if n is not None and n > 0 else None


def _por_partida(ctx: Contexto, h: HojaSalida, formula: str) -> str:
    pres = _hoja_rx(ctx.hoja_presupuesto)
    col_num_b = ctx.perfil.columnas_presupuesto["numero"]
    b = rf"\$?{col_num_b}\$?\d+:\$?{col_num_b}\$?\d+"
    destino = cita(ctx.hoja_presupuesto)

    def directo(col: str, clave_txt: str, original: str) -> str:
        n = _valor_clave(h, clave_txt)
        p = ctx.partida(n) if n is not None else None
        if p is None:
            return original
        return f"{destino}!${col.upper()}${p.fila}"

    rx_index = re.compile(
        rf"INDEX\(\s*{pres}!{_COL_RANGO}\s*,\s*MATCH\(\s*({_CELDA_TXT})\s*,\s*{pres}!{b}\s*,"
        r"\s*0\s*\)\s*\)",
        re.IGNORECASE,
    )
    rx_sumif = re.compile(
        rf"SUMIF\(\s*{pres}!{b}\s*,\s*({_CELDA_TXT})\s*,\s*{pres}!{_COL_RANGO}\s*\)",
        re.IGNORECASE,
    )
    formula = rx_index.sub(lambda m: directo(m.group(1), m.group(2), m.group(0)), formula)
    return rx_sumif.sub(lambda m: directo(m.group(2), m.group(1), m.group(0)), formula)


def _rotulo_por_encabezado(h: HojaSalida, fila: int, col: int) -> Rotulo | None:
    for f in range(fila - 1, max(fila - 40, 0), -1):
        cel = h.celdas.get((f, col))
        if cel is None or cel.formula is not None or not isinstance(cel.valor, str):
            continue
        n = normalizar(cel.valor)
        for clave_t, r in _ENCABEZADO_ROTULO:
            if clave_t in n:
                return r
        return None
    return None


def _indirect_apu(ctx: Contexto, h: HojaSalida, fila: int, col: int, formula: str) -> str:
    prefijo = re.escape(ctx.perfil.prefijo_apu)
    rx = re.compile(
        rf"INDIRECT\(\s*\"'?{prefijo}-\"\s*&\s*TEXT\(\s*({_CELDA_TXT})\s*,\s*\"0+\"\s*\)\s*&\s*"
        r"\"'?!\$?([A-Z]{1,3})\$?(\d+)\"\s*\)",
        re.IGNORECASE,
    )

    def nombre(m: re.Match[str]) -> str:
        n = _valor_clave(h, m.group(1))
        p = ctx.partida(n) if n is not None else None
        if p is None or p.hoja_apu not in ctx.unidos:
            return m.group(0)
        r = _rotulo_por_encabezado(h, fila, col)
        if r is None:
            apu = ctx.apu(p.hoja_apu)
            ref = f"{m.group(2).upper()}{m.group(3)}"
            r = next((x for x, c in (apu.rotulos.items() if apu else ()) if c.ref == ref), None)
        if r is None or r not in (
            Rotulo.MAT,
            Rotulo.MO,
            Rotulo.EQ,
            Rotulo.TR,
            Rotulo.CD,
            Rotulo.ADM,
            Rotulo.SUB,
            Rotulo.UTI,
            Rotulo.PU,
            Rotulo.REND,
            Rotulo.ESC,
        ):
            return m.group(0)
        return ctx.nombre_rotulo(p.hoja_apu, r)

    return rx.sub(nombre, formula)


def _lee_apus_o_aux(ctx: Contexto, formula: str) -> bool:
    hojas = set(ctx.unidos) | ctx.quitadas
    for parte in re.findall(r"(?:'(?:[^']|'')+'|[A-Za-z0-9_.\-]+)!", formula):
        hoja = parte[:-1].strip("'").replace("''", "'")
        if hoja in hojas:
            return True
    return False


def _texto_fila(h: HojaSalida, fila: int) -> str:
    partes = []
    for c in range(1, 4):
        cel = h.celdas.get((fila, c))
        if cel is not None and cel.formula is None and isinstance(cel.valor, str):
            partes.append(cel.valor)
    return normalizar(" ".join(partes))


def _procura(ctx: Contexto, h: HojaSalida, fila: int, formula: str) -> str | None:
    if not _lee_apus_o_aux(ctx, formula):
        return None
    assert ctx.maqueta is not None
    pres = cita(ctx.hoja_presupuesto)
    g = ctx.perfil.columnas_presupuesto["cantidad"]
    partidas = [(hoja, p) for hoja, p in ctx.unidos.items()]
    if "SUMIF(" in formula.upper():
        m = re.search(r"SUMIF\([^,]+,\s*\$?([A-Z]{1,3})\$?\d+", formula, re.IGNORECASE)
        if m is None:
            return None
        col = m.group(1).upper()
        ini, fin = ctx.maqueta.primera_linea, ctx.maqueta.ultima_linea
        terminos = [
            f"SUMIF({cita(hoja)}!$B${ini}:$B${fin},${col}{fila},"
            f"{cita(hoja)}!$H${ini}:$H${fin})*{pres}!${g}${p.fila}"
            for hoja, p in partidas
        ]
        return "=" + ("+".join(terminos) if terminos else "0")
    if "escombro" in _texto_fila(h, fila):
        terminos = [
            f"{ctx.nombre_rotulo(hoja, Rotulo.ESC)}*{pres}!${g}${p.fila}" for hoja, p in partidas
        ]
        return "=" + ("+".join(terminos) if terminos else "0")
    return None


def _resumen(ctx: Contexto, h: HojaSalida, fila: int, formula: str) -> str | None:
    if "#REF!" not in formula.upper():
        return None
    if not re.fullmatch(r"=\s*\+?\s*(?:'[^']+'|[^!]+)!#REF!\s*", formula, re.IGNORECASE):
        return None
    etiqueta = _texto_fila(h, fila)
    if not etiqueta:
        return None
    especiales = sorted(ctx.libro.filas_especiales, key=lambda e: e.fila)
    q = ctx.perfil.columnas_presupuesto["monto"]
    for i, e in enumerate(especiales):
        if e.tipo is TipoFilaEspecial.CAPITULO and normalizar(e.texto) == etiqueta:
            sub = next(
                (
                    x
                    for x in especiales[i + 1 :]
                    if x.tipo in (TipoFilaEspecial.SUBTOTAL, TipoFilaEspecial.SUMA)
                ),
                None,
            )
            if sub is not None:
                return f"={cita(ctx.hoja_presupuesto)}!${q}${sub.fila}"
    return None


def _motivo(ctx: Contexto, formula: str) -> str:
    u = formula.upper()
    if "#REF!" in u:
        return "contenía #REF!"
    if "[" in formula:
        return "leía otro libro (vínculo externo)"
    if "INDIRECT(" in u:
        return "INDIRECT a un APU que no existe (la fila no tiene partida con APU unido)"
    if any(f"{q}!" in formula or f"{cita(q)}!" in formula for q in ctx.quitadas):
        return "leía una hoja que no sale en la devolución (AUX o plantilla)"
    return "leía una celda sin equivalente en la devolución"


def transformar_hoja(
    ctx: Contexto, h: HojaSalida, resueltas: set[tuple[int, int]] | None = None
) -> None:
    """Aplica las reglas y la reescritura general a todas las fórmulas de una hoja copiada."""
    resueltas = resueltas or set()
    es_procura = ctx.es(h.nombre, "PROCURA")
    es_resumen = ctx.es(h.nombre, "RESUMEN")
    for (f, c), cel in sorted(h.celdas.items()):
        if cel.formula is None or (f, c) in resueltas:
            continue
        original = cel.formula
        # La explosión de PROCURA ya sale en coordenadas de la maqueta: no se vuelve a mapear.
        final = _procura(ctx, h, f, original) if es_procura else None
        if final is None:
            texto = _resumen(ctx, h, f, original) if es_resumen else None
            if texto is None:
                texto = _por_partida(ctx, h, original)
                texto = _indirect_apu(ctx, h, f, c, texto)
            final = reescribir(texto, lambda t: ctx.rango(t, h.nombre))
        if final is not None and "INDIRECT(" in final.upper():
            final = None
        if final is None:
            ctx.pendientes.append((h.nombre, f, c, original, _motivo(ctx, original)))
            cel.formula = None
            cel.valor = None
        else:
            cel.formula = final
    _validaciones(ctx, h)
    _condicionales(ctx, h)


def _validaciones(ctx: Contexto, h: HojaSalida) -> None:
    quedan = []
    for rango, op in h.validaciones:
        fuente = op.get("source") or op.get("value")
        if isinstance(fuente, str) and fuente.startswith("="):
            nueva = reescribir(fuente, lambda t: ctx.rango(t, h.nombre))
            if nueva is None:
                continue
            op["source" if "source" in op else "value"] = nueva
        quedan.append((rango, op))
    h.validaciones = quedan


def _condicionales(ctx: Contexto, h: HojaSalida) -> None:
    quedan = []
    for rango, op, estilo in h.condicionales:
        claves = ["value", "minimum", "maximum"]
        if op.get("type") == "formula":
            claves.append("criteria")
        ok = True
        for k in claves:
            v = op.get(k)
            if not (isinstance(v, str) and v.startswith("=")):
                continue
            nueva = reescribir(v, lambda t: ctx.rango(t, h.nombre))
            if nueva is None:
                ok = False
                break
            op[k] = nueva
        if ok:
            quedan.append((rango, op, estilo))
    h.condicionales = quedan


def anotar_pendiente(ctx: Contexto, hoja: str, f: int, c: int, valor: object, motivo: str) -> None:
    ctx.salida.anotar(
        "Fórmula sustituida por su valor", valor, clave(hoja, f"{letra(c)}{f}"), motivo
    )
