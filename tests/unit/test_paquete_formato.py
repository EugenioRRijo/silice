"""Abrir un ZIP ajeno sin riesgo: las fronteras exactas de S3 §8.4 (RNF-16, RF-86).

Oráculo: los números literales de la tabla del spec (20 MiB = 20 971 520 B, 50 MiB = 52 428 800 B,
100 MiB = 104 857 600 B, 100:1) y la aritmética de la cabecera ZIP (30 + 46 + 22 bytes fijos, con
el nombre dos veces). Cada límite se prueba en su valor y en su valor + 1 byte, con los límites
REALES (los archivos grandes se escriben por partes en `tmp_path`, con ceros comprimibles y un
prefijo pseudoaleatorio para no disparar la relación de compresión) y, además, con límites chicos
puestos con `monkeypatch` para que la frontera sea legible.
"""

from __future__ import annotations

import io
import random
import zipfile
from pathlib import Path

import pytest

from paquete import formato
from paquete.formato import PaqueteRechazado, abrir_zip, comprobar_salida, relacion_aceptable

NOMBRE = "presupuesto.json"
#: Una entrada sin compresión en un ZIP de Python pesa N + 98 + 2 x len(nombre): cabecera local
#: (30), directorio central (46) y fin del directorio central (22), con el nombre en dos.
SOBRECARGA = 98 + 2 * len(NOMBRE)
MIB = 1024 * 1024
BLOQUE = MIB


def zip_de(entradas: dict[str, bytes], metodo: int = zipfile.ZIP_STORED) -> bytes:
    flujo = io.BytesIO()
    with zipfile.ZipFile(flujo, "w", metodo) as z:
        for nombre, octetos in entradas.items():
            z.writestr(nombre, octetos)
    return flujo.getvalue()


def zip_mixto(ruta: Path, entradas: dict[str, tuple[bytes, int]]) -> bytes:
    """Un ZIP *deflate* escrito por partes en disco: cada entrada es `prefijo` seguido de ceros
    hasta `total` bytes. Nunca arma en memoria el contenido descomprimido."""
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, (prefijo, total) in entradas.items():
            with z.open(nombre, "w") as destino:
                destino.write(prefijo)
                faltan = total - len(prefijo)
                ceros = bytes(BLOQUE)
                while faltan > 0:
                    trozo = min(faltan, BLOQUE)
                    destino.write(ceros[:trozo])
                    faltan -= trozo
    return ruta.read_bytes()


def ruido(semilla: int, n: int) -> bytes:
    """Bytes pseudoaleatorios reproducibles: no se comprimen."""
    return random.Random(semilla).randbytes(n)


def comprimido(datos: bytes, nombre: str = NOMBRE) -> int:
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        return z.getinfo(nombre).compress_size


# --- los números del spec ------------------------------------------------------------------


def test_los_limites_son_los_numeros_literales_del_spec() -> None:
    assert (formato.LIMITE_ARCHIVO, formato.LIMITE_ENTRADA, formato.LIMITE_TOTAL) == (
        20_971_520,
        52_428_800,
        104_857_600,
    )
    assert (formato.RELACION_MAXIMA, formato.LIMITE_FILAS) == (100, 200_000)


# --- tamaño del archivo: 20 MiB -------------------------------------------------------------


def test_el_archivo_de_20_mib_exactos_pasa_y_con_un_byte_mas_se_rechaza() -> None:
    justo = zip_de({NOMBRE: b"x" * (formato.LIMITE_ARCHIVO - SOBRECARGA)})
    assert len(justo) == 20_971_520
    assert len(abrir_zip(justo)[NOMBRE]) == 20_971_520 - SOBRECARGA
    mas = zip_de({NOMBRE: b"x" * (formato.LIMITE_ARCHIVO - SOBRECARGA + 1)})
    assert len(mas) == 20_971_521
    with pytest.raises(PaqueteRechazado, match="20 MiB"):
        abrir_zip(mas)


# --- descomprimido por entrada: 50 MiB ------------------------------------------------------


@pytest.mark.parametrize("tamano,pasa", [(1000, True), (1001, False)])
def test_el_limite_por_entrada_en_su_frontera(monkeypatch, tamano: int, pasa: bool) -> None:
    monkeypatch.setattr(formato, "LIMITE_ENTRADA", 1000)
    datos = zip_de({NOMBRE: b"y" * tamano})
    if pasa:
        assert len(abrir_zip(datos)[NOMBRE]) == 1000
    else:
        with pytest.raises(PaqueteRechazado, match="descomprimido excede 1000"):
            abrir_zip(datos)


@pytest.mark.parametrize("extra,pasa", [(0, True), (1, False)])
def test_la_entrada_de_50_mib_exactos_pasa_y_con_un_byte_mas_se_rechaza(
    tmp_path: Path, extra: int, pasa: bool
) -> None:
    # 600 000 B de ruido: el comprimido supera 52 428 800 / 100 = 524 288 B (relación < 100:1)
    prefijo = ruido(50, 600_000)
    datos = zip_mixto(tmp_path / "e.zip", {NOMBRE: (prefijo, 52_428_800 + extra)})
    assert len(datos) < 20_971_520 and comprimido(datos) > 524_288
    if pasa:
        assert len(abrir_zip(datos)[NOMBRE]) == 52_428_800
    else:
        with pytest.raises(PaqueteRechazado, match="descomprimido excede 52428800 bytes"):
            abrir_zip(datos)


# --- descomprimido en total: 100 MiB --------------------------------------------------------


@pytest.mark.parametrize("ultimo,pasa", [(500, True), (501, False)])
def test_el_limite_total_en_su_frontera(monkeypatch, ultimo: int, pasa: bool) -> None:
    monkeypatch.setattr(formato, "LIMITE_TOTAL", 2500)
    datos = zip_de({NOMBRE: b"a" * 1000, "informe.json": b"b" * 1000, "cadena.json": b"c" * ultimo})
    if pasa:
        assert sum(len(v) for v in abrir_zip(datos).values()) == 2500
    else:
        with pytest.raises(PaqueteRechazado, match="en total"):
            abrir_zip(datos)


@pytest.mark.parametrize("ultimo,pasa", [(0, True), (1, False)])
def test_el_total_de_100_mib_exactos_pasa_y_con_un_byte_mas_se_rechaza(
    tmp_path: Path, ultimo: int, pasa: bool
) -> None:
    entradas = {
        NOMBRE: (ruido(1, 600_000), 52_428_800),
        "informe.json": (ruido(2, 600_000), 52_428_800),
        "cadena.json": (b"c" * ultimo, ultimo),
    }
    datos = zip_mixto(tmp_path / "t.zip", entradas)
    assert len(datos) < 20_971_520
    if pasa:
        assert sum(len(v) for v in abrir_zip(datos).values()) == 104_857_600
    else:
        with pytest.raises(PaqueteRechazado, match="excede 104857600 bytes en total"):
            abrir_zip(datos)


# --- relación de compresión: 100:1 ----------------------------------------------------------


def test_la_relacion_de_compresion_en_enteros() -> None:
    assert relacion_aceptable(100, 1) and not relacion_aceptable(101, 1)
    assert relacion_aceptable(0, 0) and not relacion_aceptable(1, 0)
    assert relacion_aceptable(10_000, 100) and not relacion_aceptable(10_001, 100)


def test_la_relacion_100_a_1_exacta_pasa_y_un_byte_mas_se_rechaza(tmp_path: Path) -> None:
    """Se busca un tamaño N con N == 100 x comprimido(N) (punto fijo), en un ZIP real."""
    prefijo = ruido(100, 2000)
    n = 100 * len(prefijo)
    for _ in range(50):
        datos = zip_mixto(tmp_path / "r.zip", {NOMBRE: (prefijo, n)})
        c = comprimido(datos)
        if n == 100 * c:
            break
        n = 100 * c
    assert n == 100 * comprimido(datos), "no se halló el punto fijo 100:1"
    assert len(abrir_zip(datos)[NOMBRE]) == n
    mas = zip_mixto(tmp_path / "r1.zip", {NOMBRE: (prefijo, n + 1)})
    assert comprimido(mas) == n // 100  # un cero más no cambia el comprimido: n + 1 > 100 x c
    with pytest.raises(PaqueteRechazado, match="comprime más de 100:1"):
        abrir_zip(mas)


def test_una_bomba_de_compresion_se_rechaza_sin_extraerse() -> None:
    bomba = zip_de({NOMBRE: b"\x00" * (5 * MIB)}, zipfile.ZIP_DEFLATED)
    assert len(bomba) < 20_000
    with pytest.raises(PaqueteRechazado, match="comprime más de 100:1"):
        abrir_zip(bomba)


def test_una_bomba_que_excede_50_mib_se_corta_por_tamano_antes_que_por_relacion(
    tmp_path: Path,
) -> None:
    datos = zip_mixto(tmp_path / "b.zip", {NOMBRE: (b"", 60 * MIB)})
    assert len(datos) < 200_000
    with pytest.raises(PaqueteRechazado, match="descomprimido excede"):
        abrir_zip(datos)


# --- cabeceras que mienten, nombres y métodos -----------------------------------------------


def test_un_tamano_de_cabecera_que_miente_por_debajo_no_deja_pasar_mas_bytes() -> None:
    datos = bytearray(zip_de({NOMBRE: b"z" * 400}))
    for firma_cabecera, desplazamiento in ((b"PK\x03\x04", 22), (b"PK\x01\x02", 24)):
        posicion = datos.find(firma_cabecera)
        fin = posicion + desplazamiento
        datos[fin : fin + 4] = (10).to_bytes(4, "little")
    with pytest.raises(PaqueteRechazado, match="dañado"):
        abrir_zip(bytes(datos))


@pytest.mark.parametrize(
    "nombre",
    [
        "../manifiesto.json",
        "/manifiesto.json",
        "a/../b.json",
        "./presupuesto.json",
        "C:/manifiesto.json",
        "anexos/../presupuesto.json",
    ],
)
def test_rutas_inseguras_se_rechazan(nombre: str) -> None:
    with pytest.raises(PaqueteRechazado, match="ruta insegura"):
        abrir_zip(zip_de({nombre: b"{}"}))


def test_ruta_con_barra_invertida_se_rechaza() -> None:
    datos = zip_de({"x_x.json": b"{}"}).replace(b"x_x.json", b"x\\x.json")  # mismo largo
    with pytest.raises(PaqueteRechazado, match="ruta insegura|no admitido"):  # Windows la normaliza
        abrir_zip(datos)


def test_ruta_absoluta_con_barra_invertida_se_rechaza_en_cualquier_sistema() -> None:
    # Windows convierte «\» en «/» al leer: queda «/manifiesto.json»; Linux la ve con «\».
    datos = zip_de({"_manifiesto.json": b"{}"}).replace(b"_manifiesto.json", b"\\manifiesto.json")
    with pytest.raises(PaqueteRechazado, match="ruta insegura"):
        abrir_zip(datos)


def test_nombre_fuera_de_la_lista_y_directorios_se_rechazan() -> None:
    mensajes = {
        "otro.json": "no admitido",
        "anexos/otro.json": "no admitido",
        "anexos/": "ruta insegura",
        "presupuesto.xlsx": "no admitido",
        "Presupuesto.json": "no admitido",
    }
    for nombre, mensaje in mensajes.items():
        with pytest.raises(PaqueteRechazado, match=mensaje):
            abrir_zip(zip_de({nombre: b"{}"}))


def test_nombre_repetido_se_rechaza() -> None:
    flujo = io.BytesIO()
    with zipfile.ZipFile(flujo, "w") as z:
        z.writestr(NOMBRE, b"{}")
        with pytest.warns(UserWarning, match="Duplicate name"):
            z.writestr(NOMBRE, b"{}")
    with pytest.raises(PaqueteRechazado, match="repite"):
        abrir_zip(flujo.getvalue())


def test_entrada_cifrada_se_rechaza() -> None:
    datos = bytearray(zip_de({NOMBRE: b"{}"}))
    # bit 0 del indicador general: offset 6 en la cabecera local y 8 en el directorio central
    datos[datos.find(b"PK\x03\x04") + 6] |= 0x01
    datos[datos.find(b"PK\x01\x02") + 8] |= 0x01
    with pytest.raises(PaqueteRechazado, match="cifrado"):
        abrir_zip(bytes(datos))


@pytest.mark.parametrize("metodo", [zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA])
def test_metodo_que_no_es_almacenado_ni_deflate_se_rechaza(metodo: int) -> None:
    with pytest.raises(PaqueteRechazado, match="método de compresión no admitido"):
        abrir_zip(zip_de({NOMBRE: b"{}"}, metodo))


def test_lo_que_no_es_un_zip_se_rechaza_con_un_mensaje() -> None:
    for basura in (b"", b"PK\x03\x04 truncado", b"no soy un zip" * 100):
        with pytest.raises(PaqueteRechazado, match="dañado"):
            abrir_zip(basura)


def test_un_paquete_que_cabe_se_lee_completo() -> None:
    entradas = {NOMBRE: b"{}", "informe.json": b"[]", "anexos/ia.json": b"{}"}
    assert abrir_zip(zip_de(entradas, zipfile.ZIP_DEFLATED)) == entradas


def test_un_zip_vacio_se_abre_sin_archivos() -> None:
    # abrir_zip no exige obligatorios: eso lo hace `verificar` (manifiesto ausente → rechazado)
    assert abrir_zip(zip_de({})) == {}


# --- lo que exporta el emisor: la misma frontera antes de generar ---------------------------


def test_comprobar_salida_en_la_frontera_del_archivo() -> None:
    comprobar_salida({NOMBRE: b"{}"}, 20_971_520)
    with pytest.raises(PaqueteRechazado, match="20971521 bytes"):
        comprobar_salida({NOMBRE: b"{}"}, 20_971_521)


def test_comprobar_salida_en_la_frontera_de_la_entrada_y_del_total() -> None:
    cincuenta = bytes(52_428_800)
    comprobar_salida({NOMBRE: cincuenta}, 1000)
    with pytest.raises(PaqueteRechazado, match="presupuesto.json excede 52428800"):
        comprobar_salida({NOMBRE: bytes(52_428_801)}, 1000)
    comprobar_salida({NOMBRE: cincuenta, "informe.json": cincuenta}, 1000)
    with pytest.raises(PaqueteRechazado, match="total descomprimido"):
        comprobar_salida({NOMBRE: cincuenta, "informe.json": cincuenta, "cadena.json": b"x"}, 1000)


def test_un_flujo_deflate_danado_se_rechaza_sin_escapar_zlib_error() -> None:
    entradas = {NOMBRE: bytes(range(256)) * 8}
    datos = bytearray(zip_de(entradas, zipfile.ZIP_DEFLATED))
    inicio = datos.find(b"PK\x03\x04") + 30 + len(NOMBRE)
    datos[inicio] = 0xFF  # tipo de bloque DEFLATE reservado (11): el inflador falla
    with pytest.raises(PaqueteRechazado, match="dañado"):
        abrir_zip(bytes(datos))


def test_un_directorio_central_corrido_se_rechaza_sin_escapar_value_error() -> None:
    """Un byte dañado en el desplazamiento del directorio central (fin del directorio central,
    bytes 16 a 19) hace que `zipfile` calcule una cabecera local en una posición negativa y lance
    `ValueError: negative seek value` al abrir la entrada. Lo encontró la prueba de un byte cambiado
    de `tests/integration/test_entrega.py` en la CI de Windows (2026-10-18); aquí, determinista."""
    datos = bytearray(zip_de({NOMBRE: b"{}"}))
    fin = datos.rfind(b"PK\x05\x06")
    desplazamiento = int.from_bytes(datos[fin + 16 : fin + 20], "little")
    datos[fin + 16 : fin + 20] = (desplazamiento + 1000).to_bytes(4, "little")
    with pytest.raises(PaqueteRechazado, match=r"^El archivo 'presupuesto\.json' del paquete"):
        abrir_zip(bytes(datos))
