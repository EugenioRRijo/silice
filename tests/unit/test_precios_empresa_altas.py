"""La lista de la empresa con insumos que el catálogo no conoce (prueba de punta a punta del
2026-11-13, D-8, D-11).

Antes, `aplicacion.precios_empresa.crear_lista` dejaba fuera todo insumo que el catálogo no tenía
(«no entraron a la lista») sin ofrecer darlo de alta, y uno con la misma descripción y otra unidad
se perdía sin decir por qué. Decisión simulada (bitácora 2026-11-13-e2e-precios §3): revisar el
archivo antes de crear la lista (`revisar_archivo`, no escribe) y darlos de alta solo si la persona
lo confirma (`dar_de_alta=True`); los de otra unidad nunca se dan de alta (serían un homónimo) y se
dice cuál es la unidad del catálogo. Además (D-11) una fila sin fecha o sin fuente toma las de la
lista, que el formulario ya pide.

Datos FICTICIOS escritos a mano: cuatro insumos del catálogo y un archivo de seis filas (dos
conocidas, dos nuevas y dos con otra unidad). Base y lista en USD, sin conversión.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aplicacion import precios_empresa
from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor

FECHA = date(2026, 10, 5)
FUENTE = "cotización 17 (ficticia)"
#: (código, tipo, descripción, unidad, precio en USD) del catálogo ficticio.
INSUMOS = (
    ("MAT-001", "material", "Cemento de prueba", "kg", Decimal("0.90")),
    ("MAT-002", "material", "Arena de prueba", "m3", Decimal("20.00")),
    ("MO-001", "mano_obra", "Albañil de prueba", None, Decimal("8.00")),
    ("MO-002", "mano_obra", "Chofer de prueba", "jornada", Decimal("7.00")),
)
ARCHIVO = (
    "tipo,insumo,unidad,precio,fecha,fuente\n"
    "material,Cemento de prueba,kg,1.10,2026-10-05,cotización 17 (ficticia)\n"
    "mano_obra,Albañil de prueba,dia,9.00,2026-10-05,cotización 17 (ficticia)\n"
    "material,Bloque de prueba,und,0.80,2026-10-05,cotización 17 (ficticia)\n"
    "equipo,Retro de prueba,dia,150.00,2026-10-05,cotización 17 (ficticia)\n"
    "mano_obra,Chofer de prueba,dia,2.71,2026-10-05,cotización 17 (ficticia)\n"
    "material,Arena de prueba,saco,3.00,2026-10-05,cotización 17 (ficticia)\n"
)
OTRA_UNIDAD = (
    "«Chofer de prueba» viene en dia y el catálogo lo tiene en jornada: no entró; escriba en el "
    "archivo la unidad del catálogo.",
    "«Arena de prueba» viene en saco y el catálogo lo tiene en m3: no entró; escriba en el "
    "archivo la unidad del catálogo.",
)


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    try:
        with abrir_sesion(motor) as s:
            base = models.ListaPrecios(
                nombre="Base en USD", moneda="USD", fecha_vigencia=date(2026, 7, 1), origen=""
            )
            s.add(base)
            s.flush()
            for codigo, tipo, descripcion, unidad, precio in INSUMOS:
                insumo = models.Insumo(
                    codigo=codigo, tipo=tipo, descripcion=descripcion, unidad=unidad
                )
                s.add(insumo)
                s.flush()
                s.add(models.PrecioInsumo(lista_id=base.id, insumo_id=insumo.id, precio=precio))
            s.commit()
            yield s
    finally:
        motor.dispose()


@pytest.fixture
def archivo(tmp_path: Path) -> Path:
    ruta = tmp_path / "lista.csv"
    ruta.write_text(ARCHIVO, encoding="utf-8")
    return ruta


def _base(s: Session) -> int:
    return s.scalars(select(models.ListaPrecios.id)).one()


def _crear(s: Session, ruta: Path, **extra) -> precios_empresa.ResumenEmpresa:
    return precios_empresa.crear_lista(
        s,
        ruta,
        empresa_nombre="Empresa ficticia",
        empresa_rif="J-00000000-0",
        base_id=_base(s),
        moneda="USD",
        fecha=FECHA,
        fuente=FUENTE,
        nombre="",
        **extra,
    )


def _insumos(s: Session) -> int:
    return s.scalar(select(func.count()).select_from(models.Insumo))


def _precios_de_la_empresa(s: Session) -> dict[str, Decimal]:
    lista_id = s.scalars(select(models.ListaEmpresa.lista_id)).one()
    filas = s.execute(
        select(models.Insumo.descripcion, models.PrecioInsumo.precio)
        .join(models.PrecioInsumo, models.PrecioInsumo.insumo_id == models.Insumo.id)
        .where(models.PrecioInsumo.lista_id == lista_id)
    )
    return dict(filas.all())


def test_revisar_el_archivo_separa_conocidos_nuevos_y_otra_unidad_sin_escribir(
    sesion: Session, archivo: Path
) -> None:
    antes = (_insumos(sesion), sesion.scalar(select(func.count()).select_from(models.ListaPrecios)))
    revision = precios_empresa.revisar_archivo(sesion, archivo)
    assert revision.reconocidos == 2  # Cemento (kg = kg) y Albañil (mano de obra, sin unidad)
    assert [(n.tipo.value, n.descripcion, n.unidad) for n in revision.nuevos] == [
        ("material", "Bloque de prueba", "und"),
        ("equipo", "Retro de prueba", "dia"),
    ]
    assert revision.otra_unidad == OTRA_UNIDAD
    assert antes == (
        _insumos(sesion),
        sesion.scalar(select(func.count()).select_from(models.ListaPrecios)),
    )


def test_sin_confirmar_el_alta_los_nuevos_no_entran_y_se_dice_por_que_los_otros(
    sesion: Session, archivo: Path
) -> None:
    antes = _insumos(sesion)
    resumen = _crear(sesion, archivo)
    assert resumen.propios == 2
    assert resumen.dados_de_alta == ()
    assert resumen.desconocidos == (
        "Bloque de prueba",
        "Retro de prueba",
        "Chofer de prueba",
        "Arena de prueba",
    )
    assert resumen.otra_unidad == OTRA_UNIDAD
    assert _insumos(sesion) == antes


def test_con_el_alta_confirmada_los_nuevos_entran_con_su_precio_y_los_de_otra_unidad_no(
    sesion: Session, archivo: Path
) -> None:
    antes = _insumos(sesion)
    resumen = _crear(sesion, archivo, dar_de_alta=True)
    assert resumen.propios == 4
    assert resumen.dados_de_alta == ("Bloque de prueba", "Retro de prueba")
    assert resumen.desconocidos == ("Chofer de prueba", "Arena de prueba")
    assert resumen.otra_unidad == OTRA_UNIDAD
    assert _insumos(sesion) == antes + 2
    precios = _precios_de_la_empresa(sesion)
    assert precios["Bloque de prueba"] == Decimal("0.80")
    assert precios["Retro de prueba"] == Decimal("150.00")
    assert precios["Cemento de prueba"] == Decimal("1.10")
    assert precios["Arena de prueba"] == Decimal("20.00")  # heredado: el de «saco» no entró
    # los dados de alta son insumos del catálogo con código nuevo de su tipo
    bloque = sesion.scalars(
        select(models.Insumo).where(models.Insumo.descripcion == "Bloque de prueba")
    ).one()
    assert (bloque.codigo, bloque.tipo, bloque.unidad) == ("MAT-003", "material", "und")


def test_dos_filas_nuevas_del_mismo_insumo_con_precios_distintos_no_crean_nada(
    sesion: Session, tmp_path: Path
) -> None:
    ruta = tmp_path / "doble.csv"
    ruta.write_text(
        "tipo,insumo,unidad,precio,fecha,fuente\n"
        "material,Bloque de prueba,und,0.80,2026-10-05,x\n"
        "material,Bloque de prueba,und,0.85,2026-10-05,x\n",
        encoding="utf-8",
    )
    antes = _insumos(sesion)
    with pytest.raises(ValueError) as error:
        _crear(sesion, ruta, dar_de_alta=True)
    assert str(error.value) == (
        "«Bloque de prueba» viene dos veces con precios distintos (0,80 y 0,85): deje una fila."
    )
    assert _insumos(sesion) == antes
    assert sesion.scalars(select(models.ListaEmpresa)).first() is None


def test_una_fila_sin_fecha_ni_fuente_toma_las_de_la_lista(sesion: Session, tmp_path: Path) -> None:
    """D-11: el formulario ya pide la fecha y la fuente de la lista; la fila no las repite."""
    ruta = tmp_path / "sin_fecha.csv"
    ruta.write_text("tipo,insumo,unidad,precio\nmaterial,Cemento de prueba,kg,1.10\n", "utf-8")
    resumen = _crear(sesion, ruta)
    assert resumen.propios == 1
    origen = sesion.scalars(
        select(models.PrecioOrigen)
        .join(models.PrecioInsumo, models.PrecioInsumo.id == models.PrecioOrigen.precio_id)
        .join(models.ListaEmpresa, models.ListaEmpresa.lista_id == models.PrecioInsumo.lista_id)
        .join(models.Insumo, models.Insumo.id == models.PrecioInsumo.insumo_id)
        .where(models.Insumo.codigo == "MAT-001")
    ).one()
    assert (origen.fecha_precio, origen.fuente) == (FECHA, FUENTE)
