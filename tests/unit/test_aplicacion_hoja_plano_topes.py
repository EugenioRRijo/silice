"""Los topes del lector de planos en `aplicacion.hoja_plano` (T10, ola de decisiones, 3e-2).

Eugenio aprobo la lectura de riesgos de `docs/bitacora/2026-10-20-hoja-3e-avance.md`: el lector no
tenia tope de tamano ni de lecturas a la vez. Medido entonces en este equipo: un DXF de 13,6 MiB
tardaba 26,5 s y 40 lecturas agotaban el grupo de 40 hilos (las rutas sincronas quedaban paradas
entre 17 y 29 minutos); una caida del proceso dejaba el plano del usuario en `%TEMP%`.

Los tres topes (oraculos a mano, escritos aqui; ninguno sale del codigo bajo prueba):

* **Bytes**: un DXF de mas de 8 MiB (11,3 s con 4,4 MiB, 26,5 s con 13,6 MiB: unos 2 s por MiB) y un
  IFC de mas de 20 MiB (el tope de cuerpo de la API) se rechazan ANTES de escribir nada.
* **Lecturas a la vez**: 2 como mucho (la lectura es de CPU de un solo hilo); la tercera recibe un
  aviso de texto fijo sin esperar, y el cupo se devuelve ocurra lo que ocurra.
* **Barrido**: las carpetas `silice_planos_*` huerfanas (de un proceso que cayo) se borran al
  arrancar y de vez en cuando; nunca las de una importacion viva ni lo que no sea una carpeta con
  ese prefijo.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import pytest

from aplicacion import hoja, hoja_borradores, hoja_plano
from tests.fixtures.planos_de_la_hoja import DXF_OF001, dxf_sin_unidad

MIB = 1024 * 1024
HORA = 3600.0


class _Subida:
    """Lo que `leer` usa de una subida: su nombre y sus bytes."""

    def __init__(self, nombre: str, datos: bytes) -> None:
        self.name = nombre
        self._datos = datos

    def getvalue(self) -> bytes:
        return self._datos


@pytest.fixture(autouse=True)
def _entorno(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    carpeta = tmp_path / "planos_temporales"
    carpeta.mkdir()
    monkeypatch.setattr(hoja_plano, "DIRECTORIO_TEMPORAL", str(carpeta))
    monkeypatch.setattr(hoja_plano, "_ultimo_barrido", None)
    hoja_borradores.olvidar_todo()
    yield carpeta
    hoja_borradores.olvidar_todo()


def _vivo(huella: str = "ficha-a"):
    return hoja_borradores.crear(
        huella, "caso-1", "P", None, hoja.Borrador(fecha=date(2026, 1, 1)), None
    )


def _carpetas(planos: Path) -> list[str]:
    return sorted(p.name for p in planos.iterdir())


# --- el tope de bytes ---


def test_los_topes_son_los_de_la_lectura_de_riesgos() -> None:
    assert hoja_plano.BYTES_MAXIMOS_DE_PLANO == {"dxf": 8 * MIB, "ifc": 20 * MIB}
    assert hoja_plano.LECTURAS_SIMULTANEAS == 2


@pytest.mark.parametrize(("nombre", "formato", "tope"), [("a.dxf", "DXF", 8), ("A.IFC", "IFC", 20)])
def test_un_plano_de_un_byte_mas_que_el_tope_se_rechaza_antes_de_escribir_nada(
    nombre, formato, tope, _entorno
) -> None:
    vivo = _vivo()
    with pytest.raises(hoja_plano.PlanoDemasiadoGrande) as error:
        hoja_plano.leer(vivo, 0, _Subida(nombre, b"0" * (tope * MIB + 1)))
    assert error.value.mensaje == (
        f"El plano {formato} pesa más de {tope} MiB, el máximo que Sílice lee en un tiempo "
        "razonable. Purgue las capas y bloques que no use, o divida el dibujo por plantas, y "
        "vuelva a subirlo."
    )
    assert _carpetas(_entorno) == []  # ni siquiera se creo la carpeta
    assert hoja_plano.IMPORTACIONES.vigente(vivo) is None


def test_un_plano_de_exactamente_el_tope_se_lee(monkeypatch, _entorno) -> None:
    monkeypatch.setattr(hoja_plano, "BYTES_MAXIMOS_DE_PLANO", {"dxf": 100, "ifc": 100})
    vivo = _vivo()
    resultado = hoja_plano.leer(
        vivo, 0, _Subida("a.dxf", b"x" * 100)
    )  # basura: rechazada, no error
    assert resultado.estado.name == "RECHAZADA"
    with pytest.raises(hoja_plano.PlanoDemasiadoGrande):
        hoja_plano.leer(vivo, 0, _Subida("a.dxf", b"x" * 101))
    assert len(_carpetas(_entorno)) == 1  # la de la importacion vigente, no la del rechazo


class _SubidaMedible:
    """Una subida que sabe su tamano sin cargarlo: leer sus bytes revienta la prueba."""

    def __init__(self, nombre: str, tamano: int) -> None:
        self.name = nombre
        self._tamano = tamano

    def tamano(self) -> int:
        return self._tamano

    def getvalue(self) -> bytes:
        raise AssertionError("el tope se mide sin cargar los bytes en memoria")


def test_el_tope_se_mide_sin_cargar_los_bytes_cuando_la_subida_sabe_su_tamano(_entorno) -> None:
    vivo = _vivo()
    with pytest.raises(hoja_plano.PlanoDemasiadoGrande):
        hoja_plano.leer(vivo, 0, _SubidaMedible("a.dxf", 8 * MIB + 1))
    assert _carpetas(_entorno) == []


def test_el_orden_de_errores_se_mantiene_con_una_subida_medible() -> None:
    vivo = _vivo()
    with pytest.raises(hoja_borradores.RevDesactualizado):
        hoja_plano.leer(vivo, 7, _SubidaMedible("a.dxf", 21 * MIB))
    with pytest.raises(ValueError, match="no es un plano"):
        hoja_plano.leer(vivo, 0, _SubidaMedible("a.txt", 21 * MIB))


def test_el_rev_y_el_formato_se_juzgan_antes_que_el_tamano() -> None:
    vivo = _vivo()
    grande = b"0" * (21 * MIB)
    with pytest.raises(hoja_borradores.RevDesactualizado):
        hoja_plano.leer(vivo, 7, _Subida("a.dxf", grande))
    with pytest.raises(ValueError, match="no es un plano"):
        hoja_plano.leer(vivo, 0, _Subida("a.txt", grande))


# --- el tope de lecturas a la vez ---


def test_la_lectura_de_mas_no_espera_y_el_cupo_vuelve_al_terminar(monkeypatch, _entorno) -> None:
    monkeypatch.setattr(hoja_plano, "_CUPOS", threading.BoundedSemaphore(1))
    dentro, soltar = threading.Event(), threading.Event()
    real = hoja_plano.hoja.subir_plano

    def lenta(subida, carpeta, **kwargs):
        dentro.set()
        assert soltar.wait(timeout=60)
        return real(subida, carpeta, **kwargs)

    monkeypatch.setattr(hoja_plano.hoja, "subir_plano", lenta)
    primero, segundo = _vivo("ficha-a"), _vivo("ficha-b")
    datos = DXF_OF001.read_bytes()
    hilo = threading.Thread(target=lambda: hoja_plano.leer(primero, 0, _Subida("a.dxf", datos)))
    hilo.start()
    assert dentro.wait(timeout=60)

    inicio = time.perf_counter()
    with pytest.raises(hoja_plano.LecturasOcupadas):
        hoja_plano.leer(segundo, 0, _Subida("b.dxf", datos))
    assert time.perf_counter() - inicio < 1  # no se queda esperando
    assert len(_carpetas(_entorno)) == 1  # solo la de la lectura en curso
    assert hoja_plano.IMPORTACIONES.vigente(segundo) is None

    soltar.set()
    hilo.join(timeout=120)
    assert not hilo.is_alive()
    monkeypatch.setattr(hoja_plano.hoja, "subir_plano", real)
    assert hoja_plano.leer(segundo, 0, _Subida("b.dxf", datos)).estado.name == "IMPORTADA"


def test_si_el_lector_revienta_el_cupo_vuelve_y_no_queda_carpeta(monkeypatch, _entorno) -> None:
    monkeypatch.setattr(hoja_plano, "_CUPOS", threading.BoundedSemaphore(1))
    real = hoja_plano.hoja.subir_plano

    def revienta(*_args, **_kwargs):
        raise RuntimeError("fallo inesperado del lector")

    monkeypatch.setattr(hoja_plano.hoja, "subir_plano", revienta)
    vivo = _vivo()
    datos = DXF_OF001.read_bytes()
    with pytest.raises(RuntimeError):
        hoja_plano.leer(vivo, 0, _Subida("a.dxf", datos))
    assert _carpetas(_entorno) == []
    monkeypatch.setattr(hoja_plano.hoja, "subir_plano", real)
    assert hoja_plano.leer(vivo, 0, _Subida("a.dxf", datos)).estado.name == "IMPORTADA"


def test_reanudar_con_la_unidad_tambien_usa_un_cupo(monkeypatch, tmp_path) -> None:
    vivo = _vivo()
    sin_unidad = dxf_sin_unidad(tmp_path / "sin_unidad.dxf").read_bytes()
    assert hoja_plano.leer(vivo, 0, _Subida("a.dxf", sin_unidad)).pide_unidad
    cupos = threading.BoundedSemaphore(1)
    monkeypatch.setattr(hoja_plano, "_CUPOS", cupos)
    assert cupos.acquire(blocking=False)  # otra lectura en curso
    with pytest.raises(hoja_plano.LecturasOcupadas):
        hoja_plano.reanudar(vivo, 0, "m")
    assert hoja_plano.IMPORTACIONES.vigente(vivo).resultado.pide_unidad  # nada cambio
    cupos.release()
    assert not hoja_plano.reanudar(vivo, 0, "m").pide_unidad
    assert cupos.acquire(blocking=False)  # y el cupo volvio


# --- el barrido de las carpetas huerfanas ---


def _vieja(planos: Path, nombre: str, antiguedad_horas: float) -> Path:
    carpeta = planos / nombre
    carpeta.mkdir()
    (carpeta / "plano.dxf").write_bytes(b"0")
    antes = time.time() - antiguedad_horas * HORA
    os.utime(carpeta, (antes, antes))
    return carpeta


def test_el_barrido_borra_solo_las_huerfanas_con_el_prefijo_y_mas_viejas_que_el_plazo(
    _entorno,
) -> None:
    vieja = _vieja(_entorno, "silice_planos_vieja", 10)
    reciente = _vieja(_entorno, "silice_planos_reciente", 0.5)
    ajena = _vieja(_entorno, "otra_cosa_vieja", 10)
    suelto = _entorno / "silice_planos_archivo"
    suelto.write_bytes(b"0")
    antes = time.time() - 10 * HORA
    os.utime(suelto, (antes, antes))

    borradas = hoja_plano.barrer_huerfanas(timedelta(hours=8))

    assert borradas == 1
    assert not vieja.exists()
    assert reciente.exists() and ajena.exists() and suelto.exists()


def _enlazar(enlace: Path, destino: Path) -> None:
    """Un enlace de verdad: junction en Windows (no pide privilegios) y simbolico en el resto."""
    if os.name == "nt":
        hecho = subprocess.run(  # noqa: S603
            ["cmd", "/c", "mklink", "/J", str(enlace), str(destino)],  # noqa: S607
            capture_output=True,
            check=False,
        )
        assert hecho.returncode == 0, hecho.stdout
    else:
        enlace.symlink_to(destino, target_is_directory=True)


def test_el_barrido_no_sigue_ni_borra_un_enlace_a_una_victima(
    monkeypatch, _entorno, tmp_path
) -> None:
    intentos: list[Path] = []
    monkeypatch.setattr(hoja_plano, "_borrar", intentos.append)
    victima = tmp_path / "victima"
    victima.mkdir()
    (victima / "importante.txt").write_text("no me borres")
    enlace = _entorno / "silice_planos_enlace"
    _enlazar(enlace, victima)
    try:
        antes = time.time() - 30 * HORA
        os.utime(victima, (antes, antes))  # el enlace "parece" viejo por su destino

        borradas = hoja_plano.barrer_huerfanas(timedelta(0))

        assert borradas == 0
        assert intentos == []  # ni siquiera se intento borrarlo (rmtree falla en silencio)
        assert (victima / "importante.txt").read_text() == "no me borres"
    finally:
        os.rmdir(enlace) if os.name == "nt" else enlace.unlink()  # solo el enlace, no el destino


def test_el_barrido_salta_lo_que_el_sistema_dice_que_es_un_enlace(
    monkeypatch, _entorno, tmp_path
) -> None:
    """El enlace simbolico no se puede crear sin privilegios en Windows: se simula con la
    pregunta que hace el barrido (`is_symlink`) sobre una carpeta que tiene el prefijo."""
    victima = _vieja(_entorno, "silice_planos_victima", 30)
    intentos: list[Path] = []
    monkeypatch.setattr(hoja_plano, "_borrar", intentos.append)
    monkeypatch.setattr(Path, "is_symlink", lambda self: self.name == victima.name)

    assert hoja_plano.barrer_huerfanas(timedelta(0)) == 0
    assert intentos == [] and (victima / "plano.dxf").exists()


def test_el_barrido_no_toca_la_carpeta_de_una_importacion_viva_aunque_sea_vieja(_entorno) -> None:
    vivo = _vivo()
    hoja_plano.leer(vivo, 0, _Subida("a.dxf", DXF_OF001.read_bytes()))
    (viva,) = list(_entorno.iterdir())
    antes = time.time() - 30 * HORA
    os.utime(viva, (antes, antes))
    huerfana = _vieja(_entorno, "silice_planos_huerfana", 30)

    assert hoja_plano.barrer_huerfanas(timedelta(hours=8)) == 1

    assert viva.exists() and (viva / "a.dxf").exists()
    assert not huerfana.exists()


def test_el_barrido_con_plazo_cero_borra_todas_las_huerfanas_y_tolera_el_directorio_ausente(
    _entorno,
) -> None:
    _vieja(_entorno, "silice_planos_a", 0.01)
    _vieja(_entorno, "silice_planos_b", 0.0)
    assert hoja_plano.barrer_huerfanas(timedelta(0)) == 2
    assert _carpetas(_entorno) == []
    _entorno.rmdir()
    assert hoja_plano.barrer_huerfanas(timedelta(0)) == 0  # sin directorio: no falla


def test_al_arrancar_se_barre_con_un_plazo_de_una_hora_y_se_marca_el_barrido(_entorno) -> None:
    vieja = _vieja(_entorno, "silice_planos_caida", 2)
    reciente = _vieja(_entorno, "silice_planos_de_otro_proceso", 0.2)
    assert hoja_plano.barrer_al_arrancar() == 1
    assert not vieja.exists() and reciente.exists()
    assert hoja_plano._ultimo_barrido is not None


def test_leer_barre_de_vez_en_cuando_pero_solo_despues_de_arrancar(monkeypatch, _entorno) -> None:
    vieja = _vieja(_entorno, "silice_planos_caida", 10)
    datos = DXF_OF001.read_bytes()
    hoja_plano.leer(_vivo("ficha-a"), 0, _Subida("a.dxf", datos))
    assert vieja.exists()  # sin arranque no se barre nada (las pruebas no tocan el %TEMP% real)

    hoja_plano.barrer_al_arrancar()  # el barrido de arranque ya borra la de mas de una hora
    assert not vieja.exists()
    otra = _vieja(_entorno, "silice_planos_otra", 10)
    hoja_plano.leer(_vivo("ficha-b"), 0, _Subida("b.dxf", datos))
    assert otra.exists()  # aun no toca (el intervalo no ha pasado)

    monkeypatch.setattr(hoja_plano, "_ultimo_barrido", time.monotonic() - 16 * 60)
    hoja_plano.leer(_vivo("ficha-c"), 0, _Subida("c.dxf", datos))
    assert not otra.exists()  # pasaron mas de 15 minutos: barre con el plazo de los borradores
    assert len(_carpetas(_entorno)) == 3  # las tres importaciones vivas siguen
