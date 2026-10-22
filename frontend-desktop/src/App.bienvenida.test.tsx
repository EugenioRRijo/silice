import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "./api/cliente";
import { App } from "./App";
import { alertaConTexto } from "./test/ayudas";

// F1 y F3 con la forma del contrato de BCP-1 (docs/especificaciones/2026-10-21-bienvenida-casos-proyectos-design.md §9):
// estas pruebas simulan `fetch`; que el servidor real coincida lo comprueba la integración (BCP-10).
function json(cuerpo: unknown, estado = 200, cabeceras: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json", ...cabeceras },
  });
}

const sesionNueva = {
  login: "admin",
  nombre: "Ana Pérez",
  roles: ["administrador"],
  csrf: "tok-nuevo",
  debe_cambiar_clave: false,
  acciones: ["administrar_cuentas"],
  modo_entrega: false,
};

const estadoSinCuentas = {
  sin_cuentas: true,
  archivo_presente: true,
  modo: "producto",
  politica: { minimo: 10, maximo: 128 },
};

const CODIGO = "ABCD-EFGH-JKLM-NPQR-STUV";
const CLAVE = "una frase larga y tranquila";

describe("App: primer arranque y recuperar acceso", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let primerArranque: () => Response;
  let reclamo: (cuerpo: unknown) => Response | Promise<Response>;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf(null);
    window.location.hash = "";
    primerArranque = () => json(estadoSinCuentas);
    reclamo = () => json(sesionNueva, 201);
    let dentro = false;
    fetchFalso.mockImplementation(async (entrada, init) => {
      const ruta = String(entrada);
      const metodo = init?.method ?? "GET";
      if (ruta === "/v1/sesion" && metodo === "GET") {
        return dentro ? json(sesionNueva) : json({ detalle: "Sin sesión." }, 401);
      }
      if (ruta === "/v1/primer-arranque" && metodo === "GET") return primerArranque();
      if (ruta === "/v1/primer-arranque/reclamo" && metodo === "POST") {
        const respuesta = await reclamo(JSON.parse(String(init?.body)));
        if (respuesta.status === 201) dentro = true;
        return respuesta;
      }
      if (ruta === "/v1/sesion" && metodo === "DELETE") {
        dentro = false;
        return new Response(null, { status: 204 });
      }
      if (ruta === "/v1/casos") return json({ actual: { nombre: "a", ruta_relativa: "data/a.db" }, casos: [] });
      if (ruta === "/v1/proyectos") return json([]);
      if (ruta === "/v1/produccion/existencias") return json([]);
      if (ruta.startsWith("/v1/auditorias-libro")) return json([]);
      return json({ detalle: "Sin sesión." }, 401);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function llenarBienvenida(usuario: ReturnType<typeof userEvent.setup>) {
    await usuario.type(await screen.findByLabelText("Código de instalación"), CODIGO);
    await usuario.type(screen.getByLabelText("Su nombre"), "Ana Pérez");
    await usuario.type(screen.getByLabelText("Usuario"), "admin");
    await usuario.type(screen.getByLabelText("Contraseña"), CLAVE);
    await usuario.type(screen.getByLabelText("Repita la contraseña"), CLAVE);
  }

  test("sin sesión pide GET /v1/primer-arranque y, sin cuentas, muestra la bienvenida y no «Entrar»", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "Bienvenida a Sílice" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Entrar" })).not.toBeInTheDocument();
    expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/primer-arranque")).toBe(true);
    // La cabecera mínima del marco (sin selectores) sigue ahí.
    expect(screen.getByRole("banner")).toHaveTextContent("Sílice");
  });

  test("mientras pregunta no muestra ni «Entrar» ni la bienvenida: una sola pantalla, sin parpadeo", async () => {
    let contestar: (r: Response) => void = () => {};
    const base = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation(async (entrada, init) => {
      if (String(entrada) === "/v1/primer-arranque") return new Promise<Response>((r) => (contestar = r));
      return base(entrada, init);
    });
    render(<App />);
    expect(await screen.findByText(/Comprobando/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Entrar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Bienvenida a Sílice" })).not.toBeInTheDocument();
    contestar(json({ ...estadoSinCuentas, sin_cuentas: false }));
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });

  test("con cuentas muestra «Entrar» con el enlace «Perdí el acceso de administrador»", async () => {
    primerArranque = () => json({ ...estadoSinCuentas, sin_cuentas: false });
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Perdí el acceso de administrador" })).toBeInTheDocument();
  });

  test.each([
    ["403 por equipo remoto", () => json({ detalle: "Solo desde el propio equipo." }, 403)],
    ["500", () => json({ detalle: "Error." }, 500)],
    ["cuerpo roto", () => new Response("no es json", { status: 200 })],
  ])("si el estado falla (%s) muestra «Entrar» y nunca una alerta", async (_nombre, respuesta) => {
    primerArranque = respuesta;
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryAllByRole("alert").filter((a) => (a.textContent ?? "").trim() !== "")).toHaveLength(0);
  });

  test("«Perdí el acceso…» abre Recuperar y «Volver a Entrar» regresa", async () => {
    const usuario = userEvent.setup();
    primerArranque = () => json({ ...estadoSinCuentas, sin_cuentas: false });
    render(<App />);
    await usuario.click(await screen.findByRole("button", { name: "Perdí el acceso de administrador" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Recuperar el acceso de administrador" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Entrar" })).not.toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Volver a Entrar" }));
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });

  test("con la sesión vencida vuelve a «Entrar» con su aviso, sin volver a preguntar por el primer arranque", async () => {
    // El 401 de una ruta en medio del trabajo: hay cuentas, así que no se pregunta por la bienvenida.
    let dentro = true;
    const base = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation(async (entrada, init) => {
      const ruta = String(entrada);
      if (ruta === "/v1/sesion" && (init?.method ?? "GET") === "GET") {
        return dentro ? json(sesionNueva) : json({ detalle: "Sin sesión." }, 401);
      }
      if (ruta === "/v1/proyectos") {
        dentro = false;
        return json({ detalle: "Su sesión venció." }, 401);
      }
      return base(entrada, init);
    });
    render(<App />);
    expect(await screen.findByText("Su sesión venció. Entre de nuevo para seguir.", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/primer-arranque")).toBe(false);
  });

  test("el reclamo manda el cuerpo del contrato, la sesión queda abierta y lleva al Inicio", async () => {
    const usuario = userEvent.setup();
    const espia = vi.spyOn(Storage.prototype, "setItem");
    const recibido: unknown[] = [];
    reclamo = (cuerpo) => {
      recibido.push(cuerpo);
      return json(sesionNueva, 201);
    };
    render(<App />);
    await llenarBienvenida(usuario);
    await usuario.click(screen.getByRole("checkbox", { name: /armar presupuestos/ }));
    await usuario.click(screen.getByRole("button", { name: "Crear la cuenta y entrar" }));

    expect(await screen.findByText("Ana Pérez", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salir/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Bienvenida a Sílice" })).not.toBeInTheDocument();
    expect(recibido).toEqual([
      { codigo: CODIGO, usuario: "admin", nombre: "Ana Pérez", contrasena: CLAVE, tambien_arma: true },
    ]);
    const llamada = fetchFalso.mock.calls.find((c) => String(c[0]) === "/v1/primer-arranque/reclamo");
    expect(llamada?.[1]?.method).toBe("POST");
    expect(new Headers(llamada?.[1]?.headers).get("Content-Type")).toBe("application/json");
    // F4: ni el código ni la contraseña quedaron en el navegador.
    expect(espia).not.toHaveBeenCalled();
    expect(window.location.href).not.toContain(CODIGO);
    expect(document.title).not.toContain(CODIGO);
    espia.mockRestore();
  });

  test("el token anti-CSRF del 201 se usa en las peticiones siguientes (Salir)", async () => {
    const usuario = userEvent.setup();
    render(<App />);
    await llenarBienvenida(usuario);
    await usuario.click(screen.getByRole("button", { name: "Crear la cuenta y entrar" }));
    await usuario.click(await screen.findByRole("button", { name: /^Salir/ }, { timeout: 5000 }));
    const borrado = fetchFalso.mock.calls.find((c) => c[1]?.method === "DELETE");
    expect(new Headers(borrado?.[1]?.headers).get("X-Silice-CSRF")).toBe("tok-nuevo");
  });

  test("un 401 del reclamo se queda en la bienvenida con el detalle tal cual", async () => {
    const usuario = userEvent.setup();
    reclamo = () => json({ detalle: "El código no es válido o ya se usó." }, 401);
    render(<App />);
    await llenarBienvenida(usuario);
    await usuario.click(screen.getByRole("button", { name: "Crear la cuenta y entrar" }));
    expect(await alertaConTexto()).toHaveTextContent("El código no es válido o ya se usó.");
    expect(screen.getByRole("heading", { name: "Bienvenida a Sílice" })).toBeInTheDocument();
  });

  test("un 429 con Retry-After lo dice con los segundos y deja el botón en espera", async () => {
    const usuario = userEvent.setup();
    reclamo = () => json({ detalle: "Demasiados intentos fallidos en este equipo." }, 429, { "Retry-After": "7" });
    render(<App />);
    await llenarBienvenida(usuario);
    await usuario.click(screen.getByRole("button", { name: "Crear la cuenta y entrar" }));
    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent("Demasiados intentos fallidos en este equipo.");
    expect(alerta).toHaveTextContent("Espere 7 segundos");
    expect(screen.getByRole("button", { name: /Espere/ })).toBeDisabled();
  });

  test("un 503 y un 423 dicen su detalle", async () => {
    const usuario = userEvent.setup();
    reclamo = () => json({ detalle: "La base de datos está ocupada. Pruebe de nuevo en unos segundos." }, 503);
    render(<App />);
    await llenarBienvenida(usuario);
    await usuario.click(screen.getByRole("button", { name: "Crear la cuenta y entrar" }));
    expect(await alertaConTexto()).toHaveTextContent("La base de datos está ocupada.");
  });

  test("recuperar con cuentas: el código nuevo abre la sesión y lleva al marco", async () => {
    const usuario = userEvent.setup();
    primerArranque = () => json({ ...estadoSinCuentas, sin_cuentas: false });
    const recibido: unknown[] = [];
    reclamo = (cuerpo) => {
      recibido.push(cuerpo);
      return json(sesionNueva, 201);
    };
    render(<App />);
    await usuario.click(await screen.findByRole("button", { name: "Perdí el acceso de administrador" }));
    await usuario.type(await screen.findByLabelText("Código de restablecimiento"), CODIGO);
    await usuario.type(screen.getByLabelText("Usuario del administrador"), "admin");
    await usuario.type(screen.getByLabelText("Su nombre"), "Ana Pérez");
    await usuario.type(screen.getByLabelText("Contraseña nueva"), CLAVE);
    await usuario.type(screen.getByLabelText("Repita la contraseña nueva"), CLAVE);
    await usuario.click(screen.getByRole("button", { name: "Restablecer y entrar" }));
    expect(await screen.findByText("Ana Pérez", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(recibido).toEqual([
      { codigo: CODIGO, usuario: "admin", nombre: "Ana Pérez", contrasena: CLAVE, tambien_arma: false },
    ]);
    expect(screen.queryByRole("heading", { name: "Recuperar el acceso de administrador" })).not.toBeInTheDocument();
  });

  test("tras Salir con la cuenta recién creada vuelve a preguntar y muestra «Entrar» (ya hay cuentas)", async () => {
    const usuario = userEvent.setup();
    render(<App />);
    await llenarBienvenida(usuario);
    await usuario.click(screen.getByRole("button", { name: "Crear la cuenta y entrar" }));
    primerArranque = () => json({ ...estadoSinCuentas, sin_cuentas: false });
    await usuario.click(await screen.findByRole("button", { name: /^Salir/ }, { timeout: 5000 }));
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });
});
