import { describe, expect, test } from "vitest";

const proceso = (
  globalThis as unknown as {
    process: {
      cwd(): string;
      getBuiltinModule(modulo: "node:fs"): { readFileSync(ruta: string, codificacion: string): string };
    };
  }
).process;

const leerAppScss = () =>
  proceso.getBuiltinModule("node:fs").readFileSync(`${proceso.cwd()}/src/estilos/app.scss`, "utf-8");

function bloqueReducedMotion(scss: string): string {
  const inicio = scss.indexOf("@media (prefers-reduced-motion: reduce)");
  expect(inicio).toBeGreaterThan(-1);
  const abre = scss.indexOf("{", inicio);
  expect(abre).toBeGreaterThan(-1);
  let profundidad = 0;
  for (let i = abre; i < scss.length; i += 1) {
    if (scss[i] === "{") profundidad += 1;
    else if (scss[i] === "}") {
      profundidad -= 1;
      if (profundidad === 0) return scss.slice(abre + 1, i);
    }
  }
  throw new Error("Bloque @media (prefers-reduced-motion: reduce) sin cierre");
}

// DESIGN.md › Movimiento (enmienda del 2026-11-26) y guía motion: bajo prefers-reduced-motion se conservan
// las transiciones de color y el spinner de carga sigue girando lento en vez de detenerse.
describe("reglas de movimiento reducido en app.scss", () => {
  test("conserva transiciones de color con transition-property y no usa transition: none", () => {
    const bloque = bloqueReducedMotion(leerAppScss());
    expect(bloque).not.toMatch(/transition:\s*none\b/);
    expect(bloque).toMatch(/transition-property:\s*[^;]*\bcolor\b[^;]*!important/);
  });

  test("conserva scroll-behavior: auto !important", () => {
    const bloque = bloqueReducedMotion(leerAppScss());
    expect(bloque).toMatch(/scroll-behavior:\s*auto\s*!important/);
  });

  test("ralentiza el spinner de Carbon (.cds--loading) en lugar de ponerle animation: none", () => {
    const bloque = bloqueReducedMotion(leerAppScss());
    const coincidencia = bloque.match(/\.cds--loading(?::not\(\.cds--loading--stop\))?\s*\{([^}]*)\}/);
    const reglaSpinner = coincidencia?.[1] ?? "";
    expect(reglaSpinner).not.toBe("");
    expect(reglaSpinner).not.toMatch(/\bnone\b/);
    expect(reglaSpinner).toMatch(/cds--rotate/);
    expect(reglaSpinner).toMatch(/\b(?:[6-9]|10)s\b/);
  });
});
