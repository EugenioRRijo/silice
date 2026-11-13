"""Prueba de punta a punta del 2026-11-13, defecto D2: el tramo declara lo que el APU ya trae.

- **Riego con suministro** (columna `suministro` = sí en la imprimación o el riego de adherencia):
  el APU del riego incluye el ligante, así que el tramo no deriva la partida del ligante; la dosis
  pasa a ser opcional y, si está, VR3 la sigue midiendo. Sin la columna, la capa se lee como antes
  (dosis obligatoria, ligante derivado): «un CSV de hoy sigue leyéndose igual» (diseño §6.3).
- **Ojos de gato sin línea** (demarcación de tipo `captafaros`): solo el número de captafaros, sin
  metros de línea ni pintura.
- **Llevar sigue siendo todo o nada**; el 404 de las partidas sin APU dice cómo declarar lo de
  arriba cuando falta el APU de un ligante o de una línea con captafaros.

Decisión simulada en `docs/bitacora/2026-11-13-e2e-vial.md` (D2). Datos FICTICIOS. Oráculos a mano:
T1 de 0 a 1 km (1.000 m), ancho 1 m: riego 1.000 × 1 = 1.000 m²; con 0,40 l/m², 400 l de ligante;
con 0,10 l/m² quedan 0,10 × 1.000 × 1,0 × 0,60 = 60 g/m² de residual, bajo el mínimo de 200 (VR3).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, select

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Demarcacion, Tramo
from adapters.vial.reglas import auditar_vial
from adapters.vial.tabular import leer_tramos
from api.esquemas_vial import TramoEntrada, a_tramos, tramo_a_respuesta
from aplicacion import hoja_edicion, hoja_vial, vial
from core import models
from core.catalog import abrir_sesion, crear_motor
from core.contracts.apu import ComposicionAPU, ResultadoAPU
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Severidad
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import sembrar_vivienda

D = Decimal
COD = {clave: datos[0] for clave, datos in PARTIDAS_VIALES.items()}
CABECERA = (
    "tramo;progresiva_ini_km;progresiva_fin_km;ancho_m;distancia_planta_km;elemento;tipo;"
    "espesor_m;densidad_t_m3;dosis_l_m2;lineas"
)
PISTA_LIGANTE = (
    "Si el APU del riego ya trae el ligante (riego con suministro), escriba «sí» en la columna "
    "«suministro» de esa capa de los tramos: el ligante no se deriva."
)
PISTA_CAPTAFAROS = (
    "Si en la vía solo se colocan ojos de gato, sin pintar la línea, declárelos como demarcación "
    "de tipo «captafaros»: no se derivan la línea ni su pintura."
)


def _tramo(*capas: Capa, demarcacion: tuple[Demarcacion, ...] = ()) -> Tramo:
    return Tramo("T1", D("0"), D("1"), D("1"), capas, demarcacion)


def _derivadas(tramo: Tramo) -> list[tuple[str, str, Decimal, str]]:
    return [(i.codigo_partida, i.unidad, i.cantidad, i.origen_id) for i in derivar_tramos([tramo])]


# --- riego con suministro -------------------------------------------------------------------------


@pytest.mark.parametrize("tipo", ["riego_adherencia", "imprimacion"])
def test_el_riego_con_suministro_no_deriva_el_ligante(tipo: str):
    for dosis in (None, D("0.4")):
        tramo = _tramo(Capa(tipo, None, None, dosis, suministro=True))
        assert _derivadas(tramo) == [(COD[tipo], "m2", D("1000"), "tramo:T1:capa:1")]


def test_sin_suministro_el_riego_sigue_exigiendo_la_dosis_y_deriva_el_ligante():
    with pytest.raises(ValueError, match="la capa riego_adherencia exige dosis"):
        Capa("riego_adherencia", None, None, None)
    tramo = _tramo(Capa("riego_adherencia", None, None, D("0.4")))
    assert [(c, u, q) for c, u, q, _ in _derivadas(tramo)] == [
        (COD["riego_adherencia"], "m2", D("1000")),
        (COD["riego_adherencia_ligante"], "l", D("400.0")),
    ]


def test_el_suministro_solo_es_de_los_riegos():
    with pytest.raises(ValueError, match="la capa carpeta no usa suministro"):
        Capa("carpeta", D("0.05"), D("2.4"), None, suministro=True)
    with pytest.raises(TypeError, match="suministro"):
        Capa("riego_adherencia", None, None, None, suministro="sí")  # type: ignore[arg-type]


def test_con_suministro_y_dosis_vr3_sigue_midiendo_el_residual():
    tramo = _tramo(Capa("riego_adherencia", None, None, D("0.1"), suministro=True))
    presupuesto = _presupuesto(tramo)
    vr3 = [(h.regla, h.severidad) for h in auditar_vial([tramo], presupuesto)]
    assert vr3 == [("VR3", Severidad.ADVERTENCIA)]


def test_con_suministro_el_ligante_aparte_en_el_presupuesto_es_vr7():
    con = _tramo(Capa("riego_adherencia", None, None, D("0.4"), suministro=True))
    sin = _tramo(Capa("riego_adherencia", None, None, D("0.4")))
    hallazgos = auditar_vial([con], _presupuesto(sin))  # el presupuesto trae el ligante
    assert [(h.regla, h.severidad) for h in hallazgos] == [("VR7", Severidad.ERROR)]


# --- ojos de gato sin línea -----------------------------------------------------------------------


def test_los_captafaros_solos_derivan_solo_las_unidades():
    tramo = _tramo(demarcacion=(Demarcacion("captafaros", 1, captafaros=40),))
    assert _derivadas(tramo) == [(COD["captafaros"], "unidad", D("40"), "tramo:T1:demarcacion:1")]
    assert derivar_tramos([tramo])[0].regla == "captafaros"
    assert auditar_vial([tramo], _presupuesto(tramo)) == []


def test_los_captafaros_en_una_linea_siguen_derivando_la_linea_y_la_pintura():
    tramo = _tramo(demarcacion=(Demarcacion("continua", 1, captafaros=40),))
    assert [c for c, *_ in _derivadas(tramo)] == [
        COD["demarcacion_continua"],
        COD["pintura_demarcacion"],
        COD["captafaros"],
    ]


@pytest.mark.parametrize(
    ("argumentos", "mensaje"),
    [
        ({"lineas": 1}, "la demarcación de captafaros exige el número de captafaros"),
        ({"lineas": 2, "captafaros": 40}, "la demarcación de captafaros no usa lineas"),
        (
            {"lineas": 1, "captafaros": 40, "area_m2": D("2")},
            "la demarcación captafaros no usa área",
        ),
    ],
)
def test_los_captafaros_solos_rechazan_lo_que_no_usan(argumentos: dict, mensaje: str):
    with pytest.raises(ValueError, match=mensaje):
        Demarcacion("captafaros", **argumentos)


# --- CSV ------------------------------------------------------------------------------------------


def test_el_csv_lee_el_suministro_y_los_captafaros_solos(tmp_path: Path):
    ruta = tmp_path / "via.csv"
    ruta.write_text(
        f"{CABECERA};suministro;captafaros\n"
        "T1;0;1;1;;capa;riego_adherencia;;;;;sí;\n"
        "T1;;;;;capa;imprimacion;;;1,20;;no;\n"
        "T1;;;;;demarcacion;captafaros;;;;;;40\n",
        encoding="utf-8",
    )
    assert leer_tramos(ruta) == [
        _tramo(
            Capa("riego_adherencia", None, None, None, suministro=True),
            Capa("imprimacion", None, None, D("1.20")),
            demarcacion=(Demarcacion("captafaros", 1, captafaros=40),),
        )
    ]


@pytest.mark.parametrize(
    ("fila", "mensaje"),
    [
        ("T1;0;1;1;;capa;riego_adherencia;;;;;quizás;", r"fila 2\b.*'suministro'.*sí o no"),
        ("T1;0;1;1;;capa;carpeta;0,05;2,4;;;sí;", r"fila 2\b.*carpeta no usa suministro"),
        ("T1;0;1;1;;demarcacion;continua;;;;1;sí;", r"fila 2\b.*demarcación no usa suministro"),
        ("T1;0;1;1;;demarcacion;captafaros;;;;3;;40", r"fila 2\b.*captafaros no usa lineas"),
    ],
)
def test_el_csv_rechaza_el_suministro_o_los_captafaros_mal_puestos(
    tmp_path: Path, fila: str, mensaje: str
):
    ruta = tmp_path / "via.csv"
    ruta.write_text(f"{CABECERA};suministro;captafaros\n{fila}\n", encoding="utf-8")
    with pytest.raises(ValueError, match=mensaje):
        leer_tramos(ruta)


def test_la_muestra_de_hoy_se_lee_igual():
    muestra = Path(__file__).resolve().parents[2] / "data" / "samples" / "vial" / "via_ficticia.csv"
    tramos = leer_tramos(muestra)
    assert all(not c.suministro for t in tramos for c in t.capas)
    assert len(derivar_tramos(tramos)) == 20  # la memoria de cálculo del README de la muestra


# --- guardado y API -------------------------------------------------------------------------------


def _declarado() -> Tramo:
    return _tramo(
        Capa("riego_adherencia", None, None, None, suministro=True),
        Capa("imprimacion", None, None, D("1.2")),
        demarcacion=(Demarcacion("captafaros", 1, captafaros=40),),
    )


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


def test_lo_guardado_se_lee_igual(motor: Engine):
    with abrir_sesion(motor) as sesion:
        version = sesion.scalars(
            select(models.Presupuesto.id).where(models.Presupuesto.codigo == "VIV-001")
        ).one()
        vial.guardar_tramos(
            sesion, version, [_declarado()], usuario="Ana <ana>", ahora=datetime(2026, 11, 13)
        )
        assert vial.tramos_de_version(sesion, version) == [_declarado()]


def test_la_api_recibe_y_devuelve_el_suministro_y_los_captafaros_solos():
    respuesta = tramo_a_respuesta(_declarado())
    capas = respuesta.model_dump()["capas"]
    assert [c.get("suministro", False) for c in capas] == [True, False]
    assert (
        "suministro"
        not in tramo_a_respuesta(_tramo(Capa("imprimacion", None, None, D("1")))).model_dump()[
            "capas"
        ][0]
    )
    assert a_tramos([TramoEntrada.model_validate(respuesta.model_dump())]) == [_declarado()]


# --- la pista del 404 al llevar -------------------------------------------------------------------


def test_la_pista_del_ligante_sale_si_falta_el_apu_de_un_ligante():
    tramo = _tramo(Capa("riego_adherencia", None, None, D("0.4")))
    assert hoja_vial.pistas_de_lo_que_falta([tramo], [COD["riego_adherencia_ligante"]]) == [
        PISTA_LIGANTE
    ]
    assert hoja_vial.pistas_de_lo_que_falta([tramo], [COD["riego_adherencia"]]) == []


def test_la_pista_de_los_captafaros_sale_si_falta_la_linea_de_una_linea_con_captafaros():
    con = _tramo(demarcacion=(Demarcacion("continua", 1, captafaros=40),))
    sin = _tramo(demarcacion=(Demarcacion("continua", 1),))
    linea, pintura = COD["demarcacion_continua"], COD["pintura_demarcacion"]
    assert hoja_vial.pistas_de_lo_que_falta([con], [pintura]) == [PISTA_CAPTAFAROS]
    assert hoja_vial.pistas_de_lo_que_falta([con], [linea, pintura]) == [PISTA_CAPTAFAROS]
    assert hoja_vial.pistas_de_lo_que_falta([sin], [linea, pintura]) == []


def test_el_404_de_llevar_lleva_las_pistas_tras_los_codigos():
    error = hoja_edicion.PartidaFueraDelCatalogo(
        COD["riego_adherencia_ligante"], pistas=(PISTA_LIGANTE,)
    )
    assert error.codigos == (COD["riego_adherencia_ligante"],)
    assert str(error) == (
        f"La partida «{COD['riego_adherencia_ligante']}» no está en el catálogo: compóngala "
        f"primero en Componer. {PISTA_LIGANTE}"
    )


def _presupuesto(tramo: Tramo) -> Presupuesto:
    cero = D("0")
    return Presupuesto(
        "VIA-TEST",
        date(2026, 11, 13),
        "Bs",
        tuple(
            PartidaPresupuestada(
                i,
                ComposicionAPU(i.codigo_partida, i.descripcion, i.unidad, D("1")),
                ResultadoAPU(cero, cero, cero, cero, cero, D("1")),
            )
            for i in derivar_tramos([tramo])
        ),
    )
