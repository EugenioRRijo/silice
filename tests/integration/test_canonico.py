"""SL-E8: el documento canónico de una versión, su vector escrito a mano y su ida y vuelta
(RF-83, RF-85; spec S3 §6.1 y §13.1).

Oráculo: `tests/fixtures/canonico/ejemplo_v1.py`, escrito a mano en S3-0 (tarea 2) con su huella
calculada aparte (2271 bytes, SHA-256 `b4b952dd…3936`), antes de que existiera
`core/budget/canonico.py`. Nunca se regenera con `documento()`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from core import models
from core.budget import canonico
from core.catalog import abrir_sesion, crear_esquema
from core.catalog.sesion import _activar_claves_foraneas
from core.contracts.apu import ParametrosCosto
from seguridad.json_estricto import PATRON_CIFRA as PATRON_DEL_LECTOR
from seguridad.json_estricto import leer_json
from tests.fixtures.canonico.ejemplo_v1 import BYTES_EJEMPLO_V1, EJEMPLO_V1, HUELLA_EJEMPLO_V1
from tests.fixtures.canonico_minimo import RELLENO, guardar_otra, sembrar_minimo


@pytest.fixture
def minimo(motor):
    with abrir_sesion(motor) as sesion:
        proyecto, version, lista = sembrar_minimo(sesion)
        sesion.commit()
        yield sesion, proyecto, version, lista


def test_el_vector_escrito_a_mano_tiene_la_huella_literal() -> None:
    """La huella se calculó aparte con `sha256sum` sobre estos mismos bytes; aquí se recalcula
    con `json` y `hashlib` estándar, sin el módulo bajo prueba, y luego con él."""
    independiente = json.dumps(
        EJEMPLO_V1, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert len(independiente) == BYTES_EJEMPLO_V1 == 2271
    assert hashlib.sha256(independiente).hexdigest() == HUELLA_EJEMPLO_V1
    datos = canonico.json_canonico(EJEMPLO_V1)
    assert datos == independiente
    assert canonico.huella(datos) == HUELLA_EJEMPLO_V1


def test_documento_de_la_version_sembrada_da_exactamente_los_bytes_del_vector(minimo) -> None:
    sesion, _, version, _ = minimo
    datos = canonico.documento(sesion, version)
    assert len(datos) == BYTES_EJEMPLO_V1
    assert datos == canonico.json_canonico(EJEMPLO_V1)
    assert hashlib.sha256(datos).hexdigest() == HUELLA_EJEMPLO_V1


def test_guardar_y_recargar_no_cambia_la_huella(motor, minimo) -> None:
    sesion, _, version, _ = minimo
    antes = canonico.huella(canonico.documento(sesion, version))
    sesion.expire_all()
    with abrir_sesion(motor) as otra:
        recargada = otra.get(models.Presupuesto, version.id)
        assert canonico.huella(canonico.documento(otra, recargada)) == antes == HUELLA_EJEMPLO_V1


def test_dos_bases_distintas_dan_los_mismos_bytes_aunque_cambien_los_ids(motor) -> None:
    """Determinismo entre instalaciones: la segunda base tiene antes otra lista y otro proyecto,
    así que los `id` de fila difieren, pero el documento no los lleva."""
    with abrir_sesion(motor) as sesion:
        _, version, lista = sembrar_minimo(sesion)
        sesion.commit()
        uno = canonico.documento(sesion, version)
        ids_uno = (version.id, version.proyecto_id, lista.id)
    otro_motor = create_engine("sqlite://", poolclass=StaticPool)
    event.listen(otro_motor, "connect", _activar_claves_foraneas)
    crear_esquema(otro_motor)
    try:
        with abrir_sesion(otro_motor) as sesion:
            sesion.add(models.Proyecto(nombre="PREVIO", descripcion="", dominio="civil"))
            sesion.add(
                models.ListaPrecios(
                    nombre="Previa", moneda="USD", fecha_vigencia=date(2026, 1, 1), origen="x"
                )
            )
            sesion.flush()
            _, version, lista = sembrar_minimo(sesion)
            sesion.commit()
            dos = canonico.documento(sesion, version)
            ids_dos = (version.id, version.proyecto_id, lista.id)
    finally:
        otro_motor.dispose()
    assert ids_dos != ids_uno
    assert dos == uno


def test_el_documento_no_lleva_ningun_id_de_fila(minimo) -> None:
    sesion, _, version, _ = minimo
    texto = canonico.documento(sesion, version).decode("utf-8")
    for clave in ("id", "proyecto_id", "presupuesto_id", "lista_id", "insumo_id", "partida_id"):
        assert f'"{clave}":' not in texto


def test_el_documento_no_cambia_al_leer_dos_veces_y_tiene_las_claves_ordenadas(minimo) -> None:
    sesion, _, version, _ = minimo
    uno = canonico.documento(sesion, version)
    assert canonico.documento(sesion, version) == uno
    assert list(json.loads(uno)) == sorted(json.loads(uno))
    # sin espacios entre elementos: reserializar sin separadores con espacio da los mismos bytes
    compacto = json.dumps(
        json.loads(uno), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert compacto == uno and b'", "' not in uno and b'": ' not in uno


def test_el_documento_va_en_utf8_sin_escapar(motor) -> None:
    with abrir_sesion(motor) as sesion:
        proyecto, version, _ = sembrar_minimo(sesion)
        proyecto.nombre = "Obra Ñandú"
        sesion.commit()
        datos = canonico.documento(sesion, version)
    assert "Obra Ñandú".encode() in datos
    assert b"\\u00d1" not in datos


def test_leer_es_la_inversa_de_documento(minimo) -> None:
    sesion, _, version, _ = minimo
    leido = canonico.leer(leer_json(canonico.documento(sesion, version)))
    assert (leido.codigo, leido.moneda, leido.proyecto, leido.moneda_proyecto) == (
        "001",
        "USD",
        "MIN-001",
        None,
    )
    assert leido.parametros == ParametrosCosto()
    assert leido.composiciones["MIN-001"] == RELLENO
    assert leido.items[0].cantidad == Decimal("20") and leido.items[0].origen_id == "FILA-1"
    declarado = leido.declarados[0]
    # literales de la memoria a mano (docstring de ejemplo_v1.py)
    assert declarado.materiales == Decimal("14.0000")
    assert declarado.equipos == Decimal("0.8875")
    assert declarado.mano_obra == Decimal("18.1875")
    assert declarado.costo_directo == Decimal("33.0750")
    assert declarado.con_administracion == Decimal("38.036250")
    assert declarado.precio_unitario == Decimal("41.83987500")
    assert declarado.total == Decimal("836.79750000")
    assert tuple(leido.plan) == (("Dia 1", (("MIN-001", Decimal("1")),)),)
    assert leido.curva[0].acumulado == Decimal("836.79750000")
    assert [linea.insumo for linea in leido.lineas["MIN-001"]] == ["MAT-001", "EQU-001", "MO-001"]
    assert leido.lineas["MIN-001"][0].precio_origen["moneda_original"] == "USD"
    assert leido.pendientes == () and leido.hallazgos == ()


def test_los_ceros_a_la_derecha_se_conservan(minimo) -> None:
    sesion, _, version, _ = minimo
    renglon = json.loads(canonico.documento(sesion, version))["renglones"][0]
    assert renglon["materiales"] == "14.0000" and renglon["precio_unitario"] == "41.83987500"


def test_un_decimal_con_exponente_se_escribe_posicional() -> None:
    assert canonico.texto_decimal(Decimal("1E+3")) == "1000"
    assert canonico.texto_decimal(Decimal("0.00001")) == "0.00001"
    assert canonico.texto_decimal(Decimal("1.50")) == "1.50"
    assert canonico.texto_decimal(None) is None


@pytest.mark.parametrize(
    "cambio",
    [
        lambda d: d.update(formato="otro"),
        lambda d: d.update(version_formato=2),
        lambda d: d.pop("renglones"),
        lambda d: d["parametros"].update(fcas="1E+5"),
        lambda d: d["renglones"][0]["item"].update(cantidad="1,5"),
        lambda d: d["renglones"][0].update(total=836.7975),
        lambda d: d["renglones"][0].update(total="1" * 21),
        lambda d: d["renglones"][0].update(precio_unitario="0." + "1" * 29),
        lambda d: d["composiciones"][0]["lineas"][0].update(tipo="inventado"),
        lambda d: d["curva"][0].update(monto="NaN"),
    ],
    ids=[
        "formato",
        "version_formato",
        "sin_renglones",
        "exponente",
        "coma_decimal",
        "float_no_texto",
        "21_enteros",
        "29_decimales",
        "tipo_inventado",
        "nan",
    ],
)
def test_un_documento_mal_formado_se_rechaza_con_un_mensaje(minimo, cambio) -> None:
    sesion, _, version, _ = minimo
    objeto = json.loads(canonico.documento(sesion, version))
    cambio(objeto)
    with pytest.raises(canonico.DocumentoInvalido):
        canonico.leer(objeto)


def test_las_cifras_en_la_frontera_del_patron_se_leen(minimo) -> None:
    """20 enteros y 28 decimales pasan (RP8-13); uno más se rechaza (prueba de arriba)."""
    sesion, _, version, _ = minimo
    objeto = json.loads(canonico.documento(sesion, version))
    objeto["renglones"][0]["total"] = "9" * 20
    objeto["renglones"][0]["precio_unitario"] = "0." + "1" * 28
    leido = canonico.leer(objeto)
    assert leido.declarados[0].total == Decimal("9" * 20)
    assert leido.declarados[0].precio_unitario == Decimal("0." + "1" * 28)


def test_el_patron_de_cifras_es_el_del_lector_estricto() -> None:
    """`core` no puede importar `seguridad`: el patrón vive en los dos y no puede divergir."""
    assert canonico.PATRON_CIFRA.pattern == PATRON_DEL_LECTOR.pattern


def test_contar_filas_suma_renglones_y_lineas(minimo) -> None:
    sesion, _, version, _ = minimo
    assert canonico.contar_filas(json.loads(canonico.documento(sesion, version))) == 1 + 3
    assert canonico.contar_filas({"renglones": "no"}) == 0
    assert canonico.contar_filas({}) == 0


def test_la_moneda_del_proyecto_sigue_el_orden_de_creacion_y_no_la_fecha(minimo) -> None:
    sesion, proyecto, v1, lista = minimo
    sesion.add(
        models.MonedaProyecto(
            proyecto_id=proyecto.id,
            moneda="USD",
            desde=datetime(2026, 11, 1, 9, 0),
            version_id=None,
            responsable="ana",
            fuente="al crear",
        )
    )
    sesion.commit()
    antes = canonico.documento(sesion, v1)
    assert json.loads(antes)["moneda_proyecto"] == "USD"
    v2 = guardar_otra(sesion, proyecto, lista, "002")
    sesion.add(
        models.MonedaProyecto(
            proyecto_id=proyecto.id,
            moneda="Bs",
            desde=datetime(2026, 11, 1, 9, 0),
            version_id=v2.id,
            responsable="ana",
            fuente="conversion",
        )
    )
    sesion.commit()
    # misma fecha de calendario, pero la conversión nació con v2: v1 NO cambia
    assert canonico.documento(sesion, v1) == antes
    assert json.loads(canonico.documento(sesion, v2))["moneda_proyecto"] == "Bs"


def test_una_declaracion_posterior_a_la_version_no_cambia_su_documento(minimo) -> None:
    sesion, proyecto, v1, _ = minimo
    antes = canonico.documento(sesion, v1)  # la versión es del 2026-11-01 y no hay declaración
    sesion.add(
        models.MonedaProyecto(
            proyecto_id=proyecto.id,
            moneda="USD",
            desde=datetime(2026, 11, 2, 0, 0),  # frontera: el día siguiente a la versión
            version_id=None,
            responsable="ana",
            fuente="declarada despues",
        )
    )
    sesion.commit()
    assert canonico.documento(sesion, v1) == antes
    assert json.loads(antes)["moneda_proyecto"] is None


def test_una_declaracion_del_mismo_dia_de_la_version_si_rige(minimo) -> None:
    """Frontera de `_moneda_del_proyecto`: `desde.date() <= fecha` incluye el mismo día."""
    sesion, proyecto, v1, _ = minimo
    sesion.add(
        models.MonedaProyecto(
            proyecto_id=proyecto.id,
            moneda="USD",
            desde=datetime(2026, 11, 1, 23, 59),
            version_id=None,
            responsable="ana",
            fuente="el mismo dia",
        )
    )
    sesion.commit()
    assert json.loads(canonico.documento(sesion, v1))["moneda_proyecto"] == "USD"
