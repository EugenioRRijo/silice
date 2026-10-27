import { describe, expect, it } from "vitest";
import type { ObraDeCarpetaRespuesta } from "../api/tipos";
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

describe("resultadosDe", () => {
  it("«clin» encuentra primero la obra", () => {
    const r = resultadosDe("clin", OBRAS);
    expect(r[0]).toEqual({
      texto: "Clínica Las Mercedes",
      detalle: "Carpeta Norte",
      ruta: "/obra/Carpeta%20Norte.db/1/resumen",
    });
  });

  it("«clin pres» encuentra la sección Presupuesto de esa obra con su ruta", () => {
    const r = resultadosDe("clin pres", OBRAS);
    expect(r).toHaveLength(1);
    expect(r[0]?.texto).toBe("Clínica Las Mercedes › Presupuesto");
    expect(r[0]?.ruta).toBe("/obra/Carpeta%20Norte.db/1/presupuesto");
  });

  it("no distingue acentos ni mayúsculas", () => {
    expect(resultadosDe("CLINICA", OBRAS)[0]?.texto).toBe("Clínica Las Mercedes");
    expect(resultadosDe("galpon", OBRAS)[0]?.texto).toBe("Galpón Sur");
  });

  it("«precios» encuentra la entrada de Empresa", () => {
    const r = resultadosDe("precios", []);
    expect(r[0]).toMatchObject({ texto: "Precios y catálogo", ruta: "/empresa/precios" });
  });

  it("sin texto da las 5 primeras obras de la lista, y nada más", () => {
    const siete = Array.from({ length: 7 }, (_, i) => obra("Carpeta Norte.db", i + 1, `Obra ${i + 1}`));
    expect(resultadosDe("", siete).map((x) => x.texto)).toEqual(["Obra 1", "Obra 2", "Obra 3", "Obra 4", "Obra 5"]);
    expect(resultadosDe("   ", [TORRE]).map((x) => x.texto)).toEqual(["Torre B"]);
  });

  it("nunca devuelve más de 8", () => {
    const muchas = Array.from({ length: 20 }, (_, i) => obra("Carpeta Norte.db", i + 1, `Obra ${i + 1}`));
    expect(resultadosDe("obra", muchas)).toHaveLength(8);
  });

  it("ordena obras, secciones de obras, entradas de Empresa y pantallas sin sitio", () => {
    const textos = resultadosDe("precio", [obra(null, 1, "Precio alto")]).map((r) => r.texto);
    expect(textos[0]).toBe("Precio alto");
    expect(textos[1]).toBe("Precio alto › Resumen");
    const i = (t: string) => textos.indexOf(t);
    expect(i("Precio alto › Control de obra")).toBeGreaterThan(i("Precio alto › Resumen"));
    expect(i("Precios y catálogo")).toBeGreaterThan(i("Precio alto › Control de obra"));
    expect(i("Precios de la empresa")).toBeGreaterThan(i("Precios y catálogo"));
  });

  it("alcanza las pantallas que no tienen sitio en el árbol", () => {
    expect(resultadosDe("simulador", [])[0]).toMatchObject({ texto: "Simulador de listas", ruta: "/simulador" });
    expect(resultadosDe("historico", [])[0]?.ruta).toBe("/historico");
  });

  it("no ofrece las secciones sin pantalla, ni lo que la cuenta no puede usar", () => {
    expect(resultadosDe("archivos", OBRAS)).toEqual([]);
    expect(resultadosDe("versiones", OBRAS)).toEqual([]);
    const sinPermisos = ofertaDe([], false);
    expect(resultadosDe("personas", [], sinPermisos)).toEqual([]);
    expect(resultadosDe("mercado", OBRAS, sinPermisos).map((r) => r.texto)).not.toContain("Clínica Las Mercedes › Mercado");
  });

  it("sin coincidencias devuelve una lista vacía", () => {
    expect(resultadosDe("zzzz", OBRAS)).toEqual([]);
  });
});
