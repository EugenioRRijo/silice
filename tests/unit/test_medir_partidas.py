"""Kappa experto–Sílice por partida y descuento de hallazgos previos (actas del 2026-11-25).

Oráculos independientes del código: las filas de PRESUPUESTO y las hojas APU de cada partida salen
del generador del libro sintético (`Construido.filas_partida`), no del lector; los kappa se
calculan a mano en cada prueba. Libros sintéticos (`tests/fixtures/libros_empresa.py`): ningún
dato real. Cada partida se identifica por su fila del PRESUPUESTO (hay libros con números de
partida repetidos, L8).
"""

from __future__ import annotations

import dataclasses
import hashlib
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import openpyxl
import pytest

from adapters.hoja_empresa.lector import leer_libro
from core.contracts.verificacion import Hallazgo, Severidad
from scripts import hallazgos_previos as hp
from scripts import medir_auditoria_libro as m
from scripts import medir_inyeccion as mi
from scripts import medir_partidas as mp
from tests.fixtures.libros_empresa import APUS_LIMPIOS, Siembra, construir_libro, libro_limpio
from tests.fixtures.recalculo_falso import LibreOfficeFalso


def _fila(numero: int, *celdas: str, regla: str = "L1") -> m.FilaPlanilla:
    return m.FilaPlanilla(
        numero=numero, regla=regla, severidad="ERROR", celdas=celdas, descripcion="d"
    )


@pytest.fixture(scope="module")
def limpio():
    c = libro_limpio()
    return c, leer_libro(c.datos, "obra.xlsx")


def _con_partidas(libro, **por_fila):
    """El mismo libro con algunas partidas cambiadas, por fila: `f6={"numero": 1}`."""
    partidas = tuple(
        dataclasses.replace(p, **por_fila.get(f"f{p.fila}", {})) for p in libro.partidas
    )
    return dataclasses.replace(libro, partidas=partidas)


# --- a qué partida va cada hallazgo --------------------------------------------------------------


def test_hallazgo_en_el_renglon_de_presupuesto_cuenta_para_su_partida(limpio):
    c, libro = limpio
    fila_p2 = c.filas_partida["APU-02"]  # 6, según el generador
    s = mp.clasificar([_fila(1, f"PRESUPUESTO!$R${fila_p2}")], libro)
    assert s.partidas == tuple(c.filas_partida[h] for h in ("APU-01", "APU-02", "APU-03"))
    assert s.con_error == {fila_p2}
    assert s.sin_partida == ()


def test_hallazgo_en_el_apu_se_acredita_a_su_partida(limpio):
    c, libro = limpio
    s = mp.clasificar([_fila(1, "'APU-03'!F12"), _fila(2, "apu-01!$G$45")], libro)
    assert s.con_error == {c.filas_partida["APU-01"], c.filas_partida["APU-03"]}


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
    assert s.con_error == {c.filas_partida["APU-01"]}  # la fila 3 toca la partida 1


def test_un_rango_del_presupuesto_cuenta_para_cada_partida_que_cubre(limpio):
    c, libro = limpio
    f1, f2 = c.filas_partida["APU-01"], c.filas_partida["APU-02"]  # 5 y 6
    s = mp.clasificar(
        [_fila(1, f"PRESUPUESTO!$N${f1}:$O${f2}"), _fila(2, "PRESUPUESTO!A1:A3")], libro
    )
    assert s.con_error == {f1, f2}
    assert s.sin_partida == (2,)  # la cabecera no es de ninguna partida


def test_un_apu_compartido_cuenta_para_todas_sus_partidas(limpio):
    c, libro = limpio
    f1, f2 = c.filas_partida["APU-01"], c.filas_partida["APU-02"]
    # la partida de la fila 6 también usa APU-01 (con un espacio de más en el nombre)
    compartido = _con_partidas(libro, **{f"f{f2}": {"hoja_apu": " apu-01 "}})
    s = mp.clasificar([_fila(1, "APU-01!F12")], compartido)
    assert s.con_error == {f1, f2}


def test_una_partida_sin_apu_solo_cuenta_por_su_renglon(limpio):
    c, libro = limpio
    f3 = c.filas_partida["APU-03"]
    sin_apu = _con_partidas(libro, **{f"f{f3}": {"hoja_apu": None}})
    s = mp.clasificar([_fila(1, "APU-03!F12"), _fila(2, f"PRESUPUESTO!P{f3}")], sin_apu)
    assert s.sin_partida == (1,)  # APU-03 ya no está unido a ninguna partida
    assert s.con_error == {f3}


def test_un_hallazgo_cuenta_para_todas_las_partidas_de_sus_celdas(limpio):
    # Decisión conservadora (acta literal): un L3 que cita la celda de otra partida como
    # referencia cuenta para las dos.
    c, libro = limpio
    s = mp.clasificar([_fila(1, f"PRESUPUESTO!P{c.filas_partida['APU-01']}", "APU-02!G45")], libro)
    assert s.con_error == {c.filas_partida["APU-01"], c.filas_partida["APU-02"]}


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


def test_kappa_sin_variacion_o_sin_revisadas_no_se_puede_calcular():
    # Todas sanas para los dos, o todas con error para los dos: pe = 1, κ indefinido.
    sanas = mp.kappa_por_partida({1: False, 2: False, 3: False}, _silice(set(), n=3))
    todas = mp.kappa_por_partida({1: True, 2: True, 3: True}, _silice({1, 2, 3}, n=3))
    vacia = mp.kappa_por_partida({1: None, 2: None, 3: None}, _silice({1}, n=3))
    assert sanas.kappa is None and sanas.ambos_no == 3
    assert todas.kappa is None and todas.ambos_si == 3
    assert vacia.kappa is None and vacia.revisadas == 0 and vacia.pendientes == 3
    for k in (sanas, todas, vacia):
        texto = m.criterio_de_fracaso(kappa_experto=k.kappa)
        assert "Kappa experto–Sílice < 0,4: no se puede calcular con los datos de esta corrida" in (
            texto
        )


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


def _llenar_revision(ruta: Path, respuestas: dict[int, str]) -> None:
    """Escribe «¿Tiene error?» por fila del PRESUPUESTO."""
    libro = openpyxl.load_workbook(ruta)
    hoja = libro[mp.HOJA_REVISION]
    cabeza = [c.value for c in hoja[1]]
    col_fila, col_error = cabeza.index("Fila") + 1, cabeza.index("¿Tiene error?") + 1
    for r in range(2, hoja.max_row + 1):
        fila = hoja.cell(row=r, column=col_fila).value
        if fila in respuestas:
            hoja.cell(row=r, column=col_error, value=respuestas[fila])
    libro.save(ruta)


def test_revision_vacia_ida_y_vuelta_y_csv(tmp_path: Path, limpio):
    c, libro = limpio
    filas = [c.filas_partida[h] for h in ("APU-01", "APU-02", "APU-03")]  # 5, 6, 7
    fuera = tmp_path / "medicion"
    fuera.mkdir()
    ruta = mp.escribir_revision_vacia(libro, fuera / "rev.xlsx", raiz_repo=tmp_path / "repo")
    hoja = openpyxl.load_workbook(ruta)[mp.HOJA_REVISION]
    assert [c.value for c in hoja[1]][:5] == [
        "Fila",
        "Partida",
        "Código",
        "Descripción",
        "¿Tiene error?",
    ]
    assert [hoja.cell(row=r, column=1).value for r in (2, 3, 4)] == filas
    assert [hoja.cell(row=r, column=2).value for r in (2, 3, 4)] == [1, 2, 3]
    assert mp.leer_revision(ruta) == dict.fromkeys(filas)
    _llenar_revision(ruta, {filas[0]: "Sí", filas[1]: "no"})
    assert mp.leer_revision(ruta) == {filas[0]: True, filas[1]: False, filas[2]: None}
    csv = fuera / "rev.csv"
    csv.write_text("Fila;¿Tiene error?\n5;Si\n6;No\n7;\n", encoding="utf-8")
    assert mp.leer_revision(csv) == {5: True, 6: False, 7: None}


def test_numeros_de_partida_repetidos_se_distinguen_por_fila(tmp_path: Path, limpio):
    # L8: dos partidas con el número 1. La revisión, la clasificación y el kappa van por fila.
    c, libro = limpio
    f1, f2, f3 = (c.filas_partida[h] for h in ("APU-01", "APU-02", "APU-03"))
    repetido = _con_partidas(libro, **{f"f{f2}": {"numero": 1}})
    fuera = tmp_path / "medicion"
    fuera.mkdir()
    ruta = mp.escribir_revision_vacia(repetido, fuera / "rev.xlsx", raiz_repo=tmp_path / "repo")
    _llenar_revision(ruta, {f1: "Sí", f2: "No", f3: "No"})
    revision = mp.leer_revision(ruta)
    assert revision == {f1: True, f2: False, f3: False}
    s = mp.clasificar([_fila(1, "APU-02!F12")], repetido)  # la segunda «partida 1»
    assert s.con_error == {f2}
    k = mp.kappa_por_partida(revision, s)
    # experto Sí No No; Sílice No Sí No: po = 1/3; pe = (1·1 + 2·2)/9 = 5/9; κ = −1/2.
    assert k.revisadas == 3 and k.kappa == Fraction(-1, 2)


def test_revision_con_respuesta_desconocida_o_fila_repetida_se_rechaza(tmp_path: Path):
    malo = tmp_path / "a.csv"
    malo.write_text("Fila,¿Tiene error?\n5,Quizás\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Quizás"):
        mp.leer_revision(malo)
    doble = tmp_path / "b.csv"
    doble.write_text("Fila,¿Tiene error?\n5,Sí\n5,No\n", encoding="utf-8")
    with pytest.raises(ValueError, match="dos veces"):
        mp.leer_revision(doble)


def test_revision_sin_las_columnas_se_rechaza_aunque_no_tenga_filas(tmp_path: Path):
    vacio = tmp_path / "a.csv"
    vacio.write_text("Partida;Opinión\n", encoding="utf-8")
    with pytest.raises(ValueError, match="debe traer las columnas"):
        mp.leer_revision(vacio)
    hoja_vacia = tmp_path / "b.xlsx"
    libro = openpyxl.Workbook()
    libro.active.title = mp.HOJA_REVISION
    libro.active.append(["Partida", "Nota"])
    libro.save(hoja_vacia)
    with pytest.raises(ValueError, match="debe traer las columnas"):
        mp.leer_revision(hoja_vacia)


# --- descuento de hallazgos previos por celda ----------------------------------------------------


def _h(regla: str, *celdas: str, texto: str = "d") -> Hallazgo:
    return Hallazgo(regla=regla, severidad=Severidad.ERROR, descripcion=texto, origen_ids=celdas)


def test_una_celda_nueva_no_rescata_las_celdas_previas_de_la_misma_regla():
    # L5 agrupado por hoja: el libro base ya citaba RESUMEN!B13; el sembrado agrega B14.
    base = [_h("L5", "RESUMEN!B13")]
    sembrado = [_h("L5", "RESUMEN!$B$13", "RESUMEN!B14")]
    assert hp.hallazgos_nuevos(base, sembrado) == [_h("L5", "RESUMEN!B14")]
    filas = m.causas_de_hallazgos(hp.hallazgos_nuevos(base, sembrado))
    d = m.deteccion([m.Sembrado(1, "RESUMEN!B13", "t"), m.Sembrado(2, "RESUMEN!B14", "t")], filas)
    assert d.por_sembrado == {1: None, 2: 1}


def test_otra_regla_sobre_la_misma_celda_si_es_nueva():
    base = [_h("L5", "RESUMEN!B13")]
    assert hp.hallazgos_nuevos(base, [_h("L9", "RESUMEN!B13")]) == [_h("L9", "RESUMEN!B13")]


def test_la_cifra_oficial_y_calcular_usan_la_misma_funcion():
    assert mi.hallazgos_nuevos is hp.hallazgos_nuevos


def test_sin_previos_conserva_la_numeracion_y_dice_que_filas_traen_algo_nuevo():
    base = [_h("L9", "P!R6"), _h("L5", "RESUMEN!B13")]
    sembrado = [_h("L9", "P!R6"), _h("L5", "RESUMEN!B13", "RESUMEN!B14"), _h("L3", "P!P5")]
    vaciados, previos, con_nuevos = hp.sin_previos(base, sembrado)
    assert [h.origen_ids for h in vaciados] == [(), ("RESUMEN!B14",), ("P!P5",)]
    assert previos == 1
    assert hp.filas_con_nuevos(sembrado, con_nuevos, sin_agrupar=False) == {2, 3}


def test_detectado_por_sobre_una_fila_solo_previa_se_rechaza():
    filas = m.filas_de_hallazgos([_h("L9"), _h("L3", "P!P5")])
    with pytest.raises(ValueError, match="solo trae hallazgos que el libro base ya tenía"):
        m.deteccion([m.Sembrado(1, "P!R6", "t", detectado_por=1)], filas, con_nuevos={2})
    d = m.deteccion([m.Sembrado(1, "APU-01!F9", "t", detectado_por=2)], filas, con_nuevos={2})
    assert d.por_sembrado == {1: 2}


# --- de punta a punta: exportar -> marcar -> calcular ---------------------------------------------

_BASE = Siembra(verificacion={2: Decimal("3")})  # L9 en PRESUPUESTO!R6: un error previo del libro
_SEMBRADO = Siembra(
    verificacion={2: Decimal("3")}, p_guardado={1: Decimal("999")}, procura_dif=Decimal("5")
)
_FECHA = ["--fecha", "2026-10-13"]


@pytest.fixture
def corrida(tmp_path: Path):
    fuera = tmp_path / "medicion"
    fuera.mkdir()
    repo = str(tmp_path / "repo")
    base, sembrado = fuera / "base.xlsx", fuera / "sembrado.xlsx"
    base.write_bytes(construir_libro(APUS_LIMPIOS, _BASE).datos)
    sembrado.write_bytes(construir_libro(APUS_LIMPIOS, _SEMBRADO).datos)
    planilla = fuera / "p1.xlsx"
    assert (
        m.main(["exportar", str(sembrado), "--salida", str(planilla), *_FECHA, "--raiz-repo", repo])
        == 0
    )
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


def _revision_de(libro: Path, fuera: Path, repo: str, respuestas: dict[int, str]) -> Path:
    destino = fuera / f"rev_{libro.stem}.xlsx"
    assert m.main(["revision", str(libro), "--salida", str(destino), "--raiz-repo", repo]) == 0
    _llenar_revision(destino, respuestas)
    return destino


def test_calcular_con_la_revision_del_experto(corrida, capsys):
    fuera, repo, _, sembrado, planilla = corrida
    # Sílice señala las partidas de las filas 5 (P5, APU-01) y 6 (R6); la 7 queda sana. PROCURA!B5
    # y RESUMEN!B10 + PRESUPUESTO!Q10 (fila de total) no son de ninguna partida: 2 filas aparte.
    # Experto: 5 Sí, 6 No, 7 No. po = 2/3; pe = (1·2 + 2·1)/9 = 4/9; κ = (2/9)/(5/9) = 2/5.
    revision = _revision_de(sembrado, fuera, repo, {5: "Sí", 6: "No", 7: "No"})
    _marcar(planilla, {1: "Verdadero"})
    argumentos = ["--libro", str(sembrado), "--revision-experto", str(revision), *_FECHA]
    assert m.main(["calcular", "--planilla", str(planilla), *argumentos]) == 0
    salida = capsys.readouterr().out
    assert "| Kappa de Cohen experto–Sílice por partida" in salida
    assert "0,40" in salida
    assert "Filas de la planilla sin partida (no entran en el kappa): 2" in salida
    assert "Kappa experto–Sílice < 0,4: NO se cumple" in salida


def test_con_recalcular_el_kappa_usa_el_libro_auditado(corrida, capsys):
    fuera, repo, _, sembrado, _ = corrida
    planilla = fuera / "p_recalculada.xlsx"
    motor = _Espia()
    comunes = [*_FECHA, "--recalcular"]
    assert (
        m.main(
            ["exportar", str(sembrado), "--salida", str(planilla), *comunes, "--raiz-repo", repo],
            recalculador=motor,
        )
        == 0
    )
    motor.llamadas.clear()
    revision = _revision_de(sembrado, fuera, repo, {5: "Sí", 6: "No", 7: "No"})
    argumentos = ["--libro", str(sembrado), "--revision-experto", str(revision), *comunes]
    assert m.main(["calcular", "--planilla", str(planilla), *argumentos], recalculador=motor) == 0
    assert motor.llamadas == ["sembrado.xlsx"]
    assert "Kappa experto–Sílice < 0,4: NO se cumple" in capsys.readouterr().out


class _Espia(LibreOfficeFalso):
    def __init__(self) -> None:
        self.llamadas: list[str] = []

    def recalcular(self, datos: bytes, nombre: str) -> bytes:
        self.llamadas.append(nombre)
        return super().recalcular(datos, nombre)


def test_revision_desde_la_linea_de_comandos(corrida):
    fuera, repo, _, sembrado, _ = corrida
    destino = fuera / "rev.xlsx"
    assert m.main(["revision", str(sembrado), "--salida", str(destino), "--raiz-repo", repo]) == 0
    assert mp.leer_revision(destino) == {5: None, 6: None, 7: None}
    instrucciones = [c.value for c in openpyxl.load_workbook(destino)["Instrucciones"]["A"]]
    sha = hashlib.sha256(sembrado.read_bytes()).hexdigest()
    assert f"SHA-256 del libro revisado: {sha}" in instrucciones


def test_calcular_rechaza_la_planilla_de_otro_libro(corrida):
    fuera, repo, base, sembrado, planilla = corrida
    revision = _revision_de(sembrado, fuera, repo, {5: "Sí", 6: "No", 7: "No"})
    with pytest.raises(ValueError, match="La planilla «p1.xlsx» no es de este libro"):
        m.main(
            ["calcular", "--planilla", str(planilla), "--libro", str(base)]
            + ["--revision-experto", str(revision), *_FECHA]
        )


def test_calcular_rechaza_la_revision_de_otro_libro(corrida):
    # Planilla y --libro del sembrado; la revisión del experto se hizo sobre el libro base.
    fuera, repo, base, sembrado, planilla = corrida
    revision = _revision_de(base, fuera, repo, {5: "Sí", 6: "No", 7: "No"})
    with pytest.raises(ValueError, match="La revisión «rev_base.xlsx» no es de este libro"):
        m.main(
            ["calcular", "--planilla", str(planilla), "--libro", str(sembrado)]
            + ["--revision-experto", str(revision), *_FECHA]
        )


def _clave(fuera: Path, repo: str, *sembrados: tuple) -> Path:
    ruta = fuera / "clave.xlsx"
    m.escribir_clave_vacia(ruta, raiz_repo=Path(repo))
    libro = openpyxl.load_workbook(ruta)
    for numero, celda, *manual in sembrados:
        libro["Sembrados"].append([numero, celda, "t", "x", manual[0] if manual else None])
    libro.save(ruta)
    return ruta


def _calcular_con_clave(planilla: Path, clave: Path, sembrado: Path, base: Path) -> int:
    return m.main(
        ["calcular", "--planilla", str(planilla), "--clave", str(clave)]
        + ["--libro", str(sembrado), "--libro-base", str(base), *_FECHA]
    )


def test_falla_sembrada_sobre_un_hallazgo_previo_no_se_acredita(corrida, capsys):
    fuera, repo, base, sembrado, planilla = corrida
    # El sembrado 1 cae en PRESUPUESTO!R6, que el libro base ya señalaba (L9 previo): no cuenta.
    # El sembrado 2 (P.U. guardado en P5) sí lo detecta un hallazgo nuevo. Detección: 1 de 2.
    clave = _clave(fuera, repo, (1, "PRESUPUESTO!R6"), (2, "PRESUPUESTO!P5"))
    _marcar(planilla, {n: "Verdadero" for n in range(1, 7)})
    assert _calcular_con_clave(planilla, clave, sembrado, base) == 0
    salida = capsys.readouterr().out
    assert "| Detección de errores sembrados (señalado por Sílice) | 1 de 2" in salida
    assert "| Detección, señalado y confirmado verdadero | 1 de 2" in salida
    assert "[9,5 %; 90,5 %]" in salida  # Wilson de 1 de 2, a mano
    assert "Hallazgos previos del libro descontados: 1" in salida


def test_la_columna_manual_no_acredita_una_fila_solo_previa(corrida):
    # La fila 4 de la planilla es el L9 de R6, que el libro base ya tenía.
    fuera, repo, base, sembrado, planilla = corrida
    clave = _clave(fuera, repo, (1, "APU-02!F12", 4))
    with pytest.raises(ValueError, match="hallazgo 4, y esa fila solo trae hallazgos"):
        _calcular_con_clave(planilla, clave, sembrado, base)


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
        _calcular_con_clave(planilla, clave, sembrado, base)
