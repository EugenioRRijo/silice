import { render, screen, within } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, test } from "vitest";
import type { CalculoDeCosto } from "../../api/produccionPlanta";
import { ResultadoDelCalculo } from "./ResultadoDelCalculo";

// Datos ficticios. Las constancias de la 4b salen de la instantánea que guardó el servidor; la pantalla no calcula nada.
function calculo(entradas: Record<string, unknown>, resultado: Record<string, unknown>): CalculoDeCosto {
  return {
    id: 11,
    periodo: "2026-11",
    moneda: "Bs",
    huella: "d".repeat(64),
    usuario: "ana",
    registrado: "2026-11-30T10:00:00",
    productos: [{ codigo: "MZP-01", por_tonelada: "50.7", presentado: "50.70" }],
    instantanea: { entradas: { agregados: [], producido: {}, ...entradas }, resultado: { total_cantera: "1500", total_planta: "120", ...resultado } },
    publicado: null,
  };
}
function ver(c: CalculoDeCosto) {
  render(<ResultadoDelCalculo calculo={c} region={createRef<HTMLElement>()} />);
  return screen.getByRole("region", { name: "Resultado del cálculo" });
}

describe("Constancias de la Tarea 4b en el resultado", () => {
  test("el cálculo muestra lo que viene del mes anterior y lo que pasa al siguiente", () => {
    const region = ver(
      calculo(
        { viene_del_mes_anterior: { cantera: { total: "1000", calculo: 5, periodo: "2026-10", costos: [1, 2], tasa: null } } },
        { pasa_al_mes_siguiente: { planta: { total: "2500.5", costos: [9] } } },
      ),
    );
    const anterior = within(region).getByRole("region", { name: "Viene del mes anterior" });
    expect(anterior).toHaveTextContent("Cantera: 1.000,00 Bs");
    expect(anterior).toHaveTextContent("cálculo n.º 5 de octubre de 2026");
    const siguiente = within(region).getByRole("region", { name: "Pasa al mes siguiente" });
    expect(siguiente).toHaveTextContent("Planta: 2.500,50 Bs");
  });

  test("lo que viene en otra moneda dice la tasa del cierre con que se convirtió", () => {
    const region = ver(
      calculo(
        { viene_del_mes_anterior: { cantera: { total: "8000", calculo: 5, periodo: "2026-10", costos: [1], tasa: { valor: "40", fecha: "2026-10-30", fuente: "BCV" } } } },
        {},
      ),
    );
    expect(within(region).getByRole("region", { name: "Viene del mes anterior" })).toHaveTextContent("tasa del cierre de octubre de 2026: 40,00 del 30/10/2026");
  });

  test("un agregado con costo de otro cálculo lo dice con su período", () => {
    const region = ver(calculo({ de_otro_calculo: { "AGR-12": { costo: "5", calculo: 4, periodo: "2026-10" } } }, {}));
    const bloque = within(region).getByRole("region", { name: "Costos tomados de otro cálculo" });
    expect(bloque).toHaveTextContent("AGR-12: 5,00 Bs por tonelada, del cálculo n.º 4 de octubre de 2026");
  });

  test("un cálculo de la versión 1 (sin esas claves) no muestra ninguna de las tres secciones", () => {
    const region = ver(calculo({}, {}));
    for (const nombre of ["Viene del mes anterior", "Pasa al mes siguiente", "Costos tomados de otro cálculo"]) {
      expect(within(region).queryByRole("region", { name: nombre })).not.toBeInTheDocument();
    }
  });

  test("un cálculo sin costos por tonelada dice que no se puede publicar", () => {
    const c = { ...calculo({}, { pasa_al_mes_siguiente: { cantera: { total: "300", costos: [1] } } }), productos: [] };
    const region = ver(c);
    expect(within(region).getByText("Este cálculo no tiene costos por tonelada: todo pasa al mes siguiente.")).toBeInTheDocument();
  });
});
