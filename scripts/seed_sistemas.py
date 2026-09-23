"""Carga el catálogo de sistemas (puntos de función) en SQLite y arma su presupuesto (Sesión M3.2).

Hermano de `scripts/seed.py`, `scripts/seed_telecom.py` y `scripts/seed_industrial.py` y, como
ellos, el único módulo fuera de `tests/` que importa su fixture:
`tests/fixtures/tarifas_sistemas.py` es la única copia de las tarifas (leídas del tabulador CIV
jul‑2026 estructurado en M0.2) y del APU de un punto de función. Aquí **no se escribe ningún
precio**.

Uso::

    uv run python scripts/seed_sistemas.py                 # crea data/apu_sistemas.db
    uv run python scripts/seed_sistemas.py --db /tmp/x.db  # otra ruta
    uv run python scripts/seed_sistemas.py --reiniciar     # borra el esquema y lo vuelve a crear

Flujo de extremo a extremo (compuerta GM3)
==========================================

1. `AdaptadorSistemas` (`adapters/sistemas`) extrae de `alcance_funcional.csv` un `ItemComputo` por
   caso de uso: cantidad = puntos de función no ajustados con la regla IFPUG declarada
   (`REGLA_PUNTOS_FUNCION`), unidad `pf`, `origen_id` = id del caso de uso.
2. `composiciones_sistemas` crea, para cada caso de uso, la partida `SIS-*` con el APU de un punto
   de función del fixture (`composicion_para`): mismas líneas de mano de obra bajo el código y la
   descripción del caso de uso, porque el alcance funcional no aporta datos para diferenciar la
   productividad por módulo sin inventarla.
3. `sembrar_sistemas` persiste proyecto, lista de precios (tabulador CIV al 01/07/2026) y las nueve
   composiciones con `core.catalog.Catalogo`. `presupuesto_sistemas` las reconstruye desde SQLite y
   las valora con `core.costing.calcular_apu` vía `core.budget.generar_presupuesto`, con
   `PARAMETROS_SISTEMAS` (sin prestaciones ni bono: honorarios profesionales, supuesto declarado).
4. La auditoría (`core.verification.auditar`) reevalúa la regla IFPUG (R1) y acepta la unidad `pf`
   (R3); UC‑02 carga `data/sistemas/fuentes/lista_tarifas_2026-07.csv`. Lo ejercen
   `tests/integration/test_presupuesto_sistemas.py` y el CLI.

Supuestos (todos `SUPUESTO (pendiente validacion del autor)`): jornada de 8 h, correspondencia
rol ↔ fila del tabulador, productividad 8 HH/PF (benchmark ISBSG, cita pendiente), reparto de
horas por rol y estructura de costos sin FCAS ni bono. Declarados en
`data/sistemas/fuentes/README.md` y en el docstring del fixture.
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

from adapters.sistemas import AdaptadorSistemas  # noqa: E402
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
from tests.fixtures import tarifas_sistemas as sis  # noqa: E402

FECHA_TABULADOR = sis.FECHA_TABULADOR
MONEDA = sis.MONEDA
NOMBRE_PROYECTO = "Sistema de gestion de presupuestos APU: alcance funcional por puntos de funcion"
DESCRIPCION_PROYECTO = (
    "Nueve casos de uso de data/samples/sistemas/alcance_funcional.csv (Presupuestos, Catalogo, "
    "Verificacion), medidos en puntos de funcion IFPUG y costeados con el tabulador CIV jul-2026"
)
NOMBRE_LISTA = "Tabulador CIV 2026-07 (sistemas)"
ORIGEN_LISTA = "data/precios/maprex_2026-07/referencia_sistemas.csv"
#: RF-33 (spec §3.3): declara que este rendimiento no viene de una ejecucion medida.
CONDICIONES_RENDIMIENTO = (
    "rendimiento estimado del caso didactico SIS-001; no proviene de una ejecucion medida"
)
#: El alcance funcional no numera presupuestos; el prefijo lo distingue de 001, TC-* y MNT-*.
CODIGO_PRESUPUESTO = "SIS-001"
RUTA_ALCANCE = RAIZ / "data" / "samples" / "sistemas" / "alcance_funcional.csv"
RUTA_LISTA_CANONICA = RAIZ / "data" / "sistemas" / "fuentes" / "lista_tarifas_2026-07.csv"
RUTA_POR_DEFECTO = "data/apu_sistemas.db"


# ---------------------------------------------------------------------------------------------
# Del adaptador a los ítems y las composiciones
# ---------------------------------------------------------------------------------------------


def items_sistemas(ruta: Path = RUTA_ALCANCE) -> list[ItemComputo]:
    """Un ítem por caso de uso, en el orden del CSV; los códigos de partida deben ser únicos."""
    items = AdaptadorSistemas().extraer(ruta)
    codigos = [item.codigo_partida for item in items]
    repetidos = sorted({codigo for codigo in codigos if codigos.count(codigo) > 1})
    if repetidos:
        raise ValueError(f"{ruta.name}: codigos de partida repetidos: {repetidos}")
    return items


def composiciones_sistemas(items: Sequence[ItemComputo] | None = None) -> dict[str, ComposicionAPU]:
    """El APU de un punto de función bajo el código y la descripción de cada caso de uso."""
    return {
        item.codigo_partida: sis.composicion_para(item.codigo_partida, item.descripcion)
        for item in (items if items is not None else items_sistemas())
    }


# ---------------------------------------------------------------------------------------------
# Persistencia: catálogo de sistemas en SQLite
# ---------------------------------------------------------------------------------------------


def sembrar_sistemas(sesion: Session) -> models.Proyecto:
    """Carga proyecto, lista de tarifas del tabulador CIV y las partidas `SIS-*`. Idempotente."""
    proyecto = sesion.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == NOMBRE_PROYECTO)
    ).one_or_none()
    if proyecto is not None:
        return proyecto

    proyecto = models.Proyecto(
        nombre=NOMBRE_PROYECTO,
        descripcion=DESCRIPCION_PROYECTO,
        dominio=str(Dominio.SISTEMAS),
    )
    lista = models.ListaPrecios(
        nombre=NOMBRE_LISTA,
        moneda=MONEDA,
        fecha_vigencia=FECHA_TABULADOR,
        origen=ORIGEN_LISTA,
    )
    sesion.add_all((proyecto, lista))
    sesion.flush()

    catalogo = Catalogo(sesion)
    for composicion in composiciones_sistemas().values():
        catalogo.cargar_composicion(
            composicion, lista, Dominio.SISTEMAS, FECHA_TABULADOR, CONDICIONES_RENDIMIENTO
        )

    sesion.commit()
    return proyecto


def lista_sistemas(sesion: Session) -> models.ListaPrecios:
    """La lista de tarifas del tabulador CIV, por nombre (conviven listas de otros dominios)."""
    lista = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == NOMBRE_LISTA)
    ).one_or_none()
    if lista is None:
        raise CatalogoIncompleto(
            f"no hay lista de precios {NOMBRE_LISTA!r} en la base: corra sembrar_sistemas primero"
        )
    return lista


def composiciones_desde_catalogo(
    sesion: Session, lista: models.ListaPrecios | None = None
) -> dict[str, ComposicionAPU]:
    """Reconstruye los APU `SIS-*` desde SQLite con los precios de `lista` (o la del tabulador)."""
    catalogo = Catalogo(sesion)
    lista = lista if lista is not None else lista_sistemas(sesion)
    return {
        item.codigo_partida: catalogo.composicion(
            item.codigo_partida, fecha=FECHA_TABULADOR, lista=lista
        )
        for item in items_sistemas()
    }


def presupuesto_sistemas(
    sesion: Session,
    items: Sequence[ItemComputo] | None = None,
    lista: models.ListaPrecios | None = None,
    parametros: ParametrosCosto = sis.PARAMETROS_SISTEMAS,
) -> Presupuesto:
    """El presupuesto del alcance funcional: PF de cada caso de uso × APU reconstruido del catálogo.

    `items` permite auditar un cómputo alterado (las pruebas lo usan para comprobar que R1 muerde).
    """
    return generar_presupuesto(
        list(items) if items is not None else items_sistemas(),
        composiciones_desde_catalogo(sesion, lista),
        parametros,
        codigo=CODIGO_PRESUPUESTO,
        fecha=FECHA_TABULADOR,
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
            proyecto = sembrar_sistemas(sesion)
            _imprimir_resumen(sesion, ruta, proyecto)
    finally:
        motor.dispose()
    return 0


def _imprimir_resumen(sesion: Session, ruta: Path, proyecto: models.Proyecto) -> None:
    lista = lista_sistemas(sesion)
    presupuesto = presupuesto_sistemas(sesion)
    informe = auditar(presupuesto)
    print(f"Base de datos: {ruta}")
    print(f"Proyecto: {proyecto.nombre} ({proyecto.dominio})")
    print(
        f"Lista de precios: {lista.nombre} ({lista.moneda}, vigente desde {lista.fecha_vigencia})"
    )
    print(
        f"Productividad: {sis.PRODUCTIVIDAD_HH_PF:f} HH/PF "
        "(SUPUESTO, pendiente validacion del autor)"
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


if __name__ == "__main__":
    raise SystemExit(main())
