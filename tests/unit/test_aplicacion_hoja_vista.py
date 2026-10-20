"""La base de las vistas de la hoja (T10, 3b-1): montos, version por omision, resumen y R17.

Oraculos a mano: la regla de la version por omision es la de la pagina clasica (P:417-421: las no
descartadas, o todas si todas lo estan; la vigente, o la ultima); los montos, `formatear_decimal`
a dos decimales (NORMAS.md §2) y el exacto con `format(x, "f")`; el resumen de OF-001 usa los
literales de la memoria (total 2 703,86 USD).
"""

from __future__ import annotations

import dataclasses
import shutil
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.espacio.conexion import con_conexion
from adapters.espacio.modelo import (
    Ambiente,
    Coord,
    Espacio,
    Especialidad,
    Punto,
    SuperficiePunto,
    TipoPunto,
)
from adapters.espacio.origen import OrigenMedida, TipoOrigen
from aplicacion import hoja, hoja_vista
from aplicacion.hoja_borradores import Registro
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts import Severidad
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from ui import hoja as clasica

D = Decimal
HOY = date(2026, 10, 19)


def _fila(codigo: str, *, vigente=False, descartada=False) -> hoja.FilaVersion:
    return hoja.FilaVersion(codigo, HOY, "", "", vigente, descartada, 0)


@pytest.mark.parametrize(
    ("valor", "texto", "exacto"),
    [
        (D("2703.856"), "2703.86", "2703.856"),
        (D("0.005"), "0.01", "0.005"),
        (D("3"), "3.00", "3"),
        (D("1E+1"), "10.00", "10"),
        (
            D("123456789012345678901234567890.1234"),
            "123456789012345678901234567890.12",
            "123456789012345678901234567890.1234",
        ),
    ],
)
def test_un_monto_es_texto_a_dos_decimales_y_exacto_sin_notacion_cientifica(valor, texto, exacto):
    m = hoja_vista.monto(valor)
    assert (m.texto, m.exacto) == (texto, exacto)


def test_version_por_omision_es_la_vigente_entre_las_no_descartadas():
    filas = [_fila("001"), _fila("002"), _fila("003", vigente=True)]
    assert hoja_vista.version_por_omision(filas) == "003"


def test_con_la_ultima_descartada_la_vigente_pasa_a_ser_otra():
    filas = [_fila("001"), _fila("002", vigente=True), _fila("003", descartada=True)]
    assert hoja_vista.version_por_omision(filas) == "002"


def test_con_todas_descartadas_se_ofrece_la_ultima():
    filas = [_fila("001", descartada=True), _fila("002", descartada=True)]
    assert hoja_vista.version_por_omision(filas) == "002"


def test_sin_versiones_no_hay_version_por_omision():
    assert hoja_vista.version_por_omision([]) is None


def test_sin_vigente_entre_las_no_descartadas_se_toma_la_ultima_no_descartada():
    filas = [_fila("001"), _fila("002")]
    assert hoja_vista.version_por_omision(filas) == "002"


def test_mensaje_de_la_instantanea_solo_si_se_creo_alguna():
    assert hoja_vista.mensaje_instantanea(0) is None
    assert hoja_vista.mensaje_instantanea(3) == (
        "Se creó y registró la instantánea de las composiciones de esta versión (3 partidas): "
        "sus APU ya no cambian si cambia el catálogo."
    )


@pytest.fixture(scope="module")
def _of001(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("vista_hoja")
    plantilla = plantilla_of001(carpeta / "of001.db")
    copia = carpeta / "copia.db"
    shutil.copyfile(plantilla, copia)
    motor = crear_motor(f"sqlite:///{Path(copia).as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            abierta = hoja.abrir_version(
                sesion, Catalogo(sesion), NOMBRE_OF001, "001", fecha_evaluacion=HOY
            )
    finally:
        motor.dispose()
    return abierta


def test_el_resumen_de_of001_da_el_total_de_la_memoria_sin_cambios(_of001):
    vivo = Registro().crear("f", "caso", NOMBRE_OF001, "001", _of001.borrador, _of001)
    r = hoja_vista.resumen(vivo)
    assert abs(Decimal(r.total.exacto) - D("2703.86")) <= D("0.01")
    assert (r.rev, r.moneda, r.cambios, r.pendientes_catalogo, r.hay_plan) == (
        0,
        "USD",
        0,
        0,
        True,
    )
    assert r.guardado_como is None and r.version_mas_nueva is None
    assert all(isinstance(h.total, int) for h in r.hallazgos)


def test_el_resumen_cuenta_los_cambios_contra_la_version_abierta(_of001):
    from dataclasses import replace

    editado = replace(
        _of001.borrador, parametros=replace(_of001.borrador.parametros, administracion=D("0.20"))
    )
    vivo = Registro().crear("f", "caso", NOMBRE_OF001, "001", editado, _of001)
    r = hoja_vista.resumen(vivo)
    assert r.cambios == 1
    assert abs(Decimal(r.total.exacto) - D("2821.42")) <= D("0.01")


def _espacio_con_un_punto_sin_fuente() -> Espacio:
    lev = OrigenMedida(
        id="LEV",
        tipo=TipoOrigen.LEVANTAMIENTO,
        referencia={"fecha": "2026-10-01", "responsable": "EP"},
    )
    ambiente = Ambiente("A", "Bano", D("0"), D("0"), D("3"), D("2"), D("2.5"), "LEV")
    punto = Punto(
        id="P2",
        nombre="lavamanos",
        especialidad=Especialidad.AGUA,
        tipo=TipoPunto.AGUA_FRIA,
        ambiente_id="A",
        superficie=SuperficiePunto.PARED,
        posicion=Coord(D("2"), D("0"), D("0.6")),
        origen_id="LEV",
        fuente_id=None,
        especificaciones={"diametro": '1/2"', "llave_de_paso": "si"},
    )
    return Espacio(origenes=(lev,), ambientes=(ambiente,), puntos=(punto,))


def test_elaborar_agrega_r17_y_no_la_deja_en_el_borrador():
    """R17 se calcula en cada elaboracion y no se guarda en el borrador (P:286-296)."""
    borrador = hoja.Borrador(fecha=HOY, espacio=_espacio_con_un_punto_sin_fuente())
    resultado = hoja_vista.elaborar(borrador)
    r17 = [h for h in resultado.elaboracion.informe.hallazgos if h.regla == "R17"]
    assert [(h.severidad, h.origen_ids) for h in r17] == [
        (Severidad.ADVERTENCIA, ("esp_puntos:P2",))
    ]
    assert "El punto P2 (lavamanos) no tiene fuente" in r17[0].descripcion
    assert borrador.reglas_extra == ()


def test_la_cache_del_calculo_se_reutiliza_por_rev(_of001):
    vivo = Registro().crear("f", "caso", NOMBRE_OF001, "001", _of001.borrador, _of001)
    primero = hoja_vista.calculo(vivo)
    segundo = hoja_vista.calculo(vivo)
    assert segundo[0] is primero[0] and segundo[1] is primero[1]
    assert vivo.calculo is not None and vivo.calculo[0] == 0


def test_la_base_abierta_describe_la_version(_of001):
    vivo = Registro().crear("f", "caso", NOMBRE_OF001, "001", _of001.borrador, _of001)
    b = hoja_vista.base(vivo, vigente="001")
    assert (b.proyecto, b.version, b.vigente, b.espacio_de, b.solo_lectura, b.moneda) == (
        NOMBRE_OF001,
        "001",
        "001",
        "001",
        False,
        "USD",
    )
    assert b.lista == _of001.lista


def test_la_base_de_un_proyecto_sin_versiones_es_en_blanco():
    vivo = Registro().crear("f", "caso", "Nuevo", None, hoja.Borrador(fecha=HOY), None)
    b = hoja_vista.base(vivo, vigente=None)
    assert (b.proyecto, b.version, b.lista, b.espacio_de, b.solo_lectura) == (
        "Nuevo",
        None,
        None,
        None,
        False,
    )


# --- 3b-2 · vista del espacio y metrajes (R5) -----------------------------------------------------


def _vivo(abierta, borrador=None, version="001"):
    return Registro().crear(
        "f",
        "caso",
        NOMBRE_OF001,
        version,
        abierta.borrador if borrador is None else borrador,
        abierta,
    )


def _elaborada_por_la_clasica(borrador):
    """La elaboracion de la pagina clasica (P:286-296): `elaborar_borrador` con R17 ligada al
    espacio vigente. Se arma aqui a mano con `ui.hoja`, no con `hoja_vista.elaborar`."""
    ligado = replace(borrador, reglas_extra=con_conexion(borrador.reglas_extra, borrador.espacio))
    return clasica.elaborar_borrador(ligado)


def _como_clasica(borrador):
    """El borrador de `aplicacion.hoja` como el `Borrador` de `ui.hoja` (mismos campos)."""
    return clasica.Borrador(
        **{c.name: getattr(borrador, c.name) for c in dataclasses.fields(borrador)}
    )


#: Las columnas de cada tabla editable, escritas a mano desde `ui/hoja.py:148-177`.
COLUMNAS_DE_LA_CLASICA = {
    "origenes": ["id", "tipo", "referencia"],
    "ambientes": ["id", "nombre", "x0", "y0", "largo", "ancho", "alto", "origen_id"],
    "fuentes": ["id", "especialidad", "tipo", "ambiente_id", "x", "y", "z", "origen_id"],
    "puntos": [
        "id",
        "nombre",
        "especialidad",
        "tipo",
        "ambiente_id",
        "superficie",
        "x",
        "y",
        "z",
        "fuente_id",
        "circuito_id",
        "especificaciones",
        "origen_id",
    ],
    "tramos": [
        "recorrido_id",
        "punto_id",
        "circuito_id",
        "orden",
        "superficie",
        "empotrado",
        "pendiente",
        "vertices",
    ],
}


def test_la_vista_del_espacio_trae_las_cinco_tablas_con_las_columnas_de_la_clasica(_of001):
    v = hoja_vista.vista_espacio(_vivo(_of001))
    assert [t.clave for t in v.tablas] == list(COLUMNAS_DE_LA_CLASICA)
    for tabla in v.tablas:
        assert [c.clave for c in tabla.columnas] == COLUMNAS_DE_LA_CLASICA[tabla.clave]
    assert [(t.clave, t.con_estado) for t in v.tablas] == [
        ("origenes", False),
        ("ambientes", True),
        ("fuentes", True),
        ("puntos", True),
        ("tramos", False),
    ]
    assert [t.rotulo for t in v.tablas] == [
        "Orígenes de medida",
        "Ambientes",
        "Fuentes",
        "Puntos",
        "Vértices de recorridos",
    ]


def test_los_rotulos_de_columna_son_los_de_la_clasica_a_mano(_of001):
    v = hoja_vista.vista_espacio(_vivo(_of001))
    ambientes = next(t for t in v.tablas if t.clave == "ambientes")
    assert [c.rotulo for c in ambientes.columnas] == [
        "Código",
        "Nombre",
        "Esquina X (m)",
        "Esquina Y (m)",
        "Largo (m)",
        "Ancho (m)",
        "Alto (m)",
        "Origen de la medida",
    ]
    puntos = next(t for t in v.tablas if t.clave == "puntos")
    assert puntos.columnas[9].rotulo == "Fuente que lo alimenta"
    tramos = next(t for t in v.tablas if t.clave == "tramos")
    assert tramos.columnas[3].rotulo == "Orden del vértice"


def _lista(vista, tabla, columna):
    t = next(t for t in vista.tablas if t.clave == tabla)
    c = next(c for c in t.columnas if c.clave == columna)
    return None if c.lista is None else [(o.valor, o.rotulo) for o in c.lista]


def test_las_listas_cerradas_llevan_el_valor_interno_y_su_rotulo_para_la_persona(_of001):
    v = hoja_vista.vista_espacio(_vivo(_of001))
    assert _lista(v, "origenes", "tipo") == [
        ("plano", "Plano"),
        ("dxf", "Archivo DXF"),
        ("ifc", "Archivo IFC"),
        ("levantamiento", "Levantamiento en obra"),
        ("supuesto", "Supuesto"),
        ("ia", "Propuesta de IA"),
    ]
    assert _lista(v, "fuentes", "especialidad") == [
        ("agua", "Agua"),
        ("datos", "Datos"),
        ("electricidad", "Electricidad"),
    ]
    assert _lista(v, "puntos", "superficie") == [
        ("pared", "Pared"),
        ("techo", "Techo"),
        ("piso", "Piso"),
    ]
    assert _lista(v, "tramos", "superficie") == [
        ("pared", "Pared"),
        ("techo", "Techo"),
        ("plafon", "Plafón"),
        ("piso", "Piso"),
        ("bandeja", "Bandeja"),
    ]
    assert _lista(v, "tramos", "empotrado") == [("", ""), ("si", "Sí"), ("no", "No")]
    assert _lista(v, "ambientes", "nombre") is None  # el texto libre no lleva lista


def test_las_filas_del_espacio_son_las_de_la_clasica_y_un_ambiente_de_of001_es_el_de_la_memoria(
    _of001,
):
    v = hoja_vista.vista_espacio(_vivo(_of001))
    assert v.filas == clasica.filas_desde_espacio(_of001.borrador.espacio)
    # memoria de OF-001, plano de planta: el baño BAN-01 va de (0; 0) y mide 2 × 1,5 × 2,5
    bano = next(f for f in v.filas["ambientes"] if f["id"] == "BAN-01")
    assert (bano["x0"], bano["y0"], bano["largo"], bano["ancho"], bano["alto"]) == (
        "0",
        "0",
        "2",
        "1.5",
        "2.5",
    )
    assert len(v.filas["ambientes"]) == 6  # BAN-01, COC-01, CT-01, REC-01, ZA y ZB
    assert v.filas["tramos"] == []  # los recorridos de OF-001 son propuestos, no declarados


def test_el_estado_por_fila_es_el_de_la_clasica_con_severidad_y_texto(_of001):
    v = hoja_vista.vista_espacio(_vivo(_of001))
    informe = _elaborada_por_la_clasica(_como_clasica(_of001.borrador)).elaboracion.informe
    esperado = clasica.estado_de_filas(_of001.borrador.espacio, informe)
    assert {k: (e.severidad, e.texto) for k, e in v.estado.items()} == {
        k: (None if e.severidad is None else e.severidad.name, e.texto) for k, e in esperado.items()
    }
    # a mano: todo OF-001 declara un origen «supuesto», que es ADVERTENCIA en cada fila que lo cita
    assert v.estado["esp_ambientes:BAN-01"].severidad == "ADVERTENCIA"
    assert v.estado["esp_ambientes:BAN-01"].texto.startswith(
        "ADVERTENCIA: ambiente BAN-01: la medida es un supuesto declarado (origen O1: "
    )
    assert all(k.startswith(("esp_ambientes:", "esp_fuentes:", "esp_puntos:")) for k in v.estado)


def test_una_fila_sin_apu_dice_pendiente_y_cuenta_como_pendiente_del_catalogo(_of001):
    sin_apu = replace(
        _of001.borrador,
        composiciones={k: c for k, c in _of001.borrador.composiciones.items() if k != "AF-SALIDA"},
    )
    p = hoja_vista.vista_espacio(_vivo(_of001, sin_apu))
    assert p.estado["esp_puntos:P1"].severidad == "ERROR"
    assert p.estado["esp_puntos:P1"].texto.startswith(
        "PENDIENTE: sin APU en el catálogo (AF-SALIDA)"
    )
    assert p.pendientes == 1


def test_una_fila_que_ningun_hallazgo_toca_dice_ok():
    lev = OrigenMedida(
        id="LEV",
        tipo=TipoOrigen.LEVANTAMIENTO,
        referencia={"fecha": "2026-10-01", "responsable": "EP"},
    )
    ambiente = Ambiente("A", "Bano", D("0"), D("0"), D("3"), D("2"), D("2.5"), "LEV")
    borrador = hoja.Borrador(fecha=HOY, espacio=Espacio(origenes=(lev,), ambientes=(ambiente,)))
    v = hoja_vista.vista_espacio(Registro().crear("f", "c", "N", None, borrador, None))
    assert (v.estado["esp_ambientes:A"].severidad, v.estado["esp_ambientes:A"].texto) == (
        None,
        "OK",
    )


def test_las_cantidades_derivadas_de_of001_son_las_de_la_memoria(_of001):
    v = hoja_vista.vista_espacio(_vivo(_of001))
    por_partida = {d.partida: d for d in v.derivadas}
    # memoria de OF-001 §2.4: la llave de paso es 3 u; tubería de drenaje 2" 3,950 × 1,10 = 4,345 m;
    # de agua fría 1/2" 7,500 × 1,10 = 8,250 m
    assert Decimal(por_partida["AF-LLAVE"].cantidad.exacto) == D("3")
    assert Decimal(por_partida["DR-TUB-PVC-2"].cantidad.exacto) == D("4.345")
    assert Decimal(por_partida["AF-TUB-PVC-1/2"].cantidad.exacto) == D("8.250")
    assert por_partida["AF-LLAVE"].unidad == "unidad"
    assert por_partida["AF-TUB-PVC-1/2"].unidad == "m"
    assert por_partida["AF-LLAVE"].cantidad.texto == "3.00"
    assert por_partida["AF-TUB-PVC-1/2"].cantidad.texto == "8.25"  # dos decimales, como la clásica
    assert len(v.derivadas) == 30
    assert all(d.origen and d.descripcion for d in v.derivadas)


def test_el_total_de_la_vista_del_espacio_es_el_de_la_memoria_y_sin_pendientes(_of001):
    v = hoja_vista.vista_espacio(_vivo(_of001))
    assert abs(Decimal(v.total.exacto) - D("2703.86")) <= D("0.01")
    assert (v.moneda, v.pendientes, v.vacio_mensaje) == ("USD", 0, None)
    assert v.ayuda.startswith("Describa el espacio en metros")


def test_un_borrador_en_blanco_no_deriva_cantidades_y_lo_dice():
    blanco = hoja.Borrador(fecha=HOY)
    v = hoja_vista.vista_espacio(Registro().crear("f", "c", "N", None, blanco, None))
    assert v.derivadas == ()
    assert v.vacio_mensaje == (
        "El borrador todavía no deriva cantidades: agregue un ambiente, una fuente y los puntos "
        "de agua, de datos o de electricidad."
    )
    assert all(filas == [] for filas in v.filas.values())
    assert v.estado == {}
    assert (v.total.texto, Decimal(v.total.exacto)) == ("0.00", D("0"))
