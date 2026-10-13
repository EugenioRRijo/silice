"""Entregar paquete (UC-22, RF-85; spec S3 §8.2): rol, equipo local, firma y cadena rota.

Adaptado a lo construido (nota de ejecución de la tarea 16): `exigir_local` rechaza con el mensaje
de `ui.cliente.operacion_sensible_permitida` (`MENSAJE_REMOTO`, criterio de
`operacion.red.es_cliente_local`), no con `ui.sesion.MENSAJE_SOLO_LOCAL`; la IP que decide es la
de `ui.cliente.ip_del_cliente`. El total esperado (836,80) sale de la memoria del ejemplo mínimo
(20 x 41,839875 = 836,7975), no de la pantalla."""

from __future__ import annotations

import hashlib
import io
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from streamlit.testing.v1 import AppTest

from adapters.espacio import crear_esquema_espacio
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from paquete.modelo import crear_esquema_paquete
from seguridad import empresas
from seguridad.modelo import EventoAcceso
from tests.fixtures.canonico_minimo import sembrar_minimo
from tests.fixtures.instalacion import AHORA
from tests.fixtures.paginas_s3 import con_ficha, preparar
from ui import cliente, entrega
from ui import sesion as ui_sesion
from ui.sesion import MENSAJE_SIN_PERMISO

CLAVE = "frase de firma larga y propia"
EMPRESA = "Contratista Demo, C.A."


def _pagina() -> None:
    from ui.paginas import entregar

    entregar.render()


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()


@pytest.fixture
def caso_db(tmp_path: Path, monkeypatch) -> Path:
    ruta = tmp_path / "caso.db"
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        crear_esquema_espacio(sesion.connection())
        crear_esquema_paquete(sesion.connection())
        sembrar_minimo(sesion, anexos_de=entrega.anexos_de_cadena)
        sesion.commit()
    motor.dispose()
    monkeypatch.setenv("SILICE_CASO", str(ruta))
    return ruta


def _abrir(monkeypatch, tmp_path: Path, rol: str = "arma", ip: str = "127.0.0.1") -> AppTest:
    ficha = preparar(monkeypatch, tmp_path, rol, ip=ip)
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: ip)
    return con_ficha(AppTest.from_function(_pagina, default_timeout=60), ficha).run()


def _con_empresa(clave: bool = True) -> None:
    with ui_sesion.instalacion() as bd:
        empresas.guardar_empresa_propia(bd, EMPRESA, "J-0", "", "admin", AHORA)
        if clave:
            empresas.generar_clave(bd, CLAVE, "admin", AHORA)


def _generar(at: AppTest, contrasena: str = "") -> AppTest:
    if contrasena:
        at.text_input(key="entregar_clave").input(contrasena)
    at.button(key="entregar_enviar").click()
    return at.run()


def _descarga(at: AppTest) -> bytes:
    """Los octetos que ofrece el único botón de descarga (los guarda la pantalla en su estado)."""
    assert len(at.get("download_button")) == 1
    return at.session_state["entregar_ultima"][1].datos


def _nombres(datos: bytes) -> set[str]:
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        return set(z.namelist())


def test_el_resumen_dice_el_total_la_cadena_y_que_no_hay_empresa(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path)
    assert not at.exception, [e.value for e in at.exception]
    valores = {m.label: m.value for m in at.metric}
    assert valores["Cadena"] == "íntegra"
    # 836,7975 a dos decimales: 836,80 (la pantalla no escribe los ceros finales)
    assert Decimal(valores["Total"]) == Decimal("836.80")
    assert any("Todavía no hay empresa" in w.value for w in at.warning)
    assert not at.get("download_button")


def test_con_empresa_sin_clave_avisa_que_saldra_sin_firma_y_la_entrega_sale_sin_firma(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path)
    _con_empresa(clave=False)
    at = at.run()
    assert any("SIN FIRMA" in w.value for w in at.warning)
    assert at.text_input(key="entregar_clave").disabled
    at = _generar(at)
    assert not at.exception, [e.value for e in at.exception]
    assert [s.value for s in at.success] == ["Paquete listo (sin firma)."]
    nombres = _nombres(_descarga(at))
    assert {"manifiesto.json", "presupuesto.json", "informe.json", "cadena.json"} <= nombres
    assert "firma.ed25519" not in nombres


def test_con_clave_en_el_equipo_el_paquete_sale_firmado_y_queda_en_el_registro(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path)
    _con_empresa()
    at = _generar(at.run(), CLAVE)
    assert not at.exception, [e.value for e in at.exception]
    assert [s.value for s in at.success] == ["Paquete listo y firmado."]
    datos = _descarga(at)
    assert "firma.ed25519" in _nombres(datos)
    sha = hashlib.sha256(datos).hexdigest()  # aparte, con hashlib
    assert any(sha in c.value for c in at.caption)
    with ui_sesion.instalacion() as bd:
        eventos = list(bd.query(EventoAcceso))
    tipos = {e.tipo for e in eventos}
    assert {"firma", "paquete exportado"} <= tipos
    assert any(sha in (e.detalle or "") for e in eventos)  # el SHA-256 queda en el registro


def test_la_base_del_caso_no_cambia_al_entregar(monkeypatch, tmp_path, caso_db) -> None:
    """Entregar no crea versiones ni eslabones: la base del caso queda como estaba."""
    at = _abrir(monkeypatch, tmp_path)
    _con_empresa()
    at = _generar(at.run(), CLAVE)
    assert at.success
    ui_sesion.limpiar_motores()
    motor = crear_motor(f"sqlite:///{caso_db.as_posix()}")
    with motor.connect() as conexion:
        versiones = conexion.execute(text("SELECT count(*) FROM presupuesto")).scalar_one()
        eslabones = conexion.execute(text("SELECT count(*) FROM eslabon_version")).scalar_one()
    motor.dispose()
    assert (versiones, eslabones) == (1, 1)


def test_contrasena_de_clave_erronea_da_mensaje_sin_traza_y_sin_descarga(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path)
    _con_empresa()
    at = _generar(at.run(), CLAVE + "x")
    assert [e.value for e in at.error] == ["La contraseña de la clave no es correcta."]
    assert not at.get("download_button") and not at.exception


def test_la_firma_no_se_pide_desde_otra_maquina(monkeypatch, tmp_path, caso_db) -> None:
    at = _abrir(monkeypatch, tmp_path, ip="192.168.1.20")
    _con_empresa()
    at = _generar(at.run(), CLAVE)
    assert cliente.MENSAJE_REMOTO in [e.value for e in at.error]
    assert not at.get("download_button")
    with ui_sesion.instalacion() as bd:
        assert not {e.tipo for e in bd.query(EventoAcceso)} & {"firma", "paquete exportado"}


def test_una_cadena_rota_se_muestra_y_no_deja_entregar(monkeypatch, tmp_path, caso_db) -> None:
    motor = crear_motor(f"sqlite:///{caso_db.as_posix()}")
    with motor.begin() as conexion:
        conexion.execute(text("UPDATE partida_presupuestada SET cantidad = '31'"))
    motor.dispose()
    at = _abrir(monkeypatch, tmp_path)
    assert {m.label: m.value for m in at.metric}["Cadena"] == "ROTA" and at.error
    assert at.button(key="entregar_enviar").disabled


@pytest.mark.parametrize("rol", ["revisa", "administrador"])
def test_otros_roles_no_entregan_aunque_lleguen_por_la_url(monkeypatch, tmp_path, caso_db, rol):
    at = _abrir(monkeypatch, tmp_path, rol)
    assert [e.value for e in at.error] == [MENSAJE_SIN_PERMISO] and not at.metric
