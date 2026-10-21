"""VB-1 de punta a punta: Entregar un presupuesto con un equipo fraccionario (rendimiento 12,
equipos = 1/12) y que Revisar lo lea y verifique la firma. Antes Revisar respondia 422
«cifra fuera del patron estricto» (expediente `docs/bitacora/2026-10-21-VB1-expediente-core.md`).

Tambien: una version sellada ANTES de la correccion (con 29 decimales en su huella) sigue abriendo
sin «cadena rota» (bases existentes deben abrir; NORMAS §9).

Oraculos: el texto de los equipos es el literal 1/12 a 28 decimales, escrito a mano; la firma se
verifica con `paquete.verificar` sobre los bytes del ZIP.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from auditoria.reauditoria import leer_documento
from core import models
from core.budget import (
    cadena,
    canonico,
)
from core.catalog import abrir_sesion
from paquete.verificar import VERIFICADO, EmpresaConocida, verificar
from seguridad import empresas, firma
from seguridad.modelo import EmpresaRegistrada
from tests.fixtures.canonico_minimo import USUARIO
from tests.fixtures.instalacion import AHORA, instalacion
from tests.fixtures.vb1_fraccionario import (
    UN_DOCEAVO_28,
    UN_DOCEAVO_29,
    sembrar_fraccionaria,
)
from ui import entrega

CLAVE = "frase de firma larga y propia"
EMPRESA = "Contratista Demo, C.A."
CUANDO = datetime(2026, 11, 10, 9, 30)
RECIBIDO = datetime(2026, 11, 11, 8, 0)


def _equipos_del_documento(datos: bytes) -> str:
    return json.loads(datos)["renglones"][0]["equipos"]


def test_entregar_y_revisar_un_equipo_fraccionario_verifica_la_firma(motor, tmp_path: Path) -> None:
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "emisor") as bd:
        empresas.guardar_empresa_propia(bd, EMPRESA, "J-00000000-0", "", "ana", AHORA)
        _, version = sembrar_fraccionaria(caso, anexos_de=entrega.anexos_de_cadena)
        empresas.generar_clave(bd, CLAVE, "ana", AHORA)
        e = entrega.entregar(
            caso,
            bd,
            version,
            usuario=USUARIO,
            ahora=CUANDO,
            version_silice="0.8.0",
            contrasena_clave=CLAVE,
            destinatario="Cliente S.A.",
        )
        assert e.firmado
        with instalacion(tmp_path / "revisor") as rev:
            archivo = empresas.exportar_clave_publica_propia(bd, AHORA)
            leida = firma.huella_corta(empresas.clave_activa(bd).publica)
            empresas.registrar_empresa_ajena(
                rev, archivo, leida, "Ing. Pedro, por telefono", "telefono", "revisor", AHORA
            )

            def buscar(huella: str) -> EmpresaConocida | None:
                f = rev.scalars(
                    select(EmpresaRegistrada).where(EmpresaRegistrada.huella == huella)
                ).first()
                return (
                    None
                    if f is None
                    else EmpresaConocida(f.empresa, f.publica, f.estado, f.fecha_estado)
                )

            v = verificar(e.datos, buscar_empresa=buscar, recibido_en=RECIBIDO)
    assert v.estado == VERIFICADO and v.motivo == "firma_valida"
    assert _equipos_del_documento(v.archivos["presupuesto.json"]) == UN_DOCEAVO_28
    leido = leer_documento(v.archivos)  # Revisar: antes, «cifra fuera del patron estricto»
    assert leido.declarados[0].equipos == Decimal(UN_DOCEAVO_28)
    assert abs(leido.declarados[0].equipos - Decimal(1) / Decimal(12)) < Decimal("1E-28")


def test_una_version_sellada_antes_de_la_correccion_no_aparece_como_cadena_rota(motor) -> None:
    with abrir_sesion(motor) as caso:
        with canonico.formato_legado():  # como se sellaba antes: 29 decimales en la huella
            proyecto, version = sembrar_fraccionaria(caso)
            assert UN_DOCEAVO_29 in canonico.documento(caso, version).decode()
        assert UN_DOCEAVO_28 in canonico.documento(caso, version).decode()
        resultado = cadena.verificar_cadena(caso, proyecto)
        assert resultado.integra, resultado
        # y una alteracion real sigue detectandose
        fila = caso.scalars(
            select(models.PartidaPresupuestada).where(
                models.PartidaPresupuestada.presupuesto_id == version.id
            )
        ).one()
        fila.materiales = Decimal("15")
        caso.flush()
        assert not cadena.verificar_cadena(caso, proyecto).integra


def test_una_version_nueva_sella_con_la_cifra_cuantizada(motor) -> None:
    with abrir_sesion(motor) as caso:
        proyecto, version = sembrar_fraccionaria(caso)
        assert UN_DOCEAVO_29 not in canonico.documento(caso, version).decode()
        assert cadena.verificar_cadena(caso, proyecto).integra
