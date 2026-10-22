"""Control de obra sin Streamlit (UC-19 y UC-20; spec S2 §5.5).

Lo que la pantalla «Control de obra» necesita del núcleo: declarar la línea base de control,
registrar una valuación a mano o desde un XLSX, anularla, anotar costos incurridos, calcular al
corte el valor ganado, la separación del desvío, las alertas y la reproyección **siempre**,
calcular las opciones de recuperación **a pedido** y elegir una, y armar las hojas
«Valuaciones», «Valor ganado» y «Decisiones» del Excel de la hoja (`hojas_extra`).

Cada función que escribe confirma su transacción o la deshace (`rollback`) y levanta
`ControlInvalido` con un mensaje en español, sin *traceback*. Los textos que vienen de fuera
(inspector, observación y fuente de un XLSX) los muestra la página con `ui.texto_seguro` o en
celdas (RV-14). Los montos se presentan a dos decimales y los índices a cuatro, que es donde se
redondea. Sin Streamlit, sin `pandas` y sin `ui.caso`; lo vigila
`tests/unit/test_arquitectura_s2.py`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core import models
from core.budget.calendario import dia_habil
from core.budget.control import (
    ResultadoControl,
    calcular_control,
    composiciones_de_la_linea_base,
    construir_estado,
    contexto_de_recuperacion,
    costo_real_al_corte,
    guardar_parametros,
    parametros_de_control,
    precios_del_corte_de_version,
)
from core.budget.decision import aplicar_decision, decisiones
from core.budget.excel import TablaExportable
from core.budget.recuperacion import Opcion, opciones
from core.budget.valor_ganado import (
    ParametrosControl,
    PreciosDelCorte,
    indicadores,
    precios_por_escalatoria,
)
from core.budget.valuaciones import (
    Calendario,
    LecturaControl,
    LineaBaseInvalidada,
    anular_valuacion,
    instantanea_control,
    leer_valuaciones_excel,
    linea_base_vigente,
    registrar_costo,
    registrar_lectura,
    registrar_linea_base,
    registrar_valuacion,
    tabla_valuaciones,
    valuaciones_registradas,
)
from core.catalog import Catalogo
from core.catalog.indices import TasaNoDisponible, tasa_aplicable
from core.catalog.moneda import convertir
from core.verification.texto import formatear_decimal
from core.verification.valuaciones import LineaValuacion

__all__ = [
    "COLUMNAS_ALERTAS",
    "COLUMNAS_DECISIONES",
    "COLUMNAS_INDICADORES",
    "COLUMNAS_LINEAS",
    "COLUMNAS_OPCIONES",
    "COLUMNAS_PARAMETROS",
    "COLUMNAS_REPROYECCION",
    "COLUMNAS_VALUACIONES",
    "METODOS_DE_PRECIOS",
    "PARAMETROS_EDITABLES",
    "ControlInvalido",
    "PrecioElegido",
    "PLANTILLAS_DEL_NUCLEO",
    "catalogo_de_frases",
    "alertas_en_filas",
    "con_tildes",
    "corte_por_defecto",
    "describir_linea_base",
    "dia_con_fecha",
    "estudios_que_suma",
    "filas_del_plan_reproyectado",
    "hay_valuaciones",
    "parametros_actuales",
    "texto_monto",
    "tiene_linea_base",
    "valuaciones_para_anular",
    "anular",
    "calcular_el_control",
    "calcular_las_opciones",
    "curva_pv_ev_ac",
    "declarar_linea_base",
    "elegir_opcion",
    "estado_de_valuaciones",
    "filas_de_decisiones",
    "filas_de_parametros",
    "filas_de_indicadores",
    "filas_de_opciones",
    "supuestos_de_opcion",
    "filas_de_reproyeccion",
    "filas_de_valuaciones",
    "guardar_los_parametros",
    "importar_excel",
    "leer_excel",
    "lineas_desde_filas",
    "parametros_desde_filas",
    "precios_del_corte",
    "registrar_costo_real",
    "registrar_y_controlar",
    "tablas_de_control",
    "versiones_para_la_linea_base",
    "versiones_revaloradas",
]

METODO_NINGUNO = "Sin precios del corte"
METODO_COMPROBACION = "Comprobacion directa (version revalorada)"
METODO_ESCALATORIA = "Escalatoria (un Km declarado)"
METODOS_DE_PRECIOS = (METODO_NINGUNO, METODO_COMPROBACION, METODO_ESCALATORIA)
COLUMNAS_LINEAS = ("Partida", "Cantidad", "Fecha de medicion", "Observacion")
COLUMNAS_VALUACIONES = ("Numero", "Periodo", "Fecha", "Inspector", "Registrada", "Estado")
COLUMNAS_INDICADORES = ("Indicador", "Valor", "En la otra moneda", "Nota")
COLUMNAS_ALERTAS = ("Alerta", "Severidad", "Descripcion", "Observado", "Umbral")
COLUMNAS_REPROYECCION = ("Partida", "Indice", "Fin (dia habil)", "Nota")
COLUMNAS_OPCIONES = (
    "Opcion",
    "Termino",
    "Retraso (dias)",
    "Costo directo adicional",
    "Costo indirecto",
    "Penalizacion",
    "Punto de equilibrio",
    "Nota",
)
COLUMNAS_DECISIONES = ("Version", "Opcion", "Corte", "Termino", "Fuente", "Responsable")
NO_DISPONIBLE = "no disponible"
NO_APLICA = "no aplica"
NATURALEZA_SUPUESTO = "SUPUESTO_DECLARADO"
NATURALEZA_DATO = "DATO_DEL_CONTRATO"


class ControlInvalido(ValueError):  # noqa: N818
    """Algo del control no se pudo hacer; el mensaje dice qué pasó y cómo arreglarlo."""


def _monto(valor: Decimal | None) -> str:
    return NO_DISPONIBLE if valor is None else formatear_decimal(valor, 2)


def _indice(valor: Decimal | None) -> str:
    return NO_APLICA if valor is None else formatear_decimal(valor, 4)


def _fecha(texto: str, que: str) -> date:
    try:
        return date.fromisoformat(texto.strip()[:10])
    except ValueError:
        raise ControlInvalido(f"{que}: {texto!r} no es una fecha (AAAA-MM-DD)") from None


def _decimal(texto: str, que: str) -> Decimal:
    try:
        valor = Decimal(str(texto).strip())
    except InvalidOperation:
        raise ControlInvalido(f"{que}: {texto!r} no es un numero decimal") from None
    if not valor.is_finite():
        raise ControlInvalido(f"{que}: {texto!r} no es un numero finito")
    return valor


def _escribir(sesion: Session, accion):
    """Corre `accion`, confirma si sale bien y deshace si no; todo error sale como
    `ControlInvalido`."""
    try:
        resultado = accion()
        sesion.commit()
        return resultado
    except ControlInvalido:
        sesion.rollback()
        raise
    except LineaBaseInvalidada as error:
        sesion.rollback()
        raise ControlInvalido(str(error)) from error
    except (ValueError, KeyError) as error:
        sesion.rollback()
        raise ControlInvalido(
            str(error.args[0] if isinstance(error, KeyError) else error)
        ) from error
    except SQLAlchemyError as error:
        sesion.rollback()
        raise ControlInvalido(
            f"No se pudo escribir en el caso: {getattr(error, 'orig', error)}"
        ) from error


# ---------------------------------------------------------------------------------------------
# Línea base, valuaciones, anulación y costos (UC-19)
# ---------------------------------------------------------------------------------------------


def versiones_para_la_linea_base(sesion: Session, proyecto: str) -> list[str]:
    """Los códigos de las versiones guardadas del proyecto, de la más reciente a la más antigua."""
    return list(
        sesion.scalars(
            select(models.Presupuesto.codigo)
            .join(models.Proyecto)
            .where(models.Proyecto.nombre == proyecto)
            .order_by(models.Presupuesto.id.desc())
        )
    )


def versiones_revaloradas(sesion: Session, proyecto: str) -> list[str]:
    """Las versiones revaloradas por UC-02: las que sirven para los precios del corte."""
    return list(
        sesion.scalars(
            select(models.Presupuesto.codigo)
            .join(models.Proyecto)
            .join(
                models.VersionOrigen, models.VersionOrigen.presupuesto_id == models.Presupuesto.id
            )
            .where(
                models.Proyecto.nombre == proyecto, models.VersionOrigen.motivo == "revaloracion"
            )
            .order_by(models.Presupuesto.id.desc())
        )
    )


def declarar_linea_base(
    sesion: Session,
    proyecto: str,
    version: str,
    *,
    desde: str,
    perspectiva: str,
    inicio: str,
    dias_por_periodo: str,
    feriados: str,
    fuente: str,
    responsable: str,
) -> None:
    """Declara la línea base de control (RF-72) desde los textos de la pantalla. Los feriados van
    separados por comas o saltos de línea, en AAAA-MM-DD."""
    dias = _decimal(dias_por_periodo, "dias por periodo")
    if dias != dias.to_integral_value():
        raise ControlInvalido(f"dias por periodo: {dias_por_periodo!r} debe ser un entero")
    lista = [parte for parte in feriados.replace("\n", ",").split(",") if parte.strip()]

    def accion():
        return registrar_linea_base(
            sesion,
            proyecto,
            version,
            desde=_fecha(desde, "desde"),
            perspectiva=perspectiva,
            calendario=Calendario(
                _fecha(inicio, "fecha de inicio"),
                int(dias),
                tuple(_fecha(dia, "feriado") for dia in lista),
            ),
            fuente=fuente,
            responsable=responsable,
        )

    _escribir(sesion, accion)


def lineas_desde_filas(filas: Sequence[Mapping[str, object]]) -> list[LineaValuacion]:
    """Las líneas de la tabla de la pantalla (`COLUMNAS_LINEAS`) como líneas de valuación. Una fila
    sin partida y sin cantidad se ignora; una cantidad ilegible o negativa se rechaza con su
    fila."""
    lineas: list[LineaValuacion] = []
    for numero, fila in enumerate(filas, start=1):
        partida = str(fila.get("Partida") or "").strip()
        cantidad = str(fila.get("Cantidad") or "").strip()
        if not partida and not cantidad:
            continue
        if not partida:
            raise ControlInvalido(f"fila {numero}: falta la partida")
        medicion = str(fila.get("Fecha de medicion") or "").strip()
        try:
            lineas.append(
                LineaValuacion(
                    partida,
                    _decimal(cantidad, f"fila {numero}, cantidad"),
                    _fecha(medicion, f"fila {numero}, fecha de medicion") if medicion else None,
                    str(fila.get("Observacion") or "").strip(),
                )
            )
        except ValueError as error:
            raise ControlInvalido(f"fila {numero}: {error}") from None
    return lineas


def registrar_y_controlar(
    sesion: Session,
    proyecto: str,
    catalogo: Catalogo,
    *,
    numero: str,
    desde: str,
    hasta: str,
    fecha: str,
    inspector: str,
    filas: Sequence[Mapping[str, object]],
    fuente: str,
    responsable: str,
    precios: PreciosDelCorte | None = None,
) -> ResultadoControl:
    """UC-19 4 y 5: registra la valuación y calcula al corte (su fecha *hasta*) el informe de
    control, los indicadores, las alertas y la reproyección. Es lo que mide RNF-15."""
    fin = _fecha(hasta, "hasta")

    def accion():
        registrar_valuacion(
            sesion,
            proyecto,
            numero=numero,
            desde=_fecha(desde, "desde"),
            hasta=fin,
            fecha=_fecha(fecha, "fecha") if fecha.strip() else None,
            inspector=inspector,
            lineas=lineas_desde_filas(filas),
            fuente=fuente,
            responsable=responsable,
        )

    _escribir(sesion, accion)
    return calcular_el_control(sesion, proyecto, catalogo, corte=fin, precios=precios)


def anular(sesion: Session, valuacion_id: int, *, motivo: str, responsable: str) -> None:
    """Anula una valuación (UC-19 4c): se conserva y deja de contar."""
    _escribir(
        sesion,
        lambda: anular_valuacion(sesion, valuacion_id, motivo=motivo, responsable=responsable),
    )


def registrar_costo_real(
    sesion: Session,
    proyecto: str,
    *,
    monto: str,
    moneda: str,
    fecha: str,
    fuente: str,
    responsable: str,
    partida: str = "",
) -> None:
    """Anota un costo incurrido (monto, moneda, fecha y fuente); se convierte al calcular."""
    _escribir(
        sesion,
        lambda: registrar_costo(
            sesion,
            proyecto,
            monto=_decimal(monto, "monto"),
            moneda=moneda,
            fecha=_fecha(fecha, "fecha"),
            fuente=fuente,
            responsable=responsable,
            codigo_partida=partida.strip() or None,
        ),
    )


def leer_excel(ruta: Path) -> LecturaControl:
    """Lee un XLSX de valuaciones sin escribir nada (informe previo). `ControlInvalido` si se
    rechaza: el archivo se rechaza entero."""
    try:
        return leer_valuaciones_excel(ruta)
    except ValueError as error:
        raise ControlInvalido(str(error)) from None


def importar_excel(
    sesion: Session, proyecto: str, lectura: LecturaControl, *, fuente: str, responsable: str
) -> int:
    """Registra lo leído (todas las valuaciones y costos, o ninguno) y devuelve cuántas son."""
    registradas, _ = _escribir(
        sesion,
        lambda: registrar_lectura(
            sesion, proyecto, lectura, fuente=fuente, responsable=responsable
        ),
    )
    return len(registradas)


# ---------------------------------------------------------------------------------------------
# Cálculo (UC-20 1 a 3, siempre) y opciones (UC-20 4 a 6, a pedido)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PrecioElegido:
    """Cómo se toman los precios del corte (S2 §4.3): ninguno, una versión revalorada
    (comprobación directa) o la escalatoria con un solo `Km` y `R` declarados. Son textos de la
    pantalla."""

    metodo: str = METODO_NINGUNO
    version: str = ""
    km: str = ""
    r: str = "0"
    fuente: str = ""


def precios_del_corte(
    sesion: Session, proyecto: str, catalogo: Catalogo, elegido: PrecioElegido, perspectiva: str
) -> PreciosDelCorte | None:
    """Los `PreciosDelCorte` que corresponden a la elección, o `None` si no se eligió ninguno."""
    if elegido.metodo == METODO_COMPROBACION:
        if not elegido.version:
            raise ControlInvalido("elija la version revalorada para la comprobacion directa")
        try:
            return precios_del_corte_de_version(
                sesion, proyecto, elegido.version, perspectiva, catalogo
            )
        except (KeyError, ValueError) as error:
            raise ControlInvalido(str(error.args[0])) from None
    if elegido.metodo == METODO_ESCALATORIA:
        if not elegido.fuente.strip():
            raise ControlInvalido("la escalatoria necesita la fuente de Km y R")
        base = instantanea_control(sesion, proyecto, catalogo=catalogo).presupuesto
        unitarios = {
            p.item.codigo_partida: (
                p.resultado.costo_directo if perspectiva == "costo" else p.resultado.precio_unitario
            )
            for p in base.partidas
        }
        km = _decimal(elegido.km, "Km")
        try:
            return precios_por_escalatoria(
                unitarios, dict.fromkeys(unitarios, km), _decimal(elegido.r, "R"), elegido.fuente
            )
        except ValueError as error:
            raise ControlInvalido(str(error)) from None
    return None


def calcular_el_control(
    sesion: Session,
    proyecto: str,
    catalogo: Catalogo,
    *,
    corte: date | None = None,
    precios: PreciosDelCorte | None = None,
) -> ResultadoControl:
    """El control al corte (sin escribir). `ControlInvalido` si no hay línea base, si está
    invalidada por un cambio de moneda o si no hay valuaciones ni corte."""
    try:
        return calcular_control(sesion, proyecto, catalogo=catalogo, corte=corte, precios=precios)
    except LineaBaseInvalidada as error:
        raise ControlInvalido(str(error)) from error
    except ValueError as error:
        raise ControlInvalido(str(error)) from None


def calcular_las_opciones(
    resultado: ResultadoControl,
    *,
    objetivo: str = "",
    horas_previas: str = "0",
    independientes: str = "",
) -> tuple[Opcion, ...]:
    """Las cuatro opciones de recuperación a pedido (UC-20 4). `objetivo` es el día hábil objetivo
    (vacío = el fin del plan base). `ControlInvalido` si un límite legal se rompe."""
    try:
        contexto = contexto_de_recuperacion(
            resultado,
            composiciones_de_la_linea_base(resultado),
            objetivo=int(_decimal(objetivo, "objetivo")) if objetivo.strip() else None,
            horas_previas=_decimal(horas_previas or "0", "horas extra previas"),
        )
        return opciones(contexto)
    except ValueError as error:
        raise ControlInvalido(str(error)) from None


def elegir_opcion(
    sesion: Session,
    resultado: ResultadoControl,
    opcion: Opcion,
    catalogo: Catalogo,
    *,
    fuente: str,
    responsable: str,
    declaracion_independencia: str = "",
) -> str:
    """UC-20 5 y 6: crea la versión de la opción elegida y guarda la decisión. Devuelve el código de
    la versión nueva."""
    decision = _escribir(
        sesion,
        lambda: aplicar_decision(
            sesion,
            resultado,
            opcion,
            catalogo=catalogo,
            fuente=fuente,
            responsable=responsable,
            declaracion_independencia=declaracion_independencia,
        ),
    )
    return sesion.get(models.Presupuesto, decision.version_resultante_id).codigo


# ---------------------------------------------------------------------------------------------
# Tablas para la pantalla y para el Excel
# ---------------------------------------------------------------------------------------------

_ORDEN = {"ERROR": 3, "ADVERTENCIA": 2, "INFO": 1}


def estado_de_valuaciones(resultado: ResultadoControl) -> dict[str, str]:
    """Por clave de valuación, el peor hallazgo de R13-R14 (columna Estado, como RF-55)."""
    peores: dict[str, tuple[int, str]] = {}
    for hallazgo in resultado.informe.hallazgos:
        clave = hallazgo.origen_ids[0].split(":")[1]
        rango = _ORDEN.get(hallazgo.severidad.name, 0)
        texto = f"{hallazgo.severidad.name}: {hallazgo.regla}"
        if clave not in peores or rango > peores[clave][0]:
            peores[clave] = (rango, texto)
    return {clave: texto for clave, (_, texto) in peores.items()}


def filas_de_valuaciones(resultado: ResultadoControl) -> list[dict[str, str]]:
    """Las valuaciones guardadas, en solo lectura, con su fecha de registro y su Estado. Las fechas
    van en dd/mm/aaaa, cada una en su columna: el número y el inspector los escribió el usuario."""
    estados = estado_de_valuaciones(resultado)
    return [
        {
            "Numero": v.numero or f"#{v.id}",
            "Periodo": f"{v.desde:%d/%m/%Y} a {v.hasta:%d/%m/%Y}",
            "Fecha": "" if v.fecha is None else f"{v.fecha:%d/%m/%Y}",
            "Inspector": v.inspector,
            "Registrada": "" if v.fecha_hora is None else v.fecha_hora.strftime("%d/%m/%Y %H:%M"),
            "Estado": estados.get(v.clave, "sin hallazgos"),
        }
        for v in resultado.instantanea.valuaciones
    ]


def _otra_moneda(sesion: Session, resultado: ResultadoControl) -> tuple[str, Decimal | None]:
    """La moneda que no es la del proyecto y la tasa aplicable a la fecha del corte (S1)."""
    moneda = resultado.instantanea.moneda
    otra = "USD" if moneda == "Bs" else "Bs"
    try:
        return otra, tasa_aplicable(sesion, resultado.instantanea.corte).valor
    except TasaNoDisponible:
        return otra, None


def filas_de_indicadores(sesion: Session, resultado: ResultadoControl) -> list[dict[str, str]]:
    """La tabla de §4.2 y la separación de §4.3, cada monto en las dos monedas con la tasa del
    corte (S1); lo que no se puede calcular dice «no disponible» y por qué."""
    ind, sep = resultado.indicadores, resultado.separacion
    moneda = resultado.instantanea.moneda
    otra, tasa = _otra_moneda(sesion, resultado)

    def en_otra(valor: Decimal | None) -> str:
        if valor is None or tasa is None:
            return NO_DISPONIBLE
        return formatear_decimal(convertir(valor, moneda, otra, tasa), 2)

    def monto(nombre: str, valor: Decimal | None, nota: str = "") -> dict[str, str]:
        return {
            "Indicador": f"{nombre} ({moneda})",
            "Valor": _monto(valor),
            "En la otra moneda": f"{en_otra(valor)} {otra}" if tasa is not None else NO_DISPONIBLE,
            "Nota": nota,
        }

    def indice(nombre: str, valor: Decimal | None, nota: str = "") -> dict[str, str]:
        return {"Indicador": nombre, "Valor": _indice(valor), "En la otra moneda": "", "Nota": nota}

    no = ind.no_disponible
    filas = [
        monto("BAC", ind.bac),
        monto("PV", ind.pv),
        monto("EV", ind.ev),
        monto("AC", ind.ac, con_tildes(no.get("AC", ""))),
        monto("SV (plazo)", ind.sv),
        monto("CV", ind.cv, con_tildes(no.get("CV", ""))),
        indice("SPI", ind.spi, con_tildes(no.get("SPI", ""))),
        indice("CPI", ind.cpi, con_tildes(no.get("CPI", ""))),
        monto("EAC (índice BAC/CPI)", ind.eac_indice, con_tildes(no.get("EAC", ""))),
        monto("EAC (sistema)", ind.eac_sistema, con_tildes(no.get("EAC", ""))),
        monto("VAC", ind.vac, con_tildes(no.get("VAC", ""))),
        {
            "Indicador": "Término por el índice (día hábil)",
            "Valor": NO_APLICA if ind.termino_indice is None else str(ind.termino_indice),
            "En la otra moneda": "",
            "Nota": "",
        },
        monto("Desvío de precio", sep.precio, con_tildes(sep.no_disponible.get("precio", ""))),
        monto("Desvío de consumo", sep.consumo, con_tildes(sep.no_disponible.get("consumo", ""))),
    ]
    if sep.metodo:
        filas.append(
            {
                "Indicador": "Método y fuente del precio del corte",
                "Valor": sep.metodo,
                "En la otra moneda": "",
                "Nota": sep.fuente,
            }
        )
    if tasa is None:
        filas.append(
            {
                "Indicador": "Tasa del corte",
                "Valor": NO_DISPONIBLE,
                "En la otra moneda": "",
                "Nota": "sin tasa aplicable a la fecha del corte",
            }
        )
    return filas


# --- tildes de las alertas ---------------------------------------------------------------------
#
# El texto de las alertas y de sus motivos nace en `core/budget/valor_ganado.py` y
# `core/budget/equilibrio.py` sin tildes, y `core/` no se toca. Aquí se restituyen sobre las FRASES
# FIJAS del núcleo, nunca sobre palabras sueltas: lo que escribió el usuario (código o nombre de una
# partida, montos, fechas) entra en un hueco `{nombre}` y sale tal cual. Una frase que el catálogo
# no conoce pasa sin cambios; la prueba de guardia (tests/unit/test_control_alertas_tildes.py)
# lista las frases del núcleo que falten aquí.

#: (frase tal como la emite el núcleo, la misma con tildes). Los huecos `{x}` son datos.
PLANTILLAS_DEL_NUCLEO: tuple[tuple[str, str], ...] = (
    # AL-1 y AL-2
    ("retraso: SPI {spi}", "retraso: SPI {spi}"),
    ("sobrecosto: CPI {cpi}", "sobrecosto: CPI {cpi}"),
    # AL-3
    (
        "el termino proyectado (dia {termino}) pasa {retraso} dia(s) habil(es) del plan base "
        "(dia {plan})",
        "el término proyectado (día {termino}) pasa {retraso} día(s) hábil(es) del plan base "
        "(día {plan})",
    ),
    # AL-4: el mensaje del punto de equilibrio que cierra la frase
    (
        "el punto de equilibrio proyectado: no existe punto de equilibrio: el margen de "
        "contribucion no es positivo",
        "el punto de equilibrio proyectado: no existe punto de equilibrio: el margen de "
        "contribución no es positivo",
    ),
    (
        "el punto de equilibrio proyectado: el punto de equilibrio no se alcanza dentro del "
        "contrato",
        "el punto de equilibrio proyectado: el punto de equilibrio no se alcanza dentro del "
        "contrato",
    ),
    (
        "el punto de equilibrio proyectado: el presupuesto no tiene ventas: no aplica",
        "el punto de equilibrio proyectado: el presupuesto no tiene ventas: no aplica",
    ),
    (
        "el punto de equilibrio proyectado: se alcanza en {periodo}",
        "el punto de equilibrio proyectado: se alcanza en {periodo}",
    ),
    (
        "el punto de equilibrio proyectado: sin curva de inversion: el punto de equilibrio no "
        "se ubica en el plan",
        "el punto de equilibrio proyectado: sin curva de inversión: el punto de equilibrio no "
        "se ubica en el plan",
    ),
    (
        "el punto de equilibrio proyectado sube mas de {puntos} puntos porcentuales sobre el de "
        "la linea base",
        "el punto de equilibrio proyectado sube más de {puntos} puntos porcentuales sobre el de "
        "la línea base",
    ),
    # AL-5
    (
        "evaluar el reajuste (S1; LCP art. 133, a cotejar): el precio del corte desvia {precio} "
        "sobre un valor ganado de {ev}",
        "evaluar el reajuste (S1; LCP art. 133, a cotejar): el precio del corte desvía {precio} "
        "sobre un valor ganado de {ev}",
    ),
    # AL-6
    (
        "la partida {codigo} tiene trabajo planificado y ningun avance (detenida)",
        "la partida {codigo} tiene trabajo planificado y ningún avance (detenida)",
    ),
    # Motivos de las alertas sin evaluar
    ("SPI no aplica", "SPI no aplica"),
    ("CPI no disponible", "CPI no disponible"),
    ("AC no disponible", "AC no disponible"),
    ("EAC no disponible", "EAC no disponible"),
    (
        "el punto de equilibrio no aplica o AC no esta disponible",
        "el punto de equilibrio no aplica o AC no está disponible",
    ),
    ("sin avance ejecutado", "sin avance ejecutado"),
    ("sin costos reales declarados", "sin costos reales declarados"),
    ("sin tasa aplicable para: {cortes}", "sin tasa aplicable para: {cortes}"),
    (
        "PV = 0: el corte es anterior a todo trabajo planificado",
        "PV = 0: el corte es anterior a todo trabajo planificado",
    ),
    ("AC = 0: aun no hay costos reales", "AC = 0: aún no hay costos reales"),
    ("sin precios del corte", "sin precios del corte"),
    (
        "sin precios del corte (S1): la separacion no esta disponible",
        "sin precios del corte (S1): la separación no está disponible",
    ),
    (
        "sin precio del corte para la partida {codigo}",
        "sin precio del corte para la partida {codigo}",
    ),
    ("sin precio del corte para {partidas}", "sin precio del corte para {partidas}"),
    (
        "sin avance o sin costos reales: el rendimiento del consumo no existe",
        "sin avance o sin costos reales: el rendimiento del consumo no existe",
    ),
    ("no proyectable: {partidas}", "no proyectable: {partidas}"),
    (
        "nada queda pendiente: la fecha de la ultima valuacion",
        "nada queda pendiente: la fecha de la última valuación",
    ),
    # Motivos por partida de la reproyección
    ("la partida no esta en el plan", "la partida no está en el plan"),
    (
        "el SPI global es 0: sin ritmo no se proyecta",
        "el SPI global es 0: sin ritmo no se proyecta",
    ),
    # Recuperación (opciones), supuestos, requisitos y mensajes sueltos del punto de equilibrio
    ("Mas cuadrillas", "Más cuadrillas"),
    ("Horas extra", "Horas extra"),
    ("Partidas en paralelo", "Partidas en paralelo"),
    ("Aceptar el retraso", "Aceptar el retraso"),
    ("ninguna partida pasa del objetivo", "ninguna partida pasa del objetivo"),
    (
        "ninguna partida sin empezar con inicio posterior al periodo siguiente",
        "ninguna partida sin empezar con inicio posterior al período siguiente",
    ),
    ("no aplica ({lista})", "no aplica ({lista})"),
    ("sin composicion de APU", "sin composición de APU"),
    ("sin rendimiento", "sin rendimiento"),
    ("sin mano de obra a jornal", "sin mano de obra a jornal"),
    (
        "sin fuente: ninguna norma verificada la fija",
        "sin fuente: ninguna norma verificada la fija",
    ),
    (
        "permiso de la Inspectoria del Trabajo (LOTTT art. 182) para las horas extra",
        "permiso de la Inspectoría del Trabajo (LOTTT art. 182) para las horas extra",
    ),
    ("penalizacion diaria", "penalización diaria"),
    ("composiciones de la linea base", "composiciones de la línea base"),
    ("costo diario de la cuadrilla", "costo diario de la cuadrilla"),
    ("costo fijo en el tiempo", "costo fijo en el tiempo"),
    ("CF' = CF · D'/D", "CF' = CF · D'/D"),
    ("eta de cuadrillas", "eta de cuadrillas"),
    (
        "Lee (2022) es la base del metodo, no del valor",
        "Lee (2022) es la base del método, no del valor",
    ),
    ("cuadrillas maximas", "cuadrillas máximas"),
    ("horas extra por dia", "horas extra por día"),
    ("tope legal 2 h", "tope legal 2 h"),
    ("eta de horas extra", "eta de horas extra"),
    ("LOTTT art. 118: por lo menos 50 %", "LOTTT art. 118: por lo menos 50 %"),
    ("FCAS sobre las horas extra", "FCAS sobre las horas extra"),
    ("si", "sí"),
    (
        "interpretacion de los arts. 104 y 178; decide el tutor",
        "interpretación de los arts. 104 y 178; decide el tutor",
    ),
    ("jornada ordinaria", "jornada ordinaria"),
    ("LOTTT art. 173", "LOTTT art. 173"),
    ("limites de horas extra", "límites de horas extra"),
    ("10 h por semana, 100 h por año", "10 h por semana, 100 h por año"),
    ("LOTTT art. 178", "LOTTT art. 178"),
    ("independencia de las partidas", "independencia de las partidas"),
    (
        "el plan no tiene dependencias: el usuario lo declara con su fuente (S2-R4)",
        "el plan no tiene dependencias: el usuario lo declara con su fuente (S2-R4)",
    ),
    (
        "LOTTT G.O. 6.076 Ext. 07-05-2012 (docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt)",
        "LOTTT G.O. 6.076 Ext. 07-05-2012 (docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt)",
    ),
    (
        "no existe punto de equilibrio: el margen de contribucion no es positivo",
        "no existe punto de equilibrio: el margen de contribución no es positivo",
    ),
    (
        "el punto de equilibrio no se alcanza dentro del contrato",
        "el punto de equilibrio no se alcanza dentro del contrato",
    ),
    ("el presupuesto no tiene ventas: no aplica", "el presupuesto no tiene ventas: no aplica"),
    ("se alcanza en {periodo}", "se alcanza en {periodo}"),
    (
        "sin curva de inversion: el punto de equilibrio no se ubica en el plan",
        "sin curva de inversión: el punto de equilibrio no se ubica en el plan",
    ),
)


#: Más largo que esto no es una frase del núcleo (la más larga mide ~200 caracteres): el catálogo
#: de regex lo devuelve intacto sin tocarlas, para que un texto hostil no cueste tiempo. El
#: desglose «no aplica (...)» no usa esas regex y no lleva tope.
LARGO_MAXIMO_A_CORREGIR = 2_000

#: Un hueco acotado: su expresión y, si lo que calza se presenta de otra forma (una fecha del
#: sistema en dd/mm/aaaa), la función que lo presenta.
Hueco = str | tuple[str, Callable[[str], str]]

#: Huecos con forma conocida: las cifras que el núcleo imprime. Acotarlos por clase hace lineal la
#: coincidencia (un `.+` voraz encadenado sería cúbico). Todo hueco no listado es texto del usuario
#: y cada plantilla tiene a lo sumo uno, de modo que tampoco encadena.
_HUECOS_NUMERICOS: dict[str, Hueco] = {
    "termino": r"\d+",
    "retraso": r"\d+",
    "plan": r"\d+",
    "spi": r"[-+0-9.,E]+",
    "cpi": r"[-+0-9.,E]+",
    "precio": r"[-+0-9.,E]+",
    "ev": r"[-+0-9.,E]+",
    "puntos": r"[-+0-9.,E]+",
}

#: Los motivos por partida del desglose «no aplica (cod: motivo; ...)» de `recuperacion.py`.
_MOTIVOS_POR_PARTIDA = {
    "sin composicion de APU": "sin composición de APU",
    "sin rendimiento": "sin rendimiento",
    "sin mano de obra a jornal": "sin mano de obra a jornal",
}


def _expresion(hueco: Hueco) -> str:
    return hueco if isinstance(hueco, str) else hueco[0]


def _compilar(crudo: str, huecos: Mapping[str, Hueco] = _HUECOS_NUMERICOS) -> re.Pattern[str]:
    """La frase del núcleo como expresión: el texto fijo literal, cada hueco `{x}` un dato."""
    partes = re.split(r"\{(\w+)\}", crudo)
    libres = [h for h in partes[1::2] if h not in huecos]
    if len(libres) > 1:
        raise ValueError(f"la plantilla {crudo!r} encadena huecos de texto libre")
    patron = "".join(
        f"(?P<{p}>{_expresion(huecos[p]) if p in huecos else '.+'})" if i % 2 else re.escape(p)
        for i, p in enumerate(partes)
    )
    return re.compile(patron, re.DOTALL)


def catalogo_de_frases(
    plantillas: Sequence[tuple[str, str]],
    huecos: Mapping[str, Hueco] = _HUECOS_NUMERICOS,
    *,
    largo_maximo: int = LARGO_MAXIMO_A_CORREGIR,
) -> Callable[[str], str]:
    """El corrector de un catálogo de frases fijas del núcleo (T8b; lo usa también Reajuste).

    Devuelve una función pura que, si el texto COMPLETO calza con una plantilla, lo reescribe con su
    versión con tildes; si no, lo devuelve igual. Lo que calza en un hueco libre (texto del usuario)
    vuelve tal cual; un hueco acotado con función (una fecha) se presenta con ella. Más largo que
    `largo_maximo` vuelve intacto sin probar ninguna expresión. Cada plantilla lleva a lo sumo un
    hueco libre (`_compilar` lo exige), así que el costo es lineal en el largo.
    """
    compilado = tuple((_compilar(crudo, huecos), con_tilde) for crudo, con_tilde in plantillas)
    presentar = {nombre: h[1] for nombre, h in huecos.items() if not isinstance(h, str)}

    def corregir(texto: str) -> str:
        if len(texto) > largo_maximo:
            return texto
        for patron, con_tilde in compilado:
            calce = patron.fullmatch(texto)
            if calce is not None:
                return con_tilde.format(
                    **{
                        nombre: presentar[nombre](valor) if nombre in presentar else valor
                        for nombre, valor in calce.groupdict().items()
                    }
                )
        return texto

    return corregir


_NO_APLICA = re.compile(r"no aplica \((?P<lista>.+)\)", re.DOTALL)
_CORREGIR_FRASE = catalogo_de_frases(PLANTILLAS_DEL_NUCLEO)


def con_tildes(texto: str) -> str:
    """Restituye las tildes de una frase fija del núcleo; cualquier otro texto pasa sin cambios.

    Función pura, sin recursión y de costo lineal. Solo actúa si la frase COMPLETA coincide con una
    plantilla del catálogo, de modo que un nombre de partida con «dia» o «ningun» puesto por el
    usuario no se altera.

    Límite conocido: el núcleo arma el desglose con `"; ".join(f"{c}: {m}" ...)` (recuperacion.py,
    intocable), así que un código de partida que contenga «; » y «: » es ambiguo con dos items y
    solo se corrige lo que calce con un motivo del conjunto cerrado. El tope de largo vale solo
    para el catálogo de regex; el desglose es lineal (split, rpartition, dict) y no lo necesita.
    """
    desglose = _NO_APLICA.fullmatch(texto)
    if desglose is not None:
        # «no aplica (cod: motivo; cod: motivo)»: el código es del usuario; solo el motivo, a la
        # derecha del último «: », se busca en el conjunto cerrado del núcleo.
        items = []
        for item in desglose.group("lista").split("; "):
            codigo, separador, motivo = item.rpartition(": ")
            corregido = _MOTIVOS_POR_PARTIDA.get(motivo)
            items.append(f"{codigo}{separador}{corregido}" if separador and corregido else item)
        return "no aplica (" + "; ".join(items) + ")"
    return _CORREGIR_FRASE(texto)


def alertas_en_filas(resultado: ResultadoControl) -> list[dict[str, str]]:
    """Las alertas que saltaron y, aparte, las que no se pudieron evaluar con su motivo."""
    filas = [
        {
            "Alerta": a.codigo,
            "Severidad": a.severidad.name,
            "Descripcion": con_tildes(a.descripcion),
            "Observado": ""
            if a.valor_observado is None
            else formatear_decimal(a.valor_observado, 4),
            "Umbral": ("" if a.umbral is None else formatear_decimal(a.umbral, 4))
            + f" ({a.naturaleza_umbral})",
        }
        for a in resultado.alertas.alertas
    ]
    filas.extend(
        {
            "Alerta": codigo,
            "Severidad": "sin evaluar",
            "Descripcion": con_tildes(motivo),
            "Observado": "",
            "Umbral": "",
        }
        for codigo, motivo in resultado.alertas.no_evaluadas.items()
    )
    return filas


def filas_de_reproyeccion(resultado: ResultadoControl) -> list[dict[str, str]]:
    """Por partida con obra pendiente: su índice, el día hábil en que termina y su nota."""
    filas = []
    for p in resultado.reproyeccion.partidas:
        if p.pendiente == 0:
            continue
        nota = con_tildes(p.motivo) or (
            "detenida"
            if p.detenida
            else "sin evidencia propia: SPI global"
            if p.sin_evidencia
            else ""
        )
        filas.append(
            {
                "Partida": p.codigo,
                "Indice": _indice(p.indice),
                "Fin (dia habil)": NO_DISPONIBLE if p.fin is None else formatear_decimal(p.fin, 2),
                "Nota": nota,
            }
        )
    return filas


def supuestos_de_opcion(opcion: Opcion) -> list[dict[str, str]]:
    """Los supuestos de una opción que aplica, cada uno en sus tres ranuras (nombre y valor con
    tilde, naturaleza tal cual): así el front los presenta por separado sin reescribir un texto
    armado que trae códigos del usuario (VD-1). La que no aplica no lista supuestos."""
    if not opcion.aplica:
        return []
    return [
        {"nombre": con_tildes(s.nombre), "valor": con_tildes(s.valor), "naturaleza": s.naturaleza}
        for s in opcion.supuestos
    ]


def filas_de_opciones(todas: Sequence[Opcion]) -> list[dict[str, str]]:
    """Una fila por opción con su término, sus costos, su punto de equilibrio y sus supuestos."""
    filas = []
    for o in todas:
        if not o.aplica:
            filas.append(
                {"Opcion": con_tildes(o.titulo), "Nota": con_tildes(o.motivo)}
                | dict.fromkeys(COLUMNAS_OPCIONES[1:-1], NO_APLICA)
            )
            continue
        pe = NO_APLICA
        if o.equilibrio is not None:
            pe = _monto(o.equilibrio.punto) + f" ({con_tildes(o.equilibrio.mensaje)})"
        filas.append(
            {
                "Opcion": con_tildes(o.titulo),
                "Termino": f"día {o.termino}",
                "Retraso (dias)": str(o.retraso),
                "Costo directo adicional": _monto(o.costo_directo_adicional),
                "Costo indirecto": _monto(o.costo_indirecto),
                "Penalizacion": _monto(o.penalizacion),
                "Punto de equilibrio": pe,
                "Nota": "; ".join(
                    f"{s['nombre']}: {s['valor']} ({s['naturaleza']})"
                    for s in supuestos_de_opcion(o)
                ),
            }
        )
    return filas


def filas_de_decisiones(sesion: Session, proyecto: str) -> list[dict[str, str]]:
    """Las decisiones de recuperación del proyecto."""
    return [
        {
            "Version": d.version,
            "Opcion": d.opcion,
            "Corte": f"{d.fecha_corte:%d/%m/%Y}",
            "Termino": f"{d.termino:%d/%m/%Y}",
            "Fuente": d.fuente,
            "Responsable": d.responsable,
        }
        for d in decisiones(sesion, proyecto)
    ]


def tablas_de_control(
    sesion: Session,
    proyecto: str,
    catalogo: Catalogo,
    *,
    precios: PreciosDelCorte | None = None,
) -> list[TablaExportable]:
    """Las hojas «Valuaciones», «Valor ganado» y «Decisiones» del Excel de la hoja (`hojas_extra`,
    SF-E4). Sin línea base de control (o sin valuaciones) no agrega ninguna: el Excel de la hoja
    conserva sus hojas y sale igual que antes."""
    try:
        resultado = calcular_control(sesion, proyecto, catalogo=catalogo, precios=precios)
    except (ValueError, LineaBaseInvalidada):
        return []
    anuladas = [
        v
        for v in valuaciones_registradas(sesion, proyecto, con_anuladas=True)
        if v.id not in {x.id for x in resultado.instantanea.valuaciones}
    ]
    valuaciones = tabla_valuaciones(
        resultado.instantanea.valuaciones,
        anuladas=anuladas,
        estados=estado_de_valuaciones(resultado),
    )
    filas = filas_de_indicadores(sesion, resultado) + alertas_en_filas(resultado)
    columnas = ("Indicador", "Valor", "En la otra moneda", "Nota")
    valor_ganado = TablaExportable(
        "Valor ganado",
        columnas,
        tuple(
            (
                f.get("Indicador") or f"{f['Alerta']} ({f['Severidad']})",
                f.get("Valor") or f.get("Observado", ""),
                f.get("En la otra moneda", ""),
                f.get("Nota") or f.get("Descripcion", ""),
            )
            for f in filas
        ),
    )
    decisiones_tabla = TablaExportable(
        "Decisiones",
        COLUMNAS_DECISIONES,
        tuple(
            tuple(f[c] for c in COLUMNAS_DECISIONES) for f in filas_de_decisiones(sesion, proyecto)
        ),
    )
    return [valuaciones, valor_ganado, decisiones_tabla]


# ---------------------------------------------------------------------------------------------
# Parámetros de control y la curva PV/EV/AC
# ---------------------------------------------------------------------------------------------

#: (campo, qué es, naturaleza): lo que la pestaña «Línea base» muestra de `ParametrosControl`.
PARAMETROS_EDITABLES = (
    ("spi_error", "SPI por debajo del cual el retraso es ERROR (AL-1)", NATURALEZA_SUPUESTO),
    ("cpi_error", "CPI por debajo del cual el sobrecosto es ERROR (AL-2)", NATURALEZA_SUPUESTO),
    (
        "retraso_error",
        "Retraso del término, fracción de D, que pasa a ERROR (AL-3)",
        NATURALEZA_SUPUESTO,
    ),
    ("precio_info", "Desvío de precio, fracción del EV, que avisa (AL-5)", NATURALEZA_SUPUESTO),
    (
        "equilibrio_puntos",
        "Puntos porcentuales de subida del PE que advierten (AL-4)",
        NATURALEZA_SUPUESTO,
    ),
    ("eta_cuadrilla", "Eficiencia de cada cuadrilla adicional (eta)", NATURALEZA_SUPUESTO),
    ("cuadrillas_max", "Cuadrillas máximas por frente", NATURALEZA_SUPUESTO),
    ("eta_horas_extra", "Eficiencia de la hora extra (eta_he)", NATURALEZA_SUPUESTO),
    ("horas_extra_dia", "Horas extra por día (tope legal 2)", NATURALEZA_SUPUESTO),
    ("recargo_horas_extra", "Recargo de las horas extra (mínimo legal 0,50)", NATURALEZA_SUPUESTO),
    ("fcas_en_horas_extra", "FCAS sobre las horas extra (sí o no)", NATURALEZA_SUPUESTO),
    ("penalizacion_diaria", "Penalización por día de retraso del contrato", NATURALEZA_DATO),
    ("fuente_penalizacion", "Fuente de la penalización", NATURALEZA_DATO),
)
COLUMNAS_PARAMETROS = ("Parametro", "Que es", "Valor", "Naturaleza")


def filas_de_parametros(parametros: ParametrosControl) -> list[dict[str, str]]:
    """Los parámetros de control como filas de la pantalla; la columna `Valor` es la editable."""
    filas = []
    for campo, que_es, naturaleza in PARAMETROS_EDITABLES:
        valor = getattr(parametros, campo)
        texto = (
            ("sí" if valor else "no")
            if isinstance(valor, bool)
            else format(valor, "f")
            if (isinstance(valor, Decimal))
            else str(valor)
        )
        filas.append(
            {"Parametro": campo, "Que es": que_es, "Valor": texto, "Naturaleza": naturaleza}
        )
    return filas


def parametros_desde_filas(filas: Sequence[Mapping[str, object]]) -> ParametrosControl:
    """Los `ParametrosControl` que describen las filas editadas. `ControlInvalido` si un valor
    no se lee o está fuera de rango (por ejemplo, `eta` fuera de (0, 1])."""
    valores = {str(f.get("Parametro")): str(f.get("Valor") or "").strip() for f in filas}
    muestra = ParametrosControl()
    leidos: dict[str, object] = {}
    for campo, _, _ in PARAMETROS_EDITABLES:
        if campo not in valores:
            raise ControlInvalido(f"falta el parametro {campo}")
        base = getattr(muestra, campo)
        texto = valores[campo]
        if isinstance(base, bool):
            if texto.casefold() not in ("si", "sí", "no"):
                raise ControlInvalido(f"{campo}: escriba sí o no")
            leidos[campo] = texto.casefold() != "no"
        elif isinstance(base, int):
            numero = _decimal(texto, campo)
            if numero != numero.to_integral_value():
                raise ControlInvalido(f"{campo}: {texto!r} debe ser un entero")
            leidos[campo] = int(numero)
        elif isinstance(base, Decimal):
            leidos[campo] = _decimal(texto, campo)
        else:
            leidos[campo] = texto
    try:
        return ParametrosControl(**leidos)
    except ValueError as error:
        raise ControlInvalido(str(error)) from None


def guardar_los_parametros(
    sesion: Session,
    proyecto: str,
    filas: Sequence[Mapping[str, object]],
    *,
    fuente: str,
    responsable: str,
) -> int:
    """Guarda los parámetros editados con un `RegistroCambio` por valor que cambió; devuelve
    cuántos cambiaron."""
    nuevos = parametros_desde_filas(filas)
    return len(
        _escribir(
            sesion,
            lambda: guardar_parametros(
                sesion, proyecto, nuevos, fuente=fuente, responsable=responsable
            ),
        )
    )


def curva_pv_ev_ac(sesion: Session, resultado: ResultadoControl) -> list[dict[str, object]]:
    """PV, EV y AC al cierre de cada período hasta el corte (el último punto es el corte mismo),
    para la curva de la pestaña «Valor ganado». El AC es `None` donde algún costo no tiene tasa."""
    instantanea = resultado.instantanea
    calendario = instantanea.calendario
    feriados = frozenset(calendario.feriados)
    largo = calendario.dias_por_periodo
    etiquetas = resultado.estado.etiquetas
    hasta = -(-resultado.estado.dia // largo)
    puntos: list[dict[str, object]] = []
    for n in range(1, hasta + 1):
        cierre = dia_habil(calendario.fecha_inicio, n * largo, feriados)
        parcial = replace(instantanea, corte=min(cierre, instantanea.corte))
        costo, _ = costo_real_al_corte(sesion, parcial)
        estado = construir_estado(parcial, costo_real=costo, precios=resultado.estado.precios)
        calculados = indicadores(estado)
        puntos.append(
            {
                "Periodo": etiquetas[n - 1] if n <= len(etiquetas) else f"Periodo {n}",
                "PV": calculados.pv,
                "EV": calculados.ev,
                "AC": calculados.ac,
            }
        )
    return puntos


# ---------------------------------------------------------------------------------------------
# Consultas cortas para la pantalla
# ---------------------------------------------------------------------------------------------


def texto_monto(valor: Decimal | None) -> str:
    """Un monto a dos decimales para mostrar; `None` es «no disponible»."""
    return _monto(valor)


def tiene_linea_base(sesion: Session, proyecto: str) -> bool:
    """True si el proyecto tiene alguna línea base de control declarada."""
    return linea_base_vigente(sesion, proyecto, date.max) is not None


def describir_linea_base(sesion: Session, proyecto: str) -> str | None:
    """La línea base vigente hoy en una frase (versión, perspectiva, calendario), o `None`.
    La fuente es texto ajeno: la pantalla la escapa con `ui.texto_seguro`."""
    fila = linea_base_vigente(sesion, proyecto, date.max)
    if fila is None:
        return None
    version = sesion.get(models.Presupuesto, fila.presupuesto_id)
    calendario = fila.calendario
    return (
        f"versión {version.codigo}, perspectiva {fila.perspectiva}, vigente desde "
        f"{fila.desde:%d/%m/%Y}; inicio de obra {calendario.fecha_inicio:%d/%m/%Y} con "
        f"{calendario.dias_por_periodo} día(s) hábil(es) por período"
    )


def hay_valuaciones(sesion: Session, proyecto: str) -> bool:
    """True si el proyecto tiene alguna valuación registrada (anulada o no)."""
    return bool(valuaciones_registradas(sesion, proyecto, con_anuladas=True))


def corte_por_defecto(sesion: Session, proyecto: str) -> date:
    """El *hasta* de la última valuación no anulada; hoy si no hay ninguna."""
    return max((v.hasta for v in valuaciones_registradas(sesion, proyecto)), default=date.today())


def valuaciones_para_anular(sesion: Session, proyecto: str) -> list[tuple[int, str]]:
    """`(id, rótulo)` de las valuaciones que cuentan y se pueden anular."""
    return [
        (v.id, f"{v.numero or '#' + str(v.id)} ({v.desde:%d/%m/%Y} a {v.hasta:%d/%m/%Y})")
        for v in valuaciones_registradas(sesion, proyecto)
    ]


def parametros_actuales(sesion: Session, proyecto: str) -> ParametrosControl:
    """Los parámetros de control del proyecto (los por defecto si no tiene fila)."""
    return parametros_de_control(sesion, proyecto)


def dia_con_fecha(resultado: ResultadoControl, dia: int | None) -> str:
    """«día N (dd/mm/aaaa)» en el calendario de la línea base; «no proyectable» si no hay día."""
    if dia is None:
        return "no proyectable"
    calendario = resultado.instantanea.calendario
    fecha = dia_habil(calendario.fecha_inicio, dia, frozenset(calendario.feriados))
    return f"día {dia} ({fecha:%d/%m/%Y})"


def filas_del_plan_reproyectado(
    resultado: ResultadoControl,
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    """Las columnas (período y una por partida) y las filas del plan reproyectado."""
    codigos = [p.codigo for p in resultado.estado.partidas]
    filas = []
    for etiqueta, reparto in resultado.reproyeccion.plan:
        fila = {"Periodo": etiqueta, **dict.fromkeys(codigos, "")}
        fila.update({codigo: format(fraccion, ".4f") for codigo, fraccion in reparto})
        filas.append(fila)
    return ("Periodo", *codigos), filas


def estudios_que_suma(resultado: ResultadoControl) -> str:
    """Una frase con los estudios de reajuste de S1 que suma V' (S2-R15), o que no suma ninguno."""
    reajuste = resultado.reajuste
    if not reajuste.estudios:
        return "Sin estudio de reajuste guardado: V' = V. Nunca se proyecta un reajuste."
    detalle = ", ".join(
        f"#{e.id} ({e.fecha_calculo:%d/%m/%Y}, {_monto(e.monto)})" for e in reajuste.estudios
    )
    return (
        f"V' suma el reajuste reconocido de {len(reajuste.estudios)} estudio(s) de reajuste "
        f"guardado(s): "
        f"{detalle}; total {_monto(reajuste.monto)} {reajuste.moneda}."
    )
