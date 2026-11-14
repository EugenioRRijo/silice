"""El presupuesto en PDF (RF-213, ola 2 línea 4, 2026-11-13): el documento y su dibujo.

Dos capas, cada una con su oráculo escrito a mano:

- `pdf_en_bytes` dibuja un `DocumentoPdf` FICTICIO construido aquí: el texto que se extrae del PDF
  con pdfplumber (otra biblioteca, no la que lo escribe) trae cada cifra y cada tilde tal cual,
  el encabezado de la tabla en cada página, «Página n de N» y el texto del usuario sin
  interpretarlo como marcas (`<b>&`).
- `documento_de_la_hoja` arma el documento desde el borrador vivo de OF-001: total 2 703,86 USD
  (memoria de OF-001), IVA 16 % = 432,62 y 3 136,48 con IVA (a mano: 2 703,86 × 0,16 = 432,6176);
  AF-LLAVE con PU 13,198738025 (memoria, NORMAS §4) que se lee 13,20 y 3 × PU = 39,60.
"""

from __future__ import annotations

import io
import shutil
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pdfplumber
import pytest

from aplicacion import hoja
from aplicacion.hoja_borradores import Registro
from aplicacion.presupuesto_pdf import (
    ApuDelPdf,
    DocumentoPdf,
    Encabezado,
    Grupo,
    LineaDeCierre,
    PartidaSinApu,
    Renglon,
    TablaDeApu,
    documento_de_la_hoja,
    nombre_del_pdf,
    pdf_en_bytes,
    sin_agrupar,
)
from core.catalog import Catalogo, abrir_sesion, crear_motor
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001

D = Decimal
HOY = date(2026, 11, 13)
PARAMETROS = "FCAS 6 · Bono de alimentación 5,81 · Administración 15 % · Utilidad 10 %"


def _texto(contenido: bytes) -> list[str]:
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        return [pagina.extract_text() or "" for pagina in pdf.pages]


def _renglon(n: int, descripcion: str = "") -> Renglon:
    return Renglon(
        numero=str(n),
        partida=f"FIC-{n:03d}",
        descripcion=descripcion or f"Partida número {n}: excavación",
        unidad="m³",
        cantidad="1.234,5",
        precio_unitario="12.345,67",
        total=f"{n}.000,00",
    )


def _documento(renglones: int = 3, grupos: tuple[Grupo, ...] | None = None) -> DocumentoPdf:
    filas = tuple(_renglon(n) for n in range(1, renglones + 1))
    return DocumentoPdf(
        encabezado=Encabezado(
            titulo="Presupuesto",
            obra="Obra ficticia «El Ñandú»",
            version="Versión 002",
            fecha="13/11/2026",
            emitido="13/11/2026",
            moneda="USD",
            notas=("Versión 002 con 1 cambio sin guardar.",),
        ),
        grupos=grupos if grupos is not None else (Grupo("", filas, None),),
        totales=(
            LineaDeCierre("Subtotal sin IVA", "6.000,00"),
            LineaDeCierre("IVA (16 %)", "960,00"),
            LineaDeCierre("Total con IVA", "6.960,00"),
        ),
        notas_finales=("La alícuota del IVA: a cotejar con la Gaceta vigente.",),
        apus=(
            ApuDelPdf(
                codigo="FIC-001",
                descripcion="Concreto f'c ≤ 250 kgf/cm² <b>&</b> curado",
                unidad="m³",
                rendimiento="12,5",
                parametros=PARAMETROS,
                tablas=(
                    TablaDeApu(
                        "Materiales",
                        ("Descripción", "Unidad", "Cantidad", "Precio"),
                        (("Cemento gris ficticio", "saco", "7,5", "10,20"),),
                        "76,50",
                    ),
                    TablaDeApu(
                        "Equipos", ("Descripción", "Cantidad", "Precio", "Depreciación"), (), "0,00"
                    ),
                ),
                cierre=(
                    LineaDeCierre("= Costo directo", "76,50"),
                    LineaDeCierre("+ Administración", "11,48"),
                    LineaDeCierre("= Precio unitario", "96,78"),
                ),
            ),
        ),
    )


# --- el dibujo -----------------------------------------------------------------------------------


def test_el_pdf_trae_el_encabezado_las_partidas_y_los_totales_con_coma_decimal_y_tildes():
    contenido = pdf_en_bytes(_documento())
    assert contenido.startswith(b"%PDF-")
    paginas = _texto(contenido)
    todo = "\n".join(paginas)
    for esperado in (
        "Presupuesto",
        "Obra ficticia «El Ñandú»",
        "Versión 002",
        "Fecha del presupuesto: 13/11/2026",
        "Moneda: USD",
        "Versión 002 con 1 cambio sin guardar.",
        "FIC-002",
        "Partida número 2: excavación",
        "m³",
        "1.234,5",
        "12.345,67",
        "3.000,00",
        "Subtotal sin IVA",
        "IVA (16 %)",
        "960,00",
        "Total con IVA",
        "6.960,00",
        "La alícuota del IVA: a cotejar con la Gaceta vigente.",
    ):
        assert esperado in todo, esperado
    assert "Precio unitario (USD)" in paginas[0] and "Total (USD)" in paginas[0]


def test_el_apu_va_en_su_pagina_con_sus_grupos_y_el_texto_del_usuario_no_es_marcado():
    paginas = _texto(pdf_en_bytes(_documento()))
    apu = paginas[-1]
    assert "Análisis de precio unitario" in apu
    assert "FIC-001" in apu
    # «<b>&</b>» es texto de la persona: se ve tal cual, no se interpreta como negrita
    assert "Concreto f'c ≤ 250 kgf/cm² <b>&</b> curado" in apu
    assert "Rendimiento: 12,5 m³ por día" in apu
    assert PARAMETROS in apu
    for esperado in ("Materiales", "Cemento gris ficticio", "7,5", "10,20", "76,50", "Equipos"):
        assert esperado in apu, esperado
    assert "Sin líneas" in apu  # Equipos vacío lo dice
    assert "+ Administración" in apu and "= Precio unitario" in apu and "96,78" in apu
    assert not any("Análisis de precio unitario" in p for p in paginas[:-1])


def test_con_150_partidas_el_encabezado_de_la_tabla_se_repite_y_cada_pagina_se_numera():
    paginas = _texto(pdf_en_bytes(replace(_documento(150), apus=())))
    assert len(paginas) >= 3
    for n, pagina in enumerate(paginas, start=1):
        assert f"Página {n} de {len(paginas)}" in pagina
        assert "Obra ficticia «El Ñandú»" in pagina  # el pie dice de qué obra es la hoja suelta
    for pagina in paginas[:-1]:
        assert "Descripción" in pagina and "Precio unitario (USD)" in pagina
    todo = "\n".join(paginas)
    assert all(f"FIC-{n:03d}" in todo for n in range(1, 151))


def test_una_descripcion_larga_se_parte_en_lineas_y_no_se_corta():
    largo = " ".join(f"palabra{n}" for n in range(60))
    documento = replace(_documento(1), grupos=(Grupo("", (_renglon(1, largo),), None),), apus=())
    todo = " ".join(_texto(pdf_en_bytes(documento))).split()
    assert all(f"palabra{n}" in todo for n in range(60))


def test_los_grupos_llevan_su_titulo_y_su_subtotal():
    """El punto de extensión del agrupado (por frente, en otra línea): cada grupo con su título y
    su subtotal; aquí se dibujan dos grupos ficticios."""
    grupos = (
        Grupo("Frente A: acceso norte", (_renglon(1), _renglon(2)), "3.000,00"),
        Grupo("Frente B: acceso sur", (_renglon(3),), "3.000,00"),
    )
    todo = "\n".join(_texto(pdf_en_bytes(replace(_documento(grupos=grupos), apus=()))))
    assert "Frente A: acceso norte" in todo and "Frente B: acceso sur" in todo
    assert todo.count("Subtotal de Frente") == 2


def test_el_nombre_del_pdf_es_seguro():
    assert nombre_del_pdf(None) == "presupuesto_borrador.pdf"
    assert nombre_del_pdf("001") == "presupuesto_001.pdf"
    assert nombre_del_pdf("001", partida="AF-LLAVE") == "apu_001_AF-LLAVE.pdf"
    assert nombre_del_pdf('a"\r\nc/d', partida="x/y") == "apu_a___c_d_x_y.pdf"
    assert len(nombre_del_pdf("ab" * 50_000, partida="c" * 50_000)) <= 260


# --- el documento desde la hoja ------------------------------------------------------------------


@pytest.fixture(scope="module")
def _of001(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("presupuesto_pdf")
    copia = carpeta / "copia.db"
    shutil.copyfile(plantilla_of001(carpeta / "of001.db"), copia)
    motor = crear_motor(f"sqlite:///{Path(copia).as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return hoja.abrir_version(
                sesion, Catalogo(sesion), NOMBRE_OF001, "001", fecha_evaluacion=HOY
            )
    finally:
        motor.dispose()


def _vivo(abierta, borrador=None, version="001"):
    return Registro().crear(
        "f", "caso", NOMBRE_OF001, version, borrador or abierta.borrador, abierta
    )


def test_el_documento_de_of001_trae_las_30_partidas_el_total_y_el_iva_de_la_memoria(_of001):
    documento = documento_de_la_hoja(_vivo(_of001), HOY)
    assert documento.encabezado.obra == NOMBRE_OF001
    assert documento.encabezado.version == "Versión 001"
    assert documento.encabezado.moneda == "USD"
    assert documento.encabezado.emitido == "13/11/2026"
    (grupo,) = documento.grupos
    assert grupo.titulo == "" and grupo.subtotal is None
    assert len(grupo.renglones) == 30
    assert [r.numero for r in grupo.renglones] == [str(n) for n in range(1, 31)]
    llave = next(r for r in grupo.renglones if r.partida == "AF-LLAVE")
    assert (llave.cantidad, llave.precio_unitario, llave.total) == ("3", "13,20", "39,60")
    assert documento.totales == (
        LineaDeCierre("Subtotal sin IVA", "2.703,86"),
        LineaDeCierre("IVA (16 %)", "432,62"),
        LineaDeCierre("Total con IVA", "3.136,48"),
    )
    assert len(documento.apus) == 30


def test_cada_apu_trae_sus_tres_grupos_sus_montos_es_ve_y_el_cierre_con_tildes(_of001):
    documento = documento_de_la_hoja(_vivo(_of001), HOY)
    llave = next(a for a in documento.apus if a.codigo == "AF-LLAVE")
    assert [t.rotulo for t in llave.tablas] == ["Materiales", "Equipos", "Mano de obra"]
    conceptos = [c.concepto for c in llave.cierre]
    assert "+ Administración" in conceptos and "= Con administración" in conceptos
    assert llave.cierre[-1] == LineaDeCierre("= Precio unitario", "13,20")
    assert llave.cierre[3] == LineaDeCierre("= Costo directo", "10,43")  # 10,433785
    for tabla in llave.tablas:
        for fila in tabla.filas:
            assert not any("." in celda and celda.replace(".", "").isdigit() for celda in fila)


def test_un_borrador_editado_lo_dice_y_trae_el_total_del_borrador_vivo(_of001):
    borrador = replace(
        _of001.borrador,
        parametros=replace(_of001.borrador.parametros, administracion=D("0.20")),
    )
    documento = documento_de_la_hoja(_vivo(_of001, borrador), HOY)
    assert documento.totales[0] == LineaDeCierre("Subtotal sin IVA", "2.821,42")
    assert "Versión 001 con 1 cambio sin guardar." in documento.encabezado.notas
    assert "Administración 20 %" in documento.apus[0].parametros


def test_con_partida_solo_va_su_apu_y_sin_ella_es_partida_sin_apu(_of001):
    documento = documento_de_la_hoja(_vivo(_of001), HOY, partida="AF-LLAVE")
    assert documento.grupos == () and documento.totales == ()
    assert [a.codigo for a in documento.apus] == ["AF-LLAVE"]
    assert documento.encabezado.titulo == "Análisis de precio unitario"
    with pytest.raises(PartidaSinApu, match="NO-EXISTE"):
        documento_de_la_hoja(_vivo(_of001), HOY, partida="NO-EXISTE")


def test_un_borrador_sin_version_lo_dice():
    vivo = Registro().crear("f", "c", "Obra nueva ficticia", None, hoja.Borrador(fecha=HOY), None)
    documento = documento_de_la_hoja(vivo, HOY)
    assert documento.encabezado.version == "Borrador sin guardar"
    assert documento.grupos[0].renglones == ()
    assert documento.totales[0] == LineaDeCierre("Subtotal sin IVA", "0,00")
    assert pdf_en_bytes(documento).startswith(b"%PDF-")


def test_el_agrupador_reparte_los_renglones_y_el_servidor_suma_cada_subtotal(_of001):
    """El punto de extensión: un agrupador ficticio por el prefijo del código (AF, DT, EL...)."""

    def por_prefijo(filas):
        grupos: dict[str, list] = {}
        for fila in filas:
            grupos.setdefault(fila.partida.split("-")[0], []).append(fila)
        return [(f"Grupo {k}", v) for k, v in grupos.items()]

    documento = documento_de_la_hoja(_vivo(_of001), HOY, agrupar=por_prefijo)
    assert len(documento.grupos) > 1
    assert sum(len(g.renglones) for g in documento.grupos) == 30
    suma = sum(D(g.subtotal.replace(".", "").replace(",", ".")) for g in documento.grupos)
    assert abs(suma - D("2703.86")) <= D("0.02")
    # la numeración sigue de un grupo al otro
    numeros = [r.numero for g in documento.grupos for r in g.renglones]
    assert numeros == [str(n) for n in range(1, 31)]
    assert sin_agrupar([]) == [("", [])]


def test_un_control_un_sustituto_suelto_o_una_letra_que_vera_no_tiene_no_rompen_el_pdf():
    raro = "Tubo\x00 de \ud800 cobre 中 → fin"
    base = _documento(1)
    documento = replace(
        base,
        encabezado=replace(base.encabezado, obra=f"Obra {raro}"),  # también el título y el pie
        grupos=(Grupo("", (_renglon(1, raro),), None),),
        apus=(),
    )
    todo = "\n".join(_texto(pdf_en_bytes(documento)))
    assert "Tubo" in todo and "cobre" in todo and "fin" in todo
    assert "Obra Tubo" in todo


def test_un_sustituto_suelto_en_una_celda_corta_del_apu_tampoco_rompe_el_pdf():
    """La unidad y la modalidad del APU van como texto llano en la tabla (no como párrafo)."""
    raro = "m\ud800x"
    base = _documento(1)
    (apu,) = base.apus
    tabla = replace(apu.tablas[0], filas=(("Cemento", raro, "7,5", "10,20"),))
    documento = replace(base, apus=(replace(apu, tablas=(tabla, *apu.tablas[1:])),))
    assert "Cemento" in "\n".join(_texto(pdf_en_bytes(documento)))


def test_las_cifras_del_apu_se_leen_con_coma_decimal_y_punto_de_miles(_of001):
    """Hallazgo de Hydrogen (2026-11-13): las celdas del APU ya vienen en es-VE («1.000», «10,5»);
    leerlas con `Decimal` daba 1 por 1.000 y dejaba «10,5» sin sus dos decimales."""
    composicion = _of001.borrador.composiciones["AF-LLAVE"]
    primera, *resto = composicion.materiales
    lineas = (
        replace(primera, cantidad=D("1000"), precio=D("1000")),
        replace(primera, descripcion="Otra ficticia", cantidad=D("2"), precio=D("10.5")),
        *resto,
    )
    borrador = replace(
        _of001.borrador,
        composiciones={
            **_of001.borrador.composiciones,
            "AF-LLAVE": replace(composicion, materiales=lineas),
        },
    )
    documento = documento_de_la_hoja(_vivo(_of001, borrador), HOY, partida="AF-LLAVE")
    filas = documento.apus[0].tablas[0].filas
    assert filas[0][2:] == ("1.000", "1.000,00")
    assert filas[1][2:] == ("2", "10,50")
