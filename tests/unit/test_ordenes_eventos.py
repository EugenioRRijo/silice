"""La orden `eventos` de `python -m operacion` (spec S5 §6.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from operacion import __main__ as cli
from operacion import config, eventos_perdidos


def _pendiente(nombre: str) -> Path:
    archivo = config.carpeta_datos() / nombre
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(json.dumps({"revisado": False, "eventos": []}), encoding="utf-8")
    return archivo


def test_los_eventos_pendientes_se_listan_y_se_revisan(capsys) -> None:
    archivo = _pendiente("eventos_perdidos_20261011-120000.json")
    assert cli.main(["eventos", "pendientes"]) == 0
    assert capsys.readouterr().out.splitlines() == [archivo.name]
    assert cli.main(["eventos", "revisar", str(archivo)]) == 0
    assert f"Revisado: {archivo}" in capsys.readouterr().out
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    assert datos["revisado"] is True and datos["revisado_por"] == "administrador"
    assert cli.main(["eventos", "pendientes"]) == 0
    assert capsys.readouterr().out == ""
    assert eventos_perdidos.bloqueadas() is False


def test_con_dos_pendientes_revisar_uno_deja_el_otro(capsys) -> None:
    uno = _pendiente("eventos_perdidos_20261011-120000.json")
    otro = _pendiente("eventos_perdidos_20261012-120000.json")
    assert cli.main(["eventos", "revisar", str(uno)]) == 0
    capsys.readouterr()
    assert cli.main(["eventos", "pendientes"]) == 0
    assert capsys.readouterr().out.splitlines() == [otro.name]


def test_sin_pendientes_la_lista_esta_vacia(capsys) -> None:
    assert cli.main(["eventos", "pendientes"]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("argumentos", [["eventos"], ["eventos", "revisar"], ["eventos", "otra"]])
def test_la_orden_mal_formada_es_un_error_de_uso(capsys, argumentos: list[str]) -> None:
    with pytest.raises(SystemExit) as salida:
        cli.main(argumentos)
    assert salida.value.code == 2
    capsys.readouterr()


@pytest.mark.parametrize("contenido", ["{no es json", "[]", None])
def test_revisar_un_archivo_ilegible_o_que_falta_dice_que_paso_y_sale_con_1(
    capsys, contenido: str | None
) -> None:
    """Tras el arreglo de SEG-12 (`marcar_revisado` ya no sobrescribe un archivo ilegible), la
    orden terminaba con una traza. Ahora dice qué pasó y qué hacer, sale con 1 y no escribe."""
    archivo = config.carpeta_datos() / "eventos_perdidos_20261011-130000.json"
    archivo.parent.mkdir(parents=True, exist_ok=True)
    if contenido is not None:
        archivo.write_text(contenido, encoding="utf-8")
    assert cli.main(["eventos", "revisar", str(archivo)]) == 1
    salida = capsys.readouterr()
    assert salida.out == ""
    # Anexo A.4 del plan de desenredo: el mismo texto que el 409 de la API (H10).
    assert archivo.name in salida.err and eventos_perdidos.MENSAJE_ILEGIBLE in salida.err
    # Un literal fijo: con la constante vacia la linea de arriba pasaria igual.
    assert "no se marcó como revisado" in salida.err and "siguen bloqueadas" in salida.err
    assert "Traceback" not in salida.err
    if contenido is None:
        assert not archivo.exists()
    else:
        assert archivo.read_text(encoding="utf-8") == contenido
