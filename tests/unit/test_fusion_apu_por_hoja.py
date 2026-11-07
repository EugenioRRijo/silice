"""F5 vial, tarea 5: auditar un libro con un APU por hoja y, si viene, su libro de presupuesto.

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §7.3 y §8.3, con las
decisiones provisionales 5 (perfiles locales fuera del repositorio) y 6 (las diferencias de
céntimos por redondeo por renglón son INFO) del 2026-11-06. Sílice lee, recalcula e informa: el
libro nunca se modifica.

Libros FICTICIOS de `tests/fixtures/libro_apu_por_hoja.py`; los hallazgos esperados salen de su
memoria de cálculo, a mano:

- APU 1: el libro escribe «lt» y el perfil lo traduce a «l» (INFO).
- APU 2: «t-km» con la cantidad en toneladas se traduce a «t» (INFO), la banda «mayor de 8 km y
  hasta 10 km» se lee de la descripción (INFO) y el P.U. impreso 4,50 no es el recalculado 4,13
  (ERROR).
- APU 3: 0,78 impreso frente a 0,81 recalculado: la diferencia es solo el redondeo por renglón
  (INFO).
- APU 4: financiamiento del 2 %: no evaluable (INFO). APU 5: bono por renglón, no evaluable (INFO),
  e impuesto del 16 % dentro del APU (ADVERTENCIA).
- Presupuesto: el renglón 3 dice 450 m y su APU 500 (ADVERTENCIA), el 5 dice P.U. 0,25 y su APU
  0,20 (ERROR) y el 6 no tiene hoja de APU (ADVERTENCIA).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.hoja_empresa.lector_apu_por_hoja import leer_hojas as leer_hojas_de_verdad
from adapters.hoja_empresa.perfil_apu_por_hoja import (
    VARIABLE_PERFILES,
    cargar_perfil_apu_por_hoja,
)
from fusion.apu_por_hoja import auditar_apu_por_hoja
from tests.fixtures.libro_apu_por_hoja import libro_apu, libro_presupuesto

D = Decimal
PAQUETE = Path(__file__).resolve().parents[2] / "adapters/hoja_empresa/perfiles/apu_por_hoja.json"


@pytest.fixture(scope="module")
def solo_apu():
    return auditar_apu_por_hoja(libro_apu(), "frente_ficticio.xlsx")


@pytest.fixture(scope="module")
def con_presupuesto():
    return auditar_apu_por_hoja(
        libro_apu(),
        "frente_ficticio.xlsx",
        presupuesto=libro_presupuesto(),
        presupuesto_nombre="presupuesto_ficticio.xlsx",
    )


def _resumen(resultado) -> list[tuple[str, str, str]]:
    return [(h.codigo, h.severidad, h.celda) for h in resultado.hallazgos]


HALLAZGOS_APU = [
    ("AH8", "INFO", "APU 1!C9"),
    ("AH8", "INFO", "APU 2!B5"),
    ("AH9", "INFO", "APU 2!B4"),
    ("AH1", "ERROR", "APU 2!G29"),
    ("AH1", "INFO", "APU 3!G35"),
    ("AH3", "INFO", "APU 4!F27"),
    ("AH2", "INFO", "APU 5!E18"),
    ("AH4", "ADVERTENCIA", "APU 5!F27"),
]


def test_los_hallazgos_del_libro_de_apu(solo_apu):
    assert _resumen(solo_apu) == HALLAZGOS_APU


def _q(valor):
    """A 12 decimales: 980 ÷ 300 no es exacto y el orden de las cuentas mueve el último dígito."""
    return None if valor is None else valor.quantize(D("1E-12"))


def test_el_precio_recalculado_de_cada_hoja(solo_apu):
    assert [(a.hoja, a.precio_impreso, _q(a.precio_silice)) for a in solo_apu.apus] == [
        ("APU 1", D("2.08"), D("2.077762500000")),
        ("APU 2", D("4.5"), D("4.132333333333")),  # 980 ÷ 300 × 1,15 × 1,10
        ("APU 3", D("0.78"), D("0.812130000000")),
        ("APU 4", D("820"), None),
        ("APU 5", D("0.2"), None),
    ]


def test_los_mensajes_dicen_las_cifras_con_coma(solo_apu):
    por_celda = {h.celda: h for h in solo_apu.hallazgos}
    assert por_celda["APU 2!G29"].descripcion == (
        "APU 2 (VF-002): el precio unitario impreso es 4,50 y Sílice lo recalcula en 4,13 "
        "(diferencia 0,37; tolerancia 0,01)."
    )
    assert por_celda["APU 3!G35"].descripcion == (
        "APU 3 (VF-003): el precio unitario impreso es 0,78 y Sílice lo recalcula en 0,81: la "
        "diferencia de 0,03 se explica por el redondeo de cada renglón a dos decimales que hace "
        "el programa que exportó el libro (Sílice redondea solo al final)."
    )
    assert por_celda["APU 1!C9"].descripcion == (
        "APU 1: la unidad «lt» del libro se lee como «l» (traducción del perfil apu_por_hoja)."
    )
    assert por_celda["APU 2!B4"].descripcion == (
        "APU 2: transporte por banda de distancia, de más de 8 km y hasta 10 km (leída de la "
        "descripción con el patrón del perfil); la cantidad va en toneladas."
    )
    assert por_celda["APU 4!F27"].descripcion == (
        "APU 4 (VF-004) no evaluable: tiene un financiamiento del 2 % y Sílice no tiene ese "
        "parámetro (reproducirlo exigiría tocar el núcleo)."
    )
    assert por_celda["APU 5!E18"].descripcion == (
        "APU 5 (VF-005) no evaluable: la mano de obra trae un bono de 5 por renglón y el bono de "
        "Sílice es un monto por obrero y día."
    )
    assert por_celda["APU 5!F27"].descripcion == (
        "APU 5 (VF-005): el APU suma un impuesto del 16 %; el IVA va sobre el total del "
        "presupuesto y contarlo también aquí lo cobraría dos veces."
    )
    assert _q(por_celda["APU 2!G29"].impacto) == D("0.367666666667")  # 4,50 − 4,1323…


def test_la_traza_del_desperdicio(solo_apu):
    assert [
        (t.descripcion, t.cantidad_neta, t.desperdicio_pct, t.cantidad) for t in solo_apu.trazas
    ] == [("Emulsión asfáltica ficticia", D("0.5"), D("4"), D("0.52"))]


def test_con_el_presupuesto_enlaza_por_renglon(con_presupuesto):
    assert _resumen(con_presupuesto) == [
        *HALLAZGOS_APU,
        ("AH6", "ADVERTENCIA", "PRESUPUESTO!E6"),
        ("AH5", "ERROR", "PRESUPUESTO!F8"),
        ("AH7", "ADVERTENCIA", "PRESUPUESTO!A9"),
    ]
    por_celda = {h.celda: h for h in con_presupuesto.hallazgos}
    assert por_celda["PRESUPUESTO!F8"].descripcion == (
        "Renglón 5 (VF-005): el presupuesto dice un precio unitario de 0,25 y su APU (APU 5!G28) "
        "imprime 0,20."
    )
    assert por_celda["PRESUPUESTO!E6"].descripcion == (
        "Renglón 3 (VF-003): el presupuesto dice una cantidad de 450 y su APU (APU 3!D5) dice 500."
    )
    assert por_celda["PRESUPUESTO!A9"].descripcion == (
        "Renglón 6 (VF-006): el presupuesto no tiene hoja de APU con ese número."
    )


def test_un_presupuesto_sin_su_hoja_se_rechaza():
    from adapters.hoja_empresa.guardia import ArchivoRechazado

    with pytest.raises(ArchivoRechazado, match="PRESUPUESTO"):
        auditar_apu_por_hoja(
            libro_apu(), "f.xlsx", presupuesto=libro_apu(), presupuesto_nombre="p.xlsx"
        )


# --- perfiles locales -----------------------------------------------------------------------------


def test_un_perfil_local_gana_al_del_paquete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    crudo = json.loads(PAQUETE.read_text(encoding="utf-8"))
    (tmp_path / "apu_por_hoja.json").write_text(
        json.dumps({**crudo, "prefijo_hoja": "HOJA"}), encoding="utf-8"
    )
    monkeypatch.setenv(VARIABLE_PERFILES, str(tmp_path))
    perfil = cargar_perfil_apu_por_hoja()
    assert (perfil.prefijo_hoja, perfil.origen) == ("HOJA", "local")
    monkeypatch.delenv(VARIABLE_PERFILES)
    assert cargar_perfil_apu_por_hoja().origen == "paquete"


def test_auditar_con_otro_perfil_dice_cual_uso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    crudo = json.loads(PAQUETE.read_text(encoding="utf-8"))
    (tmp_path / "frente_local.json").write_text(
        json.dumps({**crudo, "nombre": "frente_local", "unidades": {}}), encoding="utf-8"
    )
    monkeypatch.setenv(VARIABLE_PERFILES, str(tmp_path))
    resultado = auditar_apu_por_hoja(libro_apu(), "f.xlsx", perfil="frente_local")
    assert (resultado.perfil, resultado.origen_perfil) == ("frente_local", "local")
    assert "AH8" not in {h.codigo for h in resultado.hallazgos}  # sin tabla, nada se traduce


# Arbitraje F5 vial, P2 (MAYOR): nadie fija `SILICE_PERFILES_LIBROS` y la pantalla no manda el
# perfil. Por omisión, los perfiles locales viven en `<carpeta de datos>/perfiles_libros/` (la que
# fija el lanzador con `SILICE_DATOS`; aquí, la temporal de la prueba) y un `apu_por_hoja.json`
# allí gana al del paquete. La variable sigue valiendo y, si está, manda ella.


def _perfil_local(carpeta: Path, **cambios) -> None:
    crudo = json.loads(PAQUETE.read_text(encoding="utf-8"))
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "apu_por_hoja.json").write_text(json.dumps({**crudo, **cambios}), encoding="utf-8")


def test_sin_la_variable_el_perfil_local_vive_en_la_carpeta_de_datos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(VARIABLE_PERFILES, raising=False)
    monkeypatch.setenv("SILICE_DATOS", str(tmp_path))
    _perfil_local(tmp_path / "perfiles_libros", unidades={})
    resultado = auditar_apu_por_hoja(libro_apu(), "f.xlsx")
    assert (resultado.perfil, resultado.origen_perfil) == ("apu_por_hoja", "local")
    assert "AH8" not in {h.codigo for h in resultado.hallazgos}  # el local no traduce unidades


def test_sin_perfil_local_en_la_carpeta_de_datos_vale_el_del_paquete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(VARIABLE_PERFILES, raising=False)
    monkeypatch.setenv("SILICE_DATOS", str(tmp_path))
    assert auditar_apu_por_hoja(libro_apu(), "f.xlsx").origen_perfil == "paquete"


def test_la_variable_manda_sobre_la_carpeta_de_datos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from adapters.hoja_empresa.guardia import ArchivoRechazado

    monkeypatch.setenv("SILICE_DATOS", str(tmp_path / "datos"))
    _perfil_local(tmp_path / "datos" / "perfiles_libros", unidades={})
    _perfil_local(tmp_path / "elegida", prefijo_hoja="FICHA")
    monkeypatch.setenv(VARIABLE_PERFILES, str(tmp_path / "elegida"))
    with pytest.raises(ArchivoRechazado, match="«FICHA»"):
        auditar_apu_por_hoja(libro_apu(), "f.xlsx")


# --- un libro hostil: hojas huecas que declaran una dimensión enorme (arbitraje F5 vial, P1) -----
#
# Una hoja con A1 y una celda lejana (CV2000: columna 100, fila 2.000) declara la dimensión
# A1:CV2000. Sin `reset_dimensions()`, openpyxl en solo lectura rellena cada fila hasta la columna
# 100 y cada fila que falta: 200.000 celdas por hoja de unos pocos bytes. Con mil hojas así, un
# archivo de 1 MB pediría gigabytes. Sílice lee solo las hojas que usa (las del prefijo del perfil y
# la del presupuesto) y cada fila solo hasta su última celda real.

LEJOS = "CV2000"
COLUMNAS_HASTA_CV = 100


def _con_hojas_huecas(datos: bytes, n: int, hoja_con_celda_lejana: str) -> bytes:
    """El libro `datos` con `n` hojas huecas declaradas grandes y una celda lejana en una hoja que
    Sílice sí lee (así se ve también que cada fila llega solo hasta su última celda real)."""
    import io

    import openpyxl

    libro = openpyxl.load_workbook(io.BytesIO(datos))
    for k in range(1, n + 1):
        hoja = libro.create_sheet(f"Notas {k}")
        hoja["A1"] = "nota ficticia"
        hoja[LEJOS] = "fin"
    libro[hoja_con_celda_lejana][LEJOS] = "nota lejana"
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def _celdas_leidas(monkeypatch: pytest.MonkeyPatch, apus: bytes, presupuesto: bytes):
    """Audita los dos libros contando las celdas que materializa `leer_hojas` en cada lectura."""
    import adapters.hoja_empresa.lector_apu_por_hoja as lector
    import fusion.apu_por_hoja as auditoria

    original = leer_hojas_de_verdad  # el de verdad, aunque otra llamada ya haya puesto su espía
    medidas: list[int] = []

    def espia(*args, **kwargs):
        hojas = original(*args, **kwargs)
        medidas.append(sum(len(fila) for filas in hojas.values() for fila in filas))
        return hojas

    monkeypatch.setattr(lector, "leer_hojas", espia)
    monkeypatch.setattr(auditoria, "leer_hojas", espia)
    resultado = auditar_apu_por_hoja(
        apus, "f.xlsx", presupuesto=presupuesto, presupuesto_nombre="p.xlsx"
    )
    return medidas, resultado


def test_las_hojas_huecas_declaradas_grandes_no_se_materializan(monkeypatch: pytest.MonkeyPatch):
    normal, de_siempre = _celdas_leidas(monkeypatch, libro_apu(), libro_presupuesto())
    hostil, resultado = _celdas_leidas(
        monkeypatch,
        _con_hojas_huecas(libro_apu(), 3, "APU 1"),
        _con_hojas_huecas(libro_presupuesto(), 3, "PRESUPUESTO"),
    )
    assert len(normal) == 2  # una lectura por libro: el de APU y el del presupuesto
    # Las hojas «Notas» no se leen; la celda lejana suma solo su fila real (A a CV): 100 celdas.
    assert hostil == [normal[0] + COLUMNAS_HASTA_CV, normal[1] + COLUMNAS_HASTA_CV]
    assert _resumen(resultado) == _resumen(de_siempre)
