import type { JSX } from "react";
import { PanelLateral } from "../../../comun/PanelLateral";
import { PresupuestoPorFrentes } from "../PresupuestoPorFrentes";
import type { FilaPresupuesto, Resumen } from "../logica";

// Panel lateral no modal para «Subtotales por frente» dentro del Presupuesto nuevo (lote G3, ficha-b1 §1.6).
export interface PropiedadesDeInspectorDeFrentes {
  readonly abierto: boolean;
  readonly id: string;
  readonly rev: number;
  readonly filas: readonly FilaPresupuesto[];
  readonly moneda: string;
  readonly puedeEditar: boolean;
  readonly alAceptar: (resumen: Resumen) => void;
  readonly alAusente: () => void;
  readonly alCerrar: () => void;
}

/** Envuelve PresupuestoPorFrentes en un panel lateral no modal para la superficie del Presupuesto. */
export function InspectorDeFrentes({
  abierto,
  id,
  rev,
  filas,
  moneda,
  puedeEditar,
  alAceptar,
  alAusente,
  alCerrar,
}: PropiedadesDeInspectorDeFrentes): JSX.Element {
  return (
    <PanelLateral titulo="Subtotales por frente" abierto={abierto} alCerrar={alCerrar}>
      {abierto && (
        <PresupuestoPorFrentes
          id={id}
          rev={rev}
          filas={filas}
          moneda={moneda}
          puedeEditar={puedeEditar}
          alAceptar={alAceptar}
          alAusente={alAusente}
          enPanel
        />
      )}
    </PanelLateral>
  );
}
