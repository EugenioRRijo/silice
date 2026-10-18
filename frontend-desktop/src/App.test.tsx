import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "./api/cliente";
import { App } from "./App";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const sesion = { login: "ana", nombre: "Ana Pérez", roles: ["revisa"], csrf: "tok" };

describe("App", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf(null);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("la cabecera dice Sílice", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "Sin sesión." }, 401));
    render(<App />);
    expect(screen.getByRole("banner")).toHaveTextContent("Sílice");
    await screen.findByRole("heading", { name: "Entrar" });
  });

  test("sin sesion muestra el formulario de entrada", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "Sin sesión." }, 401));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.getByLabelText("Usuario")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Salir" })).not.toBeInTheDocument();
  });

  test("mientras comprueba la sesion no muestra el formulario", () => {
    fetchFalso.mockImplementation(() => new Promise<Response>(() => {}));
    render(<App />);
    expect(screen.queryByLabelText("Usuario")).not.toBeInTheDocument();
    expect(screen.getByText(/Comprobando su sesión/)).toBeInTheDocument();
  });

  test("con sesion vigente muestra el nombre, Salir y el visor", async () => {
    fetchFalso.mockImplementation(async () => json(sesion));
    render(<App />);
    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salir" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Suelte aquí el libro \.xlsx de la empresa/ })).toBeInTheDocument();
  });

  test("entrar con una cuenta buena abre el visor y guarda el token solo en memoria", async () => {
    const usuario = userEvent.setup();
    const espia = vi.spyOn(Storage.prototype, "setItem");
    fetchFalso.mockImplementation(async (entrada, init) => {
      if (String(entrada) === "/v1/sesion" && init?.method === "POST") return json(sesion);
      return json({ detalle: "Sin sesión." }, 401);
    });
    render(<App />);
    await usuario.type(await screen.findByLabelText("Usuario"), "ana");
    await usuario.type(screen.getByLabelText("Contraseña"), "clave");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    expect(espia).not.toHaveBeenCalled();
    espia.mockRestore();
  });

  test("Salir cierra la sesion con DELETE y vuelve al formulario", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockImplementation(async (_entrada, init) => {
      if (init?.method === "DELETE") return new Response(null, { status: 204 });
      return json(sesion);
    });
    render(<App />);
    await usuario.click(await screen.findByRole("button", { name: "Salir" }));
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    const borrado = fetchFalso.mock.calls.find((c) => c[1]?.method === "DELETE");
    expect(new Headers(borrado?.[1]?.headers).get("X-Silice-CSRF")).toBe("tok");
  });
});
