import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { olvidarFormularios } from "../../shell/sucio";
import { ComponerEnPanel } from "./ComponerEnPanel";

// Ronda 3 del dictamen del autocompletado (2026-11-05), MAYOR 1, por el panel de verdad: el Esc del panel devuelve un campo a su
// valor con un evento `input`, y ese evento no es un tecleo. El origen de una celda se decide por su valor: si vuelve a lo que
// puso el catalogo, sigue siendo del catalogo y el siguiente insumo la reemplaza sin «se conserva el precio que escribio».
// Montos y textos ficticios.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};

const VACIA = {
  estado: "vacio",
  aviso: "Comience por la cabecera (código y descripción) y declare al menos un insumo.",
  desglose: null,
  advertencias: [],
  requiere_justificacion: false,
  contraste: null,
};
const CON_LISTA = {
  moneda: "Bs",
  declarada: true,
  lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-25", origen: "prueba" },
  aviso: null,
};
const CATALOGO = [
  { codigo: "MAT-1", descripcion: "Cemento gris ficticio", unidad: "saco", precio: "18.00" },
  { codigo: "MAT-2", descripcion: "Cemento blanco ficticio", unidad: null, precio: null },
  { codigo: "MAT-3", descripcion: "Cemento rojo ficticio", unidad: "kg", precio: "9.00" },
];
const FECHA = "2026-08-15";

describe("Componer en el panel: Esc no vuelve «tecleado» lo que puso el catálogo", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      const url = new URL(ruta, "http://x");
      if (ruta === "/v1/composicion/opciones") return json({ dominios: ["civil"], modalidades: ["jornal"] });
      if (ruta === "/v1/composicion/evaluar") return json(VACIA);
      if (ruta.startsWith("/v1/composicion/partidas/")) {
        return json({ existe: false, tablas: { materiales: [], equipos: [], mano_obra: [] }, rendimiento_propuesto: null, hay_historial: false });
      }
      if (url.pathname === "/v1/composicion/referencia" || url.pathname === "/v1/composicion/similares") return json([]);
      if (ruta === "/v1/carpeta") return json(CON_LISTA);
      if (ruta === "/v1/consulta/unidades") return json({ unidades: [] });
      if (url.pathname === "/v1/consulta/insumos") {
        const q = (url.searchParams.get("q") ?? "").toLowerCase();
        const resultados = CATALOGO.filter((i) => i.descripcion.toLowerCase().includes(q)).map((i) => ({
          valor: i.codigo,
          etiqueta: `${i.descripcion} (${i.codigo})`,
          fuente: "Catálogo de la carpeta de trabajo: material",
          descripcion: i.descripcion,
          ...(i.unidad ? { unidad: i.unidad } : {}),
          ...(i.precio === null ? {} : { precio: i.precio, moneda: "Bs", fecha_precio: "2026-07-01" }),
        }));
        return json({ tabla: "insumos", hay_mas: false, resultados });
      }
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
    olvidarFormularios();
  });

  async function abrirPanel() {
    const valor: Aplicacion = { sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <ComponerEnPanel partida={{ codigo: "", descripcion: "" }} alCerrar={vi.fn()} alGuardar={vi.fn()} />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
    const panel = await screen.findByRole("complementary", { name: "Componer una partida" });
    await within(panel).findByText("Precios en Bs", {}, { timeout: 3000 });
    fireEvent.change(within(panel).getByLabelText("Fecha"), { target: { value: FECHA } });
    await userEvent.click(within(panel).getByRole("button", { name: "Agregar fila a Materiales" }));
    return panel;
  }

  const descripcion = () => screen.getByRole("combobox", { name: "Descripción, fila 1" });
  const unidad = () => screen.getByRole("combobox", { name: "Unidad, fila 1" });
  const precio = () => screen.getByRole("textbox", { name: "Precio, fila 1" });

  async function elegir(buscado: string, nombre: RegExp) {
    await userEvent.clear(descripcion());
    await userEvent.type(descripcion(), buscado);
    await userEvent.click(await screen.findByRole("option", { name: nombre }));
    await waitFor(() => expect(screen.queryByRole("listbox")).not.toBeInTheDocument());
  }

  // Elige el cemento gris (18,00), teclea un 5 al final del precio y pulsa Esc: el panel lo devuelve a «18,00».
  async function conElPrecioTecleadoYDevueltoPorEsc() {
    await abrirPanel();
    await elegir("cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    await userEvent.type(precio(), "5");
    expect(precio()).toHaveValue("18,005");
    await userEvent.keyboard("{Escape}");
    expect(precio()).toHaveValue("18,00");
    expect(screen.getByRole("complementary", { name: "Componer una partida" })).toBeInTheDocument();
  }

  test("tecleo, Esc y un insumo sin precio ni unidad: la celda del precio y la de la unidad se vacían", async () => {
    await conElPrecioTecleadoYDevueltoPorEsc();
    await elegir("cemento b", /Cemento blanco ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
    expect(precio()).toHaveValue("");
    expect(unidad()).toHaveValue("");
    expect(precio()).not.toHaveAccessibleDescription(expect.stringContaining("se conserva"));
  });

  test("tecleo, Esc y un insumo con precio: se reemplaza sin «se conserva el precio que escribió»", async () => {
    await conElPrecioTecleadoYDevueltoPorEsc();
    await elegir("cemento r", /Cemento rojo ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("9,00"));
    expect(unidad()).toHaveValue("kg");
    expect(precio()).not.toHaveAccessibleDescription(expect.stringContaining("se conserva"));
    expect(precio()).not.toHaveAccessibleDescription(expect.stringContaining("El catálogo tiene"));
  });

  test("teclear, borrar lo tecleado y volver al mismo valor del catálogo: sigue siendo del catálogo", async () => {
    await abrirPanel();
    await elegir("cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    await userEvent.type(precio(), "5");
    await userEvent.clear(precio());
    await userEvent.type(precio(), "18,00");
    expect(precio()).toHaveValue("18,00");

    await elegir("cemento b", /Cemento blanco ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
    expect(precio()).toHaveValue("");
    expect(precio()).not.toHaveAccessibleDescription(expect.stringContaining("se conserva"));
  });

  test("lo que la persona escribió de verdad sigue siendo suyo: con otro valor que el del catálogo se conserva y se dice", async () => {
    await abrirPanel();
    await elegir("cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    await userEvent.type(precio(), "5"); // 18,005: ya no es el del catalogo
    await elegir("cemento r", /Cemento rojo ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento rojo ficticio"));
    expect(precio()).toHaveValue("18,005");
    expect(precio()).toHaveAccessibleDescription(expect.stringContaining("El catálogo tiene 9,00 Bs; se conserva el precio que escribió."));
  });
});

// D16 de la tanda de detalles: elegir en «Código» una partida existente llena la descripción y la unidad y, al rato, precarga
// sus tablas. Un Esc que solo devolviera el código dejaría la partida mezclada (el código de antes con lo de la elegida). Se
// confirma el valor: la base del Esc de «Código» es la partida elegida (patrón de Fiori). Datos
// ficticios con la forma de `api/rutas/busqueda.py`.
describe("Componer en el panel: Esc en «Código» tras elegir una partida existente", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const DEL_CATALOGO = {
    rotulo: "Partidas del catálogo",
    resultados: [
      { clave: "partida:FIC-02", codigo: "FIC-02", descripcion: "Relleno compactado ficticio", unidad: "m3", dominio: "civil", tiene_composicion: true },
    ],
    hay_mas: false,
  };
  const ARENA = { descripcion: "Arena ficticia", unidad: "m3", cantidad: "1", precio: "5,00" };

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      const url = new URL(ruta, "http://x");
      if (ruta === "/v1/composicion/opciones") return json({ dominios: ["civil"], modalidades: ["jornal"] });
      if (ruta === "/v1/composicion/evaluar") return json(VACIA);
      if (ruta === "/v1/composicion/partidas/FIC-02") {
        return json({ existe: true, tablas: { materiales: [ARENA], equipos: [], mano_obra: [] }, rendimiento_propuesto: null, hay_historial: false });
      }
      if (ruta.startsWith("/v1/composicion/partidas/")) {
        return json({ existe: false, tablas: { materiales: [], equipos: [], mano_obra: [] }, rendimiento_propuesto: null, hay_historial: false });
      }
      if (url.pathname === "/v1/composicion/referencia" || url.pathname === "/v1/composicion/similares") return json([]);
      if (ruta === "/v1/carpeta") return json(CON_LISTA);
      if (ruta === "/v1/consulta/unidades") return json({ unidades: [] });
      if (ruta.startsWith("/v1/buscar/partidas?")) return json(DEL_CATALOGO);
      if (ruta.startsWith("/v1/consulta/partidas_viales?")) return json({ tabla: "partidas_viales", resultados: [], hay_mas: false });
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
    olvidarFormularios();
  });

  async function conLaPartidaElegida(codigoInicial = "") {
    const alCerrar = vi.fn();
    const valor: Aplicacion = { sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <ComponerEnPanel partida={{ codigo: codigoInicial, descripcion: "" }} alCerrar={alCerrar} alGuardar={vi.fn()} />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
    const panel = await screen.findByRole("complementary", { name: "Componer una partida" });
    await within(panel).findByText("Precios en Bs", {}, { timeout: 3000 });
    const codigo = within(panel).getByRole("combobox", { name: "Código" });
    await userEvent.clear(codigo);
    await userEvent.type(codigo, "relleno");
    await userEvent.click(await screen.findByRole("option", { name: /FIC-02/ }, { timeout: 3000 }));
    await waitFor(() => expect(codigo).toHaveValue("FIC-02"));
    expect(within(panel).getByLabelText("Descripción")).toHaveValue("Relleno compactado ficticio");
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Descripción, fila 1" })).toHaveValue("Arena ficticia"), { timeout: 3000 });
    return { panel, codigo, alCerrar };
  }

  function esDeLaPartidaElegida(panel: HTMLElement, codigo: HTMLElement) {
    expect(codigo).toHaveValue("FIC-02");
    expect(within(panel).getByLabelText("Descripción")).toHaveValue("Relleno compactado ficticio");
    expect(within(panel).getByLabelText("Unidad")).toHaveValue("m3");
    expect(screen.getByRole("combobox", { name: "Descripción, fila 1" })).toHaveValue("Arena ficticia");
  }

  test.each([
    ["con el código inicial vacío", ""],
    ["con el código inicial «OBRA-04»", "OBRA-04"],
  ])("lo tecleado después de elegir se devuelve con Esc al código elegido, sin partida mezclada (%s)", async (_caso, inicial) => {
    const { panel, codigo, alCerrar } = await conLaPartidaElegida(inicial);
    await userEvent.type(codigo, "9");
    expect(codigo).toHaveValue("FIC-029");
    await userEvent.keyboard("{Escape}");
    esDeLaPartidaElegida(panel, codigo);
    expect(alCerrar).toHaveBeenCalledTimes(0);
  });

  test("elegir y pulsar Esc sin teclear no cambia nada y cierra el panel de una vez", async () => {
    const { panel, codigo, alCerrar } = await conLaPartidaElegida();
    codigo.focus();
    await userEvent.keyboard("{Escape}");
    esDeLaPartidaElegida(panel, codigo);
    expect(alCerrar).toHaveBeenCalledTimes(1);
  });
});
