import { describe, expect, test } from "vitest";

// Revisión del rediseño (2026-11-22): texto de 0,75 rem por debajo de 4,5:1 (WCAG 1.4.3) y la severidad de los
// hallazgos de la ventana principal dicha solo con el color del borde (WCAG 1.4.1). Se calcula con la fórmula WCAG,
// como `indicadores/contrasteAviso.test.ts`.
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const fs = nodo.getBuiltinModule("node:fs");
const raiz = nodo.cwd();
const scss = fs.readFileSync(`${raiz}/src/portada/portada.scss`, "utf-8");
const doc = new DOMParser().parseFromString(fs.readFileSync(`${raiz}/portada.html`, "utf-8"), "text/html");

const bloqueRaiz = /:root\s*\{([^}]*)\}/.exec(scss)?.[1] ?? "";
const tokens = Object.fromEntries([...bloqueRaiz.matchAll(/--([\w-]+):\s*(#[0-9a-f]{6})\s*;/gi)].map((m) => [m[1], m[2].toLowerCase()]));
const token = (nombre: string): string => {
  const valor = tokens[nombre];
  if (!valor) throw new Error(`falta el token --${nombre} en :root de portada.scss`);
  return valor;
};

function luminancia(hex: string): number {
  const canal = (i: number) => {
    const c = parseInt(hex.slice(1 + 2 * i, 3 + 2 * i), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * canal(0) + 0.7152 * canal(1) + 0.0722 * canal(2);
}
function contraste(a: string, b: string): number {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

describe("portada de pruebas: contraste de los tokens de texto (WCAG 1.4.3)", () => {
  const fondos = ["stone", "surface"];

  test.each(["ink", "muted", "muted-soft", "ok", "err", "atipico"])("--%s llega a 4,5:1 sobre --stone y --surface", (nombre) => {
    for (const fondo of fondos) {
      expect(contraste(token(nombre), token(fondo)), `--${nombre} sobre --${fondo}`).toBeGreaterThanOrEqual(4.5);
    }
  });

  test("el atípico es el morado 60 de Carbon (#8a3ffc), reservado a los precios atípicos (DESIGN.md)", () => {
    expect(token("atipico")).toBe("#8a3ffc");
    expect(scss).toMatch(/\.finding--ml\s*\{[^}]*em\s*\{[^}]*color:\s*var\(--atipico\)/);
    expect(scss).not.toMatch(/#5925dc/i);
  });

  test("los íconos de severidad de la ventana llegan a 3:1 sobre --surface (WCAG 1.4.11)", () => {
    expect(contraste(token("sev-critico"), token("surface"))).toBeGreaterThanOrEqual(3);
    expect(contraste(token("sev-advertencia-icono"), token("surface"))).toBeGreaterThanOrEqual(3);
  });

  test("la palabra de cada fila del panel de hallazgos llega a 4,5:1 sobre el fondo de su fila", () => {
    const filas = [...scss.matchAll(/\.finding--(\w+)\s*\{\s*background-color:\s*(#[0-9a-f]{6});[^{}]*em\s*\{\s*color:\s*([^;]+);/gi)];
    expect(filas.map((f) => f[1])).toEqual(["err", "ml", "warn"]);
    for (const [, clase, fondo, color] of filas) {
      const hex = /var\(--([\w-]+)\)/.exec(color)?.[1];
      const valor = hex ? token(hex) : color.trim();
      expect(contraste(valor, fondo), `.finding--${clase}`).toBeGreaterThanOrEqual(4.5);
    }
  });
});

describe("portada de pruebas: la severidad se dice con ícono y palabra (WCAG 1.4.1)", () => {
  // El mismo vocabulario que la aplicación (comun/Severidad.tsx) y que el marcador de atípicos (RF-100).
  const PALABRAS = new Set(["Crítico", "Error", "Advertencia", "Información", "Atípico"]);

  test("cada hallazgo de la ventana principal lleva un ícono decorativo y su palabra visible", () => {
    const hallazgos = [...doc.querySelectorAll(".ventana__hallazgos li.ventana__hallazgo")];
    expect(hallazgos).toHaveLength(3);
    for (const li of hallazgos) {
      const severidad = li.querySelector(".ventana__sev");
      expect(severidad, li.textContent ?? "").not.toBeNull();
      expect(severidad?.querySelector("svg[aria-hidden='true'][focusable='false']"), li.textContent ?? "").not.toBeNull();
      expect(PALABRAS.has(severidad?.textContent?.trim() ?? "")).toBe(true);
    }
    expect(hallazgos.map((li) => li.querySelector(".ventana__sev")?.textContent?.trim())).toEqual(["Crítico", "Advertencia", "Advertencia"]);
  });

  test("las filas del panel de hallazgos usan el mismo vocabulario, también con su ícono", () => {
    const palabras = [...doc.querySelectorAll(".finding em")];
    expect(palabras.map((em) => em.textContent?.trim())).toEqual(["Crítico", "Atípico", "Advertencia"]);
    for (const em of palabras) expect(em.querySelector("svg[aria-hidden='true'][focusable='false']"), em.textContent ?? "").not.toBeNull();
  });
});
