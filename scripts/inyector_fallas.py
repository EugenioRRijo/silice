"""Inyector genérico de fallas en libros `.xlsx` a partir de una taxonomía TOML.

Herramienta LOCAL para evaluación no circular: un tercero define las categorías en TOML y
ejecuta el inyector sobre un libro limpio; las operaciones modifican celdas genéricas de hoja
de cálculo sin conocer las reglas de auditoría de Sílice.

    uv run python scripts/inyector_fallas.py LIBRO.xlsx --taxonomia T.toml \\
        --n 12 --semilla 7 --salida D:/ensayo
"""

from __future__ import annotations

import argparse
import io
import math
import posixpath
import random
import re
import sys
import tomllib
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import openpyxl
from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError
from defusedxml.ElementTree import fromstring as xml_seguro
from openpyxl.utils.cell import column_index_from_string as _col_idx
from openpyxl.utils.cell import get_column_letter as _col_letra

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.medir_auditoria_libro import (  # noqa: E402
    _destino_seguro,
    _texto,
    escribir_clave_vacia,
)

OPERACIONES: tuple[str, ...] = (
    "valor_fijo",
    "referencia_desplazada",
    "rango_recortado",
    "signo",
    "escala",
    "formula_borrada",
)
_DELTAS_FIJO: tuple[str, ...] = ("-0.2", "-0.15", "-0.1", "0.1", "0.15", "0.2")
_MAX_COL_EXCEL = 16384
_MAX_FILA_EXCEL = 1048576

_ATRS_XML = r"(?:\s+[^\s=/<>]+\s*=\s*(?:\"[^\"]*\"|'[^']*'))*\s*"
_CELDA_XML = re.compile(
    rf"<(?P<p>(?:\w+:)?)c\b(?P<attrs>{_ATRS_XML})(?:/>|>(?P<cuerpo>.*?)</(?P=p)c>)",
    re.S,
)
_ATRIBUTO_XML = re.compile(r'(?P<nombre>[^\s=/<>]+)\s*=\s*(?P<q>["\'])(?P<valor>.*?)(?P=q)')
_TAG_F = re.compile(
    rf"<(?P<fp>(?:\w+:)?)f\b(?P<fattrs>{_ATRS_XML})(?:/>|>(?P<ftext>.*?)</(?P=fp)f>)",
    re.S,
)
_TAG_V = re.compile(
    rf"<(?P<vp>(?:\w+:)?)v\b(?P<vattrs>{_ATRS_XML})(?:/>|>(?P<vtext>.*?)</(?P=vp)v>)",
    re.S,
)
_TAG_IS = re.compile(
    rf"<(?P<ip>(?:\w+:)?)is\b(?P<iattrs>{_ATRS_XML})(?:/>|>(?P<itext>.*?)</(?P=ip)is>)",
    re.S,
)
_ATTR_T = re.compile(r"\s+(?:\w+:)?t\s*=\s*(?:\"[^\"]*\"|'[^']*')")

_CITADO_FORMULA = re.compile(r'"(?:[^"]|"")*"|\'(?:[^\']|\'\')*\'')
_REF_CELDA = re.compile(
    r"(?<![A-Za-z0-9_:])(\$?[A-Za-z]{1,3}\$?)(\d+)(?![A-Za-z0-9_(:])(?!\s*!)"
)
_RANGO = re.compile(
    r"(?<![A-Za-z0-9_:])(\$?[A-Za-z]{1,3}\$?)(\d+):(\$?[A-Za-z]{1,3}\$?)(\d+)"
    r"(?![A-Za-z0-9_(:])(?!\s*!)"
)


@dataclass(frozen=True, slots=True)
class Inyeccion:
    numero: int
    hoja: str
    celda: str
    categoria: str
    operacion: str
    antes: str
    despues: str


@dataclass(frozen=True, slots=True)
class _Categoria:
    id: str
    nombre: str
    fuente: str
    operacion: str
    peso: float
    hojas: tuple[str, ...] | None = None
    delta: float | None = None


@dataclass(frozen=True, slots=True)
class _Celda:
    hoja: str
    coord: str
    es_formula: bool
    formula: str | None
    valor: object


def cargar_taxonomia(ruta: Path) -> dict[str, Any]:
    with Path(ruta).open("rb") as archivo:
        return tomllib.load(archivo)


def _es_numero_finito(valor: object) -> bool:
    if isinstance(valor, bool):
        return False
    if isinstance(valor, Decimal):
        return valor.is_finite()
    return isinstance(valor, (int, float)) and math.isfinite(valor)


def _parsear_categorias(taxonomia: Mapping[str, Any]) -> list[_Categoria]:
    crudo = taxonomia.get("categorias")
    if not isinstance(crudo, Sequence) or isinstance(crudo, (str, bytes)) or not crudo:
        raise ValueError("La taxonomía debe incluir una lista no vacía «categorias».")
    categorias: list[_Categoria] = []
    for idx, item in enumerate(crudo, start=1):
        if not isinstance(item, Mapping):
            raise ValueError(f"La categoría #{idx} debe ser una tabla TOML.")
        for campo in ("id", "nombre", "fuente", "operacion", "peso"):
            if campo not in item:
                raise ValueError(f"A la categoría #{idx} le falta el campo obligatorio «{campo}».")
        op = str(item["operacion"])
        if op not in OPERACIONES:
            raise ValueError(f"Operación desconocida «{op}» en la categoría {item['id']}.")
        peso = item["peso"]
        if not _es_numero_finito(peso) or float(peso) <= 0:
            raise ValueError(f"El peso de la categoría {item['id']} debe ser un número mayor a 0.")
        hojas_raw = item.get("hojas")
        hojas = tuple(str(h) for h in hojas_raw) if hojas_raw is not None else None
        delta_raw = item.get("delta")
        delta = float(delta_raw) if delta_raw is not None else None
        if delta is not None and (not math.isfinite(delta) or delta == 0):
            raise ValueError(f"El delta de la categoría {item['id']} debe ser distinto de 0.")
        categorias.append(
            _Categoria(
                id=str(item["id"]),
                nombre=str(item["nombre"]),
                fuente=str(item["fuente"]),
                operacion=op,
                peso=float(peso),
                hojas=hojas,
                delta=delta,
            )
        )
    return categorias


def _fmt_decimal(d: Decimal) -> str:
    if d == 0:
        return "0"
    return f"{d.normalize():f}"


def _a_xml(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _col_valida(col_prefijo: str) -> int | None:
    letras = col_prefijo.replace("$", "").upper()
    try:
        idx = _col_idx(letras)
    except ValueError:
        return None
    return idx if 1 <= idx <= _MAX_COL_EXCEL else None


def _tramos_no_citados(cuerpo: str) -> list[tuple[int, int]]:
    tramos: list[tuple[int, int]] = []
    pos = 0
    for m in _CITADO_FORMULA.finditer(cuerpo):
        if m.start() > pos:
            tramos.append((pos, m.start()))
        pos = m.end()
    if pos < len(cuerpo):
        tramos.append((pos, len(cuerpo)))
    return tramos


def _refs_celda(formula: str) -> list[tuple[int, int, str, int]]:
    cuerpo = formula[1:]
    halladas: list[tuple[int, int, str, int]] = []
    for ini, fin in _tramos_no_citados(cuerpo):
        for m in _REF_CELDA.finditer(cuerpo, ini, fin):
            col_pref = m.group(1)
            fila = int(m.group(2))
            if _col_valida(col_pref) is not None and 1 <= fila <= _MAX_FILA_EXCEL:
                halladas.append((m.start() + 1, m.end() + 1, col_pref, fila))
    return halladas


def _rangos(formula: str) -> list[tuple[int, int, str, int, str, int, int, int]]:
    cuerpo = formula[1:]
    hallados: list[tuple[int, int, str, int, str, int, int, int]] = []
    for ini, fin in _tramos_no_citados(cuerpo):
        for m in _RANGO.finditer(cuerpo, ini, fin):
            c1, r1, c2, r2 = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
            idx1, idx2 = _col_valida(c1), _col_valida(c2)
            if idx1 is None or idx2 is None:
                continue
            if not (1 <= r1 <= _MAX_FILA_EXCEL and 1 <= r2 <= _MAX_FILA_EXCEL):
                continue
            if r2 > r1 or (r1 == r2 and idx2 > idx1):
                hallados.append((m.start() + 1, m.end() + 1, c1, r1, c2, r2, idx1, idx2))
    return hallados


def _es_elegible(celda: _Celda, operacion: str) -> bool:
    if operacion == "valor_fijo":
        return celda.es_formula and celda.formula is not None and _es_numero_finito(celda.valor)
    if operacion == "referencia_desplazada":
        return celda.es_formula and celda.formula is not None and bool(_refs_celda(celda.formula))
    if operacion == "rango_recortado":
        return celda.es_formula and celda.formula is not None and bool(_rangos(celda.formula))
    if operacion in ("signo", "escala"):
        return not celda.es_formula and _es_numero_finito(celda.valor) and celda.valor != 0
    if operacion == "formula_borrada":
        return celda.es_formula and celda.formula is not None
    return False


def _aplicar_operacion(
    celda: _Celda, cat: _Categoria, rng: random.Random
) -> tuple[str, str, str, str]:
    """Devuelve `(antes, despues, modo_xml, payload_xml)`."""
    op = cat.operacion
    if op == "valor_fijo":
        assert celda.formula is not None
        delta = (Decimal(str(cat.delta)) if cat.delta is not None
                 else Decimal(rng.choice(_DELTAS_FIJO)))
        nuevo = _fmt_decimal(Decimal(str(celda.valor)) * (Decimal(1) + delta))
        return celda.formula, nuevo, "numero", nuevo
    if op == "referencia_desplazada":
        assert celda.formula is not None
        ini, fin, col_pref, fila = rng.choice(_refs_celda(celda.formula))
        nueva_fila = fila + 1 if fila < _MAX_FILA_EXCEL else fila - 1
        nueva = f"{celda.formula[:ini]}{col_pref}{nueva_fila}{celda.formula[fin:]}"
        return celda.formula, nueva, "formula", nueva
    if op == "rango_recortado":
        assert celda.formula is not None
        ini, fin, c1, r1, c2, r2, _idx1, idx2 = rng.choice(_rangos(celda.formula))
        if r2 > r1:
            extremo = f"{c2}{r2 - 1}"
        else:
            dolar_c = "$" if c2.startswith("$") else ""
            dolar_f = "$" if c2.endswith("$") else ""
            extremo = f"{dolar_c}{_col_letra(idx2 - 1)}{dolar_f}{r2}"
        nueva = f"{celda.formula[:ini]}{c1}{r1}:{extremo}{celda.formula[fin:]}"
        return celda.formula, nueva, "formula", nueva
    if op == "signo":
        antes_dec = Decimal(str(celda.valor))
        nuevo = _fmt_decimal(-antes_dec)
        return _fmt_decimal(antes_dec), nuevo, "numero", nuevo
    if op == "escala":
        antes_dec = Decimal(str(celda.valor))
        nuevo = _fmt_decimal(antes_dec * Decimal(1000))
        return _fmt_decimal(antes_dec), nuevo, "numero", nuevo
    if op == "formula_borrada":
        assert celda.formula is not None
        return celda.formula, "(vacía)", "vacio", ""
    raise ValueError(f"Operación no soportada: {op}")


def _attr(attrs: str, objetivo: str) -> str | None:
    for m in _ATRIBUTO_XML.finditer(attrs):
        if m.group("nombre").rsplit(":", 1)[-1] == objetivo:
            return m.group("valor")
    return None


def _comprobar_xml(nombre: str, contenido: bytes) -> None:
    try:
        xml_seguro(contenido, forbid_dtd=True)
    except (DefusedXmlException, ParseError) as err:
        raise ValueError(f"XML inválido en «{nombre}»: {err}") from err


def _mapa_hojas(paquete: Mapping[str, bytes]) -> dict[str, str]:
    rels_bytes = paquete.get("xl/_rels/workbook.xml.rels", b"")
    wb_bytes = paquete.get("xl/workbook.xml", b"")
    if not rels_bytes or not wb_bytes:
        return {}
    rels_root = xml_seguro(rels_bytes, forbid_dtd=True)
    destinos: dict[str, str] = {}
    for el in rels_root:
        rid = el.attrib.get("Id")
        target = el.attrib.get("Target", "")
        if rid and target:
            parte = target.lstrip("/") if target.startswith("/") else posixpath.normpath(
                posixpath.join("xl", target)
            )
            destinos[rid] = parte
    wb_root = xml_seguro(wb_bytes, forbid_dtd=True)
    mapa: dict[str, str] = {}
    for el in wb_root.iter():
        if el.tag.rsplit("}", 1)[-1] != "sheet":
            continue
        nombre = el.attrib.get("name")
        rid = next((v for k, v in el.attrib.items() if k.rsplit("}", 1)[-1] == "id"), None)
        if nombre and rid in destinos:
            mapa[nombre] = destinos[rid]
    return mapa


def _celdas_formula_especial(xml: str) -> set[str]:
    especiales: set[str] = set()
    for m in _CELDA_XML.finditer(xml):
        cuerpo = m.group("cuerpo") or ""
        if not cuerpo:
            continue
        mf = _TAG_F.search(cuerpo)
        if mf is None:
            continue
        tipo = _attr(mf.group("fattrs"), "t")
        if tipo in ("shared", "array") or not (mf.group("ftext") or "").strip():
            coord = _attr(m.group("attrs"), "r")
            if coord:
                especiales.add(coord)
    return especiales


def _editar_celda_xml(xml: str, coord: str, modo: str, payload: str) -> str:
    for m in _CELDA_XML.finditer(xml):
        if _attr(m.group("attrs"), "r") != coord:
            continue
        p = m.group("p")
        attrs = m.group("attrs")
        cuerpo = m.group("cuerpo") or ""
        if modo == "formula":
            formula_xml = _a_xml(payload.removeprefix("="))
            nuevo_cuerpo, n = _TAG_F.subn(
                lambda fm, fx=formula_xml: (
                    f"<{fm.group('fp')}f{fm.group('fattrs')}>{fx}</{fm.group('fp')}f>"
                ),
                cuerpo,
                count=1,
            )
            if n != 1:
                raise RuntimeError(f"No se encontró fórmula editable en {coord}.")
            nuevo_tag = f"<{p}c{attrs}>{nuevo_cuerpo}</{p}c>"
        elif modo == "numero":
            attrs_limpios = _ATTR_T.sub("", attrs)
            cuerpo = _TAG_F.sub("", cuerpo)
            cuerpo = _TAG_IS.sub("", cuerpo)
            cuerpo, n = _TAG_V.subn(
                lambda vm: f"<{vm.group('vp')}v>{payload}</{vm.group('vp')}v>",
                cuerpo,
                count=1,
            )
            if n == 0:
                cuerpo = f"{cuerpo}<{p}v>{payload}</{p}v>"
            nuevo_tag = f"<{p}c{attrs_limpios}>{cuerpo}</{p}c>"
        elif modo == "vacio":
            attrs_limpios = _ATTR_T.sub("", attrs)
            cuerpo = _TAG_F.sub("", cuerpo)
            cuerpo = _TAG_V.sub("", cuerpo)
            cuerpo = _TAG_IS.sub("", cuerpo)
            nuevo_tag = (
                f"<{p}c{attrs_limpios}>{cuerpo}</{p}c>" if cuerpo.strip()
                else f"<{p}c{attrs_limpios}/>"
            )
        else:
            raise ValueError(f"Modo XML desconocido: {modo}")
        return f"{xml[:m.start()]}{nuevo_tag}{xml[m.end():]}"
    raise RuntimeError(f"No se encontró la celda {coord} en el XML de la hoja.")


def _leer_celdas(
    datos: bytes, paquete: Mapping[str, bytes], mapa: Mapping[str, str]
) -> list[_Celda]:
    especiales = {
        hoja: _celdas_formula_especial(paquete[parte].decode("utf-8", "replace"))
        for hoja, parte in mapa.items()
        if parte in paquete
    }
    wb_f = openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=False)
    wb_v = openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=True)
    celdas: list[_Celda] = []
    try:
        for ws_f in wb_f.worksheets:
            hoja = ws_f.title
            if hoja not in mapa:
                continue
            ws_v = wb_v[hoja]
            valores: dict[tuple[int, int], object] = {}
            for fila in ws_v.iter_rows(values_only=False):
                for cell in fila:
                    if cell.value is not None:
                        valores[(cell.row, cell.column)] = cell.value
            omitir = especiales.get(hoja, set())
            for fila in ws_f.iter_rows(values_only=False):
                for cell in fila:
                    val = cell.value
                    if val is None:
                        continue
                    coord = cell.coordinate
                    if coord in omitir:
                        continue
                    es_formula = cell.data_type == "f" or (
                        isinstance(val, str) and val.startswith("=")
                    )
                    celdas.append(
                        _Celda(
                            hoja=hoja,
                            coord=coord,
                            es_formula=es_formula,
                            formula=val if es_formula and isinstance(val, str) else None,
                            valor=valores.get((cell.row, cell.column)),
                        )
                    )
    finally:
        wb_f.close()
        wb_v.close()
    return celdas


def inyectar(
    datos: bytes, taxonomia: Mapping[str, Any], n: int, semilla: int
) -> tuple[bytes, list[Inyeccion]]:
    """Inyecta hasta `n` fallas deterministas en `datos` según `taxonomia` y `semilla`."""
    if n < 0:
        raise ValueError("El número de fallas `n` no puede ser negativo.")
    categorias = _parsear_categorias(taxonomia)
    if n == 0:
        return datos, []

    with zipfile.ZipFile(io.BytesIO(datos)) as zf:
        infos = zf.infolist()
        paquete = {info.filename: zf.read(info.filename) for info in infos}
    for nombre, contenido in paquete.items():
        if nombre.endswith((".xml", ".rels")) or nombre == "[Content_Types].xml":
            _comprobar_xml(nombre, contenido)

    mapa = _mapa_hojas(paquete)
    celdas = _leer_celdas(datos, paquete, mapa)
    xml_hojas: dict[str, str] = {}
    hojas_tocadas: set[str] = set()
    rng = random.Random(semilla)
    pendientes = list(categorias)
    modificadas: set[tuple[str, str]] = set()
    inyecciones: list[Inyeccion] = []

    while len(inyecciones) < n and pendientes:
        cat = rng.choices(pendientes, weights=[c.peso for c in pendientes], k=1)[0]
        elegibles = [
            c
            for c in celdas
            if (c.hoja, c.coord) not in modificadas
            and (cat.hojas is None or c.hoja in cat.hojas)
            and _es_elegible(c, cat.operacion)
        ]
        if not elegibles:
            print(
                f"Aviso: la operación «{cat.operacion}» (categoría {cat.id}) "
                "no encontró celdas elegibles.",
                file=sys.stderr,
            )
            pendientes = [c for c in pendientes if c is not cat]
            continue

        objetivo = rng.choice(elegibles)
        antes, despues, modo, payload = _aplicar_operacion(objetivo, cat, rng)
        parte = mapa[objetivo.hoja]
        if parte not in xml_hojas:
            xml_hojas[parte] = paquete[parte].decode("utf-8")
        xml_hojas[parte] = _editar_celda_xml(xml_hojas[parte], objetivo.coord, modo, payload)
        hojas_tocadas.add(parte)
        modificadas.add((objetivo.hoja, objetivo.coord))
        inyecciones.append(
            Inyeccion(
                numero=len(inyecciones) + 1,
                hoja=objetivo.hoja,
                celda=objetivo.coord,
                categoria=cat.id,
                operacion=cat.operacion,
                antes=antes,
                despues=despues,
            )
        )

    if not hojas_tocadas:
        return datos, inyecciones

    for parte in hojas_tocadas:
        codificado = xml_hojas[parte].encode("utf-8")
        _comprobar_xml(parte, codificado)
        paquete[parte] = codificado

    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in infos:
            zout.writestr(info, paquete[info.filename])
    return salida.getvalue(), inyecciones


def generar(
    origen: Path,
    taxonomia_ruta: Path,
    *,
    n: int,
    semilla: int,
    salida: Path,
    raiz_repo: Path = RAIZ,
) -> tuple[Path, Path]:
    """Escribe fuera del repositorio el libro inyectado y su clave."""
    origen = Path(origen)
    salida = Path(salida)
    raiz_repo = Path(raiz_repo)
    ruta_libro = _destino_seguro(salida / f"{origen.stem}_inyectado.xlsx", raiz_repo)
    ruta_clave_prev = _destino_seguro(salida / f"{origen.stem}_clave.xlsx", raiz_repo)

    taxonomia = cargar_taxonomia(taxonomia_ruta)
    nombres = {str(c["id"]): str(c["nombre"]) for c in taxonomia.get("categorias", ())}
    datos_out, inyecciones = inyectar(origen.read_bytes(), taxonomia, n=n, semilla=semilla)

    salida.mkdir(parents=True, exist_ok=True)
    ruta_libro.write_bytes(datos_out)
    ruta_clave = escribir_clave_vacia(ruta_clave_prev, raiz_repo=raiz_repo)
    wb_clave = openpyxl.load_workbook(ruta_clave)
    hoja = wb_clave["Sembrados"]
    for inj in inyecciones:
        fila = hoja.max_row + 1
        hoja.cell(row=fila, column=1, value=inj.numero)
        _texto(hoja.cell(row=fila, column=2), f"{inj.hoja}!{inj.celda}")
        nombre = nombres.get(inj.categoria, inj.categoria)
        _texto(hoja.cell(row=fila, column=3), f"{inj.categoria}: {nombre}")
        _texto(hoja.cell(row=fila, column=4), f"{inj.antes} → {inj.despues}")
    wb_clave.save(ruta_clave)
    return ruta_libro, ruta_clave


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("libro", help="ruta del libro .xlsx de entrada")
    analizador.add_argument("--taxonomia", required=True, help="archivo TOML de categorías")
    analizador.add_argument("--n", type=int, default=12, help="cantidad de fallas a inyectar")
    analizador.add_argument("--semilla", type=int, default=7, help="semilla determinista")
    analizador.add_argument("--salida", required=True, help="carpeta fuera del repositorio")
    analizador.add_argument("--raiz-repo", default=str(RAIZ))
    args = analizador.parse_args(argv)
    libro, clave = generar(
        Path(args.libro),
        Path(args.taxonomia),
        n=args.n,
        semilla=args.semilla,
        salida=Path(args.salida),
        raiz_repo=Path(args.raiz_repo),
    )
    print(f"Libro inyectado: {libro}")
    print(f"Clave de la siembra: {clave}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
