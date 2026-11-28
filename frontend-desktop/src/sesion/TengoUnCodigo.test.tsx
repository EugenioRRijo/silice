import { render, renderHook, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf, pedir } from "../api/cliente";
import { alertaConTexto } from "../test/ayudas";
import { TengoUnCodigo } from "./TengoUnCodigo";
import { useSesion } from "./useSesion";

function json(cuerpo: unknown, estado = 200, cabeceras?: Record<string, string>): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json", ...cabeceras },
  });
}

const CLAVE = "frase-secreta-canje-12";
const SESION_ABIERTA = {
  login: "mrivas",
  nombre: "María Rivas",
  roles: ["arma"],
  csrf: "tok-canje",
  debe_cambiar_clave: false,
  acciones: ["leer_proyecto"],
  modo_entrega: false,
};

describe("TengoUnCodigo", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf(null);
  });

  afterEach(() => {
    fijarCsrf(null);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  test("muestra el h1, los campos Usuario, Contraseña y Código con su ayuda exacta, y el botón Volver", () => {
    render(<TengoUnCodigo alVolver={vi.fn()} />);
    const h1 = screen.getByRole("heading", { level: 1, name: "Tengo un código" });
    expect(h1.className).toContain("cds--type-heading-04");
    expect(document.title).toBe("Tengo un código · Sílice");
    expect(screen.getByRole("textbox", { name: "Usuario" })).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña")).toHaveAttribute("type", "password");
    const campoCodigo = screen.getByRole("textbox", { name: "Código" });
    expect(campoCodigo).toBeInTheDocument();
    expect(
      screen.getByText("20 caracteres en 5 grupos de 4, como lo recibió en su correo"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Canjear el código y entrar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Volver" })).toHaveAttribute("type", "button");
  });

  test("acepta pegado con guiones o espacios, hace POST /v1/solicitudes/canjear y con 200 abre la sesión en useSesion", async () => {
    const usuario = userEvent.setup();
    const espiaStorage = vi.spyOn(Storage.prototype, "setItem");
    fetchFalso.mockImplementation(async (entrada, init) => {
      const ruta = String(entrada);
      if (ruta === "/v1/sesion" && (init?.method ?? "GET") === "GET") {
        return json({ detalle: "Sin sesión." }, 401);
      }
      if (ruta === "/v1/solicitudes/canjear" && init?.method === "POST") {
        return json(SESION_ABIERTA, 200);
      }
      return json({ ok: true }, 200);
    });

    const { result } = renderHook(() => useSesion());
    await waitFor(() => expect(result.current.estado.tipo).toBe("sin_sesion"));

    render(<TengoUnCodigo />);
    await usuario.type(screen.getByRole("textbox", { name: "Usuario" }), "mrivas");
    await usuario.type(screen.getByLabelText("Contraseña"), CLAVE);
    const campoCodigo = screen.getByRole("textbox", { name: "Código" });
    campoCodigo.focus();
    await usuario.paste("ABCD EFGH-JKLM NPQR STUV");
    expect(campoCodigo).toHaveValue("ABCD EFGH-JKLM NPQR STUV");

    await usuario.click(screen.getByRole("button", { name: "Canjear el código y entrar" }));

    await waitFor(() => expect(result.current.estado.tipo).toBe("activa"));
    if (result.current.estado.tipo === "activa") {
      expect(result.current.estado.sesion).toMatchObject({
        login: "mrivas",
        nombre: "María Rivas",
        roles: ["arma"],
        csrf: "tok-canje",
      });
    }

    const llamadaCanje = fetchFalso.mock.calls.find(([r]) => String(r) === "/v1/solicitudes/canjear");
    expect(llamadaCanje).toBeDefined();
    expect(JSON.parse(String(llamadaCanje?.[1]?.body))).toEqual({
      login: "mrivas",
      contrasena: CLAVE,
      codigo: "ABCD EFGH-JKLM NPQR STUV",
    });

    await pedir("/v1/comprobacion", { metodo: "POST", cuerpo: {} });
    const ultima = fetchFalso.mock.calls.at(-1)!;
    expect(new Headers(ultima[1]?.headers).get("X-Silice-CSRF")).toBe("tok-canje");
    expect(espiaStorage).not.toHaveBeenCalled();
  });

  test("con campos vacíos no llama a la API y lleva el foco al primer campo faltante", async () => {
    const usuario = userEvent.setup();
    render(<TengoUnCodigo />);

    await usuario.click(screen.getByRole("button", { name: "Canjear el código y entrar" }));
    expect(fetchFalso).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox", { name: "Usuario" })).toHaveFocus();
  });

  // T4 (mutante TC1): un código que solo trae separadores (guiones y espacios) cuenta como vacío.
  test("un código de solo guiones y espacios no llama a la API y lleva el foco al código", async () => {
    const usuario = userEvent.setup();
    render(<TengoUnCodigo />);
    await usuario.type(screen.getByRole("textbox", { name: "Usuario" }), "mrivas");
    await usuario.type(screen.getByLabelText("Contraseña"), CLAVE);
    const campoCodigo = screen.getByRole("textbox", { name: "Código" });
    campoCodigo.focus();
    await usuario.paste("- - --");

    await usuario.click(screen.getByRole("button", { name: "Canjear el código y entrar" }));
    expect(fetchFalso).not.toHaveBeenCalled();
    expect(campoCodigo).toHaveFocus();
    expect(screen.getByText("Escriba el código de 20 caracteres.")).toBeInTheDocument();
  });

  test("401 muestra el mensaje del servidor y limpia la contraseña y el código", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(
      json({ detalle: "El usuario, la contraseña o el código no son válidos." }, 401),
    );

    render(<TengoUnCodigo />);
    await usuario.type(screen.getByRole("textbox", { name: "Usuario" }), "mrivas");
    await usuario.type(screen.getByLabelText("Contraseña"), CLAVE);
    await usuario.type(screen.getByRole("textbox", { name: "Código" }), "ABCD-EFGH-JKLM-NPQR-STUV");
    await usuario.click(screen.getByRole("button", { name: "Canjear el código y entrar" }));

    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent("El usuario, la contraseña o el código no son válidos.");
    expect(screen.getByLabelText("Contraseña")).toHaveValue("");
    expect(screen.getByRole("textbox", { name: "Código" })).toHaveValue("");
    expect(document.body.innerHTML).not.toContain(CLAVE);
  });

  test("423 muestra el mensaje de cuenta bloqueada del servidor", async () => {
    const usuario = userEvent.setup();
    const detalle =
      "Demasiados intentos fallidos. Espere 15 minutos o pida al administrador que desbloquee la cuenta.";
    fetchFalso.mockResolvedValueOnce(json({ detalle }, 423));

    render(<TengoUnCodigo />);
    await usuario.type(screen.getByRole("textbox", { name: "Usuario" }), "mrivas");
    await usuario.type(screen.getByLabelText("Contraseña"), CLAVE);
    await usuario.type(screen.getByRole("textbox", { name: "Código" }), "ABCD-EFGH-JKLM-NPQR-STUV");
    await usuario.click(screen.getByRole("button", { name: "Canjear el código y entrar" }));

    expect(await alertaConTexto()).toHaveTextContent(detalle);
  });

  test("429 muestra el detalle del servidor y los segundos de espera de Retry-After", async () => {
    const usuario = userEvent.setup();
    const detalle = "Demasiados intentos fallidos en este equipo. Espere unos segundos y vuelva a probar.";
    fetchFalso.mockResolvedValueOnce(json({ detalle }, 429, { "Retry-After": "30" }));

    render(<TengoUnCodigo />);
    await usuario.type(screen.getByRole("textbox", { name: "Usuario" }), "mrivas");
    await usuario.type(screen.getByLabelText("Contraseña"), CLAVE);
    await usuario.type(screen.getByRole("textbox", { name: "Código" }), "ABCD-EFGH-JKLM-NPQR-STUV");
    await usuario.click(screen.getByRole("button", { name: "Canjear el código y entrar" }));

    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent(detalle);
    expect(alerta).toHaveTextContent("Espere 30 segundos antes de volver a intentarlo.");
  });

  test("429 con Retry-After de 1 usa el singular", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(
      json({ detalle: "Demasiados intentos fallidos en este equipo." }, 429, { "Retry-After": "1" }),
    );

    render(<TengoUnCodigo />);
    await usuario.type(screen.getByRole("textbox", { name: "Usuario" }), "mrivas");
    await usuario.type(screen.getByLabelText("Contraseña"), CLAVE);
    await usuario.type(screen.getByRole("textbox", { name: "Código" }), "ABCD-EFGH-JKLM-NPQR-STUV");
    await usuario.click(screen.getByRole("button", { name: "Canjear el código y entrar" }));

    expect(await alertaConTexto()).toHaveTextContent("Espere 1 segundo antes de volver a intentarlo.");
  });
});
