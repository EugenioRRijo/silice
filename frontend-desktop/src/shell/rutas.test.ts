import { describe, expect, test } from "vitest";
import { PAGINAS, SECCIONES, enlaceClasico, estaMigrada, paginaPorId, rutaDe, seccionesVisibles, visible } from "./rutas";

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
  ["revisar", "Revisión", "revisar_paquete"],
  ["libros", "Revisión", "leer_proyecto"],
  ["escenarios", "Investigación", "editar_hoja"],
  ["similares", "Investigación", "editar_hoja"],
  ["simulador", "Investigación", "editar_hoja"],
  ["visor", "Investigación", "editar_hoja"],
  ["administracion", "Administración", "administrar_cuentas"],
];

describe("registro de paginas", () => {
  test("tiene las 21 paginas de Streamlit, en su orden, con su seccion y su accion", () => {
    expect(PAGINAS.map((p) => [p.id, p.seccion, p.accion])).toEqual(COMO_STREAMLIT);
  });

  test("los ids son unicos y las secciones son las cuatro de Streamlit", () => {
    expect(new Set(PAGINAS.map((p) => p.id)).size).toBe(PAGINAS.length);
    expect(SECCIONES).toEqual(["Trabajo", "Revisión", "Investigación", "Administración"]);
  });

  test("estan migradas las paginas ya construidas, con carga perezosa", () => {
    expect(PAGINAS.filter(estaMigrada).map((p) => p.id)).toEqual([
      "inicio",
      "componer",
      "elaborar",
      "actualizacion",
      "entregar",
      "libros",
      "escenarios",
      "similares",
      "simulador",
    ]);
    const libro = paginaPorId("libros");
    expect(libro?.titulo).toBe("Libro de la empresa");
    expect(typeof libro?.cargar).toBe("function");
  });

  test("la ruta de una pagina es su id", () => {
    expect(rutaDe(paginaPorId("libros")!)).toBe("/libros");
    expect(paginaPorId("no_existe")).toBeUndefined();
  });
});

describe("quien ve que", () => {
  const todas = PAGINAS.flatMap((p) => (p.accion ? [p.accion] : []));

  test("sin ninguna accion solo se ven Inicio y Acerca", () => {
    expect(PAGINAS.filter((p) => visible(p, [], false)).map((p) => p.id)).toEqual(["inicio", "acerca"]);
  });

  test("con todas las acciones se ven las 21", () => {
    expect(PAGINAS.filter((p) => visible(p, todas, false))).toHaveLength(21);
  });

  test("el modo entrega esconde Investigacion y nada mas", () => {
    const sinInvestigacion = PAGINAS.filter((p) => visible(p, todas, true));
    expect(sinInvestigacion).toHaveLength(17);
    expect(sinInvestigacion.some((p) => p.seccion === "Investigación")).toBe(false);
  });

  test("seccionesVisibles agrupa en orden y omite las secciones vacias", () => {
    const rol = ["leer_proyecto", "revisar_paquete"]; // como el rol que revisa
    const secciones = seccionesVisibles(rol, false);
    expect(secciones.map((s) => s.seccion)).toEqual(["Trabajo", "Revisión"]);
    expect(secciones[0].paginas.map((p) => p.id)).toEqual(["inicio", "tablero", "catalogo", "historico", "acerca"]);
    expect(secciones[1].paginas.map((p) => p.id)).toEqual(["revisar", "libros"]);
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
