"""Importacion de DXF a la hoja de metrajes (spec §6.6.1, RF-50, RNF-12).

Convencion de capas (los nombres no distinguen mayusculas):

| Capa | Entidad | Se convierte en |
|---|---|---|
| `AMBIENTES` | polilinea cerrada con un texto adentro (su nombre) | ambiente |
| `FTE-AGUA`, `FTE-DRENAJE`, `FTE-DATOS`, `FTE-ELEC` | bloque insertado | fuente |
| `PTO-AGUA`, `PTO-DRENAJE`, `PTO-DATOS`, `PTO-TOMA`, `PTO-LUZ` | bloque con atributos | punto |
| `REC-<especialidad>` | polilinea abierta | recorrido declarado (opcional) |

Atributos de bloque (texto, en las unidades del dibujo cuando son longitudes; coma o punto decimal):
`ID` (el `id` de la fila; sin el, `<capa>-<handle>`), `ALTURA` (cota z del punto o de la fuente),
`DIAMETRO`, `CALIBRE` y `CIRCUITO` (la convencion del spec) y tres EXTENSIONES opcionales que la
convencion no nombra pero sin las cuales el DXF no puede reproducir la hoja de OF-001 (RS-SF5-3):
`CATEGORIA` (datos), `LLAVE` (`si`, agua fria), `SUPERFICIE` (`pared`, `techo` o `piso`) y
`AMBIENTE` (el nombre del ambiente, para un punto que cae en el borde de dos). Los ambientes
comparten texto e `id`.

Que se decide y que no: el nombre del texto es el `id` del ambiente; un no rectangular se
importa por su caja envolvente y se declara; la altura del ambiente queda PENDIENTE (alto
provisional, R8 la marca); la fuente de un punto es la compatible de su ambiente o la mas
cercana; la unidad sale de `$INSUNITS` y si falta la importacion se DETIENE y pide la unidad.
Lo que no sigue la convencion va al informe, no a la hoja. Un archivo malformado o de mas de
20 MB se rechaza con un mensaje, sin traza (RNF-12).
"""

from __future__ import annotations

import tempfile
from collections import Counter, defaultdict
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import ezdxf

from adapters.espacio.modelo import (
    TOLERANCIA,
    Ambiente,
    Circuito,
    Coord,
    Especialidad,
    Fuente,
    ModoRecorrido,
    Punto,
    Recorrido,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoPunto,
    Tramo,
)
from adapters.espacio.origen import OrigenMedida, TipoOrigen
from adapters.espacio.planos.comun import (
    CALIBRE_PENDIENTE,
    CONDUCTORES_POR_DEFECTO,
    LIMITE_BYTES,
    PUNTOS_MAXIMOS_POR_DEFECTO,
    Acumulador,
    contiene_en_planta,
    decimal,
    digitos_finales,
    en_una_linea,
    fuente_para,
    numero,
    sin_filas,
    superficie_de,
)
from adapters.espacio.planos.informe import EstadoImportacion, ResultadoImportacion, TipoItem
from adapters.espacio.reglas import ALTO_PROVISIONAL, ALTURA_PENDIENTE, ORIGEN_ALTURA_PENDIENTE

__all__ = ["LIMITE_BYTES", "importar_dxf"]

#: `$INSUNITS` (codigo DXF) -> metros por unidad. 0 es «sin unidad»; los demas no se soportan.
_METROS_POR_CODIGO = {
    1: Decimal("0.0254"),  # pulgada
    2: Decimal("0.3048"),  # pie
    4: Decimal("0.001"),  # milimetro
    5: Decimal("0.01"),  # centimetro
    6: Decimal(1),  # metro
    14: Decimal("0.1"),  # decimetro
}
#: Unidades que el usuario puede indicar cuando el plano no la declara.
_METROS_POR_NOMBRE = {
    "m": Decimal(1),
    "metro": Decimal(1),
    "metros": Decimal(1),
    "cm": Decimal("0.01"),
    "centimetro": Decimal("0.01"),
    "centimetros": Decimal("0.01"),
    "mm": Decimal("0.001"),
    "milimetro": Decimal("0.001"),
    "milimetros": Decimal("0.001"),
    "dm": Decimal("0.1"),
    "in": Decimal("0.0254"),
    "pulgada": Decimal("0.0254"),
    "pulgadas": Decimal("0.0254"),
    "ft": Decimal("0.3048"),
    "pie": Decimal("0.3048"),
    "pies": Decimal("0.3048"),
}
_UNIDADES_ACEPTADAS = "m, cm, mm, dm, in, ft"

_FUENTES = {
    "AGUA": (Especialidad.AGUA, TipoFuente.MONTANTE_AGUA),
    "DRENAJE": (Especialidad.AGUA, TipoFuente.COLECTOR_DRENAJE),
    "DATOS": (Especialidad.DATOS, TipoFuente.RACK),
    "ELEC": (Especialidad.ELECTRICIDAD, TipoFuente.TABLERO),
}
_PUNTOS = {
    "AGUA": (Especialidad.AGUA, TipoPunto.AGUA_FRIA),
    "DRENAJE": (Especialidad.AGUA, TipoPunto.DRENAJE),
    "DATOS": (Especialidad.DATOS, TipoPunto.DATOS),
    "TOMA": (Especialidad.ELECTRICIDAD, TipoPunto.TOMACORRIENTE),
    "LUZ": (Especialidad.ELECTRICIDAD, TipoPunto.ILUMINACION),
}
_RECORRIDOS = {
    "AGUA": Especialidad.AGUA,
    "DATOS": Especialidad.DATOS,
    "ELEC": Especialidad.ELECTRICIDAD,
    "ELECTRICIDAD": Especialidad.ELECTRICIDAD,
}
_SUPERFICIES = {s.value: s for s in SuperficiePunto}
_ENTIDADES_REC = ("LWPOLYLINE", "POLYLINE", "LINE")


# --- lectura del archivo --------------------------------------------------------------------------


def _rechazo(archivo: str, motivo: str) -> ResultadoImportacion:
    return sin_filas(
        "dxf",
        archivo,
        EstadoImportacion.RECHAZADA,
        f"{archivo}: no se pudo leer como DXF ({motivo}).",
    )


def _demasiado_grande(archivo: str, tamano: int) -> ResultadoImportacion:
    mb = Decimal(tamano) / (1024 * 1024)
    return sin_filas(
        "dxf",
        archivo,
        EstadoImportacion.RECHAZADA,
        f"{archivo}: el archivo DXF pesa {mb:.1f} MB y supera el limite de 20 MB.",
    )


def _abrir(ruta: Path):
    try:
        return ezdxf.readfile(ruta), ""
    except Exception as error:  # noqa: BLE001 - un lector de CAD puede lanzar cualquier cosa
        return None, f"{type(error).__name__}: {en_una_linea(error)}"


def _leer(contenido: bytes | Path | str, nombre: str | None):
    """`(documento, archivo, rechazo)`: el documento ezdxf o el resultado de rechazo."""
    if isinstance(contenido, bytes | bytearray):
        archivo = nombre or "plano.dxf"
        if len(contenido) > LIMITE_BYTES:
            return None, archivo, _demasiado_grande(archivo, len(contenido))
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "plano.dxf"
            ruta.write_bytes(bytes(contenido))
            doc, motivo = _abrir(ruta)
    else:
        ruta = Path(contenido)
        archivo = nombre or ruta.name
        try:
            tamano = ruta.stat().st_size
        except OSError as error:
            return None, archivo, _rechazo(archivo, en_una_linea(error))
        if tamano > LIMITE_BYTES:
            return None, archivo, _demasiado_grande(archivo, tamano)
        doc, motivo = _abrir(ruta)
    if doc is None:
        return None, archivo, _rechazo(archivo, motivo)
    return doc, archivo, None


def _factor(doc, unidades: str | None) -> tuple[Decimal | None, int, str]:
    """`(metros por unidad, codigo $INSUNITS, motivo si no hay)`."""
    codigo = int(doc.header.get("$INSUNITS", 0) or 0)
    if codigo in _METROS_POR_CODIGO:
        return _METROS_POR_CODIGO[codigo], codigo, ""
    if unidades is not None:
        return _METROS_POR_NOMBRE.get(unidades.strip().lower()), codigo, "indicada"
    return None, codigo, "falta"


# --- geometria de entidades --------------------


def _geometria(e) -> tuple[list[tuple[float, float, float]], bool, bool, bool]:
    """`(vertices, cerrada, con_arcos, es_3d)` de una polilinea o una linea."""
    tipo = e.dxftype()
    if tipo == "LWPOLYLINE":
        puntos = list(e.get_points("xyb"))
        z = float(e.dxf.elevation) if e.dxf.hasattr("elevation") else 0.0
        vertices = [(p[0], p[1], z) for p in puntos]
        arcos = any(abs(p[2]) > 1e-9 for p in puntos)
        return vertices, bool(e.closed), arcos, False
    if tipo == "POLYLINE":
        vertices = [(v.dxf.location.x, v.dxf.location.y, v.dxf.location.z) for v in e.vertices]
        return vertices, bool(e.is_closed), False, bool(e.is_3d_polyline)
    a, b = e.dxf.start, e.dxf.end  # LINE
    return [(a.x, a.y, a.z), (b.x, b.y, b.z)], False, False, True


def _cerrada(vertices, cerrada_marcada: bool) -> list[tuple[float, float, float]]:
    """Los vertices sin repetir el ultimo si coincide con el primero; [] si no es un contorno."""
    if len(vertices) >= 4 and vertices[0] == vertices[-1]:
        cerrada_marcada, vertices = True, vertices[:-1]
    return vertices if cerrada_marcada and len(vertices) >= 3 else []


def _dentro(poligono: list[tuple[float, float, float]], x: float, y: float) -> bool:
    """Punto en poligono por rayos (planta). El borde cuenta por la tolerancia de quien llama."""
    dentro = False
    j = len(poligono) - 1
    for i, (xi, yi, _) in enumerate(poligono):
        xj, yj, _ = poligono[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def _area(puntos: list[tuple[Decimal, Decimal]]) -> Decimal:
    n = len(puntos)
    doble = sum(
        (puntos[i][0] * puntos[(i + 1) % n][1] - puntos[(i + 1) % n][0] * puntos[i][1])
        for i in range(n)
    )
    return abs(doble) / 2


def _texto(e) -> str:
    bruto = e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text
    return " ".join(str(bruto).split())


def _atributos(e) -> dict[str, str]:
    return {a.dxf.tag.strip().upper(): (a.dxf.text or "").strip() for a in e.attribs}


# --- el lector ----------------------


class _Lector:
    def __init__(self, doc, archivo: str, factor: Decimal) -> None:
        self.doc = doc
        self.factor = factor
        self.acc = Acumulador("dxf", archivo)
        self.archivo = archivo
        self.calibre_de: dict[str, str] = {}
        self.circuito_de: dict[str, str] = {}

    # utilidades
    def _m(self, valor: float) -> Decimal:
        return decimal(valor, self.factor)

    def _origen(self, e, capa: str, extra: tuple[tuple[str, str], ...] = ()) -> OrigenMedida:
        handle = e.dxf.handle
        referencia = {"archivo": self.archivo, "capa": e.dxf.layer or capa, "handle": handle}
        referencia.update(dict(extra))
        origen = OrigenMedida(id=f"DXF-{handle}", tipo=TipoOrigen.DXF, referencia=referencia)
        self.acc.origenes[origen.id] = origen
        return origen

    def _no_reconocido(self, tabla: str, e, mensaje: str, fila: str = "") -> None:
        self.acc.item(TipoItem.NO_RECONOCIDO, tabla, mensaje, e.dxf.handle, fila)

    def _ambiente_de(self, atributos, x: Decimal, y: Decimal, tabla: str, e, fila: str):
        elegido = atributos.get("AMBIENTE")
        if elegido:
            if elegido in self.acc.ambientes:
                return elegido
            self._no_reconocido(
                tabla, e, f"{fila}: el ambiente {elegido!r} del atributo AMBIENTE no existe", fila
            )
            return None
        candidatos = sorted(
            a.id for a in self.acc.ambientes.values() if contiene_en_planta(a, x, y)
        )
        if not candidatos:
            self._no_reconocido(tabla, e, f"{fila}: queda fuera de todo ambiente", fila)
            return None
        if len(candidatos) > 1:
            self.acc.item(
                TipoItem.APROXIMADO,
                tabla,
                f"{fila}: cae en varios ambientes ({', '.join(candidatos)}); se toma "
                f"{candidatos[0]} (el atributo AMBIENTE lo decide)",
                e.dxf.handle,
                fila,
            )
        return candidatos[0]

    # ambientes
    def ambientes(self, poligonos, textos) -> None:
        usados: set[str] = set()
        for e in poligonos:
            vertices, cerrada, arcos, _ = _geometria(e)
            contorno = _cerrada(vertices, cerrada)
            if not contorno:
                self._no_reconocido(
                    "AMBIENTES", e, "polilinea abierta o sin area: no es un ambiente"
                )
                continue
            adentro = [t for t in textos if _dentro(contorno, t[1], t[2])]
            usados.update(t[3] for t in adentro)
            nombres = sorted({t[0] for t in adentro if t[0]})
            if not nombres:
                self._no_reconocido("AMBIENTES", e, "ambiente sin texto adentro: no tiene nombre")
                continue
            if len(nombres) > 1:
                self._no_reconocido(
                    "AMBIENTES",
                    e,
                    f"ambiente con varios textos adentro ({', '.join(nombres)}): no se adivina "
                    "cual es el nombre",
                )
                continue
            self._ambiente(e, nombres[0], contorno, arcos)
        for texto, _, _, handle in textos:
            if handle not in usados:
                self.acc.item(
                    TipoItem.NO_RECONOCIDO,
                    "AMBIENTES",
                    f"texto {texto!r} fuera de todo ambiente",
                    handle,
                )

    def _ambiente(self, e, nombre: str, contorno, arcos: bool) -> None:
        plano = [(self._m(x), self._m(y)) for x, y, _ in contorno]
        x0, x1 = min(p[0] for p in plano), max(p[0] for p in plano)
        y0, y1 = min(p[1] for p in plano), max(p[1] for p in plano)
        largo, ancho = x1 - x0, y1 - y0
        if largo <= TOLERANCIA or ancho <= TOLERANCIA:
            self._no_reconocido("AMBIENTES", e, f"{nombre}: dimension nula en planta", nombre)
            return
        if nombre in self.acc.ambientes:
            self._no_reconocido(
                "AMBIENTES",
                e,
                f"el nombre {nombre!r} esta repetido; solo se importa el primero",
                nombre,
            )
            return
        recto = all(
            abs(a[0] - b[0]) <= TOLERANCIA or abs(a[1] - b[1]) <= TOLERANCIA
            for a, b in zip(plano, [*plano[1:], plano[0]], strict=True)
        )
        rectangular = (
            not arcos
            and recto
            and abs(_area(plano) - largo * ancho) <= TOLERANCIA * (largo + ancho)
        )
        origen = self._origen(e, "AMBIENTES", (ORIGEN_ALTURA_PENDIENTE,))
        self.acc.ambientes[nombre] = Ambiente(
            id=nombre,
            nombre=nombre,
            x0=x0,
            y0=y0,
            largo=largo,
            ancho=ancho,
            alto=ALTO_PROVISIONAL,
            origen_id=origen.id,
        )
        self.acc.importado("esp_ambientes", e.dxf.handle, nombre, "ambiente")
        if not rectangular:
            self.acc.item(
                TipoItem.APROXIMADO,
                "esp_ambientes",
                f"{nombre}: no es rectangular; se importa su caja envolvente ({largo} x {ancho} m)",
                e.dxf.handle,
                nombre,
            )
        self.acc.item(
            TipoItem.PENDIENTE,
            "esp_ambientes",
            f"ambiente {nombre}: altura pendiente; entra con {ALTO_PROVISIONAL} m provisionales "
            "hasta cargar la real",
            e.dxf.handle,
            nombre,
        )

    # fuentes
    def fuentes(self, bloques) -> None:
        for e, sufijo, capa in bloques:
            atributos = _atributos(e)
            id_ = atributos.get("ID") or f"{capa}-{e.dxf.handle}"
            if id_ in self.acc.fuentes:
                self._no_reconocido("esp_fuentes", e, f"el id {id_!r} esta repetido", id_)
                continue
            x, y = self._m(e.dxf.insert.x), self._m(e.dxf.insert.y)
            z = self._altura(atributos, e)[0]
            ambiente = self._ambiente_de(atributos, x, y, "esp_fuentes", e, id_)
            if ambiente is None:
                continue
            especialidad, tipo = _FUENTES[sufijo]
            if sufijo == "AGUA":
                nombre = e.dxf.name.upper()
                if "ACOMETIDA" in nombre:
                    tipo = TipoFuente.ACOMETIDA_AGUA
                elif "MONTANTE" not in nombre:
                    self.acc.item(
                        TipoItem.APROXIMADO,
                        "esp_fuentes",
                        f"{id_}: el bloque {e.dxf.name} no dice si es acometida o montante; "
                        "se toma montante",
                        e.dxf.handle,
                        id_,
                    )
            origen = self._origen(e, capa)
            self.acc.fuentes[id_] = Fuente(
                id=id_,
                especialidad=especialidad,
                tipo=tipo,
                ambiente_id=ambiente,
                posicion=Coord(x, y, z),
                origen_id=origen.id,
            )
            self.acc.importado("esp_fuentes", e.dxf.handle, id_, "fuente")

    def _altura(self, atributos, e) -> tuple[Decimal, str]:
        """`(z, motivo)`: la ALTURA del bloque o, si falta o no es un numero, la cota de su
        insercion
        y el motivo por el que queda pendiente."""
        bruto = atributos.get("ALTURA")
        valor = numero(bruto)
        if valor is not None:
            return (valor * self.factor).quantize(Decimal("0.0001")), ""
        motivo = "sin atributo ALTURA" if not bruto else f"ALTURA {bruto!r} no es un numero"
        return self._m(e.dxf.insert.z), motivo

    # puntos
    def puntos(self, bloques) -> None:
        for e, sufijo, capa in bloques:
            atributos = _atributos(e)
            id_ = atributos.get("ID") or f"{capa}-{e.dxf.handle}"
            if id_ in self.acc.puntos:
                self._no_reconocido("esp_puntos", e, f"el id {id_!r} esta repetido", id_)
                continue
            x, y = self._m(e.dxf.insert.x), self._m(e.dxf.insert.y)
            ambiente = self._ambiente_de(atributos, x, y, "esp_puntos", e, id_)
            if ambiente is None:
                continue
            especialidad, tipo = _PUNTOS[sufijo]
            z, pendiente = self._altura(atributos, e)
            especificaciones = self._especificaciones(atributos, e, id_, pendiente)
            superficie = _SUPERFICIES.get(atributos.get("SUPERFICIE", "").lower()) or superficie_de(
                tipo, z
            )
            circuito = atributos.get("CIRCUITO") or None
            if circuito and especialidad is not Especialidad.ELECTRICIDAD:
                self.acc.item(
                    TipoItem.APROXIMADO,
                    "esp_puntos",
                    f"{id_}: el atributo CIRCUITO solo vale en electricidad; se ignora",
                    e.dxf.handle,
                    id_,
                )
                circuito = None
            origen = self._origen(e, capa)
            self.acc.puntos[id_] = Punto(
                id=id_,
                nombre=id_,
                especialidad=especialidad,
                tipo=tipo,
                ambiente_id=ambiente,
                superficie=superficie,
                posicion=Coord(x, y, z),
                origen_id=origen.id,
                circuito_id=circuito,
                especificaciones=especificaciones,
            )
            if atributos.get("CALIBRE"):
                self.calibre_de[id_] = atributos["CALIBRE"]
            self.acc.importado("esp_puntos", e.dxf.handle, id_, "punto")

    def _especificaciones(
        self, atributos, e, id_: str, pendiente: str
    ) -> tuple[tuple[str, str], ...]:
        especificaciones: dict[str, str] = {}
        if pendiente:
            especificaciones[ALTURA_PENDIENTE[0]] = ALTURA_PENDIENTE[1]
            self.acc.item(
                TipoItem.PENDIENTE,
                "esp_puntos",
                f"punto {id_}: altura pendiente ({pendiente}); la cota z es la de la insercion",
                e.dxf.handle,
                id_,
            )
        if atributos.get("DIAMETRO"):
            especificaciones["diametro"] = atributos["DIAMETRO"]
        if atributos.get("CATEGORIA"):
            especificaciones["categoria"] = atributos["CATEGORIA"]
        llave = atributos.get("LLAVE", "")
        if llave:
            if llave.lower() in ("si", "sí"):
                especificaciones["llave_de_paso"] = "si"
            else:
                self.acc.item(
                    TipoItem.APROXIMADO,
                    "esp_puntos",
                    f"{id_}: el atributo LLAVE {llave!r} no es «si»; se ignora",
                    e.dxf.handle,
                    id_,
                )
        return tuple(especificaciones.items())

    def asignar_fuentes(self) -> None:
        for id_, punto in list(self.acc.puntos.items()):
            fuente, cercania = fuente_para(punto, self.acc.fuentes.values())
            handle = dict(self.acc.origenes[punto.origen_id].referencia)["handle"]
            if fuente is None:
                if punto.especialidad is not Especialidad.ELECTRICIDAD:
                    self.acc.item(
                        TipoItem.PENDIENTE,
                        "esp_puntos",
                        f"punto {id_}: sin fuente compatible en el plano; se asigna en la hoja",
                        handle,
                        id_,
                    )
                continue
            self.acc.puntos[id_] = replace(punto, fuente_id=fuente.id)
            if cercania:
                self.acc.item(
                    TipoItem.APROXIMADO,
                    "esp_puntos",
                    f"{id_}: fuente {fuente.id} asignada por cercania (no hay una unica en su "
                    "ambiente)",
                    handle,
                    id_,
                )

    # circuitos
    def circuitos(self) -> None:
        por_circuito: dict[str, list[Punto]] = defaultdict(list)
        for p in self.acc.puntos.values():
            if p.circuito_id:
                por_circuito[p.circuito_id].append(p)
        tableros = sorted(
            (f for f in self.acc.fuentes.values() if f.tipo is TipoFuente.TABLERO),
            key=lambda f: f.id,
        )
        for indice, cid in enumerate(sorted(por_circuito), start=1):
            puntos = por_circuito[cid]
            if not tableros:
                self.acc.item(
                    TipoItem.PENDIENTE,
                    "esp_circuitos",
                    f"circuito {cid}: sin tablero (capa FTE-ELEC) en el plano; sus puntos quedan "
                    "sin circuito",
                    "",
                    cid,
                )
                for p in puntos:
                    self.acc.puntos[p.id] = replace(p, circuito_id=None)
                continue
            tablero = self._tablero(cid, puntos, tableros)
            calibre = self._calibre(cid, puntos)
            numero_ = digitos_finales(cid) or indice
            self.acc.circuitos[cid] = Circuito(
                id=cid,
                tablero=tablero.id,
                numero=numero_,
                conductores=(1, 1, 1),
                calibre=calibre,
                puntos_maximos=int(PUNTOS_MAXIMOS_POR_DEFECTO.valor),
            )
            self.acc.item(
                TipoItem.APROXIMADO,
                "esp_circuitos",
                f"circuito {cid}: conductores {CONDUCTORES_POR_DEFECTO.valor} y "
                f"{PUNTOS_MAXIMOS_POR_DEFECTO.valor} puntos maximos son supuestos declarados "
                f"({CONDUCTORES_POR_DEFECTO.id}, {PUNTOS_MAXIMOS_POR_DEFECTO.id}); ajustelos en "
                "la hoja",
                "",
                cid,
            )

    def _tablero(self, cid: str, puntos: list[Punto], tableros: list[Fuente]) -> Fuente:
        if len(tableros) == 1:
            return tableros[0]
        n = Decimal(len(puntos))
        centro = Coord(
            sum((p.posicion.x for p in puntos), Decimal(0)) / n,
            sum((p.posicion.y for p in puntos), Decimal(0)) / n,
            sum((p.posicion.z for p in puntos), Decimal(0)) / n,
        )
        elegido = min(tableros, key=lambda f: (f.posicion.distancia(centro), f.id))
        self.acc.item(
            TipoItem.APROXIMADO,
            "esp_circuitos",
            f"circuito {cid}: hay varios tableros; se toma {elegido.id}, el mas cercano a "
            "sus puntos",
            "",
            cid,
        )
        return elegido

    def _calibre(self, cid: str, puntos: list[Punto]) -> str:
        calibres = [self.calibre_de[p.id] for p in puntos if p.id in self.calibre_de]
        if not calibres:
            self.acc.item(
                TipoItem.PENDIENTE,
                "esp_circuitos",
                f"circuito {cid}: calibre pendiente (ningun punto declara CALIBRE)",
                "",
                cid,
            )
            return CALIBRE_PENDIENTE
        cuenta = Counter(calibres)
        elegido = sorted(cuenta, key=lambda c: (-cuenta[c], c))[0]
        if len(cuenta) > 1:
            self.acc.item(
                TipoItem.APROXIMADO,
                "esp_circuitos",
                f"circuito {cid}: calibres distintos en sus puntos ({', '.join(sorted(cuenta))}); "
                f"se toma {elegido}, el mas repetido",
                "",
                cid,
            )
        return elegido

    # recorridos declarados
    def recorridos(self, entidades) -> None:
        for e, sufijo in entidades:
            vertices, cerrada, _, es_3d = _geometria(e)
            if cerrada or (len(vertices) >= 4 and vertices[0] == vertices[-1]):
                self._no_reconocido(
                    "esp_recorridos", e, "polilinea cerrada: un recorrido es abierto"
                )
                continue
            puntos = [Coord(self._m(x), self._m(y), self._m(z)) for x, y, z in vertices]
            self._recorrido(e, sufijo, puntos, es_3d)

    def _recorrido(self, e, sufijo: str, vertices: list[Coord], es_3d: bool) -> None:
        especialidad = _RECORRIDOS[sufijo]
        extremos = (vertices[0], vertices[-1])

        def toca(p: Punto, v: Coord) -> bool:
            planta = abs(p.posicion.x - v.x) <= TOLERANCIA and abs(p.posicion.y - v.y) <= TOLERANCIA
            return planta and (not es_3d or abs(p.posicion.z - v.z) <= TOLERANCIA)

        tocados = sorted(
            {
                p.id
                for p in self.acc.puntos.values()
                if p.especialidad is especialidad and any(toca(p, v) for v in extremos)
            }
        )
        if not tocados:
            self._no_reconocido(
                "esp_recorridos", e, f"el recorrido no toca ningun punto de {especialidad.value}"
            )
            return
        if len(tocados) > 1:
            self._no_reconocido(
                "esp_recorridos",
                e,
                f"un extremo coincide con varios puntos ({', '.join(tocados)}): no se adivina",
            )
            return
        punto = self.acc.puntos[tocados[0]]
        dueno: dict[str, str | None] = {"punto_id": punto.id, "circuito_id": None}
        if especialidad is Especialidad.ELECTRICIDAD:
            if punto.circuito_id is None:
                self._no_reconocido(
                    "esp_recorridos",
                    e,
                    f"el punto {punto.id} no tiene circuito: no hay donde colgarlo",
                )
                return
            dueno = {"punto_id": None, "circuito_id": punto.circuito_id}
        tramos = self._tramos(vertices)
        if not tramos:
            self._no_reconocido("esp_recorridos", e, "el recorrido no tiene longitud")
            return
        id_ = f"REC-{e.dxf.handle}"
        self.acc.recorridos[id_] = Recorrido(
            id=id_, modo=ModoRecorrido.DECLARADO, tramos=tuple(tramos), **dueno
        )
        self.acc.item(
            TipoItem.IMPORTADO,
            "esp_recorridos",
            f"recorrido {id_}: importado como declarado; la superficie de cada tramo se infiere "
            "de su cota",
            e.dxf.handle,
            id_,
        )
        if not es_3d:
            self.acc.item(
                TipoItem.APROXIMADO,
                "esp_recorridos",
                f"{id_}: polilinea plana; su cota es su elevacion (use una polilinea 3D para "
                "recorridos con alturas)",
                e.dxf.handle,
                id_,
            )

    def _tramos(self, vertices: list[Coord]) -> list[Tramo]:
        techo = max((a.alto for a in self.acc.ambientes.values()), default=ALTO_PROVISIONAL)
        tramos = []
        for a, b in zip(vertices, vertices[1:], strict=False):
            if a.distancia(b) <= TOLERANCIA:
                continue
            vertical = abs(a.x - b.x) <= TOLERANCIA and abs(a.y - b.y) <= TOLERANCIA
            if vertical:
                superficie = SuperficieTramo.PARED
            elif a.z >= techo - TOLERANCIA:
                superficie = SuperficieTramo.TECHO
            elif a.z <= TOLERANCIA:
                superficie = SuperficieTramo.PISO
            else:
                superficie = SuperficieTramo.PARED
            tramos.append(Tramo(orden=len(tramos), superficie=superficie, vertices=(a, b)))
        return tramos


def _capas(doc):
    """Clasifica las entidades del espacio modelo por capa. Devuelve los grupos y el informe de lo
    que no se reconoce."""
    grupos: dict[str, list] = defaultdict(list)
    ajenas: dict[str, Counter] = defaultdict(Counter)
    sueltas: list[tuple[str, object, str]] = []  # (tabla, entidad, mensaje)
    for e in doc.modelspace():
        capa = (e.dxf.layer or "").strip().upper()
        tipo = e.dxftype()
        if capa == "AMBIENTES":
            if tipo in ("LWPOLYLINE", "POLYLINE"):
                grupos["poligonos"].append(e)
            elif tipo in ("TEXT", "MTEXT"):
                x, y = e.dxf.insert.x, e.dxf.insert.y
                grupos["textos"].append((_texto(e), x, y, e.dxf.handle))
            else:
                sueltas.append(
                    (capa, e, f"capa {capa}: una entidad {tipo} no es polilinea ni texto")
                )
        elif capa.startswith("FTE-") and capa[4:] in _FUENTES:
            _bloque(e, tipo, capa, "fuentes", grupos, sueltas)
        elif capa.startswith("PTO-") and capa[4:] in _PUNTOS:
            _bloque(e, tipo, capa, "puntos", grupos, sueltas)
        elif capa.startswith("REC-"):
            sufijo = capa[4:]
            if sufijo not in _RECORRIDOS:
                sueltas.append(
                    (capa, e, f"capa {capa}: la especialidad {sufijo!r} no es agua, datos ni elec")
                )
            elif tipo in _ENTIDADES_REC:
                grupos["recorridos"].append((e, sufijo))
            else:
                sueltas.append(
                    (capa, e, f"capa {capa}: una entidad {tipo} no es polilinea ni linea")
                )
        else:
            ajenas[capa or "(sin capa)"][tipo] += 1
    return grupos, ajenas, sueltas


def _bloque(e, tipo: str, capa: str, clave: str, grupos, sueltas) -> None:
    if tipo == "INSERT":
        grupos[clave].append((e, capa[4:], capa))
    else:
        sueltas.append((capa, e, f"capa {capa}: una entidad {tipo} no es un bloque insertado"))


def importar_dxf(
    contenido: bytes | Path | str, *, unidades: str | None = None, nombre: str | None = None
) -> ResultadoImportacion:
    """Importa un DXF con la convencion de capas del spec §6.6.1.

    `contenido`: los bytes del archivo o su ruta. `unidades`: la unidad del dibujo (`m`, `cm`, `mm`,
    `dm`, `in`, `ft`) cuando el plano no declara `$INSUNITS`; si el plano la declara, esa manda.
    `nombre`: el nombre de archivo que cita el origen (por defecto el de la ruta, o `plano.dxf`).

    Nunca lanza por un archivo malo: devuelve un resultado `RECHAZADA` (malformado, mas de 20 MB) o
    `DETENIDA` (falta la unidad, con `pide_unidad`) con su mensaje y sin filas."""
    doc, archivo, rechazo = _leer(contenido, nombre)
    if rechazo is not None:
        return rechazo
    factor, codigo, estado = _factor(doc, unidades)
    if factor is None and estado == "indicada":
        return sin_filas(
            "dxf",
            archivo,
            EstadoImportacion.RECHAZADA,
            f"{archivo}: la unidad indicada {unidades!r} no se conoce; use {_UNIDADES_ACEPTADAS}.",
        )
    if factor is None:
        declara = "no declara sus unidades ($INSUNITS ausente o sin unidad)"
        if codigo:
            declara = f"declara $INSUNITS = {codigo}, que no se puede convertir a metros"
        return sin_filas(
            "dxf",
            archivo,
            EstadoImportacion.DETENIDA,
            f"{archivo}: el plano {declara}; indique la unidad del dibujo ({_UNIDADES_ACEPTADAS}) "
            "con unidades= y vuelva a importar.",
            pide_unidad=True,
        )
    grupos, ajenas, sueltas = _capas(doc)
    lector = _Lector(doc, archivo, factor)
    for tabla, e, mensaje in sueltas:
        lector._no_reconocido(tabla, e, mensaje)
    lector.ambientes(grupos["poligonos"], grupos["textos"])
    lector.fuentes(grupos["fuentes"])
    lector.puntos(grupos["puntos"])
    lector.asignar_fuentes()
    lector.circuitos()
    lector.recorridos(grupos["recorridos"])
    for capa in sorted(ajenas):
        n = sum(ajenas[capa].values())
        tipos = ", ".join(f"{t} {c}" for t, c in sorted(ajenas[capa].items()))
        lector.acc.item(
            TipoItem.NO_RECONOCIDO,
            capa,
            f"capa {capa}: {n} {'entidad' if n == 1 else 'entidades'} ({tipos}) fuera de la "
            "convencion; no se importan",
        )
    acc = lector.acc
    if not (acc.ambientes or acc.fuentes or acc.puntos or acc.recorridos):
        return acc.resultado(
            mensaje=f"{archivo}: el plano no sigue la convencion de capas (AMBIENTES, FTE-*, "
            "PTO-*, REC-*); no se importo ninguna fila."
        )
    return acc.resultado()
