import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { CampoDeCelda } from "../paginas/hoja/CampoDeCelda";

interface Fs {
  readdirSync(carpeta: string, o: { withFileTypes: true }): { name: string; isDirectory(): boolean }[];
  readFileSync(ruta: string, codificacion: string): string;
}
interface Ruta {
  join(...partes: string[]): string;
  basename(ruta: string): string;
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
    else if (/\.tsx$/.test(e.name) && !/\.test\.tsx$/.test(e.name)) salida.push(completa);
  }
  return salida;
}

// 3e-3, H-3: el TextInput de Carbon monta un <span role="alert"> vacío por campo (900 en el Plan). Solo `CampoTexto`
// (y `AreaTexto`) pueden usar los componentes de Carbon que lo montan; el resto de la interfaz pasa por ellos.
describe("regiones vivas vacías (H-3)", () => {
  test("ningún componente usa TextInput ni TextArea de Carbon directamente", () => {
    const permitidos = new Set(["CampoTexto.tsx", "AreaTexto.tsx"]);
    const infractores = fuentes(`${nodo.cwd()}/src`)
      .filter((f) => !permitidos.has(ruta.basename(f)))
      .filter((f) => /<(TextInput|TextArea)[\s>]/.test(fs.readFileSync(f, "utf-8")))
      .map((f) => ruta.relative(nodo.cwd(), f));
    expect(infractores).toEqual([]);
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
