import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { MenuCuenta } from "./MenuCuenta";

const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const leer = (ruta: string) => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/${ruta}`, "utf-8");

describe("MenuCuenta", () => {
  test("muestra el nombre de la persona y su menú tiene solo «Salir»", async () => {
    const u = userEvent.setup();
    render(<MenuCuenta nombre="Ana Pérez" alSalir={() => {}} />);
    const boton = screen.getByRole("button", { name: /Ana Pérez/ });
    expect(boton).toHaveTextContent("Ana Pérez");
    expect(boton).toHaveAttribute("aria-expanded", "false");
    await u.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    const region = screen.getByRole("region", { name: "Cuenta" });
    const botones = within(region).getAllByRole("button");
    expect(botones).toHaveLength(1);
    expect(botones[0]).toHaveTextContent("Salir");
  });

  test("el botón muestra las iniciales en un círculo y su nombre accesible sigue siendo «Cuenta de …»", () => {
    render(<MenuCuenta nombre="Ana Pérez" alSalir={() => {}} />);
    const boton = screen.getByRole("button", { name: "Cuenta de Ana Pérez" });
    const circulo = within(boton).getByText("AP");
    expect(circulo).toHaveClass("silice-cuenta__iniciales");
    expect(circulo).toHaveAttribute("aria-hidden", "true");
  });

  test("con un solo nombre, una inicial", () => {
    render(<MenuCuenta nombre="Ana" alSalir={() => {}} />);
    expect(within(screen.getByRole("button", { name: "Cuenta de Ana" })).getByText("A")).toHaveClass("silice-cuenta__iniciales");
  });

  test("sin nombre no hay círculo vacío", () => {
    render(<MenuCuenta nombre="  " alSalir={() => {}} />);
    expect(document.querySelector(".silice-cuenta__iniciales")).toBeNull();
  });

  test("el círculo es del color de acento con texto del color del marco", () => {
    const fuente = leer("shell/MenuCuenta.scss");
    const i = fuente.indexOf(".silice-cuenta__iniciales {");
    const regla = fuente.slice(i, fuente.indexOf("}", i));
    expect(i).toBeGreaterThan(-1);
    expect(regla).toMatch(/background(-color)?:\s*var\(--silice-acento\)/);
    expect(regla).toMatch(/(^|[\s;])color:\s*var\(--silice-marco\)/);
    expect(regla).toMatch(/border-radius:\s*50%/);
    expect(regla).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });

  test("dos instancias no repiten el id del menú", () => {
    render(
      <>
        <MenuCuenta nombre="Ana" alSalir={() => {}} />
        <MenuCuenta nombre="Rita" alSalir={() => {}} />
      </>,
    );
    const ids = screen.getAllByRole("button").map((b) => b.getAttribute("aria-controls"));
    expect(new Set(ids).size).toBe(2);
  });

  test("«Salir» llama a alSalir", async () => {
    const u = userEvent.setup();
    const alSalir = vi.fn();
    render(<MenuCuenta nombre="Ana Pérez" alSalir={alSalir} />);
    await u.click(screen.getByRole("button", { name: /Ana Pérez/ }));
    await u.click(screen.getByRole("button", { name: /^Salir/ }));
    expect(alSalir).toHaveBeenCalledTimes(1);
  });

  test("Esc cierra el menú y devuelve el foco al botón; un clic fuera también cierra", async () => {
    const u = userEvent.setup();
    render(<MenuCuenta nombre="Ana Pérez" alSalir={() => {}} />);
    const boton = screen.getByRole("button", { name: /Ana Pérez/ });
    await u.click(boton);
    await u.keyboard("{Escape}");
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(boton).toHaveFocus();
    await u.click(boton);
    await u.click(document.body);
    expect(boton).toHaveAttribute("aria-expanded", "false");
  });

  test("ninguna cadena visible lleva la palabra «caso»", async () => {
    const u = userEvent.setup();
    render(<MenuCuenta nombre="Ana Pérez" alSalir={() => {}} />);
    await u.click(screen.getByRole("button", { name: /Ana Pérez/ }));
    expect(screen.queryByText(/\bcaso\b/i)).toBeNull();
  });
});
