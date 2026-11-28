import { describe, expect, test } from "vitest";
import { ESPACIOS, SUBVISTAS } from "../../marco/espacios";
import { SECCIONES_DE_OBRA } from "../../marco/secciones";
import { PASOS_DE_EMPIEZA_AQUI, PRIMERA_VEZ } from "./empiezaAqui";
import { sinComentarios } from "./sinComentarios";
import { AYUDA_DE_PANTALLAS, GLOSARIO, GUIAS } from "./textos";

// F7 (Ayuda), tareas A1 a A3: el catálogo único de los textos de ayuda. Estas pruebas no leen la interfaz pintada: vigilan
// que cada pantalla de la obra y de los espacios tenga su «¿Qué es esto?», que las guías y el glosario existan con los
// términos que pidió el plan, y que cada control que un texto nombra entre comillas («…») exista de verdad en el código.
// Oráculos escritos a mano: los identificadores de las pantallas y los títulos de las guías salen del plan
// (docs/planes/PLAN_TANDA_DETALLES.md, Fase 2), no del catálogo.

interface Fs {
  readdirSync(carpeta: string, opciones: { recursive: true }): string[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const fs = nodo.getBuiltinModule("node:fs");
const raiz = `${nodo.cwd()}/src`;
const aplicacion = `${nodo.cwd()}/../aplicacion`;

// El código donde viven los textos de la interfaz: el front (sin pruebas ni la propia ayuda, que no puede citarse a sí misma)
// y la capa `aplicacion/`, que manda los textos de la franja del paso y de los pendientes. Los espacios se juntan: una
// etiqueta de JSX puede partirse en dos líneas. Se quitan los comentarios y los docstrings: un rótulo que solo vive en uno no
// existe para quien usa la interfaz (revisión del árbitro de F7, A2).
function fuentes(): string {
  const front = fs
    .readdirSync(raiz, { recursive: true })
    .map((r) => r.replaceAll("\\", "/"))
    .filter((r) => /\.tsx?$/.test(r) && !/\.test\.tsx?$/.test(r) && !r.startsWith("comun/ayuda/"))
    .map((r) => sinComentarios(fs.readFileSync(`${raiz}/${r}`, "utf-8"), "ts"));
  const servidor = fs
    .readdirSync(aplicacion, { recursive: true })
    .map((r) => r.replaceAll("\\", "/"))
    .filter((r) => r.endsWith(".py"))
    .map((r) => sinComentarios(fs.readFileSync(`${aplicacion}/${r}`, "utf-8"), "py"));
  return [...front, ...servidor].join("\n").replace(/\s+/g, " ");
}

const citas = (texto: string): string[] => [...texto.matchAll(/«([^«»]+)»/g)].map((m) => m[1]!.replace(/\s+/g, " "));

// Las pantallas que la obra y los espacios montan (secciones, subvistas y herramientas), según la tabla del marco.
const DE_LA_OBRA = [...new Set([...SECCIONES_DE_OBRA.map((s) => s.pagina), ...Object.values(SUBVISTAS).flatMap((v) => v!.map((h) => h.pagina))])];
const DE_LOS_ESPACIOS = Object.values(ESPACIOS).flatMap((e) => e.herramientas.map((h) => h.pagina));

const PROHIBIDAS = /(?<!\p{L})(m[oó]dulos?|[aá]reas?|p[aá]ginas?|streamlit|carpetas? de trabajo|proyectos?)(?!\p{L})/iu;

describe("«¿Qué es esto?» de cada pantalla (A1)", () => {
  test("cada pantalla de la obra y de los tres espacios tiene su ayuda, salvo las pestañas del Presupuesto, que la tienen por pestaña", () => {
    expect(DE_LA_OBRA).toHaveLength(17); // las nueve secciones y las ocho subvistas que no son la raíz («hoja_pestanas» entre ellas)
    expect(DE_LOS_ESPACIOS).toHaveLength(13);
    const sinAyudaPropia = ["hoja_pestanas"];
    const faltan = [...DE_LA_OBRA, ...DE_LOS_ESPACIOS].filter((p) => !sinAyudaPropia.includes(p!) && AYUDA_DE_PANTALLAS[p!] === undefined);
    expect(faltan).toEqual([]);
    expect(AYUDA_DE_PANTALLAS.hoja).toBeDefined();
    expect(AYUDA_DE_PANTALLAS.hoja_pestanas).toBeUndefined();
    expect(AYUDA_DE_PANTALLAS.pendientes).toBeDefined();
  });

  test("cada ayuda dice algo (de una a tres frases), sin jerga ni «proyecto», y sus enlaces van a guías y términos que existen", () => {
    const guias = new Set(GUIAS.map((g) => g.id));
    const terminos = new Set(GLOSARIO.map((t) => t.id));
    for (const [pagina, ayuda] of Object.entries(AYUDA_DE_PANTALLAS)) {
      expect(ayuda.titulo.length, pagina).toBeGreaterThan(0);
      expect(ayuda.parrafos.length, pagina).toBeGreaterThan(0);
      for (const p of ayuda.parrafos) {
        expect(p, pagina).not.toMatch(PROHIBIDAS);
        expect(p.length, pagina).toBeLessThanOrEqual(420);
        expect(p, pagina).toMatch(/[.:]$/);
      }
      if (ayuda.guia !== undefined) expect(guias.has(ayuda.guia), pagina).toBe(true);
      for (const t of ayuda.terminos ?? []) expect(terminos.has(t), `${pagina}: ${t}`).toBe(true);
    }
  });
});

describe("Guías por tarea (A2)", () => {
  test("son las cuatro del plan, en este orden y con estos títulos", () => {
    expect(GUIAS.map((g) => [g.id, g.titulo])).toEqual([
      ["presupuesto", "Montar un presupuesto"],
      ["aprobacion", "Enviarlo a aprobación"],
      ["precios", "Actualizar precios"],
      ["auditar", "Auditar un libro"],
    ]);
  });

  test("cada guía dice quién la hace y tiene pasos, sin jerga ni «proyecto»", () => {
    for (const g of GUIAS) {
      expect(g.quien, g.id).toMatch(/^Quien /);
      expect(g.partes.length, g.id).toBeGreaterThan(0);
      for (const parte of g.partes) {
        expect(parte.pasos.length, `${g.id}: ${parte.titulo}`).toBeGreaterThan(1);
        for (const paso of [...parte.pasos, parte.titulo]) expect(paso, g.id).not.toMatch(PROHIBIDAS);
      }
    }
  });

  test("«Guardar y descargar» dice que guardar solo el desglose del desperdicio no crea versión (anexo A.6, DS-48i)", () => {
    const parte = GUIAS.find((g) => g.id === "presupuesto")!.partes.find((p) => p.titulo === "Guardar y descargar")!;
    const guardar = parte.pasos[0]!;
    expect(guardar).toMatch(/nace una versión/);
    expect(guardar).toMatch(/«Guardar ajuste de desperdicio…»/); // el botón de la franja
    expect(guardar).toMatch(/«Guardar el desglose»/); // el del diálogo
    expect(guardar).toMatch(/no crea versión/);
  });
});

describe("Glosario (A3)", () => {
  test("trae los términos que pidió el plan, con un id estable para enlazarlos", () => {
    const ids = GLOSARIO.map((t) => t.id);
    for (const id of [
      "apu",
      "fcas",
      "valor-ganado",
      "reajuste",
      "linea-base",
      "lista-para-armar",
      "aace",
      "asistente-ia",
      "bac",
      "clave-api",
      "clave-de-firma",
      "codigo-verificacion",
      "comprobacion-directa",
      "comprobacion-hacia-atras",
      "cpi",
      "cuartil-y-mediana",
      "depreciacion-equipo",
      "eac",
      "erosion",
      "escalatoria",
      "factor-km",
      "incidencia",
      "inpc",
      "lista-base",
      "pareto",
      "perfil-libro",
      "procura",
      "punto-de-equilibrio",
      "pv-ev-ac",
      "reparto-cantera",
      "reserva-contingencia",
      "simulacion",
      "spi",
    ])
      expect(ids, id).toContain(id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) expect(id).toMatch(/^[a-z0-9-]+$/);
    expect(GLOSARIO.find((t) => t.id === "spi")!.definicion).toContain("1,00");
    expect(GLOSARIO.find((t) => t.id === "cpi")!.definicion).toContain("1,00");
  });

  test("va en orden alfabético (español) y cada definición es una o dos frases terminadas en punto", () => {
    const nombres = GLOSARIO.map((t) => t.termino);
    expect(nombres).toEqual([...nombres].sort((a, b) => a.localeCompare(b, "es", { sensitivity: "base" })));
    for (const t of GLOSARIO) {
      expect(t.definicion, t.id).toMatch(/\.$/);
      expect(t.definicion, t.id).not.toMatch(PROHIBIDAS);
    }
  });

  test("el FCAS no se presenta como cifra de una norma: dice cómo se escribe y dónde se cambia", () => {
    const fcas = GLOSARIO.find((t) => t.id === "fcas")!;
    expect(fcas.definicion).toContain("6,00");
    expect(fcas.definicion).toContain("«Ajustes de costo»");
    expect(fcas.definicion).not.toMatch(/ley|norma|LOTTT|convención/i);
  });
});

describe("cada control que la ayuda nombra existe en la interfaz", () => {
  const codigo = fuentes();
  const todos = [
    ...Object.values(AYUDA_DE_PANTALLAS).flatMap((a) => a.parrafos),
    ...GUIAS.flatMap((g) => [g.quien, ...g.partes.flatMap((p) => [p.titulo, ...p.pasos])]),
    ...GLOSARIO.map((t) => t.definicion),
    ...Object.values(PASOS_DE_EMPIEZA_AQUI).flatMap((p) => [p.titulo, p.texto]),
    ...PRIMERA_VEZ.parrafos,
  ];

  test("la guardia recorre el código y encuentra lo que se sabe que está", () => {
    expect(codigo).toContain("Agregar partida");
    expect(codigo).not.toContain("Botón que no existe en Sílice");
    expect(citas("Pulse «Guardar versión…» y luego «Crear\n obra».")).toEqual(["Guardar versión…", "Crear obra"]);
  });

  test("todo texto entre comillas angulares de la ayuda aparece tal cual en el código", () => {
    const citadas = [...new Set(todos.flatMap(citas))];
    expect(citadas.length).toBeGreaterThan(40);
    expect(citadas.filter((c) => !codigo.includes(c))).toEqual([]);
  });
});

// Revisor goldfish (2026-11-22): dos definiciones decían lo contrario de lo que significan.
describe("el glosario define bien el CPI y el P50/P80", () => {
  const def = (id: string) => GLOSARIO.find((t) => t.id === id)!.definicion;

  test("el CPI compara lo gastado con lo que vale lo ejecutado, no con lo planificado (eso es el SPI)", () => {
    expect(def("cpi")).toContain("más de lo que vale lo ejecutado");
    expect(def("cpi")).not.toContain("más de lo planificado");
  });

  test("P50 y P80 son los totales que no se superan en la mitad y en 8 de cada 10 simulaciones", () => {
    expect(def("p50-p80")).toContain("no se supera en la mitad de las simulaciones");
    expect(def("p50-p80")).toContain("8 de cada 10");
    expect(def("p50-p80")).not.toContain("no superan el 50 %");
  });

  test("el SPI habla de atraso frente a lo planificado", () => {
    expect(def("spi")).toContain("atraso frente a lo planificado");
  });
});

// Pasada goldfish N1 (2026-11-23): un solo nombre por idea, el que se lee en pantalla.
describe("el glosario usa los nombres únicos de la pasada goldfish", () => {
  const termino = (id: string) => GLOSARIO.find((t) => t.id === id)!.termino;
  const def = (id: string) => GLOSARIO.find((t) => t.id === id)!.definicion;

  test("cada término lleva el nombre que se lee en pantalla", () => {
    expect(termino("comprobacion-hacia-atras")).toBe("Prueba con meses pasados");
    expect(termino("incidencia")).toBe("Incidencia en el cambio (%)");
    expect(termino("inpc")).toBe("Índice Nacional de Precios al Consumidor (INPC)");
    expect(termino("fcas")).toBe("Factor de costos asociados al salario (FCAS)");
    expect(termino("simulacion")).toBe("Simulación y semilla");
  });

  test("P50 y P80 se definen con el texto acordado", () => {
    expect(def("p50-p80")).toBe(
      "En Riesgo, P50 es el total que no se supera en la mitad de las simulaciones; P80, el que no se supera en 8 de cada 10. La reserva recomendada es la diferencia entre el total base y el P80.",
    );
  });

  test("Riesgo habla solo de simulaciones: ni trayectorias ni escenarios", () => {
    for (const id of ["simulacion", "p50-p80", "comprobacion-hacia-atras"]) {
      expect(def(id), id).not.toMatch(/trayectoria|escenario/i);
    }
    expect(AYUDA_DE_PANTALLAS.riesgo!.parrafos.join(" ")).not.toMatch(/trayectoria/i);
  });

  test("MaPreX se presenta como referencia pública de precios en bolívares", () => {
    expect(def("maprex")).toContain("referencia pública de precios de la construcción en bolívares");
  });

  test("N2: la clave de firma no habla de «clave pública» y el reparto de cantera es por tonelada", () => {
    expect(def("clave-de-firma")).not.toContain("clave pública");
    expect(def("clave-de-firma")).toContain("Código de verificación de la clave (SHA-256)");
    expect(def("reparto-cantera")).toContain("en proporción a las toneladas producidas");
    expect(def("reparto-cantera")).not.toContain("partes iguales");
  });

  test("N2: Componer dice de qué lista y a qué fecha salen los precios", () => {
    expect(AYUDA_DE_PANTALLAS.componer!.parrafos.join(" ")).toContain(
      "Los precios salen de la lista de precios activa, en la «Fecha de precios» de este análisis.",
    );
  });
});

