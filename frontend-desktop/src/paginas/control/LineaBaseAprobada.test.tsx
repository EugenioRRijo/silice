import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { PestanaLineaBase } from "./PestanaLineaBase";
import type { LineaBase } from "./logica";

// Tarea 20: la aprobada manda en Control de obra. «Declarar una línea base» propone la última versión aprobada (la del
// último dictamen que aprobó, de `GET /v1/aprobaciones?proyecto=`, Tarea 18) y avisa si se elige una que no lo está.
// Archivo propio (no Control.test.tsx) para no pisar a otras tareas que editan Control a la vez. Datos ficticios.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["control_de_obra", "editar_hoja"],
  modo_entrega: false,
};

const SIN_LINEA_BASE: LineaBase = {
  tiene_linea_base: false,
  descripcion: null,
  versiones: ["VIV-003", "VIV-002", "VIV-001"],
  hay_valuaciones: false,
  parametros: [],
};

const evento = (id: number, tipo: string, version: string, resultado: string | null, cierre_de: number | null) => ({
  id,
  tipo,
  version,
  resultado,
  notas: resultado === "devuelta" ? "Corregir." : "",
  por: tipo === "dictamen" ? "Rita Gómez <rita>" : "Ana Pérez <ana>",
  el: `2026-10-2${id}T09:00:00`,
  armo: false,
  cierre_de,
});

// VIV-001 devuelta y VIV-002 aprobada; VIV-003 solo guardada.
const APROBACIONES = {
  rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
  fases: "VIV-001 devuelta → VIV-002 aprobada",
  versiones: {
    "VIV-001": { estado: "devuelta", por: "Rita Gómez <rita>", el: "2026-10-22T09:00:00", notas: "Corregir.", armo: false },
    "VIV-002": { estado: "aprobada", por: "Rita Gómez <rita>", el: "2026-10-24T09:00:00", notas: "", armo: false },
    "VIV-003": { estado: "guardada", por: null, el: null, notas: "", armo: false },
  },
  eventos: [evento(1, "envio", "VIV-001", null, null), evento(2, "dictamen", "VIV-001", "devuelta", 1), evento(3, "envio", "VIV-002", null, null), evento(4, "dictamen", "VIV-002", "aprobada", 3)],
};

const fetchFalso = vi.fn<typeof fetch>();
let aprobaciones: () => Response;

beforeEach(() => {
  fijarCsrf("tok");
  vi.stubGlobal("fetch", fetchFalso);
  fetchFalso.mockReset();
  aprobaciones = () => json(APROBACIONES);
  fetchFalso.mockImplementation(async (entrada, init) => {
    const url = new URL(String(entrada), "http://x");
    const metodo = init?.method ?? "GET";
    if (url.pathname === "/v1/control/linea-base" && metodo === "GET") return json(SIN_LINEA_BASE);
    if (url.pathname === "/v1/aprobaciones" && metodo === "GET") return aprobaciones();
    if (url.pathname === "/v1/control/linea-base" && metodo === "POST") return json({ ok: true }, 201);
    return json({ detalle: "No encontrado." }, 404);
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

function montar(acciones: string[] = SESION.acciones) {
  const aplicacion: Aplicacion = {
    sesion: { ...SESION, acciones },
    proyecto: "5",
    caso: null,
    recargarProyectos: vi.fn(),
    alExpirar: vi.fn(),
  };
  return render(
    <ContextoAplicacion.Provider value={aplicacion}>
      <PestanaLineaBase proyecto="5" clave={0} alCambiar={vi.fn()} />
    </ContextoAplicacion.Provider>,
  );
}

const version = () => screen.findByLabelText("Versión del contrato");

describe("la aprobada manda en la línea base", () => {
  test("propone la última aprobada (VIV-002), no la más nueva, y lo dice", async () => {
    montar();
    expect(await version()).toHaveValue("VIV-002");
    expect(screen.getByText("Se propone VIV-002, la última versión aprobada.")).toBeInTheDocument();
    expect(fetchFalso.mock.calls.map(([e]) => String(e))).toContain("/v1/aprobaciones?proyecto=5");
  });

  test("cada versión dice su estado en la lista", async () => {
    montar();
    const opciones = Array.from(((await version()) as HTMLSelectElement).options).map((o) => o.textContent);
    expect(opciones).toEqual(["VIV-003 · Guardada", "VIV-002 · Aprobada", "VIV-001 · Devuelta"]);
  });

  test("elegir una no aprobada avisa «Esta versión no está aprobada.» y deja declararla igual", async () => {
    const u = userEvent.setup();
    montar();
    await u.selectOptions(await version(), "VIV-001");
    expect(await screen.findByText("Esta versión no está aprobada.")).toBeInTheDocument();
    await u.type(screen.getByLabelText("Vigente desde"), "2026-11-02");
    await u.click(screen.getByRole("button", { name: "Declarar línea base" }));
    await waitFor(() => {
      const post = fetchFalso.mock.calls.find(([e, init]) => String(e) === "/v1/control/linea-base" && init?.method === "POST");
      expect(JSON.parse(String(post?.[1]?.body))).toMatchObject({ proyecto: "5", version: "VIV-001" });
    });
  });

  test("declarar no pinta un aviso verde: lo dice en texto neutro", async () => {
    const u = userEvent.setup();
    montar();
    await version();
    await u.click(screen.getByRole("button", { name: "Declarar línea base" }));
    expect(await screen.findByText("Línea base declarada.")).toBeInTheDocument();
    expect(document.querySelector(".cds--inline-notification--success")).toBeNull();
  });

  test("sin ninguna aprobada propone la más nueva y avisa que no está aprobada", async () => {
    aprobaciones = () =>
      json({ ...APROBACIONES, fases: "", eventos: [], versiones: { "VIV-003": { estado: "guardada", por: null, el: null, notas: "", armo: false } } });
    montar();
    expect(await version()).toHaveValue("VIV-003");
    expect(await screen.findByText("Esta versión no está aprobada.")).toBeInTheDocument();
  });

  test("sin `editar_hoja` no pide las aprobaciones y propone la más nueva, sin avisos", async () => {
    montar(["control_de_obra"]);
    expect(await version()).toHaveValue("VIV-003");
    expect(fetchFalso.mock.calls.map(([e]) => String(e)).some((u) => u.startsWith("/v1/aprobaciones"))).toBe(false);
    expect(screen.queryByText("Esta versión no está aprobada.")).toBeNull();
  });

  test("si las aprobaciones no se pueden leer, propone la más nueva sin avisos", async () => {
    aprobaciones = () => json({ detalle: "Falla." }, 503);
    montar();
    expect(await version()).toHaveValue("VIV-003");
    expect(screen.queryByText("Esta versión no está aprobada.")).toBeNull();
  });
});
