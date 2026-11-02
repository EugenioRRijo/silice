"""UC-18 sin Streamlit: de los textos de la pantalla a la clausula y los periodos, el calculo en
memoria, la tabla lado a lado, el guardado y el Excel por `hojas_extra` (spec S1 §8). Vive en
`aplicacion/` (RM-1) para que la API y la pantalla `ui/paginas/reajuste.py` (que solo pinta) la
compartan; `ui/reajuste.py` la reexporta. Sin Streamlit, sin pandas y sin `ui.caso`. Las celdas se
leen con `aplicacion.composicion.texto_de_celda`.

`calcular` usa el mismo `guardar_estudio` que guarda y el recalculo de `cargar_estudio`, dentro de
una transaccion que se deshace entera al terminar: lo que se ve antes de guardar es exactamente lo
que se guardaria, y nada queda escrito. Por eso se llama con una sesion sin cambios pendientes (la
pantalla abre una por accion)."""

from __future__ import annotations

import tempfile
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from sqlalchemy import select

from aplicacion.composicion import ComposicionInvalida, decimal_desde_texto, texto_de_celda
from aplicacion.control import Hueco, catalogo_de_frases
from aplicacion.errores import HojaInvalida
from core import models
from core.budget import TablaExportable, cargar_elaboracion, exportar_hoja
from core.budget.puente import PeriodoDelEstudio, estudio_con_valuaciones, periodos_declarados
from core.budget.reajuste import (
    Clausula,
    Componente,
    Ejecutado,
    EstadoEstudio,
    Estructura,
    Mecanismo,
    PeriodoDeclarado,
    ResultadoEstudio,
    cargar_estudio,
    guardar_estudio,
)
from core.catalog import Catalogo
from core.contracts import ParametrosCosto
from core.verification.texto import formatear_decimal

COLUMNAS_REAJUSTE = (
    "Período",
    "Escalatoria",
    "Comprobación",
    "Diferencia",
    "Reconocido",
    "Mecanismo",
    "Moneda",
    "Escalatoria (otra)",
    "Comprobación (otra)",
    "Diferencia (otra)",
    "Tasa",
    "Marcas",
)
COLUMNAS_EJECUTADO = ("Período", "Partida", "Cantidad", "Fuente")
NO_DISPONIBLE = "no disponible"
FUENTE_DEL_CALCULO = "calculo en pantalla, sin guardar"
_SI = {"si", "sí", "true", "1"}
#: Como se llama cada campo en la pantalla: los mensajes usan estos nombres, no los internos.
ROTULOS = {
    "fecha_inicio": "Inicio del contrato",
    "duracion_meses": "Duración (meses)",
    "fecha_referencia_primer_anio": "El primer año corre desde",
    "periodicidad": "Periodicidad",
    "mecanismo": "Mecanismo",
    "mecanismo_pagadero": "Mecanismo pagadero",
    "fuente_pagadero": "Fuente del mecanismo pagadero",
    "estructura": "Estructura",
    "fecha_base_indices": "Mes base de los índices",
    "r": "R (fracción no reajustable)",
    "fuente_r": "Fuente de R",
    "fuente": "Fuente de la cláusula",
    "responsable": "Responsable",
    "componente": "Componente",
    "serie": "Serie del componente",
    "peso": "Peso del componente",
    "desde": "Período, desde",
    "hasta": "Período, hasta",
    "version_comprobacion": "Versión de comprobación",
    "periodo": "Número del período (ejecutado)",
    "partida": "Partida (ejecutado)",
    "cantidad": "Cantidad ejecutada",
}


def _fecha_del_sistema(iso: str) -> str:
    """«2027-01-15» -> «15/01/2027»; lo que no es una fecha real queda como vino."""
    try:
        return f"{date.fromisoformat(iso):%d/%m/%Y}"
    except ValueError:
        return iso


_FECHA_ISO: Hueco = (r"\d{4}-\d{2}-\d{2}", _fecha_del_sistema)
_FECHA_ES = r"\d{2}/\d{2}/\d{4}"

#: Los huecos acotados de los mensajes de Reajuste: fechas del sistema (las ISO se presentan en
#: dd/mm/aaaa), números de estudio e importación, la suma de los pesos y el código de una versión
#: sin espacios. Todo otro hueco (`codigo`, `series`, `partidas`, `serie`) es texto del usuario,
#: uno por plantilla, y sale tal cual.
HUECOS_DE_REAJUSTE: dict[str, Hueco] = {
    "desde": _FECHA_ISO,
    "hasta": _FECHA_ISO,
    "aniversario": _FECHA_ISO,
    "desde_es": _FECHA_ES,
    "hasta_es": _FECHA_ES,
    "fecha_es": _FECHA_ES,
    "estudio": r"\d+",
    "importacion": r"\d+",
    "suma": r"[-+0-9.E]+",
    "version": r"\S+",
}

#: (mensaje tal como lo emite `core/budget/reajuste.py`, el mismo con tildes). Solo tildes: los
#: códigos que traen (S1-R10, UC-18 3b, mecanismo_pagadero) son del núcleo y quedan (ver el
#: informe). La guardia `tests/unit/test_reajuste_tildes.py` falla si el núcleo emite un mensaje
#: que no está aquí.
PLANTILLAS_DE_REAJUSTE: tuple[tuple[str, str], ...] = (
    (
        "una partida con costo directo cero no tiene pesos por componente",
        "una partida con costo directo cero no tiene pesos por componente",
    ),
    ("el estudio necesita al menos un periodo", "el estudio necesita al menos un período"),
    ("los periodos van en orden y sin solaparse", "los períodos van en orden y sin solaparse"),
    (
        "las series {series} no estan importadas (UC-17)",
        "las series {series} no están importadas (UC-17)",
    ),
    (
        "la version de comprobacion {codigo} no existe en el proyecto (UC-18 4)",
        "la versión de comprobación {codigo} no existe en el proyecto (UC-18 4)",
    ),
    (
        "la version {version} no valora {partidas}: no sirve de comprobacion para ese periodo",
        "la versión {version} no valora {partidas}: no sirve de comprobación para ese período",
    ),
    (
        "el estudio {estudio} no es de la version {codigo}",
        "el estudio {estudio} no es de la versión {codigo}",
    ),
    (
        "el estudio {estudio} esta cerrado: solo un parcial se reemplaza",
        "el estudio {estudio} está cerrado: solo un parcial se reemplaza",
    ),
    (
        "un parcial se reemplaza una sola vez (S1-R21)",
        "un parcial se reemplaza una sola vez (S1-R21)",
    ),
    (
        "el estudio que reemplaza a un parcial debe estar cerrado (S1-R21)",
        "el estudio que reemplaza a un parcial debe estar cerrado (S1-R21)",
    ),
    (
        "el estudio exige fuente y responsable (UC-18 6)",
        "el estudio exige fuente y responsable (UC-18 6)",
    ),
    (
        "cada cantidad ejecutada exige su fuente: acta o valuacion (UC-18 2)",
        "cada cantidad ejecutada exige su fuente: acta o valuación (UC-18 2)",
    ),
    ("no hay ningun estudio de reajuste {estudio}", "no hay ningún estudio de reajuste {estudio}"),
    ("la duracion del contrato debe ser positiva", "la duración del contrato debe ser positiva"),
    (
        "el mes base de los indices se declara con su primer dia (S1-R10)",
        "el mes base de los índices se declara con su primer día (S1-R10)",
    ),
    ("R va en [0, 1) con su fuente (S1-R8)", "R va en [0, 1) con su fuente (S1-R8)"),
    ("la clausula exige fuente y responsable", "la cláusula exige fuente y responsable"),
    (
        "mecanismo_pagadero solo con 'ambos', uno de los dos y con su fuente",
        "mecanismo_pagadero solo con 'ambos', uno de los dos y con su fuente",
    ),
    ("componente repetido en la clausula", "componente repetido en la cláusula"),
    (
        "la cantidad ejecutada de {codigo} no puede ser negativa",
        "la cantidad ejecutada de {codigo} no puede ser negativa",
    ),
    (
        "el periodo {desde_es}-{hasta_es} del estudio {estudio} no recalcula igual a lo guardado "
        "(RNF-14)",
        "el período {desde_es}-{hasta_es} del estudio {estudio} no recalcula igual a lo guardado "
        "(RNF-14)",
    ),
    (
        "por_partida exige materiales, equipos y mano_obra con su serie",
        "por_partida exige materiales, equipos y mano_obra con su serie",
    ),
    (
        "la estructura declarada exige el peso de cada componente",
        "la estructura declarada exige el peso de cada componente",
    ),
    (
        "los pesos de la estructura declarada suman {suma}, no 1 (§8.1)",
        "los pesos de la estructura declarada suman {suma}, no 1 (§8.1)",
    ),
    (
        "la partida {codigo} no esta en la version del contrato",
        "la partida {codigo} no está en la versión del contrato",
    ),
    (
        "el periodo {desde}\u2013{hasta} cruza el aniversario {aniversario}: partalo (UC-18 3b)",
        "el período {desde}\u2013{hasta} cruza el aniversario {aniversario}: pártalo (UC-18 3b)",
    ),
    (
        "el estudio {estudio} cita la importacion {importacion} de {serie} al {fecha_es}, que ya "
        "no esta en la base",
        "el estudio {estudio} cita la importación {importacion} de {serie} al {fecha_es}, que ya "
        "no está en la base",
    ),
)

#: Restituye las tildes de un mensaje del núcleo de reajuste; otro texto pasa sin cambios.
con_tildes_de_reajuste = catalogo_de_frases(PLANTILLAS_DE_REAJUSTE, HUECOS_DE_REAJUSTE)


def _rotulo(campo: str) -> str:
    return ROTULOS.get(campo, campo)


# --- textos -> clausula y periodos ---------------------------------------------------------------


def _campo(
    fila: Mapping[str, object], campo: str, *, obligatorio: bool = True, rotulo: str | None = None
) -> str:
    texto = texto_de_celda(fila, campo)
    if obligatorio and not texto:
        raise HojaInvalida(f"Escriba «{rotulo or _rotulo(campo)}»: es obligatorio.")
    return texto


def _fecha(texto: str, campo: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise HojaInvalida(f"{_rotulo(campo)}: {texto!r} no es una fecha AAAA-MM-DD.") from None


def _decimal(texto: str, campo: str) -> Decimal:
    try:
        return decimal_desde_texto(texto, campo)
    except ComposicionInvalida as error:
        raise HojaInvalida(str(error)) from None


def _opcion[E: StrEnum](tipo: type[E], texto: str, campo: str) -> E:
    try:
        return tipo(texto)
    except ValueError:
        opciones = ", ".join(m.value for m in tipo)
        raise HojaInvalida(f"{_rotulo(campo)}: {texto!r}; se espera uno de {opciones}.") from None


def _con_datos(fila: Mapping[str, object]) -> bool:
    return any(texto_de_celda(fila, clave) for clave in fila)


def clausula_desde_textos(
    campos: Mapping[str, str], componentes: Sequence[Mapping[str, str]]
) -> Clausula:
    """La clausula de S1 §8.1 desde el formulario y la tabla de componentes (filas en blanco se
    ignoran). `HojaInvalida` con el campo culpable, o con la regla de la clausula que no cumple."""
    try:
        duracion = int(_campo(campos, "duracion_meses"))
    except ValueError:
        raise HojaInvalida("Duración (meses): escriba un número entero de meses.") from None
    lista = []
    for fila in (f for f in componentes if _con_datos(f)):
        componente = _campo(fila, "componente")
        peso = _campo(fila, "peso", obligatorio=False)
        lista.append(
            Componente(
                componente,
                _campo(fila, "serie"),
                _decimal(peso, f"peso de {componente}") if peso else None,
            )
        )
    pagadero = _campo(campos, "mecanismo_pagadero", obligatorio=False)
    try:
        return Clausula(
            _fecha(_campo(campos, "fecha_inicio"), "fecha_inicio"),
            duracion,
            _fecha(_campo(campos, "fecha_referencia_primer_anio"), "fecha_referencia_primer_anio"),
            _campo(campos, "periodicidad"),
            _opcion(Mecanismo, _campo(campos, "mecanismo"), "mecanismo"),
            _opcion(Estructura, _campo(campos, "estructura"), "estructura"),
            tuple(lista),
            _fecha(_campo(campos, "fecha_base_indices"), "fecha_base_indices"),
            _decimal(_campo(campos, "r"), _rotulo("r")),
            _campo(campos, "fuente_r"),
            _campo(campos, "fuente"),
            _campo(campos, "responsable"),
            mecanismo_pagadero=(
                _opcion(Mecanismo, pagadero, "mecanismo_pagadero") if pagadero else None
            ),
            fuente_pagadero=_campo(campos, "fuente_pagadero", obligatorio=False),
            r_en_comprobacion=(
                _campo(campos, "r_en_comprobacion", obligatorio=False).casefold() in _SI
            ),
        )
    except HojaInvalida:
        raise
    except ValueError as error:  # las reglas de la clausula (pesos que no suman 1, R, ...)
        raise HojaInvalida(
            f"La cláusula no es válida: {con_tildes_de_reajuste(str(error))}"
        ) from None


def periodos_desde_filas(
    periodos: Sequence[Mapping[str, str]], ejecutado: Sequence[Mapping[str, str]]
) -> list[PeriodoDeclarado]:
    """Los periodos (desde, hasta, version de comprobacion, excepcion) y lo ejecutado de cada uno
    (`periodo` es el numero del periodo, desde 1; la fuente es obligatoria por fila, UC-18 2)."""
    filas = [f for f in periodos if _con_datos(f)]
    por_periodo: dict[int, list[Ejecutado]] = {n: [] for n in range(1, len(filas) + 1)}
    for fila in (f for f in ejecutado if _con_datos(f)):
        try:
            numero = int(_campo(fila, "periodo"))
        except ValueError:
            raise HojaInvalida(
                "Número del período (ejecutado): escriba 1, 2, ... según la fila de períodos."
            ) from None
        if numero not in por_periodo:
            raise HojaInvalida(f"Período {numero}: no hay un período con ese número en la tabla.")
        partida = _campo(fila, "partida")
        por_periodo[numero].append(
            Ejecutado(
                partida,
                _decimal(_campo(fila, "cantidad"), f"cantidad de {partida}"),
                _campo(fila, "fuente", rotulo="Fuente de lo ejecutado"),
            )
        )
    return [
        PeriodoDeclarado(
            _fecha(_campo(fila, "desde"), "desde"),
            _fecha(_campo(fila, "hasta"), "hasta"),
            tuple(por_periodo[n]),
            _campo(fila, "version_comprobacion", obligatorio=False),
            _campo(fila, "excepcion", obligatorio=False),
        )
        for n, fila in enumerate(filas, start=1)
    ]


# --- calcular, guardar y presentar ------------------------------------------------------------


def _version(sesion, proyecto: str, codigo: str) -> models.Presupuesto:
    version = sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
    ).one_or_none()
    if version is None:
        raise HojaInvalida(f"El proyecto {proyecto!r} no tiene una versión {codigo!r}.")
    return version


def calcular(
    sesion,
    proyecto: str,
    codigo: str,
    clausula: Clausula,
    periodos: Sequence[PeriodoDeclarado],
    *,
    fecha_calculo: date,
) -> ResultadoEstudio:
    """UC-18 3-5 en memoria (ver el docstring del modulo): nada queda escrito."""
    try:
        estudio = guardar_estudio(
            sesion,
            _version(sesion, proyecto, codigo),
            clausula,
            periodos,
            fecha_calculo=fecha_calculo,
            fuente=FUENTE_DEL_CALCULO,
            responsable=clausula.responsable,
        )
        return cargar_estudio(sesion, estudio.id).resultado
    except HojaInvalida:
        raise
    except ValueError as error:
        raise HojaInvalida(f"No se pudo calcular: {con_tildes_de_reajuste(str(error))}") from error
    finally:
        sesion.rollback()


def guardar(
    sesion,
    proyecto: str,
    codigo: str,
    clausula: Clausula,
    periodos: Sequence[PeriodoDeclarado],
    *,
    fecha_calculo: date,
    fuente: str,
    responsable: str,
    reemplaza_a: int | None = None,
) -> int:
    """UC-18 6: guarda el estudio y confirma; devuelve su id. Si algo falla, deshace todo."""
    try:
        estudio = guardar_estudio(
            sesion,
            _version(sesion, proyecto, codigo),
            clausula,
            periodos,
            fecha_calculo=fecha_calculo,
            fuente=fuente,
            responsable=responsable,
            reemplaza_a=reemplaza_a,
        )
        sesion.commit()
    except HojaInvalida:
        sesion.rollback()
        raise
    except ValueError as error:
        sesion.rollback()
        raise HojaInvalida(
            f"No se guardó el estudio: {con_tildes_de_reajuste(str(error))}"
        ) from error
    except BaseException:
        sesion.rollback()
        raise
    return estudio.id


# --- lo ejecutado desde las valuaciones (S2, UC-18 enmendado) ------------------------------------


def _periodos_del_estudio(periodos: Sequence[Mapping[str, str]]) -> list[PeriodoDelEstudio]:
    return [
        PeriodoDelEstudio(
            _fecha(_campo(fila, "desde"), "desde"),
            _fecha(_campo(fila, "hasta"), "hasta"),
            _campo(fila, "version_comprobacion", obligatorio=False),
            _campo(fila, "excepcion", obligatorio=False),
        )
        for fila in periodos
        if _con_datos(fila)
    ]


def periodos_desde_valuaciones(
    sesion, proyecto: str, periodos: Sequence[Mapping[str, str]]
) -> list[PeriodoDeclarado]:
    """Los periodos de la pantalla con lo ejecutado de las valuaciones registradas y no anuladas
    (cada una al periodo que contiene su *hasta*; UC-18 enmendado, RF-72). No escribe nada."""
    return periodos_declarados(sesion, proyecto, _periodos_del_estudio(periodos))


def guardar_con_valuaciones(
    sesion,
    proyecto: str,
    codigo: str,
    clausula: Clausula,
    periodos: Sequence[Mapping[str, str]],
    *,
    fecha_calculo: date,
    fuente: str,
    responsable: str,
    reemplaza_a: int | None = None,
) -> int:
    """Como `guardar`, pero con lo ejecutado de las valuaciones, que el estudio cita. Confirma."""
    try:
        estudio = estudio_con_valuaciones(
            sesion,
            proyecto,
            codigo,
            clausula,
            _periodos_del_estudio(periodos),
            fecha_calculo=fecha_calculo,
            fuente=fuente,
            responsable=responsable,
            reemplaza_a=reemplaza_a,
        )
        sesion.commit()
    except HojaInvalida:
        sesion.rollback()
        raise
    except ValueError as error:
        sesion.rollback()
        raise HojaInvalida(
            f"No se guardó el estudio: {con_tildes_de_reajuste(str(error))}"
        ) from error
    except BaseException:
        sesion.rollback()
        raise
    return estudio.id


def parciales_por_reemplazar(sesion, proyecto: str, codigo: str) -> list[tuple[int, date]]:
    """Los estudios «parcial al corte» de la version que nadie reemplazo aun (id, fecha de
    calculo): los unicos que un estudio cerrado puede reemplazar (S1-R21)."""
    version = _version(sesion, proyecto, codigo)
    reemplazados = select(models.EstudioReajuste.reemplaza_a).where(
        models.EstudioReajuste.reemplaza_a.is_not(None)
    )
    return [
        (estudio.id, estudio.fecha_calculo)
        for estudio in sesion.scalars(
            select(models.EstudioReajuste)
            .where(
                models.EstudioReajuste.presupuesto_id == version.id,
                models.EstudioReajuste.estado == EstadoEstudio.PARCIAL.value,
                models.EstudioReajuste.id.not_in(reemplazados),
            )
            .order_by(models.EstudioReajuste.id)
        )
    ]


def versiones_del_proyecto(sesion, proyecto: str) -> list[tuple[str, str]]:
    """(codigo, motivo) de cada version del proyecto, de la mas antigua a la mas reciente. El
    motivo «revaloracion» marca las versiones que sirven a la comprobacion directa (S1 §8.3)."""
    filas = sesion.execute(
        select(models.Presupuesto.codigo, models.VersionOrigen.motivo)
        .join(models.Proyecto)
        .outerjoin(
            models.VersionOrigen, models.VersionOrigen.presupuesto_id == models.Presupuesto.id
        )
        .where(models.Proyecto.nombre == proyecto)
        .order_by(models.Presupuesto.id)
    ).all()
    return [(codigo, motivo or "") for codigo, motivo in filas]


def _monto(valor: Decimal | None) -> str:
    return NO_DISPONIBLE if valor is None else formatear_decimal(valor, 2)


def _suma(valores) -> Decimal | None:
    presentes = [v for v in valores if v is not None]
    return sum(presentes, Decimal(0)) if presentes else None


def _periodo(desde: date, hasta: date) -> str:
    return f"{desde:%d/%m/%Y} a {hasta:%d/%m/%Y}"


def _valores(resultado: ResultadoEstudio) -> list[tuple]:
    """Una fila por periodo y la del total, con los montos como `Decimal` (o `None`)."""
    filas = []
    for p in resultado.periodos:
        c = p.comparacion
        filas.append(
            (
                _periodo(p.desde, p.hasta),
                p.escalatoria,
                p.comprobacion,
                c.diferencia,
                p.reconocido,
                p.mecanismo_reconocido,
                c.moneda,
                c.escalatoria_otra,
                c.comprobacion_otra,
                c.diferencia_otra,
                c.tasa,
                "; ".join(p.marcas),
            )
        )
    comparaciones = [p.comparacion for p in resultado.periodos]
    filas.append(
        (
            "Total",
            resultado.total_escalatoria,
            resultado.total_comprobacion,
            _suma(c.diferencia for c in comparaciones),
            resultado.total_reconocido,
            "",
            resultado.moneda,
            _suma(c.escalatoria_otra for c in comparaciones),
            _suma(c.comprobacion_otra for c in comparaciones),
            _suma(c.diferencia_otra for c in comparaciones),
            None,
            "; ".join((f"estado: {resultado.estado.value}", *resultado.avisos)),
        )
    )
    return filas


def filas_lado_a_lado(resultado: ResultadoEstudio) -> list[dict[str, str]]:
    """La tabla lado a lado de UC-18 5 como texto: montos a dos decimales (redondeados una sola
    vez, S1 §8.4), «no disponible» donde no hay dato; la tasa exacta. Marcas y avisos van como
    texto en celdas (RV-14)."""
    salida = []
    for fila in _valores(resultado):
        textos = list(fila)
        for i in (1, 2, 3, 4, 7, 8, 9):
            textos[i] = _monto(fila[i])
        textos[10] = (
            ""
            if fila[0] == "Total"
            else (NO_DISPONIBLE if fila[10] is None else formatear_decimal(fila[10]))
        )
        salida.append(dict(zip(COLUMNAS_REAJUSTE, textos, strict=True)))
    return salida


def tabla_reajuste(resultado: ResultadoEstudio) -> TablaExportable:
    """La hoja «Reajuste» del Excel: los montos como numeros; lo que no hay, «no disponible»."""
    return TablaExportable(
        "Reajuste",
        COLUMNAS_REAJUSTE,
        tuple(
            tuple(NO_DISPONIBLE if v is None else v for v in fila) for fila in _valores(resultado)
        ),
    )


def tabla_ejecutado(periodos: Sequence[PeriodoDeclarado]) -> TablaExportable:
    """La hoja «Ejecutado» del Excel: lo ejecutado de cada periodo con su fuente."""
    return TablaExportable(
        "Ejecutado",
        COLUMNAS_EJECUTADO,
        tuple(
            (_periodo(p.desde, p.hasta), e.codigo, e.cantidad, e.fuente)
            for p in periodos
            for e in p.ejecutado
        ),
    )


def excel_en_bytes(
    sesion,
    proyecto: str,
    codigo: str,
    resultado: ResultadoEstudio,
    periodos: Sequence[PeriodoDeclarado],
) -> bytes:
    """El libro de la version del contrato (`exportar_hoja`) con las hojas Reajuste y Ejecutado
    por `hojas_extra` (RF-71), como bytes para `st.download_button`."""
    version = _version(sesion, proyecto, codigo)
    elaboracion = cargar_elaboracion(sesion, proyecto, codigo, Catalogo(sesion))
    parametros = ParametrosCosto(
        fcas=version.fcas,
        bono_alimentacion=version.bono_alimentacion,
        administracion=version.administracion,
        utilidad=version.utilidad,
    )
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = exportar_hoja(
            elaboracion.presupuesto,
            elaboracion.informe,
            Path(carpeta) / "reajuste.xlsx",
            parametros,
            hojas_extra=[tabla_reajuste(resultado), tabla_ejecutado(periodos)],
        )
        return ruta.read_bytes()
