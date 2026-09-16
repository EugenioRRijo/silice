"""Genera `docs/resultados_ml.md`: compuerta G2 y metricas del modulo predictivo (RF-28).

Sesiones I6.3 (conteo civil y metricas de la linea base) y M4.1 (recuento multidominio y
metricas por dominio).

Todo corre sobre bases **en memoria** sembradas al vuelo: el informe es reproducible con
`uv run python scripts/generar_resultados_ml.py`, sin depender de `data/*.db` ni de estado previo.

Tres acopios, cada uno en su propia base (asi ninguna lista de precios de un dominio contamina la
"lista vigente" de otro):

1. **Conteo G2 multidominio** (`conteo_multidominio`): se siembran los cuatro catalogos (civil,
   telecom, industrial y sistemas, con los seeds de cada dominio) y se cuentan las partidas por
   dominio. La tecnica la dicta `ml.prediction.tecnica_para` (la tabla de CLAUDE.md §8.1 hecha
   codigo).
2. **Evaluacion civil** (`evaluar_sobre_linea_base`): el caso UC-02 verificado por las pruebas de
   integracion: presupuesto 001 -> lista de muestra del 01/06/2026 -> presupuesto 002; los PU del
   motor de costos (funcion pura, la verdad de terreno) se comparan contra la prediccion del
   sistema de reglas de `ml.prediction` y las tres metricas obligatorias salen de ahi.
3. **Evaluacion telecom** (`evaluar_sobre_telecom`, Sesion M4.1): el unico dominio ademas de civil
   con un historico **observado** de `CambioPrecio` (lista ARENAZA 18/05/2026 -> referencia MaPreX
   09/07/2026, Sesion M1.3). Los 40 PU de los dos presupuestos ARENAZA valorados con la lista
   ARENAZA son la base; valorados con la lista MaPreX son la verdad de terreno; la regla predice
   con las variaciones de ese historico. Industrial y sistemas no tienen historico (una sola lista
   publicada cada uno): se declaran **no evaluables**, no se inventa uno.

La seccion de texto (`generar_informe`) es pura y la cubren `tests/unit/test_resultados_ml.py` y
`tests/unit/test_resultados_ml_multidominio.py`; este script solo acopia los datos y escribe el
archivo.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy.orm import Session  # noqa: E402

from core.budget import (  # noqa: E402
    actualizar_precios,
    elaborar,
    generar_presupuesto,
    guardar_presupuesto,
    plan_secuencial,
)
from core.catalog import (  # noqa: E402
    Catalogo,
    abrir_sesion,
    cambios_precio,
    crear_esquema,
    crear_lista_desde_archivo,
    crear_motor,
)
from core.catalog.precios import registrar_cambios  # noqa: E402
from core.contracts.dominio import Dominio  # noqa: E402
from core.contracts.verificacion import Hallazgo  # noqa: E402
from core.costing import calcular_apu  # noqa: E402
from core.models import ListaPrecios  # noqa: E402
from core.verification.informe import DECIMALES_PRESENTACION  # noqa: E402
from core.verification.texto import formatear_decimal  # noqa: E402
from ml.prediction import (  # noqa: E402
    UMBRAL_CASOS,
    Metricas,
    PrediccionPrecio,
    contrastar_aace,
    metricas,
    predecir_por_reglas,
    tecnica_para,
)
from scripts import seed_telecom as telecom  # noqa: E402
from scripts.derivar_listas_telecom import (  # noqa: E402
    FECHA_LISTA_MAPREX,
    RUTA_LISTA_ARENAZA,
    RUTA_LISTA_MAPREX,
)
from scripts.seed import NOMBRE_PROYECTO, sembrar  # noqa: E402
from scripts.seed_industrial import sembrar_industrial  # noqa: E402
from scripts.seed_sistemas import sembrar_sistemas  # noqa: E402
from tests.fixtures import apu_linea_base as linea_base  # noqa: E402
from tests.fixtures.computo_auditado import items_auditados  # noqa: E402

MUESTRA_PRECIOS = RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv"
RUTA_INFORME = RAIZ / "docs" / "resultados_ml.md"
FECHA_LISTA_NUEVA = date(2026, 6, 1)
_CIEN = Decimal(100)


@dataclass(frozen=True)
class EvaluacionDominio:
    """Lo que la regla produjo sobre el historico observado de un dominio (RF-28 y RF-29)."""

    dominio: str
    lista_base: str
    lista_nueva: str
    partidas: int
    cambios_de_precio: int
    metricas: Metricas
    predicciones: list[PrediccionPrecio]
    reales: dict[str, Decimal]
    hallazgos: list[Hallazgo]

    @property
    def partidas_con_cambio(self) -> list[PrediccionPrecio]:
        return [p for p in self.predicciones if self.reales[p.codigo_partida] != p.pu_base]


#: Por que un dominio no se evalua: se declara en el informe, no se omite.
SIN_HISTORICO = "sin historico de variaciones: una sola lista de precios publicada (M2.2 / M3.2)"


# ---------------------------------------------------------------------------------------------
# 1. Conteo G2
# ---------------------------------------------------------------------------------------------


def conteo_por_dominio(sesion: Session) -> dict[str, int]:
    """Registros de APU disponibles por dominio: partidas del catalogo (compuerta G2)."""
    catalogo = Catalogo(sesion)
    return {dominio.value: len(catalogo.partidas(dominio)) for dominio in Dominio}


def conteo_multidominio(sesion: Session) -> dict[str, int]:
    """Siembra los cuatro catalogos en `sesion` y cuenta sus partidas (Sesion M4.1)."""
    sembrar(sesion)
    telecom.sembrar_telecom(sesion)
    sembrar_industrial(sesion)
    sembrar_sistemas(sesion)
    return conteo_por_dominio(sesion)


# ---------------------------------------------------------------------------------------------
# 2. Evaluacion civil (I6.3)
# ---------------------------------------------------------------------------------------------


def evaluar_sobre_linea_base(
    sesion: Session,
) -> tuple[Metricas, list[PrediccionPrecio], list[Hallazgo]]:
    """Predice los PU del presupuesto 002 con la regla y los mide contra el motor de costos."""
    proyecto = sembrar(sesion)
    catalogo = Catalogo(sesion)
    items = items_auditados()
    codigos = [apu.codigo_partida for apu in linea_base.APUS_LINEA_BASE]
    composiciones = catalogo.composiciones(codigos, fecha=linea_base.FECHA_LINEA_BASE)
    argumentos = dict(
        codigo=linea_base.CODIGO_PRESUPUESTO,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
    )
    borrador = generar_presupuesto(
        items, composiciones, linea_base.PARAMETROS_LINEA_BASE, **argumentos
    )
    resultado = elaborar(
        items,
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        plan=plan_secuencial(borrador),
        **argumentos,
    )
    guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
        parametros=linea_base.PARAMETROS_LINEA_BASE,
    )

    resumen = crear_lista_desde_archivo(
        sesion,
        MUESTRA_PRECIOS,
        nombre="Lista de precios 01/06/2026",
        moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_LISTA_NUEVA,
        origen=MUESTRA_PRECIOS.name,
    )
    _, comparativo = actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        linea_base.CODIGO_PRESUPUESTO,
        resumen.lista,
        "002",
        plan=plan_secuencial(resultado.presupuesto),
    )

    pus_base = {
        fila.codigo_partida: fila.pu_anterior for fila in comparativo.tabla.itertuples(index=False)
    }
    reales = {
        fila.codigo_partida: fila.pu_nuevo for fila in comparativo.tabla.itertuples(index=False)
    }
    variaciones = [cambio.variacion for cambio in cambios_precio(sesion)]

    predicciones = predecir_por_reglas(pus_base, variaciones)
    estimados = {prediccion.codigo_partida: prediccion.pu_estimado for prediccion in predicciones}
    hallazgos = _hallazgos_aace(reales, estimados)
    return metricas(estimados=estimados, reales=reales), predicciones, hallazgos


# ---------------------------------------------------------------------------------------------
# 3. Evaluacion telecom (M4.1): el unico historico observado fuera de civil
# ---------------------------------------------------------------------------------------------


def evaluar_sobre_telecom(sesion: Session) -> EvaluacionDominio:
    """Los 40 PU ARENAZA con la lista ARENAZA (base) y con la lista MaPreX (verdad de terreno).

    Reproduce el flujo UC-02 de `tests/integration/test_auditoria_arenaza.py`: las dos listas
    canonicas de `data/telecom/fuentes/` se cargan en ese orden y `registrar_cambios` produce el
    historico (cinco `CambioPrecio`, Sesion M1.3). La regla predice cada PU con la media de esas
    variaciones y se mide contra el motor de costos con la lista nueva.
    """
    telecom.sembrar_telecom(sesion)
    catalogo = Catalogo(sesion)
    resumen_base = crear_lista_desde_archivo(
        sesion,
        RUTA_LISTA_ARENAZA,
        nombre="Precios ARENAZA",
        moneda=telecom.MONEDA,
        fecha_vigencia=telecom.FECHA_ARENAZA,
        origen=RUTA_LISTA_ARENAZA.name,
    )
    resumen_nueva = crear_lista_desde_archivo(
        sesion,
        RUTA_LISTA_MAPREX,
        nombre="Precios MaPreX 2026-07",
        moneda=telecom.MONEDA,
        fecha_vigencia=FECHA_LISTA_MAPREX,
        origen=RUTA_LISTA_MAPREX.name,
    )
    cambios = registrar_cambios(sesion, resumen_base.lista, resumen_nueva.lista)
    variaciones = [cambio.variacion for cambio in cambios]

    codigos = [
        codigo
        for numero in sorted(telecom.PRESUPUESTOS)
        for codigo in telecom.codigos_arenaza(numero)
    ]

    def precio_con(lista: ListaPrecios, codigo: str) -> Decimal:
        composicion = catalogo.composicion(codigo, fecha=telecom.FECHA_ARENAZA, lista=lista)
        return calcular_apu(composicion, telecom.PARAMETROS_ARENAZA).precio_unitario

    pus_base = {codigo: precio_con(resumen_base.lista, codigo) for codigo in codigos}
    reales = {codigo: precio_con(resumen_nueva.lista, codigo) for codigo in codigos}

    predicciones = predecir_por_reglas(pus_base, variaciones)
    estimados = {prediccion.codigo_partida: prediccion.pu_estimado for prediccion in predicciones}
    return EvaluacionDominio(
        dominio=Dominio.TELECOM.value,
        lista_base=f"{resumen_base.lista.nombre} ({resumen_base.lista.fecha_vigencia})",
        lista_nueva=f"{resumen_nueva.lista.nombre} ({resumen_nueva.lista.fecha_vigencia})",
        partidas=len(codigos),
        cambios_de_precio=len(cambios),
        metricas=metricas(estimados=estimados, reales=reales),
        predicciones=predicciones,
        reales=reales,
        hallazgos=_hallazgos_aace(reales, estimados),
    )


def _hallazgos_aace(
    reales: Mapping[str, Decimal], estimados: Mapping[str, Decimal]
) -> list[Hallazgo]:
    return [
        hallazgo
        for codigo in sorted(reales)
        if (hallazgo := contrastar_aace(codigo, reales[codigo], estimados[codigo])) is not None
    ]


# ---------------------------------------------------------------------------------------------
# El informe
# ---------------------------------------------------------------------------------------------


def _dos(valor: Decimal) -> str:
    return formatear_decimal(valor, DECIMALES_PRESENTACION)


def _cuatro(valor: Decimal) -> str:
    # R2 va con cuatro decimales: a dos, un 0.9974 se presentaria como "1.00", que enganna.
    return formatear_decimal(valor, 4)


def _r2(valor: Decimal | None) -> str:
    return "sin varianza en los reales" if valor is None else _cuatro(valor)


def generar_informe(
    conteos: dict[str, int],
    metricas: Metricas,
    predicciones: list[PrediccionPrecio],
    hallazgos: list[Hallazgo],
    por_dominio: Mapping[str, EvaluacionDominio | str] | None = None,
) -> str:
    """El texto de `docs/resultados_ml.md`. Puro: todo lo que presenta viene por parametro.

    `por_dominio` (Sesion M4.1) trae, por dominio distinto de civil, su `EvaluacionDominio` o el
    texto que explica por que no se evaluo. Sin el, el informe es el de la Sesion I6.3.
    """
    lineas = [
        "# Resultados del modulo predictivo (Sesion I6.3, RF-28; recuento multidominio M4.1)",
        "",
        "Generado por `scripts/generar_resultados_ml.py` sobre bases en memoria sembradas con los",
        "catalogos de los cuatro dominios; reproducible con",
        "`uv run python scripts/generar_resultados_ml.py`.",
        "",
        "## Compuerta G2: conteo de registros y tecnica (CLAUDE.md §8.1)",
        "",
        "| Dominio | Registros de APU | Tecnica que dicta la tabla |",
        "|---|---|---|",
    ]
    for dominio, registros in sorted(conteos.items()):
        lineas.append(f"| {dominio} | {registros} | {tecnica_para(registros).value} |")
    lineas += [
        "",
        f"Todos los dominios estan por debajo de los {UMBRAL_CASOS} registros: la tecnica de",
        "`ml/prediction/` es el **sistema de reglas con analisis de sensibilidad**, y se declara",
        "como **limitacion** del trabajo, no como logro: no hay datos suficientes para entrenar",
        "ni validar un modelo de aprendizaje (la tabla de degradacion existe exactamente para",
        "este caso). La compuerta G2 queda cruzada con esta evidencia; tras el sprint",
        "multidominio la limitacion esta demostrada con catalogos poblados en los cuatro dominios,",
        "no con ausencia de datos (compuerta GM4, PLAN_MULTIDOMINIO §2).",
        "",
        "## Regla declarada",
        "",
        "PU estimado = PU base x (1 + media de las variaciones del historico de cambios de",
        "precio). Sensibilidad: el rango recorre la variacion minima y la maxima observadas.",
        "La regla no conoce la composicion del APU: el motor de costos (`core.costing`) es la",
        "verdad de terreno contra la que se mide.",
        "",
        "## Metricas (RF-28) — dominio civil, caso UC-02 de la linea base",
        "",
        "| Metrica | Valor |",
        "|---|---|",
        f"| MAPE | {_dos(metricas.mape * _CIEN)} % |",
        f"| RMSE | {_dos(metricas.rmse)} USD |",
        f"| R2 | {_r2(metricas.r2)} |",
        "",
        "## Predicciones sobre el caso UC-02 de la linea base",
        "",
        "| Partida | PU base | PU estimado | Rango de sensibilidad |",
        "|---|---|---|---|",
    ]
    for prediccion in predicciones:
        lineas.append(
            f"| {prediccion.codigo_partida} | {_dos(prediccion.pu_base)} | "
            f"{_dos(prediccion.pu_estimado)} | "
            f"[{_dos(prediccion.pu_minimo)}, {_dos(prediccion.pu_maximo)}] |"
        )
    lineas += ["", "## Contraste AACE clase 3 (RF-29) — dominio civil", ""]
    lineas += _lineas_aace(hallazgos)
    if por_dominio is not None:
        lineas += _seccion_por_dominio(por_dominio)
    lineas.append("")
    return "\n".join(lineas)


def _lineas_aace(hallazgos: list[Hallazgo], maximo: int | None = None) -> list[str]:
    if not hallazgos:
        return [
            "Ningun precio construido se desvia del estimado fuera del rango declarado "
            "(-20 % / +30 %): sin hallazgos."
        ]
    lineas = [f"{len(hallazgos)} hallazgo(s) de severidad ADVERTENCIA:", ""]
    mostrados = hallazgos if maximo is None else hallazgos[:maximo]
    lineas += [f"- {hallazgo.descripcion}" for hallazgo in mostrados]
    if maximo is not None and len(hallazgos) > maximo:
        lineas.append(f"- … y {len(hallazgos) - maximo} mas.")
    return lineas


def _seccion_por_dominio(por_dominio: Mapping[str, EvaluacionDominio | str]) -> list[str]:
    lineas = [
        "",
        "## Metricas por dominio (Sesion M4.1)",
        "",
        "Solo se evalua donde hay un historico observado de `CambioPrecio` entre dos listas de "
        "precios",
        "fechadas; donde no lo hay se declara, no se fabrica.",
        "",
        "| Dominio | Historico | Partidas | Cambios de precio | MAPE | RMSE | R2 | AACE |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for dominio, evaluacion in sorted(por_dominio.items()):
        if isinstance(evaluacion, str):
            lineas.append(f"| {dominio} | {evaluacion} | — | — | no evaluable | — | — | — |")
            continue
        lineas.append(
            f"| {dominio} | {evaluacion.lista_base} -> {evaluacion.lista_nueva} | "
            f"{evaluacion.partidas} | {evaluacion.cambios_de_precio} | "
            f"{_dos(evaluacion.metricas.mape * _CIEN)} % | {_dos(evaluacion.metricas.rmse)} USD | "
            f"{_r2(evaluacion.metricas.r2)} | {len(evaluacion.hallazgos)} hallazgo(s) |"
        )
    for dominio, evaluacion in sorted(por_dominio.items()):
        if isinstance(evaluacion, str):
            continue
        con_cambio = evaluacion.partidas_con_cambio
        lineas += [
            "",
            f"### {dominio}: partidas cuyo PU cambio con la lista nueva "
            f"({len(con_cambio)} de {evaluacion.partidas})",
            "",
            "| Partida | PU base | PU observado (lista nueva) | PU estimado | "
            "Rango de sensibilidad |",
            "|---|---|---|---|---|",
        ]
        for prediccion in con_cambio:
            lineas.append(
                f"| {prediccion.codigo_partida} | {_dos(prediccion.pu_base)} | "
                f"{_dos(evaluacion.reales[prediccion.codigo_partida])} | "
                f"{_dos(prediccion.pu_estimado)} | "
                f"[{_dos(prediccion.pu_minimo)}, {_dos(prediccion.pu_maximo)}] |"
            )
        sin_cambio = evaluacion.partidas - len(con_cambio)
        lineas += [
            "",
            f"Las otras {sin_cambio} partidas conservan su PU con la lista nueva, pero la regla",
            "(que no conoce la composicion) les aplica igualmente la variacion media del",
            f"historico: las metricas de arriba son sobre las {evaluacion.partidas} partidas y",
            "muestran exactamente esa limitacion.",
            "",
            f"Contraste AACE clase 3 (RF-29) — {dominio}:",
            "",
        ]
        lineas += _lineas_aace(evaluacion.hallazgos, maximo=5)
    return lineas


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------


def _en_base_nueva[T](funcion: Callable[[Session], T]) -> T:
    """Ejecuta `funcion(sesion)` sobre una base SQLite en memoria recien creada."""
    motor = crear_motor("sqlite://")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            return funcion(sesion)
    finally:
        motor.dispose()


def main() -> int:
    conteos = _en_base_nueva(conteo_multidominio)
    resultado_metricas, predicciones, hallazgos = _en_base_nueva(evaluar_sobre_linea_base)
    evaluacion_telecom = _en_base_nueva(evaluar_sobre_telecom)
    por_dominio: dict[str, EvaluacionDominio | str] = {
        Dominio.TELECOM.value: evaluacion_telecom,
        Dominio.INDUSTRIAL.value: SIN_HISTORICO,
        Dominio.SISTEMAS.value: SIN_HISTORICO,
    }
    informe = generar_informe(conteos, resultado_metricas, predicciones, hallazgos, por_dominio)

    RUTA_INFORME.write_text(informe, encoding="utf-8")
    print(f"Informe escrito en: {RUTA_INFORME}")
    print("Conteo G2: " + ", ".join(f"{d} {n}" for d, n in sorted(conteos.items())))
    print(
        f"civil   MAPE {resultado_metricas.mape * _CIEN:.2f} % | "
        f"RMSE {resultado_metricas.rmse:.2f} | R2 {_r2(resultado_metricas.r2)}"
    )
    m = evaluacion_telecom.metricas
    print(
        f"telecom MAPE {m.mape * _CIEN:.2f} % | RMSE {m.rmse:.2f} | R2 {_r2(m.r2)} | "
        f"{evaluacion_telecom.cambios_de_precio} cambios, "
        f"{len(evaluacion_telecom.hallazgos)} hallazgos AACE"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
