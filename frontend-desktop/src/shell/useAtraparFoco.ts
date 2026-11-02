import { useCallback } from "react";
import type { KeyboardEvent, RefObject } from "react";

const ENFOCABLES =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]';

// Lo enfocable que de verdad se ve: una parte puede estar oculta por CSS (p. ej. las areas del sidebar cuando la barra
// si cabe) y el navegador no la enfocaria.
function enfocables(caja: HTMLElement): HTMLElement[] {
  return Array.from(caja.querySelectorAll<HTMLElement>(ENFOCABLES)).filter((el) => {
    for (let nodo: HTMLElement | null = el; nodo && nodo !== caja; nodo = nodo.parentElement) {
      if (getComputedStyle(nodo).display === "none") return false;
    }
    return true;
  });
}

// Primer elemento enfocable y visible de la caja (para llevar el foco adentro al abrir).
export function primerEnfocable(caja: HTMLElement): HTMLElement | undefined {
  return enfocables(caja)[0];
}

// Foco atrapado de un dialogo modal (el sidebar en capa, «Cambios sin guardar»): devuelve el manejador de teclado de la
// caja. Tab desde el ultimo vuelve al primero y Mayus+Tab desde el primero (o desde la propia caja) va al ultimo; en
// medio, el orden natural. Lo demas (Esc, foco inicial, devolver el foco) lo decide cada dialogo.
export function useAtraparFoco(caja: RefObject<HTMLElement | null>): (e: KeyboardEvent<HTMLElement>) => void {
  return useCallback(
    (e: KeyboardEvent<HTMLElement>) => {
      if (e.key !== "Tab" || !caja.current) return;
      const lista = enfocables(caja.current);
      const primero = lista[0];
      const ultimo = lista[lista.length - 1];
      if (!primero || !ultimo) return;
      const activo = document.activeElement;
      if (e.shiftKey && (activo === primero || activo === caja.current)) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && activo === ultimo) {
        e.preventDefault();
        primero.focus();
      }
    },
    [caja],
  );
}
