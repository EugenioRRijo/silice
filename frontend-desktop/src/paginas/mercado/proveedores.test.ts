import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { RUTA_DE_PROVEEDORES, buscadorDeProveedores, filtrarProveedores, gruposDeProveedores } from "./proveedores";
import type { ProveedorUsado } from "./proveedores";

// AC4 (pedido de Eugenio del 2026-10-21): el proveedor de una cotización se elige de los que ya se usaron en la carpeta
// (`GET /v1/consulta/proveedores`, el último usado primero) o se escribe uno nuevo. Datos ficticios.

const PROVEEDORES: ProveedorUsado[] = [
  { proveedor: "Ferretería Demo, C.A.", ultimo_uso: "2026-10-05" },
  { proveedor: "Bloquera Ficticia", ultimo_uso: "2026-09-12" },
  { proveedor: "Depósito El Ferretero", ultimo_uso: "2026-08-01" },
];

const nombres = (halladas: ProveedorUsado[]) => halladas.map((p) => p.proveedor);

describe("filtrarProveedores", () => {
  test("todas las palabras, en cualquier orden y sin distinguir mayúsculas ni tildes; el último usado primero", () => {
    expect(nombres(filtrarProveedores(PROVEEDORES, "FERRE"))).toEqual(["Ferretería Demo, C.A.", "Depósito El Ferretero"]);
    expect(nombres(filtrarProveedores(PROVEEDORES, "ferreteria demo"))).toEqual(["Ferretería Demo, C.A."]);
    expect(nombres(filtrarProveedores(PROVEEDORES, "deposito ferre"))).toEqual(["Depósito El Ferretero"]);
    expect(filtrarProveedores(PROVEEDORES, "cantera")).toEqual([]);
  });
});

describe("gruposDeProveedores", () => {
  test("un grupo con el proveedor arriba y la fecha de su última cotización abajo, en dd/mm/aaaa", () => {
    const [grupo] = gruposDeProveedores(PROVEEDORES.slice(0, 2), 8);
    expect(grupo.rotulo).toBe("Proveedores de cotizaciones anteriores");
    expect(grupo.opciones.map((o) => [o.principal, o.secundaria])).toEqual([
      ["Ferretería Demo, C.A.", ["Última cotización: 05/10/2026"]],
      ["Bloquera Ficticia", ["Última cotización: 12/09/2026"]],
    ]);
    expect(grupo.hayMas).toBe(false);
    expect(gruposDeProveedores(PROVEEDORES, 1)[0].hayMas).toBe(true);
    expect(gruposDeProveedores([], 8)).toEqual([]);
  });
});

describe("buscadorDeProveedores", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async () => new Response(JSON.stringify({ proveedores: PROVEEDORES }), { status: 200 }));
  });
  afterEach(() => vi.unstubAllGlobals());

  test("pide la lista una sola vez y filtra en el navegador", async () => {
    const buscar = buscadorDeProveedores();
    const senal = new AbortController().signal;
    await buscar("ferre", senal, 8);
    const [grupo] = await buscar("bloq", senal, 8);
    expect(grupo.opciones.map((o) => o.principal)).toEqual(["Bloquera Ficticia"]);
    expect(fetchFalso.mock.calls.map(([r]) => String(r))).toEqual([RUTA_DE_PROVEEDORES]);
  });
});
