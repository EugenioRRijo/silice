"""Seguridad del paquete: el estado esperado de cada caso de S3 §13.3 (RF-85, RF-86, RNF-16).

Los paquetes se arman con `tests/fixtures/paquetes.py`, cuyas huellas se calculan con `hashlib`
aparte del núcleo; las claves son efímeras (`firma.generar_par()`), nunca de una empresa real.
Fronteras: firma de 0, 63, 64 (ceros) y 65 bytes; retiro de la clave en el mismo instante de la
recepción, un microsegundo antes y un segundo después; 200 000 / 200 001 renglones más líneas.
"""

from __future__ import annotations

import hashlib
import io
import json
import random
import zipfile
from datetime import datetime, timedelta

import pytest

from paquete import formato
from paquete.exportar import Emisor, construir_paquete
from paquete.formato import PaqueteRechazado
from paquete.verificar import (
    ALTERADO,
    NO_VERIFICADO,
    RECHAZADO,
    VERIFICADO,
    EmpresaConocida,
    banner,
    verificar,
)
from seguridad import firma
from tests.fixtures.paquetes import (
    CUATRO_ANEXOS,
    EMITIDO,
    EMPRESA,
    ESPACIO,
    INFORME,
    PRESUPUESTO,
    canonico,
    con_archivo_rehecho,
    con_manifiesto,
    escribir_zip,
    huella_anexos,
    leer_zip,
    paquete,
    reempaquetar,
    refirmar,
    sha,
)

RECIBIDO = datetime(2026, 11, 12, 10, 0)
PAR = firma.generar_par()
HUELLA = firma.huella_completa(PAR.publica)


def conocidas(estado="activa", fecha=None, par=PAR, nombre=EMPRESA):
    conocida = EmpresaConocida(nombre, par.publica, estado, fecha)
    tabla = {firma.huella_completa(par.publica): conocida}
    return tabla.get


def ver(datos, buscar=None, recibido=RECIBIDO, **mas):
    return verificar(datos, buscar_empresa=buscar or conocidas(), recibido_en=recibido, **mas)


def firmado(**mas) -> bytes:
    return paquete(par=PAR, **mas)


def _un_byte_cambiado(octetos: bytes) -> bytes:
    """El mismo largo y un solo byte distinto (el del medio, con su bit bajo invertido)."""
    medio = len(octetos) // 2
    return octetos[:medio] + bytes([octetos[medio] ^ 0x01]) + octetos[medio + 1 :]


# --- verificado ------------------------------------------------------------------------------


def test_integro_firmado_con_los_cuatro_anexos_es_verificado() -> None:
    v = ver(firmado())
    assert (v.estado, v.motivo, v.empresa_verificada) == (VERIFICADO, "firma_valida", EMPRESA)
    assert v.empresa_declarada == EMPRESA and v.legible and v.avisos == ()
    assert set(v.archivos) == {
        "manifiesto.json",
        "firma.ed25519",
        "presupuesto.json",
        "informe.json",
        "cadena.json",
        *CUATRO_ANEXOS,
    }
    assert v.sha256 == hashlib.sha256(firmado()).hexdigest()
    color, texto = banner(v)
    assert color == "verde" and texto == (
        "Verificado: emitido por Contratista Demo, C.A. el 2026-11-10. "
        "No se alteró desde que se firmó."
    )


def test_integro_firmado_sin_anexos_es_verificado() -> None:
    v = ver(firmado(anexos={}))
    assert (v.estado, v.motivo) == (VERIFICADO, "firma_valida")
    assert not any(n.startswith("anexos/") for n in v.archivos)


# --- clave retirada: la frontera de la fecha de recepción ------------------------------------


def test_firmada_con_clave_retirada_vale_si_se_recibio_antes_del_retiro() -> None:
    retiro = RECIBIDO + timedelta(days=1)
    v = ver(firmado(), conocidas("retirada", retiro))
    assert (v.estado, v.motivo, v.retirada, v.empresa_verificada) == (
        VERIFICADO,
        "retirada",
        True,
        EMPRESA,
    )
    assert v.avisos == ("La clave del emisor se retiró después de que usted recibió este paquete.",)
    assert banner(v)[1].endswith("(clave retirada después)")


@pytest.mark.parametrize(
    "recibido,estado,motivo",
    [
        (RECIBIDO - timedelta(microseconds=1), VERIFICADO, "retirada"),
        (RECIBIDO, NO_VERIFICADO, "retirada_tarde"),  # el mismo instante NO es «antes»
        (RECIBIDO + timedelta(seconds=1), NO_VERIFICADO, "retirada_tarde"),
    ],
)
def test_la_frontera_del_retiro_es_estricta(recibido, estado, motivo) -> None:
    v = ver(firmado(), conocidas("retirada", RECIBIDO), recibido=recibido)
    assert (v.estado, v.motivo) == (estado, motivo)
    assert v.retirada is (estado == VERIFICADO)


def test_firmada_con_clave_retirada_y_recibida_despues_es_no_verificado() -> None:
    v = ver(firmado(), conocidas("retirada", RECIBIDO - timedelta(days=1)))
    assert (v.estado, v.motivo, v.empresa_verificada) == (NO_VERIFICADO, "retirada_tarde", None)
    assert "Su clave se retiró antes de que usted recibiera el paquete." in banner(v)[1]


def test_clave_retirada_sin_fecha_de_retiro_es_no_verificado() -> None:
    v = ver(firmado(), conocidas("retirada", None))
    assert (v.estado, v.motivo) == (NO_VERIFICADO, "retirada_tarde")


# --- alterado ---------------------------------------------------------------------------------


def test_un_byte_cambiado_en_el_presupuesto_sin_tocar_el_manifiesto_es_alterado() -> None:
    datos = firmado()
    malo = reempaquetar(datos, {"presupuesto.json": _un_byte_cambiado(PRESUPUESTO)})
    v = ver(malo)
    assert (v.estado, v.motivo) == (ALTERADO, "integridad")
    assert v.detalle == "presupuesto.json cambió después de firmarse"
    assert banner(v) == (
        "rojo",
        "Alterado: presupuesto.json cambió después de firmarse. No confíe en este paquete; "
        "pida uno nuevo.",
    )


@pytest.mark.parametrize(
    "nombre", ["presupuesto.json", "informe.json", "cadena.json", *sorted(CUATRO_ANEXOS)]
)
def test_un_byte_cambiado_en_cualquier_archivo_listado_es_alterado(nombre: str) -> None:
    datos = firmado()
    original = leer_zip(datos)[nombre]
    v = ver(reempaquetar(datos, {nombre: _un_byte_cambiado(original)}))
    assert (v.estado, v.motivo, v.detalle) == (
        ALTERADO,
        "integridad",
        f"{nombre} cambió después de firmarse",
    )


def test_un_byte_cambiado_en_un_anexo_es_alterado() -> None:
    v = ver(reempaquetar(firmado(), {"anexos/control.json": b"{}"}))
    assert v.estado == ALTERADO and "anexos/control.json cambió" in v.detalle


def test_presupuesto_cambiado_con_manifiesto_rehecho_y_firma_vieja_es_alterado_por_la_firma():
    nuevo = b'{"formato":"silice-presupuesto","version_formato":1,"nota":"otra"}'
    v = ver(con_archivo_rehecho(firmado(), "presupuesto.json", nuevo))
    assert (v.estado, v.motivo) == (ALTERADO, "firma")
    assert v.detalle == "la firma no es válida con la clave registrada"


@pytest.mark.parametrize(
    "campo,valor", [("total", "999.00"), ("empresa", "Otra, C.A."), ("emitido", "2027-01-01")]
)
def test_un_campo_del_manifiesto_alterado_con_la_firma_vieja_es_alterado(campo, valor) -> None:
    v = ver(con_manifiesto(firmado(), **{campo: valor}))
    assert (v.estado, v.motivo) == (ALTERADO, "firma")


def test_un_manifiesto_alterado_sin_firma_no_se_puede_detectar_y_queda_no_verificado() -> None:
    """Límite declarado (banner «sin firma»): sin firma, cambiar el total del manifiesto no se
    detecta; por eso el estado es «no verificado» y no «verificado»."""
    v = ver(con_manifiesto(paquete(par=None), total="999.00"))
    assert (v.estado, v.motivo) == (NO_VERIFICADO, "sin_firma")


@pytest.mark.parametrize("tamano", [0, 1, 63, 65])
def test_firma_vacia_o_truncada_o_larga_es_alterado_sin_lanzar(tamano: int) -> None:
    datos = firmado()
    firma_buena = leer_zip(datos)["firma.ed25519"]
    assert len(firma_buena) == 64
    rellena = (firma_buena + b"\x00")[:tamano]
    v = ver(reempaquetar(datos, {"firma.ed25519": rellena}))
    assert (v.estado, v.motivo) == (ALTERADO, "firma")


def test_firma_de_64_ceros_es_alterado_sin_lanzar() -> None:
    v = ver(reempaquetar(firmado(), {"firma.ed25519": bytes(64)}))
    assert (v.estado, v.motivo) == (ALTERADO, "firma")


def test_firma_presente_sin_huella_de_clave_declarada_es_alterado() -> None:
    datos = con_manifiesto(firmado(), huella_clave=None)
    v = ver(datos)
    assert (v.estado, v.motivo, v.detalle) == (
        ALTERADO,
        "firma",
        "firma.ed25519 no es una firma válida",
    )


def test_la_firma_de_un_aviso_de_revocacion_no_vale_como_firma_de_paquete() -> None:
    datos = firmado()
    manifiesto = leer_zip(datos)["manifiesto.json"]
    otro_dominio = firma.firmar(PAR.privada, firma.DOMINIO_REVOCACION, manifiesto)
    v = ver(reempaquetar(datos, {"firma.ed25519": otro_dominio}))
    assert (v.estado, v.motivo) == (ALTERADO, "firma")


def test_el_manifiesto_que_lista_un_archivo_ausente_es_alterado() -> None:
    v = ver(reempaquetar(firmado(), {"anexos/ia.json": None}))
    assert v.estado == ALTERADO and v.detalle == "falta anexos/ia.json, que el manifiesto lista"


def test_un_archivo_admitido_que_el_manifiesto_no_lista_es_alterado() -> None:
    datos = paquete(par=PAR, anexos={"anexos/espacio.json": ESPACIO})
    v = ver(reempaquetar(datos, {"anexos/ia.json": b"{}"}))
    assert v.estado == ALTERADO
    assert v.detalle == "anexos/ia.json está en el paquete y el manifiesto no lo lista"


def test_refirmado_con_otra_clave_que_dice_ser_la_empresa_registrada_es_alterado() -> None:
    impostor = firma.generar_par()
    v = ver(refirmar(firmado(), impostor, huella_declarada=HUELLA))
    assert (v.estado, v.motivo) == (ALTERADO, "firma")  # se verifica con la clave REGISTRADA


def test_un_paquete_alterado_se_audita_igual_y_conserva_sus_archivos() -> None:
    v = ver(reempaquetar(firmado(), {"presupuesto.json": b"{}"}))
    assert v.estado == ALTERADO and v.legible and "presupuesto.json" in v.archivos


def test_la_cadena_que_no_cuadra_es_alterada_aunque_no_tenga_firma() -> None:
    archivos = leer_zip(paquete(par=None))
    cadena = json.loads(archivos["cadena.json"])
    cadena["eslabones"][0]["usuario"] = "Otra Persona"
    v = ver(con_archivo_rehecho(paquete(par=None), "cadena.json", canonico(cadena)))
    assert (v.estado, v.motivo) == (ALTERADO, "cadena")
    assert v.detalle == "el eslabón de la versión 004 no cuadra"


def test_la_cadena_atada_a_otro_presupuesto_es_alterada() -> None:
    """Presupuesto cambiado y su huella rehecha en el manifiesto de un paquete SIN firma: el
    último eslabón sigue sellando el presupuesto original."""
    nuevo = b'{"formato":"silice-presupuesto","version_formato":1,"nota":"otra"}'
    v = ver(con_archivo_rehecho(paquete(par=None), "presupuesto.json", nuevo))
    assert (v.estado, v.motivo, v.detalle) == (
        ALTERADO,
        "cadena",
        "el contenido de presupuesto.json no es el que selló el último eslabón",
    )


# --- no verificado ----------------------------------------------------------------------------


def test_refirmado_con_clave_no_registrada_y_otro_nombre_es_no_verificado_con_dice_venir_de():
    impostor = firma.generar_par()
    ajeno = paquete(par=impostor, empresa="**Empresa Falsa** ![x](http://127.0.0.1:9/p.png)")
    v = ver(ajeno)
    assert (v.estado, v.motivo) == (NO_VERIFICADO, "empresa_no_registrada")
    color, texto = banner(v, nombre_seguro=lambda s: s.replace("*", "\\*").replace("![", "\\!["))
    assert color == "ambar" and "dice venir de \\*\\*Empresa Falsa\\*\\*" in texto
    assert "![" not in texto.replace("\\![", "")


def test_sin_firma_es_no_verificado_y_el_banner_lo_dice_con_esas_palabras() -> None:
    v = ver(paquete(par=None))
    assert (v.estado, v.motivo, v.empresa_verificada) == (NO_VERIFICADO, "sin_firma", None)
    assert "firma.ed25519" not in v.archivos
    color, texto = banner(v)
    assert color == "ambar"
    assert "no que nadie lo cambió" in texto and "Se audita igual" in texto


def test_clave_revocada_es_no_verificado() -> None:
    v = ver(firmado(), conocidas("revocada", RECIBIDO + timedelta(days=30)))
    assert (v.estado, v.motivo) == (NO_VERIFICADO, "revocada")  # revocada: sin importar la fecha
    assert "Su clave fue revocada." in banner(v)[1]


def test_la_verificacion_nunca_usa_la_clave_que_trae_el_paquete() -> None:
    """Un paquete bien firmado por una clave que NO está registrada no se verifica solo porque
    su manifiesto la nombre: sin registro, es no verificado."""
    pedidas: list[str] = []

    def buscar(huella: str):
        pedidas.append(huella)
        return None

    v = verificar(firmado(), buscar_empresa=buscar, recibido_en=RECIBIDO)
    assert v.estado == NO_VERIFICADO and pedidas == [HUELLA]


def test_el_destinatario_de_otra_empresa_avisa() -> None:
    v = ver(firmado(destinatario="Otra Constructora, C.A."), mi_empresa=("Mi Empresa", "abc"))
    assert v.estado == VERIFICADO
    assert v.avisos == ("Este paquete se emitió para Otra Constructora, C.A..",)
    sin_aviso = ver(firmado(destinatario="Mi Empresa"), mi_empresa=("Mi Empresa", "abc"))
    assert sin_aviso.avisos == ()
    por_huella = ver(firmado(destinatario="abc"), mi_empresa=("Mi Empresa", "abc"))
    assert por_huella.avisos == ()


# --- rechazado --------------------------------------------------------------------------------


def test_un_manifiesto_con_clave_duplicada_se_rechaza() -> None:
    archivos = leer_zip(firmado())
    archivos["manifiesto.json"] = b'{"formato":"silice-paquete","formato":"silice-paquete"}'
    v = ver(escribir_zip(archivos))
    assert v.estado == RECHAZADO and "duplicada" in v.detalle


def test_formato_2_se_rechaza_con_su_mensaje() -> None:
    v = ver(con_manifiesto(firmado(), version_formato=2))
    assert v.estado == RECHAZADO and "versión de formato 2" in v.detalle


def test_un_formato_desconocido_o_un_manifiesto_que_no_es_objeto_se_rechaza() -> None:
    for manifiesto in (b"[]", b'{"formato":"otro","version_formato":1}'):
        archivos = leer_zip(firmado())
        archivos["manifiesto.json"] = manifiesto
        v = ver(escribir_zip(archivos))
        assert v.estado == RECHAZADO and "formato desconocido" in v.detalle


def test_un_paquete_sin_manifiesto_se_rechaza() -> None:
    v = ver(reempaquetar(firmado(), {"manifiesto.json": None}))
    assert v.estado == RECHAZADO and "no trae manifiesto.json" in v.detalle


@pytest.mark.parametrize("valor", ["NaN", "Infinity", "-Infinity"])
def test_constantes_no_finitas_en_el_manifiesto_se_rechazan(valor: str) -> None:
    archivos = leer_zip(firmado())
    archivos["manifiesto.json"] = (
        b'{"formato":"silice-paquete","version_formato":1,"x":%s}' % valor.encode()
    )
    assert ver(escribir_zip(archivos)).estado == RECHAZADO


def test_un_manifiesto_con_cifra_hostil_se_rechaza() -> None:
    archivos = leer_zip(firmado())
    archivos["manifiesto.json"] = (
        b'{"formato":"silice-paquete","version_formato":1,"x":1E+999999999}'
    )
    assert ver(escribir_zip(archivos)).estado == RECHAZADO


@pytest.mark.parametrize("niveles,estado", [(64, RECHAZADO), (65, RECHAZADO)])
def test_anidamiento_en_el_manifiesto(niveles: int, estado: str) -> None:
    # 64 niveles se leen (no es objeto: formato desconocido) y 65 no se leen (anidado)
    archivos = leer_zip(firmado())
    archivos["manifiesto.json"] = b"[" * niveles + b"]" * niveles
    v = ver(escribir_zip(archivos))
    assert v.estado == estado
    esperado = "formato desconocido" if niveles == 64 else "64 niveles"
    assert esperado in v.detalle


def test_presupuesto_con_json_no_estricto_se_rechaza() -> None:
    """Desviación registrada (bitácora S3-3, segundo PR): `verificar` lee `presupuesto.json` con el
    lector estricto aunque el manifiesto cuadre."""
    malo = b'{"formato":"silice-presupuesto","x":NaN}'
    v = ver(con_archivo_rehecho(paquete(par=None), "presupuesto.json", malo))
    assert v.estado == RECHAZADO and "presupuesto.json no es un JSON válido" in v.detalle


@pytest.mark.parametrize("renglones,lineas,rechazado", [(199_999, 1, False), (199_999, 2, True)])
def test_el_limite_de_200_000_renglones_y_lineas(renglones, lineas, rechazado) -> None:
    documento = {
        "formato": "silice-presupuesto",
        # números distintos: el JSON no se comprime más de 100:1 (la relación no se adelanta)
        "renglones": list(range(renglones)),
        "composiciones": [{"lineas": list(range(lineas))}, "no es objeto"],
    }
    presupuesto = canonico(documento)
    v = ver(paquete(par=PAR, presupuesto=presupuesto))
    if rechazado:
        assert v.estado == RECHAZADO
        assert v.detalle == (
            "presupuesto.json trae más de 200000 renglones y líneas de composición."
        )
    else:  # 200 000 justos: se lee y la firma y la cadena cuadran
        assert (v.estado, v.motivo) == (VERIFICADO, "firma_valida")


def test_un_paquete_rechazado_no_se_audita() -> None:
    v = ver(b"no es un zip")
    assert v.estado == RECHAZADO and not v.legible and v.archivos == {}
    assert "dañado" in v.detalle and banner(v)[0] == "rojo"
    assert banner(v)[1].startswith("Rechazado: ")


def test_zip_con_entradas_propias_del_formato_pero_con_un_nombre_extra_se_rechaza() -> None:
    archivos = leer_zip(firmado())
    archivos["anexos/otro.json"] = b"{}"
    v = ver(escribir_zip(archivos))
    assert v.estado == RECHAZADO and "no admitido" in v.detalle


def test_el_zip_que_miente_en_el_tamano_declarado_se_rechaza() -> None:
    datos = bytearray(firmado())
    posicion = datos.find(b"PK\x01\x02")  # primer registro del directorio central
    datos[posicion + 24 : posicion + 28] = (1).to_bytes(4, "little")  # descomprimido: 1 B
    v = ver(bytes(datos))
    assert v.estado == RECHAZADO and "dañado" in v.detalle


def test_zip_cifrado_se_rechaza() -> None:
    """El plan cambiaba el byte 8 de la cabecera LOCAL (el método de compresión, no el indicador)
    y `zipfile` lee el indicador del directorio central: se pone el bit 0 donde corresponde."""
    datos = bytearray(firmado())
    datos[datos.find(b"PK\x03\x04") + 6] |= 0x01
    datos[datos.find(b"PK\x01\x02") + 8] |= 0x01
    v = ver(bytes(datos))
    assert v.estado == RECHAZADO and "cifrado" in v.detalle


def test_compresion_que_no_es_almacenado_ni_deflate_se_rechaza() -> None:
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_BZIP2) as z:
        z.writestr("manifiesto.json", b"{}")
    v = ver(salida.getvalue())
    assert v.estado == RECHAZADO and "método de compresión no admitido" in v.detalle


def test_un_paquete_de_mas_de_20_mib_se_rechaza_antes_de_abrirse() -> None:
    v = ver(b"PK" + bytes(20_971_520 - 1))
    assert v.estado == RECHAZADO and "20 MiB" in v.detalle


# --- exportar: el manifiesto, la firma y la reproducibilidad ----------------------------------


def test_la_exportacion_es_reproducible_byte_a_byte() -> None:
    assert firmado() == firmado()
    assert paquete(par=None) == paquete(par=None)
    assert firmado(paquete_id="22222222-2222-4222-8222-222222222222") != firmado()
    assert firmado(emitido=EMITIDO + timedelta(seconds=1)) != firmado()


def test_el_manifiesto_lleva_las_huellas_calculadas_aparte_y_no_viaja_el_excel() -> None:
    datos = firmado()
    archivos = leer_zip(datos)
    manifiesto = json.loads(archivos["manifiesto.json"])
    listados = {a["nombre"]: (a["sha256"], a["tamano"]) for a in manifiesto["archivos"]}
    esperados = {"presupuesto.json": PRESUPUESTO, "informe.json": INFORME, **CUATRO_ANEXOS}
    for nombre, octetos in esperados.items():
        assert listados[nombre] == (sha(octetos), len(octetos))
    assert set(listados) == {*esperados, "cadena.json"}
    assert manifiesto["huella_anexos"] == huella_anexos(CUATRO_ANEXOS)
    assert (manifiesto["empresa"], manifiesto["huella_clave"], manifiesto["algoritmo"]) == (
        EMPRESA,
        HUELLA,
        "Ed25519",
    )
    assert manifiesto["emitido"] == "2026-11-10T09:30:00"
    assert not any(n.endswith((".xlsx", ".xls")) for n in archivos)
    assert firma.verificar(
        PAR.publica, firma.DOMINIO_PAQUETE, archivos["manifiesto.json"], archivos["firma.ed25519"]
    )
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        assert {i.date_time for i in z.infolist()} == {(1980, 1, 1, 0, 0, 0)}
        assert {i.compress_type for i in z.infolist()} == {zipfile.ZIP_DEFLATED}


def ruido(n: int) -> bytes:
    return random.Random(n).randbytes(n)


def _construir(**cambios):
    valores = dict(
        presupuesto=PRESUPUESTO,
        informe=INFORME,
        cadena=b"{}",
        anexos={},
        emisor=Emisor(EMPRESA, None, "Ana <ana>"),
        destinatario=None,
        proyecto="MIN-001",
        codigo="005",
        moneda="USD",
        total="0",
        ultima_huella="0" * 64,
        ahora=EMITIDO,
        version_silice="0.8.0",
        paquete_id="p",
    )
    valores.update(cambios)
    return construir_paquete(**valores)


def test_exportar_rechaza_un_anexo_fuera_del_formato_y_firmar_sin_huella() -> None:
    with pytest.raises(PaqueteRechazado, match="anexos/otro.json"):
        _construir(anexos={"anexos/otro.json": b"{}"})
    with pytest.raises(ValueError, match="huella de la clave"):
        _construir(privada=PAR.privada)


def test_exportar_no_genera_una_entrada_mayor_que_el_limite(monkeypatch) -> None:
    monkeypatch.setattr(formato, "LIMITE_ENTRADA", 1000)
    _construir(informe=ruido(1000))  # el límite justo: se genera
    with pytest.raises(PaqueteRechazado, match="informe.json excede 1000"):
        _construir(informe=ruido(1001))


def test_exportar_no_genera_un_paquete_que_el_revisor_rechazaria_por_la_relacion() -> None:
    """22f: lo que se exporta lo abre el revisor. Un informe muy repetitivo se comprime más de
    100:1 y el revisor lo rechaza: el emisor no debe generarlo."""
    informe = b" " * 1_000_000
    with pytest.raises(PaqueteRechazado, match="100:1"):
        _construir(informe=informe)
