"""Recibir, dictaminar y encontrar la entrega anterior (UC-23, RF-86/87; spec S3 §6.5 y §9).

Una base de caso temporal con las tablas `paq_*` y una `instalacion.db` temporal con la empresa
emisora registrada. El archivo recibido se guarda una vez por SHA-256 (23h). Los SHA-256 esperados
se calculan aparte con `hashlib`."""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from aplicacion import revision
from core.budget.canonico import json_canonico
from core.catalog import abrir_sesion, crear_motor
from paquete import modelo as paq
from seguridad import firma
from seguridad.modelo import EmpresaRegistrada
from tests.fixtures.canonico.ejemplo_v1 import EJEMPLO_V1
from tests.fixtures.instalacion import AHORA, instalacion
from tests.fixtures.paquetes import EMPRESA, paquete

PAR = firma.generar_par()
ANTES = datetime(2026, 11, 3, 9, 0)
DESPUES = datetime(2026, 11, 10, 9, 30)
RECIBIDO = datetime(2026, 11, 12, 10, 0)
ID_1 = "11111111-1111-4111-8111-111111111111"
ID_2 = "22222222-2222-4222-8222-222222222222"


def _doc(**cambios) -> bytes:
    objeto = copy.deepcopy(EJEMPLO_V1)
    objeto.update(cambios)
    return json_canonico(objeto)


def _paquete(emitido: datetime, codigo: str, paquete_id: str, **mas) -> bytes:
    return paquete(
        par=PAR,
        presupuesto=_doc(),
        emitido=emitido,
        codigo=codigo,
        paquete_id=paquete_id,
        anexos={},
        **mas,
    )


@pytest.fixture
def mundo(tmp_path: Path):
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    paq.crear_esquema_paquete(motor)
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "revisor") as bd:
        bd.add(
            EmpresaRegistrada(
                empresa=EMPRESA,
                rif="J-00000000-0",
                publica=PAR.publica,
                huella=firma.huella_completa(PAR.publica),
                estado="activa",
                comprobada_con="Ana, por teléfono",
                metodo="telefono",
                fecha_comprobacion=AHORA,
                registrada_por="admin",
            )
        )
        bd.commit()
        yield caso, bd, tmp_path / "paquetes"
    motor.dispose()


def _recibir(mundo, datos: bytes, nombre: str = "a.silice", **mas):
    caso, bd, carpeta = mundo
    return revision.recibir(
        datos,
        nombre,
        caso=caso,
        instalacion=bd,
        carpeta_paquetes=carpeta,
        revisor="Luis <luis>",
        ahora=RECIBIDO,
        **mas,
    )


def _recibidos(caso) -> int:
    return caso.scalar(select(func.count()).select_from(paq.paq_recibido))


def test_recibir_un_paquete_firmado_lo_verifica_lo_guarda_y_lo_registra_una_vez(mundo) -> None:
    caso, _, carpeta = mundo
    datos = _paquete(DESPUES, "005", ID_1)
    r = _recibir(mundo, datos)
    assert r.verificacion.estado == "verificado" and not r.ya_recibido
    assert r.verificacion.sha256 == hashlib.sha256(datos).hexdigest()
    assert r.ruta.read_bytes() == datos and r.ruta.parent == carpeta
    assert r.ruta.name.startswith(r.verificacion.sha256)
    assert revision.banner_de_version(r) == (
        "Versión 005 del 2026-11-10; es la primera que recibe de este proyecto."
    )
    otra = _recibir(mundo, datos)  # el mismo archivo: no se duplica (23h)
    assert otra.ya_recibido and otra.paquete_id == r.paquete_id
    assert revision.banner_de_version(otra) == (
        "Versión 005 del 2026-11-10; ya recibió este mismo paquete el 2026-11-12."
    )
    assert _recibidos(caso) == 1
    assert len(list(carpeta.iterdir())) == 1


def test_el_registro_guarda_lo_que_dice_el_manifiesto_y_quien_recibio(mundo) -> None:
    caso, _, _ = mundo
    r = _recibir(mundo, _paquete(DESPUES, "005", ID_1, destinatario="Obra Norte"))
    fila = caso.execute(select(paq.paq_recibido)).mappings().one()
    assert (fila["proyecto"], fila["codigo"], fila["paquete_id"], fila["destinatario"]) == (
        "MIN-001",
        "005",
        ID_1,
        "Obra Norte",
    )
    assert (fila["estado"], fila["recibido_por"], fila["fecha"]) == (
        "verificado",
        "Luis <luis>",
        RECIBIDO,
    )
    assert fila["empresa_verificada"] == EMPRESA
    assert fila["huella_clave"] == firma.huella_completa(PAR.publica)
    assert fila["huella_archivo"] == r.verificacion.sha256


def test_un_archivo_que_no_es_un_paquete_se_rechaza_y_no_se_guarda_nada(mundo) -> None:
    caso, _, carpeta = mundo
    r = _recibir(mundo, b"esto no es un zip", "malo.silice")
    assert r.verificacion.estado == "rechazado" and r.paquete_id == 0 and not r.ya_recibido
    assert _recibidos(caso) == 0
    assert not carpeta.exists() or not list(carpeta.iterdir())


def test_el_nombre_del_archivo_recibido_no_escapa_de_la_carpeta(mundo) -> None:
    _, _, carpeta = mundo
    datos = _paquete(DESPUES, "005", ID_1)
    r = _recibir(mundo, datos, "..\\..\\afuera.silice")
    assert r.ruta.parent == carpeta and ".." not in r.ruta.name
    assert r.ruta.resolve().is_relative_to(carpeta.resolve())
    assert sorted(p.name for p in carpeta.iterdir()) == [r.ruta.name]
    assert not (carpeta.parent.parent / "afuera.silice").exists()


@pytest.mark.parametrize("nombre", ["../../afuera.silice", "", "C:\\Windows\\x.silice"])
def test_ningun_nombre_hostil_deja_el_archivo_fuera(mundo, nombre: str) -> None:
    _, _, carpeta = mundo
    r = _recibir(mundo, _paquete(DESPUES, "005", ID_1), nombre)
    assert r.ruta.parent == carpeta
    assert r.ruta.resolve().is_relative_to(carpeta.resolve())


def test_sin_la_empresa_registrada_el_paquete_queda_no_verificado(mundo) -> None:
    caso, bd, _ = mundo
    bd.query(EmpresaRegistrada).delete()
    bd.commit()
    r = _recibir(mundo, _paquete(DESPUES, "005", ID_1))
    assert r.verificacion.estado == "no_verificado"
    assert caso.execute(select(paq.paq_recibido.c.estado)).scalar_one() == "no_verificado"


def test_el_dictamen_queda_atado_al_sha256_y_al_estado_de_ese_momento(mundo) -> None:
    caso, _, _ = mundo
    r = _recibir(mundo, _paquete(DESPUES, "005", ID_1))
    revision.dictaminar(
        caso,
        r,
        resultado="con observaciones",
        notas="Falta la memoria de R4",
        revisor="Luis <luis>",
        ahora=RECIBIDO,
        armo=False,
    )
    fila = paq.dictamenes_de(caso, r.verificacion.sha256)[0]
    assert (
        fila["resultado"],
        fila["usuario"],
        fila["estado_verificacion"],
        fila["revisor_armo"],
    ) == ("con observaciones", "Luis <luis>", "verificado", False)
    assert fila["huella_archivo"] == r.verificacion.sha256
    assert fila["paquete_id"] == r.paquete_id


@pytest.mark.parametrize("resultado", ["con observaciones", "rechazado"])
def test_un_dictamen_sin_notas_que_no_es_conforme_se_rechaza_y_no_se_guarda(
    mundo, resultado: str
) -> None:
    caso, _, _ = mundo
    r = _recibir(mundo, _paquete(DESPUES, "005", ID_1))
    with pytest.raises(ValueError, match="necesita notas"):
        revision.dictaminar(
            caso,
            r,
            resultado=resultado,
            notas="  ",
            revisor="Luis <luis>",
            ahora=RECIBIDO,
            armo=False,
        )
    assert not paq.dictamenes_de(caso, r.verificacion.sha256)


def test_un_dictamen_conforme_no_necesita_notas_y_un_resultado_desconocido_no_vale(mundo) -> None:
    caso, _, _ = mundo
    r = _recibir(mundo, _paquete(DESPUES, "005", ID_1))
    revision.dictaminar(
        caso, r, resultado="conforme", notas="", revisor="Luis <luis>", ahora=RECIBIDO, armo=True
    )
    with pytest.raises(ValueError, match="resultado desconocido"):
        revision.dictaminar(
            caso, r, resultado="aprobado", notas="x", revisor="L", ahora=RECIBIDO, armo=False
        )
    [fila] = paq.dictamenes_de(caso, r.verificacion.sha256)
    assert (fila["resultado"], fila["revisor_armo"]) == ("conforme", True)


def test_la_entrega_anterior_es_la_ultima_del_mismo_proyecto_y_emisor_emitida_antes(mundo) -> None:
    caso, bd, _ = mundo
    primera = _recibir(mundo, _paquete(ANTES, "004", ID_2))
    actual = _recibir(mundo, _paquete(DESPUES, "005", ID_1))
    previa = revision.entrega_anterior(caso, bd, actual.verificacion)
    assert previa is not None and previa.codigo == "004"
    assert previa.documento.codigo == "001"
    assert previa.huellas == tuple(
        e["huella_eslabon"] for e in primera.verificacion.cadena["eslabones"]
    )
    assert revision.entrega_anterior(caso, bd, primera.verificacion) is None  # nada antes
    assert revision.banner_de_version(actual).startswith(
        "Versión 005 del 2026-11-10; la última que usted recibió de este proyecto:"
    )


def test_la_entrega_de_otro_emisor_no_es_la_anterior(mundo) -> None:
    """Mismo proyecto, otra clave: §6.5 compara solo con el mismo proyecto Y emisor."""
    caso, bd, _ = mundo
    otro_par = firma.generar_par()
    _recibir(
        mundo,
        paquete(
            par=otro_par,
            presupuesto=_doc(),
            emitido=ANTES,
            codigo="004",
            paquete_id=ID_2,
            anexos={},
        ),
    )
    actual = _recibir(mundo, _paquete(DESPUES, "005", ID_1))
    assert revision.entrega_anterior(caso, bd, actual.verificacion) is None


def test_si_el_archivo_anterior_ya_no_esta_no_hay_entrega_anterior(mundo) -> None:
    caso, bd, _ = mundo
    primera = _recibir(mundo, _paquete(ANTES, "004", ID_2))
    actual = _recibir(mundo, _paquete(DESPUES, "005", ID_1))
    primera.ruta.unlink()
    assert revision.entrega_anterior(caso, bd, actual.verificacion) is None


def test_la_empresa_propia_para_revisar_da_su_nombre_y_la_huella_de_su_clave(mundo) -> None:
    from seguridad import empresas

    _, bd, _ = mundo
    assert revision.empresa_propia_para_revisar(bd) == (None, None)
    empresas.guardar_empresa_propia(bd, EMPRESA, "J-00000000-0", "", "admin", AHORA)
    assert revision.empresa_propia_para_revisar(bd) == (EMPRESA, None)
    clave = empresas.generar_clave(bd, "una clave de firma larga y unica", "admin", AHORA)
    assert revision.empresa_propia_para_revisar(bd) == (EMPRESA, clave.huella)
    assert len(clave.huella) == 64
