"""Anonimiza un libro de presupuesto real (.xlsx) para que pueda entrar al repositorio.

Por que existe: la decision V-D3 de Silice 1.5
(`docs/especificaciones/2026-10-13-silice-1.5-fusion-design.md`) deja los libros de Excel reales
fuera del repositorio, porque son confidenciales. Lo que si entra son casos *derivados*: el mismo
libro, con sus formulas, hojas, montos y VALORES GUARDADOS, pero sin nada que identifique al
cliente, al contratista, la obra, la direccion ni a las personas que lo firman.

Por que trabaja sobre el ZIP y no con openpyxl: abrir el libro con openpyxl en modo formulas y
guardarlo borra el valor guardado (`<v>`) de cada formula, y un caso asi no sirve para las reglas
que leen valores guardados (L3, L9, F1, totales). Por eso el script copia cada entrada del paquete
tal cual y solo reescribe, con expresiones regulares acotadas, el texto que anonimiza; los numeros,
los `<v>` numericos, los estilos y todo lo demas quedan byte a byte. No se re-serializa ningun XML
con un arbol (ElementTree renombra los prefijos de espacio de nombres y Excel rechaza el
resultado): defusedxml se usa para comprobar que la ENTRADA no trae DTD ni entidades y que cada
parte reescrita sigue siendo XML bien formado.

Por que el script descubre los datos en vez de traerlos escritos: una lista de nombres dentro del
repositorio seria, ella misma, la fuga que se quiere evitar. Los datos identificables se leen de la
PORTADA de la plantilla (rotulos CLIENTE, CONTRATISTA, UBICACION, firmas y nombre de la obra) y del
patron del RIF; los autores, de los comentarios y de las propiedades del documento.

Lo que se REESCRIBE (sustituyendo los datos descubiertos y el RIF):

- `xl/sharedStrings.xml` y las cadenas en linea (`<is>`) de las hojas: un texto con formato mixto
  que cambia queda como un solo tramo sin formato.
- Las hojas: solo el texto entre comillas de las formulas (`<f>`, formulas de validaciones y de
  formatos condicionales), los valores guardados que son texto (`<v>` de `t="str"`), los
  encabezados y pies (`<oddHeader>` etc.) y los mensajes de las validaciones que quedan.
- Comentarios: el texto (tambien los nombres de los autores) y `<author>` a 'anonimo'; personas de
  los comentarios encadenados (`xl/persons/`) a 'anonimo'.
- `docProps/core.xml` (autor, ultimo en modificar, titulo, asunto...) y `docProps/app.xml`
  (empresa, responsable) a 'anonimo'; `docProps/custom.xml` se vacia.
- Cualquier otra parte XML (graficos, dibujos, VML, tablas...): sus textos y atributos.

Lo que se QUITA, porque no se puede revisar texto por texto:

- Los vinculos externos (`xl/externalLinks/**`), sus relaciones, sus tipos de contenido, el bloque
  `<externalReferences>` y los `<definedName>` que los usan (`[n]`). Los valores guardados de las
  celdas que dependian de ellos se conservan.
- Los hipervinculos: el bloque `<hyperlinks>` de cada hoja, los `<a:hlinkClick>` de los dibujos y
  sus relaciones (una direccion web o de correo identifica tanto como un nombre).
- Las listas literales de validacion (`"opcion1,opcion2"`): suelen enumerar personas o empresas.
- La ruta del archivo en el equipo de origen (`x15ac:absPath`) y el usuario de `fileSharing`.
- La configuracion de impresora de cada hoja (`xl/printerSettings/**`, guarda el nombre de la
  impresora o del servidor), con su relacion y el `r:id` de `<pageSetup>`.

Las IMAGENES (logos del membrete) no se quitan sino que se SUSTITUYEN por un PNG neutro de 1x1
transparente (`xl/media/anonimoN.png`), y se borran la descripcion y el titulo de cada imagen. Es
lo mas seguro: una imagen la puede referenciar un dibujo, un VML de encabezado o el fondo de una
hoja, y quitarla obligaria a operar cada una de esas estructuras; sustituirla no rompe ninguna
relacion y el logo desaparece igual.

Por que verifica al final: sustituir es facil de hacer a medias (un espacio doble, un tramo de
formato, un literal dentro de una formula). Por eso el script relee la SALIDA y busca de nuevo cada
dato descubierto y el RIF en el XML crudo de TODAS las entradas (y en las binarias), comprueba que
no quede nada de lo que se quita, que toda imagen sea el PNG neutro, que cada relacion y cada tipo
de contenido apunte a una parte que existe y que el libro abra con openpyxl; si algo falla, borra
la SALIDA y termina con codigo 1. Un caso anonimizado que no paso esa verificacion no existe.

Lo que no hace: no toca montos, cantidades ni fechas, no renombra hojas (si una hoja lleva el
nombre del cliente la verificacion falla) y no anonimiza nombres que no esten en la PORTADA (por
ejemplo, un proveedor citado solo en una hoja de insumos). Esa revision sigue siendo de quien sube
el caso.

Uso::

    uv run python scripts/anonimizar_libro.py ENTRADA.xlsx SALIDA.xlsx [--etiqueta A]

Codigos de salida: 0 bien; 1 sin rotulos en la PORTADA, paquete inseguro o verificacion fallida
(la SALIDA se borra); 2 argumentos o ENTRADA invalidos.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import struct
import sys
import unicodedata
import zipfile
import zlib
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

import openpyxl
from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError
from defusedxml.ElementTree import fromstring as xml_seguro
from openpyxl.workbook.workbook import Workbook

#: Texto que sustituye a cada clase de dato. `{e}` es la etiqueta del caso.
SUSTITUTOS: dict[str, str] = {
    "cliente": "CLIENTE-{e}",
    "contratista": "CONTRATISTA-{e}",
    "ubicacion": "UBICACIÓN ANONIMIZADA",
    "firma": "PERSONA-{e}",
    "rif": "J-00000000-0",
}

#: Rotulos de la PORTADA (normalizados: sin acentos, en minusculas, sin ':').
ROTULOS: dict[str, str] = {
    "cliente": "cliente",
    "contratista": "contratista",
    "ubicacion": "ubicacion",
}
ROTULOS_FIRMA: tuple[str, ...] = ("elaborado por", "aprobado por")
ROTULO_OBRA = "presupuesto de obra"

RIF = re.compile(r"(?<![A-Za-z0-9])[JVEGP]-?\d{7,9}-?\d?(?![0-9])")
RIF_NEUTRO = SUSTITUTOS["rif"]

#: Un fragmento mas corto que esto no se usa como variante (seria demasiado generico).
LARGO_MINIMO_VARIANTE = 5

ANONIMO = "anonimo"

LITERAL_FORMULA = re.compile(r'"(?:[^"]|"")*"')

# --- Paquete -----------------------------------------------------------------------------------

#: Partes que se quitan enteras (prefijo del nombre en el paquete).
QUITADAS: tuple[str, ...] = ("xl/externalLinks/", "xl/printerSettings/")
MEDIA = "xl/media/"
HOJAS: tuple[str, ...] = (
    "xl/worksheets/",
    "xl/chartsheets/",
    "xl/dialogsheets/",
    "xl/macrosheets/",
)
#: Relaciones que se quitan por su tipo (final del atributo Type).
TIPOS_REL_QUITADOS: tuple[str, ...] = ("/externalLink", "/hyperlink", "/printerSettings")

CAMPOS_CORE: tuple[str, ...] = (
    "creator",
    "lastModifiedBy",
    "title",
    "subject",
    "keywords",
    "description",
    "category",
    "contentStatus",
    "identifier",
)
CAMPOS_APP: tuple[str, ...] = ("Company", "Manager")
CUSTOM_VACIO = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
    b'<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"'
    b' xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"/>'
)

#: Etiquetas (nombre local) cuyo texto es una formula: solo se tocan sus literales.
FORMULAS: frozenset[str] = frozenset({"f", "formula", "formula1", "formula2", "definedName"})
ENCABEZADOS: frozenset[str] = frozenset(
    {"oddHeader", "oddFooter", "evenHeader", "evenFooter", "firstHeader", "firstFooter"}
)
#: Textos de una hoja que se sustituyen (las cadenas en linea `<is>` van aparte).
TEXTOS_HOJA: frozenset[str] = FORMULAS | ENCABEZADOS | {"v"}
#: Etiquetas de hoja con atributos tecnicos que no se revisan (son la mayoria: rapidez).
ETIQUETAS_TECNICAS_HOJA: frozenset[str] = frozenset(
    {"c", "row", "col", "f", "v", "pane", "selection"}
)
#: Etiquetas con texto en el formato escapado de OOXML (`_x000D_`).
TEXTOS_OOXML: frozenset[str] = frozenset({"t", "v"}) | ENCABEZADOS

# --- XML a mano, con expresiones acotadas ------------------------------------------------------

_ATRS = r"(?:\s+[^\s=/<>]+\s*=\s*(?:\"[^\"]*\"|'[^']*'))*\s*"
_NOMBRE = r"[A-Za-z_][\w.:-]*"
_APERTURA = re.compile(rf"<(?P<tag>{_NOMBRE})(?P<attrs>{_ATRS})(?P<fin>/?)>")
_ATRIBUTO = re.compile(r"(?P<pre>\s+(?P<nombre>[^\s=/<>]+)\s*=\s*)(?P<q>[\"'])(?P<valor>.*?)(?P=q)")
_HOJA_XML = re.compile(rf"<(?P<tag>{_NOMBRE})(?P<attrs>{_ATRS})>(?P<texto>[^<]*)</(?P=tag)>")
_ENTIDAD = re.compile(r"&(#[xX][0-9A-Fa-f]+|#[0-9]+|amp|lt|gt|quot|apos);")
_NOMBRADAS = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}
_ESCAPE_OOXML = re.compile(r"_x([0-9A-Fa-f]{4})_")
_GUID = re.compile(r"\{?[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\}?")
_REF_RELACION = re.compile(r"\s(?:r:(?:id|embed|link|pict)|o:relid)\s*=\s*\"([^\"]*)\"")


def _png_neutro() -> bytes:
    """PNG de 1x1 transparente, armado aqui para no depender de Pillow."""

    def trozo(tipo: bytes, datos: bytes) -> bytes:
        crc = zlib.crc32(tipo + datos)
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", crc)

    cabecera = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    pixel = zlib.compress(b"\x00\x00\x00\x00\x00", 9)
    firma = b"\x89PNG\r\n\x1a\n"
    return firma + trozo(b"IHDR", cabecera) + trozo(b"IDAT", pixel) + trozo(b"IEND", b"")


PNG_NEUTRO = _png_neutro()


def _local(nombre: str) -> str:
    return nombre.rsplit(":", 1)[-1]


def _des_xml(texto: str) -> str:
    if "&" not in texto:
        return texto

    def entidad(m: re.Match[str]) -> str:
        e = m.group(1)
        if e.startswith("#"):
            return chr(int(e[2:], 16) if e[1] in "xX" else int(e[1:]))
        return _NOMBRADAS[e]

    return _ENTIDAD.sub(entidad, texto)


def _a_xml(texto: str, *, atributo: bool = False) -> str:
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    texto = texto.replace("\r", "&#13;")
    if atributo:
        texto = texto.replace('"', "&quot;").replace("'", "&apos;")
        texto = texto.replace("\n", "&#10;").replace("\t", "&#9;")
    return texto


def _des_ooxml(texto: str) -> str:
    return _ESCAPE_OOXML.sub(lambda m: chr(int(m.group(1), 16)), texto)


def _a_ooxml(texto: str) -> str:
    texto = re.sub(r"_(?=x[0-9A-Fa-f]{4}_)", "_x005F_", texto)
    return re.sub(r"[\x00-\x08\x0b-\x1f]", lambda m: f"_x{ord(m.group(0)):04X}_", texto)


def _tiene_letra(texto: str) -> bool:
    return any(c.isalpha() for c in texto)


def _atributos(attrs: str) -> dict[str, str]:
    return {
        _local(m.group("nombre")): _des_xml(m.group("valor")) for m in _ATRIBUTO.finditer(attrs)
    }


# --- Descubrimiento ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Dato:
    """Un texto identificable descubierto en el libro y lo que lo sustituye.

    `palabra`: solo cuenta como palabra completa (los nombres de autor, que pueden ser cortos).
    """

    tipo: str
    texto: str
    sustituto: str
    palabra: bool = False

    @property
    def patron(self) -> re.Pattern[str]:
        cuerpo = r"\s+".join(re.escape(p) for p in self.texto.split())
        if self.palabra:
            cuerpo = rf"(?<!\w){cuerpo}(?!\w)"
        return re.compile(cuerpo, re.IGNORECASE)


def _normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return " ".join(sin_acentos.casefold().strip().rstrip(":").split())


def _es_texto(valor: object) -> bool:
    return isinstance(valor, str) and bool(valor.strip()) and not valor.startswith("=")


def _variantes(tipo: str, valor: str) -> list[str]:
    """El valor completo, la parte antes de " (" y la parte antes de ",".

    En la ubicacion, ademas, cada tramo entre comas: una direccion es una lista de lugares y
    cualquiera de ellos (la calle, el edificio) puede aparecer suelto en otra hoja.
    """
    completo = " ".join(valor.split())
    candidatos = [completo]
    antes_parentesis = completo.split(" (")[0].strip()
    candidatos.append(antes_parentesis)
    candidatos.append(antes_parentesis.split(",")[0].strip())
    if tipo == "ubicacion":
        candidatos.extend(t.strip() for t in antes_parentesis.split(","))
    vistos: list[str] = []
    for c in candidatos:
        c = c.strip(" .;-")
        if len(c) >= LARGO_MINIMO_VARIANTE and any(ch.isalpha() for ch in c):
            if c.casefold() not in {v.casefold() for v in vistos}:
                vistos.append(c)
    return vistos


def _hoja_portada(libro: Workbook):
    for hoja in libro.worksheets:
        if _normalizar(hoja.title) == "portada":
            return hoja
    return None


def _a_la_derecha(hoja, fila: int, columna: int) -> str | None:
    for c in range(columna + 1, columna + 4):
        valor = hoja.cell(row=fila, column=c).value
        if valor is not None and str(valor).strip():
            return valor if _es_texto(valor) else None
    return None


def descubrir(libro: Workbook, etiqueta: str) -> list[Dato]:
    """Lee la PORTADA y devuelve los datos identificables, del mas largo al mas corto."""
    portada = _hoja_portada(libro)
    if portada is None:
        return []
    crudos: dict[str, list[str]] = defaultdict(list)
    obras: list[str] = []
    for fila in portada.iter_rows():
        for celda in fila:
            if not isinstance(celda.value, str):
                continue
            rotulo = _normalizar(celda.value)
            for tipo, esperado in ROTULOS.items():
                if rotulo == esperado:
                    valor = _a_la_derecha(portada, celda.row, celda.column)
                    if valor:
                        crudos[tipo].append(valor)
            for firma in ROTULOS_FIRMA:
                if rotulo.startswith(firma):
                    resto = celda.value.split(":", 1)[1] if ":" in celda.value else ""
                    debajo = portada.cell(row=celda.row + 1, column=celda.column).value
                    for valor in (resto, debajo):
                        if _es_texto(valor) and set(str(valor).strip()) - {"_", " "}:
                            crudos["firma"].append(str(valor))
            if rotulo == ROTULO_OBRA:
                debajo = portada.cell(row=celda.row + 1, column=celda.column).value
                if _es_texto(debajo):
                    obras.append(str(debajo))

    datos: list[Dato] = []
    conocidos: set[str] = set()
    for tipo in ("cliente", "contratista", "ubicacion", "firma"):
        sustituto = SUSTITUTOS[tipo].format(e=etiqueta)
        for valor in crudos.get(tipo, []):
            for variante in _variantes(tipo, valor):
                if variante.casefold() in conocidos:
                    continue
                conocidos.add(variante.casefold())
                datos.append(Dato(tipo, variante, sustituto))
    datos.sort(key=lambda d: len(d.texto), reverse=True)

    # El nombre de la obra solo es identificable si nombra al cliente; entonces se sustituye
    # por el mismo nombre con el cliente ya anonimizado.
    clientes = [d for d in datos if d.tipo == "cliente"]
    for obra in obras:
        if any(d.patron.search(obra) for d in clientes):
            anonima = _sustituir_texto(obra, clientes)[0]
            completo = " ".join(obra.split())
            if completo.casefold() not in conocidos:
                conocidos.add(completo.casefold())
                datos.insert(0, Dato("obra", completo, anonima))
    return datos


def _es_parte_de_comentarios(nombre: str) -> bool:
    return nombre.startswith(("xl/comments", "xl/threadedComments/", "xl/persons/"))


def descubrir_autores(paquete: dict[str, bytes]) -> list[Dato]:
    """Nombres de autor: de los comentarios, de las personas y de las propiedades del documento.

    Se sustituyen por 'anonimo' en los comentarios (que suelen empezar por "Autor:"); las
    propiedades se reescriben enteras."""
    nombres: list[str] = []
    for nombre, contenido in paquete.items():
        if not nombre.endswith(".xml"):
            continue
        texto = contenido.decode("utf-8", "replace")
        if nombre.startswith("xl/comments"):
            nombres += re.findall(r"<(?:\w+:)?author>([^<]*)</(?:\w+:)?author>", texto)
        elif nombre.startswith("xl/persons/"):
            nombres += re.findall(r"\sdisplayName\s*=\s*\"([^\"]*)\"", texto)
        elif nombre in ("docProps/core.xml", "docProps/app.xml"):
            campos = "|".join(("creator", "lastModifiedBy", *CAMPOS_APP))
            nombres += [
                m.group(2)
                for m in re.finditer(rf"<((?:\w+:)?(?:{campos}))\b[^>]*>([^<]*)</\1>", texto)
            ]
    autores: list[Dato] = []
    vistos: set[str] = {ANONIMO}
    for crudo in nombres:
        nombre = " ".join(_des_xml(crudo).split())
        if len(nombre) >= 2 and _tiene_letra(nombre) and nombre.casefold() not in vistos:
            vistos.add(nombre.casefold())
            autores.append(Dato("autor", nombre, ANONIMO, palabra=True))
    autores.sort(key=lambda d: len(d.texto), reverse=True)
    return autores


# --- Sustitucion de textos ---------------------------------------------------------------------


def _sustituir_texto(texto: str, datos: list[Dato]) -> tuple[str, set[str]]:
    """Sustituye los datos y el RIF en un texto; devuelve el texto y los tipos que cambiaron."""
    tipos: set[str] = set()
    for dato in datos:
        nuevo = dato.patron.sub(lambda _m, s=dato.sustituto: s, texto)
        if nuevo != texto:
            tipos.add(dato.tipo)
            texto = nuevo
    nuevo = RIF.sub(lambda m: m.group(0) if m.group(0) == RIF_NEUTRO else RIF_NEUTRO, texto)
    if nuevo != texto:
        tipos.add("rif")
        texto = nuevo
    return texto, tipos


def _sustituir_formula(formula: str, datos: list[Dato]) -> tuple[str, set[str]]:
    """Solo toca los literales entre comillas; las referencias y funciones quedan igual."""
    tipos: set[str] = set()

    def literal(m: re.Match[str]) -> str:
        nuevo, t = _sustituir_texto(m.group(0), datos)
        tipos.update(t)
        return nuevo

    return LITERAL_FORMULA.sub(literal, formula), tipos


class PaqueteInseguroError(Exception):
    """La ENTRADA trae algo que no se puede anonimizar con garantias (DTD, XML roto...)."""


@dataclass
class Contexto:
    """Lo que necesita y lo que va contando la reescritura del paquete."""

    datos: list[Dato]
    autores: list[Dato]
    lugares: dict[str, str] = field(default_factory=dict)
    informe: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    quitado: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def anotar(self, tipos: set[str], parte: str) -> None:
        lugar = self.lugares.get(parte, parte)
        for t in tipos:
            self.informe[t][lugar] += 1


def _sustituir_xml(
    xml: str,
    ctx: Contexto,
    parte: str,
    datos: list[Dato],
    *,
    textos: frozenset[str] | None = None,
    atributos: Callable[[str, str], bool] | None = None,
) -> str:
    """Sustituye en el texto de los elementos hoja (`textos`: nombres locales; None, todos) y en
    los atributos que acepte `atributos(etiqueta, atributo)`. Las formulas solo en sus literales.
    Lo que no cambia queda con sus mismos caracteres."""
    if atributos is not None:
        filtro = atributos

        def atributo_nuevo(local: str, a: re.Match[str]) -> str:
            if not filtro(local, _local(a.group("nombre"))):
                return a.group(0)
            valor = _des_xml(a.group("valor"))
            if not _tiene_letra(valor) or _GUID.fullmatch(valor):
                return a.group(0)
            nuevo, tipos = _sustituir_texto(valor, datos)
            if not tipos:
                return a.group(0)
            ctx.anotar(tipos, parte)
            q = a.group("q")
            return f"{a.group('pre')}{q}{_a_xml(nuevo, atributo=True)}{q}"

        def apertura(m: re.Match[str]) -> str:
            attrs = m.group("attrs")
            if not attrs.strip():
                return m.group(0)
            local = _local(m.group("tag"))
            nuevos = _ATRIBUTO.sub(lambda a: atributo_nuevo(local, a), attrs)
            if nuevos == attrs:
                return m.group(0)
            return f"<{m.group('tag')}{nuevos}{m.group('fin')}>"

        xml = _APERTURA.sub(apertura, xml)

    def elemento(m: re.Match[str]) -> str:
        local = _local(m.group("tag"))
        crudo = m.group("texto")
        if not crudo or (textos is not None and local not in textos):
            return m.group(0)
        texto = _des_xml(crudo)
        if not _tiene_letra(texto):
            return m.group(0)
        if local in FORMULAS:
            nuevo, tipos = _sustituir_formula(texto, datos)
            codificado = _a_xml(nuevo)
        elif local in TEXTOS_OOXML:
            nuevo, tipos = _sustituir_texto(_des_ooxml(texto), datos)
            codificado = _a_xml(_a_ooxml(nuevo))
        else:
            nuevo, tipos = _sustituir_texto(texto, datos)
            codificado = _a_xml(nuevo)
        if not tipos:
            return m.group(0)
        ctx.anotar(tipos, parte)
        inicio, fin = m.start("texto") - m.start(), m.end("texto") - m.start()
        return m.group(0)[:inicio] + codificado + m.group(0)[fin:]

    return _HOJA_XML.sub(elemento, xml)


def _texto_de_tramos(cuerpo: str) -> str:
    """El texto visible de un `<si>`, `<is>` o `<text>`: sus `<t>`, sin la fonetica (`<rPh>`)."""
    visible = re.sub(r"<(?P<p>(?:\w+:)?)rPh\b.*?</(?P=p)rPh>", "", cuerpo, flags=re.S)
    partes = re.findall(r"<(?:\w+:)?t(?:\s[^>]*)?>([^<]*)</(?:\w+:)?t>", visible)
    return "".join(_des_ooxml(_des_xml(p)) for p in partes)


def _colapsar(xml: str, local: str, ctx: Contexto, parte: str, datos: list[Dato]) -> str:
    """Sustituye en cada `<local>` con tramos; si cambia, queda un solo `<t>` sin formato (un
    nombre partido en dos tramos de formato no se veria tramo a tramo)."""
    patron = re.compile(
        rf"<(?P<p>(?:\w+:)?){local}(?P<attrs>{_ATRS})>(?P<cuerpo>.*?)</(?P=p){local}>", re.S
    )

    def cambiar(m: re.Match[str]) -> str:
        nuevo, tipos = _sustituir_texto(_texto_de_tramos(m.group("cuerpo")), datos)
        if not tipos:
            return m.group(0)
        ctx.anotar(tipos, parte)
        p = m.group("p")
        t = f'<{p}t xml:space="preserve">{_a_xml(_a_ooxml(nuevo))}</{p}t>'
        return f"<{p}{local}{m.group('attrs')}>{t}</{p}{local}>"

    return patron.sub(cambiar, xml)


def _quitar(xml: str, local: str, ctx: Contexto, que: str, *, contar: str | None = None) -> str:
    """Quita cada elemento `local` (con su contenido). `contar`: elemento hijo que se cuenta."""
    patron = re.compile(
        rf"<(?P<p>(?:\w+:)?){local}\b{_ATRS}(?:/>|>(?P<cuerpo>.*?)</(?P=p){local}>)", re.S
    )

    def quitar(m: re.Match[str]) -> str:
        cuerpo = m.group("cuerpo") or ""
        ctx.quitado[que] += len(re.findall(rf"<(?:\w+:)?{contar}\b", cuerpo)) if contar else 1
        return ""

    return patron.sub(quitar, xml)


def _fijar_atributos(xml: str, local: str, valores: dict[str, str]) -> str:
    """Pone `valores` en los atributos (ya presentes) de cada etiqueta `local`."""

    def apertura(m: re.Match[str]) -> str:
        if _local(m.group("tag")) != local:
            return m.group(0)

        def atributo(a: re.Match[str]) -> str:
            nuevo = valores.get(_local(a.group("nombre")))
            if nuevo is None:
                return a.group(0)
            return f"{a.group('pre')}{a.group('q')}{_a_xml(nuevo, atributo=True)}{a.group('q')}"

        return f"<{m.group('tag')}{_ATRIBUTO.sub(atributo, m.group('attrs'))}{m.group('fin')}>"

    return _APERTURA.sub(apertura, xml)


def _quitar_atributos(xml: str, local: str, nombres: set[str]) -> str:
    def apertura(m: re.Match[str]) -> str:
        if _local(m.group("tag")) != local:
            return m.group(0)
        attrs = _ATRIBUTO.sub(
            lambda a: "" if _local(a.group("nombre")) in nombres else a.group(0), m.group("attrs")
        )
        return f"<{m.group('tag')}{attrs}{m.group('fin')}>"

    return _APERTURA.sub(apertura, xml)


# --- Una parte por tipo ------------------------------------------------------------------------


def _es_lista_literal(cuerpo: str, attrs: str) -> bool:
    """Validacion de tipo lista cuyos valores van escritos en la regla (`"a,b,c"`)."""
    if _atributos(attrs).get("type") != "list":
        return False
    m = re.search(r"<(?:\w+:)?formula1>(?:\s*<(?:\w+:)?f>)?([^<]*)", cuerpo)
    return m is not None and _des_xml(m.group(1)).strip().startswith('"')


def _validaciones(xml: str, ctx: Contexto) -> str:
    """Quita las listas literales de validacion y corrige el `count` de su contenedor."""
    contenedor = re.compile(
        rf"<(?P<p>(?:\w+:)?)dataValidations\b(?P<attrs>{_ATRS})>(?P<cuerpo>.*?)"
        rf"</(?P=p)dataValidations>",
        re.S,
    )
    una = re.compile(
        rf"<(?P<p>(?:\w+:)?)dataValidation\b(?P<attrs>{_ATRS})(?:/>|>(?P<cuerpo>.*?)"
        rf"</(?P=p)dataValidation>)",
        re.S,
    )

    def en_contenedor(m: re.Match[str]) -> str:
        quitadas = 0

        def validacion(v: re.Match[str]) -> str:
            nonlocal quitadas
            if _es_lista_literal(v.group("cuerpo") or "", v.group("attrs")):
                quitadas += 1
                return ""
            return v.group(0)

        cuerpo = una.sub(validacion, m.group("cuerpo"))
        if not quitadas:
            return m.group(0)
        ctx.quitado["listas de validacion literales"] += quitadas
        quedan = len(una.findall(cuerpo))
        p = m.group("p")
        if not quedan and not p:
            return ""  # <dataValidations> exige al menos una validacion
        attrs = re.sub(r"(\scount\s*=\s*)\"\d+\"", rf'\g<1>"{quedan}"', m.group("attrs"))
        return f"<{p}dataValidations{attrs}>{cuerpo}</{p}dataValidations>"

    return contenedor.sub(en_contenedor, xml)


def _parte_hoja(xml: str, ctx: Contexto, parte: str) -> str:
    xml = _quitar(xml, "hyperlinks", ctx, "hipervinculos", contar="hyperlink")
    xml = _validaciones(xml, ctx)
    xml = _colapsar(xml, "is", ctx, parte, ctx.datos)
    return _sustituir_xml(
        xml,
        ctx,
        parte,
        ctx.datos,
        textos=TEXTOS_HOJA,
        atributos=lambda etiqueta, _a: etiqueta not in ETIQUETAS_TECNICAS_HOJA,
    )


def _parte_libro(xml: str, ctx: Contexto, parte: str) -> str:
    """`xl/workbook.xml`: vinculos externos, nombres que los usan, ruta y usuario de origen."""
    xml = _quitar(
        xml, "externalReferences", ctx, "referencias externas", contar="externalReference"
    )

    def nombre(m: re.Match[str]) -> str:
        if re.search(r"\[\d+\]", _des_xml(m.group("texto"))):
            ctx.quitado["nombres definidos externos"] += 1
            return ""
        return m.group(0)

    xml = re.sub(
        rf"<(?P<p>(?:\w+:)?)definedName\b{_ATRS}>(?P<texto>[^<]*)</(?P=p)definedName>", nombre, xml
    )
    xml = re.sub(
        rf"<(?P<p>(?:\w+:)?)definedNames\b{_ATRS}(?:/>|>\s*</(?P=p)definedNames>)", "", xml
    )
    antes = xml
    xml = re.sub(
        r"<mc:AlternateContent\b[^>]*>(?:(?!</mc:AlternateContent>).)*?absPath"
        r"(?:(?!</mc:AlternateContent>).)*</mc:AlternateContent>",
        "",
        xml,
        flags=re.S,
    )
    xml = re.sub(rf"<(?:\w+:)?absPath\b{_ATRS}/>", "", xml)
    if xml != antes:
        ctx.quitado["ruta del archivo de origen"] += 1
    xml = _fijar_atributos(xml, "fileSharing", {"userName": ANONIMO})
    return _sustituir_xml(xml, ctx, parte, ctx.datos, textos=FORMULAS)


def _parte_comentarios(xml: str, ctx: Contexto, parte: str) -> str:
    datos = ctx.datos + ctx.autores
    if parte.startswith("xl/persons/"):
        xml = _fijar_atributos(
            xml, "person", {"displayName": ANONIMO, "userId": ANONIMO, "providerId": "None"}
        )
        return _sustituir_xml(xml, ctx, parte, datos, atributos=lambda _e, _a: True)
    if parte.startswith("xl/threadedComments/"):
        return _sustituir_xml(xml, ctx, parte, datos, textos=frozenset({"text"}))
    ctx.quitado["autores de comentarios anonimizados"] += len(
        re.findall(r"<(?:\w+:)?author>[^<]+</(?:\w+:)?author>", xml)
    )
    xml = re.sub(
        r"<(?P<p>(?:\w+:)?)author>[^<]*</(?P=p)author>",
        lambda m: f"<{m.group('p')}author>{ANONIMO}</{m.group('p')}author>",
        xml,
    )
    return _colapsar(xml, "text", ctx, parte, datos)


def _parte_propiedades(xml: str, ctx: Contexto, parte: str, campos: tuple[str, ...]) -> str:
    patron = rf"<(?P<tag>(?:\w+:)?(?:{'|'.join(campos)}))(?P<attrs>{_ATRS})>[^<]*</(?P=tag)>"
    xml = re.sub(
        patron, lambda m: f"<{m.group('tag')}{m.group('attrs')}>{ANONIMO}</{m.group('tag')}>", xml
    )
    xml = re.sub(
        rf"<(?P<p>(?:\w+:)?)HyperlinkBase\b{_ATRS}(?:/>|>[^<]*</(?P=p)HyperlinkBase>)", "", xml
    )
    return _sustituir_xml(xml, ctx, parte, ctx.datos)


def _parte_generica(xml: str, ctx: Contexto, parte: str) -> str:
    """Graficos, dibujos, VML, tablas...: sin hipervinculos ni descripcion de imagen; textos y
    atributos sustituidos."""
    for local in ("hlinkClick", "hlinkHover"):
        xml = _quitar(xml, local, ctx, "hipervinculos")
    xml = _quitar_atributos(xml, "cNvPr", {"descr", "title"})
    xml = _quitar_atributos(xml, "imagedata", {"title"})
    return _sustituir_xml(xml, ctx, parte, ctx.datos, atributos=lambda _e, _a: True)


def _origen_de_rels(nombre: str) -> tuple[str, str]:
    """`xl/worksheets/_rels/sheet1.xml.rels` -> (`xl/worksheets/sheet1.xml`, `xl/worksheets`)."""
    carpeta, archivo = posixpath.split(nombre)
    base = posixpath.dirname(carpeta)
    return posixpath.join(base, archivo.removesuffix(".rels")), base


def _resolver(base: str, destino: str) -> str:
    destino = unquote(destino)
    if destino.startswith("/"):
        return destino.lstrip("/")
    return posixpath.normpath(posixpath.join(base, destino))


_RELACION = re.compile(
    rf"<(?P<p>(?:\w+:)?)Relationship\b(?P<attrs>{_ATRS})(?:/>|>\s*</(?P=p)Relationship>)"
)


def _parte_rels(
    xml: str, nombre: str, quitadas: set[str], medios: dict[str, str]
) -> tuple[str, set[str], int]:
    """Quita las relaciones a partes quitadas o de tipo quitado y renombra las imagenes.
    Devuelve el XML, los Id quitados y cuantas relaciones de hipervinculo se quitaron."""
    _origen, base = _origen_de_rels(nombre)
    ids: set[str] = set()
    vinculos = 0

    def relacion(m: re.Match[str]) -> str:
        nonlocal vinculos
        a = _atributos(m.group("attrs"))
        externa = a.get("TargetMode") == "External"
        destino = "" if externa else _resolver(base, a.get("Target", ""))
        if a.get("Type", "").endswith(TIPOS_REL_QUITADOS) or destino.startswith(tuple(quitadas)):
            ids.add(a.get("Id", ""))
            vinculos += a.get("Type", "").endswith("/hyperlink")
            return ""
        if destino in medios:
            original = a["Target"]
            nuevo = medios[destino]
            objetivo = (
                "/" + nuevo if original.startswith("/") else posixpath.relpath(nuevo, base or ".")
            )
            return _fijar_atributos(m.group(0), "Relationship", {"Target": objetivo})
        return m.group(0)

    return _RELACION.sub(relacion, xml), ids, vinculos


def _parte_tipos(xml: str, quitadas: set[str], medios: dict[str, str]) -> str:
    def override(m: re.Match[str]) -> str:
        parte = _atributos(m.group("attrs")).get("PartName", "").lstrip("/")
        return "" if parte.startswith(tuple(quitadas)) or parte in medios else m.group(0)

    xml = re.sub(
        rf"<(?P<p>(?:\w+:)?)Override\b(?P<attrs>{_ATRS})(?:/>|>\s*</(?P=p)Override>)", override, xml
    )
    if medios and not re.search(r"<(?:\w+:)?Default\b[^>]*Extension\s*=\s*\"png\"", xml, re.I):
        xml = re.sub(
            rf"(<(?:\w+:)?Types\b{_ATRS}>)",
            r'\g<1><Default Extension="png" ContentType="image/png"/>',
            xml,
            count=1,
        )
    return xml


def _lugares(paquete: dict[str, bytes]) -> dict[str, str]:
    """Parte de cada hoja -> nombre de la hoja, para el informe."""
    libro = paquete.get("xl/workbook.xml", b"").decode("utf-8", "replace")
    rels = paquete.get("xl/_rels/workbook.xml.rels", b"").decode("utf-8", "replace")
    destinos = {}
    for m in _RELACION.finditer(rels):
        a = _atributos(m.group("attrs"))
        destinos[a.get("Id")] = _resolver("xl", a.get("Target", ""))
    lugares = {}
    for m in _APERTURA.finditer(libro):
        if _local(m.group("tag")) != "sheet":
            continue
        crudos = {
            mm.group("nombre"): _des_xml(mm.group("valor"))
            for mm in _ATRIBUTO.finditer(m.group("attrs"))
        }
        rid = next((v for k, v in crudos.items() if _local(k) == "id" and ":" in k), None)
        if rid in destinos:
            lugares[destinos[rid]] = crudos.get("name", destinos[rid])
    return lugares


def _comprobar_entrada(nombre: str, contenido: bytes) -> None:
    """Toda parte XML de la ENTRADA debe leerse con defusedxml (sin DTD ni entidades)."""
    if nombre.endswith(".vml"):
        # El VML de Excel no siempre es XML bien formado; basta con que no declare nada.
        if re.search(rb"<!(?:DOCTYPE|ENTITY)", contenido):
            raise PaqueteInseguroError(f"{nombre}: declara DTD o entidades")
        return
    try:
        xml_seguro(contenido, forbid_dtd=True)
    except DefusedXmlException as error:
        raise PaqueteInseguroError(f"{nombre}: {type(error).__name__}") from error
    except ParseError as error:
        raise PaqueteInseguroError(f"{nombre}: XML mal formado ({error})") from error


def _es_xml(nombre: str) -> bool:
    return nombre.endswith((".xml", ".rels", ".vml")) or nombre == "[Content_Types].xml"


def comprobar_paquete(paquete: dict[str, bytes]) -> None:
    """Antes de leer nada con openpyxl: ninguna parte XML trae DTD ni entidades y todas estan
    bien formadas. Lanza `PaqueteInseguroError`."""
    for nombre, contenido in paquete.items():
        if _es_xml(nombre):
            _comprobar_entrada(nombre, contenido)


def anonimizar_paquete(
    infos: list[zipfile.ZipInfo], paquete: dict[str, bytes], ctx: Contexto
) -> list[tuple[zipfile.ZipInfo, bytes]]:
    """Devuelve las entradas de la SALIDA, en el orden de la ENTRADA (ya `comprobar_paquete`)."""
    quitadas = {n for n in paquete if n.startswith(QUITADAS)}
    ctx.quitado["partes de vinculos externos"] += sum(
        1 for n in quitadas if n.startswith("xl/externalLinks/") and not n.endswith(".rels")
    )
    ctx.quitado["configuraciones de impresora"] += sum(
        1 for n in quitadas if n.startswith("xl/printerSettings/")
    )
    originales = sorted(n for n in paquete if n.startswith(MEDIA) and not n.endswith("/"))
    medios = {n: f"{MEDIA}anonimo{i}.png" for i, n in enumerate(originales, start=1)}
    ctx.quitado["imagenes sustituidas por el PNG neutro"] += len(medios)

    nuevos: dict[str, bytes] = {}
    ids_quitados: dict[str, set[str]] = {}
    for nombre, contenido in paquete.items():
        if nombre.endswith(".rels") and not nombre.startswith(tuple(quitadas)):
            xml, ids, vinculos = _parte_rels(contenido.decode("utf-8"), nombre, quitadas, medios)
            ids_quitados[_origen_de_rels(nombre)[0]] = ids
            ctx.quitado["relaciones de hipervinculo"] += vinculos
            nuevos[nombre] = xml.encode("utf-8")

    for nombre, contenido in paquete.items():
        if nombre in nuevos or nombre in quitadas or nombre in medios or not _es_xml(nombre):
            continue
        try:
            xml = contenido.decode("utf-8")
        except UnicodeDecodeError as error:
            raise PaqueteInseguroError(f"{nombre}: no esta en UTF-8") from error
        if nombre == "[Content_Types].xml":
            xml = _parte_tipos(xml, quitadas, medios)
        elif nombre == "docProps/custom.xml":
            ctx.quitado["propiedades personalizadas vaciadas"] += xml.count("<property")
            nuevos[nombre] = CUSTOM_VACIO
            continue
        elif nombre == "docProps/core.xml":
            xml = _parte_propiedades(xml, ctx, nombre, CAMPOS_CORE)
        elif nombre == "docProps/app.xml":
            xml = _parte_propiedades(xml, ctx, nombre, CAMPOS_APP)
        elif nombre == "xl/workbook.xml":
            xml = _parte_libro(xml, ctx, nombre)
        elif nombre.startswith(HOJAS) and nombre.endswith(".xml"):
            xml = _parte_hoja(xml, ctx, nombre)
        elif _es_parte_de_comentarios(nombre):
            xml = _parte_comentarios(xml, ctx, nombre)
        else:
            xml = _parte_generica(xml, ctx, nombre)
        for rid in ids_quitados.get(nombre, set()):
            # Solo quedan atributos opcionales (el r:id de <pageSetup>): los bloques que
            # dependian de la relacion (hipervinculos, referencias externas) ya se quitaron.
            xml = re.sub(rf"\s\w+:(?:id|embed|link|pict)\s*=\s*\"{re.escape(rid)}\"", "", xml)
        nuevo = xml.encode("utf-8")
        if nuevo != contenido:
            if not nombre.endswith(".vml"):
                try:
                    xml_seguro(nuevo, forbid_dtd=True)
                except (ParseError, DefusedXmlException) as error:
                    raise PaqueteInseguroError(
                        f"{nombre}: la reescritura no es XML valido"
                    ) from error
            nuevos[nombre] = nuevo

    salida: list[tuple[zipfile.ZipInfo, bytes]] = []
    for info in infos:
        nombre = info.filename
        if nombre in quitadas:
            continue
        if nombre in medios:
            salida.append((_info(info, medios[nombre]), PNG_NEUTRO))
        else:
            salida.append((_info(info, nombre), nuevos.get(nombre, paquete[nombre])))
    return salida


def _info(original: zipfile.ZipInfo, nombre: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(nombre, date_time=original.date_time)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = original.external_attr
    return info


# --- Verificacion ------------------------------------------------------------------------------


def _vistas(xml: str) -> Iterator[str]:
    """El texto de una parte XML tal como se buscaria a mano: los tramos de formato unidos, cada
    elemento en su linea; y, aparte, cada valor de atributo (salvo los GUID)."""
    sin_formato = re.sub(
        rf"<(?P<p>(?:\w+:)?)rPr\b{_ATRS}(?:/>|>.*?</(?P=p)rPr>)", "", xml, flags=re.S
    )
    sin_tramos = re.sub(r"</?(?:\w+:)?[rt](?:\s[^>]*)?/?>", "", sin_formato)
    yield _des_ooxml(_des_xml(re.sub(r"<[^>]*>", "\n", sin_tramos)))
    valores = []
    for m in _APERTURA.finditer(xml):
        for a in _ATRIBUTO.finditer(m.group("attrs")):
            valor = _des_xml(a.group("valor"))
            if _tiene_letra(valor) and not _GUID.fullmatch(valor):
                valores.append(valor)
    yield "\n".join(valores)


def _comprobar_estructura(nombre: str, xml: str, restos: dict[str, int]) -> None:
    if re.search(r"<(?:\w+:)?(?:hyperlinks|hlinkClick|hlinkHover)\b", xml):
        restos["hipervinculo"] += 1
    if re.search(r"<(?:\w+:)?externalReferences?\b|absPath\b", xml):
        restos["vinculo externo o ruta de origen"] += 1
    if nombre == "xl/workbook.xml":
        for m in re.finditer(r"<(?:\w+:)?definedName\b[^>]*>([^<]*)<", xml):
            if re.search(r"\[\d+\]", _des_xml(m.group(1))):
                restos["nombre definido externo"] += 1
    for m in re.finditer(
        rf"<(?P<p>(?:\w+:)?)dataValidation\b(?P<attrs>{_ATRS})(?:/>|>(?P<cuerpo>.*?)"
        rf"</(?P=p)dataValidation>)",
        xml,
        flags=re.S,
    ):
        if _es_lista_literal(m.group("cuerpo") or "", m.group("attrs")):
            restos["lista de validacion literal"] += 1
    if nombre.endswith(".rels"):
        for m in _RELACION.finditer(xml):
            if _atributos(m.group("attrs")).get("Type", "").endswith(TIPOS_REL_QUITADOS):
                restos["relacion que debia quitarse"] += 1
    if nombre == "docProps/core.xml":
        campos = "|".join(CAMPOS_CORE)
        for m in re.finditer(rf"<((?:\w+:)?(?:{campos}))\b[^>]*>([^<]*)</\1>", xml):
            if m.group(2).strip() not in ("", ANONIMO):
                restos["propiedad del documento"] += 1
    if nombre == "docProps/app.xml":
        if re.search(r"<(?:\w+:)?HyperlinkBase\b", xml):
            restos["propiedad del documento"] += 1
        for m in re.finditer(r"<((?:\w+:)?(?:Company|Manager))\b[^>]*>([^<]*)</\1>", xml):
            if m.group(2).strip() not in ("", ANONIMO):
                restos["propiedad del documento"] += 1
    if nombre == "docProps/custom.xml" and "<property" in xml:
        restos["propiedad personalizada"] += 1
    if nombre.startswith("xl/comments"):
        for autor in re.findall(r"<(?:\w+:)?author>([^<]*)</", xml):
            if autor not in ("", ANONIMO):
                restos["autor de comentario"] += 1


def _comprobar_relaciones(contenido: dict[str, bytes], restos: dict[str, int]) -> None:
    """Cada relacion interna y cada tipo de contenido apuntan a una parte que existe, y cada
    `r:id` de una parte esta en sus relaciones."""
    for nombre, datos in contenido.items():
        if not nombre.endswith(".rels"):
            continue
        origen, base = _origen_de_rels(nombre)
        ids = set()
        for m in _RELACION.finditer(datos.decode("utf-8")):
            a = _atributos(m.group("attrs"))
            ids.add(a.get("Id"))
            if (
                a.get("TargetMode") != "External"
                and _resolver(base, a.get("Target", "")) not in contenido
            ):
                restos["relacion rota"] += 1
        if origen in contenido and _es_xml(origen):
            usados = _REF_RELACION.findall(contenido[origen].decode("utf-8", "replace"))
            restos["referencia rota"] += sum(1 for r in usados if r not in ids)
    for nombre, datos in contenido.items():
        if (
            _es_xml(nombre)
            and not nombre.endswith(".rels")
            and f"{posixpath.dirname(nombre)}/_rels/{posixpath.basename(nombre)}.rels".lstrip("/")
            not in contenido
        ):
            if _REF_RELACION.search(datos.decode("utf-8", "replace")):
                restos["referencia rota"] += 1
    tipos = contenido.get("[Content_Types].xml", b"").decode("utf-8")
    for m in re.finditer(r"<(?:\w+:)?Override\b[^>]*PartName\s*=\s*\"([^\"]*)\"", tipos):
        if unquote(m.group(1)).lstrip("/") not in contenido:
            restos["tipo de contenido huerfano"] += 1


def verificar(salida: Path, datos: list[Dato], autores: list[Dato] | None = None) -> dict[str, int]:
    """Relee la SALIDA entrada por entrada (XML crudo) y cuenta lo que sobrevive, por tipo."""
    autores = autores or []
    restos: dict[str, int] = defaultdict(int)
    with zipfile.ZipFile(salida) as paquete:
        contenido = {n: paquete.read(n) for n in paquete.namelist()}
    for nombre, binario in contenido.items():
        if nombre.startswith(QUITADAS):
            restos["parte que debia quitarse"] += 1
        if nombre.startswith(MEDIA):
            if binario != PNG_NEUTRO:
                restos["imagen"] += 1
            continue
        if _es_xml(nombre):
            try:
                xml = binario.decode("utf-8")
            except UnicodeDecodeError:
                restos["parte ilegible"] += 1
                continue
            if not nombre.endswith(".vml"):
                try:
                    xml_seguro(binario, forbid_dtd=True)
                except (ParseError, DefusedXmlException):
                    restos["XML invalido"] += 1
            _comprobar_estructura(nombre, xml, restos)
            vistas = list(_vistas(xml))
        else:
            vistas = [
                binario.decode("latin-1"),
                binario.decode("utf-16-le", "ignore"),
                binario[1:].decode("utf-16-le", "ignore"),
            ]
        buscados = datos + autores if _es_parte_de_comentarios(nombre) else datos
        for vista in vistas:
            for dato in buscados:
                if dato.patron.search(vista):
                    restos[dato.tipo] += 1
            if any(m.group(0) != RIF_NEUTRO for m in RIF.finditer(vista)):
                restos["rif"] += 1
    _comprobar_relaciones(contenido, restos)
    try:
        openpyxl.load_workbook(salida, keep_links=False).close()
    except Exception:  # noqa: BLE001 - cualquier fallo de lectura invalida el caso
        restos["no abre con openpyxl"] += 1
    return {tipo: n for tipo, n in restos.items() if n}


# --- Informe y CLI -----------------------------------------------------------------------------


def _imprimir_informe(datos: list[Dato], autores: list[Dato], ctx: Contexto) -> None:
    por_tipo: dict[str, int] = defaultdict(int)
    for dato in datos + autores:
        por_tipo[dato.tipo] += 1
    print("Datos descubiertos (variantes por tipo):")
    for tipo, n in sorted(por_tipo.items()):
        print(f"  {tipo}: {n}")
    print("Textos cambiados por tipo de dato (cadena, formula, valor o atributo):")
    if not ctx.informe:
        print("  (ninguno)")
    for tipo in sorted(ctx.informe):
        lugares = ctx.informe[tipo]
        total = sum(lugares.values())
        detalle = ", ".join(f"{h}={n}" for h, n in sorted(lugares.items()))
        print(f"  {tipo}: {total} [{detalle}]")
    print("Quitado o neutralizado:")
    for que, n in sorted(ctx.quitado.items()):
        print(f"  {que}: {n}")
    print(f"Propiedades del documento: '{ANONIMO}'")


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("entrada", type=Path, help="libro real (.xlsx); no se modifica")
    analizador.add_argument("salida", type=Path, help="libro anonimizado (.xlsx)")
    analizador.add_argument(
        "--etiqueta", default="A", help="letra del caso: CLIENTE-<etiqueta>, CONTRATISTA-..."
    )
    args = analizador.parse_args(argv)

    entrada: Path = args.entrada
    salida: Path = args.salida
    if not entrada.is_file():
        print(f"No existe la ENTRADA: {entrada}", file=sys.stderr)
        return 2
    if salida.resolve() == entrada.resolve() or (salida.exists() and salida.samefile(entrada)):
        print(
            "La SALIDA no puede ser la ENTRADA: el libro real no se sobrescribe.", file=sys.stderr
        )
        return 2
    etiqueta = args.etiqueta.strip()
    if not etiqueta:
        print("La etiqueta no puede estar vacia.", file=sys.stderr)
        return 2
    try:
        with zipfile.ZipFile(entrada) as zip_entrada:
            infos = [i for i in zip_entrada.infolist() if not i.is_dir()]
            paquete = {i.filename: zip_entrada.read(i) for i in infos}
    except zipfile.BadZipFile:
        print(f"La ENTRADA no es un libro .xlsx (no es un ZIP): {entrada}", file=sys.stderr)
        return 2
    try:
        comprobar_paquete(paquete)
    except PaqueteInseguroError as error:
        print(f"No se anonimiza: {error}", file=sys.stderr)
        return 1

    libro = openpyxl.load_workbook(entrada, keep_links=False)
    datos = descubrir(libro, etiqueta)
    libro.close()
    if not any(d.tipo in ("cliente", "contratista") for d in datos):
        print(
            "No se encontraron los rotulos CLIENTE/CONTRATISTA en la PORTADA: "
            "no se puede garantizar el anonimato y no se escribe nada.",
            file=sys.stderr,
        )
        return 1
    autores = descubrir_autores(paquete)

    ctx = Contexto(datos=datos, autores=autores, lugares=_lugares(paquete))
    try:
        entradas = anonimizar_paquete(infos, paquete, ctx)
    except PaqueteInseguroError as error:
        print(f"No se anonimiza: {error}", file=sys.stderr)
        return 1
    salida.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zip_salida:
        for info, contenido in entradas:
            zip_salida.writestr(info, contenido)
    _imprimir_informe(datos, autores, ctx)

    restos = verificar(salida, datos, autores)
    if restos:
        salida.unlink(missing_ok=True)
        detalle = ", ".join(f"{t}={n}" for t, n in sorted(restos.items()))
        print(f"VERIFICACION FALLIDA, SALIDA borrada. Restos por tipo: {detalle}", file=sys.stderr)
        return 1
    print(f"Verificacion: ningun dato descubierto aparece en la SALIDA ({salida.name}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
