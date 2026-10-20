import { describe, expect, test } from "vitest";
import {
  PESTANAS,
  SIN_VERSIONES,
  esBorradorAusente,
  rotuloDeVersion,
  rutaDeVersiones,
  textoDeCambios,
  versionesOfrecidas,
} from "./logica";
import type { VersionFila } from "./logica";
import { ErrorDeApi } from "../../api/cliente";

function version(codigo: string, extra: Partial<VersionFila> = {}): VersionFila {
  return {
    codigo,
    fecha: "2026-10-05",
    motivo: "",
    origen: "",
    vigente: false,
    descartada: false,
    cambios: 0,
    ...extra,
  };
}

describe("lógica de la hoja del proyecto", () => {
  test("las nueve pestañas van en el orden de la página clásica", () => {
    expect(PESTANAS).toEqual([
      "Espacio y metrajes",
      "APU",
      "Presupuesto",
      "Plan y curva",
      "Punto de equilibrio",
      "Precios",
      "Parámetros",
      "Auditoría",
      "Trazabilidad",
    ]);
  });

  test("el proyecto va codificado en la ruta de versiones", () => {
    expect(rutaDeVersiones("OF-001: oficina & baño")).toBe(
      "/v1/hoja/versiones?proyecto=OF-001%3A%20oficina%20%26%20ba%C3%B1o",
    );
  });

  test("se ofrecen las versiones no descartadas; si todas lo están, todas", () => {
    const a = version("001");
    const b = version("002", { vigente: true });
    const c = version("003", { descartada: true });
    expect(versionesOfrecidas([a, b, c]).map((v) => v.codigo)).toEqual(["001", "002"]);
    expect(versionesOfrecidas([{ ...a, descartada: true }, c]).map((v) => v.codigo)).toEqual(["001", "003"]);
    expect(versionesOfrecidas([])).toEqual([]);
  });

  test("la vigente se rotula con ' (vigente)' y las demás con su código", () => {
    expect(rotuloDeVersion(version("002", { vigente: true }))).toBe("002 (vigente)");
    expect(rotuloDeVersion(version("001"))).toBe("001");
  });

  test("los cambios sin guardar se dicen en singular y plural", () => {
    expect(textoDeCambios(0)).toBe("Sin cambios sin guardar");
    expect(textoDeCambios(1)).toBe("1 cambio sin guardar");
    expect(textoDeCambios(3)).toBe("3 cambios sin guardar");
  });

  test("el aviso de proyecto sin versiones lleva tilde", () => {
    expect(SIN_VERSIONES).toBe("Este proyecto aún no tiene versiones");
  });

  test("solo el 404 de 'ya no está en el servidor' es un borrador ausente", () => {
    const ausente = new ErrorDeApi(404, "Ese borrador ya no está en el servidor (se reinició Sílice).");
    expect(esBorradorAusente(ausente)).toBe(true);
    expect(esBorradorAusente(new ErrorDeApi(404, "El proyecto «Z» no existe en este caso."))).toBe(false);
    expect(esBorradorAusente(new ErrorDeApi(500, "Ese borrador ya no está"))).toBe(false);
    expect(esBorradorAusente("otra cosa")).toBe(false);
  });
});
