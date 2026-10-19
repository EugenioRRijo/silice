"""Revisar un paquete `.silice` o un presupuesto de otra herramienta (UC-23; spec S3 §9 y §10).

Quien revisa elige un archivo y la pantalla lo **verifica** (banner de estado y banner de versión),
lo **reaudita** con las reglas de esta instalación, lo **compara** con la entrega anterior y con su
propia lista de precios, muestra **quién cambió qué**, avisa si quien revisa es quien armó, regenera
el Excel **en esta instalación** (el del emisor no viaja y no se ofrece) y guarda el **dictamen**
atado al SHA-256 del archivo. Todo en memoria: el caso no cambia salvo el registro de lo recibido
y el dictamen. Todo texto del paquete pasa por `texto_seguro`.

El análisis (verificar, reauditar, comparar) se calcula una vez por archivo y se guarda en
`st.session_state` con una clave propia: mover el dictamen o elegir otra lista no lo repite. Los
dos Excel se generan solo al pulsar. La pantalla trabaja con ids, no con objetos ORM de otro ciclo.
"""

from __future__ import annotations

import hashlib
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from sqlalchemy.orm import Session

from core.budget.comparacion import Diferencia
from core.catalog import abrir_sesion_de_escritura, crear_motor
from core.verification.texto import formatear_decimal
from operacion.base_datos import ErrorDeBase, preparar_base
from operacion.config import carpeta_datos
from paquete import modelo as paq
from paquete.formato import PaqueteRechazado
from paquete.verificar import banner
from seguridad.json_estricto import JsonRechazado
from seguridad.permisos import Accion
from ui import revision
from ui import sesion as ui_sesion
from ui.caso import ruta_caso
from ui.texto_seguro import texto_seguro

COLORES = {"verde": st.success, "ambar": st.warning, "rojo": st.error}
CARPETA_PAQUETES = "paquetes"
CLAVE_ESTADO = "revisar_estado"  # lo analizado de un archivo: no es clave de ningún widget
CLAVE_EXCEL = "revisar_excel"  # (sha, nombre, octetos) del Excel pedido


def _ahora() -> datetime:
    return ui_sesion.ahora()


def servicios_de_la_instalacion(caso: Session) -> revision.Servicios:
    """La referencia MaPreX y las tasas de ESTA instalación (S1). Las pruebas lo sustituyen."""
    from auditoria.servicios import servicios_de_la_instalacion as armar

    return armar(caso)


Analisis = revision.Analisis  # vive en la capa de aplicación (T7): la comparte la API


# --- piezas de la pantalla ------------------------------------------------------------------


def _tabla_diferencia(d: Diferencia, titulo: str) -> None:
    st.subheader(titulo)
    columnas = st.columns(3)
    columnas[0].metric("Total antes", formatear_decimal(d.total_1, 2))
    columnas[1].metric("Total después", formatear_decimal(d.total_2, 2))
    columnas[2].metric("Diferencia", formatear_decimal(d.total_2 - d.total_1, 2))
    st.caption(texto_seguro(revision.texto_por_cantidad_y_precio(d)))
    st.dataframe(
        [
            {
                "Partida": texto_seguro(p.codigo_partida),
                "Descripción": texto_seguro(p.descripcion),
                "Estado": p.estado,
                "Δ cantidad": formatear_decimal(p.desvio_cantidad, 2),
                "Δ precio": formatear_decimal(p.desvio_precio, 2),
                "Δ total": formatear_decimal(p.desvio_total, 2),
            }
            for p in d.partidas
            if p.estado != "igual"
        ],
        hide_index=True,
    )


def _hallazgos(r: revision.Reauditoria) -> None:
    for campo, titulo in revision.TITULOS_DE_HALLAZGOS:
        lote = getattr(r, campo)
        st.subheader(f"{titulo} ({len(lote)})")
        st.dataframe(
            [
                {
                    "Regla": h.regla,
                    "Severidad": h.severidad.name,
                    "Descripción": texto_seguro(h.descripcion),
                }
                for h in lote
            ],
            hide_index=True,
        )


def _diferencias_de_precio(r: revision.Reauditoria) -> None:
    if not r.diferencias:
        st.success(revision.PRECIOS_COINCIDEN)
        return
    st.error(revision.PRECIOS_NO_COINCIDEN)
    st.dataframe(
        [
            {
                "Partida": texto_seguro(d.codigo_partida),
                "Campo": d.campo,
                "Declarado": formatear_decimal(d.declarado, 4),
                "Recalculado": formatear_decimal(d.recalculado, 4),
                "Diferencia": formatear_decimal(d.monto, 2),
            }
            for d in r.diferencias
        ],
        hide_index=True,
    )


def _contra_mi_lista(caso: Session, r: revision.Reauditoria) -> None:
    listas = {x.id: x for x in revision.listas_del_caso(caso)}
    if not listas:
        st.caption(revision.SIN_LISTAS)
        return
    eleccion = st.selectbox(
        "Contrastar con mi lista",
        list(listas),
        key="rev_lista",
        format_func=lambda i: texto_seguro(listas[i].nombre),
    )
    diferencia, revalorado = revision.contra_mi_lista(caso, r.documento, listas[eleccion])
    _tabla_diferencia(diferencia, revision.TITULO_CONTRA_MI_LISTA)
    no_contrastables = revision.texto_de_no_contrastables(revalorado)
    if no_contrastables:
        st.caption(texto_seguro(no_contrastables))


def _cambios(a: Analisis) -> None:
    st.subheader(texto_seguro(revision.titulo_de_cambios(a.previa is not None)))
    st.dataframe(
        [{k: texto_seguro(str(x)) for k, x in c.items()} for c in a.cambios], hide_index=True
    )


def _dictamen(caso: Session, a: Analisis, revisor: str) -> None:
    sha = a.recibido.verificacion.sha256
    for d in paq.dictamenes_de(caso, sha):
        st.caption(texto_seguro(revision.texto_de_dictamen(d)))
    with st.form("rev_dictamen", clear_on_submit=True):
        resultado = st.radio("Dictamen", paq.RESULTADOS, key="rev_resultado")
        notas = st.text_area("Notas", key="rev_notas")
        enviar = st.form_submit_button("Guardar dictamen", type="primary", key="rev_enviar")
    if not enviar:
        return
    try:
        revision.dictaminar(
            caso,
            a.recibido,
            resultado=resultado,
            notas=notas,
            revisor=revisor,
            ahora=_ahora(),
            armo=bool(a.armo),
        )
    except ValueError as error:
        st.error(texto_seguro(str(error)))
        return
    st.success(revision.DICTAMEN_GUARDADO)


def _excel(a: Analisis) -> None:
    """Los dos Excel se regeneran en esta instalación y solo al pulsar (el del emisor no viaja)."""
    r = a.reauditoria
    sha = a.recibido.verificacion.sha256
    columnas = st.columns(2)
    if columnas[0].button("Preparar el Excel del presupuesto", key="rev_preparar_presupuesto"):
        st.session_state[CLAVE_EXCEL] = (
            sha,
            revision.nombre_de_excel("presupuesto", sha),
            revision.excel_de_presupuesto(r),
        )
    if columnas[1].button("Preparar el Excel de la revisión", key="rev_preparar_revision"):
        st.session_state[CLAVE_EXCEL] = (
            sha,
            revision.nombre_de_excel("revision", sha),
            revision.excel_de_revision(a.recibido.verificacion, r, a.diferencia, list(a.cambios)),
        )
    listo = st.session_state.get(CLAVE_EXCEL)
    if listo and listo[0] == sha:
        st.download_button(
            f"Descargar {listo[1]}",
            listo[2],
            file_name=listo[1],
            key="rev_bajar_excel",
        )
        st.caption(revision.NOTA_EXCEL)


# --- el flujo del paquete -------------------------------------------------------------------


def _analizar(datos: bytes, nombre: str, caso: Session, bd: Session, sesion) -> Analisis:
    return revision.analizar(
        datos,
        nombre,
        caso=caso,
        instalacion=bd,
        carpeta_paquetes=carpeta_datos() / CARPETA_PAQUETES,
        revisor=sesion.usuario,
        login=sesion.login,
        ahora=_ahora(),
        servicios=lambda: servicios_de_la_instalacion(caso),
    )


def _encabezado(a: Analisis) -> None:
    v = a.recibido.verificacion
    color, texto = banner(v, texto_seguro)
    COLORES.get(color, st.error)(texto)
    if v.manifiesto is not None:
        st.caption(texto_seguro(revision.banner_de_version(a.recibido)))
    ayuda = revision.ayuda_de_registro(v)
    if ayuda:
        st.caption(texto_seguro(ayuda))
    for aviso in revision.avisos_visibles(a.recibido):  # «ya recibió» lo dice el banner de versión
        st.warning(texto_seguro(aviso))
    if v.cadena:
        retroactiva = revision.declaracion_retroactiva(v.cadena)
        if retroactiva:
            st.caption(texto_seguro(retroactiva))
    aviso_armo = revision.aviso_de_quien_armo(a.armo)
    if aviso_armo:
        st.warning(texto_seguro(aviso_armo))


def _paquete(sesion) -> None:
    archivo = st.file_uploader("Paquete .silice", key="rev_archivo")
    if archivo is None:
        st.caption("Elija el archivo `.silice` que recibió.")
        return
    datos = archivo.getvalue()
    ruta = ruta_caso()
    try:
        preparar_base(ruta)  # RV-5: la única puerta a la base del caso
    except ErrorDeBase as error:
        st.error(texto_seguro(str(error)))
        return
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion_de_escritura(motor) as caso, ui_sesion.instalacion() as bd:
            guardado = st.session_state.get(CLAVE_ESTADO)
            sha = hashlib.sha256(datos).hexdigest()
            if (
                guardado is None
                or guardado.sha_del_archivo != sha
                or guardado.login != sesion.login
            ):
                try:
                    guardado = _analizar(datos, archivo.name, caso, bd, sesion)
                except (PaqueteRechazado, JsonRechazado, ValueError) as error:
                    st.error(texto_seguro(str(error)))
                    return
                st.session_state[CLAVE_ESTADO] = guardado
            _encabezado(guardado)
            v = guardado.recibido.verificacion
            if not v.legible:  # rechazado: el banner ya dijo el motivo y no hay qué auditar
                return
            r = guardado.reauditoria
            for aviso in r.avisos:
                st.warning(texto_seguro(aviso))
            if r.resultado is None:
                return
            st.metric("Total recalculado", formatear_decimal(r.total_recalculado, 2))
            st.caption(texto_seguro(revision.texto_de_reglas(r)))
            _diferencias_de_precio(r)
            _hallazgos(r)
            if guardado.previa is not None and guardado.diferencia is not None:
                _tabla_diferencia(
                    guardado.diferencia,
                    texto_seguro(revision.titulo_contra_anterior(guardado.previa.codigo)),
                )
            else:
                st.caption(revision.SIN_ENTREGA_ANTERIOR)
            _contra_mi_lista(caso, r)
            _cambios(guardado)
            _excel(guardado)
            _dictamen(caso, guardado, sesion.usuario)
    except (PaqueteRechazado, JsonRechazado, ValueError) as error:
        st.error(texto_seguro(str(error)))
    finally:
        motor.dispose()


def _excel_externo() -> None:
    st.download_button(
        "Descargar la plantilla del formato",
        revision.plantilla_uc05(),
        file_name="plantilla-presupuesto.xlsx",
        key="rev_plantilla",
    )
    archivo = st.file_uploader("Presupuesto en Excel", type=["xlsx"], key="rev_excel")
    if archivo is None:
        return
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "externo.xlsx"
        ruta.write_bytes(archivo.getvalue())
        try:
            importado, informe = revision.auditar_excel_externo(ruta)
        except (ValueError, KeyError) as error:
            st.error(texto_seguro(str(error)))
            return
    st.warning(revision.EXCEL_NO_VERIFICADO)
    st.metric("Total", formatear_decimal(importado.presupuesto.total, 2))
    st.dataframe(
        [
            {
                "Regla": h.regla,
                "Severidad": h.severidad.name,
                "Descripción": texto_seguro(h.descripcion),
            }
            for h in informe.hallazgos
        ],
        hide_index=True,
    )


def render() -> None:
    sesion = ui_sesion.exigir(Accion.REVISAR_PAQUETE)
    pestanas = st.tabs(["Paquete .silice", "Presupuesto en Excel"])
    with pestanas[0]:
        _paquete(sesion)
    with pestanas[1]:
        _excel_externo()
