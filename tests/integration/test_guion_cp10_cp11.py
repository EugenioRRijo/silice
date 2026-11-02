"""Las cifras esperadas de CP-10 y CP-11 del guion, comprobadas contra el sistema con base real.

`docs/guion_prueba_arenia.md` (CP-10 y CP-11) promete cifras que, hasta esta prueba, solo se
comprobaban como texto: total 2706,12; Dia 23; CV 2137,44 -> 2139,23; PE 1530,49 -> 1531,77; PU
9,45 -> 9,78; subida 2,26; 49 insumos; cotizacion 5,1648 -> 5,50. Aqui se aplican esos cambios a
la `001` de OF-001 (la misma que siembra `scripts/seed_of001.py`) con `ui.hoja`, la logica que
pintan las pantallas, y se compara con aritmetica aparte (+-0,01):

* el precio del tubo es el de la lista en bolivares entre la tasa (3 271,19 Bs / 633,3644 Bs/USD);
* la cantidad de la partida es la de la memoria del bano (`bano_of001.md`: 6,300 x 1,10 = 6,930 m);
* administracion 15 % y utilidad 10 % en cascada (x 1,15 x 1,10) y V = CV x 1,265;
* el punto de equilibrio es 0,15 / 0,265 de las ventas.

Nada de esto lee el resultado de la funcion bajo prueba para calcular lo esperado.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import pytest

from aplicacion import hoja
from core.catalog import Catalogo, abrir_sesion, crear_motor
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001

D = Decimal
TOL = D("0.01")
AHORA = datetime(2026, 10, 5, 17, 0, 0)

# Oraculos a mano (memoria, lista en bolivares y tasa MaPreX del 01/07/2026).
CANTIDAD_TUBO_M = D("6.300") * D("1.10")  # memoria del bano, seccion 3: 6,930 m
PRECIO_TUBO_USD = D("3271.19") / D("633.3644")  # 5,1648
CASCADA = D("1.15") * D("1.10")
PARTIDA = "AF-TUB-PVC-3/4"
DESCRIPCION_TUBO = "Tubo PVC 3/4 pulg A.B. presion agua fria [MT2050]"
TOTAL_001 = D("2703.86")


@pytest.fixture(scope="module")
def recorrido(tmp_path_factory):
    """CP-10 (edicion y guardado de la 002) y CP-11 (cotizacion y la 003) sobre la base real."""
    ruta = plantilla_of001(tmp_path_factory.mktemp("cp10_cp11") / "prueba_sf.db")
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            v1 = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
            antes = hoja.elaborar_borrador(v1.borrador, codigo="001")

            # CP-10 paso 2: la cantidad del tubo de 1 a 1,05 en la copia de la version
            composicion = v1.borrador.composiciones[PARTIDA]
            lineas = tuple(
                replace(m, cantidad=D("1.05")) if m.descripcion == DESCRIPCION_TUBO else m
                for m in composicion.materiales
            )
            assert lineas != composicion.materiales, "el guion nombra una linea que no existe"
            editado = replace(
                v1.borrador,
                composiciones={
                    **v1.borrador.composiciones,
                    PARTIDA: replace(composicion, materiales=lineas),
                },
            )
            despues = hoja.elaborar_borrador(editado, codigo="002")

            # paso 4: sin fuente no se guarda; paso 5: con fuente y responsable, si
            try:
                hoja.guardar_version(
                    sesion, catalogo, v1, editado, fuente="", responsable="Ing. Participante"
                )
                rechazo = ""
            except hoja.HojaInvalida as error:
                rechazo = str(error)
            guardada = hoja.guardar_version(
                sesion,
                catalogo,
                v1,
                editado,
                fuente="ficha tecnica del fabricante: 5 % de desperdicio en el tubo",
                responsable="Ing. Participante",
                ahora=AHORA,
            )

            # CP-11 paso 1: la pestaña Precios de la 002
            precios_002 = hoja.precios_de_version(sesion, NOMBRE_OF001, "002")
            tubo = next(f for f in precios_002 if f.descripcion == DESCRIPCION_TUBO)

            # paso 2: cotizar MAT-003 a 5,50
            cotizada = hoja.cotizar(
                sesion,
                catalogo,
                NOMBRE_OF001,
                "002",
                insumo=tubo.codigo,
                precio=D("5.50"),
                proveedor="Ferreteria Los Andes",
                numero="COT-2026-0412",
                fecha=date(2026, 10, 5),
                responsable="Ing. Participante",
                ahora=AHORA,
            )
            v3 = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, cotizada)
            tras_cotizar = hoja.elaborar_borrador(v3.borrador, codigo=cotizada)
            precios_003 = hoja.precios_de_version(sesion, NOMBRE_OF001, cotizada)
            registros_003 = hoja.registros_de_version(sesion, NOMBRE_OF001, cotizada)
            return {
                "antes": antes,
                "despues": despues,
                "rechazo": rechazo,
                "guardada": guardada,
                "tubo": tubo,
                "precios_002": precios_002,
                "cotizada": cotizada,
                "tras_cotizar": tras_cotizar,
                "precios_003": precios_003,
                "registros_003": registros_003,
            }
    finally:
        motor.dispose()


def _total(r) -> Decimal:
    return r.elaboracion.presupuesto.total


def _pu(r) -> Decimal:
    partida = next(
        p for p in r.elaboracion.presupuesto.partidas if p.item.codigo_partida == PARTIDA
    )
    return partida.resultado.precio_unitario


# --- CP-10 ---------------------------------------------------------------------------------------


def test_cp10_paso1_el_total_y_el_punto_de_equilibrio_de_la_001(recorrido):
    antes = recorrido["antes"]
    pe = antes.equilibrio
    assert abs(_total(antes) - TOTAL_001) <= TOL
    assert abs(pe.venta - D("2703.86")) <= TOL
    assert abs(pe.costo_variable - D("2137.44")) <= TOL
    assert abs(pe.costo_fijo - D("320.62")) <= TOL
    assert abs(pe.punto - D("1530.49")) <= TOL
    assert abs(pe.porcentaje - D("56.60")) <= TOL
    assert pe.periodo.split(" [")[0] == "Dia 23"
    # aritmetica aparte: V = CV x 1,265 y PE = 0,15 x V / 0,265
    assert abs(pe.costo_variable - TOTAL_001 / D("1.265")) <= TOL
    assert abs(pe.punto - TOTAL_001 * D("0.15") / D("0.265")) <= TOL


def test_cp10_paso3_la_subida_de_2_26_es_la_aritmetica_de_la_cantidad_y_el_precio(recorrido):
    antes, despues = recorrido["antes"], recorrido["despues"]
    subida = CANTIDAD_TUBO_M * D("0.05") * PRECIO_TUBO_USD * CASCADA
    assert abs(subida - D("2.26")) <= TOL  # la cifra del guion
    assert abs((_total(despues) - _total(antes)) - subida) <= D("0.001")
    assert abs(_total(despues) - D("2706.12")) <= TOL
    assert abs(_total(despues) - (TOTAL_001 + subida)) <= TOL


def test_cp10_paso3_el_precio_unitario_de_la_partida_pasa_de_9_45_a_9_78(recorrido):
    antes, despues = recorrido["antes"], recorrido["despues"]
    assert abs(_pu(antes) - D("9.45")) <= TOL
    assert abs(_pu(despues) - D("9.78")) <= TOL
    # el material no se divide entre el rendimiento: el PU sube 0,05 x precio x cascada
    assert abs((_pu(despues) - _pu(antes)) - D("0.05") * PRECIO_TUBO_USD * CASCADA) <= D("0.001")


def test_cp10_paso3_el_equilibrio_nuevo(recorrido):
    pe = recorrido["despues"].equilibrio
    total = D("2706.12")
    assert abs(pe.venta - total) <= TOL
    assert abs(pe.costo_variable - D("2139.23")) <= TOL
    assert abs(pe.costo_variable - total / D("1.265")) <= TOL
    assert abs(pe.punto - D("1531.77")) <= TOL
    assert abs(pe.punto - total * D("0.15") / D("0.265")) <= TOL
    assert pe.periodo.split(" [")[0] == "Dia 23"


def test_cp10_pasos4_y_5_sin_fuente_se_rechaza_y_con_fuente_se_guarda_la_002(recorrido):
    assert "fuente" in recorrido["rechazo"].lower()
    guardada = recorrido["guardada"]
    assert guardada.codigo == "002" and guardada.cambios == 1
    assert abs(guardada.total - D("2706.12")) <= TOL


# --- CP-11 ---------------------------------------------------------------------------------------


def test_cp11_paso1_la_pestana_precios_tiene_49_insumos_y_el_tubo_sin_referencia(recorrido):
    precios = recorrido["precios_002"]
    assert len(precios) == 49
    tubo = recorrido["tubo"]
    assert tubo.codigo == "MAT-003"
    assert abs(tubo.precio - PRECIO_TUBO_USD) <= D("0.0001")
    assert tubo.lista == "Lista MaPreX jul-2026 (OF-001)" and tubo.moneda == "USD"
    assert tubo.estado == "Sin referencia ni cotización: el precio no tiene fuente"


def test_cp11_paso3_la_cotizacion_cambia_solo_ese_insumo_y_la_003_es_la_aritmetica(recorrido):
    """MAT-003 solo lo usa AF-TUB-PVC-3/4 (6,930 m x 1,05): la 003 sube (5,50 - 5,1648) x eso."""
    segunda, tercera = recorrido["despues"], recorrido["tras_cotizar"]
    assert recorrido["cotizada"] == "003"
    subida = (D("5.50") - PRECIO_TUBO_USD) * CANTIDAD_TUBO_M * D("1.05") * CASCADA
    assert abs((_total(tercera) - _total(segunda)) - subida) <= D("0.001")
    assert abs(_total(tercera) - (D("2706.12") + subida)) <= TOL

    precios_003 = {f.codigo: f for f in recorrido["precios_003"]}
    assert len(precios_003) == 49
    assert precios_003["MAT-003"].precio == D("5.50")
    assert precios_003["MAT-003"].estado == "OK"
    assert "Ferreteria Los Andes" in precios_003["MAT-003"].cotizacion
    assert "COT-2026-0412" in precios_003["MAT-003"].cotizacion
    # ningun otro insumo cambio de precio
    antes = {f.codigo: f.precio for f in recorrido["precios_002"]}
    cambiados = [c for c, f in precios_003.items() if f.precio != antes[c]]
    assert cambiados == ["MAT-003"]


def test_cp11_paso4_el_registro_de_la_003_es_el_que_dice_el_guion(recorrido):
    (registro,) = recorrido["registros_003"]
    assert (registro.objeto, registro.clave, registro.campo) == ("precio", "MAT-003", "cotizacion")
    assert abs(D(registro.valor_anterior) - PRECIO_TUBO_USD) <= D("0.0001")
    assert D(registro.valor_nuevo) == D("5.50")
    assert "COT-2026-0412" in registro.fuente and "Ferreteria Los Andes" in registro.fuente
    assert registro.responsable == "Ing. Participante"


def test_cp11_paso_negativo_cotizar_sin_proveedor_o_sin_fuente_se_rechaza(tmp_path):
    """Paso negativo del guion: una cotizacion sin proveedor, sin numero o sin responsable no se
    registra y no deja ninguna version nueva."""
    ruta = plantilla_of001(tmp_path / "negativo.db")
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            base = {
                "insumo": "MAT-003",
                "precio": D("5.50"),
                "proveedor": "Ferreteria Los Andes",
                "numero": "COT-2026-0412",
                "fecha": date(2026, 10, 5),
                "responsable": "Ing. Participante",
            }
            for campo in ("proveedor", "numero", "responsable"):
                with pytest.raises(hoja.HojaInvalida):
                    hoja.cotizar(sesion, catalogo, NOMBRE_OF001, "001", **{**base, campo: "  "})
            assert hoja.codigo_vigente(sesion, NOMBRE_OF001) == "001"
    finally:
        motor.dispose()
