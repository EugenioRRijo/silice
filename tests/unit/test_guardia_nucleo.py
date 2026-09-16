"""Pruebas de `scripts/guardia_nucleo.py` (integracion continua).

La regla ya la prueba `test_meta_alpha.py` (`estado_nucleo_intacto`); aqui se prueba lo que la
guardia agrega: el codigo de salida y que una base inexistente nunca pase como rango vacio. Como en
`test_meta_alpha.py`, ninguna prueba ejecuta git: `veredicto` recibe los datos ya leidos.
"""

from scripts import guardia_nucleo


def test_base_inexistente_sale_con_2_aunque_no_haya_commits():
    """Sin la validacion, un rango invalido daria cero commits, PENDIENTE y un verde falso."""
    codigo, mensaje = guardia_nucleo.veredicto(
        "rama-inexistente", base_existe=False, commits=[], ramas=[]
    )

    assert codigo == 2
    assert "rama-inexistente" in mensaje


def test_commit_que_mezcla_core_y_adapters_sale_con_1():
    commits = [("a" * 40, ["core/costing/motor.py", "adapters/telecom/adaptador.py"])]

    codigo, mensaje = guardia_nucleo.veredicto("main", base_existe=True, commits=commits, ramas=[])

    assert codigo == 1
    assert "FALLA" in mensaje


def test_commits_que_solo_tocan_adapters_salen_con_0():
    commits = [("b" * 40, ["adapters/telecom/adaptador.py", "tests/unit/test_adapter_telecom.py"])]

    codigo, mensaje = guardia_nucleo.veredicto("main", base_existe=True, commits=commits, ramas=[])

    assert codigo == 0
    assert "OK" in mensaje


def test_rango_sin_commits_de_dominio_sale_con_0():
    """PENDIENTE: no hay commits de adapters/ ni ml/ que puedan violar la regla."""
    codigo, mensaje = guardia_nucleo.veredicto("main", base_existe=True, commits=[], ramas=[])

    assert codigo == 0
    assert "PENDIENTE" in mensaje
