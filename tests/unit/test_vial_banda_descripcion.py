"""Prueba de punta a punta del 2026-11-13, defecto D3: VR4 lee la banda de la descripción del APU.

Antes VR4 solo leía la directiva `_tramo_km`, que Componer no deja declarar, y decía «la descripción
no dice la banda» aunque la dijera. Ahora, sin directiva, lee la descripción del APU de la partida
con el patrón del perfil del libro con un APU por hoja y la misma función que su AH9
(`aplicacion.banda_de_distancia.leer_banda`): una sola lectura. La directiva, si está, sigue
mandando. El patrón del perfil del repositorio lee «mayor de», «mayores de» y «más de». Decisión
simulada en `docs/bitacora/2026-11-13-e2e-vial.md` (D3). Datos FICTICIOS.

Oráculos a mano (los de `test_vial_banda_f5.py`): tramo B1 de 0 a 1 km, ancho 5 m, carpeta de
0,01 m a 2,4 t/m³: 1.000 × 5 × 0,01 × 2,4 = 120 t. «Mayores de 8 km y hasta 10 km»: 9 km cae dentro,
12 km fuera.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, select

from adapters.hoja_empresa.perfil_apu_por_hoja import cargar_perfil_apu_por_hoja
from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.modelo import Capa, Tramo
from adapters.vial.reglas import ESPEC_BANDA_KM, auditar_vial
from aplicacion import vial
from core import models
from core.catalog import abrir_sesion, crear_motor
from core.contracts import Dominio, ItemComputo, OrigenTipo
from core.contracts.apu import ComposicionAPU, ResultadoAPU
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Severidad
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import sembrar_vivienda

D = Decimal
CAPA = "tramo:B1:capa:1"
BANDA = PARTIDAS_VIALES["transporte_mezcla_banda"][0]
EN_PALABRAS = "Transporte de mezcla asfáltica a distancias mayores de 8 km y hasta 10 km"
CON_MILES = r"mayor de (?P<minimo>[0-9.,]+) km y hasta (?P<maximo>[0-9.,]+) km"


def leer_banda(patron: str, texto: str):
    # perezosa: el módulo común es lo que se prueba (en rojo no existía)
    from aplicacion.banda_de_distancia import leer_banda as leer

    return leer(patron, texto)


def _patron() -> str:
    patron = cargar_perfil_apu_por_hoja(carpetas=()).patron_banda
    assert patron is not None
    return patron


def _tramo(distancia: str | None = "9") -> Tramo:
    return Tramo(
        "B1",
        D("0"),
        D("1"),
        D("5"),
        (Capa("carpeta", D("0.01"), D("2.4"), None),),
        distancia_planta_km=None if distancia is None else D(distancia),
        transporte="banda",
    )


def _presupuesto(descripcion: str, banda: str | None = None) -> Presupuesto:
    item = ItemComputo(
        BANDA,
        "Transporte de mezcla asfáltica desde la planta, por banda de distancia, tramo B1",
        "t",
        D("120"),
        CAPA,
        OrigenTipo.MANUAL,
        Dominio.CIVIL,
        especificaciones={} if banda is None else {ESPEC_BANDA_KM: banda},
    )
    cero = D("0")
    return Presupuesto(
        "VIA-TEST",
        date(2026, 11, 13),
        "Bs",
        (
            PartidaPresupuestada(
                item,
                ComposicionAPU(BANDA, descripcion, "t", D("1")),
                ResultadoAPU(cero, cero, cero, cero, cero, D("1")),
            ),
        ),
    )


def _vr4(tramo: Tramo, presupuesto: Presupuesto, lector=None) -> list[tuple[Severidad, str]]:
    if lector is None:
        patron = _patron()

        def lector(texto: str):
            return leer_banda(patron, texto)

    return [
        (h.severidad, h.descripcion)
        for h in auditar_vial([tramo], presupuesto, lector_de_banda=lector)
        if h.regla == "VR4"
    ]


# --- la lectura común ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "banda"),
    [
        (EN_PALABRAS, (D("8"), D("10"))),
        ("TRANSPORTE DE MEZCLA, MAYOR DE 8 KM Y HASTA 10 KM", (D("8"), D("10"))),
        ("Transporte de mezcla, más de 8,5 km y hasta 10 km", (D("8.5"), D("10"))),
        ("Transporte de mezcla asfáltica desde la planta, por banda de distancia", None),
    ],
)
def test_el_patron_del_perfil_lee_la_banda_escrita_en_palabras(texto: str, banda):
    assert leer_banda(_patron(), texto) == banda


def test_una_cifra_mal_escrita_no_se_adivina():
    from aplicacion.banda_de_distancia import BandaIlegible

    with pytest.raises(BandaIlegible) as error:
        leer_banda(CON_MILES, "Transporte, mayor de 1.5 km y hasta 10 km")
    assert error.value.pieza == "1.5"
    assert str(error.value) == (
        "«1.5» no es una cifra con coma decimal y punto de miles: Sílice no adivina la banda"
    )
    assert leer_banda(CON_MILES, "Transporte, mayor de 1.000 km y hasta 1.200,5 km") == (
        D("1000"),
        D("1200.5"),
    )


def test_el_ah9_del_libro_usa_la_misma_lectura():
    from aplicacion import banda_de_distancia
    from fusion import apu_por_hoja

    assert apu_por_hoja.leer_banda is banda_de_distancia.leer_banda


# --- VR4 con la descripción -----------------------------------------------------------------------


def test_vr4_lee_la_banda_de_la_descripcion_y_no_dice_nada_si_cuadra():
    assert _vr4(_tramo("9"), _presupuesto(EN_PALABRAS)) == []


def test_vr4_advierte_si_la_distancia_cae_fuera_de_la_banda_de_la_descripcion():
    assert _vr4(_tramo("12"), _presupuesto(EN_PALABRAS)) == [
        (
            Severidad.ADVERTENCIA,
            f"{CAPA}: el tramo está a 12 km de la planta y la partida {BANDA} cobra la banda de "
            "más de 8 km y hasta 10 km (leída de su descripción)",
        )
    ]


def test_vr4_dice_de_donde_salio_la_banda_si_el_tramo_no_dice_su_distancia():
    assert _vr4(_tramo(None), _presupuesto(EN_PALABRAS)) == [
        (
            Severidad.INFO,
            f"{CAPA}: la banda de más de 8 km y hasta 10 km (leída de su descripción) no se "
            "compara: el tramo no declara la distancia a la planta",
        )
    ]


def test_vr4_cita_la_descripcion_que_no_dice_la_banda():
    descripcion = "Transporte de mezcla asfáltica desde la planta"
    assert _vr4(_tramo(), _presupuesto(descripcion)) == [
        (
            Severidad.INFO,
            f"{CAPA}: transporte por banda no evaluable: la descripción de la partida {BANDA} "
            f"(«{descripcion}») no dice la banda de distancia como la lee Sílice (por ejemplo "
            "«mayor de 8 km y hasta 10 km»)",
        )
    ]


def test_la_directiva_sigue_mandando_sobre_la_descripcion():
    presupuesto = _presupuesto("Transporte, mayor de 20 km y hasta 30 km", banda="8-10")
    assert _vr4(_tramo("9"), presupuesto) == []


def test_vr4_advierte_una_banda_de_la_descripcion_con_una_cifra_mal_escrita():
    descripcion = "Transporte, mayor de 1.5 km y hasta 10 km"

    def lector(texto: str):
        return leer_banda(CON_MILES, texto)

    assert _vr4(_tramo(), _presupuesto(descripcion), lector) == [
        (
            Severidad.ADVERTENCIA,
            f"{CAPA}: la descripción de la partida {BANDA} («{descripcion}») sigue la forma de la "
            "banda de distancia, pero «1.5» no es una cifra con coma decimal y punto de miles: "
            "Sílice no adivina la banda",
        )
    ]


def test_vr4_advierte_una_banda_de_la_descripcion_al_reves():
    descripcion = "Transporte, mayor de 10 km y hasta 8 km"
    assert _vr4(_tramo(), _presupuesto(descripcion)) == [
        (
            Severidad.ADVERTENCIA,
            f"{CAPA}: la banda de distancia de la descripción de la partida {BANDA} "
            f"(«{descripcion}») no se entiende: el mínimo debe ser menor que el máximo",
        )
    ]


# --- las reglas de la Hoja llevan el lector -------------------------------------------------------


@pytest.fixture
def motor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    vacia = tmp_path / "perfiles"
    vacia.mkdir()
    monkeypatch.setenv("SILICE_PERFILES_LIBROS", str(vacia))  # solo el perfil del repositorio
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            sembrar_vivienda(s, usuario="Ana <ana>")
        yield motor
    finally:
        motor.dispose()


@pytest.mark.parametrize("con_receta", [True, False])
def test_las_reglas_viales_de_la_version_leen_la_descripcion(motor: Engine, con_receta: bool):
    with abrir_sesion(motor) as sesion:
        version = sesion.scalars(
            select(models.Presupuesto.id).where(models.Presupuesto.codigo == "VIV-001")
        ).one()
        vial.guardar_tramos(
            sesion, version, [_tramo("12")], usuario="Ana <ana>", ahora=datetime(2026, 11, 13)
        )
        argumentos = {"codigo_ligante": "LIG-001"} if con_receta else {"hoy": date(2026, 11, 13)}
        (regla,) = vial.reglas_viales(sesion, version, **argumentos)
        hallazgos = [h for h in regla.evaluar(_presupuesto(EN_PALABRAS)) if h.regla == "VR4"]
    assert [
        (h.severidad, h.descripcion.endswith("(leída de su descripción)")) for h in hallazgos
    ] == [(Severidad.ADVERTENCIA, True)]
