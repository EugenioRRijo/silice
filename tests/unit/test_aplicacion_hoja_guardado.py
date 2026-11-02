"""3b-B3C (T10, 3d-1): `guardar_version` y `crear_primera_version`.

Corre las funciones que escriben la version de la ruta S1 (con la sesion envuelta en
`con_anexos_de_cadena`, como la ruta) sobre una COPIA de la base del caso y fija lo que dejan: el
codigo de la version, los mensajes de error (igualdad exacta de cadena), las filas escritas
(cuentas a mano por tabla) y el estado de la cadena. Casos: OF-001 (con espacio), TI-001 (sin
espacio) y un proyecto nuevo sin versiones. Ya no compara contra `ui.hoja` (retiro de Streamlit,
F6).

Oraculos a mano (ninguno sale del codigo): total de OF-001 2 703,86 (memoria `of001.md`); con
administracion 0,20 y utilidad 0,10, CV 2 137,44 x 1,20 x 1,10 = 2 821,4208; la primera version de
un proyecto nuevo con el espacio y los parametros de OF-001 vuelve a dar 2 703,86; el
RegistroCambio de la edicion es (parametro, administracion, valor, 0.15, 0.20) y el de la
creacion (version, 001, creacion, "", 001). Las filas escritas: una version nueva de OF-001 copia
sus 30 partidas, 6 ambientes, 6 fuentes, 2 circuitos y 21 puntos de la memoria (`of001.md` §1) y
sella un eslabon de la cadena. Un cambio legitimo del comportamiento exige cambiar esta prueba
con el aval de Eugenio.
"""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from aplicacion import hoja
from aplicacion.entrega import con_anexos_de_cadena, estado_de_la_cadena
from aplicacion.errores import HojaInvalida
from core import models
from core.budget import crear_proyecto
from core.catalog import Catalogo, abrir_sesion, crear_motor
from tests.fixtures import caso_of001, caso_ti001
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    NOMBRE_TI001,
    plantilla_of001,
    plantilla_ti001,
)

D = Decimal
AHORA = datetime(2026, 10, 20, 9, 30, 0)
FUENTE = "acta de revision 7: el contrato fija la administracion en 20 %"
RESPONSABLE = "Ana <ana>"
NUEVO = "Proyecto nuevo: guardado"
TOLERANCIA = D("0.01")
TOTAL_V002 = D("2821.4208")  # 2 137,44 x 1,20 x 1,10
TOTAL_MEMORIA = D("2703.86")
#: Columnas que dependen del reloj de la corrida y no del contenido: la hora del sello y la huella
#: del eslabon, que la incluye (`cadena.huella_del_eslabon`). No entran en el volcado; que el
#: sello sea valido lo dice `estado_de_la_cadena`.
HORA_DEL_RELOJ = {("eslabon_version", "fecha_hora"), ("eslabon_version", "huella_eslabon")}
#: Lo que escribe una version nueva de OF-001 (memoria `of001.md`): tabla -> filas por version.
POR_VERSION_OF001 = {
    "presupuesto": 1,
    "eslabon_version": 1,
    "item_computo": 30,
    "partida_presupuestada": 30,
    "composicion_version": 30,
    "esp_origenes": 1,
    "esp_ambientes": 6,
    "esp_fuentes": 6,
    "esp_circuitos": 2,
    "esp_puntos": 21,
}


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> tuple[Path, Path]:
    carpeta = tmp_path_factory.mktemp("hoja_guardado")
    return plantilla_of001(carpeta / "of001.db"), plantilla_ti001(carpeta / "ti001.db")


class _Caso:
    """Una copia de la base con su sesion envuelta (la cadena cubre los anexos de espacio)."""

    def __init__(self, plantilla: Path, destino: Path, nuevo: bool = False) -> None:
        self.ruta = destino / "caso.db"
        shutil.copyfile(plantilla, self.ruta)
        self.motor = crear_motor(f"sqlite:///{self.ruta.as_posix()}")
        self.sesion = abrir_sesion(self.motor)
        con_anexos_de_cadena(self.sesion)
        self.catalogo = Catalogo(self.sesion)
        if nuevo:
            crear_proyecto(self.sesion, NUEVO)
            self.sesion.commit()

    def abrir(self, nombre: str, codigo: str):
        return hoja.abrir_version(
            self.sesion, self.catalogo, nombre, codigo, fecha_evaluacion=caso_of001.FECHA
        )

    def cerrar(self) -> None:
        self.sesion.close()
        self.motor.dispose()

    def volcado(self) -> dict[str, list[tuple]]:
        """Todas las filas de todas las tablas, sin las columnas que dependen del reloj."""
        with closing(sqlite3.connect(f"file:{self.ruta.as_posix()}?mode=ro", uri=True)) as bd:
            tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            volcado = {}
            for tabla in tablas:
                columnas = [c[1] for c in bd.execute(f'PRAGMA table_info("{tabla}")')]
                quitar = {n for n, c in enumerate(columnas) if (tabla, c) in HORA_DEL_RELOJ}
                filas = [
                    tuple(v for n, v in enumerate(fila) if n not in quitar)
                    for fila in bd.execute(f'SELECT * FROM "{tabla}"')
                ]
                volcado[tabla] = sorted(filas, key=repr)
            return volcado

    def cuentas(self) -> dict[str, int]:
        """Filas por tabla (para dar por escrito lo que una operacion agrego)."""
        return {tabla: len(filas) for tabla, filas in self.volcado().items()}

    def registros(self, nombre: str, codigo: str) -> list[tuple]:
        r = models.RegistroCambio
        return [
            tuple(f)
            for f in self.sesion.execute(
                select(
                    r.objeto,
                    r.clave,
                    r.campo,
                    r.valor_anterior,
                    r.valor_nuevo,
                    r.fuente,
                    r.responsable,
                    r.fecha_hora,
                )
                .join(models.Presupuesto, models.Presupuesto.id == r.version_resultante_id)
                .join(models.Proyecto, models.Proyecto.id == models.Presupuesto.proyecto_id)
                .where(models.Proyecto.nombre == nombre, models.Presupuesto.codigo == codigo)
                .order_by(r.id)
            )
        ]

    def cadena(self, nombre: str):
        return estado_de_la_cadena(self.sesion, nombre)


@pytest.fixture
def abrir_caso(tmp_path):
    abiertos: list[_Caso] = []

    def abrir(plantilla: Path, nuevo: bool = False) -> _Caso:
        caso = _Caso(plantilla, tmp_path, nuevo)
        abiertos.append(caso)
        return caso

    yield abrir
    for caso in abiertos:
        caso.cerrar()


def _con_administracion(borrador, valor: str):
    return replace(borrador, parametros=replace(borrador.parametros, administracion=D(valor)))


def _en_blanco(**cambios):
    return replace(
        hoja.Borrador(
            fecha=caso_of001.FECHA,
            moneda=caso_of001.MONEDA,
            espacio=espacio_of001(),
            parametros=caso_ti001.PARAMETROS,
        ),
        **cambios,
    )


def _guardar(caso: _Caso, abierta, borrador, **opciones):
    opciones.setdefault("fuente", FUENTE)
    opciones.setdefault("responsable", RESPONSABLE)
    opciones.setdefault("ahora", AHORA)
    return hoja.guardar_version(caso.sesion, caso.catalogo, abierta, borrador, **opciones)


def _primera(caso: _Caso, borrador, nombre: str = NUEVO, **opciones):
    opciones.setdefault("fuente", FUENTE)
    opciones.setdefault("responsable", RESPONSABLE)
    opciones.setdefault("ahora", AHORA)
    return hoja.crear_primera_version(caso.sesion, caso.catalogo, nombre, borrador, **opciones)


def _tupla(guardada) -> tuple:
    """Los tres datos de una `VersionGuardada`."""
    return (guardada.codigo, guardada.cambios, guardada.total)


def _error(funcion, *args, **kwargs) -> str:
    with pytest.raises(HojaInvalida) as caido:
        funcion(*args, **kwargs)
    return str(caido.value)


# --- guardar_version sobre OF-001 ------------------------------------------------------------


def test_guardar_la_administracion_en_20_da_la_002_con_el_total_de_la_memoria(
    _plantillas, abrir_caso
) -> None:
    caso = abrir_caso(_plantillas[0])
    abierta = caso.abrir(NOMBRE_OF001, "001")
    caso.sesion.commit()
    antes = caso.cuentas()
    guardada = _guardar(caso, abierta, _con_administracion(abierta.borrador, "0.20"))
    assert _tupla(guardada)[:2] == ("002", 1)
    assert abs(guardada.total - TOTAL_V002) <= TOLERANCIA  # 2 821,42
    assert caso.registros(NOMBRE_OF001, "002") == [
        ("parametro", "administracion", "valor", "0.15", "0.20", FUENTE, RESPONSABLE, AHORA)
    ]
    estado = caso.cadena(NOMBRE_OF001)
    assert estado.integra, estado.mensaje
    caso.sesion.commit()
    despues = caso.cuentas()
    # una version nueva copia las 30 partidas y el espacio de la memoria; un registro; un eslabon
    for tabla, por_version in POR_VERSION_OF001.items():
        assert despues[tabla] - antes[tabla] == por_version, tabla
    assert (despues["registro_cambio"] - antes["registro_cambio"]) == 1
    assert (despues["version_origen"] - antes["version_origen"]) == 1


def test_guardar_sin_cambios_no_hace_nada_y_devuelve_none(_plantillas, abrir_caso) -> None:
    caso = abrir_caso(_plantillas[0])
    abierta = caso.abrir(NOMBRE_OF001, "001")
    caso.sesion.commit()
    antes = caso.volcado()
    assert _guardar(caso, abierta, abierta.borrador) is None
    assert caso.volcado() == antes


def test_los_mensajes_de_error_al_guardar_son_los_escritos_a_mano(_plantillas, abrir_caso) -> None:
    caso = abrir_caso(_plantillas[0])
    abierta = caso.abrir(NOMBRE_OF001, "001")
    caso.sesion.commit()
    editado = _con_administracion(abierta.borrador, "0.20")
    antes = caso.volcado()
    solo_lectura = replace(abierta, solo_lectura=True)
    mensajes = [
        _error(_guardar, caso, abierta, editado, fuente=""),
        _error(_guardar, caso, abierta, editado, fuente="   "),
        _error(_guardar, caso, abierta, editado, responsable="  "),
        _error(_guardar, caso, solo_lectura, editado),
    ]
    assert caso.volcado() == antes  # nada se escribio
    assert mensajes == [
        "Escriba la fuente del cambio: por que se cambia y con que respaldo.",
        "Escriba la fuente del cambio: por que se cambia y con que respaldo.",
        "Escriba el responsable del cambio: quien lo hace.",
        "Esta version esta en solo lectura: alguna de sus partidas ya no tiene composicion "
        "vigente en el catalogo, asi que recalcularla cambiaria sus precios.",
    ]


def test_el_motivo_para_no_guardar_dice_lo_primero_que_falta() -> None:
    base = hoja.Borrador(fecha=caso_of001.FECHA)
    editado = replace(base, parametros=replace(base.parametros, utilidad=D("0.5")))
    assert hoja.motivo_para_no_guardar(base, base, "x", "y") == (
        "No hay cambios para guardar: edite alguna celda primero."
    )
    assert hoja.motivo_para_no_guardar(base, editado, "", "y") == (
        "Escriba la fuente del cambio: por que se cambia y con que respaldo."
    )
    assert hoja.motivo_para_no_guardar(base, editado, "x", "") == (
        "Escriba el responsable del cambio: quien lo hace."
    )
    assert hoja.motivo_para_no_guardar(base, editado, "x", "y") is None


def test_si_la_copia_del_espacio_falla_se_deshace_todo(
    _plantillas, abrir_caso, monkeypatch
) -> None:
    caso = abrir_caso(_plantillas[0])
    abierta = caso.abrir(NOMBRE_OF001, "001")
    caso.sesion.commit()
    antes = caso.volcado()

    def roto(*_args, **_kwargs):
        raise RuntimeError("disco lleno")

    with monkeypatch.context() as parche:
        parche.setattr(hoja, "guardar_espacio", roto)
        with pytest.raises(RuntimeError, match="disco lleno"):
            _guardar(caso, abierta, _con_administracion(abierta.borrador, "0.20"))
    assert caso.volcado() == antes
    assert caso.cadena(NOMBRE_OF001).integra


# --- guardar_version sobre TI-001 (sin espacio) ----------------------------------------------


def test_guardar_sobre_ti001_sin_espacio_escribe_la_version_y_ninguna_tabla_de_espacio(
    _plantillas, abrir_caso
) -> None:
    caso = abrir_caso(_plantillas[1])
    abierta = caso.abrir(NOMBRE_TI001, caso_ti001.CODIGO)
    caso.sesion.commit()
    antes = caso.cuentas()
    editado = replace(
        abierta.borrador, parametros=replace(abierta.borrador.parametros, utilidad=D("0.12"))
    )
    guardada = _guardar(caso, abierta, editado)
    assert guardada.codigo == "TI-002" and guardada.cambios == 1  # el prefijo de la 001
    assert guardada.total != abierta.guardada.presupuesto.total  # la utilidad sube el total
    assert caso.registros(NOMBRE_TI001, "TI-002")[0][:5] == (
        "parametro",
        "utilidad",
        "valor",
        "0.10",
        "0.12",
    )
    assert caso.cadena(NOMBRE_TI001).integra
    caso.sesion.commit()
    despues = caso.cuentas()
    assert "esp_ambientes" not in despues  # sin espacio no se crean las tablas esp_*
    assert despues["presupuesto"] - antes["presupuesto"] == 1
    assert despues["eslabon_version"] - antes["eslabon_version"] == 1
    assert despues["item_computo"] - antes["item_computo"] == 27  # las 27 partidas de TI-001


# --- crear_primera_version ---------------------------------------------------------------------


def test_la_primera_version_da_la_001_con_el_total_de_la_memoria(_plantillas, abrir_caso) -> None:
    caso = abrir_caso(_plantillas[0], nuevo=True)
    antes = caso.cuentas()
    guardada = _primera(caso, _en_blanco())
    assert guardada.codigo == "001" and guardada.cambios == 1
    assert abs(guardada.total - TOTAL_MEMORIA) <= TOLERANCIA  # 2 703,86
    assert caso.registros(NUEVO, "001") == [
        ("version", "001", "creacion", "", "001", FUENTE, RESPONSABLE, AHORA)
    ]
    estado = caso.cadena(NUEVO)
    assert estado.integra, estado.mensaje
    caso.sesion.commit()
    despues = caso.cuentas()
    for tabla, por_version in POR_VERSION_OF001.items():
        assert despues[tabla] - antes[tabla] == por_version, tabla  # y la 001 de OF-001 sigue


def test_los_mensajes_de_error_de_la_primera_version_son_los_escritos_a_mano(
    _plantillas, abrir_caso
) -> None:
    caso = abrir_caso(_plantillas[0], nuevo=True)
    antes = caso.volcado()
    vacio = hoja.Borrador(fecha=caso_of001.FECHA, moneda=caso_of001.MONEDA)
    mensajes = [
        _error(_primera, caso, _en_blanco(), fuente=""),
        _error(_primera, caso, _en_blanco(), responsable=" "),
        _error(_primera, caso, vacio),
        _error(_primera, caso, _en_blanco(), nombre="Proyecto que no existe"),
        _error(_primera, caso, _en_blanco(), nombre=NOMBRE_OF001),
        _error(_primera, caso, _en_blanco(fecha=date(2000, 1, 1))),
    ]
    assert caso.volcado() == antes
    assert mensajes[0] == (
        "Escriba la fuente de la medida: de donde salen los datos (un plano, un acta)."
    )
    assert mensajes[1] == "Escriba el responsable: quien crea esta primera version."
    assert mensajes[2].startswith("La hoja esta vacia")
    assert mensajes[3] == (
        "El proyecto 'Proyecto que no existe' no existe: creelo desde la barra superior "
        "(Proyectos)."
    )
    assert mensajes[4] == (
        f"El proyecto {NOMBRE_OF001!r} ya tiene versiones: abra una y use Guardar version."
    )
    assert mensajes[5].startswith("No hay una lista de precios vigente al 01/01/2000")


def test_el_motivo_para_no_crear_la_primera_dice_lo_primero_que_falta() -> None:
    vacio = hoja.Borrador(fecha=caso_of001.FECHA)
    lleno = _en_blanco()
    assert hoja.motivo_para_no_crear_primera(vacio, "x", "y") == (
        "La hoja esta vacia: describa o importe el espacio antes de guardar la primera version."
    )
    assert hoja.motivo_para_no_crear_primera(lleno, "", "y") == (
        "Escriba la fuente de la medida: de donde salen los datos (un plano, un acta)."
    )
    assert hoja.motivo_para_no_crear_primera(lleno, "x", "") == (
        "Escriba el responsable: quien crea esta primera version."
    )
    assert hoja.motivo_para_no_crear_primera(lleno, "x", "y") is None
