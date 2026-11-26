import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Sin `globals`, Testing Library no limpia solo el DOM entre pruebas.
afterEach(() => {
  cleanup();
});

// jsdom no trae ResizeObserver ni matchMedia, que usan Carbon (pestanas) y el visor.
class ResizeObserverFalso {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (!("ResizeObserver" in globalThis)) {
  Object.defineProperty(globalThis, "ResizeObserver", { value: ResizeObserverFalso, configurable: true });
}
if (!window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: (consulta: string) => ({
      matches: false,
      media: consulta,
      onchange: null,
      addEventListener() {},
      removeEventListener() {},
      addListener() {},
      removeListener() {},
      dispatchEvent: () => false,
    }),
  });
}

// Respaldo solo para pruebas: jsdom no implementa showModal; el navegador real sí.
if (typeof HTMLDialogElement !== "undefined" && !HTMLDialogElement.prototype.showModal) {
  const ENFOCABLES =
    'a[href], area[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"]):not([disabled])';
  const focoPrevio = new WeakMap<HTMLDialogElement, Element | null>();

  const esVisible = (el: HTMLElement, raiz: HTMLElement): boolean => {
    for (let nodo: HTMLElement | null = el; nodo && nodo !== raiz; nodo = nodo.parentElement) {
      if (nodo.hasAttribute("hidden") || getComputedStyle(nodo).display === "none") return false;
    }
    return true;
  };

  const primerVisible = (raiz: HTMLElement, selector: string): HTMLElement | undefined => {
    for (const el of raiz.querySelectorAll<HTMLElement>(selector)) {
      if (esVisible(el, raiz)) return el;
    }
    return undefined;
  };

  if (!("returnValue" in HTMLDialogElement.prototype)) {
    const valoresDeRetorno = new WeakMap<HTMLDialogElement, string>();
    Object.defineProperty(HTMLDialogElement.prototype, "returnValue", {
      configurable: true,
      get(this: HTMLDialogElement): string {
        return valoresDeRetorno.get(this) ?? "";
      },
      set(this: HTMLDialogElement, valor: string) {
        valoresDeRetorno.set(this, String(valor));
      },
    });
  }

  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    if (!this.open) {
      focoPrevio.set(this, document.activeElement);
      this.open = true;
    }
    const objetivo = primerVisible(this, "[autofocus]:not([disabled])") ?? primerVisible(this, ENFOCABLES);
    objetivo?.focus();
  };

  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement, valor?: string) {
    if (!this.open) return;
    this.open = false;
    if (valor !== undefined) this.returnValue = valor;
    this.dispatchEvent(new Event("close", { bubbles: false }));
    const anterior = focoPrevio.get(this);
    focoPrevio.delete(this);
    if (anterior instanceof HTMLElement && anterior.isConnected) {
      anterior.focus();
    }
  };

  document.addEventListener(
    "keydown",
    (evento) => {
      if (evento.key !== "Escape") return;
      const dialogo = evento.target instanceof Element ? evento.target.closest("dialog[open]") : null;
      if (!(dialogo instanceof HTMLDialogElement)) return;
      const cancelar = new Event("cancel", { bubbles: false, cancelable: true });
      if (dialogo.dispatchEvent(cancelar)) {
        dialogo.close();
      }
    },
    true,
  );
}
