import { describe, expect, test } from "vitest";
import * as rutas from "./rutas";
import type { PaginaDef } from "./rutas";
import {
  MODULOS,
  PAGINAS,
  SECCIONES,
  fueraDeModulos,
  inicioDe,
  moduloDePagina,
  modulosVisibles,
  paginaPorId,
  rutaDe,
  visible,
} from "./rutas";

// Oraculo escrito a mano: el plan de modulos («Restricciones globales» y la tarea MOD-1) y la seccion y la accion de
// cada pantalla de ui/app.py y de seguridad/permisos.py. [id, seccion, accion, "modulo/area" o null], en su orden.
const REGISTRO: [string, string, string | null, string | null][] = [
  ["auditoria", "Revisión", null, "auditoria/inicio"],
  ["libros", "Revisión", "leer_proyecto", "auditoria/auditar"],
  ["revisar", "Revisión", "revisar_paquete", "auditoria/paquetes"],
  ["historial", "Revisión", "leer_proyecto", "auditoria/historial"],
  ["obras", "Trabajo", null, "obras/inicio"],
  ["hoja", "Trabajo", "editar_hoja", "obras/obras"],
  ["elaborar", "Trabajo", "editar_hoja", "obras/obras"],
  ["tablero", "Trabajo", "leer_proyecto", "obras/obras"],
  ["entregar", "Trabajo", "entregar_paquete", "obras/obras"],
  ["componer", "Trabajo", "editar_hoja", "obras/partidas"],
  ["catalogo", "Trabajo", "leer_proyecto", "obras/partidas"],
  ["similares", "Investigación", "editar_hoja", "obras/partidas"],
  ["precios_empresa", "Trabajo", "administrar_precios", "obras/mercado"],
  ["actualizacion", "Trabajo", "editar_hoja", "obras/mercado"],
  ["historico", "Trabajo", "leer_proyecto", "obras/mercado"],
  ["indices", "Trabajo", "administrar_precios", "obras/mercado"],
  ["simulador", "Investigación", "editar_hoja", "obras/mercado"],
  ["control", "Trabajo", "control_de_obra", "obras/control"],
  ["reajuste", "Trabajo", "convertir_y_reajustar", "obras/control"],
  ["escenarios", "Investigación", "editar_hoja", "obras/control"],
  ["produccion", "Trabajo", null, "produccion/inicio"],
  ["existencias", "Trabajo", "operar_arenera", "produccion/existencias"],
  ["administracion", "Administración", "administrar_cuentas", null],
  ["acerca", "Trabajo", null, null],
];

// Acciones por rol, escritas a mano desde PERMISOS de seguridad/permisos.py (ana arma, rita revisa, admin administra).
const ANA = [
  "editar_hoja",
  "convertir_y_reajustar",
  "control_de_obra",
  "decidir_recuperacion",
  "entregar_paquete",
  "operar_arenera",
  "leer_proyecto",
  "aprobar_version",
  "cambiar_caso",
];
const RITA = ["leer_proyecto", "revisar_paquete", "aprobar_version"];
const ADMIN = [
  "operar_arenera",
  "cambiar_caso",
  "administrar_cuentas",
  "administrar_empresa",
  "administrar_precios",
  "administrar_red_y_api",
  "cambiar_carpeta_de_datos",
];

function ubicacionEnTexto(p: PaginaDef): string | null {
  return p.ubicacion ? `${p.ubicacion.modulo}/${p.ubicacion.area}` : null;
}

describe("registro de paginas", () => {
  test("tiene las 24 pantallas en su orden, con su seccion, su accion y su modulo y area", () => {
    expect(PAGINAS.map((p) => [p.id, p.seccion, p.accion, ubicacionEnTexto(p)])).toEqual(REGISTRO);
  });

  test("ya no existe la pantalla «inicio»: la direccion /inicio solo redirige", () => {
    expect(paginaPorId("inicio")).toBeUndefined();
  });

  test("los ids son unicos y las secciones son las cuatro de Streamlit", () => {
    expect(new Set(PAGINAS.map((p) => p.id)).size).toBe(PAGINAS.length);
    expect(SECCIONES).toEqual(["Trabajo", "Revisión", "Investigación", "Administración"]);
  });

  test("toda pagina del registro carga su pantalla; ya no existe el concepto de «sin migrar»", () => {
    expect(PAGINAS.every((p) => typeof p.cargar === "function")).toBe(true);
    expect("estaMigrada" in rutas).toBe(false);
    expect("enlaceClasico" in rutas).toBe(false);
    expect(paginaPorId("libros")?.titulo).toBe("Libro de la empresa");
    expect(paginaPorId("hoja")).toMatchObject({ titulo: "Hoja del proyecto", seccion: "Trabajo", accion: "editar_hoja" });
  });

  test("los tres inicios nuevos, con su titulo y su linea", () => {
    const inicios = ["auditoria", "obras", "produccion"].map((id) => paginaPorId(id)!);
    expect(inicios.map((p) => [p.id, p.titulo, p.enUnaLinea])).toEqual([
      ["auditoria", "Inicio de auditoría", "Suelte un Excel y vea las últimas auditorías"],
      ["obras", "Inicio de presupuestos y obras", "Cifras, obras y pendientes de un vistazo"],
      ["produccion", "Inicio de producción", "Lo que requiere atención en la arenera"],
    ]);
  });

  test("se retiran las areas, los grupos, las secciones visibles y las herramientas principales", () => {
    for (const nombre of [
      "AREAS",
      "areasVisibles",
      "HERRAMIENTAS_PRINCIPALES",
      "herramientasVisibles",
      "seccionesVisibles",
    ]) {
      expect(nombre in rutas, nombre).toBe(false);
    }
  });

  test("la ruta de una pagina es su id", () => {
    expect(rutaDe(paginaPorId("libros")!)).toBe("/libros");
    expect(rutaDe({ id: "historial" })).toBe("/historial");
    expect(rutaDe(paginaPorId("obras")!)).toBe("/obras");
    expect(paginaPorId("no_existe")).toBeUndefined();
  });
});

describe("modulos", () => {
  test("son tres, en orden, con su nombre, su linea y los titulos de sus areas", () => {
    expect(MODULOS.map((m) => [m.id, m.titulo, m.enUnaLinea, m.areas.map((a) => a.titulo)])).toEqual([
      ["auditoria", "Auditoría", "Revise presupuestos propios o de terceros", ["Inicio", "Auditar", "Paquetes", "Historial"]],
      [
        "obras",
        "Presupuestos y obras",
        "Arme, apruebe y controle sus obras",
        ["Inicio", "Obras", "Partidas", "Mercado", "Aprobaciones", "Control"],
      ],
      ["produccion", "Producción", "Existencias y báscula de la arenera", ["Inicio", "Existencias"]],
    ]);
  });

  test("los ids de las areas", () => {
    expect(Object.fromEntries(MODULOS.map((m) => [m.id, m.areas.map((a) => a.id)]))).toEqual({
      auditoria: ["inicio", "auditar", "paquetes", "historial"],
      obras: ["inicio", "obras", "partidas", "mercado", "aprobaciones", "control"],
      produccion: ["inicio", "existencias"],
    });
  });

  test("cada pantalla con ubicacion apunta a un area que existe en su modulo", () => {
    for (const p of PAGINAS) {
      if (!p.ubicacion) continue;
      const modulo = MODULOS.find((m) => m.id === p.ubicacion!.modulo);
      expect(modulo, p.id).toBeDefined();
      expect(modulo!.areas.map((a) => a.id), p.id).toContain(p.ubicacion.area);
    }
  });

  test("solo Administracion y Acerca quedan fuera de los modulos", () => {
    expect(PAGINAS.filter((p) => p.ubicacion === null).map((p) => p.id)).toEqual(["administracion", "acerca"]);
  });

  test("cada modulo tiene exactamente un inicio", () => {
    for (const m of MODULOS) {
      const inicios = PAGINAS.filter((p) => p.ubicacion?.modulo === m.id && p.ubicacion.area === "inicio");
      expect(inicios, m.id).toHaveLength(1);
    }
  });

  test("inicioDe devuelve la pantalla de inicio de cada modulo", () => {
    expect(inicioDe("auditoria").id).toBe("auditoria");
    expect(inicioDe("obras").id).toBe("obras");
    expect(inicioDe("produccion").id).toBe("produccion");
  });

  test("inicioDe falla con un registro sin el inicio pedido (es un error del registro, no de la persona)", () => {
    expect(() => inicioDe("obras", PAGINAS.filter((p) => p.id !== "obras"))).toThrow();
  });

  test("moduloDePagina: el modulo de la pantalla, o null fuera de los modulos o si no existe", () => {
    expect(moduloDePagina("componer")).toBe("obras");
    expect(moduloDePagina("revisar")).toBe("auditoria");
    expect(moduloDePagina("existencias")).toBe("produccion");
    expect(moduloDePagina("produccion")).toBe("produccion");
    expect(moduloDePagina("acerca")).toBeNull();
    expect(moduloDePagina("administracion")).toBeNull();
    expect(moduloDePagina("no_existe")).toBeNull();
  });
});

describe("quien ve que", () => {
  const todas = [...new Set(PAGINAS.flatMap((p) => (p.accion ? [p.accion] : [])))];

  test("sin ninguna accion solo se ve Acerca: los inicios exigen otra pantalla visible de su modulo", () => {
    expect(PAGINAS.filter((p) => visible(p, [], false)).map((p) => p.id)).toEqual(["acerca"]);
  });

  test("con todas las acciones se ven las 24", () => {
    expect(PAGINAS.filter((p) => visible(p, todas, false))).toHaveLength(24);
  });

  test("el modo entrega esconde Investigacion y nada mas (21)", () => {
    const vistas = PAGINAS.filter((p) => visible(p, todas, true));
    expect(vistas).toHaveLength(21);
    expect(vistas.some((p) => p.seccion === "Investigación")).toBe(false);
  });

  test("un inicio se ve si su modulo tiene otra pantalla visible", () => {
    const auditoria = paginaPorId("auditoria")!;
    const produccion = paginaPorId("produccion")!;
    expect(visible(auditoria, ["revisar_paquete"], false)).toBe(true);
    expect(visible(auditoria, ["operar_arenera"], false)).toBe(false);
    expect(visible(produccion, ["operar_arenera"], false)).toBe(true);
    expect(visible(produccion, RITA, false)).toBe(false);
  });

  test("un inicio cuyo modulo solo tiene pantallas de Investigacion no se ve en modo entrega", () => {
    const solo: PaginaDef[] = [paginaPorId("obras")!, paginaPorId("similares")!];
    expect(visible(solo[0], ["editar_hoja"], false, solo)).toBe(true);
    expect(visible(solo[0], ["editar_hoja"], true, solo)).toBe(false);
  });

  test("Existencias de la arenera solo la ve quien puede operar la arenera", () => {
    const existencias = paginaPorId("existencias")!;
    expect(visible(existencias, ["leer_proyecto", "editar_hoja"], false)).toBe(false);
    expect(visible(existencias, ["operar_arenera"], false)).toBe(true);
  });

  test("modulosVisibles por rol, en el orden de los modulos", () => {
    expect(modulosVisibles(ANA, false).map((m) => m.id)).toEqual(["auditoria", "obras", "produccion"]);
    expect(modulosVisibles(RITA, false).map((m) => m.id)).toEqual(["auditoria", "obras"]);
    expect(modulosVisibles(ADMIN, false).map((m) => m.id)).toEqual(["obras", "produccion"]);
    expect(modulosVisibles([], false)).toEqual([]);
  });

  test("fueraDeModulos por rol", () => {
    expect(fueraDeModulos(ANA, false).map((p) => p.id)).toEqual(["acerca"]);
    expect(fueraDeModulos(RITA, false).map((p) => p.id)).toEqual(["acerca"]);
    expect(fueraDeModulos(ADMIN, false).map((p) => p.id)).toEqual(["administracion", "acerca"]);
    expect(fueraDeModulos([], false).map((p) => p.id)).toEqual(["acerca"]);
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

  test("cada pagina y cada modulo tiene una linea de 1 a 60 caracteres sin jerga", () => {
    for (const { id, enUnaLinea } of [...PAGINAS, ...MODULOS]) {
      expect(enUnaLinea.length, id).toBeGreaterThanOrEqual(1);
      expect(enUnaLinea.length, id).toBeLessThanOrEqual(60);
      expect(JERGA.test(enUnaLinea), id).toBe(false);
    }
  });
});
