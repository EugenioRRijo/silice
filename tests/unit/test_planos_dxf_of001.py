"""Compuerta GSF5 (RF-50): el DXF de OF-001, con las alturas cargadas, da las mismas cantidades
derivadas que la hoja manual a +-0,001 m (spec §4.2 y §11.2).

El DXF (`tests/fixtures/planos/of001.dxf`) se dibujo desde las TABLAS de la memoria de calculo
(`scripts/dibujar_of001_dxf.py`), nunca desde la hoja `tests/fixtures/espacio_of001.py`:
contra esta se compara, asi que la comparacion no es circular. Las pruebas vigilan esa
independencia.
"""

from __future__ import annotations

import ast
import datetime
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

import ezdxf
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from adapters.espacio import (
    ESPECIALIDADES,
    Espacio,
    cargar_espacio,
    crear_esquema_espacio,
    derivar,
    guardar_espacio,
)
from adapters.espacio.planos.dxf import importar_dxf
from adapters.espacio.planos.informe import EstadoImportacion, TipoItem, cargar_alturas, fusionar
from adapters.espacio.reglas import CoherenciaEspacial, OrigenDeLaMedida
from core.contracts import Severidad
from core.contracts.presupuesto import Presupuesto
from tests.fixtures.espacio_of001 import espacio_of001

D = Decimal
RAIZ = Path(__file__).resolve().parents[2]
DXF = RAIZ / "tests" / "fixtures" / "planos" / "of001.dxf"
README = RAIZ / "tests" / "fixtures" / "planos" / "README.md"
SCRIPT = RAIZ / "scripts" / "dibujar_of001_dxf.py"
MEMORIA = RAIZ / "tests" / "fixtures" / "memorias" / "of001.md"
TOLERANCIA = D("0.001")
VACIO = Presupuesto(codigo="X", fecha=datetime.date(2026, 1, 1), moneda="USD", partidas=())


def _techo() -> Decimal:
    """Altura de los ambientes: la dice la MEMORIA a mano (bloque JSON), no la hoja."""
    bloque = re.findall(r"```json\n(.*?)\n```", MEMORIA.read_text(encoding="utf-8"), re.DOTALL)[0]
    return D(json.loads(bloque)["techo"])


@pytest.fixture(scope="module")
def importado():
    return importar_dxf(DXF)


@pytest.fixture(scope="module")
def cargado(importado):
    return cargar_alturas(importado, {a.id: _techo() for a in importado.ambientes})


def _firma(items):
    return sorted((i.codigo_partida, i.unidad, i.cantidad) for i in items)


# --- el archivo y su procedencia ----------


def test_el_dxf_existe_con_su_procedencia_declarada():
    assert DXF.is_file()
    texto = README.read_text(encoding="utf-8")
    for dicho in ("of001.dxf", "memorias/of001.md", "ezdxf", "programático"):
        assert dicho in texto.lower(), dicho
    assert re.search(r"RNF[-‑]09", texto)
    assert "dibujar_of001_dxf.py" in texto


def test_el_script_que_dibuja_no_importa_la_hoja_ni_los_adaptadores():
    arbol = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    importados = {
        n.module if isinstance(n, ast.ImportFrom) else a.name
        for n in ast.walk(arbol)
        if isinstance(n, ast.Import | ast.ImportFrom)
        for a in (n.names if isinstance(n, ast.Import) else [n])
    }
    assert not {
        m for m in importados if m and m.split(".")[0] in ("adapters", "core", "tests", "ui")
    }


def _resumen(ruta: Path) -> list:
    """Contenido del espacio modelo (tipo, capa, handle, geometria, atributos y texto), sin el orden
    interno de las tablas de ezdxf, que depende de la semilla de hash de Python."""
    filas = []
    for e in ezdxf.readfile(ruta).modelspace():
        d = e.dxf
        geometria = (
            tuple(round(c, 6) for c in d.insert)
            if e.dxftype() in ("INSERT", "TEXT")
            else tuple(tuple(round(c, 6) for c in p) for p in e.get_points("xy"))
        )
        atributos = tuple(sorted((a.dxf.tag, a.dxf.text) for a in getattr(e, "attribs", ())))
        texto = d.text if e.dxftype() == "TEXT" else ""
        filas.append((e.dxftype(), d.layer, d.handle, geometria, atributos, texto))
    return filas


def test_el_script_regenera_el_mismo_contenido(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("dibujar_of001_dxf", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo  # los dataclass con slots buscan su modulo
    spec.loader.exec_module(modulo)
    salida = modulo.dibujar(tmp_path / "otra.dxf")
    assert _resumen(salida) == _resumen(DXF)
    assert len(_resumen(DXF)) == 39  # 6 polilineas, 6 textos, 6 fuentes y 21 puntos


def test_el_dxf_declara_metros_y_la_convencion_de_capas():
    doc = ezdxf.readfile(DXF)
    assert doc.units == 6
    capas = {e.dxf.layer for e in doc.modelspace()}
    assert capas == {
        "AMBIENTES",
        "FTE-AGUA",
        "FTE-DRENAJE",
        "FTE-DATOS",
        "FTE-ELEC",
        "PTO-AGUA",
        "PTO-DRENAJE",
        "PTO-DATOS",
        "PTO-TOMA",
        "PTO-LUZ",
    }


# --- la importacion ----------


def test_la_importacion_da_las_filas_de_la_memoria(importado):
    assert importado.estado is EstadoImportacion.IMPORTADA
    assert importado.filas["esp_ambientes"] == 6
    assert importado.filas["esp_fuentes"] == 6
    assert importado.filas["esp_puntos"] == 21
    assert importado.filas["esp_circuitos"] == 2
    assert importado.filas["esp_recorridos"] == 0  # no hay capas REC: todos son propuestos
    # 33 del plano (6 + 6 + 21) y 2 origenes SUPUESTOS, uno por circuito (RS-17)
    assert importado.filas["esp_origenes"] == 35


def test_nada_del_dxf_queda_sin_reconocer(importado):
    assert importado.conteos[TipoItem.NO_RECONOCIDO] == 0
    assert importado.conteos[TipoItem.IMPORTADO] == 33


def test_la_altura_de_los_seis_ambientes_queda_pendiente_y_r8_la_marca(importado):
    pendientes = [i for i in importado.informe if i.tipo is TipoItem.PENDIENTE]
    assert sorted(i.fila for i in pendientes if i.tabla == "esp_ambientes") == sorted(
        a.id for a in importado.ambientes
    )
    hallazgos = OrigenDeLaMedida(importado.espacio()).evaluar(VACIO)
    de_altura = [h for h in hallazgos if "ambiente" in h.descripcion and "altura" in h.descripcion]
    assert len(de_altura) == 6 and {h.severidad for h in de_altura} == {Severidad.ADVERTENCIA}


def test_con_las_alturas_cargadas_r8_ya_no_marca_ningun_ambiente(cargado):
    hallazgos = OrigenDeLaMedida(cargado.espacio()).evaluar(VACIO)
    assert not [h for h in hallazgos if "altura pendiente" in h.descripcion]
    assert not [h for h in hallazgos if h.severidad is Severidad.ERROR]


def test_el_espacio_importado_es_coherente(cargado):
    espacio = cargado.espacio()
    assert espacio.validar() == []
    assert not [h for h in CoherenciaEspacial(espacio).evaluar(VACIO) if "origen" in h.descripcion]


def test_las_filas_importadas_coinciden_con_la_hoja_manual(cargado):
    hoja = espacio_of001()
    for tabla in ("ambientes", "fuentes", "puntos"):
        del_dxf = {f.id: f for f in getattr(cargado.espacio(), tabla)}
        de_la_hoja = {f.id: f for f in getattr(hoja, tabla)}
        assert set(del_dxf) == set(de_la_hoja), tabla
    for id_, a in {a.id: a for a in hoja.ambientes}.items():
        b = next(x for x in cargado.ambientes if x.id == id_)
        for campo in ("x0", "y0", "largo", "ancho", "alto"):
            assert abs(getattr(a, campo) - getattr(b, campo)) <= TOLERANCIA, (id_, campo)
    for p in hoja.puntos:
        q = next(x for x in cargado.puntos if x.id == p.id)
        assert (q.tipo, q.especialidad, q.ambiente_id, q.superficie) == (
            p.tipo,
            p.especialidad,
            p.ambiente_id,
            p.superficie,
        ), p.id
        assert q.posicion.distancia(p.posicion) <= TOLERANCIA, p.id
        assert dict(q.especificaciones) == dict(p.especificaciones), p.id
    for c in hoja.circuitos:
        d = next(x for x in cargado.circuitos if x.id == c.id)
        assert (d.tablero, d.numero, d.conductores, d.calibre, d.puntos_maximos) == (
            c.tablero,
            c.numero,
            c.conductores,
            c.calibre,
            c.puntos_maximos,
        )


@pytest.mark.parametrize("especialidad", ESPECIALIDADES)
def test_el_dxf_da_las_mismas_cantidades_derivadas_que_la_hoja_manual(cargado, especialidad):
    """RF-50: mismas partidas y cantidades a +-0,001 m (conteos exactos)."""
    del_dxf = _firma(derivar(cargado.espacio(), especialidad))
    de_la_hoja = _firma(derivar(espacio_of001(), especialidad))
    assert del_dxf, "la hoja deriva algo para esta especialidad"
    assert [(c, u) for c, u, _ in del_dxf] == [(c, u) for c, u, _ in de_la_hoja]
    for (codigo, _, a), (_, _, b) in zip(del_dxf, de_la_hoja, strict=True):
        assert abs(a - b) <= TOLERANCIA, (especialidad, codigo, a, b)


def test_el_dxf_tiene_la_misma_cantidad_de_partidas_que_la_hoja(cargado):
    total_dxf = sum(len(derivar(cargado.espacio(), e)) for e in ESPECIALIDADES)
    total_hoja = sum(len(derivar(espacio_of001(), e)) for e in ESPECIALIDADES)
    assert total_dxf == total_hoja > 0


def test_sin_cargar_las_alturas_el_resultado_no_es_el_de_la_hoja(importado):
    """El oraculo no es trivial: con otra altura, las cifras cambian."""
    provisional = cargar_alturas(importado, {a.id: D("3.4") for a in importado.ambientes})
    distintas = [
        e
        for e in ESPECIALIDADES
        if _firma(derivar(provisional.espacio(), e)) != _firma(derivar(espacio_of001(), e))
    ]
    assert distintas, "una altura de 3,4 m debe cambiar alguna cantidad"


# --- reimportacion e idas y vueltas ----------


def test_reimportar_el_mismo_dxf_no_cambia_el_espacio(cargado):
    primero, _ = fusionar(Espacio(), cargado)
    segundo, informe = fusionar(primero, importar_dxf(DXF))
    assert segundo.ambientes == primero.ambientes
    assert segundo.puntos == primero.puntos  # las alturas cargadas se conservan
    assert segundo.fuentes == primero.fuentes
    assert not [i for i in informe if i.tipo in (TipoItem.DESAPARECIDO, TipoItem.OMITIDO)]
    assert {a.alto for a in segundo.ambientes} == {_techo()}


def test_reimportar_un_dxf_al_que_le_falta_una_entidad_la_marca(tmp_path):
    primero, _ = fusionar(Espacio(), importar_dxf(DXF))
    doc = ezdxf.readfile(DXF)
    msp = doc.modelspace()
    borrado = next(
        e
        for e in msp.query("INSERT")
        if {a.dxf.tag: a.dxf.text for a in e.attribs}.get("ID") == "LZ4"
    )
    handle = borrado.dxf.handle
    msp.delete_entity(borrado)
    ruta = tmp_path / DXF.name
    doc.saveas(ruta)
    espacio, informe = fusionar(primero, importar_dxf(ruta))
    assert "LZ4" in {p.id for p in espacio.puntos}
    assert [
        (i.tabla, i.fila, i.referencia) for i in informe if i.tipo is TipoItem.DESAPARECIDO
    ] == [("esp_puntos", "LZ4", handle)]
    hallazgos = OrigenDeLaMedida(espacio).evaluar(VACIO)
    assert any("plano" in h.descripcion and h.origen_ids == ("esp_puntos:LZ4",) for h in hallazgos)


def test_el_espacio_importado_sobrevive_a_guardar_y_cargar(tmp_path, cargado):
    espacio, _ = fusionar(Espacio(), cargado)
    motor = create_engine(f"sqlite:///{tmp_path / 'e.db'}")
    crear_esquema_espacio(motor)
    with Session(motor) as sesion:
        guardar_espacio(sesion, 1, espacio)
        sesion.commit()
    with Session(motor) as sesion:
        assert cargar_espacio(sesion, 1) == espacio
    motor.dispose()


def test_importar_dos_veces_el_mismo_archivo_da_el_mismo_resultado(importado):
    assert importar_dxf(DXF) == importado
