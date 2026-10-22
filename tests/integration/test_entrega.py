"""Entregar el paquete: de la base del emisor a un `.silice` que OTRA instalación verifica
(UC-22, RF-85; spec S3 §8.1, §8.2 y §13.2). Dos bases de instalación temporales (la del emisor y
la del revisor), una base del caso en memoria y la firma Ed25519 de verdad.

Oráculos independientes de `ui.entrega`:
* el `presupuesto.json` es el documento canónico de MIN-001 v001 ESCRITO A MANO
  (`tests/fixtures/canonico/ejemplo_v1.py`): su SHA-256 es el literal `HUELLA_EJEMPLO_V1`,
  calculado aparte con `sha256sum`, y su total el de la memoria (20 x 41,83987500 = 836,79750000);
* las huellas del manifiesto, de los anexos y del eslabón se recalculan aquí con `hashlib` y
  `json.dumps` sobre los bytes que trae el ZIP, leído con `zipfile` (no con `paquete.formato`);
* la firma se comprueba con `cryptography` sobre `b"silice-paquete-v1\\0" + manifiesto.json`, el
  dominio literal del spec (§8.1), sin pasar por `seguridad.firma`;
* la huella de la clave es el SHA-256 de la pública cruda (spec S3 §7.1);
* los mensajes de cadena rota son los del spec S3 §6.4, copiados como literal.
"""

from __future__ import annotations

import hashlib
import io
import json
import uuid
import zipfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from adapters.espacio import crear_esquema_espacio, guardar_espacio
from aplicacion import entrega
from core import models
from core.catalog import abrir_sesion
from paquete import formato
from paquete.formato import PaqueteRechazado
from paquete.verificar import (
    ALTERADO,
    NO_VERIFICADO,
    RECHAZADO,
    VERIFICADO,
    EmpresaConocida,
    verificar,
)
from seguridad import empresas, firma
from seguridad.modelo import EmpresaRegistrada, EventoAcceso
from tests.fixtures.canonico.ejemplo_v1 import BYTES_EJEMPLO_V1, HUELLA_EJEMPLO_V1
from tests.fixtures.canonico_minimo import USUARIO, guardar_otra, sembrar_minimo
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.instalacion import AHORA, instalacion

CLAVE = "frase de firma larga y propia"
EMPRESA = "Contratista Demo, C.A."
CUANDO = datetime(2026, 11, 10, 9, 30)
RECIBIDO = datetime(2026, 11, 11, 8, 0)
GENESIS = "0" * 64
DOMINIO_DEL_SPEC = b"silice-paquete-v1\x00"
#: memoria de MIN-001: 20 m3 x 41,83987500 USD/m3 (tests/fixtures/canonico/ejemplo_v1.py).
TOTAL_MEMORIA = "836.79750000"
#: spec S3 §6.4, con la versión y el motivo de cada caso.
CADENA_ROTA_001_CONTENIDO = (
    "Cadena rota en la versión 001: su contenido no coincide con su huella; alguien cambió la "
    "base fuera del sistema. Revíselo con el administrador antes de entregar un paquete."
)
CADENA_ROTA_002_CONTENIDO = CADENA_ROTA_001_CONTENIDO.replace("versión 001", "versión 002")
CADENA_ROTA_001_SIN_SELLAR = (
    "Cadena rota en la versión 001: no tiene eslabón; alguien cambió la base fuera del sistema. "
    "Revíselo con el administrador antes de entregar un paquete."
)
ID_FIJO = uuid.UUID("12345678-1234-4234-8234-123456789abc")


# --- ayudantes (independientes de lo que se prueba) ----------------------------------------


def _sha(octetos: bytes) -> str:
    return hashlib.sha256(octetos).hexdigest()


def _canon(objeto) -> bytes:
    """JSON canónico del spec S3 §6.1, escrito aquí: claves ordenadas, sin espacios, UTF-8."""
    return json.dumps(objeto, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _zip(datos: bytes) -> dict[str, bytes]:
    """El contenido del `.silice` leído con `zipfile` (no con `paquete.formato.abrir_zip`)."""
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        return {i.filename: z.read(i) for i in z.infolist()}


def _rehacer_zip(archivos: dict[str, bytes]) -> bytes:
    flujo = io.BytesIO()
    with zipfile.ZipFile(flujo, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, octetos in archivos.items():
            z.writestr(nombre, octetos)
    return flujo.getvalue()


def _volcado(sesion: Session) -> dict[str, list[str]]:
    """Todas las filas de todas las tablas de la base del caso, por la MISMA conexión de la sesión
    (lo no confirmado también se ve)."""
    conexion = sesion.connection()
    tablas = conexion.execute(
        text("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
    ).scalars()
    return {
        t: sorted(repr(tuple(f)) for f in conexion.execute(text(f'SELECT * FROM "{t}"')))
        for t in list(tablas)
    }


def _conteos(bd: Session) -> dict[str, int]:
    conexion = bd.connection()
    tablas = conexion.execute(
        text("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
    ).scalars()
    return {
        t: conexion.execute(text(f'SELECT count(*) FROM "{t}"')).scalar_one() for t in list(tablas)
    }


def _eventos(bd: Session) -> list[EventoAcceso]:
    bd.expire_all()
    return list(bd.scalars(select(EventoAcceso).order_by(EventoAcceso.id)))


def _buscador(bd_revisor: Session):
    """Lo que el revisor sabe de las empresas: SOLO su propia base (`empresa_registrada`)."""

    def buscar(huella: str) -> EmpresaConocida | None:
        fila = bd_revisor.scalars(
            select(EmpresaRegistrada).where(EmpresaRegistrada.huella == huella)
        ).first()
        if fila is None:
            return None
        return EmpresaConocida(fila.empresa, fila.publica, fila.estado, fila.fecha_estado)

    return buscar


def _registrar_en_el_revisor(bd_emisor: Session, bd_revisor: Session) -> None:
    """El revisor registra la clave pública del emisor; la huella corta se «lee por teléfono»."""
    archivo = empresas.exportar_clave_publica_propia(bd_emisor, AHORA)
    leida = firma.huella_corta(empresas.clave_activa(bd_emisor).publica)
    empresas.registrar_empresa_ajena(
        bd_revisor, archivo, leida, "Ing. Pedro, por teléfono", "telefono", "revisor", AHORA
    )


# --- fixtures ------------------------------------------------------------------------------


def _sembrar(caso: Session, con_espacio: bool = True):
    crear_esquema_espacio(caso.connection())
    proyecto, version, lista = sembrar_minimo(caso, anexos_de=entrega.anexos_de_cadena)
    if con_espacio:
        guardar_espacio(caso, version.id, espacio_of001())
    caso.commit()  # sella v001 (con su espacio) antes de confirmar
    return proyecto, version, lista


@pytest.fixture
def emisor(motor, tmp_path: Path):
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "emisor") as bd:
        empresas.guardar_empresa_propia(bd, EMPRESA, "J-00000000-0", "", "ana", AHORA)
        proyecto, version, lista = _sembrar(caso)
        yield caso, bd, proyecto, version, lista


@pytest.fixture
def revisor(tmp_path: Path):
    with instalacion(tmp_path / "revisor") as bd:
        yield bd


def _entregar(caso, bd, version, **mas) -> entrega.Entrega:
    return entrega.entregar(
        caso, bd, version, usuario=USUARIO, ahora=CUANDO, version_silice="0.8.0", **mas
    )


# --- RF-85: el paquete firmado se verifica en otra instalación -----------------------------


def test_el_paquete_firmado_se_verifica_en_otra_instalacion(emisor, revisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    _registrar_en_el_revisor(bd, revisor)
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE, destinatario="Cliente S.A.")
    assert e.firmado and e.nombre == "MIN-001-001.silice"
    v = verificar(
        e.datos,
        buscar_empresa=_buscador(revisor),
        recibido_en=RECIBIDO,
        mi_empresa=("Cliente S.A.", None),
    )
    assert (v.estado, v.motivo, v.empresa_verificada) == (VERIFICADO, "firma_valida", EMPRESA)
    assert v.avisos == ()
    m = v.manifiesto
    assert (m["proyecto"], m["codigo"], m["moneda"], m["total"]) == (
        "MIN-001",
        "001",
        "USD",
        TOTAL_MEMORIA,
    )
    assert (m["usuario_emisor"], m["destinatario"], m["empresa"]) == (
        USUARIO,
        "Cliente S.A.",
        EMPRESA,
    )
    assert (m["paquete_id"], m["version_silice"], m["algoritmo"]) == (
        e.paquete_id,
        "0.8.0",
        "Ed25519",
    )
    assert m["emitido"] == "2026-11-10T09:30:00"
    assert "anexos/espacio.json" in v.archivos  # el espacio, cubierto por la cadena
    assert not any(n.endswith((".xlsx", ".xlsm", ".xls")) for n in v.archivos)  # DA-S3-10


def test_sin_registrar_la_clave_el_revisor_no_lo_da_por_verificado(emisor, revisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE)
    v = verificar(e.datos, buscar_empresa=_buscador(revisor), recibido_en=RECIBIDO)
    assert (v.estado, v.motivo, v.empresa_verificada) == (
        NO_VERIFICADO,
        "empresa_no_registrada",
        None,
    )
    assert v.empresa_declarada == EMPRESA


def test_destinatario_distinto_avisa_al_revisor(emisor, revisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    _registrar_en_el_revisor(bd, revisor)
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE, destinatario="Cliente Demo")
    v = verificar(
        e.datos,
        buscar_empresa=_buscador(revisor),
        recibido_en=RECIBIDO,
        mi_empresa=("Otra Empresa", None),
    )
    assert v.estado == VERIFICADO
    assert v.avisos == ("Este paquete se emitió para Cliente Demo.",)


def test_la_firma_es_ed25519_sobre_el_dominio_del_spec_y_la_clave_de_la_empresa(emisor) -> None:
    caso, bd, _, version, _ = emisor
    clave = empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE)
    archivos = _zip(e.datos)
    manifiesto = json.loads(archivos["manifiesto.json"])
    assert manifiesto["huella_clave"] == _sha(clave.publica)  # SHA-256 de la pública cruda
    publica = Ed25519PublicKey.from_public_bytes(clave.publica)
    firma_ = archivos["firma.ed25519"]
    assert len(firma_) == 64
    publica.verify(firma_, DOMINIO_DEL_SPEC + archivos["manifiesto.json"])  # lanza si no


def test_el_manifiesto_lista_cada_archivo_con_su_sha256_y_su_tamano(emisor) -> None:
    caso, bd, _, version, _ = emisor
    e = _entregar(caso, bd, version)
    archivos = _zip(e.datos)
    manifiesto = json.loads(archivos["manifiesto.json"])
    listados = {a["nombre"]: (a["sha256"], a["tamano"]) for a in manifiesto["archivos"]}
    esperados = {n: (_sha(b), len(b)) for n, b in archivos.items() if n not in ("manifiesto.json",)}
    assert listados == esperados
    assert set(archivos) == {
        "manifiesto.json",
        "presupuesto.json",
        "informe.json",
        "cadena.json",
        "anexos/espacio.json",
    }
    anexos = sorted(n for n in archivos if n.startswith("anexos/"))
    assert manifiesto["huella_anexos"] == _sha(_canon([[n, _sha(archivos[n])] for n in anexos]))


def test_el_presupuesto_del_paquete_es_el_documento_canonico_escrito_a_mano(emisor) -> None:
    caso, bd, _, version, _ = emisor
    e = _entregar(caso, bd, version)
    presupuesto = _zip(e.datos)["presupuesto.json"]
    assert (len(presupuesto), _sha(presupuesto)) == (BYTES_EJEMPLO_V1, HUELLA_EJEMPLO_V1)
    informe = json.loads(_zip(e.datos)["informe.json"])
    assert informe == {
        "codigo": "001",
        "formato": "silice-informe",
        "hallazgos": [],
        "version_formato": 1,
    }


def test_la_cadena_del_paquete_recalcula_a_mano_y_ata_el_ultimo_eslabon(emisor) -> None:
    caso, bd, _, version, _ = emisor
    e = _entregar(caso, bd, version)
    archivos = _zip(e.datos)
    cadena = json.loads(archivos["cadena.json"])
    manifiesto = json.loads(archivos["manifiesto.json"])
    [eslabon] = cadena["eslabones"]
    assert cadena["cambios"] == {}  # v001 no tiene RegistroCambio
    assert (eslabon["anterior"], eslabon["codigo"], eslabon["usuario"], eslabon["tipo"]) == (
        GENESIS,
        "001",
        USUARIO,
        "normal",
    )
    assert eslabon["huella_contenido"] == HUELLA_EJEMPLO_V1
    assert eslabon["huella_cambios"] == _sha(b"[]")
    espacio = archivos["anexos/espacio.json"]
    assert eslabon["huella_anexos"] == _sha(_canon([["anexos/espacio.json", _sha(espacio)]]))
    recalculada = _sha(
        _canon(
            {
                "anterior": GENESIS,
                "codigo": "001",
                "contenido": HUELLA_EJEMPLO_V1,
                "cambios": _sha(b"[]"),
                "anexos": eslabon["huella_anexos"],
                "usuario": USUARIO,
                "fecha_hora": eslabon["fecha_hora"],
                "tipo": "normal",
                "version_formato": eslabon["version_formato"],
            }
        )
    )
    assert eslabon["huella_eslabon"] == recalculada == manifiesto["ultima_huella_eslabon"]
    guardado = caso.scalar(text("SELECT huella_eslabon FROM eslabon_version"))
    assert guardado == recalculada


def test_una_version_anterior_viaja_solo_con_su_parte_de_la_cadena(emisor, revisor) -> None:
    caso, bd, proyecto, v1, lista = emisor
    v2 = guardar_otra(
        caso, proyecto, lista, "002", cantidad="30", version_origen=v1, motivo="edicion"
    )
    caso.commit()
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    _registrar_en_el_revisor(bd, revisor)
    e1 = _entregar(caso, bd, v1, contrasena_clave=CLAVE)
    e2 = _entregar(caso, bd, v2, contrasena_clave=CLAVE)
    c1 = json.loads(_zip(e1.datos)["cadena.json"])
    c2 = json.loads(_zip(e2.datos)["cadena.json"])
    assert [x["codigo"] for x in c1["eslabones"]] == ["001"]
    assert [x["codigo"] for x in c2["eslabones"]] == ["001", "002"]
    assert c2["eslabones"][1]["anterior"] == c2["eslabones"][0]["huella_eslabon"]
    # 30 m3 x 41,83987500 = 1255,19625000 (misma memoria que v001)
    assert json.loads(_zip(e2.datos)["manifiesto.json"])["total"] == "1255.19625000"
    for e in (e1, e2):
        v = verificar(e.datos, buscar_empresa=_buscador(revisor), recibido_en=RECIBIDO)
        assert (v.estado, v.motivo) == (VERIFICADO, "firma_valida")


# --- 22a: sin clave, sin firma y declarado ---------------------------------------------------


def test_sin_clave_se_exporta_sin_firma_y_se_declara(emisor, revisor) -> None:
    caso, bd, _, version, _ = emisor
    e = _entregar(caso, bd, version)
    assert not e.firmado
    v = verificar(e.datos, buscar_empresa=_buscador(revisor), recibido_en=RECIBIDO)
    assert (v.estado, v.motivo, v.empresa_verificada) == (NO_VERIFICADO, "sin_firma", None)
    assert v.manifiesto["huella_clave"] is None and v.manifiesto["empresa"] == EMPRESA
    assert "firma.ed25519" not in _zip(e.datos)
    assert [x.tipo for x in _eventos(bd) if x.tipo in ("firma", "paquete exportado")] == [
        "paquete exportado"
    ]


def test_sin_empresa_el_paquete_no_dice_quien_lo_emite(motor, tmp_path: Path) -> None:
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "sola") as bd:
        _, version, _ = _sembrar(caso)
        e = _entregar(caso, bd, version)
        m = json.loads(_zip(e.datos)["manifiesto.json"])
        assert (m["empresa"], m["huella_clave"], e.firmado) == (None, None, False)
        v = verificar(e.datos, buscar_empresa=lambda h: None, recibido_en=RECIBIDO)
        assert (v.estado, v.motivo) == (NO_VERIFICADO, "sin_firma")


def test_con_clave_pero_sin_contrasena_sale_sin_firma(emisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    e = _entregar(caso, bd, version)
    assert not e.firmado and "firma.ed25519" not in _zip(e.datos)
    assert json.loads(_zip(e.datos)["manifiesto.json"])["huella_clave"] is None


# --- 22b: contraseña de la clave errónea -----------------------------------------------------


def test_contrasena_de_clave_erronea_no_firma_ni_deja_nada_escrito(emisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    antes_bd, antes_caso = _conteos(bd), _volcado(caso)
    with pytest.raises(
        empresas.ContrasenaDeClaveIncorrecta, match=r"^La contraseña de la clave no es correcta\.$"
    ):
        _entregar(caso, bd, version, contrasena_clave=CLAVE + "x")
    bd.rollback()
    assert _conteos(bd) == antes_bd
    assert _volcado(caso) == antes_caso


# --- UC-22 paso 5: el SHA-256 del archivo descargado en `evento_acceso` -----------------------


def test_el_sha256_del_archivo_descargado_queda_en_el_registro_de_accesos(emisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    antes = len(_eventos(bd))
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE)
    descargado = hashlib.sha256(e.datos).hexdigest()  # el archivo tal cual baja
    assert e.sha256 == descargado
    nuevos = _eventos(bd)[antes:]
    assert [x.tipo for x in nuevos] == ["firma", "paquete exportado"]
    for x in nuevos:
        assert descargado in x.detalle and e.paquete_id in x.detalle
        assert "version 001" in x.detalle
        assert x.fecha_hora == CUANDO
        assert CLAVE not in x.detalle  # sin secretos


def test_el_registro_de_la_entrega_dice_el_usuario(emisor) -> None:
    """UC-22 paso 5: «guarda su SHA-256, su `paquete_id`, la versión y el usuario en
    `evento_acceso`». El usuario debe poder leerse del evento (login o detalle)."""
    caso, bd, _, version, _ = emisor
    _entregar(caso, bd, version)
    [exportado] = [x for x in _eventos(bd) if x.tipo == "paquete exportado"]
    assert USUARIO in exportado.detalle or exportado.login_intentado == USUARIO


def test_dos_entregas_de_la_misma_version_son_dos_paquetes_distintos(emisor) -> None:
    caso, bd, _, version, _ = emisor
    a = _entregar(caso, bd, version)
    b = _entregar(caso, bd, version)
    assert a.paquete_id != b.paquete_id and a.sha256 != b.sha256
    exportados = [x.detalle for x in _eventos(bd) if x.tipo == "paquete exportado"]
    assert len(exportados) == 2
    assert a.sha256 in exportados[0] and b.sha256 in exportados[1]


# --- la base del caso no cambia --------------------------------------------------------------


def test_la_base_del_caso_no_cambia_al_entregar(emisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    antes = _volcado(caso)
    assert antes["eslabon_version"] and antes["presupuesto"]  # hay algo que comparar
    _entregar(caso, bd, version, contrasena_clave=CLAVE, destinatario="Cliente S.A.")
    _entregar(caso, bd, version)
    assert not caso.new and not caso.dirty and not caso.deleted
    assert _volcado(caso) == antes
    caso.rollback()  # lo no confirmado tampoco existía
    assert _volcado(caso) == antes


# --- 22c: cadena rota o versión sin sellar -----------------------------------------------------


def test_una_cadena_rota_impide_entregar_y_dice_en_que_version(emisor) -> None:
    caso, bd, _, version, _ = emisor
    caso.execute(text("UPDATE partida_presupuestada SET cantidad = '21'"))
    caso.commit()
    caso.expire_all()
    antes = len(_eventos(bd))
    with pytest.raises(entrega.EntregaRechazada) as error:
        _entregar(caso, bd, version)
    assert str(error.value) == CADENA_ROTA_001_CONTENIDO
    assert len(_eventos(bd)) == antes  # no se registró ninguna entrega


def test_la_cadena_rota_en_una_version_anterior_impide_entregar_la_ultima(emisor) -> None:
    caso, bd, proyecto, v1, lista = emisor
    v2 = guardar_otra(
        caso, proyecto, lista, "002", cantidad="30", version_origen=v1, motivo="edicion"
    )
    caso.commit()
    caso.execute(
        text("UPDATE partida_presupuestada SET cantidad = '21' WHERE presupuesto_id = :v"),
        {"v": v1.id},
    )
    caso.commit()
    caso.expire_all()
    with pytest.raises(entrega.EntregaRechazada) as error:
        _entregar(caso, bd, v2)
    assert str(error.value) == CADENA_ROTA_001_CONTENIDO


def test_la_cadena_rota_solo_en_la_ultima_version_lo_dice(emisor) -> None:
    caso, bd, proyecto, v1, lista = emisor
    v2 = guardar_otra(
        caso, proyecto, lista, "002", cantidad="30", version_origen=v1, motivo="edicion"
    )
    caso.commit()
    caso.execute(
        text("UPDATE partida_presupuestada SET cantidad = '31' WHERE presupuesto_id = :v"),
        {"v": v2.id},
    )
    caso.commit()
    caso.expire_all()
    with pytest.raises(entrega.EntregaRechazada) as error:
        _entregar(caso, bd, v2)
    assert str(error.value) == CADENA_ROTA_002_CONTENIDO


def test_un_espacio_cambiado_fuera_del_sistema_rompe_la_cadena(emisor) -> None:
    caso, bd, _, version, _ = emisor
    tablas = list(
        caso.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'esp_%'")
        ).scalars()
    )
    con_filas = [t for t in tablas if caso.scalar(text(f'SELECT count(*) FROM "{t}"'))]
    assert con_filas  # OF-001 tiene ambientes, puntos...
    caso.execute(
        text(
            f'DELETE FROM "{con_filas[0]}" WHERE rowid = (SELECT max(rowid) FROM "{con_filas[0]}")'
        )
    )
    caso.commit()
    caso.expire_all()
    with pytest.raises(
        entrega.EntregaRechazada, match="^Cadena rota en la versión 001: uno de sus anexos"
    ):
        _entregar(caso, bd, version)


def test_una_version_sin_sellar_no_se_entrega(emisor) -> None:
    caso, bd, _, version, _ = emisor
    caso.execute(text("DELETE FROM eslabon_version"))
    caso.commit()
    caso.expire_all()
    with pytest.raises(entrega.EntregaRechazada) as error:
        _entregar(caso, bd, version)
    assert str(error.value) == CADENA_ROTA_001_SIN_SELLAR


# --- el resumen (UC-22 paso 2) y el estado de la cadena ----------------------------------------


def test_el_resumen_dice_total_hallazgos_cadena_empresa_firma_y_anexos(emisor) -> None:
    caso, bd, _, version, _ = emisor
    r = entrega.resumen_de_entrega(caso, bd, version)
    assert (r.codigo, r.cadena_integra, r.empresa, r.firma_disponible) == (
        "001",
        True,
        EMPRESA,
        False,
    )
    assert r.total == Decimal(TOTAL_MEMORIA)
    assert dict(r.hallazgos_por_severidad) == {}  # el informe a mano no tiene hallazgos
    assert r.anexos == ("anexos/espacio.json",)
    assert r.mensaje_de_cadena == "Cadena íntegra: 1 versiones"
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    assert entrega.resumen_de_entrega(caso, bd, version).firma_disponible is True


def test_el_resumen_de_una_cadena_rota_lo_dice_sin_lanzar(emisor) -> None:
    caso, bd, _, version, _ = emisor
    caso.execute(text("UPDATE partida_presupuestada SET cantidad = '21'"))
    caso.commit()
    caso.expire_all()
    r = entrega.resumen_de_entrega(caso, bd, version)
    assert (r.cadena_integra, r.mensaje_de_cadena) == (False, CADENA_ROTA_001_CONTENIDO)


def test_el_estado_de_la_cadena_de_un_proyecto(emisor) -> None:
    caso, *_ = emisor
    estado = entrega.estado_de_la_cadena(caso, "MIN-001")
    assert estado == entrega.EstadoDeLaCadena(True, "Cadena íntegra: 1 versiones", None)
    assert entrega.estado_de_la_cadena(caso, "NO-EXISTE") is None


def test_el_estado_de_la_cadena_declara_las_versiones_retroactivas(emisor) -> None:
    from core.budget import cadena

    caso, bd, proyecto, v1, lista = emisor
    guardar_otra(caso, proyecto, lista, "002", cantidad="30", version_origen=v1, motivo="edicion")
    caso.commit()
    caso.execute(text("DELETE FROM eslabon_version"))
    caso.commit()
    caso.expire_all()
    cadena.sellar_historial(
        caso, USUARIO, anexos_de=entrega.anexos_de_cadena, ahora=datetime(2026, 11, 3, 8, 0)
    )
    caso.commit()
    estado = entrega.estado_de_la_cadena(caso, "MIN-001")
    assert estado == entrega.EstadoDeLaCadena(
        True,
        "Cadena íntegra: 2 versiones",
        "Versiones 001 a 002 selladas el 2026-11-03: prueban que no cambiaron desde esa fecha; "
        "antes no hay garantía.",
    )


# --- anexos que viajan -----------------------------------------------------------------------


def test_sin_espacio_no_hay_anexo_de_cadena_y_el_paquete_verifica(motor, tmp_path: Path) -> None:
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "e") as bd:
        _, version, _ = _sembrar(caso, con_espacio=False)
        assert dict(entrega.anexos_de_cadena(caso, version)) == {}
        e = _entregar(caso, bd, version)
        archivos = _zip(e.datos)
        assert not any(n.startswith("anexos/") for n in archivos)
        cadena = json.loads(archivos["cadena.json"])
        assert cadena["eslabones"][0]["huella_anexos"] == _sha(b"[]")
        v = verificar(e.datos, buscar_empresa=lambda h: None, recibido_en=RECIBIDO)
        assert (v.estado, v.motivo) == (NO_VERIFICADO, "sin_firma")


def test_los_anexos_de_s1_viajan_con_huella_por_entrada(emisor) -> None:
    caso, bd, proyecto, version, _ = emisor
    # Declarada DESPUÉS de la fecha de v001 (2026-11-01): no cambia su documento ni su cadena.
    caso.add(
        models.MonedaProyecto(
            proyecto_id=proyecto.id,
            moneda="USD",
            desde=datetime(2026, 11, 5),
            version_id=None,
            responsable="ana",
            fuente="al crear",
        )
    )
    caso.commit()
    e = _entregar(caso, bd, version)
    archivos = _zip(e.datos)
    anexo = json.loads(archivos["anexos/reajuste.json"])
    assert (anexo["formato"], anexo["nombre"], anexo["version_formato"]) == (
        "silice-anexo",
        "reajuste",
        1,
    )
    [entrada] = [x for x in anexo["entradas"] if x["tabla"] == "moneda_proyecto"]
    assert entrada["fila"]["moneda"] == "USD" and entrada["fila"]["responsable"] == "ana"
    assert entrada["huella"] == _sha(_canon(entrada["fila"]))
    assert "anexos/control.json" not in archivos  # sin filas de S2 en este proyecto
    assert _sha(archivos["presupuesto.json"]) == HUELLA_EJEMPLO_V1


def test_el_anexo_de_ia_que_se_pasa_viaja_tal_cual_y_no_rompe_la_verificacion(
    emisor, revisor
) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    _registrar_en_el_revisor(bd, revisor)
    ia = _canon({"formato": "silice-ia", "sesiones": []})
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE, ia=ia)
    archivos = _zip(e.datos)
    assert archivos["anexos/ia.json"] == ia
    v = verificar(e.datos, buscar_empresa=_buscador(revisor), recibido_en=RECIBIDO)
    assert (v.estado, v.motivo) == (VERIFICADO, "firma_valida")


# --- un byte cambiado en el archivo entregado --------------------------------------------------


@pytest.mark.parametrize(
    "nombre", ["presupuesto.json", "informe.json", "cadena.json", "anexos/espacio.json"]
)
def test_un_byte_cambiado_en_un_archivo_del_paquete_da_alterado(emisor, revisor, nombre) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    _registrar_en_el_revisor(bd, revisor)
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE)
    archivos = _zip(e.datos)
    original = archivos[nombre]
    medio = len(original) // 2
    archivos[nombre] = original[:medio] + bytes([original[medio] ^ 0x01]) + original[medio + 1 :]
    v = verificar(_rehacer_zip(archivos), buscar_empresa=_buscador(revisor), recibido_en=RECIBIDO)
    assert (v.estado, v.motivo) == (ALTERADO, "integridad")
    assert nombre in v.detalle


def test_un_byte_cambiado_en_el_manifiesto_firmado_da_alterado_por_la_firma(
    emisor, revisor
) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    _registrar_en_el_revisor(bd, revisor)
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE, destinatario="Cliente S.A.")
    archivos = _zip(e.datos)
    archivos["manifiesto.json"] = archivos["manifiesto.json"].replace(
        b"Cliente S.A.", b"Cliente S.B."
    )
    v = verificar(_rehacer_zip(archivos), buscar_empresa=_buscador(revisor), recibido_en=RECIBIDO)
    assert (v.estado, v.motivo) == (ALTERADO, "firma")


def test_un_byte_cambiado_en_el_zip_crudo_nunca_lanza_ni_pasa_contenido_cambiado(
    emisor, revisor
) -> None:
    """Un byte del archivo crudo cambiado, en una muestra de posiciones que cubre cabeceras, datos
    comprimidos y directorio central (spec S3 §8.3): `verificar` nunca lanza, y solo puede decir
    «verificado» si el contenido de TODOS los archivos es el original (un byte de metadatos del
    ZIP, como la hora o los atributos, no cambia lo que se firmó). Lo demás es «rechazado» (ZIP
    dañado) o «alterado»."""
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    _registrar_en_el_revisor(bd, revisor)
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE)
    originales = _zip(e.datos)
    buscar = _buscador(revisor)
    estados = []
    for posicion in range(0, len(e.datos), max(1, len(e.datos) // 97)):
        danado = bytearray(e.datos)
        danado[posicion] ^= 0xFF
        v = verificar(bytes(danado), buscar_empresa=buscar, recibido_en=RECIBIDO)
        assert v.estado in (RECHAZADO, ALTERADO, VERIFICADO), (posicion, v.estado, v.motivo)
        if v.estado == VERIFICADO:
            assert dict(v.archivos) == originales, posicion
        estados.append(v.estado)
    assert RECHAZADO in estados  # los daños del ZIP o de un flujo comprimido se rechazan
    assert estados.count(VERIFICADO) < len(estados) // 4  # solo bytes de metadatos


# --- 22f: un paquete que el revisor rechazaría no se genera -------------------------------------


def test_un_paquete_mas_grande_que_el_limite_no_se_genera_y_el_limite_exacto_si(
    emisor, monkeypatch
) -> None:
    caso, bd, _, version, _ = emisor
    monkeypatch.setattr(uuid, "uuid4", lambda: ID_FIJO)  # mismo paquete, mismo tamaño
    tamano = len(_entregar(caso, bd, version).datos)
    assert len(_entregar(caso, bd, version).datos) == tamano  # determinista sin firma
    antes = len(_eventos(bd))
    monkeypatch.setattr(formato, "LIMITE_ARCHIVO", tamano - 1)
    with pytest.raises(PaqueteRechazado, match="no se genera un paquete que el revisor"):
        _entregar(caso, bd, version)
    assert len(_eventos(bd)) == antes  # nada se registró
    monkeypatch.setattr(formato, "LIMITE_ARCHIVO", tamano)
    assert len(_entregar(caso, bd, version).datos) == tamano


def test_el_limite_real_es_20_mib() -> None:
    assert formato.LIMITE_ARCHIVO == 20 * 1024 * 1024 == 20_971_520


# --- 22e: la firma solo desde el propio equipo (el gancho de RV-15) ------------------------------


@pytest.mark.parametrize("ip", ["127.0.0.1", "::1", "127.0.0.2"])
def test_desde_el_bucle_local_si_se_firma(ip: str) -> None:
    empresas.exigir_equipo_propio(ip)


@pytest.mark.parametrize("ip", ["192.168.1.20", "10.0.0.5", "8.8.8.8", "", None, "no-es-ip"])
def test_desde_otra_ip_no_se_firma(ip) -> None:
    with pytest.raises(
        empresas.ClaveError, match=r"^La clave de firma solo se gestiona desde el propio equipo\.$"
    ):
        empresas.exigir_equipo_propio(ip)


def test_la_ip_propia_de_la_red_local_cuenta_como_el_equipo_y_su_vecina_no() -> None:
    empresas.exigir_equipo_propio("192.168.1.20", "192.168.1.20")
    with pytest.raises(empresas.ClaveError):
        empresas.exigir_equipo_propio("192.168.1.21", "192.168.1.20")


# --- nombre del archivo ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("proyecto", "codigo", "esperado"),
    [
        ("OF-001: oficina/../x?", "003", "OF-001--oficina----x-003.silice"),
        ("MIN-001", "001", "MIN-001-001.silice"),
        ("", "001", "proyecto-001.silice"),
        ("///", "002", "proyecto-002.silice"),
        ("A" * 61, "001", "A" * 60 + "-001.silice"),
        ("A" * 60, "001", "A" * 60 + "-001.silice"),
        ("..\\..\\C:\\x", "001", "C--x-001.silice"),
    ],
)
def test_el_nombre_de_archivo_no_lleva_caracteres_peligrosos(
    proyecto: str, codigo: str, esperado: str
) -> None:
    assert entrega.nombre_de_archivo(proyecto, codigo) == esperado


def test_el_conteo_de_eventos_no_depende_de_otras_tablas(emisor) -> None:
    """Sanidad del oráculo `_eventos`: la tabla `evento_acceso` del emisor parte con el alta de la
    empresa (un evento «empresa»)."""
    _, bd, *_ = emisor
    assert [x.tipo for x in _eventos(bd)] == ["empresa"]
    assert bd.scalar(select(func.count()).select_from(EventoAcceso)) == 1
