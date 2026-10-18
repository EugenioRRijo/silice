"""Libro de la empresa (spec 1.5 §1 y §5, UC-25): subir el libro → resumen → hallazgos con la vista
calcada → alertas USD-Bs → descargar el libro devuelto.

Quien trabaja sube el Excel de su empresa (y, si lo tiene, el PDF que se entregó al cliente y una
versión anterior del libro). Silice lo lee por rótulos, recalcula cada APU con el motor del núcleo,
lo audita y devuelve el libro calcado con las hojas AUDITORÍA, TRAZABILIDAD y ALERTAS USD-Bs
(`fusion.proceso`). Todo en memoria (F-D9): el caso solo se lee, para las tasas del BCV y los
precios propios de esta instalación.

Sin Excel, la página acepta **solo un PDF simple** (el presupuesto impreso, formato 001/002): lo
coteja consigo mismo (L10, `fusion.proceso.auditar_pdf_simple`) y muestra el resumen y los
hallazgos; sin libro no hay recálculo ni libro devuelto.

Fechas (F-D8): la del libro, si se deja vacía, es la de la PORTADA, que se lee una sola vez al
auditar (no se abre el libro dos veces para proponerla); el resumen dice cuál se usó y de dónde
salió. La de devolución es hoy, a la vista y editable. El resultado se calcula una vez al pulsar
«Auditar» y se guarda en `st.session_state` con una clave que no es de widget; el libro devuelto se
genera solo al pulsar «Preparar el libro devuelto». El libro abierto para la vista calcada vive en
`st.cache_resource` con su SHA-256 como clave, no en la sesión. La vista activa se elige con
`st.segmented_control`, así que una edición solo pinta la vista que se ve. Lo pesado se importa
dentro de las acciones: la página se importa sin efectos y sin cargar `fusion` ni el lector del PDF.

Errores (directriz 4): un archivo rechazado o un libro que no se puede interpretar dicen por qué; un
fallo inesperado da un mensaje fijo y, plegado, solo el nombre de la clase de error. El detalle va
al registro del servidor (`logging`), nunca a la pantalla.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import streamlit as st

from adapters.hoja_empresa.guardia import ArchivoRechazado, verificar_archivo
from adapters.hoja_empresa.modelo import LibroNoInterpretable
from core.catalog import abrir_sesion, crear_motor
from core.verification.texto import formatear_decimal
from operacion.base_datos import ErrorDeBase, preparar_base
from seguridad.permisos import Accion
from ui import libros
from ui import sesion as ui_sesion
from ui.caso import ruta_caso
from ui.subidas import nombre_seguro
from ui.texto_seguro import texto_seguro

LOG = logging.getLogger(__name__)

CLAVE_RESULTADO = "libros_resultado"  # lo auditado: no es clave de ningún widget
CLAVE_RESULTADO_PDF = "libros_resultado_pdf"  # lo revisado de un PDF simple (L10)
CLAVE_VERIFICADO = "libros_verificado"  # SHA-256 del último libro que pasó la guardia
CLAVE_DEVUELTO = "libros_devuelto"  # (firma, nombre, octetos) del libro devuelto
CLAVE_PRECARGADO = "libros_precargado"  # (nombre, octetos) del libro que se subió en el Inicio
CLAVE_VISTAS = "libros_vistas"  # vistas calcadas ya armadas, por (sha, hoja, desde, ocultas)
CLAVE_SECCION = "libros_seccion"
SECCIONES = ("Hallazgos", "Vista de la hoja", "Alertas USD-Bs")
MAX_VISTAS_GUARDADAS = 12
UMBRAL_POR_DEFECTO_PCT = 5.0
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ERRORES_DEL_USUARIO = (ArchivoRechazado, LibroNoInterpretable)  # su mensaje es para el usuario
MENSAJE_FALLO = (
    "No se pudo auditar el libro por un problema inesperado. Revise que sea el libro de "
    "presupuesto de la empresa y vuelva a intentarlo; si se repite, comunique a quien administra "
    "Silice el tipo de error de abajo (el detalle quedó en el registro del servidor)."
)
MENSAJE_FALLO_PDF = (
    "No se pudo revisar el PDF por un problema inesperado. Revise que sea el presupuesto impreso "
    "(formato 001/002) y vuelva a intentarlo; si se repite, comunique a quien administra Silice el "
    "tipo de error de abajo (el detalle quedó en el registro del servidor)."
)
ACCIONES_F_D7 = (
    "**corregido**: Silice lo corrigió en el libro devuelto · **a confirmar**: se conservó lo "
    "escrito y la empresa debe confirmarlo · **informado**: solo se informa."
)
LEYENDA_PDF = "Un PDF no se devuelve corregido: todos sus hallazgos son **informado**."
LIMITES_DEL_CALCADO = (
    "No se copian hipervínculos, protección de hoja ni formatos condicionales de barras, escalas "
    "o iconos; todo cambio queda en AUDITORÍA y TRAZABILIDAD."
)


@dataclass(frozen=True, slots=True)
class Precargado:
    """El libro que se subió en el Inicio, con la forma mínima de un archivo subido."""

    name: str
    datos: bytes

    def getvalue(self) -> bytes:
        return self.datos


@dataclass(frozen=True, slots=True)
class Auditado:
    """Lo que se guarda tras «Auditar»: el resultado y con qué archivos y fechas salió."""

    firma: str
    login: str
    nombre: str
    resultado: object  # fusion.proceso.ResultadoFusion (importado de forma perezosa)


@dataclass(frozen=True, slots=True)
class Entrada:
    """Lo que el usuario subió y eligió. `xlsx` es `None` en el modo «solo un PDF simple»."""

    xlsx: object | None
    pdf: object | None
    otro: object | None
    fecha_libro: date | None = None
    fecha_devolucion: date | None = None
    umbral: Decimal = Decimal("0.05")


def _sha(datos: bytes | None) -> str:
    return hashlib.sha256(datos).hexdigest() if datos is not None else "-"


def _firma(e: Entrada) -> str:
    def octetos(subida) -> bytes | None:
        return subida.getvalue() if subida is not None else None

    return "|".join(
        (
            _sha(octetos(e.xlsx)),
            _sha(octetos(e.pdf)),
            _sha(octetos(e.otro)),
            str(e.fecha_libro),
            str(e.fecha_devolucion),
            str(e.umbral),
        )
    )


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


def _detalle_tecnico(error: BaseException, que: str) -> None:
    """Solo el nombre de la clase de error, plegado; el detalle y la traza, al registro."""
    LOG.error("%s: %s", que, type(error).__name__, exc_info=error)
    with st.expander("Detalle técnico"):
        st.code(type(error).__name__, language=None)


def _fallo_inesperado(error: Exception, mensaje: str = MENSAJE_FALLO) -> None:
    """Mensaje claro y la clase del error plegada, sin traza ni texto del error (directriz 4)."""
    st.error(mensaje)
    _detalle_tecnico(error, "Libro de la empresa: fallo inesperado")


@st.cache_resource(max_entries=4, ttl=1800, show_spinner=False)
def _libro_abierto(sha: str, _origen: bytes):
    """El libro abierto para la vista calcada, uno por SHA-256 (el `_` deja los octetos fuera de la
    clave). Se comparte entre reruns sin guardarlo en la sesión; solo lo alcanza quien sube los
    mismos octetos."""
    return libros.abrir_libro(_origen)


# --- entrada --------------------------------------------------------------------------------------


def _verificar(datos: bytes, nombre: str) -> bool:
    """La guardia (F-D10), barata y una vez por archivo: un archivo rechazado se dice al subirlo.
    No lee el libro: eso pasa una sola vez, al auditar."""
    sha = _sha(datos)
    if st.session_state.get(CLAVE_VERIFICADO) == sha:
        return True
    try:
        verificar_archivo(datos, nombre)
    except ArchivoRechazado as error:
        st.error(texto_seguro(str(error)))
        return False
    st.session_state[CLAVE_VERIFICADO] = sha
    return True


def _entrada() -> Entrada | None:
    """Los archivos, las fechas y el umbral. `None` si todavía no hay nada que revisar."""
    xlsx = st.file_uploader(
        "Libro de Excel de la empresa (.xlsx)",
        type=["xlsx"],
        key="libros_xlsx",
        help="El libro de presupuesto tal como lo trabaja la empresa. Sin macros (.xlsm no).",
    )
    a, b = st.columns(2)
    pdf = a.file_uploader(
        "PDF entregado al cliente (opcional si sube el Excel)",
        type=["pdf"],
        key="libros_pdf",
        help=(
            "Con el Excel: si es el impreso desde el libro, Silice coteja su subtotal, IVA y "
            "total con los del libro; si es un PDF simple, lo revisa consigo mismo. Sin el Excel, "
            "revisa solo el PDF del presupuesto (formato 001/002)."
        ),
    )
    otro = b.file_uploader(
        "Versión anterior del libro (opcional)",
        type=["xlsx"],
        key="libros_otro",
        help="Para avisar de los precios que cambiaron entre una versión y otra.",
    )
    if xlsx is None and CLAVE_PRECARGADO in st.session_state:
        nombre, datos = st.session_state[CLAVE_PRECARGADO]
        xlsx = Precargado(nombre, datos)
        st.caption(
            f"Libro traído desde el Inicio: {texto_seguro(nombre)}. Suba otro aquí para cambiarlo."
        )
    if xlsx is None:
        if pdf is not None:
            if otro is not None:
                st.caption("Sin el Excel, la versión anterior no se usa: se revisa solo el PDF.")
            return Entrada(None, pdf, None)
        st.info(
            "Suba el libro de Excel de la empresa para empezar. Si solo tiene el presupuesto en "
            "PDF (formato 001/002), súbalo solo y Silice lo revisa sin el Excel."
        )
        return None
    if not _verificar(xlsx.getvalue(), _nombre(xlsx, "libro.xlsx")):
        return None
    c, d, e = st.columns(3)
    fecha_libro = c.date_input(
        "Fecha del libro",
        value=None,
        key=f"libros_fecha_{_sha(xlsx.getvalue())[:12]}",
        format="DD/MM/YYYY",
        help=(
            "Fija la tasa del BCV de partida. Vacía, se toma la de la PORTADA al auditar; escriba "
            "otra si el libro es de otra fecha."
        ),
    )
    fecha_dev = d.date_input(
        "Fecha de devolución",
        value=_hoy(),
        key="libros_devolucion",
        format="DD/MM/YYYY",
        help="La tasa del BCV con la que se compara el precio en Bs. Por defecto, hoy.",
    )
    porcentaje = e.number_input(
        "Umbral de alerta (%)",
        min_value=0.1,
        max_value=99.9,
        value=UMBRAL_POR_DEFECTO_PCT,
        step=0.5,
        format="%.1f",
        key="libros_umbral",
        help="Un precio que cambia más que esto (frente al de la empresa o al de la otra versión) "
        "genera una alerta.",
    )
    c.caption("Vacía: la de la PORTADA." if fecha_libro is None else "Escrita por usted.")
    umbral = Decimal(str(porcentaje)) / 100
    return Entrada(xlsx, pdf, otro, fecha_libro, fecha_dev, umbral)


def _auditar(sesion, e: Entrada, firma: str) -> Auditado:
    """Procesa el libro con las tasas y precios de esta instalación. Sin caso legible, audita
    igual sin ellos (las alertas en Bs dirán «no contrastable»)."""
    from fusion.alertas import ContextoPrecios
    from fusion.proceso import procesar_libro, servicios_desde_sesion

    datos = e.xlsx.getvalue()
    nombre = _nombre(e.xlsx, "libro.xlsx")
    argumentos = {
        "pdf": e.pdf.getvalue() if e.pdf is not None else None,
        "pdf_nombre": _nombre(e.pdf, "entregado.pdf") if e.pdf is not None else "",
        "fecha_libro": e.fecha_libro,
        "fecha_devolucion": e.fecha_devolucion,
        "otro": e.otro.getvalue() if e.otro is not None else None,
    }
    ruta = ruta_caso()
    try:
        preparar_base(ruta)  # RV-5: la única puerta a la base del caso
    except ErrorDeBase as error:
        st.warning(
            texto_seguro(f"No se pudo abrir el caso ({error}).")
            + " Se audita sin las tasas del BCV ni los precios de la empresa."
        )
        contexto = ContextoPrecios(umbral=e.umbral)
        resultado = procesar_libro(datos, nombre, contexto=contexto, **argumentos)
        return Auditado(firma, sesion.login, nombre, resultado)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as caso:
            contexto = servicios_desde_sesion(caso, umbral=e.umbral)
            resultado = procesar_libro(datos, nombre, contexto=contexto, **argumentos)
    finally:
        motor.dispose()
    return Auditado(firma, sesion.login, nombre, resultado)


# --- resultado ------------------------------------------------------------------------------------


def _conteo(severidades) -> dict[str, int]:
    conteo: dict[str, int] = {}
    for s in severidades:
        conteo[s] = conteo.get(s, 0) + 1
    return conteo


def _veredicto(conteo: dict[str, int], donde: str) -> None:
    c = st.columns(len(libros.ORDEN_SEVERIDAD))
    for columna, severidad in zip(c, libros.ORDEN_SEVERIDAD, strict=True):
        columna.metric(severidad.capitalize(), conteo.get(severidad, 0))
    graves = conteo.get("CRITICO", 0) + conteo.get("ERROR", 0)
    if not graves:
        st.success("Cumple: ningún hallazgo de error ni crítico.")
    else:
        st.error(f"No cumple: {graves} hallazgo(s) de error o crítico(s). Véalos en {donde}.")


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
    if r.fecha_libro is None:
        st.warning(
            "La PORTADA no trae una fecha legible y no se escribió otra: sin fecha del libro, las "
            "alertas en Bs no se contrastan. Escriba la «Fecha del libro» y vuelva a auditar."
        )
    filas = libros.filas_totales(libro.totales, r.totales_silice, r.pdf_totales)
    principal = filas[0]
    m = st.columns(3)
    m[0].metric("Sin IVA, libro entregado", principal["Libro entregado"])
    m[1].metric("Sin IVA, según Silice", principal["Según Silice"])
    m[2].metric("Diferencia (Silice − libro)", principal["Diferencia"] or "—")
    st.dataframe(filas, hide_index=True, width="stretch")
    conteo = {s.name: n for s, n in r.informe.por_severidad().items()}
    _veredicto(conteo, "«Hallazgos» y en la hoja AUDITORÍA del libro devuelto")


def _tabla_hallazgos(filas, prefijo: str, leyenda: str = ACCIONES_F_D7) -> None:
    if not filas:
        st.success("No hay hallazgos.")
        return
    severidades, reglas, hojas = libros.opciones_de_filtro(filas)
    f = st.columns(3)
    sev = f[0].multiselect("Severidad", severidades, key=f"{prefijo}_sev", placeholder="Todas")
    reg = f[1].multiselect("Regla", reglas, key=f"{prefijo}_regla", placeholder="Todas")
    hoj = f[2].multiselect("Hoja", hojas, key=f"{prefijo}_hoja", placeholder="Todas")
    elegidas = libros.filtrar_hallazgos(filas, sev, reg, hoj)
    st.caption(f"{len(elegidas)} de {len(filas)} hallazgos. " + leyenda)
    st.dataframe(libros.filas_hallazgos(elegidas), hide_index=True, width="stretch")


def _hallazgos(a: Auditado) -> None:
    _tabla_hallazgos(a.resultado.hallazgos_tabla, "libros_f")


def dibujar_hoja(
    prefijo: str,
    sha: str,
    origen: bytes,
    hojas: Sequence[str],
    primera: str,
    marcas: Mapping[str, Mapping[str, Sequence[str]]] | None = None,
    *,
    rotulo: str = "",
    citas: bool = False,
) -> str | None:
    """El selector de hoja y la hoja dibujada, con las celdas citadas en `marcas` (si las hay).

    Devuelve la hoja elegida, o `None` si no se pudo dibujar. Las claves de los widgets llevan el
    `prefijo`, así que el libro recibido y el devuelto tienen cada uno el suyo. `citas` dice que la
    vista acompaña a la tabla de hallazgos (el libro recibido); el devuelto no lleva marcas."""
    marcas = marcas or {}
    c = st.columns([3, 1, 1])
    hoja = c[0].selectbox(
        "Hoja del libro",
        hojas,
        index=hojas.index(primera),
        key=f"{prefijo}_hoja",
        format_func=lambda h: (
            f"{h} ({len(marcas.get(h, {}))} celdas citadas)" if marcas.get(h) else h
        ),
    )
    desde = int(
        c[1].number_input(
            "Desde la fila", min_value=1, value=1, step=libros.FILAS_VISTA, key=f"{prefijo}_desde"
        )
    )
    ocultas = c[2].toggle(
        "Ver lo oculto",
        value=True,
        key=f"{prefijo}_ocultas",
        help="Muestra las filas y columnas que el libro oculta (encabezado en ámbar).",
    )
    vistas: dict = st.session_state.setdefault(CLAVE_VISTAS, {})
    clave = (sha, hoja, desde, ocultas)
    vista = vistas.get(clave)
    if vista is None:
        try:
            with st.spinner("Abriendo el libro para dibujar sus hojas…"):
                abierto = _libro_abierto(sha, origen)
            vista = libros.vista_calcada(
                abierto, hoja, marcas.get(hoja), desde=desde, ocultas=ocultas
            )
        except Exception as error:  # noqa: BLE001 - la vista es una ayuda: su fallo no tumba nada
            st.warning(
                "No se pudo dibujar esta hoja; "
                + ("los hallazgos siguen en la tabla." if citas else "el libro se descarga igual.")
            )
            _detalle_tecnico(error, "Libro de la empresa: vista calcada")
            return None
        if len(vistas) >= MAX_VISTAS_GUARDADAS:
            vistas.pop(next(iter(vistas)))
        vistas[clave] = vista
    if vista.aviso:
        st.warning(vista.aviso)
    st.caption(
        f"{rotulo.format(hoja=hoja)}Filas {vista.desde} a {vista.hasta} de {vista.filas}, "
        "columnas A a Z como máximo."
        + (
            " Las celdas con borde rojo las cita un hallazgo (pase el cursor por encima para ver "
            "el código); la tabla de abajo lista los de esta hoja."
            if citas
            else ""
        )
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
    return hoja


def _vista(a: Auditado) -> None:
    r = a.resultado
    origen = r.origen
    marcas = libros.marcas_por_hoja(r.informe.hallazgos)
    hojas = r.libro.hojas or libros.hojas_del_libro(origen)
    if not hojas:
        st.info("El libro no tiene hojas que mostrar.")
        return
    primera = next(
        (libros.hoja_de(f.celda) for f in r.hallazgos_tabla if libros.hoja_de(f.celda) in hojas),
        hojas[0],
    )
    hoja = dibujar_hoja("libros", r.libro.sha256, origen, hojas, primera, marcas, citas=True)
    if hoja is None:
        return
    propios = [f for f in r.hallazgos_tabla if libros.hoja_de(f.celda) == hoja]
    if propios:
        st.dataframe(libros.filas_hallazgos(propios), hide_index=True, width="stretch")


def _vista_devuelto(octetos: bytes) -> None:
    """El libro devuelto dibujado como el original, con sus hojas y las tres nuevas."""
    hojas = libros.hojas_del_libro(octetos)
    if not hojas:
        return
    st.subheader("Vista del libro devuelto")
    dibujar_hoja(
        "libros_dev",
        _sha(octetos),
        octetos,
        hojas,
        hojas[0],
        rotulo="Libro devuelto, hoja {hoja}: ",
    )


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
    st.caption(LIMITES_DEL_CALCADO)
    if st.button("Preparar el libro devuelto", key="libros_preparar"):
        from fusion.proceso import devolver

        try:
            st.session_state[CLAVE_DEVUELTO] = (
                a.firma,
                libros.nombre_devuelto(a.nombre),
                devolver(a.resultado),
            )
        except ERRORES_DEL_USUARIO as error:
            st.error(texto_seguro(str(error)))
        except Exception as error:  # noqa: BLE001 - mensaje claro, sin traza
            st.error("No se pudo preparar el libro devuelto.")
            _detalle_tecnico(error, "Libro de la empresa: libro devuelto")
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
        _vista_devuelto(listo[2])


# --- solo un PDF simple (L10) ---------------------------------------------------------------------


def _resumen_pdf(a: Auditado) -> None:
    r = a.resultado
    pdf = r.pdf
    numero = str(getattr(pdf, "numero", "") or "").strip()
    fecha = str(getattr(pdf, "fecha", "") or "").strip()
    st.subheader("Resumen del PDF")
    st.caption(
        f"PDF: {texto_seguro(a.nombre)} · SHA-256 {r.sha256[:16]}…"
        + (f" · N.º {texto_seguro(numero)}" if numero else "")
        + (f" · fecha {texto_seguro(fecha)}" if fecha else "")
    )
    m = st.columns(3)
    m[0].metric("Renglones de cómputos", len(getattr(pdf, "computos", ()) or ()))
    m[1].metric("Renglones del presupuesto", len(getattr(pdf, "presupuesto", ()) or ()))
    total = getattr(pdf, "total_impreso", None)
    m[2].metric("Total impreso", "no disponible" if total is None else formatear_decimal(total, 2))
    _veredicto(_conteo(f.severidad for f in r.hallazgos_tabla), "la tabla de abajo")
    st.caption(
        "Sin el libro de Excel no hay recálculo ni libro devuelto: Silice coteja el PDF consigo "
        "mismo (cómputos contra presupuesto, cantidades por precio y la suma impresa). Para la "
        "auditoría completa suba también el Excel."
    )


def _solo_pdf(sesion, pdf) -> None:
    datos = pdf.getvalue()
    nombre = _nombre(pdf, "presupuesto.pdf")
    firma = "pdf|" + _sha(datos)
    if st.button("Revisar el PDF", type="primary", key="libros_auditar_pdf"):
        from fusion.proceso import auditar_pdf_simple

        try:
            with st.spinner("Leyendo y revisando el PDF…"):
                resultado = auditar_pdf_simple(datos, nombre)
        except ERRORES_DEL_USUARIO as error:
            st.error(texto_seguro(str(error)))
            return
        except Exception as error:  # noqa: BLE001 - nunca una traza en pantalla (directriz 4)
            _fallo_inesperado(error, MENSAJE_FALLO_PDF)
            return
        st.session_state[CLAVE_RESULTADO_PDF] = Auditado(firma, sesion.login, nombre, resultado)
    revisado = st.session_state.get(CLAVE_RESULTADO_PDF)
    if revisado is None or revisado.login != sesion.login or revisado.firma != firma:
        st.caption("Pulse «Revisar el PDF» para ver el resultado.")
        return
    _resumen_pdf(revisado)
    _tabla_hallazgos(revisado.resultado.hallazgos_tabla, "libros_fp", LEYENDA_PDF)


# --- página ---------------------------------------------------------------------------------------


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
    if entrada.xlsx is None:
        _solo_pdf(sesion, entrada.pdf)
        return
    firma = _firma(entrada)
    if st.button("Auditar", type="primary", key="libros_auditar"):
        try:
            with st.spinner("Leyendo, recalculando y auditando el libro…"):
                auditado = _auditar(sesion, entrada, firma)
        except ERRORES_DEL_USUARIO as error:
            st.error(texto_seguro(str(error)))
            return
        except Exception as error:  # noqa: BLE001 - nunca una traza en pantalla (directriz 4)
            _fallo_inesperado(error)
            return
        st.session_state[CLAVE_RESULTADO] = auditado
        for clave in (CLAVE_DEVUELTO, CLAVE_VISTAS):
            st.session_state.pop(clave, None)
    auditado = st.session_state.get(CLAVE_RESULTADO)
    if auditado is None or auditado.login != sesion.login:
        st.caption("Pulse «Auditar» para ver el resultado.")
        return
    if auditado.firma != firma:
        st.info(
            "Cambió un archivo, una fecha o el umbral: pulse «Auditar» para actualizar el "
            "resultado."
        )
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
