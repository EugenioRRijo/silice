import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { buscadorDeConsulta, gruposDeConsulta, rutaDeConsulta } from "./consulta";
import type { SugerenciasHalladas } from "./consulta";

// Plan vial, Tarea 20: el adaptador de GET /v1/consulta/{tabla} para CampoConBusqueda. Datos ficticios.

const RESPUESTA: SugerenciasHalladas = {
  tabla: "insumos",
  resultados: [
    { valor: "MAT-1", etiqueta: "Cemento gris ficticio (MAT-1, saco)", fuente: "Catálogo de la carpeta de trabajo: material" },
    { valor: "MAT-2", etiqueta: "Arena lavada ficticia (MAT-2, m3)", fuente: "Catálogo de la carpeta de trabajo: material" },
  ],
  hay_mas: true,
};

describe("rutaDeConsulta", () => {
  test("codifica la tabla y el texto", () => {
    expect(rutaDeConsulta("insumos", "ce ment", 8)).toBe("/v1/consulta/insumos?q=ce+ment&limite=8");
  });
});

describe("gruposDeConsulta", () => {
  test("un grupo con el rótulo de la tabla, una opción por sugerencia y su fuente a la vista", () => {
    const [grupo, ...resto] = gruposDeConsulta(RESPUESTA);
    expect(resto).toEqual([]);
    expect(grupo.rotulo).toBe("Insumos del catálogo");
    expect(grupo.hayMas).toBe(true);
    expect(grupo.opciones.map((o) => o.clave)).toEqual(["insumos:MAT-1", "insumos:MAT-2"]);
    expect(grupo.opciones[0].principal).toBe("Cemento gris ficticio (MAT-1, saco)");
    expect(grupo.opciones[0].secundaria).toEqual(["MAT-1", "Catálogo de la carpeta de trabajo: material"]);
    expect(grupo.opciones[0].valor.valor).toBe("MAT-1");
  });
});

describe("buscadorDeConsulta pide la ruta con la señal de aborto", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("GET a /v1/consulta/insumos con la señal y entrega los grupos", async () => {
    fetchFalso.mockImplementation(async () => new Response(JSON.stringify(RESPUESTA), { status: 200 }));
    const controlador = new AbortController();
    const grupos = await buscadorDeConsulta("insumos")("cemento", controlador.signal, 8);
    expect(fetchFalso.mock.calls[0][0]).toBe("/v1/consulta/insumos?q=cemento&limite=8");
    expect(fetchFalso.mock.calls[0][1]?.signal).toBe(controlador.signal);
    expect(grupos[0].opciones).toHaveLength(2);
  });
});
