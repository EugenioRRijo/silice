import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import type { CarpetaRespuesta } from "../api/tipos";
import { ListaDeLaCarpeta } from "./ListaDeLaCarpeta";
import { estadoInicial, montarMarco, servidorFalso, sesionDe } from "./obras/datosDePrueba";

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

  test("una lista derivada que ya trae su fecha en el nombre no la repite", async () => {
    con({
      moneda: "Bs",
      declarada: true,
      lista: { nombre: "MaPreX ficticio en Bs al 25/10/2026", moneda: "Bs", fecha: "2026-10-25", origen: "derivada" },
      aviso: null,
    });
    render(<ListaDeLaCarpeta alExpirar={vi.fn()} />);
    expect(
      await screen.findByText("Moneda de trabajo: Bs · Lista para armar: MaPreX ficticio en Bs al 25/10/2026"),
    ).toBeInTheDocument();
  });

  test("tampoco la repite con el número de la del mismo día, y sí la dice si el nombre trae otra fecha", async () => {
    con({
      moneda: "Bs",
      declarada: true,
      lista: { nombre: "MaPreX ficticio en Bs al 25/10/2026 (2)", moneda: "Bs", fecha: "2026-10-25", origen: "derivada" },
      aviso: null,
    });
    const { unmount } = render(<ListaDeLaCarpeta alExpirar={vi.fn()} />);
    expect(
      await screen.findByText("Moneda de trabajo: Bs · Lista para armar: MaPreX ficticio en Bs al 25/10/2026 (2)"),
    ).toBeInTheDocument();
    unmount();
    con({
      moneda: "Bs",
      declarada: true,
      lista: { nombre: "Base ficticia al 01/07/2026", moneda: "Bs", fecha: "2026-10-25", origen: "prueba" },
      aviso: null,
    });
    render(<ListaDeLaCarpeta alExpirar={vi.fn()} />);
    expect(
      await screen.findByText("Moneda de trabajo: Bs · Lista para armar: Base ficticia al 01/07/2026, al 25/10/2026"),
    ).toBeInTheDocument();
  });

  test("con la vigente en otra moneda dice el aviso, no «Lista para armar»", async () => {
    // El sentido de `lista` desde T4: la vigente aunque esté en otra moneda; el aviso lo dice.
    const AVISO = "La lista vigente «Base ficticia» está en USD y la carpeta trabaja en Bs: conviértala antes de armar.";
    con({
      moneda: "Bs",
      declarada: true,
      lista: { nombre: "Base ficticia", moneda: "USD", fecha: "2026-07-01", origen: "prueba" },
      aviso: AVISO,
    });
    render(<ListaDeLaCarpeta alExpirar={vi.fn()} />);
    expect(await screen.findByText(`Moneda de trabajo: Bs · ${AVISO}`)).toBeInTheDocument();
    expect(screen.queryByText(/Lista para armar:/)).not.toBeInTheDocument();
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

// El marco la monta en la cabecera de la obra abierta (Tarea 8 del plan del marco).
describe("La lista de la carpeta en la cabecera de la obra", () => {
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

  test("va en la cabecera de la obra y se lee al entrar en ella", async () => {
    montarMarco(sesionDe("ana"), "/obra/empresa/7/presupuesto");
    await screen.findByRole("heading", { level: 1, name: "Hoja de la obra" });
    const cabecera = screen.getByRole("region", { name: "Obra abierta" });
    expect(
      await within(cabecera).findByText("Moneda de trabajo: Bs · Lista para armar: Lista ficticia de Bs, al 25/10/2026"),
    ).toBeInTheDocument();
    expect(servidor.de("GET", "/v1/carpeta").length).toBeGreaterThan(0);
  });
});
