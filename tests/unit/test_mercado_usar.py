"""MP-5, Tarea 14 (lógica): usar un precio del mercado, anular observaciones, APU afectados,
precios objetivo y la fuente de pendientes «el mercado cobra menos que su costo».

Datos FICTICIOS de `tests/fixtures/mercado_ficticio.py` (carpeta en Bs, `hoy = 2026-10-25`, lista
«Lista demo en Bs» del 01/07/2026: Cemento gris 500,00, Arena lavada 1.250,50, Albañil 100,00;
`OBRA-04` = 2 sacos de cemento, `OBRA-05` = 1 albañil con rendimiento 10). Oráculos a mano:

- APU afectados: el cemento (MAT-001) solo está en OBRA-04; el albañil (MO-001) solo en OBRA-05; la
  arena (MAT-002) en ninguna.
- La lista de hoy derivada se llama «{raíz} al dd/mm/aaaa»: «Lista demo en Bs al 25/10/2026».
- Pendientes (los números del plan): OBRA-05 con fcas 9 y bono 0 cuesta (100 × (1 + 9) + 0) / 10 =
  100,00 de costo directo; con administración 0,25 el piso es 125 y con 0,10 es 110. El mercado
  [100, 120, 130, 150, 200] tiene primer cuartil 120 (posición (5 − 1)·0,25 = 1): 120 < 125
  aparece; 120 ≥ 110 no. Con administración 0,20 el piso es 120 = primer cuartil: no aparece
  (igual vale, decisión 3 de Eugenio).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aplicacion.cifras import MENSAJE_CIFRA, CifraInvalida
from aplicacion.mercado import (
    NoExiste,
    ObservacionAnulada,
    anular_observacion,
    apus_afectados,
    estadisticas,
    objetivos,
    observaciones_vigentes,
    pendientes_de_mercado,
    registrar_observacion,
    usar_precio_de_cobro,
    usar_precio_de_compra,
)
from aplicacion.mesa import Pendiente, Siguiente
from aplicacion.tablas_mercado import ObservacionDeMercado, PrecioObjetivo
from core import models
from tests.fixtures.mercado_ficticio import (
    AHORA,
    HOY,
    LISTA,
    RESPONSABLE,
    nueva_sesion,
    observacion_cruda,
    observar,
    version,
)

MERCADO_5 = ["100", "120", "130", "150", "200"]
LISTA_DE_HOY = "Lista demo en Bs al 25/10/2026"
OBSERVACION_AJENA = "La observación elegida no es un precio vigente de este insumo o partida."
ESTUDIO_DE_MERCADO = Siguiente("Estudio de mercado", "mercado")


@pytest.fixture
def s() -> Iterator[Session]:
    yield from nueva_sesion()


def _precio(s: Session, lista: str, codigo: str) -> Decimal:
    return s.scalars(
        select(models.PrecioInsumo.precio)
        .join(models.ListaPrecios)
        .join(models.Insumo)
        .where(models.ListaPrecios.nombre == lista, models.Insumo.codigo == codigo)
    ).one()


def _listas(s: Session) -> int:
    return s.scalar(select(func.count()).select_from(models.ListaPrecios))


# --- responsable y códigos (encargos del árbitro de T13) --------------------------------------


def test_un_responsable_de_mas_de_200_caracteres_se_rechaza_sin_recortar(s: Session) -> None:
    with pytest.raises(ValueError) as error:
        observar_con(s, responsable="r" * 201)
    assert str(error.value) == "quien lo hace (responsable) admite hasta 200 caracteres"
    assert s.scalars(select(ObservacionDeMercado)).all() == []
    ident = observar_con(s, responsable="r" * 200)
    fila = s.get(ObservacionDeMercado, ident)
    assert fila is not None and fila.responsable == "r" * 200


def observar_con(s: Session, *, responsable: str) -> int:
    return registrar_observacion(
        s,
        lado="compra",
        codigo="MAT-001",
        fuente_tipo="proveedor",
        fuente="Ferretería Demo",
        fecha=HOY,
        precio="480,00",
        nota="",
        responsable=responsable,
        ahora=AHORA,
    )


def test_un_codigo_que_no_existe_es_no_existe(s: Session) -> None:
    with pytest.raises(NoExiste) as error:
        observar(s, "MAT-999", ["10"])
    assert str(error.value) == "No hay ningún insumo «MAT-999» en esta carpeta de trabajo."
    with pytest.raises(NoExiste) as error:
        observar(s, "OBRA-99", ["10"], lado="cobro")
    assert str(error.value) == (
        "No hay ninguna partida «OBRA-99» en el catálogo de esta carpeta de trabajo."
    )


# --- observaciones vigentes ---------------------------------------------------------------------


def test_las_observaciones_vigentes_son_las_de_la_ventana_sin_anuladas(s: Session) -> None:
    dentro = observar(s, "MAT-001", ["480"])
    observar(s, "MAT-001", ["470"], fecha=HOY.replace(month=7, day=26))  # 91 días: fuera
    usd = observacion_cruda(s, "MAT-001", Decimal("3"), moneda="USD")
    observacion_cruda(s, "MAT-001", Decimal("5"), moneda="Bs", anulada_por=dentro[0])
    filas = observaciones_vigentes(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert [f.id for f in filas] == [dentro[0], usd]  # la de otra moneda se ve; no cuenta


# --- anular -------------------------------------------------------------------------------------


def test_anular_deja_un_contraasiento_y_la_observacion_deja_de_contar(s: Session) -> None:
    ids = observar(s, "MAT-001", ["480", "520"])
    contra = anular_observacion(s, ids[0], responsable="Rita <rita>", ahora=AHORA)
    original = s.get(ObservacionDeMercado, ids[0])
    asiento = s.get(ObservacionDeMercado, contra)
    assert original is not None and asiento is not None
    assert original.anulada_por == contra
    assert (asiento.anulada_por, asiento.nota, asiento.responsable, asiento.fecha_hora) == (
        contra,
        f"Anula la observación n.º {ids[0]}.",
        "Rita <rita>",
        AHORA,
    )
    assert (asiento.lado, asiento.codigo, asiento.precio, asiento.moneda) == (
        "compra",
        "MAT-001",
        Decimal("480"),
        "Bs",
    )
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert (est.n, est.minimo, est.ids) == (1, Decimal("520"), (ids[1],))


def test_no_se_anula_dos_veces_ni_lo_que_no_existe(s: Session) -> None:
    ids = observar(s, "MAT-001", ["480"])
    contra = anular_observacion(s, ids[0], responsable=RESPONSABLE, ahora=AHORA)
    for ident in (ids[0], contra):
        with pytest.raises(ObservacionAnulada) as error:
            anular_observacion(s, ident, responsable=RESPONSABLE, ahora=AHORA)
        assert str(error.value) == f"La observación n.º {ident} ya está anulada."
    with pytest.raises(NoExiste) as error:
        anular_observacion(s, 999, responsable=RESPONSABLE, ahora=AHORA)
    assert str(error.value) == "No hay ninguna observación n.º 999 en esta carpeta de trabajo."


# --- APU afectados ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("insumo", "partidas"),
    [("MAT-001", ["OBRA-04"]), ("MO-001", ["OBRA-05"]), ("MAT-002", [])],
)
def test_los_apu_afectados_son_las_partidas_que_usan_el_insumo(
    s: Session, insumo: str, partidas: list[str]
) -> None:
    assert apus_afectados(s, insumo) == partidas


def test_los_apu_afectados_de_un_insumo_que_no_existe(s: Session) -> None:
    with pytest.raises(NoExiste, match="^No hay ningún insumo «MAT-999» en esta carpeta"):
        apus_afectados(s, "MAT-999")


# --- usar un precio de compra -------------------------------------------------------------------


def test_usar_un_precio_de_compra_lo_pone_en_la_lista_de_hoy_con_su_fuente(s: Session) -> None:
    ids = observar(s, "MAT-001", ["480,00"])
    lista = usar_precio_de_compra(
        s, "MAT-001", "480,00", observacion_id=ids[0], fecha=HOY, responsable=RESPONSABLE
    )
    assert (lista.nombre, lista.moneda, lista.fecha_vigencia) == (LISTA_DE_HOY, "Bs", HOY)
    assert _precio(s, LISTA_DE_HOY, "MAT-001") == Decimal("480.00")
    assert _precio(s, LISTA_DE_HOY, "MAT-002") == Decimal("1250.50")  # lo demás se copia
    assert _precio(s, LISTA, "MAT-001") == Decimal("500.00")  # la del 01/07 no cambia
    fila = s.scalars(
        select(models.PrecioInsumo)
        .join(models.Insumo)
        .where(models.PrecioInsumo.lista_id == lista.id, models.Insumo.codigo == "MAT-001")
    ).one()
    origen = s.get(models.PrecioOrigen, fila.id)
    assert origen is not None
    assert (origen.fuente, origen.moneda_original, origen.precio_original, origen.fecha_precio) == (
        f"Estudio de mercado: observación n.º {ids[0]}, por ana",
        "Bs",
        Decimal("480.00"),
        HOY,
    )
    assert (origen.tasa, origen.fecha_tasa) == (None, None)


def test_sin_observacion_la_fuente_solo_dice_estudio_de_mercado(s: Session) -> None:
    lista = usar_precio_de_compra(
        s, "MAT-002", "1.300", observacion_id=None, fecha=HOY, responsable=RESPONSABLE
    )
    fila = s.scalars(
        select(models.PrecioInsumo)
        .join(models.Insumo)
        .where(models.PrecioInsumo.lista_id == lista.id, models.Insumo.codigo == "MAT-002")
    ).one()
    origen = s.get(models.PrecioOrigen, fila.id)
    assert fila.precio == Decimal("1300")
    assert origen is not None and origen.fuente == "Estudio de mercado, por ana"


def test_dos_precios_el_mismo_dia_sin_version_reescriben_la_misma_lista(s: Session) -> None:
    primera = usar_precio_de_compra(
        s, "MAT-001", "480", observacion_id=None, fecha=HOY, responsable=RESPONSABLE
    )
    antes = _listas(s)
    segunda = usar_precio_de_compra(
        s, "MAT-001", "470", observacion_id=None, fecha=HOY, responsable=RESPONSABLE
    )
    assert segunda.id == primera.id and _listas(s) == antes
    assert _precio(s, LISTA_DE_HOY, "MAT-001") == Decimal("470")


@pytest.mark.parametrize("cual", ["anulada", "de_otro_insumo", "de_cobro", "no_existe"])
def test_la_observacion_citada_debe_ser_un_precio_vigente_del_insumo(s: Session, cual: str) -> None:
    propia = observar(s, "MAT-001", ["480"])[0]
    citada = {
        "anulada": observacion_cruda(s, "MAT-001", Decimal("480"), moneda="Bs", anulada_por=propia),
        "de_otro_insumo": observar(s, "MAT-002", ["1300"])[0],
        "de_cobro": observar(s, "OBRA-04", ["2000"], lado="cobro")[0],
        "no_existe": 999,
    }[cual]
    antes = _listas(s)
    with pytest.raises(ValueError) as error:
        usar_precio_de_compra(
            s, "MAT-001", "480", observacion_id=citada, fecha=HOY, responsable=RESPONSABLE
        )
    assert str(error.value) == OBSERVACION_AJENA
    assert _listas(s) == antes


def test_el_precio_de_compra_se_lee_con_la_regla_y_es_mayor_que_cero(s: Session) -> None:
    antes = _listas(s)
    with pytest.raises(CifraInvalida) as error:
        usar_precio_de_compra(
            s, "MAT-001", "2.5", observacion_id=None, fecha=HOY, responsable=RESPONSABLE
        )
    assert str(error.value) == MENSAJE_CIFRA
    with pytest.raises(ValueError, match="^El precio debe ser mayor que cero.$"):
        usar_precio_de_compra(
            s, "MAT-001", "0,00", observacion_id=None, fecha=HOY, responsable=RESPONSABLE
        )
    with pytest.raises(NoExiste):
        usar_precio_de_compra(
            s, "MAT-999", "10", observacion_id=None, fecha=HOY, responsable=RESPONSABLE
        )
    assert _listas(s) == antes


# --- usar un precio de cobro y los objetivos ----------------------------------------------------


def test_usar_un_precio_de_cobro_guarda_el_objetivo_y_vale_el_ultimo(s: Session) -> None:
    ids = observar(s, "OBRA-04", ["1900", "2000", "2100"], lado="cobro")
    usar_precio_de_cobro(
        s,
        "OBRA-04",
        "1.980,00",
        observaciones=[ids[2], ids[0], ids[0]],
        responsable=RESPONSABLE,
        ahora=AHORA,
    )
    fila = s.scalars(select(PrecioObjetivo)).one()
    assert (fila.codigo_partida, fila.precio, fila.moneda, fila.responsable, fila.fecha_hora) == (
        "OBRA-04",
        Decimal("1980.00"),
        "Bs",
        RESPONSABLE,
        AHORA,
    )
    assert json.loads(fila.observaciones) == [ids[0], ids[2]]  # sin repetir, en orden
    usar_precio_de_cobro(
        s, "OBRA-04", "2.050", observaciones=[], responsable=RESPONSABLE, ahora=AHORA
    )
    hallados = objetivos(s, ["OBRA-05", "OBRA-04", "OBRA-99"])
    assert [(o.codigo_partida, o.precio) for o in hallados] == [("OBRA-04", Decimal("2050"))]


def test_el_objetivo_cita_solo_precios_de_cobro_vigentes_de_su_partida(s: Session) -> None:
    compra = observar(s, "MAT-001", ["480"])[0]
    with pytest.raises(ValueError) as error:
        usar_precio_de_cobro(
            s, "OBRA-04", "1980", observaciones=[compra], responsable=RESPONSABLE, ahora=AHORA
        )
    assert str(error.value) == OBSERVACION_AJENA
    with pytest.raises(NoExiste):
        usar_precio_de_cobro(
            s, "OBRA-99", "1980", observaciones=[], responsable=RESPONSABLE, ahora=AHORA
        )
    with pytest.raises(ValueError, match="^El precio debe ser mayor que cero.$"):
        usar_precio_de_cobro(
            s, "OBRA-04", "-1", observaciones=[], responsable=RESPONSABLE, ahora=AHORA
        )
    assert s.scalars(select(PrecioObjetivo)).all() == []


# --- pendientes de la mesa -----------------------------------------------------------------------


def _obra_con_friso(s: Session, administracion: str) -> models.Presupuesto:
    """VIV-001 de OBRA-01 con OBRA-05 presupuestada (fcas 9 y bono 0: costo directo 100)."""
    presupuesto = version(
        s, "OBRA-01", "VIV-001", fcas="9.00", bono="0.00", administracion=administracion
    )
    item = models.ItemComputo(
        codigo_partida="OBRA-05",
        descripcion="Friso ficticio de pared",
        unidad_original="m2",
        unidad="m2",
        cantidad=Decimal("10"),
        origen_id="prueba",
        origen_tipo="manual",
        dominio="civil",
        presupuesto_id=presupuesto.id,
    )
    s.add(item)
    s.flush()
    partida = s.scalars(select(models.Partida).where(models.Partida.codigo == "OBRA-05")).one()
    cero = Decimal("0")
    s.add(
        models.PartidaPresupuestada(
            presupuesto_id=presupuesto.id,
            partida_id=partida.id,
            item_computo_id=item.id,
            orden=1,
            cantidad=Decimal("10"),
            materiales=cero,
            equipos=cero,
            mano_obra=Decimal("100"),
            costo_directo=Decimal("100"),
            con_administracion=Decimal("100"),
            precio_unitario=Decimal("100"),
            total=Decimal("1000"),
        )
    )
    s.flush()
    return presupuesto


def test_el_mercado_que_cobra_menos_que_el_costo_es_un_pendiente(s: Session) -> None:
    presupuesto = _obra_con_friso(s, administracion="0.25")  # piso 125
    observar(s, "OBRA-05", MERCADO_5, lado="cobro", fuente_tipo="competidor")
    assert pendientes_de_mercado(s, HOY) == [
        Pendiente(
            str(presupuesto.proyecto_id),
            "OBRA-01",
            "OBRA-05: el mercado cobra menos que su costo",
            ESTUDIO_DE_MERCADO,
        )
    ]


@pytest.mark.parametrize("administracion", ["0.10", "0.20"])  # piso 110 y piso 120 (= q1)
def test_si_el_mercado_no_baja_del_costo_no_hay_pendiente(s: Session, administracion: str) -> None:
    _obra_con_friso(s, administracion=administracion)
    observar(s, "OBRA-05", MERCADO_5, lado="cobro", fuente_tipo="competidor")
    assert pendientes_de_mercado(s, HOY) == []


def test_sin_observaciones_de_cobro_no_hay_pendiente(s: Session) -> None:
    _obra_con_friso(s, administracion="0.25")
    observar(s, "OBRA-05", MERCADO_5, lado="cobro", fecha=HOY.replace(month=7, day=1))
    assert pendientes_de_mercado(s, HOY) == []


def test_sin_lista_para_armar_la_fuente_no_dice_nada() -> None:
    for sesion in nueva_sesion(con_lista=False):
        assert pendientes_de_mercado(sesion, HOY) == []
