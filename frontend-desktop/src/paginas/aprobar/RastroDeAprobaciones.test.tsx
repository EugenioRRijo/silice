import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { trazabilidadRespuesta } from "../hoja/datosDePrueba";
import { PestanaTrazabilidad } from "../versiones/RegistroDeCambios";

// Tarea 20: la pestaña «Trazabilidad» de la Hoja muestra las fases de aprobación de la obra («VIV-001 devuelta → VIV-002
// aprobada»), si su rastro está íntegro y cada movimiento (quién, cuándo, versión, desenlace y notas), leídos de
// `GET /v1/aprobaciones?proyecto=` (Tarea 18). Datos ficticios.

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

const evento = (id: number, tipo: string, version: string, resultado: string | null, notas = "", armo = false) => ({
  id,
  tipo,
  version,
  resultado,
  notas,
  por: tipo === "dictamen" ? "Rita Gómez <rita>" : "Ana Pérez <ana>",
  el: `2026-10-2${id}T09:30:00`,
  armo,
  cierre_de: tipo === "envio" ? null : id - 1,
});

const APROBACIONES = {
  rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
  fases: "VIV-001 devuelta → VIV-002 aprobada",
  versiones: {},
  eventos: [
    evento(1, "envio", "VIV-001", null, "Primera entrega."),
    evento(2, "dictamen", "VIV-001", "devuelta", "Falta el acero."),
    evento(3, "envio", "VIV-002", null),
    evento(4, "dictamen", "VIV-002", "aprobada", "", true),
  ],
};

const fetchFalso = vi.fn<typeof fetch>();
let aprobaciones: () => Response;

beforeEach(() => {
  vi.stubGlobal("fetch", fetchFalso);
  fetchFalso.mockReset();
  aprobaciones = () => json(APROBACIONES);
  fetchFalso.mockImplementation(async (entrada) => {
    const url = new URL(String(entrada), "http://x");
    if (url.pathname === "/v1/hoja/trazabilidad") return json(trazabilidadRespuesta());
    if (url.pathname === "/v1/hoja/cadena") return json({ integra: true, mensaje: "Cadena íntegra." });
    if (url.pathname === "/v1/aprobaciones") return aprobaciones();
    return json({ detalle: "No encontrado." }, 404);
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function montar() {
  const aplicacion: Aplicacion = { sesion: SESION, proyecto: "OF-001", caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
  return render(
    <ContextoAplicacion.Provider value={aplicacion}>
      <PestanaTrazabilidad proyecto="OF-001" version="002" alAusente={vi.fn()} cambios={0} alCrearVersion={vi.fn()} />
    </ContextoAplicacion.Provider>,
  );
}

describe("Trazabilidad: las aprobaciones de la obra", () => {
  test("las fases y el rastro íntegro, con ícono y texto", async () => {
    montar();
    const region = await screen.findByRole("region", { name: "Aprobaciones" });
    expect(await within(region).findByText("VIV-001 devuelta → VIV-002 aprobada")).toBeInTheDocument();
    expect(within(region).getByText("Rastro de aprobaciones íntegro.")).toBeInTheDocument();
    expect(region.querySelector("svg")).not.toBeNull(); // el color nunca va solo
    expect(fetchFalso.mock.calls.map(([e]) => String(e))).toContain("/v1/aprobaciones?proyecto=OF-001");
  });

  test("cada movimiento con quién, cuándo, desenlace y notas; el dictamen de quien la armó lo dice", async () => {
    montar();
    const tabla = await screen.findByRole("table", { name: "Movimientos de aprobación" });
    const filas = within(tabla).getAllByRole("row").slice(1).map((f) => Array.from(f.querySelectorAll("td")).map((c) => c.textContent));
    expect(filas).toEqual([
      ["Envío", "VIV-001", "En aprobación", "Ana Pérez", "21/10/2026 09:30", "Primera entrega."],
      ["Dictamen", "VIV-001", "Devuelta", "Rita Gómez", "22/10/2026 09:30", "Falta el acero."],
      ["Envío", "VIV-002", "En aprobación", "Ana Pérez", "23/10/2026 09:30", ""],
      ["Dictamen", "VIV-002", "Aprobada · por quien la armó", "Rita Gómez", "24/10/2026 09:30", ""],
    ]);
  });

  test("un rastro roto se dice con su mensaje", async () => {
    aprobaciones = () => json({ ...APROBACIONES, rastro: { integro: false, mensaje: "El rastro de aprobaciones se rompió en el evento n.º 2." } });
    montar();
    const region = await screen.findByRole("region", { name: "Aprobaciones" });
    expect(await within(region).findByText("El rastro de aprobaciones se rompió en el evento n.º 2.")).toBeInTheDocument();
  });

  test("una obra que no envió versiones lo dice", async () => {
    aprobaciones = () => json({ rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." }, fases: "", versiones: {}, eventos: [] });
    montar();
    const region = await screen.findByRole("region", { name: "Aprobaciones" });
    expect(await within(region).findByText("Esta obra todavía no envió versiones a aprobación.")).toBeInTheDocument();
    expect(within(region).queryByRole("table")).toBeNull();
  });

  test("un 403 no dice nada y el resto de la pestaña sigue", async () => {
    aprobaciones = () => json({ detalle: "Su cuenta no puede hacer esto." }, 403);
    montar();
    await screen.findByRole("table", { name: "Versiones del proyecto" });
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByRole("region", { name: "Aprobaciones" })).toBeNull();
  });

  test("un fallo del servidor se dice sin romper la pestaña", async () => {
    aprobaciones = () => json({ detalle: "Falla." }, 503);
    montar();
    const region = await screen.findByRole("region", { name: "Aprobaciones" });
    expect(await within(region).findByText("No se pudo leer el rastro de aprobaciones")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Versiones del proyecto" })).toBeInTheDocument();
  });
});
