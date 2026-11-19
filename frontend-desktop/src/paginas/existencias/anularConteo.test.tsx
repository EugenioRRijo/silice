import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import PaginaExistencias from "./index";
import { crearServidor, json } from "./servidorFalso";
import type { ServidorFalso } from "./servidorFalso";

// «Anular conteo» en Existencias (tanda 2026-11-19): un conteo fisico mal hecho se anula con un motivo y no se borra.
// En el servidor falso, ARE-01 tiene su ultimo conteo del 10/10/2026 (n.º 41, ajuste -2,5); los otros, ninguno.

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["operar_arenera"],
  modo_entrega: false,
};

const EXISTENCIAS = "/v1/produccion/existencias";
const ANULAR = "/v1/produccion/conteos/41/anular";
const BOTON = "Anular el conteo de Arena lavada del 10/10/2026";

describe("Anular un conteo físico", () => {
  let servidor: ServidorFalso;
  let alExpirar: ReturnType<typeof vi.fn<() => void>>;
  let usuario: ReturnType<typeof userEvent.setup>;

  async function montar() {
    render(
      <ContextoAplicacion.Provider value={{ sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar }}>
        <MemoryRouter>
          <PaginaExistencias />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
    await screen.findByText("Arena lavada");
  }

  const filaDe = (codigo: string) => screen.getByRole("row", { name: new RegExp(codigo) });

  async function abrirDialogo() {
    await montar();
    await usuario.click(screen.getByRole("button", { name: BOTON }));
    return screen.getByRole("dialog", { name: "Anular un conteo físico" });
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 18, 10, 0, 0));
    servidor = crearServidor();
    vi.stubGlobal("fetch", servidor.fetchFalso);
    fijarCsrf("tok");
    alExpirar = vi.fn();
    usuario = userEvent.setup();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("cada material dice su último conteo; solo el que tiene uno ofrece anularlo", async () => {
    await montar();
    const tabla = screen.getByRole("table", { name: "Existencias por material" });
    expect(within(tabla).getByRole("columnheader", { name: /Último conteo/ })).toBeInTheDocument();
    expect(within(filaDe("ARE-01")).getByRole("cell", { name: "10/10/2026" })).toBeInTheDocument();
    expect(within(filaDe("ARE-01")).getByRole("button", { name: BOTON })).toHaveTextContent("Anular conteo");
    expect(within(filaDe("PIE-01")).getByRole("cell", { name: "Sin conteo" })).toBeInTheDocument();
    expect(within(filaDe("PIE-01")).queryByRole("button")).not.toBeInTheDocument();
    expect(within(filaDe("GRA-01")).queryByRole("button")).not.toBeInTheDocument();
  });

  test("el diálogo dice qué se anula y que no se borra, con el foco en el motivo", async () => {
    const dialogo = await abrirDialogo();
    expect(dialogo).toHaveTextContent("Conteo físico de Arena lavada del 10/10/2026, con un ajuste de -2,5 m³.");
    expect(dialogo).toHaveTextContent("Anular no lo borra");
    expect(within(dialogo).getByLabelText("Motivo de la anulación")).toHaveFocus();
  });

  test("sin motivo no llama a la API y lo pide", async () => {
    const dialogo = await abrirDialogo();
    await usuario.click(within(dialogo).getByRole("button", { name: "Anular conteo" }));
    expect(within(dialogo).getByText("Escriba el motivo de la anulación.")).toBeInTheDocument();
    expect(servidor.de("POST", ANULAR)).toHaveLength(0);
  });

  test("anula con el motivo, cierra el diálogo, avisa y vuelve a pedir la existencia", async () => {
    const dialogo = await abrirDialogo();
    const pedidasAntes = servidor.de("GET", EXISTENCIAS).length;
    await usuario.type(within(dialogo).getByLabelText("Motivo de la anulación"), "  Se contó la pila de otra planta.  ");
    await usuario.click(within(dialogo).getByRole("button", { name: "Anular conteo" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(servidor.de("POST", ANULAR).map((l) => l.cuerpo)).toEqual([{ motivo: "Se contó la pila de otra planta." }]);
    expect(screen.getByText(/Conteo anulado/)).toBeInTheDocument();
    await waitFor(() => expect(servidor.de("GET", EXISTENCIAS).length).toBeGreaterThan(pedidasAntes));
  });

  test("si la API lo rechaza muestra su detalle en el diálogo, que sigue abierto", async () => {
    servidor.responder(`POST ${ANULAR}`, () =>
      json({ detalle: "Solo se puede anular el último conteo vigente de ARE-01, que es el del 12/10/2026: anule primero ese." }, 409),
    );
    const dialogo = await abrirDialogo();
    await usuario.type(within(dialogo).getByLabelText("Motivo de la anulación"), "mal contado");
    await usuario.click(within(dialogo).getByRole("button", { name: "Anular conteo" }));
    expect(await within(dialogo).findByRole("alert")).toHaveTextContent("anule primero ese");
    expect(screen.getByRole("dialog", { name: "Anular un conteo físico" })).toBeInTheDocument();
  });

  test("con la sesión vencida avisa a la aplicación", async () => {
    servidor.responder(`POST ${ANULAR}`, () => json({ detalle: "Sesión ausente o vencida." }, 401));
    const dialogo = await abrirDialogo();
    await usuario.type(within(dialogo).getByLabelText("Motivo de la anulación"), "mal contado");
    await usuario.click(within(dialogo).getByRole("button", { name: "Anular conteo" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("Cancelar cierra sin anular", async () => {
    const dialogo = await abrirDialogo();
    await usuario.click(within(dialogo).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(servidor.de("POST", ANULAR)).toHaveLength(0);
  });
});
