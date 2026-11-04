import { describe, expect, test } from "vitest";
import { rutaCanonica, rutaOPendientes } from "./espacios";

// Plan F6, T1: una sola función dice a qué ruta lleva cada pantalla; quien enlaza (recorridos, buscador, pendientes,
// botones de las pantallas) la usa y no escribe rutas a mano. Oráculos escritos a mano, no derivados de PAGINAS.
describe("rutaCanonica", () => {
  test("una sección de obra, con la obra, va a la ruta de esa obra", () => {
    expect(rutaCanonica("hoja", { carpeta: "demo.db", obraId: 1 })).toBe("/obra/demo.db/1/presupuesto");
    expect(rutaCanonica("tramos", { carpeta: "Carpeta Norte.db", obraId: 7 })).toBe("/obra/Carpeta%20Norte.db/7/tramos");
    expect(rutaCanonica("obras", { carpeta: "demo.db", obraId: 2 })).toBe("/obra/demo.db/2/resumen");
    expect(rutaCanonica("aprobar", { carpeta: "demo.db", obraId: 2 })).toBe("/obra/demo.db/2/aprobaciones");
  });

  test("la obra de la empresa (sin carpeta) se escribe «empresa»", () => {
    expect(rutaCanonica("hoja", { carpeta: null, obraId: 1 })).toBe("/obra/empresa/1/presupuesto");
  });

  test("una sección de obra sin obra va a su dirección corta, que redirige a la obra de la sesión", () => {
    expect(rutaCanonica("hoja")).toBe("/hoja");
    expect(rutaCanonica("mercado")).toBe("/mercado");
  });

  test("una entrada de empresa va a /empresa/<entrada>, con o sin obra", () => {
    expect(rutaCanonica("catalogo")).toBe("/empresa/precios");
    expect(rutaCanonica("auditoria")).toBe("/empresa/auditoria");
    expect(rutaCanonica("existencias")).toBe("/empresa/produccion");
    expect(rutaCanonica("administracion")).toBe("/empresa/personas");
    expect(rutaCanonica("acerca")).toBe("/empresa/ayuda");
    expect(rutaCanonica("auditoria", { carpeta: "demo.db", obraId: 1 })).toBe("/empresa/auditoria");
  });

  test("las demás pantallas conservan su dirección /<id>", () => {
    expect(rutaCanonica("costos")).toBe("/costos");
    expect(rutaCanonica("libros")).toBe("/libros");
    expect(rutaCanonica("historial")).toBe("/historial");
    expect(rutaCanonica("receta_planta")).toBe("/receta_planta");
    expect(rutaCanonica("produccion")).toBe("/produccion");
    expect(rutaCanonica("costos", { carpeta: "demo.db", obraId: 1 })).toBe("/costos");
  });

  test("un id desconocido da null (también los que son propiedades de Object)", () => {
    expect(rutaCanonica("inexistente")).toBeNull();
    expect(rutaCanonica("")).toBeNull();
    expect(rutaCanonica("toString")).toBeNull();
  });
});

describe("rutaOPendientes", () => {
  test("da la ruta canónica y, si el id no es pantalla, nunca un enlace muerto: lleva a Pendientes", () => {
    expect(rutaOPendientes("existencias")).toBe("/empresa/produccion");
    expect(rutaOPendientes("hoja", { carpeta: "demo.db", obraId: 1 })).toBe("/obra/demo.db/1/presupuesto");
    expect(rutaOPendientes("inexistente")).toBe("/pendientes");
  });
});

