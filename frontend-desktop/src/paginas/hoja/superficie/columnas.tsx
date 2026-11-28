import type { ColumnaDeGrilla } from "../../../comun/Grilla";
import { unidadEscrita } from "../../../comun/unidades";
import { formatoEsVe } from "../../../indicadores/formatoEsVe";
import { CeldaDeCantidad } from "./CeldaDeCantidad";
import type { CantidadesDeLaSuperficie } from "./useCantidadesDeLaSuperficie";
import { CeldaDeProblemas, textoDeCeldaDeProblemas } from "./CeldaDeProblemas";
import type { FilaDeLaGrilla } from "./logica";

// Columnas de la grilla del Presupuesto (lotes B1-4 y B1-10, ficha-b1 §1.6 y §3.2): las cifras llegan del servidor y se
// presentan en es-VE sin title ni recalcular montos; las partidas sin precio dicen «Pendiente» en texto; la gravedad siempre
// va con su palabra junto al ícono (`CeldaDeProblemas`). Con las cantidades de la superficie (`useCantidadesDeLaSuperficie`)
// la columna Cantidad es la celda editable (`CeldaDeCantidad`); sin ellas es solo texto (solo lectura).

/** Construye las siete columnas de la grilla de partidas. */
export function columnasDePresupuesto(
  cantidades?: Pick<CantidadesDeLaSuperficie, "celda">,
): readonly ColumnaDeGrilla<FilaDeLaGrilla>[] {
  return [
    {
      clave: "partida",
      titulo: "Partida",
      valor: (f) => f.partida,
    },
    {
      clave: "descripcion",
      titulo: "Descripción",
      valor: (f) => f.descripcion,
    },
    {
      clave: "unidad",
      titulo: "Unidad",
      valor: (f) => unidadEscrita(f.unidad),
    },
    {
      clave: "cantidad",
      titulo: "Cantidad",
      numerica: true,
      valor: (f) => (cantidades === undefined ? f.cantidad : cantidades.celda(f.fila).valor),
      ...(cantidades === undefined ? {} : { render: (f: FilaDeLaGrilla) => <CeldaDeCantidad {...cantidades.celda(f.fila)} /> }),
    },
    {
      clave: "pu",
      titulo: "Precio unitario",
      numerica: true,
      valor: (f) => (f.fila.pu === null ? "Pendiente" : formatoEsVe(f.puTexto)),
    },
    {
      clave: "total",
      titulo: "Total",
      numerica: true,
      valor: (f) => (f.fila.total === null ? "Pendiente" : formatoEsVe(f.totalTexto)),
    },
    {
      clave: "problemas",
      titulo: "Problemas",
      valor: (f) => textoDeCeldaDeProblemas(f.problema),
      render: (f) => <CeldaDeProblemas problema={f.problema} />,
    },
  ];
}
