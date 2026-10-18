import { describe, expect, test } from "vitest";
import {
  descripcionLista,
  encabezadoDeLista,
  filasEquipos,
  filasManoObra,
  filasMateriales,
  origenDePropuesta,
  resultadosDe,
  rendimientoEnTexto,
  tituloDePropuesta,
} from "./logica";
import type { Composicion, Propuesta } from "./logica";

const COMPOSICION: Composicion = {
  unidad: "m3",
  rendimiento: "8.00",
  materiales: [{ descripcion: "Cemento", unidad: "saco", cantidad: "7.50", precio: "15.00" }],
  equipos: [{ descripcion: "Pala", cantidad: "2.00", precio: "10.00", depreciacion: "0.03" }],
  mano_obra: [{ descripcion: "Ayudante", cantidad: "4.00", sueldo: "3.00" }],
};
const PROPUESTA: Propuesta = {
  codigo: "LB-04-CON",
  descripcion: "Vaciado de concreto",
  puntaje: "0.9137",
  puntaje_corto: "0.91",
  composicion: COMPOSICION,
  aviso: null,
};

describe("logica de Partidas similares", () => {
  test("el titulo y el origen son los de la pagina de Streamlit", () => {
    expect(tituloDePropuesta(PROPUESTA)).toBe("0.91 - LB-04-CON - Vaciado de concreto");
    expect(origenDePropuesta(PROPUESTA)).toBe("Partida de origen: LB-04-CON | puntaje de similitud: 0.9137");
    expect(encabezadoDeLista(2)).toBe("2 propuestas, de mayor a menor similitud");
    expect(encabezadoDeLista(1)).toBe("1 propuesta");
    expect(rendimientoEnTexto(COMPOSICION)).toEqual({ unidad: "m3", rendimiento: "8.00 m3/día" });
    expect(resultadosDe("  zanja ")).toBe("Resultados de: “zanja”");
  });

  test("las filas conservan el texto de la API y llevan id por posicion", () => {
    expect(filasMateriales(COMPOSICION)).toEqual([
      { id: "0", descripcion: "Cemento", unidad: "saco", cantidad: "7.50", precio: "15.00" },
    ]);
    expect(filasEquipos(COMPOSICION)[0]).toMatchObject({ id: "0", depreciacion: "0.03" });
    expect(filasManoObra(COMPOSICION)[0]).toMatchObject({ id: "0", sueldo: "3.00" });
  });

  test("una descripcion en blanco no se envia", () => {
    expect(descripcionLista("")).toBe(false);
    expect(descripcionLista("   ")).toBe(false);
    expect(descripcionLista(" zanja ")).toBe(true);
  });
});
