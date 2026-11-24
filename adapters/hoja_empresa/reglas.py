"""Reglas del libro L1-L9 (spec 1.5 §3) sobre un `LibroLeido`.

Cada regla compara lo que el libro **dice** (sus fórmulas) con lo que el libro **calcula** (sus
valores guardados) y con la forma real de cada APU (sus rótulos). Así detecta las causas raíz C1-C6
del análisis de los libros de la empresa sin ejecutar ninguna fórmula: las fórmulas se leen como
texto con expresiones regulares propias y los `INDIRECT` se resuelven con el valor guardado de las
celdas que concatenan (lo mismo que haría Excel en el momento en que se guardó el libro).

Principios:

- **La celda de origen siempre.** Todo hallazgo lleva en `origen_ids` las celdas `HOJA!REF`
  implicadas: la que tiene la fórmula, la que lee y, si la hay, la que debería leer.
- **Descripción para un administrador.** Cada descripción dice qué celda, qué lee, qué debería leer
  y qué efecto tiene, sin jerga de hoja de cálculo más allá de la referencia de celda.
- **El auditor no decide la intención** (F-D7). Lo que puede ser intencional (una utilidad
  escrita a mano, un rendimiento literal) es ADVERTENCIA "a confirmar"; lo que no admite dos
  lecturas es ERROR.
- **Sin falsos positivos por forma.** Una celda que lee el subtotal del bloque (`G12`) en lugar de
  la línea del resumen (`G43 = G12`) lee bien: se acepta toda celda que el rótulo lee o que lee al
  rótulo por referencia pura ("clase de equivalencia" del rótulo).
- **Determinismo.** Mismo libro, mismos hallazgos y en el mismo orden (regla, hoja, fila, columna).

Límites declarados:

- Solo se resuelven `INDIRECT` cuyo argumento concatena textos, celdas y `TEXT(celda,"00")`. Otro
  `INDIRECT` no se juzga (no se adivina).
- L3 compara lecturas puras (directa, `=+X`, nombre de una celda, `N()`, `IFERROR(X,…)`,
  `IF(…,"",X)`, `1/(1/X)`, `INDIRECT` resuelto y `VLOOKUP(código,PRECIOS,k,…)`); no recalcula
  aritmética (eso es F1, con el motor del núcleo).
- L4 y L6 solo miran los APU unidos a una partida: una plantilla sin partida no entra al
  presupuesto (L2 la informa). L4 y los complementos de L1 y L5 viven en `reglas_calculo.py`.
- Los impactos de L6 son informativos: suponen que el resto del APU no cambia.
- En PROCURA, L9 no informa la fila "Dif. vs Costo Directo" si alguna "Dif. vs componente" ya dio
  hallazgo: el Costo Directo es la suma de los cuatro componentes y la contaría dos veces.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterator
from decimal import Decimal

from adapters.hoja_empresa import reglas_calculo as calc
from adapters.hoja_empresa.guardia import MAX_FILAS_HOJA
from adapters.hoja_empresa.modelo import (
    VINCULO_ILEGIBLE,
    ApuLeido,
    Celda,
    LibroLeido,
    PartidaLeida,
    Rotulo,
    clave,
)
from adapters.hoja_empresa.perfil import Perfil, cargar_perfil, normalizar
from adapters.hoja_empresa.reglas_contexto import (
    _CERO,
    _NOMBRE_ROTULO,
    _ORDEN_DESGLOSE,
    _RX_ARIT_LITERALES,
    _RX_DIVISOR_LITERAL,
    _RX_FACTOR_DECIMAL,
    _RX_SECCION,
    _TOL_CENTAVO,
    _TOL_CUADRE,
    _centavos,
    _Contexto,
    _filas,
    _fmt,
    _fu,
    _iguales,
    _lectura_precios,
    _n0,
    _num,
    _partir,
    _sin_textos,
    _valor,
)
from core.contracts.verificacion import Hallazgo, Severidad

__all__ = ["REGLAS_LIBRO", "reglas_del_libro"]

REGLAS_LIBRO: tuple[tuple[str, str], ...] = (
    ("L1", "Referencia desalineada"),
    ("L2", "Enlace partida ↔ APU roto"),
    ("L3", "Valor guardado ≠ fórmula"),
    ("L4", "Componente fuera del total"),
    ("L5", "Referencia rota o externa"),
    ("L6", "Parámetro global sobrescrito"),
    ("L7", "Dato dentro de fórmula"),
    ("L8", "Número de partida duplicado"),
    ("L9", "Cuadre interno"),
)

# --- L1 Referencia desalineada --------------------------------------------------------------------


def _rotulo_de_columna(ctx: _Contexto) -> dict[str, Rotulo]:
    cp = ctx.perfil.columnas_presupuesto
    out = {cp["rendimiento"]: Rotulo.REND}
    out.update(dict(zip(ctx.perfil.columnas_desglose, _ORDEN_DESGLOSE, strict=False)))
    return out


def _l1_comparar(
    ctx: _Contexto,
    origen: Celda,
    leida: Celda,
    apu: ApuLeido,
    r: Rotulo,
    quien: str,
    efecto: str,
    apu_leido: str | None = None,
) -> Hallazgo | None:
    """Compara la celda leída con la clase del rótulo `r` en `apu`; hallazgo si no coincide."""
    correcta, equivalentes = ctx.equivalentes(apu, r)
    v_leido = ctx.an.valor(leida)
    if apu_leido is None and str(leida) in equivalentes:
        return None
    nombre = _NOMBRE_ROTULO[r]
    if correcta is None:
        if _n0(v_leido) == 0:
            return None
        return Hallazgo(
            regla="L1",
            severidad=Severidad.ERROR,
            descripcion=(
                f"{origen} ({quien}) lee {leida} (valor {_valor(v_leido)}) como {nombre}, pero "
                f"{apu.hoja} no tiene ese rótulo: el valor correcto es 0. {efecto}"
            ),
            origen_ids=(str(origen), str(leida)),
            valor_observado=_num(v_leido),
            valor_esperado=_CERO,
        )
    v_ok = ctx.an.valor(correcta)
    if apu_leido is not None:
        motivo = (
            f"lee la hoja {apu_leido}, pero la partida está unida a {apu.hoja}: el {nombre} "
            f"correcto está en {correcta}"
        )
    else:
        motivo = f"el {nombre} de {apu.hoja} está en {correcta}"
    return Hallazgo(
        regla="L1",
        severidad=Severidad.ERROR,
        descripcion=(
            f"{origen} ({quien}) lee {leida} (valor {_valor(v_leido)}) como {nombre}; {motivo} "
            f"(valor {_valor(v_ok)}). {efecto}"
        ),
        origen_ids=(str(origen), str(leida), str(correcta)),
        valor_observado=_num(v_leido),
        valor_esperado=_num(v_ok),
    )


def _l1_presupuesto(ctx: _Contexto) -> list[Hallazgo]:
    mapa = _rotulo_de_columna(ctx)
    out: list[Hallazgo] = []
    for p in ctx.libro.partidas:
        if p.hoja_apu is None or p.hoja_apu not in ctx.apus:
            continue
        apu = ctx.apus[p.hoja_apu]
        for letra, r in mapa.items():
            origen = Celda(ctx.h_pres, f"{letra}{p.fila}")
            f = ctx.an.formula(origen)
            if not f:
                continue
            for lec in ctx.an.lecturas(f, ctx.h_pres):
                if lec.destino.hoja not in ctx.hojas_apu:
                    continue
                otro = lec.destino.hoja if lec.destino.hoja != apu.hoja else None
                efecto = (
                    "Efecto: la columna REND. muestra un rendimiento que no es el de la partida."
                    if r is Rotulo.REND
                    else f"Efecto: el {_NOMBRE_ROTULO[r]} de la fila no es el de su APU."
                )
                h = _l1_comparar(
                    ctx, origen, lec.destino, apu, r, f"partida {p.numero}", efecto, otro
                )
                if h is not None:
                    out.append(h)
    return out


def _l1_cronograma(ctx: _Contexto, hoja: str) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    for k in ctx.formulas_de.get(hoja, ()):
        f = ctx.libro.formulas[k]
        origen = Celda(hoja, k.split("!", 1)[1])
        _, fila = _partir(origen.ref)
        for lec in ctx.an.lecturas(f, hoja):
            apu = ctx.apus.get(lec.destino.hoja)
            if apu is None:
                continue
            numero = next(
                (v for c, v in ctx.por_fila.get((hoja, fila), ()) if isinstance(v, Decimal)), None
            )
            quien = f"partida {int(numero)}" if numero is not None else f"fila {fila}"
            v = _n0(ctx.an.valor(lec.destino))
            efecto = (
                "Efecto: la duración de la partida da 0 días y la curva S, el avance planificado "
                "y la holgura quedan falseados."
                if v == 0
                else "Efecto: la duración de la partida se calcula con otro rendimiento y la "
                "curva S y el avance planificado quedan falseados."
            )
            h = _l1_comparar(ctx, origen, lec.destino, apu, Rotulo.REND, quien, efecto)
            if h is not None:
                out.append(h)
    return out


def _l1_aux(ctx: _Contexto, hoja: str) -> list[Hallazgo]:
    """AUX lee filas fijas de cada APU: una fila por línea de insumo y una celda de escombro."""
    filas_leidas: dict[str, set[int]] = defaultdict(set)
    primera: dict[str, str] = {}
    escombro: dict[str, tuple[Celda, Celda]] = {}
    for k in ctx.formulas_de.get(hoja, ()):
        origen = Celda(hoja, k.split("!", 1)[1])
        _, fila = _partir(origen.ref)
        for lec in ctx.an.lecturas(ctx.libro.formulas[k], hoja):
            if lec.destino.hoja not in ctx.apus:
                continue
            ah = lec.destino.hoja
            if lec.fila_variable:
                filas_leidas[ah].add(_partir(lec.destino.ref)[1])
                primera.setdefault(ah, str(origen))
            elif _seccion_escombro(ctx, hoja, fila):
                escombro.setdefault(ah, (origen, lec.destino))
    out: list[Hallazgo] = []
    for ah in sorted(set(filas_leidas) | set(escombro), key=ctx.libro.hojas.index):
        apu = ctx.apus[ah]
        col_cod = ctx.perfil.columnas_linea["codigo"]
        lineas = {_partir(ln.celda_codigo.ref)[1]: ln.codigo for ln in apu.lineas}
        partes: list[str] = []
        origenes: list[str] = []
        observado = esperado = None
        if ah in filas_leidas:
            leidas = filas_leidas[ah]
            faltan = sorted(set(lineas) - leidas)
            de_mas = sorted(
                f
                for f in leidas - set(lineas)
                if ctx.an.valor(Celda(ah, f"{col_cod}{f}")) not in (None, "")
            )
            if faltan:
                codigos = ", ".join(f"{lineas[f]} (fila {f})" for f in faltan)
                partes.append(f"deja sin leer {len(faltan)} línea(s) de insumo reales: {codigos}")
                origenes.extend(f"{ah}!{col_cod}{f}" for f in faltan)
            if de_mas:
                textos = ", ".join(
                    f"{f} ({_valor(ctx.an.valor(Celda(ah, f'{col_cod}{f}')))})" for f in de_mas
                )
                partes.append(f"lee filas que no son líneas de insumo: {textos}")
            if partes:
                origenes.insert(0, primera[ah])
                partes[0] = (
                    f"AUX lee de {ah} las filas fijas {_filas(leidas)} para la lista de compras; "
                    + partes[0]
                )
        if ah in escombro:
            origen, leida = escombro[ah]
            correcta, equivalentes = ctx.equivalentes(apu, Rotulo.ESC)
            v_leido = ctx.an.valor(leida)
            v_ok = ctx.an.valor(correcta) if correcta is not None else _CERO
            if str(leida) not in equivalentes and _n0(v_leido) != _n0(v_ok):
                donde = (
                    f"en vez de {correcta} (valor {_valor(v_ok)})"
                    if correcta is not None
                    else "pero ese APU no tiene bloque de escombro (debería ser 0)"
                )
                partes.append(
                    f"{origen} toma el escombro de {leida} (valor {_valor(v_leido)}) {donde}"
                )
                origenes.extend([str(origen), str(leida)])
                if correcta is not None:
                    origenes.append(str(correcta))
                observado, esperado = _num(v_leido), _n0(v_ok)
        if not partes:
            continue
        out.append(
            Hallazgo(
                regla="L1",
                severidad=Severidad.ERROR,
                descripcion=(
                    "; ".join(partes)
                    + ". Efecto: PROCURA (lista de compras y escombro) no corresponde al "
                    "presupuesto."
                ),
                origen_ids=tuple(dict.fromkeys(origenes)),
                valor_observado=observado,
                valor_esperado=esperado,
            )
        )
    return out


def _seccion_escombro(ctx: _Contexto, hoja: str, fila: int) -> bool:
    """¿La fila está bajo un encabezado de AUX que habla de escombro?"""
    pref = normalizar(ctx.perfil.prefijo_apu)
    for f in range(fila, 0, -1):
        t = normalizar(ctx.etiqueta(hoja, f, hasta_col=1))
        if t and not t.startswith(pref):
            return "escombro" in t
    return False


def _l1_otras(ctx: _Contexto, hoja: str) -> list[Hallazgo]:
    """Otras hojas: solo se juzga lo que el rótulo de la fila permite saber (escombro o
    rendimiento); cualquier otra lectura de un APU no tiene un rótulo esperado y no se adivina."""
    out: list[Hallazgo] = []
    for k in ctx.formulas_de.get(hoja, ()):
        f = ctx.libro.formulas[k]
        origen = Celda(hoja, k.split("!", 1)[1])
        _, fila = _partir(origen.ref)
        lecs = [x for x in ctx.an.lecturas(f, hoja) if x.destino.hoja in ctx.apus]
        if not lecs:
            continue
        t = normalizar(ctx.etiqueta(hoja, fila))
        if "escombro" in t:
            r = Rotulo.ESC
        elif "rendimiento" in t:
            r = Rotulo.REND
        else:
            continue
        for lec in lecs:
            h = _l1_comparar(
                ctx,
                origen,
                lec.destino,
                ctx.apus[lec.destino.hoja],
                r,
                f"«{ctx.etiqueta(hoja, fila)[:50]}»",
                f"Efecto: {hoja} usa otro dato del APU como {_NOMBRE_ROTULO[r]}.",
            )
            if h is not None:
                out.append(h)
    return out


def _l1(ctx: _Contexto) -> list[Hallazgo]:
    out = _l1_presupuesto(ctx)
    for hoja in ctx.libro.hojas:
        if hoja in ctx.hojas_apu or hoja == ctx.h_pres:
            continue
        if ctx.es_hoja(hoja, "CRONOGRAMA"):
            out.extend(_l1_cronograma(ctx, hoja))
        elif ctx.es_hoja(hoja, "AUX"):
            out.extend(_l1_aux(ctx, hoja))
        else:
            out.extend(_l1_otras(ctx, hoja))
    return out


# --- L2 Enlace partida ↔ APU roto -----------------------------------------------------------------


def _l2(ctx: _Contexto) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    libro = ctx.libro
    titulo = ctx.perfil.celda_titulo_apu
    reclamos: dict[int, list[ApuLeido]] = defaultdict(list)
    for a in libro.apus:
        if a.fila_presupuesto is not None:
            reclamos[a.fila_presupuesto].append(a)
    for fila in sorted(reclamos):
        apus = reclamos[fila]
        if len(apus) < 2:
            continue
        p = ctx.partida_por_fila.get(fila)
        ganador = p.hoja_apu if p is not None else None
        nombres = " y ".join(a.hoja for a in apus)
        quien = f"la fila {fila} de {ctx.h_pres}" + (f" (partida {p.numero})" if p else "")
        desc = (
            f"Las hojas {nombres} tienen el mismo título {titulo} = +{ctx.h_pres}!D{fila}: las dos "
            f"dicen ser {quien}. "
        )
        desc += (
            f"Silice la unió a {ganador} (coincide por número o por P.U. guardado). "
            if ganador
            else "Ninguna se pudo unir. "
        )
        desc += (
            "Efecto: el título del otro APU no corresponde a su partida y cualquier fórmula que "
            "dependa del nombre de la hoja (parche manual, causa C2) puede leer el APU equivocado."
        )
        out.append(
            Hallazgo(
                regla="L2",
                severidad=Severidad.ERROR,
                descripcion=desc,
                origen_ids=tuple(f"{a.hoja}!{titulo}" for a in apus) + (f"{ctx.h_pres}!D{fila}",),
            )
        )
    for a in libro.apus:
        p = ctx.partida_de_apu.get(a.hoja)
        if p is None or a.fila_presupuesto is None or a.fila_presupuesto == p.fila:
            continue
        nombrada = ctx.partida_por_fila.get(a.fila_presupuesto)
        out.append(
            Hallazgo(
                regla="L2",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{a.hoja} está unido a la fila {p.fila} de {ctx.h_pres} (partida {p.numero}, "
                    f"«{p.descripcion[:60]}»), pero su título {titulo} apunta a la fila "
                    f"{a.fila_presupuesto}"
                    + (f" («{nombrada.descripcion[:60]}»)" if nombrada else "")
                    + ". Efecto: el APU impreso lleva el nombre de otra partida."
                ),
                origen_ids=(f"{a.hoja}!{titulo}", f"{ctx.h_pres}!D{p.fila}"),
            )
        )
    for p in libro.partidas:
        if p.hoja_apu is None:
            out.append(
                Hallazgo(
                    regla="L2",
                    severidad=Severidad.ERROR,
                    descripcion=(
                        f"La partida {p.numero} (fila {p.fila} de {ctx.h_pres}, "
                        f"«{p.descripcion[:60]}») no tiene APU: ningún título la nombra y no hay "
                        f"una hoja libre con su número o con su P.U. Efecto: su precio no se puede "
                        f"recalcular ni rastrear."
                    ),
                    origen_ids=(f"{ctx.h_pres}!B{p.fila}",),
                )
            )
    usados = set(ctx.partida_de_apu)
    plantillas = [a for a in libro.apus if a.hoja not in usados]
    for a in libro.apus:
        if a.hoja in usados and "#REF!" in (a.titulo or ""):
            out.append(
                Hallazgo(
                    regla="L2",
                    severidad=Severidad.ERROR,
                    descripcion=(
                        f"El título de {a.hoja} ({titulo}) es #REF!: la partida que nombraba se "
                        f"borró. Efecto: el APU impreso no dice a qué partida pertenece."
                    ),
                    origen_ids=(f"{a.hoja}!{titulo}",),
                )
            )
    if plantillas:
        rotos = [a.hoja for a in plantillas if "#REF!" in (a.titulo or "")]
        out.append(
            Hallazgo(
                regla="L2",
                severidad=Severidad.INFO,
                descripcion=(
                    f"Hojas de plantilla sin partida: {', '.join(a.hoja for a in plantillas)}. "
                    "Ninguna fila del presupuesto las usa; no se copian a la devolución"
                    + (f" (título #REF! en {', '.join(rotos)})" if rotos else "")
                    + "."
                ),
                origen_ids=tuple(f"{a.hoja}!{titulo}" for a in plantillas),
            )
        )
    return out


# --- L3 Valor guardado ≠ fórmula ------------------------------------------------------------------


def _l3(ctx: _Contexto) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    col_pu = ctx.perfil.columnas_presupuesto["precio_unitario"]
    col_monto = ctx.perfil.columnas_presupuesto["monto"]
    for k in ctx.orden:
        f = ctx.libro.formulas[k]
        hoja, ref = k.split("!", 1)
        lec = ctx.an.lectura_pura(f, hoja)
        destino = lec.destino if lec is not None else None
        if destino is None and hoja in ctx.hojas_apu:
            destino = _lectura_precios(ctx, f, hoja)
        if destino is None or str(destino) == k:
            continue
        guardado = ctx.libro.valores.get(k)
        leido = ctx.an.valor(destino)
        if isinstance(leido, str) and leido.startswith("#"):
            continue  # error leído: lo informa L5 y el IFERROR de la fórmula lo tapa
        if lec is not None and lec.numerica:
            leido = _n0(leido)
        if _iguales(guardado, leido):
            continue
        letras, fila = _partir(ref)
        p = ctx.partida_por_fila.get(fila) if hoja == ctx.h_pres else None
        if hoja in ctx.hojas_apu:
            p = ctx.partida_de_apu.get(hoja)
        dif = _num(leido)
        g = _num(guardado)
        impacto = None
        mueve = p is not None and p.cantidad != 0
        if hoja == ctx.h_pres and letras == col_pu and mueve and dif is not None and g is not None:
            impacto = _centavos(p.cantidad * (dif - g))
        elif hoja == ctx.h_pres and letras == col_monto and dif is not None and g is not None:
            impacto = _centavos(dif - g)
            mueve = True
        elif hoja == ctx.h_pres and letras not in (col_pu, col_monto):
            mueve = False
        sev = Severidad.ERROR if mueve else Severidad.ADVERTENCIA
        efecto = (
            "Efecto: el monto de la partida cambia al recalcular el libro."
            if mueve
            else "Efecto: el libro no estaba recalculado; al abrirlo en Excel el valor cambia"
            + (" (la partida tiene cantidad 0, no mueve el total)." if p is not None else ".")
        )
        out.append(
            Hallazgo(
                regla="L3",
                severidad=sev,
                descripcion=(
                    f"{k} guarda {_valor(guardado)}, pero su fórmula lee {destino}, que vale "
                    f"{_valor(leido)}. {efecto}"
                ),
                impacto=impacto,
                origen_ids=(k, str(destino)),
                valor_observado=g,
                valor_esperado=dif,
            )
        )
    return out + _l3_plantilla(ctx)


def _l3_plantilla(ctx: _Contexto) -> list[Hallazgo]:
    """P.U. de PRESUPUESTO parcheado a mano contra la fórmula de la plantilla (por número): L2.

    Ruling del líder (2026-10-13, bitácora 1.5): esto NO es L3. Los valores guardados de estos
    libros coinciden con sus fórmulas (Excel los guardó recalculados); lo que hay es un ENLACE
    parcheado a
    mano y atado al nombre de la hoja. Por eso se informa como L2 (enlace partida-APU frágil),
    ADVERTENCIA y sin impacto: la cifra es el riesgo si la fórmula volviera a la de la plantilla, no
    un error del total entregado.

    La fórmula de la plantilla lee el P.U. con `INDIRECT("'APU-"&TEXT($Bnn,"00")&"'!…")`: la hoja
    del NÚMERO de la partida. En los libros C esa fórmula se sustituyó a mano por una referencia
    directa a una hoja con otro nombre (`='APU-08'!G44` en la partida 6). El valor guardado sale del
    parche; la fórmula de la plantilla, recalculada sobre el mismo libro, daría otro (es lo que pasa
    si se recalcula con la plantilla, se renombran o se reordenan las hojas: hallazgo H5, causa C2).
    Solo se compara la columna del P.U. (la que mueve el monto) y solo si la hoja del número existe.
    """
    out: list[Hallazgo] = []
    col_pu = ctx.perfil.columnas_presupuesto["precio_unitario"]
    for p in ctx.libro.partidas:
        k = clave(ctx.h_pres, f"{col_pu}{p.fila}")
        f = ctx.libro.formulas.get(k)
        lec = ctx.an.lectura_pura(f, ctx.h_pres) if f else None
        if lec is None or lec.via_indirect or lec.destino.hoja not in ctx.hojas_apu:
            continue
        por_numero = ctx.an.hoja(f"{ctx.perfil.prefijo_apu}-{p.numero:02d}")
        if por_numero is None or por_numero == lec.destino.hoja:
            continue
        plantilla = Celda(por_numero, lec.destino.ref)
        guardado = ctx.libro.valores.get(k)
        segun_plantilla = _n0(ctx.an.valor(plantilla))
        if _iguales(guardado, segun_plantilla):
            continue
        g = _n0(guardado)
        riesgo = _centavos(p.cantidad * (segun_plantilla - g)) if p.cantidad != 0 else None
        efecto = (
            f"el monto de la partida cambiaría en {_fmt(riesgo)} USD sin IVA."
            if riesgo is not None
            else "la partida tiene cantidad 0 y no mueve el total, pero su P.U. cambiaría."
        )
        out.append(
            Hallazgo(
                regla="L2",
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"{k} (partida {p.numero}) guarda {_valor(guardado)}, coherente con su "
                    "fórmula, pero esa "
                    f"fórmula se cambió a mano para leer {lec.destino}; la de la plantilla lee la "
                    f"hoja del número de partida, {plantilla}, que vale {_valor(segun_plantilla)}. "
                    "El enlace depende del nombre de la hoja: si el libro se recalcula con la "
                    f"fórmula de la plantilla o se renombran o reordenan las hojas, {efecto}"
                ),
                origen_ids=(k, str(lec.destino), str(plantilla)),
                valor_observado=g,
                valor_esperado=segun_plantilla,
            )
        )
    return out


# --- L5 Referencia rota o externa -----------------------------------------------------------------


def _archivo(destino: str) -> str:
    """Solo el nombre del archivo de un vínculo (sin ruta de red ni de disco)."""
    from urllib.parse import unquote

    return unquote(re.split(r"[\\/]", destino.rstrip("/\\"))[-1]) or destino


def _l5(ctx: _Contexto) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    por_hoja: dict[str, list[str]] = defaultdict(list)
    externas: dict[str, list[str]] = defaultdict(list)
    for k in ctx.orden:
        f = ctx.libro.formulas[k]
        hoja = k.split("!", 1)[0]
        if "#REF!" in f.upper():
            por_hoja[hoja].append(k)
        if re.search(r"\[\d+\]", _sin_textos(f)):
            externas[hoja].append(k)
    for hoja in sorted(por_hoja, key=ctx.libro.hojas.index):
        celdas = por_hoja[hoja]
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{len(celdas)} fórmula(s) de {hoja} con #REF! (la celda u hoja que citaban "
                    f"se borró): {', '.join(c.split('!', 1)[1] for c in celdas)}. Efecto: esas "
                    "celdas muestran #REF! o un valor que ya no se puede rastrear."
                ),
                origen_ids=tuple(celdas),
            )
        )
    for hoja in sorted(externas, key=ctx.libro.hojas.index):
        celdas = externas[hoja]
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"{len(celdas)} fórmula(s) de {hoja} leen otro libro: "
                    f"{', '.join(c.split('!', 1)[1] for c in celdas)}. Efecto: fuera del equipo "
                    "que tiene ese libro el valor no se puede recalcular."
                ),
                origen_ids=tuple(celdas),
            )
        )
    rotos = sorted(n for n, t in ctx.libro.nombres.items() if "#REF!" in t.upper())
    if rotos:
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{len(rotos)} nombre(s) definido(s) apuntan a #REF!: {', '.join(rotos)}. "
                    "Efecto: una fórmula que los use da #REF!; quedan de una hoja copiada o de "
                    "celdas borradas."
                ),
                origen_ids=tuple(f"nombre:{n}" for n in rotos),
            )
        )
    con_libro = sorted(
        (n for n, t in ctx.libro.nombres.items() if re.search(r"\[\d+\]", t)),
        key=lambda n: (len(n), n),
    )
    if con_libro:
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"{len(con_libro)} nombre(s) definido(s) apuntan a otro libro: "
                    f"{', '.join(con_libro)}. Efecto: fuera del equipo que tiene ese libro, "
                    "cualquier fórmula que los use da #REF! (la hoja se copió desde otro libro)."
                ),
                origen_ids=tuple(f"nombre:{n}" for n in con_libro),
            )
        )
    ilegibles = [v for v in ctx.libro.vinculos_externos if v.startswith(VINCULO_ILEGIBLE)]
    legibles = [v for v in ctx.libro.vinculos_externos if not v.startswith(VINCULO_ILEGIBLE)]
    for pieza in dict.fromkeys(v.removeprefix(VINCULO_ILEGIBLE) for v in ilegibles):
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"El libro guarda un vínculo a otro libro cuya relación («{pieza}») no se "
                    "pudo leer (XML dañado o con entidades): no se sabe a qué archivo apunta. "
                    "Efecto: Excel puede pedir actualizarlo al abrir; la devolución lo quita."
                ),
                origen_ids=(f"vinculo:{pieza}",),
            )
        )
    for destino in dict.fromkeys(_archivo(v) for v in legibles):
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"El libro guarda un vínculo a otro libro en una ruta de red: «{destino}». "
                    "Efecto: Excel pide actualizarlo al abrir; la devolución lo quita."
                ),
                origen_ids=(f"vinculo:{destino}",),
            )
        )
    return out


# --- L6 Parámetro global sobrescrito --------------------------------------------------------------


def _usa_nombre(formula: str | None, nombre: str, celda_param: Celda | None) -> bool:
    if not formula:
        return False
    sin = _sin_textos(formula)
    if re.search(rf"(?<![\w.]){re.escape(nombre)}(?![\w.(])", sin, re.I):
        return True
    if celda_param is not None:
        hoja, ref = celda_param.hoja, celda_param.ref
        letras, fila = _partir(ref)
        patron = rf"{re.escape(hoja)}'?!\$?{letras}\$?{fila}(?!\d)"
        return re.search(patron, sin) is not None
    return False


def _l6_porcentajes(ctx: _Contexto, apu: ApuLeido, p: PartidaLeida) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    params = ctx.libro.parametros
    col_pct = ctx.perfil.columna_porcentaje_apu
    casos = (
        (Rotulo.ADM, "ADMON", params.administracion, Rotulo.CD, "administración"),
        (Rotulo.UTI, "UTIL", params.utilidad, Rotulo.SUB, "utilidad"),
    )
    for r, nombre, global_, base_r, texto in casos:
        celda_g = apu.rotulos.get(r)
        if celda_g is None or nombre not in params.celdas:
            continue
        fila = _partir(celda_g.ref)[1]
        celda_f = Celda(apu.hoja, f"{col_pct}{fila}")
        f_g = ctx.an.formula(celda_g)
        f_f = ctx.an.formula(celda_f)
        param = params.celdas.get(nombre)
        if _usa_nombre(f_g, nombre, param):
            continue
        usa_f = bool(f_g) and re.search(
            rf"(?<![A-Z$]){col_pct}\$?{fila}(?!\d)", _sin_textos(f_g or "").replace("$", "")
        )
        if usa_f and _usa_nombre(f_f, nombre, param):
            continue
        local: Decimal | None
        if usa_f:
            local = _num(ctx.an.valor(celda_f))
            donde = celda_f
        else:
            m = re.search(r"\*\s*(\d*\.?\d+)\s*$", f_g or "")
            local = Decimal(m.group(1)) if m else _num(ctx.an.valor(celda_f))
            donde = celda_g if m else celda_f
        if local is None or local == global_:
            continue
        base = apu.guardados.get(base_r)
        impacto = _centavos((global_ - local) * base * p.cantidad) if base is not None else None
        out.append(
            Hallazgo(
                regla="L6",
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"A confirmar: la {texto} de {apu.hoja} (partida {p.numero}) está escrita a "
                    f"mano en {donde} = {_fu(local)}, en lugar de leer el parámetro global "
                    f"{nombre} ({_fu(global_)}). "
                    + (
                        f"Con el parámetro global la partida cambiaría en {_fmt(impacto)} USD sin "
                        "IVA (informativo). "
                        if impacto is not None
                        else ""
                    )
                    + "Puede ser intencional: la devolución conserva el valor escrito."
                ),
                impacto=impacto,
                origen_ids=tuple(dict.fromkeys((str(donde), str(celda_g)))),
                valor_observado=local,
                valor_esperado=global_,
            )
        )
    return out


def _l6_rendimiento(ctx: _Contexto, apu: ApuLeido, p: PartidaLeida) -> list[Hallazgo]:
    rend = apu.guardados.get(Rotulo.REND)
    celda_rend = apu.rotulos.get(Rotulo.REND)
    celda_mat = apu.rotulos.get(Rotulo.MAT)
    filas_mo_eq = [_partir(ln.celda_codigo.ref)[1] for ln in apu.lineas if ln.tipo.value != "MT"]
    if rend is None or celda_rend is None or not filas_mo_eq:
        return []
    desde = min(filas_mo_eq)
    hasta = _partir(celda_mat.ref)[1] if celda_mat is not None else 10**6
    distintos: dict[Decimal, list[str]] = defaultdict(list)
    for k in ctx.formulas_de.get(apu.hoja, ()):
        if not desde <= _partir(k.split("!", 1)[1])[1] < hasta:
            continue
        for m in _RX_DIVISOR_LITERAL.finditer(_sin_textos(ctx.libro.formulas[k])):
            distintos[Decimal(m.group(1))].append(k)
    out: list[Hallazgo] = []
    for literal in sorted(distintos):
        celdas = list(dict.fromkeys(distintos[literal]))
        if literal == rend:
            sev, intro = Severidad.INFO, "Rendimiento escrito dentro de fórmulas, igual al del APU"
            efecto = "Hoy da lo mismo, pero si cambia el rendimiento esas celdas no lo siguen."
        else:
            sev, intro = (
                Severidad.ADVERTENCIA,
                "A confirmar: rendimiento escrito dentro de fórmulas",
            )
            efecto = (
                f"Esas celdas dividen entre {_fu(literal)} y no entre el rendimiento del APU "
                f"({celda_rend} = {_fu(rend)}): el costo por unidad de equipos o consumo no sigue "
                "al rendimiento."
            )
        out.append(
            Hallazgo(
                regla="L6",
                severidad=sev,
                descripcion=(
                    f"{intro} en {apu.hoja} (partida {p.numero}): "
                    f"{', '.join(c.split('!', 1)[1] for c in celdas)} usan «/{_fu(literal)}». "
                    + efecto
                ),
                origen_ids=(*celdas, str(celda_rend)),
                valor_observado=literal,
                valor_esperado=rend,
            )
        )
    return out


def _l6(ctx: _Contexto) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    for apu in ctx.libro.apus:
        p = ctx.partida_de_apu.get(apu.hoja)
        if p is None:
            continue
        out.extend(_l6_porcentajes(ctx, apu, p))
        out.extend(_l6_rendimiento(ctx, apu, p))
    return out


# --- L7 Dato dentro de fórmula --------------------------------------------------------------------


def _l7(ctx: _Contexto) -> list[Hallazgo]:
    hoja = ctx.an.hoja(ctx.perfil.hoja("MEDICIONES"))
    if hoja is None:
        return []
    secciones: dict[str, list[str]] = {}
    for k in ctx.formulas_de.get(hoja, ()):
        f = _sin_textos(ctx.libro.formulas[k])
        if not (_RX_ARIT_LITERALES.search(f) or _RX_FACTOR_DECIMAL.search(f)):
            continue
        fila = _partir(k.split("!", 1)[1])[1]
        seccion = next(
            (
                t
                for x in range(fila, 0, -1)
                if _RX_SECCION.match(t := ctx.etiqueta(hoja, x, hasta_col=1))
            ),
            hoja,
        )
        secciones.setdefault(seccion, []).append(k)
    out: list[Hallazgo] = []
    for seccion, celdas in secciones.items():
        ejemplos = "; ".join(
            f"{c.split('!', 1)[1]} {ctx.libro.formulas[c]}" for c in celdas[:4]
        ) + ("; …" if len(celdas) > 4 else "")
        out.append(
            Hallazgo(
                regla="L7",
                severidad=Severidad.INFO,
                descripcion=(
                    f"{hoja}, sección «{seccion[:60]}»: {len(celdas)} fórmula(s) con medidas o "
                    f"factores escritos dentro ({ejemplos}). Efecto: esos datos no tienen celda "
                    "propia ni fuente, y no se pueden revisar ni rastrear."
                ),
                origen_ids=tuple(celdas),
            )
        )
    return out


# --- L8 Número de partida duplicado ---------------------------------------------------------------


def _l8(ctx: _Contexto) -> list[Hallazgo]:
    por_numero: dict[int, list[PartidaLeida]] = defaultdict(list)
    for p in ctx.libro.partidas:
        por_numero[p.numero].append(p)
    duplicados = {n: ps for n, ps in por_numero.items() if len(ps) > 1}
    if not duplicados:
        return []
    col_num = ctx.perfil.columnas_presupuesto["numero"]
    rx_pres = re.compile(
        rf"(?:'{re.escape(ctx.h_pres)}'|{re.escape(ctx.h_pres)})!\$?{col_num}\$?\d", re.I
    )
    con_match: set[str] = set()
    con_suma: set[str] = set()
    for k, f in ctx.libro.formulas.items():
        hoja = k.split("!", 1)[0]
        if hoja == ctx.h_pres or not rx_pres.search(f):
            continue
        fu = f.upper()
        if "MATCH(" in fu or "VLOOKUP(" in fu or "LOOKUP(" in fu:
            con_match.add(hoja)
        if "SUMIF" in fu:
            con_suma.add(hoja)
    orden = ctx.libro.hojas.index
    efectos: list[str] = []
    if con_match:
        efectos.append(
            f"{', '.join(sorted(con_match, key=orden))} buscan la partida por número (MATCH) y "
            "toman siempre la primera fila"
        )
    if con_suma:
        efectos.append(
            f"{', '.join(sorted(con_suma, key=orden))} suman por número (SUMIF) y mezclan las "
            "filas repetidas"
        )
    efecto = (
        "; ".join(efectos) + "."
        if efectos
        else "Ninguna hoja derivada busca por número en este libro, pero el número repetido "
        "confunde la lectura del presupuesto y de cualquier hoja que se agregue."
    )
    out: list[Hallazgo] = []
    for n in sorted(duplicados):
        ps = duplicados[n]
        filas = ", ".join(
            f"fila {p.fila} («{p.descripcion[:40]}», cantidad {_fu(p.cantidad)})" for p in ps
        )
        out.append(
            Hallazgo(
                regla="L8",
                severidad=Severidad.ADVERTENCIA,
                descripcion=f"El número de partida {n} se repite en {ctx.h_pres}: {filas}. "
                + efecto,
                origen_ids=tuple(f"{ctx.h_pres}!{col_num}{p.fila}" for p in ps),
            )
        )
    return out


# --- L9 Cuadre interno ----------------------------------------------------------------------------


def _l9_presupuesto(ctx: _Contexto) -> list[Hallazgo]:
    letra = dict(zip(_ORDEN_DESGLOSE, ctx.perfil.columnas_desglose, strict=False))
    col_ver = ctx.perfil.columnas_presupuesto["verificacion"]
    reglas = (
        ((Rotulo.MAT, Rotulo.MO, Rotulo.EQ, Rotulo.TR), Rotulo.CD),
        ((Rotulo.CD, Rotulo.ADM), Rotulo.SUB),
        ((Rotulo.SUB, Rotulo.UTI), Rotulo.PU),
    )
    out: list[Hallazgo] = []
    for p in ctx.libro.partidas:
        g = p.guardados
        cuadro_pu = True
        for sumandos, total in reglas:
            lt = letra[total]
            if lt not in g or not any(letra[s] in g for s in sumandos):
                continue
            suma = sum((g.get(letra[s], _CERO) for s in sumandos), _CERO)
            dif = suma - g[lt]
            if abs(dif) <= _TOL_CUADRE:
                continue
            if total is Rotulo.PU:
                cuadro_pu = False
            cols = "+".join(letra[s] for s in sumandos)
            impacto = _centavos(dif * p.cantidad)
            out.append(
                Hallazgo(
                    regla="L9",
                    severidad=Severidad.ERROR,
                    descripcion=(
                        f"Desglose de la partida {p.numero} (fila {p.fila} de {ctx.h_pres}): "
                        f"{cols} = {_fu(suma)} USD/u, pero {lt}{p.fila} "
                        f"({_NOMBRE_ROTULO[total]}) = {_fu(g[lt])}; diferencia {_fu(dif)} USD/u. "
                        f"Efecto: con la cantidad {_fu(p.cantidad)}, {_fmt(impacto)} USD que el "
                        "desglose muestra y el total no cobra (o al revés)."
                    ),
                    impacto=impacto,
                    origen_ids=tuple(f"{ctx.h_pres}!{letra[s]}{p.fila}" for s in sumandos)
                    + (f"{ctx.h_pres}!{lt}{p.fila}",),
                    valor_observado=g[lt],
                    valor_esperado=suma,
                )
            )
        celda_r = Celda(ctx.h_pres, f"{col_ver}{p.fila}")
        r = _num(ctx.an.valor(celda_r))
        if cuadro_pu and r is not None and abs(r) >= _TOL_CENTAVO:
            out.append(
                Hallazgo(
                    regla="L9",
                    severidad=Severidad.ERROR,
                    descripcion=(
                        f"La verificación {celda_r} de la partida {p.numero} vale {_fu(r)} "
                        "(debería ser 0)."
                    ),
                    impacto=_centavos(r * p.cantidad),
                    origen_ids=(str(celda_r),),
                    valor_observado=r,
                    valor_esperado=_CERO,
                )
            )
    return out


def _celdas_con_formula(ctx: _Contexto, hoja: str) -> Iterator[tuple[str, int, Decimal]]:
    for k in ctx.formulas_de.get(hoja, ()):
        v = _num(ctx.libro.valores.get(k))
        if v is not None:
            yield k, _partir(k.split("!", 1)[1])[1], v


#: Fila de PROCURA que compara el Costo Directo; las otras "Dif." son por componente.
_PROCURA_DIF_CD = "Dif. vs Costo Directo"


def _l9_dif(
    ctx: _Contexto,
    logica: str,
    prefijos: tuple[str, ...],
    que: str,
    prefijo_total: str | None = None,
) -> list[Hallazgo]:
    """Filas de verificación ("Dif.", "Verificación") que deberían valer 0.

    `prefijo_total` marca una fila que es la suma de las demás (en PROCURA, "Dif. vs Costo
    Directo" = materiales + mano de obra + equipos + transporte). Si alguna de las otras ya dio
    hallazgo, la del total repetiría la misma diferencia (doble conteo) y no se emite; si solo la
    del total difiere, sí se emite, porque es lo único que delata el descuadre.
    """
    hoja = ctx.an.hoja(ctx.perfil.hoja(logica))
    if hoja is None:
        return []
    out: list[Hallazgo] = []
    del_total: list[Hallazgo] = []
    for k, fila, v in _celdas_con_formula(ctx, hoja):
        etiqueta = ctx.etiqueta(hoja, fila)
        if not any(normalizar(etiqueta).startswith(normalizar(x)) for x in prefijos):
            continue
        if abs(v) < _TOL_CENTAVO:
            continue
        es_total = prefijo_total is not None and normalizar(etiqueta).startswith(
            normalizar(prefijo_total)
        )
        (del_total if es_total else out).append(
            Hallazgo(
                regla="L9",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{k} «{etiqueta[:70]}» vale {_fmt(v)} USD (debería ser 0). Efecto: {que}"
                ),
                impacto=_centavos(v),
                origen_ids=(k,),
                valor_observado=v,
                valor_esperado=_CERO,
            )
        )
    if del_total and not out:
        return del_total
    return out


def _l9_resumen(ctx: _Contexto) -> list[Hallazgo]:
    hoja = ctx.an.hoja(ctx.perfil.hoja("RESUMEN"))
    nombre_sub = ctx.perfil.nombres_totales[0]
    celda_sub = ctx.an.nombre_a_celda(nombre_sub)
    sub = ctx.libro.totales.get(nombre_sub)
    if hoja is None or sub is None:
        return []
    out: list[Hallazgo] = []
    for k, fila, v in _celdas_con_formula(ctx, hoja):
        f = ctx.libro.formulas[k]
        m = re.fullmatch(
            r"=\s*SUM\(\s*\$?([A-Z]{1,3})\$?(\d+)\s*:\s*\$?([A-Z]{1,3})\$?(\d+)\s*\)", f
        )
        etiqueta = normalizar(ctx.etiqueta(hoja, fila))
        es_composicion = es_costo = False
        if m is not None and m.group(1) == m.group(3):
            # Hasta el tope de filas del lector: más allá la hoja está vacía (guardia).
            fs = [
                ctx.libro.formulas.get(f"{hoja}!{m.group(1)}{x}", "").upper()
                for x in range(int(m.group(2)), min(int(m.group(4)), MAX_FILAS_HOJA) + 1)
            ]
            es_composicion = sum("SUMPRODUCT(" in x for x in fs) >= 2
            # El costo de la obra suma montos que leen PRESUPUESTO, no pesos en %.
            es_costo = etiqueta.startswith("costo de la obra") and any(
                normalizar(ctx.h_pres) in normalizar(x) for x in fs
            )
        if not (es_composicion or es_costo):
            continue
        dif = v - sub
        if abs(dif) < _TOL_CENTAVO:
            continue
        que = "el total de la composición del costo" if es_composicion else "el costo de la obra"
        out.append(
            Hallazgo(
                regla="L9",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{k} ({que}) suma {_fmt(v)} USD, pero el subtotal sin IVA del presupuesto "
                    f"({nombre_sub}"
                    + (f", {celda_sub}" if celda_sub else "")
                    + f") es {_fmt(sub)} USD: la hoja no cuadra por {_fmt(dif)} USD. Efecto: algún "
                    "componente que el desglose muestra no está en el total (o al revés)."
                ),
                impacto=_centavos(dif),
                origen_ids=(k,) + ((str(celda_sub),) if celda_sub else ()),
                valor_observado=v,
                valor_esperado=sub,
            )
        )
    return out


def _l9(ctx: _Contexto) -> list[Hallazgo]:
    return (
        _l9_presupuesto(ctx)
        + _l9_resumen(ctx)
        + _l9_dif(
            ctx,
            "PROCURA",
            ("Dif.",),
            "la lista de compras no corresponde al presupuesto (se compraría de más o de menos).",
            prefijo_total=_PROCURA_DIF_CD,
        )
        + _l9_dif(
            ctx,
            "PLAN DE PAGOS",
            ("Verificación",),
            "el plan de pagos no suma el total del presupuesto.",
        )
    )


# --- Entrada pública ------------------------------------------------------------------------------


def reglas_del_libro(libro: LibroLeido, perfil: Perfil | None = None) -> list[Hallazgo]:
    """Aplica L1-L9 al libro y devuelve los hallazgos en orden de regla; dentro de una regla, cada
    revisión va completa y en orden de celda (L1 de `reglas.py` y después la del BUSCARV).

    `perfil` es la plantilla con que se leyó el libro (por defecto `libro.perfil`). Las reglas no
    modifican el libro ni lanzan por una rareza: lo que no se puede juzgar se omite (ver los
    límites declarados en la cabecera del módulo).
    """
    ctx = _Contexto(libro, perfil or cargar_perfil(libro.perfil))
    reglas = (_l1, calc.l1_buscarv, _l2, _l3, calc.l4, _l5, calc.l5_celdas_con_error)
    hallazgos: list[Hallazgo] = []
    for regla in (*reglas, _l6, _l7, _l8, _l9):
        hallazgos.extend(regla(ctx))
    return hallazgos
