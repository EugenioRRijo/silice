import { describe, expect, test } from "vitest";
import { SEVERIDADES, estiloDeSeveridad, normalizarSeveridad } from "./severidad";

describe("severidad (fuente unica)", () => {
  test("el orden es de mas a menos grave", () => {
    expect(SEVERIDADES).toEqual(["CRITICO", "ERROR", "ADVERTENCIA", "INFO"]);
  });

  test("cada severidad tiene token, icono y texto", () => {
    expect(estiloDeSeveridad("CRITICO")).toEqual({
      token: "--silice-sev-critico",
      icono: "ErrorFilled",
      texto: "Crítico",
    });
    expect(estiloDeSeveridad("ADVERTENCIA").icono).toBe("WarningAltFilled");
  });

  test("una severidad desconocida es Informacion", () => {
    expect(normalizarSeveridad("RARA")).toBe("INFO");
    expect(normalizarSeveridad("ERROR")).toBe("ERROR");
  });
});
