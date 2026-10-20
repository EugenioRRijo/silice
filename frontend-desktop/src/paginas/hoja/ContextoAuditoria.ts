import { createContext } from "react";

// Lo que una fila pide al ir a «Auditoría»: los orígenes con que se buscan sus hallazgos y cómo se nombra la fila.
export interface FiltroDeAuditoria {
  claves: string[];
  rotulo: string;
}

// La página ofrece esta función a los Estados de fila (3b-F6b). Sin ella (una tabla fuera de la página) no hay enlace.
export const ContextoAuditoria = createContext<((filtro: FiltroDeAuditoria) => void) | null>(null);
