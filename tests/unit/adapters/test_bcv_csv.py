"""CSV canonico de series (S1 §7.3; UC-17 2f): las mismas validaciones de fecha, valor y repeticion
que los .xls, con la fuente obligatoria por fila."""

import hashlib
from datetime import date
from decimal import Decimal

import pytest

from adapters.bcv.csv_canonico import COLUMNAS_CSV, leer_csv_canonico
from adapters.bcv.informe import FormatoNoReconocido

D = Decimal

D = Decimal
DESCARGA = date(2026, 10, 8)
FUENTE = "https://www.bcv.org.ve/estadisticas/insumos-de-la-construccion"
BUENAS = f"IIC-GENERAL,2026-01-01,100.5,no,{FUENTE}\nIIC-GENERAL,2026-02-01,101.25,si,{FUENTE}\n"


def _csv(tmp_path, cuerpo, encabezado=",".join(COLUMNAS_CSV)):
    ruta = tmp_path / "serie.csv"
    ruta.write_text(f"{encabezado}\n{cuerpo}", encoding="utf-8")
    return ruta


def test_las_filas_buenas_dan_una_serie_con_su_huella_y_su_fuente(tmp_path):
    ruta = _csv(tmp_path, BUENAS)
    informe = leer_csv_canonico(ruta, fecha_descarga=DESCARGA)
    (serie,) = informe.series
    assert serie.clave == "IIC-GENERAL" and (serie.unidad, serie.periodicidad) == ("", "")
    assert [(v.fecha, v.valor, v.provisional) for v in serie.valores] == [
        (date(2026, 1, 1), D("100.5"), False),
        (date(2026, 2, 1), D("101.25"), True),
    ]
    assert informe.huella == hashlib.sha256(ruta.read_bytes()).hexdigest()
    assert (informe.fuente, informe.filas_leidas, informe.rechazos) == (FUENTE, 2, ())


@pytest.mark.parametrize(
    "fila, motivo",
    [
        (f"IIC-GENERAL,01/03/2026,100,no,{FUENTE}", "AAAA-MM-DD"),
        (f'IIC-GENERAL,2026-03-01,"1,5",no,{FUENTE}', "use punto"),
        (f"IIC-GENERAL,2026-03-01,0,no,{FUENTE}", "mayor que cero"),
        ("IIC-GENERAL,2026-03-01,100,no,", "fuente"),
        (f"IIC-GENERAL,2026-02-01,102,no,{FUENTE}", "repetido"),
        (f"IIC-GENERAL,2026-11-01,100,no,{FUENTE}", "posterior a la descarga"),
        (f"IIC-GENERAL,2026-03-01,100,quizas,{FUENTE}", "provisional"),
        (f",2026-03-01,100,no,{FUENTE}", "serie"),
    ],
)
def test_cada_fila_mala_se_rechaza_con_su_motivo_y_las_buenas_siguen(tmp_path, fila, motivo):
    informe = leer_csv_canonico(_csv(tmp_path, BUENAS + fila + "\n"), fecha_descarga=DESCARGA)
    assert len(informe.series[0].valores) == 2
    (rechazo,) = informe.rechazos
    assert rechazo.lugar == "serie.csv:4" and motivo in rechazo.motivo


def test_sin_las_cinco_columnas_se_rechaza_el_archivo(tmp_path):
    ruta = _csv(tmp_path, "IIC,2026-01-01,1,no\n", "serie,fecha,valor,provisional")
    with pytest.raises(FormatoNoReconocido, match="fuente"):
        leer_csv_canonico(ruta, fecha_descarga=DESCARGA)
