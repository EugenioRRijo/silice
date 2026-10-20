"""La capa de aplicacion de «Componer una partida» (ola 3, S2-B; plan §2 y §3, RB-2 a RB-5).

Lo que la API (`api/rutas/composicion.py`) y, despues, la pagina Streamlit comparten sin pintar
nada: evaluar la composicion en vivo (estado, desglose y las advertencias de las ayudas), la
precarga de una partida existente (UC-11, paso 1), las similares con su composicion (ayuda 1), las
sugerencias de la referencia y el guardado con la justificacion de UC-06 4a.

Caso didactico (NORMAS.md §1): la linea base sembrada por `scripts.seed.sembrar` en `tmp_path`
(nunca `data/`). Oraculos a mano o de la fuente de la linea base (`tests/fixtures/apu_linea_base`):
el precio unitario de la tuberia es el del PDF (10,19) y su subtotal de materiales,
1,05 x 6 + 0,2 x 2,5 + 0,2 x 1,2 + 0,01 x 15 = 7,19. Los mensajes son los literales de la pagina
clasica (`ui/paginas/componer.py`), copiados aqui a mano. Las ayudas de `ml` se sustituyen por
dobles (como `tests/unit/test_composicion_ia.py`): la prueba no depende del extra ni del modelo.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aplicacion.composicion import (
    MENSAJE_CONDICIONES_OBLIGATORIAS,
    MENSAJE_FORMULARIO_VACIO,
    ComposicionInvalida,
    evaluar_composicion,
    guardar_desde_tablas,
    precarga_de_partida,
    similares_con_composicion,
    sugerencias_de_referencia,
)
from core import models
from core.catalog import (
    Catalogo,
    abrir_sesion,
    crear_esquema,
    crear_motor,
    registrar_rendimiento,
)
from core.contracts import Dominio, Hallazgo, Severidad, TipoRendimiento
from ml.anomaly import VeredictoRendimiento
from ml.normalization import PartidaSimilar, Propuesta
from scripts.seed import sembrar
from tests.fixtures.apu_linea_base import (
    APU_TUBERIA,
    APUS_LINEA_BASE,
    FECHA_LINEA_BASE,
    PRECIO_UNITARIO_ESPERADO,
)
from tests.fixtures.filas_composicion import filas_equipos, filas_mano_obra, filas_materiales

TUBERIA = APU_TUBERIA.codigo_partida
NUEVA = "PRUEBA-01-NUEVA"
CONDICIONES = "condiciones de prueba de la ola 3: no provienen de una ejecucion medida"
JUSTIFICACION = "cuadrilla reforzada en la prueba de la ola 3; texto de prueba, no de obra"
FECHA = date(2026, 5, 1)  # posterior a la lista sembrada (FECHA_LINEA_BASE)


def _tablas(apu=APU_TUBERIA):
    return filas_materiales(apu), filas_equipos(apu), filas_mano_obra(apu)


def _sembrar(base: Path, segundo_rendimiento: bool = False) -> Path:
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            if segundo_rendimiento:
                # Dos observaciones de la tuberia, rango [100, 110]: 150 queda fuera.
                registrar_rendimiento(
                    sesion,
                    TUBERIA,
                    Decimal("110"),
                    TipoRendimiento.ESTIMADO,
                    FECHA_LINEA_BASE,
                    condiciones="segundo estimado de prueba (ola 3)",
                )
            sesion.commit()
    finally:
        motor.dispose()
    return base


@contextmanager
def _sesion(base: Path) -> Iterator[Session]:
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            yield sesion
    finally:
        motor.dispose()


@pytest.fixture
def base(tmp_path: Path) -> Path:
    return _sembrar(tmp_path / "caso.db")


@pytest.fixture
def base_con_rango(tmp_path: Path) -> Path:
    return _sembrar(tmp_path / "caso.db", segundo_rendimiento=True)


def _sin_atipicos() -> SimpleNamespace:
    """`ml.anomaly` que no marca nada: aisla la prueba de las ayudas 2 y 3."""
    return SimpleNamespace(
        precios_atipicos=lambda _serie: [],
        evaluar_rendimiento=lambda _observados, _valor: None,
    )


def _sin_prediccion() -> SimpleNamespace:
    def _falla(*_args, **_kwargs):
        raise RuntimeError("sin prediccion en esta prueba")

    return SimpleNamespace(predecir_por_reglas=_falla)


def _evaluar(sesion, codigo, descripcion, unidad, rendimiento, tablas, **dobles):
    dobles.setdefault("cargar_anomalia", _sin_atipicos)
    dobles.setdefault("cargar_prediccion", _sin_prediccion)
    return evaluar_composicion(
        sesion, codigo, descripcion, unidad, Dominio.CIVIL, rendimiento, *tablas, **dobles
    )


# --- evaluar_composicion ------------------------------------------------------------------------


def test_el_formulario_en_blanco_es_vacio_con_la_bienvenida_de_la_pagina(base: Path) -> None:
    with _sesion(base) as sesion:
        evaluacion = _evaluar(sesion, "", "", "", "", ([{}], [], []))
    assert evaluacion.estado == "vacio"
    assert evaluacion.aviso == (
        "Comience por la cabecera (código y descripción) y declare al menos un insumo en alguna "
        "de las tres tablas de abajo, o búsquelo en la referencia MaPreX: el desglose se calcula "
        "aquí automáticamente, sin necesidad de guardar."
    )
    assert evaluacion.aviso == MENSAJE_FORMULARIO_VACIO
    assert evaluacion.resultado is None
    assert evaluacion.advertencias == ()
    assert evaluacion.requiere_justificacion is False


def test_una_tabla_a_medias_es_incompleta_con_el_mensaje_de_la_conversion(base: Path) -> None:
    with _sesion(base) as sesion:
        evaluacion = _evaluar(sesion, NUEVA, "Partida de prueba", "m", "", _tablas())
    assert evaluacion.estado == "incompleto"
    assert evaluacion.aviso == "rendimiento: '' no es un numero decimal valido"
    assert evaluacion.resultado is None


def test_una_composicion_valida_da_el_desglose_y_avisa_que_la_partida_es_nueva(
    base: Path,
) -> None:
    with _sesion(base) as sesion:
        evaluacion = _evaluar(
            sesion, NUEVA, "Partida de prueba", APU_TUBERIA.unidad, "100", _tablas()
        )
    assert evaluacion.estado == "valido"
    assert evaluacion.aviso is None
    assert evaluacion.resultado is not None
    assert evaluacion.resultado.materiales == Decimal("7.19")
    precio = evaluacion.resultado.precio_unitario
    assert precio.quantize(Decimal("0.01")) == PRECIO_UNITARIO_ESPERADO[TUBERIA]
    assert [(a.tipo, a.texto) for a in evaluacion.advertencias] == [
        (
            "partida_nueva",
            "Partida nueva: la estimacion por reglas parte del PU anterior de la partida, que "
            "no existe; el contraste no es posible (UC-07, flujo 3a).",
        )
    ]
    assert evaluacion.contraste is None
    assert evaluacion.requiere_justificacion is False


def test_el_rendimiento_fuera_de_rango_advierte_aunque_las_tablas_esten_vacias(
    base_con_rango: Path,
) -> None:
    """RF-27 y UC-06 4a: la advertencia de rango se calcula con el rendimiento y el codigo, igual
    que `_advertir_si_corresponde`, aunque la composicion todavia no sea valida."""
    with _sesion(base_con_rango) as sesion:
        evaluacion = _evaluar(sesion, TUBERIA, APU_TUBERIA.descripcion, "", "150", ([], [], []))
    assert evaluacion.estado == "incompleto"
    [advertencia] = evaluacion.advertencias
    assert advertencia.tipo == "rendimiento"
    assert advertencia.texto.startswith("el rendimiento 150 se aparta")
    assert "2 observaciones" in advertencia.texto
    assert evaluacion.requiere_justificacion is True


def test_el_rendimiento_dentro_del_rango_no_advierte(base_con_rango: Path) -> None:
    with _sesion(base_con_rango) as sesion:
        evaluacion = _evaluar(sesion, TUBERIA, APU_TUBERIA.descripcion, "", "105", ([], [], []))
    assert evaluacion.advertencias == ()
    assert evaluacion.requiere_justificacion is False


def test_el_bosque_de_aislamiento_agrega_su_advertencia_sin_pedir_justificacion(
    base_con_rango: Path,
) -> None:
    anomalia = SimpleNamespace(
        precios_atipicos=lambda _serie: [],
        evaluar_rendimiento=lambda _observados, _valor: VeredictoRendimiento(
            atipico=True, puntaje=-0.25
        ),
    )
    with _sesion(base_con_rango) as sesion:
        evaluacion = _evaluar(
            sesion,
            TUBERIA,
            APU_TUBERIA.descripcion,
            "",
            "105",
            ([], [], []),
            cargar_anomalia=lambda: anomalia,
        )
    assert [(a.tipo, a.texto) for a in evaluacion.advertencias] == [
        (
            "rendimiento_ml",
            "El bosque de aislamiento (ayuda 3 de Sílice, spec §3.7) tambien marca este "
            "rendimiento como atipico frente al historico de la partida (puntaje -0.250); el "
            "registro no queda bloqueado por esto.",
        )
    ]
    assert evaluacion.requiere_justificacion is False


def test_un_precio_atipico_frente_a_su_historico_advierte(base: Path) -> None:
    """Ayuda 2: con un cambio registrado del insumo (precio anterior 5) y el doble que marca la
    variacion tecleada como atipica, la advertencia cita el insumo y el precio de la tabla."""
    insumo = APU_TUBERIA.materiales[0].descripcion
    marcadas: list[dict] = []

    def _atipicos(serie):
        marcadas.append(dict(serie))
        return [SimpleNamespace(id="candidato-precio-tecleado")]

    anomalia = SimpleNamespace(precios_atipicos=_atipicos, evaluar_rendimiento=lambda _o, _v: None)
    with _sesion(base) as sesion:
        lista = Catalogo(sesion).lista_vigente(FECHA)
        modelo = sesion.scalars(select(models.Insumo).where(models.Insumo.descripcion == insumo))
        sesion.add(
            models.CambioPrecio(
                lista_anterior_id=lista.id,
                lista_nueva_id=lista.id,
                insumo_id=modelo.one().id,
                precio_anterior=Decimal("4"),
                precio_nuevo=Decimal("5"),
                variacion=Decimal("0.25"),
                fecha=FECHA_LINEA_BASE,
            )
        )
        sesion.flush()
        materiales = filas_materiales(APU_TUBERIA)[:1]
        evaluacion = _evaluar(
            sesion,
            NUEVA,
            "Partida de prueba",
            "m",
            "100",
            (materiales, [], []),
            cargar_anomalia=lambda: anomalia,
        )
    precio = APU_TUBERIA.materiales[0].precio
    textos = [a.texto for a in evaluacion.advertencias if a.tipo == "precio_atipico"]
    assert textos == [
        f"El precio de «{insumo}» ({precio}) resulta atipico frente al historico de ese insumo "
        "(ayuda 2 de Sílice, spec §3.7); reviselo, aunque el sistema no bloquea el guardado "
        "por esto."
    ]
    # La variacion implicita (6 - 5) / 5 = 0,2 viaja junto al historico.
    assert marcadas and marcadas[0]["candidato-precio-tecleado"] == Decimal("0.2")


def test_el_contraste_aace_de_una_partida_existente_viaja_con_su_hallazgo(base: Path) -> None:
    hallazgo = Hallazgo(
        regla="AACE",
        severidad=Severidad.ADVERTENCIA,
        descripcion="precio fuera de la clase 3 (texto del doble de prueba)",
    )
    prediccion = SimpleNamespace(
        predecir_por_reglas=lambda _pu, _variaciones: [
            SimpleNamespace(pu_estimado=Decimal("9.50"))
        ],
        contrastar_aace=lambda _codigo, _construido, _estimado: hallazgo,
        tecnica_para=lambda _registros: "reglas",
    )
    with _sesion(base) as sesion:
        evaluacion = _evaluar(
            sesion,
            TUBERIA,
            APU_TUBERIA.descripcion,
            APU_TUBERIA.unidad,
            "100",
            _tablas(),
            cargar_prediccion=lambda: prediccion,
        )
    assert evaluacion.estado == "valido"
    assert evaluacion.contraste is not None
    assert evaluacion.contraste.tecnica == "reglas"
    assert evaluacion.contraste.registros == len(APUS_LINEA_BASE)
    assert evaluacion.contraste.pu_estimado == Decimal("9.50")
    assert evaluacion.contraste.dentro_de_rango is False
    assert [(a.tipo, a.texto) for a in evaluacion.advertencias] == [
        ("contraste_aace", "precio fuera de la clase 3 (texto del doble de prueba)")
    ]


# --- precarga_de_partida ------------------------------------------------------------------------


def test_una_partida_existente_precarga_sus_tablas_y_su_rendimiento(base: Path) -> None:
    with _sesion(base) as sesion:
        precarga = precarga_de_partida(sesion, f" {TUBERIA} ")
    assert precarga.existe is True
    materiales, equipos, mano_obra = precarga.tablas
    assert [fila["descripcion"] for fila in materiales] == [
        linea.descripcion for linea in APU_TUBERIA.materiales
    ]
    assert [Decimal(fila["precio"]) for fila in materiales] == [
        linea.precio for linea in APU_TUBERIA.materiales
    ]
    assert [Decimal(fila["depreciacion"]) for fila in equipos] == [
        linea.depreciacion for linea in APU_TUBERIA.equipos
    ]
    assert [fila["modalidad"] for fila in mano_obra] == ["jornal"] * len(APU_TUBERIA.mano_obra)
    assert Decimal(precarga.rendimiento_propuesto) == APU_TUBERIA.rendimiento
    assert precarga.hay_historial is True


def test_un_codigo_desconocido_no_precarga_nada(base: Path) -> None:
    with _sesion(base) as sesion:
        precarga = precarga_de_partida(sesion, NUEVA)
    assert precarga.existe is False
    assert precarga.tablas == ([], [], [])
    assert precarga.rendimiento_propuesto is None
    assert precarga.hay_historial is False


# --- similares_con_composicion -----------------------------------------------------------------


def test_las_similares_traen_la_composicion_de_cada_partida_propuesta(base: Path) -> None:
    vistas: list[dict] = []

    def _proponedor(partidas):
        vistas.append(dict(partidas))
        return lambda _descripcion: Propuesta(
            (PartidaSimilar(TUBERIA, APU_TUBERIA.descripcion, 0.875),)
        )

    normalizacion = SimpleNamespace(Propuesta=Propuesta, proponedor=_proponedor)
    with _sesion(base) as sesion:
        similares = similares_con_composicion(
            sesion, Dominio.CIVIL, "tuberia de pvc", cargar_normalizacion=lambda: normalizacion
        )
    assert set(vistas[0]) == {apu.codigo_partida for apu in APUS_LINEA_BASE}
    [similar] = similares
    assert (similar.codigo, similar.descripcion, similar.puntaje) == (
        TUBERIA,
        APU_TUBERIA.descripcion,
        0.875,
    )
    assert similar.aviso is None
    assert similar.composicion is not None
    assert similar.composicion.rendimiento == APU_TUBERIA.rendimiento


def test_sin_descripcion_no_hay_similares(base: Path) -> None:
    normalizacion = SimpleNamespace(Propuesta=Propuesta, proponedor=None)
    with _sesion(base) as sesion:
        similares = similares_con_composicion(
            sesion, Dominio.CIVIL, "   ", cargar_normalizacion=lambda: normalizacion
        )
    assert similares == []


# --- sugerencias_de_referencia -----------------------------------------------------------------

_CABECERA_CSV = (
    "tipo,insumo,unidad,precio_bs,bono_bs,factor_depreciacion,precio_usd,fecha_vigencia,"
    "archivo,ref_maprex,notas\n"
)


def _referencia_ficticia(raiz: Path) -> Path:
    """Los cuatro CSV de la referencia con filas inventadas para la prueba (ninguna es real)."""
    carpeta = raiz / "data" / "precios" / "maprex_2026-07"
    carpeta.mkdir(parents=True)
    filas = {
        "referencia_civil.csv": (
            "material,TUBO FICTICIO DE PRUEBA,m,,,,2.50,2026-07-01,prueba.pdf,FIC01,\n"
            "equipo,MEZCLADORA FICTICIA,dia,,,0.03,40.00,2026-07-01,prueba.pdf,FIC02,\n"
        ),
        "referencia_telecom.csv": "",
        "referencia_industrial.csv": (
            "mano_obra,AYUDANTE FICTICIO,dia,,1.00,,3.00,2026-07-01,prueba.pdf,FIC03,\n"
        ),
        "referencia_sistemas.csv": "",
    }
    for nombre, contenido in filas.items():
        (carpeta / nombre).write_text(_CABECERA_CSV + contenido, encoding="utf-8")
    return raiz


def test_las_sugerencias_traen_la_etiqueta_la_referencia_y_la_fila_completada(
    tmp_path: Path,
) -> None:
    raiz = _referencia_ficticia(tmp_path)
    [material] = sugerencias_de_referencia("tubo", "material", raiz)
    assert material.ref_maprex == "FIC01"
    assert material.etiqueta == "TUBO FICTICIO DE PRUEBA — 2.50 USD/m · ref. FIC01"
    assert material.fila == {
        "descripcion": "TUBO FICTICIO DE PRUEBA",
        "unidad": "m",
        "cantidad": "",
        "precio": "2.50",
    }
    [equipo] = sugerencias_de_referencia("mezcladora", "equipo", raiz)
    assert equipo.fila == {
        "descripcion": "MEZCLADORA FICTICIA",
        "cantidad": "",
        "precio": "40.00",
        "depreciacion": "0.03",
    }
    [obrero] = sugerencias_de_referencia("ayudante", "mano_obra", raiz)
    assert obrero.fila == {
        "descripcion": "AYUDANTE FICTICIO",
        "cantidad": "",
        "sueldo": "3.00",
        "modalidad": "",
    }


def test_sin_texto_no_hay_sugerencias_y_un_tipo_desconocido_es_un_error(tmp_path: Path) -> None:
    raiz = _referencia_ficticia(tmp_path)
    assert sugerencias_de_referencia("   ", "material", raiz) == []
    with pytest.raises(ValueError, match="tipo"):
        sugerencias_de_referencia("tubo", "herramienta", raiz)


# --- guardar_desde_tablas ----------------------------------------------------------------------


def _guardar(
    sesion,
    codigo,
    descripcion,
    unidad,
    rendimiento,
    tablas,
    condiciones=CONDICIONES,
    justificacion=None,
):
    return guardar_desde_tablas(
        sesion,
        codigo,
        descripcion,
        unidad,
        Dominio.CIVIL,
        rendimiento,
        *tablas,
        fecha=FECHA,
        condiciones=condiciones,
        justificacion=justificacion,
    )


def _contar(sesion, modelo) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


def test_guardar_una_partida_nueva_da_el_precio_y_el_mensaje_de_la_pagina(base: Path) -> None:
    with _sesion(base) as sesion:
        guardado = _guardar(sesion, NUEVA, "Partida de prueba", "m", "100", _tablas())
        sesion.commit()
    assert guardado.motivo is None
    assert guardado.precio_unitario == "10.19"
    assert (
        guardado.mensaje
        == "Composicion guardada para la partida PRUEBA-01-NUEVA: precio unitario 10.19."
    )
    assert guardado.justificada is False
    assert guardado.avisos == ()
    with _sesion(base) as sesion:
        assert Catalogo(sesion).partida(NUEVA).descripcion == "Partida de prueba"


def test_sin_condiciones_no_se_guarda_nada(base: Path) -> None:
    with _sesion(base) as sesion:
        with pytest.raises(ComposicionInvalida) as error:
            _guardar(sesion, NUEVA, "Partida", "m", "100", _tablas(), condiciones="  ")
        assert str(error.value) == MENSAJE_CONDICIONES_OBLIGATORIAS
        assert MENSAJE_CONDICIONES_OBLIGATORIAS.startswith(
            "Las condiciones del rendimiento son obligatorias para guardar (RF-33)"
        )
        with pytest.raises(KeyError):
            Catalogo(sesion).partida(NUEVA)


def test_una_composicion_invalida_no_se_guarda(base: Path) -> None:
    with _sesion(base) as sesion:
        with pytest.raises(ComposicionInvalida, match="rendimiento"):
            _guardar(sesion, NUEVA, "Partida", "m", "", _tablas())


def test_una_cabecera_distinta_sobre_una_partida_existente_da_el_motivo(base: Path) -> None:
    with _sesion(base) as sesion:
        antes = _contar(sesion, models.Rendimiento)
        guardado = _guardar(
            sesion, TUBERIA, "Otra descripcion", APU_TUBERIA.unidad, "100", _tablas()
        )
        assert guardado.precio_unitario is None and guardado.mensaje is None
        assert guardado.motivo is not None
        assert guardado.motivo.startswith(f"la partida {TUBERIA} ya existe con la descripcion")
        assert _contar(sesion, models.Rendimiento) == antes


def test_con_advertencia_y_justificacion_se_justifica_el_rendimiento_nuevo(
    base_con_rango: Path,
) -> None:
    with _sesion(base_con_rango) as sesion:
        guardado = _guardar(
            sesion,
            TUBERIA,
            APU_TUBERIA.descripcion,
            APU_TUBERIA.unidad,
            "150",
            _tablas(),
            justificacion=JUSTIFICACION,
        )
        sesion.commit()
    assert guardado.justificada is True
    assert guardado.mensaje is not None
    assert guardado.mensaje.endswith(
        " Justificacion de la advertencia registrada junto al rendimiento 150 (UC-06, flujo 4a)."
    )
    assert guardado.avisos == ()
    with _sesion(base_con_rango) as sesion:
        [justificacion] = sesion.scalars(select(models.JustificacionRendimiento)).all()
    assert justificacion.texto == JUSTIFICACION
    assert "se aparta" in justificacion.advertencia


def test_con_advertencia_y_sin_justificacion_avisa_y_no_justifica(base_con_rango: Path) -> None:
    with _sesion(base_con_rango) as sesion:
        guardado = _guardar(
            sesion,
            TUBERIA,
            APU_TUBERIA.descripcion,
            APU_TUBERIA.unidad,
            "150",
            _tablas(),
            justificacion="   ",
        )
        assert _contar(sesion, models.JustificacionRendimiento) == 0
    assert guardado.justificada is False
    assert guardado.avisos == (
        "El rendimiento se guardo con la advertencia y sin justificacion (UC-06, flujo 4a): la "
        "advertencia informa, no impide el registro (RF-27).",
    )


def test_sin_advertencia_la_justificacion_se_ignora(base_con_rango: Path) -> None:
    with _sesion(base_con_rango) as sesion:
        guardado = _guardar(
            sesion,
            TUBERIA,
            APU_TUBERIA.descripcion,
            APU_TUBERIA.unidad,
            "105",
            _tablas(),
            justificacion=JUSTIFICACION,
        )
        assert _contar(sesion, models.JustificacionRendimiento) == 0
    assert guardado.justificada is False
    assert guardado.avisos == ()
