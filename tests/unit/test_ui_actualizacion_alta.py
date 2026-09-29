"""UC-02 2a y 2b (INV-090) y UC-07 5 (INV-099) en la pantalla «Actualizar precios» (fase C6).

La pantalla se ejercita entera con `AppTest`: se sube el archivo con `file_uploader` (Streamlit
1.62 lo admite en `AppTest`), se elige en el `multiselect` «Dar de alta» y se pulsa «Revalorar
presupuesto». Cada caso parte de una base temporal con el presupuesto 001 de la linea base
guardado por el nucleo directo (`tests.fixtures.base_con_pendiente.emitir`, sin pendientes;
INV-052: lo compartido vive en `tests/fixtures/`); ninguna prueba toca `data/apu.db` (se vigila su
huella).

Oraculos independientes de la pagina: lo que queda en la base (insumos, listas, precios,
presupuestos y hallazgos guardados) se lee con un motor propio, y los datos del caso vienen de la
muestra `lista_2026-06-01.csv` y de `tests/fixtures/actualizacion_uc02.py` (dos insumos cambian de
precio, cemento y arena, y los dos entran al concreto).

Archivos de prueba (caso didactico, CLAUDE.md §1): «Cemento blanco» no esta en el catalogo sembrado
(flujo 2a, se ofrece para el alta); «Arena lavada» en kg existe con otra unidad, m3 (flujo 2b, se
rechaza y no se ofrece).
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from streamlit.testing.v1 import AppTest

from core import models
from core.catalog import abrir_sesion, crear_motor
from tests.conftest import RUTA_BASE_REAL, huella
from tests.fixtures.actualizacion_uc02 import PRECIOS_NUEVOS, VARIACIONES
from tests.fixtures.base_con_pendiente import emitir
from tests.fixtures.computo_auditado import items_auditados
from tests.fixtures.sin_extra import SinExtra

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv"
SCRIPT = "from ui.paginas.actualizacion import render\nrender()\n"
ROTULO_ALTA = "Dar de alta"
ROTULO_REVALORAR = "Revalorar presupuesto"

CABECERA = "tipo,insumo,unidad,precio\n"
#: Un precio que cambia (el cemento, como en la muestra), un desconocido (2a) y un rechazado (2b).
LISTA_MIXTA = (
    CABECERA
    + "material,Cemento Portland,saco,18\n"
    + "material,Cemento blanco,saco,20\n"
    + "material,Arena lavada,kg,1\n"
)
#: El mismo desconocido dos veces, con precios distintos: el nucleo lo rechaza (ronda 1 de N).
LISTA_REPETIDA = (
    CABECERA
    + "material,Cemento Portland,saco,18\n"
    + "material,Cemento blanco,saco,20\n"
    + "material,Cemento blanco,saco,21\n"
)
#: UC-02 3a: la piedra picada sigue a 35 (ningun precio cambia) y un desconocido para el alta.
LISTA_SIN_CAMBIOS = (
    CABECERA + "material,Piedra picada,m3,35\n" + "material,Cemento blanco,saco,20\n"
)


# ---------------------------------------------------------------------------------------------
# Arnes
# ---------------------------------------------------------------------------------------------


def _abrir(monkeypatch, base: Path, contenido: bytes, nombre: str = "lista.csv") -> AppTest:
    """La pagina sobre `base` con el archivo ya subido (un run para el arranque, otro con el
    archivo)."""
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.run()
    at.file_uploader[0].set_value((nombre, contenido, "text/csv"))
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _multiselect(at: AppTest):
    return next(m for m in at.multiselect if m.label == ROTULO_ALTA)


def _revalorar(at: AppTest, elegir: tuple[str, ...] = ()) -> None:
    """Elige en «Dar de alta» las opciones que contienen cada texto de `elegir` y revalora."""
    if elegir:
        opciones = _multiselect(at).options
        _multiselect(at).set_value([o for o in opciones if any(t in o for t in elegir)])
    next(b for b in at.button if b.label == ROTULO_REVALORAR).click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def _en_base(base: Path, consulta):
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return consulta(sesion)
    finally:
        motor.dispose()


def _contar(base: Path, entidad) -> int:
    return _en_base(base, lambda s: s.scalar(select(func.count()).select_from(entidad)))


def _insumos(base: Path, descripcion: str) -> list[models.Insumo]:
    return _en_base(
        base,
        lambda s: list(
            s.scalars(select(models.Insumo).where(models.Insumo.descripcion == descripcion))
        ),
    )


def _precios_de(base: Path, descripcion: str) -> dict[int, Decimal]:
    """{id de la lista: precio} del insumo con esa descripcion."""
    return _en_base(
        base,
        lambda s: {
            lista_id: precio
            for lista_id, precio in s.execute(
                select(models.PrecioInsumo.lista_id, models.PrecioInsumo.precio)
                .join(models.Insumo, models.Insumo.id == models.PrecioInsumo.insumo_id)
                .where(models.Insumo.descripcion == descripcion)
            )
        },
    )


def _ids_de_listas(base: Path) -> list[int]:
    return _en_base(
        base,
        lambda s: list(s.scalars(select(models.ListaPrecios.id).order_by(models.ListaPrecios.id))),
    )


def _textos(elementos) -> str:
    return "\n".join(str(e.value) for e in elementos)


def _base(tmp_path: Path) -> Path:
    base = tmp_path / "caso.db"
    emitir(base, items_auditados())
    return base


# ---------------------------------------------------------------------------------------------
# INV-090: UC-02 2a (alta a eleccion) y 2b (rechazo por unidad), aparte
# ---------------------------------------------------------------------------------------------


def test_al_subir_la_lista_ofrece_dar_de_alta_solo_los_desconocidos_del_flujo_2a(
    monkeypatch, tmp_path
):
    base = _base(tmp_path)
    insumos_antes = _contar(base, models.Insumo)
    antes = huella(RUTA_BASE_REAL)

    at = _abrir(monkeypatch, base, LISTA_MIXTA.encode())

    seleccion = _multiselect(at)
    assert [o for o in seleccion.options if "Cemento blanco" in o] != []
    assert not [o for o in seleccion.options if "Arena lavada" in o], "2b no se ofrece"
    assert not [o for o in seleccion.options if "Cemento Portland" in o], "un conocido tampoco"
    assert seleccion.value == [], "por defecto no se da de alta ninguno"
    # U-3: «los lista» a la vista, sin abrir el desplegable; 2b y los conocidos no cuentan.
    lista = _textos(at.info)
    assert "El archivo trae 1 insumo(s) que no estan en el catalogo" in lista
    assert "Cemento blanco" in lista
    assert "Arena lavada" not in lista and "Cemento Portland" not in lista
    assert _contar(base, models.Insumo) == insumos_antes, "subir el archivo no escribe"
    assert _contar(base, models.ListaPrecios) == 1
    assert huella(RUTA_BASE_REAL) == antes


def test_revalorar_sin_elegir_ignora_los_desconocidos_y_rechaza_los_de_otra_unidad(
    monkeypatch, tmp_path
):
    base = _base(tmp_path)
    insumos_antes = _contar(base, models.Insumo)
    pagina = importlib.import_module("ui.paginas.actualizacion")

    at = _abrir(monkeypatch, base, LISTA_MIXTA.encode())
    _revalorar(at)

    assert not at.error, _textos(at.error)
    presentacion = at.session_state[pagina.CLAVE_RESULTADO]
    assert presentacion.version_guardada == "002"
    assert presentacion.dados_de_alta == ()
    assert [d for d in presentacion.ignorados if "Cemento blanco" in d] != []
    assert not [d for d in presentacion.ignorados if "Arena lavada" in d]
    assert [r for r in presentacion.rechazados if "Arena lavada" in r] != []
    assert not [r for r in presentacion.rechazados if "Cemento blanco" in r]
    avisos = _textos(at.warning)
    assert "ignoraron" in avisos and "Cemento blanco" in avisos
    assert "rechazaron" in avisos and "Arena lavada" in avisos
    assert _contar(base, models.Insumo) == insumos_antes
    assert _insumos(base, "Cemento blanco") == []


def test_revalorar_con_el_elegido_lo_da_de_alta_con_precio_solo_en_la_lista_nueva(
    monkeypatch, tmp_path
):
    base = _base(tmp_path)
    insumos_antes = _contar(base, models.Insumo)
    [lista_anterior] = _ids_de_listas(base)
    pagina = importlib.import_module("ui.paginas.actualizacion")
    antes = huella(RUTA_BASE_REAL)

    at = _abrir(monkeypatch, base, LISTA_MIXTA.encode())
    _revalorar(at, elegir=("Cemento blanco",))

    assert not at.error, _textos(at.error)
    presentacion = at.session_state[pagina.CLAVE_RESULTADO]
    assert [d for d in presentacion.dados_de_alta if "Cemento blanco" in d] != []
    assert not [d for d in presentacion.ignorados if "Cemento blanco" in d]
    assert [r for r in presentacion.rechazados if "Arena lavada" in r] != []
    assert "dieron de alta" in _textos(at.success) + _textos(at.info) + _textos(at.warning)
    assert _contar(base, models.Insumo) == insumos_antes + 1
    [nuevo] = _insumos(base, "Cemento blanco")
    assert nuevo.tipo == models.TipoInsumo.MATERIAL.value
    # Solo en la lista nueva (la que creo la pantalla), con el precio del archivo.
    [anterior, lista_nueva] = _ids_de_listas(base)
    assert anterior == lista_anterior
    assert _precios_de(base, "Cemento blanco") == {lista_nueva: Decimal("20")}
    assert _insumos(base, "Arena lavada")[0].unidad == "m3", "el rechazado no crea homonimo"
    assert huella(RUTA_BASE_REAL) == antes


def test_filas_repetidas_con_precios_distintos_son_un_error_sin_escribir(monkeypatch, tmp_path):
    base = _base(tmp_path)
    insumos_antes = _contar(base, models.Insumo)
    listas_antes = _contar(base, models.ListaPrecios)
    presupuestos_antes = _contar(base, models.Presupuesto)
    pagina = importlib.import_module("ui.paginas.actualizacion")

    at = _abrir(monkeypatch, base, LISTA_REPETIDA.encode())
    assert len([o for o in _multiselect(at).options if "Cemento blanco" in o]) == 2
    assert "El archivo trae 2 insumo(s)" in _textos(at.info), "cada fila repetida cuenta"
    _revalorar(at, elegir=("Cemento blanco",))

    assert "precios distintos" in _textos(at.error)
    assert at.session_state[pagina.CLAVE_RESULTADO] is None
    assert _contar(base, models.Insumo) == insumos_antes
    assert _contar(base, models.ListaPrecios) == listas_antes
    assert _contar(base, models.Presupuesto) == presupuestos_antes


def test_sin_cambios_de_precio_las_altas_tampoco_se_guardan(monkeypatch, tmp_path):
    """UC-02 3a con un alta elegida: la pagina deshace la transaccion y, con ella, el alta."""
    base = _base(tmp_path)
    insumos_antes = _contar(base, models.Insumo)
    pagina = importlib.import_module("ui.paginas.actualizacion")

    at = _abrir(monkeypatch, base, LISTA_SIN_CAMBIOS.encode())
    _revalorar(at, elegir=("Cemento blanco",))

    assert not at.error, _textos(at.error)
    avisos = _textos(at.warning)
    assert "Ningun precio cambio" in avisos
    assert "tampoco se guardaron" in avisos and "Cemento blanco" in avisos
    presentacion = at.session_state[pagina.CLAVE_RESULTADO]
    assert presentacion.version_guardada is None
    assert presentacion.dados_de_alta == ()
    assert _contar(base, models.Insumo) == insumos_antes
    assert _insumos(base, "Cemento blanco") == []


# ---------------------------------------------------------------------------------------------
# La vista previa no escribe ni revienta (U-2 / Q-1 de la revision de U)
# ---------------------------------------------------------------------------------------------

#: Sin la columna obligatoria `precio`: el nucleo lo rechaza con un `ValueError`.
LISTA_MAL_FORMADA = "tipo,insumo,unidad\nmaterial,Cemento blanco,saco\n"


def test_un_archivo_mal_formado_no_ofrece_nada_y_el_error_sale_al_revalorar(monkeypatch, tmp_path):
    """Subir un archivo ilegible no da traza ni ofrece altas; al revalorar sale el mensaje del
    nucleo como error de la pagina y no se escribe nada."""
    base = _base(tmp_path)
    listas_antes = _contar(base, models.ListaPrecios)
    pagina = importlib.import_module("ui.paginas.actualizacion")

    at = _abrir(monkeypatch, base, LISTA_MAL_FORMADA.encode())  # afirma: sin excepcion

    assert not [m for m in at.multiselect if m.label == ROTULO_ALTA]
    assert "El archivo trae" not in _textos(at.info)
    assert not at.error, "la vista previa no informa: el error sale al revalorar"
    _revalorar(at)
    assert "precio" in _textos(at.error)
    assert at.session_state[pagina.CLAVE_RESULTADO] is None
    assert _contar(base, models.ListaPrecios) == listas_antes


def test_con_un_caso_inexistente_la_vista_previa_no_crea_la_base(monkeypatch, tmp_path):
    """La vista previa corre en cada rerun al subir el archivo: sobre un caso que aun no existe
    no abre la base (SQLite la crearia vacia) y no ofrece nada."""
    base = tmp_path / "no_existe.db"
    antes = huella(RUTA_BASE_REAL)

    at = _abrir(monkeypatch, base, LISTA_MIXTA.encode())  # afirma: sin excepcion

    assert not base.exists()
    assert not [m for m in at.multiselect if m.label == ROTULO_ALTA]
    assert not at.error
    assert huella(RUTA_BASE_REAL) == antes


# ---------------------------------------------------------------------------------------------
# INV-099: UC-07 5, los precios atipicos de la lista nueva en el informe revalorado
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Marca:
    """Cumple `core.budget.MarcaAtipica` (id, valor, puntaje) sin depender de `ml`."""

    id: str
    valor: Decimal
    puntaje: float


def test_el_informe_revalorado_muestra_los_precios_atipicos(monkeypatch, tmp_path):
    """El detector se sustituye por uno que marca todo el historico: con la muestra cambian dos
    insumos (cemento y arena, `PRECIOS_NUEVOS`), los dos del concreto, asi que el informe de la
    version nueva trae dos `ATIPICO` y la base los guarda."""
    base = _base(tmp_path)
    pagina = importlib.import_module("ui.paginas.actualizacion")
    recibidos: list[dict[str, Decimal]] = []

    def marcar_todo(historico):
        recibidos.append(dict(historico))
        return [_Marca(id=clave, valor=valor, puntaje=-0.25) for clave, valor in historico.items()]

    monkeypatch.setattr(pagina, "_detector_de_atipicos", lambda: marcar_todo)
    at = _abrir(monkeypatch, base, MUESTRA.read_bytes(), MUESTRA.name)
    _revalorar(at)

    assert not at.error, _textos(at.error)
    assert len(recibidos) == 1
    assert sorted(recibidos[0].values()) == sorted(VARIACIONES.values())
    presentacion = at.session_state[pagina.CLAVE_RESULTADO]
    assert presentacion.informe.count("ATIPICO") >= len(PRECIOS_NUEVOS)
    assert "Cemento Portland" in presentacion.informe
    assert "ATIPICO" in _textos(at.markdown)
    guardados = _en_base(
        base,
        lambda s: s.scalar(
            select(func.count())
            .select_from(models.Hallazgo)
            .where(models.Hallazgo.regla == "ATIPICO")
        ),
    )
    assert guardados == len(PRECIOS_NUEVOS)


def test_sin_detector_el_informe_no_trae_atipicos(monkeypatch, tmp_path):
    base = _base(tmp_path)
    pagina = importlib.import_module("ui.paginas.actualizacion")
    monkeypatch.setattr(pagina, "_detector_de_atipicos", lambda: None)

    at = _abrir(monkeypatch, base, MUESTRA.read_bytes(), MUESTRA.name)
    _revalorar(at)

    assert not at.error, _textos(at.error)
    assert "ATIPICO" not in at.session_state[pagina.CLAVE_RESULTADO].informe


_MODULOS_RELACIONADOS_CON_ML = (
    "ml",
    "ml.anomaly",
    "ml.anomaly.detector",
    "ui.paginas.actualizacion",
)


def test_el_detector_es_el_de_ml_y_sin_el_extra_no_hay(monkeypatch):
    """El import perezoso: con el extra `ml`, `ml.anomaly.precios_atipicos`; sin el, `None` y la
    pagina se importa igual."""
    import ml.anomaly

    pagina = importlib.import_module("ui.paginas.actualizacion")
    assert pagina._detector_de_atipicos() is ml.anomaly.precios_atipicos

    with SinExtra(monkeypatch, ("ml",), _MODULOS_RELACIONADOS_CON_ML):
        sin_ml = importlib.import_module("ui.paginas.actualizacion")
        assert callable(sin_ml.render)
        assert sin_ml._detector_de_atipicos() is None
