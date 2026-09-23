"""Pagina de UC-01: elaborar un presupuesto desde un cómputo de muestra por dominio (Sesion F.1).

Selector de dominio, archivo de muestra, adaptador, tabla de `ItemComputo` extraidos y boton para
elaborar el presupuesto: el mismo flujo que describe la spec F.1 §2 para `POST /computos/{dominio}`
seguido de `POST /presupuestos`, pero llamando a `core` y a `adapters` directo (la UI no consume la
API por HTTP, decision del usuario, 2026-08-31, spec F.1 §4). `elaborar()` audita siempre, sin que
se le pida (principio 7 de CLAUDE.md §2): el informe se muestra en cuanto el presupuesto existe.

El adaptador civil tabular (`adapters/civil/tabular.py`) es el unico que no trae su propio codigo
de partida en la fuente: recibe un mapeo `codigos` del llamador (`adapters/civil/reglas.py`). Esta
pantalla deja que el usuario elija esos codigos entre las partidas civiles ya cargadas en el
catalogo, en vez de inventar codigos que el catalogo no tiene (regla del contrato congelado,
CLAUDE.md §5: los codigos de partida son del catalogo, no del adaptador).
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from datetime import date
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from adapters.civil.tabular import AdaptadorCivilTabular
from adapters.industrial.adaptador import AdaptadorIndustrial
from adapters.sistemas.adaptador import AdaptadorSistemas
from adapters.telecom.adaptador import AdaptadorTelecom
from core.budget import elaborar, exportar_excel, generar_presupuesto, plan_secuencial
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.contracts import AdaptadorDominio, Dominio, ItemComputo, ParametrosCosto
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal

TITULO = "Elaborar presupuesto (UC-01)"
RUTA_BASE_POR_DEFECTO = "data/apu.db"
CODIGO_POR_DEFECTO = "P-001"
MONEDA_POR_DEFECTO = "USD"
CLAVE_ITEMS = "elaborar_items"
CLAVE_RESULTADO = "elaborar_resultado"

#: Adaptadores sin parametros propios: el dominio y el archivo bastan para construirlos.
_ADAPTADORES_SIN_CODIGOS: dict[Dominio, type[AdaptadorDominio]] = {
    Dominio.TELECOM: AdaptadorTelecom,
    Dominio.INDUSTRIAL: AdaptadorIndustrial,
    Dominio.SISTEMAS: AdaptadorSistemas,
}


def render() -> None:
    """Selector de dominio y archivo; tabla de cómputo; botón de elaboración e informe."""
    st.title(TITULO)
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

    _mostrar_resultado(st.session_state.get(CLAVE_RESULTADO))


# ---------------------------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------------------------


def _barra_lateral() -> dict[str, object]:
    with st.sidebar:
        st.header("Base de datos")
        ruta = st.text_input("Archivo SQLite", value=RUTA_BASE_POR_DEFECTO)

        st.header("Cómputo")
        dominio = st.selectbox("Dominio", list(Dominio), format_func=lambda d: d.value)

        st.header("Presupuesto")
        codigo = st.text_input("Código del presupuesto", value=CODIGO_POR_DEFECTO)
        fecha = st.date_input("Fecha", value=date.today())
        moneda = st.text_input("Moneda", value=MONEDA_POR_DEFECTO)

    return {
        "ruta": Path(ruta),
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
        crear_esquema(motor)
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
            ruta_archivo = Path(carpeta) / archivo.name
            ruta_archivo.write_bytes(archivo.getvalue())
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


def _elaborar(parametros: dict[str, object], items: list[ItemComputo]) -> None:
    ruta = parametros["ruta"]
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            codigos_unicos = list(dict.fromkeys(item.codigo_partida for item in items))
            composiciones = catalogo.composiciones(codigos_unicos, fecha=parametros["fecha"])
            borrador = generar_presupuesto(
                items,
                composiciones,
                ParametrosCosto(),
                codigo=str(parametros["codigo"]),
                fecha=parametros["fecha"],
                moneda=str(parametros["moneda"]),
            )
            resultado = elaborar(
                items,
                composiciones,
                ParametrosCosto(),
                codigo=str(parametros["codigo"]),
                fecha=parametros["fecha"],
                moneda=str(parametros["moneda"]),
                plan=plan_secuencial(borrador),
            )
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # `LookupError` (`CatalogoIncompleto`) si falta la composición de alguna partida del
        # cómputo (por ejemplo, un dominio sin catálogo cargado); `ValueError` de
        # `generar_presupuesto` o `plan_secuencial`; `ArithmeticError`/`SQLAlchemyError` por
        # simetría con el mismo criterio de `ui/paginas/actualizacion.py`.
        st.session_state[CLAVE_RESULTADO] = None
        st.error(str(error))
        return
    finally:
        motor.dispose()

    st.session_state[CLAVE_RESULTADO] = resultado


def _mostrar_resultado(resultado) -> None:
    if resultado is None:
        return

    st.subheader("Presupuesto elaborado")
    total = formatear_decimal(resultado.presupuesto.total, DECIMALES_PRESENTACION)
    st.metric("Total del presupuesto", f"{total} {resultado.presupuesto.moneda}")

    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / f"presupuesto_{resultado.presupuesto.codigo}.xlsx"
        libro = exportar_excel(resultado.presupuesto, resultado.informe, ruta)
        st.download_button(
            "Exportar a Excel",
            data=libro.read_bytes(),
            file_name=libro.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.subheader("Informe de auditoría")
    st.markdown(resultado.informe.a_markdown())
