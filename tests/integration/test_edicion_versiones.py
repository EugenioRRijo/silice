"""SF-E2 (RF-52 a RF-54, spec 9.3): guardar una edicion, registrar el cambio y restaurar.

Guardar crea una version nueva con su `version_origen` y un `RegistroCambio` por celda, exige fuente
y responsable, y NO crea versiones ni registros vacios (FR-4). Restaurar la version N crea una
version nueva copia de N; la vigente es la de mayor id no descartada. Todo ocurre en una sola
`Session`, y un gancho de quien llama (la hoja, que copia sus filas `esp_*`) corre en la misma
transaccion sin que `core` conozca esas tablas.

Oraculos independientes: consultas propias a `models.Presupuesto`, `models.VersionOrigen` y
`models.RegistroCambio`, y la version 001 recargada antes y despues (debe ser identica).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from core import models
from core.budget import (
    actualizar_precios,
    cargar_elaboracion,
    descartar_version,
    plan_secuencial,
)
from core.budget.edicion import (
    CambioEditado,
    guardar_edicion,
    registros_de_version,
    restaurar_version,
    siguiente_codigo,
    version_vigente,
)
from core.budget.instantanea import (
    asegurar_instantanea,
    composiciones_de_presupuesto,
    composiciones_de_version,
    plan_de_version,
)
from core.budget.persistencia import _buscar
from core.catalog import Catalogo
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.versiones import (
    CAMBIO_CEMENTO,
    CODIGO_CONCRETO,
    FUENTE,
    RESPONSABLE,
    con_cemento,
    elaborar_001,
    elaborar_editada,
    guardar_001,
)

CODIGO = linea_base.CODIGO_PRESUPUESTO
AHORA = datetime(2026, 10, 5, 9, 30, 15)


@pytest.fixture
def v001(sesion):
    resultado = elaborar_001(sesion)
    guardar_001(sesion, sembrar(sesion), resultado)
    sesion.commit()
    return resultado


def _editada(sesion, codigo="002", plan=plan_secuencial):
    """La 001 con mas cemento en el concreto, elaborada como la hoja: composiciones de la version
    editadas, mismas cantidades, parametros y plan."""
    composiciones = composiciones_de_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))
    composiciones[CODIGO_CONCRETO] = con_cemento(composiciones[CODIGO_CONCRETO])
    return elaborar_editada(sesion, composiciones, codigo, plan)


def _guardar(sesion, resultado, cambios=(CAMBIO_CEMENTO,), **opciones):
    argumentos = {"fuente": FUENTE, "responsable": RESPONSABLE, "ahora": AHORA}
    argumentos.update(opciones)
    return guardar_edicion(
        sesion,
        NOMBRE_PROYECTO,
        argumentos.pop("origen", CODIGO),
        resultado,
        linea_base.PARAMETROS_LINEA_BASE,
        list(cambios),
        **argumentos,
    )


def _contar(sesion, tabla) -> int:
    return sesion.scalar(select(func.count()).select_from(tabla))


def _modelo(sesion, codigo) -> models.Presupuesto:
    return _buscar(sesion, NOMBRE_PROYECTO, codigo)


# ---------------------------------------------------------------------------------------------
# Guardar exige fuente y responsable; sin cambios no crea nada (FR-4)
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fuente", "responsable", "campo"),
    [("", RESPONSABLE, "fuente"), ("   ", RESPONSABLE, "fuente"), (FUENTE, "", "responsable"),
     (FUENTE, "  ", "responsable")],
)
def test_guardar_sin_fuente_o_sin_responsable_se_rechaza_y_no_deja_filas(
    sesion, v001, fuente, responsable, campo
):
    editada = _editada(sesion)

    with pytest.raises(ValueError, match=campo):
        _guardar(sesion, editada, fuente=fuente, responsable=responsable)

    assert _contar(sesion, models.Presupuesto) == 1
    assert _contar(sesion, models.RegistroCambio) == 0
    assert _contar(sesion, models.VersionOrigen) == 0


def test_sin_cambios_no_crea_version_ni_registros(sesion, v001):
    resultado = _guardar(sesion, v001, cambios=())

    assert resultado is None
    assert _contar(sesion, models.Presupuesto) == 1
    assert _contar(sesion, models.RegistroCambio) == 0


def test_un_cambio_que_vuelve_al_valor_anterior_no_cuenta(sesion, v001):
    igual = CambioEditado("apu", "LB-04-CON|Cemento Portland", "cantidad", "7.5", "7.5")

    assert _guardar(sesion, v001, cambios=(igual,)) is None
    assert _contar(sesion, models.Presupuesto) == 1


def test_guardar_dos_veces_sin_cambios_deja_una_sola_version_nueva(sesion, v001):
    primera = _guardar(sesion, _editada(sesion))
    sesion.commit()
    segunda = _guardar(sesion, _editada(sesion, "003"), cambios=(), origen="002")
    sesion.commit()

    assert primera is not None
    assert segunda is None
    assert _contar(sesion, models.Presupuesto) == 2
    assert _contar(sesion, models.RegistroCambio) == 1


def test_el_objeto_debe_ser_uno_de_los_conocidos(sesion, v001):
    raro = CambioEditado("cosa", "x", "y", "1", "2")

    with pytest.raises(ValueError, match="objeto"):
        _guardar(sesion, _editada(sesion), cambios=(raro,))

    assert _contar(sesion, models.Presupuesto) == 1


def test_un_codigo_de_version_repetido_se_rechaza_sin_dejar_filas(sesion, v001):
    with pytest.raises(ValueError, match="001"):
        _guardar(sesion, _editada(sesion, codigo=CODIGO))

    assert _contar(sesion, models.RegistroCambio) == 0
    assert _contar(sesion, models.Presupuesto) == 1


# ---------------------------------------------------------------------------------------------
# La version nueva
# ---------------------------------------------------------------------------------------------


def test_guardar_crea_la_version_con_origen_instantanea_y_un_registro_completo(sesion, v001):
    editada = _editada(sesion)

    nueva = _guardar(sesion, editada)
    sesion.commit()

    assert nueva is not None and nueva.codigo == "002"
    origen = sesion.get(models.VersionOrigen, nueva.id)
    assert (origen.origen_id, origen.motivo) == (_modelo(sesion, CODIGO).id, "edicion")
    registros = registros_de_version(sesion, nueva)
    assert len(registros) == 1
    r = registros[0]
    assert (r.objeto, r.clave, r.campo) == ("apu", CAMBIO_CEMENTO.clave, "cantidad")
    assert (r.valor_anterior, r.valor_nuevo) == ("7.5", "9")
    assert (r.fuente, r.responsable, r.fecha_hora) == (FUENTE, RESPONSABLE, AHORA)
    assert r.version_origen_id == _modelo(sesion, CODIGO).id
    assert r.version_resultante_id == nueva.id
    assert r.proyecto_id == nueva.proyecto_id
    cemento = next(
        m
        for m in composiciones_de_version(sesion, nueva)[CODIGO_CONCRETO].materiales
        if m.descripcion == "Cemento Portland"
    )
    assert cemento.cantidad == Decimal("9")
    recargada = cargar_elaboracion(sesion, NOMBRE_PROYECTO, "002", Catalogo(sesion))
    assert recargada.presupuesto.total == editada.presupuesto.total
    assert editada.presupuesto.total > linea_base.TOTAL_EXACTO_LINEA_BASE


def test_un_registro_por_celda_cambiada(sesion, v001):
    cambios = (
        CAMBIO_CEMENTO,
        CambioEditado("parametro", "fcas", "valor", "6.00", "5.00"),
        CambioEditado("plan", "LB-01-EXC", "periodo", "1", "2"),
    )

    nueva = _guardar(sesion, _editada(sesion), cambios=cambios)

    assert [(r.objeto, r.campo) for r in registros_de_version(sesion, nueva)] == [
        ("apu", "cantidad"),
        ("parametro", "valor"),
        ("plan", "periodo"),
    ]


def test_la_version_anterior_sigue_cargando_identica(sesion, v001):
    antes = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))

    _guardar(sesion, _editada(sesion))
    sesion.commit()
    sesion.expunge_all()

    despues = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))
    assert despues.presupuesto == antes.presupuesto
    assert despues.informe.hallazgos == antes.informe.hallazgos


def test_el_plan_de_la_edicion_se_conserva(sesion, v001):
    plan = plan_secuencial(v001.presupuesto)

    nueva = _guardar(sesion, _editada(sesion, plan=plan), plan=plan)

    assert plan_de_version(sesion, nueva) == [(e, tuple(r)) for e, r in plan]


def test_el_gancho_corre_en_la_misma_sesion_con_la_version_ya_creada(sesion, v001):
    vistos = []

    def gancho(session, modelo):
        vistos.append((session is sesion, modelo.id is not None, modelo.codigo))

    nueva = _guardar(sesion, _editada(sesion), gancho=gancho)

    assert vistos == [(True, True, "002")]
    assert nueva.id is not None


def test_si_el_gancho_falla_y_quien_llama_deshace_no_queda_nada(sesion, v001):
    def gancho(session, modelo):
        raise RuntimeError("falla al copiar las filas de la hoja")

    with pytest.raises(RuntimeError):
        _guardar(sesion, _editada(sesion), gancho=gancho)
    sesion.rollback()

    assert _contar(sesion, models.Presupuesto) == 1
    assert _contar(sesion, models.RegistroCambio) == 0
    assert _contar(sesion, models.VersionOrigen) == 0
    assert _contar(sesion, models.ComposicionVersion) == len(linea_base.APUS_LINEA_BASE)


def test_siguiente_codigo(sesion, v001):
    assert siguiente_codigo(sesion, NOMBRE_PROYECTO) == "002"
    _guardar(sesion, _editada(sesion))
    assert siguiente_codigo(sesion, NOMBRE_PROYECTO) == "003"


# ---------------------------------------------------------------------------------------------
# Restaurar y versión vigente
# ---------------------------------------------------------------------------------------------


def test_restaurar_crea_una_version_copia_de_n_y_n_sigue_existiendo(sesion, v001):
    _guardar(sesion, _editada(sesion))
    sesion.commit()
    catalogo = Catalogo(sesion)

    nueva = restaurar_version(
        sesion, NOMBRE_PROYECTO, CODIGO, "003", catalogo,
        fuente="se descarta la edicion de cemento", responsable=RESPONSABLE, ahora=AHORA,
    )
    sesion.commit()

    original = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, catalogo)
    copia = cargar_elaboracion(sesion, NOMBRE_PROYECTO, "003", catalogo)
    assert nueva.codigo == "003"
    assert {m.codigo for m in sesion.scalars(select(models.Presupuesto))} == {"001", "002", "003"}
    assert copia.presupuesto.partidas == original.presupuesto.partidas
    assert copia.presupuesto.curva == original.presupuesto.curva
    assert copia.presupuesto.total == linea_base.TOTAL_EXACTO_LINEA_BASE
    assert copia.informe.hallazgos == original.informe.hallazgos
    assert plan_de_version(sesion, nueva) == plan_de_version(sesion, _modelo(sesion, CODIGO))
    origen = sesion.get(models.VersionOrigen, nueva.id)
    assert (origen.origen_id, origen.motivo) == (_modelo(sesion, CODIGO).id, "restauracion")
    (registro,) = registros_de_version(sesion, nueva)
    assert (registro.objeto, registro.campo) == ("version", "restauracion")
    assert registro.fuente == "se descarta la edicion de cemento"
    assert version_vigente(sesion, NOMBRE_PROYECTO).codigo == "003"


def test_restaurar_exige_fuente_y_responsable(sesion, v001):
    with pytest.raises(ValueError, match="fuente"):
        restaurar_version(
            sesion, NOMBRE_PROYECTO, CODIGO, "002", Catalogo(sesion),
            fuente="", responsable=RESPONSABLE,
        )
    with pytest.raises(ValueError, match="responsable"):
        restaurar_version(
            sesion, NOMBRE_PROYECTO, CODIGO, "002", Catalogo(sesion),
            fuente=FUENTE, responsable="",
        )
    assert _contar(sesion, models.Presupuesto) == 1


def test_restaurar_una_version_sin_instantanea_funciona_y_la_nueva_si_la_tiene(sesion, v001):
    from sqlalchemy import delete

    modelo = _modelo(sesion, CODIGO)
    ids = select(models.ComposicionVersion.id).where(
        models.ComposicionVersion.presupuesto_id == modelo.id
    )
    sesion.execute(
        delete(models.LineaComposicionVersion).where(
            models.LineaComposicionVersion.composicion_id.in_(ids)
        )
    )
    sesion.execute(delete(models.ComposicionVersion))
    sesion.execute(delete(models.PlanVersion))
    sesion.commit()
    sesion.expire_all()

    nueva = restaurar_version(
        sesion, NOMBRE_PROYECTO, CODIGO, "002", Catalogo(sesion),
        fuente=FUENTE, responsable=RESPONSABLE,
    )

    assert set(composiciones_de_version(sesion, nueva)) == set(linea_base.CODIGOS_LINEA_BASE)


def test_la_version_vigente_es_la_de_mayor_id_no_descartada(sesion, v001):
    assert version_vigente(sesion, NOMBRE_PROYECTO).codigo == "001"
    _guardar(sesion, _editada(sesion))
    sesion.commit()
    assert version_vigente(sesion, NOMBRE_PROYECTO).codigo == "002"

    descartar_version(sesion, NOMBRE_PROYECTO, "002", date(2026, 10, 5))

    assert version_vigente(sesion, NOMBRE_PROYECTO).codigo == "001"


def test_un_proyecto_sin_versiones_no_tiene_vigente(sesion):
    sembrar(sesion)

    assert version_vigente(sesion, NOMBRE_PROYECTO) is None


# ---------------------------------------------------------------------------------------------
# version_origen en toda version nueva
# ---------------------------------------------------------------------------------------------


def test_la_revaloracion_por_uc02_declara_su_version_de_origen(sesion, v001):
    from pathlib import Path

    from core.catalog import crear_lista_desde_archivo

    muestra = Path(__file__).resolve().parents[2] / "data/samples/precios/lista_2026-06-01.csv"
    lista = crear_lista_desde_archivo(
        sesion, muestra, nombre="L", moneda="USD", fecha_vigencia=date(2026, 6, 1), origen="m"
    ).lista

    actualizar_precios(sesion, NOMBRE_PROYECTO, CODIGO, lista, "002")

    origen = sesion.get(models.VersionOrigen, _modelo(sesion, "002").id)
    assert (origen.origen_id, origen.motivo) == (_modelo(sesion, CODIGO).id, "revaloracion")
    assert sesion.get(models.VersionOrigen, _modelo(sesion, CODIGO).id) is None


# ---------------------------------------------------------------------------------------------
# UC-15e: la instantanea creada al abrir se registra
# ---------------------------------------------------------------------------------------------


def test_asegurar_instantanea_registra_su_creacion_una_sola_vez(sesion, v001):
    from sqlalchemy import delete

    sesion.execute(delete(models.LineaComposicionVersion))
    sesion.execute(delete(models.ComposicionVersion))
    sesion.commit()
    sesion.expire_all()

    asegurar_instantanea(
        sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion), responsable="Ing. Prueba", ahora=AHORA
    )
    asegurar_instantanea(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))

    (registro,) = registros_de_version(sesion, _modelo(sesion, CODIGO))
    assert (registro.objeto, registro.campo) == ("apu", "instantanea")
    assert registro.responsable == "Ing. Prueba"
    assert "UC-15e" in registro.fuente
    assert registro.fecha_hora == AHORA
