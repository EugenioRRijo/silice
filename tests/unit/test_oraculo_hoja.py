"""Oráculo independiente de hojas de cálculo (Fase 1, auditoría no circular)."""

from __future__ import annotations

import io
import shutil
import subprocess
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import openpyxl
import pytest

from aplicacion import oraculo_hoja as oh
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    MEMORIA,
    Siembra,
    construir_libro,
    libro_limpio,
)


class RecalculadorFalso:
    """Construye con openpyxl un `.xlsx` recalculado cambiando valores a mano."""

    def __init__(self, cambios: Mapping[str, object] | None = None) -> None:
        self._cambios = dict(cambios or {})

    def recalcular(self, datos: bytes, nombre: str) -> bytes:
        origen = openpyxl.load_workbook(
            io.BytesIO(datos), read_only=True, data_only=True, keep_links=False
        )
        nuevo = openpyxl.Workbook()
        nuevo.remove(nuevo.active)
        try:
            for ws_orig in origen.worksheets:
                ws_nueva = nuevo.create_sheet(ws_orig.title)
                for indice_fila, fila in enumerate(ws_orig.iter_rows(values_only=True), start=1):
                    for indice_col, valor in enumerate(fila, start=1):
                        if valor is not None:
                            ws_nueva.cell(row=indice_fila, column=indice_col, value=valor)
        finally:
            origen.close()
        for clave_celda, nuevo_valor in self._cambios.items():
            hoja, coord = clave_celda.split("!", 1)
            ws = nuevo[hoja] if hoja in nuevo.sheetnames else nuevo.create_sheet(hoja)
            ws[coord] = nuevo_valor
        salida = io.BytesIO()
        nuevo.save(salida)
        nuevo.close()
        return salida.getvalue()


def _libro_simple(celdas: Mapping[str, tuple[object, str | None]]) -> bytes:
    """Crea un `.xlsx` mínimo con fórmulas y valores opcionales usando openpyxl."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hoja"
    for coord, (valor, formula) in celdas.items():
        ws[coord] = formula if formula is not None else valor
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def test_recalculador_falso_cumple_el_protocolo() -> None:
    assert isinstance(RecalculadorFalso(), oh.Recalculador)


def test_sin_cambios_devuelve_lista_vacia() -> None:
    construido = libro_limpio()
    assert oh.oraculo(construido.datos, "limpio.xlsx", RecalculadorFalso()) == []


def test_numero_fuera_de_tolerancia_da_una_discrepancia_con_hoja_celda_y_formula() -> None:
    construido = libro_limpio()
    fila_p1 = construido.filas_partida["APU-01"]
    fila_pu = construido.filas_apu["APU-01"].pu
    celda = f"P{fila_p1}"
    falso = RecalculadorFalso({f"PRESUPUESTO!{celda}": Decimal("20")})
    discrepancias = oh.oraculo(construido.datos, "libro.xlsx", falso)
    assert discrepancias == [
        oh.Discrepancia(
            hoja="PRESUPUESTO",
            celda=celda,
            formula=f'=INDIRECT("\'APU-"&TEXT($B{fila_p1},"00")&"\'!G{fila_pu}")',
            guardado=MEMORIA["componentes"]["APU-01"]["PU"],
            recalculado=Decimal("20"),
        )
    ]


def test_diferencia_dentro_de_tolerancia_no_produce_discrepancia() -> None:
    construido = libro_limpio()
    fila_p1 = construido.filas_partida["APU-01"]
    pu_base = MEMORIA["componentes"]["APU-01"]["PU"]
    # Diferencia de 0,003275 <= tolerancia_absoluta (0,005).
    falso_abs = RecalculadorFalso({f"PRESUPUESTO!P{fila_p1}": Decimal("14.49")})
    assert oh.oraculo(construido.datos, "libro.xlsx", falso_abs) == []
    assert abs(pu_base - Decimal("14.49")) < Decimal("0.005")
    # Tolerancia relativa (1e-9) sobre una cifra grande cuando la absoluta supera 0,005.
    grande = construir_libro(
        APUS_LIMPIOS,
        Siembra(parches={"MEDICIONES!D4": (Decimal("10000000"), "=B4*C4")}),
    )
    cerca = RecalculadorFalso({"MEDICIONES!D4": Decimal("10000000.008")})
    lejos = RecalculadorFalso({"MEDICIONES!D4": Decimal("10000000.05")})
    assert oh.oraculo(grande.datos, "grande.xlsx", cerca) == []
    assert len(oh.oraculo(grande.datos, "grande.xlsx", lejos)) == 1


def test_celdas_sin_formula_se_ignoran() -> None:
    construido = libro_limpio()
    falso = RecalculadorFalso(
        {
            "INSUMOS!E5": Decimal("999"),
            "PRESUPUESTO!G5": Decimal("777"),
            "PORTADA!B4": "Otro cliente",
        }
    )
    assert oh.oraculo(construido.datos, "libro.xlsx", falso) == []


def test_error_ref_frente_a_numero_es_discrepancia() -> None:
    con_ref = construir_libro(APUS_LIMPIOS, Siembra(resumen_ref_rota=True))
    assert oh.oraculo(con_ref.datos, "ref.xlsx", RecalculadorFalso()) == []
    falso_num = RecalculadorFalso({"RESUMEN!B13": Decimal("125")})
    assert oh.oraculo(con_ref.datos, "ref.xlsx", falso_num) == [
        oh.Discrepancia(
            hoja="RESUMEN",
            celda="B13",
            formula="=PRESUPUESTO!#REF!",
            guardado="#REF!",
            recalculado=Decimal("125"),
        )
    ]
    falso_otro_err = RecalculadorFalso({"RESUMEN!B13": "#DIV/0!"})
    assert oh.oraculo(con_ref.datos, "ref.xlsx", falso_otro_err) == [
        oh.Discrepancia(
            hoja="RESUMEN",
            celda="B13",
            formula="=PRESUPUESTO!#REF!",
            guardado="#REF!",
            recalculado="#DIV/0!",
        )
    ]


def test_guardado_vacio_y_recalculado_no_vacio_es_discrepancia() -> None:
    original = _libro_simple({"A1": (None, "=2+3"), "A2": (10, None)})
    falso = RecalculadorFalso({"Hoja!A1": Decimal("5")})
    assert oh.oraculo(original, "vacio.xlsx", falso) == [
        oh.Discrepancia(
            hoja="Hoja",
            celda="A1",
            formula="=2+3",
            guardado=None,
            recalculado=Decimal("5"),
        )
    ]


def test_recalculador_libreoffice_sin_ejecutable_pide_instalarlo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vacia = tmp_path / "vacia"
    vacia.mkdir()
    monkeypatch.setattr(shutil, "which", lambda *_args, **_kwargs: None)
    for variable in ("PATH", "ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        monkeypatch.setenv(variable, str(vacia))
    recalculador = oh.RecalculadorLibreOffice()
    with pytest.raises(FileNotFoundError, match="Instale LibreOffice"):
        recalculador.version()


def test_recalculador_libreoffice_usa_perfil_temporal_y_recalculo_forzado(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    falso_soffice = tmp_path / "soffice.exe"
    falso_soffice.write_bytes(b"falso")
    original = _libro_simple({"A1": (None, "=1+1")})
    capturas: dict[str, object] = {}

    def _falso_run(
        orden: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if "--version" in orden:
            return subprocess.CompletedProcess(orden, 0, "LibreOffice 24.8.3.2\n", "")
        arg_env = next(a for a in orden if a.startswith("-env:UserInstallation=file:///"))
        uri = arg_env.split("=", 1)[1]
        perfil = Path(url2pathname(urlparse(uri).path))
        xcu = (perfil / "user" / "registrymodifications.xcu").read_text(encoding="utf-8")
        capturas["xcu"] = xcu
        capturas["headless"] = "--headless" in orden and "--convert-to" in orden
        idx = orden.index("--outdir")
        carpeta_salida = Path(orden[idx + 1])
        entrada = Path(orden[-1])
        (carpeta_salida / entrada.name).write_bytes(
            RecalculadorFalso({"Hoja!A1": Decimal("2")}).recalcular(original, "libro.xlsx")
        )
        return subprocess.CompletedProcess(orden, 0, "convertido\n", "")

    class _FalsoPopen:
        def __init__(self, orden: list[str], **kwargs: object) -> None:
            self.returncode = 0
            self.pid = 1
            _falso_run(orden)

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            capturas["timeout"] = timeout
            return "convertido\n", ""

        def poll(self) -> int:
            return 0

    monkeypatch.setattr(subprocess, "run", _falso_run)
    monkeypatch.setattr(subprocess, "Popen", _FalsoPopen)
    recalculador = oh.RecalculadorLibreOffice(ejecutable=falso_soffice)
    assert recalculador.version() == "LibreOffice 24.8.3.2"
    discrepancias = oh.oraculo(original, "libro.xlsx", recalculador)
    assert len(discrepancias) == 1 and discrepancias[0].recalculado == Decimal("2")
    xcu_texto = str(capturas["xcu"])
    assert "/org.openoffice.Office.Calc/Formula/Load" in xcu_texto
    assert "OOXMLRecalcMode" in xcu_texto and "<value>0</value>" in xcu_texto
    assert capturas["timeout"] == 120
    assert capturas["headless"] is True


class _ProcesoLento:
    """Doble de `subprocess.Popen` que nunca termina: `communicate` lanza `excepcion`."""

    instancias: list[_ProcesoLento] = []  # noqa: RUF012 - registro del doble de prueba
    excepcion: type[BaseException] = subprocess.TimeoutExpired

    def __init__(self, orden: list[str], **kwargs: object) -> None:
        self.pid = 4242
        self.returncode = None
        self.kwargs = kwargs
        idx = orden.index("--outdir")
        # La conversión alcanzó a escribir una salida parcial antes de colgarse.
        (Path(orden[idx + 1]) / Path(orden[-1]).name).write_bytes(b"parcial")
        type(self).instancias.append(self)

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        if self.excepcion is subprocess.TimeoutExpired:
            raise subprocess.TimeoutExpired("soffice", timeout or 0)
        raise self.excepcion

    def poll(self) -> None:
        return None


class _ColgadoEnWindows:
    """Escenario de Windows: el hijo retiene el archivo de entrada y de salida."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, excepcion: type) -> None:
        self.base = tmp_path / "base_temporal"
        self.terminados: list[object] = []
        self.arbol_terminado = False
        self.borrados_antes_de_matar: list[str] = []
        self.retenido_siempre = False
        base = self.base
        escenario = self

        class _CarpetaQueNoSeLimpia:
            def __init__(self, **kwargs: object) -> None:
                base.mkdir()

            def __enter__(self) -> str:
                return str(base)

            def __exit__(self, *_exc: object) -> None:
                return None

        def _terminar(proceso: object) -> None:
            escenario.terminados.append(proceso)
            escenario.arbol_terminado = True

        unlink_original = Path.unlink

        def _unlink(ruta: Path, *args: object, **kwargs: object) -> None:
            if ruta.name == "libro.xlsx" and not escenario.arbol_terminado:
                escenario.borrados_antes_de_matar.append(str(ruta))
                raise PermissionError("retenido por el hijo")
            if ruta.name == "libro.xlsx" and escenario.retenido_siempre:
                raise PermissionError("retenido para siempre")
            unlink_original(ruta, *args, **kwargs)

        _ProcesoLento.instancias = []
        _ProcesoLento.excepcion = excepcion
        falso_soffice = tmp_path / "soffice.exe"
        falso_soffice.write_bytes(b"falso")
        monkeypatch.setattr(oh.tempfile, "TemporaryDirectory", _CarpetaQueNoSeLimpia)
        monkeypatch.setattr(oh.subprocess, "Popen", _ProcesoLento)
        monkeypatch.setattr(oh, "_terminar_arbol", _terminar, raising=False)
        monkeypatch.setattr(Path, "unlink", _unlink)
        self.recalculador = oh.RecalculadorLibreOffice(ejecutable=falso_soffice, tiempo_maximo=1)

    def recalcular(self) -> None:
        self.recalculador.recalcular(_libro_simple({"A1": (None, "=1+1")}), "libro.xlsx")

    def quedan_copias(self) -> bool:
        return (self.base / "entrada" / "libro.xlsx").exists() or (
            self.base / "salida" / "libro.xlsx"
        ).exists()


def test_tiempo_agotado_termina_el_arbol_antes_de_borrar_entrada_y_salida(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    escenario = _ColgadoEnWindows(tmp_path, monkeypatch, subprocess.TimeoutExpired)

    with pytest.raises(oh.OraculoError, match="tiempo máximo"):
        escenario.recalcular()

    assert escenario.terminados == _ProcesoLento.instancias and len(escenario.terminados) == 1
    assert escenario.borrados_antes_de_matar == []
    assert not escenario.quedan_copias()


def test_interrupcion_termina_el_arbol_antes_de_borrar_la_copia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    escenario = _ColgadoEnWindows(tmp_path, monkeypatch, KeyboardInterrupt)

    with pytest.raises(KeyboardInterrupt):
        escenario.recalcular()

    assert len(escenario.terminados) == 1
    assert escenario.borrados_antes_de_matar == []
    assert not escenario.quedan_copias()


def test_avisa_por_stderr_si_la_copia_no_se_pudo_borrar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    escenario = _ColgadoEnWindows(tmp_path, monkeypatch, subprocess.TimeoutExpired)
    escenario.retenido_siempre = True  # ni siquiera tras matar el árbol se puede borrar

    with pytest.raises(oh.OraculoError):
        escenario.recalcular()

    assert escenario.quedan_copias()
    err = capsys.readouterr().err
    assert "No se pudo borrar" in err and "libro.xlsx" in err


def test_en_posix_el_proceso_nace_en_su_propio_grupo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    escenario = _ColgadoEnWindows(tmp_path, monkeypatch, subprocess.TimeoutExpired)
    monkeypatch.setattr(oh, "_ES_WINDOWS", False, raising=False)

    with pytest.raises(oh.OraculoError):
        escenario.recalcular()

    assert _ProcesoLento.instancias[0].kwargs.get("start_new_session") is True


class _ProcesoRegistro:
    pid = 4242

    def __init__(self) -> None:
        self.killed = False
        self.esperado = False

    def kill(self) -> None:
        self.killed = True

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        self.esperado = True
        return "", ""


def test_terminar_arbol_en_windows_usa_taskkill_sobre_el_arbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordenes: list[list[str]] = []

    def _run(orden: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        ordenes.append(orden)
        return subprocess.CompletedProcess(orden, 0, "", "")

    monkeypatch.setattr(oh, "_ES_WINDOWS", True, raising=False)
    monkeypatch.setattr(oh.subprocess, "run", _run)
    proceso = _ProcesoRegistro()
    oh._terminar_arbol(proceso)  # type: ignore[arg-type]
    assert ordenes == [["taskkill", "/F", "/T", "/PID", "4242"]]
    assert proceso.killed and proceso.esperado


def test_terminar_arbol_fuera_de_windows_solo_mata_el_proceso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _run(orden: list[str], **kwargs: object) -> None:
        raise AssertionError("no debe invocar taskkill fuera de Windows")

    grupos: list[tuple[int, int]] = []
    monkeypatch.setattr(oh, "_ES_WINDOWS", False, raising=False)
    monkeypatch.setattr(oh.subprocess, "run", _run)
    monkeypatch.setattr(oh.os, "getpgid", lambda pid: pid + 1, raising=False)
    monkeypatch.setattr(oh.os, "killpg", lambda g, sig: grupos.append((g, sig)), raising=False)
    proceso = _ProcesoRegistro()
    oh._terminar_arbol(proceso)  # type: ignore[arg-type]
    assert grupos == [(4243, 9)]  # se mata el grupo entero, no solo el lanzador
    assert proceso.killed and proceso.esperado
