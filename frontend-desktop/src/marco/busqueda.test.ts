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

  // F6, T4: «Precios y catálogo» es un espacio con cuatro herramientas; el nombre del espacio encuentra cada una, en su ruta.
  it("«precios» encuentra las herramientas del espacio Precios y catálogo, en sus rutas", () => {
    const r = resultadosDe("precios", [], COMPLETA);
    expect(r.map((x) => x.ruta)).toEqual(expect.arrayContaining(["/precios/catalogo", "/precios/listas", "/precios/indices", "/precios/simulador"]));
    expect(r[0]).toMatchObject({ texto: "Catálogo de partidas e insumos", ruta: "/precios/catalogo" });
  });

  it("quien arma (sin administrar precios) encuentra «precios» en el Catálogo, no en los precios de la empresa", () => {
    const arma = ofertaDe(["leer_proyecto", "editar_hoja"], false);
    const rutas = resultadosDe("precios", [], arma).map((x) => x.ruta);
    expect(rutas).toContain("/precios/catalogo");
    expect(rutas).not.toContain("/precios/listas");
  });

  it("«auditar» y «arenera» llevan a los espacios Auditoría y Producción", () => {
    expect(resultadosDe("auditar", [], COMPLETA).map((x) => x.ruta)).toEqual(["/auditoria/subir", "/auditoria/libros", "/auditoria/historial"]);
    expect(resultadosDe("existencias", [], COMPLETA)[0]).toMatchObject({ texto: "Existencias de la arenera", ruta: "/produccion/existencias" });
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

  it("ordena obras, secciones de obras, secciones de la Cuenta y pantallas sin sitio", () => {
    // Las nueve secciones de una obra (Resumen, Presupuesto, Tramos, Archivos y planos, Versiones, Aprobaciones, Mercado,
    // Control de obra y Riesgo) ya no caben con las dos pantallas de Empresa cuyo orden se mira. Con «vial» y «riesgo»
    // apagados se van «Tramos» y «Riesgo», y sin `aprobar_version`, `revisar_paquete` ni `entregar_paquete` (F6, T5: una sección
    // con una subvista usable se ofrece) se va «Aprobaciones»; «Resumen» no sale porque lleva a
    // la misma ruta que la obra. Quedan la obra, sus cinco secciones y dos de Empresa: ocho. No se apaga «edificación»: desde la Tarea 12 de F4 «Archivos y
    // planos» no es de ningún módulo y no se quita con él.
    const sinVialNiAprobar = ofertaDe(
      PAGINAS.flatMap((p) => (p.accion === null || ["aprobar_version", "revisar_paquete", "entregar_paquete"].includes(p.accion) ? [] : [p.accion])),
      false,
      ["vial", "riesgo"],
    );
    const textos = resultadosDe("precio", [obra(null, 1, "Precio alto")], sinVialNiAprobar).map((r) => r.texto);
    expect(textos[0]).toBe("Precio alto");
    expect(textos[1]).toBe("Precio alto › Presupuesto");
    const i = (t: string) => textos.indexOf(t);
    expect(i("Precio alto › Control de obra")).toBeGreaterThan(i("Precio alto › Presupuesto"));
    expect(i("Catálogo de partidas e insumos")).toBeGreaterThan(i("Precio alto › Control de obra"));
    expect(i("Precios de la empresa")).toBeGreaterThan(i("Catálogo de partidas e insumos"));
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
    expect(resultadosDe("simulador", [], COMPLETA)[0]).toMatchObject({ texto: "Simulador de listas", ruta: "/precios/simulador" });
    expect(resultadosDe("historico", [], COMPLETA)).toEqual([]);
  });

  // F4, Tarea 9, baja 20: buscar parecidas es una salida de «Agregar partida», no una pantalla.
  it("no ofrece «Partidas similares»", () => {
    expect(resultadosDe("similares", [], COMPLETA)).toEqual([]);
  });

  it("ofrece las secciones que ya tienen pantalla, y no lo que la cuenta no puede usar", () => {
    // «Archivos y planos» (Tarea 11 de F4) y «Versiones» (Tarea 6) ya tienen pantalla: se ofrecen en cada obra, y no a
    // quien no lee las obras.
    expect(resultadosDe("clin archivos", OBRAS, COMPLETA).map((r) => r.ruta)).toEqual(["/obra/Carpeta%20Norte.db/1/archivos"]);
    expect(resultadosDe("clin versiones", OBRAS, COMPLETA).map((r) => r.ruta)).toEqual(["/obra/Carpeta%20Norte.db/1/versiones"]);
    expect(resultadosDe("archivos", OBRAS, ofertaDe([], false))).toEqual([]);
    expect(resultadosDe("versiones", OBRAS, ofertaDe([], false))).toEqual([]);
    const sinPermisos = ofertaDe([], false);
    // Control positivo: la misma búsqueda con todos los permisos sí encuentra la entrada.
    expect(resultadosDe("personas", [], COMPLETA).map((r) => [r.texto, r.ruta])).toContainEqual(["Cuentas y permisos", "/cuenta/cuentas"]);
    expect(resultadosDe("personas", [], sinPermisos)).toEqual([]);
    expect(resultadosDe("mercado", OBRAS, sinPermisos).map((r) => r.texto)).not.toContain("Clínica Las Mercedes › Mercado");
  });

  it("sin coincidencias devuelve una lista vacía", () => {
    expect(resultadosDe("zzzz", OBRAS, COMPLETA)).toEqual([]);
  });
});

// F6, T6: «Empresa y personas» y «Ayuda» pasaron a la Cuenta; el buscador ofrece sus secciones por su ruta canónica y solo
// las que la cuenta puede usar.
describe("resultadosDe: las secciones de la Cuenta (F6, T6)", () => {
  // «Carpetas» pide además `cambiar_caso`, que ninguna pantalla exige por sí sola: la cuenta completa la suma.
  const CON_CARPETAS = ofertaDe([...PAGINAS.flatMap((p) => (p.accion === null ? [] : [p.accion])), "cambiar_caso"], false);
  const rutas = (texto: string, oferta = CON_CARPETAS) => resultadosDe(texto, [], oferta).map((r) => [r.texto, r.ruta]);

  it("encuentra cada sección por su título", () => {
    expect(rutas("tamano de letra")).toContainEqual(["Pantalla y tamaño de letra", "/cuenta/preferencias"]);
    expect(rutas("acerca")).toContainEqual(["Ayuda y acerca de Sílice", "/cuenta/ayuda"]);
    expect(rutas("empresa y tema")).toContainEqual(["Empresa y tema", "/cuenta/empresa"]);
    expect(rutas("carpetas")).toContainEqual(["Carpetas", "/cuenta/carpetas"]);
    expect(rutas("instalacion")).toContainEqual(["Especialidades, IA e instalación", "/cuenta/sistema"]);
  });

  it("«Carpetas» no se ofrece a quien administra pero no cambia de carpeta", () => {
    expect(rutas("carpetas", COMPLETA)).toEqual([]);
    expect(rutas("carpetas")).toEqual([["Carpetas", "/cuenta/carpetas"]]);
  });

  it("a quien no administra solo le ofrece preferencias y ayuda", () => {
    const rita = ofertaDe(["leer_proyecto", "revisar_paquete"], false);
    expect(rutas("cuentas", rita)).toEqual([]);
    expect(rutas("carpetas", rita)).toEqual([]);
    expect(rutas("letra", rita)).toEqual([["Pantalla y tamaño de letra", "/cuenta/preferencias"]]);
    expect(rutas("ayuda", rita)).toEqual([["Ayuda y acerca de Sílice", "/cuenta/ayuda"]]);
  });
});
