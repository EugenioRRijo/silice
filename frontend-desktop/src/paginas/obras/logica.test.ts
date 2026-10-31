import { describe, expect, test } from "vitest";
import type { ObraFilaRespuesta } from "../../api/tipos";
import { etiquetaAvance, pasoDeLaObra } from "./logica";

// Lógica pura del Resumen de la obra.

describe("etiquetaAvance", () => {
  test("real de plan, en es-VE", () => {
    expect(etiquetaAvance("30.0", "37.5")).toBe("30,0 % de 37,5 %");
    expect(etiquetaAvance("100.0", "0.0")).toBe("100,0 % de 0,0 %");
  });

  test("sin alguno de los dos: «Sin avance»", () => {
    expect(etiquetaAvance(null, null)).toBe("Sin avance");
    expect(etiquetaAvance("30.0", null)).toBe("Sin avance");
    expect(etiquetaAvance(null, "37.5")).toBe("Sin avance");
  });
});

// Tarea 2 del plan F4: qué dice la franja del Resumen. Obra ficticia; los textos son los que daría el servidor.
const OBRA: ObraFilaRespuesta = {
  codigo: "3",
  nombre: "Galpón Norte",
  cliente: "",
  etapa: "en_elaboracion",
  etapa_texto: "En elaboración",
  version: "001",
  total: "100.00",
  moneda: "Bs",
  avance_real: null,
  avance_plan: null,
  que_pasa: null,
  siguiente: null,
};
const IR_A_LA_HOJA = { texto: "Abrir la Hoja", pagina: "hoja" };

describe("pasoDeLaObra", () => {
  test("con «qué pasa» y siguiente paso, lo que falta, con la acción", () => {
    expect(pasoDeLaObra({ ...OBRA, que_pasa: "Faltan 2 precios", siguiente: IR_A_LA_HOJA })).toEqual({
      tipo: "falta",
      texto: "Faltan 2 precios",
      accion: IR_A_LA_HOJA,
    });
  });

  test("con «qué pasa» y sin siguiente paso, lo que falta, sin acción", () => {
    expect(pasoDeLaObra({ ...OBRA, que_pasa: "Faltan 2 precios" })).toEqual({ tipo: "falta", texto: "Faltan 2 precios", accion: null });
  });

  test("solo con siguiente paso, el siguiente paso con el texto de la acción", () => {
    expect(pasoDeLaObra({ ...OBRA, siguiente: IR_A_LA_HOJA })).toEqual({ tipo: "siguiente", texto: "Abrir la Hoja", accion: IR_A_LA_HOJA });
  });

  test("sin ninguno de los dos, no hay franja", () => {
    expect(pasoDeLaObra(OBRA)).toBeNull();
  });
});
