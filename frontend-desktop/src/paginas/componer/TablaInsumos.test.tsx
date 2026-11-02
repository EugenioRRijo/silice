import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { TablaInsumos } from "./TablaInsumos";

const MODALIDADES = ["JORNAL", "DESTAJO"];

describe("TablaInsumos", () => {
  test("sin filas muestra el título y el botón de agregar", () => {
    render(<TablaInsumos tipo="materiales" filas={[]} modalidades={MODALIDADES} alCambiar={vi.fn()} alAgregar={vi.fn()} alBorrar={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Materiales" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Consumo por unidad" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar fila a Materiales" })).toBeInTheDocument();
  });

  test("teclear en una celda avisa con la fila, la columna y el texto", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn();
    render(
      <TablaInsumos
        tipo="equipos"
        filas={[{ descripcion: "", cantidad: "", precio: "", depreciacion: "" }]}
        modalidades={MODALIDADES}
        alCambiar={alCambiar}
        alAgregar={vi.fn()}
        alBorrar={vi.fn()}
      />,
    );
    await usuario.type(screen.getByLabelText("Cantidad, fila 1"), "7");
    expect(alCambiar).toHaveBeenCalledWith(0, "cantidad", "7");
  });

  test("los montos se alinean a la derecha", () => {
    render(
      <TablaInsumos
        tipo="materiales"
        filas={[{ descripcion: "Arena ficticia", unidad: "m3", cantidad: "2", precio: "10.00" }]}
        modalidades={MODALIDADES}
        alCambiar={vi.fn()}
        alAgregar={vi.fn()}
        alBorrar={vi.fn()}
      />,
    );
    const celda = screen.getByLabelText("Precio, fila 1").closest("td")!;
    expect(celda).toHaveClass("silice-cifra");
    expect(screen.getByLabelText("Descripción, fila 1").closest("td")).not.toHaveClass("silice-cifra");
  });

  test("mano de obra trae un selector de modalidad con las opciones de la API", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn();
    render(
      <TablaInsumos
        tipo="mano_obra"
        filas={[{ descripcion: "Ayudante ficticio", cantidad: "1", sueldo: "5", modalidad: "" }]}
        modalidades={MODALIDADES}
        alCambiar={alCambiar}
        alAgregar={vi.fn()}
        alBorrar={vi.fn()}
      />,
    );
    const selector = screen.getByLabelText("Modalidad, fila 1");
    const opciones = within(selector).getAllByRole("option").map((o) => o.textContent);
    expect(opciones).toEqual(["", "JORNAL", "DESTAJO"]);
    await usuario.selectOptions(selector, "DESTAJO");
    expect(alCambiar).toHaveBeenCalledWith(0, "modalidad", "DESTAJO");
  });

  test("agregar y borrar avisan al padre", async () => {
    const usuario = userEvent.setup();
    const alAgregar = vi.fn();
    const alBorrar = vi.fn();
    render(
      <TablaInsumos
        tipo="materiales"
        filas={[
          { descripcion: "A", unidad: "", cantidad: "", precio: "" },
          { descripcion: "B", unidad: "", cantidad: "", precio: "" },
        ]}
        modalidades={MODALIDADES}
        alCambiar={vi.fn()}
        alAgregar={alAgregar}
        alBorrar={alBorrar}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Agregar fila a Materiales" }));
    expect(alAgregar).toHaveBeenCalledOnce();
    await usuario.click(screen.getByRole("button", { name: "Borrar fila 2 de Materiales" }));
    expect(alBorrar).toHaveBeenCalledWith(1);
  });
});
