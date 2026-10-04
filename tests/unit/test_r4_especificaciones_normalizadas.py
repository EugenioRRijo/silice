"""R4 compara especificaciones normalizadas, no subcadenas (SF‑E5, hallazgo A‑2).

Oráculos:

- **Caso directo** de `docs/linea_base.md` (inconsistencia 5): la memoria rotula la tubería en 3/4"
  y el proyecto y el APU la costean en 4". Aquí el cómputo lleva el rótulo de la memoria también en
  su descripción, como en el PDF: la descripción del propio ítem no puede confirmar su
  especificación (la escribe la misma persona que se equivocó).
- **Los cuatro pares** de la bitácora de TI‑001 (`docs/bitacora/2026-09-30-caso-ti001.md`, A‑2):
  «4 pulg» frente a «3/4 pulg», «2» frente a «1/2», «6» frente a «16» y «1/2» frente a «1 1/2». Con
  la comparación por subcadena el primero de cada par «aparecía» dentro del segundo y R4 callaba.
- **Casos de borde:** sin especificaciones, números sin unidad, mezcla de decimal y fracción, y que
  todo valor numérico sea `Decimal` (NORMAS.md §2.3).

`test_auditoria_7_de_7.py` y `test_r4_marca_3_4_pulg_y_no_marca_pvc` no se tocan: siguen fijando
el 7 de 7 y el ERROR de 3/4 pulg sobre la fixture de siete inconsistencias.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from core.contracts import (
    ComposicionAPU,
    Dominio,
    ItemComputo,
    LineaMaterial,
    OrigenTipo,
    PartidaPresupuestada,
    Presupuesto,
    Severidad,
)
from core.costing import calcular_apu
from core.verification import CorrespondenciaEspecificaciones, directivas
from core.verification import texto as modulo_texto
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.presupuesto_auditado import presupuesto_con_siete_inconsistencias

ORIGEN = "prueba:R4"


def _presupuesto(
    texto_apu: str,
    especificaciones: dict[str, str],
    *,
    descripcion_item: str = "partida de prueba",
    lineas: tuple[str, ...] = (),
) -> Presupuesto:
    """Una sola partida: el APU dice `texto_apu` (y sus `lineas` de material), el cómputo declara
    `especificaciones`."""
    apu = ComposicionAPU(
        codigo_partida="P-01",
        descripcion=texto_apu,
        unidad="m",
        rendimiento=Decimal(1),
        materiales=tuple(
            LineaMaterial(descripcion, "m", Decimal(1), Decimal(1)) for descripcion in lineas
        ),
    )
    item = ItemComputo(
        codigo_partida="P-01",
        descripcion=descripcion_item,
        unidad="m",
        cantidad=Decimal(1),
        origen_id=ORIGEN,
        origen_tipo=OrigenTipo.MANUAL,
        dominio=Dominio.CIVIL,
        especificaciones=especificaciones,
    )
    partida = PartidaPresupuestada(
        item=item, apu=apu, resultado=calcular_apu(apu, linea_base.PARAMETROS_LINEA_BASE)
    )
    return Presupuesto(
        codigo="R4-PRUEBA",
        fecha=date(2026, 10, 4),
        moneda="USD",
        partidas=(partida,),
    )


def _r4(presupuesto: Presupuesto):
    return CorrespondenciaEspecificaciones().evaluar(presupuesto)


def _unico(presupuesto: Presupuesto):
    (hallazgo,) = _r4(presupuesto)
    return hallazgo


# ---------------------------------------------------------------------------------------------
# Caso directo de la línea base
# ---------------------------------------------------------------------------------------------


def test_caso_directo_la_descripcion_del_item_no_confirma_su_especificacion():
    """Inconsistencia 5 tal como la trae el PDF: el cómputo dice «Tubería de 3/4 pulg» y declara
    3/4 pulg; el APU de tubería dice 4 pulgadas. Con la descripción del ítem en el corpus, el 3/4
    se «reconocía» en el propio cómputo y R4 no veía la contradicción."""
    presupuesto = presupuesto_con_siete_inconsistencias()
    tuberia = linea_base.APU_TUBERIA.codigo_partida
    partidas = tuple(
        replace(
            partida,
            item=replace(
                partida.item, descripcion=f"Tubería de {linea_base.DIAMETRO_TUBERIA_MEMORIA}"
            ),
        )
        if partida.item.codigo_partida == tuberia
        else partida
        for partida in presupuesto.partidas
    )

    hallazgos = _r4(replace(presupuesto, partidas=partidas))

    errores = [h for h in hallazgos if h.severidad is Severidad.ERROR]
    assert len(errores) == 1
    assert errores[0].origen_ids[0].endswith(tuberia)
    assert "declara 3/4 pulg" in errores[0].descripcion
    assert "dice 4 pulg" in errores[0].descripcion


def test_una_especificacion_que_solo_nombra_la_descripcion_del_item_no_es_contrastable():
    """El APU calla el diámetro; solo la descripción del propio cómputo lo nombra: no hay contra
    qué contrastarlo (INFO), en vez de darlo por reconocido."""
    hallazgo = _unico(
        _presupuesto(
            "Suministro e instalacion de tuberia PVC",
            {"diametro": "3/4 pulg"},
            descripcion_item="Tuberia PVC de 3/4 pulg",
        )
    )
    assert hallazgo.severidad is Severidad.INFO
    assert "no es contrastable" in hallazgo.descripcion


# ---------------------------------------------------------------------------------------------
# Los cuatro pares de la bitácora de TI‑001, en los dos sentidos
# ---------------------------------------------------------------------------------------------

PARES = [
    pytest.param("4 pulg", "3/4 pulg", "4", "3/4", id="4-frente-a-3/4"),
    pytest.param("2 pulg", "1/2 pulg", "2", "1/2", id="2-frente-a-1/2"),
    pytest.param("6 pulg", "16 pulg", "6", "16", id="6-frente-a-16"),
    pytest.param("1/2 pulg", "1 1/2 pulg", "1/2", "1 1/2", id="1/2-frente-a-1-1/2"),
]


@pytest.mark.parametrize(("declarado", "en_apu", "numero_declarado", "numero_apu"), PARES)
def test_r4_marca_el_valor_declarado_contenido_en_el_del_apu(
    declarado, en_apu, numero_declarado, numero_apu
):
    hallazgo = _unico(_presupuesto(f"Tuberia de {en_apu}", {"diametro": declarado}))
    assert hallazgo.severidad is Severidad.ERROR
    assert f"declara {numero_declarado} pulg" in hallazgo.descripcion
    assert f"dice {numero_apu} pulg" in hallazgo.descripcion
    assert hallazgo.origen_ids == (ORIGEN,)


@pytest.mark.parametrize(("declarado", "en_apu", "numero_declarado", "numero_apu"), PARES)
def test_r4_marca_el_par_en_el_sentido_inverso(declarado, en_apu, numero_declarado, numero_apu):
    """Al revés (el APU dice el valor corto): «1 1/2 pulg» frente a «1/2 pulg» también fallaba,
    porque el número mixto se partía y su `1/2` coincidía con el del texto."""
    hallazgo = _unico(_presupuesto(f"Tuberia de {declarado}", {"diametro": en_apu}))
    assert hallazgo.severidad is Severidad.ERROR
    assert f"declara {numero_apu} pulg" in hallazgo.descripcion
    assert f"dice {numero_declarado} pulg" in hallazgo.descripcion


def test_r4_ve_la_contradiccion_aunque_el_apu_cite_el_valor_dentro_de_un_rango():
    """El control de 1/2 pulg de TI‑001: el APU costea tubo de 1 pulg y cita la «Dobladora de tubo
    EMT 1/2 a 1 1/2 pulg». El `1/2` del rango no es un 1/2 pulg."""
    hallazgo = _unico(
        _presupuesto(
            "Suministro e instalacion de tuberia EMT 1 pulg",
            {"diametro": "1/2 pulg"},
            lineas=("Tubo EMT 1 pulg", "Dobladora de tubo EMT 1/2 a 1 1/2 pulg"),
        )
    )
    assert hallazgo.severidad is Severidad.ERROR
    assert "declara 1/2 pulg" in hallazgo.descripcion


def test_r4_reconoce_el_valor_exacto_y_no_marca_el_rango():
    """El caso limpio de TI‑001: 1 pulg declarado, 1 pulg en el APU, aunque la dobladora cite otros
    diámetros."""
    presupuesto = _presupuesto(
        "Suministro e instalacion de tuberia EMT 1 pulg",
        {"diametro": "1 pulg"},
        lineas=("Dobladora de tubo EMT 1/2 a 1 1/2 pulg",),
    )
    assert _r4(presupuesto) == []


# ---------------------------------------------------------------------------------------------
# Casos de borde
# ---------------------------------------------------------------------------------------------


def test_sin_especificaciones_no_hay_hallazgos():
    assert _r4(_presupuesto("Tuberia de 4 pulg", {})) == []


def test_solo_directivas_no_hay_hallazgos():
    especificaciones = {directivas.CLAVE_UNIDAD_ORIGINAL: "mts"}
    assert _r4(_presupuesto("Tuberia de 4 pulg", especificaciones)) == []


def test_un_numero_sin_unidad_no_se_reconoce_dentro_de_otro():
    """«2» no está en «1/2»: sin unidad no hay contradicción que afirmar, pero tampoco se da por
    reconocido. Antes callaba."""
    hallazgo = _unico(_presupuesto("Juego de llaves 1/2", {"medida": "2"}))
    assert hallazgo.severidad is Severidad.INFO
    assert "no es contrastable" in hallazgo.descripcion


def test_un_numero_sin_unidad_igual_al_del_apu_se_reconoce():
    assert _r4(_presupuesto("Cable de 16 hilos", {"hilos": "16"})) == []


@pytest.mark.parametrize(
    ("declarado", "en_apu"),
    [
        ("0.5 pulg", "1/2 pulg"),
        ("0,75 pulg", '3/4"'),
        ("1.5 pulg", "1 1/2 pulgadas"),
        ("4.0 pulg", "4 pulg"),
        ("0.10 m", "0.1 m"),
    ],
)
def test_decimal_y_fraccion_del_mismo_valor_se_reconocen(declarado, en_apu):
    assert _r4(_presupuesto(f"Tuberia de {en_apu}", {"diametro": declarado})) == []


def test_decimal_frente_a_otra_fraccion_es_contradiccion():
    hallazgo = _unico(_presupuesto("Tuberia de 4 pulg", {"diametro": "0.75 pulg"}))
    assert hallazgo.severidad is Severidad.ERROR
    assert "declara 0.75 pulg" in hallazgo.descripcion
    assert "dice 4 pulg" in hallazgo.descripcion


def test_una_palabra_no_se_reconoce_dentro_de_otra():
    """El hallazgo 1 de la bitácora M3.2: «auditor» no está en «auditoria»."""
    hallazgo = _unico(
        _presupuesto("Generar el informe de auditoria del presupuesto", {"actor": "auditor"})
    )
    assert hallazgo.severidad is Severidad.INFO


def test_la_puntuacion_del_texto_no_impide_reconocer_una_palabra():
    """Comparar por palabra no puede volver «no contrastable» lo que el texto sí dice al final de
    una frase («...de concreto.»)."""
    assert _r4(_presupuesto("Vaciado de concreto.", {"material": "Concreto"})) == []


def test_una_denominacion_de_varias_palabras_se_reconoce_en_orden():
    assert (
        _r4(_presupuesto("Tuberia PVC de 4 pulg", {"diametro": "4 pulg", "material": "pvc"})) == []
    )
    hallazgo = _unico(_presupuesto("Tuberia de 4 pulg de PVC", {"material": "pvc de 4 pulg"}))
    assert hallazgo.severidad is Severidad.INFO


def test_una_fraccion_de_denominador_cero_no_es_un_numero_ni_rompe_la_regla():
    hallazgo = _unico(_presupuesto("Tuberia de 4 pulg", {"diametro": "1/0 pulg"}))
    assert hallazgo.severidad is Severidad.INFO


# ---------------------------------------------------------------------------------------------
# El valor comparable es Decimal (NORMAS.md §2.3)
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "esperado"),
    [
        ("4", Decimal(4)),
        ("3/4", Decimal("0.75")),
        ("0.10", Decimal("0.1")),
        ("16", Decimal(16)),
    ],
)
def test_valor_numerico_es_decimal_exacto(token, esperado):
    valor = modulo_texto.valor_numerico(token)
    assert isinstance(valor, Decimal)
    assert valor == esperado


@pytest.mark.parametrize("token", ["pulg", "1/0", "0/0", "28/04/2026", "6x6x4", ""])
def test_valor_numerico_de_lo_que_no_es_un_numero_es_none(token):
    assert modulo_texto.valor_numerico(token) is None


def test_magnitudes_une_el_numero_mixto_y_conserva_su_grafia():
    """`1 1/2 pulg` es una sola magnitud de 1,5 pulgadas; la grafía original se conserva para la
    descripción del hallazgo."""
    magnitudes = modulo_texto.magnitudes("Dobladora de tubo EMT 1/2 a 1 1/2 pulg y tubo 2,5 m")
    assert [(m.texto, m.valor, m.unidad) for m in magnitudes] == [
        ("1/2", Decimal("0.5"), "a"),
        ("1 1/2", Decimal("1.5"), "pulg"),
        ("2.5", Decimal("2.5"), "m"),
    ]
    assert all(isinstance(m.valor, Decimal) for m in magnitudes)


# ---------------------------------------------------------------------------------------------
# Ronda de corrección 1 de la tarea 1.2
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "linea",
    [
        'Codo PVC 90° 1/2"',
        'Codo PVC 90º 1/2"',
        'Codo PVC 90 grados 1/2"',
        'Codo PVC 90°1/2"',
    ],
)
def test_un_angulo_no_forma_numero_mixto_con_el_diametro_que_le_sigue(linea):
    """«90° 1/2"» es un codo de 90 grados y 1/2 pulg, no una cantidad de 90,5 pulg: con el «°»
    descartado, el 90 y el 1/2 quedaban juntos y R4 marcaba un ERROR falso (1/2 frente a 90 1/2)."""
    presupuesto = _presupuesto(
        "Instalacion de codos de PVC",
        {"diametro": "1/2 pulg"},
        lineas=(linea,),
    )
    assert _r4(presupuesto) == []
    assert [m.valor for m in modulo_texto.magnitudes(linea) if m.unidad == "pulg"] == [
        Decimal("0.5")
    ]


def test_dos_descripciones_no_se_leen_como_una_sola():
    """Comparación línea a línea: una descripción que termina en «… 4» y la siguiente que empieza
    por «pulg …» no forman «4 pulg» (ni para reconocer la especificación ni como magnitud)."""
    hallazgo = _unico(
        _presupuesto(
            "Suministro e instalacion de tuberia de 4",
            {"diametro": "4 pulg"},
            lineas=("pulg galvanizada de acero",),
        )
    )
    assert hallazgo.severidad is Severidad.INFO
    assert "no es contrastable" in hallazgo.descripcion


# ---------------------------------------------------------------------------------------------
# Ronda de corrección 2 de la tarea 1.2
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("texto", ['Tubo 1-1/2"', "Tubo 1 - 1/2 pulg", "Tubo 1 -1/2 pulgadas"])
def test_el_guion_une_el_numero_mixto(texto):
    """«1-1/2"» es la otra grafía del número mixto: vale 1,5 pulg, igual que «1 1/2"»."""
    assert [(m.valor, m.unidad) for m in modulo_texto.magnitudes(texto)] == [
        (Decimal("1.5"), "pulg")
    ]


def test_r4_reconoce_1_1_2_pulg_en_un_apu_escrito_con_guion():
    assert _r4(_presupuesto('Tuberia EMT de 1-1/2"', {"diametro": "1 1/2 pulg"})) == []


@pytest.mark.parametrize("texto", ['Codo PVC 90°1/2"', 'Codo PVC 90° 1/2"', 'Codo PVC 90°-1/2"'])
def test_el_angulo_sigue_separado_del_diametro(texto):
    assert [m.valor for m in modulo_texto.magnitudes(texto) if m.unidad == "pulg"] == [
        Decimal("0.5")
    ]
