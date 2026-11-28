import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { alertaConTexto } from "../test/ayudas";
import { CrearCuenta } from "./CrearCuenta";

function json(cuerpo: unknown, estado = 200, cabeceras?: Record<string, string>): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json", ...cabeceras },
  });
}

const CLAVE_SECRETA = "frase-larga-segura-2026";
const MENSAJE_201 =
  "Su solicitud quedó registrada. Cuando el administrador la apruebe, le llegará un código de 20 caracteres a su correo. Escríbalo en “Tengo un código”.";

describe("CrearCuenta", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  async function llenarFormulario(usuario: ReturnType<typeof userEvent.setup>, clave = CLAVE_SECRETA) {
    await usuario.type(screen.getByRole("textbox", { name: "Nombre" }), "María Rivas");
    await usuario.type(screen.getByRole("textbox", { name: "Correo" }), "maria@empresa.com");
    await usuario.type(screen.getByRole("textbox", { name: "Usuario" }), "mrivas");
    await usuario.type(screen.getByLabelText("Contraseña"), clave);
    await usuario.type(screen.getByLabelText("Confirme la contraseña"), clave);
  }

  test("muestra el título h1, los campos y los botones «Enviar la solicitud» y «Volver»", () => {
    render(<CrearCuenta alVolver={vi.fn()} alIrACanjear={vi.fn()} />);
    const h1 = screen.getByRole("heading", { level: 1, name: "Crear una cuenta" });
    expect(h1.className).toContain("cds--type-heading-04");
    expect(document.title).toBe("Crear una cuenta · Sílice");
    expect(screen.getByRole("textbox", { name: "Nombre" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Correo" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Usuario" })).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña")).toHaveAttribute("type", "password");
    expect(screen.getByLabelText("Confirme la contraseña")).toHaveAttribute("type", "password");
    expect(screen.getByRole("button", { name: "Enviar la solicitud" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Volver" })).toHaveAttribute("type", "button");
  });

  test("con campos vacíos o contraseñas que no coinciden no llama a la API y lleva el foco al primer error", async () => {
    const usuario = userEvent.setup();
    render(<CrearCuenta alVolver={vi.fn()} alIrACanjear={vi.fn()} />);

    await usuario.click(screen.getByRole("button", { name: "Enviar la solicitud" }));
    expect(fetchFalso).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox", { name: "Nombre" })).toHaveFocus();

    await usuario.type(screen.getByRole("textbox", { name: "Nombre" }), "María Rivas");
    await usuario.type(screen.getByRole("textbox", { name: "Correo" }), "maria@empresa.com");
    await usuario.type(screen.getByRole("textbox", { name: "Usuario" }), "mrivas");
    await usuario.type(screen.getByLabelText("Contraseña"), CLAVE_SECRETA);
    await usuario.type(screen.getByLabelText("Confirme la contraseña"), "otra-distinta-123");
    await usuario.click(screen.getByRole("button", { name: "Enviar la solicitud" }));

    expect(fetchFalso).not.toHaveBeenCalled();
    expect(screen.getByText("Las contraseñas no coinciden.")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirme la contraseña")).toHaveFocus();
  });

  test("201 envía POST /v1/solicitudes, borra la contraseña del estado y ofrece «Ya tengo el código»", async () => {
    const usuario = userEvent.setup();
    const alIrACanjear = vi.fn();
    fetchFalso.mockResolvedValueOnce(json({ mensaje: MENSAJE_201 }, 201));

    render(<CrearCuenta alVolver={vi.fn()} alIrACanjear={alIrACanjear} />);
    await llenarFormulario(usuario);
    await usuario.click(screen.getByRole("button", { name: "Enviar la solicitud" }));

    expect(await screen.findByText(MENSAJE_201)).toBeInTheDocument();
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    const [ruta, init] = fetchFalso.mock.calls[0]!;
    expect(ruta).toBe("/v1/solicitudes");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({
      nombre: "María Rivas",
      correo: "maria@empresa.com",
      login: "mrivas",
      contrasena: CLAVE_SECRETA,
    });
    expect(document.body.innerHTML).not.toContain(CLAVE_SECRETA);

    await usuario.click(screen.getByRole("button", { name: "Ya tengo el código" }));
    expect(alIrACanjear).toHaveBeenCalledTimes(1);
  });

  test("409 muestra el mensaje junto al campo Usuario con el foco allí y borra la contraseña del estado", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json({ detalle: "Ese usuario ya está en uso; elija otro." }, 409));

    render(<CrearCuenta alVolver={vi.fn()} alIrACanjear={vi.fn()} />);
    await llenarFormulario(usuario);
    await usuario.click(screen.getByRole("button", { name: "Enviar la solicitud" }));

    expect(await screen.findByText("Ese usuario ya está en uso; elija otro.")).toBeInTheDocument();
    const campoUsuario = screen.getByRole("textbox", { name: "Usuario" });
    expect(campoUsuario).toHaveAttribute("aria-invalid", "true");
    await waitFor(() => expect(campoUsuario).toHaveFocus());
    expect(screen.getByLabelText("Contraseña")).toHaveValue("");
    expect(screen.getByLabelText("Confirme la contraseña")).toHaveValue("");
    expect(document.body.innerHTML).not.toContain(CLAVE_SECRETA);
  });

  test("422 de correo muestra el mensaje junto al campo Correo con el foco allí y vacía la contraseña", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(
      json({ detalle: "Escriba un correo válido, como nombre@empresa.com." }, 422),
    );

    render(<CrearCuenta alVolver={vi.fn()} alIrACanjear={vi.fn()} />);
    await llenarFormulario(usuario);
    await usuario.click(screen.getByRole("button", { name: "Enviar la solicitud" }));

    expect(await screen.findByText("Escriba un correo válido, como nombre@empresa.com.")).toBeInTheDocument();
    const campoCorreo = screen.getByRole("textbox", { name: "Correo" });
    expect(campoCorreo).toHaveAttribute("aria-invalid", "true");
    await waitFor(() => expect(campoCorreo).toHaveFocus());
    expect(screen.getByLabelText("Contraseña")).toHaveValue("");
    expect(screen.getByLabelText("Confirme la contraseña")).toHaveValue("");
  });

  test("422 de contraseña muestra el mensaje junto al campo Contraseña con el foco allí y vacía el estado", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(
      json({ detalle: "Esa contraseña es demasiado común; elija otra." }, 422),
    );

    render(<CrearCuenta alVolver={vi.fn()} alIrACanjear={vi.fn()} />);
    await llenarFormulario(usuario);
    await usuario.click(screen.getByRole("button", { name: "Enviar la solicitud" }));

    expect(await screen.findByText("Esa contraseña es demasiado común; elija otra.")).toBeInTheDocument();
    const campoContrasena = screen.getByLabelText("Contraseña");
    expect(campoContrasena).toHaveAttribute("aria-invalid", "true");
    await waitFor(() => expect(campoContrasena).toHaveFocus());
    expect(campoContrasena).toHaveValue("");
    expect(screen.getByLabelText("Confirme la contraseña")).toHaveValue("");
  });

  test("429 muestra el mensaje del servidor arriba con el foco en el aviso y vacía la contraseña", async () => {
    const usuario = userEvent.setup();
    const detalle = "Hay demasiadas solicitudes pendientes. Pida al administrador que revise las que hay.";
    fetchFalso.mockResolvedValueOnce(json({ detalle }, 429, { "Retry-After": "60" }));

    render(<CrearCuenta alVolver={vi.fn()} alIrACanjear={vi.fn()} />);
    await llenarFormulario(usuario);
    await usuario.click(screen.getByRole("button", { name: "Enviar la solicitud" }));

    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent(detalle);
    expect(alerta).toHaveTextContent("Espere 60 segundos");
    await waitFor(() => expect(alerta.closest("[tabindex='-1']")).toHaveFocus());
    expect(screen.getByLabelText("Contraseña")).toHaveValue("");
    expect(screen.getByLabelText("Confirme la contraseña")).toHaveValue("");
    expect(document.body.innerHTML).not.toContain(CLAVE_SECRETA);
  });

  // T4 (mutante CC2): mientras la confirmación sigue vacía no se acusa que no coincide; en cuanto se escribe otra, sí.
  test("la confirmación solo avisa que no coincide cuando ya se escribió algo distinto", async () => {
    const usuario = userEvent.setup();
    render(<CrearCuenta alVolver={vi.fn()} alIrACanjear={vi.fn()} />);

    await usuario.type(screen.getByLabelText("Contraseña"), CLAVE_SECRETA);
    expect(screen.queryByText("Las contraseñas no coinciden.")).toBeNull();

    await usuario.type(screen.getByLabelText("Confirme la contraseña"), "otra");
    expect(screen.getByText("Las contraseñas no coinciden.")).toBeInTheDocument();
  });

  // T4 (mutante CC5): los espacios sobrantes de nombre, correo y usuario no viajan al servidor.
  test("envía el nombre, el correo y el usuario sin espacios sobrantes", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json({ mensaje: MENSAJE_201 }, 201));
    render(<CrearCuenta alVolver={vi.fn()} alIrACanjear={vi.fn()} />);

    await usuario.type(screen.getByRole("textbox", { name: "Nombre" }), "  María Rivas  ");
    await usuario.type(screen.getByRole("textbox", { name: "Correo" }), " maria@empresa.com ");
    await usuario.type(screen.getByRole("textbox", { name: "Usuario" }), " mrivas ");
    await usuario.type(screen.getByLabelText("Contraseña"), CLAVE_SECRETA);
    await usuario.type(screen.getByLabelText("Confirme la contraseña"), CLAVE_SECRETA);
    await usuario.click(screen.getByRole("button", { name: "Enviar la solicitud" }));

    await screen.findByText(MENSAJE_201);
    expect(JSON.parse(String(fetchFalso.mock.calls[0]![1]?.body))).toEqual({
      nombre: "María Rivas",
      correo: "maria@empresa.com",
      login: "mrivas",
      contrasena: CLAVE_SECRETA,
    });
  });

  test("«Volver» llama a alVolver sin enviar nada", async () => {
    const usuario = userEvent.setup();
    const alVolver = vi.fn();
    render(<CrearCuenta alVolver={alVolver} alIrACanjear={vi.fn()} />);

    await usuario.click(screen.getByRole("button", { name: "Volver" }));
    expect(alVolver).toHaveBeenCalledTimes(1);
    expect(fetchFalso).not.toHaveBeenCalled();
  });
});
