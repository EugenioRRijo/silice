"""Prueba de `scripts/probar_precios_maprex.py` (C6, pista R; C6-plan §5).

El script prueba los casos didacticos con precios de referencia publicados (listados MaPreX de
julio de 2026 y tabulador CIV; NORMAS.md §1). Aqui corre sin el detector de atipicos
(`detectar_atipicos=None`): la prueba no depende del extra `ml`; el script, si.

Oraculos independientes del script, escritos a mano desde los CSV:

- **Lista civil derivada: 12 filas.** `referencia_civil.csv` trae 37 filas (13 materiales,
  17 equipos, 7 roles de mano de obra). Los equipos quedan fuera por el ruling C6-9. De los 13
  materiales, solo 5 traen una unidad MaPreX equivalente a la de `data/civil/plantilla_precios.csv`
  (tuberia `m`/`m`; arena, piedra, agua y material granular `m3`/`m3`); los otros 8 no
  (`pza`, `env`, `lt`, `und`, `m3` o `sco` frente a `unidad`, `m2` o `saco`; «sco» no es un alias de
  `core.contracts.unidades`). Los 7 roles de mano de obra se cotizan por `dia` y el catalogo no
  declara unidad para la mano de obra: casan los 7. 5 + 7 = 12; excluidas 8 + 17 = 25.
- **Precios:** tuberia 13,9291 USD/m (PLOA38) y ayudante 1,7816 USD/dia (1-1.2, tabla del README
  de `data/precios/maprex_2026-07/`).
- **Direccion de la revaloracion** (NORMAS.md §4): la tuberia sube (su material pasa de 6 a
  13,9291 USD/m, 1,05 m por pieza: +8,33 USD de materiales; la mano de obra baja
  (11,5 x 7 + 3) / 100 = 0,835 -> (5,8847 x 7 + 3) / 100 = 0,442), y la excavacion baja (no lleva
  materiales y toda su mano de obra baja de jornal).
- **Resultado publicado** (bitacora `2026-09-29-C6-precios-maprex.md`), a mano con NORMAS.md §4:
  tuberia, materiales 7,19 + 1,05 x 7,9291 = 15,515555; equipos 0,033; mano de obra
  (5,8847 x 7 + 3) / 100 = 0,441929; costo directo 15,990484 x 1,15 x 1,10 = 20,2280 -> **20,23**.
  Los cinco PU nuevos 7,54 / 20,23 / 29,38 / 273,96 / 36,37 por las cantidades 9,74 / 24 / 23,68 /
  1,66 / 1,3 dan **1 756,70**. Los precios no mueven ninguna regla: R1-R7 cuentan lo mismo antes y
  despues (3/0/2/1/1/1/0), con R2 = R7 = 0 porque el 001 lleva `plan_secuencial` (su curva cierra
  al 100 %).
- **Contraste de equipos:** el vehiculo de transporte de la tuberia cuesta en el APU
  50 x 0,03 = 1,50 USD/dia y en MaPreX 214,5684 x 1 = 214,5684 (EZ0512, factor 1,000000); la
  retroexcavadora, 200 x 1,00 = 200 frente a 110 025,9187 x 0,0035 = 385,09071545 (MOV027).
- **Bono del Ayudante N2** (Ref 1-1.2): 3 939,53 Bs / 633,3644 = 6,21999... -> 6,2200 USD/dia.
- **Cobertura del listado crudo sobre la base civil** (`lista_maprex_usd.csv`, 111 filas): casa
  una sola fila, `material,ARENA LAVADA,m3` (el catalogo tiene «Arena lavada» en m3); se rechaza
  por unidad una, `equipo,HERRAMIENTAS MENORES,dia` (el catalogo la conoce sin unidad); las otras
  109 son desconocidas del flujo 2a.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path

import pytest

from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.catalog.precios import crear_lista_desde_archivo
from scripts import probar_precios_maprex as prueba
from scripts.seed import RUTA_POR_DEFECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base

RAIZ = Path(__file__).resolve().parents[2]
BASE_DE_TRABAJO = RAIZ / RUTA_POR_DEFECTO

#: Las 12 filas de la lista civil derivada, contadas a mano (docstring del modulo).
FILAS_CIVILES = {
    ("material", "Tubería PVC 4 pulg"),
    ("material", "Arena lavada"),
    ("material", "Piedra picada"),
    ("material", "Agua"),
    ("material", "Material granular"),
    ("mano_obra", "Operador de equipo de 1ra"),
    ("mano_obra", "Ayudante"),
    ("mano_obra", "Chofer de 2da"),
    ("mano_obra", "Chofer de 4ta"),
    ("mano_obra", "Maestro (electricista, según el APU original)"),
    ("mano_obra", "Carpintero de 1ra"),
    ("mano_obra", "Albañil de 1ra"),
}
EXCLUIDAS_CIVILES = 25
SIETE_REGLAS = tuple(f"R{numero}" for numero in range(1, 8))
#: Hallazgos R1-R7 del 001 con sus trazas y `plan_secuencial`, iguales antes y despues.
HALLAZGOS_POR_REGLA_001 = (3, 0, 2, 1, 1, 1, 0)


def _huella(ruta: Path) -> tuple[bool, str | None, int | None]:
    if not ruta.exists():
        return (False, None, None)
    return (True, hashlib.sha256(ruta.read_bytes()).hexdigest(), ruta.stat().st_mtime_ns)


@pytest.fixture(scope="module")
def corridas(tmp_path_factory):
    """Dos corridas completas en carpetas temporales distintas, con la huella de data/apu.db
    antes y despues."""
    antes = _huella(BASE_DE_TRABAJO)
    primera = prueba.probar(tmp_path_factory.mktemp("primera"))
    segunda = prueba.probar(tmp_path_factory.mktemp("segunda"))
    return antes, primera, segunda, _huella(BASE_DE_TRABAJO)


def test_la_lista_civil_derivada_tiene_doce_filas_y_todas_casan(tmp_path):
    derivacion = prueba.derivar_lista_civil()

    assert {(fila.tipo, fila.insumo) for fila in derivacion.filas} == FILAS_CIVILES
    assert len(derivacion.filas) == len(FILAS_CIVILES) == 12
    assert len(derivacion.excluidas) == EXCLUIDAS_CIVILES
    precios = {fila.insumo: fila.precio for fila in derivacion.filas}
    assert precios["Tubería PVC 4 pulg"] == Decimal("13.9291")
    assert precios["Ayudante"] == Decimal("1.7816")
    assert all(isinstance(fila.precio, Decimal) for fila in derivacion.filas)

    # Todas casan con el catalogo sembrado: la carga no deja ninguna desconocida.
    archivo = prueba.escribir_lista(derivacion.filas, tmp_path / "civil.csv")
    motor = crear_motor(f"sqlite:///{(tmp_path / 'civil.db').as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            resumen = crear_lista_desde_archivo(
                sesion,
                archivo,
                nombre="derivada",
                moneda=linea_base.MONEDA,
                fecha_vigencia=prueba.VIGENCIA,
            )
            assert resumen.desconocidos == ()
            sesion.rollback()
    finally:
        motor.dispose()


def test_la_revaloracion_civil_mueve_el_total_y_evalua_las_siete_reglas(corridas):
    _, resultado, _, _ = corridas
    civil = resultado.civil
    comparativo = civil.comparativo

    assert comparativo.total_anterior.quantize(Decimal("0.01")) == Decimal("1586.61")
    assert comparativo.total_nuevo.quantize(Decimal("0.01")) != Decimal("1586.61")
    for informe in (civil.informe_anterior, civil.informe_nuevo):
        assert tuple(codigo for codigo, _ in informe.reglas_evaluadas) == SIETE_REGLAS

    pu = {
        fila.codigo_partida: (fila.pu_anterior, fila.pu_nuevo)
        for fila in comparativo.tabla.itertuples(index=False)
    }
    anterior, nuevo = pu[linea_base.APU_TUBERIA.codigo_partida]
    assert nuevo > anterior
    anterior, nuevo = pu[linea_base.APU_EXCAVACION.codigo_partida]
    assert nuevo < anterior
    # Los 12 precios de la lista cambian 13 insumos: «Agua» tiene dos variantes en el catalogo.
    assert comparativo.insumos_afectados == 13

    # El resultado publicado en la bitacora (aritmetica en el docstring del modulo).
    assert comparativo.total_nuevo.quantize(Decimal("0.01")) == Decimal("1756.70")
    _, pu_tuberia = pu[linea_base.APU_TUBERIA.codigo_partida]
    assert pu_tuberia.quantize(Decimal("0.01")) == Decimal("20.23")
    antes = {r: len(h) for r, h in civil.informe_anterior.por_regla().items() if r in SIETE_REGLAS}
    despues = {r: len(h) for r, h in civil.informe_nuevo.por_regla().items() if r in SIETE_REGLAS}
    assert antes == despues
    assert "R2" not in despues and "R7" not in despues
    for informe in (civil.informe_anterior, civil.informe_nuevo):
        conteos = tuple(n for _, _, n in informe.cuenta_por_regla_evaluada())
        assert conteos == HALLAZGOS_POR_REGLA_001


def test_el_contraste_de_equipos_aplica_el_factor_de_maprex():
    (vehiculo,) = [
        c
        for c in prueba.contrastar_equipos()
        if c.partidas == (linea_base.APU_TUBERIA.codigo_partida,)
        and c.equipo == "Vehículo de transporte"
    ]

    assert vehiculo.tarifa_apu == Decimal("1.50")
    assert vehiculo.tarifa_maprex == Decimal("214.5684")
    # El vehiculo tiene factor 1: la retroexcavadora es la que prueba que el factor se aplica.
    (retro,) = [c for c in prueba.contrastar_equipos() if c.equipo == "Retroexcavadora"]
    assert retro.tarifa_apu == Decimal("200")
    assert retro.tarifa_maprex == Decimal("385.09071545")


def test_el_bono_del_ayudante_n2_sale_de_su_bono_en_bolivares():
    assert prueba.bono_ayudante_maprex() == Decimal("6.2200")


def test_la_cobertura_del_listado_crudo_es_determinista(corridas):
    _, primera, segunda, _ = corridas

    def recuento(resultado):
        return [
            (
                cobertura.base,
                cobertura.filas,
                cobertura.casados,
                tuple(leido.descripcion for leido in cobertura.desconocidos),
                tuple(leido.descripcion for leido in cobertura.rechazados),
            )
            for cobertura in resultado.coberturas
        ]

    assert recuento(primera) == recuento(segunda)
    civil = next(c for c in primera.coberturas if c.base == "civil")
    assert (civil.filas, civil.casados) == (111, 1)
    assert [leido.descripcion for leido in civil.rechazados] == ["HERRAMIENTAS MENORES"]
    assert len(civil.desconocidos) == 109


def test_industrial_y_sistemas_se_revaloran_sin_cambios(corridas):
    _, resultado, _, _ = corridas

    assert [c.caso for c in resultado.comprobaciones] == ["MNT-001", "SIS-001"]
    for comprobacion in resultado.comprobaciones:
        assert comprobacion.desconocidos == 0
        assert comprobacion.insumos_afectados == 0
        assert comprobacion.total_nuevo == comprobacion.total_anterior


def test_el_informe_markdown_trae_las_secciones(corridas):
    _, resultado, _, _ = corridas

    texto = prueba.informe_markdown(resultado)

    for titulo in ("Cobertura", "Comparativo", "Hallazgos", "Atipicos", "Salvedades"):
        assert titulo in texto
    assert "presupuesto real" not in texto.lower()


def test_data_apu_db_no_cambia(corridas):
    antes, _, _, despues = corridas

    assert antes == despues
