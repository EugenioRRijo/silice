import type { JSX } from "react";

// Esbozo del rojo de la Tarea 9 del plan F4 (la implementación llega con el `feat`).
export interface PartidaParecida {
  codigo: string;
  descripcion: string;
  unidad: string | null;
}

interface Props {
  descripcion: string;
  alUsar: (partida: PartidaParecida) => void;
  deshabilitado?: boolean;
}

export function Parecidas(props: Props): JSX.Element | null {
  void props;
  return null;
}
