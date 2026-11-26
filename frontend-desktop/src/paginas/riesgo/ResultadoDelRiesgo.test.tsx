import { render, screen, within } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, test } from "vitest";
import type { ProyeccionDeLaObra } from "../../api/riesgo";
import { ResultadoDeLaProyeccion } from "./ResultadoDelRiesgo";

// El medidor del rango de la proyección (rediseño 2026-11-21) con la respuesta de `POST /v1/riesgo/proyectar` tal como llega:
// los montos con punto decimal y más decimales de los que se leen. La pantalla los escribe en centésimas es-VE y no calcula
// ninguna variación: la API no la manda. Datos ficticios.
const PROYECCION: ProyeccionDeLaObra = {
  proyecto: "Vía Demo",
  version: "VIA-002",
  moneda: "USD",
  inicio: "2027-02-01",
  inicio_de: "linea_base",
  meses: 6,
  trayectorias: 2000,
  semilla: 1,
  total_base: "1000",
  p50: "1248.7171",
  p80: "1302.4561",
  reserva: "302.4561",
  contribucion: [{ insumo: "Cemento asfáltico", monto: "200.5" }],
  meses_usados: 24,
  supuestos: ["gasto uniforme en el plazo"],
  mezclas: [],
};

function montar(datos: ProyeccionDeLaObra = PROYECCION) {
  render(<ResultadoDeLaProyeccion datos={datos} region={createRef<HTMLElement>()} conSeries={false} />);
  return screen.getByRole("group", { name: "Rango de exposición de costos" });
}

describe("el medidor del rango de la proyección", () => {
  test("escribe la base, el P50 y el P80 de la API en centésimas es-VE", () => {
    const medidor = montar();
    expect(within(medidor).getByText("1.000,00 USD")).toBeInTheDocument();
    expect(within(medidor).getByText("1.248,72 USD")).toBeInTheDocument();
    expect(within(medidor).getByText("1.302,46 USD")).toBeInTheDocument();
    expect(medidor.textContent).not.toMatch(/1248\.7|1302\.4/);
  });

  test("no escribe la variación contra la base: la API no la da y el navegador no la calcula", () => {
    const medidor = montar();
    expect(medidor.textContent).not.toMatch(/%/);
    expect(medidor.textContent).not.toMatch(/\+\s*\d/);
  });

  test("ningún monto del medidor sale de redondear en el navegador: un total de 30 cifras se lee entero", () => {
    const medidor = montar({ ...PROYECCION, total_base: "123456789012345678901234567890.125", p50: "1", p80: "2" });
    expect(within(medidor).getByText("123.456.789.012.345.678.901.234.567.890,13 USD")).toBeInTheDocument();
  });

  test("las barras miden la diferencia contra la base: el P50 queda visiblemente por debajo del P80", () => {
    // Con movimiento reducido el medidor se pinta ya en su valor final (sin él, crece desde la base al cargar).
    const original = window.matchMedia;
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: (q: string) => ({ matches: q.includes("reduced-motion"), media: q, addEventListener() {}, removeEventListener() {} }),
    });
    let medidor: HTMLElement;
    try {
      medidor = montar();
    } finally {
      Object.defineProperty(window, "matchMedia", { configurable: true, value: original });
    }
    const [p50, p80] = [...medidor.querySelectorAll<HTMLElement>(".silice-riesgo-medidor__barra")];
    // Base 1.000, P50 1.248,72 y P80 1.302,46: contra cero las tres medirían casi lo mismo (77 %, 96 % y 100 %).
    expect(Number.parseFloat(p50!.style.inlineSize)).toBeCloseTo(82.23, 1);
    expect(p80!.style.inlineSize).toBe("100%");
  });
});

describe("el rango de la proyección como tabla", () => {
  test("«Ver como tabla» trae el presupuesto, el P50, el P80 y la reserva con los mismos montos del medidor", () => {
    montar();
    expect(screen.getByText("Ver como tabla")).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: "Rango de la proyección en cifras" });
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["Presupuesto base vigente", "1.000,00 USD"],
      ["Costo probable (P50)", "1.248,72 USD"],
      ["Costo conservador (P80)", "1.302,46 USD"],
      ["Reserva recomendada para cubrir el P80", "302,46 USD"],
    ]);
  });

  test("la tabla no inventa el P10 ni el P90: la API no los manda", () => {
    montar();
    const tabla = screen.getByRole("table", { name: "Rango de la proyección en cifras" });
    expect(tabla.textContent).not.toMatch(/P10|P90/);
  });

  test("la tabla se escribe igual que el medidor: sin variación contra la base", () => {
    montar();
    const tabla = screen.getByRole("table", { name: "Rango de la proyección en cifras" });
    expect(tabla.textContent).not.toMatch(/%/);
  });
});
