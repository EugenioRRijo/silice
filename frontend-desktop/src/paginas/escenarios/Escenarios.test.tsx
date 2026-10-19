import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaEscenarios from "./index";
import type { EscenarioRespuesta, EscenariosBaseRespuesta, EscenariosRespuesta } from "./tipos";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

const FCAS = "FCAS (fracción; 6.00 = prestaciones del 600 %)";

const LISTA = [
  { codigo: "FIC-1", total: "1000.00", proyecto: "Obra ficticia" },
  { codigo: "FIC-2", total: "2000.00", proyecto: "Otra obra ficticia" },
];

const BASE_1: EscenariosBaseRespuesta = {
  codigo: "FIC-1",
  proyecto: "Obra ficticia",
  moneda: "USD",
  total: "1000.00",
  parametros: { fcas: "6.00", bono_alimentacion: "2.50", administracion: "0.10", utilidad: "0.12" },
  pendientes_base: [],
};
const BASE_2: EscenariosBaseRespuesta = {
  ...BASE_1,
  codigo: "FIC-2",
  proyecto: "Otra obra ficticia",
  total: "2000.00",
  parametros: { fcas: "5.00", bono_alimentacion: "1.00", administracion: "0.08", utilidad: "0.10" },
};

function escenario(nombre: string, total: string): EscenarioRespuesta {
  return {
    nombre,
    total,
    variacion: "50.00",
    variacion_pct: "5.00",
    hallazgos: 2,
    insumos_variados: 1,
    partidas: [
      {
        codigo_partida: "P-001",
        descripcion: "Partida ficticia",
        cantidad: "10.00",
        pu_anterior: "100.00",
        pu_nuevo: "105.00",
        variacion_pct: "5.00",
        total_anterior: "1000.00",
        total_nuevo: "1050.00",
        incidencia_pct: "100.00",
      },
    ],
  };
}

// Carbon antepone al titulo el aviso de ordenacion: se compara el final.
const titulo = (c: HTMLElement) => (c.textContent ?? "").replace(/^Click to sort rows by .* header in ascending order/, "");

describe("Escenarios de sensibilidad", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let lista: unknown;
  let bases: Record<string, EscenariosBaseRespuesta>;
  let alPostear: (cuerpo: { escenarios: { nombre: string }[] }) => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    lista = LISTA;
    bases = { "FIC-1": BASE_1, "FIC-2": BASE_2 };
    alPostear = (cuerpo) =>
      json({
        codigo_base: "FIC-1",
        total_base: "1000.00",
        pendientes_base: [],
        escenarios: cuerpo.escenarios.map((e, i) => escenario(e.nombre, `${1050 + i}.00`)),
      } satisfies EscenariosRespuesta);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      const metodo = init?.method ?? "GET";
      if (url === "/presupuestos") return json(lista);
      const base = /^\/presupuestos\/([^/]+)\/escenarios\/base\?proyecto=/.exec(url);
      if (base) return json(bases[decodeURIComponent(base[1])]);
      if (metodo === "POST" && url.includes("/escenarios/csv?")) {
        return new Response("a,b\n1,2\n", { status: 200, headers: { "Content-Type": "text/csv" } });
      }
      if (metodo === "POST" && url.includes("/escenarios?")) {
        return alPostear(JSON.parse(String(init?.body)));
      }
      return json({ detalle: "ruta no prevista" }, 404);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(alExpirar = vi.fn()) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaEscenarios />
      </ContextoAplicacion.Provider>,
    );
    return alExpirar;
  }

  const posts = () => fetchFalso.mock.calls.filter(([, init]) => init?.method === "POST");
  const cuerpoDe = (llamada: (typeof fetchFalso.mock.calls)[number]) => JSON.parse(String(llamada[1]?.body));

  async function listo() {
    await screen.findByLabelText(FCAS);
    await waitFor(() => expect(screen.getByLabelText(FCAS)).toHaveValue("6.00"));
  }

  test("lista los presupuestos con etiqueta proyecto / codigo y muestra el texto de ayuda", async () => {
    montar();
    await listo();
    expect(screen.getByText(/Recalcula un presupuesto guardado variando parámetros de costo o precios de insumos/)).toBeInTheDocument();
    const selector = screen.getByLabelText("Presupuesto base");
    expect(within(selector).getByRole("option", { name: "Obra ficticia / FIC-1" })).toBeInTheDocument();
    expect(within(selector).getByRole("option", { name: "Otra obra ficticia / FIC-2" })).toBeInTheDocument();
    expect(screen.getByText("Defina un escenario para compararlo contra el presupuesto base.")).toBeInTheDocument();
  });

  test("sin presupuestos guardados muestra el estado vacio", async () => {
    lista = [];
    montar();
    expect(await screen.findByText("No hay presupuestos guardados todavía: elabore uno primero.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Presupuesto base")).toBeNull();
  });

  test("precarga los parametros del base y el nombre por omision", async () => {
    montar();
    await listo();
    expect(screen.getByLabelText("Bono de alimentación")).toHaveValue("2.50");
    expect(screen.getByLabelText("Administración")).toHaveValue("0.10");
    expect(screen.getByLabelText("Utilidad")).toHaveValue("0.12");
    expect(screen.getByLabelText("Nombre del escenario")).toHaveValue("escenario 1");
    expect(fetchFalso).toHaveBeenCalledWith(
      "/presupuestos/FIC-1/escenarios/base?proyecto=Obra%20ficticia",
      expect.anything(),
    );
  });

  test("declara los pendientes del base", async () => {
    bases["FIC-1"] = {
      ...BASE_1,
      pendientes_base: [
        { codigo_partida: "X-9", descripcion: "Algo ficticio", unidad: "m2", cantidad: "3.5", origen_id: "ITEM-7" },
      ],
    };
    montar();
    expect(await screen.findByText("El presupuesto base tiene ítems pendientes, sin partida en el catálogo:")).toBeInTheDocument();
    expect(screen.getByText("- ITEM-7: X-9 (Algo ficticio)")).toBeInTheDocument();
    expect(screen.getByText(/Pendientes del base: los escenarios solo recalculan los renglones valorados/)).toBeInTheDocument();
  });

  test("genera un escenario con los cuatro parametros y los precios, y luego un segundo con los dos", async () => {
    montar();
    await listo();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "Agregar precio" }));
    await usuario.type(screen.getByLabelText("Insumo 1"), "  Cemento ficticio ");
    await usuario.type(screen.getByLabelText("Precio nuevo 1"), "18.50");
    await usuario.click(screen.getByRole("button", { name: "Agregar precio" }));
    await usuario.type(screen.getByLabelText("Precio nuevo 2"), "99"); // insumo en blanco: se ignora
    await usuario.click(screen.getByRole("button", { name: "Generar escenario" }));

    expect(await screen.findByText("Comparación contra el base")).toBeInTheDocument();
    expect(posts()).toHaveLength(1);
    expect(posts()[0][0]).toBe("/presupuestos/FIC-1/escenarios?proyecto=Obra%20ficticia");
    expect(cuerpoDe(posts()[0])).toEqual({
      escenarios: [
        {
          nombre: "escenario 1",
          fcas: "6.00",
          bono_alimentacion: "2.50",
          administracion: "0.10",
          utilidad: "0.12",
          precios: { "Cemento ficticio": "18.50" },
        },
      ],
    });
    const tabla = screen.getByRole("table", { name: "Comparación contra el base" });
    const filas = within(tabla).getAllByRole("row");
    expect(within(filas[1]).getAllByRole("cell").map((c) => c.textContent)).toEqual(["FIC-1", "1000.00", "0.00(sin variación)", "0.00(sin variación)"]);
    expect(within(filas[2]).getAllByRole("cell").map((c) => c.textContent)).toEqual(["escenario 1", "1050.00", "50.00(desfavorable)", "5.00(desfavorable)"]);

    // el nombre por omision avanza y el segundo envio lleva los dos
    expect(screen.getByLabelText("Nombre del escenario")).toHaveValue("escenario 2");
    await usuario.click(screen.getByRole("button", { name: "Generar escenario" }));
    await waitFor(() => expect(posts()).toHaveLength(2));
    expect(cuerpoDe(posts()[1]).escenarios.map((e: { nombre: string }) => e.nombre)).toEqual(["escenario 1", "escenario 2"]);
    await waitFor(() =>
      expect(within(screen.getByRole("table", { name: "Comparación contra el base" })).getAllByRole("row")).toHaveLength(4),
    );
  });

  test("un 422 muestra el error y el escenario nuevo no queda en la lista", async () => {
    alPostear = () => json({ detalle: "utilidad no puede ser negativa" }, 422);
    montar();
    await listo();
    const usuario = userEvent.setup();
    await usuario.clear(screen.getByLabelText("Utilidad"));
    await usuario.type(screen.getByLabelText("Utilidad"), "-1");
    await usuario.click(screen.getByRole("button", { name: "Generar escenario" }));
    expect((await screen.findAllByText("utilidad no puede ser negativa")).length).toBeGreaterThan(0);
    expect(screen.getByText("Defina un escenario para compararlo contra el presupuesto base.")).toBeInTheDocument();
    expect(screen.getByLabelText("Nombre del escenario")).toHaveValue("escenario 1");
    // corregido, el siguiente envio lleva solo el escenario valido
    alPostear = (cuerpo) =>
      json({
        codigo_base: "FIC-1",
        total_base: "1000.00",
        pendientes_base: [],
        escenarios: cuerpo.escenarios.map((e) => escenario(e.nombre, "1.00")),
      });
    await usuario.clear(screen.getByLabelText("Utilidad"));
    await usuario.type(screen.getByLabelText("Utilidad"), "0.12");
    await usuario.click(screen.getByRole("button", { name: "Generar escenario" }));
    await screen.findByText("Comparación contra el base");
    expect(cuerpoDe(posts()[1]).escenarios).toHaveLength(1);
  });

  test("cambiar de base descarta los escenarios y recarga los parametros", async () => {
    montar();
    await listo();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "Generar escenario" }));
    await screen.findByText("Comparación contra el base");
    await usuario.selectOptions(screen.getByLabelText("Presupuesto base"), "FIC-2");
    await waitFor(() => expect(screen.getByLabelText(FCAS)).toHaveValue("5.00"));
    expect(screen.getByText("Defina un escenario para compararlo contra el presupuesto base.")).toBeInTheDocument();
    expect(screen.getByLabelText("Nombre del escenario")).toHaveValue("escenario 1");
  });

  test("una respuesta vieja de base se descarta si ya se eligio otra", async () => {
    const pendientes: Record<string, (r: Response) => void> = {};
    fetchFalso.mockImplementation((entrada) => {
      const url = String(entrada);
      if (url === "/presupuestos") return Promise.resolve(json(LISTA));
      const m = /^\/presupuestos\/([^/]+)\/escenarios\/base/.exec(url);
      return new Promise<Response>((resolver) => {
        pendientes[m![1]] = resolver;
      });
    });
    montar();
    await waitFor(() => expect(pendientes["FIC-1"]).toBeDefined());
    const usuario = userEvent.setup();
    await usuario.selectOptions(await screen.findByLabelText("Presupuesto base"), "FIC-2");
    await waitFor(() => expect(pendientes["FIC-2"]).toBeDefined());
    pendientes["FIC-2"](json(BASE_2));
    await waitFor(() => expect(screen.getByLabelText(FCAS)).toHaveValue("5.00"));
    pendientes["FIC-1"](json(BASE_1));
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.getByLabelText(FCAS)).toHaveValue("5.00");
  });

  test("descarga el CSV por POST con el mismo cuerpo", async () => {
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:x"), revokeObjectURL: vi.fn() });
    montar();
    await listo();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "Generar escenario" }));
    await screen.findByText("Comparación contra el base");
    await usuario.click(screen.getByRole("button", { name: "Descargar tabla (CSV, valores exactos)" }));
    await waitFor(() => expect(posts()).toHaveLength(2));
    expect(posts()[1][0]).toBe("/presupuestos/FIC-1/escenarios/csv?proyecto=Obra%20ficticia");
    expect(cuerpoDe(posts()[1])).toEqual(cuerpoDe(posts()[0]));
  });

  test("Descartar escenarios vacia la lista", async () => {
    montar();
    await listo();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "Generar escenario" }));
    await screen.findByText("Comparación contra el base");
    await usuario.click(screen.getByRole("button", { name: "Descartar escenarios" }));
    expect(screen.getByText("Defina un escenario para compararlo contra el presupuesto base.")).toBeInTheDocument();
    expect(screen.getByLabelText("Nombre del escenario")).toHaveValue("escenario 1");
  });

  test("el detalle por partida trae las nueve columnas y la nota de hallazgos", async () => {
    montar();
    await listo();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "Generar escenario" }));
    await usuario.click(await screen.findByRole("button", { name: "Detalle por partida: escenario 1" }));
    const tabla = screen.getByRole("table", { name: "Detalle por partida: escenario 1" });
    expect(within(tabla).getAllByRole("columnheader").map(titulo)).toEqual([
      "Partida",
      "Descripción",
      "Total anterior",
      "Total nuevo",
      "Variación %",
      "Incidencia %",
      "P.U. anterior",
      "P.U. nuevo",
      "Cantidad",
    ]);
    expect(within(tabla).getByText("1050.00")).toBeInTheDocument();
    expect(
      screen.getByText("Hallazgos de la auditoría del escenario: 2 (el informe se genera siempre). Insumos variados: 1."),
    ).toBeInTheDocument();
  });

  test("un 401 al listar avisa a la aplicacion", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "Sesión vencida" }, 401));
    const alExpirar = montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    expect(await screen.findByText("Sesión vencida")).toBeInTheDocument();
  });

  test("un 401 al generar avisa a la aplicacion", async () => {
    alPostear = () => json({ detalle: "Sesión vencida" }, 401);
    const alExpirar = montar();
    await listo();
    await userEvent.setup().click(screen.getByRole("button", { name: "Generar escenario" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("los encabezados de la comparacion no llevan snake_case", async () => {
    montar();
    await listo();
    await userEvent.setup().click(screen.getByRole("button", { name: "Generar escenario" }));
    const tabla = await screen.findByRole("table", { name: "Comparación contra el base" });
    expect(within(tabla).getAllByRole("columnheader").map(titulo)).toEqual([
      "Escenario",
      "Total",
      "Variación",
      "Variación %",
    ]);
  });

  test("los precios de ensayo enseñan con un ejemplo, tienen cabecera y manejan el foco", async () => {
    montar();
    await listo();
    expect(screen.getByText("p. ej. Cemento Portland → 18.50")).toBeInTheDocument();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "Agregar precio" }));
    expect(screen.getByText("Insumo (descripción exacta)")).toBeInTheDocument();
    expect(screen.getByLabelText("Insumo 1")).toHaveFocus();
    await usuario.click(screen.getByRole("button", { name: "Agregar precio" }));
    expect(screen.getByLabelText("Insumo 2")).toHaveFocus();
    await usuario.click(screen.getByRole("button", { name: "Quitar precio 1" }));
    expect(screen.getByLabelText("Insumo 1")).toHaveFocus(); // la que era la segunda
    await usuario.click(screen.getByRole("button", { name: "Quitar precio 1" }));
    expect(screen.getByRole("button", { name: "Agregar precio" })).toHaveFocus();
  });

  test("un 422 que nombra un parametro marca ese campo", async () => {
    alPostear = () => json({ detalle: "utilidad no puede ser negativa" }, 422);
    montar();
    await listo();
    await userEvent.setup().click(screen.getByRole("button", { name: "Generar escenario" }));
    await screen.findAllByText("utilidad no puede ser negativa");
    expect(screen.getByLabelText("Utilidad")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Administración")).not.toHaveAttribute("aria-invalid", "true");
  });
});
