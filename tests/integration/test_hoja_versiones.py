"""La hoja del proyecto contra una base real (SF3, spec §5.3, §8.4 y §9.3): abrir, guardar,
restaurar, heredar el espacio, cotizar y exportar, todo en `ui.hoja` y sin Streamlit.

Casos: OF-001 (con su espacio `esp_*`), la clinica de la linea base (sin espacio ni hoja: FR-5) y
TI-001 (sin espacio, con plan). Oraculos independientes de la hoja: los literales documentados
(2 703,86 USD de OF-001; 1 586,61 de la linea base; 50 503,27 USD y punto de equilibrio de
28 586,76 en el Dia 6 de TI-001), el precio unitario y el costo directo que la version GUARDADA
trae en cada renglon, y las consultas propias a `models.*` y a las tablas `esp_*`. Cada prueba
trabaja sobre una copia de un archivo temporal sembrado una sola vez.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import pytest
from openpyxl import load_workbook
from sqlalchemy import func, select

from adapters.espacio import cargar_espacio, guardar_espacio
from aplicacion import hoja
from core import models
from core.budget import cargar_elaboracion
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts import ParametrosCosto
from scripts.seed import NOMBRE_PROYECTO as NOMBRE_CLINICA
from scripts.seed import sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.evaluador_excel import _celda, evaluar
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    NOMBRE_TI001,
    borrar_instantanea,
    plantilla_of001,
    plantilla_ti001,
)
from tests.fixtures.versiones import elaborar_001, guardar_001

D = Decimal
AHORA = datetime(2026, 10, 5, 14, 0, 0)
FUENTE = "memoria de calculo rev. C, hoja 4"
RESPONSABLE = "Ing. Prueba"


@pytest.fixture(scope="module")
def _plantilla_of(tmp_path_factory):
    return plantilla_of001(tmp_path_factory.mktemp("hoja_of") / "of001.db")


@pytest.fixture(scope="module")
def _plantilla_ti(tmp_path_factory):
    return plantilla_ti001(tmp_path_factory.mktemp("hoja_ti") / "ti001.db")


def _abrir(plantilla, tmp_path):
    copia = tmp_path / "copia.db"
    shutil.copy(plantilla, copia)
    motor = crear_motor(f"sqlite:///{copia.as_posix()}")
    return motor, abrir_sesion(motor)


@pytest.fixture
def of001(_plantilla_of, tmp_path):
    motor, sesion = _abrir(_plantilla_of, tmp_path)
    with sesion:
        yield sesion, Catalogo(sesion)
    motor.dispose()


@pytest.fixture
def ti001(_plantilla_ti, tmp_path):
    motor, sesion = _abrir(_plantilla_ti, tmp_path)
    with sesion:
        yield sesion, Catalogo(sesion)
    motor.dispose()


def _contar(sesion, tabla) -> int:
    return sesion.scalar(select(func.count()).select_from(tabla))


def _modelo(sesion, proyecto, codigo) -> models.Presupuesto:
    return sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
    ).one()


def _filas_esp(sesion, version_id) -> int:
    from sqlalchemy import text

    return sesion.execute(
        text("SELECT COUNT(*) FROM esp_ambientes WHERE version_id = :v"), {"v": version_id}
    ).scalar_one()


# ---------------------------------------------------------------------------------------------
# Abrir una version
# ---------------------------------------------------------------------------------------------


def test_abrir_la_version_de_la_hoja_recarga_su_espacio_y_el_total_de_la_memoria(of001):
    sesion, catalogo = of001

    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")

    assert abierta.borrador.espacio == espacio_of001()
    assert abierta.espacio_de == "001"
    assert abierta.borrador.items_base == ()
    assert dict(abierta.borrador.cantidades) == {}
    assert abs(abierta.guardada.presupuesto.total - D("2703.86")) <= D("0.01")
    assert abierta.instantanea.creadas == ()  # la 001 ya nacio con su instantanea


def test_el_borrador_abierto_elabora_lo_mismo_que_la_version_guardada(of001):
    sesion, catalogo = of001
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")

    vivo = hoja.elaborar_borrador(abierta.borrador, codigo="001")

    assert vivo.elaboracion.presupuesto.total == abierta.guardada.presupuesto.total
    assert set(vivo.elaboracion.informe.hallazgos) == set(abierta.guardada.informe.hallazgos)
    assert vivo.elaboracion.presupuesto.curva == abierta.guardada.presupuesto.curva
    # sin tocar nada no hay nada que guardar
    assert hoja.cambios_entre(abierta.borrador, abierta.borrador) == []


def test_el_conjunto_exacto_de_hallazgos_de_la_hoja_abierta_es_el_de_of001(of001):
    """OF-001 limpia no da cero hallazgos: 33 advertencias de R8 (origen supuesto), y nada mas."""
    sesion, catalogo = of001

    informe = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001").guardada.informe

    assert {(h.regla, h.severidad.name) for h in informe.hallazgos} == {("R8", "ADVERTENCIA")}
    assert len(informe.hallazgos) == 33


def test_la_reauditoria_reemplaza_los_hallazgos_guardados_de_r8_a_r10_no_los_suma(of001):
    """§8.4: al abrir, R8 a R10 se vuelven a correr sobre la instantanea del espacio y
    REEMPLAZAN los guardados de esas reglas. Se siembran dos desfases: un hallazgo falso de R8 en
    la base, y una fila `esp_*` alterada (un ambiente mas bajo que sus puntos: R9)."""
    sesion, catalogo = of001
    modelo = _modelo(sesion, NOMBRE_OF001, "001")
    sesion.add(
        models.Hallazgo(
            regla="R8",
            severidad=3,
            descripcion="hallazgo viejo que ya no existe",
            origen_ids='["esp_puntos:FANTASMA"]',
            presupuesto_id=modelo.id,
        )
    )
    espacio = espacio_of001()
    bajo = replace(espacio.ambientes[0], alto=D("0.3"))
    guardar_espacio(sesion, modelo.id, replace(espacio, ambientes=(bajo, *espacio.ambientes[1:])))
    sesion.commit()

    informe = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001").guardada.informe

    descripciones = [h.descripcion for h in informe.hallazgos]
    assert "hallazgo viejo que ya no existe" not in descripciones
    assert any(h.regla == "R9" for h in informe.hallazgos)  # la reauditoria vio el espacio nuevo
    assert len(descripciones) == len(set(descripciones))  # nada duplicado
    assert sum(1 for h in informe.hallazgos if h.regla == "R8") == 33


# ---------------------------------------------------------------------------------------------
# Guardar: fuente y responsable, sin cambios, atomicidad
# ---------------------------------------------------------------------------------------------


def _editar(abierta, **cambios) -> hoja.Borrador:
    return replace(abierta.borrador, **cambios)


@pytest.mark.parametrize(
    ("fuente", "responsable", "campo"),
    [("", RESPONSABLE, "fuente"), ("  ", RESPONSABLE, "fuente"), (FUENTE, "", "responsable")],
)
def test_guardar_sin_fuente_o_sin_responsable_se_rechaza_y_no_deja_filas(
    of001, fuente, responsable, campo
):
    sesion, catalogo = of001
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
    editado = _editar(abierta, parametros=ParametrosCosto(fcas=D("7")))

    assert hoja.puede_guardar(abierta.borrador, editado, fuente, responsable) is False
    assert campo in hoja.motivo_para_no_guardar(abierta.borrador, editado, fuente, responsable)
    with pytest.raises(hoja.HojaInvalida, match=campo):
        hoja.guardar_version(
            sesion, catalogo, abierta, editado, fuente=fuente, responsable=responsable
        )

    assert _contar(sesion, models.Presupuesto) == 1
    assert _contar(sesion, models.RegistroCambio) == 0


def test_guardar_sin_cambios_no_hace_nada(of001):
    sesion, catalogo = of001
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")

    assert hoja.puede_guardar(abierta.borrador, abierta.borrador, FUENTE, RESPONSABLE) is False
    assert (
        "no hay cambios"
        in hoja.motivo_para_no_guardar(
            abierta.borrador, abierta.borrador, FUENTE, RESPONSABLE
        ).lower()
    )
    resultado = hoja.guardar_version(
        sesion, catalogo, abierta, abierta.borrador, fuente=FUENTE, responsable=RESPONSABLE
    )

    assert resultado is None
    assert _contar(sesion, models.Presupuesto) == 1
    assert _contar(sesion, models.RegistroCambio) == 0
    assert _contar(sesion, models.VersionOrigen) == 0


def _guardar_edicion_completa(sesion, catalogo):
    """001 -> 002: administracion 15 % -> 20 %, AF-LLAVE de 3 a 5 a mano y un ambiente mas largo."""
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
    items = hoja.items_sin_escribir(abierta.borrador)
    llave = next(
        c
        for c, i in zip(hoja.claves_de_items(items), items, strict=True)
        if i.codigo_partida == "AF-LLAVE"
    )
    filas = hoja.filas_desde_espacio(abierta.borrador.espacio)
    filas["ambientes"][0]["largo"] = "2.5"
    editado = replace(
        abierta.borrador,
        espacio=hoja.espacio_desde_filas(filas, base=abierta.borrador.espacio),
        parametros=ParametrosCosto(
            fcas=D("6.00"),
            bono_alimentacion=abierta.borrador.parametros.bono_alimentacion,
            administracion=D("0.20"),
            utilidad=D("0.10"),
        ),
        cantidades={llave: D("5")},
    )
    guardada = hoja.guardar_version(
        sesion, catalogo, abierta, editado, fuente=FUENTE, responsable=RESPONSABLE, ahora=AHORA
    )
    return abierta, editado, guardada, llave


def test_guardar_crea_la_version_002_con_su_registro_y_el_espacio_de_la_edicion(of001):
    sesion, catalogo = of001
    antes = cargar_elaboracion(sesion, NOMBRE_OF001, "001", catalogo)

    abierta, editado, guardada, llave = _guardar_edicion_completa(sesion, catalogo)

    assert guardada.codigo == "002"
    v1, v2 = _modelo(sesion, NOMBRE_OF001, "001"), _modelo(sesion, NOMBRE_OF001, "002")
    origen = sesion.get(models.VersionOrigen, v2.id)
    assert (origen.origen_id, origen.motivo) == (v1.id, "edicion")
    registros = [
        (r.objeto, r.clave, r.campo, r.valor_anterior, r.valor_nuevo)
        for r in sesion.scalars(
            select(models.RegistroCambio)
            .where(models.RegistroCambio.version_resultante_id == v2.id)
            .order_by(models.RegistroCambio.id)
        )
    ]
    assert registros == [
        ("metraje", "esp_ambientes:BAN-01", "largo", "2", "2.5"),
        ("cantidad", llave, "cantidad", "3", "5"),
        ("parametro", "administracion", "valor", "0.15", "0.20"),
    ]
    assert guardada.cambios == 3
    todos = sesion.scalars(select(models.RegistroCambio)).all()
    assert {(r.fuente, r.responsable, r.fecha_hora) for r in todos} == {
        (FUENTE, RESPONSABLE, AHORA)
    }
    # el espacio editado se copio con la clave de la version nueva; el de la 001 sigue igual
    assert cargar_espacio(sesion, v2.id) == editado.espacio
    assert cargar_espacio(sesion, v1.id) == espacio_of001()
    # la version anterior recarga identica
    despues = cargar_elaboracion(sesion, NOMBRE_OF001, "001", catalogo)
    assert despues.presupuesto == antes.presupuesto
    assert despues.informe.hallazgos == antes.informe.hallazgos
    assert abs(abierta.guardada.presupuesto.total - antes.presupuesto.total) <= D("0.000001")


def test_el_total_de_la_version_002_es_la_aritmetica_de_la_001(of001):
    """Oraculo: cada renglon de la 001 trae su cantidad y su costo directo; con administracion
    20 % y utilidad 10 % el total de la 002 es la suma de cantidad x CD x 1,20 x 1,10, con el
    AF-LLAVE a 5 unidades. (El ambiente mas largo no mueve el AF-LLAVE ni los demas renglones
    que no dependan de su largo; se compara solo el efecto de administracion y de la cantidad.)"""
    sesion, catalogo = of001
    de_001 = cargar_elaboracion(sesion, NOMBRE_OF001, "001", catalogo).presupuesto

    _, _, guardada, _ = _guardar_edicion_completa(sesion, catalogo)

    nuevo = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "002")
    por_codigo_001 = {p.item.codigo_partida: p for p in de_001.partidas}
    for partida in nuevo.guardada.presupuesto.partidas:
        costo_directo = por_codigo_001[partida.item.codigo_partida].resultado.costo_directo
        assert partida.resultado.costo_directo == costo_directo
        assert abs(partida.resultado.precio_unitario - costo_directo * D("1.20") * D("1.10")) <= D(
            "0.000001"
        )
    llave = next(
        p for p in nuevo.guardada.presupuesto.partidas if p.item.codigo_partida == "AF-LLAVE"
    )
    assert llave.item.cantidad == D("5")
    assert guardada.total == nuevo.guardada.presupuesto.total


def test_la_cantidad_escrita_y_guardada_sigue_marcada_por_r8_al_reabrir(of001):
    sesion, catalogo = of001
    _, _, _, llave = _guardar_edicion_completa(sesion, catalogo)

    reabierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "002")

    assert dict(reabierta.borrador.cantidades) == {llave: D("5")}
    assert any(
        h.regla == "R8" and "AF-LLAVE" in h.descripcion and "a mano" in h.descripcion
        for h in reabierta.guardada.informe.hallazgos
    )
    assert hoja.cambios_entre(reabierta.borrador, reabierta.borrador) == []


def test_guardar_dos_veces_seguidas_no_crea_una_version_vacia(of001):
    """[FR-4]"""
    sesion, catalogo = of001
    _guardar_edicion_completa(sesion, catalogo)
    cuenta = (_contar(sesion, models.Presupuesto), _contar(sesion, models.RegistroCambio))

    reabierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "002")
    otra = hoja.guardar_version(
        sesion, catalogo, reabierta, reabierta.borrador, fuente=FUENTE, responsable=RESPONSABLE
    )

    assert otra is None
    assert (_contar(sesion, models.Presupuesto), _contar(sesion, models.RegistroCambio)) == cuenta


def test_si_el_gancho_falla_no_queda_nada_de_la_version(of001, monkeypatch):
    """Una sola Session: si no se puede copiar el espacio, tampoco existe la version."""
    sesion, catalogo = of001
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
    editado = _editar(abierta, parametros=ParametrosCosto(fcas=D("7")))

    def roto(*_):
        raise RuntimeError("disco lleno")

    monkeypatch.setattr(hoja, "guardar_espacio", roto)
    with pytest.raises(RuntimeError, match="disco lleno"):
        hoja.guardar_version(
            sesion, catalogo, abierta, editado, fuente=FUENTE, responsable=RESPONSABLE
        )

    assert _contar(sesion, models.Presupuesto) == 1
    assert _contar(sesion, models.RegistroCambio) == 0
    assert _contar(sesion, models.ComposicionVersion) == len(abierta.borrador.composiciones)


def test_un_plan_editado_se_guarda_y_la_curva_de_la_version_nueva_lo_sigue(of001):
    sesion, catalogo = of001
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
    plan = list(abierta.borrador.plan)
    (e0, r0), (e1, r1) = plan[0], plan[1]
    codigo = r0[0][0]
    plan[0] = (e0, ((codigo, D("0.5")),))
    plan[1] = (e1, ((codigo, D("0.5")), *r1))

    hoja.guardar_version(
        sesion,
        catalogo,
        abierta,
        _editar(abierta, plan=tuple(plan)),
        fuente=FUENTE,
        responsable=RESPONSABLE,
    )

    nueva = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "002")
    assert nueva.borrador.plan[0][1] == ((codigo, D("0.5")),)
    assert nueva.guardada.presupuesto.curva[0].monto != abierta.guardada.presupuesto.curva[0].monto
    assert nueva.guardada.presupuesto.total == abierta.guardada.presupuesto.total
    assert nueva.guardada.presupuesto.curva[-1].acumulado == nueva.guardada.presupuesto.total


# ---------------------------------------------------------------------------------------------
# Restaurar y espacio heredado
# ---------------------------------------------------------------------------------------------


def test_restaurar_crea_una_copia_nueva_vigente_y_hereda_el_espacio(of001):
    sesion, catalogo = of001
    antes = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
    _guardar_edicion_completa(sesion, catalogo)

    codigo = hoja.restaurar(
        sesion,
        catalogo,
        NOMBRE_OF001,
        "001",
        fuente="volver a la medida original",
        responsable=RESPONSABLE,
        ahora=AHORA,
    )

    assert codigo == "003"
    assert hoja.codigo_vigente(sesion, NOMBRE_OF001) == "003"
    assert _contar(sesion, models.Presupuesto) == 3  # nada se borra
    restaurada = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "003")
    assert restaurada.guardada.presupuesto.total == antes.guardada.presupuesto.total
    assert restaurada.borrador.espacio == espacio_of001()  # heredado de la 001
    assert restaurada.espacio_de == "001"
    # no copio filas esp_*: su espacio es el de su version de origen
    assert _filas_esp(sesion, _modelo(sesion, NOMBRE_OF001, "003").id) == 0
    origen = sesion.get(models.VersionOrigen, _modelo(sesion, NOMBRE_OF001, "003").id)
    assert origen.origen_id == _modelo(sesion, NOMBRE_OF001, "001").id
    assert origen.motivo == "restauracion"


def test_restaurar_una_restauracion_sube_por_la_cadena_hasta_el_espacio_propio(of001):
    sesion, catalogo = of001
    _guardar_edicion_completa(sesion, catalogo)  # 002 con espacio propio
    hoja.restaurar(sesion, catalogo, NOMBRE_OF001, "002", fuente="a", responsable=RESPONSABLE)
    hoja.restaurar(sesion, catalogo, NOMBRE_OF001, "003", fuente="b", responsable=RESPONSABLE)

    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "004")

    assert abierta.espacio_de == "002"
    assert (
        cargar_espacio(sesion, _modelo(sesion, NOMBRE_OF001, "002").id) == abierta.borrador.espacio
    )


def test_una_version_guardada_con_el_espacio_vacio_no_hereda_el_de_su_origen(of001):
    """El espacio de una version de la hoja es suyo aunque quede vacio: no sube por la cadena."""
    sesion, catalogo = of001
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
    from adapters.espacio import Espacio

    vaciado = _editar(
        abierta,
        espacio=Espacio(),
        items_base=tuple(abierta.borrador.items_base),
    )
    hoja.guardar_version(sesion, catalogo, abierta, vaciado, fuente=FUENTE, responsable=RESPONSABLE)

    reabierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "002")

    assert reabierta.borrador.espacio == Espacio()
    assert reabierta.espacio_de is None


def test_el_historial_marca_la_vigente_el_motivo_y_el_origen(of001):
    sesion, catalogo = of001
    _guardar_edicion_completa(sesion, catalogo)
    hoja.restaurar(sesion, catalogo, NOMBRE_OF001, "001", fuente="a", responsable=RESPONSABLE)

    filas = hoja.historial_de_versiones(sesion, NOMBRE_OF001)

    assert [(f.codigo, f.motivo, f.origen, f.vigente, f.cambios) for f in filas] == [
        ("001", "", "", False, 0),
        ("002", "edicion", "001", False, 3),
        ("003", "restauracion", "001", True, 1),
    ]


# ---------------------------------------------------------------------------------------------
# Cotizar y retirar
# ---------------------------------------------------------------------------------------------


def _insumo_pvc34(sesion) -> models.Insumo:
    return sesion.scalars(
        select(models.Insumo).where(
            models.Insumo.descripcion.like("Tubo PVC 3/4 pulg A.B. presion agua fria%")
        )
    ).one()


def test_cotizar_cambia_solo_ese_insumo_conserva_el_plan_y_hereda_el_espacio(of001):
    sesion, catalogo = of001
    insumo = _insumo_pvc34(sesion)
    precio = next(
        p.precio
        for p in _modelo(sesion, NOMBRE_OF001, "001").lista_precios.precios
        if p.insumo_id == insumo.id
    )
    antes = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
    cantidad = next(
        p.item.cantidad
        for p in antes.guardada.presupuesto.partidas
        if p.item.codigo_partida == "AF-TUB-PVC-3/4"
    )

    codigo = hoja.cotizar(
        sesion,
        catalogo,
        NOMBRE_OF001,
        "001",
        insumo=insumo.codigo,
        precio=precio * 2,
        proveedor="Ferreteria Los Andes",
        numero="COT-77",
        fecha=date(2026, 10, 5),
        responsable=RESPONSABLE,
        ahora=AHORA,
    )

    assert codigo == "002"
    despues = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "002")
    # el tubo de 3/4 pulg lleva 1 m de material por metro; el PU sube precio x 1,15 x 1,10
    esperado = cantidad * precio * D("1.15") * D("1.10")
    assert abs(
        (despues.guardada.presupuesto.total - antes.guardada.presupuesto.total) - esperado
    ) <= D("0.0001")
    assert despues.borrador.plan == antes.borrador.plan
    assert despues.guardada.presupuesto.curva[-1].acumulado == despues.guardada.presupuesto.total
    assert despues.espacio_de == "001" and despues.borrador.espacio == espacio_of001()
    fila = next(
        f for f in hoja.precios_de_version(sesion, NOMBRE_OF001, "002") if f.codigo == insumo.codigo
    )
    assert fila.precio == precio * 2
    assert "COT-77" in fila.cotizacion and "Ferreteria Los Andes" in fila.cotizacion
    otra = next(
        f for f in hoja.precios_de_version(sesion, NOMBRE_OF001, "002") if f.codigo != insumo.codigo
    )
    assert otra.cotizacion == ""  # la cotizacion es solo de ese insumo


def test_retirar_la_cotizacion_vuelve_al_precio_de_la_lista(of001):
    sesion, catalogo = of001
    insumo = _insumo_pvc34(sesion)
    original = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001").guardada.presupuesto.total
    precio = next(
        p.precio
        for p in _modelo(sesion, NOMBRE_OF001, "001").lista_precios.precios
        if p.insumo_id == insumo.id
    )
    hoja.cotizar(
        sesion,
        catalogo,
        NOMBRE_OF001,
        "001",
        insumo=insumo.codigo,
        precio=precio * 2,
        proveedor="Ferreteria Los Andes",
        numero="COT-77",
        fecha=date(2026, 10, 5),
        responsable=RESPONSABLE,
    )

    codigo = hoja.retirar_cotizacion(
        sesion,
        catalogo,
        NOMBRE_OF001,
        "002",
        insumo=insumo.codigo,
        fuente="el proveedor retiro la oferta",
        responsable=RESPONSABLE,
    )

    assert codigo == "003"
    assert abs(
        hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "003").guardada.presupuesto.total
        - original
    ) <= D("0.000001")


def test_cotizar_un_precio_igual_al_de_la_lista_se_rechaza_con_mensaje(of001):
    sesion, catalogo = of001
    insumo = _insumo_pvc34(sesion)
    precio = next(
        p.precio
        for p in _modelo(sesion, NOMBRE_OF001, "001").lista_precios.precios
        if p.insumo_id == insumo.id
    )

    with pytest.raises(hoja.HojaInvalida, match="ya vale"):
        hoja.cotizar(
            sesion,
            catalogo,
            NOMBRE_OF001,
            "001",
            insumo=insumo.codigo,
            precio=precio,
            proveedor="X",
            numero="1",
            fecha=date(2026, 10, 5),
            responsable=RESPONSABLE,
        )

    assert _contar(sesion, models.Presupuesto) == 1


# ---------------------------------------------------------------------------------------------
# Precios con su origen
# ---------------------------------------------------------------------------------------------


def test_los_precios_muestran_lista_moneda_fecha_y_marcan_los_que_no_tienen_fuente(of001):
    sesion, catalogo = of001

    filas = hoja.precios_de_version(sesion, NOMBRE_OF001, "001")

    assert filas
    primera = filas[0]
    assert (primera.lista, primera.moneda) == ("Lista MaPreX jul-2026 (OF-001)", "USD")
    assert primera.fecha == date(2026, 10, 5)
    # los sembradores de prueba no cargan referencia ni tasa: todos quedan marcados
    assert all("sin referencia" in f.estado.lower() for f in filas)
    assert all(f.tasa is None for f in filas)


# ---------------------------------------------------------------------------------------------
# La clinica y TI-001: abrir sin hoja (FR-5, UC-15e)
# ---------------------------------------------------------------------------------------------


@pytest.fixture
def clinica(sesion):
    resultado = elaborar_001(sesion)
    guardar_001(sesion, sembrar(sesion), resultado)
    sesion.commit()
    return sesion, Catalogo(sesion)


def test_abrir_la_clinica_no_tiene_espacio_y_da_el_total_de_la_linea_base(clinica):
    sesion, catalogo = clinica

    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_CLINICA, linea_base.CODIGO_PRESUPUESTO)

    assert abierta.espacio_de is None
    assert abierta.borrador.espacio.ambientes == ()
    assert len(abierta.borrador.items_base) == 5
    assert abs(abierta.guardada.presupuesto.total - D("1586.61")) <= D("0.01")
    vivo = hoja.elaborar_borrador(abierta.borrador, codigo=linea_base.CODIGO_PRESUPUESTO)
    assert vivo.elaboracion.presupuesto.total == abierta.guardada.presupuesto.total
    assert [h.regla for h in vivo.elaboracion.informe.hallazgos] == [
        h.regla for h in abierta.guardada.informe.hallazgos
    ]


def test_abrir_una_version_sin_instantanea_la_crea_y_deja_el_registro(clinica):
    """[FR-5] UC-15e: una base anterior a SF-E6 abre; la instantanea se crea y se registra."""
    sesion, catalogo = clinica
    borrar_instantanea(sesion, NOMBRE_CLINICA, linea_base.CODIGO_PRESUPUESTO)

    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_CLINICA, linea_base.CODIGO_PRESUPUESTO)

    assert sorted(abierta.instantanea.creadas) == sorted(linea_base.CODIGOS_LINEA_BASE)
    assert abierta.instantanea.sin_composicion == ()
    registro = sesion.scalars(
        select(models.RegistroCambio).where(models.RegistroCambio.campo == "instantanea")
    ).one()
    assert registro.objeto == "apu" and registro.responsable == "sistema"
    assert _contar(sesion, models.Presupuesto) == 1  # no creo una version
    # reabrir no la vuelve a crear
    otra = hoja.abrir_version(sesion, catalogo, NOMBRE_CLINICA, linea_base.CODIGO_PRESUPUESTO)
    assert otra.instantanea.creadas == ()
    assert _contar(sesion, models.RegistroCambio) == 1


def test_editar_la_clinica_guarda_una_version_con_el_espacio_que_se_le_agrega(clinica):
    """Abrir sin espacio y agregar uno: la version nueva lo guarda; la anterior sigue sin el."""
    sesion, catalogo = clinica
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_CLINICA, linea_base.CODIGO_PRESUPUESTO)
    espacio = espacio_of001()
    editado = replace(
        abierta.borrador, espacio=replace(espacio, puntos=(), recorridos=(), circuitos=())
    )

    guardada = hoja.guardar_version(
        sesion, catalogo, abierta, editado, fuente=FUENTE, responsable=RESPONSABLE
    )

    assert guardada.codigo == "002"
    nueva = _modelo(sesion, NOMBRE_CLINICA, "002")
    assert len(cargar_espacio(sesion, nueva.id).ambientes) == len(espacio.ambientes)
    assert cargar_espacio(sesion, _modelo(sesion, NOMBRE_CLINICA, "001").id).ambientes == ()


def test_abrir_ti001_da_el_total_y_el_punto_de_equilibrio_del_caso(ti001):
    """RF-58 por la hoja: 50 503,27 USD y PE de 28 586,76 USD (56,60 %) en el Dia 6."""
    sesion, catalogo = ti001

    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_TI001, "TI-001")

    assert abs(abierta.guardada.presupuesto.total - D("50503.27")) <= D("0.01")
    assert abierta.espacio_de is None
    pe = hoja.elaborar_borrador(abierta.borrador, codigo="TI-001").equilibrio
    assert abs(pe.punto - D("28586.76")) <= D("0.01")
    assert abs(pe.porcentaje - D("56.60")) <= D("0.01")
    assert pe.periodo.startswith("Dia 6")
    assert hoja.texto_equilibrio(pe).startswith("Se alcanza en Dia 6")


def test_ti001_sin_instantanea_se_abre_con_su_plan_inferido(ti001):
    sesion, catalogo = ti001
    borrar_instantanea(sesion, NOMBRE_TI001, "TI-001")

    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_TI001, "TI-001")

    assert len(abierta.instantanea.creadas) == 10
    assert abs(abierta.guardada.presupuesto.total - D("50503.27")) <= D("0.01")


def test_el_fcas_de_ti001_recalcula_y_queda_en_el_registro(ti001):
    """RF-57: cambiar el FCAS recalcula todos los APU de la version y queda registrado."""
    sesion, catalogo = ti001
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_TI001, "TI-001")
    editado = replace(
        abierta.borrador,
        parametros=replace(abierta.borrador.parametros, fcas=D("7.00")),
    )

    guardada = hoja.guardar_version(
        sesion, catalogo, abierta, editado, fuente=FUENTE, responsable=RESPONSABLE
    )

    # SF-E9: `siguiente_codigo` reconoce prefijo y numero, asi que «TI-001» sigue en «TI-002»
    # (antes de SF-E9 solo contaba los codigos numericos y la nueva salia «001»)
    assert guardada.codigo == "TI-002"
    assert guardada.total > abierta.guardada.presupuesto.total
    [registro] = hoja.registros_de_version(sesion, NOMBRE_TI001, guardada.codigo)
    assert (registro.objeto, registro.clave, registro.campo) == ("parametro", "fcas", "valor")
    assert (registro.valor_anterior, registro.valor_nuevo) == ("6.00", "7.00")


# ---------------------------------------------------------------------------------------------
# Excel de la hoja: exportar y reabrir verificando totales
# ---------------------------------------------------------------------------------------------


def test_el_excel_de_la_hoja_se_reabre_y_sus_formulas_dan_el_total_del_sistema(of001, tmp_path):
    sesion, catalogo = of001
    _guardar_edicion_completa(sesion, catalogo)
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "002")
    resultado = hoja.elaborar_borrador(abierta.borrador, codigo="002")
    ruta = tmp_path / "hoja.xlsx"

    hoja.exportar_excel(
        ruta,
        resultado,
        abierta.borrador,
        trazabilidad=hoja.tabla_de_trazabilidad(sesion, NOMBRE_OF001, "002"),
        precios=hoja.precios_de_version(sesion, NOMBRE_OF001, "002"),
    )

    libro = load_workbook(ruta)
    assert libro.sheetnames[:9] == [
        "Espacio y metrajes",
        "APU",
        "Presupuesto",
        "Plan y curva",
        "Punto de equilibrio",
        "Precios",
        "Parametros",
        "Auditoria",
        "Trazabilidad",
    ]
    celdas = evaluar(ruta)
    total = celdas[("PRESUPUESTO", _celda(libro, "Presupuesto", "TOTAL", "G"))]
    exacto = resultado.elaboracion.presupuesto.total
    assert abs(D(str(total)) - exacto) <= D("0.005")
    # el espacio y la trazabilidad llegan como tablas
    espacio = libro["Espacio y metrajes"]
    assert espacio.max_row == 1 + len(resultado.items)
    traza = libro["Trazabilidad"]
    assert [c.value for c in traza[2]][2:5] == ["metraje", "esp_ambientes:BAN-01", "largo"]
    assert traza.max_row == 1 + 3
    precios = libro["Precios"]
    assert precios.max_row > 1 and precios["A1"].value == "Insumo"


def test_exportar_en_bytes_da_un_libro_valido(of001):
    sesion, catalogo = of001
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
    resultado = hoja.elaborar_borrador(abierta.borrador, codigo="001")

    contenido = hoja.excel_de_hoja_en_bytes(resultado, abierta.borrador)

    import io

    assert "Presupuesto" in load_workbook(io.BytesIO(contenido)).sheetnames


def test_un_texto_con_prefijo_de_formula_no_se_exporta_como_formula(of001, tmp_path):
    """RNF-12 en las tablas de la hoja: el nombre de un ambiente escrito como `=1+1`."""
    sesion, catalogo = of001
    abierta = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
    filas = hoja.filas_desde_espacio(abierta.borrador.espacio)
    filas["ambientes"][0]["nombre"] = '=HYPERLINK("http://x")'
    editado = replace(
        abierta.borrador, espacio=hoja.espacio_desde_filas(filas, base=abierta.borrador.espacio)
    )
    ruta = tmp_path / "m1.xlsx"

    hoja.exportar_excel(ruta, hoja.elaborar_borrador(editado), editado)

    libro = load_workbook(ruta)
    hoja_ambientes = libro["Esp ambientes"]
    celda = next(
        c
        for fila in hoja_ambientes.iter_rows(min_row=2)
        for c in fila
        if c.value and "HYPERLINK" in str(c.value)
    )
    assert celda.data_type == "s" and celda.quotePrefix


# ---------------------------------------------------------------------------------------------
# Version vigente y registros
# ---------------------------------------------------------------------------------------------


def test_la_version_vigente_de_un_proyecto_sin_hoja_es_la_unica(clinica):
    sesion, _ = clinica

    assert hoja.codigo_vigente(sesion, NOMBRE_CLINICA) == linea_base.CODIGO_PRESUPUESTO
    assert hoja.codigo_vigente(sesion, "proyecto que no existe") is None


def test_la_trazabilidad_de_la_version_lista_sus_celdas(of001):
    sesion, catalogo = of001
    _guardar_edicion_completa(sesion, catalogo)

    registros = hoja.registros_de_version(sesion, NOMBRE_OF001, "002")

    assert [(r.objeto, r.campo) for r in registros] == [
        ("metraje", "largo"),
        ("cantidad", "cantidad"),
        ("parametro", "valor"),
    ]
    assert hoja.registros_de_version(sesion, NOMBRE_OF001, "001") == []


# ---------------------------------------------------------------------------------------------
# Insumos candidatos para cambiar la linea de un APU
# ---------------------------------------------------------------------------------------------


def test_los_insumos_candidatos_salen_del_catalogo_con_el_precio_de_la_lista_de_la_version(of001):
    sesion, _ = of001

    candidatos = hoja.insumos_candidatos(sesion, NOMBRE_OF001, "001", "material", "tubo pvc")

    assert candidatos
    assert all("tubo pvc" in c.descripcion.lower() for c in candidatos)
    pvc34 = next(c for c in candidatos if "3/4" in c.descripcion)
    precio = next(
        p.precio
        for p in _modelo(sesion, NOMBRE_OF001, "001").lista_precios.precios
        if p.insumo_id == _insumo_pvc34(sesion).id
    )
    assert pvc34.precio == precio and pvc34.unidad == "m"
    assert hoja.insumos_candidatos(sesion, NOMBRE_OF001, "001", "equipo", "no existe este") == []
    assert len(hoja.insumos_candidatos(sesion, NOMBRE_OF001, "001", "material", "", limite=3)) == 3
