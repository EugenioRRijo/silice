import { describe, expect, test } from "vitest";

// La portada web es solo de pruebas (Eugenio, 2026-11-22): `npm run build` (lo que compila la CI y empaqueta el
// instalador) deja fuera portada.html; solo `npm run build:portada` (`vite build --mode portada`) la agrega a dist.
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs };
  }
).process;
const fs = nodo.getBuiltinModule("node:fs");
const paquete = JSON.parse(fs.readFileSync(`${nodo.cwd()}/package.json`, "utf-8")) as {
  scripts: Record<string, string>;
};

type Entradas = Record<string, string>;
interface Configuracion {
  build?: { rollupOptions?: { input?: Entradas } };
}
type FabricaDeConfiguracion = (entorno: { mode: string; command: "build" | "serve" }) => Configuracion;

// Ruta en variable: vite.config.ts es del proyecto de Node (tsconfig.node.json), no de la interfaz.
const RUTA_CONFIGURACION = "../../vite.config.ts";

async function entradas(mode: string): Promise<string[]> {
  const modulo = (await import(/* @vite-ignore */ RUTA_CONFIGURACION)) as { default: FabricaDeConfiguracion | Configuracion };
  const config = typeof modulo.default === "function" ? modulo.default({ mode, command: "build" }) : modulo.default;
  return Object.keys(config.build?.rollupOptions?.input ?? {}).sort();
}

describe("compilación de la portada de pruebas", () => {
  test("la compilación del producto solo lleva la suite (index.html)", async () => {
    expect(await entradas("production")).toEqual(["main"]);
  });

  test("con --mode portada se agrega portada.html junto a la suite", async () => {
    expect(await entradas("portada")).toEqual(["main", "portada"]);
  });

  test("npm run build no pide la portada y build:portada la compila con su modo", () => {
    expect(paquete.scripts.build).toBe("tsc -b && vite build");
    expect(paquete.scripts["build:portada"]).toBe("tsc -b && vite build --mode portada");
    expect(paquete.scripts.dist).not.toContain("portada");
  });
});
