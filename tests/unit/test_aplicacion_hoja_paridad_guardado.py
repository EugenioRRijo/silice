"""3b-B3C (T10, 3d-1): `guardar_version` y `crear_primera_version` contra `ui.hoja` VIVO.

`aplicacion/hoja.py` es una copia de `ui/hoja.py` (Plan C: la clasica esta en el congelado del
experimento y no se toca). Esta prueba (que SI puede importar `ui`) corre en las dos las funciones
que escriben la version de la ruta S1 (con la sesion envuelta en `con_anexos_de_cadena`, como la
pagina clasica y como la ruta) y compara lo que dejan en una COPIA de la base del caso: el codigo
de la version, los mensajes de error (igualdad exacta de cadena), las filas escritas y el estado de
la cadena. Casos: OF-001 (con espacio), TI-001 (sin espacio) y un proyecto nuevo sin versiones.

Oraculos a mano (ninguno sale de la copia): total de OF-001 2 703,86 (memoria `of001.md`); con
administracion 0,20 y utilidad 0,10, CV 2 137,44 x 1,20 x 1,10 = 2 821,4208; la primera version de
un proyecto nuevo con el espacio y los parametros de OF-001 vuelve a dar 2 703,86; el
RegistroCambio de la edicion es (parametro, administracion, valor, 0.15, 0.20) y el de la
creacion (version, 001, creacion, "", 001).

Si la copia y la clasica divergen, la unica que se corrige es la copia: `ui/hoja.py` esta
congelado. Un cambio legitimo del comportamiento exige cambiar esta prueba con el aval de Eugenio.
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

from aplicacion import hoja as copia
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
from ui import hoja as clasica

D = Decimal
MODULOS = [pytest.param(clasica, id="clasica"), pytest.param(copia, id="copia")]
AHORA = datetime(2026, 10, 20, 9, 30, 0)
FUENTE = "acta de revision 7: el contrato fija la administracion en 20 %"
RESPONSABLE = "Ana <ana>"
NUEVO = "Proyecto nuevo: paridad"
TOLERANCIA = D("0.01")
TOTAL_V002 = D("2821.4208")  # 2 137,44 x 1,20 x 1,10
TOTAL_MEMORIA = D("2703.86")
#: Columnas que dependen del reloj de la corrida y no del contenido: la hora del sello y la huella
#: del eslabon, que la incluye (`cadena.huella_del_eslabon`). No entran en la comparacion; que el
#: sello sea valido lo dice `estado_de_la_cadena`, que SI se compara.
HORA_DEL_RELOJ = {("eslabon_version", "fecha_hora"), ("eslabon_version", "huella_eslabon")}


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> tuple[Path, Path]:
    carpeta = tmp_path_factory.mktemp("paridad_guardado")
    return plantilla_of001(carpeta / "of001.db"), plantilla_ti001(carpeta / "ti001.db")


class _Caso:
    """Una copia de la base con su sesion envuelta (la cadena cubre los anexos de espacio)."""

    def __init__(self, plantilla: Path, destino: Path, modulo, nuevo: bool = False) -> None:
        self.ruta = destino / f"{modulo.__name__}.db"
        shutil.copyfile(plantilla, self.ruta)
        self.motor = crear_motor(f"sqlite:///{self.ruta.as_posix()}")
        self.sesion = abrir_sesion(self.motor)
        con_anexos_de_cadena(self.sesion)
        self.catalogo = Catalogo(self.sesion)
        self.modulo = modulo
        if nuevo:
            crear_proyecto(self.sesion, NUEVO)
            self.sesion.commit()

    def abrir(self, nombre: str, codigo: str):
        return self.modulo.abrir_version(
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

    def abrir(plantilla: Path, modulo, nuevo: bool = False) -> _Caso:
        caso = _Caso(plantilla, tmp_path, modulo, nuevo)
        abiertos.append(caso)
        return caso

    yield abrir
    for caso in abiertos:
        caso.cerrar()


def _con_administracion(borrador, valor: str):
    return replace(borrador, parametros=replace(borrador.parametros, administracion=D(valor)))


def _en_blanco(modulo, **cambios):
    return replace(
        modulo.Borrador(
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
    return caso.modulo.guardar_version(caso.sesion, caso.catalogo, abierta, borrador, **opciones)


def _primera(caso: _Caso, borrador, nombre: str = NUEVO, **opciones):
    opciones.setdefault("fuente", FUENTE)
    opciones.setdefault("responsable", RESPONSABLE)
    opciones.setdefault("ahora", AHORA)
    return caso.modulo.crear_primera_version(
        caso.sesion, caso.catalogo, nombre, borrador, **opciones
    )


def _tupla(guardada) -> tuple:
    """`VersionGuardada` de cada modulo es una clase distinta: se comparan sus tres datos."""
    return (guardada.codigo, guardada.cambios, guardada.total)


def _error(funcion, *args, **kwargs) -> str:
    with pytest.raises(HojaInvalida) as caido:
        funcion(*args, **kwargs)
    return str(caido.value)


# --- guardar_version sobre OF-001 ------------------------------------------------------------


def test_guardar_la_administracion_en_20_da_la_002_con_el_total_de_la_memoria(
    _plantillas, abrir_caso
) -> None:
    resultados = {}
    for modulo in (clasica, copia):
        caso = abrir_caso(_plantillas[0], modulo)
        abierta = caso.abrir(NOMBRE_OF001, "001")
        guardada = _guardar(caso, abierta, _con_administracion(abierta.borrador, "0.20"))
        resultados[modulo] = (guardada, caso)
        assert guardada.codigo == "002" and guardada.cambios == 1
        assert abs(guardada.total - TOTAL_V002) <= TOLERANCIA  # 2 821,42
        assert caso.registros(NOMBRE_OF001, "002") == [
            ("parametro", "administracion", "valor", "0.15", "0.20", FUENTE, RESPONSABLE, AHORA)
        ]
        assert caso.cadena(NOMBRE_OF001).integra, caso.cadena(NOMBRE_OF001).mensaje
    (g_clasica, c_clasica), (g_copia, c_copia) = resultados[clasica], resultados[copia]
    assert _tupla(g_copia) == _tupla(g_clasica)
    assert c_copia.cadena(NOMBRE_OF001) == c_clasica.cadena(NOMBRE_OF001)
    c_clasica.sesion.close()
    c_copia.sesion.close()
    assert c_copia.volcado() == c_clasica.volcado()  # mismas filas escritas, tabla por tabla


@pytest.mark.parametrize("modulo", MODULOS)
def test_guardar_sin_cambios_no_hace_nada_y_devuelve_none(modulo, _plantillas, abrir_caso) -> None:
    caso = abrir_caso(_plantillas[0], modulo)
    abierta = caso.abrir(NOMBRE_OF001, "001")
    caso.sesion.commit()
    antes = caso.volcado()
    assert _guardar(caso, abierta, abierta.borrador) is None
    assert caso.volcado() == antes


def test_los_mensajes_de_error_al_guardar_son_los_mismos(_plantillas, abrir_caso) -> None:
    mensajes: dict[str, list[str]] = {}
    for modulo in (clasica, copia):
        caso = abrir_caso(_plantillas[0], modulo)
        abierta = caso.abrir(NOMBRE_OF001, "001")
        caso.sesion.commit()
        editado = _con_administracion(abierta.borrador, "0.20")
        antes = caso.volcado()
        solo_lectura = replace(abierta, solo_lectura=True)
        mensajes[modulo.__name__] = [
            _error(_guardar, caso, abierta, editado, fuente=""),
            _error(_guardar, caso, abierta, editado, fuente="   "),
            _error(_guardar, caso, abierta, editado, responsable="  "),
            _error(_guardar, caso, solo_lectura, editado),
        ]
        assert caso.volcado() == antes  # nada se escribio
    clasicos, copiados = mensajes["ui.hoja"], mensajes["aplicacion.hoja"]
    assert copiados == clasicos
    assert clasicos == [
        "Escriba la fuente del cambio: por que se cambia y con que respaldo.",
        "Escriba la fuente del cambio: por que se cambia y con que respaldo.",
        "Escriba el responsable del cambio: quien lo hace.",
        "Esta version esta en solo lectura: alguna de sus partidas ya no tiene composicion "
        "vigente en el catalogo, asi que recalcularla cambiaria sus precios.",
    ]


@pytest.mark.parametrize("modulo", MODULOS)
def test_el_motivo_para_no_guardar_dice_lo_primero_que_falta(modulo) -> None:
    base = modulo.Borrador(fecha=caso_of001.FECHA)
    editado = replace(base, parametros=replace(base.parametros, utilidad=D("0.5")))
    assert modulo.motivo_para_no_guardar(base, base, "x", "y") == (
        "No hay cambios para guardar: edite alguna celda primero."
    )
    assert modulo.motivo_para_no_guardar(base, editado, "", "y") == (
        "Escriba la fuente del cambio: por que se cambia y con que respaldo."
    )
    assert modulo.motivo_para_no_guardar(base, editado, "x", "") == (
        "Escriba el responsable del cambio: quien lo hace."
    )
    assert modulo.motivo_para_no_guardar(base, editado, "x", "y") is None


def test_si_la_copia_del_espacio_falla_las_dos_deshacen_todo(
    _plantillas, abrir_caso, monkeypatch
) -> None:
    for modulo in (clasica, copia):
        caso = abrir_caso(_plantillas[0], modulo)
        abierta = caso.abrir(NOMBRE_OF001, "001")
        caso.sesion.commit()
        antes = caso.volcado()

        def roto(*_args, **_kwargs):
            raise RuntimeError("disco lleno")

        with monkeypatch.context() as parche:
            parche.setattr(modulo, "guardar_espacio", roto)
            with pytest.raises(RuntimeError, match="disco lleno"):
                _guardar(caso, abierta, _con_administracion(abierta.borrador, "0.20"))
        assert caso.volcado() == antes
        assert caso.cadena(NOMBRE_OF001).integra


# --- guardar_version sobre TI-001 (sin espacio) ----------------------------------------------


def test_guardar_sobre_ti001_sin_espacio_escribe_lo_mismo_en_las_dos(
    _plantillas, abrir_caso
) -> None:
    casos = {}
    for modulo in (clasica, copia):
        caso = abrir_caso(_plantillas[1], modulo)
        abierta = caso.abrir(NOMBRE_TI001, caso_ti001.CODIGO)
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
        assert "esp_ambientes" not in caso.volcado()  # sin espacio no se crean las tablas esp_*
        casos[modulo] = (guardada, caso)
    (g_clasica, c_clasica), (g_copia, c_copia) = casos[clasica], casos[copia]
    assert _tupla(g_copia) == _tupla(g_clasica)
    c_clasica.sesion.close()
    c_copia.sesion.close()
    assert c_copia.volcado() == c_clasica.volcado()


# --- crear_primera_version ---------------------------------------------------------------------


def test_la_primera_version_da_la_001_con_el_total_de_la_memoria_en_las_dos(
    _plantillas, abrir_caso
) -> None:
    casos = {}
    for modulo in (clasica, copia):
        caso = abrir_caso(_plantillas[0], modulo, nuevo=True)
        guardada = _primera(caso, _en_blanco(modulo))
        assert guardada.codigo == "001" and guardada.cambios == 1
        assert abs(guardada.total - TOTAL_MEMORIA) <= TOLERANCIA  # 2 703,86
        assert caso.registros(NUEVO, "001") == [
            ("version", "001", "creacion", "", "001", FUENTE, RESPONSABLE, AHORA)
        ]
        assert caso.cadena(NUEVO).integra, caso.cadena(NUEVO).mensaje
        casos[modulo] = (guardada, caso)
    (g_clasica, c_clasica), (g_copia, c_copia) = casos[clasica], casos[copia]
    assert _tupla(g_copia) == _tupla(g_clasica)
    assert c_copia.cadena(NUEVO) == c_clasica.cadena(NUEVO)
    c_clasica.sesion.close()
    c_copia.sesion.close()
    assert c_copia.volcado() == c_clasica.volcado()


def test_los_mensajes_de_error_de_la_primera_version_son_los_mismos(
    _plantillas, abrir_caso
) -> None:
    mensajes: dict[str, list[str]] = {}
    for modulo in (clasica, copia):
        caso = abrir_caso(_plantillas[0], modulo, nuevo=True)
        antes = caso.volcado()
        vacio = modulo.Borrador(fecha=caso_of001.FECHA, moneda=caso_of001.MONEDA)
        mensajes[modulo.__name__] = [
            _error(_primera, caso, _en_blanco(modulo), fuente=""),
            _error(_primera, caso, _en_blanco(modulo), responsable=" "),
            _error(_primera, caso, vacio),
            _error(_primera, caso, _en_blanco(modulo), nombre="Proyecto que no existe"),
            _error(_primera, caso, _en_blanco(modulo), nombre=NOMBRE_OF001),
            _error(_primera, caso, _en_blanco(modulo, fecha=date(2000, 1, 1))),
        ]
        assert caso.volcado() == antes
    clasicos, copiados = mensajes["ui.hoja"], mensajes["aplicacion.hoja"]
    assert copiados == clasicos
    assert clasicos[0] == (
        "Escriba la fuente de la medida: de donde salen los datos (un plano, un acta)."
    )
    assert clasicos[1] == "Escriba el responsable: quien crea esta primera version."
    assert clasicos[2].startswith("La hoja esta vacia")
    assert clasicos[3] == (
        "El proyecto 'Proyecto que no existe' no existe: creelo desde la barra superior "
        "(Proyectos)."
    )
    assert clasicos[4] == (
        f"El proyecto {NOMBRE_OF001!r} ya tiene versiones: abra una y use Guardar version."
    )
    assert clasicos[5].startswith("No hay una lista de precios vigente al 01/01/2000")


@pytest.mark.parametrize("modulo", MODULOS)
def test_el_motivo_para_no_crear_la_primera_dice_lo_primero_que_falta(modulo) -> None:
    vacio = modulo.Borrador(fecha=caso_of001.FECHA)
    lleno = _en_blanco(modulo)
    assert modulo.motivo_para_no_crear_primera(vacio, "x", "y") == (
        "La hoja esta vacia: describa o importe el espacio antes de guardar la primera version."
    )
    assert modulo.motivo_para_no_crear_primera(lleno, "", "y") == (
        "Escriba la fuente de la medida: de donde salen los datos (un plano, un acta)."
    )
    assert modulo.motivo_para_no_crear_primera(lleno, "x", "") == (
        "Escriba el responsable: quien crea esta primera version."
    )
    assert modulo.motivo_para_no_crear_primera(lleno, "x", "y") is None
