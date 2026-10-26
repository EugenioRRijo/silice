"""MP-1, Tarea 1: la moneda de la carpeta de trabajo y la lista para armar (D-MP1: una moneda por
carpeta; diseño de montar un presupuesto §5.1 y §10).

Base en memoria con `crear_esquema` + `crear_esquema_carpeta`; datos ficticios (insumos «Cemento
gris», «Arena lavada», «Albañil»; tasa del BCV de 40,00 Bs/USD inventada). Los oráculos están
escritos a mano: los nombres de las listas, los mensajes y las cuentas (400 Bs ÷ 40 = 10 USD,
1.250,50 Bs ÷ 40 = 31,2625 USD, 3.200 Bs ÷ 40 = 80 USD) no salen del código bajo prueba.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aplicacion import listas_para_armar as armar
from aplicacion.listas_para_armar import (
    CarpetaConOtraMoneda,
    ListaParaArmar,
    SinListaParaArmar,
)
from aplicacion.tablas_carpeta import METADATA_CARPETA, CarpetaDeTrabajo, crear_esquema_carpeta
from core import models
from core.budget.moneda import declarar_moneda
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.catalog.empresa import lista_de_referencia
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion

HOY = date(2026, 10, 25)
JULIO = date(2026, 7, 1)
AHORA = datetime(2026, 10, 25, 9, 30)
MAPREX = "MaPreX julio 2026 en Bs"

SIN_LISTA = (
    "Esta carpeta de trabajo no tiene lista de precios para armar. Créela a partir de MaPreX o "
    "convirtiendo la que tiene."
)
SIN_TASA = "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar."

#: (código, tipo, descripción, unidad, precio en Bs) de la siembra ficticia.
INSUMOS = (
    ("MAT-001", "material", "Cemento gris", "saco", Decimal("400.00")),
    ("MAT-002", "material", "Arena lavada", "m3", Decimal("1250.50")),
    ("MO-001", "mano_obra", "Albañil", None, Decimal("3200.00")),
)


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    crear_esquema_carpeta(motor)
    try:
        with abrir_sesion(motor) as s:
            for codigo, tipo, descripcion, unidad, _ in INSUMOS:
                s.add(
                    models.Insumo(codigo=codigo, tipo=tipo, descripcion=descripcion, unidad=unidad)
                )
            s.flush()
            yield s
    finally:
        motor.dispose()


def _lista(
    s: Session, nombre: str, moneda: str = "Bs", fecha: date = JULIO, alcance: str | None = None
) -> models.ListaPrecios:
    lista = models.ListaPrecios(nombre=nombre, moneda=moneda, fecha_vigencia=fecha, origen="")
    s.add(lista)
    s.flush()
    if alcance is not None:
        s.add(models.ListaPreciosOrigen(lista_id=lista.id, alcance=alcance))
    for codigo, *_, precio in INSUMOS:
        insumo = s.scalars(select(models.Insumo).where(models.Insumo.codigo == codigo)).one()
        s.add(models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=precio))
    s.flush()
    s.expire(lista, ["precios"])
    return lista


def _precios(lista: models.ListaPrecios) -> dict[str, Decimal]:
    return {p.insumo.codigo: p.precio for p in lista.precios}


def _version(s: Session, lista: models.ListaPrecios, codigo: str) -> None:
    proyecto = s.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == "OBRA-01")
    ).one_or_none()
    if proyecto is None:
        proyecto = models.Proyecto(nombre="OBRA-01", descripcion="Vivienda de 80 m²")
        s.add(proyecto)
        s.flush()
    s.add(
        models.Presupuesto(
            codigo=codigo,
            proyecto_id=proyecto.id,
            fecha=HOY,
            moneda="Bs",
            lista_precios_id=lista.id,
            fcas=Decimal("0"),
            bono_alimentacion=Decimal("0"),
            administracion=Decimal("0"),
            utilidad=Decimal("0"),
        )
    )
    s.flush()


def _tasa(s: Session, fecha: date, valor: str = "40.00") -> None:
    registrar_importacion(
        s,
        definicion_tasa("venta"),
        [Observacion(fecha, Decimal(valor))],
        archivo="tasa_ficticia.xls",
        huella=f"{fecha:%Y%m%d}".ljust(64, "0"),
        fuente="BCV (dato ficticio de prueba)",
        fecha_descarga=fecha,
        responsable="ana",
        filas_leidas=1,
        filas_rechazadas=0,
    )


def _cuantas_listas(s: Session) -> int:
    return s.scalar(select(func.count()).select_from(models.ListaPrecios))


# --- moneda de la carpeta ---------------------------------------------------------------------


def test_la_tabla_de_la_carpeta_es_la_del_plan() -> None:
    tabla = METADATA_CARPETA.tables["mp_carpeta"]
    assert [c.name for c in tabla.columns] == ["id", "moneda", "declarada_por", "declarada_el"]
    assert [c.name for c in tabla.primary_key.columns] == ["id"]
    assert tabla.c.moneda.type.length == 10
    assert tabla.c.declarada_por.type.length == 200


def test_sin_declarar_y_sin_listas_la_carpeta_no_tiene_moneda(sesion: Session) -> None:
    assert armar.moneda_de_la_carpeta(sesion) is None


def test_sin_declarar_la_moneda_es_la_de_la_lista_vigente(sesion: Session) -> None:
    _lista(sesion, MAPREX)
    assert armar.moneda_de_la_carpeta(sesion) == "Bs"


def test_la_declarada_manda_sobre_la_de_la_lista(sesion: Session) -> None:
    _lista(sesion, MAPREX)
    sesion.add(CarpetaDeTrabajo(id=1, moneda="USD", declarada_por="ana", declarada_el=AHORA))
    sesion.flush()
    assert armar.moneda_de_la_carpeta(sesion) == "USD"


def test_las_listas_de_referencia_o_de_proyecto_no_dan_la_moneda(sesion: Session) -> None:
    _lista(sesion, MAPREX, alcance=models.ALCANCE_REFERENCIA)
    _lista(sesion, "Cotización en USD", moneda="USD", alcance=models.ALCANCE_PROYECTO)
    assert armar.moneda_de_la_carpeta(sesion) is None


def test_declarar_guarda_una_sola_fila_con_quien_y_cuando(sesion: Session) -> None:
    armar.declarar_moneda_de_la_carpeta(sesion, "Bs", responsable=" ana ", ahora=AHORA)
    filas = sesion.scalars(select(CarpetaDeTrabajo)).all()
    assert [(f.id, f.moneda, f.declarada_por, f.declarada_el) for f in filas] == [
        (1, "Bs", "ana", AHORA)
    ]
    assert armar.moneda_de_la_carpeta(sesion) == "Bs"


def test_declarar_otra_vez_la_misma_no_cambia_nada(sesion: Session) -> None:
    armar.declarar_moneda_de_la_carpeta(sesion, "Bs", responsable="ana", ahora=AHORA)
    armar.declarar_moneda_de_la_carpeta(
        sesion, "Bs", responsable="rita", ahora=datetime(2026, 10, 26, 8, 0)
    )
    filas = sesion.scalars(select(CarpetaDeTrabajo)).all()
    assert [(f.moneda, f.declarada_por, f.declarada_el) for f in filas] == [("Bs", "ana", AHORA)]


def test_no_se_cambia_la_moneda_declarada(sesion: Session) -> None:
    armar.declarar_moneda_de_la_carpeta(sesion, "Bs", responsable="ana", ahora=AHORA)
    with pytest.raises(CarpetaConOtraMoneda) as error:
        armar.declarar_moneda_de_la_carpeta(sesion, "USD", responsable="ana", ahora=AHORA)
    assert str(error.value) == (
        "La carpeta de trabajo ya trabaja en Bs: para trabajar en USD, cree otra carpeta."
    )
    assert armar.moneda_de_la_carpeta(sesion) == "Bs"


def test_no_se_declara_otra_moneda_que_la_de_la_lista_vigente(sesion: Session) -> None:
    _lista(sesion, MAPREX)
    with pytest.raises(CarpetaConOtraMoneda) as error:
        armar.declarar_moneda_de_la_carpeta(sesion, "USD", responsable="ana", ahora=AHORA)
    assert str(error.value) == (
        "La carpeta de trabajo ya trabaja en Bs: para trabajar en USD, cree otra carpeta."
    )
    assert sesion.scalars(select(CarpetaDeTrabajo)).all() == []


def test_declarar_la_moneda_de_la_lista_vigente_si_se_puede(sesion: Session) -> None:
    _lista(sesion, MAPREX)
    armar.declarar_moneda_de_la_carpeta(sesion, "Bs", responsable="ana", ahora=AHORA)
    assert sesion.get(CarpetaDeTrabajo, 1).moneda == "Bs"


@pytest.mark.parametrize("moneda", ["EUR", "bs", ""])
def test_declarar_una_moneda_que_no_existe_falla(sesion: Session, moneda: str) -> None:
    with pytest.raises(ValueError):
        armar.declarar_moneda_de_la_carpeta(sesion, moneda, responsable="ana", ahora=AHORA)
    assert sesion.scalars(select(CarpetaDeTrabajo)).all() == []


def test_declarar_sin_responsable_falla(sesion: Session) -> None:
    with pytest.raises(ValueError):
        armar.declarar_moneda_de_la_carpeta(sesion, "Bs", responsable="  ", ahora=AHORA)
    assert sesion.scalars(select(CarpetaDeTrabajo)).all() == []


# --- lista para armar -------------------------------------------------------------------------


def test_sin_listas_no_hay_lista_para_armar(sesion: Session) -> None:
    with pytest.raises(SinListaParaArmar) as error:
        armar.lista_para_armar(sesion, HOY)
    assert str(error.value) == SIN_LISTA
    assert armar.describir(sesion, HOY) is None


def test_la_lista_vigente_en_otra_moneda_no_sirve_para_armar(sesion: Session) -> None:
    _lista(sesion, "Base")
    # una carpeta declarada en USD que luego recibió una lista en Bs (p. ej. subida de otra)
    sesion.add(CarpetaDeTrabajo(id=1, moneda="USD", declarada_por="ana", declarada_el=AHORA))
    sesion.flush()
    with pytest.raises(SinListaParaArmar) as error:
        armar.lista_para_armar(sesion, HOY)
    assert str(error.value) == (
        "La lista vigente «Base» está en Bs y la carpeta trabaja en USD: "
        "conviértala antes de armar."
    )
    assert armar.describir(sesion, HOY) is None


def test_la_lista_para_armar_es_la_vigente_de_la_moneda_de_la_carpeta(sesion: Session) -> None:
    vieja = _lista(sesion, "Base", fecha=date(2026, 1, 15))
    vigente = _lista(sesion, MAPREX)
    _lista(sesion, "Futura", fecha=date(2026, 12, 1))
    _lista(sesion, "Cotización", fecha=HOY, alcance=models.ALCANCE_PROYECTO)
    assert armar.lista_para_armar(sesion, HOY).id == vigente.id
    assert armar.lista_para_armar(sesion, date(2026, 6, 30)).id == vieja.id


def test_describir_la_lista_para_armar(sesion: Session) -> None:
    vigente = _lista(sesion, MAPREX)
    vigente.origen = "lista_maprex_bs.csv"
    sesion.flush()
    assert armar.describir(sesion, HOY) == ListaParaArmar(
        lista_id=vigente.id, nombre=MAPREX, moneda="Bs", fecha=JULIO, origen="lista_maprex_bs.csv"
    )


# --- lista de hoy -----------------------------------------------------------------------------


def test_la_lista_de_hoy_deriva_la_vigente_con_la_fecha_de_hoy(sesion: Session) -> None:
    base = _lista(sesion, MAPREX)
    hoy = armar.lista_de_hoy(sesion, HOY, nueva_si_usada=False)
    assert hoy.id != base.id
    assert (hoy.nombre, hoy.moneda, hoy.fecha_vigencia, hoy.origen) == (
        "MaPreX julio 2026 en Bs al 25/10/2026",
        "Bs",
        HOY,
        "derivada de «MaPreX julio 2026 en Bs»",
    )
    assert _precios(hoy) == {
        "MAT-001": Decimal("400.00"),
        "MAT-002": Decimal("1250.50"),
        "MO-001": Decimal("3200.00"),
    }
    assert len(base.precios) == 3
    assert Catalogo(sesion).lista_vigente(HOY).id == hoy.id
    assert sesion.get(models.ListaPreciosOrigen, hoy.id) is None  # global
    assert armar.lista_de_hoy(sesion, HOY, nueva_si_usada=False).id == hoy.id
    assert _cuantas_listas(sesion) == 2


def test_la_lista_de_hoy_ya_existente_se_reutiliza_aunque_este_usada(sesion: Session) -> None:
    hoy = _lista(sesion, "Lista de hoy", fecha=HOY)
    _version(sesion, hoy, "VIV-001")
    assert armar.lista_de_hoy(sesion, HOY, nueva_si_usada=False).id == hoy.id


def test_la_lista_de_hoy_sin_usar_se_reutiliza_con_nueva_si_usada(sesion: Session) -> None:
    hoy = _lista(sesion, "Lista de hoy", fecha=HOY)
    assert armar.lista_de_hoy(sesion, HOY, nueva_si_usada=True).id == hoy.id


def test_una_lista_de_hoy_usada_por_una_version_da_otra_numerada(sesion: Session) -> None:
    _lista(sesion, MAPREX)
    primera = armar.lista_de_hoy(sesion, HOY, nueva_si_usada=False)
    _version(sesion, primera, "VIV-001")

    segunda = armar.lista_de_hoy(sesion, HOY, nueva_si_usada=True)
    assert segunda.nombre == "MaPreX julio 2026 en Bs al 25/10/2026 (2)"
    assert segunda.origen == "derivada de «MaPreX julio 2026 en Bs al 25/10/2026»"
    assert segunda.fecha_vigencia == HOY
    assert _precios(segunda) == _precios(primera)

    _version(sesion, segunda, "VIV-002")
    tercera = armar.lista_de_hoy(sesion, HOY, nueva_si_usada=True)
    assert tercera.nombre == "MaPreX julio 2026 en Bs al 25/10/2026 (3)"
    assert Catalogo(sesion).lista_vigente(HOY).id == tercera.id


def test_el_nombre_de_la_lista_de_hoy_cabe_en_120_letras(sesion: Session) -> None:
    _lista(sesion, "L" * 120)
    hoy = armar.lista_de_hoy(sesion, HOY, nueva_si_usada=False)
    assert hoy.nombre == "L" * 106 + " al 25/10/2026"
    assert len(hoy.nombre) == 120


def test_la_lista_de_hoy_respeta_la_moneda_de_la_carpeta(sesion: Session) -> None:
    _lista(sesion, "Base")
    sesion.add(CarpetaDeTrabajo(id=1, moneda="USD", declarada_por="ana", declarada_el=AHORA))
    sesion.flush()
    with pytest.raises(SinListaParaArmar) as error:
        armar.lista_de_hoy(sesion, HOY, nueva_si_usada=False)
    assert "está en Bs y la carpeta trabaja en USD" in str(error.value)
    assert _cuantas_listas(sesion) == 1


def test_sin_lista_no_hay_lista_de_hoy(sesion: Session) -> None:
    with pytest.raises(SinListaParaArmar) as error:
        armar.lista_de_hoy(sesion, HOY, nueva_si_usada=True)
    assert str(error.value) == SIN_LISTA
    assert _cuantas_listas(sesion) == 0


# --- crear la lista para armar ----------------------------------------------------------------


def test_crear_desde_maprex_en_una_carpeta_en_bs_copia_la_referencia(sesion: Session) -> None:
    referencia = _lista(sesion, MAPREX, alcance=models.ALCANCE_REFERENCIA)
    precio_cemento = next(p for p in referencia.precios if p.insumo.codigo == "MAT-001")
    sesion.add(models.ReferenciaPrecio(precio_id=precio_cemento.id, referencia="REF-0001"))
    armar.declarar_moneda_de_la_carpeta(sesion, "Bs", responsable="ana", ahora=AHORA)

    nueva = armar.crear_lista_para_armar(sesion, desde="maprex", fecha=HOY, responsable="ana")

    assert (nueva.nombre, nueva.moneda, nueva.fecha_vigencia) == (
        "MaPreX julio 2026 en Bs al 25/10/2026",
        "Bs",
        HOY,
    )
    assert nueva.origen == "copia de la referencia «MaPreX julio 2026 en Bs», por ana"
    assert _precios(nueva) == _precios(referencia)
    assert armar.lista_para_armar(sesion, HOY).id == nueva.id
    copia_cemento = next(p for p in nueva.precios if p.insumo.codigo == "MAT-001")
    assert sesion.get(models.ReferenciaPrecio, copia_cemento.id).referencia == "REF-0001"
    assert len(referencia.precios) == 3


def test_crear_desde_maprex_dos_veces_el_mismo_dia_numera_la_segunda(sesion: Session) -> None:
    _lista(sesion, MAPREX, alcance=models.ALCANCE_REFERENCIA)
    armar.declarar_moneda_de_la_carpeta(sesion, "Bs", responsable="ana", ahora=AHORA)
    armar.crear_lista_para_armar(sesion, desde="maprex", fecha=HOY, responsable="ana")
    segunda = armar.crear_lista_para_armar(sesion, desde="maprex", fecha=HOY, responsable="ana")
    assert segunda.nombre == "MaPreX julio 2026 en Bs al 25/10/2026 (2)"


def test_crear_desde_maprex_en_una_carpeta_en_usd_convierte_con_la_tasa(sesion: Session) -> None:
    _lista(sesion, MAPREX, alcance=models.ALCANCE_REFERENCIA)
    armar.declarar_moneda_de_la_carpeta(sesion, "USD", responsable="ana", ahora=AHORA)
    _tasa(sesion, date(2026, 10, 24))

    nueva = armar.crear_lista_para_armar(sesion, desde="maprex", fecha=HOY, responsable="ana")

    assert (nueva.nombre, nueva.moneda, nueva.fecha_vigencia) == (
        "MaPreX julio 2026 en USD al 25/10/2026",
        "USD",
        HOY,
    )
    assert nueva.origen == (
        "copia de la referencia «MaPreX julio 2026 en Bs» en USD con 40.00 Bs/USD del "
        "24/10/2026, por ana"
    )
    assert _precios(nueva) == {
        "MAT-001": Decimal("10"),
        "MAT-002": Decimal("31.2625"),
        "MO-001": Decimal("80"),
    }
    cemento = next(p for p in nueva.precios if p.insumo.codigo == "MAT-001")
    origen = sesion.get(models.PrecioOrigen, cemento.id)
    assert (origen.tasa, origen.fecha_tasa) == (Decimal("40.00"), date(2026, 10, 24))
    assert (origen.moneda_original, origen.precio_original) == ("Bs", Decimal("400.00"))
    assert armar.lista_para_armar(sesion, HOY).id == nueva.id


def test_la_tasa_de_hace_siete_dias_todavia_sirve(sesion: Session) -> None:
    _lista(sesion, MAPREX, alcance=models.ALCANCE_REFERENCIA)
    armar.declarar_moneda_de_la_carpeta(sesion, "USD", responsable="ana", ahora=AHORA)
    _tasa(sesion, date(2026, 10, 18))
    nueva = armar.crear_lista_para_armar(sesion, desde="maprex", fecha=HOY, responsable="ana")
    assert _precios(nueva)["MAT-001"] == Decimal("10")


def test_crear_desde_maprex_sin_tasa_reciente_no_escribe_nada(sesion: Session) -> None:
    _lista(sesion, MAPREX, alcance=models.ALCANCE_REFERENCIA)
    armar.declarar_moneda_de_la_carpeta(sesion, "USD", responsable="ana", ahora=AHORA)
    _tasa(sesion, date(2026, 10, 17))  # ocho días antes
    with pytest.raises(SinListaParaArmar) as error:
        armar.crear_lista_para_armar(sesion, desde="maprex", fecha=HOY, responsable="ana")
    assert str(error.value) == SIN_TASA
    assert _cuantas_listas(sesion) == 1


def test_sin_tasa_no_se_carga_la_referencia_de_maprex(sesion: Session) -> None:
    armar.declarar_moneda_de_la_carpeta(sesion, "USD", responsable="ana", ahora=AHORA)
    with pytest.raises(SinListaParaArmar) as error:
        armar.crear_lista_para_armar(sesion, desde="maprex", fecha=HOY, responsable="ana")
    assert str(error.value) == SIN_TASA
    assert lista_de_referencia(sesion) is None
    assert _cuantas_listas(sesion) == 0


def test_sin_referencia_se_carga_maprex_y_se_copia(sesion: Session) -> None:
    armar.declarar_moneda_de_la_carpeta(sesion, "Bs", responsable="ana", ahora=AHORA)
    nueva = armar.crear_lista_para_armar(sesion, desde="maprex", fecha=HOY, responsable="ana")
    referencia = lista_de_referencia(sesion)
    assert referencia is not None and referencia.nombre == MAPREX
    assert nueva.nombre == "MaPreX julio 2026 en Bs al 25/10/2026"
    assert len(nueva.precios) == len(referencia.precios) > 0
    assert armar.lista_para_armar(sesion, HOY).id == nueva.id


def test_crear_desde_maprex_sin_moneda_declarada_ni_listas_queda_en_bs(sesion: Session) -> None:
    _lista(sesion, MAPREX, alcance=models.ALCANCE_REFERENCIA)
    nueva = armar.crear_lista_para_armar(sesion, desde="maprex", fecha=HOY, responsable="ana")
    assert nueva.moneda == "Bs"
    assert armar.moneda_de_la_carpeta(sesion) == "Bs"


def test_convertir_la_vigente_a_la_moneda_de_la_carpeta(sesion: Session) -> None:
    _lista(sesion, "Base")
    sesion.add(CarpetaDeTrabajo(id=1, moneda="USD", declarada_por="ana", declarada_el=AHORA))
    _tasa(sesion, date(2026, 10, 24))

    nueva = armar.crear_lista_para_armar(sesion, desde="convertir", fecha=HOY, responsable="ana")

    assert (nueva.nombre, nueva.moneda, nueva.fecha_vigencia) == (
        "Base en USD al 25/10/2026",
        "USD",
        HOY,
    )
    assert nueva.origen == "«Base» convertida a USD con 40.00 Bs/USD del 24/10/2026, por ana"
    assert _precios(nueva) == {
        "MAT-001": Decimal("10"),
        "MAT-002": Decimal("31.2625"),
        "MO-001": Decimal("80"),
    }
    assert armar.lista_para_armar(sesion, HOY).id == nueva.id


def test_convertir_sin_tasa_reciente_no_escribe_nada(sesion: Session) -> None:
    _lista(sesion, "Base")
    sesion.add(CarpetaDeTrabajo(id=1, moneda="USD", declarada_por="ana", declarada_el=AHORA))
    sesion.flush()
    with pytest.raises(SinListaParaArmar) as error:
        armar.crear_lista_para_armar(sesion, desde="convertir", fecha=HOY, responsable="ana")
    assert str(error.value) == SIN_TASA
    assert _cuantas_listas(sesion) == 1


def test_convertir_una_lista_que_ya_esta_en_la_moneda_de_la_carpeta(sesion: Session) -> None:
    _lista(sesion, "Base")
    with pytest.raises(SinListaParaArmar) as error:
        armar.crear_lista_para_armar(sesion, desde="convertir", fecha=HOY, responsable="ana")
    assert str(error.value) == "La lista vigente «Base» ya está en Bs: no hay nada que convertir."
    assert _cuantas_listas(sesion) == 1


def test_convertir_sin_listas(sesion: Session) -> None:
    armar.declarar_moneda_de_la_carpeta(sesion, "USD", responsable="ana", ahora=AHORA)
    with pytest.raises(SinListaParaArmar) as error:
        armar.crear_lista_para_armar(sesion, desde="convertir", fecha=HOY, responsable="ana")
    assert str(error.value) == SIN_LISTA


def test_crear_sin_responsable_falla(sesion: Session) -> None:
    _lista(sesion, MAPREX, alcance=models.ALCANCE_REFERENCIA)
    with pytest.raises(ValueError):
        armar.crear_lista_para_armar(sesion, desde="maprex", fecha=HOY, responsable=" ")
    assert _cuantas_listas(sesion) == 1


# --- lista para el proyecto (foco 1) ----------------------------------------------------------


def _proyecto(s: Session, nombre: str, moneda: str) -> models.Proyecto:
    proyecto = models.Proyecto(nombre=nombre, descripcion="Vivienda de 80 m²")
    s.add(proyecto)
    s.flush()
    declarar_moneda(s, proyecto, moneda, responsable="ana", ahora=AHORA)
    return proyecto


def test_un_proyecto_en_la_moneda_de_la_carpeta_usa_la_lista_para_armar(sesion: Session) -> None:
    vigente = _lista(sesion, MAPREX)
    _proyecto(sesion, "OBRA-01", "Bs")
    assert armar.lista_para_el_proyecto(sesion, "OBRA-01", HOY, responsable="ana").id == vigente.id
    assert _cuantas_listas(sesion) == 1


def test_un_proyecto_en_usd_en_una_carpeta_en_bs_se_valora_convertido(sesion: Session) -> None:
    vigente = _lista(sesion, MAPREX)
    armar.declarar_moneda_de_la_carpeta(sesion, "Bs", responsable="ana", ahora=AHORA)
    proyecto = _proyecto(sesion, "OBRA-02", "USD")
    _tasa(sesion, date(2026, 10, 24))

    lista = armar.lista_para_el_proyecto(sesion, "OBRA-02", HOY, responsable="ana")

    assert lista.moneda == "USD"
    assert lista.id != vigente.id
    origen = sesion.get(models.ListaPreciosOrigen, lista.id)
    assert (origen.alcance, origen.proyecto_id) == (models.ALCANCE_PROYECTO, proyecto.id)
    assert (origen.tasa, origen.fecha_tasa) == (Decimal("40.00"), date(2026, 10, 24))
    assert _precios(lista) == {
        "MAT-001": Decimal("10"),
        "MAT-002": Decimal("31.2625"),
        "MO-001": Decimal("80"),
    }
    assert "40.00 Bs/USD del 24/10/2026" in lista.origen
    assert Catalogo(sesion).lista_vigente(HOY).id == vigente.id  # no cambia la de la carpeta
    otra_vez = armar.lista_para_el_proyecto(sesion, "OBRA-02", HOY, responsable="ana")
    assert otra_vez.id == lista.id
    assert _cuantas_listas(sesion) == 2


def test_la_conversion_del_proyecto_es_por_dia(sesion: Session) -> None:
    _lista(sesion, MAPREX)
    _proyecto(sesion, "OBRA-02", "USD")
    _tasa(sesion, date(2026, 10, 24))
    _tasa(sesion, date(2026, 10, 26), "41.00")
    hoy = armar.lista_para_el_proyecto(sesion, "OBRA-02", HOY, responsable="ana")
    manana = armar.lista_para_el_proyecto(sesion, "OBRA-02", date(2026, 10, 26), responsable="ana")
    assert manana.id != hoy.id
    assert sesion.get(models.ListaPreciosOrigen, manana.id).tasa == Decimal("41.00")


def test_la_conversion_de_un_proyecto_no_sirve_a_otro(sesion: Session) -> None:
    _lista(sesion, MAPREX)
    _proyecto(sesion, "OBRA-02", "USD")
    _proyecto(sesion, "OBRA-03", "USD")
    _tasa(sesion, date(2026, 10, 24))
    dos = armar.lista_para_el_proyecto(sesion, "OBRA-02", HOY, responsable="ana")
    tres = armar.lista_para_el_proyecto(sesion, "OBRA-03", HOY, responsable="ana")
    assert dos.id != tres.id


def test_un_proyecto_en_otra_moneda_sin_tasa_no_se_valora(sesion: Session) -> None:
    _lista(sesion, MAPREX)
    _proyecto(sesion, "OBRA-02", "USD")
    with pytest.raises(SinListaParaArmar) as error:
        armar.lista_para_el_proyecto(sesion, "OBRA-02", HOY, responsable="ana")
    assert str(error.value) == SIN_TASA
    assert _cuantas_listas(sesion) == 1


def test_el_proyecto_hereda_el_aviso_de_la_carpeta(sesion: Session) -> None:
    _proyecto(sesion, "OBRA-02", "USD")
    with pytest.raises(SinListaParaArmar) as error:
        armar.lista_para_el_proyecto(sesion, "OBRA-02", HOY, responsable="ana")
    assert str(error.value) == SIN_LISTA


def test_un_proyecto_que_no_existe(sesion: Session) -> None:
    _lista(sesion, MAPREX)
    with pytest.raises(ValueError) as error:
        armar.lista_para_el_proyecto(sesion, "OBRA-99", HOY, responsable="ana")
    assert not isinstance(error.value, SinListaParaArmar)
    assert str(error.value) == "No hay ninguna obra «OBRA-99» en esta carpeta de trabajo."
