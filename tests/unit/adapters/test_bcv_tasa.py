from datetime import date
from decimal import Decimal

import pytest

from adapters.bcv.formatos import cargar_formatos
from adapters.bcv.informe import FormatoNoReconocido
from adapters.bcv.libro import abrir_libro
from adapters.bcv.tasa import leer_tasa
from tests.fixtures.bcv_cuadriculas import CARPETA, campo, hoja_tasa, libro, transcripcion

D = Decimal

FUENTE = "https://www.bcv.org.ve/estadisticas/tipo-cambio-de-referencia-smc"
DESCARGA = date(2026, 10, 8)
LETRAS = {"a": 1, "b": 2, "c": 3, "d": 4}


def _leer(lib, fuente=FUENTE):
    return leer_tasa(lib, fuente=fuente, fecha_descarga=DESCARGA, trimestre_por_letra=LETRAS)


def test_el_archivo_real_da_n_hojas_y_coincide_con_la_transcripcion_a_mano():
    real = abrir_libro(CARPETA / campo("Tasa", "Archivo"))
    informe = leer_tasa(
        real,
        fuente=campo("Tasa", "Dirección"),
        fecha_descarga=date.fromisoformat(campo("Tasa", "Fecha de descarga")),
        trimestre_por_letra=cargar_formatos().trimestre_por_letra,
    )
    compra, venta = informe.series
    assert len(venta.valores) == int(campo("Tasa", "Hojas (N)"))  # PRU‑H13: N transcrito
    por_hoja = {
        v.lugar.split("!")[0]: (c, v) for c, v in zip(compra.valores, venta.valores, strict=True)
    }
    for fila in transcripcion("Tasa"):
        c, v = por_hoja[fila["Hoja"]]
        assert (v.fecha.isoformat(), c.valor, v.valor) == (
            fila["Fecha valor"],
            D(fila["Compra"]),
            D(fila["Venta"]),
        )
    # El archivo guarda 8 decimales (860.1753); el literal 860,18 del BCV es su redondeo a 2.
    hoy = next(v for v in venta.valores if v.fecha == date(2026, 10, 1))
    assert hoy.valor == D("860.1753") and hoy.valor.quantize(D("0.01")) == D("860.18")


def test_hoja_nueva_o_renombrada_no_tumba_el_archivo():
    """[Foco 1] una hoja sin la etiqueta se rechaza; una renombrada vale por contenido."""
    resumen = libro(hoja_tasa("Resumen", etiqueta="Notas"), hoja_tasa("hoja renombrada"))
    informe = _leer(resumen)
    assert [r.lugar for r in informe.rechazos] == ["Resumen"]
    assert "Fecha Valor" in informe.rechazos[0].motivo
    assert informe.series[1].valores[0].valor == D("860.18")


@pytest.mark.parametrize(
    "hojas, motivo",
    [
        ((hoja_tasa("a"), hoja_tasa("b")), "repetida"),
        ((hoja_tasa("a", fecha="15/05/2026"),), "fuera del trimestre"),
        ((hoja_tasa("a", fecha="09/10/2026"),), "posterior a la descarga"),
        ((hoja_tasa("a", venta="860,18"),), "no numerico"),
        ((hoja_tasa("a", compra=D("0")),), "mayor que cero"),
        ((hoja_tasa("a", codigo="EUR"),), "fila USD"),
    ],
)
def test_cuadriculas_negativas_se_rechazan_con_su_motivo(hojas, motivo):
    rechazos = _leer(libro(*hojas)).rechazos
    assert rechazos and motivo in rechazos[-1].motivo


def test_sin_ninguna_etiqueta_se_rechaza_el_archivo_y_dominio_ajeno_tambien():
    with pytest.raises(FormatoNoReconocido, match="Fecha Valor"):
        _leer(libro(hoja_tasa("x", etiqueta="Otra")))
    with pytest.raises(FormatoNoReconocido, match="bcv.org.ve"):
        _leer(libro(hoja_tasa("x")), fuente="https://bcv.org.ve.ejemplo.com/x.xls")


def test_nombre_fuera_de_patron_advierte_y_compra_mayor_que_venta_advierte():
    informe = _leer(libro(hoja_tasa("x", compra=D("861")), archivo="tasas.xls"))
    assert any("2e" in a for a in informe.advertencias)
    assert any("compra" in a for a in informe.advertencias)
