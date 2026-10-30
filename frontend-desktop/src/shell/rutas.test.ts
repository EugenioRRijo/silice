import { describe, expect, test } from "vitest";
import * as rutas from "./rutas";
import { PAGINAS, SECCIONES, paginaPorId, rutaDe, usable } from "./rutas";

// Oraculo escrito a mano: la seccion y la accion de cada pantalla de ui/app.py y de seguridad/permisos.py, en su orden.
// Dónde se ve cada una ya no lo dice el registro sino el marco (marco/secciones.ts y el buscador).
const REGISTRO: [string, string, string | null][] = [
  ["auditoria", "Revisión", null],
  ["libros", "Revisión", "leer_proyecto"],
  ["revisar", "Revisión", "revisar_paquete"],
  ["historial", "Revisión", "leer_proyecto"],
  ["obras", "Trabajo", null],
  ["hoja", "Trabajo", "editar_hoja"],
  ["elaborar", "Trabajo", "editar_hoja"],
  ["tablero", "Trabajo", "leer_proyecto"],
  ["entregar", "Trabajo", "entregar_paquete"],
  ["componer", "Trabajo", "editar_hoja"],
  ["catalogo", "Trabajo", "leer_proyecto"],
  ["similares", "Investigación", "editar_hoja"],
  ["mercado", "Trabajo", "editar_hoja"],
  ["precios_empresa", "Trabajo", "administrar_precios"],
  ["actualizacion", "Trabajo", "editar_hoja"],
  ["historico", "Trabajo", "leer_proyecto"],
  ["indices", "Trabajo", "administrar_precios"],
  ["simulador", "Investigación", "editar_hoja"],
  ["aprobar", "Revisión", "aprobar_version"],
  ["control", "Trabajo", "control_de_obra"],
  ["reajuste", "Trabajo", "convertir_y_reajustar"],
  ["escenarios", "Investigación", "editar_hoja"],
  // Sin su módulo, el inicio de producción exige lo mismo que la arenera (Tarea 8 del plan del marco).
  ["produccion", "Trabajo", "operar_arenera"],
  ["existencias", "Trabajo", "operar_arenera"],
  // Plan vial, Tarea 2: los costos del periodo los registra quien arma o administra (API: registrar_costos_produccion).
  ["costos", "Trabajo", "registrar_costos_produccion"],
  // Plan vial, Tarea 6: la receta la registra quien opera la arenera; el costo por tonelada, quien registra costos.
  ["receta_planta", "Trabajo", "operar_arenera"],
  ["costo_tonelada", "Trabajo", "registrar_costos_produccion"],
  ["administracion", "Administración", "administrar_cuentas"],
  ["acerca", "Trabajo", null],
];

const RITA = ["leer_proyecto", "revisar_paquete", "aprobar_version"];

describe("registro de paginas", () => {
  test("tiene las 29 pantallas en su orden, con su seccion y su accion", () => {
    expect(PAGINAS.map((p) => [p.id, p.seccion, p.accion])).toEqual(REGISTRO);
  });

  test("ya no existe la pantalla «inicio»: la direccion /inicio solo redirige", () => {
    expect(paginaPorId("inicio")).toBeUndefined();
  });

  test("los ids son unicos y las secciones de permisos son cuatro", () => {
    expect(new Set(PAGINAS.map((p) => p.id)).size).toBe(PAGINAS.length);
    expect(SECCIONES).toEqual(["Trabajo", "Revisión", "Investigación", "Administración"]);
  });

  test("toda pagina del registro carga su pantalla", () => {
    expect(PAGINAS.every((p) => typeof p.cargar === "function")).toBe(true);
    expect(paginaPorId("libros")?.titulo).toBe("Libro de la empresa");
    expect(paginaPorId("hoja")).toMatchObject({ titulo: "Hoja de la obra", seccion: "Trabajo", accion: "editar_hoja" });
    expect(paginaPorId("mercado")).toMatchObject({
      titulo: "Estudio de mercado",
      enUnaLinea: "Compare precios del mercado y elija los suyos",
    });
    expect(paginaPorId("aprobar")).toMatchObject({
      titulo: "Aprobar una versión",
      enUnaLinea: "Revise y dé su dictamen sobre una versión",
    });
  });

  // Plan del rediseño del marco, Tarea 8: el marco nuevo reemplaza a los módulos; el registro ya no los conoce.
  test("se retiran los módulos, sus áreas y sus inicios", () => {
    for (const nombre of ["MODULOS", "inicioDe", "modulosVisibles", "fueraDeModulos", "moduloDePagina", "visible"]) {
      expect(nombre in rutas, nombre).toBe(false);
    }
    expect(PAGINAS.some((p) => "ubicacion" in p)).toBe(false);
  });

  test("la ruta de una pagina es su id", () => {
    expect(rutaDe(paginaPorId("libros")!)).toBe("/libros");
    expect(rutaDe({ id: "historial" })).toBe("/historial");
    expect(paginaPorId("no_existe")).toBeUndefined();
  });
});

describe("quien puede usar que", () => {
  const todas = [...new Set(PAGINAS.flatMap((p) => (p.accion ? [p.accion] : [])))];

  test("sin ninguna accion: el inicio de auditoría, la mesa y Acerca (las que no exigen ninguna)", () => {
    expect(PAGINAS.filter((p) => usable(p, [], false)).map((p) => p.id)).toEqual(["auditoria", "obras", "acerca"]);
  });

  test("con todas las acciones se usan las 29", () => {
    expect(PAGINAS.filter((p) => usable(p, todas, false))).toHaveLength(29);
  });

  test("el modo entrega esconde Investigacion y nada mas (26)", () => {
    const vistas = PAGINAS.filter((p) => usable(p, todas, true));
    expect(vistas).toHaveLength(26);
    expect(vistas.some((p) => p.seccion === "Investigación")).toBe(false);
  });

  test("Existencias e Inicio de producción solo los usa quien puede operar la arenera", () => {
    for (const id of ["existencias", "produccion"]) {
      const pagina = paginaPorId(id)!;
      expect(usable(pagina, ["leer_proyecto", "editar_hoja"], false), id).toBe(false);
      expect(usable(pagina, ["operar_arenera"], false), id).toBe(true);
      expect(usable(pagina, RITA, false), id).toBe(false);
    }
  });
});

describe("linea de ayuda", () => {
  // Codigos internos que no deben verse en la interfaz (UC-12, RF-3, RNF-04, BCP-2, INV-108, MOD-1).
  const JERGA = /\b(UC|RF|RNF|BCP|INV|MOD)-\d/;

  test("la prueba de jerga detecta los codigos internos", () => {
    for (const codigo of ["UC-12", "RF-3", "RNF-04", "BCP-2", "INV-108", "MOD-1"]) {
      expect(JERGA.test(`vea ${codigo}`), codigo).toBe(true);
    }
    expect(JERGA.test("Arme el análisis de precio de una partida")).toBe(false);
  });

  test("cada pagina tiene una linea de 1 a 60 caracteres sin jerga", () => {
    for (const { id, enUnaLinea } of PAGINAS) {
      expect(enUnaLinea.length, id).toBeGreaterThanOrEqual(1);
      expect(enUnaLinea.length, id).toBeLessThanOrEqual(60);
      expect(JERGA.test(enUnaLinea), id).toBe(false);
    }
  });
});
