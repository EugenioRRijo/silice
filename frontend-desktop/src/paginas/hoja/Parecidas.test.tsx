import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { Parecidas } from "./Parecidas";
import type { PartidaParecida } from "./Parecidas";

// Tarea 9 del plan F4: «Parecidas a esta descripción», la salida de «Agregar partida» que sustituye a la pantalla
// «Partidas similares» (baja 20). Usa la misma ruta y el mismo cuerpo que la pantalla (`POST /v1/similares`
// `{descripcion}`, `api/rutas/similares.py`) y su lista de propuestas, con un botón «Usar esta partida». Las propuestas
// son ficticias; los textos de la API, los de `aplicacion/similares.py`.

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

const ZANJA = {
  codigo: "FIC-01",
  descripcion: "Excavación de zanja ficticia a mano",
  puntaje: "0.9137",
  puntaje_corto: "0.91",
  aviso: null,
  composicion: {
    unidad: "m3",
    rendimiento: "8.00",
    materiales: [{ descripcion: "Arena ficticia", unidad: "m3", cantidad: "7.50", precio: "1500.00" }],
    equipos: [{ descripcion: "Pala ficticia", cantidad: "1.00", precio: "60.00", depreciacion: "1.00" }],
    mano_obra: [{ descripcion: "Ayudante", cantidad: "4.00", sueldo: "3.00" }],
  },
};
const INCOMPLETA = {
  codigo: "FIC-02",
  descripcion: "Zanja ficticia con entibado",
  puntaje: "0.6402",
  puntaje_corto: "0.64",
  composicion: null,
  aviso: "Desglose incompleto en la lista vigente: falta el precio de Arena ficticia.",
};

describe("Parecidas a esta descripción (Tarea 9)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let respuesta: () => Response | Promise<Response>;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    respuesta = () => json({ propuestas: [ZANJA, INCOMPLETA], falla: null, mensaje: null });
    fetchFalso.mockImplementation(async () => respuesta());
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(descripcion: string, alUsar = vi.fn<(p: PartidaParecida) => void>(), alExpirar = vi.fn()) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "VIV-80",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    const vista = render(
      <ContextoAplicacion.Provider value={valor}>
        <Parecidas descripcion={descripcion} alUsar={alUsar} />
      </ContextoAplicacion.Provider>,
    );
    const volverAPintar = (otra: string) =>
      vista.rerender(
        <ContextoAplicacion.Provider value={valor}>
          <Parecidas descripcion={otra} alUsar={alUsar} />
        </ContextoAplicacion.Provider>,
      );
    return { alUsar, alExpirar, volverAPintar };
  }

  test("con la descripción en blanco «Buscar parecidas» está deshabilitado y no se pide nada", () => {
    montar("   ");
    expect(screen.getByRole("button", { name: "Buscar parecidas" })).toBeDisabled();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("manda la descripción por POST a /v1/similares y lista las propuestas con su puntaje", async () => {
    montar("excavación de zanja");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    expect(await screen.findByRole("heading", { name: "2 propuestas, de mayor a menor similitud" })).toBeInTheDocument();
    const [ruta, opciones] = fetchFalso.mock.calls[0]!;
    expect(ruta).toBe("/v1/similares");
    expect(opciones?.method).toBe("POST");
    expect(JSON.parse(String(opciones?.body))).toEqual({ descripcion: "excavación de zanja" });
    const lista = screen.getByRole("list", { name: "Partidas parecidas" });
    // Solo las propuestas (el análisis plegado de cada una es otra lista, la del acordeón).
    const propuestas = within(lista).getAllByRole("listitem").filter((li) => li.parentElement === lista);
    expect(propuestas.map((li) => li.querySelector("p")?.textContent)).toEqual([
      "Puntaje 0,91 - FIC-01 - Excavación de zanja ficticia a mano",
      "Puntaje 0,64 - FIC-02 - Zanja ficticia con entibado",
    ]);
  });

  test("«Usar esta partida» entrega el código, la descripción y la unidad de la propuesta", async () => {
    const { alUsar } = montar("excavación de zanja");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    await userEvent.click(await screen.findByRole("button", { name: "Usar esta partida: FIC-01" }));
    expect(alUsar).toHaveBeenCalledTimes(1);
    expect(alUsar).toHaveBeenCalledWith({ codigo: "FIC-01", descripcion: "Excavación de zanja ficticia a mano", unidad: "m3" });
  });

  test("una propuesta sin desglose se usa igual, sin unidad", async () => {
    const { alUsar } = montar("zanja");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    await userEvent.click(await screen.findByRole("button", { name: "Usar esta partida: FIC-02" }));
    expect(alUsar).toHaveBeenCalledWith({ codigo: "FIC-02", descripcion: "Zanja ficticia con entibado", unidad: null });
  });

  test("el análisis de cada propuesta se ve plegado, con sus cifras en es-VE", async () => {
    montar("zanja");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    await userEvent.click(await screen.findByRole("button", { name: "Ver el análisis de FIC-01" }));
    expect(screen.getByText("Partida de origen: FIC-01 | puntaje de similitud: 0,9137")).toBeInTheDocument();
    expect(screen.getByText("8,00 m³/día", { exact: false })).toHaveTextContent("Unidad: m³ | Rendimiento: 8,00 m³/día");
    const materiales = screen.getByRole("table", { name: "Materiales" });
    expect(within(materiales).getByText("1.500,00")).toBeInTheDocument();
    expect(within(materiales).queryByText("1500.00")).toBeNull();
  });

  test("el desglose incompleto se avisa y no se muestra a medias", async () => {
    montar("zanja");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    await userEvent.click(await screen.findByRole("button", { name: "Ver el análisis de FIC-02" }));
    const aviso = screen.getByText(/Desglose incompleto en la lista vigente/);
    const detalle = aviso.closest(".silice-parecidas__detalle") as HTMLElement;
    expect(within(detalle).queryAllByRole("table")).toHaveLength(0);
  });

  test("si la descripción cambia después de buscar, dice qué se buscó", async () => {
    const { volverAPintar } = montar("zanja");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    await screen.findByRole("heading", { name: "2 propuestas, de mayor a menor similitud" });
    expect(screen.queryByText(/Resultados de:/)).toBeNull();
    volverAPintar("zanja profunda");
    expect(screen.getByText("Resultados de: “zanja”")).toBeInTheDocument();
  });

  test("nada sobre el umbral dice el mensaje de la API", async () => {
    respuesta = () => json({ propuestas: [], falla: null, mensaje: "Ninguna partida supera el umbral." });
    montar("algo raro");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    expect(await screen.findByText("Ninguna partida supera el umbral.")).toBeInTheDocument();
  });

  test("el modelo no disponible se dice como error, con su texto", async () => {
    respuesta = () => json({ propuestas: [], falla: "El modelo de similitud no está disponible.", mensaje: null });
    montar("algo");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    expect(await screen.findByText(/El modelo de similitud no está disponible/)).toBeInTheDocument();
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });

  // Menor 2 del árbitro de la Tarea 9 (cierre de F4): vuelve la de la pantalla «Partidas similares» (Similares.test.tsx:192).
  test("un error de la API muestra su detalle", async () => {
    respuesta = () => json({ detalle: "Su cuenta no tiene permiso para esta acción." }, 403);
    const { alExpirar } = montar("algo");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    expect(await screen.findByText("Su cuenta no tiene permiso para esta acción.")).toBeInTheDocument();
    expect(alExpirar).not.toHaveBeenCalled();
  });

  test("un 401 avisa a alExpirar", async () => {
    respuesta = () => json({ detalle: "Sesión ausente o vencida." }, 401);
    const { alExpirar } = montar("algo");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("mientras busca lo dice, y una respuesta vieja se descarta", async () => {
    const pendientes: ((r: Response) => void)[] = [];
    respuesta = () => new Promise<Response>((resolver) => pendientes.push(resolver));
    const { volverAPintar } = montar("primera");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    expect(await screen.findByText("Buscando partidas parecidas…")).toBeInTheDocument();
    volverAPintar("segunda");
    await userEvent.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    pendientes[1]!(json({ propuestas: [], falla: null, mensaje: "Respuesta de la segunda." }));
    expect(await screen.findByText("Respuesta de la segunda.")).toBeInTheDocument();
    pendientes[0]!(json({ propuestas: [], falla: null, mensaje: "Respuesta de la primera." }));
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByText("Respuesta de la primera.")).toBeNull();
  });
});
