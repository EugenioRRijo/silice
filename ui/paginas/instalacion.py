"""Pestaña «Instalación»: red local y API, respaldos y eventos de seguridad perdidos (RF-98; spec S5
§5.2 y §6.5). Los cambios de red no se hacen desde el navegador.

`render_pestana()` es el cuerpo de la pestaña «Instalación» de la página Administración
(`ui.paginas.administracion.PESTANAS`, S3-3); ya no es una pantalla propia del menú.
"""

from __future__ import annotations

import json

import streamlit as st

# RM-1 (ola de Administracion): la logica sin Streamlit vive en aplicacion/instalacion.py.
from aplicacion.instalacion import JuegoResumen as JuegoResumen
from aplicacion.instalacion import juegos_de_respaldo as juegos_de_respaldo
from aplicacion.instalacion import zip_del_juego as zip_del_juego
from operacion import base_datos, config, eventos_perdidos
from ui import cliente
from ui.texto_seguro import texto_seguro


def _red_y_api() -> None:
    ajustes = config.cargar_ajustes(config.ruta_ajustes())
    for aviso in ajustes.avisos:
        st.warning(aviso)
    if ajustes.red_local:
        st.markdown(f"Red local: encendida en http://{ajustes.direccion}:{ajustes.puerto}")
    else:
        st.markdown(f"Red local: apagada (solo http://127.0.0.1:{ajustes.puerto})")
    st.markdown(
        f"API: {'activa' if ajustes.api_activa else 'apagada'} (puerto {ajustes.puerto_api})"
    )
    st.caption(
        "Para cambiar la red local use, en el equipo servidor, el acceso «Sílice: red local "
        "(administrador)». La API se activa en silice.toml y entra en vigor al reiniciar."
    )


def _respaldos() -> None:
    st.subheader("Respaldos")
    if st.button("Crear respaldo ahora", key="crear_respaldo"):
        st.success(f"Respaldo creado: {base_datos.respaldar_todo().name}")
    juegos = juegos_de_respaldo()
    for juego in juegos:
        st.markdown(f"- {texto_seguro(juego.nombre)} ({juego.motivo}, {juego.bases} bases)")
    if not juegos:
        st.caption("Todavía no hay respaldos.")
        return
    permitida, motivo = cliente.operacion_sensible_permitida()
    if not permitida:
        st.error(motivo)
        return
    elegido = st.selectbox("Descargar", [j.nombre for j in juegos], key="juego_elegido")
    st.warning(
        "El respaldo trae huellas de contraseñas y la clave de firma cifrada: guárdelo bien."
    )
    if st.button("Preparar descarga", key="preparar_descarga"):
        carpeta = next(j.carpeta for j in juegos if j.nombre == elegido)
        st.download_button(
            "Descargar el juego (.zip)",
            zip_del_juego(carpeta),
            f"{elegido}.zip",
            on_click="ignore",
        )


def _eventos() -> None:
    pendientes = eventos_perdidos.pendientes()
    if not pendientes:
        return
    st.error(
        "Las operaciones sensibles están bloqueadas: se restauró un respaldo y hay eventos de "
        "seguridad perdidos sin revisar."
    )
    for archivo in pendientes:
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {}
        if not isinstance(datos, dict):
            datos = {}
        with st.expander(archivo.name, expanded=True):
            diferencias = datos.get("diferencias")
            eventos = datos.get("eventos")
            for dif in diferencias if isinstance(diferencias, list) else []:
                if not isinstance(dif, dict):
                    continue
                st.markdown(
                    f"- {texto_seguro(str(dif.get('tipo')))}: "
                    f"{texto_seguro(str(dif.get('tabla')))} "
                    f"{texto_seguro(str(dif.get('etiqueta')))}"
                )
            st.markdown(
                "Eventos de acceso posteriores al respaldo: "
                f"{len(eventos) if isinstance(eventos, list) else 0}"
            )
            st.caption("Vuelva a aplicar lo que corresponda (revocar, desactivar) y luego marque.")
            confirmado = st.checkbox("Ya revisé esto", key=f"confirmar_{archivo.name}")
            if st.button(
                "Marcar como revisado", key=f"revisar_{archivo.name}", disabled=not confirmado
            ):
                eventos_perdidos.marcar_revisado(archivo, por="administrador")
                st.rerun()


def render_pestana() -> None:
    _red_y_api()
    _respaldos()
    _eventos()
