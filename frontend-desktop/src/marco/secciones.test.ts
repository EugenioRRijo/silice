import { describe, expect, it } from "vitest";
import { paginaPorId } from "../shell/rutas";
import {
  ENTRADAS_DE_EMPRESA,
  PATRON_DE_EMPRESA,
  PATRON_DE_OBRA,
  RUTA_DE_PENDIENTES,
  SECCIONES_DE_OBRA,
  carpetaDeLaRuta,
  rutaDeEmpresa,
  rutaDeObra,
  seccionPorId,
} from "./secciones";

const PROHIBIDAS = /m[oó]dulo|[aá]rea|p[aá]gina|streamlit|carpeta de trabajo/i;

describe("SECCIONES_DE_OBRA", () => {
  it("son las siete, en este orden", () => {
    expect(SECCIONES_DE_OBRA.map((s) => s.id)).toEqual([
      "resumen",
      "presupuesto",
      "archivos",
      "versiones",
      "aprobaciones",
      "mercado",
      "control",
    ]);
  });

  it("montan las pantallas de hoy por su id del registro", () => {
    expect(Object.fromEntries(SECCIONES_DE_OBRA.map((s) => [s.id, s.pagina]))).toEqual({
      resumen: "obras",
      presupuesto: "hoja",
      archivos: null,
      versiones: null,
      aprobaciones: "aprobar",
      mercado: "mercado",
      control: "control",
    });
    for (const s of SECCIONES_DE_OBRA) {
      if (s.pagina !== null) expect(paginaPorId(s.pagina), s.id).toBeDefined();
    }
  });

  it("hablan en el vocabulario de la persona, con una ayuda corta", () => {
    for (const s of SECCIONES_DE_OBRA) {
      expect(s.titulo, s.id).not.toMatch(PROHIBIDAS);
      expect(s.ayuda, s.id).not.toMatch(PROHIBIDAS);
      expect(s.ayuda.length, s.id).toBeGreaterThan(0);
      expect(s.ayuda.length, s.id).toBeLessThanOrEqual(90);
    }
  });

  it("se buscan por id; uno desconocido no es seccion", () => {
    expect(seccionPorId("presupuesto")?.titulo).toBe("Presupuesto");
    expect(seccionPorId("tablero")).toBeUndefined();
    expect(seccionPorId("toString")).toBeUndefined();
  });
});

describe("ENTRADAS_DE_EMPRESA", () => {
  it("son cinco, en este orden, cada una con su pantalla de hoy", () => {
    expect(ENTRADAS_DE_EMPRESA.map((e) => [e.titulo, e.pagina])).toEqual([
      ["Precios y catálogo", "catalogo"],
      ["Auditar un presupuesto", "auditoria"],
      ["Producción", "existencias"],
      ["Empresa y personas", "administracion"],
      ["Ayuda", "acerca"],
    ]);
    for (const e of ENTRADAS_DE_EMPRESA) expect(paginaPorId(e.pagina), e.id).toBeDefined();
    expect(new Set(ENTRADAS_DE_EMPRESA.map((e) => e.id)).size).toBe(ENTRADAS_DE_EMPRESA.length);
  });

  it("hablan en el vocabulario de la persona, con una ayuda corta", () => {
    for (const e of ENTRADAS_DE_EMPRESA) {
      expect(e.titulo, e.id).not.toMatch(PROHIBIDAS);
      expect(e.ayuda, e.id).not.toMatch(PROHIBIDAS);
      expect(e.ayuda.length, e.id).toBeGreaterThan(0);
      expect(e.ayuda.length, e.id).toBeLessThanOrEqual(90);
    }
  });
});

describe("rutas del marco", () => {
  it("la obra lleva su carpeta con el .db, codificada", () => {
    expect(rutaDeObra("Carpeta Sur.db", 3, "presupuesto")).toBe("/obra/Carpeta%20Sur.db/3/presupuesto");
    expect(rutaDeObra("50% & más.db", 7, "control")).toBe("/obra/50%25%20%26%20m%C3%A1s.db/7/control");
  });

  it("la carpeta de la empresa se escribe «empresa»", () => {
    expect(rutaDeObra(null, 1, "resumen")).toBe("/obra/empresa/1/resumen");
    expect(carpetaDeLaRuta("empresa")).toBeNull();
    expect(carpetaDeLaRuta("Carpeta Sur.db")).toBe("Carpeta Sur.db");
  });

  it("pendientes y las entradas de la empresa", () => {
    expect(RUTA_DE_PENDIENTES).toBe("/pendientes");
    expect(rutaDeEmpresa("precios")).toBe("/empresa/precios");
    expect(PATRON_DE_OBRA).toBe("/obra/:carpeta/:obraId/:seccion");
    expect(PATRON_DE_EMPRESA).toBe("/empresa/:entrada");
  });
});
