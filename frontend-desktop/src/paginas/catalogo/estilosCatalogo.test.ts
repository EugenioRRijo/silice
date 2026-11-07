import { describe, expect, test } from "vitest";

// Resto de la pasada en navegador de F8: con letra muy grande a 1056 px el Catálogo medía 1.248 px y se desplazaba en
// horizontal: la pista implícita de la rejilla de la página (`auto`) crecía hasta el ancho mínimo de su contenido y el
// título, la ayuda y el buscador se iban más allá de la ventana. jsdom no calcula el diseño: aquí se comprueban las reglas
// escritas; el efecto se MIDE en navegador (1056, 1366 y 1920 px, con letra normal, grande y muy grande).
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const leer = (ruta: string): string =>
  nodo
    .getBuiltinModule("node:fs")
    .readFileSync(`${nodo.cwd()}/src/paginas/catalogo/${ruta}`, "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/.*$/gm, "");

describe("ancho del Catálogo con letra muy grande", () => {
  test("la pista de la rejilla no crece más que la página (minmax(0, 1fr)), así el contenido se ajusta al ancho", () => {
    const m = /\.silice-catalogo\s*\{([^}]*)\}/.exec(leer("catalogo.scss"));
    expect(m, "falta la regla .silice-catalogo").not.toBeNull();
    expect(m![1]).toMatch(/grid-template-columns:\s*minmax\(0,\s*1fr\)/);
  });

  test("la página carga su hoja de estilos y su sección lleva la clase", () => {
    const fuente = leer("index.tsx");
    expect(fuente).toMatch(/import "\.\/catalogo\.scss"/);
    expect(fuente).toMatch(/className="silice-pagina silice-catalogo"/);
  });
});
