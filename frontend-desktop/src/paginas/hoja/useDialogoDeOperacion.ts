import { useCallback, useContext, useEffect, useRef, useState } from "react";
import { ContextoDeDialogos } from "./ContextoDeDialogos";

// Abrir y cerrar el diálogo de una operación desde su botón. Mientras está abierto la página queda `inert`; al cancelarlo el
// foco vuelve al botón, pero solo cuando el `inert` ya se quitó (en un navegador real no se puede enfocar dentro de un
// subárbol inert): el efecto corre tras cada commit y espera a que no quede ningún diálogo abierto. Al terminar bien (se abre
// la versión nueva) no se devuelve el foco: lo lleva la página al selector de versión.
export function useDialogoDeOperacion() {
  const { anfitrion, abiertos, registrar } = useContext(ContextoDeDialogos);
  const [abierto, setAbierto] = useState(false);
  const boton = useRef<HTMLButtonElement | null>(null);
  // Ancla de función (no un objeto ref): lo que devuelve el hook no contiene nada que se lea al pintar.
  const anclaDelBoton = useCallback((el: HTMLButtonElement | null) => {
    boton.current = el;
  }, []);
  const devolver = useRef(false);

  useEffect(() => {
    if (!abierto) return;
    registrar(1);
    return () => registrar(-1);
  }, [abierto, registrar]);

  useEffect(() => {
    if (abierto || !devolver.current || abiertos > 0) return;
    devolver.current = false;
    boton.current?.focus();
  });

  const abrir = useCallback(() => setAbierto(true), []);
  const cerrar = useCallback((devolverElFoco: boolean) => {
    devolver.current = devolverElFoco;
    setAbierto(false);
  }, []);
  return { abierto: abierto && anfitrion !== null, anfitrion, abrir, cerrar, anclaDelBoton };
}
