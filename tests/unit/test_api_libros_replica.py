"""`POST /v1/libros/replica` e `indicadores_de` (Sílice 1.2.0, Task 2.3b; RF-111, RF-116, RS2-5,
RS2-7).

La réplica se ejerce sobre `api.main.app` real (protección de red y de hosts, clave o sesión). La
instalación de la prueba lleva una clave de API y tres cuentas creadas por el camino real: `admin`
(administrador), `ana` (arma) y `rita` (revisa).

Oráculos, ninguno sale del código bajo prueba:

- El libro limpio de `tests/fixtures/libros_empresa.py`: el monto de APU-01 es el de la memoria
  de cálculo a mano (120 × 14,486725 = 1 738,407), el orden de las hojas es el que el generador
  escribe (`Construido.hojas`) y la huella se recalcula aquí con `hashlib`.
- Ancho de RESUMEN!A: el generador pide 36 caracteres y XlsxWriter guarda el ancho con el relleno
  de la fuente por omisión (7 px por carácter y 5 px de margen):
  trunc((36 × 7 + 5) ÷ 7 × 256) ÷ 256 = trunc(9 398,857…) ÷ 256 = 9 398 ÷ 256 = 36,7109375.
- Los mensajes de error son los literales de la guardia, del adaptador visual y de la sesión.
- `indicadores_de`: cuentas a mano en cada caso (Δ = actual − meta; Δ% = Δ ÷ meta × 100 en
  centésimas con redondeo al par).
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from adapters.hoja_empresa import visual
from api.main import app
from api.rutas import libros
from api.rutas.libros import IndicadorRespuesta, indicadores_de
from operacion import config
from operacion.base_datos import Destino, preparar_base
from seguridad import cuentas, sesiones
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import Usuario
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona
from tests.fixtures.libros_empresa import MEMORIA, libro_limpio

RUTA = "/v1/libros/replica"
NUEVA = "otra contrasena larga de prueba"
CUENTAS = {"admin": CONTRASENA, "ana": NUEVA, "rita": NUEVA}
COOKIE = "silice_sesion"
MENSAJE_LIBRO = "El libro no se pudo interpretar."
MENSAJE_SIN_SESION = "Sesión ausente o vencida: entre de nuevo con su cuenta."
MENSAJE_CSRF = "Falta la comprobación anti-CSRF de la sesión o no coincide."
MENSAJE_PERMISO = "Su cuenta no tiene permiso para esta acción."
SECRETO = "detalle-interno-que-no-debe-salir C:\\ruta\\secreta"


# --- Ayudas ---------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    """`instalacion.db` migrada con tres cuentas por el camino real (una vez por módulo)."""
    carpeta = tmp_path_factory.mktemp("plantilla_replica")
    plantilla = carpeta / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    motor = crear_motor(plantilla)
    sesion = abrir_sesion(motor)
    try:
        admin = administrador(sesion, carpeta)
        for login, roles in (("ana", ("arma",)), ("rita", ("revisa",))):
            usuario = persona(sesion, admin, login, roles)
            cuentas.cambiar_contrasena(sesion, usuario.id, CONTRASENA, NUEVA, AHORA)
        for usuario in sesion.scalars(select(Usuario)):
            sesiones.cerrar_todas(sesion, usuario.id, "plantilla")
        sesion.commit()
    finally:
        sesion.close()
        motor.dispose()
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path) -> Iterator[None]:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_plantilla, destino)
    cuentas.FRENO.reiniciar()
    yield
    cuentas.FRENO.reiniciar()


@pytest.fixture(scope="module")
def limpio():
    return libro_limpio()


def _cliente(**extra) -> TestClient:
    return TestClient(
        app, base_url=ANFITRION, client=IP_LOCAL, raise_server_exceptions=False, **extra
    )


def _con_clave() -> TestClient:
    return _cliente(headers={CABECERA: crear_clave_de_prueba()})


def _con_cuenta(login: str) -> tuple[TestClient, str]:
    cliente = _cliente()
    r = cliente.post("/v1/sesion", json={"login": login, "contrasena": CUENTAS[login]})
    assert r.status_code == 200, r.text
    ficha = r.cookies.get(COOKIE)
    assert ficha
    return cliente, ficha


def _csrf(ficha: str) -> str:
    return hashlib.sha256(("csrf:" + ficha).encode("utf-8")).hexdigest()


def _protegida(ficha: str) -> dict[str, str]:
    return {"X-Silice-CSRF": _csrf(ficha), "Origin": ANFITRION}


def _replica(cliente: TestClient, datos: bytes, nombre: str = "libro.xlsx", **extra):
    return cliente.post(RUTA, files={"libro": (nombre, datos)}, **extra)


def _sin_float(valor: object) -> bool:
    """True si ningún número del JSON es `float` (los montos viajan como texto)."""
    if isinstance(valor, float):
        return False
    if isinstance(valor, dict):
        return all(_sin_float(v) for v in valor.values())
    if isinstance(valor, list):
        return all(_sin_float(v) for v in valor)
    return True


# --- POST /v1/libros/replica ----------------------------------------------------------------


def test_replica_del_libro_limpio_trae_sus_hojas_y_el_monto_de_apu_01(limpio) -> None:
    r = _replica(_con_clave(), limpio.datos)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["nombre"] == "libro.xlsx"
    assert d["sha256"] == hashlib.sha256(limpio.datos).hexdigest()
    assert [h["nombre"] for h in d["hojas"]] == list(limpio.hojas)
    presupuesto = next(h for h in d["hojas"] if h["nombre"] == "PRESUPUESTO")
    ref = f"Q{limpio.filas_partida['APU-01']}"
    monto = next(c for c in presupuesto["celdas"] if c["ref"] == ref)
    assert monto["mostrado"] == "1738.407"
    assert (
        Decimal(monto["mostrado"]) == MEMORIA["montos"][1] == Decimal("120") * Decimal("14.486725")
    )
    assert monto["formula"].startswith("=")
    assert (monto["fila"], monto["columna"]) == (limpio.filas_partida["APU-01"], 17)  # Q = 17
    assert 0 <= monto["estilo"] < len(d["estilos"])
    assert _sin_float(d)


def test_replica_anchos_y_altos_con_la_columna_en_texto(limpio) -> None:
    d = _replica(_con_clave(), limpio.datos).json()
    resumen = next(h for h in d["hojas"] if h["nombre"] == "RESUMEN")
    # 36 y 16 caracteres pedidos: trunc((n × 7 + 5) ÷ 7 × 256) ÷ 256 (ver la cabecera).
    assert resumen["anchos"] == {"1": "36.7109375", "2": "16.7109375"}
    for hoja in d["hojas"]:
        for mapa in (hoja["anchos"], hoja["altos"]):
            assert all(k.isdigit() and isinstance(v, str) for k, v in mapa.items())
    estilo = d["estilos"][0]
    assert set(estilo) == {
        "relleno",
        "fuente",
        "tamano",
        "negrita",
        "cursiva",
        "subrayado",
        "color",
        "alineacion_h",
        "alineacion_v",
        "ajustar_texto",
        "formato_numero",
        "bordes",
    }
    assert len(estilo["bordes"]) == 4


def test_replica_no_pide_fecha_de_devolucion_ni_toca_la_base_del_proyecto(limpio) -> None:
    """Solo `libro`: la réplica no audita, así que no necesita la fecha ni el contexto de
    precios."""
    assert _replica(_con_clave(), limpio.datos).status_code == 200


@pytest.mark.parametrize("nombre", ["libro.txt", "libro.xlsm", ".xlsx"])
def test_replica_rechaza_lo_que_no_es_xlsx_con_415(limpio, nombre: str) -> None:
    r = _replica(_con_clave(), limpio.datos, nombre=nombre)
    assert r.status_code == 415, r.text
    assert r.json() == {
        "detalle": f"'libro' debe ser un archivo .xlsx (se recibió «{nombre}»). Solo se aceptan "
        "libros de Excel .xlsx sin macros."
    }


def test_replica_de_mas_del_tope_da_413(limpio, monkeypatch) -> None:
    """La lectura por bloques de `_leer` corta en `TOPE_BYTES` (aquí, uno menos que el libro)."""
    monkeypatch.setattr(libros, "TOPE_BYTES", len(limpio.datos) - 1)
    r = _replica(_con_clave(), limpio.datos)
    assert r.status_code == 413, r.text
    assert r.json()["detalle"].startswith("'libro' supera el máximo de ")


def test_replica_de_un_zip_roto_da_422(limpio) -> None:
    roto = limpio.datos[: len(limpio.datos) // 2]  # sin el directorio central del zip
    r = _replica(_con_clave(), roto, nombre="roto.xlsx")
    assert r.status_code == 422, r.text
    assert r.json() == {
        "detalle": "El archivo «roto.xlsx» no es un libro .xlsx válido (está dañado o no es "
        "de Excel)."
    }


def test_replica_de_un_libro_demasiado_grande_da_422_con_su_mensaje(limpio, monkeypatch) -> None:
    monkeypatch.setattr(visual, "MAX_CELDAS_VISUALES", 10)
    r = _replica(_con_clave(), limpio.datos)
    assert r.status_code == 422, r.text
    assert r.json() == {
        "detalle": "El libro tiene más de 10 celdas con valor o formato; es demasiado grande "
        "para mostrarlo en el visor."
    }


def test_fallo_interno_de_la_replica_da_500_con_mensaje_fijo(limpio, monkeypatch, caplog) -> None:
    def _revienta(*_a, **_k):
        raise RuntimeError(SECRETO)

    monkeypatch.setattr(libros, "replicar_libro", _revienta)
    r = _replica(_con_clave(), limpio.datos)
    assert r.status_code == 500
    assert r.json() == {"detalle": MENSAJE_LIBRO}
    assert "detalle-interno" not in r.text and "RuntimeError" not in r.text
    assert any("RuntimeError" in m and RUTA in m for m in caplog.messages)


# --- Acceso: clave o sesión (RS2-5) ---------------------------------------------------------


def test_replica_sin_nada_da_401(limpio, monkeypatch) -> None:
    llamadas: list[int] = []
    monkeypatch.setattr(libros, "replicar_libro", lambda *a, **k: llamadas.append(1))
    r = _replica(_cliente(), limpio.datos)
    assert r.status_code == 401
    assert r.json() == {"detalle": MENSAJE_SIN_SESION}
    assert llamadas == []


def test_replica_con_una_clave_mala_da_401_de_la_clave(limpio) -> None:
    r = _replica(_cliente(headers={CABECERA: "AB12CD34.no-es-la-clave"}), limpio.datos)
    assert r.status_code == 401
    assert r.json() == {"detalle": "Clave de API ausente, desconocida o revocada."}


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_replica_con_cookie_y_csrf_pasa(limpio, login: str) -> None:
    cliente, ficha = _con_cuenta(login)
    r = _replica(cliente, limpio.datos, headers=_protegida(ficha))
    assert r.status_code == 200, r.text
    assert [h["nombre"] for h in r.json()["hojas"]] == list(limpio.hojas)


def test_replica_con_cookie_sin_csrf_da_403(limpio) -> None:
    cliente, _ = _con_cuenta("ana")
    r = _replica(cliente, limpio.datos, headers={"Origin": ANFITRION})
    assert r.status_code == 403
    assert r.json() == {"detalle": MENSAJE_CSRF}


def test_replica_con_el_rol_administrador_solo_da_403(limpio) -> None:
    cliente, ficha = _con_cuenta("admin")
    r = _replica(cliente, limpio.datos, headers=_protegida(ficha))
    assert r.status_code == 403
    assert r.json() == {"detalle": MENSAJE_PERMISO}


@pytest.mark.parametrize(
    "ruta", ["/v1/libros/auditoria", "/v1/libros/devolucion", "/v1/libros/pdf", RUTA]
)
def test_las_cuatro_rutas_de_libros_aceptan_la_sesion_del_navegador(ruta: str) -> None:
    """Con cookie y CSRF de una cuenta que arma, la extensión equivocada llega a la ruta (415):
    la dependencia de acceso de `api.main` es la de clave o sesión en las cuatro."""
    cliente, ficha = _con_cuenta("ana")
    campo = "pdf" if ruta.endswith("/pdf") else "libro"
    r = cliente.post(
        ruta,
        files={campo: ("archivo.txt", b"no es nada")},
        data={"fecha_devolucion": "2026-10-13"},
        headers=_protegida(ficha),
    )
    assert r.status_code == 415, r.text


# --- indicadores_de (función pura, RS2-7) ---------------------------------------------------

D = Decimal


def _uno(actual: str, meta: str) -> IndicadorRespuesta:
    (indicador,) = indicadores_de({"SUBSINIVA": D(actual)}, {"SUBSINIVA": D(meta)})
    return indicador


def test_meta_cero_da_delta_pct_nulo() -> None:
    i = _uno("12.5", "0")
    assert (i.actual, i.meta, i.delta, i.delta_pct) == ("12.5", "0", "12.5", None)
    j = _uno("0", "0.00")
    assert (j.meta, j.delta, j.delta_pct) == ("0", "0", None)


def test_claves_titulos_orden_y_sentido() -> None:
    libro = {"TOTALGEN": D("116"), "IVATOT": D("16"), "SUBSINIVA": D("100")}
    silice = {"IVATOT": D("16"), "SUBSINIVA": D("80"), "TOTALGEN": D("116")}
    assert [i.model_dump() for i in indicadores_de(libro, silice)] == [
        # Δ = 100 − 80 = 20; Δ% = 20 ÷ 80 × 100 = 25
        {
            "clave": "SUBSINIVA",
            "titulo": "Subtotal sin IVA",
            "actual": "100",
            "meta": "80",
            "delta": "20",
            "delta_pct": "25.00",
            "sentido": "costo",
        },
        {
            "clave": "IVATOT",
            "titulo": "IVA",
            "actual": "16",
            "meta": "16",
            "delta": "0",
            "delta_pct": "0.00",
            "sentido": "costo",
        },
        {
            "clave": "TOTALGEN",
            "titulo": "Total general",
            "actual": "116",
            "meta": "116",
            "delta": "0",
            "delta_pct": "0.00",
            "sentido": "costo",
        },
    ]


def test_solo_las_claves_presentes_en_los_dos_totales() -> None:
    libro = {"SUBSINIVA": D("1"), "IVATOT": None, "TOTALGEN": D("2"), "OTRA": D("9")}
    silice = {"SUBSINIVA": D("1"), "IVATOT": D("3"), "OTRA": D("9")}
    assert [i.clave for i in indicadores_de(libro, silice)] == ["SUBSINIVA"]
    assert indicadores_de({}, silice) == []
    assert indicadores_de(libro, {}) == []


@pytest.mark.parametrize(
    ("actual", "delta", "delta_pct"),
    [
        # 1,25 ÷ 1 000 × 100 = 0,125 -> 0,12 (al par; al alza sería 0,13)
        ("1001.25", "1.25", "0.12"),
        # 1,35 ÷ 1 000 × 100 = 0,135 -> 0,14 (al par)
        ("1001.35", "1.35", "0.14"),
        # −1,25 ÷ 1 000 × 100 = −0,125 -> −0,12
        ("998.75", "-1.25", "-0.12"),
        # 0,00049 ÷ 1 000 × 100 = 0,000049 -> 0,00
        ("1000.00049", "0.00049", "0.00"),
        # −0,00001 ÷ 1 000 × 100 = −0,000001 -> −0,00, que se muestra sin signo: 0,00
        ("999.99999", "-0.00001", "0.00"),
    ],
)
def test_delta_pct_en_centesimas_con_redondeo_al_par(actual, delta, delta_pct) -> None:
    i = _uno(actual, "1000")
    assert (i.delta, i.delta_pct) == (delta, delta_pct)


def test_los_montos_viajan_como_texto_sin_notacion_cientifica() -> None:
    i = _uno("1E+3", "5E+2")  # 1 000 y 500
    assert (i.actual, i.meta, i.delta, i.delta_pct) == ("1000", "500", "500", "100.00")


@pytest.mark.parametrize(
    ("actual", "meta", "esperado"),
    [
        # Sílice guarda ceros de relleno (4 358,2082500): se quitan sin redondear nada.
        ("4358.20825", "4358.2082500", ("4358.20825", "4358.20825", "0")),
        ("100.10", "100.000", ("100.1", "100", "0.1")),
        # −0,000 se muestra como 0, sin signo
        ("5.000", "5", ("5", "5", "0")),
        ("1E+3", "1000.0", ("1000", "1000", "0")),
    ],
)
def test_los_montos_se_muestran_sin_ceros_de_relleno(actual, meta, esperado) -> None:
    i = _uno(actual, meta)
    assert (i.actual, i.meta, i.delta) == esperado


def test_un_porcentaje_que_no_cabe_en_la_precision_decimal_da_delta_pct_nulo() -> None:
    # Δ ÷ meta × 100 = 1E+40 ÷ 0,01 × 100 = 1E+44: 45 cifras enteras, más que las 28 del
    # contexto decimal; cuantizarlo lanzaría InvalidOperation y tumbaría toda la auditoría.
    i = _uno("1E+40", "0.01")
    assert i.delta_pct is None
    assert i.delta == "1" + "0" * 40


@pytest.mark.parametrize(
    "ruta", ["/v1/libros/auditoria", "/v1/libros/devolucion", "/v1/libros/pdf", RUTA]
)
def test_las_cuatro_rutas_de_libros_niegan_el_rol_administrador_solo(ruta: str) -> None:
    cliente, ficha = _con_cuenta("admin")
    campo = "pdf" if ruta.endswith("/pdf") else "libro"
    r = cliente.post(
        ruta,
        files={campo: ("archivo.txt", b"no es nada")},
        data={"fecha_devolucion": "2026-10-13"},
        headers=_protegida(ficha),
    )
    assert r.status_code == 403, r.text
    assert r.json() == {"detalle": MENSAJE_PERMISO}
