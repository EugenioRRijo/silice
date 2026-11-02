import { useEffect } from "react";
import type { KeyboardEvent, RefObject } from "react";

const ENFOCABLES = 'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]';

// El comportamiento de un diálogo accesible, común a la confirmación de cambio de versión y al modal de guardar: al montarse
// lleva el foco adentro (a `inicial` si la hay, si no a la caja), se cierra con Escape en todo el documento y devuelve un
// manejador de teclado que atrapa Tab. Lo demás (el resto de la página `inert`, devolver el foco al cerrar) lo decide quien lo
// monta, porque el `inert` se quita en el commit siguiente y solo entonces se puede enfocar fuera del diálogo.
export function useDialogo(
  caja: RefObject<HTMLElement | null>,
  alCancelar: () => void,
  inicial?: () => HTMLElement | null,
): { atrapar: (e: KeyboardEvent<HTMLElement>) => void } {
  useEffect(() => {
    (inicial?.() ?? caja.current)?.focus();
    // Solo al montar: un diálogo no le quita el foco a quien escribe cuando cambia su contenido.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const alTeclear = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") alCancelar();
    };
    document.addEventListener("keydown", alTeclear);
    return () => document.removeEventListener("keydown", alTeclear);
  }, [alCancelar]);

  const atrapar = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key !== "Tab" || !caja.current) return;
    const enfocables = Array.from(caja.current.querySelectorAll<HTMLElement>(ENFOCABLES));
    const primero = enfocables[0];
    const ultimo = enfocables[enfocables.length - 1];
    if (primero === undefined || ultimo === undefined) return;
    const activo = document.activeElement;
    if (e.shiftKey && (activo === primero || activo === caja.current)) {
      e.preventDefault();
      ultimo.focus();
    } else if (!e.shiftKey && activo === ultimo) {
      e.preventDefault();
      primero.focus();
    }
  };

  return { atrapar };
}
