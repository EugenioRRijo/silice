"""Pruebas de sensibilidad de umbrales viales (`aplicacion/sensibilidad_umbrales.py`)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from adapters.vial import constantes as constantes_viales
from adapters.vial import derivacion as derivacion_vial
from adapters.vial import reglas as reglas_viales
from aplicacion.sensibilidad_umbrales import (
    Fila,
    barrido,
    con_umbral,
    umbrales_supuestos,
)
from core.contracts.verificacion import Hallazgo, Severidad
from scripts import sensibilidad_umbrales as script_sensibilidad


def _hallazgo_vr(
    regla: str,
    origen: str,
    descripcion: str = "diferencia",
    severidad: Severidad = Severidad.ERROR,
) -> Hallazgo:
    return Hallazgo(
        regla=regla,
        severidad=severidad,
        descripcion=descripcion,
        origen_ids=(origen,),
    )


def test_umbrales_supuestos_incluye_solo_los_ocho_supuestos_declarados() -> None:
    esperados = {
        "FRACCION_PINTADA_DISCONTINUA",
        "TOLERANCIA_CARPETA",
        "DENSIDAD_LIGANTE_KG_L",
        "FRACCION_RESIDUAL_EMULSION",
        "TOLERANCIA_TRANSPORTE",
        "ANCHO_LINEA_SUPUESTO_CM",
        "PINTURA_POR_DEFECTO_L_KM",
        "TOLERANCIA_CANTIDAD_CONCILIADA",
    }
    assert set(umbrales_supuestos()) == esperados


def test_con_umbral_sustituye_y_restaura_en_constantes_reglas_y_derivacion() -> None:
    original_carpeta = constantes_viales.TOLERANCIA_CARPETA
    original_ancho = constantes_viales.ANCHO_LINEA_SUPUESTO_CM

    with con_umbral("TOLERANCIA_CARPETA", Decimal("0.5")) as sustituida:
        assert sustituida.valor == Decimal("0.0025")
        assert constantes_viales.TOLERANCIA_CARPETA.valor == Decimal("0.0025")
        assert reglas_viales.TOLERANCIA_CARPETA.valor == Decimal("0.0025")
        assert constantes_viales.TOLERANCIA_CARPETA.id == original_carpeta.id

    assert constantes_viales.TOLERANCIA_CARPETA is original_carpeta
    assert reglas_viales.TOLERANCIA_CARPETA is original_carpeta

    with con_umbral("ANCHO_LINEA_SUPUESTO_CM", Decimal("1.5")):
        assert constantes_viales.ANCHO_LINEA_SUPUESTO_CM.valor == Decimal("15.0")
        assert reglas_viales.ANCHO_LINEA_SUPUESTO_CM.valor == Decimal("15.0")
        assert derivacion_vial.ANCHO_LINEA_SUPUESTO_CM.valor == Decimal("15.0")

    assert constantes_viales.ANCHO_LINEA_SUPUESTO_CM is original_ancho
    assert reglas_viales.ANCHO_LINEA_SUPUESTO_CM is original_ancho
    assert derivacion_vial.ANCHO_LINEA_SUPUESTO_CM is original_ancho


def test_con_umbral_restaura_el_valor_aunque_haya_excepcion() -> None:
    original = constantes_viales.TOLERANCIA_TRANSPORTE
    with pytest.raises(RuntimeError, match="fallo inducido"):
        with con_umbral("TOLERANCIA_TRANSPORTE", Decimal("1.5")):
            assert constantes_viales.TOLERANCIA_TRANSPORTE.valor == Decimal("0.0075")
            assert reglas_viales.TOLERANCIA_TRANSPORTE.valor == Decimal("0.0075")
            raise RuntimeError("fallo inducido")
    assert constantes_viales.TOLERANCIA_TRANSPORTE is original
    assert reglas_viales.TOLERANCIA_TRANSPORTE is original


def test_con_umbral_rechaza_no_supuesto_desconocido_y_factor_no_positivo() -> None:
    with pytest.raises(ValueError, match="supuesto"):
        with con_umbral("TOLERANCIA_ASFALTO_PUNTOS", Decimal("0.5")):
            pass
    with pytest.raises(ValueError, match="constante"):
        with con_umbral("UMBRAL_QUE_NO_EXISTE", Decimal("0.5")):
            pass
    with pytest.raises(ValueError, match="factor"):
        with con_umbral("TOLERANCIA_CARPETA", Decimal("0")):
            pass
    with pytest.raises(ValueError, match="factor"):
        with con_umbral("TOLERANCIA_CARPETA", Decimal("-1")):
            pass


def test_barrido_con_auditor_falso_que_depende_del_umbral() -> None:
    def auditor_falso() -> list[Hallazgo]:
        tol = Decimal(reglas_viales.TOLERANCIA_CARPETA.valor)
        hallazgos = [
            # Hallazgo no VR: debe ignorarse al contar los VR.
            Hallazgo(regla="R1", severidad=Severidad.ADVERTENCIA, descripcion="manual"),
        ]
        if Decimal("0.004") > tol:
            hallazgos.append(_hallazgo_vr("VR1", "tramo:T1:capa:1", f"tol {tol}"))
        if Decimal("0.006") > tol:
            hallazgos.append(_hallazgo_vr("VR1", "tramo:T2:capa:1", f"tol {tol}"))
        return hallazgos

    filas = barrido(auditor_falso, ["TOLERANCIA_CARPETA"])
    assert filas == [
        Fila("TOLERANCIA_CARPETA", Decimal("0.5"), base=1, ahora=2, cambian=1),
        Fila("TOLERANCIA_CARPETA", Decimal("0.75"), base=1, ahora=2, cambian=1),
        Fila("TOLERANCIA_CARPETA", Decimal("1.25"), base=1, ahora=0, cambian=1),
        Fila("TOLERANCIA_CARPETA", Decimal("1.5"), base=1, ahora=0, cambian=1),
    ]


def test_barrido_cuenta_reemplazo_y_ignora_cambio_solo_de_texto() -> None:
    def auditor_falso() -> list[Hallazgo]:
        tol = Decimal(reglas_viales.TOLERANCIA_CARPETA.valor)
        if tol < Decimal("0.005"):
            return [_hallazgo_vr("VR1", "tramo:T2:capa:1", f"nuevo texto {tol}")]
        return [_hallazgo_vr("VR1", "tramo:T1:capa:1", f"mismo hallazgo {tol}")]

    filas = barrido(auditor_falso, ["TOLERANCIA_CARPETA"], factores=(0.5, 1.5))
    assert filas == [
        Fila("TOLERANCIA_CARPETA", Decimal("0.5"), base=1, ahora=1, cambian=2),
        Fila("TOLERANCIA_CARPETA", Decimal("1.5"), base=1, ahora=1, cambian=0),
    ]


def test_barrido_rechaza_umbral_que_no_es_supuesto() -> None:
    with pytest.raises(ValueError, match="supuesto"):
        barrido(lambda: [], ["PINTURA_MIN_L_KM"])


def test_script_sensibilidad_imprime_tabla_markdown_con_coma_decimal(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = script_sensibilidad.main([])
    assert codigo == 0
    salida = capsys.readouterr().out
    assert "| Umbral | Factor | Base (VR) | Ahora (VR) | Cambian |" in salida
    assert "| 0,50 |" in salida and "| 0,75 |" in salida
    assert "| 1,25 |" in salida and "| 1,50 |" in salida
