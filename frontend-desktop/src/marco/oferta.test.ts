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

describe("ofertaDe con módulos apagados (plan vial, Tarea 19)", () => {
  it("con vial apagado no hay sección Tramos ni la pantalla entre las sueltas (buscador)", () => {
    const oferta = ofertaDe(TODAS, false, ["vial"]);
    expect(oferta.soloVial).toEqual([]);
    expect(oferta.sueltas.map((p) => p.id)).not.toContain("tramos");
    expect(seccionesDeLaObra(oferta, true).map((s) => s.id)).not.toContain("tramos");
  });

  it("con producción apagada desaparece la entrada «Producción» de la empresa y sus pantallas del buscador", () => {
    const oferta = ofertaDe(TODAS, false, ["produccion"]);
    expect(oferta.entradas.map((e) => e.id)).not.toContain("produccion");
    const ids = oferta.sueltas.map((p) => p.id);
    for (const id of ["produccion", "costos", "receta_planta", "producir_mezcla", "costo_tonelada"]) {
      expect(ids, id).not.toContain(id);
    }
  });

  it("con riesgo apagado la pantalla de riesgo no se ofrece", () => {
    expect(ofertaDe(TODAS, false, ["riesgo"]).sueltas.map((p) => p.id)).not.toContain("riesgo");
  });

  it("sin nada apagado la oferta es la de siempre", () => {
    expect(ofertaDe(TODAS, false, [])).toEqual(ofertaDe(TODAS, false));
    expect(ofertaDe(TODAS, false).entradas.map((e) => e.id)).toContain("produccion");
  });
});

describe("ofertaDe con edificación apagada (plan vial, Tarea 19, T19-5)", () => {
  it("no oculta pantallas del registro: «Espacio y metrajes» es una pestaña de la hoja, no una pantalla", () => {
    expect(ofertaDe(TODAS, false, ["edificacion"])).toEqual(ofertaDe(TODAS, false));
  });
});
