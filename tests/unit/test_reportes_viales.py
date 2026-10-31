"""Plan vial, Tarea 21: los seis reportes en Excel (`aplicacion/reportes_viales.py`). FICTICIO.

Cada libro se abre con openpyxl y se comprueban los nombres de hoja, la hoja de portada (que dice de
dónde sale cada cifra) y las celdas clave. Oráculos a mano:

- Cómputos de la muestra `data/samples/vial/via_ficticia.csv` (memoria de cálculo de su README):
  T1 mide 1.200 m por 7,30 m = 8.760 m2; la mezcla de su carpeta es 8.760 x 0,05 x 2,35 = **1.029,3
  t** y su transporte a 15 km es 15.439,5 t·km; la pintura de su línea continua, 2.400 m x 0,0365 =
  87,6 l. T2: mezcla 478,4 t. T3: bacheo 34,5 t. En total, 20 cantidades. (El «857,75 t» del plan es
  del tramo de 1.000 m de `test_vial_derivacion.py`, no de la muestra; la pintura de la Tarea 16b no
  cambia ninguna tonelada.)
- Costo de producción de noviembre de 2026 en USD (`tests/fixtures/costo_propio.py`): cantera 1.000,
  planta 1.200; AGR-12 a 5 USD/t, MZ-1 a 50,70 USD/t.
- Riesgo: total base 1.000, P50 = P80 = 1.248,7171, reserva 248,7171.
- Mejora: real 130, original 100 y Sílice 125 dan 23,08 %, 3,85 % y 19,23 puntos.
- IVA: subtotal 1.000 x 0,16 = 160; total 1.160.
- CV3: el APU usa la mezcla propia a 210 y el último cálculo publicado (n.º 5) da 200; el precio
  viene del cálculo n.º 3 (su fuente dice «cálculo n.º 3»), y el hallazgo debe nombrarlo.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook
from openpyxl.workbook import Workbook
from sqlalchemy.orm import Session

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.derivacion import derivar_tramos
from aplicacion import reportes_viales as reportes
from aplicacion import vial
from aplicacion.costo_propio import (
    CalculoGuardado,
    Publicacion,
    calcular_periodo,
    calculos_registrados,
)
from aplicacion.hoja import FilaPrecio
from aplicacion.riesgo.comprobacion import Comprobacion, ResultadoCorte
from aplicacion.riesgo.mejora import mejora_de_estimacion
from aplicacion.riesgo.obra import ComprobacionDeLaObra, ProyeccionDeLaObra
from aplicacion.riesgo.proyeccion import ParametrosProyeccion, Proyeccion
from core.contracts import Dominio, ItemComputo, OrigenTipo
from core.contracts.apu import ComposicionAPU, LineaMaterial, ParametrosCosto
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.costing import calcular_apu
from tests.fixtures import costo_propio as cp

D = Decimal
MUESTRA = Path(__file__).resolve().parents[2] / "data" / "samples" / "vial" / "via_ficticia.csv"
MEZCLA, TRANSPORTE, PINTURA = (
    PARTIDAS_VIALES[c][0] for c in ("carpeta_mezcla", "transporte_mezcla", "pintura_demarcacion")
)
BACHEO_MEZCLA = PARTIDAS_VIALES["bacheo_mezcla"][0]
LINEA_MZP = "Costo propio de mezcla MZ-1"
#: El formato numérico del libro: el patrón de `hoja_exportar` (`#,##0.00`), que Excel muestra con
#: coma decimal y punto de miles en un equipo es-VE.
FORMATO_DINERO = "#,##0.00"
FORMATO_CANTIDAD = "#,##0.00##"


def _libro(contenido: bytes) -> Workbook:
    return load_workbook(BytesIO(contenido))


def _hoja(libro: Workbook, nombre: str):
    assert nombre in libro.sheetnames, f"falta la hoja {nombre!r}: hay {libro.sheetnames}"
    return libro[nombre]


def _filas(libro: Workbook, hoja: str) -> list[tuple]:
    return [fila for fila in _hoja(libro, hoja).iter_rows(values_only=True) if any(fila)]


def _texto(libro: Workbook, hoja: str) -> str:
    return " | ".join(str(c) for fila in _filas(libro, hoja) for c in fila if c is not None)


def _valor(libro: Workbook, hoja: str, rotulo: str, columna: int = 1):
    """El valor de la columna siguiente al `rotulo` de la columna `columna` (empieza en 0)."""
    for fila in _filas(libro, hoja):
        if fila[columna] == rotulo:
            return fila[columna + 1]
    raise AssertionError(f"no hay {rotulo!r} en {hoja}: {_filas(libro, hoja)}")


def _d(valor) -> Decimal:
    return D(str(valor))


def _formato(libro: Workbook, hoja: str, rotulo: str) -> str:
    for fila in _hoja(libro, hoja).iter_rows():
        if fila[0].value == rotulo:
            return fila[1].number_format
    raise AssertionError(rotulo)


def _con_portada(libro: Workbook) -> None:
    """La primera hoja es la portada y cada hoja de datos tiene una fila con su fuente."""
    assert libro.sheetnames[0] == "Portada"
    portada = _filas(libro, "Portada")
    cabecera = next(i for i, f in enumerate(portada) if f[0] == "Hoja")
    assert portada[cabecera] == ("Hoja", "Qué contiene", "De dónde sale cada cifra")
    por_hoja = {f[0]: f for f in portada[cabecera + 1 :]}
    assert set(por_hoja) == set(libro.sheetnames[1:])
    assert all(f[2] and len(str(f[2])) > 20 for f in por_hoja.values())


# --- Cómputos por tramo ---------------------------------------------------------------------------


def _computos() -> Workbook:
    tramos = vial.tramos_desde_csv(MUESTRA.read_bytes(), MUESTRA.name)
    return _libro(
        reportes.computos_por_tramo(
            tramos, vial.cantidades_de_tramos(tramos), proyecto="Vía Ficticia", version="V-001"
        )
    )


def test_computos_hojas_y_portada():
    libro = _computos()
    assert libro.sheetnames == ["Portada", "Tramos", "Cómputos por tramo", "Totales por partida"]
    _con_portada(libro)
    assert "Vía Ficticia" in _texto(libro, "Portada") and "V-001" in _texto(libro, "Portada")


def test_computos_las_veinte_cantidades_con_las_de_la_mano():
    libro = _computos()
    filas = _filas(libro, "Cómputos por tramo")
    cabecera, datos = filas[0], filas[1:]
    assert cabecera == ("Tramo", "Código", "Descripción", "Unidad", "Cantidad", "Regla", "Origen")
    assert len(datos) == 20
    por_clave = {(f[0], f[1], f[3]): _d(f[4]) for f in datos}
    assert por_clave[("T1", MEZCLA, "t")] == D("1029.3")
    assert por_clave[("T1", TRANSPORTE, "t·km")] == D("15439.5")
    assert por_clave[("T2", MEZCLA, "t")] == D("478.4")
    assert por_clave[("T3", BACHEO_MEZCLA, "t")] == D("34.5")
    pinturas = sorted(_d(f[4]) for f in datos if f[1] == PINTURA)
    assert pinturas == [D("16.425"), D("87.6")]
    assert all(f[5] and f[6] for f in datos)  # cada cantidad dice su regla y su origen


def test_computos_los_totales_por_partida_suman_los_tramos():
    libro = _computos()
    totales = {f[0]: _d(f[3]) for f in _filas(libro, "Totales por partida")[1:]}
    assert totales[MEZCLA] == D("1029.3") + D("478.4")  # 1.507,7 t
    assert totales[BACHEO_MEZCLA] == D("34.5")


def test_computos_los_tramos_con_su_longitud_en_metros():
    filas = {f[0]: f for f in _filas(_computos(), "Tramos")[1:]}
    assert (_d(filas["T1"][3]), _d(filas["T2"][3]), _d(filas["T3"][3])) == (D(1200), D(800), D(50))


def test_computos_formato_numerico_es_ve():
    libro = _computos()
    hoja = _hoja(libro, "Cómputos por tramo")
    assert hoja["E2"].number_format == FORMATO_CANTIDAD
    assert hoja["E2"].data_type == "n"


# --- APU con origen y CV3 -------------------------------------------------------------------------


def _fila_de_precio(descripcion: str, fuente: str, precio: str = "210.00") -> FilaPrecio:
    return FilaPrecio(
        codigo="MZP-MZ-1",
        descripcion=descripcion,
        tipo="material",
        precio=D(precio),
        lista="Costo propio 2026-10, cálculo n.º 3",
        moneda="Bs",
        fecha=date(2026, 10, 31),
        tasa=None,
        fecha_tasa=None,
        referencia="",
        cotizacion="",
        alcance="",
        estado="ok",
        fuente=fuente,
    )


def _caso_cv3():
    item = ItemComputo(
        codigo_partida=MEZCLA,
        descripcion="Mezcla asfáltica de la carpeta, tramo T1",
        unidad="t",
        cantidad=D("840"),
        origen_id="tramo:T1:capa:1",
        origen_tipo=OrigenTipo.TABULAR,
        dominio=Dominio.CIVIL,
    )
    apu = ComposicionAPU(
        MEZCLA,
        item.descripcion,
        "t",
        D("10"),
        materiales=(LineaMaterial(LINEA_MZP, "t", D("1"), D("210.00")),),
    )
    parametros = ParametrosCosto()
    presupuesto = Presupuesto(
        "VIAL-TEST",
        date(2026, 10, 31),
        "Bs",
        (PartidaPresupuestada(item, apu, calcular_apu(apu, parametros)),),
    )
    return presupuesto, {MEZCLA: apu}, parametros


def _apu(fuente: str = "Producción, período 2026-10, cálculo n.º 3") -> Workbook:
    presupuesto, composiciones, parametros = _caso_cv3()
    ultimo = CalculoGuardado(5, "2026-11", "Bs", {"MZ-1": D("200.00")}, "huella")
    return _libro(
        reportes.apu_con_origen(
            presupuesto,
            composiciones,
            parametros,
            [_fila_de_precio(LINEA_MZP, fuente)],
            items_viales=(),
            costos_propios={"MZP-MZ-1": ultimo},
            proyecto="Vía Ficticia",
        )
    )


def test_apu_hojas_y_portada():
    libro = _apu()
    assert libro.sheetnames == ["Portada", "Partidas", "APU con origen", "Conciliación"]
    _con_portada(libro)


def test_apu_cada_linea_dice_la_fuente_de_su_precio_y_el_numero_del_calculo():
    libro = _apu()
    filas = _filas(libro, "APU con origen")
    cabecera, linea = filas[0], filas[1]
    assert cabecera[:4] == ("Partida", "Tipo de línea", "Concepto", "Unidad")
    columna = {nombre: i for i, nombre in enumerate(cabecera)}
    assert linea[columna["Concepto"]] == LINEA_MZP
    assert linea[columna["Origen del precio"]] == "Producción, período 2026-10, cálculo n.º 3"
    assert linea[columna["Cálculo n.º"]] == 3
    assert _d(linea[columna["Precio"]]) == D("210.00")


def test_apu_cv3_nombra_el_calculo_usado_y_no_dice_ningun_conocido():
    """El añadido del árbitro de la Tarea 10: `calculos_usados` sale de `numero_de_calculo`."""
    texto = _texto(_apu(), "Conciliación")
    assert "CV3" in texto
    assert "cálculo n.º 3" in texto and "cálculo n.º 5" in texto
    assert "ningún cálculo publicado conocido" not in texto


def test_apu_cv3_sin_fuente_de_calculo_lo_dice():
    texto = _texto(_apu("Cotización de un proveedor"), "Conciliación")
    assert "ningún cálculo publicado conocido" in texto


def test_apu_formato_numerico_es_ve():
    hoja = _hoja(_apu(), "APU con origen")
    columnas = {c.value: c.column_letter for c in hoja[1]}
    assert hoja[f"{columnas['Precio']}2"].number_format == FORMATO_DINERO


def test_apu_sin_hallazgos_la_hoja_lo_dice():
    presupuesto, composiciones, parametros = _caso_cv3()
    ultimo = CalculoGuardado(5, "2026-11", "Bs", {"MZ-1": D("210.00")}, "huella")
    libro = _libro(
        reportes.apu_con_origen(
            presupuesto,
            composiciones,
            parametros,
            [],
            items_viales=derivar_tramos([]),
            costos_propios={"MZP-MZ-1": ultimo},
            proyecto="Vía Ficticia",
        )
    )
    assert "Sin hallazgos" in _texto(libro, "Conciliación")
    assert "sin origen registrado" in _texto(libro, "APU con origen")


# --- Costo de producción --------------------------------------------------------------------------


@pytest.fixture
def ins() -> Iterator[Session]:
    with cp.instalacion_en_memoria() as sesion:
        yield sesion


@pytest.fixture
def caso(tmp_path: Path) -> Iterator[Session]:
    with cp.carpeta_del_caso(tmp_path) as sesion:
        yield sesion


def _produccion(ins: Session, caso: Session) -> tuple[Workbook, int]:
    cp.noviembre_usd(ins, caso)
    calculo = calcular_periodo(ins, caso, cp.PERIODO, "USD", usuario="ana", ahora=cp.AHORA)
    libro = _libro(
        reportes.costo_de_produccion(calculos_registrados(ins, cp.PERIODO), periodo=cp.PERIODO)
    )
    return libro, calculo.id


def test_produccion_hojas_y_portada(ins, caso):
    libro, _ = _produccion(ins, caso)
    assert libro.sheetnames == [
        "Portada",
        "Cálculos",
        "Costo por tonelada",
        "Costos del período",
        "Producido",
    ]
    _con_portada(libro)


def test_produccion_costo_por_tonelada_de_la_mano(ins, caso):
    libro, numero = _produccion(ins, caso)
    filas = _filas(libro, "Costo por tonelada")
    assert filas[0] == ("Cálculo n.º", "Período", "Producto", "Tipo", "Costo por t", "Moneda")
    por_producto = {f[2]: (f[0], f[3], _d(f[4]), f[5]) for f in filas[1:]}
    assert por_producto["AGR-12"] == (numero, "agregado", D(5), "USD")
    assert por_producto["MZ-1"] == (numero, "mezcla", D("50.70"), "USD")
    hoja = _hoja(libro, "Costo por tonelada")
    assert hoja["E2"].number_format == FORMATO_DINERO


def test_produccion_los_totales_y_que_no_esta_publicado(ins, caso):
    libro, _ = _produccion(ins, caso)
    cabecera, fila = _filas(libro, "Cálculos")[:2]
    columna = {n: i for i, n in enumerate(cabecera)}
    assert _d(fila[columna["Total de la cantera"]]) == D(1000)
    assert _d(fila[columna["Total de la planta"]]) == D(1200)
    assert fila[columna["Publicado"]] == "No"
    assert fila[columna["Período"]] == cp.PERIODO


def test_produccion_los_costos_registrados_dicen_su_fuente(ins, caso):
    libro, _ = _produccion(ins, caso)
    filas = _filas(libro, "Costos del período")
    assert sum(1 for f in filas[1:] if f[1] == "cantera") == 2
    assert {f[7] for f in filas[1:]} == {"factura ficticia"}


def test_produccion_publicado_dice_la_lista(ins, caso):
    cp.noviembre_usd(ins, caso)
    calculo = calcular_periodo(ins, caso, cp.PERIODO, "USD", usuario="ana", ahora=cp.AHORA)
    publicacion = Publicacion(1, calculo.id, "carpeta.db", 9, "admin", datetime(2026, 11, 30, 19))
    libro = _libro(reportes.costo_de_produccion([(calculo, publicacion)], periodo=cp.PERIODO))
    texto = _texto(libro, "Cálculos")
    assert "Sí" in texto and "admin" in texto and "carpeta.db" in texto


def test_produccion_sin_calculos_es_un_error_llano():
    with pytest.raises(ValueError, match="2026-11"):
        reportes.costo_de_produccion([], periodo="2026-11")


# --- Riesgo ---------------------------------------------------------------------------------------


def _proyeccion() -> ProyeccionDeLaObra:
    proyeccion = Proyeccion(
        total_base=D(1000),
        percentiles={50: D("1248.7171"), 80: D("1248.7171")},
        reserva=D("248.7171"),
        contribucion=(("Cemento asfáltico", D("848.7171")), ("Gasoil", D(100))),
        meses_usados=24,
        semilla=1,
        supuestos=("supuesto uno de la proyección", "supuesto dos"),
    )
    parametros = ParametrosProyeccion(inicio=date(2026, 10, 1), meses=6, trayectorias=2000)
    return ProyeccionDeLaObra(
        "Vía Ficticia Riesgo",
        "VR-001",
        "USD",
        date(2026, 10, 1),
        "linea_base",
        parametros,
        proyeccion,
        {LINEA_MZP: 3},
    )


MAPA = {"Cemento asfáltico": "CEMENTO_ASFALTICO_PPI"}


def _comprobacion() -> ComprobacionDeLaObra:
    cortes = (
        ResultadoCorte(date(2025, 10, 1), D(1100), D(1200), D(1150), True),
        ResultadoCorte(date(2025, 11, 1), D(1100), D(1200), D(1250), False),
    )
    base = _proyeccion()
    return ComprobacionDeLaObra(
        base.proyecto,
        base.version,
        base.moneda,
        base.parametros,
        Comprobacion(cortes, D("0.5"), 2),
        base.mezclas,
    )


def test_riesgo_hojas_y_portada():
    libro = _libro(reportes.informe_de_riesgo(_proyeccion(), mapa=MAPA))
    assert libro.sheetnames == [
        "Portada",
        "Proyección",
        "Contribución",
        "Supuestos",
        "Mapa de series",
        "Mezclas propias",
    ]
    _con_portada(libro)


def test_riesgo_p50_p80_reserva_y_supuestos():
    libro = _libro(reportes.informe_de_riesgo(_proyeccion(), mapa=MAPA))
    assert _d(_valor(libro, "Proyección", "Total base")) == D(1000)
    assert _d(_valor(libro, "Proyección", "P50")) == D("1248.7171")
    assert _d(_valor(libro, "Proyección", "P80")) == D("1248.7171")
    assert _d(_valor(libro, "Proyección", "Reserva (P80 − total base)")) == D("248.7171")
    assert _valor(libro, "Proyección", "Moneda") == "USD"
    assert _valor(libro, "Proyección", "Origen del inicio") == "línea base de la versión"
    assert _formato(libro, "Proyección", "P80") == "#,##0.00##"
    texto = _texto(libro, "Supuestos")
    assert "supuesto uno de la proyección" in texto and "supuesto dos" in texto
    assert _filas(libro, "Mapa de series")[1] == ("Cemento asfáltico", "CEMENTO_ASFALTICO_PPI")
    assert _filas(libro, "Mezclas propias")[1] == (LINEA_MZP, 3)
    contribucion = _filas(libro, "Contribución")
    assert contribucion[1][0] == "Cemento asfáltico" and _d(contribucion[1][1]) == D("848.7171")


def test_riesgo_con_comprobacion_trae_la_cobertura():
    libro = _libro(reportes.informe_de_riesgo(_proyeccion(), _comprobacion(), mapa=MAPA))
    assert libro.sheetnames[-1] == "Comprobación"
    _con_portada(libro)
    assert _d(_valor(libro, "Comprobación", "Cobertura (%)")) == D("50.00")
    assert _valor(libro, "Comprobación", "Cortes dentro del P80") == 1
    assert _valor(libro, "Comprobación", "Cortes") == 2
    cortes = [f for f in _filas(libro, "Comprobación") if isinstance(f[0], datetime)]
    assert [(f[0].date(), f[4]) for f in cortes] == [
        (date(2025, 10, 1), "Sí"),
        (date(2025, 11, 1), "No"),
    ]


# --- Mejora ---------------------------------------------------------------------------------------


def _mejora(real="130", original="100", silice="125") -> Workbook:
    mejora = mejora_de_estimacion(D(real), D(original), D(silice))
    return _libro(
        reportes.informe_de_mejora(
            mejora,
            costo_final_real=D(real),
            presupuesto_original=D(original),
            estimacion_silice=D(silice),
        )
    )


def test_mejora_las_tres_cifras_de_la_mano():
    libro = _mejora()
    assert libro.sheetnames == ["Portada", "Mejora"]
    _con_portada(libro)
    assert _d(_valor(libro, "Mejora", "Error del presupuesto original (%)")) == D("23.08")
    assert _d(_valor(libro, "Mejora", "Error de la estimación de Sílice (%)")) == D("3.85")
    assert _d(_valor(libro, "Mejora", "Mejora (puntos porcentuales)")) == D("19.23")
    assert _d(_valor(libro, "Mejora", "Costo final real")) == D(130)
    assert "acertó más" in _texto(libro, "Mejora")
    assert _formato(libro, "Mejora", "Mejora (puntos porcentuales)") == FORMATO_DINERO


def test_mejora_negativa_no_se_esconde():
    libro = _mejora("100", "120", "70")
    assert _d(_valor(libro, "Mejora", "Mejora (puntos porcentuales)")) == D("-10")
    assert "acertó menos" in _texto(libro, "Mejora")


# --- Resumen con IVA ------------------------------------------------------------------------------


def test_resumen_con_iva_de_la_mano():
    presupuesto, _, _ = _caso_cv3()
    # 840 t x 265,65 = 223.146 (precio unitario con la cascada 1,15 x 1,10 sobre 210)
    libro = _libro(reportes.resumen_con_iva(presupuesto, proyecto="Vía Ficticia", version="V-001"))
    assert libro.sheetnames == ["Portada", "Resumen", "Partidas"]
    _con_portada(libro)
    subtotal = presupuesto.total
    assert _d(_valor(libro, "Resumen", "Subtotal sin IVA")) == subtotal.quantize(D("0.01"))
    assert _d(_valor(libro, "Resumen", "IVA (16 %)")) == (subtotal * D("0.16")).quantize(D("0.01"))
    total = _d(_valor(libro, "Resumen", "Total con IVA"))
    assert total == _d(_valor(libro, "Resumen", "Subtotal sin IVA")) + _d(
        _valor(libro, "Resumen", "IVA (16 %)")
    )
    assert _valor(libro, "Resumen", "Moneda") == "Bs"
    assert _formato(libro, "Resumen", "Total con IVA") == FORMATO_DINERO
    assert "Gaceta" in _texto(libro, "Portada")  # la fuente de la alícuota, «a cotejar»


def test_resumen_con_iva_un_subtotal_redondo():
    item = ItemComputo(
        codigo_partida="X-1",
        descripcion="Partida",
        unidad="u",
        cantidad=D("10"),
        origen_id="F-1",
        origen_tipo=OrigenTipo.TABULAR,
        dominio=Dominio.CIVIL,
    )
    apu = ComposicionAPU(
        "X-1", "Partida", "u", D("1"), materiales=(LineaMaterial("M", "u", D("1"), D("100")),)
    )
    parametros = ParametrosCosto(
        fcas=D(0), bono_alimentacion=D(0), administracion=D(0), utilidad=D(0)
    )
    presupuesto = Presupuesto(
        "P",
        date(2026, 10, 31),
        "USD",
        (PartidaPresupuestada(item, apu, calcular_apu(apu, parametros)),),
    )
    libro = _libro(reportes.resumen_con_iva(presupuesto, proyecto="P", version="V"))
    assert _d(_valor(libro, "Resumen", "Subtotal sin IVA")) == D(1000)
    assert _d(_valor(libro, "Resumen", "IVA (16 %)")) == D(160)
    assert _d(_valor(libro, "Resumen", "Total con IVA")) == D(1160)


# --- Transversal ----------------------------------------------------------------------------------


def test_un_texto_con_caracter_de_control_no_rompe_el_libro():
    mala = "Cemento\x00 asfáltico"
    proyeccion = _proyeccion()
    proyeccion = ProyeccionDeLaObra(
        proyeccion.proyecto,
        proyeccion.version,
        proyeccion.moneda,
        proyeccion.inicio,
        proyeccion.inicio_de,
        proyeccion.parametros,
        Proyeccion(D(1000), {50: D(1), 80: D(1)}, D(0), ((mala, D(1)),), 24, 1, ("supuesto",)),
        {},
    )
    libro = _libro(reportes.informe_de_riesgo(proyeccion, mapa={mala: "SERIE"}))
    assert _hoja(libro, "Contribución")["A2"].value == "Cemento� asfáltico"


def test_nombre_de_archivo_seguro():
    assert reportes.nombre_de_reporte("computos", "Vía / Ficticia", "V-001") == (
        "computos_V_a_Ficticia_V-001.xlsx"
    )
    assert reportes.nombre_de_reporte("produccion", "2026-11") == "produccion_2026-11.xlsx"
