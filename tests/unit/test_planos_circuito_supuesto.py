"""RS-17 (revision de SF5): un circuito importado con conductores y puntos SUPUESTOS no puede quedar
marcado solo en el informe de importacion. La marca es persistente y la lee R8: mientras el circuito
conserve los valores supuestos (conductores 1-1-1, 6 puntos maximos; constantes SF5-1 y SF5-2) R8 da
una ADVERTENCIA; cuando el usuario los declara, deja de avisar.

Oraculos: literales de lo dibujado (dos circuitos, C1 y C2) y de la memoria de OF-001 (`of001.md`:
dos circuitos), no la salida del importador.
"""

from __future__ import annotations

import datetime
import io
from decimal import Decimal
from pathlib import Path

import ezdxf
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from adapters.espacio import (
    Espacio,
    TipoOrigen,
    cargar_espacio,
    crear_esquema_espacio,
    guardar_espacio,
)
from adapters.espacio.planos.dxf import importar_dxf
from adapters.espacio.planos.informe import (
    TipoItem,
    cargar_alturas,
    declarar_circuito,
    declarar_circuitos,
    fusionar,
)
from adapters.espacio.reglas import (
    CoherenciaEspacial,
    LimitesDeEspecialidad,
    OrigenDeLaMedida,
)
from core.contracts import Severidad
from core.contracts.presupuesto import Presupuesto

D = Decimal
RAIZ = Path(__file__).resolve().parents[2]
DXF_OF001 = RAIZ / "tests" / "fixtures" / "planos" / "of001.dxf"
VACIO = Presupuesto(codigo="X", fecha=datetime.date(2026, 1, 1), moneda="USD", partidas=())
TEXTO = "circuito importado con conductores y puntos supuestos"


def _plano() -> bytes:
    """Sala de 6 x 3 con un tablero y tres puntos en dos circuitos (C1: T-A, T-B; C2: L-A)."""
    doc = ezdxf.new("R2010")
    doc.units = 6
    msp = doc.modelspace()
    bloque = doc.blocks.new("PUNTO")
    bloque.add_circle((0, 0), 0.05)
    msp.add_lwpolyline(
        [(0, 0), (6, 0), (6, 3), (0, 3)], close=True, dxfattribs={"layer": "AMBIENTES"}
    )
    msp.add_text("SALA", dxfattribs={"layer": "AMBIENTES", "insert": (3, 1.5), "height": 0.1})

    def poner(capa, x, y, **atributos):
        ref = msp.add_blockref("PUNTO", (x, y, 0), dxfattribs={"layer": capa})
        for tag, valor in atributos.items():
            ref.add_attrib(tag.upper(), valor, (x, y), dxfattribs={"layer": capa})

    poner("FTE-ELEC", 1, 1, id="T1", altura="1.5")
    poner("PTO-TOMA", 2, 2, id="T-A", altura="0.3", circuito="C1", calibre="12 AWG")
    poner("PTO-TOMA", 3, 2, id="T-B", altura="0.3", circuito="C1", calibre="12 AWG")
    poner("PTO-LUZ", 3, 1, id="L-A", altura="2.4", circuito="C2", calibre="14 AWG")
    destino = io.StringIO()
    doc.write(destino)
    return destino.getvalue().encode("utf-8")


def _r8(espacio: Espacio):
    return OrigenDeLaMedida(espacio).evaluar(VACIO)


def _de_circuitos(espacio: Espacio):
    return sorted(h.origen_ids[0] for h in _r8(espacio) if h.origen_ids[0].startswith("esp_circ"))


@pytest.fixture(scope="module")
def importado():
    return importar_dxf(_plano(), nombre="a.dxf")


# --- la marca persistente ----------


def test_el_circuito_importado_lleva_un_origen_supuesto_por_circuito(importado):
    supuestos = [o for o in importado.origenes if o.tipo is TipoOrigen.SUPUESTO]
    assert sorted(dict(o.referencia)["circuito"] for o in supuestos) == ["C1", "C2"]
    assert all(not o.incompleto for o in supuestos)  # trae su «motivo»
    assert len({o.id for o in importado.origenes}) == len(importado.origenes)


def test_r8_da_advertencia_por_cada_circuito_con_valores_supuestos(importado):
    hallazgos = [h for h in _r8(importado.espacio()) if h.origen_ids[0].startswith("esp_circ")]
    assert [(h.regla, h.severidad, h.origen_ids) for h in hallazgos] == [
        ("R8", Severidad.ADVERTENCIA, ("esp_circuitos:C1",)),
        ("R8", Severidad.ADVERTENCIA, ("esp_circuitos:C2",)),
    ]
    assert all(TEXTO in h.descripcion for h in hallazgos)
    assert all("SF5-1" in h.descripcion and "SF5-2" in h.descripcion for h in hallazgos)


def test_el_hallazgo_es_determinista(importado):
    assert _r8(importado.espacio()) == _r8(importado.espacio())


def test_una_hoja_hecha_a_mano_no_recibe_la_advertencia(importado):
    """El circuito sin marca de supuesto (hoja manual) no avisa aunque tenga 1-1-1 y 6."""
    limpio = Espacio(
        origenes=tuple(o for o in importado.origenes if o.tipo is not TipoOrigen.SUPUESTO),
        ambientes=importado.ambientes,
        fuentes=importado.fuentes,
        circuitos=importado.circuitos,
        puntos=importado.puntos,
    )
    assert _de_circuitos(limpio) == []


def test_otros_formatos_y_filas_no_cambian(importado):
    """Las filas de R8 distintas de los circuitos son las de antes: solo se agregan dos."""
    quitando = [h for h in _r8(importado.espacio()) if not h.origen_ids[0].startswith("esp_circ")]
    assert [h.origen_ids[0] for h in quitando] == ["esp_ambientes:SALA"]  # solo altura pendiente


# --- declarar los valores ----------


def test_declarar_valores_propios_quita_la_advertencia_de_ese_circuito(importado):
    r = declarar_circuitos(importado, {"C1": ((2, 1, 1), 4)})
    c1 = next(c for c in r.circuitos if c.id == "C1")
    assert (c1.conductores, c1.puntos_maximos) == ((2, 1, 1), 4)
    assert _de_circuitos(r.espacio()) == ["esp_circuitos:C2"]  # C2 sigue supuesto
    assert not [
        i for i in r.informe if i.tabla == "esp_circuitos" and i.fila == "C1" and "supuest" in i.mensaje
    ]
    assert [i.fila for i in r.informe if i.tabla == "esp_circuitos" and "supuest" in i.mensaje] == [
        "C2"
    ]


def test_declarar_no_muta_el_resultado_original(importado):
    declarar_circuitos(importado, {"C1": ((2, 1, 1), 4)})
    assert _de_circuitos(importado.espacio()) == ["esp_circuitos:C1", "esp_circuitos:C2"]


def test_declarar_un_circuito_que_no_existe_se_ignora(importado):
    assert declarar_circuitos(importado, {"X9": ((1, 1, 1), 6)}) == importado


def test_confirmar_los_mismos_valores_tambien_quita_la_advertencia(importado):
    """Declarar es una decision del usuario: confirmar 1-1-1 y 6 retira la marca aunque coincidan."""
    espacio = declarar_circuito(importado.espacio(), "C1")
    assert _de_circuitos(espacio) == ["esp_circuitos:C2"]
    assert next(c for c in espacio.circuitos if c.id == "C1").puntos_maximos == 6


def test_declarar_en_el_espacio_cambia_solo_lo_pedido(importado):
    espacio = declarar_circuito(importado.espacio(), "C2", puntos_maximos=3)
    c2 = next(c for c in espacio.circuitos if c.id == "C2")
    assert (c2.conductores, c2.puntos_maximos) == ((1, 1, 1), 3)
    assert _de_circuitos(espacio) == ["esp_circuitos:C1"]
    with pytest.raises(KeyError):
        declarar_circuito(importado.espacio(), "X9")


def test_editar_los_valores_sin_declarar_tambien_apaga_la_advertencia(importado):
    """Si la hoja cambia los valores (otro camino de edicion), la marca ya no describe al circuito."""
    from dataclasses import replace

    espacio = importado.espacio()
    editados = tuple(
        replace(c, conductores=(2, 1, 1)) if c.id == "C1" else c for c in espacio.circuitos
    )
    cambiado = replace(espacio, circuitos=editados)
    assert _de_circuitos(cambiado) == ["esp_circuitos:C2"]
    otro = tuple(replace(c, puntos_maximos=8) if c.id == "C2" else c for c in cambiado.circuitos)
    assert _de_circuitos(replace(cambiado, circuitos=otro)) == []


# --- persistencia y reimportacion ----------


def test_la_marca_sobrevive_a_guardar_y_cargar(tmp_path, importado):
    espacio, _ = fusionar(Espacio(), importado)
    motor = create_engine(f"sqlite:///{tmp_path / 'e.db'}")
    crear_esquema_espacio(motor)
    with Session(motor) as sesion:
        guardar_espacio(sesion, 1, espacio)
        sesion.commit()
    with Session(motor) as sesion:
        recargado = cargar_espacio(sesion, 1)
    motor.dispose()
    assert recargado == espacio
    assert _de_circuitos(recargado) == ["esp_circuitos:C1", "esp_circuitos:C2"]


def test_fusionar_en_una_hoja_vacia_trae_la_marca(importado):
    espacio, _ = fusionar(Espacio(), importado)
    assert _de_circuitos(espacio) == ["esp_circuitos:C1", "esp_circuitos:C2"]


def test_reimportar_no_vuelve_a_marcar_un_circuito_ya_declarado(importado):
    espacio, _ = fusionar(Espacio(), importado)
    declarado = declarar_circuito(espacio, "C1", conductores=(2, 1, 1), puntos_maximos=4)
    de_nuevo, _ = fusionar(declarado, importar_dxf(_plano(), nombre="a.dxf"))
    assert _de_circuitos(de_nuevo) == ["esp_circuitos:C2"]
    c1 = next(c for c in de_nuevo.circuitos if c.id == "C1")
    assert (c1.conductores, c1.puntos_maximos) == ((2, 1, 1), 4)  # el existente manda


def test_un_circuito_nuevo_de_la_reimportacion_trae_su_marca(importado):
    espacio, _ = fusionar(Espacio(), importado)
    sin_c2 = declarar_circuito(espacio, "C2")  # se declara C2; solo C1 queda supuesto
    de_nuevo, _ = fusionar(sin_c2, importar_dxf(_plano(), nombre="a.dxf"))
    assert _de_circuitos(de_nuevo) == ["esp_circuitos:C1"]


def test_el_informe_de_importacion_sigue_marcando_los_supuestos(importado):
    aprox = [i for i in importado.informe if i.tipo is TipoItem.APROXIMADO and i.tabla == "esp_circuitos"]
    assert sorted(i.fila for i in aprox) == ["C1", "C2"]


# --- OF-001 por la via del DXF: conjunto exacto ----------


@pytest.fixture(scope="module")
def of001_dxf():
    base = importar_dxf(DXF_OF001)
    return cargar_alturas(base, {a.id: D("2.5") for a in base.ambientes})  # 2,5 m: of001.md


def test_of001_por_dxf_conjunto_exacto_de_hallazgos(of001_dxf):
    """Con las alturas cargadas, el DXF de OF-001 solo deja las dos ADVERTENCIAS de los dos
    circuitos de la memoria (C1 y C2); R9 y R10 no dan nada. La hoja manual no las tiene: es la
    diferencia documentada de la via DXF (el DXF no trae conductores ni maximo de puntos)."""
    espacio = of001_dxf.espacio()
    assert [(h.regla, h.severidad, h.origen_ids) for h in _r8(espacio)] == [
        ("R8", Severidad.ADVERTENCIA, ("esp_circuitos:C1",)),
        ("R8", Severidad.ADVERTENCIA, ("esp_circuitos:C2",)),
    ]
    assert CoherenciaEspacial(espacio).evaluar(VACIO) == []
    assert LimitesDeEspecialidad(espacio).evaluar(VACIO) == []


def test_of001_por_dxf_sin_advertencia_tras_declarar_los_dos_circuitos(of001_dxf):
    declarado = declarar_circuitos(
        of001_dxf, {"C1": ((1, 1, 1), 6), "C2": ((1, 1, 1), 6)}
    )
    assert _r8(declarado.espacio()) == []
