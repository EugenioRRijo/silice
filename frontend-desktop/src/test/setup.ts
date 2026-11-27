import "@testing-library/jest-dom/vitest";
import { act, cleanup } from "@testing-library/react";
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

// Respaldo solo para pruebas: jsdom no implementa `transform.baseVal` de SVG y d3 (dentro de Carbon Charts) lo lee al
// animar ejes y barras (`transform.baseVal.consolidate()`); sin esto, cada gráfico deja errores no atrapados. `null`
// es «sin transformación», lo mismo que d3 hace con un atributo vacío. El navegador real sí lo implementa.
if (typeof SVGElement !== "undefined" && !("transform" in SVGElement.prototype)) {
  Object.defineProperty(SVGElement.prototype, "transform", {
    configurable: true,
    get: () => ({ baseVal: { consolidate: () => null } }),
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

  // Modelo del navegador real (Chrome y WebView2) para lo que las pruebas del diálogo necesitan comprobar:
  // - el Esc se atiende en burbuja y solo si ningún control interno lo previno (p. ej. el menú del ComboBox);
  // - va al diálogo modal superior aunque el foco esté en `body`;
  // - con `closedby="none"` el Esc no despacha `cancel`;
  // - un segundo Esc sin activación de usuario nueva despacha un `cancel` que ya no es cancelable;
  // - `close` se despacha en una tarea aparte, no dentro de `close()`;
  // - al quitar del DOM un modal abierto el foco se pierde y un `close()` posterior no lo devuelve.
  const pila: HTMLDialogElement[] = [];
  let activacionDeUsuario = false;

  const superior = (): HTMLDialogElement | undefined => {
    for (let i = pila.length - 1; i >= 0; i--) {
      if (pila[i].isConnected && pila[i].open) return pila[i];
    }
    return undefined;
  };

  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    if (!this.isConnected) {
      throw new DOMException("El diálogo no está conectado al documento.", "InvalidStateError");
    }
    if (this.open) return;
    focoPrevio.set(this, document.activeElement);
    this.open = true;
    pila.push(this);
    activacionDeUsuario = true;
    const objetivo = primerVisible(this, "[autofocus]:not([disabled])") ?? primerVisible(this, ENFOCABLES);
    objetivo?.focus();
  };

  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement, valor?: string) {
    if (!this.open) return;
    const conectado = this.isConnected;
    this.open = false;
    const posicion = pila.indexOf(this);
    if (posicion >= 0) pila.splice(posicion, 1);
    if (valor !== undefined) this.returnValue = valor;
    const anterior = focoPrevio.get(this);
    focoPrevio.delete(this);
    if (conectado && anterior instanceof HTMLElement && anterior.isConnected) {
      anterior.focus();
    }
    setTimeout(() => {
      act(() => {
        this.dispatchEvent(new Event("close", { bubbles: false }));
      });
    }, 0);
  };

  // Las teclas y los clics de la persona renuevan la activación; el Esc no cuenta como activación.
  for (const tipo of ["pointerdown", "mousedown", "click", "keydown"]) {
    window.addEventListener(
      tipo,
      (evento) => {
        if (evento instanceof KeyboardEvent && evento.key === "Escape") return;
        activacionDeUsuario = true;
      },
      true,
    );
  }

  window.addEventListener("keydown", (evento) => {
    if (evento.key !== "Escape" || evento.defaultPrevented) return;
    const dialogo = superior();
    if (dialogo === undefined) return;
    if (dialogo.getAttribute("closedby") === "none") return;
    const cancelable = activacionDeUsuario;
    activacionDeUsuario = false;
    const cancelar = new Event("cancel", { bubbles: false, cancelable });
    if (dialogo.dispatchEvent(cancelar)) {
      dialogo.close();
    }
  });
}
