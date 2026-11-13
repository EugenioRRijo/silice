"""Crear una version nueva desde una GUARDADA y leer la cadena de sellos (T10, 3d-2, S2 a S6).

Son los botones de la pagina clasica que parten de una version guardada y no de un borrador:
«Restaurar» (`_restaurar`, P:2139), «Cotizar» y «Retirar cotizacion» (P:1954-2025) y «Convertir la
version» (`_moneda`, P:2068-2118); mas el estado de la cadena que la clasica nunca mostro
(`aplicacion.entrega.estado_de_la_cadena`). Cada una llama a la funcion de `aplicacion.hoja` (la
copia del Plan C, identica a `ui.hoja`) y cuida lo mismo que `hoja_guardado.guardar` (S1):

* **Una sola transaccion que empieza con `BEGIN IMMEDIATE`.** La sesion que llega es la de
  `core.catalog.abrir_sesion_de_escritura`: su primera sentencia toma el bloqueo de escritura ANTES
  de resolver el proyecto y de leer el ultimo codigo (`siguiente_codigo`): dos personas a la vez
  obtienen codigos distintos.
* **La sesion envuelta en `con_anexos_de_cadena`** (diseno §1.2): sin ella la cadena sella con
  «anexos ninguno» y `verificar_cadena` da por rota la version.
* **Todo o nada**, tambien en lo que se rechaza ANTES de escribir (proyecto o version inexistentes,
  un precio mal escrito): se deshace la transaccion que abrio la primera lectura, para que el
  bloqueo de escritura no quede retenido hasta que alguien cierre la sesion.
* Nada se lee de la sesion despues de confirmar (solo cadenas ya leidas): si no, el commit expiraria
  los objetos y la lectura abriria otra transaccion que retendria el bloqueo.

El responsable lo da quien llama (la persona de la sesion, RF-82). Sin FastAPI ni Streamlit (RM-1).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion import entrega, hoja
from aplicacion.entrega import EstadoDeLaCadena, con_anexos_de_cadena
from aplicacion.errores import HojaInvalida
from aplicacion.proyectos import resolver_proyecto
from core import models
from core.catalog import Catalogo

__all__ = [
    "ProyectoInexistente",
    "VersionInexistente",
    "VersionNueva",
    "convertir",
    "cotizar",
    "estado_de_la_cadena",
    "fuentes_de_versiones",
    "restaurar",
    "retirar_cotizacion",
]


def fuentes_de_versiones(sesion: Session, proyecto: str) -> dict[str, str]:
    """La fuente que escribió quien creó cada versión de `proyecto` (su nombre), por código: la de
    su registro de cambios; si los registros traen fuentes distintas, todas, en el orden en que se
    guardaron y separadas por « · ». Una versión sin registro no sale (E2E-3: la columna «Motivo» de
    Versiones decía la clave del servidor, «edicion», y no lo escrito). Solo lee."""
    filas = sesion.execute(
        select(models.Presupuesto.codigo, models.RegistroCambio.fuente)
        .join(models.Proyecto, models.Proyecto.id == models.Presupuesto.proyecto_id)
        .join(
            models.RegistroCambio,
            models.RegistroCambio.version_resultante_id == models.Presupuesto.id,
        )
        .where(models.Proyecto.nombre == proyecto)
        .order_by(models.RegistroCambio.id)
    ).all()
    fuentes: dict[str, list[str]] = {}
    for codigo, fuente in filas:
        texto = fuente.strip()
        if texto and texto not in fuentes.setdefault(codigo, []):
            fuentes[codigo].append(texto)
    return {codigo: " · ".join(lista) for codigo, lista in fuentes.items() if lista}


class ProyectoInexistente(Exception):  # noqa: N818
    """El proyecto (codigo o nombre) no existe en esta carpeta."""

    def __init__(self, referencia: str) -> None:
        super().__init__(f"La obra «{referencia}» no existe en esta carpeta.")


class VersionInexistente(Exception):  # noqa: N818
    """El proyecto no tiene esa version; el texto es el de la clasica (H:1572)."""


@dataclass(frozen=True, slots=True)
class VersionNueva:
    """Lo que dejo una operacion: el codigo de la version creada, el proyecto y el aviso."""

    codigo: str
    proyecto: str
    mensaje: str


def _proyecto(sesion: Session, referencia: str) -> str:
    encontrado = resolver_proyecto(sesion, referencia)
    if encontrado is None:
        raise ProyectoInexistente(referencia)
    return encontrado.nombre


def _crear(
    sesion: Session,
    referencia: str,
    version: str,
    escribir: Callable[[str], tuple[str, str]],
) -> VersionNueva:
    """El esqueleto comun: prepara la sesion, comprueba proyecto y version (404) y deja que
    `escribir(nombre)` cree la version y devuelva (codigo, mensaje). Ante cualquier error deshace
    la transaccion y lo deja subir."""
    con_anexos_de_cadena(sesion)  # el sello de lo que se escriba cubre el espacio (§1.2)
    try:
        nombre = _proyecto(sesion, referencia)
        try:
            hoja.lista_de_version(sesion, nombre, version)  # el 404 de la clasica (H:1572)
        except HojaInvalida as error:
            raise VersionInexistente(str(error)) from None
        codigo, mensaje = escribir(nombre)
    except BaseException:
        sesion.rollback()  # lo nucleo ya deshizo lo suyo; esto cubre lo de antes de escribir
        raise
    return VersionNueva(codigo=codigo, proyecto=nombre, mensaje=mensaje)


def restaurar(
    sesion: Session, proyecto: str, version: str, *, fuente: str, responsable: str
) -> VersionNueva:
    """S2: crea una version nueva, copia de `version`, que pasa a ser la vigente (RF-54)."""

    def escribir(nombre: str) -> tuple[str, str]:
        nuevo = hoja.restaurar(
            sesion, Catalogo(sesion), nombre, version, fuente=fuente, responsable=responsable
        )
        return nuevo, f"La versión {version} se restauró como la versión {nuevo} (la vigente)."

    return _crear(sesion, proyecto, version, escribir)


def cotizar(
    sesion: Session,
    proyecto: str,
    version: str,
    *,
    insumo: str,
    precio: str,
    proveedor: str,
    numero: str,
    fecha: date,
    evidencia: str | None,
    responsable: str,
) -> VersionNueva:
    """S3: cotiza `insumo` (su codigo) a `precio` (texto) para el proyecto (RF-56). El precio es
    lo que teclea la persona: coma decimal y punto de miles (`hoja.cifra_de_celda`)."""

    def escribir(nombre: str) -> tuple[str, str]:
        try:
            valor = hoja.cifra_de_celda(precio, "precio")
        except (
            ValueError
        ) as error:  # ComposicionInvalida: la clasica la muestra como cualquier otra
            raise HojaInvalida(str(error)) from error
        nuevo = hoja.cotizar(
            sesion,
            Catalogo(sesion),
            nombre,
            version,
            insumo=insumo,
            precio=valor,
            proveedor=proveedor,
            numero=numero,
            fecha=fecha,
            responsable=responsable,
            fuente=evidencia or "",
        )
        return nuevo, f"Se guardó la versión {nuevo} con la cotización de {insumo}."

    return _crear(sesion, proyecto, version, escribir)


def retirar_cotizacion(
    sesion: Session, proyecto: str, version: str, *, insumo: str, motivo: str, responsable: str
) -> VersionNueva:
    """S4: retira la cotizacion de `insumo`; la version nueva vuelve al precio de la lista base."""

    def escribir(nombre: str) -> tuple[str, str]:
        nuevo = hoja.retirar_cotizacion(
            sesion,
            Catalogo(sesion),
            nombre,
            version,
            insumo=insumo,
            fuente=motivo,
            responsable=responsable,
        )
        return nuevo, f"Se guardó la versión {nuevo} sin la cotización."

    return _crear(sesion, proyecto, version, escribir)


def convertir(
    sesion: Session,
    proyecto: str,
    version: str,
    moneda: str,
    *,
    lado: str,
    fecha: date,
    fuente: str,
    responsable: str,
) -> VersionNueva:
    """S5: la version convertida a `moneda` con la tasa del BCV aplicable a `fecha` (RF-64)."""

    def escribir(nombre: str) -> tuple[str, str]:
        nuevo = hoja.convertir(
            sesion,
            Catalogo(sesion),
            nombre,
            version,
            moneda,
            lado=lado,
            fecha=fecha,
            fuente=fuente,
            responsable=responsable,
        )
        return nuevo, f"Se guardó la versión {nuevo}, convertida a {moneda}."

    return _crear(sesion, proyecto, version, escribir)


def estado_de_la_cadena(sesion: Session, proyecto: str) -> EstadoDeLaCadena:
    """S6: recalcula cada huella de la cadena del proyecto. Solo lee."""
    nombre = _proyecto(sesion, proyecto)
    estado = entrega.estado_de_la_cadena(sesion, nombre)
    assert estado is not None  # el proyecto acaba de resolverse
    return estado
