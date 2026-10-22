"""Lector de reportes de bascula (Tarea 4.6; RT-S4-5, RT-S4-6, RNF-25).

EJEMPLO CONSTRUIDO. Los valores esperados estan escritos a mano a partir de
`tests/fixtures/bascula/ORACULO.md`; los generadores de `construir.py` solo producen las ENTRADAS.

Discrepancia declarada con el oraculo (fila 6, TCK-006, GRAVA9): el lector no conoce el catalogo de
materiales, asi que NO la marca; la devuelve como leida y la importacion (Tarea 4.7) decide
«material desconocido». Por eso aqui el basico da 3 leidos y 3 dudosos, no 2 y 4.
"""

from __future__ import annotations

import hashlib
import io
from datetime import date, datetime
from decimal import Decimal

import openpyxl
import pytest

from produccion.conectores import bascula
from produccion.conectores.bascula import (
    LecturaBascula,
    PesajeDudoso,
    PesajeLeido,
    ReporteRechazado,
    leer,
)
from produccion.conectores.detector_columnas import MapeoNecesario
from produccion.fuentes import MAX_COLUMNAS, MAX_FILAS
from tests.fixtures.bascula import construir

HOY = date(2026, 10, 18)  # fecha de referencia del oraculo (la manda el cliente, no el reloj)
CABECERA = "Ticket;Fecha;Placa;Cliente;Material;Bruto (kg);Tara (kg);Neto (kg)"


def _csv(*lineas: str, cabecera: str = CABECERA) -> bytes:
    return ("\n".join([cabecera, *lineas]) + "\n").encode("utf-8")


def _linea(
    ticket="TCK-900",
    fecha="2026-10-15",
    material="ARENA",
    bruto="40000",
    tara="15000",
    neto="25000",
):
    return f"{ticket};{fecha};EJ-900;Cliente Ejemplo A;{material};{bruto};{tara};{neto}"


def _xlsx(filas: list[list[object]]) -> bytes:
    libro = openpyxl.Workbook()
    hoja = libro.active
    assert hoja is not None
    for fila in filas:
        hoja.append(fila)
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


# Oraculo a mano, ORACULO.md §1 (referencia 2026-10-18, pesos en kg -> toneladas). La fila 6 se lee.
LEIDOS_BASICO = (
    PesajeLeido(
        fila=2,
        ticket="TCK-001",
        fecha=date(2026, 10, 15),
        placa="EJ-001",
        cliente="Cliente Ejemplo A",
        material="ARENA",
        bruto_t=Decimal("42.5"),
        tara_t=Decimal("14.2"),
        neto_t=Decimal("28.300"),
    ),
    PesajeLeido(
        fila=3,
        ticket="TCK-002",
        fecha=date(2026, 10, 15),
        placa="EJ-002",
        cliente="Cliente Ejemplo B",
        material="PIEDRA34",
        bruto_t=Decimal("38.0"),
        tara_t=Decimal("13.5"),
        neto_t=Decimal("24.5"),
    ),
    PesajeLeido(
        fila=7,
        ticket="TCK-006",
        fecha=date(2026, 10, 17),
        placa="EJ-006",
        cliente="Cliente Ejemplo C",
        material="GRAVA9",
        bruto_t=Decimal("40"),
        tara_t=Decimal("15"),
        neto_t=Decimal("25"),
    ),
)
DUDOSOS_BASICO = (
    PesajeDudoso(
        fila=4,
        ticket="TCK-003",
        fecha_texto="2026-10-16",
        placa="EJ-003",
        material="ARENA",
        bruto_texto="42000",
        tara_texto="45000",
        neto_texto="-3000",
        motivo="tara mayor o igual que el bruto",
    ),
    PesajeDudoso(
        fila=5,
        ticket="TCK-004",
        fecha_texto="2026-10-16",
        placa="EJ-004",
        material="ARENA",
        bruto_texto="40000",
        tara_texto="15000",
        neto_texto="20000",
        motivo="neto distinto de bruto − tara",
    ),
    PesajeDudoso(
        fila=6,
        ticket="TCK-005",
        fecha_texto="2026-12-31",
        placa="EJ-005",
        material="PIEDRA34",
        bruto_texto="40000",
        tara_texto="15000",
        neto_texto="25000",
        motivo="fecha futura",
    ),
)


@pytest.mark.parametrize(
    ("datos", "nombre"),
    [(construir.csv_basico(), "basico.csv"), (construir.xlsx_basico(), "basico.xlsx")],
)
def test_pesajes_del_oraculo(datos, nombre):
    lectura = leer(datos, nombre, fecha_referencia=HOY)
    assert lectura.pesajes == LEIDOS_BASICO
    assert lectura.dudosos == DUDOSOS_BASICO
    assert isinstance(lectura, LecturaBascula)
    assert lectura.huella == hashlib.sha256(datos).hexdigest()


def test_xlsx_y_csv_dan_lo_mismo():
    en_csv = leer(construir.csv_basico(), "r.csv", fecha_referencia=HOY)
    en_xlsx = leer(construir.xlsx_basico(), "r.xlsx", fecha_referencia=HOY)
    assert en_csv.pesajes == en_xlsx.pesajes
    assert en_csv.dudosos == en_xlsx.dudosos
    assert en_csv.huella != en_xlsx.huella


def test_la_huella_es_el_sha256_de_los_bytes():
    datos = construir.csv_basico()
    assert leer(datos, "a.csv", fecha_referencia=HOY).huella == hashlib.sha256(datos).hexdigest()
    otro = datos + b"\n"
    assert leer(otro, "a.csv", fecha_referencia=HOY).huella == hashlib.sha256(otro).hexdigest()


def test_sin_unidad_no_se_importa():
    with pytest.raises(ReporteRechazado) as error:
        leer(construir.xlsx_sin_unidad(), "r.xlsx", fecha_referencia=HOY)
    assert str(error.value) == "Indique si los pesos están en kg o en t."
    assert isinstance(error.value, ValueError)


def test_con_unidad_kg_dada_el_sin_unidad_es_igual_al_basico():
    lectura = leer(construir.xlsx_sin_unidad(), "r.xlsx", fecha_referencia=HOY, unidad_peso="kg")
    assert lectura.pesajes == LEIDOS_BASICO
    assert lectura.dudosos == DUDOSOS_BASICO


def test_con_unidad_t_dada_los_numeros_son_toneladas():
    lectura = leer(construir.xlsx_sin_unidad(), "r.xlsx", fecha_referencia=HOY, unidad_peso="t")
    primero = lectura.pesajes[0]
    assert (primero.bruto_t, primero.tara_t, primero.neto_t) == (
        Decimal("42500"),
        Decimal("14200"),
        Decimal("28300"),
    )


def test_la_unidad_dada_manda_sobre_la_del_encabezado():
    lectura = leer(construir.csv_basico(), "r.csv", fecha_referencia=HOY, unidad_peso="t")
    assert lectura.pesajes[0].bruto_t == Decimal("42500")


def test_unidad_invalida_se_rechaza():
    with pytest.raises(ReporteRechazado, match="kg o en t"):
        leer(construir.csv_basico(), "r.csv", fecha_referencia=HOY, unidad_peso="lb")


def test_numeros_con_coma_y_punto():
    lectura = leer(construir.csv_coma_decimal(), "r.csv", fecha_referencia=HOY)
    uno, dos = lectura.pesajes
    # ORACULO.md §3: 1.234,56 y 1,234.56 son 1234,56 kg = 1,23456 t; 234,56 kg = 0,23456 t;
    # 1000,00 kg = 1 t.
    assert (uno.ticket, uno.bruto_t, uno.tara_t, uno.neto_t) == (
        "TCK-101",
        Decimal("1.23456"),
        Decimal("0.23456"),
        Decimal("1"),
    )
    assert (dos.ticket, dos.bruto_t, dos.tara_t, dos.neto_t) == (
        "TCK-102",
        Decimal("1.23456"),
        Decimal("0.23456"),
        Decimal("1"),
    )
    assert lectura.dudosos == (
        PesajeDudoso(
            fila=4,
            ticket="TCK-103",
            fecha_texto="2026-10-15",
            placa="EJ-103",
            material="ARENA",
            bruto_texto="42500",
            tara_texto="14200",
            neto_texto="28,300",
            motivo="número ambiguo",
        ),
    )


def _bruto_leido(texto: str) -> Decimal | str:
    """Lee una fila con `texto` como bruto (tara 0, neto igual) y devuelve bruto_t o el motivo."""
    lectura = leer(_csv(_linea(bruto=texto, tara="0", neto=texto)), "r.csv", fecha_referencia=HOY)
    if lectura.pesajes:
        return lectura.pesajes[0].bruto_t
    return lectura.dudosos[0].motivo


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("1.234.567", Decimal("1234.567")),  # solo puntos de miles: 1 234 567 kg
        ("1,234,567", Decimal("1234.567")),  # solo comas de miles
        ("1.234.567,5", Decimal("1234.5675")),
        ("12,5", Decimal("0.0125")),  # un separador y dos/una cifras despues: decimal
        ("12.5", Decimal("0.0125")),
        ("1.234,5", Decimal("1.2345")),
        ("1,2345", Decimal("0.0012345")),
        ("0,500", Decimal("0.0005")),  # un grupo de miles no empieza en cero: es decimal
        ("40000", Decimal("40")),
        ("12345,678", Decimal("12.345678")),  # cuatro o mas cifras antes: no puede ser de miles
        ("-5", "peso negativo"),
        ("1.234", "número ambiguo"),
        ("1,234", "número ambiguo"),
        ("999,999", "número ambiguo"),
        ("1.23.4", "peso ilegible"),
        ("12,3,4", "peso ilegible"),
        ("1,2.3,4", "peso ilegible"),
        ("abc", "peso ilegible"),
        ("12a", "peso ilegible"),
        ("1.,2", "peso ilegible"),
        ("", "peso ilegible"),
        (",5", "peso ilegible"),
    ],
)
def test_formas_de_escribir_un_numero(texto, esperado):
    assert _bruto_leido(texto) == esperado


def test_celdas_nativas_de_xlsx_no_son_ambiguas():
    # 28.3 y 1234.56 nativos (flotantes): exactos y nunca «numero ambiguo».
    datos = _xlsx(
        [
            ["Ticket", "Fecha", "Material", "Bruto (kg)", "Tara (kg)", "Neto (kg)"],
            ["TCK-1", "2026-10-15", "ARENA", 1234.56, 234.56, 1000],
            ["TCK-2", "2026-10-15", "ARENA", 28300, 0, 28300],
        ]
    )
    lectura = leer(datos, "r.xlsx", fecha_referencia=HOY)
    assert lectura.dudosos == ()
    assert [(p.ticket, p.bruto_t, p.tara_t, p.neto_t) for p in lectura.pesajes] == [
        ("TCK-1", Decimal("1.23456"), Decimal("0.23456"), Decimal("1")),
        ("TCK-2", Decimal("28.3"), Decimal("0"), Decimal("28.3")),
    ]
    assert all(p.placa == "" and p.cliente == "" for p in lectura.pesajes)


def test_fechas_nativas_y_en_dia_mes_anio():
    datos = _xlsx(
        [
            ["Ticket", "Fecha", "Material", "Neto (kg)"],
            ["TCK-1", datetime(2026, 10, 15, 8, 30), "ARENA", 1000],
            ["TCK-2", "16/10/2026", "ARENA", 1000],
            ["TCK-3", "2026-10-17 06:15:00", "ARENA", 1000],
        ]
    )
    lectura = leer(datos, "r.xlsx", fecha_referencia=HOY)
    assert [(p.ticket, p.fecha) for p in lectura.pesajes] == [
        ("TCK-1", date(2026, 10, 15)),
        ("TCK-2", date(2026, 10, 16)),
        ("TCK-3", date(2026, 10, 17)),
    ]


def test_fecha_ilegible_va_a_la_bandeja_con_su_texto():
    lectura = leer(_csv(_linea(fecha="31/31/2026")), "r.csv", fecha_referencia=HOY)
    assert lectura.pesajes == ()
    assert [(d.fecha_texto, d.motivo) for d in lectura.dudosos] == [
        ("31/31/2026", "fecha ilegible")
    ]


def test_la_fecha_de_referencia_no_es_futura_pero_el_dia_siguiente_si():
    lectura = leer(
        _csv(_linea("T-1", fecha="2026-10-18"), _linea("T-2", fecha="2026-10-19")),
        "r.csv",
        fecha_referencia=HOY,
    )
    assert [p.ticket for p in lectura.pesajes] == ["T-1"]
    assert [(d.ticket, d.motivo) for d in lectura.dudosos] == [("T-2", "fecha futura")]
    # Con otra referencia cambia el resultado: el lector no usa el reloj.
    despues = leer(
        _csv(_linea("T-2", fecha="2026-10-19")), "r.csv", fecha_referencia=date(2026, 10, 19)
    )
    assert [p.ticket for p in despues.pesajes] == ["T-2"]


def test_neto_ausente_se_calcula_como_bruto_menos_tara():
    sin_columna = b"Ticket;Fecha;Material;Bruto (kg);Tara (kg)\nT-1;2026-10-15;ARENA;42500;14200\n"
    lectura = leer(sin_columna, "r.csv", fecha_referencia=HOY)
    assert [(p.bruto_t, p.tara_t, p.neto_t) for p in lectura.pesajes] == [
        (Decimal("42.5"), Decimal("14.2"), Decimal("28.3"))
    ]
    celda_vacia = _csv(_linea("T-1", bruto="42500", tara="14200", neto=""))
    lectura = leer(celda_vacia, "r.csv", fecha_referencia=HOY)
    assert [p.neto_t for p in lectura.pesajes] == [Decimal("28.3")]


def test_solo_neto_sin_bruto_ni_tara():
    datos = b"Ticket;Fecha;Material;Peso Neto (kg)\nT-1;2026-10-15;ARENA;28300\n"
    lectura = leer(datos, "r.csv", fecha_referencia=HOY)
    assert [(p.bruto_t, p.tara_t, p.neto_t) for p in lectura.pesajes] == [
        (Decimal("0"), Decimal("0"), Decimal("28.3"))
    ]


def test_ticket_repetido_en_el_archivo():
    datos = _csv(
        _linea("T-1", bruto="40000", tara="15000", neto="25000"),
        _linea("T-2"),
        _linea("T-1", bruto="41000", tara="15000", neto="26000"),
        _linea("T-3", fecha="2027-01-01"),
        _linea("T-3"),
    )
    lectura = leer(datos, "r.csv", fecha_referencia=HOY)
    assert [(p.fila, p.ticket) for p in lectura.pesajes] == [(2, "T-1"), (3, "T-2")]
    # El primero se lee; el segundo T-1 es repetido. El primer T-3 es dudoso por su fecha y el
    # segundo, aunque coherente, sigue siendo repetido: la primera fila reclama el ticket.
    assert [(d.fila, d.ticket, d.motivo) for d in lectura.dudosos] == [
        (4, "T-1", "ticket repetido en el archivo"),
        (5, "T-3", "fecha futura"),
        (6, "T-3", "ticket repetido en el archivo"),
    ]


def test_un_ticket_se_compara_sin_espacios_en_los_bordes():
    lectura = leer(_csv(_linea(" T-1 "), _linea("T-1")), "r.csv", fecha_referencia=HOY)
    assert [p.ticket for p in lectura.pesajes] == ["T-1"]
    assert [d.motivo for d in lectura.dudosos] == ["ticket repetido en el archivo"]


def test_filas_en_blanco_se_saltan_pero_cuentan_en_la_numeracion():
    datos = _csv(_linea("T-1"), ";;;;;;;", "", _linea("T-2"))
    lectura = leer(datos, "r.csv", fecha_referencia=HOY)
    assert [(p.fila, p.ticket) for p in lectura.pesajes] == [(2, "T-1"), (5, "T-2")]
    assert lectura.dudosos == ()


# Orden de reglas (documentado en el docstring de bascula.py): la primera que salta es la unica.
ORDEN_DE_REGLAS = [
    # (linea que falla ESA regla y todas las siguientes, motivo esperado)
    (_linea("", fecha="x", material="", bruto="abc", tara="9", neto="1"), "falta el ticket"),
    (
        _linea("DUP", fecha="x", material="", bruto="abc", tara="9", neto="1"),
        "ticket repetido en el archivo",
    ),
    (_linea("T-3", fecha="x", material="", bruto="abc", tara="9", neto="1"), "fecha ilegible"),
    (_linea("T-4", fecha="2027-01-01", material="", bruto="abc"), "fecha futura"),
    (_linea("T-5", material="", bruto="abc", tara="9", neto="1"), "falta el material"),
    (_linea("T-6", bruto="abc", tara="1,234", neto="1"), "peso ilegible"),
    (_linea("T-7", bruto="1,234", tara="abc", neto="1"), "número ambiguo"),
    (_linea("T-8", bruto="1,234", tara="-5", neto="1"), "número ambiguo"),
    (_linea("T-9", bruto="40000", tara="-5", neto="40005"), "peso negativo"),
    (_linea("T-10", bruto="-20", tara="-10", neto="-10"), "peso negativo"),
    (_linea("T-11", bruto="40000", tara="45000", neto="1"), "tara mayor o igual que el bruto"),
    (_linea("T-12", bruto="40000", tara="40000", neto="0"), "tara mayor o igual que el bruto"),
    (_linea("T-13", bruto="40000", tara="15000", neto="1"), "neto distinto de bruto − tara"),
]


def test_orden_de_reglas():
    # La primera fila tambien lleva ticket DUP para que la quinta lo repita.
    primero = _linea("DUP")
    datos = _csv(primero, *(linea for linea, _ in ORDEN_DE_REGLAS))
    lectura = leer(datos, "r.csv", fecha_referencia=HOY)
    assert [p.ticket for p in lectura.pesajes] == ["DUP"]
    assert [d.motivo for d in lectura.dudosos] == [motivo for _, motivo in ORDEN_DE_REGLAS]


def test_una_fila_correcta_con_neto_coherente_no_tiene_motivo():
    lectura = leer(_csv(_linea("T-1")), "r.csv", fecha_referencia=HOY)
    assert len(lectura.pesajes) == 1 and lectura.dudosos == ()


@pytest.mark.parametrize(
    "transformar",
    [
        lambda b: b"\xef\xbb\xbf" + b,  # UTF-8 con BOM
        lambda b: b.replace(b";", b","),  # delimitador coma
        lambda b: b.replace(b";", b"\t"),  # delimitador tabulador
    ],
)
def test_bom_y_delimitadores(transformar):
    lectura = leer(transformar(construir.csv_basico()), "r.csv", fecha_referencia=HOY)
    assert lectura.pesajes == LEIDOS_BASICO
    assert lectura.dudosos == DUDOSOS_BASICO


def test_latin1_si_no_decodifica_como_utf8():
    texto = "Ticket;Fecha;Placa;Cliente;Material;Bruto (kg);Tara (kg);Neto (kg)\n"
    texto += "T-1;2026-10-15;EJ-1;Cliente Peña Ñandú;ARENA;40000;15000;25000\n"
    lectura = leer(texto.encode("latin-1"), "r.csv", fecha_referencia=HOY)
    assert [p.cliente for p in lectura.pesajes] == ["Cliente Peña Ñandú"]


def test_utf8_con_tildes():
    texto = "Ticket;Fecha;Placa;Cliente;Material;Bruto (kg);Tara (kg);Neto (kg)\n"
    texto += "T-1;2026-10-15;EJ-1;Cliente Peña;ARENA;40000;15000;25000\n"
    lectura = leer(texto.encode("utf-8"), "r.csv", fecha_referencia=HOY)
    assert [p.cliente for p in lectura.pesajes] == ["Cliente Peña"]


def test_la_extension_decide_el_lector():
    datos = construir.csv_basico()
    assert leer(datos, "R.CSV", fecha_referencia=HOY).pesajes == LEIDOS_BASICO
    assert leer(construir.xlsx_basico(), "R.XLSX", fecha_referencia=HOY).pesajes == LEIDOS_BASICO
    for nombre in ("r.txt", "r.xls", "r", "r.csv.exe"):
        with pytest.raises(ReporteRechazado, match=r"\.csv o \.xlsx"):
            leer(datos, nombre, fecha_referencia=HOY)


def test_un_libro_con_extension_csv_o_texto_con_extension_xlsx_se_rechaza():
    with pytest.raises(ReporteRechazado, match="Excel"):
        leer(construir.xlsx_basico(), "r.csv", fecha_referencia=HOY)
    with pytest.raises(ReporteRechazado, match="no es un libro"):
        leer(construir.csv_basico(), "r.xlsx", fecha_referencia=HOY)


def test_archivo_vacio_o_sin_filas_se_rechaza():
    with pytest.raises(ReporteRechazado, match="no tiene filas"):
        leer(b"", "r.csv", fecha_referencia=HOY)
    with pytest.raises(ReporteRechazado, match="no tiene filas"):
        leer(_xlsx([]), "r.xlsx", fecha_referencia=HOY)


def test_archivo_desmedido_se_rechaza():
    with pytest.raises(ReporteRechazado, match="filas"):
        leer(construir.csv_desmedido(200000), "r.csv", fecha_referencia=HOY)


def test_borde_de_filas_exactamente_el_maximo_se_acepta_y_una_mas_se_rechaza():
    en_el_borde = leer(construir.csv_desmedido(MAX_FILAS), "r.csv", fecha_referencia=HOY)
    assert len(en_el_borde.pesajes) == MAX_FILAS
    assert en_el_borde.dudosos == ()
    with pytest.raises(ReporteRechazado, match="filas"):
        leer(construir.csv_desmedido(MAX_FILAS + 1), "r.csv", fecha_referencia=HOY)


def test_borde_de_filas_en_xlsx_y_el_lector_corta_al_pasar_el_tope(monkeypatch):
    monkeypatch.setattr(bascula, "MAX_FILAS", 5)
    cabecera = ["Ticket", "Fecha", "Material", "Neto (kg)"]

    def libro(n):
        return _xlsx([cabecera, *([f"T-{i}", "2026-10-15", "ARENA", 1000] for i in range(n))])

    assert len(leer(libro(5), "r.xlsx", fecha_referencia=HOY).pesajes) == 5
    with pytest.raises(ReporteRechazado, match="filas"):
        leer(libro(6), "r.xlsx", fecha_referencia=HOY)

    # No se itera sin limite: con un tope de 5 no se piden mas filas que tope + encabezados + 1.
    pedidas = []
    real = bascula._filas_de_xlsx

    class Espia:
        def __init__(self, filas):
            self._filas = filas

        def __iter__(self):
            return self

        def __next__(self):
            fila = next(self._filas)
            pedidas.append(fila)
            return fila

    monkeypatch.setattr(
        bascula, "_filas_de_xlsx", lambda datos, tope: Espia(iter(real(datos, tope)))
    )
    with pytest.raises(ReporteRechazado):
        leer(libro(500), "r.xlsx", fecha_referencia=HOY)
    assert len(pedidas) <= 5 + 30 + 1


def test_columnas_de_mas_se_rechazan_y_el_maximo_se_acepta():
    def reporte(n_columnas):
        extra = [f"Extra {i}" for i in range(n_columnas - 8)]
        filas = [f"x{i}" for i in range(n_columnas - 8)]
        cabecera = ";".join([CABECERA, *extra])
        return _csv(";".join([_linea("T-1"), *filas]), cabecera=cabecera)

    assert len(leer(reporte(MAX_COLUMNAS), "r.csv", fecha_referencia=HOY).pesajes) == 1
    with pytest.raises(ReporteRechazado, match="columnas"):
        leer(reporte(MAX_COLUMNAS + 1), "r.csv", fecha_referencia=HOY)
    ancho = [f"c{i}" for i in range(MAX_COLUMNAS + 1)]
    with pytest.raises(ReporteRechazado, match="columnas"):
        leer(_xlsx([ancho]), "r.xlsx", fecha_referencia=HOY)


def test_mapeo_explicito_manda():
    # Encabezados que el detector no reconoce: sin mapeo se pide el mapeo.
    cabecera = "Col A;Col B;Col C;Col D;Col E;Col F;Col G;Col H"
    datos = _csv(_linea("T-1", bruto="42500", tara="14200", neto="28300"), cabecera=cabecera)
    with pytest.raises(MapeoNecesario):
        leer(datos, "r.csv", fecha_referencia=HOY, unidad_peso="kg")
    mapeo = {
        "ticket": 0,
        "fecha": 1,
        "placa": 2,
        "cliente": 3,
        "material": 4,
        "bruto": 5,
        "tara": 6,
        "neto": 7,
    }
    lectura = leer(datos, "r.csv", fecha_referencia=HOY, unidad_peso="kg", mapeo=mapeo)
    assert [
        (p.ticket, p.placa, p.cliente, p.material, p.bruto_t, p.neto_t) for p in lectura.pesajes
    ] == [("T-1", "EJ-900", "Cliente Ejemplo A", "ARENA", Decimal("42.5"), Decimal("28.3"))]

    # Con encabezados reconocibles el mapeo del usuario gana a la deteccion: ticket <- Placa.
    reconocible = leer(construir.csv_basico(), "r.csv", fecha_referencia=HOY, mapeo={"ticket": 2})
    assert [p.ticket for p in reconocible.pesajes] == ["EJ-001", "EJ-002", "EJ-006"]
    assert reconocible.pesajes[0].material == "ARENA"  # lo no mapeado se sigue detectando


def test_mapeo_explicito_usa_la_unidad_del_encabezado_de_la_columna_elegida():
    cabecera = "Ticket;Fecha;Placa;Cliente;Material;Col F;Col G;Carga (kg)"
    datos = _csv(_linea("T-1", bruto="42500", tara="14200", neto="28300"), cabecera=cabecera)
    lectura = leer(datos, "r.csv", fecha_referencia=HOY, mapeo={"neto": 7})
    assert [(p.bruto_t, p.neto_t) for p in lectura.pesajes] == [(Decimal("0"), Decimal("28.3"))]


def test_mapeo_invalido_se_rechaza():
    with pytest.raises(ReporteRechazado, match="peso"):
        leer(construir.csv_basico(), "r.csv", fecha_referencia=HOY, mapeo={"peso": 7})
    with pytest.raises(ReporteRechazado, match="columna"):
        leer(construir.csv_basico(), "r.csv", fecha_referencia=HOY, mapeo={"ticket": 99})
    with pytest.raises(ReporteRechazado, match="columna"):
        leer(construir.csv_basico(), "r.csv", fecha_referencia=HOY, mapeo={"ticket": -1})


def test_faltan_columnas_en_leer_propaga_mapeo_necesario():
    datos = b"Ticket;Fecha;Bruto (kg);Tara (kg)\nT-1;2026-10-15;40000;15000\n"
    with pytest.raises(MapeoNecesario) as error:
        leer(datos, "r.csv", fecha_referencia=HOY)
    assert error.value.faltan == ("material",)


def test_el_libro_se_abre_en_solo_lectura_con_valores_y_se_cierra(monkeypatch):
    llamadas = []
    cierres = []
    real = openpyxl.load_workbook

    def espia(*args, **kwargs):
        llamadas.append(kwargs)
        libro = real(*args, **kwargs)
        cerrar = libro.close

        def cerrar_y_anotar():
            cierres.append(True)
            cerrar()

        libro.close = cerrar_y_anotar
        return libro

    monkeypatch.setattr(openpyxl, "load_workbook", espia)
    leer(construir.xlsx_basico(), "r.xlsx", fecha_referencia=HOY)
    assert len(llamadas) == 1
    assert llamadas[0]["read_only"] is True and llamadas[0]["data_only"] is True
    assert cierres == [True]
    # Tambien se cierra si el reporte se rechaza.
    with pytest.raises(ReporteRechazado):
        leer(construir.xlsx_sin_unidad(), "r.xlsx", fecha_referencia=HOY)
    assert cierres == [True, True]


def test_se_lee_la_primera_hoja_del_libro():
    libro = openpyxl.Workbook()
    primera = libro.active
    assert primera is not None
    primera.title = "Primera"
    primera.append(["Ticket", "Fecha", "Material", "Neto (kg)"])
    primera.append(["T-1", "2026-10-15", "ARENA", 1000])
    segunda = libro.create_sheet("Segunda")
    segunda.append(["Ticket", "Fecha", "Material", "Neto (kg)"])
    segunda.append(["T-2", "2026-10-15", "ARENA", 2000])
    libro.active = 1  # la hoja activa NO decide: la primera si
    salida = io.BytesIO()
    libro.save(salida)
    lectura = leer(salida.getvalue(), "r.xlsx", fecha_referencia=HOY)
    assert [p.ticket for p in lectura.pesajes] == ["T-1"]
