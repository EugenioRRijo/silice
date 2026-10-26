"""La moneda de la carpeta de trabajo y la lista de precios para armar (MP-1, Tarea 1).

D-MP1 (diseño de montar un presupuesto §10): **una moneda por carpeta**. La carpeta declara su
moneda de trabajo (al crearla o, en las existentes, la de su lista vigente); la lista para armar es
la vigente de la carpeta, y si no está en esa moneda se avisa y no se arma. `core/` elige la lista
vigente sin mirar la moneda (`Catalogo.lista_vigente`), así que la regla vive aquí y el núcleo no
cambia. Ningún precio cambia de moneda en silencio: toda conversión usa la tasa del BCV de
`tasa_aplicable` (a lo sumo 7 días) y la declara en el origen de la lista y de cada precio. La
conversión es la de `core.catalog.moneda.convertir`: 28 dígitos significativos con ROUND_HALF_EVEN,
sin redondear a centésimas (100 Bs a 36,53 Bs/USD son 2,737476047084588009854913770 USD).

Ninguna función hace `commit`: escriben con `flush` y el que llama confirma o deshace (Componer
llama `lista_de_hoy` dentro de su guardado). La única excepción es la carga de la referencia
MaPreX, que `cargar_referencia_maprex` confirma por su cuenta cuando la carpeta aún no la tiene;
por eso `crear_lista_para_armar` comprueba la tasa antes de cargarla.

Los mensajes de `SinListaParaArmar` y `CarpetaConOtraMoneda` son los que ve la persona.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from sqlalchemy import ColumnElement, and_, exists, func, or_, select
from sqlalchemy.orm import Session

from aplicacion.cifras import texto_de_cifra
from aplicacion.precios_empresa import cargar_referencia_maprex
from aplicacion.tablas_carpeta import CarpetaDeTrabajo
from core import models
from core.budget.moneda import moneda_del_proyecto
from core.catalog import Catalogo
from core.catalog.empresa import lista_de_referencia
from core.catalog.errores import CatalogoIncompleto
from core.catalog.indices import TasaNoDisponible, tasa_aplicable
from core.catalog.moneda import TasaDeclarada, convertir_lista, copiar_precios, exigir_moneda

__all__ = [
    "MENSAJE_SIN_LISTA",
    "MENSAJE_SIN_TASA",
    "CarpetaConOtraMoneda",
    "ListaParaArmar",
    "SinListaParaArmar",
    "ValoracionDeLaObra",
    "crear_lista_para_armar",
    "declarar_moneda_de_la_carpeta",
    "describir",
    "exigir_responsable",
    "lista_de_hoy",
    "lista_para_armar",
    "lista_para_el_proyecto",
    "moneda_de_la_carpeta",
    "valoracion_de_la_obra",
]

MENSAJE_SIN_LISTA = (
    "Esta carpeta de trabajo no tiene lista de precios para armar. Créela a partir de MaPreX o "
    "convirtiendo la que tiene."
)
MENSAJE_SIN_TASA = (
    "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar."
)
#: La referencia MaPreX solo existe en Bs (`aplicacion/precios_empresa.py`, choque 6 del plan).
MONEDA_DE_MAPREX = "Bs"
#: Largo de `lista_precios.nombre` y `lista_precios.origen` (`core/models/entidades.py`).
_LARGO_NOMBRE = 120
_LARGO_ORIGEN = 200
_ID_CARPETA = 1
#: El nombre sin un sufijo final « al dd/mm/aaaa» ni « (n)» (la raíz de una lista derivada).
_RAIZ = re.compile(r"(.*?)(?: al \d{2}/\d{2}/\d{4})?(?: \(\d+\))?", re.DOTALL)


class SinListaParaArmar(ValueError):  # noqa: N818
    """No hay lista para armar en la moneda de la carpeta (o no se pudo crear); el mensaje es el
    que ve la persona."""


class CarpetaConOtraMoneda(ValueError):  # noqa: N818
    """La carpeta ya trabaja en otra moneda (declarada o la de su lista vigente): para trabajar en
    la otra se crea otra carpeta (D-MP1). El mensaje es el que ve la persona."""


@dataclass(frozen=True)
class ValoracionDeLaObra:
    """Con qué se valora una obra a una fecha, sin escribir nada: la lista para armar de la carpeta
    y, si la obra está en la otra moneda, la tasa del BCV con que se convierte (`None` si no)."""

    proyecto: models.Proyecto
    moneda: str
    base: models.ListaPrecios
    tasa: TasaDeclarada | None


@dataclass(frozen=True)
class ListaParaArmar:
    lista_id: int
    nombre: str
    moneda: str
    fecha: date
    origen: str


# --- la moneda de la carpeta ------------------------------------------------------------------


def _declarada(sesion: Session) -> str | None:
    fila = sesion.get(CarpetaDeTrabajo, _ID_CARPETA)
    return None if fila is None else fila.moneda


def _vigente(sesion: Session, fecha: date) -> models.ListaPrecios | None:
    try:
        return Catalogo(sesion).lista_vigente(fecha)
    except CatalogoIncompleto:
        return None


def _moneda(sesion: Session, fecha: date) -> str | None:
    declarada = _declarada(sesion)
    if declarada is not None:
        return declarada
    vigente = _vigente(sesion, fecha)
    return None if vigente is None else vigente.moneda


def moneda_de_la_carpeta(sesion: Session, fecha: date | None = None) -> str | None:
    """La moneda declarada; si no hay, la de la lista vigente a `fecha` (hoy, sin `fecha`); sin
    lista, `None`."""
    return _moneda(sesion, date.today() if fecha is None else fecha)


def exigir_responsable(responsable: str) -> str:
    responsable = responsable.strip()
    if not responsable:
        raise ValueError("hace falta quién lo hace (responsable)")
    return responsable


def declarar_moneda_de_la_carpeta(
    sesion: Session, moneda: str, *, responsable: str, ahora: datetime
) -> None:
    """Declara la moneda de trabajo de la carpeta (una sola vez: D-MP1).

    Declarar la que ya tiene no cambia nada (ni quién ni cuándo). `CarpetaConOtraMoneda` si ya
    hay otra declarada o la lista vigente a `ahora` está en otra; `ValueError` con una moneda que
    no es Bs ni USD o sin responsable. No confirma."""
    exigir_moneda(moneda)
    responsable = exigir_responsable(responsable)
    actual = moneda_de_la_carpeta(sesion, ahora.date())
    if actual is not None and actual != moneda:
        raise CarpetaConOtraMoneda(
            f"La carpeta de trabajo ya trabaja en {actual}: para trabajar en {moneda}, "
            "cree otra carpeta."
        )
    if sesion.get(CarpetaDeTrabajo, _ID_CARPETA) is not None:
        return
    sesion.add(
        CarpetaDeTrabajo(
            id=_ID_CARPETA,
            moneda=moneda,
            declarada_por=responsable[:200],
            declarada_el=ahora,
        )
    )
    sesion.flush()


# --- la lista para armar ----------------------------------------------------------------------


def _primera_posterior(sesion: Session, fecha: date) -> date | None:
    """La fecha de vigencia de la primera lista que `lista_vigente` resolvería después de `fecha`
    (las de proyecto, empresa y referencia no cuentan, como en el núcleo); `None` si no hay."""
    fuera_de_vigente = exists().where(
        models.ListaPreciosOrigen.lista_id == models.ListaPrecios.id,
        models.ListaPreciosOrigen.alcance.in_(models.ALCANCES_FUERA_DE_VIGENTE),
    )
    return sesion.scalar(
        select(func.min(models.ListaPrecios.fecha_vigencia)).where(
            models.ListaPrecios.fecha_vigencia > fecha, ~fuera_de_vigente
        )
    )


def lista_para_armar(sesion: Session, fecha: date) -> models.ListaPrecios:
    """La lista vigente a `fecha` si está en la moneda de la carpeta; si no, `SinListaParaArmar`."""
    vigente = _vigente(sesion, fecha)
    if vigente is None:
        raise SinListaParaArmar(MENSAJE_SIN_LISTA)
    moneda = _declarada(sesion) or vigente.moneda
    if vigente.moneda != moneda:
        raise SinListaParaArmar(
            f"La lista vigente «{vigente.nombre}» está en {vigente.moneda} y la carpeta trabaja "
            f"en {moneda}: conviértala antes de armar."
        )
    return vigente


def describir(sesion: Session, fecha: date) -> ListaParaArmar | None:
    """La lista para armar a `fecha`, para mostrarla; `None` si no la hay."""
    try:
        lista = lista_para_armar(sesion, fecha)
    except SinListaParaArmar:
        return None
    return _descrita(lista)


def describir_vigente(sesion: Session, fecha: date) -> ListaParaArmar | None:
    """La lista vigente a `fecha` en cualquier moneda, para mostrarla; `None` si no la hay.

    En la moneda de la carpeta es la de `describir`; en otra, es la que no sirve para armar y hay
    que convertir (`lista_para_armar` lo dice con su mensaje)."""
    vigente = _vigente(sesion, fecha)
    return None if vigente is None else _descrita(vigente)


def _descrita(lista: models.ListaPrecios) -> ListaParaArmar:
    return ListaParaArmar(lista.id, lista.nombre, lista.moneda, lista.fecha_vigencia, lista.origen)


def _raiz(nombre: str) -> str:
    coincidencia = _RAIZ.fullmatch(nombre)
    return nombre if coincidencia is None else coincidencia.group(1)


def _en_moneda(raiz: str, de: str, a: str) -> str:
    """«MaPreX julio 2026 en Bs» en USD es «MaPreX julio 2026 en USD»; «Base», «Base en USD»."""
    if de == a:
        return raiz
    sufijo = f" en {de}"
    if raiz.endswith(sufijo):
        raiz = raiz[: -len(sufijo)]
    return f"{raiz} en {a}"


def _nombre_libre(sesion: Session, raiz: str, fecha: date) -> str:
    """`{raiz} al dd/mm/aaaa`, y « (2)», « (3)»… si ya existe; recorta la raíz para caber."""
    cuerpo = f" al {fecha:%d/%m/%Y}"
    existentes = set(sesion.scalars(select(models.ListaPrecios.nombre)))
    numero = 1
    while True:
        extra = "" if numero == 1 else f" ({numero})"
        nombre = raiz[: _LARGO_NOMBRE - len(cuerpo) - len(extra)] + cuerpo + extra
        if nombre not in existentes:
            return nombre
        numero += 1


def _lista_global(
    sesion: Session,
    de: models.ListaPrecios,
    *,
    nombre: str,
    moneda: str,
    fecha: date,
    origen: str,
    tasa: TasaDeclarada | None,
) -> models.ListaPrecios:
    """Lista global nueva (sin `ListaPreciosOrigen`, así la resuelve `lista_vigente`) con los
    precios de `de`, convertidos con `tasa` si las monedas difieren."""
    nueva = models.ListaPrecios(
        nombre=nombre, moneda=moneda, fecha_vigencia=fecha, origen=origen[:_LARGO_ORIGEN]
    )
    sesion.add(nueva)
    sesion.flush()
    copiar_precios(sesion, de, nueva, tasa)
    sesion.expire(nueva, ["precios"])
    return nueva


def _nombre_convertida(base: str, moneda: str, fecha: date) -> str:
    """El nombre que ve la persona de la conversión de alcance proyecto de la lista `base` a
    `moneda` hecha a `fecha`. Se recorta para caber, así que NO identifica la base: eso lo hace
    `_marca_de_conversion`."""
    sufijo = f" en {moneda} al {fecha:%d/%m/%Y}"
    return base[: _LARGO_NOMBRE - len(sufijo)] + sufijo


def _marca_de_conversion(base_id: int) -> str:
    """El comienzo del `origen` de una conversión de alcance proyecto: dice de qué lista sale por
    su número. Es la clave fiable de la base (el nombre se recorta y `convertir_lista` deja
    `lista_base_id` vacío a propósito); va al principio para que el recorte a 200 no la toque."""
    return f"Convertida de la lista n.º {base_id}: "


def _convertida_de(base_id: int) -> ColumnElement[bool]:
    """La condición SQL «esta lista es una conversión de alcance proyecto de `base_id`»."""
    marca = _marca_de_conversion(base_id)
    return and_(
        models.ListaPreciosOrigen.lista_id == models.ListaPrecios.id,
        models.ListaPreciosOrigen.alcance == models.ALCANCE_PROYECTO,
        func.substr(models.ListaPrecios.origen, 1, len(marca)) == marca,
    )


def _usada(sesion: Session, lista: models.ListaPrecios) -> bool:
    """Si reescribir un precio de `lista` en el lugar dejaría algo copiado con el precio viejo: la
    usa una versión, otra lista la tomó de base (`ListaPreciosOrigen`, `ListaEmpresa`) o una obra
    en la otra moneda la convirtió (`lista_para_el_proyecto` reutilizaría esa conversión)."""
    origen = models.ListaPreciosOrigen
    empresa = models.ListaEmpresa
    copiada = [
        exists().where(models.Presupuesto.lista_precios_id == lista.id),
        exists().where(origen.lista_base_id == lista.id),
        exists().where(
            or_(empresa.lista_base_id == lista.id, empresa.lista_referencia_id == lista.id)
        ),
        exists().where(_convertida_de(lista.id)),
    ]
    return bool(sesion.scalar(select(or_(*copiada))))


def lista_de_hoy(sesion: Session, fecha: date, *, nueva_si_usada: bool) -> models.ListaPrecios:
    """La lista donde se escribe un precio tecleado a `fecha` (O-13: no se reescribe una lista
    vieja). Es la lista para armar si ya es de esa fecha (y, con `nueva_si_usada`, nada la usa ni
    la copió: `_usada`); si no, una derivada global de esa moneda y fecha con los mismos precios."""
    base = lista_para_armar(sesion, fecha)
    if base.fecha_vigencia == fecha and not (nueva_si_usada and _usada(sesion, base)):
        return base
    return _lista_global(
        sesion,
        base,
        nombre=_nombre_libre(sesion, _raiz(base.nombre), fecha),
        moneda=base.moneda,
        fecha=fecha,
        origen=f"derivada de «{base.nombre}»",
        tasa=None,
    )


def _tasa(sesion: Session, fecha: date) -> TasaDeclarada:
    try:
        return TasaDeclarada.de_importacion(tasa_aplicable(sesion, fecha))
    except TasaNoDisponible:
        raise SinListaParaArmar(MENSAJE_SIN_TASA) from None


def _con_tasa(tasa: TasaDeclarada) -> str:
    """La tasa como la escribe Sílice: coma decimal y punto de miles («40,00 Bs/USD»)."""
    return f"con {texto_de_cifra(tasa.valor)} Bs/USD del {tasa.fecha:%d/%m/%Y}"


def valoracion_de_la_obra(sesion: Session, proyecto: str, fecha: date) -> ValoracionDeLaObra:
    """La lista para armar a `fecha` y, si la obra `proyecto` está en la otra moneda, la tasa del
    BCV del día (a lo sumo 7 días). No escribe. `SinListaParaArmar` sin lista o sin tasa;
    `ValueError` si la obra no existe.

    La Hoja valora a la fecha del borrador: si la carpeta tiene listas pero todas rigen después,
    el mensaje dice esa fecha y desde cuándo rige la primera (no es que falte la lista: todavía no
    rige). Componer, que arma a hoy, conserva el mensaje de `lista_para_armar`."""
    fila = sesion.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == proyecto)
    ).one_or_none()
    if fila is None:
        raise ValueError(f"No hay ninguna obra «{proyecto}» en esta carpeta de trabajo.")
    if _vigente(sesion, fecha) is None and (primera := _primera_posterior(sesion, fecha)):
        raise SinListaParaArmar(
            f"Esta carpeta de trabajo no tiene lista de precios para armar vigente al "
            f"{fecha:%d/%m/%Y}: su primera lista rige desde el {primera:%d/%m/%Y}."
        )
    base = lista_para_armar(sesion, fecha)
    moneda = moneda_del_proyecto(sesion, fila)
    tasa = None if moneda == base.moneda else _tasa(sesion, fecha)
    return ValoracionDeLaObra(fila, moneda, base, tasa)


def lista_para_el_proyecto(
    sesion: Session, proyecto: str, fecha: date, *, responsable: str
) -> models.ListaPrecios:
    """La lista con que se valora la obra `proyecto` a `fecha`.

    Si la obra está en la moneda de la carpeta, la lista para armar. Si no (choque 16), su
    conversión de alcance proyecto con la tasa del BCV del día (`convertir_lista`), que se
    reutiliza si ya existe para esa obra, esa base (por su número en el `origen`, no por el
    nombre, que se recorta), esa fecha y esa tasa. `SinListaParaArmar` sin
    lista o sin tasa de los últimos 7 días; `ValueError` si la obra no existe. No confirma."""
    responsable = exigir_responsable(responsable)
    valoracion = valoracion_de_la_obra(sesion, proyecto, fecha)
    fila, moneda, base, tasa = (
        valoracion.proyecto,
        valoracion.moneda,
        valoracion.base,
        valoracion.tasa,
    )
    if tasa is None:
        return base
    nombre = _nombre_convertida(base.nombre, moneda, fecha)
    existente = sesion.scalars(
        select(models.ListaPrecios)
        .join(
            models.ListaPreciosOrigen, models.ListaPreciosOrigen.lista_id == models.ListaPrecios.id
        )
        .where(
            _convertida_de(base.id),
            models.ListaPreciosOrigen.proyecto_id == fila.id,
            models.ListaPreciosOrigen.tasa == tasa.valor,
            models.ListaPreciosOrigen.fecha_tasa == tasa.fecha,
            models.ListaPrecios.moneda == moneda,
            models.ListaPrecios.fecha_vigencia == base.fecha_vigencia,
        )
        .order_by(models.ListaPrecios.id.desc())
        .limit(1)
    ).one_or_none()
    if existente is not None:
        return existente
    convertida = convertir_lista(sesion, base, moneda, tasa, nombre=nombre, proyecto=fila)
    convertida.origen = f"{_marca_de_conversion(base.id)}{convertida.origen}, por {responsable}"[
        :_LARGO_ORIGEN
    ]
    sesion.flush()
    return convertida


# --- crear la lista para armar ----------------------------------------------------------------


def _desde_maprex(sesion: Session, fecha: date, responsable: str) -> models.ListaPrecios:
    referencia = lista_de_referencia(sesion)
    moneda_referencia = MONEDA_DE_MAPREX if referencia is None else referencia.moneda
    moneda = _moneda(sesion, fecha) or moneda_referencia
    # la tasa se comprueba antes de cargar la referencia, que se confirma por su cuenta
    tasa = None if moneda == moneda_referencia else _tasa(sesion, fecha)
    if referencia is None:
        cargar_referencia_maprex(sesion)
        referencia = lista_de_referencia(sesion)
        if referencia is None:  # pragma: no cover - cargar_referencia_maprex la deja cargada
            raise SinListaParaArmar(MENSAJE_SIN_LISTA)
    convertida = "" if tasa is None else f" en {moneda} {_con_tasa(tasa)}"
    return _lista_global(
        sesion,
        referencia,
        nombre=_nombre_libre(
            sesion, _en_moneda(_raiz(referencia.nombre), referencia.moneda, moneda), fecha
        ),
        moneda=moneda,
        fecha=fecha,
        origen=f"copia de la referencia «{referencia.nombre}»{convertida}, por {responsable}",
        tasa=tasa,
    )


def _convirtiendo(sesion: Session, fecha: date, responsable: str) -> models.ListaPrecios:
    vigente = _vigente(sesion, fecha)
    if vigente is None:
        raise SinListaParaArmar(MENSAJE_SIN_LISTA)
    moneda = _declarada(sesion) or vigente.moneda
    if vigente.moneda == moneda:
        raise SinListaParaArmar(
            f"La lista vigente «{vigente.nombre}» ya está en {moneda}: no hay nada que convertir."
        )
    tasa = _tasa(sesion, fecha)
    return _lista_global(
        sesion,
        vigente,
        nombre=_nombre_libre(
            sesion, _en_moneda(_raiz(vigente.nombre), vigente.moneda, moneda), fecha
        ),
        moneda=moneda,
        fecha=fecha,
        origen=f"«{vigente.nombre}» convertida a {moneda} {_con_tasa(tasa)}, por {responsable}",
        tasa=tasa,
    )


def crear_lista_para_armar(
    sesion: Session,
    *,
    desde: Literal["maprex", "convertir"],
    fecha: date,
    responsable: str,
) -> models.ListaPrecios:
    """Crea la lista para armar de la carpeta, global y fechada `fecha`.

    `"maprex"`: copia la referencia MaPreX (la carga si falta) en la moneda de la carpeta,
    convirtiendo con la tasa del BCV si la carpeta trabaja en USD; sin moneda declarada ni lista,
    queda en la de la referencia (Bs). `"convertir"`: copia la lista vigente, que está en otra
    moneda, a la de la carpeta con la tasa del BCV. `SinListaParaArmar` sin tasa de los últimos 7
    días, sin lista que convertir o si la vigente ya está en la moneda de la carpeta. No confirma
    (salvo la carga de la referencia: ver el módulo)."""
    responsable = exigir_responsable(responsable)
    if desde == "maprex":
        return _desde_maprex(sesion, fecha, responsable)
    if desde == "convertir":
        return _convirtiendo(sesion, fecha, responsable)
    raise ValueError(f"desde {desde!r}; se espera maprex o convertir")
