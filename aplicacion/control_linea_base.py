"""Línea base, valuaciones, anulación y costos del control de obra (UC-19).

Declarar la línea base desde los textos de la pantalla (con los días por período que propone
el plan), registrar una valuación y calcular al corte, anularla, anotar un costo incurrido y
leer o registrar un XLSX de valuaciones. Las partidas del contrato se quedan en la fachada:
leen `aplicacion.frentes`, que está en el ciclo de la mesa (ola 5).

Salió de `aplicacion/control.py` sin cambios (tarea 4.3 del plan de desenredo);
`aplicacion.control` lo reexporta.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.causas import causas_de_las_filas
from aplicacion.control_calculo import calcular_el_control
from aplicacion.control_comun import (
    ControlInvalido,
    _decimal,
    _escribir,
    _exigir_texto,
    _fecha,
)
from aplicacion.control_corte import exigir_que_no_sea_futura
from aplicacion.tablas_causas import guardar_causas
from core import models
from core.budget.control import ResultadoControl
from core.budget.instantanea import plan_de_version
from core.budget.valor_ganado import PreciosDelCorte
from core.budget.valuaciones import (
    Calendario,
    LecturaControl,
    anular_valuacion,
    leer_valuaciones_excel,
    registrar_costo,
    registrar_lectura,
    registrar_linea_base,
    registrar_valuacion,
)
from core.catalog import Catalogo
from core.verification.valuaciones import LineaValuacion


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


#: Lo que se responde a un respaldo en blanco, con el nombre del campo de la pantalla: el núcleo
#: diría «la fuente del cambio es obligatoria» también bajo «Motivo» (prueba en vivo 2026-11-18).
_SIN_FUENTE_DE_LINEA_BASE = (
    "La fuente de la línea base es obligatoria: diga de dónde sale (acta, contrato)."
)
_SIN_FUENTE_DE_VALUACION = (
    "La fuente de la valuación es obligatoria: diga de dónde sale (acta, oficio)."
)
_SIN_FUENTE_DE_COSTO = (
    "La fuente del costo es obligatoria: diga de dónde sale (factura, libro de obra)."
)
_SIN_FUENTE_DE_IMPORTACION = (
    "La fuente de la importación es obligatoria: diga de dónde sale el archivo."
)
_SIN_MOTIVO_DE_ANULACION = (
    "El motivo de la anulación es obligatorio: diga por qué se anula y con qué respaldo."
)

#: El informe previo del XLSX (`core/budget/valuaciones.py`, sin tildes) como lo lee la persona.
_INFORME = re.compile(r"(Valuaciones|Lineas|Costos): (\d+) (valuacion\(es\)|linea\(s\)|costo\(s\))")
_CONTADO = {"valuacion(es)": "valuación(es)", "linea(s)": "línea(s)", "costo(s)": "costo(s)"}


def _informe_con_tildes(linea: str) -> str:
    calce = _INFORME.fullmatch(linea)
    if calce is None:
        return linea
    hoja, cuantos, que = calce.groups()
    return f"Hoja «{hoja}»: {cuantos} {_CONTADO[que]}"


#: Días hábiles por período que se proponen si el plan no dice su unidad: un mes de cuatro semanas
#: de cinco días (ola 2 del 2026-11-13; los de `aplicacion.plan_rendimientos.DIAS_POR_MES`).
DIAS_POR_OMISION = 20
#: Los días hábiles de un período del plan por el nombre de su etiqueta («Dia n», «Semana n»,
#: «Mes n», las de `aplicacion.plan_rendimientos`; «Día» con tilde también).
_DIAS_DE_LA_UNIDAD = {"dia": 1, "semana": 5, "mes": 20}
_ETIQUETA = re.compile(r"^(d[ií]a|semana|mes) [0-9]+( \([0-9]+\))?$", re.IGNORECASE)
_PLAN_SIN_UNIDAD = (
    "El plan de la versión no dice su unidad (sus períodos no son «Dia n», «Semana n» ni "
    "«Mes n»): se proponen 20 días hábiles, un mes. Cámbielo si sus períodos duran otra cosa."
)
_SIN_PLAN = "La versión no tiene plan de trabajo: se proponen 20 días hábiles, un mes."


@dataclass(frozen=True, slots=True)
class DiasDelPlan:
    """Los días hábiles por período que se proponen para la línea base, la unidad del plan de la
    que salen («dia», «semana», «mes» o vacía si el plan no la dice) y el aviso de ese caso."""

    dias: int
    unidad: str
    aviso: str


def dias_de_las_etiquetas(etiquetas: Sequence[str]) -> DiasDelPlan:
    """Los días por período de un plan por sus etiquetas: todas de la misma unidad («Dia n» 1,
    «Semana n» 5, «Mes n» 20); si no, o sin plan, `DIAS_POR_OMISION` con su aviso.

    Control cuenta cada período del plan como `dias_por_periodo` días hábiles: con 5 fijos, un plan
    por días quedaba cinco veces más largo (ola 2 del 2026-11-13, simulación en la bitácora)."""
    if not etiquetas:
        return DiasDelPlan(DIAS_POR_OMISION, "", _SIN_PLAN)
    unidades = set()
    for etiqueta in etiquetas:
        encontrada = _ETIQUETA.match(etiqueta.strip())
        if encontrada is None:
            return DiasDelPlan(DIAS_POR_OMISION, "", _PLAN_SIN_UNIDAD)
        unidades.add(encontrada.group(1).lower().replace("í", "i"))
    if len(unidades) != 1:
        return DiasDelPlan(DIAS_POR_OMISION, "", _PLAN_SIN_UNIDAD)
    unidad = unidades.pop()
    return DiasDelPlan(_DIAS_DE_LA_UNIDAD[unidad], unidad, "")


def _version(sesion: Session, proyecto: str, version: str) -> models.Presupuesto:
    modelo = sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == version)
    ).one_or_none()
    if modelo is None:
        raise ControlInvalido(f"La obra no tiene la versión «{version}».")
    return modelo


def dias_por_periodo_del_plan(sesion: Session, proyecto: str, version: str) -> DiasDelPlan:
    """Los días por período que se proponen para declarar la línea base sobre `version`, desde su
    plan guardado (`dias_de_las_etiquetas`). `ControlInvalido` si la versión no existe."""
    plan = plan_de_version(sesion, _version(sesion, proyecto, version)) or []
    return dias_de_las_etiquetas([etiqueta for etiqueta, _ in plan])


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
    separados por comas o saltos de línea, en AAAA-MM-DD. Sin `dias_por_periodo` (en blanco), los
    del plan de la versión (`dias_por_periodo_del_plan`, RF-196)."""
    _exigir_texto(fuente, _SIN_FUENTE_DE_LINEA_BASE)
    if not dias_por_periodo.strip():
        dias_por_periodo = str(dias_por_periodo_del_plan(sesion, proyecto, version).dias)
    dias = _decimal(dias_por_periodo, "Días hábiles por período")
    if dias != dias.to_integral_value():
        raise ControlInvalido(
            f"«Días hábiles por período» debe ser un número entero: «{dias_por_periodo.strip()}»."
        )
    lista = [parte for parte in feriados.replace("\n", ",").split(",") if parte.strip()]

    def accion():
        return registrar_linea_base(
            sesion,
            proyecto,
            version,
            desde=_fecha(desde, "Vigente desde"),
            perspectiva=perspectiva,
            calendario=Calendario(
                _fecha(inicio, "Inicio de obra"),
                int(dias),
                tuple(_fecha(dia, "Feriados") for dia in lista),
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
            raise ControlInvalido(f"Línea {numero}: falta la partida.")
        medicion = str(fila.get("Fecha de medicion") or "").strip()
        cifra = _decimal(cantidad, f"Cantidad {numero}")
        dia = _fecha(medicion, f"Fecha de medición {numero}") if medicion else None
        try:
            lineas.append(
                LineaValuacion(partida, cifra, dia, str(fila.get("Observacion") or "").strip())
            )
        except ValueError as error:
            raise ControlInvalido(f"Línea {numero}: {error}") from None
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
    hoy: date | None = None,
) -> ResultadoControl:
    """UC-19 4 y 5: registra la valuación y calcula al corte (su fecha *hasta*) el informe de
    control, los indicadores, las alertas y la reproyección. Es lo que mide RNF-15.

    La causa de retraso de cada línea (clave «Causa» de la fila, MP-7) se guarda en la misma
    transacción que la valuación; una causa desconocida la rechaza entera. Una valuación que
    termina o se firma después de `hoy` (por defecto, el reloj) se rechaza sin guardar nada:
    mide obra ya ejecutada (`exigir_que_no_sea_futura`)."""
    _exigir_texto(fuente, _SIN_FUENTE_DE_VALUACION)
    inicio = _fecha(desde, "Período desde")
    fin = _fecha(hasta, "Período hasta")
    firmada = _fecha(fecha, "Fecha de la valuación") if fecha.strip() else None
    exigir_que_no_sea_futura(fin, firmada, hoy)
    lineas = lineas_desde_filas(filas)
    if not lineas:
        # el núcleo diría «una valuacion necesita al menos una linea», sin tildes
        raise ControlInvalido("Una valuación necesita al menos una línea medida.")

    def accion():
        causas = causas_de_las_filas(filas)
        valuacion = registrar_valuacion(
            sesion,
            proyecto,
            numero=numero,
            desde=inicio,
            hasta=fin,
            fecha=firmada,
            inspector=inspector,
            lineas=lineas,
            fuente=fuente,
            responsable=responsable,
        )
        guardar_causas(sesion, valuacion.id, causas, valuacion.fecha_hora)

    _escribir(sesion, accion)
    return calcular_el_control(sesion, proyecto, catalogo, corte=fin, precios=precios)


def anular(sesion: Session, valuacion_id: int, *, motivo: str, responsable: str) -> None:
    """Anula una valuación (UC-19 4c): se conserva y deja de contar."""
    _exigir_texto(motivo, _SIN_MOTIVO_DE_ANULACION)
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
    cifra = _decimal(monto, "Monto")
    dia = _fecha(fecha, "Fecha")
    _exigir_texto(fuente, _SIN_FUENTE_DE_COSTO)
    _escribir(
        sesion,
        lambda: registrar_costo(
            sesion,
            proyecto,
            monto=cifra,
            moneda=moneda,
            fecha=dia,
            fuente=fuente,
            responsable=responsable,
            codigo_partida=partida.strip() or None,
        ),
    )


def leer_excel(ruta: Path) -> LecturaControl:
    """Lee un XLSX de valuaciones sin escribir nada (informe previo). `ControlInvalido` si se
    rechaza: el archivo se rechaza entero."""
    try:
        lectura = leer_valuaciones_excel(ruta)
    except ValueError as error:
        raise ControlInvalido(str(error)) from None
    return replace(lectura, informe=tuple(map(_informe_con_tildes, lectura.informe)))


def importar_excel(
    sesion: Session,
    proyecto: str,
    lectura: LecturaControl,
    *,
    fuente: str,
    responsable: str,
    hoy: date | None = None,
) -> int:
    """Registra lo leído (todas las valuaciones y costos, o ninguno) y devuelve cuántas son. Una
    valuación del futuro (`exigir_que_no_sea_futura`) rechaza el archivo entero."""
    _exigir_texto(fuente, _SIN_FUENTE_DE_IMPORTACION)
    for valuacion in lectura.valuaciones:
        try:
            exigir_que_no_sea_futura(valuacion.hasta, valuacion.fecha, hoy)
        except ControlInvalido as error:
            raise ControlInvalido(
                f"Valuación {valuacion.numero}: {error} No se importó nada."
            ) from None
    registradas, _ = _escribir(
        sesion,
        lambda: registrar_lectura(
            sesion, proyecto, lectura, fuente=fuente, responsable=responsable
        ),
    )
    return len(registradas)
