"""Plan vial, Tarea 8: los tramos guardados por versión (`aplicacion/vial.py`). Datos FICTICIOS.

La carpeta es la «Vivienda Demo 80 m2» de `tests/fixtures/carpeta_aprobaciones.py` (VIV-001 y
VIV-002), migrada con `preparar_base` (así la migración `caso_0019` también se ejerce). Los tramos
son los del contrato de la Tarea 7. Oráculos a mano: lo que se guarda es lo que se lee, cifra por
cifra (el ancho «7.30» conserva sus dos decimales), un guardado nuevo no borra el anterior (queda
como otra fila del rastro) y una versión enviada a aprobación, aprobada o devuelta ya no se
edita. Las filas se cuentan con `sqlite3`, sin pasar por el código bajo prueba.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from adapters.vial.modelo import Capa, Demarcacion, Tramo
from adapters.vial.reglas import ReglasViales
from aplicacion import aprobaciones, vial
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from produccion.receta import Componente, Receta
from tests.fixtures.carpeta_aprobaciones import guardar_version, sembrar_vivienda

D = Decimal
ANA = "Ana <ana>"
LUNES = datetime(2026, 10, 19, 9, 0)
MARTES = datetime(2026, 10, 20, 10, 30)
MUESTRA = Path(__file__).resolve().parents[2] / "data" / "samples" / "vial" / "via_ficticia.csv"

T1 = Tramo(
    "T1",
    D("0"),
    D("1.2"),
    D("7.30"),
    (
        Capa("fresado", D("0.05"), None, None),
        Capa("riego_adherencia", None, None, D("0.40")),
        Capa("carpeta", D("0.05"), D("2.35"), None),
    ),
    (Demarcacion("continua", 2), Demarcacion("discontinua", 1)),
    D("15"),
)
T2 = Tramo(
    "T2",
    D("1.2"),
    D("2.0"),
    D("6.5"),
    (Capa("base_granular", D("0.20"), None, None),),
)


@pytest.fixture
def motor(tmp_path: Path) -> Iterator[Engine]:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            obra = sembrar_vivienda(s, usuario=ANA)
            guardar_version(s, obra, "VIV-002", usuario=ANA)
        yield motor
    finally:
        motor.dispose()


@pytest.fixture
def sesion(motor: Engine) -> Iterator[Session]:
    with abrir_sesion(motor) as s:
        yield s


def _version(s: Session, codigo: str = "VIV-002") -> int:
    return s.scalars(select(models.Presupuesto.id).where(models.Presupuesto.codigo == codigo)).one()


def _filas(motor: Engine, tabla: str) -> int:
    ruta = motor.url.database
    with closing(sqlite3.connect(ruta)) as conexion:
        return conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


def _filas_si_existe(motor: Engine, tabla: str) -> int:
    with closing(sqlite3.connect(motor.url.database)) as conexion:
        existe = conexion.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (tabla,)).fetchone()
        return conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] if existe else 0


def _enviar(s: Session, version: str = "VIV-002") -> int:
    return aprobaciones.enviar(
        s, "Vivienda Demo 80 m2", version, nota="listo", usuario=ANA, ahora=LUNES
    ).id


def test_guardar_y_leer_igual(sesion: Session) -> None:
    v = _version(sesion)
    vial.guardar_tramos(sesion, v, [T1, T2], usuario=ANA, ahora=LUNES)
    leidos = vial.tramos_de_version(sesion, v)
    assert leidos == [T1, T2]
    # exacto: el «7.30» conserva sus dos decimales y la distancia ausente sigue ausente
    assert str(leidos[0].ancho_m) == "7.30"
    assert leidos[1].distancia_planta_km is None
    assert leidos[0].capas[1].dosis_l_m2 == D("0.40")
    assert leidos[0].demarcacion == (Demarcacion("continua", 2), Demarcacion("discontinua", 1))


def test_version_sin_tramos_da_lista_vacia(sesion: Session) -> None:
    assert vial.tramos_de_version(sesion, _version(sesion)) == []
    assert vial.guardado_de_version(sesion, _version(sesion)) is None


def test_un_guardado_nuevo_no_borra_el_anterior(sesion: Session, motor: Engine) -> None:
    v = _version(sesion)
    vial.guardar_tramos(sesion, v, [T1, T2], usuario=ANA, ahora=LUNES)
    vial.guardar_tramos(sesion, v, [T2], usuario="Rita <rita>", ahora=MARTES, fuente="via.csv")
    assert vial.tramos_de_version(sesion, v) == [T2]
    assert _filas(motor, "vial_tramos_guardado") == 2  # el rastro conserva los dos
    assert _filas(motor, "vial_tramo") == 3
    ultimo = vial.guardado_de_version(sesion, v)
    assert (ultimo.usuario, ultimo.fecha_hora, ultimo.fuente) == ("Rita <rita>", MARTES, "via.csv")


def _tercera(s: Session) -> int:
    obra = s.scalars(select(models.Proyecto)).one()
    guardar_version(s, obra, "VIV-003", usuario=ANA)
    return _version(s, "VIV-003")


def test_version_sin_guardado_propio_hereda_de_la_anterior(sesion: Session, motor: Engine) -> None:
    uno = _version(sesion, "VIV-001")
    # VIV-002 existe: se guarda en la más reciente y la anterior queda sin guardado propio
    assert vial.heredados_de(sesion, uno) is None
    dos = _version(sesion, "VIV-002")
    vial.guardar_tramos(sesion, dos, [T1], usuario=ANA, ahora=LUNES)
    tres = _tercera(sesion)
    assert vial.tramos_de_version(sesion, tres) == [T1]
    assert vial.heredados_de(sesion, tres) == "VIV-002"
    assert [c.tramo for c in vial.cantidades_de_tramos(vial.tramos_de_version(sesion, tres))][
        0
    ] == "T1"
    assert _filas_si_existe(motor, "vial_tramos_guardado") == 1  # heredar no escribe nada


def test_viv003_hereda_de_viv002_tras_guardar_en_viv002(sesion: Session) -> None:
    dos = _version(sesion, "VIV-002")
    vial.guardar_tramos(sesion, dos, [T2], usuario=ANA, ahora=LUNES)
    tres = _tercera(sesion)
    assert vial.tramos_de_version(sesion, tres) == [T2]
    assert vial.heredados_de(sesion, tres) == "VIV-002"
    assert (
        vial.guardado_de_version(sesion, tres).usuario == ANA
    )  # el rastro es el del guardado usado
    # y VIV-002 ya no es la más reciente: no se toca
    assert "VIV-003" in vial.bloqueo_de_version(sesion, dos)


def test_solo_se_guarda_en_la_version_mas_reciente(sesion: Session, motor: Engine) -> None:
    uno = _version(sesion, "VIV-001")
    texto = "Solo se editan los tramos de la versión más reciente (VIV-002)."
    with pytest.raises(vial.VersionBloqueada) as error:
        vial.guardar_tramos(sesion, uno, [T1], usuario=ANA, ahora=LUNES)
    assert str(error.value) == texto
    assert vial.bloqueo_de_version(sesion, uno) == texto
    assert vial.bloqueo_de_version(sesion, _version(sesion, "VIV-002")) is None
    assert _filas_si_existe(motor, "vial_tramos_guardado") == 0


def test_obra_sin_ningun_guardado(sesion: Session) -> None:
    assert vial.heredados_de(sesion, _version(sesion)) is None
    assert vial.tramos_de_version(sesion, _version(sesion)) == []


def test_un_guardado_que_falla_a_medias_no_deja_filas(sesion: Session, motor: Engine) -> None:
    v = _version(sesion)
    with pytest.raises(ValueError, match="repetido"):
        vial.guardar_tramos(sesion, v, [T1, T1], usuario=ANA, ahora=LUNES)
    assert _filas_si_existe(motor, "vial_tramos_guardado") == 0
    assert _filas_si_existe(motor, "vial_tramo") == 0
    assert vial.tramos_de_version(sesion, v) == []


def test_version_inexistente(sesion: Session) -> None:
    with pytest.raises(vial.VersionInexistente):
        vial.guardar_tramos(sesion, 9999, [T1], usuario=ANA, ahora=LUNES)
    with pytest.raises(vial.VersionInexistente):
        vial.tramos_de_version(sesion, 9999)


def test_version_aprobada_no_se_edita(sesion: Session, motor: Engine) -> None:
    v = _version(sesion)
    vial.guardar_tramos(sesion, v, [T1], usuario=ANA, ahora=LUNES)
    envio = _enviar(sesion)
    aprobaciones.dictaminar(
        sesion, envio, resultado="aprobada", notas="", usuario="Rita <rita>", ahora=MARTES
    )
    with pytest.raises(vial.VersionBloqueada, match="VIV-002 está aprobada"):
        vial.guardar_tramos(sesion, v, [T2], usuario=ANA, ahora=MARTES)
    assert vial.tramos_de_version(sesion, v) == [T1]  # nada cambió
    assert _filas(motor, "vial_tramos_guardado") == 1
    assert vial.bloqueo_de_version(sesion, v) == (
        "La versión VIV-002 está aprobada: sus tramos ya no se editan. Guarde una versión nueva "
        "y cargue los tramos allí."
    )


def test_version_en_aprobacion_o_devuelta_tampoco(sesion: Session) -> None:
    v = _version(sesion)
    assert vial.bloqueo_de_version(sesion, v) is None
    envio = _enviar(sesion)
    assert "está en aprobación" in vial.bloqueo_de_version(sesion, v)
    aprobaciones.dictaminar(
        sesion, envio, resultado="devuelta", notas="falta", usuario="Rita <rita>", ahora=MARTES
    )
    assert "está devuelta" in vial.bloqueo_de_version(sesion, v)
    with pytest.raises(vial.VersionBloqueada):
        vial.guardar_tramos(sesion, v, [T1], usuario=ANA, ahora=MARTES)


def test_una_version_retirada_vuelve_a_editarse(sesion: Session) -> None:
    v = _version(sesion)
    _enviar(sesion, "VIV-002")
    _enviar(sesion, "VIV-001")  # retira el envío pendiente de VIV-002
    assert vial.bloqueo_de_version(sesion, v) is None
    vial.guardar_tramos(sesion, v, [T1], usuario=ANA, ahora=MARTES)


def test_csv_de_la_muestra(sesion: Session) -> None:
    tramos = vial.tramos_desde_csv(MUESTRA.read_bytes(), "via_ficticia.csv")
    assert [t.id for t in tramos] == ["T1", "T2", "T3"]
    assert tramos[0].ancho_m == D("7.30")
    assert tramos[1].progresiva_ini_km == D("1.2")


def test_csv_con_fila_mala_dice_la_fila() -> None:
    malo = MUESTRA.read_text(encoding="utf-8").replace("T2;1,2;2,0;6,50", "T2;2,0;1,2;6,50")
    with pytest.raises(ValueError, match=r"'via_mala\.csv', fila 7\b"):
        vial.tramos_desde_csv(malo.encode("utf-8"), "via_mala.csv")


def test_csv_que_no_es_texto_utf8() -> None:
    with pytest.raises(ValueError, match="ilegible"):
        vial.tramos_desde_csv(b"\xff\xfe\x00\x00", "x.csv")


# --- Tarea 9: reglas del auditor ------------------------------------------------------------------

MEZCLA = Receta(
    1,
    "MZP-001",
    (
        Componente("AGP-001", D("0.945"), "t", "propio"),
        Componente("LIG-001", D("0.055"), "t", "comprado"),
        Componente("DIE-001", D("2"), "l", "comprado"),
    ),
    "fórmula ficticia",
    datetime(2026, 10, 1).date(),
)


def test_formula_de_trabajo_es_el_ligante_de_la_receta_en_puntos() -> None:
    assert vial.formula_asfalto_de_receta(MEZCLA, "LIG-001") == D("5.5")


@pytest.mark.parametrize("codigo", [None, "", "NO-HAY", "DIE-001"])
def test_sin_ligante_en_toneladas_no_hay_formula(codigo: str | None) -> None:
    assert vial.formula_asfalto_de_receta(MEZCLA, codigo) is None


def test_sin_receta_no_hay_formula() -> None:
    assert vial.formula_asfalto_de_receta(None, "LIG-001") is None


def test_reglas_viales_de_una_version_con_tramos_heredados(sesion: Session) -> None:
    v1, v2 = _version(sesion, "VIV-001"), _version(sesion, "VIV-002")
    assert vial.reglas_viales(sesion, v2) == ()  # sin tramos, sin reglas
    vial.guardar_tramos(sesion, v2, [T1, T2], usuario=ANA, ahora=LUNES)
    (regla,) = vial.reglas_viales(sesion, v2, receta=MEZCLA, codigo_ligante="LIG-001")
    assert isinstance(regla, ReglasViales)
    assert regla.tramos == (T1, T2) and regla.formula_asfalto_pct == D("5.5")
    (sin_receta,) = vial.reglas_viales(sesion, v2)
    assert sin_receta.formula_asfalto_pct is None
    assert v1 != v2


# --- Tarea 16c: el ligante marcado manda sobre la regla del único comprado en t -------------------


def _con_arena() -> Receta:
    return Receta(
        2,
        "MZP-002",
        (
            Componente("AGP-001", D("0.80"), "t", "propio"),
            Componente("ARE-001", D("0.15"), "t", "comprado"),
            Componente("LIG-001", D("0.05"), "t", "comprado", es_ligante=True),
        ),
        "fórmula ficticia con arena comprada",
        datetime(2026, 10, 1).date(),
    )


def test_el_ligante_marcado_da_la_formula_aunque_haya_otro_comprado_en_t() -> None:
    # oráculo a mano: 0,05 t de asfalto por t de mezcla son 5 puntos, no los 15 de la arena
    assert vial.formula_asfalto_de_receta(_con_arena(), None) == D("5")
    assert vial.formula_asfalto_de_receta(_con_arena(), "LIG-001") == D("5")


def test_la_marca_manda_sobre_el_codigo_dado() -> None:
    assert vial.formula_asfalto_de_receta(_con_arena(), "ARE-001") == D("5")
