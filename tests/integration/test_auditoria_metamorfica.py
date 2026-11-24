"""Pruebas metamórficas de robustez sobre `procesar_libro` y `aplicacion.causas_raiz.agrupar`.

Parten del libro ficticio con 12 errores sembrados (`scripts/libro_ficticio_con_errores.py`) y
comparan el CONJUNTO de causas `(codigo, patron)` tras transformaciones que deberían conservarlas:
renombrar el archivo, mover una hoja sin renombrarla, escalar los precios de INSUMOS por k = 10 y
repetir la misma auditoría (determinismo).
"""

from __future__ import annotations

import io
import posixpath
import re
import warnings
import zipfile
from datetime import date
from decimal import Decimal

import openpyxl
from defusedxml import ElementTree

from aplicacion.causas_raiz import agrupar, patron
from fusion.proceso import ResultadoFusion, procesar_libro
from scripts import libro_ficticio_con_errores

FECHA_FIJA = date(2026, 11, 23)
PREFIJOS_INSUMO = ("MT-", "MO-", "EQ-")


def _causas(resultado: ResultadoFusion) -> set[tuple[str, str]]:
    filas = [
        (h.regla, h.severidad.name, h.descripcion)
        for h in resultado.informe.hallazgos
    ]
    causas, _ = agrupar(filas)
    return {(c.codigo, patron(c.descripcion)) for c in causas}


def _impactos_f1(resultado: ResultadoFusion) -> dict[tuple[str, ...], Decimal]:
    return {
        h.origen_ids: h.impacto
        for h in resultado.informe.hallazgos
        if h.regla == "F1" and h.impacto is not None
    }


def _nombres_de_hojas(datos: bytes) -> list[str]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        wb = openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=True)
        try:
            return list(wb.sheetnames)
        finally:
            wb.close()


def _mover_hoja(datos: bytes, nombre_hoja: str) -> bytes:
    """Mueve `nombre_hoja` al final del libro preservando `<v>` guardados y vínculos externos."""
    entrada = io.BytesIO(datos)
    salida = io.BytesIO()
    with (
        zipfile.ZipFile(entrada) as zin,
        zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        xml = zin.read("xl/workbook.xml").decode("utf-8")
        coincidencia = re.search(r"<sheets>(.*?)</sheets>", xml, re.DOTALL)
        assert coincidencia is not None
        etiquetas = re.findall(r"<sheet\b[^>]*(?:/>|></sheet>)", coincidencia.group(1))
        indice = next(i for i, e in enumerate(etiquetas) if f'name="{nombre_hoja}"' in e)
        elegida = etiquetas.pop(indice)
        if indice == len(etiquetas):
            etiquetas.insert(0, elegida)
        else:
            etiquetas.append(elegida)
        nuevo_xml = (
            xml[: coincidencia.start(1)] + "".join(etiquetas) + xml[coincidencia.end(1) :]
        )
        for item in zin.infolist():
            contenido = (
                nuevo_xml.encode("utf-8")
                if item.filename == "xl/workbook.xml"
                else zin.read(item.filename)
            )
            zout.writestr(item, contenido)
    return salida.getvalue()


def _ruta_xml_hoja(zf: zipfile.ZipFile, nombre_hoja: str) -> str:
    wb_xml = ElementTree.fromstring(zf.read("xl/workbook.xml"))
    rid = None
    for el in wb_xml.iter():
        if el.tag.rsplit("}", 1)[-1] == "sheet" and el.attrib.get("name") == nombre_hoja:
            rid = next(v for k, v in el.attrib.items() if k.endswith("}id") or k == "r:id")
            break
    assert rid is not None
    rels_xml = ElementTree.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    for el in rels_xml.iter():
        if el.tag.rsplit("}", 1)[-1] == "Relationship" and el.attrib.get("Id") == rid:
            destino = el.attrib["Target"]
            if destino.startswith("/"):
                return destino.lstrip("/")
            return posixpath.normpath(posixpath.join("xl", destino))
    raise AssertionError(f"no se encontró la hoja {nombre_hoja!r} en workbook.xml.rels")


def _escalar_precios_insumos(datos: bytes, factor: Decimal) -> bytes:
    """Localiza los precios de INSUMOS con openpyxl y los multiplica por `factor` en el XML."""
    coordenadas: list[str] = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        wb = openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=True)
        try:
            ws = wb["INSUMOS"]
            for fila_num, fila in enumerate(
                ws.iter_rows(min_col=1, max_col=6, values_only=True), start=1
            ):
                codigo, precio = fila[1], fila[4]
                if (
                    isinstance(codigo, str)
                    and codigo.strip().upper().startswith(PREFIJOS_INSUMO)
                    and isinstance(precio, int | float | Decimal)
                    and not isinstance(precio, bool)
                ):
                    coordenadas.append(f"E{fila_num}")
        finally:
            wb.close()
    assert coordenadas

    entrada = io.BytesIO(datos)
    salida = io.BytesIO()
    with (
        zipfile.ZipFile(entrada) as zin,
        zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        ruta_insumos = _ruta_xml_hoja(zin, "INSUMOS")
        xml = zin.read(ruta_insumos).decode("utf-8")
        for coord in coordenadas:
            patron_celda = re.compile(rf'(<c\b[^>]*\br="{coord}"[^>]*>\s*<v>)([^<]+)(</v>)')
            xml, reemplazos = patron_celda.subn(
                lambda m: f"{m.group(1)}{format(Decimal(m.group(2)) * factor, 'f')}{m.group(3)}",
                xml,
            )
            assert reemplazos == 1, coord
        for item in zin.infolist():
            contenido = (
                xml.encode("utf-8") if item.filename == ruta_insumos else zin.read(item.filename)
            )
            zout.writestr(item, contenido)
    return salida.getvalue()


def test_cambiar_nombre_del_archivo_conserva_las_causas() -> None:
    datos = libro_ficticio_con_errores.construir()
    r1 = procesar_libro(datos, "ficticio_original.xlsx", fecha_devolucion=FECHA_FIJA)
    r2 = procesar_libro(datos, "otro_nombre_presupuesto.xlsx", fecha_devolucion=FECHA_FIJA)
    causas = _causas(r1)
    assert causas
    assert _causas(r2) == causas


def test_mover_una_hoja_conserva_las_causas() -> None:
    datos = libro_ficticio_con_errores.construir()
    movido = _mover_hoja(datos, "APU-02")
    hojas_orig = _nombres_de_hojas(datos)
    hojas_mov = _nombres_de_hojas(movido)
    assert hojas_mov != hojas_orig
    assert set(hojas_mov) == set(hojas_orig)

    r_base = procesar_libro(datos, "ficticio.xlsx", fecha_devolucion=FECHA_FIJA)
    r_movido = procesar_libro(movido, "ficticio.xlsx", fecha_devolucion=FECHA_FIJA)
    assert _causas(r_movido) == _causas(r_base)


# Escalar los precios de INSUMOS por k no es una relación válida sin recalcular el libro: Sílice lee
# los valores que Excel guardó, y las fórmulas que dependen de INSUMOS conservan su valor viejo (L3 y
# F1 nuevos). Se prueba cuando esté el oráculo de LibreOffice (plan no circular, Fase 1), que
# recalcula el libro antes de auditarlo. Hallazgo de Gemini Neon, 2026-11-23.


def test_auditar_dos_veces_da_resultado_identico() -> None:
    datos = libro_ficticio_con_errores.construir()
    r1 = procesar_libro(datos, "ficticio.xlsx", fecha_devolucion=FECHA_FIJA)
    r2 = procesar_libro(datos, "ficticio.xlsx", fecha_devolucion=FECHA_FIJA)
    assert r1.informe.hallazgos == r2.informe.hallazgos
    assert r1.hallazgos_tabla == r2.hallazgos_tabla
    assert dict(r1.precios_unitarios) == dict(r2.precios_unitarios)
    assert dict(r1.totales_silice) == dict(r2.totales_silice)
    assert _causas(r1) == _causas(r2)
