"""3b-B3C (T10, 3c-1): `espacio_desde_filas` y `completar_composiciones`.

Corre las funciones que edita la ruta E1 de la sub-rebanada 3c-1 y fija lo que producen: el
espacio, los textos de error (igualdad exacta de cadena) y lo que el espacio derivado dice despues
(cantidades y Estado por fila). Casos: OF-001 (espacio completo), TI-001 (sin espacio) y un
espacio armado a mano. Ya no compara contra `ui.hoja` (retiro de Streamlit, F6).

Oraculos: el espacio de la memoria de OF-001 (`tests/fixtures/espacio_of001.py`), las cantidades de
`tests/fixtures/memorias/of001.md` §2.2 y §2.4 recalculadas a mano con el alto de la cocineta en
3,0 m (sube 3,0 + en x 1,0 + baja 2,1 = 6,1 m; tuberia de 1/2": 2,4 + 6,1 = 8,5 x 1,10 = **9,35**;
picado de pared de agua fria: 5,7 + (3,0 + 2,1) = **10,8**), y los textos de error escritos a mano
desde `docs/especificaciones/2026-10-19-hoja-react-design.md` §2.5.1 y desde los mensajes de
`adapters/espacio/modelo.py`. Ninguno sale del codigo que se prueba.
"""

from __future__ import annotations

import copy
import dataclasses
import shutil
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.espacio import (
    Coord,
    Espacio,
    ModoRecorrido,
    Recorrido,
    SuperficieTramo,
    Tramo,
)
from aplicacion import hoja
from aplicacion.errores import HojaInvalida
from core.catalog import Catalogo, abrir_sesion, crear_motor
from tests.fixtures import caso_of001
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001

D = Decimal


def _filas() -> dict[str, list[dict[str, str]]]:
    """Las cinco tablas de OF-001 tal como las muestra el editor."""
    return copy.deepcopy(hoja.filas_desde_espacio(espacio_of001()))


def _fila(filas: dict[str, list[dict[str, str]]], tabla: str, id_: str) -> dict[str, str]:
    return next(f for f in filas[tabla] if f["id"] == id_)


# --- las filas: el espacio que describen las tablas -----------------------------------------


def test_las_tablas_de_of001_reconstruyen_el_espacio_de_la_memoria() -> None:
    base = espacio_of001()
    assert hoja.espacio_desde_filas(_filas(), base=base) == base


def test_sin_tablas_el_espacio_es_el_vacio_de_ti001() -> None:
    """TI-001 no tiene espacio (FR-5): ninguna tabla, o las cinco vacias, dan el espacio vacio."""
    assert hoja.espacio_desde_filas({}) == Espacio()
    vacias = {t: [] for t in ("origenes", "ambientes", "fuentes", "puntos", "tramos")}
    assert hoja.espacio_desde_filas(vacias, base=Espacio()) == Espacio()
    assert hoja.filas_desde_espacio(Espacio()) == vacias


def test_una_tabla_ausente_cuenta_como_vacia() -> None:
    """Sin la tabla de vertices, el recorrido declarado de la base se va; con ella, se conserva."""
    declarado = Recorrido(
        id="R9",
        modo=ModoRecorrido.DECLARADO,
        punto_id="P1",
        tramos=(
            Tramo(
                orden=1,
                superficie=SuperficieTramo.PARED,
                vertices=(Coord(D(0), D(0), D(0)), Coord(D(0), D(0), D(2))),
            ),
        ),
    )
    base = replace(espacio_of001(), recorridos=(declarado,))
    filas = copy.deepcopy(hoja.filas_desde_espacio(base))
    assert len(filas["tramos"]) == 1
    assert hoja.espacio_desde_filas(filas, base=base) == base
    sin_tramos = {t: f for t, f in filas.items() if t != "tramos"}
    resultado = hoja.espacio_desde_filas(sin_tramos, base=base)
    assert resultado.recorridos == ()
    assert resultado.circuitos == base.circuitos and resultado.puntos == base.puntos


def test_una_fila_en_blanco_no_es_un_error_ni_agrega_nada() -> None:
    base = espacio_of001()
    filas = _filas()
    filas["ambientes"] += [{}, {c: "" for c in hoja.COLUMNAS["ambientes"]}]
    filas["puntos"].insert(2, {})
    assert hoja.espacio_desde_filas(filas, base=base) == base


def test_los_circuitos_de_la_base_se_conservan_aunque_el_editor_no_los_muestre() -> None:
    base = espacio_of001()
    filas = _filas()
    _fila(filas, "ambientes", "COC-01")["alto"] = "3"
    resultado = hoja.espacio_desde_filas(filas, base=base)
    assert [c.id for c in resultado.circuitos] == ["C1", "C2"]
    assert resultado.circuitos == base.circuitos
    coc = next(a for a in resultado.ambientes if a.id == "COC-01")
    assert coc.alto == D("3")


def test_un_recorrido_propuesto_se_va_con_su_punto_y_un_declarado_lo_reemplaza() -> None:
    """H:617-623, a mano: dos propuestos (P1 y P2); sin P2 en la tabla solo queda el de P1."""
    base = replace(
        espacio_of001(),
        recorridos=(
            Recorrido(id="RP1", modo=ModoRecorrido.PROPUESTO, punto_id="P1"),
            Recorrido(id="RP2", modo=ModoRecorrido.PROPUESTO, punto_id="P2"),
        ),
    )
    filas = _filas()
    filas["puntos"] = [f for f in filas["puntos"] if f["id"] != "P2"]
    resultado = hoja.espacio_desde_filas(filas, base=base)
    assert [r.id for r in resultado.recorridos] == ["RP1"]
    # un recorrido declarado con el nombre de un propuesto lo reemplaza
    filas["tramos"] = [
        {
            "recorrido_id": "RP1",
            "punto_id": "P1",
            "circuito_id": "",
            "orden": "1",
            "superficie": "pared",
            "empotrado": "si",
            "pendiente": "",
            "vertices": "0,0,0; 0,0,2",
        }
    ]
    declarado = hoja.espacio_desde_filas(filas, base=base).recorridos
    assert [(r.id, r.modo) for r in declarado] == [("RP1", ModoRecorrido.DECLARADO)]


# --- los mensajes de error ------------------------------------------------------------------


def _con(tabla: str, id_: str | None, **celdas: str):
    def cambiar(filas: dict[str, list[dict[str, str]]]) -> None:
        destino = filas[tabla][0] if id_ is None else _fila(filas, tabla, id_)
        destino.update(celdas)

    return cambiar


def _repetir_ambiente(filas: dict[str, list[dict[str, str]]]) -> None:
    filas["ambientes"].append(dict(_fila(filas, "ambientes", "BAN-01")))


def _tramo_suelto(**celdas: str):
    def agregar(filas: dict[str, list[dict[str, str]]]) -> None:
        tramo = {
            "recorrido_id": "R9",
            "punto_id": "P1",
            "circuito_id": "",
            "orden": "1",
            "superficie": "pared",
            "empotrado": "",
            "pendiente": "",
            "vertices": "0,0,0; 0,0,2",
        }
        tramo.update(celdas)
        filas["tramos"] = [tramo]

    return agregar


#: (como se rompe la tabla, el mensaje que debe salir). Los textos son los de
#: H:452-492 y H:564-568 del diseno (§2.5.1) y los del modelo `Espacio`; la fila es la posicion de
#: la fila en la tabla enviada, desde 1 (los ambientes de OF-001 salen por id: COC-01 es la 2).
ERRORES = [
    pytest.param(
        _con("ambientes", "COC-01", alto="2,5"),
        "ambientes, fila 2: alto: '2,5' no es un numero decimal valido",
        id="coma-decimal",
    ),
    pytest.param(
        _con("ambientes", "BAN-01", largo="mucho"),
        "ambientes, fila 1: largo: 'mucho' no es un numero decimal valido",
        id="no-numero",
    ),
    pytest.param(
        _con("origenes", None, tipo="mapa"),
        "origenes de medida, fila 1: tipo: 'mapa' no es un valor valido "
        "(plano, dxf, ifc, levantamiento, supuesto, ia)",
        id="lista-cerrada",
    ),
    pytest.param(
        _con("origenes", None, referencia="sin igual"),
        "origenes de medida, fila 1: referencia: 'sin igual' no tiene la forma clave=valor",
        id="clave-valor",
    ),
    pytest.param(
        _con("puntos", "P1", x="1", y="dos", z="0"),
        "puntos, fila 8: posicion y: 'dos' no es un numero decimal valido",
        id="coordenada",
    ),
    pytest.param(
        _tramo_suelto(recorrido_id=""),
        "vertices de recorridos, fila 1: recorrido_id: el tramo debe nombrar su recorrido",
        id="tramo-sin-recorrido",
    ),
    pytest.param(
        _tramo_suelto(orden="uno"),
        "vertices de recorridos, fila 1: orden: 'uno' no es un entero",
        id="orden-no-entero",
    ),
    pytest.param(
        _tramo_suelto(vertices="0,0; 1,1,1"),
        "vertices de recorridos, fila 1: vertices: '0,0' no tiene la forma x,y,z",
        id="vertice-mal-formado",
    ),
    pytest.param(
        _tramo_suelto(vertices="0,0,0"),
        "vertices de recorridos, fila 1: vertices: un tramo necesita dos vertices x,y,z o mas, "
        "separados por «;»",
        id="un-solo-vertice",
    ),
    pytest.param(
        _tramo_suelto(empotrado="tal vez"),
        "vertices de recorridos, fila 1: empotrado: 'tal vez' debe ser «si», «no» o quedar vacio",
        id="tri-estado",
    ),
    pytest.param(
        _repetir_ambiente,
        "ids repetidos en ambientes: ['BAN-01']",
        id="id-duplicado",
    ),
    pytest.param(
        _con("puntos", "P1", fuente_id="XX"),
        "el punto 'P1' cita una fuente inexistente: 'XX'",
        id="referencia-rota",
    ),
]


@pytest.mark.parametrize(("romper", "mensaje"), ERRORES)
def test_el_texto_de_cada_error_es_el_escrito_a_mano(romper, mensaje) -> None:
    filas = _filas()
    romper(filas)
    with pytest.raises(HojaInvalida) as error:
        hoja.espacio_desde_filas(filas, base=espacio_of001())
    assert str(error.value) == mensaje


# --- cantidades y Estado tras editar el espacio ------------------------------------


def _con_sesion(plantilla: Path, destino: Path):
    copiado = destino / "copia.db"
    shutil.copyfile(plantilla, copiado)
    motor = crear_motor(f"sqlite:///{copiado.as_posix()}")
    return motor, abrir_sesion(motor)


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_of001(tmp_path_factory.mktemp("hoja_espacio") / "of001.db")


def _abierta(sesion):
    return hoja.abrir_version(
        sesion, Catalogo(sesion), NOMBRE_OF001, "001", fecha_evaluacion=caso_of001.FECHA
    )


def _cantidades(borrador) -> dict[str, Decimal]:
    return {i.codigo_partida: i.cantidad for i in hoja.items_elaborados(borrador)}


def _estado(borrador) -> dict[str, tuple]:
    resultado = hoja.elaborar_borrador(borrador)
    return {
        k: (None if e.severidad is None else e.severidad.name, e.texto)
        for k, e in resultado.estado.items()
    }


def test_editar_el_alto_de_la_cocineta_da_las_cantidades_y_el_estado_a_mano(
    _plantilla, tmp_path
) -> None:
    motor, sesion = _con_sesion(_plantilla, tmp_path)
    try:
        abierta = _abierta(sesion)
        filas = hoja.filas_desde_espacio(abierta.borrador.espacio)
        _fila(filas, "ambientes", "COC-01")["alto"] = "3"
        editado = replace(
            abierta.borrador,
            espacio=hoja.espacio_desde_filas(filas, base=abierta.borrador.espacio),
        )
        cantidades, estado = _cantidades(editado), _estado(editado)
    finally:
        sesion.close()
        motor.dispose()
    # el oraculo a mano (memoria of001.md §2.2/§2.4 con la cocineta a 3,0 m)
    assert cantidades["AF-TUB-PVC-1/2"] == D("9.35")
    assert cantidades["AF-PICADO-PARED"] == D("10.8")
    assert cantidades["AF-LLAVE"] == D("3")  # lo que no depende del alto no cambia
    assert cantidades["DR-TUB-PVC-2"] == D("4.345")
    assert estado["esp_ambientes:COC-01"][0] == "ADVERTENCIA"  # y el resto de las filas
    # y lo unico que cambio es esa celda
    assert [
        (c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo)
        for c in hoja.cambios_entre(abierta.borrador, editado)
    ] == [("metraje", "esp_ambientes:COC-01", "alto", "2.5", "3")]


def test_las_filas_de_of001_son_las_de_la_memoria() -> None:
    """Memoria of001.md §1.1-§1.3, a mano: la cocineta, su montante de agua y su fregadero."""
    filas = hoja.filas_desde_espacio(espacio_of001())
    assert (len(filas["ambientes"]), len(filas["fuentes"]), len(filas["puntos"])) == (6, 6, 21)
    assert _fila(filas, "ambientes", "COC-01") == {
        "id": "COC-01",
        "nombre": "Cocineta",
        "x0": "0",
        "y0": "1.5",
        "largo": "2",
        "ancho": "1.5",
        "alto": "2.5",
        "origen_id": "O1",
    }
    assert _fila(filas, "fuentes", "FC1") == {
        "id": "FC1",
        "especialidad": "agua",
        "tipo": "montante_agua",
        "ambiente_id": "COC-01",
        "x": "0",
        "y": "1.5",
        "z": "0",
        "origen_id": "O1",
    }
    pc1 = _fila(filas, "puntos", "PC1")
    assert (pc1["ambiente_id"], pc1["superficie"], pc1["fuente_id"]) == ("COC-01", "pared", "FC1")
    assert (pc1["x"], pc1["y"], pc1["z"]) == ("1", "1.5", "0.9")


def test_completar_composiciones_trae_del_catalogo_la_partida_que_falta(
    _plantilla, tmp_path
) -> None:
    motor, sesion = _con_sesion(_plantilla, tmp_path)
    try:
        abierta = _abierta(sesion)
        lista = hoja.lista_de_version(sesion, NOMBRE_OF001, "001")
        sin_salida = {k: v for k, v in abierta.borrador.composiciones.items() if k != "AF-SALIDA"}
        recortado = replace(abierta.borrador, composiciones=sin_salida)
        assert "AF-SALIDA" not in recortado.composiciones  # parte de una version sin ese APU
        completo = hoja.completar_composiciones(Catalogo(sesion), recortado, lista=lista)
        original = abierta.borrador.composiciones
    finally:
        sesion.close()
        motor.dispose()
    assert set(completo.composiciones) == set(original) and len(original) == 30  # las 30
    assert completo.composiciones["AF-SALIDA"] == original["AF-SALIDA"]  # la que traia la version
    assert dataclasses.asdict(completo.composiciones["AF-SALIDA"]) == dataclasses.asdict(
        original["AF-SALIDA"]
    )


def test_completar_composiciones_sin_nada_nuevo_devuelve_el_mismo_borrador(
    _plantilla, tmp_path
) -> None:
    motor, sesion = _con_sesion(_plantilla, tmp_path)
    try:
        abierta = _abierta(sesion)
        assert hoja.completar_composiciones(Catalogo(sesion), abierta.borrador) is abierta.borrador
    finally:
        sesion.close()
        motor.dispose()
