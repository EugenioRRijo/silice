import { describe, expect, test } from "vitest";
import type { ObraFilaRespuesta } from "../../api/tipos";
import { bloquesPedidos, etiquetaAvance, gruposConItems, pasoDeLaObra } from "./logica";
import type { GrupoRespuesta } from "./logica";

// Plan de modulos, MOD-4b: la logica pura de la mesa de control. Acciones por rol copiadas a mano de
// seguridad/permisos.py (las mismas de `src/shell/obras/datosDePrueba.tsx`).
const ANA = [
  "editar_hoja",
  "convertir_y_reajustar",
  "control_de_obra",
  "decidir_recuperacion",
  "entregar_paquete",
  "operar_arenera",
  "leer_proyecto",
  "aprobar_version",
  "cambiar_caso",
];
const RITA = ["leer_proyecto", "revisar_paquete", "aprobar_version"];
const ADMIN = [
  "operar_arenera",
  "cambiar_caso",
  "administrar_cuentas",
  "administrar_empresa",
  "administrar_precios",
  "administrar_red_y_api",
  "cambiar_carpeta_de_datos",
];

describe("bloquesPedidos", () => {
  // T19: con `aprobar_version` se pide ademas lo de aprobar (la cifra «Por aprobar» y los envios de todas las carpetas).
  test("quien arma pide cifras, obras, pendientes y lo de aprobar (no los accesos)", () => {
    expect(bloquesPedidos(ANA)).toEqual(["cifras", "obras", "pendientes", "por_aprobar"]);
  });

  test("quien revisa pide cifras, obras y lo de aprobar; los pendientes de las obras exigen editar la hoja", () => {
    expect(bloquesPedidos(RITA)).toEqual(["cifras", "obras", "por_aprobar"]);
  });

  test("el administrador no lee obras: solo los accesos de su módulo", () => {
    expect(bloquesPedidos(ADMIN)).toEqual(["accesos"]);
  });

  test("solo editar la hoja: pendientes, sin cifras ni obras ni accesos", () => {
    expect(bloquesPedidos(["editar_hoja"])).toEqual(["pendientes"]);
  });

  test("solo aprobar versiones: lo de aprobar, sin accesos", () => {
    expect(bloquesPedidos(["aprobar_version"])).toEqual(["por_aprobar"]);
  });

  test("sin acciones: accesos", () => {
    expect(bloquesPedidos([])).toEqual(["accesos"]);
  });
});

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

describe("gruposConItems", () => {
  const item = { obra: "7", obra_nombre: "Casa Demo", texto: "1 precio sin referencia en CD-001", accion: { texto: "Ver el catálogo", pagina: "catalogo" } };
  test("quita los grupos vacíos y conserva el orden de la API", () => {
    const grupos: GrupoRespuesta[] = [
      { clave: "aprobar", titulo: "Aprobar", items: [] },
      { clave: "precios", titulo: "Precios", items: [item] },
      { clave: "calidad", titulo: "Calidad", items: [] },
    ];
    expect(gruposConItems(grupos).map((g) => g.clave)).toEqual(["precios"]);
  });

  test("todos vacíos: ninguno", () => {
    expect(gruposConItems([{ clave: "precios", titulo: "Precios", items: [] }])).toEqual([]);
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
