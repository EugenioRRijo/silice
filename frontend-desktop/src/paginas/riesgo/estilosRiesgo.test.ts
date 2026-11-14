import { describe, expect, test } from "vitest";

// Resto de la pasada en navegador de F8: en la fila «Proyectar» el texto de ayuda de «Fecha de inicio» dejaba su campo
// entre 23 y 30 px más arriba que «Trayectorias» y el botón, porque la fila alineaba por abajo. jsdom no calcula el
// diseño: aquí solo se comprueba que las reglas estén escritas; el efecto se MIDE en navegador (1056, 1366 y 1920 px, con
// letra normal, grande y muy grande).
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const estilos = nodo
  .getBuiltinModule("node:fs")
  .readFileSync(`${nodo.cwd()}/src/paginas/riesgo/riesgo.scss`, "utf-8")
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .replace(/\/\/.*$/gm, "");

function regla(selector: string): string {
  const i = estilos.indexOf(`${selector} {`);
  expect(i, `falta la regla ${selector}`).toBeGreaterThanOrEqual(0);
  let hondo = 0;
  const desde = estilos.indexOf("{", i);
  for (let k = desde; k < estilos.length; k++) {
    if (estilos[k] === "{") hondo++;
    if (estilos[k] === "}" && --hondo === 0) return estilos.slice(desde + 1, k);
  }
  throw new Error(`regla ${selector} sin cierre`);
}

describe("fila «Proyectar» de Riesgo: campos alineados por su caja de entrada", () => {
  test("la fila alinea por el inicio de sus hijos, no por abajo (la ayuda de un campo no sube a los demás)", () => {
    const cuerpo = regla(".riesgo-acciones");
    expect(cuerpo).toMatch(/align-items:\s*flex-start/);
    expect(cuerpo).not.toMatch(/align-items:\s*flex-end/);
  });

  test("el botón y la espera de una sección con campos bajan lo que mide el rótulo, para quedar a la altura de la caja", () => {
    const cuerpo = regla(".riesgo-seccion .riesgo-acciones > :not(.cds--form-item)");
    expect(cuerpo).toMatch(/margin-block-start:\s*1\.5rem/);
  });
});
