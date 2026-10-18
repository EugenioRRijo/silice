import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "./api/cliente";
import { App } from "./App";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const sesion = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["revisa"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["leer_proyecto", "revisar_paquete", "cambiar_caso"],
  modo_entrega: false,
};

const casos = {
  actual: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
  casos: [{ nombre: "clinica", ruta_relativa: "data/clinica.db" }],
};

describe("App", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  // Lo que contesta GET /v1/sesion; cada prueba lo cambia.
  let sesionActual: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf(null);
    window.location.hash = "";
    sesionActual = () => json(sesion);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const ruta = String(entrada);
      const metodo = init?.method ?? "GET";
      if (ruta === "/v1/sesion" && metodo === "GET") return sesionActual();
      if (ruta === "/v1/sesion" && metodo === "DELETE") return new Response(null, { status: 204 });
      if (ruta === "/v1/casos") return json(casos);
      if (ruta === "/v1/proyectos") return json([]);
      return json({ detalle: "Sin sesión." }, 401);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("la cabecera dice Sílice", async () => {
    sesionActual = () => json({ detalle: "Sin sesión." }, 401);
    render(<App />);
    expect(screen.getByRole("banner")).toHaveTextContent("Sílice");
    await screen.findByRole("heading", { name: "Entrar" });
  });

  test("sin sesion muestra el formulario de entrada", async () => {
    sesionActual = () => json({ detalle: "Sin sesión." }, 401);
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

  test("con sesion vigente muestra el nombre, Salir, el menu y aterriza en el Inicio", async () => {
    render(<App />);
    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salir" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Libro de la empresa" })).toBeInTheDocument();
    // La pagina llega por import() dinamico: con la suite entera en marcha tarda mas que el plazo por omision.
    expect(await screen.findByRole("heading", { name: "Audite un presupuesto" }, { timeout: 5000 })).toBeInTheDocument();
    expect(window.location.hash).toBe("#/inicio");
  });

  test("una direccion con #/libros abre esa pagina", async () => {
    window.location.hash = "#/libros";
    render(<App />);
    expect(
      await screen.findByRole("button", { name: /Suelte aquí el libro \.xlsx de la empresa/ }, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  test("una API anterior, sin acciones ni modo_entrega, no tumba la pantalla", async () => {
    sesionActual = () => json({ login: "ana", nombre: "Ana Pérez", roles: ["revisa"], csrf: "tok" });
    render(<App />);
    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    // El Inicio no exige ninguna accion: una cuenta sin acciones igual aterriza en el.
    expect(await screen.findByRole("heading", { name: "Audite un presupuesto" }, { timeout: 5000 })).toBeInTheDocument();
  });

  test("entrar con una cuenta buena abre el shell y guarda el token solo en memoria", async () => {
    const usuario = userEvent.setup();
    const espia = vi.spyOn(Storage.prototype, "setItem");
    let entro = false;
    sesionActual = () => (entro ? json(sesion) : json({ detalle: "Sin sesión." }, 401));
    const base = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation(async (entrada, init) => {
      if (String(entrada) === "/v1/sesion" && init?.method === "POST") {
        entro = true;
        return json(sesion);
      }
      return base(entrada, init);
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
    render(<App />);
    await usuario.click(await screen.findByRole("button", { name: "Salir" }));
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    const borrado = fetchFalso.mock.calls.find((c) => c[1]?.method === "DELETE");
    expect(new Headers(borrado?.[1]?.headers).get("X-Silice-CSRF")).toBe("tok");
  });

  describe("cambio de contrasena obligatorio", () => {
    const provisional = { ...sesion, debe_cambiar_clave: true, acciones: [] };

    test("con debe_cambiar_clave solo se ve el cambio de contrasena, sin menu ni pidiendo datos", async () => {
      sesionActual = () => json(provisional);
      render(<App />);
      expect(await screen.findByRole("heading", { name: "Cambie su contraseña" })).toBeInTheDocument();
      expect(screen.queryByRole("navigation", { name: "Menú principal" })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Salir" })).toBeInTheDocument();
      expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/casos")).toBe(false);
      expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/proyectos")).toBe(false);
    });

    test("entrar con una cuenta provisional lleva al cambio", async () => {
      const usuario = userEvent.setup();
      sesionActual = () => json({ detalle: "Sin sesión." }, 401);
      const base = fetchFalso.getMockImplementation()!;
      fetchFalso.mockImplementation(async (entrada, init) => {
        if (String(entrada) === "/v1/sesion" && init?.method === "POST") return json(provisional);
        return base(entrada, init);
      });
      render(<App />);
      await usuario.type(await screen.findByLabelText("Usuario"), "ana");
      await usuario.type(screen.getByLabelText("Contraseña"), "provisional");
      await usuario.click(screen.getByRole("button", { name: "Entrar" }));
      expect(await screen.findByRole("heading", { name: "Cambie su contraseña" })).toBeInTheDocument();
    });

    test("al cambiarla manda actual y nueva con el token y entra al shell", async () => {
      const usuario = userEvent.setup();
      let cambiada = false;
      sesionActual = () => json(cambiada ? { ...sesion, csrf: "tok2" } : provisional);
      const base = fetchFalso.getMockImplementation()!;
      fetchFalso.mockImplementation(async (entrada, init) => {
        if (String(entrada) === "/v1/sesion/contrasena" && init?.method === "POST") {
          cambiada = true;
          return new Response(null, { status: 204 });
        }
        return base(entrada, init);
      });
      render(<App />);
      await usuario.type(await screen.findByLabelText("Contraseña actual"), "provisional");
      await usuario.type(screen.getByLabelText("Contraseña nueva"), "una-clave-larga-1");
      await usuario.type(screen.getByLabelText("Confirme la contraseña nueva"), "una-clave-larga-1");
      await usuario.click(screen.getByRole("button", { name: "Cambiar contraseña" }));

      expect(await screen.findByRole("navigation", { name: "Menú principal" })).toBeInTheDocument();
      const llamada = fetchFalso.mock.calls.find((c) => String(c[0]) === "/v1/sesion/contrasena");
      expect(llamada?.[1]?.body).toBe(JSON.stringify({ actual: "provisional", nueva: "una-clave-larga-1" }));
      expect(new Headers(llamada?.[1]?.headers).get("X-Silice-CSRF")).toBe("tok");
      expect(screen.queryByRole("heading", { name: "Cambie su contraseña" })).not.toBeInTheDocument();
    });

    test("si la API rechaza la contrasena nueva sigue en el cambio y muestra el detalle", async () => {
      const usuario = userEvent.setup();
      sesionActual = () => json(provisional);
      const base = fetchFalso.getMockImplementation()!;
      fetchFalso.mockImplementation(async (entrada, init) => {
        if (String(entrada) === "/v1/sesion/contrasena") {
          return json({ detalle: "La contraseña nueva es demasiado corta." }, 422);
        }
        return base(entrada, init);
      });
      render(<App />);
      await usuario.type(await screen.findByLabelText("Contraseña actual"), "provisional");
      await usuario.type(screen.getByLabelText("Contraseña nueva"), "corta");
      await usuario.type(screen.getByLabelText("Confirme la contraseña nueva"), "corta");
      await usuario.click(screen.getByRole("button", { name: "Cambiar contraseña" }));
      expect(await screen.findByText("La contraseña nueva es demasiado corta.")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Cambie su contraseña" })).toBeInTheDocument();
    });
  });
});
