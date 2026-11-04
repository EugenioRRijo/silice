"""Plan vial, Tarea 16b (filas 58 y 63): VR2 recibe la fórmula de la receta vigente. FICTICIO.

`aplicacion.vial.reglas_viales(sesion, version, hoy=…, instalacion=…)` sin receta explícita arma
la fórmula de trabajo de cada partida de mezcla de los tramos (`C-000.000.009` carpeta,
`C-000.000.011` bacheo) así: el APU de la partida en el catálogo de la carpeta usa la mezcla propia
por su línea «Costo propio de mezcla <producto>» (la que deja la publicación, la misma que reconoce
CV3); de la base de la instalación sale la receta **vigente** de ese producto a `hoy`; el ligante
es el único componente comprado en t de la receta, y la fórmula, su cantidad por tonelada × 100.
Cuando falta algo, `sin_formula` dice qué y VR2 lo declara.

Carpeta: la «Vivienda Demo 80 m2» (VIV-001) con la partida de la mezcla de la carpeta compuesta
con la mezcla propia MZ-1. Instalación en memoria con las recetas de `tests/fixtures/costo_propio`:
A desde el 01/10/2026 (CA-30 0,05 t/t → 5 %) y B desde el 16/11/2026 (CA-30 0,04 t/t → 4 %).
Oráculos a mano.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Tramo
from aplicacion import hoja, vial
from core import models
from core.budget import elaborar, guardar_presupuesto, plan_secuencial
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts import Dominio
from core.contracts.apu import ComposicionAPU, LineaMaterial
from core.contracts.verificacion import Severidad
from operacion.base_datos import preparar_base
from produccion.receta import Componente, receta_vigente
from tests.fixtures import costo_propio as cp
from tests.fixtures.carpeta_aprobaciones import FECHA, OBRA, PARAMETROS, sembrar_vivienda

D = Decimal
ANA = "Ana <ana>"
LUNES = datetime(2026, 10, 19, 9, 0)
MEZCLA = "C-000.000.009"
BACHEO = "C-000.000.011"
T1 = Tramo(
    "T1",
    D("0"),
    D("1"),
    D("7"),
    (Capa("carpeta", D("0.05"), D("2.4"), None, D("6.5")),),
)


def _componer(sesion: Session, codigo: str, unidad: str, material: str) -> None:
    lista = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == "Lista Bs de prueba")
    ).one()
    linea = LineaMaterial(material, unidad, D("1"), D("3"))
    apu = ComposicionAPU(codigo, f"Partida vial {codigo}", unidad, D("10"), materiales=(linea,))
    Catalogo(sesion).cargar_composicion(apu, lista, Dominio.CIVIL, FECHA, "prueba")
    sesion.commit()


def _version(sesion: Session) -> int:
    return sesion.scalars(
        select(models.Presupuesto.id).where(models.Presupuesto.codigo == "VIV-001")
    ).one()


def _carpeta(tmp_path: Path, material: str) -> Iterator[Session]:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar_vivienda(sesion, usuario=ANA)
            _componer(sesion, MEZCLA, "t", material)
            vial.guardar_tramos(sesion, _version(sesion), [T1], usuario=ANA, ahora=LUNES)
            yield sesion
    finally:
        motor.dispose()


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator[Session]:
    yield from _carpeta(tmp_path, "Costo propio de mezcla MZ-1")


@pytest.fixture
def ins() -> Iterator[Session]:
    with cp.instalacion_en_memoria() as sesion:
        cp.materiales(sesion)
        cp.receta(sesion)  # A, desde el 01/10/2026
        cp.receta(sesion, cp.RECETA_B, desde=date(2026, 11, 16))
        yield sesion


def _regla(sesion: Session, ins: Session | None, hoy: date):
    (regla,) = vial.reglas_viales(sesion, _version(sesion), hoy=hoy, instalacion=ins)
    return regla


def test_la_formula_sale_de_la_receta_vigente_de_la_mezcla_del_apu(sesion, ins) -> None:
    regla = _regla(sesion, ins, date(2026, 10, 31))
    assert (regla.formulas, regla.sin_formula) == ({MEZCLA: D("5")}, {})
    assert _regla(sesion, ins, date(2026, 11, 20)).formulas == {MEZCLA: D("4")}


def test_sin_receta_vigente_vr2_no_se_evalua_y_dice_por_que(sesion, ins) -> None:
    regla = _regla(sesion, ins, date(2026, 9, 30))
    assert regla.formulas == {}
    assert regla.sin_formula == {
        MEZCLA: "la mezcla propia MZ-1 no tiene receta vigente al 30/09/2026"
    }


def test_un_ligante_que_no_se_distingue_no_se_adivina(sesion) -> None:
    with cp.instalacion_en_memoria() as ins:
        cp.materiales(ins)
        cp.receta(
            ins,
            (
                Componente("AGR-12", D("0.90"), "t", "propio"),
                Componente("CA-30", D("0.05"), "t", "comprado"),
                Componente("CAL", D("0.05"), "t", "comprado"),
            ),
        )
        regla = _regla(sesion, ins, date(2026, 10, 31))
    assert regla.formulas == {}
    assert regla.sin_formula == {
        MEZCLA: "la receta n.º 1 de MZ-1 tiene 2 componentes comprados en t (CA-30, CAL) y no se "
        "sabe cuál es el ligante"
    }


def test_un_apu_sin_mezcla_propia_no_abre_la_instalacion(tmp_path, monkeypatch) -> None:
    def no_abrir():
        raise AssertionError("no debía abrir la instalación")

    monkeypatch.setattr(vial, "_abrir_instalacion", no_abrir)
    for sesion in _carpeta(tmp_path, "Mezcla asfáltica comprada"):
        regla = _regla(sesion, None, date(2026, 10, 31))
        assert regla.formulas == {}
        assert regla.sin_formula == {
            MEZCLA: "el APU de la partida C-000.000.009 no usa una mezcla propia (una línea "
            "«Costo propio de mezcla …»)"
        }


def test_una_partida_de_mezcla_sin_apu_lo_dice(sesion, ins) -> None:
    bacheo = Tramo("T2", D("1"), D("2"), D("3"), (Capa("bacheo", D("0.1"), D("2.3"), None),))
    vial.guardar_tramos(sesion, _version(sesion), [T1, bacheo], usuario=ANA, ahora=LUNES)
    regla = _regla(sesion, ins, date(2026, 10, 31))
    assert regla.formulas == {MEZCLA: D("5")}
    assert regla.sin_formula == {BACHEO: "la partida C-000.000.011 no está en el catálogo"}


def test_con_receta_explicita_manda_la_de_siempre(sesion, ins) -> None:
    """La forma de la Tarea 9 (receta y código del ligante dados) no mira la instalación."""
    (regla,) = vial.reglas_viales(
        sesion,
        _version(sesion),
        receta=receta_vigente(ins, "MZ-1", date(2026, 10, 31)),
        codigo_ligante="CA-30",
    )
    assert (regla.formula_asfalto_pct, regla.formulas, regla.sin_formula) == (D("5"), {}, {})


def test_el_porcentaje_de_asfalto_se_guarda_y_se_lee(sesion) -> None:
    (leido,) = vial.tramos_de_version(sesion, _version(sesion))
    assert leido == T1 and leido.capas[0].asfalto_pct == D("6.5")


# --- al abrir una versión con tramos (la llamada de `hoja.abrir_version`, sin `hoy`) ------------


def _guardar_vial_001(sesion: Session) -> Catalogo:
    """La versión VIAL-001 de la obra con las cantidades de T1, guardada como en la Hoja."""
    obra = sesion.scalars(select(models.Proyecto).where(models.Proyecto.nombre == OBRA)).one()
    _componer(sesion, "C-000.000.008", "m2", "Material de C-000.000.008")
    lista = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == "Lista Bs de prueba")
    ).one()
    catalogo = Catalogo(sesion)
    items = derivar_tramos([T1])
    resultado = elaborar(
        items,
        catalogo.composiciones({i.codigo_partida for i in items}, FECHA),
        PARAMETROS,
        codigo="VIAL-001",
        fecha=FECHA,
        moneda="Bs",
        plan=plan_secuencial,
    )
    guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=obra,
        lista=lista,
        parametros=PARAMETROS,
        pendientes=resultado.pendientes,
        usuario=ANA,
    )
    sesion.commit()
    return catalogo


def test_al_abrir_una_version_con_tramos_vr2_usa_la_receta_vigente(sesion, monkeypatch) -> None:
    """`abrir_version` llama `reglas_viales(sesion, id)` (su llamada es parte del experimento
    congelado y no cambia): la fórmula se lee de la instalación con la fecha del día. La receta
    rige desde el 01/01/2026, así el día del reloj no cambia el oráculo: 6,5 contra 5."""
    catalogo = _guardar_vial_001(sesion)
    with cp.instalacion_en_memoria() as ins:
        cp.materiales(ins)
        cp.receta(ins, desde=date(2026, 1, 1))

        @contextmanager
        def la_de_la_prueba():
            yield ins

        monkeypatch.setattr(vial, "_abrir_instalacion", la_de_la_prueba)
        abierta = hoja.abrir_version(sesion, catalogo, OBRA, "VIAL-001")

    (vr2,) = [h for h in abierta.guardada.informe.hallazgos if h.regla == "VR2"]
    assert (vr2.severidad, vr2.origen_ids) == (Severidad.ADVERTENCIA, ("tramo:T1:capa:1",))
    assert (vr2.valor_observado, vr2.valor_esperado) == (D("6.5"), D("5"))


@pytest.mark.parametrize(
    "falla",
    [
        OperationalError("SELECT", {}, Exception("database is locked")),
        PermissionError(13, "Acceso denegado", "instalacion.db"),
    ],
    ids=["base_bloqueada", "archivo_ilegible"],
)
def test_si_la_instalacion_no_se_puede_leer_vr2_lo_declara_y_la_hoja_abre(
    sesion, monkeypatch, falla
):
    """VR2 es un aviso: una base de la instalación bloqueada (`SQLAlchemyError`) o un archivo que
    el sistema no deja leer (`OSError`, p. ej. la carpeta sincronizada sin permiso) no impide
    abrir la Hoja: la versión abre y VR2 declara el motivo (MENOR 2 del árbitro de la 16b)."""

    def rota():
        raise falla

    catalogo = _guardar_vial_001(sesion)
    monkeypatch.setattr(vial, "_abrir_instalacion", rota)
    regla = _regla(sesion, None, date(2026, 10, 31))
    assert regla.formulas == {}
    assert regla.sin_formula == {
        MEZCLA: "no se pudo leer la base de la instalación para buscar la receta de MZ-1"
    }

    abierta = hoja.abrir_version(sesion, catalogo, OBRA, "VIAL-001")

    (vr2,) = [h for h in abierta.guardada.informe.hallazgos if h.regla == "VR2"]
    assert vr2.severidad == Severidad.INFO
    assert vr2.descripcion == (
        "tramo:T1:capa:1: asfalto de 6,5 % sin comparar con la fórmula de trabajo: no se pudo "
        "leer la base de la instalación para buscar la receta de MZ-1"
    )


def test_el_ligante_marcado_resuelve_una_receta_con_otro_comprado_en_t(sesion) -> None:
    with cp.instalacion_en_memoria() as ins:
        cp.materiales(ins)
        cp.receta(
            ins,
            (
                Componente("AGR-12", D("0.90"), "t", "propio"),
                Componente("CAL", D("0.05"), "t", "comprado"),
                Componente("CA-30", D("0.05"), "t", "comprado", es_ligante=True),
            ),
        )
        regla = _regla(sesion, ins, date(2026, 10, 31))
    assert (regla.formulas, regla.sin_formula) == ({MEZCLA: D("5")}, {})


def test_sin_marca_y_con_dos_comprados_en_t_se_mantiene_el_motivo(sesion) -> None:
    # la regla vieja no cambia: sin marca no se adivina (véase el caso de arriba, sin es_ligante)
    with cp.instalacion_en_memoria() as ins:
        cp.materiales(ins)
        cp.receta(
            ins,
            (
                Componente("AGR-12", D("0.90"), "t", "propio"),
                Componente("CAL", D("0.05"), "t", "comprado"),
                Componente("CA-30", D("0.05"), "t", "comprado"),
            ),
        )
        regla = _regla(sesion, ins, date(2026, 10, 31))
    assert regla.formulas == {} and "no se sabe cuál es el ligante" in regla.sin_formula[MEZCLA]
