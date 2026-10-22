"""Remedio del limite abierto de VB-1 (expediente
`docs/bitacora/2026-10-21-VB1-expediente-core.md`).

Una version sellada ANTES de VB-1 con una cifra de 29 decimales abre sin «cadena rota», pero
Entregar produciria un `presupuesto.json` cuantizado cuya huella no es la sellada (verificable
pero irrevisable). Remedio: `cadena.formato_de_sellado` la reconoce y `entregar` la rechaza con un
mensaje claro; hay que confirmar una version nueva.

Oraculos: textos literales de 1/12 a 28 y 29 decimales escritos a mano.
"""

from __future__ import annotations

import io
import json
import threading
import zipfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from aplicacion import entrega
from core import models
from core.budget import cadena, canonico
from core.catalog import abrir_sesion
from core.models.cadena import EslabonVersion
from tests.fixtures.canonico_minimo import USUARIO
from tests.fixtures.instalacion import instalacion
from tests.fixtures.vb1_fraccionario import UN_DOCEAVO_28, UN_DOCEAVO_29, sembrar_fraccionaria

CUANDO = datetime(2026, 11, 10, 9, 30)
AVISO = (
    "se selló antes de la corrección de cifras y no puede entregarse tal cual; confirme una "
    "versión nueva (quedará sellada con la cifra corregida) y entregue esa."
)


def _legada(caso):
    with canonico.formato_legado():
        return sembrar_fraccionaria(caso, anexos_de=entrega.anexos_de_cadena)


def _entregar(caso, bd, version):
    return entrega.entregar(
        caso, bd, version, usuario=USUARIO, ahora=CUANDO, version_silice="0.8.0"
    )


def test_entregar_una_version_sellada_antes_se_rechaza_con_el_aviso(motor, tmp_path: Path) -> None:
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "emisor") as bd:
        _, version = _legada(caso)
        with pytest.raises(entrega.EntregaRechazada) as error:
            _entregar(caso, bd, version)
    assert f"La versión {version.codigo} {AVISO}" == str(error.value)


def test_la_misma_version_sellada_con_formato_actual_entrega_y_verifica(
    motor, tmp_path: Path
) -> None:
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "emisor") as bd:
        proyecto, version = sembrar_fraccionaria(caso, anexos_de=entrega.anexos_de_cadena)
        assert cadena.formato_de_sellado(caso, version) == "actual"
        e = _entregar(caso, bd, version)
        assert cadena.verificar_cadena(caso, proyecto, anexos_de=entrega.anexos_de_cadena).integra
    assert UN_DOCEAVO_28.encode() in zipfile.ZipFile(io.BytesIO(e.datos)).read("presupuesto.json")


def test_formato_de_sellado_distingue_actual_legado_y_roto(motor) -> None:
    with abrir_sesion(motor) as caso:
        _, version = _legada(caso)
        assert cadena.formato_de_sellado(caso, version) == "legado"


def test_una_version_legada_alterada_es_rota(motor) -> None:
    with abrir_sesion(motor) as caso:
        proyecto, version = _legada(caso)
        fila = caso.scalars(
            select(models.PartidaPresupuestada).where(
                models.PartidaPresupuestada.presupuesto_id == version.id
            )
        ).one()
        fila.materiales = Decimal("15")
        caso.flush()
        assert cadena.formato_de_sellado(caso, version) == "roto"
        assert not cadena.verificar_cadena(caso, proyecto).integra


def test_alterar_solo_el_decimal_29_de_la_cifra_legada_se_detecta(motor) -> None:
    with abrir_sesion(motor) as caso:
        proyecto, version = _legada(caso)
        fila = caso.scalars(
            select(models.PartidaPresupuestada).where(
                models.PartidaPresupuestada.presupuesto_id == version.id
            )
        ).one()
        assert fila.equipos == Decimal(UN_DOCEAVO_29)  # la base guarda los 29 decimales
        fila.equipos = Decimal(UN_DOCEAVO_29[:-1] + "4")  # solo cambia el decimal 29
        caso.flush()
        assert canonico.texto_decimal(fila.equipos) == UN_DOCEAVO_28  # la forma actual no lo ve
        assert cadena.formato_de_sellado(caso, version) == "roto"
        resultado = cadena.verificar_cadena(caso, proyecto)
        assert not resultado.integra
        assert resultado.fallo is not None and resultado.fallo.motivo == "contenido"


def test_el_resumen_de_entrega_avisa_antes_de_pedir_la_contrasena(motor, tmp_path: Path) -> None:
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "emisor") as bd:
        _, version = _legada(caso)
        resumen = entrega.resumen_de_entrega(caso, bd, version)
        assert resumen.cadena_integra  # la base abre: no es una cadena rota
        assert not resumen.entregable
        assert AVISO in resumen.mensaje_de_cadena


def test_el_resumen_de_una_version_actual_es_entregable(motor, tmp_path: Path) -> None:
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "emisor") as bd:
        _, version = sembrar_fraccionaria(caso, anexos_de=entrega.anexos_de_cadena)
        resumen = entrega.resumen_de_entrega(caso, bd, version)
    assert resumen.entregable
    assert "selló antes" not in resumen.mensaje_de_cadena


def test_tras_una_excepcion_dentro_de_formato_legado_se_vuelve_a_cuantizar() -> None:
    uno_doceavo = Decimal(1) / Decimal(12)
    with pytest.raises(RuntimeError):
        with canonico.formato_legado():
            assert canonico.texto_decimal(uno_doceavo) == UN_DOCEAVO_29
            raise RuntimeError("falla dentro del contexto")
    assert canonico.texto_decimal(uno_doceavo) == UN_DOCEAVO_28


def test_formato_legado_no_se_filtra_a_otro_hilo() -> None:
    uno_doceavo = Decimal(1) / Decimal(12)
    abierto, visto = threading.Event(), threading.Event()
    en_otro_hilo: list[str | None] = []

    def lector() -> None:
        abierto.wait(5)
        en_otro_hilo.append(canonico.texto_decimal(uno_doceavo))
        visto.set()

    hilo = threading.Thread(target=lector)
    hilo.start()
    with canonico.formato_legado():
        abierto.set()
        assert visto.wait(5)
        assert canonico.texto_decimal(uno_doceavo) == UN_DOCEAVO_29
    hilo.join(5)
    assert en_otro_hilo == [UN_DOCEAVO_28]


def test_el_total_del_manifiesto_cabe_en_el_patron_estricto(motor, tmp_path: Path) -> None:
    """Hallazgo 4: el total sale de `sum(r.total)`; si fuera fraccionario debe ser leible."""
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "emisor") as bd:
        _, version = sembrar_fraccionaria(caso, anexos_de=entrega.anexos_de_cadena)
        fila = caso.scalars(
            select(models.PartidaPresupuestada).where(
                models.PartidaPresupuestada.presupuesto_id == version.id
            )
        ).one()
        fila.total = Decimal(1) / Decimal(12)  # 29 decimales
        caso.flush()
        caso.delete(caso.get(EslabonVersion, version.id))  # se vuelve a sellar con ese total
        caso.flush()
        cadena.sellar_version(caso, version, USUARIO, anexos_de=entrega.anexos_de_cadena)
        caso.commit()
        resumen = entrega.resumen_de_entrega(caso, bd, version)
        assert canonico.PATRON_CIFRA.match(canonico.texto_decimal(resumen.total) or "")
        e = _entregar(caso, bd, version)
    manifiesto = json.loads(zipfile.ZipFile(io.BytesIO(e.datos)).read("manifiesto.json"))
    assert canonico.PATRON_CIFRA.match(manifiesto["total"])
