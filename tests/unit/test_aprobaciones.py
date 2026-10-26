"""MP-4, Tarea 17: envíos, dictámenes y rastro encadenado de las aprobaciones (diseño de montar un
presupuesto §5.4 y §10: un solo envío pendiente por obra, la devuelta no se reenvía, quien arma
también aprueba y queda rotulado, rastro verificable fuera de `core/`).

Base SQLite en archivo (`tmp_path`, WAL como la de una carpeta real) con `crear_esquema` del núcleo
y `crear_esquema_aprobacion`; obra ficticia «Vivienda Demo 80 m2» con VIV-001 y VIV-002 guardadas
por el embudo del núcleo a nombre de «Ana <ana>» (otra obra, «Galpón Demo», con GAL-001). Oráculos
escritos a mano: los mensajes, los estados y cada huella, recalculada aquí con `json` y `hashlib`
sobre la fórmula del plan (sin pasar por el código bajo prueba); la huella del eslabón de cada
versión se lee de `eslabon_version`, que sella el núcleo.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aplicacion import aprobaciones
from aplicacion.aprobaciones import (
    ESTADOS,
    AprobacionInvalida,
    EstadoDeVersion,
    RastroVerificado,
)
from aplicacion.tablas_aprobacion import FilaEventoAprobacion, crear_esquema_aprobacion
from core import models
from core.budget import crear_proyecto
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.contracts.dominio import Dominio
from core.models.cadena import EslabonVersion
from tests.fixtures.canonico_minimo import FECHA, RELLENO, guardar_otra

OBRA = "Vivienda Demo 80 m2"
OTRA_OBRA = "Galpón Demo"
ANA = "Ana <ana>"
RITA = "Rita <rita>"
CERO = "0" * 64  # el génesis, escrito a mano

LUNES = datetime(2026, 10, 19, 9, 0)
MARTES = datetime(2026, 10, 20, 10, 30)
MIERCOLES = datetime(2026, 10, 21, 11, 15, 20)
JUEVES = datetime(2026, 10, 22, 16, 45)

YA_EN_APROBACION = "La versión VIV-001 ya está en aprobación."
YA_APROBADA = "La versión VIV-002 ya está aprobada."
DEVUELTA = "La versión VIV-001 fue devuelta: corríjala en una versión nueva y envíe esa."
SIN_NOTAS = "Escriba las notas: son obligatorias para devolver o aprobar con observaciones."
CERRADO = "Este envío ya tiene dictamen o fue retirado."
INTEGRO = "Rastro de aprobaciones íntegro."


def _rota(evento: int) -> str:
    return f"El rastro de aprobaciones se rompió en el evento n.º {evento}."


# --- la carpeta ficticia ------------------------------------------------------------------------


@pytest.fixture
def motor(tmp_path: Path) -> Iterator[Engine]:
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    crear_esquema(motor)
    crear_esquema_aprobacion(motor)
    try:
        with abrir_sesion(motor) as s:
            lista = models.ListaPrecios(
                nombre="Lista de prueba", moneda="USD", fecha_vigencia=FECHA, origen="prueba"
            )
            s.add(lista)
            s.flush()
            Catalogo(s).cargar_composicion(RELLENO, lista, Dominio.CIVIL, FECHA, "prueba")
            vivienda = crear_proyecto(s, OBRA, dominio=Dominio.CIVIL)
            galpon = crear_proyecto(s, OTRA_OBRA, dominio=Dominio.CIVIL)
            v1 = guardar_otra(s, vivienda, lista, "VIV-001", usuario=ANA)
            s.commit()
            guardar_otra(
                s,
                vivienda,
                lista,
                "VIV-002",
                "30",
                usuario=ANA,
                version_origen=v1,
                motivo="edicion",
            )
            s.commit()
            guardar_otra(s, galpon, lista, "GAL-001", usuario=RITA)
            s.commit()
        yield motor
    finally:
        motor.dispose()


@pytest.fixture
def sesion(motor: Engine) -> Iterator[Session]:
    with abrir_sesion(motor) as s:
        yield s


def _sha_json(objeto: dict) -> str:
    return hashlib.sha256(
        json.dumps(objeto, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _proyecto_id(s: Session, nombre: str) -> int:
    return s.scalars(select(models.Proyecto.id).where(models.Proyecto.nombre == nombre)).one()


def _sello(s: Session, codigo: str) -> str:
    """La `huella_eslabon` que el núcleo selló para la versión `codigo`."""
    return s.scalars(
        select(EslabonVersion.huella_eslabon)
        .join(models.Presupuesto, models.Presupuesto.id == EslabonVersion.presupuesto_id)
        .where(models.Presupuesto.codigo == codigo)
    ).one()


def _filas(s: Session) -> list[FilaEventoAprobacion]:
    s.expire_all()
    return list(s.scalars(select(FilaEventoAprobacion).order_by(FilaEventoAprobacion.id)))


def _cuenta(s: Session, tipo: str | None = None) -> int:
    consulta = select(func.count()).select_from(FilaEventoAprobacion)
    if tipo is not None:
        consulta = consulta.where(FilaEventoAprobacion.tipo == tipo)
    return s.scalar(consulta)


def _enviar(s: Session, version: str, ahora: datetime = LUNES, nota: str = "", usuario=ANA):
    return aprobaciones.enviar(s, OBRA, version, nota=nota, usuario=usuario, ahora=ahora)


def _dictaminar(
    s: Session, envio_id: int, resultado: str, notas: str = "", usuario=RITA, ahora=MARTES
):
    return aprobaciones.dictaminar(
        s, envio_id, resultado=resultado, notas=notas, usuario=usuario, ahora=ahora
    )


def _mensaje(error: pytest.ExceptionInfo) -> str:
    return str(error.value)


# --- estados ------------------------------------------------------------------------------------


def test_los_estados_son_los_del_diseno() -> None:
    assert ESTADOS == (
        "guardada",
        "en_aprobacion",
        "retirada",
        "aprobada",
        "aprobada_con_observaciones",
        "devuelta",
    )
    assert issubclass(AprobacionInvalida, ValueError)


def test_sin_eventos_las_versiones_estan_guardadas(sesion: Session) -> None:
    assert aprobaciones.estados(sesion, OBRA) == {
        "VIV-001": EstadoDeVersion("guardada", None, None, "", False),
        "VIV-002": EstadoDeVersion("guardada", None, None, "", False),
    }
    assert aprobaciones.historial(sesion, OBRA) == []
    assert aprobaciones.fases(sesion, OBRA) == ""
    assert aprobaciones.ultima_aprobada(sesion, OBRA) is None
    assert aprobaciones.verificar_rastro(sesion, OBRA) == RastroVerificado(True, INTEGRO)


def test_enviar_deja_la_version_en_aprobacion(sesion: Session) -> None:
    envio = _enviar(sesion, "VIV-001", nota="Primera entrega")

    assert envio.retirada is None
    estados = aprobaciones.estados(sesion, OBRA)
    assert estados["VIV-001"] == EstadoDeVersion(
        "en_aprobacion", ANA, LUNES, "Primera entrega", True
    )
    assert estados["VIV-002"].estado == "guardada"
    (fila,) = _filas(sesion)
    assert (fila.id, fila.tipo, fila.version, fila.cierre_de, fila.resultado) == (
        envio.id,
        "envio",
        "VIV-001",
        None,
        None,
    )


def test_el_proyecto_tambien_se_nombra_por_su_codigo(sesion: Session) -> None:
    codigo = str(_proyecto_id(sesion, OBRA))
    aprobaciones.enviar(sesion, codigo, "VIV-001", nota="", usuario=ANA, ahora=LUNES)
    assert aprobaciones.estados(sesion, codigo)["VIV-001"].estado == "en_aprobacion"
    assert aprobaciones.estados(sesion, OBRA)["VIV-001"].estado == "en_aprobacion"


def test_enviar_otra_version_retira_la_pendiente(sesion: Session) -> None:
    primero = _enviar(sesion, "VIV-001")
    segundo = _enviar(sesion, "VIV-002", ahora=MARTES)

    assert segundo.retirada == "VIV-001"
    estados = aprobaciones.estados(sesion, OBRA)
    assert estados["VIV-001"] == EstadoDeVersion("retirada", ANA, MARTES, "", True)
    assert estados["VIV-002"].estado == "en_aprobacion"
    envio, retiro, otro = _filas(sesion)
    assert [envio.tipo, retiro.tipo, otro.tipo] == ["envio", "retiro", "envio"]
    assert (retiro.version, retiro.cierre_de) == ("VIV-001", primero.id)
    assert otro.id == segundo.id and otro.version == "VIV-002"


def test_reenviar_la_que_esta_en_aprobacion_no_se_puede(sesion: Session) -> None:
    _enviar(sesion, "VIV-001")
    with pytest.raises(AprobacionInvalida) as error:
        _enviar(sesion, "VIV-001", ahora=MARTES)
    assert _mensaje(error) == YA_EN_APROBACION
    assert _cuenta(sesion) == 1


def test_una_retirada_se_puede_volver_a_enviar(sesion: Session) -> None:
    _enviar(sesion, "VIV-001")
    _enviar(sesion, "VIV-002", ahora=MARTES)
    envio = _enviar(sesion, "VIV-001", ahora=MIERCOLES)
    assert envio.retirada == "VIV-002"
    estados = aprobaciones.estados(sesion, OBRA)
    assert (estados["VIV-001"].estado, estados["VIV-002"].estado) == ("en_aprobacion", "retirada")


# --- dictámenes ---------------------------------------------------------------------------------


@pytest.mark.parametrize("resultado", ["devuelta", "aprobada_con_observaciones"])
@pytest.mark.parametrize("notas", ["", "   \n "])
def test_devolver_o_observar_sin_notas_no_se_puede(sesion: Session, resultado, notas) -> None:
    envio = _enviar(sesion, "VIV-001")
    with pytest.raises(AprobacionInvalida) as error:
        _dictaminar(sesion, envio.id, resultado, notas)
    assert _mensaje(error) == SIN_NOTAS
    assert _cuenta(sesion) == 1
    assert aprobaciones.estados(sesion, OBRA)["VIV-001"].estado == "en_aprobacion"


def test_devolver_con_notas_y_la_devuelta_no_se_reenvia(sesion: Session) -> None:
    envio = _enviar(sesion, "VIV-001")
    dictamen = _dictaminar(sesion, envio.id, "devuelta", "Falta el acero de la losa.")

    assert aprobaciones.estados(sesion, OBRA)["VIV-001"] == EstadoDeVersion(
        "devuelta", RITA, MARTES, "Falta el acero de la losa.", False
    )
    fila = _filas(sesion)[-1]
    assert (fila.id, fila.tipo, fila.cierre_de, fila.resultado) == (
        dictamen,
        "dictamen",
        envio.id,
        "devuelta",
    )
    with pytest.raises(AprobacionInvalida) as error:
        _enviar(sesion, "VIV-001", ahora=MIERCOLES)
    assert _mensaje(error) == DEVUELTA
    assert _cuenta(sesion) == 2


@pytest.mark.parametrize("resultado", ["aprobada", "aprobada_con_observaciones"])
def test_la_aprobada_no_se_reenvia(sesion: Session, resultado) -> None:
    envio = _enviar(sesion, "VIV-002")
    _dictaminar(sesion, envio.id, resultado, "Revisar el acarreo en obra.")
    assert aprobaciones.estados(sesion, OBRA)["VIV-002"].estado == resultado
    with pytest.raises(AprobacionInvalida) as error:
        _enviar(sesion, "VIV-002", ahora=MIERCOLES)
    assert _mensaje(error) == YA_APROBADA


def test_aprobar_sin_notas_si_se_puede(sesion: Session) -> None:
    envio = _enviar(sesion, "VIV-001")
    _dictaminar(sesion, envio.id, "aprobada")
    assert aprobaciones.estados(sesion, OBRA)["VIV-001"] == EstadoDeVersion(
        "aprobada", RITA, MARTES, "", False
    )


def test_un_dictamen_desconocido_no_se_registra(sesion: Session) -> None:
    envio = _enviar(sesion, "VIV-001")
    with pytest.raises(AprobacionInvalida) as error:
        _dictaminar(sesion, envio.id, "aprobadisima", "x")
    assert _mensaje(error) == (
        "Elija el dictamen: aprobada, aprobada con observaciones o devuelta."
    )
    assert _cuenta(sesion) == 1


def test_dos_dictamenes_seguidos_sobre_el_mismo_envio(sesion: Session) -> None:
    """Foco 3: el segundo dictamen se rechaza y no queda rastro doble."""
    envio = _enviar(sesion, "VIV-001")
    _dictaminar(sesion, envio.id, "aprobada")
    with pytest.raises(AprobacionInvalida) as error:
        _dictaminar(sesion, envio.id, "devuelta", "Otra opinión.", ahora=MIERCOLES)
    assert _mensaje(error) == CERRADO
    assert _cuenta(sesion, "dictamen") == 1
    assert aprobaciones.estados(sesion, OBRA)["VIV-001"].estado == "aprobada"


def test_dictaminar_un_envio_retirado_no_se_puede(sesion: Session) -> None:
    primero = _enviar(sesion, "VIV-001")
    _enviar(sesion, "VIV-002", ahora=MARTES)
    with pytest.raises(AprobacionInvalida) as error:
        _dictaminar(sesion, primero.id, "aprobada", ahora=MIERCOLES)
    assert _mensaje(error) == CERRADO
    assert _cuenta(sesion, "dictamen") == 0


def test_dos_sesiones_que_leen_el_mismo_anterior(motor: Engine, monkeypatch) -> None:
    """Foco 3: dos dictámenes a la vez. La sesión lenta ya leyó el envío abierto y el último
    eslabón del rastro cuando la rápida confirma el suyo; al escribir, la lenta recibe el mensaje
    de envío cerrado y solo queda el dictamen de la rápida."""
    with abrir_sesion(motor) as s:
        envio = _enviar(s, "VIV-001")
    real = aprobaciones._cabeza
    leidas: list[str] = []

    def cabeza_con_carrera(sesion_lenta: Session, proyecto_id: int) -> str:
        leida = real(sesion_lenta, proyecto_id)
        if not leidas:
            leidas.append(leida)
            with abrir_sesion(motor) as rapida:
                _dictaminar(rapida, envio.id, "aprobada", usuario=RITA, ahora=MARTES)
        return leida

    monkeypatch.setattr(aprobaciones, "_cabeza", cabeza_con_carrera)
    with abrir_sesion(motor) as lenta:
        with pytest.raises(AprobacionInvalida) as error:
            _dictaminar(lenta, envio.id, "devuelta", "Tarde.", usuario=ANA, ahora=MIERCOLES)
    assert _mensaje(error) == CERRADO
    assert len(leidas) == 1  # la carrera ocurrió de verdad
    with abrir_sesion(motor) as s:
        assert _cuenta(s, "dictamen") == 1
        assert aprobaciones.estados(s, OBRA)["VIV-001"] == EstadoDeVersion(
            "aprobada", RITA, MARTES, "", False
        )
        assert aprobaciones.verificar_rastro(s, OBRA) == RastroVerificado(True, INTEGRO)


def test_la_base_rechaza_dos_cierres_del_mismo_envio_y_dos_hijos_del_mismo_anterior(
    sesion: Session,
) -> None:
    """La salvaguarda vive en la base, no solo en la lógica: `cierre_de` es único y
    (`proyecto_id`, `anterior`) también."""
    envio = _enviar(sesion, "VIV-001")
    _dictaminar(sesion, envio.id, "aprobada")
    dictamen = _filas(sesion)[-1]
    campos = {
        "proyecto_id": dictamen.proyecto_id,
        "tipo": "dictamen",
        "version": "VIV-001",
        "huella_version": dictamen.huella_version,
        "resultado": "devuelta",
        "notas": "a mano",
        "usuario": ANA,
        "fecha_hora": MIERCOLES,
        "armo": True,
        "huella": "f" * 64,
    }
    sesion.add(FilaEventoAprobacion(**campos, cierre_de=envio.id, anterior="e" * 64))
    with pytest.raises(IntegrityError):
        sesion.flush()
    sesion.rollback()
    sesion.add(FilaEventoAprobacion(**campos, cierre_de=None, anterior=dictamen.anterior))
    with pytest.raises(IntegrityError):
        sesion.flush()
    sesion.rollback()
    assert _cuenta(sesion) == 2


def test_todo_o_nada_si_falla_el_envio_no_queda_el_retiro(sesion: Session, monkeypatch) -> None:
    _enviar(sesion, "VIV-001")
    real = aprobaciones._huella
    llamadas: list[int] = []

    def huella_que_falla_la_segunda_vez(**campos):
        llamadas.append(1)
        if len(llamadas) == 2:
            raise RuntimeError("disco lleno (simulado)")
        return real(**campos)

    monkeypatch.setattr(aprobaciones, "_huella", huella_que_falla_la_segunda_vez)
    with pytest.raises(RuntimeError, match="simulado"):
        _enviar(sesion, "VIV-002", ahora=MARTES)
    assert len(llamadas) == 2  # el retiro ya estaba armado cuando falló el envío
    assert _cuenta(sesion) == 1
    estados = aprobaciones.estados(sesion, OBRA)
    assert (estados["VIV-001"].estado, estados["VIV-002"].estado) == ("en_aprobacion", "guardada")


# --- quien la armó ------------------------------------------------------------------------------


def test_ana_aprueba_su_propia_version_y_queda_rotulado(sesion: Session) -> None:
    envio = _enviar(sesion, "VIV-002")
    dictamen = _dictaminar(sesion, envio.id, "aprobada", usuario=ANA)

    estado = aprobaciones.estados(sesion, OBRA)["VIV-002"]
    assert estado.armo is True and estado.por == ANA
    assert [e.armo for e in aprobaciones.historial(sesion, OBRA) if e.id == dictamen] == [True]


def test_quien_armo_se_reconoce_por_su_cuenta_aunque_cambie_el_nombre(sesion: Session) -> None:
    envio = _enviar(sesion, "VIV-002")
    _dictaminar(sesion, envio.id, "aprobada", usuario="Ana María Pérez <ana>")
    assert aprobaciones.estados(sesion, OBRA)["VIV-002"].armo is True


def test_quien_armo_es_quien_guardo_la_version_no_quien_la_envio(sesion: Session) -> None:
    """Decisión 7 ratificada: la armó quien la guardó (el usuario de su eslabón)."""
    envio = aprobaciones.enviar(sesion, OBRA, "VIV-001", nota="", usuario=RITA, ahora=LUNES)
    assert aprobaciones.estados(sesion, OBRA)["VIV-001"].armo is False  # Rita la envió, no la armó
    _dictaminar(sesion, envio.id, "aprobada", usuario=ANA)
    assert aprobaciones.estados(sesion, OBRA)["VIV-001"].armo is True


# --- fases y última aprobada --------------------------------------------------------------------


def test_fases_y_ultima_aprobada(sesion: Session) -> None:
    envio = _enviar(sesion, "VIV-001")
    _dictaminar(sesion, envio.id, "devuelta", "Falta el acero de la losa.")
    assert aprobaciones.ultima_aprobada(sesion, OBRA) is None
    envio = _enviar(sesion, "VIV-002", ahora=MIERCOLES)
    assert aprobaciones.fases(sesion, OBRA) == "VIV-001 devuelta → VIV-002 en aprobación"
    _dictaminar(sesion, envio.id, "aprobada", ahora=JUEVES)

    assert aprobaciones.fases(sesion, OBRA) == "VIV-001 devuelta → VIV-002 aprobada"
    assert aprobaciones.ultima_aprobada(sesion, OBRA) == "VIV-002"


def test_fases_con_retiro_y_observaciones(sesion: Session) -> None:
    _enviar(sesion, "VIV-001")
    envio = _enviar(sesion, "VIV-002", ahora=MARTES)
    _dictaminar(sesion, envio.id, "aprobada_con_observaciones", "Revisar el acarreo.", ahora=JUEVES)
    assert aprobaciones.fases(sesion, OBRA) == (
        "VIV-001 retirada → VIV-002 aprobada con observaciones"
    )
    assert aprobaciones.ultima_aprobada(sesion, OBRA) == "VIV-002"


def test_cada_obra_lleva_su_propio_rastro(sesion: Session) -> None:
    _enviar(sesion, "VIV-001")
    galpon = aprobaciones.enviar(sesion, OTRA_OBRA, "GAL-001", nota="", usuario=RITA, ahora=MARTES)

    assert galpon.retirada is None  # el envío pendiente de otra obra no se retira
    assert aprobaciones.estados(sesion, OBRA)["VIV-001"].estado == "en_aprobacion"
    assert aprobaciones.estados(sesion, OTRA_OBRA) == {
        "GAL-001": EstadoDeVersion("en_aprobacion", RITA, MARTES, "", True)
    }
    vivienda, otra = _filas(sesion)
    assert vivienda.anterior == otra.anterior == CERO
    assert [e.version for e in aprobaciones.historial(sesion, OTRA_OBRA)] == ["GAL-001"]


# --- el rastro ----------------------------------------------------------------------------------


def test_cada_huella_sigue_la_formula_del_plan(sesion: Session) -> None:
    envio = _enviar(sesion, "VIV-001", nota="Primera entrega: «losa» y ñandú")
    segundo = _enviar(sesion, "VIV-002", ahora=MARTES)
    dictamen = _dictaminar(sesion, segundo.id, "devuelta", "Falta el acero.", ahora=MIERCOLES)
    proyecto_id = _proyecto_id(sesion, OBRA)
    sello_1, sello_2 = _sello(sesion, "VIV-001"), _sello(sesion, "VIV-002")

    esperada_1 = _sha_json(
        {
            "anterior": CERO,
            "tipo": "envio",
            "proyecto_id": proyecto_id,
            "version": "VIV-001",
            "huella_version": sello_1,
            "resultado": None,
            "notas": "Primera entrega: «losa» y ñandú",
            "usuario": ANA,
            "fecha_hora": "2026-10-19T09:00:00",
            "armo": True,
            "cierre_de": None,
        }
    )
    esperada_2 = _sha_json(
        {
            "anterior": esperada_1,
            "tipo": "retiro",
            "proyecto_id": proyecto_id,
            "version": "VIV-001",
            "huella_version": sello_1,
            "resultado": None,
            "notas": "",
            "usuario": ANA,
            "fecha_hora": "2026-10-20T10:30:00",
            "armo": True,
            "cierre_de": envio.id,
        }
    )
    esperada_3 = _sha_json(
        {
            "anterior": esperada_2,
            "tipo": "envio",
            "proyecto_id": proyecto_id,
            "version": "VIV-002",
            "huella_version": sello_2,
            "resultado": None,
            "notas": "",
            "usuario": ANA,
            "fecha_hora": "2026-10-20T10:30:00",
            "armo": True,
            "cierre_de": None,
        }
    )
    esperada_4 = _sha_json(
        {
            "anterior": esperada_3,
            "tipo": "dictamen",
            "proyecto_id": proyecto_id,
            "version": "VIV-002",
            "huella_version": sello_2,
            "resultado": "devuelta",
            "notas": "Falta el acero.",
            "usuario": RITA,
            "fecha_hora": "2026-10-21T11:15:20",
            "armo": False,
            "cierre_de": segundo.id,
        }
    )
    filas = _filas(sesion)
    assert [(f.anterior, f.huella) for f in filas] == [
        (CERO, esperada_1),
        (esperada_1, esperada_2),
        (esperada_2, esperada_3),
        (esperada_3, esperada_4),
    ]
    assert [f.huella_version for f in filas] == [sello_1, sello_1, sello_2, sello_2]
    assert filas[-1].id == dictamen
    eventos = aprobaciones.historial(sesion, OBRA)
    assert [(e.id, e.tipo, e.version, e.huella) for e in eventos] == [
        (f.id, f.tipo, f.version, f.huella) for f in filas
    ]


def test_el_rastro_integro_lo_dice(sesion: Session) -> None:
    envio = _enviar(sesion, "VIV-001")
    _dictaminar(sesion, envio.id, "devuelta", "Falta el acero.")
    assert aprobaciones.verificar_rastro(sesion, OBRA) == RastroVerificado(True, INTEGRO)


def test_alterar_las_notas_de_un_evento_rompe_el_rastro(sesion: Session) -> None:
    envio = _enviar(sesion, "VIV-001")
    dictamen = _dictaminar(sesion, envio.id, "devuelta", "Falta el acero.")
    _enviar(sesion, "VIV-002", ahora=MIERCOLES)
    sesion.execute(
        text("UPDATE mp_aprobacion_evento SET notas = 'Todo bien.' WHERE id = :id"),
        {"id": dictamen},
    )
    sesion.commit()
    assert aprobaciones.verificar_rastro(sesion, OBRA) == RastroVerificado(False, _rota(dictamen))


def test_borrar_un_evento_rompe_el_rastro_en_el_siguiente(sesion: Session) -> None:
    envio = _enviar(sesion, "VIV-001")
    dictamen = _dictaminar(sesion, envio.id, "devuelta", "Falta el acero.")
    otro = _enviar(sesion, "VIV-002", ahora=MIERCOLES)
    sesion.execute(text("DELETE FROM mp_aprobacion_evento WHERE id = :id"), {"id": dictamen})
    sesion.commit()
    assert aprobaciones.verificar_rastro(sesion, OBRA) == RastroVerificado(False, _rota(otro.id))


def test_cambiar_el_sello_de_la_version_rompe_el_rastro(sesion: Session) -> None:
    """`huella_version` se compara con el eslabón actual: si el sello de la versión cambió
    después del envío, el rastro lo dice en el primer evento que la nombra."""
    _enviar(sesion, "VIV-001")
    segundo = _enviar(sesion, "VIV-002", ahora=MARTES)
    sesion.execute(
        text(
            "UPDATE eslabon_version SET huella_eslabon = :otra WHERE presupuesto_id = "
            "(SELECT id FROM presupuesto WHERE codigo = 'VIV-002')"
        ),
        {"otra": "a" * 64},
    )
    sesion.commit()
    assert aprobaciones.verificar_rastro(sesion, OBRA) == RastroVerificado(False, _rota(segundo.id))


# --- errores de entrada -------------------------------------------------------------------------


def test_obra_version_o_envio_que_no_existen(sesion: Session) -> None:
    with pytest.raises(AprobacionInvalida) as error:
        aprobaciones.enviar(sesion, "Obra fantasma", "VIV-001", nota="", usuario=ANA, ahora=LUNES)
    assert _mensaje(error) == "No se encontró la obra «Obra fantasma»."
    with pytest.raises(AprobacionInvalida) as error:
        _enviar(sesion, "VIV-009")
    assert _mensaje(error) == "No se encontró la versión VIV-009 de esta obra."
    with pytest.raises(AprobacionInvalida) as error:
        _enviar(sesion, "GAL-001")  # existe, pero es de otra obra
    assert _mensaje(error) == "No se encontró la versión GAL-001 de esta obra."
    with pytest.raises(AprobacionInvalida) as error:
        _dictaminar(sesion, 999, "aprobada")
    assert _mensaje(error) == "No se encontró ese envío."
    with pytest.raises(AprobacionInvalida) as error:
        aprobaciones.estados(sesion, "Obra fantasma")
    assert _mensaje(error) == "No se encontró la obra «Obra fantasma»."
    assert _cuenta(sesion) == 0


def test_dictaminar_un_evento_que_no_es_envio(sesion: Session) -> None:
    primero = _enviar(sesion, "VIV-001")
    _enviar(sesion, "VIV-002", ahora=MARTES)
    (retiro,) = [f.id for f in _filas(sesion) if f.tipo == "retiro"]
    assert retiro != primero.id
    with pytest.raises(AprobacionInvalida) as error:
        _dictaminar(sesion, retiro, "aprobada")
    assert _mensaje(error) == "No se encontró ese envío."


def test_notas_demasiado_largas(sesion: Session) -> None:
    with pytest.raises(AprobacionInvalida) as error:
        _enviar(sesion, "VIV-001", nota="x" * 2001)
    assert _mensaje(error) == "Las notas no pueden pasar de 2000 caracteres."
    envio = _enviar(sesion, "VIV-001", nota="x" * 2000)
    with pytest.raises(AprobacionInvalida) as error:
        _dictaminar(sesion, envio.id, "devuelta", "y" * 2001)
    assert _mensaje(error) == "Las notas no pueden pasar de 2000 caracteres."
    assert _cuenta(sesion) == 1


def test_una_version_sin_sello_no_se_envia(sesion: Session) -> None:
    sesion.execute(
        text(
            "DELETE FROM eslabon_version WHERE presupuesto_id = "
            "(SELECT id FROM presupuesto WHERE codigo = 'VIV-002')"
        )
    )
    sesion.commit()
    with pytest.raises(AprobacionInvalida) as error:
        _enviar(sesion, "VIV-002")
    assert _mensaje(error) == "La versión VIV-002 no está sellada."
    assert _cuenta(sesion) == 0
