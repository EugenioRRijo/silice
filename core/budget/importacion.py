"""RF‑24 y UC‑05, pasos 1 y 2: importar el presupuesto tabular de un tercero para auditarlo.

El auditor recibe un presupuesto que el sistema no elaboró. `leer_presupuesto_tabular` lo
reconstruye en memoria, **conservando las unidades que escribió su autor** (RF‑24): la unidad de
cada renglón se guarda también en `especificaciones[CLAVE_UNIDAD_ORIGINAL]`, la convención que
lee la regla R3, así que «mts» llega intacto al hallazgo. `importar_presupuesto` además lo audita
(principio 7 de NORMAS.md §2) y lo persiste con su informe, para que las rutas que ya existen lo
sirvan (`GET /presupuestos/{codigo}/informe` y `…/excel`). Expediente C6.4 de
`docs/bitacora/2026-09-29-C6-expedientes.md`.

**Formato.** Un solo XLSX; este módulo es la fuente única de sus hojas y columnas:

- `Datos` (`clave`, `valor`): `codigo`, `fecha` (ISO), `moneda`, `dominio`, `fcas`,
  `bono_alimentacion`, `administracion` y `utilidad`, todas obligatorias.
- `Presupuesto`: un renglón por cantidad de obra. `parametros` y `especificaciones` son objetos
  JSON; con `regla` el origen es `REGLA` y sin ella `MANUAL` (R1 advierte la trazabilidad ausente,
  UC‑05 2b); sin `origen_id`, el origen es `<archivo>:Presupuesto:<fila>`.
- `APU`: una fila por partida, con su rendimiento en unidades de partida por día.
- `Insumos`: las líneas de cada APU. `tipo` con las grafías de UC‑02; `unidad` solo en los
  materiales; `depreciacion` solo en los equipos; `modalidad` solo en la mano de obra, jornal por
  defecto (D9); en la mano de obra, `precio` es el sueldo.
- `Curva` (opcional): el plan de trabajo del autor, tal cual. Sin ella R2 y R7 se declaran no
  aplicables (UC‑05 2a).

Todo número se lee como texto y se convierte a `Decimal` (NORMAS.md §2.3), con la misma lectura de
XLSX celda por celda que las listas de precios (`core.catalog.precios`). No es el formato del libro
que escribe `exportar_excel`: aquel presenta el presupuesto, este lo describe completo.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget.curva import con_curva
from core.budget.persistencia import guardar_presupuesto
from core.budget.presupuesto import ResultadoElaboracion, generar_presupuesto
from core.catalog import Catalogo, CatalogoIncompleto
from core.catalog.precios import PRIMERA_FILA_DE_DATOS, SUFIJOS_EXCEL, leer_tabla, tipo_insumo
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ModalidadManoObra,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.presupuesto import Presupuesto, PuntoCurva
from core.contracts.verificacion import ReglaVerificacion
from core.verification import REGLAS, auditar
from core.verification.directivas import CLAVE_UNIDAD_ORIGINAL

__all__ = [
    "COLUMNAS_APU",
    "COLUMNAS_CURVA",
    "COLUMNAS_DATOS",
    "COLUMNAS_INSUMOS",
    "COLUMNAS_PRESUPUESTO",
    "CLAVES_DATOS",
    "HOJA_APU",
    "HOJA_CURVA",
    "HOJA_DATOS",
    "HOJA_INSUMOS",
    "HOJA_PRESUPUESTO",
    "PresupuestoImportado",
    "importar_presupuesto",
    "leer_presupuesto_tabular",
]

HOJA_DATOS = "Datos"
HOJA_PRESUPUESTO = "Presupuesto"
HOJA_APU = "APU"
HOJA_INSUMOS = "Insumos"
HOJA_CURVA = "Curva"

COLUMNAS_DATOS = ("clave", "valor")
COLUMNAS_PRESUPUESTO = (
    "codigo_partida",
    "descripcion",
    "unidad",
    "cantidad",
    "origen_id",
    "regla",
    "parametros",
    "especificaciones",
)
COLUMNAS_APU = ("codigo_partida", "descripcion", "unidad", "rendimiento")
COLUMNAS_INSUMOS = (
    "codigo_partida",
    "tipo",
    "insumo",
    "unidad",
    "cantidad",
    "precio",
    "depreciacion",
    "modalidad",
)
COLUMNAS_CURVA = ("periodo", "monto", "acumulado")

#: Los cuatro parámetros de costo, derivados del contrato: la hoja `Datos` no los repite.
_PARAMETROS = tuple(campo.name for campo in fields(ParametrosCosto))

#: Claves obligatorias de la hoja `Datos`.
CLAVES_DATOS = ("codigo", "fecha", "moneda", "dominio", *_PARAMETROS)

#: Sufijos del único formato que se importa: un libro de hojas (el CSV no las tiene).
SUFIJOS_IMPORTABLES = SUFIJOS_EXCEL


@dataclass(frozen=True, slots=True)
class PresupuestoImportado:
    """Lo que se lee del archivo del tercero: el presupuesto valorado con su curva (si la trae),
    los parámetros de costo con que se valoró, sus APU por código y su dominio."""

    presupuesto: Presupuesto
    parametros: ParametrosCosto
    composiciones: Mapping[str, ComposicionAPU]
    dominio: Dominio


def leer_presupuesto_tabular(ruta: Path) -> PresupuestoImportado:
    """Reconstruye en memoria el presupuesto del tercero (UC‑05, paso 2). No toca la base.

    El presupuesto se valora con el motor (`generar_presupuesto`) sobre los APU y los parámetros del
    propio archivo, y lleva la curva del autor tal cual, para que R2 y R7 la auditen. Todo error
    de forma es `ValueError` con el archivo, la hoja y, si corresponde, la fila: hoja o columna
    ausente, clave de `Datos` ausente, número o fecha ilegibles, partida repetida en `APU`,
    insumo de una partida sin APU, hoja `Presupuesto` sin renglones o renglón del presupuesto
    cuya partida no tiene APU.
    """
    if ruta.suffix.lower() not in SUFIJOS_IMPORTABLES:
        raise ValueError(
            f"{ruta.name}: el presupuesto de un tercero se importa de un libro "
            f"{' o '.join(SUFIJOS_IMPORTABLES)} con las hojas {HOJA_DATOS}, {HOJA_PRESUPUESTO}, "
            f"{HOJA_APU}, {HOJA_INSUMOS} y, opcional, {HOJA_CURVA}"
        )
    datos = _leer_datos(ruta)
    dominio = _dominio(datos, ruta)
    parametros = ParametrosCosto(
        **{clave: _decimal(datos[clave], ruta, HOJA_DATOS, None, clave) for clave in _PARAMETROS}
    )
    composiciones = _leer_composiciones(ruta)
    items = _leer_items(ruta, dominio, composiciones)
    presupuesto = generar_presupuesto(
        items,
        composiciones,
        parametros,
        codigo=datos["codigo"],
        fecha=_fecha(datos["fecha"], ruta),
        moneda=datos["moneda"],
    )
    if HOJA_CURVA in _hojas(ruta):
        presupuesto = con_curva(presupuesto, _leer_curva(ruta))
    return PresupuestoImportado(
        presupuesto=presupuesto,
        parametros=parametros,
        composiciones=composiciones,
        dominio=dominio,
    )


def importar_presupuesto(
    session: Session,
    ruta: Path,
    proyecto: models.Proyecto,
    reglas: Sequence[ReglaVerificacion] = REGLAS,
    usuario: str | None = None,
) -> ResultadoElaboracion:
    """UC‑05 con el archivo de un tercero: lee, audita siempre y persiste con su informe.

    Antes de escribir nada comprueba que ningún código de partida del archivo esté ya en el
    catálogo (`ValueError`: el APU del tercero no sustituye ni se mezcla con el del catálogo; el
    caso necesita códigos propios), que el proyecto no tenga ya un presupuesto con ese código y
    que la moneda del archivo sea la de la lista vigente a su fecha, si la hay (`ValueError`: la
    lista importada copia esos precios y no mezcla monedas). Luego crea la lista «Importada:
    <archivo>», vigente a la fecha del presupuesto, que copia los precios de la lista vigente a
    esa fecha si la hay (así sigue valorando el catálogo completo, como
    `crear_lista_desde_archivo`); carga cada APU del tercero con esa lista
    (`Catalogo.cargar_composicion`) y guarda el presupuesto con su informe
    (`guardar_presupuesto`), que `cargar_elaboracion` recarga igual. `reglas` son las que audita la
    importación (las siete por defecto); los hallazgos de las que no son de `REGLAS` se guardan con
    el informe y la recarga los vuelve a declarar (SF‑E1, RF‑62). No confirma la transacción.
    """
    reglas = tuple(reglas)
    importado = leer_presupuesto_tabular(ruta)
    presupuesto = importado.presupuesto
    informe = auditar(presupuesto, reglas)

    catalogo = Catalogo(session)
    existentes = sorted(
        codigo
        for codigo in importado.composiciones
        if session.scalar(select(models.Partida.id).where(models.Partida.codigo == codigo))
        is not None
    )
    if existentes:
        raise ValueError(
            f"{ruta.name}: las partidas {', '.join(existentes)} ya estan en el catalogo; el "
            "presupuesto de un tercero se importa con codigos de partida propios"
        )
    repetido = session.scalar(
        select(models.Presupuesto.id).where(
            models.Presupuesto.proyecto_id == proyecto.id,
            models.Presupuesto.codigo == presupuesto.codigo,
        )
    )
    if repetido is not None:
        raise ValueError(
            f"el proyecto {proyecto.nombre!r} ya tiene un presupuesto {presupuesto.codigo!r}"
        )

    try:
        vigente: models.ListaPrecios | None = catalogo.lista_vigente(presupuesto.fecha)
    except CatalogoIncompleto:
        vigente = None
    if vigente is not None and vigente.moneda != presupuesto.moneda:
        raise ValueError(
            f"{ruta.name}: el presupuesto esta en {presupuesto.moneda} y la lista vigente al "
            f"{presupuesto.fecha} ({vigente.nombre!r}) en {vigente.moneda}; la lista importada "
            "copia esos precios y no mezcla monedas"
        )

    lista = _lista_importada(session, vigente, ruta, presupuesto)
    condiciones = f"importado de {ruta.name} (presupuesto de un tercero, UC-05)"
    for composicion in importado.composiciones.values():
        catalogo.cargar_composicion(
            composicion, lista, importado.dominio, presupuesto.fecha, condiciones
        )
    guardar_presupuesto(
        session,
        presupuesto,
        informe,
        proyecto=proyecto,
        lista=lista,
        parametros=importado.parametros,
        usuario=usuario,
    )
    return ResultadoElaboracion(presupuesto=presupuesto, informe=informe)


def _lista_importada(
    session: Session,
    vigente: models.ListaPrecios | None,
    ruta: Path,
    presupuesto: Presupuesto,
) -> models.ListaPrecios:
    lista = models.ListaPrecios(
        nombre=f"Importada: {ruta.name}",
        moneda=presupuesto.moneda,
        fecha_vigencia=presupuesto.fecha,
        origen=ruta.name,
    )
    session.add(lista)
    session.flush()
    if vigente is not None:
        session.add_all(
            models.PrecioInsumo(lista_id=lista.id, insumo_id=precio.insumo_id, precio=precio.precio)
            for precio in vigente.precios
        )
        session.flush()
    return lista


# ---------------------------------------------------------------------------------------------
# Lectura de cada hoja
# ---------------------------------------------------------------------------------------------


def _hojas(ruta: Path) -> list[str]:
    libro = openpyxl.load_workbook(ruta, read_only=True)
    try:
        return list(libro.sheetnames)
    finally:
        libro.close()


def _filas(ruta: Path, hoja: str, columnas: tuple[str, ...]) -> list[tuple[int, dict[str, str]]]:
    """Las filas de la hoja con su número, como texto; `ValueError` si falta una columna."""
    tabla = leer_tabla(ruta, hoja)
    faltantes = [columna for columna in columnas if columna not in tabla.columns]
    if faltantes:
        raise ValueError(
            f"{ruta.name}, hoja {hoja}: faltan las columnas {', '.join(faltantes)}; "
            f"se esperan {', '.join(columnas)}"
        )
    return [
        (numero, {columna: str(fila[columna]).strip() for columna in columnas})
        for numero, fila in enumerate(tabla.to_dict("records"), start=PRIMERA_FILA_DE_DATOS)
    ]


def _leer_datos(ruta: Path) -> dict[str, str]:
    datos = {
        fila["clave"].lower(): fila["valor"] for _, fila in _filas(ruta, HOJA_DATOS, COLUMNAS_DATOS)
    }
    for clave in CLAVES_DATOS:
        if not datos.get(clave):
            raise ValueError(f"{ruta.name}, hoja {HOJA_DATOS}: falta la clave {clave}")
    return datos


def _dominio(datos: Mapping[str, str], ruta: Path) -> Dominio:
    try:
        return Dominio(datos["dominio"].lower())
    except ValueError:
        esperados = ", ".join(dominio.value for dominio in Dominio)
        raise ValueError(
            f"{ruta.name}, hoja {HOJA_DATOS}: dominio {datos['dominio']!r} desconocido; se espera "
            f"uno de {esperados}"
        ) from None


def _fecha(texto: str, ruta: Path) -> date:
    try:
        return date.fromisoformat(texto[:10])
    except ValueError:
        raise ValueError(
            f"{ruta.name}, hoja {HOJA_DATOS}: la fecha {texto!r} no es una fecha ISO (AAAA-MM-DD)"
        ) from None


def _leer_composiciones(ruta: Path) -> dict[str, ComposicionAPU]:
    cabeceras: dict[str, tuple[int, dict[str, str]]] = {}
    for numero, fila in _filas(ruta, HOJA_APU, COLUMNAS_APU):
        codigo = fila["codigo_partida"]
        if not codigo:
            raise ValueError(f"{ruta.name}, hoja {HOJA_APU}, fila {numero}: falta codigo_partida")
        if codigo in cabeceras:
            raise ValueError(
                f"{ruta.name}, hoja {HOJA_APU}, fila {numero}: la partida {codigo} ya tiene APU "
                f"en la fila {cabeceras[codigo][0]}"
            )
        cabeceras[codigo] = (numero, fila)

    lineas: dict[str, dict[str, list]] = {
        codigo: {"materiales": [], "equipos": [], "mano_obra": []} for codigo in cabeceras
    }
    for numero, fila in _filas(ruta, HOJA_INSUMOS, COLUMNAS_INSUMOS):
        codigo = fila["codigo_partida"]
        if codigo not in lineas:
            raise ValueError(
                f"{ruta.name}, hoja {HOJA_INSUMOS}, fila {numero}: la partida {codigo!r} no "
                f"tiene APU en la hoja {HOJA_APU}"
            )
        tipo, linea = _linea(fila, numero, ruta)
        lineas[codigo][tipo].append(linea)

    composiciones: dict[str, ComposicionAPU] = {}
    for codigo, (numero, fila) in cabeceras.items():
        try:
            composiciones[codigo] = ComposicionAPU(
                codigo_partida=codigo,
                descripcion=fila["descripcion"],
                unidad=fila["unidad"],
                rendimiento=_decimal(fila["rendimiento"], ruta, HOJA_APU, numero, "rendimiento"),
                materiales=tuple(lineas[codigo]["materiales"]),
                equipos=tuple(lineas[codigo]["equipos"]),
                mano_obra=tuple(lineas[codigo]["mano_obra"]),
            )
        except ValueError as error:
            raise ValueError(f"{ruta.name}, hoja {HOJA_APU}, fila {numero}: {error}") from error
    return composiciones


def _linea(
    fila: Mapping[str, str], numero: int, ruta: Path
) -> tuple[str, LineaMaterial | LineaEquipo | LineaManoObra]:
    """Una fila de `Insumos` como línea del contrato, con el nombre de la tupla donde va."""
    try:
        tipo = tipo_insumo(fila["tipo"])
    except ValueError as error:
        raise ValueError(f"{ruta.name}, hoja {HOJA_INSUMOS}, fila {numero}: {error}") from None
    cantidad = _decimal(fila["cantidad"], ruta, HOJA_INSUMOS, numero, "cantidad")
    precio = _decimal(fila["precio"], ruta, HOJA_INSUMOS, numero, "precio")
    try:
        if tipo is models.TipoInsumo.MATERIAL:
            return "materiales", LineaMaterial(
                descripcion=fila["insumo"], unidad=fila["unidad"], cantidad=cantidad, precio=precio
            )
        if tipo is models.TipoInsumo.EQUIPO:
            depreciacion = _decimal(
                fila["depreciacion"], ruta, HOJA_INSUMOS, numero, "depreciacion"
            )
            return "equipos", LineaEquipo(
                descripcion=fila["insumo"],
                cantidad=cantidad,
                precio=precio,
                depreciacion=depreciacion,
            )
        modalidad = ModalidadManoObra(fila["modalidad"].lower() or ModalidadManoObra.JORNAL)
        return "mano_obra", LineaManoObra(
            descripcion=fila["insumo"], cantidad=cantidad, sueldo=precio, modalidad=modalidad
        )
    except ValueError as error:
        raise ValueError(f"{ruta.name}, hoja {HOJA_INSUMOS}, fila {numero}: {error}") from error


def _leer_items(
    ruta: Path, dominio: Dominio, composiciones: Mapping[str, ComposicionAPU]
) -> list[ItemComputo]:
    items: list[ItemComputo] = []
    for numero, fila in _filas(ruta, HOJA_PRESUPUESTO, COLUMNAS_PRESUPUESTO):
        codigo = fila["codigo_partida"]
        if codigo not in composiciones:
            raise ValueError(
                f"{ruta.name}, hoja {HOJA_PRESUPUESTO}, fila {numero}: la partida {codigo!r} no "
                f"tiene APU en la hoja {HOJA_APU}"
            )
        regla = fila["regla"] or None
        cantidad = _decimal(fila["cantidad"], ruta, HOJA_PRESUPUESTO, numero, "cantidad")
        parametros = {
            clave: _decimal(str(valor), ruta, HOJA_PRESUPUESTO, numero, clave)
            for clave, valor in _json(fila["parametros"], ruta, numero, "parametros").items()
        }
        especificaciones = {
            **_json(fila["especificaciones"], ruta, numero, "especificaciones"),
            CLAVE_UNIDAD_ORIGINAL: fila["unidad"],  # la unidad que escribió el autor (RF‑24)
        }
        try:
            items.append(
                ItemComputo(
                    codigo_partida=codigo,
                    descripcion=fila["descripcion"],
                    unidad=fila["unidad"],
                    cantidad=cantidad,
                    origen_id=fila["origen_id"] or f"{ruta.name}:{HOJA_PRESUPUESTO}:{numero}",
                    origen_tipo=OrigenTipo.REGLA if regla else OrigenTipo.MANUAL,
                    dominio=dominio,
                    regla=regla,
                    parametros=parametros,
                    especificaciones={clave: str(v) for clave, v in especificaciones.items()},
                )
            )
        except ValueError as error:
            raise ValueError(
                f"{ruta.name}, hoja {HOJA_PRESUPUESTO}, fila {numero}: {error}"
            ) from error
    if not items:
        raise ValueError(
            f"{ruta.name}, hoja {HOJA_PRESUPUESTO}: no trae renglones; un presupuesto sin "
            "cantidades no se audita"
        )
    return items


def _leer_curva(ruta: Path) -> tuple[PuntoCurva, ...]:
    return tuple(
        PuntoCurva(
            periodo=fila["periodo"],
            monto=_decimal(fila["monto"], ruta, HOJA_CURVA, numero, "monto"),
            acumulado=_decimal(fila["acumulado"], ruta, HOJA_CURVA, numero, "acumulado"),
        )
        for numero, fila in _filas(ruta, HOJA_CURVA, COLUMNAS_CURVA)
    )


def _json(texto: str, ruta: Path, numero: int, columna: str) -> dict[str, object]:
    if not texto:
        return {}
    try:
        valor = json.loads(texto, parse_float=Decimal, parse_int=Decimal)
    except json.JSONDecodeError:
        valor = None
    if not isinstance(valor, dict):
        raise ValueError(
            f"{ruta.name}, hoja {HOJA_PRESUPUESTO}, fila {numero}: la columna {columna} debe ser "
            "un objeto JSON"
        )
    return valor


def _decimal(texto: str, ruta: Path, hoja: str, numero: int | None, columna: str) -> Decimal:
    donde = f"{ruta.name}, hoja {hoja}" + (f", fila {numero}" if numero is not None else "")
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ValueError(f"{donde}: {columna} {texto!r} no es un numero decimal") from None
    if not valor.is_finite():
        raise ValueError(f"{donde}: {columna} {texto!r} no es un numero finito")
    return valor
