import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { HistoricoDePrecios } from "./HistoricoDePrecios";

interface OpcionesCapturadasMercado {
  title?: string;
  axes?: {
    left?: { title?: string; ticks?: { formatter?: (v: number) => string }; thresholds?: { value: number; label?: string }[] };
    right?: unknown;
  };
  color?: { scale: Record<string, string> };
  points?: { enabled?: boolean };
  tooltip?: { valueFormatter?: (v: number, label: string) => string; customHTML?: (data: unknown, html: string, datum: unknown) => string };
}

vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ tipo, datos, opciones }: { tipo: string; datos: { group?: string; key?: string; value?: number }[]; opciones: OpcionesCapturadasMercado }) => {
    const primero = datos[0];
    return (
      <div
        role="img"
        aria-label={opciones.title ?? "Gráfico"}
        data-tipo={tipo}
        data-filas={datos.length}
        data-claves={datos.map((d) => d.key).join("|")}
        data-puntos={String(opciones.points?.enabled)}
        data-eje-titulo={opciones.axes?.left?.title ?? ""}
        data-eje-formato={opciones.axes?.left?.ticks?.formatter?.(1250.5) ?? ""}
        data-doble-eje={String(Boolean(opciones.axes?.right))}
        data-colores={JSON.stringify(opciones.color?.scale ?? null)}
        data-umbrales={JSON.stringify(opciones.axes?.left?.thresholds ?? null)}
        data-globo-formato={opciones.tooltip?.valueFormatter?.(10.625, "p") ?? ""}
        data-globo={primero ? opciones.tooltip?.customHTML?.([primero], "", primero) ?? "" : ""}
      />
    );
  },
}));

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["lector"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["leer_proyecto"],
  modo_entrega: false,
};

const INSUMOS = [
  { codigo: "CEM-GRIS", descripcion: "Cemento ficticio", tipo: "material", unidad: "saco", precio_vigente: "18.00" },
];

const CAMBIOS = [
  { insumo: "Cemento ficticio", precio_anterior: "10.0000", precio_nuevo: "10.6250", variacion: "0.0625", fecha: "2026-02-01" },
];

describe("Histórico de cambios de precio", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    fetchFalso.mockImplementation(async (url) => (String(url) === "/insumos" ? json(INSUMOS) : json(CAMBIOS)));
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <HistoricoDePrecios />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  test("lista los cambios con los montos de la API y la variacion en por ciento", async () => {
    montar();
    const tabla = await screen.findByRole("table", { name: "Cambios de precio" });
    // VB-19: la fecha se lee dd/mm/aaaa; los precios y la variacion, en es-VE con el texto de la API en el title
    // VD-5: la fecha no lleva su forma ISO en el title; el title es de las cifras
    expect(within(tabla).getByText("01/02/2026")).not.toHaveAttribute("title");
    expect(within(tabla).getByText("10,6250")).toHaveAttribute("title", "10,6250");
    expect(within(tabla).getByText("10,0000")).toHaveAttribute("title", "10,0000");
    expect(within(tabla).getByText("6,25 %")).toBeInTheDocument();
    expect(tabla).not.toHaveTextContent("2026-02-01");
    expect(fetchFalso.mock.calls[0]![0]).toBe("/cambios-precio");
  });

  test("los filtros de fecha son selectores de fecha y se envian AAAA-MM-DD (VB-19)", async () => {
    montar();
    await screen.findByRole("table", { name: "Cambios de precio" });
    expect(screen.getByLabelText("Desde")).toHaveAttribute("type", "date");
    expect(screen.getByLabelText("Hasta")).toHaveAttribute("type", "date");
    expect(screen.queryByLabelText(/AAAA-MM-DD/)).toBeNull();
  });

  test("filtra por insumo y fechas validas", async () => {
    const usuario = userEvent.setup();
    montar();
    await screen.findByRole("table", { name: "Cambios de precio" });
    // El insumo se elige de la lista (autocompletado), ya no se escribe la descripción exacta.
    await usuario.type(screen.getByRole("combobox", { name: "Insumo" }), "cemento");
    await usuario.click(await screen.findByRole("option", { name: /Cemento ficticio/ }));
    await usuario.type(screen.getByLabelText("Desde"), "2026-01-01");
    await usuario.click(screen.getByRole("button", { name: "Filtrar" }));
    await waitFor(() =>
      expect(fetchFalso).toHaveBeenLastCalledWith(
        "/cambios-precio?insumo=Cemento+ficticio&desde=2026-01-01",
        expect.anything(),
      ),
    );
  });

  test("un rango invertido avisa y no consulta", async () => {
    const usuario = userEvent.setup();
    montar();
    await screen.findByRole("table", { name: "Cambios de precio" });
    await usuario.type(screen.getByLabelText("Desde"), "2026-03-01");
    await usuario.type(screen.getByLabelText("Hasta"), "2026-02-01");
    expect(screen.getByText("Rango invertido")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Filtrar" }));
    expect(fetchFalso.mock.calls.filter(([u]) => String(u).startsWith("/cambios-precio"))).toHaveLength(1);
  });
  test.each([
    [404, "No existe el histórico en este caso."],
    [403, "Su cuenta no tiene permiso para el histórico."],
  ])("con %i de la API muestra el detalle y no se queda cargando", async (estado, detalle) => {
    fetchFalso.mockImplementation(() => Promise.resolve(json({ detail: detalle }, estado)));
    montar();
    expect(await screen.findByText(detalle)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  test("con un error de red muestra un aviso en vez del esqueleto", async () => {
    fetchFalso.mockRejectedValue(new TypeError("Failed to fetch"));
    montar();
    expect((await screen.findAllByRole("alert")).length).toBeGreaterThan(0);
  });

  // Menor de la Tarea 13 (cierre de F4): Mercado ya tiene sus principales; el histórico no suma ninguno («Filtrar» es
  // secundario, decisión 2).
  test("el histórico no pinta ningún botón principal: «Filtrar» es secundario", async () => {
    montar();
    await screen.findByRole("table", { name: "Cambios de precio" });
    expect(document.querySelectorAll(".cds--btn--primary")).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Filtrar" })).toHaveClass("cds--btn--secondary");
  });

  test("el título es un h2: el h1 es el de Mercado (un solo h1 por pantalla)", async () => {
    montar();
    expect(await screen.findByRole("heading", { level: 2, name: "Histórico de cambios de precio" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
  });

  test("dibuja la evolución del precio con una sola escala vertical, rótulo solo en el último punto, lectura y tabla", async () => {
    const serie = [
      { insumo: "Cemento ficticio", precio_anterior: "10.0000", precio_nuevo: "10.5000", variacion: "0.05", fecha: "2026-01-10" },
      { insumo: "Cemento ficticio", precio_anterior: "10.5000", precio_nuevo: "11.0250", variacion: "0.05", fecha: "2026-02-15" },
      { insumo: "Cemento ficticio", precio_anterior: "11.0250", precio_nuevo: "11.5762", variacion: "0.05", fecha: "2026-03-20" },
    ];
    fetchFalso.mockImplementation(async (url) => (String(url) === "/insumos" ? json(INSUMOS) : json(serie)));
    montar();

    const imagen = await screen.findByRole("img", { name: "Precio registrado de Cemento ficticio (precio unitario)" });
    expect(imagen).toHaveAttribute("data-tipo", "linea");
    expect(imagen).toHaveAttribute("data-doble-eje", "false");
    expect(imagen).toHaveAttribute("data-eje-formato", "1.250,5");
    expect(imagen).toHaveAttribute("data-globo-formato", "10,625");
    expect(JSON.parse(imagen.getAttribute("data-umbrales")!)).toEqual([
      expect.objectContaining({ value: 10, label: "Lista anterior: 10,0000" }),
    ]);

    const cierre = screen.getByRole("list", { name: "Último precio por insumo" });
    const puntosRotulados = within(cierre).getAllByRole("listitem");
    expect(puntosRotulados).toHaveLength(1);
    expect(puntosRotulados[0]).toHaveTextContent("Cemento ficticio (20/03/2026): 11,5762 (+5 %)");

    expect(screen.getByText(/Qué muestra:.*Qué leer:.*20\/03\/2026.*11,5762/)).toBeInTheDocument();
    expect(screen.getByText("Ver como tabla")).toBeInTheDocument();
    expect(within(screen.getByRole("table", { name: "Cambios de precio" })).getAllByRole("row")).toHaveLength(4);
    expect(imagen.getAttribute("data-globo")).toContain("10/01/2026");
    expect(imagen.getAttribute("data-globo")).toContain("10,5000");
  });

  // T4 (mutante H1): un precio que no cambió se lee «0 %», no «+0 %».
  test("una variación nula se rotula sin signo", async () => {
    const serie = [
      { insumo: "Cemento ficticio", precio_anterior: "10.0000", precio_nuevo: "10.0000", variacion: "0", fecha: "2026-01-10" },
    ];
    fetchFalso.mockImplementation(async (url) => (String(url) === "/insumos" ? json(INSUMOS) : json(serie)));
    montar();
    await screen.findByRole("img", { name: /Precio registrado de/ });
    const cierre = screen.getByRole("list", { name: "Último precio por insumo" });
    const rotulo = within(cierre).getByRole("listitem");
    expect(rotulo).toHaveTextContent("(0 %)");
    expect(rotulo).not.toHaveTextContent("+0");
  });

  // T4 (mutante H3): dos cambios del mismo insumo el mismo día no comparten la clave del eje.
  test("dos cambios del mismo insumo el mismo día llevan su número de orden en el eje", async () => {
    const serie = [
      { insumo: "Cemento ficticio", precio_anterior: "10.00", precio_nuevo: "11.00", variacion: "0.10", fecha: "2026-01-10" },
      { insumo: "Cemento ficticio", precio_anterior: "11.00", precio_nuevo: "12.00", variacion: "0.09", fecha: "2026-01-10" },
    ];
    fetchFalso.mockImplementation(async (url) => (String(url) === "/insumos" ? json(INSUMOS) : json(serie)));
    montar();
    const imagen = await screen.findByRole("img", { name: /Precio registrado de/ });
    expect(imagen).toHaveAttribute("data-claves", "10/01/2026|10/01/2026 (2)");
  });

  // T4 (mutante H2): hasta 16 fechas distintas el gráfico marca cada punto; con 17 deja solo la línea.
  test.each([
    [16, "true"],
    [17, "false"],
  ])("con %i fechas distintas los puntos marcados son: %s", async (cuantas, esperado) => {
    const serie = Array.from({ length: cuantas }, (_, i) => ({
      insumo: "Cemento ficticio",
      precio_anterior: "10.00",
      precio_nuevo: "11.00",
      variacion: "0.10",
      fecha: `2026-01-${String(i + 1).padStart(2, "0")}`,
    }));
    fetchFalso.mockImplementation(async (url) => (String(url) === "/insumos" ? json(INSUMOS) : json(serie)));
    montar();
    const imagen = await screen.findByRole("img", { name: /Precio registrado de/ });
    expect(imagen).toHaveAttribute("data-puntos", esperado);
  });

  test("el color sigue al insumo al filtrar y el título incorpora la unidad del catálogo elegido", async () => {
    const varios = [
      { insumo: "Cemento ficticio", precio_anterior: "10.00", precio_nuevo: "11.00", variacion: "0.10", fecha: "2026-02-01" },
      { insumo: "Arena ficticia", precio_anterior: "40.00", precio_nuevo: "42.00", variacion: "0.05", fecha: "2026-02-05" },
    ];
    const catalogo = [
      ...INSUMOS,
      { codigo: "ARE-LAV", descripcion: "Arena ficticia", tipo: "material", unidad: "m3", precio_vigente: "42.00" },
    ];
    fetchFalso.mockImplementation(async (url) => {
      const ruta = String(url);
      if (ruta === "/insumos") return json(catalogo);
      if (ruta.includes("Arena+ficticia")) return json([varios[1]]);
      return json(varios);
    });

    const usuario = userEvent.setup();
    montar();
    const inicial = await screen.findByRole("img", { name: "Precio registrado por insumo (precio unitario)" });
    const coloresIniciales = JSON.parse(inicial.getAttribute("data-colores")!) as Record<string, string>;
    expect(coloresIniciales).toEqual({ "Cemento ficticio": "#2A78D6", "Arena ficticia": "#1BAF7A" });

    await usuario.type(screen.getByRole("combobox", { name: "Insumo" }), "arena");
    await usuario.click(await screen.findByRole("option", { name: /Arena ficticia/ }));
    await usuario.click(screen.getByRole("button", { name: "Filtrar" }));

    const filtrado = await screen.findByRole("img", { name: "Precio registrado de Arena ficticia (por m³)" });
    const coloresFiltrados = JSON.parse(filtrado.getAttribute("data-colores")!) as Record<string, string>;
    expect(coloresFiltrados["Arena ficticia"]).toBe(coloresIniciales["Arena ficticia"]);
  });

  test("escapa nombres de insumo en el detalle del globo y no dibuja gráfico cuando no hay cambios", async () => {
    fetchFalso.mockImplementationOnce(async () =>
      json([{ insumo: "<img src=x onerror=1>", precio_anterior: "1.00", precio_nuevo: "2.00", variacion: "1", fecha: "2026-02-01" }]),
    );
    const vista = montar();
    const conHtml = await screen.findByRole("img", { name: /Precio registrado de/ });
    expect(conHtml.getAttribute("data-globo")).not.toContain("<img");
    expect(conHtml.getAttribute("data-globo")).toContain("&lt;img");
    vista.unmount();

    fetchFalso.mockImplementation(async () => json([]));
    montar();
    expect(await screen.findByText("No hay cambios de precio registrados con esos filtros")).toBeInTheDocument();
    expect(screen.queryByRole("img")).toBeNull();
  });
});
