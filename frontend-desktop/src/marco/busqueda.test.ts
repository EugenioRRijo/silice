import { describe, expect, it } from "vitest";
import type { ObraDeCarpetaRespuesta } from "../api/tipos";
import { PAGINAS } from "../shell/rutas";
import { resultadosDe } from "./busqueda";
import { ofertaDe } from "./oferta";

// Carpetas y obras inventadas.
function obra(carpeta: string | null, obra_id: number, nombre: string): ObraDeCarpetaRespuesta {
  return { carpeta, carpeta_titulo: carpeta?.replace(/\.db$/, "") ?? "Carpeta de la empresa", obra_id, obra: nombre, version_codigo: null };
}
const CLINICA = obra("Carpeta Norte.db", 1, "Clínica Las Mercedes");
const TORRE = obra("Carpeta Norte.db", 2, "Torre B");
const GALPON = obra("Carpeta Sur.db", 3, "Galpón Sur");
const OBRAS = [CLINICA, TORRE, GALPON];
// Una cuenta que lo puede todo: la oferta ya no tiene valor por omisión, quien busca dice qué ofrece.
const COMPLETA = ofertaDe(
  PAGINAS.flatMap((p) => (p.accion === null ? [] : [p.accion])),
  false,
);

describe("resultadosDe: «Tramos» en toda obra", () => {
  it("la sección Tramos se encuentra en cualquier obra, tenga o no tramos guardados", () => {
    expect(resultadosDe("clin tramos", OBRAS, COMPLETA)).toEqual([
      { texto: "Clínica Las Mercedes › Tramos", detalle: "Los tramos de la vía con sus cantidades de obra.", ruta: "/obra/Carpeta%20Norte.db/1/tramos" },
    ]);
    expect(resultadosDe("torre tramos", OBRAS, COMPLETA)).toHaveLength(1);
  });

  it("sin obra no se ofrece «Tramos de la vía» (llevaría a Pendientes sin decir nada)", () => {
    expect(resultadosDe("tramos", [], COMPLETA)).toEqual([]);
  });
});

describe("resultadosDe", () => {
  it("«clin» encuentra primero la obra", () => {
    const r = resultadosDe("clin", OBRAS, COMPLETA);
    expect(r[0]).toEqual({
      texto: "Clínica Las Mercedes",
      detalle: "Carpeta Norte",
      ruta: "/obra/Carpeta%20Norte.db/1/resumen",
    });
  });

  it("«clin pres» encuentra la sección Presupuesto de esa obra con su ruta", () => {
    const r = resultadosDe("clin pres", OBRAS, COMPLETA);
    expect(r).toHaveLength(1);
    expect(r[0]?.texto).toBe("Clínica Las Mercedes › Presupuesto");
    expect(r[0]?.ruta).toBe("/obra/Carpeta%20Norte.db/1/presupuesto");
  });

  it("no distingue acentos ni mayúsculas", () => {
    expect(resultadosDe("CLINICA", OBRAS, COMPLETA)[0]?.texto).toBe("Clínica Las Mercedes");
    expect(resultadosDe("galpon", OBRAS, COMPLETA)[0]?.texto).toBe("Galpón Sur");
  });

  it("«precios» encuentra la entrada de Empresa", () => {
    const r = resultadosDe("precios", [], COMPLETA);
    expect(r[0]).toMatchObject({ texto: "Precios y catálogo", ruta: "/empresa/precios" });
  });

  it("sin texto da las 5 primeras obras de la lista, y nada más", () => {
    const siete = Array.from({ length: 7 }, (_, i) => obra("Carpeta Norte.db", i + 1, `Obra ${i + 1}`));
    expect(resultadosDe("", siete, COMPLETA).map((x) => x.texto)).toEqual(["Obra 1", "Obra 2", "Obra 3", "Obra 4", "Obra 5"]);
    expect(resultadosDe("   ", [TORRE], COMPLETA).map((x) => x.texto)).toEqual(["Torre B"]);
  });

  it("nunca devuelve más de 8", () => {
    const muchas = Array.from({ length: 20 }, (_, i) => obra("Carpeta Norte.db", i + 1, `Obra ${i + 1}`));
    expect(resultadosDe("obra", muchas, COMPLETA)).toHaveLength(8);
  });

  it("ordena obras, secciones de obras, entradas de Empresa y pantallas sin sitio", () => {
    // Con «vial» apagado (sin «Tramos») caben en las ocho la obra, sus cinco secciones y dos de Empresa. Antes se apagaba
    // «edificación», pero desde la Tarea 12 de F4 «Archivos y planos» no es de ningún módulo y no se quita con él.
    const sinVial = ofertaDe(
      PAGINAS.flatMap((p) => (p.accion === null ? [] : [p.accion])),
      false,
      ["vial"],
    );
    const textos = resultadosDe("precio", [obra(null, 1, "Precio alto")], sinVial).map((r) => r.texto);
    expect(textos[0]).toBe("Precio alto");
    expect(textos[1]).toBe("Precio alto › Presupuesto");
    const i = (t: string) => textos.indexOf(t);
    expect(i("Precio alto › Control de obra")).toBeGreaterThan(i("Precio alto › Presupuesto"));
    expect(i("Precios y catálogo")).toBeGreaterThan(i("Precio alto › Control de obra"));
    expect(i("Precios de la empresa")).toBeGreaterThan(i("Precios y catálogo"));
  });

  it("si sale la obra no repite su sección «Resumen», que lleva a la misma ruta", () => {
    const r = resultadosDe("precio", [obra(null, 1, "Precio alto")], COMPLETA);
    expect(r.map((x) => x.texto)).not.toContain("Precio alto › Resumen");
    const rutas = r.map((x) => x.ruta);
    expect(new Set(rutas).size).toBe(rutas.length);
    // Sin la obra entre los resultados, la sección sí se alcanza: «resumen» no encuentra la obra «Torre B».
    expect(resultadosDe("torre resumen", [TORRE], COMPLETA).map((x) => x.texto)).toEqual(["Torre B › Resumen"]);
  });

  it("alcanza las pantallas que no tienen sitio en el árbol", () => {
    expect(resultadosDe("simulador", [], COMPLETA)[0]).toMatchObject({ texto: "Simulador de listas", ruta: "/simulador" });
    expect(resultadosDe("historico", [], COMPLETA)[0]?.ruta).toBe("/historico");
  });

  it("no ofrece las secciones sin pantalla, ni lo que la cuenta no puede usar", () => {
    expect(resultadosDe("versiones", OBRAS, COMPLETA)).toEqual([]);
    const sinPermisos = ofertaDe([], false);
    // Control positivo: la misma búsqueda con todos los permisos sí encuentra la entrada.
    expect(resultadosDe("personas", [], COMPLETA).map((r) => r.texto)).toContain("Empresa y personas");
    expect(resultadosDe("personas", [], sinPermisos)).toEqual([]);
    expect(resultadosDe("mercado", OBRAS, sinPermisos).map((r) => r.texto)).not.toContain("Clínica Las Mercedes › Mercado");
  });

  it("sin coincidencias devuelve una lista vacía", () => {
    expect(resultadosDe("zzzz", OBRAS, COMPLETA)).toEqual([]);
  });
});
