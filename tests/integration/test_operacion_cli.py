"""`python -m operacion` (spec S5 §6.5): adoptar la base de trabajo anterior y las órdenes de
consulta, respaldo y restauración, con la carpeta de datos temporal de `tests/conftest.py`."""

from __future__ import annotations

from pathlib import Path

from operacion import config, respaldo
from operacion.__main__ import main
from operacion.base_datos import Destino, revision_head
from tests.fixtures import bases_prueba


def test_adoptar_y_las_demas_ordenes(tmp_path: Path, capsys) -> None:
    anterior = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "data" / "apu.db")
    antes = respaldo.huella(anterior)
    assert main(["adoptar", str(anterior), "--nombre", "silice"]) == 0
    assert respaldo.huella(anterior) == antes
    assert main(["casos"]) == 0
    assert "silice.db" in capsys.readouterr().out
    assert main(["revision"]) == 0
    assert f"silice.db: {revision_head(Destino.CASO)}" in capsys.readouterr().out
    assert main(["respaldar"]) == 0
    manuales = [
        c for c, f in respaldo.listar_juegos(config.carpeta_respaldos()) if f["motivo"] == "manual"
    ]
    assert len(manuales) == 1
    assert main(["restaurar", str(manuales[0]), "--solo-caso", "silice"]) == 0
    assert main(["migrar"]) == 0


def test_un_error_de_base_sale_con_1_y_su_mensaje(tmp_path: Path, capsys) -> None:
    futura = bases_prueba.crear_base_futura(tmp_path / "futura.db")
    assert main(["adoptar", str(futura)]) == 1
    assert "versión más nueva" in capsys.readouterr().err
    assert not (config.carpeta_casos() / "futura.db").exists()
