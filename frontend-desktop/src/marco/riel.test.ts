import { describe, expect, it } from "vitest";
import * as riel from "./riel";
import { iconoDeOpcion } from "./riel";

// La barra reducida se recuerda en UNA sola clave, la del marco (`silice_sidebar_collapsed`, useWorkspaceLayout): el riel ya
// no guarda la suya (antes `silice-riel-reducido`), que podía contradecir a la del marco.
describe("riel: no guarda su propio estado", () => {
  it("no exporta una clave ni funciones de lectura o guardado de la barra reducida", () => {
    expect(Object.keys(riel).sort()).toEqual(["iconoDeOpcion"]);
  });
});

describe("riel: el icono de cada opción", () => {
  it("las opciones conocidas tienen un icono propio y las desconocidas uno de respaldo", () => {
    for (const id of ["vista-general", "nueva-obra", "auditoria", "precios", "produccion", "presupuesto", "tramos", "archivos", "mercado", "versiones", "control", "riesgo"]) {
      expect(iconoDeOpcion(id)).toBeDefined();
    }
    expect(iconoDeOpcion("no-existe")).toBe(iconoDeOpcion("otra-que-tampoco"));
  });

  it("opciones distintas no comparten icono cuando significan cosas distintas", () => {
    expect(iconoDeOpcion("presupuesto")).not.toBe(iconoDeOpcion("tramos"));
    expect(iconoDeOpcion("mercado")).not.toBe(iconoDeOpcion("versiones"));
    expect(iconoDeOpcion("auditoria")).not.toBe(iconoDeOpcion("precios"));
  });
});
