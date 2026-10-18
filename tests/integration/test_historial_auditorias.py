"""`fusion.historial`: cada auditoria de «Libro de la empresa» se guarda (UC-25; RF-142 a RF-144).

Se guarda el resumen y los hallazgos compactos; nunca el libro ni el PDF (RNF-28). Oraculos a mano:

- Seis hallazgos (CRITICO, ERROR, ADVERTENCIA, ADVERTENCIA, INFO y un ATIPICO, que es una regla de
  severidad ADVERTENCIA) dan errores = 2 (CRITICO cuenta como error, igual que `cumple` de la API),
  advertencias = 2, informativos = 1 y atipicos = 1: las cuatro cuentas suman los seis y un atipico
  no se cuenta ademas como advertencia.
- Con 503 hallazgos se guardan los primeros 500, `recortado` es verdadero y los conteos siguen
  siendo los de los 503; con exactamente 500 no se recorta nada.
- La fila de la prueba usa totales que se escriben como texto exacto en la base ('1586.61').
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from adapters.hoja_empresa.modelo import FilaHallazgo
from fusion.historial import (
    TOPE_HALLAZGOS,
    AuditoriaInexistente,
    HallazgoCompacto,
    compactar,
    detalle,
    listar,
    registrar_auditoria,
)
from operacion.base_datos import Destino, aplicar_revisiones
from seguridad.base import abrir_sesion, crear_motor

SHA = "ab" * 32
AHORA = datetime(2026, 10, 18, 14, 3, 5)


def _hallazgo(severidad: str = "ERROR", regla: str = "L4", n: int = 0) -> HallazgoCompacto:
    return HallazgoCompacto(
        regla=regla, hoja="APU-02", celda=f"G{n}", severidad=severidad, mensaje=f"mensaje {n}"
    )


SEIS = [
    _hallazgo("CRITICO", "F1", 1),
    _hallazgo("ERROR", "L4", 2),
    _hallazgo("ADVERTENCIA", "L2", 3),
    _hallazgo("ADVERTENCIA", "R3", 4),
    _hallazgo("INFO", "R2", 5),
    _hallazgo("ADVERTENCIA", "ATIPICO", 6),
]


@pytest.fixture
def ruta(tmp_path: Path) -> Path:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION)
    return base


@pytest.fixture
def sesion(ruta: Path) -> Iterator[Session]:
    motor = crear_motor(ruta)
    s = abrir_sesion(motor)
    try:
        yield s
    finally:
        s.close()
        motor.dispose()


def _registrar(sesion: Session, **cambios):
    datos = {
        "usuario": "Ana <ana>",
        "tipo": "libro",
        "nombre_archivo": "presupuesto.xlsx",
        "sha256": SHA,
        "fecha_libro": date(2026, 10, 1),
        "total_libro": Decimal("1586.61"),
        "total_silice": Decimal("1500.00"),
        "hallazgos": SEIS,
        "ahora": AHORA,
    }
    datos.update(cambios)
    return registrar_auditoria(sesion, **datos)


def _filas(ruta: Path) -> list[tuple]:
    with closing(sqlite3.connect(ruta)) as conexion:
        return conexion.execute(
            "SELECT id, fecha_hora, usuario, tipo, nombre_archivo, sha256, fecha_libro, "
            "total_libro, total_silice, errores, advertencias, informativos, atipicos, "
            "recortado, hallazgos FROM auditoria_libro ORDER BY id"
        ).fetchall()


# --- registrar -----------------------------------------------------------------------------------


def test_registrar_guarda_el_resumen_y_devuelve_lo_guardado(sesion, ruta) -> None:
    guardada = _registrar(sesion)
    sesion.commit()

    assert guardada.id == 1
    assert guardada.fecha_hora == AHORA
    assert (guardada.usuario, guardada.tipo) == ("Ana <ana>", "libro")
    assert (guardada.errores, guardada.advertencias) == (2, 2)
    assert (guardada.informativos, guardada.atipicos) == (1, 1)
    assert guardada.recortado is False
    assert guardada.hallazgos == tuple(SEIS)
    [fila] = _filas(ruta)
    assert fila[:14] == (
        1, "2026-10-18 14:03:05.000000", "Ana <ana>", "libro", "presupuesto.xlsx", SHA,
        "2026-10-01", "1586.61", "1500.00", 2, 2, 1, 1, 0,
    )


def test_los_hallazgos_se_guardan_compactos_y_en_orden(sesion, ruta) -> None:
    _registrar(sesion)
    sesion.commit()
    guardados = json.loads(_filas(ruta)[0][14])
    assert [set(h) for h in guardados] == [{"regla", "hoja", "celda", "severidad", "mensaje"}] * 6
    assert guardados[0] == {
        "regla": "F1", "hoja": "APU-02", "celda": "G1", "severidad": "CRITICO",
        "mensaje": "mensaje 1",
    }
    assert [h["regla"] for h in guardados] == ["F1", "L4", "L2", "R3", "R2", "ATIPICO"]


def test_repetir_la_misma_auditoria_guarda_otra_fila(sesion, ruta) -> None:
    primera = _registrar(sesion)
    segunda = _registrar(sesion, ahora=datetime(2026, 10, 18, 15, 0, 0))
    sesion.commit()
    assert (primera.id, segunda.id) == (1, 2)
    assert [f[5] for f in _filas(ruta)] == [SHA, SHA]


def test_un_pdf_simple_se_guarda_sin_totales_ni_fecha_del_libro(sesion, ruta) -> None:
    guardada = _registrar(
        sesion,
        tipo="pdf",
        nombre_archivo="presupuesto.pdf",
        fecha_libro=None,
        total_libro=None,
        total_silice=None,
        hallazgos=[_hallazgo("ERROR", "L10", 1)],
    )
    sesion.commit()
    assert (guardada.fecha_libro, guardada.total_libro, guardada.total_silice) == (None, None, None)
    fila = _filas(ruta)[0]
    assert fila[3] == "pdf" and fila[6:9] == (None, None, None)


def test_sin_hallazgos_se_guarda_una_lista_vacia(sesion, ruta) -> None:
    guardada = _registrar(sesion, hallazgos=[])
    sesion.commit()
    assert (guardada.errores, guardada.advertencias, guardada.informativos, guardada.atipicos) == (
        0, 0, 0, 0,
    )
    assert _filas(ruta)[0][14] == "[]"


def test_pasado_el_tope_se_guardan_los_primeros_500_y_los_conteos_son_los_de_todos(
    sesion, ruta
) -> None:
    assert TOPE_HALLAZGOS == 500
    muchos = [_hallazgo("ERROR", "L4", n) for n in range(503)]
    guardada = _registrar(sesion, hallazgos=muchos)
    sesion.commit()
    assert guardada.recortado is True and guardada.errores == 503
    assert len(guardada.hallazgos) == 500
    fila = _filas(ruta)[0]
    guardados = json.loads(fila[14])
    assert len(guardados) == 500 and guardados[-1]["celda"] == "G499"
    assert (fila[9], fila[13]) == (503, 1)


def test_con_exactamente_el_tope_no_se_recorta(sesion) -> None:
    guardada = _registrar(sesion, hallazgos=[_hallazgo("INFO", "R2", n) for n in range(500)])
    assert guardada.recortado is False and len(guardada.hallazgos) == 500
    assert guardada.informativos == 500


def test_un_mensaje_largo_se_corta_a_500_caracteres(sesion) -> None:
    largo = HallazgoCompacto("L4", "APU-01", "G1", "ERROR", "x" * 900)
    guardada = _registrar(sesion, hallazgos=[largo])
    assert guardada.hallazgos[0].mensaje == "x" * 500


@pytest.mark.parametrize(
    "cambio",
    [
        {"tipo": "excel"},
        {"sha256": "no-es-un-sha"},
        {"sha256": "AB" * 32},
        {"usuario": ""},
        {"nombre_archivo": "  "},
        {"hallazgos": [_hallazgo("GRAVE")]},
    ],
)
def test_un_dato_invalido_no_guarda_nada(sesion, ruta, cambio) -> None:
    with pytest.raises(ValueError):
        _registrar(sesion, **cambio)
    sesion.commit()
    assert _filas(ruta) == []


def test_el_nombre_del_archivo_pierde_la_ruta(sesion) -> None:
    guardada = _registrar(sesion, nombre_archivo="C:\\Users\\ana\\obras\\libro.xlsx")
    assert guardada.nombre_archivo == "libro.xlsx"


# --- compactar una fila de la API ----------------------------------------------------------------


def test_compactar_separa_la_hoja_de_la_celda_y_descarta_el_resto() -> None:
    fila = FilaHallazgo(
        codigo="L4", severidad="ERROR", descripcion="El CD no suma", celda="APU-02!G12",
        impacto=Decimal("1.65"), accion="informado",
    )
    assert compactar(fila) == HallazgoCompacto(
        regla="L4", hoja="APU-02", celda="G12", severidad="ERROR", mensaje="El CD no suma"
    )
    sin_celda = FilaHallazgo("R2", "INFO", "Sin tasa", "", None, "informado")
    assert compactar(sin_celda) == HallazgoCompacto("R2", "", "", "INFO", "Sin tasa")
    suelta = FilaHallazgo("L10", "ERROR", "Fila 3", "F3", None, "informado")
    assert compactar(suelta) == HallazgoCompacto("L10", "", "F3", "ERROR", "Fila 3")


# --- listar y detalle ----------------------------------------------------------------------------


def test_listar_da_las_mas_recientes_primero_y_respeta_el_limite(sesion) -> None:
    _registrar(sesion, nombre_archivo="a.xlsx", ahora=datetime(2026, 10, 18, 9, 0, 0))
    _registrar(sesion, nombre_archivo="c.xlsx", ahora=datetime(2026, 10, 18, 11, 0, 0))
    _registrar(sesion, nombre_archivo="b.xlsx", ahora=datetime(2026, 10, 18, 10, 0, 0))
    _registrar(sesion, nombre_archivo="d.xlsx", ahora=datetime(2026, 10, 18, 11, 0, 0))  # empate
    sesion.commit()

    todas = listar(sesion, 10)
    assert [r.nombre_archivo for r in todas] == ["d.xlsx", "c.xlsx", "b.xlsx", "a.xlsx"]
    assert [r.id for r in todas] == [4, 2, 3, 1]
    assert [r.nombre_archivo for r in listar(sesion, 2)] == ["d.xlsx", "c.xlsx"]
    assert listar(sesion, 1)[0].errores == 2


def test_listar_sin_auditorias_da_lista_vacia(sesion) -> None:
    assert listar(sesion, 5) == []


def test_detalle_devuelve_el_resumen_y_los_hallazgos(sesion) -> None:
    _registrar(sesion)
    sesion.commit()
    visto = detalle(sesion, 1)
    assert visto.hallazgos == tuple(SEIS)
    assert (visto.total_libro, visto.total_silice) == (Decimal("1586.61"), Decimal("1500.00"))
    assert visto.fecha_libro == date(2026, 10, 1)
    assert visto.sha256 == SHA


def test_detalle_de_una_auditoria_que_no_existe(sesion) -> None:
    with pytest.raises(AuditoriaInexistente):
        detalle(sesion, 99)
    assert issubclass(AuditoriaInexistente, LookupError)
