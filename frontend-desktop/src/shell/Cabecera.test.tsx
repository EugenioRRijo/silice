import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { Cabecera } from "./Cabecera";

// Letra grande por presbicia: el control «Tamaño de letra» está siempre en la cabecera, también antes de entrar (la
// persona necesita leer la pantalla de entrada).
describe("Cabecera", () => {
  test("con sesión trae el control de tamaño de letra junto al nombre y «Salir»", () => {
    render(<Cabecera nombre="Ana Pérez" alSalir={() => {}} />);
    expect(screen.getByRole("group", { name: "Tamaño de letra" })).toBeInTheDocument();
    expect(screen.getByText("Ana Pérez")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salir/ })).toBeInTheDocument();
  });

  test("sin sesión (pantalla de entrada) también trae el control, y no el nombre ni «Salir»", () => {
    render(<Cabecera />);
    expect(screen.getByRole("group", { name: "Tamaño de letra" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Salir/ })).not.toBeInTheDocument();
  });

  // Con la letra Grande o Muy grande el nombre se oculta en la cabecera (no cabe): sigue en el nombre accesible y el título
  // del botón «Salir».
  test("«Salir» lleva el nombre de la persona en su nombre accesible y en su título", () => {
    render(<Cabecera nombre="Ana Pérez" alSalir={() => {}} />);
    const salir = screen.getByRole("button", { name: "Salir (Ana Pérez)" });
    expect(salir).toHaveAttribute("title", "Salir (Ana Pérez)");
    expect(salir).toHaveTextContent("Salir");
  });
});
