"""El panel del asistente en la hoja (S4 §3.1, UC-09, RF-32, RF-92, RNF-18; plan 0.9.0, tarea 14).

Con proveedores guionados: ninguna prueba abre la red. `AppTest` no escribe en un
`st.data_editor`: aqui se prueba el flujo del panel (pedido, vista previa y costo, propuestas,
aceptar, rechazar, pregunta, cancelar, guardar) y sus efectos en el estado y en la base.

Ajustes a lo construido (registrados en la bitacora 0.9.0, T14 y revision final de S4.3): quien
decide sale de `ui.sesion` (con el acceso apagado, la persona de desarrollo) y no de un doble de
`silice_sesion`; la sesion guardada en el estado no retiene el proveedor (la clave), y responder
toma el VIGENTE de la instalacion; el registro `ia_*` va por una conexion propia que confirma.
"""

from __future__ import annotations

import dataclasses
import importlib
import shutil
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from asistente.proveedores.base import FALTA_EL_COMPONENTE, FinTurno, LlamadaHerramienta, Turno, Uso
from asistente.proveedores.guionado import ProveedorGuionado
from asistente.registro import anexo_ia, ia_propuestas, ia_sesiones
from core import models
from core.catalog import abrir_sesion, crear_motor
from tests.fixtures.asistente_pedidos import AMBIENTE, PEDIDO
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from ui import hoja
from ui import sesion as ui_sesion
from ui.paginas.hoja import (
    CLAVE_ABIERTA,
    CLAVE_ASISTENTE,
    CLAVE_ASISTENTE_ACEPTADAS,
    CLAVE_ASISTENTE_PEDIDO,
    CLAVE_ASISTENTE_RESPUESTA,
    CLAVE_BORRADOR,
    CLAVE_FUENTE,
    CLAVE_PROYECTO,
    CLAVE_RESPONSABLE,
)

SCRIPT = "from ui.paginas.hoja import render\nrender()\n"
CLAVE_IA = "sk-ant-api03-CLAVE-DEL-PROVEEDOR-7777"
#: Con el acceso apagado (`SILICE_ACCESO=0`, conftest), decide la persona de desarrollo.
QUIEN = "Desarrollo <desarrollo>"
APAGADO = "El asistente esta apagado: lo activa el administrador de la instalacion."


class ProveedorConClave(ProveedorGuionado):
    """Un guionado que, como el adaptador de Claude, guarda la clave de IA en un atributo."""

    def __init__(self, guion, **kwargs) -> None:
        super().__init__(guion, **kwargs)
        self._clave = CLAVE_IA


def guion(ambiente=AMBIENTE, *, nube: bool = True) -> ProveedorConClave:
    llamadas = (
        LlamadaHerramienta("a", "proponer_ambiente", ambiente),
        LlamadaHerramienta("t", "terminar", {"notas": ["listo"]}),
    )
    return ProveedorConClave(
        [Turno("", llamadas, FinTurno.HERRAMIENTAS, Uso(entrada=100, salida=50))],
        nombre="claude" if nube else "ollama",
        modelo="claude-opus-5-5" if nube else "muse-glimmer",
        envia_fuera_del_equipo=nube,
    )


def guion_con_pregunta(pregunta: str = "Cual es el alto del bano?") -> ProveedorConClave:
    primero = (LlamadaHerramienta("q", "preguntar_al_usuario", {"pregunta": pregunta}),)
    segundo = (
        LlamadaHerramienta("a", "proponer_ambiente", AMBIENTE),
        LlamadaHerramienta("t", "terminar", {"notas": []}),
    )
    return ProveedorConClave(
        [
            Turno("", primero, FinTurno.HERRAMIENTAS, Uso(entrada=1)),
            Turno("", segundo, FinTurno.HERRAMIENTAS, Uso(entrada=1)),
        ],
        nombre="claude",
        modelo="claude-opus-5-5",
        envia_fuera_del_equipo=True,
    )


def arrancar(monkeypatch, base: Path, ofertas, *, borrador: bool = True, **estado) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    pagina = importlib.import_module("ui.paginas.hoja")
    vigentes = {"ofertas": ofertas}
    monkeypatch.setattr(pagina, "_proveedores_del_asistente", lambda: vigentes["ofertas"])
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    if borrador:
        at.session_state[CLAVE_BORRADOR] = hoja.Borrador(fecha=date(2026, 10, 5))
    for clave, valor in estado.items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    at.vigentes = vigentes  # para cambiar lo que ofrece la instalacion a mitad de la prueba
    return at


def boton(at: AppTest, rotulo: str):
    return next(b for b in at.button if b.label == rotulo)


def proponer(at: AppTest, pedido: str = PEDIDO) -> AppTest:
    at.text_area(key=CLAVE_ASISTENTE_PEDIDO).set_value(pedido).run()
    boton(at, "Proponer").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def limpio(texto: str) -> str:
    """Sin las barras con que `texto_seguro` escapa el Markdown (lo que la persona ve)."""
    return texto.replace("\\", "")


def textos(at: AppTest) -> str:
    """Todo el texto visible, sin las barras de escape: lo que la persona lee."""
    return limpio(
        " ".join(
            [c.value for c in at.caption]
            + [m.value for m in at.markdown]
            + [w.value for w in at.warning]
            + [i.value for i in at.info]
            + [e.value for e in at.error]
            + [s.value for s in at.success]
        )
    )


def alcanza(objeto, buscado, vistos=None) -> bool:
    """True si `buscado` (un texto o un objeto) se alcanza desde `objeto` siguiendo atributos,
    campos, contenedores y cierres de funciones: la busqueda de RNF-18 c en el estado."""
    vistos = set() if vistos is None else vistos
    if id(objeto) in vistos:
        return False
    vistos.add(id(objeto))
    if objeto is buscado or (
        isinstance(buscado, str) and isinstance(objeto, str) and buscado in objeto
    ):
        return True
    if isinstance(objeto, (str, bytes, int, float, bool, type(None), date)):
        return False
    hijos: list = []
    if isinstance(objeto, dict):
        hijos += list(objeto.keys()) + list(objeto.values())
    elif isinstance(objeto, (list, tuple, set, frozenset)):
        hijos += list(objeto)
    if dataclasses.is_dataclass(objeto) and not isinstance(objeto, type):
        hijos += [getattr(objeto, f.name, None) for f in dataclasses.fields(objeto)]
    hijos += list(getattr(objeto, "__dict__", {}).values())
    for nombre in getattr(type(objeto), "__slots__", ()):
        hijos.append(getattr(objeto, nombre, None))
    for celda in getattr(objeto, "__closure__", None) or ():
        try:
            hijos.append(celda.cell_contents)
        except ValueError:
            pass
    return any(alcanza(h, buscado, vistos) for h in hijos)


def estado_de_la_pantalla(at: AppTest) -> dict:
    return {clave: at.session_state[clave] for clave in at.session_state.filtered_state}


# --- disponibilidad y vista previa -----------------------------------------------------------


def test_apagado_el_asistente_no_ofrece_nada_pero_explica_por_que(monkeypatch, tmp_path):
    at = arrancar(monkeypatch, tmp_path / "no_existe.db", {"claude": (None, APAGADO)})
    assert not [b for b in at.button if b.label == "Proponer"]
    assert any(APAGADO == limpio(c.value) for c in at.caption)


def test_sin_el_extra_ia_la_hoja_no_se_cae_y_dice_como_instalarlo(monkeypatch, tmp_path):
    sin = {"claude": (None, FALTA_EL_COMPONENTE), "ollama": (None, FALTA_EL_COMPONENTE)}
    at = arrancar(monkeypatch, tmp_path / "no_existe.db", sin)
    assert not [b for b in at.button if b.label == "Proponer"]
    assert any(limpio(c.value) == FALTA_EL_COMPONENTE for c in at.caption)


def test_la_vista_previa_dice_el_destino_y_el_costo_antes_de_enviar(monkeypatch, tmp_path):
    at = arrancar(monkeypatch, tmp_path / "no_existe.db", {"claude": (guion(), "")})
    assert boton(at, "Proponer").disabled  # sin pedido no se envia nada
    at.text_area(key=CLAVE_ASISTENTE_PEDIDO).set_value(PEDIDO).run()
    assert not boton(at, "Proponer").disabled
    leyenda = textos(at)
    # 1,2144 USD de la cota de §8.4 (calculada a mano en test_asistente_servicio.py) a 2 decimales
    assert "Destino: Anthropic, en internet" in leyenda and "1.21 USD" in leyenda
    assert "Tope por sesion (lo fija el administrador): 2.00 USD" in leyenda
    assert PEDIDO in " ".join(t.value for t in at.text)  # el texto exacto que se enviara


def test_el_modo_local_dice_este_equipo_y_cuesta_cero(monkeypatch, tmp_path):
    at = arrancar(monkeypatch, tmp_path / "no_existe.db", {"ollama": (guion(nube=False), "")})
    at.text_area(key=CLAVE_ASISTENTE_PEDIDO).set_value(PEDIDO).run()
    leyenda = textos(at)
    assert "Destino: este equipo" in leyenda and "0.00 USD" in leyenda


def test_un_proveedor_no_disponible_dice_por_que_junto_al_disponible(monkeypatch, tmp_path):
    ofertas = {
        "claude": (None, "Falta registrar la clave de IA de la empresa."),
        "ollama": (guion(nube=False), ""),
    }
    at = arrancar(monkeypatch, tmp_path / "no_existe.db", ofertas)
    assert any(
        limpio(c.value) == "claude: Falta registrar la clave de IA de la empresa."
        for c in at.caption
    )
    assert next(s for s in at.selectbox if s.label == "Proveedor").options == ["ollama"]


# --- proponer y decidir ----------------------------------------------------------------------


def test_proponer_no_cambia_el_borrador_hasta_que_se_acepta(monkeypatch, tmp_path):
    at = proponer(arrancar(monkeypatch, tmp_path / "no_existe.db", {"claude": (guion(), "")}))
    assert at.session_state[CLAVE_BORRADOR].espacio.ambientes == ()  # RF-32
    assert [p.id for p in at.session_state[CLAVE_ASISTENTE].pendientes.vigentes()] == ["P1"]
    # lo que el SISTEMA calcula si se aceptara todo: total 0 (sin partidas) y los 2 supuestos (R8)
    assert "calcularia un total de 0.00 USD" in textos(at) and "ADVERTENCIA: 2" in textos(at)
    at.button(key="hoja_asistente_aceptada_P1").click().run()
    borrador = at.session_state[CLAVE_BORRADOR]
    assert [a.id for a in borrador.espacio.ambientes] == ["BAN-01"]
    assert borrador.espacio.origenes[0].tipo.value == "ia"
    assert at.session_state[CLAVE_FUENTE] == "propuesta de IA, sesion 0, claude/claude-opus-5-5"
    assert any(limpio(s.value) == "P1: aceptada." for s in at.success)


def test_la_fuente_escrita_por_la_persona_no_se_pisa(monkeypatch, tmp_path):
    at = arrancar(
        monkeypatch,
        tmp_path / "no_existe.db",
        {"claude": (guion(), "")},
        **{CLAVE_FUENTE: "memoria rev. D"},
    )
    proponer(at).button(key="hoja_asistente_aceptada_P1").click().run()
    assert at.session_state[CLAVE_FUENTE] == "memoria rev. D"


def test_rechazar_todo_deja_el_borrador_identico(monkeypatch, tmp_path):
    at = proponer(arrancar(monkeypatch, tmp_path / "no_existe.db", {"claude": (guion(), "")}))
    antes = at.session_state[CLAVE_BORRADOR]
    at.button(key="hoja_asistente_rechazada_P1").click().run()
    assert at.session_state[CLAVE_BORRADOR] == antes
    assert not at.session_state[CLAVE_ASISTENTE].pendientes.vigentes()
    assert CLAVE_FUENTE not in at.session_state or not at.session_state[CLAVE_FUENTE]


def test_aceptar_lo_que_depende_de_otra_pendiente_avisa_y_no_decide(monkeypatch, tmp_path):
    fuente = {
        "id": "F1",
        "especialidad": "agua",
        "tipo": "montante_agua",
        "ambiente_id": "BAN-01",
        "x": "0",
        "y": "0",
        "z": "0",
        "citas": [],
        "supuestos": [{"campo": c, "motivo": "montante en la esquina"} for c in "xyz"],
    }
    llamadas = (
        LlamadaHerramienta("a", "proponer_ambiente", AMBIENTE),
        LlamadaHerramienta("b", "proponer_fuente", fuente),
        LlamadaHerramienta("t", "terminar", {"notas": []}),
    )
    proveedor = ProveedorConClave(
        [Turno("", llamadas, FinTurno.HERRAMIENTAS, Uso(entrada=1))],
        nombre="claude",
        modelo="claude-opus-5-5",
        envia_fuera_del_equipo=True,
    )
    at = proponer(arrancar(monkeypatch, tmp_path / "no_existe.db", {"claude": (proveedor, "")}))
    at.button(key="hoja_asistente_aceptada_P2").click().run()
    assert any("P2 depende de una propuesta que aun no acepto" in w.value for w in at.warning)
    assert at.session_state[CLAVE_BORRADOR].espacio.fuentes == ()
    assert [p.id for p in at.session_state[CLAVE_ASISTENTE].pendientes.vigentes()] == ["P1", "P2"]


def test_sin_persona_que_decida_no_se_decide_nada(monkeypatch, tmp_path):
    at = proponer(arrancar(monkeypatch, tmp_path / "no_existe.db", {"claude": (guion(), "")}))
    pagina = importlib.import_module("ui.paginas.hoja")
    monkeypatch.setattr(pagina, "_usuario_de_la_sesion", lambda: "")  # acceso sin sesion vigente
    at.button(key="hoja_asistente_aceptada_P1").click().run()
    assert any(ui_sesion.MENSAJE_SIN_ENTRAR == limpio(e.value) for e in at.error)
    assert at.session_state[CLAVE_BORRADOR].espacio.ambientes == ()
    assert [p.id for p in at.session_state[CLAVE_ASISTENTE].pendientes.vigentes()] == ["P1"]


def test_el_texto_del_modelo_se_muestra_escapado(monkeypatch, tmp_path):
    imagen = "![x](http://127.0.0.1:9/x.png)"  # una imagen Markdown hacia un servidor ajeno
    supuestos = [{"campo": "x0", "motivo": imagen}, {"campo": "y0", "motivo": "esquina"}]
    ambiente = {**AMBIENTE, "supuestos": supuestos}
    at = proponer(
        arrancar(monkeypatch, tmp_path / "no_existe.db", {"claude": (guion(ambiente), "")})
    )
    markdown = " ".join([m.value for m in at.markdown] + [c.value for c in at.caption])  # crudo
    assert "Supuestos de la IA" in markdown
    assert imagen not in markdown and r"\!\[x\]" in markdown  # escapada, no cargada


def test_la_clave_del_proveedor_nunca_queda_en_el_estado_de_la_pantalla(monkeypatch, tmp_path):
    proveedor = guion()
    at = proponer(arrancar(monkeypatch, tmp_path / "no_existe.db", {"claude": (proveedor, "")}))
    estado = estado_de_la_pantalla(at)
    assert CLAVE_ASISTENTE in estado
    assert not alcanza(estado, proveedor) and not alcanza(estado, CLAVE_IA)
    # control positivo: la misma busqueda SI la encuentra desde el proveedor
    assert alcanza({"x": [proveedor]}, CLAVE_IA)


def test_descartar_lo_pendiente_conserva_lo_aceptado(monkeypatch, tmp_path):
    at = proponer(arrancar(monkeypatch, tmp_path / "no_existe.db", {"claude": (guion(), "")}))
    at.button(key="hoja_asistente_aceptada_P1").click().run()
    at.button(key="hoja_asistente_descartar").click().run()
    assert CLAVE_ASISTENTE not in at.session_state
    assert [a.id for a in at.session_state[CLAVE_BORRADOR].espacio.ambientes] == ["BAN-01"]


# --- la pregunta del modelo (9g, 9h) ---------------------------------------------------------


def test_la_pregunta_de_la_ia_se_rotula_se_responde_y_la_sesion_sigue(monkeypatch, tmp_path):
    ofertas = {"claude": (guion_con_pregunta(), "")}
    at = proponer(arrancar(monkeypatch, tmp_path / "no_existe.db", ofertas))
    assert any("Pregunta generada por la IA: no escriba" in w.value for w in at.warning)
    assert any("alto del bano" in w.value.replace("\\", "") for w in at.warning)
    assert not alcanza(estado_de_la_pantalla(at), CLAVE_IA)  # pausada tampoco la retiene
    at.text_input(key=CLAVE_ASISTENTE_RESPUESTA).set_value("2,5 m").run()
    at.button(key="hoja_asistente_responder").click().run()
    assert not at.exception and CLAVE_ASISTENTE_RESPUESTA not in at.session_state
    assert [p.id for p in at.session_state[CLAVE_ASISTENTE].pendientes.vigentes()] == ["P1"]
    assert at.session_state[CLAVE_ASISTENTE].resultado.respuestas_de_la_persona == ("2,5 m",)


def test_una_respuesta_con_clave_no_llega_al_modelo_ni_queda_en_la_pantalla(monkeypatch, tmp_path):
    proveedor = guion_con_pregunta()
    at = proponer(arrancar(monkeypatch, tmp_path / "no_existe.db", {"claude": (proveedor, "")}))
    at.text_input(key=CLAVE_ASISTENTE_RESPUESTA).set_value("sk-ant-api03-SECRETA").run()
    at.button(key="hoja_asistente_responder").click().run()
    resultados = proveedor.recibidos[1][1][2].resultados
    assert resultados[0].es_error and "SECRETA" not in resultados[0].contenido
    assert not alcanza(estado_de_la_pantalla(at), "SECRETA")
    assert at.session_state[CLAVE_ASISTENTE].resultado.respuestas_de_la_persona == ()


def test_cancelar_la_pregunta_cancela_la_sesion(monkeypatch, tmp_path):
    ofertas = {"claude": (guion_con_pregunta(), "")}
    at = proponer(arrancar(monkeypatch, tmp_path / "no_existe.db", ofertas))
    at.button(key="hoja_asistente_cancelar").click().run()
    assert at.session_state[CLAVE_ASISTENTE].resultado.motivo.value == "cancelado"
    assert not at.session_state[CLAVE_ASISTENTE].pendientes.propuestas


def test_si_el_proveedor_ya_no_esta_al_responder_la_sesion_se_cancela_y_lo_dice(
    monkeypatch, tmp_path
):
    at = proponer(
        arrancar(monkeypatch, tmp_path / "no_existe.db", {"claude": (guion_con_pregunta(), "")})
    )
    at.vigentes["ofertas"] = {"claude": (None, APAGADO)}  # el administrador lo apago
    at.text_input(key=CLAVE_ASISTENTE_RESPUESTA).set_value("2,5 m").run()
    at.button(key="hoja_asistente_responder").click().run()
    assert at.session_state[CLAVE_ASISTENTE].resultado.motivo.value == "cancelado"
    assert any("ya no se puede usar" in w.value for w in at.warning)


# --- con una base real: registro ia_*, guardar y solo lectura ---------------------------------


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory):
    return plantilla_of001(tmp_path_factory.mktemp("hoja_asistente") / "of001.db")


@pytest.fixture
def base_of(_plantilla, tmp_path):
    copia = tmp_path / "of001.db"
    shutil.copy(_plantilla, copia)
    return copia


#: OF-001 ya tiene un BAN-01: el asistente propone otro bano, fuera de los ambientes del caso.
AMBIENTE_NUEVO = {**AMBIENTE, "id": "BAN-02", "nombre": "Bano 2", "x0": "20", "y0": "20"}


def _leer(base: Path):
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sesiones = sesion.execute(
                select(
                    ia_sesiones.c.proyecto,
                    ia_sesiones.c.version_partida,
                    ia_sesiones.c.version_guardada,
                    ia_sesiones.c.proveedor,
                    ia_sesiones.c.motivo_fin,
                )
            ).all()
            estados = sesion.execute(
                select(
                    ia_propuestas.c.propuesta, ia_propuestas.c.estado, ia_propuestas.c.decidida_por
                )
            ).all()
            fuentes = sesion.scalars(select(models.RegistroCambio.fuente)).all()
            anexo = anexo_ia(sesion.connection(), NOMBRE_OF001, "002")
    finally:
        motor.dispose()
    return sesiones, estados, fuentes, anexo


def test_con_base_la_sesion_y_la_decision_quedan_en_el_registro_y_entran_al_guardar(
    monkeypatch, base_of
):
    at = arrancar(
        monkeypatch,
        base_of,
        {"claude": (guion(AMBIENTE_NUEVO), "")},
        borrador=False,
        **{CLAVE_PROYECTO: NOMBRE_OF001},
    )
    assert at.session_state[CLAVE_ABIERTA].codigo == "001"
    proponer(at)
    assert _leer(base_of)[0] == [(NOMBRE_OF001, "001", None, "claude", "terminar")]
    at.button(key="hoja_asistente_aceptada_P1").click().run()
    sesiones, estados, _, anexo = _leer(base_of)
    assert estados == [("P1", "aceptada", QUIEN)]  # confirmado aunque no se guarde la version
    assert anexo is None  # aun no se guardo
    assert at.session_state[CLAVE_ASISTENTE_ACEPTADAS] == [1]
    assert at.session_state[CLAVE_FUENTE] == "propuesta de IA, sesion 1, claude/claude-opus-5-5"

    at.text_input(key=CLAVE_RESPONSABLE).set_value("Ing. Prueba").run()
    boton(at, "Guardar version").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Se guardo la version 002" in s.value for s in at.success)
    sesiones, estados, fuentes, anexo = _leer(base_of)
    assert sesiones == [(NOMBRE_OF001, "001", "002", "claude", "terminar")]
    assert fuentes and set(fuentes) == {"propuesta de IA, sesion 1, claude/claude-opus-5-5"}
    assert anexo is not None and b'"decidida_por":"Desarrollo <desarrollo>"' in anexo
    assert CLAVE_ASISTENTE not in at.session_state
    assert CLAVE_ASISTENTE_ACEPTADAS not in at.session_state


def test_una_sesion_descartada_con_algo_aceptado_se_marca_igual_al_guardar(monkeypatch, base_of):
    at = arrancar(
        monkeypatch,
        base_of,
        {"claude": (guion(AMBIENTE_NUEVO), "")},
        borrador=False,
        **{CLAVE_PROYECTO: NOMBRE_OF001},
    )
    proponer(at).button(key="hoja_asistente_aceptada_P1").click().run()
    at.button(key="hoja_asistente_descartar").click().run()
    at.text_input(key=CLAVE_RESPONSABLE).set_value("Ing. Prueba").run()
    boton(at, "Guardar version").click().run()
    assert _leer(base_of)[0] == [(NOMBRE_OF001, "001", "002", "claude", "terminar")]


def test_en_una_version_de_solo_lectura_no_se_abre_el_panel(monkeypatch, base_of):
    """9i: el panel no se abre y dice por que."""
    at = arrancar(
        monkeypatch,
        base_of,
        {"claude": (guion(), "")},
        borrador=False,
        **{CLAVE_PROYECTO: NOMBRE_OF001},
    )
    borrador = at.session_state[CLAVE_BORRADOR]
    at.session_state[CLAVE_ABIERTA] = replace(at.session_state[CLAVE_ABIERTA], solo_lectura=True)
    at.session_state[CLAVE_BORRADOR] = borrador
    at.run()
    assert not [b for b in at.button if b.label == "Proponer"]
    assert any("no se abre en una version de solo lectura" in c.value for c in at.caption)
