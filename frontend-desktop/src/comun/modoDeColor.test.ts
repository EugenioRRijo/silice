import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  CLAVE_MODO_COLOR,
  aplicarModo,
  guardarModo,
  leerModo,
  modoDelSistema,
  useModoDeColor,
} from "./modoDeColor";

function instalarMatchMedia(oscuroInicial = false) {
  let oscuro = oscuroInicial;
  const oyentes = new Set<EventListener>();
  const descriptorOriginal = Object.getOwnPropertyDescriptor(window, "matchMedia");

  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (consulta: string) => ({
      get matches() {
        return consulta === "(prefers-color-scheme: dark)" ? oscuro : false;
      },
      media: consulta,
      onchange: null,
      addEventListener(_tipo: string, oyente: EventListenerOrEventListenerObject | null) {
        if (typeof oyente === "function") oyentes.add(oyente);
      },
      removeEventListener(_tipo: string, oyente: EventListenerOrEventListenerObject | null) {
        if (typeof oyente === "function") oyentes.delete(oyente);
      },
      addListener() {},
      removeListener() {},
      dispatchEvent: () => false,
    }),
  });

  return {
    cambiar(nuevoOscuro: boolean) {
      oscuro = nuevoOscuro;
      const evento = Object.assign(new Event("change"), {
        matches: nuevoOscuro,
        media: "(prefers-color-scheme: dark)",
      });
      for (const oyente of oyentes) oyente(evento);
    },
    restaurar() {
      if (descriptorOriginal) {
        Object.defineProperty(window, "matchMedia", descriptorOriginal);
      } else {
        Reflect.deleteProperty(window, "matchMedia");
      }
    },
  };
}

describe("modoDeColor", () => {
  let stubMedia: ReturnType<typeof instalarMatchMedia>;

  beforeEach(() => {
    localStorage.clear();
    delete document.documentElement.dataset.modo;
    document.head.querySelectorAll('meta[name="color-scheme"]').forEach((m) => m.remove());
    stubMedia = instalarMatchMedia(false);
  });

  afterEach(() => {
    stubMedia.restaurar();
    vi.restoreAllMocks();
  });

  test("sin nada guardado devuelve sistema", () => {
    expect(leerModo()).toBe("sistema");
  });

  test("lee claro y oscuro cuando están guardados", () => {
    localStorage.setItem(CLAVE_MODO_COLOR, "claro");
    expect(leerModo()).toBe("claro");
    localStorage.setItem(CLAVE_MODO_COLOR, "oscuro");
    expect(leerModo()).toBe("oscuro");
  });

  test.each(["sistema", "azul", "", "OSCURO", "claro "])("un valor inválido (%j) equivale a sistema", (malo) => {
    localStorage.setItem(CLAVE_MODO_COLOR, malo);
    expect(leerModo()).toBe("sistema");
  });

  test("guardarModo escribe claro u oscuro y quita la clave al volver a sistema", () => {
    guardarModo("oscuro");
    expect(localStorage.getItem(CLAVE_MODO_COLOR)).toBe("oscuro");
    guardarModo("claro");
    expect(localStorage.getItem(CLAVE_MODO_COLOR)).toBe("claro");
    guardarModo("sistema");
    expect(localStorage.getItem(CLAVE_MODO_COLOR)).toBeNull();
  });

  test("si localStorage lanza al leer, guardar o quitar, no rompe ni propaga el error", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("lleno", "QuotaExceededError");
    });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    expect(leerModo()).toBe("sistema");
    expect(() => guardarModo("oscuro")).not.toThrow();
    expect(() => guardarModo("sistema")).not.toThrow();
  });

  test("aplicarModo fija data-modo en html y content del meta color-scheme", () => {
    const meta = document.createElement("meta");
    meta.setAttribute("name", "color-scheme");
    meta.setAttribute("content", "light dark");
    document.head.appendChild(meta);

    aplicarModo("oscuro");
    expect(document.documentElement.dataset.modo).toBe("oscuro");
    expect(meta.getAttribute("content")).toBe("dark");

    aplicarModo("claro");
    expect(document.documentElement.dataset.modo).toBe("claro");
    expect(meta.getAttribute("content")).toBe("light");

    aplicarModo("sistema");
    expect(document.documentElement.dataset.modo).toBeUndefined();
    expect(document.documentElement.hasAttribute("data-modo")).toBe(false);
    expect(meta.getAttribute("content")).toBe("light dark");
  });

  test("modoDelSistema refleja la consulta prefers-color-scheme: dark", () => {
    expect(modoDelSistema()).toBe("claro");
    stubMedia.cambiar(true);
    expect(modoDelSistema()).toBe("oscuro");
  });

  test("useModoDeColor permite elegir, sincroniza con el evento storage y escucha cambios de matchMedia", () => {
    const { result } = renderHook(() => useModoDeColor());
    expect(result.current.modo).toBe("sistema");
    expect(result.current.delSistema).toBe("claro");

    act(() => {
      result.current.elegir("oscuro");
    });
    expect(result.current.modo).toBe("oscuro");
    expect(document.documentElement.dataset.modo).toBe("oscuro");
    expect(localStorage.getItem(CLAVE_MODO_COLOR)).toBe("oscuro");

    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: "otra-clave", newValue: "claro" }));
    });
    expect(result.current.modo).toBe("oscuro");

    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: CLAVE_MODO_COLOR, newValue: "claro" }));
    });
    expect(result.current.modo).toBe("claro");
    expect(document.documentElement.dataset.modo).toBe("claro");
    expect(document.head.querySelector('meta[name="color-scheme"]')?.getAttribute("content")).toBe("light");

    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: CLAVE_MODO_COLOR, newValue: null }));
    });
    expect(result.current.modo).toBe("sistema");
    expect(document.documentElement.hasAttribute("data-modo")).toBe(false);
    expect(document.head.querySelector('meta[name="color-scheme"]')?.getAttribute("content")).toBe("light dark");

    act(() => {
      stubMedia.cambiar(true);
    });
    expect(result.current.delSistema).toBe("oscuro");
  });
});
