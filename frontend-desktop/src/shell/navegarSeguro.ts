import { useCallback } from "react";
import { useLocation, useNavigate } from "react-router";
import { confirmarSalida } from "./salida";
import { formulariosSucios } from "./sucio";

// Navegar desde una pantalla sin perder trabajo (diseno de modulos §12.5): si la pantalla de destino es otra y hay
// formularios sucios, primero se pregunta. Volver a la misma pantalla no pregunta. Atras/adelante del navegador no pasan
// por aqui (declarado en el diseno). En el marco (barra lateral, migas, buscador) pregunta marco/Marco. Lo que sobrevive
// al ir a `to` no cuenta (el borrador de la Hoja entre las secciones de su obra, Tarea 3 del plan F4).
export function useNavegarSeguro(): (to: string) => Promise<boolean> {
  const navegar = useNavigate();
  const { pathname } = useLocation();
  return useCallback(
    async (to: string) => {
      if (to !== pathname && formulariosSucios(to).length > 0 && !(await confirmarSalida("salir", [], null, to))) return false;
      navegar(to);
      return true;
    },
    [navegar, pathname],
  );
}
