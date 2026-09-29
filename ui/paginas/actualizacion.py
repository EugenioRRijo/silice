"""Pagina de UC-02: cargar una lista de precios y ver el presupuesto revalorado (I1, F.1).

Movida integra desde el antiguo `ui/app.py` (Sesion F.1, Tarea 4): misma logica, el mismo criterio
`insumos_afectados` para decidir si se guarda la version nueva, las mismas cuatro excepciones
previsibles y los mismos dos decimales de `core.verification.informe.DECIMALES_PRESENTACION`. Solo
cambia la ubicacion (ahora es una pagina entre varias de `st.navigation`, registrada en
`ui/app.py`) y que `st.set_page_config` ya no se llama aqui: en una app multipagina se llama una
sola vez, antes de `st.navigation`, en el enrutador.

Solo presentacion. Toda la logica vive en `core`: esta capa abre la sesion, llama a
`crear_lista_desde_archivo` y a `actualizar_precios`, muestra el comparativo y el informe de
auditoria -que se genera siempre, sin pedirlo (principio 7 de CLAUDE.md §2)- y ofrece el libro de
Excel. No calcula ni redondea nada por su cuenta: los dos decimales de la tabla son los de
`core.verification.informe.DECIMALES_PRESENTACION`, la unica definicion de presentacion del
sistema.

La transaccion se confirma aqui porque el nucleo la deja abierta a proposito: es esta pantalla la
que representa al usuario que acepta o descarta la version nueva (UC-02, flujos 3a y 7a).

Flujo 2a (INV-090, fase C6): al subir el archivo, la pantalla lista sus insumos desconocidos con
`insumos_desconocidos` (vista previa, no escribe) en el `multiselect` «Dar de alta», sin ninguno
elegido por defecto; los elegidos pasan a `crear_lista_desde_archivo`, que los crea con precio solo
en la lista nueva. El aviso separa los dados de alta, los ignorados (2a) y los rechazados por unidad
(2b: las filas que la vista previa no ofrece porque su insumo existe con otra unidad).

Paso 5 de UC-07 (INV-099, fase C6): la pantalla pasa a `actualizar_precios` el detector
`ml.anomaly.precios_atipicos` (import perezoso; sin el extra `ml`, ninguno), y los precios
atipicos de la lista nueva llegan como hallazgos `ATIPICO` al informe de la version revalorada que
se muestra.
"""

from __future__ import annotations

import tempfile
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.budget import (
    Comparativo,
    DetectorAtipicos,
    actualizar_precios,
    descartar_version,
    exportar_excel,
)
from core.catalog import (
    Catalogo,
    PrecioLeido,
    abrir_sesion,
    crear_esquema,
    crear_lista_desde_archivo,
    crear_motor,
    insumos_desconocidos,
)
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from scripts.seed import NOMBRE_PROYECTO, sembrar
from ui.caso import ruta_caso

CODIGO_BASE_POR_DEFECTO = "001"
CODIGO_NUEVO_POR_DEFECTO = "002"
MONEDA_POR_DEFECTO = "USD"
TIPOS_ACEPTADOS = ["csv", "xlsx"]
CLAVE_RESULTADO = "resultado_uc02"
CLAVE_DESCARTADA = "actualizacion_version_descartada"
CERO = Decimal(0)

#: Columnas del comparativo que se presentan redondeadas; el resto va como texto tal cual.
COLUMNAS_NUMERICAS = (
    "cantidad",
    "pu_anterior",
    "pu_nuevo",
    "variacion_pct",
    "total_anterior",
    "total_nuevo",
    "incidencia_pct",
)


# `eq=False` por el mismo motivo que en `Comparativo`: lleva un `DataFrame` dentro.
@dataclass(frozen=True, slots=True, eq=False)
class Presentacion:
    """Lo que la pantalla necesita mostrar despues de confirmar (o descartar) la actualizacion."""

    tabla: DataFrame
    resumen: str
    informe: str
    #: Los insumos desconocidos que no se eligieron para el alta: ignorados (UC-02, flujo 2a).
    ignorados: tuple[str, ...]
    libro: bytes
    nombre_libro: str
    proyecto: str
    #: El codigo de la version que esta ejecucion confirmo; `None` si no se guardo (UC-02 3a). Solo
    #: esa version se ofrece para descartar (UC-02 7a; limite de `descartar_version`).
    version_guardada: str | None
    #: El caso donde se guardo: el descarte marca esa base aunque despues se abra otro caso.
    ruta: Path
    #: Las filas cuyo insumo esta en el catalogo con otra unidad: rechazadas (UC-02, flujo 2b).
    rechazados: tuple[str, ...] = ()
    #: Los insumos elegidos que quedaron en el catalogo (UC-02, flujo 2a). Vacio si no se guardo
    #: la version: sin cambios de precio la transaccion se deshace y las altas con ella.
    dados_de_alta: tuple[str, ...] = ()


def render() -> None:
    """Pantalla unica: parametros en la barra lateral, archivo y resultados en el cuerpo."""
    st.caption(
        "Carga una lista de precios nueva (CSV o XLSX con las columnas tipo, insumo, unidad y "
        "precio) y el sistema revalora el presupuesto guardado, registra que cambio y audita la "
        "version nueva."
    )

    parametros = _barra_lateral()
    archivo = st.file_uploader("Lista de precios", type=TIPOS_ACEPTADOS)
    elegidos = _ofrecer_alta(parametros["ruta"], archivo) if archivo is not None else ()

    if st.button("Revalorar presupuesto", type="primary", disabled=archivo is None):
        with st.spinner("Revalorando..."):
            _ejecutar(parametros, archivo, elegidos)

    _mostrar(st.session_state.get(CLAVE_RESULTADO))


# ---------------------------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------------------------


def _barra_lateral() -> dict[str, object]:
    """Los datos que necesita `actualizar_precios`, con la linea base como valor por defecto."""
    with st.sidebar:
        st.header("Base de datos")
        ruta = ruta_caso()
        if st.button("Sembrar la linea base"):
            _sembrar(ruta)

        st.header("Presupuesto")
        proyecto = st.text_input("Proyecto", value=NOMBRE_PROYECTO)
        codigo = st.text_input("Codigo del presupuesto base", value=CODIGO_BASE_POR_DEFECTO)
        codigo_nuevo = st.text_input("Codigo de la version nueva", value=CODIGO_NUEVO_POR_DEFECTO)

        st.header("Lista de precios")
        vigencia = st.date_input("Fecha de vigencia", value=date.today())
        moneda = st.text_input("Moneda", value=MONEDA_POR_DEFECTO)
        nombre = st.text_input("Nombre de la lista", value=f"Lista {vigencia:%d/%m/%Y}")

    return {
        "ruta": ruta,
        "proyecto": proyecto,
        "codigo": codigo,
        "codigo_nuevo": codigo_nuevo,
        "vigencia": vigencia,
        "moneda": moneda,
        "nombre": nombre,
    }


def _sembrar(ruta: Path) -> None:
    """Crea el esquema y carga la linea base en la base indicada, si aun no esta."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            partidas = len(Catalogo(sesion).partidas())
        st.sidebar.success(f"Base lista en {ruta} con {partidas} partidas.")
    finally:
        motor.dispose()


def _ofrecer_alta(ruta: Path, archivo) -> tuple[PrecioLeido, ...]:
    """UC-02 2a: los desconocidos del archivo en «Dar de alta», ninguno elegido por defecto.

    Devuelve las filas elegidas tal como las dio la vista previa: `crear_lista_desde_archivo`
    rechaza (`ValueError`) cualquier otra.
    """
    ofrecidos = _vista_previa(ruta, archivo)
    if not ofrecidos:
        return ()
    # UC-02 2a «los lista»: a la vista antes de revalorar, sin abrir el desplegable (U-3).
    st.info(
        f"El archivo trae {len(ofrecidos)} insumo(s) que no estan en el catalogo (UC-02, flujo "
        f'2a): {", ".join(_nombrar(leido) for leido in ofrecidos)}. Elija en "Dar de alta" los '
        "que quiera crear antes de revalorar; los demas se ignoran."
    )
    # La posicion hace unica cada opcion aunque el archivo repita una fila.
    opciones = {
        f"{numero}. {_nombrar(leido)}, precio {leido.precio}": leido
        for numero, leido in enumerate(ofrecidos, start=1)
    }
    elegidas = st.multiselect(
        "Dar de alta",
        list(opciones),
        default=[],
        help=(
            "Insumos del archivo que no estan en el catalogo (UC-02, flujo 2a). Los elegidos se "
            "crean con codigo nuevo y su precio entra solo en la lista nueva; los demas se "
            "ignoran y no intervienen en el recalculo."
        ),
    )
    return tuple(opciones[etiqueta] for etiqueta in elegidas)


def _vista_previa(ruta: Path, archivo) -> tuple[PrecioLeido, ...]:
    """`insumos_desconocidos` sobre el caso abierto, sin escribir en el.

    Un caso que aun no existe no tiene catalogo: no se ofrece nada (y no se crea el archivo). Un
    archivo o una base que no se pueden leer tampoco ofrecen nada: el mismo fallo se muestra con
    su mensaje al revalorar, que es donde la pantalla informa los errores de UC-02.
    """
    if not ruta.exists():
        return ()
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with _archivo_temporal(archivo) as ruta_archivo, abrir_sesion(motor) as sesion:
            return insumos_desconocidos(sesion, ruta_archivo)
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError):
        return ()
    finally:
        motor.dispose()


@contextmanager
def _archivo_temporal(archivo) -> Iterator[Path]:
    """El archivo subido, con su nombre, en una carpeta temporal que se borra al salir."""
    with tempfile.TemporaryDirectory() as carpeta:
        ruta_archivo = Path(carpeta) / archivo.name
        ruta_archivo.write_bytes(archivo.getvalue())
        yield ruta_archivo


# ---------------------------------------------------------------------------------------------
# Caso de uso
# ---------------------------------------------------------------------------------------------


def _ejecutar(
    parametros: dict[str, object], archivo, dar_de_alta: Collection[PrecioLeido] = ()
) -> None:
    """Corre UC-02 completo y deja en la sesion de Streamlit lo que hay que mostrar.

    `dar_de_alta` son las filas que el usuario eligio en «Dar de alta» (UC-02, flujo 2a).
    """
    # Una revaloracion nueva olvida el descarte de la anterior: el mismo caso, proyecto y codigo
    # pueden volver (un caso resembrado en la misma ruta), y la version nueva no esta descartada.
    st.session_state.pop(CLAVE_DESCARTADA, None)
    motor = crear_motor(f"sqlite:///{parametros['ruta'].as_posix()}")
    try:
        crear_esquema(motor)
        with _archivo_temporal(archivo) as ruta_archivo, abrir_sesion(motor) as sesion:
            st.session_state[CLAVE_RESULTADO] = _actualizar(
                sesion, parametros, ruta_archivo, ruta_archivo.parent, dar_de_alta
            )
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # Los cuatro fallos previsibles de UC-02, que en una pantalla deben ser un mensaje y no una
        # traza cruda: `CatalogoIncompleto` (LookupError) y los errores de lectura del archivo
        # (ValueError); el `IntegrityError` de un segundo clic con el mismo codigo de presupuesto
        # (SQLAlchemyError); y `decimal.InvalidOperation` (ArithmeticError) desde cualquier
        # importe que llegue mal formado (revision final, item 5). Desde C6, tambien el
        # `ValueError` de un alta que el nucleo no admite (dos filas elegidas del mismo insumo con
        # precios distintos): se valida antes de escribir, asi que no queda nada a medias.
        st.session_state[CLAVE_RESULTADO] = None
        st.error(str(error))
    finally:
        motor.dispose()


def _actualizar(
    sesion: Session,
    parametros: dict[str, object],
    archivo: Path,
    carpeta: Path,
    dar_de_alta: Collection[PrecioLeido] = (),
) -> Presentacion:
    """Crea la lista, revalora, confirma si algun insumo cambio de precio y arma la presentacion.

    `dar_de_alta` son las filas de la vista previa que el usuario eligio (UC-02, flujo 2a).
    """
    # La vista previa se toma antes de crear la lista: despues, los dados de alta ya no son
    # desconocidos. Lo que la carga no uso y la vista previa no ofrecia es el flujo 2b.
    ofrecidos = insumos_desconocidos(sesion, archivo)
    resumen = crear_lista_desde_archivo(
        sesion,
        archivo,
        nombre=str(parametros["nombre"]),
        moneda=str(parametros["moneda"]),
        fecha_vigencia=parametros["vigencia"],
        origen=archivo.name,
        dar_de_alta=dar_de_alta,
    )
    dados_de_alta = tuple(
        f"{insumo.descripcion} ({insumo.codigo})" for insumo in resumen.dados_de_alta
    )
    nuevo, comparativo = actualizar_precios(
        sesion,
        str(parametros["proyecto"]),
        str(parametros["codigo"]),
        resumen.lista,
        str(parametros["codigo_nuevo"]),
        detectar_atipicos=_detector_de_atipicos(),
    )
    libro = exportar_excel(
        nuevo.presupuesto, nuevo.informe, carpeta / f"presupuesto_{nuevo.presupuesto.codigo}.xlsx"
    )

    if comparativo.insumos_afectados == 0:
        # Ningun insumo cambio de precio entre la lista anterior y la nueva: no hay nada que
        # guardar (UC-02, flujo 3a). Descartar la transaccion tambien descarta la lista nueva, que
        # aqui es identica a la anterior en sus precios.
        aviso = "Ningun precio cambio: no se guardo una version nueva (UC-02, flujo 3a)."
        if dados_de_alta:
            aviso += (
                " Los insumos elegidos para el alta tampoco se guardaron: "
                + ", ".join(dados_de_alta)
                + "."
            )
        st.warning(aviso)
        version_guardada = None
        dados_de_alta = ()
    else:
        # Algun insumo cambio de precio (se persiste siempre, ya lo hizo actualizar_precios), pero
        # eso no implica que el presupuesto varie: si el insumo no participa de ninguna de sus
        # partidas, `comparativo.variacion` da cero. Antes esta rama decidia con `variacion`, que
        # confundia ambos casos y descartaba la lista y su historial de CambioPrecio cuando el
        # unico cambio no tocaba este presupuesto (hallazgo de la ronda de correccion 1).
        if comparativo.variacion == CERO:
            st.info(
                "Cambiaron precios de insumos que no afectan a este presupuesto: se guardo la "
                "version nueva y su historial de cambios, pero el total no vario."
            )
        sesion.commit()
        # Solo la version que esta ejecucion acaba de confirmar se ofrece para descartar (UC-02
        # 7a): es el llamador que exige el docstring de `descartar_version`.
        version_guardada = str(parametros["codigo_nuevo"])

    return Presentacion(
        tabla=_para_presentar(comparativo.tabla),
        resumen=_resumen(comparativo, nuevo.presupuesto.moneda),
        informe=nuevo.informe.a_markdown(),
        ignorados=tuple(_nombrar(d) for d in resumen.desconocidos if d in ofrecidos),
        libro=libro.read_bytes(),
        nombre_libro=libro.name,
        proyecto=str(parametros["proyecto"]),
        version_guardada=version_guardada,
        ruta=Path(parametros["ruta"]),
        rechazados=tuple(_nombrar(d) for d in resumen.desconocidos if d not in ofrecidos),
        dados_de_alta=dados_de_alta,
    )


def _detector_de_atipicos() -> DetectorAtipicos | None:
    """`ml.anomaly.precios_atipicos`, o `None` sin el extra `ml` (UC-07, paso 5).

    Import perezoso, como `ui/composicion.py`: `core` no importa `ml`, y la pantalla funciona sin
    el extra; sin el, el informe es la auditoria de siempre, sin hallazgos `ATIPICO`.
    """
    try:
        from ml.anomaly import precios_atipicos
    except ImportError:
        return None
    return precios_atipicos


def _nombrar(leido: PrecioLeido) -> str:
    """Una fila del archivo como la lee el usuario: descripcion, tipo y unidad."""
    return f"{leido.descripcion} ({leido.tipo.value}, {leido.unidad or 'sin unidad'})"


# ---------------------------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------------------------


def _para_presentar(tabla: DataFrame) -> DataFrame:
    """El comparativo con sus `Decimal` a dos decimales, ya como texto: la tabla es de lectura."""
    presentada = tabla.copy()
    for columna in COLUMNAS_NUMERICAS:
        presentada[columna] = [
            formatear_decimal(valor, DECIMALES_PRESENTACION) for valor in tabla[columna]
        ]
    return presentada


def _resumen(comparativo: Comparativo, moneda: str) -> str:
    anterior = formatear_decimal(comparativo.total_anterior, DECIMALES_PRESENTACION)
    nuevo = formatear_decimal(comparativo.total_nuevo, DECIMALES_PRESENTACION)
    variacion = formatear_decimal(comparativo.variacion, DECIMALES_PRESENTACION)
    porcentaje = formatear_decimal(comparativo.variacion_pct, DECIMALES_PRESENTACION)
    return f"{anterior} -> {nuevo} {moneda}  ({variacion} {moneda}, {porcentaje} %)"


def _marca(presentacion: Presentacion) -> tuple[str, str, str | None]:
    """La identidad de la version guardada: su caso, su proyecto y su codigo."""
    return (presentacion.ruta.as_posix(), presentacion.proyecto, presentacion.version_guardada)


def _descartar(presentacion: Presentacion) -> None:
    """UC-02 7a: marca la version nueva como descartada; su historial de cambios se conserva.

    Marca la base donde se guardo (`presentacion.ruta`), no la del caso abierto ahora.
    """
    motor = crear_motor(f"sqlite:///{presentacion.ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            descartar_version(
                sesion, presentacion.proyecto, presentacion.version_guardada, date.today()
            )
            sesion.commit()
    except (LookupError, ValueError, SQLAlchemyError) as error:
        st.error(str(error))
        return
    finally:
        motor.dispose()
    st.session_state[CLAVE_DESCARTADA] = _marca(presentacion)
    st.rerun()  # el estado final: el aviso de descartada, sin el boton


def _mostrar(presentacion: Presentacion | None) -> None:
    if presentacion is None:
        return

    st.subheader("Comparativo por partida")
    st.metric("Total del presupuesto", presentacion.resumen)
    st.dataframe(presentacion.tabla, hide_index=True)

    if presentacion.dados_de_alta:
        st.success(
            "Se dieron de alta en el catalogo, con precio solo en la lista nueva (UC-02, flujo "
            "2a): " + ", ".join(presentacion.dados_de_alta)
        )
    if presentacion.ignorados:
        st.warning(
            "Se ignoraron los insumos del archivo que no estan en el catalogo y no se eligieron "
            "para el alta (UC-02, flujo 2a; no intervienen en el recalculo): "
            + ", ".join(presentacion.ignorados)
        )
    if presentacion.rechazados:
        st.warning(
            "Se rechazaron las filas cuyo insumo esta en el catalogo con otra unidad (UC-02, "
            "flujo 2b; no intervienen en el recalculo): " + ", ".join(presentacion.rechazados)
        )

    st.download_button(
        "Exportar a Excel",
        data=presentacion.libro,
        file_name=presentacion.nombre_libro,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.subheader("Informe de auditoria de la version nueva")
    st.markdown(presentacion.informe)

    if presentacion.version_guardada is not None:
        if st.session_state.get(CLAVE_DESCARTADA) == _marca(presentacion):
            st.info(
                f"Version {presentacion.version_guardada} descartada: sigue guardada como "
                "documento y su historial de cambios se conserva (UC-02, flujo 7a)."
            )
        elif st.button("Descartar version"):
            _descartar(presentacion)
