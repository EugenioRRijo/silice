import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import PaginaIndices from "./index";
import { SeriesViales } from "./SeriesViales";
import { resumenDeLaSerie } from "./logicaSeriesViales";
import type { ImportacionVial, SeriesViales as Datos } from "./logicaSeriesViales";

// «Series del riesgo vial» en «Índices del BCV»: el índice del asfalto y el gasoil que usa «Riesgo de la obra». La API
// trae la historia (fecha ISO y valor con punto) y el resultado de importar; la pantalla lee fechas dd/mm/aaaa y cifras
// con coma, y no calcula nada. Datos FICTICIOS.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "admin",
  nombre: "Admin de Prueba",
  roles: ["administrador"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["administrar_precios"],
  modo_entrega: false,
};

const VACIAS: Datos = {
  responsable: "Admin de Prueba <admin>",
  series: [
    {
      codigo: "CEMENTO_ASFALTICO_PPI",
      nombre: "PPI de asfalto de EE. UU. (ficticio)",
      organismo: "FRED/BLS",
      unidad: "indice",
      periodicidad: "mensual",
      observaciones: 0,
      desde: "",
      hasta: "",
      historia: [],
      omitidas: 0,
    },
    {
      codigo: "GASOIL_USD",
      nombre: "Gasoil, precio administrado (ficticio)",
      organismo: "Gaceta Oficial",
      unidad: "USD/l",
      periodicidad: "mensual",
      observaciones: 0,
      desde: "",
      hasta: "",
      historia: [],
      omitidas: 0,
    },
  ],
};
const CARGADAS: Datos = {
  ...VACIAS,
  series: [
    {
      ...VACIAS.series[0]!,
      observaciones: 3,
      desde: "2026-01-01",
      hasta: "2026-03-01",
      historia: [
        { fecha: "2026-01-01", valor: "101.2", provisional: false },
        { fecha: "2026-02-01", valor: "1100.39", provisional: true },
        { fecha: "2026-03-01", valor: "103", provisional: false },
      ],
    },
    VACIAS.series[1]!,
  ],
};
const IMPORTADA: ImportacionVial = {
  serie: "CEMENTO_ASFALTICO_PPI",
  importada: true,
  observaciones: 3,
  desde: "2026-01-01",
  hasta: "2026-03-01",
  mensaje: "Se importaron 3 valores del 01/01/2026 al 01/03/2026.",
};
const YA_ESTABA: ImportacionVial = {
  serie: "CEMENTO_ASFALTICO_PPI",
  importada: false,
  observaciones: null,
  desde: null,
  hasta: null,
  mensaje: "Ya estaba importado: este archivo ya se cargó antes para esta serie; no se escribió nada.",
};

describe("Series del riesgo vial", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let leer: () => Response;
  let importar: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    leer = () => json(VACIAS);
    importar = () => json(IMPORTADA);
    fetchFalso.mockImplementation(async (ruta) => {
      const url = String(ruta);
      if (url === "/v1/indices/series-viales") return leer();
      if (url === "/v1/indices/series-viales/importar") return importar();
      if (url === "/v1/indices/contexto")
        return json({ tipos: [], periodicidades: [], unidad_por_defecto: "indice_bs", extensiones: [], lee_xls: true, responsable: "" });
      return json({ detalle: "ruta inesperada " + url }, 404);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(nodo = <SeriesViales />, extra: Partial<Aplicacion> = {}) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
      ...extra,
    };
    return render(<ContextoAplicacion.Provider value={valor}>{nodo}</ContextoAplicacion.Provider>);
  }
  const llamadas = (url: string) => fetchFalso.mock.calls.filter(([r]) => String(r) === url);

  async function elegirArchivo(nombre = "series.csv") {
    const usuario = userEvent.setup();
    await screen.findByRole("heading", { name: "Series del riesgo vial" });
    await screen.findByRole("combobox", { name: "Serie" });
    const campo = document.querySelector('input[type="file"]') as HTMLInputElement;
    await usuario.upload(campo, new File(["serie,fecha,valor,provisional,fuente"], nombre));
    return usuario;
  }

  test("trae las dos series con su definición y dice que todavía no hay valores", async () => {
    montar();
    expect(await screen.findByRole("heading", { name: "Series del riesgo vial" })).toBeInTheDocument();
    await waitFor(() => expect(llamadas("/v1/indices/series-viales")).toHaveLength(1));
    expect(await screen.findByText("PPI de asfalto de EE. UU. (ficticio)")).toBeInTheDocument();
    expect(screen.getByText("Gasoil, precio administrado (ficticio)")).toBeInTheDocument();
    expect(screen.getAllByText("Todavía no hay valores cargados de esta serie.")).toHaveLength(2);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  test("lo cargado se lee con fechas dd/mm/aaaa y cifras con coma y punto de miles", async () => {
    leer = () => json(CARGADAS);
    montar();
    const tabla = await screen.findByRole("table", { name: /CEMENTO_ASFALTICO_PPI/ });
    expect(within(tabla).getByText("01/01/2026")).toBeInTheDocument();
    expect(within(tabla).getByText("101,2")).toBeInTheDocument();
    expect(within(tabla).getByText("1.100,39")).toBeInTheDocument();
    expect(within(tabla).getByText("Provisional")).toBeInTheDocument();
    expect(within(tabla).queryByText("2026-01-01")).not.toBeInTheDocument();
    expect(screen.getByText("3 valores, del 01/01/2026 al 01/03/2026 (indice, mensual).")).toBeInTheDocument();
  });

  test("ofrece las dos series para elegir y propone su organismo como fuente", async () => {
    montar();
    const serie = await screen.findByRole("combobox", { name: "Serie" });
    expect(within(serie).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "CEMENTO_ASFALTICO_PPI · PPI de asfalto de EE. UU. (ficticio)",
      "GASOIL_USD · Gasoil, precio administrado (ficticio)",
    ]);
    expect(screen.getByLabelText("Fuente de la serie")).toHaveValue("FRED/BLS");
    await userEvent.selectOptions(serie, "GASOIL_USD");
    expect(screen.getByLabelText("Fuente de la serie")).toHaveValue("Gaceta Oficial");
  });

  test("una fuente que la persona escribió no la pisa un cambio de serie", async () => {
    montar();
    const usuario = userEvent.setup();
    const fuente = await screen.findByLabelText("Fuente de la serie");
    await usuario.clear(fuente);
    await usuario.type(fuente, "Gaceta Oficial n.º 6.800");
    await usuario.selectOptions(screen.getByRole("combobox", { name: "Serie" }), "GASOIL_USD");
    expect(screen.getByLabelText("Fuente de la serie")).toHaveValue("Gaceta Oficial n.º 6.800");
  });

  test("importar sin elegir el archivo lo dice y no llama a la API", async () => {
    montar();
    await screen.findByRole("combobox", { name: "Serie" });
    await userEvent.click(screen.getByRole("button", { name: "Importar" }));
    expect(await alertaConTexto()).toHaveTextContent("Elija el archivo CSV de la serie.");
    expect(llamadas("/v1/indices/series-viales/importar")).toHaveLength(0);
  });

  test("importar manda la serie, el archivo, la fuente y la fecha, y muestra lo que dice la API", async () => {
    montar();
    const usuario = await elegirArchivo();
    await usuario.click(screen.getByRole("button", { name: "Importar" }));
    expect(await screen.findByText("Se importaron 3 valores del 01/01/2026 al 01/03/2026.")).toBeInTheDocument();
    const [, init] = llamadas("/v1/indices/series-viales/importar")[0]!;
    const cuerpo = init?.body as FormData;
    expect(cuerpo.get("serie")).toBe("CEMENTO_ASFALTICO_PPI");
    expect((cuerpo.get("archivo") as File).name).toBe("series.csv");
    expect(cuerpo.get("fuente")).toBe("FRED/BLS");
    expect(cuerpo.get("fecha_descarga")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  test("al importar vuelve a leer la historia para mostrar lo que quedó guardado", async () => {
    montar();
    const usuario = await elegirArchivo();
    leer = () => json(CARGADAS);
    await usuario.click(screen.getByRole("button", { name: "Importar" }));
    expect(await screen.findByRole("table", { name: /CEMENTO_ASFALTICO_PPI/ })).toBeInTheDocument();
    expect(llamadas("/v1/indices/series-viales")).toHaveLength(2);
  });

  test("«ya estaba importado» se dice como información y no escribe ni relee nada de más", async () => {
    importar = () => json(YA_ESTABA);
    montar();
    const usuario = await elegirArchivo();
    await usuario.click(screen.getByRole("button", { name: "Importar" }));
    expect(await screen.findByText(YA_ESTABA.mensaje)).toBeInTheDocument();
    expect(screen.queryByText("Importación")).not.toBeInTheDocument();
    expect(screen.getByText("Ya estaba importado")).toBeInTheDocument();
  });

  test("una fila rechazada muestra el detalle del servidor y deja el archivo para corregirlo", async () => {
    importar = () => json({ detalle: "No se importó nada: filas rechazadas: series.csv:4: '103,5' lleva coma." }, 422);
    montar();
    const usuario = await elegirArchivo();
    await usuario.click(screen.getByRole("button", { name: "Importar" }));
    expect(await alertaConTexto()).toHaveTextContent("No se importó nada: filas rechazadas: series.csv:4: '103,5' lleva coma.");
    expect(llamadas("/v1/indices/series-viales")).toHaveLength(1);
  });

  test("si la sesión vence al importar avisa al marco", async () => {
    importar = () => json({ detalle: "Entre de nuevo." }, 401);
    const alExpirar = vi.fn();
    montar(<SeriesViales />, { alExpirar });
    const usuario = await elegirArchivo();
    await usuario.click(screen.getByRole("button", { name: "Importar" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("si no se pudo leer lo cargado muestra el error de la API y no el formulario", async () => {
    leer = () => json({ detalle: "El módulo riesgo está apagado en esta instalación." }, 404);
    montar();
    expect(await alertaConTexto()).toHaveTextContent("El módulo riesgo está apagado en esta instalación.");
    expect(screen.queryByRole("button", { name: "Importar" })).not.toBeInTheDocument();
  });

  test("la página de índices trae la sección y la oculta si la instalación apagó el riesgo", async () => {
    const { unmount } = montar(<PaginaIndices />);
    expect(await screen.findByRole("heading", { name: "Series del riesgo vial" })).toBeInTheDocument();
    unmount();
    fetchFalso.mockClear();
    montar(<PaginaIndices />, { modulosApagados: ["riesgo"] });
    await screen.findByRole("heading", { name: "Índices del BCV" });
    expect(screen.queryByRole("heading", { name: "Series del riesgo vial" })).not.toBeInTheDocument();
    expect(llamadas("/v1/indices/series-viales")).toHaveLength(0);
  });

  test("el resumen de una serie con un solo valor dice el día", () => {
    const una = { ...CARGADAS.series[0]!, observaciones: 1, desde: "2026-01-01", hasta: "2026-01-01" };
    expect(resumenDeLaSerie(una)).toBe("1 valor, el 01/01/2026 (indice, mensual).");
  });
});
