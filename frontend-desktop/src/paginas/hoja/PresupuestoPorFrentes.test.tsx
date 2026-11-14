import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
function montarConRev(rev: number) {
  const valor = { alExpirar: vi.fn() } as unknown as Aplicacion;
  const panel = (r: number) => (
    <ContextoAplicacion.Provider value={valor}>
      <PresupuestoPorFrentes id={ID} rev={r} filas={FILAS} moneda="Bs" puedeEditar alAceptar={vi.fn()} alAusente={vi.fn()} />
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
      ["Sin frente", "1", "10,00"],
    ]);
    expect(screen.getByText("Total general: 4.701,13 Bs")).toBeInTheDocument();
  });

  test("pone el frente de un renglón y muestra lo que devuelve el servidor", async () => {
    const alAceptar = montar();
    await usuario.click(screen.getByRole("button", { name: "Ver el presupuesto por frente" }));
    await screen.findByRole("table", { name: "Presupuesto por frente" });
    await usuario.selectOptions(screen.getByRole("combobox", { name: "Renglón" }), "VF-009|a-mano:1");
    await usuario.type(screen.getByRole("textbox", { name: "Frente" }), "Norte");
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
});
