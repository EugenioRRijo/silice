import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, test } from "vitest";

// Eugenio (2026-11-23), comparando Control de obra con Presupuesto: «el top bar de las obras individuales son
// diferentes ... sé consistente ... lo mejor sería tener un fondo como lo tiene el control de obra». Una sola forma de
// pestañas internas en toda la app: la de Carbon con fondo (`contained`). Esta guardia falla si una pantalla vuelve a
// armar sus pestañas de línea, para que la consistencia no dependa de acordarse.

const RAIZ = join(__dirname, "..");

function archivosTsx(dir: string): string[] {
  return readdirSync(dir).flatMap((nombre) => {
    const ruta = join(dir, nombre);
    if (statSync(ruta).isDirectory()) return archivosTsx(ruta);
    return nombre.endsWith(".tsx") && !nombre.includes(".test.") ? [ruta] : [];
  });
}

// Cada apertura de `<TabList ...>` con sus atributos, aunque ocupen varias líneas.
function aperturasDeTabList(codigo: string): string[] {
  return [...codigo.matchAll(/<TabList\b[^>]*>/g)].map((m) => m[0]);
}

describe("pestañas internas con fondo en toda la app", () => {
  const archivos = archivosTsx(RAIZ);

  test("la guardia encuentra las pestañas de Control, del Presupuesto y de Mercado", () => {
    const conPestanas = archivos.filter((a) => aperturasDeTabList(readFileSync(a, "utf8")).length > 0).map((a) => relative(RAIZ, a).replaceAll("\\", "/"));
    expect(conPestanas).toEqual(expect.arrayContaining(["paginas/control/index.tsx", "paginas/hoja/pestanas.tsx", "paginas/mercado/index.tsx"]));
  });

  test("cada <TabList> lleva `contained`, como las de Control de obra", () => {
    const sinFondo = archivos.flatMap((a) =>
      aperturasDeTabList(readFileSync(a, "utf8"))
        .filter((t) => !/\bcontained\b/.test(t))
        .map((t) => `${relative(RAIZ, a).replaceAll("\\", "/")}: ${t}`),
    );
    expect(sinFondo).toEqual([]);
  });
});
