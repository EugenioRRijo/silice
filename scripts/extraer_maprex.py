"""Extrae de los tres listados MaPreX (julio 2026) una referencia de precios estructurada
por dominio: `referencia_civil.csv`, `referencia_telecom.csv`, `referencia_industrial.csv` y
`referencia_sistemas.csv`, todos en `data/precios/maprex_2026-07/` (Sesion M0.2 del
PLAN_MULTIDOMINIO).

PyMuPDF no es dependencia del proyecto (no se agrega a pyproject.toml: los tres PDF son
evidencia de una sola sesion, no un flujo de la aplicacion). Ejecutar con:

    uv run --with pymupdf python scripts/extraer_maprex.py

Que hace este script
--------------------
1. Lee el texto de `materiales.pdf`, `equipos.pdf` y `mano_de_obra.pdf` con PyMuPDF y lo
   parsea a diccionarios `{ref_maprex: datos_de_la_fila}` con expresiones regulares ajustadas
   al layout real de cada listado (columnas intercaladas y encabezados de pagina repetidos,
   ver `data/precios/maprex_2026-07/README.md`).
2. Selecciona, por dominio, una lista curada de referencias MaPreX (`ref_maprex`) elegidas y
   verificadas a mano contra el PDF durante la Sesion M0.2 (Ref, descripcion, unidad y precio
   comparados digito a digito; ver la bitacora de la sesion). El alcance de cada dominio:
   - civil: solo los insumos de `tests/fixtures/apu_linea_base.py` (37 insumos: materiales,
     equipos y roles de mano de obra de los cinco APU de la linea base).
   - telecom: renglones comparables con los presupuestos ARENAZA (`data/telecom/
     plantilla_precios.csv`): UTP, fibra optica, tubo corrugado, conectores RJ45, canalizacion,
     rack, patch panel, etc.
   - industrial: repuestos y servicios aplicables a los activos de
     `data/samples/industrial/activos_planta.csv` (rodamientos, correas, valvulas, aceites,
     filtros, sello mecanico, transformadores, tecnicos por tabulador).
   - sistemas: las 43 filas del tabulador CIV (agrupacion "TAB CIV") del listado de mano de
     obra, escalafon P-1..P-10.
   No incluir una referencia no es un error del script: es la regla de la Sesion M0.2 ("mejor
   omitir que adivinar"). Los insumos sin equivalente claro (marcas y modelos de equipos de
   red/camaras/UPS que MaPreX no lista) se documentan en la bitacora, no se inventan aqui.
3. Vuelve a resolver cada referencia contra el diccionario recien parseado (no contra un valor
   copiado a mano): si el PDF cambiara o la referencia no existiera, el script falla con un
   error explicito en vez de escribir un CSV con datos obsoletos o inventados. Para
   `equipos.pdf` en particular (unico listado con un descarte automatico, ver punto 5) el
   error distingue las dos causas posibles: la Ref nunca aparecio en el PDF, o aparecio pero
   su fila fue descartada por el cruce Total = Precio x Factor (`_resolver_equipo`).
4. Convierte cada precio en bolivares a USD con la tasa declarada en el README de la carpeta
   (633,3644 Bs/USD al 01/07/2026) y escribe los cuatro CSV con la cabecera exacta:
   `tipo,insumo,unidad,precio_bs,bono_bs,factor_depreciacion,precio_usd,fecha_vigencia,
   archivo,ref_maprex,notas`.
5. En `equipos.pdf`, descarta (no usa) toda fila cuyo Total impreso no coincida con
   Precio x Factor (`parsear_equipos`): es la unica verificacion cruzada automatica del
   script. Cada descarte queda registrado con Ref, descripcion y los dos valores que no
   coincidieron, e impreso al final de `main()` (auditoria, no solo un `continue` silencioso).

Convenciones declaradas (para quien lea los CSV)
-------------------------------------------------
- `unidad` de una fila de `equipos.pdf` es "dia": el listado no trae columna de unidad propia
  (Ref, Descripcion, Precio/Alq., Cop/Depr., Total, Proveedor, Fecha) y el motor de costeo usa
  el precio de equipo como tarifa diaria (`core.contracts.apu.LineaEquipo`).
- `unidad` de una fila de `mano_de_obra.pdf` es "dia": el jornal es una tarifa diaria.
- `precio_bs` de una fila de equipo es el "Precio/Alq." (precio base), no el "Total" ya
  multiplicado por el factor: asi coincide con `LineaEquipo.precio` del contrato (cantidad x
  precio x depreciacion), que aplica el factor por separado.
- Un caracter "\\ufffd" en el texto crudo del PDF es un glifo que PyMuPDF no pudo mapear a
  Unicode (fuente propia de MaPreX). Se verifico a mano que, en las descripciones usadas por
  este script, siempre reemplaza una "Ñ"; se restituye por eso, no por conjetura general.
- Una descripcion que termina en "\\" o que abre parentesis sin cerrarlo esta truncada por el
  ancho fijo de columna del reporte MaPreX (no es un error de extraccion): se conserva tal
  cual y se anota en la columna `notas`.
"""

from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover - guia de uso, no logica de negocio
    raise SystemExit(
        "Falta PyMuPDF. Ejecutar con:\n  uv run --with pymupdf python scripts/extraer_maprex.py"
    ) from exc

RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "data" / "precios" / "maprex_2026-07"
RUTA_MATERIALES = CARPETA / "materiales.pdf"
RUTA_EQUIPOS = CARPETA / "equipos.pdf"
RUTA_MANO_OBRA = CARPETA / "mano_de_obra.pdf"

TASA = Decimal("633.3644")
FECHA_MATERIALES_EQUIPOS = "2026-07-09"
FECHA_MANO_OBRA = "2026-07-01"

CABECERA = [
    "tipo",
    "insumo",
    "unidad",
    "precio_bs",
    "bono_bs",
    "factor_depreciacion",
    "precio_usd",
    "fecha_vigencia",
    "archivo",
    "ref_maprex",
    "notas",
]

# --------------------------------------------------------------------------------------
# Lectura y parseo de los tres PDF
# --------------------------------------------------------------------------------------

PATRON_MATERIALES = re.compile(
    r"^([A-Z0-9./-]{2,10})\n(.+)\n(\S{1,15})\n(\d{2}/\d{2}/\d{4})\n([\d.,]+)([^\n]*)$",
    re.MULTILINE,
)
PATRON_EQUIPOS = re.compile(
    r"^([A-Z]{2,4}\d{3,4})\s?(.+)\n([\d.,]+)\n([\d.,]+)\n([\d.,]+)([^\n]*)\n(\d{1,2}/\d{2}/\d{2,4})$",
    re.MULTILINE,
)
# Tabulador CIV (sistemas): agrupacion "e-TAB CIV ...". Solo se necesitan ref/desc/jornal/bono;
# nivel y fecha del renglon no se usan (fecha_vigencia se declara aparte, ver modulo).
PATRON_TAB_CIV = re.compile(
    r"([A-Z]{2,4}\d{3})\s+([^\n]+)\n([\d.,]+)\n([\d.,]+)\s+([^\n]*TAB CIV[^\n]*)"
)
# Tabulador de la construccion (civil/industrial): agrupacion "a-SAL CONST-...".
PATRON_SAL_CONST = re.compile(
    r"^(\d+-[\w.]+)\s+([^\n]+)\n([\d.,]+)\n([\d.,]+)\s+(a-SAL CONST[^\n]*)", re.MULTILINE
)


def _texto_pdf(ruta: Path) -> str:
    with fitz.open(ruta) as doc:
        return "".join(pagina.get_text() for pagina in doc)


def _bs(texto: str) -> Decimal:
    """Convierte un monto en formato venezolano ('6.795.000,00') a Decimal."""
    return Decimal(texto.strip().replace(".", "").replace(",", "."))


def _usd(precio_bs: Decimal) -> Decimal:
    return (precio_bs / TASA).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _fix_enye(desc: str) -> str:
    """El glifo Ñ de la fuente propia de MaPreX no siempre mapea a Unicode y PyMuPDF lo
    exporta como U+FFFD. Verificado a mano: en toda descripcion usada por este script
    representa una Ñ (ALBAÑIL, ALBAÑILERIA, AÑOS)."""
    return desc.replace("�", "Ñ")


def _desc_material_o_equipo(desc: str) -> tuple[str, bool]:
    """Limpia una descripcion de materiales/equipos. Devuelve (descripcion, truncada):
    MaPreX marca con '\\' final la descripcion que no cupo en el ancho de columna."""
    desc = _fix_enye(desc).strip()
    truncada = desc.endswith("\\")
    if truncada:
        desc = desc[:-1].rstrip()
    return desc, truncada


@dataclass(frozen=True, slots=True)
class FilaMaterial:
    descripcion: str
    unidad: str
    precio_bs: Decimal
    truncada: bool


@dataclass(frozen=True, slots=True)
class FilaEquipo:
    descripcion: str
    precio_bs: Decimal
    factor: Decimal
    total: Decimal
    truncada: bool


@dataclass(frozen=True, slots=True)
class FilaManoObra:
    descripcion: str
    jornal: Decimal
    bono: Decimal


def parsear_materiales(texto: str) -> dict[str, FilaMaterial]:
    filas: dict[str, FilaMaterial] = {}
    for ref, desc, unidad, _fecha, precio, _resto in PATRON_MATERIALES.findall(texto):
        desc_limpia, truncada = _desc_material_o_equipo(desc)
        filas[ref] = FilaMaterial(desc_limpia, unidad.strip(), _bs(precio), truncada)
    return filas


def parsear_equipos(texto: str) -> tuple[dict[str, FilaEquipo], dict[str, str]]:
    """Devuelve (filas_validas, descartadas). `descartadas` es un diagnostico por Ref
    (ref -> mensaje) de toda fila que el cruce Total = Precio x Factor rechazo: sirve para
    que `_resolver_equipo` distinga "la Ref no existe en el PDF" de "la Ref existe pero su
    fila fue descartada por el cruce" cuando una seleccion curada falle mas abajo."""
    filas: dict[str, FilaEquipo] = {}
    descartadas: dict[str, str] = {}
    for ref, desc, precio, factor, total, _resto, _fecha in PATRON_EQUIPOS.findall(texto):
        desc_limpia, truncada = _desc_material_o_equipo(desc)
        precio_dec, factor_dec, total_dec = _bs(precio), _bs(factor), _bs(total)
        # Verificacion cruzada declarada en el README: Total = Precio x Factor. Si no
        # coincide (redondeo del propio MaPreX aparte, tolerancia 0.01), el dato es dudoso
        # y no se usa: mejor detenerse aqui que arrastrar una fila mal alineada por el parser.
        calculado = (precio_dec * factor_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_redondeado = total_dec.quantize(Decimal("0.01"))
        if abs(calculado - total_redondeado) > Decimal("0.02"):
            descartadas[ref] = (
                f"{ref} ({desc_limpia}): Total del PDF={total_redondeado} vs "
                f"Precio x Factor calculado={calculado} (precio={precio_dec}, "
                f"factor={factor_dec}) -> fila descartada por el cruce Total=Precio x Factor"
            )
            continue
        filas[ref] = FilaEquipo(desc_limpia, precio_dec, factor_dec, total_dec, truncada)
    return filas, descartadas


def _resolver_equipo(
    ref: str, dic: dict[str, FilaEquipo], descartadas: dict[str, str]
) -> FilaEquipo:
    """Resuelve una Ref de equipos.pdf distinguiendo las dos causas de fallo posibles:
    la Ref nunca aparecio en el PDF, o aparecio pero su fila fue descartada por el cruce
    Total = Precio x Factor (ver `parsear_equipos`). Un `KeyError` sin este contexto no
    deja saber cual de las dos paso."""
    if ref in dic:
        return dic[ref]
    if ref in descartadas:
        raise KeyError(
            f"La referencia '{ref}' SI aparece en equipos.pdf pero fue descartada por el "
            f"cruce de verificacion (no falta en el PDF): {descartadas[ref]}"
        )
    raise KeyError(
        f"La referencia '{ref}' no aparece en equipos.pdf (no se encontro al parsear el "
        "PDF con PATRON_EQUIPOS; revisar si el Ref es correcto o si el layout del PDF cambio)."
    )


# Tres referencias del tabulador CIV cuya descripcion viene truncada sin abrir parentesis
# (no las detecta la heuristica "'(' sin ')'"): verificado a mano contra `mano_de_obra.pdf`
# comparando con renglones hermanos completos del mismo escalafon (Sesion M0.2).
TAB_CIV_TRUNCADAS_SIN_PARENTESIS = {"DIS038", "DIS025", "DIS043"}


def _tab_civ_truncada(ref: str, desc: str) -> bool:
    if "(" in desc and ")" not in desc:
        return True
    return ref in TAB_CIV_TRUNCADAS_SIN_PARENTESIS


def parsear_tabulador_civ(texto: str) -> dict[str, FilaManoObra]:
    filas: dict[str, FilaManoObra] = {}
    for ref, desc, jornal, bono, _agrupacion in PATRON_TAB_CIV.findall(texto):
        filas[ref] = FilaManoObra(_fix_enye(desc.strip()), _bs(jornal), _bs(bono))
    return filas


def parsear_tabulador_construccion(texto: str) -> dict[str, FilaManoObra]:
    filas: dict[str, FilaManoObra] = {}
    for ref, desc, jornal, bono, _agrupacion in PATRON_SAL_CONST.findall(texto):
        filas[ref] = FilaManoObra(_fix_enye(desc.strip()), _bs(jornal), _bs(bono))
    return filas


# --------------------------------------------------------------------------------------
# Construccion de filas del CSV de salida
# --------------------------------------------------------------------------------------


def _nota_truncamiento(truncada: bool) -> str:
    return "descripcion truncada en el PDF (ancho fijo de columna de MaPreX)" if truncada else ""


def _combinar_notas(*partes: str) -> str:
    return "; ".join(p for p in partes if p)


def fila_material(
    ref: str,
    dic: dict[str, FilaMaterial],
    nota: str,
    *,
    archivo: str = "materiales.pdf",
    fecha: str = FECHA_MATERIALES_EQUIPOS,
) -> dict[str, str]:
    dato = dic[ref]
    precio_usd = _usd(dato.precio_bs)
    return {
        "tipo": "material",
        "insumo": dato.descripcion,
        "unidad": dato.unidad,
        "precio_bs": str(dato.precio_bs),
        "bono_bs": "",
        "factor_depreciacion": "",
        "precio_usd": str(precio_usd),
        "fecha_vigencia": fecha,
        "archivo": archivo,
        "ref_maprex": ref,
        "notas": _combinar_notas(nota, _nota_truncamiento(dato.truncada)),
    }


def fila_equipo(
    ref: str, dic: dict[str, FilaEquipo], nota: str, descartadas: dict[str, str]
) -> dict[str, str]:
    dato = _resolver_equipo(ref, dic, descartadas)
    precio_usd = _usd(dato.precio_bs)
    return {
        "tipo": "equipo",
        "insumo": dato.descripcion,
        "unidad": "dia",
        "precio_bs": str(dato.precio_bs),
        "bono_bs": "",
        "factor_depreciacion": str(dato.factor),
        "precio_usd": str(precio_usd),
        "fecha_vigencia": FECHA_MATERIALES_EQUIPOS,
        "archivo": "equipos.pdf",
        "ref_maprex": ref,
        "notas": _combinar_notas(nota, _nota_truncamiento(dato.truncada)),
    }


def fila_mano_obra(
    ref: str, dic: dict[str, FilaManoObra], nota: str, *, truncada: bool = False
) -> dict[str, str]:
    dato = dic[ref]
    precio_usd = _usd(dato.jornal)
    return {
        "tipo": "mano_obra",
        "insumo": dato.descripcion,
        "unidad": "dia",
        "precio_bs": str(dato.jornal),
        "bono_bs": str(dato.bono),
        "factor_depreciacion": "",
        "precio_usd": str(precio_usd),
        "fecha_vigencia": FECHA_MANO_OBRA,
        "archivo": "mano_de_obra.pdf",
        "ref_maprex": ref,
        "notas": _combinar_notas(nota, _nota_truncamiento(truncada)),
    }


# --------------------------------------------------------------------------------------
# Seleccion curada por dominio (Sesion M0.2): cada tupla es (ref_maprex, nota de contexto).
# Elegida y verificada a mano contra el PDF (ver docstring del modulo y la bitacora de la
# sesion). No es una busqueda difusa en tiempo de ejecucion: es la decision editorial de la
# sesion, y el script solo la resuelve contra el texto real del PDF (ver seccion anterior).
# --------------------------------------------------------------------------------------

# --- civil: los 37 insumos de tests/fixtures/apu_linea_base.py ------------------------

CIVIL_MATERIALES: tuple[tuple[str, str], ...] = (
    (
        "PLOA38",
        "equivalente de 'Tuberia PVC 4 pulg'; PVC A.N. (sanitario/drenaje) NORMA, D=4\"/110mm",
    ),
    ("PLO035", "equivalente de 'Curva PVC 4 pulg'; codo PVC 90 grados A.N. D=4\""),
    (
        "PLO560",
        "equivalente de 'Conector PVC 4 pulg'; union PVC A.B. 4\" (generica, sin "
        "distincion A.N./A.B. en MaPreX para uniones)",
    ),
    ("MT539", "equivalente de 'Pegamento para PVC'; pegamento 1/4 gl marca Tangit o similar"),
    (
        "ENC010",
        "equivalente de 'Madera'; madera de pino para encofrado, MaPreX cotiza por m3 "
        "(la linea base usa m2 de consumo simplificado, no unidad comercial)",
    ),
    (
        "ENC048",
        "equivalente de 'Listones de madera 2x2'; MaPreX solo lista liston 2\"x4\"x3mt, "
        "no 2x2; se usa como proxy dimensional mas cercano",
    ),
    (
        "ACE076",
        "equivalente de 'Clavos de acero 2 1/2 pulg'; clavo de acero liso L=2 1/2\", unidad pza",
    ),
    ("MZ0201", "equivalente de 'Desencofrante'; desencofrante Sika"),
    (
        "CEM019",
        "equivalente de 'Cemento Portland'; cemento gris Portland saco 42.5 kg "
        "(estandar de mercado)",
    ),
    ("MZ0027", "equivalente de 'Arena lavada'"),
    ("AGR081", "equivalente de 'Piedra picada'; variante 'para concreto'"),
    (
        "AGR003",
        "equivalente de 'Agua'; agua suministrada en camion cisterna o tanque (agua de "
        "obra, no potable embotellada)",
    ),
    ("BAS006", "equivalente de 'Material granular'; material granular integral"),
)

CIVIL_EQUIPOS: tuple[tuple[str, str], ...] = (
    ("MOV027", "equivalente de 'Retroexcavadora'; CASE o similar, sin martillo hidraulico adosado"),
    ("ALB072", "equivalente de 'Pico'; pico con cabo"),
    ("EZ0576", "equivalente de 'Pala'; pala cuadrada con cabo de madera"),
    ("VEH010", "equivalente de 'Camion de volteo'; Ford 7000 u similar, 8 m3"),
    ("EZ0512", "equivalente de 'Vehiculo de transporte'; vehiculo para transporte de personal"),
    ("CAR010", "equivalente de 'Segueta'; segueta ajustable (arco)"),
    ("MED001", "equivalente de 'Cinta metrica'; cinta metrica de 3 m"),
    ("ALB045", "equivalente de 'Sierra circular electrica'; D=7 1/4\" 110V"),
    ("DEM005", "equivalente de 'Martillo'; martillo carpintero nacional 0,6 kgm"),
    ("ALB024", "equivalente de 'Nivel de mano'; nivel de 3 burbujas 18\""),
    ("ELE046", "equivalente de 'Alicate'; alicate para electricista"),
    ("CON007", "equivalente de 'Mezcladora de concreto'; capacidad 0,40 m3, 12,2 HP diesel"),
    ("CON041", "equivalente de 'Vibrador de concreto'"),
    ("ALB073", "equivalente de 'Carretilla'; carretilla para construccion"),
    ("ALB146", "equivalente de 'Tobos plasticos'; tobo plastico 10 lt de albañileria"),
    (
        "CPT018",
        "equivalente de 'Compactadora de percusion tipo sapo'; MaPreX la llama 'rana' "
        "(sinonimo), 280 kg",
    ),
    (
        "ALB213",
        "equivalente de 'Herramientas menores'; MaPreX tiene tres filas con la misma "
        "descripcion exacta (ALB213 9.060 Bs, ALB171 30.200 Bs, EZ0263 37.750 Bs) sin "
        "ningun otro campo que las distinga; se elige la de menor precio (ALB213) como "
        "referencia conservadora ante la falta de un criterio propio de MaPreX",
    ),
)

CIVIL_MANO_OBRA: tuple[tuple[str, str], ...] = (
    (
        "24-5.4",
        "equivalente de 'Operador de equipo de 1ra'; tabulador construccion, operador "
        "de equipo pesado 1ra",
    ),
    ("1-1.2", "equivalente de 'Ayudante'; tabulador construccion, ayudante generico"),
    ("8-3.5", "equivalente de 'Chofer de 2da'; tabulador construccion, chofer de 2da (3 a 8 ton)"),
    ("4-3.3", "equivalente de 'Chofer de 4ta'; tabulador construccion"),
    (
        "24-216",
        "equivalente de 'Maestro (electricista, segun el APU original)'; maestro "
        "electricista, tabulador construccion",
    ),
    ("19-2.5", "equivalente de 'Carpintero de 1ra'; tabulador construccion"),
    ("19-2.2", "equivalente de 'Albañil de 1ra'; tabulador construccion"),
)

# --- telecom: renglones comparables con ARENAZA (data/telecom/plantilla_precios.csv) --

TELECOM_MATERIALES: tuple[tuple[str, str], ...] = (
    (
        "ELA006",
        "cable UTP categoria 6 (cubre 'Bobina Cable Utp Cat 6' y 'Bobina Cable Utp "
        "Cat6 305m Int' de la plantilla: mismo insumo, distinta presentacion de rollo)",
    ),
    (
        "ELE906",
        "equivalente de 'Tubo Corrugado Flexible 1 Pulgada'; tubo PVC electricidad "
        'corrugado flexible D=1" exacto',
    ),
    (
        "ELC069",
        "equivalente de 'Conectores Rj45 Cat6 Utp Bolsa'; conector RJ45 macho cat 6 "
        "(precio por pieza, no por bolsa de 100)",
    ),
    (
        "ELC065",
        "equivalente de 'Conector Jack Coupler Ubiquiti Rj45'; jack coupler hembra "
        "RJ45 cat 6 generico (MaPreX no distingue marca Ubiquiti)",
    ),
    (
        "QUI059",
        "cubre 'Bolsa Tirrap (100 unidades)' y 'Amarre Tiewrap Negro Plastico 20 Cm'; "
        "tirrap 3,5mm x 200mm, precio por pieza",
    ),
    (
        "ELF449",
        "equivalente de 'Organizador De Cables Individuales 20cm'; espiral organizador "
        "de cable (forma distinta: espiral continuo vs organizadores individuales)",
    ),
    (
        "ELF215",
        "cubre 'Teipe Electrico Negro Cobra' y 'Teipe Aislante Para Cableado "
        "Electrico'; cinta aislante plastica negra (MaPreX no lista la marca Cobra)",
    ),
    (
        "ELA190",
        "equivalente de 'Toma Doble Con Tierra 270 20a Con Placa Blanca'; "
        "tomacorriente doble 1 fase 20/30A",
    ),
    ("ELE033", "equivalente de 'Anillo E.m.t. 2'; anillo EMT D=2\" exacto"),
    (
        "ACE894",
        "equivalente de 'Guaya Guia Pasa Cable De Acero'; guaya de acero D=1/4\" "
        "(calibre fino, tipico de guia pasacables)",
    ),
    (
        "ELE654",
        "equivalente de 'Cajetin Plastico 4x2 Pvc Con Grapa Metalica'; cajetin "
        'rectangular PVC 2"x4" (misma medida, orden invertido)',
    ),
    (
        "ELC066",
        "equivalente de 'Cajetin Superficial 4x2 Hembra'; cajetin superficial de red "
        "1 puerto (MaPreX no distingue '4x2' en cajetines de red)",
    ),
    (
        "ELA633",
        "referencia generica de categoria para 'Switch Escritorio Gigabit 10P PoE', "
        "'Switch Tp-link Tl-sg108 8P' y 'Switch Tp-link 16P'; unico switch de marca en "
        "MaPreX es TP-Link 48P 10/100 para rack (puertos y PoE no coinciden, ver "
        "bitacora)",
    ),
    (
        "ELA553",
        "equivalente de 'Canaleta Plastica 40x40x2mts'; canaleta para cableado "
        'superficial 1"/25mm (seccion menor a 40x40mm)',
    ),
    (
        "ELC051",
        "referencia de categoria para 'Rack Fijo Onlink 12u'; rack abierto 4U de "
        "pared (MaPreX no tiene racks de pared de 12U)",
    ),
    (
        "ELC057",
        "referencia adicional de patch panel (categoria 'racks/canalizacion' del "
        "alcance de la sesion), no de un insumo puntual de la plantilla",
    ),
    (
        "EFO001",
        "referencia adicional de fibra optica (categoria explicita del alcance de la "
        "sesion), no de un insumo puntual de la plantilla; cable ADSS 48 hilos "
        "monomodo OM3",
    ),
)

TELECOM_EQUIPOS: tuple[tuple[str, str], ...] = (
    (
        "EFO001",
        "fusionadora/empalmadora de fibra optica; referencia de equipo de red para "
        "contraste (README: 'fusionadoras y equipos de red')",
    ),
)

# --- industrial: repuestos/servicios de data/samples/industrial/activos_planta.csv ----

INDUSTRIAL_MATERIALES: tuple[tuple[str, str], ...] = (
    (
        "MZ0623",
        "rodamiento de referencia para motores/bombas rotativas (MaPreX solo lista "
        "rodamiento de alternador; sin SKU generico de rodamiento industrial)",
    ),
    ("MZ0341", "grasa para rodamientos; lubricante de mantenimiento de rodamientos"),
    (
        "MEC528",
        "correa industrial A41 para motor; repuesto de transmision aplicable a compresores/motores",
    ),
    (
        "PLOG46",
        "repuesto para IN-005 Valvula de control neumatica (diametro=4 pulg; MaPreX "
        'solo tiene bola D=2" en acero inoxidable, diametro distinto)',
    ),
    (
        "PLO887",
        'valvula check D=1" piston acero inoxidable; repuesto adicional de valvuleria para bombas',
    ),
    ("COM032", "aceite para maquinas/motores; lubricante generico de mantenimiento"),
    ("MZ0294", "filtro de aceite de motor; repuesto de mantenimiento generico"),
    (
        "MZ0471",
        "material para instalacion de sello mecanico tipo cartucho; repuesto de "
        "IN-001/IN-007 (bombas centrifuga y sumergible)",
    ),
    (
        "ELA073",
        "repuesto/referencia para IN-004 Transformador de distribucion (150 kVA); "
        "MaPreX no tiene 150 kVA exacto, se usa 100 kVA monofasico como proxy de "
        "capacidad",
    ),
    ("ELA067", "repuesto/referencia para IN-010 Transformador de emergencia (75 kVA exacto)"),
)

INDUSTRIAL_EQUIPOS: tuple[tuple[str, str], ...] = (
    (
        "EZ0453",
        "herramienta de taller (README: 'herramientas y equipos de taller'); taladro "
        'industrial de banco 3/4" 750W',
    ),
)

INDUSTRIAL_MANO_OBRA: tuple[tuple[str, str], ...] = (
    (
        "24-6.7",
        "tecnico de mantenimiento; mecanico de equipo pesado de 1ra, tabulador construccion",
    ),
    ("19-215", "tecnico electricista; electricista de 1ra, tabulador construccion"),
)


# --------------------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------------------


def construir_civil(materiales, equipos, equipos_descartados, mano_obra) -> list[dict[str, str]]:
    filas = [fila_material(ref, materiales, nota) for ref, nota in CIVIL_MATERIALES]
    filas += [fila_equipo(ref, equipos, nota, equipos_descartados) for ref, nota in CIVIL_EQUIPOS]
    filas += [fila_mano_obra(ref, mano_obra, nota) for ref, nota in CIVIL_MANO_OBRA]
    return filas


def construir_telecom(materiales, equipos, equipos_descartados) -> list[dict[str, str]]:
    filas = [fila_material(ref, materiales, nota) for ref, nota in TELECOM_MATERIALES]
    filas += [fila_equipo(ref, equipos, nota, equipos_descartados) for ref, nota in TELECOM_EQUIPOS]
    return filas


def construir_industrial(
    materiales, equipos, equipos_descartados, mano_obra
) -> list[dict[str, str]]:
    filas = [fila_material(ref, materiales, nota) for ref, nota in INDUSTRIAL_MATERIALES]
    filas += [
        fila_equipo(ref, equipos, nota, equipos_descartados) for ref, nota in INDUSTRIAL_EQUIPOS
    ]
    filas += [fila_mano_obra(ref, mano_obra, nota) for ref, nota in INDUSTRIAL_MANO_OBRA]
    return filas


def construir_sistemas(tab_civ: dict[str, FilaManoObra]) -> list[dict[str, str]]:
    filas = []
    for ref, dato in sorted(tab_civ.items()):
        truncada = _tab_civ_truncada(ref, dato.descripcion)
        filas.append(
            fila_mano_obra(
                ref,
                tab_civ,
                "tabulador CIV 01/07/2026, escalafon P-1..P-10 (incluye ingeniero computista y "
                "analista de telecomunicaciones)",
                truncada=truncada,
            )
        )
    return filas


def escribir_csv(ruta: Path, filas: list[dict[str, str]]) -> None:
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CABECERA)
        escritor.writeheader()
        escritor.writerows(filas)


def main() -> int:
    texto_materiales = _texto_pdf(RUTA_MATERIALES)
    texto_equipos = _texto_pdf(RUTA_EQUIPOS)
    texto_mano_obra = _texto_pdf(RUTA_MANO_OBRA)

    materiales = parsear_materiales(texto_materiales)
    equipos, equipos_descartados = parsear_equipos(texto_equipos)
    tab_civ = parsear_tabulador_civ(texto_mano_obra)
    sal_const = parsear_tabulador_construccion(texto_mano_obra)

    if len(tab_civ) != 43:
        raise SystemExit(
            f"Se esperaban 43 filas del tabulador CIV y se parsearon {len(tab_civ)}. "
            "El layout de mano_de_obra.pdf pudo haber cambiado; revisar PATRON_TAB_CIV."
        )

    filas_civil = construir_civil(materiales, equipos, equipos_descartados, sal_const)
    filas_telecom = construir_telecom(materiales, equipos, equipos_descartados)
    filas_industrial = construir_industrial(materiales, equipos, equipos_descartados, sal_const)
    filas_sistemas = construir_sistemas(tab_civ)

    escribir_csv(CARPETA / "referencia_civil.csv", filas_civil)
    escribir_csv(CARPETA / "referencia_telecom.csv", filas_telecom)
    escribir_csv(CARPETA / "referencia_industrial.csv", filas_industrial)
    escribir_csv(CARPETA / "referencia_sistemas.csv", filas_sistemas)

    truncadas_sistemas = sum(
        1 for ref, dato in tab_civ.items() if _tab_civ_truncada(ref, dato.descripcion)
    )
    print("Referencia MaPreX generada:")
    print(f"  referencia_civil.csv       -> {len(filas_civil)} filas")
    print(f"  referencia_telecom.csv     -> {len(filas_telecom)} filas")
    print(f"  referencia_industrial.csv  -> {len(filas_industrial)} filas")
    print(f"  referencia_sistemas.csv    -> {len(filas_sistemas)} filas (tabulador CIV completo)")
    print(f"  descripciones truncadas en el PDF (sistemas): {truncadas_sistemas} de 43")

    # Diagnostico de auditoria (hallazgo de revision): equipos.pdf trae filas cuyo
    # Total impreso no coincide con Precio x Factor; se descartan del parseo (no se usan
    # como candidatas) y quedan registradas aqui, no solo silenciadas.
    print(
        f"  filas de equipos.pdf descartadas por el cruce Total=Precio x Factor: "
        f"{len(equipos_descartados)}"
    )
    for mensaje in equipos_descartados.values():
        print(f"    - {mensaje}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
