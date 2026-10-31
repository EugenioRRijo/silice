"""Respuestas de Eugenio al calculo y a la publicacion (plan vial, Tarea 4b: P14, P15, P16, P22).

Datos FICTICIOS: la planta de `tests/fixtures/costo_propio.py` (agregados `AGR-12` y `AGR-34`,
mezcla `MZ-1`) con meses de octubre a diciembre de 2026. Oraculos a mano, ninguno sacado del codigo
bajo prueba:

- P14, tasa del cierre: lista en USD vigente desde el 01/06 (tasa ese dia 50) y calculo en Bs de
  noviembre con la ultima tasa del mes a 200 (27/11). Costos en Bs: cantera 1.000 / 200 t = 5;
  planta 1.200 / 100 t = 12. `CA-30` a 600 USD/t son 600 x 200 = 120.000 Bs/t (no 30.000) y `GO` a
  0,5 USD/l son 100 Bs/l. Mezcla: 0,94 x 5 + 0,05 x 120.000 + 8 x 100 + 12 = 4,70 + 6.000 + 800 + 12
  = 6.816,70.
- P15, agregado no producido: octubre, 500 USD de cantera sobre 100 t de `AGR-12` = 5. En noviembre
  solo hay mezcla (100 t) y planta 1.200: 0,94 x 5 + 0,05 x 600 + 8 x 0,5 + 12 = 50,70.
- P16, arrastre: octubre, cantera 1.000 sin agregados (la mezcla de octubre es solo de comprados:
  0,99 x 600 + 8 x 0,5 + 120 / 10 = 594 + 4 + 12 = 610); noviembre, cantera 500 y 150 t de `AGR-12`:
  (1.000 + 500) / 150 = 10. Con un mes mas sin receptor: (1.000 + 500 + 300) / 100 = 18.
- Arrastre en otra moneda: 36.500 Bs de octubre con la tasa del cierre de octubre (36,50 del 30/10)
  son 1.000 USD; con la de noviembre (50) serian 730 y el agregado saldria a 8,20, no a 10.
- Ronda 2: la tasa del cierre es la ultima del mes aunque este a mas de 7 dias del ultimo dia (la
  del 03/11 o la del 02/10 sirven). Entre varios calculos anteriores, el del periodo mas reciente:
  octubre (5) aunque septiembre (7) se recalcule despues.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aplicacion.costo_propio import (
    VERSION_DE_LA_INSTANTANEA,
    CalculoGuardado,
    CalculoYaPublicado,
    FaltanTasas,
    calcular_periodo,
    calculo_guardado,
    publicacion_de,
    publicar_calculo,
)
from core import models
from core.catalog import Catalogo
from produccion.costo import ErrorDeCalculo
from produccion.costos import CostoDelPeriodo, registrar_costo
from produccion.modelo import Calculo
from produccion.receta import Componente
from tests.fixtures import costo_propio as cp

D = Decimal
OCT, NOV, DIC = "2026-10", "2026-11", "2026-12"
EMPRESA = ("Constructora Ejemplo, C.A.", "J-00000000-0")
CARPETA = "carpeta-ficticia.db"
SOLO_COMPRADO = (
    Componente("CA-30", D("0.99"), "t", "comprado"),
    Componente("GO", D("8"), "l", "comprado"),
)
NO_SE_PUBLICA = "Este cálculo no tiene costos por tonelada que publicar."


@pytest.fixture
def ins() -> Iterator[Session]:
    with cp.instalacion_en_memoria() as sesion:
        yield sesion


@pytest.fixture
def caso(tmp_path: Path) -> Iterator[Session]:
    with cp.carpeta_del_caso(tmp_path) as sesion:
        yield sesion


def _costo(ins, periodo: str, centro: str, monto: str, moneda: str, fecha: date) -> int:
    registro = CostoDelPeriodo(periodo, centro, "otro", D(monto), moneda, fecha, "factura ficticia")
    return registrar_costo(ins, registro, usuario="ana", ahora=cp.AHORA)


def _calcular(ins, caso, periodo: str, moneda: str = "USD") -> CalculoGuardado:
    return calcular_periodo(ins, caso, periodo, moneda, usuario="ana", ahora=cp.AHORA)


def _datos(calculo: CalculoGuardado) -> dict:
    return json.loads(calculo.instantanea)


def _calculos(ins) -> int:
    return ins.scalar(select(func.count()).select_from(Calculo)) or 0


def _listas(caso) -> int:
    return caso.scalar(select(func.count()).select_from(models.ListaPrecios)) or 0


def _publicar(ins, caso, calculo: CalculoGuardado) -> models.ListaPrecios:
    return publicar_calculo(
        caso,
        calculo,
        sesion_ins=ins,
        nombre_del_caso=CARPETA,
        base=Catalogo(caso).lista_vigente(date(2026, 11, 30)),
        empresa_nombre=EMPRESA[0],
        empresa_rif=EMPRESA[1],
        usuario="admin",
        ahora=cp.AHORA,
    )


# --- P14: la tasa del cierre del mes --------------------------------------------------------------


def test_lista_vieja_se_convierte_con_la_tasa_del_cierre(ins, caso) -> None:
    cp.planta(ins)
    _costo(ins, NOV, "cantera", "1000", "Bs", cp.dia(3))
    _costo(ins, NOV, "planta", "1200", "Bs", cp.dia(12))
    cp.lista(caso, "USD", date(2026, 6, 1), cp.LISTA_USD)
    cp.tasas(caso, {date(2026, 6, 1): "50", date(2026, 11, 27): "200"})
    calculo = _calcular(ins, caso, NOV, "Bs")
    assert calculo.por_tonelada == {"AGR-12": D("5"), "AGR-34": D("5"), "MZ-1": D("6816.70")}
    entradas = _datos(calculo)["entradas"]
    ca30 = entradas["precios_comprados"]["CA-30"]
    assert D(ca30["convertido"]) == D("120000")
    assert ca30["tasa"]["fecha"] == "2026-11-27"
    assert (entradas["tasa_del_cierre"]["valor"], entradas["tasa_del_cierre"]["fecha"]) == (
        "200",
        "2026-11-27",
    )


def test_la_instantanea_es_la_version_2_con_sus_cuatro_claves(ins, caso) -> None:
    """Todo en USD: no hizo falta convertir (`tasa_del_cierre` nula) y sin calculo de octubre nada
    viene del mes anterior; todo tuvo receptor, nada pasa al siguiente."""
    cp.noviembre_usd(ins, caso)
    datos = _datos(_calcular(ins, caso, NOV))
    assert VERSION_DE_LA_INSTANTANEA == 2 and datos["entradas"]["version"] == 2
    assert datos["entradas"]["tasa_del_cierre"] is None
    assert datos["entradas"]["de_otro_calculo"] == {}
    assert datos["entradas"]["viene_del_mes_anterior"] == {}
    assert datos["resultado"]["pasa_al_mes_siguiente"] == {}


def test_la_lista_sin_tasa_del_cierre_falla_y_la_nombra(ins, caso) -> None:
    cp.planta(ins)
    cp.costos_usd(ins)
    cp.lista(caso, "Bs", cp.dia(1), cp.LISTA_BS, nombre="Lista Bs ficticia")
    cp.tasas(caso, {date(2026, 10, 31): cp.TASA})  # la de octubre no sirve para noviembre
    with pytest.raises(FaltanTasas, match=r"«Lista Bs ficticia».*2026-11"):
        _calcular(ins, caso, NOV)
    assert _calculos(ins) == 0


def test_lo_comprado_con_una_tasa_lejos_del_cierre(ins, caso) -> None:
    """Ronda 2: la unica tasa de noviembre es la del 03/11 (200), 27 dias antes del cierre."""
    cp.planta(ins)
    _costo(ins, NOV, "cantera", "1000", "Bs", cp.dia(3))
    _costo(ins, NOV, "planta", "1200", "Bs", cp.dia(12))
    cp.lista(caso, "USD", date(2026, 6, 1), cp.LISTA_USD)
    cp.tasas(caso, {date(2026, 6, 1): "50", date(2026, 11, 3): "200"})
    calculo = _calcular(ins, caso, NOV, "Bs")
    assert calculo.por_tonelada["MZ-1"] == D("6816.70")
    assert _datos(calculo)["entradas"]["tasa_del_cierre"]["fecha"] == "2026-11-03"


def test_la_base_al_publicar_con_una_tasa_lejos_del_cierre(ins, caso) -> None:
    """Calculo en USD sobre una base en Bs; la unica tasa de noviembre es la del 03/11 (36,50):
    21.900 / 36,50 = 600."""
    cp.noviembre_usd(ins, caso)
    cp.tasas(caso, {cp.dia(3): cp.TASA})
    calculo = _calcular(ins, caso, NOV)
    otra = caso.get(models.ListaPrecios, cp.lista(caso, "Bs", cp.dia(5), cp.LISTA_BS, "Otra"))
    lista = publicar_calculo(
        caso,
        calculo,
        sesion_ins=ins,
        nombre_del_caso=CARPETA,
        base=otra,
        empresa_nombre=EMPRESA[0],
        empresa_rif=EMPRESA[1],
        usuario="admin",
        ahora=cp.AHORA,
    )
    precios = {p.insumo.codigo: p.precio for p in lista.precios}
    assert precios["CA-30"] == D("600") and precios["MZP-MZ-1"] == D("50.70")


# --- P15: agregado propio no producido en el mes --------------------------------------------------


def _mezcla_de_noviembre_sin_agregados(ins, caso) -> None:
    """`AGR-12` entra en octubre (100 t) y en noviembre solo se produce mezcla, con planta 1.200."""
    cp.materiales(ins)
    cp.receta(ins)
    cp.entrada(ins, "AGR-12", "100", date(2026, 10, 5))
    cp.producir(ins, "100", cp.dia(10))
    _costo(ins, NOV, "planta", "1200", "USD", cp.dia(12))
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)


def test_agregado_no_producido_toma_el_ultimo_calculo_anterior(ins, caso) -> None:
    _mezcla_de_noviembre_sin_agregados(ins, caso)
    _costo(ins, OCT, "cantera", "500", "USD", date(2026, 10, 3))
    octubre = _calcular(ins, caso, OCT)
    assert octubre.por_tonelada == {"AGR-12": D("5")}
    noviembre = _calcular(ins, caso, NOV)
    assert noviembre.por_tonelada == {"MZ-1": D("50.70")}
    assert _datos(noviembre)["entradas"]["de_otro_calculo"] == {
        "AGR-12": {"costo": "5", "calculo": octubre.id, "periodo": OCT}
    }


def test_de_varios_calculos_anteriores_toma_el_de_id_mayor(ins, caso) -> None:
    _mezcla_de_noviembre_sin_agregados(ins, caso)
    _costo(ins, OCT, "cantera", "500", "USD", date(2026, 10, 3))
    _calcular(ins, caso, OCT)
    _costo(ins, OCT, "cantera", "100", "USD", date(2026, 10, 20))
    segundo = _calcular(ins, caso, OCT)  # 600 / 100 = 6
    noviembre = _calcular(ins, caso, NOV)
    assert noviembre.por_tonelada == {"MZ-1": D("0.94") * 6 + D("46")}
    assert _datos(noviembre)["entradas"]["de_otro_calculo"]["AGR-12"]["calculo"] == segundo.id


def test_de_varios_meses_anteriores_toma_el_periodo_mas_reciente(ins, caso) -> None:
    """Decision del orquestador (fila 26): septiembre recalculado despues de octubre no gana."""
    _mezcla_de_noviembre_sin_agregados(ins, caso)
    cp.entrada(ins, "AGR-12", "100", date(2026, 9, 5))
    _costo(ins, OCT, "cantera", "500", "USD", date(2026, 10, 3))
    _costo(ins, "2026-09", "cantera", "700", "USD", date(2026, 9, 3))
    octubre = _calcular(ins, caso, OCT)
    septiembre = _calcular(ins, caso, "2026-09")
    assert septiembre.id > octubre.id and septiembre.por_tonelada == {"AGR-12": D("7")}
    noviembre = _calcular(ins, caso, NOV)
    assert noviembre.por_tonelada == {"MZ-1": D("50.70")}
    assert _datos(noviembre)["entradas"]["de_otro_calculo"]["AGR-12"]["calculo"] == octubre.id


def test_agregado_no_producido_de_otra_moneda_no_sirve(ins, caso) -> None:
    _mezcla_de_noviembre_sin_agregados(ins, caso)
    _costo(ins, OCT, "cantera", "18250", "Bs", date(2026, 10, 3))
    assert _calcular(ins, caso, OCT, "Bs").por_tonelada == {"AGR-12": D("182.5")}
    with pytest.raises(ErrorDeCalculo) as error:
        _calcular(ins, caso, NOV)
    assert str(error.value) == (
        "La mezcla MZ-1 usa AGR-12, que no se produjo en 2026-11 ni tiene un costo calculado "
        "antes en USD."
    )
    assert _calculos(ins) == 1


def test_agregado_no_producido_nunca_de_un_mes_posterior(ins, caso) -> None:
    """Recalcular noviembre despues de diciembre no usa diciembre, ni aunque su id sea mayor."""
    _mezcla_de_noviembre_sin_agregados(ins, caso)
    cp.entrada(ins, "AGR-12", "100", date(2026, 12, 5))
    _costo(ins, DIC, "cantera", "900", "USD", date(2026, 12, 3))
    assert _calcular(ins, caso, DIC).por_tonelada == {"AGR-12": D("9")}
    with pytest.raises(ErrorDeCalculo, match="AGR-12, que no se produjo en 2026-11"):
        _calcular(ins, caso, NOV)
    _costo(ins, OCT, "cantera", "500", "USD", date(2026, 10, 3))
    octubre = _calcular(ins, caso, OCT)
    _calcular(ins, caso, DIC)  # otro de diciembre, con id mayor que el de octubre
    noviembre = _calcular(ins, caso, NOV)
    assert noviembre.por_tonelada == {"MZ-1": D("50.70")}
    assert _datos(noviembre)["entradas"]["de_otro_calculo"]["AGR-12"] == {
        "costo": "5",
        "calculo": octubre.id,
        "periodo": OCT,
    }


# --- P16: lo que no tiene quien lo reciba pasa al mes siguiente -----------------------------------


def _octubre_con_cantera_sin_agregados(ins, caso) -> tuple[int, CalculoGuardado]:
    cp.materiales(ins)
    cp.receta(ins, SOLO_COMPRADO)
    cp.producir(ins, "10", date(2026, 10, 10))
    cantera = _costo(ins, OCT, "cantera", "1000", "USD", date(2026, 10, 5))
    _costo(ins, OCT, "planta", "120", "USD", date(2026, 10, 12))
    cp.lista(caso, "USD", date(2026, 10, 1), cp.LISTA_USD)
    return cantera, _calcular(ins, caso, OCT)


def test_cantera_sin_agregados_pasa_al_mes_siguiente(ins, caso) -> None:
    c1, octubre = _octubre_con_cantera_sin_agregados(ins, caso)
    assert octubre.por_tonelada == {"MZ-1": D("610")}
    assert _datos(octubre)["resultado"]["pasa_al_mes_siguiente"] == {
        "cantera": {"total": "1000", "costos": [c1]}
    }
    cp.entrada(ins, "AGR-12", "150", cp.dia(5))
    _costo(ins, NOV, "cantera", "500", "USD", cp.dia(3))
    noviembre = _calcular(ins, caso, NOV)
    assert noviembre.por_tonelada == {"AGR-12": D("10")}
    datos = _datos(noviembre)
    assert datos["entradas"]["viene_del_mes_anterior"] == {
        "cantera": {
            "total": "1000",
            "calculo": octubre.id,
            "periodo": OCT,
            "costos": [c1],
            "tasa": None,
        }
    }
    assert datos["resultado"]["pasa_al_mes_siguiente"] == {}
    assert D(datos["resultado"]["total_cantera"]) == D("1500")


def test_planta_sin_mezcla_pasa_al_mes_siguiente(ins, caso) -> None:
    cp.materiales(ins)
    cp.entrada(ins, "AGR-12", "200", cp.dia(5))
    _costo(ins, NOV, "cantera", "1000", "USD", cp.dia(3))
    planta = _costo(ins, NOV, "planta", "1200", "USD", cp.dia(12))
    calculo = _calcular(ins, caso, NOV)
    assert calculo.por_tonelada == {"AGR-12": D("5")}
    assert _datos(calculo)["resultado"]["pasa_al_mes_siguiente"] == {
        "planta": {"total": "1200", "costos": [planta]}
    }


def test_lo_que_vuelve_a_quedar_sin_receptor_pasa_sumado(ins, caso) -> None:
    cp.materiales(ins)
    c1 = _costo(ins, OCT, "cantera", "1000", "USD", date(2026, 10, 5))
    c2 = _costo(ins, NOV, "cantera", "500", "USD", cp.dia(3))
    _calcular(ins, caso, OCT)
    noviembre = _calcular(ins, caso, NOV)
    assert noviembre.por_tonelada == {}
    assert _datos(noviembre)["resultado"]["pasa_al_mes_siguiente"] == {
        "cantera": {"total": "1500", "costos": [c1, c2]}
    }
    cp.entrada(ins, "AGR-12", "100", date(2026, 12, 5))
    _costo(ins, DIC, "cantera", "300", "USD", date(2026, 12, 3))
    diciembre = _calcular(ins, caso, DIC)
    assert diciembre.por_tonelada == {"AGR-12": D("18")}
    viene = _datos(diciembre)["entradas"]["viene_del_mes_anterior"]["cantera"]
    assert (viene["total"], viene["calculo"], viene["periodo"], viene["costos"]) == (
        "1500",
        noviembre.id,
        NOV,
        [c1, c2],
    )


def test_lo_que_viene_del_mes_anterior_basta_aunque_el_mes_no_tenga_costos(ins, caso) -> None:
    """Decision del orquestador (n.º 24 de la bitacora): lo que pasa cuenta como costo del mes."""
    cp.materiales(ins)
    _costo(ins, OCT, "cantera", "1000", "USD", date(2026, 10, 5))
    _calcular(ins, caso, OCT)
    cp.entrada(ins, "AGR-12", "100", cp.dia(5))
    assert _calcular(ins, caso, NOV).por_tonelada == {"AGR-12": D("10")}


def test_mes_sin_produccion_se_calcula_y_todo_pasa(ins, caso) -> None:
    cp.materiales(ins)
    a = _costo(ins, NOV, "cantera", "600", "USD", cp.dia(3))
    b = _costo(ins, NOV, "cantera", "400", "USD", cp.dia(4))
    c = _costo(ins, NOV, "planta", "1200", "USD", cp.dia(12))
    calculo = _calcular(ins, caso, NOV)
    assert calculo.por_tonelada == {}
    assert _datos(calculo)["resultado"]["pasa_al_mes_siguiente"] == {
        "cantera": {"total": "1000", "costos": [a, b]},
        "planta": {"total": "1200", "costos": [c]},
    }
    assert _calculos(ins) == 1


def test_ese_calculo_no_se_publica(ins, caso) -> None:
    cp.materiales(ins)
    _costo(ins, NOV, "cantera", "1000", "USD", cp.dia(3))
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
    calculo = _calcular(ins, caso, NOV)
    antes = _listas(caso)
    with pytest.raises(ErrorDeCalculo) as error:
        _publicar(ins, caso, calculo)
    assert str(error.value) == NO_SE_PUBLICA
    assert _listas(caso) == antes and publicacion_de(ins, calculo.id) is None
    assert not caso.new and not ins.new


def test_arrastre_en_otra_moneda_se_convierte_con_el_cierre_del_mes_de_origen(ins, caso) -> None:
    cp.materiales(ins)
    c1 = _costo(ins, OCT, "cantera", "36500", "Bs", date(2026, 10, 5))
    octubre = _calcular(ins, caso, OCT, "Bs")
    cp.tasas(caso, {date(2026, 10, 5): "10", date(2026, 10, 30): cp.TASA, date(2026, 11, 3): "50"})
    cp.entrada(ins, "AGR-12", "150", cp.dia(5))
    _costo(ins, NOV, "cantera", "500", "USD", cp.dia(3))
    noviembre = _calcular(ins, caso, NOV)
    assert noviembre.por_tonelada == {"AGR-12": D("10")}
    viene = _datos(noviembre)["entradas"]["viene_del_mes_anterior"]["cantera"]
    assert D(viene["total"]) == D("1000")
    assert (viene["calculo"], viene["periodo"], viene["costos"]) == (octubre.id, OCT, [c1])
    assert (viene["tasa"]["valor"], viene["tasa"]["fecha"]) == ("36.50", "2026-10-30")


def test_arrastre_con_una_tasa_lejos_del_cierre_de_origen(ins, caso) -> None:
    """Ronda 2: la unica tasa de octubre es la del 02/10 (36,50), 29 dias antes del 31/10."""
    cp.materiales(ins)
    _costo(ins, OCT, "cantera", "36500", "Bs", date(2026, 10, 5))
    _calcular(ins, caso, OCT, "Bs")
    cp.tasas(caso, {date(2026, 10, 2): cp.TASA, date(2026, 11, 3): "50"})
    cp.entrada(ins, "AGR-12", "150", cp.dia(5))
    _costo(ins, NOV, "cantera", "500", "USD", cp.dia(3))
    noviembre = _calcular(ins, caso, NOV)
    assert noviembre.por_tonelada == {"AGR-12": D("10")}
    viene = _datos(noviembre)["entradas"]["viene_del_mes_anterior"]["cantera"]
    assert viene["tasa"]["fecha"] == "2026-10-02"


def test_arrastre_en_otra_moneda_sin_tasa_del_cierre_de_origen_falla(ins, caso) -> None:
    cp.materiales(ins)
    _costo(ins, OCT, "cantera", "36500", "Bs", date(2026, 10, 5))
    _calcular(ins, caso, OCT, "Bs")
    cp.tasas(caso, {date(2026, 11, 3): "50"})
    cp.entrada(ins, "AGR-12", "150", cp.dia(5))
    _costo(ins, NOV, "cantera", "500", "USD", cp.dia(3))
    with pytest.raises(FaltanTasas, match="2026-10"):
        _calcular(ins, caso, NOV)
    assert _calculos(ins) == 1


def test_un_calculo_del_mes_anterior_hecho_despues_no_cambia_el_del_mes(ins, caso) -> None:
    cp.materiales(ins)
    _costo(ins, OCT, "cantera", "1000", "USD", date(2026, 10, 5))
    primero_oct = _calcular(ins, caso, OCT)
    cp.entrada(ins, "AGR-12", "150", cp.dia(5))
    _costo(ins, NOV, "cantera", "500", "USD", cp.dia(3))
    noviembre = _calcular(ins, caso, NOV)
    _costo(ins, OCT, "cantera", "200", "USD", date(2026, 10, 6))
    segundo_oct = _calcular(ins, caso, OCT)
    guardado = calculo_guardado(ins, noviembre.id)
    assert guardado.por_tonelada == {"AGR-12": D("10")}
    assert guardado.huella == noviembre.huella
    viene = _datos(guardado)["entradas"]["viene_del_mes_anterior"]["cantera"]
    assert viene["calculo"] == primero_oct.id
    otra_vez = _calcular(ins, caso, NOV)  # recalcular si toma el ultimo de octubre
    assert otra_vez.por_tonelada == {"AGR-12": D("1700") / D("150")}
    viene = _datos(otra_vez)["entradas"]["viene_del_mes_anterior"]["cantera"]
    assert viene["calculo"] == segundo_oct.id


# --- P22: una sola publicacion por calculo --------------------------------------------------------


def test_publicar_registra_la_publicacion(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    calculo = _calcular(ins, caso, NOV)
    assert publicacion_de(ins, calculo.id) is None
    lista = _publicar(ins, caso, calculo)
    publicacion = publicacion_de(ins, calculo.id)
    assert publicacion is not None
    assert (publicacion.calculo_id, publicacion.lista_id, publicacion.caso) == (
        calculo.id,
        lista.id,
        CARPETA,
    )
    assert (publicacion.usuario, publicacion.registrado) == ("admin", cp.AHORA)


def test_publicar_dos_veces_se_niega_sin_escribir_nada(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    calculo = _calcular(ins, caso, NOV)
    lista = _publicar(ins, caso, calculo)
    antes = _listas(caso), caso.scalar(select(func.count()).select_from(models.Insumo))
    with pytest.raises(CalculoYaPublicado) as error:
        _publicar(ins, caso, calculo)
    esperado = f"El cálculo n.º {calculo.id} ya se publicó en la lista n.º {lista.id}."
    assert str(error.value) == esperado
    despues = _listas(caso), caso.scalar(select(func.count()).select_from(models.Insumo))
    assert despues == antes
    assert not caso.new and not ins.new


def test_un_choque_al_registrar_la_publicacion_es_ya_publicado(ins, caso, monkeypatch) -> None:
    """Menor (a) de la ronda 2: si dos publicaciones del mismo calculo pasan la comprobacion a la
    vez, el `unique` de `prod_publicacion` frena la segunda al escribir; se simula saltando la
    comprobacion previa. Sale `CalculoYaPublicado` con la lista de la primera."""
    cp.noviembre_usd(ins, caso)
    calculo = _calcular(ins, caso, NOV)
    lista = _publicar(ins, caso, calculo)
    monkeypatch.setattr("aplicacion.costo_propio.exigir_publicable", lambda *a, **k: None)
    with pytest.raises(CalculoYaPublicado) as error:
        _publicar(ins, caso, calculo)
    esperado = f"El cálculo n.º {calculo.id} ya se publicó en la lista n.º {lista.id}."
    assert str(error.value) == esperado
    assert publicacion_de(ins, calculo.id).lista_id == lista.id


# --- La version 1 de la instantanea se sigue leyendo ----------------------------------------------


def _calculo_v1(ins) -> int:
    """Un calculo de octubre guardado como lo guardaba la Tarea 4 (version 1): `AGR-12` a 5."""
    datos = {
        "entradas": {
            "version": 1,
            "periodo": OCT,
            "moneda": "USD",
            "reparto_cantera": "por tonelada",
            "pesos": None,
            "fecha_de_la_lista": "2026-10-31",
            "costos": [],
            "producido": {"AGR-12": "100"},
            "agregados": ["AGR-12"],
            "recetas": [],
            "precios_comprados": {},
        },
        "resultado": {
            "total_cantera": "500",
            "total_planta": "0",
            "planta_por_t": None,
            "por_tonelada": {"AGR-12": "5"},
        },
    }
    texto = json.dumps(datos, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    fila = Calculo(
        periodo=OCT,
        moneda="USD",
        huella=hashlib.sha256(texto.encode("utf-8")).hexdigest(),
        instantanea=texto,
        usuario="ana",
        registrado=datetime(2026, 10, 31, 18, 0),
    )
    ins.add(fila)
    ins.flush()
    return fila.id


def test_instantanea_v1_se_sigue_leyendo(ins, caso) -> None:
    v1 = _calculo_v1(ins)
    guardado = calculo_guardado(ins, v1)
    assert guardado.por_tonelada == {"AGR-12": D("5")}
    assert guardado.huella == hashlib.sha256(guardado.instantanea.encode("utf-8")).hexdigest()
    # y sirve de mes anterior (no trae nada que pase) y de costo de otro calculo
    cp.materiales(ins)
    cp.receta(ins)
    cp.producir(ins, "100", cp.dia(10))
    _costo(ins, NOV, "planta", "1200", "USD", cp.dia(12))
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
    noviembre = _calcular(ins, caso, NOV)
    assert noviembre.por_tonelada == {"MZ-1": D("50.70")}
    entradas = _datos(noviembre)["entradas"]
    assert entradas["viene_del_mes_anterior"] == {}
    assert entradas["de_otro_calculo"]["AGR-12"]["calculo"] == v1


# --- Tarea 16b, fila 27: sin el calculo de M, lo que dejo M-1 no se pierde ------------------------
#
# Oraculos a mano: octubre deja 1.000 USD de cantera sin agregados (la mezcla es solo de comprados);
# noviembre no tiene calculo. Calcular diciembre se niega pidiendo noviembre y no escribe nada. Si
# octubre no dejo nada (sus 1.000 los recibieron 100 t de AGR-12), diciembre se calcula sin
# noviembre: 300 / 100 t = 3. Con un hueco de dos meses (diciembre deja, enero y febrero sin
# calculo), marzo pide enero, el primero que falta, aunque el ano cambie.

FALTA_NOVIEMBRE = "Calcule primero 2026-11: el cálculo de 2026-10 dejó costos que pasan a ese mes."


def test_sin_calculo_de_m_lo_que_dejo_m_menos_1_niega_m_mas_1(ins, caso) -> None:
    _octubre_con_cantera_sin_agregados(ins, caso)
    cp.entrada(ins, "AGR-12", "100", date(2026, 12, 5))
    _costo(ins, DIC, "cantera", "300", "USD", date(2026, 12, 3))
    with pytest.raises(ErrorDeCalculo) as error:
        _calcular(ins, caso, DIC)
    assert str(error.value) == FALTA_NOVIEMBRE
    assert _calculos(ins) == 1


def test_si_m_menos_1_no_dejo_nada_el_hueco_no_importa(ins, caso) -> None:
    cp.materiales(ins)
    cp.entrada(ins, "AGR-12", "100", date(2026, 10, 5))
    _costo(ins, OCT, "cantera", "1000", "USD", date(2026, 10, 3))
    assert _datos(_calcular(ins, caso, OCT))["resultado"]["pasa_al_mes_siguiente"] == {}
    cp.entrada(ins, "AGR-12", "100", date(2026, 12, 5))
    _costo(ins, DIC, "cantera", "300", "USD", date(2026, 12, 3))
    assert _calcular(ins, caso, DIC).por_tonelada == {"AGR-12": D("3")}


def test_con_un_hueco_mas_largo_pide_el_primer_mes_que_falta(ins, caso) -> None:
    cp.materiales(ins)
    _costo(ins, DIC, "cantera", "1000", "USD", date(2026, 12, 3))
    _calcular(ins, caso, DIC)
    cp.entrada(ins, "AGR-12", "100", date(2027, 3, 5))
    _costo(ins, "2027-03", "cantera", "300", "USD", date(2027, 3, 3))
    with pytest.raises(ErrorDeCalculo) as error:
        _calcular(ins, caso, "2027-03")
    assert str(error.value) == (
        "Calcule primero 2027-01: el cálculo de 2026-12 dejó costos que pasan a ese mes."
    )
    assert _calculos(ins) == 1
