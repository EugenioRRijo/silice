import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { Impuestos } from "../control/logica";
import { IvaDelPresupuesto, parrafosDeAyudaDelIva } from "./IvaDelPresupuesto";

// Tarea 5b del plan F4: el subtotal, el IVA y el total con IVA que manda el servidor; la interfaz no calcula. En la
// superficie nueva (`SuperficiePresupuesto`) los montos del IVA van al pie de la grilla (`tfoot`, probados en
// `superficie/SuperficiePresupuesto.test.tsx`); aquí se conserva la prueba directa de `IvaDelPresupuesto` y `parrafosDeAyudaDelIva`.
const FUENTE =
  "Ley del IVA, alícuota general: Decreto 3.584, G.O. 6.395 Ext., 17-08-2018 (16 %) — a cotejar con la Gaceta vigente";

function impuestos(subtotal: string, iva: string, total: string): Impuestos {
  return { subtotal, iva, total, alicuota: "0.16", fuente_alicuota: FUENTE };
}

describe("IvaDelPresupuesto (pieza directa)", () => {
  test("muestra subtotal, IVA (16 %) y total con IVA con coma decimal y moneda", () => {
    render(<IvaDelPresupuesto impuestos={impuestos("1000.00", "160.00", "1160.00")} moneda="USD" />);
    const region = screen.getByRole("region", { name: "IVA del presupuesto" });
    expect(within(region).getByText("Subtotal").closest("p")).toHaveTextContent("Subtotal 1.000,00 USD");
    expect(within(region).getByText("IVA (16 %)").closest("p")).toHaveTextContent("IVA (16 %) 160,00 USD");
    expect(within(region).getByText("Total con IVA").closest("p")).toHaveTextContent("Total con IVA 1.160,00 USD");
  });

  test("el medio céntimo que sube llega tal como lo manda el servidor", () => {
    render(<IvaDelPresupuesto impuestos={impuestos("0.03", "0.01", "0.04")} moneda="USD" />);
    const region = screen.getByRole("region", { name: "IVA del presupuesto" });
    expect(within(region).getByText("IVA (16 %)").closest("p")).toHaveTextContent("IVA (16 %) 0,01 USD");
    expect(within(region).getByText("Total con IVA").closest("p")).toHaveTextContent("Total con IVA 0,04 USD");
  });

  test("parrafosDeAyudaDelIva entrega la explicación y la fuente de la alícuota", () => {
    const parrafos = parrafosDeAyudaDelIva(impuestos("1000.00", "160.00", "1160.00"));
    expect(parrafos[1]).toBe(`Alícuota: 16 %. Fuente: ${FUENTE}.`);
  });
});
