"""Kappa experto–Sílice por partida y descuento de hallazgos previos (actas del 2026-11-25).

Oráculos independientes del código: las filas de PRESUPUESTO y las hojas APU de cada partida salen
del generador del libro sintético (`Construido.filas_partida`), no del lector; los kappa se
calculan a mano en cada prueba. Libros sintéticos (`tests/fixtures/libros_empresa.py`): ningún
dato real.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import openpyxl
import pytest

from adapters.hoja_empresa.lector import leer_libro
from scripts import medir_auditoria_libro as m
from scripts import medir_partidas as mp
from tests.fixtures.libros_empresa import APUS_LIMPIOS, Siembra, construir_libro, libro_limpio


def _fila(numero: int, *celdas: str, regla: str = "L1") -> m.FilaPlanilla:
    return m.FilaPlanilla(
        numero=numero, regla=regla, severidad="ERROR", celdas=celdas, descripcion="d"
    )


@pytest.fixture(scope="module")
def limpio():
    c = libro_limpio()
    return c, leer_libro(c.datos, "obra.xlsx")


# --- a qué partida va cada hallazgo --------------------------------------------------------------


def test_hallazgo_en_el_renglon_de_presupuesto_cuenta_para_su_partida(limpio):
    c, libro = limpio
    fila_p2 = c.filas_partida["APU-02"]  # 6, según el generador
    s = mp.clasificar([_fila(1, f"PRESUPUESTO!$R${fila_p2}")], libro)
    assert s.partidas == (1, 2, 3)
    assert s.con_error == {2}
    assert s.sin_partida == ()


def test_hallazgo_en_el_apu_se_acredita_a_su_partida(limpio):
    _, libro = limpio
    s = mp.clasificar([_fila(1, "'APU-03'!F12"), _fila(2, "apu-01!$G$45")], libro)
    assert s.con_error == {1, 3}


def test_hallazgo_sin_partida_se_informa_aparte(limpio):
    c, libro = limpio
    filas = [
        _fila(1, "RESUMEN!B13", regla="L5"),
        _fila(2, "INSUMOS!D3", f"PRESUPUESTO!Q{c.fila_subsiniva}", regla="L9"),  # fila de total
        _fila(3, "PROCURA!B5", f"PRESUPUESTO!P{c.filas_partida['APU-01']}", regla="L9"),
        _fila(4),  # sin celdas
    ]
    s = mp.clasificar(filas, libro)
    assert s.sin_partida == (1, 2, 4)
    assert s.con_error == {1}  # la fila 3 toca la partida 1, aunque cite también PROCURA


# --- el kappa por partida ------------------------------------------------------------------------


def _silice(con_error: set[int], n: int = 6, sin_partida: tuple[int, ...] = ()):
    return mp.ClasificacionSilice(
        partidas=tuple(range(1, n + 1)), con_error=frozenset(con_error), sin_partida=sin_partida
    )


def test_kappa_por_partida_incluye_las_sanas():
    # 4 partidas: experto Sí, Sí, No, No; Sílice Sí, No, No, No.
    # po = 3/4; pe = (2·1 + 2·3)/16 = 1/2; κ = (3/4 − 1/2)/(1/2) = 1/2.
    k = mp.kappa_por_partida({1: True, 2: True, 3: False, 4: False}, _silice({1}, n=4))
    assert k.kappa == Fraction(1, 2)
    assert (k.ambos_si, k.solo_experto, k.solo_silice, k.ambos_no) == (1, 1, 0, 2)
    assert k.revisadas == 4 and k.pendientes == 0


def test_partidas_pendientes_no_entran_y_las_filas_sin_partida_se_cuentan():
    # La 5 y la 6 quedan en blanco: el kappa sale de las 4 revisadas (el mismo 1/2 de arriba).
    revision = {1: True, 2: True, 3: False, 4: False, 5: None, 6: None}
    k = mp.kappa_por_partida(revision, _silice({1, 5}, sin_partida=(7, 9)))
    assert k.kappa == Fraction(1, 2)
    assert k.pendientes == 2 and k.filas_sin_partida == 2


def test_la_revision_debe_traer_las_partidas_del_libro():
    with pytest.raises(ValueError, match="faltan \\[3\\]"):
        mp.kappa_por_partida({1: True, 2: False}, _silice(set(), n=3))
    with pytest.raises(ValueError, match="sobran \\[9\\]"):
        mp.kappa_por_partida({1: True, 2: False, 9: True}, _silice(set(), n=2))


def test_kappa_experto_silice_en_la_frontera_exacta_no_declara_fracaso():
    # experto Sí Sí No No No No; Sílice Sí Sí Sí Sí No No: po = 4/6, pe = 1/2, κ = 2/5 exacto.
    revision = {1: True, 2: True, 3: False, 4: False, 5: False, 6: False}
    k = mp.kappa_por_partida(revision, _silice({1, 2, 3, 4}))
    assert k.kappa == Fraction(2, 5)
    assert "Kappa experto–Sílice < 0,4: NO se cumple" in m.criterio_de_fracaso(
        kappa_experto=k.kappa
    )
    assert "Kappa experto–Sílice < 0,4: SE CUMPLE" in m.criterio_de_fracaso(
        kappa_experto=Fraction(39, 100)
    )


def test_el_kappa_entre_evaluadores_no_decide_el_fracaso():
    texto = m.resumen(
        precision=m.precision({1: "Verdadero"}),
        deteccion=None,
        exhaustividad=m.exhaustividad(1, 0),
        kappa=0.3,  # dos evaluadores en desacuerdo: es fiabilidad entre personas
    )
    assert "Kappa experto–Sílice < 0,4: no se puede calcular con los datos de esta corrida" in texto
    assert "fiabilidad entre personas" in texto
    assert "SE CUMPLE" not in texto


def test_el_resumen_trae_el_kappa_experto_silice_y_decide_con_el():
    k = mp.kappa_por_partida({1: True, 2: False, 3: False}, _silice({2, 3}, n=3, sin_partida=(4,)))
    # experto Sí No No; Sílice No Sí Sí: po = 0, κ < 0.
    texto = m.resumen(
        precision=m.precision({1: "Verdadero"}),
        deteccion=None,
        exhaustividad=m.exhaustividad(1, 0),
        kappa=1.0,
        experto=k,
    )
    assert "Kappa experto–Sílice < 0,4: SE CUMPLE" in texto
    assert "Filas de la planilla sin partida (no entran en el kappa): 1" in texto


# --- la planilla de la revisión ------------------------------------------------------------------


def test_revision_vacia_ida_y_vuelta_y_csv(tmp_path: Path, limpio):
    _, libro = limpio
    fuera = tmp_path / "medicion"
    fuera.mkdir()
    ruta = mp.escribir_revision_vacia(libro, fuera / "rev.xlsx", raiz_repo=tmp_path / "repo")
    hoja_ = openpyxl.load_workbook(ruta)
    hoja = hoja_[mp.HOJA_REVISION]
    assert [c.value for c in hoja[1]][:4] == ["Partida", "Código", "Descripción", "¿Tiene error?"]
    assert [hoja.cell(row=f, column=1).value for f in (2, 3, 4)] == [1, 2, 3]
    assert mp.leer_revision(ruta) == {1: None, 2: None, 3: None}
    hoja.cell(row=2, column=4, value="Sí")
    hoja.cell(row=3, column=4, value="no")
    hoja_.save(ruta)
    assert mp.leer_revision(ruta) == {1: True, 2: False, 3: None}
    csv = fuera / "rev.csv"
    csv.write_text("Partida;¿Tiene error?\n1;Si\n2;No\n3;\n", encoding="utf-8")
    assert mp.leer_revision(csv) == {1: True, 2: False, 3: None}


def test_revision_con_respuesta_desconocida_o_partida_repetida_se_rechaza(tmp_path: Path):
    malo = tmp_path / "a.csv"
    malo.write_text("Partida,¿Tiene error?\n1,Quizás\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Quizás"):
        mp.leer_revision(malo)
    doble = tmp_path / "b.csv"
    doble.write_text("Partida,¿Tiene error?\n1,Sí\n1,No\n", encoding="utf-8")
    with pytest.raises(ValueError, match="dos veces"):
        mp.leer_revision(doble)


# --- de punta a punta: exportar -> marcar -> calcular ---------------------------------------------

_BASE = Siembra(verificacion={2: Decimal("3")})  # L9 en PRESUPUESTO!R6: un error previo del libro
_SEMBRADO = Siembra(
    verificacion={2: Decimal("3")}, p_guardado={1: Decimal("999")}, procura_dif=Decimal("5")
)


@pytest.fixture
def corrida(tmp_path: Path):
    fuera = tmp_path / "medicion"
    fuera.mkdir()
    repo = str(tmp_path / "repo")
    base, sembrado = fuera / "base.xlsx", fuera / "sembrado.xlsx"
    base.write_bytes(construir_libro(APUS_LIMPIOS, _BASE).datos)
    sembrado.write_bytes(construir_libro(APUS_LIMPIOS, _SEMBRADO).datos)
    planilla = fuera / "p1.xlsx"
    comunes = ["--fecha", "2026-10-13", "--raiz-repo", repo]
    assert m.main(["exportar", str(sembrado), "--salida", str(planilla), *comunes]) == 0
    return fuera, repo, base, sembrado, planilla


def _marcar(planilla: Path, veredictos: dict[int, str]) -> None:
    libro = openpyxl.load_workbook(planilla)
    hoja = libro["Hallazgos"]
    col = [c.value for c in hoja[1]].index("Veredicto") + 1
    for fila in range(2, hoja.max_row + 1):
        numero = hoja.cell(row=fila, column=1).value
        if numero in veredictos:
            hoja.cell(row=fila, column=col, value=veredictos[numero])
    libro.save(planilla)


def test_calcular_con_la_revision_del_experto(corrida, capsys):
    fuera, repo, _, sembrado, planilla = corrida
    # Sílice señala las partidas 1 (P5, APU-01) y 2 (R6); la 3 queda sana. PROCURA!B5 y
    # RESUMEN!B10 + PRESUPUESTO!Q10 (fila de total) no son de ninguna partida: 2 filas aparte.
    # Experto: 1 Sí, 2 No, 3 No. po = 2/3; pe = (1·2 + 2·1)/9 = 4/9; κ = (2/9)/(5/9) = 2/5.
    revision = fuera / "rev.csv"
    revision.write_text("Partida;¿Tiene error?\n1;Sí\n2;No\n3;No\n", encoding="utf-8")
    _marcar(planilla, {1: "Verdadero"})
    argumentos = ["--libro", str(sembrado), "--revision-experto", str(revision)]
    assert m.main(["calcular", "--planilla", str(planilla), *argumentos]) == 0
    salida = capsys.readouterr().out
    assert "| Kappa de Cohen experto–Sílice por partida" in salida
    assert "0,40" in salida
    assert "Filas de la planilla sin partida (no entran en el kappa): 2" in salida
    assert "Kappa experto–Sílice < 0,4: NO se cumple" in salida


def test_revision_desde_la_linea_de_comandos(corrida):
    fuera, repo, _, sembrado, _ = corrida
    destino = fuera / "rev.xlsx"
    assert m.main(["revision", str(sembrado), "--salida", str(destino), "--raiz-repo", repo]) == 0
    assert mp.leer_revision(destino) == {1: None, 2: None, 3: None}
    instrucciones = [c.value for c in openpyxl.load_workbook(destino)["Instrucciones"]["A"]]
    sha = hashlib.sha256(sembrado.read_bytes()).hexdigest()
    assert f"SHA-256 del libro revisado: {sha}" in instrucciones


def test_calcular_rechaza_la_revision_de_otro_libro(corrida):
    fuera, _, base, _, planilla = corrida
    revision = fuera / "rev.csv"
    revision.write_text("Partida;¿Tiene error?\n1;Sí\n2;No\n3;No\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no es de este libro"):
        m.main(
            ["calcular", "--planilla", str(planilla), "--libro", str(base)]
            + ["--revision-experto", str(revision)]
        )


def _clave(fuera: Path, repo: str, *sembrados: tuple[int, str]) -> Path:
    ruta = fuera / "clave.xlsx"
    m.escribir_clave_vacia(ruta, raiz_repo=Path(repo))
    libro = openpyxl.load_workbook(ruta)
    for numero, celda in sembrados:
        libro["Sembrados"].append([numero, celda, "t", "x", None])
    libro.save(ruta)
    return ruta


def test_falla_sembrada_sobre_un_hallazgo_previo_no_se_acredita(corrida, capsys):
    fuera, repo, base, sembrado, planilla = corrida
    # El sembrado 1 cae en PRESUPUESTO!R6, que el libro base ya señalaba (L9 previo): no cuenta.
    # El sembrado 2 (P.U. guardado en P5) sí lo detecta un hallazgo nuevo. Detección: 1 de 2.
    clave = _clave(fuera, repo, (1, "PRESUPUESTO!R6"), (2, "PRESUPUESTO!P5"))
    _marcar(planilla, {n: "Verdadero" for n in range(1, 7)})
    assert (
        m.main(
            ["calcular", "--planilla", str(planilla), "--clave", str(clave)]
            + ["--libro", str(sembrado), "--libro-base", str(base), "--fecha", "2026-10-13"]
        )
        == 0
    )
    salida = capsys.readouterr().out
    assert "| Detección de errores sembrados (señalado por Sílice) | 1 de 2" in salida
    assert "| Detección, señalado y confirmado verdadero | 1 de 2" in salida
    assert "[9,5 %; 90,5 %]" in salida  # Wilson de 1 de 2, a mano
    assert "Hallazgos previos del libro descontados: 1" in salida


def test_calcular_con_clave_exige_el_libro_base(corrida):
    fuera, repo, _, sembrado, planilla = corrida
    clave = _clave(fuera, repo, (1, "PRESUPUESTO!P5"))
    with pytest.raises(SystemExit):
        m.main(["calcular", "--planilla", str(planilla), "--clave", str(clave)])
    with pytest.raises(SystemExit):
        m.main(
            ["calcular", "--planilla", str(planilla), "--clave", str(clave)]
            + ["--libro", str(sembrado)]
        )


def test_la_reauditoria_debe_dar_las_mismas_filas(corrida):
    # Si la auditoría de `calcular` (otra fecha, otro perfil, sin recalcular) no da las filas que
    # vio el evaluador, las marcas no corresponden: se rechaza en vez de medir mal.
    fuera, repo, base, sembrado, planilla = corrida
    clave = _clave(fuera, repo, (1, "PRESUPUESTO!P5"))
    libro = openpyxl.load_workbook(planilla)
    libro["Hallazgos"].cell(row=2, column=2, value="L4")  # la fila 1 ya no es la de la auditoría
    libro.save(planilla)
    with pytest.raises(ValueError, match="no reproduce la planilla"):
        m.main(
            ["calcular", "--planilla", str(planilla), "--clave", str(clave)]
            + ["--libro", str(sembrado), "--libro-base", str(base), "--fecha", "2026-10-13"]
        )
