"""UC-01, flujo 2a (INV-089): una fuente ilegible o de otro dominio se rechaza con archivo y fila.

La ERS (UC-01 2a) pide que el sistema rechace la carga, no cree el presupuesto e indique el archivo
y el elemento o fila que fallo. Antes de C5 solo tenian prueba un CSV de telecom con una longitud
vacia y el CSV civil sin zanja o con dos diametros. Estas pruebas cubren lo que faltaba, cada caso
con una fuente ilegible real escrita en `tmp_path`:

- un IFC que no es STEP (binario, vacio o un CSV) y un STEP que ifcopenshell no abre (cabecera
  danada o esquema no soportado), en el adaptador civil IFC;
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


MUESTRA_IFC = MUESTRAS / "tanquilla.ifc"

#: Archivos con extension `.ifc` que no son STEP: no empiezan con `ISO-10303-21`.
IFC_QUE_NO_ES_STEP = {
    "binario": b"\x00\xff\xfe basura binaria que no es STEP \x00",
    "vacio": b"",
    "csv-con-extension-ifc": MUESTRA_CIVIL.read_bytes(),
}

#: Archivos STEP (cabecera `ISO-10303-21` valida) que ifcopenshell no puede abrir, con la parte
#: del motivo que el mensaje debe dar. El esquema no soportado es la muestra con
#: `FILE_SCHEMA(('IFC9'))`.
IFC_STEP_DANADO = {
    "cabecera-danada": (b"ISO-10303-21;\nHEADER;\n@@@ basura $$$ \x00\xff\nENDSEC;\n", "cabecera"),
    "solo-la-palabra-inicial": (b"ISO-10303-21;", "cabecera"),
    "con-bom-y-cabecera-danada": (b"\xef\xbb\xbfISO-10303-21;\nHEADER;\n@@@\n", "cabecera"),
    "esquema-no-soportado": (
        MUESTRA_IFC.read_bytes().replace(b"FILE_SCHEMA(('IFC4'))", b"FILE_SCHEMA(('IFC9'))"),
        "esquema",
    ),
}


def _extraer_ifc(ruta: Path) -> None:
    pytest.importorskip("ifcopenshell")
    from adapters.civil.ifc import AdaptadorCivilIFC

    AdaptadorCivilIFC().extraer(ruta)


@pytest.mark.parametrize("caso", sorted(IFC_QUE_NO_ES_STEP))
def test_un_ifc_que_no_es_step_se_rechaza_nombrando_el_archivo(tmp_path, caso):
    ruta = tmp_path / f"{caso}.ifc"
    ruta.write_bytes(IFC_QUE_NO_ES_STEP[caso])

    with pytest.raises(ValueError) as error:
        _extraer_ifc(ruta)

    assert ruta.name in str(error.value)
    assert "no es un modelo IFC" in str(error.value)


@pytest.mark.parametrize("caso", sorted(IFC_STEP_DANADO))
def test_un_step_que_ifcopenshell_no_abre_se_rechaza_con_archivo_y_motivo(tmp_path, caso):
    """La cabecera STEP es valida, asi que pasa la primera comprobacion; lo rechaza el estado con
    que ifcopenshell abre el archivo (T-1 de la revision de la pista P).

    El archivo tiene un nombre neutro, `modelo.ifc`: con el nombre del caso («cabecera-danada»,
    «esquema-no-soportado»), el mensaje contendria el motivo aunque no lo diera (T-7).
    """
    contenido, motivo = IFC_STEP_DANADO[caso]
    assert contenido != MUESTRA_IFC.read_bytes(), "la muestra no se altero"
    ruta = tmp_path / "modelo.ifc"
    assert motivo not in ruta.name
    ruta.write_bytes(contenido)

    with pytest.raises(ValueError) as error:
        _extraer_ifc(ruta)

    assert ruta.name in str(error.value)
    assert "ilegible como modelo IFC" in str(error.value)
    assert motivo in str(error.value)


@pytest.mark.parametrize(
    "caso",
    [f"no-step:{caso}" for caso in sorted(IFC_QUE_NO_ES_STEP)]
    + [f"step:{caso}" for caso in sorted(IFC_STEP_DANADO)],
)
def test_rechazar_estos_ifc_no_deja_excepciones_no_atrapables(tmp_path, monkeypatch, caso):
    """Cubre exactamente los archivos de `IFC_QUE_NO_ES_STEP` e `IFC_STEP_DANADO`.

    Con `ifcopenshell.open`, ifcopenshell 0.8.5 deja a medio construir el objeto del archivo que no
    pudo abrir, y su `__del__` lanza un `KeyError` que Python solo puede reportar por
    `sys.unraisablehook`; con `-W error` rompe la prueba que este corriendo cuando el recolector
    lo libere, que puede ser cualquier otra. El adaptador no construye ese objeto
    (`adapters/civil/ifc.py`, `_abrir_modelo`). Aqui se libera la excepcion, se recolecta y se
    comprueba que el gancho, sustituido solo durante esta prueba, no recibio nada.

    No cubre un STEP de cuerpo truncado o con basura: ifcopenshell lo abre sin error (limite
    declarado en `_abrir_modelo`), asi que no hay rechazo que probar.
    """
    grupo, nombre = caso.split(":")
    contenido = IFC_QUE_NO_ES_STEP[nombre] if grupo == "no-step" else IFC_STEP_DANADO[nombre][0]
    ruta = tmp_path / f"{nombre}.ifc"
    ruta.write_bytes(contenido)
    no_atrapables = []
    monkeypatch.setattr(sys, "unraisablehook", no_atrapables.append)

    def _rechazar() -> None:
        try:
            _extraer_ifc(ruta)
        except ValueError:
            return
        pytest.fail(f"{ruta.name} no se rechazo con ValueError")

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
        ("civil", MUESTRA_TELECOM),
        ("telecom", MUESTRA_INDUSTRIAL),
        ("industrial", MUESTRA_SISTEMAS),
        ("sistemas", MUESTRA_TELECOM),
    ],
    ids=[
        "civil<-industrial",
        "civil<-telecom",
        "telecom<-industrial",
        "industrial<-sistemas",
        "sistemas<-telecom",
    ],
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
    assert f"no es una fuente del dominio {dominio}" in mensaje
    # Solo el nombre: la ruta (en la API, un directorio temporal del servidor) no se expone (T-4).
    assert "/" not in mensaje and "\\" not in mensaje, mensaje


@pytest.mark.parametrize("dominio", sorted(_ADAPTADORES_TABULARES))
def test_un_archivo_binario_se_rechaza_nombrando_el_archivo(tmp_path, dominio):
    ruta = tmp_path / "planos_escaneados.csv"
    ruta.write_bytes(b"%PDF-1.7\r\n%\xb5\xb5\xb5\xb5\r\n1 0 obj\r\n<</Type/Catalog>>\r\n\xff\xfe")

    with pytest.raises(ValueError) as error:
        _ADAPTADORES_TABULARES[dominio]().extraer(ruta)

    assert "planos_escaneados.csv" in str(error.value)


# ---------------------------------------------------------------------------------------------
# Filas cortas y celdas de telecom (T-2 y T-3 de la revision de la pista P de C5)
# ---------------------------------------------------------------------------------------------


def _muestra_con_lineas(origen: Path, destino: Path, *lineas: str) -> Path:
    """La muestra `origen` con `lineas` anadidas al final, escrita en `destino`."""
    texto = origen.read_text(encoding="utf-8").rstrip("\n")
    destino.write_text("\n".join([texto, *lineas]) + "\n", encoding="utf-8")
    return destino


def test_civil_una_fila_corta_falla_con_archivo_y_fila(tmp_path):
    """Una fila con menos celdas que la cabecera (aqui, solo el `id`): `csv.DictReader` pone `None`
    en las que faltan, y antes `None.strip()` daba un `AttributeError` (500 en la API)."""
    ruta = _muestra_con_lineas(MUESTRA_CIVIL, tmp_path / "civil_corto.csv", "T-02")

    with pytest.raises(ValueError) as error:
        AdaptadorCivilTabular(codigos=CODIGOS).extraer(ruta)

    mensaje = str(error.value)
    assert "civil_corto.csv" in mensaje
    assert "'T-02'" in mensaje
    assert "tipo de fila no reconocido" in mensaje


def test_telecom_una_celda_mal_formada_nombra_archivo_fila_y_columna(tmp_path):
    lineas = MUESTRA_TELECOM.read_text(encoding="utf-8").splitlines()
    # SW-CORE es un nodo con cantidad 1 (data/samples/telecom/topologia_arenaza.csv, linea 3).
    assert lineas[2].startswith("nodo,SW-CORE,") and lineas[2].split(",")[5] == "1"
    celdas = lineas[2].split(",")
    celdas[5] = "uno"
    lineas[2] = ",".join(celdas)
    ruta = tmp_path / "red_mala.csv"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    with pytest.raises(ValueError) as error:
        AdaptadorTelecom().extraer(ruta)

    mensaje = str(error.value)
    assert "red_mala.csv" in mensaje
    assert "'SW-CORE'" in mensaje
    assert "linea 3" in mensaje
    assert "'cantidad'" in mensaje


def test_telecom_una_fila_corta_se_identifica_por_su_linea_y_no_por_none(tmp_path):
    """En telecom el `id` es la segunda columna: una fila con solo el tipo no lo trae."""
    total_lineas = len(MUESTRA_TELECOM.read_text(encoding="utf-8").splitlines())
    ruta = _muestra_con_lineas(MUESTRA_TELECOM, tmp_path / "red_corta.csv", "nodo")

    with pytest.raises(ValueError) as error:
        AdaptadorTelecom().extraer(ruta)

    mensaje = str(error.value)
    assert "red_corta.csv" in mensaje
    assert f"linea {total_lineas + 1}" in mensaje
    assert "None" not in mensaje


@pytest.mark.parametrize(
    ("reemplazo", "motivo"),
    [
        (b"IFCPROPERTYSINGLEVALUE('Unidad',$,IFCLABEL('kg'),$)", "no sabe que tipo de cantidad"),
        (b"IFCPROPERTYSINGLEVALUE('Unidad',$,IFCLABEL('m2'),$)", "no se encontro una cantidad"),
    ],
    ids=["unidad-sin-cantidad-ifc", "unidad-sin-su-cantidad-en-el-elemento"],
)
def test_un_elemento_ifc_que_falla_nombra_el_archivo_y_no_su_ruta(tmp_path, reemplazo, motivo):
    """UC-01 2a en un elemento del modelo: el mensaje da el nombre del archivo, no su ruta (T-4)."""
    original = b"IFCPROPERTYSINGLEVALUE('Unidad',$,IFCLABEL('m3'),$)"
    muestra = MUESTRA_IFC.read_bytes()
    assert muestra.count(original) == 1
    ruta = tmp_path / "tanquilla_mala.ifc"
    ruta.write_bytes(muestra.replace(original, reemplazo))

    with pytest.raises(ValueError) as error:
        _extraer_ifc(ruta)

    mensaje = str(error.value)
    assert motivo in mensaje
    assert "'tanquilla_mala.ifc'" in mensaje
    assert "/" not in mensaje and "\\" not in mensaje, mensaje
