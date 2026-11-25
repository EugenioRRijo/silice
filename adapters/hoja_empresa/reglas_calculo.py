"""Reglas del libro sobre la cadena de cálculo de los montos: L4 y dos complementos de L1 y L5.

Vienen de la medición una falla por vez del 2026-11-24 (plan no circular, «Segunda medición»):
de 12 fallas inyectadas de a una en el libro de desarrollo, Sílice dejaba escapar 7, y tres de
los escapes eran huecos reales de reglas. Se cierran aquí, antes del congelamiento:

- `l1_buscarv`: un BUSCARV de un APU que busca en la lista de precios el código de **otra fila**.
  El APU queda coherente consigo mismo (cada cifra sale de su fórmula), así que solo la fila lo
  delata. Una fila sin código propio no se juzga: puede citar el de otra a propósito.
- `l4`: el costo directo que deja fuera un componente. Si el componente vale algo es ERROR con
  impacto (como siempre); si hoy vale 0 es ADVERTENCIA sin impacto: el monto de hoy no cambia,
  pero el día en que el componente tenga valor no entrará al precio.
- `l5_celdas_con_error`: una celda con fórmula de un APU, del PRESUPUESTO o del RESUMEN que da un
  error de cálculo (#VALUE!, #N/A…), por ejemplo un SUMPRODUCT con rangos de distinto tamaño.
  El #REF! queda fuera: lo informa L5 por la fórmula que cita la celda borrada, y una celda que
  lo arrastra es la misma causa.

Las tres usan el contexto común de `reglas_contexto.py`; `reglas_del_libro` (en `reglas.py`) las
llama en el orden de su regla. Sobre los 5 libros reales del equipo (2026-11-24) no agregan ningún
hallazgo.
"""

from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal

from adapters.hoja_empresa.modelo import ApuLeido, Celda, Rotulo
from adapters.hoja_empresa.reglas_contexto import (
    _CERO,
    _NOMBRE_ROTULO,
    _TOL_CUADRE,
    _centavos,
    _Contexto,
    _fmt,
    _fu,
    _iguales,
    _lectura_precios,
    _n0,
    _num,
    _partir,
    _valor,
)
from core.contracts.verificacion import Hallazgo, Severidad

__all__ = ["ERRORES_DE_CALCULO", "l1_buscarv", "l4", "l5_celdas_con_error"]

#: Componentes del costo directo (L4).
_COMPONENTES = (Rotulo.MAT, Rotulo.MO, Rotulo.EQ, Rotulo.TR)
_UNO = Decimal(1)
#: `VLOOKUP(B10,PRECIOS,k` dentro de la fórmula (con o sin IF/IFERROR alrededor).
_BUSCARV = re.compile(r"VLOOKUP\(\s*\$?([A-Z]{1,3})\$?(\d+)\s*,\s*PRECIOS\s*,\s*(\d+)", re.I)
#: Errores de cálculo que Excel puede guardar en una celda. #REF! va aparte: lo informa L5 por la
#: fórmula que cita la celda borrada (un #REF! que llega por INDIRECT no se ve; límite declarado).
ERRORES_DE_CALCULO = frozenset(
    {
        "#N/A", "#VALUE!", "#DIV/0!", "#NUM!", "#NAME?", "#NULL!", "#SPILL!", "#CALC!",
        "#FIELD!", "#CONNECT!", "#BLOCKED!", "#UNKNOWN!", "#GETTING_DATA",
    }
)  # fmt: skip


# --- L1: BUSCARV con el código de otra fila -----------------------------------------------------


def _de_lista(ctx: _Contexto, columna: str, fila: int, k: str, hoja: str) -> object:
    """Lo que la lista de precios da al código de `columna` y `fila` en su columna `k`."""
    celda = _lectura_precios(ctx, f"=VLOOKUP({columna}{fila},PRECIOS,{k},0)", hoja)
    return ctx.an.valor(celda) if celda is not None else None


def _hay(v: object) -> bool:
    return v is not None and str(v).strip() != ""


def _mismo_codigo(a: object, b: object) -> bool:
    """Como BUSCARV de Excel: sin distinguir mayúsculas ni espacios a los lados."""
    return str(a).strip().casefold() == str(b).strip().casefold()


def l1_buscarv(ctx: _Contexto) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    for k in ctx.orden:
        hoja, ref = k.split("!", 1)
        if hoja not in ctx.hojas_apu:
            continue
        fila = _partir(ref)[1]
        for m in _BUSCARV.finditer(ctx.libro.formulas[k]):
            columna, fila_citada = m.group(1).upper(), int(m.group(2))
            propia, citada = Celda(hoja, f"{columna}{fila}"), Celda(hoja, f"{columna}{fila_citada}")
            codigo, codigo_citado = ctx.an.valor(propia), ctx.an.valor(citada)
            if fila_citada == fila or not _hay(codigo):
                continue
            if _hay(codigo_citado) and _mismo_codigo(codigo, codigo_citado):
                continue
            # Se compara lo que trae cada búsqueda, no la cifra guardada: la fórmula puede hacer
            # cuentas alrededor del BUSCARV.
            trae = _de_lista(ctx, columna, fila_citada, m.group(3), hoja)
            esperado = _de_lista(ctx, columna, fila, m.group(3), hoja)
            mueve = _num(esperado) is not None and not _iguales(trae, esperado)
            efecto = (
                f"la búsqueda trae {_valor(trae)} en vez de {_valor(esperado)}, la cifra de su "
                "propio insumo, y el APU la arrastra al precio de la partida."
                if mueve
                else "el renglón muestra el dato de otro insumo."
            )
            out.append(
                Hallazgo(
                    regla="L1",
                    severidad=Severidad.ERROR if mueve else Severidad.ADVERTENCIA,
                    descripcion=(
                        f"{k} busca en la lista de precios el código de {citada} "
                        f"({_valor(codigo_citado)}), pero está en la fila {fila}, cuyo código es "
                        f"{propia} ({_valor(codigo)}). Efecto: {efecto}"
                    ),
                    origen_ids=(k, str(citada), str(propia)),
                    valor_observado=_num(trae),
                    valor_esperado=_num(esperado),
                )
            )
            break
    return out


# --- L4 Componente fuera del total --------------------------------------------------------------


def l4(ctx: _Contexto) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    for apu in ctx.libro.apus:
        p = ctx.partida_de_apu.get(apu.hoja)
        celda_cd = apu.rotulos.get(Rotulo.CD)
        cd = apu.guardados.get(Rotulo.CD)
        if p is None or celda_cd is None or cd is None:
            continue
        f_cd = ctx.an.formula(celda_cd) or ""
        citadas = ctx.an.celdas_referidas(f_cd, apu.hoja) if f_cd else set()
        suma = _CERO
        fuera: list[tuple[Rotulo, Celda, Decimal]] = []
        en_cero: list[tuple[Rotulo, Celda]] = []
        for r in _COMPONENTES:
            celda, equivalentes = ctx.equivalentes(apu, r)
            if celda is None:
                continue
            leido = ctx.an.valor(celda)
            v = _n0(leido)
            suma += v
            if not f_cd or citadas & equivalentes:
                continue
            if v != 0:
                fuera.append((r, celda, v))
            elif not isinstance(leido, str):  # un texto o un error no «vale 0» (L5 lo informa)
                en_cero.append((r, celda))
        if fuera or abs(suma - cd) > _TOL_CUADRE:
            out.append(_l4_error(apu, p.numero, p.cantidad, (celda_cd, f_cd), cd, suma, fuera))
        if en_cero:
            out.append(_l4_en_cero(apu, p.numero, (celda_cd, f_cd), en_cero))
    return out


def _l4_error(
    apu: ApuLeido,
    numero: int,
    cantidad: Decimal,
    cd_y_formula: tuple[Celda, str],
    cd: Decimal,
    suma: Decimal,
    fuera: list[tuple[Rotulo, Celda, Decimal]],
) -> Hallazgo:
    celda_cd, f_cd = cd_y_formula
    factor = (_UNO + apu.administracion) * (_UNO + apu.utilidad)
    impacto = _centavos((suma - cd) * factor * cantidad)
    if fuera:
        que = ", ".join(f"{_NOMBRE_ROTULO[r]} ({c}, {_fu(v)} USD/u)" for r, c, v in fuera)
        detalle = f"la fórmula {celda_cd} {f_cd} deja fuera {que}"
    else:
        detalle = f"{celda_cd} no es la suma de los componentes"
    return Hallazgo(
        regla="L4",
        severidad=Severidad.ERROR,
        descripcion=(
            f"Costo directo de {apu.hoja} (partida {numero}): {detalle}. El CD guardado "
            f"es {_fu(cd)} USD/u y la suma de materiales, mano de obra, equipos y "
            f"transporte es {_fu(suma)} USD/u. Efecto: con administración "
            f"({_fu(apu.administracion)}) y utilidad ({_fu(apu.utilidad)}) del APU y la "
            f"cantidad {_fu(cantidad)}, la partida queda corta en {_fmt(impacto)} USD "
            "sin IVA."
        ),
        impacto=impacto,
        origen_ids=(str(celda_cd), *(str(c) for _, c, _ in fuera)),
        valor_observado=cd,
        valor_esperado=suma,
    )


def _l4_en_cero(
    apu: ApuLeido,
    numero: int,
    cd_y_formula: tuple[Celda, str],
    en_cero: list[tuple[Rotulo, Celda]],
) -> Hallazgo:
    celda_cd, f_cd = cd_y_formula
    que = ", ".join(f"{_NOMBRE_ROTULO[r]} ({c})" for r, c in en_cero)
    return Hallazgo(
        regla="L4",
        severidad=Severidad.ADVERTENCIA,
        descripcion=(
            f"Costo directo de {apu.hoja} (partida {numero}): la fórmula {celda_cd} {f_cd} deja "
            f"fuera {que}, que hoy vale 0. Efecto: el monto de hoy no cambia, pero el día en que "
            "ese componente tenga valor no entrará al costo directo ni al precio de la partida."
        ),
        origen_ids=(str(celda_cd), *(str(c) for _, c in en_cero)),
    )


# --- L5: celda de la cadena de montos con error -------------------------------------------------


def l5_celdas_con_error(ctx: _Contexto) -> list[Hallazgo]:
    # Como L4 y L6, solo los APU unidos a una partida: una plantilla no entra al presupuesto.
    resumen = ctx.an.hoja(ctx.perfil.hoja("RESUMEN"))
    cadena = set(ctx.partida_de_apu) | {ctx.h_pres} | ({resumen} if resumen else set())
    por_hoja: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for k in ctx.orden:
        hoja = k.split("!", 1)[0]
        v = ctx.libro.valores.get(k)
        if hoja in cadena and isinstance(v, str) and v.strip().upper() in ERRORES_DE_CALCULO:
            por_hoja[hoja].append((k, v.strip().upper()))
    out: list[Hallazgo] = []
    for hoja in sorted(por_hoja, key=ctx.libro.hojas.index):
        celdas = por_hoja[hoja]
        lista = ", ".join(f"{k.split('!', 1)[1]} ({v})" for k, v in celdas)
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{len(celdas)} celda(s) de {hoja} dan error al calcular: {lista}. Efecto: "
                    "el monto que depende de ellas no se puede calcular; Excel muestra el error "
                    "en lugar de la cifra."
                ),
                origen_ids=tuple(k for k, _ in celdas),
            )
        )
    return out
