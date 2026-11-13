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
import io
import json
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
from tests.fixtures.libro_apu_por_hoja import (
    ApuFicticio,
    Material,
    con_celdas,
    libro_apu,
    libro_presupuesto,
)
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
PERFIL_DEL_PAQUETE = (
    Path(__file__).resolve().parents[2] / "adapters/hoja_empresa/perfiles/apu_por_hoja.json"
)


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


def test_replica_de_una_hoja_sin_formulas_con_una_celda_lejana_da_422() -> None:
    """Acta del árbitro de los topes, NOTA 6: la hoja no tiene fórmulas (no pasa por la lectura de
    valores guardados) y declara solo A1; la celda lejana la rechaza igual, con el aviso del
    lector."""
    from openpyxl import Workbook

    libro = Workbook()
    libro.active.title = "Notas"
    libro.active["A1"] = "nota ficticia"
    salida = io.BytesIO()
    libro.save(salida)
    datos = con_celdas(salida.getvalue(), "Notas", {"A1048576": "fin ficticio"})
    r = _replica(_con_clave(), datos, nombre="notas.xlsx")
    assert r.status_code == 422, r.text
    assert r.json() == {
        "detalle": "El libro «notas.xlsx», hoja «Notas»: tiene filas con datos o con formato más "
        "allá de la 20.000. Sílice lee de cada hoja hasta 20.000 filas y 100 columnas (de la A a "
        "la CV). Se rechaza por seguridad: borre lo que sobra al final de la hoja y guárdelo de "
        "nuevo."
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
    assert (i.actual, i.meta, i.delta, i.delta_pct) == ("12.50", "0.00", "12.50", None)
    j = _uno("0", "0.00")
    assert (j.meta, j.delta, j.delta_pct) == ("0.00", "0.00", None)


def test_claves_titulos_orden_y_sentido() -> None:
    libro = {"TOTALGEN": D("116"), "IVATOT": D("16"), "SUBSINIVA": D("100")}
    silice = {"IVATOT": D("16"), "SUBSINIVA": D("80"), "TOTALGEN": D("116")}
    assert [i.model_dump() for i in indicadores_de(libro, silice)] == [
        # Δ = 100 − 80 = 20; Δ% = 20 ÷ 80 × 100 = 25
        {
            "clave": "SUBSINIVA",
            "titulo": "Subtotal sin IVA",
            "actual": "100.00",
            "meta": "80.00",
            "delta": "20.00",
            "delta_pct": "25.00",
            "sentido": "exactitud",
        },
        {
            "clave": "IVATOT",
            "titulo": "IVA",
            "actual": "16.00",
            "meta": "16.00",
            "delta": "0.00",
            "delta_pct": "0.00",
            "sentido": "exactitud",
        },
        {
            "clave": "TOTALGEN",
            "titulo": "Total general",
            "actual": "116.00",
            "meta": "116.00",
            "delta": "0.00",
            "delta_pct": "0.00",
            "sentido": "exactitud",
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
        ("1000.00049", "0.00", "0.00"),  # Δ < medio centavo: 0,00
        # −0,00001 ÷ 1 000 × 100 = −0,000001 -> −0,00, que se muestra sin signo: 0,00
        ("999.99999", "0.00", "0.00"),  # ídem, sin signo
    ],
)
def test_delta_pct_en_centesimas_con_redondeo_al_par(actual, delta, delta_pct) -> None:
    i = _uno(actual, "1000")
    assert (i.delta, i.delta_pct) == (delta, delta_pct)


def test_los_montos_viajan_como_texto_sin_notacion_cientifica() -> None:
    i = _uno("1E+3", "5E+2")  # 1 000 y 500
    assert (i.actual, i.meta, i.delta, i.delta_pct) == ("1000.00", "500.00", "500.00", "100.00")


@pytest.mark.parametrize(
    ("actual", "meta", "esperado"),
    [
        # RS2-12: la franja presenta en centésimas al par (NORMAS §2.3); el exacto sigue en
        # totales_libro y totales_silice. 4 358,20825 -> 4 358,21 (resto 0,00825 > medio centavo).
        ("4358.20825", "4358.2082500", ("4358.21", "4358.21", "0.00", "0.00")),
        ("100.10", "100.000", ("100.10", "100.00", "0.10", "0.10")),
        # −0,000 se presenta 0,00, sin signo
        ("5.000", "5", ("5.00", "5.00", "0.00", "0.00")),
        # Ruido de división del libro real: Δ = −7,14E−13, menos de medio centavo -> sin variación
        (
            "9955.645590263035714285714286",
            "9955.645590263036428571428572",
            ("9955.65", "9955.65", "0.00", "0.00"),
        ),
        # Δ = 0,004 sobre meta 0,01 sería 40 %; como Δ se presenta 0,00, Δ% también (coherencia)
        ("0.014", "0.01", ("0.01", "0.01", "0.00", "0.00")),
        # 154,275 al par en centésimas -> 154,28 (el 7 es impar)
        ("4203.93325", "4358.20825", ("4203.93", "4358.21", "-154.28", "-3.54")),
    ],
)
def test_los_montos_se_presentan_en_centesimas_al_par(actual, meta, esperado) -> None:
    i = _uno(actual, meta)
    assert (i.actual, i.meta, i.delta, i.delta_pct) == esperado


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


# --- F5 vial, tarea 6: POST /v1/libros/apu-por-hoja --------------------------------------------
#
# El libro con un APU por hoja (`libro`, obligatorio), el de presupuesto (`presupuesto`, opcional)
# y el perfil (`perfil`, opcional: `apu_por_hoja` por omisión, local o del paquete). En el mismo
# router de `/v1/libros` (clave o sesión que arma o revisa); nada se guarda; los montos viajan como
# texto. Libros FICTICIOS de `tests/fixtures/libro_apu_por_hoja.py`; oráculos de su memoria.

RUTA_APU = "/v1/libros/apu-por-hoja"


def _auditar(cliente, *, presupuesto: bool = False, **extra):
    archivos = {"libro": ("frente_ficticio.xlsx", libro_apu())}
    if presupuesto:
        archivos["presupuesto"] = ("presupuesto_ficticio.xlsx", libro_presupuesto())
    return cliente.post(RUTA_APU, files=archivos, **extra)


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


def test_sin_mandar_perfil_usa_el_local_de_la_carpeta_de_datos():
    """Arbitraje F5 vial, P2: la pantalla no manda `perfil`; el `apu_por_hoja.json` de
    `<carpeta de datos>/perfiles_libros/` (la que fija el lanzador) gana al del paquete."""
    crudo = json.loads(PERFIL_DEL_PAQUETE.read_text(encoding="utf-8"))
    carpeta = config.carpeta_datos() / "perfiles_libros"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "apu_por_hoja.json").write_text(json.dumps(crudo), encoding="utf-8")
    r = _auditar(_con_clave())
    assert r.status_code == 200, r.text
    assert (r.json()["perfil"], r.json()["origen_perfil"]) == ("apu_por_hoja", "local")


def test_un_libro_sin_hojas_de_apu_es_422_con_el_mensaje():
    r = _con_clave().post(RUTA_APU, files={"libro": ("p.xlsx", libro_presupuesto())})
    assert r.status_code == 422
    assert "no tiene ninguna hoja de APU" in r.json()["detalle"]


def test_un_precio_negativo_es_422_con_la_celda():
    """Arbitraje F5 vial, P3: un valor que el núcleo no admite era un 500; ahora es 422 y dice
    la celda (la hoja ficticia de `tests/unit/test_hoja_empresa_apu_por_hoja.py`)."""
    invalida = ApuFicticio(
        9,
        "VF-009",
        "Partida ficticia inválida",
        "m2",
        "1",
        "1",
        materiales=(Material(1, "Cemento ficticio", "kg", "1", "0", "-1"),),
    )
    r = _con_clave().post(RUTA_APU, files={"libro": ("f.xlsx", libro_apu((invalida,)))})
    assert r.status_code == 422, r.text
    assert r.json()["detalle"] == (
        "APU 9!F9: el precio de «Cemento ficticio» es -1 y no puede ser negativo: Sílice no "
        "recalcula la hoja «APU 9»."
    )


# Arbitraje F5/F7/F8 r2, P1: un libro que declara una <dimension> pequeña y escribe lejos
# (A1048576 en el de APU, variante C; XFD en 2.000 filas del de presupuesto, variante E) se rechaza
# por la ruta con 422 y el mensaje de la guardia, sin materializar el millón de filas.
SIGUE_APU = (
    "Sílice lee de cada hoja hasta 20.000 filas y 100 columnas (de la A a la CV). Se rechaza por "
    "seguridad: borre lo que sobra al final de la hoja y guárdelo de nuevo."
)


@pytest.mark.parametrize("hostil", ["libro", "presupuesto"])
def test_una_celda_lejana_que_la_dimension_no_declara_es_422(hostil: str):
    libro, presupuesto = libro_apu(), libro_presupuesto()
    if hostil == "libro":
        libro = con_celdas(libro, "APU 1", {"A1048576": "fin ficticio"})
        esperado = (
            "El libro «frente_ficticio.xlsx», hoja «APU 1»: tiene filas con datos o con formato "
            f"más allá de la 20.000. {SIGUE_APU}"
        )
    else:
        presupuesto = con_celdas(
            presupuesto, "PRESUPUESTO", {f"XFD{fila}": "y" for fila in range(2, 2002)}
        )
        esperado = (
            "El libro «presupuesto_ficticio.xlsx», hoja «PRESUPUESTO»: la fila 2 tiene celdas "
            f"con datos o con formato hasta la columna XFD, más allá de la CV. {SIGUE_APU}"
        )
    r = _con_clave().post(
        RUTA_APU,
        files={
            "libro": ("frente_ficticio.xlsx", libro),
            "presupuesto": ("presupuesto_ficticio.xlsx", presupuesto),
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["detalle"] == esperado


# Arbitraje F5/F7/F8 r2, N3 (el resto de P3): 1e20, 1e300 o 9,99e307 en la cantidad o el precio
# daban un 500 (`decimal.InvalidOperation` al presentar el precio). Ahora son 422 con su celda; y si
# cada cifra cabe en el tope pero el recálculo no cabe en la precisión (un billón por un billón con
# una administración de un billón por ciento), 422 con la hoja, también cuando la hoja no se compara
# (impuesto dentro del APU). En el presupuesto, el P.U. enorme dice su celda.
_ENORME = ApuFicticio(
    9,
    "VF-009",
    "Partida ficticia enorme",
    "m2",
    "1",
    "1",
    materiales=(Material(1, "Cemento ficticio", "kg", "1", "0", "1"),),
)
_TOPE = "1.000.000.000.000"
_NO_RECALCULA = ": Sílice no recalcula la hoja «APU 9»."
_DEMASIADO = (
    "La hoja «APU 9» da un precio unitario demasiado grande para recalcularlo con exactitud: "
    "revise sus cantidades, sus precios y sus porcentajes."
)


@pytest.mark.parametrize(
    ("celdas", "esperado"),
    [
        (
            {"D9": 1e20, "F9": 1e20},
            f"APU 9!D9: la cantidad de «Cemento ficticio» pasa del tope de {_TOPE}{_NO_RECALCULA}",
        ),
        (
            {"F9": 1e300},
            f"APU 9!F9: el precio de «Cemento ficticio» pasa del tope de {_TOPE}{_NO_RECALCULA}",
        ),
        (
            {"F9": 9.99e307, "D9": 9.99e307},
            f"APU 9!D9: la cantidad de «Cemento ficticio» pasa del tope de {_TOPE}{_NO_RECALCULA}",
        ),
        ({"D9": 1e12, "F9": 1e12, "F24": 1e12}, _DEMASIADO),
        ({"D9": 1e12, "F9": 1e12, "F24": 1e12, "F27": 16}, _DEMASIADO),
    ],
    ids=["1e20", "1e300", "9_99e307", "recalculo_enorme", "recalculo_enorme_con_impuesto"],
)
def test_una_magnitud_enorme_es_422_y_no_500(celdas: dict[str, float], esperado: str):
    datos = con_celdas(libro_apu((_ENORME,)), "APU 9", celdas, dimension_de_antes=False)
    r = _con_clave().post(RUTA_APU, files={"libro": ("f.xlsx", datos)})
    assert r.status_code == 422, r.text
    assert r.json()["detalle"] == esperado


def test_un_precio_enorme_en_el_presupuesto_es_422_con_su_celda():
    presupuesto = con_celdas(
        libro_presupuesto(), "PRESUPUESTO", {"F4": 1e300}, dimension_de_antes=False
    )
    r = _con_clave().post(
        RUTA_APU,
        files={"libro": ("f.xlsx", libro_apu()), "presupuesto": ("p.xlsx", presupuesto)},
    )
    assert r.status_code == 422, r.text
    assert r.json()["detalle"] == (
        f"PRESUPUESTO!F4: el precio unitario del renglón 1 pasa del tope de {_TOPE}: Sílice no "
        "enlaza el presupuesto con sus APU."
    )


def test_otra_extension_es_415():
    r = _con_clave().post(RUTA_APU, files={"libro": ("frente.csv", b"a;b")})
    assert r.status_code == 415
