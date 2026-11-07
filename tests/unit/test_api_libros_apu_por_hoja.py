"""F5 vial, tarea 6: `POST /v1/libros/apu-por-hoja`, auditar el libro con un APU por hoja.

La ruta vive en el router de `/v1/libros` (clave o sesión que arma o revisa, `LEER_PROYECTO`) y
recibe en multipart el libro de APU (`libro`, obligatorio), el de presupuesto (`presupuesto`,
opcional) y el nombre del perfil (`perfil`, opcional: por omisión `apu_por_hoja`, local de la
instalación o del paquete). Todo en memoria: nada se guarda. Los montos viajan como texto.

Libros FICTICIOS de `tests/fixtures/libro_apu_por_hoja.py`; los oráculos son los de su memoria.
"""

from __future__ import annotations

from tests.fixtures.libro_apu_por_hoja import libro_apu, libro_presupuesto
from tests.unit.test_api_libros_replica import (  # noqa: F401 (fixtures de pytest)
    _con_clave,
    _con_cuenta,
    _instalacion,
    _plantilla,
    _protegida,
    _sin_float,
)

RUTA = "/v1/libros/apu-por-hoja"


def _auditar(cliente, *, presupuesto: bool = False, **extra):
    archivos = {"libro": ("frente_ficticio.xlsx", libro_apu())}
    if presupuesto:
        archivos["presupuesto"] = ("presupuesto_ficticio.xlsx", libro_presupuesto())
    return cliente.post(RUTA, files=archivos, **extra)


def test_con_clave_responde_el_informe_del_libro_y_del_presupuesto():
    r = _auditar(_con_clave(), presupuesto=True)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert _sin_float(cuerpo)
    assert (cuerpo["perfil"], cuerpo["origen_perfil"]) == ("apu_por_hoja", "paquete")
    assert cuerpo["libro"]["nombre"] == "frente_ficticio.xlsx"
    assert cuerpo["presupuesto"] == "presupuesto_ficticio.xlsx"
    assert cuerpo["cumple"] is False
    assert cuerpo["por_severidad"] == {"INFO": 6, "ERROR": 2, "ADVERTENCIA": 3}
    assert cuerpo["apus"][0] == {
        "hoja": "APU 1",
        "numero": 1,
        "codigo": "VF-001",
        "descripcion": "Riego de adherencia ficticio",
        "unidad": "m2",
        "precio_impreso": "2.08",
        "precio_silice": "2.08",  # presentado a dos decimales por el servidor
        "precio_silice_exacto": "2.0777625",
        "celda_precio": "APU 1!G33",
    }
    assert cuerpo["apus"][3]["precio_silice"] is None
    assert cuerpo["apus"][3]["precio_impreso"] == "820.00"
    assert [h["celda"] for h in cuerpo["hallazgos"]][-3:] == [
        "PRESUPUESTO!E6",
        "PRESUPUESTO!F8",
        "PRESUPUESTO!A9",
    ]
    assert cuerpo["desperdicios"] == [
        {
            "descripcion": "Emulsión asfáltica ficticia",
            "unidad": "l",
            "cantidad_neta": "0.5",
            "desperdicio_pct": "4",
            "cantidad": "0.52",
        }
    ]


def test_sin_presupuesto_solo_las_hojas():
    cuerpo = _auditar(_con_clave()).json()
    assert cuerpo["presupuesto"] is None
    assert not any(h["celda"].startswith("PRESUPUESTO!") for h in cuerpo["hallazgos"])


def test_quien_revisa_audita_con_su_sesion():
    cliente, ficha = _con_cuenta("rita")
    assert _auditar(cliente, headers=_protegida(ficha)).status_code == 200


def test_un_perfil_que_no_existe_es_422():
    r = _auditar(_con_clave(), data={"perfil": "no_existe"})
    assert r.status_code == 422
    assert r.json()["detalle"] == "no existe el perfil 'no_existe'"


def test_un_libro_sin_hojas_de_apu_es_422_con_el_mensaje():
    r = _con_clave().post(RUTA, files={"libro": ("p.xlsx", libro_presupuesto())})
    assert r.status_code == 422
    assert "no tiene ninguna hoja de APU" in r.json()["detalle"]


def test_otra_extension_es_415():
    r = _con_clave().post(RUTA, files={"libro": ("frente.csv", b"a;b")})
    assert r.status_code == 415
