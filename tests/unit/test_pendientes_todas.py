"""Pendientes de todas las carpetas (rediseño F3, T1): `aplicacion.pendientes_todas`.

Carpetas ficticias en temporal: la de la empresa (`None`) con «Edificio Central»; «Carpeta Norte»
con «Galpón» (id 1) y «Clínica» (id 2); «Carpeta Sur» con «Vialidad». Las fuentes de la mesa se
reemplazan por fuentes falsas que leen la tabla `proyecto` (un texto por obra y grupo, escrito a
mano). Oráculos a mano: el orden (lo que bloquea primero; dentro de cada urgencia, la carpeta de
la empresa, luego las demás por nombre; luego el grupo en el orden de `GRUPOS`), el `obra_id`, el
nombre de la obra y la urgencia por grupo (D-F3-1: aprobar y compras bloquean; precios y calidad
avisan). El último caso usa las fuentes reales con un envío devuelto sembrado.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from aplicacion import aprobaciones, mesa
from aplicacion.mesa import Pendiente, Siguiente
from aplicacion.pendientes_todas import (
    URGENCIA_DEL_GRUPO,
    PendienteDeObra,
    pendientes_de_las_carpetas,
)
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import ANA, OBRA, sembrar_vivienda

HOY = date(2026, 10, 28)
OBRAS = {
    "empresa.db": ["Edificio Central"],
    "Carpeta Norte.db": ["Galpón", "Clínica"],
    "Carpeta Sur.db": ["Vialidad"],
}
VER_EL_ENVIO = Siguiente("Ver el envío", "aprobar")
ABRIR_LA_HOJA = Siguiente("Abrir la Hoja", "hoja")
ACTUALIZAR = Siguiente("Actualizar precios", "actualizacion")
VER_COMPRAS = Siguiente("Ver las compras", "compras")

#: (grupo, obra) -> (texto, acción): lo que dicen las fuentes falsas.
ESCENARIO: dict[tuple[str, str], tuple[str, Siguiente]] = {}


def _fuente_falsa(grupo: str):
    def fuente(sesion, hoy):
        obras = sesion.scalars(select(models.Proyecto).order_by(models.Proyecto.id)).all()
        return [
            Pendiente(str(o.id), o.nombre, *ESCENARIO[(grupo, o.nombre)])
            for o in obras
            if (grupo, o.nombre) in ESCENARIO
        ]

    return fuente


@pytest.fixture(autouse=True)
def _fuentes_falsas(monkeypatch: pytest.MonkeyPatch):
    ESCENARIO.clear()
    monkeypatch.setattr(mesa, "FUENTES", {g: (_fuente_falsa(g),) for g, _ in mesa.GRUPOS})
    yield
    ESCENARIO.clear()


def _crear(ruta: Path, obras: list[str]) -> None:
    preparar_base(ruta)
    with closing(sqlite3.connect(ruta)) as conexion:
        for n, obra in enumerate(obras, 1):
            conexion.execute(
                "INSERT INTO proyecto (id, nombre, descripcion, dominio) VALUES (?, ?, '', '')",
                (n, obra),
            )
        conexion.commit()
        conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")


@pytest.fixture
def carpetas(tmp_path: Path) -> list[tuple[str | None, Path]]:
    salida: list[tuple[str | None, Path]] = []
    for nombre, obras in OBRAS.items():
        _crear(tmp_path / nombre, obras)
        salida.append((None if nombre == "empresa.db" else nombre, tmp_path / nombre))
    return salida


def _claves(resultado) -> list[tuple[str | None, str, str]]:
    return [(i.carpeta, i.obra, i.urgencia) for i in resultado.items]


def test_une_las_carpetas_y_pone_primero_lo_que_bloquea(carpetas) -> None:
    ESCENARIO[("precios", "Galpón")] = ("Galpón: precios viejos", ACTUALIZAR)
    ESCENARIO[("aprobar", "Vialidad")] = ("V2 devuelta: falta acero", ABRIR_LA_HOJA)
    resultado = pendientes_de_las_carpetas(carpetas, HOY, alcance="todo")
    assert _claves(resultado) == [
        ("Carpeta Sur.db", "Vialidad", "bloquea"),
        ("Carpeta Norte.db", "Galpón", "aviso"),
    ]
    assert resultado.carpetas_omitidas == 0
    assert resultado.items[0] == PendienteDeObra(
        carpeta="Carpeta Sur.db",
        obra_id=1,
        obra="Vialidad",
        grupo="aprobar",
        urgencia="bloquea",
        texto="V2 devuelta: falta acero",
        accion=ABRIR_LA_HOJA,
    )


def test_dentro_de_la_urgencia_carpeta_y_grupo(carpetas) -> None:
    ESCENARIO[("compras", "Clínica")] = ("Falta comprar cemento", VER_COMPRAS)
    ESCENARIO[("aprobar", "Vialidad")] = ("V1 espera dictamen", VER_EL_ENVIO)
    ESCENARIO[("aprobar", "Edificio Central")] = ("V3 espera dictamen", VER_EL_ENVIO)
    ESCENARIO[("compras", "Galpón")] = ("Falta comprar acero", VER_COMPRAS)
    ESCENARIO[("aprobar", "Galpón")] = ("V9 espera dictamen", VER_EL_ENVIO)
    resultado = pendientes_de_las_carpetas(carpetas, HOY, alcance="todo")
    # empresa primero, luego Norte (aprobar antes que compras; en compras, el orden de la fuente
    # = id de la obra: Galpón 1, Clínica 2), luego Sur
    assert [(i.carpeta, i.obra, i.grupo) for i in resultado.items] == [
        (None, "Edificio Central", "aprobar"),
        ("Carpeta Norte.db", "Galpón", "aprobar"),
        ("Carpeta Norte.db", "Galpón", "compras"),
        ("Carpeta Norte.db", "Clínica", "compras"),
        ("Carpeta Sur.db", "Vialidad", "aprobar"),
    ]
    assert {i.urgencia for i in resultado.items} == {"bloquea"}


def test_urgencia_por_grupo() -> None:
    assert URGENCIA_DEL_GRUPO == {
        "aprobar": "bloquea",
        "compras": "bloquea",
        "precios": "aviso",
        "calidad": "aviso",
    }


def test_obra_id_y_nombre_de_la_obra(carpetas) -> None:
    ESCENARIO[("calidad", "Clínica")] = ("Hallazgo grave", ABRIR_LA_HOJA)
    (item,) = pendientes_de_las_carpetas(carpetas, HOY, alcance="todo").items
    assert (item.carpeta, item.obra_id, item.obra, item.grupo) == (
        "Carpeta Norte.db",
        2,
        "Clínica",
        "calidad",
    )


@pytest.mark.parametrize("contenido", [b"esto no es SQLite " * 40, b""], ids=["texto", "vacio"])
def test_carpeta_ilegible_se_omite_y_se_cuenta(carpetas, tmp_path: Path, contenido: bytes) -> None:
    rota = tmp_path / "Carpeta Rota.db"
    rota.write_bytes(contenido)
    ESCENARIO[("aprobar", "Vialidad")] = ("V1 espera dictamen", VER_EL_ENVIO)
    resultado = pendientes_de_las_carpetas(
        [*carpetas, ("Carpeta Rota.db", rota)], HOY, alcance="todo"
    )
    assert _claves(resultado) == [("Carpeta Sur.db", "Vialidad", "bloquea")]
    assert resultado.carpetas_omitidas == 1


def test_alcance_por_aprobar_deja_solo_lo_que_espera_dictamen(carpetas) -> None:
    ESCENARIO[("aprobar", "Vialidad")] = ("V1 espera dictamen", VER_EL_ENVIO)
    ESCENARIO[("aprobar", "Galpón")] = ("V2 devuelta: falta acero", ABRIR_LA_HOJA)
    ESCENARIO[("compras", "Clínica")] = ("Falta comprar", VER_COMPRAS)
    ESCENARIO[("precios", "Edificio Central")] = ("Precios viejos", ACTUALIZAR)
    todo = pendientes_de_las_carpetas(carpetas, HOY, alcance="todo")
    assert len(todo.items) == 4
    resultado = pendientes_de_las_carpetas(carpetas, HOY, alcance="por_aprobar")
    assert [(i.obra, i.texto) for i in resultado.items] == [("Vialidad", "V1 espera dictamen")]


def test_no_escribe(carpetas) -> None:
    ESCENARIO[("aprobar", "Vialidad")] = ("V1 espera dictamen", VER_EL_ENVIO)
    rutas = [r for _, r in carpetas]
    fechas = {r: r.stat().st_mtime_ns for r in rutas}
    antes = sorted(p.name for p in rutas[0].parent.iterdir())
    pendientes_de_las_carpetas(carpetas, HOY, alcance="todo")
    assert {r: r.stat().st_mtime_ns for r in rutas} == fechas
    assert sorted(p.name for p in rutas[0].parent.iterdir()) == antes  # ni -wal ni -shm nuevos


def test_con_las_fuentes_reales_una_devuelta_sale_como_bloquea(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.undo()  # vuelven las fuentes reales de la mesa
    ruta = tmp_path / "Carpeta Norte.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar_vivienda(sesion)
            lunes = datetime(2026, 10, 19, 9, 0)
            envio = aprobaciones.enviar(sesion, OBRA, "VIV-001", nota="", usuario=ANA, ahora=lunes)
            aprobaciones.dictaminar(
                sesion,
                envio.id,
                resultado="devuelta",
                notas="Falta el acero de la losa.",
                usuario="Rita <rita>",
                ahora=lunes.replace(hour=10),
            )
    finally:
        motor.dispose()
    resultado = pendientes_de_las_carpetas([("Carpeta Norte.db", ruta)], HOY, alcance="todo")
    devuelta = [i for i in resultado.items if i.grupo == "aprobar"]
    assert [(i.obra, i.urgencia, i.texto, i.accion.pagina) for i in devuelta] == [
        (OBRA, "bloquea", "VIV-001 devuelta: Falta el acero de la losa.", "hoja")
    ]
    assert devuelta[0].obra_id == 1


def sembrar_fecha_no_iso(ruta: Path) -> None:
    """Un envío con `fecha_hora` en texto no ISO: leerlo lanza `ValueError`."""
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO mp_aprobacion_evento (proyecto_id, tipo, version, huella_version, notas,"
            " usuario, fecha_hora, armo, anterior, huella) VALUES (1, 'envio', 'V1', ?, '',"
            " 'Ana <ana>', '28/10/2026 9:00', 0, ?, ?)",
            ("a" * 64, "0" * 64, "b" * 64),
        )
        conexion.commit()
        conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def test_carpeta_con_datos_raros_se_omite_y_la_sana_sigue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.undo()  # fuentes reales de la mesa
    rara, sana = tmp_path / "Carpeta Rara.db", tmp_path / "Carpeta Sana.db"
    _crear(rara, ["Galpón"])
    sembrar_fecha_no_iso(rara)
    _crear(sana, ["Vialidad"])
    sembrar_fecha_no_iso(sana)  # el mismo envío pero con fecha válida abajo
    with closing(sqlite3.connect(sana)) as conexion:
        conexion.execute("UPDATE mp_aprobacion_evento SET fecha_hora = '2026-10-28 09:00:00'")
        conexion.commit()
        conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    with caplog.at_level(logging.WARNING, logger="aplicacion.pendientes_todas"):
        resultado = pendientes_de_las_carpetas(
            [("Carpeta Rara.db", rara), ("Carpeta Sana.db", sana)], HOY, alcance="todo"
        )
    assert [(i.carpeta, i.obra, i.texto) for i in resultado.items] == [
        ("Carpeta Sana.db", "Vialidad", "V1 espera dictamen")
    ]
    assert resultado.carpetas_omitidas == 1
    # el registro dice la carpeta y el tipo del error, no el texto de la excepción (trae datos)
    avisos = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(avisos) == 1
    assert "Carpeta Rara.db" in avisos[0] and "ValueError" in avisos[0]
    for rastro in ("28/10/2026", "isoformat"):
        assert rastro not in avisos[0]


def test_la_traza_de_una_carpeta_omitida_va_solo_al_registro_local_en_debug(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.undo()
    rara = tmp_path / "Carpeta Rara.db"
    _crear(rara, ["Galpón"])
    sembrar_fecha_no_iso(rara)
    with caplog.at_level(logging.DEBUG, logger="aplicacion.pendientes_todas"):
        pendientes_de_las_carpetas([("Carpeta Rara.db", rara)], HOY, alcance="todo")
    trazas = [r for r in caplog.records if r.levelno == logging.DEBUG and r.exc_info]
    assert len(trazas) == 1
    assert trazas[0].exc_info[0] is ValueError
    # la traza no viaja en el mensaje: solo el formateador del registro local la imprime
    assert "28/10/2026" not in trazas[0].getMessage()


def test_por_aprobar_exige_el_grupo_aprobar(carpetas) -> None:
    ESCENARIO[("aprobar", "Vialidad")] = ("V1 espera dictamen", VER_EL_ENVIO)
    ESCENARIO[("precios", "Galpón")] = ("Otro grupo con página aprobar", VER_EL_ENVIO)
    resultado = pendientes_de_las_carpetas(carpetas, HOY, alcance="por_aprobar")
    assert [(i.obra, i.grupo) for i in resultado.items] == [("Vialidad", "aprobar")]


def test_carpeta_sin_archivo_no_se_cuenta_como_omitida_ni_deja_aviso(
    carpetas, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Cierre de F3 (H2): la carpeta de la empresa de la demostración no existe como archivo;
    sin archivo no hay obras ni pendientes, y no es un fallo."""
    ESCENARIO[("aprobar", "Vialidad")] = ("V1 espera dictamen", VER_EL_ENVIO)
    with caplog.at_level(logging.WARNING, logger="aplicacion.pendientes_todas"):
        resultado = pendientes_de_las_carpetas(
            [*carpetas, (None, tmp_path / "silice.db")], HOY, alcance="todo"
        )
    assert _claves(resultado) == [("Carpeta Sur.db", "Vialidad", "bloquea")]
    assert resultado.carpetas_omitidas == 0
    assert not [r for r in caplog.records if r.levelno == logging.WARNING]
