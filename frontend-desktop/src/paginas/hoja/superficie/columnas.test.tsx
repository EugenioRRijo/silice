import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { Grilla } from "../../../comun/Grilla";
import { vistaPresupuesto } from "../datosDePrueba";
import { columnasDePresupuesto } from "./columnas";
import { filasDeLaGrilla } from "./logica";
import type { FilaDeLaGrilla } from "./logica";

// Pruebas de columnas.tsx (lote B1-4): columnas del presupuesto en solo lectura, formato es-VE, «Pendiente» en texto,
// severidad en palabra junto al ícono y cero atributos title.

function filasEjemplo(): FilaDeLaGrilla[] {
  const vista = vistaPresupuesto({
    filas: [
      {
        clave: "AF-LLAVE|esp_puntos:P1",
        partida: "AF-LLAVE",
        descripcion: "Llave de paso de bronce con rosca",
        unidad: "m2",
        cantidad: "1.234,5",
        cantidad_calculada: "1.000",
        escrita: true,
        pu: { texto: "13.20", exacto: "13.198738025" },
        total: { texto: "16295.40", exacto: "16295.40" },
        estado: { severidad: null, texto: "OK" },
        quitable: false,
        nota: null,
        calculo: null,
      },
      {
        clave: "AF-SALIDA|esp_puntos:P2",
        partida: "AF-SALIDA",
        descripcion: "Salida de agua",
        unidad: "dia",
        cantidad: "5",
        cantidad_calculada: "3",
        escrita: true,
        pu: null,
        total: null,
        estado: { severidad: "ERROR", texto: "PENDIENTE: sin APU en el catálogo (AF-SALIDA)" },
        quitable: false,
        nota: null,
        calculo: null,
      },
      {
        clave: "OC-EXC|manual",
        partida: "OC-EXC",
        descripcion: "Excavación a mano",
        unidad: "m3",
        cantidad: "12,5",
        cantidad_calculada: "12,5",
        escrita: false,
        pu: { texto: "25.00", exacto: "25" },
        total: { texto: "312.50", exacto: "312.5" },
        estado: { severidad: "ADVERTENCIA", texto: "Cantidad escrita a mano (12.5 m3)" },
        quitable: true,
        nota: null,
        calculo: null,
      },
    ],
  });
  return filasDeLaGrilla(vista, null);
}

describe("columnasDePresupuesto", () => {
  test("define las siete columnas del presupuesto en su orden y marca numéricas solo cantidad, precio unitario y total", () => {
    const columnas = columnasDePresupuesto();
    expect(columnas.map((c) => c.titulo)).toEqual([
      "Partida",
      "Descripción",
      "Unidad",
      "Cantidad",
      "Precio unitario",
      "Total",
      "Problemas",
    ]);
    expect(columnas.filter((c) => c.numerica).map((c) => c.clave)).toEqual(["cantidad", "pu", "total"]);
    expect(columnas.some((c) => c.editable === true)).toBe(false);
  });

  test("en la Grilla presenta unidades, cifras en es-VE, «Pendiente» en texto y severidad en palabra sin ningún title", () => {
    const filas = filasEjemplo();
    const { container } = render(
      <Grilla<FilaDeLaGrilla>
        etiqueta="Presupuesto"
        columnas={columnasDePresupuesto()}
        filas={filas}
        idDeFila={(f) => f.clave}
      />,
    );

    const grilla = screen.getByRole("grid", { name: "Presupuesto" });
    expect(within(grilla).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Partida",
      "Descripción",
      "Unidad",
      "Cantidad",
      "Precio unitario",
      "Total",
      "Problemas",
    ]);

    const filaLlave = within(grilla).getByRole("row", { name: /AF-LLAVE/ });
    expect(within(filaLlave).getByRole("gridcell", { name: "m²" })).toBeInTheDocument();
    expect(within(filaLlave).getByRole("gridcell", { name: "1.234,5" })).toBeInTheDocument();
    expect(within(filaLlave).getByRole("gridcell", { name: "13,20" })).toBeInTheDocument();
    expect(within(filaLlave).getByRole("gridcell", { name: "16.295,40" })).toBeInTheDocument();
    expect(within(filaLlave).getByRole("gridcell", { name: "Sin problemas" })).toBeInTheDocument();

    const filaSalida = within(grilla).getByRole("row", { name: /AF-SALIDA/ });
    expect(within(filaSalida).getByRole("gridcell", { name: "día" })).toBeInTheDocument();
    expect(within(filaSalida).getAllByRole("gridcell", { name: "Pendiente" })).toHaveLength(2);
    const celdaProblemaSalida = within(filaSalida).getByText("Error").closest("td");
    expect(celdaProblemaSalida).not.toBeNull();
    expect(celdaProblemaSalida).toHaveTextContent("Pendiente: sin precio con la lista de esta versión (AF-SALIDA)");
    expect(celdaProblemaSalida).not.toHaveTextContent("PENDIENTE:");

    const filaExc = within(grilla).getByRole("row", { name: /OC-EXC/ });
    expect(within(filaExc).getByRole("gridcell", { name: "m³" })).toBeInTheDocument();
    const celdaProblemaExc = within(filaExc).getByText("Advertencia").closest("td");
    // La cifra del mensaje del servidor pasa a es-VE; la unidad dentro de un texto libre se deja como viene.
    expect(celdaProblemaExc).toHaveTextContent("Cantidad escrita a mano (12,5 m3)");

    expect(container.querySelectorAll("[title]")).toHaveLength(0);
    expect(within(grilla).queryByRole("button", { name: /Ver el valor exacto/ })).toBeNull();
  });

  test("las celdas no se editan con F2, Enter ni al escribir caracteres", async () => {
    const u = userEvent.setup();
    render(
      <Grilla<FilaDeLaGrilla>
        etiqueta="Presupuesto"
        columnas={columnasDePresupuesto()}
        filas={filasEjemplo()}
        idDeFila={(f) => f.clave}
      />,
    );

    const celdaCantidad = screen.getByRole("gridcell", { name: "1.234,5" });
    await u.click(celdaCantidad);
    await u.keyboard("{F2}{Enter}99");
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  test("con las cantidades de la superficie, la celda Cantidad es la celda editable y muestra lo escrito (no lo del servidor)", () => {
    const filas = filasEjemplo();
    const celda = vi.fn((f: { clave: string; partida: string; cantidad: string }) => ({
      etiqueta: `Cantidad, ${f.partida}`,
      valor: f.partida === "AF-LLAVE" ? "77,7" : f.cantidad,
      alCambiar: vi.fn(),
      alRestaurar: vi.fn(),
      alConfirmar: vi.fn(),
    }));
    render(
      <Grilla<FilaDeLaGrilla>
        etiqueta="Presupuesto"
        columnas={columnasDePresupuesto({ celda })}
        filas={filas}
        idDeFila={(f) => f.clave}
      />,
    );
    const filaLlave = within(screen.getByRole("grid", { name: "Presupuesto" })).getByRole("row", { name: /AF-LLAVE/ });
    expect(within(filaLlave).getByRole("gridcell", { name: "77,7" })).toBeInTheDocument();
    expect(within(filaLlave).queryByRole("gridcell", { name: "1.234,5" })).toBeNull();
    expect(celda).toHaveBeenCalled();
  });

  test("la columna Problemas dice cuántos problemas tiene la partida cuando son varios", () => {
    const vista = vistaPresupuesto();
    const base = filasDeLaGrilla(vista, null)[0]!;
    const fila: FilaDeLaGrilla = {
      ...base,
      problema: { severidad: "ERROR", palabra: "Error", texto: "Cantidad dudosa", total: 3 },
    };
    render(
      <Grilla<FilaDeLaGrilla> etiqueta="Presupuesto" columnas={columnasDePresupuesto()} filas={[fila]} idDeFila={(f) => f.clave} />,
    );
    expect(screen.getByRole("gridcell", { name: /Error.*3 problemas/ })).toBeInTheDocument();
  });
});
