"""Orquestación de la 1.5: libro de la empresa -> motor del núcleo -> auditoría -> alertas ->
devolución calcada (spec 1.5, F-D2, F-D9).

Sigue el patrón de la reauditoría (`auditoria/reauditoria.py`): procesa un documento ajeno **en
memoria**, no guarda nada, y **no cree los precios escritos**: cada P.U. se recalcula con el motor
del núcleo desde la composición del APU y los precios de INSUMOS (`fusion.mapeo`, F-D1). Lo que el
libro guarda (P de PRESUPUESTO, totales con nombre) solo se usa para compararlo con Silice (F1, L3,
L11) y para lo que Silice no puede recalcular (una partida sin APU entra con su monto guardado y se
informa).

Los servicios de la instalación (tasas del BCV, precios propios) llegan inyectados en un
`ContextoPrecios` (`servicios_desde_sesion` lo arma desde una sesión de la base); sin contexto, las
alertas en Bs dicen "no contrastable".

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
from decimal import Decimal
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.hoja_empresa.escritor import escribir_devolucion
from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.modelo import (
    ApuCalculado,
    DatosDevolucion,
    FilaAlerta,
    FilaHallazgo,
    FilaTraza,
    LibroLeido,
    PartidaLeida,
    Rotulo,
)
from adapters.hoja_empresa.pdf import TotalesImpresos, cotejar_con_libro, leer_totales_impresos
from adapters.hoja_empresa.perfil import Perfil, cargar_perfil, normalizar
from adapters.hoja_empresa.reglas import REGLAS_LIBRO, reglas_del_libro
from core import models
from core.catalog.origen import origenes_efectivos
from core.contracts.apu import ResultadoAPU
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, Severidad
from core.costing.motor import calcular_apu
from core.verification.informe import InformeAuditoria, auditar
from core.verification.texto import formatear_decimal
from fusion.alertas import ContextoPrecios, alertas_de_precios
from fusion.mapeo import (
    CalculoPartida,
    avisos_de_composicion,
    codigos_de_partida,
    componentes,
    composicion_nucleo,
    hoja_presupuesto,
    parametros_nucleo,
    presupuesto_nucleo,
)
from operacion.version import version

__all__ = [
    "ACCION_A_CONFIRMAR",
    "ACCION_CORREGIDO",
    "ACCION_INFORMADO",
    "REGLA_F1",
    "REGLA_L11",
    "ResultadoFusion",
    "devolver",
    "fecha_del_libro",
    "procesar_libro",
    "servicios_desde_sesion",
]

REGLA_F1 = ("F1", "P.U. recalculado")
REGLA_L11 = ("L11", "Libro ↔ PDF entregado")

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

    def __post_init__(self) -> None:
        for nombre in (
            "calculos",
            "resultados_nucleo",
            "precios_unitarios",
            "totales_silice",
            "metadatos",
        ):
            object.__setattr__(self, nombre, MappingProxyType(dict(getattr(self, nombre))))


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
    """
    p = calculo.partida
    guardado = p.guardados.get(col_pu)
    if guardado is None:
        return None
    silice = calculo.resultado.precio_unitario
    diferencia = silice - guardado
    impacto = diferencia * p.cantidad
    if abs(impacto) < UMBRAL_F1:
        return None
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


def _monto_guardado(partida: PartidaLeida, col_pu: str, col_monto: str) -> Decimal:
    """El monto de una partida que Silice no puede recalcular: el guardado en la columna de monto
    o, si no lo hay, cantidad × P guardado; 0 si tampoco."""
    if (monto := partida.guardados.get(col_monto)) is not None:
        return monto
    if (pu := partida.guardados.get(col_pu)) is not None:
        return partida.cantidad * pu
    return Decimal(0)


def _hallazgo_sin_apu(partida: PartidaLeida, hoja: str, col_monto: str, monto: Decimal) -> Hallazgo:
    motivo = (
        "tiene cantidad negativa y no entra al núcleo"
        if partida.cantidad < 0 and partida.hoja_apu
        else "no tiene APU"
    )
    return Hallazgo(
        regla=REGLA_F1[0],
        severidad=Severidad.ADVERTENCIA,
        descripcion=(
            f"partida {partida.numero} ({partida.codigo or 'sin código'}) {motivo}: Silice no "
            f"puede recalcular su P.U. y la suma a los totales con su monto guardado "
            f"({formatear_decimal(monto, 2)})"
        ),
        origen_ids=(f"{hoja}!{col_monto}{partida.fila}",),
        valor_observado=monto,
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


def _tabla(informe: InformeAuditoria, informados: frozenset[Hallazgo]) -> tuple[FilaHallazgo, ...]:
    return tuple(
        FilaHallazgo(
            codigo=h.regla,
            severidad=h.severidad.name,
            descripcion=h.descripcion,
            celda=h.origen_ids[0] if h.origen_ids else "",
            impacto=h.impacto,
            accion=_accion(h, informados),
        )
        for h in informe.hallazgos
    )


def _trazabilidad(
    libro: LibroLeido,
    perfil: Perfil,
    codigos: Mapping[int, str],
    calculos: Sequence[CalculoPartida],
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
            al_nucleo = valor - 1 if valor else valor
            nota = (
                f"factor de la plantilla; el núcleo recibe fcas = {_num(al_nucleo)} y bono de "
                "alimentación 0 (F-D1)"
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
    vistos: set[str] = set()
    for calculo in calculos:
        if calculo.apu.hoja in vistos:
            continue
        vistos.add(calculo.apu.hoja)
        for aviso in avisos_de_composicion(calculo.apu, libro):
            filas.append(FilaTraza("Aviso del mapeo", "", aviso.origen, aviso.mensaje))
    return tuple(filas)


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
) -> ResultadoFusion:
    """Lee el libro, recalcula cada APU con el motor del núcleo, lo audita y arma las alertas.

    Pasos: `leer_libro` -> por cada partida unida a un APU, `calcular_apu` con la composición y los
    parámetros de `fusion.mapeo` -> F1 -> `auditar` el presupuesto del núcleo (R1-R7) -> L1-L9
    (`reglas_del_libro`) -> L11 si hay PDF -> informe combinado -> totales de Silice -> alertas.

    `fecha_devolucion` la pasa la interfaz (o la API) explícita; por omisión es hoy, y ese es el
    único lugar donde se lee el reloj. `otro` son los bytes de otra versión del mismo libro, para
    las alertas de cambio de precio. Lanza `ArchivoRechazado` si la guardia o el lector rechazan el
    libro (o la otra versión).
    """
    if fecha_devolucion is None:
        fecha_devolucion = date.today()
    perfil = cargar_perfil()
    libro = leer_libro(datos, nombre, perfil)
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
    sin_apu: list[tuple[PartidaLeida, Decimal]] = []
    for partida in libro.partidas:
        apu = libro.apu(partida.hoja_apu) if partida.hoja_apu else None
        if apu is None or partida.cantidad < 0:
            sin_apu.append((partida, _monto_guardado(partida, col_pu, col_monto)))
            continue
        composicion = composicion_nucleo(apu, libro, codigos[partida.fila])
        resultado = calcular_apu(composicion, parametros_nucleo(apu, libro))
        calculos.append(
            CalculoPartida(
                partida=partida,
                apu=apu,
                codigo=codigos[partida.fila],
                composicion=composicion,
                resultado=resultado,
                calculado=componentes(apu, libro, resultado),
            )
        )

    f1: list[Hallazgo] = []
    atribucion_f1: dict[Hallazgo, str | None] = {}
    for calculo in calculos:
        hallazgo = _hallazgo_f1(calculo, hoja, col_pu)
        if hallazgo is not None:
            f1.append(hallazgo)
            atribucion_f1[hallazgo] = calculo.codigo
    informados: set[Hallazgo] = set()
    for partida, monto in sin_apu:
        hallazgo = _hallazgo_sin_apu(partida, hoja, col_monto, monto)
        f1.append(hallazgo)
        informados.add(hallazgo)

    fecha_presupuesto = fecha or fecha_devolucion
    presupuesto = presupuesto_nucleo(libro, calculos, fecha_presupuesto, perfil)
    informe_nucleo = auditar(presupuesto)
    del_libro = reglas_del_libro(libro)

    pdf_totales: TotalesImpresos | None = None
    del_pdf: list[Hallazgo] = []
    reglas_evaluadas = (*informe_nucleo.reglas_evaluadas, REGLA_F1, *REGLAS_LIBRO)
    if pdf is not None:
        pdf_nombre = pdf_nombre or "entregado.pdf"
        pdf_totales = leer_totales_impresos(pdf, pdf_nombre)
        del_pdf = cotejar_con_libro(pdf_totales, libro)
        reglas_evaluadas = (*reglas_evaluadas, REGLA_L11)
    informados.update(del_pdf)

    informe = InformeAuditoria(
        codigo_presupuesto=presupuesto.codigo,
        hallazgos=(*informe_nucleo.hallazgos, *f1, *del_libro, *del_pdf),
        partida_por_origen=informe_nucleo.partida_por_origen,
        partida_por_hallazgo={**informe_nucleo.partida_por_hallazgo, **atribucion_f1},
        reglas_evaluadas=reglas_evaluadas,
    )

    subtotal = sum((c.partida.cantidad * c.resultado.precio_unitario for c in calculos), Decimal(0))
    subtotal += sum((monto for _, monto in sin_apu), Decimal(0))
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
            fecha,
            origen_fecha,
            fecha_presupuesto,
            pdf,
            pdf_nombre,
        ),
        hallazgos_tabla=_tabla(informe, frozenset(informados)),
        totales_silice=totales,
        fecha_libro=fecha,
        fecha_devolucion=fecha_devolucion,
        metadatos=metadatos,
    )


def devolver(resultado: ResultadoFusion) -> bytes:
    """El libro calcado (`.xlsx`) con los valores de Silice y las hojas AUDITORÍA, TRAZABILIDAD y
    ALERTAS USD-Bs (spec §1). Lo escribe el adaptador sobre los bytes del libro recibido."""
    datos = DatosDevolucion(
        libro=resultado.libro,
        apus=resultado.calculos,
        precios_unitarios=resultado.precios_unitarios,
        totales=resultado.totales_silice,
        hallazgos=resultado.hallazgos_tabla,
        alertas=resultado.alertas,
        trazabilidad=resultado.trazabilidad,
        metadatos=resultado.metadatos,
    )
    return escribir_devolucion(resultado.origen, datos)


# --- Servicios de la instalación ----------------------------------------------------------------


def _precios_de_empresa(session: Session) -> dict[str, tuple[Decimal, date, str]]:
    """Código -> (precio, fecha, moneda) de la lista de empresa más reciente de la instalación.

    El código de la empresa (MT-01, MO-03…) se busca primero como Ref del precio
    (`ReferenciaPrecio`, solo las Ref únicas en la lista, como hace la reauditoría con MaPreX) y
    luego como código del insumo del catálogo. La fecha es la del origen efectivo del precio
    (`PrecioOrigen` o, si falta, la vigencia de la lista).
    """
    lista = session.scalars(
        select(models.ListaPrecios)
        .join(models.ListaEmpresa, models.ListaEmpresa.lista_id == models.ListaPrecios.id)
        .order_by(models.ListaPrecios.id.desc())
        .limit(1)
    ).one_or_none()
    if lista is None:
        return {}
    origenes = origenes_efectivos(session, lista)
    refs = dict(
        session.execute(
            select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
            .join(models.PrecioInsumo, models.PrecioInsumo.id == models.ReferenciaPrecio.precio_id)
            .where(models.PrecioInsumo.lista_id == lista.id)
        ).all()
    )
    veces: dict[str, int] = {}
    for ref in refs.values():
        veces[ref] = veces.get(ref, 0) + 1
    salida: dict[str, tuple[Decimal, date, str]] = {}
    for precio in lista.precios:
        dato = (precio.precio, origenes[precio.id].fecha_precio, lista.moneda)
        salida.setdefault(precio.insumo.codigo, dato)
    for precio in lista.precios:
        ref = refs.get(precio.id)
        if ref and veces[ref] == 1:
            salida[ref] = (precio.precio, origenes[precio.id].fecha_precio, lista.moneda)
    return salida


def servicios_desde_sesion(session: Session) -> ContextoPrecios:
    """El `ContextoPrecios` de esta instalación: las tasas del BCV que importó (las mismas de la
    reauditoría, `auditoria.servicios.servicios_de_la_instalacion`) y los precios de su lista de
    empresa más reciente.

    Los precios se leen una vez, al armar el contexto: la sesión puede cerrarse después de
    consultar las alertas, pero no antes (las tasas se consultan con ella).

    Límite: la lista de empresa es una copia de su lista base con los propios encima (S1 §6.1);
    aquí cuentan todos sus precios, heredados o propios, porque todos son "el precio de la empresa"
    en la instalación. Un código de la empresa que no es Ref ni código del catálogo no contrasta.
    """
    # Importación diferida a propósito: `auditoria` importa la reauditoría, que arrastra
    # `adapters.espacio` y con él el extra `planos` (shapely, ezdxf). Leer, recalcular y devolver
    # un libro no lo necesita; solo armar el contexto desde la base de la instalación.
    from auditoria.servicios import servicios_de_la_instalacion

    servicios = servicios_de_la_instalacion(session)
    precios = _precios_de_empresa(session)
    return ContextoPrecios(
        tasa_en=servicios.tasa_en,
        precio_propio=precios.get if precios else None,
    )
