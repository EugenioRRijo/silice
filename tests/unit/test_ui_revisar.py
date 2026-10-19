"""Revisar (UC-23, RF-86/87; spec S3 §9): estado, reauditoría, aviso de P2, dictamen y Excel.

`st.file_uploader` no lo maneja `AppTest`: la prueba lo sustituye (con `monkeypatch`, que lo
devuelve al terminar) por un archivo en memoria con los octetos que dejó en `st.session_state`.

Adaptado a lo construido (nota 4 de la tarea 20): el aviso de P2 dice «Usted armó o cambió este
presupuesto: ... (figura en la versión 004, 005)», el texto del spec §9. El total esperado
(836,80) sale de la memoria del ejemplo mínimo, no de la pantalla."""

from __future__ import annotations

import copy
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.budget.canonico import json_canonico
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from paquete import modelo as paq
from seguridad import empresas, firma
from seguridad.modelo import EmpresaRegistrada
from tests.fixtures.canonico.ejemplo_v1 import EJEMPLO_V1
from tests.fixtures.instalacion import AHORA
from tests.fixtures.paginas_s3 import con_ficha, preparar
from tests.fixtures.paquetes import EMPRESA, paquete
from ui import revision
from ui import sesion as ui_sesion
from ui.sesion import MENSAJE_SIN_PERMISO

PAR = firma.generar_par()


def _pagina() -> None:
    from ui.paginas import revisar

    revisar.render()


def _sustituir(monkeypatch) -> None:
    import io

    import streamlit as st

    from ui import revision as rev
    from ui.paginas import revisar

    class Archivo(io.BytesIO):
        name = "recibido.silice"

    def subida(*_, key=None, **__):
        octetos = st.session_state.get("_archivos", {}).get(key)
        return Archivo(octetos) if octetos is not None else None

    monkeypatch.setattr(st, "file_uploader", subida)
    monkeypatch.setattr(revisar, "servicios_de_la_instalacion", lambda caso: rev.Servicios())


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()


@pytest.fixture
def caso_db(tmp_path: Path, monkeypatch) -> Path:
    ruta = tmp_path / "caso.db"
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema(motor)
    paq.crear_esquema_paquete(motor)
    motor.dispose()
    monkeypatch.setenv("SILICE_CASO", str(ruta))
    return ruta


def _registrar_emisora() -> None:
    with ui_sesion.instalacion() as bd:
        bd.add(
            EmpresaRegistrada(
                empresa=EMPRESA,
                rif="J-0",
                publica=PAR.publica,
                huella=firma.huella_completa(PAR.publica),
                estado="activa",
                comprobada_con="Ana",
                metodo="telefono",
                fecha_comprobacion=AHORA,
                registrada_por="admin",
            )
        )
        bd.commit()


def _documento() -> bytes:
    return json_canonico(copy.deepcopy(EJEMPLO_V1))


def _abrir(
    monkeypatch, tmp_path: Path, archivos: dict, rol: str = "revisa", login: str = "luis"
) -> AppTest:
    ficha = preparar(monkeypatch, tmp_path, rol, login=login)
    _sustituir(monkeypatch)
    _registrar_emisora()
    at = con_ficha(AppTest.from_function(_pagina, default_timeout=120), ficha)
    at.session_state["_archivos"] = archivos
    return at.run()


def _firmado(**mas) -> bytes:
    return paquete(par=PAR, presupuesto=_documento(), anexos={}, **mas)


def _total(at: AppTest, rotulo: str) -> Decimal:
    valor = {m.label: m.value for m in at.metric}[rotulo]
    return Decimal(valor)  # `formatear_decimal`: punto decimal, sin separador de miles


def test_un_paquete_verificado_muestra_su_banner_su_total_y_los_hallazgos(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path, {"rev_archivo": _firmado()})
    assert not at.exception, [e.value for e in at.exception]
    assert any(s.value.startswith("Verificado: emitido por") for s in at.success)
    assert _total(at, "Total recalculado") == Decimal("836.80")  # 836,7975 a dos decimales
    assert any("no recibió una entrega anterior" in c.value for c in at.caption)
    assert any("es la primera que recibe" in c.value for c in at.caption)
    assert at.button(key="rev_preparar_presupuesto")
    assert not at.get("download_button") or all(
        b.proto.label != "Descargar el Excel del emisor" for b in at.get("download_button")
    )


def test_el_excel_solo_se_genera_al_pulsar_y_se_regenera_aqui(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path, {"rev_archivo": _firmado()})
    assert "revisar_excel" not in at.session_state
    at.button(key="rev_preparar_revision").click()
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    _, nombre, octetos = at.session_state["revisar_excel"]
    assert nombre.startswith("revision-") and nombre.endswith(".xlsx")
    assert octetos[:2] == b"PK"  # un libro xlsx (ZIP)
    assert any("se regeneró aquí" in c.value for c in at.caption)


def test_un_paquete_sin_firma_se_audita_igual_y_se_dice_no_verificado(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(
        monkeypatch,
        tmp_path,
        {"rev_archivo": paquete(par=None, presupuesto=_documento(), anexos={})},
    )
    assert not at.exception, [e.value for e in at.exception]
    assert any(w.value.startswith("No verificado") for w in at.warning)
    assert {m.label for m in at.metric} >= {"Total recalculado"}


def test_un_archivo_que_no_es_un_paquete_se_rechaza_con_mensaje_y_sin_traza(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path, {"rev_archivo": b"esto no es un zip"})
    assert not at.exception and at.error and not at.metric
    assert any(e.value.startswith("Rechazado") for e in at.error)
    assert not (tmp_path / "paquetes").exists() or not list((tmp_path / "paquetes").iterdir())


def test_quien_revisa_y_figura_como_quien_armo_ve_el_aviso(monkeypatch, tmp_path, caso_db) -> None:
    ficha = preparar(monkeypatch, tmp_path, "arma", "revisa", login="ana")
    _sustituir(monkeypatch)
    _registrar_emisora()
    with ui_sesion.instalacion() as bd:
        empresas.guardar_empresa_propia(bd, EMPRESA, "J-0", "", "admin", AHORA)
    at = con_ficha(AppTest.from_function(_pagina, default_timeout=120), ficha)
    at.session_state["_archivos"] = {
        "rev_archivo": paquete(par=None, presupuesto=_documento(), anexos={})
    }
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    avisos = [w.value for w in at.warning if "Usted armó o cambió este presupuesto" in w.value]
    assert len(avisos) == 1 and "figura en la versión 004, 005" in avisos[0]


def test_el_aviso_de_quien_armo_escapa_el_codigo_de_version(monkeypatch, tmp_path, caso_db) -> None:
    """T7: el texto sale sin escapar de `aplicacion.revision` y la pantalla lo pasa entero por
    `texto_seguro`; un código de versión con marcas de Markdown llega escapado, no interpretado."""
    ficha = preparar(monkeypatch, tmp_path, "arma", "revisa", login="ana")
    _sustituir(monkeypatch)
    _registrar_emisora()
    with ui_sesion.instalacion() as bd:
        empresas.guardar_empresa_propia(bd, EMPRESA, "J-0", "", "admin", AHORA)
    at = con_ficha(AppTest.from_function(_pagina, default_timeout=120), ficha)
    at.session_state["_archivos"] = {
        "rev_archivo": paquete(
            par=None, presupuesto=_documento(), anexos={}, codigos=("0*4_", "005")
        )
    }
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    avisos = [w.value for w in at.warning if "Usted armó o cambió este presupuesto" in w.value]
    assert len(avisos) == 1 and "figura en la versión 0\\*4\\_, 005" in avisos[0]


def test_otro_revisor_de_la_misma_empresa_no_ve_el_aviso(monkeypatch, tmp_path, caso_db) -> None:
    ficha = preparar(monkeypatch, tmp_path, "revisa", login="pedro")
    _sustituir(monkeypatch)
    _registrar_emisora()
    with ui_sesion.instalacion() as bd:
        empresas.guardar_empresa_propia(bd, EMPRESA, "J-0", "", "admin", AHORA)
    at = con_ficha(AppTest.from_function(_pagina, default_timeout=120), ficha)
    at.session_state["_archivos"] = {
        "rev_archivo": paquete(par=None, presupuesto=_documento(), anexos={})
    }
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert not any("Usted armó" in w.value for w in at.warning)


def test_el_dictamen_se_guarda_atado_al_archivo_y_pide_notas_si_hay_observaciones(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path, {"rev_archivo": _firmado()})
    at.radio(key="rev_resultado").set_value("con observaciones")
    at.button(key="rev_enviar").click()
    at = at.run()
    assert any("necesita notas" in e.value for e in at.error)
    at.radio(key="rev_resultado").set_value("con observaciones")
    at.text_area(key="rev_notas").input("Falta la memoria de cálculo de R4")
    at.button(key="rev_enviar").click()
    at = at.run()
    assert any("Dictamen guardado" in s.value for s in at.success)
    ui_sesion.limpiar_motores()
    motor = crear_motor(f"sqlite:///{caso_db.as_posix()}")
    with abrir_sesion(motor) as caso:
        [fila] = caso.execute(paq.paq_dictamen.select()).mappings().all()
        [recibido] = caso.execute(paq.paq_recibido.select()).mappings().all()
    motor.dispose()
    assert (fila["resultado"], fila["usuario"], fila["estado_verificacion"]) == (
        "con observaciones",
        "Luis <luis>",
        "verificado",
    )
    assert fila["huella_archivo"] == recibido["huella_archivo"]


def test_un_excel_externo_se_audita_en_memoria_y_se_dice_no_verificado(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path, {"rev_excel": revision.plantilla_uc05()})
    assert not at.exception, [e.value for e in at.exception]
    assert any("un Excel no trae cadena ni firma" in w.value for w in at.warning)
    assert _total(at, "Total") == Decimal("836.80")


@pytest.mark.parametrize("rol", ["arma", "administrador"])
def test_otros_roles_no_revisan_aunque_lleguen_por_la_url(
    monkeypatch, tmp_path, caso_db, rol
) -> None:
    at = _abrir(monkeypatch, tmp_path, {"rev_archivo": _firmado()}, rol=rol)
    assert [e.value for e in at.error] == [MENSAJE_SIN_PERMISO] and not at.metric
