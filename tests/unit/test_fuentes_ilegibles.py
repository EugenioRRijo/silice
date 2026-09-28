"""UC-01, flujo 2a (INV-089): una fuente ilegible o de otro dominio se rechaza con archivo y fila.

La ERS (UC-01 2a) pide que el sistema rechace la carga, no cree el presupuesto e indique el archivo
y el elemento o fila que fallo. Antes de C5 solo tenian prueba un CSV de telecom con una longitud
vacia y el CSV civil sin zanja o con dos diametros. Estas pruebas cubren lo que faltaba, cada caso
con una fuente ilegible real escrita en `tmp_path`:

- un IFC corrupto, vacio o que en realidad es un CSV (el adaptador civil IFC);
- una celda mal formada de industrial, de sistemas y del CSV civil;
- la muestra de otro dominio entregada a cada adaptador tabular;
- un archivo binario (no es texto UTF-8) entregado a cada adaptador tabular.

El rechazo es siempre un `ValueError`: es la excepcion que la API traduce a 422
(`api/main.py`, `manejar_value_error`; su prueba esta en
`tests/integration/test_api_fuentes_ilegibles.py`) y la que la pagina «Elaborar un presupuesto»
muestra. Los oraculos son los nombres de archivo, filas y columnas de las muestras, transcritos de
`data/samples/*/`; el mensaje no se compara entero, solo lo que el flujo 2a exige que indique.
"""

from __future__ import annotations

import gc
import sys
from pathlib import Path

import pytest

from adapters.civil.tabular import AdaptadorCivilTabular
from adapters.industrial.adaptador import AdaptadorIndustrial
from adapters.sistemas.adaptador import AdaptadorSistemas
from adapters.telecom.adaptador import AdaptadorTelecom
from tests.fixtures.computo_civil import CODIGOS

RAIZ = Path(__file__).resolve().parents[2]
MUESTRAS = RAIZ / "data" / "samples"
MUESTRA_CIVIL = MUESTRAS / "civil" / "tanquillas_y_zanja.csv"
MUESTRA_INDUSTRIAL = MUESTRAS / "industrial" / "activos_planta.csv"
MUESTRA_SISTEMAS = MUESTRAS / "sistemas" / "alcance_funcional.csv"
MUESTRA_TELECOM = MUESTRAS / "telecom" / "topologia_arenaza.csv"


def _copia_con_celda(origen: Path, destino: Path, fila_id: str, columna: str, valor: str) -> Path:
    """Copia la muestra `origen` en `destino` cambiando una sola celda de la fila `fila_id`.

    La fila se reconoce por su primera celda (la clave `id` de la muestra civil y la de sistemas,
    `id_activo` de la industrial), y la columna por su nombre en el encabezado; se falla si la
    fila no esta una sola vez, para que la prueba no pase sobre una fuente que no se altero.
    """
    lineas = origen.read_text(encoding="utf-8").splitlines()
    encabezado = lineas[0].split(",")
    indice = encabezado.index(columna)
    alteradas = [lineas[0]]
    cambiadas = 0
    for linea in lineas[1:]:
        celdas = linea.split(",")
        if celdas[0] == fila_id:
            celdas[indice] = valor
            cambiadas += 1
        alteradas.append(",".join(celdas))
    assert cambiadas == 1, f"la fila {fila_id!r} no esta una sola vez en {origen.name}"
    destino.write_text("\n".join(alteradas) + "\n", encoding="utf-8")
    return destino


# ---------------------------------------------------------------------------------------------
# IFC corrupto o ilegible
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nombre", "contenido"),
    [
        ("corrupto.ifc", b"\x00\xff\xfe basura binaria que no es STEP \x00"),
        ("vacio.ifc", b""),
        ("es_un_csv.ifc", MUESTRA_CIVIL.read_bytes()),
    ],
    ids=["binario", "vacio", "csv-con-extension-ifc"],
)
def test_un_ifc_ilegible_se_rechaza_nombrando_el_archivo(tmp_path, nombre, contenido):
    pytest.importorskip("ifcopenshell")
    from adapters.civil.ifc import AdaptadorCivilIFC

    ruta = tmp_path / nombre
    ruta.write_bytes(contenido)

    with pytest.raises(ValueError) as error:
        AdaptadorCivilIFC().extraer(ruta)

    assert nombre in str(error.value)
    assert "IFC" in str(error.value)


def test_un_ifc_ilegible_no_deja_excepciones_no_atrapables(tmp_path, monkeypatch):
    """ifcopenshell deja a medio construir el objeto del archivo que no pudo abrir, y su `__del__`
    lanza un `KeyError` que Python solo puede reportar por `sys.unraisablehook`. Con `-W error`
    esa excepcion rompe la prueba que este corriendo cuando el recolector la libere, que puede
    ser cualquier otra. El rechazo del adaptador no debe dejarla: se libera la excepcion, se
    recolecta y se comprueba que el gancho no recibio nada.
    """
    pytest.importorskip("ifcopenshell")
    from adapters.civil.ifc import AdaptadorCivilIFC

    ruta = tmp_path / "corrupto.ifc"
    ruta.write_bytes(b"\x00\xff\xfe basura binaria que no es STEP \x00")
    no_atrapables = []
    monkeypatch.setattr(sys, "unraisablehook", no_atrapables.append)

    def _rechazar() -> None:
        try:
            AdaptadorCivilIFC().extraer(ruta)
        except ValueError:
            return
        pytest.fail("el IFC corrupto no se rechazo")

    _rechazar()
    gc.collect()

    assert [repr(registro.exc_value) for registro in no_atrapables] == []


# ---------------------------------------------------------------------------------------------
# Celdas mal formadas: el mensaje nombra el archivo, la fila y la columna
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("valor", ["cuatro", ""], ids=["no-numerica", "vacia"])
def test_industrial_una_frecuencia_mal_formada_falla_con_archivo_fila_y_columna(tmp_path, valor):
    ruta = _copia_con_celda(
        MUESTRA_INDUSTRIAL, tmp_path / "activos_malos.csv", "IN-002", "frecuencia_anual", valor
    )

    with pytest.raises(ValueError) as error:
        AdaptadorIndustrial().extraer(ruta)

    mensaje = str(error.value)
    assert "activos_malos.csv" in mensaje
    assert "IN-002" in mensaje
    assert "frecuencia_anual" in mensaje


@pytest.mark.parametrize("valor", ["dos", ""], ids=["no-numerica", "vacia"])
def test_sistemas_un_conteo_mal_formado_falla_con_archivo_fila_y_columna(tmp_path, valor):
    ruta = _copia_con_celda(
        MUESTRA_SISTEMAS, tmp_path / "alcance_malo.csv", "SI-03", "consultas", valor
    )

    with pytest.raises(ValueError) as error:
        AdaptadorSistemas().extraer(ruta)

    mensaje = str(error.value)
    assert "alcance_malo.csv" in mensaje
    assert "SI-03" in mensaje
    assert "consultas" in mensaje


@pytest.mark.parametrize(
    ("fila_id", "columna"),
    [("T-01", "a"), ("Z-01", "longitud")],
    ids=["tanquilla", "zanja"],
)
def test_civil_una_medida_vacia_falla_con_archivo_fila_y_columna(tmp_path, fila_id, columna):
    ruta = _copia_con_celda(MUESTRA_CIVIL, tmp_path / "civil_malo.csv", fila_id, columna, "")

    with pytest.raises(ValueError) as error:
        AdaptadorCivilTabular(codigos=CODIGOS).extraer(ruta)

    mensaje = str(error.value)
    assert "civil_malo.csv" in mensaje
    assert fila_id in mensaje
    assert repr(columna) in mensaje


# ---------------------------------------------------------------------------------------------
# Fuente de otro dominio y fuente binaria
# ---------------------------------------------------------------------------------------------

_ADAPTADORES_TABULARES = {
    "civil": lambda: AdaptadorCivilTabular(codigos=CODIGOS),
    "telecom": AdaptadorTelecom,
    "industrial": AdaptadorIndustrial,
    "sistemas": AdaptadorSistemas,
}


@pytest.mark.parametrize(
    ("dominio", "muestra_ajena"),
    [
        ("civil", MUESTRA_INDUSTRIAL),
        ("telecom", MUESTRA_INDUSTRIAL),
        ("industrial", MUESTRA_SISTEMAS),
        ("sistemas", MUESTRA_TELECOM),
    ],
    ids=["civil<-industrial", "telecom<-industrial", "industrial<-sistemas", "sistemas<-telecom"],
)
def test_la_muestra_de_otro_dominio_se_rechaza_nombrando_archivo_y_dominio(
    tmp_path, dominio, muestra_ajena
):
    ruta = tmp_path / muestra_ajena.name
    ruta.write_bytes(muestra_ajena.read_bytes())

    with pytest.raises(ValueError) as error:
        _ADAPTADORES_TABULARES[dominio]().extraer(ruta)

    mensaje = str(error.value)
    assert muestra_ajena.name in mensaje
    assert dominio in mensaje


@pytest.mark.parametrize("dominio", sorted(_ADAPTADORES_TABULARES))
def test_un_archivo_binario_se_rechaza_nombrando_el_archivo(tmp_path, dominio):
    ruta = tmp_path / "planos_escaneados.csv"
    ruta.write_bytes(b"%PDF-1.7\r\n%\xb5\xb5\xb5\xb5\r\n1 0 obj\r\n<</Type/Catalog>>\r\n\xff\xfe")

    with pytest.raises(ValueError) as error:
        _ADAPTADORES_TABULARES[dominio]().extraer(ruta)

    assert "planos_escaneados.csv" in str(error.value)
