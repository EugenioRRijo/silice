"""Del libro de la empresa a los contratos del núcleo, sin tocar el núcleo (spec 1.5, F-D1).

La plantilla de la empresa calcula un APU así (análisis de causas raíz, "Cómo funcionan los
libros", y las fórmulas de los cinco libros recibidos)::

    línea           = cantidad × precio [× factor escrito en la fórmula: ×1,1 de desperdicio, ÷8]
    MO              = Σ jornal (cuadrilla × jornal/día) × FCAS ÷ rendimiento + Σ destajo
    equipos         = Σ cantidad × costo/día ÷ rendimiento + herramientas × MO
    transporte      = escombro × (flete ÷ camión + vertedero)
    CD              = materiales + MO + equipos + transporte
    P.U.            = CD × (1 + administración) × (1 + utilidad)

El motor del núcleo (`core.costing.motor.calcular_apu`) reproduce exactamente esa cuenta con los
contratos que ya existen, sin una línea nueva en `core/`:

- el FCAS de la empresa es un **factor** (1,9 multiplica la base); el núcleo suma `1 + fcas`, así
  que recibe `fcas = FCAS − 1` y `bono_alimentacion = 0` (la plantilla no paga bono aparte);
- una línea de mano de obra cuya unidad no es "día" (un instalador a 60 USD/m²) es **destajo**: la
  plantilla la deja fuera del subtotal de salarios base y la suma completa al costo de mano de obra,
  sin FCAS ni rendimiento; es exactamente `ModalidadManoObra.DESTAJO` del núcleo;
- un factor literal en la fórmula del subtotal de una línea (`=E10*F10*1.1`, `=E11*F11/8`) es parte
  del cálculo de la empresa y se conserva (F-D7: puede ser intencional, L6/L7 lo informan): entra
  multiplicando la cantidad;
- el transporte y la disposición de escombros es una `LineaMaterial` más: cantidad = m³ de escombro
  por unidad, precio = flete ÷ camión + vertedero (los materiales no se dividen entre el
  rendimiento, igual que el transporte de la plantilla);
- las herramientas menores son una `LineaEquipo` de cantidad 1 y depreciación 1 cuyo precio es
  `herramientas × MO por unidad × rendimiento`: el motor la divide entre el rendimiento y queda
  `herramientas × MO por unidad`, que es lo que suma la plantilla (MO con el destajo incluido).

Los precios salen siempre de INSUMOS (`libro.insumo(codigo).precio`), no del valor que muestra la
línea del APU: si el libro no estaba recalculado, el APU puede mostrar un precio viejo (L3), y
Silice devuelve el que corresponde a la hoja de precios. La administración y la utilidad son **las
del APU** (F-D7: un literal escrito a mano, como la utilidad del 2 %, se conserva y L6 lo marca "a
confirmar").

Lo que no admite dos lecturas se corrige por construcción (F-D7): el motor siempre suma los cuatro
componentes al costo directo (H1: un CD que omite los equipos da F1) y divide los equipos entre el
rendimiento del APU (un `/12` literal en la fórmula de equipos no se reproduce; L6 lo informa).

Lo que el mapeo no puede tomar tal cual del libro (un código que no está en INSUMOS, una unidad
vacía, una fórmula de línea que no es un producto) no hace fallar el proceso: se usa el respaldo
declarado y se deja un `Aviso` que `fusion.proceso` lleva a TRAZABILIDAD.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache

from adapters.hoja_empresa.modelo import (
    ApuCalculado,
    ApuLeido,
    LibroLeido,
    LineaApu,
    PartidaLeida,
    Rotulo,
    TipoInsumo,
)
from adapters.hoja_empresa.perfil import Perfil, cargar_perfil, normalizar
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ModalidadManoObra,
    ParametrosCosto,
    ResultadoAPU,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.unidades import normalizar_unidad

__all__ = [
    "DESCRIPCION_HERRAMIENTAS",
    "DESCRIPCION_TRANSPORTE",
    "UNIDAD_POR_DEFECTO",
    "Aviso",
    "CalculoPartida",
    "avisos_de_composicion",
    "codigos_de_partida",
    "componentes",
    "composicion_nucleo",
    "hoja_presupuesto",
    "moneda_del_libro",
    "parametros_nucleo",
    "presupuesto_nucleo",
]

DESCRIPCION_TRANSPORTE = "Transporte y disposición de escombros"
DESCRIPCION_HERRAMIENTAS = "Herramientas menores"
#: Unidad de respaldo cuando ni INSUMOS ni la línea del APU ni la partida dicen cuál es. Se anota.
UNIDAD_POR_DEFECTO = "und"
#: Códigos de partida que la empresa usa para decir "sin código" (`S/C`): no identifican nada.
_SIN_CODIGO = frozenset({"", "s/c", "sc", "s/c.", "sin codigo", "sin código"})
#: La PORTADA dice la moneda en texto libre ("Dólares de los Estados Unidos de América (USD)").
_RE_BOLIVARES = re.compile(r"(?<![a-z])(bs|ves)(?![a-z])|bol[ií]var")
#: `N($E10)` -> `E10`; `IF($B10="",0,expr)` -> `expr` (la forma de la plantilla más nueva).
_RE_N = re.compile(r"N\(([A-Z]+\d+)\)")
_RE_SI_VACIO = re.compile(r'IF\([A-Z]+\d+="",0,')

_CERO = Decimal(0)
_UNO = Decimal(1)
_DIA = "dia"


@dataclass(frozen=True, slots=True)
class Aviso:
    """Algo que el mapeo tuvo que suplir o conservar. `origen` es la celda `HOJA!CELDA`."""

    origen: str
    mensaje: str


@dataclass(frozen=True, slots=True)
class CalculoPartida:
    """Una partida de PRESUPUESTO con su APU recalculado por el motor del núcleo.

    `codigo` es el código ÚNICO con el que la partida entra al `Presupuesto` del núcleo (el de la
    composición y el del `ItemComputo` son el mismo, ver `codigos_de_partida`).
    """

    partida: PartidaLeida
    apu: ApuLeido
    codigo: str
    composicion: ComposicionAPU
    resultado: ResultadoAPU
    calculado: ApuCalculado


# --- Datos del libro ----------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _perfil_por_omision() -> Perfil:
    return cargar_perfil()


def _perfil(perfil: Perfil | None) -> Perfil:
    return perfil if perfil is not None else _perfil_por_omision()


def hoja_presupuesto(libro: LibroLeido, perfil: Perfil | None = None) -> str:
    """El nombre real de la hoja PRESUPUESTO en el libro (puede diferir en mayúsculas o espacios
    del que dice el perfil): los `origen_id` deben apuntar a la hoja que existe."""
    esperado = _perfil(perfil).hoja("PRESUPUESTO")
    n = normalizar(esperado)
    return next((h for h in libro.hojas if normalizar(h) == n), esperado)


def moneda_del_libro(libro: LibroLeido) -> str:
    """'Bs' si la PORTADA habla de bolívares; si no, 'USD' (todos los libros recibidos están en
    dólares y la plantilla rotula sus montos "USD/u")."""
    if _RE_BOLIVARES.search(normalizar(libro.portada.moneda)):
        return "Bs"
    return "USD"


def _sin_codigo(codigo: str) -> bool:
    return normalizar(codigo) in _SIN_CODIGO


def codigos_de_partida(libro: LibroLeido) -> dict[int, str]:
    """Fila de PRESUPUESTO -> código único de la partida en el núcleo.

    El núcleo identifica cada partida por `codigo_partida`, pero la empresa repite códigos (la misma
    partida COVENIN en varios ambientes) y números (H4). La regla:

    - el código de la partida; si está vacío o es `S/C`, `P<número>`;
    - si ese código lo comparte más de una partida, `<código>#<fila>`, que es único porque la fila
      lo es.
    """
    base = {
        p.fila: (f"P{p.numero}" if _sin_codigo(p.codigo) else p.codigo.strip())
        for p in libro.partidas
    }
    veces = Counter(base.values())
    return {fila: (f"{c}#{fila}" if veces[c] > 1 else c) for fila, c in base.items()}


# --- Parámetros ---------------------------------------------------------------------------------


def _fcas_nucleo(libro: LibroLeido) -> Decimal:
    """`FCAS − 1` (F-D1). Un libro sin FCAS (0) pasa 0: no se inventa un factor."""
    fcas = libro.parametros.fcas
    if fcas == 0:
        return _CERO
    if fcas < 1:
        raise ValueError(
            f"el FCAS del libro es {fcas}: la plantilla lo usa como factor que multiplica la base "
            "(1,9 = +90 %); un factor menor que 1 no es de la plantilla y no se adivina"
        )
    return fcas - 1


def parametros_nucleo(apu: ApuLeido, libro: LibroLeido) -> ParametrosCosto:
    """Los `ParametrosCosto` con los que el motor reproduce el P.U. de la plantilla (F-D1, F-D7)."""
    return ParametrosCosto(
        fcas=_fcas_nucleo(libro),
        bono_alimentacion=_CERO,
        administracion=apu.administracion,
        utilidad=apu.utilidad,
    )


# --- Factor escrito en la fórmula de una línea --------------------------------------------------


class _FormulaNoReconocidaError(ValueError):
    """La fórmula del subtotal de la línea no es cantidad × precio × literales."""


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


def _factor_linea(
    linea: LineaApu, libro: LibroLeido, perfil: Perfil, avisos: list[Aviso]
) -> Decimal:
    """El factor con que la plantilla multiplica cantidad × precio en el subtotal de la línea.

    El subtotal de cada línea vive en la columna de los subtotales del APU (la del rótulo MAT),
    en la fila de la línea. Sin fórmula reconocible (texto, literal escrito a mano, otra
    referencia), el factor es 1 y queda el aviso: Silice calcula cantidad × precio.
    """
    fila = int(re.sub(r"\D", "", linea.celda_cantidad.ref))
    col_sub = perfil.rotulos_apu[Rotulo.MAT].columna
    col_cant = perfil.columnas_linea["cantidad"]
    col_precio = perfil.columnas_linea["precio"]
    celda = f"{linea.celda_cantidad.hoja}!{col_sub}{fila}"
    formula = libro.formulas.get(celda)
    if formula is None:
        if libro.valores.get(celda) is not None:
            avisos.append(
                Aviso(celda, "subtotal de línea escrito a mano: Silice calcula cantidad × precio")
            )
        return _UNO
    try:
        factor = _factor_formula(formula, fila, col_cant, col_precio)
    except _FormulaNoReconocidaError:
        avisos.append(
            Aviso(
                celda,
                f"fórmula de línea no reconocida ({formula}): Silice calcula cantidad × precio",
            )
        )
        return _UNO
    if factor != _UNO:
        avisos.append(
            Aviso(
                celda,
                f"la fórmula {formula} multiplica cantidad × precio por {_texto(factor)}: se "
                "conserva (F-D7)",
            )
        )
    return factor


# --- Composición --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Partes:
    """Lo que se deriva del APU una sola vez y comparten `composicion_nucleo` y `componentes`."""

    materiales: tuple[LineaMaterial, ...]
    mano_obra: tuple[LineaManoObra, ...]
    equipos: tuple[LineaEquipo, ...]
    unidad: str
    base_mo_dia: Decimal  # Σ jornal: cuadrilla × jornal/día (sin destajo)
    destajo: Decimal  # USD/u
    equipos_dia: Decimal
    precio_transporte: Decimal  # USD/m³ de escombro
    transporte: Decimal  # USD/u
    herramientas: Decimal  # USD/u
    avisos: tuple[Aviso, ...]


def _precio(linea: LineaApu, libro: LibroLeido, avisos: list[Aviso]) -> Decimal:
    insumo = libro.insumo(linea.codigo)
    if insumo is not None:
        return insumo.precio
    avisos.append(
        Aviso(
            str(linea.celda_codigo),
            f"{linea.codigo} no está en INSUMOS: se usa el precio que muestra el APU "
            f"({_texto(linea.precio)})",
        )
    )
    return linea.precio


def _unidad(candidatas: Iterable[str], origen: str, avisos: list[Aviso]) -> str:
    """La primera unidad no vacía; si no hay ninguna, `UNIDAD_POR_DEFECTO` y un aviso.

    `normalizar_unidad` solo rechaza la unidad vacía (una desconocida la deja como está), así que
    basta con no pasarle una vacía.
    """
    for unidad in candidatas:
        if unidad and unidad.strip():
            return unidad.strip()
    avisos.append(Aviso(origen, f"sin unidad en el libro: se usa «{UNIDAD_POR_DEFECTO}»"))
    return UNIDAD_POR_DEFECTO


def _divisor_equipos(apu: ApuLeido, libro: LibroLeido) -> tuple[Decimal, str] | None:
    """El número literal entre el que una fórmula del APU divide el subtotal de equipos por día
    (`=G27/12+G28`), con la celda de esa fórmula; `None` si lo divide entre el rendimiento (una
    referencia) o si no hay subtotal de equipos.

    F-D7: ese `/12` (L6) puede ser un rendimiento de equipos distinto del de la cuadrilla, escrito a
    propósito, así que Silice lo conserva y L6 lo deja "a confirmar".
    """
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
            return Decimal(m.group(1)), clave_celda
    return None


def _filas_base_mo(apu: ApuLeido, libro: LibroLeido) -> frozenset[int] | None:
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


def _modalidad(
    linea: LineaApu, unidad: str, filas_base: frozenset[int] | None, avisos: list[Aviso]
) -> ModalidadManoObra:
    """JORNAL o DESTAJO según lo que hace la plantilla con la línea.

    La fórmula manda: una línea que entra en el subtotal de salarios base se multiplica por FCAS y
    se divide entre el rendimiento (JORNAL), aunque su unidad sea m² (así está en algunos APU, y
    F-D7 no decide la intención). Una línea fuera de esa suma cuya unidad no es "día" es el destajo
    que la plantilla suma completo al costo de mano de obra. Una línea en días fuera de la suma es
    un rango mal ajustado: Silice la cuenta como JORNAL (se corrige, y F1 lo cuantifica). Sin
    fórmula reconocible, decide la unidad.
    """
    en_dias = not unidad.strip() or normalizar_unidad(unidad) == _DIA
    if filas_base is None:
        return ModalidadManoObra.JORNAL if en_dias else ModalidadManoObra.DESTAJO
    fila = int(re.sub(r"\D", "", linea.celda_cantidad.ref))
    if fila in filas_base:
        return ModalidadManoObra.JORNAL
    if en_dias:
        avisos.append(
            Aviso(
                str(linea.celda_codigo),
                f"{linea.codigo} se paga por día pero el subtotal de salarios base no la suma: "
                "Silice la cuenta como jornal",
            )
        )
        return ModalidadManoObra.JORNAL
    return ModalidadManoObra.DESTAJO


def _precio_transporte(libro: LibroLeido) -> Decimal:
    """USD por m³ de escombro: flete ÷ camión + vertedero (un camión de capacidad 0 no lleva
    flete)."""
    p = libro.parametros
    flete = p.flete / p.capacidad_camion if p.capacidad_camion else _CERO
    return flete + p.tarifa_vertedero


def _partes(apu: ApuLeido, libro: LibroLeido, perfil: Perfil | None = None) -> _Partes:
    perfil = _perfil(perfil)
    avisos: list[Aviso] = []
    materiales: list[LineaMaterial] = []
    mano_obra: list[LineaManoObra] = []
    equipos: list[LineaEquipo] = []
    base_mo_dia = _CERO
    destajo = _CERO
    equipos_dia = _CERO
    filas_base = _filas_base_mo(apu, libro)
    # El motor divide los equipos entre el rendimiento del APU; si la plantilla los divide entre
    # otro número escrito en la fórmula, la cantidad se escala por rendimiento ÷ ese número.
    escala_eq = _UNO
    divisor = _divisor_equipos(apu, libro)
    if divisor is not None and divisor[0] != apu.rendimiento:
        escala_eq = apu.rendimiento / divisor[0]
        avisos.append(
            Aviso(
                divisor[1],
                f"los equipos se dividen entre {_texto(divisor[0])} y no entre el rendimiento "
                f"({_texto(apu.rendimiento)}): se conserva (F-D7)",
            )
        )
    for linea in apu.lineas:
        precio = _precio(linea, libro, avisos)
        cantidad = linea.cantidad * _factor_linea(linea, libro, perfil, avisos)
        insumo = libro.insumo(linea.codigo)
        unidad_libro = insumo.unidad if insumo and insumo.unidad.strip() else linea.unidad
        if linea.tipo is TipoInsumo.MATERIAL:
            unidad = _unidad((unidad_libro,), str(linea.celda_codigo), avisos)
            materiales.append(LineaMaterial(linea.descripcion, unidad, cantidad, precio))
        elif linea.tipo is TipoInsumo.MANO_OBRA:
            modalidad = _modalidad(linea, unidad_libro, filas_base, avisos)
            mano_obra.append(LineaManoObra(linea.descripcion, cantidad, precio, modalidad))
            if modalidad is ModalidadManoObra.JORNAL:
                base_mo_dia += cantidad * precio
            else:
                destajo += cantidad * precio
                avisos.append(
                    Aviso(
                        str(linea.celda_codigo),
                        f"{linea.codigo} se paga por {unidad_libro} (no por día): destajo, entra "
                        "completo sin FCAS ni rendimiento",
                    )
                )
        else:
            equipos_dia += cantidad * precio
            equipos.append(LineaEquipo(linea.descripcion, cantidad * escala_eq, precio, _UNO))

    precio_transporte = _precio_transporte(libro)
    transporte = _CERO
    if apu.escombro > 0:
        materiales.append(
            LineaMaterial(DESCRIPCION_TRANSPORTE, "m3", apu.escombro, precio_transporte)
        )
        transporte = apu.escombro * precio_transporte

    herramientas = _CERO
    if apu.herramientas > 0:
        # herramientas × MO por unidad × rendimiento, con MO por unidad = base × FCAS ÷ rend +
        # destajo; se escribe sin dividir y volver a multiplicar por el rendimiento, para no
        # introducir redondeos.
        precio_herr = apu.herramientas * (
            base_mo_dia * (1 + _fcas_nucleo(libro)) + destajo * apu.rendimiento
        )
        equipos.append(LineaEquipo(DESCRIPCION_HERRAMIENTAS, _UNO, precio_herr, _UNO))
        herramientas = precio_herr / apu.rendimiento

    partida = next((p for p in libro.partidas if p.hoja_apu == apu.hoja), None)
    unidad = _unidad((apu.unidad, partida.unidad if partida else ""), f"{apu.hoja}!unidad", avisos)
    return _Partes(
        materiales=tuple(materiales),
        mano_obra=tuple(mano_obra),
        equipos=tuple(equipos),
        unidad=unidad,
        base_mo_dia=base_mo_dia,
        destajo=destajo,
        equipos_dia=equipos_dia,
        precio_transporte=precio_transporte,
        transporte=transporte,
        herramientas=herramientas,
        avisos=tuple(avisos),
    )


def _codigo_por_omision(apu: ApuLeido, libro: LibroLeido) -> str:
    codigos = codigos_de_partida(libro)
    fila = next((p.fila for p in libro.partidas if p.hoja_apu == apu.hoja), None)
    if fila is not None:
        return codigos[fila]
    return apu.codigo_partida.strip() or apu.hoja


def composicion_nucleo(
    apu: ApuLeido, libro: LibroLeido, codigo_partida: str | None = None
) -> ComposicionAPU:
    """La `ComposicionAPU` del núcleo para un APU del libro (F-D1).

    `codigo_partida` es el código único de la partida a la que se une (ver `codigos_de_partida`);
    por omisión, el de la partida cuyo `hoja_apu` es este APU.
    """
    partes = _partes(apu, libro)
    return ComposicionAPU(
        codigo_partida=codigo_partida or _codigo_por_omision(apu, libro),
        descripcion=apu.titulo or apu.hoja,
        unidad=partes.unidad,
        rendimiento=apu.rendimiento,
        materiales=partes.materiales,
        equipos=partes.equipos,
        mano_obra=partes.mano_obra,
    )


def avisos_de_composicion(apu: ApuLeido, libro: LibroLeido) -> tuple[Aviso, ...]:
    """Lo que `composicion_nucleo` tuvo que suplir o conservar para este APU (códigos sin INSUMOS,
    unidades vacías, factores escritos en fórmulas, destajo)."""
    return _partes(apu, libro).avisos


def componentes(apu: ApuLeido, libro: LibroLeido, resultado: ResultadoAPU) -> ApuCalculado:
    """Los componentes del APU según Silice, con el desglose de la plantilla (rótulos MAT, MO, EQ,
    TR…).

    El motor del núcleo devuelve el transporte dentro de los materiales y las herramientas dentro
    de los equipos; aquí se separa el transporte (la plantilla lo muestra en su propia fila) y las
    herramientas se informan aparte sin sacarlas de los equipos (el rótulo EQ de la plantilla las
    incluye). La administración es `CD × adm` y la utilidad lo que falta hasta el P.U., de modo que
    `CD + adm + utilidad = P.U.` exactamente.
    """
    partes = _partes(apu, libro)
    administracion = resultado.costo_directo * apu.administracion
    return ApuCalculado(
        hoja=apu.hoja,
        materiales=resultado.materiales - partes.transporte,
        mano_obra=resultado.mano_obra,
        equipos=resultado.equipos,
        transporte=partes.transporte,
        costo_directo=resultado.costo_directo,
        administracion=administracion,
        subtotal=resultado.con_administracion,
        utilidad=resultado.precio_unitario - resultado.con_administracion,
        precio_unitario=resultado.precio_unitario,
        base_mo_dia=partes.base_mo_dia,
        equipos_dia=partes.equipos_dia,
        herramientas=partes.herramientas,
    )


# --- Presupuesto --------------------------------------------------------------------------------


def presupuesto_nucleo(
    libro: LibroLeido,
    calculos: Iterable[CalculoPartida],
    fecha: date,
    perfil: Perfil | None = None,
) -> Presupuesto:
    """El `Presupuesto` del núcleo: una `PartidaPresupuestada` por partida con APU.

    La cantidad es el valor guardado de la columna de cantidad de PRESUPUESTO y su `origen_id` es
    esa celda (`OrigenTipo.TABULAR`: trazable por la celda, sin regla). Sin curva: el libro tiene
    CRONOGRAMA, pero Silice no la reconstruye en la 1.5 y no la inventa (R2 y R7 lo declaran "no
    aplicable"). `fecha` es la del libro (F-D8).
    """
    perfil = _perfil(perfil)
    hoja = hoja_presupuesto(libro, perfil)
    col_cantidad = perfil.columnas_presupuesto["cantidad"]
    partidas = []
    for calculo in calculos:
        p = calculo.partida
        partidas.append(
            PartidaPresupuestada(
                item=ItemComputo(
                    codigo_partida=calculo.codigo,
                    descripcion=p.descripcion,
                    unidad=p.unidad or calculo.composicion.unidad,
                    cantidad=p.cantidad,
                    origen_id=f"{hoja}!{col_cantidad}{p.fila}",
                    origen_tipo=OrigenTipo.TABULAR,
                    dominio=Dominio.CIVIL,
                ),
                apu=calculo.composicion,
                resultado=calculo.resultado,
            )
        )
    return Presupuesto(
        codigo=libro.nombre,
        fecha=fecha,
        moneda=moneda_del_libro(libro),
        partidas=tuple(partidas),
    )


def _texto(valor: Decimal) -> str:
    return format(valor, "f")
