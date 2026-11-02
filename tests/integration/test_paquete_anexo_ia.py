"""El paquete trae `anexos/ia.json` (maestro §4.5, RV-19; S4 §5.5; plan 0.9.0, tarea 16).

Contra los nombres reales de S3-3: `ui.entrega.entregar` arma el `.silice` en memoria y
`paquete.verificar.verificar` lo abre en OTRA instalacion (la del receptor, que registro la clave
publica del emisor comparando la huella corta). Lo que se comprueba: el anexo viaja con pedido,
llamadas con su validacion, citas y decisiones; no lleva uso de fichas, costo, topes ni la clave;
sin sesiones aceptadas no viaja; esta cubierto por `huella_anexos` del manifiesto firmado, de modo
que alterar un byte da «alterado» aunque el atacante rehaga la entrada del manifiesto.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import zipfile
from datetime import datetime

import pytest
from sqlalchemy import select

from aplicacion import entrega
from asistente.propuestas import EstadoPropuesta
from asistente.registro import anexo_ia, crear_esquema_ia
from core import models
from core.budget.cadena import huella_de_anexos
from core.catalog import abrir_sesion, crear_motor
from paquete.verificar import ALTERADO, NO_VERIFICADO, VERIFICADO, EmpresaConocida, verificar
from seguridad import empresas, firma
from seguridad.modelo import EmpresaRegistrada
from tests.fixtures.asistente_base import PROYECTO, QUIEN, VERSION, plantilla_s4, sesion_en_base
from tests.fixtures.asistente_pedidos import AMBIENTE, PEDIDO
from tests.fixtures.hoja_en_base import plantilla_of001
from tests.fixtures.instalacion import instalacion

AHORA = datetime(2026, 10, 13, 9, 0)
CONTRASENA_FIRMA = "una contrasena de firma larga"
PROHIBIDAS = (
    "costo",
    "cache_lectura",
    "cache_escritura",
    '"entrada"',
    '"salida"',
    "topes",
    "sk-ant-",
)


@pytest.fixture(scope="module")
def _con_sesion(tmp_path_factory):
    return plantilla_s4(tmp_path_factory.mktemp("paquete_ia") / "s4.db")


@pytest.fixture(scope="module")
def _of001(tmp_path_factory):
    return plantilla_of001(tmp_path_factory.mktemp("paquete_of") / "of001.db")


@pytest.fixture
def base_of(_of001, tmp_path):
    copia = tmp_path / "of001.db"
    shutil.copy(_of001, copia)
    return copia


@pytest.fixture
def base_con_sesion_ia(_con_sesion, tmp_path):
    copia = tmp_path / "s4.db"
    shutil.copy(_con_sesion, copia)
    return copia


def _version(sesion, codigo: str = VERSION) -> models.Presupuesto:
    return sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == PROYECTO, models.Presupuesto.codigo == codigo)
    ).one()


def exportar(base, carpeta, *, firmar: bool = False) -> tuple[bytes, object]:
    """El `.silice` de la version 001; con `firmar`, la empresa emisora firma con su clave."""
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion, instalacion(carpeta / "emisor") as bd:
            entrega.con_anexos_de_cadena(sesion)
            contrasena = None
            if firmar:
                empresas.guardar_empresa_propia(
                    bd, "Emisora Ficticia", "J-0001", "Caracas", "adm", AHORA
                )
                empresas.generar_clave(bd, CONTRASENA_FIRMA, "adm", AHORA)
                contrasena = CONTRASENA_FIRMA
            hecho = entrega.entregar(
                sesion,
                bd,
                _version(sesion),
                usuario="ana",
                ahora=AHORA,
                version_silice="0.9.0",
                contrasena_clave=contrasena,
            )
            publica = (
                empresas.exportar_clave_publica_propia(bd, AHORA) if firmar else None,
                empresas.clave_activa(bd).publica if firmar else None,
            )
    finally:
        motor.dispose()
    return hecho, publica


def verificar_en_otra_instalacion(datos: bytes, carpeta, publica=None):
    """El receptor registra la clave publica del emisor (huella corta leida por telefono)."""
    with instalacion(carpeta / "receptor") as bd:
        if publica is not None:
            archivo, cruda = publica
            empresas.registrar_empresa_ajena(
                bd, archivo, firma.huella_corta(cruda), "Pedro", "telefono", "adm", AHORA
            )

        def buscar(huella: str):
            fila = bd.scalars(
                select(EmpresaRegistrada).where(EmpresaRegistrada.huella == huella)
            ).first()
            if fila is None:
                return None
            return EmpresaConocida(fila.empresa, fila.publica, fila.estado, fila.fecha_estado)

        return verificar(datos, buscar_empresa=buscar, recibido_en=AHORA)


def rehacer(datos: bytes, cambios: dict[str, bytes]) -> bytes:
    """El mismo ZIP con algunos archivos reemplazados (mismo orden y compresion)."""
    salida = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(datos)) as viejo, zipfile.ZipFile(salida, "w") as nuevo:
        for info in viejo.infolist():
            nuevo.writestr(info, cambios.get(info.filename, viejo.read(info.filename)))
    return salida.getvalue()


def leer(datos: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(datos)) as archivo:
        return {n: archivo.read(n) for n in archivo.namelist()}


def test_el_paquete_trae_ia_json_sin_uso_ni_costo_ni_clave(base_con_sesion_ia, tmp_path):
    hecho, _ = exportar(base_con_sesion_ia, tmp_path)
    archivos = leer(hecho.datos)
    anexo = archivos["anexos/ia.json"].decode("utf-8")
    documento = json.loads(anexo)
    assert documento["formato"] == "silice-ia" and documento["version_formato"] == 1
    (sesion,) = documento["sesiones"]
    assert sesion["pedido"] == PEDIDO and sesion["proveedor"] == "claude"
    assert [(c["herramienta"], c["resultado"]) for c in sesion["llamadas"]] == [
        ("proponer_ambiente", "valida"),
        ("terminar", "valida"),
    ]
    (propuesta,) = sesion["propuestas"]
    assert propuesta["decidida_por"] == QUIEN and propuesta["estado"] == "aceptada"
    assert propuesta["citas"] == [[c["campo"], c["texto"]] for c in AMBIENTE["citas"]]
    assert not [p for p in PROHIBIDAS if p in anexo]
    manifiesto = json.loads(archivos["manifiesto.json"])
    listados = {a["nombre"] for a in manifiesto["archivos"]}
    assert "anexos/ia.json" in listados
    sin_firma = verificar_en_otra_instalacion(hecho.datos, tmp_path)
    assert (sin_firma.estado, sin_firma.motivo) == (NO_VERIFICADO, "sin_firma")


def test_el_paquete_firmado_con_ia_json_se_verifica_en_otra_instalacion(
    base_con_sesion_ia, tmp_path
):
    hecho, publica = exportar(base_con_sesion_ia, tmp_path, firmar=True)
    assert hecho.firmado and "anexos/ia.json" in leer(hecho.datos)
    resultado = verificar_en_otra_instalacion(hecho.datos, tmp_path, publica)
    assert (resultado.estado, resultado.motivo) == (VERIFICADO, "firma_valida")
    assert resultado.empresa_verificada == "Emisora Ficticia"


def test_alterar_un_byte_de_ia_json_da_alterado(base_con_sesion_ia, tmp_path):
    hecho, publica = exportar(base_con_sesion_ia, tmp_path, firmar=True)
    original = leer(hecho.datos)["anexos/ia.json"]
    alterado = original.replace(b'"decidida_por":"ana"', b'"decidida_por":"eva"')
    assert alterado != original and len(alterado) == len(original)  # un byte, mismo tamano
    resultado = verificar_en_otra_instalacion(
        rehacer(hecho.datos, {"anexos/ia.json": alterado}), tmp_path, publica
    )
    assert (resultado.estado, resultado.motivo) == (ALTERADO, "integridad")
    assert resultado.detalle == "anexos/ia.json cambió después de firmarse"


def test_rehacer_la_entrada_del_manifiesto_no_basta_la_huella_de_anexos_lo_delata(
    base_con_sesion_ia, tmp_path
):
    """El atacante cambia `ia.json` y rehace su sha256 y tamano en el manifiesto, pero no la
    `huella_anexos`: la integridad lo delata. Si rehace tambien la huella, la firma lo delata."""
    hecho, publica = exportar(base_con_sesion_ia, tmp_path, firmar=True)
    archivos = leer(hecho.datos)
    alterado = archivos["anexos/ia.json"].replace(b'"ana"', b'"eva"')
    manifiesto = json.loads(archivos["manifiesto.json"])
    for entrada in manifiesto["archivos"]:
        if entrada["nombre"] == "anexos/ia.json":
            entrada["sha256"] = hashlib.sha256(alterado).hexdigest()
            entrada["tamano"] = len(alterado)
    a_medias = rehacer(
        hecho.datos,
        {"anexos/ia.json": alterado, "manifiesto.json": json.dumps(manifiesto).encode()},
    )
    resultado = verificar_en_otra_instalacion(a_medias, tmp_path, publica)
    assert (resultado.estado, resultado.motivo) == (ALTERADO, "integridad")
    assert "huella de anexos" in resultado.detalle

    anexos = {n: b for n, b in archivos.items() if n.startswith("anexos/")}
    anexos["anexos/ia.json"] = alterado
    manifiesto["huella_anexos"] = huella_de_anexos(anexos)
    completo = rehacer(
        hecho.datos,
        {"anexos/ia.json": alterado, "manifiesto.json": json.dumps(manifiesto).encode()},
    )
    resultado = verificar_en_otra_instalacion(completo, tmp_path / "otra", publica)
    assert (resultado.estado, resultado.motivo) == (ALTERADO, "firma")


def test_sin_sesiones_aceptadas_el_paquete_no_trae_ia_json(tmp_path):
    base = tmp_path / "s4.db"
    plantilla_s4(base, estado=EstadoPropuesta.RECHAZADA)
    hecho, _ = exportar(base, tmp_path)
    assert "anexos/ia.json" not in leer(hecho.datos)


def test_una_base_sin_las_tablas_ia_exporta_sin_el_anexo(base_of, tmp_path):
    """Una base anterior a la 0.9.0 (sin `ia_*`): el anexo es opcional y la entrega no falla."""
    hecho, _ = exportar(base_of, tmp_path)
    assert "anexos/ia.json" not in leer(hecho.datos)


@pytest.mark.parametrize(
    ("guardada", "hasta", "entra"),
    [
        ("001", "001", True),
        ("002", "001", False),  # guardada despues: no es de esa version
        ("009", "010", True),
        ("010", "010", True),  # frontera: la misma version
        ("011", "010", False),  # frontera + 1
    ],
)
def test_el_anexo_trae_solo_lo_guardado_hasta_esa_version(base_of, guardada, hasta, entra):
    base = base_of
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema_ia(motor)
    finally:
        motor.dispose()
    sesion_en_base(base, version=guardada)
    sesion_en_base(base, version=None)  # una sesion aceptada que no se guardo: nunca entra
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with motor.connect() as con:
            anexo = anexo_ia(con, PROYECTO, hasta)
            assert anexo_ia(con, "OTRO PROYECTO", hasta) is None
    finally:
        motor.dispose()
    if entra:
        assert [s["version_guardada"] for s in json.loads(anexo)["sesiones"]] == [guardada]
    else:
        assert anexo is None
