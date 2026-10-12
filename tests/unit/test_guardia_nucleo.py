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


def _git_en(repo, *argumentos):
    import subprocess

    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *argumentos],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _escribir(repo, ruta, texto):
    destino = repo / ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")


def test_traer_main_a_una_rama_de_adaptador_no_cuenta_como_cambio_de_nucleo(tmp_path, monkeypatch):
    """Una rama que agrega adapters/ y trae main (con cambios de core/) no viola la regla.

    La fusion de main hacia dentro de la rama no es lo que la rama introdujo: su segundo padre ya
    esta en la base. Sin esta distincion la CI falla en cuanto un adaptador se pone al dia.
    """
    from scripts import meta_alpha

    monkeypatch.setattr(meta_alpha, "RAIZ", tmp_path)
    _git_en(tmp_path, "init", "-q", "-b", "main")
    _escribir(tmp_path, "core/a.py", "x = 1\n")
    _git_en(tmp_path, "add", "-A")
    _git_en(tmp_path, "commit", "-q", "-m", "base")
    _git_en(tmp_path, "switch", "-q", "-c", "rama")
    _escribir(tmp_path, "adapters/nuevo/a.py", "y = 1\n")
    _git_en(tmp_path, "add", "-A")
    _git_en(tmp_path, "commit", "-q", "-m", "adaptador")
    _git_en(tmp_path, "switch", "-q", "main")
    _escribir(tmp_path, "core/a.py", "x = 2\n")
    _escribir(tmp_path, "adapters/otro/b.py", "z = 1\n")
    _git_en(tmp_path, "add", "-A")
    _git_en(tmp_path, "commit", "-q", "-m", "nucleo y otro adaptador en main")
    _git_en(tmp_path, "switch", "-q", "rama")
    _git_en(tmp_path, "merge", "-q", "--no-ff", "-m", "merge main en rama", "main")

    assert meta_alpha._ramas_adaptador("main") == []


def test_una_rama_de_adaptador_fusionada_a_main_con_core_sigue_fallando(tmp_path, monkeypatch):
    """La regla real se conserva: la rama que agrega un adaptador y cambia core/ viola."""
    from scripts import meta_alpha

    monkeypatch.setattr(meta_alpha, "RAIZ", tmp_path)
    _git_en(tmp_path, "init", "-q", "-b", "main")
    _escribir(tmp_path, "core/a.py", "x = 1\n")
    _git_en(tmp_path, "add", "-A")
    _git_en(tmp_path, "commit", "-q", "-m", "base")
    _git_en(tmp_path, "branch", "linea-base")
    _git_en(tmp_path, "switch", "-q", "-c", "rama")
    _escribir(tmp_path, "adapters/nuevo/a.py", "y = 1\n")
    _escribir(tmp_path, "core/a.py", "x = 3\n")
    _git_en(tmp_path, "add", "-A")
    _git_en(tmp_path, "commit", "-q", "-m", "adaptador y core")
    _git_en(tmp_path, "switch", "-q", "main")
    _git_en(tmp_path, "merge", "-q", "--no-ff", "-m", "fusion de rama", "rama")

    ramas = meta_alpha._ramas_adaptador("linea-base")

    assert len(ramas) == 1
    assert ramas[0][1] == ["core/a.py"]
