import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import RecetaPlanta from "./RecetaPlanta";

// Datos ficticios. La API manda las cantidades como texto con punto; la pantalla las muestra con coma.
const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["operar_arenera", "registrar_costos_produccion"],
  modo_entrega: false,
};

const VIGENTE = {
  id: 3,
  producto: "MZP-01",
  componentes: [
    { codigo: "AGR-12", cantidad_por_t: "0.94", unidad: "t", tipo: "propio" },
    { codigo: "CA-30", cantidad_por_t: "0.05", unidad: "t", tipo: "comprado" },
    { codigo: "GO", cantidad_por_t: "8", unidad: "l", tipo: "comprado" },
  ],
  fuente: "dosificación ficticia 12",
  vigente_desde: "2026-11-01",
};

const INSUMOS = [
  { valor: "AGR-12", etiqueta: "Agregado grueso ficticio (AGR-12, t)", fuente: "Catálogo de la carpeta de trabajo: material" },
  { valor: "CA-30", etiqueta: "Cemento asfáltico ficticio (CA-30, t)", fuente: "Catálogo de la carpeta de trabajo: material" },
];

function consulta(q: string) {
  const buscado = q.toLowerCase();
  const resultados = INSUMOS.filter((i) => i.etiqueta.toLowerCase().includes(buscado));
  return { tabla: "insumos", resultados, hay_mas: false };
}

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("Receta de la planta", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let vigente: () => Response;
  let alta: () => Response;
  let usuario: ReturnType<typeof userEvent.setup>;
  const alExpirar = vi.fn();

  function montar() {
    render(
      <ContextoAplicacion.Provider value={{ sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar }}>
        <MemoryRouter>
          <RecetaPlanta />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  const posts = () =>
    fetchFalso.mock.calls
      .filter((c) => c[1]?.method === "POST")
      .map((c) => ({ ruta: String(c[0]), cuerpo: JSON.parse(String(c[1]?.body)) }));

  async function abrir() {
    await usuario.click(screen.getByRole("button", { name: "Registrar una receta nueva" }));
    return screen.getByRole("dialog", { name: "Registrar una receta nueva" });
  }

  async function llenarComponente(dialogo: HTMLElement, n: number, codigo: string, cantidad: string, unidad = "t", tipo = "propio") {
    const fila = within(dialogo).getByRole("group", { name: `Componente ${n}` });
    await usuario.type(within(fila).getByLabelText("Código"), codigo);
    await usuario.type(within(fila).getByLabelText("Cantidad por t"), cantidad);
    await usuario.selectOptions(within(fila).getByLabelText("Unidad"), unidad);
    await usuario.selectOptions(within(fila).getByLabelText("Tipo"), tipo);
  }

  async function llenarCabecera(dialogo: HTMLElement) {
    await usuario.type(within(dialogo).getByLabelText("Producto (código)"), "MZP-01");
    await usuario.type(within(dialogo).getByLabelText("Vigente desde"), "2026-11-01");
    await usuario.type(within(dialogo).getByLabelText("Fuente (dosificación)"), "dosificación ficticia 12");
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 10, 15, 10, 0, 0));
    usuario = userEvent.setup();
    fijarCsrf("tok");
    alExpirar.mockReset();
    fetchFalso.mockReset();
    vi.stubGlobal("fetch", fetchFalso);
    vigente = () => json(VIGENTE);
    alta = () => json({ id: 4 }, 201);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/produccion/recetas/vigente" && metodo === "GET") return vigente();
      if (url.pathname === "/v1/produccion/recetas" && metodo === "POST") return alta();
      if (url.pathname === "/v1/consulta/insumos") return json(consulta(url.searchParams.get("q") ?? ""));
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("tiene un solo h1 y pide el producto antes de buscar", () => {
    montar();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1, name: "Receta de la planta" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ver la receta vigente" })).toBeDisabled();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("muestra la receta vigente con la suma de masa, sin contar los litros", async () => {
    montar();
    await usuario.type(screen.getByLabelText("Producto (código)"), "MZP-01");
    await usuario.click(screen.getByRole("button", { name: "Ver la receta vigente" }));
    const region = await screen.findByRole("region", { name: "Receta vigente" });
    expect(within(region).getByText(/Receta n\.º 3 de MZP-01/)).toHaveTextContent("vigente desde 01/11/2026");
    expect(within(region).getByRole("row", { name: /AGR-12/ })).toHaveTextContent("0,94");
    expect(within(region).getByText("Suma de masa: 0,99 t por t de mezcla")).toBeInTheDocument();
    expect(fetchFalso.mock.calls[0]![0]).toBe("/v1/produccion/recetas/vigente?producto=MZP-01&fecha=2026-11-15");
  });

  test("sin receta vigente dice lo que dijo el servidor", async () => {
    vigente = () => json({ detalle: "No hay receta vigente de MZP-09 el 2026-11-15." }, 404);
    montar();
    await usuario.type(screen.getByLabelText("Producto (código)"), "MZP-09");
    await usuario.click(screen.getByRole("button", { name: "Ver la receta vigente" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No hay receta vigente de MZP-09 el 2026-11-15.");
  });

  test("la receta muestra la suma de masa y bloquea Guardar si no está entre 0,98 y 1,02", async () => {
    montar();
    const dialogo = await abrir();
    const guardar = within(dialogo).getByRole("button", { name: "Registrar receta" });
    const suma = within(dialogo).getByRole("status", { name: "Suma de masa" });
    expect(suma).toHaveTextContent("0 t por t de mezcla");
    expect(suma).toHaveTextContent("entre 0,98 y 1,02");
    await llenarCabecera(dialogo);
    await llenarComponente(dialogo, 1, "AGR-12", "0,90");
    await usuario.click(within(dialogo).getByRole("button", { name: "Agregar un componente" }));
    await llenarComponente(dialogo, 2, "CA-30", "0,05", "t", "comprado");
    expect(suma).toHaveTextContent("0,95 t por t de mezcla");
    expect(suma).toHaveTextContent("fuera del rango");
    expect(guardar).toBeDisabled();
    await usuario.clear(within(dialogo).getAllByLabelText("Cantidad por t")[0]!);
    await usuario.type(within(dialogo).getAllByLabelText("Cantidad por t")[0]!, "0,94");
    expect(suma).toHaveTextContent("0,99 t por t de mezcla");
    expect(suma).not.toHaveTextContent("fuera del rango");
    expect(guardar).toBeEnabled();
    expect(posts()).toHaveLength(0);
  });

  test("registra la receta con las cantidades en punto decimal y deja el foco en el aviso", async () => {
    montar();
    const dialogo = await abrir();
    await llenarCabecera(dialogo);
    await llenarComponente(dialogo, 1, "AGR-12", "0,94");
    await usuario.click(within(dialogo).getByRole("button", { name: "Agregar un componente" }));
    await llenarComponente(dialogo, 2, "CA-30", "0,05", "t", "comprado");
    await usuario.click(within(dialogo).getByRole("button", { name: "Agregar un componente" }));
    await llenarComponente(dialogo, 3, "GO", "8", "l", "comprado");
    await usuario.click(within(dialogo).getByRole("button", { name: "Registrar receta" }));
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(posts()[0]!.ruta).toBe("/v1/produccion/recetas");
    expect(posts()[0]!.cuerpo).toEqual({
      producto: "MZP-01",
      vigente_desde: "2026-11-01",
      fuente: "dosificación ficticia 12",
      componentes: [
        { codigo: "AGR-12", cantidad_por_t: "0.94", unidad: "t", tipo: "propio" },
        { codigo: "CA-30", cantidad_por_t: "0.05", unidad: "t", tipo: "comprado" },
        { codigo: "GO", cantidad_por_t: "8", unidad: "l", tipo: "comprado" },
      ],
    });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(document.activeElement).toBe(screen.getByText("Receta registrada.").closest("[tabindex]")));
  });

  test("ni la unidad, ni el tipo, ni la fecha tienen valor por defecto", async () => {
    montar();
    const dialogo = await abrir();
    const fila = within(dialogo).getByRole("group", { name: "Componente 1" });
    expect(within(fila).getByLabelText("Unidad")).toHaveValue("");
    expect(within(fila).getByLabelText("Tipo")).toHaveValue("");
    expect(within(dialogo).getByLabelText("Vigente desde")).toHaveValue("");
    // Con la masa en rango y sin producto, la pantalla dice qué falta.
    await llenarComponente(dialogo, 1, "AGR-12", "1");
    await usuario.click(within(dialogo).getByRole("button", { name: "Registrar receta" }));
    expect(await within(dialogo).findByText("Indique el código del producto.")).toBeInTheDocument();
    expect(await within(dialogo).findByText("Indique desde qué fecha rige la receta.")).toBeInTheDocument();
    expect(await within(dialogo).findByText("Indique la fuente de la receta (la dosificación de donde sale).")).toBeInTheDocument();
    expect(posts()).toHaveLength(0);
  });

  test("un componente propio en litros se rechaza antes de enviar", async () => {
    montar();
    const dialogo = await abrir();
    await llenarCabecera(dialogo);
    await llenarComponente(dialogo, 1, "CA-30", "1", "t", "comprado");
    await usuario.click(within(dialogo).getByRole("button", { name: "Agregar un componente" }));
    await llenarComponente(dialogo, 2, "AGR-12", "0,5", "l", "propio");
    await usuario.click(within(dialogo).getByRole("button", { name: "Registrar receta" }));
    expect(await within(dialogo).findByRole("alert")).toHaveTextContent(
      "Componente 2: un componente propio sale del inventario y va en t.",
    );
    expect(posts()).toHaveLength(0);
  });

  test("quitar un componente tiene nombre propio que empieza por el texto visible", async () => {
    montar();
    const dialogo = await abrir();
    await usuario.click(within(dialogo).getByRole("button", { name: "Agregar un componente" }));
    await usuario.type(within(dialogo).getAllByLabelText("Código")[1]!, "CA-30");
    const quitar = within(dialogo).getByRole("button", { name: "Quitar componente 2 (CA-30)" });
    expect(quitar).toHaveTextContent("Quitar");
    await usuario.click(quitar);
    expect(within(dialogo).queryByRole("group", { name: "Componente 2" })).not.toBeInTheDocument();
    // El foco pasa a «Agregar un componente», que sigue ahí.
    expect(document.activeElement).toBe(within(dialogo).getByRole("button", { name: "Agregar un componente" }));
  });

  test("el 422 del servidor se lee en español, sin estado ni cuerpo técnico", async () => {
    alta = () => json({ detail: [{ loc: ["body"], msg: "x", type: "y" }] }, 422);
    montar();
    const dialogo = await abrir();
    await llenarCabecera(dialogo);
    await llenarComponente(dialogo, 1, "AGR-12", "1");
    await usuario.click(within(dialogo).getByRole("button", { name: "Registrar receta" }));
    const alerta = await within(dialogo).findByRole("alert");
    expect(alerta).toHaveTextContent("Revise los datos: alguno no es válido.");
    expect(alerta).not.toHaveTextContent(/422|loc|detail/);
  });

  test("Esc cierra el diálogo y devuelve el foco al botón que lo abrió", async () => {
    montar();
    const boton = screen.getByRole("button", { name: "Registrar una receta nueva" });
    await usuario.click(boton);
    await usuario.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(document.activeElement).toBe(boton);
  });

  test("el código del producto y el de cada componente se buscan en los insumos del catálogo", async () => {
    montar();
    const dialogo = await abrir();
    const producto = within(dialogo).getByRole("combobox", { name: "Producto (código)" });
    await usuario.type(producto, "agre");
    const lista = await within(dialogo).findByRole("listbox");
    expect(within(lista).getAllByRole("option")).toHaveLength(1);
    await usuario.keyboard("{ArrowDown}{Enter}");
    expect(producto).toHaveValue("AGR-12");
    expect(fetchFalso.mock.calls.some((c) => String(c[0]).startsWith("/v1/consulta/insumos?q=agre"))).toBe(true);

    const fila = within(dialogo).getByRole("group", { name: "Componente 1" });
    const componente = within(fila).getByRole("combobox", { name: "Código" });
    await usuario.type(componente, "cemento");
    await within(dialogo).findByRole("listbox");
    await usuario.keyboard("{ArrowDown}{Enter}");
    expect(componente).toHaveValue("CA-30");
  });

  test("un código que no está en la lista se puede usar tal cual", async () => {
    montar();
    const dialogo = await abrir();
    const producto = within(dialogo).getByRole("combobox", { name: "Producto (código)" });
    await usuario.type(producto, "MZP-77");
    expect(producto).toHaveValue("MZP-77");
  });
});
