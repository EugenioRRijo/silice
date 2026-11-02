import { describe, expect, test } from "vitest";
import { esFilaAfectada, gravesDe, necesitaLaAprobacion, pasoDelPresupuesto } from "./pasoDelPresupuesto";
import type { EntradaDelPaso } from "./pasoDelPresupuesto";

// Tarea 5 del plan F4: la franja del Presupuesto. Una prueba por regla, en el orden del plan (la primera que se cumple
// gana), con el texto y la acción escritos a mano desde el plan. Versiones ficticias 001 y 002.

const BASE: EntradaDelPaso = {
  version: "001",
  vigente: "001",
  cambios: 0,
  graves: 0,
  aprobacion: "guardada",
  puedeEditar: true,
  puedeEnviar: true,
};
const con = (extra: Partial<EntradaDelPaso>): EntradaDelPaso => ({ ...BASE, ...extra });

describe("pasoDelPresupuesto: las reglas en su orden", () => {
  test("1. borrador en blanco sin cambios: te falta agregar la primera partida", () => {
    expect(pasoDelPresupuesto(con({ version: null, vigente: null, aprobacion: null }))).toEqual({
      tipo: "falta",
      texto: "Agregue la primera partida",
      accion: "agregar_partida",
    });
  });

  test("2. con cambios: siguiente paso, guardarlos", () => {
    expect(pasoDelPresupuesto(con({ cambios: 2 }))).toEqual({
      tipo: "siguiente",
      texto: "Hay 2 cambios sin guardar",
      accion: "guardar",
    });
  });

  test("2. un solo cambio se dice en singular", () => {
    expect(pasoDelPresupuesto(con({ cambios: 1 }))?.texto).toBe("Hay 1 cambio sin guardar");
  });

  test("2. el borrador en blanco con cambios también se guarda (la primera versión)", () => {
    expect(pasoDelPresupuesto(con({ version: null, vigente: null, aprobacion: null, cambios: 3 }))).toEqual({
      tipo: "siguiente",
      texto: "Hay 3 cambios sin guardar",
      accion: "guardar",
    });
  });

  test("2. los cambios ganan a los hallazgos graves y a la aprobación", () => {
    expect(pasoDelPresupuesto(con({ cambios: 2, graves: 4, aprobacion: "devuelta" }))?.accion).toBe("guardar");
  });

  test("3. con hallazgos graves: te falta revisarlos antes de enviar", () => {
    expect(pasoDelPresupuesto(con({ graves: 2 }))).toEqual({
      tipo: "falta",
      texto: "Hay 2 hallazgos graves: revíselos antes de enviar",
      accion: "ver_revision",
    });
  });

  test("3. un solo hallazgo grave se dice en singular", () => {
    expect(pasoDelPresupuesto(con({ graves: 1 }))?.texto).toBe("Hay 1 hallazgo grave: revíselo antes de enviar");
  });

  test("4. devuelta: te falta corregir, con una versión nueva", () => {
    expect(pasoDelPresupuesto(con({ aprobacion: "devuelta" }))).toEqual({
      tipo: "falta",
      texto: "La versión 001 fue devuelta: corrija lo observado",
      accion: "version_nueva",
    });
  });

  test("5. en aprobación: espera dictamen y no hay nada que pulsar", () => {
    expect(pasoDelPresupuesto(con({ aprobacion: "en_aprobacion" }))).toEqual({
      tipo: "siguiente",
      texto: "La versión 001 espera dictamen",
      accion: null,
    });
  });

  test.each(["aprobada", "aprobada_con_observaciones"])("6. %s: no hay franja", (aprobacion) => {
    expect(pasoDelPresupuesto(con({ aprobacion }))).toBeNull();
  });

  test("7. versión abierta distinta de la vigente: no hay franja (solo la vigente se envía)", () => {
    expect(pasoDelPresupuesto(con({ version: "001", vigente: "002" }))).toBeNull();
  });

  test.each([["guardada"], ["retirada"], [null]])("8. %s: siguiente paso, enviarla a aprobación", (aprobacion) => {
    expect(pasoDelPresupuesto(con({ aprobacion }))).toEqual({
      tipo: "siguiente",
      texto: "Envíe la versión 001 a aprobación",
      accion: "enviar_a_aprobacion",
    });
  });
});

// Ronda 2 del árbitro: cada caso de arriba parte de «guardada» y de la vigente abierta, así que no fija el orden de las
// reglas 3 a 7. Estos cruzan dos reglas a la vez; gana la de número menor.
describe("pasoDelPresupuesto: precedencia de las reglas 3 a 7", () => {
  const GRAVES_2 = { tipo: "falta", texto: "Hay 2 hallazgos graves: revíselos antes de enviar", accion: "ver_revision" };

  test.each(["devuelta", "en_aprobacion", "aprobada"])("3 gana a la aprobación %s", (aprobacion) => {
    expect(pasoDelPresupuesto(con({ graves: 2, aprobacion }))).toEqual(GRAVES_2);
  });

  test("3 gana a la versión abierta distinta de la vigente (7)", () => {
    expect(pasoDelPresupuesto(con({ graves: 2, version: "001", vigente: "002" }))).toEqual(GRAVES_2);
  });

  test("4 gana a la versión abierta distinta de la vigente (7)", () => {
    expect(pasoDelPresupuesto(con({ aprobacion: "devuelta", version: "001", vigente: "002" }))).toEqual({
      tipo: "falta",
      texto: "La versión 001 fue devuelta: corrija lo observado",
      accion: "version_nueva",
    });
  });

  test("5 gana a la versión abierta distinta de la vigente (7)", () => {
    expect(pasoDelPresupuesto(con({ aprobacion: "en_aprobacion", version: "001", vigente: "002" }))).toEqual({
      tipo: "siguiente",
      texto: "La versión 001 espera dictamen",
      accion: null,
    });
  });
});

describe("pasoDelPresupuesto: sin permiso el texto se queda y la acción se va (Foco 3)", () => {
  test("1 sin puedeEditar: sin agregar", () => {
    expect(pasoDelPresupuesto(con({ version: null, vigente: null, aprobacion: null, puedeEditar: false }))).toEqual({
      tipo: "falta",
      texto: "Agregue la primera partida",
      accion: null,
    });
  });

  test("2 sin puedeEditar: sin guardar", () => {
    expect(pasoDelPresupuesto(con({ cambios: 2, puedeEditar: false }))).toEqual({
      tipo: "siguiente",
      texto: "Hay 2 cambios sin guardar",
      accion: null,
    });
  });

  test("4 sin puedeEditar: sin versión nueva", () => {
    expect(pasoDelPresupuesto(con({ aprobacion: "devuelta", puedeEditar: false }))).toEqual({
      tipo: "falta",
      texto: "La versión 001 fue devuelta: corrija lo observado",
      accion: null,
    });
  });

  test("8 sin puedeEnviar: sin enviar", () => {
    expect(pasoDelPresupuesto(con({ puedeEnviar: false }))).toEqual({
      tipo: "siguiente",
      texto: "Envíe la versión 001 a aprobación",
      accion: null,
    });
  });

  test("3 sin puedeEditar: ir a Revisión solo lee, así que se queda", () => {
    expect(pasoDelPresupuesto(con({ graves: 2, puedeEditar: false, puedeEnviar: false }))?.accion).toBe("ver_revision");
  });

  test("8 con un borrador de solo lectura y permiso: enviar obra sobre la versión guardada y se queda (Eugenio, 2026-10-31)", () => {
    expect(pasoDelPresupuesto(con({ puedeEditar: false, puedeEnviar: true }))?.accion).toBe("enviar_a_aprobacion");
  });
});

describe("las piezas de la franja y de las filas", () => {
  test("gravesDe suma solo CRITICO y ERROR", () => {
    expect(
      gravesDe([
        { severidad: "CRITICO", total: 1 },
        { severidad: "ERROR", total: 2 },
        { severidad: "ADVERTENCIA", total: 5 },
        { severidad: "INFO", total: 3 },
      ]),
    ).toBe(3);
    expect(gravesDe([])).toBe(0);
  });

  test.each([
    ["CRITICO", true],
    ["ERROR", true],
    ["ADVERTENCIA", true],
    ["error", true],
    ["INFO", false],
    [null, false],
  ])("esFilaAfectada(%s) = %s", (severidad, afectada) => {
    expect(esFilaAfectada(severidad)).toBe(afectada);
  });

  test("necesitaLaAprobacion: solo cuando las tres primeras reglas no deciden", () => {
    expect(necesitaLaAprobacion({ version: "001", cambios: 0, graves: 0 })).toBe(true);
    expect(necesitaLaAprobacion({ version: null, cambios: 0, graves: 0 })).toBe(false);
    expect(necesitaLaAprobacion({ version: "001", cambios: 1, graves: 0 })).toBe(false);
    expect(necesitaLaAprobacion({ version: "001", cambios: 0, graves: 1 })).toBe(false);
  });
});
