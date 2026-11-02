"""El informe de la importacion en `aplicacion.hoja_plano` (T10, 3e-2): filas en tiempo lineal.

`filas_del_informe` de `aplicacion/hoja.py` quita las referencias internas `(SF5-1, SF5-2)` con
una expresion regular cuyo espacio inicial opcional hace la sustitucion CUADRATICA en una corrida
larga de espacios: medido en este equipo, 100 000 espacios en un mensaje tardan decenas de
segundos. El mensaje sale del plano subido (capas, textos), asi que un DXF hostil lo puede
provocar dentro del tope de 20 MiB. La API usa una version lineal
(`hoja_plano.filas_del_informe`): esta prueba fija con literales a mano el texto de cada caso y
mide el caso hostil. Ya no compara contra `ui.hoja` (retiro de Streamlit, F6).

Oraculos a mano: el texto esperado de cada caso esta escrito aqui (quitar la referencia y los
espacios que la preceden, nada mas).
"""

from __future__ import annotations

import time

import pytest

from adapters.espacio.planos import ItemInforme, TipoItem
from aplicacion import hoja, hoja_plano
from tests.fixtures.planos_de_la_hoja import DXF_OF001

CLAVES = ("tipo", "referencia", "fila", "mensaje")

CASOS = [
    ("", ""),
    ("sin referencias", "sin referencias"),
    ("texto (SF5-1, SF5-2)", "texto"),
    ("a  (SF1-2)b", "ab"),
    ("(SF1-1)", ""),
    ("x (SF1-1)(SF2-2) y", "x y"),
    ("x\t\n(SF3-4,  SF3-5) fin", "x fin"),
    ("( SF1-1) queda", "( SF1-1) queda"),
    ("(SF1-) queda", "(SF1-) queda"),
    ("(SF1-1 sin cerrar", "(SF1-1 sin cerrar"),
    ("  (SF1-1)  ", "  "),
    ("a (SF1-1)", "a"),
    ("a\x1c(SF1-1)", "a"),
    ("a (SF1-1, ) b", "a b"),
    ("a (SF12-345,SF6-7) b (SF8-9)", "a b"),
    ("(sf1-1) minusculas", "(sf1-1) minusculas"),
]


def _item(mensaje: str) -> ItemInforme:
    return ItemInforme(TipoItem.APROXIMADO, "esp_puntos", "H1", "P1", mensaje)


@pytest.mark.parametrize(("mensaje", "esperado"), CASOS)
def test_cada_mensaje_queda_sin_sus_referencias_internas(mensaje, esperado) -> None:
    (fila,) = hoja_plano.filas_del_informe([_item(mensaje)])
    assert fila == {"tipo": "Aproximado", "referencia": "H1", "fila": "P1", "mensaje": esperado}


def test_el_informe_del_dxf_de_of001_cuenta_33_importados_y_6_pendientes() -> None:
    """Memoria de OF-001: 33 elementos importados (6 ambientes + 6 fuentes + 21 puntos) y las 6
    alturas pendientes de los ambientes; ninguna fila conserva una referencia interna."""
    informe = hoja.leer_plano(DXF_OF001).informe
    filas = hoja_plano.filas_del_informe(informe)
    assert len(filas) == len(informe)
    assert [f["tipo"] for f in filas].count("Importado") == 33
    assert [f["tipo"] for f in filas].count("Pendiente") == 6
    assert {f["tipo"] for f in filas} == {"Importado", "Aproximado", "Pendiente"}
    assert all(set(f) == set(CLAVES) for f in filas)
    assert not any("(SF" in f["mensaje"] for f in filas)


@pytest.mark.parametrize(
    ("mensaje", "esperado"),
    [
        (" " * 100_000, " " * 100_000),
        (" " * 100_000 + "(SF1-1)", ""),
        ("x" + " " * 100_000 + "(x", "x" + " " * 100_000 + "(x"),
        ("(SF1-1, " * 14_000, "(SF1-1, " * 14_000),
        (" (SF1-1)" * 12_500, ""),
    ],
    ids=["espacios", "espacios-y-referencia", "espacios-y-parentesis", "sin-cierre", "muchas"],
)
def test_un_mensaje_hostil_de_100_000_caracteres_tarda_menos_de_un_segundo(
    mensaje, esperado
) -> None:
    inicio = time.perf_counter()
    (fila,) = hoja_plano.filas_del_informe([_item(mensaje)])
    assert time.perf_counter() - inicio < 1
    assert fila["mensaje"] == esperado


# --- ronda 1 del arbitro: cada red de `_sin_rutas` por separado ---


def _rechazo(mensaje: str):
    from adapters.espacio.planos import EstadoImportacion, ResultadoImportacion

    return ResultadoImportacion(
        formato="dxf", archivo="a.dxf", estado=EstadoImportacion.RECHAZADA, mensaje=mensaje
    )


@pytest.mark.parametrize(
    "motivo",
    ["OSError: [Errno 5] Input/output error", "OSError: [WinError 32] El archivo esta en uso"],
)
def test_la_marca_de_un_oserror_basta_aunque_no_traiga_la_ruta(motivo, tmp_path) -> None:
    resultado = hoja_plano._sin_rutas(_rechazo(f"a.dxf: no se pudo leer ({motivo})."), tmp_path)
    assert resultado.mensaje == hoja_plano.mensaje_sin_ruta("a.dxf")


@pytest.mark.parametrize("escritura", ["tal cual", "repr", "barras"])
def test_el_comienzo_de_la_raiz_basta_aunque_no_haya_marca_ni_raiz_entera(
    escritura, tmp_path
) -> None:
    comienzo = str(tmp_path.parent)[:15]  # ancla y primer componente, recortado como el lector
    texto = {
        "tal cual": comienzo,
        "repr": comienzo.replace("\\", "\\\\"),
        "barras": comienzo.replace("\\", "/"),
    }[escritura]
    carpeta = tmp_path / "silice_planos_x"
    resultado = hoja_plano._sin_rutas(_rechazo(f"a.dxf: no se pudo leer ('{texto}...)."), carpeta)
    assert resultado.mensaje == hoja_plano.mensaje_sin_ruta("a.dxf")


def test_un_mensaje_sin_rutas_queda_igual(tmp_path) -> None:
    mensaje = "a.dxf: no se pudo leer como DXF (DXFStructureError: el archivo esta vacio)."
    assert hoja_plano._sin_rutas(_rechazo(mensaje), tmp_path / "x").mensaje == mensaje
