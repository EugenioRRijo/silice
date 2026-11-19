"""Orquestacion de la elaboracion, sin Streamlit (INV-043, fase C3; RM-1, ola 2 de la sesion 2b).

Movido de `ui/elaboracion.py`, que lo reexporta: la API (`POST /presupuestos/calcular`) y la
pagina de Streamlit comparten esta logica. `guardar_composicion` y `Guardado` siguen en
`ui/elaboracion.py` hasta que la ola 3 (Componer una partida) los lleve a `aplicacion/`.

Antes vivia dentro de `ui/paginas/componer.py`, que asi pintaba, orquestaba «cantidades ->
elaborar -> exportar», calculaba y persistia a la vez (criterio S, spec de cierre §4). Aqui queda
la orquestacion contra `core.budget` y `core.catalog`; las paginas solo pintan y deciden los
mensajes. Sin Streamlit, sin `pandas` y sin `ui.caso`: cada funcion recibe lo que necesita y se
prueba como funcion (`tests/unit/test_elaboracion.py`). Lo vigila
`tests/unit/test_arquitectura.py::test_ui_respeta_sus_importaciones_prohibidas`.

Es el unico modulo de `ui/` sin pagina que escribe filas en la base (regla A-2 del plan de C3):
`guardar_composicion` y `declarar_rendimiento` (UC-01 3b, INV-088) escriben, pero no confirman;
el `commit` es de la pagina. Filas, no esquema:
`ui.caso.estado_caso` no escribe: lee con una conexion de solo lectura (RV-5).

Tarea 12 de montar un presupuesto: `elaborar_desde_catalogo` acepta la lista de la obra elegida y
`llevar_a_la_hoja` mete los items elaborados en el borrador de la Hoja de la obra (todo o nada, sin
guardar version; `POST /v1/hoja/llevar`).
"""

from __future__ import annotations

import dataclasses
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import select

from aplicacion import hoja, hoja_borradores, hoja_edicion, hoja_sin_valorar, importaciones
from aplicacion.cifras import CifraInvalida, texto_de_cifra
from aplicacion.composicion import (
    ComposicionInvalida,
    decimal_desde_texto,
    item_desde_cantidad,
    texto_de_celda,
)
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_partidas import CalculoInvalido, calculo_de_regla, cantidad_y_regla
from aplicacion.listas_para_armar import valoracion_de_la_obra
from core import models
from core.budget import ResultadoElaboracion, elaborar, exportar_excel, plan_secuencial
from core.budget.moneda import moneda_del_proyecto
from core.catalog import Catalogo, PropuestaRendimiento, proponer_rendimiento, registrar_rendimiento
from core.contracts import Dominio, ItemComputo, ParametrosCosto
from core.contracts.apu import Rendimiento, TipoRendimiento
from core.contracts.unidades import unidades_equivalentes

if TYPE_CHECKING:
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from aplicacion.hoja_borradores import BorradorVivo
    from core.budget import GeneradorPlan, PeriodoPlan
    from core.contracts.apu import ComposicionAPU
    from core.contracts.presupuesto import Presupuesto
    from core.models import Partida
    from ml.normalization import PartidaSimilar

#: Columnas de la tabla de cantidades de obra: la clave interna de cada fila, no su rotulo.
COLUMNAS_CANTIDADES = ("codigo_partida", "cantidad", "origen_id")

#: Columnas de la tabla del plan de trabajo (UC-01, paso 6): una fila por partida y periodo.
COLUMNAS_PLAN = ("periodo", "codigo_partida", "fraccion")


def items_desde_filas(
    filas: Sequence[Mapping[str, object]], partidas_por_codigo: Mapping[str, Partida]
) -> tuple[list[ItemComputo], list[str]]:
    """Las filas de la tabla de cantidades de obra como `ItemComputo`, mas un aviso por fila mala.

    El origen es obligatorio (una cantidad sin origen no es trazable, y `item_desde_cantidad` la
    rechaza: no es un dato, es un hallazgo). El dominio de cada item es el que ya declara la
    cabecera de esa partida en el catalogo (`models.Partida.dominio`). Una fila todavia en blanco
    no es un aviso: es el estado normal de una tabla dinamica.
    """
    items: list[ItemComputo] = []
    avisos: list[str] = []
    for indice, fila in enumerate(filas, start=1):
        codigo, cantidad_texto, origen_id = (
            texto_de_celda(fila, clave) for clave in COLUMNAS_CANTIDADES
        )
        if not codigo and not cantidad_texto and not origen_id:
            continue  # fila dinamica todavia en blanco: no es un error, es el estado normal
        if not codigo or codigo not in partidas_por_codigo:
            avisos.append(f"cantidades de obra, fila {indice}: seleccione una partida del catalogo")
            continue
        partida = partidas_por_codigo[codigo]
        try:
            items.append(
                item_desde_cantidad(
                    codigo=codigo,
                    descripcion=partida.descripcion,
                    unidad=partida.unidad,
                    cantidad=cantidad_texto,
                    origen_id=origen_id,
                    dominio=Dominio(partida.dominio),
                )
            )
        except ComposicionInvalida as error:
            avisos.append(f"cantidades de obra, fila {indice}: {error}")
    return items, avisos


def elaborar_desde_catalogo(
    catalogo: Catalogo,
    items: Sequence[ItemComputo],
    codigo: str,
    fecha: date,
    moneda: str,
    plan: Sequence[PeriodoPlan] | GeneradorPlan = plan_secuencial,
    lista: models.ListaPrecios | None = None,
) -> ResultadoElaboracion:
    """Elabora y audita el presupuesto de `items` con las composiciones del catalogo a `fecha`.

    UC-01, paso 6 (INV-087): `plan` es el plan de trabajo que distribuyo el proyectista
    (`plan_desde_filas`). Por defecto, `plan_secuencial` (una partida por dia, en el orden del
    presupuesto): la curva cierra exactamente en el total y R2 y R7 quedan limpias, y la linea base
    no cambia. Un plan que no reparte exactamente una vez cada partida lanza `PlanInvalido`.

    UC-01 3a (INV-072): pide solo las composiciones de los codigos que el catalogo tiene, el mismo
    criterio que `api/rutas/presupuestos.py`. Un item sin partida no lanza: `elaborar` lo deja en
    `ResultadoElaboracion.pendientes` y el informe lo declara con un hallazgo `PENDIENTE`.

    Con `lista` (Tarea 12 de montar un presupuesto: la de `lista_para_el_proyecto` de la obra
    elegida), los precios salen de esa lista y no de la vigente del catalogo, que no mira la moneda;
    `moneda` debe ser entonces la de esa lista (la pone la ruta).
    """
    existentes = {partida.codigo for partida in catalogo.partidas()}
    codigos_unicos = [
        codigo
        for codigo in dict.fromkeys(item.codigo_partida for item in items)
        if codigo in existentes
    ]
    if lista is None:
        composiciones = catalogo.composiciones(codigos_unicos, fecha=fecha)
    else:
        composiciones = {
            codigo: catalogo.composicion(codigo, fecha=fecha, lista=lista)
            for codigo in codigos_unicos
        }
    return elaborar(
        list(items),
        composiciones,
        ParametrosCosto(),
        codigo=codigo,
        fecha=fecha,
        moneda=moneda,
        plan=plan,
    )


def filas_desde_plan(plan: Sequence[PeriodoPlan]) -> list[dict[str, str]]:
    """UC-01, paso 6 (INV-087): el plan de trabajo como filas de la tabla editable, una por
    partida y periodo, con la fraccion como texto exacto en notacion fija (`format(x, "f")`: `str`
    daba «1E-7», que la pantalla no puede volver a leer)."""
    return [
        {"periodo": periodo, "codigo_partida": codigo, "fraccion": format(fraccion, "f")}
        for periodo, reparto in plan
        for codigo, fraccion in reparto
    ]


def plan_de(filas: Sequence[Mapping[str, object]] | None) -> list[PeriodoPlan] | GeneradorPlan:
    """UC-01, paso 6: el plan de las filas del proyectista o, sin filas, el plan por defecto
    (`plan_secuencial`). Decide aqui, no en la pagina (U-6 de la revision de C5)."""
    return plan_secuencial if filas is None else plan_desde_filas(filas)


def filas_del_plan_por_defecto(presupuesto: Presupuesto) -> list[dict[str, str]]:
    """Las filas del plan por defecto (`plan_secuencial`) sobre el presupuesto ya valorado: la
    tabla que la pagina precarga tras cada elaboracion sin plan del proyectista."""
    return filas_desde_plan(plan_secuencial(presupuesto))


def plan_desde_filas(filas: Sequence[Mapping[str, object]]) -> list[PeriodoPlan]:
    """UC-01, paso 6 (INV-087): las filas de la tabla del plan como plan de trabajo de `elaborar`.

    Los periodos siguen el orden de su primera fila, y cada uno reune las partidas de sus filas en
    su orden. Una fila en blanco se ignora (estado normal de una tabla dinamica); una a medias o
    con una fraccion que no es un decimal lanza `ComposicionInvalida` (un `ValueError`) con su
    numero de fila. Que cada partida sume exactamente 1 lo juzga `elaborar` (`PlanInvalido`): la
    regla del plan vive en `core.budget.curva`, no aqui.
    """
    periodos: dict[str, list[tuple[str, Decimal]]] = {}
    for indice, fila in enumerate(filas, start=1):
        periodo, codigo, fraccion = (texto_de_celda(fila, clave) for clave in COLUMNAS_PLAN)
        if not periodo and not codigo and not fraccion:
            continue  # fila dinamica todavia en blanco
        if not periodo or not codigo or not fraccion:
            raise ComposicionInvalida(
                f"plan de trabajo, fila {indice}: declare el periodo, la partida y la fraccion"
            )
        valor = decimal_desde_texto(fraccion, f"plan de trabajo, fila {indice}, fraccion")
        periodos.setdefault(periodo, []).append((codigo, valor))
    return [(periodo, tuple(reparto)) for periodo, reparto in periodos.items()]


def nombre_de_archivo(prefijo: str, codigo: str, extension: str) -> str:
    """`<prefijo>_<codigo>.<extension>` con solo [A-Za-z0-9._ -]: sin rutas, comillas ni saltos de
    linea. El codigo es texto de la persona y acaba en una cabecera `Content-Disposition` o en el
    nombre de una descarga: nunca se usa tal cual para nombrar un archivo."""
    limpio = re.sub(r"[^A-Za-z0-9._ -]", "_", codigo).replace("..", "_")
    return f"{prefijo}_{limpio[:64]}.{extension}"


def libro_excel(resultado: ResultadoElaboracion) -> tuple[bytes, str]:
    """El libro de Excel del presupuesto elaborado (con su hoja de auditoria) y su nombre.

    El libro se escribe con un nombre fijo dentro de un directorio temporal: el codigo del
    presupuesto (texto de la persona) solo da el nombre de la descarga, ya saneado."""
    with tempfile.TemporaryDirectory() as carpeta:
        libro = exportar_excel(
            resultado.presupuesto, resultado.informe, Path(carpeta) / "presupuesto.xlsx"
        )
        nombre = nombre_de_archivo("presupuesto", resultado.presupuesto.codigo, "xlsx")
        return libro.read_bytes(), nombre


# --- UC-01 3a: los pendientes, sus propuestas y la aceptacion (INV-072, D6) --------------------


@dataclass(frozen=True, slots=True)
class PendienteConPropuestas:
    """Un item pendiente y las partidas similares que se le proponen (o por que no las hay)."""

    item: ItemComputo
    similares: tuple[PartidaSimilar, ...] = ()
    falla: str | None = None


def propuestas_de_pendientes(
    partidas: Mapping[str, str], pendientes: Sequence[ItemComputo]
) -> tuple[PendienteConPropuestas, ...]:
    """Una entrada por pendiente, en su orden, con las partidas del catalogo parecidas a su
    descripcion (`partidas`: codigo -> descripcion). Sin pendientes devuelve `()` sin cargar nada.

    El emparejamiento es `ml.normalization.propuestas_para`, el mismo de la API (INV-081): un solo
    normalizador por elaboracion, y el criterio unico de fallas (una falla declarada deja al
    pendiente sin similares y con su `falla`; un defecto se propaga). `ml.normalization` se importa
    aqui, perezoso, como las demas ayudas de `ml`: no arrastra el extra, pero `ui/` no carga `ml`
    hasta que hay pendientes.
    """
    if not pendientes:
        return ()
    from ml.normalization import propuestas_para

    return tuple(
        PendienteConPropuestas(item, propuesta.similares, propuesta.falla)
        for item, propuesta in propuestas_para(partidas, pendientes)
    )


def aceptar_propuesta(
    items: Sequence[ItemComputo], pendiente: ItemComputo, codigo_elegido: str
) -> list[ItemComputo]:
    """UC-01 3a (D6): el item `pendiente` pasa a la partida propuesta que el usuario acepto. Los
    demas items no cambian; si `pendiente` no esta entre `items`, ValueError."""
    if pendiente not in items:
        raise ValueError(f"el item {pendiente.origen_id!r} no esta entre los items a elaborar")
    return [
        dataclasses.replace(item, codigo_partida=codigo_elegido) if item == pendiente else item
        for item in items
    ]


# --- UC-01 3b: la partida sin rendimiento vigente (INV-088) ------------------------------------


@dataclass(frozen=True, slots=True)
class RendimientoPorDeclarar:
    """Una partida sin rendimiento estimado vigente y la propuesta del historico (UC-06), o
    `None` si la partida no tiene ningun rendimiento registrado."""

    codigo_partida: str
    propuesta: PropuestaRendimiento | None


def es_rendimiento_vigente(
    tipo: TipoRendimiento | str, fecha_rendimiento: date, fecha: date
) -> bool:
    """La politica de «rendimiento vigente» fuera del nucleo, en un solo sitio (plan de desenredo,
    tarea 2.5): lo que `Catalogo.composicion` exige para reconstruir un APU, un rendimiento
    ESTIMADO de fecha no posterior a `fecha`. `tipo` puede ser el texto de la fila ORM
    (`"estimado"`), como en `aplicacion.hoja_vial`."""
    return TipoRendimiento(tipo) is TipoRendimiento.ESTIMADO and fecha_rendimiento <= fecha


def rendimientos_por_declarar(
    sesion: Session, items: Sequence[ItemComputo], fecha: date
) -> tuple[RendimientoPorDeclarar, ...]:
    """UC-01 3b: las partidas de `items` sin rendimiento estimado vigente a `fecha`, en su orden,
    cada una con la propuesta de `proponer_rendimiento` (el rendimiento y su dispersion).

    Vigente es lo que dice `es_rendimiento_vigente`. Los codigos sin partida no cuentan: quedan
    pendientes (flujo 3a).

    `Catalogo.composiciones` resuelve la lista de precios antes que los rendimientos, asi que sin
    lista vigente a `fecha` el `CatalogoIncompleto` es de la lista, no de 3b: se relanza aqui
    (`Catalogo.lista_vigente`) antes de clasificar nada (U-1 de la revision de C5).
    """
    catalogo = Catalogo(sesion)
    catalogo.lista_vigente(fecha)
    existentes = {partida.codigo for partida in catalogo.partidas()}
    codigos = [
        codigo
        for codigo in dict.fromkeys(item.codigo_partida for item in items)
        if codigo in existentes
    ]
    return tuple(
        RendimientoPorDeclarar(codigo, proponer_rendimiento(sesion, codigo))
        for codigo in codigos
        if not any(
            es_rendimiento_vigente(rendimiento.tipo, rendimiento.fecha, fecha)
            for rendimiento in catalogo.rendimientos(codigo)
        )
    )


def rendimiento_por_declarar(sesion: Session, codigo: str, fecha: date) -> RendimientoPorDeclarar:
    """UC-01 3b para una sola partida: su propuesta del historico, si le falta el rendimiento
    estimado vigente a `fecha`. `KeyError` (404) si la partida no existe; `ValueError` (422) si ya
    tiene uno vigente: no hay nada que declarar."""
    catalogo = Catalogo(sesion)
    catalogo.partida(codigo)
    if any(
        es_rendimiento_vigente(rendimiento.tipo, rendimiento.fecha, fecha)
        for rendimiento in catalogo.rendimientos(codigo)
    ):
        raise ValueError(f"la partida {codigo} ya tiene un rendimiento estimado vigente al {fecha}")
    return RendimientoPorDeclarar(codigo, proponer_rendimiento(sesion, codigo))


def declarar_rendimiento(
    sesion: Session, por_declarar: RendimientoPorDeclarar, tipo: TipoRendimiento, fecha: date
) -> Rendimiento:
    """UC-01 3b: registra el rendimiento propuesto con el tipo que declaro el proyectista.

    La elaboracion usa solo el rendimiento ESTIMADO vigente (`Catalogo.composicion`): declarado
    ESTIMADO, se registra a la `fecha` del presupuesto con condiciones generadas desde su
    procedencia (tipo, fecha, ejecucion y dispersion del propuesto). Declarado MEDIDO no se usa tal
    cual (esa politica es de `core/`, fuera del alcance de C5): `ValueError` y nada se registra.
    Sin propuesta, tambien `ValueError`. **No confirma**: el `commit` es de la pagina, como en
    `guardar_composicion`.
    """
    propuesta = por_declarar.propuesta
    codigo = por_declarar.codigo_partida
    if propuesta is None:
        raise ValueError(f"la partida {codigo} no tiene historico de rendimientos que proponer")
    if tipo is not TipoRendimiento.ESTIMADO:
        raise ValueError(
            f"la elaboracion usa el rendimiento estimado vigente de {codigo}: un rendimiento "
            "declarado medido no se usa tal cual; declare el propuesto como estimado para elaborar"
        )
    origen = propuesta.rendimiento
    dispersion = propuesta.dispersion
    referencia = f", ejecucion {origen.referencia_ejecucion}" if origen.referencia_ejecucion else ""
    condiciones = (
        f"propuesto del historico al elaborar (UC-01 3b): {origen.tipo.value} del {origen.fecha}"
        f"{referencia}; dispersion: {dispersion.observaciones} observaciones, rango "
        f"[{dispersion.minimo}, {dispersion.maximo}]"
    )
    return registrar_rendimiento(sesion, codigo, origen.valor, tipo, fecha, condiciones)


# --- Tarea 12 de montar un presupuesto: llevar los items a la Hoja de la obra -------------------


#: Elaborar o llevar a la Hoja con una obra que no esta en la carpeta; no repite lo enviado.
MENSAJE_SIN_OBRA = (
    "Esa obra no está en esta carpeta de trabajo: elíjala de nuevo en el selector de obra."
)


class VersionQueNoSeAbre(Exception):  # noqa: N818
    """La version vigente de la obra ya no se puede abrir como borrador (la `HojaInvalida` de
    `hoja.abrir_version`); el mensaje es el que ve la persona."""


@dataclass(frozen=True, slots=True)
class PartidaParaLlevar:
    """Un item de Elaborar que va a la Hoja: el codigo de su partida, su cantidad exacta (la del
    computo) y, si la persona lo escribio, el calculo con coma decimal (Tarea 8).

    Prueba en vivo del 18/11/2026: lo que el computo sabe del item viaja con el, para no perder su
    trazabilidad: su `unidad` (si no equivale a la del APU, no se lleva: R3), su `origen` y su
    `regla` con sus `parametros` (el calculo y la nota del renglon, `_calculo_y_nota`)."""

    codigo: str
    cantidad: Decimal
    calculo: str = ""
    unidad: str = ""
    origen: str = ""
    regla: str = ""
    parametros: Mapping[str, Decimal] = field(default_factory=dict)


def _choque_de_unidades(computo: str, apu: str) -> str:
    """Lo que dice el 422 de un item del computo cuya unidad no es la de su APU (R3, antes de
    llevar)."""
    return (
        f"el cómputo la mide en «{computo}» y su APU está en «{apu}»: no son la misma unidad, así "
        f"que su precio no aplicaría a esa cantidad. No se llevó nada: elija una partida que se "
        f"mida en «{computo}» o corrija el cómputo."
    )


#: El largo maximo de la nota de un renglon (`POST /v1/hoja/borradores/{id}/partidas`).
LARGO_DE_NOTA = 500


def _cuadra(cantidad: Decimal, calculo: str) -> bool:
    try:
        cantidad_y_regla(texto_de_cifra(cantidad), calculo)
    except (CalculoInvalido, CifraInvalida):
        return False
    return True


def _calculo_y_nota(partida: PartidaParaLlevar) -> tuple[str, str]:
    """El calculo y la nota con que el item entra a la Hoja. El calculo es el escrito o, si no, la
    regla del computo con sus parametros (`calculo_de_regla`) cuando da su cantidad; la nota dice
    de donde salio («Del cómputo: TQ-01.») y, si la regla no se pudo escribir como calculo, la
    regla misma, para que la cantidad no quede sin explicar."""
    calculo = partida.calculo
    if not calculo and partida.regla:
        derivado = calculo_de_regla(partida.regla, partida.parametros)
        if derivado is not None and _cuadra(partida.cantidad, derivado):
            calculo = derivado
    if not partida.origen:
        return calculo, ""
    con_regla = f", con la regla {partida.regla}" if partida.regla and not calculo else ""
    nota = f"Del cómputo: {partida.origen}{con_regla}."
    return calculo, nota if len(nota) <= LARGO_DE_NOTA else nota[: LARGO_DE_NOTA - 1] + "…"


def _validar(sesion: Session, partidas: Sequence[PartidaParaLlevar]) -> None:
    """Lo que `hoja_edicion.agregar` rechazaria de cada partida, antes de tocar ningun borrador:
    que este en el catalogo (`PartidaFueraDelCatalogo`) y su cantidad y su calculo (`HojaInvalida`
    con el codigo delante), con las mismas reglas (`cantidad_y_regla`, Tarea 8). Y, con la unidad
    del computo, que equivalga a la del APU (R3, `HojaInvalida`): una tuberia en m sobre un APU
    por pieza no se lleva (prueba en vivo del 18/11/2026)."""
    catalogo = Catalogo(sesion)
    for partida in partidas:
        try:
            fila = catalogo.partida(partida.codigo)
        except KeyError:
            raise hoja_edicion.PartidaFueraDelCatalogo(partida.codigo) from None
        if partida.unidad and not unidades_equivalentes(partida.unidad, fila.unidad):
            choque = _choque_de_unidades(partida.unidad, fila.unidad)
            raise HojaInvalida(f"{partida.codigo}: {choque}")
        try:
            cantidad_y_regla(texto_de_cifra(partida.cantidad), partida.calculo)
        except (CalculoInvalido, CifraInvalida) as error:
            raise HojaInvalida(f"{partida.codigo}: {error}") from None


def _sin_valorar(
    sesion: Session, vivo: BorradorVivo, codigos: Sequence[str], **textos: str
) -> str | None:
    """Qué dice la Hoja de las partidas `codigos` que quedaron sin APU (PENDIENTE) en la versión
    abierta de `vivo`: qué insumos no tienen precio en su lista, en qué listas están, qué
    rendimiento falta y qué hacer (`hoja_sin_valorar`, con la política de rendimiento vigente de
    este módulo). `None` si todas se valoran o el borrador está en blanco (se valora con la lista
    para armar, donde escribe Componer)."""
    if vivo.abierta is None:
        return None
    faltan = sorted(set(codigos) - set(vivo.borrador.composiciones))
    if not faltan:
        return None
    lista, _valoracion = hoja_edicion.lista_para_completar(sesion, vivo, vivo.borrador.fecha)
    return hoja_sin_valorar.explicar(
        sesion,
        faltan,
        lista,
        vivo.abierta.codigo,
        vivo.borrador.fecha,
        vigente=es_rendimiento_vigente,
        **textos,
    )


def agregar(
    sesion: Session,
    huella: str,
    id: str,
    rev: int,
    *,
    codigo: str,
    cantidad: str,
    calculo: str,
    nota: str,
) -> tuple[BorradorVivo, str, str | None]:
    """`hoja_edicion.agregar` desde la Hoja, con el aviso de una partida que queda PENDIENTE con
    la lista de la versión (prueba en vivo del 18/11/2026): el borrador, la clave del renglón y el
    aviso, o `None`. Árbitro de la rama (2026-11-18): agregar a mano no se bloquea, porque una
    partida puede esperar su cotización (UC-01 3a), otro renglón de una partida ya pendiente es
    legítimo y una lista de la obra o convertida no la escribe Componer; el diálogo de guardar
    vuelve a avisarlo."""
    vivo, clave = hoja_edicion.agregar(
        sesion, huella, id, rev, codigo=codigo, cantidad=cantidad, calculo=calculo, nota=nota
    )
    aviso = _sin_valorar(
        sesion,
        vivo,
        [codigo],
        inicio=f"La partida «{codigo}» queda pendiente en el Presupuesto",
        se_valora="se puede valorar",
        esas="esa partida",
        # la fila que ya está no se revalora sola: el borrador completa solo las partidas nuevas
        # (re-verificación del 18/11/2026; revalorarla haría falta una ruta nueva en la Hoja)
        cierre=(
            "Después, quite la fila y agréguela de nuevo: la fila que ya está no se vuelve a "
            "valorar sola. Mientras siga pendiente, la versión no se podrá enviar a aprobación."
        ),
    )
    return vivo, clave, aviso


def _exigir_valoradas(sesion: Session, vivo: BorradorVivo, codigos: Sequence[str]) -> None:
    """Llevar es todo o nada (como los tramos, `hoja_vial._valorado`): si alguna partida queda
    PENDIENTE con la lista de la versión, `hoja_sin_valorar.PartidasSinValorar` (409) con TODAS
    las que faltan a la vez (árbitro de la rama, 2026-11-18)."""
    faltan = sorted(set(codigos) - set(vivo.borrador.composiciones))
    cuantas = (
        "1 partida quedaría pendiente"
        if len(faltan) == 1
        else f"{len(faltan)} partidas quedarían pendientes"
    )
    mensaje = _sin_valorar(
        sesion, vivo, codigos, inicio=f"No se llevó nada: {cuantas} en el Presupuesto"
    )
    if mensaje is not None:
        raise hoja_sin_valorar.PartidasSinValorar(mensaje)


def version_del_borrador_de_la_obra(
    sesion: Session, huella: str, caso: str, proyecto: str
) -> tuple[BorradorVivo | None, str | None]:
    """El borrador de la Hoja de la obra `proyecto` (su nombre) que usan llevar a la Hoja y llevar
    los tramos: el vivo mas reciente de esa ficha y esa obra en el caso, si lo hay, y el codigo de
    la version sobre la que esta o, sin vivo, sobre la que se abriria (la vigente); `None` si es
    (o seria) un borrador en blanco. Solo lee: no abre ni registra nada. Es la unica eleccion del
    borrador de la obra: `borrador_de_la_obra` la usa para abrirlo. No toma el cerrojo de ningun
    borrador ni cuenta sus cambios (DS-54): llevar el libro elige con su transaccion abierta."""
    for vivo in hoja_edicion.borradores_abiertos(huella, caso):
        if vivo.proyecto == proyecto:
            return vivo, vivo.version
    return None, hoja.codigo_vigente(sesion, proyecto)


def borrador_de_la_obra(
    sesion: Session,
    huella: str,
    caso: str,
    proyecto: models.Proyecto,
    *,
    responsable: str,
    hoy: date,
) -> tuple[BorradorVivo, bool]:
    """El borrador de `version_del_borrador_de_la_obra` (`False`: ya existia) o uno nuevo (`True`)
    sobre la version vigente o, sin versiones, en blanco en la moneda de la obra, como
    `POST /v1/hoja/borradores`. Abrir la vigente escribe su instantanea si faltaba (UC-15e), la
    misma y unica escritura de abrir la Hoja; `VersionQueNoSeAbre` si ya no se puede reconstruir.
    En blanco, comprueba antes de registrarlo que haya lista con que valorar la obra
    (`SinListaDeLaObra`): registrar uno nuevo puede expulsar el menos usado de la ficha
    (`POR_FICHA`), asi que solo se registra cuando ya no queda nada previsible que pueda fallar."""
    nombre = proyecto.nombre
    existente, vigente = version_del_borrador_de_la_obra(sesion, huella, caso, nombre)
    if existente is not None:
        return existente, False
    if vigente is None:
        try:  # el 409 de la Hoja en blanco, antes de registrar el borrador (ronda 2)
            valoracion_de_la_obra(sesion, nombre, hoy)
        except ValueError as error:  # sin lista para armar o sin tasa del BCV
            raise hoja_edicion.SinListaDeLaObra(str(error)) from None
        borrador = hoja.Borrador(fecha=hoy, moneda=moneda_del_proyecto(sesion, proyecto))
        abierta = None
    else:
        try:
            abierta = hoja.abrir_version(
                sesion,
                Catalogo(sesion),
                nombre,
                vigente,
                fecha_evaluacion=hoy,
                responsable=responsable,
            )
        except HojaInvalida as error:
            raise VersionQueNoSeAbre(str(error)) from None
        borrador = abierta.borrador
    vivo = hoja_borradores.crear(
        huella, caso, nombre, vigente, borrador, abierta, vigente_al_abrir=vigente
    )
    return vivo, True


def llevar_a_la_hoja(
    sesion: Session,
    huella: str,
    caso: str,
    proyecto: models.Proyecto,
    partidas: Sequence[PartidaParaLlevar],
    *,
    responsable: str,
    hoy: date,
    archivo: str | None = None,
) -> str:
    """Agrega `partidas` al borrador de la Hoja de la obra `proyecto` y devuelve su id. No guarda
    version: los renglones quedan como altas del borrador, que se guardan desde la Hoja.

    Usa el borrador vivo mas reciente de esa ficha y obra o abre uno (`borrador_de_la_obra`) y
    agrega cada partida con `hoja_edicion.agregar` (Tarea 9), la cantidad escrita como la teclearia
    la persona (`texto_de_cifra`: «1.125» del computo es uno coma ciento veinticinco). **Todo o
    nada:** con el cerrojo del borrador tomado de punta a punta, si una partida falla
    (`PartidaFueraDelCatalogo`, `HojaInvalida` con el codigo de la partida delante,
    `SinListaDeLaObra`, `hoja_sin_valorar.PartidasSinValorar` si quedaria pendiente con la lista
    de la version, la base) el borrador abierto aqui se descarta y uno que ya existia vuelve
    exactamente a como estaba, con su `rev` (la ventana que lo esta editando no ve ningun cambio),
    y el error sube. `VersionQueNoSeAbre` si la vigente ya no se puede abrir.

    Ronda 2: las partidas se validan (`_validar`) y la lista de la obra en blanco se comprueba
    ANTES de abrir el borrador, porque registrar uno nuevo puede expulsar el menos usado de la
    ficha: un llevar que falla por algo previsible no quita ningun otro borrador.

    F4, Tarea 10: con `archivo` (el nombre del cómputo, sin ruta) el llevar queda anotado en el
    registro de importaciones de la obra (`aplicacion.importaciones`), «sin guardar» hasta que se
    guarde la versión; sin él no se registra nada. Solo se anota si todas las partidas entraron."""
    _validar(sesion, partidas)
    vivo, nuevo = borrador_de_la_obra(
        sesion, huella, caso, proyecto, responsable=responsable, hoy=hoy
    )
    with vivo.cerrojo:
        antes = (vivo.borrador, vivo.rev, vivo.calculo, vivo.tamano)
        try:
            for partida in partidas:
                calculo, nota = _calculo_y_nota(partida)
                try:
                    vivo, _clave = hoja_edicion.agregar(
                        sesion,
                        huella,
                        vivo.id,
                        vivo.rev,
                        codigo=partida.codigo,
                        cantidad=texto_de_cifra(partida.cantidad),
                        calculo=calculo,
                        nota=nota,
                    )
                except HojaInvalida as error:  # varias partidas: se dice cual
                    raise HojaInvalida(f"{partida.codigo}: {error}") from None
            _exigir_valoradas(sesion, vivo, [partida.codigo for partida in partidas])
            if archivo is not None:
                texto = importaciones.resumen_de_computo(len(partidas))
                importaciones.anotar(
                    vivo, importaciones.nueva("computo", archivo, responsable, texto)
                )
        except BaseException:
            if nuevo:
                hoja_borradores.descartar(huella, vivo.id)
            else:
                vivo.borrador, vivo.rev, vivo.calculo, vivo.tamano = antes
            raise
    return vivo.id


@dataclass(frozen=True)
class PreciosSinEfecto:
    """Los precios de ensayo de un escenario de UC-08 que no cambian nada, por su descripción y en
    el orden en que se enviaron.

    El cálculo (`core.budget.escenarios`) empareja la descripción del insumo por igualdad exacta y
    deja el precio vigente a lo que no nombra: un precio de un insumo que el presupuesto base no
    tiene se descarta en silencio, y uno igual al vigente no varía nada. `insumos_variados` solo
    los cuenta; aquí se nombran, para que la pantalla lo diga.

    - `sin_insumo`: ningún renglón del base usa esa descripción (p. ej. otra mayúscula).
    - `sin_cambio`: está en el base, pero en todos sus renglones ya vale ese precio."""

    sin_insumo: tuple[str, ...] = ()
    sin_cambio: tuple[str, ...] = ()


def precios_sin_efecto(
    composiciones: Mapping[str, ComposicionAPU], precios: Mapping[str, Decimal]
) -> PreciosSinEfecto:
    """Compara los precios de ensayo con los de las composiciones del base, con el mismo criterio
    que `insumos_variados` (descripción exacta; materiales y equipos por precio, mano de obra por
    sueldo). No calcula ningún monto."""
    vigentes: dict[str, set[Decimal]] = {}
    for composicion in composiciones.values():
        for linea in (*composicion.materiales, *composicion.equipos):
            vigentes.setdefault(linea.descripcion, set()).add(linea.precio)
        for obrero in composicion.mano_obra:
            vigentes.setdefault(obrero.descripcion, set()).add(obrero.sueldo)
    return PreciosSinEfecto(
        sin_insumo=tuple(d for d in precios if d not in vigentes),
        sin_cambio=tuple(d for d, p in precios.items() if vigentes.get(d) == {p}),
    )


# --- Consultas del caso que antes escribian las rutas (tarea 3.1 del plan de desenredo) --------


def presupuestos_guardados(sesion: Session) -> list[models.Presupuesto]:
    """Todos los presupuestos guardados del caso, ordenados por codigo (`GET /presupuestos`)."""
    return list(sesion.scalars(select(models.Presupuesto).order_by(models.Presupuesto.codigo)))


class PresupuestoAmbiguo(Exception):  # noqa: N818
    """El codigo existe en mas de una obra y no se dijo cual: la ruta lo declara con un 409. No es
    un `LookupError`, que seria un 404: el presupuesto si existe."""

    def __init__(self, codigo: str, obras: tuple[str, ...]) -> None:
        super().__init__(f"el código {codigo!r} existe en más de una obra ({', '.join(obras)})")
        self.codigo = codigo
        self.obras = obras


def presupuesto_por_codigo(
    sesion: Session, codigo: str, proyecto: str | None
) -> models.Presupuesto:
    """El renglon de `models.Presupuesto` de ese codigo, acotado por obra si se indica.

    `codigo` solo es unico **por obra** (`UniqueConstraint(proyecto_id, codigo)`): sin `proyecto`,
    dos obras con el mismo codigo lanzan `PresupuestoAmbiguo` (con las obras por nombre) en vez de
    un `MultipleResultsFound`. Ninguna coincidencia es `LookupError` (404)."""
    consulta = select(models.Presupuesto).where(models.Presupuesto.codigo == codigo)
    if proyecto is not None:
        consulta = consulta.join(models.Proyecto).where(models.Proyecto.nombre == proyecto)
    encontrados = list(sesion.scalars(consulta))
    if not encontrados:
        detalle = f"no hay ningún presupuesto con código {codigo!r}"
        if proyecto is not None:
            detalle += f" en la obra {proyecto!r}"
        raise LookupError(detalle)
    if len(encontrados) > 1:
        obras = tuple(sorted({modelo.proyecto.nombre for modelo in encontrados}))
        raise PresupuestoAmbiguo(codigo, obras)
    return encontrados[0]


def ejecuciones(sesion: Session) -> list[models.Ejecucion]:
    """Las obras ejecutadas registradas, de la mas antigua a la mas reciente (`id` si empatan)."""
    consulta = select(models.Ejecucion).order_by(models.Ejecucion.fecha_inicio, models.Ejecucion.id)
    return list(sesion.scalars(consulta))
