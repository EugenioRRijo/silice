"""3b-B3C (T10, 3e-2): importar un plano con `aplicacion.hoja`.

Corre las funciones que usan las rutas P1 a P5 (`formato_de_plano`, `leer_plano`,
`alturas_pendientes`, `cargar_alturas_desde_texto`, `circuitos_supuestos`,
`declarar_circuitos_desde_texto`, `fusionar_plano`, `resumen_de_importacion`,
`resumen_de_la_fusion`, `filas_del_informe`) con el DXF de OF-001 y sus variantes, y fija lo que
producen y sus mensajes de error con igualdad exacta contra literales a mano
(`tests/fixtures/planos_de_la_hoja.py`, memoria de OF-001). Ya no compara contra `ui.hoja`
(retiro de Streamlit, F6). Un cambio legitimo del comportamiento exige cambiar esta prueba con el
aval de Eugenio.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.espacio.planos import EstadoImportacion
from aplicacion import hoja
from aplicacion.errores import HojaInvalida
from tests.fixtures import caso_ti001
from tests.fixtures.planos_de_la_hoja import (
    AMBIENTES_OF001,
    CIRCUITOS_OF001,
    CORRUPTO,
    DXF_OF001,
    FILAS_OF001,
    IMPORTADOS_OF001,
    altura_de_la_memoria,
    dxf_sin_unidad,
)


def _llamar(funcion: str, *args, **kwargs):
    """Lo que devuelve (o el texto con que falla) `funcion`: ("ok", valor) o ("error", texto)."""
    try:
        return ("ok", getattr(hoja, funcion)(*args, **kwargs))
    except HojaInvalida as error:
        return ("error", str(error))


@pytest.fixture(scope="module")
def importado():
    return hoja.leer_plano(DXF_OF001)


def test_leer_el_dxf_de_of001_da_las_filas_de_la_memoria(importado):
    tipo, resultado = _llamar("leer_plano", DXF_OF001)
    assert tipo == "ok" and resultado.estado is EstadoImportacion.IMPORTADA
    assert resultado.estado is EstadoImportacion.IMPORTADA
    assert {k: resultado.filas[k] for k in FILAS_OF001} == FILAS_OF001
    conteos = dict(_llamar("resumen_de_importacion", resultado)[1])
    assert (conteos["Importado"], conteos["No reconocido"], conteos["Pendiente"]) == (
        IMPORTADOS_OF001,
        0,
        len(AMBIENTES_OF001),
    )
    assert _llamar("filas_del_informe", resultado.informe)[0] == "ok"


@pytest.mark.parametrize("nombre", ["plano.exe", "plano", "plano.dxf.txt", "", "PLANO.DXF"])
def test_el_formato_por_la_extension_y_su_mensaje(nombre):
    tipo, valor = _llamar("formato_de_plano", nombre)
    if nombre == "PLANO.DXF":
        assert (tipo, valor) == ("ok", "dxf")
    else:
        assert (tipo, valor) == (
            "error",
            f"El archivo «{nombre}» no es un plano que se pueda importar. "
            "Suba un plano en formato DXF o IFC.",
        )


def test_un_archivo_corrupto_se_rechaza_y_no_se_fusiona(tmp_path):
    ruta = tmp_path / "corrupto.dxf"
    ruta.write_bytes(CORRUPTO)
    tipo, rechazado = _llamar("leer_plano", ruta)
    assert tipo == "ok" and rechazado.estado is EstadoImportacion.RECHAZADA
    assert rechazado.mensaje.startswith("corrupto.dxf: no se pudo leer como DXF (")
    blanco = hoja.Borrador(fecha=date(2026, 10, 20))
    assert _llamar("fusionar_plano", blanco, rechazado) == (
        "error",
        f"No se puede fusionar «corrupto.dxf»: {rechazado.mensaje}",
    )


def test_sin_unidad_se_detiene_y_con_metros_reanuda(tmp_path, importado):
    ruta = dxf_sin_unidad(tmp_path / "sin_unidad.dxf")
    tipo, detenido = _llamar("leer_plano", ruta)
    assert tipo == "ok" and detenido.estado is EstadoImportacion.DETENIDA and detenido.pide_unidad
    tipo, reanudado = _llamar("leer_plano", ruta, unidades="m")
    assert tipo == "ok" and reanudado.estado is EstadoImportacion.IMPORTADA
    assert reanudado.filas == importado.filas


def test_las_alturas_pendientes_y_su_carga_de_la_memoria(importado):
    tipo, pendientes = _llamar("alturas_pendientes", importado)
    assert sorted(i for i, _ in pendientes) == sorted(AMBIENTES_OF001)
    textos = {i: altura_de_la_memoria() for i, _ in pendientes}
    tipo, cargado = _llamar("cargar_alturas_desde_texto", importado, textos)
    assert tipo == "ok" and hoja.alturas_pendientes(cargado) == []
    assert {a.alto for a in cargado.ambientes} == {Decimal("2.500")}


@pytest.mark.parametrize("malo", ["250,5", "0", "abc", "-1", "NaN"])
def test_una_altura_invalida_da_el_texto_escrito_y_no_carga_ninguna(importado, malo):
    textos = {i: altura_de_la_memoria() for i in AMBIENTES_OF001}
    textos["ZB"] = malo
    assert _llamar("cargar_alturas_desde_texto", importado, textos) == (
        "error",
        f"Altura de «ZB»: «{malo}» no es una altura valida. "
        "Escriba un numero de metros mayor que 0 y hasta 250, por ejemplo 2,50.",
    )


def test_los_circuitos_supuestos_y_su_declaracion(importado):
    tipo, supuestos = _llamar("circuitos_supuestos", importado)
    assert [c.id for c in supuestos] == list(CIRCUITOS_OF001)
    valores = {c: ("1", "1", "1", "8") for c in CIRCUITOS_OF001}
    tipo, declarado = _llamar("declarar_circuitos_desde_texto", importado, valores)
    assert tipo == "ok" and hoja.circuitos_supuestos(declarado) == []
    assert {c.puntos_maximos for c in declarado.circuitos} == {8}


@pytest.mark.parametrize(
    ("valores", "esperado"),
    [
        (
            ("x", "1", "1", "6"),
            "Circuito «C2»: los conductores de fase debe ser un numero entero "
            "de 0 o mas (se escribio «x»).",
        ),
        (
            ("1", "-1", "1", "6"),
            "Circuito «C2»: los conductores de neutro debe ser un numero entero "
            "de 0 o mas (se escribio «-1»).",
        ),
        (
            ("1", "1", "1,5", "6"),
            "Circuito «C2»: los conductores de tierra debe ser un numero entero "
            "de 0 o mas (se escribio «1,5»).",
        ),
        (
            ("1", "1", "1", "0"),
            "Circuito «C2»: los puntos maximos debe ser un numero entero "
            "de 1 o mas (se escribio «0»).",
        ),
    ],
)
def test_un_circuito_invalido_da_el_texto_escrito(importado, valores, esperado):
    entrada = {"C1": ("1", "1", "1", "6"), "C2": valores}
    assert _llamar("declarar_circuitos_desde_texto", importado, entrada) == ("error", esperado)


def test_fusionar_da_el_espacio_de_la_memoria_y_el_resumen_cuenta_una_vez(importado):
    textos = {i: altura_de_la_memoria() for i in AMBIENTES_OF001}
    listo = hoja.declarar_circuitos_desde_texto(
        hoja.cargar_alturas_desde_texto(importado, textos),
        {c: ("1", "1", "1", "6") for c in CIRCUITOS_OF001},
    )
    blanco = hoja.Borrador(fecha=date(2026, 10, 20), parametros=caso_ti001.PARAMETROS)
    nuevo, informe = hoja.fusionar_plano(blanco, listo)
    espacio = nuevo.espacio
    # memoria of001.md §1: 6 ambientes (ids de AMBIENTES_OF001), 6 fuentes, 21 puntos, 2 circuitos
    assert {a.id for a in espacio.ambientes} == set(AMBIENTES_OF001)
    assert (len(espacio.ambientes), len(espacio.fuentes), len(espacio.puntos)) == (6, 6, 21)
    assert [c.id for c in espacio.circuitos] == list(CIRCUITOS_OF001)
    assert {a.alto for a in espacio.ambientes} == {Decimal("2.500")}
    resumen = hoja.resumen_de_la_fusion(listo, informe)
    # el resumen no duplica: 33 importados (no 68, 33 del plano + 35 de la fusion)
    assert dict(resumen.por_tipo)["Importado"] == IMPORTADOS_OF001
    por_tabla = dict(resumen.filas_por_tabla)
    assert (por_tabla["Ambientes"], por_tabla["Fuentes"], por_tabla["Puntos"]) == (6, 6, 21)
    assert _llamar("filas_del_informe", informe)[0] == "ok"


def test_subir_plano_rechaza_otra_extension_antes_de_escribir(tmp_path: Path):
    class Subida:
        name = "virus.exe"

        def getvalue(self) -> bytes:
            return b"MZ"

    carpeta = tmp_path / "subidas"
    carpeta.mkdir()
    with pytest.raises(HojaInvalida) as error:
        hoja.subir_plano(Subida(), carpeta)
    assert "«virus.exe» no es un plano" in str(error.value)
    assert list(carpeta.iterdir()) == []
