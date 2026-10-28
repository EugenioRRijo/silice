import { describe, expect, it } from "vitest";
import { obrasConMismoNombre } from "./homonimas";

const fila = (carpeta: string | null, obra_id: number, obra: string, carpeta_titulo: string) => ({
  carpeta,
  obra_id,
  obra,
  carpeta_titulo,
});

describe("obrasConMismoNombre (D-F3-3)", () => {
  it("sin nombres repetidos no marca ninguna obra", () => {
    const m = obrasConMismoNombre([fila("a.db", 1, "Clínica", "Norte"), fila("b.db", 1, "Torre", "Sur")]);
    expect(m.size).toBe(0);
  });

  it("dos obras con el mismo nombre en carpetas distintas devuelven la carpeta de cada una, por carpeta y número", () => {
    const m = obrasConMismoNombre([
      fila("a.db", 1, "Galpón", "Norte"),
      fila(null, 1, "Galpón", "Carpeta de la empresa"),
      fila("a.db", 2, "Clínica", "Norte"),
    ]);
    expect(m.get("a.db|1")).toBe("Norte");
    expect(m.get("|1")).toBe("Carpeta de la empresa");
    expect(m.has("a.db|2")).toBe(false);
    expect(m.size).toBe(2);
  });

  it("no distingue mayúsculas ni espacios de más al comparar", () => {
    const m = obrasConMismoNombre([fila("a.db", 1, "Galpón Sur", "Norte"), fila("b.db", 2, "  galpón sur ", "Sur")]);
    expect([...m.keys()].sort()).toEqual(["a.db|1", "b.db|2"]);
  });

  it("dos con el mismo nombre en la misma carpeta no se marcan: la carpeta no las distingue", () => {
    const m = obrasConMismoNombre([fila("a.db", 1, "Galpón", "Norte"), fila("a.db", 2, "Galpón", "Norte")]);
    expect(m.size).toBe(0);
  });

  it("tres con el mismo nombre en dos carpetas marcan las tres", () => {
    const m = obrasConMismoNombre([
      fila("a.db", 1, "Galpón", "Norte"),
      fila("a.db", 2, "Galpón", "Norte"),
      fila("b.db", 1, "Galpón", "Sur"),
    ]);
    expect(m.size).toBe(3);
  });

  it("un doble espacio interno no distingue", () => {
    const m = obrasConMismoNombre([fila("a.db", 1, "Galpón  Sur", "Norte"), fila("b.db", 2, "Galpón Sur", "Sur")]);
    expect(m.size).toBe(2);
  });

  it("«Galpón» escrito en NFD y en NFC es el mismo nombre", () => {
    const m = obrasConMismoNombre([
      fila("a.db", 1, "Galpón", "Norte"),
      fila("b.db", 2, "Galpón", "Sur"),
    ]);
    expect(m.size).toBe(2);
  });

  it("«Galpón» frente a «Galpon» sigue siendo distinto", () => {
    const m = obrasConMismoNombre([fila("a.db", 1, "Galpón", "Norte"), fila("b.db", 2, "Galpon", "Sur")]);
    expect(m.size).toBe(0);
  });
});
