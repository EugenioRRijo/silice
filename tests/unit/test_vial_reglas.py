"""Plan vial, Tarea 9: reglas viales VR1 a VR7 (`adapters/vial/reglas.py`). Datos FICTICIOS.

Vía de prueba: T1, 0 a 1 km, 7 m de ancho, carpeta de 0,05 m a 2,4 t/m3 y una línea continua,
transporte desde 10 km. Oráculos a mano: área 1.000 x 7 = 7.000 m2; carpeta 7.000 x 0,05 x 2,4 =
840 t (tolerancia 0,5 % = 4,2 t); transporte 840 x 10 = 8.400 t·km (tolerancia 42); línea de 1 km.
El presupuesto del caso coherente es la propia derivación del tramo: no da ningún hallazgo. Cada
prueba cambia UN valor y espera exactamente su hallazgo.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Demarcacion, Tramo
from adapters.vial.reglas import ReglasViales, auditar_vial
from core.contracts import Dominio, ItemComputo, OrigenTipo
from core.contracts.apu import ComposicionAPU, ResultadoAPU
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Severidad

D = Decimal
CAPA1 = "tramo:T1:capa:1"
LINEA1 = "tramo:T1:demarcacion:1"


def _tramo(*capas: Capa, id: str = "T1", ini: str = "0", fin: str = "1", linea: bool = True):
    return Tramo(
        id,
        D(ini),
        D(fin),
        D("7"),
        capas,
        (Demarcacion("continua", 1),) if linea else (),
        D("10"),
    )


CARPETA = Capa("carpeta", D("0.05"), D("2.4"), None)
T1 = _tramo(CARPETA)


def _presupuesto(items: list[ItemComputo]) -> Presupuesto:
    cero = D("0")
    partidas = []
    for item in items:
        apu = ComposicionAPU(item.codigo_partida, item.descripcion, item.unidad, D("1"))
        resultado = ResultadoAPU(cero, cero, cero, cero, cero, D("1"))
        partidas.append(PartidaPresupuestada(item, apu, resultado))
    return Presupuesto("VIV-TEST", date(2026, 10, 31), "Bs", tuple(partidas))


def _cambiar(tramos, clave: str, origen: str = CAPA1, **cambios) -> Presupuesto:
    codigo = PARTIDAS_VIALES[clave][0]
    items = [
        replace(i, **cambios) if (i.codigo_partida, i.origen_id) == (codigo, origen) else i
        for i in derivar_tramos(tramos)
    ]
    return _presupuesto(items)


def _pintura(cantidad: str, ancho: str | None = None) -> ItemComputo:
    espec = {} if ancho is None else {"_ancho_linea_cm": ancho}
    return ItemComputo(
        "PINT-1",
        "Pintura de tráfico",
        "l",
        D(cantidad),
        LINEA1,
        OrigenTipo.MANUAL,
        Dominio.CIVIL,
        especificaciones=espec,
    )


def _con_pintura(cantidad: str, ancho: str | None = None) -> Presupuesto:
    return _presupuesto([*derivar_tramos([T1]), _pintura(cantidad, ancho)])


def _solo(hallazgos, regla: str):
    assert [h.regla for h in hallazgos] == [regla], hallazgos
    return hallazgos[0]


# --- caso coherente -------------------------------------------------------------------------------


def test_el_caso_coherente_no_da_hallazgos():
    assert auditar_vial([T1], _presupuesto(derivar_tramos([T1]))) == []


def test_regla_viales_es_la_misma_auditoria():
    presupuesto = _cambiar([T1], "carpeta_mezcla", cantidad=D("900"))
    esperado = auditar_vial([T1], presupuesto)
    assert ReglasViales([T1]).evaluar(presupuesto) == esperado
    assert esperado


# --- VR1 ------------------------------------------------------------------------------------------


def test_vr1_dentro_de_la_tolerancia():
    for toneladas in ("844.2", "835.8", "840"):
        assert auditar_vial([T1], _cambiar([T1], "carpeta_mezcla", cantidad=D(toneladas))) == []


def test_vr1_justo_fuera_por_arriba():
    h = _solo(auditar_vial([T1], _cambiar([T1], "carpeta_mezcla", cantidad=D("844.21"))), "VR1")
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == ((CAPA1,), D("844.21"), D("840"))
    assert h.severidad is Severidad.ERROR
    assert "844,21 t" in h.descripcion and "840 t" in h.descripcion


def test_vr1_justo_fuera_por_abajo():
    h = _solo(auditar_vial([T1], _cambiar([T1], "carpeta_mezcla", cantidad=D("835.79"))), "VR1")
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == ((CAPA1,), D("835.79"), D("840"))


# --- VR2 ------------------------------------------------------------------------------------------


def _con_asfalto(texto: str) -> Presupuesto:
    return _cambiar([T1], "carpeta_mezcla", especificaciones={"_porcentaje_asfalto": texto})


def test_vr2_dentro_de_mas_menos_medio_punto():
    for texto in ("6,0", "5.0", "5,5"):
        assert auditar_vial([T1], _con_asfalto(texto), formula_asfalto_pct=D("5.5")) == []


def test_vr2_justo_fuera():
    for texto, observado in (("6,01", D("6.01")), ("4.99", D("4.99"))):
        h = _solo(auditar_vial([T1], _con_asfalto(texto), formula_asfalto_pct=D("5.5")), "VR2")
        assert (h.origen_ids, h.valor_observado, h.valor_esperado) == (
            (CAPA1,),
            observado,
            D("5.5"),
        )
        assert h.severidad is Severidad.ADVERTENCIA
        assert "5,5 %" in h.descripcion


def test_vr2_sin_formula_no_se_evalua():
    assert auditar_vial([T1], _con_asfalto("9")) == []


def test_vr2_un_texto_que_no_es_numero_se_avisa():
    h = _solo(auditar_vial([T1], _con_asfalto("mucho"), formula_asfalto_pct=D("5.5")), "VR2")
    assert h.origen_ids == (CAPA1,) and h.valor_observado is None


# --- VR3 ------------------------------------------------------------------------------------------
# residual = dosis x 1.000 g/kg x 1,0 kg/l x 0,60


def _vr3(tipo: str, dosis: str):
    tramos = [_tramo(Capa(tipo, None, None, D(dosis)), linea=False)]
    return auditar_vial(tramos, _presupuesto(derivar_tramos(tramos)))


def test_vr3_imprimacion_dentro():
    assert _vr3("imprimacion", "0.84") == []  # 504 g/m2
    assert _vr3("imprimacion", "3.33") == []  # 1.998 g/m2


def test_vr3_imprimacion_bajo_el_minimo():
    h = _solo(_vr3("imprimacion", "0.83"), "VR3")  # 498 g/m2
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == ((CAPA1,), D("498"), D("500"))
    assert "498 g/m²" in h.descripcion and "mínimo" in h.descripcion


def test_vr3_imprimacion_sobre_el_maximo():
    h = _solo(_vr3("imprimacion", "3.34"), "VR3")  # 2.004 g/m2
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == ((CAPA1,), D("2004"), D("2000"))
    assert "máximo" in h.descripcion


def test_vr3_riego_de_adherencia():
    assert _vr3("riego_adherencia", "0.34") == []  # 204 g/m2
    h = _solo(_vr3("riego_adherencia", "0.33"), "VR3")  # 198 g/m2
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == ((CAPA1,), D("198"), D("200"))
    assert h.severidad is Severidad.ADVERTENCIA


def test_vr3_el_riego_de_adherencia_no_tiene_maximo():
    assert _vr3("riego_adherencia", "5") == []


# --- VR4 ------------------------------------------------------------------------------------------


def test_vr4_dentro():
    for t_km in ("8442", "8358", "8400"):
        assert auditar_vial([T1], _cambiar([T1], "transporte_mezcla", cantidad=D(t_km))) == []


def test_vr4_justo_fuera():
    for t_km in ("8442.01", "8357.99"):
        h = _solo(auditar_vial([T1], _cambiar([T1], "transporte_mezcla", cantidad=D(t_km))), "VR4")
        assert (h.origen_ids, h.valor_observado, h.valor_esperado) == (
            (CAPA1,),
            D(t_km),
            D("8400"),
        )
        assert h.severidad is Severidad.ERROR


# --- VR5 ------------------------------------------------------------------------------------------
# 1 km de línea continua, una línea; sin ancho declarado se supone 10 cm.


def test_vr5_dentro_del_rango():
    for litros in ("29", "44", "36.5"):
        assert auditar_vial([T1], _con_pintura(litros)) == []


def test_vr5_justo_fuera():
    h = _solo(auditar_vial([T1], _con_pintura("28.99")), "VR5")
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == ((LINEA1,), D("28.99"), D("29"))
    h = _solo(auditar_vial([T1], _con_pintura("44.01")), "VR5")
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == ((LINEA1,), D("44.01"), D("44"))
    assert h.severidad is Severidad.ADVERTENCIA


def test_vr5_es_proporcional_al_ancho_de_la_linea():
    # 20 cm: el rango pasa a 58 a 88 l por km
    assert auditar_vial([T1], _con_pintura("58", "20")) == []
    assert auditar_vial([T1], _con_pintura("88", "20")) == []
    h = _solo(auditar_vial([T1], _con_pintura("56", "20")), "VR5")  # 28 l por km de 10 cm
    assert (h.valor_observado, h.valor_esperado) == (D("28"), D("29"))


def test_vr5_discontinua_mide_el_largo_pintado():
    t = replace(T1, demarcacion=(Demarcacion("discontinua", 1),))  # 375 m pintados
    base = derivar_tramos([t])
    dentro = _presupuesto([*base, _pintura("12")])  # 32 l por km
    assert auditar_vial([t], dentro) == []
    fuera = _presupuesto([*base, _pintura("10")])  # 26,67 l por km
    h = _solo(auditar_vial([t], fuera), "VR5")
    assert h.valor_esperado == D("29") and round(h.valor_observado, 2) == D("26.67")


def test_vr5_un_ancho_ilegible_se_avisa():
    h = _solo(auditar_vial([T1], _con_pintura("36", "ancho")), "VR5")
    assert h.origen_ids == (LINEA1,)


# --- VR6 ------------------------------------------------------------------------------------------


def _vr6(*tramos: tuple[str, str, str]):
    via = [_tramo(id=i, ini=a, fin=b, linea=False) for i, a, b in tramos]
    return auditar_vial(via, _presupuesto([]))


def test_vr6_tramos_contiguos_sin_hallazgo():
    assert _vr6(("T1", "0", "1"), ("T2", "1", "2")) == []


def test_vr6_solape():
    h = _solo(_vr6(("T1", "0", "1"), ("T2", "0.9", "2")), "VR6")
    assert "solape de 0,1 km entre T1 y T2" in h.descripcion
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == (
        ("tramo:T1", "tramo:T2"),
        D("0.1"),
        D("0"),
    )
    assert h.severidad is Severidad.ERROR


def test_vr6_hueco():
    h = _solo(_vr6(("T1", "0", "1"), ("T2", "1.2", "2")), "VR6")
    assert "hueco de 0,2 km entre T1 y T2" in h.descripcion
    assert (h.origen_ids, h.valor_observado) == (("tramo:T1", "tramo:T2"), D("0.2"))
    assert h.severidad is Severidad.ADVERTENCIA


def test_vr6_no_depende_del_orden_de_entrada():
    h = _solo(_vr6(("T2", "0.9", "2"), ("T1", "0", "1")), "VR6")
    assert "solape de 0,1 km entre T1 y T2" in h.descripcion


def test_vr6_un_tramo_dentro_de_otro_solapa_todo_su_largo_y_no_crea_hueco():
    h = _solo(_vr6(("T1", "0", "3"), ("T2", "1", "2"), ("T3", "3", "4")), "VR6")
    assert "solape de 1 km entre T1 y T2" in h.descripcion


# --- VR7 ------------------------------------------------------------------------------------------


def test_vr7_unidad_equivalente_no_avisa():
    assert auditar_vial([T1], _cambiar([T1], "carpeta", unidad="m²")) == []


def test_vr7_unidad_incompatible():
    h = _solo(auditar_vial([T1], _cambiar([T1], "carpeta", unidad="m3")), "VR7")
    assert h.origen_ids == (CAPA1,) and h.severidad is Severidad.ERROR
    assert "va en m2" in h.descripcion and "en m3" in h.descripcion


def test_vr7_partida_que_la_capa_no_produce():
    codigo_base = PARTIDAS_VIALES["base_granular"][0]
    presupuesto = _cambiar([T1], "carpeta", codigo_partida=codigo_base, unidad="m3")
    h = _solo(auditar_vial([T1], presupuesto), "VR7")
    assert h.origen_ids == (CAPA1,) and "no la produce" in h.descripcion


def test_vr7_ignora_las_partidas_que_no_son_viales():
    assert auditar_vial([T1], _con_pintura("36")) == []
