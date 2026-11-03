import { describe, expect, it } from "vitest";
import { PAGINAS } from "../shell/rutas";
import { ofertaDe, seccionesDeLaObra } from "./oferta";

const TODAS = PAGINAS.flatMap((p) => (p.accion === null ? [] : [p.accion]));

describe("ofertaDe: «Tramos» (plan vial)", () => {
  it("la sección Tramos es de toda obra mientras el módulo vial esté encendido", () => {
    const oferta = ofertaDe(TODAS, false);
    expect(oferta.secciones.map((s) => s.id)).toContain("tramos");
    expect(seccionesDeLaObra(oferta).map((s) => s.id)).toEqual(["resumen", "presupuesto", "tramos", "archivos", "aprobaciones", "mercado", "control"]);
  });

  it("sin obra no hay pantalla suelta «Tramos de la vía»: el buscador la ofrece dentro de cada obra", () => {
    expect(ofertaDe(TODAS, false).sueltas.map((p) => p.id)).not.toContain("tramos");
  });

  it("quien no edita la hoja no la ve de ningún modo", () => {
    const oferta = ofertaDe(["leer_proyecto", "aprobar_version"], false);
    expect(oferta.secciones.map((s) => s.id)).not.toContain("tramos");
    expect(oferta.sueltas.map((p) => p.id)).not.toContain("tramos");
  });
});

describe("ofertaDe con módulos apagados (plan vial, Tarea 19)", () => {
  it("con vial apagado no hay sección Tramos ni la pantalla entre las sueltas (buscador)", () => {
    const oferta = ofertaDe(TODAS, false, ["vial"]);
    expect(oferta.secciones.map((s) => s.id)).not.toContain("tramos");
    expect(oferta.sueltas.map((p) => p.id)).not.toContain("tramos");
    expect(seccionesDeLaObra(oferta).map((s) => s.id)).not.toContain("tramos");
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
  // «Espacio y metrajes» es una pestaña de la hoja, no una pantalla: la oculta la Hoja. «Archivos y planos» se sigue
  // ofreciendo (F4, Tarea 12: edificación apaga los planos y el espacio, no los cómputos); dentro, solo se carga el cómputo.
  it("sigue ofreciendo «Archivos y planos» y deja todo como está", () => {
    const apagada = ofertaDe(TODAS, false, ["edificacion"]);
    const siempre = ofertaDe(TODAS, false);
    expect(apagada.secciones.map((s) => s.id)).toContain("archivos");
    expect(apagada.secciones.map((s) => s.id)).toEqual(siempre.secciones.map((s) => s.id));
    expect(apagada.entradas).toEqual(siempre.entradas);
    expect(apagada.sueltas).toEqual(siempre.sueltas);
  });
});
