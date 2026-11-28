import { describe, expect, it } from "vitest";
import { catalogoDePrueba } from "../paginas/auditoria/datosDePrueba";
import { guiaDeAlerta, guiaDeRegla, leerCatalogoQueHacer } from "./catalogoQueHacer";

describe("leerCatalogoQueHacer", () => {
  it("acepta la respuesta del servidor", () => {
    const c = catalogoDePrueba();
    expect(leerCatalogoQueHacer(JSON.parse(JSON.stringify(c)))).toEqual(c);
  });

  it("rechaza lo que no es un catálogo", () => {
    expect(() => leerCatalogoQueHacer(null)).toThrow();
    expect(() => leerCatalogoQueHacer({})).toThrow();
    expect(() => leerCatalogoQueHacer({ reglas: {}, alertas: {} })).toThrow();
  });

  it("rechaza una guía sin su «qué hacer»", () => {
    const c = JSON.parse(JSON.stringify(catalogoDePrueba())) as { reglas: Record<string, Record<string, unknown>> };
    delete c.reglas.L1.que_hacer;
    expect(() => leerCatalogoQueHacer(c)).toThrow(/L1/);
  });

  it("rechaza una guía con un tipo equivocado", () => {
    const c = JSON.parse(JSON.stringify(catalogoDePrueba())) as { alertas: Record<string, Record<string, unknown>> };
    c.alertas["USD-Bs"].sin_aviso_si = "dentro del umbral";
    expect(() => leerCatalogoQueHacer(c)).toThrow(/USD-Bs/);
  });
});

describe("guiaDeRegla y guiaDeAlerta", () => {
  const c = catalogoDePrueba();

  it("dan la guía propia del código", () => {
    expect(guiaDeRegla(c, "L4").titulo).toBe("Componente fuera del total");
    expect(guiaDeAlerta(c, "sin fuente").codigo).toBe("alerta:sin-fuente");
  });

  it("un código que no se conoce recibe la genérica, marcada, con su código", () => {
    const g = guiaDeRegla(c, "ZZ9");
    expect(g.generico).toBe(true);
    expect(g.codigo).toBe("ZZ9");
    expect(g.que_hacer).toBe(c.generico.que_hacer);
    expect(guiaDeAlerta(c, "rara").generico).toBe(true);
  });
});
