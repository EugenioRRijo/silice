"""SL-E7: el registro encadenado, sellado en el embudo al confirmar (RF-83; spec S3 §6.2 a §6.5).

Oráculos independientes: la huella del contenido es el literal escrito a mano de
`tests/fixtures/canonico/ejemplo_v1.py`, y la del eslabón se recalcula aquí con `json` y `hashlib`
estándar sobre la fórmula del expediente SL-E7, sin `cadena.huella_del_eslabon`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

import pytest
from sqlalchemy import text

from core import models
from core.budget import cadena
from core.budget.cadena import GENESIS
from core.catalog import abrir_sesion
from core.models.cadena import EslabonVersion
from tests.fixtures.canonico.ejemplo_v1 import HUELLA_EJEMPLO_V1
from tests.fixtures.canonico_minimo import USUARIO, guardar_otra, registro, sembrar_minimo

#: SHA-256 de `[]` (lista vacía en JSON canónico): sin registros de cambio y sin anexos.
HUELLA_LISTA_VACIA = hashlib.sha256(b"[]").hexdigest()


def _sha_json(objeto) -> str:
    return hashlib.sha256(
        json.dumps(objeto, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


@pytest.fixture
def sesion(motor):
    with abrir_sesion(motor) as sesion:
        yield sesion


def _tres_versiones(sesion):
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    v2 = guardar_otra(sesion, proyecto, lista, "002", "30", version_origen=v1, motivo="edicion")
    sesion.add(registro(proyecto, v1, v2))
    sesion.commit()
    v3 = guardar_otra(sesion, proyecto, lista, "003", "35", version_origen=v2, motivo="edicion")
    sesion.add(registro(proyecto, v2, v3, campo="precio"))
    sesion.commit()
    return proyecto, (v1, v2, v3), lista


def _anexo_a(sesion, version):
    """Como `ui.entrega.anexos_de_cadena`: solo las versiones que tienen espacio traen anexo."""
    return {"anexos/espacio.json": b'{"ambientes":[]}'} if version.codigo == "002" else {}


def test_la_version_se_sella_al_confirmar_y_no_antes(sesion) -> None:
    proyecto, v1, _ = sembrar_minimo(sesion)
    assert sesion.get(EslabonVersion, v1.id) is None  # el embudo solo la marcó
    sesion.commit()
    eslabon = sesion.get(EslabonVersion, v1.id)
    assert eslabon.anterior == GENESIS == "0" * 64
    assert eslabon.usuario == USUARIO and eslabon.tipo == "normal"
    assert eslabon.huella_contenido == HUELLA_EJEMPLO_V1  # el contenido encadenado es el vector
    assert eslabon.huella_cambios == eslabon.huella_anexos == HUELLA_LISTA_VACIA
    assert len(eslabon.huella_eslabon) == 64 != eslabon.huella_contenido


def test_la_huella_del_eslabon_sigue_la_formula_del_expediente(sesion) -> None:
    """Recalculada aparte con `json` + `hashlib`: no con `huella_del_eslabon`."""
    _, v1, _ = sembrar_minimo(sesion)
    sesion.commit()
    e = sesion.get(EslabonVersion, v1.id)
    esperada = _sha_json(
        {
            "anterior": GENESIS,
            "codigo": "001",
            "contenido": HUELLA_EJEMPLO_V1,
            "cambios": HUELLA_LISTA_VACIA,
            "anexos": HUELLA_LISTA_VACIA,
            "usuario": USUARIO,
            "fecha_hora": e.fecha_hora.isoformat(),
            "tipo": "normal",
            "version_formato": 1,
        }
    )
    assert e.huella_eslabon == esperada


def test_las_huellas_de_cambios_y_anexos_siguen_la_formula_del_expediente(sesion) -> None:
    proyecto, (v1, v2, _), _ = _tres_versiones(sesion)
    fila = [
        "apu",
        "MIN-001|Arena",
        "cantidad",
        "1.00",
        "1.50",
        "memoria rev. B",
        USUARIO,
        "2026-11-01T10:00:00",
    ]
    assert sesion.get(EslabonVersion, v2.id).huella_cambios == _sha_json([fila])
    anexo = b'{"ambientes":[]}'
    assert cadena.huella_de_anexos({"anexos/espacio.json": anexo}) == _sha_json(
        [["anexos/espacio.json", hashlib.sha256(anexo).hexdigest()]]
    )
    # el orden de los anexos no cambia la huella (se ordenan por nombre)
    assert cadena.huella_de_anexos({"b": b"2", "a": b"1"}) == cadena.huella_de_anexos(
        {"a": b"1", "b": b"2"}
    )


@pytest.mark.sin_usuario_por_omision
def test_confirmar_sin_usuario_se_rechaza_y_no_se_escribe_nada(sesion) -> None:
    sembrar_minimo(sesion, usuario=None)
    with pytest.raises(cadena.SelladoSinUsuario, match="sin usuario"):
        sesion.commit()
    sesion.rollback()
    assert sesion.query(models.Presupuesto).count() == 0
    assert sesion.query(EslabonVersion).count() == 0


@pytest.mark.sin_usuario_por_omision
@pytest.mark.parametrize("usuario", ["", "   ", "\t\n"])
def test_un_usuario_vacio_o_en_blanco_tampoco_vale(sesion, usuario) -> None:
    sembrar_minimo(sesion, usuario=usuario)
    with pytest.raises(cadena.SelladoSinUsuario):
        sesion.commit()
    sesion.rollback()
    assert sesion.query(models.Presupuesto).count() == 0


@pytest.mark.sin_usuario_por_omision
def test_un_usuario_de_un_caracter_si_vale(sesion) -> None:
    """Frontera: el mínimo aceptado es un carácter no blanco."""
    _, v1, _ = sembrar_minimo(sesion, usuario="a")
    sesion.commit()
    assert sesion.get(EslabonVersion, v1.id).usuario == "a"


@pytest.mark.sin_usuario_por_omision
def test_el_rollback_olvida_las_versiones_pendientes(sesion) -> None:
    sembrar_minimo(sesion, usuario=None)
    sesion.rollback()
    sesion.commit()  # sin pendientes: ya no exige usuario
    assert sesion.query(EslabonVersion).count() == 0
    assert sesion.query(models.Presupuesto).count() == 0


def test_un_savepoint_no_sella_pero_la_transaccion_raiz_si(sesion) -> None:
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    with sesion.begin_nested():
        v2 = guardar_otra(sesion, proyecto, lista, "002", version_origen=v1, motivo="edicion")
    assert sesion.get(EslabonVersion, v2.id) is None  # liberar el SAVEPOINT no sella
    sesion.add(registro(proyecto, v1, v2))  # llega DESPUÉS del embudo y entra a la huella
    sesion.commit()
    eslabon = sesion.get(EslabonVersion, v2.id)
    registro_de_v2 = (
        sesion.query(models.RegistroCambio).filter_by(version_resultante_id=v2.id).one()
    )
    assert eslabon.huella_cambios == cadena.huella_de_cambios([registro_de_v2])
    assert eslabon.huella_cambios != HUELLA_LISTA_VACIA


def test_la_cadena_es_lineal_desde_el_genesis(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    e1, e2, e3 = (sesion.get(EslabonVersion, v.id) for v in (v1, v2, v3))
    assert (e1.anterior, e2.anterior, e3.anterior) == (
        GENESIS,
        e1.huella_eslabon,
        e2.huella_eslabon,
    )
    ids = [e.presupuesto_id for e in cadena.eslabones_de(sesion, proyecto)]
    assert ids == [v1.id, v2.id, v3.id]
    resultado = cadena.verificar_cadena(sesion, proyecto)
    assert resultado.integra and resultado.versiones == 3 and resultado.fallo is None
    assert cadena.mensaje_de_cadena(resultado) == "Cadena íntegra: 3 versiones"


def test_cada_proyecto_tiene_su_propio_genesis(sesion) -> None:
    proyecto, (v1, _, _), lista = _tres_versiones(sesion)
    otro = models.Proyecto(nombre="OTRO", descripcion="", dominio="civil")
    sesion.add(otro)
    sesion.flush()
    v = guardar_otra(sesion, otro, lista, "001")
    sesion.commit()
    assert sesion.get(EslabonVersion, v.id).anterior == GENESIS
    assert cadena.verificar_cadena(sesion, proyecto).integra
    assert cadena.verificar_cadena(sesion, otro).versiones == 1


def test_los_registros_de_cambio_entran_a_la_huella_aunque_lleguen_despues_del_embudo(sesion):
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    v2 = guardar_otra(sesion, proyecto, lista, "002", version_origen=v1, motivo="edicion")
    sesion.add(registro(proyecto, v1, v2))
    sesion.commit()
    assert sesion.get(EslabonVersion, v1.id).huella_cambios == HUELLA_LISTA_VACIA
    assert sesion.get(EslabonVersion, v2.id).huella_cambios != HUELLA_LISTA_VACIA


@pytest.mark.parametrize("motivo", [None, *models.MOTIVOS_VERSION])
def test_todo_motivo_de_version_y_el_motivo_vacio_quedan_sellados(sesion, motivo) -> None:
    """RV-7: la invariante no depende de una lista de caminos, sino del embudo."""
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    opciones = {} if motivo is None else {"version_origen": v1, "motivo": motivo}
    v2 = guardar_otra(sesion, proyecto, lista, "002", **opciones)
    sesion.commit()
    assert sesion.get(EslabonVersion, v2.id) is not None
    assert cadena.verificar_cadena(sesion, proyecto).integra


def _romper(sesion, sentencia: str, **parametros) -> None:
    sesion.execute(text(sentencia), parametros)
    sesion.commit()


def test_un_byte_cambiado_en_el_contenido_rompe_la_cadena_en_esa_version(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    _romper(
        sesion,
        "UPDATE partida_presupuestada SET cantidad = '31' WHERE presupuesto_id = :v",
        v=v2.id,
    )
    sesion.expire_all()
    resultado = cadena.verificar_cadena(sesion, proyecto)
    assert not resultado.integra and resultado.fallo.codigo_version == "002"
    assert resultado.fallo.motivo == "contenido" and resultado.versiones == 1
    mensaje = cadena.mensaje_de_cadena(resultado)
    assert "Cadena rota en la versión 002" in mensaje
    assert "Revíselo con el administrador" in mensaje


def test_un_precio_alterado_en_la_composicion_rompe_la_cadena(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    _romper(
        sesion,
        "UPDATE linea_composicion_version SET precio = '14.01' WHERE composicion_id IN "
        "(SELECT id FROM composicion_version WHERE presupuesto_id = :v)",
        v=v1.id,
    )
    sesion.expire_all()
    fallo = cadena.verificar_cadena(sesion, proyecto).fallo
    assert (fallo.codigo_version, fallo.motivo) == ("001", "contenido")


def test_un_registro_de_cambio_alterado_rompe_la_cadena(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    _romper(
        sesion,
        "UPDATE registro_cambio SET valor_nuevo = '9' WHERE version_resultante_id = :v",
        v=v3.id,
    )
    sesion.expire_all()
    fallo = cadena.verificar_cadena(sesion, proyecto).fallo
    assert (fallo.codigo_version, fallo.motivo) == ("003", "registro")


def test_un_registro_de_cambio_borrado_rompe_la_cadena(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    _romper(sesion, "DELETE FROM registro_cambio WHERE version_resultante_id = :v", v=v2.id)
    sesion.expire_all()
    fallo = cadena.verificar_cadena(sesion, proyecto).fallo
    assert (fallo.codigo_version, fallo.motivo) == ("002", "registro")


def test_un_anexo_alterado_rompe_la_cadena(sesion) -> None:
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    guardar_otra(sesion, proyecto, lista, "002", anexos_de=_anexo_a)
    sesion.commit()
    assert cadena.verificar_cadena(sesion, proyecto, anexos_de=_anexo_a).integra
    alterado = {"anexos/espacio.json": b'{"ambientes":[1]}'}
    fallo = cadena.verificar_cadena(
        sesion, proyecto, anexos_de=lambda s, v: alterado if v.codigo == "002" else {}
    ).fallo
    assert (fallo.codigo_version, fallo.motivo) == ("002", "anexo")


def test_un_eslabon_alterado_rompe_la_cadena(sesion) -> None:
    proyecto, (v1, v2, _), _ = _tres_versiones(sesion)
    _romper(
        sesion,
        "UPDATE eslabon_version SET usuario = 'otra persona' WHERE presupuesto_id = :v",
        v=v1.id,
    )
    sesion.expire_all()
    fallo = cadena.verificar_cadena(sesion, proyecto).fallo
    assert (fallo.codigo_version, fallo.motivo) == ("001", "eslabon")


def test_un_eslabon_reenganchado_a_otro_anterior_rompe_la_cadena(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    _romper(
        sesion,
        "UPDATE eslabon_version SET anterior = :a WHERE presupuesto_id = :v",
        a="f" * 64,
        v=v3.id,
    )
    sesion.expire_all()
    fallo = cadena.verificar_cadena(sesion, proyecto).fallo
    assert (fallo.codigo_version, fallo.motivo) == ("003", "eslabon")


def test_una_version_posterior_al_genesis_sin_eslabon_es_un_error_de_cadena(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    _romper(sesion, "DELETE FROM eslabon_version WHERE presupuesto_id = :v", v=v2.id)
    sesion.expire_all()
    fallo = cadena.verificar_cadena(sesion, proyecto).fallo
    assert (fallo.codigo_version, fallo.motivo) == ("002", "sin_sellar")


def test_el_indice_unico_impide_que_dos_versiones_cuelguen_del_mismo_eslabon(sesion) -> None:
    """Contra una versión REAL (la clave foránea se cumple): solo el índice único puede fallar.
    El plan usaba un `presupuesto_id` inexistente, que fallaba por la clave foránea y no probaba
    el índice."""
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    e2 = sesion.get(EslabonVersion, v2.id)
    anterior_de_e2 = e2.anterior
    _romper(sesion, "DELETE FROM eslabon_version WHERE presupuesto_id = :v", v=v3.id)
    sesion.add(
        EslabonVersion(
            presupuesto_id=v3.id,
            proyecto_id=proyecto.id,
            anterior=anterior_de_e2,
            huella_contenido="a" * 64,
            huella_cambios="b" * 64,
            huella_anexos="c" * 64,
            huella_eslabon="d" * 64,
            usuario="x",
            fecha_hora=datetime(2026, 1, 1),
            tipo="normal",
            version_formato=1,
        )
    )
    with pytest.raises(Exception, match="UNIQUE"):
        sesion.flush()
    sesion.rollback()


def test_una_cadena_bifurcada_impide_sellar_otra_version(sesion) -> None:
    proyecto, (v1, v2, v3), lista = _tres_versiones(sesion)
    # e3 deja de colgar de e2: la cadena queda con dos cabezas (e2 y e3)
    _romper(
        sesion,
        "UPDATE eslabon_version SET anterior = :a WHERE presupuesto_id = :v",
        a="f" * 64,
        v=v3.id,
    )
    sesion.expire_all()
    proyecto = sesion.get(models.Proyecto, proyecto.id)
    lista = sesion.get(models.ListaPrecios, lista.id)
    guardar_otra(sesion, proyecto, lista, "004", "40")
    with pytest.raises(cadena.SelladoEnConflicto, match="bifurc"):
        sesion.commit()
    sesion.rollback()
    assert sesion.query(models.Presupuesto).count() == 3


def test_el_sellado_retroactivo_cubre_lo_anterior_y_se_declara(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    _romper(sesion, "DELETE FROM eslabon_version")  # bases anteriores a S3: sin eslabones
    sesion.expire_all()
    assert cadena.verificar_cadena(sesion, proyecto).fallo.motivo == "sin_sellar"
    cuando = datetime(2026, 11, 3, 8, 30)
    selladas = cadena.sellar_historial(sesion, "Admin <admin>", ahora=cuando)
    sesion.commit()
    assert selladas == ("MIN-001/001", "MIN-001/002", "MIN-001/003")
    assert {e.tipo for e in cadena.eslabones_de(sesion, proyecto)} == {"retroactivo"}
    assert {e.usuario for e in cadena.eslabones_de(sesion, proyecto)} == {"Admin <admin>"}
    assert cadena.verificar_cadena(sesion, proyecto).integra
    assert cadena.texto_retroactivo(sesion, proyecto) == (
        "Versiones 001 a 003 selladas el 2026-11-03: prueban que no cambiaron desde esa fecha; "
        "antes no hay garantía."
    )
    assert cadena.sellar_historial(sesion, "Admin <admin>", ahora=cuando) == ()  # una sola vez


def test_guardar_en_un_proyecto_de_antes_de_s3_sella_primero_lo_anterior_como_retroactivo(
    sesion,
) -> None:
    """La API y los scripts también guardan: la cadena no queda con huecos (S3 §6.5)."""
    proyecto, (v1, v2, v3), lista = _tres_versiones(sesion)
    ids = (v1.id, v2.id, v3.id)
    _romper(sesion, "DELETE FROM eslabon_version")  # el proyecto viene de antes de S3
    sesion.expire_all()
    proyecto = sesion.get(models.Proyecto, proyecto.id)
    lista = sesion.get(models.ListaPrecios, lista.id)
    v3 = sesion.get(models.Presupuesto, ids[2])
    v4 = guardar_otra(sesion, proyecto, lista, "004", "40", version_origen=v3, motivo="edicion")
    sesion.commit()
    tipos = {e.presupuesto_id: e.tipo for e in cadena.eslabones_de(sesion, proyecto)}
    assert tipos == {
        ids[0]: "retroactivo",
        ids[1]: "retroactivo",
        ids[2]: "retroactivo",
        v4.id: "normal",
    }
    assert cadena.verificar_cadena(sesion, proyecto).integra
    assert cadena.texto_retroactivo(sesion, proyecto).startswith("Versiones 001 a 003 selladas")


def test_dos_versiones_nuevas_en_la_misma_transaccion_no_se_sellan_como_retroactivas(
    sesion,
) -> None:
    proyecto, v1, lista = sembrar_minimo(sesion)
    v2 = guardar_otra(sesion, proyecto, lista, "002", "30", version_origen=v1, motivo="edicion")
    sesion.commit()
    assert [e.tipo for e in cadena.eslabones_de(sesion, proyecto)] == ["normal", "normal"]
    assert v2.id > v1.id and cadena.verificar_cadena(sesion, proyecto).integra


def test_la_sesion_fija_el_proveedor_de_anexos_de_todo_lo_que_guarda(sesion) -> None:
    """Las pantallas que escriben `esp_*` con la versión no tienen que pasar `anexos_de` en cada
    llamada al embudo: la sesión lo trae (`anexos_por_omision`)."""
    cadena.anexos_por_omision(sesion, _anexo_a)
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    v2 = guardar_otra(sesion, proyecto, lista, "002", "30", version_origen=v1, motivo="edicion")
    sesion.add(registro(proyecto, v1, v2))
    sesion.commit()
    assert cadena.verificar_cadena(sesion, proyecto, anexos_de=_anexo_a).integra
    sin = cadena.verificar_cadena(sesion, proyecto)  # el verificador sin proveedor no ve el anexo
    assert not sin.integra and sin.fallo.motivo == "anexo" and sin.fallo.codigo_version == "002"


def test_sin_versiones_retroactivas_no_hay_declaracion(sesion) -> None:
    proyecto, _, _ = _tres_versiones(sesion)
    assert cadena.texto_retroactivo(sesion, proyecto) is None


def test_sellar_dos_veces_la_misma_version_es_un_error(sesion) -> None:
    _, v1, _ = sembrar_minimo(sesion)
    sesion.commit()
    with pytest.raises(ValueError, match="ya esta sellada"):
        cadena.sellar_version(sesion, v1, USUARIO)


def test_un_tipo_de_eslabon_desconocido_se_rechaza(sesion) -> None:
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    v2 = guardar_otra(sesion, proyecto, lista, "002")
    with pytest.raises(ValueError, match="tipo de eslabon"):
        cadena.sellar_version(sesion, v2, USUARIO, tipo="inventado")
    sesion.rollback()
