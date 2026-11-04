"""Plan vial, Tarea 10: conciliacion entre APU, presupuesto, tramos y costo propio. FICTICIO.

Via de prueba: T1, 0 a 1 km, 7 m de ancho, carpeta de 0,05 m a 2,4 t/m3, transporte desde 10 km.
Oraculos a mano: area 1.000 x 7 = 7.000 m2; mezcla 7.000 x 0,05 x 2,4 = 840 t; transporte
840 x 10 = 8.400 t·km. Precios (parametros por defecto: administracion 15 % y utilidad 10 % en
cascada, factor 1,15 x 1,10 = 1,265): carpeta con material de 10,00 -> 12,65; mezcla con el
`MZP-MZ-1` a 200,00 -> 253,00; transporte con material de 2,00 -> 2,53.

El caso coherente no da hallazgos; cada prueba cambia UN valor y espera exactamente su hallazgo.
Antes de escribir CV1 se comprobo que ninguna regla R1 a R12 compara el precio unitario del
renglon con el recalculado de su APU (R1 y R5 solo lo usan como `impacto`).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Tramo
from aplicacion import conciliacion
from aplicacion.conciliacion import conciliar
from aplicacion.costo_propio import (
    CalculoGuardado,
    calcular_periodo,
    descripcion_de_costo_propio,
    publicar_calculo,
)
from core.catalog import Catalogo
from core.contracts import Dominio, ItemComputo, OrigenTipo
from core.contracts.apu import ComposicionAPU, LineaMaterial, ParametrosCosto, ResultadoAPU
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Severidad
from tests.fixtures import costo_propio as cp

D = Decimal
CAPA1 = "tramo:T1:capa:1"
T1 = Tramo("T1", D("0"), D("1"), D("7"), (Capa("carpeta", D("0.05"), D("2.4"), None),), (), D("10"))
CARPETA, MEZCLA, TRANSPORTE = (
    PARTIDAS_VIALES[c][0] for c in ("carpeta", "carpeta_mezcla", "transporte_mezcla")
)
FRESADO = PARTIDAS_VIALES["fresado"][0]
PARAMETROS = ParametrosCosto()
MZP = "MZP-MZ-1"
LINEA_MZP = "Costo propio de mezcla MZ-1"

#: (precio del material, precio unitario con la cascada 1,15 x 1,10), a mano.
PRECIOS = {CARPETA: ("10.00", "12.65"), MEZCLA: ("200.00", "253.00"), TRANSPORTE: ("2.00", "2.53")}


def _composicion(item: ItemComputo, precio: str) -> ComposicionAPU:
    descripcion = LINEA_MZP if item.codigo_partida == MEZCLA else "Material"
    linea = LineaMaterial(descripcion, item.unidad, D("1"), D(precio))
    return ComposicionAPU(
        item.codigo_partida, item.descripcion, item.unidad, D("10"), materiales=(linea,)
    )


def _resultado(material: str, pu: str) -> ResultadoAPU:
    cd = D(material)
    return ResultadoAPU(cd, D("0"), D("0"), cd, cd * D("1.15"), D(pu))


DERIVADOS = derivar_tramos([T1])
COMPOSICIONES = {i.codigo_partida: _composicion(i, PRECIOS[i.codigo_partida][0]) for i in DERIVADOS}
MZP_10 = CalculoGuardado(5, "2026-10", "Bs", {"MZ-1": D("200.00")}, "huella")


def _presupuesto(items=DERIVADOS, *, pu=None, moneda="Bs") -> Presupuesto:
    pu = pu or {}
    partidas = []
    for item in items:
        material, normal = PRECIOS.get(item.codigo_partida, ("1.00", "1.265"))
        partidas.append(
            PartidaPresupuestada(
                item,
                COMPOSICIONES.get(item.codigo_partida) or _composicion(item, material),
                _resultado(material, pu.get(item.codigo_partida, normal)),
            )
        )
    return Presupuesto("VIAL-TEST", date(2026, 10, 31), moneda, tuple(partidas))


def _conciliar(presupuesto=None, *, viales=DERIVADOS, costos=None, usados=None):
    return conciliar(
        presupuesto or _presupuesto(),
        COMPOSICIONES,
        PARAMETROS,
        items_viales=viales,
        costos_propios={MZP: MZP_10} if costos is None else costos,
        calculos_usados=usados,
    )


def _solo(hallazgos, regla: str):
    assert [h.regla for h in hallazgos] == [regla], hallazgos
    return hallazgos[0]


def _cambiar(codigo: str, **cambios) -> Presupuesto:
    return _presupuesto(
        [replace(i, **cambios) if i.codigo_partida == codigo else i for i in DERIVADOS]
    )


# --- el caso coherente ----------------------------------------------------------------------------


def test_los_derivados_son_los_de_la_mano():
    assert [(i.codigo_partida, i.cantidad) for i in DERIVADOS] == [
        (CARPETA, D("7000")),
        (MEZCLA, D("840.000")),
        (TRANSPORTE, D("8400.000")),
    ]


def test_caso_coherente_no_da_hallazgos():
    assert _conciliar() == []


# --- CV1 ------------------------------------------------------------------------------------------


def test_cv1_precio_distinto_del_recalculado():
    h = _solo(_conciliar(_presupuesto(pu={CARPETA: "12.70"})), "CV1")
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == ((CAPA1,), D("12.70"), D("12.65"))
    assert h.severidad is Severidad.ERROR
    assert "12,70" in h.descripcion and "12,65" in h.descripcion and CARPETA in h.descripcion


def test_cv1_en_la_frontera_de_un_centavo():
    assert _conciliar(_presupuesto(pu={CARPETA: "12.66"})) == []
    assert _conciliar(_presupuesto(pu={CARPETA: "12.64"})) == []
    assert _solo(_conciliar(_presupuesto(pu={CARPETA: "12.661"})), "CV1").valor_observado == D(
        "12.661"
    )


def test_cv1_sin_composicion_no_se_recalcula():
    h = conciliar(
        _presupuesto(pu={CARPETA: "99"}),
        {k: v for k, v in COMPOSICIONES.items() if k != CARPETA},
        PARAMETROS,
        items_viales=DERIVADOS,
        costos_propios={MZP: MZP_10},
    )
    assert h == []


# --- CV2 ------------------------------------------------------------------------------------------


def test_cv2_cantidad_distinta_de_la_suma_de_los_tramos():
    h = _solo(_conciliar(_cambiar(MEZCLA, cantidad=D("800"))), "CV2")
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == ((CAPA1,), D("800"), D("840.000"))
    assert h.severidad is Severidad.ERROR
    assert "800 t" in h.descripcion and "840 t" in h.descripcion and MEZCLA in h.descripcion


def test_cv2_dentro_de_la_tolerancia_de_una_milesima():
    assert _conciliar(_cambiar(MEZCLA, cantidad=D("840.84"))) == []
    assert _solo(_conciliar(_cambiar(MEZCLA, cantidad=D("840.85"))), "CV2")


def test_cv2_suma_los_renglones_de_la_misma_partida_y_dos_tramos():
    t2 = Tramo(
        "T2", D("1"), D("2"), D("7"), (Capa("carpeta", D("0.05"), D("2.4"), None),), (), D("10")
    )
    viales = derivar_tramos([T1, t2])
    presupuesto = _presupuesto(
        [i for i in viales if i.origen_id.startswith("tramo:T1")]
        + [i for i in viales if i.origen_id.startswith("tramo:T2")]
    )
    assert _conciliar(presupuesto, viales=viales) == []
    sin_mezcla_t2 = [i for i in viales if i.codigo_partida != MEZCLA or "T1" in i.origen_id]
    h = _solo(_conciliar(_presupuesto(sin_mezcla_t2), viales=viales), "CV2")
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == (
        ("tramo:T1:capa:1", "tramo:T2:capa:1"),
        D("840.000"),
        D("1680.000"),
    )


def test_cv2_partida_derivada_ausente_del_presupuesto():
    sin = [i for i in DERIVADOS if i.codigo_partida != TRANSPORTE]
    h = _solo(_conciliar(_presupuesto(sin)), "CV2")
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == (
        (CAPA1,),
        D("0"),
        D("8400.000"),
    )
    assert h.severidad is Severidad.ERROR
    assert "falta en el presupuesto" in h.descripcion and TRANSPORTE in h.descripcion


def test_cv2_partida_vial_del_presupuesto_sin_tramos_que_la_respalden():
    extra = ItemComputo(
        FRESADO, "Fresado", "m3", D("50"), "MAN-1", OrigenTipo.MANUAL, Dominio.CIVIL
    )
    h = _solo(_conciliar(_presupuesto([*DERIVADOS, extra])), "CV2")
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == (("MAN-1",), D("50"), D("0"))
    assert h.severidad is Severidad.ADVERTENCIA
    assert "ningún tramo" in h.descripcion


def test_cv2_sin_tramos_no_hay_nada_que_conciliar():
    extra = ItemComputo(
        FRESADO, "Fresado", "m3", D("50"), "MAN-1", OrigenTipo.MANUAL, Dominio.CIVIL
    )
    assert _conciliar(_presupuesto([*DERIVADOS, extra]), viales=()) == []


# --- CV3 ------------------------------------------------------------------------------------------


def _costos(precio: str, moneda: str = "Bs") -> dict[str, CalculoGuardado]:
    return {MZP: CalculoGuardado(8, "2026-11", moneda, {"MZ-1": D(precio)}, "huella")}


def test_cv3_precio_usado_distinto_del_ultimo_publicado_con_el_numero_de_ambos():
    h = _solo(_conciliar(costos=_costos("210.00"), usados={MZP: 5}), "CV3")
    assert (h.origen_ids, h.valor_observado, h.valor_esperado) == (
        (CAPA1,),
        D("200.00"),
        D("210.00"),
    )
    assert h.severidad is Severidad.ADVERTENCIA
    assert "200,00" in h.descripcion and "210,00" in h.descripcion
    assert "cálculo n.º 5" in h.descripcion and "cálculo n.º 8" in h.descripcion
    assert MZP in h.descripcion


def test_cv3_sin_saber_de_que_calculo_viene_el_precio_usado():
    h = _solo(_conciliar(costos=_costos("210.00")), "CV3")
    assert "ningún cálculo publicado conocido" in h.descripcion and "n.º 8" in h.descripcion


def test_cv3_en_la_frontera_de_un_centavo():
    assert _conciliar(costos=_costos("200.01")) == []
    assert _conciliar(costos=_costos("199.99")) == []
    assert _solo(_conciliar(costos=_costos("200.02")), "CV3")


def test_cv3_en_otra_moneda_no_se_compara_y_lo_dice():
    h = _solo(_conciliar(costos=_costos("5.00", "USD")), "CV3")
    assert h.severidad is Severidad.INFO
    assert h.valor_observado is None and h.valor_esperado is None
    assert "regla no evaluable" in h.descripcion and "USD" in h.descripcion


def test_cv3_un_insumo_propio_sin_publicar_o_una_linea_ajena_no_dan_hallazgo():
    assert _conciliar(costos={}) == []
    assert (
        _conciliar(costos={"AGP-OTRO": CalculoGuardado(1, "2026-10", "Bs", {"OTRO": D("9")}, "h")})
        == []
    )


# --- helpers del costo propio ---------------------------------------------------------------------


def test_la_descripcion_del_insumo_propio_es_la_que_publica_el_costo_propio():
    assert descripcion_de_costo_propio("AGP-AGR-12") == "Costo propio de agregado AGR-12"
    assert descripcion_de_costo_propio("MZP-MZ-1") == LINEA_MZP
    with pytest.raises(ValueError, match="AGP-"):
        descripcion_de_costo_propio("CA-30")


@pytest.mark.parametrize(
    ("fuente", "numero"),
    [
        ("Producción, período 2026-11, cálculo n.º 7", 7),
        ("Producción, período 2026-11, cálculo n.º 12; publicado por admin", 12),
        ("Lista de la empresa 2026", None),
        ("", None),
    ],
)
def test_el_numero_de_calculo_sale_de_la_fuente_del_precio(fuente, numero):
    assert conciliacion.numero_de_calculo(fuente) == numero


@pytest.fixture
def ins() -> Iterator[Session]:
    with cp.instalacion_en_memoria() as sesion:
        yield sesion


@pytest.fixture
def caso(tmp_path: Path) -> Iterator[Session]:
    with cp.carpeta_del_caso(tmp_path) as sesion:
        yield sesion


def _publicar(ins: Session, caso: Session, calculo: CalculoGuardado) -> None:
    publicar_calculo(
        caso,
        calculo,
        sesion_ins=ins,
        nombre_del_caso="carpeta.db",
        base=Catalogo(caso).lista_vigente(date(2026, 11, 30)),
        empresa_nombre="Constructora Ejemplo, C.A.",
        empresa_rif="J-00000000-0",
        usuario="admin",
        ahora=cp.AHORA,
    )


def _calcular(ins: Session, caso: Session) -> CalculoGuardado:
    return calcular_periodo(ins, caso, cp.PERIODO, "USD", usuario="ana", ahora=cp.AHORA)


def test_los_costos_propios_son_los_del_ultimo_calculo_publicado(ins, caso):
    cp.noviembre_usd(ins, caso)
    assert conciliacion.costos_propios_publicados(ins) == {}
    primero, segundo, tercero = (_calcular(ins, caso) for _ in range(3))
    assert conciliacion.costos_propios_publicados(ins) == {}  # calcular no es publicar
    _publicar(ins, caso, primero)
    _publicar(ins, caso, segundo)
    # el tercero no se publica: manda el segundo (id mayor entre los publicados)
    publicados = conciliacion.costos_propios_publicados(ins)
    assert sorted(publicados) == ["AGP-AGR-12", "AGP-AGR-34", "MZP-MZ-1"]
    assert {c.id for c in publicados.values()} == {segundo.id}
    assert publicados["MZP-MZ-1"].por_tonelada["MZ-1"] == D("50.70")
    assert tercero.id == 3
