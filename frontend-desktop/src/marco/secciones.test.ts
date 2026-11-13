import { describe, expect, it } from "vitest";
import { paginaPorId } from "../shell/rutas";
import { ofertaDe } from "./oferta";
import * as todo from "./secciones";
import {
  PATRON_DE_OBRA,
  RUTA_DE_PENDIENTES,
  SECCIONES_DE_OBRA,
  carpetaDeLaRuta,
  quedaEnLaHoja,
  rutaDeObra,
  seccionPorId,
} from "./secciones";

// Palabras enteras: «tarea» no es «área».
const PROHIBIDAS = /(?<!\p{L})(m[oó]dulos?|[aá]reas?|p[aá]ginas?|streamlit|carpetas? de trabajo)(?!\p{L})/iu;

describe("SECCIONES_DE_OBRA", () => {
  it("la lista de palabras prohibidas las reconoce enteras", () => {
    for (const t of ["el módulo", "Área de obra", "las áreas", "una página", "Streamlit", "carpeta de trabajo"]) {
      expect(t).toMatch(PROHIBIDAS);
    }
    expect("cada tarea").not.toMatch(PROHIBIDAS);
  });

  it("son las nueve (con «Riesgo»), en este orden", () => {
    expect(SECCIONES_DE_OBRA.map((s) => s.id)).toEqual([
      "resumen",
      "presupuesto",
      "tramos",
      "archivos",
      "versiones",
      "aprobaciones",
      "mercado",
      "control",
      "riesgo",
    ]);
  });

  it("montan las pantallas de hoy por su id del registro", () => {
    expect(Object.fromEntries(SECCIONES_DE_OBRA.map((s) => [s.id, s.pagina]))).toEqual({
      resumen: "obras",
      presupuesto: "hoja",
      tramos: "tramos",
      archivos: "archivos",
      versiones: "versiones",
      aprobaciones: "aprobar",
      mercado: "mercado",
      control: "control",
      riesgo: "riesgo",
    });
    for (const s of SECCIONES_DE_OBRA) {
      if (s.pagina !== null) expect(paginaPorId(s.pagina), s.id).toBeDefined();
    }
  });

  it("«Versiones» tiene su pantalla (Tarea 6 del plan F4) y aparece en el árbol de quien lee la obra", () => {
    expect(seccionPorId("versiones")?.pagina).toBe("versiones");
    expect(paginaPorId("versiones")?.accion).toBe("leer_proyecto");
    expect(ofertaDe(["leer_proyecto"], false).secciones.map((s) => s.id)).toContain("versiones");
    expect(ofertaDe([], false).secciones.map((s) => s.id)).not.toContain("versiones");
  });

  it("«Tramos» es una sección como las demás: toda obra la tiene mientras el módulo vial esté encendido", () => {
    expect(SECCIONES_DE_OBRA.map((s) => s.id)).toContain("tramos");
    expect(Object.keys(SECCIONES_DE_OBRA[0]!)).not.toContain("soloVial");
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

// F6, T6: «Empresa y personas» y «Ayuda» pasaron a la Cuenta (`espacios.ts`, SECCIONES_DE_CUENTA): ya no hay entradas de Empresa.
describe("la zona Empresa ya no existe", () => {
  it("secciones.ts no exporta entradas de Empresa ni sus rutas", () => {
    for (const nombre of ["ENTRADAS_DE_EMPRESA", "PATRON_DE_EMPRESA", "rutaDeEmpresa"]) {
      expect(nombre in todo, nombre).toBe(false);
    }
  });
});

describe("rutas del marco", () => {
  it("la obra lleva su carpeta con el .db, codificada", () => {
    expect(rutaDeObra("Carpeta Sur.db", 3, "presupuesto")).toBe("/obra/Carpeta%20Sur.db/3/presupuesto");
    expect(rutaDeObra("50% & más.db", 7, "control")).toBe("/obra/50%25%20%26%20m%C3%A1s.db/7/control");
  });

  // F6, T5: la subvista es un cuarto segmento (contrato de rutas 2.1); sin ella, la ruta de siempre.
  it("una subvista agrega su segmento a la ruta de la sección, con la carpeta codificada", () => {
    expect(rutaDeObra("Carpeta Sur.db", 3, "control", "reajuste")).toBe("/obra/Carpeta%20Sur.db/3/control/reajuste");
    expect(rutaDeObra(null, 1, "presupuesto", "componer")).toBe("/obra/empresa/1/presupuesto/componer");
    expect(rutaDeObra(null, 1, "presupuesto", "")).toBe("/obra/empresa/1/presupuesto");
    expect(rutaDeObra(null, 1, "presupuesto", undefined)).toBe("/obra/empresa/1/presupuesto");
  });

  it("la carpeta de la empresa se escribe «empresa»", () => {
    expect(rutaDeObra(null, 1, "resumen")).toBe("/obra/empresa/1/resumen");
    expect(carpetaDeLaRuta("empresa")).toBeNull();
    expect(carpetaDeLaRuta("Carpeta Sur.db")).toBe("Carpeta Sur.db");
  });

  it("pendientes y el patrón de la obra", () => {
    // F6, T8 (contrato 2.4): Pendientes vive en el espacio Inicio; `/pendientes` quedó como dirección vieja que redirige.
    expect(RUTA_DE_PENDIENTES).toBe("/inicio/pendientes");
    expect(PATRON_DE_OBRA).toBe("/obra/:carpeta/:obraId/:seccion/:subvista?");
  });
});

// Nota H-F6-1 de Antigravity: `quedaEnLaHoja` compara el segmento de la sección y no la ruta entera, para que pasar de
// Presupuesto a Componer (`/presupuesto` a `/presupuesto/componer`) no pregunte por cambios sin guardar. Oráculos a mano.
describe("quedaEnLaHoja (F6, T5)", () => {
  const OBRA = "/obra/Carpeta%20Sur.db/3";

  it.each(["presupuesto", "archivos", "versiones"])("%s, de la misma obra, queda en la Hoja", (seccion) => {
    expect(quedaEnLaHoja(`${OBRA}/${seccion}`, "Carpeta Sur.db", 3)).toBe(true);
  });

  it("una subvista de una sección con Hoja (Componer) también queda en la Hoja", () => {
    expect(quedaEnLaHoja(`${OBRA}/presupuesto/componer`, "Carpeta Sur.db", 3)).toBe(true);
  });

  it("la consulta y el ancla no cuentan", () => {
    expect(quedaEnLaHoja(`${OBRA}/presupuesto?version=001`, "Carpeta Sur.db", 3)).toBe(true);
    expect(quedaEnLaHoja(`${OBRA}/presupuesto/componer?codigo=X#fila`, "Carpeta Sur.db", 3)).toBe(true);
  });

  it("las secciones sin Hoja, y sus subvistas, no quedan en ella", () => {
    for (const destino of ["resumen", "resumen/tablero", "control/reajuste", "mercado/actualizar", "aprobaciones/revisar", "tramos", "riesgo"]) {
      expect(quedaEnLaHoja(`${OBRA}/${destino}`, "Carpeta Sur.db", 3), destino).toBe(false);
    }
  });

  it("otra obra o otra carpeta no queda en la Hoja de esta", () => {
    expect(quedaEnLaHoja("/obra/Carpeta%20Sur.db/4/presupuesto", "Carpeta Sur.db", 3)).toBe(false);
    expect(quedaEnLaHoja("/obra/Carpeta%20Norte.db/3/presupuesto/componer", "Carpeta Sur.db", 3)).toBe(false);
    expect(quedaEnLaHoja("/obra/empresa/3/presupuesto", "Carpeta Sur.db", 3)).toBe(false);
    expect(quedaEnLaHoja("/obra/empresa/3/presupuesto/componer", null, 3)).toBe(true);
  });

  it("un segmento que solo empieza igual no cuenta (presupuestos no es presupuesto)", () => {
    expect(quedaEnLaHoja(`${OBRA}/presupuestos`, "Carpeta Sur.db", 3)).toBe(false);
    expect(quedaEnLaHoja(`${OBRA}/versiones2/componer`, "Carpeta Sur.db", 3)).toBe(false);
  });

  it("fuera de una obra no queda en la Hoja", () => {
    expect(quedaEnLaHoja("/pendientes", "Carpeta Sur.db", 3)).toBe(false);
    expect(quedaEnLaHoja("/precios/catalogo", "Carpeta Sur.db", 3)).toBe(false);
  });
});
