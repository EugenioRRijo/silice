"""Lo que la pantalla «Libro de la empresa» muestra, sin Streamlit (spec 1.5 §1 y §5).

`ui.paginas.libros` pinta; este módulo arma las filas de las tablas (hallazgos, alertas,
trazabilidad, totales) y la **vista calcada** de una hoja del libro recibido: una tabla HTML con los
rellenos, la fuente (negrita, cursiva, color) y las celdas combinadas del original, leídos con
openpyxl, en la que se resaltan las celdas que cita algún hallazgo (`origen_ids` = `HOJA!CELDA`).

Todo el libro es texto ajeno (spec S3, texto ajeno): cada texto que entra al HTML pasa por
`html.escape`, y los colores solo se aceptan como seis dígitos hexadecimales. La vista se limita a
una ventana de `FILAS_VISTA` × `COLUMNAS_VISTA` celdas; lo citado que queda fuera se declara.
Un libro con alguna hoja de más de `TOPE_FILAS` filas o `TOPE_COLUMNAS` columnas usadas se abre
en modo ligero (solo la ventana) y la vista lo avisa.

Sin Streamlit, sin pandas y sin `ui.caso`: se prueba como cualquier función.
"""

from __future__ import annotations

import colorsys
import html
import io
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from core.contracts.verificacion import Hallazgo
from core.verification.texto import formatear_decimal
from ui.subidas import nombre_seguro

__all__ = [
    "COLUMNAS_HALLAZGOS",
    "COLUMNAS_VISTA",
    "FILAS_VISTA",
    "ORDEN_SEVERIDAD",
    "SIN_HOJA",
    "TOPE_AREA_COMBINADA",
    "TOPE_COLUMNAS",
    "TOPE_FILAS",
    "VistaHoja",
    "abrir_libro",
    "filas_alertas",
    "filas_hallazgos",
    "filas_totales",
    "filas_traza",
    "filtrar_hallazgos",
    "hay_tasas",
    "hoja_de",
    "hojas_del_libro",
    "marcas_por_hoja",
    "nombre_devuelto",
    "opciones_de_filtro",
    "vista_calcada",
]

FILAS_VISTA = 80
COLUMNAS_VISTA = 26
MAX_TEXTO_CELDA = 200
MAX_CELDAS_RANGO = 500  # un origen `A1:Z999` no se expande sin cota
TOPE_FILAS = 20_000  # una hoja más grande se abre en modo ligero (solo la ventana)
TOPE_COLUMNAS = 200
TOPE_AREA_COMBINADA = TOPE_FILAS * TOPE_COLUMNAS  # celdas cubiertas por combinadas, sumadas
_BLOQUE_XML = 1 << 20
_SOLAPE_XML = 512  # una etiqueta <mergeCell> partida entre dos bloques se lee en el siguiente
_RE_COMBINADA = re.compile(rb'<(?:[A-Za-z_][\w.-]*:)?mergeCell\b[^>]{0,200}?\bref="([^"]{1,40})"')
SIN_HOJA = "(sin celda)"
NO_CONTRASTABLE = "no contrastable"
SUFIJO_DEVUELTO = " - devuelto por Silice.xlsx"
ORDEN_SEVERIDAD = ("CRITICO", "ERROR", "ADVERTENCIA", "INFO")
COLUMNAS_HALLAZGOS = ("Código", "Severidad", "Descripción", "Celda", "Impacto", "Acción")
CLAVES_TOTALES = (
    ("SUBSINIVA", "Subtotal sin IVA"),
    ("IVATOT", "IVA"),
    ("TOTALGEN", "Total general"),
)
CAMPOS_PDF = {"SUBSINIVA": "subtotal", "IVATOT": "iva", "TOTALGEN": "total"}

COLOR_MARCA = "#C62828"
FONDO_MARCA = "#FDECEA"
_REF = re.compile(r"^\$?([A-Za-z]{1,3})\$?(\d{1,7})$")
_HEX = re.compile(r"^[0-9A-Fa-f]{6}$")

# Tema de Office por defecto, en el orden de índice de Excel (0 = lt1, 1 = dk1, 2 = lt2, 3 = dk2,
# 4-9 = accent1-6, 10 = hlink, 11 = folHlink). Se usa si el libro no trae su propio tema.
_TEMA_OFFICE = (
    "FFFFFF", "000000", "E7E6E6", "44546A", "4472C4", "ED7D31",
    "A5A5A5", "FFC000", "5B9BD5", "70AD47", "0563C1", "954F72",
)  # fmt: skip
_ORDEN_XML_TEMA = (
    "lt1", "dk1", "lt2", "dk2", "accent1", "accent2",
    "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink",
)  # fmt: skip
_NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


# --- celdas citadas ------------------------------------------------------------------------------


def _letras_a_numero(letras: str) -> int:
    """`AB` -> 28, con openpyxl (perezoso: este módulo se importa sin cargarlo)."""
    from openpyxl.utils.cell import column_index_from_string

    return column_index_from_string(letras)


def _numero_a_letras(n: int) -> str:
    """28 -> `AB`, con openpyxl (perezoso: este módulo se importa sin cargarlo)."""
    from openpyxl.utils.cell import get_column_letter

    return get_column_letter(n)


def _separar(origen: str) -> tuple[str, str] | None:
    """`'APU 1'!$G$48` -> ('APU 1', 'G48:G48'); un rango conserva sus dos extremos. `None` si no
    es una celda (un hallazgo del núcleo cita partidas, no celdas)."""
    if "!" not in origen:
        return None
    hoja, ref = origen.rsplit("!", 1)
    hoja = hoja.strip()
    if len(hoja) >= 2 and hoja[0] == hoja[-1] == "'":
        hoja = hoja[1:-1].replace("''", "'")
    extremos = ref.replace("$", "").strip().split(":")
    if not hoja or len(extremos) > 2 or not all(_REF.match(e) for e in extremos):
        return None
    return hoja, ":".join(extremos).upper()


def _expandir(rango: str) -> list[str]:
    extremos = rango.split(":")
    if len(extremos) == 1:
        return extremos
    (c1, f1), (c2, f2) = (_REF.match(e).groups() for e in extremos)  # type: ignore[union-attr]
    col1, col2 = sorted((_letras_a_numero(c1), _letras_a_numero(c2)))
    fil1, fil2 = sorted((int(f1), int(f2)))
    celdas = []
    for fila in range(fil1, fil2 + 1):
        for col in range(col1, col2 + 1):
            celdas.append(f"{_numero_a_letras(col)}{fila}")
            if len(celdas) >= MAX_CELDAS_RANGO:
                return celdas
    return celdas


def marcas_por_hoja(hallazgos: Iterable[Hallazgo]) -> dict[str, dict[str, tuple[str, ...]]]:
    """Por hoja, cada celda citada y los códigos de regla que la citan (sin repetir, en orden)."""
    marcas: dict[str, dict[str, list[str]]] = {}
    for h in hallazgos:
        for origen in h.origen_ids:
            separado = _separar(str(origen))
            if separado is None:
                continue
            hoja, rango = separado
            for ref in _expandir(rango):
                codigos = marcas.setdefault(hoja, {}).setdefault(ref, [])
                if h.regla not in codigos:
                    codigos.append(h.regla)
    return {
        hoja: {ref: tuple(codigos) for ref, codigos in celdas.items()}
        for hoja, celdas in marcas.items()
    }


def hoja_de(celda: str) -> str:
    """La hoja de una celda `HOJA!REF` de la tabla de hallazgos; `SIN_HOJA` si no la nombra."""
    separado = _separar(celda) if celda else None
    if separado is not None:
        return separado[0]
    if celda and "!" in celda:
        return celda.rsplit("!", 1)[0].strip().strip("'") or SIN_HOJA
    return SIN_HOJA


# --- tablas ---------------------------------------------------------------------------------------


def _monto(valor: Decimal | None, decimales: int = 2) -> str:
    if valor is None:
        return ""
    texto = formatear_decimal(valor, decimales)
    return texto[1:] if texto.startswith("-") and not texto.strip("-0.") else texto  # sin «-0.00»


def filas_hallazgos(filas: Sequence[Any]) -> list[dict[str, str]]:
    """Las filas de la tabla de hallazgos (`FilaHallazgo`), con los nombres de columna de la
    pantalla. El texto ajeno va en celdas de la tabla, nunca en Markdown (RV-14)."""
    return [
        dict(
            zip(
                COLUMNAS_HALLAZGOS,
                (f.codigo, f.severidad, f.descripcion, f.celda, _monto(f.impacto), f.accion),
                strict=True,
            )
        )
        for f in filas
    ]


def opciones_de_filtro(filas: Sequence[Any]) -> tuple[list[str], list[str], list[str]]:
    """Severidades (de la más grave a la más leve), reglas y hojas presentes, sin repetir."""
    severidades = {f.severidad for f in filas}
    ordenadas = [s for s in ORDEN_SEVERIDAD if s in severidades]
    ordenadas += sorted(severidades - set(ORDEN_SEVERIDAD))
    reglas = sorted({f.codigo for f in filas})
    hojas = sorted({hoja_de(f.celda) for f in filas})
    return ordenadas, reglas, hojas


def filtrar_hallazgos(
    filas: Sequence[Any],
    severidades: Iterable[str] = (),
    reglas: Iterable[str] = (),
    hojas: Iterable[str] = (),
) -> list[Any]:
    """Las filas que pasan los tres filtros; un filtro vacío deja pasar todo."""
    sev, reg, hoj = set(severidades), set(reglas), set(hojas)
    return [
        f
        for f in filas
        if (not sev or f.severidad in sev)
        and (not reg or f.codigo in reg)
        and (not hoj or hoja_de(f.celda) in hoj)
    ]


def hay_tasas(alertas: Sequence[Any]) -> bool:
    """True si alguna alerta trae tasa del BCV (si ninguna, la instalación no las tiene)."""
    return any(a.tasa is not None for a in alertas)


def filas_alertas(alertas: Sequence[Any]) -> list[dict[str, str]]:
    """Las filas de ALERTAS USD-Bs. Sin tasa, la columna dice «no contrastable» (spec 1.5, F-D8)."""
    return [
        {
            "Código": a.codigo,
            "Descripción": a.descripcion,
            "Tipo": a.tipo,
            "Moneda": a.moneda,
            "Precio": _monto(a.precio),
            "Fecha": a.fecha,
            "Fuente": a.fuente,
            "Tasa BCV": NO_CONTRASTABLE if a.tasa is None else formatear_decimal(a.tasa, 4),
            "Precio en Bs": NO_CONTRASTABLE if a.precio_bs is None else _monto(a.precio_bs),
            "Variación": _porcentaje(a.variacion),
            "Mensaje": a.mensaje,
        }
        for a in alertas
    ]


def _porcentaje(fraccion: Decimal | None) -> str:
    """Una fracción (0,05) como porcentaje con signo y dos decimales (+5.00 %)."""
    if fraccion is None:
        return ""
    texto = formatear_decimal(fraccion * 100, 2)
    return f"{'' if texto.startswith('-') else '+'}{texto} %"


def filas_traza(traza: Sequence[Any]) -> list[dict[str, str]]:
    """Las filas de TRAZABILIDAD: un dato, su valor y de dónde salió."""
    return [{"Dato": t.dato, "Valor": t.valor, "Origen": t.origen, "Nota": t.nota} for t in traza]


def _decimal(valor: object) -> Decimal | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None


def filas_totales(
    del_libro: Mapping[str, Any], de_silice: Mapping[str, Any], pdf: object | None = None
) -> list[dict[str, str]]:
    """Subtotal, IVA y total: los del libro, los de Silice y la diferencia (Silice − libro). Con
    PDF entregado, una columna más con lo impreso. Lo que falta se dice «no disponible»."""
    filas = []
    for clave, rotulo in CLAVES_TOTALES:
        libro = _decimal(del_libro.get(clave))
        silice = _decimal(de_silice.get(clave))
        fila = {
            "Concepto": rotulo,
            "Libro entregado": _monto(libro) or "no disponible",
            "Según Silice": _monto(silice) or "no disponible",
            "Diferencia": (
                _monto(silice - libro) if libro is not None and silice is not None else ""
            ),
        }
        if pdf is not None:
            impreso = _decimal(getattr(pdf, CAMPOS_PDF[clave], None))
            fila["PDF entregado"] = _monto(impreso) or "no disponible"
        filas.append(fila)
    return filas


def nombre_devuelto(nombre: str) -> str:
    """`<nombre original sin extensión> - devuelto por Silice.xlsx`, con el nombre ya limpio
    (A-1: un solo componente, válido en Windows)."""
    try:
        limpio = nombre_seguro(nombre)
    except ValueError:
        limpio = "libro"
    base = limpio.rsplit(".", 1)[0] if "." in limpio else limpio
    return (base.strip(" .") or "libro") + SUFIJO_DEVUELTO


# --- la vista calcada -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VistaHoja:
    """La hoja como HTML y lo que la ventana deja fuera.

    `fuera` son las celdas citadas que no se ven (fuera de la ventana u ocultas), con sus códigos;
    `filas` y `columnas` son el tamaño usado de la hoja en el original; `desde` y `hasta`, las filas
    que la ventana muestra. `aviso` no está vacío cuando el libro se abrió en modo ligero (pasa
    del tope `TOPE_FILAS` × `TOPE_COLUMNAS`): la vista es solo la ventana, sin combinadas ni
    ocultas.
    """

    html: str
    fuera: tuple[tuple[str, tuple[str, ...]], ...]
    filas: int
    columnas: int
    desde: int = 1
    hasta: int = 1
    aviso: str = ""


def _medida(hoja) -> tuple[int, int]:
    """Filas y columnas usadas de una hoja. En modo de solo lectura se toman de la etiqueta
    `<dimension>` del archivo y, si falta, se cuentan leyendo la hoja por partes (sin cargarla)."""
    if getattr(hoja, "max_row", None) is None or getattr(hoja, "max_column", None) is None:
        try:
            hoja.calculate_dimension(force=True)
        except Exception:  # noqa: BLE001 - una hoja vacía sin <dimension> no tiene tamaño
            return 1, 1
    return hoja.max_row or 1, hoja.max_column or 1


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _excede(filas: int, columnas: int) -> bool:
    return filas > TOPE_FILAS or columnas > TOPE_COLUMNAS


def _limites_ref(ref: str) -> tuple[int, int, int, int] | None:
    """`B3:D9` -> (3, 2, 9, 4): fila y columna mínimas y máximas. `None` si no es una referencia."""
    extremos = ref.replace("$", "").strip().split(":")
    if len(extremos) > 2:
        return None
    partes = [_REF.match(e) for e in extremos]
    if not all(partes):
        return None
    filas = [int(m.group(2)) for m in partes]  # type: ignore[union-attr]
    cols = [_letras_a_numero(m.group(1)) for m in partes]  # type: ignore[union-attr]
    return min(filas), min(cols), max(filas), max(cols)


def _combinadas_excesivas(ligero) -> bool:
    """True si alguna hoja declara celdas combinadas más allá del tope o que en total cubren más
    de `TOPE_AREA_COMBINADA` celdas. Se mira leyendo el XML de la hoja por bloques, sin cargarla:
    openpyxl, al abrir el libro entero, recorre CADA celda de cada rango combinado, y un
    `C3:XFD1048576` lo dejaría colgado."""
    archivo = getattr(ligero, "_archive", None)
    if archivo is None:
        return False
    for hoja in ligero.worksheets:
        ruta = getattr(hoja, "_worksheet_path", None)
        if not ruta:
            continue
        area = 0
        resto = b""
        with archivo.open(ruta) as fuente:
            while bloque := fuente.read(_BLOQUE_XML):
                datos = resto + bloque
                ultimo = 0
                for m in _RE_COMBINADA.finditer(datos):
                    ultimo = m.end()
                    limites = _limites_ref(m.group(1).decode("ascii", "replace"))
                    if limites is None:
                        continue
                    f0, c0, f1, c1 = limites
                    if _excede(f1, c1):
                        return True
                    area += (f1 - f0 + 1) * (c1 - c0 + 1)
                    if area > TOPE_AREA_COMBINADA:
                        return True
                resto = datos[max(ultimo, len(datos) - _SOLAPE_XML) :]
    return False


def abrir_libro(origen: bytes):
    """El libro recibido abierto con openpyxl (valores guardados, estilos y combinadas), para
    dibujar varias hojas sin volver a leerlo: leerlo cuesta segundos y dibujar una hoja, no.

    Con tope: primero se abre en modo de solo lectura (no carga las celdas) y se mide cada hoja. Si
    alguna pasa de `TOPE_FILAS` filas o `TOPE_COLUMNAS` columnas usadas, o declara celdas
    combinadas más allá de ese tope o que en total pasan de `TOPE_AREA_COMBINADA` celdas, el libro
    se queda en ese modo ligero y `vista_calcada` lee solo la ventana (sin combinadas, anchos ni
    ocultas) y lo avisa; si no, se abre entero. Límite: el tamaño de las celdas sale de la etiqueta
    `<dimension>` que declara el archivo; uno que la falsee se abre entero, acotado igual por la
    guardia (F-D10).
    """
    from openpyxl import load_workbook  # perezoso: la página se importa sin cargar openpyxl

    ligero = load_workbook(io.BytesIO(origen), read_only=True, data_only=True)
    try:
        grande = any(_excede(*_medida(h)) for h in ligero.worksheets)
        grande = grande or _combinadas_excesivas(ligero)
    except Exception:
        ligero.close()
        raise
    if grande:
        return ligero
    ligero.close()
    return load_workbook(io.BytesIO(origen), data_only=True)


def hojas_del_libro(origen: bytes) -> tuple[str, ...]:
    """Los nombres de hoja del libro, en su orden."""
    from openpyxl import load_workbook

    libro = load_workbook(io.BytesIO(origen), read_only=True)
    try:
        return tuple(libro.sheetnames)
    finally:
        libro.close()


def _tema(libro) -> tuple[str, ...]:
    """Los doce colores del tema del libro (orden de índice de Excel); el de Office si no hay."""
    crudo = getattr(libro, "loaded_theme", None)
    if not crudo:
        return _TEMA_OFFICE
    try:
        from defusedxml.ElementTree import fromstring

        raiz = fromstring(crudo)
        esquema = raiz.find(f".//{_NS_A}clrScheme")
        if esquema is None:
            return _TEMA_OFFICE
        colores = []
        for nombre, defecto in zip(_ORDEN_XML_TEMA, _TEMA_OFFICE, strict=True):
            nodo = esquema.find(f"{_NS_A}{nombre}")
            valor = None
            if nodo is not None:
                srgb = nodo.find(f"{_NS_A}srgbClr")
                sys_ = nodo.find(f"{_NS_A}sysClr")
                if srgb is not None:
                    valor = srgb.get("val")
                elif sys_ is not None:
                    valor = sys_.get("lastClr")
            colores.append(valor if valor and _HEX.match(valor) else defecto)
        return tuple(colores)
    except Exception:  # noqa: BLE001 - un tema ilegible no impide ver la hoja
        return _TEMA_OFFICE


def _matiz(hexa: str, tinte: float) -> str:
    """Aplica el `tint` de Excel (luminosidad en HLS) a un color."""
    if not tinte:
        return hexa
    r, g, b = (int(hexa[i : i + 2], 16) / 255 for i in (0, 2, 4))
    h, l_, s = colorsys.rgb_to_hls(r, g, b)
    l_ = l_ * (1 + tinte) if tinte < 0 else l_ * (1 - tinte) + tinte
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, l_)), s)
    return "".join(f"{round(c * 255):02X}" for c in (r, g, b))


def _color(color, tema: Sequence[str]) -> str | None:
    """Un color de openpyxl como `#RRGGBB`, o `None` si es automático o no se puede resolver."""
    if color is None:
        return None
    try:
        tipo = color.type
        if tipo == "rgb":
            hexa = str(color.rgb or "")[-6:]  # ARGB: el alfa se ignora, como hace Excel
            if not _HEX.match(hexa):
                return None
        elif tipo == "theme":
            indice = int(color.theme)
            if not 0 <= indice < len(tema):
                return None
            hexa = tema[indice]
        elif tipo == "indexed":
            from openpyxl.styles.colors import COLOR_INDEX

            indice = int(color.indexed)
            if not 0 <= indice < len(COLOR_INDEX):
                return None  # 64 y 65: colores del sistema (automático)
            hexa = COLOR_INDEX[indice][-6:]
        else:
            return None
        hexa = _matiz(hexa, float(color.tint or 0))
    except (AttributeError, TypeError, ValueError):
        return None
    return f"#{hexa.upper()}" if _HEX.match(hexa) else None


def _decimales(formato: str) -> int | None:
    seccion = formato.split(";", 1)[0]
    if "." not in seccion:
        return 0 if "0" in seccion else None
    parte = seccion.split(".", 1)[1]
    return len(re.match(r"[0#]*", parte).group(0))  # type: ignore[union-attr]


def _texto_celda(valor: object, formato: str) -> str:
    """El valor guardado como se lee en la hoja (aproximado: decimales y % del formato)."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "VERDADERO" if valor else "FALSO"
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y") if valor.time() == time(0) else f"{valor:%d/%m/%Y %H:%M}"
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, int | float | Decimal):
        numero = Decimal(str(valor))
        formato = formato or "General"
        decimales = None if formato == "General" else _decimales(formato)
        if "%" in formato:
            return formatear_decimal(numero * 100, decimales if decimales is not None else 0) + "%"
        if decimales is None:
            return formatear_decimal(numero.quantize(Decimal("0.0001")) if numero % 1 else numero)
        return formatear_decimal(numero, decimales)
    texto = str(valor)
    return texto if len(texto) <= MAX_TEXTO_CELDA else texto[: MAX_TEXTO_CELDA - 1] + "…"


def _columnas(hoja, hasta_col: int = COLUMNAS_VISTA) -> dict[int, tuple[float | None, bool]]:
    """Ancho y si está oculta, por número de columna, solo hasta `hasta_col` (la ventana). Una
    dimensión de openpyxl puede cubrir un tramo (`min`..`max`), no solo la columna de su letra; el
    tramo se recorta a la ventana antes de recorrerlo."""
    salida: dict[int, tuple[float | None, bool]] = {}
    for letra, dim in hoja.column_dimensions.items():
        if not letra.isalpha():
            continue
        propia = _letras_a_numero(letra)
        desde, hasta = dim.min or propia, dim.max or propia
        for c in range(max(1, desde), min(hasta, hasta_col) + 1):
            salida[c] = (dim.width or None, bool(dim.hidden))
    return salida


def _ancho(ancho: float | None) -> int:
    return max(24, min(400, round((ancho or 8.43) * 7 + 5)))


ENCABEZADO = "background:#E6E9EE;border:1px solid #BFC5CD;font-weight:normal;color:#333333;"
ENCABEZADO_OCULTO = "background:#F3E2BC;border:1px solid #BFC5CD;font-weight:normal;color:#5C4813;"


def _celdas_de_la_ventana(hoja, desde: int, hasta: int, ultima_col: int) -> dict:
    """Modo ligero: las celdas de la ventana, leídas por partes (`iter_rows` de solo lectura)."""
    celdas: dict[tuple[int, int], Any] = {}
    filas = hoja.iter_rows(min_row=desde, max_row=hasta, min_col=1, max_col=ultima_col)
    for f, fila in enumerate(filas, start=desde):
        for c, celda in enumerate(fila, start=1):
            celdas[(f, c)] = celda
    return celdas


def vista_calcada(
    origen: bytes | Any,
    nombre_hoja: str,
    marcas: Mapping[str, Sequence[str]] | None = None,
    *,
    desde: int = 1,
    filas: int = FILAS_VISTA,
    columnas: int = COLUMNAS_VISTA,
    ocultas: bool = True,
) -> VistaHoja:
    """La hoja `nombre_hoja` del libro como tabla HTML, desde la fila `desde`, con las celdas de
    `marcas` (ref -> códigos) resaltadas en rojo y sus códigos en el `title` de la celda.

    `origen` son los octetos del libro o el libro ya abierto con `abrir_libro` (no se cierra).
    Con `ocultas` se muestran también las filas y columnas que el libro oculta, con el encabezado
    en ámbar: un auditor necesita verlas (un hallazgo puede citar una fila oculta). Sin `ocultas`,
    la vista es la de Excel y lo citado que queda oculto se declara en `fuera`.
    Todo lo que se recorre (combinadas, anchos, celdas) se recorta antes a la ventana: un rango
    combinado `A1:XFD1048576` cuesta lo mismo que uno de dos celdas.
    `KeyError` si el libro no tiene esa hoja.
    """
    marcas = {ref.upper(): tuple(c) for ref, c in (marcas or {}).items()}
    propio = isinstance(origen, bytes | bytearray)
    libro = abrir_libro(bytes(origen)) if propio else origen
    try:
        hoja = libro[nombre_hoja]
        tema = _tema(libro)
        ligero = bool(getattr(libro, "read_only", False))
        if ligero:
            max_fila, max_col = _medida(hoja)
        else:
            max_fila, max_col = hoja.max_row or 1, hoja.max_column or 1
        desde = max(1, min(desde, max_fila))
        hasta = min(max_fila, desde + filas - 1)
        ultima_col = min(max_col, columnas)
        aviso = ""
        if ligero:
            # Solo lectura: sin combinadas, anchos ni ocultas; las celdas, solo las de la ventana.
            dims: dict[int, tuple[float | None, bool]] = {}
            ocultas_col: set[int] = set()
            ocultas_fila: set[int] = set()
            rangos: Iterable[Any] = ()
            celdas = _celdas_de_la_ventana(hoja, desde, hasta, ultima_col)
            aviso = (
                f"El libro tiene alguna hoja de más de {_miles(TOPE_FILAS)} filas o "
                f"{TOPE_COLUMNAS} columnas usadas, o celdas combinadas que pasan de ese tope "
                f"(esta hoja: {_miles(max_fila)} × {_miles(max_col)}). Para no agotar la memoria "
                "se abrió en modo ligero: se muestra solo la ventana, sin celdas combinadas, "
                "anchos de columna ni filas o columnas ocultas."
            )
        else:
            dims = _columnas(hoja, ultima_col)
            ocultas_col = {c for c, (_, oculta) in dims.items() if oculta}
            ocultas_fila = {
                n for n, dim in hoja.row_dimensions.items() if dim.hidden and desde <= n <= hasta
            }
            rangos = hoja.merged_cells.ranges
            celdas = None
        cols = [c for c in range(1, ultima_col + 1) if ocultas or c not in ocultas_col]
        filas_vistas = [f for f in range(desde, hasta + 1) if ocultas or f not in ocultas_fila]

        # Celdas combinadas: la esquina lleva rowspan/colspan (recortados a la ventana) y las
        # demás no se pintan. Cada bloque se RECORTA a la ventana antes de recorrerlo. Una marca en
        # cualquier celda del bloque (aun fuera de la ventana) se muestra en la esquina visible.
        esquina: dict[tuple[int, int], tuple[int, int, int, int]] = {}
        cubiertas: dict[tuple[int, int], tuple[int, int]] = {}
        bloques: list[tuple[int, int, int, int, tuple[int, int]]] = []
        for rango in rangos:
            f0, c0, f1, c1 = rango.min_row, rango.min_col, rango.max_row, rango.max_col
            if f1 < desde or f0 > hasta or c0 > ultima_col:
                continue
            fa, fz = max(f0, desde), min(f1, hasta)
            ca, cz = max(c0, 1), min(c1, ultima_col)
            vis_f = [f for f in filas_vistas if fa <= f <= fz]
            vis_c = [c for c in cols if ca <= c <= cz]
            if not vis_f or not vis_c:
                continue
            ancla = (vis_f[0], vis_c[0])
            esquina[ancla] = (len(vis_f), len(vis_c), f0, c0)
            for f in range(fa, fz + 1):
                for c in range(ca, cz + 1):
                    if (f, c) != ancla:
                        cubiertas[(f, c)] = ancla
            bloques.append((f0, c0, f1, c1, ancla))

        visibles = {(f, c) for f in filas_vistas for c in cols}
        marcas_en: dict[tuple[int, int], list[str]] = {}
        fuera: list[tuple[str, tuple[str, ...]]] = []
        for ref, codigos in marcas.items():
            m = _REF.match(ref)
            if m is None:
                continue
            pos = (int(m.group(2)), _letras_a_numero(m.group(1)))
            destino = cubiertas.get(pos, pos)
            if destino not in visibles:
                destino = next(
                    (b[4] for b in bloques if b[0] <= pos[0] <= b[2] and b[1] <= pos[1] <= b[3]),
                    destino,
                )
            if destino in visibles:
                lista = marcas_en.setdefault(destino, [])
                lista.extend(c for c in codigos if c not in lista)
            else:
                fuera.append((ref, tuple(codigos)))

        partes = [
            '<div style="overflow:auto;max-height:640px;border:1px solid #BFC5CD;'
            'background:#FFFFFF;">',
            '<table style="border-collapse:collapse;table-layout:fixed;font-family:Calibri,'
            'Arial,sans-serif;font-size:12px;color:#000000;background:#FFFFFF;">',
            "<thead><tr>",
            f'<th style="position:sticky;top:0;left:0;z-index:2;{ENCABEZADO}'
            'min-width:36px;width:36px;"></th>',
        ]
        for c in cols:
            ancho = _ancho(dims.get(c, (None, False))[0])
            oculta = c in ocultas_col
            partes.append(
                '<th style="position:sticky;top:0;z-index:1;'
                f"{ENCABEZADO_OCULTO if oculta else ENCABEZADO}"
                f'width:{ancho}px;min-width:{ancho}px;"'
                + (' title="Columna oculta en el libro"' if oculta else "")
                + f">{_numero_a_letras(c)}</th>"
            )
        partes.append("</tr></thead><tbody>")
        for f in filas_vistas:
            oculta = f in ocultas_fila
            partes.append(
                '<tr><th style="position:sticky;left:0;z-index:1;'
                f'{ENCABEZADO_OCULTO if oculta else ENCABEZADO}"'
                + (' title="Fila oculta en el libro"' if oculta else "")
                + f">{f}</th>"
            )
            for c in cols:
                if (f, c) in cubiertas:
                    continue
                combinada = esquina.get((f, c))
                # la esquina visible de un bloque combinado muestra el valor y el estilo del bloque
                fila_o, col_o = (combinada[2], combinada[3]) if combinada else (f, c)
                if celdas is not None:
                    celda = celdas.get((fila_o, col_o), _VACIA)
                else:
                    celda = hoja.cell(row=fila_o, column=col_o)
                partes.append(
                    _celda_html(
                        celda, tema, combinada, marcas_en.get((f, c)), f"{_numero_a_letras(c)}{f}"
                    )
                )
            partes.append("</tr>")
        partes.append("</tbody></table></div>")
        return VistaHoja(
            "".join(partes), tuple(sorted(fuera)), max_fila, max_col, desde, hasta, aviso
        )
    finally:
        if propio:
            libro.close()


class _CeldaVacia:
    """Una celda que la ventana ligera no trae (fila o columna sin datos): sin valor ni estilo."""

    __slots__ = ()
    value = None
    font = None
    fill = None
    alignment = None
    number_format = None


_VACIA = _CeldaVacia()


def _celda_html(celda, tema, combinada, codigos, ref: str) -> str:
    estilos = [
        "border:1px solid #E1E4E8",
        "padding:1px 4px",
        "overflow:hidden",
        "white-space:nowrap",
        "text-overflow:ellipsis",
        "vertical-align:bottom",
    ]
    relleno = celda.fill
    fondo = None
    if relleno is not None and relleno.fill_type == "solid":
        fondo = _color(relleno.fgColor, tema)
    fuente = celda.font
    if fuente is not None:
        if fuente.b:
            estilos.append("font-weight:bold")
        if fuente.i:
            estilos.append("font-style:italic")
        if fuente.u:
            estilos.append("text-decoration:underline")
        color = _color(fuente.color, tema)
        if color:
            estilos.append(f"color:{color}")
    alineacion = celda.alignment
    horizontal = alineacion.horizontal if alineacion is not None else None
    valor = celda.value
    if horizontal in {"center", "centerContinuous"}:
        estilos.append("text-align:center")
    elif horizontal == "right" or (
        horizontal in {None, "general"}
        and isinstance(valor, int | float | Decimal)
        and not isinstance(valor, bool)
    ):
        estilos.append("text-align:right")
    if alineacion is not None and alineacion.wrap_text:
        estilos[3] = "white-space:normal"
    atributos = ""
    if combinada:
        filas, columnas = combinada[0], combinada[1]
        if filas > 1:
            atributos += f' rowspan="{filas}"'
        if columnas > 1:
            atributos += f' colspan="{columnas}"'
    if codigos:
        estilos.append(f"box-shadow:inset 0 0 0 2px {COLOR_MARCA}")
        fondo = FONDO_MARCA  # el resalte manda sobre el relleno original
        etiqueta = f"{ref}: " + ", ".join(codigos)
        atributos += f' title="{html.escape(etiqueta, quote=True)}"'
    if fondo:
        estilos.append(f"background:{fondo}")
    texto = html.escape(_texto_celda(valor, celda.number_format or ""), quote=True)
    return f'<td style="{";".join(estilos)}"{atributos}>{texto}</td>'
