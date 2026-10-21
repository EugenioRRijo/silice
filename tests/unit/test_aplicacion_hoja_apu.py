"""3b-B3C (T10, 3c-3): `composicion_con_cantidades` y `cambiar_insumo` (con `insumos_candidatos`)
contra `ui.hoja` VIVO.

`aplicacion/hoja.py` es una copia de `ui/hoja.py` (Plan C: la clasica esta en el congelado del
experimento y no se toca). Esta prueba (que SI puede importar `ui`) corre en las dos las funciones
que validan las rutas E6 y E7 y compara lo que producen (el APU resultante y los textos de error,
igualdad exacta de cadena), con OF-001 y TI-001, y fija los valores contra literales a mano.

Oraculos a mano (ninguno sale de la copia). AF-LLAVE de OF-001 (memoria `of001.md` y
`tests/fixtures/caso_of001.py`: llave 4 907,50 Bs, herramientas 9 060,00 Bs, plomero 1 385,63 Bs,
ayudante 1 128,42 Bs, bono 3 679,85 Bs, todo a 633,3644 Bs/USD y 4 decimales; FCAS 6,00;
administracion 0,15; utilidad 0,10; rendimiento 20):

* llave 7,7483 · herramientas 14,3046 · plomero 2,1877 · ayudante 1,7816 · bono 5,8100
* CD = 7,7483 + 14,3046 / 20 + ((2,1877 + 1,7816) x 7,00 + 5,81 x 2) / 20 = **10,433785**
* PU = CD x 1,15 x 1,10 = **13,198738025** (y el delta de pasar de 3 a 5 unidades: 2 x PU =
  26,39747605, el 26,39748 de P15)
* llave x 2: CD = 10,433785 + 7,7483 = 18,182085, PU = 23,000337525
* rendimiento 10: CD = 7,7483 + 14,3046 / 10 + (27,7851 + 11,62) / 10 = 13,11927, PU = 16,59587655
* el pegamento (21 895,00 Bs = 34,5694) en lugar de la llave: CD = 10,433785 - 7,7483 + 34,5694 =
  37,254885 (PU 47,1274295250); el tecnico de redes (10,0000) en lugar del plomero: CD = 10,433785 +
  (10 - 2,1877) x 7 / 20 = 13,168090 (PU 16,657633850)

Si la copia y la clasica divergen, la unica que se corrige es la copia: `ui/hoja.py` esta
congelado. Un cambio legitimo del comportamiento exige cambiar esta prueba con el aval de Eugenio.
"""

from __future__ import annotations

import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion import hoja as copia
from aplicacion.errores import HojaInvalida
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.costing.motor import calcular_apu
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
FACTOR = D("1.15") * D("1.10")  # administracion y utilidad en cascada
TOLERANCIA = D("0.0000001")


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> tuple[Path, Path]:
    carpeta = tmp_path_factory.mktemp("paridad_apu")
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
    destino = tmp_path_factory.mktemp("of001_apu")
    return {m: _abrir(_plantillas[0], destino, m, NOMBRE_OF001, "001") for m in (clasica, copia)}


@pytest.fixture(scope="module")
def _ti001(_plantillas, tmp_path_factory) -> dict:
    destino = tmp_path_factory.mktemp("ti001_apu")
    return {
        m: _abrir(_plantillas[1], destino, m, NOMBRE_TI001, caso_ti001.CODIGO)
        for m in (clasica, copia)
    }


def _tablas(*cantidades: tuple[str, ...]) -> tuple[list[dict[str, str]], ...]:
    return tuple([{"cantidad": c} for c in rubro] for rubro in cantidades)


def _cd(composicion) -> Decimal:
    return calcular_apu(composicion, caso_ti001.PARAMETROS).costo_directo


def _pu(composicion) -> Decimal:
    return calcular_apu(composicion, caso_ti001.PARAMETROS).precio_unitario


# --- composicion_con_cantidades ---------------------------------------------------------------


@pytest.mark.parametrize("modulo", MODULOS)
def test_la_llave_de_oficina_cuesta_10_433785_y_su_precio_unitario_13_198738025(
    modulo, _of001
) -> None:
    base = _of001[modulo].composiciones["AF-LLAVE"]
    assert abs(_cd(base) - D("10.433785")) <= TOLERANCIA
    assert abs(_pu(base) - D("13.198738025")) <= TOLERANCIA
    assert abs(2 * _pu(base) - D("26.39747605")) <= TOLERANCIA  # el delta de 3 a 5 unidades


@pytest.mark.parametrize("modulo", MODULOS)
def test_las_tablas_sin_tocar_devuelven_el_mismo_apu(modulo, _of001) -> None:
    base = _of001[modulo].composiciones["AF-LLAVE"]
    materiales, equipos, mano = _tablas(("1",), ("1",), ("1", "1"))
    assert modulo.composicion_con_cantidades(base, materiales, equipos, mano, "20") == base


@pytest.mark.parametrize("modulo", MODULOS)
def test_dos_llaves_por_unidad_dan_cd_18_182085(modulo, _of001) -> None:
    base = _of001[modulo].composiciones["AF-LLAVE"]
    materiales, equipos, mano = _tablas(("2",), ("1",), ("1", "1"))
    nueva = modulo.composicion_con_cantidades(base, materiales, equipos, mano, "20")
    assert nueva.materiales[0].cantidad == D(2) and nueva.rendimiento == D(20)
    assert nueva.materiales[0].precio == base.materiales[0].precio  # solo cambia la cantidad
    assert nueva.materiales[0].descripcion == base.materiales[0].descripcion
    assert abs(_cd(nueva) - D("18.182085")) <= TOLERANCIA
    assert abs(_pu(nueva) - D("23.000337525")) <= TOLERANCIA


@pytest.mark.parametrize("modulo", MODULOS)
def test_rendimiento_10_da_cd_13_11927(modulo, _of001) -> None:
    base = _of001[modulo].composiciones["AF-LLAVE"]
    materiales, equipos, mano = _tablas(("1",), ("1",), ("1", "1"))
    nueva = modulo.composicion_con_cantidades(base, materiales, equipos, mano, "10")
    assert nueva.rendimiento == D(10)
    assert abs(_cd(nueva) - D("13.11927")) <= TOLERANCIA
    assert abs(_pu(nueva) - D("16.59587655")) <= TOLERANCIA


@pytest.mark.parametrize(
    ("tablas", "rendimiento", "mensaje"),
    [
        (
            (("-1",), ("1",), ("1", "1")),
            "20",
            "materiales, fila 1: la cantidad no puede ser negativa",
        ),
        (
            (("1",), ("1",), ("1", "-0.5")),
            "20",
            "mano de obra, fila 2: la cantidad no puede ser negativa",
        ),
        (
            (("2,5",), ("1",), ("1", "1")),
            "20",
            "materiales, fila 1: cantidad: '2,5' no es un numero decimal valido",
        ),
        (
            (("1",), ("x",), ("1", "1")),
            "20",
            "equipos, fila 1: cantidad: 'x' no es un numero decimal valido",
        ),
        (
            (("1",), ("1",), ("1", "1")),
            "0,5",
            "rendimiento: '0,5' no es un numero decimal valido",
        ),
        (
            (("1", "1"), ("1",), ("1", "1")),
            "20",
            "materiales: la tabla tiene 2 lineas y el APU 1; en la hoja solo se edita la cantidad "
            "de cada linea (para agregar o quitar una, use Componer)",
        ),
        (
            (("1",), ("1",), ("1",)),
            "20",
            "mano de obra: la tabla tiene 1 lineas y el APU 2; en la hoja solo se edita la "
            "cantidad de cada linea (para agregar o quitar una, use Componer)",
        ),
    ],
)
@pytest.mark.parametrize("modulo", MODULOS)
def test_los_errores_dicen_la_tabla_la_fila_y_el_campo_con_el_texto_de_la_clasica(
    modulo, _of001, tablas, rendimiento, mensaje
) -> None:
    base = _of001[modulo].composiciones["AF-LLAVE"]
    with pytest.raises(HojaInvalida) as error:
        modulo.composicion_con_cantidades(base, *_tablas(*tablas), rendimiento)
    assert str(error.value) == mensaje


@pytest.mark.parametrize("rendimiento", ["0", "-5"])
def test_un_rendimiento_que_el_modelo_rechaza_da_el_mismo_texto_en_las_dos(
    rendimiento, _of001
) -> None:
    mensajes = []
    for modulo in (clasica, copia):
        base = _of001[modulo].composiciones["AF-LLAVE"]
        with pytest.raises(HojaInvalida) as error:
            modulo.composicion_con_cantidades(
                base, *_tablas(("1",), ("1",), ("1", "1")), rendimiento
            )
        mensajes.append(str(error.value))
    assert mensajes[0] == mensajes[1] and mensajes[0]


@pytest.mark.parametrize("modulo", MODULOS)
def test_en_ti001_cada_partida_acepta_sus_propias_lineas(modulo, _ti001) -> None:
    """TI-001: reenviar las cantidades de cada APU tal cual no lo cambia."""
    for codigo, base in _ti001[modulo].composiciones.items():
        materiales = [{"cantidad": str(linea.cantidad)} for linea in base.materiales]
        equipos = [{"cantidad": str(linea.cantidad)} for linea in base.equipos]
        mano = [{"cantidad": str(linea.cantidad)} for linea in base.mano_obra]
        assert (
            modulo.composicion_con_cantidades(
                base, materiales, equipos, mano, str(base.rendimiento)
            )
            == base
        ), codigo


def test_las_dos_dan_el_mismo_apu_en_todas_las_partidas_de_ti001_y_de_oficina(
    _of001, _ti001
) -> None:
    for casos in (_of001, _ti001):
        for codigo in casos[clasica].composiciones:
            resultados = []
            for modulo in (clasica, copia):
                base = casos[modulo].composiciones[codigo]
                materiales = [{"cantidad": "3"} for _ in base.materiales]
                equipos = [{"cantidad": "2"} for _ in base.equipos]
                mano = [{"cantidad": "1.5"} for _ in base.mano_obra]
                resultados.append(
                    modulo.composicion_con_cantidades(base, materiales, equipos, mano, "7")
                )
            assert resultados[0] == resultados[1], codigo


# --- insumos_candidatos y cambiar_insumo ------------------------------------------------------


def _candidatos(plantilla: Path, modulo, tipo: str, texto: str = "", limite: int = 20):
    motor = crear_motor(f"sqlite:///{plantilla.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return modulo.insumos_candidatos(
                sesion, NOMBRE_OF001, "001", tipo, texto, limite=limite
            )
    finally:
        motor.dispose()


@pytest.mark.parametrize(("tipo", "total"), [("material", 38), ("equipo", 6), ("mano_obra", 5)])
def test_los_candidatos_son_los_mismos_y_el_ultimo_tipo_trae_los_conteos_de_la_lista(
    tipo, total, _plantillas
) -> None:
    de_clasica = _candidatos(_plantillas[0], clasica, tipo, limite=400)
    de_copia = _candidatos(_plantillas[0], copia, tipo, limite=400)
    assert [(f.codigo, f.descripcion, f.unidad, f.precio) for f in de_clasica] == [
        (f.codigo, f.descripcion, f.unidad, f.precio) for f in de_copia
    ]
    assert len(de_copia) == total  # la lista de OF-001 trae 38 materiales, 6 equipos y 5 oficios


def test_el_buscador_acota_por_descripcion_y_el_limite_corta(_plantillas) -> None:
    for modulo in (clasica, copia):
        pegamento = _candidatos(_plantillas[0], modulo, "material", "pegamento")
        assert [(f.codigo, f.unidad, f.precio) for f in pegamento] == [
            ("MAT-002", "env", D("34.5694"))
        ]
        assert len(_candidatos(_plantillas[0], modulo, "material", "", limite=10)) == 10
        assert _candidatos(_plantillas[0], modulo, "material", "no existe jamas") == []


def _fila(modulo, plantilla: Path, tipo: str, texto: str):
    (fila,) = _candidatos(plantilla, modulo, tipo, texto)
    return fila


@pytest.mark.parametrize("modulo", MODULOS)
def test_cambiar_el_material_por_el_pegamento_da_cd_37_254885_y_conserva_la_cantidad(
    modulo, _of001, _plantillas
) -> None:
    base = _of001[modulo].composiciones["AF-LLAVE"]
    pegamento = _fila(modulo, _plantillas[0], "material", "pegamento")
    nueva = modulo.cambiar_insumo(base, "material", 0, pegamento)
    linea = nueva.materiales[0]
    assert (linea.descripcion, linea.unidad, linea.precio, linea.cantidad) == (
        "Pegamento para PVC 1/4 gl [MT539]",
        "env",
        D("34.5694"),
        D(1),
    )
    assert abs(_cd(nueva) - D("37.254885")) <= TOLERANCIA
    assert abs(_pu(nueva) - D("47.127429525")) <= TOLERANCIA
    assert nueva.equipos == base.equipos and nueva.mano_obra == base.mano_obra


@pytest.mark.parametrize("modulo", MODULOS)
def test_cambiar_el_plomero_por_el_tecnico_cambia_el_sueldo_y_no_la_cantidad(
    modulo, _of001, _plantillas
) -> None:
    base = _of001[modulo].composiciones["AF-LLAVE"]
    tecnico = _fila(modulo, _plantillas[0], "mano_obra", "Tecnico")
    nueva = modulo.cambiar_insumo(base, "mano_obra", 0, tecnico)
    assert nueva.mano_obra[0].sueldo == D("10.0000") and nueva.mano_obra[0].cantidad == D(1)
    assert nueva.mano_obra[1] == base.mano_obra[1]
    assert abs(_cd(nueva) - D("13.16809")) <= TOLERANCIA
    assert abs(_pu(nueva) - D("16.65763385")) <= TOLERANCIA


@pytest.mark.parametrize("modulo", MODULOS)
def test_cambiar_el_equipo_conserva_la_depreciacion(modulo, _of001, _plantillas) -> None:
    base = _of001[modulo].composiciones["AF-LLAVE"]
    escalera = _fila(modulo, _plantillas[0], "equipo", "Escalera")
    nueva = modulo.cambiar_insumo(base, "equipo", 0, escalera)
    assert nueva.equipos[0].precio == D("247.9457")
    assert nueva.equipos[0].depreciacion == base.equipos[0].depreciacion
    assert nueva.equipos[0].cantidad == base.equipos[0].cantidad


@pytest.mark.parametrize(
    ("tipo", "indice", "mensaje"),
    [
        (
            "xx",
            0,
            "tipo de linea 'xx' desconocido; se espera uno de ('material', 'equipo', 'mano_obra')",
        ),
        ("material", 1, "la linea 2 no existe: el grupo material tiene 1 lineas"),
        ("mano_obra", 2, "la linea 3 no existe: el grupo mano_obra tiene 2 lineas"),
        ("material", -1, "la linea 0 no existe: el grupo material tiene 1 lineas"),
    ],
)
@pytest.mark.parametrize("modulo", MODULOS)
def test_los_errores_de_cambiar_insumo_son_los_de_la_clasica(
    modulo, _of001, _plantillas, tipo, indice, mensaje
) -> None:
    base = _of001[modulo].composiciones["AF-LLAVE"]
    pegamento = _fila(modulo, _plantillas[0], "material", "pegamento")
    with pytest.raises(HojaInvalida) as error:
        modulo.cambiar_insumo(base, tipo, indice, pegamento)
    assert str(error.value) == mensaje
