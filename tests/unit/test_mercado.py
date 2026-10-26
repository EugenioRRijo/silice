"""MP-5, Tarea 13: observaciones de mercado, estadísticas, piso y propuesta (diseño de montar un
presupuesto §5.1 y §10; decisiones ratificadas por Eugenio el 2026-10-25).

Datos FICTICIOS de `tests/fixtures/mercado_ficticio.py` (carpeta en Bs, `hoy = 2026-10-25`).
Oráculos a mano, nunca del código bajo prueba:

- Cuartiles como `CUARTIL.INC` de Excel (tipo 7): sobre los precios ordenados x0..x(n-1), la
  posición es h = (n − 1)·p; el cuartil es x[⌊h⌋] + (h − ⌊h⌋)·(x[⌊h⌋+1] − x[⌊h⌋]).
  [100, 120, 130, 150, 200]: q1 → h = 1 → 120; mediana → h = 2 → 130; promedio 700/5 = 140.
  [10, 20]: q1 → h = 0,25 → 10 + 0,25·10 = 12,5; mediana → h = 0,5 → 15.
  [100, 120, 130, 150]: q1 → h = 0,75 → 100 + 0,75·20 = 115; mediana → h = 1,5 → 125.
- Ventana de 90 días: 25/10/2026 − 90 días = 27/07/2026 (entra) y el 26/07/2026 no.
- Piso = costo directo × (1 + administración); precio con utilidad = piso × (1 + utilidad).
  OBRA-04: 2 × 500,00 = 1.000,00 → por omisión (adm. 0,15, util. 0,10) 1.150 y 1.265.
  OBRA-05: (100 × (1 + fcas) + bono × 1) / 10.
- Margen = (objetivo − precio unitario) / precio unitario × 100, a una cifra decimal:
  (1.980 − 2.074,44) / 2.074,44 × 100 = −4,5525… → −4,6.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.cifras import MENSAJE_CIFRA, MENSAJE_CIFRA_VACIA, CifraInvalida
from aplicacion.listas_para_armar import MENSAJE_SIN_LISTA, SinListaParaArmar
from aplicacion.mercado import (
    CarpetaSinMoneda,
    Estadisticas,
    Propuesta,
    centimos,
    estadisticas,
    margen,
    piso_de_cobro,
    propuesta,
    registrar_observacion,
)
from aplicacion.tablas_mercado import (
    METADATA_MERCADO,
    ObservacionDeMercado,
    PrecioObjetivo,
)
from core import models
from core.catalog import Catalogo
from tests.fixtures.mercado_ficticio import (
    AHORA,
    HOY,
    RESPONSABLE,
    nueva_sesion,
    observacion_cruda,
    observar,
    version,
)

MERCADO_5 = ["100", "120", "130", "150", "200"]
SIN_OBSERVACIONES_90 = "Sin observaciones en los últimos 90 días."
POR_ENCIMA = "Primer cuartil del mercado, igual o por encima de su costo."
POR_DEBAJO = "La competencia cobra menos que su costo: se propone su costo."


@pytest.fixture
def s() -> Iterator[Session]:
    yield from nueva_sesion()


def _registrar(s: Session, **cambios: object) -> int:
    datos: dict[str, object] = {
        "lado": "compra",
        "codigo": "MAT-001",
        "fuente_tipo": "proveedor",
        "fuente": "Ferretería Demo",
        "fecha": HOY,
        "precio": "520,00",
        "nota": "",
        "responsable": RESPONSABLE,
        "ahora": AHORA,
    }
    datos.update(cambios)
    return registrar_observacion(s, **datos)  # type: ignore[arg-type]


# --- las tablas ---------------------------------------------------------------------------------


def test_las_tablas_del_estudio_de_mercado_son_las_del_plan() -> None:
    assert set(METADATA_MERCADO.tables) == {"mp_observacion", "mp_precio_objetivo"}
    assert [c.name for c in ObservacionDeMercado.__table__.columns] == [
        "id",
        "lado",
        "codigo",
        "fuente_tipo",
        "fuente",
        "fecha",
        "moneda",
        "precio",
        "nota",
        "responsable",
        "fecha_hora",
        "anulada_por",
    ]
    assert [c.name for c in PrecioObjetivo.__table__.columns] == [
        "id",
        "codigo_partida",
        "precio",
        "moneda",
        "observaciones",
        "responsable",
        "fecha_hora",
    ]


# --- registrar una observación ----------------------------------------------------------------


def test_registrar_lee_la_cifra_con_coma_y_guarda_la_moneda_de_la_carpeta(s: Session) -> None:
    ident = _registrar(s, precio="1.234,56", nota="Precio de contado")
    fila = s.get(ObservacionDeMercado, ident)
    assert fila is not None
    assert (fila.lado, fila.codigo, fila.fuente_tipo, fila.fuente) == (
        "compra",
        "MAT-001",
        "proveedor",
        "Ferretería Demo",
    )
    assert fila.precio == Decimal("1234.56")
    assert isinstance(fila.precio, Decimal)
    assert (fila.moneda, fila.fecha, fila.nota) == ("Bs", HOY, "Precio de contado")
    assert (fila.responsable, fila.fecha_hora, fila.anulada_por) == (RESPONSABLE, AHORA, None)


def test_registrar_un_precio_de_cobro_de_una_partida_del_catalogo(s: Session) -> None:
    ident = _registrar(s, lado="cobro", codigo="OBRA-04", fuente_tipo="competidor")
    fila = s.get(ObservacionDeMercado, ident)
    assert fila is not None and (fila.lado, fila.codigo) == ("cobro", "OBRA-04")


@pytest.mark.parametrize(
    "fuente_tipo", ["proveedor", "competidor", "cotizacion", "maprex", "compra"]
)
def test_registrar_acepta_los_cinco_tipos_de_fuente(s: Session, fuente_tipo: str) -> None:
    assert _registrar(s, fuente_tipo=fuente_tipo) > 0


@pytest.mark.parametrize(
    ("precio", "mensaje"),
    [("2.5", MENSAJE_CIFRA), ("1,234.5", MENSAJE_CIFRA), ("", MENSAJE_CIFRA_VACIA)],
)
def test_un_precio_mal_escrito_es_cifra_invalida(s: Session, precio: str, mensaje: str) -> None:
    with pytest.raises(CifraInvalida) as error:
        _registrar(s, precio=precio)
    assert str(error.value) == mensaje
    assert s.scalars(select(ObservacionDeMercado)).all() == []


@pytest.mark.parametrize("precio", ["0", "0,00", "-5"])
def test_un_precio_que_no_es_mayor_que_cero_no_se_registra(s: Session, precio: str) -> None:
    with pytest.raises(ValueError, match="^El precio debe ser mayor que cero.$"):
        _registrar(s, precio=precio)


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"lado": "venta"}, "lado 'venta'; se espera compra o cobro"),
        (
            {"fuente_tipo": "amigo"},
            "fuente_tipo 'amigo'; se espera proveedor, competidor, cotizacion, maprex o compra",
        ),
        ({"codigo": "MAT-999"}, "No hay ningún insumo «MAT-999» en esta carpeta de trabajo."),
        ({"codigo": "OBRA-04"}, "No hay ningún insumo «OBRA-04» en esta carpeta de trabajo."),
        (
            {"lado": "cobro", "codigo": "OBRA-99"},
            "No hay ninguna partida «OBRA-99» en el catálogo de esta carpeta de trabajo.",
        ),
        (
            {"lado": "cobro", "codigo": "MAT-001"},
            "No hay ninguna partida «MAT-001» en el catálogo de esta carpeta de trabajo.",
        ),
        ({"fuente": "   "}, "Escriba de dónde sale el precio (la fuente)."),
        ({"fuente": "F" * 201}, "La fuente admite hasta 200 caracteres."),
        ({"nota": "n" * 501}, "La nota admite hasta 500 caracteres."),
        ({"fecha": date(2026, 10, 26)}, "La fecha de la observación no puede ser posterior a hoy."),
        ({"responsable": "  "}, "hace falta quién lo hace (responsable)"),
    ],
)
def test_registrar_rechaza_lo_que_no_cumple_las_reglas(
    s: Session, cambios: dict[str, object], mensaje: str
) -> None:
    with pytest.raises(ValueError) as error:
        _registrar(s, **cambios)
    assert str(error.value) == mensaje
    assert s.scalars(select(ObservacionDeMercado)).all() == []


def test_registrar_admite_los_largos_justos(s: Session) -> None:
    ident = _registrar(s, fuente="F" * 200, nota="n" * 500)
    fila = s.get(ObservacionDeMercado, ident)
    assert fila is not None and (len(fila.fuente), len(fila.nota)) == (200, 500)


def test_sin_moneda_en_la_carpeta_no_se_registra_ni_se_calcula() -> None:
    for sesion in nueva_sesion(moneda=None, con_lista=False):
        with pytest.raises(CarpetaSinMoneda) as error:
            _registrar(sesion)
        assert str(error.value) == (
            "Esta carpeta de trabajo aún no tiene moneda: declárela o cree su lista para armar "
            "antes de estudiar el mercado."
        )
        with pytest.raises(CarpetaSinMoneda):
            estadisticas(sesion, lado="compra", codigo="MAT-001", hoy=HOY)


# --- estadísticas -----------------------------------------------------------------------------


def test_cinco_observaciones_dan_las_seis_cifras(s: Session) -> None:
    ids = observar(s, "MAT-001", MERCADO_5)
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert est == Estadisticas(
        moneda="Bs",
        n=5,
        minimo=Decimal("100"),
        q1=Decimal("120"),
        mediana=Decimal("130"),
        promedio=Decimal("140"),
        maximo=Decimal("200"),
        ids=tuple(ids),
        otras_monedas=0,
        dias=90,
    )


def test_los_cuartiles_interpolan_como_cuartil_inc(s: Session) -> None:
    observar(s, "MAT-001", ["10", "20"])
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert (est.q1, est.mediana, est.promedio) == (Decimal("12.5"), Decimal("15"), Decimal("15"))
    assert centimos(est.q1) == Decimal("12.50")


def test_los_cuartiles_ordenan_antes_de_interpolar(s: Session) -> None:
    observar(s, "MAT-001", ["150", "100", "130", "120"])
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert (est.minimo, est.q1, est.mediana, est.maximo) == (
        Decimal("100"),
        Decimal("115"),
        Decimal("125"),
        Decimal("150"),
    )


def test_una_sola_observacion_es_todas_las_cifras(s: Session) -> None:
    observar(s, "MAT-001", ["50"])
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert est.n == 1
    assert {est.minimo, est.q1, est.mediana, est.promedio, est.maximo} == {Decimal("50")}


def test_sin_observaciones_todo_es_none(s: Session) -> None:
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert est == Estadisticas("Bs", 0, None, None, None, None, None, (), 0, 90)


def test_el_promedio_es_exacto_y_se_muestra_en_centimos(s: Session) -> None:
    observar(s, "MAT-001", ["10", "20", "20"])
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert est.promedio == Decimal(50) / Decimal(3)
    assert centimos(est.promedio) == Decimal("16.67")


def test_centimos_redondea_la_mitad_hacia_arriba() -> None:
    assert centimos(Decimal("16.665")) == Decimal("16.67")
    assert centimos(Decimal("16.664")) == Decimal("16.66")
    assert str(centimos(Decimal("140"))) == "140.00"
    assert centimos(None) is None


def test_la_ventana_de_90_dias_incluye_el_dia_27_de_julio_y_no_el_26(s: Session) -> None:
    dentro = observar(s, "MAT-001", ["100"], fecha=date(2026, 7, 27))
    observar(s, "MAT-001", ["999"], fecha=date(2026, 7, 26))
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert (est.n, est.ids, est.maximo) == (1, tuple(dentro), Decimal("100"))


def test_la_ventana_se_puede_cambiar(s: Session) -> None:
    dentro = observar(s, "MAT-001", ["100"], fecha=date(2026, 9, 25))
    observar(s, "MAT-001", ["999"], fecha=date(2026, 9, 24))
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY, dias=30)
    assert (est.n, est.ids, est.dias) == (1, tuple(dentro), 30)


def test_una_observacion_posterior_a_hoy_no_entra(s: Session) -> None:
    observar(s, "MAT-001", ["100"], fecha=HOY)
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=date(2026, 10, 24))
    assert est.n == 0


def test_una_ventana_negativa_es_un_error(s: Session) -> None:
    with pytest.raises(ValueError, match="^dias -1; se espera 0 o más$"):
        estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY, dias=-1)


def test_otra_moneda_no_se_mezcla_y_se_cuenta_aparte(s: Session) -> None:
    ids = observar(s, "MAT-001", ["100", "200"])
    observacion_cruda(s, "MAT-001", Decimal("3"), moneda="USD")
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert (est.n, est.maximo, est.ids, est.otras_monedas) == (2, Decimal("200"), tuple(ids), 1)


def test_una_observacion_anulada_no_cuenta(s: Session) -> None:
    ids = observar(s, "MAT-001", ["100"])
    observacion_cruda(s, "MAT-001", Decimal("5"), moneda="Bs", anulada_por=ids[0])
    observacion_cruda(s, "MAT-001", Decimal("7"), moneda="USD", anulada_por=ids[0])
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert (est.n, est.minimo, est.otras_monedas) == (1, Decimal("100"), 0)


def test_compra_y_cobro_y_cada_codigo_van_por_separado(s: Session) -> None:
    observar(s, "MAT-001", ["100"])
    observar(s, "MAT-002", ["900"])
    observar(s, "OBRA-04", ["5000"], lado="cobro", fuente_tipo="competidor")
    compra = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    cobro = estadisticas(s, lado="cobro", codigo="OBRA-04", hoy=HOY)
    assert (compra.n, compra.maximo) == (1, Decimal("100"))
    assert (cobro.n, cobro.maximo) == (1, Decimal("5000"))


def test_estadisticas_rechaza_un_lado_desconocido(s: Session) -> None:
    with pytest.raises(ValueError, match="^lado 'venta'; se espera compra o cobro$"):
        estadisticas(s, lado="venta", codigo="MAT-001", hoy=HOY)


# --- propuesta --------------------------------------------------------------------------------


def _cobro(s: Session, precios: list[str]) -> Estadisticas:
    observar(s, "OBRA-04", precios, lado="cobro", fuente_tipo="competidor")
    return estadisticas(s, lado="cobro", codigo="OBRA-04", hoy=HOY)


def test_la_propuesta_de_compra_es_la_mediana_y_nombra_la_mas_barata(s: Session) -> None:
    observar(s, "MAT-001", MERCADO_5)
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert propuesta("compra", est, None) == Propuesta(
        precio=Decimal("130.00"),
        razon="Mediana de 5 observaciones; la más barata vista: 100,00 Bs.",
        piso=None,
    )


def test_la_propuesta_de_compra_escribe_la_cifra_con_punto_de_miles(s: Session) -> None:
    observar(s, "MAT-002", ["1.250,50", "1.300"])
    est = estadisticas(s, lado="compra", codigo="MAT-002", hoy=HOY)
    elegida = propuesta("compra", est, None)
    assert elegida.precio == Decimal("1275.25")
    assert elegida.razon == "Mediana de 2 observaciones; la más barata vista: 1.250,50 Bs."


def test_con_una_observacion_la_razon_va_en_singular(s: Session) -> None:
    observar(s, "MAT-001", ["50"])
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert propuesta("compra", est, None).razon == (
        "Mediana de 1 observación; la más barata vista: 50,00 Bs."
    )


def test_la_compra_no_tiene_piso(s: Session) -> None:
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    with pytest.raises(ValueError, match="^lo que se compra no tiene piso$"):
        propuesta("compra", est, Decimal("1"))


def test_sin_observaciones_no_hay_propuesta(s: Session) -> None:
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert propuesta("compra", est, None) == Propuesta(None, SIN_OBSERVACIONES_90, None)
    cobro = estadisticas(s, lado="cobro", codigo="OBRA-04", hoy=HOY, dias=30)
    assert propuesta("cobro", cobro, Decimal("125")) == Propuesta(
        None, "Sin observaciones en los últimos 30 días.", Decimal("125")
    )


@pytest.mark.parametrize(
    ("piso", "precio", "razon"),
    [
        (Decimal("125"), Decimal("125.00"), POR_DEBAJO),
        (Decimal("110"), Decimal("120.00"), POR_ENCIMA),
        (Decimal("120"), Decimal("120.00"), POR_ENCIMA),  # igual al piso: vale (ratificado)
        (Decimal("250"), Decimal("250.00"), POR_DEBAJO),  # piso mayor que todo el mercado
        (Decimal("125.001"), Decimal("125.01"), POR_DEBAJO),  # nunca por debajo de su costo
    ],
)
def test_la_propuesta_de_cobro_es_el_primer_cuartil_sin_bajar_del_piso(
    s: Session, piso: Decimal, precio: Decimal, razon: str
) -> None:
    est = _cobro(s, MERCADO_5)
    assert propuesta("cobro", est, piso) == Propuesta(precio=precio, razon=razon, piso=piso)


def test_el_redondeo_del_primer_cuartil_no_lo_deja_bajo_el_piso(s: Session) -> None:
    est = _cobro(s, ["120,004"])
    elegida = propuesta("cobro", est, Decimal("120.003"))
    assert (elegida.precio, elegida.razon) == (Decimal("120.01"), POR_ENCIMA)


def test_el_cobro_exige_su_piso(s: Session) -> None:
    est = _cobro(s, MERCADO_5)
    with pytest.raises(ValueError, match="^lo que se cobra necesita su piso$"):
        propuesta("cobro", est, None)


def test_propuesta_rechaza_un_lado_desconocido(s: Session) -> None:
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    with pytest.raises(ValueError, match="^lado 'venta'; se espera compra o cobro$"):
        propuesta("venta", est, None)


# --- piso de cobro ----------------------------------------------------------------------------


def _piso(s: Session, codigo: str = "OBRA-04", proyecto: str | None = None):
    return piso_de_cobro(s, Catalogo(s), codigo, proyecto=proyecto, fecha=HOY)


def test_el_piso_por_omision_es_costo_directo_mas_administracion(s: Session) -> None:
    assert _piso(s) == (Decimal("1150.00"), Decimal("1265.00"))


def test_el_piso_usa_los_parametros_de_la_version_vigente_de_la_obra(s: Session) -> None:
    version(s, "OBRA-01", "VIV-001", administracion="0.30", utilidad="0.10")
    version(s, "OBRA-01", "VIV-002", administracion="0.20", utilidad="0.05")
    assert _piso(s, proyecto="OBRA-01") == (Decimal("1200"), Decimal("1260"))


def test_una_version_descartada_no_da_los_parametros(s: Session) -> None:
    version(s, "OBRA-01", "VIV-001", administracion="0.30", utilidad="0.10")
    descartada = version(s, "OBRA-01", "VIV-002", administracion="0.20", utilidad="0.05")
    s.add(models.DescarteVersion(presupuesto_id=descartada.id, fecha=HOY))
    s.flush()
    assert _piso(s, proyecto="OBRA-01") == (Decimal("1300"), Decimal("1430"))


def test_una_obra_sin_versiones_usa_los_parametros_por_omision(s: Session) -> None:
    s.add(models.Proyecto(nombre="OBRA-02", descripcion="Obra ficticia sin versiones"))
    s.flush()
    assert _piso(s, proyecto="OBRA-02") == (Decimal("1150"), Decimal("1265"))


def test_el_piso_con_mano_de_obra_aplica_fcas_y_bono(s: Session) -> None:
    # por omisión: (100 × 7 + 1 × 1) / 10 = 70,1 → × 1,15 = 80,615 → × 1,10 = 88,6765
    assert _piso(s, "OBRA-05") == (Decimal("80.615"), Decimal("88.6765"))
    # versión en Bs: fcas 1, bono 2 → (100 × 2 + 2) / 10 = 20,2 → × 1,10 = 22,22 → × 1,10
    version(s, "OBRA-01", "VIV-001", fcas="1.00", bono="2.00", administracion="0.10")
    assert _piso(s, "OBRA-05", proyecto="OBRA-01") == (Decimal("22.22"), Decimal("24.442"))


def test_el_bono_de_una_obra_en_otra_moneda_no_se_mezcla(s: Session) -> None:
    # la versión en USD declara un bono de 2 USD: no vale en la carpeta en Bs, se usa el de
    # omisión (1): (100 × 2 + 1) / 10 = 20,1 → × 1,10 = 22,11 → × 1,10 = 24,321
    version(s, "OBRA-03", "VIV-001", moneda="USD", fcas="1.00", bono="2.00", administracion="0.10")
    assert _piso(s, "OBRA-05", proyecto="OBRA-03") == (Decimal("22.11"), Decimal("24.321"))


def test_el_piso_de_una_obra_que_no_existe_es_un_error(s: Session) -> None:
    with pytest.raises(ValueError) as error:
        _piso(s, proyecto="OBRA-99")
    assert str(error.value) == "No hay ninguna obra «OBRA-99» en esta carpeta de trabajo."


def test_el_piso_de_una_partida_que_no_existe_es_un_error(s: Session) -> None:
    with pytest.raises(ValueError) as error:
        _piso(s, "OBRA-99")
    assert str(error.value) == (
        "No hay ninguna partida «OBRA-99» en el catálogo de esta carpeta de trabajo."
    )


def test_sin_lista_para_armar_no_hay_piso() -> None:
    for sesion in nueva_sesion(con_lista=False):
        with pytest.raises(SinListaParaArmar) as error:
            _piso(sesion)
        assert str(error.value) == MENSAJE_SIN_LISTA


# --- margen -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("objetivo", "precio_unitario", "esperado"),
    [
        ("1980.00", "2074.44", "-4.6"),
        ("1100", "1000", "10.0"),
        ("1000.5", "1000", "0.1"),  # 0,05 → mitad hacia arriba
        ("1000", "1000", "0.0"),
    ],
)
def test_el_margen_contra_el_precio_unitario(
    objetivo: str, precio_unitario: str, esperado: str
) -> None:
    resultado = margen(Decimal(objetivo), Decimal(precio_unitario))
    assert resultado == Decimal(esperado)
    assert str(resultado) == esperado


def test_el_margen_sin_precio_unitario_es_un_error() -> None:
    with pytest.raises(ValueError, match="^el precio unitario debe ser mayor que cero$"):
        margen(Decimal("10"), Decimal("0"))
