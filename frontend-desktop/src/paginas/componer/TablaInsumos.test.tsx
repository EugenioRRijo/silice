import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, test, vi } from "vitest";
import { TablaInsumos } from "./TablaInsumos";

const MODALIDADES = ["JORNAL", "DESTAJO"];

describe("TablaInsumos", () => {
  test("sin filas muestra el título y el botón de agregar", () => {
    render(<TablaInsumos tipo="materiales" filas={[]} modalidades={MODALIDADES} alCambiar={vi.fn()} alAgregar={vi.fn()} alBorrar={vi.fn()} alExpirar={vi.fn()} alCompletar={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Materiales" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Consumo por unidad" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar fila a Materiales" })).toBeInTheDocument();
  });

  test("la columna de borrar tiene un encabezado con texto (axe: empty-table-header), oculto a la vista", () => {
    render(<TablaInsumos tipo="materiales" filas={[]} modalidades={MODALIDADES} alCambiar={vi.fn()} alAgregar={vi.fn()} alBorrar={vi.fn()} alExpirar={vi.fn()} alCompletar={vi.fn()} />);
    const acciones = screen.getByRole("columnheader", { name: "Acciones" });
    expect(acciones).toHaveTextContent("Acciones");
    expect(within(acciones).getByText("Acciones")).toHaveClass("cds--visually-hidden");
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
        alBorrar={vi.fn()} alExpirar={vi.fn()} alCompletar={vi.fn()}
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
        alBorrar={vi.fn()} alExpirar={vi.fn()} alCompletar={vi.fn()}
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
        alBorrar={vi.fn()} alExpirar={vi.fn()} alCompletar={vi.fn()}
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
        alBorrar={alBorrar} alExpirar={vi.fn()} alCompletar={vi.fn()}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Agregar fila a Materiales" }));
    expect(alAgregar).toHaveBeenCalledOnce();
    await usuario.click(screen.getByRole("button", { name: "Borrar fila 2 de Materiales" }));
    expect(alBorrar).toHaveBeenCalledWith(1);
  });
});

// Ola 2 (2026-11-13; bitácora `2026-11-13-ola2-front.md` §2): un precio de la lista convertido de Bs trae 28 cifras
// (5,041157684630738522954091816) y la sugerencia lo lee «5,04 USD». La celda lo lee con dos decimales en reposo, como
// una celda de Excel, y al entrar en ella se ve y se edita el número completo; guardar sin tocarla manda el exacto. Lo que
// la persona teclea se ve siempre tal cual. Montos ficticios.
describe("TablaInsumos: la celda del precio en reposo y al editarla", () => {
  const EXACTO = "5,041157684630738522954091816";

  function ConEstado({ precio, alCambiar = vi.fn() }: { precio: string; alCambiar?: (i: number, c: string, v: string) => void }) {
    const [filas, setFilas] = useState([{ descripcion: "Cemento ficticio", unidad: "saco", cantidad: "1", precio }]);
    return (
      <TablaInsumos
        tipo="materiales"
        filas={filas}
        modalidades={MODALIDADES}
        alCambiar={(i, clave, valor) => {
          alCambiar(i, clave, valor);
          setFilas((f) => f.map((fila, j) => (j === i ? { ...fila, [clave]: valor } : fila)));
        }}
        alAgregar={vi.fn()}
        alBorrar={vi.fn()}
        alExpirar={vi.fn()}
        alCompletar={vi.fn()}
      />
    );
  }
  const precio = () => screen.getByRole("textbox", { name: "Precio, fila 1" });

  test("con más de dos decimales se lee con dos en reposo y entero al entrar; salir sin tocarla no cambia nada", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn();
    render(<ConEstado precio={EXACTO} alCambiar={alCambiar} />);
    expect(precio()).toHaveValue("5,04");
    expect(precio()).toHaveAttribute("title", `Precio exacto: ${EXACTO}. Al entrar en la celda se ve y se edita completo.`);
    await usuario.click(precio());
    expect(precio()).toHaveValue(EXACTO);
    await usuario.tab();
    expect(precio()).toHaveValue("5,04");
    expect(alCambiar).not.toHaveBeenCalled();
  });

  test("lo que la persona teclea se ve tal cual, también en reposo", async () => {
    const usuario = userEvent.setup();
    render(<ConEstado precio={EXACTO} />);
    await usuario.click(precio());
    await usuario.clear(precio());
    await usuario.type(precio(), "5,0411");
    await usuario.tab();
    expect(precio()).toHaveValue("5,0411");
    expect(precio()).not.toHaveAttribute("title");
  });

  test("con dos decimales o menos, o con un texto que no es cifra, se ve igual en reposo", () => {
    render(<ConEstado precio="12,5" />);
    expect(precio()).toHaveValue("12,5");
    expect(precio()).not.toHaveAttribute("title");
  });

  test("la nota bajo la tabla lo explica solo cuando alguna celda se lee con dos decimales", () => {
    const { unmount } = render(<ConEstado precio={EXACTO} />);
    expect(screen.getByText("Los precios con más de dos decimales se leen con dos; al entrar en la celda se ve y se edita el número completo.")).toBeInTheDocument();
    unmount();
    render(<ConEstado precio="12,50" />);
    expect(screen.queryByText(/se leen con dos/)).not.toBeInTheDocument();
  });
});
