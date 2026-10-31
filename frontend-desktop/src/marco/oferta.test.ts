import { describe, expect, it } from "vitest";
import { PAGINAS } from "../shell/rutas";
import { ofertaDe, seccionesDeLaObra } from "./oferta";

const TODAS = PAGINAS.flatMap((p) => (p.accion === null ? [] : [p.accion]));

describe("ofertaDe: «Tramos» (plan vial, Tarea 8)", () => {
  it("la sección Tramos no va entre las de toda obra, va aparte para las viales", () => {
    const oferta = ofertaDe(TODAS, false);
    expect(oferta.secciones.map((s) => s.id)).not.toContain("tramos");
    expect(oferta.soloVial.map((s) => s.id)).toEqual(["tramos"]);
  });

  it("la pantalla Tramos de la vía queda entre las sueltas: se alcanza por el buscador", () => {
    expect(ofertaDe(TODAS, false).sueltas.map((p) => p.id)).toContain("tramos");
  });

  it("quien no edita la hoja no la ve de ningún modo", () => {
    const oferta = ofertaDe(["leer_proyecto", "aprobar_version"], false);
    expect(oferta.soloVial).toEqual([]);
    expect(oferta.sueltas.map((p) => p.id)).not.toContain("tramos");
  });

  it("seccionesDeLaObra: sin ser vial, las de siempre; siéndolo, Tramos entre Presupuesto y Aprobaciones", () => {
    const oferta = ofertaDe(TODAS, false);
    expect(seccionesDeLaObra(oferta, false).map((s) => s.id)).toEqual(["resumen", "presupuesto", "aprobaciones", "mercado", "control"]);
    expect(seccionesDeLaObra(oferta, true).map((s) => s.id)).toEqual(["resumen", "presupuesto", "tramos", "aprobaciones", "mercado", "control"]);
  });
});
