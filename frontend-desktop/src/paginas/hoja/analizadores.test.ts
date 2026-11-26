import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { InformeAuditoriaRespuesta } from "../../api/tipos";
import { leerInforme, leerResumen, leerVistaPresupuesto } from "./analizadores";
import { informeAuditoria, vistaPresupuesto } from "./datosDePrueba";
import type { Resumen } from "./logica";

function resumenBase(extra: Partial<Resumen> = {}): Resumen {
  return {
    rev: 2,
    moneda: "USD",
    total: { texto: "2703.86", exacto: "2703.8602323440440333" },
    cambios: 1,
    pendientes_catalogo: 0,
    hallazgos: [{ severidad: "ERROR", total: 1 }],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
    ...extra,
  };
}

function respuestaJson(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("analizadores de la Hoja", () => {
  describe("leerVistaPresupuesto", () => {
    test("acepta los datos de prueba existentes y conserva sus campos", () => {
      const ejemplo = vistaPresupuesto();
      expect(leerVistaPresupuesto(ejemplo)).toEqual(ejemplo);
    });

    test("acepta una vista vacía y una fila con de_tramo booleano", () => {
      const vacia = vistaPresupuesto({ filas: [], vacio_mensaje: "Esta obra aún no tiene partidas." });
      expect(leerVistaPresupuesto(vacia)).toEqual(vacia);

      const base = vistaPresupuesto();
      const conTramo = {
        ...base,
        filas: [{ ...base.filas[0]!, de_tramo: true }],
      };
      expect(leerVistaPresupuesto(conTramo)).toEqual(conTramo);
    });

    test("rechaza una fila sin clave (ausente, nula o vacía)", () => {
      const base = vistaPresupuesto();
      const filaValida = base.filas[0]!;
      const sinClave = { ...filaValida } as Record<string, unknown>;
      delete sinClave.clave;

      expect(() => leerVistaPresupuesto({ ...base, filas: [sinClave] })).toThrow();
      expect(() => leerVistaPresupuesto({ ...base, filas: [{ ...filaValida, clave: null }] })).toThrow();
      expect(() => leerVistaPresupuesto({ ...base, filas: [{ ...filaValida, clave: "" }] })).toThrow();
      expect(() => leerVistaPresupuesto({ ...base, filas: [{ ...filaValida, clave: "   " }] })).toThrow();
    });

    test("rechaza valores que no coinciden con la forma de VistaPresupuesto", () => {
      const base = vistaPresupuesto();
      const fila = base.filas[0]!;
      expect(() => leerVistaPresupuesto(null)).toThrow();
      expect(() => leerVistaPresupuesto([])).toThrow();
      expect(() => leerVistaPresupuesto({ ...base, filas: "no-es-lista" })).toThrow();
      expect(() => leerVistaPresupuesto({ ...base, total: { texto: "10,00" } })).toThrow();
      expect(() => leerVistaPresupuesto({ ...base, vacio_mensaje: undefined })).toThrow();
      expect(() => leerVistaPresupuesto({ ...base, impuestos: { ...base.impuestos, iva: 16 } })).toThrow();
      expect(() => leerVistaPresupuesto({ ...base, filas: [{ ...fila, escrita: "si" }] })).toThrow();
      expect(() => leerVistaPresupuesto({ ...base, filas: [{ ...fila, pu: { texto: "1", exacto: 1 } }] })).toThrow();
      expect(() => leerVistaPresupuesto({ ...base, filas: [{ ...fila, estado: { severidad: 1, texto: "OK" } }] })).toThrow();
      expect(() => leerVistaPresupuesto({ ...base, filas: [{ ...fila, de_tramo: "si" }] })).toThrow();
    });
  });

  describe("leerInforme", () => {
    test("acepta los datos de prueba existentes y un informe sin hallazgos", () => {
      const ejemplo = informeAuditoria();
      expect(leerInforme(ejemplo)).toEqual(ejemplo);

      const limpio: InformeAuditoriaRespuesta = {
        codigo_presupuesto: "OB-001",
        cumple: true,
        veredicto: "CUMPLE",
        total_hallazgos: 0,
        por_severidad: [],
        reglas_evaluadas: [{ regla: "R1", nombre: "Completitud de APU", hallazgos: 0 }],
        hallazgos: [],
        sin_hallazgos: "Sílice revisó 18 reglas y no halló problemas.",
      };
      expect(leerInforme(limpio)).toEqual(limpio);
    });

    test("rechaza formas inválidas en el informe o sus hallazgos", () => {
      const base = informeAuditoria();
      const hallazgo = base.hallazgos[0]!;
      expect(() => leerInforme(null)).toThrow();
      expect(() => leerInforme({ ...base, cumple: "no" })).toThrow();
      expect(() => leerInforme({ ...base, total_hallazgos: Number.NaN })).toThrow();
      expect(() => leerInforme({ ...base, por_severidad: [{ severidad: "ERROR", total: "1" }] })).toThrow();
      expect(() => leerInforme({ ...base, reglas_evaluadas: [{ regla: "R1", nombre: "Regla" }] })).toThrow();
      expect(() => leerInforme({ ...base, hallazgos: [{ ...hallazgo, numero: "1" }] })).toThrow();
      expect(() => leerInforme({ ...base, hallazgos: [{ ...hallazgo, origen: [123] }] })).toThrow();
      expect(() => leerInforme({ ...base, sin_hallazgos: 0 })).toThrow();
    });
  });

  describe("leerResumen", () => {
    test("acepta un resumen sin opcionales y con espacio_vacio y desgloses", () => {
      const minimo = resumenBase();
      expect(leerResumen(minimo)).toEqual(minimo);

      const completo = resumenBase({ espacio_vacio: true, desgloses: 2 });
      expect(leerResumen(completo)).toEqual(completo);
    });

    test("rechaza un resumen con campos faltantes o de tipo incorrecto", () => {
      const base = resumenBase();
      expect(() => leerResumen(null)).toThrow();
      expect(() => leerResumen({ ...base, rev: "2" })).toThrow();
      expect(() => leerResumen({ ...base, rev: Number.POSITIVE_INFINITY })).toThrow();
      expect(() => leerResumen({ ...base, total: null })).toThrow();
      expect(() => leerResumen({ ...base, hay_plan: 1 })).toThrow();
      expect(() => leerResumen({ ...base, version_mas_nueva: 2 })).toThrow();
      expect(() => leerResumen({ ...base, hallazgos: [{ severidad: "ERROR" }] })).toThrow();
      expect(() => leerResumen({ ...base, espacio_vacio: "si" })).toThrow();
      expect(() => leerResumen({ ...base, desgloses: "1" })).toThrow();
      expect(() => leerResumen({ ...base, desgloses: Number.NaN })).toThrow();
    });
  });

  describe("integración con pedir(ruta, { leer })", () => {
    const fetchFalso = vi.fn<typeof fetch>();

    beforeEach(() => {
      vi.stubGlobal("fetch", fetchFalso);
      fetchFalso.mockReset();
    });
    afterEach(() => {
      vi.unstubAllGlobals();
    });

    test("entrega los datos validados cuando cumplen el contrato", async () => {
      const vista = vistaPresupuesto();
      const informe = informeAuditoria();
      const resumen = resumenBase({ espacio_vacio: false });

      fetchFalso
        .mockResolvedValueOnce(respuestaJson(vista))
        .mockResolvedValueOnce(respuestaJson(informe))
        .mockResolvedValueOnce(respuestaJson(resumen));

      await expect(pedir("/v1/hoja/borradores/b1/vistas/presupuesto", { leer: leerVistaPresupuesto })).resolves.toEqual(vista);
      await expect(pedir("/v1/hoja/borradores/b1/vistas/auditoria", { leer: leerInforme })).resolves.toEqual(informe);
      await expect(pedir("/v1/hoja/borradores/b1/resumen", { leer: leerResumen })).resolves.toEqual(resumen);
    });

    test("convierte una respuesta mal formada en ErrorDeApi con código respuesta_invalida", async () => {
      const vista = vistaPresupuesto();
      const filaSinClave = { ...vista.filas[0]!, clave: "" };
      fetchFalso.mockResolvedValueOnce(respuestaJson({ ...vista, filas: [filaSinClave] }));

      const error = await pedir("/v1/hoja/borradores/b1/vistas/presupuesto", { leer: leerVistaPresupuesto }).catch((e: unknown) => e);
      expect(error).toBeInstanceOf(ErrorDeApi);
      expect((error as ErrorDeApi).codigo).toBe("respuesta_invalida");
    });
  });
});
