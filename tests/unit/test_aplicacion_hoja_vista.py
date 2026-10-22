"""La base de las vistas de la hoja (T10, 3b-1): montos, version por omision, resumen y R17.

Oraculos a mano: la regla de la version por omision (las no descartadas, o todas si todas lo estan;
la vigente, o la ultima); los montos, `formatear_decimal` a dos decimales (NORMAS.md §2) y el
exacto con `format(x, "f")`; el resumen de OF-001 usa los literales de la memoria (total
2 703,86 USD; las 30 cantidades de `of001.md` §2.4, §3.4 y §4.5) y el precio unitario de cada
partida se recalcula en la propia prueba con la formula de NORMAS.md §4 (`_pu_a_mano`), no con el
motor. Ya no compara contra `ui.hoja` (retiro de Streamlit, F6).
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

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
from tests.fixtures import caso_of001
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001

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


@pytest.mark.parametrize(
    ("vigente_ahora", "vigente_al_abrir", "esperado"),
    [
        ("002", "002", None),  # nadie guardo: abrir a proposito una vieja no avisa
        ("003", "002", "003"),  # alguien guardo despues de abrir
        ("001", "001", None),
        ("002", None, "002"),  # no habia vigente al abrir (todas descartadas) y ahora si
        (None, "002", None),  # ahora todas descartadas: no hay version mas nueva que ofrecer
        (None, None, None),
    ],
)
def test_version_mas_nueva_compara_la_vigente_de_ahora_con_la_de_cuando_se_abrio(
    _of001, vigente_ahora, vigente_al_abrir, esperado
):
    vivo = Registro().crear(
        "f", "caso", NOMBRE_OF001, "001", _of001.borrador, _of001, vigente_al_abrir=vigente_al_abrir
    )
    assert hoja_vista.version_mas_nueva(vivo, vigente_ahora) == esperado


def test_un_borrador_en_blanco_nunca_avisa_de_una_version_mas_nueva():
    vivo = Registro().crear("f", "caso", "Nuevo", None, hoja.Borrador(fecha=HOY), None)
    assert hoja_vista.version_mas_nueva(vivo, "001") is None


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


#: Las 30 cantidades finales de OF-001, escritas desde la memoria `of001.md`: §2.4 (agua, con 10 %
#: de desperdicio en tuberia), §3.4 (datos) y §4.5 (electricidad).
CANTIDADES_DE_LA_MEMORIA = {
    "AF-TUB-PVC-3/4": D("6.930"),
    "AF-TUB-PVC-1/2": D("8.250"),
    "AF-CODO-3/4": D("2"),
    "AF-CODO-1/2": D("3"),
    "AF-TEE-3/4": D("1"),
    "AF-LLAVE": D("3"),
    "AF-PICADO-PARED": D("9.800"),
    "AF-SALIDA": D("3"),
    "DR-TUB-PVC-2": D("4.345"),
    "DR-TUB-PVC-1-1/2": D("1.925"),
    "DR-CODO-2": D("3"),
    "DR-CODO-1-1/2": D("2"),
    "DR-PICADO-PISO": D("4.750"),
    "DR-PICADO-PARED": D("0.950"),
    "DR-SALIDA": D("3"),
    "DT-UTP-CAT-6": D("101.640"),
    "DT-CAN-EMT-3/4": D("23.200"),
    "DT-CAN-EMT-1/2": D("8.200"),
    "DT-CAJA": D("7"),
    "DT-FACEPLATE": D("7"),
    "DT-JACK": D("7"),
    "DT-CERT": D("7"),
    "EL-COND-12-AWG": D("75.570"),
    "EL-COND-14-AWG": D("33.000"),
    "EL-TUB-EMT-3/4": D("16.300"),
    "EL-TUB-EMT-1/2": D("9.000"),
    "EL-CAJA": D("8"),
    "EL-SALIDA-TOMA": D("4"),
    "EL-SALIDA-ILUM": D("4"),
    "EL-PROT": D("2"),
}
CONCEPTOS_DEL_CIERRE = [
    "Materiales",
    "Equipos",
    "Mano de obra",
    "= Costo directo",
    "+ Administracion",
    "= Con administracion",
    "+ Utilidad",
    "= Precio unitario",
]
CENTAVO = D("0.01")


def _a_mano(composicion):
    """Los ocho montos del cierre de un APU de OF-001, con la formula de NORMAS.md §4 y los
    parametros de la memoria (FCAS 6,00, bono 5,81, administracion 0,15, utilidad 0,10): materiales
    completos; equipos con su depreciacion entre el rendimiento; mano de obra a jornal con
    FCAS y bono entre el rendimiento; administracion y utilidad en cascada. Sin redondeos."""
    materiales = sum((m.cantidad * m.precio for m in composicion.materiales), D(0))
    equipos = (
        sum((e.cantidad * e.precio * e.depreciacion for e in composicion.equipos), D(0))
        / composicion.rendimiento
    )
    obreros = sum((o.cantidad for o in composicion.mano_obra), D(0))
    sueldos = sum((o.cantidad * o.sueldo * (1 + D("6.00")) for o in composicion.mano_obra), D(0))
    mano_obra = (sueldos + D("5.81") * obreros) / composicion.rendimiento
    costo_directo = materiales + equipos + mano_obra
    administracion = costo_directo * D("0.15")
    con_administracion = costo_directo + administracion
    utilidad = con_administracion * D("0.10")
    return [
        materiales,
        equipos,
        mano_obra,
        costo_directo,
        administracion,
        con_administracion,
        utilidad,
        con_administracion + utilidad,
    ]


def _pu_a_mano(codigo: str) -> Decimal:
    return _a_mano(caso_of001.COMPOSICIONES[codigo])[-1]


def _a_dos_decimales(valor: Decimal) -> str:
    return str(valor.quantize(CENTAVO, rounding=ROUND_HALF_UP))


def test_la_formula_a_mano_da_los_literales_de_af_llave_y_el_total_de_la_memoria():
    """Valida el oraculo de esta prueba contra los literales de la memoria: AF-LLAVE (costo
    directo 10,433785; precio unitario 13,198738025) y el total de OF-001 (2 703,86)."""
    llave = _a_mano(caso_of001.COMPOSICIONES["AF-LLAVE"])
    assert llave[3] == D("10.433785") and llave[-1] == D("13.198738025")
    total = sum((c * _pu_a_mano(k) for k, c in CANTIDADES_DE_LA_MEMORIA.items()), D(0))
    assert abs(total - D("2703.86")) <= D("0.01")
    assert set(CANTIDADES_DE_LA_MEMORIA) == set(caso_of001.COMPOSICIONES)


#: Las columnas de cada tabla editable, escritas a mano.
COLUMNAS_DE_LAS_TABLAS = {
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


def test_la_vista_del_espacio_trae_las_cinco_tablas_con_sus_columnas(_of001):
    v = hoja_vista.vista_espacio(_vivo(_of001))
    assert [t.clave for t in v.tablas] == list(COLUMNAS_DE_LAS_TABLAS)
    for tabla in v.tablas:
        assert [c.clave for c in tabla.columnas] == COLUMNAS_DE_LAS_TABLAS[tabla.clave]
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


def test_los_rotulos_de_columna_son_los_escritos_a_mano(_of001):
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


def test_las_filas_del_espacio_son_las_de_la_memoria_de_of001(_of001):
    v = hoja_vista.vista_espacio(_vivo(_of001))
    assert (len(v.filas["ambientes"]), len(v.filas["fuentes"]), len(v.filas["puntos"])) == (
        6,
        6,
        21,
    )
    f1 = next(f for f in v.filas["fuentes"] if f["id"] == "F1")  # memoria §1.2: agua en BAN-01
    assert (f1["especialidad"], f1["ambiente_id"], f1["x"], f1["y"], f1["z"]) == (
        "agua",
        "BAN-01",
        "0",
        "0",
        "0",
    )
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


def test_el_estado_por_fila_es_advertencia_de_origen_supuesto_en_las_33_filas(_of001):
    """Memoria §1: todo OF-001 declara un origen «supuesto» (O1), que es ADVERTENCIA en cada uno de
    sus 6 ambientes, 6 fuentes y 21 puntos (33 filas, una por hallazgo R8)."""
    v = hoja_vista.vista_espacio(_vivo(_of001))
    assert len(v.estado) == 6 + 6 + 21
    assert {e.severidad for e in v.estado.values()} == {"ADVERTENCIA"}
    assert all(e.texto.startswith("ADVERTENCIA: ") for e in v.estado.values())
    assert all(
        "la medida es un supuesto declarado (origen O1: " in e.texto for e in v.estado.values()
    )
    assert v.estado["esp_ambientes:BAN-01"].texto.startswith(
        "ADVERTENCIA: ambiente BAN-01: la medida es un supuesto declarado (origen O1: "
    )
    assert v.estado["esp_fuentes:F1"].texto.startswith("ADVERTENCIA: fuente F1: la medida es un")
    assert v.estado["esp_puntos:P1"].texto.startswith("ADVERTENCIA: punto P1: la medida es un")
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
    assert {d.partida: Decimal(d.cantidad.exacto) for d in v.derivadas} == CANTIDADES_DE_LA_MEMORIA
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


# --- 3b-2 · vista del presupuesto (R6) ----------------------------------------------------------

#: A mano, con la fórmula de NORMAS.md §4 y los precios de `tests/fixtures/caso_of001.py` (USD a 4
#: decimales): materiales 7,7483; equipos 14,3046 ÷ 20 = 0,71523; mano de obra (2,1877 + 1,7816) ×
#: (1 + 6,00) = 27,7851 más bono 5,81 × 2 = 11,62, todo ÷ 20 = 1,970255; costo directo 10,433785;
#: × 1,15 × 1,10 = 13,19874 (el precio unitario de AF-LLAVE).
PU_DE_AF_LLAVE = D("13.19874")


def _fila_de(vista, partida):
    return next(f for f in vista.filas if f.partida == partida)


def test_las_filas_del_presupuesto_son_las_de_la_memoria_con_su_monto_exacto(_of001):
    v = hoja_vista.vista_presupuesto(_vivo(_of001))
    assert [f.partida for f in v.filas] == CODIGOS_DE_OF001
    assert all(f.clave.startswith(f"{f.partida}|") for f in v.filas)
    assert {f.partida: Decimal(f.cantidad) for f in v.filas} == CANTIDADES_DE_LA_MEMORIA
    for f in v.filas:
        pu = _pu_a_mano(f.partida)
        total = CANTIDADES_DE_LA_MEMORIA[f.partida] * pu
        assert abs(Decimal(f.pu.exacto) - pu) <= D("0.000001"), f.partida
        assert abs(Decimal(f.total.exacto) - total) <= D("0.000001"), f.partida
        assert (f.pu.texto, f.total.texto) == (_a_dos_decimales(pu), _a_dos_decimales(total))
    assert (_fila_de(v, "AF-LLAVE").unidad, _fila_de(v, "DR-TUB-PVC-2").unidad) == ("unidad", "m")
    assert len(v.filas) == 30
    assert abs(Decimal(v.total.exacto) - D("2703.86")) <= D("0.01")
    assert (v.moneda, v.vacio_mensaje) == ("USD", None)


def test_el_precio_unitario_de_una_partida_es_el_de_la_cascada_a_mano(_of001):
    llave = _fila_de(hoja_vista.vista_presupuesto(_vivo(_of001)), "AF-LLAVE")
    assert abs(Decimal(llave.pu.exacto) - PU_DE_AF_LLAVE) <= D("0.0001")
    assert llave.pu.texto == "13.20"
    assert llave.cantidad == "3" and llave.cantidad_calculada == "3" and llave.escrita is False
    assert abs(Decimal(llave.total.exacto) - 3 * PU_DE_AF_LLAVE) <= D("0.001")
    assert (llave.estado.severidad, llave.estado.texto) == (None, "OK")


def test_una_cantidad_escrita_a_mano_se_marca_y_conserva_la_calculada(_of001):
    clave = next(
        c
        for c in hoja.claves_de_items(hoja.items_sin_escribir(_of001.borrador))
        if c.startswith("AF-LLAVE|")
    )
    editado = replace(_of001.borrador, cantidades={clave: D("5")})
    antes = hoja_vista.vista_presupuesto(_vivo(_of001))
    v = hoja_vista.vista_presupuesto(_vivo(_of001, editado))
    llave = _fila_de(v, "AF-LLAVE")
    assert (llave.cantidad, llave.cantidad_calculada, llave.escrita) == ("5", "3", True)
    assert llave.estado.severidad == "ADVERTENCIA"  # R8: escrita a mano
    # 3c-B3: la diferencia del total son 2 unidades más a 13,19874 (confirmado por el árbitro)
    delta = Decimal(v.total.exacto) - Decimal(antes.total.exacto)
    assert abs(delta - 2 * PU_DE_AF_LLAVE) <= D("0.001")
    assert [f.escrita for f in v.filas].count(True) == 1


def test_una_partida_sin_apu_no_tiene_precio_ni_total_y_queda_pendiente(_of001):
    sin_apu = replace(
        _of001.borrador,
        composiciones={k: c for k, c in _of001.borrador.composiciones.items() if k != "AF-SALIDA"},
    )
    v = hoja_vista.vista_presupuesto(_vivo(_of001, sin_apu))
    salida = _fila_de(v, "AF-SALIDA")
    assert (salida.pu, salida.total) == (None, None)
    assert salida.estado.severidad == "ERROR"
    assert salida.estado.texto.startswith("PENDIENTE: sin APU en el catálogo (AF-SALIDA)")
    assert len(v.filas) == 30


def test_un_presupuesto_sin_renglones_lo_dice():
    v = hoja_vista.vista_presupuesto(
        Registro().crear("f", "c", "N", None, hoja.Borrador(fecha=HOY), None)
    )
    assert v.filas == ()
    assert v.vacio_mensaje == "El presupuesto no tiene renglones todavía."
    assert (v.total.texto, v.moneda) == ("0.00", "USD")


# --- 3b-2 · vista del APU (R7) -------------------------------------------------------------------

CODIGOS_DE_OF001 = [
    "AF-CODO-1/2",
    "AF-CODO-3/4",
    "AF-LLAVE",
    "AF-PICADO-PARED",
    "AF-SALIDA",
    "AF-TEE-3/4",
    "AF-TUB-PVC-1/2",
    "AF-TUB-PVC-3/4",
    "DR-CODO-1-1/2",
    "DR-CODO-2",
    "DR-PICADO-PARED",
    "DR-PICADO-PISO",
    "DR-SALIDA",
    "DR-TUB-PVC-1-1/2",
    "DR-TUB-PVC-2",
    "DT-CAJA",
    "DT-CAN-EMT-1/2",
    "DT-CAN-EMT-3/4",
    "DT-CERT",
    "DT-FACEPLATE",
    "DT-JACK",
    "DT-UTP-CAT-6",
    "EL-CAJA",
    "EL-COND-12-AWG",
    "EL-COND-14-AWG",
    "EL-PROT",
    "EL-SALIDA-ILUM",
    "EL-SALIDA-TOMA",
    "EL-TUB-EMT-1/2",
    "EL-TUB-EMT-3/4",
]


def test_la_lista_de_partidas_trae_las_valoradas_con_su_descripcion_y_selecciona_la_primera(
    _of001,
):
    v = hoja_vista.vista_apu(_vivo(_of001))
    assert [p.codigo for p in v.partidas] == CODIGOS_DE_OF001
    assert v.partidas[2].descripcion == "Llave de paso de agua fria instalada"
    assert (v.sin_coincidencias, v.seleccionada, v.vacio_mensaje) == (False, "AF-CODO-1/2", None)
    assert v.detalle is not None and v.detalle.codigo == "AF-CODO-1/2"


@pytest.mark.parametrize(
    ("buscar", "esperados"),
    [
        ("picado", ["AF-PICADO-PARED", "DR-PICADO-PARED", "DR-PICADO-PISO"]),
        ("PICADO", ["AF-PICADO-PARED", "DR-PICADO-PARED", "DR-PICADO-PISO"]),
        ("sifón", ["DR-SALIDA"]),  # sin tildes ni mayúsculas: «sifon» en la descripción
        ("af-llave", ["AF-LLAVE"]),  # por código
        ("  ", CODIGOS_DE_OF001),
    ],
)
def test_buscar_filtra_por_codigo_o_descripcion_sin_tildes_ni_mayusculas(_of001, buscar, esperados):
    v = hoja_vista.vista_apu(_vivo(_of001), buscar=buscar)
    assert [p.codigo for p in v.partidas] == esperados
    assert v.sin_coincidencias is False
    assert v.seleccionada == esperados[0]


def test_sin_coincidencias_se_muestran_todas_y_se_avisa(_of001):
    v = hoja_vista.vista_apu(_vivo(_of001), buscar="zzz")
    assert v.sin_coincidencias is True
    assert [p.codigo for p in v.partidas] == CODIGOS_DE_OF001
    assert v.seleccionada == "AF-CODO-1/2"


def test_la_partida_pedida_se_selecciona_y_una_ajena_a_la_lista_cae_a_la_primera(_of001):
    vivo = _vivo(_of001)
    assert hoja_vista.vista_apu(vivo, partida="AF-LLAVE").seleccionada == "AF-LLAVE"
    assert hoja_vista.vista_apu(vivo, partida="NO-EXISTE").seleccionada == "AF-CODO-1/2"
    # filtrada fuera de la lista visible: la primera visible, como el radio de la clásica (P:1604)
    v = hoja_vista.vista_apu(vivo, partida="AF-LLAVE", buscar="picado")
    assert v.seleccionada == "AF-PICADO-PARED"


def test_el_detalle_de_af_llave_trae_los_tres_rubros_de_la_composicion(_of001):
    d = hoja_vista.vista_apu(_vivo(_of001), partida="AF-LLAVE").detalle
    assert (d.codigo, d.unidad, d.rendimiento) == ("AF-LLAVE", "unidad", "20")
    assert d.descripcion == "Llave de paso de agua fria instalada"
    assert [(g.clave, g.rotulo) for g in d.grupos] == [
        ("materiales", "Materiales"),
        ("equipos", "Equipos"),
        ("mano de obra", "Mano de obra"),
    ]
    materiales, equipos, mano_obra = d.grupos
    assert [c.clave for c in materiales.columnas] == ["descripcion", "unidad", "cantidad", "precio"]
    assert [c.clave for c in equipos.columnas] == [
        "descripcion",
        "cantidad",
        "precio",
        "depreciacion",
    ]
    assert [c.clave for c in mano_obra.columnas] == [
        "descripcion",
        "cantidad",
        "sueldo",
        "modalidad",
    ]
    assert materiales.filas == [
        {
            "descripcion": "Llave de paso de bola PVC 1/2 pulg [PLOG26]",
            "unidad": "pieza",
            "cantidad": "1",
            "precio": "7.7483",
        }
    ]
    assert [f["descripcion"] for f in mano_obra.filas] == [
        "Plomero de 1ra N5 [19-212]",
        "Ayudante N2 [1-1.2]",
    ]
    assert mano_obra.filas[0]["sueldo"] == "2.1877" and mano_obra.filas[0]["modalidad"] == "jornal"


def test_los_subtotales_y_el_cierre_de_af_llave_son_la_cascada_a_mano(_of001):
    """Hecha a mano con `caso_of001.py` (ver el test del presupuesto): materiales 7,7483; equipos
    14,3046 ÷ 20 = 0,71523; mano de obra ((2,1877 + 1,7816) × 7 + 2 × 5,81) ÷ 20 = 1,970255;
    costo directo 10,433785; administración 15 % = 1,56506775; con administración 11,99885275;
    utilidad 10 % en cascada = 1,199885275; precio unitario 13,198738025."""
    d = hoja_vista.vista_apu(_vivo(_of001), partida="AF-LLAVE").detalle
    subtotales = [Decimal(g.subtotal.exacto) for g in d.grupos]
    assert subtotales == [D("7.7483"), D("0.71523"), D("1.970255")]
    assert [g.subtotal.texto for g in d.grupos] == ["7.75", "0.72", "1.97"]
    esperado = [
        ("Materiales", "7.7483", "completos"),
        ("Equipos", "0.71523", "entre el rendimiento"),
        ("Mano de obra", "1.970255", "FCAS 6 y bono 5.81, entre el rendimiento"),
        ("= Costo directo", "10.433785", ""),
        ("+ Administracion", "1.56506775", "15.0 % del costo directo"),
        ("= Con administracion", "11.99885275", ""),
        ("+ Utilidad", "1.199885275", "10.0 % en cascada"),
        ("= Precio unitario", "13.198738025", ""),
    ]
    assert [(c.concepto, c.nota) for c in d.cierre] == [(c, n) for c, _, n in esperado]
    for fila, (_, exacto, _) in zip(d.cierre, esperado, strict=True):
        assert abs(Decimal(fila.monto.exacto) - D(exacto)) <= D("0.000001")
    assert [c.monto.texto for c in d.cierre] == [
        "7.75",
        "0.72",
        "1.97",
        "10.43",
        "1.57",
        "12.00",
        "1.20",
        "13.20",
    ]
    m = d.metricas
    assert (m.materiales.texto, m.equipos.texto, m.mano_obra.texto) == ("7.75", "0.72", "1.97")
    assert abs(Decimal(m.precio_unitario.exacto) - D("13.198738025")) <= D("0.000001")


def test_el_cierre_y_las_tablas_de_cada_partida_son_los_de_la_formula_a_mano(_of001):
    """Las 30 partidas: tablas = lineas de la fixture; cierre = los ocho montos de NORMAS.md §4."""
    vivo = _vivo(_of001)
    for codigo in CODIGOS_DE_OF001:
        d = hoja_vista.vista_apu(vivo, partida=codigo).detalle
        composicion = caso_of001.COMPOSICIONES[codigo]
        materiales, equipos, mano_obra = (g.filas for g in d.grupos)
        assert [(f["descripcion"], f["unidad"]) for f in materiales] == [
            (m.descripcion, m.unidad) for m in composicion.materiales
        ], codigo
        assert [Decimal(f["precio"]) for f in materiales] == [
            m.precio for m in composicion.materiales
        ], codigo
        assert [Decimal(f["cantidad"]) for f in equipos] == [
            e.cantidad for e in composicion.equipos
        ]
        assert [Decimal(f["depreciacion"]) for f in equipos] == [
            e.depreciacion for e in composicion.equipos
        ], codigo
        assert [Decimal(f["sueldo"]) for f in mano_obra] == [
            o.sueldo for o in composicion.mano_obra
        ]
        assert d.rendimiento == format(composicion.rendimiento, "f"), codigo
        esperado = _a_mano(composicion)
        assert [c.concepto for c in d.cierre] == CONCEPTOS_DEL_CIERRE, codigo
        for fila, monto in zip(d.cierre, esperado, strict=True):
            assert abs(Decimal(fila.monto.exacto) - monto) <= D("0.000001"), (codigo, fila.concepto)
            assert fila.monto.texto == _a_dos_decimales(monto), (codigo, fila.concepto)
        assert [c.nota for c in d.cierre][3:] == [
            "",
            "15.0 % del costo directo",
            "",
            "10.0 % en cascada",
            "",
        ], codigo


def test_el_estado_de_la_partida_se_dice_solo_si_no_esta_ok(_of001):
    vivo = _vivo(_of001)
    limpio = hoja_vista.vista_apu(vivo, partida="AF-LLAVE").detalle
    assert limpio.estados == ()
    advertido = hoja_vista.vista_apu(vivo, partida="AF-CODO-3/4").detalle
    assert len(advertido.estados) == 1
    assert advertido.estados[0].startswith(
        "Estado de AF-CODO-3/4|esp_fuentes:F1: ADVERTENCIA: fuente F1: la medida es un supuesto"
    )


def test_cambiar_el_insumo_solo_se_ofrece_con_una_version_abierta(_of001):
    assert hoja_vista.vista_apu(_vivo(_of001)).detalle.solo_lectura_insumos is False
    sin_version = Registro().crear("f", "c", "N", None, _of001.borrador, None)
    assert hoja_vista.vista_apu(sin_version).detalle.solo_lectura_insumos is True


def test_sin_partidas_valoradas_no_hay_detalle_y_se_dice():
    v = hoja_vista.vista_apu(Registro().crear("f", "c", "N", None, hoja.Borrador(fecha=HOY), None))
    assert (v.partidas, v.seleccionada, v.detalle) == ((), None, None)
    assert v.vacio_mensaje == (
        "Todavía no hay partidas valoradas: derive cantidades en Espacio y metrajes."
    )


# --- 3b-2 · vista del plan y la curva (R8) ----------------------------------------------------


def test_el_plan_de_of001_es_secuencial_una_partida_por_dia(_of001):
    v = hoja_vista.vista_plan(_vivo(_of001))
    assert v.hay_plan is True and v.mensaje is None and v.moneda == "USD"
    assert list(v.etiquetas) == [f"Dia {n}" for n in range(1, 31)]
    # a mano: el plan secuencial pone cada partida, al 100 %, en su propio dia y en el orden del
    # presupuesto (la primera es AF-CODO-1/2, la segunda AF-CODO-3/4)
    primera, segunda = v.filas[0], v.filas[1]
    assert primera.partida == "AF-CODO-1/2" and segunda.partida == "AF-CODO-3/4"
    assert primera.valores["Dia 1"] == "1" and primera.valores["Dia 2"] == "0"
    assert segunda.valores["Dia 2"] == "1" and segunda.valores["Dia 1"] == "0"
    assert [f.partida for f in v.filas] == CODIGOS_DE_OF001
    for i, fila in enumerate(v.filas, start=1):  # la partida i va entera en el dia i
        assert fila.valores == {f"Dia {n}": "1" if n == i else "0" for n in range(1, 31)}


def test_la_curva_de_of001_acumula_los_montos_y_cierra_en_el_total_y_en_100(_of001):
    v = hoja_vista.vista_plan(_vivo(_of001))
    total = Decimal(hoja_vista.vista_presupuesto(_vivo(_of001)).total.exacto)
    assert len(v.curva) == 30
    acumulado = D(0)
    for punto in v.curva:
        acumulado += Decimal(punto.monto.exacto)
        assert Decimal(punto.acumulado.exacto) == acumulado
        # el porcentaje es lo acumulado entre el total por 100 (lo declara la tabla de la clásica)
        assert abs(Decimal(punto.porcentaje.exacto) - acumulado / total * 100) <= D("0.000001")
    assert abs(Decimal(v.curva[-1].acumulado.exacto) - total) <= D("0.000001")
    assert v.curva[-1].porcentaje.texto == "100.00"
    # la memoria de OF-001: el punto de equilibrio se alcanza en el día 23 de la curva
    assert v.curva[22].periodo == "Dia 23"


def test_la_curva_muestra_los_montos_de_cada_dia_calculados_a_mano(_of001):
    """Plan secuencial: el monto del dia i es cantidad x precio unitario de la partida i."""
    v = hoja_vista.vista_plan(_vivo(_of001))
    montos = [CANTIDADES_DE_LA_MEMORIA[c] * _pu_a_mano(c) for c in CODIGOS_DE_OF001]
    total = sum(montos, D(0))
    acumulado = D(0)
    for punto, codigo, monto in zip(v.curva, CODIGOS_DE_OF001, montos, strict=True):
        acumulado += monto
        assert punto.periodo.split(" [")[0] == f"Dia {CODIGOS_DE_OF001.index(codigo) + 1}"
        assert punto.monto.texto == _a_dos_decimales(monto), codigo
        assert punto.acumulado.texto == _a_dos_decimales(acumulado), codigo
        assert punto.porcentaje.texto == _a_dos_decimales(acumulado / total * 100), codigo
    assert v.curva[0].monto.texto == "11.18" and v.curva[1].acumulado.texto == "21.05"


def test_sin_plan_no_hay_curva_y_lo_dice():
    v = hoja_vista.vista_plan(Registro().crear("f", "c", "N", None, hoja.Borrador(fecha=HOY), None))
    assert (v.hay_plan, v.etiquetas, v.filas, v.curva) == (False, (), (), ())
    assert v.mensaje == (
        "Esta versión no tiene plan de trabajo, así que no hay curva de inversión."
    )
    assert v.moneda == "USD"


# --- 3b-3 · vista del punto de equilibrio (R9) ----------------------------------------------------

from core.budget.equilibrio import equilibrio as _pe_de_core  # noqa: E402
from core.contracts.presupuesto import PuntoCurva  # noqa: E402


def test_el_equilibrio_de_of001_es_el_de_la_memoria(_of001):
    """3b-B8 / P3: CV 2137,44; PE 1530,49 (±0,01); 56,60 % (±0,01); se alcanza en el Dia 23."""
    v = hoja_vista.vista_equilibrio(_vivo(_of001))
    assert v.estado == "calculado" and v.moneda == "USD"
    assert v.costo_variable.texto == "2137.44"
    assert abs(Decimal(v.punto.exacto) - D("1530.49")) <= D("0.01")
    assert abs(Decimal(v.porcentaje.exacto) - D("56.60")) <= D("0.01")
    assert v.periodo is not None and v.periodo.startswith("Dia 23")
    assert v.mensaje.startswith("Se alcanza en Dia 23, al ") and v.mensaje.endswith(
        " % de ese período."
    )
    assert D("0") < Decimal(v.fraccion_periodo) <= D("1")
    # a mano: ventas 2703,86; CF = CV × 0,15 = 320,616; utilidad = V − CV − CF = 245,80
    assert abs(Decimal(v.venta.exacto) - D("2703.86")) <= D("0.01")
    assert abs(Decimal(v.costo_fijo.exacto) - D("320.616")) <= D("0.002")
    assert abs(Decimal(v.utilidad.exacto) - D("245.80")) <= D("0.02")


def test_con_administracion_020_el_equilibrio_sube_a_la_memoria(_of001):
    """P13 (las cifras que confirmo el arbitro): total 2821,42; PE 1763,39; 62,50 %."""
    editado = replace(
        _of001.borrador, parametros=replace(_of001.borrador.parametros, administracion=D("0.20"))
    )
    v = hoja_vista.vista_equilibrio(_vivo(_of001, editado))
    assert abs(Decimal(v.venta.exacto) - D("2821.42")) <= D("0.01")
    assert abs(Decimal(v.punto.exacto) - D("1763.39")) <= D("0.01")
    assert abs(Decimal(v.porcentaje.exacto) - D("62.50")) <= D("0.01")


CURVA = (
    PuntoCurva("Dia 1", D("10"), D("10")),
    PuntoCurva("Dia 2", D("30"), D("40")),
    PuntoCurva("Dia 3", D("60"), D("100")),
)


@pytest.mark.parametrize(
    ("venta", "cv", "cf", "curva", "estado", "frase"),
    [
        # V = 0: no aplica (texto de H:1221-1238)
        (
            D("0"),
            D("0"),
            D("0"),
            (),
            "no_aplicable",
            "El presupuesto no tiene ventas: el punto de equilibrio no aplica.",
        ),
        # m = (100 − 100) / 100 = 0 → no hay punto
        (
            D("100"),
            D("100"),
            D("10"),
            CURVA,
            "no_existe",
            "No existe punto de equilibrio: el margen de contribución no es positivo "
            "(los costos directos igualan o superan las ventas).",
        ),
        # PE = 60 × 100 / (100 − 50) = 120 > 100 → no se alcanza
        (
            D("100"),
            D("50"),
            D("60"),
            CURVA,
            "no_se_alcanza",
            "El punto de equilibrio (120.00) no se alcanza dentro del contrato (100.00).",
        ),
        # PE = 10 × 100 / 50 = 20 y sin curva → no se ubica
        (
            D("100"),
            D("50"),
            D("10"),
            (),
            "calculado",
            "Sin curva de inversión: el punto de equilibrio no se ubica en el plan.",
        ),
        # PE = 20: acumulado del Dia 1 = 10 < 20 <= 40; fracción (20 − 10) / 30 = 1/3 → 33 %
        (
            D("100"),
            D("50"),
            D("10"),
            CURVA,
            "calculado",
            "Se alcanza en Dia 2, al 33 % de ese período.",
        ),
    ],
)
def test_los_cuatro_casos_limite_del_equilibrio_dicen_su_frase(venta, cv, cf, curva, estado, frase):
    """3b-B9 / P4: cada caso límite, con montos escritos a mano."""
    pe = _pe_de_core(venta, cv, cf, curva)
    v = hoja_vista.equilibrio_a_vista(pe, "USD")
    assert v.estado == estado and v.mensaje == frase


def test_sin_punto_no_hay_punto_ni_porcentaje_ni_periodo():
    v = hoja_vista.equilibrio_a_vista(_pe_de_core(D("0"), D("0"), D("0"), ()), "USD")
    assert (v.punto, v.porcentaje, v.periodo, v.fraccion_periodo) == (None, None, None, None)
    v = hoja_vista.equilibrio_a_vista(_pe_de_core(D("100"), D("50"), D("60"), CURVA), "USD")
    assert (v.punto.texto, v.porcentaje.texto, v.periodo) == ("120.00", "120.00", None)


def test_el_equilibrio_de_un_borrador_en_blanco_no_aplica():
    v = hoja_vista.vista_equilibrio(
        Registro().crear("f", "c", "N", None, hoja.Borrador(fecha=HOY), None)
    )
    assert v.estado == "no_aplicable" and v.punto is None
    assert v.mensaje == "El presupuesto no tiene ventas: el punto de equilibrio no aplica."


# --- 3b-3 · vista de los parametros (R10) ---------------------------------------------------------

#: Los rotulos de los parametros, escritos a mano y sin tildes;
#: la nueva los lleva con tildes (D-3), asi que se comparan normalizados.
ROTULOS_DE_LOS_PARAMETROS = {
    "fcas": "FCAS (fraccion: 6.00 = prestaciones del 600 %)",
    "bono_alimentacion": "Bono de alimentacion (por obrero y dia)",
    "administracion": "Administracion (fraccion del costo directo)",
    "utilidad": "Utilidad (fraccion, en cascada sobre la administracion)",
}


def test_los_parametros_de_of001_son_los_cuatro_de_la_memoria_con_su_texto_exacto(_of001):
    from tests.fixtures import caso_ti001

    v = hoja_vista.vista_parametros(_vivo(_of001), "USD", True)
    assert [c.clave for c in v.campos] == [
        "fcas",
        "bono_alimentacion",
        "administracion",
        "utilidad",
    ]
    valores = {c.clave: Decimal(c.valor) for c in v.campos}
    assert valores["fcas"] == D("6.00") and valores["administracion"] == D("0.15")
    assert valores["utilidad"] == D("0.10")
    assert valores["bono_alimentacion"] == caso_ti001.PARAMETROS.bono_alimentacion
    assert abs(Decimal(v.total.exacto) - D("2703.86")) <= D("0.01")
    assert (v.moneda_proyecto, v.puede_convertir) == ("USD", True)


def test_los_rotulos_de_los_parametros_llevan_tildes(_of001):
    from core.verification.texto import normalizar_texto

    v = hoja_vista.vista_parametros(_vivo(_of001), "USD", True)
    assert {c.clave: normalizar_texto(c.rotulo) for c in v.campos} == {
        k: normalizar_texto(r) for k, r in ROTULOS_DE_LOS_PARAMETROS.items()
    }
    assert v.campos[2].rotulo == "Administración (fracción del costo directo)"  # con tildes


def test_un_parametro_editado_se_ve_con_su_texto_y_mueve_el_total(_of001):
    editado = replace(
        _of001.borrador, parametros=replace(_of001.borrador.parametros, administracion=D("0.20"))
    )
    v = hoja_vista.vista_parametros(_vivo(_of001, editado), "USD", True)
    assert {c.clave: c.valor for c in v.campos}["administracion"] == "0.20"
    assert abs(Decimal(v.total.exacto) - D("2821.42")) <= D("0.01")


def test_sin_version_abierta_no_hay_moneda_del_proyecto_ni_se_puede_convertir():
    vivo = Registro().crear("f", "c", "N", None, hoja.Borrador(fecha=HOY), None)
    v = hoja_vista.vista_parametros(vivo, "USD", True)
    assert (v.moneda_proyecto, v.puede_convertir) == (None, False)
    assert v.total.exacto == "0" and [c.valor for c in v.campos][2] == "0.15"  # los del contrato


def test_sin_el_permiso_de_convertir_la_vista_no_lo_ofrece(_of001):
    assert hoja_vista.vista_parametros(_vivo(_of001), "USD", False).puede_convertir is False


# --- 3b-3 · informe de auditoria (R11) y R17 ------------------------------------------------------


def test_el_informe_de_la_auditoria_de_of001_trae_sus_34_hallazgos_y_evalua_r17(_of001):
    """3b-B21 (segunda clausula): la auditoria sale de `elaborar` (con R17) y no de la base.
    Memoria: 33 hallazgos R8 (origen «supuesto» en 6 ambientes + 6 fuentes + 21 puntos) y el R11
    informativo de los 49 insumos sin referencia MaPreX (38 materiales + 6 equipos + 5 oficios)."""
    informe = hoja_vista.informe_de_auditoria(_vivo(_of001))
    reglas = [h.regla for h in informe.hallazgos]
    assert (reglas.count("R8"), reglas.count("R11"), len(reglas)) == (33, 1, 34)
    assert {h.severidad for h in informe.hallazgos if h.regla == "R8"} == {Severidad.ADVERTENCIA}
    (r11,) = [h for h in informe.hallazgos if h.regla == "R11"]
    assert r11.severidad == Severidad.INFO
    assert r11.descripcion.startswith("49 insumos no contrastables: 49 sin referencia MaPreX")
    assert "R17" in [codigo for codigo, _, _ in informe.cuenta_por_regla_evaluada()]


def test_un_punto_de_agua_sin_fuente_da_r17_advertencia_en_la_auditoria():
    borrador = hoja.Borrador(fecha=HOY, espacio=_espacio_con_un_punto_sin_fuente())
    vivo = Registro().crear("f", "c", "N", None, borrador, None)
    r17 = [h for h in hoja_vista.informe_de_auditoria(vivo).hallazgos if h.regla == "R17"]
    assert [(h.severidad, h.origen_ids) for h in r17] == [
        (Severidad.ADVERTENCIA, ("esp_puntos:P2",))
    ]
    assert "El punto P2 (lavamanos) no tiene fuente" in r17[0].descripcion
    assert vivo.borrador.reglas_extra == ()  # no se guarda en el borrador


# --- 3b-3 · vista de los precios con su origen (R12) ----------------------------------------------


def _fila_de_precio(**campos) -> hoja.FilaPrecio:
    base = {
        "codigo": "INS-1",
        "descripcion": "Cemento gris",
        "tipo": "material",
        "precio": D("1000"),
        "lista": "Lista demo",
        "moneda": "Bs",
        "fecha": date(2026, 7, 1),
        "tasa": D("633.3644"),
        "fecha_tasa": date(2026, 7, 1),
        "referencia": "MaPreX jul-2026",
        "cotizacion": "",
        "alcance": "global",
        "estado": "OK",
        "moneda_original": "Bs",
        "precio_original": D("1000"),
        "fuente_tasa": "MaPreX",
        "fuente": "MaPreX jul-2026",
        "propio": True,
    }
    return hoja.FilaPrecio(**{**base, **campos})


def test_la_erosion_de_la_memoria_s1_se_ve_en_dos_decimales_y_exacta():
    """Memoria S1 §9.1.1: erosión 0,4163… USD, 358,1123… Bs y 26,3683…% (P = 1 000 Bs)."""
    fila = _fila_de_precio(
        erosion_usd=D("0.416322546891039049840245251"),
        erosion_bs=D("358.112328384733969891582160"),
        erosion_pct=D("0.2636838801181148131786370295"),
    )
    v = hoja_vista.vista_precios([fila], "Bs", date(2026, 10, 1))
    f = v.filas[0]
    assert (f.erosion_usd.texto, f.erosion_usd.exacto) == ("0.42", "0.416322546891039049840245251")
    assert (f.erosion_bs.texto, f.erosion_bs.exacto) == ("358.11", "358.112328384733969891582160")
    # el porcentaje se muestra multiplicado por 100 (la clásica: `erosion_pct * 100`)
    assert (f.erosion_pct.texto, f.erosion_pct.exacto) == ("26.37", "26.36838801181148131786370295")
    assert (f.precio.texto, f.precio.exacto, f.tasa.exacto) == ("1000.00", "1000", "633.3644")
    assert (f.fecha_precio, f.fecha_tasa, f.propio) == ("2026-07-01", "2026-07-01", "propio")
    assert (v.moneda, v.fecha_evaluacion) == ("Bs", "2026-10-01")


def test_sin_evaluacion_la_erosion_y_la_tasa_vacias_son_nulas():
    fila = _fila_de_precio(tasa=None, fecha_tasa=None, propio=None, precio_original=None)
    f = hoja_vista.vista_precios([fila], "Bs", HOY).filas[0]
    assert (f.erosion_usd, f.erosion_bs, f.erosion_pct, f.erosion_indice) == (None,) * 4
    assert (f.tasa, f.fecha_tasa, f.precio_original, f.propio) == (None, None, None, "")


def test_un_precio_heredado_de_la_lista_de_empresa_dice_heredado():
    f = hoja_vista.vista_precios([_fila_de_precio(propio=False)], "Bs", HOY).filas[0]
    assert f.propio == "heredado"


def test_las_columnas_de_precios_son_las_21_con_sus_rotulos():
    columnas = hoja_vista.vista_precios([], "USD", HOY).columnas
    assert [c.rotulo for c in columnas] == [
        "Insumo", "Código", "Tipo", "Precio", "Lista", "Moneda", "Fecha del precio", "Tasa",
        "Fecha de la tasa", "Referencia", "Cotización", "Moneda original", "Precio original",
        "Fuente de la tasa", "Fuente", "Propio/heredado", "Erosión USD", "Erosión Bs",
        "Erosión %", "Erosión por índice", "Estado",
    ]  # fmt: skip
    assert [c.clave for c in columnas if c.numerica] == [
        "precio", "tasa", "precio_original", "erosion_usd", "erosion_bs", "erosion_pct",
        "erosion_indice",
    ]  # fmt: skip
