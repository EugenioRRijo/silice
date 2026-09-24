"""Carga la línea base auditada en SQLite para reproducir el presupuesto desde la base de datos.

Este script es el **único** módulo fuera de `tests/` que importa `tests.fixtures.apu_linea_base`, y
lo hace a propósito: ese fixture es la única copia de la línea base en todo el sistema (CLAUDE.md
§2, principio DRY). Duplicar aquí los cinco APU sería exactamente lo que el principio prohíbe.

Uso:
    uv run python scripts/seed.py                 # crea data/apu.db
    uv run python scripts/seed.py --db /tmp/x.db  # otra ruta
    uv run python scripts/seed.py --db /tmp/x.db --reiniciar     # reinicia otra base
    uv run python scripts/seed.py --reiniciar --confirmar       # reinicia la base por defecto
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

# Ejecutado como `python scripts/seed.py`, sys.path[0] es scripts/, no la raíz del repositorio, y
# `core` no se resuelve (pyproject declara `package = false`: no hay instalación que lo exponga).
# pytest lo arregla con `pythonpath = ["."]`; aquí se hace explícito antes de importar el núcleo.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from core import models  # noqa: E402
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor  # noqa: E402
from core.contracts import Presupuesto  # noqa: E402
from core.contracts.dominio import Dominio  # noqa: E402
from core.verification import InformeAuditoria  # noqa: E402
from core.verification.informe import DECIMALES_PRESENTACION  # noqa: E402
from core.verification.texto import formatear_decimal  # noqa: E402
from tests.fixtures import apu_linea_base as linea_base  # noqa: E402

NOMBRE_PROYECTO = "Drenaje de la clínica"
DESCRIPCION_PROYECTO = (
    "Obra civil del drenaje de una clínica: 24 m de tubería PVC de 4 pulgadas y cuatro "
    "tanquillas de 0,80 x 0,80 x 0,80 m con paredes de 0,10 m"
)
ORIGEN_LISTA = "APUS_CLINICA.pdf"
RUTA_POR_DEFECTO = "data/apu.db"

#: Condiciones bajo las que se estimo cada rendimiento de la linea base.
#:
#: Son supuestos declarados de un caso didactico, no mediciones de obra ejecutada: nadie cronometro
#: una cuadrilla real. Se escriben para que la siembra de la base sea trazable, siguiendo la misma
#: exigencia que la pantalla de composicion (fase P2) le hara a cualquier rendimiento nuevo.
CONDICIONES_LINEA_BASE: dict[str, str] = {
    "LB-01-EXC": (
        "cuadrilla de cinco obreros (operador de equipo y dos choferes incluidos), excavacion "
        "mecanizada con retroexcavadora y acarreo en camion de volteo"
    ),
    "LB-02-TUB": "cuadrilla de tres obreros, tuberia PVC de 4 pulgadas, zanja abierta y nivelada",
    "LB-03-ENC": "cuadrilla de cuatro obreros, encofrado de madera reutilizable, paredes rectas",
    "LB-04-CON": (
        "cuadrilla de seis obreros, concreto dosificado y mezclado en sitio con mezcladora, "
        "consolidado con vibrador de concreto"
    ),
    "LB-05-REL": (
        "cuadrilla de seis obreros, material granular en sitio, compactacion mecanizada con "
        "compactadora tipo sapo y agua para control de humedad"
    ),
}

_TABLAS_DEL_RESUMEN = (
    models.Partida,
    models.Insumo,
    models.PrecioInsumo,
    models.ComposicionAPU,
    models.Rendimiento,
)


def sembrar(sesion: Session) -> models.Proyecto:
    """Carga proyecto, lista de precios y los cinco APU. Idempotente: si ya está, no duplica."""
    proyecto = sesion.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == NOMBRE_PROYECTO)
    ).one_or_none()
    if proyecto is not None:
        return proyecto

    proyecto = models.Proyecto(
        nombre=NOMBRE_PROYECTO,
        descripcion=DESCRIPCION_PROYECTO,
        dominio=str(Dominio.CIVIL),
    )
    lista = models.ListaPrecios(
        nombre=f"Linea base {linea_base.FECHA_LINEA_BASE:%d/%m/%Y}",
        moneda=linea_base.MONEDA,
        fecha_vigencia=linea_base.FECHA_LINEA_BASE,
        origen=ORIGEN_LISTA,
    )
    sesion.add_all((proyecto, lista))
    sesion.flush()

    catalogo = Catalogo(sesion)
    for apu in linea_base.APUS_LINEA_BASE:
        catalogo.cargar_composicion(
            apu,
            lista,
            Dominio.CIVIL,
            linea_base.FECHA_LINEA_BASE,
            CONDICIONES_LINEA_BASE[apu.codigo_partida],
        )

    sesion.commit()
    return proyecto


def motivo_para_no_reiniciar(
    ruta: str, reiniciar: bool, confirmar: bool, por_defecto: str
) -> str | None:
    """Por que no se debe reiniciar `ruta`, o `None` si se puede (INV-050).

    `--reiniciar` borra todas las tablas. Sobre la base por defecto (la de trabajo, la que abre la
    aplicacion) exige ademas `--confirmar`; sobre cualquier otra ruta pasada con `--db` basta
    `--reiniciar`. Las rutas se comparan resueltas, asi que `--db data/apu.db` explicito tambien
    cuenta como la ruta por defecto.
    """
    if not reiniciar or confirmar:
        return None
    if Path(ruta).resolve() != Path(por_defecto).resolve():
        return None
    return (
        f"--reiniciar borraria todas las tablas de la base por defecto ({por_defecto}). "
        "Repita la orden con --confirmar si de verdad quiere vaciarla, o use --db <ruta> para "
        "reiniciar otra base."
    )


# ---------------------------------------------------------------------------------------------
# Resumen impreso de los sembradores (INV-049): una sola forma de redondear y de listar
# ---------------------------------------------------------------------------------------------


def monto(valor: Decimal) -> str:
    """Un monto como texto, con la fuente unica de presentacion (`formatear_decimal` con
    `DECIMALES_PRESENTACION`, `ROUND_HALF_UP`), no con `:.2f`, que redondea al par (INV-049)."""
    return formatear_decimal(valor, DECIMALES_PRESENTACION)


def lineas_presupuesto(presupuesto: Presupuesto, moneda: str) -> list[str]:
    """Encabezado, una linea por partida y el total: lo comun al `resumen` de los sembradores."""
    lineas = [f"Presupuesto {presupuesto.codigo} ({len(presupuesto.partidas)} partidas):"]
    lineas += [
        f"  {partida.item.codigo_partida} [{partida.item.origen_id}] "
        f"{partida.item.cantidad:f} {partida.item.unidad} x "
        f"{monto(partida.resultado.precio_unitario)} = {monto(partida.total)} {moneda}"
        for partida in presupuesto.partidas
    ]
    lineas.append(f"  Total: {monto(presupuesto.total)} {moneda}")
    return lineas


def linea_auditoria(informe: InformeAuditoria) -> str:
    """La linea del informe de auditoria, que todo resumen imprime (principio 7, CLAUDE.md §2)."""
    return (
        f"Auditoria: {len(informe.hallazgos)} hallazgo(s), "
        f"{'CUMPLE' if informe.cumple else 'NO CUMPLE'}"
    )


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
    analizador.add_argument(
        "--confirmar",
        action="store_true",
        help="necesario para --reiniciar sobre la ruta por defecto (INV-050)",
    )
    argumentos = analizador.parse_args(argv)
    motivo = motivo_para_no_reiniciar(
        argumentos.db, argumentos.reiniciar, argumentos.confirmar, RUTA_POR_DEFECTO
    )
    if motivo is not None:
        print(motivo, file=sys.stderr)
        return 2

    ruta = Path(argumentos.db)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        if argumentos.reiniciar:
            models.Base.metadata.drop_all(motor)
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar(sesion)
            _imprimir_resumen(sesion, ruta, proyecto)
    finally:
        motor.dispose()
    return 0


def _imprimir_resumen(sesion: Session, ruta: Path, proyecto: models.Proyecto) -> None:
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)

    print(f"Base de datos: {ruta}")
    print(f"Proyecto: {proyecto.nombre} ({proyecto.dominio})")
    print(
        f"Lista de precios: {lista.nombre} ({lista.moneda}, vigente desde {lista.fecha_vigencia})"
    )
    conteos = " | ".join(
        f"{tabla.__name__}: {sesion.scalar(select(func.count()).select_from(tabla))}"
        for tabla in _TABLAS_DEL_RESUMEN
    )
    print(conteos)

    print("Partidas cargadas:")
    for partida in catalogo.partidas():
        composicion = catalogo.composicion(partida.codigo, fecha=linea_base.FECHA_LINEA_BASE)
        print(
            f"  {partida.codigo}  {partida.unidad:<6} rendimiento {composicion.rendimiento:>4}"
            f"  materiales {len(composicion.materiales)}"
            f"  equipos {len(composicion.equipos)}"
            f"  mano de obra {len(composicion.mano_obra)}"
        )

    variantes = sesion.execute(
        select(models.Insumo.descripcion)
        .group_by(models.Insumo.tipo, models.Insumo.descripcion)
        .having(func.count(models.Insumo.id) > 1)
        .order_by(models.Insumo.descripcion)
    ).scalars()
    print(
        "Insumos homonimos cargados como variantes (hallazgo, docs/modelo_datos.md seccion 6): "
        + ", ".join(variantes)
    )


if __name__ == "__main__":
    raise SystemExit(main())
