"""Pagina de UC-01: elaborar un presupuesto desde un cómputo de muestra por dominio (Sesion F.1).

Selector de dominio, archivo de muestra, adaptador, tabla de `ItemComputo` extraidos y boton para
elaborar el presupuesto: el mismo flujo que describe la spec F.1 §2 para `POST /computos/{dominio}`
seguido de `POST /presupuestos`, pero llamando a `core` y a `adapters` directo (la UI no consume la
API por HTTP, decision del usuario, 2026-08-31, spec F.1 §4). `elaborar()` audita siempre, sin que
se le pida (principio 7 de NORMAS.md §2): el informe se muestra en cuanto el presupuesto existe.

El adaptador civil tabular (`adapters/civil/tabular.py`) es el unico que no trae su propio codigo
de partida en la fuente: recibe un mapeo `codigos` del llamador (`adapters/civil/reglas.py`). Esta
pantalla deja que el usuario elija esos codigos entre las partidas civiles ya cargadas en el
catalogo, en vez de inventar codigos que el catalogo no tiene (regla del contrato congelado,
NORMAS.md §5: los codigos de partida son del catalogo, no del adaptador).

UC-01 3a (INV-072, D6): un item cuyo codigo no esta en el catalogo no aborta la elaboracion: queda
pendiente, el informe lo declara y la pantalla propone partidas similares
(`ui.elaboracion.propuestas_de_pendientes`, calculadas una vez por elaboracion). Si el usuario
acepta una, `ui.elaboracion.aceptar_propuesta` reasigna el item y se vuelve a elaborar. Las dos se
llaman como atributos del modulo `ui.elaboracion`, para que las pruebas las parchen donde se
resuelven.

UC-01 6 (INV-087): el proyectista distribuye las partidas en periodos. Cada elaboracion sin plan
del proyectista (el boton, aceptar una propuesta de 3a o registrar un rendimiento de 3b) usa el
plan por defecto, `plan_secuencial`, que decide `ui.elaboracion.plan_de`, y precarga con el la
tabla «Plan de trabajo» (si descarta un plan editado, lo avisa); el proyectista la edita y
«Aplicar plan y volver a elaborar» elabora con su plan. Un plan invalido es un mensaje y deja a la
vista el presupuesto anterior.

UC-01 3b (INV-088): si una partida no tiene rendimiento estimado vigente a la fecha del
presupuesto, la elaboracion no se detiene en el mensaje de `CatalogoIncompleto`: el bloque
«Rendimientos por declarar» propone el rendimiento del historico con su dispersion
(`ui.elaboracion.rendimientos_por_declarar`), exige declarar su tipo, lo registra
(`ui.elaboracion.declarar_rendimiento`) y vuelve a elaborar.
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from adapters.civil.tabular import AdaptadorCivilTabular
from adapters.industrial.adaptador import AdaptadorIndustrial
from adapters.sistemas.adaptador import AdaptadorSistemas
from adapters.telecom.adaptador import AdaptadorTelecom
from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion, crear_motor
from core.contracts import AdaptadorDominio, Dominio, ItemComputo
from core.contracts.apu import TipoRendimiento
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from operacion.base_datos import preparar_base
from ui import elaboracion
from ui.caso import ruta_caso
from ui.resultado import mostrar_elaboracion
from ui.subidas import guardar_subida

CODIGO_POR_DEFECTO = "P-001"
MONEDA_POR_DEFECTO = "USD"
CLAVE_ITEMS = "elaborar_items"
CLAVE_RESULTADO = "elaborar_resultado"
#: Las propuestas para los pendientes de la elaboracion guardada en `CLAVE_RESULTADO`.
CLAVE_PROPUESTAS = "elaborar_propuestas"
#: El `st.data_editor` del plan de trabajo (UC-01 6); sus filas viven en `f"{CLAVE_PLAN}__filas"`.
CLAVE_PLAN = "elaborar_plan"
#: Si la ultima elaboracion sin plan del proyectista descarto uno editado (duda 6 de la revision).
CLAVE_PLAN_REINICIADO = "elaborar_plan_reiniciado"
#: Las filas del plan por defecto de la ultima elaboracion sin plan del proyectista: el aviso de
#: `CLAVE_PLAN_REINICIADO` compara con ellas, no con las del plan por defecto nuevo, que cambian
#: con el computo aunque nadie haya editado la tabla (R-2 de la re-revision de U).
CLAVE_PLAN_POR_DEFECTO = "elaborar_plan_por_defecto"
#: Las partidas sin rendimiento estimado vigente de la ultima elaboracion (UC-01 3b).
CLAVE_RENDIMIENTOS = "elaborar_rendimientos_por_declarar"

#: Adaptadores sin parametros propios: el dominio y el archivo bastan para construirlos.
_ADAPTADORES_SIN_CODIGOS: dict[Dominio, type[AdaptadorDominio]] = {
    Dominio.TELECOM: AdaptadorTelecom,
    Dominio.INDUSTRIAL: AdaptadorIndustrial,
    Dominio.SISTEMAS: AdaptadorSistemas,
}


def render() -> None:
    """Selector de dominio y archivo; tabla de cómputo; botón de elaboración e informe."""
    st.caption(
        "Elige un dominio, carga su archivo de muestra (data/samples/<dominio>/) y extrae el "
        "cómputo con el adaptador correspondiente; luego elabora el presupuesto, que se audita "
        "siempre."
    )

    parametros = _barra_lateral()
    dominio = parametros["dominio"]

    codigos_civil: dict[str, str] = {}
    if dominio == Dominio.CIVIL:
        codigos_civil = _codigos_civil(parametros["ruta"]) or {}
        if not codigos_civil:
            st.warning(
                "El catalogo no tiene partidas del dominio civil todavia (o la base de datos no "
                "se pudo leer; revise el mensaje de error de arriba, si lo hay): cargue primero "
                "un presupuesto civil (por ejemplo, sembrando la linea base en la pagina de "
                "Actualizacion) antes de extraer un cómputo civil."
            )

    archivo = st.file_uploader("Archivo de muestra (CSV)", type=["csv"])
    puede_extraer = archivo is not None and (dominio != Dominio.CIVIL or bool(codigos_civil))

    if st.button("Extraer cómputo", disabled=not puede_extraer):
        _extraer(dominio, archivo, codigos_civil)

    items = st.session_state.get(CLAVE_ITEMS)
    _mostrar_items(items)

    if items and st.button("Elaborar presupuesto", type="primary"):
        with st.spinner("Elaborando..."):
            _elaborar(parametros, items)

    _declarar_rendimientos(parametros)
    _mostrar_resultado(parametros)


# ---------------------------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------------------------


def _barra_lateral() -> dict[str, object]:
    with st.sidebar:
        st.header("Cómputo")
        dominio = st.selectbox("Dominio", list(Dominio), format_func=lambda d: d.value)

        st.header("Presupuesto")
        codigo = st.text_input("Código del presupuesto", value=CODIGO_POR_DEFECTO)
        fecha = st.date_input("Fecha", value=date.today())
        moneda = st.text_input("Moneda", value=MONEDA_POR_DEFECTO)

    return {
        "ruta": ruta_caso(),
        "dominio": dominio,
        "codigo": codigo,
        "fecha": fecha,
        "moneda": moneda,
    }


def _codigos_civil(ruta: Path) -> dict[str, str] | None:
    """Los códigos de concreto, encofrado, excavación, tubería y (opcional) relleno del catálogo.

    `None` si la base de datos no se pudo leer (el error ya se mostró con `st.error`, mismo
    criterio que `ui/paginas/actualizacion.py`); un diccionario vacío si se pudo leer pero el
    catálogo no tiene partidas civiles todavía.
    """
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        preparar_base(ruta)
        with abrir_sesion(motor) as sesion:
            codigos = [partida.codigo for partida in Catalogo(sesion).partidas(Dominio.CIVIL)]
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        st.error(str(error))
        return None
    finally:
        motor.dispose()

    if not codigos:
        return {}

    with st.sidebar:
        st.header("Códigos de partida (civil)")
        concreto = st.selectbox("Concreto", codigos, key="elaborar_civil_concreto")
        encofrado = st.selectbox("Encofrado", codigos, key="elaborar_civil_encofrado")
        excavacion = st.selectbox("Excavación", codigos, key="elaborar_civil_excavacion")
        tuberia = st.selectbox("Tubería", codigos, key="elaborar_civil_tuberia")
        con_relleno = st.checkbox("Incluir relleno (balance R5)", value=False)
        relleno = (
            st.selectbox("Relleno", codigos, key="elaborar_civil_relleno") if con_relleno else None
        )

    mapeo = {
        "concreto": concreto,
        "encofrado": encofrado,
        "excavacion": excavacion,
        "tuberia": tuberia,
    }
    if relleno is not None:
        mapeo["relleno"] = relleno
    return mapeo


# ---------------------------------------------------------------------------------------------
# Extracción del cómputo
# ---------------------------------------------------------------------------------------------


def _construir_adaptador(dominio: Dominio, codigos_civil: Mapping[str, str]) -> AdaptadorDominio:
    if dominio == Dominio.CIVIL:
        return AdaptadorCivilTabular(codigos=codigos_civil)
    return _ADAPTADORES_SIN_CODIGOS[dominio]()


def _extraer(dominio: Dominio, archivo, codigos_civil: Mapping[str, str]) -> None:
    try:
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_archivo = guardar_subida(carpeta, archivo)
            adaptador = _construir_adaptador(dominio, codigos_civil)
            items = adaptador.extraer(ruta_archivo)
    except (LookupError, ValueError, ArithmeticError) as error:
        # `ValueError` cubre tanto un archivo mal formado (columnas faltantes, tipo de fila
        # desconocido) como el limite declarado del balance de relleno civil (dos diametros de
        # tuberia); `ArithmeticError` cubre un `Decimal` mal formado en alguna celda.
        st.session_state[CLAVE_ITEMS] = None
        st.error(str(error))
        return

    st.session_state[CLAVE_ITEMS] = items
    st.session_state[CLAVE_RESULTADO] = None


def _mostrar_items(items: list[ItemComputo] | None) -> None:
    if not items:
        return

    st.subheader("Cómputo extraído")
    tabla = DataFrame(
        [
            {
                "codigo_partida": item.codigo_partida,
                "descripcion": item.descripcion,
                "unidad": item.unidad,
                "cantidad": formatear_decimal(item.cantidad, DECIMALES_PRESENTACION),
                "origen_id": item.origen_id,
                "origen_tipo": item.origen_tipo,
                "regla": item.regla or "",
            }
            for item in items
        ]
    )
    st.dataframe(tabla, hide_index=True)


# ---------------------------------------------------------------------------------------------
# Elaboración del presupuesto
# ---------------------------------------------------------------------------------------------


def _elaborar(
    parametros: dict[str, object],
    items: list[ItemComputo],
    filas_plan: list[dict[str, str]] | None = None,
) -> bool:
    """Elabora `items` y guarda el resultado; con `filas_plan`, con el plan del proyectista.

    Sin `filas_plan` usa el plan por defecto y precarga con el la tabla del plan (INV-087). Si
    falla, pinta el error y devuelve `False`: con el plan del proyectista el presupuesto anterior
    sigue a la vista; sin el, se borra.
    """
    try:
        plan = elaboracion.plan_de(filas_plan)
    except ValueError as error:  # `ComposicionInvalida`: una fila del plan a medias
        st.error(str(error))
        return False
    ruta = parametros["ruta"]
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        preparar_base(ruta)
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            try:
                resultado = elaboracion.elaborar_desde_catalogo(
                    catalogo,
                    items,
                    str(parametros["codigo"]),
                    parametros["fecha"],
                    str(parametros["moneda"]),
                    plan,
                )
            except CatalogoIncompleto:
                por_declarar = elaboracion.rendimientos_por_declarar(
                    sesion, items, parametros["fecha"]
                )
                if not por_declarar:
                    # Falta un precio, una unidad o una depreciacion: el mensaje de siempre. La
                    # falta de lista vigente no llega aqui: la lanza `rendimientos_por_declarar`.
                    raise
                # UC-01 3b: el bloque «Rendimientos por declarar» toma el relevo del mensaje.
                st.session_state[CLAVE_RENDIMIENTOS] = por_declarar
                st.session_state[CLAVE_RESULTADO] = None
                st.session_state[CLAVE_PROPUESTAS] = ()
                return False
            partidas = {partida.codigo: partida.descripcion for partida in catalogo.partidas()}
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # `LookupError` (`CatalogoIncompleto`) si no hay lista de precios vigente a esa fecha (un
        # item sin partida ya no lanza: queda pendiente, UC-01 3a); `ValueError` (`PlanInvalido`)
        # del plan de trabajo; `ArithmeticError`/`SQLAlchemyError` por simetría con el mismo
        # criterio de `ui/paginas/actualizacion.py`.
        if filas_plan is None:
            st.session_state[CLAVE_RESULTADO] = None
            st.session_state[CLAVE_PROPUESTAS] = ()
        st.error(str(error))
        return False
    finally:
        motor.dispose()

    st.session_state[CLAVE_RESULTADO] = resultado
    st.session_state[CLAVE_RENDIMIENTOS] = ()
    st.session_state[CLAVE_PROPUESTAS] = elaboracion.propuestas_de_pendientes(
        partidas, resultado.pendientes
    )
    if filas_plan is None:
        # El plan vuelve al de por defecto; si con eso se descarta uno editado, se avisa. Editado
        # es distinto del plan por defecto que se precargo, no del nuevo: si el computo cambio,
        # el nuevo difiere aunque nadie haya tocado la tabla.
        por_defecto = elaboracion.filas_del_plan_por_defecto(resultado.presupuesto)
        anteriores = st.session_state.get(f"{CLAVE_PLAN}__filas")
        precargado = st.session_state.get(CLAVE_PLAN_POR_DEFECTO)
        st.session_state[CLAVE_PLAN_REINICIADO] = bool(anteriores) and anteriores != precargado
        st.session_state[CLAVE_PLAN_POR_DEFECTO] = por_defecto
        st.session_state[f"{CLAVE_PLAN}__filas"] = por_defecto
        st.session_state.pop(CLAVE_PLAN, None)  # el editor se vuelve a crear con esas filas
    else:
        st.session_state[CLAVE_PLAN_REINICIADO] = False
    return True


def _mostrar_resultado(parametros: dict[str, object]) -> None:
    resultado = st.session_state.get(CLAVE_RESULTADO)
    if resultado is None:
        return
    libro, nombre_libro = elaboracion.libro_excel(resultado)
    eleccion = mostrar_elaboracion(
        resultado,
        libro,
        nombre_libro,
        prefijo="elaborar",
        propuestas=st.session_state.get(CLAVE_PROPUESTAS, ()),
    )
    _plan_de_trabajo(parametros)
    if eleccion is None:
        return
    # D6: el item pendiente pasa a la partida aceptada y se vuelve a elaborar con la lista guardada.
    pendiente, codigo_elegido = eleccion
    items = st.session_state.get(CLAVE_ITEMS)
    if not items or pendiente not in items:
        # El computo cambio (o una extraccion fallo) despues de esta elaboracion: el resultado a la
        # vista ya no corresponde a los items guardados (revision de A4, Q-2).
        st.error(
            "El computo cambio despues de esta elaboracion: extraigalo de nuevo y vuelva a "
            "elaborar el presupuesto antes de aceptar una propuesta."
        )
        return
    st.session_state[CLAVE_ITEMS] = elaboracion.aceptar_propuesta(items, pendiente, codigo_elegido)
    with st.spinner("Elaborando..."):
        elaborado = _elaborar(parametros, st.session_state[CLAVE_ITEMS])
    if elaborado:
        st.rerun()
    # Si la reelaboracion fallo, `_elaborar` ya pinto su `st.error`: sin `st.rerun()`, que lo
    # borraria, queda a la vista (revision de A4, R-2).


def _plan_de_trabajo(parametros: dict[str, object]) -> None:
    """UC-01 6 (INV-087): la tabla del plan de trabajo y el boton que elabora con ella."""
    st.subheader("Plan de trabajo")
    st.caption(
        "Distribuya las partidas en periodos: cada fila es la fraccion de una partida que se "
        "ejecuta en un periodo, y las fracciones de cada partida suman 1. Por defecto, una "
        "partida por dia; la curva de inversion sale de este plan y cierra en el total."
    )
    if st.session_state.get(CLAVE_PLAN_REINICIADO):
        st.caption(
            "Al volver a elaborar, el plan de trabajo volvio a una partida por dia: el plan "
            "editado antes se descarto. Vuelva a distribuirlo y aplique el plan."
        )
    clave_filas = f"{CLAVE_PLAN}__filas"
    editado = st.data_editor(
        DataFrame(st.session_state.get(clave_filas, []), columns=elaboracion.COLUMNAS_PLAN).astype(
            str
        ),
        num_rows="dynamic",
        hide_index=True,
        key=CLAVE_PLAN,
    )
    filas = editado.to_dict("records")
    st.session_state[clave_filas] = filas
    if not st.button("Aplicar plan y volver a elaborar", key="elaborar_aplicar_plan"):
        return
    items = st.session_state.get(CLAVE_ITEMS)
    if not items:
        st.error("Extraiga de nuevo el computo antes de aplicar el plan.")
        return
    with st.spinner("Elaborando..."):
        elaborado = _elaborar(parametros, items, filas_plan=filas)
    if elaborado:
        st.rerun()  # el presupuesto de arriba se pinto antes de volver a elaborar
    # Si fallo, `_elaborar` ya pinto su `st.error`: sin `st.rerun()`, que lo borraria.


# ---------------------------------------------------------------------------------------------
# UC-01 3b: partidas sin rendimiento vigente (INV-088)
# ---------------------------------------------------------------------------------------------


def _presentar(valor: Decimal) -> str:
    """Un `Decimal` como lo presenta el sistema: dos decimales, con la fuente unica (INV-045)."""
    return formatear_decimal(valor, DECIMALES_PRESENTACION)


def _declarar_rendimientos(parametros: dict[str, object]) -> None:
    """El bloque «Rendimientos por declarar»: propuesta, dispersion, tipo declarado y registro."""
    por_declarar = st.session_state.get(CLAVE_RENDIMIENTOS) or ()
    if not por_declarar:
        return
    st.subheader("Rendimientos por declarar")
    st.caption(
        "Estas partidas no tienen rendimiento estimado vigente a la fecha del presupuesto: se "
        "propone el del historico con su dispersion. Declare si es estimado o medido para "
        "registrarlo y volver a elaborar."
    )
    # Claves por codigo, no por posicion (U-2 de la revision de C5): tras registrar una partida la
    # siguiente ocupa su lugar, y con clave por posicion heredaria el tipo ya declarado.
    for entrada in por_declarar:
        codigo = entrada.codigo_partida
        if entrada.propuesta is None:
            st.error(
                f"{codigo}: la partida no tiene ningun rendimiento registrado que proponer; "
                "declarelo con sus condiciones en «Componer una partida»."
            )
            continue
        rendimiento = entrada.propuesta.rendimiento
        dispersion = entrada.propuesta.dispersion
        st.markdown(
            f"**{codigo}** · rendimiento propuesto {_presentar(rendimiento.valor)} unidades por "
            f"dia ({rendimiento.tipo.value} del {rendimiento.fecha})"
        )
        st.caption(
            f"Dispersion del historico: {dispersion.observaciones} observaciones "
            f"({dispersion.medidos} medidas, {dispersion.estimados} estimadas), media "
            f"{_presentar(dispersion.media)}, rango [{_presentar(dispersion.minimo)}, "
            f"{_presentar(dispersion.maximo)}]."
        )
        tipo = st.radio(
            f"Tipo declarado del rendimiento de {codigo}",
            [opcion.value for opcion in TipoRendimiento],
            index=None,
            horizontal=True,
            key=f"elaborar_tipo_rendimiento_{codigo}",
        )
        if st.button(
            "Registrar y volver a elaborar", key=f"elaborar_registrar_rendimiento_{codigo}"
        ):
            _registrar_y_elaborar(parametros, entrada, tipo)


def _registrar_y_elaborar(
    parametros: dict[str, object], entrada: elaboracion.RendimientoPorDeclarar, tipo: str | None
) -> None:
    """Registra el rendimiento declarado y vuelve a elaborar; si algo falla, el mensaje queda."""
    if tipo is None:
        st.error(f"Declare si el rendimiento de {entrada.codigo_partida} es estimado o medido.")
        return
    items = st.session_state.get(CLAVE_ITEMS)
    if not items:
        st.error("Extraiga de nuevo el computo antes de registrar el rendimiento.")
        return
    ruta = parametros["ruta"]
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            elaboracion.declarar_rendimiento(
                sesion, entrada, TipoRendimiento(tipo), parametros["fecha"]
            )
            sesion.commit()
    except (LookupError, ValueError, SQLAlchemyError) as error:
        st.error(str(error))
        return
    finally:
        motor.dispose()
    with st.spinner("Elaborando..."):
        elaborado = _elaborar(parametros, items)
    if elaborado or st.session_state.get(CLAVE_RENDIMIENTOS):
        st.rerun()  # el presupuesto, o la siguiente partida por declarar
