"""UC‑04 sobre el cómputo civil (INV‑073): el recálculo por reglas y sus flujos 1a y 2b.

El oráculo del flujo principal no pasa por `recalcular`: el mismo adaptador tabular extrae la
fuente con la fila ya editada, como la editaría el proyectista. El del flujo 2b es aritmética
escrita a mano sobre la muestra (`data/samples/civil/tanquillas_y_zanja.csv`; supuestos en
`tests/fixtures/computo_civil.py`):

- relleno anterior = 3,6 + 7,68 − 0,896 − 25,2 × 0,008107338624 = 10,1796950666752 m3;
- con la zanja Z‑01 de 500 m × 0,001 m × 0,001 m: excavación 3,6 + 0,0005, tubería 525 m, y el
  balance da 3,6005 − 0,896 − 525 × 0,008107338624 = −1,5518527776 m3, que el recálculo rechaza.

El flujo 2a (modelo IFC) vive en `tests/unit/test_adapter_civil_ifc.py`, que exige el extra civil.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.civil.recalculo import emparejar, recalcular
from adapters.civil.tabular import AdaptadorCivilTabular
from core.budget import elaborar, plan_secuencial
from core.contracts.verificacion import Severidad
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import composiciones_linea_base
from tests.fixtures.computo_civil import CODIGOS

MUESTRA = (
    Path(__file__).resolve().parents[2] / "data" / "samples" / "civil" / "tanquillas_y_zanja.csv"
)
RELLENO_ANTERIOR = Decimal("10.1796950666752")
BALANCE_CON_ZANJA_MINIMA = Decimal("-1.5518527776")
ZANJA_MINIMA = {
    "longitud": Decimal("500"),
    "ancho": Decimal("0.001"),
    "profundidad": Decimal("0.001"),
}
#: Una zanja de longitud cero: la fuente queda sin tubería y su volumen en el relleno, en cero.
SIN_TUBERIA = {"Z-01": {"longitud": Decimal("0")}}
CODIGOS_SIN_RELLENO = {clave: codigo for clave, codigo in CODIGOS.items() if clave != "relleno"}


def _anteriores():
    return AdaptadorCivilTabular(CODIGOS).extraer(MUESTRA)


def _fuente_con(
    tmp_path: Path, cambios: dict[str, dict[str, Decimal]], nombre: str = "fuente_editada"
) -> Path:
    """La muestra con algunas filas cambiadas: la fuente que editaría el proyectista."""
    with MUESTRA.open(newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        campos = lector.fieldnames
        filas = [
            {**fila, **{clave: str(valor) for clave, valor in cambios.get(fila["id"], {}).items()}}
            for fila in lector
        ]
    ruta = tmp_path / f"{nombre}.csv"
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta


@pytest.mark.parametrize(
    ("fila_id", "valores"),
    [
        ("T-01", {"a": Decimal("1.00")}),  # la tanquilla: concreto, encofrado y excavación
        ("Z-01", {"longitud": Decimal("30.00")}),  # la zanja: el volumen de tubería se reescala
    ],
)
def test_recalcular_equivale_a_extraer_la_fuente_editada(tmp_path, fila_id, valores):
    """UC‑04, pasos 1 y 2 (RF‑19): las reglas afectadas se reevalúan, el relleno se rebalancea, y
    el resultado es exactamente lo que da extraer la fuente con la fila ya editada."""
    recalculo = recalcular(_anteriores(), {fila_id: valores}, CODIGOS)

    esperado = AdaptadorCivilTabular(CODIGOS).extraer(_fuente_con(tmp_path, {fila_id: valores}))
    assert recalculo.items == tuple(esperado)
    assert recalculo.sin_regla == () and recalculo.rechazados == ()


def test_sin_relleno_en_los_codigos_no_se_rebalancea(tmp_path):
    """Un llamador que no pide relleno (el adaptador tabular sin `relleno` en `codigos`) recibe
    lo mismo que extraer la fuente editada con esos códigos: ningún ítem de relleno aparece."""
    cambio = {"T-01": {"a": Decimal("1.00")}}
    anteriores = AdaptadorCivilTabular(CODIGOS_SIN_RELLENO).extraer(MUESTRA)

    recalculo = recalcular(anteriores, cambio, CODIGOS_SIN_RELLENO)

    esperado = AdaptadorCivilTabular(CODIGOS_SIN_RELLENO).extraer(_fuente_con(tmp_path, cambio))
    assert recalculo.items == tuple(esperado)


def test_sin_tuberia_en_la_fuente_la_tanquilla_se_recalcula_igual(tmp_path):
    """Con la zanja en longitud cero la tubería es 0 antes y después del cambio: el volumen de
    tubería del relleno se conserva tal cual, sin dividir 0 entre 0."""
    cambio = {"T-01": {"a": Decimal("1.00")}}
    fuente = _fuente_con(tmp_path, SIN_TUBERIA, "sin_tuberia")
    anteriores = AdaptadorCivilTabular(CODIGOS).extraer(fuente)

    recalculo = recalcular(anteriores, cambio, CODIGOS)

    editada = _fuente_con(tmp_path, {**SIN_TUBERIA, **cambio}, "sin_tuberia_editada")
    assert recalculo.items == tuple(AdaptadorCivilTabular(CODIGOS).extraer(editada))


def test_sin_tuberia_en_la_fuente_la_zanja_exige_volver_a_extraerla(tmp_path):
    """Sin tubería previa no hay proporción que escalar: el factor de sección solo vive en la
    fuente, como `diametro`."""
    anteriores = AdaptadorCivilTabular(CODIGOS).extraer(
        _fuente_con(tmp_path, SIN_TUBERIA, "sin_tuberia")
    )

    with pytest.raises(ValueError, match="no tenia tuberia"):
        recalcular(anteriores, {"Z-01": {"longitud": Decimal("30.00")}}, CODIGOS)


def test_un_origen_que_no_esta_en_el_computo_se_rechaza():
    """Un cambio para un objeto que el cómputo no tiene no es un flujo 1a: es un error del
    llamador, y se rechaza en vez de informarse como «sin regla»."""
    with pytest.raises(ValueError, match="ningun item del computo tiene el origen 'X-99'"):
        recalcular(_anteriores(), {"X-99": {"a": Decimal("1.00")}}, CODIGOS)


def test_1a_un_parametro_sin_regla_no_recalcula_y_se_informa():
    anteriores = _anteriores()

    recalculo = recalcular(anteriores, {"T-01": {"material": Decimal("1")}}, CODIGOS)

    assert recalculo.items == tuple(anteriores)
    assert recalculo.sin_regla == ("T-01:material",)
    assert recalculo.rechazados == ()


def test_el_diametro_solo_cambia_volviendo_a_extraer_la_fuente():
    """`diametro` participa en el balance del relleno por un factor fijado al extraer; ningún
    ítem lo lleva, así que no es un flujo 1a: se exige volver a extraer la fuente."""
    with pytest.raises(ValueError, match="vuelva a extraerla"):
        recalcular(_anteriores(), {"Z-01": {"diametro": Decimal("0.2032")}}, CODIGOS)


def test_2b_una_cantidad_nula_se_rechaza_y_conserva_la_anterior():
    """Rechazado un ítem que no es el relleno, el relleno se rebalancea con la cantidad conservada
    y cuadra: el rechazo se informa en `rechazados`, no con un hallazgo de R5 (C2‑6)."""
    anteriores = _anteriores()
    de_la_tanquilla = tuple(item for item in anteriores if item.origen_id == "T-01")

    recalculo = recalcular(anteriores, {"T-01": {"n": Decimal("0")}}, CODIGOS)

    assert recalculo.items == tuple(anteriores)
    assert recalculo.rechazados == de_la_tanquilla


def test_2b_un_relleno_negativo_se_rechaza_y_r5_lo_declara():
    anteriores = _anteriores()
    (relleno,) = [item for item in anteriores if item.codigo_partida == CODIGOS["relleno"]]
    assert relleno.cantidad == RELLENO_ANTERIOR  # el oráculo a mano coincide con la muestra

    recalculo = recalcular(anteriores, {"Z-01": ZANJA_MINIMA}, CODIGOS)

    assert recalculo.rechazados == (relleno,)
    assert relleno in recalculo.items
    resultado = elaborar(
        recalculo.items,
        composiciones_linea_base(),
        linea_base.PARAMETROS_LINEA_BASE,
        codigo="UC04-2B",
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan_secuencial,
    )
    (hallazgo,) = [h for h in resultado.informe.hallazgos if h.regla == "R5"]
    assert hallazgo.severidad == Severidad.ERROR
    assert hallazgo.valor_observado == RELLENO_ANTERIOR
    assert hallazgo.valor_esperado == BALANCE_CON_ZANJA_MINIMA
    assert resultado.informe.partida_de(hallazgo) == CODIGOS["relleno"]
    assert not [h for h in resultado.informe.hallazgos if h.regla == "R1"]  # trazas intactas


@pytest.mark.parametrize("repetida", ["anterior", "nueva"])
def test_emparejar_rechaza_claves_repetidas_en_cualquiera_de_las_versiones(repetida):
    anteriores = _anteriores()
    duplicados = [*anteriores, *anteriores]
    versiones = (duplicados, anteriores) if repetida == "anterior" else (anteriores, duplicados)

    with pytest.raises(ValueError, match=f"la version {repetida} repite .* ambiguo"):
        emparejar(*versiones)
