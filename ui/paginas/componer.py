"""Pagina de UC-10 (componer) y UC-11 (editar) una partida a mano (`docs/ERS.md`).

Es la novena pantalla y la que da sentido al prototipo: hasta esta sesion, solo los scripts de
siembra llamaban a `Catalogo.cargar_composicion`
(`2026-09-16-prototipo-composicion-apu-design.md` §1) y ninguna de las ocho
paginas existentes permitia armar una partida desde cero.

No contiene logica de dominio ni orquesta (INV-043, fase C3): la composicion y su desglose viven
en `ui/composicion.py` (puro), la persistencia y la elaboracion en `ui/elaboracion.py`, y el
presupuesto elaborado lo pinta `ui/resultado.py`. Esta pagina solo pinta: abre la sesion, arma las
tres tablas con `st.data_editor`, llama a `composicion_desde_tablas` y a `desglose` para el
desglose en vivo, guarda con `guardar_composicion` (UC-10 si la partida no existe, UC-11 si ya
existe) y confirma con `sesion.commit()` solo si hubo resultado. En tiempo de ejecucion no importa
`core.costing`, `core.budget` ni `sqlalchemy.orm` (`tests/unit/test_arquitectura.py`).

El vocabulario de los dos campos de "rendimiento" no se comparte a proposito (spec §3.2): la nota de
campo que origino este trabajo llama "rendimiento" tanto al consumo de material por unidad de obra
como a la produccion diaria de la cuadrilla, y ahi es exactamente donde se produce el error. Por eso
la columna de materiales dice "Consumo por unidad" y el campo de la partida dice "Rendimiento -
unidades por dia": nunca la misma palabra para las dos cosas.

UC-06, flujo 4a (INV-093, fase C6): con la advertencia de RF-27 a la vista, la pagina ofrece el
campo de justificacion y, al guardar, la registra con `core.catalog.justificar_rendimiento`, que la
liga al ultimo rendimiento de la partida. Por eso solo justifica si el guardado registro un
rendimiento nuevo (cuenta de rendimientos antes y despues); si no, lo avisa y no justifica, porque
el ultimo seria otro (hallazgo 1 de la revision de requisitos de C6 y N-5 de la de arquitectura).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import (
    Catalogo,
    CatalogoIncompleto,
    DispersionRendimiento,
    PropuestaRendimiento,
    abrir_sesion,
    advertencia_rendimiento,
    cambios_precio,
    crear_esquema,
    crear_motor,
    dispersion_rendimientos,
    justificar_rendimiento,
    proponer_rendimiento,
)
from core.contracts import ComposicionAPU, Dominio, ItemComputo, ModalidadManoObra
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from ui.caso import ruta_caso
from ui.composicion import (
    ComposicionInvalida,
    FilaReferencia,
    advertencia_precio_atipico,
    buscar_referencia,
    composicion_desde_tablas,
    contrastar_precio_con_reglas,
    decimal_desde_texto,
    desglose,
    etiqueta_referencia,
    fila_equipos_desde_referencia,
    fila_mano_obra_desde_referencia,
    fila_materiales_desde_referencia,
    filas_desde_composicion,
    formulario_vacio,
    sugerir_partidas_similares,
    veredicto_ml_rendimiento,
)
from ui.elaboracion import (
    COLUMNAS_CANTIDADES,
    elaborar_desde_catalogo,
    guardar_composicion,
    items_desde_filas,
    libro_excel,
)
from ui.resultado import mostrar_elaboracion

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

RENDIMIENTO_ETIQUETA = "Rendimiento — unidades por día"
CONSUMO_ETIQUETA = "Consumo por unidad"
CODIGO_PRESUPUESTO_POR_DEFECTO = "P-001"
MONEDA_POR_DEFECTO = "USD"

#: Columnas de cada tabla de insumos: la clave interna que espera `composicion_desde_tablas`
#: (contrato), no el rotulo que se ve en pantalla (presentacion).
COLUMNAS_MATERIALES = ("descripcion", "unidad", "cantidad", "precio")
COLUMNAS_EQUIPOS = ("descripcion", "cantidad", "precio", "depreciacion")
COLUMNAS_MANO_OBRA = ("descripcion", "cantidad", "sueldo", "modalidad")

#: Claves de `st.session_state` para el resultado de elaboracion y el libro de Excel ya generado
#: (paso 3): se guardan aparte de las filas de la tabla para que la descarga sobreviva a los
#: reruns de Streamlit sin repetir la elaboracion en cada uno.
CLAVE_RESULTADO = "componer_resultado_elaboracion"
CLAVE_LIBRO = "componer_libro_excel"
CLAVE_NOMBRE_LIBRO = "componer_nombre_libro"

#: Clave de `st.session_state` con el codigo para el que ya se precargaron las tres tablas (UC-11,
#: paso 1): la precarga ocurre una sola vez por codigo, para no pisar lo que la persona edite
#: despues, y se repite solo si el codigo tecleado cambia.
CLAVE_CODIGO_PRECARGADO = "componer_codigo_precargado"

#: Clave de cada `st.data_editor` de insumos; sus filas viven en `f"{clave}__filas"`.
CLAVE_MATERIALES = "componer_materiales"
CLAVE_EQUIPOS = "componer_equipos"
CLAVE_MANO_OBRA = "componer_mano_obra"

#: Rotulo del campo de UC-06 4a; solo se pinta cuando hay advertencia de rendimiento (RF-27).
JUSTIFICACION_ETIQUETA = "Justificacion de la advertencia (UC-06, flujo 4a)"


@dataclass(frozen=True, slots=True)
class AdvertenciaRendimiento:
    """La advertencia de RF-27 que la persona tiene a la vista y lo que escribio para aceptarla."""

    advertencia: str
    justificacion: str


def _presentar(valor: Decimal) -> str:
    """Un `Decimal` como lo presenta el sistema: dos decimales, con la fuente unica (INV-045)."""
    return formatear_decimal(valor, DECIMALES_PRESENTACION)


def render() -> None:
    """Cabecera de la partida, tres tablas de insumos, desglose en vivo y boton de guardado."""
    st.caption(
        "Componga una partida a mano: declare su cabecera y sus tres tablas de insumos, vea el "
        "precio unitario desglosarse en vivo (sin necesidad de guardar) y guarde la composicion. "
        "Si la partida ya existe, sus tablas se precargan al teclear su codigo y guardar reemplaza "
        "su composicion vigente (UC-11); si no existe, la crea (UC-10)."
    )

    ruta = ruta_caso()
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            _pagina(sesion)
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # Mismo criterio que las demas paginas que escriben en la base
        # (`ui/paginas/actualizacion.py`, `ui/paginas/escenarios.py`): un dato invalido o una base
        # inaccesible es un mensaje, no una traza cruda. `ComposicionInvalida` es un `ValueError`
        # y queda cubierta aqui.
        st.error(str(error))
    finally:
        motor.dispose()


# ---------------------------------------------------------------------------------------------
# Orquestacion de la pagina
# ---------------------------------------------------------------------------------------------


def _pagina(sesion: Session) -> None:
    codigo, descripcion, unidad, dominio, fecha = _cabecera()
    catalogo = Catalogo(sesion)

    _sugerencias_similares(catalogo, dominio, descripcion)

    # Antes de pintar las tablas y en la misma ejecucion en que se teclea el codigo: la cabecera
    # se pinta primero, asi que aqui ya se conoce el codigo de esta ejecucion.
    _precargar_tablas(catalogo, codigo)

    rendimiento_texto, advertida = _rendimiento(sesion, codigo)
    condiciones = st.text_area(
        "Condiciones del rendimiento",
        help="Obligatorio (RF-33): el sistema no persiste una composicion cuyo rendimiento no se "
        "declare junto con las condiciones en que se obtuvo.",
    )
    condiciones_vacias = not condiciones.strip()
    if condiciones_vacias:
        st.caption(
            "Las condiciones del rendimiento son obligatorias para guardar (RF-33): el boton de "
            "guardar permanece deshabilitado hasta que se declaren."
        )

    filas_materiales, filas_equipos, filas_mano_obra = _tablas_de_insumos()

    composicion = _desglose_en_vivo(
        codigo,
        descripcion,
        unidad,
        rendimiento_texto,
        filas_materiales,
        filas_equipos,
        filas_mano_obra,
    )

    if composicion is not None:
        _advertencias_precios(sesion, composicion)
        _contraste_aace(catalogo, sesion, codigo, dominio, composicion)

    st.subheader("Guardar")
    if st.button("Guardar composicion", type="primary", disabled=condiciones_vacias):
        if composicion is None:
            st.warning(
                "La composicion todavia no es valida (revise el aviso del desglose en vivo, "
                "arriba): corrija las tablas antes de guardar."
            )
        else:
            _guardar(sesion, catalogo, composicion, dominio, fecha, condiciones, advertida)

    items = _cantidades_de_obra(catalogo)
    _elaborar_presupuesto(catalogo, items)
    _mostrar_resultado_presupuesto()


def _cabecera() -> tuple[str, str, str, Dominio, date]:
    """Codigo, descripcion, unidad, dominio y fecha de la partida (UC-10, paso 1)."""
    st.subheader("Cabecera de la partida")
    columnas = st.columns(3)
    codigo = columnas[0].text_input("Codigo")
    descripcion = columnas[1].text_input("Descripcion")
    unidad = columnas[2].text_input("Unidad")

    columnas_dominio = st.columns(2)
    dominio = columnas_dominio[0].selectbox(
        "Dominio", list(Dominio), format_func=lambda d: d.value
    )
    fecha = columnas_dominio[1].date_input("Fecha", value=date.today())
    return codigo, descripcion, unidad, dominio, fecha


def _precargar_tablas(catalogo: Catalogo, codigo: str) -> None:
    """UC-11, paso 1: precarga las tres tablas de insumos de una partida que ya existe.

    Solo cuando el codigo tecleado cambia respecto del de la ultima precarga
    (`CLAVE_CODIGO_PRECARGADO`): asi las ediciones de la persona sobreviven a los reruns, y teclear
    otro codigo existente vuelve a precargar. Un codigo nuevo (UC-10), una partida sin lineas o un
    catalogo sin lista de precios vigente no precargan nada: las tablas quedan como estaban.
    Borrar la clave de cada `st.data_editor` es la via documentada para imponerle un contenido
    nuevo (ver `_tabla_con_busqueda`).
    """
    codigo = codigo.strip()
    if st.session_state.get(CLAVE_CODIGO_PRECARGADO) == codigo:
        return
    st.session_state[CLAVE_CODIGO_PRECARGADO] = codigo
    if not codigo:
        return
    try:
        composicion = catalogo.composicion(codigo)
    except (KeyError, CatalogoIncompleto):
        return
    tablas = filas_desde_composicion(composicion)
    if not any(tablas):
        return
    claves = (CLAVE_MATERIALES, CLAVE_EQUIPOS, CLAVE_MANO_OBRA)
    for clave, filas in zip(claves, tablas, strict=True):
        st.session_state[f"{clave}__filas"] = filas
        st.session_state.pop(clave, None)


def _rendimiento(sesion: Session, codigo: str) -> tuple[str, AdvertenciaRendimiento | None]:
    """El campo de rendimiento de la partida: precargado, con su advertencia si corresponde.

    Devuelve el texto tecleado y, si hubo advertencia de RF-27, la advertencia con su
    justificacion (UC-06, flujo 4a).

    `proponer_rendimiento` y `dispersion_rendimientos` exigen que la partida ya exista en el
    catalogo (`Catalogo.partida`, `KeyError` si no); una partida nueva (UC-10) no tiene historial
    todavia, asi que ese `KeyError` se trata igual que "sin historial": el campo queda vacio y el
    aviso lo dice, sin ser un error. `observados` (los valores crudos del historico) alimenta la
    ayuda 3 de AREN.IA (spec §3.7): la lectura adicional de `ml.anomaly` sobre el rendimiento.
    """
    propuesta: PropuestaRendimiento | None = None
    dispersion: DispersionRendimiento | None = None
    observados: list[Decimal] = []
    if codigo.strip():
        try:
            propuesta = proponer_rendimiento(sesion, codigo)
            dispersion = dispersion_rendimientos(sesion, codigo)
            observados = [r.valor for r in Catalogo(sesion).rendimientos(codigo)]
        except KeyError:
            propuesta = None
            dispersion = None

    valor_precargado = str(propuesta.rendimiento.valor) if propuesta is not None else ""
    rendimiento_texto = st.text_input(RENDIMIENTO_ETIQUETA, value=valor_precargado)

    if propuesta is None:
        st.caption(
            "Todavia no hay historial de rendimientos registrado para esta partida: es el "
            "comportamiento correcto, no un error. Declare el rendimiento con sus condiciones."
        )

    advertida = _advertir_si_corresponde(dispersion, observados, rendimiento_texto)
    return rendimiento_texto, advertida


def _advertir_si_corresponde(
    dispersion: DispersionRendimiento | None,
    observados: Sequence[Decimal],
    rendimiento_texto: str,
) -> AdvertenciaRendimiento | None:
    """RF-27: avisa si el valor tecleado se aparta de lo observado, sin bloquear nunca.

    Dos avisos independientes, ninguno bloqueante: el rango observado
    (`core.catalog.advertencia_rendimiento`, Tarea 1) y, cuando hay observaciones suficientes, la
    lectura estadistica de `ml.anomaly` (ayuda 3 de AREN.IA, spec §3.7,
    `ui.composicion.veredicto_ml_rendimiento`). Solo con el primero se pinta el campo de
    justificacion (UC-06, flujo 4a): es la advertencia que la ERS pide aceptar con un motivo.
    """
    if not rendimiento_texto.strip():
        return None
    try:
        valor = decimal_desde_texto(rendimiento_texto, "rendimiento")
    except ComposicionInvalida:
        return None  # el valor todavia no es un decimal valido: nada que advertir aun

    advertida: AdvertenciaRendimiento | None = None
    advertencia = advertencia_rendimiento(dispersion, valor)
    if advertencia:
        st.warning(advertencia)
        justificacion = st.text_input(
            JUSTIFICACION_ETIQUETA,
            help=(
                "Opcional: el motivo con el que acepta el rendimiento pese a la advertencia. Se "
                "guarda junto al rendimiento que registre este guardado; la advertencia no "
                "impide guardar (RF-27)."
            ),
        )
        advertida = AdvertenciaRendimiento(advertencia=advertencia, justificacion=justificacion)

    veredicto = veredicto_ml_rendimiento(observados, valor)
    if veredicto is not None and veredicto.atipico:
        st.warning(
            f"El bosque de aislamiento (ayuda 3 de AREN.IA, spec §3.7) tambien marca este "
            f"rendimiento como atipico frente al historico de la partida (puntaje "
            f"{veredicto.puntaje:.3f}); el registro no queda bloqueado por esto."
        )
    return advertida


def _buscador_de_referencia(
    titulo: str,
    tipo: str,
    clave: str,
    completar: Callable[[FilaReferencia], dict[str, str]],
) -> dict[str, str] | None:
    """El `st.text_input` + selector de resultados de `buscar_referencia` de una tabla (Tarea 3).

    Devuelve la fila ya convertida (`completar(fila_elegida)`) si la persona pulsa "Usar esta
    fila", o `None` si todavia no hay nada que agregar. Muestra la `ref_maprex` de la fila
    elegida como `st.caption` junto al selector: es la procedencia del precio, y sin ella el
    numero deja de ser trazable.
    """
    columna_texto, columna_resultado = st.columns([1, 2])
    texto = columna_texto.text_input(
        f"Buscar en la referencia MaPreX ({titulo.lower()})", key=f"{clave}__busqueda"
    )
    if not texto.strip():
        return None

    resultados = buscar_referencia(texto, tipo)
    if not resultados:
        columna_resultado.caption("Sin coincidencias en la referencia MaPreX.")
        return None

    fila_elegida = columna_resultado.selectbox(
        "Resultado",
        resultados,
        format_func=etiqueta_referencia,
        key=f"{clave}__resultado",
    )
    columna_resultado.caption(f"Referencia MaPreX: {fila_elegida.ref_maprex}")
    if columna_resultado.button("Usar esta fila", key=f"{clave}__usar"):
        return completar(fila_elegida)
    return None


def _tabla_con_busqueda(
    titulo: str,
    tipo: str,
    columnas: tuple[str, ...],
    clave: str,
    completar: Callable[[FilaReferencia], dict[str, str]],
    column_config: dict | None = None,
) -> list[dict]:
    """Una tabla dinamica de insumos con su buscador de la referencia MaPreX al lado (Tarea 3).

    El buscador solo agrega una fila nueva ya rellena; la persona sigue editando cualquier celda
    en la tabla de siempre, incluido el precio (spec 3.4: MaPreX es referencia, no verdad).
    `st.data_editor` no admite imponerle un valor nuevo por asignacion directa a
    `st.session_state[clave]` (esa entrada es la bitacora interna de ediciones, no el contenido);
    la via documentada es borrar su clave y volver a crearlo, que es lo que pasa aqui cuando se
    usa una fila de la referencia.
    """
    st.subheader(titulo)
    clave_filas = f"{clave}__filas"
    if clave_filas not in st.session_state:
        st.session_state[clave_filas] = []

    fila_nueva = _buscador_de_referencia(titulo, tipo, clave, completar)
    if fila_nueva is not None:
        st.session_state[clave_filas] = [*st.session_state[clave_filas], fila_nueva]
        st.session_state.pop(clave, None)
        st.rerun()

    editado = st.data_editor(
        DataFrame(st.session_state[clave_filas], columns=columnas).astype(str),
        num_rows="dynamic",
        hide_index=True,
        column_config=column_config,
        key=clave,
    )
    filas = editado.to_dict("records")
    st.session_state[clave_filas] = filas
    return filas


def _tablas_de_insumos() -> tuple[list[dict], list[dict], list[dict]]:
    """Las tres tablas dinamicas de insumos (UC-10, pasos 2 a 4), como listas de diccionarios."""
    materiales = _tabla_con_busqueda(
        "Materiales",
        "material",
        COLUMNAS_MATERIALES,
        CLAVE_MATERIALES,
        fila_materiales_desde_referencia,
        column_config={"cantidad": st.column_config.TextColumn(CONSUMO_ETIQUETA)},
    )

    equipos = _tabla_con_busqueda(
        "Equipos",
        "equipo",
        COLUMNAS_EQUIPOS,
        CLAVE_EQUIPOS,
        fila_equipos_desde_referencia,
    )

    mano_obra = _tabla_con_busqueda(
        "Mano de obra",
        "mano_obra",
        COLUMNAS_MANO_OBRA,
        CLAVE_MANO_OBRA,
        fila_mano_obra_desde_referencia,
        column_config={
            # Sin `default`: una fila nueva debe quedar en blanco en las cuatro columnas (igual
            # que materiales y equipos) para que `_fila_vacia` (`ui/composicion.py`) la descarte
            # sin error mientras el proyectista no haya escrito nada. Con un valor por defecto
            # aqui, la celda de modalidad dejaria de estar en blanco y esa fila se trataria como
            # "con datos", disparando "la descripcion no puede estar vacia" al solo agregar la
            # fila. El contrato ya asume JORNAL cuando el texto viene vacio.
            "modalidad": st.column_config.SelectboxColumn(
                "modalidad",
                options=[modalidad.value for modalidad in ModalidadManoObra],
            )
        },
    )

    return materiales, equipos, mano_obra


def _desglose_en_vivo(
    codigo: str,
    descripcion: str,
    unidad: str,
    rendimiento_texto: str,
    filas_materiales: list[dict],
    filas_equipos: list[dict],
    filas_mano_obra: list[dict],
) -> ComposicionAPU | None:
    """El `ResultadoAPU` en vivo (UC-10, paso 6): nunca hace falta guardar para verlo.

    Una tabla a medio llenar es el estado normal mientras se teclea, no un fallo: por eso
    `ComposicionInvalida` se muestra con `st.info`, no con `st.error`, y no se pinta nada mas. El
    formulario en blanco es un caso distinto: sin `formulario_vacio`, la primera vez que se abre
    la pantalla el mensaje que ve la persona es "rendimiento: '' no es un numero decimal valido",
    tecnicamente correcto pero una mala bienvenida. Aqui se distingue de "a medio llenar" (que
    sigue mostrando el aviso de siempre: es la funcionalidad principal, no se oculta).
    """
    st.subheader("Desglose en vivo")
    try:
        composicion = composicion_desde_tablas(
            codigo,
            descripcion,
            unidad,
            rendimiento_texto,
            filas_materiales,
            filas_equipos,
            filas_mano_obra,
        )
    except ComposicionInvalida as error:
        vacio = formulario_vacio(
            codigo, descripcion, filas_materiales, filas_equipos, filas_mano_obra
        )
        if vacio:
            st.info(
                "Comience por la cabecera (codigo y descripcion) y declare al menos un insumo "
                "en alguna de las tres tablas de abajo, o busquelo en la referencia MaPreX: el "
                "desglose se calcula aqui automaticamente, sin necesidad de guardar."
            )
        else:
            st.info(str(error))
        return None

    resultado = desglose(composicion)
    columnas = st.columns(6)
    columnas[0].metric("Materiales", _presentar(resultado.materiales))
    columnas[1].metric("Equipos", _presentar(resultado.equipos))
    columnas[2].metric("Mano de obra", _presentar(resultado.mano_obra))
    columnas[3].metric("Costo directo", _presentar(resultado.costo_directo))
    columnas[4].metric("Con administracion", _presentar(resultado.con_administracion))
    columnas[5].metric("Precio unitario", _presentar(resultado.precio_unitario))
    return composicion


# ---------------------------------------------------------------------------------------------
# Las cuatro ayudas de AREN.IA (Tarea 4, spec §3.7): sugieren, nunca deciden ni guardan por su
# cuenta. La logica de cada una (que hacer con el resultado, como degradar si `ml` falla o no
# esta instalado) vive en `ui/composicion.py`; esta pagina solo arma los datos planos que esas
# funciones piden y pinta lo que devuelven.
# ---------------------------------------------------------------------------------------------


def _sugerencias_similares(catalogo: Catalogo, dominio: Dominio, descripcion: str) -> None:
    """Ayuda 1: partidas del catalogo (del mismo dominio) parecidas a la descripcion tecleada.

    Solo lectura: la persona copia a mano lo que le sirva en las tablas de abajo. Ninguna tabla se
    llena por su cuenta (spec §3.7). Una falla declarada del modelo deja la ayuda sin sugerencias
    (ya la registro `ml.normalization`); cualquier otra excepcion se propaga (INV-081).
    """
    partidas = {partida.codigo: partida.descripcion for partida in catalogo.partidas(dominio)}
    propuestas = sugerir_partidas_similares(partidas, descripcion).similares
    if not propuestas:
        return

    st.subheader("Partidas similares del catalogo")
    st.caption(
        "Sugerencias de solo lectura (ayuda 1 de AREN.IA, spec §3.7): copie a mano lo que le "
        "sirva en las tablas de abajo; el sistema no llena nada por su cuenta."
    )
    for propuesta in propuestas:
        titulo = f"{propuesta.puntaje:.2f} · {propuesta.codigo} · {propuesta.descripcion}"
        with st.expander(titulo, expanded=False):
            try:
                composicion = catalogo.composicion(propuesta.codigo)
            except CatalogoIncompleto as error:
                st.caption(f"Desglose incompleto en la lista vigente: {error}")
                continue
            rendimiento = _presentar(composicion.rendimiento)
            st.caption(f"Rendimiento: {rendimiento} {composicion.unidad}/dia")
            if composicion.materiales:
                st.markdown("**Materiales**")
                st.dataframe(
                    DataFrame(
                        [
                            {
                                "descripcion": linea.descripcion,
                                "unidad": linea.unidad,
                                "cantidad": _presentar(linea.cantidad),
                                "precio": _presentar(linea.precio),
                            }
                            for linea in composicion.materiales
                        ]
                    ),
                    hide_index=True,
                )
            if composicion.equipos:
                st.markdown("**Equipos**")
                st.dataframe(
                    DataFrame(
                        [
                            {
                                "descripcion": linea.descripcion,
                                "cantidad": _presentar(linea.cantidad),
                                "precio": _presentar(linea.precio),
                                "depreciacion": str(linea.depreciacion),
                            }
                            for linea in composicion.equipos
                        ]
                    ),
                    hide_index=True,
                )
            if composicion.mano_obra:
                st.markdown("**Mano de obra**")
                st.dataframe(
                    DataFrame(
                        [
                            {
                                "descripcion": linea.descripcion,
                                "cantidad": _presentar(linea.cantidad),
                                "sueldo": _presentar(linea.sueldo),
                            }
                            for linea in composicion.mano_obra
                        ]
                    ),
                    hide_index=True,
                )


def _historico_de_insumo(
    sesion: Session, descripcion: str
) -> tuple[dict[str, Decimal], Decimal | None]:
    """El historico de variaciones de un insumo y su ultimo precio conocido (ayuda 2).

    `cambios_precio` filtra por descripcion exacta (`core/catalog/precios.py`); sin ningun cambio
    registrado para esa descripcion no hay precio anterior del que partir, y la ayuda 2 se
    abstiene (`ui.composicion.advertencia_precio_atipico` ya trata `None` como "nada que evaluar").
    """
    cambios = cambios_precio(sesion, insumo=descripcion)
    historico = {str(cambio.id): cambio.variacion for cambio in cambios}
    precio_anterior = cambios[-1].precio_nuevo if cambios else None
    return historico, precio_anterior


def _advertencias_precios(sesion: Session, composicion: ComposicionAPU) -> None:
    """Ayuda 2: avisa, sin bloquear, si algun precio de la composicion en vivo resulta atipico
    frente al historico de su insumo. Solo se evalua sobre lineas ya validas: mientras una fila
    esta a medias no hay nada que contrastar todavia.
    """
    precios = [(linea.descripcion, linea.precio) for linea in composicion.materiales]
    precios += [(linea.descripcion, linea.precio) for linea in composicion.equipos]
    precios += [(linea.descripcion, linea.sueldo) for linea in composicion.mano_obra]

    for descripcion, precio in precios:
        historico, precio_anterior = _historico_de_insumo(sesion, descripcion)
        if advertencia_precio_atipico(historico, precio_anterior, precio):
            st.warning(
                f"El precio de «{descripcion}» ({precio}) resulta atipico frente al historico "
                "de ese insumo (ayuda 2 de AREN.IA, spec §3.7); reviselo, aunque el sistema no "
                "bloquea el guardado por esto."
            )


def _contraste_aace(
    catalogo: Catalogo,
    sesion: Session,
    codigo: str,
    dominio: Dominio,
    composicion: ComposicionAPU,
) -> None:
    """Ayuda 4: contrasta el PU obtenido contra la estimacion por reglas (UC-07, compuerta G2).

    Solo aplica si la partida ya existe (hay un PU anterior del que partir: la regla no conoce la
    composicion nueva, declarado en `ml/prediction/reglas.py`). Una partida nueva (UC-10) no tiene
    ese PU anterior: no se estima, y la pantalla informa que el contraste no es posible (UC-07,
    flujo 3a; INV-094). El sistema detecta 3a como «partida sin PU anterior», no busca analogas
    (U-8 de la revision de C5).
    """
    try:
        pu_anterior = desglose(catalogo.composicion(codigo)).precio_unitario
    except KeyError:
        st.subheader("Contraste con la estimacion por reglas (AACE)")
        st.info(
            "Partida nueva: la estimacion por reglas parte del PU anterior de la partida, que "
            "no existe; el contraste no es posible (UC-07, flujo 3a)."
        )
        return
    except CatalogoIncompleto:
        return

    variaciones = [cambio.variacion for cambio in cambios_precio(sesion)]
    registros = len(catalogo.partidas(dominio))
    pu_construido = desglose(composicion).precio_unitario

    contraste = contrastar_precio_con_reglas(
        codigo, pu_construido, pu_anterior, variaciones, registros
    )
    if contraste is None:
        return

    st.subheader("Contraste con la estimacion por reglas (AACE)")
    st.caption(
        f"Ayuda 4 de AREN.IA (spec §3.7): tecnica de la compuerta G2 para este dominio: "
        f"{contraste.tecnica} ({registros} registro(s)). PU estimado por reglas: "
        f"{contraste.pu_estimado}."
    )
    if contraste.hallazgo is None:
        st.info(
            "El precio construido cae dentro del rango de la clase 3 de AACE International "
            "frente a la estimacion por reglas."
        )
    else:
        st.warning(contraste.hallazgo.descripcion)


def _guardar(
    sesion: Session,
    catalogo: Catalogo,
    composicion: ComposicionAPU,
    dominio: Dominio,
    fecha: date,
    condiciones: str,
    advertida: AdvertenciaRendimiento | None = None,
) -> None:
    """Persiste la composicion con `guardar_composicion` y confirma solo si hubo resultado.

    Sobre una partida existente, `motivo_para_no_reemplazar` decide antes de escribir (dentro de
    `guardar_composicion`): si hay motivo, `st.error` y nada se escribe ni se confirma.

    Con `advertida` (UC-06, flujo 4a), la justificacion se registra en la misma transaccion, antes
    del `commit`, y solo si el guardado registro un rendimiento nuevo: `justificar_rendimiento` la
    liga al ultimo de la partida, que sin rendimiento nuevo seria otro.
    """
    codigo = composicion.codigo_partida
    rendimientos_antes = _cuantos_rendimientos(catalogo, codigo)
    guardado = guardar_composicion(catalogo, composicion, dominio, fecha, condiciones)
    if guardado.resultado is None:
        st.error(guardado.motivo)
        return
    justificada = False
    if advertida is not None:
        if _cuantos_rendimientos(catalogo, codigo) == rendimientos_antes:
            st.warning(
                "El guardado no registro un rendimiento nuevo (el valor y las condiciones son los "
                "del ultimo estimado): la justificacion no se registro, porque se ligaria a otro "
                "rendimiento (UC-06, flujo 4a)."
            )
        elif advertida.justificacion.strip():
            justificar_rendimiento(
                sesion, codigo, advertida.justificacion, advertida.advertencia, fecha
            )
            justificada = True
        else:
            st.info(
                "El rendimiento se guardo con la advertencia y sin justificacion (UC-06, flujo "
                "4a): la advertencia informa, no impide el registro (RF-27)."
            )
    sesion.commit()
    mensaje = (
        f"Composicion guardada para la partida {composicion.codigo_partida}: precio unitario "
        f"{_presentar(guardado.resultado.precio_unitario)}."
    )
    if justificada:
        # U-1 (ronda 1 de C6): ninguna pantalla lee despues la justificacion; este aviso es la
        # evidencia de que el paso 4a ocurrio.
        mensaje += (
            " Justificacion de la advertencia registrada junto al rendimiento "
            f"{composicion.rendimiento} (UC-06, flujo 4a)."
        )
    st.success(mensaje)


def _cuantos_rendimientos(catalogo: Catalogo, codigo: str) -> int:
    """Los rendimientos registrados de la partida; cero si todavia no existe (UC-10)."""
    try:
        return len(catalogo.rendimientos(codigo))
    except KeyError:
        return 0


# ---------------------------------------------------------------------------------------------
# De componer a Excel sin salir de la aplicacion (Tarea 2, fase P3): cantidades de obra sobre las
# partidas ya guardadas, elaboracion con `core.budget.elaborar` (que audita siempre, principio 7
# de NORMAS.md §2) y descarga del libro de Excel, con el mismo patron de
# `ui/paginas/actualizacion.py`.
# ---------------------------------------------------------------------------------------------


def _cantidades_de_obra(catalogo: Catalogo) -> list[ItemComputo]:
    """La tabla de cantidad de obra por partida ya guardada (paso 1): la entrada de `elaborar`.

    El origen es obligatorio (una cantidad sin origen no es trazable, y `item_desde_cantidad` la
    rechaza: no es un dato, es un hallazgo). El dominio de cada `ItemComputo` es el que ya declara
    la cabecera de esa partida en el catalogo -su propio `models.Partida.dominio`-, no el dominio
    seleccionado arriba para la partida que se esta componiendo: esta tabla reparte cantidades
    entre todas las partidas guardadas, no solo la de la cabecera.
    """
    st.subheader("Cantidades de obra")
    partidas = catalogo.partidas()
    if not partidas:
        st.info(
            "Todavia no hay partidas guardadas en el catalogo: guarde al menos una composicion "
            "arriba antes de elaborar un presupuesto."
        )
        return []

    st.caption(
        "Asigne una cantidad de obra a las partidas ya guardadas, con su origen (obligatorio): "
        "una cantidad sin origen no es trazable, y el sistema la trata como hallazgo, no como "
        "dato."
    )
    codigos = [partida.codigo for partida in partidas]
    por_codigo = {partida.codigo: partida for partida in partidas}

    clave_filas = "componer_cantidades__filas"
    if clave_filas not in st.session_state:
        st.session_state[clave_filas] = []

    editado = st.data_editor(
        DataFrame(st.session_state[clave_filas], columns=COLUMNAS_CANTIDADES).astype(str),
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "codigo_partida": st.column_config.SelectboxColumn("codigo_partida", options=codigos),
        },
        key="componer_cantidades",
    )
    filas = editado.to_dict("records")
    st.session_state[clave_filas] = filas

    items, avisos = items_desde_filas(filas, por_codigo)
    for aviso in avisos:
        st.warning(aviso)
    return items


def _elaborar_presupuesto(catalogo: Catalogo, items: list[ItemComputo]) -> None:
    """Boton de elaboracion (paso 2): `elaborar(..., plan=plan_secuencial)`.

    Igual que `ui/paginas/elaborar.py`: sin plan la curva no existe y R2 lo hace constar; con este
    plan trivial (una partida por dia, en el orden del presupuesto) la curva cierra exactamente en
    el total y R2 y R7 quedan limpias. El prototipo debe enseñar un presupuesto sano.
    """
    st.subheader("Elaborar presupuesto")
    columnas = st.columns(3)
    codigo_presupuesto = columnas[0].text_input(
        "Codigo del presupuesto",
        value=CODIGO_PRESUPUESTO_POR_DEFECTO,
        key="componer_presupuesto_codigo",
    )
    fecha_presupuesto = columnas[1].date_input(
        "Fecha del presupuesto", value=date.today(), key="componer_presupuesto_fecha"
    )
    moneda = columnas[2].text_input(
        "Moneda", value=MONEDA_POR_DEFECTO, key="componer_presupuesto_moneda"
    )

    if items and st.button("Elaborar y auditar", type="primary"):
        with st.spinner("Elaborando..."):
            _elaborar(catalogo, items, codigo_presupuesto, fecha_presupuesto, moneda)


def _elaborar(
    catalogo: Catalogo,
    items: list[ItemComputo],
    codigo_presupuesto: str,
    fecha_presupuesto: date,
    moneda: str,
) -> None:
    """Genera el presupuesto y su curva, lo audita siempre y prepara el libro de Excel (paso 3)."""
    try:
        resultado = elaborar_desde_catalogo(
            catalogo, items, codigo_presupuesto, fecha_presupuesto, moneda
        )
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # `LookupError` (`CatalogoIncompleto`) si no hay lista de precios vigente a esa fecha;
        # `ValueError` (`PlanInvalido`) del plan de trabajo; `ArithmeticError` y
        # `SQLAlchemyError` por el mismo criterio que `ui/paginas/elaborar.py`.
        st.session_state[CLAVE_RESULTADO] = None
        st.session_state[CLAVE_LIBRO] = None
        st.error(str(error))
        return

    libro, nombre_libro = libro_excel(resultado)
    st.session_state[CLAVE_LIBRO] = libro
    st.session_state[CLAVE_NOMBRE_LIBRO] = nombre_libro
    st.session_state[CLAVE_RESULTADO] = resultado


def _mostrar_resultado_presupuesto() -> None:
    """El presupuesto elaborado, si lo hay, con el fragmento comun de `ui/resultado.py` (paso 3)."""
    resultado = st.session_state.get(CLAVE_RESULTADO)
    libro = st.session_state.get(CLAVE_LIBRO)
    if resultado is None or libro is None:
        return
    mostrar_elaboracion(
        resultado, libro, st.session_state.get(CLAVE_NOMBRE_LIBRO), prefijo="componer"
    )
