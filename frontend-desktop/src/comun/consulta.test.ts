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

  // AC1b: Componer pide el detalle (descripción y unidad) y, si tiene fecha, el precio de la lista para armar a esa fecha.
  test("con detalle y fecha de armado los agrega; sin ellos la ruta es la de siempre", () => {
    expect(rutaDeConsulta("insumos", "cemento", 8, { detalle: true, paraArmarAl: "2026-08-15" })).toBe(
      "/v1/consulta/insumos?q=cemento&limite=8&detalle=true&para_armar_al=2026-08-15",
    );
    expect(rutaDeConsulta("salarios_cct", "alba", 8, { detalle: true })).toBe(
      "/v1/consulta/salarios_cct?q=alba&limite=8&detalle=true",
    );
    expect(rutaDeConsulta("insumos", "cemento", 8, { detalle: true, paraArmarAl: "" })).toBe(
      "/v1/consulta/insumos?q=cemento&limite=8&detalle=true",
    );
    expect(rutaDeConsulta("insumos", "cemento", 8, {})).toBe("/v1/consulta/insumos?q=cemento&limite=8");
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

// Dictamen de Claude (xhigh), hallazgo MAYOR: cada sugerencia de Componer dice el precio, la moneda y la fecha de la lista.
// Solo con `mostrarPrecio` (Componer, con fecha de armado); los demas adaptadores (Produccion) siguen con [valor, fuente].
describe("gruposDeConsulta con el precio a la vista", () => {
  const completa = (extra: Record<string, unknown>) => ({
    tabla: "insumos",
    hay_mas: false,
    resultados: [{ valor: "MAT-1", etiqueta: "Cemento gris ficticio (MAT-1, saco)", fuente: "Catálogo de la carpeta de trabajo: material", ...extra }],
  });
  const linea = (extra: Record<string, unknown>) => gruposDeConsulta(completa(extra), { mostrarPrecio: true })[0].opciones[0].secundaria;

  test("código, unidad, precio con coma y moneda, y la fecha de la lista como dd/mm/aaaa", () => {
    expect(linea({ unidad: "saco", precio: "18.00", moneda: "Bs", fecha_precio: "2026-07-01" })).toEqual([
      "MAT-1",
      "saco",
      "18,00 Bs",
      "lista del 01/07/2026",
    ]);
    expect(linea({ unidad: "saco", precio: "1234.5", moneda: "USD", fecha_precio: "2026-10-01" })).toEqual([
      "MAT-1",
      "saco",
      "1.234,5 USD",
      "lista del 01/10/2026",
    ]);
  });

  test("sin unidad no deja un hueco, y sin precio dice que no hay en la lista para armar", () => {
    expect(linea({})).toEqual(["MAT-1", "sin precio en la lista para armar"]);
    expect(linea({ unidad: "saco" })).toEqual(["MAT-1", "saco", "sin precio en la lista para armar"]);
  });

  test("en otra moneda que la de la carpeta el servidor no manda el precio y sí su aviso: es lo que se lee", () => {
    const aviso = "El catálogo lo tiene en USD; escriba el precio en Bs.";
    expect(linea({ unidad: "saco", moneda: "USD", fecha_precio: "2026-07-01", aviso_precio: aviso })).toEqual(["MAT-1", "saco", aviso]);
  });

  test("sin `mostrarPrecio` la línea es la de siempre (Producción no cambia)", () => {
    const con = { unidad: "saco", precio: "18.00", moneda: "Bs", fecha_precio: "2026-07-01" };
    expect(gruposDeConsulta(completa(con))[0].opciones[0].secundaria).toEqual([
      "MAT-1",
      "Catálogo de la carpeta de trabajo: material",
    ]);
    expect(gruposDeConsulta(completa(con), { mostrarPrecio: false })[0].opciones[0].secundaria).toEqual([
      "MAT-1",
      "Catálogo de la carpeta de trabajo: material",
    ]);
  });

  test("`mostrarPrecio` no cambia la ruta que se pide", () => {
    expect(rutaDeConsulta("insumos", "cemento", 8, { detalle: true, paraArmarAl: "2026-08-15", mostrarPrecio: true })).toBe(
      "/v1/consulta/insumos?q=cemento&limite=8&detalle=true&para_armar_al=2026-08-15",
    );
  });

  test("con `tipo` (material, equipo, mano de obra) la línea lo dice al final: en Equipos el catálogo los mezcla", () => {
    expect(linea({ unidad: "saco", precio: "18.00", moneda: "Bs", fecha_precio: "2026-07-01", tipo: "equipo" })).toEqual([
      "MAT-1",
      "saco",
      "18,00 Bs",
      "lista del 01/07/2026",
      "equipo",
    ]);
    expect(linea({ unidad: "saco", tipo: "material" })).toEqual(["MAT-1", "saco", "sin precio en la lista para armar", "material"]);
  });

  test("el buscador de consulta con `mostrarPrecio` entrega la línea con el precio", async () => {
    const fetchFalso = vi.fn<typeof fetch>(
      async () => new Response(JSON.stringify(completa({ unidad: "saco", precio: "18.00", moneda: "Bs", fecha_precio: "2026-07-01" })), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchFalso);
    try {
      const grupos = await buscadorDeConsulta("insumos", { detalle: true, paraArmarAl: "2026-08-15", mostrarPrecio: true })(
        "cemento",
        new AbortController().signal,
        8,
      );
      expect(grupos[0].opciones[0].secundaria).toEqual(["MAT-1", "saco", "18,00 Bs", "lista del 01/07/2026"]);
    } finally {
      vi.unstubAllGlobals();
    }
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

  test("con opciones las manda en la ruta y entrega la sugerencia con su precio tal cual llega", async () => {
    const conPrecio = {
      tabla: "insumos",
      hay_mas: false,
      resultados: [{ ...RESPUESTA.resultados[0], descripcion: "Cemento gris ficticio", unidad: "saco", precio: "18.00", moneda: "Bs", fecha_precio: "2026-07-01" }],
    };
    fetchFalso.mockImplementation(async () => new Response(JSON.stringify(conPrecio), { status: 200 }));
    const grupos = await buscadorDeConsulta("insumos", { detalle: true, paraArmarAl: "2026-08-15" })("cemento", new AbortController().signal, 8);
    expect(fetchFalso.mock.calls[0][0]).toBe("/v1/consulta/insumos?q=cemento&limite=8&detalle=true&para_armar_al=2026-08-15");
    expect(grupos[0].opciones[0].valor).toMatchObject({ precio: "18.00", moneda: "Bs", fecha_precio: "2026-07-01" });
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

  test("si los materiales fallan (módulo de producción apagado), siguen los insumos del catálogo", async () => {
    fetchFalso.mockImplementation(async (entrada) => {
      if (String(entrada) === "/v1/produccion/materiales") return new Response("{}", { status: 404 });
      return new Response(JSON.stringify(RESPUESTA), { status: 200 });
    });
    const grupos = await buscadorDeComponentes()("agr", new AbortController().signal, 8);
    expect(grupos.map((g) => g.rotulo)).toEqual(["Insumos del catálogo"]);
  });
});
