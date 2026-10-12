"""Graficos del tablero en Altair, sin Streamlit ni pandas (PLAN_SILICE_UI, tarea 3).

Cada funcion recibe las filas de `ui.tablero` (dicts) y devuelve un grafico de Altair con los
datos en linea (`alt.Data(values=...)`), sin DataFrame. La pantalla los pinta con
`st.altair_chart`. Los tooltips de Vega-Lite son texto plano: las descripciones ajenas van ahi,
nunca en un titulo (RU-9).
"""

from __future__ import annotations

from collections.abc import Sequence

import altair as alt

from ui.estilo import COLOR_PRIMARIO, COLOR_TENUE, COLORES_RUBRO, COLORES_SERIE

Filas = Sequence[dict[str, object]]


def anillo(fraccion: float, texto: str, *, color: str = COLOR_PRIMARIO) -> alt.LayerChart:
    """Un anillo de progreso con `texto` al centro; la fraccion se recorta a [0, 1]."""
    parte = min(max(fraccion, 0.0), 1.0)
    arcos = (
        alt.Chart(
            alt.Data(
                values=[
                    {"parte": "a", "valor": parte},
                    {"parte": "b", "valor": 1 - parte},
                ]
            )
        )
        .mark_arc(innerRadius=44, outerRadius=60)
        .encode(
            theta=alt.Theta("valor:Q", stack=True),
            color=alt.Color(
                "parte:N",
                scale=alt.Scale(domain=["a", "b"], range=[color, COLOR_TENUE]),
                legend=None,
            ),
            order=alt.Order("parte:N"),
        )
    )
    centro = (
        alt.Chart(alt.Data(values=[{"t": texto}]))
        .mark_text(fontSize=18, fontWeight="bold")
        .encode(text="t:N")
    )
    return alt.layer(arcos, centro).properties(width=140, height=140)


def desglose(filas: Filas) -> alt.Chart:
    """Anillo del costo por rubro."""
    return (
        alt.Chart(alt.Data(values=list(filas)))
        .mark_arc(innerRadius=60)
        .encode(
            theta=alt.Theta("monto:Q"),
            color=alt.Color(
                "Rubro:N",
                scale=alt.Scale(domain=list(COLORES_RUBRO), range=list(COLORES_RUBRO.values())),
                legend=alt.Legend(orient="bottom", title=None),
            ),
            tooltip=["Rubro:N", "Monto:N", "Peso:N"],
        )
        .properties(height=280)
    )


def curvas(filas: Filas) -> alt.Chart:
    """Lineas acumuladas por periodo: Plan, o PV, EV y AC."""
    presentes = [s for s in COLORES_SERIE if any(f["Serie"] == s for f in filas)]
    return (
        alt.Chart(alt.Data(values=list(filas)))
        .mark_line(point=True)
        .encode(
            x=alt.X("Orden:O", title="Periodo"),
            y=alt.Y("Acumulado:Q", title="Acumulado"),
            color=alt.Color(
                "Serie:N",
                scale=alt.Scale(domain=presentes, range=[COLORES_SERIE[s] for s in presentes]),
                legend=alt.Legend(orient="top", title=None),
            ),
            tooltip=["Periodo:N", "Serie:N", alt.Tooltip("Acumulado:Q", format=",.2f")],
        )
        .properties(height=280)
    )


def pareto(filas: Filas) -> alt.Chart:
    """Barras horizontales de las partidas de mayor total."""
    return (
        alt.Chart(alt.Data(values=list(filas)))
        .mark_bar(color=COLOR_PRIMARIO)
        .encode(
            y=alt.Y("Partida:N", sort="-x", title=None),
            x=alt.X("monto:Q", title="Total"),
            tooltip=["Partida:N", "Descripcion:N", "Total:N", "Peso:N", "Acumulado:N"],
        )
        .properties(height=300)
    )


def versiones(filas: Filas) -> alt.Chart:
    """Total de cada version, la vigente resaltada."""
    return (
        alt.Chart(alt.Data(values=list(filas)))
        .mark_bar()
        .encode(
            x=alt.X("Version:N", sort=None, title=None),
            y=alt.Y("total:Q", title="Total"),
            color=alt.condition(
                alt.datum.Vigente == "si", alt.value(COLOR_PRIMARIO), alt.value(COLOR_TENUE)
            ),
            tooltip=["Version:N", "Fecha:N", "Motivo:N", "Total:N"],
        )
        .properties(height=240)
    )
