import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";
import { TablaPaginada } from "./TablaPaginada";

const columnas = [{ clave: "codigo", titulo: "Código", ordenable: false }];
const filasDe = (n: number) => Array.from({ length: n }, (_, i) => ({ id: `f${i}`, codigo: `A${i + 1}` }));

describe("TablaPaginada", () => {
  test("vuelve a la primera página cuando cambia el número de filas", async () => {
    const { rerender } = render(<TablaPaginada etiqueta="Prueba" columnas={columnas} filas={filasDe(120)} />);
    await userEvent.click(screen.getByRole("button", { name: /página siguiente|next page/i }));
    expect(screen.getByText(/51–100 de 120/)).toBeInTheDocument();
    rerender(<TablaPaginada etiqueta="Prueba" columnas={columnas} filas={filasDe(110)} />);
    expect(screen.getByText(/1–50 de 110/)).toBeInTheDocument();
    expect(within(screen.getByRole("table", { name: "Prueba" })).getByText("A1")).toBeInTheDocument();
  });

  test("hasta 100 filas no hay paginación", () => {
    render(<TablaPaginada etiqueta="Prueba" columnas={columnas} filas={filasDe(100)} />);
    expect(screen.queryByText(/ de 100/)).toBeNull();
  });

  test("el texto del Estado no se recorta con puntos suspensivos: se lee completo con el teclado", () => {
    const css = readFileSync(resolve(process.cwd(), "src/paginas/hoja/hoja.scss"), "utf-8");
    const bloque = /\.silice-hoja__estado-texto\s*\{[^}]*\}/.exec(css)?.[0] ?? "";
    expect(bloque).not.toBe("");
    expect(bloque).not.toMatch(/text-overflow|nowrap/);
  });
});
