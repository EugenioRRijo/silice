"""3b-B3C (T10, 3c-2): `cantidades_desde_filas`, `plan_desde_filas`, `parametros_desde_texto` y
`con_plan_secuencial` contra `ui.hoja` VIVO.

`aplicacion/hoja.py` es una copia de `ui/hoja.py` (Plan C: la clasica esta en el congelado del
experimento y no se toca). Esta prueba (que SI puede importar `ui`) corre en las dos las funciones
que validan las rutas E2 a E5 de la sub-rebanada 3c-2 y compara lo que producen: los diccionarios y
los planes, los textos de error (igualdad exacta de cadena) y lo que el borrador dice despues
(total, punto de equilibrio, cambios). Casos: OF-001 (con plan y sin el) y TI-001 (50 503,27 USD,
10 periodos de plan).

Oraculos a mano, ninguno sale de la copia:

* total 2 703,86 USD; CV 2 137,44; PE 1 530,49 en el «Dia 23»; 56,60 % (memoria de OF-001);
* administracion 0,20: total 2 821,42; PE 1 763,39; 62,50 % (P13, confirmado por el arbitro);
* AF-LLAVE de 3 a 5: CD = 10,4338 (llave 4 907,50 Bs / 633,3644 + herramientas 9 060,00 Bs /
  633,3644 / rendimiento 20 + mano de obra con FCAS 6,00 y bono) y Δtotal = 2 x 10,4338 x 1,15 x
  1,10 = 26,3975 (P15: se compara con tolerancia 0,001 contra el valor exacto);
* los textos de error de `docs/especificaciones/2026-10-19-hoja-react-design.md` §2.5 y §6.2
  (3c-B2, 3c-B5, 3c-B12), con la posicion de la fila a mano: AF-LLAVE es el renglon 3 de
  OF-001 (orden alfabetico de partida y luego de origen).

Si la copia y la clasica divergen, la unica que se corrige es la copia: `ui/hoja.py` esta
congelado. Un cambio legitimo del comportamiento exige cambiar esta prueba con el aval de Eugenio.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion import hoja as copia
from aplicacion.errores import HojaInvalida
from core.catalog import Catalogo, abrir_sesion, crear_motor
from tests.fixtures import caso_of001, caso_ti001
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    NOMBRE_TI001,
    plantilla_of001,
    plantilla_ti001,
)
from ui import hoja as clasica

D = Decimal
MODULOS = [pytest.param(clasica, id="clasica"), pytest.param(copia, id="copia")]

#: La clave del renglon de las llaves de OF-001 (tres llaves: F1, FC1 y los puntos P1, P2 y PC1).
LLAVE = "AF-LLAVE|esp_fuentes:F1;esp_fuentes:FC1;esp_puntos:P1;esp_puntos:P2;esp_puntos:PC1"
FILA_LLAVE = 3  # AF-CODO-1/2, AF-CODO-3/4, AF-LLAVE...


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> tuple[Path, Path]:
    carpeta = tmp_path_factory.mktemp("paridad_secciones")
    return plantilla_of001(carpeta / "of001.db"), plantilla_ti001(carpeta / "ti001.db")


def _abrir(plantilla: Path, destino: Path, modulo, nombre: str, codigo: str):
    copiada = destino / f"{modulo.__name__}.db"
    shutil.copyfile(plantilla, copiada)
    motor = crear_motor(f"sqlite:///{copiada.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return modulo.abrir_version(
                sesion, Catalogo(sesion), nombre, codigo, fecha_evaluacion=caso_of001.FECHA
            ).borrador
    finally:
        motor.dispose()


@pytest.fixture(scope="module")
def _of001(_plantillas, tmp_path_factory) -> dict:
    destino = tmp_path_factory.mktemp("of001_secciones")
    return {m: _abrir(_plantillas[0], destino, m, NOMBRE_OF001, "001") for m in (clasica, copia)}


@pytest.fixture(scope="module")
def _ti001(_plantillas, tmp_path_factory) -> dict:
    destino = tmp_path_factory.mktemp("ti001_secciones")
    return {
        m: _abrir(_plantillas[1], destino, m, NOMBRE_TI001, caso_ti001.CODIGO)
        for m in (clasica, copia)
    }


def _tabla(modulo, borrador, **cambios: str) -> list[dict[str, str]]:
    """La tabla del Presupuesto tal como la siembra la clasica: clave y cantidad vigente."""
    items = modulo.items_sin_escribir(borrador)
    vigentes = modulo.items_elaborados(borrador)
    filas = [
        {"clave": c, "cantidad": modulo.texto_numero(i.cantidad)}
        for c, i in zip(modulo.claves_de_items(items), vigentes, strict=True)
    ]
    for fila in filas:
        if fila["clave"] in cambios:
            fila["cantidad"] = cambios[fila["clave"]]
    return filas


# --- cantidades_desde_filas -------------------------------------------------------------------


@pytest.mark.parametrize("modulo", MODULOS)
def test_la_tabla_sin_tocar_no_escribe_ninguna_cantidad(modulo, _of001) -> None:
    borrador = _of001[modulo]
    items = modulo.items_sin_escribir(borrador)
    assert modulo.claves_de_items(items)[FILA_LLAVE - 1] == LLAVE
    assert modulo.cantidades_desde_filas(_tabla(modulo, borrador), items) == {}


@pytest.mark.parametrize("modulo", MODULOS)
def test_una_cantidad_distinta_de_la_calculada_queda_escrita_como_decimal(modulo, _of001) -> None:
    borrador = _of001[modulo]
    items = modulo.items_sin_escribir(borrador)
    escritas = modulo.cantidades_desde_filas(_tabla(modulo, borrador, **{LLAVE: "5"}), items)
    assert escritas == {LLAVE: D(5)}
    assert isinstance(escritas[LLAVE], Decimal)


@pytest.mark.parametrize("modulo", MODULOS)
def test_escribir_el_valor_calculado_deja_de_ser_una_cantidad_escrita(modulo, _of001) -> None:
    """3c-B4: AF-LLAVE vale 3; enviar «3» (o «3.000») no es escribir nada."""
    borrador = _of001[modulo]
    items = modulo.items_sin_escribir(borrador)
    for texto in ("3", "3.000"):
        assert (
            modulo.cantidades_desde_filas(_tabla(modulo, borrador, **{LLAVE: texto}), items) == {}
        )


@pytest.mark.parametrize("modulo", MODULOS)
def test_una_cantidad_negativa_dice_la_fila_y_la_partida(modulo, _of001) -> None:
    """3c-B5 / P16: el texto de H:861-863, con la posicion de la fila en la tabla completa."""
    borrador = _of001[modulo]
    items = modulo.items_sin_escribir(borrador)
    with pytest.raises(HojaInvalida) as error:
        modulo.cantidades_desde_filas(_tabla(modulo, borrador, **{LLAVE: "-1"}), items)
    assert str(error.value) == (
        "presupuesto, fila 3 (AF-LLAVE): la cantidad no puede ser negativa; "
        "escriba cero o una cantidad positiva"
    )


@pytest.mark.parametrize("modulo", MODULOS)
def test_cero_es_una_cantidad_valida(modulo, _of001) -> None:
    borrador = _of001[modulo]
    items = modulo.items_sin_escribir(borrador)
    assert modulo.cantidades_desde_filas(_tabla(modulo, borrador, **{LLAVE: "0"}), items) == {
        LLAVE: D(0)
    }


@pytest.mark.parametrize("modulo", MODULOS)
def test_la_coma_decimal_y_el_texto_no_numerico_son_errores_con_el_texto_de_la_clasica(
    modulo, _of001
) -> None:
    borrador = _of001[modulo]
    items = modulo.items_sin_escribir(borrador)
    casos = {
        "2,5": "presupuesto, fila 3 (AF-LLAVE): cantidad: '2,5' no es un numero decimal valido",
        "mucho": "presupuesto, fila 3 (AF-LLAVE): cantidad: 'mucho' no es un numero decimal valido",
        "": "presupuesto, fila 3 (AF-LLAVE): cantidad: '' no es un numero decimal valido",
        "Infinity": "presupuesto, fila 3 (AF-LLAVE): cantidad: 'Infinity' no es un monto finito",
    }
    for texto, mensaje in casos.items():
        with pytest.raises(HojaInvalida) as error:
            modulo.cantidades_desde_filas(_tabla(modulo, borrador, **{LLAVE: texto}), items)
        assert str(error.value) == mensaje, texto


@pytest.mark.parametrize("modulo", MODULOS)
def test_una_clave_que_no_es_de_ningun_renglon_se_ignora_en_la_funcion(modulo, _of001) -> None:
    borrador = _of001[modulo]
    items = modulo.items_sin_escribir(borrador)
    tabla = _tabla(modulo, borrador)
    tabla.append({"clave": "NO-EXISTE|x", "cantidad": "9"})
    assert modulo.cantidades_desde_filas(tabla, items) == {}


@pytest.mark.parametrize("modulo", MODULOS)
def test_ti001_la_primera_fila_negativa_nombra_su_partida(modulo, _ti001) -> None:
    borrador = _ti001[modulo]
    items = modulo.items_sin_escribir(borrador)
    clave = modulo.claves_de_items(items)[0]
    assert clave.startswith("TI-RACK|")  # el primer renglon de TI-001 es el rack
    with pytest.raises(HojaInvalida) as error:
        modulo.cantidades_desde_filas(_tabla(modulo, borrador, **{clave: "-2"}), items)
    assert str(error.value) == (
        "presupuesto, fila 1 (TI-RACK): la cantidad no puede ser negativa; "
        "escriba cero o una cantidad positiva"
    )
    assert len(items) == 27  # 27 renglones: la tabla completa fija la posicion de cada fila


@pytest.mark.parametrize("modulo", MODULOS)
def test_la_cantidad_de_llaves_en_5_suma_26_3975_al_total_de_la_memoria(modulo, _of001) -> None:
    """P15: Δtotal = 2 x CD x 1,15 x 1,10 con CD = 10,4338 (calculo a mano, ver el docstring)."""
    borrador = _of001[modulo]
    antes = modulo.elaborar_borrador(borrador)
    escritas = modulo.cantidades_desde_filas(
        _tabla(modulo, borrador, **{LLAVE: "5"}), modulo.items_sin_escribir(borrador)
    )
    editado = replace(borrador, cantidades=escritas)
    despues = modulo.elaborar_borrador(editado)
    assert abs(antes.elaboracion.presupuesto.total - D("2703.86")) <= D("0.01")
    delta = despues.elaboracion.presupuesto.total - antes.elaboracion.presupuesto.total
    assert abs(delta - D("26.39748")) <= D("0.001")
    cambios = modulo.cambios_entre(borrador, editado)
    assert [(c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("cantidad", LLAVE, "cantidad", "3", "5")
    ]
    estado = despues.estado_items[LLAVE]
    assert estado.severidad is not None and estado.severidad.name == "ADVERTENCIA"  # R8


# --- parametros_desde_texto -------------------------------------------------------------------

TEXTOS = {
    "fcas": "6.00",
    "bono_alimentacion": "5.8100",
    "administracion": "0.15",
    "utilidad": "0.10",
}


@pytest.mark.parametrize("modulo", MODULOS)
def test_los_cuatro_textos_de_of001_dan_sus_parametros(modulo, _of001) -> None:
    parametros = modulo.parametros_desde_texto(TEXTOS)
    assert (parametros.fcas, parametros.bono_alimentacion) == (D("6.00"), D("5.8100"))
    assert (parametros.administracion, parametros.utilidad) == (D("0.15"), D("0.10"))
    assert parametros == _of001[modulo].parametros  # y son los de la version abierta


@pytest.mark.parametrize("modulo", MODULOS)
def test_administracion_020_da_los_literales_de_p13(modulo, _of001) -> None:
    """Total 2 821,42; PE 1 763,39; 62,50 %; un solo cambio `administracion` 0.15 -> 0.20."""
    borrador = _of001[modulo]
    parametros = modulo.parametros_desde_texto({**TEXTOS, "administracion": "0.20"})
    editado = replace(borrador, parametros=parametros)
    resultado = modulo.elaborar_borrador(editado)
    assert abs(resultado.elaboracion.presupuesto.total - D("2821.42")) <= D("0.01")
    assert abs(resultado.equilibrio.punto - D("1763.39")) <= D("0.01")
    assert abs(resultado.equilibrio.porcentaje - D("62.50")) <= D("0.01")
    cambios = modulo.cambios_entre(borrador, editado)
    assert [(c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("parametro", "administracion", "valor", "0.15", "0.20")
    ]


@pytest.mark.parametrize("modulo", MODULOS)
def test_un_parametro_invalido_dice_el_campo_y_el_texto_de_la_clasica(modulo) -> None:
    casos = {
        ("utilidad", "mucho"): "parametros: utilidad: 'mucho' no es un numero decimal valido",
        ("fcas", "6,00"): "parametros: fcas: '6,00' no es un numero decimal valido",
        ("administracion", ""): "parametros: administracion: '' no es un numero decimal valido",
        ("bono_alimentacion", "Infinity"): (
            "parametros: bono_alimentacion: 'Infinity' no es un monto finito"
        ),
        ("fcas", "-1"): "parametros: fcas no puede ser negativo: -1",
    }
    for (campo, texto), mensaje in casos.items():
        with pytest.raises(HojaInvalida) as error:
            modulo.parametros_desde_texto({**TEXTOS, campo: texto})
        assert str(error.value) == mensaje, (campo, texto)


@pytest.mark.parametrize("modulo", MODULOS)
def test_un_campo_ausente_cuenta_como_vacio(modulo) -> None:
    sin_utilidad = {k: v for k, v in TEXTOS.items() if k != "utilidad"}
    with pytest.raises(HojaInvalida) as error:
        modulo.parametros_desde_texto(sin_utilidad)
    assert str(error.value) == "parametros: utilidad: '' no es un numero decimal valido"


# --- plan_desde_filas -------------------------------------------------------------------------


def _matriz(modulo, borrador, **cambios: dict[str, str]):
    """La matriz del plan como la siembra la clasica: etiquetas y una fila por partida."""
    resultado = modulo.elaborar_borrador(borrador)
    codigos = list(
        dict.fromkeys(p.item.codigo_partida for p in resultado.elaboracion.presupuesto.partidas)
    )
    etiquetas, filas = modulo.plan_como_filas(resultado.plan or (), codigos)
    for fila in filas:
        fila.update(cambios.get(fila["partida"], {}))
    return etiquetas, filas


@pytest.mark.parametrize("modulo", MODULOS)
def test_la_matriz_sin_tocar_reconstruye_el_plan_de_of001(modulo, _of001) -> None:
    borrador = _of001[modulo]
    etiquetas, filas = _matriz(modulo, borrador)
    plan = modulo.plan_desde_filas(filas, etiquetas)
    assert len(plan) == 30 and etiquetas[0] == "Dia 1" and etiquetas[-1] == "Dia 30"
    assert plan[2] == ("Dia 3", (("AF-LLAVE", D(1)),))
    assert plan == list(modulo.elaborar_borrador(borrador).plan)


@pytest.mark.parametrize("modulo", MODULOS)
def test_repartir_las_llaves_entre_el_dia_3_y_el_dia_30_conserva_el_total_y_mueve_la_mitad(
    modulo, _of001
) -> None:
    """P19/P20: AF-LLAVE 0,5 en «Dia 3» y 0,5 en «Dia 30»: la mitad de su total (39,5967 / 2 =
    19,798, a mano) cambia de periodo y la curva sigue cerrando en 2 703,86."""
    borrador = _of001[modulo]
    etiquetas, filas = _matriz(modulo, borrador, **{"AF-LLAVE": {"Dia 3": "0.5", "Dia 30": "0.5"}})
    plan = tuple(modulo.plan_desde_filas(filas, etiquetas))
    resultado = modulo.elaborar_borrador(replace(borrador, plan=plan))
    curva = resultado.elaboracion.presupuesto.curva
    por_dia = {p.periodo.split(" [")[0]: p for p in curva}  # «Dia 3 [AF-LLAVE]»: se corta el [..]
    base = {
        p.periodo.split(" [")[0]: p
        for p in modulo.elaborar_borrador(borrador).elaboracion.presupuesto.curva
    }
    assert abs(por_dia["Dia 30"].monto - base["Dia 30"].monto - D("19.798")) <= D("0.01")
    assert abs(por_dia["Dia 3"].monto - (base["Dia 3"].monto - D("19.798"))) <= D("0.01")
    assert abs(curva[-1].acumulado - D("2703.86")) <= D("0.01")


@pytest.mark.parametrize("modulo", MODULOS)
def test_un_plan_que_no_suma_1_dice_cuanto_suma(modulo, _of001) -> None:
    """3c-B12 / P19: el texto de H:1209-1212, con la suma como la teclea una persona."""
    etiquetas, filas = _matriz(modulo, _of001[modulo], **{"AF-LLAVE": {"Dia 3": "0.5"}})
    with pytest.raises(HojaInvalida) as error:
        modulo.plan_desde_filas(filas, etiquetas)
    assert str(error.value) == (
        "plan, partida AF-LLAVE: las fracciones suman 0.5 y deben sumar exactamente 1; "
        "repartala entre los periodos hasta completar 1"
    )


@pytest.mark.parametrize("modulo", MODULOS)
def test_una_fraccion_negativa_y_una_que_no_es_numero(modulo, _of001) -> None:
    borrador = _of001[modulo]
    etiquetas, filas = _matriz(modulo, borrador, **{"AF-LLAVE": {"Dia 3": "-1", "Dia 4": "2"}})
    with pytest.raises(HojaInvalida) as error:
        modulo.plan_desde_filas(filas, etiquetas)
    assert str(error.value) == "plan, partida AF-LLAVE: la fraccion de Dia 3 no puede ser negativa"
    etiquetas, filas = _matriz(modulo, borrador, **{"AF-LLAVE": {"Dia 3": "0,5"}})
    with pytest.raises(HojaInvalida) as error:
        modulo.plan_desde_filas(filas, etiquetas)
    assert str(error.value) == (
        "plan, partida AF-LLAVE: Dia 3: '0,5' no es un numero decimal valido"
    )


@pytest.mark.parametrize("modulo", MODULOS)
def test_una_celda_vacia_vale_cero(modulo, _of001) -> None:
    """«Dia 3» vacio y «Dia 4» en 1: la partida se ejecuta entera el Dia 4, sin error."""
    etiquetas, filas = _matriz(modulo, _of001[modulo], **{"AF-LLAVE": {"Dia 3": "", "Dia 4": "1"}})
    plan = dict(modulo.plan_desde_filas(filas, etiquetas))
    assert ("AF-LLAVE", D(1)) in plan["Dia 4"] and ("AF-LLAVE", D(1)) not in plan["Dia 3"]


@pytest.mark.parametrize("modulo", MODULOS)
def test_una_fila_sin_partida_se_ignora(modulo, _of001) -> None:
    etiquetas, filas = _matriz(modulo, _of001[modulo])
    con_vacia = [*filas, {"partida": "", "Dia 1": "7"}]
    assert modulo.plan_desde_filas(con_vacia, etiquetas) == modulo.plan_desde_filas(
        filas, etiquetas
    )


@pytest.mark.parametrize("modulo", MODULOS)
def test_ti001_su_plan_de_10_periodos_se_reconstruye_con_las_mismas_fracciones(
    modulo, _ti001
) -> None:
    borrador = _ti001[modulo]
    etiquetas, filas = _matriz(modulo, borrador)
    assert etiquetas == [f"Dia {n}" for n in range(1, 11)]
    plan = modulo.plan_desde_filas(filas, etiquetas)
    celdas = {(c, e): f for e, reparto in plan for c, f in reparto}
    assert celdas[("TI-EMT1", "Dia 1")] == D("0.45") and celdas[("TI-RACK", "Dia 1")] == D(1)
    assert celdas[("TI-SRV", "Dia 4")] == D("0.50") and celdas[("TI-CERT", "Dia 10")] == D("0.40")
    assert modulo.cambios_entre(borrador, replace(borrador, plan=tuple(plan))) == []


# --- con_plan_secuencial ----------------------------------------------------------------------


@pytest.mark.parametrize("modulo", MODULOS)
def test_el_plan_secuencial_es_una_partida_por_periodo_y_la_curva_cierra_en_el_total(
    modulo, _of001
) -> None:
    """P20 (`test_ui_hoja.py:267`): sin plan, `con_plan_secuencial` da 30 periodos al 100 %."""
    borrador = replace(_of001[modulo], plan=None)
    con_plan = modulo.con_plan_secuencial(borrador)
    assert len(con_plan.plan) == 30
    assert con_plan.plan[0] == ("Dia 1", (("AF-CODO-1/2", D(1)),))
    assert con_plan.plan[-1] == ("Dia 30", (("EL-TUB-EMT-3/4", D(1)),))
    resultado = modulo.elaborar_borrador(con_plan)
    assert abs(resultado.elaboracion.presupuesto.curva[-1].acumulado - D("2703.86")) <= D("0.01")
    assert resultado.elaboracion.presupuesto.curva[-1].periodo.split(" [")[0] == "Dia 30"
