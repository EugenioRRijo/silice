"""Importacion de IFC (spec §6.6.2, RF-51, RNF-12, tarea 5.3).

Los IFC de prueba son PROGRAMATICOS (`tests/fixtures/planos_ifc.py`, `ifcopenshell.api`): la prueba
demuestra que el importador lee lo que el esquema declara, no que lea el export de un programa de
modelado concreto (salvedad heredada de RNF-09, declarada en `tests/fixtures/planos/README.md`).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import ifcopenshell
import ifcopenshell.ifcopenshell_wrapper as wrapper
import pytest

from adapters.espacio import Espacio, SuperficiePunto, TipoFuente, TipoOrigen
from adapters.espacio.planos.ifc import CLASES_POR_ESQUEMA, LIMITE_BYTES, importar_ifc
from adapters.espacio.planos.informe import EstadoImportacion, TipoItem, fusionar
from tests.fixtures.planos_ifc import ESQUEMAS, crear_ifc

D = Decimal
TANQUILLA = Path(__file__).resolve().parents[2] / "data" / "samples" / "tanquilla.ifc"


def contenido(esquema: str, milimetros: bool = False) -> bytes:
    return crear_ifc(esquema, milimetros).to_string().encode("utf-8")


def tipos(resultado, tipo):
    return [i for i in resultado.informe if i.tipo is tipo]


def por_id(filas):
    return {f.id: f for f in filas}


# --- las clases por esquema son las del esquema ----------


@pytest.mark.parametrize("esquema", ESQUEMAS)
def test_cada_clase_que_se_lee_existe_en_su_esquema_con_sus_valores_de_enumeracion(esquema):
    schema = wrapper.schema_by_name(esquema)
    clases = CLASES_POR_ESQUEMA[esquema]
    assert clases, esquema
    for clase in clases.entidades:
        schema.declaration_by_name(clase)  # lanza si la clase no existe en el esquema
    for tipo_ifc, enumeracion, valores in clases.valores_de_tipo:
        items = schema.declaration_by_name(enumeracion).enumeration_items()
        assert set(valores) <= set(items), (esquema, tipo_ifc, valores)


def test_ifc2x3_no_inventa_clases_que_solo_tiene_ifc4():
    schema = wrapper.schema_by_name("IFC2X3")
    for clase in (
        "IfcSanitaryTerminal",
        "IfcOutlet",
        "IfcLightFixture",
        "IfcElectricDistributionBoard",
    ):
        with pytest.raises(RuntimeError):
            schema.declaration_by_name(clase)
        assert clase not in CLASES_POR_ESQUEMA["IFC2X3"].entidades


# --- ambientes y terminales ----------


@pytest.mark.parametrize("milimetros", [False, True], ids=["metros", "milimetros"])
@pytest.mark.parametrize("esquema", ESQUEMAS)
def test_los_ambientes_salen_de_los_espacios_con_su_caja_y_su_altura(esquema, milimetros):
    r = importar_ifc(contenido(esquema, milimetros), nombre="of.ifc")
    assert r.estado is EstadoImportacion.IMPORTADA and r.formato == "ifc"
    a = por_id(r.ambientes)
    assert set(a) == {"SALA", "BANO", "SALON-L"}
    esperado = {
        "SALA": (0, 0, 4, 3, "2.8"),
        "BANO": (4, 0, 2, 3, "2.8"),
        "SALON-L": (10, 0, 6, 4, "3"),
    }
    for id_, (x0, y0, largo, ancho, alto) in esperado.items():
        fila = a[id_]
        for valor, buscado in zip(
            (fila.x0, fila.y0, fila.largo, fila.ancho, fila.alto),
            (x0, y0, largo, ancho, alto),
            strict=True,
        ):
            assert abs(valor - D(str(buscado))) <= D("0.001"), (id_, valor, buscado)


@pytest.mark.parametrize("esquema", ESQUEMAS)
def test_la_altura_del_ambiente_no_queda_pendiente_porque_el_ifc_la_trae(esquema):
    r = importar_ifc(contenido(esquema), nombre="of.ifc")
    assert not [i for i in tipos(r, TipoItem.PENDIENTE) if i.tabla == "esp_ambientes"]
    for a in r.ambientes:
        assert "altura" not in dict(r.origenes_por_id[a.origen_id].referencia)


@pytest.mark.parametrize("esquema", ESQUEMAS)
def test_un_espacio_no_rectangular_se_aproxima_por_su_caja_y_se_declara(esquema):
    r = importar_ifc(contenido(esquema), nombre="of.ifc")
    aproximados = [i for i in tipos(r, TipoItem.APROXIMADO) if i.tabla == "esp_ambientes"]
    assert [i.fila for i in aproximados] == ["SALON-L"]
    assert "caja envolvente" in aproximados[0].mensaje


def _puntos_esperados(esquema: str) -> dict[str, tuple]:
    esperados = {
        "lavamanos": ("agua_fria", "SALA", (D(1), D(0), D("0.8")), SuperficiePunto.PARED),
        "toma de datos": ("datos", "SALA", (D("3.5"), D(2), D("0.3")), SuperficiePunto.PARED),
        "toma de corriente": (
            "tomacorriente",
            "SALA",
            (D(2), D(3), D("0.3")),
            SuperficiePunto.PARED,
        ),
        "luminaria": ("iluminacion", "SALA", (D(2), D("1.5"), D("2.8")), SuperficiePunto.TECHO),
    }
    if esquema == "IFC4":
        esperados["desague"] = ("drenaje", "BANO", (D(5), D("1.5"), D(0)), SuperficiePunto.PISO)
    return esperados


@pytest.mark.parametrize("milimetros", [False, True], ids=["metros", "milimetros"])
@pytest.mark.parametrize("esquema", ESQUEMAS)
def test_los_terminales_salen_con_su_tipo_ambiente_y_cota_sobre_el_piso(esquema, milimetros):
    r = importar_ifc(contenido(esquema, milimetros), nombre="of.ifc")
    puntos = por_id(r.puntos)
    esperados = _puntos_esperados(esquema)
    assert set(puntos) == set(esperados)
    for id_, (tipo, ambiente, (x, y, z), superficie) in esperados.items():
        p = puntos[id_]
        assert (p.tipo.value, p.ambiente_id, p.superficie) == (tipo, ambiente, superficie)
        for valor, buscado in zip(
            (p.posicion.x, p.posicion.y, p.posicion.z), (x, y, z), strict=True
        ):
            assert abs(valor - buscado) <= D("0.001"), (id_, valor, buscado)


@pytest.mark.parametrize("esquema", ESQUEMAS)
def test_el_tablero_es_una_fuente_de_electricidad(esquema):
    r = importar_ifc(contenido(esquema), nombre="of.ifc")
    assert [(f.id, f.tipo, f.especialidad.value, f.ambiente_id) for f in r.fuentes] == [
        ("tablero", TipoFuente.TABLERO, "electricidad", "SALA")
    ]
    assert abs(r.fuentes[0].posicion.z - D("1.5")) <= D("0.001")


@pytest.mark.parametrize("esquema", ESQUEMAS)
def test_cada_fila_lleva_origen_ifc_con_archivo_y_global_id(esquema):
    modelo = crear_ifc(esquema)
    r = importar_ifc(modelo.to_string().encode("utf-8"), nombre="of.ifc")
    ids_del_archivo = {e.GlobalId for e in modelo.by_type("IfcRoot")}
    assert len(r.origenes) == len(r.ambientes) + len(r.fuentes) + len(r.puntos)
    for o in r.origenes:
        ref = dict(o.referencia)
        assert o.tipo is TipoOrigen.IFC and not o.incompleto
        assert ref["archivo"] == "of.ifc" and ref["global_id"] in ids_del_archivo
    espacio = {a.nombre: a for a in r.ambientes}["SALA"]
    espacio_ifc = next(e for e in modelo.by_type("IfcSpace") if e.Name == "SALA")
    assert (
        dict(r.origenes_por_id[espacio.origen_id].referencia)["global_id"] == espacio_ifc.GlobalId
    )


@pytest.mark.parametrize("esquema", ESQUEMAS)
def test_lo_que_no_se_reconoce_va_al_informe_agrupado_por_clase(esquema):
    r = importar_ifc(contenido(esquema), nombre="of.ifc")
    ajenos = {i.tabla: i for i in tipos(r, TipoItem.NO_RECONOCIDO)}
    assert "IfcWall" in ajenos and "1 elemento" in ajenos["IfcWall"].mensaje
    audiovisual = [i for i in tipos(r, TipoItem.NO_RECONOCIDO) if "AUDIOVISUALOUTLET" in i.mensaje]
    assert len(audiovisual) == 1
    assert "toma audiovisual" not in {p.nombre for p in r.puntos}


@pytest.mark.parametrize("esquema", ESQUEMAS)
def test_lo_que_el_ifc_no_declara_queda_pendiente_y_no_se_adivina(esquema):
    r = importar_ifc(contenido(esquema), nombre="of.ifc")
    mensajes = " | ".join(i.mensaje for i in tipos(r, TipoItem.PENDIENTE))
    assert "sin fuente" in mensajes  # el IFC no trae montante, colector ni rack
    assert "sin circuito" in mensajes  # ni circuitos
    assert all(p.fuente_id is None for p in r.puntos)
    assert r.circuitos == ()


def test_el_drenaje_de_un_aparato_sanitario_no_se_infiere():
    r = importar_ifc(contenido("IFC4"), nombre="of.ifc")
    assert [p.id for p in r.puntos if p.tipo.value == "drenaje"] == ["desague"]
    assert any("drenaje" in i.mensaje for i in tipos(r, TipoItem.PENDIENTE))


def test_un_ifc_sin_ninguna_clase_de_la_convencion_da_informe_y_ninguna_fila():
    assert TANQUILLA.is_file()
    r = importar_ifc(TANQUILLA)
    assert r.estado is EstadoImportacion.IMPORTADA
    assert r.espacio().vacio
    assert tipos(r, TipoItem.NO_RECONOCIDO)
    assert not tipos(r, TipoItem.IMPORTADO)


def test_dos_espacios_con_el_mismo_nombre_usan_el_global_id():
    modelo = crear_ifc("IFC4")
    for e in modelo.by_type("IfcSpace"):
        e.Name = "IGUAL"
    r = importar_ifc(modelo.to_string().encode("utf-8"), nombre="of.ifc")
    assert len(r.ambientes) == 3
    gids = {e.GlobalId for e in modelo.by_type("IfcSpace")}
    assert {a.id for a in r.ambientes} == gids


def test_un_terminal_fuera_de_todo_espacio_se_informa_y_no_crea_fila():
    modelo = crear_ifc("IFC4")
    lejos = modelo.by_type("IfcLightFixture")[0]
    import ifcopenshell.api.geometry
    import numpy as np

    m = np.eye(4)
    m[:3, 3] = (90.0, 90.0, 0.0)
    ifcopenshell.api.geometry.edit_object_placement(modelo, product=lejos, matrix=m)
    r = importar_ifc(modelo.to_string().encode("utf-8"), nombre="of.ifc")
    assert "luminaria" not in {p.id for p in r.puntos}
    assert any("fuera de todo ambiente" in i.mensaje for i in tipos(r, TipoItem.NO_RECONOCIDO))


# --- archivos malos (RNF-12) ----------


@pytest.mark.parametrize(
    "datos",
    [b"", b"hola mundo", b'{"no": "ifc"}', b"\x00\x01\x02", b"ISO-10303-21;\nHEADER;\nBASURA\n"],
    ids=["vacio", "texto", "json", "binario", "cabecera-sin-datos"],
)
def test_un_archivo_malformado_se_rechaza_con_mensaje_y_sin_traza(datos):
    r = importar_ifc(datos, nombre="malo.ifc")
    assert r.estado is EstadoImportacion.RECHAZADA
    assert r.espacio().vacio
    assert "malo.ifc" in r.mensaje and "IFC" in r.mensaje
    assert "Traceback" not in r.mensaje and "\n" not in r.mensaje


def test_un_ifc_truncado_se_rechaza():
    datos = contenido("IFC4")
    r = importar_ifc(datos[: len(datos) // 2], nombre="cortado.ifc")
    assert r.estado is EstadoImportacion.RECHAZADA


def test_un_archivo_de_mas_de_20_mb_se_rechaza():
    assert LIMITE_BYTES == 20 * 1024 * 1024
    r = importar_ifc(b"0" * (LIMITE_BYTES + 1), nombre="grande.ifc")
    assert r.estado is EstadoImportacion.RECHAZADA and "20 MB" in r.mensaje


def test_una_ruta_de_mas_de_20_mb_o_inexistente_se_rechaza(tmp_path):
    grande = tmp_path / "grande.ifc"
    grande.write_bytes(b"0" * (LIMITE_BYTES + 1))
    assert "20 MB" in importar_ifc(grande).mensaje
    r = importar_ifc(tmp_path / "no_esta.ifc")
    assert r.estado is EstadoImportacion.RECHAZADA and "no_esta.ifc" in r.mensaje


def test_la_ruta_y_los_bytes_dan_el_mismo_resultado(tmp_path):
    datos = contenido("IFC4")
    ruta = tmp_path / "of.ifc"
    ruta.write_bytes(datos)
    assert importar_ifc(ruta) == importar_ifc(datos, nombre="of.ifc")
    assert importar_ifc(str(ruta)) == importar_ifc(ruta)


def test_ifc4x3_hereda_las_clases_de_ifc4():
    modelo = ifcopenshell.file(schema="IFC4X3")
    r = importar_ifc(modelo.to_string().encode("utf-8"), nombre="x.ifc")
    assert r.estado is EstadoImportacion.IMPORTADA  # IFC4X3 hereda las clases de IFC4
    assert r.espacio().vacio


def test_importar_dos_veces_da_lo_mismo():
    datos = contenido("IFC4")
    assert importar_ifc(datos, nombre="of.ifc") == importar_ifc(datos, nombre="of.ifc")


# --- reimportacion por GlobalId ----------


def test_reimportar_el_ifc_editado_actualiza_agrega_y_marca_lo_que_desaparecio():
    modelo = crear_ifc("IFC4")
    primero, _ = fusionar(Espacio(), importar_ifc(modelo.to_string().encode(), nombre="of.ifc"))

    import ifcopenshell.api.geometry
    import ifcopenshell.api.root
    import numpy as np

    luminaria = modelo.by_type("IfcLightFixture")[0]
    m = np.eye(4)
    m[:3, 3] = (2.0, 2.5, 2.8)
    ifcopenshell.api.geometry.edit_object_placement(modelo, product=luminaria, matrix=m)
    ifcopenshell.api.root.remove_product(modelo, product=modelo.by_type("IfcWasteTerminal")[0])

    espacio, informe = fusionar(primero, importar_ifc(modelo.to_string().encode(), nombre="of.ifc"))
    puntos = por_id(espacio.puntos)
    assert abs(puntos["luminaria"].posicion.y - D("2.5")) <= D("0.001")
    assert "desague" in puntos  # no se borra
    assert [i.fila for i in informe if i.tipo is TipoItem.DESAPARECIDO] == ["desague"]
    marca = dict(
        next(o for o in espacio.origenes if o.id == puntos["desague"].origen_id).referencia
    )
    assert marca["importacion"] == "desaparecida"


def test_reimportar_el_mismo_ifc_no_cambia_nada():
    datos = contenido("IFC2X3")
    r = importar_ifc(datos, nombre="of.ifc")
    primero, _ = fusionar(Espacio(), r)
    segundo, informe = fusionar(primero, importar_ifc(datos, nombre="of.ifc"))
    assert segundo == primero
    assert not [i for i in informe if i.tipo in (TipoItem.DESAPARECIDO, TipoItem.OMITIDO)]


# --- RNF-12: tope de elementos tras abrir el archivo (revision SF5) ----------


def _elementos(datos: bytes) -> int:
    modelo = ifcopenshell.file.from_string(datos.decode("utf-8"))
    return len(modelo.by_type("IfcElement")) + len(modelo.by_type("IfcSpace"))


def test_un_ifc_con_mas_elementos_que_el_tope_se_rechaza_sin_traza():
    from adapters.espacio.planos.ifc import MAX_ELEMENTOS_IFC

    assert MAX_ELEMENTOS_IFC == 50_000
    datos = contenido("IFC4")
    n = _elementos(datos)
    assert n > 3
    r = importar_ifc(datos, nombre="denso.ifc", max_elementos=n - 1)
    assert r.estado is EstadoImportacion.RECHAZADA
    assert r.espacio().vacio
    assert "denso.ifc" in r.mensaje and "tope" in r.mensaje and str(n) in r.mensaje
    assert "Traceback" not in r.mensaje and "\n" not in r.mensaje


def test_un_ifc_con_exactamente_el_tope_de_elementos_se_importa():
    datos = contenido("IFC4")
    r = importar_ifc(datos, nombre="a.ifc", max_elementos=_elementos(datos))
    assert r.estado is EstadoImportacion.IMPORTADA


def test_el_tope_de_elementos_tambien_rige_para_una_ruta(tmp_path):
    ruta = tmp_path / "a.ifc"
    ruta.write_bytes(contenido("IFC2X3"))
    assert importar_ifc(ruta, max_elementos=2).estado is EstadoImportacion.RECHAZADA


def test_los_bytes_y_la_ruta_de_un_ifc_dan_el_mismo_resultado(tmp_path):
    """Al leer sin duplicar memoria (archivo directo) el resultado no cambia."""
    datos = contenido("IFC4")
    ruta = tmp_path / "a.ifc"
    ruta.write_bytes(datos)
    assert importar_ifc(ruta) == importar_ifc(datos, nombre="a.ifc")
