import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FranjaDelPaso } from "./FranjaDelPaso";

// Tarea 2 del plan F4: la franja «Te falta / Siguiente paso» (especificación §2.3): un texto y, como mucho, un botón
// principal. Textos ficticios.
const region = () => screen.getByRole("region", { name: "Siguiente paso" });

describe("FranjaDelPaso", () => {
  it("«falta» dice «Te falta:» y el texto", () => {
    render(<FranjaDelPaso tipo="falta" texto="Faltan 2 precios" />);
    expect(region()).toHaveTextContent("Te falta: Faltan 2 precios");
  });

  it("«siguiente» dice «Siguiente paso:» y el texto, sin ícono de advertencia", () => {
    render(<FranjaDelPaso tipo="siguiente" texto="Abrir la Hoja" />);
    expect(region()).toHaveTextContent("Siguiente paso: Abrir la Hoja");
    expect(region().querySelector("svg")).toBeNull();
  });

  it("«falta» lleva un ícono decorativo junto a la palabra", () => {
    render(<FranjaDelPaso tipo="falta" texto="Faltan 2 precios" />);
    expect(region().querySelector('svg[aria-hidden="true"]')).not.toBeNull();
  });

  it("con acción hay un solo botón principal y al pulsarlo se llama alPulsar", async () => {
    const alPulsar = vi.fn();
    render(<FranjaDelPaso tipo="falta" texto="Faltan 2 precios" accion={{ texto: "Abrir la Hoja", alPulsar }} />);
    const botones = region().querySelectorAll("button");
    expect(botones).toHaveLength(1);
    expect(botones[0]).toHaveClass("cds--btn--primary");
    await userEvent.click(screen.getByRole("button", { name: "Abrir la Hoja" }));
    expect(alPulsar).toHaveBeenCalledTimes(1);
  });

  it("sin acción no hay botón", () => {
    render(<FranjaDelPaso tipo="falta" texto="Faltan 2 precios" />);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("deshabilitada deshabilita el botón", () => {
    render(<FranjaDelPaso tipo="falta" texto="x" accion={{ texto: "Abrir la Hoja", alPulsar: vi.fn(), deshabilitada: true }} />);
    expect(screen.getByRole("button", { name: "Abrir la Hoja" })).toBeDisabled();
  });
});
