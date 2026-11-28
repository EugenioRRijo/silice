import { describe, expect, test } from "vitest";

// T3 (2026-11-28, 1366 px, claro y oscuro): en el calendario anual de Actividad las celdas vacías casi no se veían
// (relleno `--silice-alzado` y borde `--silice-linea` al 10 %) y la última columna salía cortada. jsdom no calcula el CSS:
// aquí se leen las reglas y se calcula el contraste de los tokens; el efecto se midió en el navegador.
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const fs = nodo.getBuiltinModule("node:fs");
const raiz = `${nodo.cwd()}/src`;
const estilos = fs.readFileSync(`${raiz}/paginas/actividad/actividad.scss`, "utf-8");
const tokens = fs.readFileSync(`${raiz}/estilos/tokens.scss`, "utf-8");

function regla(selector: string): string {
  const i = estilos.indexOf(`\n${selector} {`);
  if (i < 0) throw new Error(`No hay una regla para ${selector}`);
  const abre = estilos.indexOf("{", i);
  // Sin las reglas anidadas (&[...] { ... }): solo las declaraciones propias.
  let hondo = 0;
  let propias = "";
  for (const c of estilos.slice(abre + 1)) {
    if (c === "{") hondo++;
    else if (c === "}") {
      if (hondo === 0) break;
      hondo--;
    } else if (hondo === 0) propias += c;
  }
  return propias;
}

// El par claro/oscuro de un token `light-dark(#claro, #oscuro)`.
function par(nombre: string): [string, string] {
  const m = new RegExp(String.raw`${nombre}:\s*light-dark\(\s*(#[0-9A-Fa-f]{6})\s*,\s*(#[0-9A-Fa-f]{6})\s*\)`).exec(tokens);
  if (!m) throw new Error(`Sin par claro/oscuro para ${nombre}`);
  return [m[1]!, m[2]!];
}
function luminancia(hex: string): number {
  const canal = (i: number) => {
    const c = parseInt(hex.slice(1 + 2 * i, 3 + 2 * i), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * canal(0) + 0.7152 * canal(1) + 0.0722 * canal(2);
}
function contraste(a: string, b: string): number {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p);
  return (x! + 0.05) / (y! + 0.05);
}
const tokenDe = (valor: string) => /var\((--[\w-]+)\)/.exec(valor)?.[1] ?? "";

describe("la celda del calendario de Actividad (WCAG 1.4.11)", () => {
  const dia = regla(".silice-actividad__dia");
  const borde = /border:\s*1px solid ([^;]+);/.exec(dia)?.[1] ?? "";

  test("su borde es un token (no un color suelto) y no es la línea tenue del 10 %", () => {
    expect(borde).toMatch(/^var\(--(silice|cds)-[\w-]+\)$/);
    expect(tokenDe(borde)).not.toBe("--silice-linea");
  });

  test.each([
    ["claro", 0],
    ["oscuro", 1],
  ] as const)("el borde de la celda vacía tiene al menos 3:1 frente al fondo y a la hoja, en %s", (_modo, i) => {
    const color = par(tokenDe(borde))[i];
    expect(contraste(color, par("--silice-fondo")[i])).toBeGreaterThanOrEqual(3);
    expect(contraste(color, par("--silice-hoja")[i])).toBeGreaterThanOrEqual(3);
  });
});

describe("el calendario cabe en su caja", () => {
  test("la caja es un contenedor de tamaño en línea y fija la celda por su ancho, entre un mínimo y 0,875 rem", () => {
    const caja = regla(".silice-actividad__calendario");
    expect(caja).toMatch(/container-type:\s*inline-size/);
    expect(caja).toMatch(/--silice-actividad-celda:\s*clamp\(\s*[\d.]+rem\s*,[^;]*100cqw[^;]*--silice-actividad-columnas[^;]*,\s*0\.875rem\s*\)/);
  });
});
