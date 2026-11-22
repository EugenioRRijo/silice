import { createContext, useContext } from "react";

export interface LayoutDelMarco {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const CLAVE_BARRA_COLAPSADA = "silice_sidebar_collapsed";

export const ContextoLayoutDelMarco = createContext<LayoutDelMarco>({
  sidebarCollapsed: false,
  toggleSidebar: () => undefined,
});

export function useWorkspaceLayout(): LayoutDelMarco {
  return useContext(ContextoLayoutDelMarco);
}

export function leerBarraColapsada(): boolean {
  try {
    return typeof window !== "undefined" && window.localStorage.getItem(CLAVE_BARRA_COLAPSADA) === "1";
  } catch {
    return false;
  }
}

export function guardarBarraColapsada(colapsada: boolean): void {
  try {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(CLAVE_BARRA_COLAPSADA, colapsada ? "1" : "0");
    }
  } catch {
    // Sin acceso a almacenamiento en marcos restringidos.
  }
}

