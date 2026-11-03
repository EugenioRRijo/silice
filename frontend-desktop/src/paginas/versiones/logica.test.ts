import { describe, expect, test } from "vitest";
import type { EstadoDeAprobacion } from "../../comun/aprobacion";
import type { VersionFila, VersionesRespuesta } from "../hoja/logica";
import { filasDeVersiones, pasoDeVersiones } from "./logica";
import type { FilaDeVersion } from "./logica";

// Tarea 6 del plan F4: la lógica pura de la sección Versiones. Datos ficticios (obra 3, VIV-001 y VIV-002); los resultados
// esperados están escritos a mano desde el plan.

const fila = (codigo: string, vigente: boolean, extra: Partial<VersionFila> = {}): VersionFila => ({
  codigo,
  fecha: "2026-10-20",
  motivo: "",
  origen: "",
  vigente,
  descartada: false,
  cambios: 0,
  ...extra,
});

const VERSIONES: VersionesRespuesta = {
  proyecto: "3",
  moneda: "Bs",
  por_omision: "VIV-002",
  versiones: [fila("VIV-002", true, { origen: "VIV-001", cambios: 4 }), fila("VIV-001", false)],
};

const estado = (e: string): EstadoDeAprobacion => ({ estado: e, por: null, el: null, notas: "", armo: false });

describe("filasDeVersiones", () => {
  test("combina el estado de aprobación de cada versión y marca la abierta", () => {
    const estados = { "VIV-001": estado("devuelta"), "VIV-002": estado("guardada") };
    expect(filasDeVersiones(VERSIONES, estados, "VIV-001")).toEqual([
      { ...fila("VIV-002", true, { origen: "VIV-001", cambios: 4 }), estado: "guardada", abierta: false, seAbre: true },
      { ...fila("VIV-001", false), estado: "devuelta", abierta: true, seAbre: true },
    ]);
  });

  test("sin estados (no se pudieron leer) deja `estado: null` en todas", () => {
    expect(filasDeVersiones(VERSIONES, null, "VIV-002").map((f) => [f.codigo, f.estado, f.abierta])).toEqual([
      ["VIV-002", null, true],
      ["VIV-001", null, false],
    ]);
  });

  test("una versión que la lectura no trae queda sin estado; sin versión abierta, ninguna lo está", () => {
    const filas = filasDeVersiones(VERSIONES, { "VIV-002": estado("en_aprobacion") }, null);
    expect(filas.map((f) => [f.codigo, f.estado, f.abierta])).toEqual([
      ["VIV-002", "en_aprobacion", false],
      ["VIV-001", null, false],
    ]);
  });

  // Ronda 2 de la Tarea 6: el historial solo crece (RF-54), así que la descartada sigue en la tabla, marcada, y se puede
  // restaurar; lo que no se ofrece es abrirla (la regla del proveedor: abrir una descartada abriría otra sin decirlo).
  test("la descartada sigue en el historial, marcada y sin «Abrir»; las demás se abren", () => {
    const conDescartada = { ...VERSIONES, versiones: [...VERSIONES.versiones, fila("VIV-000", false, { descartada: true })] };
    expect(filasDeVersiones(conDescartada, { "VIV-000": estado("devuelta") }, null)).toEqual([
      { ...fila("VIV-002", true, { origen: "VIV-001", cambios: 4 }), estado: null, abierta: false, seAbre: true },
      { ...fila("VIV-001", false), estado: null, abierta: false, seAbre: true },
      { ...fila("VIV-000", false, { descartada: true }), estado: "devuelta", abierta: false, seAbre: false },
    ]);
  });

  test("si todas están descartadas, todas van marcadas y todas se abren (el proveedor abre cualquiera)", () => {
    const viv001 = fila("VIV-001", false, { descartada: true });
    const viv000 = fila("VIV-000", false, { descartada: true });
    expect(filasDeVersiones({ ...VERSIONES, versiones: [viv001, viv000] }, null, "VIV-001")).toEqual([
      { ...viv001, estado: null, abierta: true, seAbre: true },
      { ...viv000, estado: null, abierta: false, seAbre: true },
    ]);
  });
});

describe("pasoDeVersiones", () => {
  const filas = (vigente: string | null): FilaDeVersion[] => [
    { ...fila("VIV-002", true), estado: vigente, abierta: true },
    { ...fila("VIV-001", false), estado: "devuelta", abierta: false },
  ];

  test("con cambios sin guardar, el paso es guardarlos (en plural y en singular)", () => {
    expect(pasoDeVersiones({ cambios: 3, puedeGuardar: true, filas: filas("guardada") })).toEqual({
      texto: "Hay 3 cambios sin guardar",
      accion: "guardar",
    });
    expect(pasoDeVersiones({ cambios: 1, puedeGuardar: true, filas: filas("guardada") })).toEqual({
      texto: "Hay 1 cambio sin guardar",
      accion: "guardar",
    });
  });

  test("los cambios ganan a la vigente en aprobación; sin permiso para guardar el texto se queda sin botón", () => {
    expect(pasoDeVersiones({ cambios: 2, puedeGuardar: false, filas: filas("en_aprobacion") })).toEqual({
      texto: "Hay 2 cambios sin guardar",
      accion: null,
    });
  });

  test("sin cambios y con la vigente en aprobación, dice que espera dictamen, sin botón", () => {
    expect(pasoDeVersiones({ cambios: 0, puedeGuardar: true, filas: filas("en_aprobacion") })).toEqual({
      texto: "La versión VIV-002 espera dictamen",
      accion: null,
    });
  });

  test("sin cambios y con la vigente fuera de aprobación (o sin estado), no hay paso", () => {
    expect(pasoDeVersiones({ cambios: 0, puedeGuardar: true, filas: filas("guardada") })).toBeNull();
    expect(pasoDeVersiones({ cambios: 0, puedeGuardar: true, filas: filas(null) })).toBeNull();
    expect(pasoDeVersiones({ cambios: 0, puedeGuardar: true, filas: [] })).toBeNull();
  });

  test("las cifras van en es-VE: 1234 cambios se dicen con punto de miles", () => {
    expect(pasoDeVersiones({ cambios: 1234, puedeGuardar: true, filas: [] })?.texto).toBe("Hay 1.234 cambios sin guardar");
  });
});
