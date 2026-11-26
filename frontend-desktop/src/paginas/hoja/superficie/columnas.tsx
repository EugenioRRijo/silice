import type { ColumnaDeGrilla } from "../../../comun/Grilla";
import { Severidad } from "../../../comun/Severidad";
import { unidadEscrita } from "../../../comun/unidades";
import { cifrasEnTextoEsVe, formatoEsVe } from "../../../indicadores/formatoEsVe";
import { estadoLlano } from "../estadoLlano";
import type { FilaDeLaGrilla } from "./logica";

// Columnas de la grilla del Presupuesto en solo lectura (lote B1-4, ficha-b1 §1.6 y §3.2):
// las cifras llegan del servidor y se presentan en es-VE sin title ni recalcular montos;
// las partidas sin precio dicen «Pendiente» en texto; la gravedad siempre va con su palabra junto al ícono.

function textoDeProblema(fila: FilaDeLaGrilla): string {
  if (fila.problema === null) return "Sin problemas";
  return estadoLlano(cifrasEnTextoEsVe(fila.problema.texto), fila.problema.severidad);
}

/** Construye las siete columnas de la grilla de partidas en solo lectura. */
export function columnasDePresupuesto(): readonly ColumnaDeGrilla<FilaDeLaGrilla>[] {
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
      valor: (f) => f.cantidad,
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
      valor: (f) => {
        if (f.problema === null) return "Sin problemas";
        const detalle = textoDeProblema(f);
        return detalle === f.problema.palabra ? f.problema.palabra : `${f.problema.palabra}: ${detalle}`;
      },
      render: (f) => {
        if (f.problema === null) {
          return <span className="silice-superficie__sin-problemas">Sin problemas</span>;
        }
        return (
          <span className="silice-superficie__problema">
            <Severidad valor={f.problema.severidad} />
            <span className="silice-superficie__problema-texto">{textoDeProblema(f)}</span>
          </span>
        );
      },
    },
  ];
}
