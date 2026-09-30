"""Fragmento de Streamlit que muestra un presupuesto elaborado (INV-043, fase C3).

Lo comparten la pagina de componer y la de elaborar: total, resumen por severidad, descarga del
libro de Excel y el informe de auditoria. El informe se muestra tenga hallazgos o no: el informe de
auditoria se genera siempre, sin que el usuario lo pida (principio 7 de NORMAS.md §2), y eso es
principio del proyecto, no preferencia de pantalla.

Solo pinta lo que recibe: no abre la base (sin `sqlalchemy.orm`) ni calcula (sin `core.costing`).
No conoce ninguna clave de `st.session_state` de ninguna pagina; `prefijo` es el de las claves de
widget de la pagina que lo llama.

UC-01 3a (INV-072, D6): si la elaboracion dejo items pendientes (sin partida en el catalogo), los
declara en un bloque «Pendientes» con sus propuestas de partidas similares; para los que traen
propuestas ofrece un selector y el boton «Aplicar y volver a elaborar», y devuelve la eleccion. La
sustitucion y la reelaboracion las hace la pagina (`ui.elaboracion.aceptar_propuesta`). Lo vigila
`tests/unit/test_arquitectura.py::test_ui_respeta_sus_importaciones_prohibidas`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import streamlit as st

from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal

if TYPE_CHECKING:
    from core.budget import ResultadoElaboracion
    from core.contracts import ItemComputo
    from ui.elaboracion import PendienteConPropuestas

MIME_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def mostrar_elaboracion(
    resultado: ResultadoElaboracion,
    libro: bytes,
    nombre_libro: str,
    *,
    prefijo: str,
    propuestas: Sequence[PendienteConPropuestas] = (),
) -> tuple[ItemComputo, str] | None:
    """Totales, severidades, pendientes, la descarga y el informe de auditoria (siempre).

    Devuelve `(pendiente, codigo_elegido)` si se pulso «Aplicar y volver a elaborar»; si no, `None`.
    """
    st.subheader("Presupuesto elaborado")
    total = formatear_decimal(resultado.presupuesto.total, DECIMALES_PRESENTACION)
    st.metric("Total del presupuesto", f"{total} {resultado.presupuesto.moneda}")

    resumen_severidad = resultado.informe.por_severidad()
    if resumen_severidad:
        columnas_severidad = st.columns(len(resumen_severidad))
        for columna, (severidad, total_hallazgos) in zip(
            columnas_severidad, resumen_severidad.items(), strict=True
        ):
            columna.metric(severidad.name, total_hallazgos)
    else:
        st.success("Sin hallazgos: la auditoria no encontro ninguna inconsistencia.")

    st.download_button(
        "Exportar a Excel",
        data=libro,
        file_name=nombre_libro,
        mime=MIME_EXCEL,
        key=f"{prefijo}_exportar_excel",
    )

    eleccion = _pendientes(resultado, propuestas, prefijo)

    st.subheader("Informe de auditoria")
    st.markdown(resultado.informe.a_markdown())
    return eleccion


def _pendientes(
    resultado: ResultadoElaboracion,
    propuestas: Sequence[PendienteConPropuestas],
    prefijo: str,
) -> tuple[ItemComputo, str] | None:
    """El bloque «Pendientes» (UC-01 3a): cada item sin partida, sus propuestas y la aceptacion.

    `propuestas` trae una entrada por pendiente, en su orden, o ninguna (la pagina de componer no
    propone): sin `similares` no hay selector. El indice va en las claves de widget para que dos
    pendientes con el mismo origen no las repitan.
    """
    if not resultado.pendientes:
        return None
    st.subheader("Pendientes")
    st.caption(
        "Estos items del computo no tienen partida en el catalogo: el presupuesto se elaboro sin "
        "ellos y el informe de auditoria los declara."
    )
    eleccion: tuple[ItemComputo, str] | None = None
    for indice, item in enumerate(resultado.pendientes):
        st.markdown(f"**{item.origen_id}** · {item.codigo_partida} · {item.descripcion}")
        propuesta = propuestas[indice] if indice < len(propuestas) else None
        if propuesta is None:
            continue
        if propuesta.falla is not None:
            st.caption(propuesta.falla)
        for similar in propuesta.similares:
            st.markdown(f"- {similar.codigo} · {similar.descripcion} ({similar.puntaje:.2f})")
        if propuesta.similares:
            elegido = st.selectbox(
                "Propuesta para " + propuesta.item.origen_id,
                [similar.codigo for similar in propuesta.similares],
                key=f"{prefijo}_propuesta_{indice}",
            )
            if st.button("Aplicar y volver a elaborar", key=f"{prefijo}_aplicar_{indice}"):
                eleccion = (propuesta.item, elegido)
    return eleccion
