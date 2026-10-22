import { describe, expect, test } from "vitest";
import { requierenAtencion } from "./PanelArenera";
import type { ExistenciaRespuesta } from "./PanelArenera";

function fila(codigo: string, parcial: Partial<ExistenciaRespuesta> = {}): ExistenciaRespuesta {
  return {
    codigo,
    nombre: codigo,
    unidad_venta: "m3",
    existencia: "10",
    minima: "5",
    queda_poco: false,
    negativa: false,
    ...parcial,
  };
}

describe("requierenAtencion", () => {
  test("deja fuera lo que está sobre el mínimo", () => {
    expect(requierenAtencion([fila("A"), fila("B")])).toEqual([]);
  });

  test("pone lo negativo primero y conserva el orden dentro de cada grupo", () => {
    const filas = [
      fila("P1", { queda_poco: true }),
      fila("N1", { negativa: true }),
      fila("P2", { queda_poco: true }),
      fila("N2", { negativa: true, queda_poco: true }),
    ];
    expect(requierenAtencion(filas).map((f) => f.codigo)).toEqual(["N1", "N2", "P1", "P2"]);
  });

  test("una negativa entra aunque no marque «queda poco»", () => {
    expect(requierenAtencion([fila("Z", { negativa: true })]).map((f) => f.codigo)).toEqual(["Z"]);
  });
});
