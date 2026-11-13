"""UC-17 4-5 sin Streamlit: la referencia MaPreX en Bs, la lista de una empresa y sus hallazgos de
R11 y R12 a una fecha de evaluacion (spec S1 §6). La pantalla `ui/paginas/precios_empresa.py` y la
ruta `api/rutas/precios_empresa.py` solo presentan. Cada accion que escribe confirma o deshace su
transaccion entera. Sin Streamlit, sin pandas y sin `ui.caso` (lo vigila
`tests/unit/test_arquitectura_s1.py`).

RM-1: vive en `aplicacion/` y `ui/precios_empresa.py` lo reexporta. La capa de aplicacion no
importa `scripts`, asi que los datos de la referencia MaPreX en Bs (tasa, fecha, fuente y el CSV)
se repiten aqui; `tests/unit/test_aplicacion_precios_empresa.py` los ata a los de
`scripts/lista_maprex_bs.py`.

2026-11-13 (prueba de punta a punta, D-8 y D-11): `revisar_archivo` dice, sin escribir, que filas
reconoce el catalogo, cuales son insumos nuevos y cuales traen una descripcion conocida con otra
unidad; `crear_lista(..., dar_de_alta=True)` da de alta los nuevos (la confirmacion de la persona)
con `Catalogo.dar_de_alta_insumo` y su precio entra a la lista. Los de otra unidad no se dan de
alta (serian un homonimo con otra unidad) y se dice la del catalogo. Una fila sin fecha o sin
fuente toma las de la lista (las pide el formulario). `core/` no cambia: el casado de cada fila
sigue siendo el de `precios_propios_desde`."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from aplicacion.cifras import texto_de_cifra
from aplicacion.plural import plural
from core import models
from core.catalog import Catalogo, leer_lista_precios
from core.catalog.empresa import (
    crear_lista_de_empresa,
    crear_lista_de_referencia,
    instantanea_de_lista,
    lista_de_referencia,
    precios_propios_desde,
)
from core.catalog.indices import tasa_aplicable
from core.catalog.moneda import TasaDeclarada, exigir_moneda
from core.catalog.precios import PrecioLeido
from core.contracts.unidades import normalizar_unidad
from core.verification.precios import reglas_precios
from core.verification.texto import formatear_decimal, normalizar_texto

COLUMNAS_HALLAZGOS = ("Regla", "Severidad", "Descripción", "Impacto")
NOMBRE_REFERENCIA = "MaPreX julio 2026 en Bs"
RUTA_REFERENCIA_MAPREX = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "precios"
    / "maprex_2026-07"
    / "lista_maprex_bs.csv"
)
TASA_MAPREX = Decimal("633.3644")
FECHA_TASA_MAPREX = date(2026, 7, 1)
FUENTE_TASA_MAPREX = (
    "MaPreX v26.0.0.1, mano_de_obra.pdf: «01JUL @ 633,3644 BS/$» "
    "(data/precios/maprex_2026-07/README.md)"
)


@dataclass(frozen=True, slots=True)
class ResumenEmpresa:
    """Lo que hizo `crear_lista`: el nombre de la lista, cuantos precios propios entraron, las
    descripciones que no entraron (UC-17 4a), las que se dieron de alta (con la confirmacion) y,
    por fila de otra unidad, el aviso con la unidad del catalogo."""

    nombre: str
    propios: int
    desconocidos: tuple[str, ...]
    dados_de_alta: tuple[str, ...] = ()
    otra_unidad: tuple[str, ...] = ()
    lista_id: int | None = None


@dataclass(frozen=True, slots=True)
class RevisionDelArchivo:
    """Lo que `revisar_archivo` encontro sin escribir: cuantas filas reconoce el catalogo, las de
    insumos nuevos (se pueden dar de alta) y el aviso de cada fila con otra unidad."""

    reconocidos: int
    nuevos: tuple[PrecioLeido, ...]
    otra_unidad: tuple[str, ...]


def _confirmar[T](sesion, accion: Callable[[], T]) -> T:
    try:
        resultado = accion()
        sesion.commit()
    except BaseException:
        sesion.rollback()
        raise
    return resultado


def cargar_referencia_maprex(sesion) -> str:
    """Carga la lista MaPreX julio 2026 en Bs (S1 §6.2). Una referencia ya cargada no se duplica."""
    existente = lista_de_referencia(sesion)
    if existente is not None:
        return f"La referencia «{existente.nombre}» ya estaba cargada: no se escribio nada."
    tasa = TasaDeclarada(TASA_MAPREX, FECHA_TASA_MAPREX, FUENTE_TASA_MAPREX)
    lista = _confirmar(
        sesion,
        lambda: crear_lista_de_referencia(
            sesion, RUTA_REFERENCIA_MAPREX, nombre=NOMBRE_REFERENCIA, moneda="Bs", tasa=tasa
        ),
    )
    return (
        f"Referencia «{lista.nombre}» cargada con "
        f"{plural(len(lista.precios), 'precio', 'precios')}."
    )


def _con_la_lista(leidos: Sequence[PrecioLeido], fecha: date, fuente: str) -> list[PrecioLeido]:
    """D-11: la fila sin fecha o sin fuente toma la fecha y la fuente de la lista (RF-67)."""
    return [
        replace(leido, fecha=leido.fecha or fecha, fuente=leido.fuente.strip() or fuente.strip())
        for leido in leidos
    ]


def _unidades_del_catalogo(sesion) -> dict[tuple[str, str], list[str]]:
    """Por (tipo, descripcion normalizada), las unidades con que el catalogo tiene el insumo."""
    unidades: dict[tuple[str, str], list[str]] = {}
    for tipo, descripcion, unidad in sesion.execute(
        select(models.Insumo.tipo, models.Insumo.descripcion, models.Insumo.unidad)
    ):
        suyas = unidades.setdefault((tipo, normalizar_texto(descripcion)), [])
        texto = normalizar_unidad(unidad) if unidad else "sin unidad"
        if texto not in suyas:
            suyas.append(texto)
    return unidades


def _separar(sesion, desconocidos: Sequence[PrecioLeido]) -> tuple[list[PrecioLeido], list[str]]:
    """Los desconocidos que son insumos nuevos y el aviso de los que el catalogo tiene con otra
    unidad (no se dan de alta: serian un homonimo con otra unidad, el flujo 2b de UC-02)."""
    unidades = _unidades_del_catalogo(sesion)
    nuevos: list[PrecioLeido] = []
    avisos: list[str] = []
    for leido in desconocidos:
        suyas = unidades.get((leido.tipo.value, normalizar_texto(leido.descripcion)))
        if suyas is None:
            nuevos.append(leido)
        else:
            avisos.append(
                f"«{leido.descripcion}» viene en {leido.unidad or 'sin unidad'} y el catálogo lo "
                f"tiene en {' o '.join(suyas)}: no entró; escriba en el archivo la unidad del "
                "catálogo."
            )
    return nuevos, avisos


def revisar_archivo(sesion, ruta: Path) -> RevisionDelArchivo:
    """Lo que la lista haria con el archivo, sin escribir nada: el mismo casado de
    `precios_propios_desde` (la fecha y la fuente no cuentan para reconocer una fila)."""
    leidos = _con_la_lista(leer_lista_precios(ruta), date.today(), "revisión")
    _, desconocidos = precios_propios_desde(sesion, leidos)
    nuevos, avisos = _separar(sesion, desconocidos)
    return RevisionDelArchivo(len(leidos) - len(desconocidos), tuple(nuevos), tuple(avisos))


def _identidad(leido: PrecioLeido) -> tuple[str, str, str | None]:
    """La identidad con que `Catalogo.dar_de_alta_insumo` daria de alta la fila (la unidad solo
    cuenta en los materiales)."""
    unidad = leido.unidad if leido.tipo is models.TipoInsumo.MATERIAL else None
    return (leido.tipo.value, normalizar_texto(leido.descripcion), unidad)


def _dar_de_alta(sesion, nuevos: Sequence[PrecioLeido]) -> list[str]:
    """Da de alta cada insumo nuevo una sola vez (sin precio: su precio es el de la lista de la
    empresa) y devuelve sus descripciones. `ValueError` antes de escribir si un mismo insumo viene
    con dos precios."""
    por_identidad: dict[tuple[str, str, str | None], list[PrecioLeido]] = {}
    for leido in nuevos:
        por_identidad.setdefault(_identidad(leido), []).append(leido)
    for mismos in por_identidad.values():
        precios = list(dict.fromkeys(leido.precio for leido in mismos))
        if len(precios) > 1:
            raise ValueError(
                f"«{mismos[0].descripcion}» viene dos veces con precios distintos "
                f"({' y '.join(texto_de_cifra(p) for p in precios)}): deje una fila."
            )
    catalogo = Catalogo(sesion)
    for mismos in por_identidad.values():
        catalogo.dar_de_alta_insumo(mismos[0].tipo, mismos[0].descripcion, mismos[0].unidad)
    return [mismos[0].descripcion for mismos in por_identidad.values()]


def crear_lista(
    sesion,
    ruta: Path,
    *,
    empresa_nombre: str,
    empresa_rif: str,
    base_id: int,
    moneda: str,
    fecha: date,
    fuente: str,
    nombre: str,
    dar_de_alta: bool = False,
) -> ResumenEmpresa:
    """UC-17 4: lee el archivo, separa los precios propios de los insumos que el catalogo no
    conoce y crea la lista de empresa sobre la base elegida. Si la base esta en otra moneda, se
    convierte con la tasa del BCV aplicable a `fecha` (S1 §6.1). Con `dar_de_alta` (la
    confirmacion de la persona, tras `revisar_archivo`) los insumos nuevos se dan de alta y su
    precio entra a la lista; los de otra unidad nunca. Confirma o deshace todo."""
    exigir_moneda(moneda)
    leidos = _con_la_lista(leer_lista_precios(ruta), fecha, fuente)

    def accion() -> ResumenEmpresa:
        base = sesion.get(models.ListaPrecios, base_id)
        if base is None:
            raise ValueError(f"la lista base {base_id} no existe en esta carpeta")
        propios, desconocidos = precios_propios_desde(sesion, leidos)
        nuevos, avisos = _separar(sesion, desconocidos)
        dados: list[str] = []
        if dar_de_alta and nuevos:
            dados = _dar_de_alta(sesion, nuevos)
            propios, desconocidos = precios_propios_desde(sesion, leidos)
        tasa_base = None
        if base.moneda != moneda:
            tasa_base = TasaDeclarada.de_importacion(tasa_aplicable(sesion, fecha))
        lista = crear_lista_de_empresa(
            sesion,
            empresa_nombre,
            empresa_rif,
            base,
            propios,
            moneda=moneda,
            fecha=fecha,
            fuente=fuente,
            referencia=lista_de_referencia(sesion),
            nombre=nombre.strip() or None,
            tasa_base=tasa_base,
        )
        return ResumenEmpresa(
            lista.nombre,
            len(propios),
            tuple(leido.descripcion for leido in desconocidos),
            tuple(dados),
            tuple(avisos),
            lista.id,
        )

    return _confirmar(sesion, accion)


def hallazgos_de_lista(sesion, lista_id: int, fecha_evaluacion: date) -> list[dict[str, str]]:
    """R11 y R12 de la lista sola a `fecha_evaluacion`, en memoria (no escribe nada): sin version
    no hay cantidades, asi que el impacto es por unidad de insumo."""
    lista = sesion.get(models.ListaPrecios, lista_id)
    if lista is None:
        raise ValueError(f"la lista {lista_id} no existe en esta carpeta")
    instantanea = instantanea_de_lista(sesion, lista, lista_de_referencia(sesion), fecha_evaluacion)
    return [
        dict(
            zip(
                COLUMNAS_HALLAZGOS,
                (
                    h.regla,
                    h.severidad.name,
                    h.descripcion,
                    "" if h.impacto is None else formatear_decimal(h.impacto, 2),
                ),
                strict=True,
            )
        )
        for regla in reglas_precios(instantanea)
        for h in regla.evaluar(None)
    ]


def listas_base(sesion) -> list[tuple[int, str, str]]:
    """Las listas que pueden ser base de una lista de empresa (id, nombre, moneda): todas menos las
    de proyecto y las de empresa, de la mas reciente a la mas antigua."""
    fuera = select(models.ListaPreciosOrigen.lista_id).where(
        models.ListaPreciosOrigen.alcance.in_((models.ALCANCE_PROYECTO, models.ALCANCE_EMPRESA))
    )
    return [
        (lista.id, lista.nombre, lista.moneda)
        for lista in sesion.scalars(
            select(models.ListaPrecios)
            .where(models.ListaPrecios.id.not_in(fuera))
            .order_by(models.ListaPrecios.fecha_vigencia.desc(), models.ListaPrecios.id.desc())
        )
    ]


def listas_de_empresa(sesion) -> list[tuple[int, str]]:
    """Las listas de empresa del caso (id, nombre), en el orden en que se crearon."""
    return [
        (lista.id, lista.nombre)
        for lista in sesion.scalars(
            select(models.ListaPrecios)
            .join(models.ListaEmpresa, models.ListaEmpresa.lista_id == models.ListaPrecios.id)
            .order_by(models.ListaPrecios.id)
        )
    ]
