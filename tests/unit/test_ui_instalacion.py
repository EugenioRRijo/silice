"""Pestaña «Instalación»: red y API, respaldos y revisión de eventos perdidos (RF-98; spec §5.2).

Desviaciones registradas respecto del plan: (1) S3-3 ya está en `main`, así que la pestaña vive en
`ui.paginas.administracion.PESTANAS` y no como pantalla propia; (2) el plan comprobaba
`"<img" not in m.value`, pero `texto_seguro` escapa con barra invertida (`\\<img`), que sigue
conteniendo la subcadena `<img`: la comprobación correcta es que ningún `<` quede sin escapar.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from operacion import config, eventos_perdidos
from operacion.base_datos import Destino, preparar_base, respaldar_todo
from ui import cliente
from ui.paginas import instalacion


def _pestana() -> None:
    from ui.paginas import instalacion as pestana

    pestana.render_pestana()


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> tuple[Path, Path]:
    """La instalación y el caso migrados una vez por módulo; cada prueba copia los suyos (bases
    reales en `tmp_path`, sin pagar las migraciones en cada prueba)."""
    carpeta = tmp_path_factory.mktemp("plantillas")
    preparar_base(carpeta / "instalacion.db", Destino.INSTALACION)
    preparar_base(carpeta / "silice.db")
    return carpeta / "instalacion.db", carpeta / "silice.db"


@pytest.fixture
def bases(_plantillas: tuple[Path, Path]) -> None:
    for plantilla, destino in zip(
        _plantillas, (config.ruta_instalacion(), config.ruta_caso_por_defecto()), strict=True
    ):
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(plantilla, destino)


def _texto(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption)


def _pendiente(nombre: str, datos: dict) -> Path:
    archivo = config.carpeta_datos() / nombre
    archivo.write_text(json.dumps(datos), encoding="utf-8")
    return archivo


def test_muestra_el_estado_de_la_red_y_de_la_api(bases) -> None:
    config.guardar_ajustes(
        config.ruta_ajustes(),
        config.Ajustes(red_local=True, direccion="192.168.1.20", api_activa=True, puerto_api=8010),
    )
    texto = _texto(AppTest.from_function(_pestana).run())
    assert "Red local: encendida en http://192.168.1.20:8501" in texto
    assert "API: activa (puerto 8010)" in texto
    assert "Sílice: red local (administrador)" in texto  # cómo cambiarla: no desde el navegador


def test_con_la_red_apagada_lo_dice(bases) -> None:
    texto = _texto(AppTest.from_function(_pestana).run())
    assert "Red local: apagada (solo http://127.0.0.1:8501)" in texto
    assert "API: apagada (puerto 8000)" in texto


def test_un_silice_toml_danado_muestra_el_aviso(bases) -> None:
    ruta = config.ruta_ajustes()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("[servidor\nred_local = true", encoding="utf-8")
    at = AppTest.from_function(_pestana).run()
    assert not at.exception
    assert any("valores por defecto" in w.value for w in at.warning)
    assert "Red local: apagada" in _texto(at)


def test_sin_respaldos_lo_dice(bases) -> None:
    at = AppTest.from_function(_pestana).run()
    assert "Todavía no hay respaldos." in _texto(at) and instalacion.juegos_de_respaldo() == []


def test_crear_un_respaldo_lo_agrega_a_la_lista(bases) -> None:
    assert instalacion.juegos_de_respaldo() == []
    at = AppTest.from_function(_pestana).run()
    at.button(key="crear_respaldo").click().run()
    assert not at.exception
    (juego,) = instalacion.juegos_de_respaldo()
    assert juego.motivo == "manual" and juego.bases == 2  # la instalación y el caso por defecto
    assert juego.nombre in " ".join(s.value for s in at.success)
    assert juego.carpeta.parent == config.carpeta_respaldos()


def test_descargar_un_respaldo_exige_ser_el_propio_equipo(bases, monkeypatch) -> None:
    respaldar_todo()
    config.guardar_ajustes(
        config.ruta_ajustes(), config.Ajustes(red_local=True, direccion="192.168.1.20")
    )
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: "192.168.1.30")
    at = AppTest.from_function(_pestana).run()
    assert [e.value for e in at.error] == [cliente.MENSAJE_REMOTO]
    assert len(at.selectbox) == 0  # ni siquiera se ofrece elegir el juego


def test_desde_el_propio_equipo_se_ofrece_la_descarga(bases) -> None:
    juego = respaldar_todo()
    at = AppTest.from_function(_pestana).run()
    assert not at.exception and at.error == []
    assert at.selectbox(key="juego_elegido").options == [juego.name]
    at.button(key="preparar_descarga").click().run()
    assert not at.exception


def test_los_eventos_pendientes_se_ven_y_se_marcan_revisados(bases) -> None:
    archivo = _pendiente(
        "eventos_perdidos_20261011-120000.json",
        {
            "juego": "x",
            "revisado": False,
            "eventos": [{"id": 9, "tipo": "revocacion"}],
            "diferencias": [
                {"tipo": "clave_revivida", "tabla": "clave_empresa", "id": 1, "etiqueta": "AAAA"}
            ],
        },
    )
    at = AppTest.from_function(_pestana).run()
    assert "clave\\_revivida: clave\\_empresa AAAA" in _texto(at)  # escapado por texto_seguro
    assert any("bloqueadas" in e.value for e in at.error)
    assert "Eventos de acceso posteriores al respaldo: 1" in _texto(at)
    assert at.button(key=f"revisar_{archivo.name}").disabled is True  # sin confirmar, no
    at.checkbox(key=f"confirmar_{archivo.name}").check().run()
    at.button(key=f"revisar_{archivo.name}").click().run()
    assert not at.exception
    assert eventos_perdidos.bloqueadas() is False
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    assert datos["revisado"] is True and datos["revisado_por"] == "administrador"


def test_sin_pendientes_no_hay_seccion_de_eventos(bases) -> None:
    at = AppTest.from_function(_pestana).run()
    assert not any("bloqueadas" in e.value for e in at.error) and len(at.checkbox) == 0


def test_un_archivo_de_eventos_ilegible_se_muestra_sin_excepcion(bases) -> None:
    archivo = config.carpeta_datos() / "eventos_perdidos_20261011-140000.json"
    archivo.write_text("[1, 2", encoding="utf-8")
    at = AppTest.from_function(_pestana).run()
    assert not at.exception and "Eventos de acceso posteriores al respaldo: 0" in _texto(at)


def test_un_nombre_con_marcado_no_se_interpreta(bases) -> None:
    _pendiente(
        "eventos_perdidos_20261011-130000.json",
        {
            "revisado": False,
            "diferencias": [
                {
                    "tipo": "cuenta_reactivada",
                    "tabla": "usuario",
                    "id": 1,
                    "etiqueta": "<img src=x onerror=alert(1)>",
                }
            ],
        },
    )
    at = AppTest.from_function(_pestana).run()
    assert not at.exception
    con_etiqueta = [m.value for m in at.markdown if "img" in m.value]
    assert con_etiqueta, "la etiqueta debe mostrarse (escapada)"
    for valor in con_etiqueta:
        assert re.search(r"(?<!\\)[<>]", valor) is None, valor  # pasó por texto_seguro


def test_administracion_registra_la_pestana() -> None:
    from seguridad.permisos import Accion
    from ui.paginas import administracion

    (pestana,) = [p for p in administracion.PESTANAS if p.titulo == "Instalación"]
    assert pestana.accion == Accion.ADMINISTRAR_RED_Y_API
    fuente = (config.RAIZ / "ui" / "paginas" / "administracion.py").read_text(encoding="utf-8")
    assert "instalacion.render_pestana" in fuente
