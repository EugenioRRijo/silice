"""`scripts/medir_rnf11.py` (RNF-11, SF3 tarea 3.7): mide la hoja sin Streamlit y SOLO registra.

La medicion es: desde aplicar una edicion (una cantidad escrita a mano) hasta tener presupuesto,
informe y punto de equilibrio, sin persistir, en `ui.hoja`, con 500 puntos del generador
determinista; una corrida de calentamiento y la mediana de cinco. La CI ejecuta el script y
registra la cifra: esta suite NO afirma ningun tiempo (una prueba de tiempo en la CI seria fragil
con la carga de la maquina y con la cobertura). Aqui se prueba que el procedimiento es el
declarado (cuantas corridas, que se mide, la mediana), que el veredicto distingue el equipo de
desarrollo de la CI, que el script no rompe por superar los 2 s y que registra la cifra.
"""

from __future__ import annotations

import json
from decimal import Decimal

from scripts import medir_rnf11 as medir
from scripts.generar_hoja_prueba import generar_items


def _reloj(segundos: list[float]):
    """Un reloj falso: cada par de llamadas (inicio, fin) dura el siguiente valor de `segundos`."""
    instantes = []
    acumulado = 0.0
    for duracion in segundos:
        instantes += [acumulado, acumulado + duracion]
        acumulado += duracion + 1.0
    marcas = iter(instantes)
    return lambda: next(marcas)


def test_la_mediana_es_la_del_medio_con_cinco_corridas_y_el_promedio_con_un_numero_par():
    assert medir.mediana([3.0, 1.0, 2.0, 100.0, 0.5]) == 2.0
    assert medir.mediana([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_se_hace_una_corrida_de_calentamiento_y_se_miden_cinco():
    llamadas = []

    def trabajo(i: int) -> None:
        llamadas.append(i)

    medicion = medir.medir(trabajo, corridas=5, reloj=_reloj([9.0, 1.0, 2.0, 3.0, 4.0, 5.0]))

    assert len(llamadas) == 6  # 1 de calentamiento + 5 medidas
    assert medicion.corridas == (1.0, 2.0, 3.0, 4.0, 5.0)  # la de calentamiento (9 s) no cuenta
    assert medicion.mediana == 3.0


def test_cada_corrida_aplica_una_edicion_distinta():
    ediciones = []
    medir.medir(ediciones.append, corridas=3, reloj=_reloj([1.0] * 4))

    assert ediciones == [0, 1, 2, 3]


def test_el_trabajo_medido_es_aplicar_una_edicion_y_elaborar_con_pe_en_ui_hoja():
    trabajo, borrador = medir.preparar(puntos=40)

    resultado = trabajo(0)

    assert len(borrador.items_base) == 40
    assert resultado.elaboracion.presupuesto.partidas  # presupuesto
    assert resultado.elaboracion.informe.reglas_evaluadas  # informe de auditoria
    assert resultado.equilibrio.venta == resultado.elaboracion.presupuesto.total  # PE
    # la edicion cuenta: una cantidad distinta da otro total
    assert trabajo(1).elaboracion.presupuesto.total != resultado.elaboracion.presupuesto.total


def test_la_carga_son_los_puntos_del_generador_determinista():
    _, borrador = medir.preparar(puntos=25)

    assert list(borrador.items_base) == generar_items(25, medir.SEMILLA)
    assert medir.PUNTOS == 500 and medir.CORRIDAS == 5 and medir.UMBRAL_SEGUNDOS == 2.0


def test_el_script_registra_la_cifra_y_no_rompe_por_superar_el_umbral(tmp_path, capsys):
    salida = tmp_path / "rnf11.json"

    codigo = medir.main(
        ["--puntos", "30", "--salida", str(salida)],
        reloj=_reloj([0.0, 5.0, 6.0, 7.0, 8.0, 9.0]),  # medianas de 7 s: muy por encima de 2 s
    )

    assert codigo == 0  # solo registra: ni la CI ni el cierre se rompen
    registro = json.loads(salida.read_text(encoding="utf-8"))
    assert registro["mediana_s"] == 7.0 and registro["puntos"] == 30
    assert registro["umbral_s"] == 2.0 and registro["cumple"] is False
    assert len(registro["corridas_s"]) == 5 and registro["equipo"]
    texto = capsys.readouterr().out
    assert "RNF-11" in texto and "mediana" in texto and "7,000" in texto and "NO cumple" in texto


def test_con_estricto_el_script_falla_solo_si_supera_el_umbral(tmp_path):
    lento = _reloj([0.0, 5.0, 5.0, 5.0, 5.0, 5.0])
    rapido = _reloj([0.0, 0.5, 0.5, 0.5, 0.5, 0.5])

    assert (
        medir.main(["--puntos", "20", "--estricto", "--salida", str(tmp_path / "a")], reloj=lento)
        == 1
    )
    assert (
        medir.main(["--puntos", "20", "--estricto", "--salida", str(tmp_path / "b")], reloj=rapido)
        == 0
    )
    assert json.loads((tmp_path / "b").read_text(encoding="utf-8"))["cumple"] is True


def test_el_registro_guarda_la_cifra_como_decimal_exacto_en_texto(tmp_path):
    salida = tmp_path / "rnf11.json"
    medir.main(["--puntos", "20", "--salida", str(salida)], reloj=_reloj([0.0, 1.25] + [1.25] * 4))

    registro = json.loads(salida.read_text(encoding="utf-8"))
    assert Decimal(registro["mediana_texto"]) == Decimal("1.250")
