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
from dataclasses import replace
from datetime import date
from types import SimpleNamespace

import pytest

from adapters.espacio import Espacio
from adapters.espacio.planos import ItemInforme, TipoItem
from aplicacion import hoja, hoja_plano
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.planos_de_la_hoja import DXF_OF001, of001_declarado

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


# --- lo que de verdad entró de un plano con filas omitidas (hallazgo 6 y revisión, 2026-11-20) ----
#
# Fusiones reales (`hoja.fusionar_plano`) del DXF de OF-001 sobre un borrador cuyo espacio ya tiene
# filas escritas a mano con los mismos `id`: esas filas del plano se omiten («su id ya lo usa otra
# fila de la hoja»). Oráculos a mano desde la memoria: 6 ambientes, 6 fuentes y 21 puntos (33).


def _fusion_sobre(espacio) -> hoja_plano.Fusion:
    leido = of001_declarado()
    borrador, informe = hoja.fusionar_plano(
        hoja.Borrador(fecha=date(2026, 10, 5), espacio=espacio), leido
    )
    assert borrador.espacio != espacio  # algo entró: el borrador cambia
    resumen = hoja_plano.resumen_de_la_fusion(leido, informe)
    return hoja_plano.Fusion(SimpleNamespace(), leido, informe, resumen, True)


def _a_mano_con_solo(ambiente_id: str):
    """El espacio de OF-001 escrito a mano con un solo ambiente (y su origen)."""
    oficina = espacio_of001()
    (ambiente,) = [a for a in oficina.ambientes if a.id == ambiente_id]
    origenes = tuple(o for o in oficina.origenes if o.id == ambiente.origen_id)
    return Espacio(ambientes=(ambiente,), origenes=origenes)


def _a_mano_sin_circuitos():
    """Todo OF-001 escrito a mano, sin circuitos: del plano solo entran sus dos circuitos."""
    oficina = espacio_of001()
    puntos = tuple(replace(p, circuito_id=None) for p in oficina.puntos)
    return replace(oficina, puntos=puntos, circuitos=(), recorridos=())


def _registro(fusion: hoja_plano.Fusion) -> str:
    vivo = SimpleNamespace(importaciones=())
    hoja_plano._anotar_en_el_registro(vivo, "plano.dxf", "ana", fusion.resumen)
    return vivo.importaciones[0].resumen


def test_con_un_ambiente_a_mano_las_cifras_de_la_fusion_cuentan_lo_que_entro_una_vez() -> None:
    """BAN-01 escrito a mano: se omiten el ambiente, su fuente y sus 5 puntos (7 de las 33 filas;
    entran 26). Las filas por tabla cuentan solo la fusión: 5 ambientes, 5 fuentes, 16 puntos y
    los 2 circuitos (antes se sumaba también lo del lector: 10, 8, 34)."""
    fusion = _fusion_sobre(_a_mano_con_solo("BAN-01"))
    vista = hoja_plano.vista_de_fusion(fusion)
    por_tipo = {f["rotulo"]: f["cantidad"] for f in vista["fusion"]["por_tipo"]}
    assert (por_tipo["Importado"], por_tipo["Omitido"]) == (26, 7)
    assert vista["fusion"]["filas_por_tabla"] == [
        {"rotulo": "Ambientes", "cantidad": 5},
        {"rotulo": "Fuentes", "cantidad": 5},
        {"rotulo": "Puntos", "cantidad": 16},
        {"rotulo": "Circuitos", "cantidad": 2},
    ]
    assert vista["mensaje"].startswith(
        "Se fusionó «of001.dxf» con el borrador de la hoja: entraron 26 de las 33 filas del "
        "plano; las otras 7 se omitieron (el informe de abajo dice por qué). "
    )
    assert _registro(fusion) == "26 filas en el espacio"


def test_si_solo_entran_los_circuitos_el_mensaje_y_el_registro_dicen_eso() -> None:
    """Todo OF-001 escrito a mano sin circuitos: las 33 filas se omiten y entran C1 y C2. El
    mensaje no dice «entraron 0 de las 33 filas» ni el registro «0 filas en el espacio»."""
    fusion = _fusion_sobre(_a_mano_sin_circuitos())
    mensaje = hoja_plano.vista_de_fusion(fusion)["mensaje"]
    assert mensaje.startswith(
        "Se fusionó «of001.dxf» con el borrador de la hoja: no entró ninguna de las 33 filas del "
        "plano: se omitieron (el informe de abajo dice por qué). Sí cambió: 2 circuitos nuevos. "
    )
    assert _registro(fusion) == "no entró ninguna fila; 2 circuitos nuevos"


def _con_cuentas(importado: int, omitido: int) -> hoja_plano.Fusion:
    """Una fusión ficticia con sus cuentas ya hechas (las de `resumen_de_la_fusion`)."""
    rotulos = hoja.ROTULOS_DEL_INFORME
    leidas = tuple(
        ItemInforme(TipoItem.IMPORTADO, "esp_puntos", f"H{n}", f"P-{n}", "leída")
        for n in range(importado + omitido)
    )
    resumen = SimpleNamespace(
        por_tipo=((rotulos[TipoItem.IMPORTADO], importado), (rotulos[TipoItem.OMITIDO], omitido)),
        filas_por_tabla=(),
        origenes=1,
    )
    resultado = SimpleNamespace(archivo="plano.dxf", informe=leidas, filas={})
    return hoja_plano.Fusion(SimpleNamespace(), resultado, leidas, resumen, True)


def test_el_mensaje_concuerda_en_singular() -> None:
    mensaje = hoja_plano.vista_de_fusion(_con_cuentas(1, 1))["mensaje"]
    assert ": entró 1 de las 2 filas del plano; la otra se omitió (el informe" in mensaje


