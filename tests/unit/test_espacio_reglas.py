"""R8 (origen de la medida) y R9 (coherencia espacial) del espacio (spec §8.2, tarea 1.6).

Cada condicion se siembra sola sobre un espacio minimo limpio y se exige UN hallazgo exacto
(regla, severidad, `origen_ids` con claves `esp_*` y mensaje). Los valores frontera usan la
tolerancia de §6.1 (0,001 m).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from adapters.espacio import (
    Ambiente,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    ModoRecorrido,
    OrigenMedida,
    Punto,
    Recorrido,
    SobrescrituraSegmento,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoOrigen,
    TipoPunto,
    Tramo,
)
from adapters.espacio.reglas import (
    CoherenciaEspacial,
    OrigenDeLaMedida,
    reglas_espacio,
)
from core.contracts import Hallazgo, ReglaVerificacion, Severidad
from core.contracts.presupuesto import Presupuesto
from tests.fixtures.espacio_bano import espacio_bano, espacio_bano_con_drenaje

D = Decimal
VACIO = Presupuesto(codigo="X", fecha=date(2026, 1, 1), moneda="USD", partidas=())
CLAVE_VERTICAL = "F|0.000,0.000,0.000|0.000,0.000,2.500"

LEVANTAMIENTO = OrigenMedida(
    id="LEV", tipo=TipoOrigen.LEVANTAMIENTO, referencia={"fecha": "2026-10-01", "responsable": "EP"}
)
SUPUESTO = OrigenMedida(id="SUP", tipo=TipoOrigen.SUPUESTO, referencia={"motivo": "sin plano"})


def r8(espacio: Espacio) -> list[Hallazgo]:
    return OrigenDeLaMedida(espacio).evaluar(VACIO)


def r9(espacio: Espacio) -> list[Hallazgo]:
    return CoherenciaEspacial(espacio).evaluar(VACIO)


def tramo(orden, superficie, a, b, empotrado=None) -> Tramo:
    return Tramo(
        orden=orden,
        superficie=superficie,
        empotrado=empotrado,
        vertices=(Coord(*(D(v) for v in a)), Coord(*(D(v) for v in b))),
    )


def punto(id_="P", z="1", ambiente="A", origen="LEV", **extra) -> Punto:
    datos = dict(
        id=id_,
        nombre=id_,
        especialidad=Especialidad.AGUA,
        tipo=TipoPunto.AGUA_FRIA,
        ambiente_id=ambiente,
        superficie=SuperficiePunto.PARED,
        posicion=Coord(D("2"), D("0"), D(z)),
        fuente_id="F",
        especificaciones={"diametro": '1/2"'},
        origen_id=origen,
    )
    datos.update(extra)
    return Punto(**datos)


def minimo(**cambios) -> Espacio:
    """Un ambiente de 4 x 3 x 2,5 m, una fuente en el origen y un punto: ningun hallazgo."""
    datos = dict(
        origenes=(LEVANTAMIENTO, SUPUESTO),
        ambientes=(
            Ambiente(
                id="A",
                nombre="Sala",
                x0=D("0"),
                y0=D("0"),
                largo=D("4"),
                ancho=D("3"),
                alto=D("2.5"),
                origen_id="LEV",
            ),
        ),
        fuentes=(
            Fuente(
                id="F",
                especialidad=Especialidad.AGUA,
                tipo=TipoFuente.MONTANTE_AGUA,
                ambiente_id="A",
                posicion=Coord(D("0"), D("0"), D("0")),
                origen_id="LEV",
            ),
        ),
        puntos=(punto(),),
    )
    datos.update(cambios)
    return Espacio(**datos)


def hallazgo(regla, severidad, origen, mensaje, **extra) -> Hallazgo:
    return Hallazgo(
        regla=regla, severidad=severidad, descripcion=mensaje, origen_ids=(origen,), **extra
    )


# --- contrato -----------------------------------------------------------------------------


def test_reglas_espacio_entrega_r8_r9_y_r10_con_codigos_cortos_y_sin_atribuir():
    reglas = reglas_espacio(minimo())

    assert isinstance(reglas, tuple)
    assert [(r.codigo, r.nombre) for r in reglas] == [
        ("R8", "Origen de la medida"),
        ("R9", "Coherencia espacial"),
        ("R10", "Límites de la especialidad"),
    ]
    for regla in reglas:
        assert isinstance(regla, ReglaVerificacion)
        assert len(regla.codigo) <= 10  # Hallazgo.regla es String(10)
        assert not hasattr(regla, "atribuir")  # ReglaAtribuible no es un contrato (§8.2)


def test_espacio_vacio_no_da_hallazgos_fr1():
    for regla in reglas_espacio(Espacio()):
        assert regla.evaluar(VACIO) == []


def test_espacio_minimo_limpio_no_da_hallazgos_ni_con_punto_sin_recorrido():
    assert r8(minimo()) == [] and r9(minimo()) == []
    assert minimo().recorridos == ()  # el punto no tiene recorrido: no es R9 por recorrido corto


def test_la_regla_lee_la_instantanea_y_no_el_presupuesto():
    espacio = minimo(origenes=(LEVANTAMIENTO, SUPUESTO), puntos=(punto(origen="SUP"),))
    a, b = OrigenDeLaMedida(espacio), OrigenDeLaMedida(espacio)
    assert a.evaluar(VACIO) == b.evaluar(VACIO) != []  # determinista


# --- R8 -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("campo", "fila", "tabla", "quien"),
    [
        ("ambientes", "ambientes", "esp_ambientes:A", "ambiente A"),
        ("fuentes", "fuentes", "esp_fuentes:F", "fuente F"),
        ("puntos", "puntos", "esp_puntos:P", "punto P"),
    ],
)
def test_r8_supuesto_en_cada_tipo_de_fila_es_advertencia(campo, fila, tabla, quien):
    base = minimo()
    filas = tuple(replace(f, origen_id="SUP") for f in getattr(base, campo))

    assert r8(replace(base, **{fila: filas})) == [
        hallazgo(
            "R8",
            Severidad.ADVERTENCIA,
            tabla,
            f"{quien}: la medida es un supuesto declarado (origen SUP: sin plano)",
        )
    ]


def test_r8_altura_pendiente_es_advertencia():
    pendiente = punto(especificaciones={"diametro": '1/2"', "altura": "pendiente"})

    assert r8(minimo(puntos=(pendiente,))) == [
        hallazgo(
            "R8",
            Severidad.ADVERTENCIA,
            "esp_puntos:P",
            "punto P: altura pendiente; la medida vertical es provisional",
        )
    ]


def test_r8_supuesto_y_altura_pendiente_dan_un_hallazgo_por_condicion():
    pto = punto(origen="SUP", especificaciones={"altura": "pendiente"})

    hallazgos = r8(minimo(puntos=(pto,)))

    assert [h.descripcion for h in hallazgos] == [
        "punto P: la medida es un supuesto declarado (origen SUP: sin plano)",
        "punto P: altura pendiente; la medida vertical es provisional",
    ]


def test_r8_sobrescritura_vigente_a_mano_es_advertencia():
    sobre = SobrescrituraSegmento(clave=CLAVE_VERTICAL, diametro='3/4"', empotrado=True)

    assert r8(minimo(sobrescrituras=(sobre,))) == [
        hallazgo(
            "R8",
            Severidad.ADVERTENCIA,
            f"esp_segmentos:{CLAVE_VERTICAL}",
            f"segmento {CLAVE_VERTICAL}: fijado a mano (diametro 3/4, empotrado si)",
        )
    ]


def test_r8_sobrescritura_huerfana_no_es_r8_sino_r9():
    sobre = SobrescrituraSegmento(clave="F|9.000,9.000,9.000|9.000,9.000,9.500", empotrado=False)

    assert r8(minimo(sobrescrituras=(sobre,))) == []
    assert len(r9(minimo(sobrescrituras=(sobre,)))) == 1


@pytest.mark.parametrize(
    ("campo", "tabla", "quien"),
    [
        ("ambientes", "esp_ambientes:A", "ambiente A"),
        ("fuentes", "esp_fuentes:F", "fuente F"),
        ("puntos", "esp_puntos:P", "punto P"),
    ],
)
@pytest.mark.parametrize("origen", ["NO-EXISTE", ""])
def test_r8_fila_sin_origen_de_medida_es_error(origen, campo, tabla, quien):
    """RF-44 / UC-13a: la fila se acepta en el espacio (sin mutar nada) y R8 la marca ERROR."""
    base = minimo()
    filas = tuple(replace(f, origen_id=origen) for f in getattr(base, campo))
    espacio = replace(base, **{campo: filas})

    assert r8(espacio) == [
        hallazgo(
            "R8",
            Severidad.ERROR,
            tabla,
            f"{quien}: origen no registrado (origen_id {origen!r})",
        )
    ]


def test_r8_origen_sin_su_referencia_obligatoria_es_error():
    """RF-44 / UC-13a: un origen al que le falta un dato se acepta y R8 lo marca ERROR."""
    sin_motivo = OrigenMedida(id="SUP", tipo=TipoOrigen.SUPUESTO, referencia={})
    sin_responsable = OrigenMedida(
        id="LEV2", tipo=TipoOrigen.LEVANTAMIENTO, referencia={"fecha": "2026-10-01"}
    )
    espacio = minimo(
        origenes=(LEVANTAMIENTO, sin_motivo, sin_responsable),
        puntos=(punto("P1", origen="SUP"), punto("P2", origen="LEV2")),
    )

    assert r8(espacio) == [
        hallazgo(
            "R8",
            Severidad.ERROR,
            "esp_puntos:P1",
            "punto P1: origen sin referencia (origen SUP: falta «motivo»)",
        ),
        hallazgo(
            "R8",
            Severidad.ERROR,
            "esp_puntos:P2",
            "punto P2: origen sin referencia (origen LEV2: falta «responsable»)",
        ),
    ]


def test_r8_origen_supuesto_sin_motivo_no_revienta_y_solo_da_el_error_de_referencia():
    sin_motivo = OrigenMedida(id="SUP", tipo=TipoOrigen.SUPUESTO, referencia={})
    espacio = minimo(origenes=(LEVANTAMIENTO, sin_motivo), puntos=(punto(origen="SUP"),))

    assert [h.severidad for h in r8(espacio)] == [Severidad.ERROR]


# --- R9 -----------------------------------------------------------------------------------


def test_r9_fuente_fuera_de_su_ambiente():
    fuente = replace(minimo().fuentes[0], posicion=Coord(D("4.0011"), D("0"), D("0")))

    assert r9(minimo(fuentes=(fuente,))) == [
        hallazgo("R9", Severidad.ERROR, "esp_fuentes:F", "fuente F: fuera del ambiente A")
    ]


def test_r9_fuente_en_el_borde_mas_tolerancia_no_es_error():
    fuente = replace(minimo().fuentes[0], posicion=Coord(D("4.001"), D("0"), D("0")))

    assert r9(minimo(fuentes=(fuente,))) == []


@pytest.mark.parametrize(
    ("z", "es_error"),
    [("2.5", False), ("2.501", False), ("2.5011", True)],
)
def test_r9_altura_de_un_punto_frente_a_la_del_ambiente(z, es_error):
    esperado = (
        [hallazgo("R9", Severidad.ERROR, "esp_puntos:P", "punto P: fuera del ambiente A")]
        if es_error
        else []
    )

    assert r9(minimo(puntos=(punto(z=z),))) == esperado


def _recorrido_con_techo(altura: str) -> Recorrido:
    pared, techo = SuperficieTramo.PARED, SuperficieTramo.TECHO
    return Recorrido(
        id="RD",
        punto_id="P",
        modo=ModoRecorrido.DECLARADO,
        tramos=(
            tramo(1, pared, ("0", "0", "0"), ("0", "0", altura)),
            tramo(2, techo, ("0", "0", altura), ("2", "0", altura)),
            tramo(3, pared, ("2", "0", altura), ("2", "0", "1")),
        ),
    )


@pytest.mark.parametrize(
    ("altura", "es_error"),
    [("2.5", False), ("2.501", False), ("2.5011", True)],
)
def test_r9_altura_de_un_recorrido_frente_a_la_del_ambiente(altura, es_error):
    esperado = (
        [
            hallazgo(
                "R9",
                Severidad.ERROR,
                "esp_recorridos:RD",
                "recorrido RD: la altura 2.5011 supera la del ambiente A (2.5)",
                valor_observado=D("2.5011"),
                valor_esperado=D("2.5"),
            )
        ]
        if es_error
        else []
    )

    assert r9(minimo(recorridos=(_recorrido_con_techo(altura),))) == esperado


def _recorrido_con_hueco(inicio_segundo: str) -> Recorrido:
    pared = SuperficieTramo.PARED
    return Recorrido(
        id="RC",
        punto_id="P",
        modo=ModoRecorrido.DECLARADO,
        tramos=(
            tramo(1, pared, ("0", "0", "0"), ("1", "0", "0")),
            tramo(2, pared, (inicio_segundo, "0", "0"), ("2", "0", "0")),
        ),
    )


def test_r9_recorrido_igual_a_la_distancia_ortogonal_minima_es_valido():
    assert r9(minimo(recorridos=(_recorrido_con_hueco("1"),))) == []


def test_r9_recorrido_un_milimetro_mas_corto_es_error():
    assert r9(minimo(recorridos=(_recorrido_con_hueco("1.001"),))) == [
        hallazgo(
            "R9",
            Severidad.ERROR,
            "esp_recorridos:RC",
            "recorrido RC: longitud 1.999 menor que la distancia ortogonal minima 2 entre sus "
            "extremos",
            valor_observado=D("1.999"),
            valor_esperado=D("2"),
        )
    ]


def test_r9_recorrido_diagonal_es_mas_corto_que_la_ortogonal():
    pared = SuperficieTramo.PARED
    diagonal = Recorrido(
        id="RG",
        punto_id="P",
        modo=ModoRecorrido.DECLARADO,
        tramos=(tramo(1, pared, ("0", "0", "0"), ("3", "4", "0")),),
    )
    espacio = minimo(recorridos=(diagonal,))

    (h,) = r9(espacio)
    assert (h.valor_observado, h.valor_esperado) == (D("5"), D("7"))


def _diagonal_en_dos_tramos(orden_ab: int, orden_bc: int) -> Recorrido:
    """A(0,0,0) -> B(1,1,0) -> C(2,2,0): 2,83 m de largo contra 4 m de distancia ortogonal."""
    pared = SuperficieTramo.PARED
    return Recorrido(
        id="RO",
        punto_id="P",
        modo=ModoRecorrido.DECLARADO,
        tramos=(
            tramo(orden_ab, pared, ("0", "0", "0"), ("1", "1", "0")),
            tramo(orden_bc, pared, ("1", "1", "0"), ("2", "2", "0")),
        ),
    )


def test_r9_extremos_del_camino_no_dependen_del_orden_declarado_de_los_tramos():
    """Los extremos son los del camino, no los de la lista de tramos: con los `orden` cruzados
    (el tramo B-C primero) la comparacion contra la distancia ortogonal sigue siendo A-C."""
    en_orden = r9(minimo(recorridos=(_diagonal_en_dos_tramos(1, 2),)))
    cruzado = r9(minimo(recorridos=(_diagonal_en_dos_tramos(2, 1),)))

    (h,) = en_orden
    assert h.valor_esperado == D("4") and h.valor_observado < D("4")
    assert cruzado == en_orden


def test_r9_tramos_que_no_forman_un_camino_no_se_comparan_ni_revientan():
    """Un recorrido ramificado (tres tramos desde B) no tiene dos extremos: no hay distancia
    ortogonal minima que exigirle, y R9 no lo inventa."""
    pared = SuperficieTramo.PARED
    ramas = Recorrido(
        id="RY",
        punto_id="P",
        modo=ModoRecorrido.DECLARADO,
        tramos=(
            tramo(1, pared, ("1", "1", "0"), ("0", "0", "0")),
            tramo(2, pared, ("1", "1", "0"), ("2", "2", "0")),
            tramo(3, pared, ("1", "1", "0"), ("1", "2", "0")),
        ),
    )

    assert r9(minimo(recorridos=(ramas,))) == []


def _recorrido_vertical(id_, punto_id, empotrado) -> Recorrido:
    return Recorrido(
        id=id_,
        punto_id=punto_id,
        modo=ModoRecorrido.DECLARADO,
        tramos=(tramo(1, SuperficieTramo.PARED, ("0", "0", "0"), ("0", "0", "2.5"), empotrado),),
    )


def _con_empotrado_en_conflicto(**cambios) -> Espacio:
    return minimo(
        puntos=(punto("P"), punto("Q", z="1")),
        recorridos=(
            _recorrido_vertical("R1", "P", True),
            _recorrido_vertical("R2", "Q", False),
        ),
        **cambios,
    )


def test_r9_segmentos_solapados_con_empotrado_distinto_sin_declarar():
    assert r9(_con_empotrado_en_conflicto()) == [
        hallazgo(
            "R9",
            Severidad.ERROR,
            f"esp_segmentos:{CLAVE_VERTICAL}",
            f"segmento {CLAVE_VERTICAL}: tramos solapados con empotrado distinto sin declarar",
        )
    ]


def test_r9_el_conflicto_declarado_con_sobrescritura_no_es_error():
    sobre = SobrescrituraSegmento(clave=CLAVE_VERTICAL, empotrado=True)

    assert r9(_con_empotrado_en_conflicto(sobrescrituras=(sobre,))) == []


def test_r9_sobrescritura_huerfana():
    clave = "F|9.000,9.000,9.000|9.000,9.000,9.500"
    sobre = SobrescrituraSegmento(clave=clave, empotrado=False)

    assert r9(minimo(sobrescrituras=(sobre,))) == [
        hallazgo(
            "R9",
            Severidad.ERROR,
            f"esp_segmentos:{clave}",
            f"sobrescritura del segmento {clave}: ningun segmento vigente tiene esa clave",
        )
    ]


def test_r9_orden_estable_por_condicion():
    clave = "F|9.000,9.000,9.000|9.000,9.000,9.500"
    fuente = replace(minimo().fuentes[0], posicion=Coord(D("5"), D("0"), D("0")))
    espacio = _con_empotrado_en_conflicto(
        fuentes=(fuente,),
        sobrescrituras=(SobrescrituraSegmento(clave=clave, empotrado=False),),
    )

    assert [h.origen_ids[0] for h in r9(espacio)] == [
        "esp_fuentes:F",  # 1. fuera del ambiente
        f"esp_segmentos:{CLAVE_VERTICAL}",  # 4. empotrado en conflicto
        f"esp_segmentos:{clave}",  # 5. sobrescritura huerfana
    ]


# --- OF-001 limpio ------------------------------------------------------------------------


def _supuesto(tabla, id_, quien) -> Hallazgo:
    return hallazgo(
        "R8",
        Severidad.ADVERTENCIA,
        f"{tabla}:{id_}",
        f"{quien}: la medida es un supuesto declarado (origen O1: ejemplo de memoria de cálculo)",
    )


def test_of001_bano_limpio_conjunto_exacto_de_hallazgos():
    """El bano trae un solo origen, un supuesto declarado (coordenadas de la memoria de calculo,
    no de un plano), asi que cada fila que lo cita es una ADVERTENCIA de R8: el ambiente, la
    fuente y los dos puntos. La sobrescritura del tramo vertical es la quinta. R9 no da nada."""
    espacio = espacio_bano()
    clave = "F1|0.000,0.000,0.000|0.000,0.000,2.500"

    assert r9(espacio) == []
    assert r8(espacio) == [
        _supuesto("esp_ambientes", "BAN-01", "ambiente BAN-01"),
        _supuesto("esp_fuentes", "F1", "fuente F1"),
        _supuesto("esp_puntos", "P1", "punto P1"),
        _supuesto("esp_puntos", "P2", "punto P2"),
        hallazgo(
            "R8",
            Severidad.ADVERTENCIA,
            f"esp_segmentos:{clave}",
            f"segmento {clave}: fijado a mano (diametro 3/4, empotrado si)",
        ),
    ]


def test_of001_bano_con_drenaje_conjunto_exacto_de_hallazgos():
    espacio = espacio_bano_con_drenaje()

    assert r9(espacio) == []
    assert [h.origen_ids[0] for h in r8(espacio)] == [
        "esp_ambientes:BAN-01",
        "esp_fuentes:F1",
        "esp_fuentes:FD1",
        "esp_puntos:D1",
        "esp_puntos:D2",
        "esp_puntos:P1",
        "esp_puntos:P2",
        "esp_segmentos:F1|0.000,0.000,0.000|0.000,0.000,2.500",
    ]
