import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { TramoConCantidades, resumenDelTramo } from "./TramoConCantidades";

// F5 vial, tarea 1: las partidas nuevas del catálogo vial llegan con sus unidades canónicas del servidor («dia»,
// «unidad», «m2») y la pantalla las escribe como se leen («día», «m²»). Datos ficticios; la pantalla no calcula.
const TRAMO = {
  id: "P1",
  progresiva_ini_km: "0",
  progresiva_fin_km: "0.5",
  ancho_m: "7",
  distancia_planta_km: null,
  capas: [{ tipo: "fresado", espesor_m: "0.04", densidad_t_m3: null, dosis_l_m2: null, esponjamiento: "1.25" }],
  demarcacion: [{ tipo: "superficie", lineas: 3, area_m2: "6" }],
};
const CANTIDADES = [
  { tramo: "P1", codigo: "C-000.000.018", descripcion: "Transporte del material fresado, medido suelto, tramo P1", unidad: "m3", cantidad: "175", origen_id: "tramo:P1:capa:1", regla: "longitud*ancho*espesor*esponjamiento" },
  { tramo: "P1", codigo: "C-000.000.021", descripcion: "Demarcación de superficies, tramo P1", unidad: "m2", cantidad: "18", origen_id: "tramo:P1:demarcacion:1", regla: "area_elemento*elementos" },
  { tramo: "P1", codigo: "C-000.000.019", descripcion: "Señalización y control de tránsito, tramo P1", unidad: "dia", cantidad: "1250.5", origen_id: "tramo:P1", regla: "" },
];

describe("Un tramo con las partidas nuevas", () => {
  test("escribe «día» y «m³» con su tilde y la cantidad con coma decimal y punto de miles", () => {
    render(<TramoConCantidades tramo={TRAMO} cantidades={CANTIDADES} />);
    const tabla = screen.getByRole("table", { name: "Cantidades del tramo P1" });
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["Transporte del material fresado, medido suelto, tramo P1", "m³", "175"],
      ["Demarcación de superficies, tramo P1", "m²", "18"],
      ["Señalización y control de tránsito, tramo P1", "día", "1.250,5"],
    ]);
  });

  test("el resumen dice cuándo la obra mide el transporte por banda de distancia (tarea 2)", () => {
    expect(resumenDelTramo({ ...TRAMO, distancia_planta_km: "9", transporte: "banda" })).toBe(
      "De 0 a 0,5 km · ancho 7 m · planta a 9 km · transporte en t por banda de distancia",
    );
    expect(resumenDelTramo({ ...TRAMO, distancia_planta_km: "9", transporte: null })).toBe("De 0 a 0,5 km · ancho 7 m · planta a 9 km");
  });
});
