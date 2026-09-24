"""Orquestacion de la elaboracion desde la interfaz, sin Streamlit (INV-043, fase C3).

Antes vivia dentro de `ui/paginas/componer.py`, que asi pintaba, orquestaba «cantidades ->
elaborar -> exportar», calculaba y persistia a la vez (criterio S, spec de cierre §4). Aqui queda
la orquestacion contra `core.budget` y `core.catalog`; las paginas solo pintan y deciden los
mensajes. Sin Streamlit, sin `pandas` y sin `ui.caso`: cada funcion recibe lo que necesita y se
prueba como funcion (`tests/unit/test_elaboracion.py`). Lo vigila
`tests/unit/test_arquitectura.py::test_ui_respeta_sus_importaciones_prohibidas`.

Es el unico modulo de `ui/` sin pagina que escribe en la base (regla A-2 del plan de C3):
`guardar_composicion` escribe, pero no confirma; el `commit` es de la pagina.
"""

from __future__ import annotations

import dataclasses
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from core.budget import ResultadoElaboracion, elaborar, exportar_excel, plan_secuencial
from core.contracts import ComposicionAPU, Dominio, ItemComputo, ParametrosCosto, ResultadoAPU
from ui import composicion as _composicion
from ui.composicion import (
    ComposicionInvalida,
    desglose,
    item_desde_cantidad,
    motivo_para_no_reemplazar,
    texto_de_celda,
)

if TYPE_CHECKING:
    from core.catalog import Catalogo
    from core.models import Partida
    from ml.normalization import PartidaSimilar

#: Columnas de la tabla de cantidades de obra: la clave interna de cada fila, no su rotulo.
COLUMNAS_CANTIDADES = ("codigo_partida", "cantidad", "origen_id")


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
    catalogo: Catalogo, items: Sequence[ItemComputo], codigo: str, fecha: date, moneda: str
) -> ResultadoElaboracion:
    """Elabora y audita el presupuesto de `items` con las composiciones del catalogo a `fecha`.

    Con `plan_secuencial` (una partida por dia, en el orden del presupuesto): sin plan la curva no
    existe y R2 lo hace constar; con este plan trivial la curva cierra exactamente en el total y R2
    y R7 quedan limpias.

    UC-01 3a (INV-072): pide solo las composiciones de los codigos que el catalogo tiene, el mismo
    criterio que `api/rutas/presupuestos.py`. Un item sin partida no lanza: `elaborar` lo deja en
    `ResultadoElaboracion.pendientes` y el informe lo declara con un hallazgo `PENDIENTE`.
    """
    existentes = {partida.codigo for partida in catalogo.partidas()}
    codigos_unicos = [
        codigo
        for codigo in dict.fromkeys(item.codigo_partida for item in items)
        if codigo in existentes
    ]
    composiciones = catalogo.composiciones(codigos_unicos, fecha=fecha)
    return elaborar(
        list(items),
        composiciones,
        ParametrosCosto(),
        codigo=codigo,
        fecha=fecha,
        moneda=moneda,
        plan=plan_secuencial,
    )


def libro_excel(resultado: ResultadoElaboracion) -> tuple[bytes, str]:
    """El libro de Excel del presupuesto elaborado (con su hoja de auditoria) y su nombre."""
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / f"presupuesto_{resultado.presupuesto.codigo}.xlsx"
        libro = exportar_excel(resultado.presupuesto, resultado.informe, ruta)
        return libro.read_bytes(), libro.name


@dataclass(frozen=True, slots=True)
class Guardado:
    """Lo que dejo `guardar_composicion`: el desglose guardado o el motivo para no guardar."""

    resultado: ResultadoAPU | None = None
    motivo: str | None = None

    def __post_init__(self) -> None:
        if (self.resultado is None) == (self.motivo is None):
            raise ValueError("un Guardado lleva exactamente uno de los dos: resultado o motivo")


def guardar_composicion(
    catalogo: Catalogo,
    composicion: ComposicionAPU,
    dominio: Dominio,
    fecha: date,
    condiciones: str,
) -> Guardado:
    """Persiste la composicion: UC-10 si la partida no existe, UC-11 si ya existe.

    Sobre una partida existente, `motivo_para_no_reemplazar` decide antes de escribir: una
    composicion sin lineas borraria el desglose, y una cabecera distinta se descartaria en silencio
    (`reemplazar_composicion` solo sustituye lineas y rendimiento). En ese caso devuelve el motivo
    y no escribe nada. **No confirma**: el `commit` lo decide la pagina.
    """
    lista = catalogo.lista_vigente(fecha)
    try:
        partida = catalogo.partida(composicion.codigo_partida)
    except KeyError:
        catalogo.cargar_composicion(composicion, lista, dominio, fecha, condiciones)
    else:
        motivo = motivo_para_no_reemplazar(partida.descripcion, partida.unidad, composicion)
        if motivo is not None:
            return Guardado(motivo=motivo)
        catalogo.reemplazar_composicion(composicion, lista, dominio, fecha, condiciones)
    return Guardado(resultado=desglose(composicion))


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

    **Cuerpo provisional (Tarea 7 del plan de C3):** llama a
    `ui.composicion.sugerir_partidas_similares` una vez por pendiente, con su criterio de error de
    hoy (una falla da una lista vacia), y por eso construye un indice semantico por pendiente. Lo
    corrige 10c, que pasa el cuerpo a `ml.normalization.propuestas_para`: un solo normalizador por
    llamada y el emparejamiento que comparte la API. La firma y el tipo de retorno no cambian.
    """
    if not pendientes:
        return ()
    return tuple(
        PendienteConPropuestas(
            item=pendiente,
            similares=tuple(
                _composicion.sugerir_partidas_similares(partidas, pendiente.descripcion)
            ),
        )
        for pendiente in pendientes
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
