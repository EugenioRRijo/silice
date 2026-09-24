"""Reglas paramétricas y adaptador tabular del dominio civil (Sesión I3.2).

Reproduce, a partir de las expresiones declaradas en `adapters/civil/reglas.py`, los mismos números
que la memoria de cálculo auditada (`tests/fixtures/apu_linea_base.py`): 0,224 m3 de concreto y
4,48 m2 de encofrado por tanquilla, y 7,68 m3 de excavación de zanja. No repite esos números salvo
los que el fixture no expone (sobreancho, espesor de fondo, diámetro y desperdicio de tubería, que
son supuestos de esta sesión, declarados también en data/samples/civil/README.md).
"""

from decimal import Decimal
from pathlib import Path

import pytest

from adapters.civil.evaluador import evaluar_regla
from adapters.civil.reglas import (
    CLAVE_BALANCE,
    REGLA_CONCRETO_TANQUILLA,
    REGLA_ENCOFRADO_TANQUILLA,
    REGLA_EXCAVACION_TANQUILLA,
    computar_relleno,
    computar_tanquillas,
    computar_zanja,
)
from adapters.civil.tabular import AdaptadorCivilTabular
from core.contracts import Dominio, OrigenTipo
from core.verification.expresiones import evaluar, sustituir_codigos
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_civil import (
    CODIGOS,
    DESPERDICIO_TUBERIA,
    DIAMETRO_TUBERIA_M,
    ESPESOR_FONDO,
    SOBREANCHO,
)
from tests.fixtures.presupuesto_auditado import BALANCE_RELLENO

RUTA_MUESTRA = (
    Path(__file__).resolve().parents[2] / "data" / "samples" / "civil" / "tanquillas_y_zanja.csv"
)
CABECERA_CSV = RUTA_MUESTRA.read_text(encoding="utf-8").splitlines()[0]


def _computar_una_tanquilla(n: Decimal):
    geometria = linea_base.GEOMETRIA_TANQUILLA
    return computar_tanquillas(
        origen_id="T-01",
        codigos=CODIGOS,
        a=geometria["a"],
        h=geometria["h"],
        e=geometria["e"],
        n=n,
        sobreancho=SOBREANCHO,
        espesor_fondo=ESPESOR_FONDO,
    )


def _computar_la_zanja():
    return computar_zanja(
        origen_id="Z-01",
        codigos=CODIGOS,
        longitud=linea_base.LONGITUD_TUBERIA_M,
        ancho=linea_base.ZANJA["ancho"],
        profundidad=linea_base.ZANJA["profundidad"],
        diametro=DIAMETRO_TUBERIA_M,
        desperdicio=DESPERDICIO_TUBERIA,
    )


def test_concreto_por_tanquilla_es_0_224():
    concreto, _encofrado, _excavacion = _computar_una_tanquilla(n=Decimal("1"))
    assert concreto.cantidad == linea_base.CANTIDAD_POR_TANQUILLA_MEMORIA["LB-04-CON"]


def test_encofrado_por_tanquilla_es_4_48():
    _concreto, encofrado, _excavacion = _computar_una_tanquilla(n=Decimal("1"))
    assert encofrado.cantidad == linea_base.CANTIDAD_POR_TANQUILLA_MEMORIA["LB-03-ENC"]


def test_cuatro_tanquillas_reproducen_el_computo_corregido():
    concreto, encofrado, _excavacion = _computar_una_tanquilla(n=linea_base.N_TANQUILLAS)
    assert concreto.cantidad == linea_base.COMPUTO_CORREGIDO["LB-04-CON"]
    assert encofrado.cantidad == linea_base.COMPUTO_CORREGIDO["LB-03-ENC"]


def test_zanja_reproduce_7_68():
    excavacion, _tuberia = _computar_la_zanja()
    assert excavacion.cantidad == linea_base.ZANJA["volumen"]


def test_tuberia_con_desperdicio():
    _excavacion, tuberia = _computar_la_zanja()
    assert tuberia.cantidad == Decimal("25.2")


def test_los_items_son_trazables():
    items = [
        *_computar_una_tanquilla(n=linea_base.N_TANQUILLAS),
        *_computar_la_zanja(),
        computar_relleno(
            origen_id="relleno:T-01,Z-01",
            codigos=CODIGOS,
            excavacion=Decimal("11.28"),
            concreto=Decimal("0.896"),
            volumen_tuberia=Decimal("0.2"),
            balance=BALANCE_RELLENO,
        ),
    ]

    assert len(items) == 6
    for item in items:
        assert item.origen_tipo is OrigenTipo.REGLA
        assert item.dominio is Dominio.CIVIL
        assert item.regla is not None
        assert evaluar_regla(item.regla, item.parametros) == item.cantidad


def test_cambiar_el_ancho_altera_solo_las_cantidades_que_dependen_de_el():
    """RF‑19 (UC‑04, pasos 1 y 2; INV‑011): cambiar el ancho de la tanquilla altera las cantidades
    derivadas de esa dimensión y ninguna otra, y cada ítem nuevo trae la expresión y los
    parámetros que lo produjeron."""
    geometria = linea_base.GEOMETRIA_TANQUILLA
    ancho_nuevo = geometria["a"] + Decimal("0.20")
    antes = [*_computar_una_tanquilla(n=linea_base.N_TANQUILLAS), *_computar_la_zanja()]
    despues = [
        *computar_tanquillas(
            origen_id="T-01",
            codigos=CODIGOS,
            a=ancho_nuevo,
            h=geometria["h"],
            e=geometria["e"],
            n=linea_base.N_TANQUILLAS,
            sobreancho=SOBREANCHO,
            espesor_fondo=ESPESOR_FONDO,
        ),
        *_computar_la_zanja(),
    ]

    cambiadas = {
        nuevo.regla
        for viejo, nuevo in zip(antes, despues, strict=True)
        if viejo.cantidad != nuevo.cantidad
    }

    assert cambiadas == {
        REGLA_CONCRETO_TANQUILLA,
        REGLA_ENCOFRADO_TANQUILLA,
        REGLA_EXCAVACION_TANQUILLA,
    }
    for item in despues:
        assert evaluar_regla(item.regla, item.parametros) == item.cantidad
        if item.regla in cambiadas:
            assert item.parametros["a"] == ancho_nuevo


def test_adaptador_tabular_extrae_la_muestra():
    adaptador = AdaptadorCivilTabular(codigos=CODIGOS)
    assert adaptador.dominio is Dominio.CIVIL

    items = adaptador.extraer(RUTA_MUESTRA)
    assert len(items) == 6

    concreto, encofrado, excavacion_tanquilla, excavacion_zanja, tuberia, relleno = items

    assert concreto.codigo_partida == CODIGOS["concreto"]
    assert encofrado.codigo_partida == CODIGOS["encofrado"]
    assert excavacion_tanquilla.codigo_partida == CODIGOS["excavacion"]
    assert excavacion_zanja.codigo_partida == CODIGOS["excavacion"]
    assert tuberia.codigo_partida == CODIGOS["tuberia"]
    assert relleno.codigo_partida == CODIGOS["relleno"]

    assert concreto.cantidad == linea_base.COMPUTO_CORREGIDO["LB-04-CON"]
    assert encofrado.cantidad == linea_base.COMPUTO_CORREGIDO["LB-03-ENC"]
    assert excavacion_zanja.cantidad == linea_base.ZANJA["volumen"]
    assert tuberia.cantidad == Decimal("25.2")

    assert CLAVE_BALANCE in relleno.especificaciones
    assert relleno.especificaciones[CLAVE_BALANCE].startswith(f"{{{CODIGOS['excavacion']}}}")


def _csv_de_filas(tmp_path: Path, *filas: str) -> Path:
    """Escribe un CSV de geometría con la cabecera de la muestra del repositorio."""
    archivo = tmp_path / "geometria.csv"
    archivo.write_text("\n".join((CABECERA_CSV, *filas)) + "\n", encoding="utf-8")
    return archivo


def _cantidades_por_codigo(items) -> dict[str, Decimal]:
    """Lo mismo que hace R5 antes de evaluar un balance: sumar cantidades por código."""
    cantidades: dict[str, Decimal] = {}
    for item in items:
        cantidades[item.codigo_partida] = (
            cantidades.get(item.codigo_partida, Decimal("0")) + item.cantidad
        )
    return cantidades


def test_adaptador_tabular_rechaza_dos_zanjas_de_diametros_distintos(tmp_path):
    """El balance de relleno lleva un solo factor de volumen de tubería.

    Con dos diámetros, el término `{tuberia} * factor` de la expresión solo puede llevar uno de
    los dos, y R5 evaluaría un volumen de tubería que no es el del cómputo: un ERROR falso sobre
    datos consistentes (revisión final, ítem 1). Un término por diámetro exigiría un código de
    partida por diámetro, que el catálogo del alpha no tiene: el límite se declara y se rechaza.
    """
    archivo = _csv_de_filas(
        tmp_path,
        "Z-01,zanja,,,,,,,40.00,0.40,0.80,0.30,0.05,",
        "Z-02,zanja,,,,,,,10.00,0.40,0.80,0.0508,0.05,",
    )

    with pytest.raises(ValueError, match="dos diametros"):
        AdaptadorCivilTabular(codigos=CODIGOS).extraer(archivo)


def test_adaptador_tabular_balancea_dos_zanjas_del_mismo_diametro(tmp_path):
    """Con un solo diámetro el balance sí cierra: la expresión que evalúa R5 da la cantidad."""
    archivo = _csv_de_filas(
        tmp_path,
        "T-01,tanquilla,0.80,0.80,0.10,4,0.10,0.10,,,,,,",
        "Z-01,zanja,,,,,,,40.00,0.40,0.80,0.1016,0.05,",
        "Z-02,zanja,,,,,,,10.00,0.40,0.80,0.1016,0.05,",
    )

    items = AdaptadorCivilTabular(codigos=CODIGOS).extraer(archivo)
    relleno = items[-1]

    expandido = sustituir_codigos(
        relleno.especificaciones[CLAVE_BALANCE], _cantidades_por_codigo(items)
    )
    assert evaluar(expandido, {}) == relleno.cantidad


def test_adaptador_tabular_exige_una_zanja_para_el_balance_de_relleno(tmp_path):
    """Sin fila de zanja no hay diámetro con el que construir el término de tubería."""
    archivo = _csv_de_filas(tmp_path, "T-01,tanquilla,0.80,0.80,0.10,4,0.10,0.10,,,,,,")

    with pytest.raises(ValueError, match="sin una fila de zanja"):
        AdaptadorCivilTabular(codigos=CODIGOS).extraer(archivo)


def test_evaluador_rechaza_llamadas_y_atributos():
    parametros = {"a": Decimal("2")}
    with pytest.raises(ValueError):
        evaluar_regla("abs(a)", parametros)
    with pytest.raises(ValueError):
        evaluar_regla("a.bit_length", parametros)


def test_evaluador_exige_parametros():
    with pytest.raises(KeyError):
        evaluar_regla("a + b", {"a": Decimal("1")})
