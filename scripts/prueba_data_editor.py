"""Prueba corta de `st.data_editor` con 500 puntos (spec §11.3, tarea 0.5). DESCARTABLE.

Se ejecuta en el navegador siguiendo scripts/medir_data_editor.md:

    uv run python -m streamlit run scripts/prueba_data_editor.py

Lo que la prueba fija (spec §11.3):

- datos: 500 puntos de `scripts.generar_hoja_prueba`;
- cálculo sustituto: cada edición recibida vuelve a llamar a `core.budget.elaborar`;
- la columna Estado vive en un componente aparte (`st.dataframe`), no en el editor, y el editor
  muestra el índice (`fila`) para comprobar la alineación tras ordenar;
- las ediciones se guardan en `st.session_state["borrador_prueba"]`, clave que NO es de widget;
- la pestaña activa es un `st.segmented_control`;
- medición: la propia aplicación anota en `scripts/_salida_prueba_editor.log` la marca de tiempo
  de cada edición recibida (con los valores completos de las celdas, altas y bajas) y de cada Estado
  pintado (servidor; `desde_recepcion_s` es una COTA INFERIOR de lo que ve el usuario, pues no
  incluye red ni pintado del navegador; ese tramo se mide con la grabación de pantalla).
"""

from __future__ import annotations

import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import streamlit as st

from core.budget import elaborar
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from scripts.generar_hoja_prueba import PARAMETROS_PRUEBA, composiciones_de_prueba, generar_items

BITACORA = Path(__file__).with_name("_salida_prueba_editor.log")
N_PUNTOS = 500
CLAVE_BORRADOR = "borrador_prueba"  # NO es la clave de ningún widget
CLAVE_BASE = "base_editor_prueba"
CLAVE_VERSION = "version_editor_prueba"
CLAVE_PESTANA_PREVIA = "pestana_previa_prueba"
PESTANAS = ("Hoja", "Resumen")
COLUMNAS = ("partida", "descripcion", "unidad", "cantidad")
FECHA = date(2026, 10, 4)


def registrar(evento: str, detalle: str = "") -> float:
    """Anota `hora ISO<TAB>marca monotónica<TAB>evento<TAB>detalle` y devuelve la marca."""
    marca = time.perf_counter()
    hora = datetime.now().isoformat(timespec="milliseconds")
    with BITACORA.open("a", encoding="utf-8") as archivo:
        archivo.write(f"{hora}\t{marca:.6f}\t{evento}\t{detalle}\n")
    return marca


def tabla_inicial(n: int = N_PUNTOS) -> pd.DataFrame:
    filas = [
        {
            "partida": i.codigo_partida,
            "descripcion": i.descripcion,
            "unidad": i.unidad,
            "cantidad": float(i.cantidad),
        }
        for i in generar_items(n)
    ]
    return pd.DataFrame(filas, columns=list(COLUMNAS))


def diferencias(antes: pd.DataFrame, despues: pd.DataFrame) -> dict[str, object]:
    """Altas, bajas y celdas cambiadas entre dos versiones del borrador (por índice de fila).

    Las altas y bajas llevan la fila completa y las celdas, el valor nuevo: el registro guarda
    valores, no conteos, para compararlos con la lista en papel.
    """
    altas = {
        fila: despues.loc[fila].to_dict() for fila in sorted(set(despues.index) - set(antes.index))
    }
    bajas = {
        fila: antes.loc[fila].to_dict() for fila in sorted(set(antes.index) - set(despues.index))
    }
    celdas = []
    for fila in despues.index:
        if fila not in antes.index:
            continue
        for col in COLUMNAS:
            a, d = antes.at[fila, col], despues.at[fila, col]
            if not (pd.isna(a) and pd.isna(d)) and a != d:
                celdas.append(f"{fila}.{col}:{a!r}->{d!r}")
    return {"altas": altas, "bajas": bajas, "celdas": celdas}


def estados(tabla: pd.DataFrame, composiciones) -> tuple[pd.DataFrame, list[ItemComputo]]:
    """Columna Estado por fila (en una tabla aparte) y los ítems valorables."""
    estado, items = [], []
    for fila, datos in tabla.iterrows():
        codigo = datos["partida"]
        try:
            cantidad = Decimal(str(datos["cantidad"]))
        except (InvalidOperation, ValueError):
            cantidad = Decimal("-1")
        if pd.isna(datos["cantidad"]) or cantidad < 0:
            estado.append("cantidad invalida")
        elif codigo not in composiciones:
            estado.append("sin partida")
        else:
            apu = composiciones[codigo]
            items.append(
                ItemComputo(
                    codigo_partida=codigo,
                    descripcion=str(datos["descripcion"] or apu.descripcion),
                    unidad=apu.unidad,
                    cantidad=cantidad,
                    origen_id=f"gen-{fila}",
                    origen_tipo=OrigenTipo.MANUAL,
                    dominio=Dominio.CIVIL,
                )
            )
            estado.append("ok")
    return pd.DataFrame({"fila": list(tabla.index), "Estado": estado}), items


def main() -> None:
    st.set_page_config(page_title="Prueba st.data_editor", layout="wide")
    composiciones = composiciones_de_prueba()
    if CLAVE_BORRADOR not in st.session_state:
        st.session_state[CLAVE_BORRADOR] = tabla_inicial()
        st.session_state[CLAVE_BASE] = st.session_state[CLAVE_BORRADOR].copy()
        st.session_state[CLAVE_VERSION] = 0
        st.session_state["ediciones_total"] = 0
        registrar("ARRANQUE", f"{N_PUNTOS} puntos")

    pestana = st.segmented_control("Pestana", PESTANAS, default="Hoja", key="pestana_prueba")
    pestana = pestana or "Hoja"
    if pestana == "Hoja" and st.session_state.get(CLAVE_PESTANA_PREVIA) != "Hoja":
        # Al volver a la hoja el editor parte del borrador (clave de editor nueva).
        st.session_state[CLAVE_BASE] = st.session_state[CLAVE_BORRADOR].copy()
        st.session_state[CLAVE_VERSION] += 1
    st.session_state[CLAVE_PESTANA_PREVIA] = pestana

    borrador: pd.DataFrame = st.session_state[CLAVE_BORRADOR]
    if pestana == "Hoja":
        izquierda, derecha = st.columns([4, 1])
        with izquierda:
            editada = st.data_editor(
                st.session_state[CLAVE_BASE],
                num_rows="dynamic",
                hide_index=False,  # muestra el índice (columna `fila`) para contrastar con Estado
                key=f"editor_prueba_{st.session_state[CLAVE_VERSION]}",
                height=520,
                column_config={
                    "partida": st.column_config.SelectboxColumn(options=sorted(composiciones))
                },
            )
        recibida = registrar("RUN", f"filas={len(editada)}")
        cambios = diferencias(borrador, editada)
        if cambios["altas"] or cambios["bajas"] or cambios["celdas"]:
            st.session_state["ediciones_total"] += 1
            registrar(
                "EDICION_RECIBIDA",
                f"n={st.session_state['ediciones_total']};altas={cambios['altas']};"
                f"bajas={cambios['bajas']};celdas={cambios['celdas']}",
            )
            st.session_state[CLAVE_BORRADOR] = editada.copy()
            borrador = st.session_state[CLAVE_BORRADOR]
        tabla_estado, items = estados(borrador, composiciones)
        inicio = time.perf_counter()
        resultado = elaborar(items, composiciones, PARAMETROS_PRUEBA, codigo="PRUEBA", fecha=FECHA)
        calculo = time.perf_counter() - inicio
        with derecha:
            st.dataframe(tabla_estado, height=520, hide_index=True)
        registrar(
            "ESTADO_PINTADO",
            f"filas={len(tabla_estado)};total={resultado.presupuesto.total};"
            f"elaborar_s={calculo:.3f};desde_recepcion_s={time.perf_counter() - recibida:.3f}",
        )
        st.caption(
            f"Ediciones recibidas: {st.session_state['ediciones_total']} | "
            f"filas: {len(borrador)} | elaborar: {calculo * 1000:.0f} ms | "
            f"bitacora: {BITACORA.name}"
        )
    else:
        _, items = estados(borrador, composiciones)
        resultado = elaborar(items, composiciones, PARAMETROS_PRUEBA, codigo="PRUEBA", fecha=FECHA)
        st.metric("Total del presupuesto (USD)", f"{resultado.presupuesto.total:,.2f}")
        st.write(
            f"Filas: {len(borrador)} | ediciones recibidas: {st.session_state['ediciones_total']}"
        )


if __name__ == "__main__":
    main()
