"""PDF de presupuestos de la empresa (spec 1.5 §3, reglas L10 y L11).

Hay dos clases de PDF y cada una tiene su lectura:

1. **PDF simple** (los presupuestos 001 y 002): un documento sin modelo de cálculo detrás, con una
   página "COMPUTOS MÉTRICOS" (Items, Descripción, Unidad, Cantidad, "Total computos métricos") y
   una página "Presupuesto" (Items, Descripción, Unidad, Cantidad, Precio Unitario, Total ($),
   "TOTAL PRESUPUESTO"), notas que empiezan con `*` y celdas resaltadas. No hay fórmulas que
   auditar: lo único que se puede comprobar es que el documento no se contradiga a sí mismo, y eso
   es la regla **L10** (`reglas_pdf_simple`).
2. **PDF impreso desde el libro** de Excel: lo que la empresa entregó al cliente. Solo interesa el
   bloque de totales (sin IVA, IVA y total), para cotejarlo con el libro que se audita: si no
   coinciden, el libro no es la versión entregada (regla **L11**, `cotejar_con_libro`).

Por qué las filas se reconstruyen por coordenadas y no con `extract_text`: el texto corrido mezcla
columnas (el número de ítem queda a veces una línea por encima o por debajo de su descripción, y
el monto total de la fila sale antes que la descripción). Se leen las palabras con su caja
(`extract_words`), las columnas salen de la cabecera de la tabla (y de las líneas verticales del
cuadriculado cuando las hay) y las filas, de las líneas horizontales del cuadriculado; sin
cuadriculado, de las líneas de texto. Las coordenadas son `float` porque son posiciones en la
página, no cantidades: todo número del presupuesto es `Decimal` (NORMAS §2.3).

`pdfplumber` (licencia MIT) se importa dentro de las funciones que leen, para que el resto del
adaptador no dependa del extra `pdf`. No se usa PyMuPDF (AGPL).

El PDF viene de fuera (revisión de seguridad 1.5): antes de abrirlo se mira el tamaño (el mismo
tope que el libro, `guardia.MAX_BYTES`), la cabecera `%PDF-` y, en los bytes crudos, `/Encrypt` y
`/JavaScript`; al abrirlo, el número de páginas (≤ 60). Cualquier falla al abrir o leer (pdfminer
lanza tipos muy variados ante un PDF dañado u hostil) se convierte en `ArchivoRechazado` con un
mensaje fijo para el usuario, sin el texto técnico de la excepción.

Lo que no sigue la convención no se adivina: un renglón sin descripción ni cifras se descarta como
fila vacía de la plantilla, un precio escrito como expresión (`3*99.75`) se guarda como texto y no
como número, y un renglón de cómputos que no se empareja con uno del presupuesto se informa en vez
de forzar el emparejamiento.
"""

from __future__ import annotations

import difflib
import hashlib
import io
import re
import unicodedata
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from adapters.hoja_empresa.guardia import MAX_BYTES, ArchivoRechazado
from core.contracts.verificacion import Hallazgo, Severidad

if TYPE_CHECKING:
    from adapters.hoja_empresa.modelo import LibroLeido

__all__ = [
    "MAX_BYTES_PDF",
    "MAX_PAGINAS_PDF",
    "TOLERANCIA",
    "UMBRAL_SIMILITUD",
    "PdfSimple",
    "RenglonPdf",
    "TotalesImpresos",
    "cotejar_con_libro",
    "leer_pdf_simple",
    "leer_totales_impresos",
    "reglas_pdf_simple",
]

#: Tolerancia de cuadre de montos (USD): medio céntimo, la mitad de la unidad impresa. Por debajo
#: de ella una diferencia es redondeo de la impresión, no un error del documento.
TOLERANCIA = Decimal("0.005")

#: Similitud mínima (difflib, 0 a 1) para emparejar un renglón de cómputos con uno del presupuesto.
#: SUPUESTO_DECLARADO (spec 1.5, encargo de L10): las descripciones de la página de presupuesto
#: salen truncadas por el ancho de la celda; 0,8 empareja "Teipe Eléctrico Negro Cobra (Blister)"
#: con "Teipe Eléctrico Negro Cobra" sin emparejar dos productos distintos de la misma familia.
UMBRAL_SIMILITUD = Decimal("0.8")

#: Tamaño máximo del PDF que se abre. SUPUESTO_DECLARADO: el mismo tope que F-D10 fija para el
#: libro (se reutiliza `guardia.MAX_BYTES`, 25 MB); el PDF impreso más pesado recibido ronda 6,3 MB.
MAX_BYTES_PDF = MAX_BYTES

#: Páginas máximas del PDF. SUPUESTO_DECLARADO (revisión de seguridad 1.5): el PDF real más largo
#: tiene 24 páginas (medido el 2026-10-13); 60 deja margen y acota el trabajo de pdfminer, que
#: analiza cada página entera para extraer sus palabras.
MAX_PAGINAS_PDF = 60

#: Mensaje fijo cuando el PDF no se puede abrir o leer: el texto técnico de pdfminer no le dice
#: nada al usuario y podría mostrar rutas internas.
_PDF_ILEGIBLE = (
    "El PDF «{nombre}» no se pudo leer: está dañado, protegido o no es un PDF de presupuesto. "
    "Imprímalo de nuevo a PDF desde el programa original."
)

_REGLA_PDF = "L10"
_REGLA_COTEJO = "L11"

# Subtipos de L10: van al principio de la descripción para que el informe los agrupe.
_SUB_UNIDADES = "suma de unidades distintas"
_SUB_INCOHERENTE = "unidad × cantidad × precio incoherente"
_SUB_ARITMETICA = "aritmética de fila"
_SUB_COMPUTOS = "cómputos ≠ presupuesto"
_SUB_PENDIENTE = "precio pendiente entregado como firme"
_SUB_NOTA = "nota que contradice el total"
_SUB_SUMA = "suma de renglones ≠ total impreso"

#: Unidades de longitud: si el precio está dado por pieza (rollo, tubo) y la cantidad en metros, el
#: total sale de otra cantidad (H13).
_UNIDADES_LONGITUD = frozenset(
    {"m", "ml", "mt", "mts", "metro", "metros", "metro lineal", "metros lineales"}
)

_COLUMNAS = ("item", "descripcion", "unidad", "cantidad", "precio", "total")
_COLUMNAS_NUMERICAS = frozenset({"cantidad", "precio", "total"})

_RE_FECHA = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")
_RE_EXPRESION = re.compile(r"^\s*(\d[\d.,]*)\s*[*xX×]\s*(\d[\d.,]*)\s*$")
_RE_PORCENTAJE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
_RE_MONTO = re.compile(r"\(?[-−]?\s*\$?\s*\d[\d.,]*\)?%?")


# --- Modelo ---------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RenglonPdf:
    """Una fila de la tabla de cómputos (página con Items/Descripción/Unidad/Cantidad) o de la de
    presupuesto (además Precio Unitario y Total).

    `precio_texto` es el precio tal como está impreso: puede ser una expresión (`3*99.75`) que no
    es un precio unitario, y entonces `precio` es None (no se elige un factor en silencio). En la
    tabla de cómputos `precio_texto` es "" y `precio`/`total` son None. `resaltado` es True si un
    rectángulo amarillo de relleno cubre la fila.
    """

    pagina: int
    item: str
    descripcion: str
    unidad: str
    cantidad: Decimal | None
    precio_texto: str
    precio: Decimal | None
    total: Decimal | None
    resaltado: bool


@dataclass(frozen=True, slots=True)
class PdfSimple:
    """Un PDF simple leído: sus dos tablas, los totales impresos y las notas.

    `total_computos` es el número de la fila "Total computos métricos"; `total_impreso`, el de
    "TOTAL PRESUPUESTO". `notas` va en el orden del documento y sin el `*` inicial; una nota
    repetida en el PDF se conserva repetida (las reglas la cuentan una vez). `numero` y `fecha`
    son los que el PDF imprime junto a "Fecha:" (texto, sin interpretar).
    """

    nombre: str
    sha256: str
    computos: tuple[RenglonPdf, ...]
    presupuesto: tuple[RenglonPdf, ...]
    total_computos: Decimal | None
    total_impreso: Decimal | None
    notas: tuple[str, ...]
    numero: str
    fecha: str


@dataclass(frozen=True, slots=True)
class TotalesImpresos:
    """El bloque de totales de un PDF impreso desde el libro.

    Si el PDF trae varios bloques distintos (por ejemplo "OPCIÓN B" y "OPCIÓN DEFINITIVA") se toma
    el ÚLTIMO, que es el que el documento presenta como definitivo; `bloques` cuenta los bloques
    distintos encontrados, `opcion` es el rótulo "OPCIÓN …" que precede al elegido y `nota` lo
    explica para el informe. `pagina` es la página del bloque elegido (1-indexada).
    """

    nombre: str
    subtotal: Decimal | None
    iva: Decimal | None
    total: Decimal | None
    paginas: int
    pagina: int | None = None
    bloques: int = 0
    opcion: str = ""
    nota: str = ""


# --- Texto y números ------------------------------------------------------------------------------


def _limpiar(texto: str) -> str:
    """Quita lo que la impresión mete en el texto: espacio duro, guion blando, espacios dobles."""
    texto = texto.replace("\xa0", " ").replace(" ", " ").replace("\xad", "-")
    return re.sub(r"\s+", " ", texto).strip()


def _normalizar(texto: str) -> str:
    """Minúsculas, sin acentos y sin espacios de más: la forma en que se comparan descripciones."""
    descompuesto = unicodedata.normalize("NFKD", _limpiar(texto).lower())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def _numero(texto: str) -> Decimal | None:
    """Interpreta un número impreso con cualquiera de las dos convenciones (`24,311.92` o
    `24.311,92`).

    Decide por la posición del último separador: si aparecen los dos, el último es el decimal. Si
    aparece uno solo una vez, es de miles cuando lo siguen exactamente tres dígitos y la parte
    entera no es 0 (`1,109` = 1109); si no, es decimal (`99.75`, `0,125`). Devuelve None si el
    texto no es un número (una expresión, un rótulo, vacío).
    """
    t = _limpiar(texto).replace(" ", "").replace("$", "").replace("USD", "")
    negativo = False
    if t.startswith("(") and t.endswith(")"):
        negativo, t = True, t[1:-1]
    if t[:1] in ("-", "−"):
        negativo, t = True, t[1:]
    if not t or not re.fullmatch(r"[\d.,]+", t) or not re.search(r"\d", t):
        return None
    coma, punto = t.rfind(","), t.rfind(".")
    if coma >= 0 and punto >= 0:
        decimal_sep = "," if coma > punto else "."
        miles = "." if decimal_sep == "," else ","
        t = t.replace(miles, "").replace(decimal_sep, ".")
    elif coma >= 0 or punto >= 0:
        sep = "," if coma >= 0 else "."
        partes = t.split(sep)
        if len(partes) > 2:
            if not all(len(p) == 3 for p in partes[1:]):
                return None
            t = "".join(partes)
        else:
            entero, fraccion = partes
            if len(fraccion) == 3 and entero not in ("", "0"):
                t = entero + fraccion
            else:
                t = (entero or "0") + "." + fraccion
    try:
        valor = Decimal(t)
    except InvalidOperation:
        return None
    return -valor if negativo else valor


def _expresion(texto: str) -> tuple[Decimal, Decimal] | None:
    """`3*99.75` -> (3, 99.75). Un precio escrito como producto no es un precio unitario: dice
    cuántas unidades de precio se cobran (3 tubos) y a cuánto (99,75)."""
    m = _RE_EXPRESION.match(_limpiar(texto))
    if m is None:
        return None
    a, b = _numero(m.group(1)), _numero(m.group(2))
    if a is None or b is None:
        return None
    return a, b


def _fmt(valor: Decimal, signo: bool = False) -> str:
    """Cifra para el texto del informe, con la convención venezolana (1.446,65)."""
    if valor == valor.to_integral_value():
        texto = f"{valor.quantize(Decimal(1)):{'+' if signo else ''},}"
    else:
        decimales = min(4, max(2, -int(valor.as_tuple().exponent)))
        texto = f"{valor:{'+' if signo else ''},.{decimales}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _es_longitud(unidad: str) -> bool:
    return _normalizar(unidad).rstrip(".") in _UNIDADES_LONGITUD


# --- Geometría de la página ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Palabra:
    texto: str
    x0: float
    x1: float
    top: float
    bottom: float

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def yc(self) -> float:
        return (self.top + self.bottom) / 2


@dataclass(frozen=True, slots=True)
class _Caja:
    """Un rectángulo o una línea dibujados en la página (cuadriculado o resaltado)."""

    x0: float
    x1: float
    top: float
    bottom: float


@dataclass(frozen=True, slots=True)
class _Tabla:
    tipo: str  # "computos" o "presupuesto"
    renglones: tuple[RenglonPdf, ...]
    total: Decimal | None
    notas: tuple[str, ...]


def _palabras(page: Any) -> list[_Palabra]:
    salida = []
    for w in page.extract_words(keep_blank_chars=False, use_text_flow=False):
        texto = _limpiar(str(w["text"]))
        if texto:
            salida.append(
                _Palabra(texto, float(w["x0"]), float(w["x1"]), float(w["top"]), float(w["bottom"]))
            )
    return salida


def _lineas(palabras: Iterable[_Palabra], tolerancia: float = 4.0) -> list[list[_Palabra]]:
    """Agrupa palabras en líneas de texto: misma línea si su borde superior difiere ≤ 4 pt (el
    número de ítem suele quedar 1 pt por encima o por debajo de la descripción)."""
    lineas: list[list[_Palabra]] = []
    for p in sorted(palabras, key=lambda p: (p.top, p.x0)):
        if lineas and p.top - lineas[-1][0].top <= tolerancia:
            lineas[-1].append(p)
        else:
            lineas.append([p])
    return [sorted(linea, key=lambda p: p.x0) for linea in lineas]


def _cajas(page: Any) -> list[_Caja]:
    objetos = list(getattr(page, "rects", []) or []) + list(getattr(page, "lines", []) or [])
    return [
        _Caja(float(o["x0"]), float(o["x1"]), float(o["top"]), float(o["bottom"])) for o in objetos
    ]


def _es_amarillo(color: object) -> bool:
    """Amarillo de resaltado en RGB (1, 1, 0) o crema (1, 1, 0,6), o en CMYK. Excluye blanco,
    gris, verde y naranja (las otras rellenos de la plantilla)."""
    if not isinstance(color, (tuple, list)):
        return False
    try:
        valores = tuple(float(c) for c in color)
    except (TypeError, ValueError):
        return False
    if len(valores) == 3:
        r, g, b = valores
        return r >= 0.85 and g >= 0.8 and b <= 0.7 and r - b >= 0.3
    if len(valores) == 4:
        c, m, y, k = valores
        return c <= 0.15 and m <= 0.2 and y >= 0.3 and k <= 0.15
    return False


def _amarillos(page: Any) -> list[_Caja]:
    return [
        _Caja(float(r["x0"]), float(r["x1"]), float(r["top"]), float(r["bottom"]))
        for r in getattr(page, "rects", []) or []
        if r.get("fill", True) and _es_amarillo(r.get("non_stroking_color"))
    ]


def _solapa(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


# --- Tabla: cabecera, columnas, filas -------------------------------------------------------------


def _columna_de(texto_normalizado: str) -> str | None:
    t = texto_normalizado
    if t.startswith("item"):
        return "item"
    if t.startswith("descrip"):
        return "descripcion"
    if t.startswith("unidad"):
        return "unidad"
    if t.startswith("cantidad"):
        return "cantidad"
    if t.startswith("precio") or t.startswith("unitario"):
        return "precio"
    if t.startswith("total"):
        return "total"
    return None


def _cabecera(palabras: Sequence[_Palabra]) -> tuple[dict[str, _Caja], float] | None:
    """Ubica la cabecera de la tabla por la palabra "Items" y devuelve la caja de cada columna y
    el borde inferior de la cabecera. La cabecera ocupa varias líneas ("Precio" encima de
    "Unitario", "Partidas" encima de "Descripción"), por eso se toma una franja alrededor."""
    ancla = next((p for p in palabras if _normalizar(p.texto).startswith("item")), None)
    if ancla is None:
        return None
    franja = [p for p in palabras if ancla.top - 25 <= p.top <= ancla.bottom + 3]
    anclas: dict[str, _Caja] = {}
    for p in franja:
        columna = _columna_de(_normalizar(p.texto))
        if columna is None:
            continue
        previa = anclas.get(columna)
        anclas[columna] = (
            _Caja(p.x0, p.x1, p.top, p.bottom)
            if previa is None
            else _Caja(
                min(previa.x0, p.x0),
                max(previa.x1, p.x1),
                min(previa.top, p.top),
                max(previa.bottom, p.bottom),
            )
        )
    if not {"item", "descripcion", "cantidad"} <= anclas.keys():
        return None
    return anclas, max(p.bottom for p in franja)


def _limites(
    anclas: dict[str, _Caja], verticales: Sequence[_Caja], y0: float, y1: float
) -> tuple[list[str], list[float]]:
    """Fronteras entre columnas: la línea vertical del cuadriculado que separa dos cabeceras; sin
    cuadriculado, un margen a la izquierda de la cabecera siguiente (el número de ítem, en cambio,
    se pega a su cabecera)."""
    orden = [c for c in _COLUMNAS if c in anclas]
    limites: list[float] = []
    for a, b in zip(orden, orden[1:], strict=False):
        izq, der = anclas[a], anclas[b]
        candidatas = [
            v
            for v in verticales
            if izq.x1 - 1 <= (v.x0 + v.x1) / 2 <= der.x0 + 1
            and _solapa(v.top, v.bottom, y0, y1) >= 10
        ]
        if candidatas:
            mejor = max(
                candidatas,
                key=lambda v: (_solapa(v.top, v.bottom, y0, y1), -abs((v.x0 + v.x1) / 2 - der.x0)),
            )
            limites.append((mejor.x0 + mejor.x1) / 2)
        elif a == "item":
            limites.append(izq.x1 + 8)
        else:
            limites.append(der.x0 - 4)
    return orden, limites


def _columna_por_x(x: float, orden: Sequence[str], limites: Sequence[float]) -> str:
    for nombre, limite in zip(orden, limites, strict=False):
        if x < limite:
            return nombre
    return orden[-1]


def _primera_palabra_alfabetica(linea: Sequence[_Palabra]) -> str:
    return next((_normalizar(p.texto) for p in linea if re.search(r"[A-Za-zÁ-ú]", p.texto)), "")


def _monto_de_linea(linea: Sequence[_Palabra]) -> Decimal | None:
    """El número de una línea de total: las palabras a la derecha del último rótulo, unidas sin
    espacio (la impresión parte `$ 1,109.29` en `$`, `1` y `,109.29`)."""
    ultimo_rotulo = max(
        (p.x1 for p in linea if re.search(r"[A-Za-zÁ-ú]", p.texto)), default=float("-inf")
    )
    cifras = "".join(p.texto for p in linea if p.x0 >= ultimo_rotulo)
    return _numero(cifras)


def _notas(lineas: Sequence[Sequence[_Palabra]]) -> list[str]:
    """Notas al pie: una línea que empieza con `*` abre una nota; una línea sin `*` continúa la
    nota anterior si está pegada a ella (≤ 18 pt), y si no abre una nota nueva."""
    notas: list[list[str]] = []
    ultimo_top: float | None = None
    for linea in lineas:
        texto = " ".join(p.texto for p in linea).strip()
        if not texto:
            continue
        top = linea[0].top
        if texto.startswith("*") or not notas or ultimo_top is None or top - ultimo_top > 18:
            notas.append([texto.lstrip("*").strip()])
        else:
            notas[-1].append(texto)
        ultimo_top = top
    return [" ".join(partes).strip() for partes in notas if " ".join(partes).strip()]


def _construir_renglon(
    pagina: int,
    palabras: Sequence[_Palabra],
    orden: Sequence[str],
    limites: Sequence[float],
    amarillos: Sequence[_Caja],
    y0: float,
    y1: float,
) -> RenglonPdf | None:
    celdas: dict[str, list[_Palabra]] = {c: [] for c in orden}
    for p in palabras:
        celdas[_columna_por_x(p.xc, orden, limites)].append(p)

    def texto(columna: str, separador: str = " ") -> str:
        orden_lectura = [p for linea in _lineas(celdas.get(columna, [])) for p in linea]
        return separador.join(p.texto for p in orden_lectura).strip()

    item = texto("item")
    descripcion = texto("descripcion")
    unidad = texto("unidad")
    cantidad_texto = texto("cantidad", "")
    precio_texto = texto("precio")
    total_texto = texto("total", "")
    if not (descripcion or unidad or cantidad_texto or precio_texto or total_texto):
        return None  # fila vacía de la plantilla (solo el número de ítem, o nada)
    x_min = min(limites[0] - 40, min(p.x0 for p in palabras))
    resaltado = any(
        _solapa(c.top, c.bottom, y0, y1) > 0.5 * min(c.bottom - c.top, y1 - y0)
        and _solapa(c.x0, c.x1, x_min, float("inf")) > 0
        for c in amarillos
    )
    return RenglonPdf(
        pagina=pagina,
        item=item,
        descripcion=descripcion,
        unidad=unidad,
        cantidad=_numero(cantidad_texto),
        precio_texto=precio_texto,
        precio=_numero(precio_texto.replace(" ", "")) if precio_texto else None,
        total=_numero(total_texto),
        resaltado=resaltado,
    )


def _grupos_por_bandas(
    palabras: Sequence[_Palabra], horizontales: Sequence[float], y0: float, y1: float
) -> list[tuple[list[_Palabra], float, float]]:
    bordes = [y0, *[y for y in horizontales if y0 < y < y1], y1]
    grupos = []
    for arriba, abajo in zip(bordes, bordes[1:], strict=False):
        dentro = [p for p in palabras if arriba <= p.yc < abajo]
        if dentro:
            grupos.append((dentro, arriba, abajo))
    return grupos


def _grupos_por_lineas(
    palabras: Sequence[_Palabra], orden: Sequence[str], limites: Sequence[float]
) -> list[tuple[list[_Palabra], float, float]]:
    """Sin cuadriculado: una línea con unidad o cifras, o con número de ítem y descripción (una
    partida global como "Micelaneos", sin cantidad), es una fila; una línea con solo
    descripción (descripción en dos líneas) o solo número de ítem se pega a la fila más cercana.
    Un número de ítem suelto a más de 10 pt de toda fila es una fila vacía y se descarta."""
    lineas = _lineas(palabras)
    columnas = [{_columna_por_x(p.xc, orden, limites) for p in linea} for linea in lineas]
    es_fila = [
        bool(cols & {"unidad", "cantidad", "precio", "total"}) or {"item", "descripcion"} <= cols
        for cols in columnas
    ]
    filas: dict[int, list[_Palabra]] = {i: list(lineas[i]) for i, f in enumerate(es_fila) if f}
    for i, linea in enumerate(lineas):
        if es_fila[i] or not filas:
            continue
        yc = sum(p.yc for p in linea) / len(linea)
        destino = min(
            filas, key=lambda j: (abs(sum(p.yc for p in lineas[j]) / len(lineas[j]) - yc), j)
        )
        distancia = abs(sum(p.yc for p in lineas[destino]) / len(lineas[destino]) - yc)
        if columnas[i] == {"item"} and distancia > 10:
            continue
        filas[destino].extend(linea)
    return [
        (ps, min(p.top for p in ps) - 2, max(p.bottom for p in ps) + 2)
        for _, ps in sorted(filas.items())
    ]


def _separadores(
    trazos: Sequence[_Caja], anclas: dict[str, _Caja], y0: float, y1: float
) -> list[float]:
    """Alturas de las líneas horizontales que separan filas.

    Los trazos a la misma altura (±1 pt) se juntan: la plantilla a veces dibuja el borde de una
    fila en dos tramos (sin borde bajo la celda de descripción). Una altura separa filas si sus
    tramos cubren la columna de ítem Y la de cantidad; así el subrayado azul de un vínculo bajo
    una descripción, que no llega a la columna de ítem, no parte una fila en dos.
    """
    item, cantidad = anclas["item"], anclas["cantidad"]
    x_cantidad = (cantidad.x0 + cantidad.x1) / 2
    niveles: list[list[_Caja]] = []
    for t in sorted(trazos, key=lambda t: (t.top + t.bottom) / 2):
        y = (t.top + t.bottom) / 2
        if not y0 - 1 < y < y1 + 1:
            continue
        if niveles and y - (niveles[-1][0].top + niveles[-1][0].bottom) / 2 <= 1:
            niveles[-1].append(t)
        else:
            niveles.append([t])
    return [
        (nivel[0].top + nivel[0].bottom) / 2
        for nivel in niveles
        if any(t.x0 <= item.x0 + 1 for t in nivel)
        and any(t.x0 <= x_cantidad <= t.x1 for t in nivel)
    ]


def _leer_tabla(pagina: int, page: Any, palabras: Sequence[_Palabra]) -> _Tabla | None:
    cabecera = _cabecera(palabras)
    if cabecera is None:
        return None
    anclas, fondo_cabecera = cabecera
    tipo = "presupuesto" if {"precio", "total"} <= anclas.keys() else "computos"
    lineas = _lineas(p for p in palabras if p.top > fondo_cabecera)

    linea_total: list[_Palabra] | None = None
    fin_tabla = float(page.height)
    indice_fin = len(lineas)
    for i, linea in enumerate(lineas):
        if _primera_palabra_alfabetica(linea).startswith("total"):
            linea_total, fin_tabla, indice_fin = linea, min(p.top for p in linea) - 0.5, i + 1
            break
        if linea[0].texto.startswith("*"):
            fin_tabla, indice_fin = min(p.top for p in linea) - 0.5, i
            break

    cajas = _cajas(page)
    verticales = [c for c in cajas if c.x1 - c.x0 <= 2 and c.bottom - c.top >= 10]
    orden, limites = _limites(anclas, verticales, fondo_cabecera, fin_tabla)
    horizontales = _separadores(
        [c for c in cajas if c.bottom - c.top <= 2], anclas, fondo_cabecera, fin_tabla
    )
    cuerpo = [p for p in palabras if fondo_cabecera < p.yc < fin_tabla]
    if len(horizontales) >= 2:
        grupos = _grupos_por_bandas(cuerpo, horizontales, fondo_cabecera, fin_tabla)
    else:
        grupos = _grupos_por_lineas(cuerpo, orden, limites)

    amarillos = _amarillos(page)
    renglones = tuple(
        r
        for ps, y0, y1 in grupos
        if (r := _construir_renglon(pagina, ps, orden, limites, amarillos, y0, y1)) is not None
    )
    total = _monto_de_linea(linea_total) if linea_total is not None else None
    return _Tabla(tipo, renglones, total, tuple(_notas(lineas[indice_fin:])))


def _numero_y_fecha(lineas: Sequence[Sequence[_Palabra]]) -> tuple[str, str]:
    """El número y la fecha que el PDF imprime como `001  Fecha: 18/05/2026`."""
    for linea in lineas:
        for i, p in enumerate(linea):
            if _normalizar(p.texto).rstrip(":") != "fecha":
                continue
            fecha = next((q.texto for q in linea[i + 1 :] if _RE_FECHA.match(q.texto)), "")
            numero = next((q.texto for q in reversed(linea[:i]) if q.texto.isdigit()), "")
            if fecha or numero:
                return numero, fecha
    return "", ""


def _verificar_bytes(datos: bytes, nombre: str) -> None:
    """Lo que se decide sin abrir el PDF: tamaño, cabecera, cifrado y JavaScript.

    `/Encrypt` y `/JavaScript` se buscan en los bytes crudos: un presupuesto impreso no los
    necesita, y un PDF cifrado no se puede leer sin su clave. Si el PDF los esconde dentro de un
    flujo comprimido, la búsqueda no los ve; no importa, porque pdfplumber no ejecuta JavaScript y
    un PDF cifrado falla al leerse (y esa falla también se rechaza).
    """
    if len(datos) > MAX_BYTES_PDF:
        raise ArchivoRechazado(
            f"El PDF «{nombre}» pesa {f'{len(datos) / 2**20:.1f}'.replace('.', ',')} MB y supera "
            f"el máximo de {MAX_BYTES_PDF // 2**20} MB."
        )
    if b"%PDF-" not in datos[:1024]:  # la norma admite bytes previos en el primer kilobyte
        raise ArchivoRechazado(f"El archivo «{nombre}» no es un PDF (no tiene la cabecera %PDF-).")
    if b"/Encrypt" in datos:
        raise ArchivoRechazado(
            f"El PDF «{nombre}» está cifrado o protegido con contraseña. Imprímalo de nuevo a PDF "
            "sin protección."
        )
    if b"/JavaScript" in datos:
        raise ArchivoRechazado(
            f"El PDF «{nombre}» contiene JavaScript, que un presupuesto no necesita. Se rechaza "
            "por seguridad: imprímalo de nuevo a PDF desde el programa original."
        )


def _paginas_declaradas(doc: Any) -> int | None:
    """El `/Count` del árbol de páginas, sin construir las páginas (None si no se puede leer)."""
    from pdfminer.pdftypes import resolve1

    raiz = resolve1(doc.doc.catalog.get("Pages"))
    cuenta = resolve1(raiz.get("Count")) if isinstance(raiz, dict) else None
    return cuenta if isinstance(cuenta, int) else None


@contextmanager
def _abrir(datos: bytes, nombre: str) -> Iterator[Any]:
    """Abre el PDF para leerlo dentro de un `with`; lanza `ArchivoRechazado` si no se debe abrir
    o si cualquier cosa falla al abrirlo o al leerlo.

    Las páginas se cuentan dos veces: primero el `/Count` que declara el documento (barato, antes
    de que pdfplumber construya cada página) y después `len(doc.pages)`, porque el `/Count` puede
    mentir. Las dos van antes de leer ninguna página.
    """
    _verificar_bytes(datos, nombre)
    try:
        import pdfplumber
    except ImportError as exc:
        raise ArchivoRechazado(
            "Esta instalación no puede leer PDF: falta el componente pdf."
        ) from exc
    try:
        doc = pdfplumber.open(io.BytesIO(datos))
    except Exception as exc:  # pdfminer lanza tipos muy variados ante un PDF dañado
        raise ArchivoRechazado(_PDF_ILEGIBLE.format(nombre=nombre)) from exc
    try:
        declaradas = _paginas_declaradas(doc)
        paginas = declaradas if declaradas is not None and declaradas > MAX_PAGINAS_PDF else None
        if paginas is None:
            paginas = len(doc.pages)
        if paginas > MAX_PAGINAS_PDF:
            raise ArchivoRechazado(
                f"El PDF «{nombre}» tiene {paginas} páginas y el máximo es {MAX_PAGINAS_PDF}. "
                "No parece un presupuesto."
            )
        yield doc
    except ArchivoRechazado:
        raise
    except Exception as exc:  # cualquier falla de lectura, dentro del `with` incluida
        raise ArchivoRechazado(_PDF_ILEGIBLE.format(nombre=nombre)) from exc
    finally:
        doc.close()


def leer_pdf_simple(datos: bytes, nombre: str) -> PdfSimple:
    """Lee un PDF simple (cómputos + presupuesto) y reconstruye sus filas.

    Cada página con una cabecera "Items … Cantidad" es una tabla: de presupuesto si la cabecera
    trae "Precio" y "Total", de cómputos si no. El total de cada tabla es la línea que empieza con
    "Total"; lo que sigue son notas. No calcula ni corrige nada: lo que el PDF dice se guarda tal
    cual para que `reglas_pdf_simple` lo contraste.
    """
    computos: list[RenglonPdf] = []
    presupuesto: list[RenglonPdf] = []
    notas: list[str] = []
    total_computos: Decimal | None = None
    total_impreso: Decimal | None = None
    numero = fecha = ""
    with _abrir(datos, nombre) as doc:
        for num, page in enumerate(doc.pages, start=1):
            palabras = _palabras(page)
            if not numero and not fecha:
                numero, fecha = _numero_y_fecha(_lineas(palabras))
            tabla = _leer_tabla(num, page, palabras)
            if tabla is None:
                continue
            if tabla.tipo == "presupuesto":
                presupuesto.extend(tabla.renglones)
                if tabla.total is not None:
                    total_impreso = tabla.total
            else:
                computos.extend(tabla.renglones)
                if tabla.total is not None:
                    total_computos = tabla.total
            notas.extend(tabla.notas)
    return PdfSimple(
        nombre=nombre,
        sha256=hashlib.sha256(datos).hexdigest(),
        computos=tuple(computos),
        presupuesto=tuple(presupuesto),
        total_computos=total_computos,
        total_impreso=total_impreso,
        notas=tuple(notas),
        numero=numero,
        fecha=fecha,
    )


# --- L10: reglas del PDF simple -------------------------------------------------------------------


def _origen(pdf: PdfSimple, r: RenglonPdf) -> str:
    if r.item:
        return f"PDF:{pdf.nombre}:p{r.pagina}:item{r.item}"
    return f"PDF:{pdf.nombre}:p{r.pagina}:«{r.descripcion[:40]}»"


def _origen_total(pdf: PdfSimple, renglones: Sequence[RenglonPdf]) -> str:
    pagina = renglones[-1].pagina if renglones else 1
    return f"PDF:{pdf.nombre}:p{pagina}:total"


def _nombre_renglon(r: RenglonPdf) -> str:
    return f"ítem {r.item or '(sin número)'} «{r.descripcion}»"


def _hallazgo(
    subtipo: str,
    severidad: Severidad,
    detalle: str,
    origen_ids: Iterable[str],
    impacto: Decimal | None = None,
    observado: Decimal | None = None,
    esperado: Decimal | None = None,
) -> Hallazgo:
    return Hallazgo(
        regla=_REGLA_PDF,
        severidad=severidad,
        descripcion=f"{subtipo}: {detalle}",
        impacto=impacto,
        origen_ids=tuple(origen_ids),
        valor_observado=observado,
        valor_esperado=esperado,
    )


def _regla_unidades(pdf: PdfSimple) -> list[Hallazgo]:
    """H14: el "Total computos métricos" suma metros con piezas, una cifra sin unidad."""
    if pdf.total_computos is None:
        return []
    por_unidad: dict[str, Decimal] = {}
    for r in pdf.computos:
        if r.cantidad is not None and r.unidad:
            clave = r.unidad.strip()
            por_unidad[clave] = por_unidad.get(clave, Decimal(0)) + r.cantidad
    if len({_normalizar(u) for u in por_unidad}) < 2:
        return []
    partes = " + ".join(f"{u} {_fmt(v)}" for u, v in por_unidad.items())
    return [
        _hallazgo(
            _SUB_UNIDADES,
            Severidad.ADVERTENCIA,
            f"el «Total computos métricos» ({_fmt(pdf.total_computos)}) suma cantidades de "
            f"unidades distintas ({partes}); la cifra no mide nada",
            [_origen_total(pdf, pdf.computos)],
            observado=pdf.total_computos,
        )
    ]


def _regla_filas(pdf: PdfSimple) -> list[Hallazgo]:
    """H13 y H17: cada fila del presupuesto debe cumplir cantidad × precio = total.

    Si no lo cumple, primero se mira si el total corresponde a otra cantidad de unidades de precio
    (el precio viene como `3*99.75`, o la unidad es de longitud y total ÷ precio es un entero
    distinto de la cantidad): eso es una incoherencia de unidad, el monto es el que se quiso y no
    hay impacto. Si no, es un error de aritmética y el impacto es lo que el total cobra de más.
    """
    hallazgos: list[Hallazgo] = []
    for r in pdf.presupuesto:
        if r.total is None:
            continue
        origen = [_origen(pdf, r)]
        expresion = _expresion(r.precio_texto) if r.precio is None else None
        if expresion is not None:
            veces, unitario = expresion
            producto = veces * unitario
            if r.cantidad is not None and r.cantidad != veces:
                esperado = r.cantidad * unitario
                hallazgos.append(
                    _hallazgo(
                        _SUB_INCOHERENTE,
                        Severidad.ERROR,
                        f"{_nombre_renglon(r)}: el precio está escrito como «{r.precio_texto}» "
                        f"({_fmt(veces)} × {_fmt(unitario)}), así que el total "
                        f"{_fmt(r.total)} cobra {_fmt(veces)} unidades de precio y no "
                        f"{_fmt(r.cantidad)} {r.unidad}; con {_fmt(r.cantidad)} {r.unidad} a "
                        f"{_fmt(unitario)} serían {_fmt(esperado)}",
                        origen,
                        observado=r.total,
                        esperado=esperado,
                    )
                )
            diferencia = r.total - producto
            if abs(diferencia) > TOLERANCIA:
                hallazgos.append(
                    _hallazgo(
                        _SUB_ARITMETICA,
                        Severidad.ERROR,
                        f"{_nombre_renglon(r)}: «{r.precio_texto}» = {_fmt(producto)} y el PDF "
                        f"imprime {_fmt(r.total)} ({_fmt(diferencia, signo=True)})",
                        origen,
                        impacto=diferencia,
                        observado=r.total,
                        esperado=producto,
                    )
                )
            continue
        if r.cantidad is None or r.precio is None:
            continue
        calculado = r.cantidad * r.precio
        diferencia = r.total - calculado
        if abs(diferencia) <= TOLERANCIA:
            continue
        if _es_longitud(r.unidad) and r.precio > 0:
            veces = (r.total / r.precio).quantize(Decimal(1), rounding=ROUND_HALF_UP)
            if veces >= 1 and veces != r.cantidad and abs(veces * r.precio - r.total) <= TOLERANCIA:
                hallazgos.append(
                    _hallazgo(
                        _SUB_INCOHERENTE,
                        Severidad.ERROR,
                        f"{_nombre_renglon(r)}: {_fmt(r.cantidad)} {r.unidad} × "
                        f"{_fmt(r.precio)} = {_fmt(calculado)}, pero el total {_fmt(r.total)} "
                        f"es {_fmt(veces)} × {_fmt(r.precio)}: el precio es por pieza (rollo, "
                        f"tubo) y la cantidad está en {r.unidad}",
                        origen,
                        observado=r.total,
                        esperado=calculado,
                    )
                )
                continue
        hallazgos.append(
            _hallazgo(
                _SUB_ARITMETICA,
                Severidad.ERROR,
                f"{_nombre_renglon(r)}: {_fmt(r.cantidad)} × {_fmt(r.precio)} = "
                f"{_fmt(calculado)} y el PDF imprime {_fmt(r.total)} "
                f"({_fmt(diferencia, signo=True)})",
                origen,
                impacto=diferencia,
                observado=r.total,
                esperado=calculado,
            )
        )
    return hallazgos


def _similitud(a: str, b: str) -> Decimal:
    """1 si las descripciones normalizadas son iguales; 0,95 si una es prefijo de la otra (la
    página de presupuesto trunca la descripción al ancho de la celda); si no, la razón de
    `difflib`."""
    na, nb = _normalizar(a), _normalizar(b)
    if not na or not nb:
        return Decimal(0)
    if na == nb:
        return Decimal(1)
    if min(len(na), len(nb)) >= 8 and (na.startswith(nb) or nb.startswith(na)):
        return Decimal("0.95")
    return Decimal(str(round(difflib.SequenceMatcher(None, na, nb).ratio(), 4)))


def _emparejar(
    computos: Sequence[RenglonPdf], presupuesto: Sequence[RenglonPdf]
) -> list[tuple[int, int]]:
    """Emparejamiento uno a uno, voraz y determinista: primero los pares más parecidos; a igual
    parecido, el que aparece antes en cada tabla."""
    candidatos = sorted(
        (
            (-s, i, j)
            for i, c in enumerate(computos)
            for j, p in enumerate(presupuesto)
            if (s := _similitud(c.descripcion, p.descripcion)) >= UMBRAL_SIMILITUD
        ),
    )
    usados_c: set[int] = set()
    usados_p: set[int] = set()
    pares = []
    for _, i, j in candidatos:
        if i in usados_c or j in usados_p:
            continue
        usados_c.add(i)
        usados_p.add(j)
        pares.append((i, j))
    return sorted(pares)


def _fila_cuadra(r: RenglonPdf) -> bool:
    return (
        r.cantidad is not None
        and r.precio is not None
        and r.total is not None
        and abs(r.cantidad * r.precio - r.total) <= TOLERANCIA
    )


def _regla_computos(pdf: PdfSimple) -> list[Hallazgo]:
    """H16: la página de cómputos y la de presupuesto del mismo PDF deben decir lo mismo.

    Cantidad distinta en un par emparejado: ERROR, con impacto (presupuesto − cómputos) × precio
    solo si la fila del presupuesto cuadra (si no cuadra, el precio no es por la unidad impresa y
    el producto no significaría nada). Unidad distinta o renglón sin pareja: ADVERTENCIA.
    """
    if not pdf.computos or not pdf.presupuesto:
        return []
    pares = _emparejar(pdf.computos, pdf.presupuesto)
    hallazgos: list[Hallazgo] = []
    for i, j in pares:
        c, p = pdf.computos[i], pdf.presupuesto[j]
        origen = [_origen(pdf, c), _origen(pdf, p)]
        if c.cantidad is not None and p.cantidad is not None and c.cantidad != p.cantidad:
            impacto = (
                (p.cantidad - c.cantidad) * p.precio
                if _fila_cuadra(p) and p.precio is not None
                else None
            )
            efecto = (
                f"; el presupuesto cobra {_fmt(impacto, signo=True)} respecto de lo medido"
                if impacto is not None
                else ""
            )
            hallazgos.append(
                _hallazgo(
                    _SUB_COMPUTOS,
                    Severidad.ERROR,
                    f"«{p.descripcion}»: {_fmt(c.cantidad)} {c.unidad} en cómputos (ítem "
                    f"{c.item}) y {_fmt(p.cantidad)} {p.unidad} en el presupuesto (ítem "
                    f"{p.item}){efecto}",
                    origen,
                    impacto=impacto,
                    observado=p.cantidad,
                    esperado=c.cantidad,
                )
            )
        if c.unidad and p.unidad and _normalizar(c.unidad) != _normalizar(p.unidad):
            hallazgos.append(
                _hallazgo(
                    _SUB_COMPUTOS,
                    Severidad.ADVERTENCIA,
                    f"«{p.descripcion}»: unidad «{c.unidad}» en cómputos y «{p.unidad}» en el "
                    f"presupuesto",
                    origen,
                )
            )
    emparejados_c = {i for i, _ in pares}
    emparejados_p = {j for _, j in pares}
    for i, c in enumerate(pdf.computos):
        if i not in emparejados_c:
            hallazgos.append(
                _hallazgo(
                    _SUB_COMPUTOS,
                    Severidad.ADVERTENCIA,
                    f"{_nombre_renglon(c)} de cómputos ({_fmt(c.cantidad) if c.cantidad else 's/c'}"
                    f" {c.unidad}) no tiene renglón en el presupuesto",
                    [_origen(pdf, c)],
                    observado=c.cantidad,
                )
            )
    for j, p in enumerate(pdf.presupuesto):
        if j not in emparejados_p:
            hallazgos.append(
                _hallazgo(
                    _SUB_COMPUTOS,
                    Severidad.ADVERTENCIA,
                    f"{_nombre_renglon(p)} del presupuesto (total "
                    f"{_fmt(p.total) if p.total is not None else 's/t'}) no tiene renglón en "
                    f"los cómputos",
                    [_origen(pdf, p)],
                    observado=p.total,
                )
            )
    return hallazgos


def _notas_unicas(pdf: PdfSimple) -> list[str]:
    """Las notas normalizadas, sin repetir (el PDF 002 repite notas copiadas del 001)."""
    vistas: dict[str, None] = {}
    for nota in pdf.notas:
        vistas.setdefault(_normalizar(nota), None)
    return list(vistas)


def _regla_notas(pdf: PdfSimple) -> list[Hallazgo]:
    """H15: notas que cambian el sentido del total.

    - Precio "en veremos" (o pendiente) y un renglón resaltado: el total lo cuenta como firme.
    - La mano de obra declarada como un % del total sin un renglón de mano de obra: el total no la
      incluye. El impacto es la lectura mínima (el % sobre el total impreso).
    - Una nota sobre misceláneos sin renglón de misceláneos: nota copiada de otro presupuesto.
    """
    hallazgos: list[Hallazgo] = []
    notas = _notas_unicas(pdf)
    pendientes = [n for n in notas if "en veremos" in n or "pendiente" in n or "por confirmar" in n]
    resaltados = [r for r in pdf.presupuesto if r.resaltado] or [
        r for r in pdf.computos if r.resaltado
    ]
    if pendientes:
        for r in resaltados:
            monto = f" ({_fmt(r.total)})" if r.total is not None else ""
            hallazgos.append(
                _hallazgo(
                    _SUB_PENDIENTE,
                    Severidad.ADVERTENCIA,
                    f"{_nombre_renglon(r)}{monto} está resaltado y una nota dice que ese "
                    f"precio está «en veremos»; el total lo suma como precio firme",
                    [_origen(pdf, r)],
                    observado=r.total,
                )
            )
        if not resaltados:
            hallazgos.append(
                _hallazgo(
                    _SUB_PENDIENTE,
                    Severidad.ADVERTENCIA,
                    "una nota dice que hay un precio «en veremos» y ningún renglón está "
                    "resaltado: no se puede saber cuál es",
                    [f"PDF:{pdf.nombre}:notas"],
                )
            )
    elif resaltados:
        for r in resaltados:
            hallazgos.append(
                _hallazgo(
                    _SUB_PENDIENTE,
                    Severidad.INFO,
                    f"{_nombre_renglon(r)} está resaltado y ninguna nota explica por qué",
                    [_origen(pdf, r)],
                )
            )

    descripciones = [_normalizar(r.descripcion) for r in pdf.presupuesto]
    hay_mano_obra = any("mano de obra" in d for d in descripciones)
    for nota in notas:
        porcentaje = _RE_PORCENTAJE.search(nota)
        if "mano de obra" not in nota or porcentaje is None or hay_mano_obra:
            continue
        pct = _numero(porcentaje.group(1))
        if pct is None:
            continue
        impacto = observado = esperado = None
        cifra = ""
        if pdf.total_impreso is not None:
            impacto = (pdf.total_impreso * pct / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            observado, esperado = pdf.total_impreso, pdf.total_impreso + impacto
            cifra = (
                f"; el TOTAL PRESUPUESTO ({_fmt(pdf.total_impreso)}) no la incluye. Lectura "
                f"mínima: {_fmt(pct)} % del total impreso = {_fmt(impacto)} (si el % es sobre "
                f"el total con mano de obra, es más)"
            )
        hallazgos.append(
            _hallazgo(
                _SUB_NOTA,
                Severidad.ERROR,
                f"una nota declara la mano de obra como el {_fmt(pct)} % del presupuesto total "
                f"y ningún renglón la incluye: la mano de obra declarada no está en el total"
                f"{cifra}",
                [f"PDF:{pdf.nombre}:notas", _origen_total(pdf, pdf.presupuesto)],
                impacto=impacto,
                observado=observado,
                esperado=esperado,
            )
        )
    hay_miscelaneos = any("micelaneo" in d or "miscelaneo" in d for d in descripciones)
    if pdf.presupuesto and not hay_miscelaneos:
        for nota in notas:
            if "micelaneo" in nota or "miscelaneo" in nota:
                hallazgos.append(
                    _hallazgo(
                        _SUB_NOTA,
                        Severidad.ADVERTENCIA,
                        "una nota habla de los misceláneos y el presupuesto no tiene renglón de "
                        "misceláneos (¿nota copiada de otro presupuesto?)",
                        [f"PDF:{pdf.nombre}:notas"],
                    )
                )
                break
    return hallazgos


def _regla_sumas(pdf: PdfSimple) -> list[Hallazgo]:
    """La suma de los renglones debe dar el total impreso (y la de cantidades, el de cómputos)."""
    hallazgos: list[Hallazgo] = []
    if pdf.presupuesto:
        origen = [_origen_total(pdf, pdf.presupuesto)]
        if pdf.total_impreso is None:
            hallazgos.append(
                _hallazgo(
                    _SUB_SUMA,
                    Severidad.ADVERTENCIA,
                    "no se encontró la línea «TOTAL PRESUPUESTO»: la suma no se puede cotejar",
                    origen,
                )
            )
        else:
            suma = sum((r.total for r in pdf.presupuesto if r.total is not None), Decimal(0))
            diferencia = pdf.total_impreso - suma
            if abs(diferencia) > TOLERANCIA:
                hallazgos.append(
                    _hallazgo(
                        _SUB_SUMA,
                        Severidad.ERROR,
                        f"los renglones del presupuesto suman {_fmt(suma)} y el TOTAL "
                        f"PRESUPUESTO impreso es {_fmt(pdf.total_impreso)} "
                        f"({_fmt(diferencia, signo=True)})",
                        origen,
                        impacto=diferencia,
                        observado=pdf.total_impreso,
                        esperado=suma,
                    )
                )
    if pdf.computos and pdf.total_computos is not None:
        suma = sum((r.cantidad for r in pdf.computos if r.cantidad is not None), Decimal(0))
        diferencia = pdf.total_computos - suma
        if abs(diferencia) > TOLERANCIA:
            hallazgos.append(
                _hallazgo(
                    _SUB_SUMA,
                    Severidad.ERROR,
                    f"las cantidades de los cómputos suman {_fmt(suma)} y el «Total computos "
                    f"métricos» impreso es {_fmt(pdf.total_computos)}",
                    [_origen_total(pdf, pdf.computos)],
                    observado=pdf.total_computos,
                    esperado=suma,
                )
            )
    return hallazgos


def reglas_pdf_simple(pdf: PdfSimple) -> list[Hallazgo]:
    """Regla L10 (documento sin modelo): todo lo que el PDF dice de sí mismo y no cuadra.

    Orden fijo (determinista): unidades mezcladas en el total de cómputos, filas (incoherencia
    de unidad y aritmética), cómputos contra presupuesto, notas, sumas contra totales impresos.
    """
    return [
        *_regla_unidades(pdf),
        *_regla_filas(pdf),
        *_regla_computos(pdf),
        *_regla_notas(pdf),
        *_regla_sumas(pdf),
    ]


# --- L11: totales impresos del PDF entregado contra el libro --------------------------------------


_RE_SUBTOTAL = re.compile(
    r"total costo de la obra \(sub-? ?total sin iva\)|costo de la obra \(sin iva\)"
)
_RE_IVA = re.compile(r"^iva\b")
_RE_TOTAL = re.compile(r"total presupuesto \(usd\)")
_RE_OPCION = re.compile(r"^opcion\b")


def _monto_tras(texto: str, desde: int) -> Decimal | None:
    """El primer monto después del rótulo, saltando porcentajes (`IVA 16% $3,889.91`,
    `… SIN IVA) $24,311.92 100.0%`)."""
    for m in _RE_MONTO.finditer(texto, desde):
        token = m.group(0).strip()
        if token.endswith("%"):
            continue
        valor = _numero(token)
        if valor is not None:
            return valor
    return None


@dataclass(slots=True)
class _Bloque:
    pagina: int
    opcion: str
    subtotal: Decimal | None = None
    iva: Decimal | None = None
    total: Decimal | None = None


def leer_totales_impresos(datos: bytes, nombre: str) -> TotalesImpresos:
    """Lee el bloque de totales de un PDF impreso desde el libro.

    Busca, línea por línea, "TOTAL COSTO DE LA OBRA (SUB-TOTAL SIN IVA)" o "Costo de la obra (sin
    IVA)", "IVA …" y "TOTAL PRESUPUESTO (USD)". Un rótulo de subtotal abre un bloque; el IVA y el
    total se agregan al bloque abierto. La portada repite el bloque del resumen: bloques iguales
    cuentan como uno. Se devuelve el ÚLTIMO bloque (el definitivo cuando hay varias opciones).
    """
    bloques: list[_Bloque] = []
    opcion = ""
    with _abrir(datos, nombre) as doc:
        paginas = len(doc.pages)
        for num, page in enumerate(doc.pages, start=1):
            lineas = [_limpiar(t) for t in (page.extract_text() or "").splitlines()]
            for k, linea in enumerate(lineas):
                normal = _normalizar(linea)
                if _RE_OPCION.match(normal):
                    opcion = linea
                    continue
                campo, encontrado = None, None
                for nombre_campo, patron in (
                    ("subtotal", _RE_SUBTOTAL),
                    ("total", _RE_TOTAL),
                    ("iva", _RE_IVA),
                ):
                    if (encontrado := patron.search(normal)) is not None:
                        campo = nombre_campo
                        break
                if campo is None or encontrado is None:
                    continue
                # `_normalizar` conserva la longitud salvo por acentos; se busca el monto desde el
                # final del rótulo en el texto normalizado, que tiene las mismas cifras.
                monto = _monto_tras(normal, encontrado.end())
                if monto is None and k + 1 < len(lineas):
                    monto = _monto_tras(_normalizar(lineas[k + 1]), 0)
                if monto is None:
                    continue
                if campo == "subtotal" or not bloques or getattr(bloques[-1], campo) is not None:
                    bloques.append(_Bloque(pagina=num, opcion=opcion))
                setattr(bloques[-1], campo, monto)
    if not bloques:
        return TotalesImpresos(nombre, None, None, None, paginas, nota="sin bloque de totales")
    distintos: dict[tuple[Decimal | None, ...], _Bloque] = {}
    for b in bloques:
        distintos.setdefault((b.subtotal, b.iva, b.total), b)
    elegido = bloques[-1]
    nota = ""
    if len(distintos) > 1:
        rotulos = ", ".join(
            f"{d.opcion or 'sin rótulo'} (p. {d.pagina}: sin IVA "
            f"{_fmt(d.subtotal) if d.subtotal is not None else '—'})"
            for d in distintos.values()
        )
        nota = (
            f"el PDF trae {len(distintos)} bloques de totales distintos: {rotulos}; se toma el "
            f"último (p. {elegido.pagina})"
        )
    return TotalesImpresos(
        nombre=nombre,
        subtotal=elegido.subtotal,
        iva=elegido.iva,
        total=elegido.total,
        paginas=paginas,
        pagina=elegido.pagina,
        bloques=len(distintos),
        opcion=elegido.opcion,
        nota=nota,
    )


def _origen_libro(libro: LibroLeido, clave_total: str) -> str:
    """La celda del libro que guarda el total, por su nombre definido; si el libro no lo define,
    `<libro>:<nombre>`."""
    referencia = libro.nombres.get(clave_total, "")
    limpia = referencia.lstrip("=").replace("$", "").replace("'", "")
    return limpia or f"{libro.nombre}:{clave_total}"


def cotejar_con_libro(totales: TotalesImpresos, libro: LibroLeido) -> list[Hallazgo]:
    """Regla L11: el subtotal, el IVA y el total impresos en el PDF entregado deben ser los del
    libro (`SUBSINIVA`, `IVATOT`, `TOTALGEN`). Si no, el libro no es la versión entregada.

    Diferencia > 0,005: ERROR, con el valor del PDF como observado, el del libro como esperado e
    impacto = PDF − libro. Si un lado no tiene la cifra, ADVERTENCIA (no se pudo cotejar). Si todo
    coincide, lista vacía.
    """
    pagina = f":p{totales.pagina}" if totales.pagina else ""
    origen_pdf = f"PDF:{totales.nombre}{pagina}"
    contexto = f" (bloque «{totales.opcion}»)" if totales.bloques > 1 and totales.opcion else ""
    hallazgos: list[Hallazgo] = []
    for clave_total, etiqueta, valor_pdf in (
        ("SUBSINIVA", "subtotal sin IVA", totales.subtotal),
        ("IVATOT", "IVA", totales.iva),
        ("TOTALGEN", "total con IVA", totales.total),
    ):
        valor_libro = libro.totales.get(clave_total)
        origen = (origen_pdf, _origen_libro(libro, clave_total))
        if valor_pdf is None or valor_libro is None:
            falta = "el PDF" if valor_pdf is None else "el libro"
            hallazgos.append(
                Hallazgo(
                    regla=_REGLA_COTEJO,
                    severidad=Severidad.ADVERTENCIA,
                    descripcion=f"{etiqueta}: {falta} no trae la cifra; no se pudo cotejar el "
                    f"PDF entregado con el libro",
                    origen_ids=origen,
                    valor_observado=valor_pdf,
                    valor_esperado=valor_libro,
                )
            )
            continue
        diferencia = valor_pdf - valor_libro
        if abs(diferencia) <= TOLERANCIA:
            continue
        hallazgos.append(
            Hallazgo(
                regla=_REGLA_COTEJO,
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{etiqueta}: el PDF entregado imprime {_fmt(valor_pdf)}{contexto} y el "
                    f"libro da {_fmt(valor_libro)} ({_fmt(diferencia, signo=True)}); el libro no "
                    f"es la versión entregada"
                ),
                impacto=diferencia,
                origen_ids=origen,
                valor_observado=valor_pdf,
                valor_esperado=valor_libro,
            )
        )
    return hallazgos
