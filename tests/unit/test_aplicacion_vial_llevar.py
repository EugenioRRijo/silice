"""Plan vial, Tarea 8b: llevar los tramos al presupuesto (borrador de la Hoja). Datos FICTICIOS.

La carpeta es la «Vivienda Demo 80 m2» de `tests/fixtures/carpeta_aprobaciones.py` (VIV-001) con
las 15 partidas viales en la lista «Lista Bs de prueba». Los tramos salen de
`data/samples/vial/via_ficticia.csv` (leídos con `tramos_desde_csv`, como los importa la API) y se
guardan en VIV-001. Las pruebas no llaman a `derivar_tramos`: lo esperado es la memoria de cálculo
del README de la muestra, escrita a mano (20 cantidades: cada línea con su pintura, Tarea 16b).

Reglas (plan, Tarea 8b): cada cantidad entra como renglón con el `origen_id` y el `origen_tipo` de
la derivación, nunca «a-mano:n»; llevar otra vez sincroniza (los renglones «tramo:» se reemplazan,
los demás no se tocan, la cantidad escrita sobre una clave que sigue se conserva y la de una clave
que desaparece se descarta); partidas sin APU: el 404 de `PartidaFueraDelCatalogo` con todos los
códigos y nada llevado; llevar rearma las reglas viales del borrador.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.vial.modelo import Tramo
from adapters.vial.reglas import ReglasViales
from aplicacion import hoja, hoja_borradores, hoja_edicion, hoja_vial, hoja_vista, vial
from core import models
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts import Dominio, ItemComputo, OrigenTipo
from core.contracts.apu import ComposicionAPU, LineaMaterial
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import FECHA, guardar_version, sembrar_vivienda

D = Decimal
ANA = "Ana <ana>"
LUNES = datetime(2026, 10, 19, 9, 0)
HOY = date(2026, 10, 31)
HUELLA = "h" * 64
CASO = "caso-de-prueba"
MUESTRA = Path(__file__).resolve().parents[2] / "data" / "samples" / "vial" / "via_ficticia.csv"

#: Las 15 partidas viales (código, descripción, unidad), copiadas a mano de la tabla del README.
PARTIDAS = (
    ("C-000.000.001", "Fresado de pavimento asfáltico", "m3"),
    ("C-000.000.002", "Base granular compactada", "m3"),
    ("C-000.000.003", "Sub-base granular compactada", "m3"),
    ("C-000.000.004", "Riego de imprimación", "m2"),
    ("C-000.000.005", "Ligante del riego de imprimación", "l"),
    ("C-000.000.006", "Riego de adherencia", "m2"),
    ("C-000.000.007", "Ligante del riego de adherencia", "l"),
    ("C-000.000.008", "Carpeta de concreto asfáltico", "m2"),
    ("C-000.000.009", "Mezcla asfáltica de la carpeta", "t"),
    ("C-000.000.010", "Bacheo con mezcla asfáltica", "m3"),
    ("C-000.000.011", "Mezcla asfáltica del bacheo", "t"),
    ("C-000.000.012", "Demarcación con línea continua", "m"),
    ("C-000.000.013", "Demarcación con línea discontinua", "m"),
    ("C-000.000.014", "Transporte de mezcla asfáltica desde la planta", "t·km"),
    ("C-000.000.015", "Pintura de demarcación", "l"),
)

#: La memoria de cálculo de `data/samples/vial/README.md`: (código, origen, cantidad), en orden.
ESPERADO = [
    ("C-000.000.001", "tramo:T1:capa:1", D("438")),
    ("C-000.000.006", "tramo:T1:capa:2", D("8760")),
    ("C-000.000.007", "tramo:T1:capa:2", D("3504")),
    ("C-000.000.008", "tramo:T1:capa:3", D("8760")),
    ("C-000.000.009", "tramo:T1:capa:3", D("1029.3")),
    ("C-000.000.014", "tramo:T1:capa:3", D("15439.5")),
    ("C-000.000.012", "tramo:T1:demarcacion:1", D("2400")),
    ("C-000.000.015", "tramo:T1:demarcacion:1", D("87.6")),
    ("C-000.000.013", "tramo:T1:demarcacion:2", D("450")),
    ("C-000.000.015", "tramo:T1:demarcacion:2", D("16.425")),
    ("C-000.000.003", "tramo:T2:capa:1", D("1300")),
    ("C-000.000.002", "tramo:T2:capa:2", D("1040")),
    ("C-000.000.004", "tramo:T2:capa:3", D("5200")),
    ("C-000.000.005", "tramo:T2:capa:3", D("6240")),
    ("C-000.000.008", "tramo:T2:capa:4", D("5200")),
    ("C-000.000.009", "tramo:T2:capa:4", D("478.4")),
    ("C-000.000.014", "tramo:T2:capa:4", D("8611.2")),
    ("C-000.000.010", "tramo:T3:capa:1", D("15")),
    ("C-000.000.011", "tramo:T3:capa:1", D("34.5")),
    ("C-000.000.014", "tramo:T3:capa:1", D("621")),
]
SIN_T3 = [fila for fila in ESPERADO if not fila[1].startswith("tramo:T3:")]
MEZCLA_T1 = "C-000.000.009|tramo:T1:capa:3"
MEZCLA_T3 = "C-000.000.011|tramo:T3:capa:1"


def _catalogar(sesion: Session, *, sin: tuple[str, ...] = ()) -> None:
    """Las partidas viales (salvo `sin`) en la lista de la vivienda, con un APU de una línea."""
    lista = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == "Lista Bs de prueba")
    ).one()
    for codigo, descripcion, unidad in PARTIDAS:
        if codigo in sin:
            continue
        linea = LineaMaterial(f"Material de {codigo}", unidad, D("1"), D("3"))
        apu = ComposicionAPU(codigo, descripcion, unidad, D("10"), materiales=(linea,))
        Catalogo(sesion).cargar_composicion(apu, lista, Dominio.CIVIL, FECHA, "prueba")
    sesion.commit()


def _version_id(sesion: Session, codigo: str = "VIV-001") -> int:
    return sesion.scalars(
        select(models.Presupuesto.id).where(models.Presupuesto.codigo == codigo)
    ).one()


def _tramos() -> list[Tramo]:
    return vial.tramos_desde_csv(MUESTRA.read_bytes(), "via_ficticia.csv")


def _preparar(tmp_path: Path, *, sin: tuple[str, ...] = ()) -> Iterator[Session]:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    hoja_borradores.olvidar_todo()
    try:
        with abrir_sesion(motor) as sesion:
            sembrar_vivienda(sesion, usuario=ANA)
            _catalogar(sesion, sin=sin)
            vial.guardar_tramos(sesion, _version_id(sesion), _tramos(), usuario=ANA, ahora=LUNES)
            yield sesion
    finally:
        hoja_borradores.olvidar_todo()
        motor.dispose()


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator[Session]:
    yield from _preparar(tmp_path)


def _obra(sesion: Session) -> models.Proyecto:
    return sesion.scalars(select(models.Proyecto)).one()


def _llevar(sesion: Session, version: str = "VIV-001") -> tuple[str, int]:
    return hoja_vial.llevar_tramos_a_la_hoja(
        sesion, HUELLA, CASO, _obra(sesion), version, responsable=ANA, hoy=HOY
    )


def _de_tramo(vivo: hoja_borradores.BorradorVivo) -> list[ItemComputo]:
    return [i for i in vivo.borrador.items_base if i.origen_id.startswith("tramo:")]


def _filas(items: list[ItemComputo]) -> list[tuple[str, str, Decimal]]:
    return [(i.codigo_partida, i.origen_id, i.cantidad) for i in items]


def _escribir(sesion: Session, vivo, clave: str, cantidad: str):
    return hoja_edicion.editar_cantidades(
        sesion, HUELLA, vivo.id, vivo.rev, [{"clave": clave, "cantidad": cantidad}]
    )


# --- regla 1: cada cantidad entra con su origen de tramo ------------------------------------------


def test_llevar_crea_renglones_con_origen_de_tramo(sesion: Session) -> None:
    id_, renglones = _llevar(sesion)

    assert renglones == 20
    vivo = hoja_borradores.obtener(HUELLA, id_)
    assert vivo.version == "VIV-001"
    assert _filas(_de_tramo(vivo)) == ESPERADO
    assert all(i.origen_tipo is OrigenTipo.REGLA for i in _de_tramo(vivo))
    assert not [i for i in vivo.borrador.items_base if i.origen_id.startswith("a-mano:")]
    # la clave del renglón es la de siempre: codigo|origen_id
    claves = hoja.claves_de_items(hoja.items_sin_escribir(vivo.borrador))
    assert MEZCLA_T1 in claves
    # cada partida vial lleva su APU de la lista de la versión (entra al presupuesto, no pendiente)
    assert {c for c, _, _ in ESPERADO} <= set(vivo.borrador.composiciones)


def test_llevar_no_guarda_version(sesion: Session) -> None:
    versiones = sesion.scalars(select(models.Presupuesto.codigo)).all()
    _llevar(sesion)
    assert sesion.scalars(select(models.Presupuesto.codigo)).all() == versiones


# --- regla 2: llevar otra vez sincroniza --------------------------------------------------------


def test_llevar_dos_veces_no_duplica_y_conserva_lo_escrito(sesion: Session) -> None:
    id_, _ = _llevar(sesion)
    vivo = _escribir(sesion, hoja_borradores.obtener(HUELLA, id_), MEZCLA_T1, "900")
    vivo, a_mano = hoja_edicion.agregar(
        sesion, HUELLA, id_, vivo.rev, codigo="OBRA-04", cantidad="12", calculo="", nota="pared"
    )
    propios_antes = [i for i in vivo.borrador.items_base if not i.origen_id.startswith("tramo:")]

    otra_vez, renglones = _llevar(sesion)

    assert (otra_vez, renglones) == (id_, 20)
    vivo = hoja_borradores.obtener(HUELLA, id_)
    assert _filas(_de_tramo(vivo)) == ESPERADO  # ni uno de más
    assert vivo.borrador.cantidades[MEZCLA_T1] == D("900")
    propios = [i for i in vivo.borrador.items_base if not i.origen_id.startswith("tramo:")]
    assert propios == propios_antes
    assert vivo.borrador.notas[a_mano] == "pared"


def test_llevar_otra_vez_sin_cambios_no_sube_el_rev(sesion: Session) -> None:
    id_, _ = _llevar(sesion)
    rev = hoja_borradores.obtener(HUELLA, id_).rev
    _llevar(sesion)
    assert hoja_borradores.obtener(HUELLA, id_).rev == rev


def test_tramo_quitado_desaparece_al_volver_a_llevar(sesion: Session) -> None:
    id_, _ = _llevar(sesion)
    _escribir(sesion, hoja_borradores.obtener(HUELLA, id_), MEZCLA_T3, "40")
    vial.guardar_tramos(sesion, _version_id(sesion), _tramos()[:2], usuario=ANA, ahora=LUNES)

    _, renglones = _llevar(sesion)

    assert renglones == 17
    vivo = hoja_borradores.obtener(HUELLA, id_)
    assert _filas(_de_tramo(vivo)) == SIN_T3
    assert MEZCLA_T3 not in vivo.borrador.cantidades


def test_lo_escrito_en_una_version_guardada_se_conserva_al_sincronizar() -> None:
    """Un renglón de tramo que vuelve de una versión guardada con la cantidad escrita a mano llega
    en `items_base` como MANUAL con esa cantidad (no en `cantidades`): sincronizar la conserva como
    escrita sobre la cantidad derivada. Uno que llegó como REGLA (el de antes de cambiar el tramo)
    toma la derivación nueva."""
    escrito = ItemComputo(
        codigo_partida="C-000.000.009",
        descripcion="Mezcla asfáltica de la carpeta, tramo T1",
        unidad="t",
        cantidad=D("900"),
        origen_id="tramo:T1:capa:3",
        origen_tipo=OrigenTipo.MANUAL,
        dominio=Dominio.CIVIL,
        regla="900",
        parametros={},
    )
    viejo = replace(
        escrito,
        codigo_partida="C-000.000.008",
        descripcion="Carpeta de concreto asfáltico, tramo T1",
        unidad="m2",
        cantidad=D("8000"),
        origen_tipo=OrigenTipo.REGLA,
        regla="longitud*ancho",
        parametros={"longitud": D("1000"), "ancho": D("8")},
    )
    borrador = hoja.Borrador(fecha=HOY, moneda="Bs", items_base=(viejo, escrito))
    tramo_t1 = _tramos()[:1]

    nuevo = hoja_vial.sincronizar_renglones(borrador, hoja_vial.items_de_tramos(tramo_t1), ())

    por_clave = dict(zip(hoja.claves_de_items(nuevo.items_base), nuevo.items_base, strict=True))
    assert por_clave["C-000.000.008|tramo:T1:capa:3"].cantidad == D("8760")
    assert por_clave[MEZCLA_T1].cantidad == D("1029.3")
    assert dict(nuevo.cantidades) == {MEZCLA_T1: D("900")}


def test_los_renglones_de_tramo_quedan_donde_estaban() -> None:
    """Sincronizar pone la derivación en el sitio del primer renglón de tramo: llevar otra vez no
    reordena la Hoja."""

    def a_mano(n: int) -> ItemComputo:
        return ItemComputo(
            codigo_partida="OBRA-04",
            descripcion="Paredes",
            unidad="m2",
            cantidad=D(n),
            origen_id=f"a-mano:{n}",
            origen_tipo=OrigenTipo.MANUAL,
            dominio=Dominio.CIVIL,
            parametros={},
        )

    viales = hoja_vial.items_de_tramos(_tramos()[2:])  # T3: tres renglones
    borrador = hoja.Borrador(fecha=HOY, moneda="Bs", items_base=(a_mano(1), *viales, a_mano(2)))
    nuevo = hoja_vial.sincronizar_renglones(borrador, viales, ())
    assert [i.origen_id for i in nuevo.items_base] == [
        "a-mano:1",
        "tramo:T3:capa:1",
        "tramo:T3:capa:1",
        "tramo:T3:capa:1",
        "a-mano:2",
    ]
    assert nuevo == borrador


# --- regla 3: partidas sin APU ------------------------------------------------------------------


def test_partidas_sin_apu_dan_404_con_todos_los_codigos_y_no_llevan_nada(tmp_path: Path) -> None:
    for sesion in _preparar(tmp_path, sin=("C-000.000.012", "C-000.000.013")):
        with pytest.raises(hoja_edicion.PartidaFueraDelCatalogo) as error:
            _llevar(sesion)
        assert str(error.value) == (
            "Las partidas «C-000.000.012» y «C-000.000.013» no están en el catálogo: "
            "compóngalas primero en Componer."
        )
        assert hoja_edicion.borradores_para_retomar(HUELLA, CASO) == []


def test_partidas_sin_apu_no_tocan_el_borrador_que_ya_estaba(tmp_path: Path) -> None:
    for sesion in _preparar(tmp_path, sin=("C-000.000.014",)):
        abierta = hoja.abrir_version(sesion, Catalogo(sesion), _obra(sesion).nombre, "VIV-001")
        vivo = hoja_borradores.crear(
            HUELLA, CASO, _obra(sesion).nombre, "VIV-001", abierta.borrador, abierta
        )
        antes = (vivo.borrador, vivo.rev)
        with pytest.raises(hoja_edicion.PartidaFueraDelCatalogo) as error:
            _llevar(sesion)
        assert str(error.value) == (
            "La partida «C-000.000.014» no está en el catálogo: compóngala primero en Componer."
        )
        assert (vivo.borrador, vivo.rev) == antes


def test_una_obra_sin_tramos_no_lleva_nada(tmp_path: Path) -> None:
    for sesion in _preparar(tmp_path):
        vial.guardar_tramos(sesion, _version_id(sesion), [], usuario=ANA, ahora=LUNES)
        with pytest.raises(hoja_vial.SinTramos) as error:
            _llevar(sesion)
        assert str(error.value) == (
            "La versión VIV-001 no tiene tramos: impórtelos en «Tramos de la vía» antes de "
            "llevarlos al presupuesto."
        )
        assert hoja_edicion.borradores_para_retomar(HUELLA, CASO) == []


# --- la versión que se ve es la del borrador (ronda 2, MAYOR del árbitro) -----------------------


def _con_viv002(sesion: Session) -> None:
    """VIV-002, posterior a VIV-001: es la vigente y hereda sus tramos."""
    guardar_version(sesion, _obra(sesion), "VIV-002", usuario=ANA)


def test_un_borrador_de_otra_version_da_409_y_no_cambia_nada(sesion: Session) -> None:
    _con_viv002(sesion)
    nombre = _obra(sesion).nombre
    abierta = hoja.abrir_version(sesion, Catalogo(sesion), nombre, "VIV-001")
    vivo = hoja_borradores.crear(HUELLA, CASO, nombre, "VIV-001", abierta.borrador, abierta)
    antes = (vivo.borrador, vivo.rev)

    with pytest.raises(hoja_vial.BorradorDeOtraVersion) as error:
        _llevar(sesion, "VIV-002")

    assert str(error.value) == (
        "La Hoja de la obra tiene abierto un borrador de VIV-001; está viendo los tramos de "
        "VIV-002. Guarde o descarte ese borrador en la Hoja, o elija VIV-001 aquí, y vuelva a "
        "llevar."
    )
    assert (vivo.borrador, vivo.rev) == antes
    assert not _de_tramo(vivo)


def test_sin_borrador_y_otra_version_que_la_vigente_da_409_y_no_abre_nada(sesion: Session) -> None:
    _con_viv002(sesion)

    with pytest.raises(hoja_vial.BorradorDeOtraVersion) as error:
        _llevar(sesion, "VIV-001")

    assert str(error.value) == (
        "La Hoja de la obra se abrirá sobre la versión vigente, VIV-002; está viendo los tramos "
        "de VIV-001. Elija VIV-002 aquí, o abra VIV-001 en la Hoja, y vuelva a llevar."
    )
    assert hoja_edicion.borradores_para_retomar(HUELLA, CASO) == []


def test_con_la_version_del_borrador_se_lleva(sesion: Session) -> None:
    _con_viv002(sesion)
    id_, renglones = _llevar(sesion, "VIV-002")
    vivo = hoja_borradores.obtener(HUELLA, id_)
    assert (vivo.version, renglones) == ("VIV-002", 20)
    assert _filas(_de_tramo(vivo)) == ESPERADO  # los heredados de VIV-001


def test_una_version_que_no_existe_no_lleva_nada(sesion: Session) -> None:
    with pytest.raises(vial.VersionInexistente):
        _llevar(sesion, "VIV-099")
    assert hoja_edicion.borradores_para_retomar(HUELLA, CASO) == []


def test_la_eleccion_del_borrador_es_una_sola() -> None:
    """La versión del borrador la decide `elaboracion.version_del_borrador_de_la_obra`, la misma
    que usa `borrador_de_la_obra` al abrirlo (menor 3 del árbitro)."""
    from aplicacion import elaboracion

    assert callable(elaboracion.version_del_borrador_de_la_obra)
    assert callable(elaboracion.borrador_de_la_obra)
    assert not hasattr(hoja_vial, "_version_del_borrador")


# --- regla 4: llevar rearma las reglas viales ---------------------------------------------------


def test_llevar_rearma_las_reglas_viales_y_la_auditoria_muestra_vr1(sesion: Session) -> None:
    id_, _ = _llevar(sesion)
    _escribir(sesion, hoja_borradores.obtener(HUELLA, id_), MEZCLA_T1, "900")
    vivo = hoja_borradores.obtener(HUELLA, id_)
    vr = [h for h in hoja_vista.informe_de_auditoria(vivo).hallazgos if h.regla.startswith("VR")]
    assert [(h.regla, h.origen_ids, h.valor_observado, h.valor_esperado) for h in vr] == [
        ("VR1", ("tramo:T1:capa:3",), D("900"), D("1029.3"))
    ]

    # se quita T3 y se vuelve a llevar: las reglas del borrador son las de los tramos de ahora
    vial.guardar_tramos(sesion, _version_id(sesion), _tramos()[:2], usuario=ANA, ahora=LUNES)
    _llevar(sesion)
    viales = [r for r in vivo.borrador.reglas_extra if isinstance(r, ReglasViales)]
    assert [[t.id for t in r.tramos] for r in viales] == [["T1", "T2"]]


def test_rearmar_sin_cambios_de_renglones_tambien_cambia_las_reglas(sesion: Session) -> None:
    """Si se guardan otra vez los mismos tramos (un guardado nuevo), los renglones no cambian pero
    las reglas se vuelven a armar con lo leído ahora; el `rev` no sube."""
    id_, _ = _llevar(sesion)
    vivo = hoja_borradores.obtener(HUELLA, id_)
    rev = vivo.rev
    vial.guardar_tramos(sesion, _version_id(sesion), _tramos(), usuario=ANA, ahora=LUNES)
    reglas_antes = [r for r in vivo.borrador.reglas_extra if isinstance(r, ReglasViales)]

    _llevar(sesion)

    reglas = [r for r in vivo.borrador.reglas_extra if isinstance(r, ReglasViales)]
    assert len(reglas) == 1 and reglas[0] is not reglas_antes[0]
    assert vivo.rev == rev


# --- regla 5: topes del CSV ---------------------------------------------------------------------

CABECERA = (
    "tramo;progresiva_ini_km;progresiva_fin_km;ancho_m;distancia_planta_km;elemento;tipo;"
    "espesor_m;densidad_t_m3;dosis_l_m2;lineas\n"
)


def test_csv_con_mas_de_2000_tramos_da_el_tope() -> None:
    filas = "".join(f"T{n};{n};{n + 1};7;;capa;fresado;0,05;;;\n" for n in range(2001))
    with pytest.raises(ValueError) as error:
        vial.tramos_desde_csv((CABECERA + filas).encode(), "grande.csv")
    assert str(error.value) == (
        "el archivo 'grande.csv' tiene 2.001 tramos: el máximo es 2.000. Divídalo en varios."
    )


def test_csv_con_2000_tramos_se_lee() -> None:
    filas = "".join(f"T{n};{n};{n + 1};7;;capa;fresado;0,05;;;\n" for n in range(2000))
    assert len(vial.tramos_desde_csv((CABECERA + filas).encode(), "justo.csv")) == 2000


def test_csv_con_demasiadas_capas_en_un_tramo_da_el_tope() -> None:
    filas = "T1;0;1;7;;capa;fresado;0,05;;;\n" + "T1;;;;;capa;fresado;0,05;;;\n" * 50
    with pytest.raises(ValueError) as error:
        vial.tramos_desde_csv((CABECERA + filas).encode(), "capas.csv")
    assert str(error.value) == (
        "el archivo 'capas.csv', tramo T1: tiene 51 capas; el máximo es 50."
    )


def test_csv_con_demasiadas_lineas_de_demarcacion_da_el_tope() -> None:
    filas = "T1;0;1;7;;capa;fresado;0,05;;;\n" + "T1;;;;;demarcacion;continua;;;;1\n" * 21
    with pytest.raises(ValueError) as error:
        vial.tramos_desde_csv((CABECERA + filas).encode(), "lineas.csv")
    assert str(error.value) == (
        "el archivo 'lineas.csv', tramo T1: tiene 21 líneas de demarcación; el máximo es 20."
    )


def test_los_topes_son_los_de_la_api() -> None:
    from api import esquemas_vial

    assert (vial.MAX_TRAMOS, vial.MAX_CAPAS, vial.MAX_LINEAS_DE_DEMARCACION) == (2000, 50, 20)
    assert esquemas_vial.MAX_TRAMOS is vial.MAX_TRAMOS
    assert esquemas_vial.MAX_CAPAS is vial.MAX_CAPAS
    assert esquemas_vial.MAX_LINEAS_DE_DEMARCACION is vial.MAX_LINEAS_DE_DEMARCACION
