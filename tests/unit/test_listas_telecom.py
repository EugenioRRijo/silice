"""Las dos listas canónicas de UC‑02 del dominio telecom (Sesión M1.3) son exactamente las que
deriva `scripts/derivar_listas_telecom.py`, y ese script aplica el criterio que documenta.

Los CSV son la forma tabular; la derivación (fixture ARENAZA vía `scripts/seed_telecom.py` y
`referencia_telecom.csv` de M0.2) es la fuente. Aquí no se transcribe ningún precio: cada valor
esperado se lee de esas fuentes.
"""

from __future__ import annotations

import csv
from decimal import ROUND_HALF_UP, Decimal

from core.catalog.precios import leer_lista_precios
from scripts import derivar_listas_telecom as listas
from scripts.seed_telecom import MARCA_AJUSTE, METROS_POR_TUBO, UNIDAD_SUMA_GLOBAL

CANTIDAD_LISTA_1 = 27
CANTIDAD_LISTA_2 = 5
#: Dos lineas de ajuste, Micelaneos, los dos renglones contradichos y el organizador.
CANTIDAD_EXCLUIDOS = 6


def _referencia_maprex() -> dict[str, dict[str, str]]:
    with open(listas.RUTA_REFERENCIA_MAPREX, newline="", encoding="utf-8") as archivo:
        return {fila["ref_maprex"]: fila for fila in csv.DictReader(archivo)}


def test_los_csv_en_disco_son_los_que_deriva_el_script():
    lista_1, _, lista_2 = listas.derivar_listas()

    assert listas.leer_csv(listas.RUTA_LISTA_ARENAZA) == [listas.fila_csv(f) for f in lista_1]
    assert listas.leer_csv(listas.RUTA_LISTA_MAPREX) == [listas.fila_csv(f.fila) for f in lista_2]


def test_verificar_no_encuentra_diferencias(capsys):
    assert listas.main(["--verificar"]) == 0
    assert "coinciden" in capsys.readouterr().out


def test_las_dos_listas_se_leen_por_uc02():
    """El formato canónico: `core.catalog.precios.leer_lista_precios` las acepta tal cual."""
    assert len(leer_lista_precios(listas.RUTA_LISTA_ARENAZA)) == CANTIDAD_LISTA_1
    assert len(leer_lista_precios(listas.RUTA_LISTA_MAPREX)) == CANTIDAD_LISTA_2


def test_lista_1_solo_insumos_con_un_precio_no_contradicho():
    lista_1, _ = listas.derivar_lista_arenaza()

    assert len(lista_1) == CANTIDAD_LISTA_1
    assert not any(fila.insumo.startswith(MARCA_AJUSTE) for fila in lista_1)
    assert not any(fila.unidad == UNIDAD_SUMA_GLOBAL for fila in lista_1)
    assert len({fila.clave for fila in lista_1}) == CANTIDAD_LISTA_1  # una fila por insumo
    assert all(fila.precio > 0 for fila in lista_1)


def test_lista_1_excluye_los_cuatro_casos_del_modulo():
    _, excluidos = listas.derivar_lista_arenaza()

    assert len(excluidos) == CANTIDAD_EXCLUIDOS
    ajustes = [d for d, m in excluidos.items() if m == listas.MOTIVO_AJUSTE]
    globales = [d for d, m in excluidos.items() if m == listas.MOTIVO_SUMA_GLOBAL]
    contradichos = [d for d, m in excluidos.items() if m.startswith("el total impreso contradice")]
    dos_precios = [d for d, m in excluidos.items() if m.startswith("dos precios distintos")]

    assert len(ajustes) == 2 and all(d.startswith(MARCA_AJUSTE) for d in ajustes)
    assert globales == ["Micelaneos"]
    assert sorted(contradichos) == [
        "Camara Bullet Ip 4mp Intemperie",
        "Conector Jack Coupler Ubiquiti Rj45",
    ]
    assert dos_precios == ["Organizador De Cables Individuales 20cm 100 Und"]
    assert excluidos[dos_precios[0]].endswith("18.00 y 19.00")


def test_el_tubo_corrugado_entra_en_la_lista_1_al_precio_por_tubo():
    """El insumo del hallazgo 80/90 conserva su precio de mercado (99,75 por tubo de 30 m)."""
    lista_1, _ = listas.derivar_lista_arenaza()

    tubos = [fila for fila in lista_1 if fila.insumo.startswith("Tubo Corrugado")]

    assert len(tubos) == 2  # el catalogo lo guarda bajo las dos descripciones impresas (P1 y P2)
    assert {fila.precio for fila in tubos} == {Decimal("99.75")}
    assert all(f"(tubo de {METROS_POR_TUBO:f} m)" in fila.insumo for fila in tubos)


def test_lista_2_se_deriva_de_la_referencia_maprex_con_su_tasa():
    lista_2 = listas.derivar_lista_maprex()

    assert len(lista_2) == CANTIDAD_LISTA_2
    for fila in lista_2:
        esperado = (fila.precio_bs * fila.correspondencia.factor / listas.TASA).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        assert fila.fila.precio == esperado, fila.fila.insumo


def test_lista_2_factor_1_reproduce_el_precio_usd_de_m02():
    """Sin conversión de unidad, el precio de la lista 2 es literalmente el `precio_usd` de M0.2;
    la única conversión admitida es la del tubo corrugado (metro -> tubo de 30 m, `ELE906`)."""
    referencia = _referencia_maprex()

    for fila in listas.derivar_lista_maprex():
        ref = fila.correspondencia.ref_maprex
        assert fila.precio_bs == Decimal(referencia[ref]["precio_bs"])
        if fila.correspondencia.factor == 1:
            assert fila.fila.precio == Decimal(referencia[ref]["precio_usd"]), ref
        else:
            assert (ref, fila.correspondencia.factor) == ("ELE906", METROS_POR_TUBO)


def test_toda_fila_de_la_lista_2_tiene_su_precio_arenaza_y_lo_cambia():
    lista_1, _, lista_2 = listas.derivar_listas()
    arenaza = {fila.clave: fila.precio for fila in lista_1}

    assert all(fila.fila.clave in arenaza for fila in lista_2)
    # Ningun precio MaPreX coincide con el ARENAZA: las cinco filas producen un CambioPrecio.
    assert all(fila.fila.precio != arenaza[fila.fila.clave] for fila in lista_2)
