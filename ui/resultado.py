"""Fragmento de Streamlit que muestra un presupuesto elaborado (INV-043, fase C3).

Lo comparten la pagina de componer y la de elaborar: total, resumen por severidad, descarga del
libro de Excel y el informe de auditoria. El informe se muestra tenga hallazgos o no: el informe de
auditoria se genera siempre, sin que el usuario lo pida (principio 7 de CLAUDE.md §2), y eso es
principio del proyecto, no preferencia de pantalla.

Solo pinta lo que recibe: no abre la base (sin `sqlalchemy.orm`) ni calcula (sin `core.costing`).
No conoce ninguna clave de `st.session_state` de ninguna pagina; `prefijo` es el de las claves de
widget de la pagina que lo llama. Lo vigila
`tests/unit/test_arquitectura.py::test_ui_respeta_sus_importaciones_prohibidas`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal

if TYPE_CHECKING:
    from core.budget import ResultadoElaboracion

MIME_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def mostrar_elaboracion(
    resultado: ResultadoElaboracion, libro: bytes, nombre_libro: str, *, prefijo: str
) -> None:
    """Totales, resumen por severidad, la descarga y el informe de auditoria (siempre)."""
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

    st.subheader("Informe de auditoria")
    st.markdown(resultado.informe.a_markdown())
