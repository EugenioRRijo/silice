"""Administración de la instalación (UC-21; spec S3 §5.7, §7 y §10; RF-80, RF-84, RF-88, RF-98).

Seis pestañas: Cuentas, Empresa y clave de firma, Empresas registradas, Claves de API, Accesos e
Instalación (red local, API, respaldos y eventos de seguridad perdidos). Solo el rol
*administrador de la instalación* llega aquí (`exigir` es lo primero de `render()`); lo que toca un
secreto (clave de firma, claves de API) exige además el propio equipo (`exigir_local`, S3 §5.6).

Solo se dibuja la pestaña elegida (`st.segmented_control`): una edición en una no vuelve a
ejecutar las demás. Todo nombre que viene de la base pasa por `texto_seguro`; ninguna contraseña ni
clave privada se pinta, se registra ni se queda en la sesión de Streamlit (los campos de contraseña
viven en formularios que se vacían al enviar). La clave de API y la contraseña temporal se
muestran **una vez**.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time

import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from seguridad import claves_api, cuentas, empresas, eventos, firma
from seguridad.modelo import ClaveApi, EmpresaRegistrada, Usuario
from seguridad.permisos import Accion, Rol, Sensible, aviso_de_roles
from seguridad.sesiones import SesionActiva
from ui import cliente
from ui import sesion as ui_sesion
from ui.paginas import instalacion
from ui.texto_seguro import texto_seguro

CLAVE_PESTANA = "adm_pestana"  # no es de widget por contenido: solo recuerda la pestaña elegida
ROLES_ELEGIBLES = tuple(rol.value for rol in Rol)
ETIQUETAS_DE_ROL = {
    "arma": "arma presupuestos (arma)",
    "revisa": "revisa paquetes (revisa)",
    "administrador": "administra la instalación (administrador)",
}
ERRORES_ESPERADOS = (
    cuentas.ErrorDeAcceso,
    cuentas.ContrasenaInvalida,
    empresas.ClaveError,
    PermissionError,
    LookupError,
    ValueError,
)


def _ahora() -> datetime:
    return ui_sesion.ahora()


def _intentar(accion: Callable[[], object], exito: str) -> bool:
    """Corre `accion()`; el mensaje de un error esperado se muestra tal cual, sin traza."""
    try:
        accion()
    except ERRORES_ESPERADOS as error:
        st.error(texto_seguro(str(error)))
        return False
    st.success(exito)
    return True


def _rol(valor: str) -> str:
    return ETIQUETAS_DE_ROL.get(valor, valor)


# --- cuentas -----------------------------------------------------------------------------------


def _actor_de_cuentas(bd: Session, sesion: SesionActiva) -> Usuario | None:
    """La cuenta que firma los cambios de cuentas. Con el acceso apagado no hay cuenta."""
    actor = bd.get(Usuario, sesion.usuario_id)
    if actor is None:
        st.info(
            "El acceso está apagado: aquí se pueden ver las cuentas, pero crearlas o cambiarlas "
            "exige entrar con una cuenta de administrador."
        )
    return actor


def _pestana_cuentas(bd: Session, sesion: SesionActiva) -> None:
    filas = bd.scalars(select(Usuario).order_by(Usuario.login)).all()
    st.dataframe(
        [
            {
                "Usuario": texto_seguro(u.login),
                "Nombre": texto_seguro(u.nombre),
                "Roles": u.roles,
                "Activa": "sí" if u.activo else "no",
            }
            for u in filas
        ],
        hide_index=True,
    )
    actor = _actor_de_cuentas(bd, sesion)
    if actor is None:
        return
    with st.form("adm_crear_cuenta", clear_on_submit=True):
        st.subheader("Crear una cuenta")
        login = st.text_input("Usuario (minúsculas, sin espacios)", key="adm_login")
        nombre = st.text_input("Nombre de la persona", key="adm_nombre")
        roles = st.multiselect(
            "Qué puede hacer", ROLES_ELEGIBLES, format_func=_rol, key="adm_roles"
        )
        temporal = st.text_input(
            "Contraseña temporal (10 a 128 caracteres)", type="password", key="adm_temporal"
        )
        crear = st.form_submit_button("Crear la cuenta", type="primary", key="adm_crear_enviar")
    if crear:
        if _intentar(
            lambda: cuentas.crear_usuario(bd, actor, login, nombre, roles, temporal, _ahora()),
            "Cuenta creada.",
        ):
            st.info("La persona deberá cambiar la contraseña al entrar.")
            aviso = aviso_de_roles([Rol(r) for r in roles])
            if aviso:
                st.warning(aviso)
    if not filas:
        return
    st.subheader("Cambiar una cuenta")
    por_id = {u.id: u for u in filas}  # se eligen ids: un objeto de otro ciclo ya no sirve
    elegida = por_id[
        st.selectbox(
            "Cuenta", list(por_id), key="adm_cuenta", format_func=lambda i: por_id[i].login
        )
    ]
    nuevos = st.multiselect(
        "Qué puede hacer la cuenta",
        ROLES_ELEGIBLES,
        format_func=_rol,
        default=[r for r in elegida.roles.split(",") if r in ROLES_ELEGIBLES],
        key=f"adm_roles_de_{elegida.id}",
    )
    aviso = aviso_de_roles([Rol(r) for r in nuevos])
    if aviso:
        st.caption(aviso)
    columnas = st.columns(3)
    if columnas[0].button("Guardar roles", key="adm_guardar_roles"):
        _intentar(
            lambda: cuentas.cambiar_roles(bd, actor, elegida.id, nuevos, _ahora()),
            "Roles cambiados; sus sesiones se cerraron.",
        )
    if elegida.activo:
        if columnas[1].button("Desactivar", key="adm_desactivar"):
            _intentar(
                lambda: cuentas.desactivar(bd, actor, elegida.id, _ahora()),
                "Cuenta desactivada; sus registros se conservan.",
            )
    elif columnas[1].button("Reactivar", key="adm_reactivar"):
        _intentar(lambda: cuentas.reactivar(bd, actor, elegida.id, _ahora()), "Cuenta reactivada.")
    if columnas[2].button("Desbloquear", key="adm_desbloquear"):
        _intentar(
            lambda: cuentas.desbloquear(bd, actor, elegida.login, _ahora()), "Cuenta desbloqueada."
        )
    with st.form("adm_restablecer_formulario", clear_on_submit=True):
        nueva = st.text_input(
            "Contraseña temporal nueva", type="password", key="adm_restablecer_clave"
        )
        restablecer = st.form_submit_button("Restablecer la contraseña", key="adm_restablecer")
    if restablecer:
        _intentar(
            lambda: cuentas.restablecer(bd, actor, elegida.id, nueva, _ahora()),
            "Contraseña restablecida; sus sesiones se cerraron.",
        )


# --- empresa y clave de firma ------------------------------------------------------------------


def _pestana_empresa(bd: Session, sesion: SesionActiva) -> None:
    propia = empresas.empresa_propia(bd)
    with st.form("adm_empresa"):
        nombre = st.text_input(
            "Nombre de la empresa", value=propia.nombre if propia else "", key="adm_empresa_nombre"
        )
        rif = st.text_input("RIF", value=propia.rif if propia else "", key="adm_empresa_rif")
        ciudad = st.text_input(
            "Ciudad", value=propia.ciudad if propia else "", key="adm_empresa_ciudad"
        )
        guardar = st.form_submit_button("Guardar la empresa", key="adm_empresa_enviar")
    if guardar:
        _intentar(
            lambda: empresas.guardar_empresa_propia(
                bd, nombre, rif, ciudad, sesion.login, _ahora()
            ),
            "Empresa guardada.",
        )
    propia = empresas.empresa_propia(bd)  # de nuevo: acaso se guardó en este mismo ciclo
    clave = empresas.clave_activa(bd)
    if clave is None:
        _generar_clave(bd, sesion, propia is not None)
        return
    st.metric("Huella de la clave de firma", firma.huella_corta(clave.publica))
    st.caption("Léala por teléfono a quien reciba sus paquetes: es lo que comprueba su clave.")
    st.download_button(
        "Descargar la clave pública",
        empresas.exportar_clave_publica_propia(bd, _ahora()),
        file_name="clave-publica.silice-clave",
        key="adm_bajar_publica",
    )
    permitida, motivo = cliente.operacion_sensible_permitida()
    if permitida:
        st.download_button(
            "Descargar el respaldo cifrado de la clave",
            empresas.exportar_respaldo_cifrado(bd),
            file_name="respaldo-clave.silice-respaldo",
            key="adm_bajar_respaldo",
        )
    else:
        st.caption(f"Respaldo de la clave: {motivo}")
    with st.expander("Retirar o revocar la clave"):
        st.caption(
            "Retirar es cambiar de clave sin que se haya comprometido; revocar es para "
            "una clave perdida o expuesta: los paquetes firmados con ella dejan de "
            "verificar. En ambos casos se destruye la clave privada de este equipo."
        )
        with st.form("adm_retirar_formulario", clear_on_submit=True):
            motivo_baja = st.text_input("Motivo", key="adm_motivo_clave")
            contrasena = st.text_input(
                "Contraseña de la clave (para firmar el aviso de revocación; opcional)",
                type="password",
                key="adm_clave_revocar",
            )
            retirar = st.form_submit_button("Retirar", key="adm_retirar")
            revocar = st.form_submit_button("Revocar", key="adm_revocar")
        if retirar or revocar:
            ui_sesion.exigir_local(Sensible.CLAVE_DE_FIRMA)
        if retirar:
            _intentar(
                lambda: empresas.retirar_clave(bd, sesion.login, _ahora(), motivo_baja),
                "Clave retirada. Genere una nueva para volver a firmar.",
            )
        elif revocar:
            if motivo_baja.strip() == "":
                st.error("Escriba el motivo de la revocación.")
                return
            try:
                aviso = empresas.revocar_clave_propia(
                    bd, sesion.login, _ahora(), motivo_baja, contrasena or None
                )
            except ERRORES_ESPERADOS as error:
                st.error(texto_seguro(str(error)))
                return
            st.success("Clave revocada: los paquetes firmados con ella dejan de verificar.")
            if aviso:
                st.download_button(
                    "Descargar el aviso de revocación",
                    aviso,
                    file_name="revocacion.silice-revocacion",
                    key="adm_bajar_aviso",
                )
            else:
                st.warning(
                    "Sin la contraseña no hay aviso firmado: avise por teléfono a quienes "
                    "reciben sus paquetes."
                )


def _generar_clave(bd: Session, sesion: SesionActiva, hay_empresa: bool) -> None:
    if not hay_empresa:
        st.info("Primero guarde el nombre y el RIF de la empresa; después se genera la clave.")
        return
    with st.form("adm_generar_clave", clear_on_submit=True):
        st.subheader("Generar la clave de firma")
        uno = st.text_input(
            "Contraseña de la clave (12 a 128 caracteres)", type="password", key="adm_clave_uno"
        )
        dos = st.text_input("Repítala", type="password", key="adm_clave_dos")
        generar = st.form_submit_button(
            "Generar la clave", type="primary", key="adm_generar_enviar"
        )
    if not generar:
        return
    ui_sesion.exigir_local(Sensible.CLAVE_DE_FIRMA)
    if uno != dos:
        st.error("Las dos contraseñas no coinciden.")
        return
    if _intentar(
        lambda: empresas.generar_clave(bd, uno, sesion.login, _ahora()),
        "Clave generada. Guarde la contraseña: sin ella no se puede firmar.",
    ):
        st.rerun()


# --- empresas registradas ----------------------------------------------------------------------


def _pestana_registradas(bd: Session, sesion: SesionActiva) -> None:
    filas = bd.scalars(select(EmpresaRegistrada).order_by(EmpresaRegistrada.id)).all()
    st.dataframe(
        [
            {
                "Empresa": texto_seguro(f.empresa),
                "Huella": firma.huella_corta(f.publica),
                "Estado": f.estado,
                "Comprobada con": texto_seguro(f.comprobada_con),
                "Método": f.metodo,
            }
            for f in filas
        ],
        hide_index=True,
    )
    if filas:
        _cambiar_registrada(bd, sesion, {f.id: f for f in filas})
    st.subheader("Registrar la clave de otra empresa")
    archivo = st.file_uploader("Archivo de la clave pública (.silice-clave)", key="adm_subir_clave")
    if archivo is None:
        return
    contenido = archivo.getvalue()
    try:
        leida = firma.leer_clave_publica(contenido)
    except ValueError as error:
        st.error(texto_seguro(str(error)))
        return
    st.write(f"Empresa declarada en el archivo: **{texto_seguro(leida.nombre)}**")
    st.metric("Huella calculada del archivo", firma.huella_corta(leida.publica))
    st.caption(
        "Pida a la otra empresa que le lea su huella por teléfono (u otro canal distinto "
        "del que le mandó el archivo) y escríbala aquí."
    )
    with st.form("adm_registrar_ajena", clear_on_submit=True):
        huella = st.text_input("Huella leída por otro canal", key="adm_huella_leida")
        con_quien = st.text_input("Comprobada con (persona)", key="adm_comprobada_con")
        metodo = st.selectbox("Cómo se comprobó", empresas.METODOS, key="adm_metodo")
        registrar = st.form_submit_button(
            "Registrar la empresa", type="primary", key="adm_registrar_enviar"
        )
    if registrar:
        _intentar(
            lambda: empresas.registrar_empresa_ajena(
                bd, contenido, huella, con_quien, metodo, sesion.login, _ahora()
            ),
            "Empresa registrada.",
        )


def _cambiar_registrada(
    bd: Session, sesion: SesionActiva, por_id: dict[int, EmpresaRegistrada]
) -> None:
    with st.expander("Retirar o revocar la clave de una empresa registrada"):
        elegida = por_id[
            st.selectbox(
                "Empresa",
                list(por_id),
                key="adm_ajena",
                format_func=lambda i: texto_seguro(por_id[i].empresa),
            )
        ]
        st.caption(
            "Retirada: la empresa avisó que cambió de clave; sus paquetes anteriores a la "
            "fecha siguen valiendo. Revocada: ningún paquete con esa clave verifica."
        )
        fecha = st.date_input("Fecha del retiro", value=_ahora().date(), key="adm_ajena_fecha")
        if st.button("Marcar como retirada", key="adm_ajena_retirar"):
            _intentar(
                lambda: empresas.retirar_ajena(
                    bd, elegida.id, datetime.combine(fecha, time.min), sesion.login, _ahora()
                ),
                "Clave marcada como retirada.",
            )
        motivo = st.text_input("Motivo de la revocación", key="adm_ajena_motivo")
        aviso = st.file_uploader("Aviso de revocación firmado (opcional)", key="adm_ajena_aviso")
        if st.button("Revocar", key="adm_ajena_revocar"):
            if aviso is None and motivo.strip() == "":
                st.error("Escriba el motivo o suba el aviso de revocación.")
            else:
                _intentar(
                    lambda: empresas.revocar_ajena(
                        bd,
                        elegida.id,
                        motivo,
                        sesion.login,
                        _ahora(),
                        aviso.getvalue() if aviso is not None else None,
                    ),
                    "Clave revocada: los paquetes con ella ya no verifican.",
                )


# --- claves de API -----------------------------------------------------------------------------


def _pestana_api(bd: Session, sesion: SesionActiva) -> None:
    claves = bd.scalars(select(ClaveApi).order_by(ClaveApi.id)).all()
    st.dataframe(
        [
            {
                "Clave": claves_api.etiqueta(f),
                "Para qué": texto_seguro(f.nombre),
                "Estado": "revocada" if f.revocada else "vigente",
                "Último uso": f.ultimo_uso.isoformat(sep=" ") if f.ultimo_uso else "nunca",
            }
            for f in claves
        ],
        hide_index=True,
    )
    with st.form("adm_crear_clave_api", clear_on_submit=True):
        nombre = st.text_input(
            "Para qué es esta clave (por ejemplo, el plugin que la usa)", key="adm_api_nombre"
        )
        crear = st.form_submit_button("Crear la clave de API", key="adm_api_enviar")
    if crear:
        ui_sesion.exigir_local(Sensible.CLAVE_DE_API)
        try:
            secreto, _ = claves_api.crear(bd, nombre, sesion.login, _ahora())
        except ValueError as error:
            st.error(texto_seguro(str(error)))
        else:
            st.success("Clave creada. Cópiela ahora: no se vuelve a mostrar.")
            st.code(secreto)
    vigentes = [f for f in claves if not f.revocada]
    if not vigentes:
        return
    por_id = {f.id: f for f in vigentes}
    elegida = por_id[
        st.selectbox(
            "Clave a revocar",
            list(por_id),
            key="adm_api_revocar",
            format_func=lambda i: claves_api.etiqueta(por_id[i]),
        )
    ]
    if st.button("Revocar la clave", key="adm_api_boton_revocar"):
        ui_sesion.exigir_local(Sensible.CLAVE_DE_API)
        if _intentar(
            lambda: claves_api.revocar(bd, elegida.id, sesion.login, _ahora()), "Clave revocada."
        ):
            st.rerun()


# --- accesos -----------------------------------------------------------------------------------


def _pestana_accesos(bd: Session, sesion: SesionActiva) -> None:
    st.caption("Los 200 últimos eventos de acceso; este registro solo se agrega, no se edita.")
    st.dataframe(
        [
            {
                "Fecha": e.fecha_hora.isoformat(sep=" "),
                "Evento": e.tipo,
                "Usuario": texto_seguro(e.login_intentado),
                "IP": texto_seguro(e.ip_cliente),
                "Detalle": texto_seguro(e.detalle),
            }
            for e in eventos.ultimos(bd, 200)
        ],
        hide_index=True,
    )


def _pestana_instalacion(bd: Session, sesion: SesionActiva) -> None:
    instalacion.render_pestana()


# --- el cuerpo ---------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Pestana:
    titulo: str
    accion: Accion  # la de la matriz de roles que la habilita
    pintar: Callable[[Session, SesionActiva], None]


PESTANAS: tuple[Pestana, ...] = (
    Pestana("Cuentas", Accion.ADMINISTRAR_CUENTAS, _pestana_cuentas),
    Pestana("Empresa y clave de firma", Accion.ADMINISTRAR_EMPRESA, _pestana_empresa),
    Pestana("Empresas registradas", Accion.ADMINISTRAR_EMPRESA, _pestana_registradas),
    Pestana("Claves de API", Accion.ADMINISTRAR_RED_Y_API, _pestana_api),
    Pestana("Accesos", Accion.ADMINISTRAR_CUENTAS, _pestana_accesos),
    Pestana("Instalación", Accion.ADMINISTRAR_RED_Y_API, _pestana_instalacion),
)
TITULOS_DE_PESTANAS = tuple(p.titulo for p in PESTANAS)


def render() -> None:
    sesion = ui_sesion.exigir(Accion.ADMINISTRAR_CUENTAS)
    visibles = [p for p in PESTANAS if ui_sesion.puede(p.accion)]
    titulos = [p.titulo for p in visibles]
    elegida = st.segmented_control(
        "Sección", titulos, default=titulos[0], key=CLAVE_PESTANA, label_visibility="collapsed"
    )
    pestana = next((p for p in visibles if p.titulo == elegida), visibles[0])
    ui_sesion.exigir(pestana.accion)
    with ui_sesion.instalacion() as bd:
        pestana.pintar(bd, sesion)
