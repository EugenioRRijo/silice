"""Parámetros de control (la pestaña «Línea base») y la curva PV/EV/AC del valor ganado.

Salió de `aplicacion/control.py` sin cambios (tarea 4.3 del plan de desenredo);
`aplicacion.control` lo reexporta.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from decimal import Decimal

from sqlalchemy.orm import Session

from aplicacion.control_comun import (
    NATURALEZA_DATO,
    NATURALEZA_SUPUESTO,
    ControlInvalido,
    _decimal,
    _escribir,
)
from core.budget.calendario import dia_habil
from core.budget.control import (
    ResultadoControl,
    construir_estado,
    costo_real_al_corte,
    guardar_parametros,
)
from core.budget.valor_ganado import (
    ParametrosControl,
    indicadores,
)

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
