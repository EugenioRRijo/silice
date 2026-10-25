import { describe, expect, test } from "vitest";
import { areaActual, navegacion, type EntradaNav } from "./navegacion";
import { PAGINAS, paginaPorId, type PaginaDef } from "./rutas";

const TODAS = [...new Set(PAGINAS.flatMap((p) => (p.accion ? [p.accion] : [])))];

function idsDe(entradas: readonly EntradaNav[]): string[] {
  return entradas.flatMap((e) => (e.tipo === "enlace" ? [e.pagina.id] : e.grupos.flatMap((g) => g.paginas.map((p) => p.id))));
}

describe("navegacion", () => {
  test("con todas las acciones: inicio, auditar, crear, produccion y mas", () => {
    expect(navegacion(TODAS, false).map((e) => [e.area, e.tipo])).toEqual([
      ["inicio", "enlace"],
      ["auditar", "panel"],
      ["crear", "panel"],
      ["produccion", "enlace"],
      ["mas", "panel"],
    ]);
  });

  test("ninguna pagina aparece dos veces", () => {
    const libros = paginaPorId("libros")!.accion!;
    const juegos: Array<[string[], boolean]> = [
      [TODAS, false],
      [[], false],
      [[libros], false],
      [TODAS, true],
    ];
    for (const [acciones, entrega] of juegos) {
      const ids = idsDe(navegacion(acciones, entrega));
      expect(new Set(ids).size).toBe(ids.length);
    }
  });

  test("sin acciones y con una pagina de prueba sin accion: solo inicio, sin grupos vacios", () => {
    const x = { id: "x", titulo: "X", enUnaLinea: "Haga X", seccion: "Trabajo", accion: null, cargar: async () => ({ default: () => null }) } as PaginaDef;
    const e = navegacion([], false, [...PAGINAS, x]);
    // La página de prueba no tiene acción, así que es visible sin permisos y, como no está en ningún área, cae en «Más».
    expect(e.map((n) => n.area)).toEqual(["inicio", "mas"]);
    for (const n of e) if (n.tipo === "panel") for (const g of n.grupos) expect(g.paginas.length).toBeGreaterThan(0);
    const soloInicio = navegacion([], false, PAGINAS.filter((p) => p.accion === null && p.id === "inicio"));
    expect(soloInicio.map((n) => n.area)).toEqual(["inicio"]);
    expect(navegacion([], false, [])).toEqual([]);
  });

  test("en modo entrega no aparece ninguna pagina de Investigacion", () => {
    const ids = idsDe(navegacion(TODAS, true));
    for (const p of PAGINAS.filter((q) => q.seccion === "Investigación")) expect(ids).not.toContain(p.id);
    expect(ids.length).toBeGreaterThan(0);
  });

  test("las huerfanas van al final de Mas en el grupo Otras", () => {
    const x = { id: "x", titulo: "X", enUnaLinea: "Haga X", seccion: "Trabajo", accion: null, cargar: async () => ({ default: () => null }) } as PaginaDef;
    const mas = navegacion(TODAS, false, [...PAGINAS, x]).find((e) => e.area === "mas")!;
    if (mas.tipo !== "panel") throw new Error("mas debe ser panel");
    expect(mas.grupos.at(-1)).toEqual({ titulo: "Otras", paginas: [x] });
    expect(mas.grupos.map((g) => g.titulo).slice(0, 4)).toEqual(["Precios", "Obra", "Análisis", "Ajustes"]);
  });

  test("las demas areas tienen un unico grupo sin titulo", () => {
    const crear = navegacion(TODAS, false).find((e) => e.area === "crear")!;
    if (crear.tipo !== "panel") throw new Error("crear debe ser panel");
    expect(crear.grupos).toHaveLength(1);
    expect(crear.grupos[0].titulo).toBeNull();
  });

  test("un area con una sola pagina es enlace con el titulo de la pagina", () => {
    const e = navegacion(TODAS, false).find((n) => n.area === "produccion")!;
    expect(e.tipo).toBe("enlace");
    expect(e.titulo).toBe(paginaPorId("existencias")!.titulo);
  });
});

describe("areaActual", () => {
  const e = navegacion(TODAS, false);
  test("encuentra el area de la ruta", () => {
    expect(areaActual("/componer", e)).toBe("crear");
    expect(areaActual("/inicio", e)).toBe("inicio");
    expect(areaActual("/administracion", e)).toBe("mas");
  });
  test("ruta desconocida: null", () => {
    expect(areaActual("/nada", e)).toBeNull();
    expect(areaActual("/", e)).toBeNull();
  });
  test("barra final, subruta, consulta y ancla no cambian el area", () => {
    expect(areaActual("/componer/", e)).toBe("crear");
    expect(areaActual("/componer/detalle", e)).toBe("crear");
    expect(areaActual("/componer?codigo=DEMO-1", e)).toBe("crear");
    expect(areaActual("/componer#arriba", e)).toBe("crear");
  });
});
