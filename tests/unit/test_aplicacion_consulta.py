"""`aplicacion.consulta.buscar`: autocompletado sobre las tablas venezolanas (plan vial, Tarea 20).

Tablas: partidas viales (constantes de `adapters.vial`), insumos y salarios (el catálogo: materiales
y equipos por un lado, mano de obra por otro) y la tasa del BCV (serie `BCV-USD-VENTA`). Datos
ficticios; oráculos escritos a mano.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from aplicacion.consulta import TABLAS, Sugerencia, buscar
from core.catalog import abrir_sesion, crear_motor
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from core.models import Insumo
from operacion.base_datos import preparar_base


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator[Session]:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            s.add_all(
                [
                    Insumo(
                        codigo="MAT-1",
                        tipo="material",
                        descripcion="Cemento gris ficticio",
                        unidad="saco",
                    ),
                    Insumo(
                        codigo="MAT-2",
                        tipo="material",
                        descripcion="Arena lavada ficticia",
                        unidad="m3",
                    ),
                    Insumo(
                        codigo="EQ-1",
                        tipo="equipo",
                        descripcion="Compactador ficticio",
                        unidad="dia",
                    ),
                    Insumo(
                        codigo="MO-1",
                        tipo="mano_obra",
                        descripcion="Albañil de primera ficticio",
                        unidad="dia",
                    ),
                ]
            )
            registrar_importacion(
                s,
                definicion_tasa("venta"),
                [
                    Observacion(date(2026, 10, 29), Decimal("40.50")),
                    Observacion(date(2026, 10, 30), Decimal("41.25")),
                    Observacion(date(2026, 9, 30), Decimal("39.10")),
                ],
                archivo="tasas.xls",
                huella="a" * 64,
                fuente="BCV, archivo ficticio",
                fecha_descarga=date(2026, 10, 31),
                responsable="prueba",
                filas_leidas=3,
                filas_rechazadas=0,
                ahora=datetime(2026, 10, 31, 8, 0),
            )
            s.commit()
            yield s
    finally:
        motor.dispose()


def test_las_tablas_son_las_del_plan() -> None:
    assert TABLAS == ("partidas_viales", "insumos", "tasa_bcv", "salarios_cct")


def test_sin_distinguir_mayusculas_ni_acentos(sesion: Session) -> None:
    a = buscar(sesion, "partidas_viales", "carpeta")
    b = buscar(sesion, "partidas_viales", "CARPÉTA")
    assert a and a[0] == b[0]
    assert a[0].valor == "C-000.000.008"  # la descripción empieza por «carpeta»; la mezcla, no
    assert "Carpeta" in a[0].etiqueta


def test_cada_sugerencia_trae_su_fuente(sesion: Session) -> None:
    for tabla, texto in (
        ("partidas_viales", "base"),
        ("insumos", "cemento"),
        ("tasa_bcv", "2026-10"),
        ("salarios_cct", "albañil"),
    ):
        halladas = buscar(sesion, tabla, texto)
        assert halladas, tabla
        assert all(isinstance(h, Sugerencia) and h.fuente.strip() for h in halladas), tabla


def test_el_codigo_exacto_va_primero_y_el_limite_se_respeta(sesion: Session) -> None:
    assert buscar(sesion, "partidas_viales", "c-000.000.003")[0].valor == "C-000.000.003"
    assert len(buscar(sesion, "partidas_viales", "granular", limite=1)) == 1


def test_insumos_son_material_y_equipo_y_salarios_la_mano_de_obra(sesion: Session) -> None:
    assert {s.valor for s in buscar(sesion, "insumos", "ficti")} == {"MAT-1", "MAT-2", "EQ-1"}
    assert [s.valor for s in buscar(sesion, "salarios_cct", "ficti")] == ["MO-1"]


def test_la_tasa_se_busca_por_fecha_en_dos_grafias_y_va_la_mas_reciente_primero(
    sesion: Session,
) -> None:
    por_mes = buscar(sesion, "tasa_bcv", "2026-10")
    assert [s.valor for s in por_mes] == ["2026-10-30", "2026-10-29"]
    assert buscar(sesion, "tasa_bcv", "30/10/2026")[0].valor == "2026-10-30"
    assert "41,25" in por_mes[0].etiqueta and "Bs/USD" in por_mes[0].etiqueta


def test_menos_de_dos_letras_no_busca(sesion: Session) -> None:
    assert buscar(sesion, "insumos", "c") == []
    assert buscar(sesion, "insumos", "   ") == []


def test_tabla_desconocida_es_un_error(sesion: Session) -> None:
    with pytest.raises(LookupError):
        buscar(sesion, "no_existe", "algo")


def test_una_partida_vial_trae_su_descripcion_y_su_unidad(sesion: Session) -> None:
    """E2E-3 (prueba de punta a punta del 2026-11-13): al elegir un código vial en Componer no se
    llenaban la descripción ni la unidad, que solo venían dentro de la etiqueta. Ahora vienen
    aparte, como las de `adapters.vial.constantes.PARTIDAS_VIALES`."""
    (base,) = [
        h for h in buscar(sesion, "partidas_viales", "c-000.000.002") if h.valor == "C-000.000.002"
    ]
    assert (base.descripcion, base.unidad) == ("Base granular compactada", "m3")
