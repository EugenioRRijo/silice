"""Entregar el paquete auditado (UC-22; spec S3 §8.2; RF-85).

El rol *arma* elige un proyecto y una versión, ve lo que va a viajar (total, hallazgos, cadena,
anexos, empresa y si hay clave de firma) y descarga el `.silice`. Si hay clave de firma, pide su
contraseña **en un formulario que se vacía al enviar** y solo desde el propio equipo
(`exigir_local`); sin clave, el paquete sale «sin firma» y la pantalla lo dice. Una cadena rota
impide entregar y se muestra con su mensaje. La base del caso no cambia.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from importlib import metadata

import streamlit as st
from sqlalchemy import select

from core import models
from core.catalog import abrir_sesion, crear_motor
from core.verification.texto import formatear_decimal
from operacion.base_datos import ErrorDeBase, preparar_base
from paquete.formato import PaqueteRechazado
from seguridad.empresas import ContrasenaDeClaveIncorrecta
from seguridad.permisos import Accion, Sensible
from ui import entrega
from ui import sesion as ui_sesion
from ui.caso import proyecto_abierto, ruta_caso
from ui.texto_seguro import texto_seguro

CLAVE_ULTIMA = "entregar_ultima"  # la última `Entrega` generada, para mostrar su descarga


def version_de_silice() -> str:
    try:
        return metadata.version("silice")
    except metadata.PackageNotFoundError:  # corrida desde el código fuente sin instalar
        return "0.8.0"


def _ahora() -> datetime:
    return ui_sesion.ahora()


def _resumen(resumen: entrega.Resumen) -> None:
    columnas = st.columns(3)
    columnas[0].metric("Total", formatear_decimal(resumen.total.quantize(Decimal("0.01"))))
    columnas[1].metric("Hallazgos", sum(resumen.hallazgos_por_severidad.values()))
    columnas[2].metric("Cadena", "íntegra" if resumen.cadena_integra else "ROTA")
    if resumen.hallazgos_por_severidad:
        st.caption(
            ", ".join(
                f"{texto_seguro(str(n))} {texto_seguro(k.lower())}"
                for k, n in sorted(resumen.hallazgos_por_severidad.items())
            )
        )
    if not resumen.cadena_integra:
        st.error(texto_seguro(resumen.mensaje_de_cadena))
        st.caption(
            "Un paquete con la cadena rota no se entrega: restaure la base desde un "
            "respaldo (Administración, pestaña Instalación) o avise a quien "
            "administra Sílice."
        )
    nombres = [a.removeprefix("anexos/").removesuffix(".json") for a in resumen.anexos]
    st.caption(
        "Viaja con: "
        + ", ".join(texto_seguro(n) for n in ("presupuesto", "informe", "cadena", *nombres))
        + "."
    )
    if resumen.empresa is None:
        st.warning("Todavía no hay empresa en Administración: el paquete no dirá quién lo emite.")
    elif not resumen.firma_disponible:
        st.warning(
            "No hay clave de firma: el paquete saldrá SIN FIRMA y quien lo reciba lo "
            "verá como «no verificado»."
        )


def render() -> None:
    ui_sesion.exigir(Accion.ENTREGAR_PAQUETE)
    ruta = ruta_caso()
    try:
        preparar_base(ruta)  # RV-5: la única puerta a la base del caso
    except ErrorDeBase as error:
        st.error(texto_seguro(str(error)))
        return
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as caso, ui_sesion.instalacion() as bd:
            proyectos = caso.scalars(select(models.Proyecto).order_by(models.Proyecto.nombre)).all()
            if not proyectos:
                st.info("Este caso todavía no tiene proyectos.")
                return
            por_id = {p.id: p for p in proyectos}  # ids: un objeto de otro ciclo ya no sirve
            abierto = proyecto_abierto()  # el de la barra superior, si hay uno
            ids = list(por_id)
            inicial = next((n for n, i in enumerate(ids) if por_id[i].nombre == abierto), 0)
            proyecto = por_id[
                st.selectbox(
                    "Proyecto",
                    ids,
                    index=inicial,
                    format_func=lambda i: por_id[i].nombre,
                    key="entregar_proyecto",
                )
            ]
            versiones = sorted(proyecto.presupuestos, key=lambda v: v.id, reverse=True)
            if not versiones:
                st.info("Este proyecto todavía no tiene versiones.")
                return
            codigos = {v.id: v for v in versiones}
            version = codigos[
                st.selectbox(
                    "Versión",
                    list(codigos),
                    format_func=lambda i: codigos[i].codigo,
                    key="entregar_version",
                )
            ]
            resumen = entrega.resumen_de_entrega(caso, bd, version)
            _resumen(resumen)
            with st.form("entregar_formulario", clear_on_submit=True):
                destinatario = st.text_input("Para quién es (opcional)", key="entregar_destino")
                contrasena = st.text_input(
                    "Contraseña de la clave de firma",
                    type="password",
                    key="entregar_clave",
                    disabled=not resumen.firma_disponible,
                )
                enviar = st.form_submit_button(
                    "Generar paquete",
                    type="primary",
                    key="entregar_enviar",
                    disabled=not resumen.cadena_integra,
                )
            if enviar:
                st.session_state.pop(CLAVE_ULTIMA, None)  # no dejar un paquete anterior a la vista
                firmar = resumen.firma_disponible
                if firmar:
                    ui_sesion.exigir_local(Sensible.FIRMAR)
                try:
                    generada = entrega.entregar(
                        caso,
                        bd,
                        version,
                        usuario=ui_sesion.responsable_actual(),
                        ahora=_ahora(),
                        version_silice=version_de_silice(),
                        destinatario=destinatario.strip() or None,
                        contrasena_clave=contrasena if firmar else None,
                    )
                    st.session_state[CLAVE_ULTIMA] = (version.id, generada)
                except ContrasenaDeClaveIncorrecta:
                    st.error("La contraseña de la clave no es correcta.")
                except (entrega.EntregaRechazada, PaqueteRechazado) as error:
                    st.error(texto_seguro(str(error)))
            version_y_entrega = st.session_state.get(CLAVE_ULTIMA)
            if version_y_entrega is not None and version_y_entrega[0] == version.id:
                ultima = version_y_entrega[1]
                st.success("Paquete listo" + (" y firmado." if ultima.firmado else " (sin firma)."))
                st.caption(f"SHA-256: {texto_seguro(ultima.sha256)}")
                st.download_button(
                    "Descargar el paquete",
                    ultima.datos,
                    file_name=ultima.nombre,
                    mime="application/zip",
                    key="entregar_bajar",
                )
    finally:
        motor.dispose()
