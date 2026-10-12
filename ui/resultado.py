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
from pandas import DataFrame

from core.verification.informe import DECIMALES_PRESENTACION, SIN_HALLAZGOS
from core.verification.texto import formatear_decimal
from ui.texto_seguro import texto_seguro

if TYPE_CHECKING:
    from core.budget import ResultadoElaboracion
    from core.contracts import ItemComputo
    from core.verification.informe import InformeAuditoria
    from ui.elaboracion import PendienteConPropuestas

MIME_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _monto(valor) -> str:
    return "" if valor is None else formatear_decimal(valor, DECIMALES_PRESENTACION)


def mostrar_informe(informe: InformeAuditoria) -> None:
    """El informe de auditoria sin interpretar su texto como Markdown (SEG-3, RV-14).

    `InformeAuditoria.a_markdown` mete la descripcion de cada hallazgo en una tabla Markdown, y
    esa descripcion puede traer el nombre de un insumo importado (R11, R12): `![x](http://...)`
    seria una imagen y `[x](http://...)` un enlace. Aqui lo ajeno va en celdas de `st.dataframe`
    (texto plano) o, si va en Markdown, por `texto_seguro`. Lo que el sistema escribe (veredicto,
    conteos) es texto propio.
    """
    veredicto = "CUMPLE" if informe.cumple else "NO CUMPLE"
    st.markdown(
        f"**Presupuesto {texto_seguro(informe.codigo_presupuesto)}** · "
        f"Hallazgos: {len(informe.hallazgos)} · Resultado: {veredicto}"
    )
    if informe.reglas_evaluadas:
        st.caption("Reglas evaluadas")
        st.dataframe(
            DataFrame(
                [
                    {"Regla": codigo, "Nombre": nombre, "Hallazgos": cuenta}
                    for codigo, nombre, cuenta in informe.cuenta_por_regla_evaluada()
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    if not informe.hallazgos:
        st.caption(SIN_HALLAZGOS)
        return
    st.dataframe(
        DataFrame(
            [
                {
                    "#": numero,
                    "Regla": h.regla,
                    "Severidad": h.severidad.name,
                    "Partida": informe.partida_de(h) or "-",
                    "Descripcion": h.descripcion,
                    "Impacto": _monto(h.impacto),
                    "Observado": _monto(h.valor_observado),
                    "Esperado": _monto(h.valor_esperado),
                    "Origen": "; ".join(h.origen_ids),
                }
                for numero, h in enumerate(informe.hallazgos, start=1)
            ]
        ),
        hide_index=True,
        width="stretch",
    )


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
    mostrar_informe(resultado.informe)
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
