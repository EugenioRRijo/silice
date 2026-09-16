"""Meta del Sprint R1 de redaccion: capitulos I y II de la tesis (12 chequeos).

Spec: `docs/superpowers/specs/2026-09-15-sprint-r1-capitulos-design.md`, seccion 6. Sigue el
patron de `scripts/meta_asistente.py`: cada chequeo es una funcion pura sobre texto, probada en
`tests/unit/test_meta_redaccion.py`; leer archivos es asunto de la orquestacion. Automatiza la
parte verificable de la lista de cotejo del tutor (`docs/tesis/rubrica_tutor.md`); lo que
requiere juicio (T2, T3, T4, T7, T13) queda en las actas de revision.

Un documento ausente da PENDIENTE; un documento presente que no cumple da FALLA.

Uso: `uv run python scripts/meta_redaccion.py [--json]`.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado, Fila, _filas_a_json, render_tabla  # noqa: E402

CARPETA_TESIS = RAIZ / "docs" / "tesis"
RUTA_CAPITULO_1 = CARPETA_TESIS / "capitulos" / "01-el-problema.md"
RUTA_CAPITULO_2 = CARPETA_TESIS / "capitulos" / "02-marco-teorico.md"
RUTA_REFERENCIAS = CARPETA_TESIS / "referencias.md"
RUTA_RUBRICA = CARPETA_TESIS / "rubrica_tutor.md"
RUTA_ACTA_1 = CARPETA_TESIS / "revisiones" / "R1-capitulo-1.md"
RUTA_ACTA_2 = CARPETA_TESIS / "revisiones" / "R1-capitulo-2.md"
RUTA_CLAUDE = RAIZ / "CLAUDE.md"

TITULOS: dict[str, str] = {
    "R1": "Capitulo I con tabla de estado y las cinco secciones del guion",
    "R2": "Objetivos en dos variantes; solo la A contiene OE7",
    "R3": "Capitulo II con antecedentes en tres ambitos, bases y terminos",
    "R4": "Voz impersonal: sin primera persona",
    "R5": "Toda cita autor-anio tiene entrada en referencias.md",
    "R6": "Ninguna referencia pendiente se cita sin marca",
    "R7": "Ningun APU del repositorio se presenta como real",
    "R8": "'Gemelo digital' solo en su delimitacion",
    "R9": "Lista de cotejo con los criterios T1-T14",
    "R10": "Acta del capitulo I: T1-T14 con veredicto, ninguno en 'no cumple'",
    "R11": "Acta del capitulo II: T1-T14 con veredicto, ninguno en 'no cumple'",
    "R12": "CLAUDE.md declara la naturaleza de todos los datos (incluye ARENAZA)",
}

CRITERIOS: tuple[str, ...] = tuple(f"T{n}" for n in range(1, 15))
VEREDICTOS: tuple[str, ...] = ("cumple", "cumple con observaciones", "no cumple")
MARCA_PENDIENTE = "[verificacion pendiente]"  # comparada sobre texto normalizado

SECCIONES_CAPITULO_1: tuple[str, ...] = (
    "planteamiento",
    "formulacion",
    "objetivos",
    "justificacion",
    "alcance y delimitacion",
)
SECCIONES_CAPITULO_2: tuple[str, ...] = (
    "antecedentes",
    "bases teoricas",
    "bases normativas",
    "definicion de terminos",
)
AMBITOS_ANTECEDENTES: tuple[str, ...] = (
    "ambito internacional",
    "ambito latinoamericano",
    "ambito nacional",
)
#: Encabezados bajo los que "gemelo digital" es legitimo (criterio T12).
ENCABEZADOS_GEMELO: tuple[str, ...] = (
    "gemelo",
    "sombra",
    "no comprende",
    "definicion de terminos",
)

_PRONOMBRES_PRIMERA_PERSONA = re.compile(
    r"\b(nosotros|nosotras|nuestros?|nuestras?|hemos)\b", re.IGNORECASE
)
#: Primera persona del plural en cualquier verbo, no en una lista cerrada (una prueba sobre el
#: capitulo real mostro que "empleamos" pasaba). Solo letras sin tilde: "ultimos", "prestamos" o
#: "minimos" llevan tilde en el texto y la vocal acentuada impide el limite de palabra.
_VERBO_PRIMERA_PLURAL = re.compile(r"\b([a-zñ]+(?:amos|emos|imos))\b", re.IGNORECASE)
#: Sustantivos y adjetivos sin tilde con la misma terminacion.
_NO_VERBOS: frozenset[str] = frozenset(
    {"amos", "ramos", "tramos", "gramos", "kilogramos", "reclamos", "remos", "extremos",
     "supremos", "primos", "racimos", "mimos"}
)
_TABLA_ESTADO = re.compile(
    r"^\|\s*capitulo\s*\|\s*estado\s*\|\s*ultima revision\s*\|", re.MULTILINE
)

_ANIO = r"(\d{4}[a-z]?|s\.\s?f\.)"
_NOMBRE = r"[A-ZÁÉÍÓÚÑ][\w'\-]*"
#: Solo espacios y tabuladores entre nombres: con `\s` la secuencia cruzaba saltos de linea y tomaba
#: la ultima palabra del subtitulo anterior ("BIM\n\nMa et al. (2011)").
_ESPACIO = r"[ \t]+"
_CITA_NARRATIVA = re.compile(
    rf"((?:{_NOMBRE}{_ESPACIO})*{_NOMBRE}"
    rf"(?:{_ESPACIO}et al\.|{_ESPACIO}y{_ESPACIO}{_NOMBRE}(?:{_ESPACIO}{_NOMBRE})*)?)"
    rf"{_ESPACIO}\({_ANIO}\)"
)
_PARENTESIS = re.compile(r"\(([^()]+)\)")
_PARTE_PARENTETICA = re.compile(rf"^\s*(.+?),\s*{_ANIO}\s*(?:,.*)?$")
_ENCABEZADO_REFERENCIA = re.compile(rf"^###\s+(.+?)\s*\({_ANIO}\)\s*$")
_ESTADO_REFERENCIA = re.compile(r"\*\*Estado:\*\*\s*(verificada|pendiente)")

_AFIRMACION_REAL = re.compile(
    r"\b(presupuestos?|apus?|obras?|casos?|datos)\b[^.\n]{0,60}?\b(real(?:es)?|ejecutad[ao]s?)\b"
    r"|\breal(?:es)?\s+(?:de\s+)?(?:presupuestos?|apus?|obras?)\b",
    re.IGNORECASE,
)
_MARCADOR_LIMITACION = re.compile(
    r"\b(no|sin|limitaci[oó]n\w*|futur\w*|pendiente\w*|ficticio\w*|did[aá]ctic\w*|ilustrativ\w*)\b",
    re.IGNORECASE,
)
#: Conectores que contienen un marcador pero no niegan la afirmacion.
_CONECTORES_NO_NEGATIVOS = re.compile(r"\b(sin embargo|no obstante|no solo)\b", re.IGNORECASE)


def _normalizar(texto: str) -> str:
    """Minusculas y sin tildes, para comparar encabezados y marcas sin depender de la ortografia."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower()


def _encabezados(texto: str) -> list[tuple[int, str]]:
    return [
        (len(m.group(1)), m.group(2).strip())
        for m in re.finditer(r"^(#{1,6})\s+(.+)$", texto, re.MULTILINE)
    ]


def _faltantes(requeridos: tuple[str, ...], titulos: list[str]) -> list[str]:
    normalizados = [_normalizar(titulo) for titulo in titulos]
    return [r for r in requeridos if not any(r in titulo for titulo in normalizados)]


# --------------------------------------------------------------------------------------
# Estructura de los capitulos
# --------------------------------------------------------------------------------------


def evaluar_capitulo_1(texto: str | None) -> tuple[Estado, str]:
    if texto is None:
        return Estado.PENDIENTE, "falta docs/tesis/capitulos/01-el-problema.md"
    return _evaluar_estructura(
        texto, niveles={2: SECCIONES_CAPITULO_1}, descripcion="las cinco secciones del guion"
    )


def evaluar_capitulo_2(texto: str | None) -> tuple[Estado, str]:
    if texto is None:
        return Estado.PENDIENTE, "falta docs/tesis/capitulos/02-marco-teorico.md"
    return _evaluar_estructura(
        texto,
        niveles={2: SECCIONES_CAPITULO_2, 3: AMBITOS_ANTECEDENTES},
        descripcion="antecedentes en tres ambitos, bases y terminos",
    )


def _evaluar_estructura(
    texto: str, niveles: Mapping[int, tuple[str, ...]], descripcion: str
) -> tuple[Estado, str]:
    problemas = []
    if not _TABLA_ESTADO.search(_normalizar(texto)):
        problemas.append("falta la tabla capitulo / estado / ultima revision")
    encabezados = _encabezados(texto)
    for nivel, requeridos in niveles.items():
        titulos = [titulo for n, titulo in encabezados if n == nivel]
        faltan = _faltantes(requeridos, titulos)
        if faltan:
            problemas.append(f"faltan secciones: {', '.join(faltan)}")
    if problemas:
        return Estado.FALLA, "; ".join(problemas)
    return Estado.OK, f"tabla de estado y {descripcion}"


def _bloque(texto: str, inicio_titulo: str) -> str | None:
    """Contenido bajo el encabezado de nivel 3 cuyo titulo empieza con `inicio_titulo`."""
    lineas = texto.splitlines()
    for indice, linea in enumerate(lineas):
        encabezado = re.match(r"^(#{1,6})\s+(.+)$", linea)
        if encabezado and len(encabezado.group(1)) == 3:
            if _normalizar(encabezado.group(2)).startswith(inicio_titulo):
                cuerpo = []
                for siguiente in lineas[indice + 1 :]:
                    if re.match(r"^#{1,3}\s", siguiente):
                        break
                    cuerpo.append(siguiente)
                return "\n".join(cuerpo)
    return None


def evaluar_objetivos(texto: str | None) -> tuple[Estado, str]:
    """Decision DR-2: variante A con OE7 y variante B sin OE7."""
    if texto is None:
        return Estado.PENDIENTE, "falta docs/tesis/capitulos/01-el-problema.md"
    variante_a = _bloque(texto, "variante a")
    variante_b = _bloque(texto, "variante b")
    problemas = []
    if variante_a is None:
        problemas.append("falta la Variante A")
    elif not re.search(r"\bOE\s?7\b", variante_a):
        problemas.append("la Variante A no contiene OE7")
    if variante_b is None:
        problemas.append("falta la Variante B")
    elif re.search(r"\bOE\s?7\b", variante_b):
        problemas.append("la Variante B no debe contener OE7")
    if problemas:
        return Estado.FALLA, "; ".join(problemas)
    return Estado.OK, "Variante A con OE7 y Variante B sin OE7"


# --------------------------------------------------------------------------------------
# Redaccion
# --------------------------------------------------------------------------------------


def evaluar_primera_persona(textos: Mapping[str, str]) -> tuple[Estado, str]:
    if not textos:
        return Estado.PENDIENTE, "sin capitulos que revisar"
    hallazgos = []
    for nombre, texto in textos.items():
        pronombres = {m.group(1).lower() for m in _PRONOMBRES_PRIMERA_PERSONA.finditer(texto)}
        verbos = {
            m.group(1).lower()
            for m in _VERBO_PRIMERA_PLURAL.finditer(texto)
            if m.group(1).lower() not in _NO_VERBOS
        }
        palabras = sorted(pronombres | verbos)
        if palabras:
            hallazgos.append(f"{nombre}: {', '.join(palabras)}")
    if hallazgos:
        return Estado.FALLA, "primera persona en " + "; ".join(hallazgos)
    return Estado.OK, f"voz impersonal en {len(textos)} capitulo(s)"


# --------------------------------------------------------------------------------------
# Citas y referencias
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Cita:
    texto: str
    autores: str
    anio: str
    fin: int


def _anio_normalizado(anio: str) -> str:
    return anio.replace(" ", "").lower()


def _palabras(autores: str) -> set[str]:
    # Los corchetes separan como los espacios: APA 7 introduce la abreviatura de un autor
    # corporativo en su primera cita ("Comision Venezolana de Normas Industriales [COVENIN]").
    return set(re.split(r"[\s\-\[\]]+", _normalizar(autores)))


def referencias_de(texto: str) -> dict[tuple[str, str], tuple[str, str]]:
    """(primer apellido normalizado, anio) -> (forma de cita, estado)."""
    referencias: dict[tuple[str, str], tuple[str, str]] = {}
    bloques = re.split(r"^(?=###\s)", texto, flags=re.MULTILINE)
    for bloque in bloques:
        encabezado = _ENCABEZADO_REFERENCIA.match(bloque.splitlines()[0] if bloque else "")
        if encabezado is None:
            continue
        autores, anio = encabezado.group(1), _anio_normalizado(encabezado.group(2))
        estado = _ESTADO_REFERENCIA.search(bloque)
        # Mismo corte que `_palabras` para las citas: "IP-3" y "Rozo-Martinez" deben coincidir.
        primer_apellido = re.split(r"[\s\-]+", _normalizar(autores))[0]
        referencias[(primer_apellido, anio)] = (
            f"{autores} ({anio})",
            estado.group(1) if estado else "pendiente",
        )
    return referencias


def citas_de(texto: str) -> list[Cita]:
    """Citas narrativas "Apellido (anio)" y parenteticas "(Apellido, anio; ...)" del texto."""
    citas = [
        Cita(m.group(0), m.group(1), _anio_normalizado(m.group(2)), m.end())
        for m in _CITA_NARRATIVA.finditer(texto)
    ]
    for parentesis in _PARENTESIS.finditer(texto):
        for parte in parentesis.group(1).split(";"):
            coincidencia = _PARTE_PARENTETICA.match(parte)
            if coincidencia:
                citas.append(
                    Cita(
                        parte.strip(),
                        coincidencia.group(1),
                        _anio_normalizado(coincidencia.group(2)),
                        parentesis.end(),
                    )
                )
    return citas


def _referencia_de(
    cita: Cita, referencias: Mapping[tuple[str, str], tuple[str, str]]
) -> tuple[str, str] | None:
    palabras = _palabras(cita.autores)
    for (apellido, anio), datos in referencias.items():
        if anio == cita.anio and apellido in palabras:
            return datos
    return None


def evaluar_citas(textos: Mapping[str, str], texto_referencias: str | None) -> tuple[Estado, str]:
    if texto_referencias is None:
        return Estado.PENDIENTE, "falta docs/tesis/referencias.md"
    if not textos:
        return Estado.PENDIENTE, "sin capitulos que revisar"
    referencias = referencias_de(texto_referencias)
    total, sin_referencia = 0, []
    for nombre, texto in textos.items():
        for cita in citas_de(texto):
            total += 1
            if _referencia_de(cita, referencias) is None:
                sin_referencia.append(f"{cita.autores.strip()} ({cita.anio}) [{nombre}]")
    if sin_referencia:
        return Estado.FALLA, "citas sin referencia: " + "; ".join(sorted(set(sin_referencia)))
    return Estado.OK, f"{total} cita(s), todas con referencia"


def evaluar_pendientes(
    textos: Mapping[str, str], texto_referencias: str | None
) -> tuple[Estado, str]:
    if texto_referencias is None:
        return Estado.PENDIENTE, "falta docs/tesis/referencias.md"
    if not textos:
        return Estado.PENDIENTE, "sin capitulos que revisar"
    referencias = referencias_de(texto_referencias)
    sin_marca = []
    for nombre, texto in textos.items():
        for cita in citas_de(texto):
            datos = _referencia_de(cita, referencias)
            if datos is None or datos[1] != "pendiente":
                continue
            resto_de_linea = texto[cita.fin :].split("\n", 1)[0][:80]
            if MARCA_PENDIENTE not in _normalizar(resto_de_linea):
                sin_marca.append(f"{cita.texto.strip()} [{nombre}]")
    if sin_marca:
        return Estado.FALLA, "referencias pendientes citadas sin marca: " + "; ".join(sin_marca)
    return Estado.OK, "toda referencia pendiente citada lleva su marca"


# --------------------------------------------------------------------------------------
# Honestidad de datos y terminologia
# --------------------------------------------------------------------------------------


def evaluar_datos_reales(textos: Mapping[str, str]) -> tuple[Estado, str]:
    """Decision DR-1: una oracion que habla de datos reales debe negarlo o declararlo limitacion."""
    if not textos:
        return Estado.PENDIENTE, "sin capitulos que revisar"
    afirmaciones = []
    for nombre, texto in textos.items():
        for oracion in re.split(r"(?<=[.!?])\s+|\n+", texto):
            afirmacion = _AFIRMACION_REAL.search(oracion)
            if afirmacion is None:
                continue
            sin_conectores = _CONECTORES_NO_NEGATIVOS.sub("", oracion)
            if not _MARCADOR_LIMITACION.search(sin_conectores):
                afirmaciones.append(f"'{afirmacion.group(0)}' [{nombre}]")
    if afirmaciones:
        return Estado.FALLA, "datos presentados como reales: " + "; ".join(afirmaciones)
    return Estado.OK, "ningun caso del repositorio se presenta como real"


def evaluar_gemelo_digital(textos: Mapping[str, str]) -> tuple[Estado, str]:
    if not textos:
        return Estado.PENDIENTE, "sin capitulos que revisar"
    fuera = []
    for nombre, texto in textos.items():
        titulo_actual = ""
        for linea in texto.splitlines():
            encabezado = re.match(r"^(#{1,6})\s+(.+)$", linea)
            if encabezado:
                titulo_actual = encabezado.group(2).strip() if len(encabezado.group(1)) >= 2 else ""
            if "gemelo digital" not in _normalizar(linea):
                continue
            if not any(clave in _normalizar(titulo_actual) for clave in ENCABEZADOS_GEMELO):
                fuera.append(f"{nombre} ({titulo_actual or 'sin seccion'})")
    if fuera:
        return Estado.FALLA, "'gemelo digital' fuera de su delimitacion: " + "; ".join(fuera)
    return Estado.OK, "'gemelo digital' solo en su delimitacion"


# --------------------------------------------------------------------------------------
# Instrumentos del tutor y fuente unica de datos
# --------------------------------------------------------------------------------------


def evaluar_rubrica(texto: str | None) -> tuple[Estado, str]:
    if texto is None:
        return Estado.PENDIENTE, "falta docs/tesis/rubrica_tutor.md"
    presentes = {f"T{n}" for n in re.findall(r"^\|\s*\*\*T(\d+)\*\*\s*\|", texto, re.MULTILINE)}
    faltan = [criterio for criterio in CRITERIOS if criterio not in presentes]
    if faltan:
        return Estado.FALLA, f"faltan criterios: {', '.join(faltan)}"
    return Estado.OK, "criterios T1-T14 presentes"


def evaluar_acta(texto: str | None) -> tuple[Estado, str]:
    if texto is None:
        return Estado.PENDIENTE, "falta el acta de revision"
    veredictos = {
        f"T{m.group(1)}": _normalizar(m.group(2)).strip()
        for m in re.finditer(r"^\|\s*T(\d+)\s*\|\s*([^|]+?)\s*\|", texto, re.MULTILINE)
    }
    problemas = []
    faltan = [criterio for criterio in CRITERIOS if criterio not in veredictos]
    if faltan:
        problemas.append(f"faltan: {', '.join(faltan)}")
    invalidos = [c for c, v in veredictos.items() if c in CRITERIOS and v not in VEREDICTOS]
    if invalidos:
        problemas.append(f"veredicto invalido: {', '.join(invalidos)}")
    no_cumple = [c for c, v in veredictos.items() if v == "no cumple"]
    if no_cumple:
        problemas.append(f"no cumple: {', '.join(no_cumple)}")
    if problemas:
        return Estado.FALLA, "; ".join(problemas)
    return Estado.OK, "T1-T14 con veredicto; ninguno en 'no cumple'"


def evaluar_naturaleza_datos(texto: str | None) -> tuple[Estado, str]:
    if texto is None:
        return Estado.FALLA, "falta CLAUDE.md"
    normalizado = _normalizar(texto)
    faltan = [
        etiqueta
        for etiqueta, presente in (
            ("parrafo 'Naturaleza de los datos'", "naturaleza de los datos" in normalizado),
            ("mencion de ARENAZA", "arenaza" in normalizado),
            ("declaracion de datos ficticios", "ficticio" in normalizado),
        )
        if not presente
    ]
    if faltan:
        return Estado.FALLA, f"CLAUDE.md no tiene: {', '.join(faltan)}"
    return Estado.OK, "CLAUDE.md declara la naturaleza de todos los datos, ARENAZA incluido"


# --------------------------------------------------------------------------------------
# Orquestacion y CLI
# --------------------------------------------------------------------------------------


def _leer(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.exists() else None


def _evaluar_metas() -> list[Fila]:
    capitulo_1, capitulo_2 = _leer(RUTA_CAPITULO_1), _leer(RUTA_CAPITULO_2)
    capitulos = {
        nombre: texto
        for nombre, texto in (("capitulo I", capitulo_1), ("capitulo II", capitulo_2))
        if texto is not None
    }
    referencias = _leer(RUTA_REFERENCIAS)
    chequeos: dict[str, Callable[[], tuple[Estado, str]]] = {
        "R1": lambda: evaluar_capitulo_1(capitulo_1),
        "R2": lambda: evaluar_objetivos(capitulo_1),
        "R3": lambda: evaluar_capitulo_2(capitulo_2),
        "R4": lambda: evaluar_primera_persona(capitulos),
        "R5": lambda: evaluar_citas(capitulos, referencias),
        "R6": lambda: evaluar_pendientes(capitulos, referencias),
        "R7": lambda: evaluar_datos_reales(capitulos),
        "R8": lambda: evaluar_gemelo_digital(capitulos),
        "R9": lambda: evaluar_rubrica(_leer(RUTA_RUBRICA)),
        "R10": lambda: evaluar_acta(_leer(RUTA_ACTA_1)),
        "R11": lambda: evaluar_acta(_leer(RUTA_ACTA_2)),
        "R12": lambda: evaluar_naturaleza_datos(_leer(RUTA_CLAUDE)),
    }
    return [Fila(codigo, TITULOS[codigo], *chequeo()) for codigo, chequeo in chequeos.items()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="meta_redaccion.py", description="Evalua las 12 metas del Sprint R1 de redaccion."
    )
    parser.add_argument("--json", action="store_true", help="imprime JSON en vez de la tabla")
    args = parser.parse_args(argv)
    filas = _evaluar_metas()
    print(_filas_a_json(filas) if args.json else render_tabla(filas))
    return 0 if all(fila.estado is Estado.OK for fila in filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
