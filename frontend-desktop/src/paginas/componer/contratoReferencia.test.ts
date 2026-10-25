import { describe, expect, test } from "vitest";
import { TIPO_DE_REFERENCIA } from "./cliente";
import { TIPOS } from "./tablas";

// Prueba de contrato (prueba en vivo 2026-10-25): el navegador mandaba `tipo=materiales` y la API solo acepta
// `material`, `equipo` y `mano_obra`: el buscador MaPreX de materiales y equipos respondia 422. El oraculo es el
// contrato publicado de la API (`docs/api.json`, que la CI regenera y compara con `api/rutas/composicion.py`), no el
// codigo del navegador: si uno de los dos cambia sin el otro, esta prueba falla.
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const contrato = JSON.parse(nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/../docs/api.json`, "utf-8")) as {
  paths: Record<string, { get?: { parameters?: { name: string; schema: { enum?: string[] } }[] } }>;
};

describe("contrato del buscador de la referencia MaPreX", () => {
  test("cada tabla manda un `tipo` que la API acepta, y entre las tres cubren todos los que acepta", () => {
    const parametro = contrato.paths["/v1/composicion/referencia"]?.get?.parameters?.find((p) => p.name === "tipo");
    const aceptados = parametro?.schema.enum ?? [];
    expect(aceptados.length).toBeGreaterThan(0);
    const enviados = TIPOS.map((tabla) => TIPO_DE_REFERENCIA[tabla]);
    expect([...enviados].sort()).toEqual([...aceptados].sort());
  });
});
