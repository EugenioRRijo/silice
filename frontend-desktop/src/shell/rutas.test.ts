import { describe, expect, test } from "vitest";
import * as rutas from "./rutas";
import { PAGINAS, SECCIONES, paginaPorId, rutaDe, usable } from "./rutas";

// Oraculo escrito a mano: la seccion y la accion de cada pantalla de ui/app.py y de seguridad/permisos.py, en su orden.
// Dónde se ve cada una ya no lo dice el registro sino el marco (marco/secciones.ts y el buscador).
const REGISTRO: [string, string, string | null][] = [
  // F6, T8: la Vista general (`/inicio/general`) es la entrada de la app y la ve toda cuenta; no es de las 31 del contrato.
  ["inicio", "Trabajo", null],
  ["auditoria", "Revisión", null],
  ["libros", "Revisión", "leer_proyecto"],
  ["revisar", "Revisión", "revisar_paquete"],
  ["historial", "Revisión", "leer_proyecto"],
  ["obras", "Trabajo", null],
  ["hoja", "Trabajo", "leer_proyecto"], // F4 2b: quien revisa la ve en solo lectura
  ["versiones", "Trabajo", "leer_proyecto"], // F4, Tarea 6: la sección Versiones de la obra
  ["archivos", "Trabajo", "leer_proyecto"], // F4 Tarea 11: quien revisa ve el registro; subir exige editar_hoja
  ["tablero", "Trabajo", "leer_proyecto"],
  ["entregar", "Trabajo", "entregar_paquete"],
  ["componer", "Trabajo", "editar_hoja"],
  ["catalogo", "Trabajo", "leer_proyecto"],
  ["mercado", "Trabajo", "leer_proyecto"], // F4, Tarea 13, ronda 2: quien revisa lee el histórico y las cotizaciones
  ["precios_empresa", "Trabajo", "administrar_precios"],
  ["actualizacion", "Trabajo", "editar_hoja"],
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
  // Plan vial, Tarea 6b: producir una mezcla con su receta lo hace quien opera la arenera.
  ["producir_mezcla", "Trabajo", "operar_arenera"],
  ["costo_tonelada", "Trabajo", "registrar_costos_produccion"],
  // Plan vial, Tarea 8: los tramos de una vía los edita quien arma (API: editar_hoja).
  ["tramos", "Trabajo", "editar_hoja"],
  // Plan vial, Tarea 16: el riesgo de la obra lo ven quien arma, quien revisa y quien administra (API: ver_riesgo).
  ["riesgo", "Trabajo", "ver_riesgo"],
  ["administracion", "Administración", "administrar_cuentas"],
  ["acerca", "Trabajo", null],
];

const RITA = ["leer_proyecto", "revisar_paquete", "aprobar_version"];

describe("registro de paginas", () => {
  test("tiene las 31 pantallas del contrato y la Vista general, en su orden, con su seccion y su accion", () => {
    expect(PAGINAS.map((p) => [p.id, p.seccion, p.accion])).toEqual(REGISTRO);
  });

  // F6, T8: «inicio» deja de no existir: es la Vista general, que monta `/inicio/general` y la ve toda cuenta.
  test("existe la pantalla «inicio»: la Vista general, que ve toda cuenta", () => {
    const inicio = paginaPorId("inicio");
    expect(inicio?.titulo).toBe("Vista general");
    expect(inicio?.accion).toBeNull();
    expect(inicio?.modulo).toBeUndefined();
    expect(usable(inicio!, [], false)).toBe(true);
    expect(usable(inicio!, [], true)).toBe(true);
  });

  // F4, Tarea 9, baja 20: «Partidas similares» pasa a «Parecidas a esta descripción», dentro de «Agregar partida».
  test("ya no existe la pantalla «Partidas similares»", () => {
    expect(paginaPorId("similares")).toBeUndefined();
    expect(PAGINAS.some((p) => p.titulo === "Partidas similares")).toBe(false);
  });

  // F4, Tarea 12 (baja 19): «Elaborar un presupuesto» es ahora «Cargar cómputo», dentro de Archivos y planos.
  test("ya no existe la pantalla «elaborar»", () => {
    expect(paginaPorId("elaborar")).toBeUndefined();
    expect(PAGINAS.some((p) => p.titulo === "Elaborar un presupuesto")).toBe(false);
  });

  // F4, Tarea 13: el histórico de cambios de precio es ahora una pestaña de Mercado.
  test("ya no existe la pantalla «historico»", () => {
    expect(paginaPorId("historico")).toBeUndefined();
    expect(PAGINAS.some((p) => p.titulo === "Histórico de cambios de precio")).toBe(false);
  });

  test("los ids son unicos y las secciones de permisos son cuatro", () => {
    expect(new Set(PAGINAS.map((p) => p.id)).size).toBe(PAGINAS.length);
    expect(SECCIONES).toEqual(["Trabajo", "Revisión", "Investigación", "Administración"]);
  });

  test("toda pagina del registro carga su pantalla", () => {
    expect(PAGINAS.every((p) => typeof p.cargar === "function")).toBe(true);
    expect(paginaPorId("libros")?.titulo).toBe("Libro de la empresa");
    expect(paginaPorId("hoja")).toMatchObject({ titulo: "Presupuesto", seccion: "Trabajo", accion: "leer_proyecto" });
    expect(paginaPorId("mercado")).toMatchObject({
      titulo: "Estudio de mercado",
      // Cierre de F4 (menor de la Tarea 13): la línea vale también para quien revisa, que no elige precios.
      enUnaLinea: "Compare precios del mercado, su histórico y las cotizaciones",
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

  test("sin ninguna accion: la Vista general, el inicio de auditoría, la mesa y Acerca (las que no exigen ninguna)", () => {
    expect(PAGINAS.filter((p) => usable(p, [], false)).map((p) => p.id)).toEqual(["inicio", "auditoria", "obras", "acerca"]);
  });

  test("con todas las acciones se usan las 32 (las 31 del contrato y la Vista general)", () => {
    expect(PAGINAS.filter((p) => usable(p, todas, false))).toHaveLength(32);
  });

  test("el modo entrega esconde Investigacion y nada mas (30)", () => {
    const vistas = PAGINAS.filter((p) => usable(p, todas, true));
    expect(vistas).toHaveLength(30);
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

describe("módulos apagados (plan vial, Tarea 19)", () => {
  // Oráculo a mano: qué módulo activable cierra cada pantalla.
  const DEL_MODULO: [string, string][] = [
    ["produccion", "produccion"],
    ["existencias", "produccion"],
    ["costos", "produccion"],
    ["receta_planta", "produccion"],
    ["producir_mezcla", "produccion"],
    ["costo_tonelada", "produccion"],
    ["tramos", "vial"],
    ["riesgo", "riesgo"],
  ];
  const TODAS_LAS_ACCIONES = PAGINAS.flatMap((p) => (p.accion === null ? [] : [p.accion]));

  test.each(DEL_MODULO)("«%s» pertenece al módulo %s", (id, modulo) => {
    expect(paginaPorId(id)?.modulo).toBe(modulo);
  });

  test.each(DEL_MODULO)("«%s» deja de ser usable cuando su módulo está apagado, y vuelve al encender", (id, modulo) => {
    expect(paginaPorId(id), id).toBeDefined();
    const pagina = paginaPorId(id)!;
    expect(usable(pagina, TODAS_LAS_ACCIONES, false, [modulo])).toBe(false);
    expect(usable(pagina, TODAS_LAS_ACCIONES, false, [])).toBe(true);
    expect(usable(pagina, TODAS_LAS_ACCIONES, false)).toBe(true);
  });

  test("apagar un módulo no toca las pantallas de los otros ni las de ninguno", () => {
    expect(usable(paginaPorId("tramos")!, TODAS_LAS_ACCIONES, false, ["produccion", "riesgo"])).toBe(true);
    expect(usable(paginaPorId("hoja")!, TODAS_LAS_ACCIONES, false, ["produccion", "vial", "riesgo", "edificacion"])).toBe(true);
  });

  // F4, Tarea 12 (decisión del orquestador, regla de la T19 del plan vial): «edificación» apaga los planos y el espacio,
  // no los cómputos. Archivos y planos no es de ningún módulo: con edificación apagada se sigue usando para el cómputo.
  test("«Archivos y planos» no es de ningún módulo y se usa con «edificación» apagada", () => {
    expect(paginaPorId("archivos")?.modulo).toBeUndefined();
    expect(usable(paginaPorId("archivos")!, TODAS_LAS_ACCIONES, false, ["edificacion"])).toBe(true);
  });
});
