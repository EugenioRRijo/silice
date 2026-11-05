import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import { useBorrador } from "../paginas/hoja/useBorrador";
import { sesionDe } from "../shell/obras/datosDePrueba";
import { useSesion } from "./useSesion";

// Plan F6, T6 (foco 4 de la revisión): salir con un borrador de la Hoja abierto pedía `DELETE /v1/hoja/borradores/{id}`
// DESPUÉS de `DELETE /v1/sesion`: la cookie ya no valía y el servidor contestaba 401 (visto en vivo el 2026-11-04). El
// servidor ya descarta los borradores de la sesión al cerrarla (api/caso_web.py:43-46), así que no hay nada que pedir.
// El `fetch` simulado anota el orden de las llamadas y contesta 401 a todo lo que llegue sin sesión, como el servidor.

const ID = "b-ficticio-1";
const BORRADOR = {
  id: ID,
  resumen: { cambios: 0, rev: 1, total: "0" },
  base: { version: "001", vigente: "001" },
  instantanea: { creadas: 0, mensaje: null },
};

let llamadas: string[];
let haySesion: boolean;

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

beforeEach(() => {
  llamadas = [];
  haySesion = true;
  fijarCsrf("tok");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (entrada: RequestInfo | URL, init?: RequestInit) => {
      const metodo = init?.method ?? "GET";
      const ruta = String(entrada);
      llamadas.push(`${metodo} ${ruta}`);
      if (metodo === "DELETE" && ruta === "/v1/sesion") {
        haySesion = false;
        return new Response(null, { status: 204 });
      }
      if (metodo === "POST" && ruta === "/v1/sesion") {
        haySesion = true;
        return json(sesionDe("ana"), 201);
      }
      if (!haySesion && ruta !== "/v1/sesion") return json({ detalle: "Sin sesión." }, 401);
      if (metodo === "GET" && ruta === "/v1/sesion") return json(sesionDe("ana"));
      if (metodo === "POST" && ruta === "/v1/hoja/borradores") return json(BORRADOR, 201);
      if (metodo === "DELETE" && ruta === `/v1/hoja/borradores/${ID}`) return new Response(null, { status: 204 });
      return json({ detalle: "No encontrado." }, 404);
    }),
  );
});
afterEach(() => {
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

// Estable entre dibujos: `useBorrador` reabre el borrador si cambia.
const SIN_EFECTO = () => undefined;

function Borrador() {
  const { estado } = useBorrador("7", "001", SIN_EFECTO);
  return <p>{`borrador: ${estado.estado}`}</p>;
}

// Una sesión con la Hoja abierta, y un botón para cerrar solo la Hoja (irse de la pantalla sin salir de la sesión).
function Arnes() {
  const { estado, entrar, salir, expirar } = useSesion();
  const [hoja, setHoja] = useState(true);
  if (estado.tipo !== "activa") {
    return (
      <>
        <p>{`sesión: ${estado.tipo}`}</p>
        <button type="button" onClick={() => void entrar("ana", "una clave ficticia")}>
          Entrar
        </button>
      </>
    );
  }
  return (
    <>
      {hoja && <Borrador />}
      <button type="button" onClick={() => setHoja(false)}>
        Cerrar la Hoja
      </button>
      <button type="button" onClick={() => void salir()}>
        Salir
      </button>
      <button type="button" onClick={expirar}>
        Vencer
      </button>
    </>
  );
}

const descartes = () => llamadas.filter((l) => l === `DELETE /v1/hoja/borradores/${ID}`);

async function conLaHojaAbierta() {
  render(<Arnes />);
  await screen.findByText("borrador: listo");
}

describe("salir de la sesión con un borrador de la Hoja abierto", () => {
  test("control: irse de la Hoja sin salir de la sesión sí descarta el borrador sin cambios", async () => {
    const u = userEvent.setup();
    await conLaHojaAbierta();
    await u.click(screen.getByRole("button", { name: "Cerrar la Hoja" }));
    await waitFor(() => expect(descartes()).toHaveLength(1));
  });

  test("ningún DELETE del borrador llega después de DELETE /v1/sesion", async () => {
    const u = userEvent.setup();
    await conLaHojaAbierta();
    await u.click(screen.getByRole("button", { name: "Salir" }));
    await screen.findByText("sesión: sin_sesion");
    // Los descartes del desmontaje esperan un turno y las ediciones pendientes: se les da tiempo de sobra.
    await act(async () => {
      await new Promise((r) => setTimeout(r, 80));
    });
    const salida = llamadas.indexOf("DELETE /v1/sesion");
    expect(salida).toBeGreaterThan(-1);
    expect(llamadas.slice(salida + 1)).toEqual([]);
    expect(descartes()).toHaveLength(0);
  });

  test("la sesión vencida tampoco pide descartar el borrador: ya no hay sesión con que pedirlo", async () => {
    const u = userEvent.setup();
    await conLaHojaAbierta();
    haySesion = false;
    await u.click(screen.getByRole("button", { name: "Vencer" }));
    await screen.findByText("sesión: sin_sesion");
    await act(async () => {
      await new Promise((r) => setTimeout(r, 80));
    });
    expect(descartes()).toHaveLength(0);
  });

  test("al entrar otra vez, irse de la Hoja vuelve a descartar su borrador", async () => {
    const u = userEvent.setup();
    await conLaHojaAbierta();
    await u.click(screen.getByRole("button", { name: "Salir" }));
    await screen.findByText("sesión: sin_sesion");
    await u.click(screen.getByRole("button", { name: "Entrar" }));
    await screen.findByText("borrador: listo");
    await u.click(screen.getByRole("button", { name: "Cerrar la Hoja" }));
    await waitFor(() => expect(descartes()).toHaveLength(1));
  });
});
