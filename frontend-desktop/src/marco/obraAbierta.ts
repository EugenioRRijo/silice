import { createContext, useContext } from "react";
import type { FichaDeLaObra } from "./useFichaDeLaObra";

// La obra de la ruta, tal como la comparten las secciones: Resumen, Presupuesto, Versiones y Archivos necesitan su
// carpeta, su número y su ficha, y pedirlas cada una por su lado repetiría la lectura (Tarea 1 del plan F4). La provee
// EspacioDeObra; fuera de una obra no hay valor.
export interface ObraAbierta {
  // null = la carpeta de la empresa.
  carpeta: string | null;
  obraId: number;
  ficha: FichaDeLaObra;
  // Vuelve a leer la ficha (por ejemplo, tras guardar una versión).
  recargarFicha: () => void;
}

export const ContextoDeLaObra = createContext<ObraAbierta | null>(null);

export function useObraAbierta(): ObraAbierta {
  const obra = useContext(ContextoDeLaObra);
  if (obra === null) throw new Error("useObraAbierta se usó fuera de una obra abierta: solo vale dentro de EspacioDeObra.");
  return obra;
}
