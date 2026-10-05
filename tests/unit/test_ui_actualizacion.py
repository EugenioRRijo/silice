"""UC-02 7a en la interfaz (INV-015): el boton marca la version y conserva el historial.

Dos arneses. Uno fija una `Presentacion` en la sesion. El otro, `_pantalla`, corre el flujo real
de la pagina: `_ejecutar` con un archivo de precios (una sola vez por marca en la sesion) y despues
`render`. Con ese arnes se prueba lo que el nucleo delega en la pagina: el boton solo aparece para
la version que esta ejecucion guardo (revision de A7, P-1). Todas las bases viven en `tmp_path`.
"""

from __future__ import annotations

import importlib
from datetime import date
from pathlib import Path

from pandas import DataFrame
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from core import models
from core.budget import actualizar_precios, elaborar, guardar_presupuesto, plan_secuencial
from core.catalog import (
    Catalogo,
    abrir_sesion,
    crear_esquema,
    crear_lista_desde_archivo,
    crear_motor,
)
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.conftest import RUTA_BASE_REAL, huella
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import PRECIOS_NUEVOS
from tests.fixtures.computo_auditado import items_auditados

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv"
SCRIPT = "from ui.paginas.actualizacion import render\nrender()\n"
CODIGO_NUEVO = "002"


def _base_con_version_nueva(ruta: Path, *, revalorar: bool = True, plan_guardado=None) -> None:
    """001 guardado y 002 revalorado con la muestra, ambos confirmados, por el nucleo directo.
    Con `revalorar=False`, solo 001."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar(sesion)
            catalogo = Catalogo(sesion)
            codigos = [apu.codigo_partida for apu in linea_base.APUS_LINEA_BASE]
            resultado = elaborar(
                items_auditados(),
                catalogo.composiciones(codigos, fecha=linea_base.FECHA_LINEA_BASE),
                linea_base.PARAMETROS_LINEA_BASE,
                codigo=linea_base.CODIGO_PRESUPUESTO,
                fecha=linea_base.FECHA_LINEA_BASE,
                moneda=linea_base.MONEDA,
                plan=plan_guardado or plan_secuencial,
            )
            guardar_presupuesto(
                sesion,
                resultado.presupuesto,
                resultado.informe,
                proyecto=proyecto,
                lista=catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
                parametros=linea_base.PARAMETROS_LINEA_BASE,
                plan=plan_guardado,
            )
            if not revalorar:
                sesion.commit()
                return
            lista = crear_lista_desde_archivo(
                sesion,
                MUESTRA,
                nombre="Lista 01/06/2026",
                moneda=linea_base.MONEDA,
                fecha_vigencia=date(2026, 6, 1),
                origen=MUESTRA.name,
            )
            actualizar_precios(
                sesion, NOMBRE_PROYECTO, linea_base.CODIGO_PRESUPUESTO, lista.lista, CODIGO_NUEVO
            )
            sesion.commit()
    finally:
        motor.dispose()


def _contar(ruta: Path, entidad) -> int:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return len(sesion.scalars(select(entidad)).all())
    finally:
        motor.dispose()


def test_descartar_version_marca_la_version_y_conserva_el_historial(monkeypatch, tmp_path):
    base = tmp_path / "caso.db"
    _base_con_version_nueva(base)
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    pagina = importlib.import_module("ui.paginas.actualizacion")
    antes = huella(RUTA_BASE_REAL)

    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.session_state[pagina.CLAVE_RESULTADO] = pagina.Presentacion(
        tabla=DataFrame(),
        resumen="",
        informe="",
        ignorados=(),
        libro=b"",
        nombre_libro="presupuesto_002.xlsx",
        proyecto=NOMBRE_PROYECTO,
        version_guardada=CODIGO_NUEVO,
        ruta=base,
    )
    at.run()
    boton = next(b for b in at.button if b.label == "Descartar version")
    boton.click().run()

    assert not at.exception
    assert _contar(base, models.DescarteVersion) == 1
    assert _contar(base, models.CambioPrecio) == len(PRECIOS_NUEVOS)
    assert huella(RUTA_BASE_REAL) == antes


def test_sin_version_guardada_no_hay_boton_de_descartar(monkeypatch, tmp_path):
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(tmp_path / "vacio.db"))
    pagina = importlib.import_module("ui.paginas.actualizacion")

    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.session_state[pagina.CLAVE_RESULTADO] = pagina.Presentacion(
        tabla=DataFrame(),
        resumen="",
        informe="",
        ignorados=(),
        libro=b"",
        nombre_libro="presupuesto_002.xlsx",
        proyecto=NOMBRE_PROYECTO,
        version_guardada=None,
        ruta=tmp_path / "vacio.db",
    )
    at.run()

    assert not at.exception
    assert "Descartar version" not in [b.label for b in at.button]


# ---------------------------------------------------------------------------------------------
# El flujo real de la pagina: `_ejecutar` y despues `render` (revision de A7, P-1 y P-2)
# ---------------------------------------------------------------------------------------------

#: Marca de sesion del arnes: si es verdadera (o falta), la proxima ejecucion revalora una vez.
REVALORAR = "prueba_revalorar"
ROTULO_DESCARTAR = "Descartar version"


def _pantalla(ruta: str, lista: str) -> None:
    """Revalora `ruta` (001 -> 002) con el archivo `lista` una vez por marca y pinta la pagina."""
    import importlib
    from datetime import date
    from pathlib import Path
    from types import SimpleNamespace

    import streamlit as st

    from scripts.seed import NOMBRE_PROYECTO

    pagina = importlib.import_module("ui.paginas.actualizacion")
    if st.session_state.get("prueba_revalorar", True):
        st.session_state["prueba_revalorar"] = False
        archivo = SimpleNamespace(name=Path(lista).name, getvalue=Path(lista).read_bytes)
        parametros = {
            "ruta": Path(ruta),
            "proyecto": NOMBRE_PROYECTO,
            "codigo": "001",
            "codigo_nuevo": "002",
            "vigencia": date(2026, 6, 1),
            "moneda": "USD",
            "nombre": "Lista de prueba",
        }
        pagina._ejecutar(parametros, archivo)
    pagina.render()


def _abrir(monkeypatch, caso_abierto: Path, guardar_en: Path, lista: Path) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(caso_abierto))
    at = AppTest.from_function(
        _pantalla, kwargs={"ruta": str(guardar_en), "lista": str(lista)}, default_timeout=120
    )
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    return at


def _rotulos(at: AppTest) -> list[str]:
    return [boton.label for boton in at.button]


def _descartadas(at: AppTest) -> list[str]:
    return [aviso.value for aviso in at.info if "descartada" in aviso.value]


def _contar_si_existe(ruta: Path, entidad) -> int:
    return _contar(ruta, entidad) if ruta.exists() else 0


def test_revalorar_con_cambios_ofrece_descartar_la_version_guardada(monkeypatch, tmp_path):
    base = tmp_path / "caso.db"
    _base_con_version_nueva(base, revalorar=False)
    pagina = importlib.import_module("ui.paginas.actualizacion")

    at = _abrir(monkeypatch, base, base, MUESTRA)

    presentacion = at.session_state[pagina.CLAVE_RESULTADO]
    assert presentacion.version_guardada == CODIGO_NUEVO
    assert presentacion.ruta == base
    assert ROTULO_DESCARTAR in _rotulos(at)


def test_revalorar_sin_cambios_no_guarda_ni_ofrece_descartar(monkeypatch, tmp_path):
    """UC-02 3a: la lista repite un precio vigente (la piedra picada sigue a 35, como en la
    muestra), ningun insumo cambia y no se guarda version: no hay nada que descartar."""
    base = tmp_path / "caso.db"
    _base_con_version_nueva(base, revalorar=False)
    igual = tmp_path / "lista_igual.csv"
    igual.write_text("tipo,insumo,unidad,precio\nmaterial,Piedra picada,m3,35\n", encoding="utf-8")
    pagina = importlib.import_module("ui.paginas.actualizacion")

    at = _abrir(monkeypatch, base, base, igual)

    assert any("Ningun precio cambio" in aviso.value for aviso in at.warning)
    assert at.session_state[pagina.CLAVE_RESULTADO].version_guardada is None
    assert ROTULO_DESCARTAR not in _rotulos(at)


def test_descartar_marca_la_base_donde_se_guardo_aunque_se_cambie_de_caso(monkeypatch, tmp_path):
    """Duda 2 de A7: la version se guardo en `original`; antes del clic se abre `otro` caso, con
    el mismo proyecto y su propia 002. La marca queda solo en `original`. P-2: el estado final es
    el aviso de descartada, sin el boton."""
    original = tmp_path / "original.db"
    otro = tmp_path / "otro.db"
    _base_con_version_nueva(original, revalorar=False)
    _base_con_version_nueva(otro)
    antes = huella(RUTA_BASE_REAL)

    at = _abrir(monkeypatch, original, original, MUESTRA)
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(otro))
    next(b for b in at.button if b.label == ROTULO_DESCARTAR).click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    assert _contar(original, models.DescarteVersion) == 1
    assert _contar(otro, models.DescarteVersion) == 0
    assert _contar(original, models.CambioPrecio) == len(PRECIOS_NUEVOS)
    assert _descartadas(at) != []
    assert ROTULO_DESCARTAR not in _rotulos(at)
    assert huella(RUTA_BASE_REAL) == antes


def test_revalorar_otra_vez_tras_descartar_vuelve_a_ofrecer_el_boton(monkeypatch, tmp_path):
    """Duda 1 de A7: se descarta la 002 del caso; el caso se vuelve a sembrar en la misma ruta y
    se revalora otra vez con el mismo codigo. La 002 nueva no esta descartada: el boton vuelve."""
    base = tmp_path / "caso.db"
    _base_con_version_nueva(base, revalorar=False)
    at = _abrir(monkeypatch, base, base, MUESTRA)
    next(b for b in at.button if b.label == ROTULO_DESCARTAR).click().run()
    assert _descartadas(at) != []

    base.unlink()  # todos los motores se cerraron (`motor.dispose()`)
    _base_con_version_nueva(base, revalorar=False)
    at.session_state[REVALORAR] = True
    at.run()

    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    assert _contar_si_existe(base, models.DescarteVersion) == 0
    assert _descartadas(at) == []
    assert ROTULO_DESCARTAR in _rotulos(at)


def test_revalorar_desde_la_pantalla_conserva_el_plan_guardado_de_la_version(monkeypatch, tmp_path):
    """SF3 (RF-56, SF3-R4): UC-02 pasa `plan_de_version`; sin el, la version revalorada saldria
    sin plan o con otro reparto. Se guarda la 001 con un plan que parte una partida en dos dias."""
    from decimal import Decimal

    from core.budget import plan_de_version

    c = linea_base.CODIGOS_LINEA_BASE
    plan = [
        ("Dia 1", [(c[0], Decimal("0.5"))]),
        ("Dia 2", [(c[0], Decimal("0.5")), (c[1], Decimal("1"))]),
        ("Dia 3", [(c[2], Decimal("1")), (c[3], Decimal("1")), (c[4], Decimal("1"))]),
    ]
    base = tmp_path / "caso.db"
    _base_con_version_nueva(base, revalorar=False, plan_guardado=plan)

    _abrir(monkeypatch, base, base, MUESTRA)

    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            modelos = {m.codigo: m for m in sesion.scalars(select(models.Presupuesto))}
            assert set(modelos) == {"001", "002"}
            # el plan guardado llega a la curva de la revaloracion: 3 dias y no los 5 del secuencial
            # (hallazgo para el nucleo: `actualizar_precios` no guarda el plan en `PlanVersion`)
            assert plan_de_version(sesion, modelos["001"]) == [(e, tuple(r)) for e, r in plan]
            assert [p.periodo.split(" [")[0] for p in modelos["002"].curva] == [
                "Dia 1",
                "Dia 2",
                "Dia 3",
            ]
            assert modelos["002"].curva[-1].acumulado == sum(
                (r.cantidad * r.precio_unitario for r in modelos["002"].partidas), Decimal(0)
            )
    finally:
        motor.dispose()
