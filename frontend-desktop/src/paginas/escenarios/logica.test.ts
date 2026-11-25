import { describe, expect, test } from "vitest";
import type { EscenarioRespuesta } from "./tipos";
import { notaHallazgos } from "./logica";

describe("notaHallazgos", () => {
  test("escribe los conteos con punto de miles", () => {
    const e = { hallazgos: 1234, insumos_variados: 2500 } as EscenarioRespuesta;
    expect(notaHallazgos(e)).toBe("Hallazgos de revisión en este escenario: 1.234. Insumos con precio modificado: 2.500.");
  });
});
