import { describe, expect, test } from "vitest";
import { ACCIONES } from "../../shell/obras/datosDePrueba";
import { PASOS_DE_EMPIEZA_AQUI, PRIMERA_VEZ, pasosDeEmpiezaAqui } from "./empiezaAqui";

// F7, tarea A4: «Empieza aquí» se deriva de los datos (no guarda nada en el navegador, RT-9). Las acciones de cada papel son
// las de la prueba del marco (ana arma, rita revisa, admin administra), que copian `seguridad/permisos.py`. Oráculos a mano.

const ana = [...ACCIONES.ana];
const rita = [...ACCIONES.rita];
const admin = [...ACCIONES.admin];

describe("pasosDeEmpiezaAqui", () => {
  test("quien administra, con su cuenta como única activa: crear las cuentas y poner la empresa", () => {
    expect(pasosDeEmpiezaAqui({ acciones: admin, obras: null, cuentasActivas: 1 })).toEqual(["cuentas", "empresa"]);
  });

  test("quien administra, cuando ya hay otra cuenta activa, o sin saber cuántas hay: nada", () => {
    expect(pasosDeEmpiezaAqui({ acciones: admin, obras: null, cuentasActivas: 2 })).toEqual([]);
    expect(pasosDeEmpiezaAqui({ acciones: admin, obras: null, cuentasActivas: null })).toEqual([]);
  });

  test("quien administra con su cuenta como única activa deja de ver los pasos en cuanto la instalación ya tiene obras", () => {
    expect(pasosDeEmpiezaAqui({ acciones: admin, obras: 2, cuentasActivas: 1 })).toEqual([]);
    expect(pasosDeEmpiezaAqui({ acciones: admin, obras: 0, cuentasActivas: 1 })).toEqual(["cuentas", "empresa"]);
    const ambos = [...new Set([...admin, ...ana])];
    expect(pasosDeEmpiezaAqui({ acciones: ambos, obras: 1, cuentasActivas: 1 })).toEqual([]);
  });

  test("quien arma, sin ninguna obra: crear la obra, armar el presupuesto y enviarlo a aprobación", () => {
    expect(pasosDeEmpiezaAqui({ acciones: ana, obras: 0, cuentasActivas: null })).toEqual(["obra", "presupuesto", "aprobacion"]);
  });

  test("quien arma, con una obra o sin saber cuántas hay: nada", () => {
    expect(pasosDeEmpiezaAqui({ acciones: ana, obras: 1, cuentasActivas: null })).toEqual([]);
    expect(pasosDeEmpiezaAqui({ acciones: ana, obras: null, cuentasActivas: null })).toEqual([]);
  });

  test("quien solo revisa, sin obras: auditar un libro y saber cómo se da el dictamen", () => {
    expect(pasosDeEmpiezaAqui({ acciones: rita, obras: 0, cuentasActivas: null })).toEqual(["auditar", "dictamen"]);
    expect(pasosDeEmpiezaAqui({ acciones: rita, obras: 3, cuentasActivas: null })).toEqual([]);
  });

  test("una cuenta que administra y también arma junta los dos grupos, sin repetir, en el orden de la tabla", () => {
    const ambos = [...new Set([...admin, ...ana])];
    expect(pasosDeEmpiezaAqui({ acciones: ambos, obras: 0, cuentasActivas: 1 })).toEqual(["cuentas", "empresa", "obra", "presupuesto", "aprobacion"]);
  });

  test("una cuenta que arma y revisa a la vez ve los pasos de quien arma, no los de quien solo revisa", () => {
    const ambos = [...new Set([...ana, ...rita])];
    expect(pasosDeEmpiezaAqui({ acciones: ambos, obras: 0, cuentasActivas: null })).toEqual(["obra", "presupuesto", "aprobacion"]);
  });
});

describe("los pasos", () => {
  test("el paso de las cuentas no afirma que quien administra nunca arma: la casilla de la bienvenida le da ese papel", () => {
    const { texto } = PASOS_DE_EMPIEZA_AQUI.cuentas;
    expect(texto).not.toContain("Quien administra no arma presupuestos");
    expect(texto).toContain("«Usaré esta cuenta también para armar presupuestos»");
  });

  test("cada paso dice para qué sirve y, si enlaza, lleva a la Cuenta, a la Ayuda o a Auditoría", () => {
    for (const [id, paso] of Object.entries(PASOS_DE_EMPIEZA_AQUI)) {
      expect(paso.titulo.length, id).toBeGreaterThan(0);
      expect(paso.texto, id).toMatch(/\.$/);
      if (paso.enlace !== undefined) expect(paso.enlace.ruta, id).toMatch(/^\/(cuenta\/(cuentas|empresa)|cuenta\/ayuda\?tema=[a-z0-9-]+|auditoria\/subir)$/);
    }
  });
});

describe("textos de «Empieza aquí» tras la ventana de escritorio (F5)", () => {
  test("el código de instalación se busca en la consola de Sílice, no en «la ventana del servidor»", () => {
    const todo = JSON.stringify({ PASOS_DE_EMPIEZA_AQUI, PRIMERA_VEZ });
    expect(todo).toContain("en la consola de Sílice");
    expect(todo).not.toContain("ventana del servidor");
  });
});
