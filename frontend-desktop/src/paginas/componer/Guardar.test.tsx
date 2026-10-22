import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, test, vi } from "vitest";
import { Guardar } from "./Guardar";
import type { Props } from "./Guardar";

function montar(parcial: Partial<Props> = {}) {
  const props: Props = {
    sinCondiciones: false,
    requiereJustificacion: false,
    guardando: false,
    resultado: null,
    error: null,
    alGuardar: vi.fn(),
    ...parcial,
  };
  render(
    <MemoryRouter>
      <Guardar {...props} />
    </MemoryRouter>,
  );
  return props;
}

describe("Guardar", () => {
  test("sin condiciones del rendimiento el botón está deshabilitado y dice por qué", () => {
    montar({ sinCondiciones: true });
    expect(screen.getByRole("button", { name: "Guardar composición" })).toBeDisabled();
    expect(screen.getByText(/obligatorias para guardar/)).toBeInTheDocument();
  });

  test("con condiciones se puede guardar y entrega justificación nula", async () => {
    const usuario = userEvent.setup();
    const props = montar();
    const boton = screen.getByRole("button", { name: "Guardar composición" });
    expect(boton).toBeEnabled();
    await usuario.click(boton);
    expect(props.alGuardar).toHaveBeenCalledWith(null);
  });

  test("la justificación solo aparece si la API la pide", () => {
    montar();
    expect(screen.queryByLabelText(/Justificación de la advertencia/)).not.toBeInTheDocument();
  });

  test("con advertencia de rendimiento aparece y viaja al guardar", async () => {
    const usuario = userEvent.setup();
    const props = montar({ requiereJustificacion: true });
    await usuario.type(screen.getByLabelText("Justificación de la advertencia"), "Cuadrilla reforzada.");
    await usuario.click(screen.getByRole("button", { name: "Guardar composición" }));
    expect(props.alGuardar).toHaveBeenCalledWith("Cuadrilla reforzada.");
  });

  test("mientras guarda no se puede pulsar otra vez", () => {
    montar({ guardando: true });
    expect(screen.getByRole("button", { name: "Guardar composición" })).toBeDisabled();
  });

  test("tras guardar muestra el mensaje, los avisos y el enlace a Elaborar un presupuesto", () => {
    montar({
      resultado: {
        precio_unitario: "29.70",
        mensaje: "Composición guardada para la partida FIC-1: precio unitario 29.70.",
        justificada: false,
        avisos: ["El rendimiento se guardó sin justificación."],
      },
    });
    expect(screen.getByText(/Composición guardada para la partida FIC-1/)).toBeInTheDocument();
    expect(screen.getByText("El rendimiento se guardó sin justificación.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Elaborar un presupuesto" })).toHaveAttribute("href", "/elaborar");
  });

  test("un error de guardado se muestra con su detalle y no hay enlace", () => {
    montar({ error: "Las condiciones del rendimiento son obligatorias." });
    expect(screen.getByRole("alert")).toHaveTextContent("Las condiciones del rendimiento son obligatorias.");
    expect(screen.queryByRole("link", { name: "Elaborar un presupuesto" })).not.toBeInTheDocument();
  });
});
