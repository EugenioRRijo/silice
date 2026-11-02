// ESBOZO DEL ROJO (Tarea 11 de F4): la firma del diálogo «Subir plano o cómputo», sin implementar.
import type { ReactNode } from "react";
import type { Resumen } from "../hoja/logica";

export interface PropsDeSubirArchivo {
  id: string;
  rev: number;
  anfitrion: HTMLElement;
  alCerrar: () => void;
  alAusente: () => void;
  alAceptar: (resumen: Resumen) => void;
  alRecargar: () => Promise<void>;
  alReabrir: () => void;
  alExpirar: () => void;
  cuerpoDelComputo?: (archivo: File) => ReactNode;
}

export function SubirArchivo(props: PropsDeSubirArchivo): ReactNode {
  void props;
  return null;
}
