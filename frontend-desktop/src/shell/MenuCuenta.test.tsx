import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { MenuCuenta } from "./MenuCuenta";

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
