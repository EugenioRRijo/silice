"""Lector de tramos (plan vial, Tarea 7): `adapters/vial/tabular.py`, Foco de revision 3.

Las cantidades esperadas de la muestra salen de la memoria de calculo a mano de
`data/samples/vial/README.md`, copiadas aqui como literales.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.modelo import Capa, Demarcacion, Tramo
from adapters.vial.tabular import AdaptadorVial, leer_tramos
from core.contracts import AdaptadorDominio, Dominio

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "vial" / "via_ficticia.csv"

CABECERA = (
    "tramo;progresiva_ini_km;progresiva_fin_km;ancho_m;distancia_planta_km;elemento;tipo;"
    "espesor_m;densidad_t_m3;dosis_l_m2;lineas"
)


def _csv(tmp_path: Path, *filas: str, cabecera: str = CABECERA) -> Path:
    ruta = tmp_path / "tramos.csv"
    ruta.write_text("\n".join((cabecera, *filas)) + "\n", encoding="utf-8")
    return ruta


def test_lee_coma_decimal(tmp_path):  # «7,30» -> Decimal("7.30") (Foco 3)
    ruta = _csv(tmp_path, "T1;0;1;7,30;12;capa;carpeta;0,05;2,35;;")
    (tramo,) = leer_tramos(ruta)
    assert tramo == Tramo(
        "T1",
        Decimal("0"),
        Decimal("1"),
        Decimal("7.30"),
        (Capa("carpeta", Decimal("0.05"), Decimal("2.35"), None),),
        (),
        Decimal("12"),
    )


def test_lee_punto_decimal_con_coma_como_separador(tmp_path):
    cabecera = CABECERA.replace(";", ",")
    ruta = _csv(tmp_path, "T1,0,1,7.30,,capa,base_granular,0.20,,,", cabecera=cabecera)
    (tramo,) = leer_tramos(ruta)
    assert tramo.ancho_m == Decimal("7.30")
    assert tramo.distancia_planta_km is None
    assert tramo.capas == (Capa("base_granular", Decimal("0.20"), None, None),)


def test_punto_de_miles_con_coma_decimal(tmp_path):
    ruta = _csv(tmp_path, "T1;0;1.000,5;7,30;;capa;base_granular;0,20;;;")
    (tramo,) = leer_tramos(ruta)
    assert tramo.progresiva_fin_km == Decimal("1000.5")


def test_fila_invertida_dice_su_numero(tmp_path):
    ruta = _csv(
        tmp_path,
        "T1;0;1;7,30;;capa;base_granular;0,20;;;",
        "T2;2;1;7,30;;capa;base_granular;0,20;;;",
    )
    with pytest.raises(ValueError, match=r"fila 3\b") as error:
        leer_tramos(ruta)
    assert "T2" in str(error.value)
    assert "tramos.csv" in str(error.value)


def test_capa_desconocida_rechazada(tmp_path):
    ruta = _csv(
        tmp_path,
        "T1;0;1;7,30;;capa;base_granular;0,20;;;",
        "T1;;;;;capa;asfalto;0,05;2,35;;",
    )
    with pytest.raises(ValueError, match=r"fila 3\b.*asfalto"):
        leer_tramos(ruta)


def test_elemento_desconocido_rechazado(tmp_path):
    ruta = _csv(tmp_path, "T1;0;1;7,30;;senal;flecha;;;;")
    with pytest.raises(ValueError, match=r"fila 2\b.*senal"):
        leer_tramos(ruta)


def test_dato_no_numerico_dice_fila_y_columna(tmp_path):
    ruta = _csv(tmp_path, "T1;0;1;siete;;capa;base_granular;0,20;;;")
    with pytest.raises(ValueError, match=r"fila 2\b.*ancho_m.*siete"):
        leer_tramos(ruta)


@pytest.mark.parametrize("valor", ["NaN", "Infinity", "-inf"])
def test_valor_no_finito_rechazado(tmp_path, valor):
    ruta = _csv(tmp_path, f"T1;0;1;{valor};;capa;base_granular;0,20;;;")
    with pytest.raises(ValueError, match=r"fila 2\b.*ancho_m"):
        leer_tramos(ruta)


def test_dato_del_tramo_que_no_coincide(tmp_path):
    ruta = _csv(
        tmp_path,
        "T1;0;1;7,30;;capa;base_granular;0,20;;;",
        "T1;;;7,00;;capa;carpeta;0,05;2,35;;",
    )
    with pytest.raises(ValueError, match=r"fila 3\b.*ancho_m"):
        leer_tramos(ruta)


def test_dato_que_la_capa_no_usa_dice_su_fila(tmp_path):
    ruta = _csv(tmp_path, "T1;0;1;7,30;;capa;riego_adherencia;0,05;;0,5;")
    with pytest.raises(ValueError, match=r"fila 2\b.*espesor"):
        leer_tramos(ruta)


def test_faltan_columnas(tmp_path):
    ruta = _csv(
        tmp_path, "T1;0;1;7,30", cabecera="tramo;progresiva_ini_km;progresiva_fin_km;ancho_m"
    )
    with pytest.raises(ValueError, match="faltan las columnas"):
        leer_tramos(ruta)


def test_archivo_sin_tramos(tmp_path):
    with pytest.raises(ValueError, match="ningun tramo"):
        leer_tramos(_csv(tmp_path))


def test_archivo_binario(tmp_path):
    ruta = tmp_path / "tramos.csv"
    ruta.write_bytes(b"\xff\xfe\x00\x81binario")
    with pytest.raises(ValueError, match="ilegible"):
        leer_tramos(ruta)


def test_lee_la_muestra_con_sus_tramos_y_demarcacion():
    tramos = leer_tramos(MUESTRA)
    assert [t.id for t in tramos] == ["T1", "T2", "T3"]
    assert tramos[0].demarcacion == (Demarcacion("continua", 2), Demarcacion("discontinua", 1))
    assert tramos[2].capas == (Capa("bacheo", Decimal("0.10"), Decimal("2.30"), None),)


def test_via_ficticia_completa():
    """La muestra produce los 18 items de la memoria de calculo del README, en este orden."""
    adaptador = AdaptadorVial()
    assert isinstance(adaptador, AdaptadorDominio)
    assert AdaptadorVial.dominio is Dominio.CIVIL
    items = adaptador.extraer(MUESTRA)
    obtenido = [(i.codigo_partida, i.origen_id, i.cantidad, i.unidad) for i in items]
    c = {clave: codigo for clave, (codigo, _, _) in PARTIDAS_VIALES.items()}
    assert obtenido == [
        (c["fresado"], "tramo:T1:capa:1", Decimal("438"), "m3"),
        (c["riego_adherencia"], "tramo:T1:capa:2", Decimal("8760"), "m2"),
        (c["riego_adherencia_ligante"], "tramo:T1:capa:2", Decimal("3504"), "l"),
        (c["carpeta"], "tramo:T1:capa:3", Decimal("8760"), "m2"),
        (c["carpeta_mezcla"], "tramo:T1:capa:3", Decimal("1029.3"), "t"),
        (c["transporte_mezcla"], "tramo:T1:capa:3", Decimal("15439.5"), "t·km"),
        (c["demarcacion_continua"], "tramo:T1:demarcacion:1", Decimal("2400"), "m"),
        (c["demarcacion_discontinua"], "tramo:T1:demarcacion:2", Decimal("450"), "m"),
        (c["subbase_granular"], "tramo:T2:capa:1", Decimal("1300"), "m3"),
        (c["base_granular"], "tramo:T2:capa:2", Decimal("1040"), "m3"),
        (c["imprimacion"], "tramo:T2:capa:3", Decimal("5200"), "m2"),
        (c["imprimacion_ligante"], "tramo:T2:capa:3", Decimal("6240"), "l"),
        (c["carpeta"], "tramo:T2:capa:4", Decimal("5200"), "m2"),
        (c["carpeta_mezcla"], "tramo:T2:capa:4", Decimal("478.4"), "t"),
        (c["transporte_mezcla"], "tramo:T2:capa:4", Decimal("8611.2"), "t·km"),
        (c["bacheo"], "tramo:T3:capa:1", Decimal("15"), "m3"),
        (c["bacheo_mezcla"], "tramo:T3:capa:1", Decimal("34.5"), "t"),
        (c["transporte_mezcla"], "tramo:T3:capa:1", Decimal("621"), "t·km"),
    ]
    assert adaptador.extraer(MUESTRA) == items  # determinista
