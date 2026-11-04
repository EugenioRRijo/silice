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
// Pasada de navegador del cierre de F4 (H9): la sección se llama «Presupuesto». Desde el pulido F5 (Tarea 4) el servidor
// (`aplicacion/mesa.py`) ya lo dice así y el front lo pinta tal cual (se fue `textoDeLaAccion`, que lo corregía).
const AL_PRESUPUESTO = { texto: "Abrir el presupuesto", pagina: "hoja" };
const PRIMERA_PARTIDA = { texto: "Agregue la primera partida", pagina: "hoja" };

describe("pasoDeLaObra", () => {
  test("con «qué pasa» y siguiente paso, lo que falta, con la acción", () => {
    expect(pasoDeLaObra({ ...OBRA, que_pasa: "Faltan 2 precios", siguiente: AL_PRESUPUESTO })).toEqual({
      tipo: "falta",
      texto: "Faltan 2 precios",
      accion: AL_PRESUPUESTO,
    });
  });

  test("con «qué pasa» y sin siguiente paso, lo que falta, sin acción", () => {
    expect(pasoDeLaObra({ ...OBRA, que_pasa: "Faltan 2 precios" })).toEqual({ tipo: "falta", texto: "Faltan 2 precios", accion: null });
  });

  test("solo con siguiente paso, el siguiente paso con el texto de la acción", () => {
    expect(pasoDeLaObra({ ...OBRA, siguiente: AL_PRESUPUESTO })).toEqual({ tipo: "siguiente", texto: "Abrir el presupuesto", accion: AL_PRESUPUESTO });
  });

  test("una obra en blanco: el paso y su botón dicen «Agregue la primera partida», como lo manda el servidor", () => {
    expect(pasoDeLaObra({ ...OBRA, siguiente: PRIMERA_PARTIDA })).toEqual({
      tipo: "siguiente",
      texto: "Agregue la primera partida",
      accion: PRIMERA_PARTIDA,
    });
  });

  test("sin ninguno de los dos, no hay franja", () => {
    expect(pasoDeLaObra(OBRA)).toBeNull();
  });
});
