"""La medición de RNF-15 (spec S2 §3.3): corre, deja su cifra y solo registra (PRU-H21)."""

from __future__ import annotations

import json

from scripts import medir_rnf15


def test_mide_los_dos_trabajos_y_deja_la_cifra_en_su_json(tmp_path):
    salida = tmp_path / "rnf15.json"
    codigo = medir_rnf15.main(
        ["--partidas", "30", "--periodos", "10", "--valuaciones", "5", "--corridas", "2",
         "--salida", str(salida)]
    )  # fmt: skip
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert codigo == 0 and datos["requisito"] == "RNF-15"
    assert (datos["partidas"], datos["periodos"], datos["valuaciones"]) == (30, 10, 5)
    assert len(datos["corridas_registro_s"]) == len(datos["corridas_opciones_s"]) == 2
    assert isinstance(datos["mediana_registro_s"], float) and datos["mediana_registro_s"] > 0
    assert isinstance(datos["mediana_opciones_s"], float) and datos["mediana_opciones_s"] > 0
    assert datos["umbral_s"] == 2.0 and "equipo" in datos


def test_sin_estricto_solo_registra_aunque_supere_el_umbral(tmp_path):
    salida = tmp_path / "rnf15.json"
    argumentos = ["--partidas", "20", "--periodos", "8", "--valuaciones", "4", "--corridas", "1",
                  "--umbral", "0.000001", "--salida", str(salida)]  # fmt: skip
    assert medir_rnf15.main(argumentos) == 0
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["cumple_registro"] is False and datos["cumple_opciones"] is False
    assert medir_rnf15.main([*argumentos, "--estricto"]) == 1


def test_la_ultima_valuacion_se_registra_sobre_una_copia_para_que_cada_corrida_parta_igual(
    tmp_path,
):
    base, obra = medir_rnf15.preparar(tmp_path, 20, 8, 4)
    trabajo = medir_rnf15.trabajo_de_registro(base, obra, tmp_path)
    primera, segunda = trabajo(0), trabajo(1)
    assert primera.indicadores.ev == segunda.indicadores.ev
    assert len(primera.instantanea.valuaciones) == 4  # tres sembradas + la que se mide
    assert (tmp_path / "base.db").stat().st_size > 0
