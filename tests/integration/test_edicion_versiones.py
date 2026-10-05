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
from core.contracts import Hallazgo, Severidad
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import items_auditados
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

D = Decimal
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
    # aritmetica a mano: +1,5 sacos de cemento a 15 USD por m3 de concreto, con administracion y
    # utilidad en cascada (1,15 x 1,10), sobre la cantidad de concreto del computo auditado
    delta_pu = D("1.5") * D("15") * D("1.15") * D("1.10")
    cantidad_concreto = sum(
        (i.cantidad for i in items_auditados() if i.codigo_partida == CODIGO_CONCRETO), D(0)
    )
    assert delta_pu == D("28.4625")
    assert abs(
        (recargada.presupuesto.total - linea_base.TOTAL_EXACTO_LINEA_BASE)
        - cantidad_concreto * delta_pu
    ) <= D("1e-9")


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

    congeladas = composiciones_de_version(sesion, nueva)
    assert set(congeladas) == set(linea_base.CODIGOS_LINEA_BASE)
    # los valores, no solo los codigos: cada composicion es la de la linea base, linea a linea
    for apu in linea_base.APUS_LINEA_BASE:
        assert congeladas[apu.codigo_partida] == apu, apu.codigo_partida


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


# ---------------------------------------------------------------------------------------------
# Restaurar: bordes (version inexistente, descartada, sin instantanea y catalogo cambiado)
# ---------------------------------------------------------------------------------------------


def test_restaurar_una_version_inexistente_es_un_error_y_no_deja_filas(sesion, v001):
    with pytest.raises(KeyError, match="999"):
        restaurar_version(
            sesion, NOMBRE_PROYECTO, "999", "002", Catalogo(sesion),
            fuente=FUENTE, responsable=RESPONSABLE,
        )

    assert _contar(sesion, models.Presupuesto) == 1
    assert _contar(sesion, models.RegistroCambio) == 0
    assert _contar(sesion, models.VersionOrigen) == 0


def test_restaurar_una_version_descartada_crea_una_nueva_vigente_y_la_descartada_sigue_descartada(
    sesion, v001
):
    _guardar(sesion, _editada(sesion))
    sesion.commit()
    total_002 = cargar_elaboracion(
        sesion, NOMBRE_PROYECTO, "002", Catalogo(sesion)
    ).presupuesto.total
    descartar_version(sesion, NOMBRE_PROYECTO, "002", date(2026, 10, 5))
    sesion.commit()
    assert version_vigente(sesion, NOMBRE_PROYECTO).codigo == "001"

    nueva = restaurar_version(
        sesion, NOMBRE_PROYECTO, "002", "003", Catalogo(sesion),
        fuente="se reconsidera la edicion de cemento", responsable=RESPONSABLE, ahora=AHORA,
    )
    sesion.commit()

    copia = cargar_elaboracion(sesion, NOMBRE_PROYECTO, "003", Catalogo(sesion))
    assert copia.presupuesto.total == total_002 > linea_base.TOTAL_EXACTO_LINEA_BASE
    assert version_vigente(sesion, NOMBRE_PROYECTO).codigo == "003"
    descartadas = sesion.scalars(select(models.DescarteVersion.presupuesto_id)).all()
    assert descartadas == [_modelo(sesion, "002").id]  # solo la 002; la copia no nace descartada
    (registro,) = registros_de_version(sesion, nueva)
    assert (registro.clave, registro.valor_anterior, registro.valor_nuevo) == ("002", "001", "003")


def _sin_instantanea(sesion) -> None:
    from sqlalchemy import delete

    sesion.execute(delete(models.LineaComposicionVersion))
    sesion.execute(delete(models.ComposicionVersion))
    sesion.execute(delete(models.PlanVersion))
    sesion.commit()
    sesion.expire_all()


def test_restaurar_sin_instantanea_con_una_lista_nueva_en_el_catalogo_da_la_linea_base(
    sesion, v001
):
    from pathlib import Path

    from core.catalog import crear_lista_desde_archivo

    muestra = Path(__file__).resolve().parents[2] / "data/samples/precios/lista_2026-06-01.csv"
    crear_lista_desde_archivo(
        sesion, muestra, nombre="L", moneda="USD", fecha_vigencia=date(2026, 6, 1), origen="m"
    )
    _sin_instantanea(sesion)

    nueva = restaurar_version(
        sesion, NOMBRE_PROYECTO, CODIGO, "002", Catalogo(sesion),
        fuente=FUENTE, responsable=RESPONSABLE,
    )

    # la 001 referencia su propia lista: una lista posterior en el catalogo no la mueve
    congeladas = composiciones_de_version(sesion, nueva)
    for apu in linea_base.APUS_LINEA_BASE:
        assert congeladas[apu.codigo_partida] == apu, apu.codigo_partida
    total = cargar_elaboracion(sesion, NOMBRE_PROYECTO, "002", Catalogo(sesion)).presupuesto.total
    assert total == linea_base.TOTAL_EXACTO_LINEA_BASE


def test_restaurar_sin_instantanea_con_la_lista_de_la_version_editada_se_rechaza_sin_filas(
    sesion, v001
):
    _sin_instantanea(sesion)
    lista = _modelo(sesion, CODIGO).lista_precios
    cemento = next(p for p in lista.precios if p.insumo.descripcion == "Cemento Portland")
    cemento.precio = D("99")  # el catalogo ya no reproduce el precio unitario guardado
    sesion.commit()

    with pytest.raises(ValueError, match="LB-04-CON|precio"):
        restaurar_version(
            sesion, NOMBRE_PROYECTO, CODIGO, "002", Catalogo(sesion),
            fuente=FUENTE, responsable=RESPONSABLE,
        )
    sesion.rollback()

    assert _contar(sesion, models.Presupuesto) == 1
    assert _contar(sesion, models.RegistroCambio) == 0


# ---------------------------------------------------------------------------------------------
# SF3 R-7: el insumo de cada linea se hereda de la instantanea de origen, no se re-resuelve
# ---------------------------------------------------------------------------------------------


def _lineas(sesion, codigo):
    """`{(partida, orden): (descripcion, precio, insumo_id)}` de la instantanea de la version."""
    modelo = _modelo(sesion, codigo)
    return {
        (fila.codigo_partida, linea.orden): (linea.descripcion, linea.precio, linea.insumo_id)
        for fila in sesion.scalars(
            select(models.ComposicionVersion).where(
                models.ComposicionVersion.presupuesto_id == modelo.id
            )
        )
        for linea in fila.lineas
    }


def test_restaurar_copia_el_insumo_id_de_cada_linea_de_la_instantanea_de_origen(sesion, v001):
    modelo = _modelo(sesion, CODIGO)
    filas = sesion.scalars(
        select(models.LineaComposicionVersion)
        .join(models.ComposicionVersion)
        .where(models.ComposicionVersion.presupuesto_id == modelo.id)
        .order_by(models.LineaComposicionVersion.id)
    ).all()
    # sembrados que el re-resolutor por tipo, descripcion y precio no reproduciria: una linea de
    # precio manual (sin insumo) y otra apuntando a un insumo de otra descripcion
    filas[0].insumo_id = None
    ajeno = sesion.scalars(
        select(models.Insumo)
        .where(models.Insumo.descripcion != filas[1].descripcion)
        .order_by(models.Insumo.id)
    ).first()
    filas[1].insumo_id = ajeno.id
    sesion.commit()
    esperado = _lineas(sesion, CODIGO)
    assert sum(1 for v in esperado.values() if v[2] is None) >= 1

    restaurar_version(
        sesion, NOMBRE_PROYECTO, CODIGO, "002", Catalogo(sesion),
        fuente=FUENTE, responsable=RESPONSABLE,
    )

    assert _lineas(sesion, "002") == esperado


def test_una_edicion_de_cantidad_hereda_el_insumo_de_todas_las_lineas(sesion, v001):
    _guardar(sesion, _editada(sesion))

    origen, copia = _lineas(sesion, CODIGO), _lineas(sesion, "002")

    assert copia.keys() == origen.keys()
    assert {k: v[2] for k, v in copia.items()} == {k: v[2] for k, v in origen.items()}


def test_un_precio_editado_a_mano_pierde_su_insumo_y_las_demas_lineas_lo_conservan(
    sesion, v001
):
    """Regla (SF3 R-7): una linea cuyo precio difiere del de la instantanea de origen es un precio
    manual; queda sin `insumo_id` para que UC-02 no la revalore con la lista. Las demas heredan."""
    from dataclasses import replace

    composiciones = composiciones_de_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))
    concreto = composiciones[CODIGO_CONCRETO]
    composiciones[CODIGO_CONCRETO] = replace(
        concreto,
        materiales=tuple(
            replace(m, precio=D("20")) if m.descripcion == "Cemento Portland" else m
            for m in concreto.materiales
        ),
    )
    editada = elaborar_editada(sesion, composiciones, "002")
    cambio = CambioEditado("apu", f"{CODIGO_CONCRETO}|Cemento Portland", "precio", "15", "20")

    _guardar(sesion, editada, cambios=(cambio,))

    origen, copia = _lineas(sesion, CODIGO), _lineas(sesion, "002")
    cemento = [
        k for k, v in copia.items() if k[0] == CODIGO_CONCRETO and v[0] == "Cemento Portland"
    ]
    assert len(cemento) == 1
    assert copia[cemento[0]][1:] == (D("20"), None)
    assert origen[cemento[0]][2] is not None
    assert copia.keys() == origen.keys()
    for clave, (_, _, insumo) in origen.items():
        if clave != cemento[0]:
            assert copia[clave][2] == insumo, clave


# ---------------------------------------------------------------------------------------------
# RF-57 (parte del nucleo): el cambio de un parametro se guarda, se registra y recarga
# ---------------------------------------------------------------------------------------------


def _pu_por_partida(sesion, codigo) -> dict[str, Decimal]:
    cargado = cargar_elaboracion(sesion, NOMBRE_PROYECTO, codigo, Catalogo(sesion))
    partidas = cargado.presupuesto.partidas
    return {p.item.codigo_partida: p.resultado.precio_unitario for p in partidas}


def test_editar_el_fcas_se_guarda_se_registra_y_la_version_recarga_con_los_pu_a_mano(sesion, v001):
    """RF-57 en el nucleo. `guardar_edicion` NO recalcula (lo hace quien edita: la hoja elabora con
    los parametros nuevos y pasa el resultado); lo que el nucleo garantiza es que el parametro
    queda en la version, el cambio queda registrado y la recarga calcula con ese parametro.

    Oraculo a mano: bajar el FCAS de 6,00 a 5,00 resta, por unidad de partida, la mano de obra a
    jornal sin prestaciones (Σ cantidad x sueldo / rendimiento) x 1,15 x 1,10; el destajo no cambia.
    """
    from core.budget import elaborar
    from core.contracts.apu import ModalidadManoObra, ParametrosCosto

    nuevos = ParametrosCosto(fcas=D("5.00"))
    composiciones = composiciones_de_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion))
    editada = elaborar(
        items_auditados(),
        composiciones,
        nuevos,
        codigo="002",
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan_secuencial,
    )
    cambio = CambioEditado("parametro", "fcas", "valor", "6.00", "5.00")

    nueva = guardar_edicion(
        sesion, NOMBRE_PROYECTO, CODIGO, editada, nuevos, [cambio],
        fuente=FUENTE, responsable=RESPONSABLE, ahora=AHORA,
    )
    sesion.commit()

    assert nueva.fcas == D("5.00")
    assert _modelo(sesion, CODIGO).fcas == D("6.00")  # la 001 conserva el suyo
    (registro,) = registros_de_version(sesion, nueva)
    assert (registro.objeto, registro.clave, registro.valor_anterior, registro.valor_nuevo) == (
        "parametro", "fcas", "6.00", "5.00",
    )
    antes, despues = _pu_por_partida(sesion, CODIGO), _pu_por_partida(sesion, "002")
    assert antes == {k: v for k, v in linea_base.PRECIO_UNITARIO_EXACTO.items()}
    assert set(despues) == set(antes) == set(linea_base.CODIGOS_LINEA_BASE)
    for apu in linea_base.APUS_LINEA_BASE:
        jornal = sum(
            (
                m.cantidad * m.sueldo
                for m in apu.mano_obra
                if m.modalidad is ModalidadManoObra.JORNAL
            ),
            D(0),
        )
        a_mano = antes[apu.codigo_partida] - jornal / apu.rendimiento * D("1.15") * D("1.10")
        assert abs(despues[apu.codigo_partida] - a_mano) <= D("1e-9"), apu.codigo_partida


# ---------------------------------------------------------------------------------------------
# RF-62: un hallazgo de regla externa (R8) sobrevive a restaurar
# ---------------------------------------------------------------------------------------------

R8 = Hallazgo(
    regla="R8",
    severidad=Severidad.ADVERTENCIA,
    descripcion="fila con origen de medida supuesto",
    impacto=D("2.5"),
    origen_ids=("LB-01-EXC",),
    valor_observado=D("1.25"),
    valor_esperado=D("1"),
)


@pytest.fixture
def v001_con_r8(sesion):
    """La 001 guardada con un hallazgo R8 que `REGLAS` (R1 a R7) no evalua."""
    from dataclasses import replace

    resultado = elaborar_001(sesion)
    informe = replace(resultado.informe, hallazgos=resultado.informe.hallazgos + (R8,))
    guardar_001(sesion, sembrar(sesion), replace(resultado, informe=informe))
    sesion.commit()
    sesion.expunge_all()
    return informe


def test_restaurar_conserva_el_hallazgo_externo_y_el_informe_recargado_es_identico(
    sesion, v001_con_r8
):
    emitido = v001_con_r8
    assert [h for h in emitido.hallazgos if h.regla == "R8"] == [R8]

    restaurar_version(
        sesion, NOMBRE_PROYECTO, CODIGO, "002", Catalogo(sesion),
        fuente=FUENTE, responsable=RESPONSABLE,
    )
    sesion.commit()
    sesion.expunge_all()

    original = cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion)).informe
    copia = cargar_elaboracion(sesion, NOMBRE_PROYECTO, "002", Catalogo(sesion)).informe
    assert [h for h in copia.hallazgos if h.regla == "R8"] == [R8]
    assert original.hallazgos == emitido.hallazgos
    assert copia.hallazgos == original.hallazgos
    assert copia.cumple == original.cumple
    guardados = sesion.scalar(
        select(func.count())
        .select_from(models.Hallazgo)
        .where(
            models.Hallazgo.regla == "R8",
            models.Hallazgo.presupuesto_id == _modelo(sesion, "002").id,
        )
    )
    assert guardados == 1


# ---------------------------------------------------------------------------------------------
# SF3 R-9: sin sesion no hay lectura; el modulo de instantanea no importa a persistencia
# ---------------------------------------------------------------------------------------------


def test_un_presupuesto_sin_sesion_falla_con_un_mensaje_claro():
    from core.budget.persistencia import _presupuesto_de

    suelto = models.Presupuesto(codigo="X")

    with pytest.raises(ValueError, match="sesion"):
        _presupuesto_de(suelto, None)


def test_instantanea_no_importa_persistencia_dentro_de_sus_funciones():
    import inspect

    from core.budget import instantanea

    assert "core.budget.persistencia" not in inspect.getsource(instantanea)
