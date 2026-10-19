import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaSimilares from "./index";
import type { Propuesta, SimilaresRespuesta } from "./logica";

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

const CONCRETO: Propuesta = {
  codigo: "FIC-01",
  descripcion: "Vaciado de concreto ficticio",
  puntaje: "0.9137",
  puntaje_corto: "0.91",
  aviso: null,
  composicion: {
    unidad: "m3",
    rendimiento: "8.00",
    materiales: [{ descripcion: "Cemento ficticio", unidad: "saco", cantidad: "7.50", precio: "15.00" }],
    equipos: [{ descripcion: "Mezcladora ficticia", cantidad: "1.00", precio: "60.00", depreciacion: "1.00" }],
    mano_obra: [{ descripcion: "Ayudante", cantidad: "4.00", sueldo: "3.00" }],
  },
};
const INCOMPLETA: Propuesta = {
  codigo: "FIC-02",
  descripcion: "Zanja ficticia",
  puntaje: "0.6402",
  puntaje_corto: "0.64",
  composicion: null,
  aviso: "Desglose incompleto en la lista vigente: falta el precio de Arena ficticia.",
};

describe("Partidas similares", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let respuesta: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    respuesta = () => json({ propuestas: [CONCRETO, INCOMPLETA], falla: null, mensaje: null } satisfies SimilaresRespuesta);
    fetchFalso.mockImplementation(async () => respuesta());
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
        <PaginaSimilares />
      </ContextoAplicacion.Provider>,
    );
    return alExpirar;
  }

  async function buscar(texto: string) {
    const usuario = userEvent.setup();
    await usuario.type(screen.getByLabelText("Descripción de la partida"), texto);
    await usuario.click(screen.getByRole("button", { name: "Buscar" }));
    return usuario;
  }

  test("al abrir pide una descripcion y no llama a la API", () => {
    montar();
    expect(screen.getByText("Escriba una descripción para buscar partidas similares.")).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("con la descripcion en blanco el boton Buscar esta deshabilitado y no se envia nada", async () => {
    montar();
    const usuario = userEvent.setup();
    expect(screen.getByRole("button", { name: "Buscar" })).toBeDisabled();
    await usuario.type(screen.getByLabelText("Descripción de la partida"), "   ");
    expect(screen.getByRole("button", { name: "Buscar" })).toBeDisabled();
    await usuario.type(screen.getByLabelText("Descripción de la partida"), "{Enter}");
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("el texto de ayuda no lleva jerga y la region de resultados esta siempre montada", () => {
    montar();
    expect(screen.getByText(/Sílice propone las más parecidas del catálogo/)).toBeInTheDocument();
    expect(screen.queryByText(/semántica|entrenamiento/)).toBeNull();
    const region = document.querySelector('[aria-live="polite"]');
    expect(region).not.toBeNull();
    expect(region?.getAttribute("aria-atomic")).toBe("true");
  });

  test("una sola propuesta dice «1 propuesta»", async () => {
    respuesta = () => json({ propuestas: [CONCRETO], falla: null, mensaje: null });
    montar();
    await buscar("concreto");
    expect(await screen.findByText("1 propuesta")).toBeInTheDocument();
  });

  test("si el texto cambia despues de buscar, avisa de que busco el anterior", async () => {
    montar();
    const usuario = await buscar("concreto");
    await screen.findByText("2 propuestas, de mayor a menor similitud");
    expect(screen.queryByText(/Resultados de:/)).toBeNull();
    await usuario.type(screen.getByLabelText("Descripción de la partida"), " armado");
    expect(screen.getByText("Resultados de: “concreto”")).toBeInTheDocument();
  });

  test("una respuesta vieja se descarta si ya se hizo otra busqueda", async () => {
    const pendientes: ((r: Response) => void)[] = [];
    fetchFalso.mockImplementation(() => new Promise<Response>((resolver) => pendientes.push(resolver)));
    montar();
    const usuario = await buscar("primera");
    await usuario.clear(screen.getByLabelText("Descripción de la partida"));
    await usuario.type(screen.getByLabelText("Descripción de la partida"), "segunda");
    await usuario.click(screen.getByRole("button", { name: "Buscar" }));
    expect(pendientes).toHaveLength(2);
    pendientes[1](json({ propuestas: [], falla: null, mensaje: "Respuesta de la segunda." }));
    expect(await screen.findByText("Respuesta de la segunda.")).toBeInTheDocument();
    pendientes[0](json({ propuestas: [], falla: null, mensaje: "Respuesta de la primera." }));
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByText("Respuesta de la primera.")).toBeNull();
    expect(screen.getByText("Respuesta de la segunda.")).toBeInTheDocument();
  });

  test("manda la descripcion por POST y lista las propuestas con titulo, origen y desglose", async () => {
    montar();
    const usuario = await buscar("concreto para paredes");
    expect(await screen.findByText("2 propuestas, de mayor a menor similitud")).toBeInTheDocument();
    const [ruta, opciones] = fetchFalso.mock.calls[0];
    expect(ruta).toBe("/v1/similares");
    expect(opciones?.method).toBe("POST");
    expect(JSON.parse(String(opciones?.body))).toEqual({ descripcion: "concreto para paredes" });

    await usuario.click(screen.getByRole("button", { name: /Puntajes*0.91 - FIC-01 - Vaciado de concreto ficticio/ }));
    expect(screen.getByText("Partida de origen: FIC-01 | puntaje de similitud: 0.9137")).toBeInTheDocument();
    expect(screen.getByText("Unidad:").tagName).toBe("STRONG");
    expect(screen.getByText("Rendimiento:").tagName).toBe("STRONG");
    expect(screen.getByText("8.00 m3/día", { exact: false })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Materiales" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Equipos" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Mano de obra" })).toBeInTheDocument();
    const materiales = screen.getByRole("table", { name: "Materiales" });
    expect(within(materiales).getByText("7.50")).toBeInTheDocument();
    expect(within(materiales).getByText("15.00")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Equipos" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Mano de obra" })).toBeInTheDocument();
  });

  test("el desglose incompleto se avisa y no se muestra a medias", async () => {
    montar();
    const usuario = await buscar("zanja");
    await usuario.click(await screen.findByRole("button", { name: /Puntajes*0.64 - FIC-02 - Zanja ficticia/ }));
    const aviso = screen.getByText(/Desglose incompleto en la lista vigente/);
    expect(aviso).toBeInTheDocument();
    const panel = aviso.closest(".silice-similares__detalle") as HTMLElement;
    expect(within(panel).queryAllByRole("table")).toHaveLength(0);
  });

  test("nada sobre el umbral muestra el mensaje de la API", async () => {
    respuesta = () => json({ propuestas: [], falla: null, mensaje: "Ninguna partida supera el umbral." });
    montar();
    await buscar("algo raro");
    expect(await screen.findByText("Ninguna partida supera el umbral.")).toBeInTheDocument();
  });

  test("el modelo no disponible se muestra como error con su texto, sin traza", async () => {
    respuesta = () =>
      json({ propuestas: [], falla: "El modelo de similitud no esta disponible: RuntimeError: x", mensaje: null });
    montar();
    await buscar("algo");
    expect(await screen.findByText(/El modelo de similitud no esta disponible/)).toBeInTheDocument();
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });

  test("un error de la API muestra su detalle", async () => {
    respuesta = () => json({ detalle: "Su cuenta no tiene permiso para esta acción." }, 403);
    montar();
    await buscar("algo");
    expect(await screen.findByText("Su cuenta no tiene permiso para esta acción.")).toBeInTheDocument();
  });

  test("un 401 avisa a alExpirar", async () => {
    respuesta = () => json({ detalle: "Sesión ausente o vencida." }, 401);
    const alExpirar = montar();
    await buscar("algo");
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("mientras busca muestra el estado de carga", async () => {
    let soltar: (r: Response) => void = () => undefined;
    fetchFalso.mockImplementation(() => new Promise<Response>((resolver) => (soltar = resolver)));
    montar();
    await buscar("algo");
    expect(await screen.findByRole("status", { name: /Buscando/ })).toBeInTheDocument();
    soltar(json({ propuestas: [], falla: null, mensaje: "Nada." }));
    expect(await screen.findByText("Nada.")).toBeInTheDocument();
  });
});
