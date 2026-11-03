import type { JSX } from "react";

// Esbozo del rojo de la Tarea 9 del plan F4 (la implementación llega con el `feat`).
export interface PartidaCompuesta {
  codigo: string;
  descripcion: string;
  unidad: string;
}

interface Props {
  codigoInicial: string;
  nivelDelTitulo: 1 | 2;
  alGuardar: (partida: PartidaCompuesta) => void;
}

export function ComponerPartida(props: Props): JSX.Element | null {
  void props;
  return null;
}
