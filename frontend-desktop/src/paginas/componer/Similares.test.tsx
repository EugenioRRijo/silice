import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { Similar } from "./cliente";
import { Similares } from "./Similares";

const UNA: Similar = {
  codigo: "FIC-001",
  descripcion: "Muro ficticio de bloque",
  puntaje: 0.8734,
  rendimiento: "12.00",
  unidad: "m2",
  tablas: {
    materiales: [{ descripcion: "Bloque ficticio", unidad: "u", cantidad: "12.5", precio: "0.80" }],
    equipos: [],
    mano_obra: [{ descripcion: "Albañil ficticio", cantidad: "1", sueldo: "20", modalidad: "JORNAL" }],
  },
  aviso: null,
};

describe("Similares", () => {
  test("sin similares no pinta nada", () => {
    const { container } = render(<Similares similares={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  test("lista cada partida con puntaje a dos decimales, código y descripción", () => {
    render(<Similares similares={[UNA]} />);
    expect(screen.getByRole("heading", { name: "Partidas similares del catálogo" })).toBeInTheDocument();
    expect(screen.getByText("0.87 · FIC-001 · Muro ficticio de bloque")).toBeInTheDocument();
  });

  test("al abrir una muestra el rendimiento y sus tablas de solo lectura", async () => {
    const usuario = userEvent.setup();
    render(<Similares similares={[UNA]} />);
    await usuario.click(screen.getByRole("button", { name: /FIC-001/ }));
    expect(screen.getByText("Rendimiento: 12.00 m2/día")).toBeInTheDocument();
    expect(screen.getByText("Bloque ficticio")).toBeInTheDocument();
    expect(screen.getByText("Albañil ficticio")).toBeInTheDocument();
    expect(screen.queryAllByRole("textbox")).toHaveLength(0);
  });

  test("con aviso de desglose incompleto lo muestra en lugar de las tablas", async () => {
    const usuario = userEvent.setup();
    render(
      <Similares
        similares={[{ ...UNA, codigo: "FIC-002", tablas: null, rendimiento: null, unidad: null, aviso: "Desglose incompleto en la lista vigente: falta un precio." }]}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: /FIC-002/ }));
    expect(screen.getByText(/Desglose incompleto en la lista vigente: falta un precio\./)).toBeInTheDocument();
  });
});
