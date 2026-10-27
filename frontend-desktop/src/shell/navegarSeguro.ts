import { useCallback } from "react";
import { useLocation, useNavigate } from "react-router";
import { confirmarSalida } from "./salida";
import { formulariosSucios } from "./sucio";

// Navegar desde una pantalla sin perder trabajo (diseno de modulos §12.5): si la pantalla de destino es otra y hay
// formularios sucios, primero se pregunta. Volver a la misma pantalla no pregunta. Atras/adelante del navegador no pasan
// por aqui (declarado en el diseno). En el marco (barra lateral, migas, buscador) pregunta marco/Marco.
export function useNavegarSeguro(): (to: string) => Promise<boolean> {
  const navegar = useNavigate();
  const { pathname } = useLocation();
  return useCallback(
    async (to: string) => {
      if (to !== pathname && formulariosSucios().length > 0 && !(await confirmarSalida("salir"))) return false;
      navegar(to);
      return true;
    },
    [navegar, pathname],
  );
}
