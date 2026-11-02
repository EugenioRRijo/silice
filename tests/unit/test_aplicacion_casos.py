"""Carpetas de trabajo sin FastAPI (BCP-2; diseño §4.2 a §4.6, §16 9.1 y 9.2; B11, B13 a B18, S5,
S6 y S9).

Oráculos escritos a mano: los mensajes se copian del diseño (§9) con sus tildes; las reglas de
nombre, del de `operacion/base_datos.py` (la clásica); los conteos del estado salen de la ficha de
la base de prueba (`tests/fixtures/bases/v1_0_0/ficha.json`) o se leen con `sqlite3` directo; el
árbol de la carpeta de datos se compara con `os.walk` antes y después. Ninguna prueba abre la red ni
usa datos reales.
"""

from __future__ import annotations

import io
import os
import sqlite3
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pytest

from aplicacion import casos
from operacion import __main__ as cli
from operacion import base_datos, config, demostracion, respaldo
from operacion.base_datos import (
    CasoYaExiste,
    Destino,
    RutaDeCasoRechazada,
    listar_casos,
    revision_head,
)
from tests.fixtures import bases_prueba
from tests.fixtures.carpetas_trabajo import HOSTILES, arbol, base_minima, copiar

MENSAJE_TOPE = "Ya hay 100 carpetas de trabajo: retire alguna antes de crear otra."
MENSAJE_EN_CURSO = "Hay otra creación de carpeta en curso: espere unos segundos y repita."
MENSAJE_RESERVADO = "Ese nombre está reservado para la demostración."
MENSAJE_GRANDE = "El archivo pasa de 20 MiB."
MENSAJE_NO_VALIDO = "El archivo no es una carpeta de trabajo de Sílice válida: no se guardó."
MENSAJE_DEMOSTRACION = (
    "No se pudo preparar la demostración. Pruebe de nuevo; si sigue, avise al administrador."
)
AVISO_MIGRADA = "Se actualizó el archivo a la versión actual de Sílice; quedó un respaldo previo."
#: Las tablas que toda base de un caso de Sílice tiene desde la 0.5.0 (`ficha.json` de v0_5_0).
NUCLEO = ("composicion_apu", "insumo", "lista_precios", "partida", "precio_insumo", "presupuesto")


@pytest.fixture(scope="module")
def plantillas(tmp_path_factory) -> dict[str, Path]:
    """Una base vacía en `head` y la `demo.db` de la 1.0.0 llevada a `head`, una vez por módulo.
    Migrar respalda: la carpeta de datos de la fixture es la suya, nunca `data/`."""
    carpeta = tmp_path_factory.mktemp("plantillas_carpetas")
    with pytest.MonkeyPatch.context() as parche:
        parche.setenv("SILICE_DATOS", str(carpeta / "datos"))
        parche.setenv("SILICE_USUARIO", str(carpeta / "datos"))
        demo = bases_prueba.copiar_base("1.0.0", "demo.db", carpeta / "demo_head.db")
        base_datos.preparar_base(demo)
        minima = base_minima(carpeta / "minima.db")
    return {"minima": minima, "demo": demo}


@pytest.fixture
def datos() -> Iterator[Path]:
    carpeta = config.carpeta_datos()
    carpeta.mkdir(parents=True, exist_ok=True)
    yield carpeta


def _abre(ruta: Path) -> sqlite3.Connection:
    return closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True))


def _revision(ruta: Path) -> str:
    with _abre(ruta) as conexion:
        return conexion.execute("SELECT version_num FROM alembic_version").fetchone()[0]


def _nombres() -> list[str]:
    return [ruta.name for ruta in listar_casos()]


# --- crear (B11, S5, §16 9.2) -----------------------------------------------------------------


def test_crear_deja_un_caso_en_head_con_el_nombre_saneado(datos: Path) -> None:
    ruta = casos.crear("Obra*1")
    assert ruta == config.carpeta_casos().resolve() / "Obra_1.db"
    assert _nombres() == ["Obra_1.db"]
    assert _revision(ruta) == revision_head(Destino.CASO)
    assert not (datos / casos.CARPETA_CUARENTENA).exists()  # la cuarentena no queda


def test_crear_conserva_tildes_y_enes(datos: Path) -> None:
    assert casos.crear("  Ñandú de prueba ").name == "Ñandú de prueba.db"


@pytest.mark.parametrize("repetido", ["Obra", "OBRA", "obra.DB", "  obra  "])
def test_un_nombre_repetido_sin_distinguir_mayusculas_es_caso_ya_existe(
    datos: Path, repetido: str
) -> None:
    casos.crear("Obra")
    antes = arbol(datos)
    with pytest.raises(CasoYaExiste) as error:
        casos.crear(repetido)
    assert str(error.value) == (
        "Ya existe la carpeta de trabajo Obra.db: ábrala de la lista o elija otro nombre."
    )
    assert isinstance(error.value, RutaDeCasoRechazada)  # la subclase: 409 y no 422
    assert arbol(datos) == antes


@pytest.mark.parametrize(
    "reservado", ["demostracion", "DEMOSTRACION", "Demostracion.db", "demostración"]
)
def test_el_nombre_de_la_demostracion_esta_reservado(datos: Path, reservado: str) -> None:
    with pytest.raises(RutaDeCasoRechazada, match=f"^{MENSAJE_RESERVADO}$"):
        casos.crear(reservado)
    assert arbol(datos) == {}


#: S5: cada nombre hostil o crea dentro de `casos/` o se rechaza antes de tocar el disco.
HOSTILES_DE_NOMBRE = [
    "..\\x",
    "../x",
    "a/b",
    "a\\b",
    "C:\\x",
    "\\\\srv\\share\\x",
    "//srv/x",
    "con",
    "NUL.db",
    "COM1",
    "COM¹",
    "lpt³.db",
    "x:y",
    "x.db::$DATA",
    "   ",
    "....",
    ".",
    "x.",
    "n" * 500,
    "Ñandú",
    "x<y>",
    "%2e%2e/x",
    "%2e%2e",
]


@pytest.mark.parametrize("nombre", HOSTILES_DE_NOMBRE)
def test_ningun_nombre_hostil_sale_de_la_carpeta_de_casos(datos: Path, nombre: str) -> None:
    afuera = datos.parent

    def _fuera(vista: dict[str, int]) -> dict[str, int]:
        return {k: v for k, v in vista.items() if k.split("/")[0] != datos.name}

    antes = _fuera(arbol(afuera))
    try:
        ruta = casos.crear(nombre)
    except RutaDeCasoRechazada:
        assert _nombres() == []
    else:
        assert ruta.resolve().is_relative_to(config.carpeta_casos().resolve())
        assert ruta.parent == config.carpeta_casos().resolve()
        assert len(ruta.stem) <= 80
    assert _fuera(arbol(afuera)) == antes
    for archivo in config.carpeta_datos().rglob("*"):
        assert archivo.resolve().is_relative_to(config.carpeta_datos().resolve())


@pytest.mark.parametrize("nombre", ["..\\x", "../x", "C:\\x", "con", "COM¹", "x:y", "   "])
def test_los_nombres_de_forma_invalida_se_rechazan(datos: Path, nombre: str) -> None:
    with pytest.raises(RutaDeCasoRechazada):
        casos.crear(nombre)
    assert arbol(datos) == {}


def test_al_llegar_a_100_carpetas_no_se_crea_otra(datos: Path) -> None:
    carpeta = config.carpeta_casos()
    carpeta.mkdir(parents=True)
    for numero in range(100):
        (carpeta / f"c{numero:03}.db").write_bytes(b"")
    with pytest.raises(casos.TopeDeCarpetas, match=f"^{MENSAJE_TOPE}$"):
        casos.crear("una mas")
    assert len(_nombres()) == 100
    (carpeta / "c000.db").unlink()
    assert casos.crear("una mas").name == "una mas.db"


def test_dos_creaciones_simultaneas_del_mismo_nombre_dejan_una_sola(datos: Path) -> None:
    barrera = threading.Barrier(2)
    resultados: list[object] = []

    def crear() -> None:
        barrera.wait()
        try:
            resultados.append(casos.crear("Gemela"))
        except (CasoYaExiste, casos.CreacionEnCurso) as error:
            resultados.append(error)

    hilos = [threading.Thread(target=crear) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert sorted(type(r).__name__ for r in resultados)[0] in {"CasoYaExiste", "CreacionEnCurso"}
    assert sum(isinstance(r, Path) for r in resultados) == 1
    assert _nombres() == ["Gemela.db"]


def test_una_creacion_en_curso_hace_esperar_y_luego_rechaza(
    datos: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dentro, soltar = threading.Event(), threading.Event()
    original = casos.preparar_base

    def lenta(ruta: Path, *args, **kwargs):
        dentro.set()
        soltar.wait(10)
        return original(ruta, *args, **kwargs)

    monkeypatch.setattr(casos, "preparar_base", lenta)
    monkeypatch.setattr(casos, "PLAZO_CERROJO_S", 0.1)
    hilo = threading.Thread(target=casos.crear, args=("Primera",))
    hilo.start()
    try:
        assert dentro.wait(10)
        with pytest.raises(casos.CreacionEnCurso, match=f"^{MENSAJE_EN_CURSO}$"):
            casos.crear("Segunda")
    finally:
        soltar.set()
        hilo.join()
    assert _nombres() == ["Primera.db"]


def test_un_fallo_al_preparar_no_deja_nada(datos: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """S9: el fallo de `preparar_base` tras crear el archivo en la cuarentena no deja rastro."""

    def falla(ruta: Path, *args, **kwargs):
        ruta.write_bytes(b"a medias")
        raise base_datos.MigracionFallida(f"no se pudo crear {ruta}")

    monkeypatch.setattr(casos, "preparar_base", falla)
    with pytest.raises(casos.PreparacionFallida) as error:
        casos.crear("Rota")
    assert str(datos) not in str(error.value) and "Rota" not in str(error.value)
    assert arbol(datos) == {}


def test_un_fallo_al_publicar_no_deja_temporales(
    datos: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S9: un `os.rename` que falla no deja `.subiendo-*.tmp` en `casos/` ni la cuarentena."""

    def falla(_origen, _destino):
        raise OSError("disco lleno")

    monkeypatch.setattr(casos.os, "rename", falla)
    with pytest.raises(casos.PreparacionFallida):
        casos.crear("Sin sitio")
    assert [p.name for p in config.carpeta_casos().iterdir()] == []
    assert not (datos / casos.CARPETA_CUARENTENA).exists()


# --- subir (B13 a B15, S5, S6) ----------------------------------------------------------------


def test_subir_una_base_al_dia_la_publica_sin_aviso(
    datos: Path, plantillas: dict[str, Path]
) -> None:
    subida = casos.subir_seguro(io.BytesIO(plantillas["minima"].read_bytes()), "Mi obra.db")
    assert subida.ruta == config.carpeta_casos().resolve() / "Mi obra.db"
    assert subida.aviso is None
    assert _nombres() == ["Mi obra.db"]
    assert _revision(subida.ruta) == revision_head(Destino.CASO)
    assert set(arbol(datos)) == {"casos", "casos/Mi obra.db"}


def test_el_nombre_elegido_gana_al_del_archivo(datos: Path, plantillas: dict[str, Path]) -> None:
    contenido = io.BytesIO(plantillas["minima"].read_bytes())
    assert casos.subir_seguro(contenido, "x.db", "Otro nombre").ruta.name == "Otro nombre.db"


def test_el_nombre_del_archivo_solo_aporta_su_ultima_parte(
    datos: Path, plantillas: dict[str, Path]
) -> None:
    contenido = io.BytesIO(plantillas["minima"].read_bytes())
    ruta = casos.subir_seguro(contenido, "..\\..\\evil.db").ruta
    assert ruta == config.carpeta_casos().resolve() / "evil.db"
    assert not (datos.parent / "evil.db").exists() and not (datos / "evil.db").exists()


@pytest.mark.parametrize("nombre", ["..\\x", "C:\\x", "con", "x:y", "demostracion"])
def test_un_nombre_elegido_hostil_se_rechaza_sin_guardar(
    datos: Path, plantillas: dict[str, Path], nombre: str
) -> None:
    with pytest.raises(RutaDeCasoRechazada):
        casos.subir_seguro(io.BytesIO(plantillas["minima"].read_bytes()), "ok.db", nombre)
    assert arbol(datos) == {}


@pytest.mark.parametrize("archivo", [None, "", "   ", "..", "/"])
def test_sin_nombre_utilizable_se_rechaza(
    datos: Path, plantillas: dict[str, Path], archivo: str | None
) -> None:
    with pytest.raises(RutaDeCasoRechazada):
        casos.subir_seguro(io.BytesIO(plantillas["minima"].read_bytes()), archivo)
    assert arbol(datos) == {}


def test_subir_una_base_0_5_0_la_respalda_y_la_migra(datos: Path, tmp_path: Path) -> None:
    """B14: la 0.5.0 (sin `alembic_version`) se adopta con respaldo y recarga como su ficha."""
    origen = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "demo.db")
    subida = casos.subir_seguro(io.BytesIO(origen.read_bytes()), "demo antigua.db")
    assert subida.aviso == AVISO_MIGRADA
    assert _revision(subida.ruta) == revision_head(Destino.CASO)
    juegos = [p for p in config.carpeta_respaldos().iterdir() if p.is_dir()]
    assert len(juegos) == 1 and (juegos[0] / "casos" / "demo antigua.db").is_file()
    esperado = bases_prueba.ficha("0.5.0")["bases"]["demo.db"]
    assert bases_prueba.diferencias_con_ficha(subida.ruta, esperado) == []
    assert not (datos / casos.CARPETA_CUARENTENA).exists()


def _juegos_por_motivo() -> dict[str, list[Path]]:
    salida: dict[str, list[Path]] = {}
    for carpeta, ficha in respaldo.listar_juegos(config.carpeta_respaldos()):
        salida.setdefault(ficha["motivo"], []).append(carpeta)
    return salida


def test_las_subidas_viejas_no_borran_el_respaldo_de_la_migracion_real(
    datos: Path, tmp_path: Path
) -> None:
    """Defecto de BCP-2: seis subidas de bases anteriores a `head` no pueden llevarse el juego de
    la migración de la instalación; las subidas se podan aparte (5) con su propio motivo."""
    real = respaldo.respaldar(
        [],
        respaldo.MOTIVO_MIGRACION,
        ruta_instalacion=config.ruta_instalacion(),
        carpeta_respaldos=config.carpeta_respaldos(),
        heads={d.value: revision_head(d) for d in Destino},
        ahora=datetime(2020, 1, 1),
    )
    origen = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "demo.db")
    for n in range(7):
        casos.subir_seguro(io.BytesIO(origen.read_bytes()), f"vieja {n}.db")
    por_motivo = _juegos_por_motivo()
    assert por_motivo[respaldo.MOTIVO_MIGRACION] == [real]
    assert len(por_motivo[respaldo.MOTIVO_SUBIDA]) == respaldo.CONSERVAR_SUBIDAS


def test_las_migraciones_de_base_datos_siguen_conservando_cinco(
    datos: Path, tmp_path: Path
) -> None:
    for n in range(7):
        origen = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / f"m{n}.db")
        base_datos.preparar_base(origen)
    por_motivo = _juegos_por_motivo()
    assert len(por_motivo[respaldo.MOTIVO_MIGRACION]) == respaldo.CONSERVAR_MIGRACIONES
    assert respaldo.MOTIVO_SUBIDA not in por_motivo


def test_purgar_borra_tambien_el_journal_wal_y_shm_de_un_temporal_viejo(datos: Path) -> None:
    casos_dir = config.carpeta_casos()
    casos_dir.mkdir()
    viejos = [casos_dir / f".subiendo-9.tmp{extra}" for extra in ("", "-journal", "-wal", "-shm")]
    nuevos = [casos_dir / f".subiendo-8.tmp{extra}" for extra in ("-wal", "-shm")]
    for ruta in (*viejos, *nuevos):
        ruta.write_bytes(b"x")
    hace_dos_horas = time.time() - 2 * 3600
    for ruta in viejos:
        os.utime(ruta, (hace_dos_horas, hace_dos_horas))
    assert casos.purgar_cuarentena() == 4
    assert {p.name for p in casos_dir.iterdir()} == {p.name for p in nuevos}


@pytest.mark.parametrize("hostil", sorted(HOSTILES))
def test_una_subida_rechazada_no_deja_rastro(
    datos: Path, plantillas: dict[str, Path], tmp_path: Path, hostil: str
) -> None:
    """B15: cada archivo hostil se rechaza con su motivo y el árbol de `<datos>` no cambia."""
    archivo = HOSTILES[hostil](tmp_path / "hostil.db", plantillas["minima"])
    config.carpeta_casos().mkdir(parents=True, exist_ok=True)
    antes = arbol(datos)
    with pytest.raises((casos.ArchivoNoValido, casos.CarpetaMasNueva)) as error:
        casos.subir_seguro(io.BytesIO(archivo.read_bytes()), "hostil.db")
    if hostil == "revision_desconocida":
        assert isinstance(error.value, casos.CarpetaMasNueva)
        assert str(error.value) == (
            "Esta base (hostil.db) es de una versión más nueva de Sílice (revisión zzz). Instale "
            "esa versión o restaure el respaldo previo; no se modificó."
        )
    elif hostil in {"texto"}:
        assert str(error.value) == "«hostil.db» no es una base de Sílice (SQLite): no se guardó."
    else:
        assert str(error.value) == MENSAJE_NO_VALIDO
    assert str(tmp_path) not in str(error.value) and str(datos) not in str(error.value)
    assert arbol(datos) == antes


def test_una_base_futura_es_mas_nueva(datos: Path, tmp_path: Path) -> None:
    futura = bases_prueba.crear_base_futura(tmp_path / "futura.db")
    with pytest.raises(casos.CarpetaMasNueva, match="caso_9999_futura"):
        casos.subir_seguro(io.BytesIO(futura.read_bytes()), "futura.db")
    assert arbol(datos) == {}


def test_pasar_el_tope_da_demasiado_grande_sin_escribir(
    datos: Path, plantillas: dict[str, Path]
) -> None:
    contenido = plantillas["minima"].read_bytes()
    with pytest.raises(casos.ArchivoDemasiadoGrande, match=f"^{MENSAJE_GRANDE}$"):
        casos.subir_seguro(io.BytesIO(contenido), "grande.db", tope=len(contenido) - 1)
    assert arbol(datos) == {}
    assert casos.subir_seguro(io.BytesIO(contenido), "justa.db", tope=len(contenido)).ruta.exists()


def test_el_tope_por_omision_es_20_mib() -> None:
    assert casos.TOPE_SUBIDA == 20 * 1024 * 1024


def test_una_validacion_que_pasa_su_plazo_se_rechaza(
    datos: Path, plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(casos, "PLAZO_VALIDACION_S", 0.0)
    with pytest.raises(casos.ArchivoNoValido, match=f"^{MENSAJE_NO_VALIDO}$"):
        casos.subir_seguro(io.BytesIO(plantillas["minima"].read_bytes()), "lenta.db")
    assert arbol(datos) == {}


def test_una_subida_con_nombre_ya_usado_no_pisa_nada(
    datos: Path, plantillas: dict[str, Path]
) -> None:
    casos.crear("Existente")
    antes = arbol(datos)
    with pytest.raises(CasoYaExiste) as error:
        casos.subir_seguro(io.BytesIO(plantillas["minima"].read_bytes()), "EXISTENTE.db")
    assert str(error.value) == (
        "Ya hay una carpeta de trabajo llamada Existente.db: cambie el nombre antes de subirla."
    )
    assert arbol(datos) == antes


def test_una_tabla_de_mas_no_se_rechaza(
    datos: Path, plantillas: dict[str, Path], tmp_path: Path
) -> None:
    archivo = copiar(plantillas["minima"], tmp_path / "extra.db")
    with closing(sqlite3.connect(archivo)) as conexion:
        conexion.execute("CREATE TABLE notas_de_obra (id INTEGER PRIMARY KEY, texto TEXT)")
        conexion.commit()
    assert casos.subir_seguro(io.BytesIO(archivo.read_bytes()), "extra.db").ruta.exists()


@pytest.mark.parametrize("tabla", NUCLEO)
def test_sin_una_tabla_del_nucleo_no_es_un_caso(
    datos: Path, plantillas: dict[str, Path], tmp_path: Path, tabla: str
) -> None:
    archivo = copiar(plantillas["minima"], tmp_path / "incompleto.db")
    with closing(sqlite3.connect(archivo)) as conexion:
        conexion.execute("PRAGMA foreign_keys = OFF")
        conexion.execute(f'DROP TABLE "{tabla}"')
        conexion.commit()
    with pytest.raises(casos.ArchivoNoValido):
        casos.subir_seguro(io.BytesIO(archivo.read_bytes()), "incompleto.db")
    assert arbol(datos) == {}


# --- la cuarentena ----------------------------------------------------------------------------


def test_purgar_borra_lo_de_mas_de_una_hora_y_deja_lo_reciente(datos: Path) -> None:
    cuarentena = datos / "cuarentena"
    viejo = cuarentena / "a"
    viejo.mkdir(parents=True)
    (viejo / "x.db").write_bytes(b"x")
    reciente = cuarentena / "b"
    reciente.mkdir()
    casos_dir = config.carpeta_casos()
    casos_dir.mkdir()
    temporal_viejo = casos_dir / ".subiendo-1.tmp"
    temporal_viejo.write_bytes(b"x")
    temporal_nuevo = casos_dir / ".subiendo-2.tmp"
    temporal_nuevo.write_bytes(b"x")
    (casos_dir / "obra.db").write_bytes(b"")
    hace_dos_horas = time.time() - 2 * 3600
    for ruta in (viejo, viejo / "x.db", temporal_viejo, casos_dir / "obra.db"):
        os.utime(ruta, (hace_dos_horas, hace_dos_horas))
    assert casos.purgar_cuarentena() == 2
    assert set(arbol(datos)) == {
        "cuarentena",
        "cuarentena/b",
        "casos",
        "casos/.subiendo-2.tmp",
        "casos/obra.db",
    }


def test_purgar_sin_cuarentena_no_crea_nada(datos: Path) -> None:
    assert casos.purgar_cuarentena() == 0
    assert arbol(datos) == {}


def test_purgar_quita_la_carpeta_de_cuarentena_vacia(datos: Path) -> None:
    (datos / "cuarentena").mkdir()
    assert casos.purgar_cuarentena() == 0
    assert arbol(datos) == {}


# --- estado de la carpeta abierta (B18) ---------------------------------------------------------


def test_el_estado_de_un_caso_que_no_existe_no_lo_crea(datos: Path) -> None:
    ruta = config.carpeta_casos() / "silice.db"
    estado = casos.estado(ruta)
    assert (estado.partidas, estado.insumos, estado.proyectos, estado.proyectos_con_version) == (
        0,
        0,
        0,
        0,
    )
    assert estado.lista_vigente is None and estado.error is None and not estado.por_migrar
    assert arbol(datos) == {}


def test_el_estado_de_una_base_vacia(datos: Path, plantillas: dict[str, Path]) -> None:
    ruta = copiar(plantillas["minima"], config.carpeta_casos() / "vacia.db")
    estado = casos.estado(ruta)
    assert (estado.partidas, estado.insumos, estado.proyectos) == (0, 0, 0)
    assert estado.nombre == "vacia.db" and not estado.es_demostracion


def test_el_estado_cuenta_sin_escribir(datos: Path, plantillas: dict[str, Path]) -> None:
    """Oráculo: los conteos de la ficha de `v1_0_0/demo.db` y su lista de mayor vigencia."""
    ruta = copiar(plantillas["demo"], config.carpeta_casos() / "demostracion.db")
    ficha = bases_prueba.ficha("1.0.0")["bases"]["demo.db"]
    with _abre(ruta) as conexion:
        lista = conexion.execute(
            "SELECT nombre FROM lista_precios ORDER BY fecha_vigencia DESC, id DESC LIMIT 1"
        ).fetchone()[0]
    huella = base_datos.respaldo.huella(ruta)
    antes = arbol(datos)
    estado = casos.estado(ruta)
    assert estado.partidas == ficha["filas_por_tabla"]["partida"] == 8
    assert estado.insumos == ficha["filas_por_tabla"]["insumo"]
    assert estado.proyectos == ficha["filas_por_tabla"]["proyecto"]
    assert estado.proyectos_con_version == len({p["proyecto"] for p in ficha["presupuestos"]})
    assert estado.lista_vigente == lista
    assert estado.es_demostracion and not estado.por_migrar and estado.error is None
    assert base_datos.respaldo.huella(ruta) == huella  # solo lectura: ni DDL ni escritura
    assert arbol(datos) == antes


def test_el_estado_de_una_base_mas_nueva_lo_dice_sin_rutas(datos: Path) -> None:
    ruta = bases_prueba.crear_base_futura(config.carpeta_casos() / "futura.db")
    estado = casos.estado(ruta)
    assert estado.error == (
        "Esta base (futura.db) es de una versión más nueva de Sílice (revisión caso_9999_futura). "
        "Instale esa versión o restaure el respaldo previo; no se modificó."
    )


def test_el_estado_de_un_archivo_ilegible_no_trae_rutas(datos: Path) -> None:
    ruta = config.carpeta_casos() / "rota.db"
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(b"SQLite format 3\x00" + b"\x00" * 50)
    estado = casos.estado(ruta)
    assert estado.error == (
        "No se pudo leer esta carpeta de trabajo: restaure un respaldo o elija otra."
    )
    assert str(datos) not in estado.error


def test_una_base_vieja_esta_por_migrar(datos: Path) -> None:
    ruta = bases_prueba.copiar_base("0.5.0", "demo.db", config.carpeta_casos() / "vieja.db")
    huella = base_datos.respaldo.huella(ruta)
    assert casos.estado(ruta).por_migrar
    assert base_datos.respaldo.huella(ruta) == huella


# --- ubicación en llano, sin rutas absolutas ---------------------------------------------------


def test_la_ubicacion_en_desarrollo_es_relativa_a_la_carpeta_de_datos(datos: Path) -> None:
    ruta = config.carpeta_casos() / "obra.db"
    assert casos.ubicacion(ruta) == "En la carpeta de datos de Sílice: casos/obra.db"


def test_la_ubicacion_bajo_el_programa_es_relativa_al_programa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SILICE_DATOS", str(config.RAIZ / "data"))
    ruta = config.RAIZ / "data" / "casos" / "obra.db"
    assert casos.ubicacion(ruta) == "En data/casos/obra.db"


def test_la_ubicacion_en_el_producto_usa_la_variable_literal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("SILICE_DATOS", str(tmp_path / "Silice" / "datos"))
    monkeypatch.setattr(config, "es_producto", lambda raiz=None: True)
    ruta = tmp_path / "Silice" / "datos" / "casos" / "demo.db"
    assert casos.ubicacion(ruta) == "En %LOCALAPPDATA%\\Silice\\datos\\casos\\demo.db"


def test_fuera_de_toda_carpeta_conocida_solo_se_da_el_nombre(tmp_path: Path) -> None:
    ruta = tmp_path.parent / "otra" / "externo.db"
    assert casos.ubicacion(ruta) == "Fuera de la carpeta de datos de Sílice: externo.db"


@pytest.mark.parametrize(
    ("nombre", "es"),
    [
        ("demostracion.db", True),
        ("Demostracion.DB", True),
        ("demostración.db", True),
        ("demostraciones.db", False),
        ("obra.db", False),
    ],
)
def test_es_demostracion_se_decide_por_el_nombre(nombre: str, es: bool) -> None:
    assert casos.es_demostracion(nombre) is es


# --- la demostración (B16, P-10) -----------------------------------------------------------------


def _doble(plantilla: Path, llamadas: list[Path]):
    def construir(salida: Path) -> None:
        llamadas.append(salida)
        copiar(plantilla, salida)

    return construir


def test_la_demostracion_se_construye_fuera_y_se_publica_una_vez(
    datos: Path, plantillas: dict[str, Path]
) -> None:
    llamadas: list[Path] = []
    abierta = copiar(plantillas["minima"], config.carpeta_casos() / "mi obra.db")
    huella = base_datos.respaldo.huella(abierta)
    ruta, creada = casos.demostracion(_doble(plantillas["demo"], llamadas))
    assert creada and ruta == config.carpeta_casos().resolve() / "demostracion.db"
    assert llamadas[0].is_absolute() and llamadas[0].name == "demostracion.db"
    assert llamadas[0].parent.parent == (datos / "cuarentena").resolve()
    assert casos.estado(ruta).partidas == 8
    ruta2, creada2 = casos.demostracion(_doble(plantillas["demo"], llamadas))
    assert (ruta2, creada2) == (ruta, False) and len(llamadas) == 1  # idempotente
    assert base_datos.respaldo.huella(abierta) == huella  # no toca la carpeta abierta
    assert set(arbol(datos)) == {"casos", "casos/demostracion.db", "casos/mi obra.db"}


@pytest.mark.parametrize("modo", ["falla", "basura", "nada"])
def test_una_demostracion_fallida_no_deja_nada(datos: Path, modo: str) -> None:
    def construir(salida: Path) -> None:
        if modo == "falla":
            raise demostracion.DemostracionFallida("el hijo terminó con 1")
        if modo == "basura":
            salida.write_bytes(b"no soy una base")

    with pytest.raises(demostracion.DemostracionFallida, match=f"^{MENSAJE_DEMOSTRACION}$"):
        casos.demostracion(construir)
    assert arbol(datos) == {}


def test_una_demostracion_vacia_existente_no_se_pisa(
    datos: Path, plantillas: dict[str, Path]
) -> None:
    ruta = copiar(plantillas["minima"], config.carpeta_casos() / "demostracion.db")
    huella = base_datos.respaldo.huella(ruta)
    with pytest.raises(CasoYaExiste, match="demostracion.db"):
        casos.demostracion(lambda salida: pytest.fail("no debe construir"))
    assert base_datos.respaldo.huella(ruta) == huella


def test_la_demostracion_respeta_el_tope(datos: Path) -> None:
    carpeta = config.carpeta_casos()
    carpeta.mkdir(parents=True)
    for numero in range(100):
        (carpeta / f"c{numero:03}.db").write_bytes(b"")
    with pytest.raises(casos.TopeDeCarpetas, match=f"^{MENSAJE_TOPE}$"):
        casos.demostracion(lambda salida: pytest.fail("no debe construir"))


# --- el proceso hijo (operacion/demostracion.py) -----------------------------------------------


def test_la_orden_del_hijo_es_la_del_instalador(tmp_path: Path) -> None:
    salida = tmp_path / "demostracion.db"
    assert demostracion.orden(salida) == [
        sys.executable,
        "-E",
        "-s",
        "-B",
        "-X",
        "utf8",
        "-m",
        "operacion",
        "demostracion",
        "--salida",
        str(salida),
    ]


def test_el_entorno_del_hijo_no_hereda_python_ni_virtual_env() -> None:
    entorno = demostracion.entorno_hijo(
        {"PYTHONPATH": "x", "pythonhome": "y", "VIRTUAL_ENV": "z", "SILICE_DATOS": "d", "PATH": "p"}
    )
    assert entorno == {"SILICE_DATOS": "d", "PATH": "p"}


def _con_orden(monkeypatch: pytest.MonkeyPatch, codigo: str) -> None:
    monkeypatch.setattr(
        demostracion, "orden", lambda salida: [sys.executable, "-c", codigo, str(salida)]
    )


def test_construir_corre_el_hijo_y_exige_el_archivo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _con_orden(monkeypatch, "import sys, pathlib; pathlib.Path(sys.argv[1]).write_bytes(b'x')")
    salida = tmp_path / "demostracion.db"
    demostracion.construir(salida)
    assert salida.read_bytes() == b"x"


@pytest.mark.parametrize(
    "codigo",
    ["import sys; sys.exit(3)", "pass", "import time; time.sleep(30)"],
    ids=["termina_con_error", "no_escribe", "pasa_el_plazo"],
)
def test_construir_falla_si_el_hijo_falla(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, codigo: str
) -> None:
    _con_orden(monkeypatch, codigo)
    inicio = time.monotonic()
    with pytest.raises(demostracion.DemostracionFallida):
        demostracion.construir(tmp_path / "demostracion.db", plazo=1.0)
    assert time.monotonic() - inicio < 20


def test_el_plazo_por_omision_es_120_s() -> None:
    assert demostracion.PLAZO_S == 120


# --- la orden `python -m operacion demostracion --salida` ---------------------------------------


def test_la_orden_con_salida_siembra_esa_ruta(tmp_path: Path, monkeypatch) -> None:
    llamadas: list[list[str]] = []
    import scripts.seed_demo as seed_demo

    monkeypatch.setattr(seed_demo, "main", lambda argv: llamadas.append(list(argv)) or 0)
    salida = tmp_path / "cuarentena" / "t" / "demostracion.db"
    salida.parent.mkdir(parents=True)
    assert cli.main(["demostracion", "--salida", str(salida)]) == 0
    assert salida.exists() and llamadas == [["--db", str(salida)]]
    assert not config.carpeta_casos().exists()  # no pasó por la carpeta de casos


def test_la_orden_con_salida_relativa_se_niega(monkeypatch, capsys) -> None:
    import scripts.seed_demo as seed_demo

    monkeypatch.setattr(seed_demo, "main", lambda argv: pytest.fail("no debe sembrar"))
    assert cli.main(["demostracion", "--salida", "relativa.db"]) == 2
    assert "absoluta" in capsys.readouterr().err
    assert not Path("relativa.db").exists()
