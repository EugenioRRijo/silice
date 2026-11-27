import { describe, expect, it, test } from "vitest";
import { SUBVISTAS } from "./espacios";
import { HERRAMIENTAS_DE_OBRA, OPCIONES_DE_HERRAMIENTA, herramientaDe, opcionActual, primeraRutaDe, rutaDeOpcion, seccionConSubvistasPropias } from "./herramientas";
import type { Herramienta } from "./herramientas";
import { SECCIONES_DE_OBRA, rutaDeObra } from "./secciones";
import type { SeccionId } from "./secciones";

// Oráculo escrito a mano: la herramienta de cada sección según la especificación 2026-11-26 (barra del lugar).
const ESPERADO: Record<SeccionId, Herramienta> = {
  resumen: "portada",
  presupuesto: "presupuestar",
  tramos: "presupuestar",
  archivos: "presupuestar",
  mercado: "presupuestar",
  aprobaciones: "auditar",
  control: "anticipar",
  riesgo: "anticipar",
  versiones: "versiones",
};

describe("herramientaDe", () => {
  it.each(Object.entries(ESPERADO))("la sección %s cae en %s", (seccion, herramienta) => {
    expect(herramientaDe(seccion as SeccionId)).toBe(herramienta);
  });

  it.each([
    ["resumen", "tablero", "portada"],
    ["presupuesto", "componer", "presupuestar"],
    ["mercado", "actualizar", "presupuestar"],
    ["aprobaciones", "revisar", "auditar"],
    ["aprobaciones", "entregar", "auditar"],
    ["control", "reajuste", "anticipar"],
    ["control", "escenarios", "anticipar"],
  ] as const)("la subvista %s/%s cae en %s", (seccion, subvista, herramienta) => {
    expect(herramientaDe(seccion, subvista)).toBe(herramienta);
  });

  it("toda subvista declarada en SUBVISTAS cae en la herramienta de su sección", () => {
    for (const [seccion, vistas] of Object.entries(SUBVISTAS)) {
      for (const v of vistas ?? []) expect(herramientaDe(seccion as SeccionId, v.id)).toBe(ESPERADO[seccion as SeccionId]);
    }
  });

  it("ninguna sección de SECCIONES_DE_OBRA queda sin herramienta", () => {
    for (const s of SECCIONES_DE_OBRA) expect(Object.keys(ESPERADO)).toContain(s.id);
    expect(SECCIONES_DE_OBRA.map((s) => herramientaDe(s.id)).every((h) => h !== undefined)).toBe(true);
  });
});

describe("HERRAMIENTAS_DE_OBRA", () => {
  it("son tres, en este orden", () => {
    expect(HERRAMIENTAS_DE_OBRA.map((h) => [h.id, h.titulo])).toEqual([
      ["presupuestar", "Presupuestar"],
      ["auditar", "Auditar"],
      ["anticipar", "Anticipar"],
    ]);
  });

  it("reparten todas las secciones menos Resumen y Versiones, sin repetir ninguna", () => {
    const repartidas = HERRAMIENTAS_DE_OBRA.flatMap((h) => h.secciones);
    expect([...repartidas].sort()).toEqual(["aprobaciones", "archivos", "control", "mercado", "presupuesto", "riesgo", "tramos"]);
  });
});

describe("primeraRutaDe", () => {
  it("da la ruta de la primera sección de cada herramienta", () => {
    expect(primeraRutaDe("presupuestar", "a.db", 3)).toBe(rutaDeObra("a.db", 3, "presupuesto"));
    expect(primeraRutaDe("auditar", "a.db", 3)).toBe(rutaDeObra("a.db", 3, "aprobaciones"));
    expect(primeraRutaDe("anticipar", "a.db", 3)).toBe(rutaDeObra("a.db", 3, "control"));
    expect(primeraRutaDe("portada", "a.db", 3)).toBe(rutaDeObra("a.db", 3, "resumen"));
    expect(primeraRutaDe("versiones", "a.db", 3)).toBe(rutaDeObra("a.db", 3, "versiones"));
  });

  it("la carpeta de la empresa (null) va como «empresa»", () => {
    expect(primeraRutaDe("presupuestar", null, 7)).toBe("/obra/empresa/7/presupuesto");
  });

  it("con las secciones que la cuenta puede usar, salta la primera que no puede", () => {
    expect(primeraRutaDe("presupuestar", null, 7, ["tramos", "mercado"])).toBe("/obra/empresa/7/tramos");
    expect(primeraRutaDe("anticipar", null, 7, ["riesgo"])).toBe("/obra/empresa/7/riesgo");
  });

  it("sin ninguna sección usable da null", () => {
    expect(primeraRutaDe("auditar", null, 7, ["presupuesto"])).toBeNull();
  });
});

describe("OPCIONES_DE_HERRAMIENTA (la segunda fila de la barra de la obra)", () => {
  const titulos = (h: keyof typeof OPCIONES_DE_HERRAMIENTA) => OPCIONES_DE_HERRAMIENTA[h].map((o) => o.titulo);

  it("cada herramienta trae las opciones acordadas, en orden", () => {
    expect(titulos("presupuestar")).toEqual(["Partidas", "Componer un APU", "Espacio, plan y ajustes", "Tramos de la vía", "Plano o cómputo", "Precios de mercado"]);
    expect(titulos("auditar")).toEqual(["Aprobar", "Revisar un paquete", "Entregar"]);
    expect(titulos("anticipar")).toEqual(["Control de obra", "Reajuste de precios", "Escenarios", "Riesgo"]);
    expect(titulos("portada")).toEqual(["Resumen", "Tablero"]);
  });

  it("sus rutas son las de siempre", () => {
    const rutas = (h: keyof typeof OPCIONES_DE_HERRAMIENTA) => OPCIONES_DE_HERRAMIENTA[h].map((o) => rutaDeOpcion(o, "a.db", 3));
    expect(rutas("presupuestar")).toEqual([
      "/obra/a.db/3/presupuesto",
      "/obra/a.db/3/presupuesto/componer",
      "/obra/a.db/3/presupuesto/pestanas",
      "/obra/a.db/3/tramos",
      "/obra/a.db/3/archivos",
      "/obra/a.db/3/mercado",
    ]);
    expect(rutas("auditar")).toEqual(["/obra/a.db/3/aprobaciones", "/obra/a.db/3/aprobaciones/revisar", "/obra/a.db/3/aprobaciones/entregar"]);
    expect(rutas("anticipar")).toEqual(["/obra/a.db/3/control", "/obra/a.db/3/control/reajuste", "/obra/a.db/3/control/escenarios", "/obra/a.db/3/riesgo"]);
    expect(rutas("portada")).toEqual(["/obra/a.db/3/resumen", "/obra/a.db/3/resumen/tablero"]);
  });

  it("cada opción cae en la herramienta que la lista, y toda subvista de SUBVISTAS (menos Versiones) tiene opción", () => {
    for (const [herramienta, opciones] of Object.entries(OPCIONES_DE_HERRAMIENTA)) {
      for (const o of opciones) expect(herramientaDe(o.seccion, o.subvista)).toBe(herramienta);
    }
    const todas = Object.values(OPCIONES_DE_HERRAMIENTA).flat();
    for (const s of SECCIONES_DE_OBRA.filter((s) => s.id !== "versiones")) {
      expect(todas.some((o) => o.seccion === s.id && o.subvista === "")).toBe(true);
    }
    for (const [seccion, vistas] of Object.entries(SUBVISTAS)) {
      for (const v of (vistas ?? []).filter((v) => v.id !== "" && v.id !== "actualizar")) {
        expect(todas.some((o) => o.seccion === seccion && o.subvista === v.id)).toBe(true);
      }
    }
  });

  it("opcionActual: exacta, o la principal de la sección si la subvista no tiene opción, o ninguna en Versiones", () => {
    expect(opcionActual("presupuestar", "presupuesto", "componer")?.titulo).toBe("Componer un APU");
    expect(opcionActual("presupuestar", "mercado", "actualizar")?.titulo).toBe("Precios de mercado");
    expect(opcionActual("anticipar", "control")?.titulo).toBe("Control de obra");
    expect(opcionActual("portada", "resumen", "tablero")?.titulo).toBe("Tablero");
    expect(opcionActual("versiones", "versiones")).toBeUndefined();
  });
});

// Integración C3-C5: la barra de subvistas «Vistas de …» solo queda donde la segunda fila de la obra no las cubre.
describe("seccionConSubvistasPropias", () => {
  test("solo Mercado (Actualizar precios) conserva su barra de subvistas", () => {
    expect(seccionConSubvistasPropias("mercado")).toBe(true);
    for (const s of ["resumen", "presupuesto", "aprobaciones", "control", "riesgo", "tramos", "archivos", "versiones"] as const) {
      expect(seccionConSubvistasPropias(s)).toBe(false);
    }
  });
});
