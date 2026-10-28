import { describe, expect, test } from "vitest";
import { TEXTOS } from "./textos";

// Los números de los textos de la bandeja se escriben en es-VE: punto de miles (decisión de Eugenio, 25/10/2026).
// Oráculos a mano.
describe("Pendientes: los números de los textos llevan punto de miles", () => {
  test("«por hacer»", () => {
    expect(TEXTOS.porHacer(4)).toBe("4 por hacer");
    expect(TEXTOS.porHacer(999)).toBe("999 por hacer");
    expect(TEXTOS.porHacer(1234)).toBe("1.234 por hacer");
  });

  test("el resumen por urgencia", () => {
    expect(TEXTOS.resumen(2, 2)).toBe("2 bloquean · 2 avisos");
    expect(TEXTOS.resumen(1, 1)).toBe("1 bloquea · 1 aviso");
    expect(TEXTOS.resumen(1200, 3500)).toBe("1.200 bloquean · 3.500 avisos");
    expect(TEXTOS.resumen(0, 1000)).toBe("1.000 avisos");
  });

  test("las carpetas que no se pudieron leer", () => {
    expect(TEXTOS.omitidas(1)).toBe("No se pudo leer 1 carpeta; sus pendientes no aparecen.");
    expect(TEXTOS.omitidas(2)).toBe("No se pudieron leer 2 carpetas; sus pendientes no aparecen.");
    expect(TEXTOS.omitidas(1500)).toBe("No se pudieron leer 1.500 carpetas; sus pendientes no aparecen.");
  });
});
