import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { SelectorDeModo } from "./SelectorDeModo";
import { CLAVE_MODO_COLOR } from "./modoDeColor";

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

describe("SelectorDeModo", () => {
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

  test("marca Como el sistema por defecto, indica el modo del sistema y muestra la línea de ayuda", () => {
    render(<SelectorDeModo />);
    expect(screen.getByRole("group", { name: "Apariencia" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Claro" })).not.toBeChecked();
    expect(screen.getByRole("radio", { name: "Oscuro" })).not.toBeChecked();
    expect(screen.getByRole("radio", { name: "Como el sistema (ahora claro)" })).toBeChecked();
    expect(
      screen.getByText("El modo oscuro cambia la pantalla; los PDF y el Excel que se entregan no cambian."),
    ).toBeInTheDocument();
    expect(localStorage.length).toBe(0);
  });

  test("elegir Oscuro pone data-modo='oscuro' y guarda; volver a Como el sistema quita la clave y el atributo", async () => {
    const usuario = userEvent.setup();
    render(<SelectorDeModo />);

    await usuario.click(screen.getByRole("radio", { name: "Oscuro" }));
    expect(screen.getByRole("radio", { name: "Oscuro" })).toBeChecked();
    expect(document.documentElement.dataset.modo).toBe("oscuro");
    expect(localStorage.getItem(CLAVE_MODO_COLOR)).toBe("oscuro");
    expect(document.head.querySelector('meta[name="color-scheme"]')?.getAttribute("content")).toBe("dark");

    await usuario.click(screen.getByRole("radio", { name: "Como el sistema (ahora claro)" }));
    expect(screen.getByRole("radio", { name: "Como el sistema (ahora claro)" })).toBeChecked();
    expect(document.documentElement.hasAttribute("data-modo")).toBe(false);
    expect(localStorage.getItem(CLAVE_MODO_COLOR)).toBeNull();
    expect(document.head.querySelector('meta[name="color-scheme"]')?.getAttribute("content")).toBe("light dark");
  });

  test("el texto de Como el sistema refleja el modo del sistema inicial y al cambiar matchMedia", () => {
    stubMedia.cambiar(true);
    render(<SelectorDeModo />);
    expect(screen.getByRole("radio", { name: "Como el sistema (ahora oscuro)" })).toBeChecked();

    act(() => {
      stubMedia.cambiar(false);
    });
    expect(screen.getByRole("radio", { name: "Como el sistema (ahora claro)" })).toBeChecked();
  });

  test("empieza marcando el modo guardado y sigue funcionando si localStorage lanza", async () => {
    localStorage.setItem(CLAVE_MODO_COLOR, "claro");
    const { unmount } = render(<SelectorDeModo />);
    expect(screen.getByRole("radio", { name: "Claro" })).toBeChecked();
    unmount();

    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    const usuario = userEvent.setup();
    render(<SelectorDeModo />);
    expect(screen.getByRole("radio", { name: "Como el sistema (ahora claro)" })).toBeChecked();
    await usuario.click(screen.getByRole("radio", { name: "Oscuro" }));
    expect(screen.getByRole("radio", { name: "Oscuro" })).toBeChecked();
    expect(document.documentElement.dataset.modo).toBe("oscuro");
  });
});
