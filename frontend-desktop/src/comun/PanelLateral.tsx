import type { JSX, ReactNode } from "react";

// Esbozo para el rojo de la Tarea 7 del plan F4: la firma de la Tarea 6, sin pintar nada todavía.
export interface PropsDelPanelLateral {
  titulo: string;
  abierto: boolean;
  alCerrar: () => void;
  ancho?: "normal" | "ancho";
  children: ReactNode;
}

export function PanelLateral(p: PropsDelPanelLateral): JSX.Element | null {
  return p.abierto ? null : null;
}
