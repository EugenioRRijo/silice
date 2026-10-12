"""Auditoría de DXF, IDS del IFC y espacio como JSON (RF-89; spec S3 §11.1, §11.2, §6.2)."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import ezdxf
import pytest

from adapters.espacio import Espacio
from adapters.espacio.planos import ids as modulo_ids
from adapters.espacio.planos.auditoria_archivo import auditar_archivo, texto_del_informe
from adapters.espacio.planos.dxf import importar_dxf
from adapters.espacio.planos.ids import MENSAJE_SIN_MODULO, RUTA_IDS, auditar_ids
from adapters.espacio.planos.informe import EstadoImportacion, TipoItem
from adapters.espacio.serie import (
    LIMITE_AMBIENTES,
    LIMITE_PUNTOS,
    LIMITE_VERTICES_POR_TRAMO,
    LimiteExcedido,
    comprobar_limites,
    espacio_a_objeto,
    espacio_desde_objeto,
)
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.planos_ifc_ids import oficina_ifc4
from tests.fixtures.sin_extra import SinExtra

RAIZ = Path(__file__).resolve().parents[2]
OF001 = RAIZ / "tests" / "fixtures" / "planos" / "of001.dxf"


# --- DXF dañado (UC-14d) --------------------------------------------------------------------


def _dxf_con_tipo_de_linea_inexistente() -> bytes:
    """Un plano de la convención de capas con una línea de un tipo de línea que no existe: la
    biblioteca lo arregla al leer con recuperación."""
    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 6
    doc.layers.add("AMBIENTES")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (4, 0), (4, 3), (0, 3)], close=True,
                       dxfattribs={"layer": "AMBIENTES"})
    msp.add_line((0, 0), (1, 1), dxfattribs={"layer": "OTRA", "linetype": "NO_EXISTE"})
    flujo = io.StringIO()
    doc.write(flujo)
    return flujo.getvalue().encode("utf-8")


def test_un_plano_limpio_no_tiene_nada_que_reparar() -> None:
    _, auditoria = auditar_archivo(OF001)
    assert auditoria.limpia and texto_del_informe(auditoria) == []


def test_of001_importa_igual_que_antes_sin_items_nuevos() -> None:
    importado = importar_dxf(OF001)
    assert importado.estado is EstadoImportacion.IMPORTADA
    assert importado.conteos[TipoItem.APROXIMADO] == 9  # los 9 de siempre, ninguno de auditoría
    assert not [i for i in importado.informe if i.tabla == "dxf"]


def test_lo_que_ezdxf_repara_se_informa_y_el_plano_se_importa() -> None:
    importado = importar_dxf(_dxf_con_tipo_de_linea_inexistente(), unidades="m")
    reparado = [i for i in importado.informe if i.tabla == "dxf"]
    assert importado.estado is EstadoImportacion.IMPORTADA
    assert len(reparado) == 1 and reparado[0].tipo is TipoItem.APROXIMADO
    assert "se repararon" in reparado[0].mensaje and "no_existe" in reparado[0].mensaje.lower()


def test_un_archivo_irrecuperable_se_rechaza_con_su_mensaje_y_sin_traza() -> None:
    rechazado = importar_dxf(b"\x00\x01 esto no es un DXF " * 20, nombre="malo.dxf")
    assert rechazado.estado is EstadoImportacion.RECHAZADA
    assert "malo.dxf: no se pudo leer como DXF" in rechazado.mensaje
    assert "Traceback" not in rechazado.mensaje and len(rechazado.mensaje) < 300


def test_el_informe_cuenta_los_errores_y_cita_solo_los_primeros() -> None:
    from adapters.espacio.planos.auditoria_archivo import Auditoria

    texto = texto_del_informe(Auditoria(reparaciones=tuple(f"fallo {i}" for i in range(8))))[0]
    assert texto.startswith("el plano tenia 8 errores de estructura que se repararon")
    assert "fallo 4" in texto and "fallo 5" not in texto and "(y 3 mas)" in texto


# --- IDS del IFC ---------------------------------------------------------------------------


def test_el_ids_versionado_es_el_que_genera_el_script() -> None:
    resultado = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "generar_ids_silice.py"), "--comprobar"],
        capture_output=True, text=True, cwd=RAIZ, check=False,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_un_ifc_que_cumple_todo_no_da_items() -> None:
    assert auditar_ids(oficina_ifc4()) == ()


def test_sin_ninguna_propiedad_fallan_los_cuatro_requisitos_con_su_global_id() -> None:
    items = auditar_ids(oficina_ifc4(con=()))
    por_requisito = {}
    for i in items:
        por_requisito.setdefault(i.mensaje.split("»")[0], []).append(i)
    assert {k: len(v) for k, v in por_requisito.items()} == {
        "IDS «Aparato sanitario con diametro": 1,
        "IDS «Espacio con altura": 3,
        "IDS «Tomacorriente con circuito": 1,
    }  # el tablero ya trae su nombre
    assert all(i.tipo is TipoItem.PENDIENTE and i.tabla == "ids" and i.referencia for i in items)
    assert any("lavamanos" in i.mensaje for i in items)


@pytest.mark.parametrize(
    "falta,fragmento",
    [("altura", "Espacio con altura"), ("diametro", "Aparato sanitario"),
     ("circuito", "Tomacorriente")],
)
def test_un_fallo_por_requisito(falta: str, fragmento: str) -> None:
    con = tuple(r for r in ("altura", "diametro", "circuito") if r != falta)
    items = auditar_ids(oficina_ifc4(con=con))
    assert items and all(fragmento in i.mensaje for i in items)


def test_sin_el_modulo_ifc_el_informe_lo_dice_y_no_falla(monkeypatch) -> None:
    """El extra `ifc` ausente de verdad (INV-021): `import ifctester` falla y la importación
    del IFC sigue."""
    modelo = oficina_ifc4()
    with SinExtra(monkeypatch, ("ifctester",), ("ifctester", "ifctester.ids")):
        assert not modulo_ids.ids_disponible()
        [item] = auditar_ids(modelo)
    assert item.mensaje == MENSAJE_SIN_MODULO and modulo_ids.ids_disponible()


def test_un_ifc2x3_recibe_un_item_que_dice_que_el_ids_es_de_ifc4() -> None:
    from tests.fixtures.planos_ifc import crear_ifc

    [item] = auditar_ids(crear_ifc("IFC2X3"))
    assert "solo cubre IFC4" in item.mensaje and "IFC2X3" in item.mensaje


def test_el_ids_existe_y_ifctester_se_importa_de_forma_diferida() -> None:
    assert RUTA_IDS.is_file()
    codigo = "import sys; import adapters.espacio.planos.ids; print('ifctester' in sys.modules)"
    salida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True,
                            cwd=RAIZ, check=True)
    assert salida.stdout.strip() == "False"


# --- el espacio como JSON ------------------------------------------------------------------


def test_el_espacio_de_of001_hace_ida_y_vuelta_exacta() -> None:
    original = espacio_of001()
    objeto = json.loads(json.dumps(espacio_a_objeto(original)))  # pasa por JSON de verdad
    assert espacio_desde_objeto(objeto) == original
    assert Espacio() == espacio_desde_objeto(json.loads(json.dumps(espacio_a_objeto(Espacio()))))


def test_las_cifras_del_espacio_se_validan_con_la_funcion_que_se_inyecta() -> None:
    from seguridad.json_estricto import JsonRechazado, a_decimal

    objeto = espacio_a_objeto(espacio_of001())
    assert espacio_desde_objeto(objeto, a_decimal) == espacio_of001()
    objeto["ambientes"][0]["largo"] = "1E+5"
    with pytest.raises(JsonRechazado):
        espacio_desde_objeto(objeto, a_decimal)
    assert Decimal("1E+5") == Decimal(100000)  # el Decimal corriente sí la tragaría


@pytest.mark.parametrize(
    "clave,tope", [("ambientes", LIMITE_AMBIENTES), ("puntos", LIMITE_PUNTOS)]
)
def test_los_limites_del_anexo_de_espacio_en_su_frontera(clave: str, tope: int) -> None:
    comprobar_limites({clave: [{}] * tope})  # pasa
    with pytest.raises(LimiteExcedido, match=str(tope)):
        comprobar_limites({clave: [{}] * (tope + 1)})


def test_mil_vertices_por_tramo_pasan_y_mil_uno_se_rechaza() -> None:
    def con(n: int) -> dict:
        return {"recorridos": [{"tramos": [{"vertices": [["0", "0", "0"]] * n}]}]}

    comprobar_limites(con(LIMITE_VERTICES_POR_TRAMO))
    with pytest.raises(LimiteExcedido, match="vertices"):
        comprobar_limites(con(LIMITE_VERTICES_POR_TRAMO + 1))


def test_un_anexo_incompleto_es_un_value_error_con_mensaje() -> None:
    with pytest.raises(ValueError, match="incompleto"):
        espacio_desde_objeto({"ambientes": [{"id": "A"}]})


def test_la_importacion_del_ifc_trae_los_items_del_ids_con_el_globalid() -> None:
    from adapters.espacio.planos.ifc import importar_ifc

    contenido = oficina_ifc4(con=("altura", "circuito")).to_string().encode("utf-8")
    importado = importar_ifc(contenido, nombre="oficina.ifc")
    ids = [i for i in importado.informe if i.mensaje.startswith("IDS «")]
    assert ids and all("Aparato sanitario con diametro" in i.mensaje for i in ids)
    assert all(i.tipo is TipoItem.PENDIENTE and i.referencia for i in ids)  # con su GlobalId


def test_un_ids_ilegible_no_tumba_la_importacion_y_se_dice(tmp_path) -> None:
    vacio = tmp_path / "vacio.ids"
    vacio.write_bytes(b"")
    [item] = auditar_ids(oficina_ifc4(), vacio)
    assert item.mensaje.startswith("IDS no comprobado: ") and item.tipo is TipoItem.PENDIENTE
