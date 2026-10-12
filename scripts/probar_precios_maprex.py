"""Prueba los casos didacticos con precios de referencia publicados (MaPreX jul-2026 y CIV).

Fase C6 del cierre, pista R (C6-plan §5). Mide la sensibilidad de los casos didacticos del
repositorio (NORMAS.md §1: los APU y presupuestos son ejercicios academicos ficticios) a los
listados MaPreX de julio de 2026 y al tabulador CIV, que si son referencias publicadas. No
convierte ningun caso en otra cosa: es una prueba del software con precios de referencia.

Trabaja siempre en un directorio temporal (`tempfile.TemporaryDirectory`): siembra cuatro bases
SQLite nuevas con los sembradores existentes (`scripts.seed.sembrar`,
`scripts.seed_telecom.sembrar_telecom`, `scripts.seed_industrial.sembrar_industrial`,
`scripts.seed_sistemas.sembrar_sistemas`). No tiene opcion `--db` y nunca abre `data/apu.db`.

Que hace, en orden:

1. **Cobertura del listado crudo** `data/precios/maprex_2026-07/lista_maprex_usd.csv` sobre cada
   base, sin confirmar (la transaccion se deshace): filas casadas, desconocidas del flujo 2a de
   UC-02 (`core.catalog.insumos_desconocidos`) y rechazadas del 2b (descripcion conocida con una
   unidad no equivalente).
2. **Civil, presupuesto 001 de la linea base** (`tests.fixtures.presupuesto_auditado.
   items_con_trazas`, con `plan_secuencial`). Deriva en memoria una lista equivalente desde
   `referencia_civil.csv`: la nota «equivalente de '<X>'» casa con
   `data/civil/plantilla_precios.csv` por `core.verification.texto.normalizar_texto` (la
   normalizacion del catalogo), con el mismo tipo y una unidad equivalente
   (`core.contracts.unidades.unidades_equivalentes`). La plantilla no declara unidad para la
   mano de obra, que el APU paga por jornal: casa si MaPreX la cotiza por `dia`. Solo materiales
   y mano de obra; los equipos quedan fuera (ruling C6-9: la columna Precio/Alq. de un equipo
   no es su tarifa diaria) y se contrastan aparte, sin cargarlos: tarifa diaria MaPreX
   (Precio/Alq. x Cop/Depr., la columna Total de `equipos.pdf`) frente a precio x depreciacion
   del APU. Lo que no casa se excluye y se reporta. El precio es la columna `precio_usd`
   (633,3644 Bs/USD al 01/07/2026), que se verifica contra `precio_bs` con la tasa de
   `scripts.derivar_listas_telecom`; vigencia unica 2026-07-09. La lista se escribe en un CSV
   temporal, se carga con `crear_lista_desde_archivo` y revalora el 001 con
   `actualizar_precios(..., plan=plan_secuencial, detectar_atipicos=...)`.
3. **Telecom TC-001 y TC-002** con `data/telecom/fuentes/lista_maprex_2026-07.csv` (la replica de
   la Sesion M1.3, `tests/integration/test_auditoria_arenaza.py`).
4. **Industrial MNT-001 y sistemas SIS-001**: ya se siembran con sus listados MaPreX y CIV, asi que
   revalorarlos con su propia lista debe dar el flujo 3a (ningun insumo afectado): comprobacion de
   la siembra; la version nueva se deshace.

El detector de atipicos es `ml.anomaly.precios_atipicos` si el extra `ml` esta instalado; sin el,
la revaloracion corre sin detector y el informe lo dice. Todo importe es `Decimal`; se redondea
solo al presentar (`core.verification.texto.formatear_decimal`).

Como `scripts/seed.py`, importa `tests.fixtures` a proposito: es la unica copia de la linea base y
del presupuesto auditado (NORMAS.md §2, principio DRY).

Uso:
    uv run --all-extras python scripts/probar_precios_maprex.py
    uv run --all-extras python scripts/probar_precios_maprex.py --salida resultado.md
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from core import models  # noqa: E402
from core.budget import (  # noqa: E402
    CODIGO_ATIPICO,
    Comparativo,
    DetectorAtipicos,
    MarcaAtipica,
    actualizar_precios,
    elaborar,
    guardar_presupuesto,
    plan_secuencial,
)
from core.catalog import (  # noqa: E402
    Catalogo,
    abrir_sesion,
    crear_esquema,
    crear_motor,
    insumos_desconocidos,
)
from core.catalog.precios import (  # noqa: E402
    COLUMNAS_ARCHIVO,
    PrecioLeido,
    cambios_precio,
    crear_lista_desde_archivo,
    leer_lista_precios,
)
from core.contracts import ParametrosCosto  # noqa: E402
from core.contracts.unidades import normalizar_unidad, unidades_equivalentes  # noqa: E402
from core.verification import InformeAuditoria  # noqa: E402
from core.verification.informe import DECIMALES_PRESENTACION  # noqa: E402
from core.verification.texto import formatear_decimal, normalizar_texto  # noqa: E402
from scripts import seed_industrial, seed_sistemas, seed_telecom  # noqa: E402
from scripts.derivar_listas_telecom import (  # noqa: E402
    FECHA_LISTA_MAPREX,
    RUTA_LISTA_MAPREX,
    TASA,
    a_usd,
)
from scripts.lista_maprex_usd import CARPETA, RUTA_SALIDA  # noqa: E402
from scripts.seed import NOMBRE_PROYECTO, sembrar  # noqa: E402
from tests.fixtures import apu_linea_base as linea_base  # noqa: E402
from tests.fixtures import mantenimiento_industrial as mnt  # noqa: E402
from tests.fixtures import tarifas_sistemas as sis  # noqa: E402
from tests.fixtures.presupuesto_auditado import items_con_trazas  # noqa: E402

RUTA_LISTA_CRUDA = RUTA_SALIDA
RUTA_REFERENCIA_CIVIL = CARPETA / "referencia_civil.csv"
RUTA_PLANTILLA_CIVIL = RAIZ / "data" / "civil" / "plantilla_precios.csv"

#: Vigencia unica de la lista civil derivada: la de `materiales.pdf` y `equipos.pdf` (09/07/2026).
#: La mano de obra de MaPreX es del 01/07/2026; la lista lleva una sola fecha (salvedad declarada).
VIGENCIA = FECHA_LISTA_MAPREX
NOMBRE_LISTA_CIVIL = "Referencia MaPreX 2026-07 (civil, derivada)"
CODIGO_CIVIL = "MAPREX-2026-07"
SUFIJO_VERSION = "-MAPREX-2026-07"
NOMBRE_LISTA_TELECOM = "Precios MaPreX 2026-07 (telecom)"

#: La unidad en que MaPreX cotiza jornales y tarifas de equipo; el catalogo no la declara.
UNIDAD_DIA = "dia"
TIPOS_REVALORADOS = ("material", "mano_obra")
TIPO_EQUIPO = "equipo"
ORDEN_TIPOS = ("material", "equipo", "mano_obra")

_EQUIVALENTE = re.compile(r"equivalente de '([^']+)'")
_TRUNCADA = "truncada"
#: El rol MaPreX del Ayudante del tabulador de la construccion (README de `data/precios/...`).
REF_AYUDANTE_N2 = "1-1.2"

MOTIVO_EQUIPO = (
    "equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria "
    "(falta el factor Cop/Depr.), se contrasta aparte"
)
MOTIVO_SIN_EQUIVALENTE = "la nota no nombra ningun insumo de la plantilla civil"
MOTIVO_TIPO = "el tipo MaPreX ({mapreX}) no es el de la plantilla ({plantilla})"
MOTIVO_UNIDAD = "unidad MaPreX {mapreX!r} no equivale a la del catalogo {catalogo!r}"

CIEN = Decimal(100)
DECIMALES_PRECIO = 4

#: El detector de atipicos: la forma de `ml.anomaly.precios_atipicos`.
Detector = Callable[[Mapping[str, Decimal]], Sequence[MarcaAtipica]]


# ---------------------------------------------------------------------------------------------
# Lista civil derivada de referencia_civil.csv
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FilaDerivada:
    """Una fila de la lista civil derivada: el insumo del catalogo con su precio MaPreX."""

    tipo: str
    insumo: str
    unidad: str
    precio: Decimal
    ref_maprex: str
    descripcion_maprex: str
    unidad_maprex: str


@dataclass(frozen=True)
class Exclusion:
    """Una fila de `referencia_civil.csv` que no entra a la lista derivada, y por que."""

    tipo: str
    descripcion_maprex: str
    ref_maprex: str
    equivalente: str
    motivo: str


@dataclass(frozen=True)
class DerivacionCivil:
    filas: tuple[FilaDerivada, ...]
    excluidas: tuple[Exclusion, ...]


def _leer_csv(ruta: Path) -> list[dict[str, str]]:
    with open(ruta, newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def _precio_usd(fila: dict[str, str]) -> Decimal:
    """`precio_usd` del CSV, verificado contra `precio_bs` con la tasa declarada."""
    precio = Decimal(fila["precio_usd"])
    if a_usd(Decimal(fila["precio_bs"])) != precio:
        raise ValueError(
            f"{RUTA_REFERENCIA_CIVIL.name}: la tasa {TASA} no reproduce el precio_usd de "
            f"{fila['ref_maprex']} ({precio})"
        )
    return precio


def _unidad_casa(unidad_catalogo: str, unidad_maprex: str) -> bool:
    """Misma unidad tras normalizar; sin unidad en el catalogo (jornal), MaPreX debe dar `dia`."""
    if unidad_catalogo:
        return unidades_equivalentes(unidad_catalogo, unidad_maprex)
    return normalizar_unidad(unidad_maprex) == UNIDAD_DIA


def derivar_lista_civil(
    referencia: Path = RUTA_REFERENCIA_CIVIL, plantilla: Path = RUTA_PLANTILLA_CIVIL
) -> DerivacionCivil:
    """La lista equivalente de la linea base: materiales y mano de obra que casan, en el orden de
    `referencia`; las demas filas se excluyen con su motivo."""
    catalogo = {normalizar_texto(fila["insumo"]): fila for fila in _leer_csv(plantilla)}
    filas: list[FilaDerivada] = []
    excluidas: list[Exclusion] = []
    for fila in _leer_csv(referencia):
        nota = _EQUIVALENTE.search(fila["notas"])
        equivalente = nota.group(1) if nota else ""
        destino = catalogo.get(normalizar_texto(equivalente)) if equivalente else None

        def excluir(motivo: str, fila: dict[str, str] = fila, equivalente: str = equivalente):
            excluidas.append(
                Exclusion(fila["tipo"], fila["insumo"], fila["ref_maprex"], equivalente, motivo)
            )

        if fila["tipo"] == TIPO_EQUIPO:
            excluir(MOTIVO_EQUIPO)
        elif destino is None:
            excluir(MOTIVO_SIN_EQUIVALENTE)
        elif destino["tipo"] != fila["tipo"]:
            excluir(MOTIVO_TIPO.format(mapreX=fila["tipo"], plantilla=destino["tipo"]))
        elif not _unidad_casa(destino["unidad"], fila["unidad"]):
            excluir(MOTIVO_UNIDAD.format(mapreX=fila["unidad"], catalogo=destino["unidad"]))
        else:
            filas.append(
                FilaDerivada(
                    tipo=destino["tipo"],
                    insumo=destino["insumo"],
                    unidad=destino["unidad"],
                    precio=_precio_usd(fila),
                    ref_maprex=fila["ref_maprex"],
                    descripcion_maprex=fila["insumo"],
                    unidad_maprex=fila["unidad"],
                )
            )
    return DerivacionCivil(tuple(filas), tuple(excluidas))


def escribir_lista(filas: Sequence[FilaDerivada], ruta: Path) -> Path:
    """Escribe las filas en el formato canonico de UC-02 (`COLUMNAS_ARCHIVO`); el precio, como
    texto del `Decimal`."""
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS_ARCHIVO)
        for fila in filas:
            escritor.writerow((fila.tipo, fila.insumo, fila.unidad, f"{fila.precio:f}"))
    return ruta


# ---------------------------------------------------------------------------------------------
# Contraste de equipos (no se cargan)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ContrasteEquipo:
    """Un equipo de la linea base (descripcion, precio y depreciacion del APU) frente a MaPreX."""

    equipo: str
    partidas: tuple[str, ...]
    precio_apu: Decimal
    depreciacion_apu: Decimal
    ref_maprex: str
    precio_alq_maprex: Decimal
    factor_maprex: Decimal

    @property
    def tarifa_apu(self) -> Decimal:
        return self.precio_apu * self.depreciacion_apu

    @property
    def tarifa_maprex(self) -> Decimal:
        return self.precio_alq_maprex * self.factor_maprex


def bono_ayudante_maprex(referencia: Path = RUTA_REFERENCIA_CIVIL) -> Decimal:
    """El bono de alimentacion diario del Ayudante N2 de MaPreX, en USD, desde su `bono_bs`."""
    (fila,) = [f for f in _leer_csv(referencia) if f["ref_maprex"] == REF_AYUDANTE_N2]
    return a_usd(Decimal(fila["bono_bs"]))


def contrastar_equipos(referencia: Path = RUTA_REFERENCIA_CIVIL) -> tuple[ContrasteEquipo, ...]:
    """Cada (equipo, precio, depreciacion) distinto de los cinco APU frente a su fila MaPreX."""
    maprex: dict[str, dict[str, str]] = {}
    for fila in _leer_csv(referencia):
        nota = _EQUIVALENTE.search(fila["notas"])
        if fila["tipo"] == TIPO_EQUIPO and nota:
            maprex[normalizar_texto(nota.group(1))] = fila
    usos: dict[tuple[str, Decimal, Decimal], list[str]] = {}
    for apu in linea_base.APUS_LINEA_BASE:
        for equipo in apu.equipos:
            clave = (equipo.descripcion, equipo.precio, equipo.depreciacion)
            usos.setdefault(clave, []).append(apu.codigo_partida)
    contrastes = []
    for (descripcion, precio, depreciacion), partidas in usos.items():
        fila = maprex.get(normalizar_texto(descripcion))
        if fila is None:
            continue
        contrastes.append(
            ContrasteEquipo(
                equipo=descripcion,
                partidas=tuple(partidas),
                precio_apu=precio,
                depreciacion_apu=depreciacion,
                ref_maprex=fila["ref_maprex"],
                precio_alq_maprex=_precio_usd(fila),
                factor_maprex=Decimal(fila["factor_depreciacion"]),
            )
        )
    return tuple(contrastes)


# ---------------------------------------------------------------------------------------------
# Bases temporales
# ---------------------------------------------------------------------------------------------


@contextmanager
def _base(ruta: Path) -> Iterator[Session]:
    """Una base SQLite nueva en `ruta` con el esquema creado; se cierra al salir."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            yield sesion
    finally:
        motor.dispose()


def _sembrar_civil(sesion: Session) -> models.Proyecto:
    return sembrar(sesion)


BASES: dict[str, Callable[[Session], models.Proyecto]] = {
    "civil": _sembrar_civil,
    "telecom": seed_telecom.sembrar_telecom,
    "industrial": seed_industrial.sembrar_industrial,
    "sistemas": seed_sistemas.sembrar_sistemas,
}


# ---------------------------------------------------------------------------------------------
# 1. Cobertura del listado crudo
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Cobertura:
    """Cuanto del listado crudo reconoce una base: casados, desconocidos (2a), rechazados (2b)."""

    base: str
    filas: int
    casados: int
    desconocidos: tuple[PrecioLeido, ...]
    rechazados: tuple[PrecioLeido, ...]


def medir_cobertura(sesion: Session, base: str, ruta: Path = RUTA_LISTA_CRUDA) -> Cobertura:
    """Carga el listado sin confirmar y deshace la transaccion."""
    leidos = leer_lista_precios(ruta)
    previa = insumos_desconocidos(sesion, ruta)
    resumen = crear_lista_desde_archivo(
        sesion, ruta, nombre="cobertura (sin confirmar)", moneda="USD", fecha_vigencia=VIGENCIA
    )
    sesion.rollback()
    rechazados = tuple(leido for leido in resumen.desconocidos if leido not in previa)
    return Cobertura(
        base=base,
        filas=len(leidos),
        casados=len(leidos) - len(resumen.desconocidos),
        desconocidos=previa,
        rechazados=rechazados,
    )


# ---------------------------------------------------------------------------------------------
# Revaloracion
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class MarcaRegistrada:
    """Una marca del detector, con el cambio de precio que marca."""

    insumo: str
    precio_anterior: Decimal
    precio_nuevo: Decimal
    variacion: Decimal
    puntaje: float
    de_esta_lista: bool


class _DetectorRegistrado:
    """Envuelve el detector para guardar lo que recibe y lo que marca."""

    def __init__(self, detector: Detector) -> None:
        self.detector = detector
        self.recibidas = 0
        self.marcas: list[MarcaAtipica] = []

    def __call__(self, variaciones: Mapping[str, Decimal]) -> list[MarcaAtipica]:
        self.recibidas = len(variaciones)
        self.marcas = list(self.detector(variaciones))
        return self.marcas


@dataclass(frozen=True, eq=False)
class Revaloracion:
    """Un presupuesto revalorado con una lista de referencia."""

    caso: str
    codigo_nuevo: str
    lista: str
    filas_lista: int
    desconocidos: tuple[PrecioLeido, ...]
    comparativo: Comparativo
    informe_anterior: InformeAuditoria
    informe_nuevo: InformeAuditoria
    variaciones_historico: int
    detector: bool
    marcas: tuple[MarcaRegistrada, ...] = ()
    insumos_presupuesto: Mapping[str, int] = field(default_factory=dict)
    insumos_revalorados: Mapping[str, int] = field(default_factory=dict)
    incidencias: int = 0

    @property
    def atipicos_en_informe(self) -> int:
        return sum(1 for h in self.informe_nuevo.hallazgos if h.regla == CODIGO_ATIPICO)


def _guardar_base(
    sesion: Session,
    proyecto: models.Proyecto,
    items,
    composiciones,
    parametros: ParametrosCosto,
    codigo: str,
    fecha: date,
    moneda: str,
    lista: models.ListaPrecios,
    plan=None,
) -> InformeAuditoria:
    resultado = elaborar(
        items, composiciones, parametros, codigo=codigo, fecha=fecha, moneda=moneda, plan=plan
    )
    guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=lista,
        parametros=parametros,
        pendientes=resultado.pendientes,
        usuario="script:probar_precios_maprex",
    )
    sesion.commit()
    return resultado.informe


def _insumos_por_tipo(
    sesion: Session, codigos: Sequence[str], solo: set[int] | None = None
) -> dict[str, int]:
    """Insumos distintos de los APU de `codigos`, por tipo (opcionalmente, solo los de `solo`)."""
    filas = sesion.execute(
        select(models.Insumo.id, models.Insumo.tipo)
        .join(models.ComposicionAPU, models.ComposicionAPU.insumo_id == models.Insumo.id)
        .join(models.Partida, models.Partida.id == models.ComposicionAPU.partida_id)
        .where(models.Partida.codigo.in_(codigos))
        .distinct()
    ).all()
    conteo = dict.fromkeys(ORDEN_TIPOS, 0)
    for insumo_id, tipo in filas:
        if solo is None or insumo_id in solo:
            conteo[str(tipo)] = conteo.get(str(tipo), 0) + 1
    return conteo


def _cargar_lista(
    sesion: Session, ruta: Path, nombre: str, moneda: str, vigencia: date
) -> tuple[models.ListaPrecios, tuple[PrecioLeido, ...]]:
    resumen = crear_lista_desde_archivo(
        sesion, ruta, nombre=nombre, moneda=moneda, fecha_vigencia=vigencia, origen=ruta.name
    )
    return resumen.lista, resumen.desconocidos


def _incidencias(sesion: Session, codigos: Sequence[str], cambios: set[int]) -> int:
    """Cuantas `IncidenciaCambio` de los cambios `cambios` citan partidas de `codigos`."""
    return len(
        sesion.execute(
            select(models.IncidenciaCambio.id)
            .join(models.Partida, models.Partida.id == models.IncidenciaCambio.partida_id)
            .where(
                models.Partida.codigo.in_(codigos),
                models.IncidenciaCambio.cambio_id.in_(cambios),
            )
        ).all()
    )


def _revalorar(
    sesion: Session,
    caso: str,
    proyecto: str,
    codigo: str,
    codigo_nuevo: str,
    lista: models.ListaPrecios,
    ruta_lista: Path,
    desconocidos: tuple[PrecioLeido, ...],
    informe_anterior: InformeAuditoria,
    detectar_atipicos: Detector | None,
    plan=None,
) -> Revaloracion:
    """`actualizar_precios` con el detector envuelto, y lo que el informe necesita contar."""
    registrado = _DetectorRegistrado(detectar_atipicos) if detectar_atipicos else None
    detector: DetectorAtipicos | None = registrado
    nuevo, comparativo = actualizar_precios(
        sesion, proyecto, codigo, lista, codigo_nuevo, plan=plan, detectar_atipicos=detector,
        usuario="script:probar_precios_maprex",
    )
    historico = cambios_precio(sesion)
    de_esta = {cambio.id for cambio in historico if cambio.lista_nueva_id == lista.id}
    por_id = {str(cambio.id): cambio for cambio in historico}
    marcas = tuple(
        MarcaRegistrada(
            insumo=por_id[marca.id].insumo.descripcion,
            precio_anterior=por_id[marca.id].precio_anterior,
            precio_nuevo=por_id[marca.id].precio_nuevo,
            variacion=por_id[marca.id].variacion,
            puntaje=marca.puntaje,
            de_esta_lista=int(marca.id) in de_esta,
        )
        for marca in (registrado.marcas if registrado else ())
    )
    codigos = list(dict.fromkeys(p.item.codigo_partida for p in nuevo.presupuesto.partidas))
    revalorados = {cambio.insumo_id for cambio in historico if cambio.id in de_esta}
    return Revaloracion(
        caso=caso,
        codigo_nuevo=nuevo.presupuesto.codigo,
        lista=ruta_lista.name,
        filas_lista=len(leer_lista_precios(ruta_lista)),
        desconocidos=desconocidos,
        comparativo=comparativo,
        informe_anterior=informe_anterior,
        informe_nuevo=nuevo.informe,
        variaciones_historico=len(historico),
        detector=registrado is not None,
        marcas=marcas,
        insumos_presupuesto=_insumos_por_tipo(sesion, codigos),
        insumos_revalorados=_insumos_por_tipo(sesion, codigos, revalorados),
        incidencias=_incidencias(sesion, codigos, de_esta),
    )


def revalorar_civil(
    sesion: Session,
    derivacion: DerivacionCivil,
    carpeta: Path,
    detectar_atipicos: Detector | None,
) -> Revaloracion:
    """El presupuesto 001 de la linea base, revalorado con la lista civil derivada."""
    proyecto = sembrar(sesion)
    catalogo = Catalogo(sesion)
    items = items_con_trazas()
    composiciones = catalogo.composiciones(
        dict.fromkeys(item.codigo_partida for item in items), fecha=linea_base.FECHA_LINEA_BASE
    )
    informe = _guardar_base(
        sesion,
        proyecto,
        items,
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        linea_base.CODIGO_PRESUPUESTO,
        linea_base.FECHA_LINEA_BASE,
        linea_base.MONEDA,
        catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
        plan=plan_secuencial,
    )
    ruta = escribir_lista(derivacion.filas, carpeta / "lista_civil_maprex_derivada.csv")
    lista, desconocidos = _cargar_lista(
        sesion, ruta, NOMBRE_LISTA_CIVIL, linea_base.MONEDA, VIGENCIA
    )
    revaloracion = _revalorar(
        sesion,
        f"civil {linea_base.CODIGO_PRESUPUESTO}",
        NOMBRE_PROYECTO,
        linea_base.CODIGO_PRESUPUESTO,
        CODIGO_CIVIL,
        lista,
        ruta,
        desconocidos,
        informe,
        detectar_atipicos,
        plan=plan_secuencial,
    )
    sesion.commit()
    return revaloracion


def revalorar_telecom(sesion: Session, detectar_atipicos: Detector | None) -> list[Revaloracion]:
    """TC-001 y TC-002 guardados con la lista ARENAZA y revalorados con la MaPreX telecom, que se
    carga una sola vez (los dos presupuestos son del mismo proyecto)."""
    proyecto = seed_telecom.sembrar_telecom(sesion)
    anterior = seed_telecom.lista_arenaza(sesion)
    informes = {
        codigo: _guardar_base(
            sesion,
            proyecto,
            seed_telecom.items_arenaza(numero),
            seed_telecom.composiciones_desde_catalogo(sesion, numero),
            seed_telecom.PARAMETROS_ARENAZA,
            codigo,
            seed_telecom.FECHA_ARENAZA,
            seed_telecom.MONEDA,
            anterior,
        )
        for numero, codigo in seed_telecom.CODIGOS_PRESUPUESTO.items()
    }
    lista, desconocidos = _cargar_lista(
        sesion, RUTA_LISTA_MAPREX, NOMBRE_LISTA_TELECOM, seed_telecom.MONEDA, FECHA_LISTA_MAPREX
    )
    revaloraciones = [
        _revalorar(
            sesion,
            f"telecom {codigo}",
            seed_telecom.NOMBRE_PROYECTO,
            codigo,
            f"{codigo}{SUFIJO_VERSION}",
            lista,
            RUTA_LISTA_MAPREX,
            desconocidos,
            informe,
            detectar_atipicos,
        )
        for codigo, informe in informes.items()
    ]
    sesion.commit()
    return revaloraciones


# ---------------------------------------------------------------------------------------------
# Industrial y sistemas: comprobacion de la siembra (flujo 3a)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Comprobacion:
    """Revalorar un caso con su propia lista: debe dar el flujo 3a (ningun insumo afectado)."""

    caso: str
    lista: str
    filas: int
    desconocidos: int
    insumos_afectados: int
    total_anterior: Decimal
    total_nuevo: Decimal

    @property
    def flujo_3a(self) -> bool:
        return self.insumos_afectados == 0 and self.total_nuevo == self.total_anterior


def comprobar_siembra(
    sesion: Session,
    sembrador: Callable[[Session], models.Proyecto],
    items,
    composiciones: Callable[[Session], Mapping],
    lista_sembrada: Callable[[Session], models.ListaPrecios],
    parametros: ParametrosCosto,
    codigo: str,
    fecha: date,
    moneda: str,
    ruta_lista: Path,
) -> Comprobacion:
    proyecto = sembrador(sesion)
    _guardar_base(
        sesion,
        proyecto,
        items,
        composiciones(sesion),
        parametros,
        codigo,
        fecha,
        moneda,
        lista_sembrada(sesion),
    )
    resumen = crear_lista_desde_archivo(
        sesion,
        ruta_lista,
        nombre=f"{ruta_lista.name} (comprobacion)",
        moneda=moneda,
        fecha_vigencia=fecha,
        origen=ruta_lista.name,
    )
    _, comparativo = actualizar_precios(
        sesion, proyecto.nombre, codigo, resumen.lista, f"{codigo}{SUFIJO_VERSION}",
        usuario="script:probar_precios_maprex",
    )
    sesion.rollback()  # flujo 3a: no hay nada que guardar
    return Comprobacion(
        caso=codigo,
        lista=ruta_lista.name,
        filas=len(leer_lista_precios(ruta_lista)),
        desconocidos=len(resumen.desconocidos),
        insumos_afectados=comparativo.insumos_afectados,
        total_anterior=comparativo.total_anterior,
        total_nuevo=comparativo.total_nuevo,
    )


# ---------------------------------------------------------------------------------------------
# La prueba completa
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, eq=False)
class Resultado:
    coberturas: tuple[Cobertura, ...]
    derivacion: DerivacionCivil
    civil: Revaloracion
    telecom: tuple[Revaloracion, ...]
    comprobaciones: tuple[Comprobacion, ...]
    equipos: tuple[ContrasteEquipo, ...]
    detector: bool


def probar(carpeta: Path, detectar_atipicos: Detector | None = None) -> Resultado:
    """Corre la prueba completa con las bases en `carpeta` (el script le pasa un temporal)."""
    coberturas = []
    for base, sembrador in BASES.items():
        with _base(carpeta / f"cobertura_{base}.db") as sesion:
            sembrador(sesion)
            coberturas.append(medir_cobertura(sesion, base))

    derivacion = derivar_lista_civil()
    with _base(carpeta / "civil.db") as sesion:
        civil = revalorar_civil(sesion, derivacion, carpeta, detectar_atipicos)
    with _base(carpeta / "telecom.db") as sesion:
        telecom = revalorar_telecom(sesion, detectar_atipicos)
    with _base(carpeta / "industrial.db") as sesion:
        industrial = comprobar_siembra(
            sesion,
            seed_industrial.sembrar_industrial,
            seed_industrial.items_industrial(),
            seed_industrial.composiciones_desde_catalogo,
            seed_industrial.lista_industrial,
            mnt.PARAMETROS_INDUSTRIAL,
            seed_industrial.CODIGO_PRESUPUESTO,
            mnt.FECHA_REFERENCIA,
            mnt.MONEDA,
            seed_industrial.RUTA_LISTA_CANONICA,
        )
    with _base(carpeta / "sistemas.db") as sesion:
        sistemas = comprobar_siembra(
            sesion,
            seed_sistemas.sembrar_sistemas,
            seed_sistemas.items_sistemas(),
            seed_sistemas.composiciones_desde_catalogo,
            seed_sistemas.lista_sistemas,
            sis.PARAMETROS_SISTEMAS,
            seed_sistemas.CODIGO_PRESUPUESTO,
            sis.FECHA_TABULADOR,
            sis.MONEDA,
            seed_sistemas.RUTA_LISTA_CANONICA,
        )
    return Resultado(
        coberturas=tuple(coberturas),
        derivacion=derivacion,
        civil=civil,
        telecom=tuple(telecom),
        comprobaciones=(industrial, sistemas),
        equipos=contrastar_equipos(),
        detector=detectar_atipicos is not None,
    )


# ---------------------------------------------------------------------------------------------
# Informe en markdown
# ---------------------------------------------------------------------------------------------


def _m(valor: Decimal) -> str:
    return formatear_decimal(valor, DECIMALES_PRESENTACION)


def _p(valor: Decimal) -> str:
    return formatear_decimal(valor, DECIMALES_PRECIO)


def _pct(valor: Decimal) -> str:
    texto = formatear_decimal(valor, DECIMALES_PRESENTACION)
    return texto if texto.startswith("-") else f"+{texto}"


def _tabla(encabezados: Sequence[str], filas: Sequence[Sequence[object]]) -> list[str]:
    lineas = [
        "| " + " | ".join(encabezados) + " |",
        "|" + "|".join("---" for _ in encabezados) + "|",
    ]
    lineas += ["| " + " | ".join(str(celda) for celda in fila) + " |" for fila in filas]
    return lineas


def _seccion_cobertura(resultado: Resultado) -> list[str]:
    lineas = [
        "## 1. Cobertura del listado crudo `lista_maprex_usd.csv`",
        "",
        "Carga sin confirmar sobre cada base sembrada (la transaccion se deshace).",
        "",
    ]
    lineas += _tabla(
        ("Base", "Filas del archivo", "Casadas", "Desconocidas (2a)", "Rechazadas (2b)"),
        [
            (c.base, c.filas, c.casados, len(c.desconocidos), len(c.rechazados))
            for c in resultado.coberturas
        ],
    )
    rechazos = [
        f"- {c.base}: "
        + ", ".join(f"{r.tipo.value} {r.descripcion!r} ({r.unidad})" for r in c.rechazados)
        for c in resultado.coberturas
        if c.rechazados
    ]
    if rechazos:
        lineas += ["", "Rechazadas por unidad no equivalente (flujo 2b):", "", *rechazos]
    return lineas


def _seccion_derivacion(derivacion: DerivacionCivil) -> list[str]:
    lineas = [
        "### Lista civil derivada de `referencia_civil.csv`",
        "",
        f"{len(derivacion.filas)} filas casadas (materiales y mano de obra); "
        f"{len(derivacion.excluidas)} excluidas.",
        "",
    ]
    lineas += _tabla(
        ("Tipo", "Insumo del catalogo", "Unidad", "USD", "Ref MaPreX", "Descripcion MaPreX"),
        [
            (
                f.tipo,
                f.insumo,
                f.unidad or "(jornal)",
                _p(f.precio),
                f.ref_maprex,
                f.descripcion_maprex,
            )
            for f in derivacion.filas
        ],
    )
    lineas += ["", "Excluidas:", ""]
    lineas += _tabla(
        ("Tipo", "Descripcion MaPreX", "Ref", "Equivalente de", "Motivo"),
        [
            (e.tipo, e.descripcion_maprex, e.ref_maprex, e.equivalente, e.motivo)
            for e in derivacion.excluidas
        ],
    )
    return lineas


def _seccion_insumos(revaloracion: Revaloracion) -> list[str]:
    lineas = ["#### Cobertura de insumos del presupuesto", ""]
    lineas += _tabla(
        ("Tipo", "Insumos en los APU", "Con precio nuevo", "Sin revalorar"),
        [
            (
                tipo,
                revaloracion.insumos_presupuesto.get(tipo, 0),
                revaloracion.insumos_revalorados.get(tipo, 0),
                revaloracion.insumos_presupuesto.get(tipo, 0)
                - revaloracion.insumos_revalorados.get(tipo, 0),
            )
            for tipo in ORDEN_TIPOS
        ],
    )
    return lineas


def _seccion_comparativo(revaloracion: Revaloracion, solo_cambios: bool = False) -> list[str]:
    comparativo = revaloracion.comparativo
    filas = [
        (
            fila.codigo_partida,
            fila.descripcion,
            _m(fila.pu_anterior),
            _m(fila.pu_nuevo),
            _pct(fila.variacion_pct),
            _pct(fila.incidencia_pct),
        )
        for fila in comparativo.tabla.itertuples(index=False)
        if not solo_cambios or fila.pu_nuevo != fila.pu_anterior
    ]
    filas.append(
        (
            "**Total**",
            "",
            _m(comparativo.total_anterior),
            _m(comparativo.total_nuevo),
            _pct(comparativo.variacion_pct),
            _pct(comparativo.variacion_pct),
        )
    )
    titulo = "#### Comparativo por partida"
    if solo_cambios:
        titulo += f" (solo las que cambian, de {len(comparativo.tabla)} renglones)"
    lineas = [titulo, ""]
    lineas += _tabla(
        ("Partida", "Descripcion", "PU anterior", "PU nuevo", "Variacion %", "Incidencia %"),
        filas,
    )
    lineas += [
        "",
        f"Insumos con precio cambiado por la lista: {comparativo.insumos_afectados}. "
        f"`IncidenciaCambio` registradas para las partidas de este presupuesto: "
        f"{revaloracion.incidencias}.",
    ]
    return lineas


def _severidades(hallazgos: Sequence) -> str:
    """`2 ERROR, 1 INFO`: cuantos hallazgos de cada severidad, o `-` si no hay."""
    conteo: dict[str, int] = {}
    for hallazgo in hallazgos:
        conteo[hallazgo.severidad.name] = conteo.get(hallazgo.severidad.name, 0) + 1
    return ", ".join(f"{n} {severidad}" for severidad, n in conteo.items()) or "-"


def _seccion_hallazgos(revaloracion: Revaloracion) -> list[str]:
    """Las siete reglas evaluadas, y los codigos que no son regla (ATIPICO, PENDIENTE)."""
    antes = revaloracion.informe_anterior.por_regla()
    despues = revaloracion.informe_nuevo.por_regla()
    filas = [(codigo, nombre) for codigo, nombre in revaloracion.informe_nuevo.reglas_evaluadas]
    evaluadas = {codigo for codigo, _ in filas}
    filas += [
        (codigo, "(no es regla)") for codigo in sorted((set(antes) | set(despues)) - evaluadas)
    ]
    lineas = ["#### Hallazgos por regla", ""]
    lineas += _tabla(
        ("Regla", "Nombre", "Antes", "Despues", "Severidades despues"),
        [
            (
                codigo,
                nombre,
                len(antes.get(codigo, ())),
                len(despues.get(codigo, ())),
                _severidades(despues.get(codigo, ())),
            )
            for codigo, nombre in filas
        ],
    )
    lineas += [
        "",
        f"Antes: {'CUMPLE' if revaloracion.informe_anterior.cumple else 'NO CUMPLE'}; "
        f"despues: {'CUMPLE' if revaloracion.informe_nuevo.cumple else 'NO CUMPLE'}.",
    ]
    return lineas


def _minimo_observaciones() -> int | None:
    """El minimo de variaciones del detector de `ml` (sin el extra, no se sabe: `None`)."""
    try:
        from ml.anomaly import MINIMO_OBSERVACIONES
    except ImportError:
        return None
    return MINIMO_OBSERVACIONES


def _seccion_atipicos(revaloracion: Revaloracion) -> list[str]:
    lineas = ["#### Atipicos", ""]
    if not revaloracion.detector:
        lineas.append(
            "Sin detector: el extra `ml` no esta instalado, la revaloracion corrio con "
            "`detectar_atipicos=None` y el informe no puede traer hallazgos ATIPICO."
        )
        return lineas
    lineas.append(
        f"Variaciones en el historico al revalorar: {revaloracion.variaciones_historico}."
    )
    minimo = _minimo_observaciones()
    if minimo is not None and revaloracion.variaciones_historico < minimo:
        lineas.append(
            f"Con menos de {minimo} variaciones el detector no marca nada "
            "(`ml.anomaly.MINIMO_OBSERVACIONES`): no hay comportamiento observado que contrastar."
        )
    elif revaloracion.marcas:
        lineas += [""]
        lineas += _tabla(
            (
                "Insumo",
                "Precio anterior",
                "Precio nuevo",
                "Variacion %",
                "Puntaje",
                "Cambio de esta lista",
            ),
            [
                (
                    m.insumo,
                    _p(m.precio_anterior),
                    _p(m.precio_nuevo),
                    _pct(m.variacion * CIEN),
                    f"{m.puntaje:.3f}",
                    "si" if m.de_esta_lista else "no",
                )
                for m in revaloracion.marcas
            ],
        )
    else:
        lineas.append("El detector no marco ninguna variacion.")
    lineas += ["", f"Hallazgos ATIPICO en el informe nuevo: {revaloracion.atipicos_en_informe}."]
    return lineas


def _seccion_equipos(contrastes: Sequence[ContrasteEquipo]) -> list[str]:
    lineas = [
        "### Contraste de equipos (no se cargan; ruling C6-9)",
        "",
        "Tarifa diaria del APU = precio x depreciacion; tarifa diaria MaPreX = Precio/Alq. x "
        "Cop/Depr. (la columna Total de `equipos.pdf`).",
        "",
    ]
    lineas += _tabla(
        (
            "Equipo",
            "Partidas",
            "Precio APU",
            "Depr. APU",
            "Tarifa APU",
            "Ref",
            "Precio/Alq. MaPreX",
            "Factor MaPreX",
            "Tarifa MaPreX",
            "MaPreX / APU",
        ),
        [
            (
                c.equipo,
                ", ".join(c.partidas),
                _m(c.precio_apu),
                formatear_decimal(c.depreciacion_apu),
                _p(c.tarifa_apu),
                c.ref_maprex,
                _m(c.precio_alq_maprex),
                formatear_decimal(c.factor_maprex),
                _p(c.tarifa_maprex),
                formatear_decimal(c.tarifa_maprex / c.tarifa_apu, DECIMALES_PRESENTACION)
                if c.tarifa_apu
                else "-",
            )
            for c in contrastes
        ],
    )
    return lineas


def _seccion_revaloracion(revaloracion: Revaloracion, solo_cambios: bool = False) -> list[str]:
    lineas = [
        f"### {revaloracion.caso} -> {revaloracion.codigo_nuevo}",
        "",
        f"Lista `{revaloracion.lista}`: {revaloracion.filas_lista} filas; desconocidas al "
        f"cargarla: {len(revaloracion.desconocidos)}.",
        "",
    ]
    for parte in (
        _seccion_insumos(revaloracion),
        _seccion_comparativo(revaloracion, solo_cambios),
        _seccion_hallazgos(revaloracion),
        _seccion_atipicos(revaloracion),
    ):
        lineas += [*parte, ""]
    return lineas


def _truncadas() -> dict[str, list[str]]:
    """Las Ref de cada `referencia_*.csv` cuya nota declara la descripcion truncada en el PDF."""
    truncadas: dict[str, list[str]] = {}
    for ruta in sorted(CARPETA.glob("referencia_*.csv")):
        refs = [fila["ref_maprex"] for fila in _leer_csv(ruta) if _TRUNCADA in fila["notas"]]
        if refs:
            truncadas[ruta.name] = refs
    return truncadas


def _seccion_salvedades(resultado: Resultado) -> list[str]:
    truncadas = _truncadas()
    bono = linea_base.PARAMETROS_LINEA_BASE.bono_alimentacion
    return [
        "## 5. Salvedades",
        "",
        "- Los casos son didacticos (NORMAS.md §1): esto mide su sensibilidad a precios de "
        "referencia publicados, no el costo de ninguna obra.",
        f"- El bono de alimentacion no se revalora: es un parametro de costo "
        f"(`ParametrosCosto.bono_alimentacion` = {_m(bono)} USD por obrero y dia), no un precio "
        f"de la lista; MaPreX trae {_p(bono_ayudante_maprex())} USD/dia para el Ayudante N2 "
        f"(Ref {REF_AYUDANTE_N2}, bono_bs de `referencia_civil.csv` a la tasa {TASA}), que solo "
        "entraria como escenario (UC-08).",
        "- Vigencia unica 2026-07-09 para la lista civil derivada, aunque la mano de obra de "
        "MaPreX es del 01/07/2026.",
        f"- Tasa 633,3644 Bs/USD al 01/07/2026; cada `precio_usd` de `referencia_civil.csv` que "
        f"se usa se verifico contra su `precio_bs` con la tasa {TASA}.",
        "- No se convierte ninguna unidad: una fila cuya unidad MaPreX no equivale a la del "
        "catalogo se excluye y se reporta (`sco` no es alias de `saco` en "
        "`core.contracts.unidades`).",
        "- Los equipos no se revaloran (C6-9): su Precio/Alq. MaPreX no es una tarifa diaria "
        "sin el factor Cop/Depr.; se contrastan aparte.",
        f"- Descripciones truncadas por el propio PDF de MaPreX "
        f"({sum(len(refs) for refs in truncadas.values())}), conservadas tal cual: "
        + (
            "; ".join(f"{archivo}: {', '.join(refs)}" for archivo, refs in truncadas.items())
            if truncadas
            else "ninguna"
        )
        + ". Una lista que las cite casa solo con un catalogo sembrado con la misma grafia.",
    ]


def informe_markdown(resultado: Resultado) -> str:
    """Las tablas del resultado en markdown; montos redondeados solo aqui."""
    lineas = [
        "# Prueba con precios de referencia publicados (MaPreX jul-2026 y tabulador CIV)",
        "",
        f"Tasa {TASA} Bs/USD (01/07/2026). Vigencia de la lista civil derivada y de la telecom: "
        f"{VIGENCIA.isoformat()}. Detector de atipicos: "
        + ("`ml.anomaly.precios_atipicos`." if resultado.detector else "ninguno (sin extra `ml`)."),
        "",
        *_seccion_cobertura(resultado),
        "",
        "## 2. Civil: presupuesto 001 de la linea base",
        "",
        *_seccion_derivacion(resultado.derivacion),
        "",
        *_seccion_revaloracion(resultado.civil),
        *_seccion_equipos(resultado.equipos),
        "",
        "## 3. Telecom: TC-001 y TC-002 (ARENAZA) con la lista MaPreX telecom",
        "",
    ]
    for revaloracion in resultado.telecom:
        lineas += _seccion_revaloracion(revaloracion, solo_cambios=True)
    lineas += [
        "## 4. Industrial y sistemas: comprobacion de la siembra",
        "",
    ]
    lineas += _tabla(
        (
            "Caso",
            "Lista",
            "Filas",
            "Desconocidas",
            "Insumos afectados",
            "Total anterior",
            "Total nuevo",
            "Flujo 3a",
        ),
        [
            (
                c.caso,
                c.lista,
                c.filas,
                c.desconocidos,
                c.insumos_afectados,
                _m(c.total_anterior),
                _m(c.total_nuevo),
                "si" if c.flujo_3a else "NO",
            )
            for c in resultado.comprobaciones
        ],
    )
    lineas += ["", *_seccion_salvedades(resultado), ""]
    return "\n".join(lineas)


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------


def _detector_ml() -> Detector | None:
    try:
        from ml.anomaly import precios_atipicos
    except ImportError:
        return None
    return precios_atipicos


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--salida", type=Path, default=None, help="escribe tambien las tablas en este .md"
    )
    argumentos = analizador.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="probar_maprex_") as temporal:
        resultado = probar(Path(temporal), _detector_ml())
    texto = informe_markdown(resultado)
    # En Windows, stdout redirigido usa la pagina de codigos local: las tablas son UTF-8.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(texto)
    if argumentos.salida is not None:
        argumentos.salida.write_text(texto, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
