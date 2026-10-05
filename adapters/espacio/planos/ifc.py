"""Importacion de IFC a la hoja de metrajes (spec §6.6.2, RF-51, RNF-12).

Lee, con `ifcopenshell`, los espacios (`IfcSpace`: ambientes), los terminales sanitarios, de
datos, de tomacorriente y de iluminacion (puntos) y los tableros (fuentes de electricidad).
Las clases se fijan por esquema (`CLASES_POR_ESQUEMA`) y se comprueban contra el propio
esquema de ifcopenshell en las pruebas; ninguna se supone:

* ambiente: `IfcSpace` (IFC4 e IFC2X3).
* punto de agua fria: `IfcSanitaryTerminal` (IFC4); en IFC2X3 un `IfcFlowTerminal` de tipo
  `IfcSanitaryTerminalType`.
* punto de drenaje: `IfcWasteTerminal` (IFC4); IFC2X3 no tiene la clase y no se importa.
* punto de datos: `IfcOutlet` DATAOUTLET, TELEPHONEOUTLET o COMMUNICATIONSOUTLET (IFC4); en IFC2X3
  un `IfcFlowTerminal` de tipo `IfcOutletType` COMMUNICATIONSOUTLET.
* tomacorriente: `IfcOutlet` POWEROUTLET; en IFC2X3 `IfcOutletType` POWEROUTLET.
* iluminacion: `IfcLightFixture`; en IFC2X3 un `IfcFlowTerminal` de tipo `IfcLightFixtureType`.
* tablero (fuente de electricidad): `IfcElectricDistributionBoard`; en IFC2X3
  `IfcElectricDistributionPoint` con funcion DISTRIBUTIONBOARD, SWITCHBOARD, CONSUMERUNIT o
  MOTORCONTROLCENTRE.

Que se decide y que no: la caja de un ambiente es la de su geometria (si no es rectangular se
aproxima por su caja envolvente y se declara); su altura es la de la geometria (no queda
pendiente); un punto va al ambiente que lo contiene (un borde compartido toma el primero por
id y se declara); su cota z es sobre el piso del ambiente; el drenaje de un aparato sanitario
NO se infiere; el IFC no trae montantes, colectores, racks ni circuitos: los puntos quedan
«sin fuente» y «sin circuito» en el informe. Lo que no es de la convencion va al informe
agrupado por clase.

Los archivos de prueba son programaticos (RNF-09). Un adaptador no importa a otro: lo poco que se
necesita de `adapters/civil/ifc.py` (abrir un STEP y rechazar uno malformado) se duplica aqui.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit

from adapters.espacio.modelo import (
    TOLERANCIA,
    Ambiente,
    Coord,
    Especialidad,
    Fuente,
    Punto,
    TipoFuente,
    TipoPunto,
)
from adapters.espacio.origen import OrigenMedida, TipoOrigen
from adapters.espacio.planos.comun import (
    LIMITE_BYTES,
    Acumulador,
    decimal,
    en_una_linea,
    sin_filas,
    superficie_de,
)
from adapters.espacio.planos.informe import EstadoImportacion, ResultadoImportacion, TipoItem

__all__ = ["CLASES_POR_ESQUEMA", "LIMITE_BYTES", "ClasesIfc", "importar_ifc"]

_CABECERA_STEP = b"ISO-10303-21"
_PIE_STEP = b"END-ISO-10303-21;"

_DATOS = ("DATAOUTLET", "TELEPHONEOUTLET", "COMMUNICATIONSOUTLET")
_TOMA = ("POWEROUTLET",)
_TABLEROS_2X3 = ("DISTRIBUTIONBOARD", "SWITCHBOARD", "CONSUMERUNIT", "MOTORCONTROLCENTRE")


@dataclass(frozen=True, slots=True)
class ClasesIfc:
    """Las clases del esquema que se leen. `valores_de_tipo`: `(clase, enumeracion, valores)` de los
    valores de enumeracion que se aceptan; las pruebas los comprueban contra el esquema."""

    entidades: tuple[str, ...]
    valores_de_tipo: tuple[tuple[str, str, tuple[str, ...]], ...]


CLASES_POR_ESQUEMA: dict[str, ClasesIfc] = {
    "IFC2X3": ClasesIfc(
        entidades=(
            "IfcSpace",
            "IfcFlowTerminal",
            "IfcSanitaryTerminalType",
            "IfcOutletType",
            "IfcLightFixtureType",
            "IfcElectricDistributionPoint",
        ),
        valores_de_tipo=(
            ("IfcOutletType", "IfcOutletTypeEnum", ("COMMUNICATIONSOUTLET", "POWEROUTLET")),
            (
                "IfcElectricDistributionPoint",
                "IfcElectricDistributionPointFunctionEnum",
                _TABLEROS_2X3,
            ),
        ),
    ),
    "IFC4": ClasesIfc(
        entidades=(
            "IfcSpace",
            "IfcSanitaryTerminal",
            "IfcWasteTerminal",
            "IfcOutlet",
            "IfcLightFixture",
            "IfcElectricDistributionBoard",
        ),
        valores_de_tipo=(("IfcOutlet", "IfcOutletTypeEnum", (*_DATOS, *_TOMA)),),
    ),
}


def _esquema(modelo) -> str | None:
    nombre = str(modelo.schema).upper()
    if nombre == "IFC2X3":
        return "IFC2X3"
    return "IFC4" if nombre.startswith("IFC4") else None


def _rechazo(archivo: str, motivo: str) -> ResultadoImportacion:
    return sin_filas(
        "ifc",
        archivo,
        EstadoImportacion.RECHAZADA,
        f"{archivo}: no se pudo leer como IFC ({motivo}).",
    )


def _abrir(contenido: bytes | Path | str, nombre: str | None):
    """`(modelo, archivo, rechazo)`: el modelo ifcopenshell o el resultado de rechazo."""
    datos: bytes | None = None
    if isinstance(contenido, bytes | bytearray):
        archivo, datos = nombre or "plano.ifc", bytes(contenido)
        tamano = len(datos)
    else:
        ruta = Path(contenido)
        archivo = nombre or ruta.name
        try:
            tamano = ruta.stat().st_size
        except OSError as error:
            return None, archivo, _rechazo(archivo, en_una_linea(error))
    if tamano > LIMITE_BYTES:
        mb = Decimal(tamano) / (1024 * 1024)
        return (
            None,
            archivo,
            sin_filas(
                "ifc",
                archivo,
                EstadoImportacion.RECHAZADA,
                f"{archivo}: el archivo IFC pesa {mb:.1f} MB y supera el limite de 20 MB.",
            ),
        )
    if datos is None:
        try:
            datos = Path(contenido).read_bytes()
        except OSError as error:
            return None, archivo, _rechazo(archivo, en_una_linea(error))
    if not datos.lstrip().startswith(_CABECERA_STEP):
        return None, archivo, _rechazo(archivo, "no empieza con la cabecera STEP ISO-10303-21")
    if not datos.rstrip().endswith(_PIE_STEP):
        return None, archivo, _rechazo(archivo, "esta truncado: no cierra con END-ISO-10303-21")
    try:
        modelo = ifcopenshell.file.from_string(datos.decode("utf-8", errors="replace"))
    except Exception as error:  # noqa: BLE001 - ifcopenshell lanza tipos propios y de C++
        return None, archivo, _rechazo(archivo, f"{type(error).__name__}: {en_una_linea(error)}")
    if _esquema(modelo) is None:
        return None, archivo, _rechazo(archivo, f"el esquema {modelo.schema} no esta soportado")
    return modelo, archivo, None


@dataclass(slots=True)
class _Caja:
    """Un ambiente leido: su caja en metros, su cota de piso y su techo (mundo)."""

    ambiente: Ambiente
    piso: Decimal
    techo: Decimal


def _caja_de(espacio, ajustes) -> tuple[list[float], list[float], int] | None:
    """`(minimo, maximo, esquinas distintas en planta)` de la geometria de un espacio, en metros del
    mundo; None si no tiene geometria legible."""
    try:
        forma = ifcopenshell.geom.create_shape(ajustes, espacio)
        verts = list(forma.geometry.verts)  # `forma` debe seguir viva mientras se lee el buffer
    except Exception:  # noqa: BLE001 - la teselacion puede fallar con cualquier error de C++
        return None
    puntos = [tuple(verts[i : i + 3]) for i in range(0, len(verts) - 2, 3)]
    if not puntos:
        return None
    minimo = [min(p[k] for p in puntos) for k in range(3)]
    maximo = [max(p[k] for p in puntos) for k in range(3)]
    esquinas = {(round(p[0], 4), round(p[1], 4)) for p in puntos}
    return minimo, maximo, len(esquinas)


class _Lector:
    def __init__(self, modelo, archivo: str, esquema: str) -> None:
        self.modelo = modelo
        self.archivo = archivo
        self.esquema = esquema
        self.escala = Decimal(repr(float(ifcopenshell.util.unit.calculate_unit_scale(modelo))))
        self.acc = Acumulador("ifc", archivo)
        self.cajas: dict[str, _Caja] = {}
        self.ajenos: Counter[tuple[str, str]] = Counter()

    def _origen(self, elemento) -> OrigenMedida:
        gid = elemento.GlobalId
        origen = OrigenMedida(
            id=f"IFC-{gid}",
            tipo=TipoOrigen.IFC,
            referencia={"archivo": self.archivo, "global_id": gid},
        )
        self.acc.origenes[origen.id] = origen
        return origen

    def _ajeno(self, clase: str, tipo: str = "") -> None:
        self.ajenos[(clase, tipo)] += 1

    @staticmethod
    def _ids(elementos) -> dict[str, str]:
        """`GlobalId` -> id de la fila: el `Name` si es unico y no vacio; si no, el `GlobalId`."""
        nombres = Counter((e.Name or "").strip() for e in elementos)
        return {
            e.GlobalId: (e.Name or "").strip()
            if (e.Name or "").strip() and nombres[(e.Name or "").strip()] == 1
            else e.GlobalId
            for e in elementos
        }

    # ambientes
    def ambientes(self) -> None:
        espacios = sorted(self.modelo.by_type("IfcSpace"), key=lambda e: e.GlobalId)
        ids = self._ids(espacios)
        ajustes = ifcopenshell.geom.settings()
        ajustes.set("use-world-coords", True)
        for e in espacios:
            id_ = ids[e.GlobalId]
            caja = _caja_de(e, ajustes)
            if caja is None:
                self.acc.item(
                    TipoItem.NO_RECONOCIDO,
                    "IfcSpace",
                    f"IfcSpace {id_}: sin geometria legible; no se puede medir",
                    e.GlobalId,
                    id_,
                )
                continue
            minimo, maximo, esquinas = caja
            x0, y0, z0 = (decimal(minimo[k]) for k in range(3))
            largo, ancho, alto = (decimal(maximo[k] - minimo[k]) for k in range(3))
            if min(largo, ancho, alto) <= TOLERANCIA:
                self.acc.item(
                    TipoItem.NO_RECONOCIDO,
                    "IfcSpace",
                    f"IfcSpace {id_}: dimension nula; no se importa",
                    e.GlobalId,
                    id_,
                )
                continue
            origen = self._origen(e)
            ambiente = Ambiente(
                id=id_,
                nombre=(e.Name or id_).strip() or id_,
                x0=x0,
                y0=y0,
                largo=largo,
                ancho=ancho,
                alto=alto,
                origen_id=origen.id,
            )
            self.acc.ambientes[id_] = ambiente
            self.cajas[id_] = _Caja(ambiente, z0, z0 + alto)
            self.acc.importado("esp_ambientes", e.GlobalId, id_, "ambiente")
            if esquinas != 4:
                self.acc.item(
                    TipoItem.APROXIMADO,
                    "esp_ambientes",
                    f"{id_}: no es rectangular; se importa su caja envolvente "
                    f"({largo} x {ancho} m)",
                    e.GlobalId,
                    id_,
                )

    # elementos
    def _posicion(self, elemento) -> tuple[Decimal, Decimal, Decimal] | None:
        if getattr(elemento, "ObjectPlacement", None) is None:
            return None
        m = ifcopenshell.util.placement.get_local_placement(elemento.ObjectPlacement)
        return tuple(decimal(float(m[k][3]), self.escala) for k in range(3))

    def _ambiente_de(self, x: Decimal, y: Decimal, z: Decimal) -> list[_Caja]:
        t = TOLERANCIA
        return sorted(
            (
                c
                for c in self.cajas.values()
                if c.ambiente.x0 - t <= x <= c.ambiente.x0 + c.ambiente.largo + t
                and c.ambiente.y0 - t <= y <= c.ambiente.y0 + c.ambiente.ancho + t
                and c.piso - t <= z <= c.techo + t
            ),
            key=lambda c: c.ambiente.id,
        )

    def _clasificar(self, elemento) -> tuple[str, object] | None:
        """`('punto', TipoPunto)`, `('tablero', None)` o None si no es de la convencion."""
        clase = elemento.is_a()
        if self.esquema == "IFC4":
            return self._clasificar_ifc4(elemento, clase)
        return self._clasificar_ifc2x3(elemento, clase)

    def _clasificar_ifc4(self, elemento, clase: str):
        if clase == "IfcSanitaryTerminal":
            return "punto", TipoPunto.AGUA_FRIA
        if clase == "IfcWasteTerminal":
            return "punto", TipoPunto.DRENAJE
        if clase == "IfcLightFixture":
            return "punto", TipoPunto.ILUMINACION
        if clase == "IfcElectricDistributionBoard":
            return "tablero", None
        if clase == "IfcOutlet":
            predefinido = str(getattr(elemento, "PredefinedType", None))
            if predefinido in _DATOS:
                return "punto", TipoPunto.DATOS
            if predefinido in _TOMA:
                return "punto", TipoPunto.TOMACORRIENTE
            self._ajeno(clase, predefinido)
            return None
        return self._otro(elemento, clase)

    def _clasificar_ifc2x3(self, elemento, clase: str):
        if clase == "IfcElectricDistributionPoint":
            funcion = str(getattr(elemento, "DistributionPointFunction", None))
            if funcion in _TABLEROS_2X3:
                return "tablero", None
            self._ajeno(clase, funcion)
            return None
        if clase == "IfcFlowTerminal":
            tipo = ifcopenshell.util.element.get_type(elemento)
            nombre = tipo.is_a() if tipo is not None else "sin tipo"
            if nombre == "IfcSanitaryTerminalType":
                return "punto", TipoPunto.AGUA_FRIA
            if nombre == "IfcLightFixtureType":
                return "punto", TipoPunto.ILUMINACION
            if nombre == "IfcOutletType":
                predefinido = str(getattr(tipo, "PredefinedType", None))
                if predefinido == "COMMUNICATIONSOUTLET":
                    return "punto", TipoPunto.DATOS
                if predefinido == "POWEROUTLET":
                    return "punto", TipoPunto.TOMACORRIENTE
                self._ajeno(f"{clase} ({nombre})", predefinido)
                return None
            self._ajeno(clase, nombre)
            return None
        return self._otro(elemento, clase)

    def _otro(self, elemento, clase: str):
        self._ajeno(clase)
        return None

    def elementos(self) -> None:
        reconocidos: list[tuple[object, str, object]] = []
        for e in sorted(self.modelo.by_type("IfcElement"), key=lambda x: x.GlobalId):
            decision = self._clasificar(e)
            if decision is not None:
                reconocidos.append((e, *decision))
        puntos = [r for r in reconocidos if r[1] == "punto"]
        ids_puntos = self._ids([r[0] for r in puntos])
        ids_tableros = self._ids([r[0] for r in reconocidos if r[1] == "tablero"])
        for elemento, clase, tipo in reconocidos:
            if clase == "punto":
                self._punto(elemento, tipo, ids_puntos[elemento.GlobalId])
            else:
                self._tablero(elemento, ids_tableros[elemento.GlobalId])

    def _ubicar(self, elemento, id_: str, tabla: str):
        """`(x, y, z sobre el piso, ambiente)` o None si no se puede ubicar (con su ítem)."""
        posicion = self._posicion(elemento)
        if posicion is None:
            self.acc.item(
                TipoItem.NO_RECONOCIDO,
                tabla,
                f"{id_}: sin colocacion en el modelo; no se puede ubicar",
                elemento.GlobalId,
                id_,
            )
            return None
        x, y, z = posicion
        candidatos = self._ambiente_de(x, y, z)
        if not candidatos:
            self.acc.item(
                TipoItem.NO_RECONOCIDO,
                tabla,
                f"{id_}: queda fuera de todo ambiente",
                elemento.GlobalId,
                id_,
            )
            return None
        if len(candidatos) > 1:
            self.acc.item(
                TipoItem.APROXIMADO,
                tabla,
                f"{id_}: cae en varios ambientes ({', '.join(c.ambiente.id for c in candidatos)}); "
                f"se toma {candidatos[0].ambiente.id}",
                elemento.GlobalId,
                id_,
            )
        caja = candidatos[0]
        return x, y, (z - caja.piso).quantize(Decimal("0.0001")), caja.ambiente.id

    def _punto(self, elemento, tipo: TipoPunto, id_: str) -> None:
        ubicado = self._ubicar(elemento, id_, "esp_puntos")
        if ubicado is None:
            return
        x, y, z, ambiente = ubicado
        origen = self._origen(elemento)
        especialidad = (
            Especialidad.ELECTRICIDAD
            if tipo in (TipoPunto.TOMACORRIENTE, TipoPunto.ILUMINACION)
            else Especialidad.DATOS
            if tipo is TipoPunto.DATOS
            else Especialidad.AGUA
        )
        self.acc.puntos[id_] = Punto(
            id=id_,
            nombre=(elemento.Name or id_).strip() or id_,
            especialidad=especialidad,
            tipo=tipo,
            ambiente_id=ambiente,
            superficie=superficie_de(tipo, z),
            posicion=Coord(x, y, z),
            origen_id=origen.id,
        )
        self.acc.importado("esp_puntos", elemento.GlobalId, id_, "punto")

    def _tablero(self, elemento, id_: str) -> None:
        ubicado = self._ubicar(elemento, id_, "esp_fuentes")
        if ubicado is None:
            return
        x, y, z, ambiente = ubicado
        origen = self._origen(elemento)
        self.acc.fuentes[id_] = Fuente(
            id=id_,
            especialidad=Especialidad.ELECTRICIDAD,
            tipo=TipoFuente.TABLERO,
            ambiente_id=ambiente,
            posicion=Coord(x, y, z),
            origen_id=origen.id,
        )
        self.acc.importado("esp_fuentes", elemento.GlobalId, id_, "tablero")

    # informe de lo que falta
    def pendientes(self) -> None:
        por_tipo: dict[str, list[str]] = defaultdict(list)
        for p in self.acc.puntos.values():
            por_tipo[p.tipo.value].append(p.id)
        sin_fuente = [i for t in ("agua_fria", "drenaje", "datos") for i in por_tipo.get(t, [])]
        if sin_fuente:
            self.acc.item(
                TipoItem.PENDIENTE,
                "esp_puntos",
                f"{len(sin_fuente)} punto(s) de agua o datos sin fuente: el IFC no trae montante, "
                "colector ni rack; se asignan en la hoja",
            )
        sin_circuito = [i for t in ("tomacorriente", "iluminacion") for i in por_tipo.get(t, [])]
        if sin_circuito:
            self.acc.item(
                TipoItem.PENDIENTE,
                "esp_puntos",
                f"{len(sin_circuito)} punto(s) electricos sin circuito: el IFC no los trae; "
                "se declaran en la hoja",
            )
        sanitarios = [
            e
            for e in self.modelo.by_type("IfcElement")
            if self.esquema == "IFC4" and e.is_a() == "IfcSanitaryTerminal"
        ]
        if sanitarios:
            self.acc.item(
                TipoItem.PENDIENTE,
                "esp_puntos",
                f"{len(sanitarios)} aparato(s) sanitario(s): se importo su punto de agua fria; el "
                "drenaje no se infiere, se agrega en la hoja",
            )
        for (clase, tipo), n in sorted(self.ajenos.items()):
            detalle = f" {tipo}" if tipo else ""
            self.acc.item(
                TipoItem.NO_RECONOCIDO,
                clase.split(" ")[0],
                f"{clase}{detalle}: {n} {'elemento' if n == 1 else 'elementos'} fuera de la "
                "convencion; no se importan",
            )


def importar_ifc(
    contenido: bytes | Path | str, *, nombre: str | None = None
) -> ResultadoImportacion:
    """Importa un IFC (IFC2X3, IFC4 o IFC4X3) a filas de la hoja con su informe.

    `contenido`: los bytes del archivo o su ruta. `nombre`: el nombre de archivo que cita el origen
    (por defecto el de la ruta, o `plano.ifc`).

    Nunca lanza por un archivo malo: devuelve un resultado `RECHAZADA` (malformado, truncado,
    esquema no soportado, mas de 20 MB) con su mensaje y sin filas."""
    modelo, archivo, rechazo = _abrir(contenido, nombre)
    if rechazo is not None:
        return rechazo
    lector = _Lector(modelo, archivo, _esquema(modelo))
    lector.ambientes()
    lector.elementos()
    lector.pendientes()
    acc = lector.acc
    if not (acc.ambientes or acc.fuentes or acc.puntos):
        return acc.resultado(
            mensaje=f"{archivo}: el IFC no trae espacios, terminales ni tableros de la convencion; "
            "no se importo ninguna fila."
        )
    return acc.resultado()
