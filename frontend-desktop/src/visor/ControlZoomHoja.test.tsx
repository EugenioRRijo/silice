import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { ControlZoomHoja } from "./ControlZoomHoja";

function montar(propios: Partial<React.ComponentProps<typeof ControlZoomHoja>> = {}) {
  const acciones = { alSubir: vi.fn(), alBajar: vi.fn(), alRestablecer: vi.fn() };
  render(<ControlZoomHoja zoom={100} razon={1} limitado={false} {...acciones} {...propios} />);
  return acciones;
}

describe("ControlZoomHoja", () => {
  test("es un grupo con nombre y el valor se anuncia con aria-live", () => {
    montar();
    expect(screen.getByRole("group", { name: "Zoom de la hoja" })).toBeInTheDocument();
    const valor = screen.getByRole("status");
    expect(valor).toHaveAttribute("aria-live", "polite");
    expect(valor).toHaveTextContent("100 %");
  });

  test("tres botones con nombre: alejar, acercar y restablecer; cada uno llama a lo suyo", async () => {
    const usuario = userEvent.setup();
    const a = montar({ zoom: 150 });
    await usuario.click(screen.getByRole("button", { name: "Alejar la hoja" }));
    await usuario.click(screen.getByRole("button", { name: "Acercar la hoja" }));
    await usuario.click(screen.getByRole("button", { name: "Restablecer el zoom de la hoja al 100 %" }));
    expect(a.alBajar).toHaveBeenCalledTimes(1);
    expect(a.alSubir).toHaveBeenCalledTimes(1);
    expect(a.alRestablecer).toHaveBeenCalledTimes(1);
  });

  test("en el tope se marca aria-disabled y no se pierde el foco ni se llama", async () => {
    const usuario = userEvent.setup();
    const a = montar({ zoom: 300 });
    const acercar = screen.getByRole("button", { name: "Acercar la hoja" });
    expect(acercar).toHaveAttribute("aria-disabled", "true");
    expect(acercar).not.toBeDisabled();
    await usuario.click(acercar);
    expect(a.alSubir).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Alejar la hoja" })).not.toHaveAttribute("aria-disabled", "true");
  });

  test("en 100 % restablecer queda inactivo; en el piso, alejar", () => {
    montar({ zoom: 50 });
    expect(screen.getByRole("button", { name: "Alejar la hoja" })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("button", { name: /Restablecer el zoom/ })).not.toHaveAttribute("aria-disabled", "true");
  });

  test("Tab recorre los tres botones y Enter y Espacio actuan", async () => {
    const usuario = userEvent.setup();
    const a = montar();
    await usuario.tab();
    expect(screen.getByRole("button", { name: "Alejar la hoja" })).toHaveFocus();
    await usuario.keyboard("{Enter}");
    await usuario.tab();
    expect(screen.getByRole("button", { name: "Acercar la hoja" })).toHaveFocus();
    await usuario.keyboard(" ");
    expect(a.alBajar).toHaveBeenCalledTimes(1);
    expect(a.alSubir).toHaveBeenCalledTimes(1);
  });

  test("si el tamano de letra cambia lo que se dibuja, el valor lo dice con texto (no solo el numero)", () => {
    montar({ zoom: 100, razon: 1.25 });
    expect(screen.getByRole("status")).toHaveTextContent("100 %");
    expect(screen.getByRole("status")).toHaveTextContent("se dibuja al 125 %");
  });

  test("cuando Univer recorta, lo avisa", () => {
    montar({ zoom: 300, razon: 4, limitado: true });
    expect(screen.getByRole("status")).toHaveTextContent("se dibuja al 400 %");
    expect(screen.getByRole("status")).toHaveTextContent("tope");
  });
});
