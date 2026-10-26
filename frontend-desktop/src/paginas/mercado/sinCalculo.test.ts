import { describe, expect, test } from "vitest";

// La interfaz no calcula montos (Restricciones globales del plan; criterio B3 del arbitro): los precios llegan de la API
// como texto con punto y se formatean una vez; lo tecleado se envia tal cual. jsdom no recorre todos los estados de la
// pantalla: se lee el fuente, sin comentarios, como `sinJergaInterna.test.ts`.
interface Fs {
  readdirSync(carpeta: string): string[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const fs = nodo.getBuiltinModule("node:fs");
const carpeta = `${nodo.cwd()}/src/paginas/mercado`;

// Lo que convertiria un monto en numero de coma flotante o lo redondearia.
const CALCULO = /\b(?:Number|parseFloat|parseInt)\s*\(|\bMath\.|\.toFixed\s*\(|\.toPrecision\s*\(|\bNumber\.|\bBigInt\s*\(/;

function sinComentarios(fuente: string): string {
  return fuente
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .split(/\r?\n/)
    .map((linea) => linea.replace(/(^|[^:"'`])\/\/.*$/, "$1"))
    .join("\n");
}

const fuentes = fs.readdirSync(carpeta).filter((r) => /\.tsx?$/.test(r) && !/\.test\.tsx?$/.test(r));

describe("el estudio de mercado no convierte montos en numeros", () => {
  test("la guardia detecta las conversiones y deja pasar los textos", () => {
    for (const malo of ["Number(precio)", "parseFloat(x)", "parseInt(dias, 10)", "Math.round(a)", "a.toFixed(2)", "Number.isFinite(x)"]) {
      expect(CALCULO.test(sinComentarios(malo)), malo).toBe(true);
    }
    expect(CALCULO.test(sinComentarios('const t = formatoEsVe(precio); // Number(precio) no'))).toBe(false);
  });

  test("ninguna fuente de la pagina usa Number, parseFloat, parseInt, Math ni toFixed", () => {
    expect(fuentes).toEqual(expect.arrayContaining(["index.tsx", "logica.ts"])); // la guardia no recorre una lista vacia
    const conCalculo = fuentes.filter((r) => CALCULO.test(sinComentarios(fs.readFileSync(`${carpeta}/${r}`, "utf-8"))));
    expect(conCalculo).toEqual([]);
  });
});
