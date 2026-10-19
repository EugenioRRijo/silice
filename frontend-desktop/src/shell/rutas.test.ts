import { describe, expect, test } from "vitest";
import {
  AREAS,
  HERRAMIENTAS_PRINCIPALES,
  PAGINAS,
  SECCIONES,
  areasVisibles,
  enlaceClasico,
  estaMigrada,
  herramientasVisibles,
  paginaPorId,
  rutaDe,
  seccionesVisibles,
  visible,
} from "./rutas";

// Lo que Streamlit declara en ui/app.py (PAGINAS) y en cada ui/paginas/*.py (ui_sesion.exigir): id (modulo), seccion, accion.
const COMO_STREAMLIT: [string, string, string | null][] = [
  ["inicio", "Trabajo", null],
  ["tablero", "Trabajo", "leer_proyecto"],
  ["catalogo", "Trabajo", "leer_proyecto"],
  ["componer", "Trabajo", "editar_hoja"],
  ["elaborar", "Trabajo", "editar_hoja"],
  ["hoja", "Trabajo", "editar_hoja"],
  ["actualizacion", "Trabajo", "editar_hoja"],
  ["historico", "Trabajo", "leer_proyecto"],
  ["precios_empresa", "Trabajo", "administrar_precios"],
  ["indices", "Trabajo", "administrar_precios"],
  ["reajuste", "Trabajo", "convertir_y_reajustar"],
  ["control", "Trabajo", "control_de_obra"],
  ["acerca", "Trabajo", null],
  ["entregar", "Trabajo", "entregar_paquete"],
  ["existencias", "Trabajo", "operar_arenera"],
  ["revisar", "Revisión", "revisar_paquete"],
  ["libros", "Revisión", "leer_proyecto"],
  ["historial", "Revisión", "leer_proyecto"], // solo existe en la interfaz nueva (UC-30)
  ["escenarios", "Investigación", "editar_hoja"],
  ["similares", "Investigación", "editar_hoja"],
  ["simulador", "Investigación", "editar_hoja"],
  ["administracion", "Administración", "administrar_cuentas"],
];

describe("registro de paginas", () => {
  test("tiene las 21 paginas de Streamlit mas el historial (22), en su orden, con su seccion y su accion", () => {
    expect(PAGINAS.map((p) => [p.id, p.seccion, p.accion])).toEqual(COMO_STREAMLIT);
  });

  test("los ids son unicos y las secciones son las cuatro de Streamlit", () => {
    expect(new Set(PAGINAS.map((p) => p.id)).size).toBe(PAGINAS.length);
    expect(SECCIONES).toEqual(["Trabajo", "Revisión", "Investigación", "Administración"]);
  });

  test("estan migradas las paginas ya construidas, con carga perezosa", () => {
    expect(PAGINAS.filter(estaMigrada).map((p) => p.id)).toEqual([
      "inicio",
      "tablero",
      "catalogo",
      "componer",
      "elaborar",
      "actualizacion",
      "historico",
      "precios_empresa",
      "indices",
      "reajuste",
      "control",
      "acerca",
      "entregar",
      "existencias",
      "libros",
      "historial",
      "escenarios",
      "similares",
      "simulador",
      "administracion",
    ]);
    const libro = paginaPorId("libros");
    expect(libro?.titulo).toBe("Libro de la empresa");
    expect(typeof libro?.cargar).toBe("function");
    const existencias = paginaPorId("existencias");
    expect(existencias).toMatchObject({
      titulo: "Existencias de la arenera",
      seccion: "Trabajo",
      accion: "operar_arenera",
    });
    expect(typeof existencias?.cargar).toBe("function");
  });

  test("la ruta de una pagina es su id", () => {
    expect(rutaDe(paginaPorId("libros")!)).toBe("/libros");
    expect(rutaDe(paginaPorId("existencias")!)).toBe("/existencias");
    expect(paginaPorId("no_existe")).toBeUndefined();
  });
});

describe("quien ve que", () => {
  const todas = PAGINAS.flatMap((p) => (p.accion ? [p.accion] : []));

  test("sin ninguna accion solo se ven Inicio y Acerca", () => {
    expect(PAGINAS.filter((p) => visible(p, [], false)).map((p) => p.id)).toEqual(["inicio", "acerca"]);
  });

  test("con todas las acciones se ven las 22", () => {
    expect(PAGINAS.filter((p) => visible(p, todas, false))).toHaveLength(22);
  });

  test("el modo entrega esconde Investigacion y nada mas", () => {
    const sinInvestigacion = PAGINAS.filter((p) => visible(p, todas, true));
    expect(sinInvestigacion).toHaveLength(19);
    expect(sinInvestigacion.some((p) => p.seccion === "Investigación")).toBe(false);
  });

  test("seccionesVisibles agrupa en orden y omite las secciones vacias", () => {
    const rol = ["leer_proyecto", "revisar_paquete"]; // como el rol que revisa
    const secciones = seccionesVisibles(rol, false);
    expect(secciones.map((s) => s.seccion)).toEqual(["Trabajo", "Revisión"]);
    expect(secciones[0].paginas.map((p) => p.id)).toEqual(["inicio", "tablero", "catalogo", "historico", "acerca"]);
    expect(secciones[1].paginas.map((p) => p.id)).toEqual(["revisar", "libros", "historial"]);
  });

  test("Existencias de la arenera solo la ve quien puede operar la arenera", () => {
    const existencias = paginaPorId("existencias")!;
    expect(visible(existencias, ["leer_proyecto", "editar_hoja"], false)).toBe(false);
    expect(visible(existencias, ["operar_arenera"], false)).toBe(true);
    expect(seccionesVisibles(["operar_arenera"], false)[0].paginas.map((p) => p.id)).toEqual([
      "inicio",
      "acerca",
      "existencias",
    ]);
  });

  test("el administrador sin acciones de trabajo solo ve su seccion y lo comun", () => {
    const secciones = seccionesVisibles(["administrar_cuentas"], false);
    expect(secciones.map((s) => s.seccion)).toEqual(["Trabajo", "Administración"]);
  });
});

describe("enlaceClasico", () => {
  test("une la direccion base con la ruta de Streamlit", () => {
    expect(enlaceClasico("http://127.0.0.1:8501", paginaPorId("tablero")!)).toBe("http://127.0.0.1:8501/tablero");
    expect(enlaceClasico("http://127.0.0.1:8501/", paginaPorId("tablero")!)).toBe("http://127.0.0.1:8501/tablero");
  });

  test("Inicio es la raiz de Streamlit", () => {
    expect(enlaceClasico("http://127.0.0.1:8501", paginaPorId("inicio")!)).toBe("http://127.0.0.1:8501/");
  });

  test("sin direccion conocida no hay enlace", () => {
    expect(enlaceClasico(null, paginaPorId("tablero")!)).toBeNull();
    expect(enlaceClasico(undefined, paginaPorId("tablero")!)).toBeNull();
    expect(enlaceClasico("", paginaPorId("tablero")!)).toBeNull();
  });

  test("solo acepta http y https (nada de javascript:)", () => {
    expect(enlaceClasico("javascript:alert(1)", paginaPorId("tablero")!)).toBeNull();
    expect(enlaceClasico("https://silice.local", paginaPorId("tablero")!)).toBe("https://silice.local/tablero");
  });
});

// Spec 2026-10-18 del Inicio, §2.2 (tabla de areas) y §2.3 (herramientas principales), copiados a mano.
describe("areas del menu", () => {
  test("son cinco, en orden, con la descripcion del spec", () => {
    expect(AREAS.map((a) => [a.id, a.titulo, a.descripcion])).toEqual([
      ["inicio", "Inicio", "Empiece aquí"],
      ["auditar", "Auditar", "Revisar presupuestos y paquetes"],
      ["crear", "Crear", "APU, presupuestos y entregas"],
      ["produccion", "Producción", "Arenera: existencias y báscula"],
      ["mas", "Más", "Precios, obra, análisis y ajustes"],
    ]);
  });

  test("reparten las pantallas como la tabla del spec, en su orden", () => {
    expect(Object.fromEntries(AREAS.map((a) => [a.id, a.paginas]))).toEqual({
      inicio: ["inicio"],
      auditar: ["libros", "revisar", "historial"],
      crear: ["componer", "elaborar", "hoja", "catalogo", "tablero", "entregar"],
      produccion: ["existencias"],
      mas: [
        "actualizacion",
        "historico",
        "precios_empresa",
        "indices",
        "reajuste",
        "control",
        "escenarios",
        "similares",
        "simulador",
        "administracion",
        "acerca",
      ],
    });
  });

  test("cada pagina del registro esta en una sola area", () => {
    const todas = AREAS.flatMap((a) => a.paginas);
    for (const pagina of PAGINAS) expect(todas.filter((id) => id === pagina.id)).toHaveLength(1);
    expect(new Set(todas).size).toBe(todas.length);
  });

  test("con todas las acciones salen las cinco areas y las 22 paginas, ninguna repetida", () => {
    const todas = PAGINAS.flatMap((p) => (p.accion ? [p.accion] : []));
    const areas = areasVisibles(todas, false);
    expect(areas.map((a) => a.id)).toEqual(["inicio", "auditar", "crear", "produccion", "mas"]);
    expect(areas.flatMap((a) => a.paginas)).toHaveLength(22);
    expect(areas[1].paginas.map((p) => p.id)).toEqual(["libros", "revisar", "historial"]);
  });

  test("una area sin pantallas visibles no se pinta", () => {
    const areas = areasVisibles(["leer_proyecto", "revisar_paquete"], false);
    expect(areas.map((a) => a.id)).toEqual(["inicio", "auditar", "crear", "mas"]);
    expect(areas[2].paginas.map((p) => p.id)).toEqual(["catalogo", "tablero"]);
    expect(areas[3].paginas.map((p) => p.id)).toEqual(["historico", "acerca"]);
  });

  test("el modo entrega quita Escenarios, Partidas similares y Simulador y deja 19", () => {
    const todas = PAGINAS.flatMap((p) => (p.accion ? [p.accion] : []));
    const ids = areasVisibles(todas, true).flatMap((a) => a.paginas.map((p) => p.id));
    expect(ids).toHaveLength(19);
    for (const fuera of ["escenarios", "similares", "simulador"]) expect(ids).not.toContain(fuera);
  });

  test("una pagina fuera de toda area cae al final de «Más» en vez de perderse", () => {
    const extra = { id: "nueva", titulo: "Nueva", seccion: "Trabajo", accion: null } as const;
    const mas = areasVisibles([], false, [...PAGINAS, extra]).find((a) => a.id === "mas")!;
    expect(mas.paginas.map((p) => p.id).at(-1)).toBe("nueva");
  });
});

describe("herramientas principales", () => {
  test("son tres, en este orden, con la linea de ayuda del spec; llevan el nombre de su pantalla", () => {
    expect(HERRAMIENTAS_PRINCIPALES.map((h) => [h.pagina, h.ayuda])).toEqual([
      ["libros", "Suba un Excel y vea lo que no cuadra"],
      ["componer", "Componga una partida o arme un presupuesto"],
      ["existencias", "Cuánto hay y cuánto queda de cada material"],
    ]);
    const todas = PAGINAS.flatMap((p) => (p.accion ? [p.accion] : []));
    expect(herramientasVisibles(todas, false).map((h) => h.titulo)).toEqual([
      "Libro de la empresa",
      "Componer una partida",
      "Existencias de la arenera",
    ]);
  });

  test("solo salen las que la cuenta puede usar y que ya estan en esta interfaz", () => {
    expect(herramientasVisibles(["leer_proyecto"], false).map((h) => h.pagina)).toEqual(["libros"]);
    const todas = PAGINAS.flatMap((p) => (p.accion ? [p.accion] : []));
    expect(herramientasVisibles(todas, false).map((h) => h.pagina)).toEqual(["libros", "componer", "existencias"]);
    const sinMigrar = PAGINAS.map((p) => (p.id === "componer" ? { ...p, cargar: undefined } : p));
    expect(herramientasVisibles(todas, false, sinMigrar).map((h) => h.pagina)).toEqual(["libros", "existencias"]);
  });
});

describe("rutaDe", () => {
  test("acepta una pagina completa o solo su id", () => {
    expect(rutaDe({ id: "historial" })).toBe("/historial");
    expect(rutaDe(paginaPorId("libros")!)).toBe("/libros");
  });
});
