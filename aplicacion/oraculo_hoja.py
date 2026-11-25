"""Oráculo independiente de recálculo de hojas `.xlsx` (Fase 1, auditoría no circular).

Rompe la circularidad de F1 ejecutando un motor externo (LibreOffice Calc sin interfaz, en un
perfil temporal que fuerza `OOXMLRecalcMode = 0`) y comparando cada celda con fórmula del libro
original frente al valor recalculado. No toca `core/`.
"""

from __future__ import annotations

import contextlib
import io
import math
import os
import shutil
import subprocess
import sys
import tempfile
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from xml.sax.saxutils import escape

import openpyxl

from adapters.hoja_empresa.guardia import MAX_CELDAS_LIBRO, ArchivoRechazado, verificar_archivo
from adapters.hoja_empresa.lector import filas_acotadas, letra
from adapters.hoja_empresa.umbrales import MEDIO_CENTAVO

__all__ = [
    "TIEMPO_MAXIMO_SEGUNDOS",
    "TOLERANCIA_ABSOLUTA",
    "TOLERANCIA_RELATIVA",
    "Discrepancia",
    "LibreOfficeNoDisponibleError",
    "OraculoError",
    "Recalculador",
    "RecalculadorLibreOffice",
    "ValorCelda",
    "buscar_libreoffice",
    "comparar",
    "contar_formulas",
    "oraculo",
]

TOLERANCIA_RELATIVA = Decimal("1e-9")
TOLERANCIA_ABSOLUTA = MEDIO_CENTAVO
TIEMPO_MAXIMO_SEGUNDOS = 120

ValorCelda = Decimal | str | bool | None


class OraculoError(RuntimeError):
    """Fallo al recalcular el libro con el motor externo."""


class LibreOfficeNoDisponibleError(FileNotFoundError):
    """No se encontró el ejecutable `soffice` de LibreOffice en el equipo."""


@runtime_checkable
class Recalculador(Protocol):
    """Motor externo capaz de recalcular todas las fórmulas de un libro `.xlsx`."""

    def recalcular(self, datos: bytes, nombre: str) -> bytes: ...


@dataclass(frozen=True, slots=True)
class Discrepancia:
    """Diferencia entre el valor guardado en el `.xlsx` y el valor recalculado."""

    hoja: str
    celda: str
    formula: str
    guardado: ValorCelda
    recalculado: ValorCelda


def _xcu_recalculo_siempre(configuracion_regional: str) -> str:
    loc = escape(configuracion_regional, {'"': "&quot;"})
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<oor:items xmlns:oor="http://openoffice.org/2001/registry" '
        'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        '<item oor:path="/org.openoffice.Office.Calc/Formula/Load">'
        '<prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item>\n'
        '<item oor:path="/org.openoffice.Office.Calc/Formula/Load">'
        '<prop oor:name="ODFRecalcMode" oor:op="fuse"><value>0</value></prop></item>\n'
        '<item oor:path="/org.openoffice.Setup/L10N">'
        f'<prop oor:name="ooSetupSystemLocale" oor:op="fuse"><value>{loc}</value></prop></item>\n'
        "</oor:items>\n"
    )


def _preparar_perfil_temporal(carpeta_perfil: Path, configuracion_regional: str) -> str:
    carpeta_usuario = carpeta_perfil / "user"
    carpeta_usuario.mkdir(parents=True, exist_ok=True)
    (carpeta_usuario / "registrymodifications.xcu").write_text(
        _xcu_recalculo_siempre(configuracion_regional), encoding="utf-8"
    )
    return f"-env:UserInstallation={carpeta_perfil.resolve().as_uri()}"


def _rutas_windows(entorno: Mapping[str, str]) -> list[Path]:
    bases = (
        entorno.get("ProgramFiles", r"C:\Program Files"),
        entorno.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        entorno.get("LOCALAPPDATA", ""),
    )
    candidatas: list[Path] = []
    vistas: set[str] = set()
    for base in bases:
        if not base or base in vistas:
            continue
        vistas.add(base)
        raiz = Path(base)
        for subcarpeta in (Path("LibreOffice/program"), Path("Programs/LibreOffice/program")):
            for binario in ("soffice.com", "soffice.exe"):
                candidatas.append(raiz / subcarpeta / binario)
    return candidatas


def buscar_libreoffice(entorno: Mapping[str, str] | None = None) -> Path:
    """Busca `soffice` en el PATH y en las rutas habituales de Windows."""
    env = os.environ if entorno is None else entorno
    ruta_path = None if entorno is None else env.get("PATH", "")
    for nombre_bin in ("soffice", "libreoffice"):
        hallado = shutil.which(nombre_bin, path=ruta_path)
        if hallado:
            return Path(hallado)
    for candidata in _rutas_windows(env):
        if candidata.is_file():
            return candidata
    raise LibreOfficeNoDisponibleError(
        "No se encontró LibreOffice (soffice) en el PATH ni en las rutas habituales. "
        "Instale LibreOffice para recalcular libros con el oráculo independiente."
    )


_ES_WINDOWS = sys.platform == "win32"


def _terminar_arbol(proceso: subprocess.Popen[str]) -> None:
    """Termina el proceso y sus hijos (soffice.bin sobrevive al lanzador en Windows)."""
    if _ES_WINDOWS:
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proceso.pid)],
                capture_output=True,
                check=False,
                timeout=30,
            )
    else:
        # El proceso nace con start_new_session=True: su pid es también el id del grupo.
        with contextlib.suppress(OSError, AttributeError):
            os.killpg(os.getpgid(proceso.pid), 9)
    with contextlib.suppress(OSError):
        proceso.kill()
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        proceso.communicate(timeout=10)


class RecalculadorLibreOffice:
    """Recalcula libros `.xlsx` mediante LibreOffice Calc sin interfaz gráfica."""

    def __init__(
        self,
        ejecutable: Path | str | None = None,
        *,
        tiempo_maximo: float = TIEMPO_MAXIMO_SEGUNDOS,
        configuracion_regional: str = "es-VE",
    ) -> None:
        self._ejecutable = Path(ejecutable) if ejecutable is not None else None
        self._tiempo_maximo = tiempo_maximo
        self._configuracion_regional = configuracion_regional

    def _resolver_ejecutable(self) -> Path:
        if self._ejecutable is None:
            return buscar_libreoffice()
        if not self._ejecutable.is_file():
            raise LibreOfficeNoDisponibleError(
                f"No existe el ejecutable «{self._ejecutable}». Instale LibreOffice o indique "
                "una ruta válida."
            )
        return self._ejecutable

    def version(self) -> str:
        """Devuelve la cadena de versión reportada por `soffice --version`."""
        ejecutable = self._resolver_ejecutable()
        try:
            proceso = subprocess.run(
                [str(ejecutable), "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=self._tiempo_maximo,
            )
        except subprocess.TimeoutExpired as exc:
            raise OraculoError(
                f"LibreOffice tardó más de {self._tiempo_maximo} s al consultar su versión."
            ) from exc
        if proceso.returncode != 0:
            detalle = (proceso.stderr or proceso.stdout).strip()
            raise OraculoError(f"No se pudo obtener la versión de LibreOffice: {detalle}")
        salida = (proceso.stdout or proceso.stderr).strip()
        return salida.splitlines()[0].strip() if salida else "LibreOffice (versión desconocida)"

    def recalcular(self, datos: bytes, nombre: str) -> bytes:
        verificar_archivo(datos, nombre)
        ejecutable = self._resolver_ejecutable()
        with tempfile.TemporaryDirectory(
            prefix="silice_lo_", ignore_cleanup_errors=True
        ) as temporal:
            base = Path(temporal)
            arg_perfil = _preparar_perfil_temporal(base / "perfil", self._configuracion_regional)
            carpeta_entrada = base / "entrada"
            carpeta_salida = base / "salida"
            carpeta_entrada.mkdir()
            carpeta_salida.mkdir()
            entrada = carpeta_entrada / "libro.xlsx"
            entrada.write_bytes(datos)
            orden = [
                str(ejecutable),
                arg_perfil,
                "--headless",
                "--norestore",
                "--nolockcheck",
                "--nodefault",
                "--nofirststartwizard",
                "--convert-to",
                "xlsx",
                "--outdir",
                str(carpeta_salida),
                str(entrada),
            ]
            salida = carpeta_salida / "libro.xlsx"
            proceso: subprocess.Popen[str] | None = None
            arbol_terminado = False
            try:
                proceso = subprocess.Popen(
                    orden,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=not _ES_WINDOWS,
                )
                try:
                    texto_salida, texto_error = proceso.communicate(timeout=self._tiempo_maximo)
                except subprocess.TimeoutExpired as exc:
                    arbol_terminado = True
                    _terminar_arbol(proceso)
                    raise OraculoError(
                        f"LibreOffice superó el tiempo máximo de {self._tiempo_maximo} s al "
                        f"recalcular «{nombre}»."
                    ) from exc
                if proceso.returncode != 0 or not salida.is_file():
                    detalle = (texto_error or texto_salida).strip()
                    raise OraculoError(
                        f"LibreOffice no pudo recalcular «{nombre}» "
                        f"(código {proceso.returncode}): {detalle}"
                    )
                return salida.read_bytes()
            finally:
                # Ante cualquier salida anormal (p. ej. Ctrl+C) el hijo puede seguir vivo y, en
                # Windows, retener la copia del libro: se termina el árbol antes de borrar.
                if proceso is not None and not arbol_terminado and proceso.poll() is None:
                    _terminar_arbol(proceso)
                for archivo in (entrada, salida):
                    with contextlib.suppress(OSError):
                        archivo.unlink()
                for archivo in (entrada, salida):
                    if archivo.exists():
                        print(
                            f"Aviso: No se pudo borrar la copia temporal «{archivo}»; "
                            "bórrela a mano (contiene el libro).",
                            file=sys.stderr,
                        )


def _abrir_solo_lectura(datos: bytes, nombre: str, *, data_only: bool) -> Any:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return openpyxl.load_workbook(
                io.BytesIO(datos),
                read_only=True,
                data_only=data_only,
                keep_vba=False,
                keep_links=False,
            )
    except Exception as exc:
        raise ArchivoRechazado(
            f"No se pudo abrir «{nombre}»: el archivo .xlsx está dañado o no es de Excel."
        ) from exc


def _formula_de(celda: Any) -> str | None:
    if getattr(celda, "data_type", None) != "f":
        return None
    valor = celda.value
    cadena = getattr(valor, "text", None) or (valor if isinstance(valor, str) else None)
    if not cadena:
        return None
    return cadena if cadena.startswith("=") else f"={cadena}"


def _normalizar_valor(valor: Any) -> ValorCelda:
    if valor is None or isinstance(valor, bool | str):
        return valor
    if isinstance(valor, Decimal):
        if not valor.is_finite():
            return str(valor)
        return valor.copy_abs() if valor.is_zero() else valor
    if isinstance(valor, int | float):
        if isinstance(valor, float) and not math.isfinite(valor):
            return str(valor)
        convertido = Decimal(str(valor))
        return convertido.copy_abs() if convertido.is_zero() else convertido
    if isinstance(valor, datetime):
        return valor.date().isoformat() if valor.time() == time(0) else valor.isoformat()
    if isinstance(valor, date | time):
        return valor.isoformat()
    return str(valor)


def _valores_iguales(
    guardado: ValorCelda,
    recalculado: ValorCelda,
    *,
    tolerancia_relativa: Decimal,
    tolerancia_absoluta: Decimal,
) -> bool:
    if guardado is None and recalculado is None:
        return True
    if guardado is None or recalculado is None:
        return False
    if isinstance(guardado, bool) or isinstance(recalculado, bool):
        return (
            isinstance(guardado, bool)
            and isinstance(recalculado, bool)
            and guardado == recalculado
        )
    if isinstance(guardado, Decimal) and isinstance(recalculado, Decimal):
        escala = max(abs(guardado), abs(recalculado))
        umbral = max(tolerancia_absoluta, tolerancia_relativa * escala)
        return abs(guardado - recalculado) <= umbral
    if isinstance(guardado, str) and isinstance(recalculado, str):
        return guardado == recalculado
    return False


def _valores_de_hoja(ws: Any, nombre: str, cuenta: list[int]) -> dict[tuple[int, int], object]:
    celdas: dict[tuple[int, int], object] = {}
    for fila in filas_acotadas(ws, nombre, cuenta, MAX_CELDAS_LIBRO, values_only=False):
        for celda in fila:
            if celda.value is not None:
                celdas[(celda.row, celda.column)] = celda.value
    return celdas


def contar_formulas(datos: bytes, nombre: str = "original.xlsx") -> int:
    """Cuenta cuántas celdas con fórmula tiene el libro `.xlsx`."""
    verificar_archivo(datos, nombre)
    wf = _abrir_solo_lectura(datos, nombre, data_only=False)
    try:
        cuenta = [0]
        total = 0
        for ws in wf.worksheets:
            for fila in filas_acotadas(ws, nombre, cuenta, MAX_CELDAS_LIBRO, values_only=False):
                for celda in fila:
                    if celda.value is not None and _formula_de(celda) is not None:
                        total += 1
        return total
    finally:
        wf.close()


def comparar(
    original: bytes,
    recalculado: bytes,
    tolerancia_relativa: Decimal = TOLERANCIA_RELATIVA,
    tolerancia_absoluta: Decimal = TOLERANCIA_ABSOLUTA,
) -> list[Discrepancia]:
    """Compara las celdas con fórmula de `original` frente a los valores de `recalculado`."""
    verificar_archivo(original, "original.xlsx")
    verificar_archivo(recalculado, "recalculado.xlsx")
    wf_orig = _abrir_solo_lectura(original, "original.xlsx", data_only=False)
    try:
        wv_orig = _abrir_solo_lectura(original, "original.xlsx", data_only=True)
        try:
            wv_rec = _abrir_solo_lectura(recalculado, "recalculado.xlsx", data_only=True)
            try:
                return _comparar_abiertos(
                    wf_orig,
                    wv_orig,
                    wv_rec,
                    tolerancia_relativa=tolerancia_relativa,
                    tolerancia_absoluta=tolerancia_absoluta,
                )
            finally:
                wv_rec.close()
        finally:
            wv_orig.close()
    finally:
        wf_orig.close()


def _comparar_abiertos(
    wf_orig: Any,
    wv_orig: Any,
    wv_rec: Any,
    *,
    tolerancia_relativa: Decimal,
    tolerancia_absoluta: Decimal,
) -> list[Discrepancia]:
    discrepancias: list[Discrepancia] = []
    hojas_orig_v = set(wv_orig.sheetnames)
    hojas_rec_v = set(wv_rec.sheetnames)
    cuenta_f, cuenta_vo, cuenta_vr = [0], [0], [0]
    for ws_f in wf_orig.worksheets:
        titulo = ws_f.title
        guardados = (
            _valores_de_hoja(wv_orig[titulo], "original.xlsx", cuenta_vo)
            if titulo in hojas_orig_v
            else {}
        )
        recalculados = (
            _valores_de_hoja(wv_rec[titulo], "recalculado.xlsx", cuenta_vr)
            if titulo in hojas_rec_v
            else {}
        )
        for fila in filas_acotadas(
            ws_f, "original.xlsx", cuenta_f, MAX_CELDAS_LIBRO, values_only=False
        ):
            for celda in fila:
                if celda.value is None:
                    continue
                formula = _formula_de(celda)
                if formula is None:
                    continue
                pos = (celda.row, celda.column)
                val_guardado = _normalizar_valor(guardados.get(pos))
                val_rec = _normalizar_valor(recalculados.get(pos))
                if not _valores_iguales(
                    val_guardado,
                    val_rec,
                    tolerancia_relativa=tolerancia_relativa,
                    tolerancia_absoluta=tolerancia_absoluta,
                ):
                    discrepancias.append(
                        Discrepancia(
                            hoja=titulo,
                            celda=f"{letra(celda.column - 1)}{celda.row}",
                            formula=formula,
                            guardado=val_guardado,
                            recalculado=val_rec,
                        )
                    )
    return discrepancias


def oraculo(
    datos: bytes,
    nombre: str,
    recalculador: Recalculador,
    *,
    tolerancia_relativa: Decimal = TOLERANCIA_RELATIVA,
    tolerancia_absoluta: Decimal = TOLERANCIA_ABSOLUTA,
) -> list[Discrepancia]:
    """Recalcula `datos` con `recalculador` y devuelve la lista de discrepancias."""
    recalculado = recalculador.recalcular(datos, nombre)
    return comparar(
        datos,
        recalculado,
        tolerancia_relativa=tolerancia_relativa,
        tolerancia_absoluta=tolerancia_absoluta,
    )
