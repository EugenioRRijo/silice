"""Importar plano en la hoja (integracion de SF3 y SF5, RF-50 y RF-51): la logica de `ui.hoja`.

El plano crea filas en el BORRADOR de la hoja con su informe; nunca salta la hoja ni la auditoria
(DA-SF-6). Aqui se prueba la logica pura (sin Streamlit): leer el archivo, pedir la unidad, el
informe, cargar alturas, declarar circuitos supuestos y fusionar. El oraculo de las cantidades es la
hoja manual de OF-001 (`tests/fixtures/espacio_of001.py`), con la tolerancia de +-0,001 m.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import ezdxf
import pytest

from adapters.espacio import Espacio
from adapters.espacio.planos import EstadoImportacion, TipoItem
from tests.fixtures.espacio_of001 import espacio_of001
from ui import hoja

D = Decimal
RAIZ = Path(__file__).resolve().parents[2]
DXF = RAIZ / "tests" / "fixtures" / "planos" / "of001.dxf"
TOLERANCIA = D("0.001")


class _Subida:
    def __init__(self, name: str, datos: bytes) -> None:
        self.name = name
        self._datos = datos

    def getvalue(self) -> bytes:
        return self._datos


def _borrador(espacio: Espacio | None = None) -> hoja.Borrador:
    return hoja.Borrador(fecha=date(2026, 10, 5), espacio=espacio or Espacio())


def _firma(items):
    return sorted((i.codigo_partida, i.unidad, i.cantidad) for i in items)


def _altura_de_la_memoria() -> dict[str, str]:
    return {a.id: "2,50" for a in hoja.leer_plano(DXF).ambientes}


# --- formato y lectura ---------------------------------------------------------------------------


def test_el_formato_se_deduce_de_la_extension_sin_distinguir_mayusculas():
    assert hoja.formato_de_plano("planta.dxf") == "dxf"
    assert hoja.formato_de_plano("Torre.IFC") == "ifc"
    assert hoja.formato_de_plano("a.b.Dxf") == "dxf"


@pytest.mark.parametrize("nombre", ["plano.pdf", "plano", "plano.dwg", "dxf", ""])
def test_un_formato_que_no_es_dxf_ni_ifc_se_rechaza_diciendo_cuales_sirven(nombre):
    with pytest.raises(hoja.HojaInvalida) as error:
        hoja.formato_de_plano(nombre)
    assert "DXF" in str(error.value) and "IFC" in str(error.value)


def test_leer_el_dxf_de_of001_devuelve_la_importacion_con_su_informe():
    resultado = hoja.leer_plano(DXF)
    assert resultado.estado is EstadoImportacion.IMPORTADA
    assert resultado.pide_unidad is False
    assert resultado.filas["esp_ambientes"] == 6
    assert resultado.filas["esp_puntos"] == 21


def test_leer_un_dxf_sin_unidad_se_detiene_y_pide_la_unidad_y_se_reanuda_con_ella(tmp_path):
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 0
    ruta = tmp_path / "sin_unidad.dxf"
    doc.saveas(ruta)

    detenido = hoja.leer_plano(ruta)
    assert detenido.estado is EstadoImportacion.DETENIDA and detenido.pide_unidad is True

    reanudado = hoja.leer_plano(ruta, unidades="cm")
    assert reanudado.estado is EstadoImportacion.IMPORTADA


def test_leer_un_archivo_roto_no_lanza_y_dice_que_no_se_pudo_leer(tmp_path):
    ruta = tmp_path / "roto.dxf"
    ruta.write_bytes(b"esto no es un dibujo")
    resultado = hoja.leer_plano(ruta)
    assert resultado.estado is EstadoImportacion.RECHAZADA
    assert resultado.mensaje


@pytest.mark.parametrize(
    ("nombre", "modulo", "comando"),
    [
        ("a.dxf", "adapters.espacio.planos.dxf", "uv sync --extra planos"),
        ("a.ifc", "adapters.espacio.planos.ifc", "uv sync --extra civil"),
    ],
)
def test_si_falta_el_extra_el_mensaje_dice_el_comando_para_instalarlo(
    monkeypatch, tmp_path, nombre, modulo, comando
):
    monkeypatch.setitem(__import__("sys").modules, modulo, None)  # simula el extra ausente
    ruta = tmp_path / nombre
    ruta.write_bytes(b"x")
    with pytest.raises(hoja.HojaInvalida) as error:
        hoja.leer_plano(ruta)
    assert comando in str(error.value)


def test_subir_el_plano_lo_guarda_con_nombre_seguro_y_lo_lee(tmp_path):
    subida = _Subida("..\\..\\of001.dxf", DXF.read_bytes())
    ruta, resultado = hoja.subir_plano(subida, tmp_path)
    assert ruta.parent == tmp_path and ruta.name == "of001.dxf"
    assert resultado.estado is EstadoImportacion.IMPORTADA


def test_subir_un_formato_ajeno_no_escribe_nada(tmp_path):
    with pytest.raises(hoja.HojaInvalida):
        hoja.subir_plano(_Subida("lista.pdf", b"%PDF"), tmp_path)
    assert list(tmp_path.iterdir()) == []


# --- informe ------------------------------------------------------------------------------------


def test_el_resumen_cuenta_importado_no_reconocido_aproximado_y_pendiente():
    resumen = hoja.resumen_de_importacion(hoja.leer_plano(DXF))
    assert resumen == [
        ("Importado", 33),
        ("No reconocido", 0),
        ("Aproximado", 9),
        ("Pendiente", 6),
    ]


def test_el_resumen_de_una_fusion_cuenta_el_informe_de_la_fusion():
    base = hoja.leer_plano(DXF)
    _, informe = hoja.fusionar_plano(_borrador(), base)
    resumen = hoja.resumen_de_importacion(base, informe)
    assert [n for n, _ in resumen] == ["Importado", "No reconocido", "Aproximado", "Pendiente"]
    assert sum(c for _, c in resumen) == len(informe)


def test_las_filas_del_informe_hablan_en_espanol_y_no_traen_siglas_internas():
    filas = hoja.filas_del_informe(hoja.leer_plano(DXF).informe)
    assert filas and set(filas[0]) == {"Tipo", "En el plano", "Fila de la hoja", "Qué pasó"}
    textos = " ".join(" ".join(f.values()) for f in filas)
    for interno in ("SF5", "DA-SF", "esp_"):
        assert interno not in textos
    assert {f["Tipo"] for f in filas} == {"Importado", "Aproximado", "Pendiente"}


# --- alturas pendientes -------------------------------------------------------------------------


def test_las_alturas_pendientes_son_los_seis_ambientes_del_plano():
    pendientes = hoja.alturas_pendientes(hoja.leer_plano(DXF))
    assert sorted(i for i, _ in pendientes) == sorted(
        ["BAN-01", "COC-01", "REC-01", "CT-01", "ZA", "ZB"]
    )
    assert [i for i, _ in pendientes] == [a.id for a in hoja.leer_plano(DXF).ambientes]


def test_cargar_las_alturas_acepta_coma_decimal_y_quita_lo_pendiente():
    resultado = hoja.cargar_alturas_desde_texto(hoja.leer_plano(DXF), _altura_de_la_memoria())
    assert hoja.alturas_pendientes(resultado) == []
    assert {a.alto for a in resultado.ambientes} == {D("2.5")}
    assert resultado.conteos[TipoItem.PENDIENTE] == 0


def test_una_altura_en_blanco_se_deja_pendiente_y_las_demas_se_cargan():
    textos = {**_altura_de_la_memoria(), "ZB": "  "}
    resultado = hoja.cargar_alturas_desde_texto(hoja.leer_plano(DXF), textos)
    assert [i for i, _ in hoja.alturas_pendientes(resultado)] == ["ZB"]


@pytest.mark.parametrize("texto", ["abc", "0", "-2,5", "2,5 m", "NaN", "Infinity"])
def test_una_altura_invalida_se_rechaza_diciendo_cual_ambiente(texto):
    with pytest.raises(hoja.HojaInvalida) as error:
        hoja.cargar_alturas_desde_texto(hoja.leer_plano(DXF), {"ZA": texto})
    assert "ZA" in str(error.value)


def test_el_limite_de_altura_es_razonable_en_metros():
    with pytest.raises(hoja.HojaInvalida):
        hoja.cargar_alturas_desde_texto(hoja.leer_plano(DXF), {"ZA": "251"})
    ok = hoja.cargar_alturas_desde_texto(hoja.leer_plano(DXF), {"ZA": "250"})
    assert next(a.alto for a in ok.ambientes if a.id == "ZA") == D("250")


# --- circuitos supuestos ------------------------------------------------------------------------


def test_los_circuitos_que_entraron_con_valores_supuestos_se_listan():
    supuestos = hoja.circuitos_supuestos(hoja.leer_plano(DXF))
    assert [c.id for c in supuestos] == ["C1", "C2"]
    assert all(c.conductores == (1, 1, 1) and c.puntos_maximos == 6 for c in supuestos)


def test_declarar_un_circuito_fija_sus_valores_y_lo_saca_de_los_supuestos():
    resultado = hoja.declarar_circuitos_desde_texto(
        hoja.leer_plano(DXF), {"C1": ("1", "1", "1", "8")}
    )
    assert [c.id for c in hoja.circuitos_supuestos(resultado)] == ["C2"]
    c1 = next(c for c in resultado.circuitos if c.id == "C1")
    assert c1.conductores == (1, 1, 1) and c1.puntos_maximos == 8


@pytest.mark.parametrize(
    "valores",
    [("x", "1", "1", "6"), ("-1", "1", "1", "6"), ("1", "1", "1", "0"), ("1", "1.5", "1", "6")],
)
def test_un_circuito_invalido_se_rechaza_diciendo_cual(valores):
    with pytest.raises(hoja.HojaInvalida) as error:
        hoja.declarar_circuitos_desde_texto(hoja.leer_plano(DXF), {"C2": valores})
    assert "C2" in str(error.value)


# --- fusionar: el plano entra al BORRADOR, no a la version ----------------------------------------


def _declarado():
    r = hoja.cargar_alturas_desde_texto(hoja.leer_plano(DXF), _altura_de_la_memoria())
    oficina = espacio_of001()
    return hoja.declarar_circuitos_desde_texto(
        r,
        {
            c.id: (
                str(c.conductores[0]),
                str(c.conductores[1]),
                str(c.conductores[2]),
                str(c.puntos_maximos),
            )
            for c in oficina.circuitos
        },
    )


def test_fusionar_en_un_borrador_vacio_da_las_mismas_cantidades_que_la_hoja_manual():
    borrador, informe = hoja.fusionar_plano(_borrador(), _declarado())
    assert informe  # el informe de la importacion viaja con la fusion
    derivados = hoja.items_del_borrador(borrador.espacio, hoja.TODAS)
    manual = hoja.items_del_borrador(espacio_of001(), hoja.TODAS)
    assert [(i.codigo_partida, i.unidad) for i in _sorted(derivados)] == [
        (i.codigo_partida, i.unidad) for i in _sorted(manual)
    ]
    for a, b in zip(_sorted(derivados), _sorted(manual), strict=True):
        assert abs(a.cantidad - b.cantidad) <= TOLERANCIA, a.codigo_partida


def _sorted(items):
    return sorted(items, key=lambda i: (i.codigo_partida, i.unidad, i.cantidad))


def test_fusionar_no_cambia_el_borrador_original_ni_toca_lo_que_no_es_del_espacio():
    original = _borrador()
    nuevo, _ = hoja.fusionar_plano(original, _declarado())
    assert original.espacio == Espacio()  # inmutable
    assert nuevo.fecha == original.fecha and nuevo.cantidades == original.cantidades
    assert nuevo.composiciones == original.composiciones and nuevo.plan == original.plan


def test_fusionar_pasa_por_la_auditoria_los_circuitos_supuestos_los_marca_la_regla_8():
    """DA-SF-6: el plano no salta la auditoria. Sin declarar los circuitos, R8 los advierte."""
    sin_declarar = hoja.cargar_alturas_desde_texto(hoja.leer_plano(DXF), _altura_de_la_memoria())
    borrador, _ = hoja.fusionar_plano(_borrador(), sin_declarar)
    informe = hoja.elaborar_borrador(borrador).elaboracion.informe
    r8 = [h for h in informe.hallazgos if h.regla == "R8"]
    assert any("C1" in h.descripcion for h in r8) and any("C2" in h.descripcion for h in r8)

    borrador2, _ = hoja.fusionar_plano(_borrador(), _declarado())
    informe2 = hoja.elaborar_borrador(borrador2).elaboracion.informe
    assert not [h for h in informe2.hallazgos if h.regla == "R8" and "circuito" in h.descripcion]


def test_fusionar_una_importacion_detenida_o_rechazada_se_rechaza_con_su_motivo(tmp_path):
    ruta = tmp_path / "roto.dxf"
    ruta.write_bytes(b"nada")
    with pytest.raises(hoja.HojaInvalida) as error:
        hoja.fusionar_plano(_borrador(), hoja.leer_plano(ruta))
    assert "roto.dxf" in str(error.value)


def test_reimportar_el_mismo_plano_no_duplica_filas():
    primero, _ = hoja.fusionar_plano(_borrador(), _declarado())
    segundo, _ = hoja.fusionar_plano(primero, _declarado())
    assert len(segundo.espacio.ambientes) == len(primero.espacio.ambientes) == 6
    assert len(segundo.espacio.puntos) == len(primero.espacio.puntos) == 21
