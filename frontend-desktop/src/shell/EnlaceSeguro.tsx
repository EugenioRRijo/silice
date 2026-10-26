import { useCallback } from "react";
import type { JSX, MouseEvent } from "react";
import { NavLink, useLocation, useNavigate, type NavLinkProps } from "react-router";
import { confirmarSalida } from "./salida";
import { formulariosSucios } from "./sucio";

// Navegar por un control de Silice sin perder trabajo (diseno de modulos §12.5): si la pantalla de destino es otra y hay
// formularios sucios, primero se pregunta. Volver a la misma pantalla no pregunta. Atras/adelante del navegador no pasan
// por aqui (declarado en el diseno).
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

// El manejador de clic de un enlace seguro, para quien no puede usar `EnlaceSeguro` tal cual (el renglon de cada modulo
// del sidebar marca `aria-current` aunque su ruta no sea la actual). Sin nada que perder deja que el enlace navegue
// solo; con algo, detiene la navegacion, pregunta y navega si la persona acepta. Un clic con Ctrl, Mayus, Cmd o Alt (u
// otro boton) abre otra pestana: no se pierde nada y no se pregunta.
export function useClicSeguro(to: string, alNavegar?: () => void): (e: MouseEvent<HTMLAnchorElement>) => void {
  const navegarSeguro = useNavegarSeguro();
  const { pathname } = useLocation();
  return (e: MouseEvent<HTMLAnchorElement>) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (to === pathname || formulariosSucios().length === 0) {
      alNavegar?.();
      return;
    }
    e.preventDefault();
    void navegarSeguro(to).then((navego) => {
      if (navego) alNavegar?.();
    });
  };
}

type Props = Omit<NavLinkProps, "to"> & {
  to: string;
  // Despues de navegar (p. ej. cerrar el panel o el sidebar); no se llama si la persona elige «Quedarme».
  alNavegar?: () => void;
};

// Un `NavLink` (marca `aria-current="page"` en su pantalla) que pregunta antes de perder trabajo. Lo usan la barra, el
// panel de area, el sidebar y los botones de la mesa.
export function EnlaceSeguro({ to, alNavegar, onClick, ...resto }: Props): JSX.Element {
  const clicSeguro = useClicSeguro(to, alNavegar);
  return (
    <NavLink
      {...resto}
      to={to}
      onClick={(e) => {
        onClick?.(e);
        clicSeguro(e);
      }}
    />
  );
}
