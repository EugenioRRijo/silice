import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { PresupuestoPorFrentes } from "./PresupuestoPorFrentes";

// Libro por frentes (ola 2, línea 3, 2026-11-13): el presupuesto de la Hoja agrupado por frente. Los subtotales y el total
// general los calcula el servidor (`GET /v1/hoja/borradores/{id}/vistas/frentes`); aquí solo se escriben en es-VE. El
// frente de un renglón se pone a mano (`PUT /v1/hoja/borradores/{id}/frentes`). Se abre a pedido: la pestaña no pide la
// vista hasta que la persona quiere verla. Datos FICTICIOS (los del libro de `tests/fixtures/libro_apu_por_hoja.py`).
const ID = "b".repeat(20);
const RUTA_VISTA = `/v1/hoja/borradores/${ID}/vistas/frentes`;
const RUTA_EDICION = `/v1/hoja/borradores/${ID}/frentes`;
const VISTA = {
  rev: 3,
  frentes: [
    { frente: "FRENTE A", renglones: 5, pendientes: 0, total: { texto: "2814.68", exacto: "2814.6756" } },
    { frente: "FRENTE B", renglones: 4, pendientes: 1, total: { texto: "1876.45", exacto: "1876.4504" } },
    { frente: null, renglones: 1, pendientes: 0, total: { texto: "10.00", exacto: "10" } },
  ],
  total: { texto: "4701.13", exacto: "4701.126" },
  con_frentes: true,
};
const FILAS = [
  { clave: "VF-001|libro:FRENTE A!E4", partida: "VF-001", descripcion: "Riego ficticio", quitable: true },
  { clave: "VF-009|a-mano:1", partida: "VF-009", descripcion: "Señal ficticia", quitable: true },
];

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

function montar(puedeEditar = true, alAceptar = vi.fn()) {
  const valor = { alExpirar: vi.fn() } as unknown as Aplicacion;
  render(
    <ContextoAplicacion.Provider value={valor}>
      <PresupuestoPorFrentes id={ID} rev={3} filas={FILAS} moneda="Bs" puedeEditar={puedeEditar} alAceptar={alAceptar} alAusente={vi.fn()} />
    </ContextoAplicacion.Provider>,
  );
  return alAceptar;
}

// Monta el panel con `rev` y devuelve cómo cambiarlo, como hace la pestaña al aceptar una edición de la Hoja.
function montarConRev(rev: number, alAceptar = vi.fn()) {
  const valor = { alExpirar: vi.fn() } as unknown as Aplicacion;
  const panel = (r: number) => (
    <ContextoAplicacion.Provider value={valor}>
      <PresupuestoPorFrentes id={ID} rev={r} filas={FILAS} moneda="Bs" puedeEditar alAceptar={alAceptar} alAusente={vi.fn()} />
    </ContextoAplicacion.Provider>
  );
  const { rerender } = render(panel(rev));
  return (r: number) => rerender(panel(r));
}

describe("El presupuesto por frente", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let usuario: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    usuario = userEvent.setup();
    fijarCsrf("tok");
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async (ruta, opciones) =>
      String(ruta) === RUTA_EDICION && opciones?.method === "PUT"
        ? json({
            rev: 4,
            resumen: { rev: 4, moneda: "Bs", total: VISTA.total, cambios: 0, pendientes_catalogo: 0 },
            frentes: { ...VISTA, rev: 4, frentes: [{ frente: "Norte", renglones: 1, pendientes: 0, total: { texto: "10.00", exacto: "10" } }, ...VISTA.frentes.slice(0, 2)] },
          })
        : json(VISTA),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  test("no pide nada hasta que se abre, y entonces muestra los subtotales del servidor con coma decimal", async () => {
    montar();
    expect(fetchFalso).not.toHaveBeenCalled();
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    const tabla = await screen.findByRole("table", { name: "Presupuesto por frente" });
    expect(String(fetchFalso.mock.calls[0]![0])).toBe(RUTA_VISTA);
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["FRENTE A", "5", "2.814,68"],
      ["FRENTE B", "4 (1 pendiente)", "1.876,45"],
      ["(sin frente)", "1", "10,00"],
    ]);
    expect(screen.getByText("Total general: 4.701,13 Bs")).toBeInTheDocument();
  });

  test("pone el frente de un renglón y muestra lo que devuelve el servidor", async () => {
    const alAceptar = montar();
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    await screen.findByRole("table", { name: "Presupuesto por frente" });
    await usuario.selectOptions(screen.getByRole("combobox", { name: "Partida del presupuesto" }), "VF-009|a-mano:1");
    await usuario.type(screen.getByRole("textbox", { name: "Frente" }), "Norte");
    expect(screen.getByText("Déjelo vacío para quitar el frente de esta partida.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Poner el frente" }));
    await waitFor(() => expect(alAceptar).toHaveBeenCalledTimes(1));
    const edicion = fetchFalso.mock.calls.find(([, o]) => o?.method === "PUT")!;
    expect(String(edicion[0])).toBe(RUTA_EDICION);
    expect(JSON.parse(String(edicion[1]?.body))).toEqual({ rev: 3, filas: [{ clave: "VF-009|a-mano:1", frente: "Norte" }] });
    const tabla = screen.getByRole("table", { name: "Presupuesto por frente" });
    expect(within(within(tabla).getAllByRole("row")[1]!).getAllByRole("cell")[0]).toHaveTextContent("Norte");
  });

  // Ronda 1 del árbitro de la ola 2 (hallazgo 5): con el panel abierto, una cantidad editada o un renglón quitado en la
  // Hoja (otro `rev`) dejaban el «Total general» y los subtotales viejos mientras el «Total del presupuesto» ya cambiaba.
  const vistasPedidas = () => fetchFalso.mock.calls.filter(([r, o]) => String(r) === RUTA_VISTA && o?.method !== "PUT").length;

  test("con el panel abierto, otro rev de la Hoja vuelve a pedir la vista y muestra el total nuevo", async () => {
    const cambiarRev = montarConRev(3);
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    await screen.findByText("Total general: 4.701,13 Bs");
    fetchFalso.mockImplementation(async () =>
      json({ ...VISTA, rev: 5, total: { texto: "4801.13", exacto: "4801.126" } }),
    );
    cambiarRev(5);
    expect(await screen.findByText("Total general: 4.801,13 Bs")).toBeInTheDocument();
    expect(vistasPedidas()).toBe(2);
  });

  // T4 (mutante PF2): en el panel lateral, si la petición se cancela antes de responder (el modo estricto monta, desmonta y
  // vuelve a montar), la vista se vuelve a pedir en vez de quedarse sin subtotales.
  test("en el panel lateral la vista se pide de nuevo si la primera petición se canceló antes de responder", async () => {
    const valor = { alExpirar: vi.fn() } as unknown as Aplicacion;
    render(
      <StrictMode>
        <ContextoAplicacion.Provider value={valor}>
          <PresupuestoPorFrentes id={ID} rev={3} filas={FILAS} moneda="Bs" puedeEditar alAceptar={vi.fn()} alAusente={vi.fn()} enPanel />
        </ContextoAplicacion.Provider>
      </StrictMode>,
    );
    expect(await screen.findByText("Total general: 4.701,13 Bs")).toBeInTheDocument();
  });

  test("con el panel cerrado, otro rev no pide nada", async () => {
    const cambiarRev = montarConRev(3);
    cambiarRev(4);
    await new Promise((r) => setTimeout(r, 20));
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("tras poner un frente, el rev nuevo no vuelve a pedir la vista (ya vino con la respuesta)", async () => {
    const cambiarRev = montarConRev(3);
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    await screen.findByRole("table", { name: "Presupuesto por frente" });
    await usuario.type(screen.getByRole("textbox", { name: "Frente" }), "Norte");
    expect(screen.getByText("Déjelo vacío para quitar el frente de esta partida.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Poner el frente" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Frente" })).toHaveValue(""));
    cambiarRev(4);
    await new Promise((r) => setTimeout(r, 20));
    expect(vistasPedidas()).toBe(1);
  });

  test("quien solo lee ve los subtotales sin poder cambiar frentes", async () => {
    montar(false);
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    await screen.findByRole("table", { name: "Presupuesto por frente" });
    expect(screen.queryByRole("button", { name: "Poner el frente" })).toBeNull();
  });

  // Ronda 2 del árbitro de la ola 2 (R2-N1): una respuesta vieja de «Ver» o de «Poner el frente» que llega después de la
  // del `rev` nuevo no puede dejar la vista atrasada: solo se aplica la del último pedido.
  function diferida() {
    let soltar!: (r: Response) => void;
    const promesa = new Promise<Response>((r) => (soltar = r));
    return { promesa, soltar };
  }
  const NUEVA = { ...VISTA, rev: 5, total: { texto: "4801.13", exacto: "4801.126" } };

  test("la vista que se pidió al abrir y llega tarde no tapa la del rev nuevo", async () => {
    const vieja = diferida();
    fetchFalso.mockImplementationOnce(() => vieja.promesa);
    const cambiarRev = montarConRev(3);
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    fetchFalso.mockImplementation(async () => json(NUEVA));
    cambiarRev(5);
    expect(await screen.findByText("Total general: 4.801,13 Bs")).toBeInTheDocument();
    vieja.soltar(json(VISTA));
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByText("Total general: 4.701,13 Bs")).toBeNull();
    expect(screen.getByText("Total general: 4.801,13 Bs")).toBeInTheDocument();
  });

  test("la respuesta de «Poner el frente» que llega después de la del rev nuevo no la tapa", async () => {
    const alAceptar = vi.fn();
    const cambiarRev = montarConRev(3, alAceptar);
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    await screen.findByText("Total general: 4.701,13 Bs");
    const edicion = diferida();
    fetchFalso.mockImplementation(async (_ruta, opciones) => (opciones?.method === "PUT" ? edicion.promesa : json(NUEVA)));
    await usuario.type(screen.getByRole("textbox", { name: "Frente" }), "Norte");
    expect(screen.getByText("Déjelo vacío para quitar el frente de esta partida.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Poner el frente" }));
    cambiarRev(5);
    expect(await screen.findByText("Total general: 4.801,13 Bs")).toBeInTheDocument();
    edicion.soltar(
      json({
        rev: 4,
        resumen: { rev: 4, moneda: "Bs", total: VISTA.total, cambios: 0, pendientes_catalogo: 0 },
        frentes: {
          ...VISTA,
          rev: 4,
          frentes: [{ frente: "Norte", renglones: 1, pendientes: 0, total: { texto: "10.00", exacto: "10" } }],
          total: { texto: "10.00", exacto: "10" },
        },
      }),
    );
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Frente" })).toHaveValue(""));
    expect(screen.getByText("Total general: 4.801,13 Bs")).toBeInTheDocument();
    expect(alAceptar).not.toHaveBeenCalled();
  });

  // Árbitro, ronda 3 (R3-1): con «Poner el frente» en vuelo, «Ocultar» y «Ver» harían que la respuesta aceptada por el
  // servidor se tomara por vieja y la Hoja no se enterara del `rev` nuevo. Mientras el PUT viaja, el panel no se cierra.
  test("con «Poner el frente» en vuelo no se puede ocultar el panel, y su respuesta llega a la Hoja", async () => {
    const alAceptar = montar();
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    await screen.findByText("Total general: 4.701,13 Bs");
    const edicion = diferida();
    fetchFalso.mockImplementation(async (_ruta, opciones) => (opciones?.method === "PUT" ? edicion.promesa : json(VISTA)));
    await usuario.type(screen.getByRole("textbox", { name: "Frente" }), "Norte");
    expect(screen.getByText("Déjelo vacío para quitar el frente de esta partida.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Poner el frente" }));
    expect(screen.getByRole("button", { name: "Ocultar el presupuesto por frente" })).toBeDisabled();
    edicion.soltar(
      json({
        rev: 4,
        resumen: { rev: 4, moneda: "Bs", total: VISTA.total, cambios: 0, pendientes_catalogo: 0 },
        frentes: { ...VISTA, rev: 4 },
      }),
    );
    await waitFor(() => expect(alAceptar).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("button", { name: "Ocultar el presupuesto por frente" })).not.toBeDisabled();
  });

  // Pasada en navegador de la ola 2: D4, «póngalo abajo» sin nada abajo; D5, dos renglones con el mismo código no se
  // distinguían en el selector.
  const SIN_FRENTES = { ...VISTA, frentes: [{ frente: null, renglones: 2, pendientes: 0, total: VISTA.total }], con_frentes: false };
  function montarCon(filas: Array<(typeof FILAS)[number] & { frente?: string | null }>, puedeEditar = true) {
    const valor = { alExpirar: vi.fn() } as unknown as Aplicacion;
    render(
      <ContextoAplicacion.Provider value={valor}>
        <PresupuestoPorFrentes id={ID} rev={3} filas={filas} moneda="Bs" puedeEditar={puedeEditar} alAceptar={vi.fn()} alAusente={vi.fn()} />
      </ContextoAplicacion.Provider>,
    );
  }

  test("sin renglones propios no dice «póngalo abajo», porque abajo no hay nada", async () => {
    fetchFalso.mockImplementation(async () => json(SIN_FRENTES));
    montarCon(FILAS.map((f) => ({ ...f, quitable: false })));
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    await screen.findByRole("table", { name: "Presupuesto por frente" });
    expect(screen.queryByRole("combobox", { name: "Partida del presupuesto" })).toBeNull();
    expect(screen.queryByText(/selector de abajo/)).toBeNull();
    expect(screen.getByText(/Ninguna partida tiene frente de trabajo/)).toHaveTextContent(/salen del espacio de la obra/);
  });

  test("con renglones propios sí invita a ponerlo abajo", async () => {
    fetchFalso.mockImplementation(async () => json(SIN_FRENTES));
    montarCon(FILAS);
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    expect(await screen.findByText("Ninguna partida tiene frente de trabajo. Asígnelo con el selector de abajo o importe un Excel organizado por frentes.")).toBeInTheDocument();
  });

  test("quien solo lee no recibe la invitación a ponerlo abajo", async () => {
    fetchFalso.mockImplementation(async () => json(SIN_FRENTES));
    montarCon(FILAS, false);
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    await screen.findByRole("table", { name: "Presupuesto por frente" });
    expect(screen.queryByText(/selector de abajo/)).toBeNull();
    expect(screen.getByText("Ninguna partida tiene frente de trabajo.")).toBeInTheDocument();
  });

  test("el selector nombra el frente de cada renglón que lo tiene", async () => {
    montarCon([
      { clave: "VF-001|libro:FRENTE A!E4", partida: "VF-001", descripcion: "Riego ficticio", quitable: true, frente: "FRENTE A" },
      { clave: "VF-001|libro:FRENTE B!E4", partida: "VF-001", descripcion: "Riego ficticio", quitable: true, frente: "FRENTE B" },
      { clave: "VF-009|a-mano:1", partida: "VF-009", descripcion: "Señal ficticia", quitable: true, frente: null },
    ]);
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    const selector = await screen.findByRole("combobox", { name: "Partida del presupuesto" });
    expect(within(selector).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "1. VF-001 (FRENTE A) · Riego ficticio",
      "2. VF-001 (FRENTE B) · Riego ficticio",
      "3. VF-009 · Señal ficticia",
    ]);
  });

  test("si el renglón elegido deja de estar (se quitó en la Hoja), «Poner el frente» manda el que muestra el selector", async () => {
    const valor = { alExpirar: vi.fn() } as unknown as Aplicacion;
    const panel = (filas: typeof FILAS) => (
      <ContextoAplicacion.Provider value={valor}>
        <PresupuestoPorFrentes id={ID} rev={3} filas={filas} moneda="Bs" puedeEditar alAceptar={vi.fn()} alAusente={vi.fn()} />
      </ContextoAplicacion.Provider>
    );
    const { rerender } = render(panel(FILAS));
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    await usuario.selectOptions(await screen.findByRole("combobox", { name: "Partida del presupuesto" }), "VF-009|a-mano:1");
    // La Hoja quitó VF-009: el selector solo ofrece VF-001.
    rerender(panel([FILAS[0]!]));
    expect(screen.getByRole("combobox", { name: "Partida del presupuesto" })).toHaveValue("VF-001|libro:FRENTE A!E4");
    await usuario.type(screen.getByRole("textbox", { name: "Frente" }), "Norte");
    expect(screen.getByText("Déjelo vacío para quitar el frente de esta partida.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Poner el frente" }));
    await waitFor(() => expect(fetchFalso.mock.calls.some(([, o]) => o?.method === "PUT")).toBe(true));
    const edicion = fetchFalso.mock.calls.find(([, o]) => o?.method === "PUT")!;
    expect(JSON.parse(String(edicion[1]?.body))).toEqual({ rev: 3, filas: [{ clave: "VF-001|libro:FRENTE A!E4", frente: "Norte" }] });
  });

  test("poner el frente espera los envíos pendientes del borrador y manda el rev más alto que contestaron", async () => {
    const { registrarVaciador } = await import("./envioPendiente");
    const soltar = registrarVaciador(ID, () =>
      Promise.resolve({
        rev: 6,
        moneda: "Bs",
        total: VISTA.total,
        cambios: 1,
        pendientes_catalogo: 0,
        hallazgos: [],
        hay_plan: true,
        version_mas_nueva: null,
        guardado_como: null,
      }),
    );
    try {
      montar();
      await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
      await screen.findByRole("table", { name: "Presupuesto por frente" });
      await usuario.type(screen.getByRole("textbox", { name: "Frente" }), "Norte");
    expect(screen.getByText("Déjelo vacío para quitar el frente de esta partida.")).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Poner el frente" }));
      await waitFor(() => expect(fetchFalso.mock.calls.some(([, o]) => o?.method === "PUT")).toBe(true));
      const edicion = fetchFalso.mock.calls.find(([, o]) => o?.method === "PUT")!;
      expect(JSON.parse(String(edicion[1]?.body))).toEqual({ rev: 6, filas: [{ clave: "VF-001|libro:FRENTE A!E4", frente: "Norte" }] });
    } finally {
      soltar();
    }
  });
});
