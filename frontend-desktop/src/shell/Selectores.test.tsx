import { describe, expect, test } from "vitest";
import type { ProyectoRespuesta } from "../api/tipos";
import { nombreDeCarpeta, rotuloDeProyecto } from "./Selectores";

// Plan de modulos, MOD-3b: los selectores «Carpeta de trabajo» y «Proyecto» de la barra se retiraron (los reemplaza el
// selector de obra); de este modulo quedan los dos rotulos que usan el selector, el dialogo de carpetas y Componer.

const obra = (codigo: string, nombre: string, version_vigente: number | null): ProyectoRespuesta => ({
  codigo,
  nombre,
  version_vigente,
  actualizado: null,
  cliente: "",
  ubicacion: "",
});

describe("nombreDeCarpeta", () => {
  test("quita el .db final y solo ese", () => {
    expect(nombreDeCarpeta("demo.db")).toBe("demo");
    expect(nombreDeCarpeta("obra.v2.db")).toBe("obra.v2");
    expect(nombreDeCarpeta("x")).toBe("x");
  });
});

describe("rotuloDeProyecto", () => {
  const TORRE = obra("8", "Torre B", null);
  const CASA = obra("7", "Casa Demo", 1);

  // F11 (BCP-6 §5.2): una obra sin version guardada lo dice en su rotulo.
  test("una obra sin versión guardada lo dice; una con versión, no", () => {
    expect(rotuloDeProyecto(TORRE, [TORRE, CASA])).toBe("Torre B (sin versión guardada)");
    expect(rotuloDeProyecto(CASA, [TORRE, CASA])).toBe("Casa Demo");
  });

  // VB-20: el codigo es un numero interno; solo si dos obras se llaman igual, el codigo las distingue.
  test("dos obras con el mismo nombre se distinguen por su código", () => {
    const a = obra("3", "OBRA-GENERADA", 1);
    const b = obra("4", "OBRA-GENERADA", null);
    expect(rotuloDeProyecto(a, [a, b, CASA])).toBe("OBRA-GENERADA (3)");
    expect(rotuloDeProyecto(b, [a, b, CASA])).toBe("OBRA-GENERADA (4) (sin versión guardada)");
  });

  test("sin la marca de la versión queda solo el nombre (el botón de la barra)", () => {
    expect(rotuloDeProyecto(TORRE, [TORRE], false)).toBe("Torre B");
  });
});
