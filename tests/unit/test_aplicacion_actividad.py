"""C10: la actividad de una cuenta, como la página de actividad de GitHub (solo lectura).

`aplicacion/actividad.py` junta, de datos que ya se guardan, lo que hizo una cuenta: las versiones
que guardó (`eslabon_version.usuario` y `.fecha_hora`, de la carpeta), las que envió a aprobación y
los dictámenes que dio (`mp_indice_aprobacion.enviado_por/enviado_el` y `dictamen_por/dictamen_el`)
y los libros que auditó (`auditoria_libro.usuario` y `.fecha_hora`).

Datos ficticios (Ana, Rita, «Vivienda Demo 80 m2»). Oráculos escritos a mano: los textos, las
cifras y los días salen de contar a mano lo sembrado, no del código bajo prueba.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session

from aplicacion import actividad
from aplicacion.actividad import Actividad, Cifras, DiaConActividad, Evento
from aplicacion.tablas_indice_aprobacion import METADATA_INDICE_APROBACION, FilaIndiceAprobacion
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.models.cadena import EslabonVersion
from fusion.historial import HallazgoCompacto, registrar_auditoria
from fusion.historial_modelo import METADATA_HISTORIAL
from tests.fixtures.carpeta_aprobaciones import guardar_version, sembrar_vivienda

ANA = "Ana Demo <ana>"
RITA = "Rita Demo <rita>"
OBRA = "Vivienda Demo 80 m2"
SHA = "ab" * 32
DESDE = date(2026, 10, 1)
HASTA = date(2026, 10, 31)
LUNES = datetime(2026, 10, 19, 9, 0)
MARTES = datetime(2026, 10, 20, 10, 30)
MIERCOLES = datetime(2026, 10, 21, 11, 15, 20)


@pytest.fixture
def instalacion() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    METADATA_INDICE_APROBACION.create_all(motor)
    METADATA_HISTORIAL.create_all(motor)
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


@pytest.fixture
def caso(tmp_path: Path) -> Iterator[Session]:
    """La carpeta ficticia con VIV-001 (Ana, lunes 19) y VIV-002 (Rita, martes 20)."""
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as s:
        obra = sembrar_vivienda(s, usuario=ANA)
        guardar_version(s, obra, "VIV-002", usuario=RITA)
        s.execute(
            update(EslabonVersion)
            .where(EslabonVersion.presupuesto_id == 1)
            .values(fecha_hora=LUNES)
        )
        s.execute(
            update(EslabonVersion)
            .where(EslabonVersion.presupuesto_id == 2)
            .values(fecha_hora=MARTES)
        )
        s.commit()
        yield s
    motor.dispose()


def _envio(sesion: Session, n: int, por: str, el: datetime, **extra) -> None:
    campos = {
        "caso": "caso.db",
        "envio_id": n,
        "proyecto": "1",
        "obra": OBRA,
        "version": "VIV-001",
        "total": Decimal("100.00"),
        "moneda": "Bs",
        "estado": "en_aprobacion",
        "enviado_por": por,
        "enviado_el": el,
        "dictamen_por": None,
        "dictamen_el": None,
        "nota": "",
        "notas": "",
        "armo": False,
    }
    sesion.add(FilaIndiceAprobacion(**{**campos, **extra}))
    sesion.flush()


def _auditoria(sesion: Session, por: str, el: datetime, archivo: str, errores: int) -> None:
    registrar_auditoria(
        sesion,
        usuario=por,
        tipo="libro",
        nombre_archivo=archivo,
        sha256=SHA,
        fecha_libro=None,
        total_libro=None,
        total_silice=None,
        hallazgos=[HallazgoCompacto("L4", "APU-02", f"G{i}", "ERROR", "x") for i in range(errores)],
        ahora=el,
    )


# --- la cuenta sin actividad ---------------------------------------------------------------------


def test_una_cuenta_sin_actividad_da_todo_en_cero(instalacion: Session, caso: Session) -> None:
    resultado = actividad.actividad_de(instalacion, "tomas", DESDE, HASTA, caso=caso)
    assert resultado == Actividad(dias=(), cifras=Cifras(0, 0, 0, 0), eventos=(), recortado=False)


def test_sin_carpeta_no_cuenta_versiones_guardadas(instalacion: Session) -> None:
    _auditoria(instalacion, ANA, LUNES, "Presupuesto cliente A.xlsx", 3)
    resultado = actividad.actividad_de(instalacion, "ana", DESDE, HASTA)
    assert resultado.cifras == Cifras(0, 0, 0, 1)


# --- varios tipos el mismo día -------------------------------------------------------------------


def test_cuatro_tipos_el_mismo_dia_suman_cuatro_en_ese_dia(
    instalacion: Session, caso: Session
) -> None:
    # Ana guardó VIV-001 el lunes 19 (9:00); ese día también envió, dictaminó y auditó.
    _envio(
        instalacion,
        1,
        ANA,
        datetime(2026, 10, 19, 10, 0),
        estado="aprobada",
        dictamen_por=ANA,
        dictamen_el=datetime(2026, 10, 19, 12, 0),
    )
    _auditoria(instalacion, ANA, datetime(2026, 10, 19, 15, 30), "Presupuesto cliente A.xlsx", 3)
    resultado = actividad.actividad_de(instalacion, "ana", DESDE, HASTA, caso=caso)
    assert resultado.dias == (DiaConActividad(date(2026, 10, 19), 4),)
    assert resultado.cifras == Cifras(
        versiones_guardadas=1, versiones_enviadas=1, dictamenes=1, auditorias=1
    )
    assert [e.tipo for e in resultado.eventos] == [
        "auditoria",
        "dictamen",
        "version_enviada",
        "version_guardada",
    ]


def test_los_dias_van_en_orden_y_solo_los_que_tuvieron_actividad(
    instalacion: Session, caso: Session
) -> None:
    _auditoria(instalacion, ANA, MIERCOLES, "libro.xlsx", 0)
    _auditoria(instalacion, ANA, datetime(2026, 10, 21, 18, 0), "otro.xlsx", 1)
    resultado = actividad.actividad_de(instalacion, "ana", DESDE, HASTA, caso=caso)
    assert resultado.dias == (
        DiaConActividad(date(2026, 10, 19), 1),
        DiaConActividad(date(2026, 10, 21), 2),
    )


# --- los textos ----------------------------------------------------------------------------------


def test_el_texto_de_una_version_guardada(instalacion: Session, caso: Session) -> None:
    (evento,) = actividad.actividad_de(instalacion, "ana", DESDE, HASTA, caso=caso).eventos
    assert evento == Evento(
        fecha_hora=LUNES,
        tipo="version_guardada",
        obra=OBRA,
        archivo="",
        texto=f"guardó la versión VIV-001 de {OBRA}",
    )


@pytest.mark.parametrize(
    ("estado", "texto"),
    [
        ("aprobada", f"aprobó la versión VIV-001 de {OBRA}"),
        ("aprobada_con_observaciones", f"aprobó con observaciones la versión VIV-001 de {OBRA}"),
        ("devuelta", f"devolvió la versión VIV-001 de {OBRA}"),
    ],
)
def test_el_texto_de_cada_dictamen(instalacion: Session, estado: str, texto: str) -> None:
    _envio(
        instalacion,
        1,
        ANA,
        LUNES,
        estado=estado,
        dictamen_por=RITA,
        dictamen_el=MARTES,
    )
    (evento,) = actividad.actividad_de(instalacion, "rita", DESDE, HASTA).eventos
    assert (evento.tipo, evento.fecha_hora, evento.obra, evento.texto) == (
        "dictamen",
        MARTES,
        OBRA,
        texto,
    )


def test_el_texto_de_un_envio(instalacion: Session) -> None:
    _envio(instalacion, 1, ANA, LUNES)
    (evento,) = actividad.actividad_de(instalacion, "ana", DESDE, HASTA).eventos
    assert evento.tipo == "version_enviada"
    assert evento.texto == f"envió la versión VIV-001 de {OBRA} a aprobación"


@pytest.mark.parametrize(
    ("errores", "texto"),
    [
        (3, "auditó Presupuesto cliente A.xlsx: 3 errores"),
        (1, "auditó Presupuesto cliente A.xlsx: 1 error"),
        (0, "auditó Presupuesto cliente A.xlsx: sin errores"),
    ],
)
def test_el_texto_de_una_auditoria(instalacion: Session, errores: int, texto: str) -> None:
    _auditoria(instalacion, ANA, LUNES, "Presupuesto cliente A.xlsx", errores)
    (evento,) = actividad.actividad_de(instalacion, "ana", DESDE, HASTA).eventos
    assert (evento.tipo, evento.archivo, evento.obra, evento.texto) == (
        "auditoria",
        "Presupuesto cliente A.xlsx",
        "",
        texto,
    )


# --- de quién es cada cosa -----------------------------------------------------------------------


def test_solo_cuenta_lo_de_la_cuenta_pedida(instalacion: Session, caso: Session) -> None:
    _envio(instalacion, 1, ANA, LUNES)
    _envio(instalacion, 2, RITA, MARTES, version="VIV-002")
    _auditoria(instalacion, RITA, MARTES, "de Rita.xlsx", 2)
    rita = actividad.actividad_de(instalacion, "rita", DESDE, HASTA, caso=caso)
    assert rita.cifras == Cifras(
        versiones_guardadas=1, versiones_enviadas=1, dictamenes=0, auditorias=1
    )
    assert {e.obra for e in rita.eventos if e.tipo == "version_enviada"} == {OBRA}


def test_se_reconoce_la_cuenta_por_su_login_aunque_cambie_el_nombre(
    instalacion: Session,
) -> None:
    _auditoria(instalacion, "Ana Pérez <ana>", LUNES, "a.xlsx", 0)
    _auditoria(instalacion, "Ana Demo <ana> (tras restablecimiento)", MARTES, "b.xlsx", 0)
    assert actividad.actividad_de(instalacion, "ana", DESDE, HASTA).cifras.auditorias == 2


def test_un_texto_sin_login_se_compara_completo(instalacion: Session) -> None:
    _auditoria(instalacion, "ana", LUNES, "a.xlsx", 0)
    assert actividad.actividad_de(instalacion, "ana", DESDE, HASTA).cifras.auditorias == 1
    assert actividad.actividad_de(instalacion, "rita", DESDE, HASTA).cifras.auditorias == 0


def test_un_envio_retirado_o_pendiente_no_cuenta_como_dictamen(instalacion: Session) -> None:
    _envio(instalacion, 1, ANA, LUNES, estado="retirada")
    _envio(instalacion, 2, ANA, MARTES, estado="en_aprobacion")
    resultado = actividad.actividad_de(instalacion, "ana", DESDE, HASTA)
    assert resultado.cifras == Cifras(0, 2, 0, 0)


def test_una_retirada_con_quien_y_cuando_tampoco_es_dictamen(instalacion: Session) -> None:
    # Mata el mutante que cuenta «retirada» como dictamen cuando la fila sí trae quién la
    # cerró y cuándo.
    _envio(instalacion, 1, ANA, LUNES, estado="retirada", dictamen_por=ANA, dictamen_el=MARTES)
    assert actividad.actividad_de(instalacion, "ana", DESDE, HASTA).cifras == Cifras(0, 1, 0, 0)


def test_quien_dictamina_y_quien_envio_son_cada_uno_su_evento(instalacion: Session) -> None:
    _envio(instalacion, 1, ANA, LUNES, estado="devuelta", dictamen_por=RITA, dictamen_el=MARTES)
    assert actividad.actividad_de(instalacion, "ana", DESDE, HASTA).cifras == Cifras(0, 1, 0, 0)
    assert actividad.actividad_de(instalacion, "rita", DESDE, HASTA).cifras == Cifras(0, 0, 1, 0)


# --- el rango ------------------------------------------------------------------------------------


def test_el_rango_incluye_los_dos_dias_de_los_extremos(instalacion: Session) -> None:
    _auditoria(instalacion, ANA, datetime(2026, 9, 30, 23, 59, 59), "antes.xlsx", 0)
    _auditoria(instalacion, ANA, datetime(2026, 10, 1, 0, 0, 0), "primero.xlsx", 0)
    _auditoria(instalacion, ANA, datetime(2026, 10, 31, 23, 59, 59), "ultimo.xlsx", 0)
    _auditoria(instalacion, ANA, datetime(2026, 11, 1, 0, 0, 0), "despues.xlsx", 0)
    resultado = actividad.actividad_de(instalacion, "ana", DESDE, HASTA)
    assert [e.archivo for e in resultado.eventos] == ["ultimo.xlsx", "primero.xlsx"]
    assert [d.fecha for d in resultado.dias] == [date(2026, 10, 1), date(2026, 10, 31)]


def test_un_solo_dia_como_rango(instalacion: Session, caso: Session) -> None:
    resultado = actividad.actividad_de(
        instalacion, "ana", date(2026, 10, 19), date(2026, 10, 19), caso=caso
    )
    assert resultado.cifras.versiones_guardadas == 1
    fuera = actividad.actividad_de(
        instalacion, "ana", date(2026, 10, 20), date(2026, 10, 20), caso=caso
    )
    assert fuera.cifras == Cifras(0, 0, 0, 0)


def test_un_rango_al_reves_es_un_error(instalacion: Session) -> None:
    with pytest.raises(ValueError, match="desde"):
        actividad.actividad_de(instalacion, "ana", HASTA, DESDE)


# --- el orden y el tope de los eventos ------------------------------------------------------------


def test_los_eventos_van_del_mas_reciente_al_mas_antiguo(
    instalacion: Session, caso: Session
) -> None:
    _auditoria(instalacion, ANA, MIERCOLES, "tercero.xlsx", 0)
    _envio(instalacion, 1, ANA, MARTES)
    resultado = actividad.actividad_de(instalacion, "ana", DESDE, HASTA, caso=caso)
    assert [e.fecha_hora for e in resultado.eventos] == [MIERCOLES, MARTES, LUNES]


def test_armar_recorta_los_eventos_pero_no_las_cifras() -> None:
    eventos = [
        Evento(datetime(2026, 10, dia, 8, 0), "auditoria", "", f"{dia}.xlsx", f"auditó {dia}")
        for dia in (1, 2, 3, 4)
    ]
    resultado = actividad.armar(eventos, DESDE, HASTA, limite_eventos=2)
    assert resultado.recortado is True
    assert [e.archivo for e in resultado.eventos] == ["4.xlsx", "3.xlsx"]
    assert resultado.cifras.auditorias == 4
    assert len(resultado.dias) == 4


def test_armar_sin_pasar_del_tope_no_marca_recorte() -> None:
    resultado = actividad.armar([], DESDE, HASTA, limite_eventos=2)
    assert resultado.recortado is False


# --- la cuenta existe ----------------------------------------------------------------------------


def test_cuenta_existe_mira_el_login_normalizado(tmp_path: Path) -> None:
    from tests.fixtures.instalacion import administrador
    from tests.fixtures.instalacion import instalacion as base_nueva

    with base_nueva(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        sesion.commit()
        assert actividad.cuenta_existe(sesion, "admin") is True
        assert actividad.cuenta_existe(sesion, "  ADMIN ") is True
        assert actividad.cuenta_existe(sesion, "nadie") is False
