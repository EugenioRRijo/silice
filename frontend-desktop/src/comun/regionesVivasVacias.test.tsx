import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { CampoDeCelda } from "../paginas/hoja/CampoDeCelda";

interface Fs {
  readdirSync(carpeta: string, o: { withFileTypes: true }): { name: string; isDirectory(): boolean }[];
  readFileSync(ruta: string, codificacion: string): string;
}
interface Ruta {
  join(...partes: string[]): string;
  relative(de: string, a: string): string;
}

const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs;
      getBuiltinModule(nombre: "node:path"): Ruta };
  }
).process;
const fs = nodo.getBuiltinModule("node:fs");
const ruta = nodo.getBuiltinModule("node:path");

function fuentes(carpeta: string): string[] {
  const salida: string[] = [];
  for (const e of fs.readdirSync(carpeta, { withFileTypes: true })) {
    const completa = ruta.join(carpeta, e.name);
    if (e.isDirectory()) salida.push(...fuentes(completa));
    else if (/\.tsx?$/.test(e.name) && !/\.test\.tsx?$/.test(e.name)) salida.push(completa);
  }
  return salida;
}

// Las unicas rutas que pueden tocar TextInput / TextArea de Carbon, por ruta exacta relativa a la raiz del front (un
// archivo con el mismo nombre en otra carpeta NO queda permitido).
const PERMITIDOS = new Set(["src/comun/CampoTexto.tsx", "src/comun/AreaTexto.tsx"]);

// Detecta cualquier via de llegar a los componentes de Carbon que montan la region viva vacia: importarlos por nombre
// (con o sin alias), importar el paquete entero o por defecto (`C.TextInput`), usar una ruta profunda del paquete,
// `require` / `import()` dinamicos del paquete, o crearlos con `createElement` / JSX.
export function usaCamposDeCarbon(codigo: string): boolean {
  const importaNombre = /import\s*(?:type\s*)?\{[^}]*\b(TextInput|TextArea)\b[^}]*\}\s*from\s*["']@carbon\/react["']/;
  const importaTodo = /import\s+(?:\*\s+as\s+\w+|\w+)(?:\s*,\s*\{[^}]*\})?\s+from\s*["']@carbon\/react["']/;
  const rutaProfunda = /["']@carbon\/react\/[^"']*(TextInput|TextArea)/;
  const dinamico = /(?:require\(|import\()\s*["']@carbon\/react["']/;
  const jsxOCrear = /<\s*(?:\w+\.)?(TextInput|TextArea)[\s>/]|createElement\(\s*(?:\w+\.)?(TextInput|TextArea)\b/;
  return [importaNombre, importaTodo, rutaProfunda, dinamico, jsxOCrear].some((r) => r.test(codigo));
}

// 3e-3, H-3: el TextInput de Carbon monta un <span role="alert"> vacío por campo (900 en el Plan). Solo `CampoTexto`
// (y `AreaTexto`) pueden usar los componentes de Carbon que lo montan; el resto de la interfaz pasa por ellos.
describe("regiones vivas vacías (H-3)", () => {
  test("ningún componente usa TextInput ni TextArea de Carbon directamente (por ruta exacta)", () => {
    const infractores = fuentes(`${nodo.cwd()}/src`)
      .map((f) => ruta.relative(nodo.cwd(), f).split("\\").join("/"))
      .filter((rel) => !PERMITIDOS.has(rel))
      .filter((rel) => usaCamposDeCarbon(fs.readFileSync(ruta.join(nodo.cwd(), rel), "utf-8")));
    expect(infractores).toEqual([]);
  });

  test("las dos rutas permitidas existen y sí usan los de Carbon", () => {
    for (const rel of PERMITIDOS) expect(usaCamposDeCarbon(fs.readFileSync(ruta.join(nodo.cwd(), rel), "utf-8"))).toBe(true);
  });

  test("el detector ve alias, importación del paquete entero, rutas profundas y createElement", () => {
    const malos = [
      'import { TextInput } from "@carbon/react";',
      'import { Button, TextArea as Area } from "@carbon/react";',
      "import {\n  TextInput as Campo,\n} from '@carbon/react';",
      'import * as C from "@carbon/react"; const x = <C.TextInput id="a" />;',
      'import Carbon from "@carbon/react"; Carbon.TextArea;',
      'import TextInput from "@carbon/react/lib/components/TextInput";',
      'const { TextInput } = require("@carbon/react");',
      'const m = await import("@carbon/react");',
      'createElement(TextInput, {})',
      "<TextArea\n id=\"x\" />",
    ];
    for (const m of malos) expect(usaCamposDeCarbon(m), m).toBe(true);
    const buenos = [
      'import { Button, Select } from "@carbon/react";',
      'import { CampoTexto } from "../../comun/CampoTexto";',
      'import { AreaTexto } from "../../comun/AreaTexto";',
      "<CampoTexto id=\"a\" />",
    ];
    for (const b of buenos) expect(usaCamposDeCarbon(b), b).toBe(false);
  });

  test("una tabla de celdas editables no deja ninguna región role=alert vacía", () => {
    const { container } = render(
      <table>
        <tbody>
          {Array.from({ length: 30 }, (_, i) => (
            <tr key={i}>
              <td>
                <CampoDeCelda id={`c${i}`} etiqueta={`Cantidad fila ${i}`} valor="1" alCambiar={() => {}} alRestaurar={() => {}} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>,
    );
    const vacias = Array.from(container.querySelectorAll('[role="alert"]')).filter((a) => (a.textContent ?? "").trim() === "");
    expect(vacias).toHaveLength(0);
  });

  test("una celda inválida sigue mostrando su texto de error", () => {
    const { getByText } = render(
      <CampoDeCelda id="x" etiqueta="Cantidad" valor="a" invalido textoInvalido="Valor no válido" alCambiar={() => {}} alRestaurar={() => {}} />,
    );
    expect(getByText("Valor no válido")).toBeInTheDocument();
  });
});
