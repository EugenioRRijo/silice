import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { TamanoLetra } from "./TamanoLetra";
import { CLAVE_TAMANO_LETRA } from "./preferenciaDeLetra";

const escala = () => document.documentElement.style.getPropertyValue("--silice-escala-letra");

describe("TamanoLetra (control de la cabecera)", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("style");
    delete document.documentElement.dataset.siliceLetra;
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("es un grupo con nombre y tres botones, con Normal marcado al empezar", () => {
    render(<TamanoLetra />);
    expect(screen.getByRole("group", { name: "Tamaño de letra" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Normal" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Grande" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Muy grande" })).toHaveAttribute("aria-pressed", "false");
  });

  test("un clic en Grande aplica la variable, lo marca y lo guarda", async () => {
    const usuario = userEvent.setup();
    render(<TamanoLetra />);
    await usuario.click(screen.getByRole("button", { name: "Grande" }));
    expect(escala()).toBe("1.25");
    expect(screen.getByRole("button", { name: "Grande" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Normal" })).toHaveAttribute("aria-pressed", "false");
    expect(localStorage.getItem(CLAVE_TAMANO_LETRA)).toBe("grande");
  });

  test("por teclado: Tab llega a los botones y Enter y Espacio eligen", async () => {
    const usuario = userEvent.setup();
    render(<TamanoLetra />);
    await usuario.tab();
    expect(screen.getByRole("button", { name: "Normal" })).toHaveFocus();
    await usuario.tab();
    expect(screen.getByRole("button", { name: "Grande" })).toHaveFocus();
    await usuario.keyboard("{Enter}");
    expect(escala()).toBe("1.25");
    await usuario.tab();
    expect(screen.getByRole("button", { name: "Muy grande" })).toHaveFocus();
    await usuario.keyboard(" ");
    expect(escala()).toBe("1.5");
    expect(localStorage.getItem(CLAVE_TAMANO_LETRA)).toBe("muy-grande");
  });

  test("empieza en lo guardado", () => {
    localStorage.setItem(CLAVE_TAMANO_LETRA, "muy-grande");
    render(<TamanoLetra />);
    expect(screen.getByRole("button", { name: "Muy grande" })).toHaveAttribute("aria-pressed", "true");
  });

  test("al montarse sin elección previa no escribe en el almacenamiento", () => {
    render(<TamanoLetra />);
    expect(localStorage.length).toBe(0);
  });

  test("sin almacenamiento (lanza al leer y al escribir) el control sigue funcionando", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    const usuario = userEvent.setup();
    render(<TamanoLetra />);
    await usuario.click(screen.getByRole("button", { name: "Muy grande" }));
    expect(escala()).toBe("1.5");
    expect(screen.getByRole("button", { name: "Muy grande" })).toHaveAttribute("aria-pressed", "true");
  });

  test("cada botón muestra la A y el nombre completo en el título", () => {
    render(<TamanoLetra />);
    for (const nombre of ["Normal", "Grande", "Muy grande"]) {
      const b = screen.getByRole("button", { name: nombre });
      expect(b).toHaveAttribute("title", nombre);
      expect(b.textContent).toContain("A");
    }
  });

  // MENOR-7: lo que manda es lo que esta aplicado en la raiz (main.tsx lo fija antes de pintar), no lo que diga el
  // almacenamiento: con el almacenamiento bloqueado la eleccion vale para la pantalla pero no se guarda, y el control del
  // shell (otra instancia, montada al entrar) debe arrancar marcando lo que se ve.
  test("empieza marcando lo aplicado en la raíz aunque el almacenamiento esté bloqueado", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    document.documentElement.dataset.siliceLetra = "grande";
    render(<TamanoLetra />);
    expect(screen.getByRole("button", { name: "Grande" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Normal" })).toHaveAttribute("aria-pressed", "false");
  });

  test("pantalla de entrada y shell: con el almacenamiento bloqueado, la segunda instancia hereda la elección de la primera", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    const usuario = userEvent.setup();
    const entrada = render(<TamanoLetra />);
    await usuario.click(screen.getByRole("button", { name: "Muy grande" }));
    entrada.unmount();
    render(<TamanoLetra />);
    expect(screen.getByRole("button", { name: "Muy grande" })).toHaveAttribute("aria-pressed", "true");
    expect(escala()).toBe("1.5");
  });

  test("sin nada aplicado ni guardado empieza en Normal", () => {
    delete document.documentElement.dataset.siliceLetra;
    render(<TamanoLetra />);
    expect(screen.getByRole("button", { name: "Normal" })).toHaveAttribute("aria-pressed", "true");
  });
});
