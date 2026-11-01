import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { buscadorDeComponentes, buscadorDeConsulta, buscadorDeMateriales, gruposDeConsulta, rutaDeConsulta } from "./consulta";
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

describe("materiales de producción de la arenera", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const MATERIALES = [
    { codigo: "MZP-01", nombre: "Mezcla asfáltica ficticia", activo: true },
    { codigo: "AGR-12", nombre: "Agregado grueso ficticio", activo: true },
    { codigo: "AGR-99", nombre: "Agregado retirado ficticio", activo: false },
  ];
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      if (ruta === "/v1/produccion/materiales") return new Response(JSON.stringify(MATERIALES), { status: 200 });
      return new Response(JSON.stringify(RESPUESTA), { status: 200 });
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("busca por código o por palabras en los materiales activos, sin distinguir tildes ni mayúsculas", async () => {
    const control = new AbortController();
    const [porNombre] = await buscadorDeMateriales()("MEZCLA asfal", control.signal, 8);
    expect(porNombre!.rotulo).toBe("Materiales de la arenera");
    expect(porNombre!.opciones.map((o) => o.valor.valor)).toEqual(["MZP-01"]);
    const [porCodigo] = await buscadorDeMateriales()("agr", control.signal, 8);
    expect(porCodigo!.opciones.map((o) => o.valor.valor)).toEqual(["AGR-12"]); // el inactivo no se ofrece
  });

  test("sin coincidencias no hay grupo", async () => {
    expect(await buscadorDeMateriales()("zzz", new AbortController().signal, 8)).toEqual([]);
  });

  test("los componentes ofrecen los materiales de la arenera y los insumos del catálogo", async () => {
    const grupos = await buscadorDeComponentes()("agr", new AbortController().signal, 8);
    expect(grupos.map((g) => g.rotulo)).toEqual(["Materiales de la arenera", "Insumos del catálogo"]);
  });
});
