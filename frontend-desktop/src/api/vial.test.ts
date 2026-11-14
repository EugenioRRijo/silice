import { describe, expect, test } from "vitest";
import type { CapaDeTramo, DemarcacionDeTramo, TramoGuardado } from "./vial";

// Prueba de contrato (2026-11-13, línea vial: el servidor ya da `suministro` en cada capa y `vial.ts` no lo declaraba). El
// oráculo es el contrato publicado de la API (`docs/api.json`, que la CI regenera y compara con `api/rutas/vial.py`), no
// el código del navegador. Cada objeto de abajo es `Required<…>` del tipo del navegador: si el tipo no tiene un campo de
// la API, el objeto no compila (`tsc -b`); si lo tiene y la API no, la comparación de claves falla.
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const contrato = JSON.parse(nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/../docs/api.json`, "utf-8")) as {
  components: { schemas: Record<string, { properties: Record<string, unknown> }> };
};
const claves = (esquema: string) => Object.keys(contrato.components.schemas[esquema]?.properties ?? {}).sort();

// Valores ficticios: solo importan las claves.
const CAPA: Required<CapaDeTramo> = {
  tipo: "riego_adherencia",
  espesor_m: null,
  densidad_t_m3: null,
  dosis_l_m2: null,
  asfalto_pct: null,
  esponjamiento: null,
  limpieza: false,
  medicion: null,
  suministro: true,
};
const DEMARCACION: Required<DemarcacionDeTramo> = { tipo: "captafaros", lineas: 0, area_m2: null, captafaros: 40 };
const TRAMO: Required<TramoGuardado> = {
  id: "T-1",
  progresiva_ini_km: "0",
  progresiva_fin_km: "1",
  ancho_m: "7.3",
  distancia_planta_km: null,
  transporte: null,
  capas: [CAPA],
  demarcacion: [DEMARCACION],
};

describe("contrato de los tramos viales", () => {
  test("una capa declara los mismos campos que la API, `suministro` incluido", () => {
    expect(Object.keys(CAPA).sort()).toEqual(claves("CapaRespuesta"));
  });

  test("la demarcación y el tramo declaran los mismos campos que la API", () => {
    expect(Object.keys(DEMARCACION).sort()).toEqual(claves("DemarcacionRespuesta"));
    expect(Object.keys(TRAMO).sort()).toEqual(claves("TramoRespuesta"));
  });
});
