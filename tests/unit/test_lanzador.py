"""Arranque y parada (RF-98; spec S5 §5.4, §8.1 y §10.1). Ningún proceso real.

Un solo proceso (Uvicorn, `api.main:app`) sirve la API y la interfaz de React en `/app/`; la sonda
es `GET /salud`. El plazo de salud (60 s) se recorre con un reloj de mentira que avanza un segundo
por consulta, para probar la frontera exacta (salud en la consulta 59 → arranca; nunca antes de 60
→ se detiene).
"""

from __future__ import annotations

import inspect
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from operacion import config, lanzador, registro
from operacion.config import Ajustes

PYTHON = Path("python.exe")
PRIVADA = "192.168.1.20"


@pytest.fixture(autouse=True)
def _registro_cerrado() -> Iterator[None]:
    """`arrancar` configura el registro `silice` en la carpeta temporal: se cierra al salir."""
    yield
    registro.olvidar_secretos()
    logger = logging.getLogger(registro.NOMBRE_LOGGER)
    for manejador in list(logger.handlers):
        logger.removeHandler(manejador)
        manejador.close()


@pytest.mark.parametrize(
    "ajustes",
    [
        Ajustes(),
        Ajustes(red_local=True, direccion="0.0.0.0"),
        Ajustes(red_local=True, direccion="::"),
        Ajustes(red_local=True, direccion=""),
        Ajustes(red_local=True, direccion=PRIVADA),
        Ajustes(red_local=True, direccion="10.9.9.9"),
    ],
)
@pytest.mark.parametrize(
    "ips", [[], ["127.0.0.1"], [PRIVADA, "127.0.0.1"], ["0.0.0.0"], ["0.0.0.0", "::"]]
)
def test_ninguna_configuracion_produce_0_0_0_0(ajustes: Ajustes, ips: list[str]) -> None:
    direccion, _ = lanzador.elegir_direccion(ajustes, ips)
    orden = lanzador.orden_uvicorn(PYTHON, direccion, ajustes.puerto)
    assert "0.0.0.0" not in " ".join(orden) and "::" not in orden
    assert direccion in {"127.0.0.1", PRIVADA}


def test_la_ip_elegida_se_usa_solo_si_sigue_existiendo() -> None:
    ajustes = Ajustes(red_local=True, direccion=PRIVADA)
    assert lanzador.elegir_direccion(ajustes, [PRIVADA, "127.0.0.1"]) == (PRIVADA, ())
    direccion, avisos = lanzador.elegir_direccion(ajustes, ["10.0.0.4", "127.0.0.1"])
    assert direccion == "127.0.0.1" and len(avisos) == 1
    assert PRIVADA in avisos[0] and "127.0.0.1" in avisos[0]


def test_con_la_red_apagada_es_siempre_el_bucle_local() -> None:
    assert lanzador.elegir_direccion(Ajustes(), [PRIVADA]) == ("127.0.0.1", ())
    apagada_con_ip = Ajustes(red_local=False, direccion=PRIVADA)
    assert lanzador.elegir_direccion(apagada_con_ip, [PRIVADA]) == ("127.0.0.1", ())


def test_ya_no_existe_ninguna_orden_de_streamlit() -> None:
    assert not hasattr(lanzador, "orden_streamlit")
    assert not hasattr(lanzador, "opciones_streamlit")
    assert not hasattr(config, "PUERTO_STREAMLIT")
    assert config.PUERTO_POR_DEFECTO == 8501  # los silice.toml y las reglas de firewall ya escritos


def test_uvicorn_escucha_en_la_misma_direccion_y_sin_registro_de_accesos() -> None:
    orden = lanzador.orden_uvicorn(PYTHON, PRIVADA, 8010)
    assert orden[:6] == ["python.exe", "-E", "-s", "-B", "-X", "utf8"]
    assert orden[6:9] == ["-m", "uvicorn", "api.main:app"]
    assert orden[orden.index("--host") + 1] == PRIVADA
    assert orden[orden.index("--port") + 1] == "8010"
    assert "--no-access-log" in orden and "--reload" not in orden
    assert "streamlit" not in " ".join(orden).lower() and "ui/app.py" not in orden


def test_el_entorno_de_los_hijos(tmp_path: Path) -> None:
    base = {
        "PATH": "x",
        "PYTHONPATH": "z",
        "PYTHONHOME": "h",
        "VIRTUAL_ENV": "v",
        "SILICE_MODO_ENTREGA": "0",
    }
    entorno = {config.VARIABLE_DATOS: str(tmp_path / "d"), config.VARIABLE_USUARIO: str(tmp_path)}
    env = lanzador.entorno_hijos(Ajustes(), "127.0.0.1", entorno, base=base)
    caso = (tmp_path / "d" / "casos" / "silice.db").resolve()
    assert env["SILICE_CASO"] == str(caso)
    assert env["APU_BASE"] == f"sqlite:///{caso.as_posix()}"
    assert env["SILICE_DATOS"] == str((tmp_path / "d").resolve())
    assert env["SILICE_INSTALACION"] == str((tmp_path / "d" / "instalacion.db").resolve())
    assert env["SILICE_USUARIO"] == str(tmp_path.resolve())
    assert env["SILICE_DIRECCION"] == "127.0.0.1" and env["SILICE_MODO_ENTREGA"] == "1"
    assert env["SILICE_PRODUCTO"] == "0"  # árbol de desarrollo
    assert env["HF_HUB_OFFLINE"] == "1" and env["TRANSFORMERS_OFFLINE"] == "1"
    assert env["PATH"] == "x"
    assert not any(k.upper().startswith("PYTHON") or k.upper() == "VIRTUAL_ENV" for k in env)
    abierto = lanzador.entorno_hijos(
        Ajustes(mostrar_investigacion=True), "127.0.0.1", entorno, base=base
    )
    assert "SILICE_MODO_ENTREGA" not in abierto  # tampoco el «0» heredado del usuario


def test_la_cache_del_modelo_se_usa_solo_si_existe(tmp_path: Path) -> None:
    codigo = tmp_path / "codigo"
    codigo.mkdir()
    assert "HF_HOME" not in lanzador.variables_de_similitud(codigo)
    modelo = tmp_path / "modulos" / "similitud" / "hf"
    modelo.mkdir(parents=True)
    variables = lanzador.variables_de_similitud(codigo)
    assert variables == {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HOME": str(modelo),
    }


@dataclass
class Hijo:
    pid: int
    stdout: list[str] = field(default_factory=lambda: ["listo\n"])
    vivo: bool = True
    terminado: bool = False

    def poll(self) -> int | None:
        return None if self.vivo else 0

    def terminate(self) -> None:
        self.terminado, self.vivo = True, False

    def kill(self) -> None:
        self.terminate()

    def wait(self, timeout: float | None = None) -> int:
        return 0


class Escenario:
    """Los efectos de `arrancar` sustituidos: se anota qué se llamó y con qué."""

    def __init__(self, salud: list[bool] | None = None, vivir_ciclos: int = 1) -> None:
        self.lanzados: list[list[str]] = []
        self.entornos: list[dict[str, str]] = []
        self.hijos: list[Hijo] = []
        self.abiertas: list[str] = []
        self.archivos: list[Path] = []
        self.salida: list[str] = []
        self.sondeadas: list[str] = []
        self.salud = list(salud if salud is not None else [True])
        self.ciclos = vivir_ciclos

    def lanzar(self, orden, entorno, cwd):
        self.lanzados.append(list(orden))
        self.entornos.append(dict(entorno))
        hijo = Hijo(pid=5000 + len(self.hijos))
        self.hijos.append(hijo)
        return hijo

    def sonda(self, url: str) -> bool:
        self.sondeadas.append(url)
        return self.salud.pop(0) if len(self.salud) > 1 else self.salud[0]

    def dormir(self, _s: float) -> None:
        self.ciclos -= 1
        if self.ciclos <= 0:
            for hijo in self.hijos:
                hijo.vivo = False

    def correr(self, entorno=None, **extra) -> int:
        return lanzador.arrancar(
            entorno,
            lanzar=self.lanzar,
            sonda=self.sonda,
            abrir=self.abiertas.append,
            ips=extra.pop("ips", lambda: ["127.0.0.1", PRIVADA]),
            tuneles=extra.pop("tuneles", lambda: []),
            puerto_libre=extra.pop("puerto_libre", lambda d, p: True),
            dormir=self.dormir,
            reloj=iter(range(0, 1000, 1)).__next__,
            salida=self.salida.append,
            asegurar=extra.pop("asegurar", self.asegurar),
            abrir_archivo=extra.pop("abrir_archivo", self.archivos.append),
            **extra,
        )

    def asegurar(self, _entorno) -> bool:
        """Por omisión no emite nada (las bases de estas pruebas no se migran)."""
        return False


@pytest.fixture
def bases_reales() -> None:
    """Marca: esta prueba prepara las bases de verdad (migraciones de Alembic)."""


@pytest.fixture(autouse=True)
def _bases_rapidas(request, monkeypatch) -> list[Path]:
    """Las pruebas del arranque que no miran las bases no pagan las migraciones: se anota la
    ruta que se habría preparado. Las que piden `bases_reales` las preparan de verdad."""
    preparadas: list[Path] = []
    if "bases_reales" not in request.fixturenames:
        monkeypatch.setattr(
            lanzador.base_datos, "preparar_base", lambda ruta, *a, **k: preparadas.append(ruta)
        )
    return preparadas


@pytest.fixture
def entorno(tmp_path: Path) -> dict[str, str]:
    return {config.VARIABLE_DATOS: str(tmp_path / "datos"), config.VARIABLE_USUARIO: str(tmp_path)}


def test_arrancar_prepara_las_bases_lanza_uvicorn_y_abre_el_navegador_en_app(
    entorno, bases_reales
) -> None:
    escenario = Escenario(salud=[True])
    assert escenario.correr(entorno) == 0
    assert (
        config.ruta_instalacion(entorno).exists() and config.ruta_caso_por_defecto(entorno).exists()
    )
    assert len(escenario.lanzados) == 1 and "uvicorn" in escenario.lanzados[0]
    assert "api.main:app" in escenario.lanzados[0] and "streamlit" not in escenario.lanzados[0]
    assert escenario.sondeadas and set(escenario.sondeadas) == {"http://127.0.0.1:8501"}
    assert escenario.abiertas == ["http://127.0.0.1:8501/app/"]
    assert config.ruta_ajustes(entorno).exists()  # se creó con los valores por defecto
    assert config.cargar_ajustes(config.ruta_ajustes(entorno)) == Ajustes()
    assert lanzador.leer_estado(entorno) is None  # al salir se limpia
    assert escenario.entornos[0]["SILICE_DATOS"] == str(config.carpeta_datos(entorno))


def test_mientras_corre_el_estado_lleva_los_pids_y_la_direccion(entorno) -> None:
    vistos: list[lanzador.EstadoServidor | None] = []
    escenario = Escenario(salud=[True])

    def dormir(_s: float) -> None:
        vistos.append(lanzador.leer_estado(entorno))
        escenario.hijos[0].vivo = False

    escenario.dormir = dormir  # type: ignore[method-assign]
    assert escenario.correr(entorno) == 0
    (estado,) = vistos
    assert estado is not None and estado.pids[1:] == (5000,)
    assert (estado.direccion, estado.puerto) == ("127.0.0.1", 8501)


def test_sin_navegador_no_abre_nada(entorno, _bases_rapidas) -> None:
    escenario = Escenario()
    assert escenario.correr(entorno, sin_navegador=True) == 0 and escenario.abiertas == []
    # las dos bases, en orden: primero la instalación y luego el caso por defecto
    assert _bases_rapidas == [
        config.ruta_instalacion(entorno),
        config.ruta_caso_por_defecto(entorno),
    ]


def test_con_la_red_local_uvicorn_escucha_en_la_ip_elegida_y_el_puerto_unico(entorno) -> None:
    config.guardar_ajustes(
        config.ruta_ajustes(entorno), Ajustes(puerto=8600, red_local=True, direccion=PRIVADA)
    )
    escenario = Escenario()
    assert escenario.correr(entorno) == 0
    (uvicorn,) = escenario.lanzados  # un solo proceso, un solo puerto
    assert uvicorn[uvicorn.index("--host") + 1] == PRIVADA
    assert uvicorn[uvicorn.index("--port") + 1] == "8600"
    assert escenario.abiertas == [f"http://{PRIVADA}:8600/app/"]


def test_un_silice_toml_viejo_con_api_arranca_igual_y_lo_avisa(entorno) -> None:
    ruta = config.ruta_ajustes(entorno)
    ruta.parent.mkdir(parents=True)
    ruta.write_text("[servidor]\npuerto = 8501\n[api]\nactiva = true\npuerto = 8010\n", "utf-8")
    escenario = Escenario()
    assert escenario.correr(entorno) == 0
    assert len(escenario.lanzados) == 1 and "8010" not in " ".join(escenario.lanzados[0])
    assert any(linea.startswith("AVISO:") and "[api]" in linea for linea in escenario.salida)


def test_la_ip_que_ya_no_existe_arranca_en_el_bucle_local_y_lo_avisa(entorno) -> None:
    config.guardar_ajustes(config.ruta_ajustes(entorno), Ajustes(red_local=True, direccion=PRIVADA))
    escenario = Escenario()
    assert escenario.correr(entorno, ips=lambda: ["127.0.0.1", "10.0.0.4"]) == 0
    uvicorn = escenario.lanzados[0]
    assert uvicorn[uvicorn.index("--host") + 1] == "127.0.0.1"
    assert any(linea.startswith("AVISO:") and PRIVADA in linea for linea in escenario.salida)


def test_una_sola_instancia_abre_el_navegador_y_no_lanza_otra(entorno) -> None:
    lanzador.escribir_estado(lanzador.EstadoServidor((1, 2), "127.0.0.1", 8501, "ayer"), entorno)
    escenario = Escenario(salud=[True])
    assert escenario.correr(entorno) == 0
    assert escenario.lanzados == [] and escenario.abiertas == ["http://127.0.0.1:8501/app/"]
    assert lanzador.leer_estado(entorno) is not None  # la instancia viva conserva su estado


def test_un_estado_huerfano_se_borra_y_se_arranca(entorno) -> None:
    lanzador.escribir_estado(lanzador.EstadoServidor((1, 2), "127.0.0.1", 8501, "ayer"), entorno)
    escenario = Escenario(salud=[False, True])
    assert escenario.correr(entorno) == 0 and len(escenario.lanzados) == 1


def test_puerto_ocupado_da_mensaje_con_el_puerto_y_no_lanza(entorno) -> None:
    escenario = Escenario()
    assert escenario.correr(entorno, puerto_libre=lambda d, p: False) == 1
    assert escenario.lanzados == []
    assert "8501" in " ".join(escenario.salida) and "silice.toml" in " ".join(escenario.salida)


def test_la_salud_en_el_segundo_59_aun_arranca(entorno) -> None:
    """Frontera del plazo: 59 sondas fallidas (relojes 1…59 < 60) y la 60.ª responde."""
    escenario = Escenario(salud=[False] * 59 + [True], vivir_ciclos=60)
    assert escenario.correr(entorno) == 0
    assert escenario.abiertas == ["http://127.0.0.1:8501/app/"]


def test_si_no_responde_en_el_plazo_se_detiene_todo(entorno) -> None:
    """Frontera +1: 60 sondas fallidas; en el reloj 60 se cumple el plazo."""
    escenario = Escenario(salud=[False] * 60 + [True], vivir_ciclos=10_000)
    assert escenario.correr(entorno) == 1
    assert all(h.terminado for h in escenario.hijos) and lanzador.leer_estado(entorno) is None
    assert "60" in " ".join(escenario.salida) and escenario.abiertas == []


def test_si_un_hijo_muere_antes_de_responder_se_detiene(entorno) -> None:
    escenario = Escenario(salud=[False], vivir_ciclos=10_000)
    original = escenario.lanzar

    def lanzar_muerto(orden, env, cwd):
        hijo = original(orden, env, cwd)
        hijo.vivo = False
        return hijo

    escenario.lanzar = lanzar_muerto  # type: ignore[method-assign]
    assert escenario.correr(entorno) == 1 and len(escenario.sondeadas) == 1


def test_una_base_que_no_se_puede_preparar_detiene_el_arranque(entorno, bases_reales) -> None:
    config.ruta_instalacion(entorno).parent.mkdir(parents=True)
    config.ruta_instalacion(entorno).write_bytes(b"esto no es sqlite" * 100)
    escenario = Escenario()
    assert escenario.correr(entorno) == 1 and escenario.lanzados == []
    assert any(linea.startswith("Sílice no arrancó") for linea in escenario.salida)


def test_un_tunel_en_ejecucion_se_avisa_y_se_arranca(entorno) -> None:
    escenario = Escenario()
    assert escenario.correr(entorno, tuneles=lambda: ["cloudflared"]) == 0
    assert "cloudflared" in " ".join(escenario.salida) and len(escenario.lanzados) == 1


def test_el_codigo_de_instalacion_se_muestra_y_no_llega_al_registro(entorno) -> None:
    codigo = config.ruta_codigo_instalacion(entorno)
    codigo.parent.mkdir(parents=True, exist_ok=True)
    codigo.write_text("K7QFM9XRA2PTW4HNC8DV\n", encoding="utf-8")
    escenario = Escenario()
    assert escenario.correr(entorno) == 0
    assert any("K7QFM9XRA2PTW4HNC8DV" in linea for linea in escenario.salida)
    logging.getLogger(registro.NOMBRE_LOGGER).error("código K7QFM9XRA2PTW4HNC8DV")
    texto = (config.carpeta_registros(entorno) / "silice.log").read_text(encoding="utf-8")
    assert "K7QFM9XRA2PTW4HNC8DV" not in texto and registro.MARCA in texto


def test_el_lanzador_emite_el_codigo_antes_de_imprimirlo(entorno) -> None:
    """Primer arranque: el archivo aún no existe cuando arranca; `asegurar` lo crea y entonces se
    imprime (antes se miraba el archivo sin que nadie lo hubiera emitido)."""
    ruta = config.ruta_codigo_instalacion(entorno)
    orden: list[str] = []

    def asegurar(recibido) -> bool:
        assert recibido is entorno
        assert not ruta.exists()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("ABCD-EFGH-IJKL-MNOP-QRST", encoding="utf-8")
        orden.append("asegurar")
        return True

    escenario = Escenario()
    assert escenario.correr(entorno, asegurar=asegurar) == 0
    assert orden == ["asegurar"]
    assert any("ABCD-EFGH-IJKL-MNOP-QRST" in linea for linea in escenario.salida)


def test_el_bloc_de_notas_se_abre_solo_en_el_producto_y_solo_si_se_emitio(
    entorno, monkeypatch: pytest.MonkeyPatch
) -> None:
    ruta = config.ruta_codigo_instalacion(entorno)

    def emite(_entorno) -> bool:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("ABCD-EFGH-IJKL-MNOP-QRST", encoding="utf-8")
        return True

    monkeypatch.setattr(config, "es_producto", lambda raiz=None: False)
    desarrollo = Escenario()
    assert desarrollo.correr(entorno, asegurar=emite) == 0
    assert desarrollo.archivos == []  # en desarrollo y en pruebas nunca se abre nada

    monkeypatch.setattr(config, "es_producto", lambda raiz=None: True)
    producto = Escenario()
    assert producto.correr(entorno, asegurar=emite) == 0
    assert producto.archivos == [ruta]

    ya_estaba = Escenario()
    assert ya_estaba.correr(entorno, asegurar=lambda _e: False) == 0
    assert ya_estaba.archivos == []  # no se emitió ahora: no se abre otra vez


def test_el_gancho_por_omision_es_el_de_la_instalacion_real() -> None:
    parametro = inspect.signature(lanzador.arrancar).parameters["asegurar"]
    assert parametro.default is lanzador.primer_arranque.asegurar_codigo_de_la_instalacion


def test_si_no_se_puede_emitir_el_codigo_el_arranque_sigue(entorno) -> None:
    def falla(_entorno) -> bool:
        raise OSError("disco lleno")

    escenario = Escenario()
    assert escenario.correr(entorno, asegurar=falla) == 0
    assert len(escenario.lanzados) == 1 and escenario.archivos == []
    texto = (config.carpeta_registros(entorno) / "silice.log").read_text(encoding="utf-8")
    assert "código de instalación" in texto and "OSError" in texto


def test_arrancar_sin_cuentas_deja_el_codigo_en_el_archivo_y_en_la_consola(
    entorno, bases_reales
) -> None:
    """De punta a punta con las bases reales: el primer arranque no tenía código y ahora sí."""
    escenario = Escenario()
    real = lanzador.primer_arranque.asegurar_codigo_de_la_instalacion
    assert escenario.correr(entorno, asegurar=real) == 0
    archivo = config.ruta_codigo_instalacion(entorno)
    escrito = archivo.read_text(encoding="ascii").strip()
    assert re.fullmatch(r"(?:[A-Z2-7]{4}-){4}[A-Z2-7]{4}", escrito)
    assert any(escrito in linea for linea in escenario.salida)
    texto = (config.carpeta_registros(entorno) / "silice.log").read_text(encoding="utf-8")
    assert escrito not in texto and escrito.replace("-", "") not in texto


def test_parar_no_mata_nada_si_la_salud_no_responde(entorno) -> None:
    """PID reutilizado: un estado viejo no autoriza a matar un proceso ajeno."""
    lanzador.escribir_estado(lanzador.EstadoServidor((4242, 4243), "127.0.0.1", 8501, "x"), entorno)
    muertos: list[int] = []
    salida: list[str] = []
    codigo = lanzador.parar(
        entorno, sonda=lambda url: False, matar=muertos.append, salida=salida.append
    )
    assert codigo == 0 and muertos == [] and lanzador.leer_estado(entorno) is None


def test_parar_mata_los_hijos_antes_que_el_lanzador(entorno) -> None:
    lanzador.escribir_estado(
        lanzador.EstadoServidor((100, 200, 300), "127.0.0.1", 8501, "x"), entorno
    )
    respuestas = iter([True, True, False])
    muertos: list[int] = []
    codigo = lanzador.parar(
        entorno,
        sonda=lambda url: next(respuestas),
        matar=muertos.append,
        dormir=lambda s: None,
        salida=lambda t: None,
    )
    assert codigo == 0 and muertos == [300, 200, 100] and lanzador.leer_estado(entorno) is None


def test_parar_no_se_mata_a_si_mismo(entorno) -> None:
    import os

    lanzador.escribir_estado(
        lanzador.EstadoServidor((os.getpid(), 200), "127.0.0.1", 8501, "x"), entorno
    )
    respuestas = iter([True, False])
    muertos: list[int] = []
    lanzador.parar(
        entorno,
        sonda=lambda url: next(respuestas),
        matar=muertos.append,
        dormir=lambda s: None,
        salida=lambda t: None,
    )
    assert muertos == [200]


def test_sin_estado_parar_no_hace_nada(entorno) -> None:
    salida: list[str] = []
    assert lanzador.parar(entorno, salida=salida.append) == 0 and "no está en marcha" in salida[0]


@pytest.mark.parametrize(
    "contenido", ["{no es json", "[]", '{"pids": [1]}', '{"pids": ["x"], "direccion": "a"}']
)
def test_un_estado_ilegible_cuenta_como_ausente(entorno, contenido: str) -> None:
    ruta = config.ruta_estado(entorno)
    ruta.parent.mkdir(parents=True)
    ruta.write_text(contenido, encoding="utf-8")
    assert (
        lanzador.leer_estado(entorno) is None
        and lanzador.hay_instancia(entorno, sonda=lambda u: True) is False
    )


def test_el_estado_se_escribe_y_se_lee_igual(entorno) -> None:
    estado = lanzador.EstadoServidor((10, 20, 30), PRIVADA, 8600, "2026-10-13T10:00:00")
    lanzador.escribir_estado(estado, entorno)
    assert lanzador.leer_estado(entorno) == estado
    lanzador.borrar_estado(entorno)
    lanzador.borrar_estado(entorno)  # dos veces no falla
    assert lanzador.leer_estado(entorno) is None


def test_la_sonda_pide_salud_y_exige_el_estado_ok(monkeypatch) -> None:
    pedidas: list[str] = []

    class Respuesta:
        status = 200

        def __init__(self, cuerpo: bytes) -> None:
            self.cuerpo = cuerpo

        def __enter__(self):
            return self

        def __exit__(self, *_a) -> None:
            return None

        def read(self, *_n: int) -> bytes:
            return self.cuerpo

    def abrir(url: str, timeout: float) -> Respuesta:
        pedidas.append(url)
        return Respuesta(b'{"estado": "ok"}')

    monkeypatch.setattr(lanzador.urllib.request, "urlopen", abrir)
    assert lanzador._sonda("http://127.0.0.1:8501") is True
    assert pedidas == ["http://127.0.0.1:8501/salud"]
    monkeypatch.setattr(lanzador.urllib.request, "urlopen", lambda u, timeout: Respuesta(b"<html>"))
    assert lanzador._sonda("http://127.0.0.1:8501") is False  # otro programa en ese puerto


def test_un_servidor_json_viejo_con_puerto_api_se_sigue_leyendo(entorno) -> None:
    ruta = config.ruta_estado(entorno)
    ruta.parent.mkdir(parents=True)
    ruta.write_text(
        '{"pids": [1, 2], "direccion": "127.0.0.1", "puerto": 8501, "puerto_api": null,'
        ' "inicio": "ayer"}',
        encoding="utf-8",
    )
    assert lanzador.leer_estado(entorno) == lanzador.EstadoServidor(
        (1, 2), "127.0.0.1", 8501, "ayer"
    )
