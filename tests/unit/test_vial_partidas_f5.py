"""F5 vial, tarea 1: las partidas que faltaban en el catálogo vial y sus variantes de medición.

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §6 (punto 3) y la
decisión provisional 4 del 2026-11-06 (fresado en m² y colocación de la carpeta en t). Datos
FICTICIOS, escritos para esta prueba. Oráculos calculados a mano y escritos como literales:

Tramo P1, de 0 a 0,5 km (500 m), ancho 7 m: área 500 × 7 = 3.500 m².
- fresado e = 0,04 con esponjamiento 1,25: 3.500 × 0,04 = 140 m³; suelto 140 × 1,25 = 175 m³.
- riego de adherencia 0,40 l/m² con limpieza: limpieza 3.500 m²; riego 3.500 m²; 1.400 l.
- carpeta e = 0,05, d = 2,4: 3.500 m²; 3.500 × 0,05 = 175 m³; 175 × 2,4 = 420 t.
- línea continua, 2 líneas, 40 captafaros: 1.000 m; pintura 1.000 × 0,0365 = 36,5 l; 40 unidades.
- demarcación de superficie: 3 elementos de 6 m² = 18 m².

Tramo P2, de 0,5 a 0,7 km (200 m), ancho 6 m: área 1.200 m².
- fresado e = 0,05 medido en m²: 1.200 m² (y ningún m³).
- carpeta e = 0,05, d = 2,3 medida en t: colocación 1.200 × 0,05 × 2,3 = 138 t; mezcla 138 t.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import TIPOS_DEMARCACION, Capa, Demarcacion, Tramo
from adapters.vial.reglas import auditar_vial
from adapters.vial.tabular import leer_tramos
from api.esquemas_vial import TramoEntrada, a_tramos, tramo_a_respuesta
from aplicacion import vial
from aplicacion.consulta import buscar
from core import models
from core.catalog import abrir_sesion, crear_motor
from core.contracts import Dominio, ItemComputo, OrigenTipo
from core.contracts.apu import ComposicionAPU, ResultadoAPU
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Severidad
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import sembrar_vivienda

D = Decimal

P1 = Tramo(
    "P1",
    D("0"),
    D("0.5"),
    D("7"),
    (
        Capa("fresado", D("0.04"), None, None, esponjamiento=D("1.25")),
        Capa("riego_adherencia", None, None, D("0.40"), limpieza=True),
        Capa("carpeta", D("0.05"), D("2.4"), None),
    ),
    (
        Demarcacion("continua", 2, captafaros=40),
        Demarcacion("superficie", 3, area_m2=D("6")),
    ),
)
P2 = Tramo(
    "P2",
    D("0.5"),
    D("0.7"),
    D("6"),
    (
        Capa("fresado", D("0.05"), None, None, medicion="m2"),
        Capa("carpeta", D("0.05"), D("2.3"), None, medicion="t"),
    ),
)


def _codigo(clave: str) -> str:
    return PARTIDAS_VIALES[clave][0]


def _de(items: list[ItemComputo], origen: str) -> list[tuple[str, str, Decimal]]:
    claves = {codigo: clave for clave, (codigo, _, _) in PARTIDAS_VIALES.items()}
    return [
        (claves[i.codigo_partida], i.unidad, i.cantidad) for i in items if i.origen_id == origen
    ]


# --- catálogo ------------------------------------------------------------------------------------


def test_seis_partidas_nuevas_y_dos_variantes_con_codigo_correlativo():
    esperadas = {
        "movilizacion_equipos": ("C-000.000.016", "viaje"),
        "limpieza_superficie": ("C-000.000.017", "m2"),
        "transporte_fresado": ("C-000.000.018", "m3"),
        "senalizacion_transito": ("C-000.000.019", "dia"),
        "captafaros": ("C-000.000.020", "unidad"),
        "demarcacion_superficie": ("C-000.000.021", "m2"),
        "fresado_area": ("C-000.000.022", "m2"),
        "carpeta_colocacion_masa": ("C-000.000.023", "t"),
    }
    for clave, (codigo, unidad) in esperadas.items():
        assert (PARTIDAS_VIALES[clave][0], PARTIDAS_VIALES[clave][2]) == (codigo, unidad), clave
    # las 15 de antes no cambian
    assert PARTIDAS_VIALES["fresado"] == ("C-000.000.001", "Fresado de pavimento asfáltico", "m3")
    assert PARTIDAS_VIALES["carpeta"][2] == "m2"


def test_la_consulta_de_partidas_viales_las_encuentra():
    assert [s.valor for s in buscar(None, "partidas_viales", "captafaros")] == ["C-000.000.020"]
    assert "C-000.000.016" in [s.valor for s in buscar(None, "partidas_viales", "movilización")]
    assert "C-000.000.019" in [s.valor for s in buscar(None, "partidas_viales", "señalización")]


# --- modelo --------------------------------------------------------------------------------------


def test_superficie_es_un_tipo_de_demarcacion():
    assert TIPOS_DEMARCACION == ("continua", "discontinua", "superficie")


@pytest.mark.parametrize(
    ("hacer", "mensaje"),
    [
        (
            lambda: Capa("carpeta", D("0.05"), D("2.4"), None, esponjamiento=D("1.2")),
            "esponjamiento",
        ),
        (
            lambda: Capa("fresado", D("0.05"), None, None, esponjamiento=D("0.9")),
            "mayor o igual a 1",
        ),
        (lambda: Capa("carpeta", D("0.05"), D("2.4"), None, limpieza=True), "limpieza"),
        (lambda: Capa("base_granular", D("0.2"), None, None, medicion="m2"), "medición"),
        (lambda: Capa("fresado", D("0.05"), None, None, medicion="kg"), "medición"),
        (lambda: Demarcacion("superficie", 2), "área"),
        (lambda: Demarcacion("continua", 2, area_m2=D("6")), "área"),
        (lambda: Demarcacion("superficie", 2, area_m2=D("6"), captafaros=4), "captafaros"),
        (lambda: Demarcacion("continua", 2, captafaros=0), "captafaros"),
        (lambda: Demarcacion("superficie", 2, area_m2=D("0")), "mayor que cero"),
    ],
)
def test_lo_que_no_sigue_la_convencion_se_rechaza(hacer, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        hacer()


def test_la_medicion_de_siempre_se_guarda_como_vacia():
    assert Capa("fresado", D("0.05"), None, None, medicion="m3") == Capa(
        "fresado", D("0.05"), None, None
    )
    assert Capa("carpeta", D("0.05"), D("2.4"), None, medicion="m2").medicion is None


# --- derivación ----------------------------------------------------------------------------------


def test_fresado_con_esponjamiento_da_el_transporte_del_fresado():
    items = derivar_tramos([P1])
    assert _de(items, "tramo:P1:capa:1") == [
        ("fresado", "m3", D("140")),
        ("transporte_fresado", "m3", D("175")),
    ]
    transporte = [i for i in items if i.codigo_partida == _codigo("transporte_fresado")][0]
    assert transporte.regla == "longitud*ancho*espesor*esponjamiento"
    assert transporte.origen_tipo is OrigenTipo.REGLA and transporte.dominio is Dominio.CIVIL


def test_riego_con_limpieza_da_la_limpieza_de_la_superficie_primero():
    assert _de(derivar_tramos([P1]), "tramo:P1:capa:2") == [
        ("limpieza_superficie", "m2", D("3500")),
        ("riego_adherencia", "m2", D("3500")),
        ("riego_adherencia_ligante", "l", D("1400")),
    ]


def test_linea_con_captafaros_y_demarcacion_de_superficie():
    items = derivar_tramos([P1])
    assert _de(items, "tramo:P1:demarcacion:1") == [
        ("demarcacion_continua", "m", D("1000")),
        ("pintura_demarcacion", "l", D("36.5")),
        ("captafaros", "unidad", D("40")),
    ]
    assert _de(items, "tramo:P1:demarcacion:2") == [("demarcacion_superficie", "m2", D("18"))]
    superficie = [i for i in items if i.codigo_partida == _codigo("demarcacion_superficie")][0]
    assert superficie.regla == "area_elemento*elementos"
    assert dict(superficie.parametros) == {"area_elemento": D("6"), "elementos": D("3")}


def test_variantes_de_medicion_del_fresado_y_de_la_carpeta():
    items = derivar_tramos([P2])
    assert _de(items, "tramo:P2:capa:1") == [("fresado_area", "m2", D("1200"))]
    assert _de(items, "tramo:P2:capa:2") == [
        ("carpeta_colocacion_masa", "t", D("138")),
        ("carpeta_mezcla", "t", D("138")),
    ]


def test_un_tramo_de_hoy_deriva_lo_mismo_que_antes():
    muestra = Path(__file__).resolve().parents[2] / "data" / "samples" / "vial" / "via_ficticia.csv"
    assert len(derivar_tramos(leer_tramos(muestra))) == 20


# --- reglas viales -------------------------------------------------------------------------------


def _presupuesto(*items: ItemComputo) -> Presupuesto:
    cero = D("0")
    partidas = []
    for item in items:
        apu = ComposicionAPU(item.codigo_partida, item.descripcion, item.unidad, D("1"))
        partidas.append(
            PartidaPresupuestada(item, apu, ResultadoAPU(cero, cero, cero, cero, cero, D("1")))
        )
    return Presupuesto("VIA-TEST", date(2026, 11, 6), "Bs", tuple(partidas))


def _renglon(clave: str, origen: str, cantidad: str) -> ItemComputo:
    codigo, descripcion, unidad = PARTIDAS_VIALES[clave]
    return ItemComputo(
        codigo_partida=codigo,
        descripcion=descripcion,
        unidad=unidad,
        cantidad=D(cantidad),
        origen_id=origen,
        origen_tipo=OrigenTipo.MANUAL,
        dominio=Dominio.CIVIL,
    )


def test_vr7_casa_la_variante_y_marca_la_medicion_que_la_capa_no_produce():
    bien = auditar_vial([P2], _presupuesto(_renglon("fresado_area", "tramo:P2:capa:1", "1200")))
    assert [h for h in bien if h.regla == "VR7"] == []
    mal = auditar_vial([P2], _presupuesto(_renglon("fresado", "tramo:P2:capa:1", "60")))
    assert [(h.regla, h.severidad) for h in mal] == [("VR7", Severidad.ERROR)]


def test_vr1_mide_tambien_la_colocacion_en_toneladas():
    hallazgos = auditar_vial(
        [P2], _presupuesto(_renglon("carpeta_colocacion_masa", "tramo:P2:capa:2", "150"))
    )
    assert [(h.regla, h.valor_observado, h.valor_esperado) for h in hallazgos] == [
        ("VR1", D("150"), D("138"))
    ]


# --- CSV -----------------------------------------------------------------------------------------

_CABECERA = (
    "tramo;progresiva_ini_km;progresiva_fin_km;ancho_m;distancia_planta_km;elemento;tipo;"
    "espesor_m;densidad_t_m3;dosis_l_m2;lineas;esponjamiento;limpieza;medicion;area_m2;captafaros"
)


def _csv(tmp_path: Path, *filas: str) -> Path:
    ruta = tmp_path / "via.csv"
    ruta.write_text("\n".join((_CABECERA, *filas)) + "\n", encoding="utf-8")
    return ruta


def test_el_csv_lee_las_columnas_nuevas(tmp_path: Path):
    ruta = _csv(
        tmp_path,
        "P1;0;0,5;7;;capa;fresado;0,04;;;;1,25;;;;",
        "P1;;;;;capa;riego_adherencia;;;0,40;;;sí;;;",
        "P1;;;;;capa;carpeta;0,05;2,4;;;;;;;",
        "P1;;;;;demarcacion;continua;;;;2;;;;;40",
        "P1;;;;;demarcacion;superficie;;;;3;;;;6;",
        "P2;0,5;0,7;6;;capa;fresado;0,05;;;;;;m2;;",
        "P2;;;;;capa;carpeta;0,05;2,3;;;;no;t;;",
    )
    assert leer_tramos(ruta) == [P1, P2]


@pytest.mark.parametrize(
    ("fila", "mensaje"),
    [
        ("P1;0;0,5;7;;capa;riego_adherencia;;;0,40;;;quizás;;;", r"fila 2\b.*limpieza"),
        ("P1;0;0,5;7;;capa;fresado;0,04;;;;;;;6;", r"fila 2\b.*area_m2"),
        ("P1;0;0,5;7;;demarcacion;continua;;;;2;1,2;;;;", r"fila 2\b.*esponjamiento"),
        ("P1;0;0,5;7;;demarcacion;continua;;;;2;;;;;dos", r"fila 2\b.*captafaros"),
    ],
)
def test_el_csv_rechaza_lo_que_no_va_con_la_fila(tmp_path: Path, fila: str, mensaje: str):
    with pytest.raises(ValueError, match=mensaje):
        leer_tramos(_csv(tmp_path, fila))


# --- guardar y leer; la API ----------------------------------------------------------------------


@pytest.fixture
def motor(tmp_path: Path) -> Iterator[Engine]:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            sembrar_vivienda(s, usuario="Ana <ana>")
        yield motor
    finally:
        motor.dispose()


@pytest.fixture
def sesion(motor: Engine) -> Iterator[Session]:
    with abrir_sesion(motor) as s:
        yield s


def test_lo_guardado_se_lee_igual(sesion: Session):
    version = sesion.scalars(
        select(models.Presupuesto.id).where(models.Presupuesto.codigo == "VIV-001")
    ).one()
    vial.guardar_tramos(
        sesion, version, [P1, P2], usuario="Ana <ana>", ahora=datetime(2026, 11, 6, 9)
    )
    assert vial.tramos_de_version(sesion, version) == [P1, P2]


def test_la_api_recibe_y_devuelve_los_datos_nuevos():
    respuesta = tramo_a_respuesta(P1)
    assert respuesta.capas[0].esponjamiento == "1.25"
    assert respuesta.capas[1].limpieza is True
    assert respuesta.demarcacion[0].captafaros == 40
    assert respuesta.demarcacion[1].area_m2 == "6"
    assert tramo_a_respuesta(P2).capas[0].medicion == "m2"
    entrada = TramoEntrada.model_validate(respuesta.model_dump())
    assert a_tramos([entrada]) == [P1]
