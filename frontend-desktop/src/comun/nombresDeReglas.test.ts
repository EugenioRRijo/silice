import { describe, expect, test } from "vitest";

// Auditoría independiente antes de medicion-v1: el front no debe fijar nombres de regla que el núcleo no usa. Los
// nombres vigentes son los de core/verification/reglas.py (con tilde): R2 Cierre de la curva de inversión, R3 Coherencia
// dimensional, R5 Balance volumétrico y R7 Conciliación presupuesto-plan; R8 es «Origen de la medida». Los nombres reales
// los manda la API (`nombre_regla`); aquí solo se vigila que ningún texto ni dato de prueba invente uno distinto.
interface Fs {
  readdirSync(carpeta: string, opciones: { recursive: true }): string[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const fs = nodo.getBuiltinModule("node:fs");
const raiz = `${nodo.cwd()}/src`;

// Se arman por trozos para que este archivo no se contenga a sí mismo.
const ERRONEOS: [string, RegExp][] = [
  ["«Consistencia" + " matemática»", new RegExp("Consistencia" + " matem[aá]tica")],
  ["«Parámetros" + " de obra» como nombre de regla", new RegExp("Par[aá]metros" + " de obra")],
  ["«Consistencia" + " de montos» (R2 se llama Cierre de la curva de inversión)", new RegExp("Consistencia" + " de montos")],
  ["R5 «Trazabilidad" + " geométrica»", new RegExp("R5[^\n]{0,40}Trazabilidad" + " geom")],
  ["R3 «Origen" + " de la medida» (es R8)", new RegExp('"R3"[^\n]{0,60}Origen' + " de la medida")],
];

describe("el front no fija nombres de regla que el núcleo no usa", () => {
  const fuentes = fs
    .readdirSync(raiz, { recursive: true })
    .map((r) => r.replaceAll("\\", "/"))
    .filter((r) => /\.tsx?$/.test(r) && r !== "comun/nombresDeReglas.test.ts");

  test("ningún archivo de src contiene un nombre de regla equivocado", () => {
    expect(fuentes.length).toBeGreaterThan(100); // la guardia no recorre una lista vacía
    const malos = fuentes.flatMap((r) => {
      const texto = fs.readFileSync(`${raiz}/${r}`, "utf-8");
      return ERRONEOS.filter(([, patron]) => patron.test(texto)).map(([nombre]) => `${r}: ${nombre}`);
    });
    expect(malos).toEqual([]);
  });
});
