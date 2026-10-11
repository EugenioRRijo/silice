"""INPC mensual del BCV (S1 §7; UC-17 2a, 2b): el archivo real contra la transcripcion a mano de
FUENTE.md (PRU-H13) y cuadriculas negativas sin escribir .xls."""

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.bcv.formatos import RUTA_FORMATOS, FormatoMensual, cargar_formatos
from adapters.bcv.informe import FormatoNoReconocido
from adapters.bcv.inpc import leer_inpc
from adapters.bcv.libro import Hoja, abrir_libro
from tests.fixtures.bcv_cuadriculas import CARPETA, campo, libro, transcripcion

D = Decimal

D = Decimal
FUENTE = "https://www.bcv.org.ve/estadisticas/consumidor"
DESCARGA = date(2026, 10, 8)
#: Formato de las cuadriculas de esta prueba (no el del archivo real, que viene de formatos.json).
FORMATO = FormatoMensual("INPC", "Período", "Índice general", "(*)", "base ficticia")
BCV_FORMATOS = Path(__file__).resolve().parents[3] / "docs" / "fuentes" / "bcv_formatos.md"
TITULO_FORMATOS = "## Formatos para `adapters/bcv/formatos.json`"


def _hoja(*filas, nombre="INPC", encabezado=("Período", "Índice general")):
    return Hoja(nombre, (("BANCO CENTRAL DE VENEZUELA", None), encabezado, *filas))


def _leer(*hojas):
    return leer_inpc(
        libro(*hojas, archivo="inpc.xls"), fuente=FUENTE, fecha_descarga=DESCARGA, formato=FORMATO
    )


def test_el_archivo_real_coincide_con_la_transcripcion_a_mano():
    real = abrir_libro(CARPETA / campo("INPC", "Archivo"))
    informe = leer_inpc(
        real,
        fuente=campo("INPC", "Dirección"),
        fecha_descarga=date.fromisoformat(campo("INPC", "Fecha de descarga")),
        formato=cargar_formatos().inpc,
    )
    (serie,) = informe.series
    assert (serie.clave, serie.unidad, serie.periodicidad) == (
        "inpc_general",
        "indice_bs",
        "mensual",
    )
    por_mes = {v.fecha.strftime("%Y-%m"): v for v in serie.valores}
    for fila in transcripcion("INPC"):
        valor = por_mes[fila["Mes"]]
        assert (valor.valor, valor.provisional) == (D(fila["Valor"]), fila["Provisional"] == "sí")


@pytest.mark.parametrize(
    "periodo", ["Ene-2026", "enero 2026", "01/2026", "2026-01", date(2026, 1, 1)]
)
def test_cada_forma_del_periodo_da_el_primer_dia_del_mes(periodo):
    (valor,) = _leer(_hoja((periodo, D("100.5")))).series[0].valores
    assert (valor.fecha, valor.valor, valor.provisional) == (date(2026, 1, 1), D("100.5"), False)


def test_la_marca_de_provisional_se_guarda_por_valor():
    informe = _leer(_hoja(("Ene-2026", D("100.5")), ("Feb-2026 (*)", D("101.2"))))
    assert [v.provisional for v in informe.series[0].valores] == [False, True]
    assert informe.provisionales == 1


def test_sin_la_hoja_o_sin_un_encabezado_se_rechaza_el_archivo_nombrandolo():
    with pytest.raises(FormatoNoReconocido, match="INPC"):
        _leer(_hoja(("Ene-2026", D("100.5")), nombre="Otra"))
    with pytest.raises(FormatoNoReconocido, match="Índice general"):
        _leer(_hoja(("Ene-2026", D("100.5")), encabezado=("Período", "Variación")))
    with pytest.raises(FormatoNoReconocido, match="Período"):
        _leer(_hoja(("Ene-2026", D("100.5")), encabezado=("Mes", "Índice general")))


@pytest.mark.parametrize(
    "filas, motivo",
    [
        ((("Ene-2026", D("100")), ("Ene-2026", D("101"))), "repetido"),
        ((("Ene-2026", D("100")), ("Mar-2026", D("102"))), "no consecutivo"),
        ((("Nov-2026", D("100")),), "posterior a la descarga"),
        ((("Ene-2026", "100,5"),), "no numerico"),
        ((("Ene-2026", D("0")),), "mayor que cero"),
        ((("Trimestre 1", D("100")),), "ilegible"),
    ],
)
def test_filas_negativas_se_rechazan_con_su_motivo_y_las_demas_siguen(filas, motivo):
    informe = _leer(_hoja(*filas))
    assert informe.rechazos and motivo in informe.rechazos[-1].motivo
    assert informe.filas_leidas == len(filas)
    assert len(informe.series[0].valores) == len(filas) - 1


def test_formatos_json_copia_bcv_formatos_md():
    seccion = BCV_FORMATOS.read_text(encoding="utf-8").split(TITULO_FORMATOS)[1]
    filas = re.findall(r"^\| `([a-z_.]+)` \| `(.+)` \|$", seccion.split("\n## ")[0], re.M)
    assert filas
    datos = json.loads(RUTA_FORMATOS.read_text(encoding="utf-8"))
    for clave, valor in filas:
        grupo, nombre = clave.split(".", 1)
        assert datos[grupo][nombre] == json.loads(valor), clave
    assert sum(len(grupo) for grupo in datos.values()) == len(filas)


# --- Disposicion real de 4_5_7.xls (docs/fuentes/bcv_formatos.md): el ano en una fila propia y
# debajo los nombres de mes, del mas reciente al mas antiguo. ---
ANIOS = FormatoMensual("INPC", "", "Indice", "(*)", "Diciembre 2007 = 100", "anio_en_filas")


def _hoja_anios(*filas, nombre="INPC"):
    return Hoja(nombre, (("INDICE NACIONAL", None, None), (None, "Indice", "Var%"), *filas))


def _leer_anios(*filas):
    informe = leer_inpc(
        libro(_hoja_anios(*filas), archivo="inpc.xls"),
        fuente=FUENTE,
        fecha_descarga=DESCARGA,
        formato=ANIOS,
    )
    return informe, informe.series[0].valores


def test_el_ano_en_su_fila_se_ordena_de_antiguo_a_reciente_y_marca_provisional_por_ano():
    informe, valores = _leer_anios(
        ("2026(*)", None, None),
        ("Febrero", D("101.2"), D("1")),
        ("Enero", D("100.5"), D("2")),
        (None, None, None),
        (D("2025"), None, None),
        ("Diciembre", D("99"), D("3")),
    )
    assert [(v.fecha, v.valor, v.provisional) for v in valores] == [
        (date(2025, 12, 1), D("99"), False),
        (date(2026, 1, 1), D("100.5"), True),
        (date(2026, 2, 1), D("101.2"), True),
    ]
    assert informe.filas_leidas == 3 and not informe.rechazos


def test_meses_consecutivos_entre_anos_y_provisional_solo_donde_hay_asterisco():
    _, valores = _leer_anios(
        ("2026(*)", None, None),
        ("Enero", D("100.5"), None),
        ("2025", None, None),
        ("Diciembre", D("99"), None),
    )
    assert [(v.fecha, v.provisional) for v in valores] == [
        (date(2025, 12, 1), False),
        (date(2026, 1, 1), True),
    ]


@pytest.mark.parametrize(
    "filas, motivo",
    [
        ((("Enero", D("100")),), "sin fila de ano"),
        ((("2026", None), ("Enero", D("100")), ("Enero", D("101"))), "repetido"),
        ((("2026", None), ("Marzo", D("102")), ("Enero", D("100"))), "no consecutivo"),
        ((("2026", None), ("Quincena", D("100"))), "ilegible"),
        ((("2026", None), ("Enero", "100,5")), "no numerico"),
        ((("2027", None), ("Enero", D("100"))), "posterior a la descarga"),
    ],
)
def test_filas_negativas_del_formato_por_ano_se_rechazan_con_su_motivo(filas, motivo):
    informe, valores = _leer_anios(*((a, b, None) for a, b in filas))
    assert informe.rechazos and any(motivo in r.motivo for r in informe.rechazos)
    assert len(valores) < len(filas)


def test_una_nota_al_pie_sin_valor_no_es_un_rechazo_pero_un_mes_sin_valor_si():
    informe, valores = _leer_anios(
        ("2026", None, None),
        ("Enero", D("100.5"), None),
        ("Febrero", None, None),
        ("Fuente: B.C.V. - I.N.E.", None, None),
    )
    assert [r.motivo for r in informe.rechazos] == ["valor no numerico"]
    assert len(valores) == 1
