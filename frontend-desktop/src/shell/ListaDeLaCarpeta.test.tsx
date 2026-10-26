import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import type { CarpetaRespuesta } from "../api/tipos";
import { ListaDeLaCarpeta } from "./ListaDeLaCarpeta";
import { botonDeObra, estadoInicial, montarShell, servidorFalso, sesionDe } from "./obras/datosDePrueba";

// Plan de montar un presupuesto, Tarea 4: al pie del selector de obra, bajo «Carpeta: … · Cambiar carpeta…», la
// moneda de trabajo de la carpeta y su lista para armar (`GET /v1/carpeta`, T2). Datos ficticios; textos del plan.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SIN_LISTA =
  "Esta carpeta de trabajo no tiene lista de precios para armar. Créela a partir de MaPreX o convirtiendo la que tiene.";

describe("La lista de la carpeta de trabajo", () => {
  let respuesta: () => Response;
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async (entrada) =>
      String(entrada) === "/v1/carpeta" ? respuesta() : json({ detalle: "No encontrado." }, 404),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  function con(carpeta: CarpetaRespuesta) {
    respuesta = () => json(carpeta);
  }

  test("dice la moneda de trabajo y la lista para armar con su fecha en dd/mm/aaaa", async () => {
    con({
      moneda: "Bs",
      declarada: true,
      lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-25", origen: "prueba" },
      aviso: null,
    });
    render(<ListaDeLaCarpeta alExpirar={vi.fn()} />);
    expect(
      await screen.findByText("Moneda de trabajo: Bs · Lista para armar: Lista ficticia de Bs, al 25/10/2026"),
    ).toBeInTheDocument();
    expect(fetchFalso).toHaveBeenCalledTimes(1);
  });

  test("sin moneda dice «Carpeta sin moneda declarada»", async () => {
    con({ moneda: null, declarada: false, lista: null, aviso: SIN_LISTA });
    render(<ListaDeLaCarpeta alExpirar={vi.fn()} />);
    expect(await screen.findByText("Carpeta sin moneda declarada")).toBeInTheDocument();
  });

  test("con moneda y sin lista para armar dice el aviso de la carpeta", async () => {
    con({ moneda: "USD", declarada: true, lista: null, aviso: SIN_LISTA });
    render(<ListaDeLaCarpeta alExpirar={vi.fn()} />);
    expect(await screen.findByText(`Moneda de trabajo: USD · ${SIN_LISTA}`)).toBeInTheDocument();
  });

  test("ninguna cadena visible dice «caso»", async () => {
    con({ moneda: "Bs", declarada: true, lista: null, aviso: SIN_LISTA });
    const { container } = render(<ListaDeLaCarpeta alExpirar={vi.fn()} />);
    await screen.findByText(/Moneda de trabajo/);
    expect(container.textContent).not.toMatch(/caso/i);
  });

  test("un 401 cierra la sesión", async () => {
    respuesta = () => json({ detalle: "Sesión vencida." }, 401);
    const alExpirar = vi.fn();
    render(<ListaDeLaCarpeta alExpirar={alExpirar} />);
    await waitFor(() => expect(alExpirar).toHaveBeenCalledTimes(1));
  });

  test("otro error lo dice en llano, sin inventar la moneda", async () => {
    respuesta = () => json({ detalle: "Falla ficticia." }, 500);
    render(<ListaDeLaCarpeta alExpirar={vi.fn()} />);
    expect(await screen.findByText("No se pudo leer la moneda de trabajo de la carpeta.")).toBeInTheDocument();
    expect(screen.queryByText(/Moneda de trabajo:/)).not.toBeInTheDocument();
  });
});

// El armazon la monta en el hueco `pie` del selector de obra (plan de montar, cambios por el diseno de modulos, T4).
describe("La lista de la carpeta en el selector de obra", () => {
  const CON_LISTA: CarpetaRespuesta = {
    moneda: "Bs",
    declarada: true,
    lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-25", origen: "prueba" },
    aviso: null,
  };
  let servidor: ReturnType<typeof servidorFalso>;

  beforeEach(() => {
    servidor = servidorFalso(estadoInicial(), (metodo, ruta) =>
      metodo === "GET" && ruta === "/v1/carpeta" ? json(CON_LISTA) : undefined,
    );
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    fijarCsrf("tok");
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("va al pie del panel, bajo «Carpeta: … · Cambiar carpeta…», y se lee cada vez que se abre", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    const antes = servidor.de("GET", "/v1/carpeta").length;
    await u.click(await botonDeObra());
    const panel = screen.getByRole("region", { name: "Obra" });
    const linea = await within(panel).findByText(
      "Moneda de trabajo: Bs · Lista para armar: Lista ficticia de Bs, al 25/10/2026",
    );
    const carpeta = within(panel).getByText("Carpeta: silice");
    expect(carpeta.compareDocumentPosition(linea) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(within(panel).getByRole("button", { name: "Cambiar carpeta…" })).toBeInTheDocument();
    expect(servidor.de("GET", "/v1/carpeta").length).toBe(antes + 1);

    // Cerrado y abierto otra vez, la vuelve a pedir (pudo crearse la lista en Componer entretanto).
    await u.keyboard("{Escape}");
    await u.click(await botonDeObra());
    await within(screen.getByRole("region", { name: "Obra" })).findByText(/^Moneda de trabajo: Bs/);
    expect(servidor.de("GET", "/v1/carpeta").length).toBe(antes + 2);
  });
});
