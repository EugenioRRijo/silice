"""Listas de precios nuevas y el historial de cambios que producen (UC‑02, Sesión I1).

Tres responsabilidades, en el orden en que las usa el caso de uso:

1. **Leer** un archivo CSV o XLSX con las columnas `tipo`, `insumo`, `unidad` y `precio`. Todo
   importe se construye con `Decimal` **desde el texto** del archivo, nunca desde un `float`
   (CLAUDE.md §2.3). El CSV ya es texto en el archivo: `pandas.read_csv(dtype=str)` lo lee tal
   cual. El XLSX es distinto: `pandas.read_excel(dtype=str)` **no** basta, porque el motor de
   Excel (`openpyxl`) analiza toda celda numérica como `float` de Python *antes* de que `pandas`
   pueda aplicar `dtype`, que solo convierte ese `float` a texto *después*, delegando el formateo a
   un arreglo intermedio de `numpy` que este módulo no controla ni puede garantizar entre
   versiones. Por eso el XLSX se lee celda por celda con `openpyxl` (`_leer_tabla_excel`), en
   Python puro y sin arreglos intermedios.
2. **Crear** la lista nueva a partir de la vigente: copia todos sus precios y sobrescribe los que
   trae el archivo. Así la lista nueva vale por sí sola para reconstruir cualquier APU, que es lo
   que exige `Catalogo.composicion`. Los insumos que el catálogo no conoce **no se crean**: se
   devuelven en `ResumenLista.desconocidos` para que el usuario decida (UC‑02, flujo 2a).
3. **Detectar y registrar** qué insumos cambiaron de precio entre dos listas. Ese historial es el
   que alimentará al módulo predictivo (Sesión I6), de modo que se persiste siempre, aunque el
   presupuesto nuevo se descarte (UC‑02, flujo 7a).

Un insumo se identifica por (tipo, descripción, unidad), no por su código: el archivo lo escribe un
proveedor que no conoce los códigos internos. La descripción se compara normalizada con
`core.verification.texto.normalizar_texto`, la única tabla de normalización de texto del sistema
(principio DRY), y la unidad con `normalizar_unidad`, la única tabla de alias.

**Homónimos.** La línea base carga como variantes los insumos con la misma descripción y distinto
precio (`Agua`, `Pala`, `Cinta métrica`, `Nivel de mano`; docs/modelo_datos.md §6). Una fila del
archivo actualiza **todas** las variantes de esa descripción y unidad: el archivo declara un precio
por insumo, y distinguir variantes exigiría que el proveedor escribiera los códigos internos.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.catalog.repositorio import Catalogo
from core.contracts.unidades import normalizar_unidad
from core.verification.texto import normalizar_texto

__all__ = [
    "COLUMNAS_ARCHIVO",
    "CambioDetectado",
    "PrecioLeido",
    "ResumenLista",
    "cambios_precio",
    "crear_lista_desde_archivo",
    "insumos_afectados",
    "leer_lista_precios",
    "registrar_cambios",
    "variacion_relativa",
]

#: Columnas obligatorias del archivo de precios.
COLUMNAS_ARCHIVO = ("tipo", "insumo", "unidad", "precio")

#: Extensiones que se saben leer. `.xls` exige `xlrd`, que no es dependencia del proyecto.
SUFIJO_CSV = ".csv"
SUFIJOS_EXCEL = (".xlsx", ".xlsm")

#: Primera fila con datos del archivo: la 1 es la de encabezados.
_PRIMERA_FILA_DE_DATOS = 2

#: Grafías de la columna `tipo` que no son el valor canónico de `models.TipoInsumo`.
_ALIAS_TIPO = {
    "mano de obra": models.TipoInsumo.MANO_OBRA,
    "mano_de_obra": models.TipoInsumo.MANO_OBRA,
}

#: Un insumo del catálogo visto desde el archivo: (tipo, descripción normalizada, unidad).
_ClaveInsumo = tuple[str, str, str | None]


@dataclass(frozen=True, slots=True)
class PrecioLeido:
    """Una fila del archivo ya validada: qué insumo describe y a qué precio."""

    tipo: models.TipoInsumo
    descripcion: str
    unidad: str | None
    precio: Decimal


@dataclass(frozen=True, slots=True)
class ResumenLista:
    """Qué produjo la carga de un archivo de precios.

    `desconocidos` son las filas cuyo (tipo, descripción, unidad) no está en el catálogo: se
    reportan y no intervienen en el recálculo, porque dar de alta un insumo es una decisión del
    administrador, no un efecto secundario de leer un archivo (UC‑02, flujo 2a). Sigue el patrón de
    `ResumenCarga`: la carga devuelve lo que hizo, no solo lo que creó.
    """

    lista: models.ListaPrecios
    desconocidos: tuple[PrecioLeido, ...] = ()


_CERO = Decimal(0)


def variacion_relativa(anterior: Decimal, nuevo: Decimal) -> Decimal:
    """Fracción (nuevo − anterior) / anterior: la fórmula de docs/modelo_datos.md §6.

    Única definición del sistema (INV‑004): la usan `CambioDetectado.variacion` y la incidencia por
    partida de `core.budget.actualizacion`.

    **Base nula.** Con `anterior == 0` la variación relativa no está definida. Política declarada:
    devuelve 0, y el registro conserva `precio_anterior = 0`, que es lo que distingue ese caso de
    un precio que no cambió. Un precio 0 es válido (`leer_lista_precios` acepta cualquier no
    negativo), así que la fórmula no puede lanzar `DivisionByZero` en medio de UC‑02.
    """
    return (nuevo - anterior) / anterior if anterior else _CERO


@dataclass(frozen=True, slots=True)
class CambioDetectado:
    """Un insumo cuyo precio difiere entre dos listas, antes de persistirlo."""

    insumo: models.Insumo
    precio_anterior: Decimal
    precio_nuevo: Decimal

    @property
    def variacion(self) -> Decimal:
        """Fracción (nuevo − anterior) / anterior, con la política de base nula declarada."""
        return variacion_relativa(self.precio_anterior, self.precio_nuevo)


# ---------------------------------------------------------------------------------------------
# Lectura del archivo
# ---------------------------------------------------------------------------------------------


def leer_lista_precios(ruta: Path) -> list[PrecioLeido]:
    """Lee un archivo de precios CSV o XLSX y devuelve sus filas validadas, en su mismo orden.

    Lanza `ValueError` citando el archivo y el número de fila si falta una columna, si el tipo de
    insumo no existe o si el precio no es un número no negativo: una lista de precios a medias
    valoraría el presupuesto en silencio (UC‑02, flujo 2a de docs/ERS.md).

    El separador decimal es el punto. Aceptar también la coma exigiría decidir qué significa el
    separador de miles, y ninguna fuente del proyecto lo necesita todavía.
    """
    tabla = _leer_tabla(ruta)
    faltantes = [columna for columna in COLUMNAS_ARCHIVO if columna not in tabla.columns]
    if faltantes:
        raise ValueError(
            f"{ruta.name}: faltan las columnas {', '.join(faltantes)}; "
            f"se esperan {', '.join(COLUMNAS_ARCHIVO)}"
        )
    return [
        _a_precio_leido(fila, numero, ruta)
        for numero, fila in enumerate(tabla.to_dict("records"), start=_PRIMERA_FILA_DE_DATOS)
    ]


def _leer_tabla(ruta: Path) -> pd.DataFrame:
    """El archivo como tabla de texto: ningún importe pasa por `float` en ningún paso."""
    sufijo = ruta.suffix.lower()
    if sufijo == SUFIJO_CSV:
        tabla = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8")
    elif sufijo in SUFIJOS_EXCEL:
        tabla = _leer_tabla_excel(ruta)
    else:
        raise ValueError(
            f"{ruta.name}: formato no soportado; se leen {', '.join((SUFIJO_CSV, *SUFIJOS_EXCEL))}"
        )
    tabla.columns = [str(columna).strip().lower() for columna in tabla.columns]
    return tabla.fillna("")


def _leer_tabla_excel(ruta: Path) -> pd.DataFrame:
    """Lee un XLSX celda por celda con `openpyxl`, sin la ruta de `pandas.read_excel(dtype=str)`.

    Esa ruta no evita el `float`: el motor `openpyxl` analiza toda celda numérica del XML como
    `float` de Python al leer el archivo, y el parámetro `dtype` de `pandas.read_excel` solo
    convierte ese `float` a texto *después*, pasando por un arreglo intermedio de `numpy` cuyo
    formateo no depende de este módulo. Aquí se lee celda por celda y se convierte cada valor a
    texto de una vez, en Python puro y sin arreglos intermedios: si la celda ya es texto se usa tal
    cual (el caso exacto por construcción, el recomendado para la columna `precio`); si Excel la
    guardó como número, se usa `str()` de Python sobre ese valor, que para cualquier precio real
    (con la precisión que un ser humano puede escribir en una celda) reconstruye el mismo texto que
    se escribió: CPython garantiza que su algoritmo de la representación más corta cumple
    `float(str(x)) == x`.
    """
    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    try:
        filas = libro.active.iter_rows(values_only=True)
        try:
            encabezados = [_texto_celda(valor) for valor in next(filas)]
        except StopIteration:
            return pd.DataFrame()
        registros = [
            dict(zip(encabezados, (_texto_celda(valor) for valor in fila), strict=False))
            for fila in filas
            if any(valor is not None for valor in fila)
        ]
    finally:
        libro.close()
    return pd.DataFrame.from_records(registros, columns=encabezados)


def _texto_celda(valor: object) -> str:
    """Una celda de Excel como texto exacto, sin pasar por ningún arreglo de `numpy`."""
    if valor is None:
        return ""
    if isinstance(valor, str):
        return valor.strip()
    return str(valor).strip()


def _a_precio_leido(fila: dict[str, object], numero: int, ruta: Path) -> PrecioLeido:
    descripcion = _texto(fila["insumo"])
    if not descripcion:
        raise ValueError(f"{ruta.name}, fila {numero}: la columna insumo está vacía")
    unidad = _texto(fila["unidad"])
    return PrecioLeido(
        tipo=_a_tipo(_texto(fila["tipo"]), numero, ruta),
        descripcion=descripcion,
        unidad=normalizar_unidad(unidad) if unidad else None,
        precio=_a_precio(_texto(fila["precio"]), numero, ruta),
    )


def _texto(valor: object) -> str:
    return str(valor).strip()


def _a_tipo(valor: str, numero: int, ruta: Path) -> models.TipoInsumo:
    clave = valor.lower()
    if clave in _ALIAS_TIPO:
        return _ALIAS_TIPO[clave]
    try:
        return models.TipoInsumo(clave)
    except ValueError as error:
        esperados = ", ".join(tipo.value for tipo in models.TipoInsumo)
        raise ValueError(
            f"{ruta.name}, fila {numero}: tipo de insumo {valor!r} desconocido; "
            f"se espera uno de {esperados}"
        ) from error


def _a_precio(valor: str, numero: int, ruta: Path) -> Decimal:
    try:
        precio = Decimal(valor)
    except InvalidOperation as error:
        raise ValueError(
            f"{ruta.name}, fila {numero}: el precio {valor!r} no es un número decimal"
        ) from error
    # `is_finite()` va primero y en la misma condicion: `Decimal("nan") < 0` lanzaria
    # `InvalidOperation` (un `ArithmeticError`, no el `ValueError` que promete el docstring de
    # `leer_lista_precios`) y `Decimal("Infinity") < 0` es `False`, asi que un precio infinito
    # entraria a la lista en silencio.
    if not precio.is_finite() or precio < 0:
        raise ValueError(
            f"{ruta.name}, fila {numero}: el precio {valor} no es un numero no negativo"
        )
    return precio


# ---------------------------------------------------------------------------------------------
# Creación de la lista
# ---------------------------------------------------------------------------------------------


def crear_lista_desde_archivo(
    session: Session,
    ruta: Path,
    nombre: str,
    moneda: str,
    fecha_vigencia: date,
    origen: str = "",
) -> ResumenLista:
    """Crea la lista de precios que declara el archivo, partiendo de la vigente a esa fecha.

    La lista nueva nace con **todos** los precios de la anterior y sobrescribe los del archivo, de
    modo que valora el catálogo completo: una lista incompleta haría fallar la reconstrucción de
    cualquier APU con un insumo sin precio (`CatalogoIncompleto`).

    Deja la transacción abierta —confirmarla o deshacerla es de quien llama, como en
    `core.budget.guardar_presupuesto`— y no modifica la lista anterior: es inmutable desde que un
    presupuesto la referencia (docs/modelo_datos.md §2.2).

    Sin `origen` queda el nombre del archivo, que es la procedencia del dato (CLAUDE.md §2.6).
    """
    leidos = leer_lista_precios(ruta)
    anterior = Catalogo(session).lista_vigente(fecha_vigencia)

    lista = models.ListaPrecios(
        nombre=nombre,
        moneda=moneda,
        fecha_vigencia=fecha_vigencia,
        origen=origen or ruta.name,
    )
    session.add(lista)
    session.flush()

    catalogados = _insumos_por_clave(session)
    precios = {precio.insumo_id: precio.precio for precio in anterior.precios}
    desconocidos: list[PrecioLeido] = []
    for leido in leidos:
        variantes = catalogados.get(_clave(leido.tipo.value, leido.descripcion, leido.unidad))
        if not variantes:
            desconocidos.append(leido)
            continue
        for insumo in variantes:
            precios[insumo.id] = leido.precio

    session.add_all(
        models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo_id, precio=precio)
        for insumo_id, precio in precios.items()
    )
    session.flush()
    return ResumenLista(lista=lista, desconocidos=tuple(desconocidos))


def _insumos_por_clave(session: Session) -> dict[_ClaveInsumo, list[models.Insumo]]:
    """Índice del catálogo por (tipo, descripción, unidad); una clave puede traer variantes."""
    indice: dict[_ClaveInsumo, list[models.Insumo]] = defaultdict(list)
    for insumo in session.scalars(select(models.Insumo).order_by(models.Insumo.codigo)):
        indice[_clave(insumo.tipo, insumo.descripcion, insumo.unidad)].append(insumo)
    return indice


def _clave(tipo: str, descripcion: str, unidad: str | None) -> _ClaveInsumo:
    return (tipo, normalizar_texto(descripcion), normalizar_unidad(unidad) if unidad else None)


# ---------------------------------------------------------------------------------------------
# Historial de cambios
# ---------------------------------------------------------------------------------------------


def insumos_afectados(
    session: Session, lista_anterior: models.ListaPrecios, lista_nueva: models.ListaPrecios
) -> list[CambioDetectado]:
    """Insumos con precio distinto entre las dos listas, ordenados por código de insumo.

    Un insumo que solo tiene precio en una de las dos no es un cambio de precio: no hay variación
    que calcular, y `CambioPrecio` exige los dos importes.
    """
    anteriores = _precios_de(session, lista_anterior)
    nuevos = session.execute(
        select(models.Insumo, models.PrecioInsumo.precio)
        .join(models.PrecioInsumo, models.PrecioInsumo.insumo_id == models.Insumo.id)
        .where(models.PrecioInsumo.lista_id == lista_nueva.id)
        .order_by(models.Insumo.codigo)
    ).all()
    return [
        CambioDetectado(insumo=insumo, precio_anterior=anteriores[insumo.id], precio_nuevo=precio)
        for insumo, precio in nuevos
        if insumo.id in anteriores and anteriores[insumo.id] != precio
    ]


def registrar_cambios(
    session: Session, lista_anterior: models.ListaPrecios, lista_nueva: models.ListaPrecios
) -> list[models.CambioPrecio]:
    """Persiste un `CambioPrecio` por insumo afectado, fechado en la vigencia de la lista nueva.

    Idempotente: si ese par de listas ya tiene su historial registrado, devuelve el existente en
    vez de duplicarlo. Como `crear_lista_desde_archivo`, no confirma la transacción.
    """
    registrados = list(
        session.scalars(
            select(models.CambioPrecio)
            .where(
                models.CambioPrecio.lista_anterior_id == lista_anterior.id,
                models.CambioPrecio.lista_nueva_id == lista_nueva.id,
            )
            .order_by(models.CambioPrecio.id)
        )
    )
    if registrados:
        return registrados

    cambios = [
        models.CambioPrecio(
            lista_anterior_id=lista_anterior.id,
            lista_nueva_id=lista_nueva.id,
            insumo_id=detectado.insumo.id,
            precio_anterior=detectado.precio_anterior,
            precio_nuevo=detectado.precio_nuevo,
            variacion=detectado.variacion,
            fecha=lista_nueva.fecha_vigencia,
        )
        for detectado in insumos_afectados(session, lista_anterior, lista_nueva)
    ]
    session.add_all(cambios)
    session.flush()
    return cambios


def cambios_precio(
    session: Session,
    insumo: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[models.CambioPrecio]:
    """El historial de `CambioPrecio`, en orden estable (fecha, id), con filtros opcionales.

    Única consulta del historial del sistema: la usan `api/rutas/listas.py` y
    `ui/paginas/historico.py`, que antes la reproducían por separado (hallazgo menor diferido de
    la bitácora F.1; principio DRY). `insumo` filtra por descripción exacta; `desde` y `hasta`
    acotan la fecha del cambio, ambos inclusivos.
    """
    consulta = (
        select(models.CambioPrecio)
        .join(models.Insumo)
        .order_by(models.CambioPrecio.fecha, models.CambioPrecio.id)
    )
    if insumo is not None:
        consulta = consulta.where(models.Insumo.descripcion == insumo)
    if desde is not None:
        consulta = consulta.where(models.CambioPrecio.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(models.CambioPrecio.fecha <= hasta)
    return list(session.scalars(consulta))


def _precios_de(session: Session, lista: models.ListaPrecios) -> dict[int, Decimal]:
    return {
        insumo_id: precio
        for insumo_id, precio in session.execute(
            select(models.PrecioInsumo.insumo_id, models.PrecioInsumo.precio).where(
                models.PrecioInsumo.lista_id == lista.id
            )
        ).all()
    }
