import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { compararDecimales, TablaDensa } from "./TablaDensa";
import type { ColumnaDensa, FilaDensa } from "./TablaDensa";

const columnas: ColumnaDensa[] = [
  { clave: "codigo", titulo: "Código" },
  { clave: "descripcion", titulo: "Descripción" },
  { clave: "monto", titulo: "Monto (Bs)", numerica: true },
];

const filas: FilaDensa[] = [
  { id: "a", codigo: "P-01", descripcion: "Excavación", monto: "1586.61" },
  { id: "b", codigo: "P-02", descripcion: "Relleno", monto: "9.5" },
  { id: "c", codigo: "P-03", descripcion: "Acarreo", monto: "9.10" },
  { id: "d", codigo: "P-04", descripcion: "Descuento", monto: "-3" },
];

function codigosEnOrden(): string[] {
  const cuerpo = screen.getAllByRole("rowgroup")[1];
  return within(cuerpo)
    .getAllByRole("row")
    .map((fila) => within(fila).getAllByRole("cell")[0].textContent ?? "");
}

describe("TablaDensa", () => {
  test("usa el tamano sm de Carbon y muestra los montos exactos como llegan", () => {
    const { container } = render(<TablaDensa etiqueta="Partidas" columnas={columnas} filas={filas} />);
    expect(container.querySelector(".cds--data-table--sm")).not.toBeNull();
    expect(screen.getByText("1586.61")).toBeInTheDocument();
    expect(screen.getByText("9.10")).toBeInTheDocument(); // sin recortar el cero final
  });

  test("las columnas numericas van a la derecha con cifras tabulares, en el encabezado y en las celdas", () => {
    render(<TablaDensa etiqueta="Partidas" columnas={columnas} filas={filas} />);
    expect(screen.getByRole("columnheader", { name: /Monto/ })).toHaveClass("silice-cifra");
    expect(screen.getByRole("cell", { name: "1586.61" })).toHaveClass("silice-cifra");
    expect(screen.getByRole("cell", { name: "P-01" })).not.toHaveClass("silice-cifra");
  });

  test("ordena una columna de texto al hacer clic en su encabezado", async () => {
    const usuario = userEvent.setup();
    render(<TablaDensa etiqueta="Partidas" columnas={columnas} filas={filas} />);
    await usuario.click(screen.getByRole("button", { name: /Descripción/ }));
    // Por descripción: Acarreo (P-03), Descuento (P-04), Excavación (P-01), Relleno (P-02)
    expect(codigosEnOrden()).toEqual(["P-03", "P-04", "P-01", "P-02"]);
  });

  test("ordena los montos como decimales exactos, no como texto", async () => {
    const usuario = userEvent.setup();
    render(<TablaDensa etiqueta="Partidas" columnas={columnas} filas={filas} />);
    await usuario.click(screen.getByRole("button", { name: /Monto/ }));
    expect(codigosEnOrden()).toEqual(["P-04", "P-03", "P-02", "P-01"]); // -3, 9.10, 9.5, 1586.61
    await usuario.click(screen.getByRole("button", { name: /Monto/ }));
    expect(codigosEnOrden()).toEqual(["P-01", "P-02", "P-03", "P-04"]);
  });

  test("una columna con ordenable:false no tiene boton de orden", () => {
    render(
      <TablaDensa
        etiqueta="Partidas"
        columnas={[{ clave: "codigo", titulo: "Código", ordenable: false }]}
        filas={[{ id: "a", codigo: "P-01" }]}
      />,
    );
    expect(screen.queryByRole("button", { name: /Código/ })).not.toBeInTheDocument();
  });

  test("sin filas muestra el estado vacio que ensena que hacer", () => {
    render(
      <TablaDensa
        etiqueta="Partidas"
        columnas={columnas}
        filas={[]}
        vacio={{ titulo: "Todavía no hay partidas", descripcion: "Elabore un presupuesto para crearlas." }}
      />,
    );
    expect(screen.getByText("Todavía no hay partidas")).toBeInTheDocument();
    expect(screen.getByText("Elabore un presupuesto para crearlas.")).toBeInTheDocument();
  });

  test("sin filas y sin texto propio usa uno general", () => {
    render(<TablaDensa etiqueta="Partidas" columnas={columnas} filas={[]} />);
    expect(screen.getByText("No hay datos para mostrar")).toBeInTheDocument();
  });

  test("al cargar muestra un esqueleto anunciado y ningun dato", () => {
    render(<TablaDensa etiqueta="Partidas" columnas={columnas} filas={filas} cargando />);
    expect(screen.getByRole("status", { name: "Cargando Partidas" })).toBeInTheDocument();
    expect(screen.queryByText("1586.61")).not.toBeInTheDocument();
  });

  test("el nombre accesible de la tabla es su etiqueta", () => {
    render(<TablaDensa etiqueta="Partidas" columnas={columnas} filas={filas} />);
    expect(screen.getByRole("table", { name: "Partidas" })).toBeInTheDocument();
  });
});

describe("compararDecimales", () => {
  test("compara sin pasar por float", () => {
    expect(compararDecimales("9.5", "9.10")).toBeGreaterThan(0);
    expect(compararDecimales("9.10", "9.1")).toBe(0);
    expect(compararDecimales("-3", "2")).toBeLessThan(0);
    expect(compararDecimales("-3", "-10")).toBeGreaterThan(0);
    expect(compararDecimales("0.1000000000000000000001", "0.1")).toBeGreaterThan(0);
    expect(compararDecimales("12345678901234567890.01", "12345678901234567890.02")).toBeLessThan(0);
    expect(compararDecimales("-0", "0")).toBe(0);
  });

  test("lo que no es decimal queda al final como texto", () => {
    expect(compararDecimales("", "1")).toBeGreaterThan(0);
    expect(compararDecimales("n/d", "1")).toBeGreaterThan(0);
    expect(compararDecimales("", "")).toBe(0);
  });
});
