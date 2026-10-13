"""Libro de la empresa (spec 1.5 §1 y §5): subir el libro → resumen → hallazgos con la vista
calcada → alertas USD-Bs → descargar el libro devuelto.

Quien trabaja sube el Excel de su empresa (y, si lo tiene, el PDF que se entregó al cliente y una
versión anterior del libro). Silice lo lee por rótulos, recalcula cada APU con el motor del núcleo,
lo audita y devuelve el libro calcado con las hojas AUDITORÍA, TRAZABILIDAD y ALERTAS USD-Bs
(`fusion.proceso`). Todo en memoria (F-D9): el caso solo se lee, para las tasas del BCV y los
precios propios de esta instalación.

Fechas (F-D8): la del libro se propone desde la PORTADA y el usuario puede cambiarla; la de
devolución es hoy, a la vista y editable. El resultado se calcula una vez al pulsar «Auditar» y se
guarda en `st.session_state` con una clave que no es de widget; el libro devuelto se genera solo al
pulsar «Preparar el libro devuelto». La vista activa se elige con `st.segmented_control`, así que
una edición solo pinta la vista que se ve. Lo pesado se importa dentro de las acciones: la página
se importa sin efectos y sin cargar `fusion` ni el lector del PDF.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

import streamlit as st

from adapters.hoja_empresa.guardia import ArchivoRechazado, verificar_archivo
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from seguridad.permisos import Accion
from ui import libros
from ui import sesion as ui_sesion
from ui.caso import ruta_caso
from ui.subidas import nombre_seguro
from ui.texto_seguro import texto_seguro

CLAVE_RESULTADO = "libros_resultado"  # lo auditado: no es clave de ningún widget
CLAVE_FECHA_SUGERIDA = "libros_fecha_sugerida"  # (sha, fecha, de dónde salió)
CLAVE_DEVUELTO = "libros_devuelto"  # (firma, nombre, octetos) del libro devuelto
CLAVE_VISTAS = "libros_vistas"  # vistas calcadas ya armadas, por (sha, hoja, desde, ocultas)
CLAVE_ABIERTO = "libros_abierto"  # (sha, libro de openpyxl): se lee una vez por resultado
CLAVE_SECCION = "libros_seccion"
SECCIONES = ("Hallazgos", "Vista de la hoja", "Alertas USD-Bs")
MAX_VISTAS_GUARDADAS = 12
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MENSAJE_FALLO = (
    "No se pudo auditar el libro por un problema inesperado. Revise que sea el libro de "
    "presupuesto de la empresa y vuelva a intentarlo; si se repite, guarde el detalle de abajo y "
    "comuníquelo a quien administra Silice."
)
ACCIONES_F_D7 = (
    "**corregido**: Silice lo corrigió en el libro devuelto · **a confirmar**: se conservó lo "
    "escrito y la empresa debe confirmarlo · **informado**: solo se informa."
)


@dataclass(frozen=True, slots=True)
class Auditado:
    """Lo que se guarda tras «Auditar»: el resultado y con qué archivos y fechas salió."""

    firma: str
    login: str
    nombre: str
    resultado: object  # fusion.proceso.ResultadoFusion (importado de forma perezosa)


def _sha(datos: bytes | None) -> str:
    return hashlib.sha256(datos).hexdigest() if datos is not None else "-"


def _firma(xlsx: bytes, pdf: bytes | None, otro: bytes | None, f_libro, f_dev) -> str:
    return "|".join((_sha(xlsx), _sha(pdf), _sha(otro), str(f_libro), str(f_dev)))


def _nombre(subida, defecto: str) -> str:
    """El nombre que manda el navegador, limpio (A-1): va a TRAZABILIDAD y al libro devuelto."""
    try:
        return nombre_seguro(subida.name)
    except ValueError:
        return defecto


def _hoy() -> date:
    return ui_sesion.ahora().date()


def _dia(fecha: date | None) -> str:
    return fecha.strftime("%d/%m/%Y") if fecha is not None else "sin fecha"


def _fallo_inesperado(error: Exception) -> None:
    """Mensaje claro y el detalle plegado, sin traza (directriz 4)."""
    st.error(MENSAJE_FALLO)
    with st.expander("Detalle técnico"):
        st.code(f"{type(error).__name__}: {error}", language=None)


# --- entrada --------------------------------------------------------------------------------------


def _fecha_sugerida(datos: bytes, nombre: str) -> tuple[date, str] | None:
    """La fecha de la PORTADA (F-D8), leída una vez por archivo; `None` si el archivo se rechaza
    (el error ya se mostró)."""
    sha = _sha(datos)
    guardada = st.session_state.get(CLAVE_FECHA_SUGERIDA)
    if guardada is not None and guardada[0] == sha:
        return guardada[1], guardada[2]
    try:
        verificar_archivo(datos, nombre)
    except ArchivoRechazado as error:
        st.error(texto_seguro(str(error)))
        return None
    fecha, origen = _hoy(), "la PORTADA no trae una fecha legible; se propone hoy"
    try:
        from adapters.hoja_empresa.lector import leer_libro
        from fusion.proceso import fecha_del_libro

        de_portada = fecha_del_libro(leer_libro(datos, nombre))
        if de_portada is not None:
            fecha, origen = de_portada, "tomada de la PORTADA"
    except ArchivoRechazado as error:
        st.error(texto_seguro(str(error)))
        return None
    except Exception:  # noqa: BLE001 - si no se puede leer aquí, «Auditar» dirá por qué
        pass
    st.session_state[CLAVE_FECHA_SUGERIDA] = (sha, fecha, origen)
    return fecha, origen


def _entrada():
    """Los archivos y las fechas. Devuelve `(xlsx, pdf, otro, fecha_libro, fecha_devolucion)` o
    `None` si todavía no hay libro."""
    xlsx = st.file_uploader(
        "Libro de Excel de la empresa (.xlsx)",
        type=["xlsx"],
        key="libros_xlsx",
        help="El libro de presupuesto tal como lo trabaja la empresa. Sin macros (.xlsm no).",
    )
    a, b = st.columns(2)
    pdf = a.file_uploader(
        "PDF entregado al cliente (opcional)",
        type=["pdf"],
        key="libros_pdf",
        help="Silice coteja el subtotal, el IVA y el total impresos con los del libro.",
    )
    otro = b.file_uploader(
        "Versión anterior del libro (opcional)",
        type=["xlsx"],
        key="libros_otro",
        help="Para avisar de los precios que cambiaron entre una versión y otra.",
    )
    if xlsx is None:
        st.info("Suba el libro de Excel de la empresa para empezar.")
        return None
    sugerida = _fecha_sugerida(xlsx.getvalue(), _nombre(xlsx, "libro.xlsx"))
    if sugerida is None:
        return None
    fecha, origen = sugerida
    c, d = st.columns(2)
    fecha_libro = c.date_input(
        "Fecha del libro",
        value=fecha,
        key=f"libros_fecha_{_sha(xlsx.getvalue())[:12]}",
        format="DD/MM/YYYY",
        help=f"Fija la tasa del BCV de partida ({origen}). Cámbiela si el libro es de otra fecha.",
    )
    fecha_dev = d.date_input(
        "Fecha de devolución",
        value=_hoy(),
        key="libros_devolucion",
        format="DD/MM/YYYY",
        help="La tasa del BCV con la que se compara el precio en Bs. Por defecto, hoy.",
    )
    c.caption(f"Fecha del libro {origen}.")
    return xlsx, pdf, otro, fecha_libro, fecha_dev


def _auditar(sesion, xlsx, pdf, otro, fecha_libro, fecha_dev, firma: str) -> Auditado | None:
    """Procesa el libro con las tasas y precios de esta instalación. Sin caso legible, audita
    igual sin ellos (las alertas en Bs dirán «no contrastable»)."""
    from fusion.proceso import procesar_libro, servicios_desde_sesion

    datos = xlsx.getvalue()
    nombre = _nombre(xlsx, "libro.xlsx")
    argumentos = {
        "pdf": pdf.getvalue() if pdf is not None else None,
        "pdf_nombre": _nombre(pdf, "entregado.pdf") if pdf is not None else "",
        "fecha_libro": fecha_libro,
        "fecha_devolucion": fecha_dev,
        "otro": otro.getvalue() if otro is not None else None,
    }
    ruta = ruta_caso()
    try:
        preparar_base(ruta)  # RV-5: la única puerta a la base del caso
    except ErrorDeBase as error:
        st.warning(
            texto_seguro(f"No se pudo abrir el caso ({error}).")
            + " Se audita sin las tasas del BCV ni los precios de la empresa."
        )
        resultado = procesar_libro(datos, nombre, contexto=None, **argumentos)
        return Auditado(firma, sesion.login, nombre, resultado)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as caso:
            contexto = servicios_desde_sesion(caso)
            resultado = procesar_libro(datos, nombre, contexto=contexto, **argumentos)
    finally:
        motor.dispose()
    return Auditado(firma, sesion.login, nombre, resultado)


# --- resultado ------------------------------------------------------------------------------------


def _resumen(a: Auditado) -> None:
    r = a.resultado
    libro = r.libro
    moneda = (libro.portada.moneda or "").strip()
    st.subheader("Resumen")
    st.caption(
        f"Libro: {texto_seguro(a.nombre)} · SHA-256 {libro.sha256[:16]}… · "
        f"fecha del libro {_dia(r.fecha_libro)} · devolución {_dia(r.fecha_devolucion)}"
        + (f" · moneda {texto_seguro(moneda)}" if moneda else "")
    )
    filas = libros.filas_totales(libro.totales, r.totales_silice, r.pdf_totales)
    principal = filas[0]
    m = st.columns(3)
    m[0].metric("Sin IVA, libro entregado", principal["Libro entregado"])
    m[1].metric("Sin IVA, según Silice", principal["Según Silice"])
    m[2].metric("Diferencia (Silice − libro)", principal["Diferencia"] or "—")
    st.dataframe(filas, hide_index=True, width="stretch")

    informe = r.informe
    conteo = {s.name: n for s, n in informe.por_severidad().items()}
    c = st.columns(len(libros.ORDEN_SEVERIDAD))
    for columna, severidad in zip(c, libros.ORDEN_SEVERIDAD, strict=True):
        columna.metric(severidad.capitalize(), conteo.get(severidad, 0))
    graves = conteo.get("CRITICO", 0) + conteo.get("ERROR", 0)
    if informe.cumple:
        st.success("Cumple: ningún hallazgo de error ni crítico.")
    else:
        st.error(
            f"No cumple: {graves} hallazgo(s) de error o crítico(s). Véalos en «Hallazgos» y en "
            "la hoja AUDITORÍA del libro devuelto."
        )


def _hallazgos(a: Auditado) -> None:
    filas = a.resultado.hallazgos_tabla
    if not filas:
        st.success("No hay hallazgos.")
        return
    severidades, reglas, hojas = libros.opciones_de_filtro(filas)
    f = st.columns(3)
    sev = f[0].multiselect("Severidad", severidades, key="libros_f_sev", placeholder="Todas")
    reg = f[1].multiselect("Regla", reglas, key="libros_f_regla", placeholder="Todas")
    hoj = f[2].multiselect("Hoja", hojas, key="libros_f_hoja", placeholder="Todas")
    elegidas = libros.filtrar_hallazgos(filas, sev, reg, hoj)
    st.caption(f"{len(elegidas)} de {len(filas)} hallazgos. " + ACCIONES_F_D7)
    st.dataframe(libros.filas_hallazgos(elegidas), hide_index=True, width="stretch")


def _vista(a: Auditado) -> None:
    r = a.resultado
    origen = r.origen
    sha = r.libro.sha256
    marcas = libros.marcas_por_hoja(r.informe.hallazgos)
    hojas = r.libro.hojas or libros.hojas_del_libro(origen)
    if not hojas:
        st.info("El libro no tiene hojas que mostrar.")
        return
    primera = next(
        (libros.hoja_de(f.celda) for f in r.hallazgos_tabla if libros.hoja_de(f.celda) in hojas),
        hojas[0],
    )
    c = st.columns([3, 1, 1])
    hoja = c[0].selectbox(
        "Hoja del libro",
        hojas,
        index=hojas.index(primera),
        key="libros_hoja",
        format_func=lambda h: (
            f"{h} ({len(marcas.get(h, {}))} celdas citadas)" if marcas.get(h) else h
        ),
    )
    desde = int(
        c[1].number_input(
            "Desde la fila", min_value=1, value=1, step=libros.FILAS_VISTA, key="libros_desde"
        )
    )
    ocultas = c[2].toggle(
        "Ver lo oculto",
        value=True,
        key="libros_ocultas",
        help="Muestra las filas y columnas que el libro oculta (encabezado en ámbar).",
    )
    vistas: dict = st.session_state.setdefault(CLAVE_VISTAS, {})
    clave = (sha, hoja, desde, ocultas)
    vista = vistas.get(clave)
    if vista is None:
        try:
            abierto = st.session_state.get(CLAVE_ABIERTO)
            if abierto is None or abierto[0] != sha:
                with st.spinner("Abriendo el libro para dibujar sus hojas…"):
                    abierto = (sha, libros.abrir_libro(origen))
                st.session_state[CLAVE_ABIERTO] = abierto
            vista = libros.vista_calcada(
                abierto[1], hoja, marcas.get(hoja), desde=desde, ocultas=ocultas
            )
        except Exception as error:  # noqa: BLE001 - la vista es una ayuda: su fallo no tumba nada
            st.warning("No se pudo dibujar esta hoja; los hallazgos siguen en la tabla.")
            with st.expander("Detalle técnico"):
                st.code(f"{type(error).__name__}: {error}", language=None)
            return
        if len(vistas) >= MAX_VISTAS_GUARDADAS:
            vistas.pop(next(iter(vistas)))
        vistas[clave] = vista
    st.caption(
        f"Filas {vista.desde} a {vista.hasta} de {vista.filas}, "
        "columnas A a Z como máximo. Las celdas con borde rojo las cita un hallazgo (pase el "
        "cursor por encima para ver el código); la tabla de abajo lista los de esta hoja."
        + (" Encabezado en ámbar: fila o columna oculta en el libro." if ocultas else "")
    )
    st.html(vista.html)
    if vista.fuera:
        st.caption(
            "Citadas pero fuera de esta vista (cambie «Desde la fila», están después de la "
            "columna Z u ocultas): "
            + ", ".join(texto_seguro(f"{ref} ({', '.join(c)})") for ref, c in vista.fuera[:40])
            + (" …" if len(vista.fuera) > 40 else "")
        )
    propios = [f for f in r.hallazgos_tabla if libros.hoja_de(f.celda) == hoja]
    if propios:
        st.dataframe(libros.filas_hallazgos(propios), hide_index=True, width="stretch")


def _alertas(a: Auditado) -> None:
    alertas = a.resultado.alertas
    if not alertas:
        st.success("Ningún precio de INSUMOS genera alerta.")
        return
    if not libros.hay_tasas(alertas):
        st.info(
            "Esta instalación no tiene tasas del BCV para esas fechas: las columnas en Bs dicen "
            "«no contrastable» y no se inventa ningún número. Puede importarlas en «Índices del "
            "BCV» y volver a auditar."
        )
    st.dataframe(libros.filas_alertas(alertas), hide_index=True, width="stretch")


def _trazabilidad(a: Auditado) -> None:
    traza = a.resultado.trazabilidad
    with st.expander(f"Trazabilidad: de dónde sale cada dato ({len(traza)})"):
        st.dataframe(libros.filas_traza(traza), hide_index=True, width="stretch")


def _descarga(a: Auditado) -> None:
    st.subheader("Libro devuelto")
    st.caption(
        "El mismo libro, con forma uniforme por dentro, los valores de Silice y tres hojas nuevas: "
        "AUDITORÍA, TRAZABILIDAD y ALERTAS USD-Bs."
    )
    if st.button("Preparar el libro devuelto", key="libros_preparar"):
        from fusion.proceso import devolver

        try:
            st.session_state[CLAVE_DEVUELTO] = (
                a.firma,
                libros.nombre_devuelto(a.nombre),
                devolver(a.resultado),
            )
        except Exception as error:  # noqa: BLE001 - mensaje claro, sin traza
            st.error("No se pudo preparar el libro devuelto.")
            with st.expander("Detalle técnico"):
                st.code(f"{type(error).__name__}: {error}", language=None)
    listo = st.session_state.get(CLAVE_DEVUELTO)
    if listo and listo[0] == a.firma:
        st.download_button(
            f"Descargar «{listo[1]}»",
            listo[2],
            file_name=listo[1],
            mime=MIME_XLSX,
            key="libros_bajar",
            type="primary",
        )


def render() -> None:
    sesion = ui_sesion.exigir(Accion.LEER_PROYECTO)
    st.caption(
        "Suba el libro de presupuesto de su empresa: Silice lo recalcula con su motor, lo audita y "
        "le devuelve el mismo libro corregido, con la auditoría, la trazabilidad y las alertas de "
        "precio dentro. Nada se guarda en el caso."
    )
    entrada = _entrada()
    if entrada is None:
        return
    xlsx, pdf, otro, fecha_libro, fecha_dev = entrada
    firma = _firma(
        xlsx.getvalue(),
        pdf.getvalue() if pdf is not None else None,
        otro.getvalue() if otro is not None else None,
        fecha_libro,
        fecha_dev,
    )
    if st.button("Auditar", type="primary", key="libros_auditar"):
        try:
            with st.spinner("Leyendo, recalculando y auditando el libro…"):
                auditado = _auditar(sesion, xlsx, pdf, otro, fecha_libro, fecha_dev, firma)
        except ArchivoRechazado as error:
            st.error(texto_seguro(str(error)))
            return
        except Exception as error:  # noqa: BLE001 - nunca una traza en pantalla (directriz 4)
            _fallo_inesperado(error)
            return
        st.session_state[CLAVE_RESULTADO] = auditado
        for clave in (CLAVE_DEVUELTO, CLAVE_ABIERTO, CLAVE_VISTAS):
            st.session_state.pop(clave, None)
    auditado = st.session_state.get(CLAVE_RESULTADO)
    if auditado is None or auditado.login != sesion.login:
        st.caption("Pulse «Auditar» para ver el resultado.")
        return
    if auditado.firma != firma:
        st.info("Cambió un archivo o una fecha: pulse «Auditar» para actualizar el resultado.")
        return
    _resumen(auditado)
    st.session_state.setdefault(CLAVE_SECCION, SECCIONES[0])
    seccion = st.segmented_control(
        "Sección", SECCIONES, key=CLAVE_SECCION, label_visibility="collapsed"
    )
    seccion = seccion or SECCIONES[0]
    if seccion == SECCIONES[0]:
        _hallazgos(auditado)
    elif seccion == SECCIONES[1]:
        _vista(auditado)
    else:
        _alertas(auditado)
    _trazabilidad(auditado)
    _descarga(auditado)
