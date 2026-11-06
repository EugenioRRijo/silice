import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { RUTA_DE_UNIDADES, buscadorDeUnidades, filtrarUnidades, gruposDeUnidades } from "./unidades";
import type { UnidadUsada } from "./unidades";

// AC4 (pedido de Eugenio del 2026-10-21): la unidad se elige de las que ya usa el catálogo de la carpeta
// (`GET /v1/consulta/unidades`, agrupadas con la tabla de alias del núcleo y en orden de uso). La lista es corta: se pide
// una vez y se filtra en el navegador. Datos ficticios.

const UNIDADES: UnidadUsada[] = [
  { unidad: "m3", usos: 12, grafias: ["m3", "m³"] },
  { unidad: "m2", usos: 9, grafias: ["m2"] },
  { unidad: "saco", usos: 4, grafias: ["saco"] },
  { unidad: "m", usos: 3, grafias: ["m", "ml"] },
  { unidad: "dia", usos: 1, grafias: ["día"] },
];

const unidades = (halladas: UnidadUsada[]) => halladas.map((u) => u.unidad);

describe("filtrarUnidades", () => {
  test("la exacta primero, luego las que empiezan así y luego las que la contienen, cada grupo en el orden de uso", () => {
    expect(unidades(filtrarUnidades(UNIDADES, "m"))).toEqual(["m", "m3", "m2"]);
    expect(unidades(filtrarUnidades(UNIDADES, "a"))).toEqual(["saco", "dia"]);
  });

  test("busca también en las grafías, sin distinguir mayúsculas ni tildes", () => {
    expect(unidades(filtrarUnidades(UNIDADES, "ML"))).toEqual(["m"]);
    expect(unidades(filtrarUnidades(UNIDADES, "Día"))).toEqual(["dia"]);
    expect(unidades(filtrarUnidades(UNIDADES, "m³"))).toEqual(["m3"]);
  });

  test("sin coincidencias no hay nada", () => {
    expect(filtrarUnidades(UNIDADES, "kg")).toEqual([]);
  });
});

describe("gruposDeUnidades", () => {
  test("un grupo: la unidad arriba; abajo sus grafías y cuántas veces la usa el catálogo", () => {
    const [grupo] = gruposDeUnidades([UNIDADES[0], UNIDADES[4]], 8);
    expect(grupo.rotulo).toBe("Unidades del catálogo");
    expect(grupo.hayMas).toBe(false);
    expect(grupo.opciones.map((o) => [o.principal, o.secundaria])).toEqual([
      ["m3", ["m3, m³", "12 veces en el catálogo"]],
      ["dia", ["día", "1 vez en el catálogo"]],
    ]);
  });

  test("corta en el límite y avisa que hay más", () => {
    const [grupo] = gruposDeUnidades(UNIDADES, 2);
    expect(grupo.opciones).toHaveLength(2);
    expect(grupo.hayMas).toBe(true);
  });

  test("sin unidades no hay grupo", () => {
    expect(gruposDeUnidades([], 8)).toEqual([]);
  });
});

describe("buscadorDeUnidades", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async () => new Response(JSON.stringify({ unidades: UNIDADES }), { status: 200 }));
  });
  afterEach(() => vi.unstubAllGlobals());

  test("pide la lista una sola vez y filtra cada búsqueda en el navegador", async () => {
    const buscar = buscadorDeUnidades();
    const senal = new AbortController().signal;
    const [primera] = await buscar("m", senal, 8);
    const [segunda] = await buscar("sa", senal, 8);
    expect(primera.opciones.map((o) => o.principal)).toEqual(["m", "m3", "m2"]);
    expect(segunda.opciones.map((o) => o.principal)).toEqual(["saco"]);
    expect(fetchFalso.mock.calls.map(([r]) => String(r))).toEqual([RUTA_DE_UNIDADES]);
  });

  test("si la lista no llega, la búsqueda falla y la siguiente vuelve a pedirla", async () => {
    fetchFalso.mockImplementationOnce(async () => new Response(JSON.stringify({ detalle: "Sin base." }), { status: 503 }));
    const buscar = buscadorDeUnidades();
    const senal = new AbortController().signal;
    await expect(buscar("m", senal, 8)).rejects.toThrow();
    const [grupo] = await buscar("m", senal, 8);
    expect(grupo.opciones).toHaveLength(3);
    expect(fetchFalso).toHaveBeenCalledTimes(2);
  });
});
