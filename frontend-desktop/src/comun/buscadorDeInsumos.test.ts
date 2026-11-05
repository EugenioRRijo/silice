import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { buscadorDeInsumosYOficios, descripcionDeInsumo } from "./buscadorDeInsumos";

// AC3: Escenarios (precios de ensayo) y el Simulador piden la DESCRIPCION EXACTA de un insumo, y la que sirve es la de
// cualquier linea de una composicion: material, equipo o mano de obra. Un solo buscador las ofrece de las dos tablas de
// consulta, con `detalle` para recibir la descripcion tal cual (la etiqueta lleva ademas codigo y unidad). Datos ficticios.

const INSUMOS = {
  tabla: "insumos",
  hay_mas: false,
  resultados: [
    {
      valor: "MAT-1",
      etiqueta: "Cemento gris ficticio (MAT-1, saco)",
      fuente: "Catálogo de la carpeta de trabajo: material",
      descripcion: "Cemento gris ficticio",
      unidad: "saco",
    },
  ],
};
const OFICIOS = {
  tabla: "salarios_cct",
  hay_mas: true,
  resultados: [
    {
      valor: "MO-1",
      etiqueta: "Albañil de primera ficticio (MO-1, jornal)",
      fuente: "Catálogo de la carpeta de trabajo: mano obra",
      descripcion: "Albañil de primera ficticio",
      unidad: "jornal",
    },
  ],
};

describe("buscadorDeInsumosYOficios", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async (entrada) =>
      new Response(JSON.stringify(String(entrada).includes("/salarios_cct") ? OFICIOS : INSUMOS), { status: 200 }),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  test("consulta insumos y salarios_cct con detalle y la misma señal de aborto", async () => {
    const control = new AbortController();
    await buscadorDeInsumosYOficios()("ficticio", control.signal, 8);
    const rutas = fetchFalso.mock.calls.map(([ruta]) => String(ruta)).sort();
    expect(rutas).toEqual([
      "/v1/consulta/insumos?q=ficticio&limite=8&detalle=true",
      "/v1/consulta/salarios_cct?q=ficticio&limite=8&detalle=true",
    ]);
    for (const llamada of fetchFalso.mock.calls) expect(llamada[1]?.signal).toBe(control.signal);
  });

  test("entrega un grupo por tabla, el de insumos primero, con la descripcion exacta en cada opcion", async () => {
    const grupos = await buscadorDeInsumosYOficios()("ficticio", new AbortController().signal, 8);
    expect(grupos.map((g) => g.rotulo)).toEqual(["Insumos del catálogo", "Oficios de mano de obra del catálogo"]);
    expect(grupos[1]!.hayMas).toBe(true);
    expect(grupos.map((g) => descripcionDeInsumo(g.opciones[0]!))).toEqual([
      "Cemento gris ficticio",
      "Albañil de primera ficticio",
    ]);
  });

  test("un fallo de cualquiera de las dos consultas es el fallo de la busqueda (un 401 cierra la sesion)", async () => {
    fetchFalso.mockImplementation(async (entrada) =>
      String(entrada).includes("/salarios_cct")
        ? new Response(JSON.stringify({ detalle: "Sesión vencida" }), { status: 401 })
        : new Response(JSON.stringify(INSUMOS), { status: 200 }),
    );
    await expect(buscadorDeInsumosYOficios()("ficticio", new AbortController().signal, 8)).rejects.toMatchObject({
      estado: 401,
    });
  });
});

describe("descripcionDeInsumo", () => {
  test("es la descripcion del catalogo, no la etiqueta con codigo y unidad; sin descripcion no hay nada que guardar", () => {
    const opcion = (valor: { descripcion?: string | null }) => ({
      clave: "k",
      principal: "Cemento gris ficticio (MAT-1, saco)",
      secundaria: [],
      valor: { valor: "MAT-1", etiqueta: "Cemento gris ficticio (MAT-1, saco)", fuente: "f", ...valor },
    });
    expect(descripcionDeInsumo(opcion({ descripcion: "Cemento gris ficticio" }))).toBe("Cemento gris ficticio");
    expect(descripcionDeInsumo(opcion({}))).toBeNull();
    expect(descripcionDeInsumo(opcion({ descripcion: "  " }))).toBeNull();
  });
});
