"""R10 (limites de la especialidad) del espacio (spec §8.2, tarea 2.3).

Tres condiciones: pendiente minima del drenaje, 90 m por enlace de datos y puntos por circuito. Cada
una se siembra sola sobre un espacio limpio y se exige UN hallazgo exacto; los valores frontera son
exactos (90,00 m pasa y 90,01 m falla; el maximo de puntos pasa y uno mas falla; la pendiente minima
pasa y una menos falla). Severidad: ERROR si el limite tiene fuente verificada, ADVERTENCIA si es un
supuesto declarado (hoy los tres lo son).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from adapters.espacio import (
    Ambiente,
    Circuito,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    ModoRecorrido,
    OrigenMedida,
    Punto,
    Recorrido,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoOrigen,
    TipoPunto,
    Tramo,
)
from adapters.espacio.especialidades import Constante
from adapters.espacio.reglas import Limites, LimitesDeEspecialidad
from core.contracts import Hallazgo, Severidad
from core.contracts.presupuesto import Presupuesto
from tests.fixtures.espacio_of001 import espacio_of001

D = Decimal
VACIO = Presupuesto(codigo="X", fecha=date(2026, 1, 1), moneda="USD", partidas=())
SUPUESTO = "supuesto declarado"
VERIFICADA = "Gaceta Oficial N.º 4.044 Extraordinario (1988)"


def r10(espacio: Espacio, limites: Limites | None = None) -> list[Hallazgo]:
    regla = (
        LimitesDeEspecialidad(espacio)
        if limites is None
        else LimitesDeEspecialidad(espacio, limites)
    )
    return regla.evaluar(VACIO)


def hallazgo(severidad, origenes, mensaje, **extra) -> Hallazgo:
    return Hallazgo(
        regla="R10", severidad=severidad, descripcion=mensaje, origen_ids=tuple(origenes), **extra
    )


def _c(x: str, y: str, z: str) -> Coord:
    return Coord(D(x), D(y), D(z))


ORIGEN = OrigenMedida(id="O", tipo=TipoOrigen.SUPUESTO, referencia={"motivo": "prueba"})


def _sala(largo: str = "100") -> Ambiente:
    return Ambiente(
        id="A",
        nombre="Sala",
        x0=D("0"),
        y0=D("0"),
        largo=D(largo),
        ancho=D("100"),
        alto=D("2.5"),
        origen_id="O",
    )


def _fuente(id_: str, esp: Especialidad, tipo: TipoFuente, pos: Coord) -> Fuente:
    return Fuente(id=id_, especialidad=esp, tipo=tipo, ambiente_id="A", posicion=pos, origen_id="O")


def _punto(id_: str, esp: Especialidad, tipo: TipoPunto, pos: Coord, **extra) -> Punto:
    datos = dict(
        id=id_,
        nombre=id_,
        especialidad=esp,
        tipo=tipo,
        ambiente_id="A",
        superficie=SuperficiePunto.PARED,
        posicion=pos,
        origen_id="O",
    )
    datos.update(extra)
    return Punto(**datos)


def _tramo(orden: int, a: tuple, b: tuple, pendiente: str | None = None) -> Tramo:
    return Tramo(
        orden=orden,
        superficie=SuperficieTramo.PISO,
        vertices=(_c(*a), _c(*b)),
        pendiente=None if pendiente is None else D(pendiente),
    )


# --- contrato -----------------------------------------------------------------------------


def test_espacio_vacio_no_da_hallazgos_fr1() -> None:
    assert r10(Espacio()) == []


def test_of001_limpia_cumple_los_tres_limites() -> None:
    assert r10(espacio_of001()) == []


# --- pendiente minima del drenaje ---------------------------------------------------------------


def _drenaje(pendientes: tuple[str | None, ...]) -> Espacio:
    """Un colector y un desague con un recorrido declarado de un tramo por cada pendiente."""
    tramos = tuple(
        _tramo(i, (str(i - 1), "0", "0"), (str(i), "0", "0"), p)
        for i, p in enumerate(pendientes, start=1)
    )
    return Espacio(
        origenes=(ORIGEN,),
        ambientes=(_sala(),),
        fuentes=(
            _fuente("FD", Especialidad.AGUA, TipoFuente.COLECTOR_DRENAJE, _c("10", "0", "0")),
        ),
        puntos=(
            _punto(
                "D",
                Especialidad.AGUA,
                TipoPunto.DRENAJE,
                _c("0", "0", "0"),
                fuente_id="FD",
                superficie=SuperficiePunto.PISO,
            ),
        ),
        recorridos=(
            Recorrido(id="R-D", punto_id="D", modo=ModoRecorrido.DECLARADO, tramos=tramos),
        ),
    )


def test_la_pendiente_minima_pasa_y_una_menos_falla() -> None:
    assert r10(_drenaje(("0.01",))) == []  # exactamente la minima
    assert r10(_drenaje(("0.02",))) == []
    assert r10(_drenaje(("0.009",))) == [
        hallazgo(
            Severidad.ADVERTENCIA,
            ("esp_recorridos:R-D", "esp_puntos:D"),
            "recorrido R-D: pendiente 0.009 del tramo 1 menor que la minima 0.01 del drenaje "
            "(limite: supuesto declarado)",
            valor_observado=D("0.009"),
            valor_esperado=D("0.01"),
        )
    ]


def test_un_tramo_sin_pendiente_declarada_no_se_evalua() -> None:
    """La propuesta de §6.4 no trae pendiente numerica: evaluarla daria ruido en todo drenaje."""
    assert r10(_drenaje((None,))) == []
    assert r10(_drenaje((None, "0.02"))) == []


def test_solo_el_tramo_malo_da_hallazgo() -> None:
    hallazgos = r10(_drenaje(("0.02", "0.005", "0.01")))
    assert len(hallazgos) == 1
    assert "del tramo 2" in hallazgos[0].descripcion


def test_la_pendiente_negativa_es_menor_que_la_minima() -> None:
    assert len(r10(_drenaje(("-0.01",)))) == 1  # sube en vez de bajar hacia el colector


def test_una_pendiente_fuera_del_drenaje_no_es_de_r10() -> None:
    base = _drenaje(("0.001",))
    agua = replace(
        base,
        puntos=tuple(
            replace(p, tipo=TipoPunto.AGUA_FRIA, especialidad=Especialidad.AGUA)
            for p in base.puntos
        ),
    )
    assert r10(agua) == []


# --- enlace de datos --------------------------------------------------------------------------


def _enlace(x: str, declarado: str | None = None) -> Espacio:
    """Un rack en el origen y un punto de datos a `x` m en x: el recorrido propuesto mide
    2,5 + x + 0 + 2,5 (sube, cruza, baja) y el enlace suma 2,0 + 0,5 de holguras."""
    puntos = (
        _punto(
            "PD",
            Especialidad.DATOS,
            TipoPunto.DATOS,
            _c(x, "0", "0"),
            fuente_id="RK",
        ),
    )
    recorridos = ()
    if declarado is not None:
        tramo = Tramo(
            orden=1,
            superficie=SuperficieTramo.TECHO,
            vertices=(_c("0", "0", "0"), _c(declarado, "0", "0")),
        )
        recorridos = (
            Recorrido(id="R-PD", punto_id="PD", modo=ModoRecorrido.DECLARADO, tramos=(tramo,)),
        )
    return Espacio(
        origenes=(ORIGEN,),
        ambientes=(_sala(largo="200"),),
        fuentes=(_fuente("RK", Especialidad.DATOS, TipoFuente.RACK, _c("0", "0", "0")),),
        puntos=puntos,
        recorridos=recorridos,
    )


def test_el_enlace_de_90_00_pasa_y_el_de_90_01_falla() -> None:
    assert r10(_enlace("82.5")) == []  # 2,5 + 82,5 + 2,5 + 2,5 de holguras = 90,00
    assert r10(_enlace("82.51")) == [
        hallazgo(
            Severidad.ADVERTENCIA,
            ("esp_puntos:PD",),
            "punto PD: enlace de 90.01 m mayor que el maximo de 90 m "
            "(recorrido mas holguras; limite: supuesto declarado)",
            valor_observado=D("90.01"),
            valor_esperado=D("90"),
        )
    ]


def test_el_enlace_de_un_recorrido_declarado_tambien_cuenta() -> None:
    assert r10(_enlace("1", declarado="87.5")) == []  # 87,5 + 2,5 = 90,00
    hallazgos = r10(_enlace("1", declarado="87.51"))
    assert [h.valor_observado for h in hallazgos] == [D("90.01")]


def test_el_enlace_incluye_las_holguras_pero_no_la_reserva() -> None:
    """Un recorrido de 90,00 m ya falla (con las holguras mide 92,5); la reserva de compra del
    10 % no entra: 87,5 m x 1,10 pasaria de 90 y no debe fallar."""
    assert len(r10(_enlace("1", declarado="90"))) == 1
    assert r10(_enlace("1", declarado="87.5")) == []


def test_un_punto_de_datos_sin_recorrido_no_tiene_enlace_que_comparar() -> None:
    espacio = _enlace("500")
    sin_fuente = replace(espacio, puntos=tuple(replace(p, fuente_id=None) for p in espacio.puntos))
    assert r10(sin_fuente) == []


def test_solo_los_puntos_de_datos_tienen_enlace() -> None:
    espacio = _enlace("500")
    otro = replace(
        espacio,
        puntos=tuple(
            replace(p, especialidad=Especialidad.AGUA, tipo=TipoPunto.AGUA_FRIA)
            for p in espacio.puntos
        ),
    )
    assert r10(otro) == []


# --- puntos por circuito ------------------------------------------------------------------------


def _circuito(n_puntos: int, maximo: int, en_orden: bool = False) -> Espacio:
    ids = [f"T{i}" for i in range(1, n_puntos + 1)]
    puntos = tuple(
        _punto(
            i,
            Especialidad.ELECTRICIDAD,
            TipoPunto.TOMACORRIENTE,
            _c(str(k), "1", "0.3"),
            circuito_id=None if en_orden else "C1",
        )
        for k, i in enumerate(ids, start=1)
    )
    return Espacio(
        origenes=(ORIGEN,),
        ambientes=(_sala(),),
        fuentes=(_fuente("TAB", Especialidad.ELECTRICIDAD, TipoFuente.TABLERO, _c("0", "0", "1")),),
        circuitos=(
            Circuito(
                id="C1",
                tablero="TAB",
                numero=1,
                conductores=(1, 1, 1),
                calibre="12 AWG",
                puntos_maximos=maximo,
                orden=tuple(ids) if en_orden else (),
            ),
        ),
        puntos=puntos,
    )


def test_el_maximo_de_puntos_pasa_y_uno_mas_falla() -> None:
    assert r10(_circuito(3, maximo=3)) == []
    assert r10(_circuito(2, maximo=3)) == []
    espacio = _circuito(4, maximo=3)
    assert r10(espacio) == [
        hallazgo(
            Severidad.ADVERTENCIA,
            (
                "esp_circuitos:C1",
                "esp_puntos:T1",
                "esp_puntos:T2",
                "esp_puntos:T3",
                "esp_puntos:T4",
            ),
            "circuito C1: 4 puntos, mas que el maximo declarado de 3 (limite: supuesto declarado)",
            valor_observado=D(4),
            valor_esperado=D(3),
        )
    ]


def test_un_punto_en_el_orden_declarado_cuenta_aunque_no_cite_el_circuito() -> None:
    assert len(r10(_circuito(4, maximo=3, en_orden=True))) == 1
    assert r10(_circuito(3, maximo=3, en_orden=True)) == []


def test_un_punto_que_cita_el_circuito_y_esta_en_su_orden_se_cuenta_una_vez() -> None:
    base = _circuito(3, maximo=3)
    espacio = replace(
        base,
        circuitos=tuple(replace(c, orden=("T1", "T2", "T3")) for c in base.circuitos),
    )
    assert r10(espacio) == []


# --- severidad segun la fuente del limite -------------------------------------------------------


def _limites_verificados() -> Limites:
    verificada = lambda id_, valor: Constante(id_, id_, valor, VERIFICADA)  # noqa: E731
    return Limites(
        pendiente_minima=verificada("pendiente", D("0.01")),
        enlace_maximo=verificada("enlace", D("90")),
        puntos_por_circuito=verificada("puntos", "declarado por circuito"),
    )


def test_con_fuente_verificada_las_tres_condiciones_son_error() -> None:
    limites = _limites_verificados()
    casos = (
        r10(_drenaje(("0.009",)), limites),
        r10(_enlace("82.51"), limites),
        r10(_circuito(4, maximo=3), limites),
    )
    for hallazgos in casos:
        assert [h.severidad for h in hallazgos] == [Severidad.ERROR]
        assert VERIFICADA in hallazgos[0].descripcion


def test_hoy_los_tres_limites_son_supuesto_y_dan_advertencia() -> None:
    casos = (r10(_drenaje(("0.009",))), r10(_enlace("82.51")), r10(_circuito(4, maximo=3)))
    for hallazgos in casos:
        assert [h.severidad for h in hallazgos] == [Severidad.ADVERTENCIA]


def test_los_limites_por_defecto_son_los_de_cada_especialidad() -> None:
    from adapters.espacio.especialidades import agua, datos, electricidad

    por_defecto = Limites.por_defecto()
    assert por_defecto.pendiente_minima is agua.LIMITE_PENDIENTE_DRENAJE
    assert por_defecto.enlace_maximo is datos.LIMITE_ENLACE
    assert por_defecto.puntos_por_circuito is electricidad.LIMITE_PUNTOS_POR_CIRCUITO
    assert agua.LIMITE_PENDIENTE_DRENAJE.valor == D("0.01")
    assert agua.LIMITE_PENDIENTE_DRENAJE.supuesto_declarado
    assert agua.LIMITES_AGUA == (agua.LIMITE_PENDIENTE_DRENAJE,)


# --- OF-001 con un error sembrado por condicion ---------------------------------------------------


def test_of001_con_cada_condicion_sembrada_da_exactamente_ese_hallazgo() -> None:
    base = espacio_of001()
    # 1. enlace: PB3 pasa a un recorrido declarado de 87,51 m
    tramo = Tramo(
        orden=1,
        superficie=SuperficieTramo.TECHO,
        vertices=(_c("3", "1", "0"), _c("90.51", "1", "0")),
    )
    largo = Recorrido(id="R-PB3", punto_id="PB3", modo=ModoRecorrido.DECLARADO, tramos=(tramo,))
    enlace = replace(base, recorridos=(largo,))
    # 2. puntos por circuito: C2 admite 3 y tiene 4
    puntos = replace(
        base,
        circuitos=tuple(
            replace(c, puntos_maximos=3) if c.id == "C2" else c for c in base.circuitos
        ),
    )
    # 3. pendiente: el desague de la ducha declara su recorrido con pendiente 0,005
    drenaje = Recorrido(
        id="R-D1",
        punto_id="D1",
        modo=ModoRecorrido.DECLARADO,
        tramos=(_tramo(1, ("1", "1.5", "0"), ("2", "1.5", "0"), "0.005"),),
    )
    pendiente = replace(base, recorridos=(drenaje,))
    esperado = {
        "enlace": "esp_puntos:PB3",
        "puntos": "esp_circuitos:C2",
        "pendiente": "esp_recorridos:R-D1",
    }
    for nombre, espacio in (("enlace", enlace), ("puntos", puntos), ("pendiente", pendiente)):
        hallazgos = r10(espacio)
        assert len(hallazgos) == 1, nombre
        assert hallazgos[0].origen_ids[0] == esperado[nombre], nombre
        assert hallazgos[0].severidad is Severidad.ADVERTENCIA
