"""Carga el catálogo de mantenimiento industrial en SQLite y arma su presupuesto (Sesión M2.2).

Hermano de `scripts/seed.py` (civil) y `scripts/seed_telecom.py` (telecom) y, como ellos, el único
módulo fuera de `tests/` que importa su fixture: `tests/fixtures/mantenimiento_industrial.py` es
la única copia de las cuatro composiciones `MNT-*`, y a su vez lee los precios de
`data/precios/maprex_2026-07/referencia_industrial.csv`. Aquí **no se escribe ningún precio**.

Uso::

    uv run python scripts/seed_industrial.py                 # crea data/apu_industrial.db
    uv run python scripts/seed_industrial.py --db /tmp/x.db  # otra ruta
    uv run python scripts/seed_industrial.py --reiniciar     # borra el esquema y lo vuelve a crear

Flujo de extremo a extremo (compuerta GM2)
==========================================

1. `AdaptadorIndustrial` (`adapters/industrial`) extrae de `activos_planta.csv` un `ItemComputo`
   por activo: cantidad = ``frecuencia_anual x horizonte_anios`` intervenciones, con la regla
   declarada (`REGLA_INTERVENCIONES`) y `origen_id` = `id_activo`.
2. `items_industrial` se queda con los activos que tienen partida en el catálogo
   (`ACTIVOS_COSTEADOS` del fixture: cuatro activos rotativos) y comprueba que el `id_activo` del
   CSV es el que el fixture declara para esa partida. Los otros seis activos no se silencian:
   `items_sin_catalogo` los devuelve para que el CLI y las pruebas los declaren.
3. `sembrar_industrial` persiste proyecto, lista de precios (la referencia MaPreX jul‑2026) y las
   cuatro composiciones con `core.catalog.Catalogo`. `presupuesto_industrial` las reconstruye
   desde SQLite y las valora con `core.costing.calcular_apu` vía `core.budget.generar_presupuesto`.
4. La auditoría (`core.verification.auditar`) reevalúa la regla de intervenciones (R1) y UC‑02
   carga `data/industrial/fuentes/lista_maprex_2026-07.csv`; ambas cosas las ejercen
   `tests/integration/test_presupuesto_industrial.py` y el CLI.

Degradación GM2 declarada
-------------------------
Los precios son el proxy fechado MaPreX julio 2026, no cotizaciones de campo
(`data/industrial/fuentes/README.md`, PLAN_MULTIDOMINIO §2). Los supuestos de alcance,
rendimiento y estructura de costos están en el docstring del fixture.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

# Igual que en scripts/seed.py: ejecutado como `python scripts/...`, sys.path[0] es scripts/ y
# `core` no se resuelve (pyproject declara `package = false`).
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from adapters.industrial import AdaptadorIndustrial  # noqa: E402
from core import models  # noqa: E402
from core.budget import generar_presupuesto  # noqa: E402
from core.catalog import (  # noqa: E402
    Catalogo,
    CatalogoIncompleto,
    abrir_sesion,
    crear_esquema,
    crear_motor,
)
from core.contracts import (  # noqa: E402
    ComposicionAPU,
    Dominio,
    ItemComputo,
    ParametrosCosto,
    Presupuesto,
)
from core.verification import auditar  # noqa: E402
from tests.fixtures import mantenimiento_industrial as mnt  # noqa: E402

FECHA_REFERENCIA = mnt.FECHA_REFERENCIA
MONEDA = mnt.MONEDA
NOMBRE_PROYECTO = "Planta industrial: mantenimiento preventivo de activos rotativos"
DESCRIPCION_PROYECTO = (
    "Intervenciones de mantenimiento de cuatro activos rotativos de data/samples/industrial/"
    "activos_planta.csv, costeadas con la referencia MaPreX jul-2026 (degradacion GM2 declarada)"
)
NOMBRE_LISTA = "Referencia MaPreX 2026-07 (industrial)"
ORIGEN_LISTA = "data/precios/maprex_2026-07/referencia_industrial.csv"
#: RF-33 (spec §3.3): declara que este rendimiento no viene de una ejecucion medida.
CONDICIONES_RENDIMIENTO = (
    "rendimiento estimado del caso didactico MNT-001; no proviene de una ejecucion medida"
)
#: El registro de activos no numera presupuestos; el prefijo lo distingue del 001 civil y TC-*.
CODIGO_PRESUPUESTO = "MNT-001"
RUTA_ACTIVOS = RAIZ / "data" / "samples" / "industrial" / "activos_planta.csv"
RUTA_LISTA_CANONICA = RAIZ / "data" / "industrial" / "fuentes" / "lista_maprex_2026-07.csv"
RUTA_POR_DEFECTO = "data/apu_industrial.db"


# ---------------------------------------------------------------------------------------------
# Del adaptador a los ítems del presupuesto
# ---------------------------------------------------------------------------------------------


def _extraer(ruta: Path) -> list[ItemComputo]:
    return AdaptadorIndustrial().extraer(ruta)


def items_industrial(ruta: Path = RUTA_ACTIVOS) -> list[ItemComputo]:
    """Los ítems del registro que tienen partida en el catálogo, en el orden del CSV.

    Comprueba que el `id_activo` del CSV es el que el fixture declara para esa partida: si el
    registro cambiara de activo bajo el mismo código, el APU dejaría de describir lo que se costea.
    """
    items = [item for item in _extraer(ruta) if item.codigo_partida in mnt.ACTIVOS_COSTEADOS]
    for item in items:
        esperado = mnt.ACTIVOS_COSTEADOS[item.codigo_partida]
        if item.origen_id != esperado:
            raise ValueError(
                f"{item.codigo_partida}: el registro trae el activo {item.origen_id} y el "
                f"catalogo describe {esperado}"
            )
    faltantes = set(mnt.ACTIVOS_COSTEADOS) - {item.codigo_partida for item in items}
    if faltantes:
        raise ValueError(f"{ruta.name} no trae las partidas del catalogo: {sorted(faltantes)}")
    return items


def items_sin_catalogo(ruta: Path = RUTA_ACTIVOS) -> list[ItemComputo]:
    """Los activos del registro sin partida en el catálogo (pendientes de cotización)."""
    return [item for item in _extraer(ruta) if item.codigo_partida not in mnt.ACTIVOS_COSTEADOS]


# ---------------------------------------------------------------------------------------------
# Persistencia: catálogo industrial en SQLite
# ---------------------------------------------------------------------------------------------


def sembrar_industrial(sesion: Session) -> models.Proyecto:
    """Carga proyecto, lista de precios MaPreX y las cuatro partidas `MNT-*`. Idempotente."""
    proyecto = sesion.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == NOMBRE_PROYECTO)
    ).one_or_none()
    if proyecto is not None:
        return proyecto

    proyecto = models.Proyecto(
        nombre=NOMBRE_PROYECTO,
        descripcion=DESCRIPCION_PROYECTO,
        dominio=str(Dominio.INDUSTRIAL),
    )
    lista = models.ListaPrecios(
        nombre=NOMBRE_LISTA,
        moneda=MONEDA,
        fecha_vigencia=FECHA_REFERENCIA,
        origen=ORIGEN_LISTA,
    )
    sesion.add_all((proyecto, lista))
    sesion.flush()

    catalogo = Catalogo(sesion)
    for composicion in mnt.COMPOSICIONES_MNT.values():
        catalogo.cargar_composicion(
            composicion, lista, Dominio.INDUSTRIAL, FECHA_REFERENCIA, CONDICIONES_RENDIMIENTO
        )

    sesion.commit()
    return proyecto


def lista_industrial(sesion: Session) -> models.ListaPrecios:
    """La lista de precios de referencia industrial, por nombre (no por fecha: conviven listas
    civil, telecom y MaPreX en la misma base)."""
    lista = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == NOMBRE_LISTA)
    ).one_or_none()
    if lista is None:
        raise CatalogoIncompleto(
            f"no hay lista de precios {NOMBRE_LISTA!r} en la base: corra sembrar_industrial primero"
        )
    return lista


def composiciones_desde_catalogo(
    sesion: Session, lista: models.ListaPrecios | None = None
) -> dict[str, ComposicionAPU]:
    """Reconstruye los APU `MNT-*` desde SQLite con los precios de `lista` (o la de referencia)."""
    catalogo = Catalogo(sesion)
    lista = lista if lista is not None else lista_industrial(sesion)
    return {
        codigo: catalogo.composicion(codigo, fecha=FECHA_REFERENCIA, lista=lista)
        for codigo in mnt.ACTIVOS_COSTEADOS
    }


def presupuesto_industrial(
    sesion: Session,
    items: Sequence[ItemComputo] | None = None,
    lista: models.ListaPrecios | None = None,
    parametros: ParametrosCosto = mnt.PARAMETROS_INDUSTRIAL,
) -> Presupuesto:
    """El presupuesto de mantenimiento: ítems del adaptador × APU reconstruidos del catálogo.

    `items` permite auditar un cómputo alterado (las pruebas lo usan para comprobar que R1 muerde);
    por defecto son los del registro de activos.
    """
    return generar_presupuesto(
        list(items) if items is not None else items_industrial(),
        composiciones_desde_catalogo(sesion, lista),
        parametros,
        codigo=CODIGO_PRESUPUESTO,
        fecha=FECHA_REFERENCIA,
        moneda=MONEDA,
    )


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--db",
        default=RUTA_POR_DEFECTO,
        help=f"ruta del archivo SQLite (por defecto {RUTA_POR_DEFECTO})",
    )
    analizador.add_argument(
        "--reiniciar", action="store_true", help="borra el esquema antes de crearlo de nuevo"
    )
    argumentos = analizador.parse_args(argv)

    ruta = Path(argumentos.db)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        if argumentos.reiniciar:
            models.Base.metadata.drop_all(motor)
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar_industrial(sesion)
            _imprimir_resumen(sesion, ruta, proyecto)
    finally:
        motor.dispose()
    return 0


def _imprimir_resumen(sesion: Session, ruta: Path, proyecto: models.Proyecto) -> None:
    lista = lista_industrial(sesion)
    presupuesto = presupuesto_industrial(sesion)
    informe = auditar(presupuesto)
    print(f"Base de datos: {ruta}")
    print(f"Proyecto: {proyecto.nombre} ({proyecto.dominio})")
    print(
        f"Lista de precios: {lista.nombre} ({lista.moneda}, vigente desde {lista.fecha_vigencia}) "
        "- proxy MaPreX, degradacion GM2 declarada"
    )
    print(f"Presupuesto {presupuesto.codigo} ({len(presupuesto.partidas)} partidas):")
    for partida in presupuesto.partidas:
        print(
            f"  {partida.item.codigo_partida} [{partida.item.origen_id}] "
            f"{partida.item.cantidad:f} {partida.item.unidad} x "
            f"{partida.resultado.precio_unitario:.2f} = {partida.total:.2f} {MONEDA}"
        )
    print(f"  Total: {presupuesto.total:.2f} {MONEDA}")
    print(
        f"Auditoria: {len(informe.hallazgos)} hallazgo(s), "
        f"{'CUMPLE' if informe.cumple else 'NO CUMPLE'}"
    )
    pendientes = items_sin_catalogo()
    print(f"Activos sin partida en el catalogo (pendientes de cotizacion): {len(pendientes)}")
    for item in pendientes:
        print(f"  {item.origen_id} {item.codigo_partida}: {item.descripcion}")


if __name__ == "__main__":
    raise SystemExit(main())
