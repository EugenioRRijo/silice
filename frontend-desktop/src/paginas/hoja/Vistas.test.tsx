import { act, configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { vistaApu, vistaEspacio, vistaPlan, vistaPresupuesto } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, VersionesRespuesta } from "./logica";

// La primera vista tarda en una máquina cargada (importa Carbon y la tabla): se espera más que el 1 s por omisión.
configure({ asyncUtilTimeout: 5000 });

// El gráfico de Carbon no se dibuja en jsdom: se deja una marca con las filas que recibiría.
vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ datos }: { datos: unknown[] }) => <div data-testid="grafico" data-filas={datos.length} />,
}));

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

const FALTA =
  "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.";
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "001",
  versiones: [{ codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
};
const BORRADOR: BorradorAbierto = {
  id: "id-borrador-aaaaaaaaaaaa",
  base: { proyecto: "OF-001", version: "001", vigente: "001", lista: "Lista", espacio_de: "001", solo_lectura: false, moneda: "USD" },
  resumen: {
    rev: 0,
    moneda: "USD",
    total: { texto: "2703.86", exacto: "2703.860232344044033333333333" },
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
  },
  instantanea: { creadas: 0, mensaje: null },
};

type Respuestas = Partial<Record<"espacio" | "presupuesto" | "apu" | "plan", (url: string) => Response | Promise<Response>>>;

describe("Hoja del proyecto: Espacio, APU, Presupuesto y Plan (3b-2)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    localStorage.clear();
    sessionStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  function servidor(respuestas: Respuestas = {}) {
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if (url === "/v1/hoja/borradores" && metodo === "POST") return json(BORRADOR, 201);
      if (url.includes("/vistas/")) {
        const nombre = /\/vistas\/([a-z]+)/.exec(url)![1] as keyof Respuestas;
        const propia = respuestas[nombre];
        if (propia) return propia(url);
        const porOmision = { espacio: vistaEspacio, presupuesto: vistaPresupuesto, apu: vistaApu, plan: vistaPlan }[nombre]!;
        return json(porOmision());
      }
      return new Response(null, { status: 204 });
    });
  }

  function vistasPedidas(): string[] {
    return fetchFalso.mock.calls.map(([r]) => String(r)).filter((r) => r.includes("/vistas/"));
  }

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
  }

  async function irA(pestana: string) {
    await screen.findByRole("region", { name: "Estado del borrador" });
    await userEvent.click(screen.getByRole("tab", { name: pestana }));
  }

  // --- Espacio y metrajes ---------------------------------------------------------------------

  test("3b-F3: al abrir solo se pide la vista de la pestaña activa, y cada cambio de pestaña pide la suya", async () => {
    servidor();
    montar();
    await screen.findByRole("heading", { level: 3, name: "Ambientes" });
    expect(vistasPedidas()).toEqual(["/v1/hoja/borradores/id-borrador-aaaaaaaaaaaa/vistas/espacio"]);
    await userEvent.click(screen.getByRole("tab", { name: "Presupuesto" }));
    await screen.findByRole("table", { name: "Presupuesto" });
    expect(vistasPedidas()).toHaveLength(2);
    expect(vistasPedidas()[1]).toMatch(/\/vistas\/presupuesto$/);
  });

  test("Espacio: cinco tablas con su título h3, su contador de filas y los rótulos de columna", async () => {
    servidor();
    montar();
    for (const [rotulo, contador] of [
      ["Orígenes de medida", "1 fila"],
      ["Ambientes", "2 filas"],
      ["Fuentes", "1 fila"],
      ["Puntos", "1 fila"],
      ["Vértices de recorridos", "0 filas"],
    ] as const) {
      const titulo = await screen.findByRole("heading", { level: 3, name: rotulo });
      expect(titulo).toHaveClass("cds--type-heading-compact-01");
      expect(titulo.parentElement).toHaveTextContent(contador);
      expect(screen.getByRole("table", { name: rotulo })).toBeInTheDocument();
    }
    const ambientes = screen.getByRole("table", { name: "Ambientes" });
    expect(within(ambientes).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Código",
      "Nombre",
      "Largo (m)",
      "Estado",
      "Acciones",
    ]);
    expect(screen.getByText(/^Describa el espacio en metros/)).toBeInTheDocument();
  });

  test("Espacio: una lista cerrada muestra su rótulo y no el valor interno", async () => {
    servidor();
    montar();
    const puntos = await screen.findByRole("table", { name: "Puntos" });
    expect(within(puntos).getByText("Pared")).toBeInTheDocument();
    expect(within(puntos).queryByText("pared")).toBeNull();
  });

  test("3b-F6: el Estado de cada fila lleva ícono y texto de severidad; el texto completo va en el title", async () => {
    servidor();
    montar();
    const ambientes = await screen.findByRole("table", { name: "Ambientes" });
    const filas = within(ambientes).getAllByRole("row");
    expect(within(filas[1]!).getByText("Advertencia")).toBeInTheDocument();
    expect(filas[1]!.querySelector("svg")).not.toBeNull(); // el color nunca va solo
    expect(
      within(filas[1]!).getByTitle(
        "ADVERTENCIA: ambiente BAN-01: la medida es un supuesto declarado (origen O1)",
      ),
    ).toBeInTheDocument();
    expect(within(filas[2]!).getByText("OK")).toBeInTheDocument();
    const fuentes = screen.getByRole("table", { name: "Fuentes" });
    expect(within(fuentes).getByText("Error")).toBeInTheDocument();
  });

  test("Espacio: las cantidades derivadas, el total y el exacto accesible", async () => {
    servidor();
    montar();
    const derivadas = await screen.findByRole("table", { name: "Cantidades derivadas" });
    const filas = within(derivadas).getAllByRole("row");
    expect(within(filas[1]!).getByText("AF-LLAVE")).toBeInTheDocument();
    expect(within(filas[1]!).getByText("3,00")).toBeInTheDocument();
    expect(within(filas[2]!).getByText("8,25")).toBeInTheDocument();
    expect(within(filas[2]!).getByTitle("8.250000000000000000000000000")).toBeInTheDocument();
    const total = screen.getByTitle("2703.86023234404403");
    expect(total).toHaveTextContent("2.703,86 USD");
    expect(screen.getByText("Valor exacto 2703.86023234404403")).toBeInTheDocument();
  });

  test("Espacio: avisa de las partidas pendientes del catálogo", async () => {
    servidor({ espacio: () => json(vistaEspacio({ pendientes: 2 })) });
    montar();
    expect(
      await screen.findByText(
        "2 partida(s) no tienen composición en el catálogo del caso: quedan pendientes y no suman al total.",
      ),
    ).toBeInTheDocument();
  });

  test("Espacio: sin cantidades derivadas muestra el mensaje del servidor", async () => {
    const vacio = "El borrador todavía no deriva cantidades: agregue un ambiente.";
    servidor({ espacio: () => json(vistaEspacio({ derivadas: [], vacio_mensaje: vacio })) });
    montar();
    expect(await screen.findByText(vacio)).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Cantidades derivadas" })).toBeNull();
  });

  test("Espacio: una tabla ancha se desplaza dentro de su región con teclado, no la página", async () => {
    servidor();
    montar();
    const region = await screen.findByRole("region", { name: "Puntos: desplazar horizontalmente" });
    expect(region).toHaveAttribute("tabindex", "0");
    expect(within(region).getByRole("table", { name: "Puntos" })).toBeInTheDocument();
  });

  test("Espacio: una tabla de más de 100 filas se pagina de 50 en 50", async () => {
    const filas = Array.from({ length: 120 }, (_, i) => ({ id: `A${i + 1}`, nombre: `Ambiente ${i + 1}`, largo: "2" }));
    const base = vistaEspacio();
    servidor({ espacio: () => json(vistaEspacio({ filas: { ...base.filas, ambientes: filas } })) });
    montar();
    const tabla = await screen.findByRole("table", { name: "Ambientes" });
    expect(within(tabla).getAllByRole("row")).toHaveLength(51); // encabezado y 50 filas
    expect(screen.getByText(/1–50 de 120/)).toBeInTheDocument();
  });

  // --- APU ------------------------------------------------------------------------------------

  test("3b-F7: la lista de partidas, su selección y el detalle con los tres rubros", async () => {
    servidor();
    montar();
    await irA("APU");
    const lista = await screen.findByRole("group", { name: "Partidas" });
    const radios = within(lista).getAllByRole("radio");
    expect(radios).toHaveLength(2);
    expect(radios[1]).toBeChecked();
    expect(within(lista).getByLabelText("AF-LLAVE · Llave de paso de agua fria instalada")).toBe(radios[1]);
    expect(screen.getByRole("heading", { level: 2, name: /^AF-LLAVE · Llave de paso de agua fria instalada/ })).toHaveClass(
      "cds--type-heading-compact-02",
    );
    for (const rubro of ["Materiales", "Equipos", "Mano de obra"]) {
      expect(screen.getByRole("heading", { level: 3, name: new RegExp(`^${rubro} ·`) })).toBeInTheDocument();
      expect(screen.getByRole("table", { name: rubro })).toBeInTheDocument();
    }
    expect(screen.getByText("Rendimiento (unidades por día)")).toBeInTheDocument();
    expect(screen.getByText("Subtotal de materiales:").parentElement).toHaveTextContent("7,75 USD");
    expect(screen.getByText("Subtotal de mano de obra:").parentElement).toHaveTextContent("1,97 USD");
  });

  test("APU: el cierre sale en el orden de la clásica con el exacto en el title", async () => {
    servidor();
    montar();
    await irA("APU");
    const cierre = await screen.findByRole("table", { name: "Cierre de partida" });
    const filas = within(cierre).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell")[0]!.textContent)).toEqual([
      "Materiales",
      "Equipos",
      "Mano de obra",
      "= Costo directo",
      "+ Administracion",
      "= Con administracion",
      "+ Utilidad",
      "= Precio unitario",
    ]);
    expect(within(filas[7]!).getByText("13,20 USD")).toBeInTheDocument();
    expect(within(filas[7]!).getByTitle("13.198738025")).toBeInTheDocument();
    expect(within(filas[2]!).getByText("FCAS 6 y bono 5.81, entre el rendimiento")).toBeInTheDocument();
  });

  test("APU: las cantidades y precios de las líneas salen en es-VE con el valor original en el title", async () => {
    servidor();
    montar();
    await irA("APU");
    const materiales = await screen.findByRole("table", { name: "Materiales" });
    expect(within(materiales).getByTitle("7.7483")).toHaveTextContent("7,7483");
  });

  test("3b-F7: escribir en «Buscar partida» pide al servidor la lista filtrada", async () => {
    servidor();
    montar();
    await irA("APU");
    await screen.findByRole("group", { name: "Partidas" });
    await userEvent.type(screen.getByRole("searchbox", { name: "Buscar partida" }), "pic");
    await waitFor(() => expect(vistasPedidas().some((u) => u.includes("/vistas/apu?buscar=pic"))).toBe(true), {
      timeout: 3000,
    });
    // la lista anterior sigue a la vista mientras llega la nueva
    expect(screen.getByRole("group", { name: "Partidas" })).toBeInTheDocument();
  });

  test("3b-F7: sin coincidencias avisa que se muestran todas", async () => {
    servidor({ apu: () => json(vistaApu({ sin_coincidencias: true })) });
    montar();
    await irA("APU");
    expect(await screen.findByText("Ninguna partida coincide; se muestran todas.")).toBeInTheDocument();
  });

  test("APU: elegir otra partida la pide al servidor por su código", async () => {
    servidor();
    montar();
    await irA("APU");
    const lista = await screen.findByRole("group", { name: "Partidas" });
    await userEvent.click(within(lista).getByLabelText(/^AF-CODO-1\/2/));
    await waitFor(() => expect(vistasPedidas().some((u) => u.includes("partida=AF-CODO-1%2F2"))).toBe(true));
  });

  test("APU: los estados de la partida se dicen y sin partidas valoradas aparece el mensaje", async () => {
    const detalle = vistaApu().detalle!;
    servidor({ apu: () => json(vistaApu({ detalle: { ...detalle, estados: ["Estado de AF-LLAVE|x: ADVERTENCIA: algo"] } })) });
    montar();
    await irA("APU");
    expect(await screen.findByText("Estado de AF-LLAVE|x: ADVERTENCIA: algo")).toBeInTheDocument();
  });

  test("APU: sin partidas valoradas muestra el mensaje y no el detalle", async () => {
    const mensaje = "Todavía no hay partidas valoradas: derive cantidades en Espacio y metrajes.";
    servidor({ apu: () => json(vistaApu({ partidas: [], seleccionada: null, detalle: null, vacio_mensaje: mensaje })) });
    montar();
    await irA("APU");
    expect(await screen.findByText(mensaje)).toBeInTheDocument();
    expect(screen.queryByRole("radio")).toBeNull();
  });

  // --- Presupuesto ----------------------------------------------------------------------------

  test("Presupuesto: renglones con cantidad, precio unitario, total y Estado", async () => {
    servidor();
    montar();
    await irA("Presupuesto");
    const tabla = await screen.findByRole("table", { name: "Presupuesto" });
    expect(within(tabla).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Partida",
      "Descripción",
      "Unidad",
      "Cantidad",
      "Precio unitario",
      "Total",
      "Estado",
    ]);
    const filas = within(tabla).getAllByRole("row");
    expect(within(filas[1]!).getByText("13,20")).toBeInTheDocument();
    expect(within(filas[1]!).getByTitle("13.198738025")).toBeInTheDocument();
    expect(within(filas[1]!).getByText("39,60")).toBeInTheDocument();
    expect(within(filas[1]!).getByText("OK")).toBeInTheDocument();
    expect(screen.getByTitle("2703.8602323440440333")).toHaveTextContent("2.703,86 USD");
  });

  test("Presupuesto: una cantidad escrita a mano dice cuál era la calculada y una partida sin APU queda pendiente", async () => {
    servidor();
    montar();
    await irA("Presupuesto");
    const tabla = await screen.findByRole("table", { name: "Presupuesto" });
    const pendiente = within(tabla).getAllByRole("row")[2]!;
    expect(within(pendiente).getByText("5 (calculada: 3)")).toBeInTheDocument();
    expect(within(pendiente).getAllByText("Pendiente")).toHaveLength(2); // sin precio unitario ni total
    expect(within(pendiente).getByText("Error")).toBeInTheDocument();
  });

  test("Presupuesto: sin renglones muestra el mensaje del servidor", async () => {
    const mensaje = "El presupuesto no tiene renglones todavía.";
    servidor({ presupuesto: () => json(vistaPresupuesto({ filas: [], vacio_mensaje: mensaje })) });
    montar();
    await irA("Presupuesto");
    expect(await screen.findByText(mensaje)).toBeInTheDocument();
  });

  // --- Plan y curva ---------------------------------------------------------------------------

  test("3b-F8: con plan, la matriz de fracciones, el gráfico y la tabla de la curva", async () => {
    servidor();
    montar();
    await irA("Plan y curva");
    const matriz = await screen.findByRole("table", { name: "Plan de trabajo" });
    expect(within(matriz).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Partida", "Día 1", "Día 2"]);
    expect(within(within(matriz).getAllByRole("row")[1]!).getAllByRole("cell").map((c) => c.textContent)).toEqual([
      "AF-CODO-1/2",
      "1",
      "0",
    ]);
    expect(await screen.findByTestId("grafico")).toHaveAttribute("data-filas", "2");
    expect(screen.getByRole("heading", { level: 2, name: "Curva de inversión" })).toHaveClass("cds--type-heading-compact-02");
    const curva = screen.getByRole("table", { name: "Curva de inversión: montos" });
    expect(within(curva).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Período",
      "Monto",
      "Acumulado",
      "% acumulado",
    ]);
    const primera = within(curva).getAllByRole("row")[1]!;
    expect(within(primera).getAllByText("11,18")).toHaveLength(2); // monto y acumulado del primer período
    expect(within(primera).getByText("0,41")).toBeInTheDocument();
    expect(within(primera).getByTitle("0.4134")).toBeInTheDocument();
  });

  test("3b-F8: sin plan muestra el mensaje y no hay curva", async () => {
    const mensaje = "Esta versión no tiene plan de trabajo, así que no hay curva de inversión.";
    servidor({
      plan: () => json(vistaPlan({ hay_plan: false, etiquetas: [], filas: [], curva: [], mensaje })),
    });
    montar();
    await irA("Plan y curva");
    expect(await screen.findByText(mensaje)).toBeInTheDocument();
    expect(screen.queryByTestId("grafico")).toBeNull();
    expect(screen.queryByRole("table", { name: "Plan de trabajo" })).toBeNull();
  });

  // --- carga, errores y seguridad -------------------------------------------------------------

  test("mientras llega la vista se ve un marcador de carga con nombre", async () => {
    servidor({ espacio: () => new Promise<Response>(() => undefined) });
    montar();
    expect(await screen.findByRole("status", { name: "Cargando Espacio y metrajes" })).toBeInTheDocument();
  });

  test("3b-F13: un error de la vista muestra su detalle tal cual", async () => {
    servidor({ presupuesto: () => json({ detalle: "No se pudo calcular el presupuesto." }, 500) });
    montar();
    await irA("Presupuesto");
    expect(await screen.findByText("No se pudo calcular el presupuesto.")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  test("3b-F13: un 401 de la vista llama a alExpirar", async () => {
    servidor({ espacio: () => json({ detalle: "Sesión ausente o vencida." }, 401) });
    montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("3b-F13: si el borrador ya no está, una sola vez el aviso y se puede abrir de nuevo", async () => {
    let abiertos = 0;
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if (url === "/v1/hoja/borradores" && metodo === "POST") {
        abiertos += 1;
        return json(BORRADOR, 201);
      }
      if (url.startsWith("/v1/hoja/borradores/") && metodo === "GET") return json({ detalle: FALTA }, 404);
      return new Response(null, { status: 204 });
    });
    montar();
    expect(await screen.findByText(FALTA)).toBeInTheDocument();
    expect(screen.getAllByText(FALTA)).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: "Abrir de nuevo" }));
    await waitFor(() => expect(abiertos).toBe(2));
  });

  test("3b-F14: ninguna vista escribe en el navegador ni pide contraseñas", async () => {
    servidor();
    const { container } = montar();
    await screen.findByRole("table", { name: "Ambientes" });
    for (const p of ["APU", "Presupuesto", "Plan y curva"]) {
      await act(async () => {
        await userEvent.click(screen.getByRole("tab", { name: p }));
      });
    }
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(container.querySelector('input[type="password"]')).toBeNull();
  });

  test("3b-F1: sigue habiendo un solo h1 y las secciones llevan heading-compact-02", async () => {
    servidor();
    montar();
    await screen.findByRole("table", { name: "Cantidades derivadas" });
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 2, name: "Cantidades derivadas" })).toHaveClass(
      "cds--type-heading-compact-02",
    );
  });
});
