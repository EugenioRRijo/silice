"""Las cifras tecleadas en la Hoja: coma decimal y punto de miles (regla de Eugenio, 2026-10-25).

Resuelve la decisión D-8 de la Hoja (`docs/especificaciones/2026-10-19-hoja-react-design.md`): la
hoja rechazaba la coma («Decimales con punto, por ejemplo 2.5: la coma no se acepta»). Ahora lo que
se escribe en una celda o un cuadro se lee con la regla única (`aplicacion.cifras.cifra_escrita`) y
lo que la vista pone en esas celdas sale escrito igual, para que una celda que nadie toca vuelva
sin cambio (la ida y vuelta de abajo). Caso: OF-001. Oráculos escritos a mano.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion import hoja, hoja_vista
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_borradores import Registro
from core.catalog import Catalogo, abrir_sesion, crear_motor
from tests.fixtures import caso_of001
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001

D = Decimal
REGLA = "Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56."
#: AF-LLAVE es el renglón 3 de OF-001 (orden de partida y luego de origen) y vale 3.
LLAVE = "AF-LLAVE|esp_fuentes:F1;esp_fuentes:FC1;esp_puntos:P1;esp_puntos:P2;esp_puntos:PC1"


@pytest.fixture(scope="module")
def _abierta(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("hoja_cifras")
    copia = carpeta / "copia.db"
    shutil.copyfile(plantilla_of001(carpeta / "of001.db"), copia)
    motor = crear_motor(f"sqlite:///{Path(copia).as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return hoja.abrir_version(
                sesion, Catalogo(sesion), NOMBRE_OF001, "001", fecha_evaluacion=caso_of001.FECHA
            )
    finally:
        motor.dispose()


def _vivo(abierta, borrador=None):
    return Registro().crear("f", "caso", NOMBRE_OF001, "001", borrador or abierta.borrador, abierta)


# --- ida y vuelta: lo que la vista pone en un campo editable vuelve igual ------------------------


def test_los_parametros_se_ven_con_coma_y_vuelven_iguales(_abierta) -> None:
    vista = hoja_vista.vista_parametros(_vivo(_abierta), "USD", False)
    textos = {c.clave: c.valor for c in vista.campos}

    # Los de OF-001 (FCAS 6,00; bono 5,8100; administración 0,15; utilidad 0,10), con su escala.
    assert textos == {
        "fcas": "6,00",
        "bono_alimentacion": "5,8100",
        "administracion": "0,15",
        "utilidad": "0,10",
    }
    assert hoja.parametros_desde_texto(textos) == _abierta.borrador.parametros


def test_las_cantidades_del_presupuesto_se_ven_con_coma_y_sin_tocar_no_escriben_nada(
    _abierta,
) -> None:
    borrador = _abierta.borrador
    vista = hoja_vista.vista_presupuesto(_vivo(_abierta))
    filas = [{"clave": f.clave, "cantidad": f.cantidad} for f in vista.filas]

    assert any("," in f["cantidad"] for f in filas)  # hay decimales: la prueba no es vacía
    assert not any("." in f["cantidad"] for f in filas)  # ninguna llega a mil en OF-001
    assert hoja.cantidades_desde_filas(filas, hoja.items_sin_escribir(borrador)) == {}


def test_la_matriz_del_plan_se_ve_con_coma_y_sin_tocar_reconstruye_el_plan(_abierta) -> None:
    vista = hoja_vista.vista_plan(_vivo(_abierta))
    filas = [{"partida": f.partida, **f.valores} for f in vista.filas]

    assert all("." not in v for f in vista.filas for v in f.valores.values())
    plan = hoja.plan_desde_filas(filas, list(vista.etiquetas))
    assert plan == list(hoja.elaborar_borrador(_abierta.borrador).plan)


def test_las_tablas_del_espacio_se_ven_con_coma_y_sin_tocar_dan_el_mismo_espacio(
    _abierta,
) -> None:
    espacio = _abierta.borrador.espacio
    vista = hoja_vista.vista_espacio(_vivo(_abierta))

    for tabla, columnas in hoja.COLUMNAS_CIFRA.items():
        for fila in vista.filas[tabla]:
            for columna in columnas:
                assert "." not in fila[columna], (tabla, columna, fila[columna])
    assert vista.filas["ambientes"][0]["ancho"] == "1,5"  # BAN-01 mide 2 x 1,5 x 2,5
    assert hoja.espacio_desde_filas(vista.filas, base=espacio, tecleado=True) == espacio


def test_el_apu_se_ve_con_coma_y_sin_tocar_es_el_mismo(_abierta) -> None:
    borrador = _abierta.borrador
    codigo = next(iter(borrador.composiciones))
    detalle = hoja_vista.vista_apu(_vivo(_abierta), codigo).detalle
    assert detalle is not None
    tablas = {g.clave: [{"cantidad": f["cantidad"]} for f in g.filas] for g in detalle.grupos}

    base = borrador.composiciones[codigo]
    nueva = hoja.composicion_con_cantidades(
        base, tablas["materiales"], tablas["equipos"], tablas["mano de obra"], detalle.rendimiento
    )
    assert nueva == base


# --- lo que se teclea --------------------------------------------------------------------------


def _tabla(borrador, **cambios: str) -> list[dict[str, str]]:
    """La tabla del Presupuesto escrita a mano: cada cantidad con coma decimal y sin miles."""
    items = hoja.items_sin_escribir(borrador)
    return [
        {"clave": clave, "cantidad": cambios.get(clave, format(i.cantidad, "f").replace(".", ","))}
        for clave, i in zip(hoja.claves_de_items(items), items, strict=True)
    ]


def test_tres_mil_con_punto_de_miles_es_tres_mil_y_tres_coma_cero_es_tres(_abierta) -> None:
    """El riesgo de la regla al revés: AF-LLAVE vale 3. «3,000» es tres (nada que escribir) y
    «3.000» es tres mil (una cantidad escrita), nunca al contrario."""
    borrador = _abierta.borrador
    items = hoja.items_sin_escribir(borrador)

    assert hoja.cantidades_desde_filas(_tabla(borrador, **{LLAVE: "3,000"}), items) == {}
    assert hoja.cantidades_desde_filas(_tabla(borrador, **{LLAVE: "3.000"}), items) == {
        LLAVE: D(3000)
    }
    assert hoja.cantidades_desde_filas(_tabla(borrador, **{LLAVE: "1.234,5"}), items) == {
        LLAVE: D("1234.5")
    }


@pytest.mark.parametrize("texto", ["2.5", "1,234.5", "1 234", "1e3"])
def test_una_cantidad_ambigua_dice_la_fila_y_la_regla(_abierta, texto) -> None:
    borrador = _abierta.borrador
    with pytest.raises(HojaInvalida) as error:
        hoja.cantidades_desde_filas(
            _tabla(borrador, **{LLAVE: texto}), hoja.items_sin_escribir(borrador)
        )
    assert str(error.value) == (
        f"presupuesto, fila 3 (AF-LLAVE): cantidad: «{texto}» no se entiende como número. {REGLA}"
    )


def test_un_parametro_con_punto_decimal_dice_el_campo_y_la_regla() -> None:
    textos = {"fcas": "0.12", "bono_alimentacion": "5,81", "administracion": "0,15"}
    with pytest.raises(HojaInvalida) as error:
        hoja.parametros_desde_texto({**textos, "utilidad": "0,10"})
    assert str(error.value) == (f"parametros: fcas: «0.12» no se entiende como número. {REGLA}")


def test_un_parametro_con_miles_y_coma_se_lee_exacto() -> None:
    parametros = hoja.parametros_desde_texto(
        {"fcas": "1.006,00", "bono_alimentacion": "5,81", "administracion": "0,15", "utilidad": "0"}
    )
    assert parametros.fcas == D("1006.00") and parametros.bono_alimentacion == D("5.81")


def test_un_parametro_vacio_dice_que_falta_el_numero() -> None:
    with pytest.raises(HojaInvalida) as error:
        hoja.parametros_desde_texto({"fcas": "6", "bono_alimentacion": "5", "administracion": "0"})
    assert str(error.value) == f"parametros: utilidad: Escriba un número. {REGLA}"


def test_una_fraccion_del_plan_con_punto_se_rechaza_y_la_suma_se_dice_con_coma() -> None:
    filas = [{"partida": "AF-LLAVE", "Dia 1": "0.5", "Dia 2": "0,5"}]
    with pytest.raises(HojaInvalida) as error:
        hoja.plan_desde_filas(filas, ["Dia 1", "Dia 2"])
    assert str(error.value) == (
        f"plan, partida AF-LLAVE: Dia 1: «0.5» no se entiende como número. {REGLA}"
    )

    with pytest.raises(HojaInvalida) as error:
        hoja.plan_desde_filas(
            [{"partida": "AF-LLAVE", "Dia 1": "0,25", "Dia 2": "0,5"}], ["Dia 1", "Dia 2"]
        )
    assert "las fracciones suman 0,75 y deben sumar exactamente 1" in str(error.value)

    assert hoja.plan_desde_filas(
        [{"partida": "AF-LLAVE", "Dia 1": "0,25", "Dia 2": "0,75"}], ["Dia 1", "Dia 2"]
    ) == [("Dia 1", (("AF-LLAVE", D("0.25")),)), ("Dia 2", (("AF-LLAVE", D("0.75")),))]


def test_el_rendimiento_del_apu_con_miles_y_coma(_abierta) -> None:
    base = next(iter(_abierta.borrador.composiciones.values()))
    filas = [
        [{"cantidad": format(linea.cantidad, "f").replace(".", ",")} for linea in rubro]
        for rubro in (base.materiales, base.equipos, base.mano_obra)
    ]
    nueva = hoja.composicion_con_cantidades(base, *filas, "1.020,5")
    assert nueva == replace(base, rendimiento=D("1020.5"))

    with pytest.raises(HojaInvalida) as error:
        hoja.composicion_con_cantidades(base, *filas, "20.5")
    assert str(error.value) == f"rendimiento: «20.5» no se entiende como número. {REGLA}"


def test_un_largo_del_espacio_con_punto_decimal_se_rechaza_con_la_regla(_abierta) -> None:
    espacio = _abierta.borrador.espacio
    filas = hoja_vista.vista_espacio(_vivo(_abierta)).filas
    ambientes = [dict(f) for f in filas["ambientes"]]
    ambientes[0]["largo"] = "2.5"
    with pytest.raises(HojaInvalida) as error:
        hoja.espacio_desde_filas({**filas, "ambientes": ambientes}, base=espacio, tecleado=True)
    assert f"largo: «2.5» no se entiende como número. {REGLA}" in str(error.value)

    ambientes[0]["largo"] = "1.002,5"
    nuevo = hoja.espacio_desde_filas({**filas, "ambientes": ambientes}, base=espacio, tecleado=True)
    assert nuevo.ambientes[0].largo == D("1002.5")


def test_los_vertices_conservan_x_y_z_con_punto_decimal_y_la_pendiente_va_con_coma(
    _abierta,
) -> None:
    """Excepción declarada: en «vértices» la coma separa las coordenadas (x,y,z), así que sus
    decimales siguen con punto; la pendiente, una cifra sola, va con coma decimal."""
    espacio = _abierta.borrador.espacio
    filas = hoja_vista.vista_espacio(_vivo(_abierta)).filas
    tramo = {
        "recorrido_id": "R-PRUEBA",
        "punto_id": "D1",
        "circuito_id": "",
        "orden": "1",
        "superficie": "piso",
        "empotrado": "",
        "pendiente": "0,02",
        "vertices": "0,0,0; 2.5,0,0",
    }
    nuevo = hoja.espacio_desde_filas({**filas, "tramos": [tramo]}, base=espacio, tecleado=True)
    declarado = next(r for r in nuevo.recorridos if r.id == "R-PRUEBA")
    assert declarado.tramos[0].pendiente == D("0.02")
    assert [(v.x, v.y, v.z) for v in declarado.tramos[0].vertices] == [
        (D(0), D(0), D(0)),
        (D("2.5"), D(0), D(0)),
    ]
    # y la vista lo devuelve igual: la pendiente con coma, los vértices como estaban
    vuelta = hoja.filas_editables_del_espacio(nuevo)["tramos"]
    assert [(t["pendiente"], t["vertices"]) for t in vuelta] == [("0,02", "0,0,0; 2.5,0,0")]


def test_el_texto_de_maquina_del_espacio_sigue_con_punto_decimal(_abierta) -> None:
    """El asistente de IA y el banco del experimento arman las tablas con `filas_desde_espacio`
    (punto decimal) y no las teclea nadie: leerlas con la regla convertiría 1,125 m en 1.125 m
    (mil ciento veinticinco). Sin `tecleado`, «1.125» sigue siendo uno coma ciento veinticinco."""
    espacio = _abierta.borrador.espacio
    filas = hoja.filas_desde_espacio(espacio)
    assert hoja.espacio_desde_filas(filas, base=espacio) == espacio
    ambientes = [dict(f) for f in filas["ambientes"]]
    ambientes[0]["largo"] = "1.125"
    nuevo = hoja.espacio_desde_filas({**filas, "ambientes": ambientes}, base=espacio)
    assert nuevo.ambientes[0].largo == D("1.125")
