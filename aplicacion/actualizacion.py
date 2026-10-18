"""UC-02 sin interfaz: revalorar un presupuesto con una lista de precios nueva (RM-1, ola 2).

Movido de `ui/paginas/actualizacion.py` (la pagina de Streamlit y la ruta
`POST /presupuestos/revalorar` de la API llaman aqui, una sola logica). No importa `streamlit`,
`ui`, `api`, `scripts` ni `tests`. Los avisos que la pagina pintaba con `st.warning` y `st.info`
salen como `Aviso`; el detector de atipicos y el responsable llegan como parametros, porque son
de quien llama (la pagina los toma de la sesion de Streamlit; la API, de la sesion web o de la
clave).

El nucleo deja la transaccion abierta a proposito: `revalorar` **confirma** cuando algun insumo
cambio de precio (UC-02, flujos 3a y 7a) y, si ninguno cambio, no confirma: la sesion que la llama
se cierra sin guardar la version ni las altas.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select

from core import models
from core.budget import (
    Comparativo,
    DetectorAtipicos,
    actualizar_precios,
    descartar_version,
    plan_de_version,
)
from core.catalog import PrecioLeido, crear_lista_desde_archivo, insumos_desconocidos
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from core.budget import ResultadoElaboracion

CERO = Decimal(0)

#: Columnas del comparativo que se presentan con los dos decimales del sistema.
COLUMNAS_NUMERICAS = (
    "cantidad",
    "pu_anterior",
    "pu_nuevo",
    "variacion_pct",
    "total_anterior",
    "total_nuevo",
    "incidencia_pct",
)


@dataclass(frozen=True, slots=True)
class Aviso:
    """Un mensaje para la persona: `advertencia` (lo que no se hizo) o `info`."""

    nivel: Literal["info", "advertencia"]
    texto: str


# `eq=False` por el mismo motivo que en `Comparativo`: lleva un `DataFrame` dentro.
@dataclass(frozen=True, slots=True, eq=False)
class Revaloracion:
    """Lo que dejo `revalorar`, para que la pantalla lo muestre."""

    nuevo: ResultadoElaboracion
    comparativo: Comparativo
    resumen: str
    #: Los insumos desconocidos que no se eligieron para el alta: ignorados (UC-02, flujo 2a).
    ignorados: tuple[str, ...]
    #: Las filas cuyo insumo esta en el catalogo con otra unidad: rechazadas (UC-02, flujo 2b).
    rechazados: tuple[str, ...]
    #: Los elegidos que quedaron en el catalogo; vacio si no se guardo la version.
    dados_de_alta: tuple[str, ...]
    #: El codigo de la version que esta ejecucion confirmo; `None` si no se guardo (UC-02 3a).
    version_guardada: str | None
    avisos: tuple[Aviso, ...]


def nombrar(leido: PrecioLeido) -> str:
    """Una fila del archivo como la lee el usuario: descripcion, tipo y unidad."""
    return f"{leido.descripcion} ({leido.tipo.value}, {leido.unidad or 'sin unidad'})"


def resumen_de(comparativo: Comparativo, moneda: str) -> str:
    anterior = formatear_decimal(comparativo.total_anterior, DECIMALES_PRESENTACION)
    nuevo = formatear_decimal(comparativo.total_nuevo, DECIMALES_PRESENTACION)
    variacion = formatear_decimal(comparativo.variacion, DECIMALES_PRESENTACION)
    porcentaje = formatear_decimal(comparativo.variacion_pct, DECIMALES_PRESENTACION)
    return f"{anterior} -> {nuevo} {moneda}  ({variacion} {moneda}, {porcentaje} %)"


def detector_de_atipicos() -> DetectorAtipicos | None:
    """`ml.anomaly.precios_atipicos`, o `None` sin el extra `ml` (UC-07, paso 5).

    Import perezoso: `core` no importa `ml`. Sin `scikit-learn` el detector aborta con
    `ModuleNotFoundError` dentro de `actualizar_precios`, asi que se pregunta antes por `sklearn`.
    """
    if importlib.util.find_spec("sklearn") is None:
        return None
    try:
        from ml.anomaly import precios_atipicos
    except ImportError:
        return None
    return precios_atipicos


def revalorar(
    sesion: Session,
    parametros: Mapping[str, object],
    archivo: Path,
    *,
    dar_de_alta: Collection[PrecioLeido] = (),
    detector: DetectorAtipicos | None = None,
    usuario: str,
) -> Revaloracion:
    """Crea la lista, revalora, confirma si algun insumo cambio de precio y arma el resultado.

    `parametros`: `proyecto`, `codigo` (base), `codigo_nuevo`, `nombre` y `moneda` de la lista y
    `vigencia`. `dar_de_alta` son las filas de la vista previa que se eligieron (flujo 2a).
    """
    # La vista previa se toma antes de crear la lista: despues, los dados de alta ya no son
    # desconocidos. Lo que la carga no uso y la vista previa no ofrecia es el flujo 2b.
    ofrecidos = insumos_desconocidos(sesion, archivo)
    resumen = crear_lista_desde_archivo(
        sesion,
        archivo,
        nombre=str(parametros["nombre"]),
        moneda=str(parametros["moneda"]),
        fecha_vigencia=parametros["vigencia"],
        origen=archivo.name,
        dar_de_alta=dar_de_alta,
    )
    dados_de_alta = tuple(
        f"{insumo.descripcion} ({insumo.codigo})" for insumo in resumen.dados_de_alta
    )
    origen = sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(
            models.Proyecto.nombre == str(parametros["proyecto"]),
            models.Presupuesto.codigo == str(parametros["codigo"]),
        )
    ).one_or_none()
    nuevo, comparativo = actualizar_precios(
        sesion,
        str(parametros["proyecto"]),
        str(parametros["codigo"]),
        resumen.lista,
        str(parametros["codigo_nuevo"]),
        detectar_atipicos=detector,
        # SF3 (RF-56, SF3-R4): revalorar conserva el plan guardado de la version de origen
        plan=None if origen is None else plan_de_version(sesion, origen),
        usuario=usuario,  # RF-82: quien confirma lo sella en la cadena
    )

    avisos: list[Aviso] = []
    if comparativo.insumos_afectados == 0:
        # Ningun insumo cambio de precio: no hay nada que guardar (UC-02, flujo 3a). No confirmar
        # descarta tambien la lista nueva, identica a la anterior en sus precios.
        texto = "Ningun precio cambio: no se guardo una version nueva (UC-02, flujo 3a)."
        if dados_de_alta:
            texto += (
                " Los insumos elegidos para el alta tampoco se guardaron: "
                + ", ".join(dados_de_alta)
                + "."
            )
        avisos.append(Aviso("advertencia", texto))
        sesion.rollback()  # la lista nueva y las altas no se guardan (el llamador puede seguir)
        version_guardada = None
        dados_de_alta = ()
    else:
        # Algun insumo cambio de precio, pero eso no implica que el presupuesto varie: si el
        # insumo no participa de ninguna de sus partidas, `variacion` da cero.
        if comparativo.variacion == CERO:
            avisos.append(
                Aviso(
                    "info",
                    "Cambiaron precios de insumos que no afectan a este presupuesto: se guardo la "
                    "version nueva y su historial de cambios, pero el total no vario.",
                )
            )
        sesion.commit()
        version_guardada = str(parametros["codigo_nuevo"])

    return Revaloracion(
        nuevo=nuevo,
        comparativo=comparativo,
        resumen=resumen_de(comparativo, nuevo.presupuesto.moneda),
        ignorados=tuple(nombrar(d) for d in resumen.desconocidos if d in ofrecidos),
        rechazados=tuple(nombrar(d) for d in resumen.desconocidos if d not in ofrecidos),
        dados_de_alta=dados_de_alta,
        version_guardada=version_guardada,
        avisos=tuple(avisos),
    )


def descartar(sesion: Session, proyecto: str, codigo: str, fecha: date) -> None:
    """UC-02 7a: marca la version `codigo` como descartada y confirma; su historial se conserva."""
    descartar_version(sesion, proyecto, codigo, fecha)
    sesion.commit()
