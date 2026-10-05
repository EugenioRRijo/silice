"""A-1 (INV-123, RNF-12): guardado seguro de las subidas de Streamlit en `ui/subidas.py`.

`UploadedFile.name` lo manda el navegador y llega tal cual: `..\\..\\x`, `/etc/passwd`, `C:\\...`,
`CON.csv`. Los oraculos son literales escritos a mano (el nombre que debe quedar), no la salida de
la propia funcion. Las pantallas con subida (`actualizacion`, `elaborar`, `visor`) deben usarla en
lugar de unir el nombre del cliente a una carpeta (`Path(carpeta) / archivo.name`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ui.subidas import LONGITUD_MAXIMA, guardar_subida, nombre_seguro

RAIZ = Path(__file__).resolve().parents[2]


class Subida:
    """Lo que las pantallas usan de un `UploadedFile`: `name` y `getvalue()`."""

    def __init__(self, name, contenido: bytes = b"a,b\n1,2\n") -> None:
        self.name = name
        self._contenido = contenido

    def getvalue(self) -> bytes:
        return self._contenido


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("lista.csv", "lista.csv"),
        ("Lista de precios 2026.xlsx", "Lista de precios 2026.xlsx"),
        ("..\\..\\evil.csv", "evil.csv"),
        ("../../evil.csv", "evil.csv"),
        ("../x.csv", "x.csv"),
        ("..\\x.csv", "x.csv"),
        ("carpeta/sub\\mezcla.csv", "mezcla.csv"),
        ("/etc/passwd", "passwd"),
        ("C:\\Windows\\win.ini", "win.ini"),
        ("\\\\servidor\\recurso\\datos.csv", "datos.csv"),
        ("C:datos.csv", "C_datos.csv"),
        ("a<b>c|d?e*f\"g.csv", "a_b_c_d_e_f_g.csv"),
        ("con\x00trol\x1f.csv", "con_trol_.csv"),
        ("  espacios.csv  ", "espacios.csv"),
        ("termina_en_punto.csv.", "termina_en_punto.csv"),
        ("termina.csv. . ", "termina.csv"),
    ],
)
def test_nombre_seguro_deja_un_solo_componente_limpio(entrada, esperado):
    assert nombre_seguro(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("CON", "_CON"),
        ("con.csv", "_con.csv"),
        ("NUL.txt", "_NUL.txt"),
        ("Prn.xlsx", "_Prn.xlsx"),
        ("AUX", "_AUX"),
        ("COM1", "_COM1"),
        ("com9.csv", "_com9.csv"),
        ("LPT1.csv", "_LPT1.csv"),
        ("LPT9", "_LPT9"),
        ("NUL.tar.gz", "_NUL.tar.gz"),
        ("..\\CON.csv", "_CON.csv"),
        ("COM10.csv", "COM10.csv"),  # no es reservado
        ("CONSOLA.csv", "CONSOLA.csv"),
        ("COM.csv", "COM.csv"),
        ("LPT0.csv", "LPT0.csv"),
    ],
)
def test_nombres_reservados_de_windows_se_renombran_y_los_demas_no(entrada, esperado):
    assert nombre_seguro(entrada) == esperado


@pytest.mark.parametrize("entrada", [None, "", "   ", ".", "..", "...", "../", "..\\", "/", "\\"])
def test_nombre_vacio_o_sin_componente_utilizable_se_rechaza(entrada):
    with pytest.raises(ValueError, match="nombre utilizable"):
        nombre_seguro(entrada)


def test_un_nombre_larguisimo_se_acorta_y_conserva_la_extension():
    resultado = nombre_seguro("a" * 5000 + ".xlsx")
    assert len(resultado) == LONGITUD_MAXIMA
    assert resultado == "a" * (LONGITUD_MAXIMA - len(".xlsx")) + ".xlsx"


def test_el_limite_exacto_no_se_toca_y_uno_mas_si():
    justo = "b" * (LONGITUD_MAXIMA - 4) + ".csv"
    assert nombre_seguro(justo) == justo
    uno_mas = "b" * (LONGITUD_MAXIMA - 3) + ".csv"
    assert len(nombre_seguro(uno_mas)) == LONGITUD_MAXIMA


def test_una_extension_larguisima_tambien_se_acota():
    resultado = nombre_seguro("x." + "e" * 5000)
    assert len(resultado) <= LONGITUD_MAXIMA


def test_guardar_escribe_dentro_de_la_carpeta_y_devuelve_la_ruta(tmp_path):
    carpeta = tmp_path / "destino"
    carpeta.mkdir()
    ruta = guardar_subida(carpeta, Subida("..\\..\\evil.csv", b"hola"))
    assert ruta == carpeta / "evil.csv"
    assert ruta.read_bytes() == b"hola"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["destino"]  # nada se escapo


@pytest.mark.parametrize(
    "nombre", ["../fuera.csv", "..\\fuera.csv", "/tmp/fuera.csv", "C:\\fuera.csv", "CON.csv"]
)
def test_guardar_nunca_deja_archivos_fuera_de_la_carpeta(tmp_path, nombre):
    carpeta = tmp_path / "destino"
    carpeta.mkdir()
    ruta = guardar_subida(carpeta, Subida(nombre))
    assert ruta.parent == carpeta
    assert ruta.is_file()
    assert [p.name for p in tmp_path.iterdir()] == ["destino"]
    assert len(list(carpeta.iterdir())) == 1


def test_guardar_con_nombre_vacio_no_escribe_nada(tmp_path):
    with pytest.raises(ValueError, match="nombre utilizable"):
        guardar_subida(tmp_path, Subida(""))
    assert list(tmp_path.iterdir()) == []


# --- las tres pantallas con subida usan la funcion unica ---------------------------------------

PAGINAS_CON_SUBIDA = ("actualizacion", "elaborar", "visor")


@pytest.mark.parametrize("pagina", PAGINAS_CON_SUBIDA)
def test_las_pantallas_con_subida_usan_el_guardado_seguro(pagina):
    texto = (RAIZ / "ui" / "paginas" / f"{pagina}.py").read_text(encoding="utf-8")
    assert "guardar_subida(" in texto
    assert "from ui.subidas import" in texto


@pytest.mark.parametrize("pagina", PAGINAS_CON_SUBIDA)
def test_ninguna_pantalla_une_el_nombre_del_cliente_a_una_carpeta(pagina):
    texto = (RAIZ / "ui" / "paginas" / f"{pagina}.py").read_text(encoding="utf-8")
    assert "/ archivo.name" not in texto
