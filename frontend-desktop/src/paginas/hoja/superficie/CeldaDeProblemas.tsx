import type { JSX } from "react";
import { Severidad } from "../../../comun/Severidad";
import { cifrasEnTextoEsVe, formatoEsVe } from "../../../indicadores/formatoEsVe";
import { estadoLlano } from "../estadoLlano";
import type { ResumenDeProblemaEnFila } from "./logica";
import "./problemas.scss";

// Celda de la columna «Problemas» en la grilla del Presupuesto (lote B1-7, ficha-b1 §1.6 y §3.2).
// Presenta ícono, severidad en palabra y texto corto en español llano (sin atributo title ni controles emergentes no
// pedidos); si la fila tiene más de un problema, indica el conteo total.

export interface PropiedadesDeCeldaDeProblemas {
  readonly problema: ResumenDeProblemaEnFila | null;
}

function detalleDeProblema(problema: ResumenDeProblemaEnFila): string {
  return estadoLlano(cifrasEnTextoEsVe(problema.texto), problema.severidad);
}

/** Texto accesible y de lectura para una celda de la columna Problemas. */
export function textoDeCeldaDeProblemas(problema: ResumenDeProblemaEnFila | null): string {
  if (problema === null) return "Sin problemas";
  const detalle = detalleDeProblema(problema);
  const base = detalle === "" || detalle === problema.palabra ? problema.palabra : `${problema.palabra}: ${detalle}`;
  return problema.total > 1 ? `${base} (${formatoEsVe(String(problema.total))} problemas)` : base;
}

/** Celda de la columna Problemas: ícono, palabra de severidad, texto corto y conteo cuando hay varios. */
export function CeldaDeProblemas({ problema }: PropiedadesDeCeldaDeProblemas): JSX.Element {
  if (problema === null) {
    return <span className="silice-problemas-celda__sin-problemas">Sin problemas</span>;
  }

  const detalle = detalleDeProblema(problema);
  const mostrarDetalle = detalle !== "" && detalle !== problema.palabra;

  return (
    <span className="silice-problemas-celda">
      <Severidad valor={problema.severidad} />
      {mostrarDetalle && (
        <>
          {" "}
          <span className="silice-problemas-celda__texto">{detalle}</span>
        </>
      )}
      {problema.total > 1 && (
        <>
          {" "}
          <span className="silice-problemas-celda__total">{`(${formatoEsVe(String(problema.total))} problemas)`}</span>
        </>
      )}
    </span>
  );
}
