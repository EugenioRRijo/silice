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
  que recibe `fcas = FCAS − 1` (`fcas_nucleo`) y `bono_alimentacion = 0` (la plantilla no paga
  bono aparte);
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

Las reglas de la plantilla sobre cada línea (factor literal, destajo, divisor literal de equipos)
viven en un solo lugar, `adapters.hoja_empresa.plantilla`, que también usa el escritor: el P.U. que
calcula el motor y el que dan las fórmulas del libro devuelto salen de la misma regla.

Los precios salen siempre de INSUMOS (`libro.insumo(codigo).precio`), no del valor que muestra la
línea del APU: si el libro no estaba recalculado, el APU puede mostrar un precio viejo (L3), y
Silice devuelve el que corresponde a la hoja de precios. La administración y la utilidad son **las
del APU** (F-D7: un literal escrito a mano, como la utilidad del 2 %, se conserva y L6 lo marca "a
confirmar").

Lo que no admite dos lecturas se corrige por construcción (F-D7): el motor siempre suma los cuatro
componentes al costo directo (H1: un CD que omite los equipos da F1). Lo que puede ser intencional
se conserva: si la fórmula de equipos divide entre un literal distinto del rendimiento (`/12`),
Silice **también** divide entre ese literal (escala la cantidad de cada equipo por rendimiento ÷
literal, porque el motor divide entre el rendimiento) y L6 lo informa "a confirmar".

Lo que el mapeo no puede tomar tal cual del libro (un código que no está en INSUMOS, una unidad
vacía, una fórmula de línea que no es un producto) no hace fallar el proceso: se usa el respaldo
declarado y se deja un `Aviso` que `fusion.proceso` lleva a TRAZABILIDAD. Lo que impide recalcular
(un FCAS menor que 1) lanza `LibroNoInterpretable`, con un mensaje para el usuario.

El perfil de plantilla es el del libro (`cargar_perfil(libro.perfil)`), salvo que quien llama pase
otro.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from adapters.hoja_empresa.modelo import (
    ApuCalculado,
    ApuLeido,
    LibroLeido,
    LibroNoInterpretable,
    LineaApu,
    PartidaLeida,
    TipoInsumo,
)
from adapters.hoja_empresa.perfil import Perfil, cargar_perfil, normalizar
from adapters.hoja_empresa.plantilla import (
    Aviso,
    divisor_equipos_con_aviso,
    factor_linea_con_aviso,
    filas_base_mo,
    modalidad_con_aviso,
    texto_decimal,
    unidad_de_linea,
)
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
from core.costing.motor import calcular_apu
from core.verification.texto import formatear_decimal

__all__ = [
    "DESCRIPCION_HERRAMIENTAS",
    "DESCRIPCION_TRANSPORTE",
    "UNIDAD_POR_DEFECTO",
    "Aviso",
    "CalculoPartida",
    "calcular_partida",
    "codigos_de_partida",
    "fcas_nucleo",
    "hoja_presupuesto",
    "moneda_del_libro",
    "parametros_nucleo",
    "perfil_del_libro",
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

_CERO = Decimal(0)
_UNO = Decimal(1)


@dataclass(frozen=True, slots=True)
class CalculoPartida:
    """Una partida de PRESUPUESTO con su APU recalculado por el motor del núcleo.

    `codigo` es el código ÚNICO con el que la partida entra al `Presupuesto` del núcleo (el de la
    composición y el del `ItemComputo` son el mismo, ver `codigos_de_partida`). `avisos` es lo que
    el mapeo tuvo que suplir o conservar para este APU (códigos sin INSUMOS, unidades vacías,
    factores escritos en fórmulas, destajo, divisor de equipos).
    """

    partida: PartidaLeida
    apu: ApuLeido
    codigo: str
    composicion: ComposicionAPU
    resultado: ResultadoAPU
    calculado: ApuCalculado
    avisos: tuple[Aviso, ...] = ()


# --- Datos del libro ----------------------------------------------------------------------------


def perfil_del_libro(libro: LibroLeido, perfil: Perfil | None = None) -> Perfil:
    """El perfil dado o, si no hay, el perfil con que se leyó el libro (`libro.perfil`)."""
    return perfil if perfil is not None else cargar_perfil(libro.perfil)


def hoja_presupuesto(libro: LibroLeido, perfil: Perfil | None = None) -> str:
    """El nombre real de la hoja PRESUPUESTO en el libro (puede diferir en mayúsculas o espacios
    del que dice el perfil): los `origen_id` deben apuntar a la hoja que existe."""
    esperado = perfil_del_libro(libro, perfil).hoja("PRESUPUESTO")
    n = normalizar(esperado)
    return next((h for h in libro.hojas if normalizar(h) == n), esperado)


def moneda_del_libro(libro: LibroLeido) -> str:
    """'Bs' si la PORTADA habla de bolívares; si no, 'USD' (todos los libros recibidos están en
    dólares y la plantilla rotula sus montos "USD/u"). Son las dos de `core.catalog.moneda.MONEDAS`.
    """
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


def fcas_nucleo(libro: LibroLeido) -> Decimal:
    """`FCAS − 1` (F-D1): lo que recibe el núcleo, que suma `1 + fcas`. Un libro sin FCAS (0) pasa
    0: no se inventa un factor.

    Lanza `LibroNoInterpretable` si el FCAS está entre 0 y 1 (o es negativo): la plantilla lo usa
    como factor que multiplica la base, y un factor así no es de la plantilla.
    """
    fcas = libro.parametros.fcas
    if fcas == 0:
        return _CERO
    if fcas < 1:
        celda = libro.parametros.celdas.get("FCAS")
        donde = f" ({celda})" if celda is not None else ""
        raise LibroNoInterpretable(
            f"El FCAS del libro{donde} vale {formatear_decimal(fcas, 4)}. La plantilla lo usa "
            "como un factor que multiplica los salarios (1,9 significa +90 %), así que debe ser 1 "
            "o mayor. Corrija el FCAS en INSUMOS y vuelva a subir el libro: Silice no adivina el "
            "factor."
        )
    return fcas - 1


def parametros_nucleo(apu: ApuLeido, libro: LibroLeido) -> ParametrosCosto:
    """Los `ParametrosCosto` con los que el motor reproduce el P.U. de la plantilla (F-D1, F-D7)."""
    return ParametrosCosto(
        fcas=fcas_nucleo(libro),
        bono_alimentacion=_CERO,
        administracion=apu.administracion,
        utilidad=apu.utilidad,
    )


# --- Composición --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Partes:
    """Lo que se deriva del APU una sola vez: la composición y el desglose de la plantilla."""

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
            f"({texto_decimal(linea.precio)})",
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


def _precio_transporte(libro: LibroLeido) -> Decimal:
    """USD por m³ de escombro: flete ÷ camión + vertedero (un camión de capacidad 0 no lleva
    flete)."""
    p = libro.parametros
    flete = p.flete / p.capacidad_camion if p.capacidad_camion else _CERO
    return flete + p.tarifa_vertedero


def _partes(apu: ApuLeido, libro: LibroLeido, perfil: Perfil) -> _Partes:
    avisos: list[Aviso] = []
    materiales: list[LineaMaterial] = []
    mano_obra: list[LineaManoObra] = []
    equipos: list[LineaEquipo] = []
    base_mo_dia = _CERO
    destajo = _CERO
    equipos_dia = _CERO
    filas_base = filas_base_mo(apu, libro)
    # El motor divide los equipos entre el rendimiento del APU; si la plantilla los divide entre
    # otro número escrito en la fórmula, la cantidad se escala por rendimiento ÷ ese número.
    escala_eq = _UNO
    divisor, aviso_divisor = divisor_equipos_con_aviso(apu, libro)
    if divisor is not None:
        escala_eq = apu.rendimiento / divisor
    if aviso_divisor is not None:
        avisos.append(aviso_divisor)
    for linea in apu.lineas:
        precio = _precio(linea, libro, avisos)
        factor, aviso_factor = factor_linea_con_aviso(linea, libro, perfil)
        if aviso_factor is not None:
            avisos.append(aviso_factor)
        cantidad = linea.cantidad * factor
        unidad_libro = unidad_de_linea(linea, libro)
        if linea.tipo is TipoInsumo.MATERIAL:
            unidad = _unidad((unidad_libro,), str(linea.celda_codigo), avisos)
            materiales.append(LineaMaterial(linea.descripcion, unidad, cantidad, precio))
        elif linea.tipo is TipoInsumo.MANO_OBRA:
            modalidad, aviso_mo = modalidad_con_aviso(linea, libro, filas_base)
            if aviso_mo is not None:
                avisos.append(aviso_mo)
            mano_obra.append(LineaManoObra(linea.descripcion, cantidad, precio, modalidad))
            if modalidad is ModalidadManoObra.JORNAL:
                base_mo_dia += cantidad * precio
            else:
                destajo += cantidad * precio
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
            base_mo_dia * (1 + fcas_nucleo(libro)) + destajo * apu.rendimiento
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


def _componentes(apu: ApuLeido, partes: _Partes, resultado: ResultadoAPU) -> ApuCalculado:
    """Los componentes del APU según Silice, con el desglose de la plantilla (rótulos MAT, MO, EQ,
    TR…).

    El motor del núcleo devuelve el transporte dentro de los materiales y las herramientas dentro
    de los equipos; aquí se separa el transporte (la plantilla lo muestra en su propia fila) y las
    herramientas se informan aparte sin sacarlas de los equipos (el rótulo EQ de la plantilla las
    incluye). La administración es `CD × adm` y la utilidad lo que falta hasta el P.U., de modo que
    `CD + adm + utilidad = P.U.` exactamente.
    """
    return ApuCalculado(
        hoja=apu.hoja,
        materiales=resultado.materiales - partes.transporte,
        mano_obra=resultado.mano_obra,
        equipos=resultado.equipos,
        transporte=partes.transporte,
        costo_directo=resultado.costo_directo,
        administracion=resultado.costo_directo * apu.administracion,
        subtotal=resultado.con_administracion,
        utilidad=resultado.precio_unitario - resultado.con_administracion,
        precio_unitario=resultado.precio_unitario,
        base_mo_dia=partes.base_mo_dia,
        equipos_dia=partes.equipos_dia,
        herramientas=partes.herramientas,
    )


def calcular_partida(
    partida: PartidaLeida,
    apu: ApuLeido,
    libro: LibroLeido,
    codigo: str,
    perfil: Perfil | None = None,
) -> CalculoPartida:
    """Recalcula con el motor del núcleo el APU de una partida (F-D1): composición, parámetros,
    `calcular_apu`, desglose de la plantilla y avisos, derivando el APU una sola vez.

    `codigo` es el código único de la partida en el núcleo (ver `codigos_de_partida`). Lanza
    `LibroNoInterpretable` si el FCAS del libro no es un factor de la plantilla; un APU que el
    núcleo no acepta (rendimiento 0) lanza el `ValueError` del contrato, que `fusion.proceso`
    traduce con el nombre de la hoja.
    """
    partes = _partes(apu, libro, perfil_del_libro(libro, perfil))
    composicion = ComposicionAPU(
        codigo_partida=codigo,
        descripcion=apu.titulo or apu.hoja,
        unidad=partes.unidad,
        rendimiento=apu.rendimiento,
        materiales=partes.materiales,
        equipos=partes.equipos,
        mano_obra=partes.mano_obra,
    )
    resultado = calcular_apu(composicion, parametros_nucleo(apu, libro))
    return CalculoPartida(
        partida=partida,
        apu=apu,
        codigo=codigo,
        composicion=composicion,
        resultado=resultado,
        calculado=_componentes(apu, partes, resultado),
        avisos=partes.avisos,
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
    perfil = perfil_del_libro(libro, perfil)
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
