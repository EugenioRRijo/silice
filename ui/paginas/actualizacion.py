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
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.budget import Comparativo, actualizar_precios, exportar_excel
from core.catalog import (
    Catalogo,
    abrir_sesion,
    crear_esquema,
    crear_lista_desde_archivo,
    crear_motor,
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
    desconocidos: tuple[str, ...]
    libro: bytes
    nombre_libro: str


def render() -> None:
    """Pantalla unica: parametros en la barra lateral, archivo y resultados en el cuerpo."""
    st.caption(
        "Carga una lista de precios nueva (CSV o XLSX con las columnas tipo, insumo, unidad y "
        "precio) y el sistema revalora el presupuesto guardado, registra que cambio y audita la "
        "version nueva."
    )

    parametros = _barra_lateral()
    archivo = st.file_uploader("Lista de precios", type=TIPOS_ACEPTADOS)

    if st.button("Revalorar presupuesto", type="primary", disabled=archivo is None):
        with st.spinner("Revalorando..."):
            _ejecutar(parametros, archivo)

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


# ---------------------------------------------------------------------------------------------
# Caso de uso
# ---------------------------------------------------------------------------------------------


def _ejecutar(parametros: dict[str, object], archivo) -> None:
    """Corre UC-02 completo y deja en la sesion de Streamlit lo que hay que mostrar."""
    motor = crear_motor(f"sqlite:///{parametros['ruta'].as_posix()}")
    try:
        crear_esquema(motor)
        with tempfile.TemporaryDirectory() as carpeta, abrir_sesion(motor) as sesion:
            ruta_archivo = Path(carpeta) / archivo.name
            ruta_archivo.write_bytes(archivo.getvalue())
            st.session_state[CLAVE_RESULTADO] = _actualizar(
                sesion, parametros, ruta_archivo, Path(carpeta)
            )
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # Los cuatro fallos previsibles de UC-02, que en una pantalla deben ser un mensaje y no una
        # traza cruda: `CatalogoIncompleto` (LookupError) y los errores de lectura del archivo
        # (ValueError); el `IntegrityError` de un segundo clic con el mismo codigo de presupuesto
        # (SQLAlchemyError); y `decimal.InvalidOperation` (ArithmeticError) desde cualquier
        # importe que llegue mal formado (revision final, item 5).
        st.session_state[CLAVE_RESULTADO] = None
        st.error(str(error))
    finally:
        motor.dispose()


def _actualizar(
    sesion: Session, parametros: dict[str, object], archivo: Path, carpeta: Path
) -> Presentacion:
    """Crea la lista, revalora, confirma si algun insumo cambio de precio y arma la presentacion."""
    resumen = crear_lista_desde_archivo(
        sesion,
        archivo,
        nombre=str(parametros["nombre"]),
        moneda=str(parametros["moneda"]),
        fecha_vigencia=parametros["vigencia"],
        origen=archivo.name,
    )
    nuevo, comparativo = actualizar_precios(
        sesion,
        str(parametros["proyecto"]),
        str(parametros["codigo"]),
        resumen.lista,
        str(parametros["codigo_nuevo"]),
    )
    libro = exportar_excel(
        nuevo.presupuesto, nuevo.informe, carpeta / f"presupuesto_{nuevo.presupuesto.codigo}.xlsx"
    )
    presentacion = Presentacion(
        tabla=_para_presentar(comparativo.tabla),
        resumen=_resumen(comparativo, nuevo.presupuesto.moneda),
        informe=nuevo.informe.a_markdown(),
        desconocidos=tuple(
            f"{precio.descripcion} ({precio.tipo.value})" for precio in resumen.desconocidos
        ),
        libro=libro.read_bytes(),
        nombre_libro=libro.name,
    )

    if comparativo.insumos_afectados == 0:
        # Ningun insumo cambio de precio entre la lista anterior y la nueva: no hay nada que
        # guardar (UC-02, flujo 3a). Descartar la transaccion tambien descarta la lista nueva, que
        # aqui es identica a la anterior en sus precios.
        st.warning("Ningun precio cambio: no se guardo una version nueva (UC-02, flujo 3a).")
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
    return presentacion


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


def _mostrar(presentacion: Presentacion | None) -> None:
    if presentacion is None:
        return

    st.subheader("Comparativo por partida")
    st.metric("Total del presupuesto", presentacion.resumen)
    st.dataframe(presentacion.tabla, hide_index=True)

    if presentacion.desconocidos:
        st.warning(
            "Insumos del archivo que no estan en el catalogo (no se crearon ni intervienen en el "
            "recalculo): " + ", ".join(presentacion.desconocidos)
        )

    st.download_button(
        "Exportar a Excel",
        data=presentacion.libro,
        file_name=presentacion.nombre_libro,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.subheader("Informe de auditoria de la version nueva")
    st.markdown(presentacion.informe)
