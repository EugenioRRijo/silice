"""Entregar una versión que no es una aprobada queda rotulado (Tarea D4, decisión de Eugenio del
2026-10-27; T20 punto 4): el paquete lleva «Versión NO aprobada» en el manifiesto (que la firma
cubre) y en el informe (la portada), con la fecha y la última aprobada que no se eligió, y el evento
de la entrega lo registra. Una versión aprobada, con o sin observaciones, no lleva la marca.

Oráculos a mano: el texto y la fecha son literales; los archivos se leen con `zipfile` y se
reescriben con `json.dumps` canónico, sin pasar por `paquete`.
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from aplicacion import aprobaciones
from aplicacion.tablas_aprobacion import crear_esquema_aprobacion
from paquete.verificar import ALTERADO, NO_VERIFICADO, VERIFICADO, verificar
from seguridad import empresas
from tests.fixtures.canonico_minimo import guardar_otra
from tests.fixtures.instalacion import AHORA
from tests.integration.test_entrega import (
    CLAVE,
    CUANDO,
    RECIBIDO,
    _buscador,
    _canon,
    _entregar,
    _eventos,
    _registrar_en_el_revisor,
    _rehacer_zip,
    _zip,
    emisor,  # noqa: F401  (fixture)
    revisor,  # noqa: F401  (fixture)
)

TEXTO = "Versión NO aprobada"
LLAVE = "version_no_aprobada"
ENVIO = datetime(2026, 11, 9, 8, 0)
DICTAMEN = datetime(2026, 11, 9, 16, 0)


def _aprobar(caso, proyecto, version: str, resultado: str = "aprobada", notas: str = "") -> None:
    crear_esquema_aprobacion(caso.get_bind())
    envio = aprobaciones.enviar(
        caso, str(proyecto.id), version, nota="Para su aprobación", usuario="ana", ahora=ENVIO
    )
    aprobaciones.dictaminar(
        caso, envio.id, resultado=resultado, notas=notas, usuario="rita", ahora=DICTAMEN
    )


def _marca(fecha: str = "2026-11-10", ultima: str | None = None) -> dict:
    return {"texto": TEXTO, "fecha": fecha, "ultima_aprobada": ultima}


def test_una_version_no_aprobada_lleva_la_marca_en_el_manifiesto_y_en_la_portada(emisor) -> None:
    caso, bd, _, version, _ = emisor
    archivos = _zip(_entregar(caso, bd, version).datos)
    assert json.loads(archivos["manifiesto.json"])[LLAVE] == _marca()
    assert json.loads(archivos["informe.json"])["marca"] == _marca()


def test_la_marca_nombra_la_ultima_aprobada_que_no_se_eligio(emisor) -> None:
    caso, bd, proyecto, v1, lista = emisor
    v2 = guardar_otra(
        caso, proyecto, lista, "002", cantidad="30", version_origen=v1, motivo="edicion"
    )
    caso.commit()
    _aprobar(caso, proyecto, "001")
    archivos = _zip(_entregar(caso, bd, v2).datos)
    assert json.loads(archivos["manifiesto.json"])[LLAVE] == _marca(ultima="001")
    assert json.loads(archivos["informe.json"])["marca"] == _marca(ultima="001")


@pytest.mark.parametrize(
    ("resultado", "notas"), [("aprobada", ""), ("aprobada_con_observaciones", "Revisar el acero.")]
)
def test_una_version_aprobada_no_lleva_la_marca(emisor, resultado, notas) -> None:
    caso, bd, proyecto, version, _ = emisor
    _aprobar(caso, proyecto, "001", resultado, notas)
    archivos = _zip(_entregar(caso, bd, version).datos)
    assert LLAVE not in json.loads(archivos["manifiesto.json"])
    assert "marca" not in json.loads(archivos["informe.json"])
    assert "NO aprobada" not in _eventos(bd)[-1].detalle


def test_una_devuelta_tampoco_es_aprobada(emisor) -> None:
    caso, bd, proyecto, version, _ = emisor
    _aprobar(caso, proyecto, "001", "devuelta", "Falta el acero.")
    archivos = _zip(_entregar(caso, bd, version).datos)
    assert json.loads(archivos["manifiesto.json"])[LLAVE] == _marca()


def test_el_evento_de_la_entrega_registra_que_no_estaba_aprobada(emisor) -> None:
    caso, bd, _, version, _ = emisor
    _entregar(caso, bd, version)
    detalle = _eventos(bd)[-1].detalle
    assert "; version NO aprobada (sin aprobada previa); " in detalle
    assert "sello_version " in detalle


def test_el_evento_nombra_la_ultima_aprobada_que_no_se_eligio(emisor) -> None:
    caso, bd, proyecto, v1, lista = emisor
    v2 = guardar_otra(
        caso, proyecto, lista, "002", cantidad="30", version_origen=v1, motivo="edicion"
    )
    caso.commit()
    _aprobar(caso, proyecto, "001")
    _entregar(caso, bd, v2)
    assert "; version NO aprobada (ultima aprobada 001); " in _eventos(bd)[-1].detalle


def test_la_marca_va_en_la_fecha_de_la_entrega(emisor) -> None:
    caso, bd, _, version, _ = emisor
    archivos = _zip(_entregar(caso, bd, version).datos)
    assert json.loads(archivos["manifiesto.json"])[LLAVE]["fecha"] == CUANDO.date().isoformat()


def test_quitar_la_marca_del_manifiesto_firmado_rompe_la_firma(emisor, revisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    _registrar_en_el_revisor(bd, revisor)
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE)
    intacto = verificar(e.datos, buscar_empresa=_buscador(revisor), recibido_en=RECIBIDO)
    assert intacto.estado == VERIFICADO
    archivos = _zip(e.datos)
    manifiesto = json.loads(archivos["manifiesto.json"])
    del manifiesto[LLAVE]
    archivos["manifiesto.json"] = _canon(manifiesto)
    v = verificar(_rehacer_zip(archivos), buscar_empresa=_buscador(revisor), recibido_en=RECIBIDO)
    assert (v.estado, v.motivo) == (ALTERADO, "firma")


def test_quitar_la_marca_del_informe_rompe_la_integridad(emisor, revisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    _registrar_en_el_revisor(bd, revisor)
    archivos = _zip(_entregar(caso, bd, version, contrasena_clave=CLAVE).datos)
    informe = json.loads(archivos["informe.json"])
    del informe["marca"]
    archivos["informe.json"] = _canon(informe)
    v = verificar(_rehacer_zip(archivos), buscar_empresa=_buscador(revisor), recibido_en=RECIBIDO)
    assert (v.estado, v.motivo) == (ALTERADO, "integridad")
    assert "informe.json" in v.detalle


def test_sin_firma_quitar_la_marca_solo_del_manifiesto_no_pasa(emisor, revisor) -> None:
    """Sin firma nada impide reescribir el manifiesto, pero manifiesto e informe deben decir lo
    mismo: quitar la marca de uno solo se detecta."""
    caso, bd, _, version, _ = emisor
    archivos = _zip(_entregar(caso, bd, version).datos)
    manifiesto = json.loads(archivos["manifiesto.json"])
    del manifiesto[LLAVE]
    archivos["manifiesto.json"] = _canon(manifiesto)
    v = verificar(_rehacer_zip(archivos), buscar_empresa=_buscador(revisor), recibido_en=RECIBIDO)
    assert v.estado == ALTERADO
    assert v.motivo == "marca"
    assert "Versión NO aprobada" in v.detalle


def test_el_paquete_marcado_se_verifica_normalmente(emisor, revisor) -> None:
    caso, bd, _, version, _ = emisor
    e = _entregar(caso, bd, version)
    v = verificar(e.datos, buscar_empresa=_buscador(revisor), recibido_en=RECIBIDO)
    assert (v.estado, v.motivo) == (NO_VERIFICADO, "sin_firma")


def test_con_el_rastro_de_aprobaciones_vacio_tambien_se_marca(emisor) -> None:
    """Sin ningún envío (la tabla existe y está vacía) la versión tampoco es una aprobada."""
    caso, bd, _, version, _ = emisor
    crear_esquema_aprobacion(caso.get_bind())
    archivos = _zip(_entregar(caso, bd, version).datos)
    assert json.loads(archivos["manifiesto.json"])[LLAVE] == _marca()
