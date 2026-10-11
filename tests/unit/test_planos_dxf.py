"""Importacion de DXF con la convencion de capas (spec §6.6.1, RF-50, RNF-12, tarea 5.2).

Cada prueba dibuja con `ezdxf` el plano minimo que necesita (no hay archivos binarios en el
repositorio salvo `of001.dxf`, que cubre `test_planos_dxf_of001.py`). Las cifras esperadas son
literales aritmeticos de lo dibujado, no la salida del importador.
"""

from __future__ import annotations

import datetime
import io
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import ezdxf
import pytest

from adapters.espacio import (
    Espacio,
    ModoRecorrido,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoOrigen,
)
from adapters.espacio.planos.dxf import LIMITE_BYTES, MAX_ENTIDADES_DXF, importar_dxf
from adapters.espacio.planos.informe import EstadoImportacion, TipoItem, cargar_alturas, fusionar
from adapters.espacio.reglas import ALTO_PROVISIONAL, ALTURA_PENDIENTE, OrigenDeLaMedida
from core.contracts.presupuesto import Presupuesto

D = Decimal
VACIO = Presupuesto(codigo="X", fecha=datetime.date(2026, 1, 1), moneda="USD", partidas=())
OF001 = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "planos" / "of001.dxf"
ATRIBUTOS = ("ID", "ALTURA", "DIAMETRO", "CALIBRE", "CIRCUITO", "CATEGORIA", "LLAVE", "AMBIENTE")


class Plano:
    """Constructor de planos de prueba: capas, bloques con atributos y polilineas."""

    def __init__(self, unidades: int | None = 6) -> None:
        self.doc = ezdxf.new("R2010")
        if unidades is None:
            self.doc.header["$INSUNITS"] = 0
        else:
            self.doc.units = unidades
        self.msp = self.doc.modelspace()
        for nombre in ("CAJA", "PUNTO"):
            bloque = self.doc.blocks.new(nombre)
            bloque.add_circle((0, 0), 0.05)

    def sala(self, texto, x0, y0, x1, y1, capa="AMBIENTES", con_texto=True):
        poli = self.msp.add_lwpolyline(
            [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs={"layer": capa}
        )
        if con_texto:
            self.texto(texto, (x0 + x1) / 2, (y0 + y1) / 2, capa)
        return poli

    def texto(self, texto, x, y, capa="AMBIENTES"):
        return self.msp.add_text(texto, dxfattribs={"layer": capa, "insert": (x, y), "height": 0.1})

    def bloque(self, capa, x, y, nombre="PUNTO", z=0.0, **atributos):
        ref = self.msp.add_blockref(nombre, (x, y, z), dxfattribs={"layer": capa})
        for tag, valor in atributos.items():
            ref.add_attrib(tag.upper(), valor, (x, y), dxfattribs={"layer": capa})
        return ref

    def bytes(self) -> bytes:
        destino = io.StringIO()
        self.doc.write(destino)
        return destino.getvalue().encode("utf-8")


def plano_base(unidades: int | None = 6) -> Plano:
    """Una sala de 4 x 3 y otra de 2 x 3 al lado, sin altura."""
    p = Plano(unidades)
    p.sala("SALA", 0, 0, 4, 3)
    p.sala("COCINA", 4, 0, 6, 3)
    return p


def tipos(resultado, tipo):
    return [i for i in resultado.informe if i.tipo is tipo]


# --- ambientes ----------


def test_un_ambiente_rectangular_con_texto_adentro_es_una_fila():
    p = plano_base()
    r = importar_dxf(p.bytes(), nombre="casa.dxf")
    assert r.estado is EstadoImportacion.IMPORTADA
    sala = next(a for a in r.ambientes if a.id == "SALA")
    assert (sala.nombre, sala.x0, sala.y0, sala.largo, sala.ancho) == (
        "SALA",
        D(0),
        D(0),
        D(4),
        D(3),
    )
    assert sala.alto == ALTO_PROVISIONAL  # la altura queda pendiente
    assert [a.id for a in r.ambientes] == ["COCINA", "SALA"]


def test_la_fila_lleva_origen_dxf_con_archivo_capa_y_handle():
    p = plano_base()
    r = importar_dxf(p.bytes(), nombre="casa.dxf")
    handles = {e.dxf.handle for e in p.msp if e.dxftype() == "LWPOLYLINE"}
    sala = next(a for a in r.ambientes if a.id == "SALA")
    origen = r.origenes_por_id[sala.origen_id]
    assert origen.tipo is TipoOrigen.DXF
    ref = dict(origen.referencia)
    assert ref["archivo"] == "casa.dxf" and ref["capa"] == "AMBIENTES"
    assert ref["handle"] in handles
    assert not origen.incompleto  # R8 no lo marca ERROR


def test_la_altura_del_ambiente_se_informa_como_pendiente_y_r8_la_marca():
    r = importar_dxf(plano_base().bytes(), nombre="casa.dxf")
    pendientes = [i for i in tipos(r, TipoItem.PENDIENTE) if i.tabla == "esp_ambientes"]
    assert sorted(i.fila for i in pendientes) == ["COCINA", "SALA"]
    assert dict(r.origenes_por_id[r.ambientes[0].origen_id].referencia)["altura"] == "pendiente"


def test_un_ambiente_no_rectangular_se_aproxima_por_su_caja_y_se_declara():
    p = Plano()
    p.msp.add_lwpolyline(
        [(0, 0), (4, 0), (4, 1), (2, 1), (2, 3), (0, 3)],
        close=True,
        dxfattribs={"layer": "AMBIENTES"},
    )
    p.texto("EN-L", 0.5, 0.5)
    r = importar_dxf(p.bytes(), nombre="l.dxf")
    a = r.ambientes[0]
    assert (a.x0, a.y0, a.largo, a.ancho) == (D(0), D(0), D(4), D(3))
    aproximados = tipos(r, TipoItem.APROXIMADO)
    assert [(i.tabla, i.fila) for i in aproximados] == [("esp_ambientes", "EN-L")]
    assert "caja envolvente" in aproximados[0].mensaje


def test_un_ambiente_sin_texto_no_crea_fila_y_va_al_informe():
    p = Plano()
    poli = p.sala("X", 0, 0, 2, 2, con_texto=False)
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.ambientes == ()
    item = tipos(r, TipoItem.NO_RECONOCIDO)[0]
    assert item.referencia == poli.dxf.handle and "sin texto" in item.mensaje


def test_un_ambiente_con_dos_textos_no_se_adivina():
    p = Plano()
    p.sala("UNO", 0, 0, 4, 4)
    p.texto("DOS", 1, 1)
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.ambientes == ()
    assert "varios textos" in tipos(r, TipoItem.NO_RECONOCIDO)[0].mensaje


def test_un_texto_fuera_de_todo_ambiente_se_informa():
    p = plano_base()
    p.texto("HUERFANO", 20, 20)
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert len(r.ambientes) == 2
    assert any("HUERFANO" in i.mensaje for i in tipos(r, TipoItem.NO_RECONOCIDO))


def test_una_polilinea_abierta_en_ambientes_no_es_ambiente():
    p = Plano()
    p.msp.add_lwpolyline([(0, 0), (4, 0), (4, 3)], dxfattribs={"layer": "AMBIENTES"})
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.ambientes == ()
    assert "abierta" in tipos(r, TipoItem.NO_RECONOCIDO)[0].mensaje


def test_dos_ambientes_con_el_mismo_nombre_no_se_duplican():
    p = Plano()
    p.sala("IGUAL", 0, 0, 2, 2)
    p.sala("IGUAL", 5, 0, 7, 2)
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert len(r.ambientes) == 1
    assert "repetido" in tipos(r, TipoItem.NO_RECONOCIDO)[0].mensaje


def test_un_ambiente_degenerado_no_se_importa():
    p = Plano()
    p.sala("PLANO", 0, 0, 4, 0.0004)
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.ambientes == ()
    assert tipos(r, TipoItem.NO_RECONOCIDO)


# --- capas fuera de convencion ----------


def test_un_dxf_fuera_de_convencion_da_informe_y_ninguna_fila():
    p = Plano()
    p.msp.add_line((0, 0), (5, 0), dxfattribs={"layer": "MUROS"})
    p.msp.add_line((0, 0), (0, 5), dxfattribs={"layer": "MUROS"})
    p.msp.add_circle((1, 1), 0.2, dxfattribs={"layer": "COLUMNAS"})
    r = importar_dxf(p.bytes(), nombre="arq.dxf")
    assert r.estado is EstadoImportacion.IMPORTADA
    assert not any(r.filas[t] for t in r.filas if t != "esp_origenes") and not r.origenes
    capas = {i.tabla: i for i in tipos(r, TipoItem.NO_RECONOCIDO)}
    assert set(capas) == {"MUROS", "COLUMNAS"}
    assert "2 entidades" in capas["MUROS"].mensaje
    assert "convencion" in r.mensaje.lower() or "convención" in r.mensaje.lower()


def test_una_entidad_ajena_en_una_capa_de_la_convencion_se_informa():
    p = plano_base()
    p.msp.add_circle((1, 1), 0.2, dxfattribs={"layer": "FTE-AGUA"})
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.fuentes == ()
    assert any("FTE-AGUA" in i.mensaje for i in tipos(r, TipoItem.NO_RECONOCIDO))


def test_los_nombres_de_capa_no_distinguen_mayusculas():
    p = Plano()
    p.sala("S", 0, 0, 2, 2, capa="ambientes")
    assert [a.id for a in importar_dxf(p.bytes(), nombre="a.dxf").ambientes] == ["S"]


# --- fuentes ----------


@pytest.mark.parametrize(
    ("capa", "bloque", "tipo", "especialidad"),
    [
        ("FTE-AGUA", "MONTANTE", TipoFuente.MONTANTE_AGUA, "agua"),
        ("FTE-AGUA", "ACOMETIDA_PUBLICA", TipoFuente.ACOMETIDA_AGUA, "agua"),
        ("FTE-DRENAJE", "COLECTOR", TipoFuente.COLECTOR_DRENAJE, "agua"),
        ("FTE-DATOS", "RACK", TipoFuente.RACK, "datos"),
        ("FTE-ELEC", "TABLERO", TipoFuente.TABLERO, "electricidad"),
    ],
)
def test_cada_capa_fte_da_su_tipo_de_fuente(capa, bloque, tipo, especialidad):
    p = plano_base()
    p.doc.blocks.new(bloque).add_circle((0, 0), 0.1)
    p.bloque(capa, 1, 1, nombre=bloque, id="X1", altura="1.5")
    f = importar_dxf(p.bytes(), nombre="a.dxf").fuentes[0]
    assert (f.id, f.tipo, f.especialidad.value, f.ambiente_id) == ("X1", tipo, especialidad, "SALA")
    assert (f.posicion.x, f.posicion.y, f.posicion.z) == (D(1), D(1), D("1.5"))


def test_una_fuente_de_agua_sin_tipo_en_el_bloque_es_montante_aproximado():
    p = plano_base()
    p.bloque("FTE-AGUA", 1, 1, id="X1")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.fuentes[0].tipo is TipoFuente.MONTANTE_AGUA
    assert [i.fila for i in tipos(r, TipoItem.APROXIMADO)] == ["X1"]


def test_una_fuente_sin_atributo_id_toma_su_handle():
    p = plano_base()
    ref = p.bloque("FTE-DATOS", 1, 1, nombre="RACK")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.fuentes[0].id == f"FTE-DATOS-{ref.dxf.handle}"


def test_la_fuente_fuera_de_todo_ambiente_no_se_importa():
    p = plano_base()
    p.bloque("FTE-DATOS", 50, 50, nombre="RACK", id="R1")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.fuentes == ()
    assert "fuera de todo ambiente" in tipos(r, TipoItem.NO_RECONOCIDO)[0].mensaje


# --- puntos ----------


def test_un_punto_toma_su_altura_y_sus_atributos_opcionales():
    p = plano_base()
    p.bloque("FTE-AGUA", 0, 0, nombre="MONTANTE", id="F1")
    p.bloque("PTO-AGUA", 1, 2, id="P1", altura="0,6", diametro='1/2"', llave="si")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    pto = r.puntos[0]
    assert (pto.id, pto.tipo.value, pto.ambiente_id, pto.fuente_id) == (
        "P1",
        "agua_fria",
        "SALA",
        "F1",
    )
    assert (pto.posicion.x, pto.posicion.y, pto.posicion.z) == (D(1), D(2), D("0.6"))
    assert dict(pto.especificaciones) == {"diametro": '1/2"', "llave_de_paso": "si"}
    assert ALTURA_PENDIENTE not in pto.especificaciones


@pytest.mark.parametrize(
    ("capa", "tipo", "especialidad"),
    [
        ("PTO-AGUA", "agua_fria", "agua"),
        ("PTO-DRENAJE", "drenaje", "agua"),
        ("PTO-DATOS", "datos", "datos"),
        ("PTO-TOMA", "tomacorriente", "electricidad"),
        ("PTO-LUZ", "iluminacion", "electricidad"),
    ],
)
def test_cada_capa_pto_da_su_tipo_de_punto(capa, tipo, especialidad):
    p = plano_base()
    p.bloque(capa, 1, 1, id="X", altura="1")
    pto = importar_dxf(p.bytes(), nombre="a.dxf").puntos[0]
    assert (pto.tipo.value, pto.especialidad.value) == (tipo, especialidad)


def test_un_punto_sin_altura_queda_pendiente_y_r8_lo_marca():
    p = plano_base()
    p.bloque("PTO-DATOS", 1, 1, id="X")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert ALTURA_PENDIENTE in r.puntos[0].especificaciones
    de_altura = [i for i in tipos(r, TipoItem.PENDIENTE) if "altura" in i.mensaje]
    assert [i.fila for i in de_altura if i.tabla == "esp_puntos"] == ["X"]


def test_una_altura_que_no_es_numero_queda_pendiente_con_su_motivo():
    p = plano_base()
    p.bloque("PTO-DATOS", 1, 1, id="X", altura="alta")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert ALTURA_PENDIENTE in r.puntos[0].especificaciones
    assert any("alta" in i.mensaje for i in tipos(r, TipoItem.PENDIENTE))


@pytest.mark.parametrize(
    ("capa", "z", "esperada"),
    [
        ("PTO-LUZ", "2.5", SuperficiePunto.TECHO),
        ("PTO-DRENAJE", "0", SuperficiePunto.PISO),
        ("PTO-DRENAJE", "0.4", SuperficiePunto.PARED),
        ("PTO-TOMA", "0.3", SuperficiePunto.PARED),
        ("PTO-AGUA", "1.2", SuperficiePunto.PARED),
    ],
)
def test_la_superficie_se_infiere_del_tipo_y_la_altura(capa, z, esperada):
    p = plano_base()
    p.bloque(capa, 1, 1, id="X", altura=z)
    assert importar_dxf(p.bytes(), nombre="a.dxf").puntos[0].superficie is esperada


def test_el_atributo_superficie_manda_sobre_la_inferencia():
    p = plano_base()
    p.bloque("PTO-LUZ", 1, 1, id="X", altura="2.0", superficie="pared")
    assert importar_dxf(p.bytes(), nombre="a.dxf").puntos[0].superficie is SuperficiePunto.PARED


def test_un_punto_en_el_borde_de_dos_ambientes_sin_atributo_toma_el_mas_pequeno_y_se_aproxima():
    p = plano_base()  # SALA (12 m2) llega a x = 4 y COCINA (6 m2) empieza en x = 4
    p.bloque("PTO-DATOS", 4, 1, id="X", altura="0.3")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.puntos[0].ambiente_id == "COCINA"  # el de menor area
    assert any("varios ambientes" in i.mensaje for i in tipos(r, TipoItem.APROXIMADO))


def test_en_el_borde_gana_el_de_menor_area_aunque_su_id_sea_posterior():
    """Revision SF5: no se elige por orden alfabetico. A-GRANDE (4 x 3 = 12 m2) precede a B-CHICA
    (2 x 3 = 6 m2) en el alfabeto, pero el borde x = 4 se asigna al mas pequeno."""
    p = Plano()
    p.sala("A-GRANDE", 0, 0, 4, 3)
    p.sala("B-CHICA", 4, 0, 6, 3)
    p.bloque("PTO-DATOS", 4, 1, id="X", altura="0.3")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.puntos[0].ambiente_id == "B-CHICA"
    aviso = next(i for i in tipos(r, TipoItem.APROXIMADO) if "varios ambientes" in i.mensaje)
    assert "se toma B-CHICA" in aviso.mensaje and "A-GRANDE" in aviso.mensaje


def test_en_el_borde_con_igual_area_gana_el_id_menor():
    p = Plano()
    p.sala("B-IGUAL", 0, 0, 4, 3)
    p.sala("A-IGUAL", 4, 0, 8, 3)  # misma area (12 m2)
    p.bloque("FTE-DATOS", 4, 2, nombre="CAJA", id="R1", altura="1")
    p.bloque("PTO-DATOS", 4, 1, id="X", altura="0.3")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert next(x for x in r.puntos if x.id == "X").ambiente_id == "A-IGUAL"
    assert next(f for f in r.fuentes if f.id == "R1").ambiente_id == "A-IGUAL"


def test_la_eleccion_del_ambiente_de_borde_es_determinista():
    p = Plano()
    p.sala("A-GRANDE", 0, 0, 4, 3)
    p.sala("B-CHICA", 4, 0, 6, 3)
    p.bloque("PTO-DATOS", 4, 1, id="X", altura="0.3")
    datos = p.bytes()
    assert importar_dxf(datos, nombre="a.dxf") == importar_dxf(datos, nombre="a.dxf")


def test_el_atributo_ambiente_resuelve_el_borde():
    p = plano_base()
    p.bloque("PTO-DATOS", 4, 1, id="X", altura="0.3", ambiente="SALA")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.puntos[0].ambiente_id == "SALA"
    assert not [i for i in tipos(r, TipoItem.APROXIMADO) if "varios ambientes" in i.mensaje]


def test_un_atributo_ambiente_que_no_existe_deja_el_punto_fuera_y_en_el_informe():
    p = plano_base()
    p.bloque("PTO-DATOS", 1, 1, id="X", altura="0.3", ambiente="NO-EXISTE")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.puntos == ()
    assert "NO-EXISTE" in tipos(r, TipoItem.NO_RECONOCIDO)[0].mensaje


def test_un_id_repetido_en_dos_puntos_no_se_duplica():
    p = plano_base()
    p.bloque("PTO-DATOS", 1, 1, id="X", altura="0.3")
    p.bloque("PTO-DATOS", 2, 1, id="X", altura="0.3")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert len(r.puntos) == 1
    assert "repetido" in tipos(r, TipoItem.NO_RECONOCIDO)[0].mensaje


def test_la_fuente_del_punto_es_la_de_su_ambiente_o_la_mas_cercana():
    p = plano_base()
    p.bloque("FTE-AGUA", 0, 0, nombre="MONTANTE", id="FA")
    p.bloque("FTE-AGUA", 5, 0, nombre="MONTANTE", id="FB")
    p.bloque("PTO-AGUA", 3, 2, id="EN-SALA", altura="1")  # FA en su ambiente, FB en otro
    p.bloque("PTO-AGUA", 5.5, 2, id="EN-COCINA", altura="1")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    por_id = {x.id: x.fuente_id for x in r.puntos}
    assert por_id == {"EN-SALA": "FA", "EN-COCINA": "FB"}


def test_un_punto_sin_fuente_compatible_queda_pendiente():
    p = plano_base()
    p.bloque("PTO-DATOS", 1, 1, id="X", altura="0.3")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.puntos[0].fuente_id is None
    assert any("sin fuente" in i.mensaje for i in tipos(r, TipoItem.PENDIENTE))


def test_la_llave_que_no_es_si_se_ignora_y_se_informa():
    p = plano_base()
    p.bloque("PTO-AGUA", 1, 1, id="X", altura="1", llave="no")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert "llave_de_paso" not in dict(r.puntos[0].especificaciones)
    assert any("LLAVE" in i.mensaje for i in tipos(r, TipoItem.APROXIMADO))


# --- circuitos ----------


def _electrico(p: Plano, tableros=("T1",)):
    for i, t in enumerate(tableros):
        p.bloque("FTE-ELEC", 1 + i * 4, 1, nombre="TABLERO", id=t, altura="1.5")
    p.bloque("PTO-TOMA", 2, 2, id="T-A", altura="0.3", circuito="C1", calibre="12 AWG")
    p.bloque("PTO-TOMA", 3, 2, id="T-B", altura="0.3", circuito="C1", calibre="12 AWG")
    p.bloque("PTO-LUZ", 3, 1, id="L-A", altura="2.5", circuito="C2", calibre="14 AWG")


def test_los_circuitos_se_crean_con_su_tablero_calibre_y_supuestos_declarados():
    p = plano_base()
    _electrico(p)
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    c1, c2 = r.circuitos
    assert (c1.id, c1.tablero, c1.numero, c1.calibre) == ("C1", "T1", 1, "12 AWG")
    assert (c2.id, c2.numero, c2.calibre) == ("C2", 2, "14 AWG")
    assert c1.conductores == (1, 1, 1) and c1.puntos_maximos == 6 and c1.orden == ()
    assert {x.id: x.circuito_id for x in r.puntos if x.circuito_id} == {
        "T-A": "C1",
        "T-B": "C1",
        "L-A": "C2",
    }
    supuestos = [i for i in tipos(r, TipoItem.APROXIMADO) if i.tabla == "esp_circuitos"]
    assert sorted(i.fila for i in supuestos) == ["C1", "C2"]


def test_con_dos_tableros_el_circuito_toma_el_mas_cercano_a_sus_puntos():
    p = plano_base()
    _electrico(p, tableros=("T1", "T2"))  # T1 en (1;1), T2 en (5;1); los puntos de C1 en x 2 a 3
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert next(c for c in r.circuitos if c.id == "C1").tablero == "T1"


def test_sin_tablero_no_se_crea_el_circuito_y_el_punto_queda_pendiente():
    p = plano_base()
    p.bloque("PTO-TOMA", 2, 2, id="T-A", altura="0.3", circuito="C1", calibre="12 AWG")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.circuitos == ()
    assert r.puntos[0].circuito_id is None
    assert any("sin tablero" in i.mensaje for i in tipos(r, TipoItem.PENDIENTE))


def test_un_circuito_sin_calibre_lo_deja_pendiente():
    p = plano_base()
    p.bloque("FTE-ELEC", 1, 1, nombre="TABLERO", id="T1", altura="1.5")
    p.bloque("PTO-TOMA", 2, 2, id="T-A", altura="0.3", circuito="C1")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.circuitos[0].calibre == "pendiente"
    assert any("calibre" in i.mensaje for i in tipos(r, TipoItem.PENDIENTE))


def test_calibres_en_conflicto_toman_el_mas_repetido_y_se_aproximan():
    p = plano_base()
    p.bloque("FTE-ELEC", 1, 1, nombre="TABLERO", id="T1", altura="1.5")
    for i, calibre in enumerate(("12 AWG", "12 AWG", "10 AWG")):
        p.bloque(
            "PTO-TOMA", 2 + i * 0.5, 2, id=f"T{i}", altura="0.3", circuito="C1", calibre=calibre
        )
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.circuitos[0].calibre == "12 AWG"
    assert any("calibres distintos" in i.mensaje for i in tipos(r, TipoItem.APROXIMADO))


def test_el_circuito_de_un_punto_que_no_es_electrico_se_ignora():
    p = plano_base()
    p.bloque("PTO-DATOS", 1, 1, id="X", altura="0.3", circuito="C9")
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.circuitos == () and r.puntos[0].circuito_id is None
    assert any("CIRCUITO" in i.mensaje for i in tipos(r, TipoItem.APROXIMADO))


# --- recorridos declarados ----------


def _con_punto_de_datos() -> Plano:
    p = plano_base()
    p.bloque("FTE-DATOS", 0.5, 0.5, nombre="RACK", id="RK")
    p.bloque("PTO-DATOS", 3, 2, id="PD", altura="0.5")
    return p


def test_una_polilinea_rec_se_convierte_en_el_recorrido_declarado_del_punto():
    p = _con_punto_de_datos()
    p.doc.layers.add("REC-DATOS")
    vertices = [(0.5, 0.5, 0), (0.5, 0.5, 2.5), (3, 0.5, 2.5), (3, 2, 2.5), (3, 2, 0.5)]
    poli = p.msp.add_polyline3d(vertices, dxfattribs={"layer": "REC-DATOS"})
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    rec = r.recorridos[0]
    assert (rec.id, rec.modo, rec.punto_id) == (
        f"REC-{poli.dxf.handle}",
        ModoRecorrido.DECLARADO,
        "PD",
    )
    assert [t.superficie for t in rec.tramos] == [
        SuperficieTramo.PARED,
        SuperficieTramo.TECHO,
        SuperficieTramo.TECHO,
        SuperficieTramo.PARED,
    ]
    assert sum(t.longitud for t in rec.tramos) == D("2.5") + D("2.5") + D("1.5") + D("2.0")
    assert [i.tipo for i in r.informe if i.tabla == "esp_recorridos"] == [TipoItem.IMPORTADO]


def test_el_recorrido_se_acepta_con_el_extremo_inicial_en_el_punto():
    p = _con_punto_de_datos()
    p.msp.add_polyline3d(
        [(3, 2, 0.5), (3, 2, 2.5), (0.5, 2, 2.5)], dxfattribs={"layer": "REC-DATOS"}
    )
    assert importar_dxf(p.bytes(), nombre="a.dxf").recorridos[0].punto_id == "PD"


def test_una_rec_que_no_toca_ningun_punto_va_al_informe():
    p = _con_punto_de_datos()
    p.msp.add_polyline3d([(5, 1, 0), (5, 1, 2.5)], dxfattribs={"layer": "REC-DATOS"})
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.recorridos == ()
    assert "ningun punto" in tipos(r, TipoItem.NO_RECONOCIDO)[0].mensaje


def test_una_rec_de_especialidad_desconocida_o_cerrada_va_al_informe():
    p = _con_punto_de_datos()
    p.msp.add_polyline3d([(3, 2, 0.5), (3, 2, 2.5)], dxfattribs={"layer": "REC-GAS"})
    p.msp.add_lwpolyline([(0, 0), (1, 0), (1, 1)], close=True, dxfattribs={"layer": "REC-DATOS"})
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.recorridos == ()
    mensajes = " | ".join(i.mensaje for i in tipos(r, TipoItem.NO_RECONOCIDO))
    assert "GAS" in mensajes and "cerrada" in mensajes


def test_la_rec_plana_se_empareja_por_planta_y_la_electrica_va_al_circuito_del_punto():
    p = plano_base()
    _electrico(p)
    p.msp.add_lwpolyline([(1, 1), (2, 1), (2, 2)], dxfattribs={"layer": "REC-ELECTRICIDAD"})
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    rec = r.recorridos[0]
    assert (rec.circuito_id, rec.punto_id) == ("C1", None)


def test_una_rec_cuyo_extremo_coincide_con_dos_puntos_no_se_adivina():
    p = plano_base()
    p.bloque("PTO-DATOS", 2, 2, id="A", altura="0.3")
    p.bloque("PTO-DATOS", 2, 2, id="B", altura="0.3")
    p.msp.add_polyline3d([(2, 2, 0.3), (2, 2, 2.5)], dxfattribs={"layer": "REC-DATOS"})
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.recorridos == ()
    assert "varios puntos" in tipos(r, TipoItem.NO_RECONOCIDO)[0].mensaje


# --- unidades ----------


def test_sin_insunits_la_importacion_se_detiene_y_pide_la_unidad():
    r = importar_dxf(plano_base(unidades=None).bytes(), nombre="a.dxf")
    assert r.estado is EstadoImportacion.DETENIDA
    assert r.pide_unidad is True
    assert "$INSUNITS" in r.mensaje and "unidades=" in r.mensaje
    assert r.espacio().vacio


def test_detenida_no_lanza_excepcion_ni_lleva_traza():
    r = importar_dxf(plano_base(unidades=None).bytes(), nombre="a.dxf")
    assert "Traceback" not in r.mensaje


def test_la_unidad_indicada_reanuda_la_importacion_y_convierte_a_metros():
    p = Plano(unidades=None)
    p.sala("S", 0, 0, 400, 300)  # centimetros
    p.bloque("PTO-DATOS", 100, 150, id="X", altura="30")
    r = importar_dxf(p.bytes(), nombre="a.dxf", unidades="cm")
    assert r.estado is EstadoImportacion.IMPORTADA and not r.pide_unidad
    assert (r.ambientes[0].largo, r.ambientes[0].ancho) == (D(4), D(3))
    pto = r.puntos[0]
    assert (pto.posicion.x, pto.posicion.y, pto.posicion.z) == (D(1), D("1.5"), D("0.3"))


@pytest.mark.parametrize(
    ("codigo", "factor"),
    [(1, "0.0254"), (2, "0.3048"), (4, "0.001"), (5, "0.01"), (6, "1"), (14, "0.1")],
)
def test_insunits_del_encabezado_convierte_a_metros(codigo, factor):
    p = Plano(unidades=codigo)
    p.sala("S", 0, 0, 100, 50)
    a = importar_dxf(p.bytes(), nombre="a.dxf").ambientes[0]
    assert abs(a.largo - D(100) * D(factor)) < D("0.0001")
    assert abs(a.ancho - D(50) * D(factor)) < D("0.0001")


def test_un_encabezado_sin_la_variable_insunits_tambien_se_detiene():
    p = plano_base()
    p.doc.header.hdrvars.pop("$INSUNITS", None)
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.estado is EstadoImportacion.DETENIDA and r.pide_unidad


def test_la_unidad_del_encabezado_gana_sobre_la_indicada():
    r = importar_dxf(plano_base().bytes(), nombre="a.dxf", unidades="mm")
    assert r.ambientes[1].id == "SALA" and r.ambientes[1].largo == D(4)


def test_una_unidad_indicada_desconocida_se_rechaza_con_mensaje():
    r = importar_dxf(plano_base(unidades=None).bytes(), nombre="a.dxf", unidades="parsecs")
    assert r.estado is EstadoImportacion.RECHAZADA
    assert "parsecs" in r.mensaje and r.pide_unidad is False


def test_un_insunits_que_no_se_puede_convertir_tambien_pide_unidad():
    p = Plano(unidades=8)  # micropulgadas: no soportada
    p.sala("S", 0, 0, 4, 3)
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    assert r.estado is EstadoImportacion.DETENIDA and r.pide_unidad


# --- archivos malos (RNF-12) ----------


@pytest.mark.parametrize(
    "contenido",
    [b"", b"hola mundo\n", b'{"no": "dxf"}', b"\x00\x01\x02\x03", plano_base().bytes()[:3000]],
    ids=["vacio", "texto", "json", "binario", "truncado"],
)
def test_un_archivo_malformado_se_rechaza_con_mensaje_y_sin_traza(contenido):
    r = importar_dxf(contenido, nombre="malo.dxf")
    assert r.estado is EstadoImportacion.RECHAZADA
    assert r.espacio().vacio
    assert "malo.dxf" in r.mensaje and "DXF" in r.mensaje
    assert "Traceback" not in r.mensaje and "\n" not in r.mensaje


def test_un_archivo_de_mas_de_20_mb_se_rechaza_sin_leerlo_de_mas():
    assert LIMITE_BYTES == 20 * 1024 * 1024
    r = importar_dxf(b"0" * (LIMITE_BYTES + 1), nombre="grande.dxf")
    assert r.estado is EstadoImportacion.RECHAZADA
    assert "20 MB" in r.mensaje


def test_un_archivo_justo_en_el_limite_no_se_rechaza_por_tamano():
    r = importar_dxf(b"0" * LIMITE_BYTES, nombre="limite.dxf")
    assert "20 MB" not in r.mensaje  # se rechaza, pero por malformado


def test_una_ruta_de_mas_de_20_mb_se_rechaza_por_su_tamano(tmp_path):
    ruta = tmp_path / "grande.dxf"
    ruta.write_bytes(b"0" * (LIMITE_BYTES + 1))
    r = importar_dxf(ruta)
    assert r.estado is EstadoImportacion.RECHAZADA and "20 MB" in r.mensaje


def test_una_ruta_que_no_existe_se_rechaza_con_mensaje(tmp_path):
    r = importar_dxf(tmp_path / "no_esta.dxf")
    assert r.estado is EstadoImportacion.RECHAZADA and "no_esta.dxf" in r.mensaje


def test_la_ruta_y_los_bytes_dan_el_mismo_resultado(tmp_path):
    p = plano_base()
    ruta = tmp_path / "casa.dxf"
    ruta.write_bytes(p.bytes())
    assert importar_dxf(ruta) == importar_dxf(p.bytes(), nombre="casa.dxf")
    assert importar_dxf(str(ruta)) == importar_dxf(ruta)


def test_el_nombre_por_defecto_de_los_bytes_es_plano_dxf():
    r = importar_dxf(plano_base().bytes())
    assert dict(r.origenes[0].referencia)["archivo"] == "plano.dxf"


def test_un_dxf_con_acentos_en_el_nombre_y_el_texto_los_conserva(tmp_path):
    p = plano_base()
    p.sala("BAÑO", 10, 0, 12, 2)
    ruta = tmp_path / "baño.dxf"
    p.doc.saveas(ruta)
    assert "BAÑO" in {a.id for a in importar_dxf(ruta).ambientes}


def test_importar_dos_veces_da_lo_mismo():
    contenido = plano_base().bytes()
    assert importar_dxf(contenido, nombre="a.dxf") == importar_dxf(contenido, nombre="a.dxf")


# --- reimportacion por handle ----------


def test_reimportar_el_plano_editado_actualiza_agrega_y_marca_lo_que_desaparecio(tmp_path):
    p = plano_base()
    p.bloque("PTO-DATOS", 1, 1, id="MOVIDO", altura="0.3")
    p.bloque("PTO-DATOS", 2, 1, id="BORRADO", altura="0.3")
    primero, _ = fusionar(Espacio(), importar_dxf(p.bytes(), nombre="casa.dxf"))

    # el CAD guarda y reabre el archivo: los handles se conservan; luego se edita
    ruta = tmp_path / "casa.dxf"
    p.doc.saveas(ruta)
    p.doc = ezdxf.readfile(ruta)
    p.msp = p.doc.modelspace()
    for e in list(p.msp.query("INSERT")):
        ident = {a.dxf.tag: a.dxf.text for a in e.attribs}.get("ID")
        if ident == "MOVIDO":
            e.dxf.insert = (1, 1.75, 0)
        if ident == "BORRADO":
            p.msp.delete_entity(e)
    p.bloque("PTO-DATOS", 3, 2, id="NUEVO", altura="0.3")

    espacio, informe = fusionar(primero, importar_dxf(p.bytes(), nombre="casa.dxf"))
    por_id = {x.id: x for x in espacio.puntos}
    assert set(por_id) == {"MOVIDO", "BORRADO", "NUEVO"}  # el borrado se marca, no se borra
    assert por_id["MOVIDO"].posicion.y == D("1.75")
    assert [i.fila for i in informe if i.tipo is TipoItem.DESAPARECIDO] == ["BORRADO"]
    marca = dict(
        next(o for o in espacio.origenes if o.id == por_id["BORRADO"].origen_id).referencia
    )
    assert marca["importacion"] == "desaparecida"


# --- altura de un punto sin atributo ALTURA: cota z de la insercion ----------


def test_un_bloque_sin_altura_con_cota_z_usa_la_cota_y_marca_la_altura_pendiente():
    p = plano_base()
    p.bloque("PTO-DATOS", 1, 1, id="X", z=0.45)
    r = importar_dxf(p.bytes(), nombre="a.dxf")
    pto = r.puntos[0]
    assert pto.posicion.z == D("0.45")  # la z de la insercion
    assert pto.superficie is SuperficiePunto.PARED  # z > 0
    assert ALTURA_PENDIENTE in pto.especificaciones
    assert any("sin atributo ALTURA" in i.mensaje for i in tipos(r, TipoItem.PENDIENTE))


def test_un_bloque_sin_altura_y_con_z_cero_queda_en_el_piso_y_tambien_pendiente():
    p = plano_base()
    p.bloque("PTO-DRENAJE", 1, 1, id="X", z=0.0)
    pto = importar_dxf(p.bytes(), nombre="a.dxf").puntos[0]
    assert pto.posicion.z == D(0)
    assert pto.superficie is SuperficiePunto.PISO
    assert ALTURA_PENDIENTE in pto.especificaciones


def test_el_atributo_altura_gana_sobre_la_cota_z_de_la_insercion():
    p = plano_base()
    p.bloque("PTO-DATOS", 1, 1, id="X", z=0.45, altura="0.3")
    pto = importar_dxf(p.bytes(), nombre="a.dxf").puntos[0]
    assert pto.posicion.z == D("0.3") and ALTURA_PENDIENTE not in pto.especificaciones


# --- RS-15: frontera del alto provisional (falso positivo declarado) ----------


def _r8_de_altura(espacio) -> list[str]:
    return [
        h.origen_ids[0]
        for h in OrigenDeLaMedida(espacio).evaluar(VACIO)
        if "altura pendiente" in h.descripcion and h.origen_ids[0].startswith("esp_ambientes")
    ]


def _con_alto(resultado, alto: Decimal):
    return replace(
        resultado, ambientes=tuple(replace(a, alto=alto) for a in resultado.ambientes)
    ).espacio()


def test_rs15_alto_exactamente_2_5_con_la_marca_puesta_sigue_en_advertencia():
    """Falso positivo conocido: un alto REAL de 2,5 m con la marca `altura=pendiente` coincide con
    el provisional y R8 sigue avisando hasta `cargar_alturas` (que quita la marca)."""
    r = importar_dxf(plano_base().bytes(), nombre="a.dxf")
    assert ALTO_PROVISIONAL == D("2.5")
    assert _r8_de_altura(_con_alto(r, D("2.5"))) == ["esp_ambientes:COCINA", "esp_ambientes:SALA"]


def test_rs15_alto_distinto_de_2_5_ya_no_avisa_aunque_la_marca_siga():
    r = importar_dxf(plano_base().bytes(), nombre="a.dxf")
    assert _r8_de_altura(_con_alto(r, D("2.501"))) == []
    assert _r8_de_altura(_con_alto(r, D("2.499"))) == []


def test_rs15_tras_cargar_alturas_con_2_5_se_quita_la_marca_y_no_avisa():
    r = importar_dxf(plano_base().bytes(), nombre="a.dxf")
    cargado = cargar_alturas(r, {"SALA": D("2.5"), "COCINA": D("2.5")})
    assert _r8_de_altura(cargado.espacio()) == []
    assert not [
        i for i in cargado.informe if i.tipo is TipoItem.PENDIENTE and i.tabla == "esp_ambientes"
    ]


# --- RNF-12: tope de entidades tras abrir el archivo ----------


def test_el_tope_por_defecto_es_una_constante_con_nombre():
    assert MAX_ENTIDADES_DXF == 100_000


def test_un_dxf_con_mas_entidades_que_el_tope_se_rechaza_sin_traza():
    p = plano_base()  # 2 polilineas + 2 textos = 4 entidades
    for i in range(7):
        p.bloque("PTO-DATOS", 1, 1, id=f"P{i}", altura="0.3")
    r = importar_dxf(p.bytes(), nombre="denso.dxf", max_entidades=10)  # 11 entidades > 10
    assert r.estado is EstadoImportacion.RECHAZADA
    assert r.espacio().vacio
    assert "denso.dxf" in r.mensaje and "11" in r.mensaje and "10" in r.mensaje
    assert "tope" in r.mensaje
    assert "Traceback" not in r.mensaje and "\n" not in r.mensaje


def test_un_dxf_con_exactamente_el_tope_de_entidades_se_importa():
    p = plano_base()  # 4 entidades
    assert importar_dxf(p.bytes(), nombre="a.dxf", max_entidades=4).estado is (
        EstadoImportacion.IMPORTADA
    )
    assert importar_dxf(p.bytes(), nombre="a.dxf", max_entidades=3).estado is (
        EstadoImportacion.RECHAZADA
    )


def test_el_tope_tambien_rige_para_una_ruta(tmp_path):
    ruta = tmp_path / "a.dxf"
    ruta.write_bytes(plano_base().bytes())
    assert importar_dxf(ruta, max_entidades=2).estado is EstadoImportacion.RECHAZADA


def test_el_tope_por_defecto_no_rechaza_el_dxf_de_of001():
    assert importar_dxf(OF001).estado is EstadoImportacion.IMPORTADA
