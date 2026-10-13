"""Orquestación de la 1.5: libro de la empresa -> motor del núcleo -> auditoría -> alertas ->
devolución calcada (spec 1.5, F-D2, F-D9).

Sigue el patrón de la reauditoría (`auditoria/reauditoria.py`): procesa un documento ajeno **en
memoria**, no guarda nada, y **no cree los precios escritos**: cada P.U. se recalcula con el motor
del núcleo desde la composición del APU y los precios de INSUMOS (`fusion.mapeo`, F-D1). Lo que el
libro guarda (P de PRESUPUESTO, totales con nombre) solo se usa para compararlo con Silice (F1, L3,
L11) y para lo que Silice no puede recalcular: una partida sin APU entra a los totales con su monto
guardado, L2 la informa y TRAZABILIDAD dice de qué celda salió el monto (F1 es solo "P.U.
recalculado", errata 5 del spec).

Los servicios de la instalación (tasas del BCV, precios propios) llegan inyectados en un
`ContextoPrecios` (`fusion.servicios.servicios_desde_sesion` lo arma desde una sesión de la base;
se re-exporta aquí); sin contexto, las alertas en Bs dicen "no contrastable".

PDF (errata 6). Si junto con el libro llega un PDF, Silice decide qué es: si trae el bloque de
totales del libro impreso ("Costo de la obra", "TOTAL PRESUPUESTO (USD)"), es el entregado y se
coteja con el libro (L11); si no, y tiene tablas de cómputos o de presupuesto, es un PDF simple y
se revisa consigo mismo (L10). Un PDF simple sin libro se revisa con `auditar_pdf_simple`.

Errores en la frontera. `procesar_libro` y `auditar_pdf_simple` dejan pasar `ArchivoRechazado` (la
guardia o el lector rechazan el archivo) y `LibroNoInterpretable` (se leyó, pero sus datos no
permiten recalcularlo); cualquier otro error de datos se traduce a una de las dos, con un mensaje
para el usuario y la causa encadenada. La interfaz y la API muestran el mensaje tal cual.

Fechas (F-D8). La del libro es la de la PORTADA ("Julio 2026" -> 31/07/2026) salvo que quien llama
dé otra. La de devolución la pasa explícita la interfaz o la API; `date.today()` es SOLO el valor
por omisión de `procesar_libro` y nunca se lee dentro de las reglas ni de las alertas.
"""

from __future__ import annotations

import calendar
import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from types import MappingProxyType

from adapters.hoja_empresa.escritor import escribir_devolucion
from adapters.hoja_empresa.guardia import ArchivoRechazado
from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.modelo import (
    ApuCalculado,
    ApuLeido,
    DatosDevolucion,
    FilaAlerta,
    FilaHallazgo,
    FilaTraza,
    LibroLeido,
    LibroNoInterpretable,
    PartidaLeida,
    Rotulo,
)
from adapters.hoja_empresa.pdf import (
    PdfSimple,
    TotalesImpresos,
    cotejar_con_libro,
    leer_pdf_simple,
    leer_totales_impresos,
    reglas_pdf_simple,
)
from adapters.hoja_empresa.perfil import Perfil, cargar_perfil, normalizar
from adapters.hoja_empresa.reglas import REGLAS_LIBRO, reglas_del_libro
from core.contracts.apu import ResultadoAPU
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, Severidad
from core.verification.informe import InformeAuditoria, auditar
from core.verification.precios import CODIGO_R11, CODIGO_R12, PrecioFueraDeRango, PrecioVencido
from core.verification.texto import formatear_decimal
from fusion.alertas import ContextoPrecios, alertas_de_precios
from fusion.mapeo import (
    CalculoPartida,
    calcular_partida,
    codigos_de_partida,
    fcas_nucleo,
    hoja_presupuesto,
    presupuesto_nucleo,
)
from fusion.servicios import servicios_desde_sesion
from operacion.version import version

__all__ = [
    "ACCION_A_CONFIRMAR",
    "ACCION_CORREGIDO",
    "ACCION_INFORMADO",
    "REGLA_F1",
    "REGLA_L10",
    "REGLA_L11",
    "REGLA_R11",
    "REGLA_R12",
    "ResultadoFusion",
    "ResultadoPdf",
    "auditar_pdf_simple",
    "devolver",
    "fecha_del_libro",
    "procesar_libro",
    "servicios_desde_sesion",
]

REGLA_F1 = ("F1", "P.U. recalculado")
REGLA_L10 = ("L10", "Documento sin modelo (PDF simple)")
REGLA_L11 = ("L11", "Libro ↔ PDF entregado")
REGLA_R11 = (CODIGO_R11, PrecioFueraDeRango.nombre)
REGLA_R12 = (CODIGO_R12, PrecioVencido.nombre)

#: Por qué R11 y R12 no se evalúan en la 1.5 (errata 4 del spec): AUDITORÍA lo dice tal cual.
MOTIVO_R11 = (
    "no se evalúa en la 1.5: no hay un mapeo de los códigos MT/MO/EQ de la empresa a MaPreX, así "
    "que ningún precio del libro tiene referencia con qué compararse"
)
MOTIVO_R12 = (
    "no se evalúa en la 1.5: los libros no traen la fecha de cada precio (solo la de la PORTADA), "
    "así que no se puede saber si un precio está vencido"
)
_SIN_PDF_L10 = "no se recibió un PDF simple (sin modelo) para revisar"
_SIN_PDF_L11 = "no se recibió el PDF entregado, así que no hay totales impresos con qué cotejar"
_PDF_ES_IMPRESO = "el PDF recibido es el impreso del libro: se cotejó con L11"
_PDF_ES_SIMPLE = (
    "el PDF recibido no trae el bloque de totales del libro impreso: es un PDF simple y se revisó "
    "con L10"
)

ACCION_CORREGIDO = "corregido"
ACCION_A_CONFIRMAR = "a confirmar"
ACCION_INFORMADO = "informado"

#: F-D7: lo que no admite dos lecturas lo arregla la devolución por construcción (los valores
#: guardados son los de Silice, las referencias son nombres definidos, los `#REF!` y vínculos se
#: quitan). Un valor escrito a mano que puede ser intencional (L6) se conserva "a confirmar". Lo
#: demás (L7, L8, los PDF y las reglas del núcleo) se informa.
_CORREGIDOS = frozenset({"F1", "L1", "L2", "L3", "L4", "L5", "L9"})
_A_CONFIRMAR = frozenset({"L6"})

#: Diferencia mínima (en la moneda del libro) para que F1 sea hallazgo: un céntimo (spec §3).
UMBRAL_F1 = Decimal("0.01")

PRODUCIDO_POR = "Silice"
#: Nombre por omisión de la otra versión del libro (la guardia exige la extensión `.xlsx`).
_NOMBRE_OTRA_VERSION = "otra_version.xlsx"
#: Errores de datos que, dentro del proceso, significan "el libro no se puede interpretar".
_ERRORES_DE_DATOS = (ValueError, ArithmeticError, LookupError)

_MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
_RE_MES_ANIO = re.compile(r"\b(" + "|".join(_MESES) + r")\s+(?:de(?:l)?\s+)?(\d{4})\b")
_RE_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_RE_DIA_MES_ANIO = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")
_RE_MES_NUM_ANIO = re.compile(r"\b(\d{1,2})[/.-](\d{4})\b")


# --- Resultado ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoFusion:
    """Todo lo que produce `procesar_libro`, inmutable y en memoria (F-D9).

    `calculos` y `resultados_nucleo` van por nombre de hoja APU; `precios_unitarios` por fila de
    PRESUPUESTO (P.U. de Silice); `totales_silice` con las claves 'SUBSINIVA', 'IVATOT' y
    'TOTALGEN'. `origen` son los bytes del libro recibido: `devolver` calca sobre ellos.
    `fecha_libro` es `None` si la PORTADA no trae una fecha legible y nadie dio otra.
    `pdf_totales` es el PDF entregado (L11) y `pdf_simple` el PDF simple (L10): a lo sumo uno de
    los dos. Las reglas evaluadas están en `informe.reglas_evaluadas`; `reglas_no_evaluadas` son
    `(código, nombre, motivo)`.
    """

    libro: LibroLeido
    origen: bytes = field(repr=False)
    pdf_totales: TotalesImpresos | None
    calculos: Mapping[str, ApuCalculado]
    resultados_nucleo: Mapping[str, ResultadoAPU]
    precios_unitarios: Mapping[int, Decimal]
    presupuesto: Presupuesto
    informe: InformeAuditoria
    alertas: tuple[FilaAlerta, ...]
    trazabilidad: tuple[FilaTraza, ...]
    hallazgos_tabla: tuple[FilaHallazgo, ...]
    totales_silice: Mapping[str, Decimal]
    fecha_libro: date | None
    fecha_devolucion: date
    metadatos: Mapping[str, str]
    reglas_no_evaluadas: tuple[tuple[str, str, str], ...] = ()
    pdf_simple: PdfSimple | None = None

    def __post_init__(self) -> None:
        for nombre in (
            "calculos",
            "resultados_nucleo",
            "precios_unitarios",
            "totales_silice",
            "metadatos",
        ):
            object.__setattr__(self, nombre, MappingProxyType(dict(getattr(self, nombre))))


@dataclass(frozen=True, slots=True)
class ResultadoPdf:
    """Lo que produce `auditar_pdf_simple`: el PDF leído, sus hallazgos L10, la tabla para mostrar
    (todos "informado": un PDF no se devuelve corregido) y el SHA-256 del archivo recibido."""

    pdf: PdfSimple
    hallazgos: tuple[Hallazgo, ...]
    hallazgos_tabla: tuple[FilaHallazgo, ...]
    sha256: str


# --- Fecha del libro ----------------------------------------------------------------------------


def _fin_de_mes(anio: int, mes: int) -> date | None:
    if not 1 <= mes <= 12:
        return None
    return date(anio, mes, calendar.monthrange(anio, mes)[1])


def _fecha(anio: int, mes: int, dia: int) -> date | None:
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def fecha_del_libro(libro: LibroLeido) -> date | None:
    """La fecha de la PORTADA (F-D8), o `None` si no se entiende.

    Un mes sin día ("Julio 2026", "julio de 2026", "07/2026") es el ÚLTIMO día de ese mes: el
    presupuesto vale para el mes y la tasa que lo representa es la del cierre. Una fecha completa
    (ISO `2026-07-15`, o `15/07/2026`, que es como se escribe en Venezuela: día/mes/año) es ese día.
    """
    texto = normalizar(libro.portada.fecha_texto)
    if not texto:
        return None
    if m := _RE_ISO.search(texto):
        return _fecha(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if m := _RE_DIA_MES_ANIO.search(texto):
        return _fecha(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    if m := _RE_MES_ANIO.search(texto):
        return _fin_de_mes(int(m.group(2)), _MESES[m.group(1)])
    if m := _RE_MES_NUM_ANIO.search(texto):
        return _fin_de_mes(int(m.group(2)), int(m.group(1)))
    return None


# --- F1 -----------------------------------------------------------------------------------------


def _num(valor: Decimal) -> str:
    return formatear_decimal(valor)


def _hallazgo_f1(calculo: CalculoPartida, hoja: str, col_pu: str) -> Hallazgo | None:
    """F1 (spec §3): el P.U. del motor del núcleo contra el P guardado en PRESUPUESTO.

    impacto = (P.U. Silice − P guardado) × cantidad: lo que el libro deja de cobrar (positivo) o
    cobra de más (negativo) en el total sin IVA. Un impacto menor que un céntimo es redondeo y no es
    hallazgo (por eso las filas con cantidad 0 nunca dan F1, aunque su P.U. difiera: no mueven el
    total).

    El impacto se informa en céntimos (ROUND_HALF_UP), igual que L4 y L9 en `reglas.py`, porque es
    un monto del total; el umbral se mide sobre el valor sin redondear. Los P.U. observado y
    esperado quedan tal cual (el del motor no se redondea).
    """
    p = calculo.partida
    guardado = p.guardados.get(col_pu)
    if guardado is None:
        return None
    silice = calculo.resultado.precio_unitario
    diferencia = silice - guardado
    bruto = diferencia * p.cantidad
    if abs(bruto) < UMBRAL_F1:
        return None
    impacto = bruto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    celda_pu = calculo.apu.rotulos.get(Rotulo.PU)
    return Hallazgo(
        regla=REGLA_F1[0],
        severidad=Severidad.ERROR,
        descripcion=(
            f"partida {p.numero} ({calculo.codigo}): PRESUPUESTO guarda un P.U. de "
            f"{_num(guardado)} y el motor de Silice lo recalcula en {_num(silice)} con el APU "
            f"{calculo.apu.hoja}; la diferencia por la cantidad ({_num(p.cantidad)}) mueve el "
            f"total sin IVA en {formatear_decimal(impacto, 2)}"
        ),
        impacto=impacto,
        origen_ids=(
            f"{hoja}!{col_pu}{p.fila}",
            str(celda_pu) if celda_pu is not None else f"{calculo.apu.hoja}!PU",
        ),
        valor_observado=guardado,
        valor_esperado=silice,
    )


@dataclass(frozen=True, slots=True)
class _SinRecalculo:
    """Una partida que Silice no puede recalcular: entra a los totales con su monto guardado."""

    partida: PartidaLeida
    monto: Decimal
    origen: str
    nota: str


def _sin_recalculo(partida: PartidaLeida, hoja: str, col_pu: str, col_monto: str) -> _SinRecalculo:
    """El monto guardado de una partida sin APU (L2 la informa) o con cantidad negativa (no entra
    al núcleo): el de la columna de monto o, si no lo hay, cantidad × P guardado; 0 si tampoco.
    La nota de TRAZABILIDAD dice por qué y de qué celda sale."""
    motivo = (
        "tiene cantidad negativa y no entra al núcleo"
        if partida.cantidad < 0 and partida.hoja_apu
        else "no tiene APU (L2)"
    )
    sigue = "Silice no puede recalcular su P.U. y suma a los totales"
    if (monto := partida.guardados.get(col_monto)) is not None:
        return _SinRecalculo(
            partida, monto, f"{hoja}!{col_monto}{partida.fila}", f"{motivo}: {sigue} este monto"
        )
    if (pu := partida.guardados.get(col_pu)) is not None:
        return _SinRecalculo(
            partida,
            partida.cantidad * pu,
            f"{hoja}!{col_pu}{partida.fila}",
            f"{motivo}: {sigue} cantidad × P.U. guardado (no hay monto guardado)",
        )
    return _SinRecalculo(
        partida,
        Decimal(0),
        f"{hoja}!{col_monto}{partida.fila}",
        f"{motivo}: no hay monto ni P.U. guardado, así que suma 0 a los totales",
    )


# --- Tabla de hallazgos y trazabilidad ----------------------------------------------------------


def _accion(hallazgo: Hallazgo, informados: frozenset[Hallazgo]) -> str:
    if hallazgo in informados:
        return ACCION_INFORMADO
    if hallazgo.regla in _CORREGIDOS:
        return ACCION_CORREGIDO
    if hallazgo.regla in _A_CONFIRMAR:
        return ACCION_A_CONFIRMAR
    return ACCION_INFORMADO


def _tabla(
    hallazgos: Sequence[Hallazgo], informados: frozenset[Hallazgo]
) -> tuple[FilaHallazgo, ...]:
    return tuple(
        FilaHallazgo(
            codigo=h.regla,
            severidad=h.severidad.name,
            descripcion=h.descripcion,
            celda=h.origen_ids[0] if h.origen_ids else "",
            impacto=h.impacto,
            accion=_accion(h, informados),
        )
        for h in hallazgos
    )


def _trazabilidad(
    libro: LibroLeido,
    perfil: Perfil,
    codigos: Mapping[int, str],
    calculos: Sequence[CalculoPartida],
    sin_recalculo: Sequence[_SinRecalculo],
    fecha_libro: date | None,
    origen_fecha: str,
    fecha_presupuesto: date,
    pdf: bytes | None,
    pdf_nombre: str,
) -> tuple[FilaTraza, ...]:
    """TRAZABILIDAD (F-D9, NORMAS §2.6): de dónde sale cada dato que Silice usó para recalcular."""
    filas = [
        FilaTraza("SHA-256 del libro recibido", libro.sha256, libro.nombre),
    ]
    if pdf is not None:
        filas.append(
            FilaTraza("SHA-256 del PDF entregado", hashlib.sha256(pdf).hexdigest(), pdf_nombre)
        )
    filas.append(
        FilaTraza(
            "Fecha del libro",
            fecha_libro.isoformat() if fecha_libro else "",
            origen_fecha,
            ""
            if fecha_libro
            else f"sin fecha legible: el presupuesto del núcleo se fecha {fecha_presupuesto} "
            "(fecha de devolución) y las alertas en Bs no son contrastables",
        )
    )
    p = libro.parametros
    for campo, nombre in perfil.nombres_parametros.items():
        celda = p.celdas.get(nombre)
        valor: Decimal = getattr(p, campo)
        nota = ""
        if campo == "fcas":
            nota = (
                f"factor de la plantilla; el núcleo recibe fcas = {_num(fcas_nucleo(libro))} y "
                "bono de alimentación 0 (F-D1)"
            )
        filas.append(
            FilaTraza(
                f"Parámetro {nombre}",
                _num(valor),
                str(celda) if celda is not None else "",
                nota if celda is not None else "el libro no define este nombre: vale 0",
            )
        )
    for insumo in libro.insumos:
        filas.append(
            FilaTraza(
                f"Precio {insumo.codigo} {insumo.descripcion}".strip(),
                _num(insumo.precio),
                str(insumo.celda),
                f"fuente: {insumo.fuente}" if insumo.fuente.strip() else "sin fuente",
            )
        )
    hoja = hoja_presupuesto(libro, perfil)
    col_cantidad = perfil.columnas_presupuesto["cantidad"]
    for partida in libro.partidas:
        filas.append(
            FilaTraza(
                f"Cantidad partida {partida.numero} ({codigos[partida.fila]})",
                _num(partida.cantidad),
                f"{hoja}!{col_cantidad}{partida.fila}",
                partida.unidad,
            )
        )
    for s in sin_recalculo:
        filas.append(
            FilaTraza(
                f"Monto guardado partida {s.partida.numero} ({codigos[s.partida.fila]})",
                formatear_decimal(s.monto, 2),
                s.origen,
                s.nota,
            )
        )
    vistos: set[str] = set()
    for calculo in calculos:
        if calculo.apu.hoja in vistos:
            continue
        vistos.add(calculo.apu.hoja)
        for aviso in calculo.avisos:
            filas.append(FilaTraza("Aviso del mapeo", "", aviso.origen, aviso.mensaje))
    return tuple(filas)


# --- PDF ----------------------------------------------------------------------------------------


def _pdf_ilegible(nombre: str, exc: Exception) -> ArchivoRechazado:
    detalle = f" ({exc})" if isinstance(exc, ValueError) and str(exc) else ""
    return ArchivoRechazado(
        f"No se pudo leer el PDF «{nombre}»{detalle}. Compruebe que es un PDF de texto (no una "
        "imagen escaneada), sin contraseña, y vuelva a subirlo."
    )


def _leer_pdf(datos: bytes, nombre: str) -> TotalesImpresos | PdfSimple:
    """El PDF que llegó con el libro: sus totales impresos si es el impreso del libro (L11), o el
    PDF simple si no trae ese bloque pero sí tablas (L10). Un PDF sin nada de eso se trata como
    impreso: L11 dirá que no encontró las cifras."""
    try:
        totales = leer_totales_impresos(datos, nombre)
        if totales.bloques or any(
            v is not None for v in (totales.subtotal, totales.iva, totales.total)
        ):
            return totales
        simple = leer_pdf_simple(datos, nombre)
    except ArchivoRechazado:
        raise
    except Exception as exc:  # pdfplumber/pdfminer lanzan sus propias excepciones
        raise _pdf_ilegible(nombre, exc) from exc
    return simple if simple.computos or simple.presupuesto else totales


def auditar_pdf_simple(datos: bytes, nombre: str) -> ResultadoPdf:
    """Revisa un PDF simple (sin libro) consigo mismo con L10 (spec §3, errata 6): lo lee con
    `leer_pdf_simple` y le aplica `reglas_pdf_simple`. No guarda nada.

    Lanza `ArchivoRechazado` si el archivo no se puede leer como PDF y `LibroNoInterpretable` si no
    tiene ninguna tabla de cómputos ni de presupuesto (no hay nada que revisar).
    """
    try:
        pdf = leer_pdf_simple(datos, nombre)
    except ArchivoRechazado:
        raise
    except Exception as exc:  # pdfplumber/pdfminer lanzan sus propias excepciones
        raise _pdf_ilegible(nombre, exc) from exc
    if not pdf.computos and not pdf.presupuesto:
        raise LibroNoInterpretable(
            f"El PDF «{nombre}» no tiene una tabla de cómputos ni de presupuesto (con columnas "
            "Items, Descripción, Unidad y Cantidad): no hay nada que revisar."
        )
    hallazgos = tuple(reglas_pdf_simple(pdf))
    return ResultadoPdf(
        pdf=pdf,
        hallazgos=hallazgos,
        hallazgos_tabla=_tabla(hallazgos, frozenset(hallazgos)),
        sha256=pdf.sha256,
    )


# --- Proceso ------------------------------------------------------------------------------------


def procesar_libro(
    datos: bytes,
    nombre: str,
    *,
    pdf: bytes | None = None,
    pdf_nombre: str = "",
    contexto: ContextoPrecios | None = None,
    fecha_libro: date | None = None,
    fecha_devolucion: date | None = None,
    otro: bytes | None = None,
    otro_nombre: str = _NOMBRE_OTRA_VERSION,
    perfil: str | None = None,
) -> ResultadoFusion:
    """Lee el libro, recalcula cada APU con el motor del núcleo, lo audita y arma las alertas.

    Pasos: `leer_libro` -> por cada partida unida a un APU, `calcular_partida` (composición,
    parámetros y `calcular_apu`, `fusion.mapeo`) -> F1 -> `auditar` el presupuesto del núcleo
    (R1-R7) -> L1-L9 (`reglas_del_libro`) -> L11 o L10 si hay PDF -> informe combinado -> totales
    de Silice -> alertas.

    `perfil` es el nombre del perfil de plantilla (`adapters/hoja_empresa/perfiles/<perfil>.json`);
    por omisión, el del lector. Todo lo demás usa el perfil con que se leyó el libro
    (`libro.perfil`). `fecha_devolucion` la pasa la interfaz (o la API) explícita; por omisión es
    hoy, y ese es el único lugar donde se lee el reloj. `otro` son los bytes de otra versión del
    mismo libro, para las alertas de cambio de precio.

    Lanza `ArchivoRechazado` si la guardia o el lector rechazan el libro, la otra versión o el PDF,
    y `LibroNoInterpretable` si los datos del libro no permiten recalcularlo. No deja escapar otro
    error de datos sin ese contexto.
    """
    if fecha_devolucion is None:
        fecha_devolucion = date.today()
    perfil_pedido = cargar_perfil(perfil) if perfil is not None else None
    libro = leer_libro(datos, nombre, perfil_pedido)
    try:
        return _procesar(
            libro,
            datos,
            pdf=pdf,
            pdf_nombre=pdf_nombre,
            contexto=contexto,
            fecha_libro=fecha_libro,
            fecha_devolucion=fecha_devolucion,
            otro=otro,
            otro_nombre=otro_nombre,
        )
    except (ArchivoRechazado, LibroNoInterpretable):
        raise
    except _ERRORES_DE_DATOS as exc:
        raise LibroNoInterpretable(
            f"Silice leyó el libro «{nombre}» pero no pudo recalcularlo: alguno de sus datos no "
            "tiene la forma de la plantilla. Revise los parámetros de INSUMOS y los APU, y vuelva "
            "a subirlo."
        ) from exc


def _calcular(
    partida: PartidaLeida, apu: ApuLeido, libro: LibroLeido, codigo: str, perfil: Perfil
) -> CalculoPartida:
    """`calcular_partida` con el nombre de la hoja en el mensaje si el núcleo no acepta el APU."""
    try:
        return calcular_partida(partida, apu, libro, codigo, perfil)
    except LibroNoInterpretable:
        raise
    except _ERRORES_DE_DATOS as exc:
        raise LibroNoInterpretable(
            f"El APU {apu.hoja} (partida {partida.numero}) no se puede recalcular: {exc}. "
            "Corríjalo en el libro (por ejemplo, un rendimiento 0) y vuelva a subirlo."
        ) from exc


def _procesar(
    libro: LibroLeido,
    datos: bytes,
    *,
    pdf: bytes | None,
    pdf_nombre: str,
    contexto: ContextoPrecios | None,
    fecha_libro: date | None,
    fecha_devolucion: date,
    otro: bytes | None,
    otro_nombre: str,
) -> ResultadoFusion:
    perfil = cargar_perfil(libro.perfil)
    fecha_portada = fecha_del_libro(libro)
    fecha = fecha_libro or fecha_portada
    if fecha_libro is not None:
        origen_fecha = "dada por el usuario"
    elif fecha_portada is not None:
        origen_fecha = f"PORTADA: «{libro.portada.fecha_texto}»"
    else:
        origen_fecha = f"PORTADA: «{libro.portada.fecha_texto}» (no legible)"

    hoja = hoja_presupuesto(libro, perfil)
    col_pu = perfil.columnas_presupuesto["precio_unitario"]
    col_monto = perfil.columnas_presupuesto["monto"]
    codigos = codigos_de_partida(libro)

    calculos: list[CalculoPartida] = []
    sin_recalculo: list[_SinRecalculo] = []
    for partida in libro.partidas:
        apu = libro.apu(partida.hoja_apu) if partida.hoja_apu else None
        if apu is None or partida.cantidad < 0:
            sin_recalculo.append(_sin_recalculo(partida, hoja, col_pu, col_monto))
            continue
        calculos.append(_calcular(partida, apu, libro, codigos[partida.fila], perfil))

    f1: list[Hallazgo] = []
    atribucion_f1: dict[Hallazgo, str | None] = {}
    for calculo in calculos:
        hallazgo = _hallazgo_f1(calculo, hoja, col_pu)
        if hallazgo is not None:
            f1.append(hallazgo)
            atribucion_f1[hallazgo] = calculo.codigo

    fecha_presupuesto = fecha or fecha_devolucion
    presupuesto = presupuesto_nucleo(libro, calculos, fecha_presupuesto, perfil)
    informe_nucleo = auditar(presupuesto)
    del_libro = reglas_del_libro(libro, perfil)

    pdf_totales: TotalesImpresos | None = None
    pdf_simple: PdfSimple | None = None
    del_pdf: list[Hallazgo] = []
    reglas_evaluadas = (*informe_nucleo.reglas_evaluadas, REGLA_F1, *REGLAS_LIBRO)
    no_evaluadas = [(*REGLA_R11, MOTIVO_R11), (*REGLA_R12, MOTIVO_R12)]
    if pdf is not None:
        pdf_nombre = pdf_nombre or "entregado.pdf"
        leido = _leer_pdf(pdf, pdf_nombre)
        if isinstance(leido, PdfSimple):
            pdf_simple = leido
            del_pdf = reglas_pdf_simple(leido)
            reglas_evaluadas = (*reglas_evaluadas, REGLA_L10)
            no_evaluadas.append((*REGLA_L11, _PDF_ES_SIMPLE))
        else:
            pdf_totales = leido
            del_pdf = cotejar_con_libro(leido, libro)
            reglas_evaluadas = (*reglas_evaluadas, REGLA_L11)
            no_evaluadas.append((*REGLA_L10, _PDF_ES_IMPRESO))
    else:
        no_evaluadas += [(*REGLA_L10, _SIN_PDF_L10), (*REGLA_L11, _SIN_PDF_L11)]
    informados = frozenset(del_pdf)

    informe = InformeAuditoria(
        codigo_presupuesto=presupuesto.codigo,
        hallazgos=(*informe_nucleo.hallazgos, *f1, *del_libro, *del_pdf),
        partida_por_origen=informe_nucleo.partida_por_origen,
        partida_por_hallazgo={**informe_nucleo.partida_por_hallazgo, **atribucion_f1},
        reglas_evaluadas=reglas_evaluadas,
    )

    subtotal = sum((c.partida.cantidad * c.resultado.precio_unitario for c in calculos), Decimal(0))
    subtotal += sum((s.monto for s in sin_recalculo), Decimal(0))
    iva = subtotal * libro.parametros.iva
    totales = {"SUBSINIVA": subtotal, "IVATOT": iva, "TOTALGEN": subtotal + iva}

    otro_libro = leer_libro(otro, otro_nombre, perfil) if otro is not None else None
    alertas = alertas_de_precios(libro, fecha, fecha_devolucion, contexto, otro_libro)

    metadatos = {
        "sha256_origen": libro.sha256,
        "version": version(),
        "fecha": fecha_devolucion.isoformat(),
        "producido_por": PRODUCIDO_POR,
        "fecha_libro": fecha.isoformat() if fecha else "",
    }
    if pdf is not None:
        metadatos["sha256_pdf"] = hashlib.sha256(pdf).hexdigest()

    return ResultadoFusion(
        libro=libro,
        origen=datos,
        pdf_totales=pdf_totales,
        calculos={c.apu.hoja: c.calculado for c in calculos},
        resultados_nucleo={c.apu.hoja: c.resultado for c in calculos},
        precios_unitarios={c.partida.fila: c.resultado.precio_unitario for c in calculos},
        presupuesto=presupuesto,
        informe=informe,
        alertas=alertas,
        trazabilidad=_trazabilidad(
            libro,
            perfil,
            codigos,
            calculos,
            sin_recalculo,
            fecha,
            origen_fecha,
            fecha_presupuesto,
            pdf,
            pdf_nombre,
        ),
        hallazgos_tabla=_tabla(informe.hallazgos, informados),
        totales_silice=totales,
        fecha_libro=fecha,
        fecha_devolucion=fecha_devolucion,
        metadatos=metadatos,
        reglas_no_evaluadas=tuple(no_evaluadas),
        pdf_simple=pdf_simple,
    )


def devolver(resultado: ResultadoFusion) -> bytes:
    """El libro calcado (`.xlsx`) con los valores de Silice y las hojas AUDITORÍA, TRAZABILIDAD y
    ALERTAS USD-Bs (spec §1). Lo escribe el adaptador sobre los bytes del libro recibido; la
    moneda de los impactos es la del presupuesto del núcleo (la del libro)."""
    datos = DatosDevolucion(
        libro=resultado.libro,
        apus=resultado.calculos,
        precios_unitarios=resultado.precios_unitarios,
        totales=resultado.totales_silice,
        hallazgos=resultado.hallazgos_tabla,
        alertas=resultado.alertas,
        trazabilidad=resultado.trazabilidad,
        metadatos=resultado.metadatos,
        reglas_evaluadas=resultado.informe.reglas_evaluadas,
        reglas_no_evaluadas=resultado.reglas_no_evaluadas,
        moneda=resultado.presupuesto.moneda,
    )
    return escribir_devolucion(resultado.origen, datos)
