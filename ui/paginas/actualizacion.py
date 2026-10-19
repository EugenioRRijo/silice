"""Pagina de UC-02: cargar una lista de precios y ver el presupuesto revalorado (I1, F.1).

Movida integra desde el antiguo `ui/app.py` (Sesion F.1, Tarea 4): misma logica, el mismo criterio
`insumos_afectados` para decidir si se guarda la version nueva, las mismas cuatro excepciones
previsibles y los mismos dos decimales de `core.verification.informe.DECIMALES_PRESENTACION`. Solo
cambia la ubicacion (ahora es una pagina entre varias de `st.navigation`, registrada en
`ui/app.py`) y que `st.set_page_config` ya no se llama aqui: en una app multipagina se llama una
sola vez, antes de `st.navigation`, en el enrutador.

Solo presentacion. Toda la logica vive en `core`: esta capa abre la sesion, llama a
`crear_lista_desde_archivo` y a `actualizar_precios`, muestra el comparativo y el informe de
auditoria -que se genera siempre, sin pedirlo (principio 7 de NORMAS.md §2)- y ofrece el libro de
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

from aplicacion import actualizacion
from core.budget import (
    DetectorAtipicos,
    descartar_version,
    exportar_excel,
)
from core.catalog import (
    Catalogo,
    PrecioLeido,
    abrir_sesion,
    crear_motor,
    insumos_desconocidos,
)
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from operacion.base_datos import ErrorDeBase, preparar_base
from seguridad.permisos import Accion
from ui import sesion as ui_sesion
from ui.caso import ruta_caso
from ui.subidas import guardar_subida, nombre_seguro

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
    ui_sesion.exigir(Accion.EDITAR_HOJA)
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
        from scripts.seed import NOMBRE_PROYECTO  # diferido (RV-25)

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
    """Prepara el caso (`preparar_base`, RV-5) y carga la linea base, si aun no esta."""
    from scripts.seed import sembrar  # diferido (RV-25)

    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        preparar_base(ruta)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            partidas = len(Catalogo(sesion).partidas())
        st.sidebar.success(f"Base lista en {ruta} con {partidas} partidas.")
    except ErrorDeBase as error:
        st.sidebar.error(str(error))
    finally:
        motor.dispose()


def _ofrecer_alta(ruta: Path, archivo) -> tuple[PrecioLeido, ...]:
    """UC-02 2a: los desconocidos del archivo en «Dar de alta», ninguno elegido por defecto.

    Devuelve las filas elegidas tal como las dio la vista previa: `crear_lista_desde_archivo`
    rechaza (`ValueError`) cualquier otra.
    """
    try:
        nombre_seguro(archivo.name)
    except ValueError as error:
        # Un nombre inutilizable no es «sin ofertas»: se dice, con como arreglarlo.
        st.error(f"{str(error).rstrip('.')}. Renombre el archivo y vuelva a subirlo.")
        return ()
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
        yield guardar_subida(carpeta, archivo)


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
        preparar_base(parametros["ruta"])
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
    """Revalora (`aplicacion.actualizacion.revalorar`, la misma logica que la API) y arma la
    presentacion. `dar_de_alta` son las filas de la vista previa que el usuario eligio (2a)."""
    revaloracion = actualizacion.revalorar(
        sesion,
        parametros,
        archivo,
        dar_de_alta=dar_de_alta,
        detector=_detector_de_atipicos(),
        usuario=ui_sesion.responsable_actual(),
    )
    for aviso in revaloracion.avisos:
        (st.warning if aviso.nivel == "advertencia" else st.info)(aviso.texto)
    nuevo = revaloracion.nuevo
    libro = exportar_excel(
        nuevo.presupuesto, nuevo.informe, carpeta / f"presupuesto_{nuevo.presupuesto.codigo}.xlsx"
    )
    return Presentacion(
        tabla=_para_presentar(revaloracion.comparativo.tabla),
        resumen=revaloracion.resumen,
        informe=nuevo.informe.a_markdown(),
        ignorados=revaloracion.ignorados,
        libro=libro.read_bytes(),
        nombre_libro=libro.name,
        proyecto=str(parametros["proyecto"]),
        version_guardada=revaloracion.version_guardada,
        ruta=Path(parametros["ruta"]),
        rechazados=revaloracion.rechazados,
        dados_de_alta=revaloracion.dados_de_alta,
    )


def _detector_de_atipicos() -> DetectorAtipicos | None:
    """`aplicacion.actualizacion.detector_de_atipicos`; la pagina lo expone para sus pruebas."""
    return actualizacion.detector_de_atipicos()


def _nombrar(leido: PrecioLeido) -> str:
    return actualizacion.nombrar(leido)


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
